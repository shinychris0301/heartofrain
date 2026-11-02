"""Run one pinned replay in a fresh directory, never an authority/database."""
import argparse
import copy
import ctypes
from ctypes import wintypes
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from package_worker126 import PackageError,collect,need,parse,plain,sha,APPROVAL_SHA256

CONTRACT_SHA='ddf09336d8cc79ea82c6ad81bdcc6253e52fb903703d994c0f38564e0cfc44e3'
JOB_SHA='1bab7436c3c114468361058e0847083babddbe282be5eefd7ff54f922eb8a567'
EXPECTED_SHA='0c37042cfb8eb85b7a17db4a598257d8a131c9682624714bdc73502245dcefdb'
CATALOG_SHA='af6579bcca42fb6f85dbd8c1e8dc8450cfd24fe7ae39d6f3675098f96063dd84'
PINS_SHA='f3603ca53ebe070610473bd18524cc4765a85b368dfeb2f8518d987ec933d70f'
MARKERS=('.hotr-staging105-owner.json','.hotr-production122-owner.json',
         '.hotr-production122-restore-quarantine.json','.hotr-staging126-restore-quarantine.json')

def isolated(path,*,fresh=False):
    plain(path)
    need(path.is_absolute(),'absolute_qualification_path_required')
    need(not any((parent/name).exists() for parent in (path,*path.parents)
                 for name in MARKERS),'qualification_authority_directory_rejected')
    if fresh:
        need(not os.path.lexists(path) and path.parent.is_dir(),'fresh_qualification_directory_required')
    return path

def local_service():
    """Read the actual Windows process token, not environment user-name text."""
    need(os.name=='nt','windows_required')
    advapi=ctypes.WinDLL('advapi32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    advapi.OpenProcessToken.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)]
    advapi.OpenProcessToken.restype=wintypes.BOOL
    advapi.GetTokenInformation.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,
                                      wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    advapi.GetTokenInformation.restype=wintypes.BOOL
    advapi.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(wintypes.LPWSTR)]
    advapi.ConvertSidToStringSidW.restype=wintypes.BOOL
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    kernel.LocalFree.restype=ctypes.c_void_p
    token=wintypes.HANDLE()
    sid_text=wintypes.LPWSTR()
    need(bool(advapi.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token))),
         'windows_token_unavailable')
    try:
        size=wintypes.DWORD()
        advapi.GetTokenInformation(token,1,None,0,ctypes.byref(size))
        need(0<size.value<=65536,'windows_token_unavailable')
        buffer=ctypes.create_string_buffer(size.value)
        need(bool(advapi.GetTokenInformation(token,1,buffer,size.value,ctypes.byref(size))),
             'windows_token_unavailable')
        # TOKEN_USER begins with SID_AND_ATTRIBUTES, whose first member is PSID.
        sid=ctypes.cast(buffer,ctypes.POINTER(ctypes.c_void_p)).contents.value
        need(bool(advapi.ConvertSidToStringSidW(sid,ctypes.byref(sid_text))),
             'windows_token_unavailable')
        return sid_text.value=='S-1-5-19'
    finally:
        if sid_text:
            kernel.LocalFree(ctypes.cast(sid_text,ctypes.c_void_p))
        kernel.CloseHandle(token)

def memory_status():
    class MemoryStatus(ctypes.Structure):
        _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD),
            *[(name,ctypes.c_ulonglong) for name in ('totalPhysical','availablePhysical',
              'totalCommit','availableCommit','totalVirtual','availableVirtual','availableExtendedVirtual')]]
    status=MemoryStatus();status.length=ctypes.sizeof(status)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GlobalMemoryStatusEx.argtypes=[ctypes.POINTER(MemoryStatus)]
    kernel.GlobalMemoryStatusEx.restype=wintypes.BOOL
    need(bool(kernel.GlobalMemoryStatusEx(ctypes.byref(status))),'memory_status_unavailable')
    return {'totalPhysicalBytes':status.totalPhysical,'availablePhysicalBytes':status.availablePhysical,
            'availableCommitBytes':status.availableCommit,'memoryLoadPercent':status.load}

def enough_memory(snapshot):
    return snapshot['availablePhysicalBytes']>=134217728 and snapshot['availableCommitBytes']>=536870912

def load_contract(backend):
    plain(backend)
    source=backend/'hotr_backend/replay_contract.py'
    plain(source)
    need(sha(source.read_bytes())==CONTRACT_SHA,'tested_replay_contract_hash_mismatch')
    # Direct loading avoids executing an unreviewed package __init__ or imports.
    spec=importlib.util.spec_from_file_location('hotr_qualification_replay126',source)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def check_fixtures(job_path,expected_path,contract):
    plain(job_path);plain(expected_path)
    raw=job_path.read_bytes();expected_raw=expected_path.read_bytes()
    need(sha(raw)==JOB_SHA and sha(expected_raw)==EXPECTED_SHA,'native_fixture_hash_mismatch')
    job=contract.strict_json(raw)
    expected=contract.validate_output(expected_raw,job,raw)
    need(job['level']==1 and len(job['actions'])==1 and not job['receipts']
         and job['pinsSHA256']==PINS_SHA,'native_fixture_scope_mismatch')
    return job,expected

