"""QA-only broad gameplay review, guarding real saves around every fixture tool."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from qa_android_target import DEFAULT_SERIAL, validate_qa_target

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/Gameplay72/Android'
ADB=Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
PKG='com.heartoftherain.verification'
BASE=f'/sdcard/Android/data/{PKG}/files'
APK=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'

def main():
    global OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--serial',default=DEFAULT_SERIAL,help='Existing QA by default; QA79 clone requires its sealed authorization record.')
    parser.add_argument('--install',action='store_true')
    parser.add_argument('--only',nargs='*')
    parser.add_argument('--out',type=Path,default=OUT.parent,help='Checkpoint evidence root; device stages are stored in its Android subdirectory')
    args=parser.parse_args()
    target=validate_qa_target(args.serial,args.out)
    OUT=args.out.resolve()/'Android'
    assert OUT.is_relative_to((ROOT/'Verification/Evidence').resolve()),'Evidence must stay in the workspace evidence directory'
    OUT.mkdir(parents=True,exist_ok=True)
    def adb(*cmd):
        return subprocess.check_output([str(ADB),'-s',args.serial,*map(str,cmd)],timeout=180)
    def state():
        prefs={name:adb('shell','run-as',PKG,'sha256sum','shared_prefs/'+name).decode().split()[0] for name in adb('shell','run-as',PKG,'ls','shared_prefs').decode().split() if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',name)}
        names=adb('shell','find',BASE+'/Profiles','-type','f','-name','*.json').decode().splitlines()
        saves={name.removeprefix(BASE+'/'):adb('shell','sha256sum',name).decode().split()[0] for name in names if re.fullmatch(re.escape(BASE)+r'/Profiles/[A-Za-z0-9_./-]+\.json',name)}
        return {'preferences':prefs,'saves':saves}
    assert adb('get-state').strip()==b'device'
    profile=json.loads(json.loads(adb('shell','cat',BASE+'/Profiles/Development-v1/profile.json'))['payload'])
    assert not any(a['state'] in ['Started','Reserved'] for a in profile['attempts']),'Keep an active QA attempt intact'
    adb('shell','am','force-stop',PKG)
    before=state()
    (OUT/'Before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
    install=None
    if args.install:
        install=adb('install','-r',APK).decode().strip()
        assert 'Success' in install and state()==before
    digest=hashlib.sha256(APK.read_bytes()).hexdigest()
    remote=adb('shell','pm','path',PKG).decode().splitlines()[0].removeprefix('package:').strip()
    assert adb('shell','sha256sum',remote).decode().split()[0]==digest
    commands=[
        ('Regression',['run_emulator_regression.py','--serial',args.serial,'--out',str(OUT/'Regression')]),
        ('Touch',['check_gameplay_audit_device.py','--serial',args.serial,'--out',str(OUT/'Touch')]),
        ('Cascade',['run_cascade_timing_device.py','--serial',args.serial,'--variant','measure','--out',str(OUT/'Cascade')]),
        ('CascadeVisual',['run_cascade_timing_device.py','--serial',args.serial,'--variant','visual','--out',str(OUT/'Cascade')]),
        ('Fluidity',['measure_fluidity.py','--serial',args.serial,'--apk',str(APK),'--out',str(OUT/'Fluidity'),'--no-install','--variant','candidate']),
    ]
    for family in ['crate','stone','gate','tiles']:
        commands.append(('Density_'+family,['run_obstacle_density_device.py','--serial',args.serial,'--variant','candidate_review-'+family,'--out',str(OUT/'Density')]))
    # Measure responsiveness first so actionable findings are available before the long campaign run.
    commands.sort(key=lambda entry: 10 if entry[0]=='Regression' else 0 if entry[0]=='Fluidity' else 1 if entry[0]=='Touch' else 2 if entry[0].startswith('Cascade') else 3)
    for name,command in commands:
        if args.only is not None and name not in args.only:
            continue
        began=datetime.now(timezone.utc).isoformat()
        print('Starting QA '+name,flush=True)
        code=1
        try:
            code=subprocess.run([sys.executable,str(ROOT/'Verification/Tools'/command[0]),*command[1:]],cwd=ROOT).returncode
        finally:
            after=state()
            audit={'utc':began,'serial':args.serial,'qa_target':target,'apk_sha256':digest,'install':install,'exit_code':code,'before':before,'after':after,'data_unchanged':after==before,'scope':'Real saved profile/preference hash audit around explicit isolated native QA fixtures. No save replacement or reset.'}
            (OUT/(name+'_Data_Audit.json')).write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
        assert after==before,name+' changed real QA save files'
        assert code==0,name+' failed; inspect saved evidence before continuing'
    adb('shell','am','force-stop',PKG)
    adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity')
    assert state()==before,'Ordinary startup changed saved data'
    print(json.dumps({'status':'PASS_SELECTED_QA_GAMEPLAY_TOOLS','data_unchanged':True}),flush=True)

if __name__=='__main__':
    main()
