"""Root-only fresh minimal model projects and two actual serialization probes."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Unity6Migration94'
PROBES = ROOT / '.verification-cache/Unity6Migration94/ModelProbe'
TEMPLATE = Path(__file__).with_name('Templates') / 'SerializationPayload94.cs'
ENTRY = 'HeartOfTheRain.Verification.SerializationPayload94.Run'
LEVEL = 'Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L001.json'
EXTRA = ('Unity/Assets/HeartOfTheRain/Verification/Model77Control78.cs',
         'Unity/Assets/HeartOfTheRain/Verification/Snapshot78Control79.cs')
TARGETS = (('Baseline2022', '2022.3.62f3', Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Unity.exe')),
           ('Candidate6', '6000.6.6f1', Path('E:/HeartRainUnity6_94/6000.6.6f1/Editor/Unity.exe')))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def need(value, code):
    if not value:
        raise RuntimeError(code)


def readers():
    api = module('payload94_main_reader', ROOT / 'Verification/Tools/Ads85/run_ads85_native.py')
    sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
    native = module('payload94_candidate_reader', Path(__file__).with_name('run_native.py'))
    process = module('payload94_process_reader', ROOT / 'Verification/Tools/PageBackdrop90/process90.py')
    jobs = module('payload94_owned_resume', ROOT / 'Verification/Tools/Review93/run_connected.py')
    guards = module('payload94_path_guards', Path(__file__).with_name('adapt_test_pins.py'))
    return api, native, process, jobs, guards


def sources():
    builder = (ROOT / 'Unity/Assets/HeartOfTheRain/App/ServerVerification/Editor/PinnedReplayBuild.cs').read_text('utf-8-sig')
    region = builder.split('public static readonly string[] ModelSources={', 1)[1].split('};', 1)[0]
    model = re.findall(r'"(Unity/Assets/HeartOfTheRain/[^"\r\n]+\.cs)"', region)
    need(len(model) == 11 and len(set(model + list(EXTRA))) == 13, 'Payload94ExactApprovedModelClosureRequired')
    return model + list(EXTRA)


def relative_project(path):
    path = Path(path).resolve()
    need(path in {(PROBES / name).resolve() for name, _, _ in TARGETS}, 'Payload94OnlyTwoMinimalProjectsAllowed')
    return path


def manifest(path, api):
    return {file.relative_to(path).as_posix(): {'sha256': api.sha(file), 'bytes': file.stat().st_size}
            for file in sorted(path.rglob('*')) if file.is_file() and not any(part in ('Library', 'Temp', 'Logs', 'obj') for part in file.relative_to(path).parts)}


def prepare(output):
    api, native, processes, _, guards = readers()
    need(not processes.unity_pids(), 'Payload94NoConcurrentUnityForPreparation')
    baseline = json.loads((OUT / 'MainSources_Before.json').read_text('utf-8-sig'))
    need(api.freeze() == baseline, 'Payload94ProtectedMainChanged')
    output = guards.fresh_output(output)
    guards.reject_links(PROBES)
    need(not PROBES.exists(), 'Payload94ExistingProbeProjectsPreserved')
    selected = sources()
    fixture = TEMPLATE.read_bytes()
    current_candidate = native.candidate_sources(api)
    for relative in selected:
        source = ROOT / relative
        guards.reject_links(source)
        need(api.sha(source) == baseline['files'][relative]['sha256'], 'Payload94ModelSourceMismatch')
        candidate = native.PROJECT / Path(relative).relative_to('Unity')
        need(api.sha(candidate) == api.sha(source), 'Payload94CandidateModelDiffersFromMain')
    output.mkdir(parents=True, exist_ok=False)
    api.write(output / 'MainSources_before.json', baseline)
    api.write(output / 'CandidateSources_before.json', current_candidate)
    report = {'schemaVersion': 1, 'status': 'RUNNING_MINIMAL_SERIALIZATION94_PREPARATION', 'utc': api.utc(),
              'runnerSHA256': api.sha(Path(__file__)), 'templateSHA256': api.sha(TEMPLATE), 'projects': [],
              'scope': 'Fresh ordinary file copies of11 approved pure model sources plus2 unchanged Editor-only control dependency files into two tiny probe projects. Exact authoredL1 and identical new diagnostic fixture, JSON module only; no original main/candidate project edits, UI/art copy, worker engine execution/re-pinning or backend mutation.'}
    for name, version, _ in TARGETS:
        project = relative_project(PROBES / name)
        need(not project.exists(), 'Payload94FreshProjectRequired')
        for relative in selected:
            for suffix in ('', '.meta'):
                source = ROOT / (relative + suffix)
                target = project / 'Assets/ProbeModel' / (Path(relative).name + suffix)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(source.read_bytes())
                need(api.sha(target) == api.sha(source) and target.stat().st_nlink == 1, 'Payload94ExactOrdinaryModelCopyRequired')
        target = project / 'Assets/Editor/SerializationPayload94.cs'
        target.parent.mkdir(parents=True)
        target.write_bytes(fixture)
        target.with_suffix('.cs.meta').write_text('fileFormatVersion: 2\nguid: 688b2d0e295a4175a4b14e14ee315394\n', encoding='utf-8')
        (project / 'ProbeInputs').mkdir()
        (project / 'ProbeInputs/C01_L001.json').write_bytes((ROOT / LEVEL).read_bytes())
        (project / 'Packages').mkdir()
        (project / 'Packages/manifest.json').write_text('{"dependencies":{"com.unity.modules.jsonserialize":"1.0.0"}}\n', encoding='utf-8')
        (project / 'ProjectSettings').mkdir()
        version_source = ROOT / 'Unity/ProjectSettings/ProjectVersion.txt' if name == 'Baseline2022' else native.PROJECT / 'ProjectSettings/ProjectVersion.txt'
        (project / 'ProjectSettings/ProjectVersion.txt').write_bytes(version_source.read_bytes())
        api.write(output / (name + '_Sources.json'), {'files': manifest(project, api)})
        report['projects'].append({'name': name, 'version': version, 'path': project.relative_to(ROOT).as_posix(),
                                   'sources': (output / (name + '_Sources.json')).relative_to(ROOT).as_posix(),
                                   'sourcesSHA256': api.sha(output / (name + '_Sources.json'))})
    need(api.freeze() == baseline and native.candidate_sources(api) == current_candidate, 'Payload94ProtectedProjectChangedDuringPreparation')
    report.update(status='PASS_MINIMAL_SERIALIZATION94_PREPARATION', mainInputsUnchanged=True, candidateInputsUnchanged=True,
                  modelSources=[{'path': relative, **baseline['files'][relative]} for relative in selected],
                  level={'path': LEVEL, **baseline['files'][LEVEL]})
    api.write(output / 'Preparation.json', report)
    print(json.dumps({'status': report['status'], 'projects': 2, 'modelSources': len(selected), 'preparation': (output / 'Preparation.json').relative_to(ROOT).as_posix()}), flush=True)


def run(prepared):
    api, native, processes, jobs, guards = readers()
    need(not processes.unity_pids(), 'Payload94SerialNativeExecutionRequired')
    prepared = Path(prepared).resolve()
    need(prepared.is_relative_to(OUT / 'Serialization') and prepared.name == 'Preparation.json', 'Payload94PreparedProjectProofRequired')
    proof = json.loads(prepared.read_text('utf-8-sig'))
    need(proof.get('status') == 'PASS_MINIMAL_SERIALIZATION94_PREPARATION'
         and proof.get('templateSHA256') == api.sha(TEMPLATE), 'Payload94UnchangedTemplateProofRequired')
    main_before = api.freeze()
    candidate_before = native.candidate_sources(api)
    need(main_before == json.loads((OUT / 'MainSources_Before.json').read_text('utf-8-sig')), 'Payload94ProtectedMainChanged')
    root = OUT / 'Serialization' / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    api.write(root / 'MainSources_before.json', main_before)
    api.write(root / 'CandidateSources_before.json', candidate_before)
    receipt = {'schemaVersion': 1, 'status': 'RUNNING_ACTUAL_TWO_ENGINE_PAYLOAD94', 'startedUtc': api.utc(),
               'runnerSHA256': api.sha(Path(__file__)), 'preparation': prepared.relative_to(ROOT).as_posix(),
               'preparationSHA256': api.sha(prepared), 'runs': [],
               'scope': 'Actual serial minimal2022/6000 model-only Editor processes and raw JsonUtility outputs. No original main/candidate project or trusted worker change; no provider/backend/device execution or acceptance waiver.'}
    api.write(root / 'Authorization.json', receipt)
    coordinates = None
    for name, version, editor in TARGETS:
        need(editor.is_file() and not processes.unity_pids(), 'Payload94ExactEditorAndIdleProcessRequired')
        project = relative_project(PROBES / name)
        declaration = next(row for row in proof['projects'] if row['name'] == name)
        initial = json.loads((ROOT / declaration['sources']).read_text('utf-8-sig'))['files']
        for relative, bound in initial.items():
            need((project / relative).is_file() and api.sha(project / relative) == bound['sha256'], 'Payload94ProbeInputChangedBeforeExecution')
        output = root / name
        output.mkdir()
        environment = dict(os.environ)
        environment.update(HOTR_SERIALIZATION94_OUT=str(output), HOTR_SERIALIZATION94_VERSION=version)
        environment.pop('HOTR_SERIALIZATION94_COORDINATES', None)
        if coordinates is not None:
            environment['HOTR_SERIALIZATION94_COORDINATES'] = coordinates
        command = [str(editor), '-batchmode', '-projectPath', str(project), '-executeMethod', ENTRY, '-logFile', str(output / 'Unity.log')]
        row = {'name': name, 'expectedUnity': version, 'project': project.relative_to(ROOT).as_posix(),
               'editorSHA256': api.sha(editor), 'explicitCoordinates': coordinates, 'startedUtc': api.utc(),
               'command': command, 'status': 'RUNNING_ACTUAL_NATIVE_PAYLOAD94'}
        process = job = None
        try:
            job = api.OwnedJob()
            startup = subprocess.STARTUPINFO();startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow = 0
            with (output / 'Console.log').open('x', encoding='utf-8') as stream:
                process = subprocess.Popen(command, cwd=project, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                                           creationflags=subprocess.CREATE_NO_WINDOW | 0x4, startupinfo=startup)
                job.assign(process.pid);jobs.resume_owned_primary(process)
                row['pid'] = process.pid;row['ownedJobAssignedBeforeResume'] = True
                try:
                    process.wait(timeout=360)
                except subprocess.TimeoutExpired:
                    row['timedOut'] = True;job.close();process.wait(timeout=20)
            native_path = output / 'Native.json'
            result = json.loads(native_path.read_text('utf-8-sig')) if native_path.is_file() else {}
            log = (output / 'Unity.log').read_text('utf-8-sig', errors='replace')
            found = re.search(r'Initialize engine version:\s*(\S+)', log)
            row.update(exitCode=process.returncode, nativeStatus=result.get('status', 'MISSING'),
                       actualEngineVersionFromLog=found.group(1) if found else None, nativeReportSHA256=api.sha(native_path) if native_path.exists() else None)
            need(process.returncode == 0 and not row.get('timedOut') and result.get('status') == 'PASS_ACTUAL_SERIALIZATION_PAYLOAD94'
                 and not result.get('error') and result.get('unity') == version == row['actualEngineVersionFromLog']
                 and len(result.get('payloads', [])) == 11, 'Payload94ActualNativeDiagnosticFailed')
            for payload in result['payloads']:
                path = output / payload['file']
                need(path.parent == output and api.sha(path) == payload['sha256'] and path.stat().st_size == payload['bytes'], 'Payload94NativeRawPayloadChanged')
            selected = ','.join(str(result[key]) for key in ('ax', 'ay', 'bx', 'by'))
            if name == 'Baseline2022':
                baseline = json.loads((ROOT / 'Verification/Evidence/Review93/Native/Set01/Cascade/LocalCascade.json').read_text('utf-8-sig'))
                accepted = next(item for item in baseline['rows'] if item['name'] == 'L1_match')
                need(api.sha(output / 'RawTurn.json') == accepted['turnHash'] and api.sha(output / 'FinalSnapshot.json') == accepted['finalHash'], 'Payload94OldProbeMustReproduceAcceptedL1Corpus')
                row['reproducesAccepted93L1RawTurnAndSnapshot'] = True
                coordinates = selected
            else:
                need(selected == coordinates and result.get('explicitCoordinates') is True, 'Payload94IdenticalExplicitActionRequired')
            row.update(status='PASS_ACTUAL_NATIVE_PAYLOAD94', payloads=result['payloads'])
        except Exception as error:
            row.update(status='FAIL_ACTUAL_NATIVE_PAYLOAD94', errorType=type(error).__name__, error=str(error))
        finally:
            if job: job.close()
            if process and process.poll() is None: process.kill();process.wait(timeout=20)
            row.update(finishedUtc=api.utc(), unityPidsAfter=processes.unity_pids(), unityLogSHA256=api.sha(output / 'Unity.log') if (output / 'Unity.log').exists() else None)
            for relative, bound in initial.items():
                need(api.sha(project / relative) == bound['sha256'], 'Payload94OriginalProbeInputsChangedDuringExecution')
            api.write(output / 'Invocation.json', row)
            receipt['runs'].append(row)
        if row['status'] != 'PASS_ACTUAL_NATIVE_PAYLOAD94' or row['unityPidsAfter']:
            break
    receipt.update(mainInputsUnchanged=api.freeze() == main_before, candidateInputsUnchanged=native.candidate_sources(api) == candidate_before,
                   completedUtc=api.utc(), unityPidsAfter=processes.unity_pids())
    receipt['status'] = ('RECORDED_ACTUAL_TWO_ENGINE_PAYLOAD94_REQUIRES_ANALYSIS' if len(receipt['runs']) == 2
                         and all(row['status'] == 'PASS_ACTUAL_NATIVE_PAYLOAD94' for row in receipt['runs'])
                         and receipt['mainInputsUnchanged'] and receipt['candidateInputsUnchanged'] and not receipt['unityPidsAfter']
                         else 'FAIL_ACTUAL_TWO_ENGINE_PAYLOAD94')
    api.write(root / 'Invocation.json', receipt)
    print(json.dumps({'status': receipt['status'], 'report': (root / 'Invocation.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if receipt['status'].startswith('RECORDED_') else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run'))
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--prepared', type=Path)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt': parser.error('Explicit root Windows action required')
    if args.action == 'prepare':
        need(args.out is not None and args.prepared is None, 'Payload94PreparationOutputRequired');prepare(args.out)
        return 0
    need(args.prepared is not None and args.out is None, 'Payload94PreparedProjectsRequired')
    return run(args.prepared)


if __name__ == '__main__':
    raise SystemExit(main())
