"""Validate the frozen checkpoint82 foundation, independently of later edits."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Launch82'
FROZEN = OUT / 'VerifiedFoundation'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text('utf-8-sig'))


def main():
    files = read(FROZEN / 'Source_SHA256.json')['files']
    baseline = read(OUT / 'Baseline81/Source_SHA256.json')['files']
    assert len(files) == 5242 and len(baseline) == 5182
    assert all(files.get(k) == v for k, v in baseline.items())
    archived, unchanged = 0, 0
    for relative, digest in files.items():
        frozen = FROZEN / 'Inputs' / relative
        path = frozen if frozen.exists() else ROOT / relative
        assert sha(path) == digest, 'Frozen foundation input is no longer recoverable: ' + relative
        archived += frozen.exists()
        unchanged += not frozen.exists()
    artifacts = {}
    for mode, name, checks, cases in [('Identity', 'Identity82', 69, 13),
                                     ('IdentityHttp', 'Identity82_HTTP', 25, 8),
                                     ('SocialHttp', 'Social82_HTTP', 65, 7)]:
        path = FROZEN / 'Native' / (name + '.json')
        value = read(path)
        assert value['status'].startswith('PASS_') and value['checks'] == checks and value['cases'] == cases
        assert value['errors'] == [] and value['unity'] == '2022.3.62f3'
        process_path = FROZEN / 'Native' / (mode + '_Process.json')
        process = read(process_path)
        assert process['exitCode'] == 0 and process['timedOut'] is False
        assert process['reportSHA256'] == sha(path)
        log = FROZEN / process['log']
        assert sha(log) == process['logSHA256']
        for key, hash_key in [('sourceManifest', 'sourceSHA256'), ('afterSourceManifest', 'afterSourceSHA256')]:
            source = FROZEN / process[key]
            assert sha(source) == process[hash_key] and read(source)['files'] == files
        for p in (path, process_path, log):
            artifacts[p.relative_to(OUT).as_posix()] = sha(p)
    backend_root = OUT / 'Backend/Verified250'
    backend_path = backend_root / 'Service_Tests.json'
    backend = read(backend_path)
    assert backend['status'] == 'PASS_BACKEND_SERVICE_TESTS' and backend['tests'] == 250
    assert len(backend['passed']) == len(set(backend['passed'])) == 250
    assert not backend['errors'] and not backend['failures'] and not backend['sourceInputsChangedDuringRun']
    assert backend['sourceSHA256'] == backend['sourceSHA256After']
    for relative, digest in backend['sourceSHA256'].items():
        assert sha(backend_root / 'Inputs' / relative) == digest
    android_path = FROZEN / 'Android/Report.json'
    android = read(android_path)
    assert android['status'] == 'PASS_ISOLATED_ANDROID_IDENTITY82_KEYSTORE_AND_RESTART'
    assert android['qa_serial'] == 'emulator-5558' and android['ordinaryDataUnchanged'] is True
    assert android['ordinaryDataBefore'] == android['ordinaryDataAfter'] and not android['errors']
    assert sum(stage['checks'] for stage in android['stages']) == 24
    assert len({stage['pid'] for stage in android['stages']}) == 3
    for relative, digest in android['artifactSHA256'].items():
        assert sha(OUT / 'Android' / relative) == digest
    for p in (backend_path, android_path, FROZEN / 'Source_SHA256.json'):
        artifacts[p.relative_to(OUT).as_posix()] = sha(p)
    summary = {'status': 'PASS_FROZEN_LAUNCH82_FOUNDATION_WITH_INTEGRATION_GATES',
               'utc': datetime.now(timezone.utc).isoformat(), 'historicalCheckpoint': 82,
               'backendTests': 250, 'backendInputs': len(backend['sourceSHA256']),
               'nativeChecks': 159, 'nativeCases': 28, 'androidChecks': 24, 'androidProcesses': 3,
               'unityInputs': len(files), 'unchanged81Inputs': len(baseline), 'newUnityInputs': 60,
               'archivedUnityInputs': archived, 'currentUnchangedInputsUsed': unchanged,
               'artifactSHA256': artifacts, 'ordinaryGameApkCheckpoint': 81,
               'scope': 'Frozen backend/identity/social transport foundation only. Current gateway, worker and connected-page edits are later work and are not certified by this report.',
               'remaining': ['Connected ordinary app services and UI', 'Trusted model replay and authenticated settlement',
                             'Hosted HTTPS and operations', 'RuStore Console/signing/legal configuration',
                             'Actual sandbox, banking return, restart and upgrade verification',
                             'Physical devices and existing gameplay smoothness limitations']}
    (OUT / 'Foundation_Summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k in ('status', 'backendTests', 'nativeChecks', 'androidChecks')}))


if __name__ == '__main__':
    main()
