"""Explicit single-host staging launch support; no production activation.

Preflight reads files only. Initialization writes no database. The launcher
holds a runtime lock and a retained loopback socket before constructing SQLite.
"""
from __future__ import annotations

import argparse
from contextlib import closing, contextmanager
from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import stat
import sys
import uuid
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).resolve().parents[1] / 'config'
MARKER = '.hotr-staging105-owner.json'
CONTROL_LOCK = '.hotr-staging105-control.lock'
RUNTIME_LOCK = '.hotr-staging105-runtime.lock'
DATABASE = 'authority.sqlite3'
COMMERCE = '.hotr-staging105-commerce.json'
ADS = '.hotr-staging105-ads.json'
_COMMERCE = {'version': 'rustore-commerce-v1', 'enabled': False, 'appId': None, 'sandbox': True, 'products': []}
_ADS = {'version': 'rewarded-shop-v1', 'enabled': False, 'completionMode': 'sdk_client_reported_capped', 'placement': 'shop_rewarded', 'rewardCoins': 400, 'dailyLimit': 3, 'dayMode': 'player_local', 'utcOffsetSeconds': 36000, 'cooldownSeconds': 600, 'opportunityTtlSeconds': 900}


class StagingError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class VkSettings:
    enabled: bool
    client_id: str
    redirect_uri: str


@dataclass(frozen=True)
class ReplaySettings:
    enabled: bool
    bundle: str
    approval_file: str
    approval_sha256: str


@dataclass(frozen=True)
class StagingManifest:
    public_origin: str
    identity_scope: str
    deployment_id: str
    data_directory: Path
    port: int
    vk: VkSettings
    replay: ReplaySettings
    rewarded_ads_enabled: bool = False


def _require(condition, code):
    if not condition:
        raise StagingError(code)


def _json(raw, maximum=16384):
    _require(isinstance(raw, bytes) and 2 <= len(raw) <= maximum, 'staging_json_size_invalid')
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'staging_duplicate_key')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        _require(type(value) is dict, 'staging_json_invalid')
        return value
    except StagingError:
        raise
    except (ValueError, UnicodeError, TypeError, RecursionError):
        raise StagingError('staging_json_invalid') from None


def _bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode('ascii')


def _plain(path):
    # Inspect ancestors first and do not follow a reparse point to inspect a
    # child: that could contact a remote junction target before rejecting it.
    for p in reversed((path, *path.parents)):
        try:
            info = p.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise StagingError('staging_linked_path_rejected')
        if stat.S_ISREG(info.st_mode):
            _require(info.st_nlink == 1, 'staging_hardlink_rejected')


def _fixed_local_drive(drive):
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetDriveTypeW.argtypes = (wintypes.LPCWSTR,)
    kernel.GetDriveTypeW.restype = wintypes.UINT
    return kernel.GetDriveTypeW(drive + '\\') == 3  # DRIVE_FIXED only


def _local_path(raw, *, absolute_required=False):
    _require(isinstance(raw, (str, Path)) and str(raw) and not any(ord(c) < 32 for c in str(raw)), 'staging_local_path_required')
    text = str(raw)
    _require(not text.startswith(('\\\\', '//')), 'staging_network_storage_rejected')
    path = Path(raw)
    _require(not absolute_required or path.is_absolute(), 'staging_absolute_path_required')
    path = Path(os.path.abspath(path))
    _require(path != Path(path.anchor), 'staging_filesystem_root_rejected')
    if os.name == 'nt':
        _require(re.fullmatch(r'[A-Za-z]:', path.drive) and _fixed_local_drive(path.drive), 'staging_network_storage_rejected')
    return path


def _private_path(raw):
    path = _local_path(raw, absolute_required=True)
    _plain(path)
    path = path.resolve()
    local = REPO / '.verification-cache/Review105'
    _require(not path.is_relative_to(REPO) or path != local and path.is_relative_to(local), 'staging_source_tree_rejected')
    if not path.is_relative_to(local):
        for parent in (path, *path.parents):
            _require(not (parent / '.git').exists(), 'staging_source_tree_rejected')
    return path


