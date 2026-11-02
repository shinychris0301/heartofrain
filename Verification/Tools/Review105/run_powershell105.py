"""Actual Windows launcher bootstrap rejection using the untouched empty example.

No execution-policy override, service start, credential, Unity or device action.
"""
import json
from pathlib import Path
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Backend/tools'))
from run_tests import source_hashes
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
from run_ads85_native import OwnedJob,freeze,sha,utc,write
sys.path.insert(0,str(ROOT/'Verification/Tools/Review93'))
from run_connected import resume_owned_primary


def bind(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)


def main():
    if sys.argv[1:]!=['--execute'] or os.name!='nt':raise SystemExit('Explicit Windows105 PowerShell probe required')
    out=ROOT/'Verification/Evidence/Review105/PowerShell/Example01'
    private=ROOT/'.verification-cache/Review105/PowerShell/Example01'
    out.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False)
    script=ROOT/'Backend/Start-Staging105.ps1';example=ROOT/'Release/RuStore/staging-server.example.json'
    support=[bind(script),bind(example)]
    before=freeze();backend=source_hashes();default_exists=(ROOT/'Backend/.local').exists()
    write(out/'MainSources_before.json',before)
    record=dict(schemaVersion=1,status='RUNNING_POWERSHELL105_EMPTY_EXAMPLE',startedUtc=utc(),runner=bind(Path(__file__)),supportBefore=support,
        scope='Actual powershell.exe -File bootstrap with no execution-policy override and the unchanged empty staging example. Expected validation rejection before service/database construction; not a hosted or Android acceptance test.')
    write(out/'Authorization.json',record)
    job=process=None;started=time.monotonic()
    try:
        job=OwnedJob()
        with (private/'Console.log').open('xb') as stream:
            process=subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-File',str(script),'-Manifest',str(example),'-Action','preflight'],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|0x4)
            job.assign(process.pid);resume_owned_primary(process);record['ownedJobAssignedBeforeResume']=True
            process.wait(timeout=60)
        text=(private/'Console.log').read_text('utf-8-sig',errors='replace')
        values=[]
        for line in text.splitlines():
            if line.startswith('{'):
                try:values.append(json.loads(line))
                except ValueError:pass
        expected=dict(status='blocked_staging105',code='staging_owned_https_origin_required',productionEnabled=False)
        good=process.returncode!=0 and values==[expected]
        record.update(status='PASS_POWERSHELL105_EMPTY_EXAMPLE_BLOCKED' if good else 'FAIL_POWERSHELL105_EMPTY_EXAMPLE',
            exitCode=process.returncode,pythonBootstrapReached=values==[expected],fixedValidationReply=values[0] if values==[expected] else None,
            executionPolicyOverridden=False,serviceStartRequested=False,privateConsole=bind(private/'Console.log'))
    except Exception as error:record.update(status='FAIL_POWERSHELL105_RUNNER',errorType=type(error).__name__)
    finally:
        if job:job.close()
        if process and process.poll() is None:process.kill();process.wait(timeout=15)
        after=freeze();backend_after=source_hashes();write(out/'MainSources_after.json',after)
        record.update(mainInputsUnchanged=before==after,backendInputsUnchanged=backend==backend_after,
            sourceSHA256=backend,sourceSHA256After=backend_after,supportAfter=[bind(script),bind(example)],
            defaultBackendLocalDirectoryExistenceUnchanged=(ROOT/'Backend/.local').exists()==default_exists,
            finishedUtc=utc(),seconds=round(time.monotonic()-started,3))
        if before!=after or backend!=backend_after or support!=record['supportAfter'] or not record['defaultBackendLocalDirectoryExistenceUnchanged']:
            record['status']='FAIL_POWERSHELL105_INPUTS_OR_DATA_BOUNDARY'
        write(out/'Report.json',record)
    print(json.dumps(dict(status=record['status'],report=(out/'Report.json').relative_to(ROOT).as_posix())))
    return 0 if record['status']=='PASS_POWERSHELL105_EMPTY_EXAMPLE_BLOCKED' else 1


if __name__=='__main__':raise SystemExit(main())