def check_result(proof,expected,job,contract):
    process=proof['process']
    canonical=sha(contract.encode_job(job))
    need(proof['approvalSHA256']==APPROVAL_SHA256 and proof['jobSHA256']==canonical,
         'replay_proof_binding_mismatch')
    need(proof['result']['jobSHA256']==canonical,'replay_canonical_job_mismatch')
    actual=copy.deepcopy(proof['result']);native=copy.deepcopy(expected)
    # Native and server canonical JSON formatting differ; both bind their bytes.
    actual.pop('jobSHA256');native.pop('jobSHA256')
    need(actual==native,'native_checkpoint_or_outcome_mismatch')
    need(process['jobObjectEnforced'] is True and process['namedMutexEnforced'] is True
         and process['exitCode']==0 and process['wallLimitSeconds']==60
         and process['memoryLimitBytes']==268435456 and process['processLimit']==2,
         'replay_os_limits_unproven')

def timeout_control(contract,directory):
    executable=Path(sys._base_executable).resolve(strict=True)
    plain(executable)
    started=time.monotonic()
    try:
        contract._run_windows_bounded(executable,
            ['-I','-B','-c','import time; time.sleep(30)'],directory,1,134217728,1)
    except contract.ReplayError as exc:
        need(str(exc)=='replay_process_timeout','timeout_control_unexpected_error')
        elapsed=time.monotonic()-started
        need(elapsed<15,'timeout_control_termination_unbounded')
        return {'status':'PASS_WINDOWS_JOB_TIMEOUT_CONTROL','wallLimitSeconds':1,
                'memoryLimitBytes':134217728,'processLimit':1,
                'observedSeconds':round(elapsed,3),'trustedPythonBaseSHA256':sha(executable.read_bytes()),
                'scope':'Trusted Python sleeping child tests existing Windows JobObject timeout; not a second Unity/model replay.'}
    raise PackageError('timeout_control_failed_to_terminate')

