"""Run one real Unity110 managed HTTP flow against a fresh owned loopback service.

No providers/replay/gameplay/device work; raw auth/DB/logs remain private.
"""
import argparse
import ctypes
from ctypes import wintypes
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.parse import urlparse
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0, str(ROOT / 'Verification/Tools/Review93'))
from run_connected import resume_owned_primary
sys.path.insert(0, str(ROOT / 'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native = load_module('help110_native_runner', Path(__file__).with_name('run_native110.py'))


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=api.sha(path), bytes=path.stat().st_size)


def backend_inputs():
    paths = []
    for directory in (ROOT / 'Backend/hotr_backend', ROOT / 'Backend/config'):
        paths += [p for p in directory.rglob('*') if p.is_file() and p.suffix in ('.py', '.json')]
    return {p.relative_to(ROOT).as_posix(): api.sha(p) for p in sorted(paths)}


def closed(origin):
    parsed = urlparse(origin)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port:
        raise ValueError('ExactLoopbackRequired110')
    with socket.socket() as sock:
        sock.settimeout(.25)
        return sock.connect_ex(('127.0.0.1', parsed.port)) != 0


def live_owned_pid(job, pid):
    # A Windows venv launcher can create another Python interpreter. The actual
    # listener PID must be live IN THIS assigned-before-resume JobObject; PID
    # coincidence with the launcher is neither required nor sufficient.
    if type(pid) is not int or pid <= 0:
        return False
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    kernel.IsProcessInJob.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x100000 | 0x1000, False, pid)
    if not handle:
        return False
    try:
        owned = wintypes.BOOL()
        return bool(kernel.IsProcessInJob(handle, job.handle, ctypes.byref(owned)) and owned.value
            and kernel.WaitForSingleObject(handle, 0) == 0x102)
    finally:
        kernel.CloseHandle(handle)


