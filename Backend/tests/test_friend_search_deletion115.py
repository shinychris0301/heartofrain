"""Real signed deletion must atomically remove only its owner's search cursors."""
import secrets
import tempfile
import unittest
import uuid
from pathlib import Path

from Crypto.PublicKey import ECC
from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.friends import Friends
from hotr_backend.social_schemas import ProfileUpdate
from tests import test_messaging as messaging_fixtures

CONFIG = Path(__file__).resolve().parents[1] / 'config'


class FriendSearchDeletion115Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='search-delete115-')
        self.now = 100000
        self.app = create_app(Path(self.tmp.name) / 'db.sqlite', CONFIG, lambda: self.now,
                              identity_enabled=True, social_enabled=True)
        self.authority = self.app.state.authority
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.tmp.cleanup()

    def signed(self, key, body, purpose):
        return messaging_fixtures.MessagingTests.signed_identity(self, key, body, purpose)

    def test_signed_deletion_and_failed_cleanup_restore_owner_cursor(self):
        key, refresh = ECC.generate(curve='P-256'), secrets.token_urlsafe(32)
        signup = self.signed(key, {'refreshToken': refresh, 'recoverySecret': secrets.token_urlsafe(32)}, 'guest')
        response = self.client.post('/v1/identity/guest', json=signup)
        self.assertEqual(response.status_code, 200, response.text)
        guest = response.json()
        guest_actor = self.authority.authenticate(guest['accessToken'])
        owner = self.authority.provision(lifetime=2592000)
        owner_actor = self.authority.authenticate(owner['token'])
        friends = Friends(self.authority, enabled=True)
        for actor in [guest_actor, owner_actor] + [self.authority.authenticate(
                self.authority.provision(lifetime=2592000)['token']) for _ in range(3)]:
            friends.update_profile(actor, ProfileUpdate(commandId=uuid.uuid4().hex,
                                   displayName='Searchable Player', leaderboardOptIn=True))
        guest_page = friends.search(guest_actor, 'searchable', limit=1)
        owner_page = friends.search(owner_actor, 'searchable', limit=1)
        self.assertTrue(guest_page['hasMore'])
        self.assertTrue(owner_page['hasMore'])

        # Abort a later delete after cursor cleanup has executed. The whole
        # account transaction, including cursor removal, must roll back.
        with self.authority.database.transaction() as db:
            db.execute("CREATE TRIGGER fail_search_delete BEFORE DELETE ON social_profiles "
                       "BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END")
        deletion = self.signed(key, {'playerId': guest['playerId'], 'refreshToken': refresh}, 'delete')
        self.assertEqual(self.client.post('/v1/account/deletion', json=deletion).status_code, 503)
        with self.authority.database.transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM friend_search_cursors WHERE player_id=?',
                                        (guest['playerId'],)).fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM friend_search_cursors WHERE player_id=?',
                                        (owner_actor.player,)).fetchone()[0], 1)
            db.execute('DROP TRIGGER fail_search_delete')
        self.assertTrue(friends.search(guest_actor, 'searchable', after=guest_page['nextCursor'], limit=1)['players'])

        deletion = self.signed(key, {'playerId': guest['playerId'], 'refreshToken': refresh}, 'delete')
        response = self.client.post('/v1/account/deletion', json=deletion)
        self.assertEqual(response.status_code, 200, response.text)
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM friend_search_cursors WHERE player_id=?',
                                        (guest['playerId'],)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM friend_search_cursors WHERE player_id=?',
                                        (owner_actor.player,)).fetchone()[0], 1)
        self.assertTrue(friends.search(owner_actor, 'searchable', after=owner_page['nextCursor'], limit=1)['players'])
        self.assertEqual(self.client.get('/v1/friends/search', params={'q': 'searchable'},
                         headers={'Authorization': 'Bearer ' + guest['accessToken']}).status_code, 401)


if __name__ == '__main__':
    unittest.main()
