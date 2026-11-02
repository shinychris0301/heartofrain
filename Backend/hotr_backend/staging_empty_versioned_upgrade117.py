"""Stopped, owner-bound schema15->16 preparation for empty gameplay history.

No historical worker attribution is inferred or accepted. A database with any
attempt or replay history is refused. Preparation does not start a service or
activate a catalog; its marker deliberately blocks the legacy launcher.
"""
import argparse
from contextlib import closing
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid

from . import staging105 as staging
from . import staging_ops105 as snapshots
from .operations import OperationError, _expected, _objects, _validate, backup_database
from .storage import canonical
from .staging_versioned_replay117 import STAGING_BINDINGS_DDL

PENDING = 'VersionedUpgradePending117'
PREPARED = 'VersionedPrepared117'
STATES = ('Ready', PENDING, PREPARED)


class UpgradeError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(value, code):
    if not value:
        raise UpgradeError(code)


def _checkpoint(stage):
    """Private controlled-test interruption seam; not exposed over HTTP."""


def _file_identity(path):
    snapshots._regular(path)
    s = path.stat()
    _need(s.st_size > 0, 'versioned_upgrade_database_missing')
    return {'device': s.st_dev, 'inode': s.st_ino}


@lru_cache(maxsize=1)
def _expected16():
    with closing(sqlite3.connect(':memory:')) as db:
        original = _expected(15)
        for kind in ('table', 'index', 'trigger', 'view'):
            for typ, _, _, sql in original:
                if typ == kind:
                    db.execute(sql)
        db.executescript(STAGING_BINDINGS_DDL)
        return _objects(db)


def _validate16(db):
    _need(db.execute('PRAGMA quick_check').fetchall() == [('ok',)], 'versioned_upgrade_integrity_failed')
    _need(db.execute('PRAGMA foreign_key_check').fetchone() is None, 'versioned_upgrade_foreign_key_failed')
    _need(db.execute('SELECT version FROM schema_info').fetchall() == [(16,)], 'versioned_upgrade_schema16_required')
    _need(_objects(db) == _expected16(), 'versioned_upgrade_schema16_mismatch')


def _logical15(db):
    """Hash all original tables and SQLite sequences, excluding schema_info."""
    digest = hashlib.sha256()
    with closing(sqlite3.connect(':memory:')) as expected:
        for kind, _, _, sql in _expected(15):
            if kind == 'table':
                expected.execute(sql)
        tables = [r[0] for r in expected.execute("SELECT name FROM sqlite_master WHERE type='table' AND name<>'schema_info' ORDER BY name")]
        for table in tables:
            cols = [r[1] for r in expected.execute('PRAGMA table_info("' + table + '")')]
            names = ','.join('"' + x + '"' for x in cols)
            digest.update(canonical([table, cols]).encode('ascii'))
            for row in db.execute('SELECT ' + names + ' FROM "' + table + '" ORDER BY ' + names):
                digest.update(canonical(list(row)).encode('ascii'))
                digest.update(b'\n')
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='sqlite_sequence'").fetchone():
            digest.update(b'sqlite_sequence\n')
            for row in db.execute('SELECT name,seq FROM sqlite_sequence ORDER BY name'):
                digest.update(canonical(list(row)).encode('ascii'))
                digest.update(b'\n')
    return digest.hexdigest()


def _empty_history(db):
    for table in ('gameplay_attempts', 'replay_attempts', 'replay_operations', 'replay_paid_bindings'):
        _need(db.execute('SELECT 1 FROM ' + table + ' LIMIT 1').fetchone() is None,
              'versioned_upgrade_legacy_history_requires_provenance')
    slot = db.execute('SELECT operation_id,lease_token,lease_until FROM replay_worker_slot WHERE id=1').fetchone()
    _need(slot is not None and slot[0] is None and slot[1] is None and slot[2] == 0,
          'versioned_upgrade_worker_slot_not_empty')


def _paths(m, name):
    directory = m.data_directory / 'backups'
    snapshots._plain(directory)
    _need(directory.is_dir(), 'versioned_upgrade_backup_directory_missing')
    return directory / (name + '.schema15.sqlite3'), directory / (name + '.versioned117.json')


