"""Close only the exact owned116 read-only observer, preserving its VM/player."""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import re
import time

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'Verification/Evidence/Review116/Emulator'
KERNEL = ctypes.WinDLL('kernel32', use_last_error=True)
KERNEL.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
KERNEL.OpenProcess.restype = wintypes.HANDLE
KERNEL.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
KERNEL.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
KERNEL.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
KERNEL.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
KERNEL.CloseHandle.argtypes = [wintypes.HANDLE]


def need(value, code):
    if not value:
        raise RuntimeError(code)


def main():
    started_path = BASE / 'ExternalShutdownRelaunch02/Started.json'
    started = json.loads(started_path.read_text())
    before = json.loads((started_path.parent / 'BeforeLaunch.json').read_text())
    runner = ROOT / 'Verification/Tools/Review116/hold_emulator116.py'
    need(hashlib.sha256(runner.read_bytes()).hexdigest() == before['runnerSha256'], 'ExactObserverSourceRequired')
    need(started['currentLauncherJob'] == dict(observed=True, processIds=[started['launcherPid']]),
        'PlayerAndVmOutsideObserverJobRequired')
    need(started['launcherPid'] == 31520 and started['playerPid'] == 38824 and started['vmPid'] == 1464,
        'ExactOwnedLaunchReceiptRequired')
    out = BASE / 'ExternalShutdownRelaunch02/ObserverCleanup.json'
    need(not out.exists(), 'FreshObserverCleanupReceiptRequired')
    handles, records = {}, {}
    try:
        for kind, pid in (('observer', started['launcherPid']), ('player', started['playerPid']), ('vm', started['vmPid'])):
            row = next(item for item in started['ancestry'] if item['ProcessId'] == pid)
            expected = int(re.fullmatch(r'/Date\(([0-9]+)\)/', row['CreationDate'])[1])
            handle = KERNEL.OpenProcess(0x100000 | 0x1000 | (1 if kind == 'observer' else 0), False, pid)
            need(handle, 'ExactOwnedHostHandleRequired')
            handles[kind] = handle
            created, ended, kernel, user = [wintypes.FILETIME() for _ in range(4)]
            need(KERNEL.GetProcessTimes(handle, *[ctypes.byref(x) for x in (created, ended, kernel, user)]),
                'ExactHostCreationReadbackRequired')
            actual = (((created.dwHighDateTime << 32) | created.dwLowDateTime) // 10000) - 11644473600000
            need(actual == expected and KERNEL.WaitForSingleObject(handle, 0) == 0x102,
                'RetainedOwnershipMustRejectPidReuseOrExit')
            records[kind] = dict(pid=pid, expectedCreationMilliseconds=expected, actualCreationMilliseconds=actual)
        need(KERNEL.TerminateProcess(handles['observer'], 0), 'ExactObserverCloseFailed')
        need(KERNEL.WaitForSingleObject(handles['observer'], 5000) == 0, 'ExactObserverDidNotExit')
        time.sleep(2)
        alive = {kind: KERNEL.WaitForSingleObject(handles[kind], 0) == 0x102 for kind in ('player', 'vm')}
        need(all(alive.values()), 'ExistingPlayerAndVmMustRemainAlive')
        value = dict(status='PASS_EXACT_OWNED_OBSERVER_ONLY_CLEANUP116', records=records,
            observerExitObserved=True, playerAndVmRemainAlive=alive,
            startedReceiptSHA256=hashlib.sha256(started_path.read_bytes()).hexdigest(),
            observerSourceSHA256=before['runnerSha256'], runnerSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            defaultAdbCommandPerformed=False, vmOrPlayerTerminationPerformed=False,
            scope='Root-authorized closure of only the owned read-only observer via exact retained Windows process handle, PID and creation-time proof. VM/player handles are query/synchronize-only, stay alive and were outside its job. Subsequent private-bridge foreground/profile proof is separate.')
        with out.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
        print(json.dumps(dict(status=value['status'], playerAndVmRemainAlive=alive)))
    finally:
        for handle in handles.values():
            KERNEL.CloseHandle(handle)


if __name__ == '__main__':
    main()
