"""Run isolated checkpoint79 first-pose controls on QA, preserving saved data.

validate_report is I/O-free and accepts every slower pair. Camera rendering,
CPU submission and physical display are deliberately separate claims.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from qa_android_target import validate_qa_target

from run_execution78_device import validate_cost

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Gameplay79/FirstPose'
ADB = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
APK = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
PKG = 'com.heartoftherain.verification'
BASE = f'/sdcard/Android/data/{PKG}/files'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def nonnegative(v):
    return number(v) and v >= 0


def integer(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def digest(v):
    return isinstance(v, str) and re.fullmatch('[0-9a-f]{64}', v) is not None


def _trace(row, frequency):
    final = json.loads(row['startupTraceJson'])
    metadata = json.loads(row['metadataTraceJson'])
    assert isinstance(final, dict) and isinstance(metadata, dict)
    assert final['pending'] is False and final['workerFailed'] is False and final['cancelled'] is False
    assert final['resumed'] is False, 'Natural fixture unexpectedly resumed a cancelled job'
    if row['checkpoint78']:
        assert final['eligible'] is False and row['initialPending'] is False
        assert all(final[k] == 0 for k in ('jobStartedFrame', 'jobCompletedFrame', 'jobStartedTicks', 'jobCompletedTicks', 'workerStartedTicks', 'workerFinishedTicks')), 'Synchronous control started background work'
        return final
    assert final['eligible'] is True and row['initialPending'] is True
    assert final['generation'] > 0 and final['reason'] == 'pure leading swap'
    assert final['acceptedFrame'] == row['commandFrame']
    frame_keys = ('acceptedFrame', 'headSubmittedFrame', 'cameraWitnessFrame', 'jobStartedFrame', 'jobCompletedFrame', 'tailInstalledFrame')
    assert all(integer(final[k]) for k in frame_keys)
    assert [final[k] for k in frame_keys] == sorted(final[k] for k in frame_keys), 'Startup frames regress'
    assert final['headSubmittedFrame'] == final['cameraWitnessFrame'] == final['jobStartedFrame'], 'Worker did not start after the submitted head camera frame'
    assert final['jobCompletedFrame'] == final['tailInstalledFrame'] <= row['metadataReadyFrame'] <= row['queueInspectionFrame']
    tick_keys = ('acceptedTicks', 'headSubmittedTicks', 'cameraWitnessTicks', 'jobStartedTicks', 'workerQueuedTicks', 'workerStartedTicks', 'workerFinishedTicks', 'jobCompletedTicks', 'tailInstalledTicks')
    assert all(integer(final[k]) and final[k] > 0 for k in tick_keys)
    assert [final[k] for k in tick_keys] == sorted(final[k] for k in tick_keys), 'Worker preceded actual camera witness or timing ownership regressed'
    assert row['commandStartedTicks'] <= final['acceptedTicks'] <= row['commandFinishedTicks'] <= final['headSubmittedTicks']
    assert final['tailInstalledTicks'] <= row['metadataReadyTicks']
    assert final['callerThreadId'] > 0 and final['workerThreadId'] > 0 and final['callerThreadId'] != final['workerThreadId'], 'Work was not detached from the caller thread'
    for key in ('mainCaptureMs', 'mainInstallMs', 'buildWorkerMs', 'resourceWorkerMs', 'totalWorkerMs', 'workerQueueMs', 'holdMs'):
        assert nonnegative(final[key]), 'Invalid startup work duration'
    assert abs((final['workerFinishedTicks'] - final['workerStartedTicks']) * 1000 / frequency - final['totalWorkerMs']) < .02
    assert final['buildWorkerMs'] + final['resourceWorkerMs'] <= final['totalWorkerMs'] + .15
    assert final['headDuration'] == row['headDuration'] or abs(final['headDuration'] - row['headDuration']) < 1e-6
    for key in ('generation', 'eligible', 'headSubmittedFrame', 'cameraWitnessFrame', 'jobStartedFrame', 'jobCompletedFrame', 'tailInstalledFrame', 'workerStartedTicks', 'workerFinishedTicks'):
        assert metadata[key] == final[key], 'Completed metadata ownership changed after publication'
    assert metadata['pending'] is False
    if row['holdWorker']:
        assert final['held'] is True and final['headEndedFrame'] > 0 and final['holdFrames'] >= 2
        assert final['headEndedFrame'] <= row['releaseFrame'] <= final['jobCompletedFrame']
        assert final['cameraWitnessTicks'] < final['headEndedTicks'] <= row['holdReleasedTicks'] <= final['workerFinishedTicks']
        assert final['workerStartedTicks'] <= row['gateEnteredTicks'] <= row['holdReleasedTicks'] <= row['gateExitedTicks'] <= final['workerFinishedTicks'], 'Controlled hold did not actually enter and exit the worker gate'
        assert final['headEndedTicks'] < final['tailInstalledTicks'] and final['holdMs'] > 0
    return final


def validate_report(report):
    """Validate raw native-device controls without executing Android or I/O."""
    assert report['status'] == 'PASS_NATIVE_FIRST_POSE79' and not report['errors']
    assert report['schema'] == 1 and report['sourceCheckpoint'] == 79
    assert report['isolatedProfile'] is True and report['launchCleared'] is True
    assert report['targetFps'] == 60 and report['bufferCapacity'] == 16384 and report['droppedFrames'] == 0
    frequency = report['stopwatchFrequency']
    assert integer(frequency) and frequency > 0
    assert 0 < len(report['frames']) <= report['bufferCapacity']
    expected = []
    pair_index = 0
    for level in (4, 14, 31, 33):
        for mode in ('update', 'coroutine'):
            control_first = pair_index % 2 == 0
            pair_index += 1
            expected.extend([(level, mode, control_first, False), (level, mode, not control_first, False)])
    expected.extend([(4, mode, False, True) for mode in ('update', 'coroutine')])
    assert len(report['rows']) == len(expected) == 18
    offset = 0
    last_frame = -1
    paired = {}
    summaries = []
    for index, (row, spec) in enumerate(zip(report['rows'], expected)):
        level, mode, control, hold = spec
        assert (row['level'], row['dispatch'], row['checkpoint78'], row['holdWorker']) == spec
        assert row['fixture'] == 'L' + str(level)
        assert row['name'] == row['fixture'] + '_' + mode + ('_hold' if hold else '_control78' if control else '_current79')
        assert row['frameStart'] == offset and integer(row['frameCount']) and row['frameCount'] > 2
        frames = report['frames'][offset:offset + row['frameCount']]
        offset += row['frameCount']
        assert len(frames) == row['frameCount'] and all(f['row'] == index for f in frames)
        assert row['commandReturnedFrame'] == row['commandFrame'] <= row['metadataReadyFrame'] <= row['queueInspectionFrame']
        assert row['actionCallbacks'] == row['modelCallbacks'] == row['settlementCallbacks'] == 1
        assert row['headReferenceRetained'] is True and abs(row['headDuration'] - .12) < 1e-6
        assert row['queuedSteps'] == len(row['phases']) > 1
        assert abs(sum(p['duration'] for p in row['phases']) - row['scheduledSeconds']) < .001
        assert row['phases'][0]['kind'] == 'swap' and abs(row['phases'][0]['duration'] - .12) < 1e-6
        assert row['initialEnqueueCost']['frame'] == row['commandFrame']
        assert 0 < row['initialEnqueueCost']['phases'] <= row['queuedSteps']
        assert all(digest(row[k]) for k in ('turnHash', 'finalHash', 'checkpointHash', 'dictionaryOrderHash', 'queueHash', 'resourceHash'))
        ticks = [row[k] for k in ('commandStartedTicks', 'modelAcceptedTicks', 'commandFinishedTicks', 'metadataReadyTicks')]
        assert all(integer(t) and t > 0 for t in ticks) and ticks == sorted(ticks)
        walls = [row[k] for k in ('commandStartedWall', 'modelAcceptedWall', 'commandFinishedWall', 'metadataReadyWall', 'settledWall')]
        assert all(nonnegative(t) for t in walls) and walls == sorted(walls)
        for name, start, end in (('commandMs', ticks[0], ticks[2]), ('preAcceptMs', ticks[0], ticks[1]), ('presentationAcceptMs', ticks[1], ticks[2]), ('metadataWaitMs', ticks[2], ticks[3])):
            assert nonnegative(row[name]) and abs((end - start) * 1000 / frequency - row[name]) < .01
        assert abs(row['preAcceptMs'] + row['presentationAcceptMs'] - row['commandMs']) < .01
        assert nonnegative(row['queueInspectionMs']) and abs(row['settledWall'] - row['commandStartedWall'] - row['settleSeconds']) < 1e-5
        assert row['queueInspectionFinishedTicks'] >= row['queueInspectionStartedTicks'] >= row['settledTicks'] >= row['commandFinishedTicks']
        assert row['queueInspectionStartedTicks'] >= row['metadataReadyTicks']
        assert abs((row['queueInspectionFinishedTicks']-row['queueInspectionStartedTicks'])*1000/frequency-row['queueInspectionMs']) < .01, 'Queue hashing was not separately measured after playback'
        trace = _trace(row, frequency)
        pending_count = 0
        command_seen = False
        previous = None
        for frame in frames:
            assert integer(frame['frame']) and frame['frame'] > last_frame
            last_frame = frame['frame']
            assert integer(frame['ticks']) and nonnegative(frame['wall']) and nonnegative(frame['intervalMs'])
            assert all(isinstance(frame[k], bool) for k in ('pending', 'busy', 'canAct', 'canBuffer'))
            value = validate_cost(frame['cost'])
            assert value['frame'] == frame['frame'] and value['updateFinishedWall'] <= frame['wall'] + .001
            assert value['lookupMs'] == value['batchAddMs'] == value['spriteUpdateMs'] == 0, 'First-pose observer is not coarse'
            if previous:
                assert frame['frame'] == previous['frame'] + 1 and frame['ticks'] >= previous['ticks'] and frame['wall'] >= previous['wall'], 'A natural observation frame was removed'
            if frame['frame'] == row['commandFrame']:
                command_seen = True
                assert row['commandFinishedWall'] <= frame['wall'] + .001
                if mode == 'coroutine':
                    assert value['updateFinishedWall'] <= row['commandStartedWall'] + .001, 'Coroutine command-tail attribution was lost'
            if frame['pending']:
                pending_count += 1
                assert frame['busy'] is True and frame['canAct'] is False and frame['canBuffer'] is False, 'Pending startup exposed an action gate'
            previous = frame
        assert command_seen and pending_count == row['pendingSamples']
        assert isinstance(row['settledBeforeRelease'], bool) and row['settledBeforeRelease'] is False
        if hold:
            assert row['holdGateValid'] is True and row['holdSamples'] == 3
            assert digest(row['holdPoseHash']) and row['holdPoseHash'] == row['holdPoseAfterHash']
            assert row['releaseFrame'] > row['commandFrame'] and row['holdReleasedTicks'] > row['commandFinishedTicks']
            assert pending_count >= 3
        else:
            assert row['holdGateValid'] is False and row['holdSamples'] == row['holdReleasedTicks'] == row['releaseFrame'] == row['gateEnteredTicks'] == row['gateExitedTicks'] == 0
            key = (level, mode)
            paired.setdefault(key, {})[control] = row
        summaries.append({'name': row['name'], 'commandMs': row['commandMs'], 'preAcceptMs': row['preAcceptMs'], 'presentationAcceptMs': row['presentationAcceptMs'], 'metadataWaitMs': row['metadataWaitMs'], 'queueInspectionMs': row['queueInspectionMs'], 'settleSeconds': row['settleSeconds'], 'headHoldMs': trace['holdMs'], 'buildWorkerMs': trace['buildWorkerMs'], 'resourceWorkerMs': trace['resourceWorkerMs'], 'mainInstallMs': trace['mainInstallMs'], 'maxIntervalMs': max(f['intervalMs'] for f in frames), 'maxRenderMs': max(f['cost']['renderMs'] for f in frames)})
    assert offset == len(report['frames']), 'Orphaned or truncated frame samples'
    pairs = []
    for key, branches in paired.items():
        assert set(branches) == {False, True}
        a, b = branches[True], branches[False]
        assert all(a[k] == b[k] for k in ('turnHash', 'finalHash', 'checkpointHash', 'dictionaryOrderHash', 'queueHash', 'resourceHash', 'queuedSteps'))
        assert abs(a['scheduledSeconds'] - b['scheduledSeconds']) < 1e-5
        pairs.append({'level': key[0], 'dispatch': key[1], 'control78CommandMs': a['commandMs'], 'current79CommandMs': b['commandMs'], 'currentMinusControlCommandMs': b['commandMs'] - a['commandMs'], 'control78PresentationAcceptMs': a['presentationAcceptMs'], 'current79PresentationAcceptMs': b['presentationAcceptMs'], 'currentMinusControlPresentationAcceptMs': b['presentationAcceptMs'] - a['presentationAcceptMs'], 'control78SettleSeconds': a['settleSeconds'], 'current79SettleSeconds': b['settleSeconds'], 'currentMinusControlSettleSeconds': b['settleSeconds'] - a['settleSeconds']})
    for row in report['rows']:
        if not row['holdWorker']:
            continue
        normal = paired[(4, row['dispatch'])][False]
        assert all(row[k] == normal[k] for k in ('turnHash', 'finalHash', 'checkpointHash', 'dictionaryOrderHash', 'queueHash', 'resourceHash', 'queuedSteps')), 'Controlled hold changed the normal current79 outcome or transferred queue/resources'
        assert abs(row['scheduledSeconds'] - normal['scheduledSeconds']) < 1e-5
        assert [(p['kind'], p['duration']) for p in row['phases']] == [(p['kind'], p['duration']) for p in normal['phases']], 'Controlled hold changed the phase schedule'
    return {'status': 'VALIDATED_FIRST_POSE79_RAW_CONTROLS', 'natural_rows': 16, 'controlled_hold_rows': 2, 'natural_pairs': 8, 'frames': len(report['frames']), 'rows': summaries, 'pairs': pairs,
            'scope': 'Single matched pair per level/dispatch; all signed/slower differences retained. Current startup begins pure planning only after actual own-camera head rendering. Metadata and hash work are outside input spans. Controlled holds validate ownership/gates, not speed. Native lifecycle and actual touch/physical-display claims are separate.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    qa_target = validate_qa_target(args.serial, args.out)
    folder = args.out.resolve()
    assert folder.is_relative_to((ROOT / 'Verification/Evidence').resolve())
    folder.mkdir(parents=True, exist_ok=True)

    def adb(*cmd, check=True):
        return subprocess.run([str(ADB), '-s', args.serial, *map(str, cmd)], capture_output=True, check=check, timeout=180).stdout

    def state():
        names = adb('shell', 'run-as', PKG, 'ls', 'shared_prefs').decode().split()
        prefs = {n: adb('shell', 'run-as', PKG, 'sha256sum', 'shared_prefs/' + n).decode().split()[0]
                 for n in names if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', n)}
        names = adb('shell', 'find', BASE + '/Profiles', '-type', 'f', '-name', '*.json').decode().splitlines()
        saves = {n.removeprefix(BASE + '/'): adb('shell', 'sha256sum', n).decode().split()[0]
                 for n in names if re.fullmatch(re.escape(BASE) + r'/Profiles/[A-Za-z0-9_./-]+\.json', n)}
        return {'preferences': prefs, 'saves': saves}

    assert adb('get-state').strip() == b'device'
    profile = json.loads(json.loads(adb('shell', 'cat', BASE + '/Profiles/Development-v1/profile.json'))['payload'])
    assert not any(a['state'] in ['Reserved', 'Started'] for a in profile['attempts']), 'Preserve an active QA attempt'
    adb('shell', 'am', 'force-stop', PKG)
    before = state()
    started = datetime.now(timezone.utc).isoformat()
    result = {'utc': started, 'serial': args.serial, 'qa_target': qa_target, 'apk_sha256': sha(APK), 'before': before,
              'scope': 'Opt-in memory profile and isolated boards; runtime PlayerSwap delegate dispatch, no OS touch injection, real attempt/progression hooks, data reset or physical-device claim.'}
    error = None
    try:
        if args.install:
            result['install'] = adb('install', '-r', APK).decode().strip()
            assert 'Success' in result['install'] and state() == before, 'Install failed or changed real saves'
        remote = adb('shell', 'pm', 'path', PKG).decode().splitlines()[0].removeprefix('package:').strip()
        result['installed_apk_sha256'] = adb('shell', 'sha256sum', remote).decode().split()[0]
        assert result['installed_apk_sha256'] == result['apk_sha256'], 'Wrong QA APK installed'
        request = ROOT / '.verification-cache/Gameplay79/FirstPoseRequest'
        request.parent.mkdir(parents=True, exist_ok=True)
        request.write_text('all', encoding='ascii')
        adb('shell', 'mkdir', '-p', BASE)
        adb('shell', 'rm', '-f', BASE + '/FirstPose79/Report.json')
        adb('push', request, BASE + '/HOTR_RunFirstPose79')
        result['launch'] = adb('shell', 'am', 'start', '-W', '-n', PKG + '/com.unity3d.player.UnityPlayerActivity').decode().strip()
        deadline = time.monotonic() + 720
        while time.monotonic() < deadline:
            raw = adb('shell', 'cat', BASE + '/FirstPose79/Report.json', check=False)
            try:
                report = json.loads(raw)
            except (ValueError, UnicodeError):
                time.sleep(3)
                continue
            if report['status'] != 'RUNNING':
                break
            time.sleep(3)
        else:
            raise TimeoutError('FirstPose79 report unavailable; preserve installed data/logs')
        (folder / 'Report.json').write_bytes(raw)
        assert datetime.fromisoformat(report['utc'].replace('Z', '+00:00')) >= datetime.fromisoformat(started), 'Stale first-pose report'
        pid = adb('shell', 'pidof', PKG).decode().strip()
        assert re.fullmatch('[0-9]+', pid), 'Missing or ambiguous QA process'
        result['pid'] = pid
        logs = adb('logcat', '-d', '--pid=' + pid, '-v', 'brief').decode(errors='replace')
        (folder / 'Runtime.log').write_text(logs, encoding='utf-8')
        result['runtime_errors'] = len(re.findall('FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException', logs))
        assert result['runtime_errors'] == 0, 'Native runtime error'
        result['validated'] = validate_report(report)
    except Exception as exc:
        error = exc
        result['error'] = str(exc)
    finally:
        result['after'] = state()
        result['data_unchanged'] = result['after'] == before
        result['finishedUtc'] = datetime.now(timezone.utc).isoformat()
        result['status'] = 'PASS_FIRST_POSE79_DEVICE_AUDIT' if error is None and result['data_unchanged'] else 'FAIL_FIRST_POSE79_DEVICE_AUDIT'
        (folder / 'Installation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    assert result['data_unchanged'], 'FirstPose79 fixture changed saved data'
    if error is not None:
        raise error
    print(json.dumps({k: result[k] for k in ('status', 'apk_sha256', 'data_unchanged', 'validated')}), flush=True)


if __name__ == '__main__':
    main()
