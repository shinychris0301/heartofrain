"""Durable text messaging and teams, with server permissions and moderation.

No push provider, media uploads, automated moderation decision or UI is implied.
Runtime activation is explicit. Moderator grants are operator-controlled rows,
never a client profile field or the financial verifier role.
"""
import hashlib
import re
import unicodedata
import uuid

from .friends import blocked, eligible_friend, require_social_peer
from .guards import require_actor
from .service import ServiceError


def text(value, maximum, *, empty=False, multiline=False):
    if not isinstance(value, str):
        raise ServiceError(422, 'invalid_text')
    if multiline:
        value = value.replace('\r\n', '\n')
    value = unicodedata.normalize('NFC', value).strip()
    # U+200D joins emoji such as a shrug with a gender sign. It is never allowed to be the whole text.
    if (not empty and not value.strip('\u200d')) or len(value) > maximum or any(
            (unicodedata.category(c).startswith('C') or unicodedata.category(c) in ('Zl', 'Zp')) and not (multiline and c in '\n\u200d') for c in value):
        raise ServiceError(422, 'invalid_text')
    return value


def team_query(value):
    """Literal NFC/casefold search; never wildcard syntax or a client region."""
    if not isinstance(value, str) or len(value) > 128 or any(
            unicodedata.category(c).startswith('C') or unicodedata.category(c) in ('Zl', 'Zp') for c in value):
        raise ServiceError(422, 'invalid_team_query')
    if len(value.encode('utf-16-le')) > 256:
        raise ServiceError(422, 'invalid_team_query')
    value = unicodedata.normalize('NFC', value.strip())
    if len(value) > 64:
        raise ServiceError(422, 'invalid_team_query')
    return unicodedata.normalize('NFC', value.casefold())


