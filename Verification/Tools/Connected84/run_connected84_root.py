"""ROOT-ONLY Connected84 fixture orchestration; import never launches a process.

Review before using --execute. Only the sealed QA2 serial and one fixed fixture
package are mutable. Normal applications are read solely for attempt and hash
audits. The helper never reads the protected recovery record or any credential.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / 'Verification/Tools'
sys.path.insert(0, str(TOOLS))
from qa_android_target import assert_no_active_attempt, validate_qa_target

PACKAGE = 'com.heartoftherain.connected84fixture'
ORDINARY = 'com.heartoftherain.verification'
SERIAL = 'emulator-5558'
ACTIVITY = PACKAGE + '/com.unity3d.player.UnityPlayerActivity'
STAGES = ('setup', 'reopen', 'logout', 'closed', 'recover', 'recovered', 'delete', 'deleted')
EDITOR = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor')
SDK = EDITOR / 'Data/PlaybackEngines/AndroidPlayer/SDK'
DEFAULT_PROJECT = ROOT / '.verification-cache/Connected84/AndroidProject'
DEFAULT_OUT = ROOT / 'Verification/Evidence/Connected84'
GATEWAY_SCRIPT = TOOLS / 'serve_server_gameplay83_fixture.py'
SDKMANAGER_OPTS = '-Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=9 -Dhttp.proxyHost=127.0.0.1 -Dhttp.proxyPort=9 -Dsun.net.client.defaultConnectTimeout=3000 -Dsun.net.client.defaultReadTimeout=3000'


def utc():
    return datetime.now(timezone.utc).isoformat()


def hidden():
    if os.name != 'nt':
        raise Failure('WINDOWS_ROOT_HOST_REQUIRED')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    return {'startupinfo': startup, 'creationflags': subprocess.CREATE_NO_WINDOW}


def extended(path):
    path = Path(path)
    if os.name != 'nt':
        return path
    text = str(path.absolute())
    if text.startswith('\\\\?\\'):
        return path
    return Path('\\\\?\\UNC\\' + text[2:] if text.startswith('\\\\') else '\\\\?\\' + text)


def sha(path):
    value = hashlib.sha256()
    with extended(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def require(value, code):
    if not value:
        raise Failure(code)


class Failure(RuntimeError):
    def __init__(self, code, return_code=None):
        super().__init__(code)
        self.code, self.return_code = code, return_code


class RetainedWindowsProcess:
    """A query/synchronize handle retains identity; it cannot terminate a PID."""
    def __init__(self, pid):
        require(os.name == 'nt' and type(pid) is int and pid > 0, 'GATEWAY_PROCESS_HANDLE_INVALID')
        import ctypes
        from ctypes import wintypes
        self.ctypes, self.types = ctypes, wintypes
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
        self.kernel.GetProcessTimes.restype = wintypes.BOOL
        self.kernel.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
        self.kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
        self.kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        self.kernel.WaitForSingleObject.restype = wintypes.DWORD
        self.kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        self.kernel.CloseHandle.restype = wintypes.BOOL
        self.handle = self.kernel.OpenProcess(0x100000 | 0x1000, False, pid)
        require(bool(self.handle), 'GATEWAY_PROCESS_HANDLE_UNAVAILABLE')
        try:
            self.created_ticks = self.creation_of(self.handle)
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            require(self.kernel.QueryFullProcessImageNameW(self.handle, 0, buffer, ctypes.byref(size)), 'GATEWAY_PROCESS_IMAGE_UNAVAILABLE')
            self.image = buffer.value
        except Exception:
            self.close()
            raise

    def creation_of(self, handle):
        values = [self.types.FILETIME() for _ in range(4)]
        require(self.kernel.GetProcessTimes(handle, *(self.ctypes.byref(value) for value in values)), 'GATEWAY_PROCESS_CREATION_UNAVAILABLE')
        return (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime

    def wait(self, seconds):
        result = self.kernel.WaitForSingleObject(self.handle, int(seconds * 1000))
        require(result in (0, 0x102), 'GATEWAY_PROCESS_WAIT_UNAVAILABLE')
        return result == 0

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def windows_argument_vector(command_line):
    """Parse CIM's native command line without substring ownership checks."""
    require(os.name == 'nt' and type(command_line) is str and command_line, 'GATEWAY_COMMAND_LINE_UNAVAILABLE')
    import ctypes
    from ctypes import wintypes
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = (wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int))
    shell.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel.LocalFree.argtypes = (wintypes.HLOCAL,)
    kernel.LocalFree.restype = wintypes.HLOCAL
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW(command_line, ctypes.byref(count))
    require(bool(pointer), 'GATEWAY_COMMAND_LINE_INVALID')
    try:
        return [pointer[index] for index in range(count.value)]
    finally:
        kernel.LocalFree(ctypes.cast(pointer, wintypes.HLOCAL))


