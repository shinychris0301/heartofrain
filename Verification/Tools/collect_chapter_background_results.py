"""Collect the narrowly scoped Chapter 1 artwork review after the native runner."""
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Verification/Evidence/ChapterBackground"
ART = "Unity/Assets/HeartOfTheRain/App/Home/Art/Chapter01_VillageWell.png"
HOME = "Unity/Assets/HeartOfTheRain/App/Home/Runtime/HomePage.cs"
RUNNER = "Verification/Run-UnityVerification.ps1"
PROBE = "Unity/Assets/HeartOfTheRain/Verification/Editor/ChapterBackgroundReview.cs"
APPROVED = "f1b2021b887b323186e25bd5f09e2f075ff840f86ce4ab3acf5950213c020533"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    previous = read("Verification/Evidence/BackendGiftUI/Source_SHA256.json")["files"]
    # The preceding checkpoint records its final collector separately from tested runtime inputs.
    previous["Verification/Tools/collect_backend_gift_ui_results.py"] = read(
        "Verification/Evidence/BackendGiftUI/Verification_Summary.json")["collection_tool_sha256"]
    changed = [p for p, old in previous.items() if digest(p) != old]
    assert set(changed) == {ART, HOME, RUNNER}, changed
    added = [p.relative_to(ROOT).as_posix() for p in (ROOT / "Unity/Assets").rglob("*")
             if p.is_file() and p.relative_to(ROOT).as_posix() not in previous]
    assert set(added) == {PROBE, PROBE + ".meta"}, added
    assert digest(ART) == APPROVED
    assert digest(ART + ".meta") == previous[ART + ".meta"]
    assert "guid: 79016e1d2af753dc8f250504aeac3654" in (ROOT / (ART + ".meta")).read_text()
    assert struct.unpack(">II", (ROOT / ART).read_bytes()[16:24]) == (937, 1678)
    process = read("Verification/Evidence/Native/ChapterBackground_Process.json")
    after = read("Verification/Evidence/ChapterBackground/After/Report.json")
    assert process["exitCode"] == 0 and not process["timedOut"]
    assert after["status"] == "PASS_NATIVE_HOME_RENDER" and not after["error"]
    assert datetime.fromisoformat(after["utc"].replace("Z", "+00:00")) >= datetime.fromisoformat(process["startedUtc"])
    assert len(after["frames"]) == 3
    reviewed = read("Verification/Evidence/ChapterBackground/Visual_Review.json")
    for p, h in reviewed["frames"].items():
        assert digest("Verification/Evidence/ChapterBackground/" + p) == h, p
    assert len(reviewed["frames"]) == 6
    for f in after["frames"]:
        assert f["texture"] == "Chapter01_VillageWell"
        assert (f["width"], f["height"]) in {(720, 1280), (900, 2000), (1200, 1600)}
        uv = f["uv"]
        assert abs(uv["y"] + uv["height"] - 1) < .0001
        assert abs(uv["width"] / uv["height"] * 937 / 1678 - f["width"] / f["height"]) < .0001
    apk = "Unity/Builds/Verification/HeartOfTheRain_Development.apk"
    assert digest(apk) == "c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018"
    own_path = Path(__file__).relative_to(ROOT).as_posix()
    tested = sorted(set(previous) | set(added) | {own_path, "Verification/Tools/collect_results.py"})
    frozen = OUT / "Source_SHA256.json"
    if frozen.exists():
        for p, h in json.loads(frozen.read_text(encoding="utf-8"))["files"].items():
            if p != own_path:
                assert digest(p) == h, "Verified input changed: " + p
    write("Source_SHA256.json", {"utc": datetime.now(timezone.utc).isoformat(), "files": {p: digest(p) for p in tested}})
    summary = {
        "utc": datetime.now(timezone.utc).isoformat(), "status": "PASS_CHAPTER_BACKGROUND_REVIEW",
        "scope": "Exact supplied PNG, existing GUID/import settings, native Unity 2022.3.62f3 Play Mode UGUI renders at three portrait sizes. Preview state; no profile host, Android build/install or device certification.",
        "changed_baseline_files": changed, "added_unity_files": added,
        "source_image_sha256": APPROVED, "existing_meta_preserved": True,
        "reviewed_native_frames": 6, "native_process": process,
        "previous_apk_sha256_unchanged": digest(apk),
        "limitations": "Cover fitting crops the lower image on tablets and the sides on tall phones. Historical landscape artwork remains available for Editor preview; the app remains portrait only. Backend/transaction suites retain their preceding checkpoint scope."
    }
    write("Verification_Summary.json", summary)
    (ROOT / "Verification/Evidence/Native_Source_Checkpoint.json").write_text(json.dumps({
        "utc": summary["utc"], "status": summary["status"], "scope": summary["scope"],
        "current_review": "Codex_Handoff/Documentation/33_CHAPTER_1_BACKGROUND_REVIEW.md",
        "summary": "Verification/Evidence/ChapterBackground/Verification_Summary.json",
        "source_sha256": digest("Verification/Evidence/ChapterBackground/Source_SHA256.json"),
        "previous_service_checkpoint": "Verification/Evidence/BackendGiftUI/Verification_Summary.json",
        "previous_service_checks_rerun": False,
        "android_apk_unchanged": summary["previous_apk_sha256_unchanged"],
        "android_scope": "Earlier Rain Cup checkpoint; no new build or installation."
    }, indent=2) + "\n", encoding="utf-8")
    cards = []
    for label, size in [("Phone", "720x1280"), ("Tall phone", "900x2000"), ("Tablet", "1200x1600")]:
        cards.append(f'<h2>{label} | {size}</h2><div class="pair">' + ''.join(
            f'<figure><figcaption>{phase}</figcaption><a href="{phase}/Home_{size}.png"><img src="{phase}/Home_{size}.png" alt="{phase} Home at {size}"></a></figure>'
            for phase in ["Before", "After"]) + '</div>')
    (OUT / "Comparison.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Chapter 1 background review</title>
<style>body{font:16px system-ui;background:#0c1929;color:#eee;max-width:1200px;margin:32px auto;padding:0 20px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}img{max-width:100%;height:auto}figcaption{margin:8px 0}a{color:#9de4ff}</style>
<h1>Chapter 1 | revised Home background</h1><p>The supplied 937 by 1678 PNG replaces the original portrait asset byte for byte. Portrait phones and tablets share it with an undistorted cover crop, aligned to the top to keep the character's face below the HUD.</p>
<p>Native Unity 2022.3.62f3 Play Mode UGUI, rendered through a camera at the stated viewports. These are preview-state Home captures from a disposable scene without a profile host; displayed balances, event badges and timers are fixture data. They are not Android screenshots or backend verification. The installed APK is unchanged.</p>
<p>Six original native frames were inspected. Tablet fitting crops the bottom of the artwork; tall-phone fitting crops its sides. Asset GUID and import settings are preserved.</p>''' + ''.join(cards) + '</html>', encoding="utf-8")
    print(json.dumps({"status": summary["status"], "reviewed_frames": 6, "changed_player_inputs": [ART, HOME]}))


if __name__ == "__main__":
    main()
