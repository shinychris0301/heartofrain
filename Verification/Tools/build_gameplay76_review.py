"""Build a local checkpoint76 evidence gallery; never grant verification approval."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / 'Verification/Evidence/Gameplay76'


def read(path):
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text('utf-8-sig'))
    except (ValueError, OSError):
        return {}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def esc(value):
    return html.escape(str(value), quote=True)


def number(value, places=3):
    return f'{value:.{places}f}' if isinstance(value, (int, float)) and math.isfinite(value) else 'pending'


def table(headers, rows):
    if not rows:
        return '<p class="pending">Awaiting current bound results.</p>'
    return '<div class="scroll"><table><thead><tr>' + ''.join(f'<th>{esc(h)}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{v}</td>' for v in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    summary, artifact, frozen = (read(out / p) for p in ['Summary.json', 'APK_Artifact.json', 'Source_SHA256.json'])
    apk = artifact.get('sha256', '')
    source_digest = digest(out / 'Source_SHA256.json') if frozen else ''
    summary_bound = bool(apk and summary.get('source_checkpoint') == 76 and summary.get('apk_sha256') == apk
                         and summary.get('source_sha256') == source_digest)
    status = summary.get('status') if summary_bound else 'PENDING: final current-source verification and visual review'
    paired, gates = (read(out / p) for p in ['Paired_Performance.json', 'Performance_Gates.json'])
    paired_bound = bool(apk and paired.get('apk_sha256') == apk and paired.get('source_sha256') == source_digest
                        and paired.get('status') == 'ANALYZED_SAME_APK_SMOOTHNESS76')
    gates_bound = bool(apk and gates.get('apk_sha256') == apk and gates.get('source_sha256') == source_digest)

    def local(path):
        target = (out / path).resolve()
        return target if target.is_relative_to(out) and target.is_file() else None

    def link(label, path):
        return f'<a href="{esc(path)}">{esc(label)}</a>' if local(path) else f'<span class="pending">{esc(label)} (pending)</span>'

    reviews, inspected = {}, {}
    for name in ['Visual_Review.json', 'Timing_Visual_Notes.json',
                 'RegressionVisual/Power_Tool_Review.json']:
        report = read(out / name)
        if (apk and report.get('apk_sha256') == apk and report.get('source_sha256') == source_digest
                and str(report.get('status', '')).startswith('REVIEWED')):
            if report.get('sourceCheckpoint', 76) != 76:
                continue
            reviews[name] = report
            for path, expected in report.get('artifactSHA256', {}).items():
                target = local(path)
                if target and digest(target) == expected:
                    inspected[path] = name

    def figure(label, path, native=False, video=False):
        if not local(path) or not native and path not in inspected:
            return ''
        caption = esc(label) + (' <small>Native Editor, source-bound; not Android timing.</small>' if native else f' <small>Bound by {esc(inspected[path])}.</small>')
        media = f'<video controls preload="none" src="{esc(path)}"></video>' if video else f'<a href="{esc(path)}"><img loading="lazy" src="{esc(path)}" alt="{esc(label)}"></a>'
        return f'<figure><figcaption>{caption}</figcaption>{media}</figure>'

    native_rows, native_bound = [], {}
    for path in sorted((out / 'Native').glob('*.json')):
        if path.stem.endswith('_Process'):
            continue
        report, process = read(path), read(path.with_name(path.stem + '_Process.json'))
        source_path = local(process.get('sourceManifest', ''))
        bound = bool(source_path and frozen and process.get('sourceSHA256') == digest(source_path)
                     and read(source_path).get('files') == frozen.get('files') and process.get('exitCode') == 0
                     and not process.get('timedOut') and str(report.get('status', '')).startswith('PASS'))
        if not report:
            continue
        count = report.get('checks', 0)
        if isinstance(count, list):
            count = len(count)
        native_rows.append([link(path.stem, 'Native/' + path.name), esc(count), esc(report.get('status', 'pending')), 'Current source' if bound else 'Pending source binding'])
        if bound:
            native_bound[path.stem] = report

    effect = native_bound.get('EffectBatchChecks', {})
    effect_rows = [[esc(r.get('name', '')), esc(r.get('draws', '')), esc(r.get('zeroAngleDraws', '')),
                    number(r.get('baselineAddMedianMs')), number(r.get('currentAddMedianMs')),
                    number(r.get('currentAddMedianMs', 0) - r.get('baselineAddMedianMs', 0))]
                   for r in effect.get('transformRows', [])]
    effect_images = ''
    if effect:
        base = 'Native/EffectBatchChecks/Artifacts/EffectBatch/Native/'
        for label, name in [('Archived75 native implementation, current fixture', 'MeshesBaseline75.png'),
                            ('Current native implementation, same fixture', 'Meshes.png'),
                            ('Controlled zero/rotated/flipped/scaled/tinted poses', 'TransformsCurrent76.png'),
                            ('Exact75 transform pixel difference', 'DifferenceTransforms75.png')]:
            effect_images += figure(label, base + name, native=True)

    visual = reviews.get('Visual_Review.json', {})
    current_movies = figure('Current76 L4 natural cascade, independently inspected movie', 'Android/Cascade/visual/HR_NaturalCascade.mp4', video=True)
    for level in [14, 31, 33]:
        current_movies += figure(f'Current76 L{level} continuation, independently inspected movie',
                                 f'ContinuationVisual/L{level}/visual/HR_NaturalCascade.mp4', video=True)
    timing_media = ''.join(figure('Current76 timing sample: ' + str(Path(path).parent.name) + ' ' + Path(path).stem, path)
                           for path in visual.get('parentInspection', {}).get('timingSheets', []))
    parent_regression_media = ''.join(figure('Parent inspected current76: ' + Path(path).stem, path)
                                      for key in ['regressionSheets', 'regressionFullOriginals']
                                      for path in visual.get('parentInspection', {}).get(key, []))

    power_tool = reviews.get('RegressionVisual/Power_Tool_Review.json', {})
    regression_media = ''.join(figure('Current76 independent sampled inspection: ' + Path(path).stem, path)
                               for path in power_tool.get('inspection_method', {}).get('contact_sheets', []))
    regression_scope = esc(power_tool.get('scope', 'Pending actual current-APK pair/tool sheet inspection.'))
    regression_observations = ''.join(f'<li>{esc(v)}</li>' for v in power_tool.get('observations', []))
    regression_qualified = ''.join(f'<li><strong>{esc(v.get("id", ""))}:</strong> {esc(v.get("observation", ""))} {esc(v.get("interpretation", ""))}</li>'
                                   for v in power_tool.get('qualified_observations', []))
    regression_limits = ''.join(f'<li>{esc(v)}</li>' for v in power_tool.get('limitations', []))

    limitations = visual.get('limitations', [])
    if isinstance(limitations, str):
        limitations = [limitations]
    remaining = gates.get('remainingGates', []) if gates_bound else []
    if isinstance(remaining, dict):
        remaining = [f'{k}: {v}' for k, v in remaining.items()]
    if not isinstance(remaining, list):
        remaining = [remaining]
    remaining_html = '<ul>' + ''.join(f'<li>{esc(v)}</li>' for v in remaining) + '</ul>' if remaining else '<p class="pending">Final performance gates are pending; no smoothness pass is inferred.</p>'
    paired_preview = ''
    command_table = density_tables = extremes_table = cadence_table = recorded_table = paired_peak_table = ''
    paired_peak_scope = '<p class="pending">Current bound paired live-effect peaks are pending.</p>'
    if paired_bound:
        command = paired.get('commandConstruction', {})
        command_rows = [[esc(r.get('name', '')), number(r.get('baselineMedianMs')), number(r.get('currentMedianMs')),
                         number(r.get('medianDifferenceMs')), number(r.get('medianPairedDifferenceMs')),
                         number(r.get('baselineP95Ms')), number(r.get('currentP95Ms')),
                         number(r.get('baselineMaxMs')), number(r.get('currentMaxMs')),
                         esc(r.get('currentSlowerPairs', '')) + '/' + esc(r.get('pairCount', ''))]
                        for r in command.get('rows', [])]
        command_table = '<h3>Pure Build CPU: every primary pair retained</h3><p>Milliseconds. Difference of medians and median paired difference are separate statistics. Slower-pair counts are retained; GC/cache/emulator effects are not censored or assigned exclusive causality.</p>'
        command_table += table(['Fixture','75 median','76 median','Median difference','Median paired difference','75 p95','76 p95','75 max','76 max','76 slower pairs'], command_rows)
        paired_peak_rows = []
        for branch in ['current76', 'control75Transform']:
            for r in paired.get('pairedDensityExtremes', {}).get(branch, {}).get('byFamilyMode', []):
                paired_peak_rows.append([esc(branch), esc(r.get('family', '')), esc(r.get('mode', '')),
                                         esc(r.get('worstRenderName', '')), number(r.get('worstRenderMs')),
                                         esc(r.get('worstIntervalName', '')), number(r.get('worstIntervalMs'))])
        paired_peak_table = table(['Same-APK branch','Family','Diagnostics','Largest Render fixture','Render ms','Largest interval fixture','Interval ms'], paired_peak_rows)
        peaks = paired.get('observedPerformanceExtremes', {})
        paired_peak_scope = f'<p>The current76 detailed one-stone fixture retains {number(peaks.get("pairedCurrentWorstCapturedRenderMs"))}ms Render and a {number(peaks.get("pairedCurrentWorstIntervalMs"))}ms following frame interval. The separate ordinary-density maximum {number(peaks.get("ordinaryWorstDensityCapturedRenderMs"))}ms does not replace this larger paired-run gate. Both same-APK math branches and every family/mode maximum remain below; Render and interval maxima need not belong to the same call. Detailed/coarse processes and extrema cannot isolate an exclusive CPU, GC, driver or scheduling cause.</p>'
        for family, modes in paired.get('pairedDensity', {}).items():
            for mode in ['detailed', 'coarse']:
                rows = []
                for r in modes.get(mode, {}).get('pairs', []):
                    metrics = r.get('renderStageStats', {}).get('renderMs', {})
                    median, p95 = metrics.get('median', {}), metrics.get('p95', {})
                    rows.append([esc(r.get('count', '')), esc(r.get('repeat', '')),
                                 number(median.get('control75Transform')), number(median.get('current76Transform')),
                                 number(median.get('currentMinusControl75Transform')),
                                 number(p95.get('control75Transform')), number(p95.get('current76Transform')),
                                 number(p95.get('currentMinusControl75Transform'))])
                density_tables += f'<h3>{esc(family)}: {esc(mode)} same-APK transform pairs</h3>'
                density_tables += table(['Obstacle count','Repeat','75 math Render median','76 math Render median','Difference','75 math Render p95','76 math Render p95','Difference'], rows)
        extremes_table = table(['Observed metric','Milliseconds'], [[esc(k), number(v)] for k, v in paired.get('observedPerformanceExtremes', {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)])
        cadence = paired.get('ordinaryCadence', {})
        cadence_table = table(['Case','Target fps','Budget ms','Largest interval ms','Budget ratio','Frames above1.5× budget'],
                              [[esc(r.get('name', '')), esc(r.get('targetFps', '')), number(r.get('targetIntervalMs')),
                                number(r.get('maxIntervalMs')), number(r.get('maxIntervalBudgetRatio')),
                                esc(r.get('framesOver1_5TargetBudget', ''))] for r in cadence.get('rows', [])])
        recorded = [paired['recordedDefaultL4']] if paired.get('recordedDefaultL4') else []
        recorded += paired.get('recordedContinuationControls', {}).get('rows', [])
        recorded_table = table(['Recorded fixture','Model ms','Accept ms','Command ms','Enqueue Build ms','Largest interval ms'],
                               [[esc(r.get('name', 'L' + str(r.get('level', '')))), number(r.get('modelMs')),
                                 number(r.get('acceptMs')), number(r.get('commandMs')), number(r.get('buildMs')),
                                 number(r.get('maxIntervalMs'))] for r in recorded])
        # The analysis owns its schema and verdict. Keep every field available
        # without inventing a speedup threshold or filtering slower rows.
        for key, value in paired.items():
            if key in {'artifactSHA256', 'apk_sha256', 'utc', 'status'}:
                continue
            paired_preview += f'<details><summary>{esc(key)}</summary><pre>{esc(json.dumps(value, indent=2))}</pre></details>'
    else:
        paired_preview = '<p class="pending">Current same-APK analysis is pending. No control or speedup verdict is shown.</p>'

    css = 'body{margin:24px;background:#10283c;color:#fff6dc;font:16px system-ui;line-height:1.55}main{max-width:1450px;margin:auto}a{color:#8fdaff}p{max-width:1150px}.pending{color:#e8ca85}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:18px}figure{margin:0;padding:12px;background:#193b54;border:1px solid #bb9b52;border-radius:10px}figcaption{font-weight:600;margin-bottom:10px}small{display:block;font-weight:400}img,video{display:block;width:100%;height:auto;max-height:700px;object-fit:contain}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;margin:18px 0}th,td{padding:9px;border:1px solid #587184;text-align:left}code{overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;background:#193b54;padding:12px}details{margin:12px 0}summary{cursor:pointer;color:#8fdaff}'
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Checkpoint76 smoothness evidence</title><style>{css}</style><main>
<h1>Command construction and effect-transform review</h1><p><strong>{esc(status)}</strong></p>
<p>Checkpoint76 evaluates narrower command-construction work and an exact-zero-angle effect transform. Authored art, effect counts, geometry, sorting, model results and conservative cascade ownership remain verification requirements. Main LDPlayer retains deployment64; QA is the isolated review target.</p>
<p>Final APK: <code>{esc(apk or 'pending')}</code><br>Source manifest: <code>{esc(source_digest or 'pending')}</code></p>
<p>{link('Collected results', 'Summary.json')} · {link('Same-APK paired analysis', 'Paired_Performance.json')} · {link('Remaining performance gates', 'Performance_Gates.json')} · {link('Sampled visual review', 'Visual_Review.json')} · {link('Original-PTS movie review', 'Timing_Visual_Notes.json')} · {link('Pair/tool still review', 'RegressionVisual/Power_Tool_Review.json')} · {link('Frozen inputs', 'Source_SHA256.json')} · {link('Source delta', 'Source_Delta.json')}</p>
<h2>Separate evidence scopes</h2>
<ul><li><strong>Native Editor:</strong> exact archived75 queue/mesh/pixel controls and alternating warmed CPU spans. Camera rendering and GPU completion are outside construction timing.</li>
<li><strong>Same-APK Android command pairs:</strong> repeated Build construction with the preserved75 planner and current planner in one process. This excludes model solving, Accept/Next, rendering and touch/display latency.</li>
<li><strong>Same-APK Android effect pairs:</strong> the legacy trigonometry branch and current exact-zero shortcut use the same final APK. Coarse diagnostics omit per-draw Stopwatch measurements; their zero per-draw fields mean unmeasured work. Ordinary detailed diagnostics remain separate.</li>
<li><strong>Archived75:</strong> a verified source/APK baseline, not a fresh same-process control and not current76 imagery. Cross-build/run changes alone do not establish causality. <a href="../Gameplay75/Comparison.html">Open archived75 review</a>.</li>
<li><strong>Visual and campaign checks:</strong> sampled current media and accelerated functional regression have different scopes. No new Match Villains recording, identical-puzzle comparison, whole-game hitch-free or physical-device claim is made.</li></ul>
<h2>Remaining measurements and limits</h2>{remaining_html}
<p>Slower and flat measurements must remain in the linked complete paired analysis. A faster isolated operation does not guarantee a faster complete turn or sustained60fps.</p>
<h3>Paired live-effect peaks remain open</h3>{paired_peak_scope}{paired_peak_table}
<h2>Same-APK paired results</h2>{command_table}{density_tables}<p>Detailed/coarse rows above come from separate process launches. Comparing them does not isolate timer overhead. The75 effect control toggles only trigonometry; all other code remains76. Render distributions refer to separately played fixtures, without frame-by-frame pose alignment. Mixed and slower effect results remain visible; no overall effect speedup is claimed.</p>
<h3>Ordinary cadence relative to the requested frame rate</h3><p>A normal15fps frame lasts about66.67ms. The largest raw interval across mixed frame-rate tests is therefore not automatically a hitch. Each interval below is normalized to its own target; the60fps row must be assessed against16.67ms. The explicit late-frame count uses1.5× that row's budget.</p>{cadence_table}
<h3>Recorded command spans</h3><p>These four current-only recorded runs include camera/recording/debug/OS conditions. Enqueue Build includes queue.AddRange; pure paired Build above does not. Model/Accept/Build spans nest and must not be added. Recorded spans remain separate from ordinary unrecorded timing and do not imply a fresh competitor comparison.</p>{recorded_table}
<h3>Observed extrema, with separate scopes</h3>{extremes_table}<details><summary>Complete analysis, including archived75 ordinary rows and native controls</summary>{paired_preview}</details>
<h2>Native exact-zero transform controls</h2><p>The shortcut applies only to exact zero angle, including signed zero. Near-zero/nonzero rotations retain the original trigonometry. Vertex operation order, scales, UVs, tint, materials and uploads are retained. The native proof accepts no geometry epsilon or changed pixel channel.</p>
{table(['Fixture/mode','Draws','Exact-zero draws','Archived75 Add median ms','Current Add median ms','Current minus75 ms'], effect_rows)}
<p>{link('Full native effect report', 'Native/EffectBatchChecks.json')} · {link('Current playback-construction proof', 'Native/PlaybackConstruction.json')} · {link('Command construction proof', 'Native/SmoothnessCommand.json')}</p>
<div class="grid">{effect_images or '<p class="pending">Current source-bound native plates are pending.</p>'}</div>
<h2>Fresh Android playback</h2><p>All four current movies were independently inspected with original-PTS samples. Only media whose hashes match a current source/APK-bound review is embedded. Movie observations and measured CPU spans have separate scopes; unchanged native schedules and overlapping75 uncertainty bounds do not establish a new timing speedup.</p><div class="grid">{current_movies or '<p class="pending">Fresh final-APK movie inspection is pending.</p>'}</div><details><summary>Parent inspected timing sheets</summary><div class="grid">{timing_media or '<p class="pending">Current bound timing sheets are pending.</p>'}</div></details>
<h2>Sampled powers, obstacles and connected flows</h2><p>{esc(visual.get('parentInspection', {}).get('regressionFinding', 'Pending current parent inspection.'))}</p><p>These are the exact parent-listed inspected sheets and full originals, including both six-power sheets and the two obstacle gesture outcomes. Thumbnail and full-image scopes remain explicit in the linked review; these samples do not certify every frame or all-feature completeness.</p><details><summary>Parent inspected regression sheets and full originals</summary><div class="grid">{parent_regression_media or '<p class="pending">Current bound regression/gesture images are pending.</p>'}</div></details>
<h2>Independent pair and tool still inspection</h2><p>{regression_scope}</p><p>{link('Exact inspection, source/APK and all constituent hashes', 'RegressionVisual/Power_Tool_Review.json')}</p><ul>{regression_observations}{regression_qualified}</ul><details><summary>Eight inspected current contact sheets</summary><div class="grid">{regression_media or '<p class="pending">Fresh final-APK sheet inspection is pending.</p>'}</div></details><ul>{regression_limits}</ul>
<h2>Parent visual-review scope</h2><p>{esc(visual.get('scope', 'Pending actual current-APK image/video inspection.'))}</p><ul>{''.join(f'<li>{esc(v)}</li>' for v in limitations)}</ul>
<h2>Current native runs</h2>{table(['Suite','Checks','Result','Source binding'], native_rows)}
<p>{link('Full50-board Android regression', 'Android/Regression/Regression.json')} · {link('Live power idle samples', 'Android/Regression/M70_Device.json')} · {link('APK packaging checks', 'APK_Artifact.json')} · {link('Preserved75 baseline', 'Baseline75.json')}</p>
<p>This page presents linked evidence and never grants test or visual approval. Approval remains defined by the strict collector and the bound human inspection notes.</p></main></html>'''
    (out / 'Comparison.html').write_text(page, 'utf-8')
    print(json.dumps({'gallery': str(out / 'Comparison.html'), 'summaryBound': summary_bound,
                      'pairedBound': paired_bound, 'currentReviewedArtifacts': len(inspected)}))


if __name__ == '__main__':
    main()
