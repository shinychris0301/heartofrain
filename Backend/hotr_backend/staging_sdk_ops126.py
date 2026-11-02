"""SDK125 snapshots of the existing staging wallet; restores stay quarantined.

The schema125 checker is selected only after the private SDK staging ownership
policy passes. Legacy snapshot entrypoints and schema validators are unchanged.
Backup receipts retain the installed monitor's public staging105 wire format.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid

from . import staging105 as staging
from . import staging_ops105 as snapshots
from .operations import OperationError, backup_database, restore_database
from .sdk_schema125 import SDK_SCHEMA_VERSION, validate_sdk_database

QUARANTINE_MARKER = '.hotr-staging-sdk126-restore-quarantine.json'
QUARANTINE_KIND = 'HeartOfTheRainStagingSdkRestoreQuarantine126'
BACKUP_KIND = 'HeartOfTheRainStagingBackup105'


class StagingSdkOpsError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise StagingSdkOpsError(code)


def _ready(manifest):
    from . import staging_sdk126
    return staging_sdk126.require_sdk_ready(manifest)


def _same_authority(manifest, owner, policy):
    current, current_owner, current_policy = _ready(manifest)
    _need(current == manifest and current_owner == owner and current_policy == policy,
          'staging_sdk_snapshot_authority_changed')


def _copy_proof(result, destination):
    digest, size = snapshots._digest(destination)
    _need(result.get('schemaVersion') == SDK_SCHEMA_VERSION
          and result.get('requiresMigration') is False
          and result.get('sha256') == digest and result.get('bytes') == size and size > 0,
          'staging_sdk_snapshot_copy_unconfirmed')
    return digest, size


def _receipt(path, owner, name):
    snapshots._regular(path)
    _need(2 <= path.stat().st_size <= 4096, 'staging_sdk_snapshot_receipt_invalid')
    raw = path.read_bytes()
    try:
        proof = staging._json(raw)
    except staging.StagingError:
        raise StagingSdkOpsError('staging_sdk_snapshot_receipt_invalid') from None
    expected = {'version', 'kind', 'state', 'deploymentId', 'publicOrigin', 'identityScope', 'nonce',
                'operationId', 'snapshotName', 'sha256', 'bytes', 'schemaVersion'}
    _need(set(proof) == expected and type(proof['version']) is int and proof['version'] == 1
          and proof['kind'] == BACKUP_KIND and proof['state'] == 'Ready',
          'staging_sdk_snapshot_not_ready')
    _need(all(proof[key] == value for key, value in snapshots._binding(owner).items()),
          'staging_sdk_snapshot_owner_mismatch')
    _need(proof['snapshotName'] == name and type(proof['operationId']) is str
          and re.fullmatch(r'[a-f0-9]{32}', proof['operationId'])
          and type(proof['sha256']) is str and re.fullmatch(r'[a-f0-9]{64}', proof['sha256'])
          and type(proof['bytes']) is int and proof['bytes'] > 0
          and type(proof['schemaVersion']) is int and proof['schemaVersion'] == SDK_SCHEMA_VERSION
          and raw == snapshots._bytes(proof), 'staging_sdk_snapshot_receipt_invalid')
    return proof, raw


def _standalone_snapshot(path, proof):
    snapshots._regular(path)
    _need(not any(os.path.lexists(str(path) + suffix) for suffix in ('-wal', '-shm', '-journal')),
          'staging_sdk_snapshot_sidecar_rejected')
    _need(snapshots._digest(path) == (proof['sha256'], proof['bytes']),
          'staging_sdk_snapshot_hash_mismatch')
    # Reject a hash-consistent but structurally wrong snapshot before creating a
    # quarantine directory. Never open Database(), which could migrate a file.
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, isolation_level=None)) as db:
        db.execute('PRAGMA query_only=ON')
        validate_sdk_database(db)


def backup_staging_sdk(manifest_or_path, name, *, timeout_seconds=60):
    name = snapshots._name(name)
    snapshots._timeout(timeout_seconds)
    manifest, _, _ = _ready(manifest_or_path)  # Reject unowned/unprepared roots before lock/artifact creation.
    with staging.root_lock(manifest, allowed_states=('Ready',)):
        manifest, owner, policy = _ready(manifest)
        source = staging.owned_database(manifest)
        snapshots._regular(source)
        target, receipt = snapshots._paths(manifest, name)
        snapshots._fresh(target)
        snapshots._fresh(receipt)
        pending = dict(version=1, kind=BACKUP_KIND, state='Pending', operationId=uuid.uuid4().hex,
                       snapshotName=name, sha256='', bytes=0, schemaVersion=SDK_SCHEMA_VERSION,
                       **snapshots._binding(owner))
        snapshots._exclusive(receipt, snapshots._bytes(pending))
        result = backup_database(source, target, timeout_seconds=timeout_seconds,
                                 _validator=validate_sdk_database)
        digest, size = _copy_proof(result, target)
        _same_authority(manifest, owner, policy)
        snapshots._ready_receipt(receipt, pending, dict(pending, state='Ready', sha256=digest, bytes=size))
        return {'status': 'completed', 'operation': 'staging_sdk_backup', 'snapshotName': name,
                'schemaVersion': SDK_SCHEMA_VERSION, 'sha256': digest, 'bytes': size,
                'productionEnabled': False, 'activationPerformed': False, 'databaseReplaced': False,
                'offHostCopyVerified': False, 'sdkAcknowledgementWritten': False}


def restore_quarantine(manifest_or_path, name, tag, *, timeout_seconds=60):
    name, tag = snapshots._name(name), snapshots._name(tag)
    snapshots._timeout(timeout_seconds)
    manifest, _, _ = _ready(manifest_or_path)
    with staging.root_lock(manifest, allowed_states=('Ready',)):
        manifest, owner, policy = _ready(manifest)
        snapshot, receipt = snapshots._paths(manifest, name)
        proof, raw_proof = _receipt(receipt, owner, name)
        _standalone_snapshot(snapshot, proof)
        parent = manifest.data_directory / 'restores'
        snapshots._plain(parent)
        _need(parent.is_dir(), 'staging_sdk_restore_directory_missing')
        target_root = parent / tag
        snapshots._fresh(target_root)
        target_root.mkdir(mode=0o700)
        pending = dict(version=1, kind=QUARANTINE_KIND, state='RestoreQuarantinedPending',
                       schemaVersion=SDK_SCHEMA_VERSION, sourceSnapshot=name,
                       sourceSHA256=proof['sha256'], sourceBytes=proof['bytes'],
                       restoredSHA256='', restoredBytes=0, activationAllowed=False,
                       **snapshots._binding(owner))
        quarantine = target_root / QUARANTINE_MARKER
        snapshots._exclusive(quarantine, snapshots._bytes(pending))
        target = target_root / staging.DATABASE
        result = restore_database(snapshot, target, timeout_seconds=timeout_seconds,
                                  _validator=validate_sdk_database)
        digest, size = _copy_proof(result, target)
        _need(snapshots._digest(snapshot) == (proof['sha256'], proof['bytes'])
              and receipt.read_bytes() == raw_proof, 'staging_sdk_snapshot_changed_during_restore')
        _same_authority(manifest, owner, policy)
        snapshots._ready_receipt(quarantine, pending,
                                 dict(pending, state='ValidatedQuarantine', restoredSHA256=digest, restoredBytes=size))
        return {'status': 'completed', 'operation': 'staging_sdk_restore_quarantine',
                'snapshotName': name, 'restoreTag': tag, 'schemaVersion': SDK_SCHEMA_VERSION,
                'sha256': digest, 'bytes': size, 'sourceSnapshotSHA256': proof['sha256'],
                'productionEnabled': False, 'activationPerformed': False, 'activationAllowed': False,
                'databaseReplaced': False, 'sdkAcknowledgementWritten': False}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise StagingSdkOpsError('staging_sdk_operator_arguments_invalid')


def main(argv=None):
    parser = _Parser(description='Owned SDK staging backups and permanently quarantined restore drills.')
    commands = parser.add_subparsers(dest='operation', required=True)
    for name in ('backup', 'restore-quarantine'):
        command = commands.add_parser(name)
        command.add_argument('--manifest', type=Path, required=True)
        command.add_argument('--timeout-seconds', type=int, default=60)
        if name == 'backup':
            command.add_argument('--name', required=True)
        else:
            command.add_argument('--backup', required=True)
            command.add_argument('--tag', required=True)
    try:
        options = parser.parse_args(argv)
        result = (backup_staging_sdk(options.manifest, options.name, timeout_seconds=options.timeout_seconds)
                  if options.operation == 'backup' else
                  restore_quarantine(options.manifest, options.backup, options.tag, timeout_seconds=options.timeout_seconds))
        code = 0
    except (StagingSdkOpsError, staging.StagingError, snapshots.StagingOpsError) as error:
        result, code = {'status': 'blocked', 'code': error.code, 'activationPerformed': False}, 1
    except KeyboardInterrupt:
        result, code = {'status': 'blocked', 'code': 'staging_sdk_operation_interrupted', 'activationPerformed': False}, 130
    except Exception:
        # Includes foreign errors, SDK-policy exceptions and SQLite details.
        result, code = {'status': 'blocked', 'code': 'staging_sdk_operation_failed', 'activationPerformed': False}, 1
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
