"""Read the actual109 SDK APK, same-phone signer, manifest/locks and JNI target DEX signature. No installation."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[3]
ANDROID=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer')
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api

def require(ok,code):
    if not ok:raise ValueError(code)
def dex_method(data,definitions):
    require(data[:4]==b'dex\n' and len(data)>=112,'DexHeaderInvalid109')
    def u4(at):return struct.unpack_from('<I',data,at)[0]
    def uleb(at):
        value=0
        for shift in range(0,35,7):
            b=data[at];at+=1;value|=(b&127)<<shift
            if not b&128:return value,at
        raise ValueError('DexIntegerInvalid109')
    n,off=u4(56),u4(60);require(n<2000000 and off+n*4<=len(data),'DexStringsInvalid109');strings=[]
    for i in range(n):
        at=u4(off+i*4);_,at=uleb(at);end=data.index(b'\0',at);strings.append(data[at:end].decode('utf-8',errors='replace'))
    nt,ot=u4(64),u4(68);types=[strings[u4(ot+i*4)] for i in range(nt)]
    np,op=u4(72),u4(76);protos=[]
    for i in range(np):
        _,ret,params=struct.unpack_from('<III',data,op+i*12);args=[]
        if params:
            count=u4(params);args=[types[struct.unpack_from('<H',data,params+4+j*2)[0]] for j in range(count)]
        protos.append('('+''.join(args)+')'+types[ret])
    nm,om=u4(88),u4(92);matching=set()
    for i in range(nm):
        owner,proto,name=struct.unpack_from('<HHI',data,om+i*8)
        if types[owner]=='Lcom/yandex/mobile/ads/common/YandexAds;' and strings[name]=='setAppAdAnalyticsReporting' and protos[proto]=='(Z)V':matching.add(i)
    nc,oc=u4(96),u4(100)
    definitions.extend(types[u4(oc+i*32)] for i in range(nc))
    if not matching:return None
    for i in range(nc):
        at=oc+i*32;owner=u4(at)
        if types[owner]!='Lcom/yandex/mobile/ads/common/YandexAds;':continue
        at=u4(at+24)
        if not at:continue
        sizes=[]
        for _ in range(4):v,at=uleb(at);sizes.append(v)
        for _ in range(sizes[0]+sizes[1]):_,at=uleb(at);_,at=uleb(at)
        for count in sizes[2:]:
            index=0
            for _ in range(count):
                diff,at=uleb(at);flags,at=uleb(at);_,at=uleb(at);index+=diff
                if index in matching:return dict(classDescriptor=types[owner],method='setAppAdAnalyticsReporting',descriptor='(Z)V',accessFlags=flags,public=bool(flags&1),static=bool(flags&8))
    return None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--build',type=Path,required=True);p.add_argument('--tag');args=p.parse_args();build=args.build.resolve()
    require(args.tag is None or re.fullmatch('[A-Za-z0-9_]{1,30}',args.tag),'SafeFreshAuditTagRequired109')
    require(args.execute and build.is_relative_to((ROOT/'Verification/Evidence/Review109/Native').resolve()),'ActualNative109BuildRequired')
    native=json.loads(build.read_text('utf-8-sig'));inv=json.loads((build.parent/'Invocation.json').read_text());require(native['status']=='PASS_NATIVE_TEAMS109_BUILD_DEVELOPMENT' and native['actualBuild'] and native['errors']==0 and inv['status']=='PASS_NATIVE109_LTS_INVOCATION','PassingActualBuildRequired109')
    apk=Path(native['apk']);require(apk.is_file() and api.sha(apk)==native['apkSHA256'] and apk.stat().st_size==native['bytes'],'ExactCompiledApkRequired109');project=apk.parent
    # APK layout is <Game>/Builds/<tag>/name.apk, with a fallback for a direct
    # Builds/name.apk chosen by an operator. The receipt determines the root.
    while project.name!='Game' and project!=project.parent:project=project.parent
    require(project.name=='Game' and (project.parent/'Preparation.json').is_file(),'OwnedCandidateRootRequired109')
    raw=ROOT/'.verification-cache/Review109/Static'/(build.parent.name+('_'+args.tag if args.tag else ''));raw.mkdir(parents=True,exist_ok=False)
    output=build.parent/'Static'/args.tag if args.tag else build.parent
    if args.tag:output.mkdir(parents=True,exist_ok=False)
    result=dict(schemaVersion=1,status='FAIL_STATIC_TEAMS109_APK',utc=api.utc(),apkSHA256=api.sha(apk),bytes=apk.stat().st_size,checks=[],errors=[],sdkInitialized=False,appLaunched=False,realAdVerified=False,scope='Actual signed development APK bytes/manifest/DEX symbols/dependency locks only. No class activation, SDK/ad/network request, impression, install, device or production/privacy certification. AppMetrica is retained as a required SDK dependency.')
    spec=importlib.util.spec_from_file_location('apk94_static_primitives',ROOT/'Verification/Tools/Unity6Migration94/check_apk94.py');primitive=importlib.util.module_from_spec(spec);spec.loader.exec_module(primitive)
    def check(value,label):require(value,label);result['checks'].append(label)
    def run(label,cmd):
        path=raw/(label+'.log')
        with path.open('xb') as stream:r=subprocess.run([str(v) for v in cmd],stdout=stream,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        require(r.returncode==0,'StaticToolFailed109'+label);return path.read_text('utf-8',errors='replace')
    try:
        tools=ANDROID/'SDK/build-tools/36.0.0';signature=run('Signature',[ANDROID/'OpenJDK/bin/java.exe','-jar',tools/'lib/apksigner.jar','verify','--verbose','--print-certs',apk]);check(True,'DevelopmentSignatureVerifies')
        observed=json.loads((ROOT/'Verification/Evidence/Review109/Physical/Inventory02/Signing109.json').read_text());certs=re.findall(r'Signer #\d+ certificate SHA-256 digest: ([a-f0-9]{64})',signature);check(certs==[observed['signerCertificateSHA256']],'ExactFreshlyInventoriedPhoneSigner');result['signerCertificateSHA256']=certs[0];result['phoneSigningInventorySHA256']=api.sha(ROOT/'Verification/Evidence/Review109/Physical/Inventory02/Signing109.json')
        run('Zipalign',[tools/'zipalign.exe','-c','-v','4',apk]);check(True,'ApkZipAlignment')
        badging=run('Badging',[tools/'aapt.exe','dump','badging',apk]);tree=run('Manifest',[tools/'aapt.exe','dump','xmltree',apk,'AndroidManifest.xml']);nodes=primitive.parse_manifest(tree)
        package='com.heartoftherain.review98'
        check("package: name='"+package+"'" in badging and "sdkVersion:'26'" in badging and "targetSdkVersion:'36'" in badging and "native-code: 'arm64-v8a'" in badging and 'application-debuggable' in badging,'PackageApiArm64AndDevelopment')
        check("versionCode='109'" in badging and "application-label:'\u0421\u0435\u0440\u0434\u0446\u0435 \u0434\u043e\u0436\u0434\u044f'" in badging,'InternalVersion109AndRussianName')
        attrs=lambda n,k:primitive.attribute_value(n['attributes'].get(k))
        metadata=[n for n in nodes if n['tag']=='meta-data' and attrs(n,'android:name')=='com.yandex.mobile.ads.AUTOMATIC_SDK_INITIALIZATION'];check(len(metadata)==1 and attrs(metadata[0],'android:value')==0,'SdkAutomaticInitializationExplicitFalse')
        applications=[n for n in nodes if n['tag']=='application'];check(len(applications)==1 and attrs(applications[0],'android:usesCleartextTraffic')==0,'CleartextTrafficDisabled')
        permissions={attrs(n,'android:name') for n in nodes if n['tag']=='uses-permission'}
        for permission in ('android.permission.ACCESS_FINE_LOCATION','android.permission.ACCESS_COARSE_LOCATION','android.permission.ACCESS_BACKGROUND_LOCATION','com.google.android.gms.permission.AD_ID'):check(permission not in permissions,'PermissionAbsent_'+permission)
        activities=[n for n in nodes if n['tag']=='activity' and attrs(n,'android:name')=='com.unity3d.player.UnityPlayerActivity'];check(len(activities)==1 and attrs(activities[0],'android:screenOrientation') in (1,'portrait'),'PortraitUnityActivity')
        curtains=[n for n in nodes if n['tag']=='provider' and attrs(n,'android:name')=='com.heartoftherain.launch99.LaunchCurtain99'];check(len(curtains)==1 and attrs(curtains[0],'android:authorities')==package+'.launch99' and attrs(curtains[0],'android:exported')==0 and curtains[0]['attributes'].get('android:enabled','').startswith('@0x'),'SamePackageNonExportedNativeCurtainConfigurationGate')
        with zipfile.ZipFile(apk) as archive:
            check(len(archive.namelist())==len(set(archive.namelist())) and archive.testzip() is None,'ZipCrcAndUniqueNamesValid');symbols=[];definitions=[];libraries=[];stored=[];dex_count=0
            for entry in archive.infolist():
                if re.fullmatch(r'classes[0-9]*\.dex',entry.filename):
                    dex_count+=1;require(entry.file_size<=96*1024*1024,'DexEntryBound109');found=dex_method(archive.read(entry),definitions)
                    if found:found['dex']=entry.filename;symbols.append(found)
                if entry.filename.startswith('lib/') and entry.filename.endswith('.so'):
                    require(re.fullmatch(r'lib/arm64-v8a/[A-Za-z0-9_.+-]+\.so',entry.filename),'UnexpectedNativeAbiOrPath109');body=archive.read(entry);archive.fp.seek(entry.header_offset);header=archive.fp.read(30);require(len(header)==30 and header[:4]==b'PK\x03\x04','ZipNativeHeaderInvalid109');name_length,extra_length=struct.unpack_from('<HH',header,26);data_offset=entry.header_offset+30+name_length+extra_length
                    if entry.compress_type==zipfile.ZIP_STORED:require(data_offset%16384==0,'StoredNativeLibraryNot16KiBAligned109');stored.append(entry.filename)
                    libraries.append(dict(file=entry.filename,compression=entry.compress_type,dataOffset=data_offset,loadSegments=primitive.elf_segments(body)))
            check(len(symbols)==1 and symbols[0]['public'] and symbols[0]['static'],'ActualDexJniTargetPublicStaticBooleanVoid');result['jniTarget']=symbols[0]
            check('Lcom/heartoftherain/identity/DeviceIdentity82;' in definitions,'ActualManagedIdentityBridgeDefined')
            expected={p:sum(v.startswith(p) for v in definitions) for p in ('Lcom/yandex/mobile/ads/','Lio/appmetrica/')};check(all(expected.values()),'ExpectedYandexAndAppMetricaClassesDefined')
            forbidden_prefixes=('Lru/rustore/sdk/pay/','Lru/rustore/sdk/core/','Lcom/applovin/','Lcom/unity3d/ads/','Lcom/ironsource/','Lcom/vungle/','Lcom/facebook/ads/','Lcom/mbridge/','Lcom/google/ads/','Lcom/google/android/ump/')
            forbidden_exact={'Lcom/google/android/gms/ads/MobileAds;','Lcom/google/android/gms/ads/AdView;','Lcom/android/billingclient/api/BillingClient;','Lcom/huawei/hms/ads/HwAds;'}
            unexpected=[v for v in definitions if v.startswith(forbidden_prefixes) or v in forbidden_exact];check(not unexpected,'NoUnexpectedPaymentOrOtherAdvertisingSdkDefinitions')
            result['sdkClassPolicy']=dict(expectedDefinitionCounts=expected,definedClassCount=len(definitions),unexpectedDefinitionCount=len(unexpected),forbiddenPrefixes=list(forbidden_prefixes),forbiddenExact=sorted(forbidden_exact),scope='Actual DEX class definitions, not incidental strings or AppMetrica adapter references. Declared play-services ads-identifier dependency is permitted; a full GoogleMobileAds SDK is rejected.')
            result['zip']=dict(libraries=libraries,dexCount=dex_count,storedNativeLibraries=stored,compressedNativeLibraryCount=sum(v['compression']!=zipfile.ZIP_STORED for v in libraries))
            check({'lib/arm64-v8a/libil2cpp.so','lib/arm64-v8a/libunity.so'}<={v['file'] for v in libraries},'ActualArm64ElfAnd16KiBLoadSegments')
        gradle=project/'Library/Bee/Android/Prj/IL2CPP/Gradle';locks=list(gradle.rglob('gradle.lockfile'));check(bool(locks),'ActualResolvedDependencyLocksPresent')
        text='\n'.join(v.read_text('utf-8') for v in locks);check('com.yandex.android:mobileads:8.6.0=' in text and 'io.appmetrica.analytics:analytics:8.6.0=' in text,'ExactYandexAndAppMetrica860Resolved')
        result['dependencyLocks']=[dict(path=v.relative_to(project).as_posix(),sha256=api.sha(v),bytes=v.stat().st_size) for v in locks]
        check(api.sha(apk)==native['apkSHA256'],'ApkUnchangedByReadOnlyAudit');result['status']='PASS_STATIC_TEAMS109_APK'
    except Exception as error:result['errors'].append(dict(type=type(error).__name__,code=str(error) if re.fullmatch('[A-Za-z0-9_.]{1,150}',str(error)) else 'SeePrivateStaticOutput109'))
    result['nativeBuildSHA256']=api.sha(build);result['invocationSHA256']=api.sha(build.parent/'Invocation.json');result['auditToolSHA256']=api.sha(Path(__file__));result['historicalSdkFreeZipPolicyInvoked']=False;result['independentManifestAndElfPrimitiveSHA256']=api.sha(ROOT/'Verification/Tools/Unity6Migration94/check_apk94.py');api.write(output/'StaticApk109.json',result);print(json.dumps(dict(status=result['status'],checks=len(result['checks']),report=(output/'StaticApk109.json').relative_to(ROOT).as_posix())));return 0 if result['status'].startswith('PASS_') else 1
if __name__=='__main__':raise SystemExit(main())
