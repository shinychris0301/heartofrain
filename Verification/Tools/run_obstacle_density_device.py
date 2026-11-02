"""Run explicit, isolated fixed-density fixtures; never clear a profile or send screen taps."""
import argparse,hashlib,json,re,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
from qa_android_target import validate_qa_target, assert_no_active_attempt

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/ObstacleDensity/Android'
ADB=Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
APK=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
PKG='com.heartoftherain.verification'
BASE=f'/sdcard/Android/data/{PKG}/files'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--serial',required=True);parser.add_argument('--variant',required=True);parser.add_argument('--install',action='store_true');parser.add_argument('--out',type=Path,default=OUT,help='Evidence folder; one subfolder per variant.');args=parser.parse_args()
    target=validate_qa_target(args.serial,args.out)
    assert re.fullmatch(r'(baseline|candidate|visual|paired)_[A-Za-z0-9_]+(-(crate|stone|gate|tiles))?',args.variant)
    folder=args.out.resolve()/args.variant;folder.mkdir(parents=True,exist_ok=True)
    def adb(*cmd,check=True):return subprocess.run([str(ADB),'-s',args.serial,*map(str,cmd)],capture_output=True,check=check,timeout=180).stdout
    def state():
        names=adb('shell','run-as',PKG,'ls','shared_prefs').decode().split()
        prefs={n:adb('shell','run-as',PKG,'sha256sum','shared_prefs/'+n).decode().split()[0] for n in names if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',n)}
        names=adb('shell','find',BASE+'/Profiles','-type','f','-name','*.json',check=False).decode().splitlines()
        saves={n.removeprefix(BASE+'/'):adb('shell','sha256sum',n).decode().split()[0] for n in names if re.fullmatch(re.escape(BASE)+r'/Profiles/[A-Za-z0-9_./-]+\.json',n)}
        return {'preferences':prefs,'saves':saves}
    assert adb('get-state').strip()==b'device'
    attempt_guard=assert_no_active_attempt(adb,PKG)
    adb('shell','am','force-stop',PKG);before=state();utc=datetime.now(timezone.utc).isoformat()
    sha=hashlib.sha256(APK.read_bytes()).hexdigest();install=None
    if args.install:
        install=adb('install','-r',APK).decode().strip();assert 'Success' in install
        assert state()==before,'Replacement install changed profile data'
    for attempt in range(10):
        package_paths=adb('shell','pm','path',PKG).decode().splitlines()
        if package_paths:break
        time.sleep(1)
    else:raise RuntimeError('QA package manager did not expose the installed app; no measurement started')
    remote=package_paths[0].removeprefix('package:').strip()
    installed=adb('shell','sha256sum',remote).decode().split()[0];assert installed==sha,'Wrong APK installed'
    adb('shell','mkdir','-p',BASE)
    request=ROOT/'.verification-cache/ObstacleDensity/Request';request.parent.mkdir(parents=True,exist_ok=True);request.write_text(args.variant,'ascii')
    adb('shell','rm','-f',BASE+'/ObstacleDensity/Report.json')
    adb('push',request,BASE+'/HOTR_RunObstacleDensity')
    launch=adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity').decode().strip()
    deadline=time.monotonic()+400
    while time.monotonic()<deadline:
        raw=adb('shell','cat',BASE+'/ObstacleDensity/Report.json',check=False)
        try:report=json.loads(raw)
        except (ValueError,UnicodeError):time.sleep(2);continue
        if report['status']!='RUNNING':break
        time.sleep(2)
    else:raise TimeoutError('Crate fixture report unavailable')
    (folder/'Report.json').write_bytes(raw)
    paired=args.variant.startswith('paired_')
    assert report['status']=='PASS_OBSTACLE_DENSITY_PLAYBACK' and not report['errors'] and len(report['rows'])==(16 if paired else 10),report['errors']
    if paired:
        for a,b in zip(report['rows'][::2],report['rows'][1::2]):
            assert a['checkpoint75Transform']!=b['checkpoint75Transform']
            assert (a['turnHash'],a['finalHash'],a['crates'])==(b['turnHash'],b['finalHash'],b['crates'])
        assert sum(r['checkpoint75Transform'] for r in report['rows'])==8
    assert datetime.fromisoformat(report['utc'].replace('Z','+00:00'))>=datetime.fromisoformat(utc),'Stale report'
    after=state();assert before==after,'Isolated board altered user data'
    foreground=[x.strip() for x in adb('shell','dumpsys','activity','activities').decode(errors='replace').splitlines() if 'ResumedActivity' in x and PKG in x]
    pid=adb('shell','pidof',PKG).decode().strip();logs=adb('logcat','-d','--pid='+pid,'-v','brief').decode(errors='replace')
    errors=len(re.findall(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException',logs));assert errors==0
    result={'utc':utc,'serial':args.serial,'apk_sha256':sha,'installed_apk_sha256':installed,'install':install,'launch':launch,'variant':args.variant,'before':before,'after':after,'data_unchanged':True,'foreground':foreground,'runtime_errors':errors,'scope':'Isolated fixture board; no attempt/progression callbacks, no screen taps or data clear. Visual run is excluded from timing comparisons.'}
    result['qa_target']=target;result['attempt_guard']=attempt_guard
    (folder/'Installation.json').write_text(json.dumps(result,indent=2)+'\n','utf-8')
    print(json.dumps({'variant':args.variant,'status':report['status'],'data_unchanged':True,'renderers_created':sum(r['renderersCreated'] for r in report['rows']),'crate_sprites_created':sum(r['crateSpritesCreated'] for r in report['rows'])}))

if __name__=='__main__':main()
