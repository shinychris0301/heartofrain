"""Real SQLite/service friend/profile proof; no native UI/social-provider claim."""
import concurrent.futures
import json
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError
from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.friends import Friends, blocked, eligible_friend, require_social_peer
from hotr_backend.service import ServiceError
from hotr_backend.social_schemas import FriendResponse, FriendTarget, ProfileUpdate

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class FriendsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-friends-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 100 * 86400
        self.app = create_app(self.path, CONFIG, lambda: self.now)
        self.authority = self.app.state.authority
        self.friends = Friends(self.authority, enabled=True)
        self.identities = [self.authority.provision(lifetime=2_592_000) for _ in range(4)]
        self.refresh_actors()

    def tearDown(self):
        self.temp.cleanup()

    def refresh_actors(self):
        self.actors = [self.authority.authenticate(v['token']) for v in self.identities]

    def target(self, index, command=None):
        return FriendTarget(commandId=command or ident(), playerId=self.actors[index].player)

    def send(self, first=0, second=1):
        return self.friends.send(self.actors[first], self.target(second))

    def accept(self, first=0, second=1):
        request = self.send(first, second)
        return self.friends.respond(self.actors[second], FriendResponse(commandId=ident(), requestId=request['requestId'], action='accept'))

    def expect(self, status, action):
        with self.assertRaises(ServiceError) as error:
            action()
        self.assertEqual(error.exception.status, status)
        return error.exception

    def count(self, table):
        with self.authority.database.connect() as db:
            return db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def test_01_default_disabled_and_public_profile_has_no_private_data(self):
        self.expect(503, lambda: Friends(self.authority).me(self.actors[0]))
        profile = self.friends.profile(self.actors[0], self.actors[1].player)
        self.assertEqual(set(profile), {'playerId', 'displayName', 'completedLevels', 'leaderboardOptIn'})
        self.assertEqual(profile['displayName'], 'Rainkeeper')
        self.assertFalse(profile['leaderboardOptIn'])
        self.assertEqual(self.count('social_profiles'), 0)
        self.assertNotIn('token', json.dumps(profile))
        self.assertNotIn('coins', profile)

    def test_02_normalized_profile_and_explicit_optin_idempotency(self):
        request = ProfileUpdate(commandId=ident(), displayName='  Cafe\u0301  ', leaderboardOptIn=True)
        first = self.friends.update_profile(self.actors[0], request)
        self.assertEqual(first['displayName'], 'Café')
        self.assertTrue(first['leaderboardOptIn'])
        self.assertEqual(self.friends.update_profile(self.actors[0], request), first)
        self.assertEqual(self.count('social_profiles'), 1)
        changed = ProfileUpdate(commandId=request.commandId, displayName='Other', leaderboardOptIn=False)
        self.expect(409, lambda: self.friends.update_profile(self.actors[0], changed))
        self.assertEqual(self.friends.me(self.actors[0]), first)
        self.assertEqual(self.count('wallet_ledger'), 4)

    def test_03_unicode_controls_surrogates_length_and_forged_fields(self):
        for value in ('', '   ', 'x' * 21, 'A\nB', 'A\u202eB', 'A\u2028B', 'A\ud800B', 'a' + '\u0301' * 256):
            with self.subTest(value=repr(value)), self.assertRaises(ValidationError):
                ProfileUpdate(commandId=ident(), displayName=value)
        for value in ('Хранитель дождя', '😀' * 20, 'e\u0301' * 20):
            self.friends.update_profile(self.actors[0], ProfileUpdate(commandId=ident(), displayName=value))
        with self.assertRaises(ValidationError):
            ProfileUpdate(commandId=ident(), displayName='Name', completedLevels=50)
        with self.assertRaises(ValidationError):
            ProfileUpdate(commandId=ident(), displayName='Name', leaderboardOptIn=1)

    def test_04_request_recipient_explicitly_accepts_mutually(self):
        request = self.send()
        self.assertEqual(request['state'], 'Pending')
        self.assertEqual(self.friends.list(self.actors[0])['friends'], [])
        self.expect(409, lambda: self.send(1, 0))  # A reciprocal send never silently accepts.
        response = FriendResponse(commandId=ident(), requestId=request['requestId'], action='accept')
        self.expect(403, lambda: self.friends.respond(self.actors[0], response))
        self.expect(404, lambda: self.friends.respond(self.actors[2], response))
        first = self.friends.respond(self.actors[1], response)
        self.assertEqual(first['state'], 'Accepted')
        self.assertEqual(self.friends.respond(self.actors[1], response), first)
        self.assertEqual(self.friends.list(self.actors[0])['friends'][0]['playerId'], self.actors[1].player)
        self.assertEqual(self.friends.list(self.actors[1])['friends'][0]['playerId'], self.actors[0].player)
        with self.authority.database.transaction() as db:
            self.assertTrue(eligible_friend(db, self.actors[0].player, self.actors[1].player))
            require_social_peer(db, self.actors[0], self.actors[1].player, friends_required=True)

    def test_05_pending_decline_and_cancel_stay_private(self):
        request = self.send()
        self.assertEqual(self.friends.requests(self.actors[0])['requests'][0]['direction'], 'outgoing')
        self.assertEqual(self.friends.requests(self.actors[1])['requests'][0]['direction'], 'incoming')
        self.assertEqual(self.friends.requests(self.actors[2])['requests'], [])
        decline = FriendResponse(commandId=ident(), requestId=request['requestId'], action='decline')
        self.friends.respond(self.actors[1], decline)
        self.assertEqual(self.friends.requests(self.actors[0])['requests'], [])
        self.assertEqual(self.friends.requests(self.actors[1])['requests'], [])
        self.expect(409, self.send)
        self.now += 86400
        self.refresh_actors()
        second = self.send()
        self.assertNotEqual(second['requestId'], request['requestId'])
        self.expect(403, lambda: self.friends.respond(self.actors[1], FriendResponse(commandId=ident(), requestId=second['requestId'], action='cancel')))
        cancelled = self.friends.respond(self.actors[0], FriendResponse(commandId=ident(), requestId=second['requestId'], action='cancel'))
        self.assertEqual(cancelled['state'], 'Cancelled')

    def test_06_remove_is_mutual_and_durable_without_wallet_effects(self):
        self.accept()
        request = self.target(1)
        first = self.friends.remove(self.actors[0], request)
        self.assertEqual(self.friends.remove(self.actors[0], request), first)
        self.assertEqual(self.friends.list(self.actors[0])['friends'], [])
        self.assertEqual(self.friends.list(self.actors[1])['friends'], [])
        self.assertEqual(self.count('wallet_ledger'), 4)

    def test_07_block_suppresses_both_directions_and_old_receipts(self):
        request = self.target(1)
        sent = self.friends.send(self.actors[0], request)
        response = FriendResponse(commandId=ident(), requestId=sent['requestId'], action='accept')
        self.friends.respond(self.actors[1], response)
        self.friends.block(self.actors[0], self.target(1))
        for first, second in ((0, 1), (1, 0)):
            self.expect(404, lambda: self.friends.profile(self.actors[first], self.actors[second].player))
            self.assertEqual(self.friends.list(self.actors[first])['friends'], [])
            self.assertEqual(self.friends.requests(self.actors[first])['requests'], [])
        self.expect(404, lambda: self.friends.send(self.actors[0], request))
        self.expect(404, lambda: self.friends.respond(self.actors[1], response))
        self.assertEqual(len(self.friends.blocks(self.actors[0])['blocks']), 1)
        self.assertEqual(self.friends.blocks(self.actors[1])['blocks'], [])
        with self.authority.database.transaction() as db:
            self.assertTrue(blocked(db, self.actors[1].player, self.actors[0].player))
            self.assertFalse(eligible_friend(db, self.actors[0].player, self.actors[1].player))

    def test_08_unblock_only_own_direction_and_never_auto_refriends(self):
        self.accept()
        self.friends.block(self.actors[0], self.target(1))
        self.friends.block(self.actors[1], self.target(0))
        self.friends.unblock(self.actors[0], self.target(1))
        self.expect(404, lambda: self.friends.profile(self.actors[0], self.actors[1].player))
        self.friends.unblock(self.actors[1], self.target(0))
        self.friends.profile(self.actors[0], self.actors[1].player)
        self.assertEqual(self.friends.list(self.actors[0])['friends'], [])

    def test_09_deleted_target_and_stale_actor_are_suppressed(self):
        self.accept()
        profile = ProfileUpdate(commandId=ident(), displayName='Before')
        self.friends.update_profile(self.actors[1], profile)
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.actors[1].player, self.now))
        self.expect(404, lambda: self.friends.profile(self.actors[0], self.actors[1].player))
        self.expect(410, lambda: self.friends.update_profile(self.actors[1], profile))
        self.assertEqual(self.friends.list(self.actors[0])['friends'], [])
        self.assertEqual(self.friends.requests(self.actors[0])['requests'], [])
        with self.authority.database.transaction() as db:
            self.assertFalse(eligible_friend(db, self.actors[0].player, self.actors[1].player))
            self.expect(404, lambda: require_social_peer(db, self.actors[0], self.actors[1].player))

    def test_10_revoked_actor_cannot_get_cached_profile_or_social_reads(self):
        request = ProfileUpdate(commandId=ident(), displayName='Before')
        self.friends.update_profile(self.actors[0], request)
        self.authority.revoke(self.identities[0]['token'])
        for action in (lambda: self.friends.update_profile(self.actors[0], request),
                       lambda: self.friends.list(self.actors[0]), lambda: self.friends.blocks(self.actors[0])):
            self.expect(401, action)

    def test_11_parallel_duplicate_send_is_one_pair_and_one_receipt(self):
        request = self.target(1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(lambda _: self.friends.send(self.actors[0], request), range(2)))
        self.assertEqual(values[0], values[1])
        self.assertEqual(self.count('social_friend_requests'), 1)
        changed = FriendTarget(commandId=request.commandId, playerId=self.actors[2].player)
        self.expect(409, lambda: self.friends.send(self.actors[0], changed))

    def test_12_reciprocal_race_does_not_implicitly_accept(self):
        barrier = threading.Barrier(2)
        def send(pair):
            barrier.wait(timeout=5)
            try:
                return self.send(*pair)['state']
            except ServiceError as error:
                return error.status
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(send, [(0, 1), (1, 0)]))
        self.assertCountEqual(values, ['Pending', 409])
        self.assertEqual(self.friends.list(self.actors[0])['friends'], [])
        self.assertEqual(self.count('social_friend_requests'), 1)

    def test_13_accept_vs_block_always_ends_ineligible(self):
        sent = self.send()
        response = FriendResponse(commandId=ident(), requestId=sent['requestId'], action='accept')
        barrier = threading.Barrier(2)
        def act(index):
            barrier.wait(timeout=5)
            try:
                return self.friends.respond(self.actors[1], response) if index == 0 else self.friends.block(self.actors[0], self.target(1))
            except ServiceError as error:
                return error.status
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(act, range(2)))
        self.assertTrue(isinstance(values[1], dict) and values[1]['blocked'])
        self.assertEqual(self.friends.list(self.actors[0])['friends'], [])
        with self.authority.database.transaction() as db:
            self.assertFalse(eligible_friend(db, self.actors[0].player, self.actors[1].player))

    def test_14_before_after_commit_faults_recover_without_duplicate_requests(self):
        request = self.target(1)
        def before(stage):
            if stage == 'BeforeCommit':
                raise RuntimeError('controlled beforecommit')
        self.authority.checkpoint = before
        with self.assertRaises(RuntimeError):
            self.friends.send(self.actors[0], request)
        self.assertEqual(self.count('social_friend_requests'), 0)
        def after(stage):
            if stage == 'AfterCommit':
                raise RuntimeError('controlled lost reply')
        self.authority.checkpoint = after
        with self.assertRaises(RuntimeError):
            self.friends.send(self.actors[0], request)
        self.assertEqual(self.count('social_friend_requests'), 1)
        self.authority.checkpoint = None
        self.assertEqual(self.friends.send(self.actors[0], request)['state'], 'Pending')
        self.assertEqual(self.count('social_friend_requests'), 1)

    def test_15_restart_preserves_profile_relationship_and_block(self):
        self.friends.update_profile(self.actors[0], ProfileUpdate(commandId=ident(), displayName='Хранитель', leaderboardOptIn=True))
        self.accept()
        self.friends.block(self.actors[0], self.target(2))
        app = create_app(self.path, CONFIG, lambda: self.now)
        service = Friends(app.state.authority, enabled=True)
        self.assertEqual(service.me(self.actors[0])['displayName'], 'Хранитель')
        self.assertTrue(service.me(self.actors[0])['leaderboardOptIn'])
        self.assertEqual(len(service.list(self.actors[0])['friends']), 1)
        self.assertEqual(len(service.blocks(self.actors[0])['blocks']), 1)
        self.assertEqual(self.count('wallet_ledger'), 4)

    def test_16_pending_friend_limits_and_cooldown_are_bounded(self):
        with patch('hotr_backend.friends.MAX_PENDING', 1):
            self.send()
            self.expect(409, lambda: self.send(0, 2))
            self.expect(409, lambda: self.send(2, 1))
        pending = self.friends.requests(self.actors[1])['requests'][0]
        self.friends.respond(self.actors[1], FriendResponse(commandId=ident(), requestId=pending['requestId'], action='accept'))
        with patch('hotr_backend.friends.MAX_FRIENDS', 1):
            self.expect(409, lambda: self.send(0, 2))
        self.friends.remove(self.actors[0], self.target(1))
        self.expect(409, self.send)

    def test_17_private_pagination_contains_only_own_visible_records(self):
        for index in range(1, 4):
            self.accept(0, index)
        first = self.friends.list(self.actors[0], limit=1)
        second = self.friends.list(self.actors[0], after=first['nextCursor'], limit=2)
        ids = [p['playerId'] for p in first['friends'] + second['friends']]
        self.assertEqual(ids, sorted(v.player for v in self.actors[1:]))
        self.assertTrue(first['hasMore'])
        self.assertFalse(second['hasMore'])
        self.friends.block(self.actors[0], self.target(2))
        self.assertNotIn(self.actors[2].player, [p['playerId'] for p in self.friends.list(self.actors[0])['friends']])
        self.expect(422, lambda: self.friends.list(self.actors[0], after='bad'))
        self.expect(422, lambda: self.friends.requests(self.actors[0], limit=True))

    def test_18_self_unknown_forged_actor_and_private_request_ids(self):
        self.expect(422, lambda: self.send(0, 0))
        self.expect(404, lambda: self.friends.profile(self.actors[0], ident()))
        self.expect(404, lambda: self.friends.respond(self.actors[0], FriendResponse(commandId=ident(), requestId=ident(), action='accept')))
        with self.assertRaises(ValidationError):
            FriendTarget(commandId=ident(), playerId=self.actors[1].player, requesterId=self.actors[2].player)
        with self.authority.database.transaction() as db:
            self.assertFalse(eligible_friend(db, self.actors[0].player, ident()))
            self.expect(404, lambda: require_social_peer(db, self.actors[0], self.actors[1].player, friends_required=True))

    def test_19_old_generation_retry_cannot_accept_new_pending_request(self):
        first = self.send()
        accept = FriendResponse(commandId=ident(), requestId=first['requestId'], action='accept')
        receipt = self.friends.respond(self.actors[1], accept)
        self.friends.remove(self.actors[0], self.target(1))
        self.now += 86400
        self.refresh_actors()
        second = self.send()
        self.assertNotEqual(first['requestId'], second['requestId'])
        self.assertEqual(self.friends.respond(self.actors[1], accept), receipt)
        self.expect(409, lambda: self.friends.respond(self.actors[1], FriendResponse(
            commandId=ident(), requestId=first['requestId'], action='accept')))
        self.assertEqual(self.friends.list(self.actors[0])['friends'], [])
        self.assertEqual(self.friends.requests(self.actors[1])['requests'][0]['requestId'], second['requestId'])
        self.assertEqual(self.count('social_friend_requests'), 2)

    def test_20_real_authenticated_http_profile_friend_and_block_routes(self):
        headers = [{'Authorization': 'Bearer ' + value['token']} for value in self.identities]
        with TestClient(self.app, raise_server_exceptions=False) as client:
            self.assertEqual(client.get('/v1/profile', headers=headers[0]).status_code, 503)
        app = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True)
        with TestClient(app, raise_server_exceptions=False) as client:
            self.assertEqual(client.get('/v1/profile').status_code, 401)
            profile = client.post('/v1/profile', headers=headers[0], json={
                'commandId': ident(), 'displayName': '  Хранитель  ', 'leaderboardOptIn': True})
            self.assertEqual(profile.status_code, 200, profile.text)
            self.assertEqual(profile.json()['displayName'], 'Хранитель')
            self.assertTrue(profile.json()['leaderboardOptIn'])
            forged = client.post('/v1/profile', headers=headers[0], json={
                'commandId': ident(), 'displayName': 'Bad', 'completedLevels': 50})
            self.assertEqual(forged.status_code, 422)
            self.assertEqual(forged.json(), {'error': 'invalid_request'})
            sent = client.post('/v1/friends/request', headers=headers[0], json={
                'commandId': ident(), 'playerId': self.actors[1].player})
            self.assertEqual(sent.status_code, 200, sent.text)
            accepted = client.post('/v1/friends/respond', headers=headers[1], json={
                'commandId': ident(), 'requestId': sent.json()['requestId'], 'action': 'accept'})
            self.assertEqual(accepted.status_code, 200, accepted.text)
            self.assertEqual(len(client.get('/v1/friends', headers=headers[0]).json()['friends']), 1)
            block = client.post('/v1/blocks/add', headers=headers[1], json={
                'commandId': ident(), 'playerId': self.actors[0].player})
            self.assertEqual(block.status_code, 200, block.text)
            self.assertEqual(client.get('/v1/players/' + self.actors[1].player, headers=headers[0]).status_code, 404)
            self.assertEqual(client.get('/v1/friends', headers=headers[0]).json()['friends'], [])
            self.assertEqual(client.get('/v1/blocks', headers=headers[0]).json()['blocks'], [])
            self.assertEqual(len(client.get('/v1/blocks', headers=headers[1]).json()['blocks']), 1)


if __name__ == '__main__':
    unittest.main()
