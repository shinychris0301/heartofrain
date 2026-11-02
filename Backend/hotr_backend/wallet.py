"""Portable staging wallet. No import of a Unity balance or public win verifier.

All projections, debits and attempt settlements share the SQLite transaction
that writes their durable receipt. Production and ordinary Unity profile use
remain disabled until identity, real verification and transport are integrated.
"""
import hashlib
import json
import re
import uuid
from pathlib import Path

from .schemas import Grant, INT_MAX
from .service import Actor, ServiceError
from .storage import canonical
from .wallet_schemas import LevelCatalog
from .guards import require_actor, require_active_player
from .production_runtime122 import production_enabled

GENESIS = [1250, 0, 5, 5, 3, 2, 3, 3, 3, 3, 5]
ACTIVE = ('Reserved', 'Started', 'AwaitingContinuation')
ZERO = [0] * 11


def ensure_wallet(db, player):
    # Historic reward-only profiles are not silently assigned new-player stock.
    db.execute('INSERT OR IGNORE INTO wallets(player_id,initialized,balances) VALUES(?,0,?)',
               (player, canonical(ZERO)))


def project(db, player, origin, delta, now):
    """Immutable origin+delta receipt; safe to replay during startup migration."""
    require_active_player(db, player)
    ensure_wallet(db, player)
    old = db.execute('SELECT * FROM wallet_ledger WHERE player_id=? AND origin=?', (player, origin)).fetchone()
    if old:
        if json.loads(old['delta_json']) != delta:
            raise ServiceError(409, 'wallet_origin_conflict')
        return old['id']
    wallet = db.execute('SELECT * FROM wallets WHERE player_id=?', (player,)).fetchone()
    balances = [a + b for a, b in zip(json.loads(wallet['balances']), delta, strict=True)]
    if len(delta) != 11 or any(type(n) is not int or n < 0 or n > INT_MAX for n in balances) or balances[10] > 5:
        raise ServiceError(409, 'wallet_balance_conflict')
    revision = wallet['revision'] + 1
    if revision > 9_223_372_036_854_775_807:
        raise ServiceError(409, 'wallet_revision_overflow')
    receipt = 'wallet/' + hashlib.sha256((player + '|' + origin).encode()).hexdigest()
    db.execute('INSERT INTO wallet_ledger(id,player_id,origin,delta_json,revision,created_at) VALUES(?,?,?,?,?,?)',
               (receipt, player, origin, canonical(delta), revision, now))
    db.execute('UPDATE wallets SET balances=?,revision=? WHERE player_id=?', (canonical(balances), revision, player))
    return receipt


def new_profile(db, player, now):
    ensure_wallet(db, player)
    project(db, player, 'genesis/v1', GENESIS, now)
    db.execute('UPDATE wallets SET initialized=1 WHERE player_id=?', (player,))


def reward_projection(db, player, receipt_id, grant, now):
    return project(db, player, 'reward/' + receipt_id, [*grant.quantities(), 0], now)


def commerce_projection(db, player, receipt_id, grant, now):
    # The integer overload preserves callers/receipts from coin-only catalogs.
    grant = Grant(coins=grant) if type(grant) is int else grant
    return project(db, player, 'commerce/' + receipt_id, [*grant.quantities(), 0], now)


