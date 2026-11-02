"""Opt-in authenticated friends and bounded public profiles; no addressbook.

Random server player IDs are nonsecret public lookup codes, never credentials.
Financial/private gameplay state is not included in any public profile response.
"""
import hashlib
import re
import secrets
import unicodedata
import uuid

from .guards import require_actor
from .service import ServiceError
from .social_schema import SOCIAL_V5_DDL
from .social_schemas import normalize_display_name

MAX_FRIENDS = 200
MAX_PENDING = 100
REQUEST_COOLDOWN_SECONDS = 86400
SEARCH_SCAN_LIMIT = 500
SEARCH_CURSOR_SECONDS = 900
SEARCH_CURSOR_PER_PLAYER = 20


def _active_exists(db, player):
    return db.execute('''SELECT p.id FROM players p WHERE p.id=? AND NOT EXISTS(
        SELECT 1 FROM account_states a WHERE a.player_id=p.id AND a.state!='Active')''', (player,)).fetchone() is not None


def blocked(db, first, second):
    return bool(db.execute('''SELECT 1 FROM social_blocks WHERE
        (blocker_id=? AND blocked_id=?) OR (blocker_id=? AND blocked_id=?)''',
                          (first, second, second, first)).fetchone())


def eligible_friend(db, first, second):
    if first == second or not _active_exists(db, first) or not _active_exists(db, second) or blocked(db, first, second):
        return False
    low, high = sorted((first, second))
    return bool(db.execute("SELECT 1 FROM social_friend_requests WHERE low_id=? AND high_id=? AND state='Accepted'", (low, high)).fetchone())


is_blocked = blocked
are_friends = eligible_friend


def require_social_peer(db, actor, player, friends_required=False):
    require_actor(db, actor)
    if (not isinstance(player, str) or not re.fullmatch('[0-9a-f]{32}', player)
            or not _active_exists(db, player) or player != actor.player and blocked(db, actor.player, player)
            or friends_required and not eligible_friend(db, actor.player, player)):
        raise ServiceError(404, 'social_player_not_found')
    return db.execute('SELECT id,completed FROM players WHERE id=?', (player,)).fetchone()


def _public(db, player):
    row = db.execute('''SELECT p.id,p.completed,s.display_name,s.leaderboard_opt_in FROM players p
        LEFT JOIN social_profiles s ON s.player_id=p.id WHERE p.id=?''', (player,)).fetchone()
    return {'playerId': row['id'], 'displayName': row['display_name'] or 'Rainkeeper',
            'completedLevels': row['completed'], 'leaderboardOptIn': bool(row['leaderboard_opt_in'])}