def _origin(value):
    _require(type(value) is str and value and len(value) <= 512 and not any(c.isspace() or ord(c) < 32 for c in value), 'staging_owned_https_origin_required')
    try:
        u = urlsplit(value)
        host = u.hostname
        valid = u.scheme == 'https' and u.port in (None, 443) and not u.username and not u.password and not u.query and not u.fragment and u.path in ('', '/') and host and '.' in host and re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', host) and '..' not in host
        _require(valid, 'staging_owned_https_origin_required')
        host = host.lower()
        _require(not re.fullmatch(r'[0-9.]+', host) and not any(host == x or host.endswith('.' + x) for x in ('example.com', 'example.org', 'example.net', 'example', 'invalid', 'test', 'local', 'localhost')), 'staging_owned_https_origin_required')
        return 'https://' + host
    except (ValueError, TypeError):
        raise StagingError('staging_owned_https_origin_required') from None


def read_manifest(value):
    try:
        if isinstance(value, StagingManifest):
            v = {'version': 1, 'mode': 'staging', 'publicOrigin': value.public_origin, 'identityScope': value.identity_scope,
                 'deploymentId': value.deployment_id, 'dataDirectory': str(value.data_directory), 'port': value.port,
                 'rewardedAdsEnabled': value.rewarded_ads_enabled,
                 'vk': {'enabled': value.vk.enabled, 'clientId': value.vk.client_id, 'redirectUri': value.vk.redirect_uri},
                 'replay': {'enabled': value.replay.enabled, 'bundle': value.replay.bundle, 'approvalFile': value.replay.approval_file, 'approvalSHA256': value.replay.approval_sha256}}
        else:
            path = _local_path(value)
            _plain(path)
            _require(path.is_file() and path.stat().st_size <= 16384, 'staging_manifest_required')
            v = _json(path.read_bytes())
        required = {'version', 'mode', 'publicOrigin', 'identityScope', 'deploymentId', 'dataDirectory', 'port', 'vk', 'replay'}
        _require(required <= set(v) <= required | {'rewardedAdsEnabled'}, 'staging_manifest_fields_invalid')
        rewarded_ads_enabled = v.get('rewardedAdsEnabled', False)
        _require(type(rewarded_ads_enabled) is bool, 'staging_rewarded_ads_flag_invalid')
        _require(type(v['version']) is int and v['version'] == 1 and v['mode'] == 'staging', 'staging_mode_invalid')
        origin = _origin(v['publicOrigin'])
        _require(type(v['identityScope']) is str and re.fullmatch(r'review-[a-z0-9.-]{1,50}', v['identityScope']), 'staging_identity_scope_invalid')
        _require(type(v['deploymentId']) is str and re.fullmatch(r'[a-z][a-z0-9-]{2,47}', v['deploymentId']), 'staging_deployment_id_required')
        _require(type(v['port']) is int and (v['port'] == 0 or 1024 <= v['port'] <= 65535), 'staging_port_invalid')
        vk, replay = v['vk'], v['replay']
        _require(type(vk) is dict and set(vk) == {'enabled', 'clientId', 'redirectUri'} and type(vk['enabled']) is bool and type(vk['clientId']) is str and type(vk['redirectUri']) is str, 'staging_vk_fields_invalid')
        if vk['enabled']:
            _require(re.fullmatch(r'[1-9][0-9]{0,19}', vk['clientId']) and vk['redirectUri'] == origin + '/v1/identity/vk/callback', 'staging_vk_configuration_invalid')
        else:
            _require(vk['clientId'] == vk['redirectUri'] == '', 'staging_disabled_vk_fields_must_be_empty')
        _require(type(replay) is dict and set(replay) == {'enabled', 'bundle', 'approvalFile', 'approvalSHA256'} and type(replay['enabled']) is bool and all(type(replay[k]) is str for k in ('bundle', 'approvalFile', 'approvalSHA256')), 'staging_replay_fields_invalid')
        if replay['enabled']:
            _require(Path(replay['bundle']).is_absolute() and Path(replay['approvalFile']).is_absolute() and re.fullmatch(r'[a-f0-9]{64}', replay['approvalSHA256']), 'staging_replay_configuration_invalid')
            _local_path(replay['bundle'], absolute_required=True)
            _local_path(replay['approvalFile'], absolute_required=True)
        else:
            _require(all(replay[k] == '' for k in ('bundle', 'approvalFile', 'approvalSHA256')), 'staging_disabled_replay_fields_must_be_empty')
        return StagingManifest(origin, v['identityScope'], v['deploymentId'], _private_path(v['dataDirectory']), v['port'], VkSettings(vk['enabled'], vk['clientId'], vk['redirectUri']), ReplaySettings(replay['enabled'], replay['bundle'], replay['approvalFile'], replay['approvalSHA256']), rewarded_ads_enabled)
    except StagingError:
        raise
    except (OSError, ValueError, TypeError, AttributeError):
        raise StagingError('staging_manifest_unavailable') from None


