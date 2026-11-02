"""Root-only 350-command raw payload collection in existing two private model probes."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

import model_payload94 as base
import compare_model94 as historical
import diagnose_json94 as diagnostic

ROOT, OUT, PROBES = base.ROOT, base.OUT, base.PROBES
TEMPLATE = Path(__file__).with_name('Templates') / 'SerializationCorpus94.cs'
ENTRY = 'HeartOfTheRain.Verification.SerializationCorpus94.Run'
SCOPE = 'Actual two-engine model-only350-command raw export. Every raw SHA difference retained; exact Decimal token values and binary32 bits separately diagnosed without rounding tolerance. No original main/candidate changes, trusted-worker re-pin, backend execution, pixels, device, performance or release certification.'


def need(value, code):
    base.need(value, code)


def binding(path, api):
    return {'path': path.resolve().relative_to(ROOT).as_posix(), 'sha256': api.sha(path), 'bytes': path.stat().st_size}


def verify_project_inputs(project, preparation, api):
    declaration = next(row for row in preparation['projects'] if row['name'] == project.name)
    expected = json.loads((ROOT / declaration['sources']).read_text('utf-8-sig'))['files']
    need(api.sha(ROOT / declaration['sources']) == declaration['sourcesSHA256'], 'Corpus94OriginalPreparationChanged')
    for relative, bound in expected.items():
        source = project / relative
        need(source.is_file() and api.sha(source) == bound['sha256'], 'Corpus94OriginalProbeInputChanged')


def prepare(output, original):
    api, native, processes, _, guards = base.readers()
    need(not processes.unity_pids(), 'Corpus94NoConcurrentUnityDuringPreparation')
    output = guards.fresh_output(output)
    original = Path(original).resolve()
    need(original.is_relative_to(OUT / 'Serialization') and original.name == 'Preparation.json', 'Corpus94OriginalPreparationRequired')
    proof = json.loads(original.read_text('utf-8-sig'))
    need(proof.get('status') == 'PASS_MINIMAL_SERIALIZATION94_PREPARATION', 'Corpus94PreparedMinimalProjectsRequired')
    main = api.freeze(); candidate = native.candidate_sources(api)
    need(main == json.loads((OUT / 'MainSources_Before.json').read_text('utf-8-sig')), 'Corpus94ProtectedMainChanged')
    levels = ['Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L' + str(number).zfill(3) + '.json' for number in range(1, 51)]
    for relative in levels:
        need(api.sha(ROOT / relative) == main['files'][relative]['sha256'], 'Corpus94AuthoredLevelChanged')
    # Preflight BOTH before writing either; never overwrite an existing fixture or input copy.
    for name, _, _ in base.TARGETS:
        project = base.relative_project(PROBES / name); guards.reject_links(project)
        verify_project_inputs(project, proof, api)
        need(not (project / 'Assets/Editor/SerializationCorpus94.cs').exists()
             and not (project / 'Assets/Editor/SerializationCorpus94.cs.meta').exists()
             and not (project / 'ProbeInputs/Corpus94').exists(), 'Corpus94FreshFixtureAndLevelCopiesRequired')
    output.mkdir(parents=True, exist_ok=False)
    api.write(output / 'MainSources_before.json', main); api.write(output / 'CandidateSources_before.json', candidate)
    report = {'schemaVersion': 1, 'scope': SCOPE, 'status': 'RUNNING_CORPUS94_PREPARATION', 'utc': api.utc(),
              'runnerSHA256': api.sha(Path(__file__)), 'template': binding(TEMPLATE, api),
              'originalPreparation': binding(original, api), 'projects': [], 'levels': [binding(ROOT / p, api) for p in levels]}
    for name, version, _ in base.TARGETS:
        project = base.relative_project(PROBES / name)
        additions = {}
        fixture = project / 'Assets/Editor/SerializationCorpus94.cs'
        with fixture.open('xb') as stream: stream.write(TEMPLATE.read_bytes())
        with fixture.with_suffix('.cs.meta').open('x', encoding='utf-8') as stream:
            stream.write('fileFormatVersion: 2\nguid: 6472a41b2d784c439f99b1c54529c694\n')
        target = project / 'ProbeInputs/Corpus94'; target.mkdir(exist_ok=False)
        for relative in levels:
            source, copy = ROOT / relative, target / Path(relative).name
            with copy.open('xb') as stream: stream.write(source.read_bytes())
            need(api.sha(copy) == api.sha(source) and copy.stat().st_nlink == 1, 'Corpus94OrdinaryExactLevelCopyRequired')
        for source in [fixture, fixture.with_suffix('.cs.meta'), *sorted(target.iterdir())]:
            additions[source.relative_to(project).as_posix()] = {'sha256': api.sha(source), 'bytes': source.stat().st_size}
        verify_project_inputs(project, proof, api)
        report['projects'].append({'name': name, 'version': version, 'addedFiles': additions})
    need(main == api.freeze() and candidate == native.candidate_sources(api), 'Corpus94ProtectedProjectChanged')
    report.update(status='PASS_CORPUS94_PREPARATION', mainInputsUnchanged=True, candidateInputsUnchanged=True)
    api.write(output / 'Preparation.json', report)
    print(json.dumps({'status': report['status'], 'preparation': (output / 'Preparation.json').relative_to(ROOT).as_posix()}), flush=True)


def verify_prepared(proof, api):
    need(proof.get('status') == 'PASS_CORPUS94_PREPARATION' and proof['template'] == binding(TEMPLATE, api), 'Corpus94ExactPreparedFixtureRequired')
    original = ROOT / proof['originalPreparation']['path']
    need(binding(original, api) == proof['originalPreparation'], 'Corpus94OriginalPreparationBindingChanged')
    old = json.loads(original.read_text('utf-8-sig'))
    for declaration in proof['projects']:
        project = base.relative_project(PROBES / declaration['name'])
        verify_project_inputs(project, old, api)
        for relative, bound in declaration['addedFiles'].items():
            path = project / relative
            need(path.is_file() and api.sha(path) == bound['sha256'] and path.stat().st_size == bound['bytes'], 'Corpus94PreparedInputChanged')


def native_rows(report, directory, api, corpus):
    need(report.get('status') == 'PASS_ACTUAL_SERIALIZATION_CORPUS94' and not report.get('error') and len(report.get('rows', [])) == 350, 'Corpus94ActualNativeCompleteExportRequired')
    rows = {row['name']: row for row in report['rows']}
    need(len(rows) == 350 and set(rows) == historical.expected_names(), 'Corpus94ExactUnique350NamesRequired')
    references = historical.validate_rows(corpus)
    for name, row in rows.items():
        payloads = {payload['name']: payload for payload in row['payloads']}
        need(len(row['payloads']) == len(payloads) == 3 and set(payloads) == {'RawTurn', 'FinalSnapshot', 'FinalCheckpoint'}, 'Corpus94ExactThreePayloadsRequired')
        for item in payloads.values():
            path = directory / item['file']
            need(item['file'] == name + '_' + item['name'] + '.json' and path.parent == directory
                 and api.sha(path) == item['sha256'] and path.stat().st_size == item['bytes'], 'Corpus94NativePayloadTampered')
        need(payloads['RawTurn']['sha256'] == references[name]['turnHash']
             and payloads['FinalSnapshot']['sha256'] == references[name]['finalHash'], 'Corpus94NativeMustReproduceFull350AcceptedCorpus')
    return rows


def run(prepared, candidate_corpus):
    api, native, processes, jobs, guards = base.readers()
    need(not processes.unity_pids(), 'Corpus94SerialNativeOnly')
    prepared = Path(prepared).resolve(); candidate_corpus = Path(candidate_corpus).resolve()
    need(prepared.is_relative_to(OUT / 'SerializationCorpus') and prepared.name == 'Preparation.json', 'Corpus94PreparedReportRequired')
    need(candidate_corpus.is_relative_to(OUT / 'Native') and candidate_corpus.name == 'LocalCascade.json', 'Corpus94ActualFullCandidateCorpusRequired')
    proof = json.loads(prepared.read_text('utf-8-sig')); verify_prepared(proof, api)
    old, _, _ = historical.validate_baseline()
    candidate_data = historical.read(candidate_corpus)
    historical.validate_candidate_invocation(historical.read(candidate_corpus.parent / 'Invocation.json'), candidate_data, candidate_corpus, candidate_corpus.parent / 'Unity.log')
    main = api.freeze(); candidate = native.candidate_sources(api)
    need(main == historical.read(OUT / 'MainSources_Before.json'), 'Corpus94ProtectedMainChanged')
    need(candidate == historical.read(candidate_corpus.parent / 'CandidateSources_after.json'), 'Corpus94ActualCandidateSourceDrift')
    directory = OUT / 'SerializationCorpus' / uuid.uuid4().hex; directory.mkdir(parents=True, exist_ok=False)
    api.write(directory / 'MainSources_before.json', main); api.write(directory / 'CandidateSources_before.json', candidate)
    receipt = {'schemaVersion': 1, 'scope': SCOPE, 'status': 'RUNNING_TWO_ENGINE_CORPUS94', 'startedUtc': api.utc(),
               'runnerSHA256': api.sha(Path(__file__)), 'diagnosticSHA256': api.sha(Path(diagnostic.__file__)),
               'preparation': binding(prepared, api), 'candidateCorpus': binding(candidate_corpus, api),
               'baselineCorpus': binding(historical.BASELINE, api), 'runs': []}
    api.write(directory / 'Authorization.json', receipt)
    for name, version, editor in base.TARGETS:
        verify_prepared(proof, api)
        need(not processes.unity_pids() and editor.is_file(), 'Corpus94ExactIdleEditorRequired')
        project = base.relative_project(PROBES / name); output = directory / name; output.mkdir()
        environment = dict(os.environ); environment.update(HOTR_CORPUS94_OUT=str(output), HOTR_CORPUS94_VERSION=version)
        environment.pop('HOTR_CORPUS94_BASELINE', None)
        if name == 'Candidate6': environment['HOTR_CORPUS94_BASELINE'] = str(directory / 'Baseline2022/Native.json')
        command = [str(editor), '-batchmode', '-projectPath', str(project), '-executeMethod', ENTRY, '-logFile', str(output / 'Unity.log')]
        row = {'name': name, 'expectedUnity': version, 'command': command, 'editorSHA256': api.sha(editor), 'startedUtc': api.utc()}
        process = job = None
        try:
            job = api.OwnedJob(); startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
            with (output / 'Console.log').open('x', encoding='utf-8') as stream:
                process = subprocess.Popen(command, cwd=project, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                                           creationflags=subprocess.CREATE_NO_WINDOW | 0x4, startupinfo=startup)
                job.assign(process.pid); jobs.resume_owned_primary(process); row.update(pid=process.pid, ownedJobAssignedBeforeResume=True)
                try: process.wait(timeout=600)
                except subprocess.TimeoutExpired: row['timedOut'] = True; job.close(); process.wait(timeout=20)
            report_path = output / 'Native.json'; result = historical.read(report_path)
            match = re.search(r'Initialize engine version:\s*(\S+)', (output / 'Unity.log').read_text('utf-8-sig', errors='replace'))
            row.update(exitCode=process.returncode, nativeStatus=result.get('status'), actualEngineVersionFromLog=match.group(1) if match else None)
            need(process.returncode == 0 and not row.get('timedOut') and result.get('unity') == version == row['actualEngineVersionFromLog'], 'Corpus94ExactActualNativeProcessRequired')
            native_rows(result, output, api, old if name == 'Baseline2022' else candidate_data)
            need(name != 'Candidate6' or result.get('explicitBaselineCommands') is True, 'Corpus94ExplicitBaselineCommandAgreementRequired')
            row.update(status='PASS_ACTUAL_NATIVE_CORPUS94', nativeReport=binding(report_path, api), checks=result['checks'], payloads=1050, reproducesExact350ReferenceHashes=True)
        except Exception as error:
            row.update(status='FAIL_ACTUAL_NATIVE_CORPUS94', errorType=type(error).__name__, error=str(error))
        finally:
            if job: job.close()
            if process and process.poll() is None: process.kill(); process.wait(timeout=20)
            row.update(finishedUtc=api.utc(), unityPidsAfter=processes.unity_pids(), unityLog=binding(output / 'Unity.log', api) if (output / 'Unity.log').exists() else None)
            api.write(output / 'Invocation.json', row); receipt['runs'].append(row)
        if row['status'] != 'PASS_ACTUAL_NATIVE_CORPUS94' or row['unityPidsAfter']: break
    receipt.update(mainInputsUnchanged=api.freeze() == main, candidateInputsUnchanged=native.candidate_sources(api) == candidate,
                   completedUtc=api.utc(), unityPidsAfter=processes.unity_pids())
    verify_prepared(proof, api)
    receipt['status'] = ('RECORDED_ACTUAL_TWO_ENGINE_CORPUS94_REQUIRES_ANALYSIS' if len(receipt['runs']) == 2 and all(row['status'] == 'PASS_ACTUAL_NATIVE_CORPUS94' for row in receipt['runs'])
                         and receipt['mainInputsUnchanged'] and receipt['candidateInputsUnchanged'] and not receipt['unityPidsAfter'] else 'FAIL_ACTUAL_TWO_ENGINE_CORPUS94')
    api.write(directory / 'Invocation.json', receipt)
    print(json.dumps({'status': receipt['status'], 'report': (directory / 'Invocation.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if receipt['status'].startswith('RECORDED_') else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('action', choices=('prepare', 'run'))
    parser.add_argument('--execute', action='store_true'); parser.add_argument('--out', type=Path); parser.add_argument('--original', type=Path)
    parser.add_argument('--prepared', type=Path); parser.add_argument('--candidate-corpus', type=Path); args = parser.parse_args()
    if not args.execute or os.name != 'nt': parser.error('Explicit root Windows action required')
    if args.action == 'prepare':
        need(args.out is not None and args.original is not None and args.prepared is None and args.candidate_corpus is None, 'Corpus94FreshPreparationArgumentsRequired')
        prepare(args.out, args.original); return 0
    need(args.prepared is not None and args.candidate_corpus is not None and args.out is None and args.original is None, 'Corpus94NativeRunArgumentsRequired')
    return run(args.prepared, args.candidate_corpus)


if __name__ == '__main__':
    raise SystemExit(main())
