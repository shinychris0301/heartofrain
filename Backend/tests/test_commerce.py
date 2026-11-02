import concurrent.futures
import json
import os
import sqlite3
import tempfile
import threading
import unittest
import uuid
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.commerce_schemas import CreateCommerceOrder, ReconcileCommerceOrder
from hotr_backend.rustore_provider import InvalidProviderResponse, ProviderUnavailable, RuStoreInvoiceProvider, VerifiedInvoice
from hotr_backend.schemas import INT_MAX
from hotr_backend.storage import COMMERCE_V2, DDL, SCHEMA_VERSION, Database

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class FakeProvider:
    configured = True

    def __init__(self):
        self.values = {}
        self.fail = False
        self.observer = None

    def lookup(self, invoice_id, sandbox):
        if self.observer:
            self.observer()
        if self.fail:
            raise ProviderUnavailable()
        return self.values[invoice_id]


class CommerceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-commerce-')
        self.path = Path(self.temp.name)
        self.now = 300 * 86400
        self.provider = FakeProvider()
        self.configuration = {'version': 'synthetic-commerce-test-v1', 'enabled': True, 'appId': 123,
                              'sandbox': True, 'products': [
                                  {'id': 'fixture_small', 'storeProductId': 'synthetic_1000', 'enabled': True,
                                   'coins': 1000, 'amountMinor': 9900, 'currency': 'RUB'},
                                  {'id': 'fixture_large', 'storeProductId': 'synthetic_5000', 'enabled': True,
                                   'coins': 5000, 'amountMinor': 39900, 'currency': 'RUB'}]}
        self.config = self.path / 'commerce.json'
        self.config.write_text(json.dumps(self.configuration), encoding='utf-8')
        self.database_path = self.path / 'authority.sqlite3'
        self.open()
        self.identity = self.authority.provision(lifetime=2_592_000)
        self.other = self.authority.provision(lifetime=2_592_000)
        self.headers = {'Authorization': 'Bearer ' + self.identity['token']}
        self.other_headers = {'Authorization': 'Bearer ' + self.other['token']}
        self.sequence = 1000

    def open(self):
        self.app = create_app(self.database_path, CONFIG, lambda: self.now,
                              commerce_provider=self.provider, commerce_config_path=self.config)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.authority = self.app.state.authority
        self.commerce = self.app.state.commerce

    def restart(self):
        self.client.close()
        self.open()

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def get(self, path, other=False):
        return self.client.get(path, headers=self.other_headers if other else self.headers)

    def post(self, path, value, other=False):
        return self.client.post(path, json=value, headers=self.other_headers if other else self.headers)

    def create(self, product='fixture_small', command=None, other=False):
        response = self.post('/v1/commerce/orders', {'commandId': command or ident(), 'productId': product}, other)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def invoice(self, order, status='CONFIRMED', **changes):
        self.sequence += 1
        value = VerifiedInvoice(str(self.sequence), str(uuid.uuid4()), 123, True, order['orderId'],
                                order['sdk']['productId'], order['playerId'], order['sdk']['developerPayload'],
                                order['amountMinor'], order['currency'], status, 'PENDING')
        value = replace(value, **changes)
        self.provider.values[str(self.sequence)] = value
        return str(self.sequence)

    def reconcile(self, order, invoice, other=False):
        return self.post('/v1/commerce/orders/' + order['orderId'] + '/reconcile', {'invoiceId': invoice}, other)

    def count(self, table):
        with self.authority.database.connect() as db:
            return db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def test_01_default_disabled_and_authentication(self):
        app = create_app(self.path / 'default.sqlite3', CONFIG, lambda: self.now)
        identity = app.state.authority.provision()
        headers = {'Authorization': 'Bearer ' + identity['token']}
        with TestClient(app) as client:
            self.assertEqual(client.get('/v1/commerce/catalog').status_code, 401)
            view = client.get('/v1/commerce/catalog', headers=headers).json()
            self.assertFalse(view['enabled'])
            self.assertFalse(view['productionEnabled'])
            self.assertFalse(view['fullGameplayWallet'])
            self.assertIsNone(view['appId'])
            self.assertIs(view['sandbox'], True)
            self.assertEqual(view['products'], [])
            self.assertEqual(client.post('/v1/commerce/orders', headers=headers,
                                         json={'commandId': ident(), 'productId': 'unknown'}).status_code, 503)
        verifier = self.authority.provision(role='verifier')
        self.assertEqual(self.client.get('/v1/commerce/catalog', headers={'Authorization': 'Bearer ' + verifier['token']}).status_code, 403)

    def test_02_create_idempotency_captures_server_mapping(self):
        catalog = self.get('/v1/commerce/catalog').json()
        self.assertEqual((catalog['appId'], catalog['sandbox']), (123, True))
        self.assertTrue(catalog['enabled'])
        key = ident()
        order = self.create(command=key)
        self.assertEqual(self.create(command=key), order)
        self.assertEqual(self.count('commerce_orders'), 1)
        self.assertEqual(order['sdk']['quantity'], 1)
        self.assertEqual(order['sdk']['appUserId'], self.identity['playerId'])
        self.assertEqual(order['sdk']['productId'], 'synthetic_1000')
        self.assertNotEqual(order['sdk']['developerPayload'], order['orderId'])
        self.assertFalse(order['availableToSpend'])
        self.assertEqual(self.post('/v1/commerce/orders', {'commandId': key, 'productId': 'fixture_large'}).status_code, 409)

    def test_03_client_amount_grants_quantity_status_and_path_rejected(self):
        for field, value in [('coins', 999999), ('amountMinor', 1), ('quantity', 2), ('status', 'CONFIRMED'), ('playerId', self.other['playerId'])]:
            with self.subTest(field=field):
                self.assertEqual(self.post('/v1/commerce/orders', {'commandId': ident(), 'productId': 'fixture_small', field: value}).status_code, 422)
        order = self.create()
        for value in ['0', '../1', 'https://attacker.test/', '-1', '1e9', 123, True]:
            self.assertEqual(self.reconcile(order, value).status_code, 422)
        self.assertEqual(self.post('/v1/commerce/orders/' + order['orderId'] + '/reconcile', {'invoiceId': '1001', 'status': 'CONFIRMED'}).status_code, 422)
        self.assertEqual(self.count('commerce_credits'), 0)

    def test_04_confirmed_once_and_reward_totals_unchanged(self):
        before = self.get('/v1/me').json()
        order = self.create()
        invoice = self.invoice(order)
        first = self.reconcile(order, invoice)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['state'], 'Confirmed')
        self.assertEqual(first.json()['credit']['coins'], 1000)
        self.assertEqual(first.json()['deliveryAcknowledgement'], 'Pending')
        self.assertFalse(first.json()['localProfileMutated'])
        self.assertEqual(self.reconcile(order, invoice).json()['credit'], first.json()['credit'])
        self.assertEqual(self.count('commerce_credits'), 1)
        self.assertEqual(self.count('commerce_delivery_ack'), 1)
        self.assertEqual(self.get('/v1/me').json(), before)
        self.assertEqual(self.count('rewards'), 0)

    def test_05_cross_owner_isolation_and_unverified_invoice_cannot_poison(self):
        victim, attacker = self.create(), self.create(other=True)
        invoice = self.invoice(victim)
        self.assertEqual(self.get('/v1/commerce/orders/' + victim['orderId'], True).status_code, 404)
        self.assertEqual(self.reconcile(victim, invoice, True).status_code, 404)
        self.assertEqual(self.reconcile(attacker, invoice, True).status_code, 409)
        self.assertEqual(self.reconcile(victim, invoice).status_code, 200)
        self.assertEqual(self.count('commerce_credits'), 1)
        self.assertEqual(self.get('/v1/commerce/credits', True).json()['credits'], [])

    def test_06_all_verified_binding_fields_are_required(self):
        changes = [('app_id', 999), ('sandbox', False), ('order_id', ident()),
                   ('product_id', 'synthetic_other'), ('app_user_id', self.other['playerId']),
                   ('developer_payload', 'unbound'), ('amount_minor', 1), ('currency', 'USD'),
                   ('invoice_id', '99999999')]
        for field, value in changes:
            with self.subTest(field=field):
                order = self.create()
                invoice = self.invoice(order, **{field: value})
                self.assertEqual(self.reconcile(order, invoice).status_code, 409)
        self.assertEqual(self.count('commerce_credits'), 0)

    def test_07_nonfinal_cancelled_refunded_and_held_never_grant(self):
        orders = [(status, self.create()) for status in self.commerce.statuses - {'CONFIRMED'}]
        for status, order in orders:
            with self.subTest(status=status):
                result = self.reconcile(order, self.invoice(order, status))
                self.assertEqual(result.status_code, 200)
                self.assertIsNone(result.json()['credit'])
                self.assertIsNone(result.json()['deliveryAcknowledgement'])
                if status == 'PAID':
                    self.assertEqual(result.json()['state'], 'Held')
        self.assertEqual(self.count('commerce_credits'), 0)

    def test_08_paid_then_confirmed_and_verified_delivery_ack(self):
        order = self.create()
        invoice = self.invoice(order, 'PAID')
        self.assertIsNone(self.reconcile(order, invoice).json()['credit'])
        self.provider.values[invoice] = replace(self.provider.values[invoice], status='CONFIRMED')
        self.assertEqual(self.reconcile(order, invoice).json()['deliveryAcknowledgement'], 'Pending')
        self.provider.fail = True
        self.assertEqual(self.reconcile(order, invoice).status_code, 503)
        self.restart()
        self.assertEqual(self.get('/v1/commerce/orders/' + order['orderId']).json()['deliveryAcknowledgement'], 'Pending')
        self.provider.fail = False
        self.provider.values[invoice] = replace(self.provider.values[invoice], acknowledgement='ACKNOWLEDGED')
        self.assertEqual(self.reconcile(order, invoice).json()['deliveryAcknowledgement'], 'Acknowledged')
        self.assertEqual(self.count('commerce_credits'), 1)

    def test_09_before_commit_rolls_back_credit_binding_and_ack(self):
        order = self.create()
        invoice = self.invoice(order)
        self.commerce.checkpoint = lambda stage: (_ for _ in ()).throw(RuntimeError('synthetic fault')) if stage == 'BeforeCreditCommit' else None
        self.assertEqual(self.reconcile(order, invoice).status_code, 500)
        self.assertEqual(self.count('commerce_credits'), 0)
        self.assertEqual(self.count('commerce_delivery_ack'), 0)
        self.assertIsNone(self.get('/v1/commerce/orders/' + order['orderId']).json()['invoiceId'])
        self.commerce.checkpoint = None
        self.assertEqual(self.reconcile(order, invoice).status_code, 200)
        self.assertEqual(self.count('commerce_credits'), 1)

    def test_10_lost_response_after_commit_recovers_once_after_restart(self):
        order = self.create()
        invoice = self.invoice(order)
        self.commerce.checkpoint = lambda stage: (_ for _ in ()).throw(RuntimeError('synthetic lost reply')) if stage == 'AfterCreditCommit' else None
        self.assertEqual(self.reconcile(order, invoice).status_code, 500)
        self.assertEqual(self.count('commerce_credits'), 1)
        self.restart()
        recovered = self.get('/v1/commerce/orders/' + order['orderId']).json()
        self.assertEqual(recovered['state'], 'Confirmed')
        self.assertEqual(self.reconcile(order, invoice).json()['credit'], recovered['credit'])
        self.assertEqual(self.count('commerce_credits'), 1)

    def test_11_provider_outage_retains_pending_recovery(self):
        order = self.create()
        invoice = self.invoice(order)
        self.provider.fail = True
        self.assertEqual(self.reconcile(order, invoice).status_code, 503)
        self.restart()
        pending = self.get('/v1/commerce/orders/' + order['orderId']).json()['pendingVerification']
        self.assertEqual(pending[0]['invoice_id'], invoice)
        self.assertEqual(pending[0]['state'], 'Unavailable')
        self.assertEqual(self.count('commerce_credits'), 0)
        self.provider.fail = False
        self.assertEqual(self.reconcile(order, invoice).status_code, 200)

    def test_12_concurrent_reconciliation_grants_once(self):
        order = self.create()
        invoice = self.invoice(order)
        actor = self.authority.authenticate(self.identity['token'])
        request = ReconcileCommerceOrder(invoiceId=invoice)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            values = list(pool.map(lambda _: self.commerce.reconcile(actor, order['orderId'], request), range(8)))
        self.assertTrue(all(v['state'] == 'Confirmed' for v in values))
        self.assertEqual(len({v['credit']['receiptId'] for v in values}), 1)
        self.assertEqual(self.count('commerce_credits'), 1)

    def test_13_concurrent_create_same_command_is_one_order(self):
        actor = self.authority.authenticate(self.identity['token'])
        request = CreateCommerceOrder(commandId=ident(), productId='fixture_small')
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            values = list(pool.map(lambda _: self.commerce.create(actor, request), range(8)))
        self.assertEqual(len({v['orderId'] for v in values}), 1)
        self.assertEqual(self.count('commerce_orders'), 1)

    def test_14_purchase_identity_cannot_fulfill_two_orders(self):
        first, second = self.create(), self.create()
        invoice = self.invoice(first)
        self.assertEqual(self.reconcile(first, invoice).status_code, 200)
        another = self.invoice(second, purchase_id=self.provider.values[invoice].purchase_id)
        self.assertEqual(self.reconcile(second, another).status_code, 409)
        self.assertEqual(self.count('commerce_credits'), 1)

    def test_15_config_changes_do_not_reprice_outstanding_order(self):
        key = ident()
        order = self.create(command=key)
        invoice = self.invoice(order)
        self.configuration['enabled'] = False
        self.configuration['products'][0]['amountMinor'] = 19900
        self.configuration['products'][0]['coins'] = 2000
        self.config.write_text(json.dumps(self.configuration), encoding='utf-8')
        self.restart()
        self.assertEqual(self.create(command=key), order)
        self.assertEqual(self.post('/v1/commerce/orders', {'commandId': ident(), 'productId': 'fixture_small'}).status_code, 503)
        self.assertEqual(self.reconcile(order, invoice).json()['credit']['coins'], 1000)

    def test_16_refund_is_a_durable_review_and_never_regrants(self):
        order = self.create()
        invoice = self.invoice(order)
        self.assertEqual(self.reconcile(order, invoice).status_code, 200)
        self.provider.values[invoice] = replace(self.provider.values[invoice], status='REFUNDED')
        value = self.reconcile(order, invoice).json()
        self.assertEqual(value['state'], 'RefundReview')
        self.assertEqual(value['deliveryAcknowledgement'], 'RefundReview')
        self.restart()
        self.provider.values[invoice] = replace(self.provider.values[invoice], status='CONFIRMED')
        self.assertEqual(self.reconcile(order, invoice).json()['state'], 'RefundReview')
        self.assertEqual(self.count('commerce_credits'), 1)

    def test_17_credit_overflow_fails_atomically(self):
        # The schema3 wallet already contains the approved1,250-coin genesis.
        self.configuration['products'][0]['coins'] = INT_MAX - 1250
        self.config.write_text(json.dumps(self.configuration), encoding='utf-8')
        self.restart()
        order = self.create()
        self.assertEqual(self.reconcile(order, self.invoice(order)).status_code, 200)
        self.assertEqual(self.get('/v1/wallet').json()['coins'], INT_MAX)
        next_order = self.create('fixture_large')
        self.assertEqual(self.reconcile(next_order, self.invoice(next_order)).status_code, 409)
        self.assertEqual(self.count('commerce_credits'), 1)
        self.assertIsNone(self.get('/v1/commerce/orders/' + next_order['orderId']).json()['invoiceId'])

    def test_18_provider_query_holds_no_database_write_lock(self):
        order = self.create()
        invoice = self.invoice(order)
        witnessed = []
        def observe():
            with self.authority.database.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                witnessed.append(True)
                db.rollback()
        self.provider.observer = observe
        self.assertEqual(self.reconcile(order, invoice).status_code, 200)
        self.assertEqual(witnessed, [True])

    def test_19_credit_receipt_pagination_and_no_public_notification_trust(self):
        for _ in range(2):
            order = self.create()
            self.assertEqual(self.reconcile(order, self.invoice(order)).status_code, 200)
        page = self.get('/v1/commerce/credits?limit=1').json()
        self.assertTrue(page['hasMore'])
        second = self.get('/v1/commerce/credits?after=' + str(page['nextCursor']) + '&limit=1').json()
        self.assertFalse(second['hasMore'])
        self.assertNotEqual(page['credits'][0]['id'], second['credits'][0]['id'])
        self.assertFalse(second['availableToSpend'])
        self.assertEqual(self.get('/v1/commerce/credits?after=9223372036854775808').status_code, 422)
        self.assertEqual(self.client.post('/v1/commerce/rustore/notifications', json={'status': 'CONFIRMED'}).status_code, 404)

    def test_20_invalid_provider_data_is_never_granted(self):
        for changes in ({'purchase_id': 'not-a-uuid'}, {'status': 'APPROVED'}, {'acknowledgement': 'bad'}, {'amount_minor': True}):
            order = self.create()
            self.assertEqual(self.reconcile(order, self.invoice(order, **changes)).status_code, 503)
        self.assertEqual(self.count('commerce_credits'), 0)

    def test_26_live_commerce_cannot_be_activated_by_catalog_config(self):
        self.configuration['sandbox'] = False
        self.config.write_text(json.dumps(self.configuration), encoding='utf-8')
        self.restart()
        catalog = self.get('/v1/commerce/catalog').json()
        self.assertFalse(catalog['enabled'])
        self.assertEqual(catalog['reason'], 'live_commerce_requires_wallet_integration')
        self.assertEqual(self.post('/v1/commerce/orders', {'commandId': ident(), 'productId': 'fixture_small'}).status_code, 503)
        self.assertEqual(self.count('commerce_orders'), 0)

    def test_27_stale_nonfinal_observations_do_not_remove_confirmed_credit(self):
        order = self.create()
        invoice = self.invoice(order)
        confirmed = self.reconcile(order, invoice).json()
        for status in ('PAID', 'CANCELLED', 'CREATED'):
            self.provider.values[invoice] = replace(self.provider.values[invoice], status=status)
            current = self.reconcile(order, invoice).json()
            self.assertEqual(current['state'], 'Confirmed')
            self.assertEqual(current['credit'], confirmed['credit'])
            self.assertEqual(current['deliveryAcknowledgement'], 'Pending')
        self.assertEqual(self.count('commerce_credits'), 1)

    def test_28_precredit_terminal_quarantine_survives_nonfinal_confirmed_and_restart(self):
        orders = [(terminal, self.create()) for terminal in ('REFUNDING', 'REFUNDED', 'REVERSED')]
        for terminal, order in orders:
            with self.subTest(terminal=terminal):
                invoice = self.invoice(order, terminal)
                first = self.reconcile(order, invoice).json()
                self.assertEqual(first['state'], 'RefundReview')
                self.assertIsNone(first['credit'])
                self.assertIsNone(first['deliveryAcknowledgement'])
                self.restart()
                for status in ('PAID', 'CREATED', 'CONFIRMED', 'CONFIRMED'):
                    self.provider.values[invoice] = replace(self.provider.values[invoice], status=status)
                    result = self.reconcile(order, invoice)
                    self.assertEqual(result.status_code, 200)
                    self.assertEqual(result.json()['state'], 'RefundReview')
                    self.assertIsNone(result.json()['credit'])
                    self.assertIsNone(result.json()['deliveryAcknowledgement'])
        self.assertEqual(self.count('commerce_credits'), 0)
        self.assertEqual(self.count('commerce_delivery_ack'), 0)

    def test_29_old_confirmation_completing_after_terminal_cannot_create_credit(self):
        orders = [(terminal, self.create()) for terminal in ('REFUNDING', 'REFUNDED', 'REVERSED')]
        for terminal, order in orders:
            with self.subTest(terminal=terminal):
                invoice_id = self.invoice(order)
                old_confirmation = self.provider.values[invoice_id]
                newer_terminal = replace(old_confirmation, status=terminal)
                began, release = threading.Event(), threading.Event()
                calls, calls_lock = [0], threading.Lock()
                def controlled_lookup(requested, sandbox):
                    with calls_lock:
                        calls[0] += 1
                        first = calls[0] == 1
                    if first:
                        began.set()
                        if not release.wait(5):
                            raise RuntimeError('Synthetic response gate timed out')
                        return old_confirmation
                    return newer_terminal
                self.provider.lookup = controlled_lookup
                actor = self.authority.authenticate(self.identity['token'])
                request = ReconcileCommerceOrder(invoiceId=invoice_id)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    old = pool.submit(self.commerce.reconcile, actor, order['orderId'], request)
                    try:
                        self.assertTrue(began.wait(5))
                        terminal_result = self.commerce.reconcile(actor, order['orderId'], request)
                        self.assertEqual(terminal_result['state'], 'RefundReview')
                        self.assertIsNone(terminal_result['credit'])
                    finally:
                        release.set()
                    delayed = old.result(timeout=5)
                    self.assertEqual(delayed['state'], 'RefundReview')
                    self.assertIsNone(delayed['credit'])
        self.assertEqual(self.count('commerce_credits'), 0)
        self.assertEqual(self.count('commerce_delivery_ack'), 0)

    def test_33_refunding_after_credit_quarantines_without_debit_or_repeat_grant(self):
        order = self.create()
        invoice = self.invoice(order)
        confirmed = self.reconcile(order, invoice).json()
        before = self.get('/v1/wallet').json()
        self.assertEqual(before['coins'], 2250)
        self.assertFalse(before['refundReviewRequired'])
        self.provider.values[invoice] = replace(self.provider.values[invoice], status='REFUNDING')
        result = self.reconcile(order, invoice)
        self.assertEqual(result.status_code, 200)
        review = result.json()
        self.assertEqual(review['state'], 'RefundReview')
        self.assertEqual(review['credit'], confirmed['credit'])
        self.assertEqual(review['deliveryAcknowledgement'], 'RefundReview')
        self.assertFalse(review['availableToSpend'])
        wallet = self.get('/v1/wallet').json()
        self.assertTrue(wallet['refundReviewRequired'])
        self.assertEqual((wallet['coins'], wallet['revision']), (before['coins'], before['revision']))
        self.assertEqual(self.post('/v1/commerce/orders', {'commandId': ident(), 'productId': 'fixture_small'}).status_code, 409)
        self.restart()
        # Final refunds and stale nonfinal/confirmed responses all preserve
        # review and the immutable already-issued receipt. No auto clawback.
        for status in ('CONFIRMED', 'PAID', 'REFUNDED', 'REVERSED', 'CONFIRMED'):
            self.provider.values[invoice] = replace(self.provider.values[invoice], status=status)
            current = self.reconcile(order, invoice).json()
            self.assertEqual(current['state'], 'RefundReview')
            self.assertEqual(current['credit'], confirmed['credit'])
            self.assertEqual(current['deliveryAcknowledgement'], 'RefundReview')
            self.assertFalse(current['availableToSpend'])
        self.assertEqual(self.count('commerce_credits'), 1)
        self.assertEqual(self.count('commerce_delivery_ack'), 1)
        wallet = self.get('/v1/wallet').json()
        self.assertEqual((wallet['coins'], wallet['revision']), (before['coins'], before['revision']))

    def test_30_server_provider_requires_explicit_enabled_config_and_both_secret_references(self):
        with patch.dict(os.environ, {'HOTR_RUSTORE_KEY_ID': 'synthetic-key', 'HOTR_RUSTORE_PRIVATE_KEY_FILE': ''}):
            with self.assertRaises(RuntimeError):
                create_app(self.path / 'incomplete-auth.sqlite3', CONFIG, lambda: self.now,
                           commerce_config_path=self.config)
        with patch.dict(os.environ, {'HOTR_RUSTORE_KEY_ID': 'synthetic-key', 'HOTR_RUSTORE_PRIVATE_KEY_FILE': 'not-read-by-startup'}):
            app = create_app(self.path / 'configured-auth.sqlite3', CONFIG, lambda: self.now,
                             commerce_config_path=self.config)
            self.assertIsInstance(app.state.commerce.provider, RuStoreInvoiceProvider)
            # A disabled default catalog never loads or requires the secret.
            disabled = create_app(self.path / 'disabled-auth.sqlite3', CONFIG, lambda: self.now)
            self.assertFalse(disabled.state.commerce.provider.configured)

    def test_31_existing_genesis_makes_purchase_wallet_overflow_atomic(self):
        self.configuration['products'][0]['coins'] = INT_MAX
        self.config.write_text(json.dumps(self.configuration), encoding='utf-8')
        self.restart()
        before = self.get('/v1/wallet').json()
        order = self.create()
        self.assertEqual(self.reconcile(order, self.invoice(order)).status_code, 409)
        self.assertEqual(self.get('/v1/wallet').json(), before)
        self.assertEqual(self.count('commerce_credits'), 0)
        self.assertEqual(self.count('commerce_delivery_ack'), 0)


