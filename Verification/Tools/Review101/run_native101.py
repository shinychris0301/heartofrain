"""Serial real Unity checks for checkpoint101; original suites keep their own pins.

Raw Editor/console logs stay private. Source equality, native report and actual
process engine version determine the invocation result; host checks cannot pass
a missing native suite. No device operation is performed by this runner.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0, str(ROOT/'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids
sys.path.insert(0, str(ROOT/'Verification/Tools/Review93'))
from run_connected import resume_owned_primary

EDITORS = {
    '2022': (api.PINNED_UNITY, ROOT/'Unity', '2022.3.62f3'),
    'lts': (Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Unity.exe'),
            ROOT/'.verification-cache/Review98/Game', '6000.3.27f1'),
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
    p.add_argument('--tag', required=True)
    p.add_argument('--entry', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--expected', required=True)
    p.add_argument('--output-env', default='HOTR_REVIEW101_OUT')
    p.add_argument('--output-is-file', action='store_true')
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--build-target', choices=('Android', 'Win64'))
    p.add_argument('--apk', type=Path)
    p.add_argument('--sdk-resolver',type=Path,default=ROOT/'Verification/Evidence/Review101/SDKResolverPreparation.json')
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
    out = ROOT/'Verification/Evidence/Review101/Native'/args.tag
    private = ROOT/'.verification-cache/Review101/RawNative'/args.tag
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
    if args.build_target:
        command += ['-buildTarget', args.build_target]
    if args.quit:
        command += ['-quit']
    environment = dict(os.environ)
    environment.update(HOTR_REVIEW93_OUT=str(out), HOTR_REVIEW101_OUT=str(out), HOTR_REVIEW101_PRIVATE_OUT=str(private), HOTR_REVIEW99_OUT=str(out), HOTR_REVIEW99_PRIVATE_OUT=str(private))
    environment[args.output_env] = str(report if args.output_is_file else out)
    if args.entry == 'HeartOfTheRain.Verification.ProfileM71Verification.Play':
        environment['HOTR_REVIEW98_PROFILE_FIXTURE'] = str(private/'ProfileAppearance.json')
    sdk_resolver = None
    if args.engine == 'lts':
        proof_path = args.sdk_resolver.resolve()
        if not proof_path.is_relative_to((ROOT/'Verification/Evidence/Review101').resolve()):
            p.error('Contained101 SDK resolver receipt required')
        proof = json.loads(proof_path.read_text('utf-8'))
        expires = datetime.fromisoformat(proof['expiresUtc'])
        hosts = ROOT/proof['privateHostsFile']['path']
        if (proof['status'] != 'PREPARED_PROCESS_LOCAL_SDK_RESOLVER98'
                or (expires-datetime.now(timezone.utc)).total_seconds() < args.timeout+60
                or api.sha(hosts) != proof['privateHostsFile']['sha256']):
            p.error('Fresh verified process-local SDK route required')
        if any(environment.get(k) for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')):
            p.error('Java-wide injected options are outside this scoped build')
        environment.update(GRADLE_USER_HOME='E:/HR98G', HOTR_GRADLE98_OFFLINE='1',
                           SDKMANAGER_OPTS='-Djdk.net.hosts.file='+str(hosts)+' -Dsun.net.client.defaultConnectTimeout=5000 -Dsun.net.client.defaultReadTimeout=15000')
        sdk_resolver = {'path':proof_path.relative_to(ROOT).as_posix(),'sha256':api.sha(proof_path),'expiresUtc':proof['expiresUtc']}
    if args.apk:
        apk = args.apk.resolve()
        if args.engine != 'lts' or not apk.is_relative_to((project/'Builds').resolve()) or apk.exists() or apk.suffix != '.apk':
            p.error('Fresh private LTS build output required')
        environment['HOTR_REVIEW101_APK'] = str(apk)
    record = {'schemaVersion': 1, 'status': 'RUNNING_NATIVE101', 'startedUtc': api.utc(),
              'entry': args.entry, 'expectedEngine': version, 'expectedNativeStatus': args.expected,
              'runnerSHA256': api.sha(Path(__file__)), 'editorSHA256': api.sha(editor),
              'mainInputCount': before['inputCount'], 'projectInputCount': candidate_before['inputCount'],
              'processLocalSdkResolver': sdk_resolver,
              'scope': 'Actual serial Editor invocation. Native report defines test scope; no Android/device/backend/production acceptance inferred.'}
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
            print(json.dumps({'status':'STARTED_NATIVE101','tag':args.tag,'entry':args.entry}), flush=True)
            try:
                process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                record['timedOut'] = True
                job.close()
                process.wait(timeout=20)
        native = json.loads(report.read_text('utf-8-sig')) if report.is_file() else {}
        text = log.read_text('utf-8-sig', errors='replace') if log.is_file() else ''
        match = re.search(r'Initialize engine version:\s*(\S+)', text)
        record.update(exitCode=process.returncode, nativeStatus=native.get('status','MISSING'),
                      actualEngine=match.group(1) if match else None,
                      checks=native.get('checks',native.get('total',0)), nativeReport=args.report,
                      nativeReportSHA256=api.sha(report) if report.is_file() else None)
        good = (process.returncode == 0 and not record.get('timedOut') and record['actualEngine'] == version
                and native.get('status') == args.expected and not any(native.get(k) for k in ('error','errors','failed','failures')))
        record['status'] = 'PASS_NATIVE101_INVOCATION' if good else 'FAIL_NATIVE101_INVOCATION'
    except Exception as error:
        record.update(status='FAIL_NATIVE101_RUNNER', errorType=type(error).__name__)
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=20)
        after, candidate_after = api.freeze(), inputs(project)
        api.write(out/'MainSources_after.json', after)
        api.write(out/'ProjectSources_after.json', candidate_after)
        private_configuration = args.engine == 'lts' and args.entry == 'HeartOfTheRain.Verification.Unity6Build101.Configure'
        project_delta = api.delta(candidate_before, candidate_after)
        preserved = True
        guids_preserved = True
        if args.engine == 'lts':
            for name, value in after['files'].items():
                relative = name.removeprefix('Unity/')
                if relative.startswith('Assets/') and not relative.endswith('.meta'):
                    copied = '.verification-cache/Review98/Game/' + relative
                    if candidate_after['files'].get(copied) != value:
                        preserved = False
                elif relative.startswith('Assets/') and relative.endswith('.meta'):
                    main_meta, candidate_meta = ROOT/name, project/relative
                    original_guid = re.findall(rb'(?m)^guid:\s*([0-9a-fA-F]{32})\s*$', main_meta.read_bytes())
                    copied_guid = re.findall(rb'(?m)^guid:\s*([0-9a-fA-F]{32})\s*$', candidate_meta.read_bytes()) if candidate_meta.is_file() else []
                    if len(original_guid) != 1 or copied_guid != original_guid:
                        guids_preserved = False
        record.update(mainInputsUnchanged=before == after, projectInputsUnchanged=candidate_before == candidate_after,
                      privateConfigurationInvocation=private_configuration, projectInputDeltas=project_delta,
                      originalAssetAndSourceBytesPreserved=preserved,
                      originalAssetGuidsPreserved=guids_preserved,
                      unityPidsAfter=unity_pids(), finishedUtc=api.utc(),
                      elapsedSeconds=round(time.monotonic()-started,3),
                      privateLogs=[{'path':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':api.sha(path),'bytes':path.stat().st_size}
                                   for path in (log,console) if path.is_file()])
        if (not record['mainInputsUnchanged'] or not preserved or not guids_preserved or record['unityPidsAfter']
                or (not record['projectInputsUnchanged'] and not private_configuration)):
            record['status'] = 'FAIL_NATIVE101_INPUTS_OR_PROCESS'
        api.write(out/'Invocation.json', record)
    print(json.dumps({'status':record['status'],'report':str((out/'Invocation.json').relative_to(ROOT)).replace('\\','/')}),flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
