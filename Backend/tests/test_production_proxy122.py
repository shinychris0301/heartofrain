"""Real pinned Caddy adaptation and isolated loopback ingress; not live provider/TLS acceptance."""
import contextlib
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from hotr_backend.production_runtime122 import PROVIDER_NETWORKS

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / 'Release/Production122/operations/Caddyfile.production122.example'
CADDY = ROOT / '.verification-cache/WindowsVps/Tools/CaddyExpanded/caddy.exe'
CADDY_SHA = '5f93a9bd555f3aac9d33af2756ba14b3519d8cca4ffd55256bdaeab444c9db2a'


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


class ProductionProxy122Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name != 'nt' or not CADDY.is_file():
            raise unittest.SkipTest('Exact reviewed optional Windows Caddy binary unavailable; proxy execution unqualified.')
        if hashlib.sha256(CADDY.read_bytes()).hexdigest() != CADDY_SHA:
            raise RuntimeError('Reviewed Caddy binary hash mismatch')

    def test_actual_caddy_adaptation_preserves_peer_binding_and_sender_deny_order(self):
        result = subprocess.run([str(CADDY), 'adapt', '--config', str(TEMPLATE), '--adapter', 'caddyfile'],
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0)
        tree = json.loads(result.stdout)
        proxies = [node for node in nodes(tree) if node.get('handler') == 'reverse_proxy']
        self.assertEqual(len(proxies), 2)
        for proxy in proxies:
            self.assertEqual(proxy['upstreams'], [{'dial': '127.0.0.1:8752'}])
            headers = proxy['headers']['request']
            self.assertEqual({key.lower(): value for key, value in headers['set'].items()},
                             {'x-hotr-verified-client-ip': ['{http.request.remote.host}']})
            self.assertEqual(set(headers['delete']), {'Forwarded', 'X-Forwarded-For', 'X-Real-IP'})
        payment = next(node for node in nodes(tree) if any('/v1/commerce/notifications/rustore/production' in match.get('path', [])
                                                        for match in node.get('match', [])))
        ordered = payment['handle'][0]['routes']
        self.assertEqual(ordered[0]['handle'][0]['status_code'], 403)
        self.assertEqual(set(ordered[0]['match'][0]['not'][0]['remote_ip']['ranges']), set(PROVIDER_NETWORKS))
        self.assertEqual(ordered[1]['handle'][0]['status_code'], 405)
        self.assertEqual(ordered[2]['handle'][0]['handler'], 'reverse_proxy')
        self.assertNotIn('logging', tree['apps']['http']['servers']['srv0'])

    def test_actual_proxy_overwrites_spoofed_header_blocks_senders_and_keeps_drafts_static(self):
        observed = []

        class Backend(BaseHTTPRequestHandler):
            def do_GET(self):
                headers = {key.lower(): value for key, value in self.headers.items()}
                observed.append((self.path, headers))
                raw = b'{"status":"synthetic-upstream"}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args):
                pass

        with tempfile.TemporaryDirectory(prefix='hotr-caddy122-') as temporary, \
             ThreadingHTTPServer(('127.0.0.1', 0), Backend) as backend:
            base = Path(temporary)
            public = base / 'public'
            public.mkdir()
            for page in ('privacy', 'support', 'terms'):
                (public / (page + '.html')).write_text('Explicit draft fixture ' + page, encoding='utf-8')
            with socket.socket() as reserve:
                reserve.bind(('127.0.0.1', 0))
                port = reserve.getsockname()[1]
            source = TEMPLATE.read_text('utf-8')
            source = source.replace('api.novamind-it.ru {', 'http://127.0.0.1:' + str(port) + ' {')
            source = source.replace('127.0.0.1:8752', '127.0.0.1:' + str(backend.server_port))
            source = source.replace('C:/ProgramData/HeartOfTheRain/production-services/public', '"' + public.as_posix() + '"')
            config = base / 'Caddyfile'
            config.write_text('{\n admin off\n auto_https off\n}\n' + source, encoding='utf-8')
            thread = threading.Thread(target=backend.serve_forever, daemon=True)
            thread.start()
            process = subprocess.Popen([str(CADDY), 'run', '--config', str(config), '--adapter', 'caddyfile'],
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                deadline = time.monotonic() + 5
                while True:
                    try:
                        with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                            break
                    except OSError:
                        self.assertIsNone(process.poll())
                        self.assertLess(time.monotonic(), deadline)
                        time.sleep(0.03)
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                origin = 'http://127.0.0.1:' + str(port)
                request = urllib.request.Request(origin + '/probe', headers={
                    'X-Hotr-Verified-Client-IP': '95.163.133.1', 'X-Forwarded-For': '95.163.133.1',
                    'Forwarded': 'for=95.163.133.1', 'X-Real-IP': '95.163.133.1'})
                with opener.open(request, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                self.assertEqual(len(observed), 1)
                headers = observed[0][1]
                self.assertEqual(headers.get('x-hotr-verified-client-ip'), '127.0.0.1')
                self.assertNotIn('forwarded', headers)
                self.assertNotIn('x-forwarded-for', headers)
                self.assertNotIn('x-real-ip', headers)
                request = urllib.request.Request(origin + '/v1/commerce/notifications/rustore/production',
                    method='POST', data=b'{}', headers={'X-Hotr-Verified-Client-IP': '95.163.133.1',
                        'X-Forwarded-For': '95.163.133.1', 'Content-Type': 'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    opener.open(request, timeout=2)
                self.assertEqual(denied.exception.code, 403)
                denied.exception.close()
                for path in ('/internal/v1/test', '/docs', '/openapi.json', '/v1/commerce/notifications/rustore/sandbox'):
                    with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as blocked:
                        opener.open(origin + path, timeout=2)
                    self.assertEqual(blocked.exception.code, 404)
                    blocked.exception.close()
                for page in ('privacy', 'support', 'terms'):
                    with opener.open(origin + '/' + page, timeout=2) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.headers['Cache-Control'], 'no-store')
                        self.assertEqual(response.read(), ('Explicit draft fixture ' + page).encode())
                self.assertEqual(len(observed), 1)
            finally:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=5)
                backend.shutdown()
                thread.join(3)
                self.assertFalse(thread.is_alive())
            with self.assertRaises(OSError):
                socket.create_connection(('127.0.0.1', port), timeout=0.1)


if __name__ == '__main__':
    unittest.main()
