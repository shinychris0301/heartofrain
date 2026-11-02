"""Authenticated VK signup/link, preserving the current managed player's save.

The callback only completes an existing authenticated intent. It cannot select
a player, import a wallet, mint a game session or silently merge two accounts.
"""
import hashlib
import os
import re
import secrets
import uuid

from fastapi import Depends, Query, Request
from fastapi.responses import HTMLResponse

from .guards import require_actor, require_active_player
from .schemas import Id, Model
from .service import Actor, ServiceError
from .vk_provider import VkConfiguration, VkProvider


class ProviderLinkRequest(Model):
    requestId: Id


def environment_configuration():
    flag = os.getenv('HOTR_VK_ID_ENABLED', '0')
    if flag not in ('0', '1'):
        raise RuntimeError('Invalid explicit VK configuration')
    return VkConfiguration(flag == '1', os.getenv('HOTR_VK_ID_CLIENT_ID', ''), os.getenv('HOTR_VK_ID_REDIRECT_URI', ''))


class ProviderIdentity:
    def __init__(self, authority, configuration=None, provider=None):
        self.authority, self.database = authority, authority.database
        self.configuration = configuration or environment_configuration()
        self.provider = provider or VkProvider(self.configuration)

    @staticmethod
    def _expire(db, now, player=None):
        sql = "UPDATE account_provider_flows SET phase='Expired',state_secret='',verifier='',updated_at=? WHERE phase IN ('Pending','Exchanging') AND expires_at<=?"
        args = (now, now)
        if player is not None:
            sql += ' AND player_id=?'
            args += (player,)
        db.execute(sql, args)

    def _view(self, db, actor, flow=None, include_url=False):
        linked = db.execute("SELECT linked_at FROM account_provider_links WHERE provider='vk' AND player_id=?", (actor.player,)).fetchone()
        value = {'playerId': actor.player, 'provider': 'vk', 'available': self.configuration.enabled,
                 'linked': bool(linked), 'linkedAt': linked['linked_at'] if linked else 0,
                 'phase': flow['phase'] if flow else 'Idle', 'flowId': flow['id'] if flow else '',
                 'requestId': flow['request_id'] if flow else '', 'expiresAt': flow['expires_at'] if flow else 0,
                 'authorizeUrl': '', 'serverUtc': actor.now, 'samePlayer': True}
        if include_url and flow and flow['phase'] == 'Pending' and flow['configuration_digest'] == self.configuration.fingerprint:
            value['authorizeUrl'] = self.provider.authorize_url(flow['state_secret'], flow['verifier'])
        return value

    def status(self, actor):
        with self.database.transaction() as db:
            now = self.authority._transaction_clock(db, actor.now)
            require_actor(db, actor)
            self._expire(db, now, actor.player)
            flow = db.execute('SELECT * FROM account_provider_flows WHERE player_id=? ORDER BY rowid DESC LIMIT 1', (actor.player,)).fetchone()
            return self._view(db, Actor(actor.player, now, actor.credential_digest), flow, True)

    def begin(self, actor, request):
        if not self.configuration.enabled:
            raise ServiceError(503, 'vk_provider_not_configured')
        with self.database.transaction() as db:
            now = self.authority._transaction_clock(db, actor.now)
            require_actor(db, actor)
            # Clear abandoned proofs globally before the pending-capacity test;
            # expired accounts must not keep the bounded pool permanently full.
            self._expire(db, now)
            old = db.execute('SELECT * FROM account_provider_flows WHERE player_id=? AND request_id=?', (actor.player, request.requestId)).fetchone()
            if old:
                return self._view(db, Actor(actor.player, now, actor.credential_digest), old, True)
            if db.execute("SELECT 1 FROM account_provider_links WHERE provider='vk' AND player_id=?", (actor.player,)).fetchone():
                return self._view(db, Actor(actor.player, now, actor.credential_digest))
            active = db.execute("SELECT * FROM account_provider_flows WHERE player_id=? AND phase IN ('Pending','Exchanging')", (actor.player,)).fetchone()
            if active:
                raise ServiceError(409, 'vk_link_pending')
            if db.execute('SELECT COUNT(*) FROM account_provider_flows WHERE player_id=? AND created_at>?', (actor.player, now - 3600)).fetchone()[0] >= 8:
                raise ServiceError(429, 'vk_link_rate_limited')
            if db.execute("SELECT COUNT(*) FROM account_provider_flows WHERE phase IN ('Pending','Exchanging')").fetchone()[0] >= 10000:
                raise ServiceError(503, 'vk_link_capacity')
            identifier, state, verifier = uuid.uuid4().hex, secrets.token_urlsafe(32), secrets.token_urlsafe(48)
            db.execute('INSERT INTO account_provider_flows VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (identifier, actor.player, request.requestId, self.configuration.fingerprint, hashlib.sha256(state.encode()).hexdigest(),
                        state, verifier, 'Pending', now + 600, now, now))
            flow = db.execute('SELECT * FROM account_provider_flows WHERE id=?', (identifier,)).fetchone()
            return self._view(db, Actor(actor.player, now, actor.credential_digest), flow, True)

    def cancel(self, actor, flow_id):
        with self.database.transaction() as db:
            now = self.authority._transaction_clock(db, actor.now)
            require_actor(db, actor)
            # Clearing proof before a delayed callback prevents its commit.
            db.execute("UPDATE account_provider_flows SET phase='Cancelled',state_secret='',verifier='',updated_at=? WHERE id=? AND player_id=? AND phase IN ('Pending','Exchanging')", (now, flow_id, actor.player))
            flow = db.execute('SELECT * FROM account_provider_flows WHERE id=? AND player_id=?', (flow_id, actor.player)).fetchone()
            if not flow:
                raise ServiceError(404, 'vk_link_not_found')
            return self._view(db, Actor(actor.player, now, actor.credential_digest), flow)

    def callback(self, state, code='', device_id='', error=''):
        if not self.configuration.enabled:
            raise ServiceError(503, 'vk_provider_not_configured')
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', state):
            raise ServiceError(400, 'vk_callback_invalid')
        with self.database.transaction() as db:
            now = self.authority._transaction_clock(db)
            self._expire(db, now)
            flow = db.execute('SELECT * FROM account_provider_flows WHERE state_digest=?', (hashlib.sha256(state.encode()).hexdigest(),)).fetchone()
            if not flow or flow['configuration_digest'] != self.configuration.fingerprint:
                raise ServiceError(400, 'vk_callback_invalid')
            require_active_player(db, flow['player_id'])
            if flow['phase'] in ('Linked', 'Cancelled', 'Failed', 'Conflict', 'Expired'):
                return flow['phase']
            if flow['phase'] != 'Pending':
                raise ServiceError(409, 'vk_callback_pending')
            if error:
                db.execute("UPDATE account_provider_flows SET phase='Cancelled',state_secret='',verifier='',updated_at=? WHERE id=?", (now, flow['id']))
                return 'Cancelled'
            if not 1 <= len(code) <= 4096 or not 1 <= len(device_id) <= 512 or any(ord(c) < 32 for c in code + device_id):
                raise ServiceError(400, 'vk_callback_invalid')
            db.execute("UPDATE account_provider_flows SET phase='Exchanging',updated_at=? WHERE id=?", (now, flow['id']))
            flow = dict(flow)
        try:
            subject = self.provider.verify(code, device_id, state, flow['verifier'])
            if not re.fullmatch(r'[0-9a-f]{64}', subject):
                raise ServiceError(502, 'vk_provider_identity_invalid')
        except ServiceError:
            with self.database.transaction() as db:
                now = self.authority._transaction_clock(db)
                db.execute("UPDATE account_provider_flows SET phase='Failed',state_secret='',verifier='',updated_at=? WHERE id=? AND phase='Exchanging'", (now, flow['id']))
            return 'Failed'
        with self.database.transaction() as db:
            now = self.authority._transaction_clock(db)
            current = db.execute('SELECT * FROM account_provider_flows WHERE id=?', (flow['id'],)).fetchone()
            require_active_player(db, flow['player_id'])
            if current is None:
                raise ServiceError(410, 'vk_link_not_found')
            if current['phase'] != 'Exchanging':
                return current['phase']
            phase = 'Expired' if current['expires_at'] <= now else 'Linked'
            if phase == 'Linked':
                owner = db.execute("SELECT player_id FROM account_provider_links WHERE provider='vk' AND subject_digest=?", (subject,)).fetchone()
                existing = db.execute("SELECT subject_digest FROM account_provider_links WHERE provider='vk' AND player_id=?", (flow['player_id'],)).fetchone()
                if owner and owner['player_id'] != flow['player_id'] or existing and existing['subject_digest'] != subject:
                    phase = 'Conflict'
                else:
                    db.execute("INSERT OR IGNORE INTO account_provider_links VALUES('vk',?,?,?)", (subject, flow['player_id'], now))
            db.execute("UPDATE account_provider_flows SET phase=?,state_secret='',verifier='',updated_at=? WHERE id=?", (phase, now, flow['id']))
            return phase


