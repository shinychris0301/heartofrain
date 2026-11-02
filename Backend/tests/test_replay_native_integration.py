"""Opt-in real Windows Unity worker through authenticated broker/SQLite.

Root alone runs this after approving the complete standalone/native corpus.
The native fixture seed is installed as TRUSTED SERVER test data before any
broker history exists; no public request can select it. No Python board rules.
"""
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.replay_contract import ApprovedWorker

CONFIG = Path(__file__).resolve().parents[1] / 'config'


@unittest.skipUnless(os.getenv('HOTR_REPLAY_INTEGRATION') == '1', 'Root-operated explicit real Unity worker proof only')
class NativeReplayBrokerIntegration(unittest.TestCase):
    def test_authenticated_native_full_history_continue_win_recovery(self):
        bundle, approval, approval_hash, native = (os.environ[name] for name in (
            'HOTR_REPLAY_BUNDLE', 'HOTR_REPLAY_APPROVAL_FILE', 'HOTR_REPLAY_APPROVAL_SHA256', 'HOTR_REPLAY_NATIVE_FIXTURE_ROOT'))
        native = Path(native)
        report = json.loads((native / 'ReplayNative.json').read_text('utf-8-sig'))
        self.assertEqual(report['status'], 'PASS_PINNED_NATIVE_REPLAY_CORPUS')
        case = next(row for row in report['fixtures'] if row['continues'] > 0 and row['outcome'] == 'Won')
        fixture = json.loads((native / case['job']).read_text('utf-8-sig'))
        with tempfile.TemporaryDirectory(prefix='hotr-actual-replay-broker-') as folder:
            root = Path(folder); jobs = root / 'jobs'; jobs.mkdir()
            worker = ApprovedWorker(bundle, approval, approval_hash, jobs, enabled=True)
            app = create_app(root / 'authority.sqlite3', CONFIG, replay_enabled=True, replay_worker=worker)
            identity = app.state.authority.provision(lifetime=3600)
            # Native corpus currently reaches a natural loss/continue/win onL8.
            # Trusted fixture progression unlocks that exact approved level;
            # no request is allowed to supply progression or a seed.
            with app.state.authority.database.transaction() as database:
                database.execute('UPDATE players SET completed=? WHERE id=?', (fixture['level'] - 1, identity['playerId']))
            headers = {'Authorization': 'Bearer ' + identity['token']}
            with TestClient(app, raise_server_exceptions=False) as client:
                def call(method, path, body=None):
                    response = client.request(method, path, json=body, headers=headers)
                    self.assertEqual(response.status_code, 200, response.text)
                    return response.json()
                before = call('GET', '/v1/wallet')
                reserved = call('POST', '/v1/attempts/reserve', {'commandId': uuid.uuid4().hex, 'expectedRevision': before['revision'], 'level': fixture['level'], 'starting': fixture['starting']})
                attempt = reserved['attempt']['attemptId']
                start = call('POST', '/v1/attempts/' + attempt + '/start', {'commandId': uuid.uuid4().hex, 'expectedRevision': reserved['wallet']['revision']})
                with app.state.authority.database.transaction() as database:
                    database.execute('UPDATE gameplay_attempts SET seed=? WHERE id=?', (fixture['seed'], attempt))
                revision, delta, last_body, result = 0, [], None, None
                for action in fixture['actions']:
                    if action['kind'] in ('Swap', 'Tap'):
                        delta.append({'index': action['index'], 'kind': action['kind'], 'x': action['ax'], 'y': action['ay'], 'toX': action['bx'], 'toY': action['by']})
                        continue
                    self.assertEqual(action['kind'], 'Continue')
                    verify = {'commandId': uuid.uuid4().hex, 'expectedPrefixRevision': revision, 'actions': delta}
                    result = call('POST', '/v1/gameplay/attempts/' + attempt + '/verify', verify)
                    self.assertEqual((result['state'], result['model']['outcome']), ('Committed', 'Out of moves'))
                    revision, delta = result['prefixRevision'], []
                    continued = call('POST', '/v1/gameplay/attempts/' + attempt + '/continue', {'commandId': uuid.uuid4().hex, 'expectedPrefixRevision': revision, 'actions': [], 'expectedWalletRevision': result['wallet']['revision']})
                    self.assertEqual((continued['state'], continued['addedMoves'], continued['model']['moves']), ('Committed', 5, 5))
                    self.assertTrue(continued['paidReceiptId'].startswith('wallet/'))
                    revision = continued['prefixRevision']
                last_body = {'commandId': uuid.uuid4().hex, 'expectedPrefixRevision': revision, 'actions': delta}
                result = call('POST', '/v1/gameplay/attempts/' + attempt + '/verify', last_body)
                self.assertEqual((result['state'], result['model']['outcome']), ('Committed', 'Won'))
                self.assertEqual((result['displayReceipt']['awardedCoins'], result['displayReceipt']['awardedStars'], result['displayReceipt']['firstClear']), (50, 1, True))
                self.assertEqual((result['wallet']['lives'], result['wallet']['coins']), (before['lives'], before['coins'] - case['continues'] * 900 + 50))
                self.assertEqual(call('POST', '/v1/gameplay/attempts/' + attempt + '/verify', last_body), result)
                with app.state.authority.database.connect() as database:
                    self.assertEqual(database.execute('SELECT COUNT(*) FROM verified_clears').fetchone()[0], 1)
                    self.assertEqual(database.execute("SELECT COUNT(*) FROM rewards WHERE source='level'").fetchone()[0], 1)
                    operations = database.execute("SELECT candidate_json,result_json FROM replay_operations WHERE state='Committed'").fetchall()
                    for row in operations:
                        execution = json.loads(row['result_json'])['execution']
                        self.assertEqual(execution['approvalSHA256'], approval_hash)
                        self.assertTrue(execution['process']['jobObjectEnforced'])
                        self.assertEqual(execution['process']['exitCode'], 0)
                print(json.dumps({'scope': 'actual_native_fixture_server_owned_seed_real_model_broker', 'operations': len(operations), 'outcome': result['model']['outcome'],
                    'actualAwardedCoins': result['displayReceipt']['awardedCoins'], 'actualAwardedStars': result['displayReceipt']['awardedStars'], 'continues': case['continues'], 'productionEnabled': False}))


if __name__ == '__main__': unittest.main()
