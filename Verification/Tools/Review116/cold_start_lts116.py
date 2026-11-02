"""Record an actual process-cold start of only the approved LTS test package.

Raw video, logs and prelaunch foreground pixels remain private. No screenshot
or native getter alone is treated as proof that startup branding was absent.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

import emulator116 as device

LTS_PACKAGE = 'com.heartoftherain.review116lts'


def configure():
    # Configuration is local to this independent Python process. The running
    # Unity2022 regression and its unchanged helper source are not modified.
    device.PACKAGE = LTS_PACKAGE
    device.BASE = '/sdcard/Android/data/' + LTS_PACKAGE + '/files'
    device.ACTIVITY = LTS_PACKAGE + '/com.unity3d.player.UnityPlayerActivity'
    return device


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--installation', type=Path, required=True)
    args = parser.parse_args()
    configure()
    installation = args.installation.resolve()
    device.need(installation.is_relative_to(device.PUBLIC), 'OwnLtsInstallationReceiptRequired')
    installed = device.read(installation)
    device.need(installed.get('status') == 'PASS_NEW_REVIEW116_INSTALL' and installed.get('package') == LTS_PACKAGE,
        'SuccessfulFreshApprovedLtsInstallationRequired')
    proof_path = device.ROOT / installed['staticProof']['path']
    device.need(device.bind(proof_path) == installed['staticProof'], 'UnchangedLtsStaticProofRequired')
    proof = device.read(proof_path)
    device.need(proof.get('status') == 'PASS_STATIC_APK116_LTS' and proof.get('unity') == '6000.3.27f1'
        and proof.get('package') == LTS_PACKAGE and proof.get('showSplashScreen') is False
        and proof.get('showUnityLogo') is False, 'ActualApprovedLtsNoSplashArtifactRequired')
    eligibility = device.require_launch_profile(installed)
    public, private = device.directories(args.name)
    target = device.Target(private)
    device.need(target.identity == installed['identity'], 'SameLtsTargetAndBootRequired')
    before = target.snapshot()
    device.write(public / 'Before.json', before)
    device.need(all(row['idleProof']['idle'] for row in before['games'].values()), 'ExistingOrdinaryProfilesMustBeIdle')
    apk_path = target.query('shell', 'pm', 'path', LTS_PACKAGE)
    device.need(apk_path.startswith('package:') and '\n' not in apk_path
        and target.exact_hash(apk_path.removeprefix('package:')) == installed['apk']['sha256'], 'ExactInstalledLtsApkRequired')
    own_before = target.files(LTS_PACKAGE)
    pid_before = target.query('shell', 'pidof', LTS_PACKAGE, accepted=(0, 1))
    if pid_before:
        device.need(target.idle(LTS_PACKAGE, own_before)['idle'], 'OwnLtsProfileMustBeIdleBeforeColdStop')
        target.query('shell', 'am', 'force-stop', LTS_PACKAGE)
    device.need(not target.query('shell', 'pidof', LTS_PACKAGE, accepted=(0, 1)), 'LtsColdStartRequiresNoExistingPid')
    device.need(not target.query('shell', 'pidof', 'screenrecord', accepted=(0, 1)), 'ExistingScreenRecordingPreserved')
    remote = device.BASE + '/RegressionHistory116/' + args.name
    device.need(not target.exists(remote), 'FreshOwnColdCaptureDirectoryRequired')
    target.query('shell', 'mkdir', '-p', remote)
    remote_video = remote + '/ColdStart.mp4'
    with (private / 'Recorder.private').open('xb') as log:
        recorder = subprocess.Popen([str(device.ADB), '-P', str(device.ADB_PORT), '-s', target.serial,
            'shell', 'screenrecord', '--time-limit', '20', '--bit-rate', '6000000', remote_video],
            stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(1)
        device.need(recorder.poll() is None, 'ActualLtsScreenRecordingDidNotStart')
        started = device.utc()
        launch = target.query('shell', 'am', 'start', '-W', '-n', device.ACTIVITY, timeout=120)
        device.need(re.search(r'(?m)^Status:\s*ok\s*$', launch), 'LtsColdLaunchFailed')
        new_pid = target.query('shell', 'pidof', LTS_PACKAGE)
        device.need(re.fullmatch('[0-9]+', new_pid) and new_pid != pid_before, 'NewLtsColdProcessRequired')
        recorder.wait(timeout=90)
        device.need(recorder.returncode == 0, 'ActualLtsScreenRecordingFailed')
    expected = target.exact_hash(remote_video)
    raw = target.query('exec-out', 'cat', remote_video, binary=True)
    device.need(device.digest(raw) == expected and len(raw) > 10000 and b'ftyp' in raw[:32], 'ExactCompletedLtsMp4Required')
    video = private / 'ColdStart.mp4'
    video.write_bytes(raw)
    screenshot = target.query('exec-out', 'screencap', '-p', binary=True)
    device.need(screenshot.startswith(b'\x89PNG\r\n\x1a\n'), 'ActualLtsPostStartOsScreenshotRequired')
    (public / 'PostColdStart_OS.png').write_bytes(screenshot)
    target.query('logcat', '-d', '--pid=' + new_pid, '-t', '2000', binary=True)
    after = target.snapshot(before)
    checks = device.compare_existing(before, after)
    device.write(public / 'After.json', after)
    result = dict(status='PASS_RECORDED_LTS_PROCESS_COLD_START' if checks['passExistingPackageAndGameData'] else 'FAIL_LTS_COLD_START_EXISTING_STATE',
        utc=device.utc(), launchStartedUtc=started, package=LTS_PACKAGE, unity='6000.3.27f1',
        apk=installed['apk'], installation=device.bind(installation), staticProof=installed['staticProof'],
        launchProfileEligibility=eligibility,
        runner=device.bind(Path(__file__)), deviceHelper=device.bind(Path(device.__file__)),
        rawVideo=device.bind(video), oldPidObserved=bool(pid_before), oldPidWasStopped=bool(pid_before),
        noExistingPidBeforeLaunch=True, newPidObserved=True, recorderExitCode=recorder.returncode,
        showSplashScreen=False, showUnityLogo=False, visualSplashReviewPending=True,
        existingState=checks,
        scope='Actual emulator process-cold launch and OS screen recording of this exact LTS no-splash-configured artifact. Full decoded-frame visual review is separate; this receipt alone does not establish absence of branding, first-ever startup, interactive readiness or performance.')
    device.write(public / 'ColdStart.json', result)
    print(json.dumps(result), flush=True)
    device.need(result['status'].startswith('PASS_'), 'LtsColdStartInvariantFailed')


if __name__ == '__main__':
    main()