def _read_proof(path, marker, name, ready_bytes):
    snapshots._regular(path)
    _need(2 <= path.stat().st_size <= 4096, 'versioned_upgrade_receipt_invalid')
    value = staging._json(path.read_bytes())
    keys = {'version', 'kind', 'state', 'operationId', 'deploymentId', 'publicOrigin', 'identityScope', 'nonce',
            'backupName', 'snapshotSHA256', 'snapshotBytes', 'sourceLogicalSHA256', 'sourceFileIdentity',
            'readyMarkerSHA256', 'fromSchema', 'toSchema', 'emptyHistoryVerified'}
    _need(type(value) is dict and set(value) == keys, 'versioned_upgrade_receipt_invalid')
    _need(type(value['version']) is int and value['version'] == 1 and value['kind'] == 'HeartOfTheRainEmptyVersionedUpgrade117'
          and value['state'] in ('ReadyBackup', 'Complete') and value['fromSchema'] == 15 and value['toSchema'] == 16
          and value['emptyHistoryVerified'] is True, 'versioned_upgrade_receipt_invalid')
    _need(value['backupName'] == name and all(value[k] == v for k, v in snapshots._binding(marker).items()), 'versioned_upgrade_owner_mismatch')
    _need(type(value['operationId']) is str and re.fullmatch(r'[a-f0-9]{32}', value['operationId']), 'versioned_upgrade_receipt_invalid')
    for key in ('snapshotSHA256', 'sourceLogicalSHA256', 'readyMarkerSHA256'):
        _need(type(value[key]) is str and re.fullmatch(r'[a-f0-9]{64}', value[key]), 'versioned_upgrade_receipt_invalid')
    identity = value['sourceFileIdentity']
    _need(type(identity) is dict and set(identity) == {'device', 'inode'} and all(type(v) is int and v >= 0 for v in identity.values())
          and type(value['snapshotBytes']) is int and value['snapshotBytes'] > 0, 'versioned_upgrade_receipt_invalid')
    _need(value['readyMarkerSHA256'] == hashlib.sha256(ready_bytes).hexdigest() and path.read_bytes() == snapshots._bytes(value), 'versioned_upgrade_receipt_invalid')
    return value


def _snapshot_proven(path, proof):
    snapshots._regular(path)
    _need(not any(os.path.lexists(Path(str(path) + suffix)) for suffix in ('-wal', '-shm', '-journal')), 'versioned_upgrade_snapshot_sidecar_rejected')
    _need(snapshots._digest(path) == (proof['snapshotSHA256'], proof['snapshotBytes']), 'versioned_upgrade_snapshot_hash_mismatch')
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, isolation_level=None)) as db:
        _need(_validate(db) == 15 and _logical15(db) == proof['sourceLogicalSHA256'], 'versioned_upgrade_snapshot_state_mismatch')
        _empty_history(db)


