"""Root-only isolated Android Editor orchestration. Import/authoring runs nothing.

Preserves immutable runner02 and all prepared project bytes. The only settings
lease is two existing typed ADB lifecycle preferences, restored after the owned
Editor closes if they still have our exact temporary values. Never sends an
ADB lifecycle command to the shared5037 endpoint or controls a foreign process.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
RUNNER=HERE/'run_payment_diagnostics127_02.py'
RUNNER_SHA256='56e7ee24e04a436230c6c85802f5d623606ef1130972064a81213692dfdd2c96'
GUARDS=HERE/'adb_isolation_guards127.py'
GUARDS_SHA256='e47204a5c8de861969400d3d4441311d07db97899a1c8fb8e0e1d3b3c49b0987'
EDITOR=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Unity.exe')
ADB=EDITOR.parent/'Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe'
ADB_SHA256='b4a6b455702684652cccf7b46258b29e653538904359a58fd4931cf3ef286b3f'
HUB=Path('C:/Program Files/Unity Hub/resources/unity.exe')
PRIVATE_PORT=5039
SHARED_PORT=5037
PUBLIC=ROOT/'Verification/Evidence/Review127/Payments/Isolation'

def sha(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda:source.read(1048576),b''):result.update(block)
    return result.hexdigest()

def need(ok,code):
    if not ok:raise RuntimeError(code)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def durable_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as output:json.dump(value,output,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())

def exact(stream,count,deadline):
    result=bytearray()
    while len(result)<count:
        remaining=deadline-time.monotonic();need(remaining>0,'AdbHostProtocolDeadline127');stream.settimeout(remaining);chunk=stream.recv(count-len(result))
        need(bool(chunk),'AdbHostProtocolTruncated127');result.extend(chunk)
    return bytes(result)

def adb_query(port,service,connector=socket.create_connection):
    need(port in (SHARED_PORT,PRIVATE_PORT) and service in ('host:version','host:devices-l'),'ReadOnlyAdbHostServiceRequired127')
    need(port==PRIVATE_PORT or service=='host:version','SharedAdbVersionOnly127')
    request=service.encode('ascii')
    deadline=time.monotonic()+1.5
    with connector(('127.0.0.1',port),timeout=1.5) as peer:
        peer.settimeout(1.5);peer.sendall(('%04x'%len(request)).encode('ascii')+request)
        need(exact(peer,4,deadline)==b'OKAY','AdbReadOnlyHostRequestRejected127')
        size=exact(peer,4,deadline);need(re.fullmatch(rb'[0-9a-fA-F]{4}',size) is not None,'AdbHostLengthInvalid127');length=int(size,16);need(length<=4096,'AdbHostResponseBound127')
        body=exact(peer,length,deadline)
    if service=='host:version':need(re.fullmatch(rb'[0-9a-fA-F]{4}',body) is not None,'AdbVersionProtocolInvalid127')
    return body

def private_environment(nonce):
    need(re.fullmatch('[0-9a-f]{32}',nonce or '') is not None,'PreparedIsolationNonceRequired127')
    return {'ADB_SERVER_SOCKET':'tcp:127.0.0.1:5039','ANDROID_ADB_SERVER_ADDRESS':'127.0.0.1','ANDROID_ADB_SERVER_PORT':'5039',
            'ADB_USB':'0','ADB_EMU':'0','ADB_MDNS':'0','ADB_MDNS_AUTO_CONNECT':'0','ADB_LOCAL_TRANSPORT_MAX_PORT':'5554',
            'ANDROID_SERIAL':'HOTR_DIAGNOSTIC_NO_DEVICE_'+nonce,'ADB_VENDOR_KEYS':None,'ADB_TRACE':None,'ADB_MDNS_OPENSCREEN':None,'ADBHOST':None,'ADB_LOG_PATH':None,'ADB_TRACE_LOG':None}

class ChildEnvironment:
    def __init__(self,values):self.values=values;self.before={}
    def __enter__(self):
        for key,value in self.values.items():
            self.before[key]=(key in os.environ,os.environ.get(key))
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
        return self
    def __exit__(self,*unused):
        for key,(present,value) in self.before.items():
            if present:os.environ[key]=value
            else:os.environ.pop(key,None)

def editor_processes():
    script="@(Get-CimInstance Win32_Process -Filter \"Name='Unity.exe'\" | Select-Object ProcessId,ExecutablePath) | ConvertTo-Json -Compress"
    result=subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',script],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
    need(result.returncode==0,'ExclusiveEditorInventoryRequired127');items=json.loads(result.stdout.decode('utf-8-sig') or '[]');items=[] if items is None else [items] if type(items) is dict else items
    actual=[]
    for item in items:
        if Path(item.get('ExecutablePath') or '').resolve()==HUB.resolve():continue
        actual.append({'pid':int(item['ProcessId']),'imagePath':item.get('ExecutablePath') or ''})
    return actual

class Ownership:
    def __init__(self,job):self.job=job;self.lock=threading.RLock();self.editor=None;self.daemon=None;self.closed=False;self.processes=[]
    def add(self,process,kind):
        with self.lock:
            need(kind in ('editor','daemon'),'ExplicitOwnedProcessKindRequired127')
            self.processes.append((kind,process));previous=self.editor if kind=='editor' else self.daemon
            if previous is not None:
                if process.poll() is None:process.kill()
                raise RuntimeError('DuplicateOwnedProcessKindRejected127')
            if kind=='editor':self.editor=process
            else:self.daemon=process
            if self.closed:
                if process.poll() is None:process.kill()
                raise RuntimeError('OwnedIsolationJobAlreadyClosed127')
            try:self.job.assign(process.pid)
            except BaseException:
                if process.poll() is None:process.kill()
                raise
    def close(self):
        with self.lock:
            if not self.closed:self.closed=True;self.job.close()
    def editor_closed(self):return all(process.poll() is not None for kind,process in self.processes if kind=='editor')
    def all_stopped(self):return all(process.poll() is not None for kind,process in self.processes)

class RunnerProcessProxy:
    """Delegates process semantics; records/contains only the exact owned Editor."""
    def __init__(self,ownership):self.ownership=ownership
    def __getattr__(self,name):return getattr(subprocess,name)
    def Popen(self,command,*args,**kwargs):
        with self.ownership.lock:
            process=subprocess.Popen(command,*args,**kwargs)
            if isinstance(command,(tuple,list)) and command and Path(command[0]).resolve()==EDITOR.resolve():self.ownership.add(process,'editor')
        return process

def private_ready(guards,ownership,expected_version=None):
    need(ownership.daemon is not None and ownership.daemon.poll() is None,'OwnedPrivateAdbDaemonExited127')
    state=guards.capture_adb_listener(PRIVATE_PORT)
    need(state['process']['pid']==ownership.daemon.pid,'PrivateAdbListenerOwnershipChanged127')
    need(bool(state['listeners']) and all(value['address']=='127.0.0.1' and value['pid']==ownership.daemon.pid for value in state['listeners']),'PrivateAdbMustListenLoopbackOnly127')
    version=adb_query(PRIVATE_PORT,'host:version').decode('ascii').lower()
    if expected_version is not None:need(version==expected_version,'PrivateAdbProtocolChanged127')
    need(adb_query(PRIVATE_PORT,'host:devices-l')==b'','PrivateAdbHasDeviceTransports127')
    return state,version

def run(receipt_path,tag,build,layout,timeout,layout_report=None,layout_sha=None):
    need(os.name=='nt' and re.fullmatch('[A-Za-z0-9_]{1,30}',tag or '') and 60<=timeout<=3600 and not (build and layout),'BoundedRootOnlyIsolationInvocationRequired127')
    need(sha(RUNNER)==RUNNER_SHA256 and re.fullmatch('[0-9a-f]{64}',GUARDS_SHA256 or '') and sha(GUARDS)==GUARDS_SHA256,'FrozenIndependentIsolationSourcesRequired127')
    runner=load('immutable_native_runner02_127',RUNNER);guards=load('frozen_adb_guards127',GUARDS)
    receipt_path=receipt_path.resolve();receipt=json.loads(receipt_path.read_text('utf-8'));project=Path(receipt['project']).resolve()
    need(project.is_relative_to(Path('E:/.verification-cache/HOTR127').resolve()) and receipt_path.parent==project.parent and receipt.get('nativeRunnerSHA256')==RUNNER_SHA256,'FrozenPrivateIsolationProjectRequired127')
    need(receipt.get('status')=='PREPARED_PAYMENT_DIAGNOSTIC127' and receipt.get('versionCode')==127 and receipt.get('packageName')=='com.heartoftherain.game','ExactPreparedDiagnosticBindingRequired127')
    need(not (runner.PUBLIC/tag).exists(),'PreserveUnderlyingNativeAttempt127');values=private_environment(receipt['nonce'])
    for relative,digest in runner.source_pin_pairs(receipt):need(sha(runner.asset_path(project,relative))==digest,'PreparedIsolationSourceChanged127')
    if not layout:runner.accepted_layout(layout_report,layout_sha,project)
    need(not editor_processes(),'ForeignEditorBlocksPreferenceLease127')
    shared_before=guards.capture_adb_listener(SHARED_PORT);need(not guards.capture_adb_listener(PRIVATE_PORT,allow_absent=True)['listeners'],'FreshPrivateAdbPort5039Required127')
    need(ADB.is_file() and sha(ADB)==ADB_SHA256,'ExactStockPrivateAdbBinaryRequired127')
    binary=ADB.read_bytes()
    for token in (b'--one-device',b'ADB_SERVER_SOCKET',b'ADB_USB',b'ADB_EMU',b'ADB_MDNS',b'ADB_MDNS_AUTO_CONNECT',b'ADB_LOCAL_TRANSPORT_MAX_PORT'):need(token+b'\x00' in binary,'InstalledAdbIsolationOptionMissing127')
    signing=load('private_capture_directory127',ROOT/'Release/Signing/manage_release_signing.py');raw=project.parent/'ADBIsolation'/tag;signing.private_directory(raw)
    public=PUBLIC/tag;need(not public.exists(),'PreserveIsolationAttemptEvidence127');public.mkdir(parents=True)
    record={'version':1,'status':'RUNNING_ISOLATED_NATIVE127','startedUtc':datetime.now(timezone.utc).isoformat(),'wrapperSHA256':sha(__file__),'guardsSHA256':GUARDS_SHA256,'runnerSHA256':RUNNER_SHA256,'preparationSHA256':sha(receipt_path),'privateAdbSHA256':sha(ADB),'privatePort':PRIVATE_PORT,'sharedBefore':shared_before,'buildRequested':build,'layoutRequested':layout,'deviceTransportPolicy':'Explicit ADB_USB=0 and ADB_EMU=0 prevent USB/scanner initialization; nonmatching USB filter and max5554 are additional defenses. ADB_MDNS=0 and automatic-connect=0; zero private device transports required before and throughout. No device actions.','adbAuthentication':'Root explicitly authorized ordinary stock SDK ADB default Windows host-key loading. No key contents inspected/exported; no private auth-home isolation claimed. Inherited ADB_VENDOR_KEYS cleared.','nativeResult':None,'deviceOrProviderActionsByWrapper':False}
    sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'));from run_ads85_native import OwnedJob
    ownership=Ownership(OwnedJob());stop=threading.Event();violation=threading.Event();watch=None;watch_started=False;lease=None;lease_entered=False;capture=None;started=time.monotonic()
    def checkpoint(captured):durable_json(raw/'PreferenceBefore127.json',{'ownerPid':os.getpid(),'preparedUtc':datetime.now(timezone.utc).isoformat(),'registryBefore':captured,'sharedBefore':shared_before,'wrapperSHA256':sha(__file__)})
    def closed_for_restore():return ownership.editor_closed() and not editor_processes()
    def observe_private(version):
        while not stop.wait(1):
            try:
                private_ready(guards,ownership,version)
                record['zeroTransportGuardSamples']=record.get('zeroTransportGuardSamples',0)+1
                with ownership.lock:other=[item for item in editor_processes() if ownership.editor is None or item['pid']!=ownership.editor.pid]
                need(not other,'ForeignEditorAppearedDuringIsolation127')
            except BaseException as failure:
                record['guardFailureType']=type(failure).__name__;record['guardFailureCode']=str(failure) if re.fullmatch('[A-Za-z0-9_]{1,120}',str(failure)) else 'PrivateIsolationGuardFailed127';violation.set();ownership.close();return
    try:
        lease=guards.EditorPrefsLease(editor_closed=closed_for_restore,checkpoint=checkpoint);lease.__enter__();lease_entered=True
        need(not editor_processes(),'ForeignEditorAppearedBeforeLaunch127')
        with ChildEnvironment(values):
            capture=(raw/'PrivateAdb.log').open('xb')
            command=[str(ADB),'-L','tcp:127.0.0.1:5039','--one-device',values['ANDROID_SERIAL'],'server','nodaemon']
            daemon_env={key:value for key,value in os.environ.items() if not key.upper().startswith('HOTR_') and not re.search('KEYSTORE|KEYALIAS|STOREPASS|KEYPASS',key,re.I)}
            daemon=subprocess.Popen(command,cwd=raw,env=daemon_env,stdin=subprocess.DEVNULL,stdout=capture,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);ownership.add(daemon,'daemon');record['privateAdbPid']=daemon.pid
            ready=None;deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                need(daemon.poll() is None,'OwnedPrivateAdbBootstrapExited127')
                try:ready=private_ready(guards,ownership);break
                except OSError:time.sleep(.2)
                except RuntimeError as failure:
                    if str(failure) in ('RequiredAdbListenerAbsent127','AdbVersionProbeUnavailable127'):time.sleep(.2)
                    else:raise
            need(ready is not None,'PrivateAdbBootstrapNotQualified127');record['privateBefore']=ready[0];record['privateProtocolVersion']=ready[1];record['zeroTransportsBefore']=True
            watch=threading.Thread(target=observe_private,args=(ready[1],),name='OwnedPrivateAdbGuard127',daemon=True);watch.start();watch_started=True
            runner.subprocess=RunnerProcessProxy(ownership)
            record['nativeResult']=runner.run(receipt_path,tag,build,layout,timeout,layout_report,layout_sha)
            need(not violation.is_set(),'PrivateAdbGuardRejectedNativeRun127');after_private=private_ready(guards,ownership,ready[1]);record['privateAfter']=after_private[0];record['zeroTransportsAfter']=True
    except BaseException as failure:
        record['errorType']=type(failure).__name__;record['errorCode']=str(failure) if re.fullmatch('[A-Za-z0-9_]{1,120}',str(failure)) else 'IsolatedNativeInvocationFailed127'
    finally:
        stop.set()
        if watch_started:
            try:watch.join(timeout=20)
            except BaseException as failure:record['guardJoinFailureType']=type(failure).__name__
        if watch and watch.is_alive():record['guardThreadFailedToStop']=True
        try:ownership.close()
        except BaseException as failure:record['ownedJobCloseFailureType']=type(failure).__name__
        for kind,process in ownership.processes:
            if process.poll() is None:
                try:process.wait(timeout=15)
                except BaseException as failure:record['ownedProcessClosureFailed']=True;record['ownedProcessClosureFailureType']=type(failure).__name__
        if capture:
            try:capture.close()
            except BaseException as failure:record['privateCaptureCloseFailureType']=type(failure).__name__
        record['ownedProcessesStopped']=ownership.all_stopped()
        if lease_entered:
            try:lease.__exit__(None,None,None);record['preferenceLease']=lease.report
            except BaseException as failure:record['preferenceRestoreFailureType']=type(failure).__name__;record['preferenceLease']=lease.report
        elif lease is not None:record['preferenceLease']=lease.report
        try:
            shared_after=guards.capture_adb_listener(SHARED_PORT);record['sharedAfter']=shared_after;guards.require_same_listener(shared_before,shared_after);record['shared5037Unchanged']=True
        except BaseException as failure:record['shared5037Unchanged']=False;record['sharedPreservationFailureType']=type(failure).__name__
        record['privateDaemonLogSHA256']=sha(raw/'PrivateAdb.log') if (raw/'PrivateAdb.log').exists() else None;record['privateDaemonLogPubliclyCopied']=False
        record['elapsedSeconds']=round(time.monotonic()-started,3);record['finishedUtc']=datetime.now(timezone.utc).isoformat()
        restored=bool(record.get('preferenceLease',{}).get('restored'))
        passed=record.get('nativeResult',{}).get('status')=='PASS_PAYMENT_DIAGNOSTIC127_NATIVE' if type(record.get('nativeResult')) is dict else False
        clean=not any(key in record for key in ('errorType','guardThreadFailedToStop','guardJoinFailureType','ownedJobCloseFailureType','ownedProcessClosureFailed','preferenceRestoreFailureType'))
        record['status']='PASS_ISOLATED_NATIVE127' if passed and clean and not violation.is_set() and record.get('zeroTransportsBefore') is True and record.get('zeroTransportsAfter') is True and record['ownedProcessesStopped'] and record.get('shared5037Unchanged') is True and restored else 'FAIL_ISOLATED_NATIVE127'
        durable_json(public/'Isolation.json',record)
    need(record['status']=='PASS_ISOLATED_NATIVE127','IsolatedNativeQualificationFailed127')
    return {'status':record['status'],'receipt':str((public/'Isolation.json').relative_to(ROOT)),'receiptSHA256':sha(public/'Isolation.json'),'nativeResult':record['nativeResult']}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--receipt',type=Path,required=True);parser.add_argument('--tag',required=True);group=parser.add_mutually_exclusive_group();group.add_argument('--layout',action='store_true');group.add_argument('--build',action='store_true');parser.add_argument('--timeout',type=int,default=2400);parser.add_argument('--layout-report',type=Path);parser.add_argument('--layout-report-sha256');args=parser.parse_args()
    return run(args.receipt,args.tag,args.build,args.layout,args.timeout,args.layout_report,args.layout_report_sha256)

if __name__=='__main__':
    try:print(json.dumps(main()))
    except Exception as failure:
        code=str(failure);print(json.dumps({'status':'BLOCKED_ISOLATED_NATIVE127','code':code if re.fullmatch('[A-Za-z0-9_]{1,120}',code) else type(failure).__name__}));raise SystemExit(1)
