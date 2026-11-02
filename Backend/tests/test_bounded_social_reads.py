"""Actual HTTP/SQLite bounded chat windows and exact relationship reads.

Tombstone/visibility fixtures below are explicit operator test state; the
existing deletion/moderation suites cover their authenticated write flows.
"""
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.service import ServiceError

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class BoundedSocialReadsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-bounded-social-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 100 * 86400
        self.app = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True)
        self.authority = self.app.state.authority
        self.identities = [self.authority.provision(lifetime=2592000) for _ in range(4)]
        self.players = [value['playerId'] for value in self.identities]
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.finance_before = self.finance()

    def tearDown(self):
        try:
            self.assertEqual(self.finance(), self.finance_before, 'Bounded social reads/writes changed financial or progression state')
        finally:
            self.client.close()
            self.temp.cleanup()

    def finance(self):
        with self.authority.database.connect() as db:
            values = {}
            for table, owner in (('players', 'id'), ('wallets', 'player_id'), ('wallet_ledger', 'player_id'),
                                 ('rewards', 'player_id'), ('gameplay_attempts', 'player_id'), ('commerce_orders', 'player_id')):
                values[table] = [tuple(r) for r in db.execute('SELECT * FROM ' + table + ' WHERE ' + owner + ' IN (?,?,?,?) ORDER BY 1', self.players)]
            return values

    def headers(self, actor=0):
        return {'Authorization': 'Bearer ' + self.identities[actor]['token']}

    def get(self, path, actor=0, status=200, **query):
        response = self.client.get(path, headers=self.headers(actor), params=query)
        self.assertEqual(response.status_code, status, response.text)
        return response

    def post(self, path, actor=0, status=200, **body):
        response = self.client.post(path, headers=self.headers(actor), json={'commandId': ident(), **body})
        self.assertEqual(response.status_code, status, response.text)
        return response.json()

    def friends(self, first=0, second=1):
        request = self.post('/v1/friends/request', first, playerId=self.players[second])
        self.post('/v1/friends/respond', second, requestId=request['requestId'], action='accept')

    def direct(self, count, *, first=0, second=1, text=None):
        result = []
        for index in range(count):
            if index and index % 10 == 0:
                self.now += 61  # Respect the actual ten messages/minute policy.
            result.append(self.post('/v1/messages/Direct/' + self.players[second], first, text=text if text is not None else 'Сообщение ' + str(index)))
        return result

    def team(self):
        team = self.post('/v1/teams', name='Хранители', description='Вместе')['teamId']
        for actor in (1, 2):
            self.post('/v1/teams/' + team + '/join', actor)
        return team

    def test_01_latest_older_forward_pages_are_ordered_exclusive_and_legacy_compatible(self):
        self.friends()
        sent = self.direct(19)
        path = '/v1/messages/Direct/' + self.players[0]
        legacy = self.get(path, 1).json()
        self.assertEqual(set(legacy), {'messages', 'nextCursor', 'hasMore', 'unreadCount'})
        self.assertEqual([row['sequence'] for row in legacy['messages']], [row['sequence'] for row in sent])
        tail = self.get(path, 1, tail='true').json()
        self.assertEqual([row['sequence'] for row in tail['messages']], [r['sequence'] for r in sent[-8:]])
        self.assertTrue(tail['hasOlder']); self.assertFalse(tail['hasNewer']); self.assertFalse(tail['hasMore'])
        self.assertEqual((tail['nextCursor'], tail['olderCursor']), (sent[-1]['sequence'], sent[-8]['sequence']))
        older = self.get(path, 1, before=tail['olderCursor'], limit=8).json()
        self.assertEqual([r['sequence'] for r in older['messages']], [r['sequence'] for r in sent[3:11]])
        self.assertTrue(older['hasOlder'] and older['hasNewer'] and older['hasMore'])
        first = self.get(path, 1, before=older['olderCursor'], limit=8).json()
        self.assertEqual([r['sequence'] for r in first['messages']], [r['sequence'] for r in sent[:3]])
        self.assertFalse(first['hasOlder']); self.assertTrue(first['hasNewer'])
        forward = self.get(path, 1, after=older['nextCursor'], limit=8).json()
        self.assertEqual(forward['messages'], tail['messages'])
        self.assertFalse(forward['hasMore'])

    def test_02_worst_case_legal_astral_unicode_wire_fits_native_64k_limit(self):
        self.friends()
        self.post('/v1/profile/name', displayName='😀' * 20)
        sent = self.direct(19, text='😀' * 1000)
        path = '/v1/messages/Direct/' + self.players[0]
        legacy = self.get(path, 1, after=0, limit=100)
        self.assertGreater(len(legacy.content), 65536, 'Control must reproduce oversized valid legacy response')
        latest = self.get(path, 1, tail='true', limit=8)
        self.assertLess(len(latest.content), 65536)
        self.assertEqual(len(latest.json()['messages']), 8)
        self.assertTrue(all(row['text'] == '😀' * 1000 for row in latest.json()['messages']))
        older = self.get(path, 1, before=latest.json()['olderCursor'], limit=8)
        self.assertLess(len(older.content), 65536)
        self.assertEqual(len(older.json()['messages']), 8)
        self.assertEqual(latest.json()['nextCursor'], sent[-1]['sequence'])

    def test_03_json_escape_heavy_legal_text_and_maximum_name_remain_bounded(self):
        self.friends()
        self.post('/v1/profile/name', displayName='A' + '\u0301' * 255)
        self.direct(12, text='"\\\n\U0001f600' * 250)
        result = self.get('/v1/messages/Direct/' + self.players[0], 1, tail='true')
        self.assertLess(len(result.content), 65536)
        self.assertEqual([r['text'] for r in result.json()['messages']], ['"\\\n\U0001f600' * 250] * 8)

    def test_04_empty_boundaries_and_new_arrivals_do_not_duplicate_old_page(self):
        self.friends()
        path = '/v1/messages/Direct/' + self.players[0]
        empty = self.get(path, 1, tail='true').json()
        self.assertEqual((empty['messages'], empty['nextCursor'], empty['olderCursor'], empty['hasOlder'], empty['hasNewer']), ([], 0, 0, False, False))
        sent = self.direct(9)
        prior = self.get(path, 1, tail='true').json()
        team = self.team()
        other = self.post('/v1/messages/Team/' + team, 2, text='Other channel')
        self.direct(1, text='New arrival')
        older = self.get(path, 1, before=prior['olderCursor']).json()
        self.assertEqual([r['sequence'] for r in older['messages']], [sent[0]['sequence']])
        self.assertFalse(older['hasOlder'])
        below = self.get(path, 1, before=sent[0]['sequence']).json()
        self.assertEqual((below['messages'], below['olderCursor'], below['hasOlder']), ([], 0, False))
        after = self.get(path, 1, after=prior['nextCursor'], limit=8).json()
        self.assertEqual([r['text'] for r in after['messages']], ['New arrival'])
        self.assertGreater(after['messages'][0]['sequence'], other['sequence'])
        reopened = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True)
        with TestClient(reopened) as client:
            resumed = client.get(path, headers=self.headers(1), params={'before': prior['olderCursor'], 'limit': 8})
        self.assertEqual(resumed.status_code, 200, resumed.text)
        self.assertEqual(resumed.json(), older)

    def test_05_team_window_filters_hidden_blocked_and_deleted_authors_before_limit(self):
        team = self.team();sent = []
        for index in range(18):
            sent.append(self.post('/v1/messages/Team/' + team, index % 3, text='Строка ' + str(index)))
        self.post('/v1/blocks/add', playerId=self.players[1])
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.players[2], self.now))
            db.execute("UPDATE social_messages SET visibility='Hidden' WHERE id=?", (sent[0]['messageId'],))
        result = self.get('/v1/messages/Team/' + team, tail='true').json()
        expected = [row['sequence'] for index, row in enumerate(sent) if index % 3 == 0 and index != 0]
        self.assertEqual([row['sequence'] for row in result['messages']], expected)
        self.assertFalse(result['hasOlder'])
        self.assertTrue(all(row['authorId'] == self.players[0] for row in result['messages']))

    def test_06_direct_permission_block_both_directions_and_revoked_actor(self):
        path = '/v1/messages/Direct/' + self.players[1]
        self.get(path, status=404, tail='true')
        self.friends();self.direct(1)
        self.post('/v1/blocks/add', 1, playerId=self.players[0])
        self.get(path, status=404, tail='true')
        self.get('/v1/messages/Direct/' + self.players[0], 1, status=404, before=999)
        self.authority.revoke(self.identities[0]['token'])
        self.get(path, status=401, tail='true')

    def test_07_team_membership_deletion_and_no_implicit_read_mark(self):
        team = self.team()
        sent = [self.post('/v1/messages/Team/' + team, 1, text='Привет ' + str(i)) for i in range(10)]
        path = '/v1/messages/Team/' + team
        self.get(path, 3, status=403, tail='true')
        view = self.get(path, tail='true').json()
        self.assertEqual(view['unreadCount'], 10)
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM social_message_reads').fetchone()[0], 0)
        self.post(path + '/read', through=sent[-1]['sequence'])
        self.assertEqual(self.get(path, tail='true').json()['unreadCount'], 0)
        self.post('/v1/teams/' + team + '/leave', 1)
        self.get(path, 1, status=403, tail='true')
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.players[2], self.now))
        self.get(path, 2, status=410, before=999)

    def test_08_query_bounds_ambiguity_and_legacy_limits(self):
        self.friends();path = '/v1/messages/Direct/' + self.players[1]
        for query in ({'tail': 'true', 'limit': 9}, {'tail': 'true', 'limit': 0}, {'tail': 'true', 'after': 0},
                      {'before': 1, 'after': 0}, {'tail': 'true', 'before': 1}, {'before': 0}, {'before': -1},
                      {'before': 9223372036854775808}, {'tail': 'garbage'}):
            self.get(path, status=422, **query)
        self.get(path, after=0, limit=100)
        self.get(path, tail='true', limit=1)
        self.get(path, before=1, limit=1)

    def test_09_relationship_state_beyond_first_eight_friends_is_exact_and_bounded(self):
        for _ in range(9):
            value = self.authority.provision(lifetime=2592000)
            actor = self.authority.authenticate(value['token'])
            from hotr_backend.social_schemas import FriendResponse, FriendTarget
            own = self.authority.authenticate(self.identities[0]['token'])
            request = self.app.state.friends.send(own, FriendTarget(commandId=ident(), playerId=value['playerId']))
            self.app.state.friends.respond(actor, FriendResponse(commandId=ident(), requestId=request['requestId'], action='accept'))
        first = self.get('/v1/friends', limit=8).json()
        self.assertEqual(len(first['friends']), 8);self.assertTrue(first['hasMore'])
        later = self.get('/v1/friends', after=first['nextCursor'], limit=8).json()['friends'][0]
        relationship = self.get('/v1/friends/relationship/' + later['playerId']).json()
        self.assertEqual(relationship, {'playerId': later['playerId'], 'state': 'Friends'})

    def test_10_relationship_pending_directions_and_current_privacy(self):
        path = '/v1/friends/relationship/' + self.players[1]
        self.assertEqual(self.get(path).json(), {'playerId': self.players[1], 'state': 'None'})
        request = self.post('/v1/friends/request', playerId=self.players[1])
        self.assertEqual(self.get(path).json(), {'playerId': self.players[1], 'state': 'Outgoing', 'requestId': request['requestId']})
        incoming = self.get('/v1/friends/relationship/' + self.players[0], 1).json()
        self.assertEqual((incoming['state'], incoming['requestId']), ('Incoming', request['requestId']))
        self.post('/v1/friends/respond', 1, requestId=request['requestId'], action='decline')
        self.assertEqual(self.get(path).json()['state'], 'None')
        self.post('/v1/blocks/add', 1, playerId=self.players[0])
        self.get(path, status=404)
        self.get('/v1/friends/relationship/' + self.players[0], 1, status=404)

    def test_11_relationship_actor_target_guards_disabled_and_no_private_payload(self):
        path = '/v1/friends/relationship/' + self.players[1]
        result = self.get(path).json()
        self.assertNotIn('displayName', result);self.assertNotIn('token', json.dumps(result))
        self.get('/v1/friends/relationship/' + self.players[0], status=422)
        self.get('/v1/friends/relationship/' + ident(), status=404)
        self.get('/v1/friends/relationship/not-an-id', status=404)
        disabled = create_app(self.path, CONFIG, lambda: self.now, social_enabled=False)
        with TestClient(disabled) as client:
            for route, query in ((path, {}), ('/v1/messages/Direct/' + self.players[1], {'tail': 'true'})):
                response = client.get(route, headers=self.headers(), params=query)
                self.assertEqual(response.status_code, 503, response.text)
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.players[1], self.now))
        self.get(path, status=404)
        self.authority.revoke(self.identities[0]['token'])
        self.get(path, status=401)


if __name__ == '__main__':
    unittest.main()
