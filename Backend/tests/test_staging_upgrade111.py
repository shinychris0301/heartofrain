"""Owned schema12-to13 upgrade with crash recovery and immutable backup."""
from contextlib import closing
import json
import sqlite3
import unittest
from unittest.mock import patch

from hotr_backend import staging105 as staging
from hotr_backend import staging_upgrade110 as previous
from hotr_backend import staging_upgrade111 as upgrade
from hotr_backend.operations import _validate
from tests import test_staging_upgrade110 as fixtures


class StagingUpgrade111Tests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.StagingUpgrade110Tests('test_01_composed10_to12_keeps_separate_old_snapshots_nonce_pending_ads_and_finance')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.f.go();self.m=self.f.m;self.path=self.f.db;self.marker=self.f.marker;self.ready=self.marker.read_bytes()

    def version(self):
        with closing(sqlite3.connect(self.path)) as db:return _validate(db)

    def go(self):return upgrade.migrate_team_mail(self.m,'before-mail')

    def test_upgrade_backup_and_old_receipt(self):
        with closing(sqlite3.connect(self.path)) as db: before=upgrade._logical(db)
        result=self.go();self.assertEqual((result['toSchema'],self.version(),self.marker.read_bytes()),(13,13,self.ready))
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(upgrade._logical(db),before)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM team_mail').fetchone()[0],0)
        with closing(sqlite3.connect(self.m.data_directory/'backups/before-mail.schema12.sqlite3')) as db:self.assertEqual(_validate(db),12)
        self.assertTrue(self.go()['alreadyCompleted'])
        self.assertTrue(previous.migrate_team_help(self.m,'before-help')['alreadyCompleted'])

    def test_crash_before_and_after_commit_keep_gate_and_resume(self):
        for stage,expected in [('BeforeCommit',12),('AfterCommit',13)]:
            with self.subTest(stage=stage):
                # Each subcase has its own exact schema12 owned fixture.
                if stage=='AfterCommit':
                    self.f.doCleanups();self.setUp()
                def fault(point):
                    if point==stage:raise OSError('controlled')
                with patch.object(upgrade,'_checkpoint',side_effect=fault):
                    with self.assertRaises(upgrade.UpgradeError):self.go()
                self.assertEqual((self.version(),json.loads(self.marker.read_text())['state']),(expected,upgrade.PENDING))
                with self.assertRaises(staging.StagingError):staging.preflight(self.m)
                self.go();self.assertEqual((self.version(),self.marker.read_bytes()),(13,self.ready))


if __name__=='__main__':unittest.main()