class CommerceMigrationTests(unittest.TestCase):
    def test_21_existing_schema1_data_survives_additive_migration(self):
        with tempfile.TemporaryDirectory(prefix='hotr-migration-') as temp:
            path = Path(temp) / 'old.sqlite3'
            db = sqlite3.connect(path)
            db.executescript(DDL)
            player = ident()
            db.execute('INSERT INTO players(id,reward_totals,created_at) VALUES(?,?,?)', (player, '[17,0,0,0,0,0,0,0,0,0]', 100))
            db.commit()
            db.close()
            migrated = Database(path)
            with migrated.connect() as db:
                self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], SCHEMA_VERSION)
                self.assertEqual(db.execute('SELECT reward_totals FROM players WHERE id=?', (player,)).fetchone()[0], '[17,0,0,0,0,0,0,0,0,0]')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_orders').fetchone()[0], 0)
            Database(path)

    def test_22_migration_failure_rolls_back_schema_and_all_new_tables(self):
        with tempfile.TemporaryDirectory(prefix='hotr-migration-') as temp:
            path = Path(temp) / 'old.sqlite3'
            with closing(sqlite3.connect(path)) as db:
                db.executescript(DDL)
            with patch('hotr_backend.storage.COMMERCE_V2', COMMERCE_V2 + '; INVALID SQL;'):
                with self.assertRaises(sqlite3.Error):
                    Database(path)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name LIKE 'commerce_%'").fetchone()[0], 0)
            Database(path)


