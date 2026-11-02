"""Present checkpoint 73 evidence; this file never grants test/visual approval."""
import html
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/LocalCascade73'


def read(path):
    return json.loads(path.read_text('utf-8-sig')) if path.exists() else {}


def figure(label, path, video=False):
    media = f'<video controls preload="none" src="{path}"></video>' if video else f'<a href="{path}"><img loading="lazy" src="{path}" alt="{html.escape(label)}"></a>'
    return f'<figure><figcaption>{html.escape(label)}</figcaption>{media}</figure>'


def main():
    contract = runpy.run_path(str(Path(__file__).with_name('collect_local_cascade73_results.py')), run_name='gallery_contract')
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
    videos = ''.join([
        figure('Verified checkpoint 72 baseline: local match waits for unrelated refill', '../Gameplay72/Android/Cascade/visual/HR_NaturalCascade.mp4', True),
        figure('Current checkpoint 73: conservative overlap, with residual local wait', 'Android/Cascade/visual/HR_NaturalCascade.mp4', True),
        figure('Current mixed-power control: source fires, earned reward survives', 'Android/Touch/MixedChain.mp4', True),
        figure('Archived actual Match Villains refill; different puzzle and capture date', '../GameplayAudit/Reference/MV_Natural_Refill.mp4', True),
    ])
    images = ''.join(figure(label, path) for label, path in [
        ('At 900 coins, refill is enabled', 'Android/Regression/LifeRefill_Exactly900.png'),
        ('After purchase: 0 coins and 5/5 Full', 'Android/Regression/LifeRefill_Full_After900.png'),
        ('Baseline local-contact-to-reaction frames', '../Gameplay72/TimingVisual/Local_Red_Row_Contact.png'),
    ])
    for label, path in [('Current local reaction', 'TimingVisual/Local_Red_Row_Contact.png'),
                        ('Unrelated bodies continue through the next match', 'TimingVisual/Carry_Overlap.png'),
                        ('Affected-column landing poses', 'TimingVisual/Closed_Column_Landing.png'),
                        ('Current natural cascade sequence', 'TimingVisual/Sequence.png')]:
        if (OUT / path).exists():
            images += figure(label, path)
    sheet_links = ''.join(f'<li><a href="{p.relative_to(OUT).as_posix()}">{html.escape(p.name)}</a></li>' for p in sorted((OUT / 'RegressionVisual').glob('*_0[1-9].png')))
    css = 'body{margin:24px;background:#10283c;color:#fff6dc;font:16px system-ui;line-height:1.55}main{max-width:1500px;margin:auto}a{color:#8fdaff}p{max-width:1150px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:20px}figure{margin:0;padding:12px;background:#193b54;border:1px solid #bb9b52;border-radius:12px}figcaption{font-weight:600;min-height:3em}img,video{display:block;width:100%;height:auto;max-height:760px;object-fit:contain}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{padding:10px;border:1px solid #587184;text-align:left}.wide img{max-height:none}code{overflow-wrap:anywhere}'
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Local cascade overlap review</title><style>{css}</style><main>
<h1>Local cascade overlap and full gameplay verification</h1><p><strong>{status}</strong></p>
<p>The restricted level 4 handoff saves 200 ms of scheduled playback by carrying six unrelated falling bodies into the next match/refill phase. Their paths, spawn clipping and landing poses remain continuous. Raw model turns, random outcomes, goals and transactions remain unchanged. At most one safe handoff is permitted per turn; interacting routes, powers and advanced cases keep the sequential fallback.</p>
<p><strong>Residual delay remains.</strong> The native case waits 245 ms between the local matching contact and safe phase handoff, before the short break marker. Original-frame inspection reports current contact-to-reaction at <strong>{observed}</strong>, versus the verified baseline 505-576 ms. Full local immediacy would require causal continuation within affected columns. This conservative change does not certify reference parity or hitch-free gameplay.</p>
<p>Protected mixed-swap rewards, original source actions, existing power chains, the full-life refill at 900 coins, 120 ms visible swaps, portrait layouts, approved assets and level masks remain regression requirements. Main LDPlayer retains deployment 64; QA is the rebuilt review target. Real save/preferences are guarded around every isolated device stage.</p>
<p><a href="../../../Codex_Handoff/Documentation/73_LOCAL_CASCADE_OVERLAP_REVIEW.md">Detailed implementation and limits</a> | <a href="Summary.json">Collected results</a> | <a href="Timing_Visual_Notes.json">Original-frame timing review</a> | <a href="Timing_Analysis.json">Measured timing analysis</a> | <a href="Power_Visual_Notes.json">Power video review</a> | <a href="Visual_Review.json">Reviewed artifact hashes</a></p>
<h2>Step-by-step comparison</h2><p>Scheduled native durations, observed video bounds and accelerated functional checks are different evidence. Reference observations come from archived actual recordings of different puzzles; a fresh reference session could not enter gameplay.</p>
<table><thead><tr><th>Element</th><th>Current app evidence</th><th>Reference observation and practical limit</th></tr></thead><tbody>
<tr><td>Accepted swap</td><td>120 ms scheduled; native rendered-pose checks retain first pose and contact boundary.</td><td>Archived visible motion about 86-133 ms. Synchronous command costs are separate from visible swap duration.</td></tr>
<tr><td>One-cell fall</td><td>About 141 ms scheduled; original route/spawn/landing clocks retained.</td><td>Archived fall about 124-198 ms. Route length, board geometry and frame sampling differ.</td></tr>
<tr><td>New local match</td><td>{observed} contact to first visible fragments in the reproduced row, versus 505-576 ms before this change.</td><td>A different green-row case reacts within a conservative 0-80 ms bound. Remaining responsiveness gap is explicit; visible endpoints differ.</td></tr>
<tr><td>Refill, fragments and flying effects</td><td>Native clearance/counter controls plus actual video and 40 density turns; carried bodies keep moving through the selected next match.</td><td>Archived recordings show refill continuing during debris and Seeker flight. Exact effect timing for every family is not established.</td></tr>
<tr><td>Power creation and chain reactions</td><td>360 native protected births; six actual final-APK swipes show source firing and earned reward surviving. Existing Bomb chains pass separate native controls.</td><td>The owner's requested immunity rule is authoritative. The archived reference does not isolate every identical mixed-swap recipe.</td></tr>
<tr><td>Obstacles and campaign flow</td><td>All 50 boards, eight damage families, jar delivery, tools, supported pairs and win/loss/continuation controls pass. Selected fresh frames reviewed.</td><td>Reference footage covers selected situations; it does not certify every obstacle family, balance, audio or all rendered frames.</td></tr>
</tbody></table><div class="grid">{videos}</div><h2>Refill and visual comparisons</h2><div class="grid wide">{images}</div>
<h2>Final APK emulator measurements</h2><p>Unaccelerated fixtures, separate from recording and accelerated campaign regression. Milliseconds include emulator scheduling. Command includes synchronous model/acceptance work. Different process/cache conditions prevent attributing every before/after frame change to this scheduler.</p><table><thead><tr><th>Phase</th><th>Frame p95</th><th>Worst frame</th><th>Command</th></tr></thead><tbody>{timing_rows}</tbody></table>
<p>Density measurements cover 40 warmed turns across crate, stone, gate and tile destruction at five densities. Read the linked analysis for burst measurements and remaining frame/command gates. A zero renderer/sprite growth result is not proof of zero allocation.</p>
<h2>Native verification</h2><table><thead><tr><th>Suite</th><th>Checks</th><th>Result</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Final regression capture sheets</h2><p>Selected board, effect and flow captures are accelerated rendering/functional evidence. They do not establish actual animation duration or every-frame visual approval.</p><ul>{sheet_links}</ul>
<p><a href="Android/Regression/Regression.json">Full 50-board Android results</a> | <a href="Source_SHA256.json">Frozen inputs</a> | <a href="Source_Delta.json">Narrow source delta</a> | <a href="APK_Artifact.json">APK checks</a> | <a href="Baseline_72.json">Verified baseline binding</a> | <a href="../Gameplay72/Reference_Analysis.json">Archived reference observations and capture dates</a></p>
<p>Fresh Match Villains gameplay was unavailable during the comparison attempt because it remained on its loading screen; archived actual recordings provide the bounded reference observations. Physical-device, sustained frame-rate, audio/haptic and production-service certification remain separate gates.</p></main></html>'''
    (OUT / 'Comparison.html').write_text(page, encoding='utf-8')
    print('Wrote LocalCascade73/Comparison.html; approval remains defined by linked proof.')


if __name__ == '__main__':
    main()
