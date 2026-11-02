"""ROOT-ONLY isolated SDK compilation; no downloads of toolchains, app launch or ADB.

Each explicit phase preserves a separate report. `export` uses the pinned
Editor's supported Java11. `assemble-stock` is a compatibility control using
its installed Gradle7.5.1/Java11. `assemble-modern` derives a separate export
for explicit external Gradle8.9/Java17 with AGP8.7.0. Neither changes the main
Unity engine, external-tool preferences, packages or ordinary application.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / '.verification-cache/Ads85'
EDITOR = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor')
PLAYER = EDITOR / 'Data/PlaybackEngines/AndroidPlayer'
PACKAGE = 'com.heartoftherain.yandex85sdkfixture'
SDKMANAGER_OPTS = '-Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=9 -Dhttp.proxyHost=127.0.0.1 -Dhttp.proxyPort=9 -Dsun.net.client.defaultConnectTimeout=3000 -Dsun.net.client.defaultReadTimeout=3000'


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(data)
    return value.hexdigest()


def require(value, code):
    if not value:
        raise ValueError(code)


def hidden():
    require(os.name == 'nt', 'PINNED_WINDOWS_HOST_REQUIRED')
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    return {'startupinfo': info, 'creationflags': subprocess.CREATE_NO_WINDOW}


def bindings(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def check_bindings(root, records):
    for relative, expected in records.items():
        target = (root / relative).resolve()
        require(target.is_relative_to(root.resolve()) and target.is_file() and sha(target) == expected, 'FROZEN_INPUT_CHANGED')


def modern_profile(export, destination):
    """Derive only a cache export; never patch Unity-owned toolchain files."""
    require(not destination.exists(), 'PRESERVE_PRIOR_MODERN_EXPORT')
    def ignored(directory, names):
        current = Path(directory).resolve()
        if current == export.resolve():
            return [name for name in names if name in ('.gradle', 'build')]
        if current in ((export / 'launcher').resolve(), (export / 'unityLibrary').resolve()):
            return ['build'] if 'build' in names else []
        return []
    shutil.copytree(export, destination, ignore=ignored)
    changes = []
    def change(relative, transform):
        path = destination / relative
        before = path.read_bytes()
        after = transform(before.decode('utf-8')).encode('utf-8')
        if before != after:
            path.write_bytes(after)
            changes.append({'path': relative, 'beforeSHA256': hashlib.sha256(before).hexdigest(), 'afterSHA256': hashlib.sha256(after).hexdigest()})
    def plugin_versions(text):
        updated, count = re.subn(r"(id 'com\.android\.(?:application|library)' version ')7\.4\.2(')", r'\g<1>8.7.0\2', text)
        require(count == 2, 'EXPECTED_STOCK_AGP742_PLUGIN_PAIR_REQUIRED')
        return updated
    change('build.gradle', plugin_versions)
    # Use the AGP-matched Maven AAPT2 instead of Unity's old local override.
    change('gradle.properties', lambda text: re.sub(r'(?m)^android\.aapt2FromMavenOverride=.*\r?\n?', '', text))
    # Unity2022's generated IL2CPP task reads the legacy NDK getter, which
    # AGP8 no longer resolves from ndkPath. Keep the installed pinned NDK and
    # pass that explicit path; do not install a different NDK implicitly.
    def explicit_ndk(text):
        require(text.count('android.ndkDirectory') == 1 and 'ndkPath "' in text, 'ONE_PINNED_NDK_TASK_REFERENCE_REQUIRED')
        return text.replace('android.ndkDirectory', 'android.ndkPath')
    change('unityLibrary/build.gradle', explicit_ndk)
    for relative in ('unityLibrary/src/main/AndroidManifest.xml', 'launcher/src/main/AndroidManifest.xml'):
        path = destination / relative
        value = ET.fromstring(path.read_bytes())
        if 'package' not in value.attrib:
            continue
        old_package = value.attrib['package']
        module = relative.split('/')[0]
        gradle = (destination / module / 'build.gradle').read_text('utf-8')
        require(re.search(r'namespace\s+["\']' + re.escape(old_package) + r'["\']', gradle), 'MANIFEST_NAMESPACE_MUST_ALREADY_MATCH')
        change(relative, lambda text: re.sub(r'\s+package\s*=\s*["\']' + re.escape(old_package) + r'["\']', '', text, count=1))
    return changes


def run(args):
    require(args.execute and os.name == 'nt' and 60 <= args.timeout <= 3600, 'EXPLICIT_BOUNDED_ROOT_EXECUTION_REQUIRED')
    project = args.project.resolve()
    require(project.is_relative_to(CACHE.resolve()) and project.is_dir(), 'PREPARED_ISOLATED_PROJECT_REQUIRED')
    prepared_path = project.parent / (project.name + '_Preparation.json')
    prepared = json.loads(prepared_path.read_text('utf-8'))
    require(prepared['status'] == 'PREPARED_ISOLATED_YANDEX85_SDK_NOT_BUILT' and prepared['package'] == PACKAGE and prepared['unity'] == '2022.3.62f3', 'PREPARATION_CONTRACT_INVALID')
    check_bindings(project, prepared['copiedVendorSHA256'])
    # PlayerSettings in the separate project is intentionally configured by
    # the export method, but vendor and integration inputs stay immutable.
    check_bindings(project, {k: v for k, v in prepared['generatedSHA256'].items() if not k.startswith('ProjectSettings/')})
    for relative, expected in prepared['copiedMainIntegrationSHA256'].items():
        require(sha(ROOT / relative) == expected, 'MAIN_ADAPTER_CHANGED_AFTER_PREPARATION')
    attempt = project.parent / 'BuildAttempts' / uuid.uuid4().hex
    attempt.mkdir(parents=True, exist_ok=False)
    main_paths = ['Unity/Packages/manifest.json', 'Unity/Packages/packages-lock.json', 'Unity/ProjectSettings/ProjectSettings.asset', 'Unity/ProjectSettings/ProjectVersion.txt']
    before_main = {relative: sha(ROOT / relative) for relative in main_paths}
    report = {'status': 'FAIL_ROOT_ISOLATED_YANDEX85_BUILD_PHASE', 'phase': args.phase, 'startedUtc': utc(), 'package': PACKAGE,
              'preparationSHA256': sha(prepared_path), 'helperSHA256': sha(Path(__file__)), 'steps': [], 'apkLaunched': False,
              'mainSettingsBeforeSHA256': before_main, 'scope': 'Isolated compilation only. No Unity engine/SDK automatic upgrade, SDK initialization/ad load/show, revenue click, wallet grant, app installation/launch, provider verification or production certification.'}
    def execute(name, command, environment, cwd):
        log = attempt / (name + '.log')
        step = {'name': name, 'startedUtc': utc(), 'hidden': True, 'timeoutSeconds': args.timeout}
        with log.open('wb') as stream:
            process = subprocess.Popen([str(value) for value in command], cwd=cwd, env=environment, stdout=stream, stderr=subprocess.STDOUT, **hidden())
            step['pid'] = process.pid
            try:
                code = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                step['timedOut'] = True
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=15)
                raise ValueError('OWN_BUILD_LAUNCHER_TIMEOUT') from None
            finally:
                step.update({'finishedUtc': utc(), 'exitCode': process.poll()})
                report['steps'].append(step)
        step['log'] = log.relative_to(ROOT).as_posix()
        step['logSHA256'] = sha(log)
        require(code == 0, 'ISOLATED_BUILD_PHASE_NONZERO')
        return log.read_text('utf-8', errors='replace')
    allowed = {'SYSTEMROOT', 'SYSTEMDRIVE', 'WINDIR', 'TEMP', 'TMP', 'COMSPEC', 'PATH', 'PATHEXT', 'USERPROFILE', 'USERNAME', 'HOMEDRIVE', 'HOMEPATH', 'APPDATA', 'LOCALAPPDATA', 'ALLUSERSPROFILE', 'PUBLIC', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMW6432', 'COMMONPROGRAMFILES', 'COMMONPROGRAMFILES(X86)', 'COMMONPROGRAMW6432', 'PROGRAMDATA', 'OS', 'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS'}
    environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    environment['SDKMANAGER_OPTS'] = SDKMANAGER_OPTS
    try:
        require(os.environ.get('HOTR_BUILD_CHANNEL') != 'rustore', 'PRODUCTION_BUILD_CHANNEL_FORBIDDEN')
        if args.phase == 'export':
            require((EDITOR / 'Unity.exe').is_file(), 'PINNED_UNITY_NOT_INSTALLED')
            # The root serializes Unity. Refuse rather than kill another Editor.
            state = subprocess.run(['powershell.exe', '-NoProfile', '-Command', '(Get-Process -Name Unity -ErrorAction SilentlyContinue | Measure-Object).Count'], capture_output=True, timeout=15, **hidden())
            require(state.returncode == 0 and state.stdout.strip() == b'0', 'OTHER_UNITY_PROCESS_EXISTS')
            log = attempt / 'Unity.log'
            execute('UnityExportProcess', [EDITOR / 'Unity.exe', '-batchmode', '-projectPath', project, '-buildTarget', 'Android', '-executeMethod', 'Yandex85SdkExport.Run', '-logFile', log], environment, project)
            report['unityLogSHA256'] = sha(log)
            exported = json.loads((project / 'AndroidExport.json').read_text('utf-8'))
            require(exported['status'] == 'PASS_ISOLATED_YANDEX85_GRADLE_EXPORT' and exported['jdkSettingsUnchanged'] and exported['actualSdkReferenceCompiled'] and exported['noSdkInitializationOrAdRequests'] and not exported['apkLaunched'], 'PINNED_UNITY_EXPORT_NOT_PASSED')
            report['exportReportSHA256'] = sha(project / 'AndroidExport.json')
        else:
            exported = json.loads((project / 'AndroidExport.json').read_text('utf-8'))
            require(exported['status'] == 'PASS_ISOLATED_YANDEX85_GRADLE_EXPORT' and exported['jdkSettingsUnchanged'], 'APPROVED_EXPORT_REQUIRED')
            export = project / 'Build/GradleExport'
            export_bindings = {row['path']: row['sha256'] for row in exported['exportBindings']}
            check_bindings(export, export_bindings)
            if args.phase == 'assemble-modern':
                require(args.jdk17 and args.gradle89, 'EXPLICIT_EXTERNAL_TOOLS_REQUIRED')
                jdk, gradle, version = args.jdk17.resolve(), args.gradle89.resolve(), '8.9'
                require(re.search(r'^JAVA_VERSION="17\.', (jdk / 'release').read_text('utf-8'), re.MULTILINE), 'EXPLICIT_JAVA17_REQUIRED')
                profile = project / ('Build/M' + attempt.name[:6])
                report['derivedProfileChanges'] = modern_profile(export, profile)
                report['derivedProfileInputSHA256'] = bindings(profile)
            else:
                jdk, gradle, version, profile = PLAYER / 'OpenJDK', PLAYER / 'Tools/gradle', '7.5.1', export
                require('JAVA_VERSION="11.' in (jdk / 'release').read_text('utf-8'), 'STOCK_EMBEDDED_JAVA11_REQUIRED')
            launcher = gradle / 'lib' / ('gradle-launcher-' + version + '.jar')
            require(launcher.is_file() and (jdk / 'bin/java.exe').is_file(), 'EXPLICIT_TOOL_DISTRIBUTION_MISSING')
            report.update({'jdkReleaseSHA256': sha(jdk / 'release'), 'gradleLauncherSHA256': sha(launcher), 'gradleVersion': version,
                           'exportReportSHA256': sha(project / 'AndroidExport.json')})
            environment['JAVA_HOME'] = str(jdk)
            environment['GRADLE_USER_HOME'] = str(CACHE / 'GradleUserHome')
            lock_script = Path(__file__).resolve().parent / 'GradleDependencyLocking85.gradle'
            report['dependencyLockingScriptSHA256'] = sha(lock_script)
            base = [jdk / 'bin/java.exe', '-cp', launcher, 'org.gradle.launcher.GradleMain', '-Dorg.gradle.java.home=' + str(jdk), '-p', profile, '--init-script', lock_script, '--no-daemon', '--console=plain', '--stacktrace']
            version_text = execute('GradleVersion', base + ['--version'], environment, profile)
            require('Gradle ' + version in version_text, 'ACTUAL_GRADLE_VERSION_MISMATCH')
            execute('Dependencies', base + [':launcher:dependencies', '--configuration', 'releaseRuntimeClasspath', '--write-locks'], environment, profile)
            execute('Assemble', base + [':launcher:assembleRelease'], environment, profile)
            check_bindings(export, export_bindings)
            apks = list((profile / 'launcher/build/outputs/apk/release').glob('*.apk'))
            require(len(apks) == 1, 'ONE_ISOLATED_FIXTURE_APK_REQUIRED')
            report['apk'] = {'path': apks[0].relative_to(ROOT).as_posix(), 'sha256': sha(apks[0]), 'bytes': apks[0].stat().st_size}
            report['mergedManifestSHA256'] = {p.relative_to(profile).as_posix(): sha(p) for p in profile.rglob('AndroidManifest.xml') if '/build/intermediates/' in p.as_posix()}
            report['dependencyLockSHA256'] = {p.relative_to(profile).as_posix(): sha(p) for p in profile.rglob('gradle.lockfile')}
            require(report['dependencyLockSHA256'], 'RESOLVED_DEPENDENCY_LOCK_REQUIRED')
        check_bindings(project, prepared['copiedVendorSHA256'])
        report['status'] = 'PASS_ROOT_ISOLATED_YANDEX85_BUILD_PHASE'
    except Exception as error:
        report['errorCode'] = str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+', str(error)) else type(error).__name__
    finally:
        after_main = {relative: sha(ROOT / relative) for relative in main_paths}
        report.update({'finishedUtc': utc(), 'mainSettingsAfterSHA256': after_main, 'mainSettingsUnchanged': before_main == after_main})
        if before_main != after_main:
            report['status'] = 'FAIL_ROOT_ISOLATED_YANDEX85_BUILD_PHASE'
            report['errorCode'] = 'MAIN_PROJECT_SETTINGS_CHANGED'
        (attempt / 'Report.json').write_text(json.dumps(report, indent=2) + '\n', 'utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--phase', required=True, choices=['export', 'assemble-stock', 'assemble-modern'])
    parser.add_argument('--project', type=Path, default=CACHE / 'SdkProject')
    parser.add_argument('--jdk17', type=Path)
    parser.add_argument('--gradle89', type=Path)
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({key: result[key] for key in ('status', 'phase', 'startedUtc', 'finishedUtc')}))
    raise SystemExit(0 if result['status'].startswith('PASS_') else 1)


if __name__ == '__main__':
    main()
