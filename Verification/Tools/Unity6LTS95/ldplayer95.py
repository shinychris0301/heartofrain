"""Root-only full-game LTS95 APK inspection and fresh LDPlayer installation.

Imports never contact a device. Each action needs --execute. Smoke APKs,
replacement installs, data clearing, uninstalling, owner launches/stops, videos,
provider activation and production acceptance are outside this helper.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import game95
import smoke95

ROOT = HERE.parents[2]
EVIDENCE = ROOT / 'Verification/Evidence/Unity6LTS95'
PACKAGE = 'com.heartoftherain.unity6lts95'
OWNER = 'com.heartoftherain.verification'
ANDROID = smoke95.EDITOR.parent / 'Data/PlaybackEngines/AndroidPlayer'
ADB = ANDROID / 'SDK/platform-tools/adb.exe'
CONSOLE = Path('E:/LDPlayer/LDPlayer14/ldconsole.exe')
BOOT_COMMAND = 'shell cat /proc/sys/kernel/random/boot_id'  # Fixed, never interpolated.
FIELD = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
REQUIRED_STATIC = (
    'signatureVerifies', 'zipAlignFourBytePass', 'zipCrcPass', 'elf16KiBLoadSegmentsPass',
    'storedNative16KiBAligned', 'abiArm64Only', 'packageMatchesNativeBuild', 'portraitActivity',
    'minApi26', 'targetApi36', 'developmentFlagMatches', 'sdkFreeDex', 'identityBridgePresent',
    'il2cppAndUnityLibrariesPresent', 'sourcesUnchanged', 'apkUnchanged',
)


def need(value, code):
    if not value:
        raise ValueError(code)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def utc():
    return datetime.now(timezone.utc).isoformat()


def bound(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT), 'LD95ArtifactOutsideWorkspace')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def safe_error(error):
    # Never serialize commands, subprocess output/exception text, USB selectors,
    # boot IDs, package payloads, preferences, or private profile content.
    result = {'errorType': type(error).__name__}
    if isinstance(error, (ValueError, RuntimeError)) and re.fullmatch(r'[A-Za-z0-9]{1,120}', str(error)):
        result['errorCategory'] = str(error)
    return result


def run(arguments, timeout, accepted=(0,)):
    need(1 <= timeout <= 180 and isinstance(arguments, list), 'LD95BoundedArgumentListRequired')
    result = subprocess.run([str(value) for value in arguments], capture_output=True, timeout=timeout,
                            creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    need(accepted is None or result.returncode in accepted, 'LD95OwnedCommandFailed')
    return result.stdout, result.stderr, result.returncode


def static_api():
    path = ROOT / 'Verification/Tools/Unity6Migration94/check_apk94.py'
    spec = importlib.util.spec_from_file_location('ld95_readonly_apk_primitives', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value, path


def build(path):
    # This central guard is pure read-only and checks the actual native process,
    # native report/APK, all six before/after manifest hashes and live sources.
    value = game95.validate_development_build(Path(path))
    need(value['package'] == PACKAGE and value['unity'] == smoke95.VERSION
         and value['native']['after']['targetApi'] == 36, 'LD95FullGameBuildOnly')
    return value


def manifest(badging, tree):
    api, _ = static_api()
    need("package: name='" + PACKAGE + "'" in badging, 'LD95ActualPackageMismatch')
    need("application-label:'Сердце дождя'" in badging, 'LD95RussianAppLabelRequired')
    need(re.search(r"(?m)^sdkVersion:'26'\s*$", badging) is not None
         and re.search(r"(?m)^targetSdkVersion:'36'\s*$", badging) is not None, 'LD95ExactActualAPI26And36Required')
    abi = re.search(r'(?m)^native-code:\s*(.+)$', badging)
    need(abi is not None and re.findall(r"'([^']+)'", abi.group(1)) == ['arm64-v8a'], 'LD95ARM64OnlyRequired')
    nodes = api.parse_manifest(tree)
    applications = [node for node in nodes if node['tag'] == 'application']
    need(len(applications) == 1 and api.attribute_value(applications[0]['attributes'].get('android:debuggable')) in (1, 0xffffffff)
         and 'application-debuggable' in badging, 'LD95DevelopmentAPKOnly')
    players = [node for node in nodes if node['tag'] == 'activity'
               and api.attribute_value(node['attributes'].get('android:name')) == 'com.unity3d.player.UnityPlayerActivity']
    need(len(players) == 1 and api.attribute_value(players[0]['attributes'].get('android:screenOrientation')) in (1, 'portrait')
         and "launchable-activity: name='com.unity3d.player.UnityPlayerActivity'" in badging
         and not any('GameActivity' in str(node['attributes'].get('android:name', '')) for node in nodes), 'LD95PortraitActivityRequired')
    sdk = [node for node in nodes if node['tag'] == 'uses-sdk']
    need(len(sdk) == 1 and api.attribute_value(sdk[0]['attributes'].get('android:minSdkVersion')) == 26
         and api.attribute_value(sdk[0]['attributes'].get('android:targetSdkVersion')) == 36, 'LD95ExactManifestAPIRequired')
    need(not any(word in tree for word in ('RuStorePayContentProvider', 'heartoftherain-pay', 'com.yandex.mobile.ads', 'io.appmetrica')),
         'LD95UnexpectedProviderManifest')
    return {'package': PACKAGE, 'development': True, 'minApi': 26, 'targetApi': 36,
            'activity': 'com.unity3d.player.UnityPlayerActivity', 'orientation': 'portrait', 'abi': ['arm64-v8a']}


def static_bindings(value):
    _, primitive = static_api()
    return {'buildInvocation': bound(value['invocationPath']), 'nativeReport': bound(value['nativePath']),
            'apk': bound(value['apk']), 'gameSources': bound(value['gameSources']),
            'buildValidator': bound(Path(game95.__file__)), 'staticPrimitives': bound(primitive), 'runner': bound(Path(__file__))}


def inspect(path):
    value = build(path)
    output = value['invocationPath'].parent
    receipt, raw = output / 'StaticApk95.json', output / 'AndroidStatic95'
    need(not receipt.exists() and not raw.exists(), 'LD95ExistingStaticEvidencePreserved')
    raw.mkdir()
    report = dict(schemaVersion=1, status='FAIL_LTS95_INTERNAL_FULL_GAME_APK', startedUtc=utc(),
                  package=PACKAGE, development=True, checks={}, errors=[], artifacts=[], toolExitCodes={},
                  scope='Actual SDK-free full-game development APK static inspection only. Native splash getters are configuration evidence; no startup, device/provider/backend, release-signing or performance acceptance.')
    report.update(static_bindings(value))
    api, _ = static_api()
    tools_root = ANDROID / 'SDK/build-tools/36.0.0'
    tools = {'aapt': tools_root / 'aapt.exe', 'zipalign': tools_root / 'zipalign.exe',
             'java': ANDROID / 'OpenJDK/bin/java.exe', 'apksignerJar': tools_root / 'lib/apksigner.jar'}
    try:
        need(all(item.is_file() for item in tools.values()), 'LD95MatchingReadOnlyAndroidToolsRequired')
        report['tools'] = {name: {'sha256': sha(item), 'bytes': item.stat().st_size} for name, item in tools.items()}
        def command(name, args):
            stdout, stderr, code = run(args, 180, accepted=None)
            (raw / (name + '_stdout.txt')).write_bytes(stdout)
            (raw / (name + '_stderr.txt')).write_bytes(stderr)
            report['toolExitCodes'][name] = code
            need(code == 0, 'LD95StaticToolCommandFailed')
            return stdout.decode('utf-8', 'strict')
        command('Signature', [tools['java'], '-jar', tools['apksignerJar'], 'verify', '--verbose', '--print-certs', value['apk']])
        report['checks']['signatureVerifies'] = True
        command('Zipalign', [tools['zipalign'], '-c', '-v', '4', value['apk']])
        report['checks']['zipAlignFourBytePass'] = True
        badging = command('Badging', [tools['aapt'], 'dump', 'badging', value['apk']])
        tree = command('Manifest', [tools['aapt'], 'dump', 'xmltree', value['apk'], 'AndroidManifest.xml'])
        report['manifest'] = manifest(badging, tree)
        profile = api.zip_profile(value['apk'])
        libraries = {row['file'] for row in profile['libraries']}
        need({'lib/arm64-v8a/libil2cpp.so', 'lib/arm64-v8a/libunity.so'} <= libraries, 'LD95ActualIL2CPPAndUnityLibrariesRequired')
        report['zip'] = profile
        for key in REQUIRED_STATIC:
            report['checks'][key] = True
        report['status'] = 'PASS_LTS95_INTERNAL_FULL_GAME_APK'
    except Exception as error:
        report['errors'].append(safe_error(error))
    finally:
        try:
            report['checks']['sourcesUnchanged'] = all(report.get(key) == item for key, item in static_bindings(build(path)).items())
            report['checks']['apkUnchanged'] = bound(value['apk']) == report['apk']
            need(report['checks']['sourcesUnchanged'] and report['checks']['apkUnchanged'], 'LD95BuildSourcesOrAPKChanged')
        except Exception as error:
            report['status'] = 'FAIL_LTS95_INTERNAL_FULL_GAME_APK'
            report['errors'].append(safe_error(error))
        report['artifacts'] = [bound(item) for item in sorted(raw.iterdir()) if item.is_file()]
        report['completedUtc'] = utc()
        write(receipt, report)
    return report


def validated_static(value):
    path = value['invocationPath'].parent / 'StaticApk95.json'
    report = read(path)
    need(report.get('status') == 'PASS_LTS95_INTERNAL_FULL_GAME_APK' and report.get('errors') == []
         and report.get('package') == PACKAGE and report.get('development') is True
         and report.get('toolExitCodes') == dict.fromkeys(('Signature', 'Zipalign', 'Badging', 'Manifest'), 0)
         and all(report.get('checks', {}).get(key) is True for key in REQUIRED_STATIC)
         and all(report.get(key) == item for key, item in static_bindings(value).items()), 'LD95PassedCurrentStaticProofRequired')
    expected = {name + '_' + stream + '.txt' for name in ('Signature', 'Zipalign', 'Badging', 'Manifest') for stream in ('stdout', 'stderr')}
    rows = report.get('artifacts', [])
    need(len(rows) == 8 and {Path(row['path']).name for row in rows} == expected, 'LD95EightStaticOutputsRequired')
    for row in rows:
        artifact = (ROOT / row['path']).resolve()
        need(artifact.is_relative_to(path.parent / 'AndroidStatic95') and bound(artifact) == row, 'LD95StaticOutputChanged')
    return bound(path)


def selector(environ):
    serial, index = environ.get('HOTR_LDPLAYER95_SERIAL', ''), environ.get('HOTR_LDPLAYER95_INDEX', '')
    need(re.fullmatch(r'emulator-[0-9]{4,5}', serial) is not None
         and re.fullmatch(r'(?:0|[1-9][0-9]?)', index) is not None and int(index) <= 31, 'LD95ExplicitEmulatorSelectorAndIndexRequired')
    return serial, int(index)


def console_instance(raw, index):
    rows = []
    for line in raw.splitlines():
        fields = line.split(',')
        if len(fields) >= 7 and fields[0] == str(index):
            rows.append(fields)
    need(len(rows) == 1 and rows[0][4] == '1'
         and all(re.fullmatch(r'[1-9][0-9]*', rows[0][column]) for column in (5, 6)), 'LD95RunningConsoleInstanceRequired')
    # Instance titles/raw list2 may contain user text; never publish them.
    return {'index': index, 'androidStarted': True, 'hostProcessPresent': True}


def advertised_arm64(abi_list, abi_list64):
    """Fail closed on emulator translation that is not advertised to Android.

    A bridge-library name alone is not proof that this ARM64 APK is supported.
    Both package-manager ABI properties must explicitly contain arm64-v8a.
    Actual native execution is still unproven until a separate launch test.
    """
    def parse(value):
        need(isinstance(value, str) and len(value) <= 256
             and re.fullmatch(r'[a-z0-9_-]+(?:,[a-z0-9_-]+)*', value) is not None, 'LD95ValidAdvertisedABIListsRequired')
        values = value.split(',')
        need(len(values) == len(set(values)), 'LD95DuplicateAdvertisedABIRejected')
        return values
    all_abis, wide_abis = parse(abi_list), parse(abi_list64)
    need('arm64-v8a' in all_abis and 'arm64-v8a' in wide_abis
         and set(wide_abis) <= set(all_abis), 'LD95AdvertisedARM64Required')
    return {'advertisedAbis': all_abis, 'advertised64BitAbis': wide_abis, 'arm64Advertised': True}


def package_map(raw):
    result = {}
    for line in raw.splitlines():
        match = re.fullmatch(r'package:([^\r\n]+)=([A-Za-z0-9_.]+)', line)
        need(match is not None and match[2] not in result, 'LD95PackageInventoryInvalid')
        result[match[2]] = match[1]
    need(result, 'LD95InstalledPackageInventoryRequired')
    return result


def packages_preserved(before, after):
    need(PACKAGE not in before and PACKAGE in after
         and {key: val for key, val in after.items() if key != PACKAGE} == before, 'LD95OtherInstalledPackagesChanged')


class LDPlayer:
    def __init__(self, build_path):
        self.build_path = Path(build_path).resolve()
        self.build = build(self.build_path)
        self.static = validated_static(self.build)
        self.serial, self.index = selector(os.environ)
        self.deadline = time.monotonic() + 600
        need(ADB.is_file() and CONSOLE.is_file(), 'LD95ExplicitInstalledADBAndLDConsoleRequired')

    def adb(self, *args, accepted=(0,), timeout=30):
        remaining = int(self.deadline - time.monotonic())
        need(remaining > 0, 'LD95DevicePhaseDeadline')
        return run([ADB, '-s', self.serial, *args], min(timeout, remaining), accepted)[0].decode('utf-8', 'strict').strip()

    def identity(self):
        # Do not auto-start/kill the shared ADB daemon. Root owns its lifecycle.
        try:
            with socket.create_connection(('127.0.0.1', 5037), timeout=2):
                pass
        except OSError:
            raise ValueError('LD95ExistingADBServerRequired') from None
        need(self.adb('get-state') == 'device', 'LD95ExplicitEmulatorUnavailable')
        listing = run([CONSOLE, 'list2'], 20)[0].decode('utf-8', 'replace')
        proof = console_instance(listing, self.index)
        through_console = run([CONSOLE, 'adb', '--index', str(self.index), '--command', BOOT_COMMAND], 30)[0].decode('utf-8', 'strict').strip()
        through_adb = self.adb('shell', 'cat', '/proc/sys/kernel/random/boot_id')
        need(FIELD.fullmatch(through_console) is not None and through_console == through_adb, 'LD95ConsoleADBTargetMismatch')
        api = self.adb('shell', 'getprop', 'ro.build.version.sdk')
        need(re.fullmatch(r'[0-9]{2,3}', api) is not None and int(api) >= 26, 'LD95EmulatorAPI26Required')
        # Read both explicit Android ABI lists before any installation. No
        # fallback based on a spoofed model or an unverified bridge property.
        proof.update(advertised_arm64(self.adb('shell', 'getprop', 'ro.product.cpu.abilist'),
                                     self.adb('shell', 'getprop', 'ro.product.cpu.abilist64')))
        proof.update(consoleAndADBCurrentBootMatch=True, selectorSHA256=hashlib.sha256(self.serial.encode()).hexdigest(),
                     bootSHA256=hashlib.sha256(through_adb.encode()).hexdigest(),
                     api=int(api), console=bound(CONSOLE) if CONSOLE.is_relative_to(ROOT) else {'sha256': sha(CONSOLE), 'bytes': CONSOLE.stat().st_size},
                     adbTool={'sha256': sha(ADB), 'bytes': ADB.stat().st_size})
        return proof

    def exists(self, path):
        _, _, code = run([ADB, '-s', self.serial, 'shell', 'test', '-e', path], 30, (0, 1))
        return code == 0

    def installed_paths(self, package):
        need(package in (PACKAGE, OWNER), 'LD95FixedPackageRequired')
        raw = self.adb('shell', 'pm', 'path', package, accepted=(0, 1))
        paths = []
        for line in raw.splitlines():
            need(re.fullmatch(r'package:/data/app/[A-Za-z0-9_./=+~@-]+\.apk', line) is not None, 'LD95InstalledAPKPathInvalid')
            paths.append(line.removeprefix('package:'))
        return paths

    def remote_hash(self, path, *, owner_private=False):
        args = ('exec-out', 'run-as', OWNER, 'sha256sum', path) if owner_private else ('shell', 'sha256sum', path)
        raw = self.adb(*args)
        match = re.fullmatch(r'([0-9a-fA-F]{64})\s+[^\r\n]+', raw)
        need(match is not None, 'LD95RemoteFileHashInvalid')
        return match[1].lower()

    def owner_snapshot(self):
        paths = self.installed_paths(OWNER)
        if not paths:
            return {'installed': False}
        need(not self.adb('shell', 'pidof', OWNER, accepted=(0, 1)), 'LD95OwnerRunningPreserved')
        base = '/sdcard/Android/data/' + OWNER + '/files'
        hashes, active = {}, 0
        if self.exists(base):
            found = self.adb('shell', 'find', base, '-type', 'f').splitlines()
            need(len(found) <= 4096, 'LD95OwnerInventoryBoundExceeded')
            for path in found:
                need(re.fullmatch(re.escape(base) + r'/[A-Za-z0-9_./-]+', path) is not None
                     and '..' not in path.removeprefix(base + '/').split('/'), 'LD95OwnerFilePathInvalid')
                relative = path.removeprefix(base + '/')
                need(not relative.startswith('HOTR_Run'), 'LD95OwnerPendingProbePreserved')
                hashes[hashlib.sha256(relative.encode()).hexdigest()] = self.remote_hash(path)
                # Only the canonical PlayerProfile envelope has attempts.
                # Nested authority journals may also be named profile.json;
                # they remain byte-hashed above without parsing their schema.
                if re.fullmatch(r'Profiles/[A-Za-z0-9_.-]+/profile\.json', relative):
                    envelope = json.loads(self.adb('exec-out', 'cat', path))
                    profile = json.loads(envelope['payload'])
                    need(all(item['state'] in ('Reserved', 'Started', 'Won', 'Lost', 'Interrupted', 'Cancelled', 'Released')
                             for item in profile['attempts']), 'LD95OwnerUnknownAttemptState')
                    active += sum(item['state'] in ('Started', 'Reserved') for item in profile['attempts'])
        need(active == 0, 'LD95OwnerActiveAttemptPreserved')
        # Fixed literal command; no dynamic shell content or credentials.
        state = self.adb('shell', 'run-as', OWNER, 'sh', '-c', '"if test -d shared_prefs; then echo PRESENT; else echo ABSENT; fi"')
        need(state in ('PRESENT', 'ABSENT'), 'LD95OwnerPreferencesAccessRequired')
        preferences = {}
        if state == 'PRESENT':
            for name in self.adb('shell', 'run-as', OWNER, 'ls', 'shared_prefs').split():
                need(re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', name) is not None, 'LD95OwnerPreferencePathInvalid')
                preferences[hashlib.sha256(name.encode()).hexdigest()] = self.remote_hash('shared_prefs/' + name, owner_private=True)
        return {'installed': True, 'apkHashes': sorted(self.remote_hash(path) for path in paths),
                'externalFileHashes': hashes, 'preferences': preferences, 'activeAttempts': 0, 'ownerStopped': True}

    def absent(self):
        need(not self.installed_paths(PACKAGE), 'LD95ExistingCandidatePreservedNoUpgrade')
        need(not self.exists('/sdcard/Android/data/' + PACKAGE), 'LD95ExistingCandidateExternalDataPreserved')

    def header(self):
        return dict(schemaVersion=1, package=PACKAGE, startedUtc=utc(), runner=bound(Path(__file__)),
                    buildInvocation=bound(self.build_path), nativeReport=bound(self.build['nativePath']),
                    apk=bound(self.build['apk']), staticReport=self.static, ownerMutation=False,
                    scope='Fresh separate-package LDPlayer installation only. Other packages are never stopped/launched/replaced/cleared/uninstalled. Owner stopped-profile/preferences and installed-package inventory are checked; unrelated apps private-data byte equality is not claimed. No game launch, video, gameplay/provider/backend, physical-device/performance or production acceptance.')


def device_output(path, *, fresh):
    for node in (Path(path), *Path(path).parents):
        if node.exists():
            need(not node.is_symlink() and not getattr(node.stat(), 'st_file_attributes', 0) & 0x400, 'LD95LinkedOutputRefused')
    path = Path(path).resolve()
    need(path.parent == (EVIDENCE / 'LDPlayerRuns').resolve() and re.fullmatch(r'[0-9a-f]{32}', path.name) is not None
         and (not path.exists() if fresh else path.is_dir()), 'LD95ScopedFreshDeviceOutputRequired')
    return path


def preflight(build_path, output):
    output = device_output(output, fresh=True)
    target = LDPlayer(build_path)
    record = target.header()
    record['identity'] = target.identity()
    target.absent()
    record['ownerBefore'] = target.owner_snapshot()
    record['packagesBefore'] = package_map(target.adb('shell', 'pm', 'list', 'packages', '-f'))
    need(PACKAGE not in record['packagesBefore'], 'LD95CandidateMustBeAbsent')
    record.update(status='PASS_READ_ONLY_LDPLAYER95_FULL_GAME_PREFLIGHT', completedUtc=utc())
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'Preflight.json', record)
    return record


def install(build_path, output):
    output = device_output(output, fresh=False)
    need(not (output / 'Installation.json').exists() and not (output / 'InstallAuthorization.json').exists(), 'LD95PreviousInstallEvidencePreserved')
    previous = read(output / 'Preflight.json')
    target = LDPlayer(build_path)
    record = target.header()
    need(previous.get('status') == 'PASS_READ_ONLY_LDPLAYER95_FULL_GAME_PREFLIGHT'
         and all(previous.get(key) == record[key] for key in ('apk', 'nativeReport', 'buildInvocation', 'staticReport', 'runner')), 'LD95MatchingCurrentPreflightRequired')
    record['identity'] = target.identity()
    need(record['identity'] == previous['identity'], 'LD95TargetChangedSincePreflight')
    target.absent()
    before = target.owner_snapshot()
    packages_before = package_map(target.adb('shell', 'pm', 'list', 'packages', '-f'))
    need(before == previous['ownerBefore'] and packages_before == previous['packagesBefore'], 'LD95OwnerOrPackagesChangedSincePreflight')
    record['ownerBefore'] = before
    record['packagesBefore'] = packages_before
    write(output / 'InstallAuthorization.json', record)
    try:
        result = target.adb('install', target.build['apk'], timeout=180)
        need(result == 'Success' or result.endswith('\nSuccess'), 'LD95FreshInstallFailed')
        paths = target.installed_paths(PACKAGE)
        need(len(paths) == 1 and target.remote_hash(paths[0]) == record['apk']['sha256'], 'LD95InstalledFullGameAPKHashMismatch')
        record['packagesAfter'] = package_map(target.adb('shell', 'pm', 'list', 'packages', '-f'))
        packages_preserved(packages_before, record['packagesAfter'])
        record['ownerAfter'] = target.owner_snapshot()
        need(record['ownerAfter'] == before, 'LD95OwnerSaveOrPreferencesChanged')
        need(not target.adb('shell', 'pidof', PACKAGE, accepted=(0, 1)), 'LD95CandidateUnexpectedlyStarted')
        need(validated_static(build(build_path)) == record['staticReport'], 'LD95BuildChangedDuringInstall')
        record.update(status='PASS_FRESH_FULL_GAME_LDPLAYER95_INSTALL', ownerDataUnchanged=True,
                      otherInstalledPackagesUnchanged=True, gameAutomaticallyLaunched=False, installResult='Success')
    except Exception as error:
        record.update(status='FAIL_FULL_GAME_LDPLAYER95_INSTALL', **safe_error(error))
    finally:
        try:
            record['ownerFinal'] = target.owner_snapshot()
            need(record['ownerFinal'] == before, 'LD95OwnerChangedAtExit')
            record['ownerPreservedAtExit'] = True
        except Exception as error:
            record.update(status='FAIL_FULL_GAME_LDPLAYER95_INSTALL', finalGuard=safe_error(error))
        record['completedUtc'] = utc()
        write(output / 'Installation.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'preflight', 'install'))
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--build', required=True, type=Path, help='Actual full-game GameRuns/<UUID>/Invocation.json')
    parser.add_argument('--out', type=Path, help='Fresh/preflight-bound LDPlayerRuns/<UUID> directory; device actions only')
    args = parser.parse_args()
    if not args.execute or os.name != 'nt':
        parser.error('Explicit root Windows execution required; imports/host tests do not contact devices')
    if (args.action == 'inspect') == (args.out is not None):
        parser.error('inspect takes no --out; preflight/install require --out')
    if args.out is not None and not args.out.is_absolute():
        parser.error('--out must be an absolute scoped LDPlayerRuns directory')
    try:
        result = inspect(args.build) if args.action == 'inspect' else globals()[args.action](args.build, args.out)
        print(json.dumps({'status': result['status'], 'package': PACKAGE, 'ownerMutation': False}))
        return 0 if result['status'].startswith('PASS_') else 1
    except Exception as error:
        print(json.dumps({'status': 'FAIL_ROOT_LDPLAYER95_ACTION', **safe_error(error), 'ownerMutation': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
