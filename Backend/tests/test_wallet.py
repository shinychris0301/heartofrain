"""Real portable-server/SQLite state tests, with synthetic upstream attestations.

No Unity, device, real provider payment, account-linking or board-replay proof is
implied. The production factory remains disabled; test purchases use a provider
double and verifier credentials provisioned only inside a temporary database.
"""
import concurrent.futures
import hashlib
import json
import re
import sqlite3
import tempfile
import threading
import unittest
import uuid
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.rustore_provider import VerifiedInvoice
from hotr_backend.storage import COMMERCE_V2, DDL, SCHEMA_VERSION, WALLET_V3
from hotr_backend.service import ServiceError
from hotr_backend.wallet_schemas import SettleAttempt

CONFIG = Path(__file__).resolve().parents[1] / 'config'
PROJECT = Path(__file__).resolve().parents[2]


def ident():
    return uuid.uuid4().hex


class Provider:
    configured = True

    def __init__(self):
        self.invoices = {}

    def lookup(self, invoice_id, sandbox):
        return self.invoices[invoice_id]


class WalletTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-wallet-')
        self.path = Path(self.temp.name)
        self.now = 300 * 86400
        self.provider = Provider()
        self.commerce_config = self.path / 'commerce.json'
        self.commerce_config.write_text(json.dumps({
            'version': 'synthetic-wallet-test-v1', 'enabled': True, 'appId': 123,
            'sandbox': True, 'products': [{'id': 'fixture_coins', 'storeProductId': 'synthetic_3000',
                                         'enabled': True, 'coins': 3000,
                                         'amountMinor': 19900, 'currency': 'RUB'}]}), encoding='utf-8')
        self.database_path = self.path / 'authority.sqlite3'
        self.open()
        self.identity = self.authority.provision()
        self.other = self.authority.provision()
        self.verifier = self.authority.provision(role='verifier')
        self.sequence = 1000

    def open(self):
        self.app = create_app(self.database_path, CONFIG, lambda: self.now,
                              commerce_provider=self.provider, commerce_config_path=self.commerce_config)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.authority = self.app.state.authority
        self.wallet_service = self.app.state.wallet

    def restart(self):
        self.client.close()
        self.open()

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def headers(self, identity=None):
        return {'Authorization': 'Bearer ' + (identity or self.identity)['token']}

    def get(self, path, identity=None):
        return self.client.get(path, headers=self.headers(identity))

    def post(self, path, value, identity=None):
        return self.client.post(path, json=value, headers=self.headers(identity))

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def wallet(self, identity=None):
        return self.ok(self.get('/v1/wallet', identity))

    def request(self, **extra):
        return {'commandId': ident(), 'expectedRevision': self.wallet()['revision'], **extra}

    def reserve(self, starting=None, level=1):
        body = self.request(level=level, starting=starting or [0, 0, 0, 0])
        return self.ok(self.post('/v1/attempts/reserve', body))

    def command(self, attempt, operation, **extra):
        return self.ok(self.post('/v1/attempts/' + attempt['attemptId'] + '/' + operation,
                                 self.request(**extra)))

    def started(self, starting=None):
        return self.command(self.reserve(starting)['attempt'], 'start')['attempt']

    def settlement_body(self, attempt, outcome, **extra):
        return self.request(playerId=self.identity['playerId'], attemptId=attempt['attemptId'],
                            outcome=outcome, proofDigest='a' * 64, **extra)

    def settle(self, attempt, outcome):
        return self.ok(self.post('/internal/v1/attempts/settle', self.settlement_body(attempt, outcome), self.verifier))

    def fund(self):
        order = self.ok(self.post('/v1/commerce/orders', {'commandId': ident(), 'productId': 'fixture_coins'}))
        self.sequence += 1
        invoice_id = str(self.sequence)
        self.provider.invoices[invoice_id] = VerifiedInvoice(
            invoice_id, str(uuid.uuid4()), 123, True, order['orderId'], order['sdk']['productId'],
            self.identity['playerId'], order['sdk']['developerPayload'], order['amountMinor'],
            order['currency'], 'CONFIRMED', 'PENDING')
        view = self.ok(self.post('/v1/commerce/orders/' + order['orderId'] + '/reconcile', {'invoiceId': invoice_id}))
        return order, invoice_id, view

    def ledger(self):
        rows, cursor = [], 0
        while True:
            page = self.ok(self.get('/v1/wallet/ledger?after=' + str(cursor) + '&limit=100'))
            rows.extend(page['entries'])
            if not page['hasMore']:
                return rows
            self.assertGreater(page['nextCursor'], cursor)
            cursor = page['nextCursor']

    def reconciles(self):
        wallet, rows = self.wallet(), self.ledger()
        total = [sum(row['delta'][i] for row in rows) for i in range(11)]
        self.assertEqual(total, [wallet['coins'], wallet['stars'], *wallet['starting'], *wallet['tools'], wallet['lives']])
        self.assertEqual(len({r['origin'] for r in rows}), len(rows))
        self.assertEqual(len({r['receiptId'] for r in rows}), len(rows))
        self.assertEqual([r['revision'] for r in rows], list(range(1, wallet['revision'] + 1)))

    def lose_lives(self, count):
        for _ in range(count):
            self.command(self.started(), 'quit')

    def test_01_genesis_once_isolated_and_explicit_staging_scope(self):
        wallet = self.wallet()
        self.assertTrue(wallet['initialized'])
        self.assertEqual((wallet['coins'], wallet['stars'], wallet['lives'], wallet['maxLives']), (1250, 0, 5, 5))
        self.assertEqual(wallet['starting'], [5, 5, 3, 2])
        self.assertEqual(wallet['tools'], [3, 3, 3, 3])
        self.assertIsNone(wallet['activeAttempt'])
        self.assertFalse(wallet['productionEnabled'])
        self.assertFalse(wallet['normalUnityProfileIntegrated'])
        self.assertFalse(wallet['localProfileMutated'])
        self.assertEqual(self.ledger()[0]['origin'], 'genesis/v1')
        self.assertEqual(self.wallet(), wallet)
        replacement = self.authority.provision(player=self.identity['playerId'])
        self.assertEqual(self.wallet(replacement), wallet)
        self.restart()
        self.assertEqual(self.wallet(), wallet)
        self.reconciles()

    def test_02_all_50_level_contracts_match_approved_source_and_rewards(self):
        catalog = json.loads((CONFIG / 'levels.json').read_text('utf-8-sig'))
        self.assertEqual([r['level'] for r in catalog['levels']], list(range(1, 51)))
        for row in catalog['levels']:
            source = (PROJECT / row['source']).resolve()
            self.assertTrue(source.is_relative_to(PROJECT))
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), row['sourceSHA256'])
            self.assertEqual(row['configHash'], row['sourceSHA256'])
            level = json.loads(source.read_text('utf-8-sig'))
            self.assertEqual(row['moves'], level['movesProposal'])
            self.assertEqual(row['goals'], level['goals'])
            self.assertEqual(row['tileSeed'], level['tileSeed'])
            self.assertEqual(row['reward'], {'coins': 50, 'stars': 1})
        prelevel = (PROJECT / catalog['rewardSource']).read_text('utf-8-sig')
        self.assertRegex(prelevel, r'(?m)^\s*rewardCoins:\s*50\s*$')
        self.assertRegex(prelevel, r'(?m)^\s*rewardStars:\s*1\s*$')

    def test_03_authentication_and_attempt_ownership(self):
        self.assertEqual(self.client.get('/v1/wallet').status_code, 401)
        self.assertEqual(self.get('/v1/wallet', self.verifier).status_code, 403)
        attempt = self.started()
        self.assertEqual(self.get('/v1/attempts/' + attempt['attemptId'], self.other).status_code, 404)
        body = {'commandId': ident(), 'expectedRevision': self.wallet(self.other)['revision']}
        self.assertEqual(self.post('/v1/attempts/' + attempt['attemptId'] + '/quit', body, self.other).status_code, 404)
        self.assertEqual(self.post('/internal/v1/attempts/settle', self.settlement_body(attempt, 'Won')).status_code, 403)
        self.assertEqual(self.post('/internal/v1/attempts/settle', self.settlement_body(attempt, 'Won'), self.other).status_code, 403)
        self.assertEqual(self.wallet()['activeAttempt']['state'], 'Started')

    def test_04_client_cannot_import_balances_or_choose_outcomes_metadata(self):
        baseline = self.wallet()
        for field, value in [('coins', 999999), ('stars', 5), ('lives', 99), ('seed', 1),
                             ('configHash', 'b' * 64), ('moves', 999), ('reward', {'coins': 999}),
                             ('playerId', self.other['playerId'])]:
            body = self.request(level=1, starting=[0] * 4, **{field: value})
            self.assertEqual(self.post('/v1/attempts/reserve', body).status_code, 422)
        for value in [-1, True, '1', 9_223_372_036_854_775_808]:
            body = {'commandId': ident(), 'expectedRevision': value, 'level': 1, 'starting': [0] * 4}
            self.assertEqual(self.post('/v1/attempts/reserve', body).status_code, 422)
        for value in [[0] * 3, [0] * 5, [2, 0, 0, 0], [True, 0, 0, 0]]:
            self.assertEqual(self.post('/v1/attempts/reserve', self.request(level=1, starting=value)).status_code, 422)
        self.assertEqual(self.wallet(), baseline)

    def test_05_reserve_is_not_debit_and_only_one_active_attempt(self):
        before = self.wallet()
        reserved = self.reserve([1, 0, 1, 0])
        attempt = reserved['attempt']
        self.assertEqual(attempt['state'], 'Reserved')
        self.assertRegex(attempt['attemptId'], r'^[0-9a-f]{32}$')
        self.assertGreater(attempt['seed'], 0)
        self.assertEqual(attempt['reward'], {'coins': 50, 'stars': 1})
        self.assertEqual(reserved['wallet']['starting'], before['starting'])
        self.assertEqual(reserved['wallet']['lives'], before['lives'])
        self.assertEqual(self.post('/v1/attempts/reserve', self.request(level=1, starting=[0] * 4)).status_code, 409)
        self.assertEqual(self.post('/v1/attempts/reserve', self.request(level=2, starting=[0] * 4)).status_code, 409)
        self.reconciles()

    def test_06_start_receipt_debits_selected_rocket_separately_once(self):
        attempt = self.reserve([1, 0, 0, 0])['attempt']
        body = self.request()
        first = self.ok(self.post('/v1/attempts/' + attempt['attemptId'] + '/start', body))
        self.assertEqual(first['wallet']['starting'], [4, 5, 3, 2])
        self.assertEqual(first['wallet']['lives'], 5)
        self.assertEqual(self.ok(self.post('/v1/attempts/' + attempt['attemptId'] + '/start', body)), first)
        self.assertEqual(self.post('/v1/attempts/' + attempt['attemptId'] + '/start', self.request()).status_code, 409)
        self.reconciles()

    def test_07_reserved_cancel_and_confirmed_loss_settle_once(self):
        reserved = self.reserve([1, 1, 0, 0])['attempt']
        canceled = self.command(reserved, 'quit')
        self.assertEqual(canceled['attempt']['state'], 'Cancelled')
        self.assertEqual(canceled['wallet']['lives'], 5)
        self.assertEqual(canceled['wallet']['starting'], [5, 5, 3, 2])
        started = self.started()
        body = self.request()
        lost = self.ok(self.post('/v1/attempts/' + started['attemptId'] + '/quit', body))
        self.assertEqual(lost['attempt']['state'], 'Lost')
        self.assertEqual(lost['wallet']['lives'], 4)
        self.assertEqual(lost['wallet']['nextLifeAt'], self.now + 1800)
        self.assertEqual(self.ok(self.post('/v1/attempts/' + started['attemptId'] + '/quit', body)), lost)
        self.assertEqual(self.post('/v1/attempts/' + started['attemptId'] + '/quit', self.request()).status_code, 409)
        self.reconciles()

    def test_08_tool_debit_is_typed_idempotent_and_started_only(self):
        reserved = self.reserve()['attempt']
        self.assertEqual(self.post('/v1/attempts/' + reserved['attemptId'] + '/tools', self.request(tool=0)).status_code, 409)
        attempt = self.command(reserved, 'start')['attempt']
        body = self.request(tool=1)
        first = self.ok(self.post('/v1/attempts/' + attempt['attemptId'] + '/tools', body))
        self.assertEqual(first['wallet']['tools'], [3, 2, 3, 3])
        self.assertEqual(self.ok(self.post('/v1/attempts/' + attempt['attemptId'] + '/tools', body)), first)
        changed = dict(body, tool=2)
        self.assertEqual(self.post('/v1/attempts/' + attempt['attemptId'] + '/tools', changed).status_code, 409)
        for value in [-1, 4, True, '1']:
            self.assertEqual(self.post('/v1/attempts/' + attempt['attemptId'] + '/tools', self.request(tool=value)).status_code, 422)
        self.reconciles()

    def test_09_fault_refunds_starting_once_but_not_spent_tools(self):
        attempt = self.started([1, 0, 1, 0])
        self.command(attempt, 'tools', tool=0)
        body = self.settlement_body(attempt, 'Fault')
        first = self.ok(self.post('/internal/v1/attempts/settle', body, self.verifier))
        self.assertEqual(first['attempt']['state'], 'Released')
        self.assertEqual(first['wallet']['starting'], [5, 5, 3, 2])
        self.assertEqual(first['wallet']['tools'], [2, 3, 3, 3])
        self.assertEqual(first['wallet']['lives'], 5)
        self.assertEqual(self.ok(self.post('/internal/v1/attempts/settle', body, self.verifier)), first)
        self.assertEqual(self.post('/internal/v1/attempts/settle', self.settlement_body(attempt, 'Won'), self.verifier).status_code, 409)
        self.reconciles()

    def test_10_final_move_victory_and_replay_do_not_double_reward(self):
        attempt = self.started()
        self.settle(attempt, 'OutOfMoves')
        body = self.settlement_body(attempt, 'Won')
        first = self.ok(self.post('/internal/v1/attempts/settle', body, self.verifier))
        self.assertEqual((first['wallet']['coins'], first['wallet']['stars'], first['wallet']['completed']), (1300, 1, 1))
        self.assertEqual(first['wallet']['lives'], 5)
        self.assertIsNone(first['wallet']['activeAttempt'])
        self.assertEqual(self.ok(self.post('/internal/v1/attempts/settle', body, self.verifier)), first)
        replay = self.started()
        second = self.settle(replay, 'Won')
        self.assertEqual((second['wallet']['coins'], second['wallet']['stars'], second['wallet']['completed']), (1300, 1, 1))
        self.reconciles()

    def test_11_topup_does_not_automatically_continue_and_repeats_cost_900(self):
        attempt = self.started()
        waiting = self.settle(attempt, 'OutOfMoves')['attempt']
        self.fund()
        self.assertEqual(self.wallet()['activeAttempt']['state'], 'AwaitingContinuation')
        self.assertEqual(self.wallet()['coins'], 4250)
        initial_moves = waiting['moves']
        for ordinal in [1, 2]:
            body = self.request()
            first = self.ok(self.post('/v1/attempts/' + attempt['attemptId'] + '/continue', body))
            self.assertEqual(first['wallet']['coins'], 4250 - 900 * ordinal)
            self.assertEqual(first['wallet']['lives'], 5)
            self.assertEqual(first['attempt']['moves'], initial_moves + 5 * ordinal)
            self.assertEqual(first['attempt']['continues'], ordinal)
            self.assertEqual((first['attempt']['seed'], first['attempt']['configHash']), (attempt['seed'], attempt['configHash']))
            self.assertEqual(self.ok(self.post('/v1/attempts/' + attempt['attemptId'] + '/continue', body)), first)
            if ordinal == 1:
                self.settle(attempt, 'OutOfMoves')
        self.reconciles()

    def test_12_insufficient_continue_is_atomic(self):
        attempt = self.started()
        self.settle(attempt, 'OutOfMoves')
        self.command(attempt, 'continue')
        self.settle(attempt, 'OutOfMoves')
        before = self.wallet()
        self.assertEqual(before['coins'], 350)
        self.assertEqual(self.post('/v1/attempts/' + attempt['attemptId'] + '/continue', self.request()).status_code, 409)
        self.assertEqual(self.wallet(), before)
        self.reconciles()

    def test_13_zero_life_refill_costs_exactly_900_and_replays_once(self):
        self.lose_lives(5)
        before = self.wallet()
        self.assertEqual(before['lives'], 0)
        self.assertIsNone(before['activeAttempt'])
        self.assertEqual(self.post('/v1/attempts/reserve', self.request(level=1, starting=[0] * 4)).status_code, 409)
        body = self.request()
        first = self.ok(self.post('/v1/wallet/refill', body))
        self.assertEqual((first['wallet']['coins'], first['wallet']['lives'], first['wallet']['nextLifeAt']), (350, 5, 0))
        self.assertEqual(self.ok(self.post('/v1/wallet/refill', body)), first)
        self.assertEqual(first['wallet']['starting'], before['starting'])
        self.lose_lives(5)
        before = self.wallet()
        self.assertEqual(self.post('/v1/wallet/refill', self.request()).status_code, 409)
        self.assertEqual(self.wallet(), before)
        self.reconciles()

    def test_14_life_deadline_is_retained_and_regenerates_to_cap(self):
        self.lose_lives(1)
        due = self.wallet()['nextLifeAt']
        self.now += 30
        self.lose_lives(1)
        self.assertEqual(self.wallet()['nextLifeAt'], due)
        self.now = due - 1
        self.assertEqual(self.wallet()['lives'], 3)
        self.now = due
        self.assertEqual((self.wallet()['lives'], self.wallet()['nextLifeAt']), (4, due + 1800))
        self.now += 1800 * 10
        self.assertEqual((self.wallet()['lives'], self.wallet()['nextLifeAt']), (5, 0))
        self.reconciles()

    def test_15_stale_revision_and_changed_idempotency_payload_rejected(self):
        body = self.request(level=1, starting=[0] * 4)
        first = self.ok(self.post('/v1/attempts/reserve', body))
        stale = dict(body, commandId=ident())
        self.assertEqual(self.post('/v1/attempts/reserve', stale).status_code, 409)
        self.assertEqual(self.post('/v1/attempts/reserve', dict(body, starting=[1, 0, 0, 0])).status_code, 409)
        self.assertEqual(self.ok(self.post('/v1/attempts/reserve', body)), first)
        self.reconciles()

    def test_16_concurrent_same_command_and_competing_reservations(self):
        body = self.request(level=1, starting=[0] * 4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            responses = list(pool.map(lambda _: self.post('/v1/attempts/reserve', body), range(6)))
        values = [self.ok(r) for r in responses]
        self.assertTrue(all(v == values[0] for v in values))
        self.command(values[0]['attempt'], 'quit')
        revision = self.wallet()['revision']
        bodies = [{'commandId': ident(), 'expectedRevision': revision, 'level': 1, 'starting': [0] * 4} for _ in range(2)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda b: self.post('/v1/attempts/reserve', b), bodies))
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])
        self.reconciles()

    def test_17_concurrent_continue_spends_once(self):
        attempt = self.started()
        self.settle(attempt, 'OutOfMoves')
        body = self.request()
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            values = [self.ok(r) for r in pool.map(lambda _: self.post('/v1/attempts/' + attempt['attemptId'] + '/continue', body), range(6))]
        self.assertTrue(all(v == values[0] for v in values))
        self.assertEqual(self.wallet()['coins'], 350)
        self.assertEqual(self.wallet()['activeAttempt']['continues'], 1)
        self.reconciles()

    def test_18_wallet_transaction_faults_rollback_or_recover_exact_receipt(self):
        for operation in ['start', 'continue', 'settle']:
            for cut in ['BeforeCommit', 'AfterCommit']:
                with self.subTest(operation=operation, cut=cut):
                    self.identity = self.authority.provision()
                    reserved = self.reserve([1, 0, 0, 0])['attempt']
                    if operation == 'start':
                        path = '/v1/attempts/' + reserved['attemptId'] + '/start'
                        body, identity = self.request(), self.identity
                    else:
                        self.command(reserved, 'start')
                        if operation == 'continue':
                            self.settle(reserved, 'OutOfMoves')
                            path, body, identity = '/v1/attempts/' + reserved['attemptId'] + '/continue', self.request(), self.identity
                        else:
                            path, body, identity = '/internal/v1/attempts/settle', self.settlement_body(reserved, 'Won'), self.verifier
                    before = self.wallet()
                    def fail(stage):
                        if stage == cut:
                            raise RuntimeError('synthetic wallet transaction cut')
                    self.wallet_service.checkpoint = fail
                    self.assertEqual(self.post(path, body, identity).status_code, 500)
                    self.wallet_service.checkpoint = None
                    if cut == 'BeforeCommit':
                        self.assertEqual(self.wallet(), before)
                    self.restart()
                    committed = self.ok(self.post(path, body, identity))
                    self.assertEqual(self.ok(self.post(path, body, identity)), committed)
                    wallet = self.wallet()
                    if operation == 'continue':
                        self.assertEqual(wallet['coins'], 350)
                        self.assertEqual(wallet['activeAttempt']['continues'], 1)
                    elif operation == 'settle':
                        self.assertEqual((wallet['coins'], wallet['stars'], wallet['completed']), (1300, 1, 1))
                    else:
                        self.assertEqual(wallet['starting'], [4, 5, 3, 2])
                    self.reconciles()

    def test_19_trusted_gift_projects_once_and_survives_restart(self):
        offer = self.ok(self.get('/v1/daily-gift/offer'))
        body = {'requestId': ident(), 'offerId': offer['id'], 'day': offer['day'], 'step': offer['step'],
                'schedule': offer['schedule'], 'expectedGrant': offer['grant']}
        first = self.ok(self.post('/v1/daily-gift/claim', body))
        after = self.wallet()
        self.assertEqual(after['coins'], 1250 + offer['grant']['coins'])
        self.assertEqual(self.ok(self.post('/v1/daily-gift/claim', body)), first)
        self.restart()
        self.assertEqual(self.wallet(), after)
        self.assertEqual(sum(r['origin'] == 'reward/' + first['receiptId'] for r in self.ledger()), 1)
        self.reconciles()

    def test_20_purchase_projection_and_refund_quarantine(self):
        # A second prepaid order exists before quarantine; fulfillment must not
        # be disabled together with new checkout or ordinary spending.
        pending = self.ok(self.post('/v1/commerce/orders', {'commandId': ident(), 'productId': 'fixture_coins'}))
        order, invoice_id, receipt = self.fund()
        self.assertEqual(self.wallet()['coins'], 4250)
        self.assertTrue(receipt['availableToSpend'])
        self.assertEqual(self.ok(self.post('/v1/commerce/orders/' + order['orderId'] + '/reconcile', {'invoiceId': invoice_id}))['credit'], receipt['credit'])
        self.provider.invoices[invoice_id] = replace(self.provider.invoices[invoice_id], status='REFUNDED')
        self.ok(self.post('/v1/commerce/orders/' + order['orderId'] + '/reconcile', {'invoiceId': invoice_id}))
        self.assertTrue(self.wallet()['refundReviewRequired'])
        self.assertEqual(self.post('/v1/attempts/reserve', self.request(level=1, starting=[0] * 4)).status_code, 409)
        self.assertEqual(self.post('/v1/wallet/refill', self.request()).status_code, 409)
        self.assertEqual(self.post('/v1/commerce/orders', {'commandId': ident(), 'productId': 'fixture_coins'}).status_code, 409)
        self.restart()
        self.assertTrue(self.wallet()['refundReviewRequired'])
        self.assertEqual(self.wallet()['coins'], 4250)
        self.assertEqual(sum(r['origin'] == 'commerce/' + receipt['credit']['receiptId'] for r in self.ledger()), 1)
        self.sequence += 1
        later = str(self.sequence)
        self.provider.invoices[later] = VerifiedInvoice(later, str(uuid.uuid4()), 123, True, pending['orderId'], pending['sdk']['productId'], self.identity['playerId'], pending['sdk']['developerPayload'], pending['amountMinor'], pending['currency'], 'CONFIRMED', 'PENDING')
        self.assertEqual(self.post('/v1/commerce/orders/' + pending['orderId'] + '/reconcile', {'invoiceId': later}).status_code, 200)
        self.assertTrue(self.wallet()['refundReviewRequired'])
        self.reconciles()

    def test_21_ledger_pagination_bounds_and_player_isolation(self):
        self.command(self.reserve()['attempt'], 'quit')
        first = self.ok(self.get('/v1/wallet/ledger?limit=1'))
        self.assertTrue(first['hasMore'])
        second = self.ok(self.get('/v1/wallet/ledger?limit=1&after=' + str(first['nextCursor'])))
        self.assertNotEqual(first['entries'][0]['receiptId'], second['entries'][0]['receiptId'])
        other = self.ok(self.get('/v1/wallet/ledger', self.other))
        self.assertEqual(len(other['entries']), 1)
        for query in ['after=-1', 'after=' + str(2 ** 63), 'limit=0', 'limit=101']:
            self.assertEqual(self.get('/v1/wallet/ledger?' + query).status_code, 422)
        self.reconciles()

    def test_24_refund_quarantine_allows_existing_exit_or_trusted_final_settlement(self):
        for outcome in ['quit', 'Won', 'Lost', 'Fault']:
            with self.subTest(outcome=outcome):
                self.identity = self.authority.provision()
                attempt = self.started([1, 0, 0, 0])
                order, invoice_id, _ = self.fund()
                self.provider.invoices[invoice_id] = replace(self.provider.invoices[invoice_id], status='REFUNDED')
                self.ok(self.post('/v1/commerce/orders/' + order['orderId'] + '/reconcile', {'invoiceId': invoice_id}))
                self.assertTrue(self.wallet()['refundReviewRequired'])
                self.assertEqual(self.post('/v1/attempts/' + attempt['attemptId'] + '/tools', self.request(tool=0)).status_code, 409)
                if outcome == 'quit':
                    path = '/v1/attempts/' + attempt['attemptId'] + '/quit'
                    body, identity = self.request(), self.identity
                else:
                    path, body, identity = '/internal/v1/attempts/settle', self.settlement_body(attempt, outcome), self.verifier
                first = self.ok(self.post(path, body, identity))
                self.assertEqual(self.ok(self.post(path, body, identity)), first)
                self.assertTrue(first['wallet']['refundReviewRequired'])
                self.assertIsNone(first['wallet']['activeAttempt'])
                self.assertEqual(first['wallet']['lives'], 4 if outcome in ('quit', 'Lost') else 5)
                self.assertEqual(first['wallet']['starting'][0], 5 if outcome == 'Fault' else 4)
                self.assertEqual(self.post('/v1/attempts/reserve', self.request(level=1, starting=[0] * 4)).status_code, 409)
                self.assertEqual(self.post('/v1/commerce/orders', {'commandId': ident(), 'productId': 'fixture_coins'}).status_code, 409)
                self.restart()
                self.assertTrue(self.wallet()['refundReviewRequired'])
                self.reconciles()


    def test_25_verifier_revoked_after_authentication_cannot_settle(self):
        attempt = self.started()
        body = self.settlement_body(attempt, 'Won')
        stale = self.authority.authenticate(self.verifier['token'], 'verifier')
        before = self.wallet()
        self.authority.revoke(self.verifier['token'])
        with self.assertRaises(ServiceError) as error:
            self.wallet_service.settle(stale, SettleAttempt(**body))
        self.assertEqual(error.exception.status, 401)
        self.assertEqual(self.wallet(), before)
        self.assertEqual(self.wallet()['activeAttempt']['state'], 'Started')
        self.reconciles()

    def test_26_revoked_verifier_cannot_read_cached_settlement_receipt(self):
        attempt = self.started()
        body = self.settlement_body(attempt, 'Lost')
        stale = self.authority.authenticate(self.verifier['token'], 'verifier')
        first = self.wallet_service.settle(stale, SettleAttempt(**body))
        self.authority.revoke(self.verifier['token'])
        with self.assertRaises(ServiceError) as error:
            self.wallet_service.settle(stale, SettleAttempt(**body))
        self.assertEqual(error.exception.status, 401)
        fresh = self.authority.provision(player=self.verifier['playerId'], role='verifier')
        actor = self.authority.authenticate(fresh['token'], 'verifier')
        self.assertEqual(self.wallet_service.settle(actor, SettleAttempt(**body)), first)
        self.assertEqual(self.wallet()['lives'], 4)
        self.reconciles()

    def test_27_private_reads_see_guard_and_payload_in_one_snapshot_beside_deletion(self):
        from hotr_backend.wallet import require_actor as real_guard
        for operation in ('ledger', 'attempt'):
            with self.subTest(operation=operation):
                self.identity = self.authority.provision()
                attempt = self.started()
                actor = self.authority.authenticate(self.identity['token'])
                checked, release = threading.Event(), threading.Event()
                deletion_started, deletion_committed = threading.Event(), threading.Event()
                def guarded(db, value):
                    real_guard(db, value)
                    self.assertTrue(db.in_transaction, 'Guard and private payload require one transaction')
                    checked.set()
                    if not release.wait(timeout=10):
                        raise RuntimeError('controlled private read hold timed out')
                def read():
                    if operation == 'ledger':
                        return self.wallet_service.ledger(actor)
                    return self.wallet_service.attempt(actor, attempt['attemptId'])
                def delete():
                    deletion_started.set()
                    with self.authority.database.transaction(timeout=5) as db:
                        db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (actor.player, self.now))
                        db.execute('UPDATE credentials SET revoked=1 WHERE player_id=?', (actor.player,))
                    deletion_committed.set()
                with patch('hotr_backend.wallet.require_actor', guarded):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                        pending = pool.submit(read)
                        try:
                            self.assertTrue(checked.wait(timeout=5))
                            deleting = pool.submit(delete)
                            self.assertTrue(deletion_started.wait(timeout=5))
                            # A snapshot read no longer blocks deletion. It answers wholly from
                            # before the deletion, and the very next read is refused below.
                            self.assertTrue(deletion_committed.wait(timeout=5))
                        finally:
                            release.set()
                        result = pending.result(timeout=5)
                        deleting.result(timeout=5)
                self.assertTrue(deletion_committed.is_set())
                if operation == 'ledger':
                    self.assertTrue(result['entries'])
                else:
                    self.assertEqual(result['attemptId'], attempt['attemptId'])
                with self.assertRaises(ServiceError) as error:
                    read()
                self.assertEqual(error.exception.status, 410)


