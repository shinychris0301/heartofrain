"""Root-only pinned Unity invocation; fresh RegionalAccounts89 reports, no device access.

The supplied native entry must write to the selected output env and exit itself.
An unexecuted method or a source-only check never becomes native evidence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import OwnedJob, PINNED_UNITY, UNITY_PROJECT, delta, disk, freeze, sha, unchanged, utc, write
sys.path.insert(0, str(ROOT / 'Verification/Tools/Review86'))
from run_native86 import unity_pids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--entry', required=True)
    parser.add_argument('--report', default='Native/RegionalAccounts89.json')
    parser.add_argument('--expected', default='PASS_NATIVE_REGIONAL89')
    parser.add_argument('--output-env', default='HOTR_REGIONAL89_OUT')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    out = args.out.resolve()
    evidence = (ROOT / 'Verification/Evidence/RegionalAccounts89').resolve()
    report = (out / args.report).resolve()
    if os.name != 'nt' or not out.is_relative_to(evidence) or out == evidence or not report.is_relative_to(out):
        parser.error('Root Windows execution and fresh RegionalAccounts89 run required')
    if not re.fullmatch(r'HeartOfTheRain\.[A-Za-z0-9_.]+', args.entry) or not re.fullmatch(r'HOTR_[A-Z0-9_]+', args.output_env) or not 30 <= args.timeout <= 1800:
        parser.error('Explicit bounded native method required')
    if not PINNED_UNITY.is_file() or unity_pids() or 'm_EditorVersion: 2022.3.62f3' not in (UNITY_PROJECT / 'ProjectSettings/ProjectVersion.txt').read_text('utf-8-sig'):
        parser.error('Pinned Editor required without concurrent Unity')
    out.mkdir(parents=True, exist_ok=False)
    before = freeze()
    write(out / 'FrozenSources.json', before)
    environment = dict(os.environ)
    environment[args.output_env] = str(out)
    log, console = out / 'Unity.log', out / 'Console.log'
    record = {'status': 'RUNNING', 'entry': args.entry, 'outputEnvironmentVariable': args.output_env, 'startedUtc': utc(), 'timeoutSeconds': args.timeout,
              'sourceSHA256': sha(out / 'FrozenSources.json'), 'inputCount': before['inputCount'],
              'runnerSHA256': sha(Path(__file__)), 'unityExeSHA256': sha(PINNED_UNITY),
              'hashProcessHelperSHA256': sha(ROOT / 'Verification/Tools/Ads85/run_ads85_native.py'),
              'processSelectorSHA256': sha(ROOT / 'Verification/Tools/Review86/run_native86.py'),
              'scope': 'Actual pinned Editor execution only; native report defines assertions and pixel evidence. No Android, phone or full-game acceptance implied.'}
    process = job = None
    started = time.monotonic()
    try:
        job = OwnedJob()
        with open(disk(console), 'x', encoding='utf-8') as stream:
            process = subprocess.Popen([str(PINNED_UNITY), '-batchmode', '-projectPath', str(UNITY_PROJECT), '-executeMethod', args.entry, '-logFile', str(log)],
                                       env=environment, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            record['pid'] = process.pid
            job.assign(process.pid)
            try:
                process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                record['timedOut'] = True
                job.close()
                process.wait(timeout=20)
        native = json.loads(report.read_text('utf-8-sig')) if report.is_file() else {}
        record.update(exitCode=process.returncode, nativeStatus=native.get('status', 'MISSING'),
                      nativeReportSHA256=sha(report) if report.is_file() else None,
                      checks=native.get('checks'), failures=native.get('failures'), errors=native.get('errors'))
        record['status'] = 'PASS_NATIVE_REGIONAL89_INVOCATION' if process.returncode == 0 and not record.get('timedOut') and native.get('status') == args.expected and not native.get('errors') and not native.get('error') and not native.get('failures') else 'FAIL_NATIVE_REGIONAL89_INVOCATION'
    except Exception as error:
        record.update(status='FAIL_NATIVE_REGIONAL89_RUNNER', errorType=type(error).__name__)
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=20)
        after = freeze()
        write(out / 'Sources_after.json', after)
        changes = delta(before, after)
        write(out / 'Source_Delta.json', changes)
        record.update(inputsUnchanged=unchanged(changes), unityPidsAfter=unity_pids(), finishedUtc=utc(),
                      elapsedSeconds=round(time.monotonic() - started, 3), unityLogSHA256=sha(log) if log.is_file() else None,
                      consoleSHA256=sha(console) if console.is_file() else None)
        if not record['inputsUnchanged'] or record['unityPidsAfter']:
            record['status'] = 'FAIL_NATIVE_REGIONAL89_INPUTS_OR_PROCESS'
        write(out / 'Invocation.json', record)
    print(json.dumps({'status': record['status'], 'report': (out / 'Invocation.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
