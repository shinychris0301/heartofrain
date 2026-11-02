"""Explicit physical-phone marker probes with preserved native timing evidence.

No device operation occurs on import. Phone owns authorization and device/APK
selection. Reports are polled through small stat calls once per ten seconds;
screenshots, video, graphics dumps and memory/thermal queries never run inside a
measured fixture. Completion means recorded diagnostics, not smoothness approval.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import struct
import time

from phone import Phone, PACKAGE


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PROBES = ROOT / "Unity/Assets/HeartOfTheRain/Verification"
REVIEW = ROOT / "Verification/Evidence/Review86/Summary.json"
# marker, text, report, native completion, native seconds, source file
SUITES = {
    "Fluidity": ("HOTR_RunFluidity", "candidate", "Fluidity/Measurement.json", "RECORDED_NATIVE_FLUIDITY", 210, "FluidityDeviceProbe.cs"),
    "PowerFall": ("HOTR_RunPowerFall77", "physical87", "PowerFall77/Report.json", "PASS_NATIVE_POWER_FALL77", 600, "PowerFall77Probe.cs"),
    "DensityCrates": ("HOTR_RunObstacleDensity", "candidate_1", "ObstacleDensity/Report.json", "PASS_OBSTACLE_DENSITY_PLAYBACK", 360, "ObstacleDensityProbe.cs"),
    "DensityStone": ("HOTR_RunObstacleDensity", "candidate_1-stone", "ObstacleDensity/Report.json", "PASS_OBSTACLE_DENSITY_PLAYBACK", 360, "ObstacleDensityProbe.cs"),
    "DensityGate": ("HOTR_RunObstacleDensity", "candidate_1-gate", "ObstacleDensity/Report.json", "PASS_OBSTACLE_DENSITY_PLAYBACK", 360, "ObstacleDensityProbe.cs"),
    "DensityTiles": ("HOTR_RunObstacleDensity", "candidate_1-tiles", "ObstacleDensity/Report.json", "PASS_OBSTACLE_DENSITY_PLAYBACK", 360, "ObstacleDensityProbe.cs"),
    "FirstPose": ("HOTR_RunFirstPose79", "physical87", "FirstPose79/Report.json", "PASS_NATIVE_FIRST_POSE79", 600, "FirstPose79Probe.cs"),
    "Execution": ("HOTR_RunExecution78", "physical87", "Execution78/Report.json", "PASS_NATIVE_EXECUTION78", 600, "Execution78Probe.cs"),
    "Smoothness": ("HOTR_RunSmoothnessCommand", "physical87", "SmoothnessCommand/Report.json", "PASS_SAME_APK_COMMAND_CONSTRUCTION76", 240, "SmoothnessCommandProbe.cs"),
}
MAX_REPORT_BYTES = 32 * 1024 * 1024


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def when(value):
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Native UTC must carry its timezone")
    return parsed.astimezone(timezone.utc)


def project_path(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Source manifest path escapes the project")
    return path


def check_sources(phone):
    accepted = read(REVIEW)
    path = project_path(accepted["sourceManifest"])
    if sha(path) != phone.target["sourceSHA256"] or phone.target.get("sourceCheckpoint") != 86:
        raise ValueError("Phone APK is not bound to the frozen review86 source manifest")
    frozen = read(path)
    expected = frozen["files"]
    actual_paths = set()
    for category in ("Assets", "Packages", "ProjectSettings"):
        for folder, _, names in os.walk(ROOT / "Unity" / category):
            for name in names:
                source = Path(folder) / name
                relative = source.relative_to(ROOT).as_posix()
                actual_paths.add(relative)
                row = expected.get(relative)
                if row is None or source.stat().st_size != row["bytes"] or sha(source) != row["sha256"]:
                    raise ValueError("Current Unity source differs from the installed frozen APK")
    if actual_paths != set(expected) or len(actual_paths) != frozen["inputCount"]:
        raise ValueError("Current Unity source inventory differs from the frozen APK")
    phone.assert_installed()
    return {"utc": utc(), "manifest": path.relative_to(ROOT).as_posix(), "manifestSHA256": sha(path),
            "inputCount": len(actual_paths), "apkSHA256": phone.target["apkSHA256"], "allCurrentFilesMatch": True}


def diagnostics(phone, folder, label):
    """Only outside measurement: own-process memory and coarse thermal status."""
    result = {"utc": utc(), "scope": "Own-package memory; only coarse device thermal status. Queries occur outside the timed fixture."}
    body = phone.adb("shell", "dumpsys", "meminfo", PACKAGE, check=False)
    if len(body.encode("utf-8")) > 256 * 1024:
        raise ValueError("App memory diagnostic exceeds its bounded export")
    # meminfo is requested for our package only; do not export a device-wide dump.
    path = folder / (label + "_AppMemory.txt")
    path.write_text(body, encoding="utf-8")
    result["appMemory"] = {"path": path.relative_to(phone.run_dir).as_posix(), "sha256": sha(path), "available": PACKAGE in body}
    thermal = phone.adb("shell", "dumpsys", "thermalservice", check=False)
    match = re.search(r"(?im)^\s*(?:Current\s+)?Thermal\s+Status\s*:\s*(\d+)\s*$", thermal)
    result["thermalStatus"] = int(match[1]) if match else None
    result["thermalStatusAvailable"] = match is not None
    # The complete thermal-service dump is intentionally never written.
    return result


def stamp(phone, remote):
    value = phone.adb("shell", "stat", "-c", "%s:%Y", remote, check=False)
    if not re.fullmatch(r"\d+:\d+", value):
        return None
    size = int(value.split(":", 1)[0])
    if size > MAX_REPORT_BYTES:
        raise ValueError("Native report exceeds the 32 MiB collection limit")
    return value


def require(value, message):
    if not value:
        raise ValueError(message)


def validate(name, report):
    expected = SUITES[name][3]
    require(report.get("status") == expected, "Native probe did not complete with its expected status")
    require(isinstance(report.get("errors"), list) and not report["errors"], "Native Unity errors remain in the report")
    require(report.get("platform") == "Android", "Report is not from the Android player")
    if "unity" in report:
        require(report["unity"] == "2022.3.62f3", "Report used a different Unity runtime")
    if name in ("Fluidity", "PowerFall", "FirstPose", "Execution"):
        require(report.get("isolatedProfile") is True and report.get("launchCleared") is True, "Launch/profile isolation proof is missing")
    if name == "Fluidity":
        require(report.get("variant") == "candidate", "Fluidity variant differs")
        phases = report.get("phases", [])
        require(len(phases) == 8 and all(row.get("frames", 0) > 0 for row in phases), "Fluidity phase inventory is incomplete")
        require(len(report.get("frameSamples", [])) > 0, "Fluidity frame measurements are missing")
    elif name.startswith("Density"):
        family = {"DensityCrates": "crate", "DensityStone": "stone", "DensityGate": "gate", "DensityTiles": "tiles"}[name]
        require(report.get("variant") == SUITES[name][1] and report.get("family") == family, "Obstacle family/variant differs")
        rows = report.get("rows", [])
        # The tiles control intentionally has no "tiles" obstacle. Its one
        # distant three-layer crate prevents an already-won fixture; requested
        # density still repeats all five counts, while actual family count is 0.
        actual_counts = Counter({0: 10}) if family == "tiles" else Counter({1: 2, 8: 2, 16: 2, 32: 2, 45: 2})
        require(len(rows) == 10 and Counter(row.get("crates") for row in rows) == actual_counts, "Obstacle density inventory differs")
        require(all(row.get("family") == family for row in rows) and bool(report.get("frames")), "Obstacle measurements are incomplete")
    elif name == "PowerFall":
        require(len(report.get("naturalRows", [])) == 16 and len(report.get("frozenRows", [])) == 4 and bool(report.get("frames")), "Power-fall row/frame inventory is incomplete")
    elif name == "FirstPose":
        rows = report.get("rows", [])
        require(len(rows) == 18 and sum(row.get("holdWorker") is True for row in rows) == 2, "First-pose natural/control inventory differs")
        require(report.get("droppedFrames") == 0 and bool(report.get("frames")), "First-pose frame evidence is missing or dropped")
    elif name == "Execution":
        for field, count in (("modelRows", 8), ("resourceRows", 8), ("naturalRows", 8), ("frozenRows", 4)):
            require(len(report.get(field, [])) == count, "Execution row inventory is incomplete: " + field)
        require(bool(report.get("frames")), "Execution frames are missing")
    elif name == "Smoothness":
        require(report.get("fixtures") == 8 and len(report.get("rows", [])) == 8 and report.get("pairsPerFixture") == 12, "Construction fixture inventory differs")
        require(all(len(row.get("pairs", [])) == 12 for row in report["rows"]), "Construction paired samples are incomplete")
        require(report.get("rawInputUnchanged") is True and report.get("completeQueueParity") is True, "Construction input/queue parity failed")


def collect_images(phone, report, native_report, folder):
    names = []
    for field in ("frames", "pngs", "images"):
        values = report.get(field)
        # Most probes' frames are numeric measurements, not image references.
        if isinstance(values, list) and values and all(isinstance(x, str) for x in values):
            names.extend(values)
    require(len(names) <= 128 and len(set(names)) == len(names), "Native image inventory is unbounded or duplicated")
    result = []
    for name in names:
        require(re.fullmatch(r"[A-Za-z0-9_-]{1,120}\.png", name) is not None, "Native image reference is unsafe")
        remote = str(PurePosixPath(phone.base) / PurePosixPath(native_report).parent / name)
        body = phone.adb("exec-out", "cat", remote, binary=True)
        require(24 <= len(body) <= 32 * 1024 * 1024 and body[:8] == b"\x89PNG\r\n\x1a\n" and body[12:16] == b"IHDR", "Referenced native image is not a bounded PNG")
        width, height = struct.unpack(">II", body[16:24])
        require(0 < width <= 20000 and 0 < height <= 20000, "Referenced native image has invalid dimensions")
        path = folder / "Images" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        result.append({"path": path.relative_to(phone.run_dir).as_posix(), "sha256": sha(path), "width": width, "height": height})
    return result


def measurements(name, report):
    """Summarize observations without imposing an unapproved frame budget."""
    result = {"acceptance": "Diagnostic recording only; no approved smoothness threshold or universal performance certification."}
    if name == "Fluidity":
        result["phases"] = [{key: row.get(key) for key in ("name", "frames", "p50Ms", "p95Ms", "worstMs", "over33ms", "over50ms", "commandMs", "renderMs", "settleSeconds")} for row in report.get("phases", [])]
    if name == "FirstPose":
        result["naturalRows"] = [{key: row.get(key) for key in ("name", "commandMs", "metadataWaitMs", "settleSeconds", "checkpoint78")} for row in report.get("rows", []) if not row.get("holdWorker")]
        result["deliberateBlockedWorkerControlsExcludedFromNaturalTiming"] = 2
    for field in ("naturalRows", "rows"):
        values = [row.get("commandMs") for row in report.get(field, []) if isinstance(row, dict)]
        values = [value for value in values if isinstance(value, (int, float)) and math.isfinite(value)]
        if values and name != "FirstPose":
            result[field + "CommandMs"] = {"count": len(values), "minimum": min(values), "maximum": max(values), "allSamples": values}
    return result


def run_suite(phone, name, root):
    marker, content, remote_rel, expected, seconds, source_name = SUITES[name]
    folder = root / name
    folder.mkdir(parents=True, exist_ok=False)
    phone.assert_no_active_attempt()
    phone.assert_installed()
    before = phone.snapshot()
    remote = phone.base + "/" + remote_rel
    prior_stamp = stamp(phone, remote)
    record = {"suite": name, "utc": utc(), "status": "RUNNING", "marker": marker, "request": content,
              "expectedNativeStatus": expected, "nativeTimeoutSeconds": seconds, "pollIntervalSeconds": 10,
              "toolSHA256": sha(__file__), "phoneHelperSHA256": sha(HERE / "phone.py"),
              "nativeProbeSource": (PROBES / source_name).relative_to(ROOT).as_posix(), "nativeProbeSHA256": sha(PROBES / source_name),
              "sourceManifestSHA256": phone.target["sourceSHA256"], "apkSHA256": phone.target["apkSHA256"],
              "ordinaryBefore": before, "images": [], "scope": "One physical phone; unchanged opt-in diagnostic source, programmatic isolated fixtures. Native PASS statuses describe their fixture invariants only. No screenshots/video/gfx/memory/thermal queries during timed work; ten-second stat polling still has observer overhead."}
    write(folder / "Manifest.json", record)
    report = None
    started = None
    try:
        record["beforeDiagnostics"] = diagnostics(phone, folder, "Before")
        started = when(phone.start_marker(marker, content))
        record["launchUtc"] = started.isoformat()
        write(folder / "Manifest.json", record)
        print(json.dumps({"suite": name, "status": "STARTED", "nativeTimeoutSeconds": seconds}), flush=True)
        deadline = time.monotonic() + seconds + 45  # allow Launch plus the probe's own timeout/report flush
        next_progress = time.monotonic() + 30
        while time.monotonic() < deadline:
            time.sleep(10)
            current = stamp(phone, remote)
            if current is not None and current != prior_stamp:
                raw = phone.adb("exec-out", "cat", remote, binary=True)
                require(len(raw) <= MAX_REPORT_BYTES, "Native report exceeds its bounded collection limit")
                try:
                    candidate = json.loads(raw)
                    fresh = isinstance(candidate, dict) and when(candidate.get("utc", "")) >= started
                except (ValueError, TypeError, AttributeError):
                    candidate, fresh = None, False
                if fresh:
                    report = candidate
                    # Preserve actual native bytes, including failed status/errors/slow samples.
                    (folder / "Report.json").write_bytes(raw)
                    status = report.get("status", "")
                    require(isinstance(status, str), "Native report has invalid status")
                    if status.startswith(("PASS", "FAIL", "RECORDED")):
                        record["nativeStatus"] = status
                        record["reportSHA256"] = sha(folder / "Report.json")
                        record["images"] = collect_images(phone, report, remote_rel, folder)
                        validate(name, report)
                        record["observations"] = measurements(name, report)
                        record["status"] = "RECORDED_PHYSICAL_PROBE_NOT_SMOOTHNESS_CERTIFIED"
                        record["nativeInvariantsPassed"] = True
                        break
            if time.monotonic() >= next_progress:
                print(json.dumps({"suite": name, "status": "WAITING_FOR_NATIVE_REPORT"}), flush=True)
                next_progress = time.monotonic() + 30
        else:
            raise TimeoutError("Physical probe exceeded native timeout plus its 45-second launch/flush allowance")
    except Exception as error:
        record["status"] = "FAIL_PHYSICAL_PROBE"
        record["nativeInvariantsPassed"] = False
        record["failureType"] = type(error).__name__
        record["failureReason"] = str(error) if isinstance(error, (ValueError, TimeoutError)) else "Device/helper operation failed; no transport retry or Unity-error suppression was applied."
    finally:
        record["finishedUtc"] = utc()
        if report is not None:
            record["nativeStatus"] = report.get("status")
            record["nativeErrors"] = report.get("errors")
        # After-work diagnostics and process-scoped logs are kept even on native failure.
        try:
            record["afterDiagnostics"] = diagnostics(phone, folder, "After")
            record["appLog"] = phone.app_log(str(folder.relative_to(phone.run_dir) / "Player.log"))
            if record["appLog"].get("selectedErrorCount", 0):
                record["status"] = "FAIL_PHYSICAL_PROBE"
                record["nativeInvariantsPassed"] = False
                record["appLogErrorsRequireReview"] = True
        except Exception as error:
            record["diagnosticsFailureType"] = type(error).__name__
            record["status"] = "FAIL_PHYSICAL_PROBE"
            record["nativeInvariantsPassed"] = False
        try:
            after = phone.snapshot()
            record["ordinaryAfter"] = after
            record["ordinaryDataUnchanged"] = before == after
            require(before == after, "Ordinary saved data changed during an isolated probe")
            phone.assert_no_active_attempt()
            phone.assert_installed()
            record["normalRelaunch"] = phone.finish_probe()
            final = phone.snapshot()
            record["ordinaryAfterNormalRelaunch"] = final
            record["ordinaryDataUnchangedAfterNormalRelaunch"] = before == final
            require(before == final, "Ordinary saved data changed after normal relaunch")
            phone.assert_no_active_attempt()
            record["safeToContinue"] = True
        except Exception as error:
            record["safeToContinue"] = False
            record["status"] = "BLOCKED_PHYSICAL_PROBE_PRESERVATION"
            record["preservationFailureType"] = type(error).__name__
        write(folder / "Manifest.json", record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--suites", default=",".join(SUITES), help="Comma-separated reviewed marker suite names")
    args = parser.parse_args()
    names = args.suites.split(",")
    if not names or len(set(names)) != len(names) or any(name not in SUITES for name in names):
        parser.error("Use unique suite names: " + ",".join(SUITES))
    phone = Phone(args.out)
    root = phone.run_dir / "Probes"
    root.mkdir(parents=True, exist_ok=True)
    # Each invocation is immutable and may run a new disjoint subset, not overwrite a suite.
    for name in names:
        if (root / name).exists():
            parser.error("A suite already has retained evidence: " + name)
    manifest = root / ("Invocation_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".json")
    result = {"utc": utc(), "status": "RUNNING", "suites": names, "records": [], "toolSHA256": sha(__file__),
              "scope": "Current frozen APK diagnostic execution on one physical phone; native fixture assertions and full raw measurements retained. No universal smoothness, manual campaign, production, provider or multiple-device acceptance."}
    result["sourceBefore"] = check_sources(phone)
    write(manifest, result)
    for name in names:
        record = run_suite(phone, name, root)
        result["records"].append({"suite": name, "status": record["status"], "manifest": (root / name / "Manifest.json").relative_to(phone.run_dir).as_posix(), "manifestSHA256": sha(root / name / "Manifest.json")})
        write(manifest, result)
        print(json.dumps({"suite": name, "status": record["status"], "nativeStatus": record.get("nativeStatus"), "safeToContinue": record["safeToContinue"]}), flush=True)
        if not record["safeToContinue"]:
            result["status"] = "BLOCKED_PHYSICAL_PROBE_PRESERVATION"
            break
    else:
        result["status"] = "RECORDED_PHYSICAL_PROBES_NOT_SMOOTHNESS_CERTIFIED" if all(row["status"] == "RECORDED_PHYSICAL_PROBE_NOT_SMOOTHNESS_CERTIFIED" for row in result["records"]) else "FAIL_PHYSICAL_PROBES"
    try:
        result["sourceAfter"] = check_sources(phone)
    except Exception as error:
        result["status"] = "BLOCKED_PHYSICAL_PROBE_SOURCE_OR_APK_CHANGED"
        result["sourceFailureType"] = type(error).__name__
    result["finishedUtc"] = utc()
    write(manifest, result)
    return 0 if result["status"] == "RECORDED_PHYSICAL_PROBES_NOT_SMOOTHNESS_CERTIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
