"""Temporary exact10/11 authorities, staged recovery and old107/109 state."""
from contextlib import closing
import json
import hashlib
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from hotr_backend import staging105 as staging
from hotr_backend import staging_upgrade109 as previous
from hotr_backend import staging_upgrade110 as upgrade
from hotr_backend.operations import _validate, backup_database
from hotr_backend.storage import canonical
from tests import test_staging_upgrade109 as historical_fixtures


def original109_fingerprint(db):
    """Independent pre110 algorithm, matching the byte-retained109 source.

    Generate an actual old-style pending proof, rather than using the new
    implementation as its own fixture generator.
    """
    digest = hashlib.sha256()
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name<>'schema_info' ORDER BY name")]
    for table in tables:
        columns = [r[1] for r in db.execute('PRAGMA table_info(' + table + ')') if r[1] != 'badge_id']
        names = ','.join('"' + name + '"' for name in columns)
        digest.update(canonical([table, columns]).encode('ascii'))
        for row in db.execute('SELECT ' + names + ' FROM "' + table + '" ORDER BY ' + names):
            digest.update(canonical(list(row)).encode('ascii'))
            digest.update(b'\n')
    return digest.hexdigest()


class StagingUpgrade110Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = historical_fixtures.StagingUpgrade109Tests('test_01_exact_upgrade_preserves_owner_finance_pending_rewards_and_old_create_receipt')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.m = self.fixture.manifest
        self.db = self.fixture.db_path
        self.marker = self.fixture.marker_path
        self.original = self.fixture.original_marker
        self.original10 = self.fixture.original_logical

    def version(self):
        with closing(sqlite3.connect(self.db)) as db:
            return _validate(db)

    def go(self, **kwargs):
        return upgrade.migrate_team_help(self.m, 'before-help', **kwargs)

    def prepare11(self):
        previous.migrate_team_badges(self.m, 'old-badges')
        with closing(sqlite3.connect(self.db)) as db:
            db.execute("UPDATE social_teams SET badge_id='oak'")
            db.commit()

    def interrupt(self, stage):
        def fault(point):
            if point == stage:
                raise OSError('controlled-upgrade110-fault')
        with patch.object(upgrade, '_checkpoint', side_effect=fault):
            with self.assertRaises(upgrade.UpgradeError):
                self.go()

    def assert_pending(self, version):
        self.assertEqual(self.version(), version)
        self.assertEqual(json.loads(self.marker.read_text())['state'], upgrade.PENDING)
        for action in (lambda: staging.preflight(self.m), lambda: staging._construct(self.m, None)):
            with self.assertRaises(staging.StagingError):
                action()
        with patch.object(staging.socket, 'socket') as socket:
            with self.assertRaises(staging.StagingError):
                staging.start(self.m)
            socket.assert_not_called()

    def test_01_composed10_to12_keeps_separate_old_snapshots_nonce_pending_ads_and_finance(self):
        result = self.go()
        self.assertEqual((result['toSchema'], self.version(), self.marker.read_bytes()), (12, 12, self.original))
        self.assertEqual(self.fixture.logical(), self.original10)
        for name, version in (('before-help-to11.schema10.sqlite3', 10), ('before-help.schema11.sqlite3', 11)):
            with closing(sqlite3.connect(self.m.data_directory / 'backups' / name)) as db:
                self.assertEqual(_validate(db), version)
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('SELECT state FROM rewarded_ad_opportunities').fetchone()[0], 'CompletedReported')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM team_life_requests').fetchone()[0], 0)
        self.assertTrue(self.go()['alreadyCompleted'])

    def test_02_schema11_upgrade_keeps_real_badge_values_and_historical109_completed_replay(self):
        self.prepare11()
        self.go()
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('SELECT badge_id FROM social_teams').fetchone()[0], 'oak')
        self.assertTrue(previous.migrate_team_badges(self.m, 'old-badges')['alreadyCompleted'])

    def test_03_pending109_precommit_resume_requires_explicit_original_proof_and_then_completes12(self):
        with patch.object(previous, '_logical', original109_fingerprint):
            self.fixture.interrupt('BeforeCommit')
        with self.assertRaises(previous.UpgradeError):
            self.go()
        self.assertEqual(json.loads(self.marker.read_text())['state'], previous.PENDING)
        self.go(prior_name='before-badges')
        self.assertEqual((self.version(), self.marker.read_bytes()), (12, self.original))

    def test_04_pending109_postcommit_resume_never_replaces_old_identity_or_financial_rows(self):
        with patch.object(previous, '_logical', original109_fingerprint):
            self.fixture.interrupt('AfterCommit')
        self.go(prior_name='before-badges')
        self.assertEqual(self.fixture.logical(), self.original10)
        self.assertEqual((self.version(), self.marker.read_bytes()), (12, self.original))

    def test_05_pending110_precommit_rolls_back12_tables_and_retry_is_safe(self):
        self.prepare11()
        self.interrupt('BeforeCommit')
        self.assert_pending(11)
        self.go()
        self.assertEqual((self.version(), self.marker.read_bytes()), (12, self.original))

    def test_06_pending110_postcommit_keeps_ordinary_factory_closed_until_exact_recovery(self):
        self.prepare11()
        self.interrupt('AfterCommit')
        self.assert_pending(12)
        self.go()
        self.assertEqual(self.marker.read_bytes(), self.original)

    def test_07_complete_receipt_and_lost_ready_ack_are_idempotent(self):
        self.prepare11()
        self.interrupt('AfterCompleteReceipt')
        self.assert_pending(12)
        self.go()
        self.assertTrue(self.go()['alreadyCompleted'])

    def test_08_runtime_lock_and_changed_owned_backup_block_without_migrating(self):
        self.prepare11()
        with staging._lock(self.m, staging.RUNTIME_LOCK):
            with self.assertRaises(staging.StagingError):
                self.go()
        self.interrupt('BeforeCommit')
        path = self.m.data_directory / 'backups/before-help.schema11.sqlite3'
        data = path.read_bytes() + b'foreign'
        path.write_bytes(data)
        with self.assertRaises(upgrade.UpgradeError):
            self.go()
        self.assertEqual(path.read_bytes(), data)
        self.assert_pending(11)

    def test_09_partial_backup_requires_new_explicit_name_without_losing_old_records(self):
        self.prepare11()
        def fail(source, target, **kwargs):
            target.write_bytes(b'incomplete')
            raise OSError('controlled-backup-failure')
        with patch.object(upgrade, 'backup_database', side_effect=fail):
            with self.assertRaises(upgrade.UpgradeError):
                self.go()
        self.assertEqual(self.version(), 11)
        self.assertEqual(self.marker.read_bytes(), self.original)
        upgrade.migrate_team_help(self.m, 'new-reviewed-name')
        self.assertEqual(self.fixture.logical(), self.original10)


if __name__ == '__main__':
    unittest.main()
