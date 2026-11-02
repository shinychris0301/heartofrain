"""Stopped, owned 14->15 search-cursor upgrade and recovery tests."""
from contextlib import closing
import json
import sqlite3
import unittest
from unittest.mock import patch

from hotr_backend import staging105 as staging
from hotr_backend import staging_upgrade112 as previous
from hotr_backend import staging_upgrade115 as upgrade
from hotr_backend.operations import _validate
from tests import test_staging_upgrade112 as fixtures


class StagingUpgrade115Tests(unittest.TestCase):
    def setUp(self):
        # Chain the authentic owner-bound 10->11->12->13->14 fixture and
        # preserve its existing signed marker, state, receipts and backups.
        self.previous = fixtures.StagingUpgrade112Tests('test_backup_receipt_and_prior_compatibility')
        self.previous.setUp()
        self.addCleanup(self.previous.doCleanups)
        self.previous.go()
        self.manifest = self.previous.m
        self.path = self.previous.path
        self.marker = self.previous.marker
        self.ready = self.marker.read_bytes()

    def version(self):
        with closing(sqlite3.connect(self.path)) as db:
            return _validate(db)

    def go(self, name='before-search'):
        return upgrade.migrate_friend_search(self.manifest, name)

    def test_upgrade_is_additive_has_owned_backup_and_prior_receipt_replays(self):
        with closing(sqlite3.connect(self.path)) as db:
            before = upgrade._logical(db)
        result = self.go()
        self.assertEqual((result['fromSchema'], result['toSchema'], self.version()), (14, 15, 15))
        self.assertEqual(self.marker.read_bytes(), self.ready)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(upgrade._logical(db), before)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM friend_search_cursors').fetchone()[0], 0)
        backup = self.manifest.data_directory / 'backups/before-search.schema14.sqlite3'
        with closing(sqlite3.connect(backup)) as db:
            self.assertEqual(_validate(db), 14)
            self.assertEqual(upgrade._logical(db), before)
        self.assertTrue(self.go()['alreadyCompleted'])
        self.assertTrue(previous.migrate_team_invites(self.manifest, 'before-invites')['alreadyCompleted'])

    def test_wrong_operation_cannot_resume_pending_or_replace_backup(self):
        def fault(stage):
            if stage == 'AfterPendingMarker':
                raise OSError('controlled interruption')
        with patch.object(upgrade, '_checkpoint', side_effect=fault):
            with self.assertRaises(upgrade.UpgradeError):
                self.go()
        self.assertEqual(json.loads(self.marker.read_text(encoding='utf-8'))['state'], upgrade.PENDING)
        with self.assertRaises(upgrade.UpgradeError):
            self.go('different-name')
        with self.assertRaises(staging.StagingError):
            staging.preflight(self.manifest)
        self.assertEqual(self.version(), 14)
        self.go()
        self.assertEqual((self.version(), self.marker.read_bytes()), (15, self.ready))

    def test_wrong_schema_fails_closed_without_replacing_data(self):
        self.go()
        with self.assertRaises(upgrade.UpgradeError):
            self.go('fresh-name')
        self.assertEqual((self.version(), self.marker.read_bytes()), (15, self.ready))

    def test_resume_rejects_new_cursor_data_after_interrupted_commit(self):
        def fault(stage):
            if stage == 'AfterCommit':
                raise OSError('controlled interruption')
        with patch.object(upgrade, '_checkpoint', side_effect=fault):
            with self.assertRaises(upgrade.UpgradeError):
                self.go()
        with closing(sqlite3.connect(self.path)) as db:
            player = db.execute('SELECT id FROM players LIMIT 1').fetchone()[0]
            db.execute('INSERT INTO friend_search_cursors VALUES(?,?,?,?,?)',
                       ('a' * 64, player, 'b' * 64, player, 9999999999))
            db.commit()
        with self.assertRaises(upgrade.UpgradeError):
            self.go()
        self.assertEqual(json.loads(self.marker.read_text(encoding='utf-8'))['state'], upgrade.PENDING)

    def test_live_owned_runtime_lock_and_forged_owner_are_rejected(self):
        with staging._lock(self.manifest, staging.RUNTIME_LOCK):
            with self.assertRaises(staging.StagingError):
                self.go()
        self.assertEqual((self.version(), self.marker.read_bytes()), (14, self.ready))
        def fault(stage):
            if stage == 'AfterPendingMarker':
                raise OSError('controlled interruption')
        with patch.object(upgrade, '_checkpoint', side_effect=fault):
            with self.assertRaises(upgrade.UpgradeError):
                self.go()
        altered = json.loads(self.marker.read_text(encoding='utf-8'))
        altered['nonce'] = '0' * 32 if altered['nonce'] != '0' * 32 else '1' * 32
        self.marker.write_bytes(upgrade.snapshots._bytes(altered))
        with self.assertRaises((staging.StagingError, upgrade.UpgradeError)):
            self.go()


def _interruption(stage, expected_version, marker_pending):
    def test(self):
        def fault(current):
            if current == stage:
                raise OSError('controlled interruption')
        with patch.object(upgrade, '_checkpoint', side_effect=fault):
            with self.assertRaises(upgrade.UpgradeError):
                self.go()
        self.assertEqual(self.version(), expected_version)
        marker_state = json.loads(self.marker.read_text(encoding='utf-8'))['state']
        self.assertEqual(marker_state, upgrade.PENDING if marker_pending else 'Ready')
        if marker_pending:
            with self.assertRaises(staging.StagingError):
                staging.preflight(self.manifest)
        self.go()
        self.assertEqual((self.version(), self.marker.read_bytes()), (15, self.ready))
    return test


for _stage, _version, _pending in [
    ('AfterBackupReady', 14, False),
    ('AfterPendingMarker', 14, True),
    ('BeforeCommit', 14, True),
    ('AfterCommit', 15, True),
    ('AfterCompleteReceipt', 15, True),
    ('AfterReadyMarker', 15, False),
]:
    setattr(StagingUpgrade115Tests, 'test_resume_' + _stage, _interruption(_stage, _version, _pending))


if __name__ == '__main__':
    unittest.main()
