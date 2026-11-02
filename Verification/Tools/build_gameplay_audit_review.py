"""Build a local, read-only review of existing gameplay audit evidence.

Only Comparison.html (or Comparison_Draft.html) is written. This tool never
captures media, runs a device, alters reports, or grants visual approval.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "Verification/Evidence/GameplayAudit"
MODES = {
    "MixedH": "Horizontal Rocket creation",
    "MixedV": "Vertical Rocket creation",
    "MixedBomb": "Bomb creation",
    "MixedOrb": "Rainbow Orb creation",
    "MixedSeeker": "Rain Seeker creation",
    "MixedChain": "Newborn power hit and chained",
    "ObstaclePartial": "Partial obstacle hit continues",
    "ObstacleClear": "Final obstacle clear and local refill",
}
GROUPS = [
    ("Refill and obstacle handoff", "MV_Natural_Refill", ["ObstaclePartial", "ObstacleClear"]),
    ("Matching and visible creation", "MV_FourMatch_Creation", ["MixedH", "MixedV", "MixedBomb", "MixedOrb", "MixedSeeker"]),
    ("Contact with another power", "MV_Rocket_Hits_Bomb", ["MixedChain"]),
]


def esc(value):
    return html.escape(str(value), quote=True)


def number(value, places=2):
    return f"{value:,.{places}f}" if isinstance(value, (int, float)) else "Pending"


def integer(value):
    return f"{value:,}" if isinstance(value, int) else "Pending"


def badge(status):
    value = str(status or "PENDING — report not present")
    upper = value.upper()
    kind = "pass" if upper.startswith("PASS") else "fail" if upper.startswith(("FAIL", "ERROR")) else "pending"
    return f'<span class="badge {kind}">{esc(value)}</span>'


class Review:
    def __init__(self, base):
        self.base = base.resolve()
        self.read_notes = []

    def read(self, relative):
        path = self.base / relative
        if not path.is_file():
            return None
        try:
            result = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(result, dict):
                raise ValueError("report root must be an object")
            return result
        except (OSError, ValueError) as error:
            self.read_notes.append(f"{relative}: {error}")
            return None

    def href(self, relative):
        return quote(str(relative).replace("\\", "/"), safe="/._-")

    def link(self, relative, label=None):
        if not (self.base / relative).is_file():
            return f'<span class="pending-text">{esc(label or relative)} — pending</span>'
        return f'<a href="{self.href(relative)}">{esc(label or relative)}</a>'

    def plate(self, candidates):
        for candidate in candidates:
            if not candidate:
                continue
            path = (self.base / str(candidate)).resolve()
            # A report field may select an existing local plate, never a remote URL.
            if path.is_relative_to(self.base) and path.is_file() and path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                relative = path.relative_to(self.base).as_posix()
                return f'<a href="{self.href(relative)}"><img loading="lazy" src="{self.href(relative)}" alt="{esc(path.stem)} frame sheet"></a>'
        return '<p class="pending-text">Selected frame sheet pending.</p>'

    def video(self, relative):
        if not (self.base / relative).is_file():
            return '<div class="media-pending">Video pending</div>'
        return f'<video controls playsinline preload="none" src="{self.href(relative)}">Open {self.link(relative, "video")}</video>'

    def media_groups(self, touch, visual):
        native = {case.get("mode"): case for case in (touch or {}).get("cases", []) if isinstance(case, dict)}
        reviewed = {case.get("mode"): case for case in (visual or {}).get("cases", []) if isinstance(case, dict)}
        groups = []
        for title, reference, modes in GROUPS:
            source = f"Reference/{reference}"
            left = f'''<article class="reference"><h3>Match Villains v7307</h3>
                {self.video(source + '.mp4')}
                <p>{self.link(source + '.json', 'Actual Android input/capture metadata')}</p>
                {self.plate([source + '_Sheet.png', source + '_Sequence.png'])}
                <p class="small">Different board, colors, progression and effect load. This is a sequencing reference; it does not establish an identical rule or timing curve.</p></article>'''
            right = []
            for mode in modes:
                case, review = native.get(mode, {}), reviewed.get(mode, {})
                description = f"{len(case.get('poses', [])):,} native sprite pose samples" if "poses" in case else "Native pose report pending"
                if "createdKind" in case and not mode.startswith("Obstacle"):
                    description += f"; created kind {case['createdKind']} at ({case.get('createdX', '?')}, {case.get('createdY', '?')})"
                if "chained" in case and not mode.startswith("Obstacle"):
                    description += "; chained" if case["chained"] else "; survives this source activation"
                plates = [review.get("plate"), review.get("sheet"), case.get("plate"), f"{mode}_Sequence.png", f"{mode}_Sheet.png", f"Touch/{mode}_Sequence.png", f"Touch/{mode}_Sheet.png"]
                right.append(f'''<article><h3>{esc(MODES[mode])}</h3>{badge(case.get('status'))}
                    {self.video('Touch/' + mode + '.mp4')}<p>{esc(description)}.</p>
                    <p>{self.link('Touch/' + mode + '_Report.json', 'Native input/state/pose report')} ·
                    {self.link('Touch/' + mode + '_Before.png', 'Before')} · {self.link('Touch/' + mode + '_After.png', 'After')}</p>
                    {self.plate(plates)}
                    <p class="small">Human visual review status comes from the separate review report above. A native fixture PASS alone is not visual approval.</p></article>''')
            groups.append(f'<section><h2>{esc(title)}</h2><div class="comparison">{left}<div class="native-grid">{"".join(right)}</div></div></section>')
        return "".join(groups)


def phase_table(before, after):
    old = {phase.get("name"): phase for phase in (before or {}).get("phases", [])}
    new = {phase.get("name"): phase for phase in (after or {}).get("phases", [])}
    names = list(dict.fromkeys([*old, *new]))
    if not names:
        return '<p class="pending-text">Before/after native timing reports pending.</p>'

    def severe(phase):
        count, frames = phase.get("over33ms"), phase.get("frames")
        if not isinstance(count, int) or not isinstance(frames, int):
            return "Pending"
        return f"{count:,} / {frames:,} ({count / frames * 100:.2f}%)" if frames else f"{count:,} / 0"

    rows = []
    for name in names:
        b, a = old.get(name, {}), new.get(name, {})
        cells = [esc(name.replace("_", " "))]
        for field in ("p95Ms", "worstMs"):
            cells.extend([number(b.get(field)), number(a.get(field))])
        cells.extend([severe(b), severe(a), integer(b.get("gen0Collections")), integer(a.get("gen0Collections"))])
        for field in ("commandMs", "firstPresentationMs"):
            cells.extend([number(b.get(field)), number(a.get(field))])
        rows.append("<tr>" + "".join(f"<td>{value}</td>" for value in cells) + "</tr>")
    return '''<div class="scroll"><table><caption>Unrecorded native Android Update intervals and command paths; milliseconds except count columns</caption>
        <thead><tr><th rowspan="2">Phase</th><th colspan="2">p95 interval</th><th colspan="2">Worst interval</th>
        <th colspan="2">Intervals &gt;33.34 ms / frames</th><th colspan="2">Gen0 collections</th><th colspan="2">Command CPU</th>
        <th colspan="2">StepStarted dispatch</th></tr><tr>''' + "<th>Before</th><th>After</th>" * 6 + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"


def check_count(report):
    for field in ("checks", "passed", "assertions"):
        value = report.get(field)
        if isinstance(value, int):
            return integer(value)
    return "See report"


def native_table(review, runtime):
    if not runtime:
        return '<p class="pending-text">Combined native runtime checkpoint report pending.</p>'
    rows = []
    for record in runtime.get("reports", []):
        report = record.get("report", {})
        mode = record.get("mode", "Native checkpoint")
        link = review.link(f"Native_Checkpoints/{mode}.json", mode)
        rows.append(f'<tr><td>{link}</td><td>{badge(report.get("status"))}</td><td>{check_count(report)}</td><td>{esc(report.get("utc", "Not recorded"))}</td></tr>')
    return f'<p>{badge(runtime.get("status"))} {review.link("Native_Runtime_Checks.json", "Combined native checkpoint evidence")}</p><div class="scroll"><table><thead><tr><th>Checkpoint</th><th>Reported status</th><th>Checks</th><th>UTC</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT)
    parser.add_argument("--draft", action="store_true", help="Write Comparison_Draft.html; preserve the final review page.")
    args = parser.parse_args()
    review = Review(args.evidence_root)
    if not review.base.is_dir():
        raise SystemExit(f"Evidence folder does not exist: {review.base}")
    before = review.read("Before/Measurement.json")
    after = review.read("After/Measurement.json")
    runtime = review.read("Native_Runtime_Checks.json")
    touch = review.read("Touch/Report.json")
    visual = review.read("Visual_Review.json")
    audit = review.read("Audit_Checks.json") or {}
    mixed = review.read("Mixed_Swap_Checks.json") or {}
    full_path = next((name for name in ("LDPlayer/Regression.json", "Android/Regression.json", "Android_Regression.json") if (review.base / name).is_file()), "LDPlayer/Regression.json")
    full = review.read(full_path)
    apk_hash = (touch or {}).get("apk_sha256", "Pending current-APK touch capture")
    visual_hash = (visual or {}).get("apk_sha256")
    hash_note = '<p class="fail-text">Touch and visual review APK hashes differ. Their PASS statuses do not establish one current artifact.</p>' if visual_hash and visual_hash != apk_hash else ""
    missing = [label for label, data in (("after Android timing", after), ("native checkpoints", runtime), ("actual Android touch cases", touch), ("human visual review", visual), ("full Android regression", full)) if data is None]
    pending = f'<p class="notice">Pending evidence: {esc(", ".join(missing))}. Existing report statuses below are shown unchanged.</p>' if missing else ""
    full_section = f'''<p>{badge((full or {}).get('status'))} {review.link(full_path, 'Full Android regression report')}</p>
        <p>{integer((full or {}).get('checks'))} checks; {integer((full or {}).get('boards'))} boards; {integer((full or {}).get('actions'))} programmatic actions.</p>
        <p class="small">{esc((full or {}).get('scope', 'Awaiting the current APK full-suite report. Historical full-suite passes are not borrowed.'))}</p>'''
    findings = ""
    if visual and visual.get("findings"):
        value = visual["findings"]
        values = value if isinstance(value, list) else [value]
        findings = '<details><summary>Recorded visual-review findings</summary><ul>' + "".join(f'<li>{esc(item if isinstance(item, str) else json.dumps(item, ensure_ascii=False))}</li>' for item in values) + '</ul></details>'
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Heart of the Rain — gameplay concurrency review</title><style>
        :root{color-scheme:dark}*{box-sizing:border-box}body{font:16px/1.55 system-ui,sans-serif;background:#142132;color:#f4f3ee;margin:0}main{max-width:1640px;margin:auto;padding:28px}h1,h2,h3{line-height:1.25}h1{font-size:2rem}h2{margin-top:2.3rem}h3{font-size:1.1rem}a{color:#b5e1ff}p{max-width:110ch}.small,caption{font-size:.86rem;color:#c2d0dd}.notice{background:#493e24;border-left:4px solid #e9bb62;padding:15px}.badge{display:inline-block;font-size:.76rem;line-height:1.5;overflow-wrap:anywhere;border:1px solid;padding:3px 7px;border-radius:5px}.pass{color:#b4e8cc;background:#193f37}.pending{color:#ffdda2;background:#493e24}.fail{color:#ffc7c7;background:#512e36}.pending-text{color:#ffdda2}.fail-text{color:#ffc7c7}table{border-collapse:collapse;width:100%;font-size:.86rem;margin:15px 0}th,td{text-align:left;border:1px solid #415166;padding:9px;vertical-align:top}th{background:#20344b}caption{text-align:left;margin-bottom:8px}.scroll{overflow:auto}video{display:block;width:100%;max-height:620px;background:#080d15;margin:14px 0}img{display:block;width:100%;max-height:410px;object-fit:contain;background:#080d15}.comparison{display:grid;grid-template-columns:minmax(280px,1fr) minmax(0,2fr);gap:20px;align-items:start}.native-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.native-grid article:only-child{grid-column:1/-1;max-width:700px}article{min-width:0;padding:18px;border:1px solid #415166;border-radius:8px;background:#1b2b3e}.reference{position:sticky;top:12px}.media-pending{height:180px;display:grid;place-items:center;background:#101a28;color:#ffdda2;margin:14px 0}code{overflow-wrap:anywhere}button,select{font:inherit;padding:7px;margin-right:9px}details{padding:12px 0}footer{margin:35px 0;border-top:1px solid #415166;padding-top:20px}@media(max-width:1050px){.comparison{grid-template-columns:1fr}.reference{position:static}.native-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:650px){main{padding:16px}.native-grid{grid-template-columns:1fr}h1{font-size:1.6rem}}
        </style></head><body><main>'''
    page += f'''<h1>Heart of the Rain: concurrent powers and creation</h1>
        <p>Current evidence review for missing gem/power-swap creation, heavy-combination stalls and basic-obstacle phase handoff. These local files compare native checks, timing probes and actual emulator recordings. The generator displays evidence; it does not approve a visual review.</p>
        <p>{review.link('../../../Codex_Handoff/Documentation/25_GAMEPLAY_CONCURRENCY_REVIEW.md', 'Detailed engineering review and coverage limits')} · {review.link('Native_Runtime_Checks.json', 'Native reports')} · {review.link('Touch/Report.json', 'Android fixture checks')} · {review.link('Visual_Review.json', 'Human visual review')}</p>
        {pending}{hash_note}<p><strong>Android input/state checks:</strong> {badge((touch or {}).get('status'))}<br>
        <strong>Human visual review:</strong> {badge((visual or {}).get('status'))}</p>
        <p class="small">Capture APK SHA256 as reported: <code>{esc(apk_hash)}</code>. This page is not an APK/source hash certification. Generated {esc(generated)}{' — DRAFT' if args.draft else ''}.</p>
        {findings}<h2>Confirmed repairs</h2>
        <div class="scroll"><table><thead><tr><th>Reproduced defect</th><th>Resulting behavior</th><th>Evidence boundary</th></tr></thead><tbody>
        <tr><td>The one-power swap path skipped its initial gem match.</td><td>The match recipe creates its item at the matching swap endpoint before the original power activates. Gesture-axis Rockets, one move charge and normal chain hits are preserved.</td><td>360 native recipe/source/direction/endpoint/shape cases; exact matching competitor swap not reproduced.</td></tr>
        <tr><td>A 768-sprite cache evicted frames still needed by large combinations.</td><td>A bounded 2,048-sprite working set and reusable eviction scratch storage avoid repeated warmed-sequence recreation. Sampled lookup/key work is reduced.</td><td>Native cache counters and isolated CPU benchmarks; final whole-frame Android results are shown below when available.</td></tr>
        <tr><td>A 0.16-second match cut a basic hit after 0.11 seconds; final clear expected hit + 0.24 seconds.</td><td>Partial-hit bodies continue on their presentation clock. Damaged match/refill scheduling reserves only affected obstacle cells; unaffected columns can start after the normal match beat. Goals follow the clear marker.</td><td>Native causal/state checks plus separate Android partial-hit/clear recordings and visual review.</td></tr>
        </tbody></table></div>
        <p>A newborn legitimately hit by the source power may chain in the same turn; it is not given immunity. Golden + Golden remains undefined. Level masks, budgets, artwork, portrait policy, existing individual fall routes and reward semantics are retained.</p>
        <h2>Before / after native Android timing</h2>
        <p>{review.link('Before/Measurement.json', 'Before probe')} · {review.link('After/Measurement.json', 'After probe')}</p>
        <p>Unrecorded, unaccelerated Update intervals include CPU/GPU waits, Android scheduling and emulator overhead. Video captures are separate and must not be used as the frame-budget measurement. Command CPU includes the measured command path, not only model solving.</p>
        <p>Threshold caveat: this emulator quantizes three-refresh intervals near50ms (before50.007ms; after49.976ms). The &gt;50ms count can therefore exaggerate improvement. The broader &gt;33.34ms counts are Orb/Rocket23 of497 before versus18 of528 after, and Golden/Bomb28 of463 versus1 of564. Orb/Rocket still reaches about100ms; sustained60fps is not certified.</p>
        <p><strong>The legacy field <code>firstPresentationMs</code> measures StepStarted event dispatch. It is not a first visible frame, touch-to-photon latency or synchronized video timestamp.</strong> Zero command/dispatch values in idle or celebration phases mean no measured command.</p>
        {phase_table(before, after)}
        <p class="small">Before scope: {esc((before or {}).get('scope', 'Pending'))}<br>After scope: {esc((after or {}).get('scope', 'Pending'))}</p>
        <p>Large cache churn is a confirmed contributor; remaining command-start spikes and slow frames are still material. Passing tests does not certify constant 60 fps. Native allocation counters require a working positive control; this environment reports them unavailable, so zero-byte observations are not promoted to allocation-free claims.</p>
        <h2>Actual recordings and selected source frames</h2>
        <p>Reference: installed Match Villains v7307. Ours: eight transient native fixtures driven by actual Android swipes. Different boards, colors, progression and effect load prevent an identical-board or exact FPS comparison. The exact gem/power swap completing a four-match was not reproduced in the reference; our rule repair follows the owner's request and deterministic tests. ADB dispatch and video clocks are not synchronized.</p>
        <p><label>Video speed <select id="speed"><option value="1">Normal</option><option value="0.5">Half speed</option><option value="0.25">Quarter speed</option></select></label><button type="button" id="pause">Pause all</button></p>
        {review.media_groups(touch, visual)}
        <section><h2>Native coverage and retained regressions</h2>{native_table(review, runtime)}
        <div class="scroll"><table><thead><tr><th>Area</th><th>Recorded coverage</th><th>Limit</th></tr></thead><tbody>
        <tr><td>Mixed gem/power swaps</td><td>{integer(mixed.get('checks'))} checks; {integer(mixed.get('turns'))} turns; {integer(mixed.get('chainedBirths'))} chained births.</td><td>Targeted fixtures; no new power immunity or competitor rule inference.</td></tr>
        <tr><td>Natural model play</td><td>{integer(audit.get('naturalBoards'))} board/seed runs; {integer(audit.get('naturalActions'))} natural actions, deterministic twins, goal/identity validation and fixed-point gravity.</td><td>Sampled continuations, not exhaustive human clears or arbitrary chain topology.</td></tr>
        <tr><td>Power pairs and tools</td><td>{integer(audit.get('pairCases'))} pair cases and {integer(audit.get('toolCases'))} tool cases across 50 boards.</td><td>Staged pairs and model stock checks; manual-tool rendering remains a separate unprofiled allocation hotspot.</td></tr>
        <tr><td>Rendering and UI</td><td>Authored sampler parity, M70R2 births, per-tile falling, swap orientation, native imports/shaders and connected smoke where listed.</td><td>Use each checkpoint's timestamp/scope. Prior APK reports do not certify the current APK.</td></tr>
        </tbody></table></div></section>
        <section><h2>Full current-build Android suite</h2>{full_section}</section>
        <section><h2>Remaining gates and observations</h2><ul>
        <li>Physical Android CPU/GPU, memory, thermal behavior and long-session/resume testing remain open. LDPlayer uses emulation/translation and host scheduling.</li>
        <li>Any remaining &gt;50 ms intervals, command-start delays or cold resource-loading gates require follow-up; isolated sampler/cache gains are not whole-frame guarantees.</li>
        <li>Human difficulty and complete UI/language review are distinct from programmatic fixture passes. Accelerated full-suite runs do not establish natural-speed touch responsiveness.</li>
        <li>Durable profile, inventory and idempotent attempt/reward settlement remain production work. Shop, Leaderboard, Teams and timers are demo data until real services exist; rendering their pages does not test billing or a backend.</li>
        <li>Exact competitor mechanics/timing/pixel parity is not established by these different-board recordings.</li></ul></section>'''
    if review.read_notes:
        page += '<section><h2>Unreadable report inputs</h2><ul>' + "".join(f'<li>{esc(note)}</li>' for note in review.read_notes) + '</ul></section>'
    page += '''<footer><p class="small">This HTML is derived from existing local reports and media. No device capture, status approval, JSON rewrite or test execution is performed by the generator.</p></footer></main>
        <script>document.getElementById('speed').addEventListener('change',function(){for(const video of document.querySelectorAll('video'))video.playbackRate=Number(this.value)});document.getElementById('pause').addEventListener('click',function(){for(const video of document.querySelectorAll('video'))video.pause()});</script></body></html>'''
    destination = review.base / ("Comparison_Draft.html" if args.draft else "Comparison.html")
    destination.write_text(page, encoding="utf-8")
    print(json.dumps({"html": str(destination), "draft": args.draft, "pending": missing, "unreadable_inputs": review.read_notes, "scope": "HTML only; input statuses and evidence files are unchanged."}, indent=2))


if __name__ == "__main__":
    run()
