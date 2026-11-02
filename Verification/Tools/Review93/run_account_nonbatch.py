"""Bounded root-only non-batch Account contracts diagnostic, unchanged C# tests.

No device, backend, clipboard or process action occurs on import. The unchanged
suite owns its explicit clipboard test and restores the previous contents in
its finally block before writing the completed report. This helper never reads
clipboard contents. No existing runner, runtime, test or project input is edited.
"""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review93/NonBatch'
ENTRY = 'HeartOfTheRain.Verification.ServerAccount83Verification.Run'
EXPECTED = 'PASS_NATIVE_SERVER_ACCOUNT83_CONTRACTS'
TEST = ROOT / 'Unity/Assets/HeartOfTheRain/App/ServerAccount/Editor/ServerAccount83Verification.cs'


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def command(unity, project, log):
    return [str(unity), '-projectPath', str(project), '-executeMethod', ENTRY, '-logFile', str(log)]


def classify(native_passed, forced_cleanup, normal_exit, unchanged, mode_zero):
    if not unchanged or not mode_zero:
        return 'FAIL_NONBATCH_ACCOUNT93_SOURCE_OR_MODE'
    if forced_cleanup:
        return 'RECORDED_NONBATCH_ACCOUNT93_FORCED_CLEANUP'
    if not normal_exit:
        return 'FAIL_NONBATCH_ACCOUNT93_PROCESS_CLEANUP'
    return 'RECORDED_NONBATCH_ACCOUNT93_NATIVE_ASSERTIONS_PASSED' if native_passed else 'RECORDED_NONBATCH_ACCOUNT93_NATIVE_ASSERTIONS_FAILED'


