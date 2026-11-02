"""Collect the scoped native header separation review without replacing earlier evidence."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Verification/Evidence/HomeHeaderAvatar"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    previous = read("Verification/Evidence/HomeLevelButton/Source_SHA256.json")["files"]
    changed = sorted(p for p, h in previous.items() if sha(p) != h)
    home = "Unity/Assets/HeartOfTheRain/App/Home/"
    assert set(changed) == {home + "Runtime/HomePage.cs", home + "Runtime/HomeLayoutEngine.cs", home + "Data/Home_Layout.json", "Verification/Run-UnityVerification.ps1"}, changed
    assets = {p.relative_to(ROOT).as_posix() for p in (ROOT / "Unity/Assets").rglob("*") if p.is_file()}
    added = assets - set(previous)
    editor = "Unity/Assets/HeartOfTheRain/Verification/Editor/HomeHeaderAvatarReview.cs"
    helper = home + "Runtime/HomeHeaderSprites.cs"
    assert added == {editor, editor + ".meta", helper, helper + ".meta"}, added
    files = {p: sha(p) for p in sorted(set(previous) | added)}
    frozen = OUT / "Source_SHA256.json"
    if frozen.exists():
        assert read(frozen)["files"] == files, "Verified source changed"
    native = {}
    image_names = []
    for phase, mode in [("Before", "HomeHeaderBefore"), ("After", "HomeHeaderAvatar")]:
        report = read(OUT / phase / "Native_Review.json")
        process = read("Verification/Evidence/Native/" + mode + "_Process.json")
        assert process["exitCode"] == 0 and not process["timedOut"]
        assert report["status"] == "PASS_NATIVE_HOME_HEADER" and not report["error"] and report["unity"] == "2022.3.62f3"
        assert datetime.fromisoformat(report["utc"].replace("Z", "+00:00")) >= datetime.fromisoformat(process["startedUtc"])
        assert len(report["frames"]) == (3 if phase == "Before" else 12)
        image_names += [phase + "/" + f["file"] for f in report["frames"]]
        native[phase] = report
    after = native["After"]
    assert after["combinations"] == 54 and after["fallbacks"] == 3 and after["stableWallet"] and after["headerRoutes"] and after["prelevel"]
    for before_frame in native["Before"]["frames"]:
        final = next(f for f in after["frames"] if f["file"] == before_frame["file"])
        assert final["edge"] == before_frame["edge"], "Original frame geometry changed"
    review = read(OUT / "Visual_Review.json")
    assert set(review["frames"]) == set(image_names)
    assert all(sha(OUT / p) == h for p, h in review["frames"].items()), "Reviewed image changed"
    atlas = home + "Art/R4_Header.png"
    assert sha(atlas) == "71f17523e9c18006da5389fd1eb615403d85014616c18b3a44190f12bc63f0b3"
    apk = "Unity/Builds/Verification/HeartOfTheRain_Development.apk"
    assert sha(apk) == "c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018"
    write("Source_SHA256.json", {"scope": "Exact current source/configuration for the targeted native header review. No APK binding.", "files": files})
    summary = {"utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_HOME_HEADER_AVATAR_CHECKPOINT", "scope": after["scope"],
               "package_sha256": "e35cb0e4a71c2905aa9f0fed5c6a5395af3c68972c43d65a44e533242a4f90b3", "revision": "R2",
               "changed_existing_inputs": changed, "added_inputs": sorted(added), "combinations": 54, "fallbacks": 3,
               "reviewed_native_frames": 15, "original_frame_size_preserved": True, "existing_art_and_metadata_preserved": True,
               "native_report_sha256": sha(OUT / "After/Native_Review.json"), "native_process_sha256": sha("Verification/Evidence/Native/HomeHeaderAvatar_Process.json"),
               "collection_tool_sha256": sha(Path(__file__)), "apk_sha256_unchanged": sha(apk),
               "limitations": "Targeted native Editor source/render/routing check. No new APK, device/touch/notch/persistence/FPS or full campaign/service regression. Earlier suites retain their own scope."}
    write("Verification_Summary.json", summary)
    pairs = ""
    for frame in native["Before"]["frames"]:
        pairs += '<div class="pair">' + ''.join(f'<figure><figcaption>{phase} | Dariya / Sapphire | {frame["width"]}×{frame["height"]}</figcaption><a href="{phase}/{frame["file"]}"><div class="crop"><img src="{phase}/{frame["file"]}" alt="{phase} header"></div></a></figure>' for phase in ["Before", "After"]) + '</div>'
    cards = ''.join(f'<figure><figcaption>{f["avatar"]} / {f["frame"]} | {f["width"]}×{f["height"]}</figcaption><a href="After/{f["file"]}"><img loading="lazy" src="After/{f["file"]}" alt="Home avatar and wallet"></a></figure>' for f in after["frames"])
    (OUT / "Comparison.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Home header avatar separation</title><style>body{background:#101b2b;color:#eee;font:16px system-ui;margin:30px auto;padding:0 20px;max-width:1400px}.frames,.pair{display:flex;flex-wrap:wrap;gap:20px}figure{margin:0 0 24px;width:min(320px,100%)}img{width:100%;height:auto}figcaption{margin-bottom:8px}.crop{height:92px;overflow:hidden}a{color:#a9d8ff}</style><h1>Home header | independent avatar</h1><p>R2 separates the portrait from the coin/lives/settings panel using the unchanged approved atlas. The original square frame remains 17% of header width; the selected portrait hides the baked fallback. Profile choices update the avatar visuals while other Home objects and counters stay intact.</p><p>Native Unity 2022.3.62f3 Play Mode: all 54 avatar/frame combinations and three fallback states pass at three portrait sizes. Programmatic Profile choices, currency/settings routing and the actual Level 18 pre-level open pass. All 15 native frames below were inspected. Click any image for the full original PNG.</p><p>Review-memory fixtures; these are camera-rendered native UGUI frames, not device screenshots or physical taps. No persistence, notch, FPS, production-service or whole-project certification is implied. No APK was built or installed.</p><h2>Original overlay versus separated header</h2>''' + pairs + '<h2>Final native frames</h2><div class="frames">' + cards + '</div></html>', encoding="utf-8")
    (ROOT / "Verification/Evidence/Native_Source_Checkpoint.json").write_text(json.dumps({"utc": summary["utc"], "status": summary["status"], "scope": summary["scope"],
        "review": "Codex_Handoff/Documentation/36_HOME_HEADER_AVATAR_REVIEW.md", "summary": "Verification/Evidence/HomeHeaderAvatar/Verification_Summary.json",
        "source_sha256": sha(OUT / "Source_SHA256.json"), "preceding_component": "Verification/Evidence/HomeLevelButton/Verification_Summary.json", "preceding_suites_rerun": False,
        "android_apk_sha256_unchanged": sha(apk)}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "native_combinations": 54, "fallback_states": 3, "reviewed_frames": 15, "source_inputs": len(files)}))


if __name__ == "__main__":
    main()
