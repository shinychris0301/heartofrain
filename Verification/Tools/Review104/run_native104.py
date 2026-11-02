"""Serial real Unity checks for checkpoint104; original suites keep their own pins.

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


def isolated_boundary(project, proof, main, candidate):
    """Independently bind a full clone, not merely the preparer's selected rows."""
    original = {name.removeprefix('Unity/'):value['sha256'] for name,value in main['files'].items()}
    prefix = project.relative_to(ROOT).as_posix() + '/'
    copied = {name.removeprefix(prefix):value['sha256'] for name,value in candidate['files'].items()}
    receipt_rows = dict(zip(proof['copiedPaths'],proof['copiedSHA256']))
    if proof.get('mainSourceSHA256') != original or receipt_rows != copied or copied.keys() != original.keys():
        raise ValueError('FullPreparedCloneAndMainReceiptEqualityRequired104')
    differences = sorted(name for name in original if copied[name] != original[name])
    if differences != ['ProjectSettings/ProjectSettings.asset']:
        raise ValueError('OnlyPrivateProjectIdentityMayDiffer104')
    def normalized_settings(path):
        lines = path.read_text('utf-8-sig').splitlines()
        normalized, in_identifiers = [], False
        for line in lines:
            if line.startswith('  applicationIdentifier:'):
                in_identifiers = True
            elif in_identifiers and line and not line.startswith('    '):
                in_identifiers = False
            if in_identifiers and line.startswith(('    Android:', '    Standalone:')):
                continue
            if line.startswith(('  companyName:', '  productName:', '  androidUseCustomKeystore:')):
                normalized.append(line.split(':',1)[0] + ': <isolated104>')
            else:
                normalized.append(line)
        return normalized
    settings = project/'ProjectSettings/ProjectSettings.asset'
    text = settings.read_text('utf-8-sig')
    if (normalized_settings(settings) != normalized_settings(ROOT/'Unity/ProjectSettings/ProjectSettings.asset')
            or not re.search(r'(?m)^  companyName: HeartRainStaging104$',text)
            or not re.search(r'(?m)^  productName: HeartRainStaging104$',text)
            or not re.search(r'(?m)^  androidUseCustomKeystore: 0$',text)):
        raise ValueError('ExactPrivatePersistentIdentityBeforeFirstImportRequired104')
    identifiers = re.search(r'(?m)^  applicationIdentifier:\n((?:    [^\n]*\n)+)',text)
    if not identifiers or not all(re.search(r'(?m)^    '+kind+r': com\.heartoftherain\.stagingreview$',identifiers.group(1)) for kind in ('Android','Standalone')):
        raise ValueError('ExactPrivateApplicationIdentifiersRequired104')
    return dict(fullCopiedInputCount=len(copied),mainSourceReceiptMatches=True,fullCandidateReceiptMatches=True,
                onlySettingsDiffer=True,approvedSettingsDifference=['companyName','productName','Android applicationIdentifier','Standalone applicationIdentifier','androidUseCustomKeystore'],
                assetSourceAndExistingMetaBytesMatchMain=True,engineAndPackagesMatchMain=True,
                separatePersistentIdentitySetBeforeFirstImport=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--engine', choices=EDITORS, required=True)
    p.add_argument('--project-scope', choices=('main', 'staging104'), default='main')
    p.add_argument('--staging-receipt', type=Path)
    p.add_argument('--staging-config', type=Path)
    p.add_argument('--tag', required=True)
    p.add_argument('--entry', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--expected', required=True)
    p.add_argument('--output-env', default='HOTR_REVIEW104_OUT')
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
    staging_receipt = None
    fixture_config = None
    if args.project_scope == 'staging104':
        if args.staging_receipt is None or args.staging_config is None:
            p.error('Explicit isolated104 preparation receipt and never-contacted fixture config required')
        receipt_path = args.staging_receipt.resolve()
        candidates = (ROOT/'.verification-cache/Review104/Candidates').resolve()
        if not receipt_path.is_relative_to(candidates) or receipt_path.name != 'Preparation.json':
            p.error('Contained isolated104 preparation receipt required')
        proof = json.loads(receipt_path.read_text('utf-8-sig'))
        project = (receipt_path.parent/'Game').resolve()
        if (proof.get('version') != 1 or proof.get('status') != 'PREPARED_STAGING104'
                or proof.get('unity') != version or Path(proof.get('project','')).resolve() != project
                or Path(proof.get('sourceRoot','')).resolve() != ROOT
                or not re.fullmatch(r'[0-9a-f]{32}',proof.get('nonce',''))
                or not re.fullmatch(r'[0-9a-f]{64}',proof.get('configSHA256',''))):
            p.error('Valid exact104 isolated project receipt required')
        names, digests = proof.get('copiedPaths',[]), proof.get('copiedSHA256',[])
        if not names or len(names) != len(digests) or len(set(names)) != len(names):
            p.error('Complete unique104 copied input hashes required')
        for name, digest in zip(names,digests):
            item = (project/name).resolve()
            if (not item.is_relative_to(project) or not name.startswith(('Assets/','Packages/','ProjectSettings/'))
                    or not item.is_file() or api.sha(item) != digest):
                p.error('Prepared104 isolated inputs must remain exact')
        staging_receipt = dict(path=receipt_path.relative_to(ROOT).as_posix(),sha256=api.sha(receipt_path),
                               project=project.relative_to(ROOT).as_posix(),copiedInputs=len(names),
                               nonce=proof['nonce'],configSHA256=proof['configSHA256'])
        config_path = args.staging_config.resolve()
        if not config_path.is_relative_to((ROOT/'.verification-cache/Review104').resolve()) or not config_path.is_file() or not 2 <= config_path.stat().st_size <= 8192:
            p.error('Contained bounded104 synthetic configuration required')
        config = json.loads(config_path.read_text('utf-8-sig'))
        origin = urlsplit(config.get('origin',''))
        if origin.geturl() != 'https://staging.hotr-native-fixture.net':
            p.error('Exact approved parser/import-only synthetic fixture required; no DNS or HTTP')
        fixture_config = dict(path=config_path.relative_to(ROOT).as_posix(),sha256=api.sha(config_path),
                              bytes=config_path.stat().st_size,syntheticNeverContacted=True,
                              assignedOrOwnedBackend=False)
    elif args.staging_receipt is not None or args.staging_config is not None:
        p.error('Staging receipt/config are only accepted with isolated104 project scope')
    if not editor.is_file() or not project.is_dir() or unity_pids():
        p.error('Selected prepared Editor/project and no concurrent Unity required')
    out = ROOT/'Verification/Evidence/Review104/Native'/args.tag
    private = ROOT/'.verification-cache/Review104/RawNative'/args.tag
    report = (out/args.report).resolve()
    if not report.is_relative_to(out.resolve()) or report.suffix != '.json':
        p.error('Contained native JSON report required')
    out.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    before, candidate_before = api.freeze(), inputs(project)
    clone_boundary = isolated_boundary(project,proof,before,candidate_before) if staging_receipt else None
    api.write(out/'MainSources_before.json', before)
    api.write(out/'ProjectSources_before.json', candidate_before)
    log, console = private/'Unity.log', private/'Console.log'
    command = [str(editor), '-batchmode', '-projectPath', str(project),
               '-executeMethod', args.entry, '-logFile', str(log)]
    if args.quit:
        command += ['-quit']
    environment = dict(os.environ)
    environment.update(HOTR_REVIEW93_OUT=str(out), HOTR_REVIEW104_OUT=str(out), HOTR_REVIEW104_PRIVATE_OUT=str(private), HOTR_REVIEW99_OUT=str(out), HOTR_REVIEW99_PRIVATE_OUT=str(private))
    environment[args.output_env] = str(report if args.output_is_file else out)
    if staging_receipt:
        environment['HOTR_STAGING104_ISOLATION'] = str(receipt_path)
        environment['HOTR_STAGING104_CONFIG'] = str(config_path)
    record = {'schemaVersion': 1, 'status': 'RUNNING_NATIVE104', 'startedUtc': api.utc(),
              'entry': args.entry, 'expectedEngine': version, 'expectedNativeStatus': args.expected,
              'runnerSHA256': api.sha(Path(__file__)), 'editorSHA256': api.sha(editor),
              'mainInputCount': before['inputCount'], 'projectInputCount': candidate_before['inputCount'],
              'projectScope':args.project_scope, 'isolatedPreparation':staging_receipt, 'fixtureConfig':fixture_config,
              'independentCloneBoundary':clone_boundary,
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
            print(json.dumps({'status':'STARTED_NATIVE104','tag':args.tag,'entry':args.entry}), flush=True)
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
        record['status'] = 'PASS_NATIVE104_INVOCATION' if good else 'FAIL_NATIVE104_INVOCATION'
    except Exception as error:
        record.update(status='FAIL_NATIVE104_RUNNER', errorType=type(error).__name__)
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
            record['status'] = 'FAIL_NATIVE104_INPUTS_OR_PROCESS'
        api.write(out/'Invocation.json', record)
    print(json.dumps({'status':record['status'],'report':str((out/'Invocation.json').relative_to(ROOT)).replace('\\','/')}),flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
