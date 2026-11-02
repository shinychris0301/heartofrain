"""Compare same-APK effect-rendering controls on the QA emulator (checkpoint 60).

baseline_* variants draw effects through one SpriteRenderer each; candidate_*
variants through the effect mesh batcher. A "-stone", "-gate" or "-tiles"
suffix breaks that family instead of crates. Writes Performance_Comparison.json
beside the per-variant folders; never touches other checkpoints' evidence.
"""
import argparse, json, statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/EffectBatch'


def read(p): return json.loads(p.read_text('utf-8-sig'))
def percentile(values, p): return sorted(values)[min(len(values) - 1, int(len(values) * p))]


def timing(frames):
    metrics = {}
    for name in ['renderMs', 'sampleMs', 'updateMs', 'intervalMs']:
        values = [f[name] for f in frames]
        metrics[name] = {'median': round(statistics.median(values), 3), 'p95': round(percentile(values, .95), 3), 'max': round(max(values), 3)}
    metrics['otherRenderMs'] = {'median': round(statistics.median(f['renderMs'] - f['sampleMs'] for f in frames), 3), 'p95': round(percentile([f['renderMs'] - f['sampleMs'] for f in frames], .95), 3)}
    return {'frames': len(frames), 'intervals_above_41_7ms': sum(f['intervalMs'] > 41.7 for f in frames), 'intervals_above_20ms': sum(f['intervalMs'] > 20 for f in frames),
            'peak_draws': max(f['draws'] for f in frames), 'peak_meshes': max(f['meshes'] for f in frames), 'metrics': metrics}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    android = args.out.resolve() / 'Android'
    groups, turns, finals, installs = {}, {}, {}, []
    for folder in sorted(p for p in android.iterdir() if p.is_dir() and (p / 'Report.json').exists()):
        variant = folder.name
        side = variant.split('_')[0]
        family = variant.split('-')[1] if '-' in variant else 'crate'
        r = read(folder / 'Report.json')
        install = read(folder / 'Installation.json')
        assert r['status'] == 'PASS_OBSTACLE_DENSITY_PLAYBACK' and not r['errors'] and len(r['rows']) == 10, variant
        assert install['before'] == install['after'] and install['runtime_errors'] == 0, variant
        installs.append({'variant': variant, 'apk_sha256': install['apk_sha256'], 'installed_apk_sha256': install['installed_apk_sha256']})
        for i, row in enumerate(r['rows']):
            count = row['crates'] if family != 'tiles' else 0
            key = (family, count)
            assert row['renderersCreated'] == 0, variant
            assert row['turnHash'] == turns.setdefault(key, row['turnHash']), 'Turn differs between variants ' + variant
            assert row['finalHash'] == finals.setdefault(key, row['finalHash']), 'Final board differs between variants ' + variant
            frames = [f for f in r['frames'] if f['phase'] == i]
            assert frames, variant
            peak = max(f['draws'] for f in frames)
            burst = [f for f in frames if f['draws'] >= peak * .5]
            if side == 'candidate':
                assert row['peakMeshes'] >= 1 and all(f['meshes'] >= 1 for f in burst), 'Candidate did not batch ' + variant
            else:
                assert row['peakMeshes'] == 0, 'Baseline batched ' + variant
            g = groups.setdefault(key, {}).setdefault(side, {'rows': [], 'frames': [], 'burst': []})
            g['rows'].append(row); g['frames'] += frames; g['burst'] += burst
    assert len({i['apk_sha256'] for i in installs}) == 1 and all(i['apk_sha256'] == i['installed_apk_sha256'] for i in installs), 'Mixed or wrong APKs'
    comparisons = []
    for (family, count), sides in sorted(groups.items()):
        entry = {'family': family, 'count': count}
        for side, data in sides.items():
            entry[side] = {'turns': len(data['rows']), 'whole_turn': timing(data['frames']), 'burst_window': timing(data['burst']),
                           'median_preparation_seconds': round(statistics.median(r['preparationSeconds'] for r in data['rows']), 3),
                           'median_command_ms': round(statistics.median(r['commandMs'] for r in data['rows']), 2)}
        comparisons.append(entry)
    summary = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'PASS_EFFECT_BATCH_ANDROID_CONTROLS',
               'scope': 'Same final development APK on QA LDPlayer. Isolated fixed-geometry fixtures (cloned level 26, Double Orb at (4,5)/(5,5)); baseline renders effects through SpriteRenderers, candidate through the effect mesh batcher; every other optimization is identical. Elapsed CPU sections and frame intervals include emulator scheduling; not GPU or physical-device certification.',
               'window_definition': 'Whole turn keeps every measured frame. Burst window keeps frames whose draw count is at least half of that turn\'s peak draw count, the same rule for both variants and every family.',
               'apk_sha256': installs[0]['apk_sha256'], 'variants': [i['variant'] for i in installs], 'groups': comparisons}
    (args.out.resolve() / 'Performance_Comparison.json').write_text(json.dumps(summary, indent=2) + '\n', 'utf-8')
    for entry in comparisons:
        line = f"{entry['family']:6s} {entry['count']:3d}"
        for side in ('baseline', 'candidate'):
            if side not in entry: continue
            w = entry[side]['burst_window']; m = w['metrics']
            line += f" | {side}: draws {w['peak_draws']:4d} meshes {w['peak_meshes']:2d} render p50/p95 {m['renderMs']['median']:5.1f}/{m['renderMs']['p95']:5.1f} ms, update p95 {m['updateMs']['p95']:5.1f}, interval p50/p95 {m['intervalMs']['median']:5.1f}/{m['intervalMs']['p95']:5.1f}, >41.7ms {w['intervals_above_41_7ms']:3d}/{w['frames']}"
        print(line)


if __name__ == '__main__':
    main()
