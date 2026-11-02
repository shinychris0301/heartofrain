"""Bounded operator work and validated new-file SQLite snapshots.

No in-place restore, automatic migration, production activation, credentials or
provider payload logging. SQLite's backup API includes committed WAL contents.
"""
import hashlib
import os
import sqlite3
import time
from contextlib import closing
from functools import lru_cache
from pathlib import Path

from .identity_schema import IDENTITY_V4_DDL
from .notification_schema import NOTIFICATIONS_V4_DDL
from .storage import COMMERCE_V2, DDL, SCHEMA_VERSION, WALLET_V3


class OperationError(Exception):
    """Public operator error code only; never embeds a path, secret or DB row."""


def require_mode(mode):
    if mode not in ('local', 'staging'):
        raise OperationError('unsupported_backend_mode')


@lru_cache(maxsize=8)
def _expected(version):
    with closing(sqlite3.connect(':memory:')) as database:
        statements = [DDL]
        if version >= 2:
            statements.append(COMMERCE_V2)
        if version >= 3:
            statements.append(WALLET_V3)
        if version >= 4:
            statements.extend((IDENTITY_V4_DDL, NOTIFICATIONS_V4_DDL))
        if version >= 5:
            from .social_schema import SOCIAL_V5_DDL
            from .messaging_schema import MESSAGING_V5_DDL
            from .records_schema import RECORDS_V5_DDL
            from .discovery_schema import DISCOVERY_V5_DDL
            from .ugc_schema import UGC_V5_DDL
            statements.extend((SOCIAL_V5_DDL, MESSAGING_V5_DDL, RECORDS_V5_DDL, DISCOVERY_V5_DDL, UGC_V5_DDL))
        if version >= 6:
            from .replay_schema import REPLAY_V6_DDL
            statements.append(REPLAY_V6_DDL)
        if version >= 7:
            from .newads_schema import NEWADS_V7_DDL
            statements.append(NEWADS_V7_DDL)
        if version >= 8:
            from .region_schema import REGIONS_V8_DDL
            from .provider_identity_schema import PROVIDER_IDENTITY_V8_DDL
            from .newads_schema import NEWADS_V8_DDL
            statements.extend((REGIONS_V8_DDL, PROVIDER_IDENTITY_V8_DDL, NEWADS_V8_DDL))
        if version >= 9:
            from .commerce_schema import COMMERCE_V9_DDL
            statements.append(COMMERCE_V9_DDL)
        if version >= 10:
            from .provider_signin_schema102 import PROVIDER_SIGNIN_V10_DDL
            statements.append(PROVIDER_SIGNIN_V10_DDL)
        if version >= 11:
            from .teams_schema109 import TEAMS_V11_DDL
            statements.append(TEAMS_V11_DDL)
        if version >= 12:
            from .team_life_schema110 import TEAM_LIFE_V12_DDL
            statements.append(TEAM_LIFE_V12_DDL)
        if version >= 13:
            from .team_mail_schema111 import TEAM_MAIL_V13_DDL
            statements.append(TEAM_MAIL_V13_DDL)
        if version >= 14:
            from .team_invite_schema112 import TEAM_INVITES_V14_DDL
            statements.append(TEAM_INVITES_V14_DDL)
        if version >= 15:
            from .friend_search_schema115 import FRIEND_SEARCH_V15_DDL
            statements.append(FRIEND_SEARCH_V15_DDL)
        database.executescript(''.join(statements))
        return _objects(database)


def _objects(database):
    return tuple(database.execute("""SELECT type,name,tbl_name,sql FROM sqlite_master
        WHERE name NOT LIKE 'sqlite_%' AND name NOT LIKE 'perf136_%' ORDER BY type,name"""))


def _validate(database):
    # quick_check does not check foreign keys, so both independent checks run.
    if database.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
        raise OperationError('database_integrity_failed')
    if database.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise OperationError('database_foreign_keys_failed')
    rows = database.execute('SELECT version FROM schema_info').fetchall()
    if len(rows) != 1 or type(rows[0][0]) is not int or not 1 <= rows[0][0] <= SCHEMA_VERSION:
        raise OperationError('unknown_database_schema')
    version = rows[0][0]
    # Include tables, explicit unique indexes, triggers and views. A claimed
    # schema_version alone cannot make a partial/altered database restorable.
    if _objects(database) != _expected(version):
        raise OperationError('database_schema_mismatch')
    return version


def _destination(path):
    supplied = Path(path).expanduser()
    parent = supplied.parent.resolve(strict=True)
    if not supplied.name or not parent.is_dir():
        raise OperationError('invalid_destination')
    # Resolve the parent, not the leaf: O_EXCL must reject even a broken link.
    return parent / supplied.name


