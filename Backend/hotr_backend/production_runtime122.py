"""Explicit owned production runtime; ordinary local/staging factories stay closed.

The manifest contains public settings and external secret references only.
Initialization never adopts a database. Provider requests occur only when the
resulting application processes an explicitly enabled provider operation.
"""
from contextlib import closing, contextmanager
from dataclasses import dataclass
from typing import Literal
from functools import wraps
import argparse
import hashlib
import inspect
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import threading
import uuid

from pydantic import Field, ValidationError

from .schemas import Model
from .commerce_schemas import CommerceConfig
from . import staging105 as paths

ROOT = Path(__file__).resolve().parents[2]
DATABASE = 'authority.sqlite3'
MARKER = '.hotr-production122-owner.json'
KIND = 'HeartOfTheRainProduction122'
CONTROL_LOCK = '.hotr-production122-control.lock'
RUNTIME_LOCK = '.hotr-production122-runtime.lock'
OPERATIONS_LOCK = '.hotr-production122-operations.lock'
DISABLED_ADS = '.hotr-production122-disabled-ads.json'
_DISABLED_ADS = {'version': 'production122-disabled', 'enabled': False,
                 'completionMode': 'sdk_client_reported_capped'}
_SECRET = object()
PROVIDER_NETWORKS = frozenset(('95.163.133.0/30', '85.198.107.0/24',
                               '79.137.140.128/26', '85.142.251.128/26'))


