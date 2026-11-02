"""Exercise portrait launch/resume across temporary QA display profiles.

No app-data reset. Restore display and rotation settings in finally, including
after a failed assertion. Native screenshots/configuration are retained.
"""
import argparse
import datetime as dt
import hashlib
import io
import json
import re
import subprocess
import time
from pathlib import Path
from PIL import Image
import numpy as np
from capture_gameplay_comparison import ADB, ROOT

PACKAGE='com.heartoftherain.verification'
ACTIVITY=PACKAGE+'/com.unity3d.player.UnityPlayerActivity'

def run():
    parser=argparse.ArgumentParser();parser.add_argument('--serial',required=True);args=parser.parse_args()
    out=ROOT/'Verification/Evidence/Portrait/DeviceMatrix';out.mkdir(parents=True,exist_ok=True)
    def adb(*parts):return subprocess.run([ADB,'-s',args.serial,*map(str,parts)],capture_output=True,check=True,timeout=90).stdout
    def text(*parts):return adb(*parts).decode('utf-8','replace').strip()
    size=text('shell','wm','size');density=text('shell','wm','density')
    override=re.search(r'Override size:\s*(\d+x\d+)',size)
    old_rotation={k:text('shell','settings','get','system',k) for k in ['accelerometer_rotation','user_rotation']}
    apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk';sha=hashlib.sha256(apk.read_bytes()).hexdigest()
    remote=text('shell','pm','path',PACKAGE).splitlines()[0].removeprefix('package:').strip()
    assert text('shell','sha256sum',remote).split()[0]==sha,'Install the final portrait APK before this test.'
    report={'status':'RUNNING','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'serial':args.serial,'apk_sha256':sha,'original_size':size,'original_density':density,'original_rotation':old_rotation,'cases':[],'failures':[],
            'scope':'Actual Android launch, ADB page input, rotation preference and background/resume checks on temporary emulator profiles. Not physical sensors, foldable certification or a frame-budget test.'}
    def launch():
        adb('shell','am','force-stop',PACKAGE);time.sleep(3)
        adb('shell','am','start','-W','-n',ACTIVITY);time.sleep(5)
    def capture(name):
        body=adb('exec-out','screencap','-p');path=out/(name+'.png');path.write_bytes(body);w,h=Image.open(io.BytesIO(body)).size
        activity=text('shell','dumpsys','activity','activities');(out/(name+'_Activity.txt')).write_text(activity,encoding='utf-8',newline='\n')
        row={'name':name,'width':w,'height':h,'portrait_display':h>w,'sha256':hashlib.sha256(body).hexdigest(),'frame':path.name}
        report['cases'].append(row)
        if not row['portrait_display']:raise AssertionError(name+' rendered a landscape display; inspect native activity bounds before treating letterboxing as a failure.')
        return path
    def tap_green_button(path):
        # Select the large green action button from the real rendered page,
        # rather than assuming its Y coordinate is constant across aspect ratios.
        pixels=np.asarray(Image.open(path).convert('RGB')).astype(np.int16);h,w=pixels.shape[:2]
        green=(pixels[:,:,1]>110)&(pixels[:,:,1]>pixels[:,:,0]*1.4)&(pixels[:,:,1]>pixels[:,:,2]*1.4)
        rows=np.flatnonzero((green.sum(axis=1)>w*.25)&(np.arange(h)>h*.5))
        bands=np.split(rows,np.flatnonzero(np.diff(rows)>1)+1)
        bands=[b for b in bands if len(b)>max(10,h*.012)]
        if not bands:raise AssertionError('No large green action button on '+path.name)
        band=max(bands,key=lambda b:len(b));ys,xs=np.nonzero(green[band[0]:band[-1]+1]);point=(int(np.median(xs)),int((band[0]+band[-1])/2))
        adb('shell','input','tap',*point);return point
    try:
        for name,profile in [('Phone','reset'),('TallPhone','1080x2400'),('TabletPortrait','1200x1920'),('TabletLandscape','1920x1200')]:
            adb('shell','wm','size',profile);adb('shell','settings','put','system','accelerometer_rotation','0');adb('shell','settings','put','system','user_rotation','0');time.sleep(2)
            launch();home=capture(name+'_Home')
            # Cold launch follows the real saved onboarding state; suite evidence
            # separately covers story/tutorial without resetting these settings.
            tap_green_button(home);time.sleep(1);pre_level=capture(name+'_PreLevel')
            tap_green_button(pre_level);time.sleep(4);capture(name+'_Gameplay')
            for rotation in [1,3]:
                adb('shell','settings','put','system','user_rotation',str(rotation));time.sleep(1);capture(name+'_Rotation'+str(rotation))
            adb('shell','am','start','-a','android.intent.action.MAIN','-c','android.intent.category.HOME');time.sleep(2)
            adb('shell','am','start','-W','-n',ACTIVITY);time.sleep(3);capture(name+'_Resume')
    except Exception as ex:report['failures'].append(str(ex))
    finally:
        adb('shell','wm','size',override.group(1) if override else 'reset')
        for key,value in old_rotation.items():
            if value=='null':adb('shell','settings','delete','system',key)
            else:adb('shell','settings','put','system',key,value)
        report['restored_size']=text('shell','wm','size');report['restored_density']=text('shell','wm','density');report['restored_rotation']={k:text('shell','settings','get','system',k) for k in old_rotation}
        report['restored']=report['restored_size']==size and report['restored_density']==density and report['restored_rotation']==old_rotation
        if not report['restored']:report['failures'].append('Display/rotation restoration differs; inspect before delivery.')
        launch()
        report['status']='CAPTURED_PORTRAIT_DEVICE_MATRIX_REQUIRES_VISUAL_REVIEW' if not report['failures'] else 'FAIL_NATIVE_PORTRAIT_DEVICE_MATRIX'
        (out/'Report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'status':report['status'],'cases':len(report['cases']),'failures':report['failures'],'restored':report['restored']},indent=2))
    if report['failures']:raise SystemExit(1)

if __name__=='__main__':run()
