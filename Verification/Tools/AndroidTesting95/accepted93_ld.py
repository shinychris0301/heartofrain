"""Root-only accepted Unity2022 checkpoint93 LDPlayer update and optional launch.

No native build, LTS migration acceptance, physical-phone operation, data reset,
uninstall, force-stop, downgrade flag, gesture, reward action or public raw log.
Every action requires --execute and the already authorized private Set03 target.
"""
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
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/AndroidTesting95/Runs'
PRIVATE = ROOT / '.verification-cache/AndroidTesting95/Runs'
SELECTOR = ROOT / '.verification-cache/AndroidTesting95/Discovery/Set03/Selector.json'
APK = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
APK_SHA = 'e4bb5d8cf99ebcbb805d14e8f167c0e245bcef585903bdcc69724a9748b422ac'
APK_BYTES = 331223027
PACKAGE = 'com.heartoftherain.verification'
SUMMARY = ROOT / 'Verification/Evidence/Review93/Summary.json'
SUMMARY_SHA = 'e6b761f46bd57a6d7b0c3c69a0cf00a3411fad4c700ce31e44598199a9432cfd'
ADB = Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe')
CONSOLE = Path('E:/LDPlayer/LDPlayer14/ldconsole.exe')
BASE = '/sdcard/Android/data/' + PACKAGE + '/files'
ACTIVITY = PACKAGE + '/com.unity3d.player.UnityPlayerActivity'
BOOT_COMMAND = 'shell cat /proc/sys/kernel/random/boot_id'
GUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
ERRORS = r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException|DllNotFoundException'


def need(value, code):
    if not value:
        raise ValueError(code)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def bound(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT), 'Accepted93ArtifactOutsideWorkspace')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def utc():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def write_raw(path, value):
    with Path(path).open('xb') as stream:
        stream.write(value)


def safe(error):
    result = {'errorType': type(error).__name__}
    if isinstance(error, (ValueError, RuntimeError)) and re.fullmatch(r'[A-Za-z0-9]{1,120}', str(error)):
        result['errorCategory'] = str(error)
    return result


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def accepted_proof():
    need(sha(SUMMARY) == SUMMARY_SHA and sha(APK) == APK_SHA and APK.stat().st_size == APK_BYTES, 'Accepted93FixedSummaryOrAPKChanged')
    collector = module('accepted93_readonly_collector', 'Verification/Tools/Review93/collect_review93.py')
    summary = read(SUMMARY)
    current = collector.freeze()
    need(current['inputCount'] == 5407 and summary.get('unityInputCount') == 5407
         and summary.get('status') == collector.STATUS, 'Accepted93SourceCountOrStatusChanged')
    collector.verify_binding(summary['sourceManifest'])
    collector.sources_match(ROOT / summary['sourceManifest']['path'], current)
    builds = collector.build_proof(ROOT / summary['proofArguments']['builds'], current)
    static = collector.static_proof(ROOT / summary['proofArguments']['android'], builds)
    development = [row for row in builds['apks'] if row.get('development') is True]
    need(len(development) == 1 and {key: development[0][key] for key in ('path', 'sha256', 'bytes')} == bound(APK), 'Accepted93DevelopmentArtifactMismatch')
    return {'summary': bound(SUMMARY), 'sourceManifest': summary['sourceManifest'], 'unityInputs': 5407,
            'builds': builds, 'static': static, 'apk': bound(APK), 'collector': bound(Path(collector.__file__)),
            'metadata': {'unity': '2022.3.62f3', 'package': PACKAGE, 'versionCode': 1, 'minApi': 22,
                         'targetApi': 36, 'abi': ['arm64-v8a'], 'development': True,
                         'unitySplashStillEnabled': True, 'productionRelease': False}}


def load_selector():
    value = read(SELECTOR)
    need(type(value.get('index')) is int and value['index'] == 0 and value.get('package') == PACKAGE
         and re.fullmatch(r'emulator-[0-9]{4,5}', value.get('serial', '')) is not None
         and GUID.fullmatch(value.get('bootID', '')) is not None
         and Path(value.get('adb', '')).resolve() == ADB.resolve()
         and Path(value.get('console', '')).resolve() == CONSOLE.resolve(), 'Accepted93ExactPrivateLDTargetRequired')
    need(ADB.is_file() and CONSOLE.is_file(), 'Accepted93InstalledReadOnlyTransportRequired')
    return value


