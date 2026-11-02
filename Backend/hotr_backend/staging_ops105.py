"""Owned staging snapshots; no database replacement, activation or credentials.

SQLite validation/copying remains in operations.py. This layer adds path fencing
and an immutable-source ownership receipt, not a second backup implementation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

from .operations import OperationError, backup_database, restore_database
from .staging105 import (StagingError, complete_restore, initialize_owned_data,
                         manifest_for_data_directory, owned_database,
                         ownership_metadata, read_manifest, root_lock)
from .storage import SCHEMA_VERSION


class StagingOpsError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


_CORE_CODES = {'invalid_operation_timeout', 'database_integrity_failed', 'database_foreign_keys_failed',
               'unknown_database_schema', 'database_schema_mismatch', 'invalid_destination', 'invalid_source',
               'database_copy_timeout', 'standalone_snapshot_unavailable', 'copied_schema_changed',
               'destination_exists', 'database_copy_failed_artifact_preserved', 'source_or_destination_unavailable'}


def _need(condition, code):
    if not condition:
        raise StagingOpsError(code)


def _name(value):
    _need(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,48}', value), 'staging_snapshot_name_invalid')
    _need(not re.fullmatch(r'(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', value), 'staging_snapshot_name_invalid')
    return value


def _timeout(value):
    _need(type(value) in (int, float) and 1 <= value <= 600, 'staging_snapshot_timeout_invalid')


def _plain(path):
    for entry in (path, *path.parents):
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        _need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
              'staging_snapshot_link_rejected')
    if path.is_file():
        _need(path.stat().st_nlink == 1, 'staging_snapshot_hardlink_rejected')


def _regular(path):
    _plain(path)
    _need(path.is_file() and stat.S_ISREG(path.stat().st_mode), 'staging_snapshot_file_required')


def _fresh(path):
    _plain(path)
    _need(not os.path.lexists(path), 'staging_snapshot_destination_exists')


def _digest(path):
    _regular(path)
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1_048_576), b''):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def _bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('ascii')


def _exclusive(path, raw):
    _fresh(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'wb') as file:
        file.write(raw)
        file.flush()
        os.fsync(file.fileno())


def _ready_receipt(path, pending, ready):
    _regular(path)
    _need(path.read_bytes() == _bytes(pending), 'staging_snapshot_receipt_changed')
    temporary = path.parent / ('.snapshot105-' + uuid.uuid4().hex + '.tmp')
    _exclusive(temporary, _bytes(ready))
    _need(path.read_bytes() == _bytes(pending), 'staging_snapshot_receipt_changed')
    os.replace(temporary, path)


def _binding(marker):
    return {key: marker[key] for key in ('deploymentId', 'publicOrigin', 'identityScope', 'nonce')}


def _paths(manifest, name):
    folder = manifest.data_directory / 'backups'
    _plain(folder)
    _need(folder.is_dir(), 'staging_snapshot_directory_required')
    return folder / (name + '.sqlite3'), folder / (name + '.receipt.json')


def _receipt(path, marker, name):
    _regular(path)
    _need(2 <= path.stat().st_size <= 4096, 'staging_snapshot_receipt_invalid')

    def pairs(items):
        value = {}
        for key, item in items:
            _need(key not in value, 'staging_snapshot_receipt_invalid')
            value[key] = item
        return value

    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise StagingOpsError('staging_snapshot_receipt_invalid') from None
    expected = {'version', 'kind', 'state', 'deploymentId', 'publicOrigin', 'identityScope', 'nonce',
                'operationId', 'snapshotName', 'sha256', 'bytes', 'schemaVersion'}
    _need(type(value) is dict and set(value) == expected, 'staging_snapshot_receipt_invalid')
    _need(type(value['version']) is int and value['version'] == 1 and value['kind'] == 'HeartOfTheRainStagingBackup105', 'staging_snapshot_receipt_invalid')
    _need(value['state'] == 'Ready', 'staging_snapshot_not_ready')
    _need(all(value[key] == item for key, item in _binding(marker).items()), 'staging_snapshot_owner_mismatch')
    _need(value['snapshotName'] == name and type(value['operationId']) is str and re.fullmatch(r'[a-f0-9]{32}', value['operationId']), 'staging_snapshot_receipt_invalid')
    _need(type(value['sha256']) is str and re.fullmatch(r'[a-f0-9]{64}', value['sha256']) and type(value['bytes']) is int and value['bytes'] > 0,
          'staging_snapshot_receipt_invalid')
    _need(type(value['schemaVersion']) is int and value['schemaVersion'] == SCHEMA_VERSION, 'staging_snapshot_current_schema_required')
    _need(raw == _bytes(value), 'staging_snapshot_receipt_invalid')
    return value


def _validated_copy(result, destination):
    digest, size = _digest(destination)
    _need(result.get('schemaVersion') == SCHEMA_VERSION and result.get('requiresMigration') is False,
          'staging_snapshot_current_schema_required')
    _need(result.get('sha256') == digest and result.get('bytes') == size and size > 0,
          'staging_snapshot_copy_unconfirmed')
    return digest, size


def backup_staging(manifest_or_path, name, *, timeout_seconds=60):
    name = _name(name)
    _timeout(timeout_seconds)
    manifest = read_manifest(manifest_or_path)
    owned_database(manifest)  # No new lock file or directory on an unowned root.
    with root_lock(manifest):  # Administrative lock, never the serving RunLock.
        marker = ownership_metadata(manifest)
        source = owned_database(manifest)
        _regular(source)
        target, receipt = _paths(manifest, name)
        _fresh(target)
        _fresh(receipt)
        pending = dict(version=1, kind='HeartOfTheRainStagingBackup105', state='Pending',
                       operationId=uuid.uuid4().hex, snapshotName=name, sha256='', bytes=0,
                       schemaVersion=SCHEMA_VERSION, **_binding(marker))
        _exclusive(receipt, _bytes(pending))
        result = backup_database(source, target, timeout_seconds=timeout_seconds)
        digest, size = _validated_copy(result, target)
        _ready_receipt(receipt, pending, dict(pending, state='Ready', sha256=digest, bytes=size))
        return {'status': 'completed', 'operation': 'staging_backup', 'snapshotName': name,
                'schemaVersion': SCHEMA_VERSION, 'sha256': digest, 'bytes': size,
                'activationPerformed': False, 'descriptorWritten': False}


def restore_staging(manifest_or_path, backup_name, restore_tag, *, timeout_seconds=60):
    name, tag = _name(backup_name), _name(restore_tag)
    _timeout(timeout_seconds)
    manifest = read_manifest(manifest_or_path)
    owned_database(manifest)
    with root_lock(manifest):
        marker = ownership_metadata(manifest)
        owned_database(manifest)
        snapshot, receipt_path = _paths(manifest, name)
        proof = _receipt(receipt_path, marker, name)
        _regular(snapshot)
        _need(not any(os.path.lexists(Path(str(snapshot) + suffix)) for suffix in ('-wal', '-shm', '-journal')),
              'staging_snapshot_sidecar_rejected')
        digest, size = _digest(snapshot)
        _need((digest, size) == (proof['sha256'], proof['bytes']), 'staging_snapshot_hash_mismatch')
        parent = manifest.data_directory / 'restores'
        _plain(parent)
        _need(parent.is_dir(), 'staging_restore_directory_required')
        target_root = parent / tag
        _fresh(target_root)
        target_manifest = manifest_for_data_directory(manifest, target_root)
        initialize_owned_data(target_manifest, restore_pending=True)
        target = target_root / 'authority.sqlite3'
        result = restore_database(snapshot, target, timeout_seconds=timeout_seconds)
        target_digest, target_size = _validated_copy(result, target)
        _need(_digest(snapshot) == (digest, size) and receipt_path.read_bytes() == _bytes(proof),
              'staging_snapshot_changed_during_restore')
        complete_restore(target_manifest)  # Independent exact-current-schema validation; atomic Ready transition.
        return {'status': 'completed', 'operation': 'staging_restore', 'snapshotName': name, 'restoreTag': tag,
                'schemaVersion': SCHEMA_VERSION, 'sha256': target_digest, 'bytes': target_size,
                'sourceSnapshotSHA256': digest, 'activationPerformed': False, 'descriptorWritten': False}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise StagingOpsError('staging_operator_arguments_invalid')


def main(argv=None):
    parser = _Parser(description='Owned staging snapshots. Never replaces or starts a database; no credentials are printed.')
    commands = parser.add_subparsers(dest='operation', required=True)
    for name in ('backup', 'restore'):
        command = commands.add_parser(name)
        command.add_argument('--manifest', required=True, type=Path)
        command.add_argument('--timeout-seconds', type=int, default=60)
        if name == 'backup':
            command.add_argument('--name', required=True)
        else:
            command.add_argument('--backup', required=True)
            command.add_argument('--tag', required=True)
    try:
        args = parser.parse_args(argv)
        result = (backup_staging(args.manifest, args.name, timeout_seconds=args.timeout_seconds)
                  if args.operation == 'backup' else restore_staging(args.manifest, args.backup, args.tag, timeout_seconds=args.timeout_seconds))
        code = 0
    except (StagingError, StagingOpsError) as error:
        result, code = {'status': 'blocked', 'code': error.code, 'activationPerformed': False}, 1
    except OperationError as error:
        safe = str(error) if str(error) in _CORE_CODES else 'staging_operation_failed'
        result, code = {'status': 'blocked', 'code': safe, 'activationPerformed': False}, 1
    except KeyboardInterrupt:
        result, code = {'status': 'blocked', 'code': 'staging_operation_interrupted', 'activationPerformed': False}, 130
    except Exception:
        result, code = {'status': 'blocked', 'code': 'staging_operation_failed', 'activationPerformed': False}, 1
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
