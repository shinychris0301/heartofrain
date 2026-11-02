"""Actual ASGI/SQLite teams, text permissions, moderation and deletion controls.

Ephemeral operator/managed-identity fixtures are local tests, not a deployed
moderation service, push channel, legal erasure or native chat UI claim.
"""
import base64
import concurrent.futures
import hashlib
import json
import secrets
import tempfile
import unittest
import uuid
from pathlib import Path

from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.messaging_schemas import SendMessage
from hotr_backend.service import ServiceError

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class MessagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-messaging-')
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.now = 100 * 86400 + 1000
        self.open()
        self.identities = [self.authority.provision(lifetime=2_592_000) for _ in range(5)]
        self.players = [value['playerId'] for value in self.identities]
        self.finance_before = self.finance()

    def open(self):
        self.app = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True, identity_enabled=True)
        self.authority = self.app.state.authority
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def restart(self):
        self.client.close()
        self.open()

    def tearDown(self):
        try:
            self.assertEqual(self.finance(), self.finance_before, 'Social actions changed existing financial/gameplay state')
        finally:
            self.client.close()
            self.temp.cleanup()

    def finance(self):
        # New managed-guest genesis is an identity operation, not social credit.
        # Existing fixture players' wallet/ledger/attempt/reward rows must remain exact.
        ids = tuple(self.players) if hasattr(self, 'players') else ()
        if not ids:
            return None
        with self.authority.database.connect() as db:
            result = {}
            for table, owner in (('players', 'id'), ('wallets', 'player_id'), ('wallet_ledger', 'player_id'),
                ('rewards', 'player_id'), ('gameplay_attempts', 'player_id'), ('commerce_orders', 'player_id'),
                ('commerce_credits', 'player_id')):
                result[table] = [tuple(row) for row in db.execute('SELECT * FROM ' + table + ' WHERE ' + owner +
                    ' IN (' + ','.join('?' for _ in ids) + ') ORDER BY 1', ids)]
            return result

    def headers(self, actor):
        value = self.identities[actor] if isinstance(actor, int) else actor
        return {'Authorization': 'Bearer ' + value.get('token', value.get('accessToken', ''))}

    def request(self, method, path, actor=0, data=None, status=200, **kwargs):
        response = self.client.request(method, path, headers=self.headers(actor), json=data, **kwargs)
        self.assertEqual(response.status_code, status, response.text)
        return response.json()

    def post(self, path, actor=0, status=200, command=None, **values):
        return self.request('POST', path, actor, {'commandId': command or ident(), **values}, status)

    def get(self, path, actor=0, status=200, **kwargs):
        return self.request('GET', path, actor, status=status, **kwargs)

    def team(self, owner=0, name='Хранители дождя', description='Вместе к победе'):
        return self.post('/v1/teams', owner, name=name, description=description)['teamId']

    def join(self, team, actor=1, **kwargs):
        return self.post('/v1/teams/' + team + '/join', actor, **kwargs)

    def friends(self, a=0, b=1):
        sent = self.post('/v1/friends/request', a, playerId=self.players[b])
        self.post('/v1/friends/respond', b, requestId=sent['requestId'], action='accept')

    def direct(self, a=0, b=1, body='Привет, друг!', **kwargs):
        return self.post('/v1/messages/Direct/' + self.players[b], a, text=body, **kwargs)

    def count(self, table):
        with self.authority.database.connect() as db:
            return db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def grant_staff(self, actor=4):
        digest = self.authority._digest(self.identities[actor]['token'])
        with self.authority.database.transaction() as db:
            db.execute('INSERT OR IGNORE INTO social_moderators VALUES(?,?)', (digest, self.now))
        return digest

    def moderate(self, message, action, actor=4, **kwargs):
        return self.post('/internal/v1/moderation/messages', actor, messageId=message, action=action,
                         reason='Проверено модератором', **kwargs)

    def test_01_default_social_disabled_and_team_public_view_has_no_private_state(self):
        disabled = create_app(Path(self.temp.name) / 'disabled.sqlite3', CONFIG, lambda: self.now)
        identity = disabled.state.authority.provision()
        with TestClient(disabled) as client:
            self.assertEqual(client.get('/v1/teams', headers=self.headers(identity)).status_code, 503)
        team = self.team()
        public = self.get('/v1/teams/' + team, 2)
        self.assertEqual(set(public), {'teamId', 'name', 'description', 'memberCount', 'capacity', 'ownerId', 'isMember', 'badgeId'})
        self.assertFalse(public['isMember'])
        self.assertNotIn('members', public)
        self.assertNotIn('token', json.dumps(public))

    def test_02_team_create_join_capacity_one_team_and_serialized_last_place(self):
        self.app.state.messaging.capacity = 2
        team = self.team()
        def join(actor):
            return self.client.post('/v1/teams/' + team + '/join', json={'commandId': ident()}, headers=self.headers(actor))
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(join, [1, 2]))
        self.assertEqual(sorted(response.status_code for response in responses), [200, 409])
        winner = 1 if responses[0].status_code == 200 else 2
        self.assertEqual(self.get('/v1/teams/' + team, winner)['memberCount'], 2)
        another = self.team(3, 'Другая команда')
        self.join(another, winner, status=409)
        self.post('/v1/teams', winner, status=409, name='Своя команда')
        self.assertEqual(self.count('social_team_members'), 3)

    def test_03_owner_leave_requires_explicit_transfer_and_lost_reply_replays_exactly(self):
        team = self.team(); self.join(team, 1)
        self.post('/v1/teams/' + team + '/leave', 0, status=409)
        command = ident()
        def lost(stage):
            if stage == 'AfterCommit':
                raise OSError('synthetic lost reply')
        self.authority.checkpoint = lost
        self.post('/v1/teams/' + team + '/members/transfer', 0, status=500, command=command, playerId=self.players[1])
        self.authority.checkpoint = None
        self.restart()
        result = self.post('/v1/teams/' + team + '/members/transfer', 0, command=command, playerId=self.players[1])
        self.assertEqual(result['action'], 'transfer')
        self.assertEqual(self.get('/v1/teams/' + team, 1)['ownerId'], self.players[1])
        self.post('/v1/teams/' + team + '/members/transfer', 0, status=403, playerId=self.players[0])
        self.post('/v1/teams/' + team + '/members/transfer', 0, status=403, command=command, playerId=self.players[2])
        leave = ident()
        first = self.post('/v1/teams/' + team + '/leave', 0, command=leave)
        self.assertEqual(self.post('/v1/teams/' + team + '/leave', 0, command=leave), first)
        self.post('/v1/teams/' + team + '/leave', 1)
        self.get('/v1/teams/' + team, 2, status=404)

    def test_04_kick_bans_and_owner_only_unban_does_not_auto_join(self):
        team = self.team(); self.join(team, 1); self.join(team, 2)
        self.post('/v1/teams/' + team + '/members/kick', 2, status=403, playerId=self.players[1])
        command = ident()
        kicked = self.post('/v1/teams/' + team + '/members/kick', command=command, playerId=self.players[1])
        self.assertEqual(self.post('/v1/teams/' + team + '/members/kick', command=command, playerId=self.players[1]), kicked)
        self.join(team, 1, status=403)
        self.post('/v1/teams/' + team + '/members/unban', 2, status=403, playerId=self.players[1])
        self.post('/v1/teams/' + team + '/members/unban', playerId=self.players[1])
        self.assertFalse(self.get('/v1/teams/' + team, 1)['isMember'])
        self.join(team, 1)
        self.post('/v1/teams/' + team + '/members/kick', status=409, playerId=self.players[0])

    def test_05_team_pagination_and_create_receipt_idempotence(self):
        command = ident()
        first = self.post('/v1/teams', name='Первая команда', command=command)
        self.assertEqual(self.post('/v1/teams', name='Первая команда', command=command), first)
        self.post('/v1/teams', name='Другое имя', command=command, status=409)
        self.team(1, 'Вторая команда'); self.team(2, 'Третья команда')
        first_page = self.get('/v1/teams', 3, params={'limit': 2})
        second = self.get('/v1/teams', 3, params={'limit': 2, 'after': first_page['nextCursor']})
        self.assertTrue(first_page['hasMore']); self.assertFalse(second['hasMore'])
        ids = [v['teamId'] for v in first_page['teams'] + second['teams']]
        self.assertEqual((len(ids), len(set(ids))), (3, 3))
        self.assertTrue(all('members' not in v for v in first_page['teams']))

    def test_06_direct_requires_mutual_friendship_and_blocks_apply_both_directions_and_cached_receipts(self):
        self.direct(status=404)
        self.friends()
        command = ident(); sent = self.direct(command=command)
        self.assertEqual(self.direct(command=command), sent)
        self.post('/v1/blocks/add', playerId=self.players[1])
        for a, b in ((0, 1), (1, 0)):
            self.direct(a, b, status=404)
            self.get('/v1/messages/Direct/' + self.players[b], a, status=404)
        self.direct(command=command, status=404)
        self.post('/v1/blocks/remove', playerId=self.players[1])
        self.direct(status=404)  # Unblock does not silently restore friendship.
        self.assertEqual(self.count('social_messages'), 1)

    def test_07_direct_pagination_unread_monotonic_read_and_channel_privacy(self):
        self.friends()
        messages = [self.direct(body='Сообщение ' + str(index)) for index in range(3)]
        first = self.get('/v1/messages/Direct/' + self.players[0], 1, params={'limit': 2})
        self.assertEqual((len(first['messages']), first['unreadCount'], first['hasMore']), (2, 3, True))
        second = self.get('/v1/messages/Direct/' + self.players[0], 1, params={'after': first['nextCursor']})
        self.assertEqual([v['messageId'] for v in second['messages']], [messages[2]['messageId']])
        read_path = '/v1/messages/Direct/' + self.players[0] + '/read'
        self.post(read_path, 1, through=messages[1]['sequence'])
        self.assertEqual(self.get('/v1/messages/Direct/' + self.players[0], 1)['unreadCount'], 1)
        self.post(read_path, 1, through=0)
        self.assertEqual(self.get('/v1/messages/Direct/' + self.players[0], 1)['unreadCount'], 1)
        self.post(read_path, 1, status=409, through=messages[-1]['sequence'] + 1000)
        self.get('/v1/messages/Direct/' + self.players[0], 2, status=404)
        self.assertEqual(self.get('/v1/messages/Direct/' + self.players[1], 0)['unreadCount'], 0)
        self.restart()
        self.assertEqual(self.get('/v1/messages/Direct/' + self.players[0], 1)['unreadCount'], 1)

    def test_08_read_rejects_other_channel_hidden_and_blocked_cursors(self):
        team = self.team(); self.join(team, 1); self.join(team, 2)
        first = self.post('/v1/messages/Team/' + team, text='Первое')
        self.friends(0, 3)
        other = self.direct(0, 3)
        blocked = self.post('/v1/messages/Team/' + team, 2, text='Не показывать')
        hidden = self.post('/v1/messages/Team/' + team, text='Скрыто')
        self.post('/v1/messages/Team/' + team, text='Последнее')
        self.grant_staff(); self.moderate(hidden['messageId'], 'Hide')
        self.post('/v1/blocks/add', 1, playerId=self.players[2])
        read = '/v1/messages/Team/' + team + '/read'
        for message in (other, hidden, blocked):
            self.post(read, 1, status=409, through=message['sequence'])
        self.post(read, 1, through=first['sequence'])

    def test_09_member_only_team_chat_blocked_author_filter_and_leave_revocation(self):
        team = self.team(); self.join(team, 1); self.join(team, 2)
        a = self.post('/v1/messages/Team/' + team, text='От владельца')
        self.post('/v1/messages/Team/' + team, 1, text='От участника')
        self.post('/v1/messages/Team/' + team, 3, status=403, text='Чужой')
        self.get('/v1/messages/Team/' + team, 3, status=403)
        self.post('/v1/blocks/add', 2, playerId=self.players[0])
        visible = self.get('/v1/messages/Team/' + team, 2)
        self.assertEqual([m['authorId'] for m in visible['messages']], [self.players[1]])
        self.assertEqual(visible['unreadCount'], 1)
        self.assertNotIn(self.players[0], [m['playerId'] for m in self.get('/v1/teams/' + team, 2)['members']])
        self.post('/v1/teams/' + team + '/leave', 1)
        self.get('/v1/messages/Team/' + team, 1, status=403)
        self.assertEqual(self.count('social_messages'), 2)

    def test_10_unicode_normalization_bounds_controls_forged_fields_and_rate(self):
        self.friends(); self.app.state.messaging.rate = 3
        first = self.direct(body='  Привет!\nCafe\u0301  ')
        self.assertEqual(self.get('/v1/messages/Direct/' + self.players[0], 1)['messages'][0]['text'], 'Привет!\nCafé')
        for body in ('A\x00B', 'A\tB', 'A\u202eB', 'A\u2028B', ' ' * 5, 'x' * 1001):
            self.direct(body=body, status=422)
        self.direct(body='x' * 1000)
        third_command = ident(); third = self.direct(body='Третье', command=third_command)
        self.assertEqual(self.direct(body='Третье', command=third_command), third)
        self.direct(body='Лишнее', status=429)
        self.direct(body='Изменено', command=third_command, status=409)
        self.request('POST', '/v1/messages/Direct/' + self.players[1], data={'commandId': ident(), 'text': 'X', 'authorId': self.players[2]}, status=422)
        self.now += 61
        self.direct(body='После паузы')
        self.assertEqual(self.count('social_messages'), 4)

    def test_11_cyrillic_team_names_control_and_length_limits_and_daily_create_cap(self):
        for name in ('x', 'x' * 33, 'A\u202eB', 'A\x00B', '  '):
            self.post('/v1/teams', name=name, status=422)
        self.post('/v1/teams', name='Хорошее имя', description='x' * 161, status=422)
        for index in range(3):
            team = self.team(name='Команда ' + str(index))
            self.post('/v1/teams/' + team + '/leave')
        self.post('/v1/teams', name='Четвёртая', status=429)
        self.now += 86401
        self.team(name='На следующий день')

    def test_12_report_received_direct_message_after_block_without_exposing_new_content(self):
        self.friends(); message = self.direct()
        self.post('/v1/blocks/add', 1, playerId=self.players[0])
        command = ident()
        reported = self.post('/v1/reports', 1, command=command, messageId=message['messageId'], reason='Abuse', details='Неприемлемое сообщение')
        self.assertEqual(self.post('/v1/reports', 1, command=command, messageId=message['messageId'], reason='Abuse', details='Неприемлемое сообщение'), reported)
        self.assertEqual(self.post('/v1/reports', 1, messageId=message['messageId'], reason='Other')['reportId'], reported['reportId'])
        self.post('/v1/reports', 2, status=404, messageId=message['messageId'], reason='Spam')
        self.get('/v1/messages/Direct/' + self.players[0], 1, status=404)
        self.assertEqual((self.count('social_reports'), set(reported)), (1, {'reportId', 'state'}))

    def test_13_staff_credential_grant_not_role_or_player_and_revoked_actor_cannot_moderate(self):
        self.friends(); message = self.direct()
        self.post('/v1/reports', 1, messageId=message['messageId'], reason='Spam')
        self.get('/internal/v1/moderation/reports', 0, status=403)
        self.moderate(message['messageId'], 'Hide', actor=0, status=403)
        verifier = self.authority.provision(self.players[4], role='verifier')
        self.get('/internal/v1/moderation/reports', verifier, status=403)
        self.grant_staff()
        reports = self.get('/internal/v1/moderation/reports', 4)
        self.assertEqual(reports['reports'][0]['text'], 'Привет, друг!')
        other_credential = self.authority.provision(self.players[4])
        self.get('/internal/v1/moderation/reports', other_credential, status=403)
        stale = self.authority.authenticate(self.identities[4]['token'])
        self.authority.revoke(self.identities[4]['token'])
        self.moderate(message['messageId'], 'Hide', status=401)
        with self.assertRaises(ServiceError) as error:
            self.app.state.messaging.moderation_queue(stale)
        self.assertEqual(error.exception.status, 401)
        self.assertEqual(self.count('social_moderation_actions'), 0)

    def test_14_moderation_hide_restore_delete_terminal_and_exact_audit_once(self):
        self.friends(); message = self.direct()
        self.post('/v1/reports', 1, messageId=message['messageId'], reason='Abuse')
        self.grant_staff(); command = ident()
        hidden = self.moderate(message['messageId'], 'Hide', command=command)
        self.assertEqual(self.moderate(message['messageId'], 'Hide', command=command), hidden)
        self.assertEqual(self.count('social_moderation_actions'), 1)
        self.assertEqual(self.get('/v1/messages/Direct/' + self.players[0], 1)['messages'], [])
        self.assertEqual(self.get('/internal/v1/moderation/reports', 4)['reports'], [])
        self.moderate(message['messageId'], 'Restore')
        self.assertEqual(len(self.get('/v1/messages/Direct/' + self.players[0], 1)['messages']), 1)
        self.moderate(message['messageId'], 'Delete')
        self.moderate(message['messageId'], 'Restore', status=409)
        self.moderate(message['messageId'], 'Hide', status=409)
        self.moderate(message['messageId'], 'DismissReports')
        with self.authority.database.connect() as db:
            row = db.execute('SELECT body,visibility FROM social_messages WHERE id=?', (message['messageId'],)).fetchone()
        self.assertEqual(tuple(row), ('', 'Deleted'))
        self.assertEqual(self.count('social_moderation_actions'), 4)

    def test_15_read_and_mutation_validation_are_bounded_and_no_public_staff_grant(self):
        team = self.team()
        for params in ({'after': -1}, {'limit': 101}, {'after': 9_223_372_036_854_775_808}):
            self.get('/v1/messages/Team/' + team, params=params, status=422)
        self.post('/v1/teams/' + team + '/members/appoint', status=422, playerId=self.players[1])
        self.post('/v1/teams/' + team + '/members/transfer', status=404, playerId=self.players[1])
        self.post('/v1/teams/' + team + '/members/kick', status=409, playerId=self.players[0])
        self.request('POST', '/internal/v1/moderation/grant', data={'credential': self.identities[0]['token']}, status=404)
        self.assertEqual(self.count('social_moderators'), 0)

    def test_17_report_daily_cap_preserves_exact_retry_and_one_report_per_message(self):
        self.friends()
        messages = []
        for index in range(21):
            if index and index % 9 == 0:
                self.now += 61
            messages.append(self.direct(body='Сообщение ' + str(index)))
        command = ident()
        first = self.post('/v1/reports', 1, command=command, messageId=messages[0]['messageId'], reason='Spam')
        for message in messages[1:20]:
            self.post('/v1/reports', 1, messageId=message['messageId'], reason='Spam')
        self.post('/v1/reports', 1, status=429, messageId=messages[20]['messageId'], reason='Spam')
        self.assertEqual(self.post('/v1/reports', 1, command=command, messageId=messages[0]['messageId'], reason='Spam'), first)
        self.assertEqual(self.post('/v1/reports', 1, messageId=messages[0]['messageId'], reason='Other')['reportId'], first['reportId'])
        self.assertEqual(self.count('social_reports'), 20)
        self.now += 86401
        self.post('/v1/reports', 1, messageId=messages[20]['messageId'], reason='Spam')
        self.assertEqual(self.count('social_reports'), 21)

    def test_18_revocation_precedes_cached_send_and_disabled_mutation_has_no_state_effect(self):
        self.friends()
        command = ident(); self.direct(command=command)
        stale = self.authority.authenticate(self.identities[0]['token'])
        self.authority.revoke(self.identities[0]['token'])
        self.direct(command=command, status=401)
        with self.assertRaises(ServiceError) as error:
            self.app.state.messaging.send(stale, 'Direct', self.players[1], SendMessage(commandId=command, text='Привет, друг!'))
        self.assertEqual(error.exception.status, 401)
        self.app.state.messaging.enabled = False
        self.post('/v1/teams', 2, status=503, name='Недоступная')
        self.assertEqual((self.count('social_messages'), self.count('social_teams')), (1, 0))

    def signed_identity(self, key, body, purpose):
        # Independently construct the public challenge binding, not a production helper.
        public = base64.b64encode(key.public_key().export_key(format='DER')).decode('ascii')
        body = {'requestId': ident(), 'publicKey': public, **body}
        digest = lambda text: hashlib.sha256(text.encode('ascii')).hexdigest()
        binding = {'protocol': 'hotr-managed-identity-v1', 'purpose': purpose, 'requestId': body['requestId'],
                   'publicKey': public, 'refreshDigest': digest(body['refreshToken'])}
        if purpose == 'guest': binding['recoveryDigest'] = digest(body['recoverySecret'])
        else: binding['playerId'] = body['playerId']
        canonical = json.dumps(binding, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        challenge = self.client.post('/v1/identity/challenges', json={'purpose': purpose, 'requestId': body['requestId'],
            'publicKey': public, 'payloadDigest': digest(canonical)})
        self.assertEqual(challenge.status_code, 200, challenge.text)
        proof = challenge.json()
        signature = DSS.new(key, 'fips-186-3', encoding='der').sign(SHA256.new(base64.b64decode(proof['signingBytes'])))
        return {**body, 'challengeId': proof['challengeId'], 'signature': base64.b64encode(signature).decode('ascii')}

    def test_16_actual_signed_deletion_atomic_cleanup_closes_team_releases_all_and_preserves_financial_audit(self):
        key, refresh = ECC.generate(curve='P-256'), secrets.token_urlsafe(32)
        signup = self.signed_identity(key, {'refreshToken': refresh, 'recoverySecret': secrets.token_urlsafe(32)}, 'guest')
        response = self.client.post('/v1/identity/guest', json=signup)
        self.assertEqual(response.status_code, 200, response.text)
        guest = response.json(); guest_id = guest['playerId']
        self.post('/v1/profile', guest, displayName='Личное имя', leaderboardOptIn=True)
        team = self.post('/v1/teams', guest, name='Личная команда', description='Личное описание')['teamId']
        self.join(team, 0); self.join(team, 1)
        message = self.post('/v1/messages/Team/' + team, guest, text='Личное сообщение')
        sent = self.post('/v1/friends/request', guest, playerId=self.players[0])
        self.post('/v1/friends/respond', 0, requestId=sent['requestId'], action='accept')
        self.post('/v1/blocks/add', guest, playerId=self.players[2])
        reply = self.post('/v1/messages/Team/' + team, 0, text='Ответ')
        self.post('/v1/reports', guest, messageId=reply['messageId'], reason='Other', details='Личная жалоба')
        self.post('/v1/messages/Team/' + team + '/read', guest, through=message['sequence'])
        with self.authority.database.transaction() as db:
            db.execute('INSERT INTO social_moderators VALUES(?,?)', (self.authority._digest(guest['accessToken']), self.now))
        with self.authority.database.connect() as db:
            wallet_before = tuple(db.execute('SELECT * FROM wallets WHERE player_id=?', (guest_id,)).fetchone())
        deletion = self.signed_identity(key, {'playerId': guest_id, 'refreshToken': refresh}, 'delete')
        # A failed cleanup transaction cannot revoke identity or strand teammates.
        with self.authority.database.transaction() as db:
            db.execute("CREATE TRIGGER fail_cleanup BEFORE DELETE ON social_profiles BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END")
        failed = self.client.post('/v1/account/deletion', json=deletion)
        self.assertEqual(failed.status_code, 503)
        self.assertEqual(self.get('/v1/teams/' + team, 0)['memberCount'], 3)
        with self.authority.database.transaction() as db: db.execute('DROP TRIGGER fail_cleanup')
        deletion = self.signed_identity(key, {'playerId': guest_id, 'refreshToken': refresh}, 'delete')
        deleted = self.client.post('/v1/account/deletion', json=deletion)
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertFalse(deleted.json()['physicalPurgeComplete'])
        self.assertFalse(deleted.json()['retentionPolicyConfigured'])
        retry_unsigned = {name: deletion[name] for name in ('requestId', 'playerId', 'refreshToken')}
        self.restart()
        retried = self.client.post('/v1/account/deletion', json=self.signed_identity(key, retry_unsigned, 'delete'))
        self.assertEqual(retried.status_code, 200, retried.text)
        self.assertEqual(retried.json(), deleted.json())
        self.get('/v1/messages/Team/' + team, guest, status=401)
        self.get('/v1/players/' + guest_id, 0, status=404)
        self.get('/v1/teams/' + team, 0, status=404)
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM social_team_members WHERE team_id=?', (team,)).fetchone()[0], 0)
            self.assertEqual(tuple(db.execute('SELECT active,name,description,owner_id FROM social_teams WHERE id=?', (team,)).fetchone()),
                             (0, 'Closed team', '', guest_id))
            self.assertEqual(tuple(db.execute('SELECT body,visibility FROM social_messages WHERE id=?', (message['messageId'],)).fetchone()), ('', 'Deleted'))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM social_profiles WHERE player_id=?', (guest_id,)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM social_friend_requests WHERE low_id=? OR high_id=?', (guest_id, guest_id)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM social_blocks WHERE blocker_id=? OR blocked_id=?', (guest_id, guest_id)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM social_message_reads WHERE player_id=?', (guest_id,)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT details FROM social_reports WHERE reporter_id=?', (guest_id,)).fetchone()[0], '')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM social_moderators WHERE credential_digest=?', (self.authority._digest(guest['accessToken']),)).fetchone()[0], 0)
            self.assertEqual(tuple(db.execute('SELECT * FROM wallets WHERE player_id=?', (guest_id,)).fetchone()), wallet_before)
            self.assertEqual(db.execute('SELECT state FROM account_states WHERE player_id=?', (guest_id,)).fetchone()[0], 'DeletionRequested')
        next_team = self.team(2, 'Новая команда')
        self.join(next_team, 0); self.join(next_team, 1)
        self.assertEqual(self.get('/v1/teams/' + next_team, 2)['ownerId'], self.players[2])


if __name__ == '__main__':
    unittest.main()
