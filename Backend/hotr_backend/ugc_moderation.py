"""Manual profile/team UGC review, with no automatic censorship or grants."""
import hashlib
import re
import uuid

from .guards import require_actor
from .service import ServiceError
from .storage import canonical

MAX_NEW_REPORTS_PER_DAY = 20
SAFE_PROFILE_NAME = 'Rainkeeper'
SAFE_TEAM_NAME = 'Moderated team'


class UgcModeration:
    def __init__(self, authority, enabled=False):
        if type(enabled) is not bool:
            raise ValueError('Explicit UGC activation required')
        self.authority, self.database, self.enabled = authority, authority.database, enabled

    def _guard(self, db, actor):
        require_actor(db, actor)
        if not self.enabled:
            raise ServiceError(503, 'social_not_configured')

    def _moderator(self, db, actor):
        self._guard(db, actor)
        if actor.credential_digest is None or not db.execute(
            'SELECT 1 FROM social_moderators WHERE credential_digest=?', (actor.credential_digest,)).fetchone():
            raise ServiceError(403, 'moderator_required')

    @staticmethod
    def _target(db, kind, target):
        if not isinstance(target, str) or not re.fullmatch('[0-9a-f]{32}', target):
            raise ServiceError(404, 'ugc_target_not_found')
        if kind == 'Profile':
            row = db.execute('''SELECT p.id AS owner_id,COALESCE(s.display_name,'Rainkeeper') AS name,'' AS description
                FROM players p LEFT JOIN social_profiles s ON s.player_id=p.id
                LEFT JOIN account_states a ON a.player_id=p.id
                WHERE p.id=? AND COALESCE(a.state,'Active')='Active' ''', (target,)).fetchone()
        elif kind == 'Team':
            row = db.execute('''SELECT t.owner_id,t.name,t.description FROM social_teams t
                LEFT JOIN account_states a ON a.player_id=t.owner_id
                WHERE t.id=? AND t.active=1 AND COALESCE(a.state,'Active')='Active' ''', (target,)).fetchone()
        else:
            raise ServiceError(422, 'invalid_ugc_kind')
        if not row:
            raise ServiceError(404, 'ugc_target_not_found')
        return row

    def report(self, actor, request):
        def run(db):
            self._guard(db, actor)
            def execute():
                # A block is a safety control, not an obstacle to filing a
                # metadata-only report for an exact known public target ID.
                target = self._target(db, request.kind, request.targetId)
                if target['owner_id'] == actor.player:
                    raise ServiceError(409, 'cannot_report_own_content')
                content = hashlib.sha256(canonical([target['name'], target['description']]).encode()).hexdigest()
                old = db.execute('SELECT * FROM social_ugc_reports WHERE reporter_id=? AND kind=? AND target_id=?',
                                 (actor.player, request.kind, request.targetId)).fetchone()
                if old:
                    identity = old['id']
                    reopened = old['state'] != 'Open' and old['content_digest'] != content
                    pending = old['state'] == 'Open' or reopened
                    if reopened:
                        db.execute("UPDATE social_ugc_reports SET reason=?,details=?,content_digest=?,state='Open',updated_at=? WHERE id=?",
                                   (request.reason, request.details, content, actor.now, identity))
                else:
                    pending = True
                    count = db.execute('SELECT COUNT(*) FROM social_ugc_reports WHERE reporter_id=? AND created_at>?',
                                       (actor.player, actor.now - 86400)).fetchone()[0]
                    if count >= MAX_NEW_REPORTS_PER_DAY:
                        raise ServiceError(429, 'ugc_report_rate_limited')
                    identity = uuid.uuid4().hex
                    db.execute("INSERT INTO social_ugc_reports VALUES(?,?,?,?,?,?,?,'Open',?,?)",
                               (identity, actor.player, request.kind, request.targetId, request.reason, request.details,
                                content, actor.now, actor.now))
                return {'reportId': identity, 'state': 'Received', 'reviewPendingAtAcceptance': pending,
                        'automatedDecision': False, 'receiptScope': 'immutable_submission_receipt'}
            # Cached receipt contains only reporter-owned metadata, not current
            # target text or moderation disposition. Actor revocation still wins.
            return self.authority._command(db, actor, 'social.ugc.report', request.commandId, request.model_dump(), execute)
        return self.authority._transaction(run)

    def queue(self, actor, after='', limit=50):
        if (not isinstance(after, str) or after and not re.fullmatch('[0-9a-f]{32}', after)
                or type(limit) is not int or not 1 <= limit <= 100):
            raise ServiceError(422, 'invalid_ugc_page')
        with self.database.transaction() as db:
            self._moderator(db, actor)
            # Filter retained/deleted targets before LIMIT, so a page remains
            # bounded even when old audit rows precede the next visible report.
            rows = db.execute('''SELECT r.* FROM social_ugc_reports r
                LEFT JOIN players p ON r.kind='Profile' AND p.id=r.target_id
                LEFT JOIN account_states pa ON pa.player_id=p.id
                LEFT JOIN social_teams t ON r.kind='Team' AND t.id=r.target_id
                LEFT JOIN account_states ta ON ta.player_id=t.owner_id
                WHERE r.state='Open' AND r.id>? AND (
                    (r.kind='Profile' AND p.id IS NOT NULL AND COALESCE(pa.state,'Active')='Active') OR
                    (r.kind='Team' AND t.id IS NOT NULL AND t.active=1 AND COALESCE(ta.state,'Active')='Active'))
                ORDER BY r.id LIMIT ?''', (after, limit + 1)).fetchall()
            visible = []
            for row in rows:
                try:
                    target = self._target(db, row['kind'], row['target_id'])
                except ServiceError as error:
                    if error.status == 404:
                        continue
                    raise
                visible.append({'reportId': row['id'], 'kind': row['kind'], 'targetId': row['target_id'],
                                'reason': row['reason'], 'details': row['details'],
                                'name': target['name'], 'description': target['description'], 'state': 'Open'})
                if len(visible) > limit:
                    break
            page = visible[:limit]
            return {'reports': page, 'nextCursor': page[-1]['reportId'] if page else after,
                    'hasMore': len(visible) > limit, 'reviewSource': 'operator_human_review'}

    def moderate(self, actor, request):
        if (request.action == 'ResetProfileName' and request.kind != 'Profile'
                or request.action == 'ResetTeamText' and request.kind != 'Team'):
            raise ServiceError(422, 'ugc_action_target_mismatch')
        def run(db):
            self._moderator(db, actor)  # Also before cached receipt; no stale staff grant bypass.
            self._target(db, request.kind, request.targetId)
            def execute():
                if request.action == 'ResetProfileName':
                    db.execute('''INSERT INTO social_profiles VALUES(?,?,0,?,?) ON CONFLICT(player_id)
                        DO UPDATE SET display_name=excluded.display_name,updated_at=excluded.updated_at''',
                               (request.targetId, SAFE_PROFILE_NAME, actor.now, actor.now))
                elif request.action == 'ResetTeamText':
                    db.execute('UPDATE social_teams SET name=?,description=?,updated_at=? WHERE id=?',
                               (SAFE_TEAM_NAME, '', actor.now, request.targetId))
                state = 'Dismissed' if request.action == 'DismissReports' else 'Resolved'
                db.execute("UPDATE social_ugc_reports SET state=?,updated_at=? WHERE kind=? AND target_id=? AND state='Open'",
                           (state, actor.now, request.kind, request.targetId))
                identity = uuid.uuid4().hex
                db.execute('INSERT INTO social_ugc_actions VALUES(?,?,?,?,?,?,?)',
                           (identity, actor.player, request.kind, request.targetId, request.action, request.reason, actor.now))
                return {'actionId': identity, 'kind': request.kind, 'targetId': request.targetId, 'action': request.action}
            return self.authority._command(db, actor, 'social.ugc.moderate', request.commandId, request.model_dump(), execute)
        return self.authority._transaction(run)
