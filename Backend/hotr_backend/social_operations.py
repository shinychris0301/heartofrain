"""Owner-only recovery of minimal durable social command receipts.

This is not a generic commands-table export. An absent receipt says only that no
matching committed command is visible in this transaction; it never asserts that
a concurrent request failed. Payload digests describe normalized server models,
not the bytes of an arbitrary client's JSON serializer.
"""
import json
import re

from .guards import require_actor
from .service import ServiceError


_ID = re.compile(r'[0-9a-f]{32}\Z')
_DIGEST = re.compile(r'[0-9a-f]{64}\Z')
_STATIC = frozenset((
    'social.profile', 'social.profile.name', 'social.profile.consent', 'social.friend.send', 'social.friend.respond',
    'social.friend.remove', 'social.block', 'social.unblock',
    'social.team.create', 'social.report', 'social.ugc.report', 'social.region.set',
))
_TEAM = re.compile(r'social\.team\.(join|leave|transfer|kick|unban)/[0-9a-f]{32}\Z')
_LIFE = re.compile(r'social\.life\.(request/[0-9a-f]{32}|help/[0-9a-f]{32}/[0-9a-f]{32}|claim/[0-9a-f]{32})\Z')
_MAIL = re.compile(r'social\.mail\.(?:(?:read|claim)/[0-9a-f]{32}/[0-9a-f]{32}|claim-owned/[0-9a-f]{32})\Z')
_INVITE = re.compile(r'social\.invite\.send/[0-9a-f]{32}/[0-9a-f]{32}\Z')
_MESSAGE = re.compile(r'social\.message\.(send|read)/(Direct|Team)/[0-9a-f]{32}\Z')


def allowed_operation(value):
    return isinstance(value, str) and len(value) <= 128 and (
        value in _STATIC or _TEAM.fullmatch(value) is not None or _MESSAGE.fullmatch(value) is not None or _LIFE.fullmatch(value) is not None or _MAIL.fullmatch(value) is not None or _INVITE.fullmatch(value) is not None)


def _minimal_response(operation, value):
    if not isinstance(value, dict):
        raise ServiceError(503, 'social_receipt_unavailable')
    if operation.startswith('social.invite.send/'):
        fields = ('receiptId','operation','teamId','friendId','inviteId','state','createdAtUtc','expiresAtUtc','serverUtc')
    elif operation.startswith('social.mail.read/'):
        fields = ('receiptId','operation','teamId','messageId','readAtUtc','serverUtc')
    elif operation.startswith(('social.mail.claim/', 'social.mail.claim-owned/')):
        fields = ('receiptId','operation','teamId','messageId','state','serverUtc','rewardCoins','rewardLives','walletRevision','coins','lives','maxLives','nextLifeAt')
    elif operation.startswith('social.life.'):
        fields = ('receiptId','operation','teamId','requestId','messageId','eventId','state','createdAt','serverUtc','creditedLives','received','claimed','remaining')
        if operation.startswith('social.life.claim/'):
            fields += ('walletRevision','lives','maxLives','nextLifeAt')
    elif operation in ('social.profile', 'social.profile.name', 'social.profile.consent'):
        fields = ('playerId', 'displayName', 'completedLevels', 'leaderboardOptIn')
    elif operation == 'social.region.set':
        fields = ('playerId', 'regionCode', 'regionSource', 'locationVerified')
    elif operation.startswith('social.friend.'):
        fields = ('playerId', 'state') + (('requestId',) if 'requestId' in value else ())
    elif operation in ('social.block', 'social.unblock'):
        fields = ('playerId', 'blocked')
    elif operation == 'social.team.create' or operation.startswith(('social.team.join/', 'social.team.leave/')):
        fields = ('teamId', 'state')
        if operation.startswith('social.team.leave/') and value.get('state') == 'Rejected':
            fields += ('reason',)
    elif operation.startswith('social.team.'):
        fields = ('teamId', 'playerId', 'action')
    elif operation.startswith('social.message.send/'):
        fields = ('messageId', 'sequence', 'createdAt', 'state')
    elif operation.startswith('social.message.read/'):
        fields = ('through',)
    elif operation == 'social.report':
        fields = ('reportId', 'state')
    elif operation == 'social.ugc.report':
        fields = ('reportId', 'state', 'reviewPendingAtAcceptance', 'automatedDecision', 'receiptScope')
    else:
        raise ServiceError(422, 'invalid_social_operation')
    if any(field not in value for field in fields):
        raise ServiceError(503, 'social_receipt_unavailable')
    return {field: value[field] for field in fields}


class SocialOperations:
    def __init__(self, authority, enabled=False):
        if type(enabled) is not bool:
            raise ValueError('Explicit social configuration required')
        self.authority, self.database, self.enabled = authority, authority.database, enabled

    def get(self, actor, command_id, operation):
        if not isinstance(command_id, str) or _ID.fullmatch(command_id) is None or not allowed_operation(operation):
            raise ServiceError(422, 'invalid_social_operation')
        with self.database.transaction() as db:
            require_actor(db, actor)
            if not self.enabled:
                raise ServiceError(503, 'social_not_configured')
            # Recovery is a managed/ordinary owner request, never an implicit
            # operator, verifier, or detached background-worker capability.
            digest = getattr(actor, 'credential_digest', None)
            credential = db.execute('SELECT role FROM credentials WHERE digest=?', (digest,)).fetchone() if digest else None
            if credential is None or credential['role'] != 'player':
                raise ServiceError(403, 'social_owner_required')
            row = db.execute('SELECT payload_digest,response_json FROM commands WHERE player_id=? AND operation=? AND command_id=?',
                             (actor.player, operation, command_id)).fetchone()
            result = {'commandId': command_id, 'operation': operation, 'status': 'Absent', 'receiptScope': 'owner_operation_receipt'}
            if row is None:
                return result
            if _DIGEST.fullmatch(row['payload_digest']) is None or len(row['response_json'].encode('utf-8')) > 65536:
                raise ServiceError(503, 'social_receipt_unavailable')
            try:
                response = _minimal_response(operation, json.loads(row['response_json']))
            except (ValueError, TypeError, OverflowError):
                raise ServiceError(503, 'social_receipt_unavailable') from None
            result.update(status='Committed', payloadDigest=row['payload_digest'], response=response,
                          digestScope='server_normalized_model_not_client_json')
            return result
