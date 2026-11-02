"""Actual ASGI/SQLite field-specific profile commands and privacy races."""
import concurrent.futures
import json
from pathlib import Path
import tempfile
import threading
import unittest
import uuid

from fastapi.testclient import TestClient
from pydantic import ValidationError

from hotr_backend.api import create_app
from hotr_backend.friends import Friends
from hotr_backend.service import ServiceError
from hotr_backend.social_operations import SocialOperations
from hotr_backend.social_schemas import ProfileNameUpdate, ProfileConsentUpdate, ProfileUpdate

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class ProfileFieldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-profile-fields-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 100 * 86400
        self.app = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True)
        self.authority = self.app.state.authority
        self.owner = self.authority.provision(lifetime=2592000)
        self.second_device = self.authority.provision(player=self.owner['playerId'], lifetime=2592000)
        self.peer = self.authority.provision(lifetime=2592000)
        self.actor = self.authority.authenticate(self.owner['token'])
        self.other = self.authority.authenticate(self.second_device['token'])
        self.service = Friends(self.authority, True)

    def tearDown(self):
        self.temp.cleanup()

    def expect(self, status, operation):
        with self.assertRaises(ServiceError) as error:
            operation()
        self.assertEqual(error.exception.status, status)

    def rename(self, name='Дождь', command=None, actor=None):
        return self.service.update_name(actor or self.actor, ProfileNameUpdate(commandId=command or ident(), displayName=name))

    def consent(self, value, command=None, actor=None):
        return self.service.update_consent(actor or self.actor, ProfileConsentUpdate(commandId=command or ident(), leaderboardOptIn=value))

    def test_01_name_creates_optout_and_consent_preserves_default_name(self):
        value = self.rename('  Cafe\u0301  ')
        self.assertEqual(value['displayName'], 'Café')
        self.assertFalse(value['leaderboardOptIn'])
        peer = self.authority.authenticate(self.peer['token'])
        value = self.consent(True, actor=peer)
        self.assertEqual(value['displayName'], 'Rainkeeper')
        self.assertTrue(value['leaderboardOptIn'])
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rewards').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM wallet_ledger').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM verified_clears').fetchone()[0], 0)

    def test_02_stale_other_device_optout_is_never_undone_by_rename(self):
        self.service.update_profile(self.actor, ProfileUpdate(commandId=ident(), displayName='Old', leaderboardOptIn=True))
        stale = self.service.me(self.actor)
        self.assertTrue(stale['leaderboardOptIn'])
        self.consent(False, actor=self.other)
        self.assertFalse(self.rename('New')['leaderboardOptIn'])
        self.assertFalse(self.service.me(self.actor)['leaderboardOptIn'])
        # The inverse race: a consent click must not replay a stale old name.
        stale_name = self.service.me(self.other)['displayName']
        self.rename('Newest', actor=self.actor)
        result = self.consent(True, actor=self.other)
        self.assertNotEqual(result['displayName'], stale_name)
        self.assertEqual(result['displayName'], 'Newest')

    def test_03_parallel_sqlite_writers_preserve_both_independent_fields(self):
        for index in range(6):
            self.service.update_profile(self.actor, ProfileUpdate(commandId=ident(), displayName='Old', leaderboardOptIn=True))
            barrier = threading.Barrier(2)
            def rename():
                barrier.wait(timeout=3)
                return self.rename('New' + str(index), actor=self.actor)
            def optout():
                barrier.wait(timeout=3)
                return self.consent(False, actor=self.other)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                tasks = [pool.submit(rename), pool.submit(optout)]
                for task in tasks:
                    task.result(timeout=10)
            value = self.service.me(self.actor)
            self.assertEqual(value['displayName'], 'New' + str(index))
            self.assertFalse(value['leaderboardOptIn'])

    def test_04_exact_cached_receipts_never_reapply_historical_consent_or_name(self):
        name_id, consent_id = ident(), ident()
        first = self.rename('First', name_id)
        opted = self.consent(True, consent_id)
        self.rename('Second')
        self.consent(False)
        self.assertEqual(self.rename('First', name_id), first)
        self.assertEqual(self.consent(True, consent_id), opted)
        current = self.service.me(self.actor)
        self.assertEqual((current['displayName'], current['leaderboardOptIn']), ('Second', False))
        self.expect(409, lambda: self.rename('Forged', name_id))
        self.expect(409, lambda: self.consent(False, consent_id))

    def test_05_strict_fields_unicode_and_explicit_boolean(self):
        for value in ('', 'A\nB', 'A\u2028B', 'A\u2029B', 'A\u202eB', 'A\ud800B', 'x' * 21):
            with self.subTest(value=repr(value)), self.assertRaises(ValidationError):
                ProfileNameUpdate(commandId=ident(), displayName=value)
        with self.assertRaises(ValidationError):
            ProfileNameUpdate(commandId=ident(), displayName='New', leaderboardOptIn=True)
        for body in ({'commandId': ident()}, {'commandId': ident(), 'leaderboardOptIn': 1},
                     {'commandId': ident(), 'leaderboardOptIn': True, 'displayName': 'Forged'}):
            with self.assertRaises(ValidationError):
                ProfileConsentUpdate(**body)

    def test_06_revocation_and_deletion_checked_before_cached_response(self):
        name_id, consent_id = ident(), ident()
        self.rename(command=name_id)
        self.consent(True, consent_id)
        self.authority.revoke(self.owner['token'])
        self.expect(401, lambda: self.rename(command=name_id))
        self.expect(401, lambda: self.consent(True, consent_id))
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)", (self.actor.player, self.now))
        self.expect(410, lambda: self.rename(actor=self.other))
        self.expect(410, lambda: self.consent(False, actor=self.other))

    def test_07_actual_http_routes_and_typed_owner_receipt_recovery(self):
        headers = {'Authorization': 'Bearer ' + self.owner['token']}
        with TestClient(self.app) as client:
            rename = {'commandId': ident(), 'displayName': 'Сердце дождя'}
            response = client.post('/v1/profile/name', json=rename, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['displayName'], rename['displayName'])
            self.assertFalse(response.json()['leaderboardOptIn'])
            consent = {'commandId': ident(), 'leaderboardOptIn': True}
            opted = client.post('/v1/profile/leaderboard-consent', json=consent, headers=headers)
            self.assertEqual(opted.status_code, 200)
            self.assertEqual(opted.json()['displayName'], rename['displayName'])
            for body, operation in ((rename, 'social.profile.name'), (consent, 'social.profile.consent')):
                receipt = client.get('/v1/social/operations/' + body['commandId'], params={'operation': operation}, headers=headers)
                self.assertEqual(receipt.status_code, 200)
                self.assertEqual(receipt.json()['status'], 'Committed')
                self.assertEqual(set(receipt.json()['response']), {'playerId', 'displayName', 'completedLevels', 'leaderboardOptIn'})
                peer = client.get('/v1/social/operations/' + body['commandId'], params={'operation': operation}, headers={'Authorization': 'Bearer ' + self.peer['token']})
                self.assertEqual(peer.json()['status'], 'Absent')
            self.assertEqual(client.post('/v1/profile/name', json=rename).status_code, 401)
            self.assertEqual(client.post('/v1/profile/name', json=dict(rename, leaderboardOptIn=False), headers=headers).status_code, 422)
            self.assertEqual(client.post('/v1/profile/leaderboard-consent', json=dict(consent, displayName='Forged'), headers=headers).status_code, 422)

    def test_08_lost_ack_and_service_reopen_preserve_exact_operation_receipt(self):
        command = ident()
        self.authority.checkpoint = lambda stage: (_ for _ in ()).throw(OSError('controlled lost reply')) if stage == 'AfterCommit' else None
        with self.assertRaises(OSError):
            self.rename('Recover', command)
        self.authority.checkpoint = None
        other = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True)
        actor = other.state.authority.authenticate(self.owner['token'])
        service = Friends(other.state.authority, True)
        request = ProfileNameUpdate(commandId=command, displayName='Recover')
        recovered = service.update_name(actor, request)
        self.assertEqual(recovered['displayName'], 'Recover')
        receipt = SocialOperations(other.state.authority, True).get(actor, command, 'social.profile.name')
        self.assertEqual(receipt['response'], recovered)
        with other.state.authority.database.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM commands WHERE operation='social.profile.name' AND command_id=?", (command,)).fetchone()[0], 1)

    def test_09_explicit_social_activation_still_required(self):
        disabled = Friends(self.authority)
        self.expect(503, lambda: disabled.update_name(self.actor, ProfileNameUpdate(commandId=ident(), displayName='Denied')))
        self.expect(503, lambda: disabled.update_consent(self.actor, ProfileConsentUpdate(commandId=ident(), leaderboardOptIn=True)))


if __name__ == '__main__':
    unittest.main()