def manifest_for_data_directory(manifest, directory):
    return replace(read_manifest(manifest), data_directory=_private_path(directory))


def manifest_mapping(manifest):
    m = read_manifest(manifest)
    return {'version': 1, 'mode': 'staging', 'publicOrigin': m.public_origin, 'identityScope': m.identity_scope,
            'deploymentId': m.deployment_id, 'dataDirectory': str(m.data_directory), 'port': m.port,
            'rewardedAdsEnabled': m.rewarded_ads_enabled,
            'vk': {'enabled': m.vk.enabled, 'clientId': m.vk.client_id, 'redirectUri': m.vk.redirect_uri},
            'replay': {'enabled': m.replay.enabled, 'bundle': m.replay.bundle, 'approvalFile': m.replay.approval_file, 'approvalSHA256': m.replay.approval_sha256}}


def ownership_metadata(manifest, *, allowed_states=('Ready',)):
    m = read_manifest(manifest)
    root = _private_path(m.data_directory)
    try:
        marker = root / MARKER
        _plain(marker)
        v = _json(marker.read_bytes())
        _require(set(v) == {'version', 'kind', 'state', 'deploymentId', 'publicOrigin', 'identityScope', 'dataDirectory', 'nonce'}, 'staging_ownership_invalid')
        _require(v['version'] == 1 and type(v['version']) is int and v['kind'] == 'HeartOfTheRainStaging105' and v['state'] in allowed_states and v['deploymentId'] == m.deployment_id and v['publicOrigin'] == m.public_origin and v['identityScope'] == m.identity_scope and v['dataDirectory'] == str(root) and type(v['nonce']) is str and re.fullmatch(r'[a-f0-9]{32}', v['nonce']), 'staging_ownership_mismatch')
        for child in ('replay-jobs', 'backups', 'restores'):
            path = root / child
            _plain(path)
            _require(path.is_dir(), 'staging_owned_directory_missing')
        for name, expected in ((CONTROL_LOCK, b'0'), (RUNTIME_LOCK, b'0'), (COMMERCE, _bytes(_COMMERCE)), (ADS, None)):
            path = root / name
            _plain(path)
            _require(path.is_file(), 'staging_owned_file_missing')
            if name == ADS:
                _require(path.read_bytes() in (_bytes(_ads_configuration(False)), _bytes(_ads_configuration(True))), 'staging_rewarded_ads_policy_changed')
            elif name not in (CONTROL_LOCK, RUNTIME_LOCK):
                _require(path.read_bytes() == expected, 'staging_disabled_provider_config_changed')
        return v
    except StagingError:
        raise
    except (OSError, ValueError, TypeError):
        raise StagingError('staging_owned_data_unavailable') from None


