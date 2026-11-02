"""Read-only current99 APK signature/manifest/ARM64/16KiB/SDK-free checks."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
ANDROID=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer')
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--build',type=Path,required=True);args=p.parse_args()
    path=args.build.resolve()
    if not args.execute or not path.is_relative_to((ROOT/'Verification/Evidence/Review99/Native').resolve()):p.error('Actual98 native build required')
    native=json.loads(path.read_text('utf-8-sig'));invocation=json.loads((path.parent/'Invocation.json').read_text('utf-8'))
    expected='PASS_NATIVE_REVIEW99_'+native['operation'].upper()
    if (native.get('status')!=expected or native.get('errors') or native.get('error') or invocation.get('status')!='PASS_NATIVE99_INVOCATION'
        or invocation.get('actualEngine')!='6000.3.27f1' or not invocation.get('originalAssetAndSourceBytesPreserved') or not invocation.get('originalAssetGuidsPreserved')):p.error('Successful source-preserving actual build required')
    apk=Path(native['apk']);original=api.sha(apk)
    if original!=native['apkSHA256'] or apk.stat().st_size!=native['bytes']:p.error('Exact native APK required')
    raw=ROOT/'.verification-cache/Review99/Static'/path.parent.name;raw.mkdir(parents=True,exist_ok=False)
    primitive=module('apk98_frozen_parser',ROOT/'Verification/Tools/Unity6Migration94/check_apk94.py')
    result=dict(schemaVersion=1,status='FAIL_STATIC_APK99',utc=api.utc(),apkSHA256=original,bytes=apk.stat().st_size,
                package='com.heartoftherain.review98',development=native['development'],checks={},errors=[],
                scope='Read-only actual internal APK checks only; no install/runtime/provider/production acceptance.')
    def run(name,cmd):
        out,err=raw/(name+'.out'),raw/(name+'.err')
        with out.open('xb') as o,err.open('xb') as e:r=subprocess.run([str(v) for v in cmd],stdout=o,stderr=e,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode:raise ValueError('StaticToolFailed'+name)
        return out.read_text('utf-8')
    tools=ANDROID/'SDK/build-tools/36.0.0'
    try:
        run('Signature',[ANDROID/'OpenJDK/bin/java.exe','-jar',tools/'lib/apksigner.jar','verify','--verbose','--print-certs',apk]);result['checks']['signature']=True
        run('Zipalign',[tools/'zipalign.exe','-c','-v','4',apk]);result['checks']['zipalign']=True
        badging=run('Badging',[tools/'aapt.exe','dump','badging',apk]);tree=run('Manifest',[tools/'aapt.exe','dump','xmltree',apk,'AndroidManifest.xml'])
        if "package: name='com.heartoftherain.review98'" not in badging or "application-label:'Сердце дождя'" not in badging:raise ValueError('PackageOrRussianLabelMismatch')
        if "sdkVersion:'26'" not in badging or "targetSdkVersion:'36'" not in badging:raise ValueError('AndroidApiMismatch')
        if "native-code: 'arm64-v8a'" not in badging or ("application-debuggable" in badging)!=bool(native['development']):raise ValueError('ArchitectureOrBuildModeMismatch')
        nodes=primitive.parse_manifest(tree)
        activities=[n for n in nodes if n['tag']=='activity' and primitive.attribute_value(n['attributes'].get('android:name'))=='com.unity3d.player.UnityPlayerActivity']
        if len(activities)!=1 or primitive.attribute_value(activities[0]['attributes'].get('android:screenOrientation')) not in (1,'portrait'):raise ValueError('PortraitActivityMismatch')
        providers=[n for n in nodes if n['tag']=='provider' and primitive.attribute_value(n['attributes'].get('android:name'))=='com.heartoftherain.launch99.LaunchCurtain99']
        if len(providers)!=1 or primitive.attribute_value(providers[0]['attributes'].get('android:authorities'))!='com.heartoftherain.review98.launch99' or primitive.attribute_value(providers[0]['attributes'].get('android:exported'))!=0:raise ValueError('NativeCurtainProviderMismatch')
        if not providers[0]['attributes'].get('android:enabled','').startswith('@0x'):raise ValueError('NativeCurtainConfigurationGateMissing')
        if any(x in tree for x in ('RuStorePayContentProvider','heartoftherain-pay','com.yandex.mobile.ads','io.appmetrica')):raise ValueError('UnexpectedProvider')
        result['checks'].update(manifest=True,portrait=True,sdkFreeManifest=True,nonExportedSameAppCurtain=True)
        result['zip']=primitive.zip_profile(apk)
        if not {'lib/arm64-v8a/libil2cpp.so','lib/arm64-v8a/libunity.so'}<={x['file'] for x in result['zip']['libraries']}:raise ValueError('NativeLibrariesMissing')
        result['checks']['arm64ElfAnd16KiB']=True
        if api.sha(apk)!=original:raise ValueError('ApkChangedDuringReadOnlyChecks')
        result['status']='PASS_STATIC_APK99'
    except Exception as error:result['errors'].append(dict(type=type(error).__name__,category=str(error) if re.fullmatch('[A-Za-z0-9]{1,100}',str(error)) else 'SeePrivateToolOutput'))
    result['nativeBuildSHA256']=api.sha(path);result['invocationSHA256']=api.sha(path.parent/'Invocation.json')
    api.write(path.parent/'StaticApk99.json',result);print(json.dumps({'status':result['status'],'report':(path.parent/'StaticApk99.json').relative_to(ROOT).as_posix()}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':raise SystemExit(main())
