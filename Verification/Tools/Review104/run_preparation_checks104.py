"""Run source-bound104 preparer tests and the untouched blocked example.

Python fixtures create disposable synthetic directory trees, not an imported
Unity project. This wrapper starts no Editor, worker, network, APK or device.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0, str(ROOT/'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=api.sha(path),bytes=path.stat().st_size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--tag',default='Host01')
    args = parser.parse_args()
    if not args.execute or not re.fullmatch(r'[A-Za-z0-9_]{1,32}',args.tag) or unity_pids():
        parser.error('Explicit serial bounded104 host invocation required')
    out = ROOT/'Verification/Evidence/Review104/Preparation'/args.tag
    private = ROOT/'.verification-cache/Review104/Preparation'/args.tag
    out.mkdir(parents=True,exist_ok=False)
    private.mkdir(parents=True,exist_ok=False)
    sources = [ROOT/'Verification/Tools/Review104'/name for name in ('prepare_staging104.py','test_prepare_staging104.py')]
    sources += [ROOT/'Release/RuStore'/name for name in ('staging-build.example.json','STAGING_BUILD_CONFIGURATION104.txt')]
    sources += [Path(__file__)]
    bound_before = [bind(path) for path in sources]
    before = api.freeze()
    api.write(out/'MainSources_before.json',before)
    record = dict(schemaVersion=1,status='RUNNING_PREPARATION104_CHECKS',startedUtc=api.utc(),
        sourceFilesBefore=bound_before,python=bind(Path(sys.executable)),
        scope='Actual Python unittest discovery over six preparer/ownership fixtures and a separate untouched-example preflight. No Unity import, actual candidate clone, APK, network, provider, worker or device operation.')
    api.write(out/'Authorization.json',record)
    started = time.monotonic()
    try:
        test_command = [sys.executable,'-B','-m','unittest','discover','-s','Verification/Tools/Review104','-p','test_prepare_staging104.py','-v']
        result = subprocess.run(test_command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        console = private/'Tests.log'
        console.write_bytes(result.stdout)
        text = result.stdout.decode('utf-8',errors='replace')
        match = re.search(r'Ran (\d+) tests? in',text)
        executed = int(match.group(1)) if match else 0
        example_command = [sys.executable,'-B','Verification/Tools/Review104/prepare_staging104.py','--config','Release/RuStore/staging-build.example.json']
        example = subprocess.run(example_command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
        example_console = private/'Example.log'
        example_console.write_bytes(example.stdout)
        reply = json.loads(example.stdout.decode('utf-8-sig'))
        tests_good = result.returncode==0 and executed==6 and bool(re.search(r'(?m)^OK\s*$',text))
        example_good = example.returncode==1 and reply.get('status')=='BLOCKED_STAGING104' and reply.get('code')=='MISSING_OR_PLACEHOLDER_STAGING_ORIGIN' and reply.get('buildPerformed') is False and reply.get('networkContacted') is False
        record.update(status='PASS_PREPARATION104_CHECKS' if tests_good and example_good else 'FAIL_PREPARATION104_CHECKS',
            testsCommand=[str(Path(x).relative_to(ROOT)) if x==sys.executable else x for x in test_command],
            testExitCode=result.returncode,executedTests=executed,testsPassed=tests_good,
            exampleCommand=example_command[2:],exampleExitCode=example.returncode,exampleReply=reply,
            untouchedExampleBlocked=example_good,privateConsole=bind(console),privateExampleConsole=bind(example_console))
    except Exception as error:
        record.update(status='FAIL_PREPARATION104_RUNNER',errorType=type(error).__name__)
    finally:
        after = api.freeze()
        api.write(out/'MainSources_after.json',after)
        bound_after = [bind(path) for path in sources]
        record.update(mainInputsUnchanged=before==after,sourceFilesAfter=bound_after,
            toolsAndExampleUnchanged=bound_before==bound_after,finishedUtc=api.utc(),elapsedSeconds=round(time.monotonic()-started,3),
            unityPidsAfter=unity_pids(),actualEditorRun=False,actualCandidatePrepared=False,networkContacted=False)
        if before!=after or bound_before!=bound_after or record['unityPidsAfter']:
            record['status']='FAIL_PREPARATION104_INPUTS_OR_PROCESS'
        api.write(out/'Report.json',record)
    print(json.dumps(dict(status=record['status'],report=(out/'Report.json').relative_to(ROOT).as_posix())))
    return 0 if record['status']=='PASS_PREPARATION104_CHECKS' else 1


if __name__=='__main__':
    raise SystemExit(main())
