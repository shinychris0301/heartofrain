"""Build the evidence gallery. Never grants visual approval or a test pass."""
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/Gameplay72'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}

def figure(label,path,video=False):
    label=html.escape(label)
    media=f'<video controls preload="none" src="{path}"></video>' if video else f'<a href="{path}"><img loading="lazy" src="{path}" alt="{label}"></a>'
    return f'<figure><figcaption>{label}</figcaption>{media}</figure>'

def main():
    native=[]
    for name in ['MixedSwapChecks','ResourceScan','ProfileChecks','Checks','TimingChecks','IndividualFallChecks','FallChecks','SwapChecks','M70R2Checks','M70Checks','GameplayAuditChecks','GameplayPerfChecks','ModelPerfChecks','EffectBatchChecks','WarmupChecks','PlaySmoke','HomeLivesUI','PlaybackOnset']:
        r=read(OUT/'Native'/(name+'.json'))
        if not r:
            continue
        count=r.get('checks',r.get('passed',''))
        if isinstance(count,list):
            count=len(count)
        native.append(f'<tr><td><a href="Native/{name}.json">{name}</a></td><td>{html.escape(str(count))}</td><td>{html.escape(r.get("status",""))}</td></tr>')
    summary=read(OUT/'Summary.json')
    status=summary.get('status','Review in progress; use linked reports for current scope')
    timing=read(OUT/'Timing_Analysis.json')
    phase_rows=''.join(f'<tr><td>{html.escape(row["name"])}</td><td>{row["p95Ms"]:.1f}</td><td>{row["worstMs"]:.1f}</td><td>{row["commandMs"]:.1f}</td></tr>' for row in timing.get('fluidity',[]))
    density_rows=[]
    for family,rows in timing.get('density',{}).items():
        for count in [1,8,16,32,45]:
            pair=[row for row in rows if row['name'].startswith(family+'_'+str(count)+'_')]
            density_rows.append(f'<tr><td>{family}</td><td>{count}</td><td>{max(row["peakDraws"] for row in pair)}</td><td>{max(row["burstP95IntervalMs"] for row in pair):.1f}</td><td>{max(row["burstP95RenderMs"] for row in pair):.1f}</td></tr>')
    videos=''.join([
        figure('Historical previous rule: the earned Rocket chains (older APK; not a timing baseline)','../GameplayAudit/Touch/MixedChain.mp4',True),
        figure('Current mixed Rocket swap: source fires, reward survives','Android/Touch/MixedChain.mp4',True),
        figure('Current match creates a Bomb','Android/Touch/MixedBomb.mp4',True),
        figure('Current match creates an Orb','Android/Touch/MixedOrb.mp4',True),
        figure('Archived Match Villains: natural swap and refill','../CascadeResponsiveness/Reference/MV_NaturalMatch.mp4',True),
        figure('Current unaccelerated six-match cascade','Android/Cascade/visual/HR_NaturalCascade.mp4',True),
    ])
    images=''.join([
        figure('Current mixed swap: reward remains after the source action','Android/Touch/MixedH_After.png'),
        figure('Exact 900 coins: full-life refill is available','Android/Regression/LifeRefill_Exactly900.png'),
        figure('After the refill: zero coins, five lives','Android/Regression/LifeRefill_Full_After900.png'),
        figure('899 coins: full-life refill is unavailable','Android/Regression/LifeRefill_Below900.png'),
    ])
    details=''.join(figure(label,path) for label,path in [
        ('Reference accepted swap: original video timestamps','ReferenceAnalysis/Natural_Swap_Detail.png'),
        ('Reference next-match reaction after contact','ReferenceAnalysis/NaturalCascade_Reaction_Detail.png'),
        ('Reference one-cell fall overlapping obstacle debris','ReferenceAnalysis/Obstacle_OneCell_Detail.png'),
        ('Reference Seeker flight overlapping refill','ReferenceAnalysis/Seeker_Refill_Detail.png'),
        ('Reference Bomb and Rocket effects overlapping refill','ReferenceAnalysis/BombRocket_Overlap_Detail.png'),
        ('Current local red match waits for unrelated refill: confirmed remaining gap','TimingVisual/Local_Red_Row_Contact.png'),
        ('Current accepted swap: original video timestamps','TimingVisual/Swap_Detail.png'),
    ])
    css='body{margin:24px;background:#10283c;color:#fff6dc;font:16px system-ui;line-height:1.55}main{max-width:1500px;margin:auto}a{color:#8fdaff}p{max-width:1100px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}figure{margin:0;padding:12px;background:#193b54;border:1px solid #bb9b52;border-radius:12px}figcaption{min-height:3em;font-weight:600}img,video{display:block;width:100%;height:auto;max-height:760px;object-fit:contain}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{padding:10px;border:1px solid #587184;text-align:left}.wide img{max-height:none}code{overflow-wrap:anywhere}small{color:#d2dae0}'
    text=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gameplay power protection and timing review</title><style>{css}</style><main>
