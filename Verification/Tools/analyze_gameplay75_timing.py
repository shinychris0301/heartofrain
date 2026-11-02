"""Analyze final75 source-bound timing and manually reviewed paired footage.

This read-only analyzer never executes Unity/ADB or infers visual endpoints.
Native schedule, CPU spans, dispatch callbacks and video PTS stay distinct.
"""
import argparse
import hashlib
import json
import math
import runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_FILE = Path(__file__).with_name('validate_gameplay74_profile.py')
PROFILE = runpy.run_path(str(PROFILE_FILE), run_name='gameplay75_profile_contract_only')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(ok, message):
    if not ok:
        raise AssertionError(message)


def select(row, keys):
    return {k: row[k] for k in keys}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'Verification/Evidence/Gameplay75')
    parser.add_argument('--baseline', type=Path, default=ROOT / 'Verification/Evidence/Gameplay74')
    args = parser.parse_args()
    out, base = args.out.resolve(), args.baseline.resolve()
    bound, external = {}, {}

    def path(name, folder=out):
        p = (folder / name).resolve()
        need(p.is_relative_to(folder) and p.is_file(), 'Missing/unsafe evidence: ' + str(p))
        need(not any(x == 'Discarded' or x.startswith('Before') for x in p.relative_to(folder).parts[:-1]),
             'Superseded evidence is not final proof: ' + name)
        return p

    def read(name, folder=out):
        p = path(name, folder)
        if folder == out:
            bound[name] = sha(p)
        else:
            external[p.relative_to(ROOT).as_posix()] = sha(p)
        data = json.loads(p.read_text('utf-8-sig'))
        need(not any(data.get(k) for k in ['errors', 'error', 'failures']), 'Evidence has failures: ' + name)
        return data

    artifact, prior_artifact = read('APK_Artifact.json'), read('APK_Artifact.json', base)
    digest = artifact['sha256']
    need(digest != prior_artifact['sha256'], 'Final75 APK is still baseline74')
    archived = read('Baseline_74.json')
    need(archived['apk_sha256'] == prior_artifact['sha256'], 'Wrong baseline identity')
    for name, expected in archived['artifacts'].items():
        p = (ROOT / name).resolve()
        need(p.is_relative_to(ROOT) and sha(p) == expected, 'Preserved74 artifact changed: ' + name)
        external[name] = expected
    visual = read('Timing_Visual_Notes.json')
    need(visual['status'] == 'REVIEWED_LOCAL_CONTINUATION75_WITH_REMAINING_GATES'
         and visual['apk_sha256'] == digest and visual.get('remainingGates'), 'Final75 visual timing review missing')
    for name, expected in visual['artifactSHA256'].items():
        need(sha(path(name)) == expected, 'Visual artifact changed: ' + name)
        bound[name] = expected
    for name, expected in visual.get('externalEvidenceSHA256', {}).items():
        need(sha(path(name, ROOT)) == expected, 'External visual artifact changed: ' + name)
        external[name] = expected

    def installation(folder):
        install = read(folder + 'Installation.json')
        need(install['serial'] == 'emulator-5556'
             and install.get('apk_sha256', install.get('sha256')) == digest, 'Wrong APK/instance: ' + folder)
        if 'installed_apk_sha256' in install:
            need(install['installed_apk_sha256'] == digest, 'Installed APK differs: ' + folder)
        return install

    def endpoints(observation, index_name, video_name):
        need({index_name, video_name} <= visual['artifactSHA256'].keys(), 'Unbound original video/PTS index')
        index = read(index_name)
        need(index['apk_sha256'] == digest and index['sha256'] == sha(path(video_name)), 'PTS source differs')
        contact, reaction = observation['contactBracketPts'], observation['firstVisibleReactionBracketPts']
        need(len(contact) == len(reaction) == 2 and contact[0] < contact[1]
             and reaction[0] < reaction[1] and reaction[0] >= contact[0], 'Invalid observed brackets')
        calculated = [round(max(0, reaction[0] - contact[1]) * 1000, 3), round((reaction[1] - contact[0]) * 1000, 3)]
        need(observation['contactToReactionBoundMs'] == calculated, 'Visible bounds do not account for both endpoints')
        for t in contact + reaction:
            frame = next((f for f in index['frames'] if abs(f['pts'] - t) < 1e-6), None)
            need(frame and sha(path(frame['file'], ROOT)) == frame['sha256'], 'Endpoint PNG is not original/hash-bound')
        return index

    old_visual = read('Timing_Visual_Notes.json', base)
    local_match = visual['localMatch']
    need(local_match['case'] == 'L4_0_30'
         and local_match['baselineContactToReactionBoundMs'] == old_visual['localMatch']['contactToReactionBoundMs'],
         'L4 does not bind actual final74 same-fixture observations')
    default_index = endpoints(local_match, 'TimingVisual/PTS_Index.json', 'Android/Cascade/visual/HR_NaturalCascade.mp4')
    # L4 scheduler is unchanged. A different sampled bound is not forced to be an improvement.
    swap = visual['acceptedSwap']
    onset, complete = swap['onsetBracketPts'], swap['completionBracketPts']
    need(onset == [swap['lastStationaryPts'], swap['firstDisplacedPts']]
         and complete == [swap['intermediateProgressPts'][-1], swap['firstOppositeCellCentersPts']]
         and onset[0] < onset[1] < complete[0] < complete[1], 'Invalid accepted-swap brackets')
    need(swap['visibleDurationBoundMs'] == [round((complete[0] - onset[1]) * 1000, 3),
                                          round((complete[1] - onset[0]) * 1000, 3)], 'Swap uncertainty is incomplete')
    need(swap['observedFirstMovingToFirstCompleteSampleIntervalMs'] == round((complete[1] - onset[1]) * 1000, 3),
         'Observed sample interval is not a duration bound')
    for t in onset + complete:
        frame = next((f for f in default_index['frames'] if abs(f['pts'] - t) < 1e-6), None)
        need(frame and sha(path(frame['file'], ROOT)) == frame['sha256'], 'Swap endpoint is not original/hash-bound')

    native = read('Native/LocalContinuation.json')
    need(native['status'] == 'PASS_NATIVE_LOCAL_CONTINUATION75' and native['modelCases'] == 350
         and native['rawTurnParity'] and native['finalSnapshotParity'] and native['checkpoint74Comparisons'] == 350,
         'Native corpus/control parity incomplete')
    native_rows = {r['name']: r for r in native['rows']}
    need(native['qualifyingTurns'] == 4 and native['newQualifyingTurns'] == 3 and native['guardCases'] >= 44,
         'Guarded expansion coverage differs')
    renderers = native['rendererRows']
    need(all(r['poseSamples'] > 0 and r['routeSamples'] > 0 and r['collisionSamples'] > 0
             and r['maxBoundaryPositionJump'] < .001 and r['maxBoundaryScaleJump'] < .001
             and r['minimumColumnClearance'] >= .90 for r in renderers), 'Native body continuity incomplete')
    extra_cases = visual['newContinuationCases']
    need(len(extra_cases) == 3 and {r['level'] for r in extra_cases} == {14, 31, 33}, 'Paired continuation review missing')
    extras, recorded_extra_rows, recorded_extra_samples = [], [], []
    for case in extra_cases:
        level = case['level']
        need(case['routeContinuityReviewed'] and case['landingIntoIdleReviewed'] and case['visualFinding'],
             'Route/idle visual inspection missing')
        native_row = native_rows['L' + str(level) + '_match']
        expected_hash = (native_row['sequentialTurnHash'], native_row['sequentialFinalHash'])
        pairs = {}
        for mode, control in [('control74', True), ('refined75', False)]:
            folder = 'ExtraContinuation/L' + str(level) + '/' + mode + '/visual/'
            need(case[mode + 'Folder'] == folder, 'Unexpected paired source folder')
            install, report = installation(folder), read(folder + 'Report.json')
            need(install['visual_level'] == report['visualLevel'] == level
                 and install['checkpoint74_continuation'] is control and report['checkpoint74Continuation'] is control
                 and not report['modelWorkEnabled'] and PROFILE['RUNNER']['validate_report'](report, 'visual', 1, True),
                 'Paired capture mode/provenance differs')
            row = report['rows'][0]
            need(row['name'] == row['baseCase'] == 'L' + str(level) + '_0_30'
                 and (row['turnHash'], row['finalHash']) == expected_hash, 'Paired model output differs')
            scheduled = native_row['checkpoint74Seconds' if control else 'refinedSeconds']
            need(abs(row['scheduledSeconds'] - scheduled) < .001, 'Paired native schedule differs')
            observation = case[mode]
            endpoints(observation, observation['ptsIndex'], folder + 'HR_NaturalCascade.mp4')
            pairs[mode] = select(row, ['scheduledSeconds', 'wallSeconds', 'modelMs', 'acceptMs', 'commandMs',
                                      'firstCommandRenderMs', 'lateFrames', 'maxIntervalMs'])
            recorded_extra_rows.append({'level': level, 'mode': mode, 'folder': folder,
                **select(row, ['commandFrame', 'modelMs', 'acceptMs', 'commandMs', 'legalSearchMs',
                    'firstCommandRenderMs', 'maxIntervalMs', 'lateFrames', 'enqueueCost'])})
            recorded_extra_samples.append({'level': level, 'mode': mode, 'folder': folder,
                                           'row': row, 'frames': report['frameSamples']})
        extras.append({'level': level, 'case': case, 'recordedCpuAndSchedule': pairs,
            'native': [r for r in renderers if r['caseName'] == 'L' + str(level) + '_match'],
            'scope': 'Same final APK/seeded outcome; opt-in preserved74 scheduling versus guarded75 continuation. '
                     'Recorded visual endpoints are distinct from CPU spans and native schedule savings.'})

    profiles, cascade = {}, []
    for variant, count in [('measure', 6), ('visual', 1)]:
        folder = 'Android/Cascade/' + variant + '/'
        installation(folder)
        report, old = read(folder + 'Report.json'), read(folder + 'Report.json', base)
        hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
        need(len(report['rows']) == count and report['repeats'] == 1 and not report['modelWorkEnabled']
             and not report['checkpoint74Continuation'], 'Default profiling scope changed')
        profiles[variant] = PROFILE['validate'](report, variant, hashes)
        for row in report['rows']:
            prior = next(r for r in old['rows'] if r['name'] == row['name'])
            cascade.append(select(row, ['name', 'targetFps', 'matches', 'scheduledSeconds', 'wallSeconds',
                'lateFrames', 'maxIntervalMs', 'modelMs', 'acceptMs', 'commandMs', 'firstCommandRenderMs']) | {
                'variant': variant, 'baseline74': select(prior, ['scheduledSeconds', 'wallSeconds', 'lateFrames', 'maxIntervalMs',
                    'modelMs', 'acceptMs', 'commandMs', 'firstCommandRenderMs'])})
    fluid, prior_fluid = read('Android/Fluidity/Measurement.json'), read('Android/Fluidity/Measurement.json', base)
    installation('Android/Fluidity/')
    need(fluid['status'] == 'RECORDED_NATIVE_FLUIDITY' and fluid['launchCleared'] and fluid['isolatedProfile']
         and len(fluid['phases']) == 8, 'Fluidity run incomplete/occluded')
    fluidity = [{'current': row, 'baseline74': next(r for r in prior_fluid['phases'] if r['name'] == row['name'])}
                for row in fluid['phases']]
    density = {}
    for family in ['crate', 'stone', 'gate', 'tiles']:
        folder = 'Android/Density/candidate_review-' + family + '/'
        installation(folder)
        report, old = read(folder + 'Report.json'), read(folder + 'Report.json', base)
        hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
        density[family] = PROFILE['validate_density'](report, family, hashes)
    repeats = read('RepeatProfiling/Summary.json')
    need(repeats['status'] == 'VALIDATED_THREE_PROCESS_REPEATS_WITH_REMAINING_PERFORMANCE_GATES'
         and repeats['apk_sha256'] == digest and repeats['processes'] == 3 and repeats['rows'] == 36,
         'Repeated process evidence incomplete')
    old = read('Android/Cascade/measure/Report.json', base)
    hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
    for entry in repeats['profiles']:
        folder = 'RepeatProfiling/Process' + str(entry['process']).zfill(2) + '/measure/'
        installation(folder)
        report = read(folder + 'Report.json')
        need(report['repeats'] == 2 and PROFILE['validate'](report, 'measure', hashes) == entry['profile'],
             'Repeated summary does not match actual rows')
    for name, expected in repeats['artifactSHA256'].items():
        need(sha(path(name)) == expected, 'Repeated artifact changed')
        bound[name] = expected
    comparison = read('Profile_Comparison74_75.json')
    need(comparison['status'] == 'DESCRIPTIVE_GAMEPLAY74_75_WITH_REMAINING_PERFORMANCE_GATES'
         and comparison['apk_sha256'] == digest, 'Direct74/75 descriptive comparison missing/stale')
    # Expensive model categorization remains outside ordinary profiling.
    installation('ExtraModelStages/measure/')
    model_diagnostic = read('ExtraModelStages/measure/Report.json')
    need(model_diagnostic['modelWorkEnabled'] and not model_diagnostic['checkpoint74Continuation'],
         'Model-stage diagnostic scope differs')
    PROFILE['validate'](model_diagnostic, 'measure', hashes)
    repeated_rows = [r for entry in repeats['profiles'] for r in entry['profile']['rows']]
    # Time.unscaledDeltaTime describes the preceding frame interval, whereas the
    # full cost tag belongs to this frame's actual Update/Render. Keep the prior
    # coroutine command tail and its spans visible rather than assigning it to
    # the first rendered swap pose.
    worst_capture = max(recorded_extra_samples,
                        key=lambda entry: max(f['intervalMs'] for f in entry['frames'] if f['timingWindow']))
    sample_index = max((i for i, f in enumerate(worst_capture['frames']) if f['timingWindow']),
                       key=lambda i: worst_capture['frames'][i]['intervalMs'])
    interval_frame = worst_capture['frames'][sample_index]
    command_tail = next(f for f in worst_capture['frames'] if f['commandFrame'])
    command_row = worst_capture['row']
    need(command_tail['frame'] == command_row['commandFrame']
         and interval_frame['intervalMs'] == command_row['maxIntervalMs'], 'Recorded worst interval provenance differs')
    recorded_extra_profile = {'rows': recorded_extra_rows, 'worstRecordedInterval': {
        'level': worst_capture['level'], 'mode': worst_capture['mode'], 'folder': worst_capture['folder'],
        'commandSpans': command_row['commandSpans'], 'enqueueCost': command_row['enqueueCost'],
        'intervalFrame': interval_frame, 'commandFrameTail': command_tail,
        'neighboringFrames': worst_capture['frames'][max(0, sample_index - 2):sample_index + 3],
        'interpretation': 'The largest recorded extra interval occurs at the first swap pose. Its preceding '
            'command frame reports an explicitly pre-command idle cost, followed by the legal-search/model/'
            'real-Accept/queue-inspection coroutine tail. The first actual swap Render is separately tagged '
            'at age zero. The interval overlaps synchronous command/probe elapsed work; it is not the CPU '
            'duration of that first swap Render or evidence of a later local-cascade barrier.',
        'limitations': 'Stopwatch and wall spans include main-thread descheduling, recording and observer '
            'overhead. Nested enqueue timings are parts of Accept and are not additive exclusive CPU '
            'percentages. Unchanged GC/resource counters narrow observed scope but do not prove a sole '
            'cause, rule out driver/OS work or establish touch-to-photon latency.'}}
    limits = visual['remainingGates'] + [
        'Diagnostics add per-draw/main-thread observer overhead; separate process/cache/host conditions prevent '
        'assigning descriptive74/75 changes to one optimization.',
        'Native Render completion, phase dispatch and video PTS are distinct clock domains; no touch-to-photon claim.',
        'The historical73 183ms aggregate has no recoverable exact cause from later instrumented samples.',
        'Physical Android GPU/memory, cold-device, long-soak, all-feature sustained frame rate and campaign balance remain open.']
    result = {
        'status': 'ANALYZED_LOCAL_CONTINUATION75_WITH_REMAINING_GATES',
        'utc': datetime.now(timezone.utc).isoformat(), 'apk_sha256': digest, 'baseline_apk_sha256': prior_artifact['sha256'],
        'scope': 'Eight ordinary fluidity phases, six default unrecorded cascade fixtures, forty warmed density turns, '
                 '36 repeated process rows, separate expensive model diagnostics, one default L4 video and six paired '
                 'new-continuation recordings. Native schedule/continuity and observed visible bounds retain distinct scopes.',
        'counts': {'fluidity': 8, 'cascadeMeasure': 6, 'cascadeVisual': 1, 'density': 40, 'nativeModelCases': 350},
        'localMatch': local_match, 'acceptedSwap': swap, 'newContinuationCases': extra_cases,
        'nativeLocalHandoff': renderers, 'pairedContinuationEvidence': extras,
        'recordedExtraProfiling': recorded_extra_profile,
        'defaultProfiling': profiles, 'cascade': cascade, 'fluidity': fluidity, 'densityProfiling': density,
        'repeatedFinalControl': repeats, 'directProfileComparison': comparison,
        'separateModelDiagnostics': model_diagnostic['rows'],
        'modelDiagnosticScope': 'ExtraModelStages enables additional per-method timers/counters in a separate run. '
                                'Some timers are inclusive/nested (for example vertical work within gravity and '
                                'planning within activation); do not sum them as exclusive CPU percentages or '
                                'substitute their elapsed values for the ordinary-profile command.',
        'observedPerformanceExtremes': {
            'largestDefaultCascadeCommandMs': max(r['commandMs'] for r in cascade if r['variant'] == 'measure'),
            'largestRepeatedCommandMs': max(r['commandMs'] for r in repeated_rows),
            'largestRepeatedIntervalMs': max(r['maxIntervalMs'] for r in repeated_rows),
            'largestRecordedExtraCommandMs': max(r['commandMs'] for r in recorded_extra_rows),
            'largestRecordedExtraIntervalMs': max(r['maxIntervalMs'] for r in recorded_extra_rows),
            'largestFluidityP95Ms': max(r['p95Ms'] for r in fluid['phases']),
            'largestDensityRenderMs': max(r['worstRenderFrame']['cost']['renderMs'] for d in density.values() for r in d['rows'])},
        'remainingGates': limits, 'artifactSHA256': dict(sorted(bound.items())),
        'externalEvidenceSHA256': dict(sorted(external.items())),
        'analyzerSHA256': sha(Path(__file__)), 'profilingValidatorSHA256': sha(PROFILE_FILE)}
    (out / 'Timing_Analysis.json').write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print(json.dumps({'status': result['status'], 'apk_sha256': digest,
                      'counts': result['counts'], 'observedPerformanceExtremes': result['observedPerformanceExtremes']}))


if __name__ == '__main__':
    main()
