"""Prepare an isolated Unity2022 staging candidate; never build, deploy or contact a host.

Unknown/duplicate fields are rejected before any output directory is created.
Only canonical allowlisted non-secret settings reach the candidate receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import sys
import uuid
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = 'com.heartoftherain.stagingreview'
RESOURCE = Path('Assets/HeartOfTheRain/Resources/HOTR_Server/ManagedStaging.json')
FIELDS = ('version', 'mode', 'origin', 'identityScope', 'allowDevelopmentLoopback', 'socialEnabled')


class Blocked(ValueError):
    """Contains a fixed code only; never include owner configuration text."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Blocked('DUPLICATE_CONFIGURATION_KEY')
        result[key] = value
    return result


def canonical_configuration(raw: str) -> str:
    if not isinstance(raw, str) or not 2 <= len(raw.encode('utf-8')) <= 8192:
        raise Blocked('CONFIGURATION_SIZE_INVALID')
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=lambda _: (_ for _ in ()).throw(Blocked('CONFIGURATION_NUMBER_INVALID')))
    except Blocked:
        raise
    except (ValueError, TypeError, RecursionError):
        raise Blocked('CONFIGURATION_JSON_INVALID') from None
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        raise Blocked('CONFIGURATION_FIELDS_INVALID')
    if type(value['version']) is not int or value['version'] != 1 or value['mode'] != 'ManagedGuestServer':
        raise Blocked('CONFIGURATION_MODE_INVALID')
    if value['allowDevelopmentLoopback'] is not False or type(value['socialEnabled']) is not bool:
        raise Blocked('CONFIGURATION_FLAGS_INVALID')
    if not isinstance(value['identityScope'], str) or not re.fullmatch(r'review-[a-z0-9.-]{1,50}', value['identityScope']):
        raise Blocked('CONFIGURATION_SCOPE_INVALID')
    origin = value['origin']
    if not isinstance(origin, str) or not origin or any(c.isspace() or ord(c) < 32 for c in origin):
        raise Blocked('MISSING_OR_PLACEHOLDER_STAGING_ORIGIN')
    try:
        uri = urlsplit(origin)
        host, port = uri.hostname, uri.port
        if uri.scheme != 'https' or uri.username is not None or uri.password is not None or uri.query or uri.fragment or uri.path not in ('', '/') or not host or '.' not in host:
            raise ValueError()
        host = host.lower()
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host) or '..' in host:
            raise ValueError()
        for suffix in ('example.com', 'example.org', 'example.net', 'example', 'invalid', 'test', 'local', 'localhost'):
            if host == suffix or host.endswith('.' + suffix):
                raise ValueError()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError()
        if port is not None and not 1 <= port <= 65535:
            raise ValueError()
    except (ValueError, TypeError):
        raise Blocked('MISSING_OR_PLACEHOLDER_STAGING_ORIGIN') from None
    value['origin'] = 'https://' + host + (f':{port}' if port not in (None, 443) else '')
    # Same field order as ServerGameplayConfiguration/JsonUtility. Unicode is
    # impossible in the validated settings; no arbitrary input is copied.
    return json.dumps({k: value[k] for k in FIELDS}, separators=(',', ':'), ensure_ascii=True)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plain(path: Path):
    for part in (path, *path.parents):
        if part.exists() and (part.is_symlink() or getattr(part.stat(), 'st_file_attributes', 0) & 0x400):
            raise Blocked('LINKED_PATH_REJECTED')


def _sources(source: Path):
    unity = source / 'Unity'
    if not (source / 'AGENTS.md').is_file() or not (unity / 'ProjectSettings/ProjectVersion.txt').is_file():
        raise Blocked('SOURCE_PROJECT_REQUIRED')
    if 'm_EditorVersion: 2022.3.62f3\n' not in (unity / 'ProjectSettings/ProjectVersion.txt').read_text(encoding='utf-8').replace('\r\n', '\n'):
        raise Blocked('PINNED_UNITY2022_REQUIRED')
    if (unity / '.hotr-staging104-lease.json').exists():
        raise Blocked('STALE_STAGING_SOURCE_REJECTED')
    result = {}
    for component in ('Assets', 'Packages', 'ProjectSettings'):
        base = unity / component
        _plain(base)
        for directory, names, files in os.walk(base, followlinks=False):
            for name in (*names, *files):
                node = Path(directory) / name
                _plain(node)
                normalized = node.relative_to(unity).as_posix().lower()
                key = normalized.rsplit('/resources/', 1)[-1]
                if '/resources/' in normalized and not normalized.endswith('.meta') and (key.rsplit('.', 1)[0] == 'hotr_server/managedstaging' or key.startswith('hotr_server/managedstaging/')):
                    raise Blocked('STALE_STAGING_SOURCE_REJECTED')
            for name in files:
                path = Path(directory) / name
                if path.stat().st_nlink != 1:
                    raise Blocked('HARDLINKED_SOURCE_REJECTED')
                relative = path.relative_to(unity).as_posix()
                normalized = relative.lower()
                key = normalized.rsplit('/resources/', 1)[-1]
                if '/resources/' in normalized and not normalized.endswith('.meta') and key.rsplit('.', 1)[0] == 'hotr_server/managedstaging':
                    raise Blocked('STALE_STAGING_SOURCE_REJECTED')
                result[relative] = sha(path)
    return dict(sorted(result.items()))


