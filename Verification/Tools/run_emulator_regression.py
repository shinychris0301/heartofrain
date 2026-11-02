"""Run the opt-in development suite on one explicitly selected emulator.

Reinstalls with -r, preserves preferences, and relaunches normal gameplay after
collecting evidence. Never clears data, uninstalls, or touches other packages.
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import time
from pathlib import Path
from qa_android_target import validate_qa_target, assert_no_active_attempt

ROOT = Path(__file__).resolve().parents[2]
ADB = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
PACKAGE = 'com.heartoftherain.verification'
REMOTE = f'/sdcard/Android/data/{PACKAGE}/files'


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True, help='Explicit serial of the dedicated authorized emulator.')
    parser.add_argument('--out', type=Path, default=ROOT/'Verification/Evidence/Regression/LDPlayer')
    parser.add_argument('--timeout-minutes', type=int, default=35)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--attach', action='store_true', help='Resume collecting an already running suite after an ADB reconnect.')
    args = parser.parse_args()
    target = validate_qa_target(args.serial,args.out)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    apk = ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'

    def adb(*command, binary=False, check=True):
        for attempt in range(4):
            result = subprocess.run([str(ADB), '-s', args.serial, *command],
                                    capture_output=True, timeout=90)
            error=result.stderr.decode('utf-8','replace')
            if result.returncode and ('not found' in error or 'offline' in error):
                endpoint=args.serial if ':' in args.serial else '127.0.0.1:'+str(int(args.serial.removeprefix('emulator-'))+1)
                subprocess.run([str(ADB),'connect',endpoint],capture_output=True,timeout=30)
                time.sleep(1)
                continue
            break
        if check and result.returncode:
            raise RuntimeError(result.stderr.decode('utf-8', 'replace') or result.stdout.decode('utf-8', 'replace'))
        return result.stdout if binary else result.stdout.decode('utf-8', 'replace').strip()

    started = dt.datetime.now(dt.timezone.utc)
    if args.attach:
        record=json.loads((out/'Installation.json').read_text(encoding='utf-8'))
        started=dt.datetime.fromisoformat(record['utc'])
    assert adb('get-state') == 'device', 'Selected emulator is not authorized'
    attempt_guard=assert_no_active_attempt(adb,PACKAGE)
    record = {'utc': started.isoformat(), 'serial': args.serial, 'package': PACKAGE,
              'qa_target': target, 'attempt_guard': attempt_guard,
              'apk': str(apk), 'sha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
              'android': adb('shell', 'getprop', 'ro.build.version.release'),
              'abi': adb('shell', 'getprop', 'ro.product.cpu.abilist'),
              'native_bridge': adb('shell', 'getprop', 'ro.dalvik.vm.native.bridge'),
              'scope': 'LDPlayer emulator execution with ARM translation; not physical ARM64 certification.'}
    if args.install and not args.attach:
        record['install'] = adb('install', '-r', str(apk))
        assert 'Success' in record['install']
    if not args.attach:
        adb('shell', 'am', 'force-stop', PACKAGE)
        time.sleep(5)
        marker = out/'HOTR_RunRegression'
        marker.write_text(started.isoformat(), encoding='utf-8')
        adb('shell', 'mkdir', '-p', REMOTE)
        adb('push', str(marker), REMOTE+'/HOTR_RunRegression')
        record['launch'] = adb('shell', 'am', 'start', '-W', '-n', PACKAGE+'/com.unity3d.player.UnityPlayerActivity')
        (out/'Installation.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    deadline = time.monotonic()+args.timeout_minutes*60
    next_progress = 0
    while time.monotonic() < deadline:
        body = adb('shell', 'cat', REMOTE+'/Regression/Regression.json', check=False)
        try:
            report = json.loads(body)
            fresh = dt.datetime.fromisoformat(report['utc'].replace('Z', '+00:00')) >= started
        except (ValueError, KeyError):
            report, fresh = {}, False
        if fresh:
            if time.monotonic() >= next_progress:
                print(json.dumps({key: report.get(key) for key in ['status', 'checks', 'labels', 'clips', 'actions', 'boards']}), flush=True)
                next_progress = time.monotonic()+30
            if report['status'] != 'RUNNING':
                adb('pull', REMOTE+'/Regression/.', str(out))
                (out/'Final_Screen.png').write_bytes(adb('exec-out', 'screencap', '-p', binary=True))
                pid = adb('shell', 'pidof', PACKAGE)
                logs = adb('logcat', '-d', '--pid='+pid, '-t', '10000')
                (out/'Player.log').write_text(logs, encoding='utf-8')
                # Close transient fixtures and return the installed app to its
                # normal saved onboarding/settings state for the user's testing.
                adb('shell', 'am', 'force-stop', PACKAGE)
                # LDPlayer can still be closing its old Android window after
                # force-stop returns. Avoid racing the next process attachment.
                time.sleep(5)
                adb('shell', 'am', 'start', '-n', PACKAGE+'/com.unity3d.player.UnityPlayerActivity')
                time.sleep(3)
                if not adb('shell','pidof',PACKAGE,check=False):
                    raise RuntimeError('Native suite finished, but the normal app relaunch needs inspection. Evidence has been collected.')
                print(json.dumps({'status': report['status'], 'failures': report.get('failures'), 'evidence': str(out)}), flush=True)
                return 0 if report['status'] == 'PASS_NATIVE_REGRESSION' else 1
        time.sleep(5)
    raise TimeoutError('Emulator suite did not finish; inspect LDPlayer and its current player log.')


if __name__ == '__main__':
    raise SystemExit(run())
