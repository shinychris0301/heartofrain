"""Guarded team leave: incarnation binding, recoverability and existing rules.

The fixtures use disposable SQLite and local ASGI only; no external account or
device is affected. The inherited fixture checks all financial tables unchanged.
"""
import concurrent.futures
import hashlib
import json
import unittest

from tests import test_messaging as fixtures

ident = fixtures.ident


class TeamLeaveVersion113(unittest.TestCase):
    setUp = fixtures.MessagingTests.setUp
    open = fixtures.MessagingTests.open
    restart = fixtures.MessagingTests.restart
    tearDown = fixtures.MessagingTests.tearDown
    finance = fixtures.MessagingTests.finance
    headers = fixtures.MessagingTests.headers
    request = fixtures.MessagingTests.request
    post = fixtures.MessagingTests.post
    get = fixtures.MessagingTests.get
    team = fixtures.MessagingTests.team
    join = fixtures.MessagingTests.join

    def detail(self, team, actor=1):
        return self.get('/v1/teams/' + team, actor)

    def test_01_private_snapshot_and_authoritative_owner_consequence(self):
        team = self.team()
        owner = self.detail(team, 0)
        self.assertRegex(owner['membershipVersion'], r'^[0-9a-f]{32}$')
        self.assertTrue(owner['leaveClosesTeam'])
        self.assertEqual(owner['leaveRestrictionReason'], '')
        public = self.detail(team, 2)
        for field in ('membershipVersion', 'leaveClosesTeam', 'leaveRestrictionReason'):
            self.assertNotIn(field, public)
        self.join(team, 1)
        owner = self.detail(team, 0)
        self.assertFalse(owner['leaveClosesTeam'])
        self.assertEqual(owner['leaveRestrictionReason'], 'transfer_ownership_first')
        member = self.detail(team)
        self.assertFalse(member['leaveClosesTeam'])
        self.assertEqual(member['leaveRestrictionReason'], '')
        self.assertNotEqual(owner['membershipVersion'], member['membershipVersion'])

    def test_02_same_second_rejoin_rejects_old_and_replays_committed_receipt(self):
        team = self.team(); self.join(team)
        old = self.detail(team)['membershipVersion']; command = ident()
        payload = {'commandId': command, 'expectedMembershipVersion': old}
        result = self.request('POST', '/v1/teams/' + team + '/leave', 1, payload)
        self.assertEqual(result, {'teamId': team, 'state': 'Left'})
        self.join(team)  # frozen identical server second
        new = self.detail(team)['membershipVersion']
        self.assertNotEqual(old, new)
        rejected = self.request('POST', '/v1/teams/' + team + '/leave', 1,
                                {'commandId': ident(), 'expectedMembershipVersion': old})
        self.assertEqual(rejected['reason'], 'team_membership_changed')
        # Recovered old receipt must not remove the new membership.
        self.assertEqual(self.request('POST', '/v1/teams/' + team + '/leave', 1, payload), result)
        self.assertEqual(self.detail(team)['membershipVersion'], new)
        self.request('POST', '/v1/teams/' + team + '/leave', 1,
                     {'commandId': command, 'expectedMembershipVersion': new}, 409)
        self.assertEqual(self.detail(team)['membershipVersion'], new)

    def test_03_missing_or_inconsistent_history_does_not_mint_a_guard(self):
        team = self.team(); self.join(team)
        old = self.detail(team)['membershipVersion']
        self.post('/v1/teams/' + team + '/leave', 1, expectedMembershipVersion=old)
        # Simulate a damaged/imported membership row without a new journaled join.
        with self.authority.database.transaction() as db:
            db.execute('INSERT INTO social_team_members VALUES(?,?,?)', (self.players[1], team, self.now))
        self.assertEqual(self.detail(team)['membershipVersion'], '')
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 1, expectedMembershipVersion=old)['state'], 'Rejected')
        self.assertTrue(self.detail(team)['isMember'])

    def test_04_kick_and_rejoin_do_not_reuse_the_old_version(self):
        team = self.team(); self.join(team)
        old = self.detail(team)['membershipVersion']
        self.post('/v1/teams/' + team + '/members/kick', 0, playerId=self.players[1])
        self.post('/v1/teams/' + team + '/members/unban', 0, playerId=self.players[1])
        self.join(team)
        self.assertNotEqual(self.detail(team)['membershipVersion'], old)
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 1, expectedMembershipVersion=old)['state'], 'Rejected')
        self.assertTrue(self.detail(team)['isMember'])

    def test_05_lost_committed_reply_is_recoverable_without_repeating_leave(self):
        team = self.team(); self.join(team)
        version = self.detail(team)['membershipVersion']; command = ident()
        payload = {'commandId': command, 'expectedMembershipVersion': version}
        def lost(stage):
            if stage == 'AfterCommit':
                raise OSError('synthetic lost response')
        self.authority.checkpoint = lost
        self.request('POST', '/v1/teams/' + team + '/leave', 1, payload, 500)
        self.authority.checkpoint = None; self.restart()
        self.join(team)
        result = self.request('POST', '/v1/teams/' + team + '/leave', 1, payload)
        self.assertEqual(result['state'], 'Left')
        self.assertTrue(self.detail(team)['isMember'])
        receipt = self.get('/v1/social/operations/' + command,
                           1, params={'operation': 'social.team.leave/' + team})
        self.assertEqual(receipt['status'], 'Committed')
        self.assertEqual(receipt['response'], result)

    def test_06_concurrent_guards_can_remove_only_one_membership(self):
        team = self.team(); self.join(team)
        version = self.detail(team)['membershipVersion']
        def attempt(_):
            response = self.client.post('/v1/teams/' + team + '/leave', headers=self.headers(1),
                                        json={'commandId': ident(), 'expectedMembershipVersion': version})
            return response.status_code, response.json()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(attempt, range(2)))
        self.assertEqual([r[0] for r in responses], [200, 200])
        self.assertEqual(sorted(r[1]['state'] for r in responses), ['Left', 'Rejected'])
        self.assertEqual(next(r[1]['reason'] for r in responses if r[1]['state'] == 'Rejected'), 'team_permission_denied')
        self.assertFalse(self.detail(team, 1)['isMember'])

    def test_07_legacy_digest_null_and_leader_change(self):
        team = self.team(); self.join(team)
        version = self.detail(team)['membershipVersion']
        self.request('POST', '/v1/teams/' + team + '/leave', 1,
                     {'commandId': ident(), 'expectedMembershipVersion': None}, 422)
        self.post('/v1/teams/' + team + '/members/transfer', 0, playerId=self.players[1])
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 1, expectedMembershipVersion=version)['reason'], 'team_membership_changed')
        self.assertEqual(self.detail(team)['leaveRestrictionReason'], 'transfer_ownership_first')
        owner_version = self.detail(team)['membershipVersion']
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 1, expectedMembershipVersion=owner_version)['reason'], 'transfer_ownership_first')
        # The prior command shape remains exactly replayable for old clients.
        legacy = ident(); self.post('/v1/teams/' + team + '/leave', 0, command=legacy)
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 0, command=legacy)['state'], 'Left')
        self.assertTrue(self.detail(team)['leaveClosesTeam'])

    def test_08_redundant_join_invalidates_confirmation_safely(self):
        team = self.team(); self.join(team)
        old = self.detail(team)['membershipVersion']
        self.join(team)  # API no-op, new durable receipt
        self.assertNotEqual(old, self.detail(team)['membershipVersion'])
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 1, expectedMembershipVersion=old)['state'], 'Rejected')
        self.assertTrue(self.detail(team)['isMember'])

    def test_09_same_command_id_in_create_and_join_namespaces_is_not_reused(self):
        command = ident()
        team = self.post('/v1/teams', 0, command=command, name='Rain', description='')['teamId']
        self.join(team)
        self.post('/v1/teams/' + team + '/members/transfer', 0, playerId=self.players[1])
        old = self.detail(team, 0)['membershipVersion']
        self.post('/v1/teams/' + team + '/leave', 0, expectedMembershipVersion=old)
        self.join(team, 0, command=command)
        self.assertNotEqual(old, self.detail(team, 0)['membershipVersion'])
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 0, expectedMembershipVersion=old)['state'], 'Rejected')
        self.assertTrue(self.detail(team, 0)['isMember'])

    def test_10_vacuum_keeps_guard_stable_and_rejoin_still_changes_it(self):
        team = self.team(); self.join(team)
        old = self.detail(team)['membershipVersion']
        with self.authority.database.connect() as db:
            db.execute('VACUUM')
        self.assertEqual(old, self.detail(team)['membershipVersion'])
        self.post('/v1/teams/' + team + '/leave', 1, expectedMembershipVersion=old)
        self.join(team)
        new = self.detail(team)['membershipVersion']
        self.assertNotEqual(old, new)
        with self.authority.database.connect() as db:
            db.execute('VACUUM')
        self.assertEqual(new, self.detail(team)['membershipVersion'])
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 1, expectedMembershipVersion=old)['state'], 'Rejected')

    def test_11_consequence_changes_invalidate_old_confirmations(self):
        team = self.team(); self.join(team)
        member_before = self.detail(team)['membershipVersion']
        # A player becoming owner must review the current owner consequence.
        self.post('/v1/teams/' + team + '/members/transfer', 0, playerId=self.players[1])
        owner_before = self.detail(team)['membershipVersion']
        self.assertNotEqual(member_before, owner_before)
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 1, expectedMembershipVersion=member_before)['state'], 'Rejected')
        # Once the other member leaves, a new action would close the team.
        self.post('/v1/teams/' + team + '/leave', 0)
        solo = self.detail(team)
        self.assertTrue(solo['leaveClosesTeam'])
        self.assertNotEqual(solo['membershipVersion'], owner_before)
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 1, expectedMembershipVersion=owner_before)['state'], 'Rejected')
        self.assertTrue(self.detail(team)['isMember'])

    def test_12_lost_rejected_receipt_stays_rejected_after_conditions_change(self):
        team = self.team(); self.join(team)
        version = self.detail(team, 0)['membershipVersion']; command = ident()
        payload = {'commandId': command, 'expectedMembershipVersion': version}
        def lost(stage):
            if stage == 'AfterCommit':
                raise OSError('synthetic lost response')
        self.authority.checkpoint = lost
        self.request('POST', '/v1/teams/' + team + '/leave', 0, payload, 500)
        self.authority.checkpoint = None; self.restart()
        receipt = self.get('/v1/social/operations/' + command, 0,
                           params={'operation': 'social.team.leave/' + team})
        expected = {'teamId': team, 'state': 'Rejected', 'reason': 'transfer_ownership_first'}
        self.assertEqual(receipt['status'], 'Committed')
        self.assertEqual(receipt['response'], expected)
        # Changing the conditions does not turn a prior rejection into a leave.
        self.post('/v1/teams/' + team + '/members/transfer', 0, playerId=self.players[1])
        self.assertEqual(self.request('POST', '/v1/teams/' + team + '/leave', 0, payload), expected)
        self.assertTrue(self.detail(team, 0)['isMember'])
        fresh = self.detail(team, 0)['membershipVersion']
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 0, expectedMembershipVersion=fresh)['state'], 'Left')

    def test_13_rejected_receipts_are_owner_scoped_and_auth_failure_is_not_journaled(self):
        team = self.team(); self.join(team)
        version = self.detail(team, 0)['membershipVersion']; command = ident()
        value = self.post('/v1/teams/' + team + '/leave', 0, command=command, expectedMembershipVersion=version)
        self.assertEqual(value['reason'], 'transfer_ownership_first')
        other = self.get('/v1/social/operations/' + command, 1,
                         params={'operation': 'social.team.leave/' + team})
        self.assertEqual(other['status'], 'Absent')
        forbidden = ident()
        response = self.client.post('/v1/teams/' + team + '/leave',
                                    json={'commandId': forbidden, 'expectedMembershipVersion': version})
        self.assertEqual(response.status_code, 401)
        absent = self.get('/v1/social/operations/' + forbidden, 0,
                          params={'operation': 'social.team.leave/' + team})
        self.assertEqual(absent['status'], 'Absent')

    def test_14_preexisting_legacy_command_digest_and_receipt_recover(self):
        team = self.team(); self.join(team)
        command = ident()
        # Construct the historic wire/digest independently of the current
        # Pydantic model, as if this committed command predates this change.
        historic_body = ('{"commandId":"' + command + '"}').encode('ascii')
        digest = hashlib.sha256(historic_body).hexdigest()
        receipt = {'teamId': team, 'state': 'Left'}
        with self.authority.database.transaction() as db:
            db.execute('INSERT INTO commands VALUES(?,?,?,?,?)',
                       (self.players[1], 'social.team.leave/' + team, command,
                        digest, json.dumps(receipt, sort_keys=True, separators=(',', ':'))))
        self.join(team)  # later durable membership evidence, as after rejoining
        # The cached historic receipt is recovered without mutating a current
        # membership; newer versioned payloads cannot reuse its command ID.
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 1, command=command), receipt)
        self.assertTrue(self.detail(team)['isMember'])
        version = self.detail(team)['membershipVersion']
        self.post('/v1/teams/' + team + '/leave', 1, status=409,
                  command=command, expectedMembershipVersion=version)
        self.assertTrue(self.detail(team)['isMember'])


if __name__ == '__main__':
    unittest.main()
