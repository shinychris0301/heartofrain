"""ROOT-ONLY serial SDK-free internal Android builds for checkpoint85.

Runs exactly NativeAndroidBuild.Run and NativeAndroidBuild.RunRelease. Preserves
prior default APKs in ignored cache, restores exact ProjectSettings bytes, and
restores the historical fixed Native report/log files after copying fresh build
reports into this run. Never installs/launches an APK, starts a service or uses
ADB. A non-development compile is not a production/store release.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

from run_ads85_native import (
    ROOT, UNITY_PROJECT, EVIDENCE, PINNED_UNITY, OwnedJob,
    delta, disk, freeze, sha, unchanged, unity_pids, utc, write,
)

TIMEOUT_SECONDS = 1200
SDKMANAGER_OPTS = '-Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=9 -Dhttp.proxyHost=127.0.0.1 -Dhttp.proxyPort=9 -Dsun.net.client.defaultConnectTimeout=3000 -Dsun.net.client.defaultReadTimeout=3000'
NATIVE = ROOT / 'Verification/Evidence/Native'
SETTINGS = UNITY_PROJECT / 'ProjectSettings'
APK_ROOT = UNITY_PROJECT / 'Builds/Verification'
BUILDS = (
    ('Development', 'HeartOfTheRain.Verification.NativeAndroidBuild.Run', 'Android_Build.json', 'PASS_ANDROID_DEVELOPMENT_BUILD', 'HeartOfTheRain_Development.apk'),
    ('NonDevelopment', 'HeartOfTheRain.Verification.NativeAndroidBuild.RunRelease', 'Android_Release_Build.json', 'PASS_ANDROID_RELEASE_COMPILE_BUILD', 'HeartOfTheRain_ReleaseCompile.apk'),
)
HISTORICAL = ('Android_Build.json', 'Android_Release_Build.json', 'AndroidBuild.log', 'AndroidReleaseBuild.log', 'AndroidBuild_Process.json', 'AndroidReleaseBuild_Process.json')


def require(value, code):
    if not value:
        raise RuntimeError(code)


def io_files(base):
    result = {}
    for folder, _, names in os.walk(disk(base)):
        for name in names:
            path = Path(str(Path(folder) / name).removeprefix('\\\\?\\'))
            result[path.relative_to(base).as_posix()] = path
    return result


def copy_exact(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    require(not destination.exists(), 'ArchiveDestinationAlreadyExists')
    shutil.copy2(disk(source), disk(destination))
    require(sha(source) == sha(destination), 'ArchiveCopyHashMismatch')


def settings_snapshot(cache):
    records = {}
    for relative, path in sorted(io_files(SETTINGS).items()):
        target = cache / relative
        copy_exact(path, target)
        records[relative] = {'sha256': sha(path), 'bytes': os.stat(disk(path)).st_size}
    return records


def restore_settings(cache, records):
    # Only exact files inside the explicitly named ProjectSettings directory.
    # Preserve changed/new post-build bytes separately before calling this.
    present = io_files(SETTINGS)
    for relative, record in records.items():
        original = cache / relative
        target = (SETTINGS / relative).resolve()
        require(target.is_relative_to(SETTINGS.resolve()) and sha(original) == record['sha256'], 'SettingsSnapshotCorruptOrOutsideScope')
        if target.is_file() and sha(target) == record['sha256']:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name('ads85-' + uuid.uuid4().hex + '.tmp')
        try:
            with open(disk(original), 'rb') as source, open(disk(temporary), 'xb') as output:
                shutil.copyfileobj(source, output); output.flush(); os.fsync(output.fileno())
            os.replace(disk(temporary), disk(target))
        finally:
            if temporary.exists():
                temporary.unlink()
    for relative, path in present.items():
        if relative not in records:
            require(path.resolve().is_relative_to(SETTINGS.resolve()), 'NewSettingsFileOutsideScope')
            path.unlink()
    final = {relative: {'sha256': sha(path), 'bytes': os.stat(disk(path)).st_size} for relative, path in io_files(SETTINGS).items()}
    require(final == records, 'ExactProjectSettingsRestorationFailed')


def sdk_free_inputs():
    require(not (UNITY_PROJECT / 'Assets/YandexMobileAds').exists() and not (UNITY_PROJECT / 'Assets/AdRevenue').exists(), 'VendorSdkPresentInOrdinaryProject')
    found = []
    for path in (UNITY_PROJECT / 'Assets').rglob('*'):
        if path.is_file() and path.suffix.lower() in ('.aar', '.jar') and any(word in path.name.lower() for word in ('yandex', 'mobileads', 'appmetrica')):
            found.append(path.relative_to(ROOT).as_posix())
    require(not found, 'VendorSdkBinaryPresentInOrdinaryProject')
    text = (SETTINGS / 'ProjectSettings.asset').read_text('utf-8-sig')
    match = re.search(r'(?m)^  scriptingDefineSymbols:.*(?:\n    .*|\r\n    .*)*', text)
    require(match is not None and 'HOTR_YANDEX_ADS' not in match.group(), 'ProviderSdkDefineActiveInOrdinaryProject')
    responses = {}
    for path in (UNITY_PROJECT / 'Assets').rglob('*.rsp'):
        value = path.read_text('utf-8-sig')
        require('HOTR_YANDEX_ADS' not in value, 'ProviderSdkDefineActiveInResponseFile')
        responses[path.relative_to(ROOT).as_posix()] = sha(path)
    return {'vendorTreeAbsent': True, 'matchingVendorBinariesAbsent': True, 'providerSdkDefineAbsent': True, 'responseFileSHA256': responses}


def run_build(entry, run, cache, baseline, settings_backup, setting_records, unity, environment):
    label, method, filename, success, apk_name = entry
    folder = run / label
    folder.mkdir(parents=True, exist_ok=False)
    target_report = NATIVE / filename
    apk = APK_ROOT / apk_name
    record = {'build': label, 'method': method, 'status': 'RUNNING', 'startedUtc': utc(), 'timeoutSeconds': TIMEOUT_SECONDS,
              'pid': None, 'exitCode': None, 'timedOut': False, 'processStopped': False, 'exactSettingsRestored': False,
              'inputsUnchangedAfterRestoration': False, 'ownedKillOnCloseJobAssigned': False}
    process = None; job = None; began = time.monotonic()
    log = folder / 'Unity.log'; console = folder / 'Console.log'
    try:
        before = freeze(); write(folder / 'Sources_before.json', before)
        require(unchanged(delta(baseline, before)), 'FrozenInputsChangedBeforeBuild')
        require(not unity_pids(), 'ConcurrentUnityRefused')
        # Removing only the archived fixed output prevents stale PASS/APK reuse.
        if target_report.exists():
            require(target_report.resolve().parent == NATIVE.resolve(), 'FixedNativeReportScopeInvalid')
            target_report.unlink()
        if apk.exists():
            require(apk.resolve().parent == APK_ROOT.resolve(), 'FixedApkScopeInvalid')
            apk.unlink()
        job = OwnedJob()
        with open(disk(console), 'x', encoding='utf-8') as stream:
            process = subprocess.Popen([str(unity), '-batchmode', '-buildTarget', 'Android', '-projectPath', str(UNITY_PROJECT),
                                        '-executeMethod', method, '-logFile', str(log)], env=environment,
                                       stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            record['pid'] = process.pid; job.assign(process.pid); record['ownedKillOnCloseJobAssigned'] = True
            try:
                process.wait(timeout=TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                record['timedOut'] = True; job.close(); process.wait(timeout=20)
            record['exitCode'] = process.returncode
        if target_report.is_file():
            copy_exact(target_report, folder / filename)
            native = json.loads((folder / filename).read_text('utf-8-sig'))
            record.update(nativeStatus=native.get('status'), nativeReportSHA256=sha(folder / filename))
            require(native.get('status') == success and native.get('errors') == 0 and not native.get('error'), 'ActualInternalBuildReportNotPassed')
            require(native.get('unity') == '2022.3.62f3' and Path(native.get('output', '')).resolve() == apk.resolve(), 'NativeBuildOutputBindingInvalid')
            # Unity's totalSize can include symbols/intermediate products; it
            # is not the size of the APK. The old path was removed above, so
            # this owned fresh output is independently hashed and inspected.
            require(apk.is_file() and apk.stat().st_size > 0 and native.get('bytes',0) > 0, 'FreshInternalApkMissingOrSizeMismatch')
            record['unityReportedBuildTotalBytes']=native['bytes']
            record['apk'] = {'path': apk.relative_to(ROOT).as_posix(), 'sha256': sha(apk), 'bytes': apk.stat().st_size}
        else:
            raise RuntimeError('FreshNativeBuildReportMissing')
        require(not record['timedOut'] and record['exitCode'] == 0, 'NativeBuildProcessNotPassed')
        record['status'] = 'PASS_INTERNAL_BUILD85'
    except Exception as error:
        record['status'] = 'FAIL_INTERNAL_BUILD85'
        record['errorCode'] = str(error) if type(error) is RuntimeError and re.fullmatch('[A-Za-z0-9]+', str(error)) else type(error).__name__
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=10)
        record['processStopped'] = process is None or process.poll() is not None
        if process:
            record['exitCode'] = process.poll()
        # Copy even failed/partial reports before historical reports are restored.
        try:
            if target_report.is_file() and not (folder / filename).exists():
                copy_exact(target_report, folder / filename)
                record['nativeReportSHA256'] = sha(folder / filename)
            if apk.is_file() and 'apk' not in record:
                record['failedOrUnacceptedApk'] = {'path': apk.relative_to(ROOT).as_posix(), 'sha256': sha(apk), 'bytes': apk.stat().st_size}
        except Exception as error:
            record['status'] = 'FAIL_INTERNAL_BUILD85'
            record['artifactCaptureErrorType'] = type(error).__name__
        try:
            require(record['processStopped'] and not unity_pids(), 'CannotRestoreWhileUnityRemains')
            raw_settings = cache / label / 'Settings_after_child'
            try:
                raw = settings_snapshot(raw_settings); write(folder / 'Settings_after_child.json', raw)
            except Exception as error:
                record['status'] = 'FAIL_INTERNAL_BUILD85'
                record['postChildSettingsCaptureErrorType'] = type(error).__name__
            restore_settings(settings_backup, setting_records)
            record['exactSettingsRestored'] = True
            after = freeze(); write(folder / 'Sources_after_restore.json', after)
            changes = delta(baseline, after); write(folder / 'Source_Delta.json', changes)
            record['inputsUnchangedAfterRestoration'] = unchanged(changes)
            record['sourcesAfterSHA256'] = sha(folder / 'Sources_after_restore.json')
            require(record['inputsUnchangedAfterRestoration'], 'UnityInputsChangedAfterSettingsRestore')
            record['sdkFreeInputProof'] = sdk_free_inputs()
        except Exception as error:
            record['status'] = 'FAIL_INPUT_OR_SETTINGS_RESTORATION85'
            record['restoreErrorType'] = type(error).__name__
        record['finishedUtc'] = utc(); record['elapsedSeconds'] = round(time.monotonic() - began, 3)
        record['unityLogSHA256'] = sha(log) if log.is_file() else None
        record['consoleSHA256'] = sha(console) if console.is_file() else None
        write(folder / 'Process.json', record)
    return record


def run(args):
    require(os.name == 'nt' and args.execute, 'ExplicitWindowsRootExecutionRequired')
    unity = args.unity.resolve()
    require(unity == PINNED_UNITY.resolve() and unity.is_file(), 'PinnedUnityExecutableRequired')
    require(os.environ.get('HOTR_BUILD_CHANNEL') != 'rustore', 'ProductionBuildChannelForbidden')
    require(not unity_pids(), 'ConcurrentUnityRefused')
    import msvcrt
    lock_path = ROOT / '.verification-cache/ShopAds85/NativeRunner.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+b') as lock:
        if os.fstat(lock.fileno()).st_size == 0:
            lock.write(b'0'); lock.flush()
        lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            require(not unity_pids(), 'ConcurrentUnityRefused')
            run_id = uuid.uuid4().hex
            output = EVIDENCE / 'Builds' / run_id; output.mkdir(parents=True, exist_ok=False)
            cache = ROOT / '.verification-cache/Ads85/InternalBuilds' / run_id; cache.mkdir(parents=True, exist_ok=False)
            baseline = freeze(); write(output / 'FrozenSources.json', baseline)
            settings_backup = cache / 'ProjectSettings_before'
            setting_records = settings_snapshot(settings_backup)
            write(output / 'Settings_before.json', setting_records)
            historical = {}
            for filename in HISTORICAL:
                source = NATIVE / filename
                historical[filename] = {'existed': source.is_file()}
                if source.is_file():
                    copy_exact(source, cache / 'HistoricalNative' / filename)
                    historical[filename]['sha256'] = sha(source)
            prior_apks = {}
            for _, _, _, _, filename in BUILDS:
                source = APK_ROOT / filename
                prior_apks[filename] = {'existed': source.is_file()}
                if source.is_file():
                    saved = cache / 'PriorApks' / filename
                    copy_exact(source, saved)
                    prior_apks[filename].update(path=saved.relative_to(ROOT).as_posix(), sha256=sha(source), bytes=source.stat().st_size)
            report = {'status': 'RUNNING', 'runId': run_id, 'startedUtc': utc(), 'runs': [],
                      'runnerSHA256': sha(Path(__file__)), 'sharedNativeRunnerSHA256': sha(Path(__file__).with_name('run_ads85_native.py')),
                      'sourceSHA256': sha(output / 'FrozenSources.json'), 'inputCount': baseline['inputCount'], 'unityExeSHA256': sha(unity),
                      'historicalNativeBefore': historical, 'archivedPriorApks': prior_apks, 'sdkFreeInputProof': sdk_free_inputs(),
                      'timeoutPerBuildSeconds': TIMEOUT_SECONDS, 'apkInstalledOrLaunched': False, 'servicesStarted': False,
                      'scope': 'Two serial SDK-free internal Android IL2CPP ARM64 development/non-development compilations. The optional Yandex provider remains uncompiled/dormant without its SDK define. No production signing, store release, SDK/provider/ad/payment execution, Android installation, first-start/touch/gameplay, physical-device or performance certification. Previous default APKs are retained in ignored cache; new accepted85 APKs stay at their ordinary default paths. A failed build can leave its default output missing or unaccepted; prior copies remain available.'}
            environment = dict(os.environ); environment['SDKMANAGER_OPTS'] = SDKMANAGER_OPTS
            try:
                for entry in BUILDS:
                    print('START ' + entry[0], flush=True)
                    record = run_build(entry, output, cache, baseline, settings_backup, setting_records, unity, environment)
                    report['runs'].append(record)
                    print('FINISH ' + entry[0] + ' ' + record['status'], flush=True)
                    if record['status'] != 'PASS_INTERNAL_BUILD85':
                        break
            except Exception as error:
                report['errorType'] = type(error).__name__
            finally:
                restored = {}
                for filename, old in historical.items():
                    target = NATIVE / filename
                    try:
                        require(not unity_pids(), 'CannotRestoreEvidenceWhileUnityRemains')
                        if old['existed']:
                            saved = cache / 'HistoricalNative' / filename
                            require(sha(saved) == old['sha256'], 'HistoricalNativeBackupChanged')
                            if not target.is_file() or sha(target) != old['sha256']:
                                target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(disk(saved), disk(target))
                            restored[filename] = target.is_file() and sha(target) == old['sha256']
                        else:
                            if target.exists():
                                require(target.resolve().parent == NATIVE.resolve(), 'HistoricalNativeRestoreOutsideScope'); target.unlink()
                            restored[filename] = not target.exists()
                    except Exception:
                        restored[filename] = False
                report['historicalNativeRestored'] = restored
                report['allHistoricalNativeRestored'] = all(restored.values())
                report['inputsUnchangedAfterSettingsRestore'] = False
                try:
                    final = freeze(); write(output / 'Sources_final.json', final)
                    report['inputsUnchangedAfterSettingsRestore'] = unchanged(delta(baseline, final))
                    report['sourcesFinalSHA256'] = sha(output / 'Sources_final.json')
                    report['unityPidsAfter'] = unity_pids()
                except Exception as error:
                    report['finalAuditErrorType'] = type(error).__name__
                    report['unityPidsAfter'] = None
                report['finishedUtc'] = utc()
                report['status'] = ('PASS_SDK_FREE_INTERNAL_ANDROID_BUILDS85' if len(report['runs']) == 2 and all(row['status'] == 'PASS_INTERNAL_BUILD85' for row in report['runs']) and report['allHistoricalNativeRestored'] and report['inputsUnchangedAfterSettingsRestore'] and report['unityPidsAfter']==[] else 'FAIL_SDK_FREE_INTERNAL_ANDROID_BUILDS85')
                write(output / 'Invocation.json', report)
            return output, report
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--unity', type=Path, default=PINNED_UNITY)
    args = parser.parse_args()
    output, report = run(args)
    print(json.dumps({'status': report['status'], 'report': (output / 'Invocation.json').relative_to(ROOT).as_posix()}))
    raise SystemExit(0 if report['status'].startswith('PASS_') else 1)


if __name__ == '__main__':
    main()
