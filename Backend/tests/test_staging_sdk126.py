"""Real stopped staging15->125 continuity; synthetic SDK/ad observations only."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid
from urllib.request import Request, urlopen

from fastapi.testclient import TestClient

from hotr_backend import staging105 as staging
from hotr_backend import staging_sdk126 as sdk
from hotr_backend.api import create_app
from hotr_backend.operations import _validate
from hotr_backend.sdk_schema125 import validate_sdk_database
from hotr_backend.staging_empty_versioned_upgrade117 import _logical15
from hotr_backend.storage import Database

ROOT=Path(__file__).resolve().parents[2]
PACKAGE='com.heartoftherain.game'

class Fixture:
    def __init__(self, *, ads=True):
        self.temp=tempfile.TemporaryDirectory(prefix='hotr-same-wallet-sdk126-')
        self.root=Path(self.temp.name)
        self.now=int(time.time())
        self.manifest_path=self.root/'staging.json'
        self.document=dict(version=1,mode='staging',publicOrigin='https://sdk126.owned-fixture.net',
            identityScope='review-sdk126-existing-wallet',deploymentId='sdk126-owned-fixture',
            dataDirectory=str(self.root/'authority'),port=0,rewardedAdsEnabled=ads,
            vk=dict(enabled=False,clientId='',redirectUri=''),
            replay=dict(enabled=False,bundle='',approvalFile='',approvalSHA256=''))
        self.manifest_path.write_text(json.dumps(self.document))
        self.m=staging.read_manifest(self.manifest_path)
        staging.initialize_owned_data(self.m,restore_pending=True)
        self.path=self.m.data_directory/staging.DATABASE
        Database(self.path)
        staging.complete_restore(self.m)
        self.app=staging._construct(self.m,None)
        self.identity=self.app.state.authority.provision(lifetime=2_592_000)
        self.headers={'Authorization':'Bearer '+self.identity['token']}
        self.owner=(self.m.data_directory/staging.MARKER).read_bytes()
        self.ads_bytes=(self.m.data_directory/staging.ADS).read_bytes()
        self.sentinel=(self.m.data_directory/staging.COMMERCE).read_bytes()
        self.catalog=json.loads((ROOT/'Release/RuStore/commerce.example.json').read_text('utf-8-sig'))
        self.catalog.update(enabled=True,sandbox=True,verificationMode='sdk_client_reported',appId=2063777840)
        for product in self.catalog['products']:
            product['enabled']=True
        self.catalog_path=self.root/'sdk-catalog.json'
        self.save_catalog()

    def save_catalog(self):
        self.catalog_path.write_text(json.dumps(self.catalog),encoding='utf-8')

    def prepare(self, **changes):
        options=dict(confirm_sdk_client_reported=True)
        options.update(changes)
        return sdk.prepare_sdk_authority(self.m,self.catalog_path,PACKAGE,'sdk126',**options)

    def logical(self):
        with closing(sqlite3.connect(self.path)) as db:
            return _logical15(db)

    def report(self,order):
        return dict(invoiceId='987654321',purchaseId=str(uuid.uuid4()),orderId=order['orderId'],
            productId=order['sdk']['productId'],developerPayload=order['sdk']['developerPayload'],
            quantity=1,sandbox=True,status='CONFIRMED',purchaseType='ONE_STEP',
            acknowledgementState='PENDING',productType='CONSUMABLE_PRODUCT',
            amountMinor=order['amountMinor'],currency=order['currency'])

    def close(self):
        self.temp.cleanup()

class StagingSdk126Tests(unittest.TestCase):
    def fixture(self, **options):
        f=Fixture(**options)
        self.addCleanup(f.close)
        return f

    def test_01_preserves_same_database_actor_wallet_owner_ads_and_legacy_attempt_history(self):
        f=self.fixture()
        with TestClient(f.app) as client:
            before=client.get('/v1/wallet',headers=f.headers).json()
            attempt=client.post('/v1/attempts/reserve',headers=f.headers,json=dict(
                commandId=uuid.uuid4().hex,expectedRevision=before['revision'],level=1,starting=[0,0,0,0]))
            self.assertEqual(attempt.status_code,200)
        logical=f.logical()
        file_id=f.path.stat().st_ino
        result=f.prepare()
        self.assertEqual(result['toSchema'],125)
        self.assertEqual(f.logical(),logical)
        self.assertEqual(f.path.stat().st_ino,file_id)
        self.assertEqual((f.m.data_directory/staging.MARKER).read_bytes(),f.owner)
        self.assertEqual((f.m.data_directory/staging.ADS).read_bytes(),f.ads_bytes)
        self.assertEqual((f.m.data_directory/staging.COMMERCE).read_bytes(),f.sentinel)
        with sdk.application_context(f.m,clock=lambda:f.now) as app, TestClient(app) as client:
            response=client.get('/v1/wallet',headers=f.headers)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['playerId'],f.identity['playerId'])
            self.assertEqual(client.get('/healthz').json(),dict(status='ok',mode='staging',productionEnabled=False))
            self.assertEqual(client.get('/readyz').status_code,200)
            self.assertFalse(app.state.notifications.enabled)
            self.assertFalse(app.state.commerce.provider.configured)
            self.assertEqual(client.get('/v1/commerce/catalog',headers=f.headers).json()['appId'],2063777840)
        with self.assertRaises(staging.StagingError):
            staging.start(f.m)
        with self.assertRaises(RuntimeError):
            Database(f.path)

    def test_02_no_implicit_confirmation_production_catalog_or_unregistered_package(self):
        f=self.fixture()
        before=f.path.read_bytes()
        with self.assertRaises(staging.StagingError):
            f.prepare(confirm_sdk_client_reported=False)
        f.catalog['sandbox']=False
        f.save_catalog()
        with self.assertRaises(staging.StagingError):
            f.prepare()
        f.catalog['sandbox']=True
        f.save_catalog()
        with self.assertRaises(staging.StagingError):
            sdk.prepare_sdk_authority(f.m,f.catalog_path,'com.example.game','sdk126',
                confirm_sdk_client_reported=True)
        self.assertEqual(f.path.read_bytes(),before)
        self.assertEqual((f.m.data_directory/staging.MARKER).read_bytes(),f.owner)

    def test_03_running_runtime_lease_refuses_upgrade_before_snapshot(self):
        f=self.fixture()
        with staging._lock(f.m,staging.RUNTIME_LOCK):
            with self.assertRaises(staging.StagingError):
                f.prepare()
        self.assertFalse((f.m.data_directory/'backups/sdk126.sqlite3').exists())

    def test_04_interruption_boundaries_resume_exact_same_operation_without_data_loss(self):
        stages=('AfterBackupReady','AfterPendingMarker','AfterPolicyReady','BeforeCommit',
                'AfterCommit','AfterCompleteReceipt','AfterReadyMarker')
        for stage in stages:
            with self.subTest(stage=stage):
                f=self.fixture()
                before=f.logical()
                def fault(value):
                    if value==stage:
                        raise OSError('explicit_controlled_interruption')
                with patch.object(sdk,'_checkpoint',side_effect=fault):
                    with self.assertRaises(staging.StagingError):
                        f.prepare()
                self.assertEqual(f.logical(),before)
                f.prepare()
                self.assertEqual(f.logical(),before)
                self.assertEqual((f.m.data_directory/staging.MARKER).read_bytes(),f.owner)
                self.assertTrue(f.prepare()['alreadyCompleted'])
                sdk.require_sdk_ready(f.m)

    def test_05_pending_receipt_rejects_changed_catalog_and_foreign_owner(self):
        f=self.fixture()
        def fault(stage):
            if stage=='AfterCommit':
                raise OSError('explicit_interruption')
        with patch.object(sdk,'_checkpoint',side_effect=fault):
            self.assertRaises(staging.StagingError,f.prepare)
        f.catalog['version']='different-pending-input'
        f.save_catalog()
        self.assertRaises(staging.StagingError,f.prepare)
        self.assertRaises(staging.StagingError,sdk.require_sdk_ready,f.m)
        self.assertRaises(staging.StagingError,sdk.prepare_sdk_authority,
            replace(f.m,identity_scope='review-foreign'),f.catalog_path,PACKAGE,'sdk126',
            confirm_sdk_client_reported=True)

    def test_06_backup_tampering_blocks_resume_without_replacing_database(self):
        f=self.fixture()
        def fault(stage):
            if stage=='AfterBackupReady':
                raise OSError('explicit_interruption')
        with patch.object(sdk,'_checkpoint',side_effect=fault):
            self.assertRaises(staging.StagingError,f.prepare)
        (f.m.data_directory/'backups/sdk126.sqlite3').write_bytes(b'changed-private-test-backup')
        before=f.path.read_bytes()
        self.assertRaises(staging.StagingError,f.prepare)
        self.assertEqual(f.path.read_bytes(),before)

    def test_07_concurrent_payment_and_pending_ad_share_same_wallet_once_across_restart(self):
        f=self.fixture()
        with TestClient(f.app) as client:
            before=client.get('/v1/wallet',headers=f.headers).json()
            reserved=client.post('/v1/ads/rewarded/reserve',headers=f.headers,
                json=dict(commandId=uuid.uuid4().hex,placement='shop_rewarded'))
            self.assertEqual(reserved.status_code,200,reserved.text)
            opportunity=reserved.json()['opportunityId']
            completed=client.post('/v1/ads/rewarded/opportunities/'+opportunity+'/client-completion',
                headers=f.headers,json=dict(commandId=uuid.uuid4().hex))
            self.assertEqual(completed.status_code,200)
        f.prepare()
        claim_id=uuid.uuid4().hex
        with sdk.application_context(f.m,clock=lambda:f.now) as app, TestClient(app) as client:
            order=client.post('/v1/commerce/orders',headers=f.headers,json=dict(
                commandId=uuid.uuid4().hex,productId='wellkeeper')).json()
            observation=f.report(order)
            barrier=threading.Barrier(2)
            def payment():
                barrier.wait()
                return client.post('/v1/commerce/orders/'+order['orderId']+'/sdk-report',
                    headers=f.headers,json=observation)
            def reward():
                barrier.wait()
                return client.post('/v1/ads/rewarded/opportunities/'+opportunity+'/claim',
                    headers=f.headers,json=dict(commandId=claim_id))
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(payment),pool.submit(reward)]
                responses=[future.result() for future in futures]
            self.assertEqual([r.status_code for r in responses],[200,200])
            after=client.get('/v1/wallet',headers=f.headers).json()
            self.assertEqual(after['coins'],before['coins']+2000+400)
            self.assertEqual(after['starting'],[n+1 for n in before['starting']])
            self.assertEqual(after['tools'],[n+1 for n in before['tools']])
            self.assertEqual(after['revision'],before['revision']+2)
            for _ in range(3):
                self.assertEqual(client.post('/v1/commerce/orders/'+order['orderId']+'/sdk-report',
                    headers=f.headers,json=observation).status_code,200)
                self.assertEqual(client.post('/v1/ads/rewarded/opportunities/'+opportunity+'/claim',
                    headers=f.headers,json=dict(commandId=claim_id)).status_code,200)
            self.assertEqual(client.get('/v1/wallet',headers=f.headers).json(),after)
        with sdk.application_context(f.m,clock=lambda:f.now) as app, TestClient(app) as client:
            self.assertEqual(client.get('/v1/wallet',headers=f.headers).json(),after)
            self.assertEqual(client.post('/v1/commerce/orders/'+order['orderId']+'/sdk-report',
                headers=f.headers,json=observation).status_code,200)
            self.assertEqual(client.post('/v1/ads/rewarded/opportunities/'+opportunity+'/claim',
                headers=f.headers,json=dict(commandId=claim_id)).status_code,200)
            self.assertEqual(client.get('/v1/wallet',headers=f.headers).json(),after)
            with app.state.authority.database.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0],1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM rewards WHERE source='client_reported_ad'").fetchone()[0],1)

    def test_08_explicit_ad_disable_preserves_pending_claim_and_sdk_purchase_recovery(self):
        f=self.fixture()
        with TestClient(f.app) as client:
            before=client.get('/v1/wallet',headers=f.headers).json()
            opportunity=client.post('/v1/ads/rewarded/reserve',headers=f.headers,
                json=dict(commandId=uuid.uuid4().hex,placement='shop_rewarded')).json()['opportunityId']
            client.post('/v1/ads/rewarded/opportunities/'+opportunity+'/client-completion',
                headers=f.headers,json=dict(commandId=uuid.uuid4().hex))
        f.prepare()
        disabled=replace(f.m,rewarded_ads_enabled=False)
        staging.configure_rewarded_ads(disabled)
        with sdk.application_context(disabled,clock=lambda:f.now) as app, TestClient(app) as client:
            self.assertFalse(client.get('/v1/ads/rewarded/status',headers=f.headers).json()['enabled'])
            claimed=client.post('/v1/ads/rewarded/opportunities/'+opportunity+'/claim',
                headers=f.headers,json=dict(commandId=uuid.uuid4().hex))
            self.assertEqual(claimed.status_code,200)
            self.assertEqual(client.get('/v1/wallet',headers=f.headers).json()['coins'],before['coins']+400)
            self.assertEqual(client.post('/v1/ads/rewarded/reserve',headers=f.headers,
                json=dict(commandId=uuid.uuid4().hex,placement='shop_rewarded')).status_code,503)
            self.assertTrue(client.get('/v1/commerce/catalog',headers=f.headers).json()['enabled'])
        staging.configure_rewarded_ads(f.m)
        with sdk.application_context(f.m,clock=lambda:f.now) as app, TestClient(app) as client:
            status=client.get('/v1/ads/rewarded/status',headers=f.headers).json()
            self.assertTrue(status['enabled'])
            self.assertEqual(status['claimedToday'],1)
            self.assertEqual(status['remainingToday'],2)
            self.assertGreater(status['cooldownRemainingSeconds'],0)
            self.assertEqual(client.get('/v1/wallet',headers=f.headers).json()['coins'],before['coins']+400)

    def test_09_historical_api_orders_and_modes_are_retained_without_reinterpretation(self):
        f=self.fixture()
        from tests.test_commerce import FakeProvider
        old=f.root/'legacy-api.json'
        old.write_text(json.dumps(f.catalog|{'verificationMode':'provider_api'}))
        legacy=create_app(f.path,staging.CONFIG,commerce_config_path=old,commerce_provider=FakeProvider(),
                          ads_config_path=f.m.data_directory/staging.ADS)
        with TestClient(legacy) as client:
            order=client.post('/v1/commerce/orders',headers=f.headers,json=dict(
                commandId=uuid.uuid4().hex,productId='coins-1000')).json()
        before=f.logical()
        f.prepare()
        self.assertEqual(f.logical(),before)
        with sdk.application_context(f.m) as app,TestClient(app) as client:
            response=client.post('/v1/commerce/orders/'+order['orderId']+'/sdk-report',
                headers=f.headers,json=f.report(order))
            self.assertEqual(response.status_code,409)
            self.assertEqual(response.json()['error'],'purchase_verification_mode_mismatch')

    def test_10_policy_and_owned_socket_remain_fenced_after_close(self):
        f=self.fixture()
        f.prepare()
        with sdk.application_context(f.m) as app:
            permit=app.state.sdk_staging_permit126
            with self.assertRaises(staging.StagingError):
                with sdk.application_context(f.m):
                    pass
            public_copy=permit.policy
            public_copy['appId']=1
            self.assertEqual(permit.policy['appId'],2063777840)
        with TestClient(app) as client:
            self.assertEqual(client.get('/readyz').status_code,503)

    def test_11_private_api_permit_cannot_be_selected_by_boolean_or_environment(self):
        with self.assertRaises(RuntimeError):
            create_app(_staging_sdk_permit126=True)
        with patch.dict('os.environ',{'HOTR_BACKEND_MODE':'production'}):
            with self.assertRaises(RuntimeError):
                create_app()

    def test_12_existing_ads_flag_must_be_explicitly_configured_before_start(self):
        f=self.fixture(ads=False)
        f.prepare()
        enabled=replace(f.m,rewarded_ads_enabled=True)
        self.assertRaises(staging.StagingError,sdk.preflight,enabled)
        staging.configure_rewarded_ads(enabled)
        self.assertTrue(sdk.preflight(enabled)['adsEnabled'])
        self.assertEqual((f.m.data_directory/staging.MARKER).read_bytes(),f.owner)

    def test_13_shutdown_drains_financial_commit_before_releasing_runtime_owner(self):
        f=self.fixture()
        f.prepare()
        context=sdk.application_context(f.m,clock=lambda:f.now)
        app=context.__enter__()
        entered,release=threading.Event(),threading.Event()
        client=TestClient(app)
        try:
            order=client.post('/v1/commerce/orders',headers=f.headers,json=dict(
                commandId=uuid.uuid4().hex,productId='coins-1000')).json()
            observation=f.report(order)
            def hold(stage):
                if stage=='BeforeCreditCommit':
                    entered.set()
                    if not release.wait(10):
                        raise RuntimeError('controlled_test_wait_expired')
            app.state.commerce.checkpoint=hold
            with ThreadPoolExecutor(max_workers=2) as pool:
                committing=pool.submit(client.post,'/v1/commerce/orders/'+order['orderId']+'/sdk-report',
                    headers=f.headers,json=observation)
                try:
                    self.assertTrue(entered.wait(10))
                    closing=pool.submit(context.__exit__,None,None,None)
                    time.sleep(0.05)
                    self.assertFalse(closing.done())
                    with self.assertRaises(staging.StagingError):
                        with sdk.application_context(f.m):
                            pass
                finally:
                    release.set()
                self.assertEqual(committing.result(timeout=10).status_code,200)
                closing.result(timeout=10)
        finally:
            release.set()
            client.close()
            context.__exit__(None,None,None)
        with sdk.application_context(f.m,clock=lambda:f.now) as reopened,TestClient(reopened) as after:
            self.assertEqual(after.post('/v1/commerce/orders/'+order['orderId']+'/sdk-report',
                headers=f.headers,json=observation).status_code,200)
            with reopened.state.authority.database.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM commerce_credits').fetchone()[0],1)

    def test_14_actual_module_cli_public_catalog_tcp_restart_and_live_backup(self):
        f=self.fixture()
        environment=staging.child_environment(f.m,os.environ)
        environment['PYTHONPATH']=str(ROOT/'Backend')
        command=[sys.executable,'-B','-m','hotr_backend.staging_sdk126']
        public_catalog=ROOT/'Release/Monetization126/commerce.sandbox.json'
        prepared=subprocess.run(command+['prepare','--manifest',str(f.manifest_path),
            '--commerce-config',str(public_catalog),'--package-name',PACKAGE,'--name','real-cli',
            '--confirm-sdk-client-reported'],env=environment,capture_output=True,text=True,timeout=30)
        self.assertEqual(prepared.returncode,0,'Actual module CLI preparation failed')
        self.assertEqual(json.loads(prepared.stdout)['appId'],2063777840)
        checked=subprocess.run(command+['preflight','--manifest',str(f.manifest_path)],
            env=environment,capture_output=True,text=True,timeout=30)
        self.assertEqual(checked.returncode,0,'Actual module CLI preflight failed')
        processes=[]
        def launch():
            run=uuid.uuid4().hex
            process=subprocess.Popen(command+['start','--manifest',str(f.manifest_path),'--run-id',run],
                env=environment,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            processes.append(process)
            rendezvous=f.m.data_directory/('rendezvous-'+run+'.json')
            deadline=time.monotonic()+20
            while not rendezvous.is_file() and process.poll() is None and time.monotonic()<deadline:
                time.sleep(0.05)
            self.assertIsNone(process.poll(),'Actual module CLI exited before publishing owned listener')
            self.assertTrue(rendezvous.is_file(),'Actual module CLI did not publish owned listener')
            proof=json.loads(rendezvous.read_bytes())
            self.assertEqual(proof['nonce'],json.loads(f.owner)['nonce'])
            self.assertFalse(proof['productionEnabled'])
            return process,'http://127.0.0.1:'+str(proof['port'])
        def request(origin,path,body=None,authenticated=True):
            headers={'Content-Type':'application/json'}
            if authenticated:
                headers.update(f.headers)
            payload=None if body is None else json.dumps(body).encode('utf-8')
            with urlopen(Request(origin+path,data=payload,headers=headers),timeout=10) as response:
                self.assertEqual(response.status,200)
                return json.loads(response.read())
        try:
            first,origin=launch()
            self.assertEqual(request(origin,'/readyz',authenticated=False),{'status':'ready'})
            self.assertEqual(request(origin,'/healthz',authenticated=False)['mode'],'staging')
            before=request(origin,'/v1/wallet')
            order=request(origin,'/v1/commerce/orders',dict(commandId=uuid.uuid4().hex,productId='coins-1000'))
            observed=f.report(order)
            settled=request(origin,'/v1/commerce/orders/'+order['orderId']+'/sdk-report',observed)
            self.assertEqual(settled['verificationMode'],'sdk_client_reported')
            self.assertEqual(request(origin,'/v1/wallet')['coins'],before['coins']+1000)
            # Crash-style process stop: SQLite durability and OS lease release,
            # rather than an in-process context reopen, must preserve the grant.
            first.terminate()
            first.communicate(timeout=10)
            second,origin=launch()
            self.assertEqual(request(origin,'/readyz',authenticated=False),{'status':'ready'})
            replay=request(origin,'/v1/commerce/orders/'+order['orderId']+'/sdk-report',observed)
            self.assertEqual(replay['credit']['receiptId'],settled['credit']['receiptId'])
            self.assertEqual(request(origin,'/v1/wallet')['coins'],before['coins']+1000)
            copied=subprocess.run([sys.executable,'-B','-m','hotr_backend.staging_sdk_ops126','backup',
                '--manifest',str(f.manifest_path),'--name','real-cli-sdk125'],env=environment,
                capture_output=True,text=True,timeout=30)
            self.assertEqual(copied.returncode,0,'Actual SDK operations module CLI backup failed')
            receipt=json.loads((f.m.data_directory/'backups/real-cli-sdk125.receipt.json').read_bytes())
            self.assertEqual(receipt['kind'],'HeartOfTheRainStagingBackup105')
            self.assertEqual(receipt['schemaVersion'],125)
            self.assertEqual(receipt['nonce'],json.loads(f.owner)['nonce'])
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                process.communicate(timeout=10)

if __name__=='__main__':
    unittest.main()

