"""Actual ASGI/SQLite request validation and bounded receive lifecycle.

No provider request, payment, Unity execution or production acceptance.
"""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from hotr_backend.api import BoundedBody, MAX_BODY, create_app


class HttpJson86Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='hotr-http86-')
        self.app = create_app(Path(self.temporary.name) / 'authority.sqlite3', social_enabled=True)
        self.identity = self.app.state.authority.provision()
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.identity['token']}
        self.client.get('/v1/profile', headers=self.headers)

    def tearDown(self):
        self.client.close()
        self.temporary.cleanup()

    def state(self):
        with self.app.state.authority.database.connect() as db:
            return {table: [dict(row) for row in db.execute('SELECT * FROM ' + table)]
                    for table in ('wallets', 'wallet_ledger', 'commands', 'social_profiles')}

    def test_01_duplicate_fields_never_mutate_profile_or_commands(self):
        before = self.state()
        body = '{"commandId":"' + '1' * 32 + '","displayName":"First","displayName":"Second"}'
        response = self.client.post('/v1/profile/name', content=body, headers=self.headers)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {'error': 'invalid_request'})
        self.assertEqual(self.state(), before)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_02_utf16_and_invalid_utf8_fail_without_mutation_or_body_echo(self):
        before = self.state()
        body = '{"commandId":"' + '2' * 32 + '","displayName":"PrivateFixtureMarker"}'
        for value in (body.encode('utf-16'), b'{"displayName":"\xffPrivateFixtureMarker"}'):
            response = self.client.post('/v1/profile/name', content=value, headers=self.headers)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {'error': 'invalid_request'})
            self.assertNotIn('PrivateFixtureMarker', response.text)
            self.assertEqual(self.state(), before)

    def test_03_normal_utf8_cyrillic_and_exact_retry_still_succeed(self):
        value = {'commandId': '3' * 32, 'displayName': '\u041c\u0438\u043b\u0430'}
        body = json.dumps(value, ensure_ascii=False).encode('utf-8')
        first = self.client.post('/v1/profile/name', content=body, headers=self.headers)
        self.assertEqual(first.status_code, 200)
        before = self.state()
        again = self.client.post('/v1/profile/name', content=body, headers=self.headers)
        self.assertEqual(again.json(), first.json())
        self.assertEqual(self.state(), before)


