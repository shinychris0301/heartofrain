"""Client-reported SDK trust tests; no store-provider/Android acceptance claim."""
import concurrent.futures
from contextlib import closing
import copy
import hashlib
import json
import sqlite3
import threading
import unittest
import uuid
from unittest.mock import patch

from hotr_backend import production_runtime122 as runtime
from hotr_backend.api import create_app
from hotr_backend.commerce_schemas import CreateCommerceOrder
from hotr_backend.sdk_commerce_schemas125 import SdkPurchaseReport125
from hotr_backend.sdk_schema125 import validate_sdk_database
from hotr_backend.service import Actor, ServiceError
from hotr_backend.storage import Database
from production_fixture122 import ProductionFixture122, CONFIG
from sdk_fixture125 import SdkProductionFixture125

class SdkCommerce125Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = SdkProductionFixture125()
        self.addCleanup(self.fixture.close)
        self.context = self.fixture.context()
        self.app = self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)
        self.identity, self.headers = self.fixture.provision(self.app)
        self.client = self.fixture.client(self.app)
        self.addCleanup(self.client.close)

    def create(self, product='wellkeeper', headers=None, command=None):
        response = self.client.post('/v1/commerce/orders', json={
            'commandId': command or uuid.uuid4().hex, 'productId': product},
            headers=headers or self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def report(self, order, observation=None, headers=None):
        return self.client.post('/v1/commerce/orders/' + order['orderId'] + '/sdk-report',
            json=observation or self.fixture.observation(order), headers=headers or self.headers)

    def wallet(self):
        response = self.client.get('/v1/wallet', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def count(self, sql):
        with self.app.state.authority.database.connect() as db:
            return db.execute(sql).fetchone()[0]

    def test_01_owned_live_sdk_runtime_uses_no_rsa_supplier_or_key_files(self):
        self.assertFalse((self.fixture.root / 'test-private-key-ref').exists())
        self.assertFalse(self.app.state.commerce.provider.configured)
        self.assertFalse(self.app.state.notifications.enabled)
        with closing(sqlite3.connect(self.app.state.authority.database.path)) as db:
            self.assertEqual(validate_sdk_database(db), 125)
        catalog = self.client.get('/v1/commerce/catalog', headers=self.headers).json()
        self.assertTrue(catalog['enabled'])
        self.assertEqual(catalog['verificationMode'], 'sdk_client_reported')
        self.assertEqual(self.report(self.create()).status_code, 200)

    def test_02_full_grant_once_and_fresh_acknowledgement(self):
        before = self.wallet()
        order = self.create()
        observed = self.fixture.observation(order)
        first = self.report(order, observed)
        self.assertEqual(first.status_code, 200, first.text)
        receipt = first.json()
        self.assertEqual(receipt['verificationMode'], 'sdk_client_reported')
        self.assertEqual(receipt['credit']['verificationMode'], 'sdk_client_reported')
        self.assertTrue(receipt['credit']['receiptId'].startswith('rustore-sdk/'))
        self.assertEqual(receipt['deliveryAcknowledgement'], 'Pending')
        after = self.wallet()
        self.assertEqual(after['coins'], before['coins'] + 2000)
        self.assertEqual(after['starting'], [value + 1 for value in before['starting']])
        self.assertEqual(after['tools'], [value + 1 for value in before['tools']])
        self.assertEqual((after['stars'], after['lives']), (before['stars'], before['lives']))
        for _ in range(3):
            self.assertEqual(self.report(order, observed).status_code, 200)
        self.assertEqual(self.wallet(), after)
        acknowledged = self.report(order, observed | {'acknowledgementState': 'ACKNOWLEDGED'}).json()
        self.assertEqual(acknowledged['deliveryAcknowledgement'], 'Acknowledged')
        stale = self.report(order, observed).json()
        self.assertEqual(stale['deliveryAcknowledgement'], 'Acknowledged')
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 1)
        self.assertEqual(self.count("SELECT COUNT(*) FROM wallet_ledger WHERE origin LIKE 'commerce/%'"), 1)
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_invoice_requests'), 0)

    def test_03_report_cannot_change_frozen_correlation_price_or_currency(self):
        order = self.create()
        observed = self.fixture.observation(order)
        for changes in ({'orderId': uuid.uuid4().hex}, {'productId': 'hotr_coins_1000'},
                        {'developerPayload': 'wrong'}, {'amountMinor': order['amountMinor'] + 1},
                        {'currency': 'USD'}, {'sandbox': True}):
            with self.subTest(fields=list(changes)):
                response = self.report(order, observed | changes)
                self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 0)
        self.assertEqual(self.report(order, observed).status_code, 200)

    def test_04_strict_sdk_contract_rejects_fabricated_extra_and_invalid_types(self):
        order = self.create()
        observed = self.fixture.observation(order)
        for changes in ({'grant': {'coins': 100000}}, {'appUserId': order['playerId']},
                        {'appId': 123}, {'quantity': True}, {'quantity': 2},
                        {'sandbox': 0}, {'amountMinor': True}, {'status': 'SUCCESS'},
                        {'productType': 'NON_CONSUMABLE_PRODUCT'},
                        {'acknowledgementState': 'NOT_ACKNOWLEDGED'},
                        {'purchaseId': observed['purchaseId'].upper()}):
            with self.subTest(fields=list(changes)):
                self.assertEqual(self.report(order, observed | changes).status_code, 422)
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 0)

    def test_05_account_switch_never_credits_new_player(self):
        order = self.create()
        _, other_headers = self.fixture.provision(self.app)
        response = self.report(order, headers=other_headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 0)
        self.assertEqual(self.report(order).status_code, 200)

    def test_06_same_invoice_or_purchase_cannot_replay_across_orders_players_or_products(self):
        order = self.create('coins-1000')
        observed = self.fixture.observation(order)
        self.assertEqual(self.report(order, observed).status_code, 200)
        _, other_headers = self.fixture.provision(self.app)
        for headers, product in ((self.headers, 'coins-5000'), (other_headers, 'coins-1000')):
            target = self.create(product, headers=headers)
            base = self.fixture.observation(target)
            for field in ('invoiceId', 'purchaseId'):
                response = self.report(target, base | {field: observed[field]}, headers=headers)
                self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 1)

    def test_07_once_per_player_and_create_command_remain_durable(self):
        command = uuid.uuid4().hex
        order = self.create(command=command)
        self.assertEqual(self.create(command=command)['orderId'], order['orderId'])
        self.assertEqual(self.create()['orderId'], order['orderId'])
        self.assertEqual(self.report(order).status_code, 200)
        response = self.client.post('/v1/commerce/orders', json={
            'commandId': uuid.uuid4().hex, 'productId': 'wellkeeper'}, headers=self.headers)
        self.assertEqual(response.status_code, 409)

    def test_08_terminal_refund_and_late_once_confirmation_are_sticky(self):
        order = self.create()
        observed = self.fixture.observation(order, status='CANCELLED')
        closed = self.report(order, observed).json()
        self.assertEqual(closed['state'], 'Cancelled')
        replacement = self.create()
        self.assertNotEqual(order['orderId'], replacement['orderId'])
        late = self.report(order, observed | {'status': 'CONFIRMED'}).json()
        self.assertEqual(late['state'], 'RefundReview')
        self.assertIsNone(late['credit'])
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 0)

    def test_08b_bank_return_after_cancel_delivers_once_without_freezing_wallet(self):
        order = self.create()
        observed = self.fixture.observation(order, status='CANCELLED')
        self.assertEqual(self.report(order, observed).json()['state'], 'Cancelled')
        late = self.report(order, observed | {'status': 'CONFIRMED'}).json()
        self.assertEqual(late['state'], 'Confirmed')
        self.assertIsNotNone(late['credit'])
        self.assertFalse(self.wallet()['refundReviewRequired'])
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 1)
        again = self.report(order, observed | {'status': 'CONFIRMED'}).json()
        self.assertEqual(again['state'], 'Confirmed')
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 1)
        self.assertEqual(self.client.post('/v1/commerce/orders', json={
            'commandId': uuid.uuid4().hex, 'productId': 'wellkeeper'}, headers=self.headers).status_code, 409)

    def test_09_refund_after_credit_never_regrants_or_silently_debits(self):
        order = self.create()
        observed = self.fixture.observation(order)
        self.report(order, observed)
        before = self.wallet()
        refunded = self.report(order, observed | {'status': 'REFUNDED'}).json()
        self.assertEqual(refunded['state'], 'RefundReview')
        self.assertFalse(refunded['availableToSpend'])
        replay = self.report(order, observed).json()
        self.assertEqual(replay['state'], 'RefundReview')
        self.assertEqual(self.wallet()['coins'], before['coins'])
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 1)

    def test_10_two_step_paid_never_grants_or_captures(self):
        order = self.create()
        observed = self.fixture.observation(order, status='PAID', purchaseType='TWO_STEP')
        held = self.report(order, observed).json()
        self.assertEqual(held['state'], 'Held')
        self.assertIsNone(held['credit'])
        self.assertEqual(self.report(order, observed | {'status': 'CONFIRMED'}).json()['state'], 'Confirmed')

    def test_11_identity_type_and_receipt_binding_cannot_change(self):
        order = self.create()
        observed = self.fixture.observation(order)
        self.report(order, observed)
        for changes in ({'purchaseType': 'TWO_STEP'}, {'purchaseId': str(uuid.uuid4())},
                        {'invoiceId': '99999'}):
            self.assertEqual(self.report(order, observed | changes).status_code, 409)

    def test_12_concurrent_reports_project_one_full_grant(self):
        order = self.create()
        observed = SdkPurchaseReport125.model_validate(self.fixture.observation(order))
        actor = Actor(self.identity['playerId'], self.fixture.now)
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            values = list(pool.map(lambda _: self.app.state.commerce.sdk_report(actor, order['orderId'], observed), range(12)))
        self.assertEqual(len({value['credit']['receiptId'] for value in values}), 1)
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 1)
        self.assertEqual(self.count("SELECT COUNT(*) FROM wallet_ledger WHERE origin LIKE 'commerce/%'"), 1)

    def test_13_commit_fault_rolls_back_entitlement_receipt_inventory_and_sdk_metadata(self):
        order = self.create()
        observed = self.fixture.observation(order)
        before = self.wallet()
        def fault(stage):
            if stage == 'BeforeCreditCommit':
                raise RuntimeError('explicit_test_fault')
        self.app.state.commerce.checkpoint = fault
        self.assertEqual(self.report(order, observed).status_code, 500)
        self.app.state.commerce.checkpoint = None
        self.assertEqual(self.wallet(), before)
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 0)
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_orders WHERE sdk_reported_at IS NOT NULL'), 0)
        self.assertEqual(self.report(order, observed).status_code, 200)

    def test_14_lost_response_replay_does_not_grant_twice(self):
        order = self.create()
        observed = self.fixture.observation(order)
        def fault(stage):
            if stage == 'AfterCreditCommit':
                raise RuntimeError('explicit_lost_response')
        self.app.state.commerce.checkpoint = fault
        self.assertEqual(self.report(order, observed).status_code, 500)
        self.app.state.commerce.checkpoint = None
        after = self.wallet()
        self.assertEqual(self.report(order, observed).status_code, 200)
        self.assertEqual(self.wallet(), after)

    def test_15_pending_discovery_returns_same_frozen_order_and_mode(self):
        order = self.create()
        pending = self.client.get('/v1/commerce/orders/pending', headers=self.headers).json()
        self.assertEqual(pending['orders'][0]['orderId'], order['orderId'])
        self.assertEqual(pending['orders'][0]['verificationMode'], 'sdk_client_reported')
        with self.app.state.authority.database.transaction() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE commerce_orders SET verification_mode='provider_api' WHERE id=?", (order['orderId'],))

    def test_16_no_server_verified_or_notification_path_is_enabled_in_sdk_mode(self):
        order = self.create()
        response = self.client.post('/v1/commerce/orders/' + order['orderId'] + '/reconcile',
            json={'invoiceId': '1234'}, headers=self.headers)
        self.assertEqual(response.status_code, 409)
        response = self.client.post('/v1/commerce/notifications/rustore/production', json={})
        self.assertEqual(response.status_code, 503)

    def test_21_vendor_pending_statuses_never_grant_and_keep_raw_observation(self):
        order = self.create()
        observed = self.fixture.observation(order, purchaseType='UNDEFINED')
        for status, state in (('INVOICE_CREATED', 'Created'), ('PROCESSING', 'Executed'),
                              ('EXECUTING', 'Executed')):
            value = self.report(order, observed | {'status': status}).json()
            self.assertEqual(value['state'], state)
            self.assertIsNone(value['credit'])
            with self.app.state.authority.database.connect() as db:
                self.assertEqual(db.execute('SELECT sdk_last_status FROM commerce_orders WHERE id=?',
                    (order['orderId'],)).fetchone()[0], status)
        self.assertEqual(self.report(order, observed | {'status': 'PROCESSING',
            'purchaseType': 'ONE_STEP'}).json()['state'], 'Executed')
        self.assertEqual(self.report(order, observed | {'status': 'CONFIRMED',
            'purchaseType': 'ONE_STEP'}).json()['state'], 'Confirmed')
        late = self.report(order, observed | {'status': 'INVOICE_CREATED'}).json()
        self.assertEqual(late['state'], 'Confirmed')
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 1)
        with self.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT sdk_purchase_type FROM commerce_orders WHERE id=?',
                (order['orderId'],)).fetchone()[0], 'ONE_STEP')

    def test_22_undefined_or_one_step_cannot_claim_held_funds_or_undefined_confirmation(self):
        order = self.create()
        observed = self.fixture.observation(order)
        for changes in ({'purchaseType': 'UNDEFINED'}, {'purchaseType': 'UNDEFINED', 'status': 'PAID'},
                        {'status': 'PAID'}, {'purchaseType': 'UNDEFINED', 'status': 'REFUNDED'}):
            self.assertEqual(self.report(order, observed | changes).status_code, 422)
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 0)

    def test_23_historical_order_app_and_environment_must_match_selected_runtime(self):
        order = self.create()
        observed = self.fixture.observation(order)
        with self.app.state.authority.database.transaction() as db:
            db.execute('UPDATE commerce_orders SET sandbox=1 WHERE id=?', (order['orderId'],))
        self.assertEqual(self.report(order, observed | {'sandbox': True}).status_code, 409)
        with self.app.state.authority.database.transaction() as db:
            db.execute('UPDATE commerce_orders SET sandbox=0,app_id=124 WHERE id=?', (order['orderId'],))
        self.assertEqual(self.report(order, observed).status_code, 409)
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 0)

    def test_24_expired_actor_cannot_report_fulfillment(self):
        order = self.create()
        observed = self.fixture.observation(order)
        self.fixture.now += 2_592_001
        self.assertEqual(self.report(order, observed).status_code, 401)
        self.assertEqual(self.count('SELECT COUNT(*) FROM commerce_credits'), 0)

