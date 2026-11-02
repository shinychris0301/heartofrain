"""Actual FastAPI/SQLite/device-signature tests with explicitly simulated VK HTTP.

No real VK account, external request, token logging or native/device acceptance.
"""
import base64
import concurrent.futures
import hashlib
import json
import secrets
import sqlite3
import threading
import unittest
import uuid
from contextlib import closing
from unittest.mock import patch

from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from fastapi.testclient import TestClient

from tests import test_provider_identity89 as fixtures
from hotr_backend.api import create_app
from hotr_backend.identity import PROTOCOL
from hotr_backend.operations import _expected, backup_database, restore_database
from hotr_backend.provider_signin_schema102 import PROVIDER_SIGNIN_V10_DDL
from hotr_backend.storage import Database, SCHEMA_VERSION


def sha(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def public(key):
    return base64.b64encode(key.public_key().export_key(format='DER')).decode('ascii')


class VkSignin102Tests(unittest.TestCase):
    tearDown = fixtures.ProviderIdentity89Tests.tearDown
    provider_http = fixtures.ProviderIdentity89Tests.provider_http
    ok = fixtures.ProviderIdentity89Tests.ok
    callback = fixtures.ProviderIdentity89Tests.callback
    signed_identity = fixtures.ProviderIdentity89Tests.signed_identity
    managed_guest = fixtures.ProviderIdentity89Tests.managed_guest

    def setUp(self):
        fixtures.ProviderIdentity89Tests.setUp(self)
        self.source_key, self.source_public, self.source_refresh = self.managed_guest()
        self.source = dict(self.account)

    def flow(self, **overrides):
        key, proof = ECC.generate(curve='P-256'), secrets.token_urlsafe(32)
        body = dict(requestId=uuid.uuid4().hex, publicKey=public(key), completionDigest=sha(proof))
        body.update(overrides)
        value = self.ok(self.client.post('/v1/identity/vk/signin', headers=self.headers, json=body))
        return dict(value=value, key=key, secret=proof, refresh=secrets.token_urlsafe(32), body=body)

    def status(self, flow, headers=None):
        return self.client.get('/v1/identity/vk/signin/' + flow['value']['flowId'], headers=headers or self.headers)

    def ready(self, flow):
        self.assertEqual(self.callback(flow['value']).status_code, 200)
        value = self.ok(self.status(flow))
        self.assertEqual(value['phase'], 'Ready')
        flow['target'] = value['targetPlayerId']
        return value

    def sign(self, body, purpose, key):
        # Independent wire binding, not production request_payload().
        payload = {name: body[name] for name in ('requestId', 'publicKey')}
        payload.update(protocol=PROTOCOL, purpose=purpose, refreshDigest=sha(body['refreshToken']))
        if purpose == 'vk':
            payload.update(flowId=body['flowId'], targetPlayerId=body['targetPlayerId'],
                           flowDigest=sha(body['flowSecret']), confirmed='true' if body['confirmed'] else 'false')
        elif purpose == 'session':
            payload['replacementDigest'] = sha(body['replacementToken'])
        elif purpose == 'delete':
            payload['playerId'] = body['playerId']
        digest = sha(json.dumps(payload, sort_keys=True, separators=(',', ':')))
        challenge = self.ok(self.client.post('/v1/identity/challenges', json=dict(
            purpose=purpose, requestId=body['requestId'], publicKey=body['publicKey'], payloadDigest=digest)))
        self.assertEqual(challenge['payloadDigest'], digest)
        signature = DSS.new(key, 'fips-186-3', encoding='der').sign(SHA256.new(base64.b64decode(challenge['signingBytes'])))
        return dict(body, challengeId=challenge['challengeId'], signature=base64.b64encode(signature).decode())

    def completion(self, flow, **overrides):
        body = dict(requestId=flow['value']['requestId'], publicKey=public(flow['key']),
                    flowId=flow['value']['flowId'], targetPlayerId=flow.get('target', self.account['playerId']),
                    flowSecret=flow['secret'], refreshToken=flow['refresh'], confirmed=True)
        body.update(overrides)
        return self.sign(body, 'vk', flow['key'])

    def complete(self, flow, **overrides):
        return self.client.post('/v1/identity/vk/complete', json=self.completion(flow, **overrides))

    def financial(self):
        with self.app.state.authority.database.connect() as db:
            return {name: [tuple(r) for r in db.execute('SELECT * FROM ' + name + ' ORDER BY rowid')]
                    for name in ('players','wallets','wallet_ledger','rewards','gameplay_attempts','identity_recovery')}

    def family_count(self):
        with self.app.state.authority.database.connect() as db:
            return db.execute('SELECT COUNT(*) FROM identity_sessions').fetchone()[0]

    def source_logout(self):
        value = self.sign(dict(requestId=uuid.uuid4().hex, publicKey=self.source_public,
                               refreshToken=self.source_refresh), 'logout', self.source_key)
        return self.client.post('/v1/identity/logout', headers=self.headers, json=value)

    def cancel(self, flow):
        return self.client.post('/v1/identity/vk/signin/' + flow['value']['flowId'] + '/cancel', headers=self.headers)

    def test_registration_requires_signed_explicit_completion_and_preserves_economy(self):
        before, families = self.financial(), self.family_count()
        flow = self.flow()
        self.assertEqual(flow['value']['flowId'], flow['body']['requestId'])
        ready = self.ready(flow)
        self.assertEqual(ready['targetPlayerId'], self.source['playerId'])
        self.assertFalse(ready['requiresConfirmation'])
        self.assertEqual(self.family_count(), families)  # Browser never mints a game session.
        self.assertEqual(self.financial(), before)
        result = self.ok(self.complete(flow))
        self.assertEqual(result['playerId'], self.source['playerId'])
        self.assertEqual(result['keyFingerprint'], sha_bytes(base64.b64decode(public(flow['key']))))
        self.assertEqual(self.family_count(), families + 1)
        self.assertEqual(self.financial(), before)
        self.assertEqual(self.ok(self.status(flow))['phase'], 'Completed')
        with self.app.state.authority.database.connect() as db:
            link = db.execute('SELECT * FROM account_provider_links').fetchone()
            self.assertEqual(link['player_id'], self.source['playerId'])
            row = db.execute('SELECT * FROM account_provider_signins').fetchone()
            self.assertEqual((row['state_secret'], row['verifier']), ('',''))
            self.assertNotIn(flow['secret'], tuple(row))

    def test_unknown_provider_registers_only_at_commit_and_begin_is_idempotent(self):
        flow = self.flow()
        replay = self.ok(self.client.post('/v1/identity/vk/signin', headers=self.headers, json=flow['body']))
        self.assertEqual(replay, flow['value'])
        body = dict(flow['body'], completionDigest='a' * 64)
        self.assertEqual(self.client.post('/v1/identity/vk/signin', headers=self.headers, json=body).status_code, 409)
        self.ready(flow)
        with self.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM account_provider_links').fetchone()[0], 0)

    def test_existing_vk_restores_exact_target_without_merge_recovery_rotation_or_reward(self):
        first = self.flow(); self.ready(first); target = self.ok(self.complete(first))['playerId']
        self.managed_guest()  # A second device's independent managed guest.
        self.source = dict(self.account)
        before, families = self.financial(), self.family_count()
        second = self.flow(); ready = self.ready(second)
        self.assertEqual(ready['targetPlayerId'], target)
        self.assertTrue(ready['requiresConfirmation'])
        self.assertEqual(self.complete(second, confirmed=False).status_code, 422)
        self.assertEqual(self.complete(second, targetPlayerId=self.account['playerId']).status_code, 409)
        result = self.ok(self.complete(second))
        self.assertEqual(result['playerId'], target)
        self.assertEqual(self.family_count(), families + 1)
        self.assertEqual(self.financial(), before)

    def test_completion_proof_wrong_secret_key_target_and_tamper_cannot_adopt(self):
        flow = self.flow(); self.ready(flow)
        before = self.family_count()
        self.assertEqual(self.complete(flow, flowSecret=secrets.token_urlsafe(32)).status_code, 401)
        body = self.completion(flow)
        body['targetPlayerId'] = uuid.uuid4().hex
        self.assertEqual(self.client.post('/v1/identity/vk/complete', json=body).status_code, 401)
        body = self.completion(flow); body['publicKey'] = public(ECC.generate(curve='P-256'))
        self.assertEqual(self.client.post('/v1/identity/vk/complete', json=body).status_code, 401)
        self.assertEqual(self.family_count(), before)

    def test_completion_replay_after_expiry_and_restart_uses_exact_family_once(self):
        flow = self.flow(); self.ready(flow)
        families = self.family_count()
        first = self.ok(self.complete(flow))
        self.now += 601
        self.client.close()
        self.app = create_app(self.path, fixtures.CONFIG, lambda: self.now, identity_enabled=True,
                              vk_configuration=self.config, vk_provider=self.provider)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        replay = self.ok(self.complete(flow))
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['familyId'], first['familyId'])
        self.assertEqual(self.family_count(), families + 1)

    def test_after_commit_lost_response_reconciles_without_duplicate_family(self):
        flow = self.flow(); self.ready(flow)
        families = self.family_count()
        def fail(stage):
            if stage == 'AfterCommit':
                raise RuntimeError('Synthetic response loss')
        self.app.state.identity.checkpoint = fail
        self.assertEqual(self.complete(flow).status_code, 500)
        self.app.state.identity.checkpoint = None
        self.assertTrue(self.ok(self.complete(flow))['replayed'])
        self.assertEqual(self.family_count(), families + 1)

    def test_before_commit_failure_rolls_back_link_device_and_family(self):
        flow = self.flow(); self.ready(flow)
        families = self.family_count()
        def fail(stage):
            if stage == 'BeforeCommit':
                raise RuntimeError('Synthetic writer failure')
        self.app.state.identity.checkpoint = fail
        self.assertEqual(self.complete(flow).status_code, 500)
        self.assertEqual(self.family_count(), families)
        with self.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM account_provider_links').fetchone()[0], 0)
        self.app.state.identity.checkpoint = None
        self.ok(self.complete(flow))

    def test_cancelled_expired_or_unfinished_browser_flow_never_completes(self):
        flow = self.flow()
        self.assertEqual(self.complete(flow).status_code, 409)
        self.ready(flow); cancelled = self.ok(self.cancel(flow))
        self.assertEqual((cancelled['targetPlayerId'], cancelled['requiresConfirmation']), ('', False))
        self.assertEqual(self.complete(flow).status_code, 409)
        second = self.flow(); self.ready(second); self.now += 600
        self.assertEqual(self.complete(second).status_code, 409)
        expired = self.ok(self.status(second))
        self.assertEqual(expired['phase'], 'Expired')
        self.assertEqual((expired['targetPlayerId'], expired['requiresConfirmation']), ('', False))
        with self.app.state.authority.database.connect() as db:
            for row in db.execute('SELECT target_player,subject_digest FROM account_provider_signins'):
                self.assertEqual(tuple(row), (None, ''))

    def test_cancel_and_expiry_during_provider_exchange_discard_delayed_identity(self):
        for expires in (False, True):
            flow = self.flow()
            original = self.provider.verify
            def delayed(*args):
                if expires:
                    self.now += 600
                else:
                    self.ok(self.cancel(flow))
                return original(*args)
            with patch.object(self.provider, 'verify', delayed):
                self.assertEqual(self.callback(flow['value']).status_code, 200)
            self.assertEqual(self.ok(self.status(flow))['phase'], 'Expired' if expires else 'Cancelled')
            self.assertEqual(self.complete(flow).status_code, 409)

    def test_source_logout_before_callback_or_confirmation_fences_both(self):
        flow = self.flow(); self.ready(flow); self.ok(self.source_logout())
        self.assertEqual(self.complete(flow).status_code, 401)
        self.assertEqual(self.callback(flow['value']).status_code, 401)

    def test_source_logout_during_network_wait_cannot_commit_ready_target(self):
        flow = self.flow(); original = self.provider.verify
        def delayed(*args):
            self.ok(self.source_logout())
            return original(*args)
        with patch.object(self.provider, 'verify', delayed):
            self.assertEqual(self.callback(flow['value']).status_code, 401)
        self.assertEqual(self.family_count(), 1)

    def test_normal_access_refresh_preserves_source_flow_ownership(self):
        flow = self.flow()
        value = self.sign(dict(requestId=uuid.uuid4().hex, publicKey=self.source_public,
                               refreshToken=self.source_refresh, replacementToken=secrets.token_urlsafe(32)), 'session', self.source_key)
        result = self.ok(self.client.post('/v1/identity/session', json=value))
        self.headers = {'Authorization':'Bearer ' + result['accessToken']}
        self.ready(flow)
        self.ok(self.complete(flow))

    def test_different_account_and_family_cannot_read_or_cancel_flow(self):
        flow = self.flow()
        self.managed_guest()
        self.assertEqual(self.status(flow).status_code, 404)
        self.assertEqual(self.cancel(flow).status_code, 404)

    def test_concurrent_unknown_vk_registration_cannot_steal_or_silently_retarget(self):
        first = self.flow(); self.ready(first)
        self.managed_guest()
        second = self.flow(); self.ready(second)
        self.ok(self.complete(first))
        before = self.family_count()
        self.assertEqual(self.complete(second).status_code, 409)
        self.assertEqual(self.family_count(), before)
        status = self.ok(self.status(second))
        self.assertEqual((status['phase'], status['targetPlayerId'], status['requiresConfirmation']),
                         ('Conflict', '', False))

    def test_provider_callback_replay_never_creates_link_or_family(self):
        flow = self.flow(); self.ready(flow)
        count = len(self.calls)
        self.assertEqual(self.callback(flow['value']).status_code, 200)
        self.assertEqual(len(self.calls), count)
        self.assertEqual(self.family_count(), 1)

    def test_deleted_target_is_not_restored_or_retargeted_to_source(self):
        first = self.flow(); self.ready(first); target = self.ok(self.complete(first))
        target_headers = {'Authorization':'Bearer ' + target['accessToken']}
        self.managed_guest(); second = self.flow(); self.ready(second)
        value = self.sign(dict(requestId=uuid.uuid4().hex, publicKey=public(first['key']),
                               refreshToken=first['refresh'], playerId=target['playerId']), 'delete', first['key'])
        self.ok(self.client.post('/v1/account/deletion', headers=target_headers, json=value))
        self.assertIn(self.complete(second).status_code, (401,409))
        status = self.ok(self.status(second))
        self.assertEqual((status['phase'], status['targetPlayerId'], status['requiresConfirmation']),
                         ('Cancelled', '', False))
        with self.app.state.authority.database.connect() as db:
            self.assertFalse(db.execute('SELECT 1 FROM account_provider_signins WHERE target_player=?', (target['playerId'],)).fetchone())
            row = db.execute('SELECT * FROM account_provider_signins WHERE id=?', (second['value']['flowId'],)).fetchone()
            self.assertEqual((row['subject_digest'], row['state_secret'], row['verifier']), ('', '', ''))

    def test_committed_reply_loss_then_target_deletion_has_cleared_terminal_source_proof(self):
        first = self.flow(); self.ready(first); target = self.ok(self.complete(first))
        self.managed_guest(); second = self.flow(); self.ready(second)
        financial = self.financial(); financial.pop('identity_recovery')
        def lost(stage):
            if stage == 'AfterCommit':
                raise RuntimeError('Synthetic committed response loss')
        self.app.state.identity.checkpoint = lost
        self.assertEqual(self.complete(second).status_code, 500)
        self.app.state.identity.checkpoint = None
        self.assertEqual(self.ok(self.status(second))['phase'], 'Completed')
        deletion = self.sign(dict(requestId=uuid.uuid4().hex, publicKey=public(first['key']),
                                  refreshToken=first['refresh'], playerId=target['playerId']), 'delete', first['key'])
        self.ok(self.client.post('/v1/account/deletion', json=deletion))
        state = self.ok(self.status(second))
        self.assertEqual((state['phase'],state['targetPlayerId'],state['requiresConfirmation']), ('Failed','',False))
        self.assertEqual(self.complete(second).status_code, 401)
        after = self.financial(); after.pop('identity_recovery')
        self.assertEqual(after, financial)
        with self.app.state.authority.database.connect() as db:
            row = db.execute('SELECT * FROM account_provider_signins WHERE id=?', (second['value']['flowId'],)).fetchone()
            self.assertEqual((row['target_player'], row['subject_digest'], row['state_secret'], row['verifier']), (None,'','',''))
            self.assertTrue(db.execute("SELECT 1 FROM identity_operations WHERE purpose='vk' AND request_id=?", (second['value']['flowId'],)).fetchone())
            self.assertEqual(db.execute('SELECT state FROM account_states WHERE player_id=?', (self.account['playerId'],)).fetchone()[0], 'Active')

    def test_disabled_configuration_and_unmanaged_accounts_fail_closed(self):
        self.app.state.provider_signin.configuration = type(self.config)()
        response = self.client.post('/v1/identity/vk/signin', headers=self.headers, json=dict(
            requestId=uuid.uuid4().hex, publicKey=public(ECC.generate(curve='P-256')), completionDigest='a'*64))
        self.assertEqual(response.status_code, 503)
        self.app.state.provider_signin.configuration = self.config
        operator = self.app.state.authority.provision()
        response = self.client.post('/v1/identity/vk/signin', headers={'Authorization':'Bearer '+operator['token']}, json=dict(
            requestId=uuid.uuid4().hex, publicKey=public(ECC.generate(curve='P-256')), completionDigest='a'*64))
        self.assertEqual(response.status_code, 403)

    def test_fresh_key_required_and_confirmation_type_is_strict(self):
        self.assertEqual(self.client.post('/v1/identity/vk/signin', headers=self.headers, json=dict(
            requestId=uuid.uuid4().hex, publicKey=self.source_public, completionDigest='a'*64)).status_code, 409)
        flow = self.flow(); self.ready(flow)
        body = self.completion(flow); body['confirmed'] = 'true'
        self.assertEqual(self.client.post('/v1/identity/vk/complete', json=body).status_code, 422)

    def test_committed_completion_reconciles_when_provider_is_disabled_or_reconfigured(self):
        flow = self.flow(); self.ready(flow)
        result = self.ok(self.complete(flow)); count = self.family_count()
        self.app.state.provider_signin.configuration = type(self.config)()
        replay = self.ok(self.complete(flow))
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['familyId'], result['familyId'])
        self.app.state.provider_signin.configuration = type(self.config)(True, '99999', self.config.redirect_uri)
        replay = self.ok(self.complete(flow))
        self.assertEqual(replay['familyId'], result['familyId'])
        self.assertEqual(self.family_count(), count)

    def test_uncommitted_ready_configuration_change_is_authoritative_terminal(self):
        for disabled in (False, True):
            self.app.state.provider_signin.configuration = self.config
            flow = self.flow(); self.ready(flow)
            self.app.state.provider_signin.configuration = (type(self.config)() if disabled else
                                                            type(self.config)(True, '99999', self.config.redirect_uri))
            status = self.ok(self.status(flow))
            self.assertEqual((status['phase'], status['targetPlayerId'], status['requiresConfirmation']),
                             ('Failed', '', False))
            self.assertEqual(self.family_count(), 1)
            with self.app.state.authority.database.connect() as db:
                row = db.execute('SELECT * FROM account_provider_signins WHERE id=?', (flow['value']['flowId'],)).fetchone()
                self.assertEqual((row['subject_digest'], row['state_secret'], row['verifier'], row['target_player']), ('', '', '', None))

    def test_actual_parallel_completion_has_one_family_and_one_provider_link(self):
        flow = self.flow(); self.ready(flow)
        body = self.completion(flow)
        count, before = self.family_count(), self.financial()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            replies = list(pool.map(lambda _: self.client.post('/v1/identity/vk/complete', json=body), range(2)))
        values = [self.ok(reply) for reply in replies]
        self.assertEqual(len({value['familyId'] for value in values}), 1)
        self.assertEqual(sum(not value['replayed'] for value in values), 1)
        self.assertEqual(self.family_count(), count + 1)
        self.assertEqual(self.financial(), before)
        with self.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM account_provider_links').fetchone()[0], 1)

    def test_waiting_for_sqlite_writer_cannot_extend_ready_flow_expiry(self):
        flow = self.flow(); self.ready(flow)
        self.now += 590
        body = self.completion(flow)
        entered = threading.Event()
        original = self.app.state.identity._start
        def announce(*args, **kwargs):
            entered.set()
            return original(*args, **kwargs)
        with self.app.state.authority.database.connect() as writer:
            writer.execute('BEGIN IMMEDIATE')
            with patch.object(self.app.state.identity, '_start', announce):
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self.client.post, '/v1/identity/vk/complete', json=body)
                    self.assertTrue(entered.wait(5))
                    self.now += 11
                    writer.commit()
                    result = future.result(timeout=10)
        self.assertEqual(result.status_code, 409, result.text)
        self.assertEqual(self.family_count(), 1)

    def test_source_deletion_during_provider_exchange_clears_flow_and_cannot_register(self):
        flow = self.flow(); original = self.provider.verify
        value = self.sign(dict(requestId=uuid.uuid4().hex, publicKey=self.source_public,
                               refreshToken=self.source_refresh, playerId=self.source['playerId']), 'delete', self.source_key)
        def delayed(*args):
            self.ok(self.client.post('/v1/account/deletion', json=value))
            return original(*args)
        with patch.object(self.provider, 'verify', delayed):
            self.assertEqual(self.callback(flow['value']).status_code, 410)
        self.assertEqual(self.complete(flow).status_code, 401)
        with self.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM account_provider_signins').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM account_provider_links').fetchone()[0], 0)

    def test_revoking_completed_target_family_rejects_old_durable_completion(self):
        flow = self.flow(); self.ready(flow)
        result = self.ok(self.complete(flow))
        with self.app.state.authority.database.transaction() as db:
            self.app.state.identity._revoke_family(db, result['familyId'])
        self.assertEqual(self.complete(flow).status_code, 401)


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


