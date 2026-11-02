"""Real SQLite/ASGI full-Grant transactions; scripted store evidence, not purchases."""
import concurrent.futures
import copy
import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from tests import test_commerce as fixtures
from hotr_backend.commerce_schemas import CommerceProduct, CreateCommerceOrder, ReconcileCommerceOrder
from hotr_backend.commerce_schema import COMMERCE_V9_DDL
from hotr_backend.operations import _expected, backup_database, restore_database
from hotr_backend.schemas import INT_MAX
from hotr_backend.storage import Database, SCHEMA_VERSION, canonical


SPECIAL = {'id': 'wellkeeper', 'storeProductId': 'hotr_bundle_wellkeeper_c', 'enabled': True,
           'coins': 2000, 'amountMinor': 9900, 'currency': 'RUB', 'purchaseLimitPerPlayer': 1,
           'grant': {'coins': 2000, 'stars': 0, 'starting': [1] * 4, 'tools': [1] * 4}}
MEGA = {'id': 'village', 'storeProductId': 'hotr_bundle_village', 'enabled': True,
        'coins': 5000, 'amountMinor': 39900, 'currency': 'RUB', 'purchaseLimitPerPlayer': None,
        'grant': {'coins': 5000, 'stars': 0, 'starting': [3] * 4, 'tools': [2] * 4}}


