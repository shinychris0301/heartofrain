# Explicit versioned staging preflight with disposable SQLite and scripted workers.
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest

from hotr_backend import staging105 as staging
from hotr_backend import staging_empty_versioned_upgrade117 as upgrade
from hotr_backend import staging_versioned_preflight117 as preflight
from hotr_backend.replay_contract import ApprovedWorker
from hotr_backend.replay_versions117 import WorkerRegistry
from tests import test_staging105 as fixtures

CONFIG = Path(__file__).resolve().parents[1] / 'config/levels.json'


class FakeApprovedWorker(ApprovedWorker):
    def __init__(self, approval, rows):
        self.enabled, self.timeout, self.approval_sha256 = True, 60, approval
        self.digest = hashlib.sha256(b'controlled-fake-pins').hexdigest()
        self.pins = {'levels': [{'level': x['level'], 'sha256': x['configHash'], 'moves': x['moves']} for x in rows]}
    def _verify_bundle(self):
        return {}, self.pins, self.digest


class StagingVersionedPreflight117Tests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.Staging105Tests('test_initialize_and_preflight_are_database_free')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.m = self.f.ready();self.dbpath = self.m.data_directory / staging.DATABASE
        upgrade.prepare_empty_authority(self.m, 'empty', confirm_empty_history=True)
        raw = CONFIG.read_bytes();self.catalog = self.m.data_directory / 'catalog-review.json';self.catalog.write_bytes(raw);self.digest = hashlib.sha256(raw).hexdigest()
        self.rows = json.loads(raw)['levels'];self.old = FakeApprovedWorker('a'*64,self.rows);self.new = FakeApprovedWorker('b'*64,self.rows)
        self.registry = WorkerRegistry([self.old,self.new],self.new.approval_sha256)

    def verify(self):
        return preflight.verify_prepared_authority(self.m,self.registry,self.catalog,self.digest)

    def snapshot(self):
        with closing(sqlite3.connect(self.dbpath)) as db: return '\n'.join(db.iterdump())

    def add_attempt(self, *, bound=True, approval=None, digest=None):
        player,attempt='1'*32,'2'*32;row=self.rows[0]
        with closing(sqlite3.connect(self.dbpath)) as db, db:
            db.execute("INSERT INTO players(id,reward_totals,created_at) VALUES(?, '{}', 0)",(player,))
            db.execute("INSERT INTO wallets(player_id,initialized,revision,balances) VALUES(?,1,0,'[]')",(player,))
            db.execute("INSERT INTO gameplay_attempts(id,player_id,level,config_hash,seed,selected_json,moves,state,created_at,updated_at) VALUES(?,?,1,?,1,'[]',?,'Started',0,0)",(attempt,player,row['configHash'],row['moves']))
            if bound:db.execute('INSERT INTO staging_attempt_version117 VALUES(?,?,?,?,?,?)',(attempt,approval or self.old.approval_sha256,self.old.digest,1,digest or row['configHash'],row['moves']))
        return attempt

    def test_prepared_empty_catalog_and_workers_are_verified_without_activation(self):
        before=self.snapshot();result=self.verify()
        self.assertEqual((result['status'],result['attemptBindingsChecked'],result['schemaVersion']),('verified_prepared_only',0,16))
        self.assertFalse(result['multiWorkerActivated']);self.assertFalse(result['historicalWorkerProvenanceInferred']);self.assertEqual(self.snapshot(),before)
        with self.assertRaises(staging.StagingError):staging.preflight(self.m)

    def test_prior_bound_worker_is_checked_even_with_new_active_worker(self):
        self.add_attempt();before=self.snapshot();result=self.verify()
        self.assertEqual(result['attemptBindingsChecked'],1);self.assertEqual(self.snapshot(),before)
        with closing(sqlite3.connect(self.dbpath)) as db, db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute('UPDATE staging_attempt_version117 SET approval_sha256=?',('b'*64,))

    def test_unbound_or_mismatched_attempts_fail_without_reassignment(self):
        self.add_attempt(bound=False);before=self.snapshot()
        with self.assertRaises(staging.StagingError) as error:self.verify()
        self.assertEqual(error.exception.code,'versioned_preflight_unbound_attempts');self.assertEqual(self.snapshot(),before)
        with closing(sqlite3.connect(self.dbpath)) as db, db:db.execute('INSERT INTO staging_attempt_version117 VALUES(?,?,?,?,?,?)',('2'*32,self.old.approval_sha256,self.old.digest,1,'f'*64,self.rows[0]['moves']))
        before=self.snapshot()
        with self.assertRaises(staging.StagingError) as error:self.verify()
        self.assertEqual(error.exception.code,'versioned_preflight_attempt_mismatch');self.assertEqual(self.snapshot(),before)

    def test_catalog_digest_worker_pins_and_owned_lock_are_enforced(self):
        before=self.snapshot();self.catalog.write_bytes(self.catalog.read_bytes()+b' ')
        with self.assertRaises(staging.StagingError) as error:self.verify()
        self.assertEqual(error.exception.code,'versioned_preflight_catalog_mismatch');self.catalog.write_bytes(CONFIG.read_bytes())
        self.old.pins['levels'][0]['moves']+=1
        with self.assertRaises(staging.StagingError):self.verify()
        self.old.pins['levels'][0]['moves']-=1
        with staging._lock(self.m,staging.RUNTIME_LOCK,allowed_states=(upgrade.PREPARED,)):
            with self.assertRaises(staging.StagingError) as error:self.verify()
            self.assertEqual(error.exception.code,'staging_owned_lock_busy')
        self.assertEqual(self.snapshot(),before)

    def test_preflight_cannot_run_on_unprepared_default_authority(self):
        f=fixtures.Staging105Tests('test_initialize_and_preflight_are_database_free');f.setUp();self.addCleanup(f.doCleanups);m=f.ready()
        with self.assertRaises(staging.StagingError):preflight.verify_prepared_authority(m,self.registry,self.catalog,self.digest)
        self.assertEqual(staging.ownership_metadata(m)['state'],'Ready')


if __name__ == '__main__':unittest.main()
