"""Run the current Unity HTTP flow against a fresh controlled loopback service.

Requires a full passing unchanged backend proof. Credentials, database, provider
controls and raw logs remain private. Only counts/hashes/scopes are exported.
"""
import argparse
import hashlib
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
from run_ads85_native import OwnedJob, sha, utc, write
sys.path.insert(0, str(ROOT / 'Verification/Tools/Review93'))
from run_connected import resume_owned_primary
sys.path.insert(0, str(ROOT / 'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids


def closed(origin):
    value = urlparse(origin)
    if value.scheme != 'http' or value.hostname != '127.0.0.1' or not value.port:
        raise ValueError('ExactLoopbackRequired101')
    with socket.socket() as sock:
        sock.settimeout(.25)
        return sock.connect_ex(('127.0.0.1', value.port)) != 0


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


def audit(database, metadata, private):
    seed = private / 'SeedReceipt.json'
    if not seed.is_file():
        return dict(seedObserved=False)
    seed_hash = json.loads(seed.read_text('utf-8'))['playerIdSHA256']
    with sqlite3.connect('file:' + database.as_posix() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        players = [r[0] for r in db.execute('SELECT id FROM players').fetchall()]
        matches = [p for p in players if hashlib.sha256(p.encode()).hexdigest() == seed_hash]
        if len(matches) != 1:
            raise ValueError('ExactlyOneSeededPlayerRequired101')
        player = matches[0]
        row = db.execute('SELECT balances,revision,next_life_at FROM wallets WHERE player_id=?', (player,)).fetchone()
        refs = db.execute("SELECT delta_json FROM wallet_ledger WHERE player_id=? AND origin LIKE 'life.refill/%'", (player,)).fetchall()
        sessions = db.execute('SELECT COUNT(*) FROM identity_sessions WHERE player_id=?', (player,)).fetchone()[0]
        rotations = db.execute('SELECT COUNT(*) FROM identity_refresh WHERE family_id IN (SELECT id FROM identity_sessions WHERE player_id=?)', (player,)).fetchone()[0]
        attempts = db.execute('SELECT COUNT(*) FROM gameplay_attempts WHERE player_id=?', (player,)).fetchone()[0]
        timer = dict(timerSeedObserved=False)
        timer_seed = private / 'TimerSeedReceipt.json'
        if timer_seed.is_file():
            timer_hash = json.loads(timer_seed.read_text('utf-8'))['playerIdSHA256']
            timer_matches = [p for p in players if hashlib.sha256(p.encode()).hexdigest() == timer_hash]
            if len(timer_matches) != 1:
                raise ValueError('ExactlyOneTimerPlayerRequired101')
            timer_player = timer_matches[0]
            timer_wallet = db.execute('SELECT balances FROM wallets WHERE player_id=?', (timer_player,)).fetchone()
            timer_values = json.loads(timer_wallet[0])
            regen = db.execute("SELECT delta_json FROM wallet_ledger WHERE player_id=? AND origin LIKE 'life/regen/%'", (timer_player,)).fetchall()
            timer_attempts = db.execute('SELECT COUNT(*) FROM gameplay_attempts WHERE player_id=?', (timer_player,)).fetchone()[0]
            timer = dict(timerSeedObserved=True, finalCoins=timer_values[0], finalLives=timer_values[10],
                         regenReceipts=len(regen), regenDeltas=[json.loads(x[0]) for x in regen], attempts=timer_attempts)
    requests = json.loads((private / 'RequestCounts.json').read_text('utf-8'))
    refreshes = sum(q['method']=='POST' and q['path']=='/v1/identity/session' and q['status']==200 for q in requests)
    balances = json.loads(row['balances'])
    return dict(seedObserved=True, identitySessions=sessions, identityRefreshRows=rotations, successfulHttpRefreshes=refreshes,
                actualRefillReceipts=len(refs), refillDeltas=[json.loads(x['delta_json']) for x in refs],
                finalCoins=balances[0], finalLives=balances[10], attempts=attempts, finalRevision=row['revision'], timer=timer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--backend-report', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt' or not re.fullmatch('[A-Za-z0-9_]{1,30}', args.tag) or unity_pids():
        parser.error('Explicit bounded Windows run and idle Unity required')
    backend = args.backend_report.resolve()
    proof = json.loads(backend.read_text('utf-8'))
    if (proof.get('status') != 'PASS_BACKEND_SERVICE_TESTS' or any(proof.get(k) for k in ('failures', 'errors', 'skipped', 'sourceInputsChangedDuringRun'))
            or not proof.get('actualPinnedWorkerIntegration') or proof.get('executedTests', 0) < 500):
        parser.error('Current full zero-skip backend proof required')
    for relative, digest in proof['sourceSHA256'].items():
        if sha(ROOT / relative) != digest:
            parser.error('Backend inputs changed after full proof')
    ident = uuid.uuid4().hex
    private = ROOT / '.verification-cache/Review101/RefillHTTP' / ident
    private.mkdir(parents=True, exist_ok=False)
    out = ROOT / 'Verification/Evidence/Review101/Connected' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).with_name('serve_refill101_fixture.py')
    record = dict(schemaVersion=1, status='RUNNING_CONNECTED_REFILL101', utc=utc(), runId=ident,
                  backendProof=bind(backend), runner=bind(Path(__file__)), fixture=bind(fixture),
                  scope='Actual managed-guest HTTP bootstrap/rotation and SQLite wallet refill through the Unity component/UI. Trusted private operator genesis adjustment and reflected local lifetime expiry are controlled. No SDK/provider, ordinary profile, device or production acceptance.')
    process = None
    job = None
    metadata = None
    try:
        job = OwnedJob()
        with (private / 'Server.log').open('xb') as stream:
            process = subprocess.Popen([str(ROOT / 'Backend/.venv/Scripts/python.exe'), '-B', str(fixture),
                                        '--directory', str(private), '--run-id', ident],
                                       cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW | 0x4)
        job.assign(process.pid)
        resume_owned_primary(process)
        record['ownedServiceJobAssignedBeforeResume'] = True
        connection = private / 'connection.json'
        for _ in range(400):
            if connection.is_file():
                metadata = json.loads(connection.read_text('utf-8'))
                if metadata['runId'] != ident or closed(metadata['origin']):
                    raise ValueError('CurrentFixtureListenerBindingFailed101')
                break
            if process.poll() is not None:
                raise ValueError('ControlledFixtureStartupFailed101')
            time.sleep(.1)
        else:
            raise TimeoutError('ControlledFixtureStartupDeadline101')
        record['service'] = {key: metadata[key] for key in ('runId', 'origin', 'scope')}
        env = dict(os.environ)
        env['HOTR_REFILL101_HTTP_CONFIG'] = str(connection)
        native_tag = args.tag + '_Native'
        with (private / 'NativeRunner.log').open('xb') as stream:
            native = subprocess.run([str(ROOT / '.venv/Scripts/python.exe'), '-B', str(Path(__file__).with_name('run_native101.py')),
                                     '--execute', '--engine', '2022', '--tag', native_tag,
                                     '--entry', 'HeartOfTheRain.Verification.Refill101HttpVerification.Run',
                                     '--report', 'Native/Refill101Http.json', '--expected', 'PASS_NATIVE_REFILL101_HTTP', '--timeout', '360'],
                                    cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                    timeout=480, creationflags=subprocess.CREATE_NO_WINDOW)
        invocation = ROOT / 'Verification/Evidence/Review101/Native' / native_tag / 'Invocation.json'
        value = json.loads(invocation.read_text('utf-8'))
        record['nativeInvocation'] = bind(invocation)
        record['nativeExitCode'] = native.returncode
        record['databaseAudit'] = audit(private / 'authority.sqlite3', metadata, private)
        actual = record['databaseAudit']
        timer = actual.get('timer', {})
        timer_ok = timer.get('timerSeedObserved') and timer.get('finalCoins') == 1250 and timer.get('finalLives') == 4 and timer.get('regenReceipts') == 1 and timer.get('attempts') == 0
        audit_ok = (actual.get('seedObserved') and actual.get('successfulHttpRefreshes', 0) >= 1 and actual.get('actualRefillReceipts') == 1 and actual.get('finalCoins') == 0 and actual.get('finalLives') == 5 and actual.get('attempts') == 0 and timer_ok)
        record['status'] = 'PASS_CONNECTED_REFILL101_HTTP' if native.returncode == 0 and value['status'] == 'PASS_NATIVE101_INVOCATION' and audit_ok else 'FAIL_CONNECTED_REFILL101'
    except Exception as error:
        record.update(status='FAIL_CONNECTED_REFILL101', errorType=type(error).__name__)
        if re.fullmatch('[A-Za-z0-9_]{1,100}', str(error)):
            record['errorCategory'] = str(error)
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            process.wait(timeout=20)
        if metadata:
            for _ in range(50):
                if closed(metadata['origin']):
                    break
                time.sleep(.1)
            record['ownedListenerClosed'] = closed(metadata['origin'])
            if not record['ownedListenerClosed']:
                record['status'] = 'FAIL_CONNECTED_REFILL101_LISTENER_CLEANUP'
        record['finishedUtc'] = utc()
        record['privateArtifacts'] = [bind(p) for p in (private / 'Server.log', private / 'NativeRunner.log', private / 'connection.json') if p.is_file()]
        write(out / 'Report.json', record)
    print(json.dumps(dict(status=record['status'], report=(out / 'Report.json').relative_to(ROOT).as_posix())), flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
