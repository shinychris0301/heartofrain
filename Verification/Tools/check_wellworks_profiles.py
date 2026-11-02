"""Native short-phone/tablet rendering; restore the emulator's original size."""
import argparse,datetime as dt,hashlib,json,re,subprocess,sys,time
from pathlib import Path
from check_wellworks_device import ADB,BASE,PKG,ROOT
def run():
    p=argparse.ArgumentParser();p.add_argument('--serial',required=True);a=p.parse_args();out=ROOT/'Verification/Evidence/Wellworks';report=json.loads((out/'Device/Report.json').read_text());run_id=next(c['runId'] for c in report['cases'] if c['mode']=='Tap')
    def adb(*args):return subprocess.run([str(ADB),'-s',a.serial,*map(str,args)],check=True,capture_output=True,timeout=100).stdout
    def prefs():return hashlib.sha256(adb('exec-out','run-as',PKG,'cat','shared_prefs/com.heartoftherain.verification.v2.playerprefs.xml')).hexdigest()
    original=adb('shell','wm','size').decode();override=re.search(r'Override size: (\d+x\d+)',original);before=prefs();cases=[]
    try:
        for name,width,height in [('Compact',320,568),('Tablet',768,1024)]:
            adb('shell','am','force-stop',PKG);adb('shell','wm','size',f'{width}x{height}');time.sleep(1)
            subprocess.run([sys.executable,'-X','utf8',str(ROOT/'Verification/Tools/check_wellworks_device.py'),'--serial',a.serial,'--out',str(out/name),'--case','Restart','--run-id',run_id,'--keep-open','--allow-resolution-prefs'],check=True,timeout=150)
            # Actual panel drag, then Android Back. Native images are reviewed
            # explicitly; issuing input alone is not a visual pass.
            adb('shell','input','swipe',width//2,int(height*.65),width//2,int(height*.25),'500');time.sleep(.6);(out/name/'After_Scroll.png').write_bytes(adb('exec-out','screencap','-p'))
            adb('shell','input','keyevent','4');time.sleep(.6);(out/name/'After_Back.png').write_bytes(adb('exec-out','screencap','-p'));cases.append({'name':name,'width':width,'height':height,'native_restart':'PASS','scroll_and_back_input_sent':True})
    finally:
        adb('shell','am','force-stop',PKG);adb('shell','wm','size',override[1] if override else 'reset');adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity');time.sleep(6)
    result={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'PASS_NATIVE_WELLWORKS_PROFILE_CHECKS_REQUIRES_VISUAL_REVIEW','apk_sha256':report['apk_sha256'],'original_wm_size':original,'restored_wm_size':adb('shell','wm','size').decode(),'preferences_before':before,'preferences_after':prefs(),'cases':cases};assert result['original_wm_size']==result['restored_wm_size'] and result['preferences_before']==result['preferences_after'];(out/'Device_Profiles.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':run()
