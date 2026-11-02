"""Read-only static acceptance for the isolated real-SDK demo APK, no launch."""
import argparse,importlib.util,json,re,struct,subprocess,zipfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
ANDROID=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,code):
 if not ok:raise ValueError(code)
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);a=p.parse_args();native_path=a.native.resolve()
 need(native_path.is_relative_to((ROOT/'Verification/Evidence/Review127/Ads').resolve()),'OwnedNativeEvidence127')
 native=json.loads(native_path.read_bytes());process=json.loads((native_path.parent/'Process.json').read_bytes())
 need(native['status']=='PASS_REAL_SDK_AD_DEMO127_ANDROID_BUILD' and native['actualBuild'] and native['debugSigning']
      and process['status']=='PASS_PRIVATE_AD_DEMO127_BUILD','ActualPassingBuild127')
 apk=Path(native['apk']);need(apk.is_relative_to(Path('E:/.verification-cache/HOTR127')) and sha(apk)==native['apkSHA256'],'ExactPrivateBuiltApk127')
 output=native_path.parent/'Static';output.mkdir(exist_ok=False)
 primitive=load('demo127_elfmanifest',ROOT/'Verification/Tools/Unity6Migration94/check_apk94.py')
 dex=load('demo127_dex',ROOT/'Verification/Tools/Review109/check_apk109.py')
 report={'status':'FAIL_DEMO_AD_APK127','checks':[],'apk':str(apk),'apkSHA256':sha(apk),'nativeSHA256':sha(native_path),'toolSHA256':sha(__file__),
         'actualAdView':False,'actualRewardGrant':False,'deviceTouched':False,
         'scope':'Static demo-fixture package, debug signer, real Yandex JNI/identity bridge, privacy, pinned resolved dependencies, ARM64 and16KiB alignment. No device or provider acceptance.'}
 def check(ok,code):need(ok,code);report['checks'].append(code)
 def run(label,args):
  r=subprocess.run([str(s) for s in args],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180,creationflags=0x08000000)
  (output/(label+'.log')).write_bytes(r.stdout);need(r.returncode==0,'StaticToolFailed127_'+label);return r.stdout.decode('utf-8','replace')
 try:
  tools=ANDROID/'SDK/build-tools/36.0.0'
  signature=run('Signature',[ANDROID/'OpenJDK/bin/java.exe','-jar',tools/'lib/apksigner.jar','verify','--verbose','--print-certs',apk])
  hashes=re.findall(r'Signer #\d+ certificate SHA-256 digest: ([a-f0-9]{64})',signature)
  check(len(hashes)==1 and 'CN=Android Debug' in signature,'ActualAndroidDebugSigner127')
  release=json.loads((ROOT/'Release/Signing/release-certificate.json').read_bytes())
  check(hashes[0]!=release['sha256'],'DeveloperReleaseSignerNotUsed127');report['debugCertificateSHA256']=hashes[0]
  run('Zipalign',[tools/'zipalign.exe','-c','-P','16','-v','4',apk]);check(True,'Apk16KiBAlignment127')
  badging=run('Badging',[tools/'aapt.exe','dump','badging',apk]);tree=run('Manifest',[tools/'aapt.exe','dump','xmltree',apk,'AndroidManifest.xml']);nodes=primitive.parse_manifest(tree)
  check("package: name='com.heartoftherain.ads127demo'" in badging and "versionCode='127'" in badging,'DistinctDemoPackage127')
  check("sdkVersion:'26'" in badging and "targetSdkVersion:'36'" in badging and "native-code: 'arm64-v8a'" in badging and 'application-debuggable' in badging,'Arm64Api26_36Development127')
  attr=lambda n,k:primitive.attribute_value(n['attributes'].get(k))
  apps=[n for n in nodes if n['tag']=='application'];check(len(apps)==1 and attr(apps[0],'android:usesCleartextTraffic')==0,'HttpsOnly127')
  init=[n for n in nodes if n['tag']=='meta-data' and attr(n,'android:name')=='com.yandex.mobile.ads.AUTOMATIC_SDK_INITIALIZATION']
  check(len(init)==1 and attr(init[0],'android:value')==0,'NoAutomaticAdSdkInitialization127')
  perms={attr(n,'android:name') for n in nodes if n['tag']=='uses-permission'}
  for name in ('android.permission.ACCESS_FINE_LOCATION','android.permission.ACCESS_COARSE_LOCATION','android.permission.ACCESS_BACKGROUND_LOCATION','com.google.android.gms.permission.AD_ID'):
   check(name not in perms,'Absent_'+name)
  check(not any(n['tag']=='meta-data' and attr(n,'android:name') in ('console_app_id_value','sdk_pay_scheme_value','internal_config_key') for n in nodes),'NoRuStorePaymentMetadata127')
  with zipfile.ZipFile(apk) as z:
   check(z.testzip() is None and len(z.namelist())==len(set(z.namelist())),'UniqueZipPathsAndCrc127')
   definitions=[];jni=[];libraries=[]
   for entry in z.infolist():
    if re.fullmatch(r'classes[0-9]*\.dex',entry.filename):
     need(entry.file_size<96*1024*1024,'BoundedDex127');observed=dex.dex_method(z.read(entry),definitions)
     if observed:jni.append(observed)
    if entry.filename.startswith('lib/') and entry.filename.endswith('.so'):
     need(re.fullmatch(r'lib/arm64-v8a/[A-Za-z0-9_.+-]+\.so',entry.filename),'OnlyApprovedAbi127')
     data=z.read(entry);z.fp.seek(entry.header_offset);header=z.fp.read(30);name,extra=struct.unpack_from('<HH',header,26);offset=entry.header_offset+30+name+extra
     if entry.compress_type==zipfile.ZIP_STORED:need(offset%16384==0,'AlignedStoredNativeLibrary127')
     libraries.append({'path':entry.filename,'segments':primitive.elf_segments(data)})
   check(len(jni)==1 and jni[0]['public'] and jni[0]['static'],'ActualYandexJniMethod127')
   check(any(s.startswith('Lcom/yandex/mobile/ads/') for s in definitions) and any(s.startswith('Lio/appmetrica/') for s in definitions),'ActualYandexAndAppMetricaDefinitions127')
   check('Lcom/heartoftherain/identity/DeviceIdentity82;' in definitions,'ActualProtectedIdentityBridge127')
   forbidden=('Lru/rustore/','Lcom/applovin/','Lcom/unity3d/ads/','Lcom/ironsource/','Lcom/vungle/','Lcom/facebook/ads/','Lcom/mbridge/','Lcom/google/ads/','Lcom/google/android/ump/')
   check(not any(s.startswith(forbidden) for s in definitions),'NoPaymentsOrUnapprovedAdSdk127')
   check({'lib/arm64-v8a/libil2cpp.so','lib/arm64-v8a/libunity.so'}<={x['path'] for x in libraries},'ActualUnityIl2Cpp127');report['libraries']=libraries
   metadata=[n for n in z.namelist() if n.endswith('global-metadata.dat')];check(len(metadata)==1,'SingleIl2CppMetadata127')
   data=z.read(metadata[0]);check(b'demo-rewarded-yandex' in data and b'https://api.novamind-it.ru' in data and b'AdsDemo127' in data,'ActualDemoUnitOriginAndFixtureMetadata127')
  project=apk.parent.parent;locks=list((project/'Library/Bee/Android/Prj/IL2CPP/Gradle').rglob('gradle.lockfile'));check(bool(locks),'ResolvedDependencyLocks127')
  text='\n'.join(p.read_text('utf-8') for p in locks)
  for dep in ('com.yandex.android:mobileads:8.6.0=','io.appmetrica.analytics:analytics:8.6.0='):check(dep in text,'ResolvedPinned_'+dep)
  check('ru.rustore' not in text,'NoResolvedPaymentDependency127');report['dependencyLocks']={p.relative_to(project).as_posix():sha(p) for p in locks}
  check(sha(apk)==native['apkSHA256'],'ApkUnchangedByAudit127');report['status']='PASS_DEMO_AD_APK127'
 except Exception as error:report['error']=str(error) if re.fullmatch('[A-Za-z0-9_.:=/-]{1,150}',str(error)) else type(error).__name__
 (output/'Audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'checks':len(report['checks']),'report':str(output/'Audit.json')}))
 return 0 if report['status'].startswith('PASS_') else 1
if __name__=='__main__':raise SystemExit(main())
