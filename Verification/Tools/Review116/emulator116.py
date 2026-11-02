"""Isolated Review116 emulator inventory and explicit opt-in regression.

Selects one emulator transport only; never selects or queries a physical phone.
All current mutations target the explicitly authorized fresh review116r2 package;
the earlier review116 package and its archived evidence are preserved read-only.
No existing package is stopped, cleared, uninstalled, reinstalled or modified.
Raw serials, settings and command output stay in the ignored cache.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import zipfile
from check_apk116 import source_qualification, APPROVED_CANONICAL_SHA256

ROOT = Path(__file__).resolve().parents[3]
ADB = Path(r'C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe')
PACKAGE = 'com.heartoftherain.review116r2'
ADB_PORT = 5041
ACTIVITY = PACKAGE + '/com.unity3d.player.UnityPlayerActivity'
BASE = '/sdcard/Android/data/' + PACKAGE + '/files'
MARKER = 'HOTR_RunRegression'
PUBLIC = ROOT / 'Verification/Evidence/Review116/Emulator'
PRIVATE = ROOT / '.verification-cache/Review116/Emulator'
EMULATOR_TRANSPORT_SHA256 = '04ab3fc382bfb33ea4fbc120f5172ecfc4aed71652e00977064492ca0f65a017'
LAUNCH_PROFILE_VALIDATOR = None
DIAGNOSTIC_2022_OPT_IN = False


def need(value, code):
    if not value:
        raise RuntimeError(code)


def require_launch_profile(context):
    if callable(LAUNCH_PROFILE_VALIDATOR):
        return LAUNCH_PROFILE_VALIDATOR(context)
    need(DIAGNOSTIC_2022_OPT_IN, 'Branded2022RequiresExplicitDiagnosticOptIn')
    return dict(status='EXPLICIT_UNITY2022_DIAGNOSTIC_ONLY', finalUserVisibleProfile=False)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def bind(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT), 'Review116BoundPathOutsideWorkspace')
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=digest(path.read_bytes()), bytes=path.stat().st_size)


class Target:
    def __init__(self, private):
        self.private = private
        self.counter = 0
        result = subprocess.run([str(ADB), '-P', str(ADB_PORT), 'devices', '-l'], capture_output=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW)
        need(result.returncode == 0, 'AdbInventoryUnavailable')
        (private / 'TransportInventory.private').write_bytes(result.stdout)
        rows = [line.split() for line in result.stdout.decode('utf-8').splitlines()
            if line and not line.startswith('List of devices')]
        emulators = [row[0] for row in rows if len(row) >= 2 and row[0].startswith('emulator-') and row[1] == 'device']
        need(len(emulators) == 1, 'ExactlyOneAuthorizedEmulatorRequired')
        self.serial = emulators[0]
        need(digest(self.serial.encode()) == EMULATOR_TRANSPORT_SHA256, 'ExplicitlyAuthorizedEmulatorTransportRequired')
        self.other_transports = len(rows) - 1
        need(self.other_transports == 0, 'PrivateBridgeMustExposeOnlyAuthorizedEmulator')
        need(self.query('get-state').strip() == 'device', 'AuthorizedEmulatorTransportRequired')
        model = self.query('shell', 'getprop', 'ro.product.model').strip()
        qemu = self.query('shell', 'getprop', 'ro.kernel.qemu').strip()
        boot_qemu = self.query('shell', 'getprop', 'ro.boot.qemu').strip()
        need(qemu == '1' or boot_qemu == '1', 'EmulatorIdentityRequired')
        self.identity = dict(serialSha256=digest(self.serial.encode()), model=model,
            manufacturer=self.query('shell', 'getprop', 'ro.product.manufacturer').strip(),
            android=self.query('shell', 'getprop', 'ro.build.version.release').strip(),
            sdk=self.query('shell', 'getprop', 'ro.build.version.sdk').strip(),
            abi=self.query('shell', 'getprop', 'ro.product.cpu.abilist').strip(),
            nativeBridge=self.query('shell', 'getprop', 'ro.dalvik.vm.native.bridge').strip(),
            bootIdSha256=digest(self.query('shell', 'cat', '/proc/sys/kernel/random/boot_id').encode()))
        self.identity['displaySize'] = self.query('shell', 'wm', 'size')
        self.identity['displayDensity'] = self.query('shell', 'wm', 'density')

    def query(self, *args, accepted=(0,), binary=False, timeout=90):
        self.counter += 1
        result = subprocess.run([str(ADB), '-P', str(ADB_PORT), '-s', self.serial, *map(str, args)],
            capture_output=True, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
        stem = str(self.counter).zfill(5)
        (self.private / (stem + '.stdout.private')).write_bytes(result.stdout)
        (self.private / (stem + '.stderr.private')).write_bytes(result.stderr)
        need(result.returncode in accepted, 'EmulatorAdbCommandFailed')
        return result.stdout if binary else result.stdout.decode('utf-8', errors='strict').strip()

    def exists(self, path):
        need(path.startswith(BASE + '/') or path == BASE, 'OnlyOwnPackagePathAllowed')
        result = self.query('shell', 'sh', '-c', '"test -e ' + path + ' && echo PRESENT || echo ABSENT"')
        need(result in ('PRESENT', 'ABSENT'), 'EmulatorExistenceReadbackInvalid')
        return result == 'PRESENT'

    def exact_hash(self, path):
        for attempt in range(3):
            output = self.query('exec-out', 'sha256sum', path)
            match = re.fullmatch(r'([a-fA-F0-9]{64})\s+(.+)', output)
            if match and match[2] == path:
                return match[1].lower()
            time.sleep(.25)
        need(False, 'ExactDeviceFileHashReadbackRequired')

    def packages(self):
        lines = sorted(self.query('shell', 'pm', 'list', 'packages', '-f').splitlines())
        need(lines and all(line.startswith('package:') and '=' in line for line in lines), 'AndroidPackageInventoryInvalid')
        return {line.rsplit('=', 1)[1]: digest(line.encode()) for line in lines}

    def files(self, package):
        need(re.fullmatch(r'com\.heartoftherain\.[a-z0-9]+', package), 'OwnedGamePackageSyntaxRequired')
        uid = self.query('shell', 'run-as', package, 'id', '-u')
        need(re.fullmatch('[0-9]+', uid) and int(uid) >= 10000,
             'ExistingDebugPackageReadOnlyHashAccessRequired')
        external = '/sdcard/Android/data/' + package + '/files'
        roots = ['/data/user/0/' + package + '/files', '/data/user/0/' + package + '/shared_prefs',
                 '/data/user/0/' + package + '/no_backup']
        # Hash-only reads. Missing directories are explicit; permission errors
        # are retained privately and prevent claiming complete profile evidence.
        script = 'for p in ' + ' '.join(roots) + '; do if [ -d "$p" ]; then find "$p" -type f -exec sha256sum {} \\;; else echo ABSENT:$p; fi; done'
        output = self.query('shell', 'run-as ' + package + " sh -c '" + script + "'")
        self.query('shell', 'ls', '-ld', '/sdcard/Android/data')
        external_script = 'if [ -d ' + external + ' ]; then find ' + external + ' -type f -exec sha256sum {} \\;; else echo ABSENT:' + external + '; fi'
        output += '\n' + self.query('shell', external_script)
        entries = {}
        absent = []
        for line in output.splitlines():
            if line.startswith('ABSENT:'):
                absent.append(line.removeprefix('ABSENT:'))
                continue
            match = re.fullmatch(r'([a-fA-F0-9]{64})\s+(.+)', line)
            need(match is not None, 'ExistingProfileHashInventoryInvalid')
            entries[match[2]] = match[1].lower()
        return dict(files=dict(sorted(entries.items())), absent=sorted(absent),
            method='Internal files via package-scoped run-as; external files via authorized adb shell. External run-as access is not evidence of absence.')

    def snapshot(self, previous=None):
        packages = self.packages()
        games = {}
        for package in sorted(packages):
            if package.startswith('com.heartoftherain.') and package != PACKAGE:
                path = self.query('shell', 'pm', 'path', package)
                apk_paths = [line.removeprefix('package:') for line in path.splitlines() if line.startswith('package:')]
                need(apk_paths, 'ExistingGameApkPathRequired')
                apks = []
                for apk in apk_paths:
                    value = self.query('shell', 'sha256sum', apk)
                    match = re.fullmatch(r'([a-fA-F0-9]{64})\s+.+', value)
                    need(match is not None, 'ExistingApkHashRequired')
                    apks.append(match[1].lower())
                games[package] = dict(apkSha256=sorted(apks), data=self.files(package),
                    pids=self.query('shell', 'pidof', package, accepted=(0, 1)))
                supplemented = []
                known = (previous or {}).get('games', {}).get(package, {}).get('data', {}).get('files', {})
                for name in sorted(set(known) - set(games[package]['data']['files'])):
                    if name.startswith('/sdcard/Android/data/' + package + '/files/'):
                        value = self.query('shell', 'sha256sum', name, accepted=(0, 1))
                    else:
                        need(name.startswith('/data/user/0/' + package + '/'), 'KnownExistingFileScopeRequired')
                        value = self.query('shell', 'run-as', package, 'sha256sum', name, accepted=(0, 1))
                    match = re.fullmatch(r'([a-fA-F0-9]{64})\s+(.+)', value)
                    if match and match[2] == name:
                        games[package]['data']['files'][name] = match[1].lower()
                        supplemented.append(name)
                games[package]['directHashSupplementForInventoryOmissions'] = supplemented
                games[package]['idleProof'] = self.idle(package, games[package]['data'])
        settings = {}
        for namespace in ('system', 'secure', 'global'):
            value = '\n'.join(sorted(self.query('shell', 'settings', 'list', namespace).splitlines()))
            settings[namespace] = digest(value.encode())
        activity = self.query('shell', 'dumpsys', 'activity', 'activities')
        foreground = re.findall(r'(?:topResumedActivity=|ResumedActivity:)[^\r\n]*?\s([A-Za-z0-9._]+/[A-Za-z0-9._]+)', activity)
        self.query('shell', 'dumpsys', 'window', 'windows')
        return dict(utc=utc(), identity=self.identity, packages=packages, games=games,
            settingsSha256=settings, otherTransportCount=self.other_transports,
            foregroundActivity=sorted(set(foreground)),
            ownPackagePresent=PACKAGE in packages,
            scope='Read-only emulator package installation references, existing game APK/profile/preferences file hashes and Android settings hashes. No physical phone command.')

    def idle(self, package, inventory):
        base = '/sdcard/Android/data/' + package + '/files/'
        profiles = []
        reasons = []
        for name, expected in inventory['files'].items():
            if not name.startswith(base):
                continue
            relative = name.removeprefix(base)
            if relative.split('/')[0].startswith('HOTR_'):
                reasons.append('ExistingFixtureMarker')
            allowed_roots = {'Profiles', 'Regression', 'il2cpp'}
            if package in (PACKAGE, 'com.heartoftherain.review116'):
                allowed_roots.add('RegressionHistory116')
            if relative.split('/')[0] not in allowed_roots:
                reasons.append('UnknownExternalStateRequiresReview')
            if relative.endswith('.tmp'):
                reasons.append('UnsettledTemporaryFile')
            if relative.startswith('ServerReview/'):
                reasons.append('ManagedAuthorityRequiresSeparateIdleProof')
            if re.fullmatch(r'Profiles/[A-Za-z0-9_.-]+/(?:DailyGiftDevelopmentAuthority/)?profile\.json', relative):
                raw = self.query('exec-out', 'cat', name, binary=True)
                need(digest(raw) == expected, 'ExistingProfileChangedDuringIdleRead')
                envelope = json.loads(raw)
                need(envelope.get('format') == 1 and digest(envelope['payload'].encode('utf-8')) == envelope.get('sha256'),
                     'ExistingCanonicalProfileChecksumRequired')
                model = json.loads(envelope['payload'])
                need(model.get('schemaVersion') == 1 and isinstance(model.get('attempts'), list),
                     'ExistingKnownProfileSchemaRequired')
                attempts = model['attempts']
                known = {'Reserved', 'Started', 'Won', 'Lost', 'Interrupted', 'Cancelled', 'Released'}
                need(all(a.get('state') in known for a in attempts), 'ExistingUnknownAttemptStatePreserved')
                active = sum(a['state'] in ('Reserved', 'Started') for a in attempts)
                pending = sum(bool((a.get('continuation') or {}).get('pending')) for a in attempts)
                pending += int(bool(model.get('hasPendingGift')))
                if active:
                    reasons.append('ActiveOrdinaryAttempt')
                if pending:
                    reasons.append('PendingOrdinaryOperation')
                profiles.append(dict(path=relative, sha256=expected, activeAttempts=active, pendingOperations=pending))
        if not any(re.fullmatch(r'Profiles/[A-Za-z0-9_.-]+/profile\.json', row['path']) for row in profiles):
            reasons.append('CanonicalOrdinaryProfileMissing')
        return dict(idle=not reasons, profiles=profiles, reasons=sorted(set(reasons)),
            scope='Read-only checksum-verified ordinary durable attempt/continuation/gift state and existing fixture-marker inventory. No mutation or settlement.')


def directories(name):
    need(re.fullmatch(r'[A-Za-z0-9_-]{1,60}', name), 'FreshScopedEvidenceNameRequired')
    public, private = PUBLIC / name, PRIVATE / name
    need(not public.exists() and not private.exists(), 'PreservePreviousEmulatorEvidence')
    public.mkdir(parents=True)
    private.mkdir(parents=True)
    return public, private


def compare_existing(before, after):
    differences = []
    if before['identity'] != after['identity']:
        differences.append('EmulatorIdentityChanged')
    for package, value in before['packages'].items():
        if package != PACKAGE and after['packages'].get(package) != value:
            differences.append('ExistingPackageChanged:' + package)
    unexpected = set(after['packages']) - set(before['packages']) - {PACKAGE}
    if unexpected:
        differences.append('UnexpectedNewPackages')
    for package, value in before['games'].items():
        current = after['games'].get(package, {})
        if current.get('apkSha256') != value['apkSha256']:
            differences.append('ExistingGameApkChanged:' + package)
        if current.get('data') != value['data']:
            differences.append('ExistingGameDataChanged:' + package)
    return dict(passExistingPackageAndGameData=not differences, differences=differences,
        androidSettingsIdentical=before['settingsSha256'] == after['settingsSha256'],
        existingPidsIdentical={p: after['games'].get(p, {}).get('pids') == v['pids'] for p, v in before['games'].items()},
        scope='Package references and existing game APK/profile/preferences hashes; Android settings and existing PIDs reported separately to distinguish OS lifecycle changes.')


def inventory(name):
    public, private = directories(name)
    target = Target(private)
    result = target.snapshot()
    result['status'] = 'PASS_READ_ONLY_EMULATOR116_INVENTORY'
    write(public / 'Inventory.json', result)
    print(json.dumps(dict(status=result['status'], model=result['identity']['model'],
        packages=len(result['packages']), existingGamePackages=list(result['games']),
        newReview116PackagePresent=result['ownPackagePresent'], report=(public / 'Inventory.json').relative_to(ROOT).as_posix())))


def validate_static(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT / 'Verification/Evidence/Review116/Android'), 'Review116StaticProofRequired')
    proof = read(path)
    snapshot = proof.get('immutableSnapshotMode') is True and proof.get('snapshotAcceptedForSeparateEmulator') is True
    need(proof.get('status') == 'PASS_STATIC_APK116' and (proof.get('currentPassingBuild') is True or snapshot)
         and proof.get('development') is True and proof.get('package') == PACKAGE,
         'CurrentPassingDevelopmentBuildAndStaticChecksRequired')
    apk = ROOT / proof['apk']['path']
    need(apk.is_file() and bind(apk) == proof['apk'], 'ExactStaticallyCheckedApkRequired')
    invocation = ROOT / proof['invocation']['path']
    need(bind(invocation) == proof['invocation'], 'UnchangedNativeBuildInvocationRequired')
    canonical = proof.get('canonicalSnapshot')
    if canonical:
        need(canonical.get('candidateMatchesApprovedCut') is True and
             canonical['manifest']['sha256'] == APPROVED_CANONICAL_SHA256 and
             bind(ROOT / canonical['manifest']['path']) == canonical['manifest'],
             'ApprovedCanonicalManifestMustRemainPinned')
    if snapshot:
        qualification = source_qualification(read(invocation))
        need(read(invocation).get('exitCode') == 0 and qualification['immutableCandidateInputs']
             and (bool(canonical) or qualification['onlyKnown115UiDifferences']),
             'SameImmutableApprovedSnapshotOrKnownUiOnlyDriftRequired')
        proof['workingTreeAtDeviceGate'] = qualification
        if canonical:
            proof['canonicalSnapshot']['authorization'] = 'User explicitly chose: Commit the tested snapshot and leave newer edits uncommitted.'
            proof['canonicalSnapshot']['workingTreeDeltasInformational'] = True
        return apk, proof
    need(read(invocation).get('status') == 'PASS_ANDROID116_INVOCATION', 'PassingCurrentNativeBuildRequired')
    frozen = read(invocation).get('mainAfter', {}).get('files', {})
    current_paths = {p.relative_to(ROOT).as_posix() for part in ('Assets', 'Packages', 'ProjectSettings')
        for p in (ROOT / 'Unity' / part).rglob('*') if p.is_file()}
    need(current_paths == set(frozen), 'NoNewMainInputsSinceBuildRequired')
    need(frozen and all((ROOT / name).is_file() and digest((ROOT / name).read_bytes()) == row.get('sha256')
        for name, row in frozen.items()), 'BuildInputsMustStillMatchCurrentMainBeforeInstall')
    return apk, proof


def install(name, static, no_streaming=False, internal=False):
    apk, proof = validate_static(static)
    launch_profile = require_launch_profile(proof)
    public, private = directories(name)
    target = Target(private)
    before = target.snapshot()
    write(public / 'Before.json', before)
    need(not before['ownPackagePresent'], 'FreshReview116PackageMustBeAbsent')
    need(all(row['idleProof']['idle'] for row in before['games'].values()),
         'ExistingOrdinaryProfilesMustBeIdleBeforeInstall')
    command = ['install'] + (['--no-streaming'] if no_streaming else []) + (['-f'] if internal else []) + [str(apk)]
    output = target.query(*command, timeout=300)
    need(re.search(r'(?m)^Success\s*$', output) and 'Failure' not in output, 'NewReview116InstallFailed')
    after = target.snapshot(before)
    checks = compare_existing(before, after)
    installed_path = target.query('shell', 'pm', 'path', PACKAGE)
    need(installed_path.startswith('package:') and '\n' not in installed_path, 'New116SingleApkRequired')
    installed = target.exact_hash(installed_path.removeprefix('package:'))
    need(installed == proof['apk']['sha256'], 'InstalledExact116ApkRequired')
    write(public / 'After.json', after)
    result = dict(status='PASS_NEW_REVIEW116_INSTALL' if checks['passExistingPackageAndGameData'] else 'FAIL_REVIEW116_EXISTING_STATE_CHANGED',
        utc=utc(), package=PACKAGE, apk=proof['apk'], staticProof=bind(static),
        immutableSnapshotMode=proof.get('immutableSnapshotMode') is True,
        currentPassingBuild=proof.get('currentPassingBuild') is True,
        untestedCurrentUiPaths=proof.get('sourceQualification', {}).get('currentMainDifferencePaths', []),
        canonicalSnapshot=proof.get('canonicalSnapshot'),
        workingTreeAtDeviceGate=proof.get('workingTreeAtDeviceGate'),
        noStreamingTransport=no_streaming, ownedPackageInternalInstall=internal,
        launchProfileEligibility=launch_profile,
        identity=target.identity, checks=checks, before=bind(public / 'Before.json'), after=bind(public / 'After.json'),
        scope='Fresh installation of the separate development package on an emulator only. Existing packages were never stopped or reinstalled. No physical-phone operation.')
    write(public / 'Installation.json', result)
    print(json.dumps(dict(status=result['status'], checks=checks,
        report=(public / 'Installation.json').relative_to(ROOT).as_posix())))
    need(checks['passExistingPackageAndGameData'], 'ExistingStateChangedAfterNewPackageInstall')


def reconcile_install(name, static, baseline):
    """Reconcile this harness's known streamed-install false-negative read-only."""
    apk, proof = validate_static(static)
    baseline = Path(baseline).resolve()
    need(baseline.is_relative_to(PUBLIC) and baseline.name == 'Before.json', 'OwnedBeforeInstallSnapshotRequired')
    before = read(baseline)
    need(before.get('ownPackagePresent') is False, 'NewPackageWasAbsentBeforeInstall')
    old_private = PRIVATE / baseline.parent.name
    outputs = [p for p in old_private.glob('*.stdout.private') if
        re.search(rb'(?m)^Success\s*$', p.read_bytes()) and b'Performing Streamed Install' in p.read_bytes()]
    need(len(outputs) == 1, 'OriginalActualAdbSuccessReadbackRequired')
    public, private = directories(name)
    target = Target(private)
    need(target.identity['serialSha256'] == before['identity']['serialSha256'] and
         target.identity['bootIdSha256'] == before['identity']['bootIdSha256'], 'SameInstallTargetAndBootRequired')
    after = target.snapshot(before)
    need(after['ownPackagePresent'], 'OwnInstalledPackageRequiredForReadOnlyReconciliation')
    installed_path = target.query('shell', 'pm', 'path', PACKAGE)
    need(installed_path.startswith('package:') and '\n' not in installed_path, 'OwnSingleInstalledApkRequired')
    installed = target.exact_hash(installed_path.removeprefix('package:'))
    need(installed == proof['apk']['sha256'], 'ReconciledInstalledApkMustMatchStaticProof')
    checks = compare_existing(before, after)
    # Earlier source revision predates display identity additions only; require
    # all originally observed identity fields, then bind the richer identity.
    if checks['differences'] == ['EmulatorIdentityChanged'] and all(after['identity'].get(k) == v for k, v in before['identity'].items()):
        checks['differences'] = []
        checks['passExistingPackageAndGameData'] = True
    write(public / 'After.json', after)
    result = dict(status='PASS_NEW_REVIEW116_INSTALL' if checks['passExistingPackageAndGameData'] else 'FAIL_RECONCILED_INSTALL_EXISTING_STATE',
        utc=utc(), package=PACKAGE, apk=proof['apk'], staticProof=bind(static),
        immutableSnapshotMode=proof.get('immutableSnapshotMode') is True,
        currentPassingBuild=proof.get('currentPassingBuild') is True,
        untestedCurrentUiPaths=proof.get('sourceQualification', {}).get('currentMainDifferencePaths', []),
        canonicalSnapshot=proof.get('canonicalSnapshot'),
        workingTreeAtDeviceGate=proof.get('workingTreeAtDeviceGate'),
        identity=target.identity, checks=checks, before=bind(baseline), after=bind(public / 'After.json'),
        runner=bind(Path(__file__)), originalActualAdbSuccess=bind(outputs[0]),
        reconciledAfterHarnessFalseNegative=True,
        scope='Read-only reconciliation of the prior actual successful new116 install. No install/reinstall, launch, lifecycle, settings or data mutation in this operation. Original wrapper false-negative retained separately.')
    write(public / 'Installation.json', result)
    print(json.dumps(dict(status=result['status'], checks=checks,
        report=(public / 'Installation.json').relative_to(ROOT).as_posix())), flush=True)
    need(checks['passExistingPackageAndGameData'], 'ExistingStateChangedDuringInstallReconciliation')


