"""Install a verified APK without clearing data; record hashes, not preference contents."""
import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from capture_gameplay_comparison import ADB, ROOT

PACKAGE='com.heartoftherain.verification'

def run():
    p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--out',type=Path,default=ROOT/'Verification/Evidence/Timing');a=p.parse_args()
    out=a.out.resolve();apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    sha=hashlib.sha256(apk.read_bytes()).hexdigest()
    if out.name in ('ObstacleFall','IndividualFall','M70R2'):
        targeted=json.loads((out/'Touch/Report.json').read_text())
        assert targeted['status']==('PASS_NATIVE_M70R2_VISUAL_REVIEW' if out.name=='M70R2' else 'PASS_ACTUAL_INDIVIDUAL_FALL_VISUAL_REVIEW' if out.name=='IndividualFall' else 'PASS_ACTUAL_OBSTACLE_FALL_VISUAL_REVIEW') and targeted['apk_sha256']==sha
        assert len(targeted['cases'])==(10 if out.name=='M70R2' else 7 if out.name=='IndividualFall' else 6) and all(c['status']==('PASS_NATIVE_DEVICE_M70R2_CREATION' if out.name=='M70R2' else 'PASS_ACTUAL_OBSTACLE_FALL_INPUT') and not c['failures'] for c in targeted['cases'])
    else:
        installation=json.loads((out/'LDPlayer/Installation.json').read_text())
        assert installation['sha256']==sha and json.loads((out/'LDPlayer/Regression.json').read_text())['status']=='PASS_NATIVE_REGRESSION'
        if out.name=='DailyGift':
            visual=json.loads((out/'Visual_Review.json').read_text());device=json.loads((out/'Device/Report.json').read_text())
            assert visual['status']=='PASS_NATIVE_DAILY_GIFT_VISUAL_REVIEW' and visual['apk_sha256']==device['apk_sha256']==sha
            assert device['status']=='PASS_NATIVE_ANDROID_DAILY_GIFT_REQUIRES_VISUAL_REVIEW' and len(device['cases'])==7
        if out.name in ('GameplayAudit','PowerWarmup'):
            touch=json.loads((out/'Touch/Report.json').read_text());visual=json.loads((out/'Visual_Review.json').read_text())
            assert touch['apk_sha256']==visual['apk_sha256']==sha and touch['status']=='PASS_NATIVE_GAMEPLAY_AUDIT_VISUAL_REVIEW' and visual['status']=='PASS_NATIVE_GAMEPLAY_AUDIT_VISUAL_REVIEW'
            assert len(touch['cases'])==8 and all(c['status']=='PASS_NATIVE_DEVICE_GAMEPLAY_AUDIT' and not c['failures'] for c in touch['cases'])
    def adb(*parts,check=True):return subprocess.run([ADB,'-s',a.serial,*map(str,parts)],capture_output=True,check=check,timeout=90)
    subprocess.run([ADB,'connect',a.serial],capture_output=True,check=True,timeout=20)
    def preferences():
        listing=adb('shell','run-as',PACKAGE,'ls','shared_prefs',check=False)
        if listing.returncode:return {'status':'NOT_OBSERVED','files':{}}
        files={}
        for name in listing.stdout.decode().split():
            if not re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',name):continue
            body=adb('exec-out','run-as',PACKAGE,'cat','shared_prefs/'+name).stdout
            files[name]=hashlib.sha256(body).hexdigest()
        return {'status':'HASHED_WITHOUT_STORING_CONTENT','files':files}
    adb('shell','am','force-stop',PACKAGE);time.sleep(5);before=preferences()
    result=adb('install','-r',apk).stdout.decode();assert 'Success' in result,result
    launch=adb('shell','am','start','-W','-n',PACKAGE+'/com.unity3d.player.UnityPlayerActivity').stdout.decode();time.sleep(8)
    pid=adb('shell','pidof',PACKAGE).stdout.decode().strip();assert pid
    remote=adb('shell','pm','path',PACKAGE).stdout.decode().splitlines()[0].removeprefix('package:').strip()
    installed=adb('shell','sha256sum',remote).stdout.decode().split()[0];assert installed==sha
    after=preferences();prefs={'status':'PASS_IDENTICAL_PREFERENCE_FILES' if before['status']==after['status']=='HASHED_WITHOUT_STORING_CONTENT' and before['files']==after['files'] else 'PREFERENCE_HASH_REVIEW_REQUIRED','before':before,'after':after,'scope':'Only shared preference file hashes. No application data clear or uninstall. This does not certify durable campaign/inventory storage.','apk_sha256':sha}
    qa=out.name in ('GameplayAudit','PowerWarmup','DailyGift') and a.serial.endswith(':5557')
    (out/('QA_Preferences_Preservation.json' if qa else 'Preferences_Preservation.json')).write_text(json.dumps(prefs,indent=2)+'\n',encoding='utf-8',newline='\n')
    report={'status':'PASS_FINAL_APK_INSTALLED_AND_RUNNING','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'instance':'Original LDPlayer instance 0','serial':a.serial,'apk_sha256':sha,'apk_bytes':apk.stat().st_size,'install':result.strip(),'launch':launch,'pid':pid,'preferences_status':prefs['status'],'scope':'Verified final APK installed with -r and launched. Other apps and their data were not modified.'}
    if qa:report['instance']='Dedicated LDPlayer instance 1';report['preferencesIdentical']=prefs['status']=='PASS_IDENTICAL_PREFERENCE_FILES'
    (out/('QA_Final_Installation.json' if qa else 'MainInstance_Final_Installation.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    (out/('QA_Launch.png' if qa else 'MainInstance_Launch.png')).write_bytes(adb('exec-out','screencap','-p').stdout)
    print(json.dumps({k:report[k] for k in ['status','serial','apk_sha256','preferences_status']},indent=2))

if __name__=='__main__':run()
