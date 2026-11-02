"""Root-only serial pinned Editor review suites, with independent current inputs.

Uses only generic hashing/process-containment helpers from the immutable85
runner. No Android installation, SDK import, production enablement or service
startup is implied. HTTP suites require root-owned fresh loopback services.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import (OwnedJob, PINNED_UNITY, UNITY_PROJECT, delta,
                             disk, freeze, sha, unchanged, unity_pids as named_unity_pids, utc, write)


def unity_pids():
    # Recent Hub versions also name their background service unity.exe. It is
    # not an Editor and must not be stopped. Exclude only that exact installed
    # binary; every other matching process (including unknown paths) blocks us.
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    hub = Path(r'C:\Program Files\Unity Hub\resources\unity.exe').resolve()
    editors = []
    for pid in named_unity_pids():
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            raise RuntimeError('UnityProcessImageUnavailable')
        try:
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                raise RuntimeError('UnityProcessImageUnavailable')
            if Path(buffer.value).resolve() != hub:
                editors.append(pid)
        finally:
            kernel.CloseHandle(handle)
    return editors

PREFIX = 'HeartOfTheRain.Verification.'
# entry, relative report, success, Play Mode, timeout seconds
SUITES = {
    'Capacity': ('ServerCapacity86Verification.Run', 'Native/ServerCapacity86.json', 'PASS_NATIVE_SERVER_CAPACITY86', True, 240),
    'Checkout': ('ShopCheckout86Verification.Run', 'Native/ShopCheckout86.json', 'PASS_NATIVE_SHOP_CHECKOUT86', False, 300),
    'Lifecycle': ('ClientLifecycle86Verification.Run', 'Native/ClientLifecycle86.json', 'PASS_NATIVE_CLIENT_LIFECYCLE86', True, 240),
    'Recovery': ('PayRecovery86Verification.Run', 'Native/PayRecovery86.json', 'PASS_NATIVE_PAY_RECOVERY86', False, 180),
    'Guard': ('RuStore81Verification.Run', 'Native/RuStore81.json', 'PASS_NATIVE_RUSTORE81_RELEASE_GUARD', False, 180),
    'Identity': ('Identity82Verification.Run', 'Native/Identity82.json', 'PASS_NATIVE_IDENTITY82', False, 180),
    'ServerCore': ('ServerGameplay83Verification.Run', 'Native/ServerGameplay.json', 'PASS_NATIVE_SERVER_GAMEPLAY83_CORE', False, 180),
    'Account': ('ServerAccount83Verification.Run', 'Native/AccountContracts.json', 'PASS_NATIVE_SERVER_ACCOUNT83_CONTRACTS', True, 240),
    'Rubles': ('ShopRuble85Verification.Run', 'Native/ShopRuble85.json', 'PASS_NATIVE_SHOP_RUBLE85_PREVIEW', True, 300),
    'AdFlow': ('RewardedAdsFlow85Verification.Run', 'Native/RewardedAdsFlow85.json', 'PASS_NATIVE_REWARDED_ADS_FLOW85', False, 240),
    'ServerHttp': ('ServerGameplay83HttpVerification.Run', 'Native/ConnectedHTTP.json', 'PASS_NATIVE_SERVER_GAMEPLAY83_CONNECTED_HTTP', True, 360),
    'AccountHttp': ('ServerAccount83HttpVerification.Run', 'Native/AccountHTTP.json', 'PASS_NATIVE_SERVER_ACCOUNT83_CONNECTED_HTTP', True, 300),
    'SocialHttp': ('Social82Verification.RunHttp', 'Native/Social82_HTTP.json', 'PASS_NATIVE_SOCIAL82_HTTP', True, 300),
    'IdentityHttp': ('Identity82Verification.RunHttp', 'Native/Identity82_HTTP.json', 'PASS_NATIVE_IDENTITY82_HTTP', True, 240),
    'PayHttp': ('RuStore81Verification.RunHttp', 'Native/HTTP.json', 'PASS_NATIVE_RUSTORE81_HTTP_STAGING_CLIENT', False, 240),
}
OUTPUT_ENV = ('HOTR_CAPACITY86_OUTPUT', 'HOTR_CHECKOUT86_OUTPUT', 'HOTR_REVIEW86_OUTPUT', 'HOTR_CLIENT86_OUTPUT', 'HOTR_RUSTORE81_OUTPUT',
              'HOTR_IDENTITY82_OUTPUT', 'HOTR_SERVER_GAMEPLAY_OUTPUT', 'HOTR_SOCIAL82_OUTPUT',
              'HOTR_SHOP_RUBLE85_OUTPUT', 'HOTR_REWARDED_ADS85_OUTPUT', 'HOTR_ADS85_OUTPUT')


def run_suite(name, run, baseline, env):
    entry, relative, expected, play, timeout = SUITES[name]
    folder = run / 'Suites' / name
    folder.mkdir(parents=True, exist_ok=False)
    before = freeze()
    write(folder / 'Sources_before.json', before)
    if not unchanged(delta(baseline, before)) or unity_pids():
        raise RuntimeError('InputsChangedOrConcurrentUnity')
    log, console = folder / 'Unity.log', folder / 'Console.log'
    report_path = run / relative
    synchronous_exit = name == 'ServerCore'
    record = {'suite': name, 'entry': PREFIX + entry, 'status': 'RUNNING',
              'startedUtc': utc(), 'playMode': play, 'quitFlag': synchronous_exit,
              'timeoutSeconds': timeout, 'timedOut': False, 'pid': None,
              'sourcesBeforeSHA256': sha(folder / 'Sources_before.json')}
    process = job = None
    started = time.monotonic()
    try:
        job = OwnedJob()
        with open(disk(console), 'x', encoding='utf-8') as stream:
            command = [str(PINNED_UNITY), '-batchmode', '-projectPath', str(UNITY_PROJECT),
                       '-executeMethod', PREFIX + entry, '-logFile', str(log)]
            if synchronous_exit:
                command.append('-quit')
            process = subprocess.Popen(command,
                                       env=env, stdout=stream, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            record['pid'] = process.pid
            job.assign(process.pid)
            record['ownedKillOnCloseJobAssigned'] = True
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                record['timedOut'] = True
                job.close()
                process.wait(timeout=20)
        record['exitCode'] = process.returncode
        native = json.loads(report_path.read_text('utf-8-sig')) if report_path.is_file() else {}
        record.update(nativeStatus=native.get('status', 'MISSING'),
                      nativeErrorsEmpty=not native.get('errors') and not native.get('error'),
                      nativeReportSHA256=sha(report_path) if report_path.is_file() else None,
                      checks=native.get('checks'), cases=native.get('cases'))
        captures = {}
        for relative_capture in native.get('captures', []):
            capture = (run / relative_capture).resolve()
            if not capture.is_relative_to(run.resolve()) or not capture.is_file():
                raise RuntimeError('CaptureMissingOrOutsideRun')
            captures[relative_capture] = sha(capture)
        record['captures'] = captures
        record['status'] = ('PASS' if process.returncode == 0 and not record['timedOut']
                            and record['nativeStatus'] == expected and record['nativeErrorsEmpty'] else 'FAIL_NATIVE')
    except Exception as error:
        record.update(status='FAIL_RUNNER', errorType=type(error).__name__)
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        record.update(processStopped=process is None or process.poll() is not None,
                      unityLogSHA256=sha(log) if log.is_file() else None,
                      consoleSHA256=sha(console) if console.is_file() else None,
                      finishedUtc=utc(), elapsedSeconds=round(time.monotonic() - started, 3))
        after = freeze()
        write(folder / 'Sources_after.json', after)
        changes = delta(before, after)
        write(folder / 'Source_Delta.json', changes)
        record['inputsUnchanged'] = unchanged(changes) and unchanged(delta(baseline, after))
        if not record['inputsUnchanged']:
            record['status'] = 'FAIL_INPUT_MUTATION'
        record['sourcesAfterSHA256'] = sha(folder / 'Sources_after.json')
        write(folder / 'Process.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suites', default='Lifecycle,Recovery,Checkout,Capacity,Guard,Identity,ServerCore,Account,Rubles,AdFlow')
    args = parser.parse_args()
    names = args.suites.split(',')
    if os.name != 'nt' or not names or len(set(names)) != len(names) or any(n not in SUITES for n in names):
        parser.error('Windows root execution with unique supported suites required')
    if not PINNED_UNITY.is_file() or unity_pids():
        parser.error('Pinned Editor required, with no concurrent Unity process')
    if 'm_EditorVersion: 2022.3.62f3' not in (UNITY_PROJECT / 'ProjectSettings/ProjectVersion.txt').read_text('utf-8-sig'):
        parser.error('Pinned project engine changed')
    run = ROOT / 'Verification/Evidence/Review86/NativeRuns' / uuid.uuid4().hex
    run.mkdir(parents=True, exist_ok=False)
    tools = run / 'RunnerInputs'
    tools.mkdir()
    for source in (Path(__file__), ROOT / 'Verification/Tools/Ads85/run_ads85_native.py'):
        shutil.copy2(source, tools / source.name)
    frozen = freeze()
    write(run / 'FrozenSources.json', frozen)
    env = dict(os.environ)
    for key in OUTPUT_ENV:
        env[key] = str(run)
    result = {'status': 'RUNNING', 'startedUtc': utc(), 'runs': [], 'runnerSHA256': sha(Path(__file__)),
              'processHelperSHA256': sha(ROOT / 'Verification/Tools/Ads85/run_ads85_native.py'),
              'inputCount': frozen['inputCount'], 'sourceSHA256': sha(run / 'FrozenSources.json'),
              'unityExeSHA256': sha(PINNED_UNITY),
              'scope': 'Actual pinned Unity Editor processes on current frozen inputs. Each native report distinguishes real files/HTTP from doubles. No Android/device, live payment, hosted deployment or whole-game performance certification.'}
    try:
        for name in names:
            print('START ' + name, flush=True)
            record = run_suite(name, run, frozen, env)
            result['runs'].append(record)
            print('FINISH ' + name + ' ' + record['status'], flush=True)
            # Independent reports can expose several defects in one serial
            # pass. Stop on compilation/missing reports, process containment or
            # source drift; retain ordinary reported failures and run the rest.
            if record['status'] != 'PASS' and (not record.get('inputsUnchanged') or not record.get('processStopped')
                                              or record.get('nativeStatus') == 'MISSING'):
                break
    finally:
        result.update(finishedUtc=utc(), unityPidsAfter=unity_pids())
        result['status'] = ('PASS_NATIVE_REVIEW86' if len(result['runs']) == len(names)
                            and all(r['status'] == 'PASS' for r in result['runs']) and not result['unityPidsAfter'] else 'FAIL_NATIVE_REVIEW86')
        write(run / 'Invocation.json', result)
        print(json.dumps({'status': result['status'], 'report': (run / 'Invocation.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
