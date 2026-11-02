"""Actual ADB gestures/video on the opt-in development fixture, without data clear."""
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
    p=argparse.ArgumentParser();p.add_argument('--serial',required=True);a=p.parse_args()
    out=ROOT/'Verification/Evidence/SwapCreation/Touch';out.mkdir(parents=True,exist_ok=True)
    def adb(*args,check=True):return subprocess.run([str(ADB),'-s',a.serial,*map(str,args)],check=check,capture_output=True,timeout=90).stdout
    subprocess.run([str(ADB),'connect',a.serial],check=True,capture_output=True)
    sha=hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest()
    remote=adb('shell','pm','path',PACKAGE).decode().splitlines()[0].removeprefix('package:').strip()
    assert adb('shell','sha256sum',remote).decode().split()[0]==sha
    result={'status':'RUNNING','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'apk_sha256':sha,'serial':a.serial,'cases':[],'scope':'Four real Android swipes; transient color fixtures, no preferences reset. Videos/captures are not frame-budget measurements.'}
    for mode in ['H','HReverse','V','VReverse']:
        adb('shell','am','force-stop',PACKAGE);time.sleep(4)
        began=dt.datetime.now(dt.timezone.utc);marker=out/'HOTR_RunSwapReview';marker.write_text(mode)
        adb('push',marker,REMOTE+'/HOTR_RunSwapReview');adb('shell','am','start','-W','-n',PACKAGE+'/com.unity3d.player.UnityPlayerActivity')
        def wait(status):
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                try:d=json.loads(adb('shell','cat',REMOTE+'/SwapReview/Report.json',check=False))
                except ValueError:d={}
                if d and dt.datetime.fromisoformat(d['utc'].replace('Z','+00:00'))>=began:
                    if d['status'].startswith('FAIL'):raise AssertionError(d)
                    if d['status']==status:return d
                time.sleep(.5)
            raise TimeoutError(mode+' '+status)
        ready=wait('READY_FOR_NATIVE_GESTURE');(out/(mode+'_Before.png')).write_bytes(adb('exec-out','screencap','-p'))
        remote_video=f'/sdcard/HOTR_Swap_{mode}.mp4'
        video=subprocess.Popen([str(ADB),'-s',a.serial,'shell','screenrecord','--time-limit','4','--bit-rate','10000000',remote_video],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(.6);adb('shell','input','swipe',ready['fromX'],ready['fromY'],ready['toX'],ready['toY'],'220')
        report=wait('PASS_ACTUAL_SWAP_CREATION_INPUT');video.communicate(timeout=30)
        adb('pull',remote_video,out/(mode+'.mp4'));(out/(mode+'_After.png')).write_bytes(adb('exec-out','screencap','-p'));(out/(mode+'_Report.json')).write_text(json.dumps(report,indent=2)+'\n')
        result['cases'].append(report);print(json.dumps({'mode':mode,'status':report['status'],'renderedSamples':len(report['samples'])}),flush=True)
    result['status']='CAPTURED_SWAP_CREATION_REQUIRES_VISUAL_REVIEW';(out/'Report.json').write_text(json.dumps(result,indent=2)+'\n')
    adb('shell','am','force-stop',PACKAGE);time.sleep(4);adb('shell','am','start','-n',PACKAGE+'/com.unity3d.player.UnityPlayerActivity')

if __name__=='__main__':run()
