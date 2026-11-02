"""Describe final checkpoint74/75 native spans, without a speedup verdict.

No Unity, ADB, image extraction or device work. Reports must have the same
instrument schema and seeded model hashes. Separate process/OS/cache conditions
prevent assigning cross-run changes to one optimization.
"""
import argparse
import hashlib
import json
import runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / 'Verification/Evidence/Gameplay75'
BASE = ROOT / 'Verification/Evidence/Gameplay74'
PROFILE = runpy.run_path(str(Path(__file__).with_name('validate_gameplay74_profile.py')),
                        run_name='candidate_final_profile_contract_only')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recorded_after(report, installation):
    parse = lambda value: datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    assert parse(report['utc']) >= parse(installation['utc']), 'Native report predates its recorded installation'


def difference(old, new, fields):
    return {key: {'baseline74': old[key], 'final75': new[key], 'finalMinusBaseline74': new[key] - old[key]}
            for key in fields}


def build(out=DEFAULT_OUT):
    out = out.resolve()
    candidate = BASE.resolve()
    bindings = {}

    def read(folder, name):
        path = (folder / name).resolve()
        assert path.is_relative_to(folder) and path.is_file(), str(path)
        value = json.loads(path.read_text('utf-8-sig'))
        assert not any(value.get(k) for k in ['errors', 'failures', 'error']), str(path)
        bindings[path.relative_to(ROOT).as_posix()] = sha(path)
        return value

    final_artifact, old_artifact = read(out, 'APK_Artifact.json'), read(candidate, 'APK_Artifact.json')
    final_sha, old_sha = final_artifact['sha256'], old_artifact['sha256']
    assert final_sha != old_sha, 'Candidate is still installed as the purported final artifact'

    def cascade(folder, digest):
        report = read(folder, 'Android/Cascade/measure/Report.json')
        install = read(folder, 'Android/Cascade/measure/Installation.json')
        assert install['apk_sha256'] == install['installed_apk_sha256'] == digest
        assert install['serial'] == 'emulator-5556' and install['data_unchanged']
        recorded_after(report, install)
        baseline = read(BASE, 'Android/Cascade/measure/Report.json')
        hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in baseline['rows']}
        assert report['repeats'] == 1 and len(report['rows']) == 6
        return report, PROFILE['validate'](report, 'measure', hashes)

    old_raw, old_profile = cascade(candidate, old_sha)
    final_raw, final_profile = cascade(out, final_sha)
    assert old_raw['profilingSchemaVersion'] == final_raw['profilingSchemaVersion'] == 1
    old_cases = {r['name']: r for r in old_profile['rows']}
    rows = []
    for row in final_profile['rows']:
        prior = old_cases[row['name']]
        rows.append({'name': row['name'], 'scope': 'Same model fixture and diagnostic schema; separate processes/runs.',
            'command': difference(prior, row, ['legalSearchMs', 'fixtureSetupMs', 'modelMs', 'acceptMs', 'commandMs',
                'queueInspectionMs', 'totalSynchronousProbeMs', 'firstCommandRenderMs', 'commandFrameAfterUpdateElapsedMs']),
            'enqueue': difference(prior['enqueueCost'], row['enqueueCost'], PROFILE['COMMAND_STAGES']),
            'medianRenderStageMs': difference(prior['medianRenderStageMs'], row['medianRenderStageMs'], PROFILE['FRAME_STAGES']),
            'maxRenderStageMs': difference(prior['maxRenderStageMs'], row['maxRenderStageMs'], PROFILE['FRAME_STAGES']),
            'resourceActivity': difference(prior, row, ['geometryMisses', 'meshSlotsCreated']),
            'maxIntervalMs': difference(prior, row, ['maxIntervalMs'])['maxIntervalMs']})

    old_fluid = read(candidate, 'Android/Fluidity/Measurement.json')
    final_fluid = read(out, 'Android/Fluidity/Measurement.json')
    old_fluid_install = read(candidate, 'Android/Fluidity/Installation.json')
    final_fluid_install = read(out, 'Android/Fluidity/Installation.json')
    for report in [old_fluid, final_fluid]:
        assert report['status'] == 'RECORDED_NATIVE_FLUIDITY' and report['launchCleared'] and report['isolatedProfile']
        assert len(report['phases']) == 8
        assert {r['name'] for r in report['phases']} == {'idle_including_hint_search', 'natural_first', 'natural_second',
            'rocket', 'three_rocket_chain', 'orb_rocket', 'golden_bomb', 'victory_animation'}
    for installation, digest in [(old_fluid_install, old_sha), (final_fluid_install, final_sha)]:
        assert installation['serial'] == 'emulator-5556'
        assert installation.get('apk_sha256', installation.get('sha256')) == digest
    recorded_after(old_fluid, old_fluid_install)
    recorded_after(final_fluid, final_fluid_install)
    old_phases = {r['name']: r for r in old_fluid['phases']}
    phase_rows = []
    for row in final_fluid['phases']:
        prior = old_phases[row['name']]
        keys = ['modelMs', 'acceptMs', 'commandMs', 'firstPresentationMs', 'preparationSeconds',
                'settleSeconds', 'p95Ms', 'worstMs', 'spriteCreates', 'synchronousTextureLoads',
                'gen0Collections', 'poolAtReady', 'poolAtEnd', 'peakCachedSprites', 'bankSpriteHighWater']
        phase_rows.append({'name': row['name'], 'metrics': difference(prior, row, keys),
            'additionalFirstUseFields': {'baseline74': {k: v for k, v in prior.items() if 'warm' in k.lower()},
                                         'final75': {k: v for k, v in row.items() if 'warm' in k.lower()}},
            'scope': 'Prepared board. Natural first/second reuse their actual process/bank context; injected power '
                     'fixtures reload. firstPresentationMs is phase dispatch, not first displayed pose.'})

    density_rows, missing_candidate, missing_final = {}, [], []
    for family in ['crate', 'stone', 'gate', 'tiles']:
        folder = 'Android/Density/candidate_review-' + family + '/'
        if not (candidate / folder / 'Report.json').is_file():
            missing_candidate.append(family)
            continue
        if not (out / folder / 'Report.json').is_file():
            missing_final.append(family)
            continue
        baseline = read(BASE, folder + 'Report.json')
        hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in baseline['rows']}
        old, final = read(candidate, folder + 'Report.json'), read(out, folder + 'Report.json')
        for directory, digest in [(candidate, old_sha), (out, final_sha)]:
            installation = read(directory, folder + 'Installation.json')
            assert installation['serial'] == 'emulator-5556'
            assert installation['apk_sha256'] == installation['installed_apk_sha256'] == digest
            recorded_after(old if directory == candidate else final, installation)
        old_summary = PROFILE['validate_density'](old, family, hashes)
        final_summary = PROFILE['validate_density'](final, family, hashes)
        prior_rows = {r['name']: r for r in old_summary['rows']}
        old_native, final_native = {r['name']: r for r in old['rows']}, {r['name']: r for r in final['rows']}
        density_rows[family] = [{'name': r['name'],
            'command': difference(prior_rows[r['name']], r, ['modelMs', 'acceptMs', 'commandMs']),
            'enqueue': difference(prior_rows[r['name']]['enqueueCost'], r['enqueueCost'], PROFILE['COMMAND_STAGES']),
            'preparationSeconds': difference(old_native[r['name']], final_native[r['name']], ['preparationSeconds'])['preparationSeconds'],
            'medianRenderStageMs': difference(prior_rows[r['name']]['medianRenderStageMs'], r['medianRenderStageMs'], PROFILE['FRAME_STAGES']),
            'maxRenderStageMs': difference(prior_rows[r['name']]['maxRenderStageMs'], r['maxRenderStageMs'], PROFILE['FRAME_STAGES']),
            'resourceActivity': difference(prior_rows[r['name']], r, ['geometryMisses', 'meshSlotsCreated']),
            'worstRenderMs': {'baseline74': prior_rows[r['name']]['worstRenderFrame']['cost']['renderMs'],
                              'final75': r['worstRenderFrame']['cost']['renderMs']}}
            for r in final_summary['rows']]
    assert set(density_rows) == {'crate', 'stone', 'gate', 'tiles'} and not missing_candidate and not missing_final, 'All four final74/75 density comparisons are mandatory'
    result = {'status': 'DESCRIPTIVE_GAMEPLAY74_75_WITH_REMAINING_PERFORMANCE_GATES',
        'utc': datetime.now(timezone.utc).isoformat(), 'apk_sha256': final_sha, 'baseline_apk_sha256': old_sha,
        'sourceSchema': 1, 'cascade': rows, 'fluidity': phase_rows, 'density': density_rows,
        'unavailableDensityComparisons': {'candidateNotRecorded': missing_candidate, 'finalNotReady': missing_final},
        'baselineCheckpoint': 74, 'finalCheckpoint': 75,
        'scope': 'Same seeded model outcomes and instrument schema; final checkpoint74/75 builds and separate processes. '
                 'Absolute differences are descriptive. No performance pass threshold, significance test or causal speedup claim.',
        'limits': [
            'Process/OS/driver/cache scheduling differs across runs; first-use timers and preparation can trade work across readiness/command boundaries.',
            'All detailed diagnostic per-draw timers add overhead. Separate stage maxima need not occur on the same frame.',
            'Native CPU Render completion and StepStarted dispatch do not establish touch/display latency.',
            'The historical73 183ms maximum lacks corrected spans; these measurements do not retrospectively identify its exact cause.',
            'Both checkpoints have separate complete regressions; this table is descriptive and cannot certify every rendered frame.',
            'Atlas lookup, topology reuse, model and continuation refinements are combined across builds. Only separately controlled native tests attribute their narrow measured operations.'
        ],
        'artifactSHA256': dict(sorted(bindings.items())), 'analyzerSHA256': sha(Path(__file__)),
        'profilingValidatorSHA256': sha(Path(__file__).with_name('validate_gameplay74_profile.py'))}
    effect = read(out, 'Native/EffectBatchChecks.json')
    lookup = read(out, 'Native/FrameLookup.json')
    model = read(out, 'Native/ModelCommands.json')
    playback = read(out, 'Native/PlaybackConstruction.json')
    assert effect['status'] == 'PASS_NATIVE_EFFECT_BATCH' and effect['optimizedBaselineDifferingPixels'] == effect['optimizedBaselineMaxChannelDelta'] == 0
    assert lookup['status'] == 'PASS_NATIVE_FRAME_LOOKUP75' and model['status'] == 'PASS_NATIVE_MODEL_COMMANDS75'
    assert playback['status'] == 'PASS_NATIVE_PLAYBACK_CONSTRUCTION75'
    result['nativeMatchedControls'] = {
        'effectConstruction': effect['constructionRows'], 'frameLookup': lookup['timings'],
        'modelCommandPairs': model['repeated'], 'isolatedSnapshotPairs': model['snapshotRepeated'],
        'playbackConstruction': playback['timings'],
        'allocationCounter': model['allocationCounter'], 'allocationCounterUsable': model['allocationCounterUsable'],
        'scope': 'Native warmed matched operations are narrower than the separate-build Android comparisons. '
                 'Model stages are inclusive; heap deltas with GC disabled are labelled separately from thread allocation counters. '
                 'No required causal whole-game speedup or sustained frame-rate threshold.'}
    result['artifactSHA256'] = dict(sorted(bindings.items()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.out.resolve()
    result = build(out)
    (out / 'Profile_Comparison74_75.json').write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print(json.dumps({'status': result['status'], 'apk_sha256': result['apk_sha256'],
                      'cascadeRows': len(result['cascade']), 'densityFamilies': list(result['density'])}))


if __name__ == '__main__':
    main()
