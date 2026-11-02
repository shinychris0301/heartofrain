"""Explicit isolated identity fixture only; no ordinary game/reset/log reads.

This tool installs one fixed fixture package on the sealed QA2 target, obtains
redacted probe reports and requires distinct Android processes for persistence.
The importable validator performs no Android or file-system operations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from qa_android_target import validate_qa_target, assert_no_active_attempt

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / '.verification-cache/Launch82/AndroidIdentityProject'
OUT = ROOT / 'Verification/Evidence/Launch82/Android'
SDK = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK')
ADB = SDK / 'platform-tools/adb.exe'
PACKAGE = 'com.heartoftherain.identity82fixture'
ORDINARY_PACKAGE = 'com.heartoftherain.verification'
ACTIVITY = PACKAGE + '/com.unity3d.player.UnityPlayerActivity'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def validate_stage(report, envelope, stage, scope_hash, record_hash):
    """Strict I/O-free validation; no hardware-backing requirement or claim."""
    assert stage in ('setup', 'reopen', 'clear')
    assert report['status'] == 'PASS_NATIVE_ANDROID_IDENTITY82_' + stage.upper()
    assert report['errors'] == [] and report['stage'] == stage and report['unity'] == '2022.3.62f3'
    assert report['scopeHash'] == scope_hash and digest(scope_hash)
    assert digest(report['publicKeyHash']) and report['recordHash'] == record_hash
    assert report['androidKeystore'] is True
    assert report['privateKeyNonexportable'] is True and report['encryptionKeyNonexportable'] is True
    assert type(report['hardwareBacked']) is bool
    assert report['recordExists'] is (stage != 'clear')
    expected_checks = {'setup': 8, 'reopen': 7, 'clear': 9}[stage]
    assert type(report['checks']) is int and report['checks'] == expected_checks
    assert len(report['passed']) == len(set(report['passed'])) == expected_checks
    assert 'Actual Android DER signature verifies' in report['passed']
    assert 'Changed message signature fails' in report['passed']
    assert 'Stale CAS rejected without overwrite' in report['passed']
    assert envelope['status'] == report['status'] and envelope['stage'] == stage
    assert envelope['scopeHash'] == scope_hash
    assert type(envelope['pid']) is int and envelope['pid'] > 0
    assert envelope['reportPath'] == 'Identity82/Reports/Identity82_' + stage + '.json'
    return {'stage': stage, 'pid': envelope['pid'], 'checks': report['checks'],
            'publicKeyHash': report['publicKeyHash'], 'recordHash': record_hash,
            'recordExists': report['recordExists'], 'hardwareBacked': report['hardwareBacked']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', default='emulator-5558')
    parser.add_argument('--apk', type=Path, default=FIXTURE / 'Build/Identity82.apk')
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--adb', type=Path, default=ADB)
    parser.add_argument('--aapt', type=Path)
    args = parser.parse_args()
    assert args.serial == 'emulator-5558', 'Only explicitly isolated QA2 may run this fixture'
    target = validate_qa_target(args.serial)
    out = args.out.resolve()
    assert out.is_relative_to((ROOT / 'Verification/Evidence/Launch82').resolve())
    apk = args.apk.resolve()
    assert apk.is_relative_to(FIXTURE.resolve()) and apk.is_file(), 'Only the isolated fixture APK may be installed'
    assert PACKAGE != 'com.heartoftherain.verification'
    preparation_path = FIXTURE / 'Preparation.json'
    build_path = FIXTURE / 'Build/Build.json'
    preparation = json.loads(preparation_path.read_text('utf-8'))
    build = json.loads(build_path.read_text('utf-8'))
    assert preparation['status'] == 'PREPARED_ISOLATED_IDENTITY82_ANDROID_PROJECT_NOT_BUILT'
    assert preparation['unity'] == build['unity'] == '2022.3.62f3'
    assert preparation['package'] == build['package'] == PACKAGE
    assert build['status'] == 'PASS_ISOLATED_IDENTITY82_ANDROID_ASSEMBLY' and build['errors'] == 0
    assert build['development'] is True and build['arm64'] is True
    for relative, expected in preparation['copiedSourceSHA256'].items():
        assert sha(ROOT / relative) == expected, 'Held main source changed after fixture preparation'
    for relative, expected in preparation['generatedSHA256'].items():
        assert sha(FIXTURE / relative) == expected, 'Generated fixture source changed after preparation'
    aapt = args.aapt
    if aapt is None:
        candidates = sorted((SDK / 'build-tools').glob('*/aapt.exe'))
        assert candidates, 'Pinned SDK aapt is required to identify the fixture APK'
        aapt = candidates[-1]
    badging = subprocess.run([str(aapt), 'dump', 'badging', str(apk)], capture_output=True, check=True, timeout=30).stdout.decode('utf-8', 'strict')
    match = re.search(r"^package: name='([^']+)'", badging, re.MULTILINE)
    assert match and match.group(1) == PACKAGE, 'Refuse any APK other than the fixed isolated fixture'
    assert "native-code: 'arm64-v8a'" in badging and "sdkVersion:'26'" in badging
    assert "launchable-activity: name='com.unity3d.player.UnityPlayerActivity'" in badging
    out.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    attempt = out / 'Attempts' / run_id
    attempt.mkdir(parents=True, exist_ok=False)
    # A unique scope is not a credential. Keep its invocation only in ignored
    # cache so a failed test can be inspected without reusing a normal alias.
    scope = 'qa82-' + run_id
    cache_invocation = ROOT / '.verification-cache/Launch82/AndroidRuns' / (run_id + '.json')
    cache_invocation.parent.mkdir(parents=True, exist_ok=True)
    cache_invocation.write_text(json.dumps({'scope': scope, 'serial': args.serial, 'fixturePackage': PACKAGE}), 'utf-8')
    scope_hash = hashlib.sha256(scope.encode('ascii')).hexdigest()
    record_hash = hashlib.sha256(('public-noncredential-qa82-record-v1:' + scope).encode('ascii')).hexdigest()
    report = {'status': 'PENDING_ISOLATED_ANDROID_IDENTITY82', 'utc': utc(), 'runId': run_id,
              'apk_sha256': sha(apk), 'package': PACKAGE, 'qa_serial': args.serial, 'qa_target': target,
              'scopeHash': scope_hash, 'stages': [], 'errors': [], 'artifactSHA256': {},
              'sourceSHA256': preparation['copiedSourceSHA256'],
              'externalSHA256': {preparation_path.relative_to(ROOT).as_posix(): sha(preparation_path),
                                 build_path.relative_to(ROOT).as_posix(): sha(build_path)},
              'scope': 'Actual isolated fixture install/P256 signing/AES-GCM CAS and distinct-process persistence only. The ordinary QA game active-attempt guard and saved-data hash audit are read-only; it is never stopped, cleared or installed by this harness.',
              'limitations': ['No physical-device, OS power-loss, attestation, backend, normal account or production integration claim.']}
    phase = 'target_readiness'
    before = None

    class HarnessFailure(RuntimeError):
        def __init__(self, code, return_code=None):
            self.code, self.return_code = code, return_code
            super().__init__(code)

    def adb(*parts, check=True, timeout=30):
        try:
            result = subprocess.run([str(args.adb), '-s', args.serial, *parts], capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise HarnessFailure('ADB_TIMEOUT') from None
        except OSError:
            raise HarnessFailure('ADB_START_FAILED') from None
        if check and result.returncode:
            raise HarnessFailure('ADB_NONZERO', result.returncode)
        return result

    def ordinary_state():
        base = '/sdcard/Android/data/' + ORDINARY_PACKAGE + '/files'
        names = adb('shell', 'run-as', ORDINARY_PACKAGE, 'ls', 'shared_prefs').stdout.decode('utf-8', 'strict').split()
        prefs = {}
        for name in names:
            if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', name):
                value = adb('shell', 'run-as', ORDINARY_PACKAGE, 'sha256sum', 'shared_prefs/' + name).stdout.decode('ascii').split()[0]
                assert digest(value)
                prefs[name] = value
        names = adb('shell', 'find', base + '/Profiles', '-type', 'f', '-name', '*.json').stdout.decode('utf-8', 'strict').splitlines()
        saves = {}
        for name in names:
            if re.fullmatch(re.escape(base) + r'/Profiles/[A-Za-z0-9_./-]+\.json', name):
                value = adb('shell', 'sha256sum', name).stdout.decode('ascii').split()[0]
                assert digest(value)
                saves[name.removeprefix(base + '/')] = value
        assert prefs and saves, 'Read-only ordinary save audit unavailable'
        return {'preferences': prefs, 'saves': saves}

    def read_json(name):
        assert name in {prefix + stage + '.json' for prefix in ('Identity82_', 'Fixture_') for stage in ('setup', 'reopen', 'clear')}, 'Only redacted report filenames may be read'
        relatives = ['files/Identity82/Reports/' + name,
                     '/sdcard/Android/data/' + PACKAGE + '/files/Identity82/Reports/' + name]
        for remote in relatives:
            result = adb('exec-out', 'run-as', PACKAGE, 'cat', remote, check=False, timeout=5)
            if result.returncode == 0 and 0 < len(result.stdout) <= 65536:
                try:
                    value = json.loads(result.stdout.decode('utf-8'))
                except (ValueError, UnicodeError):
                    continue
                return result.stdout, value, remote
        # Android's run-as context can lack external-storage group access.
        # The shell fallback is restricted to the exact fixed fixture Reports
        # allowlist above; it never reads protected records or account data.
        remote = relatives[1]
        result = adb('exec-out', 'cat', remote, check=False, timeout=5)
        if result.returncode == 0 and 0 < len(result.stdout) <= 65536:
            try:
                value = json.loads(result.stdout.decode('utf-8'))
                return result.stdout, value, remote
            except (ValueError, UnicodeError):
                pass
        return None

    try:
        readiness_end = time.monotonic() + 20
        while True:
            ready = adb('get-state', check=False, timeout=5)
            if ready.returncode == 0 and ready.stdout.strip() == b'device':
                break
            if time.monotonic() >= readiness_end:
                raise HarnessFailure('QA2_NOT_READY_AFTER_BOUNDED_REDISCOVERY', ready.returncode)
            time.sleep(.5)
        phase = 'ordinary_active_attempt_guard'
        report['ordinaryAttemptGuard'] = assert_no_active_attempt(lambda *parts: adb(*parts).stdout.decode('utf-8', 'strict'))
        phase = 'ordinary_state_before'
        before = ordinary_state()
        report['ordinaryDataBefore'] = before
        phase = 'device_properties'
        report['device'] = {name: adb('shell', 'getprop', prop).stdout.decode('utf-8', 'strict').strip()[:128]
                            for name, prop in (('sdk', 'ro.build.version.sdk'), ('android', 'ro.build.version.release'), ('model', 'ro.product.model'))}
        assert int(report['device']['sdk']) >= 26
        phase = 'fixture_install'
        installed = adb('install', '-r', str(apk), timeout=180)
        assert b'Success' in installed.stdout, 'Fixture install did not complete successfully'
        report['installedUtc'] = utc()
        phase = 'fixture_package_path'
        report['installedPath'] = adb('shell', 'pm', 'path', PACKAGE).stdout.decode('utf-8').strip()
        for stage in ('setup', 'reopen', 'clear'):
            phase = stage + '_stop'
            adb('shell', 'am', 'force-stop', PACKAGE)
            # Confirm the preceding process is gone before requesting the next.
            assert not adb('shell', 'pidof', PACKAGE, check=False).stdout.strip()
            phase = stage + '_start'
            adb('shell', 'am', 'start', '-n', ACTIVITY, '--es', 'identity82_scope', scope, '--es', 'identity82_stage', stage)
            phase = stage + '_redacted_report_wait'
            end = time.monotonic() + 90
            pair = None
            while time.monotonic() < end:
                first, second = read_json('Identity82_' + stage + '.json'), read_json('Fixture_' + stage + '.json')
                if first and second and first[1].get('scopeHash') == second[1].get('scopeHash') == scope_hash:
                    pair = (first, second)
                    break
                time.sleep(.5)
            assert pair is not None, 'Bounded isolated fixture stage did not produce current reports'
            for name, item in zip(('Identity82_' + stage + '.json', 'Fixture_' + stage + '.json'), pair):
                path = attempt / name
                path.write_bytes(item[0])
                report['artifactSHA256'][path.relative_to(out).as_posix()] = sha(path)
            phase = stage + '_validate'
            checked = validate_stage(pair[0][1], pair[1][1], stage, scope_hash, record_hash)
            checked['reportRemotePaths'] = [item[2] for item in pair]
            process_pid = adb('shell', 'pidof', PACKAGE).stdout.decode('ascii').strip()
            assert process_pid == str(checked['pid']), 'Stage envelope PID is not the live fixture process'
            report['stages'].append(checked)
        phase = 'cross_process_and_source_validation'
        assert len({r['pid'] for r in report['stages']}) == 3, 'A distinct-process reopen was not demonstrated'
        assert len({r['publicKeyHash'] for r in report['stages']}) == 1, 'P256 identity changed between processes or clear'
        for relative, expected in preparation['copiedSourceSHA256'].items():
            assert sha(ROOT / relative) == expected, 'Main source changed while Android fixture ran'
        assert sha(apk) == report['apk_sha256'], 'Fixture APK changed during execution'
        report['status'] = 'PASS_ISOLATED_ANDROID_IDENTITY82_KEYSTORE_AND_RESTART'
    except Exception as error:
        report['status'] = 'FAIL_ISOLATED_ANDROID_IDENTITY82_KEYSTORE_AND_RESTART'
        # Constant failure type only; never include adb output/Android exception
        # bodies, key material, plaintext protected records or account secrets.
        report['errors'].append(type(error).__name__)
        report['failure'] = {'phase': phase, 'type': type(error).__name__,
                             'code': error.code if isinstance(error, HarnessFailure) else 'ASSERTION_FAILED' if isinstance(error, AssertionError) else 'VALIDATION_OR_IO_FAILED',
                             'returnCode': error.return_code if isinstance(error, HarnessFailure) else None}
    finally:
        if before is not None:
            try:
                after = ordinary_state()
                report['ordinaryDataAfter'] = after
                report['ordinaryDataUnchanged'] = before == after
                if before != after:
                    report['errors'].append('OrdinaryDataChanged')
                    report['status'] = 'FAIL_ISOLATED_ANDROID_IDENTITY82_KEYSTORE_AND_RESTART'
            except Exception:
                report['errors'].append('OrdinaryDataAfterAuditUnavailable')
                report['status'] = 'FAIL_ISOLATED_ANDROID_IDENTITY82_KEYSTORE_AND_RESTART'
        try:
            adb('shell', 'am', 'force-stop', PACKAGE, check=False)
        except (OSError, subprocess.SubprocessError, HarnessFailure):
            report['errors'].append('FixtureStopUnavailable')
            report['status'] = 'FAIL_ISOLATED_ANDROID_IDENTITY82_KEYSTORE_AND_RESTART'
        report['finishedUtc'] = utc()
        (attempt / 'Report.json').write_text(json.dumps(report, indent=2), 'utf-8')
        canonical = out / 'Report.json'
        if canonical.exists():
            prior = out / 'Attempts' / ('prior-summary-' + uuid.uuid4().hex + '.json')
            shutil_copy_bytes = canonical.read_bytes()
            prior.write_bytes(shutil_copy_bytes)
        canonical.write_text(json.dumps(report, indent=2), 'utf-8')
    print(json.dumps({'status': report['status'], 'stages': len(report['stages']), 'out': str(out)}))
    return 0 if report['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
