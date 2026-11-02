"""Credential deadlines at the actual handler/commit boundary.

Real ASGI requests and temporary SQLite databases, with controlled time and a
scripted invoice provider. This is not hosted latency or a real payment test.
"""
import concurrent.futures
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
import uuid

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.rustore_provider import VerifiedInvoice
from hotr_backend.service import Actor, ServiceError


CONFIG = Path(__file__).resolve().parents[1] / 'config'


class ActorDeadline93Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-handler-deadline93-')
        self.now = 100 * 86400 + 59
        self.bad_clock = False
        self.app = create_app(Path(self.temp.name) / 'authority.sqlite3',
                              clock=self.clock, social_enabled=True)
        self.authority = self.app.state.authority
        self.database = self.authority.database
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def clock(self):
        return float('nan') if self.bad_clock else self.now

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def credential(self, lifetime=1):
        value = self.authority.provision(lifetime=lifetime)
        return {'Authorization': 'Bearer ' + value['token']}

    def business(self):
        # Authentication/rate metadata may commit before handler authorization;
        # no gameplay, social, reward, or financial mutation may commit after it.
        names = ('players', 'wallets', 'wallet_ledger', 'commands',
                 'social_profiles', 'player_regions', 'rewards')
        with self.database.connect() as db:
            return {name: [tuple(r) for r in db.execute('SELECT * FROM ' + name)]
                    for name in names}

    def held_handler(self, method, path, headers, body=None, elapsed=1, transaction_number=3):
        original = self.database.transaction
        entering, held, at_lock, release = (threading.Event() for _ in range(4))
        visits = 0

        @contextmanager
        def observed(timeout=10):
            nonlocal visits
            visits += 1
            # Numbered as before review 136, when authentication took the first two writers.
            # It is now a snapshot read, and each handler writer must still check expiry itself.
            if visits == transaction_number - 2:
                entering.set()
                if not held.wait(3):
                    raise RuntimeError('handler_writer_fixture_not_ready')
                at_lock.set()
            with original(timeout=timeout) as db:
                yield db

        def writer():
            if not entering.wait(3):
                raise RuntimeError('handler_fixture_not_ready')
            with self.database.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                try:
                    held.set()
                    if not release.wait(3):
                        raise RuntimeError('handler_fixture_release_timeout')
                finally:
                    db.rollback()

        self.database.transaction = observed
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                blocker = pool.submit(writer)
                request = pool.submit(self.client.request, method, path,
                                      headers=headers, json=body)
                try:
                    self.assertTrue(at_lock.wait(3))
                    self.assertFalse(request.done())
                    self.now += elapsed
                finally:
                    release.set()
                blocker.result(timeout=4)
                return request.result(timeout=4)
        finally:
            release.set()
            self.database.transaction = original

    def test_01_expiry_during_handler_writer_wait_cannot_mutate_profile(self):
        headers = self.credential()
        before = self.business()
        response = self.held_handler('POST', '/v1/profile/name', headers,
                                    {'commandId': uuid.uuid4().hex, 'displayName': 'Deadline fixture'})
        self.assertEqual((response.status_code, response.json()), (401, {'error': 'unauthorized'}))
        self.assertEqual(self.business(), before)

    def test_02_private_social_read_rechecks_expiry_of_an_authenticated_actor(self):
        headers = self.credential()
        actor = self.authority.authenticate(headers['Authorization'].split(' ', 1)[1])
        before = self.business()
        self.now += 1
        with self.assertRaises(ServiceError) as raised:
            self.app.state.friends.list(actor)
        self.assertEqual((raised.exception.status, raised.exception.code), (401, 'unauthorized'))
        response = self.client.get('/v1/friends', headers=headers)
        self.assertEqual((response.status_code, response.json()), (401, {'error': 'unauthorized'}))
        self.assertEqual(self.business(), before)

    def test_03_unexpired_handler_retains_actor_snapshot_and_exact_retry(self):
        headers = self.credential(lifetime=2)
        snapshot = self.now
        body = {'commandId': uuid.uuid4().hex, 'displayName': 'Allowed fixture'}
        response = self.held_handler('POST', '/v1/profile/name', headers, body)
        self.assertEqual(response.status_code, 200)
        with self.database.connect() as db:
            self.assertEqual(db.execute('SELECT updated_at FROM social_profiles').fetchone()[0], snapshot)
        before = self.business()
        again = self.client.post('/v1/profile/name', headers=headers, json=body)
        self.assertEqual(again.json(), response.json())
        self.assertEqual(self.business(), before)

    def test_04_committed_social_receipt_cannot_be_read_with_newly_expired_actor(self):
        headers = self.credential(lifetime=2)
        body = {'commandId': uuid.uuid4().hex, 'displayName': 'Receipt fixture'}
        self.assertEqual(self.client.post('/v1/profile/name', headers=headers, json=body).status_code, 200)
        original = self.authority.authenticate
        def expire_after_authentication(*args, **kwargs):
            actor = original(*args, **kwargs)
            self.now += 2
            return actor
        self.authority.authenticate = expire_after_authentication
        before = self.business()
        response = self.client.get('/v1/social/operations/' + body['commandId']
                                   + '?operation=social.profile.name', headers=headers)
        self.assertEqual((response.status_code, response.json()), (401, {'error': 'unauthorized'}))
        self.assertEqual(self.business(), before)

    def test_05_invalid_clock_after_authentication_fails_closed_without_mutation(self):
        headers = self.credential()
        original = self.authority.authenticate
        def break_clock_after_authentication(*args, **kwargs):
            actor = original(*args, **kwargs)
            self.bad_clock = True
            return actor
        self.authority.authenticate = break_clock_after_authentication
        before = self.business()
        response = self.client.post('/v1/region', headers=headers,
                                    json={'commandId': uuid.uuid4().hex, 'regionCode': 'RU'})
        self.assertEqual((response.status_code, response.json()), (503, {'error': 'clock_unavailable'}))
        self.assertEqual(self.business(), before)

    def test_06_backward_clock_cannot_undo_authenticated_high_water_deadline(self):
        headers = self.credential()
        token = headers['Authorization'].split(' ', 1)[1]
        actor = self.authority.authenticate(token)
        with self.database.transaction() as db:
            db.execute('UPDATE clock_state SET high_water=? WHERE id=1', (self.now + 1,))
        self.now -= 100
        with self.assertRaises(ServiceError) as failure:
            self.app.state.friends.me(actor)
        self.assertEqual((failure.exception.status, failure.exception.code), (401, 'unauthorized'))

    def test_07_internal_worker_actor_remains_a_separate_server_capability(self):
        headers = self.credential()
        actor = self.authority.authenticate(headers['Authorization'].split(' ', 1)[1])
        self.now += 1
        # Detached actors exist only inside trusted workers, never from API
        # request bodies. Active/deleted-account checks still apply to them.
        internal = Actor(actor.player, self.now)
        self.assertEqual(self.app.state.friends.me(internal)['playerId'], actor.player)
        with self.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (actor.player, self.now))
        with self.assertRaises(ServiceError) as failure:
            self.app.state.friends.me(internal)
        self.assertEqual(failure.exception.status, 410)

    def test_08_invoice_provider_wait_cannot_credit_after_request_credential_expires(self):
        config = json.loads((CONFIG / 'commerce.json').read_text('utf-8-sig'))
        config.update(enabled=True, sandbox=True, appId=12345,
                      products=[{'id': 'deadline-fixture', 'storeProductId': 'deadline-fixture',
                                 'coins': 1000, 'amountMinor': 9900, 'currency': 'RUB', 'enabled': True}])
        path = Path(self.temp.name) / 'commerce.json'
        path.write_text(json.dumps(config), 'utf-8')
        outer = self
        class Provider:
            configured = True
            order = None
            def lookup(self, invoice_id, sandbox):
                outer.now += 1
                row = self.order
                return VerifiedInvoice(invoice_id, str(uuid.uuid4()), 12345, True,
                                       row['orderId'], 'deadline-fixture', row['playerId'],
                                       row['sdk']['developerPayload'], 9900, 'RUB', 'CONFIRMED', 'PENDING')
        provider = Provider()
        app = create_app(Path(self.temp.name) / 'payment.sqlite3', clock=self.clock,
                         commerce_config_path=path, commerce_provider=provider)
        owner = app.state.authority.provision(lifetime=1)
        headers = {'Authorization': 'Bearer ' + owner['token']}
        with TestClient(app, raise_server_exceptions=False) as client:
            order = client.post('/v1/commerce/orders', headers=headers,
                                json={'commandId': uuid.uuid4().hex, 'productId': 'deadline-fixture'})
            self.assertEqual(order.status_code, 200)
            provider.order = order.json()
            with app.state.authority.database.connect() as db:
                before_wallet = [tuple(r) for r in db.execute('SELECT * FROM wallets')]
                before_ledger = [tuple(r) for r in db.execute('SELECT * FROM wallet_ledger')]
            response = client.post('/v1/commerce/orders/' + provider.order['orderId'] + '/reconcile',
                                   headers=headers, json={'invoiceId': '10001'})
            self.assertEqual((response.status_code, response.json()), (401, {'error': 'unauthorized'}))
            with app.state.authority.database.connect() as db:
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM wallets')], before_wallet)
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM wallet_ledger')], before_ledger)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT state FROM commerce_invoice_requests').fetchone()[0], 'Pending')
            # Recovery uses a fresh authenticated credential and the same
            # order/invoice. It creates exactly one credit, never a second order.
            fresh = app.state.authority.provision(player=owner['playerId'], lifetime=60)
            headers = {'Authorization': 'Bearer ' + fresh['token']}
            recovered = client.post('/v1/commerce/orders/' + provider.order['orderId'] + '/reconcile',
                                    headers=headers, json={'invoiceId': '10001'})
            self.assertEqual(recovered.status_code, 200)
            self.assertEqual(recovered.json()['credit']['coins'], 1000)
            with app.state.authority.database.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0], 1)

    def reported_ad(self):
        # Explicit lower-trust development policy; no ad provider is contacted.
        ads = self.app.state.rewarded_ads
        ads.config = ads.config.model_copy(update={'enabled': True, 'completionMode': 'sdk_client_reported_capped'})
        headers = self.credential(lifetime=3600)
        response = self.client.get('/v1/ads/rewarded/status?utcOffsetSeconds=0', headers=headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/v1/ads/rewarded/reserve', headers=headers,
                                    json={'commandId': uuid.uuid4().hex, 'placement': ads.config.placement})
        self.assertEqual(response.status_code, 200)
        value = response.json()
        path = '/v1/ads/rewarded/opportunities/' + value['opportunityId']
        response = self.client.post(path + '/client-completion', headers=headers,
                                    json={'commandId': uuid.uuid4().hex})
        self.assertEqual(response.status_code, 200)
        return headers, path, value

    def test_09_ad_claim_wait_crossing_midnight_uses_actual_commit_day_and_cooldown(self):
        self.now = 101 * 86400 - 1
        headers, path, _ = self.reported_ad()
        # Ads sample an independent clock before the claim writer, so their
        # actual claim is the fourth writer after authentication.
        response = self.held_handler('POST', path + '/claim', headers,
                                     {'commandId': uuid.uuid4().hex}, elapsed=2, transaction_number=4)
        self.assertEqual(response.status_code, 200)
        value = response.json()
        self.assertEqual((value['claimedAt'], value['claimedDay']), (self.now, 101))
        self.assertEqual(value['receipt']['serverUtc'], self.now)
        status = self.client.get('/v1/ads/rewarded/status', headers=headers).json()
        self.assertEqual((status['claimedToday'], status['cooldownRemainingSeconds']), (1, 600))

    def test_10_reported_ad_passing_its_expiry_during_claim_writer_wait_still_credits_once(self):
        headers, path, value = self.reported_ad()
        self.now = value['expiresAt'] - 1
        response = self.held_handler('POST', path + '/claim', headers,
                                     {'commandId': uuid.uuid4().hex}, elapsed=2, transaction_number=4)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['state'], 'Claimed')

    def daily_body(self, offer):
        return {'requestId': uuid.uuid4().hex, 'offerId': offer['id'], 'day': offer['day'],
                'step': offer['step'], 'schedule': offer['schedule'], 'expectedGrant': offer['grant']}

    def cup_fixture(self, headers):
        player = self.authority.authenticate(headers['Authorization'].split(' ', 1)[1]).player
        # Trusted server fixture progression, never a public request field.
        with self.database.transaction() as db:
            db.execute('UPDATE players SET completed=10 WHERE id=?', (player,))
        response = self.client.post('/v1/rain-cup/join', headers=headers,
                                    json={'commandId': uuid.uuid4().hex})
        self.assertEqual(response.status_code, 200)
        return player, response.json()

    def zero_lives_due_soon(self, headers):
        player = self.authority.authenticate(headers['Authorization'].split(' ', 1)[1]).player
        with self.database.transaction() as db:
            row = db.execute('SELECT balances,revision FROM wallets WHERE player_id=?', (player,)).fetchone()
            values = json.loads(row['balances'])
            values[10] = 0
            due = self.now + 1
            db.execute('UPDATE wallets SET balances=?,next_life_at=? WHERE player_id=?',
                       (json.dumps(values), due, player))
            return row['revision'], due

    def test_11_daily_claim_expiring_during_writer_wait_does_not_grant_old_day(self):
        self.now = 101 * 86400 - 1
        headers = self.credential(lifetime=2592000)
        offer = self.client.get('/v1/daily-gift/offer', headers=headers).json()
        response = self.held_handler('POST', '/v1/daily-gift/claim', headers,
                                     self.daily_body(offer), elapsed=2)
        self.assertEqual((response.status_code, response.json()), (410, {'error': 'gift_expired'}))
        with self.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rewards').fetchone()[0], 0)
        current = self.client.get('/v1/daily-gift/offer', headers=headers).json()
        self.assertEqual((current['day'], current['step']), (101, 0))
        body = self.daily_body(current)
        committed = self.client.post('/v1/daily-gift/claim', headers=headers, json=body)
        self.assertEqual(committed.status_code, 200)
        self.now += 86400
        self.assertEqual(self.client.post('/v1/daily-gift/claim', headers=headers, json=body).json(), committed.json())
        with self.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rewards').fetchone()[0], 1)

    def test_12_daily_offer_wait_crossing_midnight_issues_current_authority_day(self):
        self.now = 101 * 86400 - 1
        headers = self.credential(lifetime=3600)
        response = self.held_handler('GET', '/v1/daily-gift/offer', headers, elapsed=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['day'], 101)
        with self.database.connect() as db:
            self.assertEqual(db.execute('SELECT day FROM offers').fetchone()[0], 101)

    def test_13_cup_view_of_an_ended_run_finishes_at_current_service_time(self):
        # Before the deadline the view is a snapshot read with no writer to wait for.
        headers = self.credential(lifetime=2592000)
        _, cup = self.cup_fixture(headers)
        self.now = cup['endsAt']
        response = self.held_handler('GET', '/v1/rain-cup', headers, elapsed=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()['state'], response.json()['serverUtc']), ('Finished', self.now))
        self.assertGreater(response.json()['run']['finalRank'], 0)

    def test_14_cup_claim_wait_crossing_deadline_claims_once_with_frozen_receipt(self):
        headers = self.credential(lifetime=2592000)
        _, cup = self.cup_fixture(headers)
        self.now = cup['endsAt'] - 1
        body = {'commandId': uuid.uuid4().hex, 'runId': cup['runId']}
        response = self.held_handler('POST', '/v1/rain-cup/claim', headers, body, elapsed=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['serverUtc'], self.now)
        self.now += 86400
        self.assertEqual(self.client.post('/v1/rain-cup/claim', headers=headers, json=body).json(), response.json())
        with self.database.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rewards WHERE source='rain_cup'").fetchone()[0], 1)

    def test_15_server_clear_wait_crossing_cup_deadline_cannot_add_late_point(self):
        headers = self.credential(lifetime=2592000)
        player, cup = self.cup_fixture(headers)
        self.now = cup['endsAt'] - 1
        verifier = self.authority.provision(player=player, role='verifier', lifetime=3600)
        response = self.held_handler('POST', '/internal/v1/verified-first-clear',
            {'Authorization': 'Bearer ' + verifier['token']},
            {'attemptId': uuid.uuid4().hex, 'level': 11, 'proofDigest': hashlib.sha256(b'controlled fixture').hexdigest()}, elapsed=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()['completed'], response.json()['cupPoint']), (11, 0))
        with self.database.connect() as db:
            self.assertEqual(tuple(db.execute('SELECT points,state FROM cup_runs').fetchone()), (0, 'Finished'))
            self.assertEqual(db.execute('SELECT created_at FROM verified_clears').fetchone()[0], self.now)

    def test_16_permanent_wellworks_wait_changes_only_new_receipt_time_not_eligibility(self):
        headers = self.credential(lifetime=2592000)
        self.cup_fixture(headers)
        body = {'commandId': uuid.uuid4().hex, 'level': 10}
        response = self.held_handler('POST', '/v1/wellworks/claim', headers, body, elapsed=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['serverUtc'], self.now)
        self.now += 86400
        self.assertEqual(self.client.post('/v1/wellworks/claim', headers=headers, json=body).json(), response.json())
        with self.database.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rewards WHERE source='wellworks'").fetchone()[0], 1)

    def test_17_wallet_view_wait_crossing_life_deadline_shows_regenerated_life_once(self):
        headers = self.credential(lifetime=3600)
        revision, due = self.zero_lives_due_soon(headers)
        self.now = due  # Before this the read is a snapshot with no writer to wait for.
        response = self.held_handler('GET', '/v1/wallet', headers, elapsed=2)
        self.assertEqual(response.status_code, 200)
        value = response.json()
        self.assertEqual((value['lives'], value['coins'], value['nextLifeAt'], value['serverUtc']),
                         (1, 1250, due + 1800, self.now))
        self.assertEqual(value['revision'], revision + 1)
        self.assertEqual(self.client.get('/v1/wallet', headers=headers).json(), value)

    def test_18_paid_refill_wait_cannot_charge_after_natural_life_becomes_due(self):
        headers = self.credential(lifetime=3600)
        revision, _ = self.zero_lives_due_soon(headers)
        response = self.held_handler('POST', '/v1/wallet/refill', headers,
                                     {'commandId': uuid.uuid4().hex, 'expectedRevision': revision}, elapsed=2)
        self.assertEqual((response.status_code, response.json()), (409, {'error': 'wallet_revision_conflict'}))
        wallet = self.client.get('/v1/wallet', headers=headers).json()
        self.assertEqual((wallet['coins'], wallet['lives']), (1250, 1))
        with self.database.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM commands WHERE operation='wallet.refill'").fetchone()[0], 0)

    def test_19_replay_commit_wait_cannot_award_cup_point_after_deadline(self):
        from tests.test_replay_service import ScriptedWorker
        self.client.close()
        worker = ScriptedWorker()
        self.app = create_app(Path(self.temp.name) / 'replay.sqlite3', clock=self.clock,
                              replay_enabled=True, replay_worker=worker)
        self.authority, self.database = self.app.state.authority, self.app.state.authority.database
        self.client = TestClient(self.app, raise_server_exceptions=False)
        headers = self.credential(lifetime=2592000)
        _, cup = self.cup_fixture(headers)
        wallet = self.client.get('/v1/wallet', headers=headers).json()
        reserved = self.client.post('/v1/attempts/reserve', headers=headers,
            json={'commandId': uuid.uuid4().hex, 'expectedRevision': wallet['revision'], 'level': 11, 'starting': [0] * 4})
        self.assertEqual(reserved.status_code, 200)
        attempt = reserved.json()['attempt']['attemptId']
        started = self.client.post('/v1/attempts/' + attempt + '/start', headers=headers,
            json={'commandId': uuid.uuid4().hex, 'expectedRevision': reserved.json()['wallet']['revision']})
        self.assertEqual(started.status_code, 200)
        worker.outcome = 'Won'
        self.now = cup['endsAt'] - 1
        body = {'commandId': uuid.uuid4().hex, 'expectedPrefixRevision': 0,
                'actions': [{'index': 0, 'kind': 'Swap', 'x': 1, 'y': 1, 'toX': 1, 'toY': 2}]}
        path = '/v1/gameplay/attempts/' + attempt + '/verify'
        # Authentication=1/2, submit=3, lease=4, post-worker clock=5,
        # actual result/debit/progression commit=6. This is the shared ordinary
        # replay orchestration with a SCRIPTED worker, not model validation.
        response = self.held_handler('POST', path, headers, body, elapsed=2, transaction_number=6)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual((result['state'], result['model']['outcome'], result['displayReceipt']['awardedCoins']),
                         ('Committed', 'Won', 50))
        with self.database.connect() as db:
            self.assertEqual(tuple(db.execute('SELECT points,state FROM cup_runs').fetchone()), (0, 'Finished'))
            self.assertEqual(db.execute('SELECT created_at FROM verified_clears').fetchone()[0], self.now)
        self.assertEqual(self.client.post(path, headers=headers, json=body).json(), result)
        self.assertEqual(len(worker.calls), 1)

    def test_20_confirmed_loss_wait_starts_life_timer_from_actual_writer_time(self):
        headers = self.credential(lifetime=3600)
        wallet = self.client.get('/v1/wallet', headers=headers).json()
        reserved = self.client.post('/v1/attempts/reserve', headers=headers,
            json={'commandId': uuid.uuid4().hex, 'expectedRevision': wallet['revision'], 'level': 1, 'starting': [0] * 4})
        self.assertEqual(reserved.status_code, 200)
        attempt = reserved.json()['attempt']['attemptId']
        started = self.client.post('/v1/attempts/' + attempt + '/start', headers=headers,
            json={'commandId': uuid.uuid4().hex, 'expectedRevision': reserved.json()['wallet']['revision']})
        self.assertEqual(started.status_code, 200)
        body = {'commandId': uuid.uuid4().hex, 'expectedRevision': started.json()['wallet']['revision']}
        path = '/v1/attempts/' + attempt + '/quit'
        response = self.held_handler('POST', path, headers, body, elapsed=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()['wallet']['lives'], response.json()['wallet']['nextLifeAt']),
                         (4, self.now + 1800))
        self.now += 10
        self.assertEqual(self.client.post(path, headers=headers, json=body).json(), response.json())


if __name__ == '__main__':
    unittest.main()
