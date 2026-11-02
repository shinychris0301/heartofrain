"""Opt-in isolated Android file profiles; real gift taps and process restarts."""
from pathlib import Path
import argparse,datetime as dt,hashlib,json,re,subprocess,time,uuid,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
ADB=Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe')
PKG='com.heartoftherain.verification';BASE=f'/sdcard/Android/data/{PKG}/files'

def run():
    p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--out',type=Path,default=ROOT/'Verification/Evidence/DailyGift/Device');p.add_argument('--case',choices=['Restart','RecoverAgain','WonRestart']);p.add_argument('--run-id');p.add_argument('--keep-open',action='store_true');p.add_argument('--allow-resolution-prefs',action='store_true');a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if a.case:assert a.run_id and re.fullmatch('[0-9a-f]{32}',a.run_id)
    def adb(*args,check=True):return subprocess.run([str(ADB),'-s',a.serial,*map(str,args)],check=check,capture_output=True,timeout=100).stdout
    subprocess.run([str(ADB),'connect',a.serial],check=True,capture_output=True)
    sha=hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest()
    remote=adb('shell','pm','path',PKG).decode().splitlines()[0].removeprefix('package:').strip();assert adb('shell','sha256sum',remote).decode().split()[0]==sha
    def preferences():
        return {name:hashlib.sha256(adb('exec-out','run-as',PKG,'cat','shared_prefs/'+name)).hexdigest() for name in adb('shell','run-as',PKG,'ls','shared_prefs').decode().split() if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',name)}
    def preference_keys():
        return {name+'/'+e.attrib['name']:hashlib.sha256(ET.tostring(e)).hexdigest() for name in preferences() for e in ET.fromstring(adb('exec-out','run-as',PKG,'cat','shared_prefs/'+name))}
    def saves():
        paths=adb('shell','find',BASE+'/Profiles','-type','f','-name','*.json',check=False).decode().splitlines()
        return {name.removeprefix(BASE+'/'):adb('shell','sha256sum',name).decode().split()[0] for name in paths if re.fullmatch(re.escape(BASE)+r'/Profiles/[A-Za-z0-9_./-]+\.json',name)}
    before=preferences();keys_before=preference_keys();real_before=saves();result={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'RUNNING','serial':a.serial,'apk_sha256':sha,'cases':[]}
    for modes in ([(a.case,)] if a.case else [('Tap','Restart'),('StartAttempt','Recover','RecoverAgain'),('Auto','WonRestart')]):
        run_id=a.run_id if a.case else uuid.uuid4().hex
        for mode in modes:
            adb('shell','am','force-stop',PKG);time.sleep(2);began=dt.datetime.now(dt.timezone.utc);marker=out/'HOTR_RunDailyGift';marker.write_text(json.dumps({'runId':run_id,'mode':mode}));adb('push',marker,BASE+'/HOTR_RunDailyGift');adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity')
            folder=BASE+f'/DailyGiftVerification/{run_id}/Evidence/{mode}';tapped=set();until=time.monotonic()+320
            while time.monotonic()<until:
                try:r=json.loads(adb('shell','cat',folder+'/Report.json',check=False))
                except ValueError:r={}
                if r and dt.datetime.fromisoformat(r['utc'].replace('Z','+00:00'))>=began:
                    status=r['status']
                    if status in ('READY_HOME_TAP','READY_CLAIM_TAP') and status not in tapped:
                        (out/(mode+'_'+status+'.png')).write_bytes(adb('exec-out','screencap','-p'));adb('shell','input','tap',r['x'],r['y']);tapped.add(status)
                    if status.startswith(('PASS','FAIL')):break
                time.sleep(.5)
            else:raise TimeoutError(mode)
            destination=out/mode;destination.mkdir(exist_ok=True);adb('pull',folder+'/.',destination)
            (destination/'Final.png').write_bytes(adb('exec-out','screencap','-p'));assert r['status']=='PASS_NATIVE_DAILY_GIFT' and not r['failures'],r
            if mode=='Tap':assert len(tapped)==2
            r['actual_android_taps']=len(tapped);result['cases'].append(r);(out/'Report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'mode':mode,'status':r['status'],'checks':r['checks'],'frames':len(r['frames'])}),flush=True)
    result['preferences_before']=before;result['preferences_after']=preferences();result['player_saves_before']=real_before;result['player_saves_after']=saves();keys_after=preference_keys();changed=[n for n in keys_before.keys()|keys_after.keys() if keys_before.get(n)!=keys_after.get(n)];result['changed_preference_keys']=changed
    allowed={'Screenmanager%20Fullscreen%20mode','Screenmanager%20Resolution%20Height','Screenmanager%20Resolution%20Width'}
    unchanged=before==result['preferences_after'];expected_resize=a.allow_resolution_prefs and all(n.split('/',1)[1] in allowed for n in changed)
    result['status']='PRESERVATION_REVIEW_REQUIRED';(out/'Report.json').write_text(json.dumps(result,indent=2)+'\n')
    assert (unchanged or expected_resize) and real_before==result['player_saves_after'],'Opt-in fixtures changed real preferences/profile files'
    result['preferences_status']='PASS_IDENTICAL_PREFERENCE_FILES' if unchanged else 'PASS_GAME_SETTINGS_WITH_EXPECTED_RESOLUTION_KEYS'
    result['status']='PASS_NATIVE_ANDROID_DAILY_GIFT_REQUIRES_VISUAL_REVIEW';(out/'Report.json').write_text(json.dumps(result,indent=2)+'\n')
    if not a.keep_open:adb('shell','am','force-stop',PKG);time.sleep(2);adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity')

if __name__=='__main__':run()
