"""Opt-in same-APK/same-process pure construction controls on the dedicated QA emulator."""
import argparse
import hashlib
import json
import math
import re
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Gameplay76/CommandPairs'
APK = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
ADB = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
PKG = 'com.heartoftherain.verification'
REMOTE = f'/sdcard/Android/data/{PKG}/files'
CASES = {'L4_match', 'L14_match', 'L31_match', 'L33_match', 'L1_Golden',
         'L26_Bomb', 'L48_Orb', 'DenseCrate45_DoubleOrb'}


def validate_report(report):
    """Pure source-level validation; calling this does not execute a device."""
    assert report['status'] == 'PASS_SAME_APK_COMMAND_CONSTRUCTION76' and not report['errors']
    assert report['baselineCheckpoint'] == 75 and report['sameProcess'] is True
    assert report['rawInputUnchanged'] is True and report['completeQueueParity'] is True
    assert report['fixtures'] == len(report['rows']) == 8 and {r['name'] for r in report['rows']} == CASES
    assert report['pairsPerFixture'] == 12 and report['warmBuildsPerBranch'] == 2
    frequency = report['stopwatchFrequency']
    assert isinstance(frequency, int) and frequency > 0
    previous_frame = -1
    for row in report['rows']:
        assert len(row['pairs']) == 12
        assert re.fullmatch('[0-9a-f]{64}', row['turnHash']) and re.fullmatch('[0-9a-f]{64}', row['finalHash'])
        for index, pair in enumerate(row['pairs']):
            assert pair['index'] == index and pair['baselineFirst'] is (index % 2 == 0)
            assert pair['frame'] > previous_frame
            previous_frame = pair['frame']
            a, b = ('baseline', 'current') if pair['baselineFirst'] else ('current', 'baseline')
            assert 0 < pair[a + 'StartedTicks'] <= pair[a + 'FinishedTicks'] <= pair[b + 'StartedTicks'] <= pair[b + 'FinishedTicks']
            for mode in ['baseline', 'current']:
                expected = (pair[mode + 'FinishedTicks'] - pair[mode + 'StartedTicks']) * 1000 / frequency
                assert math.isfinite(pair[mode + 'Ms']) and pair[mode + 'Ms'] >= 0
                assert abs(pair[mode + 'Ms'] - expected) <= .000001
                assert pair[mode + 'Gc0After'] >= pair[mode + 'Gc0Before'] >= 0
            assert pair[b + 'Gc0Before'] >= pair[a + 'Gc0After']
            assert pair['rawUnchanged'] is True and pair['queueParity'] is True
            assert pair['rawBeforeHash'] == pair['rawAfterHash'] == row['turnHash']
            assert pair['baselineQueueHash'] == pair['currentQueueHash']
            assert re.fullmatch('[0-9a-f]{64}', pair['baselineQueueHash'])
            assert pair['baselinePhases'] == pair['currentPhases'] > 0
        for mode in ['baseline', 'current']:
            values = sorted(p[mode + 'Ms'] for p in row['pairs'])
            assert abs(row[mode + 'MedianMs'] - statistics.median(values)) <= .000001
            assert abs(row[mode + 'P95Ms'] - values[math.ceil(len(values) * .95) - 1]) <= .000001
            assert abs(row[mode + 'MaxMs'] - max(values)) <= .000001
    assert 'Archived queues never enter GameplayScreen' in report['scope']
    return {'fixtures': 8, 'pairs': 96, 'builds': 192,
            'scope': 'Pure construction CPU only; same-process balanced order reduces separate-process confounds. '
                     'Elapsed spans still include development/debug and OS scheduling; no rendering, input-latency, '
                     'allocation-saving or universal speedup conclusion.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    assert args.serial == 'emulator-5556', 'Dedicated QA instance only'
    out = args.out.resolve()
    assert out.is_relative_to((ROOT / 'Verification/Evidence').resolve()), 'Evidence path leaves the workspace evidence root'
    out.mkdir(parents=True, exist_ok=True)

    def adb(*cmd, check=True):
        return subprocess.run([str(ADB), '-s', args.serial, *map(str, cmd)], capture_output=True,
                              check=check, timeout=180).stdout

    def state():
        names = adb('shell', 'run-as', PKG, 'ls', 'shared_prefs').decode().split()
        prefs = {n: adb('shell', 'run-as', PKG, 'sha256sum', 'shared_prefs/' + n).decode().split()[0]
                 for n in names if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', n)}
        names = adb('shell', 'find', REMOTE + '/Profiles', '-type', 'f', '-name', '*.json', check=False).decode().splitlines()
        saves = {n.removeprefix(REMOTE + '/'): adb('shell', 'sha256sum', n).decode().split()[0]
                 for n in names if re.fullmatch(re.escape(REMOTE) + r'/Profiles/[A-Za-z0-9_./-]+\.json', n)}
        return {'preferences': prefs, 'saves': saves}

    assert adb('get-state').strip() == b'device'
    adb('shell', 'am', 'force-stop', PKG)
    before = state()
    started = datetime.now(timezone.utc)
    digest = hashlib.sha256(APK.read_bytes()).hexdigest()
    record = {'utc': started.isoformat(), 'serial': args.serial, 'apk_sha256': digest,
              'before': before, 'scope': 'Single opt-in process; isolated memory onboarding and pure BoardModel turns. '
              'No live attempt/progression owner or archived queue is submitted to gameplay. Actual preference/save hashes '
              'are audited; no data reset, screen input, rendering timing or physical-device certification.'}
    failure = None
    try:
        if args.install:
            record['install'] = adb('install', '-r', APK).decode().strip()
            assert 'Success' in record['install'] and state() == before
        else:
            record['install'] = 'EXACT_INSTALLED_APK_HASH_VERIFIED_NO_REINSTALL'
        remote_apk = adb('shell', 'pm', 'path', PKG).decode().splitlines()[0].removeprefix('package:').strip()
        record['installed_apk_sha256'] = adb('shell', 'sha256sum', remote_apk).decode().split()[0]
        assert record['installed_apk_sha256'] == digest, 'Wrong installed APK'
        request = ROOT / '.verification-cache/Gameplay76/SmoothnessCommandRequest'
        request.parent.mkdir(parents=True, exist_ok=True)
        request.write_text('run', encoding='ascii')
        adb('shell', 'rm', '-f', REMOTE + '/SmoothnessCommand/Report.json')
        adb('push', request, REMOTE + '/HOTR_RunSmoothnessCommand')
        record['launch'] = adb('shell', 'am', 'start', '-W', '-n', PKG + '/com.unity3d.player.UnityPlayerActivity').decode().strip()
        record['pid'] = adb('shell', 'pidof', PKG).decode().strip()
        deadline = time.monotonic() + 360
        while time.monotonic() < deadline:
            raw = adb('shell', 'cat', REMOTE + '/SmoothnessCommand/Report.json', check=False)
            try:
                report = json.loads(raw)
            except (ValueError, UnicodeError):
                time.sleep(1)
                continue
            if datetime.fromisoformat(report['utc'].replace('Z', '+00:00')) >= started and report['status'] != 'RUNNING':
                (out / 'Report.json').write_bytes(raw)
                record['validated'] = validate_report(report)
                break
            time.sleep(1)
        else:
            raise TimeoutError('Fresh construction report unavailable')
        logs = adb('logcat', '-d', '--pid=' + record['pid'], '-v', 'brief').decode(errors='replace')
        (out / 'Player.log').write_text(logs, encoding='utf-8')
        record['runtime_errors'] = len(re.findall(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException', logs))
        assert record['runtime_errors'] == 0
    except Exception as error:
        failure = error
        record['error'] = str(error)
    finally:
        adb('shell', 'am', 'force-stop', PKG, check=False)
        record['after'] = state()
        record['data_unchanged'] = record['before'] == record['after']
        record['finishedUtc'] = datetime.now(timezone.utc).isoformat()
        record['status'] = 'PASS_SAME_APK_COMMAND_DEVICE_AUDIT76' if failure is None and record['data_unchanged'] else 'FAIL_SAME_APK_COMMAND_DEVICE_AUDIT76'
        (out / 'Installation.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    if failure is not None:
        raise failure
    assert record['data_unchanged'], 'Construction probe changed real saved data'
    print(json.dumps({'status': record['status'], 'apk_sha256': digest,
                      'validated': record['validated'], 'data_unchanged': True}, indent=2))


if __name__ == '__main__':
    main()
