"""Experimental explicit staging-only atomic attempt binding.

Not registered in create_app, migrations, CLI, or production configuration.
A caller must provide an independently provisioned isolated schema, verify
operator provenance for old attempts, and integrate/verify the whole replay
broker before activation. Missing bindings fail closed; no legacy inference.
"""
import hashlib
import json
import uuid

from .replay_contract import ReplayError
from .replay_versions117 import AttemptVersion, WorkerRegistry
from .replay_service import ReplayBroker
from .service import ServiceError
from .storage import canonical
from .wallet import ZERO
from .wallet_schemas import ReserveAttempt, WalletCommand

# DDL is deliberately not installed by application startup or Database.
STAGING_BINDINGS_DDL = """
CREATE TABLE staging_attempt_version117 (
 attempt_id TEXT PRIMARY KEY REFERENCES gameplay_attempts(id),
 approval_sha256 TEXT NOT NULL, pins_sha256 TEXT NOT NULL,
 level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 50),
 level_sha256 TEXT NOT NULL, initial_moves INTEGER NOT NULL CHECK(initial_moves BETWEEN 1 AND 1000));
CREATE TRIGGER staging_attempt_version117_immutable BEFORE UPDATE ON staging_attempt_version117
 BEGIN SELECT RAISE(ABORT, 'attempt version is immutable'); END;
"""


class StagingBoundAttempts:
    """Unexposed staging component; wallet/registry must be operator-created."""
    def __init__(self, wallet, registry):
        if type(registry) is not WorkerRegistry:
            raise ReplayError('invalid_worker_registry')
        self.wallet, self.authority, self.registry = wallet, wallet.authority, registry
        self.checkpoint = None  # in-process fault injection only, never an HTTP callback

    def _binding(self, db, actor, attempt_id):
        attempt = self.wallet._attempt(db, actor, attempt_id)
        row = db.execute('SELECT * FROM staging_attempt_version117 WHERE attempt_id=?', (attempt_id,)).fetchone()
        if row is None:
            raise ServiceError(409, 'attempt_version_missing')
        binding = AttemptVersion(row['approval_sha256'], row['pins_sha256'], row['level'], row['level_sha256'], row['initial_moves'])
        if (attempt['level'] != binding.level or attempt['config_hash'] != binding.level_sha256
                or attempt['moves'] != binding.initial_moves + attempt['continues'] * 5):
            raise ServiceError(409, 'attempt_configuration_mismatch')
        try:
            worker = self.registry.resolve_metadata(binding)
        except ReplayError:
            raise ServiceError(503, 'attempt_worker_unavailable') from None
        return binding, worker

    def reserve(self, actor, request):
        """Like Wallet.reserve, with version and attempt committed atomically."""
        if type(request) is not ReserveAttempt:
            raise ServiceError(422, 'invalid_gameplay_request')
        # Full bundle hashing can be expensive. Preflight outside SQLite's
        # write transaction; the transaction checks exact cached pin metadata.
        try:
            self.registry.verify_all()
        except ReplayError:
            raise ServiceError(503, 'attempt_worker_unavailable') from None
        def run(db, current):
            def execute():
                row = self.wallet._guard(db, current, request.expectedRevision)
                values = json.loads(row['balances'])
                if values[10] <= 0:
                    raise ServiceError(409, 'no_lives')
                if request.level > self.authority._player(db, current)['completed'] + 1:
                    raise ServiceError(409, 'level_locked')
                if any(b < n for b, n in zip(values[2:6], request.starting, strict=True)):
                    raise ServiceError(409, 'insufficient_inventory')
                if db.execute("SELECT 1 FROM gameplay_attempts WHERE player_id=? AND state IN ('Reserved','Started','AwaitingContinuation')", (current.player,)).fetchone():
                    raise ServiceError(409, 'attempt_active')
                level = self.wallet.catalog.levels[request.level - 1]
                try:
                    binding = self.registry.reserve_binding_metadata(request.level, level.configHash, level.moves)
                except ReplayError:
                    raise ServiceError(503, 'attempt_worker_unavailable') from None
                attempt_id = uuid.uuid4().hex
                seed = int(hashlib.sha256(('hotr-attempt-seed-v1|' + attempt_id).encode()).hexdigest()[:8], 16) or 1
                db.execute("""INSERT INTO gameplay_attempts
                    (id,player_id,level,config_hash,seed,selected_json,moves,state,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,'Reserved',?,?)""",
                    (attempt_id,current.player,request.level,level.configHash,seed,canonical(request.starting),level.moves,current.now,current.now))
                db.execute('INSERT INTO staging_attempt_version117 VALUES(?,?,?,?,?,?)', (attempt_id,binding.approval_sha256,binding.pins_sha256,binding.level,binding.level_sha256,binding.initial_moves))
                if self.checkpoint: self.checkpoint('AfterBinding')
                return self.wallet._response(db,current,'attempt.reserve',request,ZERO,attempt_id)
            response = self.authority._command(db,current,'wallet.reserve',request.commandId,request.model_dump(),execute)
            # A retry cannot silently adopt an unbound older attempt or an
            # unavailable version, even when the wallet command was cached.
            self._binding(db,current,response['attempt']['attemptId'])
            return response
        return self.wallet._transaction(run, actor)

    def worker_for_attempt(self, actor, attempt_id):
        """Return only the persisted owner-bound worker; no player selection."""
        with self.wallet.database.transaction() as db:
            current = self.authority._transaction_actor(db, actor)
            binding, _ = self._binding(db,current,attempt_id)
        try:
            worker = self.registry.resolve(binding)
        except ReplayError:
            raise ServiceError(503, 'attempt_worker_unavailable') from None
        return binding, worker

    def start(self, actor, attempt_id, request):
        """Verify outside the transaction; fence the same binding before debit."""
        if type(request) is not WalletCommand:
            raise ServiceError(422, 'invalid_gameplay_request')
        verified, _ = self.worker_for_attempt(actor, attempt_id)
        def run(db, current):
            binding, _ = self._binding(db, current, attempt_id)
            if binding != verified:
                raise ServiceError(409, 'attempt_configuration_mismatch')
            return self.wallet._command_in_transaction(db, current, attempt_id, 'start', request)
        return self.wallet._transaction(run, actor)

    def execute_server_job(self, actor, attempt_id, job):
        """Route an already authorized server-built job, never an HTTP payload.

        This is not a replay broker: it neither validates the saved action
        prefix nor commits results, receipts, ledger entries, or settlements.
        A future broker must do those checks and revalidate the binding at commit.
        """
        binding, _ = self.worker_for_attempt(actor, attempt_id)
        if type(job) is not dict or job.get('playerId') != actor.player or job.get('attemptId') != attempt_id:
            raise ServiceError(409, 'attempt_configuration_mismatch')
        return self.registry.run(binding, job)