class SdkModeIsolation125Tests(unittest.TestCase):
    def test_25_legacy_api_manifest_ownership_hash_does_not_change(self):
        with ProductionFixture122(initialize=False) as fixture:
            self.assertNotIn('verificationMode', fixture.manifest.raw)
            self.assertEqual(fixture.manifest.verification_mode, 'provider_api')
            self.assertEqual(fixture.manifest.manifest_sha256,
                             hashlib.sha256(runtime._bytes(fixture.document)).hexdigest())

    def test_17_provider_api_default_factory_rejects_sdk_reports_and_stays_schema15(self):
        with ProductionFixture122() as fixture, fixture.context() as app, fixture.client(app) as client:
            identity, headers = fixture.provision(app)
            order = client.post('/v1/commerce/orders', json={'commandId': uuid.uuid4().hex,
                'productId': 'wellkeeper'}, headers=headers).json()
            with SdkProductionFixture125(initialize=False) as sdk:
                observation = sdk.observation(order)
            response = client.post('/v1/commerce/orders/' + order['orderId'] + '/sdk-report',
                json=observation, headers=headers)
            self.assertEqual(response.status_code, 409)
            self.assertEqual(order['verificationMode'], 'provider_api')
            with app.state.authority.database.connect() as db:
                self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 15)

    def test_18_sdk_factory_never_automatically_migrates_existing15(self):
        with SdkProductionFixture125(initialize=False) as fixture:
            path = fixture.root / 'preexisting.sqlite3'
            Database(path)
            before = path.read_bytes()
            with self.assertRaises(Exception):
                Database(path, _sdk_commerce125=True)
            self.assertEqual(path.read_bytes(), before)

    def test_19_sdk_manifest_rejects_credentials_and_mode_mismatch(self):
        with SdkProductionFixture125(initialize=False) as fixture:
            raw = copy.deepcopy(fixture.document)
            raw['provider'] = {'keyId': 'not-allowed', 'privateKeyFile': str(fixture.root / 'a'),
                'notificationKeyFile': str(fixture.root / 'b'), 'allowedNetworks': sorted(runtime.PROVIDER_NETWORKS)}
            fixture.manifest_path.write_text(json.dumps(raw))
            with self.assertRaises(runtime.ProductionError):
                runtime.read_manifest(fixture.manifest_path)
            fixture.catalog.pop('verificationMode')
            fixture.catalog_path.write_text(json.dumps(fixture.catalog))
            fixture.document['commerceSHA256'] = hashlib.sha256(fixture.catalog_path.read_bytes()).hexdigest()
            fixture.write_manifest()
            with self.assertRaises(runtime.ProductionError):
                runtime.preflight(fixture.manifest)

    def test_20_sdk_owned_restart_preserves_wallet_mode_and_receipt(self):
        with SdkProductionFixture125() as fixture:
            with fixture.context() as app, fixture.client(app) as client:
                identity, headers = fixture.provision(app)
                order = client.post('/v1/commerce/orders', json={'commandId': uuid.uuid4().hex,
                    'productId': 'wellkeeper'}, headers=headers).json()
                observation = fixture.observation(order)
                receipt = client.post('/v1/commerce/orders/' + order['orderId'] + '/sdk-report',
                    json=observation, headers=headers).json()['credit']
                before = client.get('/v1/wallet', headers=headers).json()
            with patch('hotr_backend.rustore_auth.RuStoreTokenSupplier.from_file',
                       side_effect=AssertionError('SDK must not construct RSA supplier')):
                with fixture.context() as app, fixture.client(app) as client:
                    replay = client.post('/v1/commerce/orders/' + order['orderId'] + '/sdk-report',
                        json=observation, headers=headers)
                    self.assertEqual(replay.status_code, 200, replay.text)
                    self.assertEqual(replay.json()['credit'], receipt)
                    self.assertEqual(client.get('/v1/wallet', headers=headers).json(), before)

if __name__ == '__main__':
    unittest.main()

