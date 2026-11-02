"""Current single-worker replay cutover guards; not multi-version support.

Scripted workers do not run Unity or prove game rules. These tests demonstrate
existing mismatch refusal; they do not imply safe multi-worker activation.
"""
import copy
import unittest

from fastapi.testclient import TestClient
from hotr_backend.api import create_app
import test_replay_service as fixtures


class CampaignCutover117Tests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ReplayServiceTests('test_01_default_disabled_and_no_client_win_seed_checkpoint_receipt_or_budget_override')
        self.f.setUp()
        self.addCleanup(self.f.tearDown)

    def snapshot(self):
        with self.f.authority.database.connect() as db:
            return {table: [dict(row) for row in db.execute('SELECT * FROM ' + table + ' ORDER BY rowid').fetchall()]
                    for table in ('wallets', 'wallet_ledger', 'gameplay_attempts', 'replay_attempts', 'replay_operations')}

    def test_mismatched_catalog_worker_does_not_replace_live_or_reserved_attempt(self):
        wallet = self.f.wallet(who=1)
        self.f.request('POST', '/v1/attempts/reserve', {'commandId': fixtures.ident(), 'expectedRevision': wallet['revision'],
            'level': 1, 'starting': [0, 0, 0, 0]}, who=1)
        before = self.snapshot()
        next_worker = fixtures.ScriptedWorker()
        next_worker.pins = copy.deepcopy(next_worker.pins)
        next_worker.pins['levels'][10]['sha256'] = 'f' * 64
        with self.assertRaisesRegex(RuntimeError, 'Replay and server level catalog differ'):
            create_app(self.f.path, fixtures.CONFIG, lambda: self.f.now, replay_enabled=True, replay_worker=next_worker)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.f.submit()['state'], 'Committed')

    def test_registered_attempt_rejects_a_different_pins_manifest_and_old_worker_recovers(self):
        self.assertEqual(self.f.submit()['state'], 'Committed')
        before = self.snapshot()
        next_worker = fixtures.ScriptedWorker()
        next_worker.digest = 'f' * 64
        new_app = create_app(self.f.path, fixtures.CONFIG, lambda: self.f.now, replay_enabled=True, replay_worker=next_worker)
        with TestClient(new_app, raise_server_exceptions=False) as client:
            response = client.post('/v1/gameplay/attempts/' + self.f.attempt + '/verify',
                json=self.f.body(1, self.f.moves(first=1)), headers=self.f.headers())
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(response.json()['error'], 'attempt_configuration_mismatch')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.f.submit(body=self.f.body(1, self.f.moves(first=1)))['state'], 'Committed')

if __name__ == '__main__':
    unittest.main()
