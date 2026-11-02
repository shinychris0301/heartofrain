"""Install and collect the explicit, unaccelerated development-player probe."""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import time
from pathlib import Path
from qa_android_target import validate_qa_target, assert_no_active_attempt, adb_endpoint

ROOT=Path(__file__).resolve().parents[2]
ADB=Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe')
PACKAGE='com.heartoftherain.verification'
REMOTE=f'/sdcard/Android/data/{PACKAGE}/files'


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--serial',required=True)
    parser.add_argument('--apk',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--no-install',action='store_true',help='Measure the already installed exact APK after a separately verified launch.')
    parser.add_argument('--variant',default='candidate',choices=['baseline','candidate','baseline_focus','candidate_focus','cache_focus','warm_focus'])
    args=parser.parse_args();target=validate_qa_target(args.serial,args.out);out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    def adb(*command,check=True):
        for attempt in range(3):
            result=subprocess.run([str(ADB),'-s',args.serial,*command],capture_output=True,timeout=90)
            if result.returncode and ('not found' in result.stderr.decode() or 'offline' in result.stderr.decode()):
                subprocess.run([str(ADB),'connect',adb_endpoint(args.serial)],capture_output=True,timeout=20);time.sleep(1);continue
            break
        if check and result.returncode:raise RuntimeError(result.stderr.decode() or result.stdout.decode())
        return result.stdout.decode('utf-8','replace').strip()
    started=dt.datetime.now(dt.timezone.utc)
    record={'utc':started.isoformat(),'sha256':hashlib.sha256(args.apk.read_bytes()).hexdigest(),'serial':args.serial,
            'qa_target':target,'apk':str(args.apk.resolve()),'scope':'Dedicated LDPlayer; ARM translation. No physical-device claim.'}
    record['attempt_guard']=assert_no_active_attempt(adb,PACKAGE)
    if args.no_install:
        remote=adb('shell','pm','path',PACKAGE).splitlines()[0].removeprefix('package:').strip()
        assert adb('shell','sha256sum',remote).split()[0]==record['sha256']
        record['install']='EXACT_INSTALLED_APK_HASH_VERIFIED_NO_REINSTALL'
    else:
        record['install']=adb('install','-r',str(args.apk.resolve()));assert 'Success' in record['install']
    adb('shell','am','force-stop',PACKAGE);time.sleep(5)
    adb('shell','wm','size','reset')
    marker=out/'HOTR_RunFluidity';marker.write_text(args.variant);record['variant']=args.variant
    adb('shell','mkdir','-p',REMOTE);adb('push',str(marker),REMOTE+'/HOTR_RunFluidity')
    adb('shell','am','start','-n',PACKAGE+'/com.unity3d.player.UnityPlayerActivity')
    (out/'Installation.json').write_text(json.dumps(record,indent=2)+'\n')
    deadline=time.monotonic()+260
    while time.monotonic()<deadline:
        body=adb('shell','cat',REMOTE+'/Fluidity/Measurement.json',check=False)
        try:
            report=json.loads(body)
            fresh=dt.datetime.fromisoformat(report['utc'].replace('Z','+00:00'))>=started
        except (ValueError,KeyError):report={};fresh=False
        if fresh and report.get('status')!='RUNNING':
            (out/'Measurement.json').write_text(json.dumps(report,indent=2)+'\n')
            assert report.get('isolatedProfile') and report.get('launchCleared'), 'Review requires an isolated profile and completed launch handoff'
            print(json.dumps({'status':report['status'],'phases':len(report['phases']),'errors':report['errors']},indent=2),flush=True)
            return 0 if report['status']=='RECORDED_NATIVE_FLUIDITY' else 1
        time.sleep(2)
    raise TimeoutError('No fresh probe report; inspect the dedicated emulator.')


if __name__=='__main__':raise SystemExit(run())
