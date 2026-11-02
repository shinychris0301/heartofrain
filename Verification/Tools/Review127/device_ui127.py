"""Scoped physical-device UI evidence; no credentials, clearing or uninstalling.

Screenshots stay private. The caller must inspect each screen before choosing
an action. This tool cannot approve a real charge or authorize a VK account.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
ADB = Path(r"C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe")
DEVICE = "1a5297cc78efd9cb7bc4041f1e27946e17badd5696deda53ea9bb78742252164"
PACKAGES = {"com.heartoftherain.game", "com.heartoftherain.ads127demo", "ru.vk.store"}
PRIVATE = ROOT / ".verification-cache/Review127/Device01"
PUBLIC = ROOT / "Verification/Evidence/Review127/Device01"


def adb(*args, timeout=20):
    result = subprocess.run([str(ADB), *args], capture_output=True, timeout=timeout,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode not in (0, 1):
        raise RuntimeError("ScopedAdbOperationFailed")
    return result


def phone():
    rows = [line.split() for line in adb("devices").stdout.decode().splitlines()[1:]]
    devices = [row[0] for row in rows if len(row) == 2 and row[1] == "device"
               and ":" not in row[0] and not row[0].startswith("emulator-")]
    if len(devices) != 1 or hashlib.sha256(devices[0].encode()).hexdigest() != DEVICE:
        raise RuntimeError("ExactAuthorizedPhysicalPhoneRequired")
    return devices[0]


def foreground(serial):
    raw = adb("-s", serial, "shell", "dumpsys", "activity", "activities").stdout.decode(errors="replace")
    matches = re.findall(r"(?:mResumedActivity|topResumedActivity).*?\s([A-Za-z0-9_.]+/[A-Za-z0-9_.$]+)", raw)
    if not matches:
        raise RuntimeError("ForegroundActivityUnavailable")
    return matches[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["capture", "tap", "press", "swipe", "back", "status"])
    parser.add_argument("--tag", required=True)
    parser.add_argument("--expect-package", choices=sorted(PACKAGES), default="com.heartoftherain.game")
    parser.add_argument("--x", type=int)
    parser.add_argument("--y", type=int)
    parser.add_argument("--x2", type=int)
    parser.add_argument("--y2", type=int)
    parser.add_argument("--wait", type=float, default=2)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,60}", args.tag) or not 0 <= args.wait <= 15:
        raise ValueError("FreshBoundedEvidenceTagRequired")
    private = PRIVATE / (args.tag + ".png")
    public = PUBLIC / (args.tag + ".json")
    if private.exists() or public.exists():
        raise RuntimeError("ExistingEvidencePreserved")
    serial = phone()
    before = foreground(serial)
    record = {"utc": datetime.now(timezone.utc).isoformat(), "operation": args.operation,
              "deviceSHA256": DEVICE, "foregroundBefore": before,
              "dataCleared": False, "uninstalled": False,
              "callerMustValidateProviderTestModeBeforeAnyConfirmation": True}
    if args.operation != "status" and before.split("/", 1)[0] != args.expect_package:
        raise RuntimeError("ExpectedForegroundPackageRequired")
    if args.operation in ("tap", "press"):
        if args.x is None or args.y is None or not 0 <= args.x < 720 or not 0 <= args.y < 1600:
            raise ValueError("BoundedObservedCoordinateRequired")
        action = ("tap", str(args.x), str(args.y)) if args.operation == "tap" else (
            "swipe", str(args.x), str(args.y), str(args.x), str(args.y), "150")
        result = adb("-s", serial, "shell", "input", *action)
        record.update(x=args.x, y=args.y, actionExitCode=result.returncode)
    elif args.operation == "swipe":
        if any(v is None for v in (args.x, args.y, args.x2, args.y2)) or not (
                0 <= args.x < 720 and 0 <= args.x2 < 720 and 0 <= args.y < 1600 and 0 <= args.y2 < 1600):
            raise ValueError("BoundedObservedSwipeRequired")
        result = adb("-s", serial, "shell", "input", "swipe", str(args.x), str(args.y), str(args.x2), str(args.y2), "350")
        record.update(x=args.x, y=args.y, x2=args.x2, y2=args.y2, actionExitCode=result.returncode)
    elif args.operation == "back":
        result = adb("-s", serial, "shell", "input", "keyevent", "4")
        record["actionExitCode"] = result.returncode
    time.sleep(args.wait)
    after = foreground(serial)
    record["foregroundAfter"] = after
    if args.operation != "status" and after.split("/", 1)[0] in PACKAGES:
        result = adb("-s", serial, "exec-out", "screencap", "-p")
        if result.returncode != 0 or not result.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("PrivatePngCaptureFailed")
        private.write_bytes(result.stdout)
        record.update(privateScreenshotSHA256=hashlib.sha256(result.stdout).hexdigest(),
                      privateScreenshot=str(private.relative_to(ROOT)).replace("\\", "/"))
    elif args.operation != "status":
        record["privateScreenshotSkipped"] = "External browser/account UI; credential screen not captured."
    public.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