class ProductionError(Exception):
    """Fixed public codes only; no credential, path or provider exception text."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(value, code):
    if not value:
        raise ProductionError(code)


def _bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('ascii')


def _plain(path):
    try:
        paths._plain(Path(path))
    except paths.StagingError:
        raise ProductionError('production_linked_path_rejected') from None


def _local_path(value, *, private=False):
    try:
        path = paths._local_path(value, absolute_required=True)
        paths._plain(path)
    except paths.StagingError:
        raise ProductionError('production_local_plain_absolute_path_required') from None
    if private:
        _require(not path.is_relative_to(ROOT), 'production_private_path_outside_source_required')
        _require(not any((p / '.git').exists() for p in (path, *path.parents)),
                 'production_private_path_outside_source_required')
    return path


def _json(raw, maximum=131_072):
    try:
        _require(isinstance(raw, bytes) and 2 <= len(raw) <= maximum, 'production_json_size_invalid')
        def pairs(items):
            result = {}
            for key, value in items:
                _require(key not in result, 'production_duplicate_json_key')
                result[key] = value
            return result
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        _require(type(value) is dict, 'production_json_object_required')
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise ProductionError('production_json_invalid') from None


class ProviderConfiguration(Model):
    keyId: str = Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')
    privateKeyFile: str
    notificationKeyFile: str
    allowedNetworks: list[str] = Field(min_length=1, max_length=4)


class ReplayConfiguration(Model):
    bundle: str
    approvalFile: str
    approvalSHA256: str = Field(pattern=r'^[0-9a-f]{64}$')


class VkSettings(Model):
    enabled: bool = False
    clientId: str = ''
    redirectUri: str = ''


class AdsSettings(Model):
    enabled: bool = False
    configFile: str = ''
    configSHA256: str = ''
    acceptClientReportedCompletion: bool = False


class IngressSettings(Model):
    trustedProxyPeer: str
    clientAddressHeader: str


class ManifestInput(Model):
    version: int = Field(ge=1, le=1)
    mode: str
    publicOrigin: str
    identityScope: str = Field(pattern=r'^prod-[a-z0-9.-]{1,50}$')
    deploymentId: str = Field(pattern=r'^[A-Za-z0-9_.-]{1,64}$')
    dataDirectory: str
    port: int = Field(ge=1, le=65535)
    configDirectory: str
    commerceConfig: str
    commerceSHA256: str = Field(pattern=r'^[0-9a-f]{64}$')
    verificationMode: Literal['provider_api', 'sdk_client_reported'] = 'provider_api'
    provider: ProviderConfiguration | None = None
    replay: ReplayConfiguration
    vk: VkSettings
    ads: AdsSettings
    ingress: IngressSettings


@dataclass(frozen=True)
class ProductionManifest:
    public_origin: str
    identity_scope: str
    deployment_id: str
    data_directory: Path
    port: int
    config_directory: Path
    commerce_config: Path
    commerce_sha256: str
    raw_json: bytes
    manifest_sha256: str

    @property
    def verification_mode(self):
        return self.raw.get('verificationMode', 'provider_api')

    @property
    def raw(self):
        return json.loads(self.raw_json)


@dataclass(frozen=True)
class RuntimePolicy122:
    deployment_id: str
    manifest_sha256: str
    production_enabled: bool = True
    verification_mode: str = 'provider_api'


def production_enabled(authority):
    policy = getattr(authority, '_runtime_policy122', None)
    return type(policy) is RuntimePolicy122 and policy.production_enabled


def read_manifest(value):
    try:
        if type(value) is ProductionManifest:
            raw = value.raw_json
        else:
            path = _local_path(value, private=True)
            with path.open('rb') as stream:
                raw = stream.read(131_073)
        model = ManifestInput.model_validate(_json(raw))
        _require(model.mode == 'production', 'production_mode_required')
        try:
            origin = paths._origin(model.publicOrigin)
        except paths.StagingError:
            raise ProductionError('production_owned_https_origin_required') from None
        _require(model.publicOrigin == origin, 'production_canonical_origin_required')
        data = _local_path(model.dataDirectory, private=True)
        config = _local_path(model.configDirectory)
        commerce = _local_path(model.commerceConfig, private=True)
        provider = model.provider
        if model.verificationMode == 'provider_api':
            _require(provider is not None, 'production_provider_configuration_required')
            _local_path(provider.privateKeyFile, private=True)
            _local_path(provider.notificationKeyFile, private=True)
            _require(provider.privateKeyFile != provider.notificationKeyFile,
                     'production_separate_provider_secrets_required')
            _require(set(provider.allowedNetworks) <= PROVIDER_NETWORKS
                     and len(set(provider.allowedNetworks)) == len(provider.allowedNetworks),
                     'production_official_notification_networks_required')
        else:
            _require(provider is None, 'production_sdk_mode_has_no_provider_credentials')
        _local_path(model.replay.bundle)
        _local_path(model.replay.approvalFile)
        _require(model.ingress.trustedProxyPeer == '127.0.0.1'
                 and model.ingress.clientAddressHeader == 'X-Hotr-Verified-Client-IP',
                 'production_verified_loopback_ingress_required')
        from .vk_provider import VkConfiguration
        VkConfiguration(model.vk.enabled, model.vk.clientId, model.vk.redirectUri)
        if model.vk.enabled:
            _require(model.vk.redirectUri == origin + '/v1/identity/vk/callback',
                     'production_vk_callback_origin_mismatch')
        else:
            _require(not model.vk.clientId and not model.vk.redirectUri, 'production_disabled_vk_values_required')
        if model.ads.enabled:
            _local_path(model.ads.configFile, private=True)
            _require(re.fullmatch(r'[0-9a-f]{64}', model.ads.configSHA256)
                     and model.ads.acceptClientReportedCompletion,
                     'production_explicit_capped_ad_policy_required')
        else:
            _require(not model.ads.configFile and not model.ads.configSHA256
                     and not model.ads.acceptClientReportedCompletion,
                     'production_disabled_ad_values_required')
        document = model.model_dump()
        # Keep existing API manifest ownership hashes byte-for-byte compatible.
        if 'verificationMode' not in _json(raw):
            document.pop('verificationMode')
        canonical = _bytes(document)
        return ProductionManifest(origin, model.identityScope, model.deploymentId, data,
            model.port, config, commerce, model.commerceSHA256, canonical,
            hashlib.sha256(canonical).hexdigest())
    except ProductionError:
        raise
    except (OSError, ValueError, TypeError, ValidationError):
        raise ProductionError('production_manifest_invalid') from None


def ownership_metadata(manifest, *, allowed_states=('Ready',)):
    m = read_manifest(manifest)
    try:
        path = m.data_directory / MARKER
        _plain(path)
        value = _json(path.read_bytes(), 16384)
        _require(set(value) == {'version', 'kind', 'state', 'deploymentId', 'publicOrigin',
                 'identityScope', 'dataDirectory', 'manifestSHA256', 'nonce'}, 'production_ownership_invalid')
        _require(type(value['version']) is int and value['version'] == 1
                 and value['kind'] == KIND and value['state'] in allowed_states
                 and value['deploymentId'] == m.deployment_id and value['publicOrigin'] == m.public_origin
                 and value['identityScope'] == m.identity_scope and value['dataDirectory'] == str(m.data_directory)
                 and value['manifestSHA256'] == m.manifest_sha256
                 and isinstance(value['nonce'], str) and re.fullmatch(r'[a-f0-9]{32}', value['nonce']),
                 'production_ownership_mismatch')
        return value
    except ProductionError:
        raise
    except (OSError, ValueError):
        raise ProductionError('production_owned_root_required') from None


def _validate_database(path, *, verification_mode='provider_api'):
    from .operations import _validate
    from .storage import SCHEMA_VERSION
    _plain(path)
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1, isolation_level=None)) as db:
            db.execute('PRAGMA query_only=ON')
            if verification_mode == 'sdk_client_reported':
                from .sdk_schema125 import validate_sdk_database, SDK_SCHEMA_VERSION
                _require(validate_sdk_database(db) == SDK_SCHEMA_VERSION, 'production_sdk_schema_required')
            else:
                _require(_validate(db) == SCHEMA_VERSION, 'production_current_schema_required')
    except ProductionError:
        raise
    except Exception:
        raise ProductionError('production_database_validation_failed') from None


def owned_database(manifest, *, allowed_states=('Ready',)):
    m = read_manifest(manifest)
    marker = ownership_metadata(m, allowed_states=allowed_states)
    path = m.data_directory / DATABASE
    for suffix in ('', '-wal', '-shm'):
        _plain(m.data_directory / (DATABASE + suffix))
    if marker['state'] == 'Initialized':
        _require(not any((m.data_directory / (DATABASE + s)).exists() for s in ('', '-wal', '-shm')),
                 'production_initialization_interrupted_preserve_database')
    else:
        _require(path.is_file() and path.stat().st_size > 0, 'production_database_missing')
        _validate_database(path, verification_mode=m.verification_mode)
    return path


def initialize_owned_data(manifest):
    m = read_manifest(manifest)
    _require(m.data_directory.parent.is_dir(), 'production_parent_directory_required')
    try:
        m.data_directory.mkdir(mode=0o700, exist_ok=False)
    except OSError:
        raise ProductionError('production_fresh_directory_required') from None
    for name in ('replay-jobs', 'backups', 'restores'):
        (m.data_directory / name).mkdir(mode=0o700)
    for name in (CONTROL_LOCK, RUNTIME_LOCK, OPERATIONS_LOCK):
        with (m.data_directory / name).open('xb') as file:
            file.write(b'0')
    with (m.data_directory / DISABLED_ADS).open('xb') as file:
        file.write(_bytes(_DISABLED_ADS)); file.flush(); os.fsync(file.fileno())
    marker = {'version': 1, 'kind': KIND, 'state': 'Initialized',
              'deploymentId': m.deployment_id, 'publicOrigin': m.public_origin,
              'identityScope': m.identity_scope, 'dataDirectory': str(m.data_directory),
              'manifestSHA256': m.manifest_sha256, 'nonce': uuid.uuid4().hex}
    with (m.data_directory / MARKER).open('xb') as file:
        file.write(_bytes(marker)); file.flush(); os.fsync(file.fileno())
    return marker


@contextmanager
def _lock(manifest, name, *, allowed_states=('Initialized', 'Ready')):
    m = read_manifest(manifest)
    _require(name in (CONTROL_LOCK, RUNTIME_LOCK, OPERATIONS_LOCK), 'production_lock_name_invalid')
    ownership_metadata(m, allowed_states=allowed_states)
    path = m.data_directory / name
    _plain(path)
    try:
        file = path.open('r+b')
    except OSError:
        raise ProductionError('production_owned_lock_unavailable') from None
    acquired = False
    try:
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            raise ProductionError('production_owned_lock_busy') from None
        yield
    finally:
        if acquired:
            if os.name == 'nt':
                import msvcrt
                file.seek(0); msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)
        file.close()


def root_lock(manifest, *, allowed_states=('Initialized', 'Ready')):
    return _lock(manifest, CONTROL_LOCK, allowed_states=allowed_states)


def _configuration_unchecked(manifest):
    m = read_manifest(manifest)
    raw = m.raw
    _plain(m.commerce_config)
    data = m.commerce_config.read_bytes()
    _require(len(data) <= 131072 and hashlib.sha256(data).hexdigest() == m.commerce_sha256,
             'production_commerce_hash_mismatch')
    catalog = CommerceConfig.model_validate(_json(data))
    _require(catalog.enabled and not catalog.sandbox, 'production_live_commerce_configuration_required')
    _require(catalog.verificationMode == m.verification_mode, 'production_verification_mode_mismatch')
    _require(m.config_directory.is_dir(), 'production_rules_directory_required')
    if m.verification_mode == 'provider_api':
        for name in ('privateKeyFile', 'notificationKeyFile'):
            path = _local_path(raw['provider'][name], private=True)
            _require(path.is_file() and 1 <= path.stat().st_size <= 16384,
                     'production_external_secret_reference_required')
    ads = raw['ads']
    if ads['enabled']:
        from .newads_schemas import RewardedAdsConfig
        path = _local_path(ads['configFile'], private=True)
        ad_raw = path.read_bytes()
        _require(len(ad_raw) <= 16384 and hashlib.sha256(ad_raw).hexdigest() == ads['configSHA256'],
                 'production_ad_configuration_hash_mismatch')
        config = RewardedAdsConfig.model_validate(_json(ad_raw, 16384))
        _require(config.enabled and config.completionMode == 'sdk_client_reported_capped'
                 and config.rewardCoins == 400 and config.dailyLimit == 3
                 and config.dayMode == 'player_local' and config.cooldownSeconds == 600,
                 'production_approved_capped_ad_policy_required')
    elif m.data_directory.exists():
        path = m.data_directory / DISABLED_ADS
        _plain(path)
        _require(path.is_file() and path.read_bytes() == _bytes(_DISABLED_ADS),
                 'production_disabled_ad_configuration_changed')
    return catalog


def _configuration(manifest):
    try:
        return _configuration_unchecked(manifest)
    except ProductionError:
        raise
    except Exception:
        raise ProductionError('production_configuration_invalid') from None


def _create_worker(m):
    from .replay_contract import ApprovedWorker
    replay = m.raw['replay']
    try:
        worker = ApprovedWorker(replay['bundle'], replay['approvalFile'], replay['approvalSHA256'],
                                m.data_directory / 'replay-jobs', enabled=True)
        worker._verify_bundle()
        return worker
    except Exception:
        raise ProductionError('production_approved_worker_unavailable') from None


class _ProductionPermit:
    def __init__(self, secret, manifest, purpose):
        _require(secret is _SECRET and purpose in ('api', 'operations'), 'production_owned_permit_required')
        self._manifest, self._purpose = manifest, purpose
        self._policy = RuntimePolicy122(manifest.deployment_id, manifest.manifest_sha256,
                                         verification_mode=manifest.verification_mode)
        self._nonce = ownership_metadata(manifest, allowed_states=('Initialized', 'Ready'))['nonce']
        self._condition = threading.Condition()
        self._open, self._inflight = True, 0

    @property
    def manifest(self):
        return self._manifest

    @property
    def purpose(self):
        return self._purpose

    @property
    def policy(self):
        return self._policy

    def validate(self, database_path):
        with self._condition:
            _require(self._open, 'production_runtime_closed')
        expected = self.manifest.data_directory / DATABASE
        _require(database_path is not None and Path(database_path).resolve() == expected.resolve(),
                 'production_authority_path_mismatch')
        marker = ownership_metadata(self.manifest, allowed_states=('Initialized', 'Ready'))
        _require(marker['nonce'] == self._nonce, 'production_authority_owner_changed')
        _plain(expected)

    def enter(self):
        with self._condition:
            if not self._open:
                return False
            try:
                marker = ownership_metadata(self.manifest, allowed_states=('Ready',))
                _require(marker['nonce'] == self._nonce, 'production_authority_owner_changed')
            except ProductionError:
                return False
            self._inflight += 1
            return True

    def leave(self):
        with self._condition:
            self._inflight -= 1
            if not self._inflight:
                self._condition.notify_all()

    def close(self):
        with self._condition:
            self._open = False
            while self._inflight:
                self._condition.wait()

    def client_address(self, request):
        from .service import ServiceError
        peer = request.client.host if request.client else ''
        if peer != self.manifest.raw['ingress']['trustedProxyPeer']:
            raise ServiceError(403, 'production_proxy_peer_required')
        values = request.headers.getlist(self.manifest.raw['ingress']['clientAddressHeader'])
        try:
            _require(len(values) == 1, 'production_verified_client_address_required')
            value = values[0]
            address = ipaddress.ip_address(value)
            _require(str(address) == value and not address.is_loopback
                     and not address.is_unspecified and not address.is_multicast,
                     'production_verified_client_address_required')
            return value
        except (ValueError, ProductionError):
            raise ServiceError(403, 'production_verified_client_address_required') from None


def fence_routes(app, permit, notifications, reviewed_notifications):
    from fastapi.routing import APIRoute
    from fastapi.security import HTTPBearer
    from .service import ServiceError
    visited = set()
    def guarded(call):
        @wraps(call)
        def invoke(*args, **kwargs):
            if not permit.enter():
                raise ServiceError(503, 'production_runtime_closed')
            try:
                return call(*args, **kwargs)
            finally:
                permit.leave()
        return invoke
    def visit(dependant, reviewed=False):
        if id(dependant) in visited:
            return
        visited.add(id(dependant))
        for child in dependant.dependencies:
            visit(child)
        call = dependant.call
        if inspect.isfunction(call) and not inspect.iscoroutinefunction(call):
            dependant.call = guarded(call)
        elif inspect.isfunction(call) and not reviewed:
            raise ProductionError('production_unreviewed_async_endpoint')
        elif not inspect.isfunction(call) and type(call) is not HTTPBearer:
            raise ProductionError('production_unreviewed_callable_dependency')
    notifications.receive = guarded(notifications.receive)
    allowed = dict(reviewed_notifications)
    for route in app.routes:
        if isinstance(route, APIRoute):
            visit(route.dependant, allowed.get(route.path) is route.dependant.call)


def require_owned_application(app, manifest, *, purpose='operations'):
    m = read_manifest(manifest)
    permit = getattr(app.state, 'production_permit122', None)
    _require(type(permit) is _ProductionPermit and permit.purpose == purpose
             and permit.manifest.manifest_sha256 == m.manifest_sha256,
             'production_owned_application_required')
    permit.validate(m.data_directory / DATABASE)
    owned_database(m)
    return permit


@contextmanager
def _application_context(manifest, *, purpose='api', clock=None):
    m = read_manifest(manifest)
    _require(purpose in ('api', 'operations'), 'production_runtime_purpose_invalid')
    allowed = ('Initialized', 'Ready') if purpose == 'api' else ('Ready',)
    listener = permit = None
    with _lock(m, RUNTIME_LOCK if purpose == 'api' else OPERATIONS_LOCK, allowed_states=allowed):
        try:
            with root_lock(m, allowed_states=allowed):
                marker = ownership_metadata(m, allowed_states=allowed)
                database = owned_database(m, allowed_states=allowed)
                _configuration(m)
                if purpose == 'api':
                    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    if os.name == 'nt':
                        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                    try:
                        listener.bind(('127.0.0.1', m.port))
                    except OSError:
                        raise ProductionError('production_loopback_bind_unavailable') from None
                worker = _create_worker(m)
                from .rustore_provider import RuStoreInvoiceProvider
                from .rustore_auth import RuStoreTokenSupplier
                from .notifications import file_key_source
                from .vk_provider import VkConfiguration
                from .api import create_app
                raw = m.raw
                provider = raw['provider']
                sdk_mode = m.verification_mode == 'sdk_client_reported'
                purchase_provider = notification_source = None
                networks = ()
                if not sdk_mode:
                    supplier = RuStoreTokenSupplier.from_file(provider['keyId'], provider['privateKeyFile'])
                    purchase_provider = RuStoreInvoiceProvider(supplier)
                    notification_source = file_key_source(provider['notificationKeyFile'])
                    networks = provider['allowedNetworks']
                permit = _ProductionPermit(_SECRET, m, purpose)
                vk = raw['vk']
                if marker['state'] == 'Initialized':
                    # Reserve a new empty file exclusively. An interrupted
                    # initialization remains blocked and is never adopted.
                    with database.open('xb'):
                        pass
                app = create_app(database_path=database, config_path=m.config_directory, clock=clock,
                    commerce_config_path=m.commerce_config, commerce_provider=purchase_provider,
                    identity_enabled=True, social_enabled=True, replay_enabled=True, replay_worker=worker, service_runtime=True,
                    notifications_enabled=not sdk_mode, notification_key_source=notification_source,
                    notification_allowed_networks=networks,
                    vk_configuration=VkConfiguration(vk['enabled'], vk['clientId'], vk['redirectUri']),
                    ads_config_path=raw['ads']['configFile'] if raw['ads']['enabled'] else m.data_directory / DISABLED_ADS,
                    _production_permit122=permit)
                _validate_database(database, verification_mode=m.verification_mode)
                if marker['state'] == 'Initialized':
                    _require((m.data_directory / MARKER).read_bytes() == _bytes(marker),
                             'production_ownership_changed_during_initialization')
                    marker = dict(marker, state='Ready')
                    temporary = m.data_directory / ('.ready-' + uuid.uuid4().hex + '.tmp')
                    with temporary.open('xb') as stream:
                        stream.write(_bytes(marker)); stream.flush(); os.fsync(stream.fileno())
                    os.replace(temporary, m.data_directory / MARKER)
                app.state.production_permit122 = permit
                app.state.production_socket122 = listener
            yield app
        finally:
            if permit is not None:
                permit.close()
            if listener is not None:
                listener.close()


def application_context(manifest, *, purpose='api', clock=None):
    # This previously exercised generic context wrapper retains ownership while
    # synchronous FastAPI workers drain, including async caller cancellation.
    from .staging_versioned_runtime117 import _ApplicationContext
    return _ApplicationContext(_application_context(manifest, purpose=purpose, clock=clock))


def preflight(manifest):
    m = read_manifest(manifest)
    _configuration(m)
    return {'status': 'production_configuration_preflight_passed',
            'productionRuntimeImplemented': True, 'productionActivated': False,
            'providerAcceptanceVerified': False, 'providerNetworkContacted': False,
            'secretContentsRead': False, 'existingAuthorityAdopted': False}


def start(manifest):
    import uvicorn
    m = read_manifest(manifest)
    with application_context(m) as app:
        config = uvicorn.Config(app, host='127.0.0.1', port=m.port, proxy_headers=False,
                                access_log=False, limit_concurrency=None, log_level='warning')
        uvicorn.Server(config).run(sockets=[app.state.production_socket122])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preflight', 'initialize', 'start'))
    parser.add_argument('--manifest', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'preflight':
            result = preflight(args.manifest)
        elif args.command == 'initialize':
            marker = initialize_owned_data(args.manifest)
            result = {'status': 'production_fresh_root_initialized', 'state': marker['state'],
                      'databaseCreated': False, 'productionActivated': False}
        else:
            start(args.manifest)
            result = {'status': 'production_owned_runtime_stopped'}
        print(json.dumps(result, separators=(',', ':')))
        return 0
    except ProductionError as error:
        print(json.dumps({'status': 'blocked_production122', 'code': error.code}, separators=(',', ':')))
        return 1
    except Exception:
        print(json.dumps({'status': 'blocked_production122', 'code': 'production_operation_failed'}, separators=(',', ':')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