def qualify(backend,bundle,approval,job_path,expected_path,out,require_localservice):
    need(os.name=='nt','windows_required')
    isolated(out,fresh=True)
    isolated(bundle);isolated(approval)
    need(not out.is_relative_to(bundle) and not bundle.is_relative_to(out),
         'qualification_worker_overlap_rejected')
    is_localservice=local_service()
    need(not require_localservice or is_localservice,'localservice_execution_required')
    contract=load_contract(backend)
    _,_,source_entries,_=collect(bundle,approval)
    catalog=backend/'config/levels.json'
    plain(catalog)
    need(sha(catalog.read_bytes())==CATALOG_SHA,'tested_level_catalog_hash_mismatch')
    job,expected=check_fixtures(job_path,expected_path,contract)
    out.mkdir(mode=0o700)
    marker={'version':1,'kind':'HeartOfTheRainIsolatedWorkerSmoke126','state':'Pending',
            'productionEnabled':False,'authorityCreated':False}
    marker_path=out/'.hotr-isolated-worker-smoke126.json'
    marker_path.write_text(json.dumps(marker,sort_keys=True)+'\n',encoding='utf-8')
    jobs=out/'Jobs';jobs.mkdir(mode=0o700)
    worker=contract.ApprovedWorker(bundle,approval,APPROVAL_SHA256,jobs,enabled=True,
                                   timeout_seconds=60,memory_bytes=268435456,process_limit=2)
    # Verify the exact all50 catalogue binding, without replaying all50 levels.
    _,pins,pins_hash=worker._verify_bundle()
    levels=parse(catalog.read_bytes())['levels']
    need(len(levels)==len(pins['levels'])==50 and pins_hash==PINS_SHA,
         'worker_catalog_pin_count_mismatch')
    for level,pin in zip(levels,pins['levels'],strict=True):
        need(level['level']==pin['level'] and level['sourceSHA256']==level['configHash']==pin['sha256']
             and level['moves']==pin['moves'],'worker_catalog_binding_mismatch')
    before={entry.name for entry in jobs.iterdir()}
    invalid=copy.deepcopy(job)
    invalid['levelSHA256']='0'*64
    try:
        worker.run(invalid)
    except contract.ReplayError as exc:
        need(str(exc)=='job_pin_mismatch','negative_pin_control_unexpected_error')
    else:
        raise PackageError('negative_pin_control_not_rejected')
    need(before=={entry.name for entry in jobs.iterdir()},'negative_pin_control_started_job')
    memory_before=memory_status()
    if not enough_memory(memory_before):
        blocked={'status':'BLOCKED_LOW_HEADROOM_WORKER_SMOKE126','actualUnityReplays':0,
                 'executionAccountIsLocalService':is_localservice,'memoryBefore':memory_before,
                 'memoryAfter':memory_status(),'qualifiedForLocalService':False,
                 'minimumAvailablePhysicalBytes':134217728,'minimumAvailableCommitBytes':536870912,
                 'productionEnabled':False,'authorityCreated':False,'liveGameplayConfigured':False}
        (out/'WorkerSmoke126.json').write_text(json.dumps(blocked,indent=2)+'\n',encoding='utf-8')
        marker['state']='BlockedLowHeadroom'
        marker_path.write_text(json.dumps(marker,sort_keys=True)+'\n',encoding='utf-8')
        return blocked
    proof=worker.run(job)
    memory_after_worker=memory_status()
    check_result(proof,expected,job,contract)
    timing=out/'TimeoutControl';timing.mkdir(mode=0o700)
    timeout=timeout_control(contract,timing)
    memory_after=memory_status()
    _,_,after_entries,_=collect(bundle,approval)
    need(source_entries==after_entries,'worker_source_changed_during_smoke')
    need(sha((backend/'hotr_backend/replay_contract.py').read_bytes())==CONTRACT_SHA,
         'replay_contract_changed_during_smoke')
    report={'status':('PASS_LOCAL_SERVICE_WORKER_SMOKE126' if require_localservice
                      else 'PASS_DEVELOPER_WORKER_PROBE126'),
            'completedUtc':datetime.now(timezone.utc).isoformat(),'scope':'One recorded Level1 swap only',
            'approvalSHA256':APPROVAL_SHA256,'pinsSHA256':PINS_SHA,'jobFixtureSHA256':JOB_SHA,
            'expectedFixtureSHA256':EXPECTED_SHA,'contractSHA256':CONTRACT_SHA,
            'catalogSHA256':CATALOG_SHA,'catalogBindingsChecked':50,
            'actualUnityReplays':1,'nativeFullCorpusExecuted':False,'levelsReplayQualified':1,
            'executionAccountIsLocalService':is_localservice,'localServiceRequired':require_localservice,
            'qualifiedForLocalService':require_localservice and is_localservice,
            'negativePinRejectedBeforeJobCreation':True,'timeoutControl':timeout,
            'memoryBefore':memory_before,'memoryAfterWorker':memory_after_worker,'memoryAfter':memory_after,
            'minimumAvailablePhysicalBytes':134217728,'minimumAvailableCommitBytes':536870912,
            'process':{key:value for key,value in proof['process'].items() if key!='pid'},
            'checkpointSHA256':proof['result']['checkpointSHA256'],'outcome':proof['result']['outcome'],
            'actions':proof['result']['actions'],'moves':proof['result']['moves'],
            'remainingGoals':proof['result']['remainingGoals'],'jobSHA256':proof['jobSHA256'],
            'workerSourceUnchanged':True,'productionEnabled':False,'financialMutation':False,
            'authorityCreated':False,'liveGameplayConfigured':False,'providerAcceptanceVerified':False,
            'pythonVersion':sys.version.split()[0]}
    (out/'WorkerSmoke126.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    marker['state']='Complete'
    marker_path.write_text(json.dumps(marker,sort_keys=True)+'\n',encoding='utf-8')
    return report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('backend','bundle','approval','job','expected','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    account=parser.add_mutually_exclusive_group(required=True)
    account.add_argument('--require-local-service',action='store_true')
    account.add_argument('--allow-developer-probe',action='store_true',
                         help='Explicit local diagnostic only; never LocalService qualification')
    args=parser.parse_args(argv)
    try:
        result=qualify(*(getattr(args,name).absolute() for name in
             ('backend','bundle','approval','job','expected','out')),args.require_local_service)
        print(json.dumps({'status':result['status'],'actualUnityReplays':result['actualUnityReplays'],
                          'executionAccountIsLocalService':result['executionAccountIsLocalService'],
                          'productionEnabled':False}))
        return 0 if result['status'] in ('PASS_LOCAL_SERVICE_WORKER_SMOKE126',
                                        'PASS_DEVELOPER_WORKER_PROBE126') else 2
    except Exception:
        # Exception values/tracebacks can contain local paths. Keep failures private
        # and fixed; a Pending marker never means qualification or activation.
        print(json.dumps({'status':'BLOCKED_ISOLATED_WINDOWS_REPLAY_SMOKE126','productionEnabled':False}))
        return 1

if __name__=='__main__':
    raise SystemExit(main())