def validate_stage(value, stage, scope_hash, origin_hash):
    """I/O-free. This validates one actual stage, not a process boundary."""
    require(type(value) is dict and stage in STAGES, 'STAGE_SCHEMA_INVALID')
    forbidden = {'backupSecret', 'accessToken', 'refreshToken', 'recoverySecret', 'signature', 'publicKey', 'token', 'authorization'}
    require(not forbidden.intersection(value), 'REDACTED_REPORT_CONTRACT_VIOLATED')
    require(value.get('status') == 'PASS_ANDROID_CONNECTED84_STAGE' and value.get('errorCode') in ('', None), 'FIXTURE_STAGE_FAILED')
    require(value.get('stage') == stage and value.get('scopeHash') == scope_hash and value.get('originHash') == origin_hash, 'STAGE_OWNER_BINDING_INVALID')
    require(value.get('package') == PACKAGE and value.get('unity') == '2022.3.62f3', 'STAGE_BINARY_SCOPE_INVALID')
    require(type(value.get('pid')) is int and value['pid'] > 0 and type(value.get('sdk')) is int and value['sdk'] >= 26, 'STAGE_PROCESS_METADATA_INVALID')
    for key in ('actualAndroid', 'actualIl2cpp', 'androidSigningKeyNonexportable', 'androidEncryptionKeyNonexportable', 'actualServerFactory', 'readOnlyProfile'):
        require(value.get(key) is True, 'STAGE_REQUIRED_CAPABILITY_FAILED')
    require(type(value.get('hardwareBackedReported')) is bool, 'STAGE_HARDWARE_SCOPE_INVALID')
    for key in ('proofKeyFingerprint', 'serverKeyFingerprint', 'playerIdHash', 'ordinaryProfilesBefore', 'ordinaryProfilesAfter'):
        require(digest(value.get(key)), 'STAGE_DIGEST_INVALID')
    require(value['ordinaryProfilesBefore'] == value['ordinaryProfilesAfter'], 'FIXTURE_LOCAL_PROFILE_CHANGED')
    require(type(value.get('checks')) is int and value['checks'] > 0 and type(value.get('passed')) is list and len(value['passed']) == value['checks'], 'STAGE_CHECK_COUNT_INVALID')
    require(all(type(item) is str and re.fullmatch('[A-Za-z][A-Za-z0-9]{0,95}', item) for item in value['passed']), 'STAGE_CHECK_LABEL_INVALID')
    index = STAGES.index(stage)
    require(value.get('stageBefore') in ('', None) if index == 0 else value.get('stageBefore') == STAGES[index - 1], 'STAGE_SEQUENCE_INVALID')
    closed = stage in ('logout', 'closed', 'delete', 'deleted')
    require(value.get('closed') is closed and value.get('ready') is (not closed), 'STAGE_CLOSED_STATE_INVALID')
    if stage == 'setup':
        for key in ('selectedStartingSpent', 'paidToolVerified', 'explicitQuit', 'backupOnlyProtectedStore'):
            require(value.get(key) is True, 'SETUP_ACTUAL_FLOW_INCOMPLETE')
        require(value.get('coins') == 1250 and value.get('stars') == 0 and value.get('lives') == 4 and value.get('starting') == [4, 5, 3, 2] and value.get('tools') == [2, 3, 3, 3], 'SETUP_WALLET_INVALID')
    if stage in ('reopen', 'logout', 'recover', 'recovered', 'delete'):
        require(value.get('exactWalletRestored') is True, 'STAGE_WALLET_RESTORE_NOT_PROVEN')
    if stage == 'recover':
        require(value.get('backupOnlyProtectedStore') is True and value.get('recoveryChangedDeviceKey') is True, 'RECOVERY_KEY_ROTATION_NOT_PROVEN')
    if stage in ('closed', 'deleted'):
        require(value.get('noAutomaticGuest') is True, 'CLOSED_AUTO_GUEST_GUARD_NOT_PROVEN')
    if stage == 'delete':
        require(value.get('deletionConfirmed') is True, 'DELETION_NOT_CONFIRMED')
    wallet = None
    if not closed:
        for key in ('coins', 'stars', 'lives', 'completed', 'currentLevel', 'revision'):
            require(type(value.get(key)) is int and value[key] >= 0, 'STAGE_WALLET_SCALAR_INVALID')
        for key in ('starting', 'tools'):
            require(type(value.get(key)) is list and len(value[key]) == 4 and all(type(item) is int and item >= 0 for item in value[key]), 'STAGE_WALLET_INVENTORY_INVALID')
        wallet = {key: value[key] for key in ('coins', 'stars', 'lives', 'completed', 'currentLevel', 'revision', 'starting', 'tools')}
    return {'stage': stage, 'pid': value['pid'], 'checks': value['checks'], 'playerIdHash': value['playerIdHash'], 'serverKeyFingerprint': value['serverKeyFingerprint'], 'proofKeyFingerprint': value['proofKeyFingerprint'], 'wallet': wallet}


