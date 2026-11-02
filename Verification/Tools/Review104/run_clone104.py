"""Record one approved Unity2022 clone preparation; delegate copying to its owner tool.

The exact synthetic host is parsed only. It is not an assigned/owned backend.
No Editor, DNS, HTTP, BuildPipeline, APK or device is invoked here.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0,str(ROOT/'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids
sys.path.insert(0,str(ROOT/'Verification/Tools/Review104'))
from run_native104 import inputs, isolated_boundary


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=api.sha(path),bytes=path.stat().st_size)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true')
    args=p.parse_args()
    candidates=ROOT/'.verification-cache/Review104/Candidates'
    if not args.execute or unity_pids() or candidates.exists() and any(candidates.iterdir()):
        p.error('Explicit first and only104 candidate preparation requires no active Editor or earlier candidate')
    out=ROOT/'Verification/Evidence/Review104/Preparation/Clone01'
    private=ROOT/'.verification-cache/Review104/Preparation/Clone01'
    out.mkdir(parents=True,exist_ok=False)
    private.mkdir(parents=True,exist_ok=False)
    config=private/'Fixture.json'
    payload=dict(version=1,mode='ManagedGuestServer',origin='https://staging.hotr-native-fixture.net',
                 identityScope='review-staging-native104',allowDevelopmentLoopback=False,socialEnabled=True)
    config.write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
    before=api.freeze()
    api.write(out/'MainSources_before.json',before)
    tool=ROOT/'Verification/Tools/Review104/prepare_staging104.py'
    record=dict(schemaVersion=1,status='RUNNING_ONE_ISOLATED104_PREPARATION',startedUtc=api.utc(),
        preparer=bind(tool),orchestrator=bind(Path(__file__)),nativeRunner=bind(ROOT/'Verification/Tools/Review104/run_native104.py'),
        fixture=bind(config),syntheticOriginAssignedOrOwned=False,networkContacted=False,
        scope='One actual filesystem clone using the builder-owned104 preparer and independently validated full source/receipt/settings boundary. No Unity import or APK, DNS, HTTP, provider, worker or device operation.')
    api.write(out/'Authorization.json',record)
    started=time.monotonic()
    try:
        command=[sys.executable,'-B',str(tool),'--execute','--config',str(config),'--tag','EditorImport01']
        result=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
        console=private/'Console.log';console.write_bytes(result.stdout)
        reply=json.loads(result.stdout.decode('utf-8-sig'))
        record.update(exitCode=result.returncode,preparerStatus=reply.get('status'),privateConsole=bind(console))
        if result.returncode!=0 or reply.get('status')!='PREPARED_STAGING104':
            raise ValueError('Actual104PreparationMustSucceed')
        project=(candidates/'EditorImport01/Game').resolve()
        receipt=project.parent/'Preparation.json'
        proof=json.loads(receipt.read_text('utf-8-sig'))
        candidate=inputs(project)
        boundary=isolated_boundary(project,proof,before,candidate)
        api.write(out/'CandidateSources_beforeFirstImport.json',candidate)
        record.update(status='PASS_ONE_ISOLATED104_PREPARATION',receipt=bind(receipt),
            project=project.relative_to(ROOT).as_posix(),independentBoundary=boundary,
            copiedInputCount=candidate['inputCount'],actualCandidatePrepared=True)
    except Exception as error:
        record.update(status='FAIL_ONE_ISOLATED104_PREPARATION',errorType=type(error).__name__)
    finally:
        after=api.freeze();api.write(out/'MainSources_after.json',after)
        record.update(mainInputsUnchanged=before==after,preparerUnchanged=bind(tool)==record['preparer'],
            finishedUtc=api.utc(),elapsedSeconds=round(time.monotonic()-started,3),unityPidsAfter=unity_pids())
        if before!=after or not record['preparerUnchanged'] or record['unityPidsAfter']:
            record['status']='FAIL_ONE_ISOLATED104_PREPARATION_BOUNDARY'
        api.write(out/'Report.json',record)
    print(json.dumps(dict(status=record['status'],report=(out/'Report.json').relative_to(ROOT).as_posix())))
    return 0 if record['status']=='PASS_ONE_ISOLATED104_PREPARATION' else 1


if __name__=='__main__':
    raise SystemExit(main())
