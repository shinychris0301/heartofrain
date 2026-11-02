"""Actual SQLite/service human UGC-review boundaries, no automated decision claim."""
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from hotr_backend.api import create_app
from hotr_backend.messaging_schemas import CreateTeam
from hotr_backend.service import ServiceError
from hotr_backend.social_schemas import FriendTarget, ProfileUpdate
from hotr_backend.ugc_moderation import UgcModeration, SAFE_PROFILE_NAME, SAFE_TEAM_NAME
from hotr_backend.ugc_schemas import UgcModerate, UgcReport

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class UgcTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-ugc-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 200 * 86400
        self.app = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True)
        self.authority = self.app.state.authority
        self.ugc = UgcModeration(self.authority, enabled=True)
        self.identities = [self.authority.provision(lifetime=2_592_000) for _ in range(4)]
        self.actors = [self.authority.authenticate(i['token']) for i in self.identities]
        self.reporter, self.owner, self.staff = self.actors[:3]
        self.app.state.friends.update_profile(self.owner, ProfileUpdate(
            commandId=ident(), displayName='Review this name', leaderboardOptIn=True))

    def tearDown(self):
        self.temp.cleanup()

    def expect(self, status, action):
        with self.assertRaises(ServiceError) as error:
            action()
        self.assertEqual(error.exception.status, status)

    def grant(self, actor=None):
        actor = actor or self.staff
        with self.authority.database.transaction() as db:
            db.execute('INSERT INTO social_moderators VALUES(?,?)', (actor.credential_digest, self.now))

    def report_request(self, kind='Profile', target=None, **extra):
        return UgcReport(**{'commandId': ident(), 'kind': kind, 'targetId': target or self.owner.player,
                            'reason': 'Abuse', 'details': 'Please review this public text.', **extra})

    def moderate_request(self, kind='Profile', target=None, action='ResetProfileName'):
        return UgcModerate(commandId=ident(), kind=kind, targetId=target or self.owner.player,
                           action=action, reason='Human review of the submitted report')

    def count(self, table):
        with self.authority.database.connect() as db:
            return db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def test_01_default_disabled_and_staff_grant_never_client_controlled(self):
        request = self.report_request()
        self.expect(503, lambda: UgcModeration(self.authority).report(self.reporter, request))
        self.expect(403, lambda: self.ugc.queue(self.reporter))
        verifier = self.authority.provision(role='verifier')
        actor = self.authority.authenticate(verifier['token'], 'verifier')
        self.expect(403, lambda: self.ugc.queue(actor))
        with self.assertRaises(ValidationError):
            UgcReport(commandId=ident(), kind='Profile', targetId=self.owner.player,
                      reason='Abuse', moderator=True)
        self.assertEqual(self.count('social_moderators'), 0)

    def test_02_blocked_profile_report_returns_only_pending_metadata(self):
        self.app.state.friends.block(self.reporter, FriendTarget(commandId=ident(), playerId=self.owner.player))
        response = self.ugc.report(self.reporter, self.report_request())
        self.assertTrue(response['reviewPendingAtAcceptance'])
        self.assertFalse(response['automatedDecision'])
        self.assertNotIn('displayName', response)
        self.assertNotIn('name', response)
        self.assertNotIn('coins', response)
        self.grant()
        reports = self.ugc.queue(self.staff)['reports']
        self.assertEqual(reports[0]['name'], 'Review this name')
        self.assertNotIn('reporterId', reports[0])
        self.assertNotIn('token', reports[0])
        self.assertEqual(self.count('wallet_ledger'), 4)

    def test_03_profile_reset_preserves_optin_progression_and_wallet(self):
        self.ugc.report(self.reporter, self.report_request())
        self.grant()
        before = self.app.state.wallet.view(self.owner)
        request = self.moderate_request()
        first = self.ugc.moderate(self.staff, request)
        self.assertEqual(self.ugc.moderate(self.staff, request), first)
        profile = self.app.state.friends.me(self.owner)
        self.assertEqual(profile['displayName'], SAFE_PROFILE_NAME)
        self.assertTrue(profile['leaderboardOptIn'])
        self.assertEqual(self.app.state.wallet.view(self.owner), before)
        self.assertEqual(self.ugc.queue(self.staff)['reports'], [])
        self.assertEqual(self.count('social_ugc_actions'), 1)
        with self.authority.database.connect() as db:
            action = db.execute('SELECT * FROM social_ugc_actions').fetchone()
            self.assertEqual(action['moderator_id'], self.staff.player)
            self.assertEqual(action['reason'], request.reason)

    def test_04_team_reset_changes_text_only(self):
        team = self.app.state.messaging.create_team(self.owner, CreateTeam(
            commandId=ident(), name='Review team', description='Review description'))
        team_id = team['teamId']
        self.ugc.report(self.reporter, self.report_request('Team', team_id))
        self.grant()
        before = self.app.state.messaging.team(self.owner, team_id)
        self.ugc.moderate(self.staff, self.moderate_request('Team', team_id, 'ResetTeamText'))
        after = self.app.state.messaging.team(self.owner, team_id)
        self.assertEqual(after['name'], SAFE_TEAM_NAME)
        self.assertEqual(after['description'], '')
        self.assertEqual(after['ownerId'], before['ownerId'])
        self.assertEqual(after['members'], before['members'])
        self.assertEqual(after['memberCount'], before['memberCount'])
        self.assertEqual(self.count('wallet_ledger'), 4)

    def test_05_own_unknown_and_mismatched_actions_are_refused(self):
        self.expect(409, lambda: self.ugc.report(self.owner, self.report_request()))
        self.expect(404, lambda: self.ugc.report(self.reporter, self.report_request(target=ident())))
        self.grant()
        self.expect(422, lambda: self.ugc.moderate(self.staff, self.moderate_request(action='ResetTeamText')))
        self.assertEqual(self.count('social_ugc_actions'), 0)

    def test_06_duplicate_reports_and_changed_command_payload(self):
        request = self.report_request()
        first = self.ugc.report(self.reporter, request)
        self.assertEqual(self.ugc.report(self.reporter, request), first)
        self.assertEqual(self.ugc.report(self.reporter, self.report_request())['reportId'], first['reportId'])
        changed = request.model_copy(update={'details': 'different'})
        self.expect(409, lambda: self.ugc.report(self.reporter, changed))
        self.assertEqual(self.count('social_ugc_reports'), 1)

    def test_07_dismiss_does_not_reset_and_changed_content_can_reopen(self):
        first = self.ugc.report(self.reporter, self.report_request())
        self.grant()
        self.ugc.moderate(self.staff, self.moderate_request(action='DismissReports'))
        self.assertEqual(self.app.state.friends.me(self.owner)['displayName'], 'Review this name')
        unchanged = self.ugc.report(self.reporter, self.report_request())
        self.assertEqual(unchanged['reportId'], first['reportId'])
        self.assertFalse(unchanged['reviewPendingAtAcceptance'])
        self.assertEqual(self.ugc.queue(self.staff)['reports'], [])
        self.app.state.friends.update_profile(self.owner, ProfileUpdate(commandId=ident(), displayName='New public text'))
        changed = self.ugc.report(self.reporter, self.report_request())
        self.assertTrue(changed['reviewPendingAtAcceptance'])
        self.assertEqual(changed['reportId'], first['reportId'])
        self.assertEqual(len(self.ugc.queue(self.staff)['reports']), 1)

    def test_08_revoked_staff_or_removed_grant_cannot_recover_cached_actions(self):
        self.grant()
        request = self.moderate_request()
        self.ugc.moderate(self.staff, request)
        with self.authority.database.transaction() as db:
            db.execute('DELETE FROM social_moderators WHERE credential_digest=?', (self.staff.credential_digest,))
        self.expect(403, lambda: self.ugc.moderate(self.staff, request))
        self.grant()
        self.authority.revoke(self.identities[2]['token'])
        self.expect(401, lambda: self.ugc.moderate(self.staff, request))
        self.expect(401, lambda: self.ugc.queue(self.staff))
        self.assertEqual(self.count('social_ugc_actions'), 1)

    def test_09_deleted_target_and_deleted_reporter_remain_private(self):
        request = self.report_request()
        self.ugc.report(self.reporter, request)
        self.grant()
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.owner.player, self.now))
        self.assertEqual(self.ugc.queue(self.staff)['reports'], [])
        self.expect(404, lambda: self.ugc.moderate(self.staff, self.moderate_request()))
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.reporter.player, self.now))
        self.expect(410, lambda: self.ugc.report(self.reporter, request))

    def test_10_moderation_before_after_commit_faults_are_atomic_and_idempotent(self):
        self.ugc.report(self.reporter, self.report_request())
        self.grant()
        request = self.moderate_request()
        def before(stage):
            if stage == 'BeforeCommit':
                raise RuntimeError('controlled precommit failure')
        self.authority.checkpoint = before
        with self.assertRaises(RuntimeError):
            self.ugc.moderate(self.staff, request)
        self.assertEqual(self.count('social_ugc_actions'), 0)
        self.assertEqual(self.app.state.friends.me(self.owner)['displayName'], 'Review this name')
        def after(stage):
            if stage == 'AfterCommit':
                raise RuntimeError('controlled lost response')
        self.authority.checkpoint = after
        with self.assertRaises(RuntimeError):
            self.ugc.moderate(self.staff, request)
        self.authority.checkpoint = None
        self.app.state.friends.update_profile(self.owner, ProfileUpdate(commandId=ident(), displayName='Later name'))
        app = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True)
        retry = UgcModeration(app.state.authority, enabled=True).moderate(self.staff, request)
        self.assertEqual(retry['action'], 'ResetProfileName')
        self.assertEqual(self.app.state.friends.me(self.owner)['displayName'], 'Later name')
        self.assertEqual(self.count('social_ugc_actions'), 1)

    def test_11_bounded_unicode_review_text_and_unknown_properties(self):
        for value in ('a\u202eb', 'a\ud800b', 'a\u2028b', 'a' * 501):
            with self.assertRaises(ValidationError):
                self.report_request(details=value)
        for value in (' ', 'a\nb', 'a' * 161):
            with self.assertRaises(ValidationError):
                UgcModerate(commandId=ident(), kind='Profile', targetId=self.owner.player, action='ResetProfileName', reason=value)
        request = UgcReport(commandId=ident(), kind='Profile', targetId=self.owner.player,
                            reason='Other', details='  First line\nsecond line  ')
        self.assertEqual(request.details, 'First line\nsecond line')

    def test_12_queue_pagination_and_new_target_report_budget(self):
        self.ugc.report(self.reporter, self.report_request())
        with patch('hotr_backend.ugc_moderation.MAX_NEW_REPORTS_PER_DAY', 1):
            self.expect(429, lambda: self.ugc.report(self.reporter, self.report_request(target=self.actors[3].player)))
            self.ugc.report(self.reporter, self.report_request())
        self.ugc.report(self.reporter, self.report_request(target=self.actors[3].player))
        self.grant()
        first = self.ugc.queue(self.staff, limit=1)
        second = self.ugc.queue(self.staff, after=first['nextCursor'], limit=1)
        self.assertTrue(first['hasMore'])
        self.assertFalse(second['hasMore'])
        self.assertNotEqual(first['reports'][0]['reportId'], second['reports'][0]['reportId'])
        self.expect(422, lambda: self.ugc.queue(self.staff, after='bad'))

    def test_13_deleted_targets_are_filtered_before_bounded_visible_page(self):
        first = self.ugc.report(self.reporter, self.report_request())
        second = self.ugc.report(self.reporter, self.report_request(target=self.actors[3].player))
        self.grant()
        with self.authority.database.transaction() as db:
            # Force retained deleted-target rows to precede the visible row.
            db.execute('UPDATE social_ugc_reports SET id=? WHERE id=?', ('0' * 32, first['reportId']))
            db.execute('UPDATE social_ugc_reports SET id=? WHERE id=?', ('f' * 32, second['reportId']))
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.owner.player, self.now))
            indexes = {r['name'] for r in db.execute("PRAGMA index_list('social_ugc_reports')")}
        self.assertIn('social_ugc_open_cursor', indexes)
        page = self.ugc.queue(self.staff, limit=1)
        self.assertEqual(len(page['reports']), 1)
        self.assertEqual(page['reports'][0]['targetId'], self.actors[3].player)
        self.assertFalse(page['hasMore'])
        self.assertEqual(page['nextCursor'], 'f' * 32)


if __name__ == '__main__':
    unittest.main()
