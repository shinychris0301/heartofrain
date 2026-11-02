"""Device-bound VK registration and explicit existing-account sign-in.

The OAuth callback prepares a target only. A fresh device key must prove the
durable app intent and confirm that exact target before any session is minted.
No wallet is imported, copied, merged, initialized or rewarded by this service.
"""
import hashlib
import hmac
import re
import secrets

from fastapi import Depends, Request
from pydantic import Field

from .guards import require_actor, require_active_player
from .identity import _digest, _key
from .identity_schemas import PUBLIC_KEY_MAX, SECRET_PATTERN, SignedRequest
from .schemas import Digest, Id, Model
from .service import ServiceError


class VkSigninRequest102(Model):
    requestId: Id
    publicKey: str = Field(min_length=64, max_length=PUBLIC_KEY_MAX)
    completionDigest: Digest


class VkCompleteRequest102(SignedRequest):
    flowId: Id
    targetPlayerId: Id
    flowSecret: str = Field(pattern=SECRET_PATTERN)
    refreshToken: str = Field(pattern=SECRET_PATTERN)
    confirmed: bool


class ProviderSignin102:
    def __init__(self, identity, linking):
        self.identity, self.linking = identity, linking
        self.database, self.authority = identity.database, identity.authority
        self.configuration, self.provider = linking.configuration, linking.provider

    @property
    def enabled(self):
        return self.identity.enabled and self.configuration.enabled

    def _enabled(self):
        if not self.enabled:
            raise ServiceError(503, 'vk_provider_not_configured')

    @staticmethod
    def _expire(db, now):
        db.execute("""UPDATE account_provider_signins SET phase='Expired',state_secret='',verifier='',subject_digest='',target_player=NULL,updated_at=?
            WHERE phase IN ('Pending','Exchanging','Ready') AND expires_at<=?""", (now, now))

    @staticmethod
    def _family(db, family_id, player, fingerprint, now):
        require_active_player(db, player)
        family = db.execute('SELECT * FROM identity_sessions WHERE id=?', (family_id,)).fetchone()
        device = db.execute('SELECT * FROM identity_devices WHERE fingerprint=?', (fingerprint,)).fetchone()
        refresh = db.execute('SELECT expires_at FROM identity_refresh WHERE digest=?',
                             (family['current_refresh_digest'],)).fetchone() if family else None
        if (not family or family['player_id'] != player or family['key_fingerprint'] != fingerprint
                or family['revoked'] or family['absolute_expires_at'] <= now
                or not device or device['player_id'] != player or device['revoked']
                or not refresh or refresh['expires_at'] <= now):
            raise ServiceError(401, 'vk_signin_source_closed')
        return family

    def _source(self, db, flow, now, actor=None):
        family = self._family(db, flow['source_family'], flow['source_player'], flow['source_fingerprint'], now)
        if actor is not None:
            require_actor(db, actor)
            access = db.execute('SELECT family_id FROM identity_access WHERE digest=?',
                                (actor.credential_digest,)).fetchone()
            if actor.player != flow['source_player'] or not access or access['family_id'] != family['id']:
                raise ServiceError(404, 'vk_signin_not_found')
        return family

    @staticmethod
    def _idle_source(db, player):
        if db.execute("SELECT 1 FROM gameplay_attempts WHERE player_id=? AND state IN ('Reserved','Started','AwaitingContinuation')", (player,)).fetchone():
            raise ServiceError(409, 'vk_signin_attempt_active')

    def _view(self, flow, now):
        target = (flow['target_player'] or '') if flow['phase'] in ('Ready', 'Completed') else ''
        value = dict(playerId=flow['source_player'], provider='vk', available=self.enabled,
                     phase=flow['phase'], flowId=flow['id'], requestId=flow['request_id'],
                     expiresAt=flow['expires_at'], serverUtc=now, authorizeUrl='',
                     targetPlayerId=target,
                     requiresConfirmation=bool(target and target != flow['source_player']))
        if flow['phase'] == 'Pending' and flow['configuration_digest'] == self.configuration.fingerprint:
            value['authorizeUrl'] = self.provider.authorize_url(flow['state_secret'], flow['verifier'])
        return value

    def _reconcile_ready(self, db, flow, now):
        # A failed explicit completion must be recoverable by an authenticated
        # source read. Never select a replacement target after confirmation.
        if flow['phase'] != 'Ready':
            return flow
        phase = None
        if not self.enabled or flow['configuration_digest'] != self.configuration.fingerprint:
            phase = 'Failed'
        else:
            target = flow['target_player']
            state = db.execute('SELECT state FROM account_states WHERE player_id=?', (target,)).fetchone()
            if not target or state and state['state'] != 'Active':
                phase = 'Failed'
            else:
                owner = db.execute("SELECT player_id FROM account_provider_links WHERE provider='vk' AND subject_digest=?", (flow['subject_digest'],)).fetchone()
                existing = db.execute("SELECT subject_digest FROM account_provider_links WHERE provider='vk' AND player_id=?", (target,)).fetchone()
                if (owner and owner['player_id'] != target
                        or existing and existing['subject_digest'] != flow['subject_digest']
                        or not owner and target != flow['source_player']):
                    phase = 'Conflict'
        if phase is not None:
            db.execute("""UPDATE account_provider_signins SET phase=?,subject_digest='',target_player=NULL,
                state_secret='',verifier='',updated_at=? WHERE id=? AND phase='Ready'""", (phase, now, flow['id']))
            return db.execute('SELECT * FROM account_provider_signins WHERE id=?', (flow['id'],)).fetchone()
        return flow

    def begin(self, actor, request):
        self._enabled()
        _, fingerprint = _key(request.publicKey)
        with self.database.transaction() as db:
            now = self.identity._now(db, actor.now)
            require_actor(db, actor)
            self._expire(db, now)
            access = db.execute('SELECT family_id FROM identity_access WHERE digest=?', (actor.credential_digest,)).fetchone()
            family = db.execute('SELECT * FROM identity_sessions WHERE id=?', (access['family_id'],)).fetchone() if access else None
            if not family:
                raise ServiceError(403, 'vk_signin_managed_account_required')
            self._family(db, family['id'], actor.player, family['key_fingerprint'], now)
            old = db.execute('SELECT * FROM account_provider_signins WHERE id=?', (request.requestId,)).fetchone()
            if old:
                self._source(db, old, now, actor)
                if (old['public_key'] != request.publicKey or old['completion_digest'] != request.completionDigest
                        or old['configuration_digest'] != self.configuration.fingerprint):
                    raise ServiceError(409, 'vk_signin_request_conflict')
                return self._view(old, now)
            self._idle_source(db, actor.player)
            if db.execute('SELECT 1 FROM identity_devices WHERE fingerprint=?', (fingerprint,)).fetchone():
                raise ServiceError(409, 'vk_signin_fresh_device_key_required')
            if db.execute("SELECT 1 FROM account_provider_signins WHERE source_player=? AND phase IN ('Pending','Exchanging','Ready')", (actor.player,)).fetchone():
                raise ServiceError(409, 'vk_signin_pending')
            if db.execute('SELECT COUNT(*) FROM account_provider_signins WHERE source_player=? AND created_at>?', (actor.player, now - 3600)).fetchone()[0] >= 8:
                raise ServiceError(429, 'vk_signin_rate_limited')
            if db.execute("SELECT COUNT(*) FROM account_provider_signins WHERE phase IN ('Pending','Exchanging','Ready')").fetchone()[0] >= 10000:
                raise ServiceError(503, 'vk_signin_capacity')
            state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
            db.execute('''INSERT INTO account_provider_signins
                (id,source_player,source_family,source_fingerprint,request_id,public_key,key_fingerprint,completion_digest,
                 configuration_digest,state_digest,state_secret,verifier,phase,expires_at,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'Pending',?,?,?)''',
                (request.requestId, actor.player, family['id'], family['key_fingerprint'], request.requestId,
                 request.publicKey, fingerprint, request.completionDigest, self.configuration.fingerprint,
                 _digest(state), state, verifier, now + 600, now, now))
            return self._view(db.execute('SELECT * FROM account_provider_signins WHERE id=?', (request.requestId,)).fetchone(), now)

    def status(self, actor, flow_id):
        with self.database.transaction() as db:
            now = self.identity._now(db, actor.now)
            self._expire(db, now)
            flow = db.execute('SELECT * FROM account_provider_signins WHERE id=?', (flow_id,)).fetchone()
            if not flow:
                raise ServiceError(404, 'vk_signin_not_found')
            self._source(db, flow, now, actor)
            flow = self._reconcile_ready(db, flow, now)
            return self._view(flow, now)

    def cancel(self, actor, flow_id):
        with self.database.transaction() as db:
            now = self.identity._now(db, actor.now)
            flow = db.execute('SELECT * FROM account_provider_signins WHERE id=?', (flow_id,)).fetchone()
            if not flow:
                raise ServiceError(404, 'vk_signin_not_found')
            self._source(db, flow, now, actor)
            db.execute("""UPDATE account_provider_signins SET phase='Cancelled',state_secret='',verifier='',subject_digest='',target_player=NULL,updated_at=?
                WHERE id=? AND phase IN ('Pending','Exchanging','Ready')""", (now, flow_id))
            return self._view(db.execute('SELECT * FROM account_provider_signins WHERE id=?', (flow_id,)).fetchone(), now)

    def callback(self, state, code='', device_id='', error=''):
        self._enabled()
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', state):
            raise ServiceError(400, 'vk_callback_invalid')
        with self.database.transaction() as db:
            now = self.identity._now(db)
            self._expire(db, now)
            flow = db.execute('SELECT * FROM account_provider_signins WHERE state_digest=?', (_digest(state),)).fetchone()
            if not flow or flow['configuration_digest'] != self.configuration.fingerprint:
                raise ServiceError(400, 'vk_callback_invalid')
            self._source(db, flow, now)
            if flow['phase'] in ('Ready','Completed','Cancelled','Failed','Expired','Conflict'):
                return flow['phase']
            if flow['phase'] != 'Pending':
                raise ServiceError(409, 'vk_callback_pending')
            if error:
                db.execute("UPDATE account_provider_signins SET phase='Cancelled',state_secret='',verifier='',updated_at=? WHERE id=?", (now, flow['id']))
                return 'Cancelled'
            if not 1 <= len(code) <= 4096 or not 1 <= len(device_id) <= 512 or any(ord(c) < 32 for c in code + device_id):
                raise ServiceError(400, 'vk_callback_invalid')
            db.execute("UPDATE account_provider_signins SET phase='Exchanging',updated_at=? WHERE id=?", (now, flow['id']))
            flow = dict(flow)
        try:
            subject = self.provider.verify(code, device_id, state, flow['verifier'])
            if not re.fullmatch(r'[0-9a-f]{64}', subject):
                raise ServiceError(502, 'vk_provider_identity_invalid')
        except ServiceError:
            with self.database.transaction() as db:
                now = self.identity._now(db)
                db.execute("UPDATE account_provider_signins SET phase='Failed',state_secret='',verifier='',updated_at=? WHERE id=? AND phase='Exchanging'", (now, flow['id']))
            return 'Failed'
        with self.database.transaction() as db:
            now = self.identity._now(db)
            current = db.execute('SELECT * FROM account_provider_signins WHERE id=?', (flow['id'],)).fetchone()
            if not current:
                raise ServiceError(410, 'vk_signin_not_found')
            self._source(db, current, now)
            if current['phase'] != 'Exchanging':
                return current['phase']
            phase, target = ('Expired', None) if current['expires_at'] <= now else ('Ready', flow['source_player'])
            if phase == 'Ready':
                owner = db.execute("SELECT player_id FROM account_provider_links WHERE provider='vk' AND subject_digest=?", (subject,)).fetchone()
                existing = db.execute("SELECT subject_digest FROM account_provider_links WHERE provider='vk' AND player_id=?", (flow['source_player'],)).fetchone()
                if owner:
                    require_active_player(db, owner['player_id'])
                    target = owner['player_id']
                elif existing and existing['subject_digest'] != subject:
                    phase, target = 'Conflict', None
            db.execute("""UPDATE account_provider_signins SET phase=?,subject_digest=?,target_player=?,state_secret='',verifier='',updated_at=? WHERE id=?""",
                       (phase, subject if phase == 'Ready' else '', target, now, flow['id']))
            return phase

    def complete(self, request, source_key=None):
        started_at = self.identity._start(source_key)
        if not request.confirmed or request.requestId != request.flowId:
            raise ServiceError(422, 'vk_signin_confirmation_required')
        refresh, proof = _digest(request.refreshToken), _digest(request.flowSecret)
        if refresh == proof:
            raise ServiceError(422, 'independent_identity_secrets_required')
        def run(db):
            now = self.identity._now(db, started_at)
            fingerprint, digest, old = self.identity._proof(db, request, 'vk', now)
            if old:
                if old['player_id'] != request.targetPlayerId:
                    raise ServiceError(409, 'vk_signin_target_changed')
                return self.identity._resume(db, old, request, refresh, now)
            self._enabled()
            flow = db.execute('SELECT * FROM account_provider_signins WHERE id=?', (request.flowId,)).fetchone()
            if (not flow or flow['public_key'] != request.publicKey or flow['key_fingerprint'] != fingerprint
                    or not hmac.compare_digest(flow['completion_digest'], proof)
                    or flow['configuration_digest'] != self.configuration.fingerprint):
                raise ServiceError(401, 'vk_signin_proof_invalid')
            self._source(db, flow, now)
            if flow['phase'] != 'Ready' or flow['expires_at'] <= now:
                raise ServiceError(409, 'vk_signin_not_ready')
            if flow['target_player'] != request.targetPlayerId:
                raise ServiceError(409, 'vk_signin_target_changed')
            self._idle_source(db, flow['source_player'])
            require_active_player(db, request.targetPlayerId)
            if db.execute('SELECT 1 FROM identity_devices WHERE fingerprint=?', (fingerprint,)).fetchone():
                raise ServiceError(409, 'vk_signin_fresh_device_key_required')
            owner = db.execute("SELECT player_id FROM account_provider_links WHERE provider='vk' AND subject_digest=?", (flow['subject_digest'],)).fetchone()
            existing = db.execute("SELECT subject_digest FROM account_provider_links WHERE provider='vk' AND player_id=?", (request.targetPlayerId,)).fetchone()
            if (owner and owner['player_id'] != request.targetPlayerId
                    or existing and existing['subject_digest'] != flow['subject_digest']
                    or not owner and request.targetPlayerId != flow['source_player']):
                raise ServiceError(409, 'vk_signin_target_changed')
            db.execute("INSERT OR IGNORE INTO account_provider_links VALUES('vk',?,?,?)", (flow['subject_digest'], request.targetPlayerId, now))
            db.execute('INSERT INTO identity_devices VALUES(?,?,?,0,?)', (fingerprint, request.targetPlayerId, request.publicKey, now))
            family = self.identity._new_family(db, request.targetPlayerId, fingerprint, refresh, now)
            self.identity._record(db, request, 'vk', fingerprint, digest, request.targetPlayerId, family['id'], {'state':'Active'}, now)
            self.identity._consume(db, request, now)
            db.execute("UPDATE account_provider_signins SET phase='Completed',updated_at=? WHERE id=?", (now, flow['id']))
            return self.identity._access(db, family, request, now, False)
        return self.identity._transaction(run)


def register_signin_routes102(app, service, actor_dependency, source_resolver=None):
    def flow_id(value):
        if not re.fullmatch(r'[0-9a-f]{32}', value):
            raise ServiceError(422, 'invalid_request')
        return value

    @app.post('/v1/identity/vk/signin')
    def begin(body: VkSigninRequest102, current=Depends(actor_dependency)):
        return service.begin(current, body)

    @app.get('/v1/identity/vk/signin/{identifier}')
    def status(identifier: str, current=Depends(actor_dependency)):
        return service.status(current, flow_id(identifier))

    @app.post('/v1/identity/vk/signin/{identifier}/cancel')
    def cancel(identifier: str, current=Depends(actor_dependency)):
        return service.cancel(current, flow_id(identifier))

    @app.post('/v1/identity/vk/complete')
    def complete(body: VkCompleteRequest102, request: Request):
        source = source_resolver(request) if source_resolver is not None else request.client.host if request.client else 'unknown'
        return service.complete(body, source_key=source)
