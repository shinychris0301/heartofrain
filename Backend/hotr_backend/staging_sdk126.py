"""Explicit same-wallet staging105 schema15 -> SDK125 transition and owned launcher.

The original owner kind/nonce and final Ready state survive. Ordinary staging105
launchers still reject schema125. No production permit, provider API, credential,
worker-version attribution or local-wallet import is introduced.
"""
import argparse
from contextlib import closing, contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import threading
import time
import uuid

from . import staging105 as staging
from . import staging_ops105 as snapshots
from .commerce_schemas import CommerceConfig
from .operations import OperationError, _validate, backup_database
from .sdk_schema125 import apply_sdk_upgrade, validate_sdk_database
from .staging_empty_versioned_upgrade117 import _logical15

POLICY = '.hotr-staging126-sdk-policy.json'
CATALOG = '.hotr-staging126-sdk-commerce.json'
PENDING = 'SdkUpgradePending126'
STATES = ('Ready', PENDING)
_SECRET = object()
PERMIT_CHECK_SECONDS = 5
PERMIT_FAILURES_TO_CLOSE = 3

def _need(value, code):
    if not value:
        raise staging.StagingError(code)

def _checkpoint(stage):
    """Private failure-injection seam, never an operator command parameter."""

def _hash(raw):
    return hashlib.sha256(raw).hexdigest()

def policy_hash(policy):
    return _hash(snapshots._bytes(policy))

def _identity(path):
    snapshots._regular(path)
    info = path.stat()
    return {'device': info.st_dev, 'inode': info.st_ino}

def _load_catalog(path):
    path = staging._local_path(path, absolute_required=True)
    snapshots._regular(path)
    _need(2 <= path.stat().st_size <= 131072, 'sdk126_catalog_size_invalid')
    raw = path.read_bytes()
    try:
        config = CommerceConfig.model_validate(staging._json(raw))
    except Exception:
        raise staging.StagingError('sdk126_catalog_invalid') from None
    _need(config.verificationMode == 'sdk_client_reported' and config.sandbox is True
          and config.enabled and type(config.appId) is int, 'sdk126_enabled_sandbox_catalog_required')
    return raw, config

def _paths(m, name):
    return (m.data_directory / 'backups' / (name + '.sqlite3'),
            m.data_directory / 'backups' / (name + '.receipt.json'),
            m.data_directory / 'backups' / (name + '.sdk126.json'))

def _policy(m, owner, name, package_name, raw, catalog):
    return {'version': 1, 'kind': 'HeartOfTheRainStagingSdk126',
            'verificationMode': 'sdk_client_reported', 'sandbox': True,
            'appId': catalog.appId, 'packageName': package_name, 'upgradeName': name,
            'catalogSHA256': _hash(raw), 'catalogFile': str(m.data_directory / CATALOG),
            'dataDirectory': str(m.data_directory), **snapshots._binding(owner)}

def _read_proof(path, m, owner, name, policy):
    snapshots._regular(path)
    _need(path.stat().st_size <= 8192, 'sdk126_receipt_invalid')
    proof = staging._json(path.read_bytes())
    keys = {'version', 'kind', 'state', 'operationId', 'backupName', 'fromSchema', 'toSchema',
            'snapshotSHA256', 'snapshotBytes', 'sourceLogicalSHA256', 'sourceFileIdentity',
            'readyMarkerSHA256', 'policySHA256', 'deploymentId', 'publicOrigin', 'identityScope', 'nonce'}
    _need(type(proof) is dict and set(proof) == keys
          and proof['version'] == 1 and type(proof['version']) is int
          and proof['kind'] == 'HeartOfTheRainStagingSdkUpgrade126'
          and proof['state'] in ('ReadyBackup', 'Complete')
          and proof['fromSchema'] == 15 and proof['toSchema'] == 125
          and proof['backupName'] == name
          and all(proof[key] == value for key, value in snapshots._binding(owner).items())
          and proof['policySHA256'] == policy_hash(policy)
          and proof['readyMarkerSHA256'] == _hash(snapshots._bytes(dict(owner, state='Ready')))
          and re.fullmatch(r'[0-9a-f]{32}', proof['operationId'])
          and path.read_bytes() == snapshots._bytes(proof), 'sdk126_receipt_invalid')
    for key in ('snapshotSHA256', 'sourceLogicalSHA256'):
        _need(type(proof[key]) is str and re.fullmatch(r'[0-9a-f]{64}', proof[key]), 'sdk126_receipt_invalid')
    _need(type(proof['snapshotBytes']) is int and proof['snapshotBytes'] > 0,
          'sdk126_receipt_invalid')
    identity = proof['sourceFileIdentity']
    _need(type(identity) is dict and set(identity) == {'device', 'inode'}
          and all(type(value) is int and value >= 0 for value in identity.values()), 'sdk126_receipt_invalid')
    return proof

