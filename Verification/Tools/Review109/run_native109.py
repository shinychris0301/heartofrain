"""Serial mainUnity2022 verification for Teams109. No import/build/device mode."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
PROJECT=ROOT/'Unity'
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0,str(ROOT/'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids
sys.path.insert(0,str(ROOT/'Verification/Tools/Review93'))
from run_connected import resume_owned_primary
# Reuse only the process-membership/retained-handle closure primitive. This
# imports no old source/build/config pins and starts no process at import time.
HELPER=ROOT/'Verification/Tools/Review107/run_native107.py'
spec=importlib.util.spec_from_file_location('native109_owned_process_primitives',HELPER)
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)

def guids():
    values={}
    for path in (PROJECT/'Assets').rglob('*.meta'):
        found=re.findall(rb'(?m)^guid:\s*([0-9a-fA-F]{32})\s*$',path.read_bytes())
        if len(found)!=1:raise ValueError('UniqueAssetGuidRequired109')
        values[path.relative_to(PROJECT).as_posix()]=found[0].decode('ascii').lower()
    if len(set(values.values()))!=len(values):raise ValueError('AssetGuidCollision109')
    return values

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true');p.add_argument('--tag',required=True)
    p.add_argument('--entry',required=True);p.add_argument('--report',required=True);p.add_argument('--expected',required=True)
    p.add_argument('--output-env',default='HOTR_REVIEW109_OUT');p.add_argument('--timeout',type=int,default=600)
    p.add_argument('--quit',action='store_true')
    p.add_argument('--import-epoch',action='store_true',help='Record only new R4 PNG importer-meta normalization; never permit original-meta/source changes.')
    args=p.parse_args()
    if not args.execute or os.name!='nt' or not 30<=args.timeout<=1800:p.error('ExplicitBoundedMain109Required')
    if not re.fullmatch('[A-Za-z0-9_]{1,40}',args.tag) or not re.fullmatch(r'HeartOfTheRain\.[A-Za-z0-9_.]+',args.entry) or not re.fullmatch('HOTR_[A-Z0-9_]+',args.output_env):p.error('SafeNative109ContractRequired')
    if unity_pids():p.error('ConcurrentEditorRejected109')
    out=ROOT/'Verification/Evidence/Review109/Native'/args.tag
    private=ROOT/'.verification-cache/Review109/RawNative'/args.tag
    report=(out/args.report).resolve()
    if not report.is_relative_to(out.resolve()) or report.suffix!='.json':p.error('Contained109ReportRequired')
    out.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False)
    before=api.freeze();api.write(out/'MainSources_before.json',before)
    guid_before=guids();api.write(out/'AssetGuids_before.json',guid_before)
    baseline=json.loads((ROOT/'Verification/Tools/Review109/BaselineMain109.json').read_text('utf-8-sig'))
    original_metas={k:v for k,v in baseline['files'].items() if k.endswith('.meta')}
    if any(before['files'].get(k)!=v for k,v in original_metas.items()):raise ValueError('OriginalAssetMetadataChanged109')
    import_candidates={k:v for k,v in before['files'].items() if k not in baseline['files'] and k.startswith('Unity/Assets/HeartOfTheRain/App/TeamsAccess/Art/') and k.endswith('.png.meta')}
    if args.import_epoch:
        retained=out/'ImportMetaBefore';retained.mkdir()
        for k in import_candidates:(retained/Path(k).name).write_bytes((ROOT/k).read_bytes())
    env=dict(os.environ);env['HOTR_REVIEW109_OUT']=str(out);env[args.output_env]=str(out)
    log=private/'Unity.log';console=private/'Console.log'
    command=[str(api.PINNED_UNITY),'-batchmode','-projectPath',str(PROJECT),'-executeMethod',args.entry,'-logFile',str(log)]
    if args.quit:command+=['-quit']
    state=dict(schemaVersion=1,status='RUNNING_NATIVE109',startedUtc=api.utc(),entry=args.entry,expectedNativeStatus=args.expected,
        expectedEngine='2022.3.62f3',runnerSHA256=api.sha(Path(__file__)),processHelperSHA256=api.sha(HELPER),
        editorSHA256=api.sha(api.PINNED_UNITY),mainInputCount=before['inputCount'],assetGuidCount=len(guid_before),
        importEpoch=args.import_epoch,importCandidateCount=len(import_candidates),
        scope='Actual main2022 Editor execution. Optional first R4 importer normalization is separately retained; only NEW PNG metas may change with GUIDs preserved. No package autoimport, APK/build, service launch, SDK initialization, device operation or production acceptance. The native suite declares its own rendering/fixture scope.')
    api.write(out/'Authorization.json',state);started=time.monotonic();job=None;process=None
    try:
        job=api.OwnedJob();startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        with console.open('x',encoding='utf-8') as stream:
            process=subprocess.Popen(command,cwd=PROJECT,env=env,stdout=stream,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW|0x4,startupinfo=startup)
            state['pid']=process.pid;job.assign(process.pid);resume_owned_primary(process);state['ownedJobAssignedBeforeResume']=True
            print(json.dumps(dict(status='STARTED_NATIVE109',tag=args.tag,entry=args.entry)),flush=True)
            try:process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:state['timedOut']=True;job.close();process.wait(timeout=30)
        native=json.loads(report.read_text('utf-8-sig')) if report.is_file() else {}
        text=log.read_text('utf-8-sig',errors='replace') if log.is_file() else '';engine=re.search(r'Initialize engine version:\s*(\S+)',text)
        checks=native.get('checks',native.get('passed',0));checks=checks if isinstance(checks,int) else native.get('passed',0)
        state.update(exitCode=process.returncode,nativeStatus=native.get('status','MISSING'),actualEngine=engine.group(1) if engine else None,
            checks=checks,nativeReport=args.report,nativeReportSHA256=api.sha(report) if report.exists() else None)
        passed=process.returncode==0 and not state.get('timedOut') and state['actualEngine']=='2022.3.62f3' and native.get('status')==args.expected and not any(native.get(k) for k in ('error','errors','failed','failures'))
        state['status']='PASS_NATIVE109_INVOCATION' if passed else 'FAIL_NATIVE109_INVOCATION'
    except Exception as error:state.update(status='FAIL_NATIVE109_RUNNER',errorType=type(error).__name__)
    finally:
        state['ownedChildClosure']=shared.owned_shutdown(job)
        if process and process.poll() is None:process.kill();process.wait(timeout=30)
        after=api.freeze();guid_after=guids();api.write(out/'MainSources_after.json',after);api.write(out/'AssetGuids_after.json',guid_after)
        change=api.delta(before,after)
        import_ok=args.import_epoch and not change['added'] and not change['removed'] and set(change['changed'])<=set(import_candidates) and guid_before==guid_after
        if args.import_epoch:
            api.write(out/'ImportNormalization109.json',dict(status='ACCEPTED_NEW_META_IMPORT109' if import_ok else 'REJECTED_IMPORT_DELTA109',
                originalMetaCount=len(original_metas),originalMetasPreserved=all(after['files'].get(k)==v for k,v in original_metas.items()),
                newImporterMetaCount=len(import_candidates),guidPreserved=guid_before==guid_after,sourceDelta=change,
                changed=[dict(path=k,before=before['files'][k],after=after['files'][k]) for k in change['changed']],
                note='Import epoch only. Acceptance suites must bind the final post-import manifest without permitted mutations.'))
        state.update(mainInputsUnchanged=before==after,importNormalizationAccepted=import_ok,assetGuidsUnchanged=guid_before==guid_after,sourceDelta=change,
            unityPidsAfter=unity_pids(),finishedUtc=api.utc(),elapsedSeconds=round(time.monotonic()-started,3),
            privateLogs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=api.sha(p),bytes=p.stat().st_size) for p in (log,console) if p.is_file()])
        if (before!=after and not import_ok) or guid_before!=guid_after or state['unityPidsAfter'] or not state['ownedChildClosure'].get('observed') or not state['ownedChildClosure'].get('allObservedHandlesSignaled'):state['status']='FAIL_NATIVE109_INPUTS_OR_PROCESS'
        api.write(out/'Invocation.json',state)
    print(json.dumps(dict(status=state['status'],report=(out/'Invocation.json').relative_to(ROOT).as_posix())),flush=True)
    return 0 if state['status'].startswith('PASS_') else 1

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        tag=sys.argv[sys.argv.index('--tag')+1] if '--tag' in sys.argv and sys.argv.index('--tag')+1<len(sys.argv) else ''
        out=ROOT/'Verification/Evidence/Review109/Native'/tag
        if re.fullmatch('[A-Za-z0-9_]{1,40}',tag) and out.is_dir() and not (out/'Authorization.json').exists() and not (out/'Invocation.json').exists():
            api.write(out/'PrelaunchFailure109.json',dict(schemaVersion=1,status='PRELAUNCH_METADATA_REJECTED',utc=api.utc(),
                errorType=type(error).__name__,code=str(error) if re.fullmatch('[A-Za-z0-9]{1,100}',str(error)) else 'PrelaunchInputRejected109',
                runnerSHA256=api.sha(Path(__file__)),actualEditorStarted=False,compilerInvoked=False))
            print(json.dumps(dict(status='PRELAUNCH_METADATA_REJECTED',report=(out/'PrelaunchFailure109.json').relative_to(ROOT).as_posix())),flush=True)
            raise SystemExit(1)
        raise
