"""Collect the current targeted fall pass; keep preceding broad Android coverage historical."""
import csv
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Verification/Evidence';BRANCH=OUT/'ObstacleFall'
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8-sig'))
def run():
 artifact=read('Native/APK_Artifact.json');sha=hashlib.sha256(Path(artifact['path']).read_bytes()).hexdigest();assert sha==artifact['sha256']
 native=read('ObstacleFall/Native_Checks.json');timing=read('Timing/Native_Checks.json');swap=read('SwapCreation/Native_Checks.json');general=read('Native/Native_Checks.json');smoke=read('Native/Play_Smoke.json');build=read('Native/Android_Build.json');touch=read('ObstacleFall/Touch/Report.json');visual=read('ObstacleFall/Visual_Review.json');integrity=read('Integrity_Current.json');source=read('ObstacleFall/Player_Source_SHA256.json');packaging=read('ObstacleFall/APK_Packaging.json')
 assert native['status']=='PASS_NATIVE_OBSTACLE_FALL' and not native['failures']
 assert timing['status']=='PASS_NATIVE_TIMING_CHECKS' and not timing['failures']
 assert swap['status']=='PASS_NATIVE_SWAP_CREATION' and not swap['failures'] and general['failed']==0
 assert smoke['status']=='PASS_NATIVE_PLAY_SMOKE' and not smoke['errors'] and build['errors']==0
 assert touch['status']=='PASS_ACTUAL_OBSTACLE_FALL_VISUAL_REVIEW' and touch['apk_sha256']==sha and len(touch['cases'])==6
 assert all(c['status']=='PASS_ACTUAL_OBSTACLE_FALL_INPUT' and not c['failures'] for c in touch['cases'])
 slow=next(c for c in touch['cases'] if c['mode']=='Slow');assert slow['forcedSlowFrame'] and 0<=slow['forcedSlowAge']<slow['seconds']
 assert visual['status']=='PASS_NATIVE_OBSTACLE_FALL_VISUAL_REVIEW' and visual['apk_sha256']==sha
 assert packaging['afterSHA256']==sha and packaging['sameSignerCertificate'] and not packaging['changedNonSignatureEntries']
 assert read('ObstacleFall/APK_Orientation.json')['apk_sha256']==sha and read('ObstacleFall/APK_Payloads.json')['apk_sha256']==sha
 assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in source['files'].items())
 assert integrity['status'].startswith('PASS_') and not integrity['unexpected_changed_baseline_files']
 installations={n:read('ObstacleFall/'+n+'.json') for n in ['MainInstance_Final_Installation','QA_Final_Installation']}
 assert all(d['status']=='PASS_FINAL_APK_INSTALLED_AND_RUNNING' and d['apk_sha256']==sha for d in installations.values())
 prior=read('SwapCreation/LDPlayer/Regression.json');prior_install=read('SwapCreation/LDPlayer/Installation.json')
 result={'status':'PASS_TARGETED_VERIFICATION_WITH_OPEN_RELEASE_GATES','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'current_evidence_branch':'ObstacleFall','unity':'2022.3.62f3','native_editor_checks':general,'native_play_smoke':smoke,'obstacle_fall_native_checks':native,'approved_timing_checks':timing,'swap_creation_native_checks':swap,'android_targeted_review':visual,'android_input_capture_review':touch,'current_full_android_regression':'NOT_RERUN_FOR_THIS_PRESENTATION_ONLY_CHANGE','historical_full_android_regression':{'evidence':'SwapCreation/LDPlayer/Regression.json','status':prior['status'],'checks':prior['checks'],'boards':prior['boards'],'actions':prior['actions'],'apk_sha256':prior_install['sha256'],'scope':'Preceding swap-creation APK; not this build.'},'android':{'apk_sha256':sha,'apk_bytes':artifact['bytes'],'apk':artifact['path'],'installations':installations,'preferences':read('ObstacleFall/Preferences_Preservation.json')},'reference_review':read('ObstacleFall/Reference_Motion_Samples.json'),'integrity':{'baseline_files':integrity['baseline_files'],'unexpected_changes':0},'open_gates':['Physical-device lifecycle/performance/thermal certification','Owner/native-speaker visual review and human campaign balance','Durable profile/inventory and idempotent settlement','Production commerce/social/events/analytics/support'],'review':'Codex_Handoff/Documentation/22_OBSTACLE_FALL_ANIMATION_REVIEW.md'}
 (OUT/'Verification_Summary.json').write_text(json.dumps(result,indent=2)+'\n')
 paths=set();tracked=set()
 for cmd in [['git','diff','--name-only','--no-renames','-z'],['git','ls-files','--others','--exclude-standard','-z']]:
  names=set(subprocess.run(cmd,cwd=ROOT,check=True,stdout=subprocess.PIPE).stdout.decode().split('\0'));paths.update(names)
  if cmd[1]=='diff':tracked=names
 from collect_results import category
 with (OUT/'Changed_Files.csv').open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=['status','path','category']);writer.writeheader();writer.writerows({'status':'MODIFIED' if p in tracked else 'ADDED','path':p,'category':category(p)} for p in sorted(paths-{''}))
 print(json.dumps({'status':result['status'],'branch':'ObstacleFall','native_checks':native['checks'],'android_cases':len(touch['cases']),'apk_sha256':sha}))
if __name__=='__main__':run()