class RuStoreTransportTests(unittest.TestCase):
    @staticmethod
    def body():
        return {'code': 'OK', 'body': {'invoiceId': 1234, 'purchaseId': str(uuid.uuid4()), 'appId': 123,
                'appUserId': ident(), 'developerPayload': 'synthetic-binding', 'invoiceStatus': 'CONFIRMED',
                'acknowledgementState': 'PENDING', 'order': {'orderId': ident(), 'itemCode': 'synthetic_product',
                'amountCurrent': 9900, 'currency': 'RUB'}, 'paymentInfo': {'maskedPan': 'synthetic-do-not-retain'}}}

    def test_23_exact_official_sandbox_and_live_urls_and_bounded_fields(self):
        for sandbox in (True, False):
            body = self.body()
            seen = []
            def response(request):
                seen.append(request)
                return httpx.Response(200, json=body)
            provider = RuStoreInvoiceProvider(lambda: 'synthetic-server-jwe', httpx.MockTransport(response))
            value = provider.lookup('1234', sandbox)
            self.assertEqual(str(seen[0].url), 'https://public-api-m.rustore.ru/public/' + ('sandbox/' if sandbox else '') + 'v2/invoices/1234')
            self.assertEqual(seen[0].headers['Public-Token'], 'synthetic-server-jwe')
            self.assertEqual(value.amount_minor, 9900)
            self.assertNotIn('maskedPan', repr(value))
            self.assertNotIn('synthetic-server-jwe', repr(value))

    def test_24_provider_errors_redirects_large_and_malformed_responses_fail_closed(self):
        cases = [httpx.Response(302, headers={'location': 'https://attacker.test/'}), httpx.Response(401),
                 httpx.Response(200, json={'code': 'ERROR', 'body': None}), httpx.Response(200, content=b'x' * 65_537),
                 httpx.Response(200, content=b'invalid-json'), httpx.Response(200, json=[]), httpx.Response(200, content=b'null'),
                 httpx.Response(200, content=b'{"code":"OK","code":"ERROR","body":{}}'),
                 httpx.Response(200, content=b'{"code":"OK","body":{"invoiceId":NaN}}')]
        malformed = self.body();malformed['body']['order']['amountCurrent'] = 1.5
        cases.append(httpx.Response(200, json=malformed))
        wrong_id = self.body();wrong_id['body']['invoiceId'] = 9999
        cases.append(httpx.Response(200, json=wrong_id))
        for reply in cases:
            with self.subTest(status=reply.status_code):
                provider = RuStoreInvoiceProvider(lambda: 'synthetic-server-jwe', httpx.MockTransport(lambda _: reply))
                with self.assertRaises((ProviderUnavailable, InvalidProviderResponse)):
                    provider.lookup('1234', True)

    def test_25_timeout_and_missing_token_remain_unavailable(self):
        def unavailable(request):
            raise httpx.ReadTimeout('synthetic timeout', request=request)
        with self.assertRaises(ProviderUnavailable):
            RuStoreInvoiceProvider(lambda: 'synthetic-server-jwe', httpx.MockTransport(unavailable)).lookup('1234', True)
        with self.assertRaises(ProviderUnavailable):
            RuStoreInvoiceProvider(lambda: '').lookup('1234', True)

    def test_32_unauthorized_invoice_invalidates_server_token_without_retry_or_credit(self):
        class Supplier:
            invalidated = 0
            def __call__(self):
                return 'synthetic-token'
            def invalidate(self):
                self.invalidated += 1
        for status in (401, 403):
            supplier, calls = Supplier(), []
            def response(request):
                calls.append(request)
                return httpx.Response(status)
            with self.assertRaises(ProviderUnavailable):
                RuStoreInvoiceProvider(supplier, httpx.MockTransport(response)).lookup('1234', True)
            self.assertEqual(supplier.invalidated, 1)
            self.assertEqual(len(calls), 1)
