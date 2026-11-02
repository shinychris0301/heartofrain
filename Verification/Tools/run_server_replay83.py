"""Run the actual pinned Windows Unity worker against native fixture outcomes.

Approval here is for this local verification only. No player-facing route,
financial grant or production configuration is changed.
"""
import argparse
import hashlib
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Backend'))
from hotr_backend.replay_contract import ApprovedWorker, ReplayError, strict_json


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=0, help='Diagnostic subset only; zero runs the full native corpus')
    args = parser.parse_args()
    if not 0 <= args.limit <= 371:
        raise SystemExit('Invalid bounded diagnostic limit')
    cache = ROOT / '.verification-cache/PinnedReplay83'
    bundle = cache / 'Worker'
    native_path = ROOT / 'Verification/Evidence/ServerReplay83/Native/ReplayNative.json'
    native = json.loads(native_path.read_text('utf-8'))
    build = json.loads((cache / 'Build.json').read_text('utf-8'))
    if native['status'] != 'PASS_PINNED_NATIVE_REPLAY_CORPUS' or build['status'] != 'PASS_PINNED_WINDOWS_REPLAY_BUILD':
        raise SystemExit('Actual native corpus and successful isolated build required')
    if sha(bundle / 'ReplayPins/manifest.json') != native['pinsSHA256'] or build['pinsSHA256'] != native['pinsSHA256']:
        raise SystemExit('Built/native pins differ')
    run_id = uuid.uuid4().hex
    output = ROOT / 'Verification/Evidence/ServerReplay83/Standalone' / run_id
    output.mkdir(parents=True, exist_ok=False)
    private = cache / 'ProofRuns' / run_id
    jobs = private / 'Jobs'
    jobs.mkdir(parents=True, exist_ok=False)
    files = {p.relative_to(bundle).as_posix(): sha(p) for p in sorted(bundle.rglob('*')) if p.is_file()}
    approval = {'version': 1, 'kind': 'PinnedUnityReplayWorker', 'unity': '2022.3.62f3',
                'executable': 'PinnedReplayWorker.exe', 'pins': 'ReplayPins/manifest.json', 'files': files}
    approval_path = private / 'Local_Approval.json'
    approval_path.write_text(json.dumps(approval, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    (output / 'Local_Approval.json').write_bytes(approval_path.read_bytes())
    worker = ApprovedWorker(bundle, approval_path, sha(approval_path), jobs, enabled=True)
    report = {'status': 'RUNNING_ACTUAL_PINNED_WINDOWS_WORKER', 'startedUtc': utc(), 'runId': run_id,
              'scope': 'Actual standalone Windows Mono Unity model process versus pinned native full-checkpoint fixtures. Synthetic server-owned jobs only; no Android parity, authenticated gateway, financial mutation, real purchase or production activation.',
              'nativeReportSHA256': sha(native_path), 'pinsSHA256': native['pinsSHA256'],
              'approvalSHA256': sha(approval_path), 'bundleFiles': len(files), 'diagnosticLimit': args.limit,
              'cases': [], 'errors': [], 'sourceSHA256': {'Backend/hotr_backend/replay_contract.py': sha(ROOT / 'Backend/hotr_backend/replay_contract.py')}}
    path = output / 'Report.json'
    def save():
        report['utc'] = utc()
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        for fixture in native['fixtures'][:args.limit or None]:
            job_path = native_path.parent / fixture['job']
            if sha(job_path) != fixture['jobSHA256']:
                raise ReplayError('fixture_hash_changed')
            job = strict_json(job_path.read_bytes())
            expected = strict_json((native_path.parent / fixture['expected']).read_bytes())
            started = time.monotonic()
            result = worker.run(job)
            actual = dict(result['result'])
            # The broker canonically encodes JSON; native fixture formatting is
            # different. Both processes independently bind their actual bytes.
            actual.pop('jobSHA256')
            expected.pop('jobSHA256')
            if actual != expected:
                raise ReplayError('actual_standalone_checkpoint_or_outcome_differs')
            report['cases'].append({'name': fixture['name'], 'seconds': round(time.monotonic() - started, 3),
                'process': result['process'], 'checkpointSHA256': actual['checkpointSHA256'],
                'outcome': actual['outcome'], 'actions': actual['actions'], 'jobSHA256': result['jobSHA256'],
                'outputSHA256': result['outputSHA256']})
            save()
        report['status'] = 'PASS_ACTUAL_PINNED_WINDOWS_WORKER_DIAGNOSTIC' if args.limit else 'PASS_ACTUAL_PINNED_WINDOWS_WORKER_FULL_NATIVE_CORPUS'
    except ReplayError as error:
        report['status'] = 'FAIL_ACTUAL_PINNED_WINDOWS_WORKER'
        report['errors'].append(str(error))  # ReplayError carries a static code only.
    except Exception as error:
        report['status'] = 'FAIL_ACTUAL_PINNED_WINDOWS_WORKER'
        report['errors'].append(type(error).__name__)
    report['finishedUtc'] = utc()
    save()
    print(json.dumps({'status': report['status'], 'cases': len(report['cases']), 'report': str(path)}))
    return 0 if report['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
