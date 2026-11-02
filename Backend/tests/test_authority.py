import concurrent.futures
import hashlib
import json
import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from hotr_backend.api import MAX_BODY, create_app
from hotr_backend.schemas import CupRules, GiftRequest, Grant, INT_MAX
from hotr_backend.service import Authority, ServiceError
from hotr_backend.storage import Database, SCHEMA_VERSION

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-backend-')
        self.root = Path(self.temp.name)
        self.now = 100 * 86400 + 1000
        self.app = create_app(self.root / 'authority.sqlite3', CONFIG, lambda: self.now)
        self.authority = self.app.state.authority
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.credential = self.authority.provision(lifetime=2_592_000)
        self.headers = {'Authorization': 'Bearer ' + self.credential['token']}

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def get(self, path, **kwargs):
        return self.client.get(path, headers=kwargs.pop('headers', self.headers), **kwargs)

    def post(self, path, body, **kwargs):
        return self.client.post(path, json=body, headers=kwargs.pop('headers', self.headers), **kwargs)

    def request(self, offer=None):
        offer = offer or self.get('/v1/daily-gift/offer').json()
        return {'requestId': ident(), 'offerId': offer['id'], 'day': offer['day'], 'step': offer['step'], 'schedule': offer['schedule'], 'expectedGrant': offer['grant']}

    def count(self, table):
        with self.authority.database.connect() as db:
            return db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def verify_to(self, level):
        verifier = self.authority.provision(self.credential['playerId'], 'verifier', 2_592_000)
        headers = {'Authorization': 'Bearer ' + verifier['token']}
        current = self.get('/v1/me').json()['completed']
        for value in range(current + 1, level + 1):
            body = {'attemptId': ident(), 'level': value, 'proofDigest': digest('fixture-proof-' + str(value))}
            response = self.post('/internal/v1/verified-first-clear', body, headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
        return headers

    def event(self, kind='level_completed'):
        stream, receipt = digest('hotr-local-stream-v1|' + self.credential['playerId']), digest('fixture-receipt')
        delta = [0] * 12
        if kind == 'level_completed':
            delta[3] = 1
        if kind == 'reward_granted':
            delta[0] = 1_000_000
        return {'schema': 1, 'id': digest(f'hotr-event-v1|{stream}|{kind}|{receipt}'), 'stream': stream,
                'kind': kind, 'receipt': receipt, 'aggregate': digest('fixture-attempt'), 'category': 'campaign',
                'level': 1, 'rank': 0, 'points': 0, 'delta': delta}

    def test_01_authentication_expiration_revocation_and_scopes(self):
        self.assertEqual(self.client.get('/v1/me').status_code, 401)
        self.assertEqual(self.get('/v1/me', headers={'Authorization': 'Bearer ' + 'x' * 43}).status_code, 401)
        self.assertEqual(self.client.get('/healthz').json()['productionEnabled'], False)
        self.assertEqual(self.client.get('/readyz').status_code, 200)
        self.assertEqual(self.get('/v1/me').headers['cache-control'], 'no-store')
        self.assertEqual(self.get('/v1/me').json()['balanceScope'], 'reward_credits_only')
        self.assertEqual(self.post('/internal/v1/verified-first-clear', {'attemptId': ident(), 'level': 1, 'proofDigest': digest('fake')}).status_code, 403)
        verifier = self.authority.provision(self.credential['playerId'], 'verifier')
        self.assertEqual(self.get('/v1/daily-gift/offer', headers={'Authorization': 'Bearer ' + verifier['token']}).status_code, 403)
        self.authority.revoke(self.credential['token'])
        self.assertEqual(self.get('/v1/time').status_code, 401)
        short = self.authority.provision(lifetime=1)
        self.now += 1
        self.assertEqual(self.get('/v1/time', headers={'Authorization': 'Bearer ' + short['token']}).status_code, 401)
        with self.authority.database.connect() as db:
            stored = '\n'.join(str(tuple(row)) for row in db.execute('SELECT * FROM credentials'))
        self.assertNotIn(self.credential['token'], stored)
        self.assertNotIn(short['token'], stored)

    def test_02_daily_schedule_missed_days_cycle_and_receipt_pagination(self):
        expected = self.authority.daily.days
        for step in range(8):
            offer = self.get('/v1/daily-gift/offer').json()
            self.assertEqual(offer['step'], step % 7)
            self.assertEqual(offer['grant'], expected[step % 7].model_dump())
            request = self.request(offer)
            response = self.post('/v1/daily-gift/claim', request)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['grant'], offer['grant'])
            self.assertEqual(self.post('/v1/daily-gift/claim', request).json(), response.json())
            self.assertTrue(self.get('/v1/daily-gift/offer').json()['claimed'])
            self.now += 86400 * (4 if step == 2 else 1)
        self.assertEqual(self.count('rewards'), 8)
        totals = [sum(g.quantities()[i] for g in [*expected, expected[0]]) for i in range(10)]
        self.assertEqual(self.get('/v1/me').json()['rewardTotals'], totals)
        seen, cursor = [], 0
        while True:
            page = self.get('/v1/rewards', params={'after': cursor, 'limit': 3}).json()
            seen.extend(r['id'] for r in page['receipts'])
            cursor = page['nextCursor']
            if not page['hasMore']:
                break
        self.assertEqual(len(set(seen)), 8)

    def test_03_client_cannot_choose_quantity_day_or_another_players_offer(self):
        request = self.request()
        invalid = json.loads(json.dumps(request));invalid['expectedGrant']['coins'] += 900
        self.assertEqual(self.post('/v1/daily-gift/claim', invalid).status_code, 409)
        invalid = dict(request, day=request['day'] - 1)
        self.assertEqual(self.post('/v1/daily-gift/claim', invalid).status_code, 409)
        invalid = dict(request, playerId=ident())
        self.assertEqual(self.post('/v1/daily-gift/claim', invalid).status_code, 422)
        other = self.authority.provision()
        self.assertEqual(self.post('/v1/daily-gift/claim', request, headers={'Authorization': 'Bearer ' + other['token']}).status_code, 404)
        self.assertEqual(self.count('rewards'), 0)
        self.assertEqual(self.get('/v1/me').json()['rewardTotals'], [0] * 10)

    def test_04_concurrent_claims_credit_once_with_distinct_commands(self):
        request = self.request()
        def claim(index):
            actor = self.authority.authenticate(self.credential['token'])
            body = dict(request, requestId=ident())
            return self.authority.daily_claim(actor, GiftRequest.model_validate(body))
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(claim, range(24)))
        self.assertEqual(len({r['receiptId'] for r in results}), 1)
        self.assertEqual(self.count('rewards'), 1)
        self.assertEqual(self.get('/v1/me').json()['rewardTotals'][0], 50)

    def test_05_before_and_after_commit_failures_are_atomic_and_retryable(self):
        for phase in ('BeforeCommit', 'AfterCommit'):
            with self.subTest(phase=phase):
                request = self.request()
                def fail(current):
                    if current == phase:
                        raise OSError('Injected interruption')
                self.authority.checkpoint = fail
                self.assertEqual(self.post('/v1/daily-gift/claim', request).status_code, 500)
                self.authority.checkpoint = None
                committed = self.count('rewards')
                self.assertEqual(committed, 0 if phase == 'BeforeCommit' else 2)
                self.assertEqual(self.post('/v1/daily-gift/claim', request).status_code, 200)
                self.assertEqual(self.post('/v1/daily-gift/claim', request).status_code, 200)
                self.now += 86400
        self.assertEqual(self.count('rewards'), 2)

    def test_06_expired_offer_rejected_but_committed_receipt_recoverable(self):
        request = self.request()
        self.now += 86400
        self.assertEqual(self.post('/v1/daily-gift/claim', request).status_code, 410)
        self.assertEqual(self.count('rewards'), 0)
        request = self.request()
        original = self.post('/v1/daily-gift/claim', request).json()
        self.now += 86400 * 7
        self.assertEqual(self.post('/v1/daily-gift/claim', request).json(), original)
        request['requestId'] = ident()
        self.assertEqual(self.post('/v1/daily-gift/claim', request).json()['receiptId'], original['receiptId'])
        self.assertEqual(self.count('rewards'), 1)

    def test_07_idempotency_payload_conflict(self):
        request = self.request()
        self.assertEqual(self.post('/v1/daily-gift/claim', request).status_code, 200)
        request['expectedGrant']['coins'] += 1
        response = self.post('/v1/daily-gift/claim', request)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error'], 'idempotency_conflict')
        self.assertEqual(self.count('rewards'), 1)

    def test_08_issued_offer_and_claim_are_frozen_across_config_change(self):
        request = self.request()
        self.authority.daily.days[0].coins = 999
        self.authority.daily.version = 'future-config'
        self.assertEqual(self.get('/v1/daily-gift/offer').json()['grant']['coins'], 50)
        self.assertEqual(self.post('/v1/daily-gift/claim', request).json()['grant']['coins'], 50)
        self.now += 86400
        self.assertEqual(self.get('/v1/daily-gift/offer').json()['schedule'], 'future-config')

    def test_09_restart_preserves_clock_claims_and_journals(self):
        request = self.request()
        self.post('/v1/daily-gift/claim', request)
        now = self.now
        recreated = create_app(self.root / 'authority.sqlite3', CONFIG, lambda: now - 86400)
        with TestClient(recreated) as client:
            self.assertEqual(client.get('/v1/time', headers=self.headers).json()['serverUtc'], now)
            self.assertEqual(client.post('/v1/daily-gift/claim', json=request, headers=self.headers).status_code, 200)
            self.assertEqual(client.get('/v1/me', headers=self.headers).json()['rewardTotals'][0], 50)
        self.assertEqual(self.count('rewards'), 1)

    def test_10_overflow_rolls_back_claim_and_receipt(self):
        request = self.request()
        with self.authority.database.transaction() as db:
            db.execute('UPDATE players SET reward_totals=? WHERE id=?', (json.dumps([INT_MAX] + [0] * 9), self.credential['playerId']))
        response = self.post('/v1/daily-gift/claim', request)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.count('rewards'), 0)
        self.assertEqual(self.count('daily_claims'), 0)
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT gift_claims FROM players').fetchone()[0], 0)

    def test_11_forged_telemetry_never_changes_progress_or_rewards(self):
        response = self.post('/v1/audit-events', {'events': [self.event(), self.event('reward_granted')]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {'accepted': 2, 'duplicates': 0, 'trust': 'client_reported', 'rewarded': False})
        account = self.get('/v1/me').json()
        self.assertEqual(account['completed'], 0)
        self.assertEqual(account['rewardTotals'], [0] * 10)
        self.assertEqual(self.post('/v1/wellworks/claim', {'commandId': ident(), 'level': 10}).status_code, 409)
        self.assertEqual(self.post('/v1/rain-cup/join', {'commandId': ident()}).status_code, 409)

    def test_12_event_deduplication_conflicts_and_batch_atomicity(self):
        event = self.event()
        self.assertEqual(self.post('/v1/audit-events', {'events': [event, event]}).json()['accepted'], 1)
        self.assertEqual(self.post('/v1/audit-events', {'events': [event]}).json()['duplicates'], 1)
        conflicting = dict(event, aggregate=digest('different'))
        response = self.post('/v1/audit-events', {'events': [self.event('reward_granted'), conflicting]})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.count('audit_events'), 1)
        other = self.authority.provision()
        self.assertEqual(self.post('/v1/audit-events', {'events': [event]}, headers={'Authorization': 'Bearer ' + other['token']}).status_code, 403)

    def test_13_event_schema_limits_and_sensitive_input_not_echoed(self):
        event = self.event()
        for change in ({'schema': 2}, {'delta': [-99] * 12}, {'id': 'x' * 64}, {'kind': 'purchase_paid'}, {'points': 1}):
            self.assertEqual(self.post('/v1/audit-events', {'events': [dict(event, **change)]}).status_code, 422)
        self.assertEqual(self.post('/v1/audit-events', {'events': [event] * 101}).status_code, 422)
        self.assertEqual(self.post('/v1/audit-events', {'events': []}).status_code, 422)
        response = self.post('/v1/daily-gift/claim', {'token': 'SENSITIVE_INPUT_MUST_NOT_ECHO'})
        self.assertNotIn('SENSITIVE_INPUT', response.text)

    def test_14_oversized_body_including_streaming_is_rejected(self):
        response = self.client.post('/v1/audit-events', headers=self.headers, content=b'x' * (MAX_BODY + 1))
        self.assertEqual(response.status_code, 413)
        def chunks():
            for _ in range(17):
                yield b'x' * 4096
        self.assertEqual(self.client.post('/v1/audit-events', headers=self.headers, content=chunks()).status_code, 413)

    def test_15_all_milestones_require_trusted_progress_and_claim_once(self):
        self.verify_to(50)
        expected = [0] * 10
        for milestone in self.authority.wellworks.milestones:
            request = {'commandId': ident(), 'level': milestone.level}
            response = self.post('/v1/wellworks/claim', request)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['grant'], milestone.grant.model_dump())
            self.assertEqual(self.post('/v1/wellworks/claim', request).json()['id'], response.json()['id'])
            self.assertEqual(self.post('/v1/wellworks/claim', dict(request, commandId=ident())).json()['id'], response.json()['id'])
            expected = [a + b for a, b in zip(expected, milestone.grant.quantities(), strict=True)]
        self.assertEqual(self.count('rewards'), 5)
        self.assertEqual(self.get('/v1/me').json()['rewardTotals'], expected)
        self.assertTrue(all(m['claimed'] for m in self.get('/v1/wellworks').json()['milestones']))

    def test_16_verifier_proof_key_binding_and_duplicate_clear(self):
        verifier = self.verify_to(0)
        request = {'attemptId': ident(), 'level': 1, 'proofDigest': digest('one')}
        original = self.post('/internal/v1/verified-first-clear', request, headers=verifier)
        self.assertEqual(original.status_code, 200)
        self.assertEqual(self.post('/internal/v1/verified-first-clear', request, headers=verifier).json(), original.json())
        self.assertEqual(self.post('/internal/v1/verified-first-clear', dict(request, proofDigest=digest('other')), headers=verifier).status_code, 409)
        self.assertEqual(self.post('/internal/v1/verified-first-clear', dict(request, attemptId=ident()), headers=verifier).status_code, 409)
        self.assertEqual(self.get('/v1/me').json()['completed'], 1)
        self.assertEqual(self.count('verified_clears'), 1)

    def test_17_cup_join_score_boundary_claim_and_restart(self):
        verifier = self.verify_to(10)
        join = {'commandId': ident()}
        response = self.post('/v1/rain-cup/join', join)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.post('/v1/rain-cup/join', join).json(), response.json())
        self.assertEqual(self.post('/v1/rain-cup/join', {'commandId': ident()}).status_code, 409)
        request = {'commandId': ident(), 'runId': join['commandId']}
        self.assertEqual(self.post('/v1/rain-cup/claim', request).status_code, 409)
        clear = {'attemptId': ident(), 'level': 11, 'proofDigest': digest('eleven')}
        self.assertEqual(self.post('/internal/v1/verified-first-clear', clear, headers=verifier).json()['cupPoint'], 1)
        self.assertEqual(self.post('/internal/v1/verified-first-clear', clear, headers=verifier).json()['cupPoint'], 1)
        ends = response.json()['endsAt'];self.now = ends
        self.assertEqual(self.post('/internal/v1/verified-first-clear', dict(clear, attemptId=ident(), level=12), headers=verifier).json()['cupPoint'], 0)
        view = self.get('/v1/rain-cup').json()
        self.assertEqual(view['run']['points'], 1)
        self.assertEqual(view['run']['finalRank'], 5)
        self.assertTrue(view['practice'] and view['simulatedRivals'])
        self.assertFalse(view['realCompetition'])
        result = self.post('/v1/rain-cup/claim', request)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['grant']['coins'], 50)
        self.assertEqual(self.post('/v1/rain-cup/claim', request).json()['id'], result.json()['id'])
        self.assertEqual(self.post('/v1/rain-cup/claim', dict(request, commandId=ident())).json()['id'], result.json()['id'])
        recreated = create_app(self.root / 'authority.sqlite3', CONFIG, lambda: ends - 1000)
        with TestClient(recreated) as client:
            self.assertEqual(client.get('/v1/rain-cup', headers=self.headers).json()['state'], 'Claimed')
        self.assertEqual(self.count('rewards'), 1)

    def test_18_all_cup_ranks_ties_and_frozen_joined_rules(self):
        for points, rank in ((25, 1), (24, 1), (18, 2), (12, 3), (6, 4), (0, 5)):
            with self.subTest(points=points):
                player = self.authority.provision(lifetime=2_592_000)
                actor = self.authority.authenticate(player['token'])
                # Privileged test fixture only, never an account-import endpoint.
                with self.authority.database.transaction() as db:
                    db.execute('UPDATE players SET completed=10 WHERE id=?', (actor.player,))
                from hotr_backend.schemas import Command, CupClaimRequest, VerifiedClear
                run = ident();self.authority.cup_join(actor, Command(commandId=run))
                for level in range(11, 11 + points):
                    self.authority.verified_clear(actor, VerifiedClear(attemptId=ident(), level=level, proofDigest=digest(str(level))))
                frozen = self.authority.cup
                replacement = CupRules.model_validate_json(frozen.model_dump_json());replacement.rankRewards[rank - 1].coins += 999
                self.authority.cup = replacement
                self.now += frozen.durationSeconds
                actor = self.authority.authenticate(player['token'])
                receipt = self.authority.cup_claim(actor, CupClaimRequest(commandId=ident(), runId=run))
                self.assertEqual(receipt['grant'], frozen.rankRewards[rank - 1].model_dump())
                self.assertEqual(self.authority.cup_view(actor)['run']['finalRank'], rank)
                self.authority.cup = frozen

    def test_19_completed_campaign_has_no_new_cup_and_cross_player_claims_fail(self):
        self.verify_to(50)
        self.assertEqual(self.get('/v1/rain-cup').json()['state'], 'Exhausted')
        self.assertEqual(self.post('/v1/rain-cup/join', {'commandId': ident()}).status_code, 409)
        self.assertEqual(self.post('/v1/rain-cup/claim', {'commandId': ident(), 'runId': ident()}).status_code, 404)
        self.assertEqual(self.get('/v1/rewards', params={'after': -1}).status_code, 422)
        self.assertEqual(self.get('/v1/rewards', params={'limit': 101}).status_code, 422)

    def test_20_rate_limit_is_credential_scoped_and_recovers(self):
        self.authority.requests_per_minute = 2
        self.assertEqual(self.get('/v1/time').status_code, 200)
        self.assertEqual(self.get('/v1/time').status_code, 200)
        self.assertEqual(self.get('/v1/time').status_code, 429)
        other = self.authority.provision()
        self.assertEqual(self.get('/v1/time', headers={'Authorization': 'Bearer ' + other['token']}).status_code, 200)
        self.now += 60
        self.assertEqual(self.get('/v1/time').status_code, 200)

    def test_21_future_schema_and_corrupt_database_fail_without_reset(self):
        future = self.root / 'future.sqlite3';shutil.copyfile(self.root / 'authority.sqlite3', future)
        # Take a proper WAL-aware backup, not a copy of the main file alone.
        with self.authority.database.connect() as db:
            import sqlite3
            target = sqlite3.connect(future)
            db.backup(target);target.execute('UPDATE schema_info SET version=?', (SCHEMA_VERSION + 1,));target.commit();target.close()
        before = future.read_bytes()
        with self.assertRaises(RuntimeError):
            Database(future)
        self.assertEqual(future.read_bytes(), before)
        corrupt = self.root / 'corrupt.sqlite3';corrupt.write_bytes(b'not a database')
        with self.assertRaises(Exception):
            Database(corrupt)
        self.assertEqual(corrupt.read_bytes(), b'not a database')

    def test_22_approved_configs_match_unity_resources_exactly(self):
        root = CONFIG.parents[1]
        files = {'daily_gift.json': 'HOTR_DailyGift/Schedule.json', 'wellworks.json': 'HOTR_Wellworks/Schedule.json', 'rain_cup.json': 'HOTR_RainCup/Rules.json'}
        for server, client in files.items():
            self.assertEqual((CONFIG / server).read_bytes(), (root / 'Unity/Assets/HeartOfTheRain/App/Profile/Resources' / client).read_bytes())

    def test_23_production_activation_requires_real_deployment_configuration(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {'HOTR_BACKEND_MODE': 'production'}):
            with self.assertRaises(RuntimeError):
                create_app(self.root / 'not-created.sqlite3', CONFIG)
        self.assertFalse((self.root / 'not-created.sqlite3').exists())


if __name__ == '__main__':
    unittest.main()
