"""Root-only exact two-private-file correction; preserves all earlier receipts."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import sprite_scale94 as scale

ROOT, OUT, PROBES = scale.ROOT, scale.OUT, scale.PROBES
OLD_OUTPUT = '                Check(output.StartsWith(Path.Combine(workspace.FullName,"Verification/Evidence/Unity6Migration94/SpriteScale")+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase),"Scoped sprite-scale output required");'
NEW_OUTPUT = '                string allowed=Path.GetFullPath(Path.Combine(workspace.FullName,"Verification/Evidence/Unity6Migration94/SpriteScale"))+Path.DirectorySeparatorChar;\n                Check(output.StartsWith(allowed,StringComparison.OrdinalIgnoreCase),"Scoped sprite-scale output required");'
OLD_PREPARED = 'Path.GetFullPath(prepared).StartsWith(Path.Combine(workspace.FullName,"Verification/Evidence/Unity6Migration94/SpriteScale")+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)'
NEW_PREPARED = 'Path.GetFullPath(prepared).StartsWith(allowed,StringComparison.OrdinalIgnoreCase)'


def corrected(before):
    text = before.decode('utf-8')
    scale.need(text.count(OLD_OUTPUT) == text.count(OLD_PREPARED) == 1
               and NEW_OUTPUT not in text and NEW_PREPARED not in text, 'SpriteScale94ExactOldGuardAnchorsRequired')
    return text.replace(OLD_OUTPUT, NEW_OUTPUT, 1).replace(OLD_PREPARED, NEW_PREPARED, 1).encode('utf-8')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--execute', action='store_true'); cli.add_argument('--prior', type=Path, required=True)
    cli.add_argument('--out', type=Path, required=True); args = cli.parse_args()
    if not args.execute or os.name != 'nt': cli.error('Explicit root Windows correction required')
    api, native, processes, _, guards = scale.base.readers()
    scale.need(not processes.unity_pids(), 'SpriteScale94NoConcurrentUnityDuringGuardRepair')
    prior_path = args.prior.resolve(); output = guards.fresh_output(args.out)
    scale.need(prior_path.is_relative_to(scale.PUBLIC) and prior_path.name == 'Preparation.json'
               and output.is_relative_to(scale.PUBLIC), 'SpriteScale94ScopedPriorAndFreshOutputRequired')
    prior = json.loads(prior_path.read_text('utf-8-sig'))
    scale.need(prior.get('status') == 'PREPARED_TWO_NATIVE_SPRITE_SCALE94_PROJECTS', 'SpriteScale94PriorPreparedCopiesRequired')
    original_path = ROOT / prior['originalPreparation']['path']
    scale.need(scale.binding(original_path, api) == prior['originalPreparation'], 'SpriteScale94OriginalPreparationChanged')
    original = json.loads(original_path.read_text('utf-8-sig'))
    main, candidate = api.freeze(), native.candidate_sources(api)
    scale.need(main == json.loads((OUT / 'MainSources_Before.json').read_text('utf-8-sig')), 'SpriteScale94MainBaselineChanged')
    scale.need(api.sha(ROOT / scale.SOURCE) == prior['assetSHA256']
               and api.sha(ROOT / (scale.SOURCE + '.meta')) == prior['metaSHA256'], 'SpriteScale94OriginalArtOrMetaChanged')
    new = scale.TEMPLATE.read_bytes(); prepared = []
    for name, version, _ in scale.base.TARGETS:
        project = scale.base.relative_project(PROBES / name); guards.reject_links(project)
        scale.verify_original(project, original, api)
        declaration = next(row for row in prior['projects'] if row['name'] == name)
        for relative, expected in declaration['addedFiles'].items():
            scale.need(api.sha(project / relative) == expected['sha256'], 'SpriteScale94FiveCopiedInputsMustRetainPriorHashes')
        source = project / scale.FIXTURE; old = source.read_bytes()
        scale.need(hashlib.sha256(old).hexdigest() == prior['templateSHA256'] and corrected(old) == new,
                   'SpriteScale94OnlyCanonicalGuardTransformationAllowed')
        prepared.append((name, version, project, declaration, old, scale.snapshot(project, api)))
    output.mkdir(parents=True, exist_ok=False)
    api.write(output / 'MainSources_before.json', main); api.write(output / 'CandidateSources_before.json', candidate)
    report = {key: value for key, value in prior.items() if key not in ('projects', 'scope', 'utc', 'runnerSHA256')}
    report.update(utc=api.utc(), runnerSHA256=api.sha(Path(__file__)), projects=[],
        guardRepairOnly=True, oldPreparation=scale.binding(prior_path, api),
        templateSHA256=api.sha(scale.TEMPLATE), originalTemplateSHA256=prior['templateSHA256'],
        scope='Exactly two existing private SpriteScale94.cs files receive the reviewed canonical Windows containment guards. PNG/meta, all other existing inputs, normal Editor-created private configuration, old preparations/reports, main and full candidate are preserved. No native execution.')
    for name, version, project, declaration, old, before in prepared:
        source = project / scale.FIXTURE
        with source.open('wb') as stream: stream.write(new)
        after = scale.snapshot(project, api)
        scale.need(set(before) == set(after) and [path for path in before if before[path] != after[path]] == [scale.FIXTURE],
                   'SpriteScale94ExactlyOneExistingFixtureChangedPerPrivateProject')
        added = dict(declaration['addedFiles']); added[scale.FIXTURE] = after[scale.FIXTURE]
        scale.need(set(added) == scale.COPY_FILES and all(after[path] == value for path, value in added.items()),
                   'SpriteScale94FiveOriginalCopyDeclarationsRetainedExceptFixtureGuard')
        scale.verify_original(project, original, api)
        api.write(output / (name + '_Before.json'), {'files': before})
        api.write(output / (name + '_After.json'), {'files': after})
        report['projects'].append({'name': name, 'version': version,
            'before': scale.binding(output / (name + '_Before.json'), api),
            'after': scale.binding(output / (name + '_After.json'), api), 'addedFiles': added,
            'correctedPath': scale.FIXTURE, 'beforeFixtureSHA256': hashlib.sha256(old).hexdigest(),
            'afterFixtureSHA256': api.sha(source)})
    scale.need(main == api.freeze() and candidate == native.candidate_sources(api), 'SpriteScale94ProtectedInputsChangedDuringGuardRepair')
    report.update(mainInputsUnchanged=True, candidateInputsUnchanged=True,
                  status='PREPARED_TWO_NATIVE_SPRITE_SCALE94_PROJECTS', correctedPrivateFiles=2)
    api.write(output / 'Preparation.json', report)
    print(json.dumps({'status': report['status'], 'correctedPrivateFiles': 2,
                      'preparation': (output / 'Preparation.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
