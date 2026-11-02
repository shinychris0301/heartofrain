"""Build a local checkpoint77 gallery from bound evidence, without granting approval."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / 'Verification/Evidence/Gameplay77'


def read(path):
    try:
        return json.loads(path.read_text('utf-8-sig')) if path.is_file() else {}
    except (OSError, ValueError):
        return {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def esc(value):
    return html.escape(str(value), quote=True)


def number(value):
    return f'{value:.3f}' if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else 'pending'


def table(headers, rows):
    if not rows:
        return '<p class="pending">Awaiting current bound measurements.</p>'
    return '<div class="scroll"><table><thead><tr>' + ''.join(f'<th>{esc(x)}</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def details(label, data):
    return f'<details><summary>{esc(label)}</summary><pre>{esc(json.dumps(data, indent=2))}</pre></details>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    def local(name):
        if not isinstance(name, str):
            return None
        path = (out / name).resolve()
        return path if path.is_relative_to(out) and path.is_file() else None

    def link(label, name):
        return f'<a href="{esc(name)}">{esc(label)}</a>' if local(name) else f'<span class="pending">{esc(label)} (pending)</span>'

    frozen, artifact, summary = (read(out / p) for p in ['Source_SHA256.json', 'APK_Artifact.json', 'Summary.json'])
    source = sha(out / 'Source_SHA256.json') if frozen else ''
    apk = artifact.get('sha256', '')

    def bound(report):
        return bool(apk and source and report.get('apk_sha256') == apk and report.get('source_sha256') == source
                    and report.get('source_checkpoint', 77) == 77 and report.get('sourceCheckpoint', 77) == 77)

    summary_bound = bound(summary) and summary.get('source_checkpoint') == 77
    status = summary.get('status') if summary_bound else 'PENDING: current source, APK, verification and actual visual review'
    analysis = read(out / 'Performance_Analysis.json')

    def artifacts_valid(report):
        own = report.get('artifactSHA256', {})
        if not own or not all(local(name) and sha(local(name)) == digest for name, digest in own.items()):
            return False
        for name, digest in report.get('externalEvidenceSHA256', {}).items():
            path = (ROOT / name).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file() or sha(path) != digest:
                return False
        return True

    analysis_bound = (bound(analysis) and analysis.get('status') == 'ANALYZED_POWER_FALL77_WITH_REMAINING_GATES'
                      and artifacts_valid(analysis))

    reviews, inspected = {}, {}
    for name in ['Visual_Review.json', 'Timing_Visual_Notes.json', 'RegressionVisual/Power_Tool_Review.json']:
        report = read(out / name)
        if bound(report) and str(report.get('status', '')).startswith('REVIEWED') and artifacts_valid(report):
            reviews[name] = report
            inspected.update({path: name for path in report['artifactSHA256']})

    def figure(name, caption=None):
        if name not in inspected or not local(name):
            return ''
        suffix = Path(name).suffix.lower()
        if suffix == '.mp4':
            content = f'<video controls preload="none" src="{esc(name)}"></video>'
        elif suffix == '.png':
            content = f'<a href="{esc(name)}"><img loading="lazy" src="{esc(name)}" alt="{esc(caption or name)}"></a>'
        else:
            return ''
        return f'<figure><figcaption>{esc(caption or name)}<small>Actual inspection bound by {esc(inspected[name])}.</small></figcaption>{content}</figure>'

    native, native_rows = {}, []
    for path in sorted((out / 'Native').glob('*.json')):
        if path.stem.endswith('_Process'):
            continue
        report = read(path)
        if not report.get('status'):
            continue
        process = read(path.with_name(path.stem + '_Process.json'))
        manifest = local(process.get('sourceManifest'))
        current = bool(manifest and frozen and process.get('sourceSHA256') == sha(manifest)
                       and read(manifest).get('files') == frozen.get('files') and process.get('exitCode') == 0
                       and not process.get('timedOut') and str(report['status']).startswith('PASS'))
        checks = report.get('checks', 0)
        checks = len(checks) if isinstance(checks, list) else checks
        native_rows.append([link(path.stem, 'Native/' + path.name), esc(checks), esc(report['status']), 'Current frozen source' if current else 'Pending source binding'])
        if current:
            native[path.stem] = report

    sampling, preparation = native.get('PowerFallSampling', {}), native.get('PowerFallPreparation', {})
    timing_rows = []
    for row in sampling.get('timings', []):
        old, new = row.get('legacyMedianMs'), row.get('currentMedianMs')
        delta = new - old if isinstance(old, (int, float)) and isinstance(new, (int, float)) else None
        timing_rows.append([esc(row.get('name', '')), esc(row.get('pairs', '')), esc(row.get('samplesPerBatch', '')),
                            number(old), number(new), number(delta), number(row.get('legacyP95Ms')),
                            number(row.get('currentP95Ms')), esc(row.get('currentSlowerPairs', ''))])
    sampling_table = table(['Native fixture','Pairs','Poses/batch','76 median ms','77 median ms','Difference','76 p95 ms','77 p95 ms','77 slower pairs'], timing_rows)
    prep_metrics = ['replayedFrames', 'coldCreates', 'preparedDemandCreates', 'preparedDemandGeometryMisses',
                    'preparationFrames', 'preparationCreates', 'preparationBatches', 'overlapFrames', 'skippedEvictedAtlases']
    prep_table = table(['Native original-clock replay metric','Observed count'],
                       [[esc(key), esc(preparation[key])] for key in prep_metrics if key in preparation])

    measured = ''
    natural_table = natural_pair_table = frozen_table = extremes_table = broader_tables = ''
    gates = []
    if analysis_bound:
        gates = analysis.get('remainingGates', analysis.get('remaining_gates', []))
        natural_rows = []
        for row in analysis.get('naturalRows', []):
            post, fall, raw = row.get('postCommand', {}), row.get('powerFall', {}), row.get('rawRow', {})
            render, interval = post.get('renderMs', {}), post.get('intervalMs', {})
            natural_rows.append([esc(row.get('name', '')), 'Skipped' if row.get('skipTurnPreparation') else 'Ahead',
                                 esc(post.get('frames', '')), number(render.get('median')), number(render.get('p95')),
                                 number(render.get('max')), number(interval.get('max')),
                                 esc(fall.get('demandSpriteCreates', '')), esc(fall.get('demandGeometryMisses', '')),
                                 esc(raw.get('preparationFrames', '')), number(raw.get('maximumPreparationBatchMs'))])
        natural_table = table(['Actual natural row','Preparation','Post-command frames','Render median ms','Render p95 ms','Render max ms','Interval max ms','Fall demand sprites','Fall geometry misses','Worker frames','Max worker batch ms'], natural_rows)
        pair_rows = []
        for row in analysis.get('naturalPairs', []):
            changes = row.get('preparedMinusSkipped', {})
            post = changes.get('postCommand', {})
            pair_rows.append([esc(row.get('family', '')), esc(row.get('count', '')), esc(row.get('repeat', '')),
                              number(post.get('renderMs', {}).get('median')), number(post.get('renderMs', {}).get('p95')),
                              number(post.get('renderMs', {}).get('max')), number(post.get('intervalMs', {}).get('max')),
                              number(changes.get('powerFall', {}).get('renderMs', {}).get('median')),
                              number(changes.get('latePowerFall2440To2620ms', {}).get('renderMs', {}).get('median'))])
        natural_pair_table = table(['Family','Obstacle count','Repeat','Post Render median delta ms','Post Render p95 delta ms','Post Render max delta ms','Interval max delta ms','Fall Render median delta ms','Late-window Render median delta ms'], pair_rows)
        frozen_rows = []
        for row in analysis.get('frozenRows', []):
            for name, metric in row.get('metrics', {}).items():
                old, new = metric.get('control76Sampling', {}), metric.get('refined77Sampling', {})
                frozen_rows.append([esc(row.get('name', '')), number(row.get('age')), esc(name),
                                    number(old.get('median')), number(new.get('median')), number(metric.get('differenceOfMedians')),
                                    number(old.get('p95')), number(new.get('p95')), number(old.get('max')), number(new.get('max')),
                                    esc(metric.get('currentSlowerPairs', '')) + '/' + esc(len(metric.get('pairedDifferences', [])))])
        frozen_table = table(['Frozen fixture','Actual age s','Measured owner','76 median ms','77 median ms','Median difference ms','76 p95 ms','77 p95 ms','76 max ms','77 max ms','77 slower pairs'], frozen_rows)
        extremes_table = table(['Observed scope-specific maximum','Milliseconds'],
                               [[esc(key), number(value)] for key, value in analysis.get('observedPerformanceExtremes', {}).items()
                                if isinstance(value, (int, float)) and not isinstance(value, bool)])
        broader = analysis.get('broaderCurrentQA', {})
        if broader:
            broader_tables = '<h3>Separate eight-phase Fluidity run</h3>' + table(
                ['Phase','Command ms','Frame p95 ms','Largest interval ms','Frames above50ms'],
                [[esc(r.get('name', '')), number(r.get('commandMs')), number(r.get('p95Ms')),
                  number(r.get('worstMs')), esc(r.get('over50ms', ''))] for r in broader.get('fluidityPhases', [])])
            ordinary = []
            for r in broader.get('ordinaryCascadeRows', []):
                fps = r.get('targetFps')
                budget = 1000 / fps if isinstance(fps, (int, float)) and fps > 0 else None
                largest = r.get('maxIntervalMs')
                ratio = largest / budget if budget and isinstance(largest, (int, float)) else None
                ordinary.append([esc(r.get('name', '')), esc(fps), number(budget), number(r.get('commandMs')),
                                 number(r.get('modelMs')), number(r.get('acceptMs')), number(largest), number(ratio)])
            broader_tables += '<h3>Separate ordinary cadence and commands</h3><p>Intervals are compared with each requested frame-rate budget. Intentional15fps pacing must not be read as a60fps stall. Model and Accept are nested command components.</p>' + table(
                ['Case','Target fps','Budget ms','Command ms','Model ms','Accept ms','Largest interval ms','Interval/budget'], ordinary)
            broader_tables += '<h3>Separate ordinary density runs</h3>' + table(
                ['Family','Turns','Post Render median ms','Post Render p95 ms','Post Render max ms','Interval max ms','Demand sprites','Geometry misses'],
                [[esc(r.get('family', '')), esc(len(r.get('rows', []))), number(r.get('postCommand', {}).get('renderMs', {}).get('median')),
                  number(r.get('postCommand', {}).get('renderMs', {}).get('p95')), number(r.get('postCommand', {}).get('renderMs', {}).get('max')),
                  number(r.get('postCommand', {}).get('intervalMs', {}).get('max')), esc(r.get('postCommand', {}).get('demandSpriteCreates', '')),
                  esc(r.get('postCommand', {}).get('demandGeometryMisses', ''))] for r in broader.get('density', [])])
        for key, value in analysis.items():
            if key not in {'artifactSHA256', 'externalEvidenceSHA256'}:
                measured += details(key, value)
    else:
        measured = '<p class="pending">Current source/APK-bound performance analysis is pending. No speedup or stall-resolution verdict is inferred.</p>'
    if not isinstance(gates, list):
        gates = [gates]
    gates_html = '<ul>' + ''.join(f'<li>{esc(g)}</li>' for g in gates) + '</ul>' if gates else '<p class="pending">Final measured gates are pending; whole-game fluidity is not certified.</p>'

    visual = reviews.get('Visual_Review.json', {})
    movies = ['Android/Cascade/visual/HR_NaturalCascade.mp4'] + [f'ContinuationVisual/L{level}/visual/HR_NaturalCascade.mp4' for level in [14, 31, 33]]
    movies += sorted(name for name in inspected if name.startswith(('PowerFall77/', 'PowerFall/')) and name.endswith('.mp4'))
    movie_html = ''.join(figure(name) for name in dict.fromkeys(movies))
    sheet_paths = sorted(name for name in inspected if name.endswith('.png') and '/Frames/' not in name
                         and (name.startswith(('RegressionVisual/', 'TimingVisual/', 'PowerFallVisual/'))
                              or '/Artifacts/EffectBatch/Native/' in name))
    full_paths = visual.get('parentInspection', {}).get('regressionFullOriginals', [])
    sheet_html = ''.join(figure(name) for name in dict.fromkeys(sheet_paths + full_paths))
    review_html = ''.join(details(name, {k: v for k, v in report.items() if k not in {'artifactSHA256', 'externalEvidenceSHA256'}})
                          for name, report in reviews.items())
    if sampling:
        review_html += details('Complete native sampling proof, including every slower CPU pair', sampling)
    if preparation:
        review_html += details('Complete native preparation replay and lifecycle proof', preparation)

    css = 'body{margin:24px;background:#10283c;color:#fff6dc;font:16px system-ui;line-height:1.5}main{max-width:1400px;margin:auto}a{color:#8fdaff}.pending{color:#ead08d}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;margin:16px 0}th,td{border:1px solid #5f7685;padding:8px;text-align:left}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}figure{margin:0;background:#193b54;border:1px solid #bb9b52;border-radius:10px;padding:12px}small{display:block;font-weight:normal}img,video{display:block;width:100%;max-height:720px;object-fit:contain}figcaption{margin-bottom:10px;overflow-wrap:anywhere}pre{font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere;background:#193b54;padding:12px}summary{cursor:pointer;color:#8fdaff}details{margin:12px 0}code{overflow-wrap:anywhere}'
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Checkpoint77 power-fall evidence</title><style>{css}</style><main>
<h1>Power-fall sampling and resource preparation</h1><p><strong>{esc(status)}</strong></p>
<p>Checkpoint77 targets repeated fall/debris work and native sprite/quad creation during power playback. Approved art, trajectories, mesh geometry, masks, model outcomes, power protection and clocks remain verification requirements. Main LDPlayer retains deployment64; final-source QA and physical-device acceptance have separate scopes.</p>
<p>APK <code>{esc(apk or 'pending')}</code><br>Frozen source <code>{esc(source or 'pending')}</code></p>
<p>{link('Collected77 results','Summary.json')} · {link('Performance analysis','Performance_Analysis.json')} · {link('Actual visual inspection','Visual_Review.json')} · {link('Original-PTS inspection','Timing_Visual_Notes.json')} · {link('Frozen inputs','Source_SHA256.json')} · {link('Preserved76 baseline','Baseline76.json')} · <a href="../Gameplay76/Comparison.html">Archived76 review</a></p>
<h2>Evidence boundaries and remaining gates</h2>
<ul><li>Native Editor sampling uses independently compiled archived76 code and exact ordered draw fields; preparation replays original recorded clocks and uploaded meshes. These are not Android frame-pacing or GPU-completion measurements.</li>
<li>Accepted-turn preparation is opportunistic. Its count limit and elapsed-time check are soft batch boundaries: one native creation operation may exceed the time target. Work runs outside Render and must be assessed with its own batch timestamps and full frame intervals.</li>
<li>Preparation keeps ordinary residency and evictable working-set limits. First-use demand, retries, eviction and repeated atlas preparation remain relevant; a passing targeted replay does not establish miss-free performance for every combination.</li>
<li>Same-APK controls, archived76 comparisons and fresh recorded visual observations are distinct. All slower/negative pairs remain available below. No fresh Match Villains parity, sustained frame rate, all-feature completeness, long-session or physical-device claim is inferred.</li></ul>
{gates_html}
<h2>Native sampler controls</h2>{sampling_table}<p>Each value above measures a complete batch of the listed poses. Native warmed CPU gains alone do not establish device latency or whole-turn improvement; the complete raw pairs and exact proof remain linked.</p>
<h2>Native original-clock resource replay</h2>{prep_table}<p>{link('Sampler proof','Native/PowerFallSampling.json')} · {link('Resource replay/lifecycle proof','Native/PowerFallPreparation.json')} · {link('Effect geometry/pixel proof','Native/EffectBatchChecks.json')}</p>
<h2>Same-APK natural preparation controls</h2><p>Fresh-bank natural turns vary only ahead-of-time preparation, with balanced branch order. The table includes every primary row. Post-command Render starts after command completion; its reported frame interval can still include work preceding that Render. Raw command-tail and preparation-overlap attribution remain in the full analysis.</p>{natural_table}
<p>Signed differences below are prepared minus skipped. Positive values and slower outcomes remain visible. Separately played natural turns are not aligned identical-frame CPU controls.</p>{natural_pair_table}
<h2>Same-bank frozen-pose sampler controls</h2><p>Each pair invokes actual Update/Render twice in one Unity frame at the same warmed powerFall pose. Only the checkpoint76/current sampler switch varies. All measured owners and slower-pair counts remain below; nested owners must not be added as independent costs. These frozen calls do not measure natural pacing, touch latency or GPU completion.</p>{frozen_table}
<h2>Broader current QA limits</h2><p>These ordinary and Fluidity runs are separate from the targeted natural/frozen experiments. Their remaining command and interval costs must not be hidden by a faster isolated sampler or a prepared resource window.</p>{broader_tables or '<p class="pending">Current bound broader QA measurements are pending.</p>'}
<h2>Current measured maxima and complete analysis</h2>{extremes_table}<p>Every analysis field is retained, including outliers, slower branches, instrumentation costs and open acceptance gates. Missing or mismatched analysis remains pending.</p>{measured}
<h2>Actual reviewed current media</h2><p>Only artifacts whose file hashes match a current source/APK-bound inspection are embedded. No uninspected or archived image is relabelled as current.</p><div class="grid">{movie_html or '<p class="pending">Current reviewed movies are pending.</p>'}</div>
<details><summary>Reviewed sheets and listed full originals</summary><div class="grid">{sheet_html or '<p class="pending">Current actual image inspection is pending.</p>'}</div></details>
<h2>Exact inspection scope and native proof details</h2>{review_html or '<p class="pending">Current review notes and source-bound native proof are pending.</p>'}
<h2>Current native runs</h2>{table(['Suite','Checks','Status','Source binding'],native_rows)}
<p>{link('Android full regression','Android/Regression/Regression.json')} · {link('Live power idle traces','Android/Regression/M70_Device.json')} · {link('Package checks','APK_Artifact.json')} · {link('Source changes','Source_Delta.json')}</p>
<p>This local gallery presents evidence and never publishes approval or changes runtime/device state.</p></main></html>'''
    (out / 'Comparison.html').write_text(page, 'utf-8')
    print(json.dumps({'gallery': str(out / 'Comparison.html'), 'summaryBound': summary_bound,
                      'analysisBound': analysis_bound, 'nativeBound': len(native),
                      'currentReviewedArtifacts': len(inspected), 'reviewedMovies': movie_html.count('<video ')}))


if __name__ == '__main__':
    main()