def regression(name, installation, timeout):
    need(60 <= timeout <= 2100, 'BoundedRegressionTimeoutRequired')
    installation = Path(installation).resolve()
    need(installation.is_relative_to(PUBLIC), 'Own116InstallationReceiptRequired')
    installed = read(installation)
    need(installed.get('status') == 'PASS_NEW_REVIEW116_INSTALL' and installed.get('package') == PACKAGE,
         'PassingOwn116InstallationRequired')
    require_launch_profile(installed)
    public, private = directories(name)
    target = Target(private)
    need(target.identity == installed['identity'], 'SameBootAndEmulatorRequired')
    before = target.snapshot()
    write(public / 'Before.json', before)
    need(before['ownPackagePresent'], 'OwnReview116PackageMustExist')
    need(all(row['idleProof']['idle'] for row in before['games'].values()),
         'ExistingOrdinaryProfilesMustBeIdleBeforeLaunch')
    own_apk_path = target.query('shell', 'pm', 'path', PACKAGE)
    need(own_apk_path.startswith('package:') and '\n' not in own_apk_path, 'OwnInstalledSingleApkRequiredBeforeRun')
    own_apk_hash = target.exact_hash(own_apk_path.removeprefix('package:'))
    need(own_apk_hash == installed['apk']['sha256'], 'OwnInstalledApkChangedBeforeRegression')
    need(not target.exists(BASE + '/' + MARKER) and not target.exists(BASE + '/Regression'),
         'PreserveExistingMarkersAndRegressionOutputs')
    own_running = target.query('shell', 'pidof', PACKAGE, accepted=(0, 1))
    if own_running:
        own_prelaunch = target.files(PACKAGE)
        own_idle = target.idle(PACKAGE, own_prelaunch)
        need(own_idle['idle'], 'NewlyOwnedPackageMustBeIdleBeforeStop')
        write(public / 'OwnedPrelaunchIdle.json', dict(utc=utc(), idle=own_idle, files=own_prelaunch,
            scope='Previously running new116 package only; no existing package lifecycle command.'))
        target.query('shell', 'am', 'force-stop', PACKAGE)
        need(not target.query('shell', 'pidof', PACKAGE, accepted=(0, 1)), 'NewOwnedIdleProcessDidNotStop')
    initial_launch = target.query('shell', 'am', 'start', '-W', '-n', ACTIVITY, timeout=120)
    need(re.search(r'(?m)^Status:\s*ok\s*$', initial_launch), 'OwnOrdinaryStartupFailed')
    time.sleep(8)
    ordinary_screen = target.query('exec-out', 'screencap', '-p', binary=True)
    need(ordinary_screen.startswith(b'\x89PNG\r\n\x1a\n'), 'OwnOrdinaryOsScreenshotRequired')
    (public / 'Ordinary_Before_OS.png').write_bytes(ordinary_screen)
    target.query('shell', 'am', 'force-stop', PACKAGE)
    need(not target.query('shell', 'pidof', PACKAGE, accepted=(0, 1)), 'OwnOrdinaryProcessDidNotStop')
    own_before = target.files(PACKAGE)
    write(public / 'OwnOrdinaryBefore.json', own_before)
    payload = private / MARKER
    payload.write_bytes(b'run\n')
    target.query('shell', 'mkdir', '-p', BASE)
    target.query('push', str(payload), BASE + '/' + MARKER)
    need(target.query('exec-out', 'cat', BASE + '/' + MARKER, binary=True) == payload.read_bytes(),
         'ExactOwnRegressionMarkerRequired')
    started = utc()
    launch = target.query('shell', 'am', 'start', '-W', '-n', ACTIVITY, timeout=120)
    need(re.search(r'(?m)^Status:\s*ok\s*$', launch), 'OwnPackageLaunchFailed')
    write(public / 'Started.json', dict(status='RUNNING_OWN_EMULATOR116_REGRESSION', utc=started,
        installation=bind(installation), package=PACKAGE, identity=target.identity,
        runner=bind(Path(__file__)),
        staticQualificationHelper=bind(Path(source_qualification.__code__.co_filename)),
        markerSha256=digest(payload.read_bytes()), scope='Transient memory fixtures in new emulator package only.'))
    deadline, progress = time.monotonic() + timeout, 0
    final = None
    while time.monotonic() < deadline:
        raw = target.query('exec-out', 'cat', BASE + '/Regression/Regression.json', accepted=(0, 1), binary=True)
        try:
            report = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            report = {}
        if report and time.monotonic() >= progress:
            print(json.dumps({key: report.get(key) for key in ('status', 'checks', 'boards', 'actions', 'clips')}), flush=True)
            progress = time.monotonic() + 30
        if report.get('status') and report['status'] != 'RUNNING':
            final = report
            (private / 'Regression.json').write_bytes(raw)
            write(public / 'Regression.json', report)
            break
        time.sleep(5)
    need(final is not None, 'Emulator116RegressionDeadline')
    need(not target.exists(BASE + '/' + MARKER), 'OwnRegressionMarkerWasNotConsumed')
    selected = ['Gameplay_English_HUD.png', 'Home_Reward_L50.png', 'Home_en.png', 'Teams_0_en.png']
    for group in (('Power_4_Effect_0.png', 'Power_4_Effect_1.png', 'Power_4_Effect_2.png'),
                  ('Stacked_Stones_Diagonal_0.png', 'Stacked_Stones_Diagonal_1.png', 'Stacked_Stones_Diagonal_2.png')):
        selected.append(next((item for item in group if item in final.get('frames', [])), ''))
    inventory = []
    for filename in selected:
        if not filename or filename not in final.get('frames', []):
            continue
        body = target.query('exec-out', 'cat', BASE + '/Regression/' + filename, binary=True)
        need(body.startswith(b'\x89PNG\r\n\x1a\n'), 'NativeSelectedPngRequired')
        (public / filename).write_bytes(body)
        inventory.append(bind(public / filename))
    write(public / 'SelectedCaptures.json', dict(captures=inventory,
        scope='Native offscreen rendered captures selected from the actual emulator regression; visual review is recorded separately.'))
    screen = target.query('exec-out', 'screencap', '-p', binary=True)
    need(screen.startswith(b'\x89PNG\r\n\x1a\n'), 'ActualEmulatorOsScreenshotRequired')
    (public / 'Final_OS.png').write_bytes(screen)
    # Only the new owned package is stopped to leave the transient suite. No
    # existing package receives a lifecycle mutation or marker operation.
    target.query('shell', 'am', 'force-stop', PACKAGE)
    own_after = target.files(PACKAGE)
    write(public / 'OwnOrdinaryAfter.json', own_after)
    # Model/prefs and this run's archived evidence must remain unchanged. The
    # new disposable package may populate its own IL2CPP extraction cache.
    # Existing user-package cache files remain protected by snapshot(before).
    def ordinary(value):
        return {k: v for k, v in value['files'].items() if
            '/Profiles/' in k or '/shared_prefs/' in k or '/no_backup/' in k or '/RegressionHistory116/' in k}
    own_ordinary_preserved = ordinary(own_before) == ordinary(own_after)
    after = target.snapshot(before)
    checks = compare_existing(before, after)
    write(public / 'After.json', after)
    native_pass = final.get('status') == 'PASS_NATIVE_REGRESSION' and not final.get('failures')
    native_pass = native_pass and final.get('boards') == 50 and final.get('actions') == 408 and final.get('clips') == 354
    result = dict(status='PASS_EMULATOR116_REGRESSION' if native_pass and checks['passExistingPackageAndGameData'] and own_ordinary_preserved else 'FAIL_EMULATOR116_REGRESSION',
        utc=utc(), startedUtc=started, package=PACKAGE, identity=target.identity,
        immutableSnapshotMode=installed.get('immutableSnapshotMode') is True,
        currentPassingBuild=installed.get('currentPassingBuild') is True,
        untestedCurrentUiPaths=installed.get('untestedCurrentUiPaths', []),
        canonicalSnapshot=installed.get('canonicalSnapshot'),
        workingTreeAtInstallation=installed.get('workingTreeAtDeviceGate'),
        nativeStatus=final.get('status'), checks=final.get('checks'), boards=final.get('boards'),
        actions=final.get('actions'), clips=final.get('clips'), failures=final.get('failures'),
        existingState=checks, ownOrdinaryFilesPreserved=own_ordinary_preserved,
        ownOrdinaryScope='Durable profile/preferences/no-backup files and preserved owned RegressionHistory116; new disposable package runtime extraction caches are separate.',
        ownRuntimeCacheFileCounts=dict(before=sum('/il2cpp/' in k for k in own_before['files']),
            after=sum('/il2cpp/' in k for k in own_after['files'])),
        finalOwnedPackageStopped=True, selectedCaptures=len(inventory),
        runner=bind(Path(__file__)),
        scope='Actual Android emulator ARM-translation execution of opt-in transient native fixtures and programmatic app actions. No manual campaign, physical-device, performance, service/provider or production certification.')
    write(public / 'Result.json', result)
    print(json.dumps(result), flush=True)
    need(result['status'] == 'PASS_EMULATOR116_REGRESSION', 'ActualEmulatorRegressionFailed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('inventory', 'install', 'reconcile-install', 'regression'))
    parser.add_argument('--name', required=True)
    parser.add_argument('--static', type=Path)
    parser.add_argument('--installation', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--timeout', type=int, default=2100)
    parser.add_argument('--no-streaming', action='store_true')
    parser.add_argument('--internal', action='store_true')
    parser.add_argument('--diagnostic-2022', action='store_true', help='Explicit diagnostic only; never final user-visible no-splash approval.')
    args = parser.parse_args()
    global DIAGNOSTIC_2022_OPT_IN
    DIAGNOSTIC_2022_OPT_IN = args.diagnostic_2022
    if args.operation == 'inventory':
        inventory(args.name)
    elif args.operation == 'install':
        need(args.static is not None, 'StaticProofRequired')
        install(args.name, args.static, args.no_streaming, args.internal)
    elif args.operation == 'reconcile-install':
        need(args.static is not None and args.baseline is not None, 'StaticProofAndOriginalBaselineRequired')
        reconcile_install(args.name, args.static, args.baseline)
    else:
        need(args.installation is not None, 'InstallationReceiptRequired')
        regression(args.name, args.installation, args.timeout)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        message = str(error)
        print(json.dumps(dict(status='BLOCKED_EMULATOR116_OPERATION', errorType=type(error).__name__,
            code=message if re.fullmatch('[A-Za-z0-9]{1,100}', message) else 'SeePrivateEvidence')), flush=True)
        raise SystemExit(1)
