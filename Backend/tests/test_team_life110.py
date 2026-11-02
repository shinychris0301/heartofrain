"""Real temporary ASGI/SQLite help transactions; labelled capacity fixtures only."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid
import secrets
from unittest.mock import patch

from fastapi.testclient import TestClient
from Crypto.PublicKey import ECC

from hotr_backend.api import create_app
from hotr_backend.operations import _validate, backup_database, restore_database
from hotr_backend.storage import Database, SCHEMA_VERSION
from hotr_backend.team_life_schema110 import TEAM_LIFE_V12_DDL
from hotr_backend.wallet import ZERO, project
from tests.legacy_schema_fixture import copy_legacy
from tests import test_messaging as messaging_fixtures

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class TeamLife110Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-teamlife110-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'authority.sqlite3'
        self.now = 2_000_000_000
        self.clients = []
        self.addCleanup(lambda: [c.close() for c in self.clients])
        self.open()
        self.users = [self.authority.provision(lifetime=2_592_000) for _ in range(7)]
        self.team = self.post('/v1/teams', name='Life Team', badgeId='oak')['teamId']
        for user in range(1, 7):
            self.post('/v1/teams/' + self.team + '/join', user)
        self.base = '/v1/teams/' + self.team + '/life-requests'

    def open(self, path=None, enabled=True):
        self.app = create_app(path or self.path, CONFIG, lambda: self.now, social_enabled=enabled, identity_enabled=True)
        self.authority = self.app.state.authority
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.clients.append(self.client)

    def headers(self, user=0):
        return {'Authorization': 'Bearer ' + self.users[user]['token']}

    def get(self, path, user=0, status=200, **kwargs):
        r = self.client.get(path, headers=self.headers(user), **kwargs)
        self.assertEqual(r.status_code, status, r.text)
        return r.json()

    def post(self, path, user=0, status=200, command=None, **values):
        r = self.client.post(path, headers=self.headers(user), json={'commandId': command or ident(), **values})
        self.assertEqual(r.status_code, status, r.text)
        return r.json()

    def request(self, user=0, command=None):
        return self.post(self.base, user, command=command)

    def help(self, request, user=1, **kwargs):
        return self.post(self.base + '/' + request['requestId'] + '/help', user, **kwargs)

    def claim(self, request, **kwargs):
        return self.post('/v1/life-requests/' + request['requestId'] + '/claim', **kwargs)

    def card(self, request, user=0):
        return next(r for r in self.get(self.base, user)['requests'] if r['requestId'] == request['requestId'])

    def fill(self, request):
        for user in range(1, 6):
            self.help(request, user)

    def capacity(self, lives, user=0):
        # Explicit test-operator ledger change, not an invented game outcome or
        # shipped route. Preserve the real regeneration and life timer rules.
        actor = self.authority.authenticate(self.users[user]['token'])
        with self.authority.database.transaction() as db:
            actor = self.authority._transaction_actor(db, actor)
            self.app.state.wallet._regenerate(db, actor)
            row = self.app.state.wallet._row(db, actor.player)
            delta = ZERO.copy()
            delta[10] = lives - json.loads(row['balances'])[10]
            if delta[10]:
                project(db, actor.player, 'fixture110/capacity/' + ident(), delta, actor.now)
            self.app.state.wallet._life_timer(db, actor, lives)

    def count(self, table):
        with self.authority.database.connect() as db:
            return db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def finance(self):
        with self.authority.database.connect() as db:
            return {name: [tuple(r) for r in db.execute('SELECT * FROM ' + name + ' ORDER BY 1')]
                    for name in ('wallets', 'wallet_ledger', 'rewards', 'gameplay_attempts', 'commerce_orders', 'commerce_credits')}

    def test_01_full_wallet_can_request_and_old_text_consumers_receive_a_stable_real_message(self):
        before = self.finance()
        r = self.request()
        self.assertEqual(self.finance(), before)
        card = self.card(r)
        self.assertEqual((card['state'], card['received'], card['required'], card['canHelp']), ('Open', 0, 5, False))
        feed = self.get('/v1/messages/Team/' + self.team + '?tail=true&limit=8')
        msg = next(m for m in feed['messages'] if m['messageId'] == r['messageId'])
        self.assertEqual(msg['sequence'], card['sequence'])
        self.assertEqual(msg['text'], 'Life request')
        self.assertEqual(r['closesAt'] if 'closesAt' in r else card['closesAt'], self.now + 14400)

    def test_02_exact_request_and_new_id_duplicate_do_not_restart_cooldown(self):
        command = ident()
        first = self.request(command=command)
        self.assertEqual(self.request(command=command), first)
        self.now += 60
        self.assertEqual(self.request(), first)
        self.assertEqual((self.count('team_life_requests'), self.count('social_messages')), (1, 1))
        self.assertEqual(self.get(self.base)['nextRequestAt'], 2_000_000_000 + 14400)

    def test_03_self_help_and_client_amount_or_clock_fields_are_rejected(self):
        r = self.request()
        self.help(r, 0, status=409)
        self.post(self.base, status=422, amount=5)
        self.post(self.base + '/' + r['requestId'] + '/help', 1, status=422, serverUtc=self.now)
        self.assertEqual(self.count('team_life_donations'), 0)

    def test_04_help_never_debits_donor_and_duplicate_ids_or_restart_do_not_duplicate_credit(self):
        r = self.request()
        before = self.finance()
        command = ident()
        first = self.help(r, command=command)
        self.assertEqual(self.help(r, command=command), first)
        self.assertEqual(self.help(r), first)
        self.client.close()
        self.open()
        self.assertEqual(self.help(r, command=command), first)
        self.assertEqual(self.count('team_life_donations'), 1)
        self.assertEqual(self.card(r)['received'], 1)
        self.assertEqual(self.finance(), before)

    def test_05_concurrent_last_slot_has_one_winner_and_no_sixth_donation(self):
        r = self.request()
        for user in range(1, 5):
            self.help(r, user)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda u: self.client.post(self.base + '/' + r['requestId'] + '/help',
                headers=self.headers(u), json={'commandId': ident()}), (5, 6)))
        self.assertEqual(sorted(x.status_code for x in results), [200, 409])
        self.assertEqual((self.card(r)['received'], self.count('team_life_donations')), (5, 5))

    def test_06_open_partial_cannot_collect_and_expired_partial_preserves_earned_life(self):
        r = self.request()
        self.help(r)
        self.claim(r, status=409)
        self.now += 14400
        card = self.card(r)
        self.assertEqual((card['state'], card['closeReason'], card['remaining']), ('Claimable', 'Expired', 1))
        self.help(r, 2, status=409)
        self.capacity(4)
        result = self.claim(r)
        self.assertEqual((result['state'], result['creditedLives'], result['lives'], result['remaining']), ('Collected', 1, 5, 0))

    def test_07_full_claim_defers_and_later_new_intent_collects_without_replaying_zero_credit(self):
        r = self.request()
        self.fill(r)
        self.assertEqual(self.card(r)['collectBlockedReason'], 'FullLives')
        command = ident()
        deferred = self.claim(r, command=command)
        self.assertEqual((deferred['state'], deferred['creditedLives'], deferred['remaining']), ('Deferred', 0, 5))
        self.capacity(0)
        self.assertEqual(self.claim(r, command=command), deferred)
        self.assertEqual(self.get('/v1/wallet')['lives'], 0)
        result = self.claim(r)
        self.assertEqual((result['creditedLives'], result['remaining'], result['nextLifeAt']), (5, 0, 0))

    def test_08_partial_capacity_keeps_remainder_then_credits_it_exactly_once(self):
        r = self.request()
        self.fill(r)
        self.capacity(3)
        first = self.claim(r)
        self.assertEqual((first['state'], first['creditedLives'], first['claimed'], first['remaining']), ('PartiallyCollected', 2, 2, 3))
        self.assertEqual(self.get('/v1/life-requests/owned')['requests'][0]['remaining'], 3)
        self.capacity(2)
        command = ident()
        second = self.claim(r, command=command)
        self.assertEqual(self.claim(r, command=command), second)
        self.assertEqual((second['state'], second['creditedLives'], second['remaining']), ('Collected', 3, 0))
        self.assertEqual(self.get('/v1/life-requests/owned')['requests'], [])

    def test_09_simultaneous_claims_cannot_overcredit_or_overconsume(self):
        r = self.request()
        self.fill(r)
        self.capacity(0)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.client.post('/v1/life-requests/' + r['requestId'] + '/claim',
                headers=self.headers(), json={'commandId': ident()}), range(2)))
        self.assertEqual(sorted(x.status_code for x in results), [200, 409])
        self.assertEqual((self.card(r)['claimed'], self.get('/v1/wallet')['lives']), (5, 5))

    def test_10_regeneration_materializes_before_claim_and_partial_timer_stays_correct(self):
        r = self.request()
        self.fill(r)
        self.capacity(0)
        self.now += 1800
        result = self.claim(r)
        self.assertEqual((result['creditedLives'], result['lives'], result['remaining'], result['nextLifeAt']), (4, 5, 1, 0))
        # The remaining entitlement is retained. A small claim below the cap
        # must preserve an existing future timer rather than resetting it.
        self.capacity(0)
        due = self.get('/v1/wallet')['nextLifeAt']
        self.now += 60
        result = self.claim(r)
        self.assertEqual((result['creditedLives'], result['lives'], result['nextLifeAt']), (1, 1, due))

    def test_11_wallet_quarantine_migration_and_revision_errors_preserve_entitlement(self):
        r = self.request()
        self.fill(r)
        self.capacity(0)
        with patch.object(self.app.state.wallet, '_quarantined', return_value=True):
            self.assertEqual(self.card(r)['collectBlockedReason'], 'WalletRefundReviewRequired')
            self.claim(r, status=409)
        original = self.app.state.wallet._guard
        def conflict(db, actor, revision, **kwargs):
            return original(db, actor, revision + 1, **kwargs)
        with patch.object(self.app.state.wallet, '_guard', side_effect=conflict):
            self.claim(r, status=409)
        with self.authority.database.transaction() as db:
            db.execute('UPDATE wallets SET initialized=0 WHERE player_id=?', (self.users[0]['playerId'],))
        self.assertEqual(self.card(r)['collectBlockedReason'], 'WalletMigrationRequired')
        self.claim(r, status=409)
        with self.authority.database.transaction() as db:
            db.execute('UPDATE wallets SET initialized=1 WHERE player_id=?', (self.users[0]['playerId'],))
        self.assertEqual((self.card(r)['remaining'], self.get('/v1/wallet')['lives']), (5, 0))

    def test_12_leave_rejoin_at_frozen_time_closes_request_and_owner_can_claim_outside_team(self):
        r = self.request()
        self.help(r)
        self.post('/v1/teams/' + self.team + '/members/transfer', playerId=self.users[1]['playerId'])
        self.post('/v1/teams/' + self.team + '/leave')
        self.get(self.base, status=403)
        owned = self.get('/v1/life-requests/owned')['requests'][0]
        self.assertEqual((owned['state'], owned['closeReason'], owned['remaining']), ('Claimable', 'MembershipEnded', 1))
        self.capacity(4)
        self.assertEqual(self.claim(r)['creditedLives'], 1)
        self.post('/v1/teams/' + self.team + '/join')
        self.help(r, 2, status=409)
        self.post(self.base, status=409)

    def test_13_removal_closes_request_and_donor_leave_rejoin_never_grants_twice(self):
        r = self.request(1)
        self.help(r, 2)
        self.post('/v1/teams/' + self.team + '/leave', 2)
        self.post('/v1/teams/' + self.team + '/join', 2)
        self.help(r, 2)
        self.post('/v1/teams/' + self.team + '/members/kick', playerId=self.users[1]['playerId'])
        self.help(r, 3, status=409)
        self.assertEqual(self.get('/v1/life-requests/owned', 1)['requests'][0]['remaining'], 1)
        self.assertEqual(self.count('team_life_donations'), 1)

    def test_14_blocks_and_moderation_hide_cards_and_stop_new_help_but_preserve_earned_units(self):
        r = self.request()
        self.help(r)
        self.post('/v1/blocks/add', 2, playerId=self.users[0]['playerId'])
        self.assertEqual(self.get(self.base, 2)['requests'], [])
        self.help(r, 2, status=409)
        with self.authority.database.transaction() as db:
            db.execute("UPDATE social_messages SET visibility='Hidden' WHERE id=?", (r['messageId'],))
        self.assertEqual(self.get(self.base, 3)['requests'], [])
        self.help(r, 3, status=409)
        self.assertEqual(self.get('/v1/life-requests/owned')['requests'][0]['closeReason'], 'Moderated')

    def test_15_claim_owner_and_auth_revocation_are_rechecked_before_cached_receipts(self):
        r = self.request()
        self.fill(r)
        self.claim(r, user=1, status=403)
        command = ident()
        self.claim(r, command=command)
        self.authority.revoke(self.users[0]['token'])
        self.claim(r, command=command, status=401)
        self.get('/v1/life-requests/owned', status=401)

    def test_16_lost_help_and_claim_commit_replies_recover_identical_receipts(self):
        r = self.request()
        command = ident()
        def fault(stage):
            if stage == 'AfterCommit':
                raise OSError('controlled-lost-commit-reply')
        self.authority.checkpoint = fault
        self.help(r, command=command, status=500)
        self.authority.checkpoint = None
        first = self.help(r, command=command)
        self.assertEqual(self.help(r, command=command), first)
        for user in range(2, 6):
            self.help(r, user)
        self.capacity(0)
        command = ident()
        self.authority.checkpoint = fault
        self.claim(r, command=command, status=500)
        self.authority.checkpoint = None
        first = self.claim(r, command=command)
        self.assertEqual((self.claim(r, command=command), self.get('/v1/wallet')['lives']), (first, 5))

    def test_17_beforecommit_failure_rolls_back_request_message_cooldown_donation_and_claim(self):
        def fault(stage):
            if stage == 'BeforeCommit':
                raise OSError('controlled-beforecommit')
        self.authority.checkpoint = fault
        self.post(self.base, status=500)
        self.authority.checkpoint = None
        self.assertEqual((self.count('team_life_requests'), self.count('social_messages')), (0, 0))
        r = self.request()
        self.authority.checkpoint = fault
        self.help(r, status=500)
        self.authority.checkpoint = None
        self.assertEqual((self.count('team_life_donations'), self.card(r)['received']), (0, 0))
        self.fill(r)
        self.capacity(0)
        self.authority.checkpoint = fault
        self.claim(r, status=500)
        self.authority.checkpoint = None
        self.assertEqual((self.card(r)['claimed'], self.get('/v1/wallet')['lives']), (0, 0))

    def test_18_social_operation_recovery_is_minimal_and_survives_membership_loss(self):
        r = self.request(1)
        command = ident()
        first = self.help(r, 2, command=command)
        self.post('/v1/teams/' + self.team + '/leave', 2)
        op = 'social.life.help/' + self.team + '/' + r['requestId']
        record = self.get('/v1/social/operations/' + command, 2, params={'operation': op})
        self.assertEqual(record['response'], first)
        self.assertNotIn('members', json.dumps(record))
        self.assertEqual(self.help(r, 2, command=command), first)
        self.help(r, 2, status=403)

    def test_19_owner_multiple_entitlements_are_paginated_without_former_private_history(self):
        for _ in range(3):
            r = self.request()
            self.help(r)
            self.now += 14400
        first = self.get('/v1/life-requests/owned', params={'limit': 2})
        second = self.get('/v1/life-requests/owned', params={'limit': 2, 'after': first['nextCursor']})
        self.assertEqual((len(first['requests']), first['hasMore'], len(second['requests']), second['hasMore']), (2, True, 1, False))
        self.assertEqual(len({r['requestId'] for r in first['requests'] + second['requests']}), 3)
        self.assertNotIn('messages', first)
        self.assertNotIn('members', json.dumps(first))

    def test_20_tail_older_and_message_id_hydration_preserve_exact_feed_sequences(self):
        ids = []
        for _ in range(3):
            ids.append(self.request())
            self.now += 14400
        tail = self.get(self.base, params={'limit': 2})
        older = self.get(self.base, params={'limit': 2, 'before': tail['olderCursor']})
        self.assertEqual([r['requestId'] for r in tail['requests']], [r['requestId'] for r in ids[1:]])
        self.assertEqual([r['requestId'] for r in older['requests']], [ids[0]['requestId']])
        hydrated = self.get(self.base, params={'messageIds': ids[0]['messageId']})
        self.assertEqual([r['messageId'] for r in hydrated['requests']], [ids[0]['messageId']])
        self.get(self.base, status=422, params={'messageIds': ids[0]['messageId'] + ',' + ids[0]['messageId']})

    def test_21_expiry_and_cooldown_use_server_time_not_device_fields_or_clock_rollback(self):
        r = self.request()
        self.now += 14400
        self.assertEqual(self.card(r)['state'], 'Expired')
        newer = self.request()
        self.assertNotEqual(newer['requestId'], r['requestId'])
        self.now -= 1
        self.assertEqual(self.request(), newer)
        self.assertEqual(self.get(self.base)['serverUtc'], newer['serverUtc'])

    def test_22_snapshot_restore_preserves_pending_entitlements_and_claim_receipts(self):
        r = self.request()
        self.fill(r)
        self.capacity(3)
        command = ident()
        first = self.claim(r, command=command)
        snapshot, restored = self.root / 'snapshot.sqlite3', self.root / 'restored.sqlite3'
        self.assertEqual(backup_database(self.path, snapshot)['schemaVersion'], SCHEMA_VERSION)
        restore_database(snapshot, restored)
        self.open(restored)
        self.assertEqual(self.claim(r, command=command), first)
        self.assertEqual(self.get('/v1/life-requests/owned')['requests'][0]['remaining'], 3)

    def test_23_schema11_migration_preserves_old_tables_and_rolls_back_partial_schema12(self):
        old = self.root / 'old11.sqlite3'
        with self.authority.database.connect() as source, closing(sqlite3.connect(old)) as target:
            copy_legacy(source, target, 11)
        with patch('hotr_backend.team_life_schema110.TEAM_LIFE_V12_DDL', TEAM_LIFE_V12_DDL + '\nINVALID MIGRATION;'):
            with self.assertRaises(sqlite3.OperationalError):
                Database(old)
        with closing(sqlite3.connect(old)) as db:
            self.assertEqual(_validate(db), 11)
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='team_life_requests'").fetchone())
        Database(old)
        with closing(sqlite3.connect(old)) as db:
            self.assertEqual(_validate(db), SCHEMA_VERSION)
            self.assertEqual(db.execute('SELECT badge_id FROM social_teams').fetchone()[0], 'oak')

    def test_24_default_social_disabled_does_not_enable_help_or_modify_old_wallets(self):
        self.open(enabled=False)
        before = self.finance()
        self.get(self.base, status=503)
        self.post(self.base, status=503)
        self.get('/v1/life-requests/owned', status=503)
        self.assertEqual(self.finance(), before)

    def managed_guest(self):
        key, refresh = ECC.generate(curve='P-256'), secrets.token_urlsafe(32)
        body = messaging_fixtures.MessagingTests.signed_identity(self, key, {'refreshToken': refresh, 'recoverySecret': secrets.token_urlsafe(32)}, 'guest')
        response = self.client.post('/v1/identity/guest', json=body)
        self.assertEqual(response.status_code, 200)
        value = response.json()
        self.users.append({'token': value['accessToken'], 'playerId': value['playerId']})
        return len(self.users) - 1, key, refresh

    def delete_guest(self, user, key, refresh):
        body = messaging_fixtures.MessagingTests.signed_identity(self, key, {'playerId': self.users[user]['playerId'], 'refreshToken': refresh}, 'delete')
        response = self.client.post('/v1/account/deletion', json=body)
        self.assertEqual(response.status_code, 200)

    def test_25_actual_signed_recipient_deletion_stops_visibility_help_and_claim(self):
        user, key, refresh = self.managed_guest()
        self.post('/v1/teams/' + self.team + '/join', user)
        r = self.request(user)
        self.help(r, 1)
        self.delete_guest(user, key, refresh)
        self.assertNotIn(r['requestId'], [row['requestId'] for row in self.get(self.base, 2)['requests']])
        self.help(r, 2, status=409)
        self.claim(r, user=user, status=401)
        self.get('/v1/life-requests/owned', user, status=401)

    def test_26_team_leader_deletion_closes_requests_but_preserves_other_owners_earned_units(self):
        leader, key, refresh = self.managed_guest()
        new_team = self.post('/v1/teams', leader, name='Second Team')['teamId']
        self.post('/v1/teams/' + self.team + '/members/transfer', playerId=self.users[1]['playerId'])
        self.post('/v1/teams/' + self.team + '/leave')
        self.post('/v1/teams/' + self.team + '/leave', 2)
        self.team, self.base = new_team, '/v1/teams/' + new_team + '/life-requests'
        self.post('/v1/teams/' + self.team + '/join')
        self.post('/v1/teams/' + self.team + '/join', 2)
        r = self.request()
        self.help(r, 2)
        self.delete_guest(leader, key, refresh)
        self.get(self.base, status=404)
        card = self.get('/v1/life-requests/owned')['requests'][0]
        self.assertEqual((card['closeReason'], card['remaining']), ('TeamClosed', 1))
        self.capacity(4)
        self.assertEqual(self.claim(r)['creditedLives'], 1)


if __name__ == '__main__':
    unittest.main()
