"""Stopped, owned schema16/worker/catalog verification; never starts a service.

The versioned API and launcher are still not wired. This operator-only step
checks explicit approved workers and catalog input without trusting player input.
"""
from contextlib import closing, nullcontext
import hashlib
from pathlib import Path
import sqlite3

from . import staging105 as staging
from .replay_versions117 import AttemptVersion, WorkerRegistry
from .staging_empty_versioned_upgrade117 import PREPARED, _validate16
from .wallet_schemas import LevelCatalog


def verify_prepared_authority(manifest, registry, catalog_path, catalog_sha256, *, _locks_held=False):
    """Check catalog, worker approvals and bindings without inferring history."""
    m = staging.read_manifest(manifest)
    try:
        if type(registry) is not WorkerRegistry:
            raise staging.StagingError('versioned_preflight_registry_required')
        if not isinstance(catalog_sha256, str) or len(catalog_sha256) != 64 or any(c not in '0123456789abcdef' for c in catalog_sha256):
            raise staging.StagingError('versioned_preflight_catalog_hash_invalid')
        path = staging._private_path(Path(catalog_path))
        staging._plain(path)
        if not path.is_file() or not 2 <= path.stat().st_size <= 1_000_000:
            raise staging.StagingError('versioned_preflight_catalog_unavailable')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != catalog_sha256:
            raise staging.StagingError('versioned_preflight_catalog_mismatch')
        catalog = LevelCatalog.model_validate_json(raw)
        if [row.level for row in catalog.levels] != list(range(1, 51)):
            raise staging.StagingError('versioned_preflight_catalog_invalid')
        with nullcontext() if _locks_held else staging._lock(m, staging.RUNTIME_LOCK, allowed_states=(PREPARED,)):
            with nullcontext() if _locks_held else staging.root_lock(m, allowed_states=(PREPARED,)):
                staging.ownership_metadata(m, allowed_states=(PREPARED,))
                staging._require_ads_policy(m)
                dbpath = staging.owned_database(m, allowed_states=(PREPARED,))
                staging._plain(dbpath)
                if not dbpath.is_file() or dbpath.stat().st_size <= 0:
                    raise staging.StagingError('versioned_preflight_database_unavailable')
                # Bundle hashing stays outside the SQLite read transaction.
                registry.verify_all()
                for level in catalog.levels:
                    if level.sourceSHA256 != level.configHash:
                        raise staging.StagingError('versioned_preflight_catalog_mismatch')
                    registry.reserve_binding_metadata(level.level, level.configHash, level.moves)
                with closing(sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True, timeout=1, isolation_level=None)) as db:
                    db.execute('PRAGMA query_only=ON')
                    db.execute('BEGIN')
                    _validate16(db)
                    unbound = db.execute('SELECT COUNT(*) FROM gameplay_attempts a LEFT JOIN staging_attempt_version117 v ON v.attempt_id=a.id WHERE v.attempt_id IS NULL').fetchone()[0]
                    if unbound:
                        raise staging.StagingError('versioned_preflight_unbound_attempts')
                    records = db.execute('''SELECT a.level,a.config_hash,a.moves,a.continues,v.approval_sha256,v.pins_sha256,v.level,v.level_sha256,v.initial_moves
                                            FROM gameplay_attempts a JOIN staging_attempt_version117 v ON v.attempt_id=a.id''').fetchall()
                    for level, digest, moves, continues, approval, pins, bound_level, bound_hash, initial in records:
                        if level != bound_level or digest != bound_hash or moves != initial + continues * 5:
                            raise staging.StagingError('versioned_preflight_attempt_mismatch')
                        registry.resolve_metadata(AttemptVersion(approval, pins, bound_level, bound_hash, initial))
                    mismatch = db.execute('''SELECT 1 FROM replay_attempts r LEFT JOIN staging_attempt_version117 v ON v.attempt_id=r.attempt_id
                                             WHERE v.attempt_id IS NULL OR r.pins_sha!=v.pins_sha256 OR r.level_sha!=v.level_sha256 LIMIT 1''').fetchone()
                    if mismatch:
                        raise staging.StagingError('versioned_preflight_replay_mismatch')
                    pending = db.execute("SELECT COUNT(*) FROM replay_operations WHERE state IN ('Pending','Running')").fetchone()[0]
                    slot = db.execute('SELECT operation_id,lease_token,lease_until FROM replay_worker_slot WHERE id=1').fetchone()
                    if slot is None:
                        raise staging.StagingError('versioned_preflight_worker_slot_missing')
                    occupied = slot[0] is not None or slot[1] is not None or slot[2] != 0
                    db.execute('ROLLBACK')
        return {'status': 'verified_prepared_only', 'schemaVersion': 16, 'catalogSHA256': catalog_sha256,
                'attemptBindingsChecked': len(records), 'pendingReplayOperations': pending, 'workerSlotOccupied': occupied,
                'multiWorkerActivated': False, 'serviceStarted': False, 'productionEnabled': False,
                'historicalWorkerProvenanceInferred': False, 'productionReadinessVerified': False}
    except staging.StagingError:
        raise
    except Exception:
        raise staging.StagingError('versioned_preflight_validation_failed') from None
