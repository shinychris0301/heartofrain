"""Run explicit, isolated crate fixtures; never clear a profile or send screen taps."""
import argparse,hashlib,json,re,subprocess,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/CrateBurst/Android'
ADB=Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
APK=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
PKG='com.heartoftherain.verification'
BASE=f'/sdcard/Android/data/{PKG}/files'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--serial',required=True);parser.add_argument('--variant',required=True);parser.add_argument('--install',action='store_true');args=parser.parse_args()
    assert re.fullmatch(r'(baseline|candidate|visual)_[A-Za-z0-9_]+',args.variant)
    folder=OUT/args.variant;folder.mkdir(parents=True,exist_ok=True)
    def adb(*cmd,check=True):return subprocess.run([str(ADB),'-s',args.serial,*map(str,cmd)],capture_output=True,check=check,timeout=180).stdout
    def state():
        names=adb('shell','run-as',PKG,'ls','shared_prefs').decode().split()
        prefs={n:adb('shell','run-as',PKG,'sha256sum','shared_prefs/'+n).decode().split()[0] for n in names if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',n)}
        names=adb('shell','find',BASE+'/Profiles','-type','f','-name','*.json',check=False).decode().splitlines()
        saves={n.removeprefix(BASE+'/'):adb('shell','sha256sum',n).decode().split()[0] for n in names if re.fullmatch(re.escape(BASE)+r'/Profiles/[A-Za-z0-9_./-]+\.json',n)}
        return {'preferences':prefs,'saves':saves}
    subprocess.run([str(ADB),'connect',args.serial],check=True,capture_output=True)
    assert adb('get-state').strip()==b'device'
    adb('shell','am','force-stop',PKG);before=state();utc=datetime.now(timezone.utc).isoformat()
    sha=hashlib.sha256(APK.read_bytes()).hexdigest();install=None
    if args.install:
        install=adb('install','-r',APK).decode().strip();assert 'Success' in install
        assert state()==before,'Replacement install changed profile data'
    remote=adb('shell','pm','path',PKG).decode().splitlines()[0].removeprefix('package:').strip()
    installed=adb('shell','sha256sum',remote).decode().split()[0];assert installed==sha,'Wrong APK installed'
    adb('shell','mkdir','-p',BASE)
    request=ROOT/'.verification-cache/CrateBurst/Request';request.parent.mkdir(parents=True,exist_ok=True);request.write_text(args.variant,'ascii')
    adb('shell','rm','-f',BASE+'/CrateBurst/Report.json')
    adb('push',request,BASE+'/HOTR_RunCrateBurst')
    launch=adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity').decode().strip()
    deadline=time.monotonic()+260
    while time.monotonic()<deadline:
        raw=adb('shell','cat',BASE+'/CrateBurst/Report.json',check=False)
        try:report=json.loads(raw)
        except (ValueError,UnicodeError):time.sleep(2);continue
        if report['status']!='RUNNING':break
        time.sleep(2)
    else:raise TimeoutError('Crate fixture report unavailable')
    (folder/'Report.json').write_bytes(raw)
    assert report['status']=='PASS_CRATE_BURST_PLAYBACK' and not report['errors'] and len(report['rows'])==6,report['errors']
    assert datetime.fromisoformat(report['utc'].replace('Z','+00:00'))>=datetime.fromisoformat(utc),'Stale report'
    after=state();assert before==after,'Isolated board altered user data'
    foreground=[x.strip() for x in adb('shell','dumpsys','activity','activities').decode(errors='replace').splitlines() if 'ResumedActivity' in x and PKG in x]
    pid=adb('shell','pidof',PKG).decode().strip();logs=adb('logcat','-d','--pid='+pid,'-v','brief').decode(errors='replace')
    errors=len(re.findall(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException',logs));assert errors==0
    result={'utc':utc,'serial':args.serial,'apk_sha256':sha,'installed_apk_sha256':installed,'install':install,'launch':launch,'variant':args.variant,'before':before,'after':after,'data_unchanged':True,'foreground':foreground,'runtime_errors':errors,'scope':'Isolated fixture board; no attempt/progression callbacks, no screen taps or data clear. Visual run is excluded from timing comparisons.'}
    (folder/'Installation.json').write_text(json.dumps(result,indent=2)+'\n','utf-8')
    print(json.dumps({'variant':args.variant,'status':report['status'],'data_unchanged':True,'renderers_created':sum(r['renderersCreated'] for r in report['rows']),'crate_sprites_created':sum(r['crateSpritesCreated'] for r in report['rows'])}))

if __name__=='__main__':main()
