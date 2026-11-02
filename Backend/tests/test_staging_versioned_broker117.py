"""Unregistered real-broker adapter with scripted workers and temporary SQLite."""
import json
import concurrent.futures
import threading
import unittest

from hotr_backend.replay_contract import TrustedModelFault
from hotr_backend.replay_schemas import ReplayTool, VerifyReplay
from hotr_backend.replay_versions117 import WorkerRegistry
from hotr_backend.service import ServiceError
from hotr_backend.staging_versioned_replay117 import STAGING_BINDINGS_DDL, StagingBoundAttempts, StagingVersionedReplay
from hotr_backend.wallet_schemas import ReserveAttempt, WalletCommand
import test_replay_service as fixtures


class VersionedScriptedWorker(fixtures.ScriptedWorker):
    def __init__(self, approval):
        super().__init__();self.approval_sha256=approval;self.proof_override=None
    def run(self, job):
        try: proof=super().run(job)
        except TrustedModelFault as error:
            error.proof['approvalSHA256']=self.proof_override or self.approval_sha256
            raise
        proof['approvalSHA256']=self.proof_override or self.approval_sha256
        return proof


class StagingVersionedBroker117Tests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReplayServiceTests('test_01_default_disabled_and_no_client_win_seed_checkpoint_receipt_or_budget_override')
        self.f.setUp();self.addCleanup(self.f.tearDown)
        with self.f.authority.database.connect() as db: db.executescript(STAGING_BINDINGS_DDL)
        self.old,self.new=VersionedScriptedWorker('a'*64),VersionedScriptedWorker('b'*64)
        self.registry=WorkerRegistry([self.old,self.new],self.old.approval_sha256)
        self.bound=StagingBoundAttempts(self.f.app.state.wallet,self.registry)
        self.actor=self.f.authority.authenticate(self.f.identities[1]['token'])
        wallet=self.f.wallet(who=1)
        self.reserved=self.bound.reserve(self.actor,ReserveAttempt(commandId=fixtures.ident(),expectedRevision=wallet['revision'],level=1,starting=[0,0,0,0]))
        self.id=self.reserved['attempt']['attemptId']
        self.bound.start(self.actor,self.id,WalletCommand(commandId=fixtures.ident(),expectedRevision=self.reserved['wallet']['revision']))
        self.registry=WorkerRegistry([self.old,self.new],self.new.approval_sha256)
        self.bound=StagingBoundAttempts(self.f.app.state.wallet,self.registry)
        self.replay=StagingVersionedReplay(self.bound)

    def verify(self,revision=0,actions=None):
        return VerifyReplay.model_validate(self.f.body(revision,actions=[] if actions is None else actions))
    def tool(self,revision=0):
        return ReplayTool.model_validate(self.f.body(revision,[],expectedWalletRevision=self.f.wallet(who=1)['revision'],tool=0,x=1,y=1))

    def test_real_broker_routes_old_approval_and_idempotent_result(self):
        request=self.verify(actions=self.f.moves())
        value=self.replay.submit(self.actor,self.id,'Verify',request)
        self.assertEqual(value['state'],'Committed')
        self.assertEqual((len(self.old.calls),len(self.new.calls)),(1,0))
        self.assertEqual(self.replay.submit(self.actor,self.id,'Verify',request),value)
        self.assertEqual((len(self.old.calls),len(self.new.calls)),(1,0))
        self.assertEqual(self.replay.get(self.actor,self.id,request.commandId),value)

    def test_binding_removed_during_worker_fences_paid_commit(self):
        self.assertEqual(self.replay.submit(self.actor,self.id,'Verify',self.verify())['state'],'Committed')
        before=self.f.wallet(who=1)
        def delete_binding(job):
            with self.f.authority.database.transaction() as db: db.execute('DELETE FROM staging_attempt_version117 WHERE attempt_id=?',(self.id,))
        self.old.observer=delete_binding
        value=self.replay.submit(self.actor,self.id,'Tool',self.tool(1))
        self.assertEqual((value['state'],value['code']),('Rejected','attempt_version_missing'))
        after=self.f.wallet(who=1)
        self.assertEqual((before['coins'],before['tools'],before['lives']),(after['coins'],after['tools'],after['lives']))
        with self.f.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM replay_paid_bindings WHERE attempt_id=?',(self.id,)).fetchone()[0],0)
            self.assertEqual(db.execute('SELECT revision FROM replay_attempts WHERE attempt_id=?',(self.id,)).fetchone()[0],1)

    def test_bad_approval_proof_leaves_paid_operation_pending_and_recoverable(self):
        self.assertEqual(self.replay.submit(self.actor,self.id,'Verify',self.verify())['state'],'Committed')
        before=self.f.wallet(who=1);request=self.tool(1);self.old.proof_override='f'*64
        value=self.replay.submit(self.actor,self.id,'Tool',request)
        self.assertEqual((value['state'],value['code']),('Pending','replay_temporarily_unavailable'))
        self.assertEqual(self.f.wallet(who=1)['tools'],before['tools'])
        self.old.proof_override=None
        value=self.replay.resume(self.actor,self.id,request.commandId)
        self.assertEqual(value['state'],'Committed')
        self.assertEqual(value['wallet']['tools'][0],before['tools'][0]-1)
        self.assertEqual(self.replay.resume(self.actor,self.id,request.commandId),value)

    def test_binding_replaced_during_worker_fences_even_with_identical_level_pins(self):
        self.assertEqual(self.replay.submit(self.actor,self.id,'Verify',self.verify())['state'],'Committed')
        before=self.f.wallet(who=1)
        def replace_binding(job):
            with self.f.authority.database.transaction() as db:
                binding=db.execute('SELECT * FROM staging_attempt_version117 WHERE attempt_id=?',(self.id,)).fetchone()
                db.execute('DELETE FROM staging_attempt_version117 WHERE attempt_id=?',(self.id,))
                db.execute('INSERT INTO staging_attempt_version117 VALUES(?,?,?,?,?,?)',
                    (self.id,self.new.approval_sha256,binding['pins_sha256'],binding['level'],binding['level_sha256'],binding['initial_moves']))
        self.old.observer=replace_binding
        value=self.replay.submit(self.actor,self.id,'Tool',self.tool(1))
        self.assertEqual((value['state'],value['code']),('Rejected','attempt_configuration_mismatch'))
        self.assertEqual(self.f.wallet(who=1)['tools'],before['tools'])
        with self.f.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM replay_paid_bindings WHERE attempt_id=?',(self.id,)).fetchone()[0],0)

    def test_fault_result_requires_bound_worker_proof_before_release(self):
        before=self.f.wallet(who=1);request=self.verify();self.old.fault=True;self.old.proof_override='f'*64
        value=self.replay.submit(self.actor,self.id,'Verify',request)
        self.assertEqual(value['state'],'Pending')
        self.assertEqual(self.f.wallet(who=1)['lives'],before['lives'])
        self.old.proof_override=None
        value=self.replay.resume(self.actor,self.id,request.commandId)
        self.assertEqual((value['state'],value['code'],value['attempt']['state']),('Committed','model_fault','Released'))
        self.assertEqual(value['wallet']['lives'],before['lives'])

    def test_account_deletion_during_worker_fences_paid_action(self):
        self.assertEqual(self.replay.submit(self.actor,self.id,'Verify',self.verify())['state'],'Committed')
        before=self.f.wallet(who=1);request=self.tool(1)
        def delete_account(job):
            with self.f.authority.database.transaction() as db:
                db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)",(self.actor.player,self.f.now))
                db.execute('UPDATE credentials SET revoked=1 WHERE player_id=?',(self.actor.player,))
        self.old.observer=delete_account
        with self.assertRaises(ServiceError): self.replay.submit(self.actor,self.id,'Tool',request)
        with self.f.authority.database.connect() as db:
            balances=json.loads(db.execute('SELECT balances FROM wallets WHERE player_id=?',(self.actor.player,)).fetchone()[0])
            self.assertEqual((balances[0],balances[6],balances[10]),(before['coins'],before['tools'][0],before['lives']))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM replay_paid_bindings WHERE attempt_id=?',(self.id,)).fetchone()[0],0)
            self.assertEqual(db.execute('SELECT revision FROM replay_attempts WHERE attempt_id=?',(self.id,)).fetchone()[0],1)

    def test_slow_bundle_reverification_does_not_hold_sqlite_writer_lock(self):
        started, release=threading.Event(),threading.Event()
        original=self.old._verify_bundle
        def slow():
            started.set()
            if not release.wait(5): raise RuntimeError('test timeout')
            return original()
        self.old._verify_bundle=slow
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(self.replay.submit,self.actor,self.id,'Verify',self.verify())
                try:
                    self.assertTrue(started.wait(3),'bundle check did not start')
                    with self.f.authority.database.transaction(timeout=.2) as db:
                        db.execute('UPDATE wallets SET revision=revision WHERE player_id=?',(self.actor.player,))
                finally:
                    release.set()
                self.assertEqual(future.result(timeout=5)['state'],'Committed')
        finally:
            release.set();self.old._verify_bundle=original

    def test_unbound_legacy_attempt_is_never_inferred(self):
        old_actor=self.f.authority.authenticate(self.f.identities[0]['token'])
        with self.assertRaises(ServiceError) as error: self.replay.submit(old_actor,self.f.attempt,'Verify',self.verify())
        self.assertEqual(error.exception.code,'attempt_version_missing')

if __name__=='__main__': unittest.main()
