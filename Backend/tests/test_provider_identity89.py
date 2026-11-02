"""Real HTTP/SQLite VK lifecycle; provider HTTP is an explicit deterministic fixture.

No test registers a real VK account, sends credentials externally or pretends a
mocked provider response is live VK authorization acceptance.
"""
import base64
import asyncio
import hashlib
import json
import tempfile
import secrets
import unittest
import uuid
import time
from unittest.mock import patch
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.provider_identity import ProviderLinkRequest
from hotr_backend.identity_schemas import DeletionRequest
from hotr_backend.service import ServiceError
from hotr_backend.vk_provider import VkConfiguration, VkProvider

CONFIG = Path(__file__).resolve().parents[1] / 'config'


class ProviderIdentity89Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-provider89-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 100 * 86400 + 1000
        self.config = VkConfiguration(True, '123456', 'https://game.example/v1/identity/vk/callback')
        self.calls, self.subject, self.token_error, self.user_error = [], '12345', '', ''
        self.provider = VkProvider(self.config, httpx.MockTransport(self.provider_http))
        self.app = create_app(self.path, CONFIG, lambda: self.now, identity_enabled=True,
                              vk_configuration=self.config, vk_provider=self.provider)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.account = self.app.state.authority.provision()
        self.headers = {'Authorization': 'Bearer ' + self.account['token']}

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def provider_http(self, request):
        # Inspect body in memory; nothing containing a provider token is logged.
        self.assertEqual(request.url.host, 'id.vk.ru')
        self.assertEqual(request.method, 'POST')
        self.assertNotIn('authorization', request.headers)
        form = parse_qs(request.content.decode())
        self.calls.append((request.url.path, form))
        self.assertEqual(form['client_id'], ['123456'])
        if request.url.path == '/oauth2/auth':
            self.assertEqual(form['redirect_uri'], [self.config.redirect_uri])
            self.assertEqual(form['grant_type'], ['authorization_code'])
            self.assertEqual(form['device_id'], ['browser-device'])
            self.assertEqual(form['code'], ['fixture-code'])
            if self.token_error == 'oauth':
                return httpx.Response(200, json={'error': 'invalid_grant'})
            return httpx.Response(200, json={'access_token': 'fixture-provider-only-token', 'state': 'é' if self.token_error == 'unicode' else 'wrong' if self.token_error == 'state' else form['state'][0], 'user_id': int(self.subject)})
        self.assertEqual(request.url.path, '/oauth2/user_info')
        self.assertEqual(form['access_token'], ['fixture-provider-only-token'])
        if self.user_error == 'redirect':
            return httpx.Response(302, headers={'Location': 'https://other.example/'})
        if self.user_error == 'oversized':
            return httpx.Response(200, headers={'Content-Type': 'application/json'}, content=b' ' * 32769)
        if self.user_error == 'type':
            return httpx.Response(200, headers={'Content-Type': 'text/html'}, content=b'{}')
        return httpx.Response(200, json={'user': {'user_id': '99999' if self.user_error == 'subject' else self.subject, 'first_name': 'discarded', 'email': 'never-retained@example.invalid'}})

    def ok(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def begin(self, request=None, headers=None):
        return self.ok(self.client.post('/v1/identity/vk/link', headers=headers or self.headers, json={'requestId': request or uuid.uuid4().hex}))

    def status(self, headers=None):
        return self.ok(self.client.get('/v1/identity/vk/status', headers=headers or self.headers))

    def callback(self, flow, **override):
        params = {key: values[0] for key, values in parse_qs(urlsplit(flow['authorizeUrl']).query).items()}
        return self.client.get('/v1/identity/vk/callback', params={'state': params['state'], 'code': 'fixture-code', 'device_id': 'browser-device', **override})

    def wallet_state(self):
        with self.app.state.authority.database.connect() as db:
            return [tuple(row) for row in db.execute('SELECT * FROM wallets ORDER BY player_id')], [tuple(row) for row in db.execute('SELECT * FROM wallet_ledger ORDER BY sequence')]

    def actor(self):
        return self.app.state.authority.authenticate(self.account['token'])

    def signed_identity(self, purpose, value, key):
        payload = {'protocol': 'hotr-managed-identity-v1', 'purpose': purpose, 'requestId': value['requestId'], 'publicKey': value['publicKey'],
                   'refreshDigest': hashlib.sha256(value['refreshToken'].encode()).hexdigest()}
        if purpose == 'guest':
            payload['recoveryDigest'] = hashlib.sha256(value['recoverySecret'].encode()).hexdigest()
        if purpose == 'delete':
            payload['playerId'] = value['playerId']
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
        challenge = self.ok(self.client.post('/v1/identity/challenges', json={
            'purpose': purpose, 'requestId': value['requestId'], 'publicKey': value['publicKey'], 'payloadDigest': digest}))
        signature = DSS.new(key, 'fips-186-3', encoding='der').sign(SHA256.new(base64.b64decode(challenge['signingBytes'])))
        return {**value, 'challengeId': challenge['challengeId'], 'signature': base64.b64encode(signature).decode()}

    def managed_guest(self):
        key, refresh = ECC.generate(curve='P-256'), secrets.token_urlsafe(32)
        public = base64.b64encode(key.public_key().export_key(format='DER')).decode()
        body = {'requestId': uuid.uuid4().hex, 'publicKey': public, 'refreshToken': refresh, 'recoverySecret': secrets.token_urlsafe(32)}
        session = self.ok(self.client.post('/v1/identity/guest', json=self.signed_identity('guest', body, key)))
        self.account = {'playerId': session['playerId'], 'token': session['accessToken']}
        self.headers = {'Authorization': 'Bearer ' + session['accessToken']}
        return key, public, refresh

    def test_01_default_disabled_and_explicit_public_configuration(self):
        app = create_app(Path(self.temp.name) / 'disabled.sqlite3', CONFIG, lambda: self.now)
        account = app.state.authority.provision()
        with TestClient(app, raise_server_exceptions=False) as client:
            headers = {'Authorization': 'Bearer ' + account['token']}
            state = self.ok(client.get('/v1/identity/vk/status', headers=headers))
            self.assertFalse(state['available'])
            response = client.post('/v1/identity/vk/link', headers=headers, json={'requestId': uuid.uuid4().hex})
            self.assertEqual(response.status_code, 503)
        for client, redirect in [('not-an-id', self.config.redirect_uri), ('123', 'http://example.com/v1/identity/vk/callback'), ('123', 'https://example.com/unregistered'), ('123', 'https://user@example.com/v1/identity/vk/callback'), ('123', self.config.redirect_uri + '?secret=1')]:
            with self.subTest(invalidConfiguration=True), self.assertRaises(ValueError):
                VkConfiguration(True, client, redirect)

    def test_02_begin_retry_has_one_flow_and_durable_same_authorize_url(self):
        before = self.wallet_state()
        request = uuid.uuid4().hex
        first, retry = self.begin(request), self.begin(request)
        self.assertEqual(first, retry)
        self.assertEqual(first['playerId'], self.account['playerId'])
        self.assertTrue(first['samePlayer'])
        self.assertEqual(first['expiresAt'], self.now + 600)
        parsed = parse_qs(urlsplit(first['authorizeUrl']).query, keep_blank_values=True)
        self.assertEqual(urlsplit(first['authorizeUrl']).hostname, 'id.vk.ru')
        self.assertEqual(parsed['code_challenge_method'], ['s256'])
        self.assertEqual(parsed['redirect_uri'], [self.config.redirect_uri])
        self.assertEqual(parsed['scope'], [''])
        self.assertEqual(self.wallet_state(), before)
        response = self.client.post('/v1/identity/vk/link', headers=self.headers, json={'requestId': uuid.uuid4().hex})
        self.assertEqual(response.status_code, 409)

    def test_03_callback_verifies_pkce_state_and_user_preserving_save(self):
        before = self.wallet_state()
        flow = self.begin()
        response = self.callback(flow)
        self.assertEqual(response.status_code, 200)
        self.assertIn('VK', response.text)
        self.assertIn("default-src 'none'", response.headers['content-security-policy'])
        self.assertEqual(response.headers['referrer-policy'], 'no-referrer')
        self.assertNotIn('fixture-code', response.text)
        self.assertNotIn('provider-only-token', response.text)
        status = self.status()
        self.assertTrue(status['linked'])
        self.assertEqual(status['phase'], 'Linked')
        self.assertEqual(status['playerId'], self.account['playerId'])
        verifier = self.calls[0][1]['code_verifier'][0]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        self.assertEqual(parse_qs(urlsplit(flow['authorizeUrl']).query)['code_challenge'], [challenge])
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.wallet_state(), before)
        with self.app.state.authority.database.connect() as db:
            row = db.execute('SELECT * FROM account_provider_flows').fetchone()
            self.assertEqual((row['state_secret'], row['verifier']), ('', ''))
            dump = '\n'.join(db.iterdump())
            self.assertNotIn('fixture-provider-only-token', dump)
            self.assertNotIn('never-retained', dump)
            self.assertNotIn('fixture-code', dump)

    def test_04_duplicate_callback_and_repeated_signup_never_relink(self):
        flow = self.begin()
        self.assertEqual(self.callback(flow).status_code, 200)
        self.assertEqual(self.callback(flow).status_code, 200)
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(self.begin()['linked'])
        self.assertEqual(self.status()['phase'], 'Linked')

    def test_05_cancel_and_delayed_callback_are_terminal(self):
        flow = self.begin()
        cancelled = self.ok(self.client.post('/v1/identity/vk/flows/' + flow['flowId'] + '/cancel', headers=self.headers))
        self.assertEqual(cancelled['phase'], 'Cancelled')
        self.assertEqual(self.callback(flow).status_code, 200)
        self.assertFalse(self.status()['linked'])
        self.assertEqual(self.calls, [])

    def test_06_expiry_is_exact_and_cannot_credit_after_network_wait(self):
        flow = self.begin()
        verify = self.provider.verify
        def delayed(*args):
            value = verify(*args)
            self.now += 600
            return value
        self.provider.verify = delayed
        self.assertEqual(self.callback(flow).status_code, 200)
        self.assertEqual(self.status()['phase'], 'Expired')
        self.assertFalse(self.status()['linked'])

    def test_07_expired_before_callback_does_not_contact_provider(self):
        flow = self.begin()
        self.now += 600
        self.assertEqual(self.callback(flow).status_code, 200)
        self.assertEqual(self.status()['phase'], 'Expired')
        self.assertEqual(self.calls, [])

    def test_08_wrong_state_does_not_disclose_or_mutate_flow(self):
        flow = self.begin()
        self.assertEqual(self.callback(flow, state='A' * 43).status_code, 400)
        self.assertEqual(self.status()['phase'], 'Pending')
        self.assertEqual(self.calls, [])

    def test_09_provider_state_mismatch_or_oauth_error_fails_closed(self):
        for failure in ('state', 'oauth'):
            with self.subTest(failure=failure):
                self.token_error = failure
                flow = self.begin()
                self.assertEqual(self.callback(flow).status_code, 200)
                self.assertEqual(self.status()['phase'], 'Failed')
                self.assertFalse(self.status()['linked'])

    def test_10_user_info_must_match_token_subject(self):
        self.user_error = 'subject'
        flow = self.begin()
        self.assertEqual(self.callback(flow).status_code, 200)
        self.assertEqual(self.status()['phase'], 'Failed')
        self.assertFalse(self.status()['linked'])

    def test_11_redirect_wrong_content_type_and_oversized_provider_body_rejected(self):
        for failure in ('redirect', 'type', 'oversized'):
            with self.subTest(failure=failure):
                self.user_error = failure
                flow = self.begin()
                self.assertEqual(self.callback(flow).status_code, 200)
                self.assertEqual(self.status()['phase'], 'Failed')
                self.assertFalse(self.status()['linked'])

    def test_12_same_vk_subject_cannot_overwrite_another_journey(self):
        first = self.begin()
        self.assertEqual(self.callback(first).status_code, 200)
        other = self.app.state.authority.provision()
        headers = {'Authorization': 'Bearer ' + other['token']}
        before = self.wallet_state()
        second = self.begin(headers=headers)
        self.assertEqual(self.callback(second).status_code, 200)
        status = self.status(headers)
        self.assertEqual(status['phase'], 'Conflict')
        self.assertFalse(status['linked'])
        self.assertTrue(self.status()['linked'])
        self.assertEqual(self.wallet_state(), before)

    def test_13_deleted_account_cannot_finish_link(self):
        flow = self.begin()
        verify = self.provider.verify
        def deletion(*args):
            value = verify(*args)
            with self.app.state.authority.database.transaction() as db:
                db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?) ON CONFLICT(player_id) DO UPDATE SET state='DeletionRequested'", (self.account['playerId'], self.now))
            return value
        self.provider.verify = deletion
        self.assertEqual(self.callback(flow).status_code, 410)
        with self.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM account_provider_links').fetchone()[0], 0)

    def test_14_cancel_during_provider_wait_prevents_commit(self):
        flow = self.begin()
        verify = self.provider.verify
        def cancellation(*args):
            value = verify(*args)
            self.app.state.provider_identity.cancel(self.actor(), flow['flowId'])
            return value
        self.provider.verify = cancellation
        self.assertEqual(self.callback(flow).status_code, 200)
        self.assertEqual(self.status()['phase'], 'Cancelled')
        self.assertFalse(self.status()['linked'])

    def test_15_restart_recovers_pending_authorization_and_linked_state(self):
        flow = self.begin()
        self.client.close()
        self.app = create_app(self.path, CONFIG, lambda: self.now, vk_configuration=self.config, vk_provider=self.provider)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.assertEqual(self.status()['authorizeUrl'], flow['authorizeUrl'])
        self.assertEqual(self.callback(flow).status_code, 200)
        self.assertTrue(self.status()['linked'])

    def test_16_anonymous_client_identity_and_duplicate_callback_fields_rejected(self):
        self.assertEqual(self.client.get('/v1/identity/vk/status').status_code, 401)
        self.assertEqual(self.client.post('/v1/identity/vk/link', headers=self.headers, json={'requestId': uuid.uuid4().hex, 'subject': '12345'}).status_code, 422)
        flow = self.begin()
        state = parse_qs(urlsplit(flow['authorizeUrl']).query)['state'][0]
        self.assertEqual(self.client.get('/v1/identity/vk/callback', params=[('state', state), ('state', state), ('code', 'fixture-code'), ('device_id', 'browser-device')]).status_code, 400)
        self.assertEqual(self.calls, [])

    def test_17_status_and_cancellation_do_not_leak_another_players_flow(self):
        flow = self.begin()
        other = self.app.state.authority.provision()
        headers = {'Authorization': 'Bearer ' + other['token']}
        self.assertEqual(self.status(headers)['flowId'], '')
        self.assertEqual(self.client.post('/v1/identity/vk/flows/' + flow['flowId'] + '/cancel', headers=headers).status_code, 404)
        self.assertEqual(self.status()['phase'], 'Pending')

    def test_18_per_account_attempt_limit_persists_after_terminal_flows(self):
        for _ in range(8):
            flow = self.begin()
            self.ok(self.client.post('/v1/identity/vk/flows/' + flow['flowId'] + '/cancel', headers=self.headers))
        response = self.client.post('/v1/identity/vk/link', headers=self.headers, json={'requestId': uuid.uuid4().hex})
        self.assertEqual(response.status_code, 429)

    def test_19_revoked_actor_after_authentication_cannot_begin(self):
        actor = self.actor()
        self.app.state.authority.revoke(self.account['token'])
        with self.assertRaises(ServiceError) as caught:
            self.app.state.provider_identity.begin(actor, ProviderLinkRequest(requestId=uuid.uuid4().hex))
        self.assertEqual(caught.exception.status, 401)

    def test_20_provider_denial_is_cancellation_without_identity_change(self):
        before = self.wallet_state()
        flow = self.begin()
        self.assertEqual(self.callback(flow, error='access_denied').status_code, 200)
        self.assertEqual(self.status()['phase'], 'Cancelled')
        self.assertEqual(self.calls, [])
        self.assertEqual(self.wallet_state(), before)

    def test_21_real_managed_deletion_removes_provider_association_and_flow(self):
        key, public, refresh = self.managed_guest()
        flow = self.begin()
        self.assertEqual(self.callback(flow).status_code, 200)
        self.assertTrue(self.status()['linked'])
        body = {'requestId': uuid.uuid4().hex, 'publicKey': public, 'playerId': self.account['playerId'], 'refreshToken': refresh}
        deletion = self.signed_identity('delete', body, key)
        response = self.ok(self.client.post('/v1/account/deletion', json=deletion))
        self.assertTrue(response['sessionsRevoked'])
        self.assertEqual(self.client.get('/v1/identity/vk/status', headers=self.headers).status_code, 401)
        with self.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM account_provider_links WHERE player_id=?', (self.account['playerId'],)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM account_provider_flows WHERE player_id=?', (self.account['playerId'],)).fetchone()[0], 0)

    def test_22_real_deletion_during_exchange_has_no_deleted_flow_dereference(self):
        key, public, refresh = self.managed_guest()
        flow = self.begin()
        body = {'requestId': uuid.uuid4().hex, 'publicKey': public, 'playerId': self.account['playerId'], 'refreshToken': refresh}
        deletion = DeletionRequest.model_validate(self.signed_identity('delete', body, key))
        verify = self.provider.verify
        def delete_during_exchange(*args):
            subject = verify(*args)
            self.app.state.identity.deletion(None, deletion)
            return subject
        self.provider.verify = delete_during_exchange
        self.assertEqual(self.callback(flow).status_code, 410)
        with self.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM account_provider_links').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM account_provider_flows').fetchone()[0], 0)

    def test_23_another_players_new_flow_clears_abandoned_expired_proofs(self):
        first = self.begin()
        other = self.app.state.authority.provision()
        self.now += 600
        self.begin(headers={'Authorization': 'Bearer ' + other['token']})
        with self.app.state.authority.database.connect() as db:
            old = db.execute('SELECT phase,state_secret,verifier FROM account_provider_flows WHERE id=?', (first['flowId'],)).fetchone()
            self.assertEqual(tuple(old), ('Expired', '', ''))

    def test_24_non_ascii_provider_state_fails_and_new_signup_can_retry(self):
        self.token_error = 'unicode'
        flow = self.begin()
        self.assertEqual(self.callback(flow).status_code, 200)
        self.assertEqual(self.status()['phase'], 'Failed')
        self.assertFalse(self.status()['linked'])
        self.token_error = ''
        retry = self.begin()
        self.assertNotEqual(flow['flowId'], retry['flowId'])
        self.assertEqual(self.callback(retry).status_code, 200)
        self.assertTrue(self.status()['linked'])

    def test_25_monotonic_budget_is_shared_across_both_provider_responses(self):
        elapsed = [0.0]
        class DelayedBody(httpx.AsyncByteStream):
            def __init__(self, content):
                self.content = content
            async def __aiter__(self):
                elapsed[0] += 8.0
                yield self.content
        def delayed(request):
            response = self.provider_http(request)
            return httpx.Response(response.status_code, headers=response.headers, stream=DelayedBody(response.content))
        self.provider.transport = httpx.MockTransport(delayed)
        self.provider.monotonic = lambda: elapsed[0]
        flow = self.begin()
        self.assertEqual(self.callback(flow).status_code, 200)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.status()['phase'], 'Failed')
        self.assertFalse(self.status()['linked'])

    def test_26_wall_budget_cancels_a_stalled_body_and_releases_flow(self):
        released = []
        class StalledBody(httpx.AsyncByteStream):
            async def __aiter__(self):
                try:
                    await asyncio.sleep(5)
                    yield b'{}'
                finally:
                    released.append(True)
        self.provider.transport = httpx.MockTransport(lambda request: httpx.Response(200, headers={'Content-Type': 'application/json'}, stream=StalledBody()))
        flow = self.begin()
        began = time.monotonic()
        with patch('hotr_backend.vk_provider.EXCHANGE_SECONDS', 0.04):
            self.assertEqual(self.callback(flow).status_code, 200)
        self.assertLess(time.monotonic() - began, 2)
        self.assertTrue(released)
        self.assertEqual(self.status()['phase'], 'Failed')

    def test_27_deep_json_and_unexpected_transport_errors_fail_without_raw_error(self):
        for kind in ('deep-json', 'transport'):
            with self.subTest(kind=kind):
                def malformed(request):
                    if kind == 'transport':
                        raise RuntimeError('fixture-private-provider-payload')
                    return httpx.Response(200, headers={'Content-Type': 'application/json'}, content=('[' * 1200 + '0' + ']' * 1200).encode())
                self.provider.transport = httpx.MockTransport(malformed)
                flow = self.begin()
                response = self.callback(flow)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('fixture-private-provider-payload', response.text)
                self.assertEqual(self.status()['phase'], 'Failed')
                self.assertFalse(self.status()['linked'])


if __name__ == '__main__':
    unittest.main()
