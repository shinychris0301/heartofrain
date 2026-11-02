"""Owned production snapshots and bounded durable reconciliation.

Never adopts staging data, restores in place, activates a restored root, emits
credentials, trusts a callback to credit currency, or acknowledges delivery.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import threading
import time
import uuid

from .operations import OperationError, backup_database, restore_database
from .storage import SCHEMA_VERSION

QUARANTINE_MARKER = '.hotr-production122-restore-quarantine.json'
BACKUP_KIND = 'HeartOfTheRainProductionBackup122'
QUARANTINE_KIND = 'HeartOfTheRainProductionRestoreQuarantine122'
MAX_RECEIPT = 8192
SDK_MODE = 'sdk_client_reported'
SDK_RECONCILIATION_UNAVAILABLE = 'production_provider_reconciliation_unavailable_in_sdk_mode'


class ProductionOpsError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise ProductionOpsError(code)


def _runtime():
    from . import production_runtime122
    return production_runtime122


def _snapshot_schema(manifest):
    if manifest.raw.get('verificationMode', 'provider_api') == SDK_MODE:
        from .sdk_schema125 import SDK_SCHEMA_VERSION, validate_sdk_database
        return SDK_SCHEMA_VERSION, {'_validator': validate_sdk_database}
    return SCHEMA_VERSION, {}


def _require_provider_reconciliation(manifest):
    _require(manifest.raw.get('verificationMode', 'provider_api') == 'provider_api',
             SDK_RECONCILIATION_UNAVAILABLE)


def _name(value):
    _require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,48}', value)
             and not re.fullmatch(r'(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', value), 'production_snapshot_name_invalid')
    return value


def _timeout(value):
    _require(type(value) in (int, float) and 1 <= value <= 600, 'production_snapshot_timeout_invalid')


def _plain(path):
    for entry in reversed((path, *path.parents)):
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        _require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                 'production_snapshot_link_rejected')
        if stat.S_ISREG(info.st_mode):
            _require(info.st_nlink == 1, 'production_snapshot_link_rejected')


def _regular(path):
    _plain(path)
    _require(path.is_file() and stat.S_ISREG(path.stat().st_mode), 'production_snapshot_file_required')


def _fresh(path):
    _plain(path)
    _require(not os.path.lexists(path), 'production_snapshot_destination_exists')


def _bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('ascii')


def _exclusive(path, raw):
    _fresh(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'wb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())


def _digest(path):
    _regular(path)
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1_048_576), b''):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def _json(path):
    _regular(path)
    _require(2 <= path.stat().st_size <= MAX_RECEIPT, 'production_snapshot_receipt_invalid')

    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value, 'production_snapshot_receipt_invalid')
            value[key] = item
        return value

    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, TypeError, RecursionError):
        raise ProductionOpsError('production_snapshot_receipt_invalid') from None
    _require(type(value) is dict and raw == _bytes(value), 'production_snapshot_receipt_invalid')
    return value, raw


def _replace_owned(path, before, after):
    _regular(path)
    _require(path.read_bytes() == _bytes(before), 'production_snapshot_receipt_changed')
    temporary = path.parent / ('.production-snapshot122-' + uuid.uuid4().hex + '.tmp')
    _exclusive(temporary, _bytes(after))
    _require(path.read_bytes() == _bytes(before), 'production_snapshot_receipt_changed')
    os.replace(temporary, path)


def _binding(marker):
    return {key: marker[key] for key in ('deploymentId', 'publicOrigin', 'identityScope', 'nonce', 'manifestSHA256')}


def _paths(manifest, name):
    folder = manifest.data_directory / 'backups'
    _plain(folder)
    _require(folder.is_dir(), 'production_snapshot_directory_missing')
    return folder / (name + '.sqlite3'), folder / (name + '.receipt.json')


def _receipt(path, marker, name, schema_version=SCHEMA_VERSION):
    proof, raw = _json(path)
    expected = {'version', 'kind', 'state', 'deploymentId', 'publicOrigin', 'identityScope', 'nonce',
                'manifestSHA256', 'operationId', 'snapshotName', 'schemaVersion', 'sha256', 'bytes',
                'startedAtUtc', 'completedAtUtc'}
    _require(set(proof) == expected and type(proof['version']) is int and proof['version'] == 1
             and proof['kind'] == BACKUP_KIND and proof['state'] == 'Ready', 'production_snapshot_not_ready')
    _require(all(proof[key] == value for key, value in _binding(marker).items()), 'production_snapshot_owner_mismatch')
    _require(proof['snapshotName'] == name and type(proof['operationId']) is str
             and re.fullmatch(r'[a-f0-9]{32}', proof['operationId'])
             and type(proof['sha256']) is str and re.fullmatch(r'[a-f0-9]{64}', proof['sha256'])
             and type(proof['bytes']) is int and proof['bytes'] > 0
             and type(proof['schemaVersion']) is int and proof['schemaVersion'] == schema_version,
             'production_snapshot_receipt_invalid')
    try:
        started, completed = (datetime.fromisoformat(proof[key]) for key in ('startedAtUtc', 'completedAtUtc'))
        _require(started.utcoffset() is not None and completed.utcoffset() is not None and started <= completed,
                 'production_snapshot_receipt_invalid')
    except (ValueError, TypeError):
        raise ProductionOpsError('production_snapshot_receipt_invalid') from None
    return proof, raw


def _validated_copy(result, target, schema_version=SCHEMA_VERSION):
    digest, size = _digest(target)
    _require(result.get('schemaVersion') == schema_version and result.get('requiresMigration') is False
             and result.get('sha256') == digest and result.get('bytes') == size and size > 0,
             'production_snapshot_copy_unconfirmed')
    return digest, size


def backup_production(manifest_or_path, name, *, timeout_seconds=60):
    name = _name(name)
    _timeout(timeout_seconds)
    runtime = _runtime()
    manifest = runtime.read_manifest(manifest_or_path)
    schema_version, validation = _snapshot_schema(manifest)
    runtime.owned_database(manifest)
    with runtime.root_lock(manifest):
        marker = runtime.ownership_metadata(manifest)
        source = runtime.owned_database(manifest)
        target, receipt = _paths(manifest, name)
        _fresh(target)
        _fresh(receipt)
        pending = dict(version=1, kind=BACKUP_KIND, state='Pending', operationId=uuid.uuid4().hex,
                       snapshotName=name, schemaVersion=schema_version, sha256='', bytes=0,
                       startedAtUtc=datetime.now(timezone.utc).isoformat(), completedAtUtc=None, **_binding(marker))
        _exclusive(receipt, _bytes(pending))
        result = backup_database(source, target, timeout_seconds=timeout_seconds, **validation)
        digest, size = _validated_copy(result, target, schema_version)
        _require(runtime.ownership_metadata(manifest) == marker, 'production_snapshot_owner_changed')
        _replace_owned(receipt, pending, dict(pending, state='Ready', sha256=digest, bytes=size,
                                             completedAtUtc=datetime.now(timezone.utc).isoformat()))
        return {'status': 'completed', 'operation': 'production_backup', 'snapshotName': name,
                'schemaVersion': schema_version, 'sha256': digest, 'bytes': size,
                'activationPerformed': False, 'databaseReplaced': False, 'offHostCopyVerified': False}


def restore_quarantine(manifest_or_path, name, tag, *, timeout_seconds=60):
    name, tag = _name(name), _name(tag)
    _timeout(timeout_seconds)
    runtime = _runtime()
    manifest = runtime.read_manifest(manifest_or_path)
    schema_version, validation = _snapshot_schema(manifest)
    runtime.owned_database(manifest)
    with runtime.root_lock(manifest):
        marker = runtime.ownership_metadata(manifest)
        runtime.owned_database(manifest)
        snapshot, receipt_path = _paths(manifest, name)
        proof, raw_proof = _receipt(receipt_path, marker, name, schema_version)
        _regular(snapshot)
        _require(not any(os.path.lexists(str(snapshot) + suffix) for suffix in ('-wal', '-shm', '-journal')),
                 'production_snapshot_sidecar_rejected')
        _require(_digest(snapshot) == (proof['sha256'], proof['bytes']), 'production_snapshot_hash_mismatch')
        parent = manifest.data_directory / 'restores'
        _plain(parent)
        _require(parent.is_dir(), 'production_restore_directory_missing')
        target_root = parent / tag
        _fresh(target_root)
        target_root.mkdir(mode=0o700)
        pending = dict(version=1, kind=QUARANTINE_KIND, state='RestoreQuarantinedPending',
                       sourceSnapshot=name, sourceSHA256=proof['sha256'], sourceBytes=proof['bytes'],
                       restoredSHA256='', restoredBytes=0, schemaVersion=schema_version,
                       activationAllowed=False, **_binding(marker))
        quarantine = target_root / QUARANTINE_MARKER
        _exclusive(quarantine, _bytes(pending))
        target = target_root / 'authority.sqlite3'
        result = restore_database(snapshot, target, timeout_seconds=timeout_seconds, **validation)
        digest, size = _validated_copy(result, target, schema_version)
        _require(_digest(snapshot) == (proof['sha256'], proof['bytes']) and receipt_path.read_bytes() == raw_proof,
                 'production_snapshot_changed_during_restore')
        _require(runtime.ownership_metadata(manifest) == marker, 'production_snapshot_owner_changed')
        _replace_owned(quarantine, pending, dict(pending, state='ValidatedQuarantine', restoredSHA256=digest, restoredBytes=size))
        return {'status': 'completed', 'operation': 'production_restore_quarantine', 'snapshotName': name,
                'restoreTag': tag, 'schemaVersion': schema_version, 'sha256': digest, 'bytes': size,
                'sourceSnapshotSHA256': proof['sha256'], 'activationPerformed': False,
                'activationAllowed': False, 'databaseReplaced': False}


def reconcile_bounded(app, manifest_or_path, *, worker_id='production-reconcile122', max_jobs=50,
                      seed_limit=50, poll_seconds=300):
    """Run already-known invoice work under the runtime's active operations permit."""
    _require(type(worker_id) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', worker_id)
             and type(max_jobs) is int and 1 <= max_jobs <= 100
             and type(seed_limit) is int and 1 <= seed_limit <= 100
             and type(poll_seconds) is int and 30 <= poll_seconds <= 86400,
             'production_reconciliation_limits_invalid')
    runtime = _runtime()
    manifest = runtime.read_manifest(manifest_or_path)
    permit = runtime.require_owned_application(app, manifest, purpose='operations')
    _require_provider_reconciliation(manifest)
    _require(permit.enter(), 'production_operations_runtime_closed')
    try:
        commerce = app.state.commerce
        _require(commerce.config.enabled and commerce.config.sandbox is False and commerce.provider.configured,
                 'production_reconciliation_not_configured')
        worker = app.state.reconciliation_worker
        seeded = worker.seed_due(seed_limit, poll_seconds)
        results = worker.run_bounded(worker_id, max_jobs)
        runtime.require_owned_application(app, manifest, purpose='operations')
        states = {}
        for result in results:
            states[result['state']] = states.get(result['state'], 0) + 1
        queue = queue_summary(manifest)
        return {'status': 'operator_attention_required' if queue['states']['Dead'] else 'completed',
                'operation': 'production_reconcile_bounded', 'seeded': seeded,
                'worked': sum(bool(result['worked']) for result in results), 'states': states, 'maxJobs': max_jobs,
                'queue': queue, 'providerAcceptanceVerified': False, 'sdkAcknowledgementWritten': False}
    finally:
        permit.leave()


