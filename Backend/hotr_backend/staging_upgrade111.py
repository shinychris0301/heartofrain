"""Explicit stopped, owned schema12->13 upgrade; no activation or DB replacement.

An immutable schema12 snapshot is sealed before mutation. UpgradePending111
closes ordinary startup until the exact bound operation finishes or resumes.
"""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid

from . import staging105 as staging
from . import staging_ops105 as snapshots
from .operations import OperationError, _validate, backup_database
from .storage import SCHEMA_VERSION, canonical
from .team_mail_schema111 import TEAM_MAIL_V13_DDL

PENDING = 'UpgradePending111'
STATES = ('Ready', PENDING)


class UpgradeError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(ok, code):
    if not ok:
        raise UpgradeError(code)


def _checkpoint(stage):
    """In-process fault seam; no HTTP endpoint, ambient flag or user callback."""


def _file_identity(path):
    snapshots._regular(path)
    info = path.stat()
    _need(info.st_size > 0, 'staging_upgrade_database_missing_or_empty')
    return {'device': info.st_dev, 'inode': info.st_ino}


def _logical(db):
    """Fingerprint every old row and sequence, excluding only schema version.

    Used only with an independently validated known schema while stopped. No
    row or credential material is returned, printed or placed in a receipt.
    """
    digest = hashlib.sha256()
    from .operations import _expected
    with closing(sqlite3.connect(':memory:')) as expected:
        for kind, _, _, sql in _expected(12):
            if kind == 'table':
                expected.execute(sql)
        tables = [r[0] for r in expected.execute("SELECT name FROM sqlite_master WHERE type='table' AND name<>'schema_info' ORDER BY name")]
        for table in tables:
            columns = [r[1] for r in expected.execute('PRAGMA table_info(' + table + ')')]
            names = ','.join('"' + name + '"' for name in columns)
            digest.update(canonical([table, columns]).encode('ascii'))
            for row in db.execute('SELECT ' + names + ' FROM "' + table + '" ORDER BY ' + names):
                digest.update(canonical(list(row)).encode('ascii'))
                digest.update(b'\n')
    return digest.hexdigest()


def _paths(manifest, name):
    folder = manifest.data_directory / 'backups'
    snapshots._plain(folder)
    _need(folder.is_dir(), 'staging_upgrade_backup_directory_required')
    return folder / (name + '.schema12.sqlite3'), folder / (name + '.upgrade111.json')


def _read_proof(path, marker, name, ready_bytes):
    snapshots._regular(path)
    _need(2 <= path.stat().st_size <= 4096, 'staging_upgrade_receipt_invalid')
    value = staging._json(path.read_bytes())
    keys = {'version', 'kind', 'state', 'operationId', 'deploymentId', 'publicOrigin', 'identityScope', 'nonce',
            'backupName', 'snapshotSHA256', 'snapshotBytes', 'sourceLogicalSHA256', 'sourceFileIdentity',
            'readyMarkerSHA256', 'fromSchema', 'toSchema'}
    _need(type(value) is dict and set(value) == keys, 'staging_upgrade_receipt_invalid')
    _need(type(value['version']) is int and value['version'] == 1
          and value['kind'] == 'HeartOfTheRainTeamMailUpgrade111'
          and value['state'] in ('ReadyBackup', 'Complete'), 'staging_upgrade_receipt_invalid')
    _need(type(value['fromSchema']) is int and value['fromSchema'] == 12
          and type(value['toSchema']) is int and value['toSchema'] == 13, 'staging_upgrade_receipt_invalid')
    _need(value['backupName'] == name and all(value[k] == v for k, v in snapshots._binding(marker).items()),
          'staging_upgrade_owner_mismatch')
    _need(type(value['operationId']) is str and re.fullmatch(r'[a-f0-9]{32}', value['operationId']),
          'staging_upgrade_receipt_invalid')
    for key in ('snapshotSHA256', 'sourceLogicalSHA256', 'readyMarkerSHA256'):
        _need(type(value[key]) is str and re.fullmatch(r'[a-f0-9]{64}', value[key]), 'staging_upgrade_receipt_invalid')
    identity = value['sourceFileIdentity']
    _need(type(identity) is dict and set(identity) == {'device', 'inode'}
          and all(type(v) is int and v >= 0 for v in identity.values())
          and type(value['snapshotBytes']) is int and value['snapshotBytes'] > 0,
          'staging_upgrade_receipt_invalid')
    _need(value['readyMarkerSHA256'] == hashlib.sha256(ready_bytes).hexdigest()
          and path.read_bytes() == snapshots._bytes(value), 'staging_upgrade_receipt_invalid')
    return value