def prepare_empty_authority(manifest_or_path, name, *, confirm_empty_history=False, timeout_seconds=60):
    """Make a backed-up, resumable schema16 candidate, never activating it."""
    _need(confirm_empty_history is True, 'versioned_upgrade_explicit_empty_history_confirmation_required')
    name = snapshots._name(name)
    _need(len(name) <= 40, 'versioned_upgrade_name_too_long')
    snapshots._timeout(timeout_seconds)
    m = staging.read_manifest(manifest_or_path)
    try:
        with staging._lock(m, staging.RUNTIME_LOCK, allowed_states=STATES):
            with staging.root_lock(m, allowed_states=STATES):
                marker = staging.ownership_metadata(m, allowed_states=STATES)
                source = staging.owned_database(m, allowed_states=STATES)
                staging._require_ads_policy(m)
                marker_path = m.data_directory / staging.MARKER
                _need(marker_path.read_bytes() == snapshots._bytes(marker), 'versioned_upgrade_marker_changed')
                ready = dict(marker, state='Ready')
                ready_bytes = snapshots._bytes(ready)
                snapshot, receipt = _paths(m, name)
                identity = _file_identity(source)
                proof = _read_proof(receipt, marker, name, ready_bytes) if os.path.lexists(receipt) else None
                if marker['state'] in (PENDING, PREPARED):
                    _need(proof is not None, 'versioned_upgrade_pending_receipt_required')
                if proof:
                    _snapshot_proven(snapshot, proof)
                    _need(proof['sourceFileIdentity'] == identity, 'versioned_upgrade_database_replaced')
                else:
                    snapshots._fresh(snapshot)
                    snapshots._fresh(receipt)
                with closing(sqlite3.connect(source.as_uri() + '?mode=rw', uri=True, timeout=timeout_seconds, isolation_level=None)) as db:
                    db.execute('PRAGMA foreign_keys=ON')
                    db.execute('PRAGMA synchronous=FULL')
                    db.execute('BEGIN IMMEDIATE')
                    try:
                        version = db.execute('SELECT version FROM schema_info').fetchall()
                        _need(_file_identity(source) == identity, 'versioned_upgrade_database_replaced')
                        if version == [(15,)]:
                            _need(_validate(db) == 15, 'versioned_upgrade_schema15_required')
                        elif version == [(16,)]:
                            _validate16(db)
                        else:
                            raise UpgradeError('versioned_upgrade_schema_invalid')
                        if proof and marker['state'] == PREPARED:
                            _need(proof['state'] == 'Complete' and version == [(16,)] and _logical15(db) == proof['sourceLogicalSHA256'], 'versioned_upgrade_prepared_state_changed')
                            _empty_history(db)
                            _need(db.execute('SELECT 1 FROM staging_attempt_version117 LIMIT 1').fetchone() is None, 'versioned_upgrade_prepared_state_changed')
                            db.rollback()
                            return _result(name, proof, True)
                        if proof:
                            _need(version in ([(15,)], [(16,)]) and _logical15(db) == proof['sourceLogicalSHA256'], 'versioned_upgrade_source_state_changed')
                            if version == [(16,)]:
                                _need(marker['state'] == PENDING, 'versioned_upgrade_pending_marker_required')
                                _need(db.execute('SELECT 1 FROM staging_attempt_version117 LIMIT 1').fetchone() is None, 'versioned_upgrade_source_state_changed')
                        else:
                            _need(version == [(15,)] and marker['state'] == 'Ready', 'versioned_upgrade_schema15_required')
                            _empty_history(db)
                            logical = _logical15(db)
                            copied = backup_database(source, snapshot, timeout_seconds=timeout_seconds)
                            _need(copied['schemaVersion'] == 15, 'versioned_upgrade_schema15_backup_required')
                            proof = dict(version=1, kind='HeartOfTheRainEmptyVersionedUpgrade117', state='ReadyBackup', operationId=uuid.uuid4().hex,
                                         backupName=name, fromSchema=15, toSchema=16, emptyHistoryVerified=True,
                                         snapshotSHA256=copied['sha256'], snapshotBytes=copied['bytes'], sourceLogicalSHA256=logical,
                                         sourceFileIdentity=identity, readyMarkerSHA256=hashlib.sha256(ready_bytes).hexdigest(), **snapshots._binding(marker))
                            _snapshot_proven(snapshot, proof)
                            snapshots._exclusive(receipt, snapshots._bytes(proof))
                            _checkpoint('AfterBackupReady')
                        _empty_history(db)
                        if marker['state'] == 'Ready':
                            pending = dict(marker, state=PENDING)
                            snapshots._ready_receipt(marker_path, marker, pending)
                            marker = pending
                        _checkpoint('AfterPendingMarker')
                        if version == [(15,)]:
                            table, trigger = STAGING_BINDINGS_DDL.strip().split('CREATE TRIGGER', 1)
                            db.execute(table.strip().rstrip(';'))
                            db.execute('CREATE TRIGGER ' + trigger.strip().rstrip(';'))
                            db.execute('UPDATE schema_info SET version=16')
                        _validate16(db)
                        _need(_logical15(db) == proof['sourceLogicalSHA256'], 'versioned_upgrade_data_preservation_failed')
                        _need(_file_identity(source) == identity and marker_path.read_bytes() == snapshots._bytes(marker), 'versioned_upgrade_owner_or_file_changed')
                        _checkpoint('BeforeCommit')
                        db.commit()
                    except BaseException:
                        db.rollback()
                        raise
                _checkpoint('AfterCommit')
                if proof['state'] != 'Complete':
                    complete = dict(proof, state='Complete')
                    snapshots._ready_receipt(receipt, proof, complete)
                    proof = complete
                _checkpoint('AfterCompleteReceipt')
                prepared = dict(marker, state=PREPARED)
                _need(_file_identity(source) == identity, 'versioned_upgrade_database_replaced')
                snapshots._ready_receipt(marker_path, marker, prepared)
                _checkpoint('AfterPreparedMarker')
                return _result(name, proof, False)
    except OperationError:
        raise UpgradeError('versioned_upgrade_database_validation_failed') from None
    except sqlite3.Error:
        raise UpgradeError('versioned_upgrade_database_failed') from None
    except OSError:
        raise UpgradeError('versioned_upgrade_interrupted') from None


def _result(name, proof, repeated):
    return {'status': 'prepared', 'operation': 'staging_empty_versioned_upgrade117', 'fromSchema': 15, 'toSchema': 16,
            'backupName': name, 'snapshotSHA256': proof['snapshotSHA256'], 'alreadyCompleted': repeated,
            'emptyHistoryVerified': True, 'trustedLegacyAttestationValidated': False, 'legacyAttemptsBound': 0,
            'economyChanged': False, 'serviceStarted': False, 'multiWorkerActivated': False, 'productionEnabled': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--name', required=True)
    parser.add_argument('--confirm-empty-history', action='store_true')
    parser.add_argument('--timeout-seconds', type=int, default=60)
    try:
        args = parser.parse_args(argv)
        result = prepare_empty_authority(args.manifest, args.name, confirm_empty_history=args.confirm_empty_history, timeout_seconds=args.timeout_seconds)
        code = 0
    except (UpgradeError, staging.StagingError, snapshots.StagingOpsError) as error:
        result, code = {'status': 'blocked', 'code': error.code, 'productionEnabled': False}, 1
    except KeyboardInterrupt:
        result, code = {'status': 'blocked', 'code': 'versioned_upgrade_interrupted', 'productionEnabled': False}, 130
    except Exception:
        result, code = {'status': 'blocked', 'code': 'versioned_upgrade_failed', 'productionEnabled': False}, 1
    print(json.dumps(result, separators=(',', ':')))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
