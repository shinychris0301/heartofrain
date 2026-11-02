"""Collect the focused Home level-label review; retain preceding component evidence."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Verification/Evidence/HomeLevelButton"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    previous = read("Verification/Evidence/ProfileM71/Source_SHA256.json")["files"]
    changed = [p for p, h in previous.items() if sha(p) != h]
    assert set(changed) == {"Unity/Assets/HeartOfTheRain/App/Home/Runtime/HomeLayoutEngine.cs", "Unity/Assets/HeartOfTheRain/App/Home/Data/Home_Layout.json", "Verification/Run-UnityVerification.ps1"}, changed
    current_assets = {p.relative_to(ROOT).as_posix() for p in (ROOT / "Unity/Assets").rglob("*") if p.is_file()}
    added = current_assets - set(previous)
    editor = "Unity/Assets/HeartOfTheRain/Verification/Editor/HomeLevelButtonReview.cs"
    assert added == {editor, editor + ".meta"}, added
    files = {p: sha(p) for p in sorted(set(previous) | added)}
    frozen = OUT / "Source_SHA256.json"
    if frozen.exists():
        assert files == json.loads(frozen.read_text(encoding="utf-8"))["files"], "Verified source changed"
    report = read("Verification/Evidence/HomeLevelButton/Native_Review.json")
    process = read("Verification/Evidence/Native/HomeLevelButton_Process.json")
    assert process["exitCode"] == 0 and not process["timedOut"]
    assert report["status"] == "PASS_NATIVE_HOME_LEVEL_BUTTON" and not report["error"] and len(report["frames"]) == 8
    assert datetime.fromisoformat(report["utc"].replace("Z", "+00:00")) >= datetime.fromisoformat(process["startedUtc"])
    assert all(f["preLevelOpened"] for f in report["frames"][:2])
    assert {f["language"] for f in report["frames"]} == {"en", "es", "fr", "de", "ru"}
    review = read("Verification/Evidence/HomeLevelButton/Visual_Review.json")
    assert set(review["frames"]) == {f["file"] for f in report["frames"]}
    assert all(sha("Verification/Evidence/HomeLevelButton/" + p) == h for p, h in review["frames"].items())
    apk = "Unity/Builds/Verification/HeartOfTheRain_Development.apk"
    assert sha(apk) == "c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018"
    write("Source_SHA256.json", {"scope": "Exact source/configuration after the targeted native review; no APK binding.", "files": files})
    summary = {"utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_HOME_LEVEL_BUTTON_CHECKPOINT",
               "scope": report["scope"], "package_sha256": "98063ab6bca8e600aebd5341a5291bc4771a33650c606ed524b7a5e80b136f8e",
               "changed_existing_inputs": changed, "added_editor_inputs": sorted(added), "reviewed_native_frames": 8,
               "prelevel_dispatch_levels": [12, 50], "existing_art_and_metadata_preserved": True,
               "native_report_sha256": sha("Verification/Evidence/HomeLevelButton/Native_Review.json"),
               "native_process_sha256": sha("Verification/Evidence/Native/HomeLevelButton_Process.json"),
               "collection_tool_sha256": sha(Path(__file__).relative_to(ROOT).as_posix()),
               "apk_sha256_unchanged": sha(apk), "limitations": "Targeted native label/routing review only. No new APK, Android/device or full campaign/service regression."}
    write("Verification_Summary.json", summary)
    cards = ''.join(f'<figure><figcaption>{f["language"]} | level {f["level"]} | {f["width"]}x{f["height"]}</figcaption><a href="{f["file"]}"><img src="{f["file"]}" alt="Home level label" loading="lazy"></a></figure>' for f in report["frames"])
    (OUT / "Comparison.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Home Level button review</title><style>body{background:#101b2b;color:#eee;font:16px system-ui;margin:30px auto;padding:0 20px;max-width:1400px}.frames{display:flex;flex-wrap:wrap;gap:20px}figure{margin:0 0 20px;width:min(320px,100%)}img{width:100%;height:auto}figcaption{margin-bottom:8px}</style><h1>Home | single Level label</h1><p>The uploaded focused patch replaces Start Level and the separate number with a larger centered Level {currentLevel}, using the existing five translations and text fitting. Button artwork, bounds and pre-level action are preserved. The package's complete older navigation source is not substituted.</p><p>Eight reviewed native Unity 2022.3.62f3 Play Mode UGUI renders, captured through a camera using review-memory campaign/appearance data. Programmatic button clicks opened and closed the actual pre-level modal for levels 12 and 50. These are not device screenshots or physical taps; fixture badges/progress do not represent live services. No APK was built or installed.</p><div class="frames">''' + cards + '</div></html>', encoding="utf-8")
    (ROOT / "Verification/Evidence/Native_Source_Checkpoint.json").write_text(json.dumps({"utc": summary["utc"], "status": summary["status"], "scope": summary["scope"], "review": "Codex_Handoff/Documentation/35_HOME_LEVEL_BUTTON_REVIEW.md", "summary": "Verification/Evidence/HomeLevelButton/Verification_Summary.json", "source_sha256": sha("Verification/Evidence/HomeLevelButton/Source_SHA256.json"), "preceding_profile_component": "Verification/Evidence/ProfileM71/Verification_Summary.json", "preceding_suites_rerun": False, "android_apk_sha256_unchanged": sha(apk)}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "reviewed_frames": 8, "prelevel_levels": [12, 50]}))


if __name__ == "__main__":
    main()
