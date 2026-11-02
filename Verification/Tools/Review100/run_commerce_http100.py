"""Run the current Unity HTTP flow against a fresh controlled loopback service.

Requires a full passing unchanged backend proof. Credentials, database, provider
controls and raw logs remain private. Only counts/hashes/scopes are exported.
"""
import argparse
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
        raise ValueError('ExactLoopbackRequired100')
    with socket.socket() as sock:
        sock.settimeout(.25)
        return sock.connect_ex(('127.0.0.1', value.port)) != 0


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


def audit(database, metadata):
    result = []
    with sqlite3.connect('file:' + database.as_posix() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        for player in metadata['players']:
            orders = db.execute('SELECT internal_product,state,COUNT(*) AS count FROM commerce_orders WHERE player_id=? GROUP BY internal_product,state', (player['playerId'],)).fetchall()
            credits = db.execute('SELECT COUNT(*) FROM commerce_credits WHERE player_id=?', (player['playerId'],)).fetchone()[0]
            entitlements = db.execute('SELECT offer_id,state FROM commerce_entitlements WHERE player_id=? ORDER BY offer_id', (player['playerId'],)).fetchall()
            result.append(dict(scenario=player['name'], orders=[dict(r) for r in orders], creditCount=credits,
                               entitlements=[dict(r) for r in entitlements]))
    return result


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
    private = ROOT / '.verification-cache/Review100/CommerceHTTP' / ident
    private.mkdir(parents=True, exist_ok=False)
    out = ROOT / 'Verification/Evidence/Review100/Connected' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).with_name('serve_commerce100_fixture.py')
    record = dict(schemaVersion=1, status='RUNNING_CONNECTED_COMMERCE100', utc=utc(), runId=ident,
                  backendProof=bind(backend), runner=bind(Path(__file__)), fixture=bind(fixture),
                  scope='Actual current Unity HTTP flow and SQLite backend; private operator-provisioned guests/backlog, controlled SDK/publisher and response fault. No real payment/provider, device or production acceptance.')
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
                    raise ValueError('CurrentFixtureListenerBindingFailed100')
                break
            if process.poll() is not None:
                raise ValueError('ControlledFixtureStartupFailed100')
            time.sleep(.1)
        else:
            raise TimeoutError('ControlledFixtureStartupDeadline100')
        record['service'] = {key: metadata[key] for key in ('runId', 'origin', 'scope', 'trustedPendingSeedCount')}
        env = dict(os.environ)
        env['HOTR_COMMERCE100_HTTP_CONFIG'] = str(connection)
        native_tag = args.tag + '_Native'
        with (private / 'NativeRunner.log').open('xb') as stream:
            native = subprocess.run([str(ROOT / '.venv/Scripts/python.exe'), '-B', str(Path(__file__).with_name('run_native100.py')),
                                     '--execute', '--engine', '2022', '--tag', native_tag,
                                     '--entry', 'HeartOfTheRain.Verification.Commerce100HttpVerification.Run',
                                     '--report', 'Native/Commerce100Http.json', '--expected', 'PASS_NATIVE_COMMERCE_HTTP100', '--timeout', '600'],
                                    cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                    timeout=720, creationflags=subprocess.CREATE_NO_WINDOW)
        invocation = ROOT / 'Verification/Evidence/Review100/Native' / native_tag / 'Invocation.json'
        value = json.loads(invocation.read_text('utf-8'))
        record['nativeInvocation'] = bind(invocation)
        record['nativeExitCode'] = native.returncode
        record['databaseAudit'] = audit(private / 'authority.sqlite3', metadata)
        record['status'] = 'PASS_CONNECTED_COMMERCE100_CONTROLLED_PROVIDER' if native.returncode == 0 and value['status'] == 'PASS_NATIVE100_INVOCATION' else 'FAIL_CONNECTED_COMMERCE100'
    except Exception as error:
        record.update(status='FAIL_CONNECTED_COMMERCE100', errorType=type(error).__name__)
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
                record['status'] = 'FAIL_CONNECTED_COMMERCE100_LISTENER_CLEANUP'
        record['finishedUtc'] = utc()
        record['privateArtifacts'] = [bind(p) for p in (private / 'Server.log', private / 'NativeRunner.log', private / 'connection.json') if p.is_file()]
        write(out / 'Report.json', record)
    print(json.dumps(dict(status=record['status'], report=(out / 'Report.json').relative_to(ROOT).as_posix())), flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