class Wallet:
    def __init__(self, authority, config: Path):
        self.authority = authority
        self.database = authority.database
        catalog = LevelCatalog.model_validate_json((Path(config) / 'levels.json').read_text('utf-8-sig'))
        if [row.level for row in catalog.levels] != list(range(1, 51)):
            raise RuntimeError('Invalid ordered server level catalog')
        self.catalog = catalog
        self.checkpoint = None  # In-process tests only; never an HTTP route.
        self.replay_enabled = False
        self._replay_key = object()  # In-process broker capability, never an HTTP value.
        # Additive backfill from trusted existing receipts, not client balances. Every later
        # grant projects in its own transaction, so this runs once per database, not per start.
        with self.database.transaction() as db:
            if db.execute("SELECT 1 FROM perf136_maintenance WHERE key='wallet_backfill'").fetchone():
                return
            for player in db.execute('SELECT id FROM players').fetchall():
                ensure_wallet(db, player['id'])
            for row in db.execute("SELECT r.* FROM rewards r WHERE NOT EXISTS(SELECT 1 FROM account_states a WHERE a.player_id=r.player_id AND a.state!='Active') ORDER BY sequence").fetchall():
                reward_projection(db, row['player_id'], row['id'], Grant.model_validate_json(row['grant_json']), row['created_at'])
            for row in db.execute("SELECT c.* FROM commerce_credits c WHERE NOT EXISTS(SELECT 1 FROM account_states a WHERE a.player_id=c.player_id AND a.state!='Active') ORDER BY rowid").fetchall():
                grant = Grant.model_validate_json(row['grant_json']) if row['grant_json'] else Grant(coins=row['coins'])
                commerce_projection(db, row['player_id'], row['id'], grant, row['created_at'])
            db.execute("INSERT INTO perf136_maintenance VALUES('wallet_backfill',1)")

    def _transaction(self, operation, actor):
        with self.database.transaction() as db:
            result = operation(db, self.authority._transaction_actor(db, actor))
            if self.checkpoint:
                self.checkpoint('BeforeCommit')
        if self.checkpoint:
            self.checkpoint('AfterCommit')
        return result

    @staticmethod
    def _row(db, player):
        row = db.execute('SELECT * FROM wallets WHERE player_id=?', (player,)).fetchone()
        if not row:
            raise ServiceError(404, 'wallet_not_found')
        return row

    def _regenerate(self, db, actor):
        require_actor(db, actor)
        row = self._row(db, actor.player)
        due = row['next_life_at']
        balances = json.loads(row['balances'])
        if not row['initialized'] or not due or due > actor.now:
            return
        count = min(5 - balances[10], 1 + (actor.now - due) // 1800)
        if count:
            delta = ZERO.copy()
            delta[10] = count
            project(db, actor.player, 'life/regen/' + str(due), delta, actor.now)
        db.execute('UPDATE wallets SET next_life_at=? WHERE player_id=?',
                   (0 if balances[10] + count >= 5 else due + count * 1800, actor.player))

    def _guard(self, db, actor, revision, allow_quarantine=False):
        self._regenerate(db, actor)
        row = self._row(db, actor.player)
        if not row['initialized']:
            raise ServiceError(409, 'wallet_migration_required')
        if not allow_quarantine and self._quarantined(db, actor.player):
            raise ServiceError(409, 'wallet_refund_review_required')
        if row['revision'] != revision:
            raise ServiceError(409, 'wallet_revision_conflict')
        return row

    @staticmethod
    def _quarantined(db, player):
        # No guessed refund/debt compensation: quarantine spending until an
        # operator-approved refund policy can resolve already-issued credit.
        return bool(db.execute("SELECT 1 FROM commerce_orders WHERE player_id=? AND state='RefundReview'", (player,)).fetchone())

    @staticmethod
    def _attempt(db, actor, attempt_id):
        require_actor(db, actor)
        if not isinstance(attempt_id, str) or not re.fullmatch('[0-9a-f]{32}', attempt_id):
            raise ServiceError(404, 'attempt_not_found')
        row = db.execute('SELECT * FROM gameplay_attempts WHERE id=? AND player_id=?', (attempt_id, actor.player)).fetchone()
        if not row:
            raise ServiceError(404, 'attempt_not_found')
        return row

    @staticmethod
    def _attempt_view(row):
        if row is None:
            return None
        return {'attemptId': row['id'], 'level': row['level'], 'state': row['state'], 'seed': row['seed'],
                'configHash': row['config_hash'], 'moves': row['moves'], 'continues': row['continues'],
                'starting': json.loads(row['selected_json']), 'reward': {'coins': 50, 'stars': 1},
                'createdAt': row['created_at'], 'updatedAt': row['updated_at']}

    def _view(self, db, actor):
        require_actor(db, actor)
        row = self._row(db, actor.player)
        values = json.loads(row['balances'])
        completed = self.authority._player(db, actor)['completed']
        active = db.execute("SELECT * FROM gameplay_attempts WHERE player_id=? AND state IN ('Reserved','Started','AwaitingContinuation')", (actor.player,)).fetchone()
        return {'playerId': actor.player, 'initialized': bool(row['initialized']), 'revision': row['revision'],
                'coins': values[0], 'stars': values[1], 'starting': values[2:6], 'tools': values[6:10],
                'lives': values[10], 'maxLives': 5, 'nextLifeAt': row['next_life_at'], 'completed': completed,
                'currentLevel': min(50, completed + 1), 'activeAttempt': self._attempt_view(active),
                'serverUtc': actor.now, 'balanceScope': 'server_wallet', 'productionEnabled': production_enabled(self.authority),
                'refundReviewRequired': self._quarantined(db, actor.player),
                'normalUnityProfileIntegrated': False, 'localProfileMutated': False}

    def view(self, actor):
        # Most reads have no due life to credit, so they need no write lock.
        with self.database.read() as db:
            current = self.authority._read_actor(db, actor)
            row = self._row(db, current.player)
            if not row['initialized'] or not row['next_life_at'] or row['next_life_at'] > current.now:
                require_actor(db, current)
                return self._view(db, current)
        with self.database.transaction() as db:
            actor = self.authority._transaction_actor(db, actor)
            self._regenerate(db, actor)
            return self._view(db, actor)

    def ledger(self, actor, after=0, limit=100):
        with self.database.read() as db:
            require_actor(db, actor)
            rows = db.execute('SELECT * FROM wallet_ledger WHERE player_id=? AND sequence>? ORDER BY sequence LIMIT ?',
                              (actor.player, after, limit + 1)).fetchall()
            page = rows[:limit]
            return {'entries': [{'cursor': r['sequence'], 'receiptId': r['id'], 'origin': r['origin'],
                                 'delta': json.loads(r['delta_json']), 'revision': r['revision'], 'serverUtc': r['created_at']} for r in page],
                    'nextCursor': page[-1]['sequence'] if page else after, 'hasMore': len(rows) > limit}

    def attempt(self, actor, attempt_id):
        with self.database.read() as db:
            return self._attempt_view(self._attempt(db, actor, attempt_id))

    def _response(self, db, actor, operation, request, delta, attempt_id=None):
        receipt = project(db, actor.player, operation + '/' + request.commandId, delta, actor.now)
        return {'receiptId': receipt, 'operation': operation, 'wallet': self._view(db, actor),
                'attempt': self._attempt_view(self._attempt(db, actor, attempt_id)) if attempt_id else None}

    def reserve(self, actor, request):
        def run(db, actor):
            def execute():
                row = self._guard(db, actor, request.expectedRevision)
                values = json.loads(row['balances'])
                if values[10] <= 0:
                    raise ServiceError(409, 'no_lives')
                if request.level > self.authority._player(db, actor)['completed'] + 1:
                    raise ServiceError(409, 'level_locked')
                if any(b < n for b, n in zip(values[2:6], request.starting, strict=True)):
                    raise ServiceError(409, 'insufficient_inventory')
                if db.execute("SELECT 1 FROM gameplay_attempts WHERE player_id=? AND state IN ('Reserved','Started','AwaitingContinuation')", (actor.player,)).fetchone():
                    raise ServiceError(409, 'attempt_active')
                level = self.catalog.levels[request.level - 1]
                attempt_id = uuid.uuid4().hex
                seed = int(hashlib.sha256(('hotr-attempt-seed-v1|' + attempt_id).encode()).hexdigest()[:8], 16) or 1
                db.execute('''INSERT INTO gameplay_attempts
                    (id,player_id,level,config_hash,seed,selected_json,moves,state,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,'Reserved',?,?)''',
                           (attempt_id, actor.player, request.level, level.configHash, seed, canonical(request.starting), level.moves, actor.now, actor.now))
                return self._response(db, actor, 'attempt.reserve', request, ZERO, attempt_id)
            return self.authority._command(db, actor, 'wallet.reserve', request.commandId, request.model_dump(), execute)
        return self._transaction(run, actor)

    def command(self, actor, attempt_id, operation, request):
        return self._transaction(lambda db, current: self._command_in_transaction(db, current, attempt_id, operation, request), actor)

    def _command_in_transaction(self, db, actor, attempt_id, operation, request, *, replay_key=None):
        require_actor(db, actor)
        if self.replay_enabled and operation in ('tool', 'continue') and replay_key is not self._replay_key:
            raise ServiceError(409, 'use_verified_gameplay')
        if self.replay_enabled and operation == 'quit' and db.execute(
                "SELECT 1 FROM replay_operations WHERE attempt_id=? AND state IN ('Pending','Running')", (attempt_id,)).fetchone():
            raise ServiceError(409, 'gameplay_operation_pending')
        def execute():
            wallet = self._guard(db, actor, request.expectedRevision, allow_quarantine=operation == 'quit')
            row = self._attempt(db, actor, attempt_id)
            values = json.loads(wallet['balances'])
            selected = json.loads(row['selected_json'])
            delta = ZERO.copy()
            state = row['state']
            if operation == 'start':
                if state != 'Reserved':
                    raise ServiceError(409, 'attempt_state_conflict')
                if any(b < n for b, n in zip(values[2:6], selected, strict=True)):
                    raise ServiceError(409, 'insufficient_inventory')
                delta[2:6] = [-n for n in selected]
                state = 'Started'
            elif operation == 'quit':
                if state not in ACTIVE:
                    raise ServiceError(409, 'attempt_state_conflict')
                state = 'Cancelled' if state == 'Reserved' else 'Lost'
                if state == 'Lost':
                    delta[10] = -min(1, values[10])
            elif operation == 'continue':
                if state != 'AwaitingContinuation':
                    raise ServiceError(409, 'attempt_state_conflict')
                if values[0] < 900:
                    raise ServiceError(409, 'insufficient_coins')
                if row['moves'] > INT_MAX - 5 or row['continues'] >= INT_MAX:
                    raise ServiceError(409, 'attempt_overflow')
                delta[0] = -900
                state = 'Started'
                db.execute('UPDATE gameplay_attempts SET moves=moves+5,continues=continues+1 WHERE id=?', (attempt_id,))
            elif operation == 'tool':
                if state != 'Started' or values[6 + request.tool] <= 0:
                    raise ServiceError(409, 'tool_unavailable')
                delta[6 + request.tool] = -1
            else:
                raise ValueError('Unknown internal wallet command')
            db.execute('UPDATE gameplay_attempts SET state=?,updated_at=? WHERE id=?', (state, actor.now, attempt_id))
            self._life_timer(db, actor, values[10] + delta[10])
            return self._response(db, actor, 'attempt.' + operation, request, delta, attempt_id)
        payload = {'attemptId': attempt_id, **request.model_dump()}
        return self.authority._command(db, actor, 'wallet.' + operation, request.commandId, payload, execute)

    @staticmethod
    def _life_timer(db, actor, lives):
        db.execute('UPDATE wallets SET next_life_at=CASE WHEN ?=5 THEN 0 WHEN next_life_at=0 THEN ? ELSE next_life_at END WHERE player_id=?',
                   (lives, actor.now + 1800, actor.player))

    def refill(self, actor, request):
        def run(db, actor):
            def execute():
                row = self._guard(db, actor, request.expectedRevision)
                values = json.loads(row['balances'])
                if values[10] != 0 or values[0] < 900:
                    raise ServiceError(409, 'refill_unavailable')
                if db.execute("SELECT 1 FROM gameplay_attempts WHERE player_id=? AND state IN ('Reserved','Started','AwaitingContinuation')", (actor.player,)).fetchone():
                    raise ServiceError(409, 'attempt_active')
                delta = ZERO.copy()
                delta[0], delta[10] = -900, 5
                db.execute('UPDATE wallets SET next_life_at=0 WHERE player_id=?', (actor.player,))
                return self._response(db, actor, 'life.refill', request, delta)
            return self.authority._command(db, actor, 'wallet.refill', request.commandId, request.model_dump(), execute)
        return self._transaction(run, actor)

    def settle(self, verifier, request):
        return self._transaction(lambda db, current: self._settle_in_transaction(db, current, request), verifier)

    def _settle_in_transaction(self, db, verifier, request, *, replay_key=None):
        actor = Actor(request.playerId, verifier.now)
        require_actor(db, verifier)
        if self.replay_enabled and replay_key is not self._replay_key:
            raise ServiceError(409, 'use_verified_gameplay')
        # The target actor deliberately has no player credential: upstream
        # verification authorizes it. Recheck that upstream credential in
        # this same transaction, including before a cached receipt returns.
        require_actor(db, verifier)
        def execute():
            wallet = self._guard(db, actor, request.expectedRevision, allow_quarantine=request.outcome in ('Won', 'Lost', 'Fault'))
            row = self._attempt(db, actor, request.attemptId)
            state = row['state']
            if state not in ('Started', 'AwaitingContinuation'):
                raise ServiceError(409, 'attempt_state_conflict')
            delta = ZERO.copy()
            if request.outcome == 'Won':
                level = row['level']
                completed = self.authority._player(db, actor)['completed']
                if level == completed + 1:
                    self.authority._record_clear(db, actor, row['id'], level, request.proofDigest)
                    self.authority._grant(db, actor, 'level', row['id'], Grant(coins=50, stars=1), 'server-level/' + row['id'])
                state = 'Won'
            elif request.outcome == 'OutOfMoves':
                if state != 'Started':
                    raise ServiceError(409, 'attempt_state_conflict')
                state = 'AwaitingContinuation'
            elif request.outcome == 'Fault':
                delta[2:6] = json.loads(row['selected_json'])
                state = 'Released'
            else:
                delta[10] = -min(1, json.loads(wallet['balances'])[10])
                state = 'Lost'
            db.execute('UPDATE gameplay_attempts SET state=?,updated_at=? WHERE id=?', (state, actor.now, row['id']))
            self._life_timer(db, actor, json.loads(wallet['balances'])[10] + delta[10])
            return self._response(db, actor, 'attempt.settle', request, delta, row['id'])
        return self.authority._command(db, actor, 'wallet.settle', request.commandId, request.model_dump(), execute)