def owned_database(manifest, *, allowed_states=('Ready',)):
    m = read_manifest(manifest)
    marker = ownership_metadata(m, allowed_states=allowed_states)
    db = m.data_directory / DATABASE
    for suffix in ('', '-wal', '-shm'):
        _plain(m.data_directory / (DATABASE + suffix))
    if marker['state'] == 'Initialized':
        _require(not any((m.data_directory / (DATABASE + x)).exists() for x in ('', '-wal', '-shm')), 'staging_initialized_database_ambiguous')
    elif marker['state'] == 'Ready':
        _require(db.is_file() and db.stat().st_size > 0, 'staging_ready_database_missing')
    return db


def _configuration_and_worker(m, *, for_initialize=False):
    from .schemas import DailyRules, WellworksRules, CupRules
    from .wallet_schemas import LevelCatalog
    from .commerce_schemas import CommerceConfig
    from .newads_schemas import RewardedAdsConfig
    from .team_life110 import TeamLifeRules110
    from .team_invites112 import TeamInvitePolicy112
    try:
        for name, model in (('daily_gift.json', DailyRules), ('wellworks.json', WellworksRules), ('rain_cup.json', CupRules), ('levels.json', LevelCatalog)):
            model.model_validate_json((CONFIG / name).read_bytes())
        TeamLifeRules110.model_validate_json((CONFIG / 'team_help.json').read_bytes())
        TeamInvitePolicy112.model_validate_json((CONFIG / 'team_invites.json').read_bytes())
        CommerceConfig.model_validate(_COMMERCE)
        RewardedAdsConfig.model_validate(_ads_configuration(m.rewarded_ads_enabled))
        if not m.replay.enabled:
            return None
        _require(os.name == 'nt', 'staging_replay_requires_approved_windows_host')
        from .replay_contract import ApprovedWorker, ReplayError
        bundle, approval = Path(m.replay.bundle), Path(m.replay.approval_file)
        _plain(bundle)
        _plain(approval)
        _require(not m.data_directory.is_relative_to(bundle.resolve()), 'staging_data_inside_worker_rejected')
        jobs = m.data_directory.parent if for_initialize else m.data_directory / 'replay-jobs'
        worker = ApprovedWorker(bundle, approval, m.replay.approval_sha256, jobs, enabled=True, timeout_seconds=60)
        _, pins, _ = worker._verify_bundle()
        catalog = LevelCatalog.model_validate_json((CONFIG / 'levels.json').read_bytes())
        for level, pin in zip(catalog.levels, pins['levels'], strict=True):
            _require(level.level == pin['level'] and level.sourceSHA256 == pin['sha256'] and level.configHash == pin['sha256'] and level.moves == pin['moves'], 'staging_worker_catalog_mismatch')
        return worker
    except StagingError:
        raise
    except Exception:
        raise StagingError('staging_rules_or_worker_invalid') from None


def preflight(manifest):
    m = read_manifest(manifest)
    marker = ownership_metadata(m, allowed_states=('Initialized', 'Ready'))
    owned_database(m, allowed_states=('Initialized', 'Ready'))
    _require_ads_policy(m)
    _configuration_and_worker(m)
    return {'status': 'staging_preflight_passed', 'state': marker['state'], 'deploymentId': m.deployment_id, 'productionEnabled': False, 'managedIdentityEnabled': True, 'socialEnabled': True, 'socialConfigured': True, 'gameplayEnabled': m.replay.enabled, 'gameplayConfigured': m.replay.enabled, 'gameplayExecutionVerified': False, 'vkConfigured': m.vk.enabled, 'providerAcceptanceVerified': False, 'commerceEnabled': False, 'adsEnabled': m.rewarded_ads_enabled, 'rewardedCompletionMode': 'sdk_client_reported_capped', 'rewardedCompletionAuthoritative': False, 'adDeliveryVerified': False, 'notificationsEnabled': False, 'databaseStructureChecked': False, 'processStarted': False, 'networkContacted': False}


