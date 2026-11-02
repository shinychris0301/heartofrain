"""Validate exact model parity and the separately frozen real broker proof."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/ServerReplay83'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text('utf-8-sig'))


def main():
    native_path = OUT / 'Native/ReplayNative.json'
    native = read(native_path)
    assert native['status'] == 'PASS_PINNED_NATIVE_REPLAY_CORPUS' and not native['error']
    assert (native['checks'], native['cases'], native['levels'], native['actions']) == (3937, 371, 50, 397)
    assert (native['tools'], native['continues'], native['negativeControls']) == (20, 1, 6)
    for case in native['fixtures']:
        assert sha(native_path.parent / case['job']) == case['jobSHA256']
        expected = read(native_path.parent / case['expected'])
        assert expected['checkpointSHA256'] == case['checkpointSHA256']
    standalone_path = OUT / 'Standalone/27891d602a644d7b9afb15cf6af28074/Report.json'
    standalone = read(standalone_path)
    assert standalone['status'] == 'PASS_ACTUAL_PINNED_WINDOWS_WORKER_FULL_NATIVE_CORPUS'
    assert standalone['nativeReportSHA256'] == sha(native_path) and not standalone['errors']
    approval_path = standalone_path.parent / 'Local_Approval.json'
    assert sha(approval_path) == standalone['approvalSHA256']
    approval = read(approval_path)
    assert len(approval['files']) == standalone['bundleFiles'] == 176
    for relative, digest in standalone['sourceSHA256'].items():
        assert sha(standalone_path.parent / 'Inputs' / relative) == digest
    assert len(standalone['cases']) == len(native['fixtures']) == 371
    for case, fixture in zip(standalone['cases'], native['fixtures']):
        assert case['name'] == fixture['name'] and case['checkpointSHA256'] == fixture['checkpointSHA256']
        assert case['process']['exitCode'] == 0 and case['process']['jobObjectEnforced'] is True
    android_path = OUT / 'Android/Report.json'
    android = read(android_path)
    assert android['status'] == 'PASS_ACTUAL_ANDROID_IL2CPP_REPLAY83_FULL_NATIVE_CORPUS'
    assert (android['cases'], android['actions'], android['tools'], android['continues']) == (371, 397, 20, 1)
    assert android['ordinaryDataUnchanged'] and android['ordinaryDataBefore'] == android['ordinaryDataAfter']
    assert android['qa_serial'] == 'emulator-5558' and not android['errors']
    device_path = OUT / 'Android/Runs' / android['runId'] / 'Device_Report.json'
    assert sha(device_path) == android['deviceReportSHA256']
    device = read(device_path)
    assert len(device['cases']) == 371 and device['scopeHash'] == android['scopeHash']
    for case, fixture in zip(device['cases'], native['fixtures']):
        assert case['name'] == fixture['name'] and case['checkpointSHA256'] == fixture['checkpointSHA256']
    build = read(OUT / 'Android/Assembly/Build.json')
    assert build['status'] == 'PASS_ANDROID_REPLAY83_ASSEMBLY' and build['errors'] == 0
    assert build['il2cpp'] is True and build['development'] is False
    assert native['pinsSHA256'] == standalone['pinsSHA256'] == android['pinsSHA256']
    backend_path = OUT / 'Backend/VerifiedIntegration/Service_Tests.json'
    backend = read(backend_path)
    assert backend['status'] == 'PASS_BACKEND_SERVICE_TESTS' and backend['tests'] == len(backend['passed']) == 304
    assert not backend['failures'] and not backend['errors'] and not backend['sourceInputsChangedDuringRun']
    assert backend['sourceSHA256'] == backend['sourceSHA256After']
    integration = 'tests.test_replay_native_integration.NativeReplayBrokerIntegration.test_authenticated_native_full_history_continue_win_recovery'
    assert integration in backend['passed']
    assert read(backend_path.parent / 'Invocation.json')['optInActualModel'] is True
    for relative, digest in backend['sourceSHA256'].items():
        assert sha(backend_path.parent / 'Inputs' / relative) == digest
    artifacts = {p.relative_to(OUT).as_posix(): sha(p) for p in (native_path, standalone_path, approval_path,
                 android_path, device_path, backend_path, OUT / 'Android/Assembly/Build.json')}
    summary = {'status': 'PASS_PINNED_MODEL83_PARITY_AND_REAL_BROKER_WITH_APP_GATES',
               'utc': datetime.now(timezone.utc).isoformat(), 'pinsSHA256': native['pinsSHA256'],
               'nativeChecks': 3937, 'nativeCases': 371, 'windowsCases': 371, 'androidIl2cppCases': 371,
               'levels': 50, 'actions': 397, 'tools': 20, 'continues': 1,
               'backendTests': 304, 'backendInputs': len(backend['sourceSHA256']),
               'actualBrokerOperations': 3, 'actualFirstClearCoins': 50, 'actualFirstClearStars': 1,
               'actualBrokerScope': 'Authenticated ASGI/SQLite with approved real Unity worker; server-owned synthetic seed/progression. OutOfMoves,900/+5,Won,duplicate no extra credit. Not a real network/app/payment test.',
               'artifactSHA256': artifacts, 'ordinaryGameApkCheckpoint': 81,
               'remaining': ['Ordinary connected app lifecycle and pages', 'Future-command parity after restored Continue boards',
                             'Naturally occurring real model fault; current fault positive control is synthetic',
                             'Production hosting, signing, Console and actual store payment acceptance',
                             'Physical devices and gameplay smoothness acceptance']}
    (OUT / 'Summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: summary[k] for k in ('status', 'nativeCases', 'windowsCases', 'androidIl2cppCases', 'backendTests')}))


if __name__ == '__main__':
    main()
