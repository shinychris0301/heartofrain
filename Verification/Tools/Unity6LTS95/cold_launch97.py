"""Normal candidate cold relaunch after a retained unexpected-postinstall PID.

Preserves the failed installation receipt and both packages' durable data. This
does not claim a first-ever launch and never clears or reinstalls either app.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

import ldplayer95 as ld
import launch97 as launch
import regression97 as state

ROOT, PACKAGE = ld.ROOT, ld.PACKAGE
PUBLIC = ld.EVIDENCE/'ColdLaunch97'
PRIVATE = ROOT/'.verification-cache/Unity6LTS95/ColdLaunch97'
SECONDS, BIT_RATE, MAX_VIDEO = launch.SECONDS, launch.BIT_RATE, launch.MAX_VIDEO


def need(value, code): ld.need(value, code)
def no_links(path): return launch.no_links(path)


def validate_install_fields(value):
    need(value.get('status') == 'FAIL_FULL_GAME_LDPLAYER95_INSTALL'
         and value.get('errorCategory') == 'LD95CandidateUnexpectedlyStarted'
         and value.get('ownerPreservedAtExit') is True
         and value.get('ownerBefore') == value.get('ownerAfter') == value.get('ownerFinal')
         and value.get('ownerFinal', {}).get('ownerStopped') is True
         and value.get('ownerFinal', {}).get('activeAttempts') == 0,
         'Cold97ExactRetainedUnexpectedProcessFailureRequired')


def installed_context(target, installation):
    path = no_links(installation)
    need(path.name == 'Installation.json' and path.parent.parent == (ld.EVIDENCE/'LDPlayerRuns').resolve(),
         'Cold97OriginalContainedInstallReceiptRequired')
    value = ld.read(path); validate_install_fields(value)
    header = target.header()
    need(all(value.get(key) == header[key] for key in
             ('runner', 'apk', 'nativeReport', 'buildInvocation', 'staticReport', 'package')),
         'Cold97CurrentBuildAndStaticBindingsRequired')
    ld.packages_preserved(value['packagesBefore'], value['packagesAfter'])
    launch.installed_candidate(target, value['apk']['sha256'])
    return value, ld.bound(path)


def output_paths(path):
    path = no_links(path)
    need(path.parent == no_links(PUBLIC) and re.fullmatch('[a-f0-9]{32}', path.name)
         and not path.exists(), 'Cold97FreshPublicUUIDRequired')
    private = no_links(PRIVATE/path.name)
    need(not private.exists(), 'Cold97PrivateEvidencePreserved')
    return path, private


def capture(target, private, name, foreground):
    launch.unlocked(target, foreground)
    raw, _, _ = launch.raw_adb(target, 'exec-out', 'screencap', '-p')
    launch.raw_file(private/name, raw)
    width, height = state.png_size(raw)
    need(0 < width <= 5000 and 0 < height <= 5000 and (not foreground or width < height),
         'Cold97ActualForegroundPortraitCaptureRequired')
    return {**ld.bound(private/name), 'width': width, 'height': height, 'capturedUtc': ld.utc()}


def record(build, installation, output):
    output, private = output_paths(output)
    target = launch.make_target(build); installed, install_binding = installed_context(target, installation)
    identity = target.identity(); need(identity == installed['identity'], 'Cold97CurrentInstalledBootRequired')
    owner = target.owner_snapshot(); need(owner == installed['ownerFinal'], 'Cold97OwnerChangedSinceInstall')
    before = state.ordinary(target, PACKAGE, installed['apk']['sha256'])
    need(not state.markers(target) and not state.markers(target, ld.OWNER), 'Cold97PendingMarkerPreserved')
    packages = ld.package_map(target.adb('shell', 'pm', 'list', 'packages', '-f'))
    launch.preserve_packages(installed['packagesAfter'], packages); launch.unlocked(target)
    prior_pid = state.pid(target)
    output.mkdir(parents=True, exist_ok=False); private.mkdir(parents=True, exist_ok=False)
    report = {'schemaVersion': 1, 'status': 'RUNNING_NORMAL_COLD_LTS_RELAUNCH97', 'startedUtc': ld.utc(),
              'runner': ld.bound(Path(__file__)), 'ldHelper': ld.bound(Path(ld.__file__)),
              'launchPrimitives': ld.bound(Path(launch.__file__)), 'statePrimitives': ld.bound(Path(state.__file__)),
              'installation': install_binding, 'originalInstallationFailurePreserved': True,
              'buildInvocation': installed['buildInvocation'], 'nativeReport': installed['nativeReport'],
              'apk': installed['apk'], 'staticReport': installed['staticReport'], 'package': PACKAGE,
              'identity': identity, 'ownerBefore': owner, 'candidateBefore': before, 'packagesBefore': packages,
              'candidatePreviouslyRunning': bool(prior_pid), 'firstEverLaunchClaim': False,
              'recordingSecondsLimit': SECONDS, 'requestedBitRate': BIT_RATE,
              'showSplashScreenNativeGetter': False, 'showUnityLogoNativeGetter': False,
              'rootVisualReviewCompleted': False, 'splashAbsenceAutomaticallyCertified': False,
              'scope': 'Normal cold relaunch after the original install guard observed an unexpected candidate PID. Fresh idle/no-marker checks precede stopping only the separate candidate. Actual OS video and captures require root visual review. Both packages durable data and APKs preserved. No first-ever launch, gesture, onboarding advancement, human campaign, physical-device/performance/provider or production acceptance.'}
    ld.write(output/'Authorization.json', report)
    process = None; recording_started = None
    try:
        state.same(before, state.ordinary(target, PACKAGE, installed['apk']['sha256']))
        state.stop_idle(target, before, identity)
        need(not state.pid(target), 'Cold97CandidateColdStopRequired')
        remote = launch.remote_path(output.name)
        need(not target.exists(remote) and not target.adb('shell', 'pidof', 'screenrecord', accepted=(0, 1)),
             'Cold97ExistingRecordingPreserved')
        with (private/'screenrecord.stdout').open('xb') as stdout, (private/'screenrecord.stderr').open('xb') as stderr:
            recording_started = time.monotonic(); report['recordingDispatchUtc'] = ld.utc()
            process = subprocess.Popen(launch.recorder_args(target, remote), stdout=stdout, stderr=stderr,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            report['remoteRecorderPID'] = launch.wait_recorder(target, process, remote)
            report['recorderVerifiedUtc'] = ld.utc()
            report['startOSCapture'] = capture(target, private, 'BeforeLaunch_OS.png', False)
            need(not state.pid(target) and target.identity() == identity, 'Cold97ColdProcessAndBootRequired')
            report['candidateLaunchDispatchUtc'] = ld.utc()
            report['candidateLaunchSecondsAfterRecordingDispatch'] = round(time.monotonic()-recording_started, 6)
            raw, stderr_start, code = launch.raw_adb(target, 'shell', 'am', 'start', '-W', '-n', launch.ACTIVITY,
                                                   timeout=60, accepted=None)
            launch.raw_file(private/'am_start.stdout', raw); launch.raw_file(private/'am_start.stderr', stderr_start)
            need(code == 0 and re.search(rb'(?m)^Status:\s*ok\s*$', raw), 'Cold97CandidateStartRequired')
            process.wait(timeout=max(1, 42-(time.monotonic()-recording_started)))
            need(process.returncode == 0, 'Cold97CompleteScreenrecordRequired')
            report['recordingCompletedUtc'] = ld.utc()
        size = target.adb('shell', 'stat', '-c', '%s', remote)
        need(re.fullmatch('[0-9]+', size) and 1024 <= int(size) <= MAX_VIDEO, 'Cold97BoundedActualVideoRequired')
        remote_sha = target.remote_hash(remote); video = private/'Startup.mp4'
        raw, stderr, code = launch.raw_adb(target, 'pull', remote, video, timeout=120, accepted=None)
        launch.raw_file(private/'pull.stdout', raw); launch.raw_file(private/'pull.stderr', stderr)
        need(code == 0 and video.is_file() and video.stat().st_size == int(size) and ld.sha(video) == remote_sha
             and video.read_bytes()[4:8] == b'ftyp', 'Cold97ExactOriginalVideoPullRequired')
        report['privateOriginalVideo'] = ld.bound(video); report['remoteOriginalVideoSHA256'] = remote_sha
        report['endOSCapture'] = capture(target, private, 'AfterLaunch_OS.png', True)
        pid = state.pid(target); need(pid and pid != prior_pid, 'Cold97FreshCandidateProcessRequired')
        raw, stderr, code = launch.raw_adb(target, 'logcat', '-d', '--pid='+pid, '-v', 'brief', accepted=None)
        need(code == 0 and len(raw) <= 16*1024*1024, 'Cold97BoundedPIDLogRequired')
        launch.raw_file(private/'PID.log', raw); launch.raw_file(private/'PID.stderr', stderr)
        report.update(privatePIDLog=ld.bound(private/'PID.log'), candidatePID=int(pid),
                      selectedRuntimeErrorCount=len(re.findall(launch.ERRORS, raw.decode('utf-8', 'replace'))),
                      status='RECORDED_NORMAL_COLD_LTS_RELAUNCH97_REQUIRES_VISUAL_REVIEW')
    except Exception as error:
        report.update(status='FAIL_NORMAL_COLD_LTS_RELAUNCH97', **ld.safe_error(error))
    finally:
        if process is not None and process.poll() is None:
            try: process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)
                report['status'] = 'FAIL_NORMAL_COLD_LTS_RELAUNCH97'
                report['ownedRecorderClientCleanupRequired'] = True
        try:
            need(target.identity() == identity, 'Cold97BootChangedNoFurtherMutation')
            report['candidateAfter'] = state.ordinary(target, PACKAGE, installed['apk']['sha256'])
            state.same(before, report['candidateAfter'])
            report['ownerAfter'] = target.owner_snapshot(); need(report['ownerAfter'] == owner, 'Cold97OwnerChanged')
            report['packagesAfter'] = ld.package_map(target.adb('shell', 'pm', 'list', 'packages', '-f'))
            launch.preserve_packages(packages, report['packagesAfter'])
            installed_context(target, installation)
            need(ld.validated_static(ld.build(build)) == installed['staticReport'], 'Cold97BuildOrStaticChanged')
            report.update(ownerDataUnchanged=True, candidateDurableDataUnchanged=True,
                          otherInstalledPackagesUnchanged=True, sourcesAndAPKUnchanged=True)
        except Exception as error:
            report.update(status='FAIL_NORMAL_COLD_LTS_RELAUNCH97', finalGuard=ld.safe_error(error))
        report.update(remoteRecordingDeletionAttempted=False, privateEvidencePublished=False, finishedUtc=ld.utc())
        ld.write(output/'Report.json', report)
    return report


def validate_launch_receipt(path, build, installation):
    path = no_links(path); value = ld.read(path)
    need(path.parent.parent == PUBLIC.resolve() and path.name == 'Report.json'
         and value.get('status') == 'RECORDED_NORMAL_COLD_LTS_RELAUNCH97_REQUIRES_VISUAL_REVIEW'
         and value.get('firstEverLaunchClaim') is False and value.get('originalInstallationFailurePreserved') is True
         and all(value.get(key) is True for key in ('ownerDataUnchanged', 'candidateDurableDataUnchanged',
                  'otherInstalledPackagesUnchanged', 'sourcesAndAPKUnchanged'))
         and value.get('candidateBefore') == value.get('candidateAfter')
         and value.get('ownerBefore') == value.get('ownerAfter')
         and value.get('installation') == ld.bound(installation)
         and value.get('runner') == ld.bound(Path(__file__)), 'Cold97ExactSuccessfulRecordedRelaunchRequired')
    current = ld.build(build); static = ld.validated_static(current)
    need(value.get('buildInvocation') == ld.bound(current['invocationPath']) and value.get('apk') == ld.bound(current['apk'])
         and value.get('staticReport') == static, 'Cold97CurrentActualBuildRequired')
    for key in ('privateOriginalVideo', 'startOSCapture', 'endOSCapture', 'privatePIDLog'):
        item = value[key]; actual = no_links(ROOT/item['path'])
        need(actual.is_relative_to((PRIVATE/path.parent.name).resolve()) and ld.bound(actual) == state.core_binding(item),
             'Cold97OriginalMediaBindingChanged')
    return {'report': value, 'binding': ld.bound(path), 'build': current, 'static': static,
            'installation': ld.bound(installation), 'visualApproval': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execute', action='store_true')
    for name in ('build', 'installation', 'out'): parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt' or not all(path.is_absolute() for path in (args.build, args.installation, args.out)):
        parser.error('Explicit Windows normal cold-relaunch action and absolute bound paths required')
    try:
        result = record(args.build, args.installation, args.out)
        print(json.dumps({'status': result['status'], 'report': str(args.out/'Report.json'), 'firstEverLaunchClaim': False}))
        raise SystemExit(0 if result['status'].startswith('RECORDED_') else 1)
    except (ValueError, RuntimeError, OSError) as error:
        print(json.dumps({'status': 'FAIL_ROOT_COLD_RELAUNCH97', **ld.safe_error(error)})); raise SystemExit(1)