def _exclusive(path, raw):
    _plain(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as file:
        file.write(raw)
        file.flush()
        os.fsync(file.fileno())


def initialize_owned_data(manifest, *, restore_pending=False):
    m = read_manifest(manifest)
    _require(type(restore_pending) is bool, 'staging_restore_mode_invalid')
    root = _private_path(m.data_directory)
    _require(root.parent.is_dir(), 'staging_private_parent_required')
    _require(not root.exists() or root.is_dir() and not any(root.iterdir()), 'staging_fresh_empty_directory_required')
    _configuration_and_worker(m, for_initialize=True)
    root.mkdir(mode=0o700, exist_ok=True)
    for name in ('replay-jobs', 'backups', 'restores'):
        (root / name).mkdir(mode=0o700)
    for name, raw in ((CONTROL_LOCK, b'0'), (RUNTIME_LOCK, b'0'), (COMMERCE, _bytes(_COMMERCE)), (ADS, _bytes(_ads_configuration(m.rewarded_ads_enabled)))):
        _exclusive(root / name, raw)
    marker = {'version': 1, 'kind': 'HeartOfTheRainStaging105', 'state': 'RestorePending' if restore_pending else 'Initialized', 'deploymentId': m.deployment_id, 'publicOrigin': m.public_origin, 'identityScope': m.identity_scope, 'dataDirectory': str(root), 'nonce': uuid.uuid4().hex}
    _exclusive(root / MARKER, _bytes(marker))
    return marker


@contextmanager
def _lock(manifest, name, *, allowed_states=('Initialized', 'Ready', 'RestorePending')):
    m = read_manifest(manifest)
    ownership_metadata(m, allowed_states=allowed_states)
    path = m.data_directory / name
    _plain(path)
    file = path.open('r+b')
    acquired = False
    try:
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise StagingError('staging_owned_lock_busy') from None
        else:
            import fcntl
            try:
                fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise StagingError('staging_owned_lock_busy') from None
        acquired = True
        yield
    finally:
        if acquired:
            if os.name == 'nt':
                import msvcrt
                file.seek(0)
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)
        file.close()


def root_lock(manifest, *, allowed_states=('Initialized', 'Ready', 'RestorePending')):
    return _lock(manifest, CONTROL_LOCK, allowed_states=allowed_states)


def _ads_configuration(enabled):
    _require(type(enabled) is bool, 'staging_rewarded_ads_flag_invalid')
    return dict(_ADS, enabled=enabled)


def _require_ads_policy(manifest):
    _require((manifest.data_directory / ADS).read_bytes() == _bytes(_ads_configuration(manifest.rewarded_ads_enabled)), 'staging_rewarded_ads_transition_required')


def configure_rewarded_ads(manifest):
    """Explicit stopped-service policy transition; never changes a DB or grant.

    Known config bytes remain recognizable after a lost acknowledgement. A
    retry observes the committed target, without rotating ownership or receipts.
    """
    m = read_manifest(manifest)
    try:
        with _lock(m, RUNTIME_LOCK):
            with root_lock(m):
                ownership_metadata(m, allowed_states=('Initialized', 'Ready'))
                owned_database(m, allowed_states=('Initialized', 'Ready'))
                path = m.data_directory / ADS
                before = path.read_bytes()
                expected = _bytes(_ads_configuration(m.rewarded_ads_enabled))
                changed = before != expected
                if changed:
                    temporary = m.data_directory / ('.rewarded107-' + uuid.uuid4().hex + '.tmp')
                    _exclusive(temporary, expected)
                    _require(path.read_bytes() == before, 'staging_ownership_changed')
                    os.replace(temporary, path)
                return {'status': 'staging_rewarded_ads_configured', 'enabled': m.rewarded_ads_enabled, 'changed': changed,
                        'rewardCoins': 400, 'dailyLimit': 3, 'dayMode': 'player_local', 'cooldownSeconds': 600,
                        'completionMode': 'sdk_client_reported_capped', 'completionAuthoritative': False,
                        'productionEnabled': False, 'databaseChanged': False, 'providerAcceptanceVerified': False}
    except StagingError:
        raise
    except OSError:
        raise StagingError('staging_rewarded_ads_transition_interrupted') from None


