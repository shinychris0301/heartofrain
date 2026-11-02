"""Isolated registry tests using deliberately scripted, non-Unity workers."""
import copy
import unittest
from dataclasses import FrozenInstanceError, replace

from hotr_backend.replay_contract import ReplayError
from hotr_backend.replay_versions117 import AttemptVersion, WorkerRegistry
import test_replay_service as fixtures
import test_replay_contract as contract_fixtures


class ReplayVersionRegistry117Tests(unittest.TestCase):
    def setUp(self):
        self.old, self.new = fixtures.ScriptedWorker(), fixtures.ScriptedWorker()
        self.old.approval_sha256, self.new.approval_sha256 = 'a'*64, 'b'*64
        self.registry = WorkerRegistry([self.old, self.new], self.new.approval_sha256)
        self.level_sha = self.new.pins['levels'][0]['sha256']
        self.moves = self.new.pins['levels'][0]['moves']

    def new_binding(self):
        return self.registry.reserve_binding(1, self.level_sha, self.moves)

    def job(self, binding):
        return {'version': 1, 'level': binding.level, 'initialMoves': binding.initial_moves, 'seed': 42,
            'jobId': '1'*32, 'playerId': '2'*32, 'attemptId': '3'*32,
            'pinsSHA256': binding.pins_sha256, 'levelSHA256': binding.level_sha256,
            'startReceiptId': 'wallet/'+'4'*64, 'starting': [0, 0, 0, 0], 'actions': [], 'receipts': []}

    def test_distinct_approvals_are_routed_even_if_manifest_and_level_hashes_match(self):
        old_binding = WorkerRegistry([self.old], self.old.approval_sha256).reserve_binding(1, self.level_sha, self.moves)
        new_binding = self.new_binding()
        self.assertEqual((old_binding.pins_sha256, old_binding.level_sha256), (new_binding.pins_sha256, new_binding.level_sha256))
        self.assertNotEqual(old_binding.approval_sha256, new_binding.approval_sha256)
        self.registry.run(old_binding, self.job(old_binding)); self.registry.run(new_binding, self.job(new_binding))
        self.assertEqual((len(self.old.calls), len(self.new.calls)), (1, 1))
        with self.assertRaises(FrozenInstanceError): new_binding.level = 2

    def test_duplicate_missing_unapproved_and_unbounded_workers_rejected(self):
        for workers, active in (([self.old,self.old],self.old.approval_sha256), ([self.old],self.new.approval_sha256), ([object()],self.old.approval_sha256)):
            with self.subTest(workers=len(workers)), self.assertRaises(ReplayError): WorkerRegistry(workers, active)
        self.old.timeout = 91
        with self.assertRaises(ReplayError): WorkerRegistry([self.old], self.old.approval_sha256)
        self.old.timeout = 60; self.old.enabled = False
        with self.assertRaises(ReplayError): WorkerRegistry([self.old], self.old.approval_sha256)

    def test_catalog_mismatch_and_invalid_level_never_bind(self):
        for level, digest, moves in ((1,'f'*64,self.moves),(1,self.level_sha,self.moves+1),(True,self.level_sha,self.moves),(51,self.level_sha,self.moves),(1,self.level_sha,True)):
            with self.subTest(level=level), self.assertRaises(ReplayError): self.registry.reserve_binding(level,digest,moves)

    def test_corrupt_or_unavailable_persisted_binding_never_runs(self):
        b = self.new_binding(); job = self.job(b)
        for bad in (None, replace(b,approval_sha256='c'*64),replace(b,pins_sha256='f'*64),replace(b,level_sha256='f'*64),replace(b,level=2),replace(b,initial_moves=b.initial_moves+1)):
            with self.subTest(binding=bad), self.assertRaises(ReplayError): self.registry.run(bad,job)
        self.assertEqual((len(self.old.calls),len(self.new.calls)), (0,0))

    def test_job_cannot_choose_other_level_manifest_or_moves(self):
        b=self.new_binding(); original=self.job(b)
        for key,value in (('pinsSHA256','f'*64),('levelSHA256','f'*64),('initialMoves',b.initial_moves+1),('level',2)):
            job=copy.deepcopy(original);job[key]=value
            with self.subTest(key=key), self.assertRaises(ReplayError): self.registry.run(b,job)
        self.assertEqual((len(self.old.calls),len(self.new.calls)), (0,0))

    def test_rechecks_worker_and_manifest_on_resolve(self):
        b=self.new_binding()
        self.new.digest='f'*64
        with self.assertRaises(ReplayError): self.registry.resolve(b)
        self.new.digest=b.pins_sha256; self.new.pins['levels'][0]['sha256']='f'*64
        with self.assertRaises(ReplayError): self.registry.resolve(b)
        self.new.pins['levels'][0]['sha256']=self.level_sha; self.new.approval_sha256='c'*64
        with self.assertRaises(ReplayError): self.registry.resolve(b)
        self.assertEqual((len(self.old.calls),len(self.new.calls)), (0,0))

    def test_worker_pin_shape_is_checked(self):
        self.new.pins['levels'][0]['level']=True
        with self.assertRaises(ReplayError): WorkerRegistry([self.new],self.new.approval_sha256)
        self.new.pins['levels'][0]['level']=1; self.new.pins['levels'][0]['moves']=True
        with self.assertRaises(ReplayError): WorkerRegistry([self.new],self.new.approval_sha256)

    def test_actual_bundle_validator_rechecks_changed_file(self):
        fixture=contract_fixtures.ReplayContractTests('test_01_exact_job_roundtrip_rejects_client_won_checkpoint_and_duplicate_keys')
        fixture.setUp(); self.addCleanup(fixture.tearDown)
        worker=fixture.broker(); registry=WorkerRegistry([worker],worker.approval_sha256)
        pin=registry.reserve_binding(1,fixture.job['levelSHA256'],26)
        self.assertIs(registry.resolve(pin),worker)
        (fixture.bundle/'PinnedReplayWorker.exe').write_bytes(b'tampered-fixture-binary')
        with self.assertRaises(ReplayError): registry.resolve(pin)

if __name__ == '__main__': unittest.main()
