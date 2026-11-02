"""Root-only complete service tests with the existing approved Windows worker.

Fresh reports/archived inputs only. No ordinary app data, providers or devices.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'Verification/Evidence/RegionalAccounts89'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(EVIDENCE.resolve()) or out == EVIDENCE.resolve():
        parser.error('Fresh checkpoint89 evidence directory required')
    out.mkdir(parents=True, exist_ok=False)
    approval = ROOT / 'Verification/Evidence/ServerGameplay83/Backend/Verified324/Local_Approval.json'
    worker = ROOT / '.verification-cache/PinnedReplay83/Worker'
    environment = dict(os.environ)
    environment.update(HOTR_BACKEND_MODE='local', HOTR_VK_ID_ENABLED='0', HOTR_REPLAY_INTEGRATION='1',
        HOTR_REPLAY_BUNDLE=str(worker), HOTR_REPLAY_APPROVAL_FILE=str(approval),
        HOTR_REPLAY_APPROVAL_SHA256=sha(approval),
        HOTR_REPLAY_NATIVE_FIXTURE_ROOT=str(ROOT / 'Verification/Evidence/ServerReplay83/Native'))
    record = {'status': 'RUNNING', 'startedUtc': utc(), 'runnerSHA256': sha(__file__),
              'approvalSHA256': sha(approval), 'scope': 'Complete Python/ASGI/SQLite service tests with the unchanged, previously approved Windows Unity gameplay worker. No actual provider, ordinary app, Android, public deployment or production acceptance.'}
    write(out / 'Invocation.json', record)
    with (out / 'Console.log').open('x', encoding='utf-8') as stream:
        process = subprocess.run([str(ROOT / 'Backend/.venv/Scripts/python.exe'), '-B',
            str(ROOT / 'Backend/tools/run_tests.py'), '--out', str(out)], env=environment,
            stdout=stream, stderr=subprocess.STDOUT, timeout=600, creationflags=subprocess.CREATE_NO_WINDOW)
    report = json.loads((out / 'Service_Tests.json').read_text('utf-8'))
    changed = []
    for relative, digest in report['sourceSHA256'].items():
        source = (ROOT / relative).resolve()
        if not source.is_relative_to((ROOT / 'Backend').resolve()) or sha(source) != digest:
            changed.append(relative)
            continue
        destination = out / 'Inputs' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    passed = process.returncode == 0 and report['status'] == 'PASS_BACKEND_SERVICE_TESTS' and not report['skipped'] and not changed and report['actualPinnedWorkerIntegration']
    record.update(status='PASS_BACKEND89_FULL_SUITE' if passed else 'FAIL_BACKEND89_FULL_SUITE',
        exitCode=process.returncode, executedTests=report['executedTests'], archiveSourceChanges=changed,
        serviceReportSHA256=sha(out / 'Service_Tests.json'), consoleSHA256=sha(out / 'Console.log'), finishedUtc=utc())
    write(out / 'Invocation.json', record)
    print(json.dumps({'status': record['status'], 'executedTests': record['executedTests'],
                      'failures': report['failures'], 'errors': report['errors'], 'skipped': report['skipped']}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
