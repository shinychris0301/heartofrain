"""Real ASGI/SQLite rewarded-ad policy and atomicity, synthetic proof only.

These tests never contact Yandex or represent an SDK callback as trusted proof.
The private HMAC key is ephemeral and no public completion-verification route is
installed. No normal Unity/local profile balance is read or imported.
"""
import concurrent.futures
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from contextlib import closing
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import tempfile
import threading
import unittest
import uuid

from fastapi.testclient import TestClient
from pydantic import ValidationError

from hotr_backend.api import create_app
from hotr_backend.newads import RewardedAds
from hotr_backend.newads_schemas import RewardedAdsConfig, ReserveRewardedAd, RewardedAdCommand
from hotr_backend.newads_verifier import SyntheticHmacCompletionVerifier, VerifiedAdCompletion
from hotr_backend.operations import backup_database, restore_database
from hotr_backend.service import ServiceError
from hotr_backend.storage import Database, canonical, SCHEMA_VERSION

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class RewardedAdTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-rewarded-ads-')
        self.root = Path(self.temp.name)
        self.path = self.root / 'authority.sqlite3'
        self.config_path = self.root / 'ads.json'
        self.config = json.loads((CONFIG / 'ads.json').read_text('utf-8'))
        self.config['enabled'] = True
        self.config['completionMode'] = 'trusted_completion'
        self.write_config()
        self.key = secrets.token_bytes(32)
        self.now = 500 * 86400
        self.open()
        self.owner = self.authority.provision(lifetime=2592000)
        self.peer = self.authority.provision(lifetime=2592000)

    def write_config(self):
        self.config_path.write_text(json.dumps(self.config), 'utf-8')

    def open(self, configured=True):
        self.verifier = SyntheticHmacCompletionVerifier(self.key, mode='staging') if configured else None
        self.app = create_app(self.path, CONFIG, lambda: self.now,
                              ads_config_path=self.config_path, ads_verifier=self.verifier)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.authority = self.app.state.authority
        self.ads = self.app.state.rewarded_ads

    def restart(self, configured=True):
        self.client.close()
        self.open(configured)

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def headers(self, owner=None):
        return {'Authorization': 'Bearer ' + (owner or self.owner)['token']}

    def get(self, path, owner=None):
        return self.client.get(path, headers=self.headers(owner))

    def post(self, path, value, owner=None):
        return self.client.post(path, json=value, headers=self.headers(owner))

    def status(self):
        response = self.get('/v1/ads/rewarded/status')
        self.assertEqual(response.status_code, 200)
        return response.json()

    def reserve(self, command=None, owner=None):
        response = self.post('/v1/ads/rewarded/reserve', {'commandId': command or ident(), 'placement': 'shop_rewarded'}, owner)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def action(self, value, action, command=None, owner=None):
        return self.post('/v1/ads/rewarded/opportunities/' + value['opportunityId'] + '/' + action,
                         {'commandId': command or ident()}, owner)

    def evidence(self, value, event=None, **changes):
        body = {'eventId': event or ident(), 'opportunityId': value['opportunityId'],
                'playerId': value['playerId'], 'placement': value['placement'],
                'configVersion': value['configVersion'], 'completedAt': self.now}
        body.update(changes)
        body['signature'] = hmac.new(self.key, canonical(body).encode('ascii'), hashlib.sha256).hexdigest()
        return body

    def verify(self, value, **changes):
        return self.ads.accept_trusted_completion(self.evidence(value, **changes))

    def wallet(self):
        return self.get('/v1/wallet').json()

    def coins(self):
        return self.wallet()['coins']

    def expect(self, status, operation):
        with self.assertRaises(ServiceError) as error:
            operation()
        self.assertEqual(error.exception.status, status)

    def claimed(self):
        value = self.reserve()
        self.verify(value)
        response = self.action(value, 'claim')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['state'], 'Claimed')
        return response.json()

    def test_01_default_disabled_and_enabled_without_bridge_fail_closed(self):
        app = create_app(self.root / 'default.sqlite3', CONFIG, lambda: self.now)
        owner = app.state.authority.provision()
        with TestClient(app) as client:
            headers = {'Authorization': 'Bearer ' + owner['token']}
            value = client.get('/v1/ads/rewarded/status', headers=headers).json()
            self.assertFalse(value['enabled'])
            self.assertFalse(value['available'])
            self.assertEqual(client.post('/v1/ads/rewarded/reserve', headers=headers,
                             json={'commandId': ident(), 'placement': 'shop_rewarded'}).status_code, 503)
        self.restart(False)
        self.assertEqual(self.status()['reason'], 'trusted_completion_unavailable')
        self.assertEqual(self.post('/v1/ads/rewarded/reserve', {'commandId': ident(), 'placement': 'shop_rewarded'}).status_code, 503)
        self.assertEqual(self.coins(), 1250)

    def test_02_client_completion_and_unverified_claim_never_credit(self):
        value = self.reserve()
        first = self.wallet()
        callback = self.action(value, 'client-completion')
        self.assertEqual(callback.json()['state'], 'AwaitingVerification')
        command = ident()
        self.assertEqual(self.action(value, 'claim', command).json()['state'], 'AwaitingVerification')
        self.assertEqual(self.wallet(), first)
        self.assertEqual(self.status()['claimedToday'], 0)
        self.verify(value)
        claimed = self.action(value, 'claim', command).json()
        self.assertEqual(claimed['receipt']['coins'], 400)
        self.assertEqual(self.coins(), 1650)

    def test_03_reward_ledger_revision_and_immutable_receipt_exactly_once(self):
        before = self.wallet()
        value = self.reserve()
        evidence = self.evidence(value)
        self.ads.accept_trusted_completion(evidence)
        command = ident()
        first = self.action(value, 'claim', command).json()
        self.assertEqual(first, self.action(value, 'claim', command).json())
        self.ads.accept_trusted_completion(evidence)
        self.action(value, 'client-completion')
        self.action(value, 'claim')
        after = self.wallet()
        self.assertEqual(after['revision'], before['revision'] + 1)
        self.assertEqual(self.coins(), 1650)
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rewards WHERE source='rewarded_ad'").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM wallet_ledger WHERE origin LIKE 'reward/%'").fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rewarded_ad_completions').fetchone()[0], 1)

    def test_04_daily_three_and_exact_600_second_cooldown(self):
        for index in range(3):
            self.claimed()
            self.assertEqual(self.status()['claimedToday'], index + 1)
            if index < 2:
                self.now += 599
                self.assertEqual(self.post('/v1/ads/rewarded/reserve', {'commandId': ident(), 'placement': 'shop_rewarded'}).status_code, 409)
                self.now += 1
        self.assertEqual(self.coins(), 2450)
        self.now += 600
        self.assertEqual(self.status()['remainingToday'], 0)
        self.assertEqual(self.status()['reason'], 'daily_limit')
        self.assertEqual(self.post('/v1/ads/rewarded/reserve', {'commandId': ident(), 'placement': 'shop_rewarded'}).status_code, 409)

    def test_05_fixed_utc10_day_not_utc_or_client_timezone(self):
        boundary = 501 * 86400 - 36000
        self.now = boundary - 1201
        for index in range(3):
            self.claimed()
            if index < 2:
                self.now += 600
        self.assertEqual(self.now, boundary - 1)
        self.assertEqual(self.status()['claimedToday'], 3)
        self.now = boundary
        self.assertEqual(self.status()['claimedToday'], 0)
        self.assertEqual(self.status()['reason'], 'cooldown')
        self.assertEqual(self.status()['cooldownRemainingSeconds'], 599)
        self.now += 599
        self.claimed()
        self.assertEqual(self.status()['claimedToday'], 1)

    def test_06_verified_cross_midnight_claim_uses_current_day_and_clock(self):
        boundary = 501 * 86400 - 36000
        self.now = boundary - 10
        value = self.reserve()
        self.verify(value)
        self.now = boundary + 1
        result = self.action(value, 'claim').json()
        self.assertEqual(result['reservedDay'] + 1, result['claimedDay'])
        self.assertEqual(result['claimedAt'], self.now)
        self.assertEqual(self.status()['claimedToday'], 1)
        self.assertEqual(self.status()['cooldownRemainingSeconds'], 600)

    def test_07_no_fill_cancel_and_expiry_spend_no_quota_cooldown(self):
        for index in range(4):
            value = self.reserve()
            self.assertEqual(self.action(value, 'cancel').status_code, 200)
        value = self.reserve()
        self.now = value['expiresAt']
        self.assertEqual(self.get('/v1/ads/rewarded/opportunities/' + value['opportunityId']).json()['state'], 'Expired')
        self.assertEqual(self.action(value, 'claim').status_code, 409)
        self.assertEqual(self.status()['remainingToday'], 3)
        self.assertEqual(self.status()['cooldownRemainingSeconds'], 0)
        self.assertEqual(self.coins(), 1250)
        self.reserve()

    def test_08_owner_bounds_and_strict_no_client_reward_payload(self):
        value = self.reserve()
        path = '/v1/ads/rewarded/opportunities/' + value['opportunityId']
        self.assertEqual(self.get(path, self.peer).status_code, 404)
        for action in ('claim', 'cancel', 'client-completion'):
            self.assertEqual(self.action(value, action, owner=self.peer).status_code, 404)
        for body in ({'commandId': ident(), 'placement': 'shop_rewarded', 'rewardCoins': 999},
                     {'commandId': ident(), 'placement': 'home_rewarded'},
                     {'commandId': ident(), 'placement': 'shop_rewarded', 'playerId': self.peer['playerId']}):
            self.assertEqual(self.post('/v1/ads/rewarded/reserve', body).status_code, 422)
        self.assertEqual(self.post(path + '/claim', {'commandId': ident(), 'verified': True}).status_code, 422)
        self.assertEqual(self.client.get('/v1/ads/rewarded/status').status_code, 401)
        for route in ('/v1/ads/rewarded/verify', '/internal/v1/ads/completion', '/v1/ads/rewarded/webhook'):
            self.assertEqual(self.post(route, {}).status_code, 404)

    def test_09_signed_proof_tamper_owner_version_future_and_event_reuse(self):
        value = self.reserve()
        tampered = self.evidence(value)
        tampered['playerId'] = self.peer['playerId']
        self.expect(403, lambda: self.ads.accept_trusted_completion(tampered))
        self.expect(404, lambda: self.verify(value, playerId=self.peer['playerId']))
        self.expect(409, lambda: self.verify(value, configVersion='foreign-version'))
        self.expect(409, lambda: self.verify(value, placement='foreign-placement'))
        self.expect(409, lambda: self.verify(value, completedAt=self.now + 1))
        self.expect(409, lambda: self.verify(value, completedAt=value['createdAt'] - 1))
        event = ident()
        self.ads.accept_trusted_completion(self.evidence(value, event))
        self.expect(409, lambda: self.verify(value))
        self.action(value, 'claim')
        self.now += 600
        other = self.reserve()
        self.expect(409, lambda: self.ads.accept_trusted_completion(self.evidence(other, event)))

    def test_10_cancelled_or_expired_proof_cannot_revive_and_outoforder_callback_safe(self):
        value = self.reserve()
        evidence = self.evidence(value)
        self.action(value, 'cancel')
        self.expect(409, lambda: self.ads.accept_trusted_completion(evidence))
        value = self.reserve()
        evidence = self.evidence(value)
        self.now = value['expiresAt']
        self.expect(409, lambda: self.ads.accept_trusted_completion(evidence))
        value = self.reserve()
        self.verify(value)
        self.assertEqual(self.action(value, 'client-completion').json()['state'], 'Verified')
        self.assertEqual(self.action(value, 'cancel').status_code, 409)
        self.action(value, 'claim')
        self.assertEqual(self.action(value, 'client-completion').json()['state'], 'Claimed')
        self.assertEqual(self.coins(), 1650)

    def test_11_restart_pending_verified_and_lost_claim_reply(self):
        value = self.reserve()
        self.action(value, 'client-completion')
        self.restart()
        self.assertEqual(self.status()['activeOpportunity']['state'], 'AwaitingVerification')
        self.verify(value)
        self.restart(False)
        self.assertEqual(self.status()['activeOpportunity']['state'], 'Verified')
        command = ident()
        first = self.action(value, 'claim', command).json()
        self.restart(False)
        self.assertEqual(self.action(value, 'claim', command).json(), first)
        self.assertEqual(self.coins(), 1650)

    def test_12_parallel_reservations_single_slot_and_parallel_claim_exact_once(self):
        actors = [self.authority.authenticate(self.owner['token']) for _ in range(6)]
        barrier = threading.Barrier(6)
        def reserve(index):
            barrier.wait(timeout=4)
            try:
                return self.ads.reserve(actors[index], ReserveRewardedAd(commandId=ident(), placement='shop_rewarded'))
            except ServiceError as error:
                return error.status
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(reserve, range(6)))
        values = [value for value in results if isinstance(value, dict)]
        self.assertEqual(len(values), 1)
        self.assertEqual(results.count(409), 5)
        value = values[0]
        self.verify(value)
        barrier = threading.Barrier(6)
        def claim(index):
            barrier.wait(timeout=4)
            return self.ads.claim(actors[index], value['opportunityId'], RewardedAdCommand(commandId=ident()))
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            claims = list(pool.map(claim, range(6)))
        self.assertTrue(all(item['state'] == 'Claimed' for item in claims))
        self.assertEqual(self.coins(), 1650)
        self.assertEqual(self.status()['claimedToday'], 1)

    def test_13_same_reservation_key_retry_and_changed_claim_binding(self):
        command = ident()
        value = self.reserve(command)
        self.assertEqual(value, self.reserve(command))
        self.verify(value)
        claim_key = ident()
        self.action(value, 'claim', claim_key)
        self.now += 600
        other = self.reserve()
        self.verify(other)
        self.assertEqual(self.action(other, 'claim', claim_key).status_code, 409)
        self.assertEqual(self.coins(), 1650)

    def test_14_revoked_and_deleted_actors_cannot_cached_replay_or_grant(self):
        actor = self.authority.authenticate(self.owner['token'])
        value = self.reserve()
        self.verify(value)
        self.authority.revoke(self.owner['token'])
        self.expect(401, lambda: self.ads.claim(actor, value['opportunityId'], RewardedAdCommand(commandId=ident())))
        self.expect(401, lambda: self.ads.status(actor))
        replacement = self.authority.provision(player=self.owner['playerId'])
        self.owner = replacement
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.owner['playerId'], self.now))
        self.assertEqual(self.action(value, 'claim').status_code, 410)
        self.expect(410, lambda: self.verify(value))
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rewards WHERE source='rewarded_ad'").fetchone()[0], 0)

    def test_15_refund_quarantine_blocks_reserve_verification_and_credit(self):
        value = self.reserve()
        self.verify(value)
        with self.authority.database.transaction() as db:
            db.execute('''INSERT INTO commerce_orders
                (id,player_id,catalog_version,internal_product,store_product,app_id,sandbox,amount_minor,currency,coins,binding,state,created_at,updated_at)
                VALUES(?,?,'synthetic','test','test',1,1,1,'RUB',1,?,'RefundReview',?,?)''',
                       (ident(), self.owner['playerId'], ident(), self.now, self.now))
        self.assertEqual(self.action(value, 'claim').status_code, 409)
        self.assertEqual(self.status()['reason'], 'wallet_refund_review_required')
        self.assertEqual(self.post('/v1/ads/rewarded/reserve', {'commandId': ident(), 'placement': 'shop_rewarded'}).status_code, 409)
        self.expect(409, lambda: self.verify(value))
        self.assertEqual(self.coins(), 1250)

    def test_16_fault_before_commit_rolls_back_and_after_commit_recovers(self):
        value = self.reserve()
        self.verify(value)
        command = ident()
        def before(point):
            if point == 'BeforeCommit':
                raise OSError('synthetic-before-commit')
        self.ads.checkpoint = before
        self.assertEqual(self.action(value, 'claim', command).status_code, 500)
        self.ads.checkpoint = None
        self.assertEqual(self.coins(), 1250)
        def after(point):
            if point == 'AfterCommit':
                raise OSError('synthetic-lost-reply')
        self.ads.checkpoint = after
        self.assertEqual(self.action(value, 'claim', command).status_code, 500)
        self.ads.checkpoint = None
        self.restart()
        self.assertEqual(self.action(value, 'claim', command).json()['state'], 'Claimed')
        self.assertEqual(self.coins(), 1650)
        self.assertEqual(self.status()['claimedToday'], 1)

    def test_17_version_snapshot_and_owed_verified_claim_survives_rollout_disable(self):
        value = self.reserve()
        self.verify(value)
        self.config['version'] = 'rewarded-shop-v2'
        self.config['enabled'] = False
        self.write_config()
        self.restart(False)
        result = self.action(value, 'claim').json()
        self.assertEqual(result['configVersion'], 'rewarded-shop-v1')
        self.assertEqual(result['receipt']['coins'], 400)
        self.assertFalse(self.status()['enabled'])
        for field, value in (('rewardCoins', 401), ('dailyLimit', 4), ('utcOffsetSeconds', 0), ('cooldownSeconds', 599)):
            candidate = dict(self.config)
            candidate[field] = value
            with self.assertRaises(ValidationError):
                RewardedAdsConfig.model_validate(candidate)

    def test_18_monotonic_clock_and_stale_authenticated_actor_use_current_claim_time(self):
        actor = self.authority.authenticate(self.owner['token'])
        value = self.reserve()
        self.verify(value)
        self.now += 20
        result = self.ads.claim(actor, value['opportunityId'], RewardedAdCommand(commandId=ident()))
        self.assertEqual(result['claimedAt'], self.now)
        self.now -= 100
        state = self.status()
        self.assertEqual(state['serverUtc'], result['claimedAt'])
        self.assertEqual(state['cooldownRemainingSeconds'], 600)

    def test_19_migration6_preserves_wallet_and_backup_restore_exact_new_receipts(self):
        value = self.claimed()
        before = self.wallet()
        snapshot = self.root / 'backup.sqlite3'
        restored = self.root / 'restored.sqlite3'
        self.assertEqual(backup_database(self.path, snapshot)['schemaVersion'], SCHEMA_VERSION)
        self.assertEqual(restore_database(snapshot, restored)['schemaVersion'], SCHEMA_VERSION)
        app = create_app(restored, CONFIG, lambda: self.now, ads_config_path=self.config_path, ads_verifier=self.verifier)
        with TestClient(app) as client:
            self.assertEqual(client.get('/v1/wallet', headers=self.headers()).json(), before)
            result = client.get('/v1/ads/rewarded/opportunities/' + value['opportunityId'], headers=self.headers()).json()
            self.assertEqual(result['receipt'], value['receipt'])
        # Construct the exact prior6 schema, not current commerce columns under
        # a changed version number. Trusted wallet/receipt rows are retained.
        migration = self.root / 'prior6.sqlite3'
        with closing(sqlite3.connect(snapshot)) as db, closing(sqlite3.connect(migration)) as old:
            from tests.legacy_schema_fixture import copy_legacy
            copy_legacy(db, old, 6)
        Database(migration)
        with closing(sqlite3.connect(migration)) as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], SCHEMA_VERSION)
            self.assertEqual(db.execute('SELECT balances,revision FROM wallets WHERE player_id=?', (self.owner['playerId'],)).fetchone(),
                             (canonical([before['coins'], before['stars'], *before['starting'], *before['tools'], before['lives']]), before['revision']))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rewarded_ad_opportunities').fetchone()[0], 0)

    def test_20_synthetic_adapter_never_accepts_production_mode_badkeys_or_badresult(self):
        for mode in ('production', '', 'local-production'):
            with self.assertRaises(ValueError):
                SyntheticHmacCompletionVerifier(self.key, mode=mode)
        with self.assertRaises(ValueError):
            SyntheticHmacCompletionVerifier(b'short', mode='local')
        class Malformed:
            configured = True
            mode = 'malformed-test'
            def verify(self, payload):
                return VerifiedAdCompletion(12, 'event', ident(), ident(), 'shop_rewarded', 'v1', 0)
        ads = RewardedAds(self.authority, self.config_path, Malformed())
        self.expect(403, lambda: ads.accept_trusted_completion({}))

    def test_21_foreign_verified_binding_and_deletion_during_verification_no_credit(self):
        value = self.reserve()
        evidence = self.evidence(value)
        original = self.ads.verifier
        authority, player = self.authority, self.owner['playerId']
        class DeleteDuringVerify:
            configured = True
            mode = 'synthetic-delete-race'
            def verify(self, payload):
                result = original.verify(payload)
                with authority.database.transaction() as db:
                    db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (player, self_now))
                return result
        self_now = self.now
        self.ads.verifier = DeleteDuringVerify()
        self.expect(410, lambda: self.ads.accept_trusted_completion(evidence))
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rewarded_ad_completions').fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rewards WHERE source='rewarded_ad'").fetchone()[0], 0)

    def test_22_historical_wallet_not_initialized_cannot_watch_for_unspendable_reward(self):
        with self.authority.database.transaction() as db:
            db.execute('UPDATE wallets SET initialized=0 WHERE player_id=?', (self.owner['playerId'],))
        self.assertEqual(self.status()['reason'], 'wallet_migration_required')
        self.assertEqual(self.post('/v1/ads/rewarded/reserve', {'commandId': ident(), 'placement': 'shop_rewarded'}).status_code, 409)

    def reported_mode(self):
        self.config['completionMode'] = 'sdk_client_reported_capped'
        self.write_config()
        self.restart(False)

    def test_23_explicit_sdk_reported_mode_server_claim_credits_lower_trust_only(self):
        self.reported_mode()
        self.assertTrue(self.status()['available'])
        self.assertEqual(self.status()['reason'], 'ready_client_reported_capped')
        self.assertEqual(self.status()['verificationMode'], 'sdk_client_reported_capped')
        value = self.reserve()
        self.assertEqual(value['completionMode'], 'sdk_client_reported_capped')
        self.assertEqual(self.action(value, 'claim').json()['state'], 'Reserved')
        reported = self.action(value, 'client-completion').json()
        self.assertEqual(reported['state'], 'CompletedReported')
        self.assertFalse(reported['completionAuthoritative'])
        self.assertEqual(reported['verifiedAt'], 0)
        self.assertEqual(self.coins(), 1250)
        command = ident()
        first = self.action(value, 'claim', command).json()
        self.assertFalse(first['completionAuthoritative'])
        self.assertEqual(first['receipt']['completionSource'], 'sdk_client_reported_capped')
        self.assertEqual(self.action(value, 'claim', command).json(), first)
        self.assertEqual(self.coins(), 1650)
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute("SELECT source FROM rewards WHERE source_key=?", (value['opportunityId'],)).fetchone()[0], 'client_reported_ad')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rewarded_ad_completions').fetchone()[0], 0)

    def test_24_forgeable_sdk_report_can_farm_only_three_fixed_claims_per_day(self):
        # This deliberately uses no real ad/network and discloses the chosen
        # lower-trust policy's abuse boundary, rather than proving impressions.
        self.reported_mode()
        for index in range(3):
            value = self.reserve()
            self.action(value, 'client-completion')
            self.assertEqual(self.action(value, 'claim').json()['receipt']['coins'], 400)
            if index < 2:
                self.assertEqual(self.post('/v1/ads/rewarded/reserve', {'commandId': ident(), 'placement': 'shop_rewarded'}).status_code, 409)
                self.now += 600
        self.now += 600
        self.assertEqual(self.post('/v1/ads/rewarded/reserve', {'commandId': ident(), 'placement': 'shop_rewarded'}).status_code, 409)
        self.assertEqual(self.coins(), 2450)
        self.assertEqual(self.status()['remainingToday'], 0)

    def test_25_reported_pending_expiry_cancel_and_restart_never_fabricate_verified(self):
        self.reported_mode()
        value = self.reserve()
        self.action(value, 'client-completion')
        self.assertEqual(self.action(value, 'cancel').json()['state'], 'Cancelled')
        self.assertEqual(self.status()['claimedToday'], 0)
        value = self.reserve()
        self.action(value, 'client-completion')
        self.restart(False)
        self.assertEqual(self.status()['activeOpportunity']['state'], 'CompletedReported')
        # Review 136, owner decision: a watched ad keeps its reward past the 900 s window.
        self.now = value['expiresAt'] + 86400
        self.assertEqual(self.status()['activeOpportunity']['state'], 'CompletedReported')
        self.assertEqual(self.action(value, 'claim').json()['state'], 'Claimed')
        self.assertEqual(self.coins(), 1650)
        self.assertEqual(self.status()['cooldownRemainingSeconds'], 600)

    def test_25b_late_report_within_a_day_is_accepted_and_limits_still_hold(self):
        self.reported_mode()
        value = self.reserve()
        self.now = value['expiresAt'] + 60
        self.assertEqual(self.get('/v1/ads/rewarded/opportunities/' + value['opportunityId']).json()['state'], 'Expired')
        self.assertEqual(self.action(value, 'client-completion').json()['state'], 'CompletedReported')
        self.assertEqual(self.action(value, 'claim').json()['state'], 'Claimed')
        self.assertEqual(self.coins(), 1650)
        # Another reservation inside the cooldown is still refused.
        response = self.client.post('/v1/ads/rewarded/reserve', headers=self.headers(), json={'commandId': ident(), 'placement': value['placement']})
        self.assertEqual((response.status_code, response.json()['error']), (409, 'ad_cooldown'))

    def test_25c_report_after_a_day_or_after_cancel_stays_closed(self):
        self.reported_mode()
        value = self.reserve()
        self.now = value['createdAt'] + 86400
        self.get('/v1/ads/rewarded/opportunities/' + value['opportunityId'])
        self.assertEqual(self.action(value, 'client-completion').status_code, 409)
        other = self.reserve()
        self.action(other, 'cancel')
        self.assertEqual(self.action(other, 'client-completion').status_code, 409)
        self.assertEqual(self.coins(), 1250)

    def test_25d_late_report_cannot_run_beside_a_newer_open_ad(self):
        self.reported_mode()
        first = self.reserve()
        self.now = first['expiresAt'] + 60
        self.get('/v1/ads/rewarded/opportunities/' + first['opportunityId'])
        self.reserve()
        self.assertEqual(self.action(first, 'client-completion').status_code, 409)

    def test_26_reported_mode_snapshot_not_reinterpreted_after_server_config_switch(self):
        self.reported_mode()
        value = self.reserve()
        self.action(value, 'client-completion')
        self.config['completionMode'] = 'trusted_completion'
        self.config['enabled'] = False
        self.write_config()
        self.restart()
        result = self.action(value, 'claim').json()
        self.assertEqual(result['state'], 'Claimed')
        self.assertEqual(result['completionMode'], 'sdk_client_reported_capped')
        self.assertFalse(result['completionAuthoritative'])
        self.assertEqual(result['receipt']['completionSource'], 'sdk_client_reported_capped')

    def test_27_trusted_opportunity_cannot_be_downgraded_by_configuration_change(self):
        value = self.reserve()
        self.action(value, 'client-completion')
        self.reported_mode()
        result = self.action(value, 'claim').json()
        self.assertEqual(result['state'], 'AwaitingVerification')
        self.assertEqual(result['completionMode'], 'trusted_completion')
        self.assertEqual(self.coins(), 1250)

    def test_28_parallel_reported_claims_share_cap_and_commit_one_wallet_revision(self):
        self.reported_mode()
        value = self.reserve()
        self.action(value, 'client-completion')
        before = self.wallet()['revision']
        actors = [self.authority.authenticate(self.owner['token']) for _ in range(8)]
        barrier = threading.Barrier(8)
        def claim(index):
            barrier.wait(timeout=4)
            return self.ads.claim(actors[index], value['opportunityId'], RewardedAdCommand(commandId=ident()))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            result = list(pool.map(claim, range(8)))
        self.assertTrue(all(row['state'] == 'Claimed' and not row['completionAuthoritative'] for row in result))
        self.assertEqual(self.wallet()['revision'], before + 1)
        self.assertEqual(self.coins(), 1650)
        self.assertEqual(self.status()['claimedToday'], 1)

    def test_29_reported_midnight_claim_uses_new_day_and_cannot_skip_cooldown(self):
        self.reported_mode()
        boundary = 501 * 86400 - 36000
        self.now = boundary - 1
        value = self.reserve()
        self.action(value, 'client-completion')
        self.now = boundary + 1
        result = self.action(value, 'claim').json()
        self.assertEqual(result['claimedDay'], self.status()['day'])
        self.assertEqual(result['claimedAt'], self.now)
        self.assertEqual(self.status()['claimedToday'], 1)
        self.assertEqual(self.status()['cooldownRemainingSeconds'], 600)

    def test_30_reported_revocation_blocks_cached_claim_and_deleted_pending_no_grant(self):
        self.reported_mode()
        value = self.reserve()
        self.action(value, 'client-completion')
        actor = self.authority.authenticate(self.owner['token'])
        command = ident()
        first = self.ads.claim(actor, value['opportunityId'], RewardedAdCommand(commandId=command))
        self.assertEqual(first['state'], 'Claimed')
        self.authority.revoke(self.owner['token'])
        self.expect(401, lambda: self.ads.claim(actor, value['opportunityId'], RewardedAdCommand(commandId=command)))
        self.owner = self.authority.provision(player=self.owner['playerId'])
        self.now += 600
        pending = self.reserve()
        self.action(pending, 'client-completion')
        actor = self.authority.authenticate(self.owner['token'])
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.owner['playerId'], self.now))
        self.expect(410, lambda: self.ads.claim(actor, pending['opportunityId'], RewardedAdCommand(commandId=ident())))
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rewards WHERE source='client_reported_ad'").fetchone()[0], 1)

    def test_31_reported_before_after_commit_cuts_recover_without_quota_or_wallet_duplication(self):
        self.reported_mode()
        value = self.reserve()
        self.action(value, 'client-completion')
        command = ident()
        def fail(point):
            if point == cut:
                raise OSError('synthetic-transaction-cut')
        cut = 'BeforeCommit'
        self.ads.checkpoint = fail
        self.assertEqual(self.action(value, 'claim', command).status_code, 500)
        self.ads.checkpoint = None
        self.assertEqual(self.coins(), 1250)
        self.assertEqual(self.status()['claimedToday'], 0)
        cut = 'AfterCommit'
        self.ads.checkpoint = fail
        self.assertEqual(self.action(value, 'claim', command).status_code, 500)
        self.ads.checkpoint = None
        self.restart(False)
        result = self.action(value, 'claim', command).json()
        self.assertEqual(result['receipt']['completionSource'], 'sdk_client_reported_capped')
        self.assertEqual(self.coins(), 1650)
        self.assertEqual(self.status()['claimedToday'], 1)

    def test_32_real_schema6_backup_validates_and_failed_migration_rolls_back_all_ads_objects(self):
        source = self.root / 'schema6.sqlite3'
        with self.authority.database.connect() as current, closing(sqlite3.connect(source)) as old:
            from tests.legacy_schema_fixture import copy_legacy
            copy_legacy(current, old, 6)
        snapshot = self.root / 'six-backup.sqlite3'
        self.assertEqual(backup_database(source, snapshot)['schemaVersion'], 6)
        # A collision in the second new table must roll the first table/indexes
        # and schema update back, preserving the complete old wallet.
        with closing(sqlite3.connect(source)) as db:
            db.execute('CREATE TABLE rewarded_ad_completions(collision INTEGER)')
            db.commit()
        with self.assertRaises(sqlite3.OperationalError):
            Database(source)
        with closing(sqlite3.connect(source)) as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 6)
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='rewarded_ad_opportunities'").fetchone())
            self.assertEqual(db.execute('SELECT COUNT(*) FROM wallet_ledger').fetchone()[0], 2)

    def test_33_source_clock_cooldown_is_claim_time_not_client_report_time(self):
        self.reported_mode()
        value = self.reserve()
        self.action(value, 'client-completion')
        self.now += 700
        result = self.action(value, 'claim').json()
        self.assertEqual(result['claimedAt'], self.now)
        self.assertEqual(self.status()['cooldownRemainingSeconds'], 600)
        self.now += 599
        self.assertEqual(self.post('/v1/ads/rewarded/reserve', {'commandId': ident(), 'placement': 'shop_rewarded'}).status_code, 409)
        self.now += 1
        self.reserve()

    def test_34_reserve_denial_rollback_and_cached_receipt_precede_eligibility_but_not_wallet_guards(self):
        self.reported_mode()

        def financial_state():
            # The monotonic clock may advance on any authenticated request.
            # No rejected reservation may change any wallet, grant, command,
            # completion or opportunity. Include both actors' rows as a control.
            with self.authority.database.connect() as db:
                return {table: sorted(canonical(dict(row)) for row in db.execute('SELECT * FROM ' + table))
                        for table in ('wallets', 'wallet_ledger', 'rewards', 'commands',
                                      'commerce_orders', 'rewarded_ad_opportunities', 'rewarded_ad_completions')}

        def rejected(code, status=409):
            command = ident()
            before = financial_state()
            response = self.post('/v1/ads/rewarded/reserve',
                                 {'commandId': command, 'placement': 'shop_rewarded'})
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.json(), {'error': code})
            self.assertEqual(financial_state(), before)
            with self.authority.database.connect() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM commands WHERE player_id=? AND operation='ads.reserve' AND command_id=?",
                                            (self.owner['playerId'], command)).fetchone()[0], 0)

        command = ident()
        reserved = self.reserve(command)

        def cached_success():
            before = financial_state()
            self.assertEqual(self.reserve(command), reserved)
            self.assertEqual(financial_state(), before)

        rejected('ad_opportunity_pending')
        cached_success()  # Same exact command must not be denied by its own slot.
        self.action(reserved, 'client-completion')
        self.assertEqual(self.action(reserved, 'claim').json()['state'], 'Claimed')
        rejected('ad_cooldown')
        cached_success()  # Historical Reserved receipt is returned, never a new ad.
        for _ in range(2):
            self.now += 600
            other = self.reserve()
            self.action(other, 'client-completion')
            self.assertEqual(self.action(other, 'claim').json()['state'], 'Claimed')
        rejected('ad_daily_limit')
        cached_success()
        self.assertEqual(self.coins(), 2450)

        self.config['enabled'] = False
        self.write_config()
        self.restart(False)
        rejected('ads_disabled', 503)
        cached_success()  # Rollout disable is also after the successful receipt lookup.

        self.config['enabled'] = True
        self.config['completionMode'] = 'trusted_completion'
        self.write_config()
        self.restart(False)
        rejected('trusted_completion_unavailable', 503)
        cached_success()

        # These wallet guard errors happen BEFORE receipt lookup. They can
        # reject a command that really committed earlier, so they are never
        # definitive evidence that a recovered unknown reservation is absent.
        refund = ident()
        with self.authority.database.transaction() as db:
            db.execute('''INSERT INTO commerce_orders
                (id,player_id,catalog_version,internal_product,store_product,app_id,sandbox,amount_minor,currency,coins,binding,state,created_at,updated_at)
                VALUES(?,?,'synthetic','test','test',1,1,1,'RUB',1,?,'RefundReview',?,?)''',
                       (refund, self.owner['playerId'], ident(), self.now, self.now))
        for expected in ('wallet_refund_review_required', 'wallet_migration_required'):
            if expected == 'wallet_migration_required':
                with self.authority.database.transaction() as db:
                    db.execute('DELETE FROM commerce_orders WHERE id=?', (refund,))
                    db.execute('UPDATE wallets SET initialized=0 WHERE player_id=?', (self.owner['playerId'],))
            before = financial_state()
            response = self.post('/v1/ads/rewarded/reserve',
                                 {'commandId': command, 'placement': 'shop_rewarded'})
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json(), {'error': expected})
            self.assertEqual(financial_state(), before)
            with self.authority.database.connect() as db:
                row = db.execute("SELECT response_json FROM commands WHERE player_id=? AND operation='ads.reserve' AND command_id=?",
                                 (self.owner['playerId'], command)).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(json.loads(row['response_json']), reserved)


    def local_status(self, offset, owner=None):
        response = self.get('/v1/ads/rewarded/status?utcOffsetSeconds=' + str(offset), owner)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_35_player_local_midnight_half_quarter_hour_and_extreme_offsets(self):
        for offset in (-43200, -18000, 0, 19800, 20700, 50400):
            with self.subTest(offset=offset):
                owner = self.authority.provision(lifetime=2592000)
                boundary = ((self.now + offset) // 86400 + 2) * 86400 - offset
                self.now = boundary - 1201
                initial = self.local_status(offset, owner)
                self.assertEqual(initial['utcOffsetSeconds'], offset)
                self.assertEqual(initial['nextDayAt'], boundary)
                for index in range(3):
                    value = self.reserve(owner=owner)
                    self.verify(value)
                    result = self.action(value, 'claim', owner=owner)
                    self.assertEqual(result.status_code, 200, result.text)
                    if index < 2:
                        self.now += 600
                self.assertEqual(self.local_status(offset, owner)['remainingToday'], 0)
                self.now = boundary
                after = self.local_status(offset, owner)
                self.assertEqual(after['remainingToday'], 3)
                self.assertEqual(after['cooldownRemainingSeconds'], 599)
                self.assertFalse(after['available'])
                self.now += 599
                self.assertTrue(self.local_status(offset, owner)['available'])

    def test_36_timezone_changes_do_not_reset_current_quota_and_are_durable(self):
        initial = self.local_status(20700)
        for index in range(3):
            self.claimed()
            if index < 2:
                self.now += 600
        for offset in (50400, -43200, 19800, 0, -18000):
            value = self.local_status(offset)
            self.assertEqual(value['utcOffsetSeconds'], 20700)
            self.assertEqual(value['nextDayAt'], initial['nextDayAt'])
            self.assertEqual(value['remainingToday'], 0)
        self.restart()
        self.assertEqual(self.status()['remainingToday'], 0)
        self.now = initial['nextDayAt']
        value = self.status()
        self.assertEqual(value['utcOffsetSeconds'], -18000)
        self.assertEqual(value['remainingToday'], 3)
        self.assertEqual(value['dayStartedAt'], initial['nextDayAt'])
        self.assertEqual((value['nextDayAt'] - 18000) % 86400, 0)

    def test_37_offset_transition_has_no_artificial_second_24_hour_lockout(self):
        for source, target, transition_seconds in ((3600, 7200, 23 * 3600),
                                                    (7200, 3600, 3600),
                                                    (50400, -43200, 2 * 3600)):
            with self.subTest(source=source, target=target):
                owner = self.authority.provision(lifetime=2592000)
                old = self.local_status(source, owner)
                self.local_status(target, owner)
                self.now = old['nextDayAt']
                value = self.local_status(target, owner)
                self.assertEqual(value['dayStartedAt'], self.now)
                self.assertEqual(value['nextDayAt'] - self.now, transition_seconds)
                self.now = value['nextDayAt']
                following = self.local_status(target, owner)
                self.assertEqual(following['nextDayAt'] - following['dayStartedAt'], 86400)

    def test_38_pending_verified_and_committed_claim_survive_calendar_change(self):
        old = self.local_status(19800)
        self.now = old['nextDayAt'] - 10
        pending = self.reserve()
        proof = self.evidence(pending)
        self.ads.accept_trusted_completion(proof)
        self.local_status(-43200)
        self.now = old['nextDayAt'] + 1
        self.restart()
        command = ident()
        first = self.action(pending, 'claim', command).json()
        self.assertEqual(first['state'], 'Claimed')
        self.assertEqual(first['utcOffsetSeconds'], 19800)
        self.assertEqual(first['claimedUtcOffsetSeconds'], -43200)
        self.assertEqual(first['claimedDay'], (self.now - 43200) // 86400)
        self.assertEqual(self.action(pending, 'claim', command).json(), first)
        self.ads.accept_trusted_completion(proof)
        self.assertEqual(self.status()['claimedToday'], 1)
        self.assertEqual(self.status()['cooldownRemainingSeconds'], 600)
        self.assertEqual(self.coins(), 1650)

    def test_39_local_calendar_validates_input_without_using_a_client_clock(self):
        initial = self.local_status(20700)
        self.claimed()
        for raw in ('50401', '-43201', '901', 'true', '1.5', '999999999999999999999'):
            self.assertEqual(self.get('/v1/ads/rewarded/status?utcOffsetSeconds=' + raw).status_code, 422)
        actor = self.authority.authenticate(self.owner['token'])
        for raw in (True, 1.5, '36000'):
            self.expect(422, lambda: self.ads.status(actor, raw))
        self.now -= 3600
        value = self.local_status(-43200)
        self.assertEqual(value['claimedToday'], 1)
        self.assertEqual(value['cooldownRemainingSeconds'], 600)
        self.assertEqual(value['nextDayAt'], initial['nextDayAt'])
        self.assertEqual(self.coins(), 1650)

    def test_40_schema7_upgrade_keeps_existing_reward_receipts_and_quota(self):
        first = self.claimed()
        before = self.wallet()
        prior = self.root / 'prior7.sqlite3'
        with self.authority.database.connect() as current, closing(sqlite3.connect(prior)) as old:
            from tests.legacy_schema_fixture import copy_legacy
            copy_legacy(current, old, 7)
        app = create_app(prior, CONFIG, lambda: self.now, ads_config_path=self.config_path, ads_verifier=self.verifier)
        with TestClient(app) as client:
            self.assertEqual(client.get('/v1/wallet', headers=self.headers()).json(), before)
            value = client.get('/v1/ads/rewarded/status?utcOffsetSeconds=-43200', headers=self.headers()).json()
            self.assertEqual(value['claimedToday'], 1)
            self.assertEqual(value['utcOffsetSeconds'], 36000)
            self.assertEqual(value['cooldownRemainingSeconds'], 600)
            read = client.get('/v1/ads/rewarded/opportunities/' + first['opportunityId'], headers=self.headers()).json()
            self.assertEqual(read['receipt'], first['receipt'])
            self.assertEqual(read['utcOffsetSeconds'], 36000)
            result = client.post('/v1/ads/rewarded/opportunities/' + first['opportunityId'] + '/claim', headers=self.headers(), json={'commandId': ident()}).json()
            self.assertEqual(result['receipt'], first['receipt'])
            self.assertEqual(client.get('/v1/wallet', headers=self.headers()).json(), before)


    def zone_status(self, zone, owner=None, offset=0):
        response = self.client.get('/v1/ads/rewarded/status', headers=self.headers(owner),
                                   params={'utcOffsetSeconds': offset, 'timeZoneId': zone})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_41_iana_dst_local_midnights_are_23_or_25_hours_without_extra_reset(self):
        for zone_name, date, hours in (('America/New_York', (2026, 3, 8), 23),
                                       ('Europe/Berlin', (2026, 3, 29), 23),
                                       ('Europe/Berlin', (2026, 10, 25), 25),
                                       ('America/New_York', (2026, 11, 1), 25)):
            with self.subTest(zone=zone_name, date=date):
                zone = ZoneInfo(zone_name)
                midnight = datetime(*date, tzinfo=zone)
                self.now = int(midnight.timestamp()) + 600
                owner = self.authority.provision(lifetime=2592000)
                first = self.zone_status(zone_name, owner)
                self.assertEqual(first['timeZoneId'], zone_name)
                self.assertEqual(first['dayStartedAt'], int(midnight.timestamp()))
                self.assertEqual(first['nextDayAt'] - first['dayStartedAt'], hours * 3600)
                self.assertEqual(first['nextDayAt'], int((midnight + timedelta(days=1)).timestamp()))
                for index in range(3):
                    value = self.reserve(owner=owner)
                    self.verify(value)
                    result = self.action(value, 'claim', owner=owner)
                    self.assertEqual(result.status_code, 200, result.text)
                    if index < 2:
                        self.now += 600
                self.now = first['nextDayAt'] - 1
                before = self.zone_status(zone_name, owner, offset=50400)
                self.assertEqual(before['remainingToday'], 0)
                self.assertEqual(before['dayStartedAt'], first['dayStartedAt'])
                self.assertEqual(before['nextDayAt'], first['nextDayAt'])
                self.assertEqual(before['utcOffsetSeconds'], int(datetime.fromtimestamp(self.now, zone).utcoffset().total_seconds()))
                self.now += 1
                after = self.zone_status(zone_name, owner)
                self.assertEqual(after['remainingToday'], 3)
                self.assertEqual(after['nextDayAt'] - after['dayStartedAt'], 86400)

    def test_42_iana_change_and_other_device_cannot_truncate_current_quota(self):
        first = self.zone_status('Asia/Kathmandu')
        self.claimed()
        for zone in ('Pacific/Kiritimati', 'Etc/GMT+12', 'Europe/Moscow'):
            changed = self.zone_status(zone)
            self.assertEqual(changed['timeZoneId'], 'Asia/Kathmandu')
            self.assertEqual(changed['claimedToday'], 1)
            self.assertEqual(changed['nextDayAt'], first['nextDayAt'])
        self.restart()
        self.now = first['nextDayAt']
        final = self.status()
        self.assertEqual(final['timeZoneId'], 'Europe/Moscow')
        self.assertEqual(final['remainingToday'], 3)
        self.assertEqual(final['dayStartedAt'], first['nextDayAt'])
        self.assertEqual((final['nextDayAt'] + 10800) % 86400, 0)

    def test_43_iana_invalid_paths_unavailable_zone_and_wrong_types_are_rejected(self):
        first = self.zone_status('Etc/UTC')
        for zone in ('../UTC', '/etc/passwd', 'Europe/../UTC', 'America/NoSuchZone', 'A' * 65, 'Europe\\Moscow'):
            response = self.client.get('/v1/ads/rewarded/status', headers=self.headers(), params={'timeZoneId': zone})
            self.assertEqual(response.status_code, 422, response.text)
        actor = self.authority.authenticate(self.owner['token'])
        for zone in (True, 123, []):
            self.expect(422, lambda: self.ads.status(actor, 0, zone))
        self.assertEqual(self.status()['nextDayAt'], first['nextDayAt'])
        self.assertEqual(self.coins(), 1250)

    def test_44_verified_claim_across_dst_uses_actual_claim_local_date_and_recovers(self):
        zone = ZoneInfo('America/New_York')
        self.now = int(datetime(2026, 3, 8, 0, 10, tzinfo=zone).timestamp())
        owner = self.authority.provision(lifetime=2592000)
        first = self.zone_status('America/New_York', owner)
        value = self.reserve(owner=owner)
        self.assertEqual(value['utcOffsetSeconds'], -18000)
        self.verify(value)
        self.now = first['nextDayAt'] + 1800
        self.restart()
        command = ident()
        response = self.action(value, 'claim', command, owner)
        self.assertEqual(response.status_code, 200, response.text)
        claimed = response.json()
        self.assertEqual(claimed['utcOffsetSeconds'], -18000)
        self.assertEqual(claimed['claimedUtcOffsetSeconds'], -14400)
        self.assertEqual(claimed['claimedDay'], (self.now - 14400) // 86400)
        self.assertEqual(self.action(value, 'claim', command, owner).json(), claimed)
        current = self.zone_status('America/New_York', owner)
        self.assertEqual(current['claimedToday'], 1)
        self.assertEqual(current['cooldownRemainingSeconds'], 600)
        self.assertEqual(self.get('/v1/wallet', owner).json()['coins'], 1650)


if __name__ == '__main__':
    unittest.main()
