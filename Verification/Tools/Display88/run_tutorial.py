"""Root-only, real-touch tutorial verification on the authorized current phone.

Requires HOTR_PHYSICAL_SERIAL privately and an existing Display88 --phone run.
No device operation occurs on import. Each mutation is dispatched once; failed
or uncertain touches are retained without retry, uninstall or data clearing.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import time

from phone import CapturePathPhone, public_binding, sha, utc
import run_phone_checks as checks

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MARKER = "HOTR_RunTutorial88"
REMOTE_REPORT = "Tutorial88/Report.json"
PASS = "PASS_PHYSICAL_TUTORIAL_TOUCH88_CURRENT"


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def when(value):
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("NativeUtcMustIncludeTimezone")
    return parsed.astimezone(timezone.utc)


def need(ok, category):
    if not ok:
        raise ValueError(category)


def point(value, report):
    need(isinstance(value, dict), "NativePointMissing")
    x, y = value.get("x"), value.get("y")
    need(type(x) is int and type(y) is int and 0 <= x < report["width"] and 0 <= y < report["height"], "NativePointOutsidePhoneFramebuffer")
    return [x, y]


class TutorialRun:
    def __init__(self, phone):
        self.phone = phone
        phone.assert_installed()
        phone.assert_no_active_attempt()
        self.folder = phone.out / "Tutorial"
        self.folder.mkdir(parents=True, exist_ok=False)
        self.frozen = checks.source_module.freeze()
        build = checks.current_build(phone, self.frozen)
        write(self.folder / "SourceManifest.json", self.frozen)
        self.before = phone.snapshot()
        self.review = {
            "checkpoint": 88, "mode": "tutorial", "status": "RUNNING_PHYSICAL_TUTORIAL_TOUCH88_CURRENT",
            "startedUtc": utc(), "apkSHA256": phone.target["candidateApkSHA256"],
            "apk": public_binding(phone.apk), "target": public_binding(phone.out / "Target.json"),
            "runner": public_binding(Path(__file__)), "phoneHelper": public_binding(HERE / "phone.py"),
            "currentBuildHelper": public_binding(HERE / "run_phone_checks.py"),
            "sourceHasher": public_binding(ROOT / "Verification/Tools/Ads85/run_ads85_native.py"),
            "matchingBuild": build, "sourceManifest": public_binding(self.folder / "SourceManifest.json"),
            "inputCount": self.frozen["inputCount"], "ordinaryBefore": self.before,
            "actions": [], "captures": [], "nativeReportUpdates": [],
            "scope": "Current APK on the explicitly authorized owner-connected physical phone. Actual Android input: one subthreshold control, Match200ms swipe, Rocket600ms swipe, Clear tap and three explicit Next taps. Native transient-memory tutorial/profile/settings; original ordinary saves/preferences are compared before, after and after normal relaunch. No synthetic pointer injection, historical87cause attribution, human campaign, provider/backend, performance or whole-game certification. Captures require separate visual review."
        }
        self.launch_utc = None
        self.first_native_utc = None
        self.deadline = None
        self.last_digest = None
        self.report = None
        self.report_bytes = None
        self.save()

    def save(self):
        write(self.folder / "Review.json", self.review)

    def capture(self, name):
        path = Path(self.phone.capture("Tutorial/" + name + ".png"))
        receipt = public_binding(path)
        metadata = json.loads(path.with_suffix(".json").read_text("utf-8-sig"))
        need(metadata["width"] == 720 and metadata["height"] == 1600, "UnexpectedPhysicalFramebufferDimensions")
        self.review["captures"].append({**receipt, "metadata": public_binding(path.with_suffix(".json"))})
        self.save()
        return receipt

    def observe(self):
        raw = self.phone.adb("exec-out", "cat", self.phone.base + "/" + REMOTE_REPORT, binary=True, check=False)
        need(len(raw) <= 8 * 1024 * 1024, "NativeTutorialReportTooLarge")
        try:
            candidate = json.loads(raw.decode("utf-8-sig"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NonfiniteNativeJson")))
            started = when(candidate.get("utc", ""))
        except (ValueError, TypeError, AttributeError, UnicodeDecodeError):
            return None  # Read-only polling may observe an old/incomplete file.
        if started < self.launch_utc:
            return None
        need(started <= datetime.now(timezone.utc), "NativeTutorialUtcInFuture")
        if self.first_native_utc is None:
            self.first_native_utc = started
            self.review["firstNativeUtc"] = started.isoformat()
        need(started == self.first_native_utc, "NativeTutorialReportChangedLaunchIdentity")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != self.last_digest:
            path = self.folder / "NativeReports" / (str(len(self.review["nativeReportUpdates"]) + 1).zfill(4) + ".json")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            self.review["nativeReportUpdates"].append(public_binding(path))
            self.last_digest = digest
            self.report, self.report_bytes = candidate, raw
            self.review["nativeStatus"] = candidate.get("status")
            self.save()
        need(not candidate.get("error") and not str(candidate.get("status", "")).startswith("FAIL"), "NativeTutorialReportedFailure")
        need(candidate.get("unity") == "2022.3.62f3" and candidate.get("platform") == "Android", "NativeTutorialPlatformMismatch")
        need(candidate.get("isolatedProfile") is True, "NativeTutorialMemoryIsolationMissing")
        need(candidate.get("width") == 720 and candidate.get("height") == 1600, "NativeTutorialGeometryMismatch")
        return candidate

    def wait(self, predicate, reason):
        while time.monotonic() < self.deadline:
            report = self.observe()
            if report is not None and predicate(report):
                return report
            time.sleep(.5)
        raise TimeoutError(reason)

    def ready(self, stage):
        def is_ready(report):
            return report.get("stage") == stage and report.get("status") == "READY_FOR_TOUCH_" + stage.upper() and report.get("busy") is False and report.get("solved") is False
        return self.wait(is_ready, "NativeTutorialReadyDeadline" + stage)

    def hint(self, report, stage):
        lessons = report.get("lessons", [])
        need(isinstance(lessons, list), "NativeTutorialLessonListInvalid")
        matches = [row for row in lessons if row.get("stage") == stage]
        need(len(matches) == 1 and matches[0].get("solved") is False and matches[0].get("turns") == 0, "NativeTutorialUnexpectedInitialLesson")
        hints = matches[0].get("hint")
        need(isinstance(hints, list) and len(hints) == (1 if stage == "Clear" else 2), "NativeTutorialHintInventoryInvalid")
        expected = ["cell:2,2"] if stage == "Clear" else ["cell:2,3", "cell:2,2"]
        need([row.get("cell") for row in hints] == expected, "NativeTutorialHintCellsChanged")
        return [point(value, report) for value in hints]

    def dispatch(self, name, kind, coordinates, duration=None):
        need(name not in {row["name"] for row in self.review["actions"]}, "DuplicateTutorialMutationRefused")
        need(kind in ("tap", "swipe"), "TutorialInputKindInvalid")
        need(len(coordinates) == (2 if kind == "tap" else 4), "TutorialInputArityInvalid")
        need(all(type(value) is int and 0 <= value < (720 if i % 2 == 0 else 1600) for i, value in enumerate(coordinates)), "TutorialInputCoordinatesInvalid")
        self.capture(str(len(self.review["actions"]) + 1).zfill(2) + "_Before_" + name)
        action = {"name": name, "kind": kind, "coordinates": coordinates, "durationMs": duration,
                  "utc": utc(), "dispatch": "PENDING", "nativeUtc": self.first_native_utc.isoformat(),
                  "stageBefore": self.report.get("stage"), "samplesBefore": len(self.report.get("samples", []))}
        self.review["actions"].append(action)
        self.save()  # Durable receipt precedes dispatch; uncertain delivery is never retried.
        args = ["shell", "input", kind, *map(str, coordinates)]
        if kind == "swipe":
            need(type(duration) is int and 1 <= duration <= 1000, "TutorialSwipeDurationInvalid")
            args.append(str(duration))
        self.phone.adb(*args)
        action["dispatch"] = "ADB_COMPLETED"
        action["dispatchCompletedUtc"] = utc()
        self.save()
        return action

    @staticmethod
    def ended_after(report, action, stage):
        samples = report.get("samples", [])
        if not isinstance(samples, list):
            return False
        end = action["coordinates"][-2:]
        return any(row.get("stage") == stage and row.get("phase") == "Ended"
                   and isinstance(row.get("x"), (int, float)) and isinstance(row.get("y"), (int, float))
                   and abs(row["x"] - end[0]) <= 3 and abs(row["y"] - (report["height"] - end[1])) <= 3
                   for row in samples[action["samplesBefore"]:])

    def solved(self, stage, action):
        report = self.wait(lambda row: row.get("stage") == stage and row.get("status") == "SOLVED_" + stage.upper()
                           and row.get("busy") is False and row.get("solved") is True and row.get("canContinue") is True
                           and self.ended_after(row, action, stage), "NativeTutorialSolveDeadline" + stage)
        lesson = [row for row in report["lessons"] if row.get("stage") == stage]
        need(len(lesson) == 1 and lesson[0].get("turns") == 1 and lesson[0].get("solved") is True, "NativeTutorialDidNotSolveInOneTurn")
        self.capture(stage + "_Solved")
        return report

    def execute(self):
        self.launch_utc = when(self.phone.start_marker(MARKER, "touch"))
        self.review["nativeLaunchUtc"] = self.launch_utc.isoformat()
        self.deadline = time.monotonic() + 600
        self.save()
        report = self.ready("Match")
        hints = self.hint(report, "Match")
        unit = math.dist(hints[0], hints[1])
        need(unit > 40, "NativeTutorialCellUnitTooSmall")
        delta = max(1, round(unit * .12))
        control_end = [hints[0][0] + delta, hints[0][1] + delta]
        need(math.dist(hints[0], control_end) < unit * .35, "TutorialControlExceedsCellThreshold")
        control = self.dispatch("Match_Subthreshold_Control", "swipe", hints[0] + control_end, 150)
        report = self.wait(lambda row: row.get("stage") == "Match" and row.get("solved") is False and row.get("busy") is False
                           and row.get("gesture", {}).get("pointerCount") == 0 and self.ended_after(row, control, "Match"), "NativeTutorialSubthresholdControlDeadline")
        self.hint(report, "Match")
        self.review["subthresholdControlPreservedLesson"] = True
        self.capture("Match_After_Subthreshold_Control")
        self.save()
        match = self.dispatch("Match_200ms", "swipe", hints[0] + hints[1], 200)
        report = self.solved("Match", match)
        self.dispatch("Next_After_Match", "tap", point(report.get("next"), report))
        report = self.ready("Rocket")
        hints = self.hint(report, "Rocket")
        rocket = self.dispatch("Rocket_600ms", "swipe", hints[0] + hints[1], 600)
        report = self.solved("Rocket", rocket)
        self.dispatch("Next_After_Rocket", "tap", point(report.get("next"), report))
        report = self.ready("Clear")
        hints = self.hint(report, "Clear")
        clear = self.dispatch("Clear_Rocket_Tap", "tap", hints[0])
        report = self.solved("Clear", clear)
        self.dispatch("Next_After_Clear", "tap", point(report.get("next"), report))
        terminal = self.wait(lambda row: row.get("status") == "PASS_NATIVE_TUTORIAL_TOUCH88", "NativeTutorialTerminalDeadline")
        lessons = terminal.get("lessons", [])
        need(terminal.get("stage") == "Ready" and len(lessons) == 3 and [row.get("stage") for row in lessons] == ["Match", "Rocket", "Clear"]
             and all(row.get("solved") is True and row.get("turns") == 1 for row in lessons), "NativeTutorialTerminalLessonInventoryInvalid")
        need(len(self.review["actions"]) == 7 and all(row["dispatch"] == "ADB_COMPLETED" for row in self.review["actions"]), "TutorialActualInputInventoryIncomplete")
        path = self.folder / "Report.json"
        path.write_bytes(self.report_bytes)
        self.review["nativeReport"] = public_binding(path)
        self.review["terminalNativeUtc"] = when(terminal["utc"]).isoformat()
        self.review["nativeReportBoundToFirstLaunch"] = self.first_native_utc == when(terminal["utc"])
        self.capture("Ready_Final_OS")
        self.review["status"] = PASS
        self.save()

    def finish(self):
        if self.report_bytes is not None and not (self.folder / "Report.json").exists():
            (self.folder / "Report.json").write_bytes(self.report_bytes)
            self.review["nativeReport"] = public_binding(self.folder / "Report.json")
        if self.review["status"] != PASS:
            try:
                self.capture("Failure_Final_OS")
            except Exception as error:
                self.review["failureCaptureType"] = type(error).__name__
        try:
            self.review["appLog"] = self.phone.app_log("Tutorial/Runtime.log")
            need(self.review["appLog"]["selectedErrorCount"] == 0, "TutorialSelectedRuntimeErrorSignatures")
        except Exception as error:
            self.review["status"] = "FAIL_PHYSICAL_TUTORIAL_TOUCH88_CURRENT"
            self.review["appLogFailureType"] = type(error).__name__
        try:
            after = self.phone.snapshot()
            self.review.update(ordinaryAfter=after, ordinaryDataUnchanged=self.before == after)
            need(self.before == after, "OrdinaryDataChangedNoFurtherMutation")
            self.phone.assert_no_active_attempt()
            self.review["normalRelaunch"] = self.phone.finish_probe()
            final = self.phone.snapshot()
            self.review.update(ordinaryAfterRelaunch=final, ordinaryDataUnchangedAfterRelaunch=self.before == final)
            need(self.before == final, "OrdinaryDataChangedAfterRelaunch")
            self.phone.assert_no_active_attempt()
        except Exception as error:
            self.review.update(status="BLOCKED_PHYSICAL_TUTORIAL88_PRESERVATION", preservationFailureType=type(error).__name__)
        try:
            after_sources = checks.source_module.freeze()
            write(self.folder / "Sources_after.json", after_sources)
            unchanged = after_sources == self.frozen
            self.review["inputsUnchanged"] = unchanged
            for name in ("runner", "phoneHelper", "currentBuildHelper", "sourceHasher"):
                same = public_binding(ROOT / self.review[name]["path"]) == self.review[name]
                self.review[name + "Unchanged"] = same
                unchanged = unchanged and same
            self.phone.assert_installed()
            if not unchanged:
                self.review["status"] = "FAIL_PHYSICAL_TUTORIAL88_INPUT_MUTATION"
        except Exception as error:
            self.review.update(status="FAIL_PHYSICAL_TUTORIAL88_INPUT_BINDING", inputBindingFailureType=type(error).__name__)
        self.review["finishedUtc"] = utc()
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phone", type=Path, required=True)
    args = parser.parse_args()
    run = TutorialRun(CapturePathPhone(args.phone))
    try:
        run.execute()
    except Exception as error:
        run.review.update(status="FAIL_PHYSICAL_TUTORIAL_TOUCH88_CURRENT", failureType=type(error).__name__)
        if isinstance(error, (ValueError, TimeoutError)) and re.fullmatch(r"[A-Za-z0-9]+", str(error)):
            run.review["failureCategory"] = str(error)
        run.save()
    finally:
        run.finish()
    print(json.dumps({"status": run.review["status"], "review": (run.folder / "Review.json").relative_to(ROOT).as_posix()}), flush=True)
    return 0 if run.review["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
