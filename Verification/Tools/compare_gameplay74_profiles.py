"""Describe archived candidate/final74 native spans, without a speedup verdict.

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
DEFAULT_OUT = ROOT / 'Verification/Evidence/Gameplay74'
BASE = ROOT / 'Verification/Evidence/LocalCascade73'
PROFILE = runpy.run_path(str(Path(__file__).with_name('validate_gameplay74_profile.py')),
                        run_name='candidate_final_profile_contract_only')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def difference(old, new, fields):
    return {key: {'candidate': old[key], 'final': new[key], 'finalMinusCandidate': new[key] - old[key]}
            for key in fields}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--require-density', action='store_true')
    parser.add_argument('--repeat-profile', type=Path,
                        help='Optional repeated final runner output root (contains measure/).')
    args = parser.parse_args()
    out = args.out.resolve()
    candidate = (args.candidate or out / 'BeforeCPURefinement').resolve()
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
    for installation, digest in [(old_fluid_install, old_sha), (final_fluid_install, final_sha)]:
        assert installation['serial'] == 'emulator-5556'
        assert installation.get('apk_sha256', installation.get('sha256')) == digest
    old_phases = {r['name']: r for r in old_fluid['phases']}
    phase_rows = []
    for row in final_fluid['phases']:
        prior = old_phases[row['name']]
        keys = ['modelMs', 'acceptMs', 'commandMs', 'firstPresentationMs', 'preparationSeconds',
                'settleSeconds', 'p95Ms', 'worstMs', 'spriteCreates', 'synchronousTextureLoads',
                'gen0Collections', 'poolAtReady', 'poolAtEnd', 'peakCachedSprites', 'bankSpriteHighWater']
        phase_rows.append({'name': row['name'], 'metrics': difference(prior, row, keys),
            'additionalFirstUseFields': {'candidate': {k: v for k, v in prior.items() if 'warm' in k.lower()},
                                         'final': {k: v for k, v in row.items() if 'warm' in k.lower()}},
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
            'worstRenderMs': {'candidate': prior_rows[r['name']]['worstRenderFrame']['cost']['renderMs'],
                              'final': r['worstRenderFrame']['cost']['renderMs']}}
            for r in final_summary['rows']]
    assert not args.require_density or density_rows and not missing_final, 'Available-candidate density comparison missing'
    repeated = None
    repeat_folder = (args.repeat_profile or out / 'RepeatProfile').resolve()
    if args.repeat_profile or (repeat_folder / 'measure/Report.json').is_file():
        repeat_raw = read(repeat_folder, 'measure/Report.json')
        repeat_install = read(repeat_folder, 'measure/Installation.json')
        assert repeat_install['apk_sha256'] == repeat_install['installed_apk_sha256'] == final_sha
        assert repeat_install['serial'] == 'emulator-5556' and repeat_install['data_unchanged']
        assert repeat_raw['repeats'] >= 2
        baseline = read(BASE, 'Android/Cascade/measure/Report.json')
        hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in baseline['rows']}
        repeat_summary = PROFILE['validate'](repeat_raw, 'measure', hashes)
        by_case = {}
        for r in repeat_summary['rows']:
            by_case.setdefault(r['baseCase'], []).append(r)
        repeated = {'status': 'DESCRIPTIVE_REPEATED_FINAL74_PROCESS_CONTROL',
            'repeats': repeat_raw['repeats'], 'rows': repeat_summary['rows'],
            'withinProcessPasses': [{'baseCase': name,
                'firstVersusLater': [{'laterRepeatIndex': later['repeatIndex'],
                    'command': difference(rows[0], later, ['modelMs', 'acceptMs', 'commandMs', 'firstCommandRenderMs']),
                    'enqueue': difference(rows[0]['enqueueCost'], later['enqueueCost'], PROFILE['COMMAND_STAGES'])}
                    for later in rows[1:]]} for name, rows in by_case.items()],
            'scope': 'Fresh banks reload for every row. Only initial L4_0_60 is process-first; '
                     'other pass-zero fixtures already reuse process/code/driver paths. '
                     'This is not a retained sprite-cache, cold-device, randomized A/B or statistically powered control.'}
    result = {'status': 'DESCRIPTIVE_CANDIDATE_FINAL74_PROFILING_WITH_CAUSALITY_LIMITS',
        'utc': datetime.now(timezone.utc).isoformat(), 'apk_sha256': final_sha, 'candidate_apk_sha256': old_sha,
        'sourceSchema': 1, 'cascade': rows, 'fluidity': phase_rows, 'density': density_rows,
        'unavailableDensityComparisons': {'candidateNotRecorded': missing_candidate, 'finalNotReady': missing_final},
        'repeatedFinalControl': repeated,
        'scope': 'Same seeded model outcomes and instrument schema; distinct candidate/final builds and processes. '
                 'Absolute differences are descriptive. No performance pass threshold, significance test or causal speedup claim.',
        'limits': [
            'Process/OS/driver/cache scheduling differs across runs; first-use timers and preparation can trade work across readiness/command boundaries.',
            'All detailed diagnostic per-draw timers add overhead. Separate stage maxima need not occur on the same frame.',
            'Native CPU Render completion and StepStarted dispatch do not establish touch/display latency.',
            'The historical73 183ms maximum lacks corrected spans; these measurements do not retrospectively identify its exact cause.',
            'This partial candidate never completed all nine stages; final completeness is established by the separate final collector.',
            'Warmup and snapshot refinements are combined here. Any per-feature causal comparison needs an equally instrumented matched control.'
        ],
        'artifactSHA256': dict(sorted(bindings.items())), 'analyzerSHA256': sha(Path(__file__)),
        'profilingValidatorSHA256': sha(Path(__file__).with_name('validate_gameplay74_profile.py'))}
    (out / 'Candidate_Final_Profile_Comparison.json').write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print(json.dumps({'status': result['status'], 'apk_sha256': final_sha,
                      'cascadeRows': len(rows), 'densityFamilies': list(density_rows)}))


if __name__ == '__main__':
    main()