def _validate_database(path):
    from .operations import _validate
    from .storage import SCHEMA_VERSION
    try:
        _plain(path)
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1, isolation_level=None)) as db:
            db.execute('PRAGMA query_only=ON')
            _require(_validate(db) == SCHEMA_VERSION, 'staging_current_schema_required')
    except StagingError:
        raise
    except Exception:
        raise StagingError('staging_database_validation_failed') from None


def _ready(m, marker):
    path = m.data_directory / MARKER
    _require(path.read_bytes() == _bytes(marker), 'staging_ownership_changed')
    updated = dict(marker, state='Ready')
    temporary = m.data_directory / ('.staging105-' + uuid.uuid4().hex + '.tmp')
    _exclusive(temporary, _bytes(updated))
    os.replace(temporary, path)
    return updated


def complete_restore(manifest):
    m = read_manifest(manifest)
    with root_lock(m):
        marker = ownership_metadata(m, allowed_states=('RestorePending',))
        db = m.data_directory / DATABASE
        for suffix in ('', '-wal', '-shm'):
            _plain(m.data_directory / (DATABASE + suffix))
        _require(db.is_file() and db.stat().st_size > 0, 'staging_restore_database_missing')
        _validate_database(db)
        return _ready(m, marker)


def app_configuration(manifest):
    m = read_manifest(manifest)
    return {'version': 1, 'mode': 'ManagedGuestServer', 'origin': m.public_origin, 'identityScope': m.identity_scope, 'allowDevelopmentLoopback': False, 'socialEnabled': True}


