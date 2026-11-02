"""Root-operated, serial native Shop/RUB and advertising verification.

No service, SDK, emulator, payment or build is started by this runner. The root
operator supplies a fresh loopback HTTP fixture when selecting Http. Every run
gets a new evidence folder; successful and failed prior runs are never replaced.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
UNITY_PROJECT = ROOT / 'Unity'
EVIDENCE = ROOT / 'Verification/Evidence/ShopAds85'
PINNED_UNITY = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe')
PREFIX = 'HeartOfTheRain.Verification.'
WINDOWS_EXTENDED = chr(92) * 2 + '?' + chr(92)
SUITES = {
    'Journal': ('RewardedAdsJournal85Verification.Run', 'RewardedAdsJournal85.json', 'PASS_NATIVE_REWARDED_ADS_JOURNAL85', 120),
    'Parser': ('RewardedAdsParser85Verification.Run', 'RewardedAdsParser85.json', 'PASS_NATIVE_REWARDED_ADS85_PARSER', 120),
    'Http': ('RewardedAdsParser85Verification.RunHttp', 'RewardedAds85_HTTP.json', 'PASS_NATIVE_REWARDED_ADS85_HTTP', 180),
    'Flow': ('RewardedAdsFlow85Verification.Run', 'RewardedAdsFlow85.json', 'PASS_NATIVE_REWARDED_ADS_FLOW85', 180),
    'Rubles': ('ShopRuble85Verification.Run', 'ShopRuble85.json', 'PASS_NATIVE_SHOP_RUBLE85_PREVIEW', 240),
    'Ui': ('RewardedAdsUi85Verification.Run', 'RewardedAdsUi85.json', 'PASS_NATIVE_REWARDED_ADS85_UI', 240),
}


def utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def disk(path: Path) -> str:
    value = str(path.resolve())
    return WINDOWS_EXTENDED + value if os.name == 'nt' and not value.startswith(WINDOWS_EXTENDED) else value


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with open(disk(path), 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(disk(path), 'x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def freeze():
    files = {}
    for category in ('Assets', 'Packages', 'ProjectSettings'):
        base = UNITY_PROJECT / category
        if not base.is_dir():
            raise RuntimeError('RequiredUnityInputDirectoryMissing')
        for folder, _, names in os.walk(disk(base)):
            for name in names:
                absolute = Path(folder) / name
                # Strip the I/O-only extended prefix before producing portable
                # project-relative evidence paths.
                logical = Path(str(absolute).removeprefix(WINDOWS_EXTENDED))
                relative = logical.relative_to(ROOT).as_posix()
                files[relative] = {'sha256': sha(logical), 'bytes': os.stat(disk(logical)).st_size}
    return {'schemaVersion': 1, 'scope': 'Exact Unity Assets, Packages and ProjectSettings bytes',
            'inputCount': len(files), 'files': dict(sorted(files.items()))}


def delta(before, after):
    a, b = before['files'], after['files']
    return {'added': sorted(b.keys() - a.keys()), 'removed': sorted(a.keys() - b.keys()),
            'changed': sorted(k for k in a.keys() & b.keys() if a[k] != b[k])}


def unchanged(change):
    return not any(change.values())


def unity_pids():
    class Entry(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD),
                    ('cntThreads', wintypes.DWORD), ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', wintypes.LONG), ('dwFlags', wintypes.DWORD), ('szExeFile', wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32FirstW.restype = kernel.Process32NextW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise RuntimeError('ProcessEnumerationUnavailable')
    found = []
    try:
        entry = Entry(); entry.dwSize = ctypes.sizeof(entry)
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        if not more:
            raise RuntimeError('ProcessEnumerationUnavailable')
        while more:
            if entry.szExeFile.lower() == 'unity.exe':
                found.append(int(entry.th32ProcessID))
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
            raise RuntimeError('ProcessEnumerationIncomplete')
        return found
    finally:
        kernel.CloseHandle(snapshot)


class OwnedJob:
    """Kill-on-close contains only the Unity process started by this runner."""
    def __init__(self):
        class Basic(ctypes.Structure):
            _fields_ = [('processTime', ctypes.c_longlong), ('jobTime', ctypes.c_longlong), ('flags', wintypes.DWORD),
                        ('minWorkingSet', ctypes.c_size_t), ('maxWorkingSet', ctypes.c_size_t),
                        ('activeLimit', wintypes.DWORD), ('affinity', ctypes.c_size_t),
                        ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
        class Io(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ('readOps', 'writeOps', 'otherOps', 'readBytes', 'writeBytes', 'otherBytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', Io), ('processMemory', ctypes.c_size_t), ('jobMemory', ctypes.c_size_t),
                        ('peakProcess', ctypes.c_size_t), ('peakJob', ctypes.c_size_t)]
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.kernel.SetInformationJobObject.restype = wintypes.BOOL
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise RuntimeError('OwnedUnityJobUnavailable')
        info = Extended(); info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close(); raise RuntimeError('OwnedUnityJobLimitUnavailable')

    def assign(self, pid):
        owned = self.kernel.OpenProcess(0x101, False, pid)  # SET_QUOTA | TERMINATE, own child only
        if not owned:
            raise RuntimeError('OwnedUnityProcessHandleUnavailable')
        try:
            if not self.kernel.AssignProcessToJobObject(self.handle, owned):
                raise RuntimeError('OwnedUnityJobAssignmentFailed')
        finally:
            self.kernel.CloseHandle(owned)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle); self.handle = None


def run_suite(name, run, frozen, unity, env, override_timeout):
    entry, report_name, expected_status, default_timeout = SUITES[name]
    folder = run / 'Suites' / name
    folder.mkdir(parents=True, exist_ok=False)
    before = freeze(); write(folder / 'Sources_before.json', before)
    if not unchanged(delta(frozen, before)):
        raise RuntimeError('FrozenInputsChangedBeforeSuite')
    if unity_pids():
        raise RuntimeError('ConcurrentUnityRefused')
    log = folder / 'Unity.log'; console = folder / 'Console.log'; report = run / 'Native' / report_name
    record = {'suite': name, 'entry': PREFIX + entry, 'status': 'RUNNING', 'startedUtc': utc(), 'pid': None,
              'timeoutSeconds': override_timeout or default_timeout, 'timedOut': False, 'exitCode': None,
              'playMode': name in ('Rubles', 'Ui'), 'quitFlag': False, 'ownedKillOnCloseJobAssigned': False,
              'sourcesBeforeSHA256': sha(folder / 'Sources_before.json')}
    process = None; job = None; began = time.monotonic()
    try:
        job = OwnedJob()
        with open(disk(console), 'x', encoding='utf-8') as output:
            process = subprocess.Popen([str(unity), '-batchmode', '-projectPath', str(UNITY_PROJECT),
                                        '-executeMethod', PREFIX + entry, '-logFile', str(log)],
                                       env=env, stdout=output, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            record['pid'] = process.pid
            job.assign(process.pid); record['ownedKillOnCloseJobAssigned'] = True
            try:
                process.wait(timeout=record['timeoutSeconds'])
            except subprocess.TimeoutExpired:
                record['timedOut'] = True; job.close(); process.wait(timeout=20)
            record['exitCode'] = process.returncode
        if report.is_file():
            native = json.loads(report.read_text('utf-8-sig'))
            record['nativeStatus'] = native.get('status'); record['reportSHA256'] = sha(report)
            record['nativeErrorsEmpty'] = not native.get('errors')
            record['captures'] = {}
            for relative in native.get('captures', []):
                artifact = (run / relative).resolve()
                if not artifact.is_relative_to(run.resolve()) or not artifact.is_file():
                    raise RuntimeError('NativeCaptureMissingOrOutsideRun')
                record['captures'][relative] = sha(artifact)
        else:
            record['nativeStatus'] = 'MISSING'
        record['status'] = ('PASS' if not record['timedOut'] and record['exitCode'] == 0
                            and record['nativeStatus'] == expected_status and record['nativeErrorsEmpty'] else 'FAIL_NATIVE_SUITE')
    except Exception as error:
        record['status'] = 'FAIL_RUNNER'; record['errorType'] = type(error).__name__
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=10)
        if process:
            record['exitCode'] = process.poll()
        record['finishedUtc'] = utc(); record['elapsedSeconds'] = round(time.monotonic() - began, 3)
        record.update(unityLogSHA256=sha(log) if log.is_file() else None, consoleSHA256=sha(console) if console.is_file() else None,
                      inputsUnchanged=False, processStopped=process is None or process.poll() is not None)
        try:
            after = freeze(); write(folder / 'Sources_after.json', after)
            changes = delta(before, after); write(folder / 'Source_Delta.json', changes)
            record.update(sourcesAfterSHA256=sha(folder / 'Sources_after.json'), sourceDeltaSHA256=sha(folder / 'Source_Delta.json'),
                          inputsUnchanged=unchanged(changes) and unchanged(delta(frozen, after)))
        except Exception as error:
            record['sourceFreezeErrorType'] = type(error).__name__
        if not record['inputsUnchanged']:
            record['status'] = 'FAIL_INPUT_MUTATION'
        write(folder / 'Process.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suites', default='Journal,Parser,Http,Flow,Rubles,Ui')
    parser.add_argument('--unity', type=Path, default=PINNED_UNITY)
    parser.add_argument('--timeout-seconds', type=int)
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('This root-operated runner requires Windows native process containment')
    suites = args.suites.split(',')
    if not suites or len(set(suites)) != len(suites) or any(name not in SUITES for name in suites):
        parser.error('Select a unique comma-separated subset: ' + ','.join(SUITES))
    if args.timeout_seconds is not None and not 60 <= args.timeout_seconds <= 900:
        parser.error('Timeout must be within 60..900 seconds')
    unity = args.unity.resolve()
    if not unity.is_file() or unity.name.lower() != 'unity.exe' or '2022.3.62f3' not in unity.parts:
        parser.error('The pinned Unity2022.3.62f3 Editor executable is required')
    if 'm_EditorVersion: 2022.3.62f3' not in (UNITY_PROJECT / 'ProjectSettings/ProjectVersion.txt').read_text('utf-8-sig'):
        parser.error('Project engine pin changed')
    if 'Http' in suites:
        from urllib.parse import urlsplit
        origin = os.environ.get('HOTR_REWARDED_ADS85_HTTP_ORIGIN', '')
        parsed = urlsplit(origin)
        if os.environ.get('HOTR_REWARDED_ADS85_HTTP_ALLOWED') != '1' or parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
            parser.error('Http requires an explicitly allowed loopback fixture origin; root owns its lifecycle')
    import msvcrt
    guard = ROOT / '.verification-cache/ShopAds85/NativeRunner.lock'; guard.parent.mkdir(parents=True, exist_ok=True)
    with guard.open('a+b') as lock:
        if os.fstat(lock.fileno()).st_size == 0:
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            parser.error('Another Ads85 native runner owns the serial lock')
        try:
            if unity_pids():
                parser.error('Concurrent Unity process refused')
            run_id = uuid.uuid4().hex; run = EVIDENCE / 'Runs' / run_id; run.mkdir(parents=True, exist_ok=False)
            frozen = freeze(); write(run / 'FrozenSources.json', frozen)
            env = dict(os.environ)
            for key in ('HOTR_ADS85_OUTPUT', 'HOTR_REWARDED_ADS85_OUTPUT', 'HOTR_SHOP_RUBLE85_OUTPUT'):
                env[key] = str(run)
            invocation = {'schemaVersion': 1, 'runId': run_id, 'status': 'RUNNING', 'startedUtc': utc(), 'runs': [],
                          'scope': 'Targeted native Editor/PlayMode suites only; individual reports define synthetic/HTTP/UI limits. No SDK/provider/payment/Android/production acceptance.',
                          'sourceSHA256': sha(run / 'FrozenSources.json'), 'inputCount': frozen['inputCount'],
                          'runnerSHA256': sha(Path(__file__)), 'unityVersion': '2022.3.62f3', 'unityExeSHA256': sha(unity),
                          'httpFixtureExternallyOwned': 'Http' in suites, 'servicesLaunchedByRunner': False, 'evidenceNeverOverwritten': True}
            code = 0
            try:
                for name in suites:
                    print('START ' + name, flush=True)
                    record = run_suite(name, run, frozen, unity, env, args.timeout_seconds)
                    invocation['runs'].append(record)
                    print('FINISH ' + name + ' ' + record['status'], flush=True)
                    if record['status'] != 'PASS':
                        code = 1; break
            except Exception as error:
                invocation['errorType'] = type(error).__name__; code = 1
            finally:
                invocation['inputsUnchanged'] = False
                invocation['unityPidsAfter'] = None
                try:
                    final = freeze(); write(run / 'Sources_final.json', final)
                    invocation['inputsUnchanged'] = unchanged(delta(frozen, final))
                    invocation['sourcesFinalSHA256'] = sha(run / 'Sources_final.json')
                    invocation['unityPidsAfter'] = unity_pids()
                except Exception as error:
                    invocation['finalFreezeErrorType'] = type(error).__name__
                    code = 1
                if not invocation['inputsUnchanged'] or invocation['unityPidsAfter']:
                    code = 1
                invocation['finishedUtc'] = utc()
                invocation['status'] = 'PASS_TARGETED_NATIVE_SHOP_ADS85' if code == 0 and len(invocation['runs']) == len(suites) else 'FAIL_TARGETED_NATIVE_SHOP_ADS85'
                write(run / 'Invocation.json', invocation)
                print('Invocation: ' + (run / 'Invocation.json').relative_to(ROOT).as_posix(), flush=True)
            return code
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    sys.exit(main())