def _prove_backup(path, proof):
    snapshots._regular(path)
    _need(not any(os.path.lexists(Path(str(path) + suffix)) for suffix in ('-wal','-shm','-journal')),
          'sdk126_backup_sidecar_rejected')
    _need(snapshots._digest(path) == (proof['snapshotSHA256'], proof['snapshotBytes']),
          'sdk126_backup_hash_mismatch')
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        _need(_validate(db) == 15 and _logical15(db) == proof['sourceLogicalSHA256'],
              'sdk126_backup_state_mismatch')

def _read_policy(m, owner):
    path = m.data_directory / POLICY
    snapshots._regular(path)
    _need(path.stat().st_size <= 8192, 'sdk126_policy_invalid')
    policy = staging._json(path.read_bytes())
    keys = {'version','kind','verificationMode','sandbox','appId','packageName','upgradeName',
            'catalogSHA256','catalogFile','dataDirectory','deploymentId','publicOrigin','identityScope','nonce'}
    _need(type(policy) is dict and set(policy) == keys and policy['version'] == 1
          and type(policy['version']) is int and policy['kind'] == 'HeartOfTheRainStagingSdk126'
          and policy['verificationMode'] == 'sdk_client_reported' and policy['sandbox'] is True
          and type(policy['appId']) is int and policy['appId'] > 0
          and policy['dataDirectory'] == str(m.data_directory)
          and policy['catalogFile'] == str(m.data_directory / CATALOG)
          and all(policy[key] == value for key, value in snapshots._binding(owner).items())
          and path.read_bytes() == snapshots._bytes(policy), 'sdk126_policy_invalid')
    _package(policy['packageName'])
    name = snapshots._name(policy['upgradeName'])
    raw, config = _load_catalog(m.data_directory / CATALOG)
    _need(_hash(raw) == policy['catalogSHA256'] and config.appId == policy['appId'],
          'sdk126_catalog_policy_mismatch')
    proof = _read_proof(_paths(m, name)[2], m, owner, name, policy)
    _need(proof['state'] == 'Complete', 'sdk126_upgrade_not_complete')
    _need(proof['sourceFileIdentity'] == _identity(m.data_directory / staging.DATABASE),
          'sdk126_database_replaced')
    return policy

def _package(value):
    _need(type(value) is str and re.fullmatch(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,}', value)
          and not any(token in value for token in ('verification','defaultcompany','example'))
          and value != 'com.heartoftherain.stagingreview', 'sdk126_registered_package_required')
    return value

def require_sdk_ready(manifest_or_path, *, full=True):
    m = staging.read_manifest(manifest_or_path)
    owner = staging.ownership_metadata(m)
    staging._require_ads_policy(m)
    database = staging.owned_database(m)
    policy = _read_policy(m, owner)
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
        validate_sdk_database(db, full=full)
    return m, owner, policy

