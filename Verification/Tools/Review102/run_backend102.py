"""Current complete backend checks with the previously approved replay worker.

This operator must be invoked only after root releases the combined source
freeze. Raw logs remain private. It never builds or updates an ordinary app.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import OwnedJob, sha, utc, write, freeze
sys.path.insert(0, str(ROOT / 'Verification/Tools/Review93'))
from run_connected import resume_owned_primary

APPROVAL = ROOT / 'Verification/Evidence/ServerGameplay83/Backend/Verified324/Local_Approval.json'
APPROVAL_SHA = 'cffc33acb67c7e8d3c7c77b5d9f52bcaeb37920a44975143c7cfa638021d8c43'
WORKER = ROOT / '.verification-cache/PinnedReplay83/Worker'


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


def validate_worker():
    if sha(APPROVAL) != APPROVAL_SHA:
        raise ValueError('OriginalReplayApprovalRequired102')
    approval = json.loads(APPROVAL.read_text('utf-8'))
    if approval.get('executable') != 'PinnedReplayWorker.exe' or len(approval.get('files', {})) != 176:
        raise ValueError('ExactApprovedReplayBundleRequired102')
    for relative, digest in approval['files'].items():
        path = (WORKER / relative).resolve()
        if not path.is_relative_to(WORKER.resolve()) or not path.is_file() or sha(path) != digest:
            raise ValueError('ApprovedReplayInputChanged102')
    return len(approval['files'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt' or not re.fullmatch('[A-Za-z0-9_]{1,32}', args.tag):
        parser.error('Explicit fresh bounded Windows run required')
    approved_files = validate_worker()
    output = ROOT / 'Verification/Evidence/Review102/Backend' / args.tag
    private = ROOT / '.verification-cache/Review102/Backend' / args.tag
    output.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    before = freeze()
    write(output / 'MainSources_before.json', before)
    environment = dict(os.environ)
    environment.update(HOTR_BACKEND_MODE='local', HOTR_VK_ID_ENABLED='0', HOTR_REPLAY_INTEGRATION='1',
        HOTR_REPLAY_BUNDLE=str(WORKER), HOTR_REPLAY_APPROVAL_FILE=str(APPROVAL),
        HOTR_REPLAY_APPROVAL_SHA256=APPROVAL_SHA,
        HOTR_REPLAY_NATIVE_FIXTURE_ROOT=str(ROOT / 'Verification/Evidence/ServerReplay83/Native'))
    started = time.monotonic()
    record = dict(schemaVersion=1, status='RUNNING_FULL_BACKEND102', startedUtc=utc(),
        runner=bind(Path(__file__)), approvalSHA256=APPROVAL_SHA, approvedWorkerFiles=approved_files,
        scope='Current full Python/SQLite/ASGI tests plus the unchanged explicitly approved actual replay worker. Provider HTTP fixtures remain simulated. No Unity Editor, app build, ordinary profile, Android device, live VK/provider, deployment or production acceptance.')
    write(output / 'Authorization.json', record)
    process = job = None
    try:
        job = OwnedJob()
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        console = private / 'Console.log'
        with console.open('xb') as stream:
            process = subprocess.Popen([str(ROOT / 'Backend/.venv/Scripts/python.exe'), '-B',
                str(ROOT / 'Backend/tools/run_tests.py'), '--out', str(output)], cwd=ROOT,
                env=environment, stdout=stream, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW | 0x4, startupinfo=startup)
            record['pid'] = process.pid
            job.assign(process.pid)
            resume_owned_primary(process)
            record['ownedJobAssignedBeforeResume'] = True
            print(json.dumps(dict(status='STARTED_FULL_BACKEND102', tag=args.tag)), flush=True)
            try:
                process.wait(timeout=900)
            except subprocess.TimeoutExpired:
                record['timedOut'] = True
                job.close()
                process.wait(timeout=20)
        report_path = output / 'Service_Tests.json'
        report = json.loads(report_path.read_text('utf-8')) if report_path.is_file() else {}
        changed = []
        for relative, digest in report.get('sourceSHA256', {}).items():
            source = (ROOT / relative).resolve()
            if not source.is_relative_to((ROOT / 'Backend').resolve()) or not source.is_file() or sha(source) != digest:
                changed.append(relative)
                continue
            archive = output / 'Inputs' / relative
            archive.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, archive)
        worker_unchanged = validate_worker() == approved_files
        good = (process.returncode == 0 and not record.get('timedOut') and
                report.get('status') == 'PASS_BACKEND_SERVICE_TESTS' and
                report.get('actualPinnedWorkerIntegration') is True and
                report.get('executedTests', 0) >= 500 and
                not any(report.get(key) for key in ('skipped', 'failures', 'errors', 'sourceInputsChangedDuringRun')) and
                not changed and worker_unchanged)
        record.update(status='PASS_FULL_BACKEND102_WITH_APPROVED_WORKER' if good else 'FAIL_FULL_BACKEND102',
            exitCode=process.returncode, executedTests=report.get('executedTests', 0),
            failures=len(report.get('failures', [])), errors=len(report.get('errors', [])),
            skips=len(report.get('skipped', [])), actualPinnedWorkerIntegration=report.get('actualPinnedWorkerIntegration', False),
            archivedSourceChanges=changed, approvedWorkerUnchanged=worker_unchanged,
            serviceReport=bind(report_path) if report_path.is_file() else None,
            privateConsole=bind(console))
    except Exception as error:
        record.update(status='FAIL_FULL_BACKEND102_RUNNER', errorType=type(error).__name__)
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=20)
        after = freeze()
        write(output / 'MainSources_after.json', after)
        record.update(mainInputsUnchanged=before == after, finishedUtc=utc(),
                      seconds=round(time.monotonic() - started, 3))
        if not record['mainInputsUnchanged']:
            record['status'] = 'FAIL_FULL_BACKEND102_MAIN_INPUTS_CHANGED'
        write(output / 'Invocation.json', record)
    print(json.dumps(dict(status=record['status'], executedTests=record.get('executedTests', 0),
                         report=(output / 'Invocation.json').relative_to(ROOT).as_posix())), flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
