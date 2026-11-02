"""Root-only current86 connected Editor suites against fresh isolated services.

Requires a passing exact current backend suite. Starts only loopback test
services and the already approved Windows gameplay worker. No Console/SDK,
emulator, ordinary profile migration or production activation is involved.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import sha, utc, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend-report', type=Path, required=True)
    args = parser.parse_args()
    backend_path = args.backend_report.resolve()
    backend = json.loads(backend_path.read_text('utf-8-sig'))
    if backend.get('skipped') or backend.get('failures') or backend.get('errors') or backend.get('sourceInputsChangedDuringRun'):
        parser.error('Passing unchanged zero-skip backend proof required')
    if backend.get('executedTests', 0) < 358 or not str(backend.get('status', '')).startswith('PASS'):
        parser.error('Passing complete backend suite required')
    for relative, digest in backend['sourceSHA256'].items():
        if sha(ROOT / relative) != digest:
            parser.error('Backend proof no longer matches current input: ' + relative)
    run = ROOT / 'Verification/Evidence/Review86/ConnectedRuns' / uuid.uuid4().hex
    run.mkdir(parents=True, exist_ok=False)
    approval = ROOT / 'Verification/Evidence/ServerGameplay83/Backend/Verified324/Local_Approval.json'
    fixture = ROOT / 'Verification/Evidence/ServerReplay83/Native/Fixtures/L08_Continue1.job.json'
    python = ROOT / 'Backend/.venv/Scripts/python.exe'
    processes, services = [], []

    def start(kind):
        ident = uuid.uuid4().hex
        base = { 'Gateway': '.verification-cache/ServerGameplay83/HTTP',
                 'Social': '.verification-cache/Launch82/HTTP',
                 'Payment': '.verification-cache/RuStore81' }[kind]
        folder = ROOT / base / ident
        folder.mkdir(parents=True)
        script = ROOT / 'Verification/Tools' / {'Gateway': 'serve_server_gameplay83_fixture.py',
                                              'Social': 'serve_identity82_fixture.py',
                                              'Payment': 'serve_rustore81_fixture.py'}[kind]
        command = [str(python), '-B', str(script), '--directory', str(folder), '--run-id', ident]
        if kind == 'Gateway':
            command += ['--bundle', str(ROOT / '.verification-cache/PinnedReplay83/Worker'),
                        '--approval', str(approval), '--approval-sha256', sha(approval), '--continue-job', str(fixture)]
        elif kind == 'Social':
            command += ['--social']
        with (folder / 'server.log').open('x', encoding='utf-8') as stream:
            process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
        processes.append(process)
        for _ in range(200):
            if (folder / 'connection.json').is_file():
                metadata = json.loads((folder / 'connection.json').read_text('utf-8'))
                public = {key: metadata[key] for key in ('runId', 'origin', 'pid', 'scope') if key in metadata}
                if kind == 'Payment':
                    # This older operator fixture writes a private bearer file.
                    # Only its path is passed to Unity; no bytes are exported.
                    metadata['privateConfigPath'] = str(folder / 'connection.json')
                services.append({'kind': kind, 'connection': public, 'fixtureSHA256': sha(script)})
                return metadata
            if process.poll() is not None:
                raise RuntimeError('FixtureStartupFailed')
            time.sleep(.1)
        raise RuntimeError('FixtureStartupTimedOut')

    result = {'status': 'RUNNING', 'startedUtc': utc(), 'backendReport': backend_path.relative_to(ROOT).as_posix(),
              'backendReportSHA256': sha(backend_path), 'runnerSHA256': sha(Path(__file__)),
              'approvalSHA256': sha(approval), 'continueFixtureSHA256': sha(fixture), 'services': services,
              'scope': 'Current backend and actual Editor HTTP identity/account/social/ordinary-server callers; separate isolated guests and synthetic L8 seed/unlock. Actual pinned Windows worker verifies replay. No Android, payment SDK, public deployment or production certification.'}
    try:
        gateway, social, payment = start('Gateway'), start('Social'), start('Payment')
        env = dict(os.environ)
        env.update(HOTR_SERVER_GAMEPLAY_HTTP_ALLOWED='1', HOTR_SERVER_GAMEPLAY_HTTP_ORIGIN=gateway['origin'],
                   HOTR_SERVER_GAMEPLAY_CONTINUE_JOB=str(fixture), HOTR_SOCIAL82_HTTP_ALLOWED='1', HOTR_SOCIAL82_HTTP_ORIGIN=social['origin'],
                   HOTR_IDENTITY82_HTTP_ALLOWED='1', HOTR_IDENTITY82_HTTP_ORIGIN=social['origin'],
                   HOTR_RUSTORE81_HTTP_CONFIG=payment['privateConfigPath'])
        with (run / 'NativeRunner.log').open('x', encoding='utf-8') as stream:
            child = subprocess.run([str(ROOT / '.venv/Scripts/python.exe'), '-B', str(Path(__file__).with_name('run_native86.py')),
                                    '--suites', 'IdentityHttp,AccountHttp,SocialHttp,ServerHttp,PayHttp'], env=env,
                                   stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW,
                                   timeout=1800)
        result['nativeRunnerExitCode'] = child.returncode
        result['nativeRunnerLogSHA256'] = sha(run / 'NativeRunner.log')
        final_line = (run / 'NativeRunner.log').read_text('utf-8').splitlines()[-1]
        native = json.loads(final_line)
        native_path = (ROOT / native['report']).resolve()
        if not native_path.is_relative_to((ROOT / 'Verification/Evidence/Review86/NativeRuns').resolve()):
            raise RuntimeError('NativeInvocationOutsideScope')
        result['nativeInvocation'] = native_path.relative_to(ROOT).as_posix()
        result['nativeInvocationSHA256'] = sha(native_path)
        result['status'] = 'PASS_CONNECTED_REVIEW86' if child.returncode == 0 else 'FAIL_CONNECTED_REVIEW86'
    except Exception as error:
        result.update(status='FAIL_CONNECTED_REVIEW86', errorType=type(error).__name__)
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        result.update(servicesStopped=all(p.poll() is not None for p in processes), finishedUtc=utc())
        if not result['servicesStopped']:
            result['status'] = 'FAIL_CONNECTED_REVIEW86'
        write(run / 'Invocation.json', result)
        print(json.dumps({'status': result['status'], 'report': (run / 'Invocation.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if result['status'].startswith('PASS') else 1


if __name__ == '__main__':
    raise SystemExit(main())
