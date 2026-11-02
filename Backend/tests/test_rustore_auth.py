import base64
import concurrent.futures
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

import httpx
from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

from hotr_backend.rustore_auth import RuStoreTokenSupplier
from hotr_backend.rustore_provider import ProviderUnavailable


class RuStoreAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generated only in this test process; never a fixture/signing asset.
        cls.key = RSA.generate(2048)
        cls.private = base64.b64encode(cls.key.export_key(format='DER', pkcs=8))

    def supplier(self, handler, source=None, mono=None):
        return RuStoreTokenSupplier('123456', source or (lambda: self.private),
            transport=httpx.MockTransport(handler), monotonic=mono,
            utc_clock=lambda: dt.datetime(2026, 10, 25, 12, 34, 56, 123456, tzinfo=dt.timezone.utc))

    @staticmethod
    def ok(token='test.header.iv.cipher.tag', ttl=900):
        return httpx.Response(200, json={'code': 'OK', 'body': {'jwe': token, 'ttl': ttl}})

    def test_official_signature_and_fixed_origin(self):
        calls = []

        def server(request):
            self.assertEqual(str(request.url), 'https://public-api-m.rustore.ru/public/auth/')
            self.assertEqual(request.method, 'POST')
            self.assertEqual(request.headers['Accept-Encoding'], 'identity')
            value = json.loads(request.content)
            self.assertEqual(set(value), {'keyId', 'timestamp', 'signature'})
            self.assertEqual(value['timestamp'], '2026-10-25T12:34:56.123+00:00')
            pkcs1_15.new(self.key.public_key()).verify(SHA512.new((value['keyId'] + value['timestamp']).encode()),
                                                    base64.b64decode(value['signature']))
            self.assertNotIn(self.private.decode(), request.content.decode())
            calls.append(value['keyId'])
            return self.ok()

        self.assertEqual(self.supplier(server)(), 'test.header.iv.cipher.tag')
        self.assertEqual(calls, ['123456'])

    def test_monotonic_cache_and_early_expiry(self):
        clock, calls = [0.0], []
        def server(_):
            calls.append(1)
            return self.ok('test.header.iv.cipher.' + ('one' if len(calls) == 1 else 'two'))
        supplier = self.supplier(server, mono=lambda: clock[0])
        first = supplier()
        clock[0] = 869
        self.assertEqual(supplier(), first)
        clock[0] = 870
        self.assertNotEqual(supplier(), first)
        self.assertEqual(len(calls), 2)

    def test_failed_refresh_never_uses_old_token(self):
        clock, calls = [0.0], []
        def server(_):
            calls.append(1)
            return httpx.Response(503) if len(calls) == 2 else self.ok()
        supplier = self.supplier(server, mono=lambda: clock[0])
        supplier()
        clock[0] = 900
        with self.assertRaisesRegex(ProviderUnavailable, '^rustore_auth_unavailable$'):
            supplier()
        supplier()
        self.assertEqual(len(calls), 3)

    def test_concurrent_calls_share_one_refresh(self):
        calls = []
        def server(_):
            calls.append(1)
            return self.ok()
        supplier = self.supplier(server)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(len(set(pool.map(lambda _: supplier(), range(16)))), 1)
        self.assertEqual(len(calls), 1)

    def test_invalidation_and_file_rotation(self):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'ephemeral-only.key'
            file.write_bytes(self.private)
            supplier = RuStoreTokenSupplier.from_file('123456', file,
                transport=httpx.MockTransport(lambda _: (calls.append(1), self.ok())[1]))
            supplier()
            file.write_bytes(b'invalid-ephemeral-rotation')
            supplier.invalidate()
            with self.assertRaises(ProviderUnavailable): supplier()
            self.assertEqual(len(calls), 1)
            file.write_bytes(self.private)
            supplier()
            self.assertEqual(len(calls), 2)

    def test_untrusted_response_shapes_are_rejected(self):
        cases = [b'[]', b'null', b'{"code":"OK","code":"ERROR"}',
                 b'{"code":"OK","body":{"jwe":"x","ttl":NaN}}']
        for content in cases:
            with self.subTest(contentKind=len(content)):
                supplier = self.supplier(lambda _, value=content: httpx.Response(200, content=value))
                with self.assertRaises(ProviderUnavailable): supplier()
        for token, ttl in [('a\r\nb', 900), ('', 900), ('x', True), ('x', 0), ('x', 901), ('x' * 16385, 900)]:
            with self.subTest(ttlType=type(ttl).__name__, tokenLength=len(token)):
                with self.assertRaises(ProviderUnavailable): self.supplier(lambda _: self.ok(token, ttl))()

    def test_redirect_oversize_and_transport_errors_are_sanitized(self):
        for response in [httpx.Response(302, headers={'Location': 'https://never-follow.invalid'}),
                         httpx.Response(200, content=b' ' * 65537)]:
            with self.assertRaisesRegex(ProviderUnavailable, '^rustore_auth_unavailable$'):
                self.supplier(lambda _: response)()
        def server(_): raise httpx.ConnectError('must-not-escape-test-secret')
        with self.assertRaises(ProviderUnavailable) as raised: self.supplier(server)()
        self.assertNotIn('must-not-escape', str(raised.exception))

    def test_public_invalid_weak_and_oversize_keys_never_send(self):
        calls = []
        for raw in (b'invalid', base64.b64encode(self.key.public_key().export_key(format='DER')),
                    RSA.generate(1024).export_key(), b'x' * 16385):
            with self.subTest(length=len(raw)):
                with self.assertRaises(ProviderUnavailable):
                    self.supplier(lambda _: (calls.append(1), self.ok())[1], source=lambda value=raw: value)()
        self.assertFalse(calls)

    def test_secret_source_exception_is_not_exposed(self):
        def source(): raise OSError('private-secret-path-must-not-escape')
        supplier = self.supplier(lambda _: self.ok(), source=source)
        with self.assertRaisesRegex(ProviderUnavailable, '^rustore_auth_unavailable$'): supplier()
        self.assertEqual(repr(supplier), '<RuStoreTokenSupplier server-only>')

    def test_naive_clock_and_slow_expired_auth_do_not_cache(self):
        clock = [0.0]
        def server(_):
            clock[0] = 1000
            return self.ok()
        supplier = self.supplier(server, mono=lambda: clock[0])
        with self.assertRaises(ProviderUnavailable): supplier()
        supplier = RuStoreTokenSupplier('123456', lambda: self.private,
            transport=httpx.MockTransport(lambda _: self.ok()), utc_clock=lambda: dt.datetime(2026, 1, 1))
        with self.assertRaises(ProviderUnavailable): supplier()

    def test_invalid_key_identifier_is_rejected(self):
        for value in (None, '', 'bad\r\nkey', 'bad key', 'x' * 129):
            with self.assertRaises(ValueError): RuStoreTokenSupplier(value, lambda: self.private)
