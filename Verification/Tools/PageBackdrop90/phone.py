"""Root-operated current90 UI verification on the same physical phone; no emulator fallback.

Import this module from the root operator's command. Set HOTR_PHYSICAL_SERIAL
privately; it is never written into public evidence. Device methods do not run
on import. An owner's active attempt can be inspected but cannot be stopped or
replaced by this helper.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import subprocess
import struct
import time
import zlib

ROOT = Path(__file__).resolve().parents[3]
ADB = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
PACKAGE = 'com.heartoftherain.verification'
EVIDENCE = ROOT / 'Verification/Evidence/PageBackdrop90'
LEGACY_EVIDENCE = ROOT / 'Verification/Evidence/Display88'
PRIOR_EVIDENCE = ROOT / 'Verification/Evidence/RegionalAccounts89'

def chain_path(path):
    return any(path.is_relative_to(base.resolve()) for base in (EVIDENCE, LEGACY_EVIDENCE, PRIOR_EVIDENCE))
ORIGIN87 = ROOT / 'Verification/Evidence/Physical87/20261026_e71bc9d09515/Target.json'
ORIGIN87_SHA256 = '54c827221e8a829584e1a17b5457d4ffaa85cf53087730bdc5e940d03dde772d'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def run_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(EVIDENCE.resolve()) or path == EVIDENCE.resolve():
        raise RuntimeError('Backdrop90RunOutsideEvidenceRoot')
    return path


def public_binding(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise RuntimeError('PublicBindingOutsideProject')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def origin87():
    if sha(ORIGIN87) != ORIGIN87_SHA256:
        raise RuntimeError('FrozenOwnerPhoneOriginChanged')
    return json.loads(ORIGIN87.read_text('utf-8-sig'))


def validate_upgrade_chain(target_path, *, require_installation=True):
    """Pure host validation of <=4 save-preserving updates on this owner phone.

    Historical candidate hashes are read from bound successful installation
    records. Their default APK paths may now contain newer bytes and are never
    rehashed here. Only the final current build is checked separately by callers.
    require_installation=False permits a new authorization before installation;
    every referenced predecessor still requires its completed installation.
    """
    origin = origin87()

    def read_record(path):
        if path.stat().st_size > 2 * 1024 * 1024:
            raise RuntimeError('UpgradeChainRecordTooLarge')
        return json.loads(path.read_text('utf-8-sig'))

    def resolve_binding(value):
        if set(value) != {'path', 'sha256', 'bytes'} or not isinstance(value['path'], str):
            raise RuntimeError('UpgradeChainBindingInvalid')
        relative = Path(value['path'])
        if relative.is_absolute() or '..' in relative.parts or '\\' in value['path']:
            raise RuntimeError('UpgradeChainBindingOutsideScope')
        path = (ROOT / relative).resolve()
        if not chain_path(path) or not path.is_file() or public_binding(path) != value:
            raise RuntimeError('UpgradeChainBoundRecordChanged')
        return path

    def walk(path, seen, need_installation):
        path = Path(path).resolve()
        if not chain_path(path) or path.name != 'Target.json' or path in seen or len(seen) >= 4:
            raise RuntimeError('UpgradeChainScopeCycleOrDepthInvalid')
        target = read_record(path)
        if target.get('authorization') not in ('OWNER_REQUESTED_DISPLAY_REPAIR88','OWNER_REQUESTED_REGIONAL_ACCOUNTS89','OWNER_REQUESTED_PAGE_BACKDROP90') or target.get('package') != PACKAGE:
            raise RuntimeError('UpgradeChainAuthorizationInvalid')
        if target.get('serialSHA256') != origin['serialSHA256'] or target.get('model') != origin['model']:
            raise RuntimeError('UpgradeChainOwnerPhoneMismatch')
        for field in ('baselineInstalledSHA256', 'candidateApkSHA256'):
            if not re.fullmatch('[0-9a-f]{64}', target.get(field, '')):
                raise RuntimeError('UpgradeChainApkHashInvalid')
        has_target, has_install = 'priorTarget' in target, 'priorInstallation' in target
        if has_target != has_install:
            raise RuntimeError('UpgradeChainPredecessorBindingIncomplete')
        links = []
        if has_target:
            prior_target = resolve_binding(target['priorTarget'])
            prior_install = resolve_binding(target['priorInstallation'])
            if prior_install != prior_target.parent / 'Installation.json':
                raise RuntimeError('UpgradeChainPredecessorInstallationMismatch')
            predecessor = walk(prior_target, seen | {path}, True)
            if target['baselineInstalledSHA256'] != predecessor['candidateApkSHA256']:
                raise RuntimeError('UpgradeChainApkContinuityBroken')
            depth = predecessor['depth'] + 1
            links = predecessor['links']
        else:
            if target['baselineInstalledSHA256'] != origin['apkSHA256']:
                raise RuntimeError('UpgradeChainDoesNotReachFrozenOrigin87')
            depth = 1
        if 'upgradeChainDepth' in target and target['upgradeChainDepth'] != depth:
            raise RuntimeError('UpgradeChainDeclaredDepthMismatch')
        installation, before = path.parent / 'Installation.json', path.parent / 'Install_Before.json'
        link = {'target': public_binding(path), 'installation': None, 'before': None,
                'baselineInstalledSHA256': target['baselineInstalledSHA256'], 'candidateApkSHA256': target['candidateApkSHA256']}
        if need_installation or installation.exists():
            installed, previous = read_record(installation), read_record(before)
            after = installed.get('after', {})
            if installed.get('status') != 'PASS_SAVE_PRESERVING_REPLACEMENT' or previous.get('activeAttempts') != 0 or after.get('activeAttempts') != 0:
                raise RuntimeError('UpgradeChainInstallNotPreservedAndIdle')
            if not previous.get('profiles') or not previous.get('preferences') or previous.get('profiles') != after.get('profiles') or previous.get('preferences') != after.get('preferences'):
                raise RuntimeError('UpgradeChainSavedDataChanged')
            if previous.get('installedSHA256') != target['baselineInstalledSHA256'] or after.get('installedSHA256') != target['candidateApkSHA256']:
                raise RuntimeError('UpgradeChainInstalledApkMismatch')
            link.update(installation=public_binding(installation), before=public_binding(before))
        return {'depth': depth, 'candidateApkSHA256': target['candidateApkSHA256'], 'links': links + [link]}

    result = walk(Path(target_path), set(), require_installation)
    result['origin'] = public_binding(ORIGIN87)
    return result


def validate_png(data):
    """Require complete, CRC-valid and decodable PNG bytes; pure host check."""
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('InvalidNativeOsPngSignature')
    cursor, width, height, chunks, ended = 8, None, None, 0, False
    while cursor < len(data):
        if len(data) - cursor < 12:
            raise RuntimeError('TruncatedNativeOsPngChunk')
        length = struct.unpack('>I', data[cursor:cursor + 4])[0]
        end = cursor + 12 + length
        if end > len(data):
            raise RuntimeError('TruncatedNativeOsPngChunk')
        kind = data[cursor + 4:cursor + 8]
        content = data[cursor + 8:cursor + 8 + length]
        crc = struct.unpack('>I', data[cursor + 8 + length:end])[0]
        if zlib.crc32(kind + content) & 0xffffffff != crc:
            raise RuntimeError('InvalidNativeOsPngChunkCrc')
        if chunks == 0:
            if kind != b'IHDR' or length != 13:
                raise RuntimeError('InvalidNativeOsPngHeader')
            width, height = struct.unpack('>II', content[:8])
            if not 1 <= width <= 20000 or not 1 <= height <= 20000:
                raise RuntimeError('InvalidNativeOsPngDimensions')
        chunks += 1
        cursor = end
        if kind == b'IEND':
            if length != 0 or cursor != len(data):
                raise RuntimeError('InvalidNativeOsPngEnd')
            ended = True
            break
    if not ended:
        raise RuntimeError('TruncatedNativeOsPngMissingIend')
    try:
        from PIL import Image
        with Image.open(BytesIO(data)) as picture:
            if picture.format != 'PNG' or picture.size != (width, height):
                raise RuntimeError('InvalidNativeOsPngDecodedDimensions')
            picture.verify()
        with Image.open(BytesIO(data)) as picture:
            picture.load()
    except (OSError, ValueError, SyntaxError) as error:
        raise RuntimeError('InvalidNativeOsPngDecodedImage') from error
    return width, height


class Phone:
    def __init__(self, out, *, authorize_from=None, candidate_apk=None):
        self.root = ROOT
        self.out = run_path(out)
        self.run_dir = self.out
        self.out.mkdir(parents=True, exist_ok=True)
        self.serial = os.environ['HOTR_PHYSICAL_SERIAL']
        if not re.fullmatch(r'[A-Za-z0-9]{8,64}', self.serial) or self.serial.startswith('emulator'):
            raise RuntimeError('ExplicitPhysicalUsbSelectorRequired')
        self.base = '/sdcard/Android/data/' + PACKAGE + '/files'
        self.serial_sha = hashlib.sha256(self.serial.encode()).hexdigest()
        if authorize_from is not None:
            # The explicit current user request authorizes testing the same
            # owner-connected phone. Bind its prior public hash, not its APK.
            previous_path = Path(authorize_from).resolve()
            previous = json.loads(previous_path.read_text('utf-8-sig'))
            prior_chain = None
            if previous.get('authorization') == 'OWNER_CONNECTED_PHYSICAL_PHONE87':
                if previous_path != ORIGIN87.resolve() or public_binding(previous_path)['sha256'] != ORIGIN87_SHA256:
                    raise RuntimeError('FrozenOwnerPhoneOriginChanged')
                expected_installed = previous['apkSHA256']
            elif previous.get('authorization') in ('OWNER_REQUESTED_DISPLAY_REPAIR88','OWNER_REQUESTED_REGIONAL_ACCOUNTS89','OWNER_REQUESTED_PAGE_BACKDROP90'):
                prior_chain = validate_upgrade_chain(previous_path)
                if prior_chain['depth'] >= 4:
                    raise RuntimeError('MaximumOwnerPhoneUpgradeChainReached')
                expected_installed = previous['candidateApkSHA256']
            else:
                raise RuntimeError('OwnerPhoneReferenceAuthorizationInvalid')
            if previous.get('serialSHA256') != self.serial_sha:
                raise RuntimeError('OwnerPhoneReferenceMismatch')
            self.identity(previous['model'])
            installed = self.installed_sha()
            if installed != expected_installed:
                raise RuntimeError('UnexpectedInstalledBaselinePreserveDevice')
            candidate = Path(candidate_apk).resolve()
            if not candidate.is_relative_to((ROOT / 'Unity/Builds').resolve()) or not candidate.is_file():
                raise RuntimeError('CandidateApkOutsideOwnedBuildOutputs')
            self.target = {
                'authorization': 'OWNER_REQUESTED_PAGE_BACKDROP90', 'utc': utc(),
                'deviceAlias': previous['deviceAlias'], 'serialSHA256': self.serial_sha,
                'model': previous['model'], 'manufacturer': previous.get('manufacturer'),
                'package': PACKAGE, 'baselineInstalledSHA256': installed,
                'candidateApk': candidate.relative_to(ROOT).as_posix(),
                'candidateApkSHA256': sha(candidate),
                'scope': 'Explicit same owner phone, current candidate; no emulator selection, data reset or active-attempt abandonment.'}
            if prior_chain:
                self.target.update(priorTarget=public_binding(previous_path), priorInstallation=public_binding(previous_path.parent / 'Installation.json'),
                                   upgradeChainDepth=prior_chain['depth'] + 1)
            write(self.out / 'Target.json', self.target)
        else:
            self.target = json.loads((self.out / 'Target.json').read_text('utf-8-sig'))
            if self.target.get('authorization') != 'OWNER_REQUESTED_PAGE_BACKDROP90' or self.target.get('serialSHA256') != self.serial_sha:
                raise RuntimeError('Backdrop90TargetMismatch')
            validate_upgrade_chain(self.out / 'Target.json', require_installation=False)
            self.identity(self.target['model'])
            if self.installed_sha() not in (self.target['baselineInstalledSHA256'], self.target['candidateApkSHA256']):
                raise RuntimeError('UnexpectedInstalledApkPreserveDevice')
        self.apk = ROOT / self.target['candidateApk']

    def adb(self, *args, binary=False, check=True, timeout=180):
        result = subprocess.run([str(ADB), '-s', self.serial, *map(str, args)], capture_output=True, timeout=timeout)
        if check and result.returncode:
            raise RuntimeError('PhysicalAdbFailure:' + str(args[0]))
        return result.stdout if binary else result.stdout.decode('utf-8', 'replace').strip()

    def identity(self, model):
        if self.adb('get-state') != 'device' or self.adb('shell', 'getprop', 'ro.kernel.qemu') == '1' or self.adb('shell', 'getprop', 'ro.product.model') != model:
            raise RuntimeError('AuthorizedPhysicalDeviceUnavailable')

    def exists(self, path):
        result = subprocess.run([str(ADB), '-s', self.serial, 'shell', 'test', '-e', path], capture_output=True, timeout=30)
        if result.returncode not in (0, 1):
            raise RuntimeError('PhysicalPathCheckFailed')
        return result.returncode == 0

    def installed_sha(self):
        # Retry only these read-only queries, not any installation or touch.
        # A malformed nonempty path/hash is rejected immediately; empty or
        # failed transport replies remain unknown and never select a fallback.
        category = 'InstalledApkPathQueryUnavailable'
        for attempt in range(3):
            try:
                value = self.adb('shell', 'pm', 'path', PACKAGE, timeout=30)
            except (RuntimeError, subprocess.TimeoutExpired):
                value = ''
            if value:
                path = value.removeprefix('package:')
                if not value.startswith('package:') or not path.startswith('/data/app/') or not path.endswith('/base.apk') or '\n' in path:
                    raise RuntimeError('ExpectedSingleInstalledBaseApk')
                category = 'InstalledApkHashQueryUnavailable'
                try:
                    reply = self.adb('shell', 'sha256sum', path, timeout=30)
                except (RuntimeError, subprocess.TimeoutExpired):
                    reply = ''
                if reply:
                    match = re.fullmatch(r'([0-9a-fA-F]{64})(?:[ \t]+[^\r\n]+)?', reply)
                    if not match:
                        raise RuntimeError('InvalidInstalledApkHash')
                    return match.group(1).lower()
            if attempt < 2:
                time.sleep(.5)
        raise RuntimeError(category)

    def inventory(self):
        """Read-only hashes and safe state counts; does not stop/launch gameplay."""
        hashes, summaries, active = {}, [], 0
        directory = self.base + '/Profiles'
        if self.exists(directory):
            for path in self.adb('shell', 'find', directory, '-type', 'f').splitlines():
                if not re.fullmatch(re.escape(directory) + r'/[A-Za-z0-9_./-]+', path):
                    raise RuntimeError('UnexpectedProfilePath')
                relative = path.removeprefix(self.base + '/')
                hashes[relative] = self.adb('shell', 'sha256sum', path).split()[0]
                # Nested development authorities use a different schema. Hash
                # them for preservation; only canonical player profiles own
                # ordinary attempts.
                if re.fullmatch(r'Profiles/[A-Za-z0-9_.-]+/profile\.json', relative):
                    envelope = json.loads(self.adb('exec-out', 'cat', path))
                    profile = json.loads(envelope['payload'])
                    states = [attempt['state'] for attempt in profile['attempts']]
                    if not all(state in ('Reserved', 'Started', 'Won', 'Lost', 'Interrupted', 'Cancelled', 'Released') for state in states):
                        raise RuntimeError('UnknownAttemptStatePreserveDevice')
                    count = sum(state in ('Reserved', 'Started') for state in states)
                    active += count
                    summaries.append({'profile': relative, 'revision': profile['revision'], 'activeAttempts': count,
                                      'coins': profile.get('coins'), 'lives': profile.get('lives'),
                                      'currentLevel': profile.get('currentLevel'), 'completed': profile.get('completed')})
        preferences = {}
        for name in self.adb('shell', 'run-as', PACKAGE, 'ls', 'shared_prefs').split():
            if not re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', name):
                raise RuntimeError('UnexpectedPreferencesPath')
            preferences[name] = hashlib.sha256(self.adb('exec-out', 'run-as', PACKAGE, 'cat', 'shared_prefs/' + name, binary=True)).hexdigest()
        return {'utc': utc(), 'profiles': hashes, 'preferences': preferences, 'profileSummaries': summaries,
                'activeAttempts': active, 'installedSHA256': self.installed_sha()}

    def require_idle(self):
        value = self.inventory()
        if not value['profileSummaries']:
            raise RuntimeError('PlayerProfileUnavailableNoMutation')
        if value['activeAttempts']:
            raise RuntimeError('PreserveActiveAttemptNoStopInstallOrFixture')
        # This helper cannot determine a remotely active attempt. Require a
        # separately audited workflow rather than trusting an idle local save.
        if self.exists(self.base + '/ServerReview/configuration.json'):
            raise RuntimeError('ManagedServerConfigurationNeedsSeparateAttemptAudit')
        return value

    def assert_no_active_attempt(self):
        """Compatibility guard retaining the current88 authorization model."""
        return self.require_idle()

    def snapshot(self):
        """Stable save hashes only; observation time is intentionally excluded."""
        value = self.inventory()
        return {key: value[key] for key in ('profiles', 'preferences')}

    def assert_installed(self):
        if sha(self.apk) != self.target['candidateApkSHA256'] or self.installed_sha() != self.target['candidateApkSHA256']:
            raise RuntimeError('CurrentAuthorizedCandidateRequired')

    def launch(self):
        return self.adb('shell', 'am', 'start', '-W', '-n', PACKAGE + '/com.unity3d.player.UnityPlayerActivity')

    def pending_markers(self):
        if not self.exists(self.base):
            return []
        paths = self.adb('shell', 'find', self.base, '-maxdepth', '1', '-type', 'f').splitlines()
        if len(paths) > 4096 or any(not path.startswith(self.base + '/') for path in paths):
            raise RuntimeError('UnexpectedAppRootFileInventory')
        return [path for path in paths if path.removeprefix(self.base + '/').startswith('HOTR_Run')]

    def start_marker(self, name, content):
        """Launch only explicitly audited probes; never replace another request."""
        allowed = {'HOTR_RunPageBackdrop90'}
        if name not in allowed:
            raise RuntimeError('UnapprovedDevelopmentProbeMarker')
        payload = content if isinstance(content, bytes) else str(content).encode('utf-8')
        if len(payload) > 2 * 1024 * 1024:
            raise RuntimeError('DevelopmentProbeMarkerTooLarge')
        if payload.strip() != b'observe':
            raise RuntimeError('UnexpectedDevelopmentProbeMode')
        self.assert_installed()
        self.require_idle()
        if self.pending_markers():
            raise RuntimeError('PendingDevelopmentProbeRequestPreserved')
        self.adb('shell', 'am', 'force-stop', PACKAGE)
        if self.adb('shell', 'pidof', PACKAGE, check=False):
            raise RuntimeError('AppDidNotStopBeforeMarker')
        self.require_idle()
        if self.pending_markers():
            raise RuntimeError('PendingDevelopmentProbeRequestPreserved')
        private = ROOT / '.verification-cache/PageBackdrop90/Markers' / self.out.relative_to(EVIDENCE.resolve()) / name
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(payload)
        self.adb('shell', 'mkdir', '-p', self.base)
        self.adb('push', private, self.base + '/' + name)
        started = datetime.now(timezone.utc)
        self.launch()
        return started

    def finish_probe(self):
        """Ordinary relaunch after an idle check; eight seconds is no ready SLA."""
        self.assert_installed()
        self.require_idle()
        if self.pending_markers():
            raise RuntimeError('PendingDevelopmentProbeRequestPreserved')
        self.adb('shell', 'am', 'force-stop', PACKAGE)
        if self.adb('shell', 'pidof', PACKAGE, check=False):
            raise RuntimeError('AppDidNotStopAfterProbe')
        self.require_idle()
        result = self.launch()
        time.sleep(8)
        return {'launchResult': result, 'fixedObservationWaitSeconds': 8,
                'scope': 'Ordinary relaunch requested; this wait does not assert Home readiness or startup performance.'}

    def app_log(self, name):
        """Export only this app process log, redacting selectors/credentials."""
        pid = self.adb('shell', 'pidof', PACKAGE)
        if not re.fullmatch(r'\d+', pid):
            raise RuntimeError('ExpectedOneAppProcessForScopedLog')
        body = self.adb('logcat', '-d', '--pid=' + pid, '-v', 'brief').replace(self.serial, 'physical-phone-1')
        body = re.sub(r'Bearer\s+[A-Za-z0-9_./+=-]+', 'Bearer [REDACTED]', body, flags=re.IGNORECASE)
        body = re.sub(r'-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----.*?-----END (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----', '[REDACTED PRIVATE KEY]', body, flags=re.DOTALL)
        credential = r'''(?i)(["']?\b(?:authorization|token|access[ _-]?token|refresh[ _-]?token|recovery[ _-]?code|api[ _-]?key|password|secret)\b["']?\s*[=:]\s*)(?:"[^"\r\n]*"|'[^'\r\n]*'|[^\s,;]+)'''
        body = re.sub(credential, lambda match: match.group(1) + '[REDACTED]', body)
        path = (self.out / name).resolve()
        if not path.is_relative_to(self.out) or path.suffix not in ('.txt', '.log') or path.exists():
            raise RuntimeError('FreshRunScopedAppLogRequired')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as stream:
            stream.write(body)
        return {'pid': pid, 'log': path.relative_to(self.out).as_posix(), 'sha256': sha(path),
                'selectedErrorCount': len(re.findall(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException|DllNotFoundException', body)),
                'scope': 'App-PID-scoped selected error signatures; zero signatures is not a whole-app test pass.'}

    def install(self):
        before = self.require_idle()
        candidate = ROOT / self.target['candidateApk']
        if sha(candidate) != self.target['candidateApkSHA256']:
            raise RuntimeError('AuthorizedCandidateBytesChanged')
        write(self.out / 'Install_Before.json', before)
        self.adb('shell', 'am', 'force-stop', PACKAGE)
        stopped = self.require_idle()
        if stopped['profiles'] != before['profiles'] or stopped['preferences'] != before['preferences']:
            raise RuntimeError('SaveChangedDuringStopPreserveBeforeInstall')
        result = self.adb('install', '-r', candidate)
        if result != 'Success' and not result.endswith('\nSuccess'):
            raise RuntimeError('CompatibleReplacementFailedNoDestructiveFallback')
        after = self.inventory()
        preserved = before['profiles'] == after['profiles'] and before['preferences'] == after['preferences']
        record = {'utc': utc(), 'status': 'PASS_SAVE_PRESERVING_REPLACEMENT' if preserved and after['installedSHA256'] == self.target['candidateApkSHA256'] else 'FAIL_REPLACEMENT_PRESERVATION',
                  'after': after, 'scope': 'Compatible replacement before first candidate launch; no uninstall or data clear.'}
        write(self.out / 'Installation.json', record)
        if not record['status'].startswith('PASS_'):
            raise RuntimeError('InstalledCandidateOrSavePreservationFailed')
        return record

    def capture(self, name):
        """True OS framebuffer; preserves Overlay mode and every camera rect."""
        activities = self.adb('shell', 'dumpsys', 'activity', 'activities')
        if not any(PACKAGE in line for line in activities.splitlines() if 'topResumedActivity=' in line or 'mResumedActivity:' in line):
            raise RuntimeError('CaptureOnlyOurForegroundApp')
        keyguard = self.adb('shell', 'dumpsys', 'window', 'policy').split('KeyguardServiceDelegate', 1)[-1]
        if not re.search(r'(?m)^\s*showing=false\s*$', keyguard):
            raise RuntimeError('NoLockscreenOrNotificationCapture')
        target = (self.out / name).resolve()
        if not target.is_relative_to(self.out) or target.suffix != '.png' or target.exists() or target.with_suffix('.json').exists():
            raise RuntimeError('FreshRunScopedPngRequired')
        # Do not discard stdout from a failed/timeout transport, and never
        # retry a screenshot implicitly. Preserve its exact partial bytes.
        transport_failed = False
        try:
            result = subprocess.run([str(ADB), '-s', self.serial, 'exec-out', 'screencap', '-p'], capture_output=True, timeout=180)
            data = result.stdout
            transport_failed = result.returncode != 0
        except subprocess.TimeoutExpired as error:
            data = error.stdout or b''
            transport_failed = True
        # Keep even a failed transport capture as exact raw evidence. It is not
        # accepted and receives no positive metadata until fully validated.
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
        if transport_failed:
            raise RuntimeError('NativeOsPngTransportFailedRawRetained')
        width, height = validate_png(data)
        record = {'utc': utc(), 'kind': 'ACTUAL_ANDROID_OS_FRAMEBUFFER', 'png': target.relative_to(self.out).as_posix(),
                  'sha256': sha(target), 'width': width, 'height': height, 'installedSHA256': self.installed_sha(),
                  'pngValidation': 'COMPLETE_CHUNKS_IEND_CRC_AND_DECODE',
                  'displaySize': self.adb('shell', 'wm', 'size'), 'displayDensity': self.adb('shell', 'wm', 'density'),
                  'scope': 'No RenderTexture, camera change, canvas conversion or artificial resize. Safe-area ownership requires the paired native geometry report and visual inspection.'}
        write(target.with_suffix('.json'), record)
        return record


class CapturePathPhone(Phone):
    """Use unchanged approved case algorithms that expect a PNG Path return."""
    def capture(self, name):
        super().capture(name)
        return (self.out / name).resolve()
