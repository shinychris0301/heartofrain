"""Actual local staging launcher rehearsal with two disposable managed guests.

The synthetic HTTPS origin is metadata only, never resolved or contacted. All
HTTP uses the retained 127.0.0.1 socket. Keys/tokens/bodies/databases stay private.
No Unity, APK, device, worker, hosted TLS or live provider is exercised.
"""
import argparse
import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
import traceback
import uuid

import httpx
from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS

ROOT=Path(__file__).resolve().parents[3]
BACKEND=ROOT/'Backend'
sys.path.insert(0,str(BACKEND))
sys.path.insert(0,str(BACKEND/'tools'))
from run_tests import source_hashes
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
from run_ads85_native import OwnedJob,freeze,sha,utc,write
sys.path.insert(0,str(ROOT/'Verification/Tools/Review93'))
from run_connected import resume_owned_primary,listener_closed


def bind(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def digest(value):return hashlib.sha256(value.encode('ascii')).hexdigest()


class DrillFailure(Exception):pass


class Drill:
    def __init__(self,tag):
        self.out=ROOT/'Verification/Evidence/Review105/TCP'/tag
        self.private=ROOT/'.verification-cache/Review105/TCP'/tag
        self.out.mkdir(parents=True,exist_ok=False);self.private.mkdir(parents=True,exist_ok=False)
        self.source_before=source_hashes();self.main_before=freeze()
        write(self.out/'MainSources_before.json',self.main_before)
        self.started=time.monotonic();self.started_utc=utc()
        self.checks=[];self.samples=[];self.processes=[];self.cli_runs=[];self.secret_values=[]
        self.process=self.job=self.http=None;self.server_stream=None;self.origin=None
        self.actual_handle=self.server_kernel=None
        self.run_id=uuid.uuid4().hex
        self.data=self.private/'Data'
        self.manifest=self.private/'Manifest.json'
        write(self.manifest,dict(version=1,mode='staging',publicOrigin='https://staging.hotr-native-fixture.net',
            identityScope='review-staging-native104',deploymentId='review105-'+self.run_id[:20],dataDirectory=str(self.data),port=0,
            vk=dict(enabled=False,clientId='',redirectUri=''),replay=dict(enabled=False,bundle='',approvalFile='',approvalSHA256='')))
        self.environment={key:value for key,value in os.environ.items() if not key.upper().startswith('HOTR_') and key.upper() not in ('PYTHONPATH','PYTHONHOME')}
        self.environment.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
        write(self.out/'Authorization.json',dict(schemaVersion=1,status='AUTHORIZED_OWNED_STAGING105_TCP',startedUtc=self.started_utc,
            harness=bind(Path(__file__)),manifest=bind(self.manifest),sourceSHA256=self.source_before,
            syntheticOriginAssignedOrOwned=False,appHttpLoopbackOnly=True,actualReplayWorker=False))

    def check(self,label,value):
        if not value:raise DrillFailure(label)
        self.checks.append(label)

    def phase(self,label):
        print(json.dumps(dict(status='PROGRESS_STAGING105_TCP',phase=label,checks=len(self.checks))),flush=True)

    def cli(self,module,args,label,script=None,expected_exit=0):
        log=self.private/('CLI_'+str(len(self.cli_runs)+1)+'.log')
        job=OwnedJob();process=None
        try:
            with log.open('xb') as stream:
                command=[sys.executable,'-B',str(script),*args] if script is not None else [sys.executable,'-B','-m',module,*args]
                process=subprocess.Popen(command,cwd=BACKEND,env=self.environment,
                    stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|0x4)
                job.assign(process.pid);resume_owned_primary(process);process.wait(timeout=90)
            reply=json.loads(log.read_text('utf-8-sig'))
            self.cli_runs.append(dict(label=label,exitCode=process.returncode,privateConsole=bind(log)))
            self.check(label+'_expected_exit',process.returncode==expected_exit)
            return reply
        finally:
            job.close()
            if process and process.poll() is None:process.kill();process.wait(timeout=15)

    def start(self,manifest,data,label):
        self.check('only_one_server_at_a_time',self.process is None)
        identifier=uuid.uuid4().hex;rendezvous=data/('rendezvous-'+identifier+'.json')
        self.check(label+'_fresh_rendezvous',not rendezvous.exists())
        self.job=OwnedJob();self.server_stream=(self.private/('Server'+str(len(self.processes)+1)+'.log')).open('xb')
        self.process=subprocess.Popen([sys.executable,'-B','-m','hotr_backend.staging105','start','--manifest',str(manifest),'--run-id',identifier],
            cwd=BACKEND,env=self.environment,stdin=subprocess.DEVNULL,stdout=self.server_stream,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW|0x4)
        self.job.assign(self.process.pid);resume_owned_primary(self.process)
        row=dict(label=label,ownedLauncherPid=self.process.pid,ownedJobAssignedBeforeResume=True,
                 scope='Owned process termination/restart; not physical power-loss acceptance.')
        self.processes.append(row)
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if self.process.poll() is not None:raise DrillFailure(label+'_server_exited_before_ready')
            if rendezvous.exists():
                proof=json.loads(rendezvous.read_text('utf-8-sig'))
                self.check(label+'_rendezvous_identity',proof['runId']==identifier and proof['host']=='127.0.0.1' and type(proof['port']) is int and 0<proof['port']<=65535)
                declared=json.loads(manifest.read_text('utf-8-sig'));owner_proof=json.loads((data/'.hotr-staging105-owner.json').read_text('utf-8-sig'))
                self.check(label+'_rendezvous_owned_root_binding',proof['deploymentId']==declared['deploymentId'] and proof['nonce']==owner_proof['nonce'])
                kernel=self.job.kernel
                kernel.IsProcessInJob.argtypes=(wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.BOOL))
                kernel.IsProcessInJob.restype=wintypes.BOOL
                kernel.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
                kernel.WaitForSingleObject.restype=wintypes.DWORD
                kernel.GetExitCodeProcess.argtypes=(wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD))
                kernel.GetExitCodeProcess.restype=wintypes.BOOL
                handle=kernel.OpenProcess(0x101000,False,proof['pid'])
                self.check(label+'_actual_pid_queryable',bool(handle))
                try:
                    member=wintypes.BOOL()
                    self.check(label+'_actual_pid_already_owned',bool(kernel.IsProcessInJob(handle,self.job.handle,ctypes.byref(member))) and bool(member.value))
                    self.actual_handle,self.server_kernel=handle,kernel;handle=None
                finally:
                    if handle:kernel.CloseHandle(handle)
                self.check(label+'_disabled_capabilities',proof['productionEnabled'] is False and proof['gameplayEnabled'] is False and proof['vkConfigured'] is False and proof['commerceEnabled'] is False and proof['adsEnabled'] is False and proof['providerAcceptanceVerified'] is False)
                self.origin='http://127.0.0.1:'+str(proof['port'])
                self.http=httpx.Client(base_url=self.origin,timeout=10,trust_env=False,follow_redirects=False)
                row.update(actualServerPid=proof['pid'],origin=self.origin,rendezvous=bind(rendezvous),gameplayAvailable=False)
                for _ in range(100):
                    try:
                        response=self.http.get('/readyz')
                        if response.status_code==200:
                            self.check(label+'_database_writer_ready',response.json()=={'status':'ready'})
                            health=self.request('GET','/healthz',label+'_health')
                            self.check(label+'_actual_staging_mode',health=={'status':'ok','mode':'staging','productionEnabled':False})
                            self.phase(label+'_ready');return
                    except httpx.HTTPError:pass
                    time.sleep(.05)
                raise DrillFailure(label+'_readiness_timeout')
            time.sleep(.05)
        raise DrillFailure(label+'_rendezvous_timeout')

    def stop(self):
        if self.http:self.http.close();self.http=None
        if self.process:
            process=self.process
            if self.job:self.job.close();self.job=None
            row=self.processes[-1]
            if self.actual_handle:
                began=time.monotonic();code=self.server_kernel.WaitForSingleObject(self.actual_handle,10000)
                row.update(actualServerWaitCode=code,actualServerTerminationObserved=code==0,
                           actualServerWaitSeconds=round(time.monotonic()-began,3))
                if code==0:
                    exit_code=wintypes.DWORD()
                    if self.server_kernel.GetExitCodeProcess(self.actual_handle,ctypes.byref(exit_code)):
                        row['actualServerExitCode']=exit_code.value
                    self.server_kernel.CloseHandle(self.actual_handle);self.actual_handle=None
                self.check(row['label']+'_actual_server_termination_observed',code==0)
            if process.poll() is None:process.wait(timeout=15)
            if self.server_stream:self.server_stream.close();self.server_stream=None
            row.update(exitCode=process.returncode,ownedProcessTerminated=True,
                terminationKind='Windows kill-on-close JobObject; crash-style process termination, not graceful shutdown.')
            if self.origin:
                began=time.monotonic();deadline=began+10;closed=False
                while time.monotonic()<deadline:
                    if listener_closed(self.origin):closed=True;break
                    time.sleep(.05)
                row.update(listenerClosed=closed,portClosureWaitSeconds=round(time.monotonic()-began,3))
                self.check(row['label']+'_owned_listener_closed',closed)
            row['privateServerLog']=bind(self.private/('Server'+str(len(self.processes))+'.log'))
            if 'rendezvous' in row:
                old=ROOT/row['rendezvous']['path']
                row['rendezvousRetainedAfterTermination']=old.exists()
                if old.exists():row['historicalRendezvousUnchanged']=bind(old)==row['rendezvous']
            self.process=None;self.origin=None

    def request(self,method,path,label,owner=None,body=None,status=200,discard_body=False):
        headers={'Authorization':'Bearer '+owner['accessToken']} if owner else {}
        started=time.monotonic()
        if discard_body:
            with self.http.stream(method,path,headers=headers,json=body) as response:
                code=response.status_code
                self.check(label+'_expected_status',code==status)
                value=None
        else:
            response=self.http.request(method,path,headers=headers,json=body);code=response.status_code
            self.check(label+'_expected_status',code==status);value=response.json()
            if isinstance(value,dict) and isinstance(value.get('accessToken'),str):self.secret_values.append(value['accessToken'])
        self.samples.append(dict(label=label,method=method,status=code,milliseconds=round((time.monotonic()-started)*1000,3),responseBodyDiscarded=discard_body))
        return value

    def signed_guest(self):
        owner=dict(key=ECC.generate(curve='P-256'),refresh=secrets.token_urlsafe(32),recovery=secrets.token_urlsafe(32))
        public=base64.b64encode(owner['key'].public_key().export_key(format='DER')).decode('ascii')
        body=dict(requestId=uuid.uuid4().hex,publicKey=public,refreshToken=owner['refresh'],recoverySecret=owner['recovery'])
        binding=dict(protocol='hotr-managed-identity-v1',purpose='guest',requestId=body['requestId'],publicKey=public,
                     refreshDigest=digest(owner['refresh']),recoveryDigest=digest(owner['recovery']))
        challenge=self.request('POST','/v1/identity/challenges','real_guest_challenge',body=dict(purpose='guest',requestId=body['requestId'],publicKey=public,payloadDigest=digest(canonical(binding))))
        expected='hotr-managed-identity-v1\n'+canonical({name:challenge[name] for name in ('challengeId','expiresAt','keyFingerprint','nonce','payloadDigest','purpose','requestId')})
        signing=base64.b64decode(challenge['signingBytes'],validate=True)
        self.check('real_guest_challenge_independently_bound',signing==expected.encode('ascii') and challenge['payloadDigest']==digest(canonical(binding))
            and challenge['purpose']=='guest' and challenge['requestId']==body['requestId']
            and challenge['keyFingerprint']==hashlib.sha256(base64.b64decode(public,validate=True)).hexdigest())
        body.update(challengeId=challenge['challengeId'],signature=base64.b64encode(DSS.new(owner['key'],'fips-186-3',encoding='der').sign(SHA256.new(signing))).decode('ascii'))
        self.secret_values.extend([owner['refresh'],owner['recovery'],public,body['signature'],challenge['signingBytes']])
        owner.update(self.request('POST','/v1/identity/guest','real_guest_enrollment',body=body));return owner

    @staticmethod
    def database(path):
        db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,isolation_level=None)
        db.execute('PRAGMA query_only=ON');return db

    def audit(self,path):
        db=self.database(path)
        try:
            self.check('sqlite_integrity_and_foreign_keys',db.execute('PRAGMA quick_check').fetchall()==[('ok',)] and not db.execute('PRAGMA foreign_key_check').fetchall())
            self.check('sqlite_current_schema10',db.execute('SELECT version FROM schema_info').fetchall()==[(10,)])
            financial={table:[tuple(row) for row in db.execute('SELECT * FROM '+table+' ORDER BY 1')] for table in ('wallets','wallet_ledger','rewards','gameplay_attempts','commerce_orders','commerce_credits')}
            self.check('two_real_players_only',db.execute('SELECT COUNT(*) FROM players').fetchone()[0]==2)
            self.check('one_genesis_each_no_social_reward',len(financial['wallets'])==2 and len(financial['wallet_ledger'])==2 and all(not financial[table] for table in ('rewards','gameplay_attempts','commerce_orders','commerce_credits')))
            return financial
        finally:db.close()

    def confirm_social(self,a,b,team,chat,financial,label,database):
        for index,owner in enumerate((a,b)):
            wallet=self.request('GET','/v1/wallet',label+'_wallet'+str(index),owner)
            self.check(label+'_wallet_genesis_preserved'+str(index),wallet['coins']==1250 and wallet['lives']==5 and wallet['playerId']==owner['playerId'])
        info=self.request('GET','/v1/teams/'+team,label+'_team',b)
        self.check(label+'_two_member_team',info['memberCount']==2 and info['isMember'] is True and info['ownerId']==a['playerId'])
        self.check(label+'_create_receipt_survives',self.request('POST','/v1/teams',label+'_exact_create_retry',a,self.create_body)['teamId']==team)
        self.check(label+'_join_receipt_survives',self.request('POST','/v1/teams/'+team+'/join',label+'_exact_join_retry',b,self.join_body)==self.join_result)
        result=self.request('POST','/v1/messages/Team/'+team,label+'_exact_chat_retry',a,chat)
        messages=self.request('GET','/v1/messages/Team/'+team,label+'_messages',b)['messages']
        self.check(label+'_one_message_after_exact_retry',len(messages)==1 and result['messageId']==messages[0]['messageId'])
        self.check(label+'_financial_rows_preserved',self.audit(database)==financial)
        return result['messageId']

    def run(self):
        from hotr_backend.staging105 import read_manifest,manifest_for_data_directory,manifest_mapping
        example=ROOT/'Release/RuStore/staging-server.example.json';example_before=bind(example)
        no_export=self.private/'InvalidExampleMustNotExport.json'
        refused=self.cli('hotr_backend.staging105',['export-app-config','--manifest',str(example),'--out',str(no_export)],'untouched_empty_example_export',expected_exit=1)
        self.check('empty_example_export_blocked_without_mutation',refused==dict(status='blocked_staging105',code='staging_owned_https_origin_required',productionEnabled=False) and not no_export.exists() and not self.data.exists() and bind(example)==example_before)
        self.phase('initialize_owned_data')
        initialized=self.cli('hotr_backend.staging105',['initialize','--manifest',str(self.manifest)],'initialize')
        self.check('initialize_marker_only',initialized['state']=='Initialized' and initialized['databaseCreated'] is False and not (self.data/'authority.sqlite3').exists())
        preflight=self.cli('hotr_backend.staging105',['preflight','--manifest',str(self.manifest)],'preflight_initialized')
        self.check('preflight_truthful_social_only_capabilities',preflight['status']=='staging_preflight_passed' and preflight['managedIdentityEnabled'] is True and preflight['socialEnabled'] is True and preflight['socialConfigured'] is True and all(preflight[key] is False for key in ('productionEnabled','gameplayConfigured','gameplayExecutionVerified','gameplayEnabled','vkConfigured','providerAcceptanceVerified','commerceEnabled','adsEnabled','notificationsEnabled','processStarted','networkContacted')) and not (self.data/'authority.sqlite3').exists())
        app_config=self.private/'AppConfiguration.json'
        exported=self.cli('hotr_backend.staging105',['export-app-config','--manifest',str(self.manifest),'--out',str(app_config)],'export_app_configuration')
        self.check('app_configuration_export_is_nonsecret_and_exact',exported['status']=='staging_app_configuration_exported' and json.loads(app_config.read_text('utf-8'))==dict(version=1,mode='ManagedGuestServer',origin='https://staging.hotr-native-fixture.net',identityScope='review-staging-native104',allowDevelopmentLoopback=False,socialEnabled=True))
        preparer=ROOT/'Verification/Tools/Review104/prepare_staging104.py';preparer_before=bind(preparer)
        candidates=ROOT/'.verification-cache/Review104/Candidates';candidates_before=sorted(path.name for path in candidates.iterdir()) if candidates.exists() else []
        accepted=self.cli(None,['--config',str(app_config)],'unchanged104_preparer_accepts_export_without_clone',script=preparer)
        self.check('actual104_preparer_export_compatibility_without_candidate',accepted['status']=='READY_FOR_EXPLICIT_PREPARATION104' and accepted['buildPerformed'] is False and accepted['networkContacted'] is False and bind(preparer)==preparer_before and (sorted(path.name for path in candidates.iterdir()) if candidates.exists() else [])==candidates_before)
        self.start(self.manifest,self.data,'original1')
        self.request('GET','/v1/wallet','unauthorized_wallet',status=401)
        a,b=self.signed_guest(),self.signed_guest()
        self.check('distinct_real_managed_players',a['playerId']!=b['playerId'])
        for owner in (a,b):self.request('GET','/v1/wallet','initial_wallet',owner)
        financial=self.audit(self.data/'authority.sqlite3')
        create=dict(commandId=uuid.uuid4().hex,name='Staging Rain 105',description='Disposable local verification')
        self.create_body=create
        team_result=self.request('POST','/v1/teams','create_team',a,create);team=team_result['teamId']
        self.check('create_exact_retry_same_team',self.request('POST','/v1/teams','create_team_retry',a,create)['teamId']==team)
        join=dict(commandId=uuid.uuid4().hex)
        joined=self.request('POST','/v1/teams/'+team+'/join','join_team',b,join)
        self.join_body,self.join_result=join,joined
        self.check('join_exact_retry_same_result',self.request('POST','/v1/teams/'+team+'/join','join_team_retry',b,join)==joined)
        keeper=self.database(self.data/'authority.sqlite3')
        try:
            keeper.execute('BEGIN');keeper.execute('SELECT version FROM schema_info').fetchone()
            chat=dict(commandId=uuid.uuid4().hex,text='Disposable staging chat 105')
            self.request('POST','/v1/messages/Team/'+team,'chat_committed_body_not_consumed',a,chat,discard_body=True)
            wal=Path(str(self.data/'authority.sqlite3')+'-wal')
            self.check('actual_committed_wal_present_at_backup',wal.is_file() and wal.stat().st_size>0)
            self.phase('live_wal_backup')
            backup=self.cli('hotr_backend.staging_ops105',['backup','--manifest',str(self.manifest),'--name','LiveWAL'],'live_backup')
            self.check('owned_live_backup_completed',backup['status']=='completed' and backup['operation']=='staging_backup' and backup['activationPerformed'] is False and backup['descriptorWritten'] is False)
        finally:keeper.close()
        snapshot=self.data/'backups/LiveWAL.sqlite3';receipt=self.data/'backups/LiveWAL.receipt.json'
        proof=json.loads(receipt.read_text('utf-8'))
        self.check('ready_snapshot_receipt_bound_to_bytes',proof['state']=='Ready' and proof['sha256']==sha(snapshot) and proof['bytes']==snapshot.stat().st_size)
        self.check('backup_financial_rows_exact',self.audit(snapshot)==financial)
        self.stop();self.start(self.manifest,self.data,'original_restart')
        message=self.confirm_social(a,b,team,chat,financial,'same_db_restart',self.data/'authority.sqlite3')
        self.stop();self.phase('restore_new_owned_root')
        restored=self.cli('hotr_backend.staging_ops105',['restore','--manifest',str(self.manifest),'--backup','LiveWAL','--tag','Restored01'],'restore')
        self.check('restore_never_auto_activates',restored['status']=='completed' and restored['activationPerformed'] is False and restored['descriptorWritten'] is False)
        restored_data=self.data/'restores/Restored01'
        restored_manifest=self.private/'RestoredManifest.json'
        write(restored_manifest,manifest_mapping(manifest_for_data_directory(read_manifest(self.manifest),restored_data)))
        self.check('restored_data_ready_before_manual_start',json.loads((restored_data/'.hotr-staging105-owner.json').read_text('utf-8'))['state']=='Ready')
        self.start(restored_manifest,restored_data,'restored_start')
        self.check('restored_receipt_replays_same_chat',self.confirm_social(a,b,team,chat,financial,'restored_db',restored_data/'authority.sqlite3')==message)
        self.stop()
        return dict(realManagedGuestEnrollments=2,teamCount=1,memberCount=2,messageCount=1,walletCoinsEach=1250,
            backup=backup,restore=restored,privateSnapshot=bind(snapshot),privateBackupReceipt=bind(receipt),
            deliberatelyDiscardedResponseBody=True,physicalNetworkLossInjected=False,actualWalPresentAtBackup=True,
            newRestoredDatabase=True,manualDescriptorAndStart=True,actualReplayWorker=False,gameplayAvailable=False,
            explicitAppConfigurationExport=bind(app_config),
            hostedHttpsVerified=False,fixtureOriginAssignedOrOwned=False,fixtureOriginResolvedOrContacted=False)

    def finish(self,status,details=None,failure=None):
        try:self.stop()
        except Exception:status='FAIL_STAGING105_TCP_CLEANUP';failure='owned_cleanup_failed'
        after=source_hashes();main_after=freeze()
        write(self.out/'MainSources_after.json',main_after)
        report=dict(schemaVersion=1,status=status,startedUtc=self.started_utc,finishedUtc=utc(),
            scope=__doc__.strip(),checks=len(self.checks),passed=self.checks,failureCode=failure,
            seconds=round(time.monotonic()-self.started,3),requests=self.samples,processes=self.processes,cliRuns=self.cli_runs,details=details,
            sourceSHA256=self.source_before,sourceSHA256After=after,backendInputsUnchanged=self.source_before==after,
            mainInputsUnchanged=self.main_before==main_after,unityOrDeviceAction=False,
            actualLiveProvider=False,productionApproved=False,fullyVetted=False)
        if self.source_before!=after or self.main_before!=main_after:report['status']='FAIL_STAGING105_TCP_SOURCE_CHANGED'
        encoded=json.dumps(report)
        if any(value and value in encoded for value in self.secret_values):raise DrillFailure('credential_export_prevented')
        write(self.out/'Report.json',report)
        print(json.dumps(dict(status=report['status'],checks=report['checks'],requests=len(self.samples),report=(self.out/'Report.json').relative_to(ROOT).as_posix())),flush=True)
        return 0 if report['status']=='PASS_STAGING105_TCP' else 1


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--tag',default='Flow01');args=p.parse_args()
    if not args.execute or os.name!='nt' or not args.tag.replace('_','').isalnum():p.error('Explicit fresh bounded Windows105 TCP rehearsal required')
    drill=Drill(args.tag)
    try:details=drill.run()
    except Exception as error:
        (drill.private/'Failure.log').write_text(traceback.format_exc(),encoding='utf-8')
        return drill.finish('FAIL_STAGING105_TCP',failure=str(error) if isinstance(error,DrillFailure) else 'unexpected_private_fixture_failure')
    return drill.finish('PASS_STAGING105_TCP',details)


if __name__=='__main__':raise SystemExit(main())
