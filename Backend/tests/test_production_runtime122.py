"""Actual owned SQLite/ASGI lifecycle with explicitly scripted provider/worker.

No live provider, deployment or real Unity replay-worker acceptance is claimed.
"""
import base64
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import secrets
import socket
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS

from hotr_backend import production_runtime122 as runtime
from hotr_backend.api import create_app
from tests.production_fixture122 import ProductionFixture122, CONFIG
from tests import test_identity as signed_identity


class ProductionRuntime122Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = ProductionFixture122()
        self.addCleanup(self.fixture.close)

    def open(self):
        app = self.enterContext(self.fixture.context())
        client = self.enterContext(self.fixture.client(app))
        return app, client

    def order(self, app, client, product='wellkeeper'):
        identity, headers = self.fixture.provision(app)
        response = client.post('/v1/commerce/orders', headers=headers,
            json={'commandId': uuid.uuid4().hex, 'productId': product})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json(), identity, headers

    def reconcile(self, client, order, headers, invoice):
        return client.post('/v1/commerce/orders/' + order['orderId'] + '/reconcile',
                           headers=headers, json={'invoiceId': invoice})

    def test_default_factory_still_rejects_ambient_production_before_database_creation(self):
        path = self.fixture.root / 'unowned.sqlite3'
        with patch.dict('os.environ', {'HOTR_BACKEND_MODE': 'production'}):
            with self.assertRaises(RuntimeError):
                create_app(path, CONFIG)
        self.assertFalse(path.exists())

    def test_forged_permit_and_missing_production_bindings_fail_before_database_creation(self):
        path = self.fixture.root / 'unowned.sqlite3'
        with self.assertRaises(RuntimeError):
            create_app(path, CONFIG, _production_permit122=object())
        self.assertFalse(path.exists())
        app, client = self.open()
        with self.assertRaises(RuntimeError):
            create_app(self.fixture.manifest.data_directory / runtime.DATABASE, CONFIG,
                       _production_permit122=app.state.production_permit122)
        self.assertEqual(client.get('/healthz').status_code, 200)

    def test_initializer_never_adopts_existing_directory_or_database(self):
        marker = (self.fixture.manifest.data_directory / runtime.MARKER).read_bytes()
        with self.assertRaises(runtime.ProductionError):
            runtime.initialize_owned_data(self.fixture.manifest)
        self.assertEqual((self.fixture.manifest.data_directory / runtime.MARKER).read_bytes(), marker)
        self.assertFalse((self.fixture.manifest.data_directory / runtime.DATABASE).exists())

    def test_staging_marker_cannot_be_relabelled_or_adopted(self):
        path = self.fixture.manifest.data_directory / runtime.MARKER
        original = path.read_bytes()
        value = json.loads(original)
        value['kind'] = 'HeartOfTheRainStaging105'
        path.write_text(json.dumps(value))
        with self.assertRaises(runtime.ProductionError):
            with self.fixture.context():
                self.fail('staging marker admitted')
        self.assertFalse((self.fixture.manifest.data_directory / runtime.DATABASE).exists())

    def test_manifest_is_immutable_and_rejects_foreign_fields_and_wide_sender_network(self):
        with self.assertRaises(FrozenInstanceError):
            self.fixture.manifest.port = 1
        value = self.fixture.manifest.raw
        value['port'] = 1
        self.assertNotEqual(self.fixture.manifest.raw['port'], 1)
        self.fixture.document['privateKey'] = 'synthetic-do-not-reflect'
        with self.assertRaises(runtime.ProductionError) as failure:
            self.fixture.write_manifest()
        self.assertNotIn('synthetic-do-not-reflect', str(failure.exception))
        del self.fixture.document['privateKey']
        self.fixture.document['provider']['allowedNetworks'] = ['0.0.0.0/0']
        with self.assertRaises(runtime.ProductionError):
            self.fixture.write_manifest()

    def test_repository_and_network_data_paths_are_rejected(self):
        for path in (str(CONFIG / 'authority'), r'\\server\share\authority'):
            with self.subTest(path_type='source' if path.startswith(str(CONFIG)) else 'network'):
                self.fixture.document['dataDirectory'] = path
                with self.assertRaises(runtime.ProductionError):
                    self.fixture.write_manifest()

    def test_bound_socket_failure_prevents_database_creation(self):
        with socket.socket() as foreign:
            foreign.bind(('127.0.0.1', self.fixture.manifest.port)); foreign.listen()
            with self.assertRaises(runtime.ProductionError):
                with self.fixture.context():
                    self.fail('foreign socket admitted')
        self.assertFalse((self.fixture.manifest.data_directory / runtime.DATABASE).exists())

    def test_duplicate_runtime_cannot_open_same_authority(self):
        app, client = self.open()
        with self.assertRaises(runtime.ProductionError):
            with self.fixture.context():
                self.fail('second runtime admitted')
        self.assertEqual(client.get('/healthz').json()['mode'], 'production')

    def test_commerce_hash_or_missing_secret_reference_fails_before_database_creation(self):
        self.fixture.catalog_path.write_text('{}')
        with self.assertRaises(runtime.ProductionError):
            with self.fixture.context():
                self.fail('changed catalogue admitted')
        self.assertFalse((self.fixture.manifest.data_directory / runtime.DATABASE).exists())
        self.fixture.catalog_path.write_text(json.dumps(self.fixture.catalog))
        (self.fixture.root / 'test-private-key-ref').unlink()
        with self.assertRaises(runtime.ProductionError):
            with self.fixture.context():
                self.fail('missing key reference admitted')
        self.assertFalse((self.fixture.manifest.data_directory / runtime.DATABASE).exists())

    def test_unapproved_worker_fails_before_database_creation_and_releases_socket(self):
        with patch('hotr_backend.production_runtime122._create_worker', side_effect=runtime.ProductionError('fixture_worker_rejected')):
            with self.assertRaises(runtime.ProductionError):
                with runtime.application_context(self.fixture.manifest):
                    self.fail('worker rejection ignored')
        self.assertFalse((self.fixture.manifest.data_directory / runtime.DATABASE).exists())
        with socket.socket() as check:
            check.bind(('127.0.0.1', self.fixture.manifest.port))

    def test_missing_ready_database_is_not_recreated(self):
        with self.fixture.context():
            pass
        path = self.fixture.manifest.data_directory / runtime.DATABASE
        path.unlink()
        with self.assertRaises(runtime.ProductionError):
            with self.fixture.context():
                self.fail('missing authority recreated')
        self.assertFalse(path.exists())

    def test_production_health_wallet_catalogue_and_pending_environment_agree(self):
        app, client = self.open()
        identity, headers = self.fixture.provision(app)
        self.assertEqual(client.get('/healthz').json(), {'status': 'ok', 'mode': 'production', 'productionEnabled': True})
        self.assertEqual(client.get('/readyz').status_code, 200)
        wallet = client.get('/v1/wallet', headers=headers).json()
        catalogue = client.get('/v1/commerce/catalog', headers=headers).json()
        pending = client.get('/v1/commerce/orders/pending', headers=headers).json()
        self.assertTrue(wallet['productionEnabled'])
        self.assertTrue(catalogue['productionEnabled'])
        self.assertTrue(catalogue['fullGameplayWallet'])
        self.assertTrue(catalogue['enabled'])
        self.assertFalse(catalogue['sandbox'])
        self.assertEqual(catalogue['appId'], 123)
        self.assertEqual(len(catalogue['products']), 12)
        self.assertTrue(pending['productionEnabled'])
        self.assertFalse(wallet['localProfileMutated'])
        self.assertFalse(wallet['normalUnityProfileIntegrated'])

    def test_production_guest_uses_real_device_signature_and_environment_flag(self):
        app, client = self.open()
        key = ECC.generate(curve='P-256')
        body = {'requestId': uuid.uuid4().hex, 'publicKey': signed_identity.public(key),
                'refreshToken': secrets.token_urlsafe(32), 'recoverySecret': secrets.token_urlsafe(32)}
        digest = signed_identity.digest(signed_identity.canonical(signed_identity.binding(body, 'guest')))
        response = client.post('/v1/identity/challenges', json={'purpose': 'guest',
            'requestId': body['requestId'], 'publicKey': body['publicKey'], 'payloadDigest': digest})
        self.assertEqual(response.status_code, 200, response.text)
        challenge = response.json()
        message = base64.b64decode(challenge['signingBytes'], validate=True)
        signature = DSS.new(key, 'fips-186-3', encoding='der').sign(SHA256.new(message))
        response = client.post('/v1/identity/guest', json={**body,
            'challengeId': challenge['challengeId'], 'signature': base64.b64encode(signature).decode()})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['productionEnabled'])
        self.assertFalse(response.json()['normalUnityProfileIntegrated'])

    def test_forwarded_header_cannot_replace_verified_proxy_peer_or_client_address(self):
        app, client = self.open()
        with self.fixture.client(app, peer='198.51.100.30') as direct:
            value = direct.post('/v1/identity/challenges', json={'purpose': 'guest',
                'requestId': uuid.uuid4().hex, 'publicKey': signed_identity.public(ECC.generate(curve='P-256')),
                'payloadDigest': 'a' * 64}, headers={'X-Hotr-Verified-Client-IP': '95.163.133.1'})
            self.assertEqual(value.status_code, 403)
        client.headers.pop('X-Hotr-Verified-Client-IP')
        value = client.post('/v1/commerce/notifications/rustore/production', json={},
                            headers={'X-Forwarded-For': '95.163.133.1'})
        self.assertEqual(value.status_code, 403)

    def test_wellkeeper_full_grant_credits_once_and_rejects_sandbox_or_deleted_sku(self):
        app, client = self.open()
        order, identity, headers = self.order(app, client)
        before = client.get('/v1/wallet', headers=headers).json()
        self.assertTrue(order['productionEnabled'])
        self.assertFalse(order['sdk']['sandbox'])
        self.assertEqual(order['sdk']['productId'], 'hotr_bundle_wellkeeper_c')
        invoice = self.fixture.invoice(order, sandbox=True)
        self.assertEqual(self.reconcile(client, order, headers, invoice).status_code, 409)
        self.fixture.provider.values[invoice] = replace(self.fixture.provider.values[invoice], sandbox=False,
                                                       product_id='hotr_bundle_wellkeeper')
        self.assertEqual(self.reconcile(client, order, headers, invoice).status_code, 409)
        self.fixture.provider.values[invoice] = replace(self.fixture.provider.values[invoice], product_id='hotr_bundle_wellkeeper_c')
        for _ in range(2):
            response = self.reconcile(client, order, headers, invoice)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()['productionEnabled'])
        after = client.get('/v1/wallet', headers=headers).json()
        self.assertEqual(after['coins'], before['coins'] + 2000)
        self.assertEqual(after['starting'], [v + 1 for v in before['starting']])
        self.assertEqual(after['tools'], [v + 1 for v in before['tools']])
        with app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 1)

    def test_held_production_invoice_never_credits_and_confirmed_refund_stays_quarantined(self):
        app, client = self.open()
        order, identity, headers = self.order(app, client)
        invoice = self.fixture.invoice(order, status='PAID')
        held = self.reconcile(client, order, headers, invoice)
        self.assertEqual(held.json()['state'], 'Held')
        self.assertIsNone(held.json()['credit'])
        self.fixture.provider.values[invoice] = replace(self.fixture.provider.values[invoice], status='CONFIRMED')
        self.assertEqual(self.reconcile(client, order, headers, invoice).json()['state'], 'Confirmed')
        self.fixture.provider.values[invoice] = replace(self.fixture.provider.values[invoice], status='REFUNDED')
        self.assertEqual(self.reconcile(client, order, headers, invoice).json()['state'], 'RefundReview')
        wallet = client.get('/v1/wallet', headers=headers).json()
        self.assertTrue(wallet['refundReviewRequired'])
        with app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 1)

    def test_production_pending_recovery_survives_owned_runtime_restart(self):
        with self.fixture.context() as app, self.fixture.client(app) as client:
            order, identity, headers = self.order(app, client)
            invoice = self.fixture.invoice(order)
            self.assertEqual(self.reconcile(client, order, headers, invoice).status_code, 200)
        with self.fixture.context() as app, self.fixture.client(app) as client:
            pending = client.get('/v1/commerce/orders/pending', headers=headers).json()
            self.assertTrue(pending['productionEnabled'])
            self.assertEqual(pending['orders'][0]['orderId'], order['orderId'])
            self.assertFalse(pending['orders'][0]['sdk']['sandbox'])
            self.assertEqual(self.reconcile(client, order, headers, invoice).status_code, 200)
            self.assertEqual(client.get('/v1/wallet', headers=headers).json()['coins'], 3250)

    def test_notification_requires_verified_source_and_authenticated_live_payload_before_queue(self):
        app, client = self.open()
        order, identity, headers = self.order(app, client)
        invoice = self.fixture.invoice(order)
        value = self.fixture.provider.values[invoice]
        key = secrets.token_bytes(32)
        (self.fixture.root / 'test-notification-key-ref').write_text(base64.b64encode(key).decode())
        body = {'product_code': value.product_id, 'change_status_time': '2026-10-30T12:00:00Z',
                'status_old': 'EXECUTED', 'status_new': 'CONFIRMED', 'purchase_token': 'explicit-scripted-token',
                'invoice_id': invoice, 'order_id': order['orderId'], 'purchase_id': value.purchase_id,
                'developer_payload': value.developer_payload}
        payload = {'app_id': 123, 'notification_type': 'INVOICE_STATUS', 'data': json.dumps(body)}
        cipher = AES.new(key, AES.MODE_GCM, nonce=secrets.token_bytes(12), mac_len=16)
        encrypted, tag = cipher.encrypt_and_digest(json.dumps(payload).encode())
        wire = {'id': uuid.uuid4().hex, 'timestamp': '2026-10-30T12:00:01Z',
                'payload': base64.b64encode(cipher.nonce + encrypted + tag).decode()}
        self.assertEqual(client.post('/v1/commerce/notifications/rustore/production', json=wire).status_code, 403)
        response = client.post('/v1/commerce/notifications/rustore/production', json=wire,
                               headers={'X-Hotr-Verified-Client-IP': '95.163.133.1'})
        self.assertEqual(response.status_code, 200, response.text)
        with app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_reconcile_jobs').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 0)
            self.assertNotIn('explicit-scripted-token', '\n'.join(db.iterdump()))
        self.assertEqual(client.post('/v1/commerce/notifications/rustore/sandbox', json=wire,
            headers={'X-Hotr-Verified-Client-IP': '95.163.133.1'}).status_code, 503)

    def test_disabled_ads_cannot_be_enabled_by_repository_or_ambient_setting(self):
        with patch.dict('os.environ', {'HOTR_MANAGED_IDENTITY_ENABLED': '0', 'HOTR_SOCIAL_ENABLED': '0',
                                     'HOTR_VK_ID_ENABLED': '1', 'HOTR_RUSTORE_NOTIFICATIONS_ENABLED': '0'}):
            app, client = self.open()
        identity, headers = self.fixture.provision(app)
        ads = client.get('/v1/ads/rewarded/status', headers=headers).json()
        self.assertTrue(ads['productionEnabled'])
        self.assertFalse(ads['enabled'])
        self.assertFalse(ads['available'])
        self.assertTrue(app.state.identity.enabled)
        self.assertFalse(app.state.provider_identity.configuration.enabled)

    def test_enabled_ads_require_explicit_capped_policy_and_retains_trust_label(self):
        with ProductionFixture122(ads_enabled=True) as fixture:
            with fixture.context() as app, fixture.client(app) as client:
                identity, headers = fixture.provision(app)
                value = client.get('/v1/ads/rewarded/status', headers=headers).json()
                self.assertTrue(value['productionEnabled'])
                self.assertTrue(value['enabled'])
                self.assertEqual(value['verificationMode'], 'sdk_client_reported_capped')
                self.assertEqual((value['rewardCoins'], value['dailyLimit'], value['cooldownSeconds']), (400, 3, 600))

    def test_context_close_blocks_retained_app_and_releases_listener(self):
        context = self.fixture.context()
        app = context.__enter__()
        with self.fixture.client(app) as client:
            self.assertEqual(client.get('/healthz').status_code, 200)
            context.__exit__(None, None, None)
            self.assertEqual(client.get('/healthz').status_code, 503)
            with socket.socket() as check:
                check.bind(('127.0.0.1', self.fixture.manifest.port))

    def test_owner_metadata_change_fences_retained_app(self):
        app, client = self.open()
        path = self.fixture.manifest.data_directory / runtime.MARKER
        value = json.loads(path.read_bytes())
        value['nonce'] = uuid.uuid4().hex
        path.write_text(json.dumps(value))
        self.assertEqual(client.get('/healthz').status_code, 503)

    def test_verified_gameplay_flags_match_production_and_upstream_bypass_stays_disabled(self):
        app, client = self.open()
        identity, headers = self.fixture.provision(app)
        wallet = client.get('/v1/wallet', headers=headers).json()
        reserved = client.post('/v1/attempts/reserve', headers=headers, json={
            'commandId': uuid.uuid4().hex, 'expectedRevision': wallet['revision'],
            'level': 1, 'starting': [0, 0, 0, 0]})
        self.assertEqual(reserved.status_code, 200, reserved.text)
        value = reserved.json()
        attempt = value['attempt']['attemptId']
        started = client.post('/v1/attempts/' + attempt + '/start', headers=headers, json={
            'commandId': uuid.uuid4().hex, 'expectedRevision': value['wallet']['revision']})
        self.assertEqual(started.status_code, 200, started.text)
        request = {'commandId': uuid.uuid4().hex, 'expectedPrefixRevision': 0,
                   'actions': [{'index': 0, 'kind': 'Swap', 'x': 1, 'y': 1, 'toX': 1, 'toY': 2}]}
        result = client.post('/v1/gameplay/attempts/' + attempt + '/verify', headers=headers, json=request)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertTrue(result.json()['productionEnabled'])
        self.assertTrue(result.json()['wallet']['productionEnabled'])
        self.assertEqual(result.json()['state'], 'Committed')
        self.assertEqual(len(self.fixture.worker.calls), 1)
        verifier = app.state.authority.provision(role='verifier')
        blocked = client.post('/internal/v1/verified-first-clear',
            headers={'Authorization': 'Bearer ' + verifier['token']},
            json={'attemptId': attempt, 'level': 1, 'proofDigest': 'a' * 64})
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()['error'], 'use_verified_gameplay')

    def test_shutdown_retains_runtime_lock_and_socket_until_inflight_credit_finishes(self):
        context = self.fixture.context()
        app = context.__enter__()
        entered, release, closed = threading.Event(), threading.Event(), threading.Event()
        errors, replies = [], []
        with self.fixture.client(app) as client:
            order, identity, headers = self.order(app, client)
            invoice = self.fixture.invoice(order)
        original = self.fixture.provider.lookup
        def blocked_lookup(number, sandbox):
            entered.set()
            if not release.wait(10):
                raise RuntimeError('explicit-scripted-test-release-timeout')
            return original(number, sandbox)
        def request():
            try:
                with self.fixture.client(app) as client:
                    replies.append(self.reconcile(client, order, headers, invoice))
            except BaseException as error:
                errors.append(type(error).__name__)
        def close():
            try:
                context.__exit__(None, None, None)
            except BaseException as error:
                errors.append(type(error).__name__)
            finally:
                closed.set()
        with patch.object(self.fixture.provider, 'lookup', side_effect=blocked_lookup):
            worker = threading.Thread(target=request)
            worker.start()
            self.assertTrue(entered.wait(5))
            closer = threading.Thread(target=close)
            closer.start()
            try:
                self.assertFalse(closed.wait(0.1))
                with self.fixture.client(app) as client:
                    self.assertEqual(client.get('/healthz').status_code, 503)
                with socket.socket() as check:
                    with self.assertRaises(OSError):
                        check.bind(('127.0.0.1', self.fixture.manifest.port))
                with self.assertRaises(runtime.ProductionError):
                    with runtime._lock(self.fixture.manifest, runtime.RUNTIME_LOCK):
                        self.fail('runtime lock released during pending credit')
            finally:
                release.set()
                worker.join(5); closer.join(5)
        self.assertTrue(closed.is_set())
        self.assertEqual(errors, [])
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0].status_code, 200)
        with app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 1)
        with socket.socket() as check:
            check.bind(('127.0.0.1', self.fixture.manifest.port))


if __name__ == '__main__':
    unittest.main()
