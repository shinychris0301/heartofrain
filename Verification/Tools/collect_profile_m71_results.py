"""Collect native M71 Profile evidence without replacing historical Android reports."""
import hashlib
import html
import json
import re
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Verification/Evidence/ProfileM71"
MODES = ["ProfileM71Play", "ProfileM71Restart", "ProfileChecks", "DailyGiftPlay",
         "WellworksPlay", "RainCupPlay", "PlaySmoke", "Checks"]
APK = "Unity/Builds/Verification/HeartOfTheRain_Development.apk"
APK_HASH = "c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    frozen = read("Verification/Evidence/ProfileM71/Source_SHA256.json")["files"]
    assert all(digest(p) == h for p, h in frozen.items()), "A verified source input changed"
    current = {p.relative_to(ROOT).as_posix() for p in (ROOT / "Unity/Assets").rglob("*") if p.is_file()}
    assert current == {p for p in frozen if p.startswith("Unity/Assets/")}, "Unity asset inventory changed"
    previous = read("Verification/Evidence/ChapterBackground/Source_SHA256.json")["files"]
    changed = [p for p, h in previous.items() if p.startswith("Unity/Assets/") and digest(p) != h]
    assert changed == ["Unity/Assets/HeartOfTheRain/App/Home/Runtime/HomePage.cs"], changed
    added = sorted(p for p in current if p not in previous)
    assert len(added) == 81, len(added)
    assert digest(APK) == APK_HASH, "The historical APK changed"
    suites = {}
    for mode in MODES:
        prefix = "Verification/Evidence/ProfileM71/Native_Checkpoints/" + mode
        report, process = read(prefix + ".json"), read(prefix + "_Process.json")
        assert process["exitCode"] == 0 and not process["timedOut"], mode
        assert report["status"].startswith("PASS") and not report.get("errors") and not report.get("failures") and not report.get("failed"), mode
        assert datetime.fromisoformat(report["utc"].replace("Z", "+00:00")) >= datetime.fromisoformat(process["startedUtc"]), mode
        checks = report["checks"]
        suites[mode] = {"checks": len(checks) if isinstance(checks, list) else checks,
                        "report_sha256": digest(prefix + ".json"), "process_sha256": digest(prefix + "_Process.json")}
    play = read("Verification/Evidence/ProfileM71/Native_Play_Checks.json")
    restart = read("Verification/Evidence/ProfileM71/Native_Restart_Checks.json")
    frames = set(play["frames"] + restart["frames"])
    reviewed = read("Verification/Evidence/ProfileM71/Visual_Review.json")
    assert frames == set(reviewed["frames"]), "A native frame has not been reviewed"
    for name, expected in reviewed["frames"].items():
        path = "Verification/Evidence/ProfileM71/" + name
        assert digest(path) == expected, name
        width, height = struct.unpack(">II", (ROOT / path).read_bytes()[16:24])
        assert (width, height) in {(393, 852), (320, 480), (320, 568), (768, 1024), (900, 2000)}
    package = read("Verification/Evidence/ProfileM71/Package_Review.json")
    assert package["package_sha256"] == "d3de8216c9c1d90af1492ae14b4bd8543f949531252b80281a11f6dc3938826d"
    for p, expected in package["imported_art_sha256"].items():
        assert digest(p) == expected, p
    all_guids = {}
    for p in (ROOT / "Unity/Assets").rglob("*.meta"):
        guid = re.search(r"^guid: (\w+)", p.read_text(encoding="utf-8-sig"), re.M)
        if guid:
            assert guid[1] not in all_guids, str(p)
            all_guids[guid[1]] = str(p)
    summary = {
        "utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_NATIVE_PROFILE_M71_CHECKPOINT",
        "scope": "Native Unity 2022.3.62f3 Play Mode, isolated preferences/restart, native UGUI pointer-drag dispatch and camera-rendered Profile evidence. No Android build/install, physical touch, notches, software keyboard, iOS or device FPS certification.",
        "native_suites": suites, "native_checks": sum(x["checks"] for x in suites.values()),
        "reviewed_profile_frames": len(frames), "frozen_input_files": len(frozen),
        "changed_existing_player_inputs": changed, "added_unity_inputs": added,
        "existing_artwork_and_metadata_unchanged": True,
        "new_art_matches_supplied_package": True, "twilight_repair": package["twilight_repair"],
        "native_open_callback_ms": {"first_after_preparation": play["coldOpenMs"], "maximum_of_12_reopens": play["warmOpenMaxMs"], "scope": "Editor stopwatch measurements of the synchronous open callback only; preparatory work is staged earlier. Not frame times or a controlled Android comparison."},
        "ordinary_appearance_preference_changed": False, "campaign_mutated_by_appearance_actions": False,
        "apk_sha256_unchanged": APK_HASH,
        "remaining": ["Android/iOS build, real touch, software keyboard, notch and graphics-context/device review", "Exact original layered artwork/font is unavailable; delivered reconstructed chrome/font approximation remains", "Real account/name/team services, entitlements and secure account migration are not part of M71", "Gameplay HUD and other demo social portraits are not connected to this Home appearance preference"]
    }
    save("Verification_Summary.json", summary)
    own = Path(__file__).relative_to(ROOT).as_posix()
    save("Verification_Tools_SHA256.json", {p: digest(p) for p in [own, "Verification/Tools/collect_results.py"]})
    groups = [
        ("Approved source and delivered native rendering", ["References/Approved_Profile.png", "Profile_en.png", "References/Approved_Rename.png", "Rename_en.png"]),
        ("Five supported languages", ["Profile_" + x + ".png" for x in ["en", "es", "fr", "de", "ru"]] + ["Rename_" + x + ".png" for x in ["en", "es", "fr", "de", "ru"]]),
        ("Appearance, stats and storage errors", ["All_Avatars.png", "All_Banners.png", "All_Frames.png", "Live_Stats.png", "Long_Names.png", "Rename_Error.png", "Save_Error.png", "Selection_Save_Error.png", "Home_Selected.png"]),
        ("Viewport and native drag review", ["Profile_320x480.png", "Compact_Scrolled.png", "Compact_Rename.png", "Profile_320x568.png", "Profile_768x1024.png", "Tablet_Scrolled.png", "Profile_900x2000.png"]),
        ("Second native process", ["Restart_Profile.png", "Restart_Home.png"])
    ]
    sections = []
    for title, names in groups:
        sections.append("<h2>" + title + '</h2><div class="frames">' + ''.join(
            f'<figure><figcaption>{html.escape(name)}</figcaption><a href="{name}"><img src="{name}" loading="lazy" alt="{html.escape(name)}"></a></figure>' for name in names) + '</div>')
    (OUT / "Comparison.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>M71 Profile native review</title>
<style>body{background:#101b2b;color:#eee;font:16px system-ui;max-width:1500px;margin:28px auto;padding:0 20px}a{color:#9de0ff}.frames{display:flex;flex-wrap:wrap;gap:20px;align-items:flex-start}figure{width:min(330px,100%);margin:0 0 20px}img{width:100%;height:auto}figcaption{font-size:13px;margin-bottom:8px}</style>
<h1>M71 R2 | Profile and Change Name</h1><p>The supplied module is merged with current Home, the revised Chapter 1 background and existing campaign/services. The corrupt Unity Twilight PNG is replaced with the valid supplied preview copy; existing asset GUIDs are preserved. No artwork is regenerated.</p>
<p>Current images are original native Unity 2022.3.62f3 Play Mode UGUI renders through a camera. The two Approved files are supplied reference artwork, not test results. Interactions use programmatic native button/input and raycast/drag dispatch. These are not device screenshots. Real touch, software keyboard, notches, Android/iOS graphics and FPS remain unverified. No APK is built or installed.</p>
<p>Profile names and appearance are local preferences. Native process-restart checks cover both an isolated file adapter and the real PlayerPrefs adapter under a separate verification key, cleaned after recovery. Campaign data is isolated. Teams remains its existing demo; no account identity, social service or entitlement is added. The supplied font/chrome are documented approximations of flattened source artwork.</p>
<p>Profile opens at the top; short/tablet displays scroll the complete authored panel. The scrolled captures intentionally crop the header. Long player/team names use presentation ellipsis without altering saved values. Background blur and collection UI are retained; opening-callback timings exclude preparation and do not certify frame budgets.</p>''' + ''.join(sections) + '</html>', encoding="utf-8")
    (ROOT / "Verification/Evidence/Native_Source_Checkpoint.json").write_text(json.dumps({
        "utc": summary["utc"], "status": summary["status"], "scope": summary["scope"],
        "review": "Codex_Handoff/Documentation/34_PROFILE_M71_INTEGRATION_REVIEW.md",
        "summary": "Verification/Evidence/ProfileM71/Verification_Summary.json",
        "source_sha256": digest("Verification/Evidence/ProfileM71/Source_SHA256.json"),
        "native_suites": suites, "native_checks": summary["native_checks"],
        "previous_service_checkpoint": "Verification/Evidence/BackendGiftUI/Verification_Summary.json",
        "backend_http_suites_rerun": False, "android_apk_sha256_unchanged": APK_HASH
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "native_suites": len(suites), "native_checks": summary["native_checks"], "reviewed_frames": len(frames)}))


if __name__ == "__main__":
    main()
