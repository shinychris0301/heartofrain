"""Prepare a stopped owned schema15 snapshot as permanently quarantined SDK125.

This command never changes/adopts the original authority or its owner marker and
never creates a production Ready marker for the candidate. Same-wallet live
cutover is a separate unresolved operator gate, not performed by this command.
"""
import argparse
from contextlib import closing, ExitStack
import hashlib
import json
import re
import sqlite3

from . import production_runtime122 as runtime
from .operations import backup_database, restore_database, _validate, OperationError
from .production_ops122 import _exclusive, _bytes, _fresh, _digest
from .sdk_schema125 import apply_sdk_upgrade, validate_sdk_database
from .staging_empty_versioned_upgrade117 import _logical15

MARKER = '.hotr-sdk125-upgrade-quarantine.json'

def _require(value, code):
    if not value:
        raise runtime.ProductionError(code)

def _checkpoint(stage):
    """Private transaction/interruption test seam; never an operator option."""

def _logical(path, validator):
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        validator(db)
        return _logical15(db)

def prepare_upgrade(source_manifest, sdk_manifest, *, tag):
    source, target = runtime.read_manifest(source_manifest), runtime.read_manifest(sdk_manifest)
    _require(source.verification_mode == 'provider_api'
             and target.verification_mode == 'sdk_client_reported', 'sdk125_explicit_mode_transition_required')
    _require(type(tag) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,48}', tag),
             'sdk125_safe_preparation_tag_required')
    _require((source.data_directory, source.public_origin, source.identity_scope,
              source.deployment_id, source.port, source.config_directory) ==
             (target.data_directory, target.public_origin, target.identity_scope,
              target.deployment_id, target.port, target.config_directory),
             'sdk125_same_wallet_runtime_identity_required')
    target_catalog = runtime._configuration(target)
    from .commerce_schemas import CommerceConfig
    old_bytes = source.commerce_config.read_bytes()
    _require(hashlib.sha256(old_bytes).hexdigest() == source.commerce_sha256,
             'sdk125_source_catalog_hash_mismatch')
    old_catalog = CommerceConfig.model_validate_json(old_bytes)
    _require(old_catalog.model_dump() == (target_catalog.model_dump() | {'verificationMode': 'provider_api'}),
             'sdk125_catalog_changes_beyond_mode_rejected')
    candidate = source.data_directory / 'restores' / ('sdk125-' + tag)
    backup = source.data_directory / 'backups' / ('sdk125-' + tag + '.schema15.sqlite3')
    backup_receipt = backup.with_suffix(backup.suffix + '.receipt.json')
    for path in (candidate, backup, backup_receipt):
        _fresh(path)
    # Nonblocking real OS leases prove both API and operations are stopped.
    # No new runtime may enter while the source-bound snapshot is prepared.
    with ExitStack() as stack:
        stack.enter_context(runtime._lock(source, runtime.RUNTIME_LOCK, allowed_states=('Ready',)))
        stack.enter_context(runtime._lock(source, runtime.OPERATIONS_LOCK, allowed_states=('Ready',)))
        stack.enter_context(runtime.root_lock(source, allowed_states=('Ready',)))
        owner = runtime.ownership_metadata(source)
        owner_bytes = (source.data_directory / runtime.MARKER).read_bytes()
        database = runtime.owned_database(source)
        before = _logical(database, _validate)
        backup_database(database, backup)
        backup_hash, backup_size = _digest(backup)
        binding = {'version': 1, 'kind': 'HeartOfTheRainSdk125UpgradeQuarantine',
                   'state': 'Pending', 'sourceManifestSHA256': source.manifest_sha256,
                   'targetManifestSHA256': target.manifest_sha256, 'sourceOwnerNonce': owner['nonce'],
                   'logical15SHA256': before, 'backupSHA256': backup_hash, 'backupBytes': backup_size,
                   'activationAllowed': False, 'sourceModified': False}
        _exclusive(backup_receipt, _bytes(dict(binding, kind='HeartOfTheRainSdk125PreparationBackup')))
        candidate.mkdir(mode=0o700)
        _exclusive(candidate / MARKER, _bytes(binding))
        target_db = candidate / runtime.DATABASE
        restore_database(backup, target_db)
        _checkpoint('BeforeUpgrade')
        with closing(sqlite3.connect(target_db, isolation_level=None)) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            try:
                apply_sdk_upgrade(db)
                _checkpoint('BeforeUpgradeCommit')
                db.commit()
            except BaseException:
                db.rollback()
                raise
        _checkpoint('AfterUpgradeCommit')
        after = _logical(target_db, validate_sdk_database)
        _require(before == after and _logical(database, _validate) == before,
                 'sdk125_original_logical_state_changed')
        with closing(sqlite3.connect(target_db.as_uri() + '?mode=ro', uri=True)) as db:
            _require(db.execute("SELECT COUNT(*) FROM commerce_orders WHERE verification_mode!='provider_api'").fetchone()[0] == 0,
                     'sdk125_historical_orders_reinterpreted')
        _require((source.data_directory / runtime.MARKER).read_bytes() == owner_bytes,
                 'sdk125_source_owner_changed')
        candidate_hash, candidate_size = _digest(target_db)
        receipt = dict(binding, state='ValidatedQuarantine', candidateSHA256=candidate_hash,
                       candidateBytes=candidate_size, schemaVersion=125,
                       allOriginalTablesUnchanged=True, historicalOrdersRemainProviderApi=True)
        temporary = candidate / '.validated.tmp'
        _exclusive(temporary, _bytes(receipt))
        import os
        os.replace(temporary, candidate / MARKER)
        return {'status': 'prepared_quarantined_sdk125', 'schemaVersion': 125,
                'originalAuthorityPreserved': True, 'allOriginalTablesUnchanged': True,
                'historicalOrdersRemainProviderApi': True, 'candidatePermanentlyQuarantined': True,
                'sourceStillRequiresExplicitCutover': True, 'productionActivated': False,
                'providerContacted': False, 'secretContentsRead': False,
                'backupSHA256': backup_hash, 'candidateSHA256': candidate_hash,
                'sourceManifestSHA256': source.manifest_sha256,
                'targetManifestSHA256': target.manifest_sha256}

def main(argv=None):
    class Parser(argparse.ArgumentParser):
        def error(self, message):
            raise runtime.ProductionError('sdk125_preparation_arguments_invalid')
    parser = Parser(description=__doc__)
    parser.add_argument('--source-manifest', required=True)
    parser.add_argument('--sdk-manifest', required=True)
    parser.add_argument('--tag', required=True)
    try:
        options = parser.parse_args(argv)
        print(json.dumps(prepare_upgrade(options.source_manifest, options.sdk_manifest, tag=options.tag),
                         separators=(',', ':')))
        return 0
    except (runtime.ProductionError, OperationError, sqlite3.Error, OSError, ValueError, RuntimeError):
        print(json.dumps({'status': 'blocked_sdk125_offline_preparation', 'productionActivated': False}))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())