def prepare(source: Path, config: Path, tag: str, execute: bool):
    if not config or not config.is_file() or config.stat().st_size > 8192:
        raise Blocked('CONFIGURATION_REQUIRED')
    canonical = canonical_configuration(config.read_text(encoding='utf-8'))
    if not execute:
        return {'status': 'READY_FOR_EXPLICIT_PREPARATION104', 'buildPerformed': False, 'networkContacted': False, 'packageName': PACKAGE}
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', tag or ''):
        raise Blocked('SAFE_FRESH_TAG_REQUIRED')
    source = source.resolve()
    candidate = source / '.verification-cache/Review104/Candidates' / tag
    project = candidate / 'Game'
    _plain(candidate)
    if candidate.exists():
        raise Blocked('PRESERVE_EXISTING_STAGING_ATTEMPT')
    before = _sources(source)
    # Every validation above precedes the first filesystem mutation.
    candidate.mkdir(parents=True, exist_ok=False)
    outcome = {'version': 1, 'status': 'FAILED_STAGING104_PREPARATION', 'sourceRoot': str(source), 'project': str(project),
               'nonce': uuid.uuid4().hex, 'configSHA256': hashlib.sha256(canonical.encode('utf-8')).hexdigest(),
               'unity': '2022.3.62f3', 'copiedPaths': [], 'copiedSHA256': [], 'buildPerformed': False, 'networkContacted': False}
    try:
        for relative, expected in before.items():
            origin, target = source / 'Unity' / relative, project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, target)
            if sha(target) != expected or target.stat().st_nlink != 1:
                raise Blocked('ISOLATED_COPY_MISMATCH')
        settings = project / 'ProjectSettings/ProjectSettings.asset'
        raw = settings.read_bytes()
        # Separate persistent Editor identity BEFORE first import. Only this
        # isolated settings copy changes; pinned engine and package bytes stay.
        raw, n1 = re.subn(rb'(?m)^  companyName: [^\r\n]*', b'  companyName: HeartRainStaging104', raw)
        raw, n2 = re.subn(rb'(?m)^  productName: [^\r\n]*', b'  productName: HeartRainStaging104', raw)
        raw, n3 = re.subn(rb'(?m)^(  applicationIdentifier:\r?\n)    Android: [^\r\n]*', rb'\1    Android: com.heartoftherain.stagingreview', raw)
        raw, n4 = re.subn(rb'(?m)^  androidUseCustomKeystore: [^\r\n]*', b'  androidUseCustomKeystore: 0', raw)
        if (n1, n2, n3, n4) != (1, 1, 1, 1):
            raise Blocked('ISOLATED_IDENTITY_FIELDS_INVALID')
        block = re.search(rb'(?m)^  applicationIdentifier:\r?\n((?:    [^\r\n]*\r?\n)+)', raw)
        if not block:
            raise Blocked('ISOLATED_IDENTITY_FIELDS_INVALID')
        identifiers = block.group(1)
        if re.search(rb'(?m)^    Standalone:', identifiers):
            identifiers, count = re.subn(rb'(?m)^    Standalone: [^\r\n]*', b'    Standalone: com.heartoftherain.stagingreview', identifiers)
            if count != 1:
                raise Blocked('ISOLATED_IDENTITY_FIELDS_INVALID')
        else:
            identifiers += b'    Standalone: com.heartoftherain.stagingreview\n'
        raw = raw[:block.start(1)] + identifiers + raw[block.end(1):]
        settings.write_bytes(raw)
        if _sources(source) != before:
            raise Blocked('MAIN_SOURCE_CHANGED_DURING_PREPARATION')
        copied = {relative: sha(project / relative) for relative in before}
        outcome.update(status='PREPARED_STAGING104', copiedPaths=list(copied), copiedSHA256=list(copied.values()),
                       isolatedSettingsDelta={'companyName': 'HeartRainStaging104', 'productName': 'HeartRainStaging104',
                                              'androidPackage': PACKAGE, 'standalonePackage': PACKAGE, 'androidUseCustomKeystore': False},
                       mainSourceSHA256=before, mainInputsUnchanged=True)
    except Exception:
        # Preserve partial copied evidence. No automatic recursive cleanup.
        raise
    finally:
        (candidate / 'Preparation.json').write_text(json.dumps(outcome, indent=2) + '\n', encoding='utf-8')
    return {'status': outcome['status'], 'receipt': str(candidate / 'Preparation.json'), 'project': str(project), 'buildPerformed': False, 'networkContacted': False}


