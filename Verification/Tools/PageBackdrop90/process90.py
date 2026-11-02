"""Read-only Windows Unity process selection; unknown unity.exe always blocks.

The only exceptions are the existing exact Unity Hub service image and the
current user's exact LocalAppData Unity auth broker, with its sole exact serve
flag and a Windows-validated Unity Technologies SF Authenticode signature.
No process is stopped or started by this module.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import unity_pids as named_unity_pids

HUB = Path(r'C:\Program Files\Unity Hub\resources\unity.exe')
BROKER_FLAG = '--internal-auth-broker-serve'


def local_app_data():
    """Use the Windows known-folder identity rather than a caller's env path."""
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
    shell.SHGetKnownFolderPath.restype = ctypes.c_long
    ole = ctypes.WinDLL('ole32', use_last_error=True)
    ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    guid = ctypes.create_string_buffer(uuid.UUID('F1B32785-6FBA-4FCF-9D55-7B8E7F157091').bytes_le)
    value = ctypes.c_void_p()
    if shell.SHGetKnownFolderPath(guid, 0, None, ctypes.byref(value)) != 0 or not value.value:
        raise RuntimeError('WindowsLocalAppDataIdentityUnavailable')
    try:
        return Path(ctypes.wstring_at(value.value)).resolve()
    finally:
        ole.CoTaskMemFree(value)


def command_arguments(command):
    """Tokenize with the same Windows API, rejecting extra broker arguments."""
    if not command or '\x00' in command or len(command) > 32768:
        raise RuntimeError('UnityProcessCommandLineInvalid')
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    count = ctypes.c_int()
    arguments = shell.CommandLineToArgvW(command, ctypes.byref(count))
    if not arguments:
        raise RuntimeError('UnityProcessCommandLineUnavailable')
    try:
        return [arguments[index] for index in range(count.value)]
    finally:
        kernel.LocalFree(arguments)


def process_details(pid, *, include_command=False):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        raise RuntimeError('UnityProcessImageUnavailable')
    try:
        size = wintypes.DWORD(32768)
        path = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
            raise RuntimeError('UnityProcessImageUnavailable')
        image = Path(path.value).resolve()
        if not include_command:
            return image, None
        class UnicodeString(ctypes.Structure):
            _fields_ = [('length', wintypes.USHORT), ('maximumLength', wintypes.USHORT), ('buffer', ctypes.c_void_p)]
        native = ctypes.WinDLL('ntdll')
        native.NtQueryInformationProcess.argtypes = [wintypes.HANDLE, wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG, ctypes.POINTER(wintypes.ULONG)]
        native.NtQueryInformationProcess.restype = ctypes.c_long
        needed = wintypes.ULONG()
        native.NtQueryInformationProcess(handle, 60, None, 0, ctypes.byref(needed))
        if not ctypes.sizeof(UnicodeString) <= needed.value <= 131072:
            raise RuntimeError('UnityProcessCommandLineUnavailable')
        storage = ctypes.create_string_buffer(needed.value)
        if native.NtQueryInformationProcess(handle, 60, storage, len(storage), ctypes.byref(needed)) != 0:
            raise RuntimeError('UnityProcessCommandLineUnavailable')
        value = UnicodeString.from_buffer(storage)
        start = ctypes.addressof(storage)
        if value.length % 2 or not value.buffer or value.length > value.maximumLength or not start <= value.buffer <= value.buffer + value.length <= start + len(storage):
            raise RuntimeError('UnityProcessCommandLineInvalid')
        return image, command_arguments(ctypes.wstring_at(value.buffer, value.length // 2))
    finally:
        kernel.CloseHandle(handle)


def authenticode(path):
    """Windows trust-chain validation; an unreadable/invalid signature blocks."""
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetSystemDirectoryW.argtypes = [wintypes.LPWSTR, wintypes.UINT]
    kernel.GetSystemDirectoryW.restype = wintypes.UINT
    location = ctypes.create_unicode_buffer(32768)
    length = kernel.GetSystemDirectoryW(location, len(location))
    if not 0 < length < len(location):
        raise RuntimeError('WindowsSystemDirectoryUnavailable')
    powershell = Path(location.value) / 'WindowsPowerShell/v1.0/powershell.exe'
    script = r'''$ErrorActionPreference='Stop'
$s=Get-AuthenticodeSignature -LiteralPath $env:HOTR_PROCESS90_BINARY
$name=$null
$subject=$null
if($s.SignerCertificate){$name=$s.SignerCertificate.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName,$false);$subject=$s.SignerCertificate.Subject}
[pscustomobject]@{status=$s.Status.ToString();simpleName=$name;subject=$subject}|ConvertTo-Json -Compress
'''
    environment = dict(os.environ, HOTR_PROCESS90_BINARY=str(path))
    result = subprocess.run([str(powershell), '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', base64.b64encode(script.encode('utf-16-le')).decode('ascii')],
                            env=environment, capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode or len(result.stdout) > 16384:
        raise RuntimeError('UnityBrokerAuthenticodeUnavailable')
    try:
        value = json.loads(result.stdout.decode('utf-8-sig'))
    except (ValueError, UnicodeError) as error:
        raise RuntimeError('UnityBrokerAuthenticodeUnavailable') from error
    return value


def approved_broker(image, arguments, signature, broker):
    return (Path(image).resolve() == Path(broker).resolve() and isinstance(arguments, list) and len(arguments) == 2
            and Path(arguments[0]).resolve() == Path(broker).resolve() and arguments[1] == BROKER_FLAG
            and isinstance(signature, dict) and signature.get('status') == 'Valid'
            and signature.get('simpleName') == 'Unity Technologies SF'
            and isinstance(signature.get('subject'), str)
            and re.search(r'(?:^|,\s*)CN=Unity Technologies SF(?:,|$)', signature['subject']) is not None)


def unity_pids():
    if os.name != 'nt':
        raise RuntimeError('WindowsProcessIdentityRequired')
    broker = local_app_data() / 'Unity/bin/unity.exe'
    blocking = []
    for pid in named_unity_pids():
        image, _ = process_details(pid)
        if image == HUB.resolve():
            continue  # Exact existing86 exception; never stop the Hub service.
        if image == broker.resolve():
            current_image, arguments = process_details(pid, include_command=True)
            if approved_broker(current_image, arguments, authenticode(broker), broker):
                continue
        blocking.append(pid)
    return blocking
