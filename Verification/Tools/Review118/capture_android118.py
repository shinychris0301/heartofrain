"""Capture the isolated Review118 Android UGUI candidate on the connected phone.

This is a visual fixture, not a production app or a live-service test. The
script restores the phone's display-size override even when a capture fails.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
ADB = Path(r"C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe")
APK = ROOT / ".verification-cache/Review118/AndroidCandidate/Unity/Builds/HeartRain_Review118_AndroidCandidate.apk"
OUTPUT = ROOT / "Verification/Evidence/Review118/Android/IsolatedCandidate13"
PACKAGE = "com.heartoftherain.review118parity"
ACTIVITY = PACKAGE + "/com.unity3d.player.UnityPlayerActivity"
STATES = (
    "players_world", "players_region", "friends", "find_friends", "teams",
    "team_reward", "invite_friends", "leave_team", "team_detail",
)
SIZES = ((360, 640), (390, 844))


def run(*args, timeout=60, binary=False):
    command = [str(ADB), *args]
    proc = subprocess.run(command, capture_output=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError(f"adb command failed ({proc.returncode}): {' '.join(args)}\n{proc.stderr.decode(errors='replace')}")
    return proc.stdout if binary else proc.stdout.decode(errors="replace").strip()


def png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("Android screencap was not a PNG")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def painted_ui_pixels(data):
    """A gold-outline guard that rejects Android Home and Unity splash frames."""
    image = Image.open(BytesIO(data)).convert("RGB")
    return sum(1 for red, green, blue in image.get_flattened_data()
               if red > 140 and green > 70 and blue < 80 and red > green * 1.25)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirmed-package", required=True, help="Must equal the verified APK package ID")
    parser.add_argument("--skip-install", action="store_true", help="Use the already installed matching candidate APK")
    args = parser.parse_args()
    if args.confirmed_package != PACKAGE or not APK.is_file() or not ADB.is_file():
        parser.error("Verify the APK package ID, APK path, and pinned adb first")
    devices = run("devices")
    online = [line for line in devices.splitlines()[1:] if line.endswith("\tdevice")]
    if len(online) != 1:
        parser.error("Exactly one authorized Android device is required")
    before = run("shell", "wm", "size")
    density = run("shell", "wm", "density")
    override = re.search(r"Override size:\s*(\d+x\d+)", before)
    restore = override.group(1) if override else "reset"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {
        "scope": "Isolated QA Android visual fixture using actual UGUI renderers and neutral data. Not the installed production app, live backend, or release acceptance.",
        "selectionMethod": "Explicit activity launch extra; wait eight seconds after process start; require painted UI pixels and distinct consecutive screenshots; manually review each state. This phone suppresses adb logcat including shell test messages.",
        "deviceBefore": before,
        "deviceDensity": density,
        "package": PACKAGE,
        "apkSHA256": hashlib.sha256(APK.read_bytes()).hexdigest(),
        "startedUtc": datetime.now(timezone.utc).isoformat(),
        "captures": [],
    }
    status = "FAIL_ANDROID_CAPTURE118"
    try:
        if args.skip_install:
            if not run("shell", "pm", "path", PACKAGE):
                raise RuntimeError("The candidate package is not installed")
        else:
            run("install", "-r", "-t", str(APK), timeout=180)
        report["installSkipped"] = args.skip_install
        previous_sha = ""
        for width, height in SIZES:
            run("shell", "wm", "size", f"{width}x{height}")
            observed = run("shell", "wm", "size")
            if f"Override size: {width}x{height}" not in observed:
                raise RuntimeError("Phone display override did not take effect: " + observed)
            for state in STATES:
                run("shell", "am", "start", "-S", "-n", ACTIVITY,
                    "--es", "hotr_review_state", state, timeout=30)
                deadline = time.monotonic() + 30
                process_id = ""
                while True:
                    try:
                        process_id = run("shell", "pidof", PACKAGE, timeout=15)
                    except RuntimeError:
                        process_id = ""
                    if process_id:
                        break
                    if time.monotonic() >= deadline:
                        diagnostic = run("exec-out", "screencap", "-p", timeout=20, binary=True)
                        (OUTPUT / f"StartupFailure_{state}_{width}x{height}.png").write_bytes(diagnostic)
                        raise RuntimeError("App process absent for " + state)
                    time.sleep(0.5)
                time.sleep(8.0)
                deadline = time.monotonic() + 45
                threshold = max(2500, int(width * height * .01))
                painted = 0
                while True:
                    png = run("exec-out", "screencap", "-p", timeout=60, binary=True)
                    try:
                        observed_size = png_size(png)
                    except ValueError:
                        if time.monotonic() >= deadline:
                            raise RuntimeError(f"Android screencap remained non-PNG for {state}")
                        time.sleep(0.6)
                        continue
                    painted = painted_ui_pixels(png) if observed_size == (width, height) else 0
                    snapshot_sha = hashlib.sha256(png).hexdigest()
                    if observed_size == (width, height) and painted >= threshold and snapshot_sha != previous_sha:
                        break
                    if time.monotonic() >= deadline:
                        (OUTPUT / f"StartupFailure_{state}_{width}x{height}.png").write_bytes(png)
                        raise RuntimeError(f"Painted UI absent for {state}: {observed_size}, {painted} gold pixels (minimum {threshold})")
                    time.sleep(0.6)
                path = OUTPUT / f"{state}_{width}x{height}.png"
                path.write_bytes(png)
                previous_sha = snapshot_sha
                report["captures"].append({
                    "state": state, "size": f"{width}x{height}",
                    "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": hashlib.sha256(png).hexdigest(),
                    "launchExtra": state, "processId": process_id,
                    "goldPixels": painted,
                })
                print(f"Captured {path.name}", flush=True)
        status = "PASS_ANDROID_CANDIDATE_CAPTURE118"
    finally:
        try:
            run("shell", "wm", "size", restore)
            report["deviceAfter"] = run("shell", "wm", "size")
            report["densityAfter"] = run("shell", "wm", "density")
            if restore == "reset" and "Override size:" in report["deviceAfter"]:
                status = "FAIL_DEVICE_RESTORE118"
            if restore != "reset" and f"Override size: {restore}" not in report["deviceAfter"]:
                status = "FAIL_DEVICE_RESTORE118"
        except Exception as exc:
            report["restoreError"] = f"{type(exc).__name__}: {exc}"
            status = "FAIL_DEVICE_RESTORE118"
        report["status"] = status
        report["finishedUtc"] = datetime.now(timezone.utc).isoformat()
        (OUTPUT / "CaptureReport.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if status == "PASS_ANDROID_CANDIDATE_CAPTURE118" else 1


if __name__ == "__main__":
    raise SystemExit(main())