def read_native(path, began):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        return None
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError('DuplicateNativeReportKey')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('NonfiniteNativeReport')
    result = json.loads(path.read_text('utf-8-sig'), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(result, dict) or result.get('status') not in (EXPECTED, 'FAIL_NATIVE_SERVER_ACCOUNT83_CONTRACTS'):
        return None
    stamp = datetime.fromisoformat(result['utc'].replace('Z', '+00:00'))
    if stamp.tzinfo is None or stamp < began:
        raise ValueError('FreshTimezoneNativeReportRequired')
    if result.get('unity') != '2022.3.62f3' or type(result.get('checks')) is not int or result['checks'] <= 0 or not isinstance(result.get('errors'), list):
        raise ValueError('ActualContractsNativeReportRequired')
    return result


def passed(native):
    return bool(native and native.get('status') == EXPECTED and native.get('errors') == []
                and native.get('cases') == len(native.get('passed', [])) == 8
                and native.get('copyCalls') == 1 and native.get('copyScreen') == 'backup'
                and native.get('clipboardReadbackLength') == 43 and native.get('clipboardReadbackMatched') is True)


def close_owned_windows(process, expected_image, process_reader):
    """WM_CLOSE only top-level windows owned by this exact child Editor PID."""
    if process.poll() is not None:
        return {'ownedWindows': 0, 'closeMessagesPosted': 0, 'processAlreadyExited': True}
    image, _ = process_reader(process.pid)
    if Path(image).resolve() != Path(expected_image).resolve():
        raise RuntimeError('OwnedEditorImageChangedBeforeClose')
    user = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes, user.EnumWindows.restype = [callback_type, wintypes.LPARAM], wintypes.BOOL
    user.GetWindowThreadProcessId.argtypes, user.GetWindowThreadProcessId.restype = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD
    user.PostMessageW.argtypes, user.PostMessageW.restype = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL
    windows = []
    @callback_type
    def visit(window, parameter):
        owner = wintypes.DWORD()
        user.GetWindowThreadProcessId(window, ctypes.byref(owner))
        if owner.value == process.pid:
            windows.append(window)
        return True
    if not user.EnumWindows(visit, 0):
        raise RuntimeError('OwnedEditorWindowEnumerationFailed')
    posted = 0
    for window in windows:
        owner = wintypes.DWORD()
        user.GetWindowThreadProcessId(window, ctypes.byref(owner))
        if owner.value != process.pid:
            raise RuntimeError('OwnedEditorWindowChangedBeforeClose')
        if user.PostMessageW(window, 0x10, 0, 0):
            posted += 1
    return {'ownedWindows': len(windows), 'closeMessagesPosted': posted,
            'scope': 'WM_CLOSE posted only to windows rechecked against the exact owned Editor PID/image; no keystrokes, other processes or clipboard API calls.'}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--execute', action='store_true')
    cli.add_argument('--visible-window', action='store_true', help='Explicitly show the diagnostic Editor without requesting foreground focus.')
    cli.add_argument('--timeout', type=int, default=180)
    args = cli.parse_args()
    if not args.execute or os.name != 'nt' or not 60 <= args.timeout <= 600:
        cli.error('Explicit bounded root Windows diagnostic execution required')
    shared = module('hotr93_nonbatch_shared', 'Verification/Tools/Ads85/run_ads85_native.py')
    # process90 imports the shared helper by its normal name; use its unchanged path.
    sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
    selector = module('hotr93_nonbatch_process_selector', 'Verification/Tools/PageBackdrop90/process90.py')
    connected = module('hotr93_nonbatch_owned_resume', 'Verification/Tools/Review93/run_connected.py')
    if not shared.PINNED_UNITY.is_file() or selector.unity_pids() or 'm_EditorVersion: 2022.3.62f3' not in (shared.UNITY_PROJECT / 'ProjectSettings/ProjectVersion.txt').read_text('utf-8-sig'):
        cli.error('Pinned Editor required without another Unity process')
    folder = OUT / ('Account_' + uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=False)
    log, console, native_path = folder / 'Unity.log', folder / 'Console.log', folder / 'Native/AccountContracts.json'
    frozen = shared.freeze()
    shared.write(folder / 'FrozenSources.json', frozen)
    def binding(path):
        path = Path(path)
        return {'path': path.resolve().relative_to(ROOT).as_posix(), 'sha256': shared.sha(path), 'bytes': path.stat().st_size}
    record = {'schemaVersion': 1, 'checkpoint': 93, 'status': 'RUNNING', 'startedUtc': shared.utc(),
        'entry': ENTRY, 'command': command(shared.PINNED_UNITY, shared.UNITY_PROJECT, log), 'batchModeRequested': False,
        'windowStartup': 'VISIBLE_WITHOUT_FOCUS_REQUEST' if args.visible_window else 'HIDDEN', 'timeoutSeconds': args.timeout,
        'closeGraceSeconds': 15, 'runner': binding(Path(__file__)), 'nativeTestSource': binding(TEST),
        'sharedProcessHelper': binding(ROOT / 'Verification/Tools/Ads85/run_ads85_native.py'),
        'processSelector': binding(ROOT / 'Verification/Tools/PageBackdrop90/process90.py'),
        'ownedResumeHelper': binding(ROOT / 'Verification/Tools/Review93/run_connected.py'),
        'sourceManifest': binding(folder / 'FrozenSources.json'), 'inputCount': frozen['inputCount'],
        'unityExeSHA256': shared.sha(shared.PINNED_UNITY), 'clipboardBytesExported': False,
        'scope': 'Separate non-batch pinned Editor diagnostic running the unchanged strict synthetic Account contracts. No HTTP, Android, account recovery/deletion, backend deployment or production acceptance. Native assertions and host cleanup classification remain separate; original batch failures are retained.'}
    helper_keys = ('runner', 'nativeTestSource', 'sharedProcessHelper', 'processSelector', 'ownedResumeHelper')
    shared.write(folder / 'Authorization.json', record)
    environment = dict(os.environ, HOTR_SERVER_GAMEPLAY_OUTPUT=str(folder), HOTR_REVIEW93_OUT=str(folder))
    process = job = None
    native = None
    force = False
    began = datetime.now(timezone.utc)
    started = time.monotonic()
    try:
        job = shared.OwnedJob()
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 4 if args.visible_window else 0  # SW_SHOWNOACTIVATE / SW_HIDE
        with console.open('x', encoding='utf-8') as output:
            process = subprocess.Popen(record['command'], cwd=ROOT, env=environment, stdout=output, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW | 0x4, startupinfo=startup)
            record['pid'] = process.pid
            job.assign(process.pid)
            record['ownedKillOnCloseJobAssignedBeforeResume'] = True
            connected.resume_owned_primary(process)
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    native = read_native(native_path, began)
                    break
                try:
                    native = read_native(native_path, began)
                except json.JSONDecodeError:
                    native = None  # File.WriteAllText may still be finishing; never accept a partial report.
                if native is not None:
                    report_hash = shared.sha(native_path)
                    time.sleep(.25)
                    if shared.sha(native_path) != report_hash:
                        raise RuntimeError('CompletedNativeReportChanged')
                    record['nativeCompletionObservedUtc'] = shared.utc()
                    break
                time.sleep(.25)
            if native is None:
                record['timedOutOrMissingNativeReport'] = True
            else:
                record.update(nativeReport=binding(native_path), nativeStatus=native['status'], nativeErrors=native['errors'],
                    checks=native['checks'], cases=native.get('cases'), nativeAssertionsPassed=passed(native),
                    clipboardObservation={'copyCalls': native.get('copyCalls'), 'readbackLength': native.get('clipboardReadbackLength'),
                                          'readbackMatched': native.get('clipboardReadbackMatched'), 'warningScreen': native.get('copyScreen')},
                    clipboardRestoreSourceFact='The unchanged test saves the previous clipboard in memory and restores it in its finally before emitting this completed report; the helper never reads, writes or exports clipboard contents.')
            record['closeRequest'] = close_owned_windows(process, shared.PINNED_UNITY, selector.process_details)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                force = True
                record['forcedCleanupReason'] = 'Owned Editor did not exit within WM_CLOSE grace; unchanged non-batch C# suite intentionally has no EditorApplication.Exit call.'
    except Exception as error:
        record.update(runnerFailureType=type(error).__name__)
        if isinstance(error, (ValueError, RuntimeError)) and re.fullmatch('[A-Za-z0-9]+', str(error)):
            record['runnerFailureCategory'] = str(error)
    finally:
        if process and process.poll() is None:
            force = True
        cleanup_errors = []
        try:
            if job:
                job.close()
        except Exception as error:
            cleanup_errors.append('OwnedJobClose' + type(error).__name__)
        try:
            if process and process.poll() is None:
                process.kill()
            if process:
                process.wait(timeout=20)
        except Exception as error:
            cleanup_errors.append('OwnedEditorWait' + type(error).__name__)
        after = shared.freeze()
        shared.write(folder / 'Sources_after.json', after)
        changes = shared.delta(frozen, after)
        shared.write(folder / 'Source_Delta.json', changes)
        mode = re.search(r'(?m)^BatchMode:\s*(\d+)', log.read_text('utf-8-sig', errors='replace')) if log.is_file() else None
        mode_zero = mode is not None and mode.group(1) == '0'
        normal_exit = bool(process and process.returncode == 0 and not force and not cleanup_errors)
        helpers_after = {key: binding(ROOT / record[key]['path']) if (ROOT / record[key]['path']).is_file() else None for key in helper_keys}
        helpers_unchanged = all(record[key] == helpers_after[key] for key in helper_keys)
        record.update(forcedCleanup=force, editorClosedNormally=normal_exit, exitCode=process.returncode if process else None,
            actualBatchMode=int(mode.group(1)) if mode else None, inputsUnchanged=shared.unchanged(changes),
            helperBindingsAfter=helpers_after, helpersUnchanged=helpers_unchanged, cleanupErrors=cleanup_errors,
            sourcesAfter=binding(folder / 'Sources_after.json'), sourceDelta=binding(folder / 'Source_Delta.json'),
            unityPidsAfter=selector.unity_pids(), finishedUtc=shared.utc(), elapsedSeconds=round(time.monotonic() - started, 3),
            unityLog=binding(log) if log.is_file() else None, consoleLog=binding(console) if console.is_file() else None)
        record['status'] = classify(passed(native), force, normal_exit, record['inputsUnchanged'] and helpers_unchanged, mode_zero)
        if record.get('runnerFailureType') or record.get('timedOutOrMissingNativeReport') or record['unityPidsAfter'] or cleanup_errors:
            record['status'] = 'FAIL_NONBATCH_ACCOUNT93_RUNNER'
        shared.write(folder / 'Invocation.json', record)
    print(json.dumps({'status': record['status'], 'nativeStatus': record.get('nativeStatus'), 'forcedCleanup': force,
                      'invocation': (folder / 'Invocation.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if record['status'] == 'RECORDED_NONBATCH_ACCOUNT93_NATIVE_ASSERTIONS_PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
