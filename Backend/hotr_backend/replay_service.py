"""Opt-in authenticated append-only gameplay broker using the real Unity worker.

Model work runs outside SQLite transactions. A tool's deterministic prospective
receipt identifies a server-only simulation budget; it becomes an actual owned
ledger receipt only in the same commit as the verified prefix. No client win,
checkpoint, paid receipt, balance, seed or level-definition claim is accepted.
"""
import hashlib
import json
import threading
import time
import uuid
from dataclasses import replace

from .guards import require_actor
from .production_runtime122 import production_enabled
from .replay_contract import ApprovedWorker, ReplayError, TrustedModelFault, encode_job, sha256, validate_output
from .replay_schemas import ReplayContinue, ReplayTool, VerifyReplay
from .service import ServiceError
from .storage import canonical
from .wallet_schemas import SettleAttempt, SpendTool, WalletCommand

LEASE_SECONDS = 120  # Exceeds this broker's approved runner limit of90seconds.
FIRST_RETRY_SECONDS = 15
LONGEST_RETRY_SECONDS = 300
FAILURES_WHEN_OTHERS_SUCCEED = 3
FAILURES_WITHOUT_ANY_SUCCESS = 6
OUTAGE_PATIENCE_SECONDS = 1800


class _Waiting:
    """An unfinished operation and the latest credential its client polled with.

    Held in memory, in arrival order. After a restart each client's next poll joins again.
    An actor of None means its credential lapsed: it keeps its place until the client returns.
    """
    __slots__ = ('actor', 'attempt', 'command', 'running', 'failures', 'first_failure', 'successes', 'not_before')

    def __init__(self, actor, attempt, command):
        self.actor, self.attempt, self.command, self.running = actor, attempt, command, False
        self.failures, self.first_failure, self.successes, self.not_before = 0, 0.0, 0, 0.0