def prepare_sdk_authority(manifest_or_path, commerce_config_path, package_name, name, *,
                          confirm_sdk_client_reported=False, timeout_seconds=60):
    _need(confirm_sdk_client_reported is True, 'sdk126_explicit_client_reported_confirmation_required')
    package_name, name = _package(package_name), snapshots._name(name)
    _need(len(name) <= 40, 'sdk126_upgrade_name_too_long')
    snapshots._timeout(timeout_seconds)
    raw, config = _load_catalog(Path(commerce_config_path).absolute())
    m = staging.read_manifest(manifest_or_path)
    try:
        with staging._lock(m, staging.RUNTIME_LOCK, allowed_states=STATES):
            with staging.root_lock(m, allowed_states=STATES):
                owner = staging.ownership_metadata(m, allowed_states=STATES)
                staging._require_ads_policy(m)
                staging._configuration_and_worker(m)
                database = staging.owned_database(m, allowed_states=STATES)
                identity = _identity(database)
                marker_path = m.data_directory / staging.MARKER
                ready = dict(owner, state='Ready')
                policy = _policy(m, owner, name, package_name, raw, config)
                backup, monitor_receipt, receipt = _paths(m, name)
                proof = _read_proof(receipt, m, owner, name, policy) if os.path.lexists(receipt) else None
                if owner['state'] == PENDING:
                    _need(proof is not None, 'sdk126_pending_proof_required')
                if proof:
                    _prove_backup(backup, proof)
                    _need(proof['sourceFileIdentity'] == identity, 'sdk126_database_replaced')
                else:
                    for path in (backup, monitor_receipt, receipt, m.data_directory / POLICY, m.data_directory / CATALOG):
                        snapshots._fresh(path)
                with closing(sqlite3.connect(database.as_uri() + '?mode=rw', uri=True,
                                              timeout=timeout_seconds, isolation_level=None)) as db:
                    db.execute('PRAGMA foreign_keys=ON')
                    db.execute('PRAGMA synchronous=FULL')
                    db.execute('BEGIN IMMEDIATE')
                    try:
                        version = db.execute('SELECT version FROM schema_info').fetchall()
                        if version == [(15,)]:
                            _need(_validate(db) == 15, 'sdk126_exact_schema15_required')
                        elif version == [(125,)]:
                            validate_sdk_database(db)
                        else:
                            raise staging.StagingError('sdk126_source_schema_not_supported')
                        if proof and proof['state'] == 'Complete' and owner['state'] == 'Ready':
                            _need(version == [(125,)] and _read_policy(m, owner) == policy,
                                  'sdk126_completed_policy_changed')
                            db.rollback()
                            return _result(proof, policy, True)
                        if proof:
                            _need(_logical15(db) == proof['sourceLogicalSHA256'],
                                  'sdk126_pending_source_state_changed')
                            _need(version != [(125,)] or owner['state'] == PENDING,
                                  'sdk126_pending_marker_required')
                        else:
                            _need(version == [(15,)] and owner['state'] == 'Ready', 'sdk126_exact_schema15_required')
                            logical = _logical15(db)
                            copied = backup_database(database, backup, timeout_seconds=timeout_seconds)
                            proof = dict(version=1, kind='HeartOfTheRainStagingSdkUpgrade126', state='ReadyBackup',
                                operationId=uuid.uuid4().hex, backupName=name, fromSchema=15, toSchema=125,
                                snapshotSHA256=copied['sha256'], snapshotBytes=copied['bytes'],
                                sourceLogicalSHA256=logical, sourceFileIdentity=identity,
                                readyMarkerSHA256=_hash(snapshots._bytes(ready)), policySHA256=policy_hash(policy),
                                **snapshots._binding(owner))
                            _prove_backup(backup, proof)
                            snapshots._exclusive(receipt, snapshots._bytes(proof))
                            monitor = dict(version=1, kind='HeartOfTheRainStagingBackup105', state='Ready',
                                operationId=proof['operationId'], snapshotName=name,
                                sha256=copied['sha256'], bytes=copied['bytes'], schemaVersion=15,
                                **snapshots._binding(owner))
                            snapshots._exclusive(monitor_receipt, snapshots._bytes(monitor))
                            _checkpoint('AfterBackupReady')
                        if owner['state'] == 'Ready':
                            pending = dict(owner, state=PENDING)
                            snapshots._ready_receipt(marker_path, owner, pending)
                            owner = pending
                        _checkpoint('AfterPendingMarker')
                        for path, data in ((m.data_directory / CATALOG, raw),
                                           (m.data_directory / POLICY, snapshots._bytes(policy))):
                            if os.path.lexists(path):
                                snapshots._regular(path)
                                _need(path.read_bytes() == data, 'sdk126_pending_configuration_changed')
                            else:
                                snapshots._exclusive(path, data)
                        _checkpoint('AfterPolicyReady')
                        if version == [(15,)]:
                            apply_sdk_upgrade(db)
                        validate_sdk_database(db)
                        _need(_logical15(db) == proof['sourceLogicalSHA256'], 'sdk126_original_state_not_preserved')
                        _need(db.execute("SELECT COUNT(*) FROM commerce_orders WHERE verification_mode!='provider_api'").fetchone()[0] == 0,
                              'sdk126_historical_order_mode_changed')
                        _need(_identity(database) == identity
                              and marker_path.read_bytes() == snapshots._bytes(owner),
                              'sdk126_owner_or_database_changed')
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
                _need(_identity(database) == identity, 'sdk126_database_replaced')
                snapshots._ready_receipt(marker_path, owner, ready)
                _checkpoint('AfterReadyMarker')
                require_sdk_ready(m)
                return _result(proof, policy, False)
    except (OperationError, sqlite3.Error):
        raise staging.StagingError('sdk126_database_validation_failed') from None
    except OSError:
        raise staging.StagingError('sdk126_upgrade_interrupted') from None

