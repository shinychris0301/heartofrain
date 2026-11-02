"""Explicit orchestration guards. Import/tests never inspect or mutate the host.

Listener inspection uses Windows metadata and one bounded host:version request.
It never starts adb.exe, contacts a device, or issues an ADB lifecycle command.
The preference lease is limited to two existing DWORD values and an owned mutex.
"""
from __future__ import annotations
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

REGISTRY_KEY = r'Software\Unity Technologies\Unity Editor 5.x'
PREFERENCE_NAMES = (
    'AndroidADBKillExternalInstance_h3576746831',
    'AndroidADBKillServerOnExit_h1981668703',
)
MUTEX_NAME = r'Local\HOTR127_ExactAdbLifecyclePreferenceLease'
REG_DWORD = 4


class IsolationError(RuntimeError):
    pass


def _need(ok, code):
    if not ok:
        raise IsolationError(code)


def _port(port):
    _need(type(port) is int and 1 <= port <= 65535, 'CanonicalAdbPortRequired127')
    return port


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def _windows_observer(port):
    _need(os.name == 'nt', 'WindowsListenerInspectionRequired127')
    # The sole interpolation is a previously validated integer. No executable
    # paths, process command lines, device identifiers or environment are exported.
    script = r'''$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$connections127=@(Get-NetTCPConnection -State Listen -ErrorAction Stop|Where-Object{$_.LocalPort -eq PORT127})
if($connections127.Count -eq 0){[pscustomobject]@{listeners=@();process=$null}|ConvertTo-Json -Compress -Depth 4;exit}
$ownerIds127=@($connections127|Select-Object -ExpandProperty OwningProcess -Unique)
if($ownerIds127.Count -ne 1){throw 'MultipleListenerOwners127'}
$ownerRecord127=Get-CimInstance Win32_Process -Filter ('ProcessId='+$ownerIds127[0])
if(!$ownerRecord127 -or !$ownerRecord127.ExecutablePath -or !$ownerRecord127.CreationDate){throw 'ListenerProcessMetadataMissing127'}
[pscustomobject]@{listeners=@($connections127|ForEach-Object{[pscustomobject]@{address=$_.LocalAddress;pid=[int]$_.OwningProcess}});process=[pscustomobject]@{pid=[int]$ownerRecord127.ProcessId;imagePath=$ownerRecord127.ExecutablePath;creationTime=$ownerRecord127.CreationDate.ToUniversalTime().ToString('o')}}|ConvertTo-Json -Compress -Depth 4
'''.replace('PORT127', str(_port(port)))
    result = subprocess.run(
        ['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoLogo',
         '-NoProfile', '-NonInteractive', '-Command', script],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    _need(result.returncode == 0 and len(result.stdout) <= 16384,
          'BoundedListenerMetadataRequired127')
    try:
        value = json.loads(result.stdout.decode('utf-8-sig'))
        listeners = value['listeners']
        _need(type(listeners) is list and len(listeners) <= 8,
              'BoundedListenerSetRequired127')
        if not listeners:
            _need(value['process'] is None, 'AbsentListenerHasNoProcess127')
            return {'port': port, 'listeners': [], 'process': None,
                    'protocolVersion': None}
        process = value['process']
        _need(type(process['pid']) is int and process['pid'] > 0
              and all(type(row['pid']) is int and row['pid'] == process['pid']
                      and type(row['address']) is str for row in listeners),
              'SingleListenerIdentityRequired127')
        image = Path(process['imagePath']).resolve(strict=True)
        _need(image.is_file() and image.name.lower() == 'adb.exe'
              and type(process['creationTime']) is str
              and len(process['creationTime']) <= 80,
              'AdbExecutableIdentityRequired127')
        return {'port': port,
                'listeners': sorted(listeners, key=lambda row: row['address']),
                'process': {'pid': process['pid'], 'imagePath': str(image),
                            'creationTime': process['creationTime'],
                            'imageSHA256': _sha(image)},
                'protocolVersion': None}
    except IsolationError:
        raise
    except Exception:
        raise IsolationError('ListenerMetadataInvalid127') from None


def _recv_exact(stream, count, deadline):
    result = bytearray()
    while len(result) < count:
        remaining = deadline - time.monotonic()
        _need(remaining > 0, 'AdbVersionDeadlineExceeded127')
        stream.settimeout(min(1.0, remaining))
        chunk = stream.recv(count - len(result))
        _need(time.monotonic() <= deadline, 'AdbVersionDeadlineExceeded127')
        _need(bool(chunk), 'AdbVersionResponseTruncated127')
        result.extend(chunk)
    return bytes(result)


def _version(port, connector):
    try:
        deadline = time.monotonic() + 1.5
        with connector(('127.0.0.1', port), timeout=1.0) as stream:
            stream.settimeout(1.0)
            stream.sendall(b'000chost:version')
            _need(_recv_exact(stream, 4, deadline) == b'OKAY', 'AdbVersionNotOkay127')
            length = _recv_exact(stream, 4, deadline)
            _need(re.fullmatch(b'[0-9a-fA-F]{4}', length) is not None
                  and int(length, 16) == 4, 'BoundedAdbVersionRequired127')
            version = _recv_exact(stream, 4, deadline)
            _need(re.fullmatch(b'[0-9a-fA-F]{4}', version) is not None,
                  'CanonicalAdbVersionRequired127')
            return version.decode('ascii').lower()
    except IsolationError:
        raise
    except Exception:
        raise IsolationError('AdbVersionProbeUnavailable127') from None


def capture_adb_listener(port, allow_absent=False, *, _observer=None, _connector=None):
    """Read listener identity twice around a host-only version request; never autostart."""
    _port(port)
    _need(type(allow_absent) is bool, 'BooleanAbsentPolicyRequired127')
    observe = _observer or _windows_observer
    before = observe(port)
    if not before['listeners']:
        _need(allow_absent, 'RequiredAdbListenerAbsent127')
        return before
    version = _version(port, _connector or socket.create_connection)
    after = observe(port)
    _need(before == after, 'AdbListenerChangedDuringProbe127')
    return dict(before, protocolVersion=version)


def require_same_listener(before, after):
    _need(type(before) is dict and type(after) is dict and before == after,
          'ProtectedAdbListenerChanged127')


assert_shared_unchanged = require_same_listener


class _WindowsPreferences:
    def __init__(self):
        _need(os.name == 'nt', 'WindowsPreferenceLeaseRequired127')
        import winreg
        self.registry = winreg

    def acquire(self, name, timeout):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.WaitForSingleObject.restype = ctypes.c_uint32
        kernel.ReleaseMutex.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateMutexW(None, False, name)
        _need(bool(handle), 'PreferenceMutexCreateFailed127')
        result = kernel.WaitForSingleObject(handle, int(timeout * 1000))
        if result != 0:
            if result == 0x80:
                kernel.ReleaseMutex(handle)
            kernel.CloseHandle(handle)
            raise IsolationError('PreferenceLeaseAbandoned127' if result == 0x80
                                 else 'PreferenceLeaseBusy127')
        return kernel, handle

    def release(self, token):
        kernel, handle = token
        try:
            _need(bool(kernel.ReleaseMutex(handle)), 'PreferenceMutexReleaseFailed127')
        finally:
            kernel.CloseHandle(handle)

    def read(self, name):
        _need(name in PREFERENCE_NAMES, 'ExactPreferenceNameRequired127')
        with self.registry.OpenKey(self.registry.HKEY_CURRENT_USER, REGISTRY_KEY,
                                   0, self.registry.KEY_QUERY_VALUE) as key:
            value, kind = self.registry.QueryValueEx(key, name)
        return kind, value

    def write(self, name, value):
        _need(name in PREFERENCE_NAMES and type(value) is int and value in (0, 1),
              'ExactBooleanPreferenceWriteRequired127')
        with self.registry.OpenKey(self.registry.HKEY_CURRENT_USER, REGISTRY_KEY,
                                   0, self.registry.KEY_SET_VALUE) as key:
            self.registry.SetValueEx(key, name, 0, self.registry.REG_DWORD, value)


class EditorPrefsLease:
    """Two-key lease. Conflicts leave values untouched and block, rather than overwrite."""
    def __init__(self, editor_closed, *, checkpoint=None, _backend=None):
        _need(callable(editor_closed), 'EditorClosureCallbackRequired127')
        _need(checkpoint is None or callable(checkpoint), 'LeaseCheckpointCallbackRequired127')
        self.editor_closed = editor_closed
        self.checkpoint = checkpoint
        self.backend = _backend
        self.token = None
        self.original = None
        self._result = {'status': 'NOT_STARTED', 'restored': False,
                        'registryKey': REGISTRY_KEY, 'preferenceNames': list(PREFERENCE_NAMES)}
        self.report = self._result

    def __enter__(self):
        try:
            self.backend = self.backend or _WindowsPreferences()
            self.token = self.backend.acquire(MUTEX_NAME, 5)
            original = {name: self.backend.read(name) for name in PREFERENCE_NAMES}
            _need(all(type(pair) is tuple and len(pair) == 2 and pair[0] == REG_DWORD
                      and type(pair[1]) is int and pair[1] in (0, 1)
                      for pair in original.values()), 'ExistingDwordPreferencesRequired127')
            _need(all(self.backend.read(name) == pair for name, pair in original.items()),
                  'PreferenceChangedBeforeLease127')
            self.original = original
            self._result['originalValues'] = {name: pair[1] for name, pair in original.items()}
            self._result['status'] = 'CAPTURED_BEFORE_MUTATION'
            if self.checkpoint is not None:
                self.checkpoint(json.loads(json.dumps(self._result)))
            _need(all(self.backend.read(name) == pair for name, pair in original.items()),
                  'PreferenceChangedBeforeMutation127')
            for name in PREFERENCE_NAMES:
                self.backend.write(name, 0)
            _need(all(self.backend.read(name) == (REG_DWORD, 0) for name in PREFERENCE_NAMES),
                  'PreferenceLeaseWriteUnconfirmed127')
            self._result['status'] = 'LEASE_ACTIVE'
            return self
        except Exception:
            self._result['status'] = 'BLOCKED_PREFERENCE_LEASE_SETUP'
            if self.token is not None:
                self.backend.release(self.token)
                self.token = None
            raise IsolationError('PreferenceLeaseSetupBlocked127') from None

    def __exit__(self, exc_type, exc_value, traceback):
        blocked = None
        try:
            try:
                closed = self.editor_closed()
            except Exception:
                closed = False
            if closed is not True:
                blocked = 'BLOCKED_OWNED_EDITOR_NOT_CLOSED'
            elif not all(self.backend.read(name) == (REG_DWORD, 0)
                         for name in PREFERENCE_NAMES):
                blocked = 'BLOCKED_PREFERENCE_OWNERSHIP_LOST'
            else:
                for name in PREFERENCE_NAMES:
                    self.backend.write(name, self.original[name][1])
                _need(all(self.backend.read(name) == pair
                          for name, pair in self.original.items()),
                      'PreferenceRestoreUnconfirmed127')
                self._result.update(status='RESTORED', restored=True)
        except Exception:
            blocked = 'BLOCKED_PREFERENCE_RESTORE_FAILED'
        finally:
            if blocked:
                self._result['status'] = blocked
            if self.token is not None:
                try:
                    self.backend.release(self.token)
                finally:
                    self.token = None
        if blocked and exc_type is None:
            raise IsolationError('PreferenceLeaseRestorationBlocked127')
        return False
