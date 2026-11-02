"""Read-only, credential-free availability monitor; also runs without the backend package.

Exit 0: every requested check passed; 1: a check failed; 2: invalid configuration.
This deliberately does not infer production/provider acceptance from green probes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import http.client
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

KIND = 'HeartOfTheRainMonitor122'
MAX_BODY = 4096
MAX_BACKUPS = 512
MAX_EVENTS_BYTES = 262144
EVENT_ARCHIVES = 3


class MonitorError(Exception):
    """Fixed code only; never include supplied paths, payloads or exceptions."""


def _need(condition, code):
    if not condition:
        raise MonitorError(code)


def _json(raw, maximum=16384):
    _need(type(raw) is bytes and 2 <= len(raw) <= maximum, 'invalid_json')

    def pairs(items):
        value = {}
        for key, item in items:
            _need(key not in value, 'invalid_json')
            value[key] = item
        return value

    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        _need(type(value) is dict, 'invalid_json')
        return value
    except (ValueError, UnicodeError, TypeError, RecursionError):
        raise MonitorError('invalid_json') from None


def _origin(raw):
    _need(type(raw) is str and len(raw) <= 512 and not any(c.isspace() or ord(c) < 32 for c in raw), 'invalid_https_origin')
    try:
        url = urllib.parse.urlsplit(raw)
        host = url.hostname or ''
        _need(url.scheme == 'https' and url.port in (None, 443) and not url.username and not url.password
              and not url.query and not url.fragment and url.path in ('', '/') and '.' in host
              and re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', host)
              and '..' not in host and not re.fullmatch(r'[0-9.]+', host), 'invalid_https_origin')
        host = host.lower()
        _need(not any(host == suffix or host.endswith('.' + suffix) for suffix in
                      ('example.com', 'example.net', 'example.org', 'example', 'invalid', 'test', 'local', 'localhost')),
              'invalid_https_origin')
        return 'https://' + host
    except ValueError:
        raise MonitorError('invalid_https_origin') from None


def _plain_path(raw, *, file_required=False):
    path = Path(raw)
    _need(path.is_absolute() and not str(path).startswith(('\\\\', '//')) and
          not any(ord(c) < 32 for c in str(path)), 'invalid_local_path')
    for entry in reversed((path, *path.parents)):
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        _need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
              'linked_path_rejected')
        _need(not stat.S_ISREG(info.st_mode) or info.st_nlink == 1, 'linked_path_rejected')
    if file_required:
        _need(path.is_file(), 'local_file_missing')
    return path


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def _opener():
    # Normal certificate/hostname verification; no ambient proxies or credentials.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect(),
                                      urllib.request.HTTPSHandler(context=ssl.create_default_context()))


def _probe(opener, base, target, name, path, *, mode, timeout, latency_ms, clock=time.monotonic):
    started = clock()
    result = {'target': target, 'check': name, 'ok': False, 'code': 'network_unavailable', 'httpStatus': None}
    request = urllib.request.Request(base + path, headers={'Accept': 'application/json', 'Accept-Encoding': 'identity',
                                                         'User-Agent': 'HeartOfTheRain-Monitor/122'})
    try:
        with opener.open(request, timeout=timeout) as response:
            result['httpStatus'] = response.status
            expected = 404 if name.startswith('private_') else 200
            if response.status != expected:
                result['code'] = 'unexpected_http_status'
            elif expected == 404:
                result.update(ok=True, code='ok')
            else:
                _need(response.headers.get('Content-Encoding', 'identity').lower() in ('', 'identity'), 'encoded_response_rejected')
                _need(response.headers.get_content_type() == 'application/json', 'unexpected_content_type')
                parts, size = [], 0
                while True:
                    _need(clock() - started <= timeout, 'response_deadline_exceeded')
                    block = response.read1(min(1024, MAX_BODY + 1 - size))
                    if not block:
                        break
                    parts.append(block)
                    size += len(block)
                    _need(size <= MAX_BODY, 'response_too_large')
                body = _json(b''.join(parts), MAX_BODY)
                if name == 'health':
                    valid = body.get('status') == 'ok' and body.get('mode') == mode and body.get('productionEnabled') is (mode == 'production')
                else:
                    valid = body.get('status') == 'ready'
                result.update(ok=valid, code='ok' if valid else 'unexpected_health_state')
    except urllib.error.HTTPError as error:
        result['httpStatus'] = error.code
        if name.startswith('private_') and error.code == 404:
            result.update(ok=True, code='ok')
        else:
            result['code'] = 'unexpected_http_status'
        error.close()
    except MonitorError as error:
        result['code'] = error.args[0]
    except (socket.timeout, TimeoutError):
        result['code'] = 'network_timeout'
    except (urllib.error.URLError, ssl.SSLError, OSError, http.client.HTTPException):
        # Exception strings and network response payloads are intentionally absent.
        result['code'] = 'network_unavailable'
    result['latencyMs'] = round(max(0, clock() - started) * 1000, 3)
    if result['ok'] and result['latencyMs'] > timeout * 1000:
        result.update(ok=False, code='response_deadline_exceeded')
    elif result['ok'] and result['latencyMs'] > latency_ms:
        result.update(ok=False, code='latency_budget_exceeded')
    return result


def _backup_check(manifest_path, origin, max_age_hours, min_free_mib, *, now=time.time):
    result = {'target': 'local_host', 'check': 'backup_freshness', 'ok': False, 'code': 'backup_unavailable',
              'snapshotIntegrityVerified': False, 'offHostCopyVerified': False}
    try:
        manifest_file = _plain_path(manifest_path, file_required=True)
        _need(manifest_file.stat().st_size <= 16384, 'backup_manifest_invalid')
        manifest = _json(manifest_file.read_bytes())
        _need(manifest.get('publicOrigin') == origin and manifest.get('mode') == 'staging', 'backup_manifest_mismatch')
        data = _plain_path(manifest['dataDirectory'])
        marker_path = _plain_path(data / '.hotr-staging105-owner.json', file_required=True)
        _need(marker_path.stat().st_size <= 16384, 'backup_ownership_invalid')
        marker = _json(marker_path.read_bytes())
        _need(marker.get('version') == 1 and marker.get('kind') == 'HeartOfTheRainStaging105'
              and marker.get('state') == 'Ready' and marker.get('dataDirectory') == str(data)
              and all(marker.get(key) == manifest.get(key) for key in ('publicOrigin', 'deploymentId', 'identityScope'))
              and type(marker.get('nonce')) is str and re.fullmatch(r'[a-f0-9]{32}', marker['nonce']), 'backup_ownership_invalid')
        folder = _plain_path(data / 'backups')
        _need(folder.is_dir(), 'backup_directory_missing')
        latest, invalid = None, 0
        # A bounded scan makes accidentally unbounded retention visible to operators.
        with os.scandir(folder) as entries:
            for count, entry in enumerate(entries, 1):
                _need(count <= MAX_BACKUPS * 2, 'backup_inventory_limit_exceeded')
                if not entry.name.endswith('.receipt.json'):
                    continue
                try:
                    receipt_path = _plain_path(Path(entry.path), file_required=True)
                    _need(receipt_path.stat().st_size <= MAX_BODY, 'backup_receipt_invalid')
                    proof = _json(receipt_path.read_bytes(), MAX_BODY)
                    name = entry.name[:-len('.receipt.json')]
                    _need(re.fullmatch(r'[A-Za-z0-9_-]{1,48}', name), 'backup_receipt_invalid')
                    _need(proof.get('version') == 1 and proof.get('kind') == 'HeartOfTheRainStagingBackup105'
                          and proof.get('state') == 'Ready' and proof.get('snapshotName') == name
                          and all(proof.get(key) == marker[key] for key in ('publicOrigin', 'deploymentId', 'identityScope', 'nonce'))
                          and type(proof.get('schemaVersion')) is int and proof['schemaVersion'] >= 1
                          and type(proof.get('bytes')) is int and proof['bytes'] > 0
                          and type(proof.get('sha256')) is str and re.fullmatch(r'[a-f0-9]{64}', proof['sha256']), 'backup_receipt_invalid')
                    snapshot = _plain_path(folder / (name + '.sqlite3'), file_required=True)
                    _need(snapshot.stat().st_size == proof['bytes'] and not any(os.path.lexists(str(snapshot) + suffix)
                          for suffix in ('-wal', '-shm', '-journal')), 'backup_snapshot_metadata_invalid')
                    stamp = min(receipt_path.stat().st_mtime, snapshot.stat().st_mtime)
                    _need(stamp <= now() + 60, 'backup_timestamp_invalid')
                    latest = stamp if latest is None else max(latest, stamp)
                except (MonitorError, OSError, KeyError, TypeError):
                    invalid += 1
        result['invalidReceiptCount'] = invalid
        _need(latest is not None, 'no_ready_backup')
        result['ageHours'] = round(max(0, now() - latest) / 3600, 3)
        _need(now() - latest <= max_age_hours * 3600, 'backup_stale')
        _need(invalid == 0, 'backup_inventory_needs_review')
        result.update(ok=True, code='ok')
        free = shutil.disk_usage(data).free / 1_048_576
        disk = {'target': 'local_host', 'check': 'disk_free', 'ok': free >= min_free_mib,
                'code': 'ok' if free >= min_free_mib else 'insufficient_disk_space', 'freeMiB': int(free)}
        return [result, disk]
    except MonitorError as error:
        result['code'] = error.args[0]
    except (OSError, KeyError, TypeError):
        result['code'] = 'backup_unavailable'
    return [result]


def check(origin, *, expected_mode='staging', loopback_port=None, timeout=3, latency_ms=2500,
          backup_manifest=None, max_backup_age_hours=24, min_free_mib=1024, opener=None):
    origin = _origin(origin)
    _need(expected_mode in ('staging', 'production'), 'invalid_expected_mode')
    for value, low, high in ((timeout, 0.25, 10), (latency_ms, 1, 10000), (max_backup_age_hours, 1, 720),
                             (min_free_mib, 1, 1_048_576)):
        _need(type(value) in (int, float) and math.isfinite(value) and low <= value <= high, 'invalid_monitor_limits')
    _need(loopback_port is None or type(loopback_port) is int and 1024 <= loopback_port <= 65535, 'invalid_loopback_port')
    opener = _opener() if opener is None else opener
    checks = []
    targets = [(origin, 'public_https')]
    if loopback_port is not None:
        targets.append(('http://127.0.0.1:' + str(loopback_port), 'loopback'))
    for base, target in targets:
        paths = [('health', '/healthz'), ('readiness', '/readyz')]
        if target == 'public_https':
            paths += [('private_docs', '/docs'), ('private_openapi', '/openapi.json'), ('private_internal', '/internal/v1/test')]
        for name, path in paths:
            checks.append(_probe(opener, base, target, name, path, mode=expected_mode,
                                 timeout=timeout, latency_ms=latency_ms))
    if backup_manifest is not None:
        checks += _backup_check(backup_manifest, origin, max_backup_age_hours, min_free_mib)
    return {'version': 1, 'kind': KIND, 'checkedAtUtc': datetime.now(timezone.utc).isoformat(),
            'status': 'healthy' if all(item['ok'] for item in checks) else 'unavailable',
            'expectedMode': expected_mode, 'productionAcceptanceVerified': False,
            'backupFreshnessChecked': backup_manifest is not None, 'checks': checks}


def write_report(path, report):
    """Replace only this monitor's own sanitized status file, in an existing private directory."""
    target = _plain_path(path)
    _need(target.parent.is_dir(), 'report_directory_missing')
    before = None
    if os.path.lexists(target):
        _need(target.is_file() and target.stat().st_size <= 65536, 'unknown_report_file')
        before = target.read_bytes()
        previous = _json(before, 65536)
        _need(previous.get('kind') == KIND and previous.get('version') == 1, 'unknown_report_file')
    temporary = target.parent / ('.monitor122-' + uuid.uuid4().hex + '.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'wb') as output:
        output.write((json.dumps(report, separators=(',', ':')) + '\n').encode('utf-8'))
        output.flush()
        os.fsync(output.fileno())
    _plain_path(target)
    _need(target.read_bytes() == before if before is not None else not os.path.lexists(target), 'report_changed_concurrently')
    os.replace(temporary, target)


def append_event(path, report):
    """Record initial state, every failure and recovery; retain four bounded owned JSONL files."""
    target = _plain_path(path)
    _need(target.parent.is_dir(), 'events_directory_missing')
    files = [target] + [Path(str(target) + '.' + str(index)) for index in range(1, EVENT_ARCHIVES + 1)]
    contents = {}
    for candidate in files:
        _plain_path(candidate)
        if not os.path.lexists(candidate):
            continue
        _need(candidate.is_file() and candidate.stat().st_size <= MAX_EVENTS_BYTES, 'unknown_events_file')
        raw = candidate.read_bytes()
        for line in raw.splitlines():
            item = _json(line, MAX_EVENTS_BYTES)
            _need(item.get('kind') == KIND and item.get('version') == 1 and
                  item.get('event') == 'availability_state', 'unknown_events_file')
        contents[candidate] = raw
    previous = contents.get(target, b'').splitlines()
    if report['status'] == 'healthy' and previous and _json(previous[-1], MAX_EVENTS_BYTES).get('status') == 'healthy':
        return
    failed = [{key: item[key] for key in ('target', 'check', 'code', 'httpStatus', 'latencyMs') if key in item}
              for item in report['checks'] if not item['ok']]
    event = {'version': 1, 'kind': KIND, 'event': 'availability_state', 'checkedAtUtc': report['checkedAtUtc'],
             'status': report['status'], 'failedChecks': failed, 'productionAcceptanceVerified': False}
    line = (json.dumps(event, separators=(',', ':')) + '\n').encode('utf-8')
    _need(len(line) <= MAX_EVENTS_BYTES, 'events_record_too_large')
    for candidate, before in contents.items():
        _need(candidate.read_bytes() == before, 'events_changed_concurrently')
    if len(contents.get(target, b'')) + len(line) > MAX_EVENTS_BYTES:
        if files[-1] in contents:
            files[-1].unlink()  # A single validated, owned, local file; no recursive deletion.
        for index in range(EVENT_ARCHIVES, 0, -1):
            if files[index - 1] in contents:
                os.replace(files[index - 1], files[index])
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'ab') as output:
        output.write(line)
        output.flush()
        os.fsync(output.fileno())


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise MonitorError('invalid_monitor_arguments')


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument('action', choices=['check'])
    parser.add_argument('--origin', required=True)
    parser.add_argument('--expected-mode', choices=['staging', 'production'], default='staging')
    parser.add_argument('--loopback-port', type=int)
    parser.add_argument('--timeout', type=float, default=3)
    parser.add_argument('--latency-ms', type=float, default=2500)
    parser.add_argument('--backup-manifest', type=Path)
    parser.add_argument('--max-backup-age-hours', type=float, default=24)
    parser.add_argument('--min-free-mib', type=float, default=1024)
    parser.add_argument('--report-file', type=Path)
    parser.add_argument('--events-file', type=Path)
    try:
        args = vars(parser.parse_args(argv))
        args.pop('action')
        destination = args.pop('report_file')
        events = args.pop('events_file')
        report = check(**args)
        if destination is not None:
            write_report(destination, report)
        if events is not None:
            append_event(events, report)
        print(json.dumps(report, separators=(',', ':')))
        return 0 if report['status'] == 'healthy' else 1
    except (MonitorError, OSError):
        print(json.dumps({'version': 1, 'kind': KIND, 'status': 'invalid_configuration', 'productionAcceptanceVerified': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
