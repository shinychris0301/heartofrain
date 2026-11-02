"""Actual Android tool/power taps and video on the opt-in obstacle fixture, without data clear."""
import datetime as dt
import hashlib
import json
import subprocess
import time
from pathlib import Path
import argparse

ROOT=Path(__file__).resolve().parents[2]
ADB=Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe')
PACKAGE='com.heartoftherain.verification'
REMOTE=f'/sdcard/Android/data/{PACKAGE}/files'

def run():
    p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--out',type=Path);p.add_argument('--large-gap',action='store_true');a=p.parse_args()
    out=a.out or ROOT/'Verification/Evidence/ObstacleFall/Touch';out.mkdir(parents=True,exist_ok=True)
    def adb(*args,check=True):return subprocess.run([str(ADB),'-s',a.serial,*map(str,args)],check=check,capture_output=True,timeout=90).stdout
    subprocess.run([str(ADB),'connect',a.serial],check=True,capture_output=True)
    sha=hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest()
    remote=adb('shell','pm','path',PACKAGE).decode().splitlines()[0].removeprefix('package:').strip()
    assert adb('shell','sha256sum',remote).decode().split()[0]==sha
    result={'status':'RUNNING','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'apk_sha256':sha,'serial':a.serial,'cases':[],'scope':'Real Android tool/power inputs on transient obstacle fixtures; Slow intentionally injects180ms. No preferences reset. Videos/captures are not frame-budget measurements.'}
    for mode in (['Match','Hammer','EdgeLeft','EdgeRight','Rocket','Slow','LargeGap'] if a.large_gap else ['Match','Hammer','EdgeLeft','EdgeRight','Rocket','Slow']):
        adb('shell','am','force-stop',PACKAGE);time.sleep(4)
        began=dt.datetime.now(dt.timezone.utc);marker=out/'HOTR_RunObstacleFall';marker.write_text(mode)
        adb('push',marker,REMOTE+'/HOTR_RunObstacleFall');adb('shell','am','start','-W','-n',PACKAGE+'/com.unity3d.player.UnityPlayerActivity')
        def wait(status):
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                try:d=json.loads(adb('shell','cat',REMOTE+'/ObstacleFallReview/Report.json',check=False))
                except ValueError:d={}
                if d and dt.datetime.fromisoformat(d['utc'].replace('Z','+00:00'))>=began:
                    if d['status'].startswith('FAIL'):raise AssertionError(d)
                    if d['status']==status:return d
                time.sleep(.5)
            raise TimeoutError(mode+' '+status)
        ready=wait('READY_FOR_NATIVE_GESTURE');(out/(mode+'_Before.png')).write_bytes(adb('exec-out','screencap','-p'))
        remote_video=f'/sdcard/HOTR_Fall_{mode}.mp4'
        video=subprocess.Popen([str(ADB),'-s',a.serial,'shell','screenrecord','--time-limit','5','--bit-rate','10000000',remote_video],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(.6)
        if mode not in ('Rocket','Match'):adb('shell','input','tap',110,1475);time.sleep(.15)
        if mode=='Match':adb('shell','input','swipe',ready['inputFromX'],ready['inputFromY'],ready['inputToX'],ready['inputToY'],'220')
        else:adb('shell','input','tap',ready['targetX'],ready['targetY'])
        report=wait('PASS_ACTUAL_OBSTACLE_FALL_INPUT');video.communicate(timeout=30)
        adb('pull',remote_video,out/(mode+'.mp4'));(out/(mode+'_After.png')).write_bytes(adb('exec-out','screencap','-p'));(out/(mode+'_Report.json')).write_text(json.dumps(report,indent=2)+'\n')
        result['cases'].append(report);print(json.dumps({'mode':mode,'status':report['status'],'renderedSamples':len(report['poses'])}),flush=True)
    result['status']='CAPTURED_OBSTACLE_FALL_REQUIRES_VISUAL_REVIEW';(out/'Report.json').write_text(json.dumps(result,indent=2)+'\n')
    adb('shell','am','force-stop',PACKAGE);time.sleep(4);adb('shell','am','start','-n',PACKAGE+'/com.unity3d.player.UnityPlayerActivity')

if __name__=='__main__':run()
