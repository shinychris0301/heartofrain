"""Summarize final checkpoint73 timing evidence; never grant FPS/visual approval.

Requires the independently inspected final visual notes. Video capture remains
separate from the eight fluidity, six cascade and forty warmed density cases.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / 'Verification/Evidence/LocalCascade73'
DEFAULT_BASE = ROOT / 'Verification/Evidence/Gameplay72'
FAMILIES = ['crate', 'stone', 'gate', 'tiles']


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
        need(not {'Discarded', 'BeforeOnset'} & set(result.parts), 'Historical/occluded proof rejected')
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

    artifact = read('APK_Artifact.json')
    digest = artifact['sha256']
    old_artifact = read('APK_Artifact.json', base)
    baseline = read('Baseline_72.json')
    need(digest != old_artifact['sha256'] == baseline['apk_sha256'], 'Final APK is not a distinct checkpoint 73 artifact')
    need(sha(path('APK_Artifact.json', base)) == baseline['artifact_sha256'], 'Archived72 artifact changed')
    need(sha(path('Summary.json', base)) == baseline['summary_sha256'], 'Archived72 summary changed')
    visual = read('Timing_Visual_Notes.json')
    need(visual['status'] == 'REVIEWED_LOCAL_CASCADE73_WITH_REMAINING_GATES'
         and visual['apk_sha256'] == digest, 'Final visual timing review missing/wrong APK')
    need(visual.get('remainingGates') and visual.get('artifactSHA256'), 'Visual review lacks limitations/bindings')
    for name, expected in visual['artifactSHA256'].items():
        need(sha(path(name)) == expected, 'Visual artifact changed: ' + name)
        bound[name] = expected
    local_match = visual['localMatch']
    baseline_gap = read('Timing_Visual_Notes.json', base)['verifiedRemainingGap']['observations']['contactToReactionBoundMs']
    need(local_match['case'] == 'L4_0_30'
         and local_match['baselineContactToReactionBoundMs'] == baseline_gap, 'Visible baseline is not comparable to checkpoint 72')
    gap = local_match['contactToReactionBoundMs']
    need(len(gap) == 2 and 0 <= gap[0] <= gap[1], 'Invalid observed visible interval')

    def installation(name):
        report = read(name)
        need(report['serial'] == 'emulator-5556'
             and report.get('apk_sha256', report.get('sha256')) == digest, 'Wrong APK/instance: ' + name)
        if 'installed_apk_sha256' in report:
            need(report['installed_apk_sha256'] == digest, 'Installed identity differs: ' + name)
        return report

    fluidity = read('Android/Fluidity/Measurement.json')
    installation('Android/Fluidity/Installation.json')
    old_fluidity = read('Android/Fluidity/Measurement.json', base)
    need(fluidity['status'] == 'RECORDED_NATIVE_FLUIDITY' and fluidity['isolatedProfile']
         and fluidity['launchCleared'] and len(fluidity['phases']) == 8, 'Fluidity capture is incomplete/occluded')
    old_phases = unique_rows(old_fluidity['phases'])
    phases = []
    for index, row in enumerate(fluidity['phases']):
        frames = [f for f in fluidity['frameSamples'] if f['phase'] == index]
        need(bool(frames) and row['name'] in old_phases, 'Fluidity frame/case mismatch')
        prior = old_phases[row['name']]
        phases.append(selected(row, ['name', 'frames', 'p95Ms', 'worstMs', 'over33ms', 'over50ms', 'modelMs', 'acceptMs',
                                      'commandMs', 'firstPresentationMs', 'settleSeconds',
                                      'preparationSeconds', 'synchronousTextureLoads', 'spriteCreates', 'gen0Collections']) | {
            'measuredFrameSamples': len(frames),
            'worstUpdateMs': max(f['updateMs'] for f in frames),
            'worstRenderMs': max(f['renderMs'] for f in frames),
            'baseline72': selected(prior, ['p95Ms', 'worstMs', 'modelMs', 'acceptMs', 'commandMs']),
            'comparisonScope': 'Separate emulator runs; differences do not isolate the causal effect of local scheduling.'})

    native = read('Native/LocalCascade.json')
    need(native['status'] == 'PASS_NATIVE_LOCAL_CASCADE73' and native['modelCases'] == 350
         and native['rawTurnParity'] and native['finalSnapshotParity'], 'Native parity proof is incomplete')
    renderers = native['rendererRows']
    need(renderers and any(r['caseName'] == 'L4_match' for r in renderers), 'L4 renderer proof missing')
    need(all(r['samples'] > 0 and r['maxBoundaryPositionJump'] < .001
             and r['maxBoundaryScaleJump'] < .001 for r in renderers), 'Native body continuity failed')
    l4_native = [r for r in renderers if r['caseName'] == 'L4_match']

    cascade_rows, transitions = [], []
    for variant, count in [('measure', 6), ('visual', 1)]:
        folder = 'Android/Cascade/' + variant + '/'
        installation(folder + 'Installation.json')
        report, old = read(folder + 'Report.json'), read(folder + 'Report.json', base)
        need(report['status'] == 'PASS_CASCADE_PLAYBACK' and len(report['rows']) == count, 'Cascade capture incomplete')
        old_rows = unique_rows(old['rows'])
        for row in report['rows']:
            prior = old_rows[row['name']]
            need((row['turnHash'], row['finalHash']) == (prior['turnHash'], prior['finalHash']), 'Cascade model changed')
            summary = selected(row, ['name', 'targetFps', 'matches', 'wallSeconds', 'scheduledSeconds',
                                     'lateFrames', 'maxIntervalMs']) | {
                'variant': variant,
                'baseline72': selected(prior, ['wallSeconds', 'scheduledSeconds', 'lateFrames', 'maxIntervalMs'])}
            cascade_rows.append(summary)
            if row['name'].startswith('L4_'):
                powers = [p for p in row['phases'] if p['kind'] == 'powerFall']
                for phase_index, (previous, following) in enumerate(zip(powers, powers[1:])):
                    offset = 1000 * (following['clock'] - previous['clock'] - previous['lastContact'])
                    if phase_index == 0:
                        need(abs(offset + l4_native[0]['secondsSaved'] * 1000) < .1,
                             'Device L4 did not dispatch the verified early handoff')
                    transitions.append({'case': row['name'], 'variant': variant, 'transitionIndex': phase_index,
                        'nextDispatchClockMinusPreviousGlobalContactMs': offset,
                        'nextDispatchWallMinusPreviousGlobalContactMs': 1000 * (following['wall'] - previous['wall'] - previous['lastContact']),
                        'meaning': 'Negative clock value can be the intended early safe handoff; callback dispatch is not a rendered pose.'})

    density = {}
    for family in FAMILIES:
        folder = 'Android/Density/candidate_review-' + family + '/'
        installation(folder + 'Installation.json')
        report, old = read(folder + 'Report.json'), read(folder + 'Report.json', base)
        need(report['status'] == 'PASS_OBSTACLE_DENSITY_PLAYBACK' and report['family'] == family
             and len(report['rows']) == 10, 'Incomplete density sweep: ' + family)
        old_rows = unique_rows(old['rows'])
        rows = []
        for index, row in enumerate(report['rows']):
            prior = old_rows[row['name']]
            need((row['turnHash'], row['finalHash']) == (prior['turnHash'], prior['finalHash']), 'Density model changed')
            frames = [f for f in report['frames'] if f['phase'] == index]
            need(bool(frames), 'No density frames: ' + row['name'])
            burst = [f for f in frames if f['draws'] >= row['peakDraws'] * .5]
            prior_index = next(i for i, item in enumerate(old['rows']) if item['name'] == row['name'])
            prior_frames = [f for f in old['frames'] if f['phase'] == prior_index]
            prior_burst = [f for f in prior_frames if f['draws'] >= prior['peakDraws'] * .5]
            rows.append(selected(row, ['name', 'hits', 'cleared', 'peakDraws', 'peakMeshes', 'modelMs',
                                        'acceptMs', 'commandMs', 'renderersCreated', 'crateSpritesCreated']) | {
                'measuredFrames': len(frames), 'burstFrames': len(burst),
                'burstP95IntervalMs': percentile([f['intervalMs'] for f in burst]),
                'burstP95RenderMs': percentile([f['renderMs'] for f in burst]),
                'burstWorstRenderMs': max(f['renderMs'] for f in burst),
                'baseline72': selected(prior, ['modelMs', 'acceptMs', 'commandMs', 'peakDraws']) | {
                    'burstFrames': len(prior_burst),
                    'burstP95IntervalMs': percentile([f['intervalMs'] for f in prior_burst]),
                    'burstP95RenderMs': percentile([f['renderMs'] for f in prior_burst]),
                    'burstWorstRenderMs': max(f['renderMs'] for f in prior_burst)}})
        density[family] = rows

    result = {
        'status': 'ANALYZED_LOCAL_CASCADE73_WITH_REMAINING_GATES',
        'utc': datetime.now(timezone.utc).isoformat(), 'apk_sha256': digest,
        'baseline_apk_sha256': old_artifact['sha256'],
        'scope': 'Final QA emulator evidence: eight unaccelerated fluidity phases, six no-recording cascade cases, '
                 'forty warmed density turns and one separately recorded visual case. Native cadence/model proofs '
                 'are distinct from device timings. No whole-game or physical-device FPS certification.',
        'counts': {'fluidity': len(phases), 'cascadeMeasure': 6, 'cascadeVisual': 1,
                   'density': sum(len(v) for v in density.values()), 'nativeModelCases': native['modelCases']},
        'nativeLocalHandoff': l4_native, 'localMatch': local_match,
        'visibleImprovementBoundMs': [baseline_gap[0] - gap[1], baseline_gap[1] - gap[0]],
        'fluidity': phases, 'cascade': cascade_rows, 'cascadeTransitions': transitions, 'density': density,
        'interpretation': [
            'The native L4 schedule saves about 200 ms and retains about 245 ms before the next phase; those are scheduled quantities, not an exact video-measured improvement.',
            'Observed local contact/reaction bounds, body landing and carry continuity come from the separately inspected original-PTS recording.',
            'An early handoff legitimately precedes the previous global last contact. Unfinished independent routes continue in the next phase; this is not negative clock debt.',
            'StepStarted is a dispatch callback. It is not the first displayed pose, touch response, or actual landing event.',
            'Interval samples include emulator/OS scheduling. Coroutine command CPU can occur after GameplayScreen.Update and appear in the following interval; do not attribute that interval solely to its sampled render time.',
            'Density cases include an untimed warm-up. Zero sprite/renderer growth is not zero managed allocation or cold-process performance.',
            'Cross-run performance changes are descriptive; asset/process warming and emulator translation/scheduling prevent attributing every change to the restricted handoff.',
            'Match Villains reference clips are archived and have sampling uncertainty; current reference gameplay capture was blocked. Exact reference parity is not established.'
        ],
        'remainingGates': visual['remainingGates'] + [
            'Synchronous model/acceptance work remains an input-latency gate; the restricted handoff does not make commands asynchronous.',
            'Warm QA measurements do not certify cold-process, sustained 60 fps, physical Android GPU/memory, or long-soak performance.',
            'Android managed allocation counter availability is reported by the raw fluidity measurement; zero renderer growth must not be substituted for allocation proof.'
        ],
        'artifactSHA256': dict(sorted(bound.items())),
        'externalEvidenceSHA256': dict(sorted(external.items())),
        'analyzerSHA256': sha(Path(__file__)),
    }
    (out / 'Timing_Analysis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'apk_sha256': digest, 'counts': result['counts'],
                      'visibleImprovementBoundMs': result['visibleImprovementBoundMs']}))


if __name__ == '__main__':
    main()