<h1>Gameplay: protected rewards, timing and life refill</h1><p><strong>{html.escape(status)}</strong></p>
<p>A mixed gem/power swap still triggers the original power. The newly earned reward survives that originating wave, including its existing chained powers; later actions can activate it normally. Full-life refill at zero lives now costs <strong>900 coins</strong>. The dependency scan during effect preparation was optimized with exact resource/order parity.</p>
<p>The first rendered pose now owns animation onset: model solving and resource preparation cannot consume the visible swap before it starts. Native renderer tests preserve the full120ms swap after deliberate200ms stalls, without adding pauses to later gravity or cascades.</p>
<p><strong>Confirmed remaining gameplay defect:</strong> in the reviewed natural cascade, a locally aligned red match waits505-576ms from contact before reacting while unrelated refill finishes. Even after landing deformation stops, the row waits405-474ms. This is distinct from the repaired onset clock and from zero extra delay after the board's final global contact. <a href="Timing_Visual_Notes.json">Bounded visible evidence and required scheduling repair</a>.</p>
<p>Functional success does not establish hitch-free play. Unaccelerated emulator measurements separate synchronous command/acceptance work from animation playback and renderer updates. Cold command spikes and occasional long render frames remain recorded performance gates; the preceding-APK timing probe failed startup, so no whole-game Android before/after speedup is claimed. The controlled native dependency microbenchmark measures a smaller CPU operation only.</p>
<p>QA LDPlayer is the review target. Main deployment64 remains older. Coin IAP and production continuation authority remain unavailable. The linked regression uses accelerated playback and programmatic UI actions; the eight gesture clips use actual Android swipes, while separate timing runs use unaccelerated playback without video readback.</p>
<p><a href="../../../Codex_Handoff/Documentation/72_GAMEPLAY_POWER_PROTECTION_AND_FLOW_REVIEW.md">Detailed review and changed files</a> | <a href="Summary.json">Collected final results</a> | <a href="Timing_Analysis.json">Current timing analysis</a> | <a href="Visual_Review.json">Reviewed artifact hashes</a> | <a href="Power_Visual_Notes.json">Independent power visual review</a> | <a href="Android/Regression/Regression.json">Full Android regression</a></p>
<h2>Power behavior and native life-refill UI</h2><p>The historical clip illustrates the superseded rule, not a comparable performance baseline. Current clips include recording and input-dispatch overhead. MixedChain is the fixture name; the four pre-existing Rocket-to-Bomb chain controls are native model tests, rather than an extra Bomb in this video.</p><div class="grid">{videos}</div><div class="grid" style="margin-top:20px">{images}</div>
<h2>Step-by-step reference observations</h2><p>The installed Match Villains reached level463 but remained on its TNT Snitch loading screen after Play. These comparisons use archived actual recordings, with original dates, frame timestamps and available version evidence. <a href="Reference/Current_Attempt.json">Current capture limitation</a> | <a href="Reference_Analysis.json">Seven source clips and bounded observations</a></p>
<table><thead><tr><th>Element</th><th>Reference observation</th><th>Heart of the Rain</th></tr></thead><tbody>
<tr><td>Accepted swap</td><td>Visible flight/settle bounded at about 86-133 ms</td><td>120 ms scheduled; command processing and first-pose timing are distinct</td></tr>
<tr><td>Invalid out-and-back swap</td><td>No isolated timing claim from these clips</td><td>220 ms scheduled</td></tr>
<tr><td>One-cell fall</td><td>About 124-198 ms from original frames; occlusion limits precision</td><td>141 ms scheduled flight, with 35 ms section spacing</td></tr>
<tr><td>Following match</td><td>Observed local reaction bounded at0-80ms after contact</td><td>Confirmed remaining local delay505-576ms while unrelated refill finishes; global phase transition adds no extra barrier after the last contact</td></tr>
<tr><td>Debris and power tails</td><td>Refill continues while fragments, projectiles and other powers remain visible</td><td>Independent effects/history continue with cell-clearance and route reservations preserved</td></tr>
</tbody></table><p>Different boards, obstacle families and game rules prevent an exact physics or frame-for-frame parity claim. The archived clips do not isolate the newly requested protected mixed-swap birth; that rule is verified by this project's own controls.</p><div class="grid wide">{details}</div>
<h2>Final APK timing measurements</h2><p>Milliseconds from an unaccelerated QA run. Command includes synchronous model and acceptance work; first-pose clock protection preserves visible animation after that work. Different emulator scheduling and process/cache conditions prevent attributing the difference from BeforeOnset to one code change.</p><table><thead><tr><th>Phase</th><th>Frame p95</th><th>Worst frame</th><th>Command</th></tr></thead><tbody>{phase_rows}</tbody></table>
<p>Density bursts use an untimed warm-up and two repetitions per count. The table shows the larger p95 from those repetitions, considering frames at or above half of peak draw count. No new renderers or obstacle sprites were created in the measured turns. Zero growth does not establish zero managed allocation or cold-start performance.</p><table><thead><tr><th>Family</th><th>Destroyed</th><th>Peak draws</th><th>Burst frame p95</th><th>Burst Render p95</th></tr></thead><tbody>{''.join(density_rows)}</tbody></table>
<h2>Native verification</h2><table><thead><tr><th>Suite</th><th>Checks</th><th>Result</th></tr></thead><tbody>{''.join(native)}</tbody></table>
<p><a href="Source_SHA256.json">Frozen Unity inputs</a> | <a href="APK_Artifact.json">Final APK checks</a> | <a href="Android/Before.json">Real QA save/preference hashes before fixtures</a> | <a href="Discarded/LaunchOverlayRun/Discard_Audit.json">Discarded launch-covered run</a></p><small>Real saves are never substituted or cleared. No physical-device, production billing, audio/haptic or sustained-60-fps certification.</small></main></html>'''
    (OUT/'Comparison.html').write_text(text,encoding='utf-8')
    print('Wrote Gameplay72/Comparison.html; review state comes only from linked proof.')

if __name__=='__main__':
    main()