class FullGrantCommerce100Tests(unittest.TestCase):
    # Reuse transport/provider setup without inheriting or rediscovering its
    # existing coin-only tests. All new assertions run against real databases.
    open = fixtures.CommerceTests.open
    restart = fixtures.CommerceTests.restart
    tearDown = fixtures.CommerceTests.tearDown
    get = fixtures.CommerceTests.get
    post = fixtures.CommerceTests.post
    create = fixtures.CommerceTests.create
    invoice = fixtures.CommerceTests.invoice
    reconcile = fixtures.CommerceTests.reconcile
    count = fixtures.CommerceTests.count

    def setUp(self):
        fixtures.CommerceTests.setUp(self)
        self.configuration['products'].extend(copy.deepcopy([SPECIAL, MEGA]))
        self.save_config()
        self.restart()

    def save_config(self):
        self.config.write_text(json.dumps(self.configuration), encoding='utf-8')

    def wallet(self):
        value = self.get('/v1/wallet')
        self.assertEqual(value.status_code, 200)
        return value.json()

    def policy(self, product='wellkeeper'):
        return next(p for p in self.get('/v1/commerce/catalog').json()['products'] if p['id'] == product)

    def entitlements(self):
        with self.authority.database.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM commerce_entitlements ORDER BY player_id,offer_id')]

    def assert_delta(self, before, grant):
        after = self.wallet()
        self.assertEqual(after['coins'], before['coins'] + grant['coins'])
        self.assertEqual(after['stars'], before['stars'])
        for field in ('starting', 'tools'):
            self.assertEqual(after[field], [a + b for a, b in zip(before[field], grant[field], strict=True)])
        self.assertEqual(after['lives'], before['lives'])
        self.assertEqual(after['revision'], before['revision'] + 1)

    def test_legacy_config_normalizes_and_invalid_purchase_grants_fail_closed(self):
        legacy = CommerceProduct(id='coins-1000', coins=1000)
        self.assertEqual(legacy.grant.model_dump(), {'coins': 1000, 'stars': 0, 'starting': [0] * 4, 'tools': [0] * 4})
        self.assertIsNone(legacy.purchaseLimitPerPlayer)
        for change in ({'coins': 1}, {'stars': 1}, {'starting': [1, 2, 3]}, {'tools': [0, 0, 0, True]}):
            value = copy.deepcopy(SPECIAL)
            value['grant'].update(change)
            with self.subTest(change=change), self.assertRaises(ValidationError):
                CommerceProduct.model_validate(value)
        for limit in (0, 2, True, '1'):
            with self.subTest(limit=limit), self.assertRaises(ValidationError):
                CommerceProduct.model_validate(SPECIAL | {'purchaseLimitPerPlayer': limit})
        self.assertEqual(self.post('/v1/commerce/orders', {'commandId': fixtures.ident(), 'productId': 'wellkeeper',
                                                         'grant': SPECIAL['grant']}).status_code, 422)

    def test_full_grant_ledger_credit_and_entitlement_commit_once(self):
        before = self.wallet()
        order = self.create('wellkeeper')
        self.assertEqual(order['grant'], SPECIAL['grant'])
        self.assertEqual((order['eligible'], order['eligibility'], order['pendingOrderId']), (False, 'Pending', order['orderId']))
        invoice = self.invoice(order)
        result = self.reconcile(order, invoice).json()
        self.assertEqual(result['credit']['grant'], SPECIAL['grant'])
        self.assertEqual(result['eligibility'], 'Purchased')
        self.assertFalse(result['repeatable'])
        self.assertIsNone(result['pendingOrderId'])
        self.assert_delta(before, SPECIAL['grant'])
        self.assertEqual(self.reconcile(order, invoice).json()['credit'], result['credit'])
        self.assert_delta(before, SPECIAL['grant'])
        self.assertEqual(self.count('commerce_credits'), 1)
        self.assertEqual(self.entitlements()[0]['state'], 'Consumed')
        credits = self.get('/v1/commerce/credits').json()['credits']
        self.assertEqual(credits[0]['grant'], SPECIAL['grant'])
        self.assertNotIn('grant_json', credits[0])
        self.assertEqual(self.post('/v1/commerce/orders', {'commandId': fixtures.ident(), 'productId': 'wellkeeper'}).json()['error'],
                         'commerce_offer_already_purchased')

    def test_concurrent_new_commands_reserve_one_special_order(self):
        actor = self.authority.authenticate(self.identity['token'])
        requests = [CreateCommerceOrder(commandId=fixtures.ident(), productId='wellkeeper') for _ in range(8)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            orders = list(pool.map(lambda request: self.commerce.create(actor, request), requests))
        self.assertEqual(len({order['orderId'] for order in orders}), 1)
        self.assertEqual(len({order['creationCommandId'] for order in orders}), 1)
        # Only one caller owns original creation. Followers must recover this
        # order without dispatching another SDK purchase UI.
        self.assertEqual(sum(order['creationCommandId'] == request.commandId
                             for request, order in zip(requests, orders, strict=True)), 1)
        self.assertEqual(self.count('commerce_orders'), 1)
        self.assertEqual(len(self.entitlements()), 1)
        order, before = orders[0], self.wallet()
        request = ReconcileCommerceOrder(invoiceId=self.invoice(order))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            receipts = list(pool.map(lambda _: self.commerce.reconcile(actor, order['orderId'], request), range(8)))
        self.assertEqual(len({value['credit']['receiptId'] for value in receipts}), 1)
        self.assert_delta(before, SPECIAL['grant'])

    def test_repeatable_mega_delivers_all_items_on_each_distinct_order(self):
        for _ in range(2):
            before = self.wallet()
            order = self.create('village')
            self.assertIsNone(order['purchaseLimitPerPlayer'])
            self.assertTrue(order['repeatable'])
            self.assertEqual(self.reconcile(order, self.invoice(order)).status_code, 200)
            self.assert_delta(before, MEGA['grant'])
        self.assertEqual(self.count('commerce_orders'), 2)
        self.assertEqual(self.count('commerce_credits'), 2)
        self.assertEqual(self.entitlements(), [])

    def test_two_credentials_race_recovers_follower_without_creation_ownership(self):
        second = self.authority.provision(player=self.identity['playerId'])
        actors = [self.authority.authenticate(token) for token in (self.identity['token'], second['token'])]
        requests = [CreateCommerceOrder(commandId=fixtures.ident(), productId='wellkeeper') for _ in actors]
        barrier = threading.Barrier(2)
        def reserve(pair):
            actor, request = pair
            barrier.wait(5)
            return self.commerce.create(actor, request)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            orders = list(pool.map(reserve, zip(actors, requests, strict=True)))
        self.assertEqual(orders[0]['orderId'], orders[1]['orderId'])
        owners = [order['creationCommandId'] == request.commandId
                  for request, order in zip(requests, orders, strict=True)]
        self.assertEqual(sorted(owners), [False, True])
        follower = 0 if not owners[0] else 1
        self.assertNotEqual(orders[follower]['creationCommandId'], requests[follower].commandId)
        self.restart()
        recovered = self.get('/v1/commerce/orders/pending').json()['orders'][0]
        self.assertEqual(recovered['creationCommandId'], orders[0]['creationCommandId'])
        self.assertEqual(self.count('commerce_orders'), 1)
        self.assertEqual(len(self.entitlements()), 1)

    def test_inventory_index_order_is_not_transposed(self):
        grant = {'coins': 2000, 'stars': 0, 'starting': [1, 2, 3, 4], 'tools': [4, 3, 2, 1]}
        self.configuration['products'][2]['grant'] = grant
        self.save_config()
        self.restart()
        before, order = self.wallet(), self.create('wellkeeper')
        self.assertEqual(self.reconcile(order, self.invoice(order)).status_code, 200)
        self.assert_delta(before, grant)

    def test_pending_full_terms_survive_catalog_change_restart_and_second_session(self):
        order = self.create('wellkeeper')
        self.configuration['products'][2]['grant']['tools'] = [9] * 4
        self.configuration['products'][2]['amountMinor'] = 19900
        self.save_config()
        self.restart()
        self.assertEqual(self.create('wellkeeper')['orderId'], order['orderId'])
        recovered = self.get('/v1/commerce/orders/pending').json()['orders'][0]
        self.assertEqual((recovered['grant'], recovered['amountMinor']), (SPECIAL['grant'], 9900))
        second = self.authority.provision(player=self.identity['playerId'])
        self.authority.revoke(self.identity['token'])
        self.headers = {'Authorization': 'Bearer ' + second['token']}
        self.assertEqual(self.get('/v1/commerce/orders/pending').json()['orders'][0]['orderId'], order['orderId'])
        before = self.wallet()
        self.assertEqual(self.reconcile(order, self.invoice(order)).status_code, 200)
        self.assert_delta(before, SPECIAL['grant'])
        other = self.create('wellkeeper', other=True)
        self.assertNotEqual(other['orderId'], order['orderId'])

    def test_new_wellkeeper_orders_use_registered_consumable_and_reject_deleted_sku(self):
        before, order = self.wallet(), self.create('wellkeeper')
        self.assertEqual(order['sdk']['productId'], 'hotr_bundle_wellkeeper_c')
        self.assertEqual(order['grant'], SPECIAL['grant'])
        self.assertEqual(order['amountMinor'], 9900)
        self.assertEqual(order['purchaseLimitPerPlayer'], 1)
        invoice = self.invoice(order)
        original = self.provider.values[invoice]
        self.provider.values[invoice] = replace(original, product_id='hotr_bundle_wellkeeper')
        rejected = self.reconcile(order, invoice)
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(rejected.json()['error'], 'purchase_binding_mismatch')
        self.assertEqual(self.count('commerce_credits'), 0)
        self.assertEqual(self.wallet(), before)
        self.provider.values[invoice] = original
        self.assertEqual(self.reconcile(order, invoice).status_code, 200)
        self.assertEqual(self.reconcile(order, invoice).status_code, 200)
        self.assert_delta(before, SPECIAL['grant'])
        self.assertEqual(self.count('commerce_credits'), 1)

    def test_wellkeeper_sku_replacement_preserves_historical_pending_order_terms(self):
        # Historical receipts must never be rewritten into a different SKU.
        self.configuration['products'][2]['storeProductId'] = 'hotr_bundle_wellkeeper'
        self.save_config()
        self.restart()
        original = self.create('wellkeeper')
        invoice = self.invoice(original)
        self.configuration['products'][2]['storeProductId'] = 'hotr_bundle_wellkeeper_c'
        self.save_config()
        self.restart()
        frozen = self.get('/v1/commerce/orders/pending').json()['orders'][0]
        self.assertEqual(frozen['orderId'], original['orderId'])
        self.assertEqual(frozen['sdk']['productId'], 'hotr_bundle_wellkeeper')
        self.assertEqual(frozen['grant'], original['grant'])
        self.assertEqual(frozen['amountMinor'], original['amountMinor'])
        self.assertEqual(self.create('wellkeeper')['orderId'], original['orderId'])
        before = self.wallet()
        self.assertEqual(self.reconcile(original, invoice).status_code, 200)
        self.assert_delta(before, SPECIAL['grant'])
        # Another stable player has no old reservation and receives the new SKU.
        other = self.create('wellkeeper', other=True)
        self.assertEqual(other['sdk']['productId'], 'hotr_bundle_wellkeeper_c')
        self.assertEqual(self.count('commerce_credits'), 1)

    def test_catalog_policy_downgrade_cannot_bypass_consumed_special(self):
        order = self.create('wellkeeper')
        self.assertEqual(self.reconcile(order, self.invoice(order)).status_code, 200)
        self.configuration['products'][2]['purchaseLimitPerPlayer'] = None
        self.save_config()
        self.restart()
        self.assertFalse(self.policy()['repeatable'])
        self.assertEqual(self.policy()['eligibility'], 'Purchased')
        self.assertEqual(self.post('/v1/commerce/orders', {'commandId': fixtures.ident(), 'productId': 'wellkeeper'}).status_code, 409)

    def test_only_verified_final_failure_releases_reserved_special(self):
        for status in ('CANCELLED', 'REJECTED', 'EXPIRED'):
            with self.subTest(status=status):
                order = self.create('wellkeeper')
                held = self.invoice(order, 'PAID')
                self.assertEqual(self.reconcile(order, held).json()['state'], 'Held')
                self.assertEqual(self.create('wellkeeper')['orderId'], order['orderId'])
                self.provider.values[held] = replace(self.provider.values[held], status=status)
                cancelled = self.reconcile(order, held).json()
                self.assertTrue(cancelled['reservationReleased'])
                self.assertEqual(self.entitlements(), [])
                self.assertTrue(self.policy()['eligible'])
                # A delayed nonfinal observation cannot reacquire eligibility.
                self.provider.values[held] = replace(self.provider.values[held], status='PAID')
                self.assertEqual(self.reconcile(order, held).json()['state'], status.title())
                self.assertEqual(self.entitlements(), [])
        self.assertEqual(self.count('commerce_credits'), 0)

    def test_unknown_unverified_and_client_cancel_never_release(self):
        order = self.create('wellkeeper')
        invoice = self.invoice(order, 'CANCELLED', amount_minor=1)
        self.assertEqual(self.reconcile(order, invoice).status_code, 409)
        self.provider.fail = True
        self.assertEqual(self.reconcile(order, invoice).status_code, 503)
        self.provider.fail = False
        self.assertEqual(self.post('/v1/commerce/orders/' + order['orderId'] + '/cancel', {}).status_code, 404)
        self.assertEqual(self.create('wellkeeper')['orderId'], order['orderId'])
        self.assertEqual(self.entitlements()[0]['state'], 'Reserved')
        self.restart()
        self.assertEqual(self.get('/v1/commerce/orders/pending').json()['orders'][0]['orderId'], order['orderId'])

    def test_late_confirmation_after_release_quarantines_without_duplicate_grant(self):
        old = self.create('wellkeeper')
        invoice = self.invoice(old, 'CANCELLED')
        self.assertEqual(self.reconcile(old, invoice).status_code, 200)
        replacement = self.create('wellkeeper')
        before = self.wallet()
        self.provider.values[invoice] = replace(self.provider.values[invoice], status='CONFIRMED')
        late = self.reconcile(old, invoice).json()
        self.assertEqual(late['state'], 'RefundReview')
        self.assertIsNone(late['credit'])
        self.assertEqual(self.wallet()['revision'], before['revision'])
        self.assertTrue(self.wallet()['refundReviewRequired'])
        self.assertEqual(self.entitlements()[0]['order_id'], replacement['orderId'])
        self.assertEqual(self.entitlements()[0]['state'], 'Reserved')
        self.restart()
        self.assertEqual(self.reconcile(old, invoice).json()['state'], 'RefundReview')
        self.assertEqual(self.count('commerce_credits'), 0)

    def test_inflight_stale_confirmation_cannot_consume_replacement_reservation(self):
        order = self.create('wellkeeper')
        invoice = self.invoice(order)
        captured = self.provider.values[invoice]
        entered, release = threading.Event(), threading.Event()
        lock, count = threading.Lock(), 0
        lookup = self.provider.lookup
        def delayed(invoice_id, sandbox):
            nonlocal count
            with lock:
                count += 1
                first = count == 1
            if first:
                entered.set()
                if not release.wait(10):
                    raise RuntimeError('controlled provider wait timed out')
                return captured
            return lookup(invoice_id, sandbox)
        self.provider.lookup = delayed
        actor = self.authority.authenticate(self.identity['token'])
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.commerce.reconcile, actor, order['orderId'], ReconcileCommerceOrder(invoiceId=invoice))
            try:
                self.assertTrue(entered.wait(5))
                self.provider.values[invoice] = replace(captured, status='CANCELLED')
                self.assertTrue(self.reconcile(order, invoice).json()['reservationReleased'])
                replacement = self.create('wellkeeper')
            finally:
                release.set()
            value = future.result(10)
        self.assertEqual(value['state'], 'RefundReview')
        self.assertIsNone(value['credit'])
        self.assertEqual(self.entitlements()[0]['order_id'], replacement['orderId'])
        self.assertEqual(self.entitlements()[0]['state'], 'Reserved')
        self.assertEqual(self.count('commerce_credits'), 0)

    def test_refund_preserves_delivered_inventory_and_consumed_cap(self):
        order = self.create('wellkeeper')
        invoice = self.invoice(order)
        self.assertEqual(self.reconcile(order, invoice).status_code, 200)
        before = self.wallet()
        self.provider.values[invoice] = replace(self.provider.values[invoice], status='REFUNDING')
        review = self.reconcile(order, invoice).json()
        self.assertEqual(review['state'], 'RefundReview')
        self.assertFalse(review['availableToSpend'])
        self.restart()
        for field in ('coins', 'stars', 'starting', 'tools', 'lives', 'revision'):
            self.assertEqual(self.wallet()[field], before[field])
        self.assertEqual(self.entitlements()[0]['state'], 'Consumed')
        self.assertEqual(self.count('commerce_credits'), 1)

    def test_refund_before_delivery_does_not_release_or_credit_special(self):
        order = self.create('wellkeeper')
        invoice = self.invoice(order, 'REFUNDING')
        value = self.reconcile(order, invoice).json()
        self.assertEqual(value['state'], 'RefundReview')
        self.assertFalse(value['reservationReleased'])
        self.assertIsNone(value['credit'])
        self.assertEqual(self.entitlements()[0]['state'], 'Reserved')
        self.provider.values[invoice] = replace(self.provider.values[invoice], status='CONFIRMED')
        self.assertEqual(self.reconcile(order, invoice).json()['state'], 'RefundReview')
        self.assertEqual(self.count('commerce_credits'), 0)

    def test_create_faults_roll_back_or_recover_the_single_reservation(self):
        def fail(stage):
            raise RuntimeError('controlled create ' + stage)
        self.authority.checkpoint = lambda stage: fail(stage) if stage == 'BeforeCommit' else None
        body = {'commandId': fixtures.ident(), 'productId': 'wellkeeper'}
        self.assertEqual(self.post('/v1/commerce/orders', body).status_code, 500)
        self.assertEqual(self.count('commerce_orders'), 0)
        self.assertEqual(self.entitlements(), [])
        self.authority.checkpoint = lambda stage: fail(stage) if stage == 'AfterCommit' else None
        self.assertEqual(self.post('/v1/commerce/orders', body).status_code, 500)
        self.assertEqual(self.count('commerce_orders'), 1)
        self.assertEqual(len(self.entitlements()), 1)
        self.restart()
        recovered = self.get('/v1/commerce/orders/pending').json()['orders'][0]
        self.assertEqual(self.post('/v1/commerce/orders', body).json()['orderId'], recovered['orderId'])
        self.assertEqual(self.count('commerce_orders'), 1)

    def test_item_overflow_rolls_back_coins_receipt_ack_and_consumption(self):
        with self.authority.database.transaction() as db:
            balances = json.loads(db.execute('SELECT balances FROM wallets WHERE player_id=?', (self.identity['playerId'],)).fetchone()[0])
            balances[5] = INT_MAX
            db.execute('UPDATE wallets SET balances=? WHERE player_id=?', (canonical(balances), self.identity['playerId']))
        before, order = self.wallet(), self.create('wellkeeper')
        response = self.reconcile(order, self.invoice(order))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.wallet(), before)
        self.assertEqual(self.count('commerce_credits'), 0)
        self.assertEqual(self.count('commerce_delivery_ack'), 0)
        self.assertEqual(self.entitlements()[0]['state'], 'Reserved')
        self.assertIsNone(self.get('/v1/commerce/orders/' + order['orderId']).json()['invoiceId'])

    def test_fault_before_commit_rolls_back_every_projection_and_retries_once(self):
        before, order = self.wallet(), self.create('wellkeeper')
        invoice = self.invoice(order)
        self.commerce.checkpoint = lambda stage: (_ for _ in ()).throw(RuntimeError('controlled transaction fault')) if stage == 'BeforeCreditCommit' else None
        self.assertEqual(self.reconcile(order, invoice).status_code, 500)
        self.assertEqual(self.wallet(), before)
        self.assertEqual(self.entitlements()[0]['state'], 'Reserved')
        self.assertEqual(self.count('commerce_credits'), 0)
        self.commerce.checkpoint = None
        self.assertEqual(self.reconcile(order, invoice).status_code, 200)
        self.assert_delta(before, SPECIAL['grant'])

    def test_lost_confirmation_reply_restart_reprojects_no_inventory_twice(self):
        before, order = self.wallet(), self.create('wellkeeper')
        invoice = self.invoice(order)
        self.commerce.checkpoint = lambda stage: (_ for _ in ()).throw(RuntimeError('controlled lost reply')) if stage == 'AfterCreditCommit' else None
        self.assertEqual(self.reconcile(order, invoice).status_code, 500)
        self.restart()
        recovered = self.get('/v1/commerce/orders/pending').json()['orders'][0]
        self.assertEqual(recovered['credit']['grant'], SPECIAL['grant'])
        self.assertEqual(self.reconcile(order, invoice).status_code, 200)
        self.assert_delta(before, SPECIAL['grant'])
        self.assertEqual(self.count('commerce_credits'), 1)

    def test_pending_is_player_scoped_bounded_and_provider_acknowledged(self):
        first, second = self.create('wellkeeper'), self.create('village')
        self.create('wellkeeper', other=True)
        invoice = self.invoice(first)
        self.assertEqual(self.reconcile(first, invoice).status_code, 200)
        page = self.get('/v1/commerce/orders/pending?limit=1').json()
        self.assertTrue(page['hasMore'])
        self.assertEqual(page['orders'][0]['orderId'], first['orderId'])
        next_page = self.get('/v1/commerce/orders/pending?limit=1&after=' + str(page['nextCursor'])).json()
        self.assertEqual(next_page['orders'][0]['orderId'], second['orderId'])
        self.assertFalse(next_page['hasMore'])
        self.provider.values[invoice] = replace(self.provider.values[invoice], acknowledgement='ACKNOWLEDGED')
        self.assertEqual(self.reconcile(first, invoice).json()['deliveryAcknowledgement'], 'Acknowledged')
        self.assertEqual([o['orderId'] for o in self.get('/v1/commerce/orders/pending').json()['orders']], [second['orderId']])
        for query in ('limit=101', 'limit=0', 'after=-1', 'after=9223372036854775808'):
            self.assertEqual(self.get('/v1/commerce/orders/pending?' + query).status_code, 422)
        self.assertEqual(self.client.get('/v1/commerce/orders/pending').status_code, 401)

    def test_pending_byte_budget_pages_full_order_histories_without_skips(self):
        actor = self.authority.authenticate(self.identity['token'])
        orders = [self.commerce.create(actor, CreateCommerceOrder(commandId=fixtures.ident(), productId='village')) for _ in range(7)]
        # Worst-case bounded order verification histories, including maximum
        # invoice IDs and error codes; no payment is inferred from these hints.
        with self.authority.database.transaction() as db:
            for order in orders:
                for index in range(100):
                    db.execute('''INSERT INTO commerce_invoice_requests(order_id,invoice_id,state,last_error,attempts,updated_at)
                        VALUES(?,?,?,?,?,?)''', (order['orderId'], str(10**29 + index), 'Unavailable', 'x' * 64, 1, self.now))
        seen, cursor, pages = [], 0, 0
        while True:
            response = self.get('/v1/commerce/orders/pending?limit=100&after=' + str(cursor))
            self.assertEqual(response.status_code, 200)
            self.assertLessEqual(len(response.content), 48 * 1024)
            page = response.json()
            self.assertTrue(page['orders'])
            self.assertGreater(page['nextCursor'], cursor)
            seen.extend(order['orderId'] for order in page['orders'])
            pages += 1
            cursor = page['nextCursor']
            if not page['hasMore']:
                break
            self.assertLess(pages, 10)
        self.assertGreater(pages, 1)
        self.assertEqual(seen, [order['orderId'] for order in orders])

    def test_pending_count_limit_pages_more_than_one_hundred_orders(self):
        actor = self.authority.authenticate(self.identity['token'])
        orders = [self.commerce.create(actor, CreateCommerceOrder(commandId=fixtures.ident(), productId='village')) for _ in range(101)]
        seen, cursor = [], 0
        while True:
            response = self.get('/v1/commerce/orders/pending?limit=100&after=' + str(cursor))
            self.assertEqual(response.status_code, 200)
            self.assertLessEqual(len(response.content), 48 * 1024)
            page = response.json()
            seen.extend(order['orderId'] for order in page['orders'])
            if not page['hasMore']:
                break
            self.assertGreater(page['nextCursor'], cursor)
            cursor = page['nextCursor']
        self.assertEqual(seen, [order['orderId'] for order in orders])

    def test_deleted_player_cannot_receive_bundle_or_reopen_eligibility(self):
        order, before = self.create('wellkeeper'), self.wallet()
        invoice = self.invoice(order)
        def delete_during_lookup():
            with self.authority.database.transaction() as db:
                db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.identity['playerId'], self.now))
        self.provider.observer = delete_during_lookup
        self.assertEqual(self.reconcile(order, invoice).status_code, 410)
        self.provider.observer = None
        self.restart()
        self.assertEqual(self.get('/v1/commerce/orders/pending').status_code, 410)
        self.assertEqual(self.count('commerce_credits'), 0)
        self.assertEqual(self.entitlements()[0]['state'], 'Reserved')
        with self.authority.database.connect() as db:
            balances = json.loads(db.execute('SELECT balances FROM wallets WHERE player_id=?', (self.identity['playerId'],)).fetchone()[0])
        self.assertEqual(balances[0], before['coins'])
        self.assertEqual(balances[2:6], before['starting'])

    def test_full_inventory_snapshot_backup_and_new_file_restore(self):
        order = self.create('wellkeeper')
        self.assertEqual(self.reconcile(order, self.invoice(order)).status_code, 200)
        snapshot, restored = self.path / 'snapshot.sqlite3', self.path / 'restored.sqlite3'
        self.assertEqual(backup_database(self.database_path, snapshot)['schemaVersion'], SCHEMA_VERSION)
        self.assertEqual(restore_database(snapshot, restored)['schemaVersion'], SCHEMA_VERSION)
        with Database(restored).connect() as db:
            self.assertEqual(db.execute('SELECT state FROM commerce_entitlements').fetchone()[0], 'Consumed')
            self.assertEqual(json.loads(db.execute('SELECT grant_json FROM commerce_credits').fetchone()[0]), SPECIAL['grant'])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])


