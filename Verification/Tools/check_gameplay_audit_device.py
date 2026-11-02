"""Actual Android mixed gem/power gestures on transient opt-in native boards."""
from pathlib import Path
import argparse, datetime as dt, hashlib, json, subprocess, time
from qa_android_target import validate_qa_target, assert_no_active_attempt
ROOT=Path(__file__).resolve().parents[2]
ADB=Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe')
PKG='com.heartoftherain.verification'

def run():
    p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--out',type=Path,default=ROOT/'Verification/Evidence/GameplayAudit/Touch');a=p.parse_args()
    target=validate_qa_target(a.serial,a.out);out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    def adb(*args,check=True):return subprocess.run([str(ADB),'-s',a.serial,*map(str,args)],check=check,capture_output=True,timeout=100).stdout
    assert adb('get-state').strip()==b'device'
    attempt_guard=assert_no_active_attempt(adb,PKG)
    sha=hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest()
    remote=adb('shell','pm','path',PKG).decode().splitlines()[0].removeprefix('package:').strip();assert adb('shell','sha256sum',remote).decode().split()[0]==sha
    base=f'/sdcard/Android/data/{PKG}/files';result={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'RUNNING','apk_sha256':sha,'serial':a.serial,'qa_target':target,'attempt_guard':attempt_guard,'cases':[]}
    for mode in ['MixedH','MixedV','MixedBomb','MixedOrb','MixedSeeker','MixedChain','ObstaclePartial','ObstacleClear']:
        adb('shell','am','force-stop',PKG);time.sleep(3);began=dt.datetime.now(dt.timezone.utc)
        marker=out/'HOTR_RunGameplayAudit';marker.write_text(mode);adb('push',marker,base+'/HOTR_RunGameplayAudit');adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity')
        def wait(status):
            until=time.monotonic()+100
            while time.monotonic()<until:
                try:r=json.loads(adb('shell','cat',base+'/GameplayAuditReview/Report.json',check=False))
                except ValueError:r={}
                if r and dt.datetime.fromisoformat(r['utc'].replace('Z','+00:00'))>=began:
                    if r['status'].startswith('FAIL'):
                        (out/(mode+'_Report.json')).write_text(json.dumps(r,indent=2)+'\n');raise AssertionError(r['failures'])
                    if r['status']==status:return r
                time.sleep(.4)
            raise TimeoutError(mode+' '+status)
        ready=wait('READY_FOR_NATIVE_GESTURE');(out/(mode+'_Before.png')).write_bytes(adb('exec-out','screencap','-p'))
        video=subprocess.Popen([str(ADB),'-s',a.serial,'shell','screenrecord','--size','720x1280','--time-limit','8','--bit-rate','8000000',f'/sdcard/HOTR_Audit_{mode}.mp4'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(.6);begin=out/'Begin';begin.write_text('begin');adb('push',begin,base+'/GameplayAuditReview/Begin');adb('shell','input','swipe',ready['fromX'],ready['fromY'],ready['toX'],ready['toY'],'180')
        report=wait('PASS_NATIVE_DEVICE_GAMEPLAY_AUDIT');assert report.get('launchCleared'), 'Launch still covers the review';assert mode.startswith('Obstacle') or report.get('sourceActivated') and report.get('protectedBirth') and not report.get('chained'), 'Mixed power protection failed';video.communicate(timeout=20);assert video.returncode==0
        adb('pull',f'/sdcard/HOTR_Audit_{mode}.mp4',out/(mode+'.mp4'));(out/(mode+'_After.png')).write_bytes(adb('exec-out','screencap','-p'));(out/(mode+'_Report.json')).write_text(json.dumps(report,indent=2)+'\n');result['cases'].append(report)
        print(json.dumps({'mode':mode,'status':report['status'],'poses':len(report['poses']),'chained':report['chained']}),flush=True)
    result['status']='CAPTURED_GAMEPLAY_AUDIT_REQUIRES_VISUAL_REVIEW';(out/'Report.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':run()