def reconcile_production(manifest_or_path, **limits):
    runtime = _runtime()
    manifest = runtime.read_manifest(manifest_or_path)
    _require_provider_reconciliation(manifest)
    with runtime.application_context(manifest, purpose='operations') as app:
        return reconcile_bounded(app, manifest, **limits)


def queue_summary(manifest_or_path):
    """Read durable queue counts without provider requests, user identifiers or clock writes."""
    runtime = _runtime()
    manifest = runtime.read_manifest(manifest_or_path)
    path = runtime.owned_database(manifest)
    try:
        connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=0.5, isolation_level=None)
        try:
            deadline = time.monotonic() + 1
            connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            connection.execute('PRAGMA query_only=ON')
            connection.execute('BEGIN')
            states = dict.fromkeys(('Pending', 'Running', 'Done', 'Dead'), 0)
            for state, count in connection.execute('SELECT state,COUNT(*) FROM commerce_reconcile_jobs GROUP BY state'):
                _require(state in states, 'production_queue_state_invalid')
                states[state] = count
            high_water = connection.execute('SELECT high_water FROM clock_state WHERE id=1').fetchone()[0]
            # An idle/stopped worker must not make overdue work look current.
            # Observe the wall clock without advancing the durable authority clock.
            now = max(high_water, int(time.time()))
            due = connection.execute("SELECT COUNT(*) FROM commerce_reconcile_jobs WHERE state='Pending' AND next_at<=?", (now,)).fetchone()[0]
            expired = connection.execute("SELECT COUNT(*) FROM commerce_reconcile_jobs WHERE state='Running' AND lease_until<=?", (now,)).fetchone()[0]
            return {'states': states, 'duePending': due, 'expiredLeases': expired, 'observedUtc': now,
                    'databaseChanged': False, 'providerNetworkContacted': False}
        finally:
            connection.close()
    except (sqlite3.Error, OSError, TypeError):
        raise ProductionOpsError('production_queue_unavailable') from None