class FullGrantMigration100Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-commerce8-9-')
        self.root = Path(self.temp.name)
        self.path = self.root / 'schema8.sqlite3'
        self.player, self.order = fixtures.ident(), fixtures.ident()
        # Build the exact previously supported schema, including its original
        # ALTER TABLE definitions. No schema9 constructor is used to fake it.
        with closing(sqlite3.connect(self.path)) as db:
            objects = _expected(8)
            for kind in ('table', 'index'):
                for typ, _, _, sql in objects:
                    if typ == kind:
                        db.execute(sql)
            db.execute('INSERT INTO schema_info VALUES(8)')
            db.execute('INSERT INTO clock_state VALUES(1,0)')
            db.execute('INSERT INTO players(id,reward_totals,created_at) VALUES(?,?,?)', (self.player, canonical([0] * 10), 100))
            db.execute('''INSERT INTO commerce_orders
                (id,player_id,catalog_version,internal_product,store_product,app_id,sandbox,amount_minor,currency,coins,binding,state,invoice_id,purchase_id,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                       (self.order, self.player, 'legacy8', 'coins-1000', 'hotr_coins_1000', 123, 1, 9900, 'RUB', 1000,
                        'synthetic-legacy-binding', 'Confirmed', '1001', fixtures.ident(), 100, 100))
            purchase = db.execute('SELECT purchase_id FROM commerce_orders').fetchone()[0]
            db.execute('INSERT INTO commerce_credits VALUES(?,?,?,?,?,?,?,?,?)',
                       ('legacy8-credit', self.order, self.player, 123, 1, '1001', purchase, 1000, 100))
            db.commit()

    def tearDown(self):
        self.temp.cleanup()

    def test_schema8_snapshot_restore_then_additive_grant_backfill(self):
        backup, restored = self.root / 'old.sqlite3', self.root / 'restored.sqlite3'
        self.assertEqual(backup_database(self.path, backup)['schemaVersion'], 8)
        restored_view = restore_database(backup, restored)
        self.assertEqual(restored_view['schemaVersion'], 8)
        self.assertTrue(restored_view['requiresMigration'])
        database = Database(restored)
        zero_items = {'coins': 1000, 'stars': 0, 'starting': [0] * 4, 'tools': [0] * 4}
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], SCHEMA_VERSION)
            for table in ('commerce_orders', 'commerce_credits'):
                row = db.execute('SELECT * FROM ' + table).fetchone()
                self.assertEqual(json.loads(row['grant_json']), zero_items)
                self.assertEqual(row['coins'], 1000)
            self.assertIsNone(db.execute('SELECT creation_command_id FROM commerce_orders').fetchone()[0])
            self.assertIsNone(db.execute('SELECT purchase_limit FROM commerce_orders').fetchone()[0])
            self.assertEqual(db.execute('SELECT reservation_released FROM commerce_orders').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_entitlements').fetchone()[0], 0)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        Database(restored)
        self.assertEqual(backup_database(restored, self.root / 'new.sqlite3')['schemaVersion'], SCHEMA_VERSION)

    def test_partial_schema9_migration_rolls_back_existing_financial_rows(self):
        with patch('hotr_backend.commerce_schema.COMMERCE_V9_DDL', COMMERCE_V9_DDL + '\nINVALID MIGRATION;'):
            with self.assertRaises(sqlite3.Error):
                Database(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 8)
            self.assertEqual(db.execute('SELECT id,coins FROM commerce_credits').fetchall(), [('legacy8-credit', 1000)])
            self.assertNotIn('grant_json', [row[1] for row in db.execute('PRAGMA table_info(commerce_orders)')])
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='commerce_entitlements'").fetchone())
        self.assertEqual(backup_database(self.path, self.root / 'rollback.sqlite3')['schemaVersion'], 8)
        Database(self.path)


if __name__ == '__main__':
    unittest.main()
