"""Root-only receipt for the installed, isolated Unity 6 Android toolchain.

This records distribution/module bytes and runs only CLI --version/java -version.
It does not launch Unity, installers, sdkmanager, adb, or any account/license tool.
Toolchain readiness is separate from project compilation and device acceptance.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from prepare_editor import (CACHE, DESTINATION, EXPECTED_MODULES, REVISION, ROOT,
                            SOURCE, VERSION, bounded, digest, reject_links_to_root,
                            write_new)

CLI_VERSION = '1.0.0-beta.14'
CLI_SHA256 = '78761a0547cd4a9bc212e27a217c66e6a621bf48c753ba440e4b2327ee7ff8ac'
PRIVATE = ROOT / '.verification-cache/Unity6Migration94/Environment'
CLI = PRIVATE / 'unity-cli-1.0.0-beta.14.exe'
INSTALL_LOG = PRIVATE / 'PortableAndroidInstallRelative.log'
PUBLIC = ROOT / 'Verification/Evidence/Unity6Migration94/Environment'
OUTPUT = PUBLIC / 'Installed'
ANDROID = DESTINATION / 'Editor/Data/PlaybackEngines/AndroidPlayer'
ARTIFACTS = {
    'android': ['UnityEditor.Android.Extensions.dll', 'Unity.Android.Gradle.dll',
                'Unity.Android.Types.dll', 'AndroidPlayerBuildProgram.exe', 'modules.asset'],
    'android-open-jdk-17.0.18+8': ['OpenJDK/bin/java.exe', 'OpenJDK/release'],
    # This manifest node is a grouping/scaffold. Its installed children supply
    # the SDK; do not invent a legacy SDK/tools/source.properties requirement.
    'android-sdk-ndk-tools': ['SDK/cmdline-tools/16.0/bin/sdkmanager.bat'],
    'android-ndk-r27c': ['NDK/source.properties', 'NDK/ndk-build.cmd',
                        'NDK/toolchains/llvm/prebuilt/windows-x86_64/bin/clang.exe'],
    'cmake-3.22.1': ['SDK/cmake/3.22.1/source.properties', 'SDK/cmake/3.22.1/bin/cmake.exe'],
    'android-sdk-build-tools-36.0.0': ['SDK/build-tools/36.0.0/source.properties',
        'SDK/build-tools/36.0.0/aapt2.exe', 'SDK/build-tools/36.0.0/zipalign.exe',
        'SDK/build-tools/36.0.0/lib/apksigner.jar', 'SDK/build-tools/36.0.0/lib/d8.jar'],
    'android-sdk-platform-tools-37.0.1': ['SDK/platform-tools/source.properties',
                                        'SDK/platform-tools/adb.exe'],
    'android-sdk-platforms-34': ['SDK/platforms/android-34/source.properties',
                                'SDK/platforms/android-34/android.jar'],
    'android-sdk-platforms-36': ['SDK/platforms/android-36/source.properties',
                                'SDK/platforms/android-36/android.jar'],
    'android-sdk-platforms-37.0': ['SDK/platforms/android-37.0/source.properties',
                                  'SDK/platforms/android-37.0/android.jar'],
    'android-sdk-command-line-tools-16.0': ['SDK/cmdline-tools/16.0/source.properties',
        'SDK/cmdline-tools/16.0/bin/sdkmanager.bat',
        'SDK/cmdline-tools/16.0/lib/sdkmanager-classpath.jar'],
}


def utc():
    return datetime.now(timezone.utc).isoformat()


def decode_private_log(raw):
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        return raw.decode('utf-16')
    return raw.decode('utf-8-sig')


def parse_install_log(raw):
    """Select a complete terminal tool result, never a wrapper's error text."""
    text = decode_private_log(raw)
    decoder = json.JSONDecoder()
    candidates = []
    for match in re.finditer(r'(?m)^\s*\{', text):
        try:
            value, consumed = decoder.raw_decode(text[match.start():].lstrip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get('command') == 'install-modules':
            following = text[match.start():].lstrip()[consumed:]
            if following.strip():
                continue
            candidates.append(value)
    if len(candidates) != 1:
        raise ValueError('Expected one complete terminal install-modules result')
    result = candidates[0]
    if result.get('success') is not True or result.get('errors') != []:
        raise ValueError('Official module installer did not report success without errors')
    data = result.get('data', {})
    complete = data.get('completedUids', [])
    items = data.get('items', [])
    if (len(complete) != len(EXPECTED_MODULES) or set(complete) != EXPECTED_MODULES or
            len(items) != len(EXPECTED_MODULES) or
            {item.get('uid') for item in items} != EXPECTED_MODULES or
            any(item.get('kind') != 'module' or item.get('status') != 'installed' for item in items)):
        raise ValueError('Terminal result does not prove all 11 Android modules installed once')
    warnings = result.get('warnings')
    if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
        raise ValueError('Unexpected installer warnings structure')
    # Do not export arbitrary provider/account/proxy content from a private log.
    for warning in warnings:
        if not re.fullmatch(r'Module install failed; retrying \(attempt \d+ of \d+\) in \d+s\.\.\.', warning):
            raise ValueError('An unfamiliar installer warning requires root review before export')
    return result


def outcome(result, wrapper_exit_code):
    return {'cliReportedSuccess': result['success'], 'cliReportedErrors': result['errors'],
            'cliWarnings': result['warnings'], 'wrapperExitCode': wrapper_exit_code,
            'wrapperPassed': wrapper_exit_code == 0,
            'cliProcessExitCode': None,
            'wrapperInterpretation': 'The PowerShell wrapper exit is retained separately. Its stderr handling can fail on the recovered installer retry warning; no CLI process exit code is inferred from the terminal JSON.'}


def properties(text):
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(('#', '!')) or '=' not in line:
            continue
        key, value = (part.strip() for part in line.split('=', 1))
        if key in result:
            raise ValueError('Repeated property key requires review: ' + key)
        result[key] = value.strip('"')
    return result


def parse_java_version(text):
    if not re.search(r'(?m)^openjdk version "17\.0\.18"', text):
        raise ValueError('Actual Java runtime does not report OpenJDK 17.0.18')
    if 'Temurin-17.0.18+8' not in text or '64-Bit Server VM' not in text:
        raise ValueError('Actual Java runtime build or architecture differs')
    return {'javaVersion': '17.0.18', 'runtimeBuild': '17.0.18+8', 'distribution': 'Temurin',
            'is64BitServerVM': True}


def load_properties(relative, required):
    path = bounded(ANDROID / relative, ANDROID)
    actual = properties(path.read_text('utf-8-sig'))
    for key, expected in required.items():
        if actual.get(key) != expected:
            raise ValueError('Unexpected toolchain package property: ' + relative + ': ' + key)
    return {'path': path.relative_to(DESTINATION).as_posix(), 'sha256': digest(path),
            'verifiedProperties': required}


def subprocess_version(path, arguments, timeout):
    environment = dict(os.environ)
    for name in ('_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS'):
        environment.pop(name, None)
    completed = subprocess.run([str(path), *arguments], env=environment, cwd=CACHE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=False)
    if completed.returncode != 0:
        raise ValueError('Version-only subprocess failed: ' + Path(path).name)
    stdout = completed.stdout.decode('utf-8-sig')
    stderr = completed.stderr.decode('utf-8-sig')
    return completed.returncode, stdout, stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--preparation', type=Path, required=True)
    parser.add_argument('--wrapper-exit-code', type=int, required=True,
                        help='Actual recorded PowerShell wrapper exit; do not substitute the JSON result')
    args = parser.parse_args()
    if not args.execute:
        print('Inspect the helper, then root may explicitly pass --execute. No receipt or subprocess created.')
        return 0
    preparation_path = bounded(args.preparation, PUBLIC / 'PortableEditor')
    preparation = json.loads(preparation_path.read_text('utf-8'))
    if (preparation.get('status') != 'PASS_PRIVATE_EDITOR_COPY94_MODULES_NOT_INSTALLED' or
            preparation.get('version') != VERSION or preparation.get('changeset') != REVISION or
            Path(preparation.get('source', '')).resolve() != SOURCE.resolve() or
            Path(preparation.get('destination', '')).resolve() != DESTINATION.resolve()):
        parser.error('Matching successful short-path Editor preparation receipt required')
    bounded(OUTPUT, PUBLIC)
    OUTPUT.mkdir(parents=True, exist_ok=False)
    record = {'schemaVersion': 1, 'status': 'RECORDING_PORTABLE_ANDROID_TOOLCHAIN94',
        'startedUtc': utc(), 'runnerSHA256': digest(__file__),
        'preparation': str(preparation_path.relative_to(ROOT)).replace('\\', '/'),
        'preparationSHA256': digest(preparation_path), 'version': VERSION, 'changeset': REVISION,
        'portableEditor': str(DESTINATION),
        'scope': 'Official isolated Android toolchain installation and version/artifact checks only. No project compile, APK build, device, SDK-provider, performance, or production acceptance.',
        'unityLaunchedByThisRecorder': False, 'installerLaunchedByThisRecorder': False,
        'sdkmanagerOrAdbLaunched': False, 'accountOrLicenseDataRead': False,
        'hubPreferenceFilesCopied': False,
        'portableCLIPathNote': 'CLI beta14 drive-absolute -d values were incorrectly appended to cwd. Installation used cwd E:/ and relative -d HeartRainUnity6_94; no global install-path change was needed.'}
    try:
        reject_links_to_root(SOURCE)
        reject_links_to_root(DESTINATION)
        reject_links_to_root(CLI)
        if digest(CLI) != CLI_SHA256:
            raise ValueError('Private official CLI SHA-256 mismatch')
        log_before = INSTALL_LOG.stat()
        raw_log = INSTALL_LOG.read_bytes()
        result = parse_install_log(raw_log)
        if INSTALL_LOG.stat().st_mtime_ns != log_before.st_mtime_ns:
            raise ValueError('Installer log is still changing')
        record['installer'] = outcome(result, args.wrapper_exit_code)
        record['installer'].update(privateLog=str(INSTALL_LOG.relative_to(ROOT)).replace('\\', '/'),
            privateLogSHA256=hashlib.sha256(raw_log).hexdigest(), rawAccountLogsCopied=False,
            completedModuleIds=result['data']['completedUids'])
        unchanged = {}
        for relative, expected in preparation['distributionMetadataSHA256'].items():
            original = bounded(SOURCE / relative, SOURCE)
            actual = digest(original)
            unchanged[relative] = {'beforeSHA256': expected, 'actualSHA256': actual,
                                   'unchanged': actual == expected}
            if actual != expected:
                raise ValueError('Original C: Editor executable/metadata changed: ' + relative)
        record['originalEditorChecks'] = unchanged
        if digest(DESTINATION / 'Editor/Unity.exe') != preparation['distributionMetadataSHA256']['Editor/Unity.exe']:
            raise ValueError('Portable Editor executable differs from the copied distribution')
        metadata_path = DESTINATION / 'modules.json'
        metadata = json.loads(metadata_path.read_text('utf-8-sig'))
        if not isinstance(metadata, list):
            raise ValueError('Installed module metadata must be a list')
        module_records = {}
        for module_id in sorted(EXPECTED_MODULES):
            matches = [item for item in metadata if item.get('id') == module_id]
            if len(matches) != 1 or matches[0].get('selected') is not True:
                raise ValueError('Installed flat module metadata is absent/unselected/ambiguous: ' + module_id)
            artifacts = []
            for relative in ARTIFACTS[module_id]:
                path = bounded(ANDROID / relative, ANDROID)
                if not path.is_file() or path.stat().st_size <= 0:
                    raise ValueError('Required installed artifact is absent or empty: ' + relative)
                artifacts.append({'path': path.relative_to(DESTINATION).as_posix(),
                                  'bytes': path.stat().st_size, 'sha256': digest(path)})
            module_records[module_id] = {'installedMetadataSelected': True, 'artifacts': artifacts}
            if module_id == 'android-sdk-ndk-tools':
                module_records[module_id]['scope'] = 'Grouping module; readiness is represented by its installed children, with the command-line entry point shared above.'
        record['modules'] = module_records
        record['installedModulesMetadataSHA256'] = digest(metadata_path)
        record['packageVersions'] = [
            load_properties('NDK/source.properties', {'Pkg.Revision': '27.2.12479018', 'Pkg.ReleaseName': 'r27c'}),
            load_properties('OpenJDK/release', {'JAVA_VERSION': '17.0.18', 'JAVA_RUNTIME_VERSION': '17.0.18+8', 'OS_ARCH': 'x86_64'}),
            load_properties('SDK/cmake/3.22.1/source.properties', {'Pkg.Revision': '3.22.1'}),
            load_properties('SDK/build-tools/36.0.0/source.properties', {'Pkg.Revision': '36.0.0'}),
            load_properties('SDK/platform-tools/source.properties', {'Pkg.Revision': '37.0.1'}),
            load_properties('SDK/cmdline-tools/16.0/source.properties', {'Pkg.Revision': '16.0'}),
            load_properties('SDK/platforms/android-34/source.properties', {'AndroidVersion.ApiLevel': '34'}),
            load_properties('SDK/platforms/android-36/source.properties', {'AndroidVersion.ApiLevel': '36'}),
            load_properties('SDK/platforms/android-37.0/source.properties', {'AndroidVersion.ApiLevel': '37.0'}),
        ]
        cli_exit, cli_stdout, cli_stderr = subprocess_version(CLI, ['--version'], 20)
        if cli_stdout.strip() != CLI_VERSION or cli_stderr.strip():
            raise ValueError('Private CLI actual version output differs from the pinned release')
        record['cli'] = {'version': CLI_VERSION, 'expectedSHA256': CLI_SHA256,
                         'actualSHA256': digest(CLI), 'versionExitCode': cli_exit}
        java_exit, java_stdout, java_stderr = subprocess_version(ANDROID / 'OpenJDK/bin/java.exe', ['-version'], 20)
        java = parse_java_version(java_stdout + java_stderr)
        record['java'] = {**java, 'versionExitCode': java_exit,
                          'versionStdoutSHA256': hashlib.sha256(java_stdout.encode('utf-8')).hexdigest(),
                          'versionStderrSHA256': hashlib.sha256(java_stderr.encode('utf-8')).hexdigest()}
        record.update(status='PASS_PORTABLE_UNITY6_ANDROID_TOOLCHAIN94_ONLY',
            expectedModuleCount=11, verifiedModuleCount=len(module_records),
            originalEditorExecutableAndMetadataUnchanged=True,
            credentialsOrAccountLogsExported=False,
            limitations=['PowerShell wrapper exit is preserved independently of the successful terminal installer result.',
                'Version commands ran only CLI --version and Java -version; no sdkmanager/adb/NDK compiler execution is claimed.',
                'Artifact presence/hashes and package properties do not prove a project builds or runs.',
                'Installed artifact hashes are observations; empty publisher integrity fields were not invented or replaced.',
                'No SDK license files were created by this recorder; further sdkmanager requests may still require official license acceptance.'])
    except Exception as error:
        record.update(status='FAIL_PORTABLE_UNITY6_ANDROID_TOOLCHAIN94',
                      errorType=type(error).__name__, error=str(error))
        raise
    finally:
        record['finishedUtc'] = utc()
        write_new(OUTPUT / 'Report.json', record)
        print(json.dumps({'status': record['status'], 'report': str(OUTPUT / 'Report.json')}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
