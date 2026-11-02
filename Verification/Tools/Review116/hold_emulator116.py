"""One normal saved-instance0 launch with a durable read-only host observer.

The observer never terminates a player/VM, changes settings or repairs data.
It stays alive until the launched player's retained handle is signaled, so a
short tool-session lifetime cannot itself end the launcher during testing.
"""
import ctypes
from ctypes import wintypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
HOST = Path('E:/LDPlayer/LDPlayer14')
PUBLIC = ROOT / 'Verification/Evidence/Review116/Emulator/ExternalShutdownRelaunch02'
PRIVATE = ROOT / '.verification-cache/Review116/EmulatorHostRelaunch02'
KERNEL = ctypes.WinDLL('kernel32', use_last_error=True)
KERNEL.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
KERNEL.OpenProcess.restype = wintypes.HANDLE
KERNEL.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
KERNEL.WaitForSingleObject.restype = wintypes.DWORD
KERNEL.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
KERNEL.CloseHandle.argtypes = [wintypes.HANDLE]


def need(value, code):
    if not value:
        raise RuntimeError(code)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (PUBLIC / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def console(name):
    result = subprocess.run([str(HOST / 'ldconsole.exe'), 'list2'], capture_output=True,
        timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    (PRIVATE / (name + '.private')).write_bytes(result.stdout + result.stderr)
    need(result.returncode == 0, 'InstalledConsoleQueryFailed')
    rows = [line.split(',') for line in result.stdout.decode('utf-8', 'replace').splitlines()]
    selected = [row for row in rows if len(row) >= 7 and row[0] == '0']
    need(len(selected) == 1, 'ExactExistingIndexZeroRequired')
    return selected[0]


def current_job():
    data = ctypes.create_string_buffer(65536)
    returned = wintypes.DWORD()
    call = KERNEL.QueryInformationJobObject
    call.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    if not call(None, 3, data, len(data), ctypes.byref(returned)):
        return dict(observed=False, win32Error=ctypes.get_last_error())
    count = ctypes.c_uint32.from_buffer(data, 4).value
    values = (ctypes.c_size_t * count).from_buffer(data, 8)
    return dict(observed=True, processIds=list(values))


def main():
    need(not PUBLIC.exists() and not PRIVATE.exists(), 'OnlyOneFreshApprovedRelaunchRequired')
    PUBLIC.mkdir(parents=True)
    PRIVATE.mkdir(parents=True)
    before = console('ConsoleBefore')
    need(before[4] == '0' and before[5:7] == ['-1', '-1'], 'PreservedInstanceMustBeStopped')
    selector = json.loads((ROOT / '.verification-cache/AndroidTesting95/Discovery/Set03/Selector.json').read_text('utf-8-sig'))
    need(selector['index'] == 0 and hashlib.sha256(selector['serial'].encode()).hexdigest() ==
        '04ab3fc382bfb33ea4fbc120f5172ecfc4aed71652e00977064492ca0f65a017', 'SameEstablishedInstanceRequired')
    config = HOST / 'vms/config/leidian0.config'
    config_before = config.read_bytes()
    (PRIVATE / 'ConfigBefore.private').write_bytes(config_before)
    settings = json.loads(config_before)
    need(settings['propertySettings.phoneModel'] == 'SM-N9810'
        and settings['advancedSettings.resolution'] == dict(width=1600, height=900)
        and settings['advancedSettings.resolutionDpi'] == 240, 'UnchangedEstablishedDeviceProfileRequired')
    paths = [HOST / 'vms/leidian0' / name for name in ('leidian.vbox', 'data.vdi', 'sdcard.vdi')]
    need(all(path.is_file() and not path.is_symlink() for path in paths), 'OriginalSavedDisksRequired')
    files_before = [dict(name=path.name, inode=path.stat().st_ino, bytes=path.stat().st_size,
        createdNs=path.stat().st_ctime_ns) for path in paths]
    write('BeforeLaunch.json', dict(utc=utc(), index=0, launcherPid=os.getpid(),
        launcherParentPid=os.getppid(), launcherCurrentJob=current_job(), files=files_before,
        descriptorSha256=sha(paths[0]), configurationSha256=hashlib.sha256(config_before).hexdigest(),
        runnerSha256=sha(Path(__file__)), ordinaryLaunchOnly=True))
    command = "$console116 = Start-Process -FilePath 'E:/LDPlayer/LDPlayer14/ldconsole.exe' -ArgumentList @('launch','--index','0') -WindowStyle Hidden -PassThru; Write-Output ('ConsolePid=' + $console116.Id); if (-not $console116.WaitForExit(15000)) { throw 'OwnedConsoleDidNotExit' }; Write-Output ('ConsoleExitCode=' + $console116.ExitCode)"
    result = subprocess.run(['powershell', '-NoProfile', '-Command', command], capture_output=True,
        timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    (PRIVATE / 'OrdinaryConsoleLaunch.private').write_bytes(result.stdout + result.stderr)
    need(result.returncode == 0, 'NormalConsoleLauncherFailed')
    match = re.search(rb'ConsolePid=([0-9]+)', result.stdout)
    need(match is not None, 'ConsolePidReceiptRequired')
    console_pid = int(match[1])
    deadline = time.monotonic() + 180
    while True:
        row = console('ConsoleAfter')
        if row[4] == '1' and all(re.fullmatch('[1-9][0-9]*', row[i]) for i in (5, 6)):
            break
        need(time.monotonic() < deadline, 'NormalExistingInstanceReadinessTimeout')
        time.sleep(3)
    player_pid, vm_pid = int(row[5]), int(row[6])
    handles = {name: KERNEL.OpenProcess(0x100000 | 0x1000, False, pid)
        for name, pid in (('player', player_pid), ('vm', vm_pid))}
    need(all(handles.values()), 'ExactLaunchedHostHandlesRequired')
    query = '$all116 = Get-CimInstance Win32_Process; $selected116 = @(' + str(player_pid) + ',' + str(vm_pid) + ',' + str(console_pid) + ',' + str(os.getpid()) + '); for ($step116=0; $step116 -lt 8; $step116++) { $parents116 = @($all116 | Where-Object { $selected116 -contains $_.ProcessId } | ForEach-Object { $_.ParentProcessId }); $selected116 = @($selected116 + $parents116 | Select-Object -Unique) }; $all116 | Where-Object { $selected116 -contains $_.ProcessId } | Select-Object Name,ProcessId,ParentProcessId,CreationDate,CommandLine | ConvertTo-Json -Depth 3 -Compress'
    ancestry = subprocess.run(['powershell', '-NoProfile', '-Command', query], capture_output=True,
        timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    (PRIVATE / 'HostAncestry.private').write_bytes(ancestry.stdout + ancestry.stderr)
    need(ancestry.returncode == 0, 'HostAncestryReadbackRequired')
    raw = json.loads(ancestry.stdout)
    rows = raw if isinstance(raw, list) else [raw]
    public_rows = [{key:value for key,value in item.items() if key != 'CommandLine'} for item in rows]
    files_after = [dict(name=path.name, inode=path.stat().st_ino, createdNs=path.stat().st_ctime_ns) for path in paths]
    need(all(a['inode'] == b['inode'] and a['createdNs'] == b['createdNs']
        for a,b in zip(files_before, files_after, strict=True)), 'SavedDiskFileIdentitiesChanged')
    write('Started.json', dict(status='RUNNING_DURABLE_ORDINARY_EMULATOR116_LAUNCH', utc=utc(),
        index=0, consolePid=console_pid, consoleExitCode=0, playerPid=player_pid, vmPid=vm_pid,
        launcherPid=os.getpid(), launcherParentPid=os.getppid(), ancestry=public_rows,
        currentLauncherJob=current_job(), savedDiskFileIdentitiesPreserved=True,
        privateServerPort=5041, defaultServerCommandPerformed=False,
        scope='Single normal launch of the same saved index0 after retained vendor host crash. Launcher remains alive and observes retained exact host handles; never terminates a VM/player or changes its settings/data. Device/profile reconciliation remains separate.'))
    print(json.dumps(dict(status='RUNNING_DURABLE_ORDINARY_EMULATOR116_LAUNCH', playerPid=player_pid,
        vmPid=vm_pid, consolePid=console_pid, launcherPid=os.getpid())), flush=True)
    try:
        while KERNEL.WaitForSingleObject(handles['player'], 0) == 0x102:
            time.sleep(5)
        exits = {}
        for name, handle in handles.items():
            code = wintypes.DWORD()
            need(KERNEL.GetExitCodeProcess(handle, ctypes.byref(code)), 'ExactRetainedHostExitReadbackFailed')
            exits[name] = dict(signaled=KERNEL.WaitForSingleObject(handle, 0) == 0,
                exitCode=code.value, hexExitCode=hex(code.value))
        write('Finished.json', dict(status='OBSERVED_DURABLE_EMULATOR116_HOST_EXIT', utc=utc(),
            retainedHandleExitStates=exits, hostTerminationCommandPerformed=False,
            scope='Read-only retained exact handle exit observation. Trigger is not inferred.'))
        print(json.dumps(dict(status='OBSERVED_DURABLE_EMULATOR116_HOST_EXIT', exits=exits)), flush=True)
    finally:
        for handle in handles.values():
            KERNEL.CloseHandle(handle)


if __name__ == '__main__':
    main()
