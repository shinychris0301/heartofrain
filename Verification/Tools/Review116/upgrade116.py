"""Archive owned116 fixture output or upgrade only the owned116 test package.

No operation targets an existing user package, profile, setting or physical phone.
Each mutation requires the exact earlier installation and native output receipt.
"""
import argparse
import json
from pathlib import Path
import re
import time

import emulator116 as device


def own_installation(path):
    path = Path(path).resolve()
    device.need(path.is_relative_to(device.PUBLIC), 'Own116InstallationReceiptRequired')
    value = device.read(path)
    device.need(value.get('status') in ('PASS_NEW_REVIEW116_INSTALL', 'PASS_OWN_REVIEW116_UPGRADE')
        and value.get('package') == device.PACKAGE, 'PassingOwn116InstallationRequired')
    return value


def installed_hash(target):
    path = target.query('shell', 'pm', 'path', device.PACKAGE)
    device.need(path.startswith('package:') and '\n' not in path, 'Own116SingleInstalledApkRequired')
    for attempt in range(3):
        output = target.query('exec-out', 'sha256sum', path.removeprefix('package:'))
        match = re.fullmatch(r'([a-fA-F0-9]{64})\s+(.+)', output)
        if match:
            return match[1].lower()
        time.sleep(.25)
    device.need(False, 'Own116InstalledHashRequired')


def prove_before(target, installation):
    device.need(target.identity == installation['identity'], 'SameAuthorized116TargetAndBootRequired')
    before = target.snapshot()
    device.need(before['ownPackagePresent'] and installed_hash(target) == installation['apk']['sha256'],
        'SameOwned116InstalledArtifactRequired')
    device.need(all(row['idleProof']['idle'] for row in before['games'].values()),
        'ExistingOrdinaryProfilesMustRemainIdle')
    own = target.files(device.PACKAGE)
    device.need(target.idle(device.PACKAGE, own)['idle'], 'Own116OrdinaryProfileMustRemainIdle')
    device.need(not target.exists(device.BASE + '/' + device.MARKER), 'NoPendingOwnRegressionMarkerAllowed')
    return before, own


def persistent(value):
    return {path: digest for path, digest in value['files'].items()
            if '/Profiles/' in path or '/shared_prefs/' in path or '/no_backup/' in path}


def archive(args):
    installation = own_installation(args.installation)
    regression = Path(args.regression).resolve()
    device.need(regression.is_relative_to(device.PUBLIC) and regression.name == 'Result.json',
        'Own116NativeRegressionReceiptRequired')
    native = device.read(regression)
    device.need(native.get('package') == device.PACKAGE and native.get('nativeStatus') in
        ('PASS_NATIVE_REGRESSION', 'FAIL_NATIVE_REGRESSION'), 'ActualOwn116RegressionRequired')
    original = device.PRIVATE / regression.parent.name / 'Regression.json'
    device.need(original.is_file(), 'ExactRetainedNativeRegressionBytesRequired')
    public, private = device.directories(args.name)
    target = device.Target(private)
    before, own_before = prove_before(target, installation)
    device.write(public / 'Before.json', before)
    device.need(not target.query('shell', 'pidof', device.PACKAGE, accepted=(0, 1)),
        'OwnedPackageMustBeStoppedBeforeArchive')
    source = device.BASE + '/Regression'
    destination = device.BASE + '/RegressionHistory116/' + args.name
    device.need(target.exists(source) and not target.exists(destination), 'FreshOwnedArchiveDestinationRequired')
    raw = target.query('exec-out', 'cat', source + '/Regression.json', binary=True)
    device.need(raw == original.read_bytes(), 'OwnedNativeOutputChangedBeforeArchive')
    old_files = {name.removeprefix(source + '/'): digest for name, digest in own_before['files'].items()
                 if name.startswith(source + '/')}
    device.need(old_files and 'Regression.json' in old_files, 'OwnedRegressionInventoryRequired')
    target.query('shell', 'mkdir', '-p', device.BASE + '/RegressionHistory116')
    target.query('shell', 'mv', source, destination)
    device.need(not target.exists(source) and target.exists(destination), 'OwnArchiveRenameReadbackRequired')
    own_after = target.files(device.PACKAGE)
    new_files = {name.removeprefix(destination + '/'): digest for name, digest in own_after['files'].items()
                 if name.startswith(destination + '/')}
    after = target.snapshot(before)
    checks = device.compare_existing(before, after)
    unchanged = old_files == new_files and persistent(own_before) == persistent(own_after)
    device.write(public / 'After.json', after)
    result = dict(status='PASS_OWN116_REGRESSION_ARCHIVE' if unchanged and checks['passExistingPackageAndGameData'] else 'FAIL_OWN116_ARCHIVE',
        utc=device.utc(), package=device.PACKAGE, source=source, destination=destination,
        files=len(old_files), originalNativeBytes=device.bind(original), regression=device.bind(regression),
        runner=device.bind(Path(__file__)), allOwnedOutputHashesPreserved=old_files == new_files,
        deviceHelper=device.bind(Path(device.__file__)),
        ownPersistentProfileAndPrefsUnchanged=persistent(own_before) == persistent(own_after), existingState=checks,
        scope='Reversible same-package rename of this run-owned Regression directory, preserving every output byte. No deletion, overwrite, save clear or existing-package mutation.')
    device.write(public / 'Archive.json', result)
    print(json.dumps(result), flush=True)
    device.need(result['status'].startswith('PASS_'), 'OwnedArchiveInvariantFailed')