def recover(source: Path, tag: str, expected_marker_sha256: str):
    """Explicit exact-hash recovery only; no recursive removal or source repair."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', tag or '') or not re.fullmatch(r'[a-f0-9]{64}', expected_marker_sha256 or ''):
        raise Blocked('EXPLICIT_RECOVERY_HASH_AND_TAG_REQUIRED')
    candidate = source.resolve() / '.verification-cache/Review104/Candidates' / tag
    project = candidate / 'Game'
    marker = project / '.hotr-staging104-lease.json'
    _plain(marker)
    if not marker.is_file() or sha(marker) != expected_marker_sha256:
        raise Blocked('RECOVERY_MARKER_MISMATCH_PRESERVED')
    receipt = json.loads((candidate / 'Preparation.json').read_text(encoding='utf-8'))
    proof = json.loads(marker.read_text(encoding='utf-8'))
    if receipt.get('status') != 'PREPARED_STAGING104' or receipt.get('project') != str(project) or proof.get('version') != 1 or proof.get('nonce') != receipt.get('nonce') or proof.get('payloadSHA256') != receipt.get('configSHA256'):
        raise Blocked('RECOVERY_OWNERSHIP_MISMATCH_PRESERVED')
    pid = proof.get('ownerPid')
    if type(pid) is not int or pid <= 0 or _process_alive(pid):
        raise Blocked('RECOVERY_OWNER_NOT_CONFIRMED_STOPPED')
    asset = project / RESOURCE
    folder = asset.parent
    owned = {asset: proof.get('payloadSHA256'), Path(str(asset) + '.meta'): proof.get('assetMetaSHA256'), Path(str(folder) + '.meta'): proof.get('folderMetaSHA256')}
    for path, expected in owned.items():
        _plain(path)
        if not re.fullmatch(r'[a-f0-9]{64}', expected or '') or path.exists() and (not path.is_file() or sha(path) != expected):
            raise Blocked('RECOVERY_FOREIGN_BYTES_PRESERVED')
    if folder.exists() and (not folder.is_dir() or any(path not in owned for path in folder.iterdir())):
        raise Blocked('RECOVERY_FOREIGN_FILES_PRESERVED')
    for path in owned:
        if path.exists():
            path.unlink()
    if folder.exists():
        folder.rmdir()
    marker.unlink()
    return {'status': 'RECOVERED_OWNED_STAGING_RESOURCE104', 'buildPerformed': False, 'networkContacted': False, 'settingsRestored': False}


def _process_alive(pid: int) -> bool:
    if os.name == 'nt':
        # Read-only process wait. Do not use os.kill(pid, 0) on Windows.
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            if ctypes.get_last_error() == 87:  # ERROR_INVALID_PARAMETER: absent PID
                return False
            raise Blocked('RECOVERY_OWNER_STATUS_UNAVAILABLE')
        try:
            state = kernel.WaitForSingleObject(handle, 0)
            if state not in (0, 258):
                raise Blocked('RECOVERY_OWNER_STATUS_UNAVAILABLE')
            return state == 258
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        raise Blocked('RECOVERY_OWNER_STATUS_UNAVAILABLE') from None
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=None)
    parser.add_argument('--tag')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--recover', action='store_true')
    parser.add_argument('--marker-sha256')
    args = parser.parse_args()
    path = args.config or (Path(os.environ['HOTR_STAGING104_CONFIG']) if os.environ.get('HOTR_STAGING104_CONFIG') else None)
    try:
        if args.recover:
            if not args.execute:
                raise Blocked('EXPLICIT_RECOVERY_EXECUTION_REQUIRED')
            result = recover(ROOT, args.tag, args.marker_sha256)
        else:
            result = prepare(ROOT, path, args.tag, args.execute)
    except Blocked as error:
        result = {'status': 'BLOCKED_STAGING104', 'code': str(error), 'buildPerformed': False, 'networkContacted': False}
    except Exception:
        result = {'status': 'BLOCKED_STAGING104', 'code': 'STAGING_PREPARATION_FAILED', 'buildPerformed': False, 'networkContacted': False}
    print(json.dumps(result, separators=(',', ':')))
    return 1 if result['status'].startswith('BLOCKED') else 0


if __name__ == '__main__':
    raise SystemExit(main())
