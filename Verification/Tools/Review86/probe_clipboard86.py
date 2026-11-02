"""Read-only Windows clipboard acquisition metadata; no clipboard content I/O.

This process opens/closes the clipboard only to test acquisition permission.
Its context does not establish an exited Unity process's desktop or Android
clipboard behavior. Reports are exclusively created and never overwritten.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "Verification/Evidence/Review86/Environment/ClipboardAccess.json"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class UserObjectFlags(ctypes.Structure):
    _fields_ = [("inherit", wintypes.BOOL), ("reserved", wintypes.BOOL),
                ("flags", wintypes.DWORD)]


def probe() -> dict:
    if os.name != "nt":
        raise RuntimeError("WindowsMetadataProbeRequired")
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    user.OpenClipboard.argtypes = [wintypes.HWND]
    user.OpenClipboard.restype = wintypes.BOOL
    user.CloseClipboard.argtypes = []
    user.CloseClipboard.restype = wintypes.BOOL
    user.GetOpenClipboardWindow.argtypes = []
    user.GetOpenClipboardWindow.restype = wintypes.HWND
    user.GetProcessWindowStation.argtypes = []
    user.GetProcessWindowStation.restype = wintypes.HANDLE
    user.GetThreadDesktop.argtypes = [wintypes.DWORD]
    user.GetThreadDesktop.restype = wintypes.HANDLE
    user.GetUserObjectInformationW.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD)]
    user.GetUserObjectInformationW.restype = wintypes.BOOL
    kernel.GetCurrentProcessId.argtypes = []
    kernel.GetCurrentProcessId.restype = wintypes.DWORD
    kernel.GetCurrentThreadId.argtypes = []
    kernel.GetCurrentThreadId.restype = wintypes.DWORD
    kernel.ProcessIdToSessionId.argtypes = [wintypes.DWORD,
                                           ctypes.POINTER(wintypes.DWORD)]
    kernel.ProcessIdToSessionId.restype = wintypes.BOOL

    def object_name(handle: int, known: str) -> dict:
        # Avoid emitting arbitrary desktop names or user-specific identifiers.
        value = ctypes.create_unicode_buffer(256)
        needed = wintypes.DWORD()
        ctypes.set_last_error(0)
        ok = bool(user.GetUserObjectInformationW(
            handle, 2, value, ctypes.sizeof(value), ctypes.byref(needed)))
        error = ctypes.get_last_error() if not ok else 0
        return {"available": ok, "name": known if ok and value.value == known
                else "nondefault_redacted" if ok else None,
                "error": error}

    pid = kernel.GetCurrentProcessId()
    session = wintypes.DWORD()
    ctypes.set_last_error(0)
    session_ok = bool(kernel.ProcessIdToSessionId(pid, ctypes.byref(session)))
    session_error = ctypes.get_last_error() if not session_ok else 0
    station = user.GetProcessWindowStation()
    desktop = user.GetThreadDesktop(kernel.GetCurrentThreadId())
    station_flags = UserObjectFlags()
    needed = wintypes.DWORD()
    ctypes.set_last_error(0)
    flags_ok = bool(user.GetUserObjectInformationW(
        station, 1, ctypes.byref(station_flags), ctypes.sizeof(station_flags),
        ctypes.byref(needed)))
    flags_error = ctypes.get_last_error() if not flags_ok else 0
    report = {
        "schema": 1, "status": "RUNNING", "startedUtc": utc(),
        "scope": "Actual current Windows Python child process acquisition "
                 "metadata only. Not an exited Unity process or Android proof.",
        "probeSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "pid": pid, "sessionId": session.value if session_ok else None,
        "sessionQueryError": session_error,
        "windowStation": object_name(station, "WinSta0"),
        "desktop": object_name(desktop, "Default"),
        "stationVisible": bool(station_flags.flags & 1) if flags_ok else None,
        "stationFlagsQueryError": flags_error,
        "clipboardContentRead": False, "clipboardContentWritten": False,
        "clipboardTitlesRead": False, "userInformationRecorded": False,
        "attemptCount": 5, "spacingMilliseconds": 100, "attempts": [],
        "limitations": [
            "Acquisition denial does not establish an Android clipboard defect.",
            "Past Unity windowstation/session were not recorded by this probe.",
            "No clipboard payload, recovery code, token, title or user name "
            "is accessed or serialized."]}
    for index in range(5):
        if index:
            time.sleep(.1)
        ctypes.set_last_error(0)
        opened = bool(user.OpenClipboard(None))
        # Capture immediately, before any subsequent Win32 API can alter it.
        open_error = ctypes.get_last_error() if not opened else 0
        row = {"index": index, "utc": utc(), "opened": opened,
               "openError": open_error, "closedByProbe": False,
               "closeError": 0}
        if opened:
            try:
                pass  # Intentionally no GetClipboardData or format/content API.
            finally:
                ctypes.set_last_error(0)
                closed = bool(user.CloseClipboard())
                row["closedByProbe"] = closed
                row["closeError"] = ctypes.get_last_error() if not closed else 0
        row["openWindowPresentAfterAttempt"] = bool(user.GetOpenClipboardWindow())
        report["attempts"].append(row)
    report["allAcquisitionsDenied"] = all(not row["opened"] for row in report["attempts"])
    report["allAcquisitionErrorsAccessDenied"] = all(row["openError"] == 5 for row in report["attempts"])
    report["status"] = ("RECORDED_WINDOWS_CLIPBOARD_ACQUISITION_METADATA86"
                        if not any(row["opened"] and not row["closedByProbe"]
                                   for row in report["attempts"])
                        else "FAIL_WINDOWS_CLIPBOARD_CLOSE86")
    report["finishedUtc"] = utc()
    return report


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    # Reserve the exact output before probing; do not overwrite older evidence.
    with REPORT.open("x", encoding="utf-8", newline="\n") as stream:
        report = probe()
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"status": report["status"],
                      "report": REPORT.relative_to(ROOT).as_posix(),
                      "allAcquisitionsDenied": report["allAcquisitionsDenied"],
                      "allAcquisitionErrorsAccessDenied": report["allAcquisitionErrorsAccessDenied"]}))
    return 0 if report["status"].startswith("RECORDED_") else 1


if __name__ == "__main__":
    sys.exit(main())
