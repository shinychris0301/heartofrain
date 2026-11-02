"""Run real Unity managed HTTP against a fresh local service with synthetic VK.

Requires a current full zero-skip backend proof. All OAuth material, database
and raw logs stay private. Exported evidence contains hashes, counts and scope.
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
        raise ValueError('ExactLoopbackRequired102')
    with socket.socket() as sock:
        sock.settimeout(.25)
        return sock.connect_ex(('127.0.0.1', value.port)) != 0


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


def audit(private):
    bindings_path = private / 'ExpectedBindings.json'
    if not bindings_path.is_file():
        return dict(bindingsObserved=False)
    bindings = json.loads(bindings_path.read_text('utf-8'))
    first, second = bindings.get('playerA'), bindings.get('playerB')
    if (not isinstance(first, str) or not re.fullmatch('[a-f0-9]{32}', first)
            or not isinstance(second, str) or not re.fullmatch('[a-f0-9]{32}', second) or first == second):
        raise ValueError('ExactPrivateManagedPlayersRequired102')
    with sqlite3.connect('file:' + (private / 'authority.sqlite3').as_posix() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        players = db.execute('SELECT COUNT(*) FROM players').fetchone()[0]
        wallets = {}
        for label, player in (('target', first), ('source', second)):
            value = json.loads(db.execute('SELECT balances FROM wallets WHERE player_id=?', (player,)).fetchone()[0])
            origins = [row[0] for row in db.execute('SELECT origin FROM wallet_ledger WHERE player_id=? ORDER BY sequence', (player,))]
            wallets[label] = dict(coins=value[0], lives=value[10], balanceDimensions=len(value),
                genesisReceipts=origins.count('genesis/v1'),
                operatorSeedReceipts=origins.count('verification102/operator-seed'), ledgerReceipts=len(origins),
                attempts=db.execute('SELECT COUNT(*) FROM gameplay_attempts WHERE player_id=?', (player,)).fetchone()[0])
        links = db.execute("SELECT player_id FROM account_provider_links WHERE provider='vk'").fetchall()
        phases = dict(db.execute('SELECT phase,COUNT(*) FROM account_provider_signins GROUP BY phase').fetchall())
        operations = db.execute("SELECT player_id,family_id FROM identity_operations WHERE purpose='vk'").fetchall()
        recovery = db.execute('SELECT digest FROM identity_recovery WHERE player_id=?', (first,)).fetchone()[0]
        vk_family_refresh_rows = [db.execute('SELECT COUNT(*) FROM identity_refresh WHERE family_id=?', (row['family_id'],)).fetchone()[0] for row in operations]
        proofs_cleared = db.execute("SELECT COUNT(*) FROM account_provider_signins WHERE phase IN ('Completed','Cancelled') AND (state_secret!='' OR verifier!='')").fetchone()[0] == 0
        expired_target_cleared = db.execute("SELECT COUNT(*) FROM account_provider_signins WHERE phase='Expired' AND (target_player IS NOT NULL OR subject_digest!='' OR state_secret!='' OR verifier!='')").fetchone()[0] == 0
        grant_count = db.execute('SELECT COUNT(*) FROM rewards').fetchone()[0]
        completion_target_matches = all(row['player_id'] == first for row in operations)
        provider_tokens_absent = all('fixture-vk102-' not in statement for statement in db.iterdump())
    requests = json.loads((private / 'RequestCounts.json').read_text('utf-8'))
    suppressed = sum(row.get('committedResponseSuppressed', False) for row in requests)
    successes = sum(row['method'] == 'POST' and row['path'] == '/v1/identity/vk/complete' and row['status'] == 200 for row in requests)
    rotations = sum(row['method'] == 'POST' and row['path'] == '/v1/identity/session' and row['status'] == 200 for row in requests)
    return dict(bindingsObserved=True, players=players, wallets=wallets,
        providerLinks=len(links), providerLinkTargetsEarlierPlayer=len(links) == 1 and links[0]['player_id'] == first,
        signinPhases=phases, signedVkOperations=len(operations), distinctVkFamilies=len(set(row['family_id'] for row in operations)),
        vkFamilyRefreshRows=vk_family_refresh_rows, completionTargetMatches=completion_target_matches,
        recoveryDigestUnchanged=recovery == bindings.get('recoveryDigest'),
        completedAndCancelledProofsCleared=proofs_cleared, rewardGrants=grant_count,
        expiredTargetAndProofsCleared=expired_target_cleared,
        providerTokensAbsent=provider_tokens_absent,
        actualCommittedCompletionRepliesSuppressed=suppressed, successfulCompletionReplies=successes,
        successfulSourceSessionRefreshes=rotations,
        providerCalls=json.loads((private / 'ProviderCounts.json').read_text('utf-8')))


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
    if (not backend.is_relative_to((ROOT / 'Verification/Evidence/Review102/Backend').resolve())
            or proof.get('status') != 'PASS_BACKEND_SERVICE_TESTS'
            or any(proof.get(key) for key in ('failures', 'errors', 'skipped', 'sourceInputsChangedDuringRun'))
            or proof.get('actualPinnedWorkerIntegration') is not True or proof.get('executedTests', 0) < 500):
        parser.error('Current full zero-skip backend proof required')
    for relative, digest in proof['sourceSHA256'].items():
        if sha(ROOT / relative) != digest:
            parser.error('Backend inputs changed after full proof')
    identifier = uuid.uuid4().hex
    private = ROOT / '.verification-cache/Review102/VkHTTP' / identifier
    output = ROOT / 'Verification/Evidence/Review102/Connected' / args.tag
    private.mkdir(parents=True, exist_ok=False)
    output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).with_name('serve_vk102_fixture.py')
    record = dict(schemaVersion=1, status='RUNNING_CONNECTED_VK_SIGNIN102', utc=utc(), runId=identifier,
        backendProof=bind(backend), runner=bind(Path(__file__)), fixture=bind(fixture),
        scope='Actual Unity managed guest/device signatures and SQLite VK registration/signin through local HTTP. Provider HTTP is explicitly httpx.MockTransport; callbacks stay loopback and browser is never opened. Private137coin seed and one after-commit503 are controlled fixtures. No Android, live VK, deployment, local save import or production acceptance.')
    process = job = None
    metadata = None
    try:
        job = OwnedJob()
        with (private / 'Server.log').open('xb') as stream:
            process = subprocess.Popen([str(ROOT / 'Backend/.venv/Scripts/python.exe'), '-B', str(fixture),
                '--directory', str(private), '--run-id', identifier], cwd=ROOT,
                stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW | 0x4)
        job.assign(process.pid)
        resume_owned_primary(process)
        record['ownedServiceJobAssignedBeforeResume'] = True
        for _ in range(400):
            connection = private / 'connection.json'
            if connection.is_file():
                metadata = json.loads(connection.read_text('utf-8'))
                if metadata['runId'] != identifier or closed(metadata['origin']):
                    raise ValueError('CurrentFixtureListenerBindingFailed102')
                break
            if process.poll() is not None:
                raise ValueError('ControlledFixtureStartupFailed102')
            time.sleep(.1)
        else:
            raise TimeoutError('ControlledFixtureStartupDeadline102')
        record['service'] = {key: metadata[key] for key in ('runId', 'origin', 'scope')}
        environment = dict(os.environ)
        environment['HOTR_VK102_HTTP_CONFIG'] = str(private / 'connection.json')
        native_tag = args.tag + '_Native'
        with (private / 'NativeRunner.log').open('xb') as stream:
            native = subprocess.run([str(ROOT / 'Backend/.venv/Scripts/python.exe'), '-B',
                str(Path(__file__).with_name('run_native102.py')), '--execute', '--engine', '2022', '--tag', native_tag,
                '--entry', 'HeartOfTheRain.Verification.VkSignin102HttpVerification.Run',
                '--report', 'Native/VkSignin102Http.json', '--expected', 'PASS_NATIVE_VK_SIGNIN102_HTTP', '--timeout', '420'],
                cwd=ROOT, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                timeout=540, creationflags=subprocess.CREATE_NO_WINDOW)
        invocation = ROOT / 'Verification/Evidence/Review102/Native' / native_tag / 'Invocation.json'
        value = json.loads(invocation.read_text('utf-8'))
        record['nativeInvocation'] = bind(invocation)
        record['nativeExitCode'] = native.returncode
        measured = audit(private)
        record['databaseAudit'] = measured
        target, source = measured.get('wallets', {}).get('target', {}), measured.get('wallets', {}).get('source', {})
        audit_ok = (measured.get('bindingsObserved') and measured.get('players') == 2
            and measured.get('providerLinks') == 1 and measured.get('providerLinkTargetsEarlierPlayer')
            and measured.get('signinPhases') == {'Completed': 2, 'Cancelled': 1, 'Expired': 1}
            and measured.get('signedVkOperations') == 2 and measured.get('distinctVkFamilies') == 2
            and measured.get('vkFamilyRefreshRows') == [1, 1] and measured.get('completionTargetMatches')
            and measured.get('recoveryDigestUnchanged') and measured.get('completedAndCancelledProofsCleared')
            and measured.get('expiredTargetAndProofsCleared')
            and measured.get('providerTokensAbsent')
            and measured.get('rewardGrants') == 0 and measured.get('actualCommittedCompletionRepliesSuppressed') == 1
            and measured.get('successfulCompletionReplies', 0) >= 2 and measured.get('successfulSourceSessionRefreshes', 0) >= 1
            and target.get('coins') == 1387 and source.get('coins') == 1250
            and target.get('lives') == source.get('lives') == 5
            and target.get('genesisReceipts') == source.get('genesisReceipts') == 1
            and target.get('ledgerReceipts') == 2 and source.get('ledgerReceipts') == 1
            and target.get('attempts') == source.get('attempts') == 0)
        audit_ok = (audit_ok and measured.get('providerCalls', {}).get('tokenExchanges') == 3
                    and measured.get('providerCalls', {}).get('userInfoReads') == 3)
        record['status'] = ('PASS_CONNECTED_VK_SIGNIN102_HTTP' if native.returncode == 0
            and value['status'] == 'PASS_NATIVE102_INVOCATION' and audit_ok else 'FAIL_CONNECTED_VK_SIGNIN102_HTTP')
    except Exception as error:
        record.update(status='FAIL_CONNECTED_VK_SIGNIN102_HTTP', errorType=type(error).__name__)
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
                record['status'] = 'FAIL_CONNECTED_VK_SIGNIN102_LISTENER_CLEANUP'
        record['finishedUtc'] = utc()
        record['privateArtifacts'] = [bind(path) for path in (private / 'Server.log', private / 'NativeRunner.log', private / 'connection.json') if path.is_file()]
        write(output / 'Report.json', record)
    print(json.dumps(dict(status=record['status'], report=(output / 'Report.json').relative_to(ROOT).as_posix())), flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
