"""Measure the submitted Android build's first Home frame without game probes.

Run only while the game is closed or on Home; force-stopping an active level
would apply the normal interrupted-attempt rule on reopening.
"""

import argparse
import json
import re
import shutil
import subprocess
import time
from pathlib import Path


PACKAGE = "com.heartoftherain.game"
ACTIVITY = PACKAGE + "/com.unity3d.player.UnityPlayerActivity"


def run(*args, input_bytes=None):
    return subprocess.run(args, input=input_bytes, capture_output=True, check=True).stdout


def rgb(png, ffmpeg):
    raw = run(ffmpeg, "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
              "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1", input_bytes=png)
    return raw


def sample(frame, width, x, y):
    start = (y * width + x) * 3
    return tuple(frame[start:start + 3])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seconds", type=float, default=35)
    args = parser.parse_args()
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for pixel sampling")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    width, height = map(int, run(args.adb, "shell", "wm", "size").decode().strip().split("Physical size: ")[-1].split("x"))
    if (width, height) != (720, 1600):
        raise RuntimeError("Expected the current realme's 720x1600 display, got %sx%s" % (width, height))
    package = run(args.adb, "shell", "dumpsys", "package", PACKAGE).decode(errors="replace")
    version = re.search(r"\bversionCode=(\d+)\b", package)
    if not version or int(version.group(1)) != 130:
        raise RuntimeError("Expected the submitted versionCode 130 build on the device")
    run(args.adb, "shell", "am", "force-stop", PACKAGE)
    started = time.monotonic()
    start_result = run(args.adb, "shell", "am", "start", "-W", "-n", ACTIVITY).decode(errors="replace")
    samples = []
    first_home = None
    while time.monotonic() - started < args.seconds:
        png = run(args.adb, "exec-out", "screencap", "-p")
        captured = time.monotonic() - started
        frame = rgb(png, ffmpeg)
        play = sample(frame, width, 350, 1350)
        # The large Play button is green only on Home. Record a color sample,
        # not a claim that wallet and reward metadata have finished loading.
        home = play[1] > play[0] * 1.35 and play[1] > play[2] * 1.15
        samples.append({"seconds": round(captured, 2), "playRgb": play, "homePlayVisible": home})
        if home and first_home is None:
            first_home = captured
            (output / "FirstHome.png").write_bytes(png)
        if len(samples) == 1:
            (output / "FirstSample.png").write_bytes(png)
        if captured >= args.seconds - 3:
            (output / "LastSample.png").write_bytes(png)
        time.sleep(1)
    report = {"artifactVersionCode": 130, "deviceResolution": [width, height],
              "launch": start_result, "firstHomePlaySeconds": round(first_home, 2) if first_home else None,
              "samples": samples,
              "scope": "Screen capture adds overhead; Home Play visibility is distinct from wallet/badge readiness."}
    (output / "Startup131.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"firstHomePlaySeconds": report["firstHomePlaySeconds"], "samples": len(samples)}))


if __name__ == "__main__":
    main()
