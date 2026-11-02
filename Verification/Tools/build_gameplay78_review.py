"""Build a local checkpoint78 review from bound artifacts; never grant approval."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / 'Verification/Evidence/Gameplay78'


def read(path):
    try:
        return json.loads(path.read_text('utf-8-sig')) if path.is_file() else {}
    except (ValueError, OSError):
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
    head = ''.join(f'<th>{esc(x)}</th>' for x in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{x}</td>' for x in row) + '</tr>' for row in rows)
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def details(label, value):
    return f'<details><summary>{esc(label)}</summary><pre>{esc(json.dumps(value, indent=2))}</pre></details>'


def build(out):
    out = Path(out).resolve()
    if not out.is_relative_to((ROOT / 'Verification/Evidence').resolve()):
        raise ValueError('Review output must stay within Verification/Evidence')
    out.mkdir(parents=True, exist_ok=True)

    def local(name):
        if not isinstance(name, str):
            return None
        path = (out / name).resolve()
        return path if path.is_relative_to(out) and path.is_file() else None

    def link(label, name):
        return f'<a href="{esc(name)}">{esc(label)}</a>' if local(name) else f'<span class="pending">{esc(label)} (pending)</span>'

    frozen = read(out / 'Source_SHA256.json')
    artifact = read(out / 'APK_Artifact.json')
    summary = read(out / 'Summary.json')
    source = sha(out / 'Source_SHA256.json') if frozen else ''
    apk = artifact.get('sha256', '')

    def bound(report):
        return bool(source and apk and report.get('source_sha256') == source and report.get('apk_sha256') == apk
                    and report.get('source_checkpoint', 78) == 78 and report.get('sourceCheckpoint', 78) == 78)

    def maps_valid(report):
        own = report.get('artifactSHA256', {})
        if not own or not all(local(name) and sha(local(name)) == digest for name, digest in own.items()):
            return False
        for name, digest in report.get('externalEvidenceSHA256', {}).items():
            path = (ROOT / name).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file() or sha(path) != digest:
                return False
        return True

    summary_bound = (bound(summary) and summary.get('source_checkpoint') == 78
                     and summary.get('status') == 'PASS_TARGETED_EXECUTION78_WITH_REMAINING_PERFORMANCE_GATES'
                     and summary.get('evidence_sha256', {}).get('Source_SHA256.json') == source
                     and summary.get('evidence_sha256', {}).get('APK_Artifact.json') == (sha(out / 'APK_Artifact.json') if artifact else ''))
    analysis = read(out / 'Execution_Analysis.json')
    analysis_bound = (bound(analysis) and analysis.get('status') == 'ANALYZED_EXECUTION78_WITH_REMAINING_GATES'
                      and maps_valid(analysis))
    status = summary['status'] if summary_bound else 'PENDING: current native/build/device/visual verification'

    reviews, inspected = {}, {}
    for name in ['Visual_Review.json', 'Timing_Visual_Notes.json', 'RegressionVisual/Power_Tool_Review.json']:
        report = read(out / name)
        if bound(report) and str(report.get('status', '')).startswith('REVIEWED') and maps_valid(report):
            reviews[name] = report
            inspected.update({path: name for path in report['artifactSHA256']})

    def figure(name, caption=None):
        if name not in inspected or not local(name):
            return ''
        if Path(name).suffix.lower() == '.mp4':
            media = f'<video controls preload="none" src="{esc(name)}"></video>'
        elif Path(name).suffix.lower() == '.png':
            media = f'<a href="{esc(name)}"><img loading="lazy" src="{esc(name)}" alt="{esc(caption or name)}"></a>'
        else:
            return ''
        return f'<figure><figcaption>{esc(caption or name)}<small>Actual inspection bound by {esc(inspected[name])}.</small></figcaption>{media}</figure>'

    native, native_rows = {}, []
    for path in sorted((out / 'Native').glob('*.json')):
        if path.stem.endswith('_Process'):
            continue
        report = read(path)
        if not str(report.get('status', '')).startswith(('PASS_', 'FAIL_')):
            continue
        process = read(path.with_name(path.stem + '_Process.json'))
        manifest = local(process.get('sourceManifest'))
        current = bool(manifest and frozen and process.get('sourceSHA256') == sha(manifest)
                       and read(manifest).get('files') == frozen.get('files') and process.get('exitCode') == 0
                       and not process.get('timedOut') and str(process.get('version', '')).startswith('2022.3.62f3')
                       and str(report['status']).startswith('PASS'))
        checks = report.get('checks', 0)
        checks = len(checks) if isinstance(checks, list) else checks
        native_rows.append([link(path.stem, 'Native/' + path.name), esc(checks), esc(report['status']),
                            'Current frozen source' if current else 'Pending source binding'])
        if current:
            native[path.stem] = report

    model = native.get('ModelWork78', {})
    model_rows = []
    for row in model.get('timings', []):
        model_rows.append([esc(row['name']), number(row['controlMedianMs']), number(row['currentMedianMs']),
                           number(row['currentMedianMs'] - row['controlMedianMs']), number(row['controlMaxMs']),
                           number(row['currentMaxMs']), f"{row['slowerPairs']}/{len(row['pairs'])}"])
    model_table = table(['Native model fixture', '77 median ms', '78 median ms', '78−77 ms', '77 max ms', '78 max ms', '78 slower pairs'], model_rows)

    resource_rows = []
    for row in native.get('CommandPreparation78', {}).get('benchmarks', []):
        resource_rows.append([esc(row['name']), esc(row['scenario']), esc(row['phases']),
                              esc(row['legacyWalkerCalls']), esc(row['currentWalkerCalls']),
                              number(row['legacyMedianMs']), number(row['currentMedianMs']),
                              number(row['currentMedianMs'] - row['legacyMedianMs'])])
    resource_table = table(['Native fixture', 'Complete workload', 'Phases', '77 walker calls', '78 walker calls',
                            '77 median ms', '78 median ms', '78−77 ms'], resource_rows)

    dense = native.get('DenseSubmission', {})
    dense_rows = []
    for row in dense.get('timings', []):
        dense_rows.append([esc(row['name']), number(row['archivedFrameMedianMs']), number(row['controlFrameMedianMs']),
                           number(row['arrayFrameMedianMs']), number(row['arrayFrameMedianMs'] - row['archivedFrameMedianMs']),
                           number(row['arrayFrameP95Ms']), f"{row['currentSlowerPairs']}/{row['pairs']}",
                           f"{row['controlSlowerPairs']}/{row['pairs']}"])
    dense_table = table(['Native submission pose', 'Independent77 median ms', 'Same-APK77 median ms', '78 array median ms',
                        '78−independent77 ms', '78 p95 ms', '78 slower vs independent77', '78 slower vs same-APK77'], dense_rows)

    execution = read(out / 'Execution/Installation.json')
    execution_bound = bool(analysis_bound and execution.get('apk_sha256') == apk
                           and execution.get('installed_apk_sha256') == apk
                           and execution.get('status') == 'PASS_EXECUTION78_DEVICE_AUDIT'
                           and execution.get('data_unchanged') is True
                           and analysis['artifactSHA256'].get('Execution/Installation.json') == sha(out / 'Execution/Installation.json')
                           and analysis['artifactSHA256'].get('Execution/Report.json') == (sha(out / 'Execution/Report.json') if local('Execution/Report.json') else ''))
    device = execution.get('validated', {}) if execution_bound else {}

    def device_pairs(rows, label):
        return table([label, 'Control77 median ms', 'Current78 median ms', '78−77 ms', 'Slower current pairs'],
                     [[esc(r['name']), number(r['controlMedianMs']), number(r['currentMedianMs']),
                       number(r['currentMedianMs'] - r['controlMedianMs']),
                       f"{r['slowerCurrentPairs']}/{len(r['pairs'])}"] for r in rows])

    device_model = device_pairs(device.get('model', []), 'Android pure model fixture')
    device_frozen = device_pairs(device.get('frozenRender', []), 'Android frozen actual Render fixture')
    device_resource_rows = []
    for row in device.get('resource', []):
        for name in ['initial', 'remainingPhaseTraversal', 'initialPlusTraversal']:
            value = row[name]
            device_resource_rows.append([esc(row['name']), esc(name), esc(row['phases']), number(value['controlMedianMs']),
                                         number(value['currentMedianMs']), number(value['currentMedianMs'] - value['controlMedianMs']),
                                         f"{value['slowerCurrentPairs']}/{len(value['pairs'])}"])
    device_resource = table(['Android fixture', 'Complete workload', 'Phases', 'Control77 median ms', 'Current78 median ms',
                             '78−77 ms', 'Slower current pairs'], device_resource_rows)
    natural_rows = [[esc(r['name']), 'Combined77' if r['checkpoint77'] else 'Current78', esc(r['frames']), number(r['modelMs']),
                     number(r['acceptMs']), number(r['commandMs']), number(r['maximumRenderMs']), number(r['maximumIntervalMs'])]
                    for r in device.get('natural', [])]
    device_natural = table(['Natural Android row', 'Branch', 'Frames', 'Model ms', 'Accept ms', 'Command ms', 'Max observed Render ms',
                            'Max observed interval ms'], natural_rows)

    gates = analysis.get('remainingGates', []) if analysis_bound else []
    gate_html = ''.join(f'<li>{esc(g if isinstance(g, str) else json.dumps(g))}</li>' for g in gates)
    review_html = ''.join(details(name, {k: v for k, v in report.items() if k not in ['artifactSHA256', 'externalEvidenceSHA256']})
                          for name, report in reviews.items()) or '<p class="pending">Actual current-source visual review is pending.</p>'
    movies = [('Android/Cascade/visual/HR_NaturalCascade.mp4', 'Current78 L4 natural cascade'),
              *[(f'ContinuationVisual/L{level}/visual/HR_NaturalCascade.mp4', f'Current78 L{level} continuation') for level in [14, 31, 33]]]
    movie_html = ''.join(figure(name, caption) or '<p>' + link(caption + ' — awaiting bound visual review', name) + '</p>' for name, caption in movies)
    sheet_names = sorted(name for name in inspected if name.endswith('.png') and '/Frames/' not in name
                         and (name.startswith(('RegressionVisual/', 'TimingVisual/', 'PowerFallVisual/', 'Native/DenseSubmission/Artifacts/'))))
    sheets = ''.join(figure(name) for name in sheet_names)
    raw_details = details('Current bound execution analysis — all extrema, signed/slower controls and remaining gates', analysis) if analysis_bound else '<p class="pending">Current raw analysis is pending; no speedup is inferred.</p>'
    native_details = ''.join(details(name + ' — raw samples and proof scope', native[name]) for name in ['ModelWork78', 'CommandPreparation78', 'DenseSubmission', 'PowerFallPreparation'] if name in native)
    baseline = read(out / 'Baseline77.json')
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Heart of the Rain — Checkpoint78</title><style>
:root{{color-scheme:dark}}body{{margin:0;background:#081b31;color:#e9f1f8;font:16px/1.55 system-ui,sans-serif}}main{{max-width:1440px;margin:auto;padding:28px}}h1,h2{{color:#f4d58b}}h2{{margin-top:36px}}a{{color:#8dd7ff}}code{{overflow-wrap:anywhere}}.pending{{color:#ffda8c}}.scope{{border-left:4px solid #dcb75d;padding:12px 20px;background:#102b45}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:8px 10px;border:1px solid #31506a;text-align:left}}th{{background:#153750}}figure{{margin:20px 0;background:#102b45;padding:14px}}figure img{{max-width:100%;height:auto}}video{{max-width:100%;max-height:760px;width:100%;background:#000}}figcaption{{margin-bottom:10px;overflow-wrap:anywhere}}small{{display:block;color:#b6c8d6}}details{{margin:14px 0;border:1px solid #31506a;padding:10px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}.gallery{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,430px),1fr));gap:16px}}
</style><main><h1>Checkpoint78 — commands, resource planning and dense submission</h1>
<p class="scope"><strong>{esc(status)}</strong><br>Native Editor CPU, Android pure commands, natural playback and frozen same-pose Render controls are separate experiments. Every slower pair remains visible. This page grants no approval and makes no sustained-frame-rate, physical-device, universal speedup or fresh Match Villains parity claim.</p>
<p>Source: <code>{esc(source or 'pending')}</code><br>APK: <code>{esc(apk or 'pending')}</code><br>Frozen inputs: {esc(len(frozen.get('files', {})) or 'pending')}; native source-bound suites shown: {len(native)}. QA only; main deployment64 is preserved.</p>
<p>{link('Strict summary', 'Summary.json')} · {link('Current source manifest', 'Source_SHA256.json')} · {link('Execution analysis', 'Execution_Analysis.json')} · {link('Raw Android execution report', 'Execution/Report.json')} · {link('Preserved77 baseline', 'Baseline77.json')}</p>
<h2>Remaining measured limits</h2><ul>{gate_html or '<li class="pending">Awaiting bound current analysis; historical spikes are not relabelled current.</li>'}</ul>
<p>Preparation uses a cooperative budget checked after native work. First-use/high-water allocation, cache eviction and long-session churn retain demand fallbacks. Completed GC counters do not measure GC duration. Natural frame intervals can include prior commands, preparation, engine and host scheduling; pure benchmark stalls are not gameplay pacing.</p>
<h2>Android pure model commands</h2>{device_model}
<h2>Android resource construction and full traversal</h2><p>Initial, remaining phases and complete initial-plus-traversal retain every recorded sample. These workloads exclude Ready, loading and callbacks.</p>{device_resource}
<h2>Android frozen same-pose actual Render</h2><p>Only effect submission switches. The same bank, frozen clock/age, draw payload and uploaded geometry/bindings must agree. These warmed calls are separate from natural frame pacing.</p>{device_frozen}
<h2>Natural combined-control playback</h2><p>Combined77 and current78 turns use fresh banks, two untimed warmups and AB/BA ordering. Command-frame prior Render remains distinct from the command tail. Extrema here include the complete captured row; detailed attribution remains in raw analysis.</p>{device_natural}
<h2>Native model proof and CPU</h2><p>Exact archived77 helper bodies compare350 authored turns,70 actual power pairs and110 planner cases; snapshot ownership, mutations and invalid-state guard order are tested. These medians are native Editor CPU, not Android.</p>{model_table}
<h2>Native resource dependency proof and CPU</h2>{resource_table}
<h2>Native dense submission proof and CPU</h2><p>Independent archived77 and same-APK77 controls compare nine actual poses,135 upload states and strict camera pixels. Active vertex/index prefixes, UVs, colors, order, texture/material bindings and depth are preserved. Development controls retain both storage modes; no allocation-saving claim follows.</p>{dense_table}
<h2>All source-bound native suites</h2>{table(['Suite','Checks','Reported status','Source scope'], native_rows)}
<h2>Actual current visual review</h2>{review_html}<div class="gallery">{movie_html}</div><div class="gallery">{sheets}</div>
<h2>Complete measurements and proof scopes</h2>{raw_details}{native_details}{details('Preserved checkpoint77 baseline identity', baseline)}
<p>Current-source images are shown only when a bound actual-review note lists their exact hashes. Captured but unreviewed movies remain labelled pending. Archived art/control versions retain their explicit labels.</p></main></html>'''
    target = out / 'Comparison.html'
    target.write_text(page, encoding='utf-8')
    result = {'path': str(target), 'summaryBound': bool(summary_bound), 'analysisBound': bool(analysis_bound),
              'executionBound': bool(execution_bound), 'nativeSourceBound': len(native),
              'reviewNotesBound': len(reviews), 'reviewedMedia': len(sheet_names) + sum(name in inspected for name, _ in movies)}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    print(json.dumps(build(parser.parse_args().out), indent=2))