def register_provider_routes(app, service, actor_dependency, signin_service=None):
    @app.get('/v1/identity/vk/status')
    def provider_status(current=Depends(actor_dependency)):
        return service.status(current)

    @app.post('/v1/identity/vk/link')
    def provider_link(body: ProviderLinkRequest, current=Depends(actor_dependency)):
        return service.begin(current, body)

    @app.post('/v1/identity/vk/flows/{flow_id}/cancel')
    def provider_cancel(flow_id: str, current=Depends(actor_dependency)):
        if not re.fullmatch(r'[0-9a-f]{32}', flow_id):
            raise ServiceError(422, 'invalid_request')
        return service.cancel(current, flow_id)

    @app.get('/v1/identity/vk/callback')
    def provider_callback(request: Request, state: str = Query('', max_length=43), code: str = Query('', max_length=4096),
                          device_id: str = Query('', max_length=512), error: str = Query('', max_length=256)):
        for key in ('state', 'code', 'device_id', 'error'):
            if len(request.query_params.getlist(key)) > 1:
                raise ServiceError(400, 'vk_callback_invalid')
        signin = False
        if signin_service is not None and re.fullmatch(r'[A-Za-z0-9_-]{43}', state):
            with service.database.connect() as db:
                signin = bool(db.execute('SELECT 1 FROM account_provider_signins WHERE state_digest=?',
                                         (hashlib.sha256(state.encode('ascii')).hexdigest(),)).fetchone())
        phase = (signin_service if signin else service).callback(state, code, device_id, error)
        message = ('Подтвердите вход в игре.' if signin and phase == 'Ready' else
                   'Аккаунт VK подключён. Вернитесь в игру.' if phase in ('Linked', 'Completed') else
                   'Вход не завершён. Вернитесь в игру и повторите попытку.')
        return HTMLResponse('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Сердце дождя</title><p>' + message + '</p></html>',
                            headers={'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'", 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store'})