def _result(proof, policy, repeated):
    return {'status':'staging_sdk126_prepared','fromSchema':15,'toSchema':125,
            'alreadyCompleted':repeated,'verificationMode':'sdk_client_reported','sandbox':True,
            'appId':policy['appId'],'packageName':policy['packageName'],
            'allOriginalTablesPreserved':True,'historicalOrdersRemainProviderApi':True,
            'ownerAndWalletIdentityPreserved':True,'snapshotSHA256':proof['snapshotSHA256'],
            'policySHA256':policy_hash(policy),'serviceStarted':False,'productionEnabled':False,
            'providerAcceptanceVerified':False}

class _Permit:
    def __init__(self, secret, manifest, owner, policy):
        _need(secret is _SECRET, 'sdk126_private_permit_required')
        self._manifest = manifest
        self._owner_bytes = snapshots._bytes(owner)
        self._policy_bytes = snapshots._bytes(policy)
        self._policy_hash = policy_hash(policy)
        self._open, self._inflight = True, 0
        self._condition = threading.Condition()
        self._checked_at = time.monotonic()
        self._checking, self._failures = False, 0

    @property
    def manifest(self):
        return self._manifest

    @property
    def owner(self):
        return json.loads(self._owner_bytes)

    @property
    def policy(self):
        return json.loads(self._policy_bytes)

    def validate(self, database_path):
        with self._condition:
            _need(self._open, 'sdk126_runtime_closed')
        _need(database_path is not None and Path(database_path).resolve() ==
              self.manifest.data_directory / staging.DATABASE, 'sdk126_owned_database_required')
        owner = staging.ownership_metadata(self.manifest)
        _need(owner == self.owner and policy_hash(_read_policy(self.manifest, owner)) == self._policy_hash,
              'sdk126_runtime_owner_or_policy_changed')
        staging._require_ads_policy(self.manifest)

    def _revalidate(self):
        try:
            self.validate(self.manifest.data_directory / staging.DATABASE)
        except Exception:
            failed = True
        else:
            failed = False
        with self._condition:
            self._failures = self._failures + 1 if failed else 0
            self._checked_at, self._checking = time.monotonic(), False

    def enter(self):
        # A request only reads flags. A background check every few seconds re-proves ownership and
        # policy from their files, so requests never wait on that I/O, and one failed file read
        # does not refuse players: a real change closes the service after a few failed checks.
        start = False
        with self._condition:
            if not self._open or self._failures >= PERMIT_FAILURES_TO_CLOSE:
                closed = True
            else:
                closed = False
                self._inflight += 1
            if self._open and not self._checking and time.monotonic() - self._checked_at >= PERMIT_CHECK_SECONDS:
                self._checking = start = True
        if start:
            threading.Thread(target=self._revalidate, daemon=True, name='hotr-permit-check').start()
        return not closed

    def leave(self):
        with self._condition:
            self._inflight -= 1
            if self._inflight == 0:
                self._condition.notify_all()

    def close(self):
        with self._condition:
            self._open = False
            while self._inflight:
                self._condition.wait()

@contextmanager
def _application_context(manifest_or_path, *, clock=None):
    m = staging.read_manifest(manifest_or_path)
    permit, listener, app = None, None, None
    with staging._lock(m, staging.RUNTIME_LOCK, allowed_states=('Ready',)):
        try:
            with staging.root_lock(m, allowed_states=('Ready',)):
                m, owner, policy = require_sdk_ready(m, full=False)
                worker = staging._configuration_and_worker(m)
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if os.name == 'nt':
                    listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                try:
                    # Bind now to own the port. uvicorn listens once the app is ready, so a
                    # client during a restart is refused at once and not left waiting.
                    listener.bind(('127.0.0.1', m.port))
                except OSError:
                    raise staging.StagingError('sdk126_loopback_bind_unavailable') from None
                permit = _Permit(_SECRET, m, owner, policy)
                from .api import create_app
                from .rustore_provider import UnavailablePurchaseProvider
                from .vk_provider import VkConfiguration
                app = create_app(database_path=m.data_directory / staging.DATABASE,
                    config_path=staging.CONFIG, clock=clock,
                    commerce_config_path=m.data_directory / CATALOG,
                    commerce_provider=UnavailablePurchaseProvider(),
                    identity_enabled=True, social_enabled=True, notifications_enabled=False,
                    replay_enabled=m.replay.enabled, replay_worker=worker,
                    ads_config_path=m.data_directory / staging.ADS,
                    vk_configuration=VkConfiguration(m.vk.enabled,m.vk.client_id,m.vk.redirect_uri),
                    trusted_client_header='X-Hotr-Verified-Client-IP', service_runtime=True,
                    _staging_sdk_permit126=permit)
                app.state.sdk_staging_socket126 = listener
            yield app
        finally:
            runtime = getattr(app.state, 'service_runtime136', None) if app is not None else None
            if runtime is not None:
                runtime.stop()
            if permit is not None:
                permit.close()
            if listener is not None:
                listener.close()

