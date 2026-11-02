"""Summarize measured Android timings without turning recordings into FPS approval."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Gameplay72'


def read(name):
    return json.loads((OUT / name).read_text('utf-8-sig'))


def percentile(values, share=.95):
    return sorted(values)[max(0, math.ceil(len(values) * share) - 1)]


def main():
    artifact = read('APK_Artifact.json')
    fluidity = read('Android/Fluidity/Measurement.json')
    cascade = read('Android/Cascade/measure/Report.json')
    visual = read('Timing_Visual_Notes.json')
    sources = ['APK_Artifact.json', 'Android/Fluidity/Measurement.json',
               'Android/Cascade/measure/Report.json', 'Reference_Analysis.json', 'Timing_Visual_Notes.json']
    phases = []
    for index, phase in enumerate(fluidity['phases']):
        frames = [f for f in fluidity['frameSamples'] if f['phase'] == index]
        phases.append({key: phase[key] for key in ['name', 'frames', 'p95Ms', 'worstMs',
                      'modelMs', 'acceptMs', 'commandMs', 'firstPresentationMs', 'settleSeconds',
                      'spriteCreates', 'gen0Collections']} | {
            'worstUpdateMs': max(f['updateMs'] for f in frames),
            'worstRenderMs': max(f['renderMs'] for f in frames)})
    cascade_rows, transitions = [], []
    for row in cascade['rows']:
        cascade_rows.append({key: row[key] for key in ['name', 'targetFps', 'matches',
                             'wallSeconds', 'scheduledSeconds', 'lateFrames', 'maxIntervalMs']})
        if row['name'].startswith('L4_'):
            powers = [p for p in row['phases'] if p['kind'] == 'powerFall']
            for previous, following in zip(powers, powers[1:]):
                transitions.append({'case': row['name'],
                    'scheduledExtraGapMs': max(0, following['clock'] - previous['clock'] - previous['lastContact']) * 1000,
                    'dispatchExtraGapMs': (following['wall'] - previous['wall'] - previous['lastContact']) * 1000})
    density = {}
    for family in ['crate', 'stone', 'gate', 'tiles']:
        name = 'Android/Density/candidate_review-' + family + '/Report.json'
        sources.append(name)
        report = read(name)
        rows = []
        for index, row in enumerate(report['rows']):
            frames = [f for f in report['frames'] if f['phase'] == index]
            burst = [f for f in frames if f['draws'] >= row['peakDraws'] * .5]
            rows.append({key: row[key] for key in ['name', 'hits', 'cleared', 'peakDraws',
                         'peakMeshes', 'modelMs', 'acceptMs', 'commandMs', 'renderersCreated',
                         'crateSpritesCreated']} | {
                'measuredFrames': len(frames), 'burstFrames': len(burst),
                'burstP95IntervalMs': percentile([f['intervalMs'] for f in burst]),
                'burstP95RenderMs': percentile([f['renderMs'] for f in burst]),
                'burstWorstRenderMs': max(f['renderMs'] for f in burst)})
        density[family] = rows
    result = {
        'status': 'ANALYZED_ANDROID_TIMINGS_WITH_OPEN_PERFORMANCE_GATES',
        'utc': datetime.now(timezone.utc).isoformat(), 'apk_sha256': artifact['sha256'],
        'scope': 'Unaccelerated QA emulator fixtures; elapsed sections include emulator scheduling. Timings are measured separately from video capture and accelerated full regression.',
        'fluidity': phases, 'cascade': cascade_rows, 'cascadeTransitions': transitions,
        'density': density,
        'remainingGameplayDefects': [visual['verifiedRemainingGap']],
        'interpretation': [
            'First-pose clock correction is verified by native renderer/clock controls, not inferred from StepStarted dispatch.',
            'Scheduled cascade gap is measured from board clock and last motion contact. Wall dispatch varies with frame pacing.',
            'Zero gap at the final global contact does not establish immediate local-match reaction. The final video separately confirms a505–576ms local contact-to-reaction delay.',
            'Density rows include an untimed warm-up; zero renderer/sprite growth does not establish zero managed allocation or cold-start performance.',
            'Fluidity power fixtures inject powers after preparation. Their loading/acceptance costs are useful diagnostics, not a direct measurement of every normal board power.',
            'Preceding-APK timing probe failed startup. BeforeOnset is a valid functional/visible baseline, but timing samples do not isolate a causal whole-game speedup.',
            'Archived Match Villains frames give visible timing ranges with sampling uncertainty; fresh gameplay was blocked on its loading screen.'
        ],
        'remainingGates': [
            'Confirmed local matches can wait for unrelated long refill routes; dependency-aware cross-phase body scheduling remains required.',
            'Synchronous model/acceptance command spikes remain visible on the emulator.',
            'Dense power effects still have occasional long render/frame intervals; sustained60fps is not certified.',
            'Allocation counter was unavailable on this Android player; GC collections are recorded instead.',
            'Repeat sustained cold and warm profiling on representative physical Android devices before launch.'
        ],
        'artifactSHA256': {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in sources}}
    (OUT / 'Timing_Analysis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'phases': len(phases), 'cascadeTransitions': len(transitions),
                      'densityRows': sum(map(len, density.values()))}))


if __name__ == '__main__':
    main()