class VkMigration102Tests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-vk102-migration-')
        self.root = Path(self.temp.name)
        self.path = self.root / 'legacy9.sqlite3'
        with closing(sqlite3.connect(self.path)) as db:
            for kind in ('table','index'):
                for typ, _, _, sql in _expected(9):
                    if typ == kind:
                        db.execute(sql)
            db.execute('INSERT INTO schema_info VALUES(9)')
            db.execute('INSERT INTO clock_state VALUES(1,0)')
            db.execute("INSERT INTO identity_challenges VALUES('old','guest','key','public','request','digest','nonce',9999999999,0)")
            db.commit()

    def tearDown(self):
        self.temp.cleanup()

    def test_atomic9_to10_preserves_pending_challenge_and_snapshot_restore(self):
        with Database(self.path).connect() as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], SCHEMA_VERSION)
            self.assertEqual(tuple(db.execute('SELECT * FROM identity_challenges').fetchone()),
                             ('old','guest','key','public','request','digest','nonce',9999999999,0))
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        snapshot, restored = self.root/'snapshot.sqlite3', self.root/'restored.sqlite3'
        self.assertEqual(backup_database(self.path, snapshot)['schemaVersion'], SCHEMA_VERSION)
        self.assertEqual(restore_database(snapshot, restored)['schemaVersion'], SCHEMA_VERSION)
        Database(restored)

    def test_failed10_migration_rolls_back_schema_challenge_and_index(self):
        with patch('hotr_backend.provider_signin_schema102.PROVIDER_SIGNIN_V10_DDL', PROVIDER_SIGNIN_V10_DDL + '\nINVALID MIGRATION;'):
            with self.assertRaises(sqlite3.Error):
                Database(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 9)
            self.assertEqual(db.execute('SELECT id FROM identity_challenges').fetchone()[0], 'old')
            self.assertTrue(db.execute("SELECT 1 FROM sqlite_master WHERE name='identity_challenge_expiry'").fetchone())
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='account_provider_signins'").fetchone())
        self.assertEqual(backup_database(self.path, self.root/'legacy.sqlite3')['schemaVersion'], 9)
        Database(self.path)


if __name__ == '__main__':
    unittest.main()