def supervise_reconciliation(manifest_or_path, *, interval_seconds=30, stop_event=None, emit=None, **limits):
    """Hold one operations lease; bounded batches survive restarts through durable job leases."""
    _require(type(interval_seconds) is int and 5 <= interval_seconds <= 3600,
             'production_reconciliation_interval_invalid')
    stop = threading.Event() if stop_event is None else stop_event
    emit = (lambda result: print(json.dumps(result, separators=(',', ':')), flush=True)) if emit is None else emit
    runtime = _runtime()
    manifest = runtime.read_manifest(manifest_or_path)
    _require_provider_reconciliation(manifest)
    with runtime.application_context(manifest, purpose='operations') as app:
        while not stop.is_set():
            emit(reconcile_bounded(app, manifest, **limits))
            if stop.wait(interval_seconds):
                break
    return {'status': 'stopped', 'operation': 'production_reconciliation_supervisor', 'sdkAcknowledgementWritten': False}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ProductionOpsError('production_operator_arguments_invalid')


def main(argv=None):
    parser = _Parser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    for action in ('backup', 'restore-quarantine', 'reconcile', 'queue-summary', 'supervise-reconciliation'):
        command = commands.add_parser(action)
        command.add_argument('--manifest', required=True, type=Path)
        if action in ('backup', 'restore-quarantine'):
            command.add_argument('--name', required=True)
            command.add_argument('--timeout-seconds', type=int, default=60)
        if action == 'restore-quarantine':
            command.add_argument('--tag', required=True)
        if action in ('reconcile', 'supervise-reconciliation'):
            command.add_argument('--worker-id', default='production-reconcile122')
            command.add_argument('--max-jobs', type=int, default=50)
            command.add_argument('--seed-limit', type=int, default=50)
            command.add_argument('--poll-seconds', type=int, default=300)
        if action == 'supervise-reconciliation':
            command.add_argument('--interval-seconds', type=int, default=30)
    try:
        args = vars(parser.parse_args(argv))
        action = args.pop('action')
        manifest = args.pop('manifest')
        function = {'backup': backup_production, 'restore-quarantine': restore_quarantine, 'reconcile': reconcile_production,
                    'queue-summary': queue_summary, 'supervise-reconciliation': supervise_reconciliation}[action]
        result = function(manifest, **args)
        print(json.dumps(result, separators=(',', ':')))
        return 0
    except KeyboardInterrupt:
        print(json.dumps({'status': 'production_operations_stopped', 'activationPerformed': False}))
        return 0
    except ProductionOpsError as error:
        if error.code == SDK_RECONCILIATION_UNAVAILABLE:
            print(json.dumps({'status': 'not_applicable_sdk_client_reported_mode', 'activationPerformed': False,
                              'providerNetworkContacted': False, 'providerAcceptanceVerified': False,
                              'sdkAcknowledgementWritten': False}))
        else:
            print(json.dumps({'status': 'blocked_production_operation122', 'activationPerformed': False}))
        return 1
    except (OperationError, OSError, ValueError, RuntimeError, _runtime().ProductionError):
        # No provider exception, SQL row, secret reference or private path is exported.
        print(json.dumps({'status': 'blocked_production_operation122', 'activationPerformed': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
