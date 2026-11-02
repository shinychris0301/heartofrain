"""Replace-install the RainCup review APK; retain preferences and real profiles."""
import argparse,datetime as dt,hashlib,json,re,subprocess,time
from pathlib import Path
from check_rain_cup_device import ADB,BASE,PKG,ROOT

def run():
    p=argparse.ArgumentParser();p.add_argument('--serial',required=True);a=p.parse_args();out=ROOT/'Verification/Evidence/RainCup';out.mkdir(exist_ok=True)
    def adb(*args,check=True):return subprocess.run([str(ADB),'-s',a.serial,*map(str,args)],check=check,capture_output=True,timeout=120).stdout
    subprocess.run([str(ADB),'connect',a.serial],check=True,capture_output=True)
    def prefs():return {n:hashlib.sha256(adb('exec-out','run-as',PKG,'cat','shared_prefs/'+n)).hexdigest() for n in adb('shell','run-as',PKG,'ls','shared_prefs').decode().split() if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',n)}
    def saves():return {n.removeprefix(BASE+'/'):adb('shell','sha256sum',n).decode().split()[0] for n in adb('shell','find',BASE+'/Profiles','-type','f','-name','*.json').decode().splitlines() if re.fullmatch(re.escape(BASE)+r'/Profiles/[A-Za-z0-9_./-]+\.json',n)}
    apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk';sha=hashlib.sha256(apk.read_bytes()).hexdigest();freeze=json.loads((out/'Player_Source_SHA256.json').read_text());assert freeze['apk_sha256']==sha
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in freeze['files'].items())
    adb('shell','am','force-stop',PKG);time.sleep(2);before=prefs();saved=saves();install=adb('install','-r',apk).decode();assert 'Success' in install
    adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity');time.sleep(8)
    pid=adb('shell','pidof',PKG).decode().strip();remote=adb('shell','pm','path',PKG).decode().splitlines()[0].removeprefix('package:').strip();assert pid and adb('shell','sha256sum',remote).decode().split()[0]==sha
    after=prefs();saved_after=saves();report={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'PRESERVATION_REVIEW_REQUIRED','serial':a.serial,'apk_sha256':sha,'apk_bytes':apk.stat().st_size,'pid':pid,'install':install.strip(),'preferences_before':before,'preferences_after':after,'player_saves_before':saved,'player_saves_after':saved_after,'scope':'Replacement install without data clear. Hashes only; no preference/save contents exported. Emulator observation, not physical-device certification.'}
    name='QA' if a.serial.endswith(':5557') else 'Main';(out/(name+'_Installation.json')).write_text(json.dumps(report,indent=2)+'\n');assert before==after and saved==saved_after,'Ordinary data changed across install'
    report['status']='PASS_APK_INSTALLED_DATA_PRESERVED';(out/(name+'_Installation.json')).write_text(json.dumps(report,indent=2)+'\n');(out/(name+'_Home.png')).write_bytes(adb('exec-out','screencap','-p'));print(json.dumps({'serial':a.serial,'status':report['status'],'pid':pid}))

if __name__=='__main__':run()