def _snapshot_proven(path, proof):
    snapshots._regular(path)
    _need(not any(os.path.lexists(Path(str(path) + suffix)) for suffix in ('-wal', '-shm', '-journal')),
          'staging_upgrade_snapshot_sidecar_rejected')
    _need(snapshots._digest(path) == (proof['snapshotSHA256'], proof['snapshotBytes']),
          'staging_upgrade_snapshot_hash_mismatch')
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, isolation_level=None)) as db:
        _need(_validate(db) == 12 and _logical(db) == proof['sourceLogicalSHA256'],
              'staging_upgrade_snapshot_state_mismatch')


def _migrate_team_mail(manifest_or_path, name, *, timeout_seconds=60):
    """Upgrade exactly12->13, or reconcile this exact completed operation."""
    _need(SCHEMA_VERSION >= 13, 'staging_upgrade_version_not_supported')
    name = snapshots._name(name)
    snapshots._timeout(timeout_seconds)
    manifest = staging.read_manifest(manifest_or_path)
    try:
        with staging._lock(manifest, staging.RUNTIME_LOCK, allowed_states=STATES):
            with staging.root_lock(manifest, allowed_states=STATES):
                marker = staging.ownership_metadata(manifest, allowed_states=STATES)
                source = staging.owned_database(manifest, allowed_states=STATES)
                staging._require_ads_policy(manifest)
                marker_path = manifest.data_directory / staging.MARKER
                _need(marker_path.read_bytes() == snapshots._bytes(marker), 'staging_upgrade_marker_changed')
                ready = dict(marker, state='Ready')
                ready_bytes = snapshots._bytes(ready)
                identity = _file_identity(source)
                snapshot, receipt = _paths(manifest, name)
                proof = _read_proof(receipt, marker, name, ready_bytes) if os.path.lexists(receipt) else None
                if marker['state'] == PENDING:
                    _need(proof is not None, 'staging_upgrade_pending_receipt_required')
                if proof:
                    _snapshot_proven(snapshot, proof)
                    _need(proof['sourceFileIdentity'] == identity, 'staging_upgrade_database_replaced')
                else:
                    snapshots._fresh(snapshot)
                    snapshots._fresh(receipt)
                # mode=rw cannot create a missing authority. The retained writer
                # connection prevents another database writer during validation,
                # backup, the marker transition and the additive SQLite change.
                with closing(sqlite3.connect(source.as_uri() + '?mode=rw', uri=True,
                                             timeout=timeout_seconds, isolation_level=None)) as db:
                    db.execute('PRAGMA foreign_keys=ON')
                    db.execute('PRAGMA synchronous=FULL')
                    db.execute('BEGIN IMMEDIATE')
                    try:
                        version = _validate(db)
                        _need(_file_identity(source) == identity, 'staging_upgrade_database_replaced')
                        if proof and proof['state'] == 'Complete' and marker['state'] == 'Ready':
                            _need(version >= 13, 'staging_upgrade_completed_schema_changed')
                            db.rollback()
                            return _result(name, proof, True)
                        if proof:
                            _need(version in (12, 13) and _logical(db) == proof['sourceLogicalSHA256'],
                                  'staging_upgrade_source_state_changed')
                            if version == 13:
                                _need(marker['state'] == PENDING, 'staging_upgrade_pending_marker_required')
                                _need(not db.execute('SELECT 1 FROM team_mail LIMIT 1').fetchone(),
                                      'staging_upgrade_source_state_changed')
                        else:
                            _need(version == 12 and marker['state'] == 'Ready', 'staging_upgrade_schema12_required')
                            logical = _logical(db)
                            copied = backup_database(source, snapshot, timeout_seconds=timeout_seconds)
                            _need(copied['schemaVersion'] == 12 and copied['requiresMigration'] is True,
                                  'staging_upgrade_schema12_backup_required')
                            proof = dict(version=1, kind='HeartOfTheRainTeamMailUpgrade111', state='ReadyBackup',
                                         operationId=uuid.uuid4().hex, backupName=name, fromSchema=12, toSchema=13,
                                         snapshotSHA256=copied['sha256'], snapshotBytes=copied['bytes'],
                                         sourceLogicalSHA256=logical, sourceFileIdentity=identity,
                                         readyMarkerSHA256=hashlib.sha256(ready_bytes).hexdigest(), **snapshots._binding(marker))
                            _snapshot_proven(snapshot, proof)
                            snapshots._exclusive(receipt, snapshots._bytes(proof))
                            _checkpoint('AfterBackupReady')
                        if marker['state'] == 'Ready':
                            pending = dict(marker, state=PENDING)
                            snapshots._ready_receipt(marker_path, marker, pending)
                            marker = pending
                        _checkpoint('AfterPendingMarker')
                        if version == 12:
                            for statement in TEAM_MAIL_V13_DDL.split(';'):
                                if statement.strip():
                                    db.execute(statement)
                            db.execute('UPDATE schema_info SET version=13')
                        _need(_validate(db) == 13 and _logical(db) == proof['sourceLogicalSHA256'],
                              'staging_upgrade_data_preservation_failed')
                        _need(_file_identity(source) == identity and marker_path.read_bytes() == snapshots._bytes(marker),
                              'staging_upgrade_owner_or_file_changed')
                        _checkpoint('BeforeCommit')
                        db.commit()
                    except BaseException:
                        db.rollback()
                        raise
                _checkpoint('AfterCommit')
                if proof['state'] != 'Complete':
                    completed = dict(proof, state='Complete')
                    snapshots._ready_receipt(receipt, proof, completed)
                    proof = completed
                _checkpoint('AfterCompleteReceipt')
                _need(_file_identity(source) == identity, 'staging_upgrade_database_replaced')
                snapshots._ready_receipt(marker_path, marker, ready)
                _checkpoint('AfterReadyMarker')
                return _result(name, proof, False)
    except OperationError:
        raise UpgradeError('staging_upgrade_database_validation_failed') from None
    except sqlite3.Error:
        raise UpgradeError('staging_upgrade_database_failed') from None
    except OSError:
        raise UpgradeError('staging_upgrade_interrupted') from None


