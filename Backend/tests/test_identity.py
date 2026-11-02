"""Real HTTP/SQLite lifecycle tests with ephemeral device keys, not attestation."""
import base64
import concurrent.futures
import hashlib
import json
import secrets
import tempfile
import threading
import unittest
import uuid
from pathlib import Path

from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.identity import MAX_OUTSTANDING_CHALLENGES, SESSION_MAX_SECONDS
from hotr_backend.rustore_provider import VerifiedInvoice
from hotr_backend.service import ServiceError
from hotr_backend.wallet_schemas import ReserveAttempt

CONFIG = Path(__file__).resolve().parents[1] / 'config'
PROTOCOL = 'hotr-managed-identity-v1'


def identifier():
    return uuid.uuid4().hex


def secret():
    return secrets.token_urlsafe(32)


def digest(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def public(key):
    return base64.b64encode(key.public_key().export_key(format='DER')).decode('ascii')


def binding(value, purpose):
    # Independent wire-format construction, not production request_payload().
    result = {name: value[name] for name in ('requestId', 'publicKey')}
    result.update(protocol=PROTOCOL, purpose=purpose)
    fields = {
        'guest': [('refreshToken', 'refreshDigest'), ('recoverySecret', 'recoveryDigest')],
        'session': [('refreshToken', 'refreshDigest'), ('replacementToken', 'replacementDigest')],
        'recover': [('recoverySecret', 'recoveryDigest'), ('replacementRecoverySecret', 'replacementRecoveryDigest'),
                    ('refreshToken', 'refreshDigest')],
        'logout': [('refreshToken', 'refreshDigest')], 'delete': [('refreshToken', 'refreshDigest')],
    }
    result.update((target, digest(value[source])) for source, target in fields[purpose])
    if purpose in ('recover', 'delete'):
        result['playerId'] = value['playerId']
    return result


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-managed-identity-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 100 * 86400 + 1000
        self.app = create_app(self.path, CONFIG, lambda: self.now, identity_enabled=True)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.key = ECC.generate(curve='P-256')
        self.refresh, self.recovery = secret(), secret()

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def restart(self):
        self.client.close()
        self.app = create_app(self.path, CONFIG, lambda: self.now, identity_enabled=True)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def base(self, key=None, **values):
        return {'requestId': identifier(), 'publicKey': public(key or self.key), **values}

    def guest_body(self):
        return self.base(refreshToken=self.refresh, recoverySecret=self.recovery)

    def signed(self, value, purpose, key=None, client=None):
        key, client = key or self.key, client or self.client
        payload = digest(canonical(binding(value, purpose)))
        challenge = self.ok(client.post('/v1/identity/challenges', json={
            'purpose': purpose, 'requestId': value['requestId'], 'publicKey': value['publicKey'], 'payloadDigest': payload}))
        self.assertEqual(challenge['purpose'], purpose)
        self.assertEqual(challenge['requestId'], value['requestId'])
        self.assertEqual(challenge['payloadDigest'], payload)
        self.assertEqual(challenge['algorithm'], 'ES256-DER')
        self.assertEqual(challenge['keyFingerprint'], hashlib.sha256(base64.b64decode(value['publicKey'])).hexdigest())
        expected = PROTOCOL + '\n' + canonical({name: challenge[name] for name in (
            'challengeId', 'expiresAt', 'keyFingerprint', 'nonce', 'payloadDigest', 'purpose', 'requestId')})
        actual = base64.b64decode(challenge['signingBytes'], validate=True)
        self.assertEqual(actual, expected.encode('ascii'))
        self.assertEqual(challenge['expiresAt'], self.now + 60)
        signature = DSS.new(key, 'fips-186-3', encoding='der').sign(SHA256.new(actual))
        return {**value, 'challengeId': challenge['challengeId'], 'signature': base64.b64encode(signature).decode('ascii')}

    def signup(self):
        value = self.guest_body()
        return self.ok(self.client.post('/v1/identity/guest', json=self.signed(value, 'guest'))), value

    @staticmethod
    def headers(response):
        return {'Authorization': 'Bearer ' + response['accessToken']}

    def wallet(self, response):
        return self.ok(self.client.get('/v1/wallet', headers=self.headers(response)))

    def count(self, table):
        with self.app.state.authority.database.connect() as db:
            return db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def rotate(self, refresh=None, replacement=None):
        value = self.base(refreshToken=refresh or self.refresh, replacementToken=replacement or secret())
        return self.ok(self.client.post('/v1/identity/session', json=self.signed(value, 'session'))), value

    def recovery_body(self, response, key):
        return self.base(key, playerId=response['playerId'], recoverySecret=self.recovery,
                         replacementRecoverySecret=secret(), refreshToken=secret())

    def deletion_body(self, response, refresh=None):
        return self.base(playerId=response['playerId'], refreshToken=refresh or self.refresh)

    def test_01_default_disabled_has_no_public_signup(self):
        app = create_app(Path(self.temp.name) / 'disabled.sqlite3', CONFIG, lambda: self.now)
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post('/v1/identity/challenges', json={
                'purpose': 'guest', 'requestId': identifier(), 'publicKey': public(self.key), 'payloadDigest': '0' * 64})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json(), {'error': 'managed_identity_not_configured'})
        with app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM identity_devices').fetchone()[0], 0)

    def test_02_guest_genesis_once_and_hash_only_retry_across_restart(self):
        response, value = self.signup()
        wallet = self.wallet(response)
        self.assertEqual([wallet['coins'], wallet['stars'], *wallet['starting'], *wallet['tools'], wallet['lives']],
                         [1250, 0, 5, 5, 3, 2, 3, 3, 3, 3, 5])
        self.assertEqual(wallet['revision'], 1)
        self.assertEqual(response['expiresAt'], self.now + 900)
        self.assertEqual(response['refreshExpiresAt'], self.now + 30 * 86400)
        self.assertFalse(response['normalUnityProfileIntegrated'])
        self.assertFalse(response['productionEnabled'])
        self.restart()
        retry = self.ok(self.client.post('/v1/identity/guest', json=self.signed(value, 'guest')))
        self.assertTrue(retry['replayed'])
        self.assertEqual((retry['playerId'], retry['familyId']), (response['playerId'], response['familyId']))
        self.assertNotEqual(retry['accessToken'], response['accessToken'])
        self.assertEqual(self.wallet(retry), wallet)
        self.assertEqual(self.count('players'), 1)
        self.assertEqual(self.count('wallet_ledger'), 1)
        self.assertEqual(self.count('identity_sessions'), 1)
        with self.app.state.authority.database.connect() as db:
            dump = '\n'.join(db.iterdump())
        for value in (self.refresh, self.recovery, response['accessToken'], retry['accessToken']):
            self.assertNotIn(value, dump)
        self.assertNotIn('testclient', dump)

    def test_03_existing_device_new_request_cannot_reset_or_import(self):
        response, _ = self.signup()
        second = self.base(refreshToken=secret(), recoverySecret=secret())
        rejected = self.client.post('/v1/identity/guest', json=self.signed(second, 'guest'))
        self.assertEqual(rejected.status_code, 409)
        forged = {**self.signed(self.guest_body(), 'guest'), 'coins': 2_147_483_647}
        self.assertEqual(self.client.post('/v1/identity/guest', json=forged).status_code, 422)
        self.assertEqual(self.wallet(response)['coins'], 1250)
        self.assertEqual(self.count('players'), 1)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_04_key_validation_rejects_private_other_curve_and_noncanonical(self):
        keys = [self.key.export_key(format='DER'), ECC.generate(curve='P-384').public_key().export_key(format='DER'), b'x' * 100]
        for key in keys:
            response = self.client.post('/v1/identity/challenges', json={
                'purpose': 'guest', 'requestId': identifier(), 'publicKey': base64.b64encode(key).decode(), 'payloadDigest': '0' * 64})
            self.assertEqual(response.status_code, 422)
        key = public(self.key)
        response = self.client.post('/v1/identity/challenges', json={
            'purpose': 'guest', 'requestId': identifier(), 'publicKey': key + '\n', 'payloadDigest': '0' * 64})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.count('identity_sessions'), 0)

    def test_05_signature_body_key_and_expiry_bindings(self):
        value = self.guest_body()
        signed = self.signed(value, 'guest')
        for change in ({'refreshToken': secret()}, {'requestId': identifier()},
                       {'signature': base64.b64encode(b'x' * 70).decode()}, {'publicKey': public(ECC.generate(curve='P-256'))}):
            response = self.client.post('/v1/identity/guest', json={**signed, **change})
            self.assertEqual(response.status_code, 401)
        self.now += 60
        self.assertEqual(self.client.post('/v1/identity/guest', json=signed).status_code, 401)
        self.assertEqual(self.count('players'), 0)

    def test_06_refresh_rotation_retires_old_access_after_grace_and_exact_retry(self):
        first, _ = self.signup()
        rotated, value = self.rotate()
        self.assertEqual(rotated['familyId'], first['familyId'])
        self.assertEqual(self.client.get('/v1/wallet', headers=self.headers(first)).status_code, 200)
        self.now += 30
        self.assertEqual(self.client.get('/v1/wallet', headers=self.headers(first)).status_code, 401)
        self.assertEqual(self.wallet(rotated)['revision'], 1)
        self.restart()
        retry = self.ok(self.client.post('/v1/identity/session', json=self.signed(value, 'session')))
        self.assertTrue(retry['replayed'])
        self.assertEqual(retry['familyId'], first['familyId'])
        self.assertEqual(self.wallet(retry)['coins'], 1250)
        self.assertEqual(self.count('identity_refresh'), 2)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_06b_logout_still_revokes_access_immediately(self):
        first, _ = self.signup()
        self.ok(self.client.post('/v1/identity/logout', json=self.signed(self.base(refreshToken=self.refresh), 'logout')))
        self.assertEqual(self.client.get('/v1/wallet', headers=self.headers(first)).status_code, 401)

    def test_06c_verified_proxy_address_separates_identity_rate_buckets(self):
        app = create_app(self.path, CONFIG, lambda: self.now, identity_enabled=True,
                         trusted_client_header='X-Hotr-Verified-Client-IP')
        body = {'purpose': 'guest', 'requestId': identifier(), 'publicKey': '!' * 100, 'payloadDigest': '0' * 64}
        def post(client, address=None):
            headers = {'X-Hotr-Verified-Client-IP': address} if address else {}
            return client.post('/v1/identity/challenges', json=body, headers=headers).status_code
        with TestClient(app, raise_server_exceptions=False, client=('127.0.0.1', 50000)) as proxy:
            for _ in range(60):
                self.assertEqual(post(proxy, '203.0.113.7'), 422)
            self.assertEqual(post(proxy, '203.0.113.7'), 429)
            # Another player keeps working, and the blocked source spent no shared budget.
            self.assertEqual(post(proxy, '203.0.113.8'), 422)
            with app.state.authority.database.connect() as db:
                self.assertEqual(db.execute("SELECT requests FROM identity_rate_windows WHERE bucket='challenge/global'").fetchone()[0], 61)
            # A malformed or loopback value falls back to the socket peer.
            self.assertEqual(post(proxy, 'not-an-address'), 422)
            self.assertEqual(post(proxy, '127.0.0.1'), 422)
            self.assertEqual(post(proxy), 422)
            with app.state.authority.database.connect() as db:
                peer = hashlib.sha256(b'127.0.0.1').hexdigest()
                self.assertEqual(db.execute('SELECT requests FROM identity_rate_windows WHERE bucket=?', ('challenge/source/' + peer,)).fetchone()[0], 3)
        # Only the local proxy may set the address: a remote peer is never trusted.
        with TestClient(app, raise_server_exceptions=False, client=('198.51.100.9', 50000)) as remote:
            for _ in range(60):
                self.assertEqual(post(remote, '203.0.113.200'), 422)
            self.assertEqual(post(remote, '203.0.113.201'), 429)

    def test_07_consumed_refresh_new_request_revokes_family_durably(self):
        first, _ = self.signup()
        second, _ = self.rotate()
        reused = self.base(refreshToken=self.refresh, replacementToken=secret())
        response = self.client.post('/v1/identity/session', json=self.signed(reused, 'session'))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'error': 'refresh_reuse_detected'})
        self.restart()
        self.assertEqual(self.client.get('/v1/wallet', headers=self.headers(first)).status_code, 401)
        self.assertEqual(self.client.get('/v1/wallet', headers=self.headers(second)).status_code, 401)
        with self.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT revoked FROM identity_sessions').fetchone()[0], 1)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_08_same_request_changed_payload_is_conflict(self):
        _, value = self.signup()
        changed = {**value, 'recoverySecret': secret()}
        self.assertEqual(self.client.post('/v1/identity/guest', json=self.signed(changed, 'guest')).status_code, 409)
        self.assertEqual(self.count('players'), 1)
        self.assertEqual(self.count('identity_sessions'), 1)

    def test_09_concurrent_exact_refresh_is_one_rotation(self):
        first, _ = self.signup()
        value = self.base(refreshToken=self.refresh, replacementToken=secret())
        requests = [self.signed(value, 'session') for _ in range(2)]
        barrier = threading.Barrier(2)
        def send(body):
            with TestClient(self.app, raise_server_exceptions=False) as client:
                barrier.wait(timeout=10)
                return client.post('/v1/identity/session', json=body)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(send, requests))
        values = [self.ok(response) for response in responses]
        self.assertEqual(sorted(v['replayed'] for v in values), [False, True])
        self.assertTrue(all(v['familyId'] == first['familyId'] for v in values))
        self.assertEqual(self.count('identity_refresh'), 2)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_10_concurrent_different_refresh_requests_fail_closed(self):
        first, _ = self.signup()
        requests = [self.signed(self.base(refreshToken=self.refresh, replacementToken=secret()), 'session') for _ in range(2)]
        barrier = threading.Barrier(2)
        def send(body):
            with TestClient(self.app, raise_server_exceptions=False) as client:
                barrier.wait(timeout=10)
                return client.post('/v1/identity/session', json=body)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(send, requests))
        self.assertEqual(sorted(v.status_code for v in responses), [200, 401])
        for response in responses:
            if response.status_code == 200:
                self.assertEqual(self.client.get('/v1/wallet', headers=self.headers(response.json())).status_code, 401)
        self.assertEqual(self.client.get('/v1/wallet', headers=self.headers(first)).status_code, 401)

    def test_11_recovery_rotates_secret_and_key_without_regrant(self):
        first, _ = self.signup()
        wallet = self.wallet(first)
        key = ECC.generate(curve='P-256')
        value = self.recovery_body(first, key)
        recovered = self.ok(self.client.post('/v1/identity/recover', json=self.signed(value, 'recover', key)))
        self.assertEqual(recovered['playerId'], first['playerId'])
        self.assertNotEqual(recovered['familyId'], first['familyId'])
        self.assertNotEqual(recovered['keyFingerprint'], first['keyFingerprint'])
        self.assertEqual(self.wallet(recovered), wallet)
        self.assertEqual(self.client.get('/v1/wallet', headers=self.headers(first)).status_code, 401)
        old = self.base(refreshToken=self.refresh, replacementToken=secret())
        self.assertEqual(self.client.post('/v1/identity/session', json=self.signed(old, 'session')).status_code, 401)
        self.restart()
        retry = self.ok(self.client.post('/v1/identity/recover', json=self.signed(value, 'recover', key)))
        self.assertEqual(retry['familyId'], recovered['familyId'])
        self.assertTrue(retry['replayed'])
        self.assertEqual(self.count('wallet_ledger'), 1)
        old_secret = self.recovery_body(first, ECC.generate(curve='P-256'))
        other_key = ECC.generate(curve='P-256')
        old_secret['publicKey'] = public(other_key)
        self.assertEqual(self.client.post('/v1/identity/recover', json=self.signed(old_secret, 'recover', other_key)).status_code, 401)

    def test_12_recovery_wrong_secret_or_existing_key_cannot_take_account(self):
        first, _ = self.signup()
        key = ECC.generate(curve='P-256')
        value = self.recovery_body(first, key)
        value['recoverySecret'] = secret()
        self.assertEqual(self.client.post('/v1/identity/recover', json=self.signed(value, 'recover', key)).status_code, 401)
        existing = self.recovery_body(first, self.key)
        self.assertEqual(self.client.post('/v1/identity/recover', json=self.signed(existing, 'recover')).status_code, 409)
        self.assertEqual(self.wallet(first)['coins'], 1250)

    def test_13_logout_exact_minimal_retry_survives_revocation(self):
        first, _ = self.signup()
        value = self.base(refreshToken=self.refresh)
        result = self.ok(self.client.post('/v1/identity/logout', json=self.signed(value, 'logout')))
        self.assertEqual(result['state'], 'LoggedOut')
        self.assertNotIn('accessToken', result)
        self.assertEqual(self.client.get('/v1/wallet', headers=self.headers(first)).status_code, 401)
        self.restart()
        retry = self.ok(self.client.post('/v1/identity/logout', json=self.signed(value, 'logout')))
        self.assertEqual(retry, result)
        new = self.base(refreshToken=self.refresh, replacementToken=secret())
        self.assertEqual(self.client.post('/v1/identity/session', json=self.signed(new, 'session')).status_code, 401)

    def test_14_deletion_revokes_erases_diagnostics_and_retains_audit(self):
        first, _ = self.signup()
        actor = self.app.state.authority.authenticate(first['accessToken'])
        verifier = self.app.state.authority.provision(first['playerId'], 'verifier')
        with self.app.state.authority.database.transaction() as db:
            db.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,'client_reported')", (first['playerId'], identifier(), 'a' * 64, '{}', self.now))
        value = self.deletion_body(first)
        deleted = self.ok(self.client.post('/v1/account/deletion', json=self.signed(value, 'delete')))
        self.assertEqual(deleted['state'], 'DeletionRequested')
        self.assertTrue(deleted['sessionsRevoked'])
        self.assertFalse(deleted['physicalPurgeComplete'])
        self.assertFalse(deleted['retentionPolicyConfigured'])
        self.assertIn('financial_audit_pending_policy', deleted['retainedClasses'])
        self.assertEqual(self.count('audit_events'), 0)
        self.assertEqual(self.count('identity_recovery'), 0)
        self.assertEqual(self.count('wallet_ledger'), 1)
        self.assertEqual(self.count('players'), 1)
        for token in (first['accessToken'], verifier['token']):
            with self.assertRaises(ServiceError):
                self.app.state.authority.authenticate(token, 'verifier' if token == verifier['token'] else 'player')
        with self.assertRaises(ServiceError):
            self.app.state.wallet.view(actor)
        with self.assertRaises(ServiceError):
            self.app.state.authority.account(actor)

    def test_15_deleted_guest_recovery_and_new_signup_cannot_restore_or_reset(self):
        first, _ = self.signup()
        value = self.deletion_body(first)
        deleted = self.ok(self.client.post('/v1/account/deletion', json=self.signed(value, 'delete')))
        self.restart()
        self.assertEqual(self.ok(self.client.post('/v1/account/deletion', json=self.signed(value, 'delete'))), deleted)
        self.assertEqual(self.client.post('/v1/identity/guest', json=self.signed(self.guest_body(), 'guest')).status_code, 410)
        key = ECC.generate(curve='P-256')
        request = self.recovery_body(first, key)
        self.assertEqual(self.client.post('/v1/identity/recover', json=self.signed(request, 'recover', key)).status_code, 410)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_16_deletion_key_and_refresh_must_both_belong_to_owner(self):
        first, _ = self.signup()
        key = ECC.generate(curve='P-256')
        wrong = {**self.deletion_body(first), 'publicKey': public(key)}
        self.assertEqual(self.client.post('/v1/account/deletion', json=self.signed(wrong, 'delete', key)).status_code, 401)
        wrong = self.deletion_body(first, secret())
        self.assertEqual(self.client.post('/v1/account/deletion', json=self.signed(wrong, 'delete')).status_code, 401)
        self.assertEqual(self.wallet(first)['coins'], 1250)

    def test_17_source_rate_limits_persist_failures_without_forwarded_header_trust(self):
        body = {'purpose': 'guest', 'requestId': identifier(), 'publicKey': '!' * 100, 'payloadDigest': '0' * 64}
        for index in range(60):
            response = self.client.post('/v1/identity/challenges', json=body, headers={'X-Forwarded-For': str(index)})
            self.assertEqual(response.status_code, 422)
        self.restart()
        self.assertEqual(self.client.post('/v1/identity/challenges', json=body).status_code, 429)
        self.now += 60
        self.assertEqual(self.client.post('/v1/identity/challenges', json=body).status_code, 422)
        with self.app.state.authority.database.connect() as db:
            stored = '\n'.join(db.iterdump())
        self.assertNotIn('testclient', stored)

    def test_18_outstanding_capacity_and_expired_challenge_cleanup(self):
        with self.app.state.authority.database.transaction() as db:
            for _ in range(MAX_OUTSTANDING_CHALLENGES):
                db.execute('INSERT INTO identity_challenges VALUES(?,?,?,?,?,?,?,?,0)',
                           (identifier(), 'guest', 'a' * 64, public(self.key), identifier(), '0' * 64, secret(), self.now + 60))
        body = {'purpose': 'guest', 'requestId': identifier(), 'publicKey': public(self.key), 'payloadDigest': '0' * 64}
        self.assertEqual(self.client.post('/v1/identity/challenges', json=body).status_code, 503)
        self.now += 60
        self.ok(self.client.post('/v1/identity/challenges', json=body))
        self.assertEqual(self.count('identity_challenges'), 1)

    def test_19_signed_device_key_revives_idle_and_absolute_lapse(self):
        # Review 136, owner decision: age alone never ends a session held by its registered key.
        first, _ = self.signup()
        family, token = first['familyId'], self.refresh
        self.now += 30 * 86400
        value = self.base(refreshToken=token, replacementToken=secret())
        revived = self.ok(self.client.post('/v1/identity/session', json=self.signed(value, 'session')))
        self.assertEqual((revived['familyId'], revived['playerId']), (family, first['playerId']))
        token = value['replacementToken']
        for _ in range(4):  # Beyond the old 90-day absolute limit, renewing regularly.
            self.now += 29 * 86400
            value = self.base(refreshToken=token, replacementToken=secret())
            rotated = self.ok(self.client.post('/v1/identity/session', json=self.signed(value, 'session')))
            token = value['replacementToken']
            self.assertEqual(rotated['familyId'], family)
            self.assertLessEqual(rotated['refreshExpiresAt'], self.now + SESSION_MAX_SECONDS + 60)
            self.assertGreaterEqual(rotated['refreshExpiresAt'], rotated['expiresAt'])
        self.now += SESSION_MAX_SECONDS + 86400
        value = self.base(refreshToken=token, replacementToken=secret())
        self.assertEqual(self.ok(self.client.post('/v1/identity/session', json=self.signed(value, 'session')))['familyId'], family)
        with self.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM wallet_ledger').fetchone()[0], 1)

    def test_19b_lapse_never_revives_a_used_token_or_another_key(self):
        self.signup()
        old = self.refresh
        value = self.base(refreshToken=old, replacementToken=secret())
        self.ok(self.client.post('/v1/identity/session', json=self.signed(value, 'session')))
        current = value['replacementToken']
        self.now += SESSION_MAX_SECONDS + 1
        # An old token after the lapse: refused without revoking the player's real session.
        value = self.base(refreshToken=old, replacementToken=secret())
        response = self.client.post('/v1/identity/session', json=self.signed(value, 'session'))
        self.assertEqual((response.status_code, response.json()['error']), (401, 'invalid_identity_session'))
        # The current token under a different device key.
        other = ECC.generate(curve='P-256')
        value = self.base(other, refreshToken=current, replacementToken=secret())
        self.assertEqual(self.client.post('/v1/identity/session', json=self.signed(value, 'session', other)).status_code, 401)
        # The real device still renews.
        value = self.base(refreshToken=current, replacementToken=secret())
        self.ok(self.client.post('/v1/identity/session', json=self.signed(value, 'session')))

    def test_19c_unlapsed_reuse_still_revokes_and_lapse_cannot_undo_revocation(self):
        self.signup()
        old = self.refresh
        value = self.base(refreshToken=old, replacementToken=secret())
        self.ok(self.client.post('/v1/identity/session', json=self.signed(value, 'session')))
        current = value['replacementToken']
        value = self.base(refreshToken=old, replacementToken=secret())
        response = self.client.post('/v1/identity/session', json=self.signed(value, 'session'))
        self.assertEqual((response.status_code, response.json()['error']), (401, 'refresh_reuse_detected'))
        self.now += SESSION_MAX_SECONDS + 1
        value = self.base(refreshToken=current, replacementToken=secret())
        self.assertEqual(self.client.post('/v1/identity/session', json=self.signed(value, 'session')).status_code, 401)

    def test_19d_recovery_elsewhere_and_deletion_stay_final_after_lapse(self):
        first, _ = self.signup()
        token = self.refresh
        key = ECC.generate(curve='P-256')
        self.ok(self.client.post('/v1/identity/recover', json=self.signed(self.recovery_body(first, key), 'recover', key)))
        self.now += SESSION_MAX_SECONDS + 1
        value = self.base(refreshToken=token, replacementToken=secret())
        self.assertEqual(self.client.post('/v1/identity/session', json=self.signed(value, 'session')).status_code, 401)

    def test_19e_lost_renewal_reply_replays_after_lapse_with_the_same_family(self):
        first, _ = self.signup()
        value = self.base(refreshToken=self.refresh, replacementToken=secret())
        signed = self.signed(value, 'session')
        answered = self.ok(self.client.post('/v1/identity/session', json=signed))
        self.now += SESSION_MAX_SECONDS + 1
        again = self.ok(self.client.post('/v1/identity/session', json=self.signed(value, 'session')))
        self.assertEqual((again['familyId'], again['replayed']), (answered['familyId'], True))
        self.assertGreater(again['expiresAt'], self.now)

    def test_19f_renewal_challenge_skips_the_global_budget_for_a_registered_device(self):
        self.signup()
        body = {'purpose': 'session', 'requestId': identifier(), 'publicKey': public(self.key), 'payloadDigest': '0' * 64}
        from hotr_backend import identity as module
        original = module.CHALLENGES_GLOBAL
        module.CHALLENGES_GLOBAL = 0
        try:
            self.ok(self.client.post('/v1/identity/challenges', json=body))
            unknown = dict(body, publicKey=public(ECC.generate(curve='P-256')), requestId=identifier())
            refused = self.client.post('/v1/identity/challenges', json=unknown)
            self.assertEqual((refused.status_code, refused.headers['Retry-After']), (429, '30'))
        finally:
            module.CHALLENGES_GLOBAL = original

    def test_20_guest_before_and_after_commit_faults_are_recoverable(self):
        value = self.guest_body()
        def fail_before(stage):
            if stage == 'BeforeCommit':
                raise RuntimeError('controlled precommit fault')
        self.app.state.identity.checkpoint = fail_before
        self.assertEqual(self.client.post('/v1/identity/guest', json=self.signed(value, 'guest')).status_code, 500)
        self.assertEqual(self.count('players'), 0)
        self.assertEqual(self.count('wallet_ledger'), 0)
        def fail_after(stage):
            if stage == 'AfterCommit':
                raise RuntimeError('controlled postcommit reply loss')
        self.app.state.identity.checkpoint = fail_after
        self.assertEqual(self.client.post('/v1/identity/guest', json=self.signed(value, 'guest')).status_code, 500)
        self.assertEqual(self.count('players'), 1)
        self.restart()
        response = self.ok(self.client.post('/v1/identity/guest', json=self.signed(value, 'guest')))
        self.assertTrue(response['replayed'])
        self.assertEqual(self.wallet(response)['coins'], 1250)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_21_refresh_and_recovery_lost_replies_preserve_exact_successors(self):
        first, _ = self.signup()
        def lost(stage):
            if stage == 'AfterCommit':
                raise RuntimeError('controlled lost response')
        self.app.state.identity.checkpoint = lost
        value = self.base(refreshToken=self.refresh, replacementToken=secret())
        self.assertEqual(self.client.post('/v1/identity/session', json=self.signed(value, 'session')).status_code, 500)
        self.restart()
        rotated = self.ok(self.client.post('/v1/identity/session', json=self.signed(value, 'session')))
        self.assertEqual(rotated['familyId'], first['familyId'])
        key = ECC.generate(curve='P-256')
        body = self.recovery_body(first, key)
        self.app.state.identity.checkpoint = lost
        self.assertEqual(self.client.post('/v1/identity/recover', json=self.signed(body, 'recover', key)).status_code, 500)
        self.restart()
        recovered = self.ok(self.client.post('/v1/identity/recover', json=self.signed(body, 'recover', key)))
        self.assertEqual(recovered['playerId'], first['playerId'])
        self.assertTrue(recovered['replayed'])
        self.assertEqual(self.wallet(recovered)['coins'], 1250)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_22_deletion_lost_reply_returns_retention_receipt_after_restart(self):
        first, _ = self.signup()
        body = self.deletion_body(first)
        def lost(stage):
            if stage == 'AfterCommit':
                raise RuntimeError('controlled lost response')
        self.app.state.identity.checkpoint = lost
        self.assertEqual(self.client.post('/v1/account/deletion', json=self.signed(body, 'delete')).status_code, 500)
        self.restart()
        deleted = self.ok(self.client.post('/v1/account/deletion', json=self.signed(body, 'delete')))
        self.assertEqual(deleted['state'], 'DeletionRequested')
        self.assertEqual(self.client.get('/v1/wallet', headers=self.headers(first)).status_code, 401)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_23_recovery_vs_deletion_serializes_ownership(self):
        first, _ = self.signup()
        key = ECC.generate(curve='P-256')
        recovery = self.signed(self.recovery_body(first, key), 'recover', key)
        deletion = self.signed(self.deletion_body(first), 'delete')
        barrier = threading.Barrier(2)
        def send(item):
            with TestClient(self.app, raise_server_exceptions=False) as client:
                barrier.wait(timeout=10)
                return client.post(item[0], json=item[1])
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(send, [('/v1/identity/recover', recovery), ('/v1/account/deletion', deletion)]))
        if responses[0].status_code == 200:
            self.assertEqual(responses[1].status_code, 401)  # Recovery revoked the old deletion key/session.
        else:
            self.assertEqual((responses[0].status_code, responses[1].status_code), (410, 200))
        with self.app.state.authority.database.connect() as db:
            state = db.execute('SELECT state FROM account_states').fetchone()[0]
        self.assertEqual(state, 'Active' if responses[0].status_code == 200 else 'DeletionRequested')
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_24_access_role_and_unknown_fields_never_authorize_verifier(self):
        response, _ = self.signup()
        body = {'attemptId': identifier(), 'level': 1, 'proofDigest': 'a' * 64}
        self.assertEqual(self.client.post('/internal/v1/verified-first-clear', json=body, headers=self.headers(response)).status_code, 403)
        forged = {**self.signed(self.base(refreshToken=self.refresh, replacementToken=secret()), 'session'), 'role': 'verifier'}
        self.assertEqual(self.client.post('/v1/identity/session', json=forged).status_code, 422)
        self.assertEqual(self.wallet(response)['completed'], 0)

    def test_25_authenticated_actor_and_cached_wallet_command_cannot_cross_deletion(self):
        first, _ = self.signup()
        actor = self.app.state.authority.authenticate(first['accessToken'])
        reserve = ReserveAttempt(commandId=identifier(), expectedRevision=1, level=1, starting=[0] * 4)
        self.app.state.wallet.reserve(actor, reserve)
        body = self.deletion_body(first)
        self.ok(self.client.post('/v1/account/deletion', json=self.signed(body, 'delete')))
        for action in (lambda: self.app.state.wallet.reserve(actor, reserve),
                       lambda: self.app.state.wallet.ledger(actor),
                       lambda: self.app.state.authority.rewards(actor),
                       lambda: self.app.state.authority.daily_offer(actor)):
            with self.assertRaises(ServiceError) as error:
                action()
            self.assertEqual(error.exception.status, 410)
        self.assertEqual(self.count('wallet_ledger'), 2)
        with self.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT state FROM gameplay_attempts').fetchone()[0], 'Reserved')

    def test_26_late_provider_confirmation_after_deletion_never_credits(self):
        entered, release = threading.Event(), threading.Event()
        class Provider:
            configured = True
            value = None
            def lookup(self, invoice_id, sandbox):
                entered.set()
                if not release.wait(timeout=15):
                    raise RuntimeError('controlled provider hold timed out')
                return self.value
        provider = Provider()
        configuration = Path(self.temp.name) / 'commerce.json'
        configuration.write_text(json.dumps({'version': 'synthetic-deletion-race', 'enabled': True,
            'appId': 123, 'sandbox': True, 'products': [{'id': 'fixture', 'storeProductId': 'synthetic_1000',
            'enabled': True, 'coins': 1000, 'amountMinor': 9900, 'currency': 'RUB'}]}), encoding='utf-8')
        self.client.close()
        self.app = create_app(self.path, CONFIG, lambda: self.now, identity_enabled=True,
                              commerce_provider=provider, commerce_config_path=configuration)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        first, _ = self.signup()
        order = self.ok(self.client.post('/v1/commerce/orders', headers=self.headers(first),
                                        json={'commandId': identifier(), 'productId': 'fixture'}))
        provider.value = VerifiedInvoice('8100001', str(uuid.uuid4()), 123, True, order['orderId'],
            order['sdk']['productId'], order['playerId'], order['sdk']['developerPayload'],
            order['amountMinor'], order['currency'], 'CONFIRMED', 'PENDING')
        def reconcile():
            with TestClient(self.app, raise_server_exceptions=False) as client:
                return client.post('/v1/commerce/orders/' + order['orderId'] + '/reconcile',
                                   headers=self.headers(first), json={'invoiceId': '8100001'})
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(reconcile)
            try:
                self.assertTrue(entered.wait(timeout=10))
                body = self.deletion_body(first)
                self.ok(self.client.post('/v1/account/deletion', json=self.signed(body, 'delete')))
            finally:
                release.set()
            response = pending.result(timeout=10)
        self.assertEqual(response.status_code, 410)
        self.assertEqual(self.count('commerce_orders'), 1)  # Restricted audit is retained.
        self.assertEqual(self.count('commerce_credits'), 0)
        self.assertEqual(self.count('wallet_ledger'), 1)
        self.assertEqual(self.count('commerce_delivery_ack'), 0)

    def test_27_consumed_recovery_secret_cannot_seed_a_second_account(self):
        first, _ = self.signup()
        key = ECC.generate(curve='P-256')
        request = self.recovery_body(first, key)
        self.ok(self.client.post('/v1/identity/recover', json=self.signed(request, 'recover', key)))
        other = ECC.generate(curve='P-256')
        guest = self.base(other, refreshToken=secret(), recoverySecret=self.recovery)
        response = self.client.post('/v1/identity/guest', json=self.signed(guest, 'guest', other))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {'error': 'identity_secret_conflict'})
        self.assertEqual(self.count('players'), 1)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def identity_state_hash(self):
        # Hash state rather than returning credentials/digests in failure logs.
        tables = ('players', 'wallets', 'wallet_ledger', 'account_states', 'credentials',
                  'identity_devices', 'identity_recovery', 'identity_sessions', 'identity_refresh',
                  'identity_access', 'identity_recovery_history', 'identity_operations', 'identity_challenges')
        with self.app.state.authority.database.connect() as db:
            value = {name: sorted(canonical(dict(row)) for row in db.execute('SELECT * FROM ' + name))
                     for name in tables}
        return digest(canonical(value))

    def queued_identity_request(self, path, signed, advance):
        identity = self.app.state.identity
        original = identity._transaction
        def delayed(operation):
            advance()
            return original(operation)
        identity._transaction = delayed
        try:
            return self.client.post(path, json=signed)
        finally:
            identity._transaction = original

    def test_28_persisted_clock_advancing_after_start_expires_proof_without_duplicate_genesis(self):
        value = self.guest_body()
        signed = self.signed(value, 'guest')
        before = self.identity_state_hash()
        def advance():
            self.now += 60
            self.app.state.authority._now()
            self.now -= 60  # A backward wall-clock jump cannot undo high-water.
        response = self.queued_identity_request('/v1/identity/guest', signed, advance)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'error': 'invalid_identity_proof'})
        self.assertEqual(self.identity_state_hash(), before)
        self.now += 60
        recovered = self.ok(self.client.post('/v1/identity/guest', json=self.signed(value, 'guest')))
        self.assertFalse(recovered['replayed'])
        retry = self.ok(self.client.post('/v1/identity/guest', json=self.signed(value, 'guest')))
        self.assertTrue(retry['replayed'])
        self.assertEqual(retry['playerId'], recovered['playerId'])
        self.assertEqual(self.count('players'), 1)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_29_refresh_expiring_between_start_and_transaction_still_renews_once(self):
        first, _ = self.signup()
        self.now += 30 * 86400 - 1
        value = self.base(refreshToken=self.refresh, replacementToken=secret())
        signed = self.signed(value, 'session')
        response = self.queued_identity_request('/v1/identity/session', signed, lambda: setattr(self, 'now', self.now + 1))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['familyId'], first['familyId'])
        self.assertEqual(self.count('identity_sessions'), 1)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_30_recovery_queued_past_proof_expiry_cannot_revoke_original_account(self):
        first, _ = self.signup()
        key = ECC.generate(curve='P-256')
        value = self.recovery_body(first, key)
        signed = self.signed(value, 'recover', key)
        before = self.identity_state_hash()
        response = self.queued_identity_request('/v1/identity/recover', signed, lambda: setattr(self, 'now', self.now + 60))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'error': 'invalid_identity_proof'})
        self.assertEqual(self.identity_state_hash(), before)
        self.assertEqual(self.wallet(first)['coins'], 1250)
        recovered = self.ok(self.client.post('/v1/identity/recover', json=self.signed(value, 'recover', key)))
        self.assertEqual(recovered['playerId'], first['playerId'])
        self.assertEqual(self.wallet(recovered)['coins'], 1250)
        self.assertEqual(self.count('players'), 1)
        self.assertEqual(self.count('wallet_ledger'), 1)

    def test_31_clock_failure_inside_proof_transaction_rolls_back_but_keeps_rate_budget(self):
        authority = self.app.state.authority
        original_clock = authority.clock
        def unavailable():
            raise OSError('controlled-clock-failure')
        for clock in (lambda: -1, lambda: 253_402_300_800, lambda: float('nan'), unavailable):
            with self.subTest(clockFailure=True):
                value = self.guest_body()
                signed = self.signed(value, 'guest')
                before = self.identity_state_hash()
                with authority.database.connect() as db:
                    count = db.execute("SELECT COALESCE(SUM(requests),0) FROM identity_rate_windows WHERE bucket='operation/global'").fetchone()[0]
                try:
                    response = self.queued_identity_request('/v1/identity/guest', signed, lambda: setattr(authority, 'clock', clock))
                finally:
                    authority.clock = original_clock
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {'error': 'clock_unavailable'})
                self.assertEqual(self.identity_state_hash(), before)
                with authority.database.connect() as db:
                    self.assertEqual(db.execute("SELECT SUM(requests) FROM identity_rate_windows WHERE bucket='operation/global'").fetchone()[0], count + 1)
        self.assertEqual(self.count('players'), 0)
        self.assertEqual(self.count('wallet_ledger'), 0)

    def test_32_real_held_writer_without_other_clock_request_cannot_extend_signed_proof(self):
        value = self.guest_body()
        signed = self.signed(value, 'guest')
        before = self.identity_state_hash()
        identity = self.app.state.identity
        original = identity._transaction
        entered, held, attempting, release = (threading.Event() for _ in range(4))
        def queued(operation):
            entered.set()
            if not held.wait(3):
                raise RuntimeError('writer-fixture-not-ready')
            attempting.set()
            return original(operation)
        def hold_writer():
            if not entered.wait(3):
                raise RuntimeError('identity-fixture-not-ready')
            with self.app.state.authority.database.transaction() as db:
                db.execute('UPDATE clock_state SET high_water=high_water WHERE id=1')
                held.set()
                if not release.wait(3):
                    raise RuntimeError('writer-fixture-release-timeout')
        identity._transaction = queued
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                writer = pool.submit(hold_writer)
                request = pool.submit(self.client.post, '/v1/identity/guest', json=signed)
                try:
                    self.assertTrue(attempting.wait(3))
                    self.assertFalse(request.done())
                    self.now += 60  # No authority._now call updates high-water here.
                finally:
                    release.set()
                writer.result(timeout=4)
                response = request.result(timeout=4)
        finally:
            release.set()
            identity._transaction = original
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'error': 'invalid_identity_proof'})
        self.assertEqual(self.identity_state_hash(), before)
        self.assertEqual(self.count('players'), 0)

    def test_33_positive_last_valid_second_and_retry_use_fresh_commit_time(self):
        value = self.guest_body()
        signed = self.signed(value, 'guest')
        response = self.queued_identity_request('/v1/identity/guest', signed, lambda: setattr(self, 'now', self.now + 59))
        first = self.ok(response)
        self.assertEqual(first['expiresAt'], self.now + 900)
        self.assertEqual(first['refreshExpiresAt'], self.now + 30 * 86400)
        retried = self.ok(self.client.post('/v1/identity/guest', json=self.signed(value, 'guest')))
        self.assertTrue(retried['replayed'])
        self.assertEqual(first['playerId'], retried['playerId'])
        self.assertEqual(self.count('players'), 1)
        self.assertEqual(self.count('identity_sessions'), 1)
        self.assertEqual(self.count('wallet_ledger'), 1)


if __name__ == '__main__':
    unittest.main()
