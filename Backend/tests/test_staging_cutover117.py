# Read-only staging cutover assessment; isolated SQLite, no worker execution.
from contextlib import closing
import json
import sqlite3
import subprocess
import sys
import unittest

from hotr_backend import staging105 as staging
from hotr_backend import staging_cutover117 as cutover
from tests import test_staging105 as fixture


class StagingCutover117Tests(unittest.TestCase):
    def setUp(self):
        self.base = fixture.Staging105Tests('test_initialize_and_preflight_are_database_free')
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.m = self.base.ready()
        self.path = self.m.data_directory / staging.DATABASE

    def snapshot(self):
        with closing(sqlite3.connect(self.path)) as db:
            return '\n'.join(db.iterdump())

    def seed_attempt(self, player, attempt, state):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT INTO players(id,reward_totals,created_at) VALUES(?,?,0)', (player, '{}'))
            db.execute('INSERT INTO wallets(player_id,initialized,revision,balances) VALUES(?,1,0,?)', (player, '[0,0,0,0,0,0,0,0,0,0,5,0]'))
            db.execute("INSERT INTO gameplay_attempts(id,player_id,level,config_hash,seed,selected_json,moves,state,created_at,updated_at) VALUES(?,?,1,?,1,'[0,0,0,0]',20,?,0,0)", (attempt, player, 'a'*64, state))

    def seed_pending_replay(self):
        player, attempt, receipt, operation = 'a'*32, 'b'*32, 'c'*32, 'd'*32
        self.seed_attempt(player, attempt, 'AwaitingContinuation')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO wallet_ledger(id,player_id,origin,delta_json,revision,created_at) VALUES(?,?,?,'[]',1,0)", (receipt, player, 'test'))
            db.execute("INSERT INTO replay_attempts(attempt_id,player_id,start_receipt_id,pins_sha,level_sha,frozen_json,moves,updated_at) VALUES(?,?,?,?,?,'{}',20,0)", (attempt, player, receipt, 'e'*64, 'f'*64))
            db.execute("INSERT INTO replay_operations(id,attempt_id,player_id,command_id,kind,request_hash,request_json,state,base_revision,created_at,updated_at) VALUES(?,?,?,?,'Verify',?,'{}','Pending',0,0,0)", (operation, attempt, player, '1'*32, '2'*64))
            db.execute('UPDATE replay_worker_slot SET operation_id=?,lease_token=?,lease_until=123 WHERE id=1', (operation, '3'*32))

    def test_empty_authority_is_read_only_and_does_not_claim_missing_legacy_provenance(self):
        before, old_preflight = self.snapshot(), staging.preflight(self.m)
        result = cutover.assess_versioned_cutover(self.m)
        self.assertEqual(result['legacyProvenance'], 'not_required_for_empty_attempt_history')
        self.assertEqual(result['legacyAttemptCount'], 0)
        self.assertFalse(result['trustedAttestationValidated'])
        self.assertNotIn('legacy_worker_provenance_requires_independent_evidence', result['blockers'])
        self.assertEqual((result['status'], result['multiWorkerActivated'], result['existingStagingRoutingChanged']), ('blocked', False, False))
        self.assertEqual((self.snapshot(), staging.preflight(self.m)), (before, old_preflight))

    def test_active_and_terminal_history_remains_ambiguous_and_unmodified(self):
        self.seed_pending_replay()
        self.seed_attempt('4'*32, '5'*32, 'Reserved')
        self.seed_attempt('6'*32, '7'*32, 'Started')
        self.seed_attempt('8'*32, '9'*32, 'Won')
        before = self.snapshot()
        result = cutover.assess_versioned_cutover(self.m)
        self.assertEqual((result['legacyAttemptCount'], result['activeLegacyAttemptCount']), (4, 3))
        self.assertEqual((result['legacyProvenance'], result['unfinishedReplayOperationCount'], result['workerSlotOccupied']), ('requires_independent_evidence', 1, True))
        self.assertTrue({'legacy_worker_provenance_requires_independent_evidence', 'active_legacy_attempts_require_preserved_routing', 'legacy_replay_history_requires_preserved_routing', 'unfinished_replay_or_worker_slot_requires_reconciliation'}.issubset(result['blockers']))
        self.assertNotIn('a'*32, json.dumps(result))
        self.assertEqual(self.snapshot(), before)

    def test_stopped_runtime_lock_and_owned_marker_are_enforced(self):
        with staging._lock(self.m, staging.RUNTIME_LOCK):
            with self.assertRaises(staging.StagingError) as error:
                cutover.assess_versioned_cutover(self.m)
            self.assertEqual(error.exception.code, 'staging_owned_lock_busy')
        marker = self.m.data_directory / staging.MARKER
        value = json.loads(marker.read_text(encoding='utf-8'))
        value['deploymentId'] = 'different-owner'
        marker.write_bytes(staging._bytes(value))
        with self.assertRaises(staging.StagingError):
            cutover.assess_versioned_cutover(self.m)
        run = subprocess.run([sys.executable, '-m', 'hotr_backend.staging105', 'assess-versioned-cutover',
                              '--manifest', str(self.base.path)], capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual((run.returncode, json.loads(run.stdout)['code']), (1, 'staging_ownership_mismatch'))

    def test_actual_staging_cli_reports_blocked_with_nonzero_exit(self):
        before = self.snapshot()
        run = subprocess.run([sys.executable, '-m', 'hotr_backend.staging105', 'assess-versioned-cutover',
                              '--manifest', str(self.base.path)], capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(run.returncode, 1)
        result = json.loads(run.stdout)
        self.assertEqual((result['status'], result['legacyProvenance'], result['multiWorkerActivated']),
                         ('blocked', 'not_required_for_empty_attempt_history', False))
        self.assertEqual(run.stderr, '')
        self.assertEqual(self.snapshot(), before)

    def test_unknown_schema_is_rejected_without_repair(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE unapproved_extra(value INTEGER)')
        before = self.snapshot()
        with self.assertRaises(staging.StagingError) as error:
            cutover.assess_versioned_cutover(self.m)
        self.assertEqual(error.exception.code, 'staging_versioned_cutover_inspection_failed')
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