def export_app_configuration(manifest, destination):
    config = app_configuration(manifest)
    path = _private_path(destination)
    _require(path.parent.is_dir() and path.suffix.lower() == '.json', 'staging_export_destination_invalid')
    raw = json.dumps(config, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    try:
        _exclusive(path, raw)
    except FileExistsError:
        raise StagingError('staging_export_destination_exists') from None
    return {'status': 'staging_app_configuration_exported', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'productionEnabled': False, 'buildPerformed': False}


def child_environment(manifest, ambient):
    m = read_manifest(manifest)
    allowed = {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'COMSPEC', 'PATH', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'LANG', 'LC_ALL', 'TZ'}
    safe = {k: v for k, v in ambient.items() if k.upper() in allowed}
    safe.update(HOTR_BACKEND_MODE='staging', HOTR_BACKEND_DATA_DIR=str(m.data_directory), HOTR_MANAGED_IDENTITY_ENABLED='1', HOTR_SOCIAL_ENABLED='1', HOTR_RUSTORE_NOTIFICATIONS_ENABLED='0', HOTR_VK_ID_ENABLED='0', HOTR_GAMEPLAY_REPLAY_ENABLED='0', PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    return safe


def _construct(m, worker):
    owned_database(m, allowed_states=('Initialized', 'Ready'))
    _require_ads_policy(m)
    from .api import create_app
    from .vk_provider import VkConfiguration
    from .rustore_provider import UnavailablePurchaseProvider
    return create_app(database_path=m.data_directory / DATABASE, config_path=CONFIG,
                      commerce_config_path=m.data_directory / COMMERCE, commerce_provider=UnavailablePurchaseProvider(),
                      identity_enabled=True, social_enabled=True, notifications_enabled=False,
                      replay_enabled=m.replay.enabled, replay_worker=worker, ads_config_path=m.data_directory / ADS, service_runtime=True,
                      vk_configuration=VkConfiguration(m.vk.enabled, m.vk.client_id, m.vk.redirect_uri))


def start(manifest, *, run_id=None):
    m = read_manifest(manifest)
    run_id = run_id or uuid.uuid4().hex
    _require(type(run_id) is str and re.fullmatch(r'[a-f0-9]{32}', run_id), 'staging_run_id_invalid')
    preflight(m)
    sock, rendezvous, proof = None, m.data_directory / ('rendezvous-' + run_id + '.json'), None
    original_environment = dict(os.environ)
    environment_changed = False
    _require(not rendezvous.exists(), 'staging_preserve_existing_run')
    with _lock(m, RUNTIME_LOCK):
        try:
            with root_lock(m):
                preflight(m)
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    if os.name == 'nt':
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                    sock.bind(('127.0.0.1', m.port))
                except OSError:
                    raise StagingError('staging_loopback_bind_unavailable') from None
                marker = ownership_metadata(m, allowed_states=('Initialized', 'Ready'))
                database = owned_database(m, allowed_states=('Initialized', 'Ready'))
                worker = _configuration_and_worker(m)
                environment = child_environment(m, os.environ)
                environment_changed = True
                os.environ.clear()
                os.environ.update(environment)
                if marker['state'] == 'Ready':
                    _validate_database(database)
                app = _construct(m, worker)
                _validate_database(database)
                if marker['state'] == 'Initialized':
                    marker = _ready(m, marker)
                proof = _bytes({'version': 1, 'runId': run_id, 'pid': os.getpid(), 'host': '127.0.0.1', 'port': sock.getsockname()[1], 'deploymentId': m.deployment_id, 'nonce': marker['nonce'], 'productionEnabled': False, 'gameplayEnabled': m.replay.enabled, 'vkConfigured': m.vk.enabled, 'providerAcceptanceVerified': False, 'commerceEnabled': False, 'adsEnabled': m.rewarded_ads_enabled, 'rewardedCompletionAuthoritative': False, 'adDeliveryVerified': False})
                _exclusive(rendezvous, proof)
            import uvicorn
            config = uvicorn.Config(app, host='127.0.0.1', port=m.port, access_log=False, proxy_headers=False, limit_concurrency=None, log_level='warning')
            uvicorn.Server(config).run(sockets=[sock])
        finally:
            try:
                if sock is not None:
                    sock.close()
                if proof is not None and rendezvous.is_file() and rendezvous.read_bytes() == proof:
                    rendezvous.unlink()
            finally:
                if environment_changed:
                    os.environ.clear()
                    os.environ.update(original_environment)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Explicit staging support; no secret or environment dumps.')
    parser.add_argument('command', choices=('preflight', 'initialize', 'start', 'export-app-config', 'configure-rewarded-ads', 'assess-versioned-cutover'))
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--restore-pending', action='store_true')
    parser.add_argument('--run-id')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = read_manifest(args.manifest)
        if args.command == 'preflight':
            result = preflight(manifest)
        elif args.command == 'initialize':
            marker = initialize_owned_data(manifest, restore_pending=args.restore_pending)
            result = {'status': 'staging_owned_data_initialized', 'state': marker['state'], 'productionEnabled': False, 'databaseCreated': False}
        elif args.command == 'export-app-config':
            _require(args.out is not None, 'staging_export_destination_required')
            result = export_app_configuration(manifest, args.out)
        elif args.command == 'configure-rewarded-ads':
            result = configure_rewarded_ads(manifest)
        elif args.command == 'assess-versioned-cutover':
            from . import staging_cutover117 as cutover
            # When invoked with ``python -m``, this CLI is __main__ while the
            # assessor imports the package module. Pass the path and translate
            # its error type instead of mixing their distinct module classes.
            try:
                result = cutover.assess_versioned_cutover(args.manifest)
            except cutover.staging.StagingError as error:
                raise StagingError(error.code) from None
            print(json.dumps(result, separators=(',', ':')))
            return 1 if result['status'] == 'blocked' else 0
        else:
            start(manifest, run_id=args.run_id)
            result = {'status': 'staging_service_stopped', 'productionEnabled': False}
        print(json.dumps(result, separators=(',', ':')))
        return 0
    except StagingError as error:
        print(json.dumps({'status': 'blocked_staging105', 'code': error.code, 'productionEnabled': False}, separators=(',', ':')))
        return 1
    except Exception:
        print(json.dumps({'status': 'blocked_staging105', 'code': 'staging_operation_failed', 'productionEnabled': False}, separators=(',', ':')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
