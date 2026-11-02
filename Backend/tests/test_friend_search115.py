"""Authenticated SQLite/ASGI name discovery; no live provider or UI claim."""
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.friends import Friends, SEARCH_SCAN_LIMIT
from hotr_backend.service import ServiceError
from hotr_backend.social_schemas import FriendResponse, FriendTarget, ProfileUpdate
from hotr_backend.storage import Database
from hotr_backend.operations import backup_database, restore_database

CONFIG = Path(__file__).resolve().parents[1] / 'config'


class FriendSearch115Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='friend-search115-')
        self.now = 100000
        self.path = Path(self.tmp.name) / 'db.sqlite'
        self.app = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True)
        self.authority = self.app.state.authority
        self.identities = [self.authority.provision(lifetime=2592000) for _ in range(6)]
        self.actors = [self.authority.authenticate(p['token']) for p in self.identities]
        self.friends = Friends(self.authority, enabled=True)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def profile(self, i, name, public=True):
        self.friends.update_profile(self.actors[i], ProfileUpdate(commandId=uuid.uuid4().hex,
                                    displayName=name, leaderboardOptIn=public))

    def search(self, q, **kwargs):
        return self.friends.search(self.actors[0], q, **kwargs)

    def test_unicode_visibility_blocks_and_no_mutations(self):
        self.profile(0, 'Хранитель Сам', True)
        self.profile(1, 'Хранитель Мира', True)
        self.profile(2, 'ХРАНИТЕЛЬ скрытый', False)
        self.profile(3, 'Хранитель блок', True)
        self.profile(4, 'Хранитель блокирует', True)
        self.profile(5, 'Café', True)
        self.friends.block(self.actors[0], FriendTarget(commandId=uuid.uuid4().hex, playerId=self.actors[3].player))
        self.friends.block(self.actors[4], FriendTarget(commandId=uuid.uuid4().hex, playerId=self.actors[0].player))
        result = self.search('  хранИТЕЛЬ  ')
        self.assertEqual([p['playerId'] for p in result['players']], [self.actors[1].player])
        self.assertEqual(set(result['players'][0]), {'playerId', 'displayName', 'completedLevels', 'leaderboardOptIn'})
        self.assertEqual(self.search('cafe\u0301')['players'][0]['playerId'], self.actors[5].player)
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM social_friend_requests').fetchone()[0], 0)
        self.profile(1, 'Хранитель Мира', False)
        self.assertEqual(self.search('хранитель')['players'], [])
        # Existing direct-ID profile access remains independent of ranking consent.
        self.assertEqual(self.friends.profile(self.actors[0], self.actors[1].player)['playerId'], self.actors[1].player)

    def test_pagination_sparse_scan_and_bounded_validation(self):
        with self.authority.database.transaction() as db:
            for n in range(1, SEARCH_SCAN_LIMIT + 3):
                pid = f'{n:032x}'
                db.execute('INSERT INTO players(id,completed,reward_totals,created_at) VALUES(?,0,?,0)', (pid, '{}'))
                db.execute('INSERT INTO social_profiles VALUES(?,?,1,0,0)', (pid, 'UniqueMatch' if n > SEARCH_SCAN_LIMIT else 'Other'))
        page = self.search('unique', limit=1)
        self.assertEqual(page['players'], [])
        self.assertTrue(page['hasMore'])
        self.assertNotIn(f'{SEARCH_SCAN_LIMIT:032x}', page['nextCursor'])
        with self.assertRaises(ServiceError):
            self.search('different', after=page['nextCursor'])
        with self.assertRaises(ServiceError):
            self.friends.search(self.actors[1], 'unique', after=page['nextCursor'])
        with self.assertRaises(ServiceError):
            self.search('unique', after=('A' if page['nextCursor'][0] != 'A' else 'B') + page['nextCursor'][1:])
        second = self.search('unique', after=page['nextCursor'], limit=1)
        self.assertEqual(len(second['players']), 1)
        self.assertTrue(second['hasMore'])
        third = self.search('unique', after=second['nextCursor'], limit=1)
        self.assertEqual(len(third['players']), 1)
        self.assertNotEqual(second['players'][0]['playerId'], third['players'][0]['playerId'])
        if third['hasMore']:
            self.assertEqual(self.search('unique', after=third['nextCursor'], limit=1)['players'], [])
        for q in ('', 'a', 'x' * 21, 'bad\nname'):
            with self.subTest(q=repr(q)), self.assertRaises(ServiceError):
                self.search(q)
        for kwargs in ({'after': 'invalid'}, {'limit': 0}, {'limit': 101}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ServiceError):
                self.search('query', **kwargs)
        self.now += 901
        self.actors[0] = self.authority.authenticate(self.identities[0]['token'])
        with self.assertRaises(ServiceError):
            self.search('unique', after=page['nextCursor'])

    def test_v14_migration_and_validated_backup(self):
        with self.authority.database.transaction() as db:
            db.execute('DROP TABLE friend_search_cursors')
            db.execute('UPDATE schema_info SET version=14')
        Database(self.path)
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 15)
            self.assertEqual(db.execute('SELECT count(*) FROM players').fetchone()[0], 6)
        backup = Path(self.tmp.name) / 'backup.sqlite'
        restored = Path(self.tmp.name) / 'restored.sqlite'
        self.assertEqual(backup_database(self.path, backup)['schemaVersion'], 15)
        self.assertEqual(restore_database(backup, restored)['schemaVersion'], 15)

    def test_http_auth_visibility_and_revocation(self):
        self.profile(1, 'Café Hero', True)
        self.assertEqual(self.client.get('/v1/friends/search', params={'q': 'café'}).status_code, 401)
        headers = {'Authorization': 'Bearer ' + self.identities[0]['token']}
        response = self.client.get('/v1/friends/search', params={'q': 'CAFÉ'}, headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['players'][0]['playerId'], self.actors[1].player)
        self.assertEqual(self.client.get('/v1/friends/search', params={'q': 'a'}, headers=headers).status_code, 422)
        with self.authority.database.transaction() as db:
            db.execute("UPDATE credentials SET revoked=1 WHERE player_id=?", (self.actors[0].player,))
        self.assertEqual(self.client.get('/v1/friends/search', params={'q': 'café'}, headers=headers).status_code, 401)

    def test_search_relationships_are_private_authoritative_and_retry_safe(self):
        # All four possible visible states and a blocked peer share the same
        # search term. Requests are created through real transactional APIs.
        for i in range(6):
            self.profile(i, 'Hero ' + str(i), True)
        target = lambda i, command=None: FriendTarget(commandId=command or uuid.uuid4().hex,
                                                       playerId=self.actors[i].player)
        outgoing_command = target(2)
        outgoing = self.friends.send(self.actors[0], outgoing_command)
        self.assertEqual(self.friends.send(self.actors[0], outgoing_command), outgoing)
        self.assertEqual(self.friends.send(self.actors[0], target(2))['requestId'], outgoing['requestId'])
        incoming = self.friends.send(self.actors[3], target(0))
        accepted = self.friends.send(self.actors[0], target(4))
        self.friends.respond(self.actors[4], FriendResponse(commandId=uuid.uuid4().hex,
                             requestId=accepted['requestId'], action='accept'))
        blocked = self.friends.send(self.actors[5], target(0))
        self.friends.block(self.actors[5], target(0))
        before = self.search('hero')
        relationships = {r['playerId']: r for r in before['relationships']}
        self.assertEqual([p['playerId'] for p in before['players']],
                         [r['playerId'] for r in before['relationships']])
        expected = {
            self.actors[1].player: {'playerId': self.actors[1].player, 'state': 'None'},
            self.actors[2].player: {'playerId': self.actors[2].player, 'state': 'Outgoing', 'requestId': outgoing['requestId']},
            self.actors[3].player: {'playerId': self.actors[3].player, 'state': 'Incoming', 'requestId': incoming['requestId']},
            self.actors[4].player: {'playerId': self.actors[4].player, 'state': 'Friends'},
        }
        self.assertEqual(relationships, expected)
        self.assertNotIn(blocked['requestId'], str(before))
        for i in range(1, 5):
            self.assertEqual(relationships[self.actors[i].player], self.friends.relationship(self.actors[0], self.actors[i].player))
        self.assertTrue(all(set(p) == {'playerId', 'displayName', 'completedLevels', 'leaderboardOptIn'}
                            for p in before['players']))
        headers = {'Authorization': 'Bearer ' + self.identities[0]['token']}
        http = self.client.get('/v1/friends/search', params={'q': 'hero'}, headers=headers)
        self.assertEqual(http.status_code, 200, http.text)
        self.assertEqual(http.json()['relationships'], before['relationships'])
        # Old cursors remain retryable, but each read observes current state.
        first = self.search('hero', limit=1)
        self.assertTrue(first['hasMore'])
        page = self.search('hero', after=first['nextCursor'], limit=2)
        self.assertEqual(self.search('hero', after=first['nextCursor'], limit=2)['relationships'], page['relationships'])
        self.friends.respond(self.actors[0], FriendResponse(commandId=uuid.uuid4().hex,
                             requestId=incoming['requestId'], action='decline'))
        after = {r['playerId']: r for r in self.search('hero')['relationships']}
        self.assertEqual(after[self.actors[3].player], {'playerId': self.actors[3].player, 'state': 'None'})
        self.friends.block(self.actors[0], target(2))
        self.assertNotIn(self.actors[2].player, [r['playerId'] for r in self.search('hero')['relationships']])
        with self.authority.database.connect() as db:
            row = db.execute("SELECT count(*) FROM social_friend_requests WHERE state='Pending' AND id=?",
                             (outgoing['requestId'],)).fetchone()
            self.assertEqual(row[0], 0)  # block cancels the one pending request


if __name__ == '__main__':
    unittest.main()
