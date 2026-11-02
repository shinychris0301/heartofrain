"""Real ASGI/SQLite country scopes and privacy-safe team aggregates.

Synthetic privileged first-clears test the authority boundary; these are not
game replay, production rankings, geolocation or device/rendering evidence.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.regions import Regions, RegionUpdate
from hotr_backend.service import ServiceError

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class RegionRankings89Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-region89-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 100 * 86400
        self.open()
        self.players = [self.authority.provision(lifetime=2592000) for _ in range(6)]
        self.verifiers = [self.authority.provision(p['playerId'], 'verifier', 2592000) for p in self.players]

    def open(self, enabled=True):
        self.app = create_app(self.path, CONFIG, lambda: self.now, social_enabled=enabled)
        self.authority = self.app.state.authority
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def headers(self, player=0, verifier=False):
        return {'Authorization': 'Bearer ' + (self.verifiers if verifier else self.players)[player]['token']}

    def get(self, path, player=0):
        return self.client.get(path, headers=self.headers(player))

    def post(self, path, body, player=0):
        return self.client.post(path, json=body, headers=self.headers(player))

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def country(self, player, code, command=None):
        return self.ok(self.post('/v1/region', {'commandId': command or ident(), 'regionCode': code}, player))

    def profile(self, player, visible=True):
        return self.ok(self.post('/v1/profile', {'commandId': ident(), 'displayName': 'Fixture' + str(player), 'leaderboardOptIn': visible}, player))

    def progress(self, player, count):
        for level in range(1, count + 1):
            self.ok(self.client.post('/internal/v1/verified-first-clear', headers=self.headers(player, True), json={
                'attemptId': ident(), 'level': level, 'proofDigest': hashlib.sha256(('synthetic89-' + str(level)).encode()).hexdigest()}))

    def fixture(self):
        for player, (code, score) in enumerate(zip(('RU', 'RU', 'US', 'RU', 'US', 'RU'), (3, 2, 2, 0, 1, 1))):
            self.country(player, code)
            self.profile(player)
            self.progress(player, score)

    def team(self, owner, members=()):
        team = self.ok(self.post('/v1/teams', {'commandId': ident(), 'name': 'Team' + str(owner), 'description': 'isolated country fixture'}, owner))['teamId']
        for player in members:
            self.ok(self.post('/v1/teams/' + team + '/join', {'commandId': ident()}, player))
        return team

    def test_01_unset_region_is_explicit_and_never_inferred(self):
        region = self.ok(self.get('/v1/region?regionCode=RU&playerId=' + self.players[1]['playerId']))
        self.assertEqual(region, {'playerId': self.players[0]['playerId'], 'regionCode': '', 'regionSource': 'player_selected_country', 'locationVerified': False})
        for path in ('/v1/leaderboards/regional', '/v1/team-leaderboards/regional'):
            response = self.get(path + '?regionCode=US')
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()['error'], 'region_required')
        self.assertEqual(self.ok(self.get('/v1/leaderboards/global'))['entries'], [])
        self.assertEqual(self.ok(self.get('/v1/team-leaderboards/global'))['entries'], [])

    def test_02_region_command_is_owned_strict_idempotent_and_preserves_consent(self):
        command = ident()
        first = self.country(0, 'RU', command)
        self.assertEqual(self.country(0, 'RU', command), first)
        self.assertEqual(self.post('/v1/region', {'commandId': command, 'regionCode': 'US'}).status_code, 409)
        self.assertEqual(self.ok(self.get('/v1/region', 1))['regionCode'], '')
        self.assertFalse(self.ok(self.get('/v1/profile'))['leaderboardOptIn'])
        for extra in ({'playerId': self.players[1]['playerId']}, {'leaderboardOptIn': True}, {'completedLevels': 50}):
            self.assertEqual(self.post('/v1/region', {'commandId': ident(), 'regionCode': 'US', **extra}).status_code, 422)
        for code in ('XX', 'ru', 'R', 'RUS', 'РФ', '', None, 12):
            self.assertEqual(self.post('/v1/region', {'commandId': ident(), 'regionCode': code}).status_code, 422)
        profile = self.ok(self.get('/v1/players/' + self.players[0]['playerId'], 1))
        self.assertNotIn('regionCode', profile)

    def test_03_region_receipt_is_recoverable_owner_only_and_survives_restart(self):
        command = ident()
        expected = self.country(0, 'RU', command)
        receipt_path = '/v1/social/operations/' + command + '?operation=social.region.set'
        receipt = self.ok(self.get(receipt_path))
        self.assertEqual(receipt['status'], 'Committed')
        self.assertEqual(receipt['response'], expected)
        self.assertEqual(self.ok(self.get(receipt_path, 1))['status'], 'Absent')
        self.client.close()
        self.open()
        self.assertEqual(self.ok(self.get('/v1/region')), expected)
        self.assertEqual(self.ok(self.get(receipt_path)), receipt)

    def test_04_player_region_filters_actual_actor_country_and_uses_local_ranks(self):
        self.fixture()
        local = self.ok(self.get('/v1/leaderboards/regional?regionCode=US&playerId=' + self.players[2]['playerId'], 5))
        self.assertEqual(local['regionCode'], 'RU')
        self.assertEqual([r['score'] for r in local['entries']], [3, 2, 1, 0])
        self.assertEqual([r['rank'] for r in local['entries']], [1, 2, 3, 4])
        us = self.ok(self.get('/v1/leaderboards/regional', 2))
        self.assertEqual(us['regionCode'], 'US')
        self.assertEqual([r['score'] for r in us['entries']], [2, 1])
        self.country(0, 'US')
        self.assertNotIn(self.players[0]['playerId'], [r['playerId'] for r in self.ok(self.get('/v1/leaderboards/regional', 1))['entries']])
        self.assertEqual([r['score'] for r in self.ok(self.get('/v1/leaderboards/global'))['entries']], [3, 2, 2, 1, 1, 0])

    def test_05_player_region_optout_blocks_and_deleted_accounts_recompute_ranks(self):
        self.fixture()
        self.profile(0, False)
        self.ok(self.post('/v1/blocks/add', {'commandId': ident(), 'playerId': self.players[1]['playerId']}, 5))
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.players[3]['playerId'], self.now))
        rows = self.ok(self.get('/v1/leaderboards/regional', 5))['entries']
        self.assertEqual([(r['playerId'], r['rank']) for r in rows], [(self.players[5]['playerId'], 1)])
        self.assertEqual([r['rank'] for r in self.ok(self.get('/v1/leaderboards/regional', 1))['entries']], [1])

    def test_06_global_and_regional_team_aggregates_are_distinct(self):
        self.fixture()
        ru = self.team(0, (1, 2))
        us = self.team(4, (3, 5))
        global_rows = self.ok(self.get('/v1/team-leaderboards/global', 5))
        self.assertEqual([(r['teamId'], r['score'], r['memberCount']) for r in global_rows['entries']], [(ru, 7, 3), (us, 2, 3)])
        self.assertEqual(global_rows['teamRegionSource'], 'current_leader_selected_country')
        self.assertEqual([r['teamId'] for r in self.ok(self.get('/v1/team-leaderboards/regional', 5))['entries']], [ru])
        self.assertEqual([r['teamId'] for r in self.ok(self.get('/v1/team-leaderboards/regional', 2))['entries']], [us])
        # Membership country does not silently move a team away from its leader.
        self.country(1, 'US')
        self.assertEqual([r['teamId'] for r in self.ok(self.get('/v1/team-leaderboards/regional', 5))['entries']], [ru])

    def test_07_team_privacy_filters_contributions_owner_and_deleted_members(self):
        self.fixture()
        first = self.team(0, (1, 2))
        second = self.team(4, (3, 5))
        self.profile(1, False)
        self.ok(self.post('/v1/blocks/add', {'commandId': ident(), 'playerId': self.players[2]['playerId']}, 5))
        rows = self.ok(self.get('/v1/team-leaderboards/global', 5))['entries']
        self.assertEqual([(r['score'], r['memberCount']) for r in rows], [(3, 1), (2, 3)])
        self.ok(self.post('/v1/blocks/add', {'commandId': ident(), 'playerId': self.players[0]['playerId']}, 5))
        self.assertEqual([r['teamId'] for r in self.ok(self.get('/v1/team-leaderboards/global', 5))['entries']], [second])
        self.profile(4, False)
        self.assertEqual(self.ok(self.get('/v1/team-leaderboards/global', 5))['entries'], [])
        self.profile(4, True)
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.players[3]['playerId'], self.now))
        self.assertEqual(self.ok(self.get('/v1/team-leaderboards/global', 5))['entries'][0]['memberCount'], 2)

    def test_08_team_ties_share_ranks_across_pages_and_current_leader_sets_region(self):
        self.fixture()
        first = self.team(0, (3,))
        second = self.team(1, (5,))
        third = self.team(2, (4,))
        page = self.ok(self.get('/v1/team-leaderboards/global?limit=2', 5))
        self.assertTrue(page['hasMore'])
        last = self.ok(self.get('/v1/team-leaderboards/global?limit=2&offset=' + str(page['nextOffset']), 5))
        self.assertEqual([r['rank'] for r in page['entries'] + last['entries']], [1, 1, 1])
        self.assertEqual({r['teamId'] for r in page['entries'] + last['entries']}, {first, second, third})
        self.country(3, 'US')
        self.ok(self.post('/v1/teams/' + first + '/members/transfer', {'commandId': ident(), 'playerId': self.players[3]['playerId']}))
        self.assertNotIn(first, [r['teamId'] for r in self.ok(self.get('/v1/team-leaderboards/regional', 5))['entries']])
        self.assertIn(first, [r['teamId'] for r in self.ok(self.get('/v1/team-leaderboards/regional', 2))['entries']])

    def test_09_authentication_activation_revocation_and_transaction_guard(self):
        paths = ('/v1/region', '/v1/leaderboards/regional', '/v1/team-leaderboards/global')
        for path in paths:
            self.assertEqual(self.client.get(path).status_code, 401)
            self.assertEqual(self.client.get(path, headers=self.headers(0, True)).status_code, 403)
        actor = self.authority.authenticate(self.players[0]['token'])
        self.authority.revoke(self.players[0]['token'])
        for operation in (lambda: Regions(self.authority, True).mine(actor), lambda: Regions(self.authority, True).update(actor, RegionUpdate(commandId=ident(), regionCode='RU'))):
            with self.assertRaises(ServiceError) as error:
                operation()
            self.assertEqual(error.exception.status, 401)
        self.client.close()
        self.open(enabled=False)
        for path in paths:
            self.assertEqual(self.get(path, 1).status_code, 503)

    def test_10_reads_never_mutate_rewards_or_wallets_and_queries_are_bounded(self):
        self.fixture()
        self.team(0, (1,))
        def finances():
            with self.authority.database.connect() as db:
                return {table: [tuple(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY rowid')]
                        for table in ('wallets', 'wallet_ledger', 'rewards', 'commerce_credits')}
        before = finances()
        for path in ('/v1/leaderboards/regional', '/v1/team-leaderboards/global', '/v1/team-leaderboards/regional'):
            for query in ('offset=-1', 'offset=10001', 'limit=0', 'limit=101', 'offset=' + '9' * 100):
                self.assertEqual(self.get(path + '?' + query).status_code, 422)
            view = self.ok(self.get(path))
            self.assertFalse(view['rewardGranted'])
            self.assertNotIn('coins', json.dumps(view))
            self.assertNotIn('proofDigest', json.dumps(view))
        self.assertEqual(self.get('/v1/team-leaderboards/friends').status_code, 422)
        self.assertEqual(finances(), before)
