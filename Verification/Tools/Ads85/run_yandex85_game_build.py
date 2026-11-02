"""ROOT-ONLY full-game Yandex85 clone export/assembly, never app/SDK execution.

Export uses pinned Unity2022.3.62f3/embedded Java11. Assembly derives the
reviewed modern Gradle profile and requires explicitly supplied Java17 and
Gradle8.9 matching an actual passed SDK-fixture assembly. Only the prepared
cache clone is writable. No SDK-fixture CLI/package guard is reused.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

import prepare_yandex85_game as game
from run_ads85_native import OwnedJob, PINNED_UNITY, unity_pids, utc, write
from run_yandex85_sdk_build import SDKMANAGER_OPTS

ROOT, CACHE = game.ROOT, game.CACHE
TIMEOUT = 1800
WINDOWS_ENVIRONMENT = {'SYSTEMROOT', 'SYSTEMDRIVE', 'WINDIR', 'TEMP', 'TMP', 'COMSPEC', 'PATH', 'PATHEXT', 'USERPROFILE', 'USERNAME', 'HOMEDRIVE', 'HOMEPATH', 'APPDATA', 'LOCALAPPDATA', 'ALLUSERSPROFILE', 'PUBLIC', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMW6432', 'COMMONPROGRAMFILES', 'COMMONPROGRAMFILES(X86)', 'COMMONPROGRAMW6432', 'PROGRAMDATA', 'OS', 'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS'}


def require(value, code):
    if not value:
        raise RuntimeError(code)


def read(path):
    with open(game.io(path), 'r', encoding='utf-8-sig') as stream:
        return json.load(stream)


def check_paths(root, records):
    for relative, expected in records.items():
        target = (root / relative).resolve()
        require(target.is_relative_to(root.resolve()) and os.path.isfile(game.io(target)), 'BOUND_INPUT_MISSING_OR_OUTSIDE_ROOT')
        require(game.sha(target) == expected, 'BOUND_INPUT_CHANGED')


def validate_project(project, prepared, after_export=False):
    require(project.parent == CACHE.resolve() and re.fullmatch(r'(?:GameProject_[0-9a-f]{32}|G85_[0-9a-f]{8})', project.name), 'PREPARED_GAME_CLONE_REQUIRED')
    require(prepared['status'] == 'PREPARED_ISOLATED_YANDEX85_FULL_GAME_NOT_BUILT' and prepared['package'] == game.GAME_PACKAGE and prepared['unity'] == '2022.3.62f3' and prepared['configurationProvisioned'] is False and prepared['apkLaunched'] is False, 'GAME_PREPARATION_CONTRACT_INVALID')
    require(prepared['project'] == project.relative_to(ROOT).as_posix(), 'GAME_PREPARATION_PATH_INVALID')
    require(game.sha(project / 'SourceInputs.json') == prepared['sourceManifestSHA256'] and read(project / 'SourceInputs.json') == prepared['sourceInputs'], 'CLONE_SOURCE_MANIFEST_CHANGED')
    require(game.manifest() == prepared['sourceInputs'] and len(prepared['sourceInputs']) == prepared['sourceInputCount'], 'MAIN_SOURCE_NO_LONGER_MATCHES_CLONE_BASELINE')
    originals = {relative: expected for relative, expected in prepared['copiedMainSHA256'].items() if relative not in prepared['generatedSHA256'] and not (after_export and relative.startswith('ProjectSettings/'))}
    generated = {relative: expected for relative, expected in prepared['generatedSHA256'].items() if not (after_export and relative.startswith('ProjectSettings/'))}
    check_paths(project, originals); check_paths(project, prepared['copiedVendorSHA256']); check_paths(project, generated)
    profile = read(project / 'GameAds85Profile.json')
    require(profile['package'] == game.GAME_PACKAGE and profile['configurationProvisioned'] is False and profile['enabledScenes'] == prepared['enabledScenes'], 'ACTUAL_GAME_SCENE_PROFILE_INVALID')
    response = (project / 'Assets/csc.rsp').read_text('utf-8-sig')
    require('HOTR_YANDEX_ADS' in response and 'HOTR_YANDEX_ADS_ISOLATED_FIXTURE' not in response, 'GAME_SDK_DEFINE_OR_NO_DEMO_POLICY_INVALID')


def exported(project):
    path = project / 'GameAndroidExport.json'
    value = read(path)
    require(value['status'] == 'PASS_ISOLATED_YANDEX85_GAME_GRADLE_EXPORT' and value['package'] == game.GAME_PACKAGE and value['unity'] == '2022.3.62f3' and value['errors'] == 0, 'PASSED_GAME_EXPORT_REQUIRED')
    for key in ('fullGame', 'development', 'jdkSettingsUnchanged', 'actualAdapterSdkBranchCompiled', 'portraitOnly', 'enabledScenesUnchanged', 'noSdkInitializationOrAdRequests'):
        require(value.get(key) is True, 'GAME_EXPORT_REQUIRED_FLAG_MISSING')
    require(value['configurationProvisioned'] is False and value['apkLaunched'] is False and value['productNameBefore'] == value['productNameAfter'], 'GAME_EXPORT_CONFIG_OR_BRANDING_CHANGED')
    require(Path(value['output']).resolve() == (project / 'Build/GameGradleExport').resolve(), 'GAME_EXPORT_OUTPUT_INVALID')
    return path, value


def execute(name, arguments, environment, cwd, attempt, report):
    require(not unity_pids(), 'CONCURRENT_UNITY_REFUSED')
    log = attempt / (name + '.log')
    row = {'name': name, 'startedUtc': utc(), 'timeoutSeconds': TIMEOUT, 'hidden': True, 'pid': None, 'timedOut': False, 'ownedKillOnCloseJobAssigned': False}
    process, job = None, None; started = time.monotonic()
    try:
        job = OwnedJob()
        with open(game.io(log), 'xb') as output:
            process = subprocess.Popen([str(arg) for arg in arguments], env=environment, cwd=cwd, stdout=output, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            row['pid'] = process.pid; job.assign(process.pid); row['ownedKillOnCloseJobAssigned'] = True
            try:
                process.wait(timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                row['timedOut'] = True; job.close(); process.wait(timeout=20)
            row['exitCode'] = process.returncode
        require(not row['timedOut'] and row['exitCode'] == 0, 'OWNED_BUILD_PHASE_NONZERO_OR_TIMEOUT')
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=10)
        row.update(finishedUtc=utc(), elapsedSeconds=round(time.monotonic()-started, 3), processStopped=process is None or process.poll() is not None,
                   exitCode=None if process is None else process.poll(), log=log.relative_to(ROOT).as_posix(), logSHA256=game.sha(log) if log.is_file() else None)
        report['steps'].append(row)
    return log


def run(args):
    require(os.name == 'nt' and args.execute, 'EXPLICIT_WINDOWS_ROOT_EXECUTION_REQUIRED')
    require(os.environ.get('HOTR_BUILD_CHANNEL') != 'rustore', 'PRODUCTION_CHANNEL_FORBIDDEN')
    require(not unity_pids(), 'CONCURRENT_UNITY_REFUSED')
    project = args.project.resolve()
    require(project.parent == CACHE.resolve() and re.fullmatch(r'(?:GameProject_[0-9a-f]{32}|G85_[0-9a-f]{8})', project.name), 'PREPARED_GAME_CLONE_REQUIRED')
    prepared_path = project.parent / (project.name + '_Preparation.json')
    prepared = read(prepared_path)
    validate_project(project, prepared, after_export=args.phase == 'assemble')
    import msvcrt
    guard = ROOT / '.verification-cache/ShopAds85/NativeRunner.lock'; guard.parent.mkdir(parents=True, exist_ok=True)
    with guard.open('a+b') as lock:
        if os.fstat(lock.fileno()).st_size == 0:
            lock.write(b'0'); lock.flush()
        lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            require(not unity_pids(), 'CONCURRENT_UNITY_REFUSED')
            attempt = CACHE / 'GameBuildAttempts' / uuid.uuid4().hex; attempt.mkdir(parents=True, exist_ok=False)
            before = game.manifest(); write(attempt / 'Main_before.json', before)
            report = {'status': 'FAIL_ROOT_YANDEX85_GAME_BUILD_PHASE', 'phase': args.phase, 'startedUtc': utc(), 'project': project.relative_to(ROOT).as_posix(), 'package': game.GAME_PACKAGE,
                      'preparationSHA256': game.sha(prepared_path), 'mainSourceManifestSHA256': game.sha(attempt / 'Main_before.json'), 'sourceInputCount': len(before),
                      'runnerSHA256': game.sha(Path(__file__)), 'gamePreparationHelperSHA256': game.sha(Path(game.__file__)), 'preparedGamePreparationHelperSHA256': prepared['helperSHA256'],
                      'sharedSdkBuildHelperSHA256': game.sha(Path(__file__).with_name('run_yandex85_sdk_build.py')), 'steps': [], 'apkLaunched': False, 'sdkAdRequested': False,
                      'configurationProvisioned': False, 'demoFixtureEnabled': False,
                      'scope': 'Full-game SDK compile in an isolated debug clone with actual enabled scenes/art/model and actual Yandex8.6 adapter branch. Embedded Unity Java11 export, separate explicit Java17/Gradle8.9/AGP8.7 assembly. No publisher unit/config, ad load/show, SDK initialization at runtime, app install/launch, impression/revenue/reward, normal startup, connected-account lifecycle, production or physical-device acceptance.'}
            environment = {key: value for key, value in os.environ.items() if key.upper() in WINDOWS_ENVIRONMENT}
            environment['SDKMANAGER_OPTS'] = SDKMANAGER_OPTS
            try:
                require(before == prepared['sourceInputs'], 'MAIN_SOURCE_CHANGED_BEFORE_PHASE')
                if args.phase == 'export':
                    require(args.unity.resolve() == PINNED_UNITY.resolve() and args.unity.is_file(), 'PINNED_UNITY_EXECUTABLE_REQUIRED')
                    require(not (project / 'GameAndroidExport.json').exists() and not (project / 'Build/GameGradleExport').exists(), 'PRESERVE_EXISTING_GAME_EXPORT_ATTEMPT')
                    unity_log = attempt / 'Unity.log'
                    report['unityExeSHA256'] = game.sha(args.unity)
                    execute('UnityExportProcess', [args.unity, '-batchmode', '-projectPath', project, '-buildTarget', 'Android', '-executeMethod', 'Yandex85GameExport.Run', '-logFile', unity_log], environment, project, attempt, report)
                    path, value = exported(project)
                    require(value['preparationSHA256'] == game.sha(prepared_path) and value['enabledScenes'] == prepared['enabledScenes'], 'GAME_EXPORT_BINDING_INVALID')
                    report['exportReportSHA256'] = game.sha(path)
                else:
                    require(args.jdk17 and args.gradle89 and args.sdk_proof, 'EXPLICIT_PROVEN_SDK_TOOL_PATHS_REQUIRED')
                    path, value = exported(project)
                    require(value['enabledScenes'] == prepared['enabledScenes'] and value['preparationSHA256'] == game.sha(prepared_path), 'GAME_EXPORT_BINDING_INVALID')
                    jdk, gradle, proof_path = args.jdk17.resolve(), args.gradle89.resolve(), args.sdk_proof.resolve()
                    require(proof_path.is_relative_to((CACHE / 'BuildAttempts').resolve()), 'ISOLATED_SDK_PROOF_LOCATION_REQUIRED')
                    proof = read(proof_path)
                    launcher = gradle / 'lib/gradle-launcher-8.9.jar'
                    require(proof['status'] == 'PASS_ROOT_ISOLATED_YANDEX85_BUILD_PHASE' and proof['phase'] == 'assemble-modern' and proof['gradleVersion'] == '8.9' and not proof['apkLaunched'], 'PASSED_SDK_MODERN_ASSEMBLY_REQUIRED')
                    require(re.search(r'^JAVA_VERSION="17\.', (jdk / 'release').read_text('utf-8'), re.MULTILINE) and game.sha(jdk / 'release') == proof['jdkReleaseSHA256'] and game.sha(launcher) == proof['gradleLauncherSHA256'], 'TOOL_BINARIES_DIFFER_FROM_PASSED_SDK_PROFILE')
                    prepared_modern = game.prepare_modern(project)
                    modern = project / 'Build/GameGradleModern'
                    require(prepared_modern['status'] == 'PREPARED_FULL_GAME_MODERN_GRADLE_NOT_ASSEMBLED' and prepared_modern['package'] == game.GAME_PACKAGE, 'FULL_GAME_MODERN_PROFILE_NOT_PREPARED')
                    check_paths(modern, prepared_modern['derivedProfileSHA256'])
                    report.update(modernPreparationSHA256=game.sha(project / 'GameModernPreparation.json'), sdkAssemblyProofSHA256=game.sha(proof_path), jdkReleaseSHA256=game.sha(jdk / 'release'),
                                  gradleLauncherSHA256=game.sha(launcher), gradleVersion='8.9', javaVersion='17', agpVersion='8.7.0')
                    environment['JAVA_HOME'] = str(jdk); environment['GRADLE_USER_HOME'] = str(CACHE / 'GradleUserHome')
                    locking = Path(__file__).with_name('GradleDependencyLocking85.gradle'); report['dependencyLockingScriptSHA256'] = game.sha(locking)
                    base = [jdk / 'bin/java.exe', '-cp', launcher, 'org.gradle.launcher.GradleMain', '-Dorg.gradle.java.home='+str(jdk), '-p', modern, '--init-script', locking, '--no-daemon', '--console=plain', '--stacktrace']
                    version_log = execute('GradleVersion', base + ['--version'], environment, modern, attempt, report)
                    require('Gradle 8.9' in version_log.read_text('utf-8', errors='replace'), 'ACTUAL_GRADLE89_VERSION_REQUIRED')
                    execute('Dependencies', base + [':launcher:dependencies', '--configuration', 'releaseRuntimeClasspath', '--write-locks'], environment, modern, attempt, report)
                    execute('Assemble', base + [':launcher:assembleRelease'], environment, modern, attempt, report)
                    locks = {p.relative_to(modern).as_posix(): game.sha(p) for p in game.files(modern) if p.name == 'gradle.lockfile'}
                    require(locks, 'RESOLVED_DEPENDENCY_LOCK_REQUIRED')
                    apks = list((modern / 'launcher/build/outputs/apk/release').glob('*.apk')); require(len(apks)==1, 'ONE_FULL_GAME_REVIEW_APK_REQUIRED')
                    report.update(exportReportSHA256=game.sha(path), dependencyLockSHA256=locks, apk={'path': apks[0].relative_to(ROOT).as_posix(), 'sha256': game.sha(apks[0]), 'bytes': apks[0].stat().st_size},
                                  mergedManifestSHA256={p.relative_to(modern).as_posix(): game.sha(p) for p in game.files(modern) if p.name == 'AndroidManifest.xml' and '/build/intermediates/' in p.as_posix()},
                                  nativeLibrarySHA256={p.relative_to(modern).as_posix(): game.sha(p) for p in game.files(modern) if p.suffix.lower()=='.so' and '/build/' in p.as_posix()})
                    check_paths(project / 'Build/GameGradleExport', {row['path']: row['sha256'] for row in value['exportBindings']})
                validate_project(project, prepared, after_export=True)
                report['status'] = 'PASS_ROOT_YANDEX85_GAME_BUILD_PHASE'
            except Exception as error:
                report['errorCode'] = str(error) if isinstance(error, (ValueError, RuntimeError)) and re.fullmatch('[A-Za-z0-9_]+', str(error)) else type(error).__name__
            finally:
                for filename in ('GameAndroidExport.json', 'GameModernPreparation.json'):
                    source = project / filename
                    if source.is_file():
                        try:
                            with open(game.io(source), 'rb') as src, open(game.io(attempt / filename), 'xb') as dst:
                                dst.write(src.read())
                        except Exception as error:
                            report['status'] = 'FAIL_ROOT_YANDEX85_GAME_BUILD_PHASE'
                            report['reportCaptureErrorType'] = type(error).__name__
                report['mainSourceUnchanged'] = False
                try:
                    after = game.manifest(); write(attempt / 'Main_after.json', after)
                    report['mainSourceUnchanged'] = after == before == prepared['sourceInputs']; report['mainAfterSHA256'] = game.sha(attempt / 'Main_after.json')
                    report['unityPidsAfter'] = unity_pids()
                except Exception as error:
                    report['finalAuditErrorType'] = type(error).__name__; report['unityPidsAfter'] = None
                if not report['mainSourceUnchanged'] or report['unityPidsAfter'] != []:
                    report['status'] = 'FAIL_ROOT_YANDEX85_GAME_BUILD_PHASE'
                report['finishedUtc'] = utc(); write(attempt / 'Report.json', report)
                print('Report: '+(attempt / 'Report.json').relative_to(ROOT).as_posix(), flush=True)
            return report
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--phase', required=True, choices=['export', 'assemble'])
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--unity', type=Path, default=PINNED_UNITY)
    parser.add_argument('--jdk17', type=Path)
    parser.add_argument('--gradle89', type=Path)
    parser.add_argument('--sdk-proof', type=Path)
    args = parser.parse_args(); result = run(args)
    print(json.dumps({'status': result['status'], 'phase': result['phase'], 'project': result['project']}))
    raise SystemExit(0 if result['status'].startswith('PASS_') else 1)


if __name__ == '__main__':
    main()
