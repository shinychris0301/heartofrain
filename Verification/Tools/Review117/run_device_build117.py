"""Exclusive owned117 LTS policy/build execution; never installs or launches an app."""
import argparse,importlib.util,json,os,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0,str(ROOT/'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids
sys.path.insert(0,str(ROOT/'Verification/Tools/Review93'))
from run_connected import resume_owned_primary
HELPER=ROOT/'Verification/Tools/Review107/run_native107.py'
spec=importlib.util.spec_from_file_location('owned117_build_primitives',HELPER);shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
EDITOR=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Unity.exe')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--tag',required=True);p.add_argument('--project',required=True,type=Path);p.add_argument('--build',action='store_true');a=p.parse_args()
 if not a.execute or os.name!='nt' or not re.fullmatch('[A-Za-z0-9_]{1,40}',a.tag):p.error('ExplicitOwned117BuildRequired')
 if unity_pids():p.error('ConcurrentEditorRejected117')
 project=a.project.resolve();receipt=project.parent/'Preparation.json';record=json.loads(receipt.read_text('utf-8'))
 expected_package='com.heartoftherain.review117preview' if record.get('previewMode') is True and record.get('preview') else 'com.heartoftherain.review117'
 if not project.is_relative_to((ROOT/'.verification-cache/Review117/Candidates').resolve()) or project.name!='Game' or record.get('status')!='PREPARED_TEAMS117' or record.get('packageName')!=expected_package or Path(record.get('project','')).resolve()!=project:p.error('ExactOwned117CandidateRequired')
 if any(os.environ.get(k) for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')):p.error('UnreviewedJavaOptionsRejected117')
 cache=Path('E:/HR107G');owner=cache/'.hotr-ads107-cache.json'
 if not owner.is_file() or json.loads(owner.read_text()).get('sourceRoot')!=str(ROOT):p.error('PreserveUnownedGradleCache117')
 out=ROOT/'Verification/Evidence/Review117/Native'/a.tag;private=ROOT/'.verification-cache/Review117/RawNative'/a.tag;out.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False)
 before=api.freeze();local_before=shared.inputs(project);guids=shared.guids(project)
 for name,value in [('MainSources_before.json',before),('ProjectSources_before.json',local_before),('ProjectGuids_before.json',guids)]:api.write(out/name,value)
 operation='BuildDevelopment' if a.build else 'RunPolicy';report_path=out/('BuildDevelopment117.json' if a.build else 'BuildPolicy117.json');expected='PASS_NATIVE_TEAMS117_BUILD_DEVELOPMENT' if a.build else 'PASS_NATIVE_TEAMS117_BUILD_POLICY'
 environment=dict(os.environ);environment.update(HOTR_REVIEW117_OUT=str(out),HOTR_TEAMS117_RECEIPT=str(receipt),GRADLE_USER_HOME=str(cache),SDKMANAGER_OPTS='-Dsun.net.client.defaultConnectTimeout=5000 -Dsun.net.client.defaultReadTimeout=15000')
 for key in ('HOTR_ADS107_RECEIPT','HOTR_ADS107_MANAGED_CONFIG','HOTR_ADS107_ADVERTISING_CONFIG','HOTR_STAGING104_CONFIG','HOTR_STAGING104_ISOLATION'):environment.pop(key,None)
 log=private/'Unity.log';console=private/'Console.log';cmd=[str(EDITOR),'-batchmode','-projectPath',str(project),'-buildTarget','Android','-executeMethod','HeartOfTheRain.Verification.TeamsBuild117.'+operation,'-logFile',str(log)]
 state=dict(status='RUNNING_NATIVE117_LTS',startedUtc=api.utc(),entry='HeartOfTheRain.Verification.TeamsBuild117.'+operation,expectedNativeStatus=expected,expectedEngine='6000.3.27f1',editorSHA256=api.sha(EDITOR),runnerSHA256=api.sha(Path(__file__)),processHelperSHA256=api.sha(HELPER),preparationSHA256=api.sha(receipt),scope='Owned private117 SDK compile/policy or actual Android Development build as reported. No installation, app/SDK request or live-provider acceptance.')
 api.write(out/'Authorization.json',state);started=time.monotonic();job=None;process=None
 try:
  job=api.OwnedJob();startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
  with console.open('x',encoding='utf-8') as stream:
   process=subprocess.Popen(cmd,cwd=project,env=environment,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|0x4,startupinfo=startup);state['pid']=process.pid;job.assign(process.pid);resume_owned_primary(process);state['ownedJobAssignedBeforeResume']=True;print(json.dumps(dict(status='STARTED_NATIVE117_LTS',operation=operation,tag=a.tag)),flush=True)
   try:process.wait(timeout=3600 if a.build else 900)
   except subprocess.TimeoutExpired:state['timedOut']=True;job.close();process.wait(timeout=30)
  native=json.loads(report_path.read_text('utf-8-sig')) if report_path.is_file() else {};text=log.read_text('utf-8-sig',errors='replace') if log.is_file() else '';engine=re.search(r'Initialize engine version:\s*(\S+)',text)
  good=process.returncode==0 and not state.get('timedOut') and engine and engine.group(1)=='6000.3.27f1' and native.get('status')==expected and not native.get('failures') and (not a.build or native.get('actualBuild') is True and native.get('errors')==0)
  state.update(status='PASS_NATIVE117_LTS_INVOCATION' if good else 'FAIL_NATIVE117_LTS_INVOCATION',exitCode=process.returncode,nativeStatus=native.get('status','MISSING'),actualEngine=engine.group(1) if engine else None,checks=native.get('checks',0),nativeReport=report_path.name,nativeReportSHA256=api.sha(report_path) if report_path.exists() else None)
 except Exception as e:state.update(status='FAIL_NATIVE117_LTS_RUNNER',errorType=type(e).__name__)
 finally:
  state['ownedChildClosure']=shared.owned_shutdown(job)
  if process and process.poll() is None:process.kill();process.wait(timeout=30)
  after=api.freeze();local_after=shared.inputs(project);guid_after=shared.guids(project)
  for name,value in [('MainSources_after.json',after),('ProjectSources_after.json',local_after),('ProjectGuids_after.json',guid_after)]:api.write(out/name,value)
  assets_ok=all(local_after['files'].get(k)==v for k,v in local_before['files'].items() if '/Assets/' in k and not k.endswith('.meta'));guid_ok=all(guid_after.get(k)==v for k,v in guids.items())
  state.update(mainInputsUnchanged=before==after,projectInputsUnchanged=local_before==local_after,projectInputDeltas=api.delta(local_before,local_after),originalPrivateAssetAndSourceBytesPreserved=assets_ok,originalPrivateMetaGuidsPreserved=guid_ok,addedMetaGuids=sorted(guid_after.keys()-guids.keys()),unityPidsAfter=unity_pids(),elapsedSeconds=round(time.monotonic()-started,3),finishedUtc=api.utc(),privateLogs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=api.sha(p),bytes=p.stat().st_size) for p in (log,console) if p.is_file()])
  if before!=after or not assets_ok or not guid_ok or state['unityPidsAfter'] or not state['ownedChildClosure'].get('observed') or not state['ownedChildClosure'].get('allObservedHandlesSignaled'):state['status']='FAIL_NATIVE117_LTS_INPUTS_OR_PROCESS'
  api.write(out/'Invocation.json',state)
 print(json.dumps(dict(status=state['status'],report=(out/'Invocation.json').relative_to(ROOT).as_posix())),flush=True)
 return 0 if state['status'].startswith('PASS_') else 1
if __name__=='__main__':raise SystemExit(main())
