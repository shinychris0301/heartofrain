"""Opt-in managed staging guests with device proof and hash-only recovery.

This is a bounded application protocol, not an OAuth/DPoP certification or a
hardware-attestation service. Short access tokens are bearer credentials. An
independent high-entropy recovery secret is essential if the device key is lost.
The ordinary Unity profile is never read, imported, reset or selected here.
"""
import base64
import hashlib
import hmac
import json
import secrets
import uuid

from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS

PROTOCOL = 'hotr-managed-identity-v1'
CHALLENGE_SECONDS = 60
ACCESS_SECONDS = 900
# A rotated access token stays valid this long so requests already in flight
# finish normally. Logout, deletion and refresh reuse still revoke immediately.
ACCESS_RENEWAL_GRACE_SECONDS = 30
REFRESH_IDLE_SECONDS = 30 * 86400
SESSION_MAX_SECONDS = 90 * 86400
MAX_OUTSTANDING_CHALLENGES = 1024
CHALLENGES_PER_SOURCE = 60
CHALLENGES_GLOBAL = 6000
RENEWALS_PER_SOURCE = 600
OPERATIONS_PER_SOURCE = 120
OPERATIONS_GLOBAL = 24000

from .identity_schema import IDENTITY_V4_DDL
from .production_runtime122 import production_enabled