class ReplayBroker:
    dispatcher = False

    def __init__(self, authority, wallet, worker=None, *, enabled=False, dispatcher=False):
        if type(enabled) is not bool or type(dispatcher) is not bool or dispatcher and not enabled:
            raise RuntimeError('Explicit replay activation required')
        self.authority, self.wallet, self.database = authority, wallet, authority.database
        self.worker, self.enabled, self.checkpoint = worker, enabled, None
        self.pins, self.pins_hash = None, None
        self.dispatcher = dispatcher
        self._queue_lock = threading.Lock()
        self._waiting = {}
        self._draining = self._stopped = False
        self._successes = 0
        if enabled:
            if not isinstance(worker, ApprovedWorker) or not worker.enabled or worker.timeout > 90:
                raise RuntimeError('An approved bounded replay worker is required')
            _, self.pins, self.pins_hash = worker._verify_bundle()
            for level, pin in zip(wallet.catalog.levels, self.pins['levels'], strict=True):
                if (level.level != pin['level'] or level.sourceSHA256 != pin['sha256']
                        or level.configHash != pin['sha256'] or level.moves != pin['moves']):
                    raise RuntimeError('Replay and server level catalog differ')
            # The owned runtime lock proves no earlier worker survives this start, so
            # its lease must not block every player. Its operation stays resumable.
            with self.database.transaction() as db:
                db.execute("UPDATE replay_operations SET state='Pending',lease_token=NULL,lease_until=0,error_code='replay_temporarily_unavailable' WHERE state='Running'")
                db.execute('UPDATE replay_worker_slot SET operation_id=NULL,lease_token=NULL,lease_until=0 WHERE id=1')
        wallet.replay_enabled = enabled

    def _guard(self, db, actor):
        require_actor(db, actor)
        if not self.enabled:
            raise ServiceError(503, 'gameplay_replay_not_configured')

    @staticmethod
    def _frozen(attempt):
        return {key: attempt[key] for key in ('id', 'player_id', 'level', 'config_hash', 'seed', 'selected_json')}

    def _register(self, db, actor, attempt):
        replay = db.execute('SELECT * FROM replay_attempts WHERE attempt_id=?', (attempt['id'],)).fetchone()
        if replay:
            return replay
        if attempt['state'] != 'Started' or attempt['continues'] != 0:
            raise ServiceError(409, 'fresh_verified_attempt_required')
        starts = db.execute("SELECT command_id,response_json FROM commands WHERE player_id=? AND operation='wallet.start' AND json_extract(response_json,'$.attempt.attemptId')=? LIMIT 2", (actor.player, attempt['id'])).fetchall()
        if len(starts) != 1 or db.execute("SELECT 1 FROM commands WHERE player_id=? AND operation IN ('wallet.tool','wallet.continue') AND json_extract(response_json,'$.attempt.attemptId')=?", (actor.player, attempt['id'])).fetchone():
            raise ServiceError(409, 'fresh_verified_attempt_required')
        receipt = json.loads(starts[0]['response_json'])['receiptId']
        ledger = db.execute('SELECT * FROM wallet_ledger WHERE id=? AND player_id=?', (receipt, actor.player)).fetchone()
        expected = [0] * 11
        expected[2:6] = [-value for value in json.loads(attempt['selected_json'])]
        if not ledger or ledger['origin'] != 'attempt.start/' + starts[0]['command_id'] or json.loads(ledger['delta_json']) != expected:
            raise ServiceError(409, 'attempt_start_receipt_mismatch')
        pin = self.pins['levels'][attempt['level'] - 1]
        if attempt['config_hash'] != pin['sha256'] or attempt['moves'] != pin['moves']:
            raise ServiceError(409, 'attempt_configuration_mismatch')
        frozen = self._frozen(attempt); frozen['startOrigin'] = ledger['origin']; frozen['startDelta'] = expected
        db.execute('''INSERT INTO replay_attempts(attempt_id,player_id,start_receipt_id,pins_sha,level_sha,frozen_json,moves,updated_at)
            VALUES(?,?,?,?,?,?,?,?)''', (attempt['id'], actor.player, receipt, self.pins_hash, pin['sha256'], canonical(frozen), pin['moves'], actor.now))
        return db.execute('SELECT * FROM replay_attempts WHERE attempt_id=?', (attempt['id'],)).fetchone()

    def _integrity(self, db, actor, attempt, replay):
        frozen = json.loads(replay['frozen_json'])
        if (any(frozen[key] != value for key, value in self._frozen(attempt).items())
                or replay['pins_sha'] != self.pins_hash or replay['level_sha'] != attempt['config_hash']):
            raise ServiceError(409, 'attempt_configuration_mismatch')
        start = db.execute('SELECT * FROM wallet_ledger WHERE id=? AND player_id=?', (replay['start_receipt_id'], actor.player)).fetchone()
        if not start or start['origin'] != frozen['startOrigin'] or json.loads(start['delta_json']) != frozen['startDelta']:
            raise ServiceError(409, 'attempt_start_receipt_mismatch')
        receipts = json.loads(replay['receipts_json']); prefix = json.loads(replay['prefix_json'])
        bindings = db.execute('SELECT * FROM replay_paid_bindings WHERE attempt_id=? ORDER BY action_index', (attempt['id'],)).fetchall()
        if len(receipts) != len(bindings):
            raise ServiceError(409, 'paid_action_binding_mismatch')
        for receipt, binding in zip(receipts, bindings, strict=True):
            ledger = db.execute('SELECT * FROM wallet_ledger WHERE id=? AND player_id=?', (binding['receipt_id'], actor.player)).fetchone()
            delta = [0] * 11
            if binding['kind'] == 'Tool': delta[6 + binding['tool']] = -1
            else: delta[0] = -900
            action = prefix[binding['action_index']] if binding['action_index'] < len(prefix) else {}
            expected = {'receiptId': binding['receipt_id'], 'attemptId': attempt['id'], 'kind': binding['kind'],
                'actionIndex': binding['action_index'], 'tool': binding['tool'], 'coins': 900 if binding['kind'] == 'Continue' else 0,
                'quantity': 1 if binding['kind'] == 'Tool' else 0, 'movesAfter': binding['moves_after']}
            if (receipt != expected or not ledger or ledger['origin'] != 'attempt.' + binding['kind'].lower() + '/' + binding['operation_id']
                    or json.loads(ledger['delta_json']) != delta or action.get('receiptId') != binding['receipt_id']
                    or action.get('ax') != binding['x'] or action.get('ay') != binding['y']):
                raise ServiceError(409, 'paid_action_binding_mismatch')
        continues = sum(row['kind'] == 'Continue' for row in bindings)
        if attempt['continues'] != continues or attempt['moves'] != self.pins['levels'][attempt['level'] - 1]['moves'] + continues * 5:
            raise ServiceError(409, 'paid_action_binding_mismatch')

    def _view(self, db, actor, operation, *, error=None):
        if operation['state'] in ('Committed', 'Rejected') and operation['response_json']:
            return json.loads(operation['response_json'])
        replay = db.execute('SELECT * FROM replay_attempts WHERE attempt_id=?', (operation['attempt_id'],)).fetchone()
        return {'operationId': operation['command_id'], 'attemptId': operation['attempt_id'], 'state': operation['state'] if operation['state'] == 'Rejected' else 'Pending',
            'prefixRevision': replay['revision'], 'acceptedActions': len(json.loads(replay['prefix_json'])),
            'model': None if not replay['checkpoint_sha'] else {'outcome': replay['outcome'], 'moves': replay['moves'], 'turn': replay['turn'], 'checkpointSHA256': replay['checkpoint_sha']},
            'wallet': self.wallet._view(db, actor), 'attempt': self.wallet._attempt_view(self.wallet._attempt(db, actor, operation['attempt_id'])),
            'addedMoves': 0, 'paidReceiptId': '', 'displayReceipt': None, 'acknowledgementRequired': replay['outcome'] == 'No legal moves',
            'code': error or operation['error_code'], 'productionEnabled': production_enabled(self.authority)}

    def get(self, actor, attempt_id, command_id):
        with self.database.transaction() as db:
            actor = self.authority._transaction_actor(db, actor)
            self._guard(db, actor); self.wallet._attempt(db, actor, attempt_id)
            operation = db.execute('SELECT * FROM replay_operations WHERE player_id=? AND attempt_id=? AND command_id=?', (actor.player, attempt_id, command_id)).fetchone()
            if operation is None: raise ServiceError(404, 'gameplay_operation_not_found')
            return self._view(db, actor, operation)

    def submit(self, actor, attempt_id, kind, request):
        types = {'Verify': VerifyReplay, 'Tool': ReplayTool, 'Continue': ReplayContinue}
        if kind not in types or type(request) is not types[kind]: raise ServiceError(422, 'invalid_gameplay_request')
        body = request.model_dump(); digest = sha256(canonical(body).encode())
        with self.database.transaction() as db:
            actor = self.authority._transaction_actor(db, actor)
            self._guard(db, actor); attempt = self.wallet._attempt(db, actor, attempt_id)
            old = db.execute('SELECT * FROM replay_operations WHERE player_id=? AND command_id=?', (actor.player, request.commandId)).fetchone()
            if old:
                if old['attempt_id'] != attempt_id or old['kind'] != kind or old['request_hash'] != digest: raise ServiceError(409, 'gameplay_command_conflict')
                if old['state'] in ('Committed', 'Rejected'): return self._view(db, actor, old)
            else:
                replay = self._register(db, actor, attempt); self._integrity(db, actor, attempt, replay)
                if replay['revision'] != request.expectedPrefixRevision: raise ServiceError(409, 'gameplay_prefix_conflict')
                if db.execute("SELECT 1 FROM replay_operations WHERE attempt_id=? AND state IN ('Pending','Running')", (attempt_id,)).fetchone(): raise ServiceError(409, 'gameplay_operation_pending')
                if attempt['state'] not in ('Started', 'AwaitingContinuation'): raise ServiceError(409, 'attempt_state_conflict')
                db.execute('''INSERT INTO replay_operations(id,attempt_id,player_id,command_id,kind,request_hash,request_json,state,base_revision,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,'Pending',?,?,?)''', (uuid.uuid4().hex, attempt_id, actor.player, request.commandId, kind, digest, canonical(body), replay['revision'], actor.now, actor.now))
        return self.resume(actor, attempt_id, request.commandId)

    def _candidate(self, db, actor, operation, attempt, replay):
        self._integrity(db, actor, attempt, replay)
        if replay['revision'] != operation['base_revision']: raise ServiceError(409, 'gameplay_prefix_conflict')
        body = json.loads(operation['request_json']); actions, receipts = json.loads(replay['prefix_json']), json.loads(replay['receipts_json'])
        # Paid actions must leave room for every remaining move. Reject before
        # regeneration, worker dispatch or any paid debit. Accepted Swap/Tap
        # deltas each consume one move; the worker still verifies the history.
        needed = 6 if operation['kind'] == 'Continue' else int(operation['kind'] != 'Verify')
        if operation['kind'] == 'Tool': needed += max(0, replay['moves'] - len(body['actions']))
        if len(actions) + len(body['actions']) + needed > 1000: raise ServiceError(409, 'gameplay_history_capacity')
        if body['actions'] and replay['outcome'] != 'Playing': raise ServiceError(409, 'gameplay_not_playing')
        for move in body['actions']:
            if move['index'] != len(actions): raise ServiceError(409, 'gameplay_action_order')
            actions.append({'index': move['index'], 'kind': move['kind'], 'ax': move['x'], 'ay': move['y'],
                'bx': move['toX'], 'by': move['toY'], 'tool': -1, 'movesAfter': 0, 'receiptId': ''})
        self.wallet._regenerate(db, actor); balance = self.wallet._row(db, actor.player)
        if operation['kind'] != 'Verify':
            expected = body['expectedWalletRevision']
            if expected < balance['revision'] and not self._wallet_moved(db, actor, expected):
                expected = balance['revision']
            self.wallet._guard(db, actor, expected)
            values = json.loads(balance['balances'])
            if operation['kind'] == 'Continue':
                if body['actions'] or replay['outcome'] != 'Out of moves' or replay['moves'] != 0 or attempt['state'] != 'AwaitingContinuation': raise ServiceError(409, 'verified_out_of_moves_required')
                if values[0] < 900: raise ServiceError(409, 'insufficient_coins')
                tool, x, y, added = -1, -1, -1, 5
            else:
                if attempt['state'] != 'Started' or replay['outcome'] != 'Playing' or values[6 + body['tool']] <= 0: raise ServiceError(409, 'tool_unavailable')
                tool, x, y, added = body['tool'], body['x'], body['y'], 0
            # Simulation only. This exact deterministic ledger ID is checked
            # against the real atomic debit before any prefix/response commits.
            receipt_id = 'wallet/' + hashlib.sha256((actor.player + '|attempt.' + operation['kind'].lower() + '/' + operation['id']).encode()).hexdigest()
            index = len(actions); actions.append({'index': index, 'kind': operation['kind'], 'ax': x, 'ay': y, 'bx': -1, 'by': -1, 'tool': tool, 'movesAfter': added, 'receiptId': receipt_id})
            receipts.append({'receiptId': receipt_id, 'attemptId': attempt['id'], 'kind': operation['kind'], 'actionIndex': index, 'tool': tool, 'coins': 900 if added else 0, 'quantity': 0 if added else 1, 'movesAfter': added})
        job = {'version': 1, 'jobId': operation['id'], 'playerId': actor.player, 'attemptId': attempt['id'], 'pinsSHA256': self.pins_hash,
            'levelSHA256': replay['level_sha'], 'level': attempt['level'], 'initialMoves': self.pins['levels'][attempt['level'] - 1]['moves'],
            'seed': attempt['seed'], 'startReceiptId': replay['start_receipt_id'], 'starting': json.loads(attempt['selected_json']), 'actions': actions, 'receipts': receipts}
        encode_job(job)
        snapshot = {'walletRevision': balance['revision'], 'attemptState': attempt['state'], 'moves': attempt['moves'], 'continues': attempt['continues'],
                    'prefixHash': sha256((replay['prefix_json'] + replay['receipts_json']).encode())}
        return job, snapshot

    # One worker runs at a time. With the dispatcher on, operations run in arrival order and a
    # background thread keeps going without waiting for each client's next poll. A client's own
    # request still runs the job when it is first in line, so a quiet server answers directly.
    def queue_depth(self):
        with self._queue_lock:
            return len(self._waiting)

    def stop_dispatcher(self):
        with self._queue_lock:
            self._stopped = True

    def _remember(self, operation, actor, attempt_id, command_id):
        if not self.dispatcher:
            return
        with self._queue_lock:
            entry = self._waiting.get(operation)
            if entry is None:
                self._waiting[operation] = _Waiting(actor, attempt_id, command_id)
            else:
                entry.actor = actor

    def _forget(self, operation, *, succeeded=False):
        if not self.dispatcher:
            return
        with self._queue_lock:
            self._waiting.pop(operation, None)
            if succeeded:
                self._successes += 1

    def _ready(self, entry, now):
        return entry.actor is not None and not entry.running and entry.not_before <= now

    def _ahead(self, operation):
        """Whether another ready operation should run before this one, and this one's place."""
        if not self.dispatcher:
            return False, 0
        now = time.monotonic()
        with self._queue_lock:
            own = self._waiting.get(operation)
            cooling = own is not None and own.not_before > now
            first, place, seen = False, 1, False
            for key, entry in self._waiting.items():
                if key == operation:
                    seen = True
                    continue
                if not seen and entry.actor is not None:
                    place += 1
                if self._ready(entry, now) and (cooling or not seen):
                    first = True
            return first, place

    def _note_failure(self, operation):
        """Send a failed job to the back of the line. True when it must stop being retried.

        A job that fails while others succeed is the job's fault. If nothing succeeds the worker
        itself is out, so the player's result waits for it to return, with a final limit.
        """
        if not self.dispatcher:
            return False
        now = time.monotonic()
        with self._queue_lock:
            entry = self._waiting.get(operation)
            if entry is None:
                return False
            if not entry.failures:
                entry.first_failure, entry.successes = now, self._successes
            entry.failures += 1
            entry.not_before = now + min(FIRST_RETRY_SECONDS * 2 ** (entry.failures - 1), LONGEST_RETRY_SECONDS)
            self._waiting[operation] = self._waiting.pop(operation)
            return (entry.failures >= FAILURES_WHEN_OTHERS_SUCCEED and self._successes > entry.successes
                    or entry.failures >= FAILURES_WITHOUT_ANY_SUCCESS and now - entry.first_failure >= OUTAGE_PATIENCE_SECONDS)

    def _kick(self):
        if not self.dispatcher:
            return
        now = time.monotonic()
        with self._queue_lock:
            if self._draining or self._stopped or not any(entry.actor is not None and not entry.running for entry in self._waiting.values()):
                return
            self._draining = True
        threading.Thread(target=self._drain, daemon=True, name='hotr-replay-dispatcher').start()

    def _drain(self):
        try:
            while True:
                now = time.monotonic()
                with self._queue_lock:
                    if self._stopped:
                        return
                    if not any(entry.actor is not None and not entry.running for entry in self._waiting.values()):
                        self._draining = False
                        return
                    selected = next(((key, entry) for key, entry in self._waiting.items() if self._ready(entry, now)), None)
                if selected is None:
                    time.sleep(.5)
                    continue
                key, entry = selected
                try:
                    _, ran = self._advance(entry.actor, entry.attempt, entry.command, dispatched=True)
                except ServiceError:
                    # Its credential lapsed or its account closed: nothing is lost, and the
                    # operation stays Pending until the client returns.
                    with self._queue_lock:
                        entry.actor = None
                except Exception:
                    self._note_failure(key)
                else:
                    if not ran:
                        time.sleep(.5)  # A client's own request holds the worker.
        finally:
            with self._queue_lock:
                self._draining = False

    def resume(self, actor, attempt_id, command_id):
        try:
            return self._advance(actor, attempt_id, command_id)[0]
        finally:
            self._kick()

    def _advance(self, actor, attempt_id, command_id, *, dispatched=False):
        view, token = self._claim(actor, attempt_id, command_id, dispatched)
        if token is None:
            return view, False
        job, snapshot, operation_id, actor = view
        return self._execute(actor, attempt_id, command_id, operation_id, token, job, snapshot), True

    def _waiting_view(self, db, actor, operation, place):
        view = self._view(db, actor, operation)
        if self.dispatcher and place:
            view['queuePosition'] = place
        return view

    def _claim(self, actor, attempt_id, command_id, dispatched):
        with self.database.transaction() as db:
            actor = self.authority._transaction_actor(db, actor)
            self._guard(db, actor); attempt = self.wallet._attempt(db, actor, attempt_id)
            operation = db.execute('SELECT * FROM replay_operations WHERE player_id=? AND attempt_id=? AND command_id=?', (actor.player, attempt_id, command_id)).fetchone()
            if not operation: raise ServiceError(404, 'gameplay_operation_not_found')
            if operation['state'] in ('Committed', 'Rejected'):
                self._forget(operation['id'])
                return self._view(db, actor, operation), None
            self._remember(operation['id'], actor, attempt_id, command_id)
            if operation['state'] == 'Running' and operation['lease_until'] > actor.now: return self._view(db, actor, operation), None
            slot = db.execute('SELECT * FROM replay_worker_slot WHERE id=1').fetchone()
            behind, place = self._ahead(operation['id'])
            if slot['lease_until'] > actor.now or behind and not dispatched: return self._waiting_view(db, actor, operation, place), None
            replay = db.execute('SELECT * FROM replay_attempts WHERE attempt_id=?', (attempt_id,)).fetchone()
            try:
                job, snapshot = self._candidate(db, actor, operation, attempt, replay)
            except (ServiceError, ReplayError) as error:
                code = error.code if isinstance(error, ServiceError) else 'invalid_gameplay_history'
                self._forget(operation['id'])
                return self._reject(db, actor, operation, code), None
            token = uuid.uuid4().hex
            db.execute("UPDATE replay_operations SET state='Running',lease_token=?,lease_until=?,candidate_json=?,snapshot_json=?,updated_at=? WHERE id=?", (token, actor.now + LEASE_SECONDS, canonical(job), canonical(snapshot), actor.now, operation['id']))
            db.execute('UPDATE replay_worker_slot SET operation_id=?,lease_token=?,lease_until=? WHERE id=1', (operation['id'], token, actor.now + LEASE_SECONDS))
            if self.dispatcher:
                with self._queue_lock:
                    entry = self._waiting.get(operation['id'])
                    if entry is not None:
                        entry.running = True
            return (job, snapshot, operation['id'], actor), token

    def _finished(self, operation_id, view, *, succeeded=False):
        if view.get('state') in ('Committed', 'Rejected'):
            self._forget(operation_id, succeeded=succeeded and view['state'] == 'Committed')
        return view

    def _failed(self, actor, attempt_id, command_id, operation_id, token, job, snapshot):
        if self._note_failure(operation_id):
            # The same no-charge route as a verified model fault: the attempt is Released, starting
            # items return, no life is charged and a prospective paid tool is not spent.
            proof = {'outputSHA256': sha256(('worker-retry-limit|' + operation_id).encode()), 'workerRetryLimit': True}
            return self._finished(operation_id, self._commit_fault(replace(actor, now=self.authority._now()), operation_id, token, job, snapshot, proof, reason='worker_retry_limit'))
        self._pending(operation_id, token, 'replay_temporarily_unavailable')
        return self.get(actor, attempt_id, command_id)

    def _execute(self, actor, attempt_id, command_id, operation_id, token, job, snapshot):
        try:
            try:
                proof = self.worker.run(job)
            except TrustedModelFault as failure:
                actor = replace(actor, now=self.authority._now())
                return self._finished(operation_id, self._commit_fault(actor, operation_id, token, job, snapshot, failure.proof), succeeded=True)
            result = proof['result']
            result = validate_output(canonical(result).encode(), job, encode_job(job))
            actor = replace(actor, now=self.authority._now())
            if self.checkpoint: self.checkpoint('AfterWorker')
            return self._finished(operation_id, self._commit(actor, operation_id, token, job, snapshot, result, proof), succeeded=True)
        except ReplayError:
            return self._failed(actor, attempt_id, command_id, operation_id, token, job, snapshot)
        except ServiceError as error:
            with self.database.transaction() as db:
                current = db.execute('SELECT * FROM replay_operations WHERE id=?', (operation_id,)).fetchone()
                if current['state'] == 'Running' and current['lease_token'] == token and error.status == 409:
                    self._guard(db, actor)
                    self._forget(operation_id)
                    return self._reject(db, actor, current, error.code)
            self._pending(operation_id, token, 'actor_reauthentication_required')
            raise
        except Exception:
            return self._failed(actor, attempt_id, command_id, operation_id, token, job, snapshot)
        finally:
            if self.dispatcher:
                with self._queue_lock:
                    entry = self._waiting.get(operation_id)
                    if entry is not None:
                        entry.running = False
            with self.database.transaction() as db:
                db.execute('UPDATE replay_worker_slot SET operation_id=NULL,lease_token=NULL,lease_until=0 WHERE id=1 AND lease_token=?', (token,))

    def _pending(self, operation, token, error):
        with self.database.transaction() as db:
            db.execute("UPDATE replay_operations SET state='Pending',lease_token=NULL,lease_until=0,error_code=? WHERE id=? AND state='Running' AND lease_token=?", (error, operation, token))

    def _wallet_moved(self, db, actor, revision):
        """Whether anything other than the regeneration of lives changed the wallet since revision."""
        return bool(db.execute("SELECT 1 FROM wallet_ledger WHERE player_id=? AND revision>? AND origin NOT LIKE 'life/regen/%' LIMIT 1", (actor.player, revision)).fetchone())

    def _commit_fault(self, actor, operation_id, token, job, snapshot, proof, *, reason='model_fault'):
        def run(db, actor):
            self._guard(db, actor)
            operation = db.execute('SELECT * FROM replay_operations WHERE id=?', (operation_id,)).fetchone()
            if operation['state'] != 'Running' or operation['lease_token'] != token:
                return self._view(db, actor, operation)
            attempt = self.wallet._attempt(db, actor, operation['attempt_id'])
            replay = db.execute('SELECT * FROM replay_attempts WHERE attempt_id=?', (attempt['id'],)).fetchone()
            self._integrity(db, actor, attempt, replay)
            self.wallet._regenerate(db, actor)
            if (replay['revision'] != operation['base_revision'] or snapshot['prefixHash'] != sha256((replay['prefix_json'] + replay['receipts_json']).encode())
                    or self._wallet_moved(db, actor, snapshot['walletRevision']) or snapshot['attemptState'] != attempt['state']
                    or snapshot['moves'] != attempt['moves'] or snapshot['continues'] != attempt['continues']):
                return self._reject(db, actor, operation, 'gameplay_snapshot_conflict')
            completed = self.authority._player(db, actor)['completed']
            request = SettleAttempt(commandId=operation_id, expectedRevision=self.wallet._row(db, actor.player)['revision'],
                playerId=actor.player, attemptId=attempt['id'], outcome='Fault', proofDigest=proof['outputSHA256'])
            settled = self.wallet._settle_in_transaction(db, actor, request, replay_key=self.wallet._replay_key)
            # The sealed fault response cannot identify its failing action.
            # Preserve only the previously verified prefix. A prospective tool
            # has no authorization/receipt yet and is retained, while every
            # previously committed tool/continue remains spent.
            response = self._view(db, actor, operation)
            response.update(state='Committed', model=None, addedMoves=0, paidReceiptId='', acknowledgementRequired=False, code='model_fault',
                displayReceipt={'receiptId': settled['receiptId'], 'outcome': 'Fault', 'awardedCoins': 0, 'awardedStars': 0,
                    'firstClear': False, 'completedBefore': completed, 'completedAfter': completed, 'livesAfter': settled['wallet']['lives']})
            audit = {'model': None, 'execution': proof, 'trustedFault': reason, 'candidatePromoted': False, 'prospectivePaidActionCharged': False}
            db.execute("UPDATE replay_operations SET state='Committed',lease_token=NULL,lease_until=0,candidate_json=NULL,result_json=?,response_json=?,error_code='model_fault',updated_at=? WHERE id=?",
                (canonical(audit), canonical(response), actor.now, operation_id))
            if self.checkpoint: self.checkpoint('BeforeCommit')
            return response
        response = self.authority._transaction(run, actor)
        if self.checkpoint: self.checkpoint('AfterCommit')
        return response

    def _reject(self, db, actor, operation, code):
        db.execute("UPDATE replay_operations SET state='Rejected',lease_token=NULL,lease_until=0,candidate_json=NULL,error_code=? WHERE id=?", (code, operation['id']))
        operation = db.execute('SELECT * FROM replay_operations WHERE id=?', (operation['id'],)).fetchone()
        response = self._view(db, actor, operation, error=code)
        db.execute('UPDATE replay_operations SET response_json=? WHERE id=?', (canonical(response), operation['id']))
        return response

    def _commit(self, actor, operation_id, token, job, snapshot, result, proof):
        def run(db, actor):
            self._guard(db, actor)
            operation = db.execute('SELECT * FROM replay_operations WHERE id=?', (operation_id,)).fetchone()
            if operation['state'] != 'Running' or operation['lease_token'] != token:
                return self._view(db, actor, operation)
            attempt = self.wallet._attempt(db, actor, operation['attempt_id']); replay = db.execute('SELECT * FROM replay_attempts WHERE attempt_id=?', (attempt['id'],)).fetchone()
            self._integrity(db, actor, attempt, replay)
            self.wallet._regenerate(db, actor)
            if (replay['revision'] != operation['base_revision'] or snapshot['prefixHash'] != sha256((replay['prefix_json'] + replay['receipts_json']).encode())
                    or self._wallet_moved(db, actor, snapshot['walletRevision']) or snapshot['attemptState'] != attempt['state']
                    or snapshot['moves'] != attempt['moves'] or snapshot['continues'] != attempt['continues']):
                return self._reject(db, actor, operation, 'gameplay_snapshot_conflict')
            completed_before = self.authority._player(db, actor)['completed']; old_reward = db.execute("SELECT 1 FROM rewards WHERE player_id=? AND source='level' AND source_key=?", (actor.player, attempt['id'])).fetchone()
            if operation['kind'] != 'Verify':
                body = json.loads(operation['request_json']); revision = self.wallet._row(db, actor.player)['revision']
                request = SpendTool(commandId=operation_id, expectedRevision=revision, tool=body['tool']) if operation['kind'] == 'Tool' else WalletCommand(commandId=operation_id, expectedRevision=revision)
                paid = self.wallet._command_in_transaction(db, actor, attempt['id'], operation['kind'].lower(), request, replay_key=self.wallet._replay_key)
                action, receipt = job['actions'][-1], job['receipts'][-1]
                if paid['receiptId'] != receipt['receiptId']: raise ServiceError(409, 'paid_action_binding_mismatch')
                db.execute('INSERT INTO replay_paid_bindings VALUES(?,?,?,?,?,?,?,?,?)', (paid['receiptId'], attempt['id'], operation_id, action['index'], operation['kind'], action['tool'], action['ax'], action['ay'], action['movesAfter']))
            display = None
            terminal = 'Won' if result['outcome'] == 'Won' else 'OutOfMoves' if result['outcome'] == 'Out of moves' and attempt['state'] == 'Started' else None
            if terminal:
                request = SettleAttempt(commandId=operation_id, expectedRevision=self.wallet._row(db, actor.player)['revision'], playerId=actor.player, attemptId=attempt['id'], outcome=terminal, proofDigest=result['checkpointSHA256'])
                settled = self.wallet._settle_in_transaction(db, actor, request, replay_key=self.wallet._replay_key)
                grant = db.execute("SELECT grant_json FROM rewards WHERE player_id=? AND source='level' AND source_key=?", (actor.player, attempt['id'])).fetchone()
                awarded = json.loads(grant['grant_json']) if grant and not old_reward else {}
                display = {'receiptId': settled['receiptId'], 'outcome': terminal, 'awardedCoins': awarded.get('coins', 0), 'awardedStars': awarded.get('stars', 0),
                    'firstClear': bool(grant and not old_reward), 'completedBefore': completed_before, 'completedAfter': self.authority._player(db, actor)['completed'], 'livesAfter': settled['wallet']['lives']}
            db.execute('''UPDATE replay_attempts SET prefix_json=?,receipts_json=?,revision=revision+1,checkpoint_sha=?,outcome=?,moves=?,turn=?,updated_at=? WHERE attempt_id=?''',
                (canonical(job['actions']), canonical(job['receipts']), result['checkpointSHA256'], result['outcome'], result['moves'], result['turn'], actor.now, attempt['id']))
            current = db.execute('SELECT * FROM replay_operations WHERE id=?', (operation_id,)).fetchone()
            response = self._view(db, actor, current); response.update(state='Committed', addedMoves=5 if operation['kind'] == 'Continue' else 0,
                paidReceiptId=paid['receiptId'] if operation['kind'] != 'Verify' else '', displayReceipt=display, code='')
            audit = {'model': result, 'execution': {key: proof[key] for key in ('process', 'approvalSHA256', 'jobSHA256', 'outputSHA256') if key in proof}}
            db.execute("UPDATE replay_operations SET state='Committed',lease_token=NULL,lease_until=0,candidate_json=NULL,result_json=?,response_json=?,error_code='',updated_at=? WHERE id=?", (canonical(audit), canonical(response), actor.now, operation_id))
            if self.checkpoint: self.checkpoint('BeforeCommit')
            return response
        response = self.authority._transaction(run, actor)
        if self.checkpoint: self.checkpoint('AfterCommit')
        return response

    def abandon(self, actor, attempt_id, request):
        def run(db, actor):
            self._guard(db, actor)
            def execute():
                attempt = self.wallet._attempt(db, actor, attempt_id)
                if attempt['state'] == 'Won': raise ServiceError(409, 'attempt_already_won')
                before = self.authority._player(db, actor)['completed']
                # Fence an in-flight result before forfeit. Keep its global slot
                # until its real process finishes or the lease expires.
                rows = db.execute("SELECT * FROM replay_operations WHERE attempt_id=? AND state IN ('Pending','Running')", (attempt_id,)).fetchall()
                for operation in rows: self._reject(db, actor, operation, 'player_forfeit')
                paid = self.wallet._command_in_transaction(db, actor, attempt_id, 'quit', request, replay_key=self.wallet._replay_key)
                return {**paid, 'displayReceipt': {'receiptId': paid['receiptId'], 'outcome': 'Lost', 'awardedCoins': 0, 'awardedStars': 0, 'firstClear': False,
                    'completedBefore': before, 'completedAfter': self.authority._player(db, actor)['completed'], 'livesAfter': paid['wallet']['lives']}, 'productionEnabled': production_enabled(self.authority)}
            return self.authority._command(db, actor, 'gameplay.abandon', request.commandId, {'attemptId': attempt_id, **request.model_dump()}, execute)
        return self.authority._transaction(run, actor)
