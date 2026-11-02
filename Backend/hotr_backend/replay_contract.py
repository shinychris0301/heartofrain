"""Explicit local broker contract for the pinned Unity model-only executable.

No HTTP endpoint, wallet mutation or production activation. Job syntax and
receipt IDs are not authority: a future authenticated gateway must assemble
jobs from its own attempt/start/tool/continue ledger and bind every submission.
Windows Job Objects bound a trusted worker, not an untrusted-code sandbox.
"""
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

MAX_BYTES = 1_048_576
STATES = ('Playing', 'Won', 'Out of moves', 'No legal moves')


class ReplayError(Exception):
    """Sanitized code only; never carries job contents, paths or process logs."""


class TrustedModelFault(ReplayError):
    """Only the approved process's exact job-bound model guard may create this."""
    def __init__(self, proof):
        super().__init__('model_fault')
        self.proof = proof


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def _require(condition, code='invalid_replay_contract'):
    if not condition:
        raise ReplayError(code)


def _fields(value, names):
    _require(type(value) is dict and set(value) == set(names.split()))
    return value


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _hash(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _id(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{32}', value) is not None


def _receipt(value):
    return isinstance(value, str) and re.fullmatch('wallet/[0-9a-f]{64}', value) is not None


def strict_json(raw):
    _require(isinstance(raw, bytes) and 2 <= len(raw) <= MAX_BYTES, 'replay_io_size')
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def constant(value):
        raise ReplayError('invalid_json')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError, TypeError):
        raise ReplayError('invalid_json') from None


def encode_job(job):
    validate_job(job)
    value = json.dumps(job, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    _require(len(value) <= MAX_BYTES, 'replay_io_size')
    return value


def validate_job(job):
    _fields(job, 'version level initialMoves seed jobId playerId attemptId pinsSHA256 levelSHA256 startReceiptId starting actions receipts')
    _require(job['version'] == 1 and type(job['version']) is int and _integer(job['level'], 1, 50)
             and _integer(job['initialMoves'], 1, 1000) and _integer(job['seed'], 1, 4_294_967_295))
    _require(all(_id(job[key]) for key in ('jobId', 'playerId', 'attemptId'))
             and all(_hash(job[key]) for key in ('pinsSHA256', 'levelSHA256')) and _receipt(job['startReceiptId']))
    _require(type(job['starting']) is list and len(job['starting']) == 4
             and all(_integer(value, 0, 1) for value in job['starting']))
    _require(type(job['actions']) is list and len(job['actions']) <= 1000
             and type(job['receipts']) is list and len(job['receipts']) <= 1000)
    receipts = {}
    for receipt in job['receipts']:
        _fields(receipt, 'receiptId attemptId kind actionIndex tool coins quantity movesAfter')
        _require(_receipt(receipt['receiptId']) and receipt['receiptId'] != job['startReceiptId']
                 and receipt['receiptId'] not in receipts and receipt['attemptId'] == job['attemptId']
                 and _integer(receipt['actionIndex'], 0, len(job['actions']) - 1))
        _require(all(type(receipt[key]) is int for key in ('tool', 'coins', 'quantity', 'movesAfter')))
        receipts[receipt['receiptId']] = receipt
    used = set()
    for index, action in enumerate(job['actions']):
        _fields(action, 'index ax ay bx by tool movesAfter kind receiptId')
        _require(type(action['index']) is int and action['index'] == index
                 and all(_integer(action[key], -1, 14) for key in ('ax', 'ay', 'bx', 'by'))
                 and type(action['tool']) is int and type(action['movesAfter']) is int)
        kind = action['kind']
        if kind in ('Swap', 'Tap'):
            _require(action['receiptId'] == '' and action['tool'] == -1 and action['movesAfter'] == 0
                     and action['ax'] >= 0 and action['ay'] >= 0)
            if kind == 'Tap':
                _require(action['bx'] == action['by'] == -1)
            else:
                _require(action['bx'] >= 0 and action['by'] >= 0
                         and abs(action['ax'] - action['bx']) + abs(action['ay'] - action['by']) == 1)
            continue
        _require(isinstance(action['receiptId'], str) and action['receiptId'] in receipts
                 and action['receiptId'] not in used)
        receipt = receipts[action['receiptId']]
        used.add(action['receiptId'])
        _require(receipt['kind'] == kind and receipt['actionIndex'] == index)
        if kind == 'Tool':
            _require(_integer(action['tool'], 0, 3) and action['bx'] == action['by'] == -1 and action['movesAfter'] == 0
                     and (receipt['tool'], receipt['coins'], receipt['quantity'], receipt['movesAfter']) == (action['tool'], 0, 1, 0))
        elif kind == 'Continue':
            _require(all(action[key] == -1 for key in ('ax', 'ay', 'bx', 'by', 'tool')) and action['movesAfter'] == 5
                     and (receipt['tool'], receipt['coins'], receipt['quantity'], receipt['movesAfter']) == (-1, 900, 0, 5))
        else:
            raise ReplayError('unknown_replay_action')
    _require(used == set(receipts))
    return job


def validate_output(raw, job, job_bytes):
    value = _fields(strict_json(raw), 'version level actions moves turn remainingGoals status code unity jobSHA256 pinsSHA256 levelSHA256 checkpointSHA256 outcome productionEnabled financialMutation actionResults')
    _require(value['version'] == 1 and type(value['version']) is int and value['status'] == 'PASS_PINNED_MODEL_REPLAY'
             and value['code'] == '' and value['unity'] == '2022.3.62f3', 'replay_worker_rejected')
    _require(value['jobSHA256'] == sha256(job_bytes) and value['pinsSHA256'] == job['pinsSHA256']
             and value['levelSHA256'] == job['levelSHA256'] and _hash(value['checkpointSHA256']))
    _require(value['productionEnabled'] is False and value['financialMutation'] is False
             and value['level'] == job['level'] and type(value['level']) is int
             and value['actions'] == len(job['actions']) and type(value['actions']) is int)
    _require(_integer(value['moves'], 0, 1000) and _integer(value['turn'], 0, 1000)
             and _integer(value['remainingGoals'], 0, 1_000_000) and value['outcome'] in STATES
             and (value['outcome'] == 'Won') == (value['remainingGoals'] == 0))
    _require(type(value['actionResults']) is list and len(value['actionResults']) == len(job['actions']))
    moves, turn = job['initialMoves'], 0
    for index, result in enumerate(value['actionResults']):
        _fields(result, 'index moves turn kind status checkpointSHA256')
        action = job['actions'][index]
        if action['kind'] in ('Swap', 'Tap'):
            moves -= 1
            turn += 1
        elif action['kind'] == 'Continue':
            moves = 5
        _require(result['index'] == index and type(result['index']) is int and result['kind'] == action['kind']
                 and result['moves'] == moves and type(result['moves']) is int
                 and result['turn'] == turn and type(result['turn']) is int
                 and result['status'] in STATES and _hash(result['checkpointSHA256']))
    _require(value['moves'] == moves and value['turn'] == turn)
    if value['actionResults']:
        _require(value['actionResults'][-1]['checkpointSHA256'] == value['checkpointSHA256']
                 and value['actionResults'][-1]['status'] == value['outcome'])
    return value


def _file(path, maximum=MAX_BYTES):
    _require(path.is_file() and not path.is_symlink() and 2 <= path.stat().st_size <= maximum, 'replay_io_size')
    with path.open('rb') as stream:
        value = stream.read(maximum + 1)
    _require(len(value) <= maximum, 'replay_io_size')
    return value


def _relative(root, relative):
    _require(isinstance(relative, str) and relative and '\\' not in relative and ':' not in relative
             and not relative.startswith('/') and all(part not in ('', '.', '..') for part in relative.split('/')), 'invalid_bundle_path')
    path = (root / relative).resolve()
    _require(path.is_relative_to(root) and path != root, 'invalid_bundle_path')
    return path


class ApprovedWorker:
    """An operator-pinned complete bundle; callers cannot select an executable."""
    def __init__(self, bundle, approval_file, approval_sha256, jobs_directory, *, enabled=False,
                 timeout_seconds=60, memory_bytes=1_073_741_824, process_limit=2):
        _require(type(enabled) is bool and _hash(approval_sha256), 'replay_not_configured')
        _require(_integer(timeout_seconds, 1, 120) and _integer(memory_bytes, 134_217_728, 2_147_483_648)
                 and _integer(process_limit, 1, 2), 'invalid_replay_limits')
        self.root = Path(bundle).resolve(strict=True)
        self.approval_file, self.approval_sha256 = Path(approval_file).resolve(strict=True), approval_sha256
        self.jobs = Path(jobs_directory).resolve(strict=True)
        _require(self.root.is_dir() and self.jobs.is_dir() and not self.jobs.is_relative_to(self.root))
        self.enabled, self.timeout, self.memory, self.process_limit = enabled, timeout_seconds, memory_bytes, process_limit

    def _verify_bundle(self):
        raw = _file(self.approval_file)
        _require(sha256(raw) == self.approval_sha256, 'approval_hash_mismatch')
        approval = _fields(strict_json(raw), 'version kind unity executable pins files')
        _require(approval['version'] == 1 and type(approval['version']) is int and approval['kind'] == 'PinnedUnityReplayWorker'
                 and approval['unity'] == '2022.3.62f3' and approval['executable'] == 'PinnedReplayWorker.exe'
                 and approval['pins'] == 'ReplayPins/manifest.json' and type(approval['files']) is dict
                 and 3 <= len(approval['files']) <= 1024, 'invalid_worker_approval')
        # Hashing the whole bundle holds the single verification slot. Repeat it
        # only if any file was added or removed, or its size or time changed.
        signature = sorted((path.relative_to(self.root).as_posix(), path.stat().st_size, path.stat().st_mtime_ns)
                           for path in self.root.rglob('*') if path.is_file())
        cached = getattr(self, '_verified_bundle', None)
        if cached and cached[0] == signature:
            return cached[1]
        total = 0
        for relative, expected in approval['files'].items():
            path = _relative(self.root, relative)
            _require(_hash(expected) and path.is_file() and not path.is_symlink(), 'invalid_worker_approval')
            size = path.stat().st_size
            total += size
            _require(size <= 536_870_912 and total <= 1_073_741_824, 'worker_bundle_size')
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1_048_576), b''):
                    digest.update(block)
            _require(digest.hexdigest() == expected, 'worker_file_hash_mismatch')
        actual = {path.relative_to(self.root).as_posix() for path in self.root.rglob('*') if path.is_file()}
        _require(actual == set(approval['files']) and approval['executable'] in actual and approval['pins'] in actual,
                 'unapproved_worker_files')
        pins_raw = _file(_relative(self.root, approval['pins']))
        pins = strict_json(pins_raw)
        _require(type(pins) is dict and pins.get('version') == 1 and pins.get('unity') == '2022.3.62f3'
                 and type(pins.get('levels')) is list and len(pins['levels']) == 50, 'invalid_worker_pins')
        for number, level in enumerate(pins['levels'], 1):
            _require(type(level) is dict and level.get('level') == number and type(level.get('level')) is int
                     and level.get('id') == f'C01_L{number:03}' and level.get('path') == f'Levels/C01_L{number:03}.json'
                     and _hash(level.get('sha256')) and _integer(level.get('moves'), 1, 1000), 'invalid_worker_pins')
            level_path = _relative(self.root, 'ReplayPins/' + level['path'])
            _require(sha256(_file(level_path)) == level['sha256'], 'worker_level_hash_mismatch')
        result = approval, pins, sha256(pins_raw)
        self._verified_bundle = signature, result
        return result

    def run(self, job):
        _require(self.enabled, 'replay_not_configured')
        _require(os.name == 'nt', 'replay_platform_not_supported')
        data = encode_job(job)
        approval, pins, pins_hash = self._verify_bundle()
        level = pins['levels'][job['level'] - 1]
        _require(job['pinsSHA256'] == pins_hash and job['levelSHA256'] == level['sha256']
                 and job['initialMoves'] == level['moves'], 'job_pin_mismatch')
        folder = Path(tempfile.mkdtemp(prefix='replay-' + job['jobId'] + '-', dir=self.jobs)).resolve()
        _require(folder.is_relative_to(self.jobs) and not folder.is_relative_to(self.root))
        request, output = folder / 'job.json', folder / 'output.json'
        descriptor = os.open(request, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        process = _run_windows_bounded(_relative(self.root, approval['executable']),
            ['-batchmode', '-nographics', '-logFile', 'NUL', '--job', str(request), '--out', str(output)], self.root,
            self.timeout, self.memory, self.process_limit)
        raw = _file(output)
        proof = {'process': process, 'approvalSHA256': self.approval_sha256,
                 'jobSHA256': sha256(data), 'outputSHA256': sha256(raw), 'productionEnabled': False}
        if process['exitCode'] != 0:
            failure = strict_json(raw)
            # This is authenticated by the separately pinned complete binary
            # bundle, private process output and exact server job bytes. A
            # caller/HTTP fault assertion never reaches this classification.
            if (process['exitCode'] == 1 and type(failure) is dict and failure.get('version') == 1
                    and type(failure.get('version')) is int and failure.get('status') == 'FAIL'
                    and failure.get('unity') == '2022.3.62f3' and failure.get('code') == 'model_fault'
                    and failure.get('jobSHA256') == sha256(data) and failure.get('productionEnabled') is False
                    and failure.get('financialMutation') is False):
                raise TrustedModelFault(proof)
            raise ReplayError('replay_process_rejected')
        result = validate_output(raw, job, data)
        # The hashes and result go to the database, so a good run keeps no folder. A failed run
        # keeps its files for diagnosis until retention clears them a day later.
        shutil.rmtree(folder, ignore_errors=True)
        return {'result': result, **proof}


def _run_windows_bounded(executable, arguments, directory, timeout_seconds, memory_bytes, process_limit):
    """Create suspended, assign limits, then resume; no unbounded pre-job race.

    Microsoft: learn.microsoft.com/windows/win32/procthread/job-objects and
    api/winnt/ns-winnt-jobobject_extended_limit_information. No Linux fallback
    silently drops limits; production requires a separately proven host profile.
    """
    _require(os.name == 'nt', 'replay_platform_not_supported')
    from ctypes import wintypes as w
    class Basic(ctypes.Structure):
        _fields_ = [('processTime', ctypes.c_int64), ('jobTime', ctypes.c_int64), ('flags', w.DWORD),
            ('minimum', ctypes.c_size_t), ('maximum', ctypes.c_size_t), ('active', w.DWORD),
            ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ('readOps', 'writeOps', 'otherOps', 'readBytes', 'writeBytes', 'otherBytes')]
    class Extended(ctypes.Structure):
        _fields_ = [('basic', Basic), ('io', IO), ('processMemory', ctypes.c_size_t), ('jobMemory', ctypes.c_size_t),
                    ('peakProcessMemory', ctypes.c_size_t), ('peakJobMemory', ctypes.c_size_t)]
    class Startup(ctypes.Structure):
        _fields_ = [('cb', w.DWORD), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR), ('title', w.LPWSTR),
            ('x', w.DWORD), ('y', w.DWORD), ('xSize', w.DWORD), ('ySize', w.DWORD), ('xChars', w.DWORD), ('yChars', w.DWORD),
            ('fill', w.DWORD), ('flags', w.DWORD), ('show', w.WORD), ('reservedSize', w.WORD),
            ('reservedBytes', ctypes.POINTER(ctypes.c_byte)), ('stdin', w.HANDLE), ('stdout', w.HANDLE), ('stderr', w.HANDLE)]
    class Process(ctypes.Structure):
        _fields_ = [('process', w.HANDLE), ('thread', w.HANDLE), ('pid', w.DWORD), ('tid', w.DWORD)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    for name, args, result in (
        ('CreateJobObjectW', [ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
        ('CreateMutexW', [ctypes.c_void_p, w.BOOL, w.LPCWSTR], w.HANDLE),
        ('ReleaseMutex', [w.HANDLE], w.BOOL),
        ('SetInformationJobObject', [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
        ('QueryInformationJobObject', [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
        ('CreateProcessW', [w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, w.BOOL, w.DWORD, ctypes.c_void_p, w.LPCWSTR, ctypes.POINTER(Startup), ctypes.POINTER(Process)], w.BOOL),
        ('AssignProcessToJobObject', [w.HANDLE, w.HANDLE], w.BOOL), ('ResumeThread', [w.HANDLE], w.DWORD),
        ('WaitForSingleObject', [w.HANDLE, w.DWORD], w.DWORD), ('GetExitCodeProcess', [w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL),
        ('TerminateJobObject', [w.HANDLE, w.UINT], w.BOOL), ('TerminateProcess', [w.HANDLE, w.UINT], w.BOOL),
        ('CloseHandle', [w.HANDLE], w.BOOL)):
        function = getattr(kernel, name); function.argtypes, function.restype = args, result
    name = 'Global\\HeartOfTheRain.Replay.' + sha256(str(Path(executable).resolve()).lower().encode('utf-8'))
    mutex = kernel.CreateMutexW(None, False, name)
    _require(bool(mutex), 'worker_limits_unavailable')
    job, process, assigned, acquired = None, Process(), False, False
    try:
        wait = kernel.WaitForSingleObject(mutex, 0)
        _require(wait in (0, 128), 'replay_worker_busy')  #128: abandoned owner; its kill-on-close job is gone.
        acquired = True
        job = kernel.CreateJobObjectW(None, None)
        _require(bool(job), 'worker_limits_unavailable')
        limits = Extended(); limits.basic.flags = 0x8 | 0x100 | 0x200 | 0x2000
        limits.basic.active, limits.processMemory, limits.jobMemory = process_limit, memory_bytes, memory_bytes
        _require(bool(kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits))), 'worker_limits_unavailable')
        environment = '\0'.join(key + '=' + os.environ[key] for key in sorted(os.environ, key=str.upper)
            if key.upper() in ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'COMSPEC', 'PATH', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA')) + '\0\0'
        env = ctypes.create_unicode_buffer(environment)
        startup = Startup(); startup.cb = ctypes.sizeof(startup)
        command = ctypes.create_unicode_buffer(subprocess.list2cmdline([str(executable), *arguments]))
        _require(bool(kernel.CreateProcessW(str(executable), command, None, None, False,
            # Suspended, Unicode environment, no window, below normal so verification never starves requests.
            0x4 | 0x400 | 0x08000000 | 0x4000, env, str(directory), ctypes.byref(startup), ctypes.byref(process))), 'worker_start_failed')
        _require(bool(kernel.AssignProcessToJobObject(job, process.process)), 'worker_limits_unavailable'); assigned = True
        _require(kernel.ResumeThread(process.thread) != 0xFFFFFFFF, 'worker_start_failed')
        started = time.monotonic(); wait = kernel.WaitForSingleObject(process.process, timeout_seconds * 1000)
        if wait == 258:
            kernel.TerminateJobObject(job, 124); kernel.WaitForSingleObject(process.process, 5000)
            raise ReplayError('replay_process_timeout')
        _require(wait == 0, 'worker_wait_failed')
        code = w.DWORD(); _require(bool(kernel.GetExitCodeProcess(process.process, ctypes.byref(code))), 'worker_exit_unavailable')
        observed = Extended(); _require(bool(kernel.QueryInformationJobObject(job, 9, ctypes.byref(observed), ctypes.sizeof(observed), None)), 'worker_limits_unavailable')
        return {'pid': process.pid, 'exitCode': code.value, 'elapsedSeconds': round(time.monotonic() - started, 6),
                'wallLimitSeconds': timeout_seconds, 'memoryLimitBytes': memory_bytes, 'processLimit': process_limit,
                'peakProcessMemoryBytes': observed.peakProcessMemory, 'peakJobMemoryBytes': observed.peakJobMemory,
                'jobObjectEnforced': True, 'namedMutexEnforced': True, 'logsCaptured': False}
    finally:
        if process.process:
            if assigned: kernel.TerminateJobObject(job, 125)
            else: kernel.TerminateProcess(process.process, 125)
        if process.thread: kernel.CloseHandle(process.thread)
        if process.process: kernel.CloseHandle(process.process)
        if job: kernel.CloseHandle(job)  # KILL_ON_JOB_CLOSE also covers any helper child.
        if acquired: kernel.ReleaseMutex(mutex)
        kernel.CloseHandle(mutex)