class Friends:
    def __init__(self, authority, enabled=False):
        if type(enabled) is not bool:
            raise ValueError('Explicit social activation required')
        self.authority, self.database, self.enabled = authority, authority.database, enabled

    def _enabled(self):
        if not self.enabled:
            raise ServiceError(503, 'social_not_configured')

    @staticmethod
    def _page(after, limit):
        if (not isinstance(after, str) or after and not re.fullmatch('[0-9a-f]{32}', after)
                or type(limit) is not int or not 1 <= limit <= 100):
            raise ServiceError(422, 'invalid_social_page')

    def _read(self, actor, execute, *, writes=False):
        self._enabled()
        with (self.database.transaction() if writes else self.database.read()) as db:
            require_actor(db, actor)
            return execute(db)

    def _command(self, actor, request, operation, execute, privacy=None):
        self._enabled()
        def run(db):
            require_actor(db, actor)
            # Current privacy must hold before even an immutable old receipt is
            # returned. A cached accepted request cannot bypass a later block.
            if privacy:
                privacy(db)
            return self.authority._command(db, actor, operation, request.commandId, request.model_dump(), lambda: execute(db))
        return self.authority._transaction(run)

    @staticmethod
    def _target(db, actor, player, visible=True):
        require_actor(db, actor)
        if player == actor.player:
            raise ServiceError(422, 'self_friend_action_forbidden')
        if not _active_exists(db, player) or visible and blocked(db, actor.player, player):
            raise ServiceError(404, 'social_player_not_found')
        return player

    def me(self, actor):
        return self._read(actor, lambda db: _public(db, actor.player))

    def profile(self, actor, player):
        def read(db):
            require_social_peer(db, actor, player)
            return _public(db, player)
        return self._read(actor, read)

    def search(self, actor, query, after='', limit=20):
        """Find already-public leaderboard profiles without disclosing others.

        Page by an opaque server cursor rather than names, which may be
        duplicated or changed between requests. Cap candidates examined per
        request as well as results; a sparse page can be empty with hasMore.
        """
        if not isinstance(after, str) or len(after) > 128 or type(limit) is not int or not 1 <= limit <= 100:
            raise ServiceError(422, 'invalid_social_page')
        try:
            name = normalize_display_name(query)
        except (ValueError, TypeError):
            raise ServiceError(422, 'invalid_social_search')
        if len(name) < 2:
            raise ServiceError(422, 'invalid_social_search')
        needle = unicodedata.normalize('NFC', name.casefold())
        query_digest = hashlib.sha256(needle.encode('utf-8')).hexdigest()

        def read(db):
            now = self.authority._transaction_clock(db, actor.now)
            cursor = ''
            if after:
                if not re.fullmatch('[A-Za-z0-9_-]{43}', after):
                    raise ServiceError(422, 'invalid_social_page')
                saved = db.execute('''SELECT last_id FROM friend_search_cursors WHERE digest=?
                    AND player_id=? AND query_digest=? AND expires_at>?''',
                    (hashlib.sha256(after.encode('ascii')).hexdigest(), actor.player, query_digest, now)).fetchone()
                if not saved:
                    raise ServiceError(422, 'invalid_social_page')
                cursor = saved['last_id']
            # Bound the raw primary-key scan, including private or deleted
            # accounts: a sparse or adversarial dataset must not make a single
            # search scan the entire player table. Do not return these rows.
            candidates = db.execute('''WITH candidate AS MATERIALIZED (
                SELECT id,completed FROM players WHERE id>? ORDER BY id LIMIT ?)
                SELECT p.id,p.completed,s.display_name,s.leaderboard_opt_in,
                NOT EXISTS (SELECT 1 FROM account_states a WHERE a.player_id=p.id AND a.state!='Active') AS active,
                NOT EXISTS (SELECT 1 FROM social_blocks b WHERE
                    (b.blocker_id=? AND b.blocked_id=p.id) OR
                    (b.blocker_id=p.id AND b.blocked_id=?)) AS unblocked
                FROM candidate p LEFT JOIN social_profiles s ON s.player_id=p.id ORDER BY p.id''',
                (cursor, SEARCH_SCAN_LIMIT + 1, actor.player, actor.player)).fetchall()
            players, examined = [], 0
            for row in candidates[:SEARCH_SCAN_LIMIT]:
                examined += 1
                cursor = row['id']
                if (row['id'] != actor.player and row['active'] and row['unblocked'] and row['leaderboard_opt_in'] == 1
                        and needle in unicodedata.normalize('NFC', row['display_name'].casefold())):
                    players.append({'playerId': row['id'], 'displayName': row['display_name'],
                                    'completedLevels': row['completed'], 'leaderboardOptIn': True})
                    if len(players) == limit:
                        break
            # Resolve only already-visible peers, in the same transaction as
            # the visibility check. The partial unique index ensures at most
            # one live request per pair. Historical cancelled/declined rows
            # intentionally have no public relationship or request ID.
            ids = [item['playerId'] for item in players]
            live = {}
            if ids:
                marks = ','.join('?' for _ in ids)
                rows = db.execute('''SELECT id,low_id,high_id,requester_id,state FROM social_friend_requests
                    WHERE state IN ('Pending','Accepted') AND
                    ((low_id=? AND high_id IN (''' + marks + ''')) OR
                     (high_id=? AND low_id IN (''' + marks + ''')))''',
                    (actor.player, *ids, actor.player, *ids)).fetchall()
                live = {row['high_id'] if row['low_id'] == actor.player else row['low_id']: row for row in rows}
            relationships = [self._relationship_result(actor.player, player, live.get(player)) for player in ids]
            # Global cleanup is capped. Limit each player's outstanding tokens,
            # while retaining a small window of retries and backward requests.
            db.execute('''DELETE FROM friend_search_cursors WHERE digest IN
                (SELECT digest FROM friend_search_cursors WHERE expires_at<=? ORDER BY expires_at LIMIT 100)''', (now,))
            next_cursor = ''
            if examined and examined < len(candidates):
                db.execute('''DELETE FROM friend_search_cursors WHERE player_id=? AND rowid IN
                    (SELECT rowid FROM friend_search_cursors WHERE player_id=? ORDER BY rowid DESC LIMIT -1 OFFSET ?)''',
                    (actor.player, actor.player, SEARCH_CURSOR_PER_PLAYER - 1))
                next_cursor = secrets.token_urlsafe(32)
                db.execute('INSERT INTO friend_search_cursors VALUES(?,?,?,?,?)',
                    (hashlib.sha256(next_cursor.encode('ascii')).hexdigest(), actor.player, query_digest, cursor,
                     now + SEARCH_CURSOR_SECONDS))
            return {'players': players, 'relationships': relationships,
                    'hasMore': examined < len(candidates), 'nextCursor': next_cursor}
        return self._read(actor, read, writes=True)

    @staticmethod
    def _relationship_result(owner, player, row):
        state = ('Friends' if row and row['state'] == 'Accepted' else
                 'Outgoing' if row and row['state'] == 'Pending' and row['requester_id'] == owner else
                 'Incoming' if row and row['state'] == 'Pending' else 'None')
        result = {'playerId': player, 'state': state}
        if state in ('Incoming', 'Outgoing'):
            result['requestId'] = row['id']
        return result

    def relationship(self, actor, player):
        def read(db):
            self._target(db, actor, player)
            row = self._pair(db, actor.player, player)
            state = 'Friends' if eligible_friend(db, actor.player, player) else (
                'Outgoing' if row and row['state'] == 'Pending' and row['requester_id'] == actor.player else
                'Incoming' if row and row['state'] == 'Pending' else 'None')
            result = {'playerId': player, 'state': state}
            if state in ('Incoming', 'Outgoing'):
                result['requestId'] = row['id']
            return result
        return self._read(actor, read)

    def update_profile(self, actor, request):
        def update(db):
            db.execute('''INSERT INTO social_profiles VALUES(?,?,?,?,?) ON CONFLICT(player_id)
                DO UPDATE SET display_name=excluded.display_name,leaderboard_opt_in=excluded.leaderboard_opt_in,
                updated_at=excluded.updated_at''', (actor.player, request.displayName, int(request.leaderboardOptIn), actor.now, actor.now))
            return _public(db, actor.player)
        return self._command(actor, request, 'social.profile', update)

    def update_name(self, actor, request):
        def update(db):
            # Read/preserve consent in this same write transaction. A stale
            # other device must never turn a rename into a fresh opt-in.
            db.execute('''INSERT INTO social_profiles VALUES(?,?,0,?,?) ON CONFLICT(player_id)
                DO UPDATE SET display_name=excluded.display_name,updated_at=excluded.updated_at''',
                       (actor.player, request.displayName, actor.now, actor.now))
            return _public(db, actor.player)
        return self._command(actor, request, 'social.profile.name', update)

    def update_consent(self, actor, request):
        def update(db):
            # Changing consent likewise cannot replay a cached display name.
            db.execute('''INSERT INTO social_profiles VALUES(?,'Rainkeeper',?,?,?) ON CONFLICT(player_id)
                DO UPDATE SET leaderboard_opt_in=excluded.leaderboard_opt_in,updated_at=excluded.updated_at''',
                       (actor.player, int(request.leaderboardOptIn), actor.now, actor.now))
            return _public(db, actor.player)
        return self._command(actor, request, 'social.profile.consent', update)

    @staticmethod
    def _pair(db, first, second):
        low, high = sorted((first, second))
        return db.execute('''SELECT * FROM social_friend_requests WHERE low_id=? AND high_id=?
            ORDER BY CASE WHEN state IN ('Pending','Accepted') THEN 0 ELSE 1 END,
            updated_at DESC,rowid DESC LIMIT 1''', (low, high)).fetchone()

    @staticmethod
    def _count(db, player, state):
        return db.execute('SELECT COUNT(*) FROM social_friend_requests WHERE state=? AND (low_id=? OR high_id=?)', (state, player, player)).fetchone()[0]

    def list(self, actor, after='', limit=50):
        self._page(after, limit)
        def read(db):
            rows = db.execute('''SELECT CASE WHEN low_id=? THEN high_id ELSE low_id END AS peer
                FROM social_friend_requests WHERE state='Accepted' AND (low_id=? OR high_id=?)
                AND (CASE WHEN low_id=? THEN high_id ELSE low_id END)>? ORDER BY peer''',
                              (actor.player, actor.player, actor.player, actor.player, after)).fetchall()
            visible = [r['peer'] for r in rows if eligible_friend(db, actor.player, r['peer'])][:limit + 1]
            page = visible[:limit]
            return {'friends': [_public(db, peer) for peer in page], 'hasMore': len(visible) > limit,
                    'nextCursor': page[-1] if page else after}
        return self._read(actor, read)

    def requests(self, actor, after='', limit=50):
        self._page(after, limit)
        def read(db):
            rows = db.execute('''SELECT * FROM social_friend_requests WHERE state='Pending'
                AND (low_id=? OR high_id=?) AND id>? ORDER BY id''', (actor.player, actor.player, after)).fetchall()
            visible = []
            for row in rows:
                peer = row['high_id'] if row['low_id'] == actor.player else row['low_id']
                if _active_exists(db, peer) and not blocked(db, actor.player, peer):
                    visible.append({'requestId': row['id'], 'direction': 'outgoing' if row['requester_id'] == actor.player else 'incoming',
                                    'profile': _public(db, peer), 'state': 'Pending', 'createdAt': row['created_at']})
                    if len(visible) > limit:
                        break
            page = visible[:limit]
            return {'requests': page, 'hasMore': len(visible) > limit, 'nextCursor': page[-1]['requestId'] if page else after}
        return self._read(actor, read)

    def send(self, actor, request):
        def run(db):
            row = self._pair(db, actor.player, request.playerId)
            if row and row['state'] == 'Accepted':
                return {'playerId': request.playerId, 'state': 'Friends'}
            if row and row['state'] == 'Pending':
                if row['requester_id'] != actor.player:
                    raise ServiceError(409, 'incoming_friend_request_exists')
                return {'requestId': row['id'], 'playerId': request.playerId, 'state': 'Pending'}
            if row and actor.now < row['updated_at'] + REQUEST_COOLDOWN_SECONDS:
                raise ServiceError(409, 'friend_request_unavailable')
            if any(self._count(db, player, 'Pending') >= MAX_PENDING for player in (actor.player, request.playerId)):
                raise ServiceError(409, 'friend_request_limit')
            if any(self._count(db, player, 'Accepted') >= MAX_FRIENDS for player in (actor.player, request.playerId)):
                raise ServiceError(409, 'friend_limit')
            identity = uuid.uuid4().hex
            low, high = sorted((actor.player, request.playerId))
            db.execute("INSERT INTO social_friend_requests VALUES(?,?,?,?,'Pending',?,?)", (identity, low, high, actor.player, actor.now, actor.now))
            return {'requestId': identity, 'playerId': request.playerId, 'state': 'Pending'}
        return self._command(actor, request, 'social.friend.send', run, lambda db: self._target(db, actor, request.playerId))

    @staticmethod
    def _request(db, actor, identity):
        row = db.execute('SELECT * FROM social_friend_requests WHERE id=? AND (low_id=? OR high_id=?)',
                         (identity, actor.player, actor.player)).fetchone()
        if not row:
            raise ServiceError(404, 'friend_request_not_found')
        peer = row['high_id'] if row['low_id'] == actor.player else row['low_id']
        Friends._target(db, actor, peer)
        return row, peer

    def respond(self, actor, request):
        def run(db):
            row, peer = self._request(db, actor, request.requestId)
            outgoing = row['requester_id'] == actor.player
            if request.action == 'cancel' and not outgoing or request.action != 'cancel' and outgoing:
                raise ServiceError(403, 'friend_response_forbidden')
            state = {'accept': 'Accepted', 'decline': 'Declined', 'cancel': 'Cancelled'}[request.action]
            if row['state'] != 'Pending' and row['state'] != state:
                raise ServiceError(409, 'friend_request_unavailable')
            if state == 'Accepted' and row['state'] == 'Pending' and any(
                self._count(db, player, 'Accepted') >= MAX_FRIENDS for player in (actor.player, peer)):
                raise ServiceError(409, 'friend_limit')
            db.execute('UPDATE social_friend_requests SET state=?,updated_at=? WHERE id=?', (state, actor.now, row['id']))
            return {'requestId': row['id'], 'playerId': peer, 'state': state}
        return self._command(actor, request, 'social.friend.respond', run, lambda db: self._request(db, actor, request.requestId))

    def remove(self, actor, request):
        def run(db):
            low, high = sorted((actor.player, request.playerId))
            db.execute("UPDATE social_friend_requests SET state='Cancelled',updated_at=? WHERE low_id=? AND high_id=? AND state='Accepted'",
                       (actor.now, low, high))
            return {'playerId': request.playerId, 'state': 'Removed'}
        return self._command(actor, request, 'social.friend.remove', run,
                             lambda db: self._target(db, actor, request.playerId, visible=False))

    def block(self, actor, request):
        def run(db):
            db.execute('INSERT OR IGNORE INTO social_blocks VALUES(?,?,?)', (actor.player, request.playerId, actor.now))
            low, high = sorted((actor.player, request.playerId))
            db.execute("UPDATE social_friend_requests SET state='Cancelled',updated_at=? WHERE low_id=? AND high_id=? AND state IN ('Pending','Accepted')",
                       (actor.now, low, high))
            return {'playerId': request.playerId, 'blocked': True}
        return self._command(actor, request, 'social.block', run,
                             lambda db: self._target(db, actor, request.playerId, visible=False))

    def unblock(self, actor, request):
        def run(db):
            if request.playerId == actor.player:
                raise ServiceError(422, 'self_friend_action_forbidden')
            db.execute('DELETE FROM social_blocks WHERE blocker_id=? AND blocked_id=?', (actor.player, request.playerId))
            return {'playerId': request.playerId, 'blocked': False}
        return self._command(actor, request, 'social.unblock', run)

    def blocks(self, actor, after='', limit=50):
        self._page(after, limit)
        def read(db):
            rows = db.execute('SELECT blocked_id,created_at FROM social_blocks WHERE blocker_id=? AND blocked_id>? ORDER BY blocked_id LIMIT ?',
                              (actor.player, after, limit + 1)).fetchall()
            page = rows[:limit]
            return {'blocks': [{'playerId': r['blocked_id'], 'createdAt': r['created_at']} for r in page],
                    'hasMore': len(rows) > limit, 'nextCursor': page[-1]['blocked_id'] if page else after}
        return self._read(actor, read)