def identity(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{32}', value):
        raise ServiceError(422, 'invalid_request')
    return value


def seed_team_reads(db, player, team_id):
    """A new member's unread count starts at zero; the history stays readable."""
    latest = db.execute("SELECT MAX(sequence) FROM social_messages WHERE kind='Team' AND target_id=?", (team_id,)).fetchone()[0]
    if latest:
        db.execute('''INSERT INTO social_message_reads VALUES(?,'Team',?,?)
            ON CONFLICT(player_id,kind,target_id) DO UPDATE SET last_sequence=MAX(last_sequence,excluded.last_sequence)''',
            (player, team_id, latest))


def direct_channel(a, b):
    return hashlib.sha256((':'.join(sorted((a, b)))).encode('ascii')).hexdigest()


class Messaging:
    def __init__(self, authority, enabled=False, *, team_capacity=50, messages_per_minute=10):
        if type(enabled) is not bool or type(team_capacity) is not int or not 2 <= team_capacity <= 100 or type(messages_per_minute) is not int or not 1 <= messages_per_minute <= 60:
            raise ValueError('Explicit bounded social configuration required')
        self.authority, self.database, self.enabled = authority, authority.database, enabled
        self.capacity, self.rate = team_capacity, messages_per_minute

    def _guard(self, db, actor):
        require_actor(db, actor)
        if not self.enabled:
            raise ServiceError(503, 'social_not_configured')

    def _mutation(self, actor, operation, request, authorize, execute, *, payload=None):
        def run(db):
            self._guard(db, actor)
            authorize(db)
            return self.authority._command(db, actor, operation, request.commandId,
                                           request.model_dump() if payload is None else payload, lambda: execute(db))
        return self.authority._transaction(run)

    def _team(self, db, team_id):
        row = db.execute("SELECT t.* FROM social_teams t LEFT JOIN account_states a ON a.player_id=t.owner_id WHERE t.id=? AND t.active=1 AND COALESCE(a.state,'Active')='Active'", (identity(team_id),)).fetchone()
        if not row:
            raise ServiceError(404, 'team_not_found')
        return row

    def _member(self, db, actor, team_id, owner=False):
        team = self._team(db, team_id)
        row = db.execute('SELECT 1 FROM social_team_members WHERE player_id=? AND team_id=?', (actor.player, team_id)).fetchone()
        if not row or owner and team['owner_id'] != actor.player:
            raise ServiceError(403, 'team_permission_denied')
        return team

    def _view_team(self, db, team):
        count = db.execute('SELECT COUNT(*) FROM social_team_members WHERE team_id=?', (team['id'],)).fetchone()[0]
        return {'teamId': team['id'], 'name': team['name'], 'description': team['description'],
                'memberCount': count, 'capacity': self.capacity, 'ownerId': team['owner_id'],
                'badgeId': team['badge_id']}

    def _membership_version(self, db, player, team_id):
        """Bind a current membership to its durable social command history.

        Membership insert and its command receipt commit in one transaction.
        Only account deletion removes a player's social receipts, and it also
        removes that player's membership. Missing/inconsistent history fails
        closed for the guarded leave; do not guess from a second-granularity
        timestamp. A repeated no-op join may safely invalidate an open dialog.
        """
        joins = db.execute('''SELECT rowid,operation,command_id FROM commands
            WHERE player_id=? AND ((operation=? AND json_extract(response_json,'$.state')='Joined')
               OR (operation='social.team.create' AND json_extract(response_json,'$.teamId')=?
                   AND json_extract(response_json,'$.state')='Joined'))''',
            (player, 'social.team.join/' + team_id, team_id)).fetchall()
        if not joins:
            return ''
        removed = db.execute('''SELECT rowid,player_id,operation,command_id FROM commands
            WHERE player_id=? AND operation=? AND json_extract(response_json,'$.state')='Left' ''',
            (player, 'social.team.leave/' + team_id)).fetchall()
        # Another player's receipt: the partial index keeps this from scanning all commands.
        removed += db.execute('''SELECT rowid,player_id,operation,command_id FROM commands
            WHERE substr(operation,1,17)='social.team.kick/' AND operation=?
            AND json_extract(response_json,'$.playerId')=? AND json_extract(response_json,'$.action')='kick' ''',
            ('social.team.kick/' + team_id, player)).fetchall()
        if removed and max(row['rowid'] for row in removed) > max(row['rowid'] for row in joins):
            return ''
        team = db.execute('SELECT owner_id,active FROM social_teams WHERE id=?', (team_id,)).fetchone()
        if not team or not team['active']:
            return ''
        count = db.execute('SELECT COUNT(*) FROM social_team_members WHERE team_id=?', (team_id,)).fetchone()[0]
        # The token identity depends on the complete, sorted immutable event
        # set, never on rowids: VACUUM can renumber implicit SQLite rowids.
        # Any later successful join, leave or kick changes this set, while a
        # replay of an already-committed command does not. Row ordering above
        # is only a conservative inconsistency check (it can fail closed).
        from .storage import canonical
        events = sorted([(player, row['operation'], row['command_id']) for row in joins] +
                        [(row['player_id'], row['operation'], row['command_id']) for row in removed])
        # Ownership and membership count affect whether departure is blocked
        # or closes the team. Bind them so an old confirmation cannot silently
        # acquire a newly consequential outcome after another member changes.
        return hashlib.sha256(canonical(['team-membership-v3', player, team_id, team['owner_id'], count, events]).encode('ascii')).hexdigest()[:32]

    def teams(self, actor, after='', limit=50, query=''):
        query = team_query(query)
        if after:
            identity(after)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ServiceError(422, 'invalid_request')
        with self.database.read() as db:
            self._guard(db, actor)
            # Apply the literal name/ID predicate before LIMIT, so matching
            # teams beyond the first directory page remain discoverable.
            db.create_function('hotr_team_name109', 1,
                               lambda name: unicodedata.normalize('NFC', name.casefold()), deterministic=True)
            search = " AND (instr(hotr_team_name109(t.name),?)>0 OR t.id=? OR EXISTS(SELECT 1 FROM team_public_codes c WHERE c.team_id=t.id AND lower(c.code)=?))" if query else ''
            code_query = query[1:] if query.startswith('#') else query
            parameters = (after, query, query, code_query, limit + 1) if query else (after, limit + 1)
            rows = db.execute("SELECT t.* FROM social_teams t LEFT JOIN account_states a ON a.player_id=t.owner_id WHERE t.active=1 AND t.id>? AND COALESCE(a.state,'Active')='Active'"
                              + search + ' ORDER BY t.id LIMIT ?', parameters).fetchall()
            page = rows[:limit]
            own = db.execute('SELECT team_id FROM social_team_members WHERE player_id=?', (actor.player,)).fetchone()
            return {'teams': [self._view_team(db, row) for row in page], 'myTeamId': own['team_id'] if own else None,
                    'nextCursor': page[-1]['id'] if page else after, 'hasMore': len(rows) > limit}

    def team(self, actor, team_id):
        with self.database.read() as db:
            self._guard(db, actor)
            team = self._team(db, team_id)
            result = self._view_team(db, team)
            member = db.execute('SELECT 1 FROM social_team_members WHERE player_id=? AND team_id=?', (actor.player, team_id)).fetchone()
            result['isMember'] = bool(member)
            if member:
                result['membershipVersion'] = self._membership_version(db, actor.player, team_id)
                is_owner = team['owner_id'] == actor.player
                result['leaveClosesTeam'] = is_owner and result['memberCount'] == 1
                result['leaveRestrictionReason'] = 'transfer_ownership_first' if is_owner and result['memberCount'] > 1 else ''
                result['members'] = [{'playerId': r['player_id'], 'displayName': r['display_name'] or 'Player',
                                      'isOwner': r['player_id'] == team['owner_id']} for r in db.execute(
                    "SELECT m.player_id,s.display_name FROM social_team_members m LEFT JOIN social_profiles s ON s.player_id=m.player_id LEFT JOIN account_states a ON a.player_id=m.player_id WHERE m.team_id=? AND COALESCE(a.state,'Active')='Active' ORDER BY m.joined_at,m.player_id", (team_id,)) if not blocked(db, actor.player, r['player_id'])]
            return result

    def create_team(self, actor, request):
        name, description = text(request.name, 32), text(request.description, 160, empty=True)
        if len(name) < 2:
            raise ServiceError(422, 'invalid_text')
        def execute(db):
            if db.execute('SELECT 1 FROM social_team_members WHERE player_id=?', (actor.player,)).fetchone():
                raise ServiceError(409, 'already_in_team')
            if db.execute('SELECT COUNT(*) FROM social_teams WHERE owner_id=? AND created_at>?', (actor.player, actor.now - 86400)).fetchone()[0] >= 3:
                raise ServiceError(429, 'team_creation_limited')
            team_id = uuid.uuid4().hex
            db.execute('INSERT INTO social_teams(id,owner_id,name,description,active,created_at,updated_at,badge_id) VALUES(?,?,?,?,1,?,?,?)',
                       (team_id, actor.player, name, description, actor.now, actor.now, request.badgeId))
            db.execute('INSERT INTO social_team_members VALUES(?,?,?)', (actor.player, team_id, actor.now))
            return {'teamId': team_id, 'state': 'Joined'}
        # Preserve the exact pre109 command shape for old clients/journals.
        # Explicit badge intent is bound separately, including explicit'drop'.
        payload = request.model_dump()
        if 'badgeId' not in request.model_fields_set:
            payload.pop('badgeId')
        return self._mutation(actor, 'social.team.create', request, lambda db: None, execute, payload=payload)

    def join(self, actor, team_id, request):
        def authorize(db):
            self._team(db, team_id)
            if db.execute('SELECT 1 FROM social_team_bans WHERE team_id=? AND player_id=?', (team_id, actor.player)).fetchone():
                raise ServiceError(403, 'team_permission_denied')
        def execute(db):
            old = db.execute('SELECT team_id FROM social_team_members WHERE player_id=?', (actor.player,)).fetchone()
            if old:
                if old['team_id'] != team_id:
                    raise ServiceError(409, 'already_in_team')
            else:
                if db.execute('SELECT COUNT(*) FROM social_team_members WHERE team_id=?', (team_id,)).fetchone()[0] >= self.capacity:
                    raise ServiceError(409, 'team_full')
                db.execute('INSERT INTO social_team_members VALUES(?,?,?)', (actor.player, team_id, actor.now))
                seed_team_reads(db, actor.player, team_id)
            return {'teamId': team_id, 'state': 'Joined'}
        return self._mutation(actor, 'social.team.join/' + team_id, request, authorize, execute)

    def leave(self, actor, team_id, request):
        def execute(db):
            expected = getattr(request, 'expectedMembershipVersion', None)
            def reject(code):
                # Guarded calls journal a deterministic rejection atomically so
                # a timeout can be reconciled without ever guessing whether a
                # delayed request might still commit. Legacy calls retain their
                # existing HTTP error behavior and original receipt format.
                if expected is not None:
                    return {'teamId': team_id, 'state': 'Rejected', 'reason': code}
                raise ServiceError(409, code)
            try:
                team = self._member(db, actor, team_id)
            except ServiceError as error:
                if expected is not None and error.code in ('team_permission_denied', 'team_not_found'):
                    return reject(error.code)
                raise
            if expected is not None:
                current = self._membership_version(db, actor.player, team_id)
                if not current or current != expected:
                    return reject('team_membership_changed')
            count = db.execute('SELECT COUNT(*) FROM social_team_members WHERE team_id=?', (team_id,)).fetchone()[0]
            if team['owner_id'] == actor.player and count > 1:
                return reject('transfer_ownership_first')
            from .team_life110 import close_member_requests
            close_member_requests(db, actor.player, team_id, actor.now)
            db.execute('DELETE FROM social_team_members WHERE player_id=?', (actor.player,))
            if team['owner_id'] == actor.player:
                db.execute('UPDATE social_teams SET active=0,updated_at=? WHERE id=?', (actor.now, team_id))
            return {'teamId': team_id, 'state': 'Left'}
        # Preserve the exact commandId-only digest for existing journals.
        payload = request.model_dump(exclude_unset=True)
        return self._mutation(actor, 'social.team.leave/' + identity(team_id), request, lambda db: None, execute, payload=payload)

    def manage_member(self, actor, team_id, request, action):
        if action not in ('kick', 'unban', 'transfer'):
            raise ServiceError(422, 'invalid_request')
        def execute(db):
            target = identity(request.playerId)
            if target == actor.player:
                raise ServiceError(409, 'invalid_team_target')
            if action == 'unban':
                db.execute('DELETE FROM social_team_bans WHERE team_id=? AND player_id=?', (team_id, target))
            else:
                if not db.execute('SELECT 1 FROM social_team_members WHERE player_id=? AND team_id=?', (target, team_id)).fetchone():
                    raise ServiceError(404, 'team_member_not_found')
                if action == 'transfer':
                    require_social_peer(db, actor, target)
                    db.execute('UPDATE social_teams SET owner_id=?,updated_at=? WHERE id=?', (target, actor.now, team_id))
                else:
                    from .team_life110 import close_member_requests
                    close_member_requests(db, target, team_id, actor.now)
                    db.execute('DELETE FROM social_team_members WHERE player_id=?', (target,))
                    db.execute('INSERT OR IGNORE INTO social_team_bans VALUES(?,?,?)', (team_id, target, actor.now))
            return {'teamId': team_id, 'playerId': target, 'action': action}
        operation = 'social.team.' + action + '/' + identity(team_id)
        def authorize(db):
            # A committed transfer removes the caller's owner permission. Its
            # exact minimal receipt remains recoverable after a lost response;
            # no new former-owner operation receives this exception.
            if action == 'transfer':
                from .storage import canonical
                prior = db.execute('SELECT payload_digest FROM commands WHERE player_id=? AND operation=? AND command_id=?',
                                   (actor.player, operation, request.commandId)).fetchone()
                if prior and prior['payload_digest'] == self.authority._digest(canonical(request.model_dump())):
                    return
            self._member(db, actor, team_id, owner=True)
        return self._mutation(actor, operation, request, authorize, execute)

    def _channel(self, db, actor, kind, target):
        identity(target)
        if kind == 'Direct':
            require_social_peer(db, actor, target, friends_required=True)
            return direct_channel(actor.player, target)
        if kind == 'Team':
            self._member(db, actor, target)
            return target
        raise ServiceError(422, 'invalid_request')

    def send(self, actor, kind, target, request):
        body = text(request.text, 1000, multiline=True)
        channel = [None]
        def authorize(db):
            channel[0] = self._channel(db, actor, kind, target)
        def execute(db):
            if db.execute('SELECT COUNT(*) FROM social_messages WHERE author_id=? AND created_at>?', (actor.player, actor.now - 60)).fetchone()[0] >= self.rate:
                raise ServiceError(429, 'message_rate_limited')
            message_id = uuid.uuid4().hex
            cursor = db.execute('INSERT INTO social_messages(id,kind,author_id,target_id,body,created_at) VALUES(?,?,?,?,?,?)',
                                (message_id, kind, actor.player, channel[0], body, actor.now))
            return {'messageId': message_id, 'sequence': cursor.lastrowid, 'createdAt': actor.now, 'state': 'Sent'}
        return self._mutation(actor, 'social.message.send/' + kind + '/' + identity(target), request, authorize, execute)

    def messages(self, actor, kind, target, after=0, limit=50):
        if type(after) is not int or not 0 <= after <= 9_223_372_036_854_775_807 or type(limit) is not int or not 1 <= limit <= 100:
            raise ServiceError(422, 'invalid_request')
        with self.database.read() as db:
            self._guard(db, actor)
            channel = self._channel(db, actor, kind, target)
            base = " FROM social_messages m LEFT JOIN account_states a ON a.player_id=m.author_id WHERE m.kind=? AND m.target_id=? AND m.visibility='Visible' AND COALESCE(a.state,'Active')='Active' AND NOT EXISTS(SELECT 1 FROM social_blocks b WHERE (b.blocker_id=? AND b.blocked_id=m.author_id) OR (b.blocker_id=m.author_id AND b.blocked_id=?))"
            args = (kind, channel, actor.player, actor.player)
            rows = db.execute('SELECT m.*,s.display_name' + base.replace(' WHERE ', ' LEFT JOIN social_profiles s ON s.player_id=m.author_id WHERE ', 1) + ' AND m.sequence>? ORDER BY m.sequence LIMIT ?', (*args, after, limit + 1)).fetchall()
            page = rows[:limit]
            read = db.execute('SELECT last_sequence FROM social_message_reads WHERE player_id=? AND kind=? AND target_id=?', (actor.player, kind, channel)).fetchone()
            unread = db.execute('SELECT COUNT(*)' + base + ' AND m.author_id<>? AND m.sequence>?', (*args, actor.player, read[0] if read else 0)).fetchone()[0]
            return {'messages': [{'messageId': r['id'], 'sequence': r['sequence'], 'authorId': r['author_id'],
                                  'displayName': r['display_name'] or 'Player', 'text': r['body'], 'createdAt': r['created_at']} for r in page],
                    'nextCursor': page[-1]['sequence'] if page else after, 'hasMore': len(rows) > limit, 'unreadCount': unread}

    def message_window(self, actor, kind, target, *, before=None, tail=False, limit=8):
        """Latest/older visible window; legacy forward pagination stays intact."""
        if (type(tail) is not bool or tail == (before is not None)
                or before is not None and (type(before) is not int or not 1 <= before <= 9_223_372_036_854_775_807)
                or type(limit) is not int or not 1 <= limit <= 8):
            raise ServiceError(422, 'invalid_request')
        with self.database.read() as db:
            self._guard(db, actor)
            channel = self._channel(db, actor, kind, target)
            base = " FROM social_messages m LEFT JOIN account_states a ON a.player_id=m.author_id WHERE m.kind=? AND m.target_id=? AND m.visibility='Visible' AND COALESCE(a.state,'Active')='Active' AND NOT EXISTS(SELECT 1 FROM social_blocks b WHERE (b.blocker_id=? AND b.blocked_id=m.author_id) OR (b.blocker_id=m.author_id AND b.blocked_id=?))"
            args = (kind, channel, actor.player, actor.player)
            older = '' if tail else ' AND m.sequence<?'
            bounds = () if tail else (before,)
            rows = db.execute('SELECT m.*,s.display_name' + base.replace(' WHERE ', ' LEFT JOIN social_profiles s ON s.player_id=m.author_id WHERE ', 1)
                              + older + ' ORDER BY m.sequence DESC LIMIT ?', (*args, *bounds, limit + 1)).fetchall()
            page = list(reversed(rows[:limit]))
            newest = page[-1]['sequence'] if page else 0
            oldest = page[0]['sequence'] if page else 0
            has_newer = False if tail else bool(db.execute('SELECT 1' + base + ' AND m.sequence>? LIMIT 1', (*args, newest)).fetchone())
            read = db.execute('SELECT last_sequence FROM social_message_reads WHERE player_id=? AND kind=? AND target_id=?', (actor.player, kind, channel)).fetchone()
            unread = db.execute('SELECT COUNT(*)' + base + ' AND m.author_id<>? AND m.sequence>?', (*args, actor.player, read[0] if read else 0)).fetchone()[0]
            return {'messages': [{'messageId': r['id'], 'sequence': r['sequence'], 'authorId': r['author_id'],
                                  'displayName': r['display_name'] or 'Player', 'text': r['body'], 'createdAt': r['created_at']} for r in page],
                    'nextCursor': newest, 'hasMore': has_newer, 'unreadCount': unread,
                    'olderCursor': oldest, 'hasOlder': len(rows) > limit, 'hasNewer': has_newer}

    def mark_read(self, actor, kind, target, request):
        channel = [None]
        def authorize(db):
            channel[0] = self._channel(db, actor, kind, target)
        def execute(db):
            maximum = db.execute('SELECT COALESCE(MAX(sequence),0) FROM social_messages WHERE kind=? AND target_id=?', (kind, channel[0])).fetchone()[0]
            if request.through > maximum:
                raise ServiceError(409, 'read_cursor_conflict')
            if request.through and not db.execute("SELECT 1 FROM social_messages m LEFT JOIN account_states a ON a.player_id=m.author_id WHERE m.kind=? AND m.target_id=? AND m.sequence=? AND m.visibility='Visible' AND COALESCE(a.state,'Active')='Active' AND NOT EXISTS(SELECT 1 FROM social_blocks b WHERE (b.blocker_id=? AND b.blocked_id=m.author_id) OR (b.blocker_id=m.author_id AND b.blocked_id=?))", (kind, channel[0], request.through, actor.player, actor.player)).fetchone():
                raise ServiceError(409, 'read_cursor_conflict')
            db.execute('INSERT INTO social_message_reads VALUES(?,?,?,?) ON CONFLICT(player_id,kind,target_id) DO UPDATE SET last_sequence=MAX(last_sequence,excluded.last_sequence)', (actor.player, kind, channel[0], request.through))
            current = db.execute('SELECT last_sequence FROM social_message_reads WHERE player_id=? AND kind=? AND target_id=?', (actor.player, kind, channel[0])).fetchone()[0]
            return {'through': current}
        return self._mutation(actor, 'social.message.read/' + kind + '/' + identity(target), request, authorize, execute)

    def _accessible_message(self, db, actor, message_id):
        row = db.execute('SELECT * FROM social_messages WHERE id=?', (identity(message_id),)).fetchone()
        if row is None or row['visibility'] != 'Visible':
            raise ServiceError(404, 'message_not_found')
        if row['kind'] == 'Team':
            self._member(db, actor, row['target_id'])
        elif direct_channel(actor.player, row['author_id']) != row['target_id']:
            raise ServiceError(404, 'message_not_found')
        # Reporting an already-received abusive direct message remains possible
        # after removing/blocking its author. This endpoint exposes no content
        # and never restores messaging permissions.
        return row

    def report(self, actor, request):
        details = text(request.details, 500, empty=True, multiline=True)
        def execute(db):
            row = self._accessible_message(db, actor, request.messageId)
            if row['author_id'] == actor.player:
                raise ServiceError(409, 'cannot_report_own_message')
            old = db.execute('SELECT id FROM social_reports WHERE reporter_id=? AND message_id=?', (actor.player, request.messageId)).fetchone()
            report_id = old['id'] if old else uuid.uuid4().hex
            if not old:
                if db.execute('SELECT COUNT(*) FROM social_reports WHERE reporter_id=? AND created_at>?', (actor.player, actor.now - 86400)).fetchone()[0] >= 20:
                    raise ServiceError(429, 'report_rate_limited')
                db.execute('INSERT INTO social_reports VALUES(?,?,?,?,?,\'Open\',?,?)', (report_id, actor.player, request.messageId, request.reason, details, actor.now, actor.now))
            return {'reportId': report_id, 'state': 'Received'}
        return self._mutation(actor, 'social.report', request, lambda db: None, execute)

    def _moderator(self, db, actor):
        self._guard(db, actor)
        if actor.credential_digest is None or not db.execute('SELECT 1 FROM social_moderators WHERE credential_digest=?', (actor.credential_digest,)).fetchone():
            raise ServiceError(403, 'moderator_required')

    def moderation_queue(self, actor, after='', limit=50):
        if after:
            identity(after)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ServiceError(422, 'invalid_request')
        with self.database.transaction() as db:
            self._moderator(db, actor)
            rows = db.execute("SELECT r.*,m.body,m.visibility,m.author_id FROM social_reports r JOIN social_messages m ON m.id=r.message_id WHERE r.state='Open' AND r.id>? ORDER BY r.id LIMIT ?", (after, limit + 1)).fetchall()
            page = rows[:limit]
            return {'reports': [{'reportId': r['id'], 'messageId': r['message_id'], 'reason': r['reason'], 'details': r['details'],
                                 'text': r['body'], 'visibility': r['visibility'], 'authorId': r['author_id']} for r in page],
                    'nextCursor': page[-1]['id'] if page else after, 'hasMore': len(rows) > limit}

    def moderate(self, actor, request):
        reason = text(request.reason, 160)
        def execute(db):
            row = db.execute('SELECT * FROM social_messages WHERE id=?', (request.messageId,)).fetchone()
            if not row:
                raise ServiceError(404, 'message_not_found')
            if request.action in ('Restore', 'Hide') and row['visibility'] == 'Deleted':
                raise ServiceError(409, 'message_deleted')
            if request.action != 'DismissReports':
                state = {'Hide': 'Hidden', 'Restore': 'Visible', 'Delete': 'Deleted'}[request.action]
                db.execute('UPDATE social_messages SET visibility=?,body=CASE WHEN ?=\'Deleted\' THEN \'\' ELSE body END WHERE id=?', (state, state, request.messageId))
            db.execute('UPDATE social_reports SET state=?,updated_at=? WHERE message_id=? AND state=\'Open\'',
                       ('Dismissed' if request.action == 'DismissReports' else 'Resolved', actor.now, request.messageId))
            action_id = uuid.uuid4().hex
            db.execute('INSERT INTO social_moderation_actions VALUES(?,?,?,?,?,?)', (action_id, actor.player, request.messageId, request.action, reason, actor.now))
            return {'actionId': action_id, 'messageId': request.messageId, 'action': request.action}
        return self._mutation(actor, 'social.moderate', request, lambda db: self._moderator(db, actor), execute)
