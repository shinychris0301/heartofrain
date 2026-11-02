"""Real loopback HTTP boundaries and isolated host controls; no provider/production claims."""
import contextlib
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from hotr_backend import monitoring122 as monitor


ORIGIN = 'https://api.novamind-it.ru'


class Reply:
    def __init__(self, value, status=200, content_type='application/json', encoding=None):
        self.status = status
        self.body = io.BytesIO(value if isinstance(value, bytes) else json.dumps(value).encode())
        self.headers = Message()
        self.headers['Content-Type'] = content_type
        if encoding:
            self.headers['Content-Encoding'] = encoding
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def read1(self, size):
        return self.body.read(size)


class Opener:
    def __init__(self, changes=None):
        self.changes, self.requests, self.replies = changes or {}, [], []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        path = urllib.parse.urlsplit(request.full_url).path
        value = self.changes.get(path)
        if isinstance(value, Exception):
            raise value
        if value is None:
            value = Reply({'status': 'ok', 'mode': 'staging', 'productionEnabled': False}) if path == '/healthz' else (
                Reply({'status': 'ready'}) if path == '/readyz' else Reply(b'', 404))
        self.replies.append(value)
        return value


class Monitor122Tests(unittest.TestCase):
    def test_healthy_public_and_loopback_probes_never_claim_production(self):
        opener = Opener()
        report = monitor.check(ORIGIN, loopback_port=8751, opener=opener)
        self.assertEqual(report['status'], 'healthy')
        self.assertEqual(len(report['checks']), 7)
        self.assertFalse(report['productionAcceptanceVerified'])
        self.assertFalse(report['backupFreshnessChecked'])
        self.assertTrue(all(reply.closed for reply in opener.replies))
        for request, timeout in opener.requests:
            self.assertEqual(request.get_header('Accept-encoding'), 'identity')
            self.assertNotIn('Authorization', request.headers)
            self.assertEqual(timeout, 3)

    def test_production_expectation_rejects_green_staging_health(self):
        report = monitor.check(ORIGIN, expected_mode='production', opener=Opener())
        self.assertEqual(report['status'], 'unavailable')
        self.assertEqual(report['checks'][0]['code'], 'unexpected_health_state')

    def test_outage_details_and_response_payloads_are_not_exported(self):
        sensitive = 'private-credential-that-must-not-appear'
        report = monitor.check(ORIGIN, opener=Opener({'/healthz': urllib.error.URLError(sensitive),
                                                     '/readyz': Reply({'status': sensitive}, 503)}))
        exported = json.dumps(report)
        self.assertNotIn(sensitive, exported)
        self.assertEqual(report['checks'][0]['code'], 'network_unavailable')
        self.assertEqual(report['checks'][1]['code'], 'unexpected_http_status')

    def test_redirect_handler_never_follows_or_forwards(self):
        handler = monitor._NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, None, None, 'https://elsewhere.net/secret'))
        opener = Opener({'/healthz': urllib.error.HTTPError(ORIGIN + '/healthz', 302, 'secret', {}, io.BytesIO(b'secret'))})
        report = monitor.check(ORIGIN, opener=opener)
        self.assertEqual(report['checks'][0]['httpStatus'], 302)
        self.assertEqual(report['checks'][0]['code'], 'unexpected_http_status')
        self.assertEqual(len(opener.requests), 5)

    def test_normal_tls_context_and_disabled_ambient_proxy_are_installed(self):
        with patch.object(monitor.ssl, 'create_default_context', wraps=monitor.ssl.create_default_context) as tls:
            opener = monitor._opener()
        tls.assert_called_once_with()
        https = next(handler for handler in opener.handlers if isinstance(handler, urllib.request.HTTPSHandler))
        self.assertTrue(https._context.check_hostname)
        self.assertEqual(https._context.verify_mode, monitor.ssl.CERT_REQUIRED)
        self.assertFalse(any(isinstance(handler, urllib.request.ProxyHandler) and handler.proxies for handler in opener.handlers))

    def test_invalid_limits_and_origins_reject_before_network(self):
        opener = Opener()
        for origin in ('http://api.novamind-it.ru', 'https://user:password@api.novamind-it.ru',
                       ORIGIN + '/path', ORIGIN + '?key=secret', ORIGIN + '#fragment',
                       'https://127.0.0.1', 'https://x.example.net', 'https://localhost', ORIGIN + ':444'):
            with self.subTest(origin=origin), self.assertRaises(monitor.MonitorError):
                monitor.check(origin, opener=opener)
        for options in ({'timeout': float('nan')}, {'timeout': True}, {'timeout': 0}, {'latency_ms': 0},
                        {'loopback_port': True}, {'loopback_port': 80}, {'max_backup_age_hours': 0}):
            with self.subTest(options=options), self.assertRaises(monitor.MonitorError):
                monitor.check(ORIGIN, opener=opener, **options)
        self.assertEqual(opener.requests, [])

    def test_oversize_duplicate_json_compressed_html_and_non_json_rejected(self):
        cases = [(Reply(b'x' * (monitor.MAX_BODY + 1)), 'response_too_large'),
                 (Reply(b'{"status":"ok","status":"ok"}'), 'invalid_json'),
                 (Reply({'status': 'ready'}, encoding='gzip'), 'encoded_response_rejected'),
                 (Reply(b'<html>secret</html>', content_type='text/html'), 'unexpected_content_type'),
                 (Reply(b'NaN'), 'invalid_json')]
        for reply, code in cases:
            with self.subTest(code=code):
                report = monitor.check(ORIGIN, opener=Opener({'/readyz': reply}))
                self.assertEqual(report['checks'][1]['code'], code)
                self.assertTrue(reply.closed)

    def test_latency_and_response_deadline_are_failure_signals(self):
        ticks = iter((1.0, 1.001, 1.002, 3.8))
        result = monitor._probe(Opener(), ORIGIN, 'public_https', 'health', '/healthz',
                                mode='staging', timeout=3, latency_ms=2500, clock=lambda: next(ticks))
        self.assertEqual(result['code'], 'latency_budget_exceeded')
        ticks = iter((1.0, 5.0, 5.0))
        result = monitor._probe(Opener(), ORIGIN, 'public_https', 'health', '/healthz',
                                mode='staging', timeout=3, latency_ms=2500, clock=lambda: next(ticks))
        self.assertEqual(result['code'], 'response_deadline_exceeded')

    def test_actual_loopback_http_health_and_unready_body_are_distinct(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = {'status': 'ok', 'mode': 'staging', 'productionEnabled': False} if self.path == '/healthz' else {'status': 'unavailable'}
                raw = json.dumps(body).encode()
                self.send_response(200 if self.path == '/healthz' else 503)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = 'http://127.0.0.1:' + str(server.server_port)
                health = monitor._probe(monitor._opener(), base, 'loopback', 'health', '/healthz', mode='staging', timeout=3, latency_ms=2500)
                ready = monitor._probe(monitor._opener(), base, 'loopback', 'readiness', '/readyz', mode='staging', timeout=3, latency_ms=2500)
                self.assertTrue(health['ok'])
                self.assertFalse(ready['ok'])
                self.assertEqual(ready['httpStatus'], 503)
            finally:
                server.shutdown()
                thread.join(3)
                self.assertFalse(thread.is_alive())

    def test_final_eof_beyond_deadline_fails_even_with_permissive_latency_budget(self):
        ticks = iter((0.0, 0.1, 0.2, 3.2))
        result = monitor._probe(Opener(), ORIGIN, 'public_https', 'health', '/healthz',
                                mode='staging', timeout=3, latency_ms=10000, clock=lambda: next(ticks))
        self.assertFalse(result['ok'])
        self.assertEqual(result['code'], 'response_deadline_exceeded')

    @staticmethod
    def backup_fixture(base):
        data = base / 'data'
        backups = data / 'backups'
        backups.mkdir(parents=True)
        manifest = {'mode': 'staging', 'publicOrigin': ORIGIN, 'dataDirectory': str(data),
                    'deploymentId': 'monitor-fixture122', 'identityScope': 'review-monitor122'}
        marker = dict(manifest, version=1, kind='HeartOfTheRainStaging105', state='Ready', nonce='a' * 32)
        manifest_path = base / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        (data / '.hotr-staging105-owner.json').write_text(json.dumps(marker), encoding='utf-8')
        proof = dict(version=1, kind='HeartOfTheRainStagingBackup105', state='Ready', snapshotName='snapshot',
                     schemaVersion=15, bytes=8, sha256='b' * 64,
                     **{key: marker[key] for key in ('publicOrigin', 'deploymentId', 'identityScope', 'nonce')})
        receipt = backups / 'snapshot.receipt.json'
        snapshot = backups / 'snapshot.sqlite3'
        receipt.write_text(json.dumps(proof), encoding='utf-8')
        snapshot.write_bytes(b'fixture!')
        return manifest_path, data, receipt, snapshot

    def test_backup_metadata_freshness_does_not_claim_integrity_or_off_host_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest, data, receipt, snapshot = self.backup_fixture(Path(temporary))
            before = {path: path.read_bytes() for path in (manifest, receipt, snapshot)}
            checks = monitor._backup_check(manifest, ORIGIN, 24, 1)
            self.assertTrue(all(item['ok'] for item in checks))
            self.assertFalse(checks[0]['snapshotIntegrityVerified'])
            self.assertFalse(checks[0]['offHostCopyVerified'])
            self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_stale_pending_foreign_and_sidecar_backup_are_failures(self):
        for variant in ('stale', 'pending', 'foreign', 'sidecar', 'future', 'missing', 'size'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                manifest, data, receipt, snapshot = self.backup_fixture(Path(temporary))
                proof = json.loads(receipt.read_bytes())
                if variant == 'stale':
                    os.utime(snapshot, (time.time() - 25 * 3600,) * 2)
                elif variant == 'future':
                    os.utime(snapshot, (time.time() + 1000,) * 2)
                    os.utime(receipt, (time.time() + 1000,) * 2)
                elif variant in ('pending', 'foreign'):
                    proof['state' if variant == 'pending' else 'nonce'] = 'Pending' if variant == 'pending' else 'c' * 32
                    receipt.write_text(json.dumps(proof), encoding='utf-8')
                elif variant == 'sidecar':
                    Path(str(snapshot) + '-wal').write_bytes(b'data')
                elif variant == 'missing':
                    snapshot.unlink()
                else:
                    snapshot.write_bytes(b'wrongsize')
                checks = monitor._backup_check(manifest, ORIGIN, 24, 1)
                self.assertFalse(checks[0]['ok'])

    def test_low_disk_and_bounded_inventory_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest, data, receipt, snapshot = self.backup_fixture(Path(temporary))
            with patch.object(monitor.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 0})()):
                self.assertFalse(monitor._backup_check(manifest, ORIGIN, 24, 1)[1]['ok'])
            with patch.object(monitor, 'MAX_BACKUPS', 1):
                (data / 'backups/third-file').write_bytes(b'')
                self.assertEqual(monitor._backup_check(manifest, ORIGIN, 24, 1)[0]['code'], 'backup_inventory_limit_exceeded')

    def test_report_updates_owned_status_but_preserves_unknown_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'status.json'
            report = monitor.check(ORIGIN, opener=Opener())
            monitor.write_report(target, report)
            self.assertEqual(json.loads(target.read_bytes()), report)
            report['status'] = 'unavailable'
            monitor.write_report(target, report)
            self.assertEqual(json.loads(target.read_bytes())['status'], 'unavailable')
            target.write_bytes(b'operator-owned-data')
            with self.assertRaises(monitor.MonitorError):
                monitor.write_report(target, report)
            self.assertEqual(target.read_bytes(), b'operator-owned-data')

    def test_cli_failures_have_sanitized_output_and_distinct_exit_codes(self):
        for arguments in (['check', '--origin', 'https://user:secret@api.novamind-it.ru'], ['check', '--secret-value']):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = monitor.main(arguments)
            self.assertEqual(code, 2)
            self.assertNotIn('secret', output.getvalue())
        with patch.object(monitor, '_opener', return_value=Opener()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(monitor.main(['check', '--origin', ORIGIN]), 0)
        with patch.object(monitor, '_opener', return_value=Opener({'/healthz': urllib.error.URLError('secret')})), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(monitor.main(['check', '--origin', ORIGIN]), 1)

    def test_bounded_incident_log_records_failures_recovery_and_skips_healthy_repeats(self):
        with tempfile.TemporaryDirectory() as temporary:
            events = Path(temporary) / 'events.jsonl'
            report = monitor.check(ORIGIN, opener=Opener())
            monitor.append_event(events, report)
            monitor.append_event(events, report)
            self.assertEqual(len(events.read_bytes().splitlines()), 1)
            report['status'] = 'unavailable'
            report['checks'][0].update(ok=False, code='network_timeout')
            monitor.append_event(events, report)
            monitor.append_event(events, report)
            report['status'] = 'healthy'
            report['checks'][0].update(ok=True, code='ok')
            monitor.append_event(events, report)
            items = [json.loads(line) for line in events.read_bytes().splitlines()]
            self.assertEqual([item['status'] for item in items], ['healthy', 'unavailable', 'unavailable', 'healthy'])
            self.assertEqual(items[1]['failedChecks'][0]['code'], 'network_timeout')
            self.assertEqual(items[-1]['failedChecks'], [])

    def test_incident_log_rotates_four_bounded_files_and_rejects_unknown_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            events = Path(temporary) / 'events.jsonl'
            report = monitor.check(ORIGIN, opener=Opener())
            report['status'] = 'unavailable'
            report['checks'][0].update(ok=False, code='network_timeout')
            with patch.object(monitor, 'MAX_EVENTS_BYTES', 1024):
                for _ in range(20):
                    monitor.append_event(events, report)
                files = list(Path(temporary).glob('events.jsonl*'))
                self.assertEqual(len(files), 4)
                self.assertTrue(all(file.stat().st_size <= 1024 for file in files))
                archive = Path(str(events) + '.3')
                archive.write_bytes(b'operator-owned-data')
                before = {file: file.read_bytes() for file in files}
                with self.assertRaises(monitor.MonitorError):
                    monitor.append_event(events, report)
                self.assertEqual(before, {file: file.read_bytes() for file in files})


if __name__ == '__main__':
    unittest.main()