def upgrade(args):
    previous = own_installation(args.installation)
    apk, proof = device.validate_static(args.static)
    device.require_launch_profile(proof)
    earlier_static = device.ROOT / previous['staticProof']['path']
    device.need(device.bind(earlier_static) == previous['staticProof'], 'OriginalStaticProofPreservedRequired')
    earlier = device.read(earlier_static)
    device.need(earlier.get('publicCertificateSha256') == proof.get('publicCertificateSha256'),
        'SameOwnDebugSigningCertificateRequired')
    public, private = device.directories(args.name)
    target = device.Target(private)
    before, own_before = prove_before(target, previous)
    device.write(public / 'Before.json', before)
    device.write(public / 'OwnPersistentBefore.json', persistent(own_before))
    device.need(not target.query('shell', 'pidof', device.PACKAGE, accepted=(0, 1)),
        'Own116MustBeStoppedBeforeUpgrade')
    command = ['install'] + (['--no-streaming'] if args.no_streaming else []) + ['-r']
    if args.internal:
        command.append('-f')
    command.append(str(apk))
    output = target.query(*command, timeout=300)
    device.need(re.search(r'(?m)^Success\s*$', output) and 'Failure' not in output, 'Own116UpgradeFailed')
    device.need(installed_hash(target) == proof['apk']['sha256'], 'ExactUpgraded116ApkRequired')
    own_after = target.files(device.PACKAGE)
    after = target.snapshot(before)
    checks = device.compare_existing(before, after)
    own_preserved = persistent(own_before) == persistent(own_after)
    device.write(public / 'After.json', after)
    device.write(public / 'OwnPersistentAfter.json', persistent(own_after))
    result = dict(status='PASS_OWN_REVIEW116_UPGRADE' if checks['passExistingPackageAndGameData'] and own_preserved else 'FAIL_OWN116_UPGRADE',
        utc=device.utc(), package=device.PACKAGE, apk=proof['apk'], staticProof=device.bind(args.static),
        previousInstallation=device.bind(args.installation), identity=target.identity,
        immutableSnapshotMode=proof.get('immutableSnapshotMode') is True,
        currentPassingBuild=proof.get('currentPassingBuild') is True,
        untestedCurrentUiPaths=proof.get('sourceQualification', {}).get('currentMainDifferencePaths', []),
        canonicalSnapshot=proof.get('canonicalSnapshot'),
        workingTreeAtDeviceGate=proof.get('workingTreeAtDeviceGate'),
        runner=device.bind(Path(__file__)), existingState=checks, ownPersistentProfileAndPrefsUnchanged=own_preserved,
        deviceHelper=device.bind(Path(device.__file__)),
        noStreamingTransport=args.no_streaming,
        ownedPackageInternalInstall=args.internal,
        scope='Replacement install of the same separately owned116 package and debug certificate. Existing packages were never stopped, installed or modified. Own extracted runtime caches may change with the APK; persistent profiles/preferences must match.')
    device.write(public / 'Installation.json', result)
    print(json.dumps(result), flush=True)
    device.need(result['status'].startswith('PASS_'), 'OwnUpgradeInvariantFailed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('archive', 'upgrade'))
    parser.add_argument('--name', required=True)
    parser.add_argument('--installation', type=Path, required=True)
    parser.add_argument('--regression', type=Path)
    parser.add_argument('--static', type=Path)
    parser.add_argument('--no-streaming', action='store_true', help='Use adb documented push/install transport after a reconciled streaming failure.')
    parser.add_argument('--internal', action='store_true', help='Request internal storage for only the owned package; does not change the APK or global install-location setting.')
    args = parser.parse_args()
    if args.operation == 'archive':
        device.need(args.regression is not None, 'PriorNativeResultRequired')
        archive(args)
    else:
        device.need(args.static is not None, 'NewActualStaticProofRequired')
        upgrade(args)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        print(json.dumps(dict(status='BLOCKED_OWN116_ARCHIVE_OR_UPGRADE', errorType=type(error).__name__,
            code=code if re.fullmatch('[A-Za-z0-9]{1,100}', code) else 'PrivateEvidenceRequired')), flush=True)
        raise SystemExit(1)
