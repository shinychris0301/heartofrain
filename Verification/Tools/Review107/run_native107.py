"""Serial107 native runner; the explicit entry defines Editor/build scope. No install."""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0,str(ROOT/'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids
sys.path.insert(0,str(ROOT/'Verification/Tools/Review93'))
from run_connected import resume_owned_primary

def inputs(project):
    previous=api.UNITY_PROJECT
    try:api.UNITY_PROJECT=project;return api.freeze()
    finally:api.UNITY_PROJECT=previous
def guids(project):
    result={}
    for path in (project/'Assets').rglob('*.meta'):
        found=re.findall(rb'(?m)^guid:\s*([0-9a-fA-F]{32})\s*$',path.read_bytes())
        if len(found)!=1:raise ValueError('UniqueAssetGuidRequired107')
        result[path.relative_to(project).as_posix()]=found[0].decode('ascii').lower()
    if len(set(result.values()))!=len(result):raise ValueError('AssetGuidCollision107')
    return result
def owned_shutdown(job):
    if not job or not job.handle:return dict(observed=False,reason='JobAlreadyClosed')
    kernel=job.kernel;kernel.QueryInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p];kernel.QueryInformationJobObject.restype=wintypes.BOOL
    kernel.IsProcessInJob.argtypes=[wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.BOOL)];kernel.IsProcessInJob.restype=wintypes.BOOL
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
    handles=[];ids=[]
    try:
        buf=ctypes.create_string_buffer(8+ctypes.sizeof(ctypes.c_size_t)*512)
        if not kernel.QueryInformationJobObject(job.handle,3,buf,len(buf),None):return dict(observed=False,reason='OwnedJobQueryFailed')
        count=ctypes.c_uint32.from_buffer(buf,4).value
        for i in range(count):
            pid=ctypes.c_size_t.from_buffer(buf,8+i*ctypes.sizeof(ctypes.c_size_t)).value
            handle=kernel.OpenProcess(0x100000|0x1000,False,pid)
            if not handle:continue
            owned=wintypes.BOOL()
            if kernel.IsProcessInJob(handle,job.handle,ctypes.byref(owned)) and owned.value:handles.append(handle);ids.append(pid)
            else:kernel.CloseHandle(handle)
        job.close();deadline=time.monotonic()+25;closed=[]
        for handle in handles:closed.append(kernel.WaitForSingleObject(handle,int(max(0,deadline-time.monotonic())*1000))==0)
        return dict(observed=True,membershipVerifiedPids=ids,allObservedHandlesSignaled=all(closed),closure='OwnedJob kill-on-close followed by bounded retained-process-handle waits; not graceful shutdown.')
    finally:
        job.close()
        for handle in handles:kernel.CloseHandle(handle)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--tag',required=True);p.add_argument('--entry',required=True);p.add_argument('--report',required=True);p.add_argument('--expected',required=True);p.add_argument('--project',type=Path);p.add_argument('--output-env',default='HOTR_REVIEW107_OUT');p.add_argument('--timeout',type=int,default=600);p.add_argument('--quit',action='store_true');p.add_argument('--apk',type=Path);p.add_argument('--phase',choices=('Before','After'));p.add_argument('--managed-config',type=Path);p.add_argument('--advertising-config',type=Path);args=p.parse_args()
    if not args.execute or os.name!='nt' or not 30<=args.timeout<=3600 or not re.fullmatch('[A-Za-z0-9_]{1,40}',args.tag) or not re.fullmatch(r'HeartOfTheRain\.[A-Za-z0-9_.]+',args.entry) or not re.fullmatch('HOTR_[A-Z0-9_]+',args.output_env):p.error('ExplicitBoundedNative107Required')
    if unity_pids():p.error('ConcurrentEditorRejected107')
    project=(args.project or ROOT/'Unity').resolve();private_project=args.project is not None
    receipt=None
    if private_project:
        if not project.is_relative_to((ROOT/'.verification-cache/Review107/Candidates').resolve()) or project.name!='Game':p.error('OwnedPrepared107CandidateRequired')
        receipt=project.parent/'Preparation.json';record=json.loads(receipt.read_text('utf-8'))
        if record.get('status')!='PREPARED_ADS107' or Path(record.get('project','')).resolve()!=project:p.error('Prepared107ReceiptRequired')
    editor=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Unity.exe') if private_project else api.PINNED_UNITY
    version='6000.3.27f1' if private_project else '2022.3.62f3'
    out=ROOT/'Verification/Evidence/Review107/Native'/args.tag;private=ROOT/'.verification-cache/Review107/RawNative'/args.tag;report=(out/args.report).resolve()
    if not report.is_relative_to(out.resolve()) or report.suffix!='.json':p.error('Contained107ReportRequired')
    for config in (args.managed_config,args.advertising_config):
        if config is not None and (not private_project or str(config).startswith('\\\\') or not config.is_file() or config.stat().st_size>8192):p.error('ExplicitLocalPrivateConfigurationRequired107')
    if args.apk is not None and (not private_project or not args.apk.resolve().is_relative_to((project/'Builds').resolve()) or args.apk.exists() or args.apk.suffix!='.apk'):p.error('FreshOwnedPrivateApkRequired107')
    if any(os.environ.get(k) for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')):p.error('UnreviewedJavaOptionsRejected107')
    out.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False)
    before,project_before=api.freeze(),inputs(project);guid_before=guids(project);api.write(out/'MainSources_before.json',before);api.write(out/'ProjectSources_before.json',project_before);api.write(out/'ProjectGuids_before.json',guid_before)
    environment=dict(os.environ);environment.update(HOTR_REVIEW107_OUT=str(out),HOTR_REVIEW107_PRIVATE_OUT=str(private));environment[args.output_env]=str(out)
    if args.phase:environment['HOTR_REVIEW106_PHASE']=args.phase
    if private_project:
        cache=Path('E:/HR107G');cache_owner=cache/'.hotr-ads107-cache.json'
        if cache.exists():
            if not cache_owner.is_file() or json.loads(cache_owner.read_text()).get('sourceRoot')!=str(ROOT):p.error('UnknownGradleCachePreserved107')
        else:cache.mkdir();api.write(cache_owner,dict(version=1,sourceRoot=str(ROOT),scope='Owned107 public Gradle/Maven cache; no credentials'))
        environment.update(HOTR_ADS107_RECEIPT=str(receipt),GRADLE_USER_HOME=str(cache),SDKMANAGER_OPTS='-Dsun.net.client.defaultConnectTimeout=5000 -Dsun.net.client.defaultReadTimeout=15000')
    if args.apk:environment['HOTR_ADS107_APK']=str(args.apk.resolve())
    if args.managed_config:environment['HOTR_ADS107_MANAGED_CONFIG']=str(args.managed_config.resolve())
    if args.advertising_config:environment['HOTR_ADS107_ADVERTISING_CONFIG']=str(args.advertising_config.resolve())
    for key in ('HOTR_ADS107_MANAGED_CONFIG','HOTR_ADS107_ADVERTISING_CONFIG'):
        if (key.endswith('MANAGED_CONFIG') and not args.managed_config) or (key.endswith('ADVERTISING_CONFIG') and not args.advertising_config):environment.pop(key,None)
    log=private/'Unity.log';console=private/'Console.log';cmd=[str(editor),'-batchmode','-projectPath',str(project),'-executeMethod',args.entry,'-logFile',str(log)]
    if private_project:cmd+=['-buildTarget','Android']
    if args.quit:cmd+=['-quit']
    state=dict(schemaVersion=1,status='RUNNING_NATIVE107',startedUtc=api.utc(),entry=args.entry,expectedNativeStatus=args.expected,expectedEngine=version,editorSHA256=api.sha(editor),runnerSHA256=api.sha(Path(__file__)),mainInputCount=before['inputCount'],projectInputCount=project_before['inputCount'],projectScope='fresh-private107-LTS' if private_project else 'main2022',scope='Actual serialEditor/nativeentry only; APK compilation is reported only by an actual BuildPipeline result. No device install/launch or SDK load/show/realreward is authorized.')
    if receipt:state['preparationSHA256']=api.sha(receipt)
    api.write(out/'Authorization.json',state);started=time.monotonic();job=None;process=None
    try:
        job=api.OwnedJob();startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        with console.open('x',encoding='utf-8') as stream:
            process=subprocess.Popen(cmd,cwd=project,env=environment,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|0x4,startupinfo=startup);state['pid']=process.pid;job.assign(process.pid);resume_owned_primary(process);state['ownedJobAssignedBeforeResume']=True;print(json.dumps(dict(status='STARTED_NATIVE107',tag=args.tag,engine=version)),flush=True)
            try:process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:state['timedOut']=True;job.close();process.wait(timeout=30)
        native=json.loads(report.read_text('utf-8-sig')) if report.is_file() else {};text=log.read_text('utf-8-sig',errors='replace') if log.is_file() else '';match=re.search(r'Initialize engine version:\s*(\S+)',text)
        state.update(exitCode=process.returncode,nativeStatus=native.get('status','MISSING'),actualEngine=match.group(1) if match else None,nativeReport=args.report,nativeReportSHA256=api.sha(report) if report.exists() else None,checks=native.get('checks',native.get('passed',0)))
        good=process.returncode==0 and not state.get('timedOut') and state['actualEngine']==version and native.get('status')==args.expected and not any(native.get(k) for k in ('error','errors','failed','failures'))
        # Build reports use numeric errors=-1 only when no build occurred.
        if native.get('operation') in ('Policy','Packaging'):good=process.returncode==0 and state['actualEngine']==version and native.get('status')==args.expected and not native.get('failures')
        state['status']='PASS_NATIVE107_INVOCATION' if good else 'FAIL_NATIVE107_INVOCATION'
    except Exception as error:state.update(status='FAIL_NATIVE107_RUNNER',errorType=type(error).__name__)
    finally:
        state['ownedChildClosure']=owned_shutdown(job)
        if process and process.poll() is None:process.kill();process.wait(timeout=30)
        after,project_after=api.freeze(),inputs(project);api.write(out/'MainSources_after.json',after);api.write(out/'ProjectSources_after.json',project_after)
        a,b=project_before['files'],project_after['files'];diff=api.delta(project_before,project_after)
        asset_preserved=all(b.get(k)==v for k,v in a.items() if '/Assets/' in k and not k.endswith('.meta'))
        guid_after=guids(project);api.write(out/'ProjectGuids_after.json',guid_after);guid_equal=all(guid_after.get(k)==v for k,v in guid_before.items())
        state.update(mainInputsUnchanged=before==after,projectInputDeltas=diff,projectInputsUnchanged=project_before==project_after,originalPrivateAssetAndSourceBytesPreserved=asset_preserved,originalPrivateMetaGuidsPreserved=guid_equal,addedMetaGuids=sorted(guid_after.keys()-guid_before.keys()),unityPidsAfter=unity_pids(),finishedUtc=api.utc(),elapsedSeconds=round(time.monotonic()-started,3),privateLogs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=api.sha(p),bytes=p.stat().st_size) for p in (log,console) if p.is_file()])
        if before!=after or state['unityPidsAfter'] or not asset_preserved or not guid_equal or not state['ownedChildClosure'].get('observed') or not state['ownedChildClosure'].get('allObservedHandlesSignaled'):state['status']='FAIL_NATIVE107_INPUTS_OR_PROCESS'
        api.write(out/'Invocation.json',state)
    print(json.dumps(dict(status=state['status'],report=(out/'Invocation.json').relative_to(ROOT).as_posix())),flush=True);return 0 if state['status'].startswith('PASS_') else 1
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        # No authorization file means Popen has not been reached. Preserve a
        # malformed-metadata/preflight rejection without claiming Unity ran.
        tag=sys.argv[sys.argv.index('--tag')+1] if '--tag' in sys.argv and sys.argv.index('--tag')+1<len(sys.argv) else ''
        out=ROOT/'Verification/Evidence/Review107/Native'/tag
        if re.fullmatch('[A-Za-z0-9_]{1,40}',tag) and out.is_dir() and not (out/'Authorization.json').exists() and not (out/'Invocation.json').exists():
            api.write(out/'PrelaunchSources107.json',api.freeze())
            api.write(out/'PrelaunchFailure107.json',dict(schemaVersion=1,status='PRELAUNCH_METADATA_REJECTED',utc=api.utc(),runnerSHA256=api.sha(Path(__file__)),errorType=type(error).__name__,code=str(error) if re.fullmatch('[A-Za-z0-9]{1,100}',str(error)) else 'PrelaunchInputRejected107',actualEditorStarted=False,compilerInvoked=False,sdkImportInvoked=False,ownedProcessCreated=False,scope='Runner/input failure before authorization/process creation; not a native Unity test result.'))
            print(json.dumps(dict(status='PRELAUNCH_METADATA_REJECTED',report=(out/'PrelaunchFailure107.json').relative_to(ROOT).as_posix())),flush=True);raise SystemExit(1)
        raise