def application_context(manifest, *, clock=None):
    from .staging_versioned_runtime117 import _ApplicationContext
    return _ApplicationContext(_application_context(manifest, clock=clock))

def preflight(manifest):
    m, owner, policy = require_sdk_ready(manifest)
    staging._configuration_and_worker(m)
    return {'status':'staging_sdk126_preflight_passed','mode':'staging','schemaVersion':125,
            'verificationMode':'sdk_client_reported','sandbox':True,'appId':policy['appId'],
            'packageName':policy['packageName'],'commerceEnabled':True,
            'adsEnabled':m.rewarded_ads_enabled,'gameplayConfigured':m.replay.enabled,
            'productionEnabled':False,'processStarted':False,'providerAcceptanceVerified':False}

def start(manifest, *, run_id=None):
    m = staging.read_manifest(manifest)
    run_id = run_id or uuid.uuid4().hex
    _need(type(run_id) is str and re.fullmatch(r'[0-9a-f]{32}', run_id), 'sdk126_run_id_invalid')
    rendezvous = m.data_directory / ('rendezvous-' + run_id + '.json')
    snapshots._fresh(rendezvous)
    original_environment = dict(os.environ)
    proof = None
    try:
        os.environ.clear()
        os.environ.update(staging.child_environment(m, original_environment))
        with application_context(m) as app:
            _, owner, policy = require_sdk_ready(m, full=False)
            listener = app.state.sdk_staging_socket126
            proof = snapshots._bytes(dict(version=1,runId=run_id,pid=os.getpid(),host='127.0.0.1',
                port=listener.getsockname()[1],deploymentId=m.deployment_id,nonce=owner['nonce'],
                productionEnabled=False,commerceEnabled=True,verificationMode='sdk_client_reported',
                sandbox=True,appId=policy['appId'],packageName=policy['packageName'],
                adsEnabled=m.rewarded_ads_enabled,providerAcceptanceVerified=False))
            snapshots._exclusive(rendezvous, proof)
            import uvicorn
            config = uvicorn.Config(app, host='127.0.0.1', port=m.port, access_log=False,
                proxy_headers=False, limit_concurrency=None, log_level='warning')
            uvicorn.Server(config).run(sockets=[listener])
    finally:
        if proof is not None and rendezvous.is_file() and rendezvous.read_bytes() == proof:
            rendezvous.unlink()
        os.environ.clear()
        os.environ.update(original_environment)

class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise staging.StagingError('sdk126_arguments_invalid')

def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument('command', choices=('prepare','preflight','start'))
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--commerce-config')
    parser.add_argument('--package-name')
    parser.add_argument('--name')
    parser.add_argument('--confirm-sdk-client-reported', action='store_true')
    parser.add_argument('--timeout-seconds', type=int, default=60)
    parser.add_argument('--run-id')
    try:
        args = parser.parse_args(argv)
        if args.command == 'prepare':
            _need(args.commerce_config is not None and args.name is not None, 'sdk126_prepare_inputs_required')
            result = prepare_sdk_authority(args.manifest,args.commerce_config,args.package_name,args.name,
                confirm_sdk_client_reported=args.confirm_sdk_client_reported,timeout_seconds=args.timeout_seconds)
        elif args.command == 'preflight':
            result = preflight(args.manifest)
        else:
            start(args.manifest,run_id=args.run_id)
            result = {'status':'staging_sdk126_stopped','productionEnabled':False}
        print(json.dumps(result,separators=(',',':')))
        return 0
    except (staging.StagingError, OperationError, sqlite3.Error, OSError, ValueError, TypeError):
        print(json.dumps({'status':'blocked_staging_sdk126','productionEnabled':False},separators=(',',':')))
        return 1

if __name__ == '__main__':
    # The API authenticates the exact package-private permit type. Construct it
    # in the canonical imported module, never the separate __main__ namespace.
    from .staging_sdk126 import main as package_main
    raise SystemExit(package_main())

