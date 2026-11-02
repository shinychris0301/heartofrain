"""Read-only owner-locked assessment of replay-version cutover prerequisites.

This does not migrate, infer worker history, switch routes or activate a new
catalog. It intentionally leaves the existing single-worker staging flow alone.
"""
from contextlib import closing
import sqlite3

from . import staging105 as staging
from .operations import _validate
from .storage import SCHEMA_VERSION


def assess_versioned_cutover(manifest):
    """Inspect one stopped, owned Ready authority without disclosing row IDs.

    An empty authority has no legacy-attempt provenance to establish. Existing
    history requires separately verified full worker provenance; current config
    and level hashes are not proof. No attestation is accepted by this assessor.
    """
    m = staging.read_manifest(manifest)
    try:
        with staging._lock(m, staging.RUNTIME_LOCK, allowed_states=('Ready',)):
            with staging.root_lock(m, allowed_states=('Ready',)):
                path = staging.owned_database(m, allowed_states=('Ready',))
                staging._plain(path)
                with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1, isolation_level=None)) as db:
                    db.execute('PRAGMA query_only=ON')
                    db.execute('BEGIN')
                    if _validate(db) != SCHEMA_VERSION:
                        raise staging.StagingError('staging_current_schema_required')
                    counts = {state: count for state, count in db.execute('SELECT state,COUNT(*) FROM gameplay_attempts GROUP BY state')}
                    active = sum(counts.get(state, 0) for state in ('Reserved', 'Started', 'AwaitingContinuation'))
                    history = sum(counts.values())
                    operations = {state: count for state, count in db.execute('SELECT state,COUNT(*) FROM replay_operations GROUP BY state')}
                    replay_history = sum(operations.values())
                    unfinished = sum(operations.get(state, 0) for state in ('Pending', 'Running'))
                    slot = db.execute('SELECT operation_id,lease_token,lease_until FROM replay_worker_slot WHERE id=1').fetchone()
                    if slot is None:
                        raise staging.StagingError('staging_versioned_replay_slot_missing')
                    slot_occupied = slot[0] is not None or slot[1] is not None or slot[2] != 0
                    db.execute('ROLLBACK')
        blockers = ['versioned_routes_and_catalog_cutover_not_activated',
                    'approved_worker_artifacts_unverified',
                    'version_binding_retention_and_deletion_unverified']
        if history:
            blockers.append('nonempty_legacy_migration_unavailable')
            blockers.append('legacy_worker_provenance_requires_independent_evidence')
        else:
            blockers.append('explicit_empty_history_preparation_required')
        if active:
            blockers.append('active_legacy_attempts_require_preserved_routing')
        if replay_history:
            blockers.append('legacy_replay_history_requires_preserved_routing')
        if unfinished or slot_occupied:
            blockers.append('unfinished_replay_or_worker_slot_requires_reconciliation')
        return {'status': 'blocked', 'readOnly': True, 'schemaVersion': SCHEMA_VERSION,
                'productionEnabled': False, 'multiWorkerActivated': False,
                'existingStagingRoutingChanged': False,
                'legacyAttemptCount': history, 'activeLegacyAttemptCount': active,
                'legacyAttemptStates': counts, 'replayOperationStates': operations,
                'unfinishedReplayOperationCount': unfinished, 'workerSlotOccupied': slot_occupied,
                'legacyProvenance': 'requires_independent_evidence' if history else 'not_required_for_empty_attempt_history',
                'trustedAttestationValidated': False, 'blockers': blockers}
    except staging.StagingError:
        raise
    except Exception:
        raise staging.StagingError('staging_versioned_cutover_inspection_failed') from None
