"""Summarize source-bound checkpoint74 timings after an actual visual review.

This tool never starts Unity/ADB, measures displayed pixels, or grants an FPS
approval. It requires fresh final-APK visual bounds; no native prediction is
substituted for a recorded observation.
"""
import argparse
import hashlib
import json
import math
import runpy
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / 'Verification/Evidence/Gameplay74'
DEFAULT_BASE = ROOT / 'Verification/Evidence/LocalCascade73'
PROFILE = runpy.run_path(str(Path(__file__).with_name('validate_gameplay74_profile.py')),
                        run_name='gameplay74_profile_contract_only')
FAMILIES = ['crate', 'stone', 'gate', 'tiles']
RENDER_STAGES = ['lookupMs', 'batchAddMs', 'batchUploadMs', 'spriteUpdateMs', 'bankEndMs']


def need(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, share=.95):
    need(bool(values), 'No samples for percentile')
    return sorted(values)[max(0, math.ceil(len(values) * share) - 1)]


def selected(row, keys):
    return {key: row[key] for key in keys}


def unique_rows(rows, key='name'):
    result = {row[key]: row for row in rows}
    need(len(result) == len(rows), 'Duplicate case names')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--baseline', type=Path, default=DEFAULT_BASE)
    args = parser.parse_args()
    out, base = args.out.resolve(), args.baseline.resolve()
    bound, external = {}, {}

    def path(name, folder=out):
        result = (folder / name).resolve()
        need(result.is_relative_to(folder), 'Unsafe evidence path: ' + name)
        need(not {'Discarded', 'BeforeOnset', 'BeforeCPURefinement'} & set(result.parts), 'Discarded/occluded evidence rejected')
        need(result.is_file(), 'Missing evidence: ' + str(result))
        return result

    def read(name, folder=out):
        source = path(name, folder)
        if folder == out:
            bound[name] = sha(source)
        else:
            external[source.relative_to(ROOT).as_posix()] = sha(source)
        value = json.loads(source.read_text('utf-8-sig'))
        need(not any(value.get(k) for k in ['errors', 'failures', 'error']), name + ' has failures')
        return value

    artifact, old_artifact = read('APK_Artifact.json'), read('APK_Artifact.json', base)
    digest = artifact['sha256']
    baseline = read('Baseline_73.json')
    need(digest != old_artifact['sha256'] == baseline['apk_sha256'], 'Final APK is not a distinct checkpoint74 artifact')
    need(sha(path('Summary.json', base)) == baseline['summary_sha256'], 'Preserved73 summary changed')
    need(sha(path('Source_SHA256.json', base)) == baseline['source_manifest_sha256'], 'Preserved73 source manifest changed')
    visual, old_visual = read('Timing_Visual_Notes.json'), read('Timing_Visual_Notes.json', base)
    need(visual['status'] == 'REVIEWED_LOCAL_CONTINUATION74_WITH_REMAINING_GATES'
         and visual['apk_sha256'] == digest, 'Fresh final74 visual timing review missing/wrong APK')
    need(visual.get('remainingGates') and visual.get('artifactSHA256'), 'Visual review lacks limitations/bindings')
    for name, expected in visual['artifactSHA256'].items():
        need(sha(path(name)) == expected, 'Visual evidence changed: ' + name)
        bound[name] = expected
    for name, expected in visual.get('externalEvidenceSHA256', {}).items():
        need(sha(path(name, ROOT)) == expected, 'External visual evidence changed: ' + name)
        external[name] = expected
    local_match = visual['localMatch']
    old_gap = old_visual['localMatch']['contactToReactionBoundMs']
    need(local_match['case'] == 'L4_0_30'
         and local_match['baselineContactToReactionBoundMs'] == old_gap == [299.456, 367.133],
         'Visible control is not the final73 seeded L4 recording')
    gap = local_match['contactToReactionBoundMs']
    need(len(gap) == 2 and 0 <= gap[0] <= gap[1], 'Invalid measured visible interval')
    need(gap[1] < old_gap[0], 'Observed improvement is not resolved beyond sampling uncertainty')
    contact, reaction = local_match['contactBracketPts'], local_match['firstVisibleReactionBracketPts']
    need(len(contact) == len(reaction) == 2 and contact[0] < contact[1]
         and reaction[0] < reaction[1] and contact[0] <= reaction[0], 'Invalid observed PTS brackets')
    calculated_gap = [max(0, 1000 * (reaction[0] - contact[1])), 1000 * (reaction[1] - contact[0])]
    need(all(abs(a - b) < .002 for a, b in zip(gap, calculated_gap)), 'Observed bound is not derived from PTS endpoints')
    video_name = 'Android/Cascade/visual/HR_NaturalCascade.mp4'
    index_name = 'TimingVisual/PTS_Index.json'
    need({video_name, index_name} <= visual['artifactSHA256'].keys(), 'Original video/PTS index not bound by visual review')
    pts_index = read(index_name)
    need(pts_index['sha256'] == sha(path(video_name)), 'PTS index does not describe final video')
    for endpoint in contact + reaction:
        frame = next((f for f in pts_index['frames'] if abs(f['pts'] - endpoint) < .000001), None)
        need(frame is not None and sha(path(frame['file'], ROOT)) == frame['sha256'],
             'Endpoint does not bind an original decoded frame')
    swap = visual['acceptedSwap']
    onset, completion = swap['onsetBracketPts'], swap['completionBracketPts']
    need(len(onset) == len(completion) == 2 and onset[0] < onset[1] <= completion[0] < completion[1],
         'Invalid accepted-swap onset/completion brackets')
    swap_bounds = [1000 * (completion[0] - onset[1]), 1000 * (completion[1] - onset[0])]
    need(len(swap['visibleDurationBoundMs']) == 2
         and all(abs(a - b) < .002 for a, b in zip(swap['visibleDurationBoundMs'], swap_bounds)),
         'Swap duration must account for uncertainty at both endpoints')
    need(abs(swap['observedFirstMovingToFirstCompleteSampleIntervalMs']
             - 1000 * (completion[1] - onset[1])) < .002, 'Swap observed sample interval mislabeled')
    for endpoint in onset + completion:
        frame = next((f for f in pts_index['frames'] if abs(f['pts'] - endpoint) < .000001), None)
        need(frame is not None and sha(path(frame['file'], ROOT)) == frame['sha256'],
             'Swap endpoint does not bind an original decoded frame')
    baseline_video = 'Verification/Evidence/LocalCascade73/Android/Cascade/visual/HR_NaturalCascade.mp4'
    need(baseline_video in visual.get('externalEvidenceSHA256', {}), 'Same-fixture original73 video not bound')

    def installation(name):
        report = read(name)
        need(report['serial'] == 'emulator-5556'
             and report.get('apk_sha256', report.get('sha256')) == digest, 'Wrong APK/instance: ' + name)
        if 'installed_apk_sha256' in report:
            need(report['installed_apk_sha256'] == digest, 'Installed identity differs: ' + name)
        return report

    fluidity, old_fluidity = read('Android/Fluidity/Measurement.json'), read('Android/Fluidity/Measurement.json', base)
    installation('Android/Fluidity/Installation.json')
    need(fluidity['status'] == 'RECORDED_NATIVE_FLUIDITY' and fluidity['isolatedProfile']
         and fluidity['launchCleared'] and len(fluidity['phases']) == 8, 'Fluidity capture incomplete/occluded')
    old_phases, phases = unique_rows(old_fluidity['phases']), []
    for index, row in enumerate(fluidity['phases']):
        frames = [f for f in fluidity['frameSamples'] if f['phase'] == index]
        need(bool(frames) and row['name'] in old_phases, 'Fluidity frame/case mismatch')
        phases.append(selected(row, ['name', 'frames', 'p95Ms', 'worstMs', 'over33ms', 'over50ms',
            'modelMs', 'acceptMs', 'commandMs', 'firstPresentationMs', 'settleSeconds',
            'preparationSeconds', 'synchronousTextureLoads', 'spriteCreates', 'gen0Collections']) | {
            'measuredFrameSamples': len(frames),
            'worstUpdateMs': max(f['updateMs'] for f in frames),
            'worstRenderMs': max(f['renderMs'] for f in frames),
            'baseline73': selected(old_phases[row['name']], ['p95Ms', 'worstMs', 'modelMs', 'acceptMs', 'commandMs']),
            'comparisonScope': 'Separate emulator runs with changed diagnostic instrumentation; descriptive only. '
                               'firstPresentationMs is StepStarted dispatch, not first displayed pixels.'})

    native = read('Native/LocalContinuation.json')
    need(native['status'] == 'PASS_NATIVE_LOCAL_CONTINUATION74' and native['modelCases'] == 350
         and native['rawTurnParity'] and native['finalSnapshotParity'], 'Native continuation parity incomplete')
    renderers = native['rendererRows']
    need(any(r['caseName'] == 'L4_confirmation' for r in renderers), 'Actual L4 confirmation missing')
    need(all(r['poseSamples'] > 0 and r['routeSamples'] > 0 and r['collisionSamples'] > 0
             and r['maxBoundaryPositionJump'] < .001 and r['maxBoundaryScaleJump'] < .001
             and r['minimumColumnClearance'] >= .90 for r in renderers), 'Native body/column continuity failed')
    l4_native = next(r for r in renderers if r['caseName'] == 'L4_confirmation')

    cascade, transitions, profiles, frame_contexts = [], [], {}, []
    for variant, count in [('measure', 6), ('visual', 1)]:
        folder = 'Android/Cascade/' + variant + '/'
        installation(folder + 'Installation.json')
        report, old = read(folder + 'Report.json'), read(folder + 'Report.json', base)
        need(report['status'] == 'PASS_CASCADE_PLAYBACK' and len(report['rows']) == count
             and report.get('repeats') == 1, 'Default cascade capture incomplete')
        old_rows = unique_rows(old['rows'])
        hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
        profiles[variant] = PROFILE['validate'](report, variant, hashes)
        for index, row in enumerate(report['rows']):
            prior = old_rows[row['baseCase']]
            cascade.append(selected(row, ['name', 'targetFps', 'matches', 'wallSeconds', 'scheduledSeconds',
                                           'lateFrames', 'maxIntervalMs']) | {
                'variant': variant,
                'baseline73': selected(prior, ['wallSeconds', 'scheduledSeconds', 'lateFrames', 'maxIntervalMs']),
                'comparisonScope': 'The corrected74 probe removes an extra diagnostic playback Build and records '
                                   'previously omitted model/search work. Legacy playback totals are not end-to-end touch latency.'})
            frames = [f for f in report['frameSamples'] if f['row'] == index]
            worst = max(frames, key=lambda f: f['intervalMs'])
            frame_contexts.append({'case': row['name'], 'variant': variant,
                'commandSpans': row['commandSpans'], 'enqueueCost': row['enqueueCost'],
                'commandFrame': row['commandFrame'],
                'commandFrameSamples': [f for f in frames if f['frame'] == row['commandFrame']],
                'largestIntervalNeighborFrames': [f for f in frames if abs(f['frame'] - worst['frame']) <= 1],
                'interpretation': 'Tags preserve Update/Render phase versus later coroutine state. '
                                  'Nearby timings constrain provenance but do not isolate OS/GPU/GC causality.'})
            if row['baseCase'].startswith('L4_'):
                powers = [p for p in row['phases'] if p['kind'] == 'powerFall']
                for number, (previous, following) in enumerate(zip(powers, powers[1:])):
                    offset = 1000 * (following['clock'] - previous['clock'] - previous['lastContact'])
                    if number == 0:
                        need(abs(previous['duration'] - l4_native['handoff']) < .0001,
                             'Device did not dispatch the verified continuation schedule')
                    transitions.append({'case': row['name'], 'variant': variant, 'transitionIndex': number,
                        'nextDispatchClockMinusPreviousGlobalContactMs': offset,
                        'nextDispatchWallMinusPreviousGlobalContactMs':
                            1000 * (following['wall'] - previous['wall'] - previous['lastContact']),
                        'meaning': 'Early dispatch is intentional continuation of unfinished routes. '
                                   'Step selection is distinct from native body contact or visible reaction.'})

    density, density_profiles = {}, {}
    for family in FAMILIES:
        folder = 'Android/Density/candidate_review-' + family + '/'
        installation(folder + 'Installation.json')
        report, old = read(folder + 'Report.json'), read(folder + 'Report.json', base)
        need(report['status'] == 'PASS_OBSTACLE_DENSITY_PLAYBACK' and report['family'] == family
             and len(report['rows']) == 10, 'Density sweep incomplete: ' + family)
        old_rows, rows = unique_rows(old['rows']), []
        density_profiles[family] = PROFILE['validate_density'](report, family,
            {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']})
        for index, row in enumerate(report['rows']):
            prior = old_rows[row['name']]
            need((row['turnHash'], row['finalHash']) == (prior['turnHash'], prior['finalHash']), 'Density model changed')
            frames = [f for f in report['frames'] if f['phase'] == index]
            need(bool(frames), 'No density frames: ' + row['name'])
            burst = [f for f in frames if f['draws'] >= row['peakDraws'] * .5]
            old_index = next(i for i, r in enumerate(old['rows']) if r['name'] == row['name'])
            old_burst = [f for f in old['frames'] if f['phase'] == old_index and f['draws'] >= prior['peakDraws'] * .5]
            need(report.get('profilingSchemaVersion') == 1 and all('cost' in f for f in frames),
                 'Density lacks tagged native render profiling: ' + row['name'])
            need(all(f['frame'] == f['cost']['frame'] and f['cost']['updateStartedWall'] > 0
                     and f['cost']['updateStartedWall'] <= f['cost']['renderStartedWall']
                     <= f['cost']['renderFinishedWall'] <= f['cost']['updateFinishedWall'] <= f['absoluteWall']
                     for f in frames), 'Mixed/missing density native wall tags: ' + row['name'])
            peak_render = max(frames, key=lambda f: f['cost']['renderMs'])
            costs = [f['cost'] for f in burst]
            stage_summary = {
                'medianMs': {k: statistics.median(c[k] for c in costs) for k in RENDER_STAGES},
                'maxMs': {k: max(c[k] for c in costs) for k in RENDER_STAGES},
                'geometryMisses': sum(c['geometryMisses'] for c in costs),
                'meshSlotsCreated': sum(c['meshSlotsCreated'] for c in costs),
                'sourceSamples': len(costs),
                'scope': 'Native diagnostic elapsed stages within high-draw frames, including timer overhead. '
                         'Separate per-stage maxima need not occur in the same frame; this is not GPU time.'}
            rows.append(selected(row, ['name', 'hits', 'cleared', 'peakDraws', 'peakMeshes', 'modelMs',
                                        'acceptMs', 'commandMs', 'renderersCreated', 'crateSpritesCreated']) | {
                'measuredFrames': len(frames), 'burstFrames': len(burst),
                'burstP95IntervalMs': percentile([f['intervalMs'] for f in burst]),
                'burstP95RenderMs': percentile([f['renderMs'] for f in burst]),
                'burstWorstRenderMs': max(f['renderMs'] for f in burst),
                'taggedRenderStages': stage_summary,
                'commandProvenance': selected(row, ['commandFrame', 'commandStartedWall', 'commandFinishedWall', 'enqueueCost']),
                'commandFrameSamples': [f for f in frames if f['frame'] == row['commandFrame']],
                'largestRenderNeighborFrames': [f for f in frames if abs(f['frame'] - peak_render['frame']) <= 1],
                'baseline73': selected(prior, ['modelMs', 'acceptMs', 'commandMs', 'peakDraws']) | {
                    'burstFrames': len(old_burst),
                    'burstP95IntervalMs': percentile([f['intervalMs'] for f in old_burst]),
                    'burstP95RenderMs': percentile([f['renderMs'] for f in old_burst]),
                    'burstWorstRenderMs': max(f['renderMs'] for f in old_burst)}})
        density[family] = rows

    repeat_summary = read('RepeatProfiling/Summary.json')
    need(repeat_summary['status'] == 'VALIDATED_THREE_PROCESS_REPEATS_WITH_REMAINING_PERFORMANCE_GATES'
         and repeat_summary['apk_sha256'] == digest and repeat_summary['processes'] == 3
         and repeat_summary['rows'] == 36, 'Three-process repeat evidence incomplete')
    repeated_profiles = []
    for item in repeat_summary['profiles']:
        process = item['process']
        need(process in [1, 2, 3], 'Unexpected repeat process')
        folder = 'RepeatProfiling/Process' + str(process).zfill(2) + '/measure/'
        installation(folder + 'Installation.json')
        report = read(folder + 'Report.json')
        old = read('Android/Cascade/measure/Report.json', base)
        hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
        profile = PROFILE['validate'](report, 'measure', hashes)
        need(report['repeats'] == 2 and len(profile['rows']) == 12 and profile == item['profile'],
             'Repeat summary does not match actual source-bound rows')
        repeated_profiles.append({'process': process, 'profile': profile})
    need({item['process'] for item in repeated_profiles} == {1, 2, 3}, 'Repeat processes duplicated/missing')
    for name, expected in repeat_summary['artifactSHA256'].items():
        need(sha(path(name)) == expected, 'Repeated raw artifact changed: ' + name)
        bound[name] = expected
    repeated_rows = [r for item in repeated_profiles for r in item['profile']['rows']]
    repeated_control = {
        'status': repeat_summary['status'], 'processes': 3, 'rows': 36, 'profiles': repeated_profiles,
        'firstL4_60CommandMs': [next(r['commandMs'] for r in item['profile']['rows']
                                    if r['baseCase'] == 'L4_0_60' and r['repeatIndex'] == 0)
                               for item in repeated_profiles],
        'largestCommandMs': max(r['commandMs'] for r in repeated_rows),
        'largestLaterL4CommandMs': max(r['commandMs'] for r in repeated_rows
                                      if r['baseCase'].startswith('L4_') and r['repeatIndex'] > 0),
        'largestIntervalMs': max(r['maxIntervalMs'] for r in repeated_rows),
        'scope': 'Three separate process launches, two passes each; every fixture reloads its bank. '
                 'Only the initial L4_0_60 of each process is process-first. This is not a cold-device '
                 'or retained-sprite-cache control, and sample differences are not causal significance.'}
    comparison = read('Candidate_Final_Profile_Comparison.json')
    need(comparison['status'] == 'DESCRIPTIVE_CANDIDATE_FINAL74_PROFILING_WITH_CAUSALITY_LIMITS'
         and comparison['apk_sha256'] == digest and comparison['candidate_apk_sha256'] != digest,
         'Candidate/final descriptive comparison is stale')
    need(len(comparison['cascade']) == 6 and len(comparison['fluidity']) == 8
         and comparison.get('density', {}).get('stone') and comparison.get('artifactSHA256'),
         'Candidate comparison omits matched source reports')
    prepared_parity = read('Native_Render_Parity.json')
    need(prepared_parity['status'] == 'VERIFIED_NATIVE_PREPARED_CAPTURE_BYTES_IDENTICAL',
         'Prepared-render capture parity missing')
    for name, expected in prepared_parity['artifactSHA256'].items():
        need(sha(path(name)) == expected, 'Native prepared parity artifact changed')
        bound[name] = expected
    effects, warmup = read('Native/EffectBatchChecks.json'), read('Native/WarmupChecks.json')
    need(effects['preparedDifferingPixels'] == effects['preparedMaxChannelDelta'] == 0
         and effects['interleavedCommonRetained'] == 352 and effects['interleavedSpriteEvictions'] == 0
         and warmup['largestCommonRetained'] == 352, 'Preparation/retention proof incomplete')

    result = {
        'status': 'ANALYZED_LOCAL_CONTINUATION74_WITH_REMAINING_GATES',
        'utc': datetime.now(timezone.utc).isoformat(), 'apk_sha256': digest,
        'baseline_apk_sha256': old_artifact['sha256'],
        'scope': 'Final QA evidence: eight fluidity phases, six corrected unrecorded cascade fixtures, '
                 'forty warmed density turns and a separately recorded original-PTS visual fixture. '
                 'No whole-game, cold-process, physical-device or exact competitor parity certification.',
        'counts': {'fluidity': len(phases), 'cascadeMeasure': 6, 'cascadeVisual': 1,
                   'density': sum(len(v) for v in density.values()), 'nativeModelCases': native['modelCases']},
        'nativeLocalHandoff': renderers, 'localMatch': local_match, 'acceptedSwap': swap,
        'visibleImprovementBoundMs': [old_gap[0] - gap[1], old_gap[1] - gap[0]],
        'fluidity': phases, 'cascade': cascade, 'cascadeTransitions': transitions,
        'correctedProfiling': profiles, 'densityProfiling': density_profiles,
        'frameProvenance': frame_contexts, 'density': density,
        'repeatedFinalControl': repeated_control,
        'candidateFinalComparison': comparison,
        'nativePreparedRendererParity': prepared_parity,
        'nativePreparationRetention': selected(effects, ['checks', 'interleavedWarmupYields',
            'interleavedCommonRetained', 'interleavedSpriteEvictions',
            'historicalCapCommonRetained', 'historicalCapSpriteEvictions']),
        'interpretation': [
            'Native continuation predicts a shorter phase wait, but only independently inspected original-PTS '
            'contact/break brackets establish the visible improvement and residual wait.',
            'Composite ownership keeps earlier routes/landings alive until their retimed following motion; '
            'native continuity and column-clearance samples are distinct from recorded visual inspection.',
            'The old73 183 ms interval lacks per-frame spans. Removing duplicate probe work and adding later '
            'instrumentation does not retrospectively prove its exact cause.',
            'Detailed per-draw timers/counters add overhead. Cross-run73/74 differences include code, '
            'diagnostic, process/cache, emulator translation and scheduling changes; they are not isolated speedup proofs.',
            'Native Render completion, phase dispatch, video PTS and actual displayed-pixel timing are separate domains.',
            'Density cases are warmed. Zero obstacle-family sprite or renderer growth is not zero allocation, '
            'zero other sprite creation, or cold-process proof.',
            'Archived Match Villains clips use different boards/effect endpoints and sampling/version limits. '
            'No new reference recording or exact mechanics/timing parity is established.'
        ],
        'remainingGates': visual['remainingGates'] + [
            'Synchronous command/model/resource work remains a separate responsiveness gate; '
            'bounded native CPU spans must not be relabelled as touch-to-photon measurements.',
            'Physical Android GPU/memory, cold/warm repeated matched controls, long sessions and '
            'all-feature sustained frame-rate certification remain open.'
        ],
        'artifactSHA256': dict(sorted(bound.items())),
        'externalEvidenceSHA256': dict(sorted(external.items())),
        'analyzerSHA256': sha(Path(__file__)),
        'profilingValidatorSHA256': sha(Path(__file__).with_name('validate_gameplay74_profile.py')),
    }
    (out / 'Timing_Analysis.json').write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print(json.dumps({'status': result['status'], 'apk_sha256': digest, 'counts': result['counts'],
                      'visibleImprovementBoundMs': result['visibleImprovementBoundMs']}))


if __name__ == '__main__':
    main()