class WalletMigrationTests(unittest.TestCase):
    def legacy(self, path, version):
        player, now = ident(), 100
        with closing(sqlite3.connect(path)) as db:
            db.executescript(DDL)
            grant = {'coins': 50, 'stars': 1, 'starting': [1, 0, 0, 0], 'tools': [0] * 4}
            db.execute('INSERT INTO players(id,reward_totals,created_at) VALUES(?,?,?)', (player, json.dumps([50, 1, 1, 0, 0, 0, 0, 0, 0, 0]), now))
            db.execute('INSERT INTO rewards(id,player_id,source,source_key,grant_json,created_at) VALUES(?,?,?,?,?,?)', ('legacy-reward', player, 'daily_gift', 'legacy-day', json.dumps(grant), now))
            if version == 2:
                db.executescript(COMMERCE_V2)
                db.execute('UPDATE schema_info SET version=2')
                order, purchase, invoice = ident(), str(uuid.uuid4()), '1001'
                db.execute('''INSERT INTO commerce_orders(id,player_id,catalog_version,internal_product,store_product,app_id,sandbox,amount_minor,currency,coins,binding,state,invoice_id,purchase_id,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (order, player, 'legacy', 'legacy-coins', 'legacy_store', 123, 1, 9900, 'RUB', 650, 'hotr-order-v1:' + order + ':' + ident(), 'Confirmed', invoice, purchase, now, now))
                db.execute('INSERT INTO commerce_credits VALUES(?,?,?,?,?,?,?,?,?)', ('legacy-commerce', order, player, 123, 1, invoice, purchase, 650, now))
            db.commit()
        return player

    def test_22_schema1_and_schema2_backfill_only_trusted_receipts_no_genesis(self):
        with tempfile.TemporaryDirectory(prefix='hotr-wallet-migrate-') as temporary:
            commerce = Path(temporary) / 'commerce.json'
            commerce.write_text(json.dumps({'version': 'migration-test', 'enabled': True, 'appId': 123, 'sandbox': True,
                                            'products': [{'id': 'fixture_coins', 'storeProductId': 'synthetic_3000',
                                                          'enabled': True, 'coins': 3000, 'amountMinor': 19900}]}), encoding='utf-8')
            for version in [1, 2]:
                path = Path(temporary) / ('v' + str(version) + '.sqlite3')
                player = self.legacy(path, version)
                for _ in range(2):
                    app = create_app(path, CONFIG, lambda: 1000, commerce_provider=Provider(), commerce_config_path=commerce)
                    identity = app.state.authority.provision(player=player)
                    headers = {'Authorization': 'Bearer ' + identity['token']}
                    with TestClient(app) as client:
                        wallet = client.get('/v1/wallet', headers=headers).json()
                        self.assertFalse(wallet['initialized'])
                        self.assertEqual((wallet['coins'], wallet['stars'], wallet['lives']), (700 if version == 2 else 50, 1, 0))
                        ledger = client.get('/v1/wallet/ledger', headers=headers).json()['entries']
                        self.assertFalse(any(r['origin'] == 'genesis/v1' for r in ledger))
                        self.assertEqual(len(ledger), version)
                        self.assertEqual(client.post('/v1/attempts/reserve', headers=headers, json={'commandId': ident(), 'expectedRevision': wallet['revision'], 'level': 1, 'starting': [0] * 4}).status_code, 409)
                        self.assertEqual(client.post('/v1/commerce/orders', headers=headers, json={'commandId': ident(), 'productId': 'fixture_coins'}).status_code, 409)

    def test_23_wallet_schema_failure_rolls_back_existing_schema2_data(self):
        with tempfile.TemporaryDirectory(prefix='hotr-wallet-rollback-') as temporary:
            path = Path(temporary) / 'v2.sqlite3'
            self.legacy(path, 2)
            with patch('hotr_backend.storage.WALLET_V3', WALLET_V3 + '; INVALID SQL;'):
                with self.assertRaises(sqlite3.Error):
                    create_app(path, CONFIG, lambda: 1000)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 2)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM rewards').fetchone()[0], 1)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name IN ('wallets','wallet_ledger','gameplay_attempts')").fetchone()[0], 0)
            app = create_app(path, CONFIG, lambda: 1000)
            with app.state.authority.database.connect() as db:
                self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], SCHEMA_VERSION)


if __name__ == '__main__':
    unittest.main()
