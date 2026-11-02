"""Collect current R2 native/device evidence with explicit build and source guards."""
from pathlib import Path
import json, hashlib, datetime as dt, subprocess, csv
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence'
BRANCH=OUT/'M70R2'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run():
    digest=sha(ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk')
    native=read(BRANCH/'Native_Checks.json');provided=read(BRANCH/'Supplied_Checks.json')
    assert native['status']=='PASS_NATIVE_M70R2_CREATION' and not native['failures'] and provided['passed'] and len(provided['checks'])==15
    freeze=read(BRANCH/'Player_Source_SHA256.json');assert all(sha(ROOT/n)==v for n,v in freeze['files'].items())
    freeze['apk_sha256']=digest;(BRANCH/'Player_Source_SHA256.json').write_text(json.dumps(freeze,indent=2)+'\n')
    artifact=read(OUT/'Native/APK_Artifact.json');assert artifact['sha256']==digest
    assert read(BRANCH/'Android_Build.json')['errors']==0 and read(BRANCH/'APK_Packaging.json')['afterSHA256']==digest
    package=read(BRANCH/'Package_Audit.json');assert all(r['samePayload'] and r['sameGUID'] for r in package['assets']) and all(r['matches'] for r in package['checksums'])
    source=read(BRANCH/'Source_Changes.json');assert source['boardModelUnchanged'] and source['boardPlaybackUnchanged']
    touch,visual=read(BRANCH/'Touch/Report.json'),read(BRANCH/'Visual_Review.json')
    assert touch['status']==visual['status']=='PASS_NATIVE_M70R2_VISUAL_REVIEW' and touch['apk_sha256']==visual['apk_sha256']==digest and len(touch['cases'])==10
    assert all(c['status']=='PASS_NATIVE_DEVICE_M70R2_CREATION' and not c['failures'] for c in touch['cases'])
    cases={c['mode']:c for c in touch['cases']};assert cases['GrantIntro']['pauseChecked'] and cases['GrantIntro']['gateHeld']
    retry=read(BRANCH/'Touch/GrantIntro_Retry_UI.json');assert retry['status']=='PASS_ACTUAL_UI_RETRY_VISUAL_REVIEW' and retry['apk_sha256']==digest
    assert cases['GrantNoIntro']['gateHeld'] and cases['FailureRetry']['failureChecked']
    assert all(sha(BRANCH/n)==v for n,v in visual['artifactSHA256'].items())
    installs=[read(BRANCH/p) for p in ['MainInstance_Final_Installation.json','QA_Final_Installation.json']]
    assert all(i['status']=='PASS_FINAL_APK_INSTALLED_AND_RUNNING' and i['apk_sha256']==digest for i in installs)
    assert read(BRANCH/'Preferences_Preservation.json')['status']=='PASS_IDENTICAL_PREFERENCE_FILES' and installs[1]['preferencesIdentical']
    checks={p:read(BRANCH/p) for p in ['Fall_Checks.json','Timing_Checks.json','Swap_Checks.json','General_Checks.json','Play_Smoke.json']};assert all(r['status'].startswith('PASS') for r in checks.values())
    assert read(BRANCH/'Integrity.json')['status'].startswith('PASS')
    summary={'status':'PASS_TARGETED_VERIFICATION_WITH_OPEN_RELEASE_GATES','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'current_evidence_branch':'M70R2','unity':'2022.3.62f3',
             'apk':artifact,'requested_patch':'M70_R2_After_M70.patch; adapted merge onto current runtime','package_audit':package,'source_changes':source,
             'native_creation':native,'supplied_unity_checks':provided,'other_current_native':checks,'actual_android':touch,'visual_review':visual,'installations':installs,
             'full_current_android_regression':'NOT_RERUN: ten targeted creation/lifecycle scenarios; all50-board falling/timing coverage is native.',
             'historical_full_android':'SwapCreation/LDPlayer/Regression.json belongs to an earlier APK, not current-APK certification.',
             'remaining':['Physical-device performance and long-session stress','Heavy combo frame spikes','Human balance and exhaustive natural play','Durable profile/inventory/idempotent attempt settlement','Production billing/social/live services']}
    for path in [OUT/'Verification_Summary.json',BRANCH/'Verification_Summary.json']:path.write_text(json.dumps(summary,indent=2)+'\n')
    status=subprocess.run(['git','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT,check=True,capture_output=True,text=True).stdout
    with (OUT/'Changed_Files.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['status','path','category'])
        for line in status.splitlines():
            name=line[3:];w.writerow([line[:2],name,'M70 R2 integration/evidence' if ('M70R2' in name or 'M70PowerCreation' in name or name.endswith(('BoardPresentation.cs','BoardReactionReview.cs','GameplayScreen.cs'))) else 'Existing project work or verification'])
    print(json.dumps({'status':summary['status'],'apk_sha256':digest,'native_creation_checks':native['checks'],'supplied_unity_checks':len(provided['checks']),'device_cases':len(touch['cases'])},indent=2))

if __name__=='__main__':run()