def audit(private):
    path = private / 'ExpectedBindings.json'
    if not path.is_file():
        return dict(bindingsObserved=False)
    value = json.loads(path.read_text('utf-8'))
    recipient, donors, request = value['recipient'], value['donors'], value['requestId']
    if len(donors) != 5 or len(set([recipient] + donors)) != 6 or not all(re.fullmatch('[a-f0-9]{32}', p) for p in [recipient, request] + donors):
        raise ValueError('SixExactManagedBindingsRequired110')
    with sqlite3.connect('file:' + (private / 'authority.sqlite3').as_posix() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        players = db.execute('SELECT COUNT(*) FROM players').fetchone()[0]
        wallets = []
        for player in [recipient] + donors:
            row = db.execute('SELECT balances,revision FROM wallets WHERE player_id=?', (player,)).fetchone()
            balances = json.loads(row['balances'])
            ledger = db.execute('SELECT origin,delta_json FROM wallet_ledger WHERE player_id=? ORDER BY sequence', (player,)).fetchall()
            grants = [json.loads(r['delta_json'])[10] for r in ledger if r['origin'].startswith('team_life/')]
            fixtures = [json.loads(r['delta_json'])[10] for r in ledger if r['origin'].startswith('fixture110/capacity/')]
            wallets.append(dict(role='recipient' if player == recipient else 'donor', coins=balances[0], lives=balances[10],
                revision=row['revision'], genesisReceipts=sum(r['origin'] == 'genesis/v1' for r in ledger),
                teamLifeCredits=grants, capacityFixtureDebits=fixtures, ledgerReceipts=len(ledger)))
        life = dict(db.execute('SELECT required,received,claimed,close_reason FROM team_life_requests WHERE id=?', (request,)).fetchone())
        life['remaining'] = life['received'] - life['claimed']
        donations = db.execute('SELECT COUNT(*),COUNT(DISTINCT player_id),COUNT(DISTINCT event_id) FROM team_life_donations WHERE request_id=?', (request,)).fetchone()
        request_count = db.execute('SELECT COUNT(*) FROM team_life_requests').fetchone()[0]
        attempts = db.execute('SELECT COUNT(*) FROM gameplay_attempts').fetchone()[0]
        membership = db.execute('SELECT COUNT(*) FROM social_team_members WHERE player_id=?', (recipient,)).fetchone()[0]
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
    requests = json.loads((private / 'RequestCounts.json').read_text('utf-8'))
    result = dict(bindingsObserved=True, players=players, wallets=wallets, requestCount=request_count,
        request=life, donations=donations[0], distinctDonors=donations[1], distinctDonationEvents=donations[2],
        recipientMembershipRows=membership, gameplayAttempts=attempts, integrity=integrity,
        requestCountHttp=len(requests), suppressedCommittedReplies=sum(bool(r['committedResponseSuppressed']) for r in requests),
        capacityFixtureReceipts=len(json.loads((private / 'CapacityReceipts.json').read_text('utf-8'))),
        note='Independent read-only SQLite audit; negative capacity fixtures are ledger debits, not gameplay loss/attempt claims.')
    passed = (players == 6 and request_count == 1 and life == dict(required=5, received=5, claimed=5, close_reason='Full', remaining=0)
        and tuple(donations) == (5, 5, 5) and membership == 0 and attempts == 0 and integrity == 'ok'
        and all(w['coins'] == 1250 and w['lives'] == 5 and w['genesisReceipts'] == 1 for w in wallets)
        and wallets[0]['teamLifeCredits'] == [2, 3] and wallets[0]['capacityFixtureDebits'] == [-2, -3]
        and all(w['teamLifeCredits'] == [] and w['capacityFixtureDebits'] == [] and w['ledgerReceipts'] == 1 for w in wallets[1:])
        and result['suppressedCommittedReplies'] == 1 and result['capacityFixtureReceipts'] == 2)
    result['status'] = 'PASS_HELP110_SQLITE_AUDIT' if passed else 'FAIL_HELP110_SQLITE_AUDIT'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--backend-report', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt' or not re.fullmatch('[A-Za-z0-9_]{1,35}', args.tag) or unity_pids():
        parser.error('Explicit bounded Windows flow with idle Editor required')
    proof_path = args.backend_report.resolve()
    proof = json.loads(proof_path.read_text('utf-8-sig'))
    if (not proof_path.is_relative_to((ROOT / 'Verification/Evidence/Review110/Backend').resolve())
            or proof.get('status') != 'PASS' or proof.get('testsRun', 0) < 200
            or any(proof.get(k) for k in ('errors', 'failures', 'skips')) or proof.get('sourcesUnchanged') is not True):
        parser.error('Actual focused zero-skip110 backend proof required')
    inputs = json.loads((proof_path.parent / 'InputsAfter.json').read_text('utf-8-sig'))
    before = backend_inputs()
    for row in inputs:
        if row['path'] in before and before[row['path']] != row['sha256']:
            parser.error('Backend runtime/config drifted after focused proof')
    identifier = uuid.uuid4().hex
    private = ROOT / '.verification-cache/Review110/HelpHTTP' / identifier
    output = ROOT / 'Verification/Evidence/Review110/Connected' / args.tag
    private.mkdir(parents=True, exist_ok=False)
    output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).with_name('serve_help110_fixture.py')
    record = dict(status='RUNNING_HELP110_HTTP', startedUtc=api.utc(), runId=identifier,
        backendProof=bind(proof_path), runner=bind(Path(__file__)), fixture=bind(fixture),
        scope='Actual Unity-to-owned-loopback HTTP and independent SQLite audit. Six genuine managed guests, fixed-clock private capacity fixtures, one after-real-commit503 and protected client reconstruction; no external services, replay/gameplay, Android/device or production acceptance.')
    api.write(output / 'BackendInputs_before.json', before)
    process = job = None
    metadata = None
    old_argv = sys.argv[:]
    previous = {k: os.environ.get(k) for k in ('HOTR_REVIEW110_HTTP_PRIVATE', 'HOTR_REVIEW110_HTTP_OUT')}
    started = time.monotonic()
    try:
        job = api.OwnedJob()
        with (private / 'Server.log').open('xb') as stream:
            process = subprocess.Popen([str(ROOT / 'Backend/.venv/Scripts/python.exe'), '-B', str(fixture),
                '--directory', str(private), '--run-id', identifier], cwd=ROOT, stdout=stream,
                stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW | 0x4)
        job.assign(process.pid)
        resume_owned_primary(process)
        record['ownedServiceAssignedBeforeResume'] = True
        for _ in range(400):
            path = private / 'connection.json'
            if path.is_file():
                metadata = json.loads(path.read_text('utf-8'))
                if metadata['runId'] != identifier or not live_owned_pid(job, metadata['pid']) or closed(metadata['origin']):
                    raise ValueError('ExactCurrentLoopbackBindingFailed110')
                record.update(launcherPid=process.pid, listenerPid=metadata['pid'],
                    listenerLiveMembershipInExactOwnedJobVerified=True)
                break
            if process.poll() is not None:
                raise ValueError('OwnedFixtureStartupFailed110')
            time.sleep(.05)
        if not metadata:
            raise TimeoutError('OwnedFixtureStartupTimedOut110')
        os.environ['HOTR_REVIEW110_HTTP_PRIVATE'] = str(private)
        os.environ['HOTR_REVIEW110_HTTP_OUT'] = str(ROOT / 'Verification/Evidence/Review110/Native' / args.tag)
        sys.argv = [str(Path(__file__).with_name('run_native110.py')), '--execute', '--tag', args.tag,
            '--entry', 'HeartOfTheRain.Verification.TeamsChatHelp110HttpVerification.Run',
            '--report', 'Native/TeamsChatHelp110_HTTP.json', '--expected', 'PASS_NATIVE_TEAMS_CHAT_HELP110_HTTP',
            '--output-env', 'HOTR_REVIEW110_HTTP_OUT', '--timeout', '900']
        record['nativeExitCode'] = native.main()
        report_path = ROOT / 'Verification/Evidence/Review110/Native' / args.tag / 'Native/TeamsChatHelp110_HTTP.json'
        record['nativeReport'] = bind(report_path) if report_path.is_file() else None
        # Stop the exact owned service before the independent DB read; this is
        # crash-style JobObject shutdown, not an unobserved graceful-stop claim.
        record['serviceClosure'] = native.shared.owned_shutdown(job)
        job = None
        process.wait(timeout=30)
        for _ in range(120):
            if closed(metadata['origin']):
                break
            time.sleep(.05)
        record['ownedLoopbackPortClosed'] = closed(metadata['origin'])
        result = audit(private)
        api.write(output / 'SQLiteAudit110.json', result)
        record['databaseAudit'] = bind(output / 'SQLiteAudit110.json')
        record['status'] = 'PASS_CONNECTED_HELP110_HTTP' if (record['nativeExitCode'] == 0
            and result.get('status') == 'PASS_HELP110_SQLITE_AUDIT' and record['ownedLoopbackPortClosed']
            and record['serviceClosure'].get('allObservedHandlesSignaled')) else 'FAIL_CONNECTED_HELP110_HTTP'
    except Exception as error:
        record.update(status='FAIL_CONNECTED_HELP110_HTTP', errorType=type(error).__name__,
            code=str(error) if re.fullmatch('[A-Za-z0-9]{1,120}', str(error)) else 'PrivateDetailsRetained110')
    finally:
        if job:
            record['serviceClosure'] = native.shared.owned_shutdown(job)
        if process and process.poll() is None:
            process.wait(timeout=30)
        if metadata:
            for _ in range(120):
                if closed(metadata['origin']):
                    break
                time.sleep(.05)
            record['ownedLoopbackPortClosed'] = closed(metadata['origin'])
        sys.argv = old_argv
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        after = backend_inputs()
        api.write(output / 'BackendInputs_after.json', after)
        record.update(backendRuntimeInputsUnchanged=before == after, finishedUtc=api.utc(),
            elapsedSeconds=round(time.monotonic() - started, 3),
            rawPrivateFiles=[bind(p) for p in private.rglob('*') if p.is_file()],
            protectedFixtureFiles=[bind(p) for p in (ROOT / '.verification-cache/Launch82/TeamHelp110' / identifier).rglob('*') if p.is_file()])
        if before != after or process and process.poll() is None or metadata and not record.get('ownedLoopbackPortClosed'):
            record['status'] = 'FAIL_CONNECTED_HELP110_PRESERVATION'
        api.write(output / 'Flow110.json', record)
    print(json.dumps(dict(status=record['status'], report=(output / 'Flow110.json').relative_to(ROOT).as_posix())), flush=True)
    return 0 if record['status'] == 'PASS_CONNECTED_HELP110_HTTP' else 1


if __name__ == '__main__':
    raise SystemExit(main())
