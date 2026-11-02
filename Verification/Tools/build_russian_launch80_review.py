"""Present existing Russian-launch80 evidence; never publish or infer a visual verdict."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "Verification/Evidence/LaunchRuStoreR3"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out=DEFAULT):
    out = Path(out).resolve()
    esc = lambda value: html.escape(str(value), quote=True)
    warnings = []

    def read(name):
        path = out / name
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError) as error:
            warnings.append(name + ": " + str(error))
            return {}

    def artifact(name):
        rel = PurePosixPath(str(name))
        if rel.is_absolute() or ".." in rel.parts or "\\" in str(name):
            return None
        path = (out / str(rel)).resolve()
        return path if path.is_relative_to(out) and path.is_file() else None

    def link(name, label=None):
        if artifact(name):
            return '<a href="' + esc(name) + '">' + esc(label or name) + "</a>"
        return '<span class="pending">Pending: ' + esc(label or name) + "</span>"

    def bound_review(name, source_sha, apk_sha=None):
        data = read(name)
        if not data:
            return False, "Review pending."
        if data.get("source_sha256") != source_sha:
            return False, "Review source identity does not match."
        if apk_sha is not None and data.get("apk_sha256") != apk_sha:
            return False, "Review APK identity does not match."
        bindings = data.get("artifactSHA256", {})
        if not isinstance(bindings, dict) or not bindings:
            return False, "Review artifact bindings are absent."
        for rel, expected in bindings.items():
            path = artifact(rel)
            if path is None or digest(path) != expected:
                return False, "Review artifact mismatch: " + str(rel)
        return True, data.get("status", "Bound review record")

    source = read("Source_SHA256.json")
    source_sha = digest(out / "Source_SHA256.json") if source else "pending"
    apk = read("APK_Artifact.json")
    apk_sha = apk.get("sha256")
    summary = read("Summary.json")
    summary_bound = bool(summary and summary.get("source_sha256") == source_sha
                         and summary.get("apk_sha256") == apk_sha)
    config = read("Native/Configuration.json")
    locale = read("Native/Locale80.json")
    launch = read("Native/Launch/Native_Review.json")
    install = read("Android/Installation.json")
    correction = read("Archive_Branding_Correction.json")
    title = correction.get("displayTitle", "\u0421\u0435\u0440\u0434\u0446\u0435 \u0434\u043e\u0436\u0434\u044f")
    native_bound, native_status = bound_review("Native_Visual_Notes.json", source_sha)
    device_name = next((name for name in ("Device_Visual_Notes.json", "Android_Visual_Notes.json")
                        if (out / name).is_file()), "Device_Visual_Notes.json")
    device_bound, device_status = bound_review(device_name, source_sha, apk_sha)
    install_bound = bool(install and install.get("source_sha256") == source_sha
                         and install.get("apk_sha256") == apk_sha
                         and install.get("installed_apk_sha256") == apk_sha)

    native_reports = [
        ("General model/import checks", "Native/Checks.json"),
        ("Russian locale and real page listeners", "Native/Locale80.json"),
        ("Launch layouts, loading bar and routes", "Native/Launch/Native_Review.json"),
        ("Connected Play smoke", "Native/PlaySmoke.json"),
        ("Portrait settings/manifest policy", "Native/PortraitChecks.json"),
        ("Profile transactions", "Native/ProfileChecks.json"),
    ]
    rows = []
    checks = 0
    passed_suites = 0
    for label, name in native_reports:
        data = read(name)
        count = data.get("checks", data.get("passed", 0))
        count = len(count) if isinstance(count, list) else count
        count = count if isinstance(count, int) else 0
        checks += count
        passed_suites += int(str(data.get("status", "")).startswith("PASS"))
        rows.append("<tr><td>" + link(name, label) + "</td><td>" + esc(count)
                    + "</td><td>" + esc(data.get("status", "pending")) + "</td></tr>")

    cards = 0
    shown_artifacts = []

    def gallery(names, caption):
        nonlocal cards
        result = []
        for name in names:
            if artifact(name) is None:
                continue
            cards += 1
            shown_artifacts.append(name)
            result.append('<figure><a href="' + esc(name) + '"><img loading="lazy" src="'
                          + esc(name) + '" alt="' + esc(Path(name).stem.replace("_", " "))
                          + '"></a><figcaption>' + esc(name) + "</figcaption></figure>")
        return "<p>" + esc(caption) + '</p><div class="gallery">' + "".join(result) + "</div>"

    frame_names = ["Native/Launch/" + name for name in launch.get("frames", [])]
    russian = [name for name in frame_names if "/Launch_ru_" in name]
    english = [name for name in frame_names if "/Launch_en_" in name]
    bars = [name for name in frame_names if "/Bar_" in name]
    routes = [name for name in frame_names if "/Route_" in name]
    locale_frames = locale.get("captures", [])

    css = """body{margin:0;background:#081c32;color:#eef3f7;font:16px/1.55 system-ui}
main{max-width:1380px;margin:auto;padding:28px}h1,h2{color:#f1cd72}h1{line-height:1.2}
a{color:#8fd6ff}code{overflow-wrap:anywhere}.note{padding:15px 18px;border-left:4px solid #e9bd59;background:#102b44}
.pending{color:#ffd99a}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
figure{margin:0;padding:10px;border:1px solid #3f5c74;background:#10273c;border-radius:8px}
img{display:block;max-width:100%;max-height:620px;width:auto;height:auto;margin:auto}
figcaption{font-size:12px;padding-top:10px;overflow-wrap:anywhere}table{border-collapse:collapse;min-width:70%}
td,th{border:1px solid #426077;padding:8px;text-align:left}.scroll{overflow:auto}video{width:min(100%,450px);max-height:800px}
details{margin:18px 0}summary{cursor:pointer;color:#f1cd72}li{margin:7px 0}.identity{font-size:13px}
"""
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
             "<title>Russian launch and RuStore branding - 80</title><style>" + css + "</style><main>",
             "<h1>" + esc(title) + "</h1><p>Russian launch and RuStore branding review - checkpoint 80.</p>",
             "<p>The launch title and Android display name use Russian. A fresh or invalid language preference defaults to Russian; Russian appears first in both language menus. Existing valid saved language choices retain their original indices and selection.</p>",
             '<p class="note"><strong>Unity splash remains.</strong> The pinned Unity 2022.3 environment reports no eligible entitlement to disable its engine splash. The user confirmed that no eligible license is available. The supplied Russian logo replaces the game opening title; the required engine splash remains. No engine upgrade, license modification or splash bypass is included.</p>',
             '<p class="identity"><strong>Source SHA-256:</strong> <code>' + esc(source_sha) + "</code><br><strong>Development APK SHA-256:</strong> <code>" + esc(apk_sha or "pending") + "</code><br><strong>Current source inputs:</strong> " + esc(len(source.get("files", {}))) + "</p>",
             "<p><strong>Strict summary:</strong> " + link("Summary.json") + " - " + esc(summary.get("status", "pending final publication")) + "; identity " + ("matches current source/APK" if summary_bound else "pending or not matched") + ".</p>",
             "<h2>Native Editor evidence</h2><p>" + esc(passed_suites) + " selected suites pass " + f"{checks:,}" + " checks. These are targeted import, policy, layout, scene-route and transaction checks; they do not rerun the whole campaign or establish Android performance.</p>",
             '<div class="scroll"><table><thead><tr><th>Native suite</th><th>Checks</th><th>Reported status</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>",
             "<p><strong>Native visual review:</strong> " + esc(native_status) + (" (source and artifact hashes match). " if native_bound else " ") + link("Native_Visual_Notes.json") + ".</p>",
             "<h2>Russian launch across portrait sizes</h2>",
             gallery(russian, "Actual native camera renders. The fixed Russian wordmark is independent of the selected status-text language. The tablet retains the approved contained portrait composition."),
             "<h2>Language menus and Russian first start</h2>",
             gallery(locale_frames, "Six native page captures. Visual order is Russian, English, Spanish, French, German; saved indices remain en0/es1/fr2/de3/ru4. Same-tick dimmed Home text in some Settings fixtures is a documented capture limit, not proof of synchronized whole-Home translation."),
             "<h2>Loading-bar fixtures and actual route destinations</h2>",
             gallery(bars, "Captured 0%, 1%, 25%, 72% and 100% fixtures. The report covers 25 bar-geometry cases across five sizes. These percentages are explicit layout fixtures, not startup-time measurements. The dark track is intentional; no black footer plate was observed."),
             gallery(routes, "Four real isolated async scene handoffs preserve fresh prologue, resumed Rocket tutorial, returning progress and completed-tutorial Home routing. Memory profiles and services are controlled fixtures."),
             "<details><summary>English status-text fixtures with the Russian RuStore title</summary>",
             gallery(english, "Existing English status text is retained when English is selected; the RuStore title remains Russian."), "</details>",
             "<h2>Android QA2 evidence</h2><p><strong>Device audit:</strong> " + esc(install.get("status", "pending")) + (" (installed APK/source identity matches)." if install_bound else " (identity verification pending).") + " " + link("Android/Installation.json") + "</p>",
             "<p><strong>Actual device visual review:</strong> " + esc(device_status) + (" (source, APK and artifact hashes match). " if device_bound else " ") + link(device_name) + ". Generating this page does not inspect or approve a screenshot or movie.</p>",
             gallery(["Android/FirstStart_Russian.png", "Android/FirstStart_Language_Menu.png"], "Current QA2 captures. Consult the bound device notes for actual inspection findings and limits."),
             "<p>" + link("Android/Cold_Start.mp4", "Original cold-start recording") + "</p>"]
    if artifact("Android/Cold_Start.mp4"):
        parts.append('<video controls preload="none" src="Android/Cold_Start.mp4"></video>')
        shown_artifacts.append("Android/Cold_Start.mp4")
    parts += [
        "<p>Only isolated QA2 / emulator-5558 receives checkpoint 80. Main LDPlayer retains deployment 64; original QA1 retains 78 and its active attempt. Both are preserved. The QA2 audit separately records preferences/save hashes and the internal verification package identity.</p>",
        "<h2>Scope and remaining limits</h2><ul><li>The engine splash remains because the current entitlement does not support removal; game-title artwork and engine splash are separate stages.</li><li>The opening artwork is the approved 941 by 1672 source. This revision adds the Russian logo, not new high-resolution production/tablet art.</li><li>Native safe-area checks simulate cutout geometry. Physical-device startup, real display cutouts and mobile-memory/compression certification remain separate.</li><li>Development and non-development builds are internal verification packages. RuStore submission, production signing, SDK/purchase services and store approval are not claimed.</li><li>This branding review does not establish full translation, whole-game verification, reference-game parity or smooth gameplay. Checkpoint 79 performance and broader service/device gates remain open.</li></ul>",
        "<p><strong>Audit encoding correction:</strong> " + link("Archive_Branding_Correction.json") + ". Some Cyrillic text in the original reviewer prose was garbled by console encoding. The append-only correction preserves the originals and reads exact wording from the package JSON; it is not an asset or runtime regression.</p>",
        "<h2>Reports and identity records</h2><p>" + " &middot; ".join(link(name) for name in ["Source_SHA256.json", "Source_Delta.json", "APK_Artifact.json", "APK_Branding.json", "APK_Packaging.json", "Android_Build.json", "Android_Release_Build.json", "Native/Configuration.json", "QA_Target.json", "Launch_Visual_Notes.json", "Locale_Visual_Notes.json"]) + "</p>",
    ]
    for doc in sorted((ROOT / "Codex_Handoff/Documentation").glob("80_*.md")):
        rel = Path(os.path.relpath(doc, out)).as_posix()
        parts.append('<p><a href="' + esc(rel) + '">' + esc(doc.name) + "</a></p>")
    if warnings:
        parts.append('<p class="pending">Read warnings: ' + esc("; ".join(warnings)) + "</p>")
    parts.append("</main></html>\n")
    output = out / "Comparison.html"
    output.write_text("".join(parts), encoding="utf-8")
    return {"output": str(output), "sha256": digest(output), "summaryBound": summary_bound,
            "nativeReviewBound": native_bound, "deviceReviewBound": device_bound,
            "nativeChecks": checks, "nativeSuites": passed_suites, "imageCards": cards,
            "shownArtifactCount": len(shown_artifacts), "warnings": warnings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT)
    print(json.dumps(build(parser.parse_args().out), indent=2))