class _BoundReplayBroker(ReplayBroker):
    """Real broker behavior with a fixed approved worker and binding fence."""
    def __init__(self, attempts, approval, worker, pins_sha):
        self.attempts, self.approval = attempts, approval
        self.authority, self.wallet = attempts.authority, attempts.wallet
        self.database, self.worker, self.enabled, self.checkpoint = self.wallet.database, worker, True, None
        _, self.pins, self.pins_hash = worker._verify_bundle()
        if self.pins_hash != pins_sha or worker.approval_sha256 != approval:
            raise ReplayError('attempt_version_mismatch')
        self.wallet.replay_enabled = True

    def _check_binding(self, db, actor, attempt):
        binding, worker = self.attempts._binding(db, actor, attempt['id'])
        if binding.approval_sha256 != self.approval or binding.pins_sha256 != self.pins_hash or worker is not self.worker:
            raise ServiceError(409, 'attempt_configuration_mismatch')

    def _register(self, db, actor, attempt):
        self._check_binding(db, actor, attempt)
        return super()._register(db, actor, attempt)

    def _integrity(self, db, actor, attempt, replay):
        # Called inside the existing broker's candidate and commit transactions,
        # including the model-fault release path, before any financial mutation.
        self._check_binding(db, actor, attempt)
        return super()._integrity(db, actor, attempt, replay)

    def _commit(self, actor, operation_id, token, job, snapshot, result, proof):
        if proof.get('approvalSHA256') != self.approval:
            raise ReplayError('attempt_version_mismatch')
        return super()._commit(actor, operation_id, token, job, snapshot, result, proof)

    def _commit_fault(self, actor, operation_id, token, job, snapshot, proof):
        if proof.get('approvalSHA256') != self.approval:
            raise ReplayError('attempt_version_mismatch')
        return super()._commit_fault(actor, operation_id, token, job, snapshot, proof)


class StagingVersionedReplay:
    """Unregistered adapter using the real ReplayBroker state/ledger logic.

    Requires the experimental binding table; never migrates or infers a legacy
    version. No production/staging launcher, route or default is changed.
    """
    def __init__(self, attempts):
        if type(attempts) is not StagingBoundAttempts:
            raise ReplayError('invalid_attempt_binding')
        self.attempts = attempts
        self.enabled = True
        self._brokers = {}
        for approval, (worker, pins_sha, _) in attempts.registry._workers.items():
            self._brokers[approval] = _BoundReplayBroker(attempts, approval, worker, pins_sha)

    def _for(self, actor, attempt_id):
        binding, worker = self.attempts.worker_for_attempt(actor, attempt_id)
        broker = self._brokers.get(binding.approval_sha256)
        if broker is None or broker.worker is not worker:
            raise ServiceError(503, 'attempt_worker_unavailable')
        return broker

    def submit(self, actor, attempt_id, kind, request):
        return self._for(actor, attempt_id).submit(actor, attempt_id, kind, request)

    def get(self, actor, attempt_id, command_id):
        return self._for(actor, attempt_id).get(actor, attempt_id, command_id)

    def resume(self, actor, attempt_id, command_id):
        return self._for(actor, attempt_id).resume(actor, attempt_id, command_id)

    def abandon(self, actor, attempt_id, request):
        return self._for(actor, attempt_id).abandon(actor, attempt_id, request)
