"""Reinstall the exact installed development86 bytes on the authorized phone.

This is a same-version, same-bytes compatible replacement check. It never
installs ReleaseCompile, migrates a profile, clears data or retries a failed
installation destructively. The final Home capture requires human inspection.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

from phone import ADB, PACKAGE, Phone, ROOT, sha, utc, write


STATIC = ROOT / 'Verification/Evidence/Review86/StaticAndroid/99438abcdab442739b9329a1444905f8'
DEVELOPMENT = 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'


def sealed_apk_metadata(phone):
    """Use the accepted signature/manifest proof only for its exact APK bytes."""
    summary_path = ROOT / 'Verification/Evidence/Review86/Summary.json'
    summary = json.loads(summary_path.read_text('utf-8-sig'))
    assert summary['source_checkpoint'] == 86
    assert summary['sourceSHA256'] == phone.target['sourceSHA256']
    assert phone.target['sourceCheckpoint'] == 86 and phone.target['apk'] == DEVELOPMENT
    paths = [STATIC / 'Report.json', STATIC / 'Development/APK_Artifact.json',
             STATIC / 'Development/Badging.txt', STATIC / 'Development/Manifest.txt']
    bindings = {}
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        digest = sha(path)
        assert summary['evidenceSHA256'][relative] == digest
        bindings[relative] = digest
    report = json.loads(paths[0].read_text('utf-8-sig'))
    assert report['status'] == 'PASS_SDK_FREE_INTERNAL_APKS_STATIC86'
    artifact = next(a for a in report['artifacts'] if a['path'] == DEVELOPMENT)
    proof = json.loads(paths[1].read_text('utf-8-sig'))
    assert artifact['sha256'] == proof['sha256'] == phone.target['apkSHA256'] == sha(phone.apk)
    assert artifact['bytes'] == proof['bytes'] == phone.apk.stat().st_size
    assert proof['developmentSignatureVerifies'] is True
    assert artifact in summary['apks'] and artifact['nativePaymentAndAdvertisingSdkAbsent'] is True
    badging = paths[2].read_text('utf-8-sig')
    package = re.search(r"(?m)^package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", badging)
    minimum = re.search(r"(?m)^sdkVersion:'(\d+)'\r?$", badging)
    target = re.search(r"(?m)^targetSdkVersion:'(\d+)'\r?$", badging)
    assert package and minimum and target
    assert package.group(1) == PACKAGE and package.group(2) == '1' and package.group(3) == '1.0'
    assert int(minimum.group(1)) == artifact['minimumApi'] == 22
    assert int(target.group(1)) == artifact['targetApi'] == 36
    assert int(phone.target['props']['ro.build.version.sdk']) >= int(minimum.group(1))
    manifest = paths[3].read_text('utf-8-sig')
    assert 'android:debuggable' in manifest and '0xffffffff' in manifest.split('android:debuggable', 1)[1].splitlines()[0]
    return {'package': PACKAGE, 'versionCode': 1, 'versionName': '1.0',
            'minimumApi': 22, 'targetApi': 36, 'apkSHA256': artifact['sha256'],
            'signatureVerification': 'Accepted bound static APK_Artifact.json for the exact same bytes',
            'reviewSummarySHA256': sha(summary_path), 'staticInputsSHA256': bindings}


def assert_ordinary_idle(phone):
    """Keep configured backend identities and unfinished probes out of this check."""
    guard = phone.assert_no_active_attempt()
    assert guard['profilePresent'], 'Expected the existing ordinary test profile'
    assert not phone.exists(phone.base + '/ServerReview/configuration.json'), 'Do not replace a configured server session'
    names = phone.adb('shell', 'find', phone.base, '-maxdepth', '1', '-type', 'f').splitlines()
    assert not any(Path(name).name.startswith('HOTR_Run') for name in names), 'Preserve an unfinished development probe'
    assert phone.foreground(), 'Begin only with our ordinary app foreground'
    return guard


def install_same_bytes(phone):
    # Phone already validated the explicit physical serial and exact installed
    # APK. No uninstall, data-clear, downgrade or replacement fallback exists.
    result = subprocess.run([str(ADB), '-s', phone.serial, 'install', '-r', str(phone.apk)],
                            capture_output=True, timeout=180)
    output = (result.stdout + result.stderr).decode('utf-8', 'replace')
    output = output.replace(phone.serial, 'physical-phone-1').replace(str(phone.apk), DEVELOPMENT)
    return {'exitCode': result.returncode, 'result': output[:8192],
            'success': result.returncode == 0 and re.search(r'(?m)^Success\r?$', output) is not None,
            'operation': 'install -r', 'apkSHA256': phone.target['apkSHA256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--startup-seconds', type=float, default=15,
                        help='Bounded observation interval; this is not a gameplay-ready timing measurement.')
    args = parser.parse_args()
    assert 5 <= args.startup_seconds <= 60
    # Phone's constructor checks authorization, model, non-emulator identity,
    # current APK hash and the explicit serial supplied through the environment.
    phone = Phone(args.out)
    assert phone.target['packageAbsentBefore'] is True
    assert phone.target['persistentDirectoryAbsentBefore'] is True
    folder = phone.run_dir / 'Replacement'
    folder.mkdir(exist_ok=False)
    record = {'status': 'RUNNING', 'startedUtc': utc(), 'lastSuccessfulStage': 'PhoneBound',
              'runnerSHA256': sha(__file__), 'phoneHelperSHA256': sha(Path(__file__).with_name('phone.py')),
              'stages': [], 'targetSHA256': sha(phone.run_dir / 'Target.json'),
              'scope': 'Same-version same-bytes development86 install-r replacement on the fresh authorized physical test phone only. No ReleaseCompile installation, release signer acceptance, schema/history migration, cross-build profile migration, configured backend or pending purchase certification.',
              'profileDirectoryLimit': 'Development-v1 and non-development Player-v1 are distinct compile-time stores. ReleaseCompile is deliberately not installed; this check does not claim migration between those stores.',
              'homeVisualReview': 'PENDING_ACTUAL_REVIEW', 'destructiveFallback': False}

    def save_stage(stage, **values):
        record.update(values)
        record['lastSuccessfulStage'] = stage
        record['stages'].append({'stage': stage, 'utc': utc()})
        write(folder / 'Invocation.json', record)

    write(folder / 'Invocation.json', record)
    try:
        metadata = sealed_apk_metadata(phone)
        guard = assert_ordinary_idle(phone)
        before = phone.snapshot()
        assert before['profiles'] and before['preferences'], 'A complete ordinary save/preferences baseline is required'
        save_stage('PreflightBound', apk=metadata, attemptGuard=guard,
                   ordinaryBefore=before, ordinarySummaryBefore=phone.profile_summary())
        before_capture = phone.capture('Replacement/Before.png')
        save_stage('BeforeCaptured', beforeCapture={'path': 'Replacement/Before.png', 'sha256': sha(before_capture)})

        # Re-check immediately before the only stop/install sequence. No
        # gameplay action or financial operation is dispatched by this runner.
        assert_ordinary_idle(phone)
        phone.assert_installed()
        phone.adb('shell', 'am', 'force-stop', PACKAGE)
        assert not phone.adb('shell', 'pidof', PACKAGE, check=False)
        stopped = phone.snapshot()
        record['ordinaryStopped'] = stopped
        record['ordinaryUnchangedAfterStop'] = stopped == before
        assert stopped == before, 'Stop changed the ordinary baseline; do not install'
        save_stage('StoppedWithUnchangedBaseline')

        installed = install_same_bytes(phone)
        record['installation'] = installed
        write(folder / 'Invocation.json', record)
        assert installed['success'], 'Compatible replacement failed; no fallback is permitted'
        phone.assert_installed()
        after_install = phone.snapshot()
        record['ordinaryAfterInstall'] = after_install
        record['ordinaryUnchangedAfterInstall'] = after_install == before
        assert after_install == before, 'Replacement changed ordinary files/preferences'
        save_stage('SameBytesInstalledAndPreserved')

        launch = phone.launch()
        record['launch'] = launch
        assert 'Status: ok' in launch
        save_stage('OrdinaryLaunchAccepted')
        deadline = time.monotonic() + args.startup_seconds
        while time.monotonic() < deadline:
            time.sleep(min(1, max(0, deadline - time.monotonic())))
        assert phone.adb('shell', 'pidof', PACKAGE, check=False), 'Ordinary process exited during startup'
        assert phone.foreground(), 'Our ordinary app is not foreground after startup'
        phone.assert_installed()
        record['attemptGuardAfter'] = phone.assert_no_active_attempt()
        capture = phone.capture('Replacement/After_Normal_Launch.png')
        record['afterCapture'] = {'path': 'Replacement/After_Normal_Launch.png', 'sha256': sha(capture),
                                  'apkSHA256': phone.target['apkSHA256'], 'scope': 'Actual OS capture; reviewer must confirm ordinary Home, not a fixture or loading screen.'}
        record['appLog'] = phone.app_log('Replacement/Runtime.log')
        assert record['appLog']['selectedErrorCount'] == 0, 'Selected app startup errors require review'
        after = phone.snapshot()
        record.update(ordinaryAfterNormalLaunch=after, ordinaryDataUnchanged=after == before,
                      ordinarySummaryAfter=phone.profile_summary(), observationSeconds=args.startup_seconds)
        assert after == before, 'Ordinary profile/preferences changed after normal relaunch'
        save_stage('NormalLaunchAndFullBaselinePreserved')
        record['status'] = 'PASS_SAME_BYTES_DEVELOPMENT_REINSTALL_REQUIRES_HOME_REVIEW'
    except Exception as error:
        # Stop on the first failure. In particular there is no uninstall,
        # data restoration/reset, second installation or automatic relaunch.
        record.update(status='FAIL_SAME_BYTES_DEVELOPMENT_REINSTALL', errorType=type(error).__name__)
    finally:
        record['finishedUtc'] = utc()
        record['artifactsSHA256'] = {p.relative_to(folder).as_posix(): sha(p)
                                    for p in folder.rglob('*') if p.is_file() and p.name != 'Invocation.json'}
        write(folder / 'Invocation.json', record)
    print(json.dumps({'status': record['status'], 'lastSuccessfulStage': record['lastSuccessfulStage'],
                      'evidence': folder.relative_to(ROOT).as_posix()}), flush=True)
    return 0 if record['status'].startswith('PASS_SAME_BYTES') else 1


if __name__ == '__main__':
    raise SystemExit(main())