def command(arguments, timeout=30, accepted=(0,)):
    need(isinstance(arguments, list) and 1 <= timeout <= 180, 'Accepted93BoundedArgumentsRequired')
    result = subprocess.run([str(x) for x in arguments], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    need(accepted is None or result.returncode in accepted, 'Accepted93OwnedCommandFailed')
    return result.stdout, result.stderr, result.returncode


def parse_packages(raw):
    result = {}
    for line in raw.splitlines():
        match = re.fullmatch(r'package:([^\r\n]+)=([A-Za-z0-9_.]+)', line)
        need(match is not None and match[2] not in result, 'Accepted93PackageInventoryInvalid')
        result[match[2]] = match[1]
    need(PACKAGE in result, 'Accepted93OwnerPackageRequired')
    return result


def unchanged_other_packages(before, after):
    need(set(before) == set(after) and {key: val for key, val in before.items() if key != PACKAGE}
         == {key: val for key, val in after.items() if key != PACKAGE}, 'Accepted93OtherPackagesChanged')


def canonical_attempts(relative, raw):
    if re.fullmatch(r'Profiles/[A-Za-z0-9_.-]+/profile\.json', relative) is None:
        return None
    value = json.loads(json.loads(raw)['payload'])
    need(all(item['state'] in ('Reserved', 'Started', 'Won', 'Lost', 'Interrupted', 'Cancelled', 'Released')
             for item in value['attempts']), 'Accepted93UnknownAttemptState')
    need(not any(item['state'] in ('Reserved', 'Started') for item in value['attempts']), 'Accepted93ActiveAttemptPreserved')
    return {key: value.get(key) for key in ('coins', 'lives', 'currentLevel', 'completed', 'revision')}


def snapshot_unchanged(expected, actual):
    need(expected == actual, 'Accepted93InstalledHashOrSaveChangedSincePreflight')


class Target:
    def __init__(self):
        self.selector = load_selector()
        self.deadline = time.monotonic() + 600

    def adb(self, *args, accepted=(0,), timeout=30, binary=False):
        remaining = int(self.deadline - time.monotonic())
        need(remaining > 0, 'Accepted93DevicePhaseDeadline')
        raw = command([ADB, '-s', self.selector['serial'], *args], min(timeout, remaining), accepted)[0]
        return raw if binary else raw.decode('utf-8', 'strict').strip()

    def identity(self):
        try:
            with socket.create_connection(('127.0.0.1', 5037), timeout=2):
                pass
        except OSError:
            raise ValueError('Accepted93ExistingADBServerRequired') from None
        need(self.adb('get-state') == 'device', 'Accepted93AuthorizedEmulatorUnavailable')
        listing = command([CONSOLE, 'list2'], 20)[0].decode('utf-8', 'replace')
        rows = [line.split(',') for line in listing.splitlines() if line.startswith('0,')]
        need(len(rows) == 1 and len(rows[0]) >= 7 and rows[0][4] == '1'
             and all(re.fullmatch(r'[1-9][0-9]*', rows[0][i]) for i in (5, 6)), 'Accepted93LDIndexZeroMustBeRunning')
        console_boot = command([CONSOLE, 'adb', '--index', '0', '--command', BOOT_COMMAND], 30)[0].decode('ascii').strip()
        adb_boot = self.adb('shell', 'cat', '/proc/sys/kernel/random/boot_id')
        need(console_boot == adb_boot == self.selector['bootID'], 'Accepted93PrivateBootLinkChanged')
        abis = self.adb('shell', 'getprop', 'ro.product.cpu.abilist').split(',')
        wide = self.adb('shell', 'getprop', 'ro.product.cpu.abilist64').split(',')
        need('arm64-v8a' in abis and 'arm64-v8a' in wide, 'Accepted93AdvertisedARM64Required')
        api = self.adb('shell', 'getprop', 'ro.build.version.sdk')
        need(re.fullmatch(r'[0-9]{2,3}', api) is not None and int(api) >= 22, 'Accepted93MinimumAndroidAPIRequired')
        return {'privateSelector': bound(SELECTOR), 'index': 0, 'sameLDConsoleAndADBBoot': True,
                'selectorSHA256': hashlib.sha256(self.selector['serial'].encode()).hexdigest(),
                'advertisedAbis': abis, 'advertised64BitAbis': wide, 'androidApi': int(api),
                'adbSHA256': sha(ADB), 'consoleSHA256': sha(CONSOLE)}

    def exists(self, path):
        _, _, code = command([ADB, '-s', self.selector['serial'], 'shell', 'test', '-e', path], 30, (0, 1))
        return code == 0

    def file_hash(self, path, private=False):
        args = ('exec-out', 'run-as', PACKAGE, 'sha256sum', path) if private else ('shell', 'sha256sum', path)
        raw = self.adb(*args)
        match = re.fullmatch(r'([a-fA-F0-9]{64})\s+[^\r\n]+', raw)
        need(match is not None, 'Accepted93RemoteHashInvalid')
        return match[1].lower()

    def snapshot(self, stopped=True):
        pid = self.adb('shell', 'pidof', PACKAGE, accepted=(0, 1))
        need(not stopped or not pid, 'Accepted93RunningOwnerPreserved')
        paths = self.adb('shell', 'pm', 'path', PACKAGE).splitlines()
        need(len(paths) == 1 and re.fullmatch(r'package:/data/app/[A-Za-z0-9_./=+~@-]+\.apk', paths[0]) is not None, 'Accepted93OneInstalledOwnerAPKRequired')
        installed_hash = self.file_hash(paths[0].removeprefix('package:'))
        package_dump = self.adb('shell', 'dumpsys', 'package', PACKAGE)
        versions = re.findall(r'(?m)^\s*versionCode=([0-9]+)\b', package_dump)
        need(len(versions) == 1 and int(versions[0]) <= 1, 'Accepted93NoDowngradeAllowed')
        external, profiles = {}, {}
        need(self.exists(BASE), 'Accepted93ExistingOwnerSaveRootRequired')
        files = self.adb('shell', 'find', BASE, '-type', 'f').splitlines()
        need(len(files) <= 4096, 'Accepted93OwnerInventoryBoundExceeded')
        for path in files:
            need(re.fullmatch(re.escape(BASE) + r'/[A-Za-z0-9_./-]+', path) is not None, 'Accepted93OwnerFilePathInvalid')
            relative = path.removeprefix(BASE + '/')
            need('..' not in relative.split('/') and not ('/' not in relative and relative.startswith('HOTR_')), 'Accepted93PendingMarkerPreserved')
            name_hash = hashlib.sha256(relative.encode()).hexdigest()
            external[name_hash] = self.file_hash(path)
            if re.fullmatch(r'Profiles/[A-Za-z0-9_.-]+/profile\.json', relative):
                profiles[name_hash] = canonical_attempts(relative, self.adb('exec-out', 'cat', path))
        need(profiles, 'Accepted93CanonicalOwnerProfileRequired')
        state = self.adb('shell', 'run-as', PACKAGE, 'sh', '-c', '"if test -d shared_prefs; then echo PRESENT; else echo ABSENT; fi"')
        need(state in ('PRESENT', 'ABSENT'), 'Accepted93OwnerPreferencesAccessRequired')
        preferences = {}
        if state == 'PRESENT':
            for name in self.adb('shell', 'run-as', PACKAGE, 'ls', 'shared_prefs').split():
                need(re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', name) is not None, 'Accepted93PreferenceNameInvalid')
                preferences[hashlib.sha256(name.encode()).hexdigest()] = self.file_hash('shared_prefs/' + name, True)
        return {'installedSHA256': installed_hash, 'externalFileHashes': external, 'preferences': preferences,
                'profiles': profiles, 'activeAttempts': 0}

    def packages(self):
        return parse_packages(self.adb('shell', 'pm', 'list', 'packages', '-f'))


def output_paths(output, fresh):
    original = Path(output)
    for path in (original, *original.parents):
        if path.exists():
            need(not path.is_symlink() and not getattr(path.stat(), 'st_file_attributes', 0) & 0x400, 'Accepted93LinkedOutputRefused')
    output = original.resolve()
    need(output.parent == OUT.resolve() and re.fullmatch(r'[a-f0-9]{32}', output.name) is not None
         and (not output.exists() if fresh else output.is_dir()), 'Accepted93ScopedFreshRunRequired')
    for path in (output, *output.parents):
        if path.exists():
            need(not path.is_symlink() and not getattr(path.stat(), 'st_file_attributes', 0) & 0x400, 'Accepted93LinkedOutputRefused')
    private = PRIVATE / output.name
    for path in (private, *private.parents):
        if path.exists():
            need(not path.is_symlink() and not getattr(path.stat(), 'st_file_attributes', 0) & 0x400, 'Accepted93LinkedPrivateOutputRefused')
    need(not private.exists() if fresh else private.is_dir(), 'Accepted93ScopedPrivateRunRequired')
    if fresh:
        output.mkdir(parents=True, exist_ok=False)
        private.mkdir(parents=True, exist_ok=False)
    return output, private


def base_report(action):
    return {'schemaVersion': 1, 'action': action, 'startedUtc': utc(), 'runner': bound(Path(__file__)),
            'package': PACKAGE, 'scope': 'Existing accepted checkpoint93 Unity2022 development APK on authorized LDPlayer index0 only. Save-preserving update/ordinary observation; no new build, Unity6 splash removal, provider/backend/whole-game/performance or production acceptance.'}


def preflight(output):
    output, _ = output_paths(output, True)
    report = base_report('preflight')
    try:
        report['proof'] = accepted_proof()  # Must succeed before ANY device command.
        target = Target()
        report['identity'] = target.identity()
        report['before'] = target.snapshot()
        report['packagesBefore'] = target.packages()
        report.update(status='PASS_READ_ONLY_ACCEPTED93_LD_PREFLIGHT95', sourceAndProofsCurrent=True)
    except Exception as error:
        report.update(status='FAIL_ACCEPTED93_LD_PREFLIGHT95', **safe(error))
    report['completedUtc'] = utc()
    write(output / 'Preflight.json', report)
    return report


def current_context(output, phase):
    output, private = output_paths(output, False)
    need(not (output / (phase + '.json')).exists() and not (output / (phase + 'Authorization.json')).exists(), 'Accepted93ExistingPhaseEvidencePreserved')
    previous = read(output / 'Preflight.json')
    need(previous.get('status') == 'PASS_READ_ONLY_ACCEPTED93_LD_PREFLIGHT95'
         and previous.get('runner') == bound(Path(__file__)), 'Accepted93PassedCurrentPreflightRequired')
    proof = accepted_proof()
    need(proof == previous['proof'], 'Accepted93ProofChangedAfterPreflight')
    target = Target()
    need(target.identity() == previous['identity'], 'Accepted93LDTargetChangedSincePreflight')
    return output, private, previous, proof, target


def validate_update_receipt(output):
    """Read-only current-source/accepted-artifact/receipt checks; no device call."""
    output, _ = output_paths(output, False)
    previous, installed = read(output / 'Preflight.json'), read(output / 'Update.json')
    proof = accepted_proof()
    runner = bound(Path(__file__))
    need(previous.get('status') == 'PASS_READ_ONLY_ACCEPTED93_LD_PREFLIGHT95'
         and installed.get('status') == 'PASS_ACCEPTED93_LD_UPDATE95_SAVES_PRESERVED'
         and previous.get('runner') == installed.get('runner') == runner
         and previous.get('proof') == installed.get('proof') == proof
         and installed.get('preflight') == bound(output / 'Preflight.json')
         and previous.get('identity') == installed.get('identity')
         and installed.get('saveAndPreferencesUnchanged') is True
         and installed.get('otherPackagesUnchanged') is True
         and installed.get('savePreservedAtExit') is True, 'Accepted93BoundCurrentUpdateRequired')
    snapshot_unchanged(previous['before'], installed['before'])
    expected = {**installed['before'], 'installedSHA256': APK_SHA}
    snapshot_unchanged(expected, installed['after'])
    snapshot_unchanged(expected, installed['final'])
    need(previous['packagesBefore'] == installed['packagesBefore'], 'Accepted93UpdatePackageChainChanged')
    unchanged_other_packages(installed['packagesBefore'], installed['packagesAfter'])
    need(installed.get('packagesFinal') == installed['packagesAfter'], 'Accepted93UpdateFinalPackageChainChanged')
    return {'proof': proof, 'identity': previous['identity'], 'before': installed['before'],
            'after': installed['after'], 'packagesAfter': installed['packagesAfter'],
            'preflight': bound(output / 'Preflight.json'), 'update': bound(output / 'Update.json')}


def update(output):
    output, private, previous, proof, target = current_context(output, 'Update')
    report = base_report('update')
    report.update(proof=proof, identity=previous['identity'], preflight=bound(output / 'Preflight.json'))
    before, packages = target.snapshot(), target.packages()
    snapshot_unchanged(previous['before'], before)
    need(packages == previous['packagesBefore'], 'Accepted93PackageInventoryChangedSincePreflight')
    report.update(before=before, packagesBefore=packages)
    write(output / 'UpdateAuthorization.json', report)
    try:
        need(accepted_proof() == proof, 'Accepted93SourceChangedBeforeMutation')
        if before['installedSHA256'] == APK_SHA:
            report['installAttempted'] = False
        else:
            # Only -r is authorized. No -d/-g, uninstall, clear or force-stop.
            stdout, stderr, code = command([ADB, '-s', target.selector['serial'], 'install', '-r', APK], 180, None)
            write_raw(private / 'Install_stdout.txt', stdout)
            write_raw(private / 'Install_stderr.txt', stderr)
            report.update(installAttempted=True, installExitCode=code)
            need(code == 0 and stdout.decode('utf-8').strip().endswith('Success'), 'Accepted93SavePreservingInstallFailed')
        after = target.snapshot()
        need(after['installedSHA256'] == APK_SHA, 'Accepted93InstalledTargetHashMismatch')
        snapshot_unchanged({**before, 'installedSHA256': APK_SHA}, after)
        after_packages = target.packages()
        unchanged_other_packages(packages, after_packages)
        report.update(after=after, packagesAfter=after_packages, status='PASS_ACCEPTED93_LD_UPDATE95_SAVES_PRESERVED',
                      saveAndPreferencesUnchanged=True, otherPackagesUnchanged=True)
    except Exception as error:
        report.update(status='FAIL_ACCEPTED93_LD_UPDATE95', **safe(error))
    finally:
        try:
            final = target.snapshot()
            report['final'] = final
            final_packages = target.packages()
            report['packagesFinal'] = final_packages
            unchanged_other_packages(packages, final_packages)
            if 'packagesAfter' in report:
                need(final_packages == report['packagesAfter'], 'Accepted93PackagesChangedAtExit')
            need({k: v for k, v in final.items() if k != 'installedSHA256'}
                 == {k: v for k, v in before.items() if k != 'installedSHA256'}, 'Accepted93SaveChangedAtExit')
            need(accepted_proof() == proof, 'Accepted93SourceChangedAtExit')
            report['savePreservedAtExit'] = True
        except Exception as error:
            report.update(status='FAIL_ACCEPTED93_LD_UPDATE95', finalGuard=safe(error))
        report['completedUtc'] = utc()
        write(output / 'Update.json', report)
    return report


def launch(output, observe=8):
    need(type(observe) is int and 2 <= observe <= 20, 'Accepted93BoundedObservationRequired')
    output, private, previous, proof, target = current_context(output, 'Launch')
    installed = read(output / 'Update.json')
    need(installed.get('status') == 'PASS_ACCEPTED93_LD_UPDATE95_SAVES_PRESERVED'
         and installed.get('proof') == proof and installed.get('savePreservedAtExit') is True, 'Accepted93CompletedUpdateRequired')
    validate_update_receipt(output)
    before, packages = target.snapshot(), target.packages()
    snapshot_unchanged(installed['after'], before)
    need(packages == installed['packagesAfter'], 'Accepted93PackageInventoryChangedBeforeLaunch')
    report = base_report('launch')
    report.update(proof=proof, update=bound(output / 'Update.json'), before=before, packagesBefore=packages,
                  observationSeconds=observe, timingScope='Fixed host observation window, not app delay or startup SLA.')
    write(output / 'LaunchAuthorization.json', report)
    try:
        stdout, stderr, code = command([ADB, '-s', target.selector['serial'], 'shell', 'am', 'start', '-W', '-n', ACTIVITY], 60, None)
        write_raw(private / 'Launch_stdout.txt', stdout)
        write_raw(private / 'Launch_stderr.txt', stderr)
        need(code == 0 and re.search(r'(?m)^Status:\s*ok\s*$', stdout.decode('utf-8')) is not None, 'Accepted93OrdinaryLaunchFailed')
        time.sleep(observe)
        pid = target.adb('shell', 'pidof', PACKAGE)
        need(re.fullmatch(r'[1-9][0-9]*', pid) is not None, 'Accepted93SingleAppPIDRequired')
        activities = target.adb('shell', 'dumpsys', 'activity', 'activities')
        need(any(PACKAGE + '/' in line for line in activities.splitlines() if 'topResumedActivity=' in line or 'mResumedActivity:' in line), 'Accepted93ForegroundAppRequired')
        policy = target.adb('shell', 'dumpsys', 'window', 'policy').split('KeyguardServiceDelegate', 1)[-1]
        need(re.search(r'(?m)^\s*showing=false\s*$', policy) is not None
             and re.search(r'(?m)^\s*showing=true\s*$', policy) is None, 'Accepted93UnlockedAppRequired')
        raw_png = target.adb('exec-out', 'screencap', '-p', binary=True)
        png = private / 'Launch_OS.png'
        with png.open('xb') as stream:
            stream.write(raw_png)
        png_reader = module('accepted93_png_reader_only', 'Verification/Tools/Review93/phone.py')
        width, height = png_reader.validate_png(raw_png)  # Pure parser; no Phone is instantiated.
        raw_log = target.adb('logcat', '-d', '--pid=' + pid, '-v', 'brief', binary=True)
        log = private / 'Runtime.log'
        with log.open('xb') as stream:
            stream.write(raw_log)
        count = len(re.findall(ERRORS, raw_log.decode('utf-8', 'replace')))
        after = target.snapshot(stopped=False)
        after_packages = target.packages()
        unchanged_other_packages(packages, after_packages)
        need(accepted_proof() == proof, 'Accepted93SourceChangedDuringLaunch')
        report.update(status='RECORDED_ACCEPTED93_LD_LAUNCH95_REQUIRES_REVIEW', pid=int(pid),
                      actualAndroidOSCapture=bound(png), width=width, height=height, privatePIDLog=bound(log),
                      selectedRuntimeErrorCount=count, after=after, ordinaryStartupDataChanged=after != before,
                      packagesAfter=after_packages, otherPackagesUnchanged=True, rootVisualReviewCompleted=False)
    except Exception as error:
        report.update(status='FAIL_ACCEPTED93_LD_LAUNCH95', **safe(error))
    try:
        need(accepted_proof() == proof, 'Accepted93SourceChangedAtLaunchExit')
        report['sourceProofsUnchangedAtExit'] = True
    except Exception as error:
        report.update(status='FAIL_ACCEPTED93_LD_LAUNCH95', finalGuard=safe(error))
    report['completedUtc'] = utc()
    write(output / 'Launch.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'update', 'launch'))
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--observe-seconds', type=int, default=8)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt' or not args.out.is_absolute():
        parser.error('Explicit root Windows execution and absolute scoped output required')
    try:
        report = launch(args.out, args.observe_seconds) if args.action == 'launch' else globals()[args.action](args.out)
        print(json.dumps({'status': report['status'], 'package': PACKAGE, 'unity6MigrationAccepted': False}))
        return 1 if report['status'].startswith('FAIL_') else 0
    except Exception as error:
        print(json.dumps({'status': 'FAIL_ROOT_ACCEPTED93_LD_ACTION95', **safe(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
