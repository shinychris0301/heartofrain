# Controlled ASGI routing on owned schema16, with scripted workers only.
from contextlib import closing
import asyncio
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
import httpx
from hotr_backend import staging105 as staging
from hotr_backend import staging_empty_versioned_upgrade117 as upgrade
from hotr_backend.staging_versioned_runtime117 import open_versioned_application, fence_routes
from hotr_backend import staging_versioned_runtime117 as runtime
from hotr_backend.replay_versions117 import WorkerRegistry
from hotr_backend.storage import Database
from tests import test_staging105 as staging_fixture
from tests import test_replay_service as replay_fixture


def ident(): return uuid.uuid4().hex


class ScriptedVersionedWorker(replay_fixture.ScriptedWorker):
    def __init__(self, approval):
        super().__init__();self.approval_sha256=approval
    def run(self, job):
        proof=super().run(job);proof['approvalSHA256']=self.approval_sha256;return proof


class StagingVersionedRuntime117Tests(unittest.TestCase):
    def setUp(self):
        self.f=staging_fixture.Staging105Tests('test_initialize_and_preflight_are_database_free');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.m=self.f.ready();self.path=self.m.data_directory/staging.DATABASE
        upgrade.prepare_empty_authority(self.m,'runtime-empty',confirm_empty_history=True)
        raw=(Path(__file__).resolve().parents[1]/'config/levels.json').read_bytes();self.catalog=self.m.data_directory/'catalog.json';self.catalog.write_bytes(raw);self.digest=hashlib.sha256(raw).hexdigest()
        self.old,self.new=ScriptedVersionedWorker('a'*64),ScriptedVersionedWorker('b'*64)
    def open(self, active):
        return open_versioned_application(self.m,WorkerRegistry([self.old,self.new],active),self.catalog,self.digest,clock=lambda:100*86400)
    @staticmethod
    def request(client,method,path,token,body=None,status=200):
        response=client.request(method,path,headers={'Authorization':'Bearer '+token},json=body)
        if response.status_code!=status:raise AssertionError((response.status_code,response.text))
        return response.json()
    def reserve_start(self,app,client):
        user=app.state.authority.provision(lifetime=2_592_000);token=user['token'];wallet=self.request(client,'GET','/v1/wallet',token)
        payload={'commandId':ident(),'expectedRevision':wallet['revision'],'level':1,'starting':[0,0,0,0]}
        reserved=self.request(client,'POST','/v1/attempts/reserve',token,payload)
        attempt=reserved['attempt']['attemptId'];self.assertEqual(self.request(client,'POST','/v1/attempts/reserve',token,payload),reserved)
        start={'commandId':ident(),'expectedRevision':reserved['wallet']['revision']}
        self.request(client,'POST','/v1/attempts/'+attempt+'/start',token,start)
        return token,attempt

    def test_actual_routes_bind_new_attempts_and_preserve_old_worker_on_switch(self):
        with self.open(self.old.approval_sha256) as app:
            with TestClient(app,raise_server_exceptions=False) as client:
                token,attempt=self.reserve_start(app,client)
                body={'commandId':ident(),'expectedPrefixRevision':0,'actions':[{'index':0,'kind':'Swap','x':1,'y':1,'toX':1,'toY':2}]}
                result=self.request(client,'POST','/v1/gameplay/attempts/'+attempt+'/verify',token,body)
                self.assertEqual(result['state'],'Committed');self.assertEqual(len(self.old.calls),1);self.assertEqual(len(self.new.calls),0)
                with self.assertRaises(staging.StagingError):
                    with staging._lock(self.m,staging.RUNTIME_LOCK,allowed_states=(upgrade.PREPARED,)):pass
        with TestClient(app,raise_server_exceptions=False) as stale:
            self.assertEqual(stale.get('/v1/wallet',headers={'Authorization':'Bearer '+token}).status_code,503)
        # Simulate a changed new campaign while retaining the exact old
        # worker; the old attempt must continue against its original pins.
        changed=json.loads(self.catalog.read_bytes());new_hash='c'*64
        changed['levels'][0]['sourceSHA256']=new_hash;changed['levels'][0]['configHash']=new_hash
        self.new.pins['levels'][0]['sha256']=new_hash
        self.new.digest=hashlib.sha256(b'controlled-new-pins').hexdigest()
        data=json.dumps(changed,separators=(',',':')).encode();self.catalog.write_bytes(data);self.digest=hashlib.sha256(data).hexdigest()
        with self.open(self.new.approval_sha256) as app2:
            with TestClient(app2,raise_server_exceptions=False) as client2:
                recovered=self.request(client2,'GET','/v1/gameplay/attempts/'+attempt+'/operations/'+body['commandId'],token)
                self.assertEqual(recovered,result)
                again={'commandId':ident(),'expectedPrefixRevision':1,'actions':[{'index':1,'kind':'Swap','x':1,'y':1,'toX':1,'toY':2}]}
                self.assertEqual(self.request(client2,'POST','/v1/gameplay/attempts/'+attempt+'/verify',token,again)['state'],'Committed')
                token2,attempt2=self.reserve_start(app2,client2)
                body2={'commandId':ident(),'expectedPrefixRevision':0,'actions':[{'index':0,'kind':'Swap','x':1,'y':1,'toX':1,'toY':2}]}
                self.assertEqual(self.request(client2,'POST','/v1/gameplay/attempts/'+attempt2+'/verify',token2,body2)['state'],'Committed')
                self.assertEqual((len(self.old.calls),len(self.new.calls)),(2,1))
                with closing(sqlite3.connect(self.path)) as db:
                    values=dict(db.execute('SELECT attempt_id,approval_sha256 FROM staging_attempt_version117'))
                    self.assertEqual((values[attempt],values[attempt2]),('a'*64,'b'*64))
        with self.assertRaises(staging.StagingError):staging.preflight(self.m)
        with self.assertRaises(RuntimeError):Database(self.path)

    def test_unbound_attempt_cannot_start_runtime_or_be_assigned_a_worker(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO players(id,reward_totals,created_at) VALUES(?, '{}', 0)",('a'*32,))
            db.execute("INSERT INTO wallets(player_id,initialized,revision,balances) VALUES(?,1,0,'[]')",('a'*32,))
            db.execute("INSERT INTO gameplay_attempts(id,player_id,level,config_hash,seed,selected_json,moves,state,created_at,updated_at) VALUES(?,?,1,?,1,'[]',26,'Started',0,0)",('b'*32,'a'*32,'f'*64))
        with self.assertRaises(staging.StagingError) as error:
            with self.open(self.new.approval_sha256):pass
        self.assertEqual(error.exception.code,'versioned_preflight_unbound_attempts')
        with closing(sqlite3.connect(self.path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM staging_attempt_version117').fetchone()[0],0)

    def test_wrong_catalog_and_stopped_owner_conflicts_fail_before_app_creation(self):
        self.catalog.write_bytes(self.catalog.read_bytes()+b' ')
        with self.assertRaises(staging.StagingError) as error:
            with self.open(self.new.approval_sha256):pass
        self.assertEqual(error.exception.code,'versioned_preflight_catalog_mismatch')
        with closing(sqlite3.connect(self.path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM gameplay_attempts').fetchone()[0],0)

    def test_versioned_permit_cannot_bypass_rejected_production_mode(self):
        with patch.dict(os.environ,{'HOTR_BACKEND_MODE':'production'}):
            with self.assertRaises(RuntimeError):
                with self.open(self.new.approval_sha256):pass
        with closing(sqlite3.connect(self.path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM gameplay_attempts').fetchone()[0],0)

    def test_runtime_lock_is_held_until_inflight_replay_finishes(self):
        entered,release,closing_started=threading.Event(),threading.Event(),threading.Event()
        def block_worker(job):
            entered.set()
            if not release.wait(15):raise RuntimeError('test worker release timeout')
        self.old.observer=block_worker
        context=self.open(self.old.approval_sha256);app=context.__enter__()
        client=TestClient(app,raise_server_exceptions=False);client.__enter__()
        try:
            token,attempt=self.reserve_start(app,client)
            body={'commandId':ident(),'expectedPrefixRevision':0,'actions':[{'index':0,'kind':'Swap','x':1,'y':1,'toX':1,'toY':2}]}
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                running=pool.submit(self.request,client,'POST','/v1/gameplay/attempts/'+attempt+'/verify',token,body)
                self.assertTrue(entered.wait(10),'replay did not start')
                def close_context():
                    closing_started.set();context.__exit__(None,None,None)
                closing_task=pool.submit(close_context)
                self.assertTrue(closing_started.wait(10))
                try:
                    with self.assertRaises(staging.StagingError):
                        with staging._lock(self.m,staging.RUNTIME_LOCK,allowed_states=(upgrade.PREPARED,)):pass
                    self.assertFalse(closing_task.done(),'runtime ownership must outlive the running replay')
                finally:
                    release.set()
                self.assertEqual(running.result(timeout=15)['state'],'Committed')
                closing_task.result(timeout=15)
            self.assertEqual(client.get('/v1/wallet',headers={'Authorization':'Bearer '+token}).status_code,503)
        finally:
            release.set();client.__exit__(None,None,None)

    def test_pending_paid_operation_recovers_under_its_bound_worker_after_switch(self):
        with self.open(self.old.approval_sha256) as app:
            with TestClient(app,raise_server_exceptions=False) as client:
                token,attempt=self.reserve_start(app,client)
                wallet=self.request(client,'GET','/v1/wallet',token);self.old.fail=True
                body={'commandId':ident(),'expectedPrefixRevision':0,'expectedWalletRevision':wallet['revision'],
                      'actions':[{'index':0,'kind':'Swap','x':1,'y':1,'toX':1,'toY':2}],
                      'tool':1,'x':1,'y':1}
                pending=self.request(client,'POST','/v1/gameplay/attempts/'+attempt+'/tool',token,body,status=202)
                self.assertEqual(pending['state'],'Pending')
                self.assertEqual(self.request(client,'GET','/v1/wallet',token)['tools'],wallet['tools'])
        self.old.fail=False
        with self.open(self.new.approval_sha256) as app:
            with TestClient(app,raise_server_exceptions=False) as client:
                path='/v1/gameplay/attempts/'+attempt+'/operations/'+body['commandId']+'/resume'
                recovered=self.request(client,'POST',path,token,{})
                self.assertEqual(recovered['state'],'Committed')
                self.assertEqual(recovered['wallet']['tools'][1],wallet['tools'][1]-1)
                self.assertEqual(self.request(client,'POST',path,token,{}),recovered)
                self.assertEqual((len(self.old.calls),len(self.new.calls)),(2,0))

    def test_reserved_attempt_without_replay_row_keeps_original_worker(self):
        with self.open(self.old.approval_sha256) as app:
            with TestClient(app,raise_server_exceptions=False) as client:
                token=app.state.authority.provision(lifetime=2_592_000)['token']
                wallet=self.request(client,'GET','/v1/wallet',token)
                body={'commandId':ident(),'expectedRevision':wallet['revision'],'level':1,'starting':[0,0,0,0]}
                reserved=self.request(client,'POST','/v1/attempts/reserve',token,body)
                attempt=reserved['attempt']['attemptId']
                with closing(sqlite3.connect(self.path)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM replay_attempts').fetchone()[0],0)
        with self.open(self.new.approval_sha256) as app:
            with TestClient(app,raise_server_exceptions=False) as client:
                start={'commandId':ident(),'expectedRevision':reserved['wallet']['revision']}
                self.request(client,'POST','/v1/attempts/'+attempt+'/start',token,start)
                verify={'commandId':ident(),'expectedPrefixRevision':0,'actions':[{'index':0,'kind':'Swap','x':1,'y':1,'toX':1,'toY':2}]}
                self.assertEqual(self.request(client,'POST','/v1/gameplay/attempts/'+attempt+'/verify',token,verify)['state'],'Committed')
                self.assertEqual((len(self.old.calls),len(self.new.calls)),(1,0))

    def test_cancelled_asgi_replay_drains_worker_before_async_context_releases_lock(self):
        async def scenario():
            entered,release=threading.Event(),threading.Event()
            def block_worker(job):
                entered.set()
                if not release.wait(15):raise RuntimeError('test worker release timeout')
            self.old.observer=block_worker
            context=self.open(self.old.approval_sha256);app=await context.__aenter__()
            token=app.state.authority.provision(lifetime=2_592_000)['token']
            headers={'Authorization':'Bearer '+token}
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://local.test') as client:
                wallet=(await client.get('/v1/wallet',headers=headers)).json()
                reserved=(await client.post('/v1/attempts/reserve',headers=headers,json={'commandId':ident(),'expectedRevision':wallet['revision'],'level':1,'starting':[0,0,0,0]})).json()
                attempt=reserved['attempt']['attemptId']
                await client.post('/v1/attempts/'+attempt+'/start',headers=headers,json={'commandId':ident(),'expectedRevision':reserved['wallet']['revision']})
                body={'commandId':ident(),'expectedPrefixRevision':0,'actions':[{'index':0,'kind':'Swap','x':1,'y':1,'toX':1,'toY':2}]}
                request=asyncio.create_task(client.post('/v1/gameplay/attempts/'+attempt+'/verify',headers=headers,json=body))
                self.assertTrue(await asyncio.to_thread(entered.wait,10))
                request.cancel()
                shutdown=asyncio.create_task(context.__aexit__(None,None,None))
                try:
                    # Let cancellation and async shutdown progress on the loop.
                    await asyncio.sleep(.15)
                    self.assertFalse(shutdown.done(),'cancelled request must not release the lock while its worker executes')
                    with self.assertRaises(staging.StagingError):
                        with staging._lock(self.m,staging.RUNTIME_LOCK,allowed_states=(upgrade.PREPARED,)):pass
                    with closing(sqlite3.connect(self.path)) as db:
                        self.assertEqual(db.execute('SELECT state FROM replay_operations').fetchone()[0],'Running')
                finally:
                    release.set()
                try:await request
                except asyncio.CancelledError:pass
                await asyncio.wait_for(shutdown,15)
                with closing(sqlite3.connect(self.path)) as db:
                    self.assertEqual(db.execute('SELECT state FROM replay_operations').fetchone()[0],'Committed')
                self.assertTrue(context.closed.is_set())
                self.assertEqual((await client.get('/v1/wallet',headers=headers)).status_code,503)
        asyncio.run(scenario())

    def test_cancelled_entry_cleans_up_after_event_loop_has_closed(self):
        entered, release = threading.Event(), threading.Event()
        original = runtime.verify_prepared_authority
        def blocked(*args, **kwargs):
            entered.set()
            if not release.wait(15): raise RuntimeError('entry test release timeout')
            return original(*args, **kwargs)
        context = self.open(self.old.approval_sha256)
        async def cancel_entry():
            task = asyncio.create_task(context.__aenter__())
            self.assertTrue(await asyncio.to_thread(entered.wait, 10))
            task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
        with patch.object(runtime, 'verify_prepared_authority', side_effect=blocked):
            try:
                asyncio.run(cancel_entry())  # The loop closes before entry finishes.
                with self.assertRaises(staging.StagingError):
                    with staging._lock(self.m, staging.RUNTIME_LOCK, allowed_states=(upgrade.PREPARED,)): pass
            finally:
                release.set()
                self.assertTrue(context.closed.wait(15), 'cancelled entry leaked runtime ownership')
        self.assertIsNone(context.close_error)
        with staging._lock(self.m, staging.RUNTIME_LOCK, allowed_states=(upgrade.PREPARED,)): pass

    def test_route_fence_rejects_unknown_callable_and_async_handlers(self):
        from fastapi import Depends, FastAPI
        class Notification:
            def receive(self): pass
        class UnsafeDependency:
            def __call__(self): return 1
        app = FastAPI()
        @app.get('/unsafe-dependency')
        def endpoint(value=Depends(UnsafeDependency())): return value
        with self.assertRaisesRegex(RuntimeError, 'Unaudited callable'):
            fence_routes(app, object(), Notification())
        other = FastAPI()
        @other.get('/unsafe-async')
        async def async_endpoint(): return 1
        with self.assertRaisesRegex(RuntimeError, 'Unaudited async'):
            fence_routes(other, object(), Notification())
        replaced = FastAPI()
        @replaced.get('/v1/commerce/notifications/rustore/sandbox')
        async def replacement(): return 1
        async def previously_reviewed(): return 1
        with self.assertRaisesRegex(RuntimeError, 'Unaudited async'):
            fence_routes(replaced, object(), Notification(), ((
                '/v1/commerce/notifications/rustore/sandbox', previously_reviewed),))


if __name__ == '__main__':unittest.main()
