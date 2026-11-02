"""Present checkpoint 75 evidence; this file never grants test/visual approval."""
import html
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Gameplay75'


def read(path):
    return json.loads(path.read_text('utf-8-sig')) if path.exists() else {}


def figure(label, path, video=False):
    media = f'<video controls preload="none" src="{path}"></video>' if video else f'<a href="{path}"><img loading="lazy" src="{path}" alt="{html.escape(label)}"></a>'
    return f'<figure><figcaption>{html.escape(label)}</figcaption>{media}</figure>'


def main():
    contract = runpy.run_path(str(Path(__file__).with_name('collect_gameplay75_results.py')), run_name='gallery_contract')
    rows = []
    for name in contract['NATIVE']:
        report = read(OUT / 'Native' / (name + '.json'))
        if report:
            count = report.get('checks', 0)
            if isinstance(count, list):
                count = len(count)
            rows.append(f'<tr><td><a href="Native/{name}.json">{name}</a></td><td>{count}</td><td>{html.escape(report["status"])}</td></tr>')
    summary = read(OUT / 'Summary.json')
    notes = read(OUT / 'Timing_Visual_Notes.json')
    match = notes.get('localMatch', {})
    bounds = match.get('contactToReactionBoundMs')
    observed = f'{bounds[0]:.0f}-{bounds[1]:.0f} ms' if bounds else 'Awaiting final original-frame inspection'
    status = html.escape(summary.get('status', 'Verification in progress; no final Android approval yet'))
    phases = read(OUT / 'Android/Fluidity/Measurement.json').get('phases', [])
    timing_rows = ''.join(f'<tr><td>{html.escape(p["name"])}</td><td>{p["p95Ms"]:.1f}</td><td>{p["worstMs"]:.1f}</td><td>{p["commandMs"]:.1f}</td></tr>' for p in phases)
    continuation = read(OUT / 'Native/LocalContinuation.json')
    continuation_rows = ''.join(f'<tr><td>{html.escape(r["name"])}</td><td>{r["checkpoint74Seconds"]:.3f} s</td><td>{r["refinedSeconds"]:.3f} s</td><td>{1000*(r["checkpoint74Seconds"]-r["refinedSeconds"]):.0f} ms</td></tr>' for r in continuation.get('rows', []) if r.get('accepted') and r.get('checkpoint74Accepted') == 0)
    snapshot = read(OUT / 'Native/ModelCommands.json')
    snapshot_rows = ''.join(f'<tr><td>{html.escape(r["name"])}</td><td>{1000*r["legacyMedianMs"]:.1f}</td><td>{1000*r["medianMs"]:.1f}</td></tr>' for r in snapshot.get('snapshotRepeated', []))
    videos = ''.join([
        figure('Verified checkpoint 74: original restricted continuation', '../Gameplay74/Android/Cascade/visual/HR_NaturalCascade.mp4', True),
        figure('Current checkpoint 75: unchanged level 4 scheduling control', 'Android/Cascade/visual/HR_NaturalCascade.mp4', True),
        figure('Current mixed-power control: source fires, earned reward survives', 'Android/Touch/MixedChain.mp4', True),
        figure('Archived actual Match Villains refill; different puzzle and capture date', '../GameplayAudit/Reference/MV_Natural_Refill.mp4', True),
    ])
    for level in [14, 31, 33]:
        for variant, label in [('control74', 'Checkpoint 74 scheduling control'), ('refined75', 'Current terminal continuation')]:
            videos += figure(f'Level {level}: {label}', f'ExtraContinuation/L{level}/{variant}/visual/HR_NaturalCascade.mp4', True)
    images = ''.join(figure(label, path) for label, path in [
        ('At 900 coins, refill is enabled', 'Android/Regression/LifeRefill_Exactly900.png'),
        ('After purchase: 0 coins and 5/5 Full', 'Android/Regression/LifeRefill_Full_After900.png'),
        ('Checkpoint 74 local-contact-to-reaction frames', '../Gameplay74/TimingVisual/Local_Red_Row_Contact.png'),
    ])
    for label, path in [('Current local reaction', 'TimingVisual/Local_Red_Row_Contact.png'),
                        ('Unrelated bodies continue through the next match', 'TimingVisual/Carry_Overlap.png'),
                        ('Affected-column landing poses', 'TimingVisual/Shared_Column_Landing.png'),
                        ('Continued and shared-column overview', 'TimingVisual/Carry_And_Shared_Column_Overview.png'),
                        ('Accepted swap intermediate poses', 'TimingVisual/Swap_Detail.png'),
                        ('Accepted swap onset, progress and completion', 'TimingVisual/Swap_Onset.png'),
                        ('Current level 4 control sequence', 'TimingVisual/Sequence.png')]:
        if (OUT / path).exists():
            images += figure(label, path)
    sheet_links = ''.join(f'<li><a href="{p.relative_to(OUT).as_posix()}">{html.escape(p.name)}</a></li>' for p in sorted((OUT / 'RegressionVisual').glob('*_0[1-9].png')))
    css = 'body{margin:24px;background:#10283c;color:#fff6dc;font:16px system-ui;line-height:1.55}main{max-width:1500px;margin:auto}a{color:#8fdaff}p{max-width:1150px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:20px}figure{margin:0;padding:12px;background:#193b54;border:1px solid #bb9b52;border-radius:12px}figcaption{font-weight:600;min-height:3em}img,video{display:block;width:100%;height:auto;max-height:760px;object-fit:contain}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{padding:10px;border:1px solid #587184;text-align:left}.wide img{max-height:none}code{overflow-wrap:anywhere}'
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gameplay responsiveness review</title><style>{css}</style><main>
<h1>Gameplay responsiveness and regression review</h1><p><strong>{status}</strong></p>
<p>Three additional natural cascades can finish their ordinary landing tails on an unchanged idle board. Levels 14, 31 and 33 save 60, 95 and 200 ms of native scheduled playback versus checkpoint 74. All flights retain their owner, and level 4 keeps its previously verified continuation. At most one safe continuation is permitted per turn; unsupported interactions retain the fallback.</p>
<p><strong>Residual delay remains.</strong> The native case waits 24 ms between local matching contact and safe phase handoff, before the short break marker. Original-frame inspection reports current contact-to-reaction at <strong>{observed}</strong>, with the checkpoint 74 fixture retained as a direct control. The guarded continuation now qualifies in four of 350 sampled commands, adding levels 14, 31 and 33. This conservative change does not certify reference parity or hitch-free gameplay.</p>
<p><strong>Command and frame stalls remain.</strong> The separately recorded refined level 31 command takes 141.808 ms and overlaps a 180.877 ms initial command/onset interval. Its playback Build span is 84.755 ms; the first swap Render is only 1.614 ms. The detailed trace localizes elapsed command/probe work without establishing an exclusive CPU cause. All three refined extra recordings have higher command spans than their paired controls despite faster local match reaction. The unrecorded default/repeated measurements and dense stone Render peak of 44.551 ms retain their separate scopes.</p>
<p>Protected mixed-swap rewards, original source actions, existing power chains, the full-life refill at 900 coins, 120 ms visible swaps, portrait layouts, approved assets and level masks remain regression requirements. Main LDPlayer retains deployment 64; QA is the rebuilt review target. Real save/preferences are guarded around every isolated device stage.</p>
<p><a href="../../../Codex_Handoff/Documentation/75_DENSE_EFFECTS_CPU_REVIEW.md">Detailed implementation and limits</a> | <a href="Summary.json">Collected results</a> | <a href="Timing_Visual_Notes.json">Original-frame timing review</a> | <a href="Timing_Analysis.json">Measured timing analysis</a> | <a href="Profile_Comparison74_75.json">All direct profiling comparisons</a> | <a href="Power_Visual_Notes.json">Power video review</a> | <a href="Visual_Review.json">Reviewed artifact hashes</a></p>
<h2>Step-by-step comparison</h2><p>Scheduled native durations, observed video bounds and accelerated functional checks are different evidence. Reference observations come from archived actual recordings of different puzzles; the preceding fresh reference attempt could not enter gameplay.</p>
<table><thead><tr><th>Element</th><th>Current app evidence</th><th>Reference observation and practical limit</th></tr></thead><tbody>
<tr><td>Accepted swap</td><td>120 ms scheduled; native rendered-pose checks retain first pose and contact boundary.</td><td>Archived visible motion about 86-133 ms. Synchronous command costs are separate from visible swap duration.</td></tr>
<tr><td>One-cell fall</td><td>About 141 ms scheduled; original route/spawn/landing clocks retained.</td><td>Archived fall about 124-198 ms. Route length, board geometry and frame sampling differ.</td></tr>
<tr><td>New local match</td><td>{observed} contact to first visible fragments in the reproduced row. Level 4 retains its checkpoint 74 scheduler; no new L4 schedule gain is claimed.</td><td>A different green-row case reacts within a conservative 0-80 ms bound. Remaining responsiveness gap is explicit; visible endpoints differ.</td></tr>
<tr><td>Refill, fragments and flying effects</td><td>Native clearance/counter controls plus actual video and 40 density turns; carried bodies keep moving through the selected next match.</td><td>Archived recordings show refill continuing during debris and Seeker flight. Exact effect timing for every family is not established.</td></tr>
<tr><td>Power creation and chain reactions</td><td>360 native protected births; six actual final-APK swipes show source firing and earned reward surviving. Existing Bomb chains pass separate native controls.</td><td>The owner's requested immunity rule is authoritative. The archived reference does not isolate every identical mixed-swap recipe.</td></tr>
<tr><td>Obstacles and campaign flow</td><td>All 50 boards, eight damage families, jar delivery, tools, supported pairs and win/loss/continuation controls pass. Selected fresh frames reviewed.</td><td>Reference footage covers selected situations; it does not certify every obstacle family, balance, audio or all rendered frames.</td></tr>
</tbody></table><h2>Additional guarded cascade cases</h2><p>Native scheduled turn duration under checkpoint 74 and 75. Same-APK videos below provide separate rendering evidence; the table does not infer visible reaction bounds from schedule saving.</p><table><thead><tr><th>Case</th><th>Checkpoint 74</th><th>Checkpoint 75</th><th>Native saving</th></tr></thead><tbody>{continuation_rows}</tbody></table><div class="grid">{videos}</div><h2>Refill and visual comparisons</h2><div class="grid wide">{images}</div>
<h2>Command and preparation work</h2><p>Snapshot sorting uses reusable private scratch while returning fresh detached objects. Playback construction reuses a turn-local immutable active-cell set and avoids temporary single-leg route lists. Effect lookups retain exact eviction ownership; batching caches texture IDs and uploads a retained active index prefix. Existing preparation and its no-dwell readiness policy are preserved. Diagnostics distinguish synchronous model/queue work, resource discovery and per-frame render stages. Remaining large frames are reported in the linked analysis; these changes do not certify hitch-free play.</p><h3>Isolated Snapshot CPU controls</h3><p>Native Editor warmed median microseconds per Snapshot, alternating control order on the same fixture. Fresh detached outputs are retained. Whole-command timings remain mixed; allocation counters were unavailable.</p><table><thead><tr><th>Fixture</th><th>Archived expression (microseconds)</th><th>Current (microseconds)</th></tr></thead><tbody>{snapshot_rows}</tbody></table><h2>Final APK emulator measurements</h2><p>Unaccelerated fixtures, separate from recording and accelerated campaign regression. Milliseconds include emulator scheduling. Command includes synchronous model/acceptance work. Different process/cache conditions prevent attributing every before/after frame change to this scheduler.</p><table><thead><tr><th>Phase</th><th>Frame p95</th><th>Worst frame</th><th>Command</th></tr></thead><tbody>{timing_rows}</tbody></table>
<p>Density measurements cover 40 warmed turns across crate, stone, gate and tile destruction at five densities. Read the linked analysis and direct checkpoint 74/75 comparison for burst measurements, all before/after rows and remaining frame/command gates. A zero renderer/sprite growth result is not proof of zero allocation.</p>
<h2>Native verification</h2><table><thead><tr><th>Suite</th><th>Checks</th><th>Result</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p>The first full 75 regression failed one old idle-animation assertion. The supplied 48-frame clips reuse the same atlas rectangle 12 frames apart, so comparing only two poses 0.40 s apart could reject a moving animation. The replacement observes intermediate live clock, logical-frame and native-rectangle changes under a bounded deadline; pause/resume checks remain. Six native alias controls and 18 frozen/stuck counterexamples accompany a fresh full regression. Gameplay animation and artwork are unchanged by this verification correction. <a href="IdleSamplingFailure/Regression.json">Original failed run</a> | <a href="IdleSamplingFailure/Correction_Delta.json">Verification-only source delta</a> | <a href="Android/Regression/M70_Device.json">Fresh live idle samples</a> | <a href="Native/FrameLookup.json">Native controls</a>.</p>
<h2>Final regression capture sheets</h2><p>Selected board, effect and flow captures are accelerated rendering/functional evidence. They do not establish actual animation duration or every-frame visual approval.</p><ul>{sheet_links}</ul>
<p><a href="Android/Regression/Regression.json">Full 50-board Android results</a> | <a href="Source_SHA256.json">Frozen inputs</a> | <a href="Source_Delta.json">Narrow source delta</a> | <a href="APK_Artifact.json">APK checks</a> | <a href="Baseline_74.json">Verified baseline binding</a> | <a href="../Gameplay72/Reference_Analysis.json">Archived reference observations and capture dates</a></p>
<p>The preceding fresh Match Villains attempt remained on its loading screen; archived actual recordings provide the bounded reference observations. Physical-device, sustained frame-rate, audio/haptic and production-service certification remain separate gates.</p></main></html>'''
    (OUT / 'Comparison.html').write_text(page, encoding='utf-8')
    print('Wrote Gameplay75/Comparison.html; approval remains defined by linked proof.')


if __name__ == '__main__':
    main()
