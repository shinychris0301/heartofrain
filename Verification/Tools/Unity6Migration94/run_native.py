"""Run real Unity 6 methods only in the approved isolated project; protect main inputs."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'
EDITOR = Path('E:/HeartRainUnity6_94/6000.6.6f1/Editor/Unity.exe')
OUT = ROOT / 'Verification/Evidence/Unity6Migration94'
VERSION = '6000.6.6f1'


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def candidate_sources(api):
    files = {}
    for category in ('Assets', 'Packages', 'ProjectSettings'):
        for path in sorted((PROJECT / category).rglob('*')):
            if path.is_file():
                if path.is_symlink() or getattr(path.stat(), 'st_file_attributes', 0) & 0x400:
                    raise RuntimeError('LinkedCandidateInputRefused')
                files[path.relative_to(PROJECT).as_posix()] = {'sha256': api.sha(path), 'bytes': path.stat().st_size}
    return {'schemaVersion': 1, 'project': PROJECT.relative_to(ROOT).as_posix(), 'inputCount': len(files), 'files': files}


def fresh_child(path, parent):
    path = Path(path).resolve()
    if not path.is_relative_to(parent.resolve()) or path == parent.resolve() or path.exists():
        raise ValueError('FreshContainedOutputRequired')
    return path


def good_native(value, expected, legacy_versionless=False):
    return (isinstance(value, dict) and value.get('status') == expected
            and (value.get('unity') == VERSION or (legacy_versionless and 'unity' not in value)) and not value.get('errors')
            and not value.get('error') and not value.get('failures') and not value.get('failed'))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--execute', action='store_true')
    cli.add_argument('--out', type=Path, required=True)
    cli.add_argument('--entry', required=True)
    cli.add_argument('--report', required=True)
    cli.add_argument('--expected', required=True)
    cli.add_argument('--output-env', default='HOTR_UNITY6_94_OUT')
    cli.add_argument('--build-target', choices=('Android', 'Win64'))
    cli.add_argument('--apk', type=Path)
    cli.add_argument('--timeout', type=int, default=900)
    cli.add_argument('--quit', action='store_true')
    cli.add_argument('--legacy-report-no-version', action='store_true', help='Declared unchanged legacy schema has no unity field; require actual engine version from this process log instead.')
    args = cli.parse_args()
    if not args.execute or os.name != 'nt' or not 30 <= args.timeout <= 3600:
        cli.error('Explicit bounded root Windows execution required')
    if not re.fullmatch(r'HeartOfTheRain\.[A-Za-z0-9_.]+', args.entry) or not re.fullmatch(r'HOTR_[A-Z0-9_]+', args.output_env):
        cli.error('Explicit native entry and output environment required')
    out = fresh_child(args.out, OUT)
    report = (out / args.report).resolve()
    if not report.is_relative_to(out) or report.suffix != '.json':
        cli.error('Contained JSON report required')
    api = module('migration94_baseline_reader', 'Verification/Tools/Ads85/run_ads85_native.py')
    sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
    processes = module('migration94_processes', 'Verification/Tools/PageBackdrop90/process90.py')
    jobs = module('migration94_resume', 'Verification/Tools/Review93/run_connected.py')
    if not EDITOR.is_file() or not PROJECT.is_dir() or processes.unity_pids():
        cli.error('Prepared portable Editor/project and no concurrent Unity required')
    before = api.freeze()
    baseline = json.loads((OUT / 'MainSources_Before.json').read_text('utf-8'))
    if before != baseline:
        cli.error('Protected main source is not the approved migration baseline')
    out.mkdir(parents=True, exist_ok=False)
    api.write(out / 'MainSources_before.json', before)
    candidate = candidate_sources(api)
    api.write(out / 'CandidateSources_before.json', candidate)
    command = [str(EDITOR), '-batchmode', '-projectPath', str(PROJECT), '-executeMethod', args.entry,
               '-logFile', str(out / 'Unity.log')]
    if args.build_target:
        command += ['-buildTarget', args.build_target]
    if args.quit:
        command += ['-quit']
    environment = dict(os.environ)
    environment.update(HOTR_UNITY6_94_VERSION=VERSION, HOTR_UNITY6_94_OUT=str(out), HOTR_REVIEW93_OUT=str(out))
    environment[args.output_env] = str(out)
    if args.apk:
        apk = fresh_child(args.apk, PROJECT / 'Builds')
        environment['HOTR_UNITY6_94_APK'] = str(apk)
    record = {'schemaVersion': 1, 'status': 'RUNNING_ISOLATED_UNITY6_94', 'startedUtc': api.utc(),
        'entry': args.entry, 'command': command, 'expectedVersion': VERSION, 'expectedNativeStatus': args.expected,
        'runnerSHA256': api.sha(Path(__file__)), 'editorSHA256': api.sha(EDITOR),
        'mainInputCount': before['inputCount'], 'candidateInputCount': candidate['inputCount'],
        'timeoutSeconds': args.timeout, 'legacyReportWithoutUnityField': args.legacy_report_no_version,
        'scope': 'Actual separate portable Unity 6 process and isolated project. Main 2022 source, backend worker and installed owner app are not migrated by this invocation. Native report and declared target determine test/build scope; no device or production acceptance inferred.'}
    api.write(out / 'Authorization.json', record)
    process = job = None
    started = time.monotonic()
    try:
        job = api.OwnedJob()
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        with (out / 'Console.log').open('x', encoding='utf-8') as stream:
            process = subprocess.Popen(command, cwd=PROJECT, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW | 0x4, startupinfo=startup)
            record['pid'] = process.pid
            job.assign(process.pid)
            record['ownedJobAssignedBeforeResume'] = True
            jobs.resume_owned_primary(process)
            print(json.dumps({'status': 'STARTED_ISOLATED_UNITY6_94', 'pid': process.pid, 'entry': args.entry}), flush=True)
            try:
                process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                record['timedOut'] = True
                job.close()
                process.wait(timeout=20)
        native = json.loads(report.read_text('utf-8-sig')) if report.is_file() else {}
        log_text = (out / 'Unity.log').read_text('utf-8-sig', errors='replace')
        match = re.search(r'Initialize engine version:\s*(\S+)', log_text)
        record['actualEngineVersionFromProcessLog'] = match.group(1) if match else None
        record.update(exitCode=process.returncode, nativeStatus=native.get('status', 'MISSING'),
            nativeReport=report.relative_to(ROOT).as_posix(), nativeReportSHA256=api.sha(report) if report.is_file() else None,
            nativeErrors=native.get('errors'), nativeError=native.get('error'), nativeChecks=native.get('checks'))
        record['status'] = 'PASS_ISOLATED_UNITY6_94_NATIVE' if process.returncode == 0 and not record.get('timedOut') and record['actualEngineVersionFromProcessLog'] == VERSION and good_native(native, args.expected, args.legacy_report_no_version) else 'FAIL_ISOLATED_UNITY6_94_NATIVE'
    except Exception as error:
        record.update(status='FAIL_ISOLATED_UNITY6_94_RUNNER', runnerErrorType=type(error).__name__)
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=20)
        after = api.freeze()
        api.write(out / 'MainSources_after.json', after)
        api.write(out / 'CandidateSources_after.json', candidate_sources(api))
        record.update(mainInputsUnchanged=before == after, unityPidsAfter=processes.unity_pids(),
            finishedUtc=api.utc(), elapsedSeconds=round(time.monotonic() - started, 3),
            unityLogSHA256=api.sha(out / 'Unity.log') if (out / 'Unity.log').is_file() else None,
            consoleLogSHA256=api.sha(out / 'Console.log'))
        if not record['mainInputsUnchanged'] or record['unityPidsAfter']:
            record['status'] = 'FAIL_ISOLATED_UNITY6_94_PRESERVATION'
        api.write(out / 'Invocation.json', record)
    print(json.dumps({'status': record['status'], 'nativeStatus': record.get('nativeStatus'),
        'mainInputsUnchanged': record['mainInputsUnchanged'], 'invocation': (out / 'Invocation.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
