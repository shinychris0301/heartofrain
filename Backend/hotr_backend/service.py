import hashlib
import json
import re
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from .schemas import CupRules, DailyRules, Grant, INT_MAX, WellworksRules
from .storage import Database, canonical


class ServiceError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


@dataclass(frozen=True)
class Actor:
    player: str
    now: int
    credential_digest: str | None = None
    # Server-only capability, never part of an API model or persisted receipt.
    # Keep the request snapshot in now for gameplay/reward semantics, while
    # credentials are revalidated at every actual transaction boundary.
    _clock: Callable[[], float] | None = field(default=None, repr=False, compare=False)


class Authority:
    def __init__(self, database: Database, config: Path, clock=None, requests_per_minute=120):
        self.database = database
        self.clock = clock or time.time
        self.requests_per_minute = requests_per_minute
        self.daily = DailyRules.model_validate_json((config / 'daily_gift.json').read_text(encoding='utf-8-sig'))
        self.wellworks = WellworksRules.model_validate_json((config / 'wellworks.json').read_text(encoding='utf-8-sig'))
        self.cup = CupRules.model_validate_json((config / 'rain_cup.json').read_text(encoding='utf-8-sig'))
        self.checkpoint = None  # In-process fault injection; never an HTTP route.
        # Requests per credential in the current minute. One process owns a database, so this
        # holds the same limit as the old table without a durable write on every read. A
        # restart forgets at most one minute of budget.
        self._rate_lock = threading.Lock()
        self._rate_window, self._rate_counts = -1, {}

    def _read_clock(self, db, sampled_at=0):
        try:
            now = int(self.clock())
        except Exception:
            raise ServiceError(503, 'clock_unavailable') from None
        if now < 0 or now > 253_402_300_799:
            raise ServiceError(503, 'clock_unavailable')
        high_water = db.execute('SELECT high_water FROM clock_state WHERE id=1').fetchone()[0]
        return max(sampled_at, now, high_water), high_water

    def _read_actor(self, db, actor):
        """The read-only counterpart of _transaction_actor, inside Database.read()."""
        return replace(actor, now=self._read_clock(db, actor.now)[0])

    def _transaction_clock(self, db, sampled_at=0):
        # Sample after acquiring this writer. A queued clock/authentication
        # transaction must not extend a credential past its real expiry.
        now, high_water = self._read_clock(db, sampled_at)
        # An unchanged clock needs no durable write on every authenticated read.
        if now != high_water:
            db.execute('UPDATE clock_state SET high_water=? WHERE id=1', (now,))
        return now

    def _now(self, timeout=10):
        with self.database.transaction(timeout=timeout) as db:
            now = self._transaction_clock(db)
        return now

    def _transaction_actor(self, db, actor):
        # A request can wait for this writer across a reward/Cup/life boundary.
        # Keep one coherent service-time snapshot for all mutations in this
        # transaction; retain identity and its independent expiry capability.
        return replace(actor, now=self._transaction_clock(db, actor.now))

    def provision(self, player=None, role='player', lifetime=86400):
        """Operator-only provisioning. No unauthenticated signup or client reset."""
        player = player or uuid.uuid4().hex
        if not re.fullmatch('[0-9a-f]{32}', player) or role not in ('player', 'verifier') or not 1 <= lifetime <= 2_592_000:
            raise ValueError('Invalid provision request')
        token = secrets.token_urlsafe(32)
        now = self._now()
        with self.database.transaction() as db:
            from .guards import require_active_player
            require_active_player(db, player)
            created = db.execute('INSERT OR IGNORE INTO players(id,reward_totals,created_at) VALUES(?,?,?)', (player, canonical([0] * 10), now)).rowcount
            if created and role == 'player':
                from .wallet import new_profile
                new_profile(db, player, now)
            else:
                from .wallet import ensure_wallet
                ensure_wallet(db, player)
            db.execute('INSERT INTO credentials VALUES(?,?,?,?,0)', (self._digest(token), player, role, now + lifetime))
        return {'playerId': player, 'token': token, 'role': role, 'expiresAt': now + lifetime}

    @staticmethod
    def _digest(text):
        return hashlib.sha256(text.encode()).hexdigest()

    def authenticate(self, token, role='player'):
        if not isinstance(token, str) or not re.fullmatch('[A-Za-z0-9_-]{43}', token):
            raise ServiceError(401, 'unauthorized')
        digest = self._digest(token)
        # A snapshot read: authentication neither takes nor waits for the write lock. Writers
        # still advance the durable clock, and require_actor rechecks at every write.
        with self.database.read() as db:
            now = self._read_clock(db)[0]
            credential = db.execute('SELECT * FROM credentials WHERE digest=?', (digest,)).fetchone()
            if not credential or credential['revoked'] or credential['expires_at'] <= now:
                raise ServiceError(401, 'unauthorized')
            if credential['role'] != role:
                raise ServiceError(403, 'forbidden')
            from .guards import require_active_player
            require_active_player(db, credential['player_id'])
        window = now // 60
        with self._rate_lock:
            if window != self._rate_window:
                self._rate_window, self._rate_counts = window, {}
            count = self._rate_counts.get(digest, 0) + 1
            self._rate_counts[digest] = count
        if count > self.requests_per_minute:
            raise ServiceError(429, 'rate_limited')
        return Actor(credential['player_id'], now, digest, self.clock)

    def revoke(self, token):
        with self.database.transaction() as db:
            db.execute('UPDATE credentials SET revoked=1 WHERE digest=?', (self._digest(token),))

    def _transaction(self, operation, actor=None):
        with self.database.transaction() as db:
            response = operation(db) if actor is None else operation(db, self._transaction_actor(db, actor))
            if self.checkpoint:
                self.checkpoint('BeforeCommit')
        if self.checkpoint:
            self.checkpoint('AfterCommit')
        return response

    def _command(self, db, actor, operation, command, payload, execute):
        from .guards import require_actor
        require_actor(db, actor)
        digest = self._digest(canonical(payload))
        old = db.execute('SELECT * FROM commands WHERE player_id=? AND operation=? AND command_id=?', (actor.player, operation, command)).fetchone()
        if old:
            if old['payload_digest'] != digest:
                raise ServiceError(409, 'idempotency_conflict')
            return json.loads(old['response_json'])
        response = execute()
        db.execute('INSERT INTO commands VALUES(?,?,?,?,?)', (actor.player, operation, command, digest, canonical(response)))
        return response

    @staticmethod
    def _player(db, actor):
        from .guards import require_actor
        require_actor(db, actor)
        row = db.execute('SELECT * FROM players WHERE id=?', (actor.player,)).fetchone()
        if not row:
            raise ServiceError(401, 'unauthorized')
        return row

    @staticmethod
    def _receipt(row):
        return {'id': row['id'], 'source': row['source'], 'grant': json.loads(row['grant_json']), 'serverUtc': row['created_at'], 'cursor': row['sequence']}

    def _grant(self, db, actor, source, key, grant, receipt_id):
        from .guards import require_actor
        require_actor(db, actor)
        old = db.execute('SELECT * FROM rewards WHERE player_id=? AND source=? AND source_key=?', (actor.player, source, key)).fetchone()
        if old:
            return self._receipt(old)
        totals = json.loads(self._player(db, actor)['reward_totals'])
        totals = [a + b for a, b in zip(totals, grant.quantities(), strict=True)]
        if any(n > INT_MAX for n in totals):
            raise ServiceError(409, 'reward_overflow')
        db.execute('INSERT INTO rewards(id,player_id,source,source_key,grant_json,created_at) VALUES(?,?,?,?,?,?)', (receipt_id, actor.player, source, key, canonical(grant.model_dump()), actor.now))
        db.execute('UPDATE players SET reward_totals=? WHERE id=?', (canonical(totals), actor.player))
        from .wallet import reward_projection
        reward_projection(db, actor.player, receipt_id, grant, actor.now)
        return self._receipt(db.execute('SELECT * FROM rewards WHERE id=?', (receipt_id,)).fetchone())

    def account(self, actor):
        with self.database.read() as db:
            player = self._player(db, actor)
            return {'playerId': actor.player, 'completed': player['completed'], 'serverUtc': actor.now,
                    'rewardTotals': json.loads(player['reward_totals']), 'balanceScope': 'reward_credits_only',
                    'realCompetition': False, 'purchaseFulfillment': False}

    def daily_offer(self, actor):
        # Home's badge asks often; only the first ask of a day has to create the offer.
        with self.database.read() as db:
            current = self._read_actor(db, actor)
            self._player(db, current)
            offer = db.execute('SELECT * FROM offers WHERE player_id=? AND day=?', (current.player, current.now // 86400)).fetchone()
            if offer:
                claimed = bool(db.execute('SELECT 1 FROM daily_claims WHERE offer_id=?', (offer['id'],)).fetchone())
                return {'id': offer['id'], 'schedule': offer['schedule'], 'day': offer['day'], 'step': offer['step'],
                        'claimed': claimed, 'grant': json.loads(offer['grant_json'])}
        def run(db, actor):
            player = self._player(db, actor)
            day = actor.now // 86400
            offer = db.execute('SELECT * FROM offers WHERE player_id=? AND day=?', (actor.player, day)).fetchone()
            if not offer:
                step = player['gift_claims'] % 7
                db.execute('INSERT INTO offers VALUES(?,?,?,?,?,?)', ('server-daily/' + uuid.uuid4().hex, actor.player, day, step, self.daily.version, canonical(self.daily.days[step].model_dump())))
                offer = db.execute('SELECT * FROM offers WHERE player_id=? AND day=?', (actor.player, day)).fetchone()
            claimed = bool(db.execute('SELECT 1 FROM daily_claims WHERE offer_id=?', (offer['id'],)).fetchone())
            return {'id': offer['id'], 'schedule': offer['schedule'], 'day': offer['day'], 'step': offer['step'],
                    'claimed': claimed, 'grant': json.loads(offer['grant_json'])}
        return self._transaction(run, actor)

    def daily_claim(self, actor, request):
        def run(db, actor):
            def execute():
                offer = db.execute('SELECT * FROM offers WHERE id=? AND player_id=?', (request.offerId, actor.player)).fetchone()
                if not offer:
                    raise ServiceError(404, 'offer_not_found')
                if (request.day, request.step, request.schedule, canonical(request.expectedGrant.model_dump())) != (offer['day'], offer['step'], offer['schedule'], offer['grant_json']):
                    raise ServiceError(409, 'offer_conflict')
                old = db.execute('SELECT 1 FROM daily_claims WHERE offer_id=?', (offer['id'],)).fetchone()
                if not old:
                    if offer['day'] != actor.now // 86400:
                        raise ServiceError(410, 'gift_expired')
                    player = self._player(db, actor)
                    if offer['day'] <= player['last_gift_day'] or offer['step'] != player['gift_claims'] % 7:
                        raise ServiceError(409, 'daily_progress_conflict')
                    self._grant(db, actor, 'daily_gift', offer['id'], Grant.model_validate_json(offer['grant_json']), offer['id'])
                    db.execute('INSERT INTO daily_claims VALUES(?,?,?,?)', (offer['id'], actor.player, offer['day'], offer['id']))
                    db.execute('UPDATE players SET gift_claims=gift_claims+1,last_gift_day=? WHERE id=?', (offer['day'], actor.player))
                # A confirmed receipt remains recoverable after midnight/expiry.
                return {'playerId': actor.player, 'receiptId': offer['id'], 'requestId': request.requestId,
                        'schedule': offer['schedule'], 'day': offer['day'], 'step': offer['step'], 'grant': json.loads(offer['grant_json'])}
            return self._command(db, actor, 'daily.claim', request.requestId, request.model_dump(), execute)
        return self._transaction(run, actor)

    def rewards(self, actor, after=0, limit=100):
        with self.database.read() as db:
            from .guards import require_actor
            require_actor(db, actor)
            rows = db.execute('SELECT * FROM rewards WHERE player_id=? AND sequence>? ORDER BY sequence LIMIT ?', (actor.player, after, limit + 1)).fetchall()
            page = rows[:limit]
            return {'receipts': [self._receipt(r) for r in page], 'nextCursor': page[-1]['sequence'] if page else after, 'hasMore': len(rows) > limit}

    def wellworks_view(self, actor):
        with self.database.read() as db:
            completed = self._player(db, actor)['completed']
            return {'completed': completed, 'milestones': [{'level': m.level, 'grant': m.grant.model_dump(),
                    'eligible': completed >= m.level, 'claimed': bool(db.execute("SELECT 1 FROM rewards WHERE player_id=? AND source='wellworks' AND source_key=?", (actor.player, str(m.level))).fetchone())} for m in self.wellworks.milestones]}

    def wellworks_claim(self, actor, request):
        def run(db, actor):
            def execute():
                milestone = next((m for m in self.wellworks.milestones if m.level == request.level), None)
                if not milestone:
                    raise ServiceError(404, 'milestone_not_found')
                if self._player(db, actor)['completed'] < request.level:
                    raise ServiceError(409, 'milestone_locked')
                return self._grant(db, actor, 'wellworks', str(request.level), milestone.grant, f'server-wellworks/{actor.player}/{request.level}')
            return self._command(db, actor, 'wellworks.claim', request.commandId, request.model_dump(), execute)
        return self._transaction(run, actor)

    @staticmethod
    def _finish(db, row, now):
        if row and row['state'] == 'Active' and now >= row['ends_at']:
            rules = CupRules.model_validate_json(row['rules_json'])
            rank = 1 + sum(score > row['points'] for score in rules.rivalFinalScores)
            db.execute("UPDATE cup_runs SET state='Finished',final_rank=? WHERE id=?", (rank, row['id']))
            return db.execute('SELECT * FROM cup_runs WHERE id=?', (row['id'],)).fetchone()
        return row

    def cup_view(self, actor):
        # Only a run that has just ended has anything to write.
        with self.database.read() as db:
            current = self._read_actor(db, actor)
            row = db.execute('SELECT state,ends_at FROM cup_runs WHERE player_id=? ORDER BY joined_at DESC,rowid DESC LIMIT 1', (current.player,)).fetchone()
            if not row or row['state'] != 'Active' or current.now < row['ends_at']:
                return self._cup_view(db, current)
        return self._transaction(self._cup_view, actor)

    def _cup_view(self, db, actor):
        completed = self._player(db, actor)['completed']
        row = db.execute('SELECT * FROM cup_runs WHERE player_id=? ORDER BY joined_at DESC,rowid DESC LIMIT 1', (actor.player,)).fetchone()
        row = self._finish(db, row, actor.now)
        state = row['state'] if row else 'Locked' if completed < self.cup.unlockClears else 'Exhausted' if completed == 50 else 'Ready'
        rules = CupRules.model_validate_json(row['rules_json']) if row else self.cup
        result = {'state': state, 'completed': completed, 'practice': True, 'simulatedRivals': True, 'realCompetition': False,
                  'serverUtc': actor.now, 'rules': rules.model_dump(), 'canJoin': completed >= self.cup.unlockClears and completed < 50 and (not row or row['state'] == 'Claimed')}
        if row:
            elapsed = max(0, min(rules.durationSeconds, actor.now - row['joined_at']))
            result['run'] = {'id': row['id'], 'joinedAt': row['joined_at'], 'endsAt': row['ends_at'], 'points': row['points'], 'finalRank': row['final_rank'], 'rivalScores': [score * elapsed // rules.durationSeconds for score in rules.rivalFinalScores]}
        return result

    def cup_join(self, actor, request):
        def run(db, actor):
            def execute():
                player = self._player(db, actor)
                if not self.cup.unlockClears <= player['completed'] < 50:
                    raise ServiceError(409, 'cup_locked')
                if db.execute("SELECT 1 FROM gameplay_attempts WHERE player_id=? AND state IN ('Reserved','Started','AwaitingContinuation')", (actor.player,)).fetchone():
                    raise ServiceError(409, 'attempt_active')
                if db.execute("SELECT 1 FROM cup_runs WHERE player_id=? AND state!='Claimed'", (actor.player,)).fetchone():
                    raise ServiceError(409, 'cup_unclaimed')
                if db.execute('SELECT 1 FROM cup_runs WHERE id=?', (request.commandId,)).fetchone():
                    raise ServiceError(409, 'cup_id_conflict')
                db.execute('INSERT INTO cup_runs VALUES(?,?,?,?,?,?,0,0,?)', (request.commandId, actor.player, 'Active', actor.now, actor.now + self.cup.durationSeconds, player['completed'], canonical(self.cup.model_dump())))
                return {'runId': request.commandId, 'endsAt': actor.now + self.cup.durationSeconds, 'practice': True}
            return self._command(db, actor, 'cup.join', request.commandId, request.model_dump(), execute)
        return self._transaction(run, actor)

    def cup_claim(self, actor, request):
        def run(db, actor):
            def execute():
                row = db.execute('SELECT * FROM cup_runs WHERE id=? AND player_id=?', (request.runId, actor.player)).fetchone()
                if not row:
                    raise ServiceError(404, 'cup_not_found')
                row = self._finish(db, row, actor.now)
                if row['state'] == 'Active':
                    raise ServiceError(409, 'cup_active')
                rules = CupRules.model_validate_json(row['rules_json'])
                receipt = self._grant(db, actor, 'rain_cup', row['id'], rules.rankRewards[row['final_rank'] - 1], 'server-rain-cup/' + row['id'])
                db.execute("UPDATE cup_runs SET state='Claimed' WHERE id=?", (row['id'],))
                return receipt
            return self._command(db, actor, 'cup.claim', request.commandId, request.model_dump(), execute)
        return self._transaction(run, actor)

    def verified_clear(self, actor, request):
        def run(db, actor):
            def execute():
                player = self._player(db, actor)
                if request.level != player['completed'] + 1:
                    raise ServiceError(409, 'clear_not_next_level')
                point = self._record_clear(db, actor, request.attemptId, request.level, request.proofDigest)
                return {'completed': request.level, 'attemptId': request.attemptId, 'cupPoint': point}
            return self._command(db, actor, 'verified.clear', request.attemptId, request.model_dump(), execute)
        return self._transaction(run, actor)

    def _record_clear(self, db, actor, attempt_id, level, proof_digest):
        from .guards import require_actor
        require_actor(db, actor)
        row = db.execute("SELECT * FROM cup_runs WHERE player_id=? AND state='Active'", (actor.player,)).fetchone()
        row = self._finish(db, row, actor.now)
        cup = row['id'] if row and row['state'] == 'Active' and actor.now < row['ends_at'] else None
        db.execute('INSERT INTO verified_clears VALUES(?,?,?,?,?,?)', (actor.player, attempt_id, level, proof_digest, actor.now, cup))
        db.execute('UPDATE players SET completed=? WHERE id=?', (level, actor.player))
        if cup:
            db.execute('UPDATE cup_runs SET points=points+1 WHERE id=?', (cup,))
        return int(cup is not None)

    def ingest(self, actor, batch):
        def run(db):
            from .guards import require_actor
            require_actor(db, actor)
            stream = self._digest('hotr-local-stream-v1|' + actor.player)
            accepted, duplicates = 0, 0
            for event in batch.events:
                if event.stream != stream:
                    raise ServiceError(403, 'stream_mismatch')
                payload = canonical(event.model_dump())
                digest = self._digest(payload)
                old = db.execute('SELECT payload_digest FROM audit_events WHERE player_id=? AND event_id=?', (actor.player, event.id)).fetchone()
                if old:
                    if old['payload_digest'] != digest:
                        raise ServiceError(409, 'event_conflict')
                    duplicates += 1
                else:
                    db.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,'client_reported')", (actor.player, event.id, digest, payload, actor.now))
                    accepted += 1
            return {'accepted': accepted, 'duplicates': duplicates, 'trust': 'client_reported', 'rewarded': False}
        return self._transaction(run)
