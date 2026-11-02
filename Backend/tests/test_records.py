"""Actual ASGI/SQLite private records and opt-in standings coverage.

Privileged first-clear and settlement fixtures are SYNTHETIC upstream
attestations. They exercise the existing authority boundary, not game replay,
Unity integration, production competition or a real player score verifier.
"""
import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.service import ServiceError

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class RecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-records-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 100 * 86400
        self.open()
        self.players = [self.authority.provision(lifetime=2_592_000) for _ in range(4)]
        # Each verifier is explicitly bound to its synthetic upstream player.
        self.verifiers = [self.authority.provision(p['playerId'], 'verifier', 2_592_000) for p in self.players]

    def open(self, enabled=True):
        self.app = create_app(self.path, CONFIG, lambda: self.now, social_enabled=enabled)
        self.authority = self.app.state.authority
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def headers(self, player=0, verifier=False):
        source = self.verifiers if verifier else self.players
        return {'Authorization': 'Bearer ' + source[player]['token']}

    def get(self, path, player=0):
        return self.client.get(path, headers=self.headers(player))

    def post(self, path, body, player=0, verifier=False):
        return self.client.post(path, json=body, headers=self.headers(player, verifier))

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def profile(self, player, opt_in=True):
        return self.ok(self.post('/v1/profile', {'commandId': ident(), 'displayName': 'Fixture' + str(player), 'leaderboardOptIn': opt_in}, player))

    def clear(self, player, level, request=None):
        body = request or {'attemptId': ident(), 'level': level,
                           'proofDigest': hashlib.sha256(('synthetic-upstream-' + str(level)).encode()).hexdigest()}
        return self.post('/internal/v1/verified-first-clear', body, player, verifier=True)

    def to_level(self, player, level):
        current = self.ok(self.get('/v1/records', player))['completedLevels']
        for value in range(current + 1, level + 1):
            self.ok(self.clear(player, value))

    def ranking_fixture(self):
        for player, level in enumerate((3, 2, 2, 0)):
            self.to_level(player, level)
            self.profile(player)

    def friendship(self, first=0, second=1):
        request = self.ok(self.post('/v1/friends/request', {'commandId': ident(), 'playerId': self.players[second]['playerId']}, first))
        return self.ok(self.post('/v1/friends/respond', {'commandId': ident(), 'requestId': request['requestId'], 'action': 'accept'}, second))

    def team(self, owner=0, members=(1,)):
        team = self.ok(self.post('/v1/teams', {'commandId': ident(), 'name': 'Rain fixture', 'description': 'isolated test team'}, owner))
        for player in members:
            self.ok(self.post('/v1/teams/' + team['teamId'] + '/join', {'commandId': ident()}, player))
        return team['teamId']

    def tombstone(self, player):
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?) ON CONFLICT(player_id) DO UPDATE SET state='DeletionRequested',requested_at=excluded.requested_at", (self.players[player]['playerId'], self.now))

    def financial_state(self):
        with self.authority.database.connect() as db:
            return {table: [tuple(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY rowid')]
                    for table in ('wallets', 'wallet_ledger', 'rewards', 'commerce_credits')}

    def test_01_authentication_default_disabled_and_revoked_actor(self):
        for path in ('/v1/records', '/v1/leaderboards/global'):
            self.assertEqual(self.client.get(path).status_code, 401)
            self.assertEqual(self.client.get(path, headers=self.headers(0, True)).status_code, 403)
        self.client.close()
        self.open(enabled=False)
        self.assertEqual(self.get('/v1/records').status_code, 503)
        self.assertEqual(self.get('/v1/leaderboards/global').status_code, 503)
        self.client.close()
        self.open()
        self.authority.revoke(self.players[0]['token'])
        self.assertEqual(self.get('/v1/records').status_code, 401)
        self.assertEqual(self.get('/v1/leaderboards/global').status_code, 401)

    def test_02_client_scores_and_other_players_records_cannot_be_forged(self):
        self.to_level(1, 2)
        self.assertEqual(self.post('/v1/records', {'completedLevels': 50}).status_code, 405)
        self.assertEqual(self.post('/v1/leaderboards/global', {'score': 999}).status_code, 405)
        self.assertEqual(self.post('/v1/profile', {'commandId': ident(), 'displayName': 'Injected', 'leaderboardOptIn': True, 'completedLevels': 50, 'score': 999}).status_code, 422)
        forged = self.post('/internal/v1/verified-first-clear', {'attemptId': ident(), 'level': 1, 'proofDigest': 'a' * 64})
        self.assertEqual(forged.status_code, 403)
        mine = self.ok(self.get('/v1/records?playerId=' + self.players[1]['playerId'] + '&score=999'))
        self.assertEqual(mine['completedLevels'], 0)
        self.assertEqual(mine['firstClears'], [])
        self.assertEqual(mine['scoreSource'], 'server_verified_completed_levels')
        self.assertFalse(mine['clientScoresAccepted'])
        self.assertEqual(self.ok(self.get('/v1/leaderboards/global'))['entries'], [])

    def test_03_ordered_verified_first_clears_idempotency_and_cursor(self):
        self.assertEqual(self.clear(0, 3).status_code, 409)
        request = {'attemptId': ident(), 'level': 1, 'proofDigest': 'a' * 64}
        first = self.ok(self.clear(0, 1, request))
        self.assertEqual(self.ok(self.clear(0, 1, request)), first)
        self.assertEqual(self.clear(0, 1, dict(request, proofDigest='b' * 64)).status_code, 409)
        self.to_level(0, 3)
        page = self.ok(self.get('/v1/records?limit=2'))
        self.assertEqual(page['completedLevels'], 3)
        self.assertEqual([r['level'] for r in page['firstClears']], [1, 2])
        self.assertTrue(page['hasMore'])
        second = self.ok(self.get('/v1/records?after=' + str(page['nextCursor']) + '&limit=2'))
        self.assertEqual([r['level'] for r in second['firstClears']], [3])
        self.assertFalse(second['hasMore'])
        self.assertTrue(all(r['verifiedAt'] == self.now for r in page['firstClears'] + second['firstClears']))
        self.assertEqual(self.ok(self.get('/v1/records?after=3'))['firstClears'], [])

    def test_04_attempt_counts_are_owned_server_state_and_replay_is_not_first_clear(self):
        def wallet():
            return self.ok(self.get('/v1/wallet'))

        def command(path, extra=None, verifier=False):
            body = {'commandId': ident(), 'expectedRevision': wallet()['revision'], **(extra or {})}
            return self.ok(self.post(path, body, verifier=verifier))

        reserved = command('/v1/attempts/reserve', {'level': 1, 'starting': [0] * 4})['attempt']
        command('/v1/attempts/' + reserved['attemptId'] + '/quit')
        for outcome in ('Lost', 'Fault', 'Won', 'Won'):
            attempt = command('/v1/attempts/reserve', {'level': 1, 'starting': [0] * 4})['attempt']
            command('/v1/attempts/' + attempt['attemptId'] + '/start')
            settled = command('/internal/v1/attempts/settle', {'playerId': self.players[0]['playerId'], 'attemptId': attempt['attemptId'], 'outcome': outcome, 'proofDigest': 'c' * 64}, verifier=True)
            self.assertIsNone(settled['wallet']['activeAttempt'])
        record = self.ok(self.get('/v1/records'))
        self.assertEqual(record['attempts'], {'Cancelled': 1, 'Lost': 1, 'Released': 1, 'Won': 2})
        self.assertEqual(record['completedLevels'], 1)
        self.assertEqual([r['level'] for r in record['firstClears']], [1])
        self.assertEqual(self.ok(self.get('/v1/records', 1))['attempts'], {})

    def test_05_opt_in_off_and_global_competition_ranks_pagination(self):
        self.ranking_fixture()
        expected = sorted([(self.players[i]['playerId'], score) for i, score in enumerate((3, 2, 2, 0))], key=lambda x: (-x[1], x[0]))
        rows, offset = [], 0
        while True:
            page = self.ok(self.get('/v1/leaderboards/global?limit=2&offset=' + str(offset), 3))
            self.assertTrue(page['tiesShareRank'])
            self.assertFalse(page['rewardGranted'])
            rows += page['entries']
            if not page['hasMore']:
                break
            self.assertGreater(page['nextOffset'], offset)
            offset = page['nextOffset']
        self.assertEqual([(r['playerId'], r['score']) for r in rows], expected)
        self.assertEqual([r['rank'] for r in rows], [1, 2, 2, 4])
        self.assertTrue(all(set(r) == {'playerId', 'displayName', 'score', 'rank'} for r in rows))
        self.profile(0, False)
        page = self.ok(self.get('/v1/leaderboards/global', 3))
        self.assertNotIn(self.players[0]['playerId'], [r['playerId'] for r in page['entries']])
        self.assertEqual([r['rank'] for r in page['entries']], [1, 1, 3])
        self.assertEqual(self.ok(self.get('/v1/records'))['completedLevels'], 3)

    def test_06_friends_scope_requires_acceptance_and_honors_opt_in(self):
        self.ranking_fixture()
        self.assertEqual([r['playerId'] for r in self.ok(self.get('/v1/leaderboards/friends'))['entries']], [self.players[0]['playerId']])
        request = self.ok(self.post('/v1/friends/request', {'commandId': ident(), 'playerId': self.players[1]['playerId']}))
        self.assertEqual(len(self.ok(self.get('/v1/leaderboards/friends'))['entries']), 1)
        self.ok(self.post('/v1/friends/respond', {'commandId': ident(), 'requestId': request['requestId'], 'action': 'accept'}, 1))
        self.assertEqual([r['playerId'] for r in self.ok(self.get('/v1/leaderboards/friends'))['entries']], [self.players[0]['playerId'], self.players[1]['playerId']])
        self.profile(1, False)
        self.assertEqual(len(self.ok(self.get('/v1/leaderboards/friends'))['entries']), 1)

    def test_07_team_scope_is_member_bound_and_uses_shared_ranks(self):
        self.ranking_fixture()
        self.assertEqual(self.get('/v1/leaderboards/team', 3).status_code, 409)
        team = self.team(1, (2, 3))
        page = self.ok(self.get('/v1/leaderboards/team', 3))
        self.assertEqual({r['playerId'] for r in page['entries']}, {p['playerId'] for p in self.players[1:]})
        self.assertEqual([r['rank'] for r in page['entries']], [1, 1, 3])
        self.profile(2, False)
        self.assertEqual([r['rank'] for r in self.ok(self.get('/v1/leaderboards/team', 3))['entries']], [1, 2])
        self.ok(self.post('/v1/teams/' + team + '/leave', {'commandId': ident()}, 3))
        self.assertEqual(self.get('/v1/leaderboards/team', 3).status_code, 409)

    def test_08_block_filters_both_global_directions_and_scope_rank(self):
        self.ranking_fixture()
        self.friendship(3, 0)
        self.ok(self.post('/v1/blocks/add', {'commandId': ident(), 'playerId': self.players[0]['playerId']}, 3))
        visible = self.ok(self.get('/v1/leaderboards/global', 3))['entries']
        self.assertNotIn(self.players[0]['playerId'], [r['playerId'] for r in visible])
        self.assertEqual([r['rank'] for r in visible], [1, 1, 3])
        reverse = self.ok(self.get('/v1/leaderboards/global', 0))['entries']
        self.assertNotIn(self.players[3]['playerId'], [r['playerId'] for r in reverse])
        self.assertEqual(self.ok(self.get('/v1/leaderboards/friends', 3))['entries'][0]['playerId'], self.players[3]['playerId'])

    def test_09_deleted_players_and_hidden_owner_team_are_filtered(self):
        self.ranking_fixture()
        self.friendship(3, 0)
        self.team(0, (3,))
        self.tombstone(0)
        self.assertNotIn(self.players[0]['playerId'], [r['playerId'] for r in self.ok(self.get('/v1/leaderboards/global', 3))['entries']])
        self.assertEqual([r['playerId'] for r in self.ok(self.get('/v1/leaderboards/friends', 3))['entries']], [self.players[3]['playerId']])
        self.assertEqual(self.get('/v1/leaderboards/team', 3).status_code, 404)
        self.assertEqual(self.get('/v1/records', 0).status_code, 410)

    def test_10_records_standings_opt_in_and_relations_survive_restart(self):
        self.ranking_fixture()
        self.friendship(3, 0)
        self.team(1, (2,))
        before = {path: self.ok(self.get(path, player)) for path, player in
                  (('/v1/records', 0), ('/v1/leaderboards/global', 3), ('/v1/leaderboards/friends', 3), ('/v1/leaderboards/team', 2))}
        self.client.close()
        self.open()
        for path, player in (('/v1/records', 0), ('/v1/leaderboards/global', 3), ('/v1/leaderboards/friends', 3), ('/v1/leaderboards/team', 2)):
            self.assertEqual(self.ok(self.get(path, player)), before[path])

    def test_11_query_bounds_including_signed64_no_sql_overflow(self):
        for query in ('after=-1', 'after=9223372036854775808', 'after=' + '9' * 100, 'limit=0', 'limit=101'):
            self.assertEqual(self.get('/v1/records?' + query).status_code, 422)
        page = self.ok(self.get('/v1/records?after=9223372036854775807&limit=100'))
        self.assertEqual(page['firstClears'], [])
        self.assertEqual(page['nextCursor'], 9223372036854775807)
        for query in ('offset=-1', 'offset=10001', 'offset=' + '9' * 100, 'limit=0', 'limit=101'):
            self.assertEqual(self.get('/v1/leaderboards/global?' + query).status_code, 422)
        self.assertEqual(self.get('/v1/leaderboards/not-a-scope').status_code, 422)
        actor = self.authority.authenticate(self.players[0]['token'])
        for action in (lambda: self.app.state.records.mine(actor, True), lambda: self.app.state.records.leaderboard(actor, offset=True)):
            with self.assertRaises(ServiceError) as error:
                action()
            self.assertEqual(error.exception.status, 422)

    def test_12_reading_standings_never_grants_rewards_or_changes_wallets(self):
        self.ranking_fixture()
        self.friendship(0, 1)
        self.team(0, (1,))
        before = self.financial_state()
        for _ in range(2):
            for player in range(2):
                for path in ('/v1/records', '/v1/leaderboards/global', '/v1/leaderboards/friends', '/v1/leaderboards/team'):
                    result = self.ok(self.get(path, player))
                    if 'rewardGranted' in result:
                        self.assertFalse(result['rewardGranted'])
                    encoded = json.dumps(result)
                    self.assertNotIn('accessToken', encoded)
                    self.assertNotIn('recoverySecret', encoded)
                    self.assertNotIn('proofDigest', encoded)
                    self.assertNotIn('coins', result)
        self.assertEqual(self.financial_state(), before)
