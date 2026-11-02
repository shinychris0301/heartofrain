"""Physical-phone continuation and Shop bounds checks; execution is opt-in.

The shared Phone helper owns device selection, APK identity, ordinary-attempt
guards and bounded ADB calls. This runner never exports a profile or credential.
Only approved, memory-only NoMoves fixtures and their redacted reports leave the
device. A failed case is retained; another case may run only after preservation
and active-attempt checks succeed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import time
from datetime import datetime, timezone
from pathlib import Path

from phone import Phone


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "Verification/Evidence/NoMovesR3/Device_Fixtures.json"
BOUNDS = ROOT / "Verification/Evidence/ShopBounds/Device_Fixtures.json"
MARKER = "HOTR_RunNoMovesR2"
REMOTE_REPORT = "NoMovesR2Device/Report.json"
TAP_STATES = {
    "READY_FOR_TAP", "READY_FOR_REPEAT", "READY_TO_END", "READY_FOR_BACK"
}
READY_STATES = TAP_STATES | {"READY_FOR_SCROLL"}
EXPECTED_INPUTS = {
    "offer": (1, 0), "insufficient": (1, 0), "shop": (1, 0),
    "prepared": (0, 0), "committed": (0, 0), "repeat": (2, 0),
    "repeat_insufficient": (1, 0), "end": (2, 0), "zero": (1, 0),
    "below": (1, 0), "exact": (1, 0), "shop_bounds": (1, 1),
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_utc(value: str | datetime) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Report timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def fixtures() -> tuple[list[dict], dict]:
    primary = json.loads(FIXTURES.read_text(encoding="utf-8"))["entries"]
    bounds = json.loads(BOUNDS.read_text(encoding="utf-8"))["entries"]
    if not isinstance(primary, list) or len(primary) != 11:
        raise ValueError("Expected the eleven approved NoMovesR3 fixtures")
    extra = [row for row in bounds if row.get("scenario") == "shop_bounds"]
    rows = primary + extra
    if len(extra) != 1 or len({row["scenario"] for row in rows}) != len(rows):
        raise ValueError("Fixture scenarios must be unique, including one Shop bounds case")
    if {row["scenario"] for row in rows} != set(EXPECTED_INPUTS):
        raise ValueError("Approved scenario inventory has changed; review before execution")
    for row in rows:
        if not isinstance(row.get("profile"), dict) or not isinstance(row.get("checkpoint"), str):
            raise ValueError("A case must provide the approved memory profile and board checkpoint")
        for key in ("coinsAfter", "movesAfter", "countAfter"):
            if type(row.get(key)) is not int or row[key] < 0:
                raise ValueError("Expected fixture balances must be nonnegative integers")
    return rows, {
        "noMovesR3": {"path": FIXTURES.relative_to(ROOT).as_posix(), "sha256": sha(FIXTURES)},
        "shopBounds": {"path": BOUNDS.relative_to(ROOT).as_posix(), "sha256": sha(BOUNDS)},
    }


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("Device capture is not a PNG")
    width, height = struct.unpack(">II", header[16:24])
    if not (1 <= width <= 20000 and 1 <= height <= 20000):
        raise ValueError("Device capture dimensions are invalid")
    return width, height


def coords(report: dict, width: int, height: int, scrolling: bool) -> list[int]:
    keys = ("x", "y", "endX", "endY") if scrolling else ("x", "y")
    values = [report.get(key) for key in keys]
    if any(type(value) is not int for value in values):
        raise ValueError("Native input coordinates must be integers")
    if any(not (0 <= x < width and 0 <= y < height) for x, y in zip(values[::2], values[1::2])):
        raise ValueError("Native input coordinates are outside the captured phone screen")
    if scrolling and values[:2] == values[2:]:
        raise ValueError("Scroll gesture has zero length")
    return values


def validate_terminal(report: dict, fixture: dict, inputs: list[dict]) -> None:
    name = fixture["scenario"]
    if report.get("status") != "PASS_ANDROID_NO_MOVES" or report.get("error") not in ("", None):
        raise ValueError("Native NoMoves case failed")
    if report.get("scenario") != name or report.get("boardPreserved") is not True:
        raise ValueError("Native case/board provenance differs from the requested fixture")
    expected = {
        "coins": fixture["coinsAfter"], "moves": fixture["movesAfter"],
        "purchases": fixture["countAfter"], "lives": 4 if name == "end" else 5,
    }
    if any(type(report.get(key)) is not int or report[key] != value for key, value in expected.items()):
        raise ValueError("Native result differs from approved wallet, moves, purchase count or lives")
    actual = (sum(row["kind"] == "tap" for row in inputs), sum(row["kind"] == "swipe" for row in inputs))
    if actual != EXPECTED_INPUTS[name]:
        raise ValueError("Expected actual phone taps/swipes were not observed")
    if name == "repeat" and report.get("playedMoves") != 5:
        raise ValueError("Repeat purchase did not play all five granted moves")
    if name == "shop_bounds" and (type(report.get("boundsChecks")) is not int or report["boundsChecks"] <= 0):
        raise ValueError("Native Shop containment and bottom reachability checks are missing")


def run_case(phone: Phone, fixture: dict, out: Path) -> dict:
    name = fixture["scenario"]
    folder = out / "NoMoves" / "Cases" / name
    folder.mkdir(parents=True, exist_ok=False)
    phone.assert_no_active_attempt()
    before = phone.snapshot()
    result = {
        "scenario": name, "startedUtc": utc(), "status": "RUNNING",
        "fixtureSHA256": hashlib.sha256(json.dumps(fixture, ensure_ascii=True, separators=(",", ":")).encode("ascii")).hexdigest(),
        "inputs": [], "captures": [], "ordinaryBefore": before,
    }
    write_json(folder / "Result.json", result)
    began = None
    report = None
    seen = set()
    try:
        began = parse_utc(phone.start_marker(MARKER, json.dumps(fixture, ensure_ascii=True, separators=(",", ":"))))
        result["nativeLaunchUtc"] = began.isoformat()
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            raw = phone.adb("shell", "cat", phone.base + "/" + REMOTE_REPORT, check=False)
            try:
                candidate = json.loads(raw)
                fresh = isinstance(candidate, dict) and parse_utc(candidate.get("utc", "")) >= began
            except (ValueError, TypeError, AttributeError):
                candidate, fresh = None, False
            if not fresh:
                time.sleep(1)
                continue
            if candidate.get("scenario") != name:
                raise ValueError("Fresh native report belongs to another scenario")
            report = candidate
            write_json(folder / "Report.json", report)
            status = report.get("status", "")
            if not isinstance(status, str):
                raise ValueError("Native status is invalid")
            if status in READY_STATES:
                scrolling = status == "READY_FOR_SCROLL"
                key = (status, report.get("stage"), report.get("screen"), report.get("x"), report.get("y"),
                       report.get("endX") if scrolling else None, report.get("endY") if scrolling else None)
                if key not in seen:
                    if len(seen) >= 6:
                        raise ValueError("Native case exceeded the bounded input-stage inventory")
                    frame = Path(phone.capture("NoMoves/Cases/" + name + "/Input_" + str(len(seen) + 1) + "_" + status + ".png"))
                    width, height = png_size(frame)
                    values = coords(report, width, height, scrolling)
                    capture = {"path": frame.relative_to(out).as_posix(), "sha256": sha(frame), "width": width, "height": height}
                    result["captures"].append(capture)
                    action = {"utc": utc(), "status": status, "kind": "swipe" if scrolling else "tap", "coordinates": values}
                    # Record before dispatch. An uncertain transport failure is never retried.
                    seen.add(key)
                    result["inputs"].append({**action, "dispatch": "PENDING"})
                    write_json(folder / "Result.json", result)
                    phone.adb("shell", "input", "swipe" if scrolling else "tap", *map(str, values), *( ["650"] if scrolling else []))
                    result["inputs"][-1]["dispatch"] = "ADB_COMPLETED"
                    write_json(folder / "Result.json", result)
            if status.startswith(("PASS", "FAIL")):
                validate_terminal(report, fixture, result["inputs"])
                result["status"] = "PASS_PHYSICAL_NO_MOVES_CASE"
                break
            time.sleep(1)
        else:
            raise TimeoutError("Physical NoMoves case exceeded its 150-second host bound")
    except Exception as error:
        result["status"] = "FAIL_PHYSICAL_NO_MOVES_CASE"
        # Error text may contain ADB transport details. Preserve only a known local category.
        result["failureType"] = type(error).__name__
        result["failureReason"] = str(error) if isinstance(error, (ValueError, TimeoutError)) else "Phone operation failed; inspect the shared device runner diagnostics."
    finally:
        result["finishedUtc"] = utc()
        if report is not None:
            result["nativeStatus"] = report.get("status")
            try:
                frame = Path(phone.capture("NoMoves/Cases/" + name + "/Final.png"))
                width, height = png_size(frame)
                result["captures"].append({"path": frame.relative_to(out).as_posix(), "sha256": sha(frame), "width": width, "height": height})
            except Exception as error:
                result["finalCaptureFailureType"] = type(error).__name__
        # Do not continue or relaunch if the ordinary account changed or a real
        # attempt became active. The report remains inspectable on either failure.
        try:
            after = phone.snapshot()
            result["ordinaryAfter"] = after
            result["ordinaryDataUnchanged"] = before == after
            if after != before:
                raise RuntimeError("Ordinary saved data changed; subsequent device mutations are blocked")
            phone.assert_no_active_attempt()
            phone.finish_probe()
            final = phone.snapshot()
            result["ordinaryAfterNormalRelaunch"] = final
            result["ordinaryDataUnchangedAfterNormalRelaunch"] = before == final
            if final != before:
                raise RuntimeError("Ordinary saved data changed after normal relaunch; further cases are blocked")
            phone.assert_no_active_attempt()
            result["safeToContinue"] = True
        except Exception as error:
            result["safeToContinue"] = False
            result["preservationFailureType"] = type(error).__name__
            result["status"] = "BLOCKED_PHYSICAL_NO_MOVES_PRESERVATION"
        write_json(folder / "Result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Root-authorized physical-phone run directory")
    args = parser.parse_args()
    out = args.out.resolve()
    rows, inputs = fixtures()
    phone = Phone(out)
    target = out / "NoMoves"
    target.mkdir(parents=True, exist_ok=False)
    summary = {
        "utc": utc(), "status": "RUNNING", "fixtureInputs": inputs, "cases": [],
        "scope": "Current APK on one explicitly selected physical phone. Approved memory-only profiles, fixed test clock, actual Android taps and one Shop list swipe. Board/RNG/continue debit/recovery and native Shop bounds are asserted by the existing Development probe. No owner-profile substitution, live payment, hosted backend, manual playthrough or performance certification.",
    }
    # Evidence lives below NoMoves; Phone captures relative to the shared run root.
    write_json(target / "Summary.json", summary)
    for fixture in rows:
        result = run_case(phone, fixture, out)
        summary["cases"].append(result)
        write_json(target / "Summary.json", summary)
        print(json.dumps({"scenario": result["scenario"], "status": result["status"], "safeToContinue": result["safeToContinue"]}), flush=True)
        if not result["safeToContinue"]:
            summary["status"] = "BLOCKED_PHYSICAL_NO_MOVES_PRESERVATION"
            break
    else:
        summary["status"] = "PASS_PHYSICAL_NO_MOVES_REQUIRES_VISUAL_REVIEW" if all(row["status"] == "PASS_PHYSICAL_NO_MOVES_CASE" for row in summary["cases"]) else "FAIL_PHYSICAL_NO_MOVES"
    summary["finishedUtc"] = utc()
    summary["actualTaps"] = sum(action["kind"] == "tap" and action["dispatch"] == "ADB_COMPLETED" for row in summary["cases"] for action in row["inputs"])
    summary["actualSwipes"] = sum(action["kind"] == "swipe" and action["dispatch"] == "ADB_COMPLETED" for row in summary["cases"] for action in row["inputs"])
    write_json(target / "Summary.json", summary)
    return 0 if summary["status"] == "PASS_PHYSICAL_NO_MOVES_REQUIRES_VISUAL_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
