"""Root-only first observed LTS candidate launch and private 30-second recording.

Requires an actual current full-game build, static proof and fresh LD installation.
Launches only the separate candidate; never stops, replaces, clears or launches
the owner app. Video/OS PNGs/PID logs remain private until explicit review.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time
from types import SimpleNamespace

import ldplayer95 as ld

ROOT = ld.ROOT
PUBLIC = ld.EVIDENCE / 'FirstLaunch97'
PRIVATE = ROOT / '.verification-cache/Unity6LTS95/FirstLaunch97'
PACKAGE = 'com.heartoftherain.unity6lts95'
ACTIVITY = PACKAGE + '/com.unity3d.player.UnityPlayerActivity'
LD_HELPER_SHA = 'cee01ac553de1510b9348ef7bf38ca8829ac7062ce3a67ac0c3ad07f0ea8837b'
SECONDS = 30
BIT_RATE = 8000000
MAX_VIDEO = 80 * 1024 * 1024
ERRORS = r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException|DllNotFoundException'


def need(value, code):
    if not value:
        raise ValueError(code)


def no_links(path):
    path = Path(path).absolute()
    for node in (path, *path.parents):
        if node.exists():
            need(not node.is_symlink() and not getattr(node.stat(), 'st_file_attributes', 0) & 0x400,
                 'Launch97LinkedPathRefused')
    return path.resolve()


def output_paths(output):
    output = no_links(output)
    need(output.parent == no_links(PUBLIC) and re.fullmatch(r'[0-9a-f]{32}', output.name)
         and not output.exists(), 'Launch97FreshPublicUUIDRequired')
    private = no_links(PRIVATE / output.name)
    need(not private.exists(), 'Launch97FreshPrivateUUIDRequired')
    return output, private


def raw_adb(target, *args, timeout=30, accepted=(0,)):
    remaining = int(target.deadline - time.monotonic())
    need(remaining > 0, 'Launch97PhaseDeadline')
    return ld.run([ld.ADB, '-s', target.serial, *args], min(timeout, remaining), accepted)


def raw_file(path, data):
    with Path(path).open('xb') as stream:
        stream.write(data)


def require_install(target, installation_path):
    path = no_links(installation_path)
    need(path.name == 'Installation.json' and path.parent.parent == (ld.EVIDENCE / 'LDPlayerRuns').resolve()
         and re.fullmatch(r'[a-f0-9]{32}', path.parent.name), 'Launch97ExactLDInstallationRequired')
    value, preflight = ld.read(path), ld.read(no_links(path.parent / 'Preflight.json'))
    current = target.header()
    fields = ('runner', 'apk', 'nativeReport', 'buildInvocation', 'staticReport', 'package')
    need(value.get('status') == 'PASS_FRESH_FULL_GAME_LDPLAYER95_INSTALL'
         and preflight.get('status') == 'PASS_READ_ONLY_LDPLAYER95_FULL_GAME_PREFLIGHT'
         and all(value.get(key) == preflight.get(key) == current[key] for key in fields)
         and value.get('identity') == preflight.get('identity')
         and value.get('ownerDataUnchanged') is True and value.get('ownerPreservedAtExit') is True
         and value.get('otherInstalledPackagesUnchanged') is True and value.get('gameAutomaticallyLaunched') is False
         and value.get('installResult') == 'Success', 'Launch97CurrentSuccessfulFreshInstallRequired')
    need(value['ownerBefore'] == value['ownerAfter'] == value['ownerFinal'] == preflight['ownerBefore']
         and value['ownerFinal'].get('installed') is True and value['ownerFinal'].get('ownerStopped') is True
         and value['ownerFinal'].get('activeAttempts') == 0
         and value['packagesBefore'] == preflight['packagesBefore'], 'Launch97PreservedStoppedOwnerRequired')
    ld.packages_preserved(value['packagesBefore'], value['packagesAfter'])
    settings = target.build['native']['after']
    need(settings.get('showSplashScreen') is False and settings.get('showUnityLogo') is False,
         'Launch97NativeSplashGetterConfigurationRequired')
    return value, ld.bound(path)


def make_target(build_path):
    need(ld.sha(Path(ld.__file__)) == LD_HELPER_SHA and ld.PACKAGE == PACKAGE,
         'Launch97FrozenLDCandidateHelperRequired')
    return ld.LDPlayer(build_path)  # Build/static validation precedes every device call.


def installed_candidate(target, apk_sha):
    paths = target.installed_paths(PACKAGE)
    need(len(paths) == 1 and target.remote_hash(paths[0]) == apk_sha, 'Launch97ExactSingleInstalledCandidateAPKRequired')


def pristine_candidate(target):
    need(not target.adb('shell', 'pidof', PACKAGE, accepted=(0, 1)), 'Launch97CandidateAlreadyRunningPreserved')
    base = '/sdcard/Android/data/' + PACKAGE + '/files'
    if target.exists(base):
        need(not target.adb('shell', 'find', base, '-type', 'f'), 'Launch97CandidateAlreadyInitializedPreserved')
    state = target.adb('shell', 'run-as', PACKAGE, 'sh', '-c', '"if test -d shared_prefs; then echo PRESENT; else echo ABSENT; fi"')
    need(state in ('PRESENT', 'ABSENT'), 'Launch97CandidatePreferencesAccessRequired')
    if state == 'PRESENT':
        need(not target.adb('shell', 'run-as', PACKAGE, 'ls', 'shared_prefs'), 'Launch97ExistingCandidatePreferencesPreserved')


def unlocked(target, foreground=False):
    if foreground:
        lines = target.adb('shell', 'dumpsys', 'activity', 'activities').splitlines()
        need(any(PACKAGE + '/' in line for line in lines if 'topResumedActivity=' in line or 'mResumedActivity:' in line),
             'Launch97CandidateForegroundRequired')
    policy = target.adb('shell', 'dumpsys', 'window', 'policy').split('KeyguardServiceDelegate', 1)[-1]
    need(re.search(r'(?m)^\s*showing=false\s*$', policy) is not None
         and re.search(r'(?m)^\s*showing=true\s*$', policy) is None, 'Launch97UnlockedScreenRequired')


def remote_path(token):
    need(re.fullmatch(r'[a-f0-9]{32}', token) is not None, 'Launch97FreshVideoTokenRequired')
    return '/data/local/tmp/HOTR_LTS97_' + token + '.mp4'


def recorder_args(target, remote):
    need(re.fullmatch(r'/data/local/tmp/HOTR_LTS97_[a-f0-9]{32}\.mp4', remote) is not None,
         'Launch97OwnedRemoteVideoOnly')
    return [str(ld.ADB), '-s', target.serial, 'shell', 'screenrecord', '--time-limit', str(SECONDS),
            '--bit-rate', str(BIT_RATE), remote]


def recorder_matches(cmdline, remote):
    words = cmdline.decode('utf-8', 'strict').strip('\x00').split('\x00')
    return words[0] in ('screenrecord', '/system/bin/screenrecord') and words[1:] == [
        '--time-limit', str(SECONDS), '--bit-rate', str(BIT_RATE), remote]


def wait_recorder(target, process, remote):
    deadline = min(target.deadline, time.monotonic() + 6)
    while time.monotonic() < deadline:
        need(process.poll() is None, 'Launch97RecorderExitedBeforeCandidateLaunch')
        pids = target.adb('shell', 'pidof', 'screenrecord', accepted=(0, 1)).split()
        need(len(pids) <= 16 and all(re.fullmatch(r'[1-9][0-9]*', pid) for pid in pids), 'Launch97RecorderPIDListInvalid')
        matched = []
        for pid in pids:
            command, _, _ = raw_adb(target, 'exec-out', 'cat', '/proc/' + pid + '/cmdline')
            if recorder_matches(command, remote):
                matched.append(pid)
        need(len(matched) <= 1, 'Launch97RecorderOwnershipAmbiguous')
        if len(matched) == 1 and target.exists(remote):
            return int(matched[0])
        time.sleep(0.15)
    raise ValueError('Launch97OwnedRecorderStartUnverified')


def capture_png(target, private, name, foreground):
    unlocked(target, foreground)
    raw, _, _ = raw_adb(target, 'exec-out', 'screencap', '-p')
    path = private / name
    raw_file(path, raw)
    spec = importlib.util.spec_from_file_location('launch97_png_reader', ROOT / 'Verification/Tools/Review93/phone.py')
    reader = importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    width, height = reader.validate_png(raw)  # Pure parser, never constructs Phone.
    need(0 < width < height <= 5000, 'Launch97PortraitOSCaptureRequired')
    return {**ld.bound(path), 'width': width, 'height': height, 'capturedUtc': ld.utc()}


def preserve_packages(before, after):
    need(before == after, 'Launch97InstalledPackageInventoryChanged')


def validate_launch_receipt(report_path, build_path, installation_path):
    """Read-only recording/source/artifact guard; no device or visual approval."""
    path = no_links(report_path)
    need(path.name == 'Report.json' and path.parent.parent == no_links(PUBLIC)
         and re.fullmatch(r'[a-f0-9]{32}', path.parent.name), 'Launch97ScopedRecordingReceiptRequired')
    need(ld.sha(Path(ld.__file__)) == LD_HELPER_SHA, 'Launch97FrozenLDCandidateHelperRequired')
    report = ld.read(path)
    build = ld.build(build_path)
    static = ld.validated_static(build)
    expected = {'buildInvocation': ld.bound(build['invocationPath']), 'nativeReport': ld.bound(build['nativePath']),
                'apk': ld.bound(build['apk']), 'staticReport': static}
    header = {**expected, 'runner': ld.bound(Path(ld.__file__)), 'package': PACKAGE}
    installed, install_binding = require_install(SimpleNamespace(build=build, header=lambda: header), installation_path)
    need(report.get('status') == 'RECORDED_FIRST_OBSERVED_LTS_LAUNCH97_REQUIRES_VISUAL_REVIEW'
         and report.get('runner') == ld.bound(Path(__file__)) and report.get('ldHelper') == ld.bound(Path(ld.__file__))
         and report.get('installation') == install_binding and report.get('identity') == installed.get('identity')
         and report.get('package') == PACKAGE and all(report.get(key) == value for key, value in expected.items())
         and report.get('ownerDataUnchanged') is True and report.get('otherInstalledPackagesUnchanged') is True
         and report.get('sourcesAndAPKUnchanged') is True and report.get('recordingSecondsLimit') == SECONDS
         and report.get('showSplashScreenNativeGetter') is False and report.get('showUnityLogoNativeGetter') is False
         and report.get('splashAbsenceAutomaticallyCertified') is False and report.get('rootVisualReviewCompleted') is False
         and report.get('privateEvidencePublished') is False,
         'Launch97BoundCurrentCompleteRecordingRequired')
    need(report['ownerBefore'] == report['ownerAfter'] == installed['ownerFinal']
         and report['packagesBefore'] == report['packagesAfter'] == installed['packagesAfter'], 'Launch97PreservationReceiptChanged')
    expected_private = no_links(PRIVATE / path.parent.name)
    for key, name in [('privateOriginalVideo', 'Startup.mp4'), ('startOSCapture', 'BeforeLaunch_OS.png'),
                      ('endOSCapture', 'AfterLaunch_OS.png'), ('privatePIDLog', 'PID.log')]:
        item = report[key]
        artifact = no_links(ROOT / item['path'])
        need(artifact == expected_private / name and ld.bound(artifact) == {key: item[key] for key in ('path', 'sha256', 'bytes')},
             'Launch97PrivateRecordingArtifactChanged')
    need(report['privateOriginalVideo']['sha256'] == report['remoteOriginalVideoSHA256'], 'Launch97VideoRemoteHashMismatch')
    return {'report': report, 'binding': ld.bound(path), 'build': build, 'static': static,
            'installation': install_binding, 'visualApproval': False}


def record(build_path, installation_path, output):
    output, private = output_paths(output)
    target = make_target(build_path)
    installed, installation_binding = require_install(target, installation_path)
    identity = target.identity()
    need(identity == installed['identity'], 'Launch97LDIdentityChangedSinceInstall')
    installed_candidate(target, installed['apk']['sha256'])
    before = target.owner_snapshot()
    need(before == installed['ownerFinal'], 'Launch97OwnerChangedSinceInstall')
    packages = ld.package_map(target.adb('shell', 'pm', 'list', 'packages', '-f'))
    preserve_packages(installed['packagesAfter'], packages)
    pristine_candidate(target)
    unlocked(target)
    remote = remote_path(output.name)
    need(not target.exists(remote), 'Launch97ExistingRemoteRecordingPreserved')
    need(not target.adb('shell', 'pidof', 'screenrecord', accepted=(0, 1)), 'Launch97OtherRecorderPreserved')
    output.mkdir(parents=True, exist_ok=False);private.mkdir(parents=True, exist_ok=False)
    report = {'schemaVersion': 1, 'status': 'RUNNING_FIRST_OBSERVED_LTS_CANDIDATE_LAUNCH97', 'startedUtc': ld.utc(),
              'runner': ld.bound(Path(__file__)), 'ldHelper': ld.bound(Path(ld.__file__)), 'installation': installation_binding,
              'buildInvocation': installed['buildInvocation'], 'nativeReport': installed['nativeReport'], 'apk': installed['apk'],
              'staticReport': installed['staticReport'], 'package': PACKAGE, 'identity': identity, 'ownerBefore': before,
              'packagesBefore': packages, 'recordingSecondsLimit': SECONDS, 'requestedBitRate': BIT_RATE,
              'showSplashScreenNativeGetter': False, 'showUnityLogoNativeGetter': False,
              'splashGetterScope': 'Native configuration only; actual video requires visual review.',
              'rootVisualReviewCompleted': False, 'splashAbsenceAutomaticallyCertified': False,
              'scope': 'First observed candidate launch after bound fresh install, no candidate PID/external files/preferences before launch. Private OS screenrecord plus start/end OS captures and PID log. Owner stays stopped and unchanged. No UI gestures, route advancement, owner mutation, physical phone/provider/performance or production approval.'}
    ld.write(output / 'Authorization.json', report)
    process = None
    recording_started = None
    try:
        with (private / 'screenrecord.stdout').open('xb') as stdout, (private / 'screenrecord.stderr').open('xb') as stderr:
            recording_started = time.monotonic()
            report['recordingDispatchUtc'] = ld.utc()
            process = subprocess.Popen(recorder_args(target, remote), stdout=stdout, stderr=stderr,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            report['remoteRecorderPID'] = wait_recorder(target, process, remote)
            report['recorderVerifiedUtc'] = ld.utc()
            report['startOSCapture'] = capture_png(target, private, 'BeforeLaunch_OS.png', False)
            need(target.owner_snapshot() == before, 'Launch97OwnerChangedBeforeLaunch')
            pristine_candidate(target)
            need(process.poll() is None, 'Launch97RecorderEndedBeforeLaunchDispatch')
            cmdline, _, _ = raw_adb(target, 'exec-out', 'cat', '/proc/' + str(report['remoteRecorderPID']) + '/cmdline')
            need(recorder_matches(cmdline, remote), 'Launch97RecorderOwnershipChangedBeforeLaunch')
            report['candidateLaunchDispatchUtc'] = ld.utc()
            report['candidateLaunchSecondsAfterRecordingDispatch'] = round(time.monotonic() - recording_started, 6)
            raw, stderr_start, code = raw_adb(target, 'shell', 'am', 'start', '-W', '-n', ACTIVITY, timeout=60, accepted=None)
            raw_file(private / 'am_start.stdout', raw);raw_file(private / 'am_start.stderr', stderr_start)
            need(code == 0 and re.search(rb'(?m)^Status:\s*ok\s*$', raw) is not None, 'Launch97CandidateStartFailed')
            process.wait(timeout=max(1, 42 - (time.monotonic() - recording_started)))
            need(process.returncode == 0, 'Launch97ScreenrecordDidNotComplete')
            report['recordingCompletedUtc'] = ld.utc()
            report['recordingCommandElapsedSeconds'] = round(time.monotonic() - recording_started, 6)
        size = target.adb('shell', 'stat', '-c', '%s', remote)
        need(re.fullmatch(r'[0-9]+', size) is not None and 1024 <= int(size) <= MAX_VIDEO, 'Launch97BoundedRemoteVideoRequired')
        remote_sha = target.remote_hash(remote)
        video = no_links(private / 'Startup.mp4')
        need(not video.exists(), 'Launch97ExistingPrivateVideoPreserved')
        stdout_pull, stderr_pull, code = raw_adb(target, 'pull', remote, video, timeout=120, accepted=None)
        raw_file(private / 'pull.stdout', stdout_pull);raw_file(private / 'pull.stderr', stderr_pull)
        need(code == 0 and video.is_file() and video.stat().st_size == int(size) and ld.sha(video) == remote_sha,
             'Launch97OriginalVideoPullMismatch')
        with video.open('rb') as stream:
            header = stream.read(12)
        need(len(header) == 12 and header[4:8] == b'ftyp', 'Launch97MP4HeaderRequired')
        report['privateOriginalVideo'] = ld.bound(video)
        report['remoteOriginalVideoSHA256'] = remote_sha
        report['endOSCapture'] = capture_png(target, private, 'AfterLaunch_OS.png', True)
        pid = target.adb('shell', 'pidof', PACKAGE)
        need(re.fullmatch(r'[1-9][0-9]*', pid) is not None, 'Launch97SingleCandidatePIDRequired')
        raw_log, stderr_log, log_code = raw_adb(target, 'logcat', '-d', '--pid=' + pid, '-v', 'brief', accepted=None)
        need(len(raw_log) <= 16 * 1024 * 1024, 'Launch97BoundedPIDLogRequired')
        raw_file(private / 'PID.log', raw_log)
        raw_file(private / 'PID.stderr', stderr_log)
        need(log_code == 0, 'Launch97CandidatePIDLogReadFailed')
        report.update(privatePIDLog=ld.bound(private / 'PID.log'), candidatePID=int(pid),
                      selectedRuntimeErrorCount=len(re.findall(ERRORS, raw_log.decode('utf-8', 'replace'))),
                      status='RECORDED_FIRST_OBSERVED_LTS_LAUNCH97_REQUIRES_VISUAL_REVIEW')
    except Exception as error:
        report.update(status='FAIL_FIRST_OBSERVED_LTS_LAUNCH97', **ld.safe_error(error))
    finally:
        try:
            if process is not None and process.poll() is None:
                process.wait(timeout=max(1, 42 - (time.monotonic() - recording_started)))
        except subprocess.TimeoutExpired:
            try:
                process.kill()  # Only this owned host adb client; remote has a 30-second cap.
                process.wait(timeout=5)
                report.update(status='FAIL_FIRST_OBSERVED_LTS_LAUNCH97', recorderClientRequiredOwnedCleanup=True)
            except Exception as error:
                report.update(status='FAIL_FIRST_OBSERVED_LTS_LAUNCH97', ownedClientCleanupError=ld.safe_error(error))
        except Exception as error:
            report.update(status='FAIL_FIRST_OBSERVED_LTS_LAUNCH97', ownedClientCleanupError=ld.safe_error(error))
        try:
            report['ownerAfter'] = target.owner_snapshot()
            need(report['ownerAfter'] == before, 'Launch97OwnerChangedAtExit')
            report['packagesAfter'] = ld.package_map(target.adb('shell', 'pm', 'list', 'packages', '-f'))
            preserve_packages(packages, report['packagesAfter'])
            installed_candidate(target, installed['apk']['sha256'])
            need(target.identity() == identity, 'Launch97LDBootChangedDuringRecording')
            need(ld.validated_static(ld.build(build_path)) == installed['staticReport'], 'Launch97CurrentBuildOrStaticProofChanged')
            report.update(ownerDataUnchanged=True, otherInstalledPackagesUnchanged=True, sourcesAndAPKUnchanged=True)
        except Exception as error:
            report.update(status='FAIL_FIRST_OBSERVED_LTS_LAUNCH97', finalGuard=ld.safe_error(error))
        report.update(remoteRecordingDeletionAttempted=False, privateEvidencePublished=False, finishedUtc=ld.utc())
        ld.write(output / 'Report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--installation', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt' or not all(path.is_absolute() for path in (args.build, args.installation, args.out)):
        parser.error('Explicit root Windows execution and absolute build/install/fresh output required')
    try:
        report = record(args.build, args.installation, args.out)
        print(json.dumps({'status': report['status'], 'package': PACKAGE, 'rootVisualReviewCompleted': False,
                          'splashAbsenceAutomaticallyCertified': False, 'ownerMutation': False}))
        return 1 if report['status'].startswith('FAIL_') else 0
    except Exception as error:
        print(json.dumps({'status': 'FAIL_ROOT_LTS_LAUNCH97', **ld.safe_error(error), 'ownerMutation': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