def _fsync_parent(parent):
    if os.name != 'posix':
        return False
    descriptor = os.open(parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True


def _copy_database(source, destination, operation, timeout_seconds, *, _validator=None):
    if type(timeout_seconds) not in (int, float) or not 1 <= timeout_seconds <= 600:
        raise OperationError('invalid_operation_timeout')
    # Only an owned production caller supplies an exact private schema checker.
    # Legacy callers and every ordinary CLI retain the original validator.
    validate = _validate if _validator is None else _validator
    descriptor = None
    created = False
    try:
        origin = Path(source).expanduser().resolve(strict=True)
        if not origin.is_file():
            raise OperationError('invalid_source')
        target = _destination(destination)
        # mode=ro never creates or migrates the source; do not use immutable=1,
        # which could ignore an active WAL and lose committed receipts.
        with closing(sqlite3.connect(origin.as_uri() + '?mode=ro', uri=True, timeout=1,
                                     isolation_level=None)) as source_db:
            source_db.execute('PRAGMA query_only=ON')
            source_db.execute('BEGIN')
            version = validate(source_db)
            descriptor = os.open(target, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
            created = True
            os.chmod(target, 0o600)
            deadline = time.monotonic() + timeout_seconds

            def progress(status, remaining, total):
                if time.monotonic() >= deadline:
                    raise OperationError('database_copy_timeout')

            with closing(sqlite3.connect(target, timeout=1, isolation_level=None)) as target_db:
                target_db.execute('PRAGMA synchronous=FULL')
                source_db.backup(target_db, pages=128, progress=progress, sleep=0.05)
                # Make the result standalone, without depending on a sidecar WAL.
                if target_db.execute('PRAGMA journal_mode=DELETE').fetchone()[0] != 'delete':
                    raise OperationError('standalone_snapshot_unavailable')
                if validate(target_db) != version:
                    raise OperationError('copied_schema_changed')
            os.fsync(descriptor)
            directory_fsynced = _fsync_parent(target.parent)
        digest = hashlib.sha256()
        with target.open('rb') as snapshot:
            for chunk in iter(lambda: snapshot.read(1_048_576), b''):
                digest.update(chunk)
        return {'status': 'completed', 'operation': operation, 'schemaVersion': version,
                'requiresMigration': version < SCHEMA_VERSION, 'bytes': target.stat().st_size,
                'sha256': digest.hexdigest(), 'fileFsynced': True, 'directoryFsynced': directory_fsynced,
                'permissionScope': 'POSIX0600' if os.name == 'posix' else 'creation_mode0600_windows_acl_inherited',
                'destinationWasNew': True, 'inPlaceRestore': False}
    except OperationError:
        raise
    except FileExistsError:
        raise OperationError('destination_exists') from None
    except (OSError, sqlite3.Error, ValueError):
        raise OperationError('database_copy_failed_artifact_preserved' if created else 'source_or_destination_unavailable') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def backup_database(source, new_destination, *, timeout_seconds=60, _validator=None):
    return _copy_database(source, new_destination, 'backup', timeout_seconds, _validator=_validator)


def restore_database(snapshot, new_destination, *, timeout_seconds=60, _validator=None):
    # Validation occurs before exclusive destination creation. Neither this nor
    # the backup path opens Database(), which would perform a schema migration.
    return _copy_database(snapshot, new_destination, 'restore', timeout_seconds, _validator=_validator)


def reconcile_bounded(app, mode, *, worker_id='operator', max_jobs=50, seed_limit=50, poll_seconds=300):
    require_mode(mode)
    commerce = app.state.commerce
    if not commerce.config.enabled or not commerce.config.sandbox or not commerce.provider.configured:
        raise OperationError('sandbox_reconciliation_not_configured')
    # Validate every limit BEFORE seeding or claiming any durable work.
    import re
    if (not isinstance(worker_id, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', worker_id)
            or type(max_jobs) is not int or not 1 <= max_jobs <= 1000
            or type(seed_limit) is not int or not 1 <= seed_limit <= 100
            or type(poll_seconds) is not int or not 30 <= poll_seconds <= 86_400):
        raise OperationError('invalid_bounded_worker_limits')
    worker = app.state.reconciliation_worker
    seeded = worker.seed_due(seed_limit, poll_seconds)
    results = worker.run_bounded(worker_id, max_jobs)
    counts = {}
    for result in results:
        counts[result['state']] = counts.get(result['state'], 0) + 1
    return {'status': 'completed', 'mode': mode, 'seeded': seeded,
            'worked': sum(bool(result['worked']) for result in results), 'states': counts,
            'maxJobs': max_jobs, 'productionEnabled': False, 'sdkAcknowledgementWritten': False}
