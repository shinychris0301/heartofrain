"""Install/review branding on QA2 only, preserving all app saves/preferences."""
import argparse,hashlib,json,re,subprocess,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/LaunchRuStoreR3'
ADB=Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
CONSOLE=Path(r'E:\LDPlayer\LDPlayer14\ldconsole.exe')
PKG='com.heartoftherain.verification'
BASE=f'/sdcard/Android/data/{PKG}/files'
APK=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
SERIAL='emulator-5558'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--install',action='store_true');args=parser.parse_args()
 rows=subprocess.check_output([str(CONSOLE),'list2'],timeout=20).decode().strip()
 assert rows.splitlines()[0].startswith('0,LDPlayer,0,0,0,-1,-1,')
 assert rows.splitlines()[1].startswith('1,Heart of the Rain QA,0,0,0,-1,-1,')
 assert rows.splitlines()[2].startswith('2,Heart of the Rain QA79 isolated,')
 prior=json.loads((ROOT/'Verification/Evidence/Gameplay79/QA_Target.json').read_text('utf-8'))
 assert prior['target']=={'index':2,'serial':SERIAL,'name':'Heart of the Rain QA79 isolated'}
 def adb(*cmd):return subprocess.check_output([str(ADB),'-s',SERIAL,*map(str,cmd)],timeout=120)
 assert adb('get-state').strip()==b'device'
 profile=json.loads(json.loads(adb('shell','cat',BASE+'/Profiles/Development-v1/profile.json'))['payload'])
 assert not any(a['state'] in ('Started','Reserved') for a in profile['attempts']),'Preserve the active QA2 attempt; do not install/stop/launch'
 def state():
  prefs={n:adb('shell','run-as',PKG,'sha256sum','shared_prefs/'+n).decode().split()[0] for n in adb('shell','run-as',PKG,'ls','shared_prefs').decode().split() if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',n)}
  names=adb('shell','find',BASE+'/Profiles','-type','f','-name','*.json').decode().splitlines()
  saves={n.removeprefix(BASE+'/'):adb('shell','sha256sum',n).decode().split()[0] for n in names if re.fullmatch(re.escape(BASE)+r'/Profiles/[A-Za-z0-9_./-]+\.json',n)}
  return {'preferences':prefs,'saves':saves}
 before=state();folder=OUT/'Android';folder.mkdir(parents=True,exist_ok=True)
 target={'status':'AUTHORIZED_ISOLATED_RUSSIAN_LAUNCH80_QA','utc':datetime.now(timezone.utc).isoformat(),'serial':SERIAL,'index':2,'name':prior['target']['name'],'priorTargetSHA256':sha(ROOT/'Verification/Evidence/Gameplay79/QA_Target.json'),'activeAttempts':0,'mainAndOriginalQAStopped':True,'list2':rows}
 target_path=OUT/'QA_Target.json'
 assert not target_path.exists(),'Preserve the earlier target/audit before another device run'
 target_path.write_text(json.dumps(target,indent=2)+'\n',encoding='utf-8')
 remote=adb('shell','pm','path',PKG).decode().splitlines()[0].removeprefix('package:').strip()
 old_sha=adb('shell','sha256sum',remote).decode().split()[0]
 assert old_sha==json.loads((OUT/'Baseline79.json').read_text('utf-8'))['apkSHA256'],'Unexpected installed QA2 APK; preserve it before replacement'
 result={'utc':datetime.now(timezone.utc).isoformat(),'serial':SERIAL,'targetSHA256':sha(target_path),'before':before,'installedBeforeSHA256':old_sha,'apk_sha256':sha(APK),'source_sha256':sha(OUT/'Source_SHA256.json'),'activeAttempts':0,'scope':'QA2 only; normal startup/first-time menu taps without choosing a language or advancing the tutorial. Original active QA1 and main remain stopped and untouched. No reset, save replacement, service or physical-device claim.'}
 error=None
 try:
  if args.install:
   result['install']=adb('install','-r',APK).decode().strip();assert 'Success' in result['install'] and state()==before
  # A replacement install changes the APK path; resolve it again before hashing.
  current=adb('shell','pm','path',PKG).decode().splitlines()[0].removeprefix('package:').strip()
  result['installed_apk_sha256']=adb('shell','sha256sum',current).decode().split()[0]
  assert result['installed_apk_sha256']==result['apk_sha256']
  adb('shell','am','force-stop',PKG);time.sleep(2)
  video=subprocess.Popen([str(ADB),'-s',SERIAL,'shell','screenrecord','--size','720x1280','--bit-rate','8000000','--time-limit','12','/sdcard/HOTR_RussianLaunch80.mp4'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
  time.sleep(.6)
  result['launch']=adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity').decode()
  stdout,stderr=video.communicate(timeout=25);assert video.returncode==0,stderr.decode()
  adb('pull','/sdcard/HOTR_RussianLaunch80.mp4',folder/'Cold_Start.mp4')
  (folder/'FirstStart_Russian.png').write_bytes(adb('exec-out','screencap','-p'))
  size=adb('shell','wm','size').decode();match=re.search(r'(\d+)x(\d+)',size);width,height=map(int,match.groups());assert width<height
  adb('shell','input','tap',round(width*.18),round(height*.045));time.sleep(.7)
  (folder/'FirstStart_Language_Menu.png').write_bytes(adb('exec-out','screencap','-p'))
  assert state()==before,'Opening the language menu changed saved data'
  # Clear this UI-only menu through a normal process restart; select no language.
  adb('shell','am','force-stop',PKG);time.sleep(2)
  adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity');time.sleep(6)
  pid=adb('shell','pidof',PKG).decode().strip();assert re.fullmatch('[0-9]+',pid)
  logs=adb('logcat','-d','--pid='+pid,'-v','brief').decode('utf-8','replace')
  (folder/'Runtime.log').write_text(logs,encoding='utf-8')
  result['runtime_errors']=len(re.findall('FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException',logs));assert result['runtime_errors']==0
  result['pid']=pid;result['portrait']=True
 except Exception as exc:
  error=exc;result['error']=str(exc)
 finally:
  result['after']=state();result['data_unchanged']=result['after']==before;result['finishedUtc']=datetime.now(timezone.utc).isoformat()
  result['status']='PASS_RUSSIAN_LAUNCH80_DEVICE_AUDIT' if error is None and result['data_unchanged'] else 'FAIL_RUSSIAN_LAUNCH80_DEVICE_AUDIT'
  (folder/'Installation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 assert result['data_unchanged'],'QA2 saved data changed'
 if error is not None:raise error
 print(json.dumps({k:result[k] for k in ('status','apk_sha256','data_unchanged','portrait','runtime_errors')}))
if __name__=='__main__':main()