class HttpBody86Tests(unittest.IsolatedAsyncioTestCase):
    async def call(self, chunks, *, timeout=0.05, receive_delay=0, downstream_delay=0, send_delay=0,
                   headers=None, scope_type='http'):
        output, received, called = [], [], []
        messages = list(chunks)

        async def receive():
            if receive_delay:
                await asyncio.sleep(receive_delay)
            return messages.pop(0) if messages else {'type': 'http.disconnect'}

        async def send(message):
            if send_delay:
                await asyncio.sleep(send_delay)
            output.append(message)

        async def downstream(scope, receive, send):
            called.append(scope['type'])
            if downstream_delay:
                await asyncio.sleep(downstream_delay)
            if scope['type'] == 'http':
                received.append(await receive())
                await send({'type': 'http.response.start', 'status': 204, 'headers': []})
                await send({'type': 'http.response.body', 'body': b''})

        scope = {'type': scope_type, 'method': 'POST', 'path': '/fixture',
                 'headers': headers if headers is not None else [(b'content-type', b'application/json')]}
        await BoundedBody(downstream, body_timeout_seconds=timeout)(scope, receive, send)
        return output, received, called

    async def test_04_timeout_is_total_receive_budget_not_downstream_budget(self):
        output, _, called = await self.call([{'type': 'http.request', 'body': b'{}'}], receive_delay=0.1)
        self.assertEqual(output[0]['status'], 408)
        self.assertEqual(json.loads(output[1]['body']), {'error': 'request_body_timeout'})
        self.assertEqual(called, [])
        output, received, called = await self.call([{'type': 'http.request', 'body': b'{}'}], downstream_delay=0.1)
        self.assertEqual(output[0]['status'], 204)
        self.assertEqual(received[0]['body'], b'{}')

    async def test_05_slow_chunks_do_not_reset_total_deadline(self):
        chunks = [{'type': 'http.request', 'body': b' ', 'more_body': True} for _ in range(10)]
        output, _, called = await self.call(chunks, receive_delay=0.02)
        self.assertEqual(output[0]['status'], 408)
        self.assertEqual(called, [])

    async def test_06_cap_is_enforced_for_one_chunk_and_for_streaming(self):
        for chunks in ([{'type': 'http.request', 'body': b'x' * (MAX_BODY + 1)}],
                       [{'type': 'http.request', 'body': b'x' * MAX_BODY, 'more_body': True},
                        {'type': 'http.request', 'body': b'x'}]):
            output, _, called = await self.call(chunks)
            self.assertEqual(output[0]['status'], 413)
            self.assertEqual(called, [])

    async def test_07_exact_byte_boundary_and_chunk_reassembly_are_preserved(self):
        body = b'{"value":"' + b'x' * (MAX_BODY - 12) + b'"}'
        self.assertEqual(len(body), MAX_BODY)
        output, received, called = await self.call([
            {'type': 'http.request', 'body': body[:100], 'more_body': True},
            {'type': 'http.request', 'body': body[100:]}])
        self.assertEqual(output[0]['status'], 204)
        self.assertEqual(received[0]['body'], body)

    async def test_08_nested_escaped_duplicate_nonfinite_and_deep_json_fail_closed(self):
        for body in (b'{"a":{"x":1,"x":2}}', b'{"a":1,"\\u0061":2}',
                     b'{"n":NaN}', b'{"n":Infinity}', b'{"n":1e999}',
                     b'[' * 80 + b'0' + b']' * 80, b'{"x":"\\ud800"}', b'{"broken":'):
            output, _, called = await self.call([{'type': 'http.request', 'body': body}])
            self.assertEqual(output[0]['status'], 422)
            self.assertEqual(json.loads(output[1]['body']), {'error': 'invalid_request'})
            self.assertEqual(called, [])

    async def test_09_strings_are_not_mistaken_for_structural_depth(self):
        body = json.dumps({'text': '[' * 100 + '\\"' + ']' * 100, 'a': {'x': 1}, 'b': {'x': 2}}).encode()
        output, received, _ = await self.call([{'type': 'http.request', 'body': body}])
        self.assertEqual(output[0]['status'], 204)
        self.assertEqual(received[0]['body'], body)

    async def test_10_disconnect_never_calls_handler(self):
        output, _, called = await self.call([{'type': 'http.disconnect'}])
        self.assertEqual((output, called), ([], []))

    async def test_11_non_http_and_non_json_scope_keep_existing_behavior(self):
        _, _, called = await self.call([], scope_type='websocket')
        self.assertEqual(called, ['websocket'])
        output, received, _ = await self.call([{'type': 'http.request', 'body': b'opaque'}],
                                              headers=[(b'content-type', b'text/plain')])
        self.assertEqual(output[0]['status'], 204)
        self.assertEqual(received[0]['body'], b'opaque')

    async def test_12_json_suffix_and_missing_type_are_validated_too(self):
        for headers in ([], [(b'content-type', b'application/vnd.fixture+json; charset=utf-8')]):
            output, _, called = await self.call([{'type': 'http.request', 'body': b'{"a":1,"a":2}'}], headers=headers)
            self.assertEqual(output[0]['status'], 422)
            self.assertEqual(called, [])

    async def test_13_slow_error_response_does_not_change_a_completed_receive_result(self):
        output, _, called = await self.call([{'type': 'http.request', 'body': b'x' * (MAX_BODY + 1)}], send_delay=0.1)
        self.assertEqual(output[0]['status'], 413)
        self.assertEqual(json.loads(output[1]['body']), {'error': 'body_too_large'})
        self.assertEqual(len(output), 2)
        self.assertEqual(called, [])


if __name__ == '__main__':
    unittest.main()
