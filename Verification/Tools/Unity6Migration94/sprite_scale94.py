"""Root-only one-asset two-engine readback in the existing tiny private projects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid

import model_payload94 as base

ROOT, OUT, PROBES = base.ROOT, base.OUT, base.PROBES
PUBLIC = OUT / 'SpriteScale'
TEMPLATE = Path(__file__).with_name('Templates') / 'SpriteScale94.cs'
SOURCE = 'Unity/Assets/HeartOfTheRain/App/Teams/Art/TM_WellRally.png'
ASSET = 'Assets/ImporterScale94/TM_WellRally.png'
FIXTURE = 'Assets/Editor/SpriteScale94.cs'
ENTRY = 'HeartOfTheRain.Verification.SpriteScale94.Run'
COPY_FILES = {FIXTURE, FIXTURE + '.meta', 'Assets/ImporterScale94.meta', ASSET, ASSET + '.meta'}
PARITY_FIELDS = ('sourceWidth', 'sourceHeight', 'textureWidth', 'textureHeight', 'mipmapCount',
    'spriteMode', 'importerPPUBits', 'spritePPUBits', 'heightScalePPUBits', 'spriteRect',
    'importerBorder', 'spriteBorder', 'importerPivot', 'spritePivot', 'guid', 'spriteGuid',
    'textureGuid', 'spriteFileID', 'textureFileID', 'activeBuildTarget')


def need(value, code):
    base.need(value, code)


def binding(path, api):
    return {'path': Path(path).resolve().relative_to(ROOT).as_posix(),
            'sha256': api.sha(path), 'bytes': Path(path).stat().st_size}


def snapshot(project, api):
    result = {}
    for category in ('Assets', 'Packages', 'ProjectSettings', 'ProbeInputs'):
        for path in sorted((project / category).rglob('*')):
            if path.is_file():
                need(not path.is_symlink() and not getattr(path.stat(), 'st_file_attributes', 0) & 0x400
                     and path.stat().st_nlink == 1, 'SpriteScale94OrdinaryPrivateInputsRequired')
                result[path.relative_to(project).as_posix()] = {'sha256': api.sha(path), 'bytes': path.stat().st_size}
    return result


def verify_original(project, original, api):
    declaration = next(item for item in original['projects'] if item['name'] == project.name)
    manifest = ROOT / declaration['sources']
    need(api.sha(manifest) == declaration['sourcesSHA256'], 'SpriteScale94OriginalModelPreparationChanged')
    for relative, expected in json.loads(manifest.read_text('utf-8-sig'))['files'].items():
        need((project / relative).is_file() and api.sha(project / relative) == expected['sha256'],
             'SpriteScale94OriginalModelInputChanged')


def exactly_five_additions(before, after, expected):
    need(set(after) - set(before) == COPY_FILES and not set(before) - set(after)
         and all(after[key] == before[key] for key in before), 'SpriteScale94OnlyFiveFreshProbeAdditionsAllowed')
    need(set(expected) == COPY_FILES and all(after[key] == expected[key] for key in expected),
         'SpriteScale94ExactFivePreparedFileHashesRequired')


def compare_readbacks(baseline, candidate):
    need(all(key in baseline and key in candidate for key in PARITY_FIELDS), 'SpriteScale94CompleteNativeReadbacksRequired')
    return [{'field': key, 'baseline': baseline[key], 'candidate': candidate[key]}
            for key in PARITY_FIELDS if baseline[key] != candidate[key]]


def prepare(output, original_path):
    api, native, processes, _, guards = base.readers()
    need(not processes.unity_pids(), 'SpriteScale94NoConcurrentUnityForPreparation')
    output = guards.fresh_output(output)
    need(output.is_relative_to(PUBLIC), 'SpriteScale94FreshScopedPreparationRequired')
    original_path = Path(original_path).resolve()
    need(original_path.is_relative_to(OUT / 'Serialization') and original_path.name == 'Preparation.json',
         'SpriteScale94ExplicitOriginalModelPreparationRequired')
    original = json.loads(original_path.read_text('utf-8-sig'))
    need(original.get('status') == 'PASS_MINIMAL_SERIALIZATION94_PREPARATION', 'SpriteScale94PreparedExistingProjectsRequired')
    main, candidate = api.freeze(), native.candidate_sources(api)
    need(main == json.loads((OUT / 'MainSources_Before.json').read_text('utf-8-sig')), 'SpriteScale94ProtectedMainChanged')
    asset, meta = (ROOT / SOURCE).read_bytes(), (ROOT / (SOURCE + '.meta')).read_bytes()
    need(api.sha(ROOT / SOURCE) == main['files'][SOURCE]['sha256']
         and api.sha(ROOT / (SOURCE + '.meta')) == main['files'][SOURCE + '.meta']['sha256'], 'SpriteScale94OriginalArtworkAuthorityChanged')
    before = {}
    for name, _, _ in base.TARGETS:
        project = base.relative_project(PROBES / name); guards.reject_links(project)
        verify_original(project, original, api)
        need(not any((project / path).exists() for path in COPY_FILES)
             and not (project / 'Assets/ImporterScale94').exists(), 'SpriteScale94FreshPrivateCopiesRequired')
        need(not any(b'2942989e23b753738db9843c2436a5c9' in path.read_bytes()
                     for path in (project / 'Assets').rglob('*.meta')), 'SpriteScale94OriginalGuidMustNotCollide')
        before[name] = snapshot(project, api)
    output.mkdir(parents=True, exist_ok=False)
    api.write(output / 'MainSources_before.json', main); api.write(output / 'CandidateSources_before.json', candidate)
    report = {'schemaVersion': 1, 'status': 'RUNNING_SPRITE_SCALE94_PREPARATION', 'utc': api.utc(),
        'runnerSHA256': api.sha(Path(__file__)), 'templateSHA256': api.sha(TEMPLATE),
        'assetSHA256': api.sha(ROOT / SOURCE), 'metaSHA256': api.sha(ROOT / (SOURCE + '.meta')),
        'originalPreparation': binding(original_path, api), 'projects': [],
        'scope': 'Only five new files per existing tiny private probe: identical Editor fixture/meta, original PNG/meta, new folder meta. Main/full candidate and all prior original model inputs preserved. No native execution.'}
    for name, version, _ in base.TARGETS:
        project = base.relative_project(PROBES / name)
        bodies = {FIXTURE: TEMPLATE.read_bytes(), ASSET: asset, ASSET + '.meta': meta,
            FIXTURE + '.meta': ('fileFormatVersion: 2\nguid: ' + uuid.uuid4().hex + '\n').encode(),
            'Assets/ImporterScale94.meta': ('fileFormatVersion: 2\nguid: ' + uuid.uuid4().hex + '\nfolderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n').encode()}
        (project / 'Assets/ImporterScale94').mkdir(exist_ok=False)
        for relative, body in bodies.items():
            with (project / relative).open('xb') as stream:
                stream.write(body)
        after = snapshot(project, api)
        added = {relative: {'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
                 for relative, body in bodies.items()}
        exactly_five_additions(before[name], after, added)
        verify_original(project, original, api)
        api.write(output / (name + '_Before.json'), {'files': before[name]})
        api.write(output / (name + '_After.json'), {'files': after})
        report['projects'].append({'name': name, 'version': version,
            'before': binding(output / (name + '_Before.json'), api),
            'after': binding(output / (name + '_After.json'), api), 'addedFiles': added})
    need(main == api.freeze() and candidate == native.candidate_sources(api), 'SpriteScale94ProtectedProjectsChangedDuringPreparation')
    report.update(status='PREPARED_TWO_NATIVE_SPRITE_SCALE94_PROJECTS', mainInputsUnchanged=True, candidateInputsUnchanged=True)
    api.write(output / 'Preparation.json', report)
    print(json.dumps({'status': report['status'], 'preparation': (output / 'Preparation.json').relative_to(ROOT).as_posix()}), flush=True)


def run(prepared, output):
    api, native, processes, jobs, guards = base.readers()
    need(not processes.unity_pids(), 'SpriteScale94SerialNativeExecutionRequired')
    prepared = Path(prepared).resolve(); output = guards.fresh_output(output)
    need(prepared.is_relative_to(PUBLIC) and prepared.name == 'Preparation.json'
         and output.is_relative_to(PUBLIC), 'SpriteScale94ExplicitScopedInputsRequired')
    proof = json.loads(prepared.read_text('utf-8-sig'))
    need(proof.get('status') == 'PREPARED_TWO_NATIVE_SPRITE_SCALE94_PROJECTS'
         and proof['templateSHA256'] == api.sha(TEMPLATE), 'SpriteScale94BoundIdenticalTemplateRequired')
    original_path = ROOT / proof['originalPreparation']['path']
    need(binding(original_path, api) == proof['originalPreparation'], 'SpriteScale94OriginalPreparationBindingChanged')
    original = json.loads(original_path.read_text('utf-8-sig'))
    main, candidate = api.freeze(), native.candidate_sources(api)
    need(main == json.loads((OUT / 'MainSources_Before.json').read_text('utf-8-sig')), 'SpriteScale94ProtectedMainChanged')
    output.mkdir(parents=True, exist_ok=False)
    api.write(output / 'MainSources_before.json', main); api.write(output / 'CandidateSources_before.json', candidate)
    receipt = {'schemaVersion': 1, 'status': 'RUNNING_TWO_NATIVE_SPRITE_SCALE94', 'utc': api.utc(),
        'runnerSHA256': api.sha(Path(__file__)), 'preparation': binding(prepared, api), 'runs': [],
        'scope': 'Actual serial 2022/6000 Android-target Editor readbacks of one identical original PNG/meta in tiny private projects. No original main/full-candidate edits, importer correction, model command, trusted-worker change or device/release acceptance.'}
    api.write(output / 'Authorization.json', receipt)
    readbacks = []
    for name, version, editor in base.TARGETS:
        project = base.relative_project(PROBES / name); declaration = next(row for row in proof['projects'] if row['name'] == name)
        need(editor.is_file() and not processes.unity_pids(), 'SpriteScale94ExactIdleEditorRequired')
        verify_original(project, original, api)
        after_manifest = ROOT / declaration['after']['path']
        need(binding(after_manifest, api) == declaration['after']
             and snapshot(project, api) == json.loads(after_manifest.read_text('utf-8-sig'))['files'],
             'SpriteScale94AllPreparedPrivateInputsMustMatch')
        for relative, expected in declaration['addedFiles'].items():
            need(api.sha(project / relative) == expected['sha256'], 'SpriteScale94PreparedCopyChangedBeforeNative')
        before = snapshot(project, api)
        folder = output / name; folder.mkdir()
        environment = dict(os.environ); environment.update(HOTR_SCALE94_OUT=str(folder), HOTR_SCALE94_VERSION=version, HOTR_SCALE94_PREPARED=str(prepared))
        command = [str(editor), '-batchmode', '-projectPath', str(project), '-buildTarget', 'Android',
                   '-executeMethod', ENTRY, '-logFile', str(folder / 'Unity.log')]
        row = {'name': name, 'expectedUnity': version, 'command': command, 'editorSHA256': api.sha(editor), 'startedUtc': api.utc()}
        process = job = None
        try:
            job = api.OwnedJob(); startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
            with (folder / 'Console.log').open('x', encoding='utf-8') as stream:
                process = subprocess.Popen(command, cwd=project, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW | 0x4, startupinfo=startup)
                job.assign(process.pid); jobs.resume_owned_primary(process); row.update(pid=process.pid, ownedJobAssignedBeforeResume=True)
                try: process.wait(timeout=360)
                except subprocess.TimeoutExpired: row['timedOut'] = True; job.close(); process.wait(timeout=20)
            path = folder / 'Native.json'; result = json.loads(path.read_text('utf-8-sig')) if path.is_file() else {}
            match = re.search(r'Initialize engine version:\s*(\S+)', (folder / 'Unity.log').read_text('utf-8-sig', errors='replace'))
            row.update(exitCode=process.returncode, actualEngineVersionFromLog=match.group(1) if match else None,
                nativeStatus=result.get('status', 'MISSING'), nativeError=result.get('error'))
            need(process.returncode == 0 and not row.get('timedOut') and result.get('status') == 'RECORDED_NATIVE_SPRITE_SCALE94_REQUIRES_COMPARISON'
                 and not result.get('error') and result.get('unity') == version == row['actualEngineVersionFromLog']
                 and result.get('inputPNGUnchanged') is True, 'SpriteScale94ActualNativeReadbackFailed')
            row.update(status='RECORDED_NATIVE_SPRITE_SCALE94', nativeReport=binding(path, api), checks=result['checks'])
            readbacks.append(result)
        except Exception as error:
            row.update(status='FAIL_NATIVE_SPRITE_SCALE94', errorType=type(error).__name__, error=str(error))
        finally:
            if job: job.close()
            if process and process.poll() is None: process.kill(); process.wait(timeout=20)
            after = snapshot(project, api)
            original_changes = [relative for relative in before if not relative.startswith(('ProjectSettings/', 'Packages/'))
                and relative != ASSET + '.meta' and after.get(relative) != before[relative]]
            row['preexistingAssetOrInputChanges'] = original_changes
            row['unexpectedAddedAssets'] = sorted(relative for relative in set(after) - set(before)
                                                   if relative.startswith('Assets/'))
            row['privateConfigurationChanges'] = [relative for relative in sorted(set(before) | set(after))
                if relative.startswith(('ProjectSettings/', 'Packages/')) and before.get(relative) != after.get(relative)]
            row['copiedMetaAfterNative'] = binding(project / (ASSET + '.meta'), api)
            if original_changes or row['unexpectedAddedAssets']: row['status'] = 'FAIL_NATIVE_SPRITE_SCALE94_PRESERVATION'
            verify_original(project, original, api)
            api.write(folder / 'Sources_before.json', {'files': before}); api.write(folder / 'Sources_after.json', {'files': after})
            row.update(finishedUtc=api.utc(), unityPidsAfter=processes.unity_pids(),
                       unityLog=binding(folder / 'Unity.log', api) if (folder / 'Unity.log').exists() else None)
            api.write(folder / 'Invocation.json', row); receipt['runs'].append(row)
        if row['status'] != 'RECORDED_NATIVE_SPRITE_SCALE94' or row['unityPidsAfter']: break
    receipt.update(mainInputsUnchanged=api.freeze() == main, candidateInputsUnchanged=native.candidate_sources(api) == candidate,
        completedUtc=api.utc(), unityPidsAfter=processes.unity_pids())
    receipt['readbackDifferences'] = compare_readbacks(*readbacks) if len(readbacks) == 2 else None
    receipt['status'] = ('PASS_TWO_ENGINE_SPRITE_SCALE94_READBACK_PARITY' if len(readbacks) == 2
        and all(row['status'] == 'RECORDED_NATIVE_SPRITE_SCALE94' for row in receipt['runs'])
        and receipt['readbackDifferences'] == [] and receipt['mainInputsUnchanged'] and receipt['candidateInputsUnchanged']
        and not receipt['unityPidsAfter'] else 'FAIL_TWO_ENGINE_SPRITE_SCALE94')
    api.write(output / 'Invocation.json', receipt)
    print(json.dumps({'status': receipt['status'], 'report': (output / 'Invocation.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if receipt['status'].startswith('PASS_') else 1


def main():
    cli = argparse.ArgumentParser(description=__doc__); cli.add_argument('action', choices=('prepare', 'run'))
    cli.add_argument('--execute', action='store_true'); cli.add_argument('--out', type=Path, required=True)
    cli.add_argument('--original', type=Path); cli.add_argument('--prepared', type=Path); args = cli.parse_args()
    if not args.execute or os.name != 'nt': cli.error('Explicit root Windows execution required')
    if args.action == 'prepare':
        need(args.original is not None and args.prepared is None, 'SpriteScale94OriginalPreparationArgumentRequired')
        prepare(args.out, args.original); return 0
    need(args.prepared is not None and args.original is None, 'SpriteScale94PreparedArgumentRequired')
    return run(args.prepared, args.out)


if __name__ == '__main__':
    raise SystemExit(main())
