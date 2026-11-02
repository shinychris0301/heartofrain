"""Collect the current targeted checkpoint without borrowing historical device passes."""
from pathlib import Path
import json, hashlib, datetime as dt, csv, subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Verification/Evidence'
BRANCH = OUT/'IndividualFall'

def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def run():
    apk = ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    digest = sha(apk)
    native = read(BRANCH/'Native_Checks.json')
    assert native['status'] == 'PASS_NATIVE_INDIVIDUAL_FALL' and not native['failures']
    freeze = read(BRANCH/'Player_Source_SHA256.json')
    assert all(sha(ROOT/name) == expected for name, expected in freeze['files'].items())
    freeze['apk_sha256'] = digest
    (BRANCH/'Player_Source_SHA256.json').write_text(json.dumps(freeze, indent=2)+'\n')
    artifact = read(OUT/'Native/APK_Artifact.json')
    assert artifact['sha256'] == digest
    touch, visual = read(BRANCH/'Touch/Report.json'), read(BRANCH/'Visual_Review.json')
    assert touch['status'] == 'PASS_ACTUAL_INDIVIDUAL_FALL_VISUAL_REVIEW' and visual['status'] == 'PASS_ACTUAL_INDIVIDUAL_FALL_VISUAL_REVIEW'
    assert touch['apk_sha256'] == visual['apk_sha256'] == digest and len(touch['cases']) == 7
    assert all(sha(BRANCH/name) == expected for name, expected in visual['artifactSHA256'].items())
    build=read(BRANCH/'Android_Build.json')
    assert build['status']=='PASS_ANDROID_DEVELOPMENT_BUILD' and build['errors']==0
    assert read(BRANCH/'APK_Packaging.json')['afterSHA256']==digest
    assert all(not c['failures'] and c['status'] == 'PASS_ACTUAL_OBSTACLE_FALL_INPUT' for c in touch['cases'])
    installs = [read(BRANCH/name) for name in ['MainInstance_Final_Installation.json', 'QA_Final_Installation.json']]
    assert all(i['apk_sha256'] == digest and i['status'] == 'PASS_FINAL_APK_INSTALLED_AND_RUNNING' for i in installs)
    assert read(BRANCH/'Preferences_Preservation.json')['status'] == 'PASS_IDENTICAL_PREFERENCE_FILES'
    checks = {name: read(BRANCH/name) for name in ['Timing_Checks.json', 'Preceding_Fall_Checks.json', 'Swap_Checks.json', 'General_Checks.json', 'Play_Smoke.json']}
    assert all(r['status'].startswith('PASS') for r in checks.values())
    assert read(BRANCH/'Integrity.json')['status'].startswith('PASS')
    summary = {'status':'PASS_TARGETED_VERIFICATION_WITH_OPEN_RELEASE_GATES', 'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
               'current_evidence_branch':'IndividualFall', 'unity':'2022.3.62f3', 'apk':artifact, 'individual_fall_native':native,
               'other_current_native':checks, 'actual_android':touch, 'visual_review':visual, 'installations':installs,
               'full_current_android_regression':'NOT_RERUN: seven targeted device scenarios; all50 boards covered by native route/timing checks.',
               'historical_full_android':{'path':'SwapCreation/LDPlayer/Regression.json','scope':'Earlier APK; not current-APK coverage.'},
               'remaining':['Physical-device performance and long-session stress','Identical-board competitor timing/pixel parity','Durable profile, inventory and idempotent attempt settlement','Production billing, social and live services','Human balance review']}
    (OUT/'Verification_Summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (BRANCH/'Verification_Summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    changed = subprocess.run(['git','status','--porcelain=v1','--untracked-files=all'], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    with (OUT/'Changed_Files.csv').open('w', newline='', encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['status','path','category'])
        for line in changed.splitlines():
            name=line[3:];writer.writerow([line[:2],name,'Current refill implementation/evidence' if ('IndividualFall' in name or name.endswith(('BoardModel.cs','BoardPlayback.cs','BoardPresentation.cs'))) else 'Existing project work or verification'])
    print(json.dumps({'status':summary['status'],'apk_sha256':digest,'native_checks':native['checks'],'device_cases':len(touch['cases'])}, indent=2))

if __name__ == '__main__': run()
