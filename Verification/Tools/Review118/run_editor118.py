"""Run one exact Review118 Unity Editor check against the working project.

This deliberately does not build, deploy, or contact a backend. Each invocation
records its own Unity log and JSON report so an Editor fixture cannot be mistaken
for an Android or hosted-service result.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "Unity"
EDITOR = Path(r"C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe")
OUTPUT = ROOT / "Verification" / "Evidence" / "Review118"
PRIVATE = ROOT / ".verification-cache" / "Review118" / "NativeLogs"
SUITES = {
    "leaderboard": ("HeartOfTheRain.Verification.LeaderboardParity118Verification.Run", "Native/LeaderboardParity118/LeaderboardParity118.json", "PASS_NATIVE_LEADERBOARD118", "HOTR_REVIEW118_OUT"),
    "teams": ("HeartOfTheRain.Verification.TeamsParity118Verification.Run", "Native/TeamsParity118.json", "PASS_EDITOR_TEAMS_PARITY118", "HOTR_REVIEW118_OUT"),
    "leaderboard_compat": ("HeartOfTheRain.Verification.LeaderboardRefresh115Verification.Run", "Leaderboard115.json", "PASS_NATIVE_LEADERBOARD115", "HOTR_REVIEW115_OUT"),
    "friends_actions": ("HeartOfTheRain.Verification.FriendsAction115Verification.Run", "Native/FriendsAction115.json", "PASS_NATIVE_FRIEND_ACTION115", "HOTR_REVIEW115_OUT"),
    "teams_access": ("HeartOfTheRain.Verification.TeamsAccess109Verification.Run", "Native/TeamsAccess109.json", "PASS_NATIVE_TEAMS_ACCESS109", "HOTR_REVIEW109_OUT"),
    "teams_invites": ("HeartOfTheRain.Verification.TeamsInvites112FunctionalVerification.Run", "Native/TeamsInvites112.json", "PASS_NATIVE_TEAMS_INVITES112", "HOTR_REVIEW112_OUT"),
    "teams_lifecycle": ("HeartOfTheRain.Verification.TeamsLifecycle113FunctionalVerification.Run", "Native/TeamsLifecycle113.json", "PASS_NATIVE_TEAMS_LIFECYCLE113", "HOTR_REVIEW113_OUT"),
    "teams_mail": ("HeartOfTheRain.Verification.TeamsMail111FunctionalVerification.Run", "Native/TeamsMail111.json", "PASS_NATIVE_TEAMS_MAIL111", "HOTR_REVIEW111_OUT"),
}


def digest(path):
    hash_value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hash_value.update(chunk)
    return hash_value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=SUITES)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_]{1,32}", args.tag):
        parser.error("Safe tag required")
    if not EDITOR.is_file() or "m_EditorVersion: 2022.3.62f3" not in (PROJECT / "ProjectSettings/ProjectVersion.txt").read_text():
        parser.error("Pinned Unity Editor unavailable")
    run = OUTPUT / "Native" / (args.suite + "_" + args.tag)
    logs = PRIVATE / (args.suite + "_" + args.tag)
    if run.exists() or logs.exists():
        parser.error("Fresh run tag required")
    run.mkdir(parents=True)
    logs.mkdir(parents=True)
    method, report, expected, output_env = SUITES[args.suite]
    env = os.environ.copy()
    env[output_env] = str(run)
    command = [str(EDITOR), "-batchmode", "-projectPath", str(PROJECT), "-executeMethod", method, "-logFile", str(logs / "Unity.log")]
    result = {"status": "RUNNING", "method": method, "editorVersion": "2022.3.62f3", "editorSHA256": digest(EDITOR),
              "toolSHA256": digest(Path(__file__)), "startedUtc": datetime.now(timezone.utc).isoformat(),
              "scope": "Actual Unity Editor UGUI/capture check; fixtures are Editor-only. No APK, device, backend, or production parity claim."}
    try:
        with (logs / "Console.log").open("x", encoding="utf-8") as console:
            completed = subprocess.run(command, cwd=PROJECT, env=env, stdout=console, stderr=subprocess.STDOUT,
                                       timeout=900, creationflags=subprocess.CREATE_NO_WINDOW)
        result["exitCode"] = completed.returncode
        target = run / report
        native = json.loads(target.read_text(encoding="utf-8-sig")) if target.is_file() else {}
        result["nativeStatus"] = native.get("status", "MISSING")
        result["checks"] = native.get("checks", 0)
        result["cases"] = native.get("cases", 0)
        result["captures"] = native.get("captures", [])
        result["reportSHA256"] = digest(target) if target.is_file() else None
        result["status"] = "PASS_UNITY_EDITOR118" if completed.returncode == 0 and native.get("status") == expected and not native.get("errors") else "FAIL_UNITY_EDITOR118"
    except subprocess.TimeoutExpired:
        result["status"] = "TIMEOUT_UNITY_EDITOR118"
    except Exception as exc:
        result["status"] = "ERROR_UNITY_EDITOR118"
        result["errorType"] = type(exc).__name__
    result["finishedUtc"] = datetime.now(timezone.utc).isoformat()
    (run / "Invocation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS_UNITY_EDITOR118" else 1


if __name__ == "__main__":
    raise SystemExit(main())
