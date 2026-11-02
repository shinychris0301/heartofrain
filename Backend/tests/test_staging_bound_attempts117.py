"""Experimental, unexposed staging reservation component on temporary SQLite."""
import json
import sqlite3
import unittest

from hotr_backend.replay_contract import ReplayError
from hotr_backend.replay_versions117 import WorkerRegistry
from hotr_backend.service import ServiceError
from hotr_backend.staging_versioned_replay117 import STAGING_BINDINGS_DDL, StagingBoundAttempts
from hotr_backend.wallet_schemas import ReserveAttempt, WalletCommand
import test_replay_service as fixtures


class StagingBoundAttempts117Tests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReplayServiceTests('test_01_default_disabled_and_no_client_win_seed_checkpoint_receipt_or_budget_override')
        self.f.setUp(); self.addCleanup(self.f.tearDown)
        with self.f.authority.database.connect() as db: db.executescript(STAGING_BINDINGS_DDL)
        self.old,self.new=fixtures.ScriptedWorker(),fixtures.ScriptedWorker()
        self.old.approval_sha256,self.new.approval_sha256='a'*64,'b'*64
        self.registry=WorkerRegistry([self.old,self.new],self.new.approval_sha256)
        self.bound=StagingBoundAttempts(self.f.app.state.wallet,self.registry)
        self.actor=self.f.authority.authenticate(self.f.identities[1]['token'])
        revision=self.f.wallet(who=1)['revision']
        self.request=ReserveAttempt(commandId=fixtures.ident(),expectedRevision=revision,level=1,starting=[0,0,0,0])

    def snapshot(self):
        with self.f.authority.database.connect() as db:
            return {t:[dict(r) for r in db.execute('SELECT * FROM '+t+' ORDER BY rowid')]
                    for t in ('wallets','wallet_ledger','gameplay_attempts','commands','staging_attempt_version117')}

    def test_atomic_reservation_retry_preserves_exact_version_across_active_change(self):
        value=self.bound.reserve(self.actor,self.request); ident=value['attempt']['attemptId']
        binding,worker=self.bound.worker_for_attempt(self.actor,ident)
        self.assertEqual((binding.approval_sha256,value['attempt']['configHash']),('b'*64,binding.level_sha256))
        self.assertIs(worker,self.new)
        old_active=StagingBoundAttempts(self.f.app.state.wallet,WorkerRegistry([self.old,self.new],self.old.approval_sha256))
        self.assertEqual(old_active.reserve(self.actor,self.request),value)
        self.assertIs(old_active.worker_for_attempt(self.actor,ident)[1],self.new)
        with self.f.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM staging_attempt_version117').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM gameplay_attempts WHERE id=?',(ident,)).fetchone()[0],1)
            with self.assertRaises(sqlite3.IntegrityError): db.execute('UPDATE staging_attempt_version117 SET approval_sha256=? WHERE attempt_id=?',('a'*64,ident))

    def test_fault_after_binding_rolls_back_attempt_binding_ledger_and_command(self):
        before=self.snapshot()
        def fail(stage): raise RuntimeError('simulated fault')
        self.bound.checkpoint=fail
        with self.assertRaisesRegex(RuntimeError,'simulated fault'): self.bound.reserve(self.actor,self.request)
        self.assertEqual(self.snapshot(),before)
        self.bound.checkpoint=None
        self.assertEqual(self.bound.reserve(self.actor,self.request)['attempt']['state'],'Reserved')

    def test_legacy_missing_version_and_foreign_attempt_fail_closed(self):
        with self.assertRaises(ServiceError) as e: self.bound.worker_for_attempt(self.f.authority.authenticate(self.f.identities[0]['token']),self.f.attempt)
        self.assertEqual(e.exception.code,'attempt_version_missing')
        value=self.bound.reserve(self.actor,self.request); ident=value['attempt']['attemptId']
        with self.assertRaises(ServiceError) as e: self.bound.worker_for_attempt(self.f.authority.authenticate(self.f.identities[0]['token']),ident)
        self.assertEqual(e.exception.code,'attempt_not_found')
        with self.f.authority.database.transaction() as db: db.execute('DELETE FROM staging_attempt_version117 WHERE attempt_id=?',(ident,))
        before=self.snapshot()
        with self.assertRaises(ServiceError) as e: self.bound.reserve(self.actor,self.request)
        self.assertEqual(e.exception.code,'attempt_version_missing'); self.assertEqual(before,self.snapshot())

    def test_absent_or_changed_worker_does_not_create_or_rebind_attempt(self):
        before=self.snapshot();self.new.approval_sha256='c'*64
        with self.assertRaises(ServiceError): self.bound.reserve(self.actor,self.request)
        self.assertEqual(before,self.snapshot())
        self.new.approval_sha256='b'*64
        value=self.bound.reserve(self.actor,self.request);ident=value['attempt']['attemptId']
        before=self.snapshot();self.new.enabled=False
        with self.assertRaises(ServiceError): self.bound.worker_for_attempt(self.actor,ident)
        self.assertEqual(before,self.snapshot())

    def test_same_manifest_routes_to_persisted_approval_after_active_change(self):
        first=self.bound.reserve(self.actor,self.request);attempt=first['attempt']['attemptId']
        binding,_=self.bound.worker_for_attempt(self.actor,attempt)
        changed=StagingBoundAttempts(self.f.app.state.wallet,WorkerRegistry([self.old,self.new],self.old.approval_sha256))
        job={'version':1,'level':binding.level,'initialMoves':binding.initial_moves,'seed':first['attempt']['seed'],
             'jobId':'1'*32,'playerId':self.actor.player,'attemptId':attempt,'pinsSHA256':binding.pins_sha256,
             'levelSHA256':binding.level_sha256,'startReceiptId':'wallet/'+'4'*64,'starting':[0,0,0,0],
             'actions':[],'receipts':[]}
        changed.execute_server_job(self.actor,attempt,job)
        self.assertEqual((len(self.old.calls),len(self.new.calls)),(0,1))
        bad=dict(job,playerId='f'*32)
        with self.assertRaises(ServiceError): changed.execute_server_job(self.actor,attempt,bad)
        bad=dict(job,levelSHA256='f'*64)
        with self.assertRaises(ReplayError): changed.execute_server_job(self.actor,attempt,bad)
        self.assertEqual((len(self.old.calls),len(self.new.calls)),(0,1))

    def test_reservation_bundle_checks_do_not_hold_sqlite_writer_lock(self):
        checked=[]
        for worker in (self.old,self.new):
            original=worker._verify_bundle
            def verify(original=original):
                with self.f.authority.database.transaction(timeout=.2) as db:
                    db.execute('UPDATE wallets SET revision=revision WHERE player_id=?',(self.actor.player,))
                checked.append(True)
                return original()
            worker._verify_bundle=verify
        self.assertEqual(self.bound.reserve(self.actor,self.request)['attempt']['state'],'Reserved')
        self.assertEqual(len(checked),2)

    def test_worker_binding_change_during_start_verification_cannot_spend_booster(self):
        request=ReserveAttempt(commandId=fixtures.ident(),expectedRevision=self.request.expectedRevision,level=1,starting=[1,0,0,0])
        value=self.bound.reserve(self.actor,request);ident=value['attempt']['attemptId']
        before=self.f.wallet(who=1);original=self.new._verify_bundle
        def replace_before_start():
            with self.f.authority.database.transaction() as db:
                row=db.execute('SELECT * FROM staging_attempt_version117 WHERE attempt_id=?',(ident,)).fetchone()
                db.execute('DELETE FROM staging_attempt_version117 WHERE attempt_id=?',(ident,))
                db.execute('INSERT INTO staging_attempt_version117 VALUES(?,?,?,?,?,?)',
                    (ident,self.old.approval_sha256,row['pins_sha256'],row['level'],row['level_sha256'],row['initial_moves']))
            return original()
        self.new._verify_bundle=replace_before_start
        with self.assertRaises(ServiceError) as error:
            self.bound.start(self.actor,ident,WalletCommand(commandId=fixtures.ident(),expectedRevision=before['revision']))
        self.assertEqual(error.exception.code,'attempt_configuration_mismatch')
        after=self.f.wallet(who=1)
        self.assertEqual(before['starting'],after['starting'])
        self.assertEqual(after['activeAttempt']['state'],'Reserved')

if __name__=='__main__': unittest.main()
