"""Stopped owned schema13-to14 invitation migration tests."""
from contextlib import closing
import json
import sqlite3
import unittest
from unittest.mock import patch
from hotr_backend import staging105 as staging
from hotr_backend import staging_upgrade111 as previous
from hotr_backend import staging_upgrade112 as upgrade
from hotr_backend.operations import _validate
from tests import test_staging_upgrade111 as fixtures

class StagingUpgrade112Tests(unittest.TestCase):
 def setUp(self):
  self.f=fixtures.StagingUpgrade111Tests('test_upgrade_backup_and_old_receipt');self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.f.go();self.m=self.f.m;self.path=self.f.path;self.marker=self.f.marker;self.ready=self.marker.read_bytes()
 def version(self):
  with closing(sqlite3.connect(self.path)) as db:return _validate(db)
 def go(self):return upgrade.migrate_team_invites(self.m,'before-invites')
 def test_backup_receipt_and_prior_compatibility(self):
  with closing(sqlite3.connect(self.path)) as db:before=upgrade._logical(db)
  result=self.go();self.assertEqual((result['toSchema'],self.version(),self.marker.read_bytes()),(14,14,self.ready))
  with closing(sqlite3.connect(self.path)) as db:
   self.assertEqual(upgrade._logical(db),before)
   self.assertEqual(db.execute('SELECT COUNT(*) FROM team_public_codes').fetchone()[0],0)
   self.assertEqual(db.execute('SELECT COUNT(*) FROM team_invitations').fetchone()[0],0)
  with closing(sqlite3.connect(self.m.data_directory/'backups/before-invites.schema13.sqlite3')) as db:self.assertEqual(_validate(db),13)
  self.assertTrue(self.go()['alreadyCompleted']);self.assertTrue(previous.migrate_team_mail(self.m,'before-mail')['alreadyCompleted'])
 def test_interrupted_before_and_after_commit_resume(self):
  for stage,expected in [('BeforeCommit',13),('AfterCommit',14)]:
   with self.subTest(stage=stage):
    if stage=='AfterCommit':self.f.doCleanups();self.setUp()
    def fault(point):
     if point==stage:raise OSError('controlled')
    with patch.object(upgrade,'_checkpoint',side_effect=fault):
     with self.assertRaises(upgrade.UpgradeError):self.go()
    self.assertEqual((self.version(),json.loads(self.marker.read_text())['state']),(expected,upgrade.PENDING))
    with self.assertRaises(staging.StagingError):staging.preflight(self.m)
    self.go();self.assertEqual((self.version(),self.marker.read_bytes()),(14,self.ready))
if __name__=='__main__':unittest.main()
