"""QA-only native continuation/UI checks with isolated in-memory profiles."""
import argparse,hashlib,json,re,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/NoMovesR2/Android'
ADB=Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
PKG='com.heartoftherain.verification';BASE=f'/sdcard/Android/data/{PKG}/files'
APK=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
def main():
    p=argparse.ArgumentParser();p.add_argument('--serial',default='emulator-5556');p.add_argument('--install',action='store_true');p.add_argument('--evidence',default='RepeatMoves',choices=['NoMovesR2','RepeatMoves','NoMovesR3','ShopBounds']);args=p.parse_args();assert args.serial=='emulator-5556','Dedicated QA instance only'
    global OUT
    OUT=ROOT/'Verification/Evidence'/args.evidence/'Android'
    OUT.mkdir(parents=True,exist_ok=True)
    def adb(*cmd,check=True):return subprocess.run([str(ADB),'-s',args.serial,*map(str,cmd)],capture_output=True,check=check,timeout=150).stdout
    def state():
        prefs={n:adb('shell','run-as',PKG,'sha256sum','shared_prefs/'+n).decode().split()[0] for n in adb('shell','run-as',PKG,'ls','shared_prefs').decode().split() if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',n)}
        names=adb('shell','find',BASE+'/Profiles','-type','f','-name','*.json').decode().splitlines();saves={n.removeprefix(BASE+'/'):adb('shell','sha256sum',n).decode().split()[0] for n in names if re.fullmatch(re.escape(BASE)+r'/Profiles/[A-Za-z0-9_./-]+\.json',n)}
        return {'preferences':prefs,'saves':saves}
    assert adb('get-state').strip()==b'device'
    profile=json.loads(json.loads(adb('shell','cat',BASE+'/Profiles/Development-v1/profile.json'))['payload']);assert not any(a['state'] in ['Started','Reserved'] for a in profile['attempts']),'Do not interrupt an active QA attempt'
    adb('shell','am','force-stop',PKG);before=state();(OUT/'Before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8');sha=hashlib.sha256(APK.read_bytes()).hexdigest();install=None
    if args.install:
        install=adb('install','-r',APK).decode().strip();assert 'Success' in install and state()==before
    remote=adb('shell','pm','path',PKG).decode().splitlines()[0].removeprefix('package:').strip();assert adb('shell','sha256sum',remote).decode().split()[0]==sha
    fixtures=json.loads((OUT.parent/'Device_Fixtures.json').read_text())['entries'];cases=[];began=datetime.now(timezone.utc).isoformat()
    for fixture in fixtures:
        name=fixture['scenario'];folder=OUT/name;folder.mkdir(parents=True,exist_ok=True);adb('shell','am','force-stop',PKG)
        request=ROOT/'.verification-cache/NoMovesR2/DeviceRequest.json';request.parent.mkdir(parents=True,exist_ok=True);request.write_text(json.dumps(fixture,ensure_ascii=True),'utf-8')
        adb('shell','rm','-f',BASE+'/NoMovesR2Device/Report.json');adb('push',request,BASE+'/HOTR_RunNoMovesR2')
        started=datetime.now(timezone.utc);adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity')
        deadline=time.monotonic()+175;sent=set();captures=[]
        while time.monotonic()<deadline:
            raw=adb('shell','cat',BASE+'/NoMovesR2Device/Report.json',check=False)
            try:r=json.loads(raw)
            except (ValueError,UnicodeError):time.sleep(.6);continue
            assert datetime.fromisoformat(r['utc'].replace('Z','+00:00'))>=started,'Stale report'
            if r['status'] in ['READY_FOR_TAP','READY_FOR_REPEAT','READY_TO_END'] and r['status'] not in sent:
                frame=r['status']+'.png';(folder/frame).write_bytes(adb('exec-out','screencap','-p'));captures.append(frame)
                adb('shell','input','tap',r['x'],r['y']);sent.add(r['status'])
            if r['status']=='READY_FOR_SCROLL' and r['status'] not in sent:
                frame=r['status']+'.png';(folder/frame).write_bytes(adb('exec-out','screencap','-p'));captures.append(frame)
                adb('shell','input','swipe',r['x'],r['y'],r['endX'],r['endY'],650);sent.add(r['status'])
            if r['status']=='READY_FOR_BACK' and r['status'] not in sent:
                frame=r['status']+'.png';(folder/frame).write_bytes(adb('exec-out','screencap','-p'));captures.append(frame)
                adb('shell','input','tap',r['x'],r['y']);sent.add(r['status'])
            if r['status'].startswith(('PASS','FAIL')):break
            time.sleep(.6)
        else:raise TimeoutError(name+' did not finish')
        (folder/'Report.json').write_bytes(raw);assert r['status']=='PASS_ANDROID_NO_MOVES' and not r['error'],r.get('error')
        frame='After.png';(folder/frame).write_bytes(adb('exec-out','screencap','-p'));captures.append(frame)
        assert state()==before,'Isolated fixture changed real saved state'
        cases.append({'scenario':name,'report':r,'actual_ui_taps':len(sent-{'READY_FOR_SCROLL'}),'actual_ui_swipes':int('READY_FOR_SCROLL' in sent),'frames':captures})
        print(json.dumps({'scenario':name,'status':r['status'],'coins':r['coins'],'moves':r['moves'],'lives':r['lives']}),flush=True)
    adb('shell','am','force-stop',PKG)
    assert state()==before
    result={'status':'PASS_ANDROID_SHOP_BOUNDS' if args.evidence=='ShopBounds' else 'PASS_ANDROID_NO_MOVES_R3' if args.evidence=='NoMovesR3' else 'PASS_ANDROID_REPEAT_MOVES' if args.evidence=='RepeatMoves' else 'PASS_ANDROID_NO_MOVES_SIX_CASES','utc':began,'serial':args.serial,'apk_sha256':sha,'install':install,'cases':cases,'before':before,'after':state(),'data_unchanged':True,'scope':'Native Android/UGUI with actual ADB button taps. ShopBounds includes a real swipe to the last coin pack, native containment checks and Back to the preserved offer. Other fixtures retain their existing scope. Before-scene opt-in seeds memory-only profiles with a fixed test clock. No owner attempt, store payment or persistent profile substitution.'}
    # Marker is consumed; return QA to its ordinary real Home after the probes.
    adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity')
    time.sleep(12)
    assert state()==before,'Ordinary startup changed the QA saved profile'
    (OUT/'Ordinary_Home.png').write_bytes(adb('exec-out','screencap','-p'))
    result['ordinary_startup_data_unchanged']=True
    (OUT/'Summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'cases':len(cases),'real_data_unchanged':True}))
if __name__=='__main__':main()
