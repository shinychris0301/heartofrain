# Explicit versioned staging preparation tests; every database is disposable.
from contextlib import closing
import json
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

from hotr_backend import staging105 as staging
from hotr_backend import staging_empty_versioned_upgrade117 as upgrade
from hotr_backend.operations import _validate
from hotr_backend.storage import Database
from tests import test_staging105 as fixtures


class StagingEmptyVersionedUpgrade117Tests(unittest.TestCase):
    def fresh(self):
        f = fixtures.Staging105Tests('test_initialize_and_preflight_are_database_free')
        f.setUp()
        self.addCleanup(f.doCleanups)
        m = f.ready()
        return f, m, m.data_directory / staging.DATABASE

    @staticmethod
    def logical(path):
        with closing(sqlite3.connect(path)) as db:
            return upgrade._logical15(db)

    def go(self, manifest, name='versioned-empty', **kwargs):
        return upgrade.prepare_empty_authority(manifest, name, confirm_empty_history=True, **kwargs)

    def test_empty_upgrade_is_owner_bound_backed_up_and_does_not_enable_runtime(self):
        f, m, path = self.fresh()
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("INSERT INTO players(id,reward_totals,created_at) VALUES(?, '{}', 0)", ('a'*32,))
            db.execute("INSERT INTO wallets(player_id,initialized,revision,balances) VALUES(?,1,0,'[0,0,0,0,0,0,0,0,0,0,5]')", ('a'*32,))
        before = self.logical(path)
        result = self.go(m)
        self.assertEqual((result['status'], result['fromSchema'], result['toSchema'], result['legacyAttemptsBound']), ('prepared', 15, 16, 0))
        self.assertFalse(result['multiWorkerActivated'])
        self.assertFalse(result['trustedLegacyAttestationValidated'])
        self.assertEqual(self.logical(path), before)
        self.assertEqual(staging.ownership_metadata(m, allowed_states=(upgrade.PREPARED,))['state'], upgrade.PREPARED)
        with closing(sqlite3.connect(path)) as db:
            upgrade._validate16(db)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM staging_attempt_version117').fetchone()[0], 0)
        backup = m.data_directory / 'backups/versioned-empty.schema15.sqlite3'
        with closing(sqlite3.connect(backup)) as db:
            self.assertEqual((_validate(db), upgrade._logical15(db)), (15, before))
        with self.assertRaises(staging.StagingError): staging.preflight(m)
        with self.assertRaises(RuntimeError): Database(path)
        self.assertTrue(self.go(m)['alreadyCompleted'])
        self.assertEqual(self.logical(path), before)

    def test_interruption_at_each_boundary_resumes_exact_operation(self):
        for stage in ('AfterBackupReady', 'AfterPendingMarker', 'BeforeCommit', 'AfterCommit', 'AfterCompleteReceipt', 'AfterPreparedMarker'):
            with self.subTest(stage=stage):
                f, m, path = self.fresh()
                before = self.logical(path)
                def fault(value):
                    if value == stage: raise OSError('controlled test cut')
                with patch.object(upgrade, '_checkpoint', side_effect=fault):
                    with self.assertRaises(upgrade.UpgradeError): self.go(m)
                self.assertEqual(self.logical(path), before)
                self.assertEqual(self.go(m)['status'], 'prepared')
                self.assertEqual(self.logical(path), before)
                with closing(sqlite3.connect(path)) as db: upgrade._validate16(db)

    def test_any_legacy_attempt_state_is_refused_without_binding_or_backup(self):
        for state in ('Reserved', 'Started', 'AwaitingContinuation', 'Won', 'Lost', 'Cancelled', 'Released'):
            with self.subTest(state=state):
                f, m, path = self.fresh()
                with closing(sqlite3.connect(path)) as db, db:
                    db.execute("INSERT INTO players(id,reward_totals,created_at) VALUES(?, '{}', 0)", ('a'*32,))
                    db.execute("INSERT INTO wallets(player_id,initialized,revision,balances) VALUES(?,1,0,'[]')", ('a'*32,))
                    db.execute("INSERT INTO gameplay_attempts(id,player_id,level,config_hash,seed,selected_json,moves,state,created_at,updated_at) VALUES(?,?,1,?,1,'[]',20,?,0,0)", ('b'*32, 'a'*32, 'f'*64, state))
                before = self.logical(path)
                with self.assertRaises(upgrade.UpgradeError) as error: self.go(m)
                self.assertEqual(error.exception.code, 'versioned_upgrade_legacy_history_requires_provenance')
                self.assertEqual(self.logical(path), before)
                self.assertFalse((m.data_directory / 'backups/versioned-empty.schema15.sqlite3').exists())
                self.assertEqual(staging.ownership_metadata(m)['state'], 'Ready')

    def test_explicit_confirmation_lock_and_foreign_owner_are_required(self):
        f, m, path = self.fresh()
        before = self.logical(path)
        with self.assertRaises(upgrade.UpgradeError): upgrade.prepare_empty_authority(m, 'versioned-empty')
        with staging._lock(m, staging.RUNTIME_LOCK):
            with self.assertRaises(staging.StagingError): self.go(m)
        marker = m.data_directory / staging.MARKER
        data = json.loads(marker.read_text(encoding='utf-8'));data['deploymentId'] = 'other-owner';marker.write_bytes(staging._bytes(data))
        with self.assertRaises(staging.StagingError): self.go(m)
        self.assertEqual(self.logical(path), before)

    def test_interrupted_snapshot_tampering_or_wrong_operation_cannot_resume(self):
        f, m, path = self.fresh()
        def fault(stage):
            if stage == 'AfterPendingMarker': raise OSError('controlled test cut')
        with patch.object(upgrade, '_checkpoint', side_effect=fault):
            with self.assertRaises(upgrade.UpgradeError): self.go(m)
        with self.assertRaises(upgrade.UpgradeError): self.go(m, 'other-name')
        backup = m.data_directory / 'backups/versioned-empty.schema15.sqlite3'
        with backup.open('r+b') as stream: stream.seek(256); v = stream.read(1); stream.seek(256); stream.write(bytes([v[0]^1]))
        with self.assertRaises(upgrade.UpgradeError) as error: self.go(m)
        self.assertEqual(error.exception.code, 'versioned_upgrade_snapshot_hash_mismatch')
        self.assertEqual(staging.ownership_metadata(m, allowed_states=(upgrade.PENDING,))['state'], upgrade.PENDING)

    def test_prepared_database_change_or_extra_table_fails_closed(self):
        f, m, path = self.fresh();self.go(m)
        with closing(sqlite3.connect(path)) as db, db: db.execute('CREATE TABLE extra_not_approved(v INTEGER)')
        with self.assertRaises(upgrade.UpgradeError): self.go(m)
        self.assertEqual(staging.ownership_metadata(m, allowed_states=(upgrade.PREPARED,))['state'], upgrade.PREPARED)

    def test_stale_worker_slot_and_changed_pending_data_are_refused(self):
        f, m, path = self.fresh()
        with closing(sqlite3.connect(path)) as db, db: db.execute('UPDATE replay_worker_slot SET lease_until=123 WHERE id=1')
        with self.assertRaises(upgrade.UpgradeError) as error: self.go(m)
        self.assertEqual(error.exception.code, 'versioned_upgrade_worker_slot_not_empty')
        self.assertFalse((m.data_directory / 'backups/versioned-empty.schema15.sqlite3').exists())
        with closing(sqlite3.connect(path)) as db, db: db.execute('UPDATE replay_worker_slot SET lease_until=0 WHERE id=1')
        def fault(stage):
            if stage == 'AfterPendingMarker': raise OSError('controlled test cut')
        with patch.object(upgrade, '_checkpoint', side_effect=fault):
            with self.assertRaises(upgrade.UpgradeError): self.go(m)
        with closing(sqlite3.connect(path)) as db, db: db.execute("INSERT INTO players(id,reward_totals,created_at) VALUES(?, '{}', 0)", ('f'*32,))
        with self.assertRaises(upgrade.UpgradeError) as error: self.go(m)
        self.assertEqual(error.exception.code, 'versioned_upgrade_source_state_changed')
        self.assertEqual(staging.ownership_metadata(m, allowed_states=(upgrade.PENDING,))['state'], upgrade.PENDING)

    def test_actual_cli_requires_explicit_empty_history_confirmation(self):
        f, m, path = self.fresh();before = self.logical(path)
        command = [sys.executable, '-m', 'hotr_backend.staging_empty_versioned_upgrade117', '--manifest', str(f.path), '--name', 'cli-empty']
        refused = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual((refused.returncode, json.loads(refused.stdout)['code']), (1, 'versioned_upgrade_explicit_empty_history_confirmation_required'))
        self.assertEqual(self.logical(path), before)
        done = subprocess.run(command + ['--confirm-empty-history'], capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual((done.returncode, json.loads(done.stdout)['status']), (0, 'prepared'))
        self.assertEqual(self.logical(path), before)


if __name__ == '__main__': unittest.main()
