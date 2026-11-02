"""Source-bound staging105 configuration/operations tests; no Unity or worker.

The owned child runs canonical unittest module discovery. Full traces and any
fixture material remain private; only static failure locations are exported.
"""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[3]
BACKEND=ROOT/'Backend'
sys.path.insert(0,str(BACKEND))
sys.path.insert(0,str(BACKEND/'tools'))
from run_tests import source_hashes,Result,failure_locations
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
from run_ads85_native import OwnedJob,freeze,sha,utc,write
sys.path.insert(0,str(ROOT/'Verification/Tools/Review93'))
from run_connected import resume_owned_primary

MODULES=('tests.test_staging105','tests.test_staging_ops105','tests.test_operations','tests.test_readiness86')


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)


def child(out,private,modules):
    before=source_hashes()
    stream=io.StringIO()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in modules)
    started=time.monotonic()
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
    (private/'Tests.log').write_text(stream.getvalue(),encoding='utf-8')
    after=source_hashes()
    changed=sorted(name for name in before.keys()|after.keys() if before.get(name)!=after.get(name))
    counts={name:sum(test.startswith(name+'.') for test in result.passed) for name in modules}
    good=result.wasSuccessful() and not result.skipped and not changed and all(counts.values())
    report=dict(schemaVersion=1,status='PASS_FOCUSED_BACKEND105' if good else 'FAIL_FOCUSED_BACKEND105',
        utc=utc(),scope='Actual Python unittest modules with real disposable SQLite and controlled ASGI/operator fixtures. No hosted service, Unity, Android, replay worker or live provider acceptance.',
        modules=list(modules),executedTests=result.testsRun-len(result.skipped),passed=result.passed,
        passedByModule=counts,failures=[test.id() for test,_ in result.failures],errors=[test.id() for test,_ in result.errors],
        skipped=[test.id() for test,_ in result.skipped],failureLocations=failure_locations(result.failures+result.errors),
        sourceSHA256=before,sourceSHA256After=after,sourceInputsChangedDuringRun=changed,
        seconds=round(time.monotonic()-started,3),privateTrace=bind(private/'Tests.log'))
    write(out/'ServiceTests.json',report)
    return 0 if good else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--tag',default='Focused01')
    p.add_argument('--only-ops',action='store_true')
    p.add_argument('--child-output',type=Path,help=argparse.SUPPRESS)
    p.add_argument('--child-private',type=Path,help=argparse.SUPPRESS)
    args=p.parse_args()
    modules=('tests.test_staging_ops105',) if args.only_ops else MODULES
    if args.child_output:
        out,private=args.child_output.resolve(),args.child_private.resolve()
        if not out.is_relative_to((ROOT/'Verification/Evidence/Review105/Focused').resolve()) or not private.is_relative_to((ROOT/'.verification-cache/Review105/Focused').resolve()):
            p.error('Exact owned105 child report paths required')
        return child(out,private,modules)
    if not args.execute or os.name!='nt' or not args.tag.replace('_','').isalnum():
        p.error('Explicit fresh Windows105 test execution required')
    out=ROOT/'Verification/Evidence/Review105/Focused'/args.tag
    private=ROOT/'.verification-cache/Review105/Focused'/args.tag
    out.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False)
    before=freeze();sources=source_hashes()
    write(out/'MainSources_before.json',before)
    record=dict(schemaVersion=1,status='RUNNING_FOCUSED105',startedUtc=utc(),runner=bind(Path(__file__)),
        modules=list(modules),scope='One owned suspended/assigned Python child, canonical focused unittest modules. The full selection includes untouched-example preflight; ops-only follow-up does not rerun that unchanged check. No Unity, gameplay worker, APK, device, hosted HTTPS or provider.')
    write(out/'Authorization.json',record)
    job=process=None;started=time.monotonic()
    try:
        job=OwnedJob()
        environment={key:value for key,value in os.environ.items() if not key.upper().startswith('HOTR_')}
        environment.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',HOTR_BACKEND_MODE='local')
        with (private/'Console.log').open('xb') as stream:
            command=[sys.executable,'-B',str(Path(__file__).resolve()),'--child-output',str(out),'--child-private',str(private)]
            if args.only_ops:command.append('--only-ops')
            process=subprocess.Popen(command,
                cwd=BACKEND,env=environment,stdout=stream,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW|0x4)
            job.assign(process.pid);resume_owned_primary(process)
            record['ownedJobAssignedBeforeResume']=True
            print(json.dumps(dict(status='STARTED_FOCUSED105',tag=args.tag)),flush=True)
            process.wait(timeout=300)
        report=load(out/'ServiceTests.json')
        if args.only_ops:
            record.update(status='PASS_FOCUSED105_INVOCATION' if process.returncode==0 and report['status']=='PASS_FOCUSED_BACKEND105' else 'FAIL_FOCUSED105_INVOCATION',
                exitCode=process.returncode,serviceReport=bind(out/'ServiceTests.json'),executedTests=report['executedTests'],untouchedExampleRerun=False)
        else:
            example_preflight(record,report,process,out,private,environment)
    except Exception as error:
        record.update(status='FAIL_FOCUSED105_RUNNER',errorType=type(error).__name__)
    finally:
        if job:job.close()
        if process and process.poll() is None:
            process.kill();process.wait(timeout=15)
        after=freeze();source_after=source_hashes()
        write(out/'MainSources_after.json',after)
        record.update(mainInputsUnchanged=before==after,backendInputsUnchanged=sources==source_after,
            sourceSHA256=sources,sourceSHA256After=source_after,finishedUtc=utc(),seconds=round(time.monotonic()-started,3),
            actualReplayWorker=False,unityOrDeviceAction=False)
        if (private/'Console.log').exists():record['privateConsole']=bind(private/'Console.log')
        if before!=after or sources!=source_after:record['status']='FAIL_FOCUSED105_SOURCE_CHANGED'
        write(out/'Invocation.json',record)
    print(json.dumps(dict(status=record['status'],report=(out/'Invocation.json').relative_to(ROOT).as_posix())))
    return 0 if record['status']=='PASS_FOCUSED105_INVOCATION' else 1


def example_preflight(record,report,process,out,private,environment):
        example=ROOT/'Release/RuStore/staging-server.example.json'
        example_before=bind(example)
        result=subprocess.run([sys.executable,'-B','-m','hotr_backend.staging105','preflight','--manifest',str(example)],
            cwd=BACKEND,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW)
        (private/'Example.log').write_bytes(result.stdout)
        reply=json.loads(result.stdout.decode('utf-8-sig'))
        blocked=result.returncode==1 and reply.get('status')=='blocked_staging105' and reply.get('code')=='staging_owned_https_origin_required'
        example_unchanged=bind(example)==example_before
        record.update(status='PASS_FOCUSED105_INVOCATION' if process.returncode==0 and report['status']=='PASS_FOCUSED_BACKEND105' and blocked and example_unchanged else 'FAIL_FOCUSED105_INVOCATION',
            exitCode=process.returncode,serviceReport=bind(out/'ServiceTests.json'),executedTests=report['executedTests'],
            example=example_before,exampleUnchanged=example_unchanged,untouchedExampleBlocked=blocked,
            exampleReply=reply,exampleExitCode=result.returncode,privateExampleConsole=bind(private/'Example.log'))


def load(path):return json.loads(path.read_text('utf-8-sig'))


if __name__=='__main__':raise SystemExit(main())
