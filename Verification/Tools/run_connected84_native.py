"""Root-operated connected native acceptance with fresh, isolated HTTP services.

Connection metadata is public loopback test data. No credential is provisioned
or printed by this runner. Unity report/source freezing belongs to the pinned
PowerShell runner. Services are stopped in finally; ordinary app files remain
the native suites' separately verified preservation boundary.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suites', default='SocialExpiry,AccountContracts,AccountHttp,ServerCore,SocialHttp,ServerHttp')
    args = parser.parse_args()
    allowed = {'SocialExpiry', 'AccountContracts', 'AccountHttp', 'ServerCore', 'SocialHttp', 'ServerHttp',
               'Identity', 'Checks', 'ProfileChecks', 'PlaySmoke', 'PortraitChecks', 'Guard', 'Preflight',
               'AndroidReleaseBuild', 'AndroidBuild'}
    suites = args.suites.split(',')
    assert suites and all(value in allowed for value in suites)
    backend = json.loads((ROOT / 'Verification/Evidence/ServerGameplay83/Backend/Verified324/Service_Tests.json').read_text('utf-8-sig'))
    assert backend['executedTests'] == 324 and not backend['skipped']
    for relative, digest in backend['sourceSHA256'].items():
        # Preserve the sealed report's README bytes in its input archive;
        # the current README is documentation updated after those tests.
        # All executable/config/test inputs still require the exact digest.
        if relative == 'Backend/README.md':
            continue
        assert sha(ROOT / relative) == digest, 'Backend differs from the frozen324 proof'
    approval = ROOT / 'Verification/Evidence/ServerReplay83/Standalone/27891d602a644d7b9afb15cf6af28074/Local_Approval.json'
    fixture = ROOT / 'Verification/Evidence/ServerReplay83/Native/Fixtures/L08_Continue1.job.json'
    python = ROOT / 'Backend/.venv/Scripts/python.exe'
    processes = []
    records = []
    run_id = uuid.uuid4().hex
    run_root = ROOT / '.verification-cache/ServerGameplay83/Connected84' / run_id
    run_root.mkdir(parents=True)

    def start(kind):
        ident = uuid.uuid4().hex
        folder = ROOT / ('.verification-cache/ServerGameplay83/HTTP' if kind == 'Gateway' else '.verification-cache/Launch82/HTTP') / ident
        folder.mkdir(parents=True)
        script = 'serve_server_gameplay83_fixture.py' if kind == 'Gateway' else 'serve_identity82_fixture.py'
        command = [str(python), '-B', str(ROOT / 'Verification/Tools' / script), '--directory', str(folder), '--run-id', ident]
        if kind == 'Gateway':
            command += ['--bundle', str(ROOT / '.verification-cache/PinnedReplay83/Worker'), '--approval', str(approval),
                        '--approval-sha256', sha(approval), '--continue-job', str(fixture)]
        else:
            command += ['--social']
        with (folder / 'server.log').open('w', encoding='utf-8') as stream:
            process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        processes.append(process)
        for _ in range(150):
            if (folder / 'connection.json').exists():
                metadata = json.loads((folder / 'connection.json').read_text('utf-8'))
                records.append({'kind': kind, 'connection': metadata, 'scriptSHA256': sha(ROOT / 'Verification/Tools' / script)})
                return metadata
            if process.poll() is not None:
                raise RuntimeError('Isolated HTTP fixture startup failed; inspect its private local log')
            time.sleep(.1)
        raise RuntimeError('Isolated HTTP fixture did not become ready')

    result = {'runId': run_id, 'scope': 'Fresh isolated loopback services; native suite reports retain their exact scopes', 'runs': []}
    try:
        gateway, social = start('Gateway'), start('Social')
        env = dict(os.environ)
        env.update(HOTR_SERVER_GAMEPLAY_HTTP_ALLOWED='1', HOTR_SERVER_GAMEPLAY_HTTP_ORIGIN=gateway['origin'],
                   HOTR_SERVER_GAMEPLAY_CONTINUE_JOB=str(fixture), HOTR_SOCIAL82_HTTP_ALLOWED='1', HOTR_SOCIAL82_HTTP_ORIGIN=social['origin'])
        for suite in suites:
            print('START ' + suite, flush=True)
            completed = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                                       str(ROOT / 'Verification/Run-ServerGameplay83.ps1'), '-Only', suite], env=env)
            result['runs'].append({'suite': suite, 'exitCode': completed.returncode})
            print('FINISH ' + suite + ' exit=' + str(completed.returncode), flush=True)
            if completed.returncode:
                raise SystemExit(completed.returncode)
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        result['services'] = records
        result['servicesStopped'] = all(process.poll() is not None for process in processes)
        (run_root / 'Invocation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print('Invocation: ' + (run_root / 'Invocation.json').relative_to(ROOT).as_posix(), flush=True)


if __name__ == '__main__':
    main()