def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _digest(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def _error(status, code):
    # Lazy import avoids service -> identity -> service initialization cycles.
    from .service import ServiceError
    return ServiceError(status, code)


def _key(public):
    try:
        encoded = base64.b64decode(public, validate=True)
        key = ECC.import_key(encoded)
        if (key.has_private() or key.curve != 'NIST P-256'
                or key.export_key(format='DER') != encoded
                or base64.b64encode(encoded).decode('ascii') != public):
            raise ValueError('Noncanonical public key')
        return key, hashlib.sha256(encoded).hexdigest()
    except (ValueError, TypeError, IndexError):
        raise _error(422, 'invalid_device_key') from None


def request_payload(request, purpose):
    """Exact ASCII unsigned binding, shared with explicit client adapters.

    challengeId/signature are deliberately absent: a fresh challenge can prove
    the same immutable outbox operation after a lost response or process restart.
    Callers hash the canonical JSON bytes, never a JSON serializer's pretty text.
    """
    value = request if isinstance(request, dict) else request.model_dump()
    payload = {'protocol': PROTOCOL, 'purpose': purpose,
               'requestId': value['requestId'], 'publicKey': value['publicKey']}
    fields = {
        'guest': (('refreshToken', 'refreshDigest'), ('recoverySecret', 'recoveryDigest')),
        'session': (('refreshToken', 'refreshDigest'), ('replacementToken', 'replacementDigest')),
        'recover': (('recoverySecret', 'recoveryDigest'), ('replacementRecoverySecret', 'replacementRecoveryDigest'),
                    ('refreshToken', 'refreshDigest')),
        'logout': (('refreshToken', 'refreshDigest'),),
        'delete': (('refreshToken', 'refreshDigest'),),
        'vk': (('refreshToken', 'refreshDigest'), ('flowSecret', 'flowDigest')),
    }
    if purpose not in fields:
        raise ValueError('Unsupported identity purpose')
    if purpose in ('recover', 'delete'):
        payload['playerId'] = value['playerId']
    if purpose == 'vk':
        payload.update(flowId=value['flowId'], targetPlayerId=value['targetPlayerId'],
                       confirmed='true' if value['confirmed'] else 'false')
    payload.update((target, _digest(value[source])) for source, target in fields[purpose])
    return payload


def payload_digest(request, purpose):
    return _digest(_canonical(request_payload(request, purpose)))


def challenge_bytes(value):
    fields = {name: value[name] for name in ('challengeId', 'expiresAt', 'keyFingerprint',
                                             'nonce', 'payloadDigest', 'purpose', 'requestId')}
    return (PROTOCOL + '\n' + _canonical(fields)).encode('ascii')


class ManagedIdentity:
    def __init__(self, authority, enabled=False):
        self.authority, self.database, self.enabled = authority, authority.database, enabled
        self.checkpoint = None  # Only in-process BeforeCommit/AfterCommit fault tests.

    def _now(self, db, started_at=0):
        # Writer-lock waits must not extend a signed challenge or refresh token.
        # Use this transaction's current clock and committed high-water together;
        # Authority._now() would open a nested writer transaction here.
        try:
            sampled = int(self.authority.clock())
        except Exception:
            raise _error(503, 'clock_unavailable') from None
        if sampled < 0 or sampled > 253_402_300_799:
            raise _error(503, 'clock_unavailable')
        high_water = db.execute('SELECT high_water FROM clock_state WHERE id=1').fetchone()[0]
        now = max(started_at, sampled, high_water)
        if now != high_water:
            db.execute('UPDATE clock_state SET high_water=? WHERE id=1', (now,))
        return now

    def _start(self, source_key=None, challenge=False, renewal_key=None):
        if not self.enabled:
            raise _error(503, 'managed_identity_not_configured')
        # A separate committed budget survives failures in the following proof
        # transaction. Source comes from actual ASGI peer, never a request field.
        source = str(source_key if source_key is not None else 'internal')[:512]
        source_hash = hashlib.sha256(source.encode('utf-8')).hexdigest()
        budgets = (('challenge/source/' + source_hash, CHALLENGES_PER_SOURCE), ('challenge/global', CHALLENGES_GLOBAL)) if challenge else (
            ('operation/source/' + source_hash, OPERATIONS_PER_SOURCE), ('operation/global', OPERATIONS_GLOBAL))
        blocked = False
        with self.database.transaction() as db:
            now = self._now(db)
            window = now // 60
            db.execute('DELETE FROM identity_rate_windows WHERE window<?', (window - 1,))
            if renewal_key is not None:
                # Renewal by a registered device that is not revoked: a shared carrier address
                # or a return from an outage must not lock existing players out.
                try:
                    fingerprint = _key(renewal_key)[1]
                except Exception:
                    fingerprint = None
                known = fingerprint and db.execute('SELECT 1 FROM identity_devices WHERE fingerprint=? AND revoked=0', (fingerprint,)).fetchone()
                if known:
                    budgets = (('challenge/renewal/' + source_hash, RENEWALS_PER_SOURCE),)
            for bucket, limit in budgets:
                row = db.execute('SELECT requests FROM identity_rate_windows WHERE bucket=? AND window=?', (bucket, window)).fetchone()
                count = row['requests'] + 1 if row else 1
                db.execute('''INSERT INTO identity_rate_windows VALUES(?,?,?) ON CONFLICT(bucket,window)
                    DO UPDATE SET requests=excluded.requests''', (bucket, window, count))
                blocked |= count > limit
                if blocked:  # A source over its own limit stops spending the shared budget.
                    break
        if blocked:
            raise _error(429, 'identity_rate_limited')
        return now

    def _transaction(self, execute):
        with self.database.transaction() as db:
            result = execute(db)
            if self.checkpoint:
                self.checkpoint('BeforeCommit')
        if self.checkpoint:
            self.checkpoint('AfterCommit')
        return result

    @staticmethod
    def _active(db, player):
        from .guards import require_active_player
        require_active_player(db, player)

    def challenge(self, request, source_key=None):
        started_at = self._start(source_key, challenge=True,
                                 renewal_key=request.publicKey if request.purpose == 'session' else None)
        _, fingerprint = _key(request.publicKey)
        with self.database.transaction() as db:
            now = self._now(db, started_at)
            value = {'challengeId': uuid.uuid4().hex, 'purpose': request.purpose,
                     'requestId': request.requestId, 'keyFingerprint': fingerprint,
                     'payloadDigest': request.payloadDigest, 'nonce': secrets.token_urlsafe(32),
                     'expiresAt': now + CHALLENGE_SECONDS, 'serverUtc': now, 'algorithm': 'ES256-DER'}
            db.execute('DELETE FROM identity_challenges WHERE expires_at<=?', (now,))
            if db.execute('SELECT COUNT(*) FROM identity_challenges').fetchone()[0] >= MAX_OUTSTANDING_CHALLENGES:
                raise _error(503, 'identity_challenge_capacity')
            db.execute('INSERT INTO identity_challenges VALUES(?,?,?,?,?,?,?,?,0)',
                       (value['challengeId'], request.purpose, fingerprint, request.publicKey,
                        request.requestId, request.payloadDigest, value['nonce'], value['expiresAt']))
        value['signingBytes'] = base64.b64encode(challenge_bytes(value)).decode('ascii')
        return value

    @staticmethod
    def _operation(db, request, purpose, fingerprint, digest):
        old = db.execute('''SELECT * FROM identity_operations WHERE key_fingerprint=?
            AND purpose=? AND request_id=?''', (fingerprint, purpose, request.requestId)).fetchone()
        if old and not hmac.compare_digest(old['payload_digest'], digest):
            raise _error(409, 'identity_request_conflict')
        return old

    def _proof(self, db, request, purpose, now):
        key, fingerprint = _key(request.publicKey)
        digest = payload_digest(request, purpose)
        row = db.execute('SELECT * FROM identity_challenges WHERE id=?', (request.challengeId,)).fetchone()
        old = self._operation(db, request, purpose, fingerprint, digest)
        if (not row or row['expires_at'] <= now or row['purpose'] != purpose
                or row['key_fingerprint'] != fingerprint or row['public_key'] != request.publicKey
                or row['request_id'] != request.requestId or row['payload_digest'] != digest
                or row['consumed_at'] and not old):
            raise _error(401, 'invalid_identity_proof')
        value = {'challengeId': row['id'], 'purpose': row['purpose'], 'requestId': row['request_id'],
                 'keyFingerprint': fingerprint, 'payloadDigest': digest, 'nonce': row['nonce'], 'expiresAt': row['expires_at']}
        try:
            signature = base64.b64decode(request.signature, validate=True)
            if base64.b64encode(signature).decode('ascii') != request.signature:
                raise ValueError('Noncanonical signature')
            DSS.new(key, 'fips-186-3', encoding='der').verify(SHA256.new(challenge_bytes(value)), signature)
        except (ValueError, TypeError):
            raise _error(401, 'invalid_identity_proof') from None
        return fingerprint, digest, old

    @staticmethod
    def _consume(db, request, now):
        db.execute('UPDATE identity_challenges SET consumed_at=? WHERE id=?', (now, request.challengeId))

    @staticmethod
    def _record(db, request, purpose, fingerprint, digest, player, family, response, now):
        db.execute('INSERT INTO identity_operations VALUES(?,?,?,?,?,?,?,?)',
                   (fingerprint, purpose, request.requestId, digest, player, family, _canonical(response), now))

    @staticmethod
    def _revoke_family(db, family):
        db.execute('UPDATE identity_sessions SET revoked=1 WHERE id=?', (family,))
        db.execute('UPDATE credentials SET revoked=1 WHERE digest IN (SELECT digest FROM identity_access WHERE family_id=?)', (family,))

    @classmethod
    def _revoke_player(cls, db, player):
        db.execute('UPDATE identity_sessions SET revoked=1 WHERE player_id=?', (player,))
        db.execute("UPDATE credentials SET revoked=1 WHERE player_id=? AND role='player'", (player,))
        db.execute('UPDATE identity_devices SET revoked=1 WHERE player_id=?', (player,))

    def _family(self, db, refresh, fingerprint, now, actor=None, revoked=False, lapsed_ok=False):
        token = db.execute('SELECT * FROM identity_refresh WHERE digest=?', (refresh,)).fetchone()
        family = db.execute('SELECT * FROM identity_sessions WHERE id=?', (token['family_id'],)).fetchone() if token else None
        if (not family or family['key_fingerprint'] != fingerprint
                or actor is not None and actor.player != family['player_id']
                or not revoked and (family['revoked'] or not lapsed_ok and (family['absolute_expires_at'] <= now or token['expires_at'] <= now))):
            raise _error(401, 'invalid_identity_session')
        if not revoked:
            self._active(db, family['player_id'])
            device = db.execute('SELECT revoked FROM identity_devices WHERE fingerprint=?', (fingerprint,)).fetchone()
            if not device or device['revoked']:
                raise _error(401, 'invalid_identity_session')
        return token, family

    @staticmethod
    def _new_family(db, player, fingerprint, refresh, now):
        if db.execute('SELECT 1 FROM identity_refresh WHERE digest=?', (refresh,)).fetchone():
            raise _error(409, 'identity_secret_conflict')
        family = uuid.uuid4().hex
        db.execute('INSERT INTO identity_sessions VALUES(?,?,?,?,?,?,?,0)',
                   (family, player, fingerprint, refresh, now, now, now + SESSION_MAX_SECONDS))
        db.execute('INSERT INTO identity_refresh VALUES(?,?,?,NULL,NULL,NULL)', (refresh, family, now + REFRESH_IDLE_SECONDS))
        return db.execute('SELECT * FROM identity_sessions WHERE id=?', (family,)).fetchone()

    def _access(self, db, family, request, now, replayed):
        token = secrets.token_urlsafe(32)
        expires = min(now + ACCESS_SECONDS, family['absolute_expires_at'])
        digest = _digest(token)
        db.execute("INSERT INTO credentials VALUES(?,?,'player',?,0)", (digest, family['player_id'], expires))
        db.execute('INSERT INTO identity_access VALUES(?,?,?)', (digest, family['id'], now))
        refresh = db.execute('SELECT expires_at FROM identity_refresh WHERE digest=?', (family['current_refresh_digest'],)).fetchone()
        return {'playerId': family['player_id'], 'familyId': family['id'], 'keyFingerprint': family['key_fingerprint'],
                'accessToken': token, 'expiresAt': expires, 'refreshExpiresAt': refresh['expires_at'],
                'requestId': request.requestId, 'replayed': replayed, 'accountState': 'Active',
                'productionEnabled': production_enabled(self.authority), 'normalUnityProfileIntegrated': False}

    def _resume(self, db, old, request, refresh, now):
        _, family = self._family(db, refresh, old['key_fingerprint'], now)
        if old['family_id'] != family['id'] or family['current_refresh_digest'] != refresh:
            raise _error(409, 'identity_retry_superseded')
        self._consume(db, request, now)
        return self._access(db, family, request, now, True)

    def guest(self, request, source_key=None):
        started_at = self._start(source_key)
        refresh, recovery = _digest(request.refreshToken), _digest(request.recoverySecret)
        if refresh == recovery:
            raise _error(422, 'independent_identity_secrets_required')
        def run(db):
            now = self._now(db, started_at)
            fingerprint, digest, old = self._proof(db, request, 'guest', now)
            if old:
                return self._resume(db, old, request, refresh, now)
            existing = db.execute('SELECT * FROM identity_devices WHERE fingerprint=?', (fingerprint,)).fetchone()
            if existing:
                self._active(db, existing['player_id'])
                raise _error(409, 'device_already_registered')
            if (db.execute('SELECT 1 FROM identity_recovery WHERE digest=?', (recovery,)).fetchone()
                    or db.execute('SELECT 1 FROM identity_recovery_history WHERE digest=?', (recovery,)).fetchone()):
                raise _error(409, 'identity_secret_conflict')
            player = uuid.uuid4().hex
            db.execute('INSERT INTO players(id,reward_totals,created_at) VALUES(?,?,?)', (player, _canonical([0] * 10), now))
            db.execute("INSERT INTO account_states VALUES(?,'Active',0)", (player,))
            from .wallet import new_profile
            new_profile(db, player, now)
            db.execute('INSERT INTO identity_devices VALUES(?,?,?,0,?)', (fingerprint, player, request.publicKey, now))
            db.execute('INSERT INTO identity_recovery VALUES(?,?,?)', (player, recovery, now))
            family = self._new_family(db, player, fingerprint, refresh, now)
            self._record(db, request, 'guest', fingerprint, digest, player, family['id'], {'state': 'Active'}, now)
            self._consume(db, request, now)
            return self._access(db, family, request, now, False)
        return self._transaction(run)

    def session(self, request, source_key=None):
        started_at = self._start(source_key)
        refresh, replacement = _digest(request.refreshToken), _digest(request.replacementToken)
        if refresh == replacement:
            raise _error(422, 'new_refresh_secret_required')
        replay_error = False
        def run(db):
            nonlocal replay_error
            now = self._now(db, started_at)
            fingerprint, digest, old = self._proof(db, request, 'session', now)
            # The signature proves the registered device key, so age alone does not end a session:
            # a returning player renews with the family's current token, or repeats the renewal
            # whose reply was lost. Revocation and reuse of any other token stay final.
            token, family = self._family(db, refresh, fingerprint, now, lapsed_ok=True)
            current = family['current_refresh_digest']
            if ((family['absolute_expires_at'] <= now or token['expires_at'] <= now)
                    and current != refresh and not (old and token['replacement_digest'] == current)):
                raise _error(401, 'invalid_identity_session')
            db.execute('UPDATE identity_sessions SET absolute_expires_at=? WHERE id=?', (now + SESSION_MAX_SECONDS, family['id']))
            family = db.execute('SELECT * FROM identity_sessions WHERE id=?', (family['id'],)).fetchone()
            if old:
                if token['replacement_digest'] == current:
                    db.execute('UPDATE identity_refresh SET expires_at=MAX(expires_at,?) WHERE digest=?', (now + REFRESH_IDLE_SECONDS, current))
                return self._resume(db, old, request, replacement, now)
            if token['used_request_id'] is not None or family['current_refresh_digest'] != refresh:
                self._revoke_family(db, family['id'])
                self._consume(db, request, now)
                replay_error = True
                return None  # Commit revocation before returning the public error.
            if db.execute('SELECT 1 FROM identity_refresh WHERE digest=?', (replacement,)).fetchone():
                raise _error(409, 'identity_secret_conflict')
            expires = min(now + REFRESH_IDLE_SECONDS, family['absolute_expires_at'])
            db.execute('INSERT INTO identity_refresh VALUES(?,?,?,NULL,NULL,NULL)', (replacement, family['id'], expires))
            db.execute('UPDATE identity_refresh SET used_request_id=?,payload_digest=?,replacement_digest=? WHERE digest=?',
                       (request.requestId, digest, replacement, refresh))
            db.execute('UPDATE identity_sessions SET current_refresh_digest=?,last_used_at=? WHERE id=?', (replacement, now, family['id']))
            self._record(db, request, 'session', fingerprint, digest, family['player_id'], family['id'], {'state': 'Active'}, now)
            self._consume(db, request, now)
            self._retire_access(db, family['id'], now)
            return self._access(db, db.execute('SELECT * FROM identity_sessions WHERE id=?', (family['id'],)).fetchone(), request, now, False)
        value = self._transaction(run)
        if replay_error:
            raise _error(401, 'refresh_reuse_detected')
        return value

    @staticmethod
    def _retire_access(db, family, now):
        db.execute('UPDATE credentials SET expires_at=MIN(expires_at,?) WHERE digest IN (SELECT digest FROM identity_access WHERE family_id=?)',
                   (now + ACCESS_RENEWAL_GRACE_SECONDS, family))

    def recover(self, request, source_key=None):
        started_at = self._start(source_key)
        recovery, replacement, refresh = (_digest(request.recoverySecret), _digest(request.replacementRecoverySecret),
                                           _digest(request.refreshToken))
        if len({recovery, replacement, refresh}) != 3:
            raise _error(422, 'independent_identity_secrets_required')
        def run(db):
            now = self._now(db, started_at)
            fingerprint, digest, old = self._proof(db, request, 'recover', now)
            if old:
                if old['player_id'] != request.playerId:
                    raise _error(401, 'invalid_identity_recovery')
                return self._resume(db, old, request, refresh, now)
            self._active(db, request.playerId)
            row = db.execute('SELECT * FROM identity_recovery WHERE player_id=?', (request.playerId,)).fetchone()
            if not row or not hmac.compare_digest(row['digest'], recovery):
                raise _error(401, 'invalid_identity_recovery')
            if db.execute('SELECT 1 FROM identity_devices WHERE fingerprint=?', (fingerprint,)).fetchone():
                raise _error(409, 'recovery_requires_new_device_key')
            if (db.execute('SELECT 1 FROM identity_recovery WHERE digest=?', (replacement,)).fetchone()
                    or db.execute('SELECT 1 FROM identity_recovery_history WHERE digest=?', (replacement,)).fetchone()):
                raise _error(409, 'identity_secret_conflict')
            self._revoke_player(db, request.playerId)
            db.execute('INSERT INTO identity_devices VALUES(?,?,?,0,?)', (fingerprint, request.playerId, request.publicKey, now))
            db.execute('INSERT INTO identity_recovery_history VALUES(?,?,?,?,?,?)',
                       (recovery, request.playerId, request.requestId, digest, replacement, fingerprint))
            db.execute('UPDATE identity_recovery SET digest=?,updated_at=? WHERE player_id=?', (replacement, now, request.playerId))
            family = self._new_family(db, request.playerId, fingerprint, refresh, now)
            self._record(db, request, 'recover', fingerprint, digest, request.playerId, family['id'], {'state': 'Active'}, now)
            self._consume(db, request, now)
            return self._access(db, family, request, now, False)
        return self._transaction(run)

    def logout(self, actor, request, source_key=None):
        started_at = self._start(source_key)
        refresh = _digest(request.refreshToken)
        def run(db):
            now = self._now(db, started_at)
            fingerprint, digest, old = self._proof(db, request, 'logout', now)
            _, family = self._family(db, refresh, fingerprint, now, actor, revoked=bool(old))
            if old:
                self._consume(db, request, now)
                return json.loads(old['response_json'])
            if family['current_refresh_digest'] != refresh:
                raise _error(401, 'invalid_identity_session')
            self._revoke_family(db, family['id'])
            value = {'playerId': family['player_id'], 'familyId': family['id'], 'requestId': request.requestId, 'state': 'LoggedOut'}
            self._record(db, request, 'logout', fingerprint, digest, family['player_id'], family['id'], value, now)
            self._consume(db, request, now)
            return value
        return self._transaction(run)

    def deletion(self, actor, request, source_key=None):
        started_at = self._start(source_key)
        refresh = _digest(request.refreshToken)
        def run(db):
            now = self._now(db, started_at)
            fingerprint, digest, old = self._proof(db, request, 'delete', now)
            _, family = self._family(db, refresh, fingerprint, now, actor, revoked=bool(old))
            if family['player_id'] != request.playerId:
                raise _error(401, 'invalid_identity_session')
            if old:
                self._consume(db, request, now)
                return json.loads(old['response_json'])
            if family['current_refresh_digest'] != refresh:
                raise _error(401, 'invalid_identity_session')
            self._revoke_player(db, request.playerId)
            # Verifier credentials can share an operator-provisioned player ID;
            # revoke every role for the deleted account, not only guest access.
            db.execute('UPDATE credentials SET revoked=1 WHERE player_id=?', (request.playerId,))
            db.execute("""INSERT INTO account_states VALUES(?,'DeletionRequested',?) ON CONFLICT(player_id)
                DO UPDATE SET state='DeletionRequested',requested_at=excluded.requested_at""", (request.playerId, now))
            db.execute('DELETE FROM audit_events WHERE player_id=?', (request.playerId,))
            db.execute('DELETE FROM rate_windows WHERE credential IN (SELECT digest FROM credentials WHERE player_id=?)', (request.playerId,))
            db.execute('DELETE FROM identity_recovery WHERE player_id=?', (request.playerId,))
            # Remove optional country/provider identity data with the account.
            # Financial/security receipts retain their existing explicit policy.
            db.execute('DELETE FROM player_regions WHERE player_id=?', (request.playerId,))
            db.execute('DELETE FROM account_provider_links WHERE player_id=?', (request.playerId,))
            db.execute('DELETE FROM account_provider_flows WHERE player_id=?', (request.playerId,))
            # Other active sources need an authenticated terminal result to
            # abandon an uncommitted confirmation safely. Retain only an opaque
            # Cancelled intent, with every deleted-target/provider association
            # cleared. A completed operation's target credentials are revoked
            # above, but a response-lost source still needs a terminal result.
            # Historical identity-operation proofs remain revocation-checked.
            db.execute("""UPDATE account_provider_signins
                SET phase=CASE WHEN phase='Completed' THEN 'Failed' ELSE 'Cancelled' END,target_player=NULL,
                subject_digest='',state_secret='',verifier='',updated_at=?
                WHERE target_player=? AND source_player<>? AND phase IN ('Pending','Exchanging','Ready','Completed')""",
                       (now, request.playerId, request.playerId))
            db.execute('DELETE FROM account_provider_signins WHERE source_player=? OR target_player=?',
                       (request.playerId, request.playerId))
            db.execute('DELETE FROM rewarded_ad_calendars WHERE player_id=?', (request.playerId,))
            from .social_deletion import close_social_account
            close_social_account(db, request.playerId, now)
            value = {'playerId': request.playerId, 'requestId': request.requestId, 'state': 'DeletionRequested',
                     'requestedAt': now, 'sessionsRevoked': True, 'optionalDiagnosticsDeleted': True,
                     'retainedClasses': ['financial_audit_pending_policy', 'security_tombstone_and_retry_proof'],
                     'physicalPurgeComplete': False, 'retentionPolicyConfigured': False,
                     'normalUnityProfileIntegrated': False, 'localProfileMutated': False}
            self._record(db, request, 'delete', fingerprint, digest, request.playerId, family['id'], value, now)
            self._consume(db, request, now)
            return value
        return self._transaction(run)