def validate_sequence(stages):
    """I/O-free full-stage relationships; physical process changes are external."""
    require([item.get('stage') for item in stages] == list(STAGES), 'ALL_EIGHT_STAGES_REQUIRED')
    require(len({item['pid'] for item in stages}) == 8, 'DISTINCT_ANDROID_PROCESSES_REQUIRED')
    require(len({item['playerIdHash'] for item in stages}) == 1 and len({item['proofKeyFingerprint'] for item in stages}) == 1, 'PERSISTED_OWNER_OR_PROOF_KEY_CHANGED')
    first, second = stages[0]['serverKeyFingerprint'], stages[4]['serverKeyFingerprint']
    require(first != second and all(item['serverKeyFingerprint'] == first for item in stages[:4]) and all(item['serverKeyFingerprint'] == second for item in stages[4:]), 'DEVICE_KEY_SEQUENCE_INVALID')
    require(all(stages[index]['wallet'] == stages[0]['wallet'] for index in (1, 4, 5)), 'PERSISTED_AUTHORITATIVE_WALLET_CHANGED')


class Runner:
    def __init__(self, args):
        self.args = args
        require(args.execute is True and args.serial == SERIAL, 'EXPLICIT_ROOT_QA2_EXECUTION_REQUIRED')
        self.target = validate_qa_target(SERIAL)
        self.project = args.project.resolve()
        require(self.project.is_relative_to((ROOT / '.verification-cache/Connected84').resolve()) and extended(self.project).is_dir(), 'PREPARED_ISOLATED_PROJECT_REQUIRED')
        self.out = args.out.resolve()
        require(self.out.is_relative_to(DEFAULT_OUT.resolve()), 'CONNECTED84_EVIDENCE_LOCATION_REQUIRED')
        self.run_id = uuid.uuid4().hex
        self.scope = 'qa84-' + self.run_id
        self.scope_hash = hashlib.sha256(self.scope.encode('ascii')).hexdigest()
        self.attempt = self.out / 'Runs' / self.run_id
        self.cache = ROOT / '.verification-cache/Connected84/Execution' / self.run_id
        extended(self.attempt).mkdir(parents=True, exist_ok=False)
        extended(self.cache).mkdir(parents=True, exist_ok=False)
        self.phase, self.before, self.gateway, self.reverse_owned, self.device_port = 'initial_inputs', None, None, False, None
        self.device_mutations_started = False
        self.gateway_server, self.gateway_server_bound = None, False
        self.report = {'status': 'PENDING_ROOT_ANDROID_CONNECTED84', 'startedUtc': utc(), 'runId': self.run_id, 'qa_serial': SERIAL, 'qa_target': self.target, 'scopeHash': self.scope_hash, 'package': PACKAGE, 'stages': [], 'errors': [], 'artifactSHA256': {}, 'externalSHA256': {}, 'helperSHA256': sha(Path(__file__)), 'ordinaryPackagesNeverStoppedOrInstalled': True, 'allAdbCommandsTargetSealedQA2': True, 'scope': 'Root-operated separate-package Android managed-session/account restart proof. Actual Home Play/paid Hammer/quit uses the pinned gateway worker. Existing host fixture has a labelled synthetic completed7 unlock; this is not a verified campaign-clear claim. No ordinary startup routing, physical-input, live payment/provider SDK, production/store, hardware-attestation or OS power-loss certification.', 'limitations': ['Ordinary verification-app persistent files/preferences are compared by hash only.', 'No commands target main instance0 or original QA1/5556; their whole-device byte state is not independently audited here.', 'No protected recovery/refresh/access record is read or exported by this harness.', 'Only a root-reviewed fixture reset flag may clear the separate fixture package.']}

    def command(self, arguments, *, timeout=30, check=True):
        try:
            result = subprocess.run([str(value) for value in arguments], capture_output=True, timeout=timeout, **hidden())
        except subprocess.TimeoutExpired:
            raise Failure('CHILD_PROCESS_TIMEOUT') from None
        except OSError:
            raise Failure('CHILD_PROCESS_START_FAILED') from None
        if check and result.returncode:
            raise Failure('CHILD_PROCESS_NONZERO', result.returncode)
        return result

    def adb(self, *parts, timeout=30, check=True):
        return self.command([self.args.adb, '-s', SERIAL, *parts], timeout=timeout, check=check)

    def bind(self, path):
        path = Path(path).resolve()
        self.report['externalSHA256'][path.relative_to(ROOT).as_posix()] = sha(path)

    def verify_project(self):
        preparation_path = self.project.parent / (self.project.name + '_Preparation.json')
        self.preparation = json.loads(extended(preparation_path).read_text('utf-8'))
        require(self.preparation['status'] == 'PREPARED_ISOLATED_CONNECTED84_ANDROID_PROJECT_NOT_BUILT' and self.preparation['package'] == PACKAGE and self.preparation['unity'] == '2022.3.62f3', 'FIXTURE_PREPARATION_BINDING_INVALID')
        require(self.preparation['project'] == self.project.relative_to(ROOT).as_posix(), 'FIXTURE_PROJECT_PATH_INVALID')
        for relative, expected in self.preparation['copiedSourceSHA256'].items():
            if relative.startswith('Assets/'):
                require(sha(self.project / relative) == expected, 'COPIED_FROZEN_ASSET_CHANGED')
        for relative, value in self.preparation['derivedPackageSHA256'].items():
            require(sha(self.project / relative) == value['afterSHA256'], 'DERIVED_JNI_PACKAGE_CHANGED')
        for relative, expected in self.preparation['generatedSHA256'].items():
            require(sha(self.project / relative) == expected, 'FIXTURE_GENERATED_INPUT_CHANGED')
        known = set(self.preparation['copiedSourceSHA256']) | set(self.preparation['generatedSHA256'])
        for path in extended(self.project / 'Assets').rglob('*'):
            if path.is_file() and path.suffix.lower() in ('.cs', '.dll', '.aar', '.jar', '.asmdef'):
                text = str(path)
                normal = Path(text[4:]) if text.startswith('\\\\?\\') else path
                require(normal.relative_to(self.project).as_posix() in known, 'UNMANIFESTED_EXECUTABLE_FIXTURE_INPUT')
        self.bind(preparation_path)
        self.report['sourceFreezeSHA256'] = self.preparation['baselineManifestSHA256']

    def build(self):
        if not self.args.build:
            return
        self.phase = 'hidden_unity_build'
        require(self.args.unity.resolve() == (EDITOR / 'Unity.exe').resolve(), 'PINNED_UNITY_EXECUTABLE_REQUIRED')
        # Read-only count; never kills or reuses another Unity process.
        found = self.command(['powershell.exe', '-NoProfile', '-Command', '(Get-Process -Name Unity -ErrorAction SilentlyContinue | Measure-Object).Count'])
        require(found.stdout.decode('ascii', 'strict').strip() == '0', 'ANOTHER_UNITY_PROCESS_IS_RUNNING')
        log = self.cache / 'UnityBuild.log'
        env = dict(os.environ)
        require(env.get('HOTR_BUILD_CHANNEL') != 'rustore', 'FIXTURE_PRODUCTION_CHANNEL_FORBIDDEN')
        # Match the existing pinned-tool runner; do not wait on optional SDK network listing.
        env['SDKMANAGER_OPTS'] = SDKMANAGER_OPTS
        started = utc()
        process = subprocess.Popen([str(self.args.unity), '-batchmode', '-projectPath', str(self.project), '-buildTarget', 'Android', '-executeMethod', 'Connected84FixtureBuild.Build', '-logFile', str(log)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, **hidden())
        try:
            code = process.wait(timeout=self.args.build_timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=15)
            raise Failure('FIXTURE_UNITY_BUILD_TIMEOUT') from None
        self.report['buildProcess'] = {'pid': process.pid, 'startedUtc': started, 'finishedUtc': utc(), 'exitCode': code, 'hidden': True}
        self.bind(log)
        require(code == 0, 'FIXTURE_UNITY_BUILD_FAILED')

    def verify_build(self):
        self.phase = 'fixture_apk_binding'
        self.apk = self.project / 'Build/Connected84.apk'
        build_path = self.project / 'Build/Build.json'
        build = json.loads(extended(build_path).read_text('utf-8'))
        require(build['status'] == 'PASS_ISOLATED_CONNECTED84_ANDROID_ASSEMBLY' and build['errors'] == 0 and build['package'] == PACKAGE and build['unity'] == '2022.3.62f3', 'FIXTURE_BUILD_NOT_PASSED')
        for flag in ('development', 'arm64', 'il2cpp', 'min26', 'noPaySdkDefine', 'exactBaselineAssetsBefore', 'exactBaselineAssetsAfter'):
            require(build.get(flag) is True, 'FIXTURE_BUILD_REQUIRED_FLAG_MISSING')
        require(build['baselineManifestSHA256'] == self.preparation['baselineManifestSHA256'] and build['apkSHA256'] == sha(self.apk), 'FIXTURE_BUILD_DIGEST_INVALID')
        aapt = self.args.aapt or sorted((SDK / 'build-tools').glob('*/aapt.exe'))[-1]
        raw = self.command([aapt, 'dump', 'badging', self.apk]).stdout.decode('utf-8', 'strict')
        require(re.search(r"^package: name='" + re.escape(PACKAGE) + "'", raw, re.MULTILINE) is not None and "native-code: 'arm64-v8a'" in raw and "sdkVersion:'26'" in raw and "launchable-activity: name='com.unity3d.player.UnityPlayerActivity'" in raw, 'APK_ISOLATED_PACKAGE_ABI_OR_API_INVALID')
        self.bind(build_path)
        self.report['apkSHA256'] = sha(self.apk)
        self.report['aaptSHA256'] = sha(aapt)

    def ordinary_state(self):
        result = {}
        groups = [('preferences', ['shell', 'run-as', ORDINARY, 'find', 'shared_prefs', '-type', 'f'], 'shared_prefs/', True), ('internalFiles', ['shell', 'run-as', ORDINARY, 'find', 'files', '-type', 'f'], 'files/', True), ('externalFiles', ['shell', 'find', '/sdcard/Android/data/' + ORDINARY + '/files', '-type', 'f'], '/sdcard/Android/data/' + ORDINARY + '/files/', False)]
        for name, command, prefix, internal in groups:
            listing = self.adb(*command, check=False)
            # Empty internal files are legitimate; absence of preferences or
            # ordinary Profiles prevents a false nonmutation claim.
            if listing.returncode != 0:
                require(name == 'internalFiles' and not listing.stdout.strip(), 'ORDINARY_DATA_ENUMERATION_UNAVAILABLE')
                missing = self.adb('shell', 'run-as', ORDINARY, 'test', '-e', 'files', check=False)
                require(missing.returncode == 1 and not missing.stderr.strip(), 'ORDINARY_INTERNAL_FILES_AUDIT_UNAVAILABLE')
            values = {}
            for path in listing.stdout.decode('utf-8', 'strict').splitlines():
                require(path.startswith(prefix) and re.fullmatch('[A-Za-z0-9_./-]+', path) is not None and '..' not in Path(path).parts, 'ORDINARY_HASH_PATH_REJECTED')
                parts = ['shell', 'run-as', ORDINARY, 'sha256sum', path] if internal else ['shell', 'sha256sum', path]
                found = self.adb(*parts).stdout.decode('ascii', 'strict').split()
                require(found and digest(found[0]), 'ORDINARY_HASH_UNAVAILABLE')
                values[path.removeprefix(prefix)] = found[0]
            result[name] = values
        require(result['preferences'] and any(name.startswith('Profiles/') and name.endswith('.json') for name in result['externalFiles']), 'ORDINARY_PREFERENCES_AND_SAVE_REQUIRED')
        return result

    def start_gateway(self):
        self.phase = 'own_gateway_start'
        require(self.args.bundle and self.args.approval and digest(self.args.approval_sha256) and self.args.continue_job, 'PINNED_GATEWAY_WORKER_INPUTS_REQUIRED')
        require(sha(self.args.approval) == self.args.approval_sha256, 'PINNED_APPROVAL_HASH_CHANGED')
        host_dir = ROOT / '.verification-cache/ServerGameplay83/HTTP' / ('connected84-' + self.run_id)
        require(not extended(host_dir).exists(), 'FRESH_GATEWAY_DIRECTORY_REQUIRED')
        log = self.cache / 'Gateway.log'
        self.gateway_log = extended(log).open('wb')
        arguments = [sys.executable, str(GATEWAY_SCRIPT), '--directory', str(host_dir), '--run-id', self.run_id, '--bundle', str(self.args.bundle.resolve()), '--approval', str(self.args.approval.resolve()), '--approval-sha256', self.args.approval_sha256, '--continue-job', str(self.args.continue_job.resolve())]
        allowed = {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'COMSPEC', 'PATH', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMDATA'}
        environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        environment['HOTR_BACKEND_MODE'] = 'local'
        self.gateway = subprocess.Popen(arguments, cwd=ROOT, stdout=self.gateway_log, stderr=subprocess.STDOUT, env=environment, **hidden())
        self.report['gateway'] = {'owned': True, 'pid': self.gateway.pid, 'launcherPid': self.gateway.pid, 'connectionReady': False, 'credentialEnvironmentInherited': False}
        connection = host_dir / 'connection.json'
        end = time.monotonic() + 45
        while not extended(connection).is_file():
            require(self.gateway.poll() is None and time.monotonic() < end, 'GATEWAY_START_NOT_READY')
            time.sleep(.2)
        value = json.loads(extended(connection).read_text('utf-8'))
        parsed = urlsplit(value['origin'])
        require(value['runId'] == self.run_id and type(value.get('pid')) is int and value['pid'] > 0 and parsed.scheme == 'http' and parsed.hostname == '127.0.0.1' and parsed.port and parsed.path in ('', '/') and not parsed.query and not parsed.fragment and not parsed.username, 'OWN_GATEWAY_CONNECTION_INVALID')
        self.bind_gateway_process(value['pid'], arguments)
        self.gateway_port = parsed.port
        self.report['gateway'].update({'connectionReady': True, 'connectionSHA256': sha(connection), 'approvalSHA256': self.args.approval_sha256, 'scope': value['scope'], 'syntheticCompleted7Unlock': True, 'noOperatorSeedUsedByLevel1': True})
        for path in (connection, GATEWAY_SCRIPT, self.args.approval, self.args.continue_job):
            self.bind(path)

    def bind_gateway_process(self, server_pid, arguments):
        # Venv python.exe can be a launcher whose real Python child serves HTTP.
        # Open first, then bind CIM metadata to this retained kernel object.
        self.gateway_server = RetainedWindowsProcess(server_pid)
        process = self.gateway_server
        query = ("$p=Get-CimInstance -ClassName Win32_Process -Filter 'ProcessId = " + str(server_pid) + "';"
                 "if($null -eq $p){exit 3};"
                 "@{pid=[long]$p.ProcessId;parentPid=[long]$p.ParentProcessId;"
                 "creationTicks=$p.CreationDate.ToUniversalTime().ToFileTimeUtc().ToString([Globalization.CultureInfo]::InvariantCulture);"
                 "executablePath=$p.ExecutablePath;commandLine=$p.CommandLine}|ConvertTo-Json -Compress")
        raw = self.command(['powershell.exe', '-NoProfile', '-Command', query], timeout=15).stdout
        metadata = json.loads(raw.decode('utf-8-sig', 'strict'))
        expected_parent = os.getpid() if server_pid == self.gateway.pid else self.gateway.pid
        require(type(metadata) is dict and metadata.get('pid') == server_pid and metadata.get('parentPid') == expected_parent, 'GATEWAY_PROCESS_PARENT_INVALID')
        require(type(metadata.get('creationTicks')) is str and re.fullmatch('[0-9]{1,20}', metadata['creationTicks']), 'GATEWAY_CIM_CREATION_INVALID')
        # CIM timestamps have microsecond precision; FILETIME has 100 ns units.
        require(abs(int(metadata['creationTicks']) - process.created_ticks) < 10, 'GATEWAY_PROCESS_IDENTITY_CHANGED')
        require(process.created_ticks >= process.creation_of(int(self.gateway._handle)) and self.gateway.poll() is None and not process.wait(0), 'GATEWAY_PROCESS_LIFETIME_INVALID')
        allowed_images = {Path(sys.executable).resolve(), Path(getattr(sys, '_base_executable', sys.executable)).resolve()}
        require(Path(process.image).resolve() in allowed_images and type(metadata.get('executablePath')) is str and Path(metadata['executablePath']).resolve() == Path(process.image).resolve(), 'GATEWAY_PROCESS_EXECUTABLE_INVALID')
        actual_arguments = windows_argument_vector(metadata.get('commandLine'))
        require(len(actual_arguments) == len(arguments) and actual_arguments[1:] == arguments[1:], 'GATEWAY_PROCESS_ARGUMENTS_INVALID')
        self.gateway_server_bound = True
        self.report['gateway'].update({'pid': server_pid, 'serverPid': server_pid, 'serverParentPid': expected_parent, 'serverCreatedFileTime': str(process.created_ticks), 'retainedQuerySynchronizeHandle': True, 'exactArgumentsMatched': True, 'serverExecutableSHA256': sha(process.image), 'venvRedirectorChild': server_pid != self.gateway.pid})

    def reverse(self):
        self.phase = 'own_adb_reverse'
        self.reverse_before = self.adb('reverse', '--list').stdout.decode('utf-8', 'strict').splitlines()
        self.device_port = self.args.device_port or self.gateway_port
        require(1024 <= self.device_port <= 65535 and all('tcp:' + str(self.device_port) not in row.split() for row in self.reverse_before), 'DEVICE_REVERSE_PORT_ALREADY_OWNED')
        self.adb('reverse', '--no-rebind', 'tcp:' + str(self.device_port), 'tcp:' + str(self.gateway_port))
        self.reverse_owned = True
        self.origin = 'http://127.0.0.1:' + str(self.device_port)
        self.origin_hash = hashlib.sha256(self.origin.encode('ascii')).hexdigest()
        self.report['originHash'] = self.origin_hash
        self.report['adbReverse'] = {'ownedDevicePort': self.device_port, 'ownHostPort': self.gateway_port, 'preexisting': self.reverse_before, 'noRebind': True}

    def read_report(self, stage):
        require(stage in STAGES and digest(self.scope_hash), 'REDACTED_REPORT_ALLOWLIST_FAILED')
        relative = 'Connected84/Reports/' + self.scope_hash + '/Stage_' + stage + '.json'
        external = '/sdcard/Android/data/' + PACKAGE + '/files/' + relative
        for command in (['shell', 'cat', external],):
            # The Android fixture writes this redacted report to its external
            # persistentDataPath. One bounded shell read avoids three parallel
            # run-as/exec-out channels during each startup poll on LDPlayer.
            value = self.adb(*command, check=False, timeout=15)
            if value.returncode == 0 and 0 < len(value.stdout) <= 65536:
                try:
                    decoded = json.loads(value.stdout.decode('utf-8', 'strict'))
                except (ValueError, UnicodeError):
                    continue
                require(type(decoded) is dict and not {'backupSecret', 'accessToken', 'refreshToken', 'recoverySecret', 'signature', 'publicKey', 'token', 'authorization'}.intersection(decoded), 'REPORT_CONTAINS_UNEXPECTED_CREDENTIAL_FIELD')
                return value.stdout, decoded
        return None

    def stages(self):
        for stage in STAGES:
            self.phase = 'stage_' + stage + '_stop'
            self.adb('shell', 'am', 'force-stop', PACKAGE)
            require(not self.adb('shell', 'pidof', PACKAGE, check=False).stdout.strip(), 'FIXTURE_PREVIOUS_PROCESS_STILL_RUNNING')
            stopped = utc()
            self.phase = 'stage_' + stage + '_launch'
            self.adb('shell', 'am', 'start', '-n', ACTIVITY, '--es', 'connected84_scope', self.scope, '--es', 'connected84_stage', stage, '--es', 'connected84_origin', self.origin)
            end = time.monotonic() + 300
            pair = None
            while time.monotonic() < end:
                pair = self.read_report(stage)
                if pair is not None:
                    break
                time.sleep(.5)
            require(pair is not None, 'BOUNDED_STAGE_REPORT_MISSING')
            raw, value = pair
            require(value.get('scopeHash') == self.scope_hash and value.get('stage') == stage, 'STALE_STAGE_REPORT_REJECTED')
            path = self.attempt / ('Stage_' + stage + '.json')
            extended(path).write_bytes(raw)
            self.report['artifactSHA256'][path.relative_to(self.out).as_posix()] = sha(path)
            checked = validate_stage(value, stage, self.scope_hash, self.origin_hash)
            current = self.adb('shell', 'pidof', PACKAGE).stdout.decode('ascii', 'strict').strip()
            require(current == str(checked['pid']), 'REPORT_DOES_NOT_MATCH_ACTUAL_LIVE_PID')
            checked.update({'precedingForceStopUtc': stopped, 'observedLivePid': int(current), 'pulledUtc': utc()})
            self.report['stages'].append(checked)
        validate_sequence(self.report['stages'])

    def execute(self):
        try:
            self.verify_project()
            self.build()
            self.verify_project()
            self.verify_build()
            self.phase = 'sealed_qa2_readiness'
            end = time.monotonic() + 20
            while True:
                value = self.adb('get-state', check=False, timeout=5)
                if value.returncode == 0 and value.stdout.strip() == b'device':
                    break
                require(time.monotonic() < end, 'SEALED_QA2_NOT_READY')
                time.sleep(.5)
            self.report['ordinaryAttemptGuard'] = assert_no_active_attempt(lambda *parts: self.adb(*parts).stdout.decode('utf-8', 'strict'))
            self.before = self.ordinary_state()
            self.report['ordinaryDataBefore'] = self.before
            self.device_mutations_started = True
            self.phase = 'own_fixture_install'
            require(b'Success' in self.adb('install', '-r', str(self.apk), timeout=180).stdout, 'FIXTURE_INSTALL_FAILED')
            if self.args.reset_fixture_data:
                self.adb('shell', 'am', 'force-stop', PACKAGE)
                require(self.adb('shell', 'pm', 'clear', PACKAGE).stdout.strip() == b'Success', 'EXPLICIT_FIXTURE_RESET_FAILED')
            self.report['explicitFixtureDataReset'] = self.args.reset_fixture_data
            installed = self.adb('shell', 'pm', 'path', PACKAGE).stdout.decode('utf-8', 'strict').strip()
            require(re.fullmatch(r'package:/data/app/(?:~~[A-Za-z0-9_=+-]+/)?com\.heartoftherain\.connected84fixture-[A-Za-z0-9_=+-]+/base\.apk', installed) is not None, 'INSTALLED_FIXTURE_PATH_INVALID')
            installed_hash = self.adb('shell', 'sha256sum', installed.removeprefix('package:')).stdout.decode('ascii', 'strict').split()[0]
            require(installed_hash == self.report['apkSHA256'], 'INSTALLED_FIXTURE_APK_DIFFERS')
            self.report['installedApkSHA256'] = installed_hash
            self.start_gateway()
            self.reverse()
            self.stages()
            self.verify_project()
            require(sha(self.apk) == self.report['apkSHA256'], 'APK_CHANGED_DURING_RUN')
            self.report['status'] = 'PASS_ACTUAL_ANDROID_CONNECTED84_DISTINCT_PROCESS_LIFECYCLE'
        except Exception as error:
            self.report['status'] = 'FAIL_ACTUAL_ANDROID_CONNECTED84_DISTINCT_PROCESS_LIFECYCLE'
            self.report['failurePhase'] = self.phase
            import traceback
            self.report['failureLocations'] = [{'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name} for frame in traceback.extract_tb(error.__traceback__)]
            self.report['errors'].append(error.code if isinstance(error, Failure) else type(error).__name__)
        finally:
            # Remove only resources this run owns. Never stop/clear/install a
            # normal package, remove other reverses or terminate shared hosts.
            if self.device_mutations_started:
                try:
                    self.adb('shell', 'am', 'force-stop', PACKAGE)
                    self.report['ownFixtureStopped'] = not self.adb('shell', 'pidof', PACKAGE, check=False).stdout.strip()
                    require(self.report['ownFixtureStopped'], 'OWN_FIXTURE_PROCESS_NOT_STOPPED')
                except Exception:
                    self.report['errors'].append('OWN_FIXTURE_STOP_UNAVAILABLE')
            if self.reverse_owned:
                try:
                    self.adb('reverse', '--remove', 'tcp:' + str(self.device_port))
                    after = self.adb('reverse', '--list').stdout.decode('utf-8', 'strict').splitlines()
                    self.report['adbReverse']['afterOwnCleanup'] = after
                    require(sorted(after) == sorted(self.reverse_before), 'UNRELATED_REVERSE_STATE_CHANGED')
                except Exception:
                    self.report['errors'].append('OWN_REVERSE_CLEANUP_UNAVAILABLE')
            if self.gateway is not None:
                try:
                    self.gateway.terminate()
                    try:
                        self.gateway.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.gateway.kill(); self.gateway.wait(timeout=10)
                    self.report['gateway']['ownLauncherStopped'] = self.gateway.poll() is not None
                    require(self.report['gateway']['ownLauncherStopped'], 'OWN_GATEWAY_LAUNCHER_NOT_STOPPED')
                    if self.gateway_server_bound:
                        self.report['gateway']['ownProcessStopped'] = self.gateway_server.wait(10)
                        require(self.report['gateway']['ownProcessStopped'], 'OWN_GATEWAY_SERVER_NOT_STOPPED')
                except Exception as error:
                    self.report['gateway']['cleanupError'] = error.code if isinstance(error, Failure) else 'OWN_GATEWAY_STOP_UNAVAILABLE'
                    self.report['errors'].append('OWN_GATEWAY_STOP_UNAVAILABLE')
                finally:
                    if self.gateway_server is not None:
                        self.gateway_server.close()
                    self.gateway_log.close()
                    self.bind(self.cache / 'Gateway.log')
            elif hasattr(self, 'gateway_log'):
                self.gateway_log.close()
            if self.before is not None:
                try:
                    after = self.ordinary_state()
                    self.report['ordinaryDataAfter'] = after
                    self.report['ordinaryDataUnchanged'] = self.before == after
                    require(self.before == after, 'ORDINARY_DATA_CHANGED')
                except Exception as audit_error:
                    self.report['ordinaryAfterAuditError'] = audit_error.code if isinstance(audit_error, Failure) else type(audit_error).__name__
                    self.report['errors'].append('ORDINARY_AFTER_AUDIT_UNAVAILABLE_OR_CHANGED')
            try:
                require(validate_qa_target(SERIAL) == self.target, 'SEALED_TARGET_RECORD_CHANGED')
            except Exception:
                self.report['errors'].append('SEALED_TARGET_AFTER_AUDIT_FAILED')
            if self.report['errors']:
                self.report['status'] = 'FAIL_ACTUAL_ANDROID_CONNECTED84_DISTINCT_PROCESS_LIFECYCLE'
            self.report['finishedUtc'] = utc()
            extended(self.attempt / 'Report.json').write_text(json.dumps(self.report, indent=2) + '\n', encoding='utf-8')
        return self.report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Explicit root-reviewed process/build/device execution opt-in')
    parser.add_argument('--build', action='store_true', help='Build the already prepared fixture with hidden pinned Unity')
    parser.add_argument('--reset-fixture-data', action='store_true', help='Explicitly clear ONLY the separate fixture package after installation; no ordinary data is touched')
    parser.add_argument('--serial', choices=[SERIAL], default=SERIAL)
    parser.add_argument('--project', type=Path, default=DEFAULT_PROJECT)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--unity', type=Path, default=EDITOR / 'Unity.exe')
    parser.add_argument('--adb', type=Path, default=SDK / 'platform-tools/adb.exe')
    parser.add_argument('--aapt', type=Path)
    parser.add_argument('--build-timeout', type=int, default=1800)
    parser.add_argument('--device-port', type=int)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--approval', type=Path, required=True)
    parser.add_argument('--approval-sha256', required=True)
    parser.add_argument('--continue-job', type=Path, required=True)
    args = parser.parse_args()
    require(args.execute and 60 <= args.build_timeout <= 3600, 'EXPLICIT_BOUNDED_ROOT_EXECUTION_REQUIRED')
    result = Runner(args).execute()
    print(json.dumps({'status': result['status'], 'runId': result['runId'], 'stageCount': len(result['stages']), 'errors': result['errors']}))
    raise SystemExit(0 if result['status'].startswith('PASS_') else 1)


if __name__ == '__main__':
    main()
