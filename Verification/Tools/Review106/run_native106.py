"""Serial real Unity checks for checkpoint106; original suites keep their own pins.

Raw Editor/console logs stay private. Source equality, native report and actual
process engine version determine the invocation result; host checks cannot pass
a missing native suite. No device operation is performed by this runner.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0, str(ROOT/'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids
sys.path.insert(0, str(ROOT/'Verification/Tools/Review93'))
from run_connected import resume_owned_primary

EDITORS = {
    '2022': (api.PINNED_UNITY, ROOT/'Unity', '2022.3.62f3'),
}


def inputs(project):
    original = api.UNITY_PROJECT
    try:
        api.UNITY_PROJECT = project
        return api.freeze()
    finally:
        api.UNITY_PROJECT = original



def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--engine', choices=EDITORS, required=True)
    p.add_argument('--phase', choices=('Before','After'))
    p.add_argument('--tag', required=True)
    p.add_argument('--entry', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--expected', required=True)
    p.add_argument('--output-env', default='HOTR_REVIEW106_OUT')
    p.add_argument('--output-is-file', action='store_true')
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--quit', action='store_true')
    args = p.parse_args()
    if not args.execute or os.name != 'nt' or not 30 <= args.timeout <= 3600:
        p.error('Explicit bounded Windows execution required')
    if not re.fullmatch(r'[A-Za-z0-9_]{1,40}', args.tag) or not re.fullmatch(r'HeartOfTheRain\.[A-Za-z0-9_.]+', args.entry):
        p.error('Explicit safe run tag and native entry required')
    if not re.fullmatch(r'HOTR_[A-Z0-9_]+', args.output_env):
        p.error('Explicit output environment variable required')
    editor, project, version = EDITORS[args.engine]
    if not editor.is_file() or not project.is_dir() or unity_pids():
        p.error('Selected prepared Editor/project and no concurrent Unity required')
    out = ROOT/'Verification/Evidence/Review106/Native'/args.tag
    private = ROOT/'.verification-cache/Review106/RawNative'/args.tag
    report = (out/args.report).resolve()
    if not report.is_relative_to(out.resolve()) or report.suffix != '.json':
        p.error('Contained native JSON report required')
    out.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    before, candidate_before = api.freeze(), inputs(project)
    api.write(out/'MainSources_before.json', before)
    api.write(out/'ProjectSources_before.json', candidate_before)
    log, console = private/'Unity.log', private/'Console.log'
    command = [str(editor), '-batchmode', '-projectPath', str(project),
               '-executeMethod', args.entry, '-logFile', str(log)]
    if args.quit:
        command += ['-quit']
    environment = dict(os.environ)
    environment.update(HOTR_REVIEW93_OUT=str(out), HOTR_REVIEW106_OUT=str(out), HOTR_REVIEW106_PRIVATE_OUT=str(private), HOTR_REVIEW99_OUT=str(out), HOTR_REVIEW99_PRIVATE_OUT=str(private))
    environment[args.output_env] = str(report if args.output_is_file else out)
    if args.phase:environment['HOTR_REVIEW106_PHASE']=args.phase
    record = {'schemaVersion': 1, 'status': 'RUNNING_NATIVE106', 'startedUtc': api.utc(),
              'entry': args.entry, 'expectedEngine': version, 'expectedNativeStatus': args.expected,
              'runnerSHA256': api.sha(Path(__file__)), 'editorSHA256': api.sha(editor),
              'mainInputCount': before['inputCount'], 'projectInputCount': candidate_before['inputCount'],
              'projectScope':'main', 'phase':args.phase,
              'scope': 'Actual serial Unity2022 Editor invocation only. No BuildPipeline, APK, HTTP, device, backend or production operation is authorized by this runner.'}
    api.write(out/'Authorization.json', record)
    started, process, job = time.monotonic(), None, None
    try:
        job = api.OwnedJob()
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        with console.open('x', encoding='utf-8') as stream:
            process = subprocess.Popen(command, cwd=project, env=environment, stdout=stream,
                stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW | 0x4,
                startupinfo=startup)
            record['pid'] = process.pid
            job.assign(process.pid)
            resume_owned_primary(process)
            record['ownedJobAssignedBeforeResume'] = True
            print(json.dumps({'status':'STARTED_NATIVE106','tag':args.tag,'entry':args.entry}), flush=True)
            try:
                process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                record['timedOut'] = True
                job.close()
                process.wait(timeout=20)
        native = json.loads(report.read_text('utf-8-sig')) if report.is_file() else {}
        text = log.read_text('utf-8-sig', errors='replace') if log.is_file() else ''
        match = re.search(r'Initialize engine version:\s*(\S+)', text)
        checks = native.get('checks',native.get('total',native.get('passed',0)))
        checks = checks if isinstance(checks,int) else native.get('passed',0)
        record.update(exitCode=process.returncode, nativeStatus=native.get('status','MISSING'),
                      actualEngine=match.group(1) if match else None,
                      checks=checks, nativeReport=args.report,
                      nativeReportSHA256=api.sha(report) if report.is_file() else None)
        good = (process.returncode == 0 and not record.get('timedOut') and record['actualEngine'] == version
                and native.get('status') == args.expected and not any(native.get(k) for k in ('error','errors','failed','failures')))
        record['status'] = 'PASS_NATIVE106_INVOCATION' if good else 'FAIL_NATIVE106_INVOCATION'
    except Exception as error:
        record.update(status='FAIL_NATIVE106_RUNNER', errorType=type(error).__name__)
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=20)
        after, candidate_after = api.freeze(), inputs(project)
        api.write(out/'MainSources_after.json', after)
        api.write(out/'ProjectSources_after.json', candidate_after)
        project_delta = api.delta(candidate_before, candidate_after)
        record.update(mainInputsUnchanged=before == after, projectInputsUnchanged=candidate_before == candidate_after,
                      projectInputDeltas=project_delta,
                      unityPidsAfter=unity_pids(), finishedUtc=api.utc(),
                      elapsedSeconds=round(time.monotonic()-started,3),
                      privateLogs=[{'path':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':api.sha(path),'bytes':path.stat().st_size}
                                   for path in (log,console) if path.is_file()])
        if not record['mainInputsUnchanged'] or not record['projectInputsUnchanged'] or record['unityPidsAfter']:
            record['status'] = 'FAIL_NATIVE106_INPUTS_OR_PROCESS'
        api.write(out/'Invocation.json', record)
    print(json.dumps({'status':record['status'],'report':str((out/'Invocation.json').relative_to(ROOT)).replace('\\','/')}),flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