def migrate_team_mail(manifest_or_path, name, *, timeout_seconds=60):
    name = snapshots._name(name)
    _need(len(name) <= 40, 'staging_upgrade_name_too_long')
    return _migrate_team_mail(manifest_or_path, name, timeout_seconds=timeout_seconds)


def _result(name, proof, repeated):
    return {'status': 'completed', 'operation': 'staging_team_mail_upgrade111',
            'fromSchema': 12, 'toSchema': 13, 'backupName': name,
            'snapshotSHA256': proof['snapshotSHA256'], 'alreadyCompleted': repeated,
            'ownershipNonceChanged': False, 'economyChanged': False,
            'processStarted': False, 'productionEnabled': False}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UpgradeError('staging_upgrade_arguments_invalid')


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--name', required=True)
    parser.add_argument('--timeout-seconds', type=int, default=60)
    try:
        args = parser.parse_args(argv)
        result = migrate_team_mail(args.manifest, args.name, timeout_seconds=args.timeout_seconds)
        code = 0
    except (UpgradeError, staging.StagingError, snapshots.StagingOpsError) as error:
        result, code = {'status': 'blocked', 'code': error.code, 'productionEnabled': False}, 1
    except KeyboardInterrupt:
        result, code = {'status': 'blocked', 'code': 'staging_upgrade_interrupted', 'productionEnabled': False}, 130
    except Exception:
        result, code = {'status': 'blocked', 'code': 'staging_upgrade_failed', 'productionEnabled': False}, 1
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
