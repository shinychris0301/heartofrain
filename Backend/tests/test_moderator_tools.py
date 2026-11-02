"""Real SQLite operator-scope tests; no staff deployment or cloud IAM claim."""
import tempfile
import unittest
from pathlib import Path

from hotr_backend.api import create_app
from hotr_backend.moderator_tools import set_moderator
from hotr_backend.service import ServiceError


class ModeratorToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(Path(self.temp.name) / 'authority.sqlite3', social_enabled=True)
        self.authority = self.app.state.authority
        self.credential = self.authority.provision()

    def tearDown(self):
        self.temp.cleanup()

    def test_grant_and_revoke_are_durable_and_do_not_export_credentials(self):
        token = self.credential['token']
        first = set_moderator(self.authority, token, True)
        self.assertNotIn(token, str(first))
        self.assertEqual(set_moderator(self.authority, token, True), first)
        actor = self.authority.authenticate(token)
        self.assertEqual(self.app.state.messaging.moderation_queue(actor)['reports'], [])
        reopened = create_app(self.authority.database.path, social_enabled=True)
        self.assertEqual(reopened.state.messaging.moderation_queue(actor)['reports'], [])
        set_moderator(self.authority, token, False)
        with self.assertRaises(ServiceError) as denied:
            reopened.state.messaging.moderation_queue(actor)
        self.assertEqual(denied.exception.status, 403)

    def test_financial_verifier_and_revoked_credentials_cannot_be_granted(self):
        verifier = self.authority.provision(role='verifier')
        with self.assertRaises(ServiceError):
            set_moderator(self.authority, verifier['token'], True)
        self.authority.revoke(self.credential['token'])
        with self.assertRaises(ServiceError):
            set_moderator(self.authority, self.credential['token'], True)
        # Operator cleanup can remove the grant of an expired/revoked token.
        self.assertEqual(set_moderator(self.authority, self.credential['token'], False)['status'], 'revoked')

    def test_stale_actor_and_deleted_account_cannot_use_granted_scope(self):
        token = self.credential['token']
        set_moderator(self.authority, token, True)
        actor = self.authority.authenticate(token)
        self.authority.revoke(token)
        with self.assertRaises(ServiceError) as denied:
            self.app.state.messaging.moderation_queue(actor)
        self.assertEqual(denied.exception.status, 401)
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',1)", (actor.player,))
        with self.assertRaises(ServiceError) as deleted:
            set_moderator(self.authority, token, True)
        self.assertIn(deleted.exception.status, (401, 410))
