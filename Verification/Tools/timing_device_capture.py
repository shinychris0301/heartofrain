"""Actual Android rejection and blast-to-rocket captures after the final suite."""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from capture_gameplay_comparison import ADB, ROOT

PACKAGE='com.heartoftherain.verification'

def run():
    p=argparse.ArgumentParser();p.add_argument('--serial',required=True);a=p.parse_args()
    base=ROOT/'Verification/Evidence/Timing';out=base/'Touch';out.mkdir(parents=True,exist_ok=True)
    sha=hashlib.sha256((ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk').read_bytes()).hexdigest()
    install=json.loads((base/'LDPlayer/Installation.json').read_text());assert install['sha256']==sha
    touch=json.loads((out/'Touch_Smoke.json').read_text());assert touch['apk_sha256']==sha
    def adb(*args):return subprocess.check_output([ADB,'-s',a.serial,*map(str,args)],timeout=60)
    def shot(name):(out/(name+'.png')).write_bytes(adb('exec-out','screencap','-p'))
    def tap(x,y):adb('shell','input','tap',x,y);time.sleep(1)
    def level(items):
        adb('shell','am','force-stop',PACKAGE);time.sleep(5)
        adb('shell','am','start','-n',PACKAGE+'/com.unity3d.player.UnityPlayerActivity');time.sleep(8)
        tap(450,1234)
        if items:tap(188,934);tap(363,934)
        shot('Chain_Selections' if items else 'Invalid_PreLevel')
        tap(450,1226);time.sleep(3)
        shot('Chain_Board_Before' if items else 'Invalid_Board_Before')
    def capture(name,*action):
        subprocess.run([sys.executable,'-X','utf8',str(ROOT/'Verification/Tools/capture_gameplay_comparison.py'),'--serial',a.serial,'record',name,'--out',str(out),'--seconds','8',*map(str,action)],check=True)
        subprocess.run([sys.executable,'-X','utf8',str(ROOT/'Verification/Tools/capture_gameplay_comparison.py'),'--serial',a.serial,'sheet',name,'--out',str(out),'--fps','24','--end','3'],check=True)
    level(False);capture('HR_Invalid_Swap','--swipe',75,825,170,825,180);shot('Invalid_Board_After')
    level(True);capture('HR_Bomb_Triggers_Rocket','--tap',450,919);shot('Chain_Board_After')
    report={'status':'CAPTURED_REQUIRES_VISUAL_REVIEW','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'apk_sha256':sha,'serial':a.serial,'scope':'Actual ADB single-finger input, native Android screenrecord and display PNGs. No data clear. Video dispatch clock is not synchronized to input or display latency.','videos':['HR_Invalid_Swap.mp4','HR_Bomb_Triggers_Rocket.mp4']}
    (out/'Timing_Video_Review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':run()
