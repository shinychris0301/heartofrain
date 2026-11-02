"""SQLite/HTTP owner-receipt recovery; no store or native-page assertion."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.friends import Friends
from hotr_backend.messaging import Messaging
from hotr_backend.messaging_schemas import Command, CreateTeam, SendMessage, TeamTarget
from hotr_backend.service import Actor, ServiceError
from hotr_backend.social_operations import SocialOperations, allowed_operation
from hotr_backend.social_schemas import FriendResponse, FriendTarget, ProfileUpdate
from hotr_backend.storage import canonical


def ident():
    return uuid.uuid4().hex


CONFIG = Path(__file__).resolve().parents[1] / 'config'


class SocialOperationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-social-receipts-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 100 * 86400
        self.app = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True)
        self.authority = self.app.state.authority
        self.identities = [self.authority.provision() for _ in range(3)]
        self.actors = [self.authority.authenticate(value['token']) for value in self.identities]
        self.service = SocialOperations(self.authority, enabled=True)
        self.friends, self.messages = Friends(self.authority, True), Messaging(self.authority, True)

    def tearDown(self):
        self.temp.cleanup()

    def expect(self, status, action):
        with self.assertRaises(ServiceError) as error:
            action()
        self.assertEqual(error.exception.status, status)

    def friend_pair(self):
        request = self.friends.send(self.actors[0], FriendTarget(commandId=ident(), playerId=self.actors[1].player))
        self.friends.respond(self.actors[1], FriendResponse(commandId=ident(), requestId=request['requestId'], action='accept'))

    def profile(self, command=None):
        request = ProfileUpdate(commandId=command or ident(), displayName='  Cafe\u0301  ', leaderboardOptIn=True)
        return request, self.friends.update_profile(self.actors[0], request)

    def test_01_disabled_input_and_allowlist_fail_closed(self):
        self.expect(503, lambda: SocialOperations(self.authority).get(self.actors[0], ident(), 'social.profile'))
        with self.assertRaises(ValueError):
            SocialOperations(self.authority, enabled=1)
        for operation in ('daily.claim', 'verified.clear', 'wallet.refill', 'commerce.confirm', 'social.moderate',
                          'social.ugc.moderate', 'social.team.join/not-an-id', 'social.message.send/Team/' + 'A' * 32,
                          'social.profile\n', None, 5):
            self.assertFalse(allowed_operation(operation))
            self.expect(422, lambda operation=operation: self.service.get(self.actors[0], ident(), operation))
        for value in ('', 'x' * 32, 'A' * 32, ident() + '\n', None):
            self.expect(422, lambda value=value: self.service.get(self.actors[0], value, 'social.profile'))

    def test_02_absent_is_owner_metadata_not_failure_claim(self):
        command = ident()
        value = self.service.get(self.actors[0], command, 'social.profile')
        self.assertEqual(value, {'commandId': command, 'operation': 'social.profile', 'status': 'Absent', 'receiptScope': 'owner_operation_receipt'})
        self.assertNotIn('failed', json.dumps(value).lower())
        self.assertNotIn('response', value)

    def test_03_normalized_profile_receipt_and_digest_scope(self):
        request, response = self.profile()
        result = self.service.get(self.actors[0], request.commandId, 'social.profile')
        self.assertEqual(result['status'], 'Committed')
        self.assertEqual(result['response'], response)
        self.assertEqual(response['displayName'], 'Café')
        self.assertEqual(result['payloadDigest'], hashlib.sha256(canonical(request.model_dump()).encode()).hexdigest())
        self.assertEqual(result['digestScope'], 'server_normalized_model_not_client_json')
        self.assertNotIn('token', json.dumps(result))
        self.assertNotIn('coins', json.dumps(result))

    def test_04_owner_and_full_operation_are_part_of_lookup(self):
        request, _ = self.profile()
        self.assertEqual(self.service.get(self.actors[1], request.commandId, 'social.profile')['status'], 'Absent')
        self.assertEqual(self.service.get(self.actors[0], request.commandId, 'social.friend.send')['status'], 'Absent')
        self.expect(403, lambda: self.service.get(Actor(self.actors[0].player, self.now), request.commandId, 'social.profile'))
        operator = self.authority.provision(role='verifier')
        verifier = self.authority.authenticate(operator['token'], role='verifier')
        self.expect(403, lambda: self.service.get(verifier, request.commandId, 'social.profile'))

    def test_05_after_commit_lost_response_is_recovered_without_second_mutation(self):
        command = ident()
        self.authority.checkpoint = lambda stage: (_ for _ in ()).throw(OSError('controlled lost response')) if stage == 'AfterCommit' else None
        with self.assertRaises(OSError):
            self.profile(command)
        self.authority.checkpoint = None
        receipt = self.service.get(self.actors[0], command, 'social.profile')
        self.assertEqual(receipt['status'], 'Committed')
        self.assertEqual(self.profile(command)[1], receipt['response'])
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM commands WHERE player_id=? AND command_id=?', (self.actors[0].player, command)).fetchone()[0], 1)

    def test_06_message_receipt_survives_block_without_returning_message_body(self):
        self.friend_pair()
        request = SendMessage(commandId=ident(), text='Private message text never returned in a receipt')
        response = self.messages.send(self.actors[0], 'Direct', self.actors[1].player, request)
        self.friends.block(self.actors[1], FriendTarget(commandId=ident(), playerId=self.actors[0].player))
        operation = 'social.message.send/Direct/' + self.actors[1].player
        result = self.service.get(self.actors[0], request.commandId, operation)
        self.assertEqual(result['response'], response)
        self.assertNotIn(request.text, json.dumps(result))
        self.assertNotIn('text', result['response'])
        self.assertEqual(self.service.get(self.actors[1], request.commandId, operation)['status'], 'Absent')

    def test_07_transfer_receipt_survives_changed_owner_permission(self):
        team = self.messages.create_team(self.actors[0], CreateTeam(commandId=ident(), name='Team', description=''))['teamId']
        self.messages.join(self.actors[1], team, Command(commandId=ident()))
        request = TeamTarget(commandId=ident(), playerId=self.actors[1].player)
        response = self.messages.manage_member(self.actors[0], team, request, 'transfer')
        self.assertEqual(self.service.get(self.actors[0], request.commandId, 'social.team.transfer/' + team)['response'], response)

    def test_08_revoked_and_deleted_actor_cannot_read_existing_receipt(self):
        request, _ = self.profile()
        self.authority.revoke(self.identities[0]['token'])
        self.expect(401, lambda: self.service.get(self.actors[0], request.commandId, 'social.profile'))
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.actors[1].player, self.now))
        self.expect(410, lambda: self.service.get(self.actors[1], request.commandId, 'social.profile'))

    def test_09_restart_retains_receipt_and_minimal_projection(self):
        request, response = self.profile()
        with self.authority.database.transaction() as db:
            extended = dict(response, privateFutureField='must-not-be-exported', coins=100)
            db.execute('UPDATE commands SET response_json=? WHERE player_id=? AND operation=? AND command_id=?',
                       (canonical(extended), self.actors[0].player, 'social.profile', request.commandId))
        other = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True)
        actor = other.state.authority.authenticate(self.identities[0]['token'])
        result = SocialOperations(other.state.authority, True).get(actor, request.commandId, 'social.profile')
        self.assertEqual(result['response'], response)
        self.assertNotIn('privateFutureField', result['response'])

    def test_10_actual_http_requires_owner_and_preserves_same_receipt(self):
        request, response = self.profile()
        path = '/v1/social/operations/' + request.commandId
        with TestClient(self.app) as client:
            self.assertEqual(client.get(path, params={'operation': 'social.profile'}).status_code, 401)
            headers = {'Authorization': 'Bearer ' + self.identities[0]['token']}
            result = client.get(path, params={'operation': 'social.profile'}, headers=headers)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['response'], response)
            self.assertEqual(client.get(path, params={'operation': 'wallet.refill'}, headers=headers).status_code, 422)
            self.assertEqual(client.get(path, headers=headers).status_code, 422)


if __name__ == '__main__':
    unittest.main()
