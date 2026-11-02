"""Actual Android input/screens on the dedicated QA instance after the suite.

This is input evidence, not a frame-budget measurement or human playthrough.
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ADB=Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe')
PACKAGE='com.heartoftherain.verification'


def run():
    parser=argparse.ArgumentParser();parser.add_argument('--serial',required=True);parser.add_argument('--out',type=Path,default=ROOT/'Verification/Evidence/Fluidity/Touch');parser.add_argument('--suite',type=Path,default=ROOT/'Verification/Evidence/Fluidity/LDPlayer');args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    apk_hash=hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest()
    installation=json.loads((args.suite/'Installation.json').read_text())
    assert installation['sha256']==apk_hash,'The completed suite used an earlier APK; install and verify the final build before touch checks.'
    def command(*parts):return [str(ADB),'-s',args.serial,*map(str,parts)]
    def adb(*parts):return subprocess.run(command(*parts),capture_output=True,check=True,timeout=60).stdout
    def picture(name):
        path=out/(name+'.png');path.write_bytes(adb('exec-out','screencap','-p'));return path.name
    def tap(x,y,pause=.5):adb('shell','input','tap',x,y);time.sleep(pause)
    def launch():
        adb('shell','am','force-stop',PACKAGE);time.sleep(5)
        adb('shell','am','start','-n',PACKAGE+'/com.unity3d.player.UnityPlayerActivity');time.sleep(8)
    fresh=adb('shell','cat',f'/sdcard/Android/data/{PACKAGE}/files/Regression/Regression.json')
    assert json.loads(fresh)['status']=='PASS_NATIVE_REGRESSION','Finish native regression before driving touch.'
    assert adb('shell','wm','size').decode().strip().endswith('900x1600'),'Fixture expects the dedicated900x1600 phone.'
    report={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'serial':args.serial,
            'apk_sha256':apk_hash,
            'scope':'ADB single-finger input and actual emulator display captures. QA instance only; no physical/multitouch/human/performance certification. No data clear.', 'frames':[]}
    launch();report['frames'].append(picture('Home_Before'))
    held=subprocess.Popen(command('shell','input','swipe',810,1450,810,1450,700),stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(.25);report['frames'].append(picture('Navigation_Held'));held.communicate(timeout=10);time.sleep(.7)
    report['frames'].append(picture('Shop_After_Navigation'));tap(450,1450)
    tap(450,1234);report['frames'].append(picture('PreLevel_No_Items'));tap(450,1226,3)
    report['frames'].append(picture('Board_Before_Drag'))
    fixture=json.loads((ROOT/'Verification/Evidence/Fluidity/Touch_Fixture.json').read_text());a=fixture['from_screen_top_left'];b=fixture['to_screen_top_left']
    started=time.monotonic();drag=subprocess.Popen(command('shell','input','swipe',*a,*b,4000),stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(1.7);down_before_capture=drag.poll() is None;report['frames'].append(picture('Drag_Before_Finger_Up'));observed=time.monotonic()-started
    still_down=down_before_capture and drag.poll() is None
    drag.communicate(timeout=10);time.sleep(3);report['frames'].append(picture('Drag_Settled'))
    report['drag']={'fixture':fixture,'command_duration_ms':4000,'capture_elapsed_seconds':observed,'input_process_running_before_and_after_capture':still_down,
                    'visual_assertions':'Inspect the Moves counter and tile changes in Drag_Before_Finger_Up; this records before-release input evidence.'}
    assert still_down,'Input ended before the intended held-finger capture'
    launch();tap(450,1234);tap(188,934);report['frames'].append(picture('PreLevel_Rocket_Selected'));tap(450,1226,3)
    report['frames'].append(picture('Rocket_Before_Single_Tap'))
    recording=subprocess.Popen(command('shell','screenrecord','--time-limit','6','--bit-rate','6000000','/sdcard/HOTR_Fluidity_Touch.mp4'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(.6);tap(450,825,.15);report['frames'].append(picture('Rocket_One_Tap_015'))
    time.sleep(.3);report['frames'].append(picture('Rocket_One_Tap_045'));time.sleep(.4);report['frames'].append(picture('Rocket_One_Tap_090'))
    recording.communicate(timeout=15);adb('pull','/sdcard/HOTR_Fluidity_Touch.mp4',str(out/'Power_One_Tap.mp4'))
    report['power']={'adb_taps':1,'point':[450,825],'video':'Power_One_Tap.mp4','visual_assertions':'Compare the initial26 moves with25 after one tap; inspect rocket and refill in the native display/video.'}
    report['status']='CAPTURED_ACTUAL_ANDROID_INPUT_REQUIRES_VISUAL_REVIEW'
    (out/'Touch_Smoke.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'status':report['status'],'frames':len(report['frames']),'drag_finger_still_down':still_down},indent=2))


if __name__=='__main__':run()
