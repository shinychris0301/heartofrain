"""Record explicit opt-in R2 match, conversion and starting-item lifecycle cases."""
from pathlib import Path
import argparse, datetime as dt, hashlib, json, subprocess, time
ROOT=Path(__file__).resolve().parents[2]
ADB=Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe')
PKG='com.heartoftherain.verification'

def run():
    parser=argparse.ArgumentParser();parser.add_argument('--serial',required=True);parser.add_argument('--mode');parser.add_argument('--starting-only',action='store_true');parser.add_argument('--out',type=Path,default=ROOT/'Verification/Evidence/M70R2/Touch');a=parser.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    def adb(*args,check=True):return subprocess.run([str(ADB),'-s',a.serial,*map(str,args)],check=check,capture_output=True,timeout=120).stdout
    subprocess.run([str(ADB),'connect',a.serial],check=True,capture_output=True)
    sha=hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest()
    remote=adb('shell','pm','path',PKG).decode().splitlines()[0].removeprefix('package:').strip();assert adb('shell','sha256sum',remote).decode().split()[0]==sha
    base=f'/sdcard/Android/data/{PKG}/files'
    result={'status':'RUNNING','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'apk_sha256':sha,'serial':a.serial,'cases':[],
            'scope':'Five real match swipes, two combination swipes, real intro tap and explicit native starting/pause/retry/load-failure lifecycle controls. Synthetic match colors, actual authored grant layouts; no save writes or performance certification.'}
    modes=['MatchH','MatchV','MatchBomb','MatchOrb','MatchSeeker','ConversionBomb','ConversionRocket','GrantIntro','GrantNoIntro','FailureRetry']
    if a.starting_only:
        modes=['GrantIntro','GrantNoIntro','FailureRetry'];result['scope']='Native starting-power grant with actual intro tap, no-intro grant and failure/retry lifecycle controls. Transient review state; no persistence or performance claim.'
    if a.mode:
        assert a.mode in modes
        result=json.loads((out/'Report.json').read_text());assert result['apk_sha256']==sha
    for mode in ([a.mode] if a.mode else modes):
        adb('shell','am','force-stop',PKG);time.sleep(4);began=dt.datetime.now(dt.timezone.utc)
        marker=out/'HOTR_RunM70R2';marker.write_text(mode);adb('push',marker,base+'/HOTR_RunM70R2');adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity')
        def wait(status):
            until=time.monotonic()+150
            while time.monotonic()<until:
                try:r=json.loads(adb('shell','cat',base+'/M70R2Review/Report.json',check=False))
                except ValueError:r={}
                if r and dt.datetime.fromisoformat(r['utc'].replace('Z','+00:00'))>=began:
                    if r['status'].startswith('FAIL'):
                        (out/(mode+'_Report.json')).write_text(json.dumps(r,indent=2)+'\n');raise AssertionError(r['failures'])
                    if r['status']==status:return r
                time.sleep(.4)
            raise TimeoutError(mode+' '+status)
        ready=wait('READY_FOR_NATIVE_GESTURE');(out/(mode+'_Before.png')).write_bytes(adb('exec-out','screencap','-p'))
        seconds=12 if mode=='GrantIntro' else 7 if mode.startswith('Conversion') else 5
        video=subprocess.Popen([str(ADB),'-s',a.serial,'shell','screenrecord','--time-limit',str(seconds),'--bit-rate','10000000',f'/sdcard/HOTR_R2_{mode}.mp4'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(.6);begin=out/'Begin';begin.write_text('begin');adb('push',begin,base+'/M70R2Review/Begin')
        if ready['action']=='swipe':adb('shell','input','swipe',ready['fromX'],ready['fromY'],ready['toX'],ready['toY'],'220')
        elif ready['action']=='introTap':adb('shell','input','tap',ready['toX'],ready['toY'])
        report=wait('PASS_NATIVE_DEVICE_M70R2_CREATION')
        if mode=='GrantIntro':
            # Supplement the native birth/pause trace with real pause-menu retry.
            (out/'GrantIntro_Retry_Before.png').write_bytes(adb('exec-out','screencap','-p'))
            assert ready['width']==900 and ready['height']==1600
            adb('shell','input','tap',799,1475);time.sleep(.6)
            (out/'GrantIntro_Retry_Menu.png').write_bytes(adb('exec-out','screencap','-p'))
            adb('shell','input','tap',ready['toX'],ready['toY']);time.sleep(1.2)
            (out/'GrantIntro_Retry_Intro.png').write_bytes(adb('exec-out','screencap','-p'))
            adb('shell','input','tap',ready['toX'],ready['toY']);time.sleep(1)
            (out/'GrantIntro_Retry_After.png').write_bytes(adb('exec-out','screencap','-p'))
            retry={'status':'CAPTURED_REQUIRES_VISUAL_REVIEW','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'apk_sha256':sha,'serial':a.serial,'scope':'Actual ADB settings/restart/Play taps following the completed native formation/pause trace. Before/menu/new-intro/after screenshots and the12s movie require visual review. The native probe retryChecked flag remains false; this supplement verifies the UI path visually, not a native post-retry model fingerprint.'}
            (out/'GrantIntro_Retry_UI.json').write_text(json.dumps(retry,indent=2)+'\n')
        video.communicate(timeout=30);adb('pull',f'/sdcard/HOTR_R2_{mode}.mp4',out/(mode+'.mp4'))
        (out/(mode+'_After.png')).write_bytes(adb('exec-out','screencap','-p'));(out/(mode+'_Report.json')).write_text(json.dumps(report,indent=2)+'\n');result['cases']=[c for c in result['cases'] if c['mode']!=mode]+[report]
        print(json.dumps({'mode':mode,'status':report['status'],'poses':len(report['poses']),'size':[report['columns'],report['rows']]}),flush=True)
    result['status']='CAPTURED_M70R2_REQUIRES_VISUAL_REVIEW';(out/'Report.json').write_text(json.dumps(result,indent=2)+'\n')
    adb('shell','am','force-stop',PKG);time.sleep(4);adb('shell','am','start','-n',PKG+'/com.unity3d.player.UnityPlayerActivity')

if __name__=='__main__':run()
