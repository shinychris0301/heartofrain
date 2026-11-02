"""Run the fixed, isolated Android IL2CPP model fixture on sealed QA2 only."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from qa_android_target import assert_no_active_attempt, validate_qa_target

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / '.verification-cache/ServerReplay83Android/Project'
OUT = ROOT / 'Verification/Evidence/ServerReplay83/Android'
SDK = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK')
ADB = SDK / 'platform-tools/adb.exe'
PACKAGE = 'com.heartoftherain.replay83fixture'
ORDINARY = 'com.heartoftherain.verification'
SERIAL = 'emulator-5558'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    target = validate_qa_target(SERIAL)
    apk = PROJECT / 'Build/Replay83.apk'
    preparation_path, build_path = PROJECT / 'Preparation.json', PROJECT / 'Build/Build.json'
    preparation, build = (json.loads(p.read_text('utf-8')) for p in (preparation_path, build_path))
    assert preparation['package'] == build['package'] == PACKAGE
    assert build['status'] == 'PASS_ANDROID_REPLAY83_ASSEMBLY' and build['errors'] == 0
    assert build['il2cpp'] is True and build['development'] is False
    assert build['unity'] == preparation['unity'] == '2022.3.62f3'
    native_path = ROOT / 'Verification/Evidence/ServerReplay83/Native/ReplayNative.json'
    assert sha(native_path) == preparation['nativeReportSHA256']
    index = json.loads((PROJECT / 'Assets/Resources/Replay83/Index.json').read_text('utf-8'))
    assert len(index['fixtures']) == 371

    def verify_sources():
        for relative, expected in preparation['inputSHA256'].items():
            assert sha(PROJECT / relative) == expected, 'Isolated fixture input differs'

    verify_sources()
    aapt = sorted((SDK / 'build-tools').glob('*/aapt.exe'))[-1]
    badging = subprocess.run([str(aapt), 'dump', 'badging', str(apk)], capture_output=True,
                             check=True, timeout=30).stdout.decode('utf-8', 'strict')
    assert re.search(r"^package: name='" + re.escape(PACKAGE) + "'", badging, re.MULTILINE)
    assert "native-code: 'arm64-v8a'" in badging and "sdkVersion:'26'" in badging
    run_id = uuid.uuid4().hex
    scope = 'qa83-' + run_id
    scope_hash = hashlib.sha256(scope.encode()).hexdigest()
    attempt = OUT / 'Runs' / run_id
    attempt.mkdir(parents=True, exist_ok=False)
    report = {'status': 'PENDING_ANDROID_IL2CPP_REPLAY83', 'runId': run_id, 'startedUtc': utc(),
              'qa_serial': SERIAL, 'qa_target': target, 'package': PACKAGE, 'apkSHA256': sha(apk),
              'pinsSHA256': preparation['pinsSHA256'], 'scopeHash': scope_hash, 'errors': [],
              'preparationSHA256': sha(preparation_path), 'buildReportSHA256': sha(build_path),
              'scope': 'Actual release IL2CPP ARM64 fixture versus pinned native full-checkpoint corpus. '
                       'Separate package only; no ordinary gameplay, purchase, banking return or physical-device claim.'}
    before = None
    phase = 'target_readiness'

    def adb(*parts, check=True, timeout=30):
        result = subprocess.run([str(ADB), '-s', SERIAL, *parts], capture_output=True, timeout=timeout)
        if check and result.returncode:
            raise RuntimeError('ADB_NONZERO')
        return result

    def ordinary_state():
        base = '/sdcard/Android/data/' + ORDINARY + '/files'
        names = adb('shell', 'run-as', ORDINARY, 'ls', 'shared_prefs').stdout.decode().split()
        prefs = {}
        for name in names:
            if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', name):
                prefs[name] = adb('shell', 'run-as', ORDINARY, 'sha256sum', 'shared_prefs/' + name).stdout.decode('ascii').split()[0]
        names = adb('shell', 'find', base + '/Profiles', '-type', 'f', '-name', '*.json').stdout.decode().splitlines()
        saves = {}
        for name in names:
            if re.fullmatch(re.escape(base) + r'/Profiles/[A-Za-z0-9_./-]+\.json', name):
                saves[name.removeprefix(base + '/')] = adb('shell', 'sha256sum', name).stdout.decode('ascii').split()[0]
        assert prefs and saves
        assert all(re.fullmatch('[0-9a-f]{64}', v) for v in [*prefs.values(), *saves.values()])
        return {'preferences': prefs, 'saves': saves}

    try:
        until = time.monotonic() + 20
        while adb('get-state', check=False, timeout=5).stdout.strip() != b'device':
            assert time.monotonic() < until, 'Sealed QA2 unavailable'
            time.sleep(.5)
        phase = 'ordinary_active_attempt_guard'
        report['ordinaryAttemptGuard'] = assert_no_active_attempt(lambda *parts: adb(*parts).stdout.decode('utf-8'))
        before = ordinary_state()
        report['ordinaryDataBefore'] = before
        phase = 'fixture_install'
        assert b'Success' in adb('install', '-r', str(apk), timeout=180).stdout
        adb('shell', 'am', 'force-stop', PACKAGE)
        phase = 'fixture_start'
        assert not adb('shell', 'pidof', PACKAGE, check=False).stdout.strip()
        adb('shell', 'am', 'start', '-n', PACKAGE + '/com.unity3d.player.UnityPlayerActivity',
            '--es', 'replay83_scope', scope)
        phase = 'fixture_report'
        remote = '/sdcard/Android/data/' + PACKAGE + '/files/Replay83/Report.json'
        end = time.monotonic() + 240
        result = None
        while time.monotonic() < end:
            raw = adb('exec-out', 'cat', remote, check=False, timeout=5).stdout
            if 0 < len(raw) < 500_000:
                try:
                    value = json.loads(raw.decode('utf-8'))
                    if value.get('scopeHash') == scope_hash:
                        result = value
                        (attempt / 'Device_Report.json').write_bytes(raw)
                        break
                except (ValueError, UnicodeError):
                    pass
            time.sleep(1)
        assert result is not None, 'Current bounded fixture report missing'
        report['deviceReportSHA256'] = sha(attempt / 'Device_Report.json')
        report['deviceStatus'] = result['status']
        report['deviceError'] = result.get('error')
        phase = 'full_checkpoint_validation'
        assert result['status'] == 'PASS_ANDROID_IL2CPP_REPLAY83_FULL_NATIVE_CORPUS'
        assert result.get('error') in ('', None) and result['androidIl2cpp'] is True
        assert result['unity'] == '2022.3.62f3' and result['pinsSHA256'] == preparation['pinsSHA256']
        assert result['ordinaryGameMutated'] is False
        assert result['levels'] == 50 and result['tools'] == 20 and result['continues'] == 1
        assert len(result['cases']) == len(index['fixtures']) == 371
        for case, fixture in zip(result['cases'], index['fixtures']):
            expected = json.loads((PROJECT / 'Assets/Resources/Replay83/Expected' / (fixture['name'] + '.bytes')).read_text())
            assert case == {'name': fixture['name'], 'checkpointSHA256': expected['checkpointSHA256'],
                            'outcome': expected['outcome'], 'actions': expected['actions']}
        assert adb('shell', 'pidof', PACKAGE).stdout.decode('ascii').strip() == str(result['pid'])
        verify_sources()
        assert sha(apk) == report['apkSHA256']
        report.update({'status': 'PASS_ACTUAL_ANDROID_IL2CPP_REPLAY83_FULL_NATIVE_CORPUS',
                       'cases': 371, 'levels': 50, 'actions': result['actions'], 'tools': 20,
                       'continues': 1, 'pid': result['pid'], 'starting': result['starting']})
    except Exception as error:
        report['status'] = 'FAIL_ACTUAL_ANDROID_IL2CPP_REPLAY83_FULL_NATIVE_CORPUS'
        report['errors'].append(type(error).__name__)
        report['failurePhase'] = phase
    finally:
        if before is not None:
            try:
                after = ordinary_state()
                report['ordinaryDataAfter'] = after
                report['ordinaryDataUnchanged'] = before == after
                if before != after:
                    report['errors'].append('OrdinaryDataChanged')
            except Exception:
                report['errors'].append('OrdinaryDataAfterAuditUnavailable')
        try:
            adb('shell', 'am', 'force-stop', PACKAGE, check=False)
        except Exception:
            report['errors'].append('FixtureStopUnavailable')
        if report['errors']:
            report['status'] = 'FAIL_ACTUAL_ANDROID_IL2CPP_REPLAY83_FULL_NATIVE_CORPUS'
        report['finishedUtc'] = utc()
        (attempt / 'Report.json').write_text(json.dumps(report, indent=2) + '\n')
        summary = OUT / 'Report.json'
        if summary.exists():
            (attempt / 'PriorSummary.json').write_bytes(summary.read_bytes())
        summary.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'cases': report.get('cases', 0), 'out': str(attempt)}))
    return 0 if report['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
