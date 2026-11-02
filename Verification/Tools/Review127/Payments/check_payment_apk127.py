"""Root-executable read-only audit of diagnostic127 APK. Never installs or signs.

Retains Review126 strict signature/SDK/privacy/resource/alignment checks; adds
127 version/source-epoch/diagnostic metadata checks. No provider acceptance.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[4]
ANDROID=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer')
def sha(path):return __import__('hashlib').sha256(Path(path).read_bytes()).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def need(value,code):
 if not value:raise RuntimeError(code)
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',type=Path,required=True);parser.add_argument('--tag');args=parser.parse_args();path=args.build.resolve()
 need(args.tag is None or re.fullmatch('[A-Za-z0-9_]{1,30}',args.tag),'SafeFreshAuditTagRequired126')
 need(path.is_relative_to((ROOT/'Verification/Evidence/Review127/Payments/Native').resolve()),'OwnedBuildReportRequired126')
 native=json.loads(path.read_text('utf-8'));process=json.loads((path.parent/'Process.json').read_text('utf-8'))
 need(native['status']=='PASS_PAYMENT_DIAGNOSTIC127_ANDROID_BUILD' and native['actualBuild'] and native['customSigning'] and process['status']=='PASS_PAYMENT_DIAGNOSTIC127_NATIVE','ActualPassingSignedBuildRequired126')
 apk=Path(native['apk']);need(sha(apk)==native['apkSHA256'],'ExactBuiltApkRequired127')
 need(native.get('receiptSHA256')==process.get('preparationSHA256') and re.fullmatch('[0-9a-f]{64}',process.get('layoutReportSHA256') or ''),'SourceEpochAndNativeLayoutReportBindingRequired127')
 project=apk.parent.parent;output=path.parent/'Static'
 if args.tag:output=output/args.tag
 output.mkdir(parents=True,exist_ok=False)
 primitive=load('apk126_primitives',ROOT/'Verification/Tools/Unity6Migration94/check_apk94.py')
 dex=load('apk126_dex',ROOT/'Verification/Tools/Review109/check_apk109.py')
 cert=json.loads((ROOT/'Release/Signing/release-certificate.json').read_text('utf-8'))
 report={'status':'FAIL_PAYMENT_DIAGNOSTIC_APK127','apkSHA256':sha(apk),'checks':[],'actualSdkPayment':False,'actualAdView':False,'appInstalled':False,'scope':'Actual APK signature, manifest, DEX definitions, native ELF/ZIP alignment and dependency locks. No provider/device/production acceptance.'}
 def check(value,code):need(value,code);report['checks'].append(code)
 def run(label,command):
  result=subprocess.run([str(p) for p in command],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
  need(result.returncode==0,'StaticToolFailed126_'+label)
  (output/(label+'.log')).write_bytes(result.stdout);return result.stdout.decode('utf-8','replace')
 try:
  tools=ANDROID/'SDK/build-tools/36.0.0'
  signature=run('Signature',[ANDROID/'OpenJDK/bin/java.exe','-jar',tools/'lib/apksigner.jar','verify','--verbose','--print-certs',apk])
  hashes=re.findall(r'Signer #\d+ certificate SHA-256 digest: ([a-f0-9]{64})',signature)
  check(hashes==[cert['sha256']],'ActualApkUsesDeveloperOwnedReleaseCertificate')
  check(re.findall(r'Signer #\d+ certificate SHA-1 digest: ([a-f0-9]{40})',signature)==[cert['sha1']],'ActualApkSha1MatchesVkRegistrationMaterial')
  run('Zipalign',[tools/'zipalign.exe','-c','-P','16','-v','4',apk]);check(True,'ApkZipAndNative16KiBAlignment')
  badging=run('Badging',[tools/'aapt.exe','dump','badging',apk]);tree=run('Manifest',[tools/'aapt.exe','dump','xmltree',apk,'AndroidManifest.xml']);nodes=primitive.parse_manifest(tree)
  check("package: name='com.heartoftherain.game'" in badging and "versionCode='127'" in badging,'RegisteredPackageAndVersion127')
  check("sdkVersion:'26'" in badging and "targetSdkVersion:'36'" in badging and "native-code: 'arm64-v8a'" in badging and 'application-debuggable' in badging,'Arm64Api26_36SandboxDevelopmentBuild')
  attrs=lambda n,k:primitive.attribute_value(n['attributes'].get(k))
  applications=[n for n in nodes if n['tag']=='application'];check(len(applications)==1 and attrs(applications[0],'android:usesCleartextTraffic')==0,'HttpsTrafficOnly')
  metadata=[n for n in nodes if n['tag']=='meta-data' and attrs(n,'android:name')=='com.yandex.mobile.ads.AUTOMATIC_SDK_INITIALIZATION']
  check(len(metadata)==1 and attrs(metadata[0],'android:value')==0,'YandexAutomaticInitializationDisabled')
  permissions={attrs(n,'android:name') for n in nodes if n['tag']=='uses-permission'}
  for p in ('android.permission.ACCESS_FINE_LOCATION','android.permission.ACCESS_COARSE_LOCATION','android.permission.ACCESS_BACKGROUND_LOCATION','com.google.android.gms.permission.AD_ID'):check(p not in permissions,'PermissionAbsent_'+p)
  resources=run('Resources',[tools/'aapt.exe','dump','--values','resources',apk])
  expected={'rustore_PayClientSettings_consoleApplicationId':'2063777840','rustore_PayClientSettings_deeplinkScheme':'heartoftherain-pay','rustore_PayClientSettings_internalConfigKey':'unity'}
  ids={}
  for key,value in expected.items():
   entries=re.findall(r'resource\s+(0x[0-9a-fA-F]+)\s+[^\r\n]*:string/'+re.escape(key)+r':([\s\S]*?)(?=\bresource\s+0x|\Z)',resources)
   actual=[(rid,found) for rid,body in entries for found in re.findall(r'\(string(?:8|16)\)\s+"([^"]*)"',body)]
   check(bool(actual) and len({rid.lower() for rid,_ in actual})==1 and all(found==value for _,found in actual),'ActualApkResource_'+key)
   ids[key]=actual[0][0].lower()
  for name,key in (('console_app_id_value','rustore_PayClientSettings_consoleApplicationId'),('sdk_pay_scheme_value','rustore_PayClientSettings_deeplinkScheme'),('internal_config_key','rustore_PayClientSettings_internalConfigKey')):
   meta=[n for n in nodes if n['tag']=='meta-data' and attrs(n,'android:name')==name]
   check(len(meta)==1 and str(attrs(meta[0],'android:value')).lower()=='@'+ids[key],'RuStoreManifestBinding_'+name)
  activities=[n for n in nodes if n['tag']=='activity' and attrs(n,'android:name')=='ru.rustore.unitysdk.RuStoreDeeplinkActivityDefault']
  check(len(activities)==1 and attrs(activities[0],'android:exported') in (1,0xffffffff,'true'),'ActualPaymentReturnActivityExported')
  def descendants(index):
   stop=next((i for i in range(index+1,len(nodes)) if nodes[i]['depth']<=nodes[index]['depth']),len(nodes))
   return list(range(index+1,stop))
  activity_index=nodes.index(activities[0]);return_filter=False
  for i in descendants(activity_index):
   if nodes[i]['tag']!='intent-filter':continue
   children=[nodes[j] for j in descendants(i)]
   actions={attrs(n,'android:name') for n in children if n['tag']=='action'}
   categories={attrs(n,'android:name') for n in children if n['tag']=='category'}
   schemes={str(attrs(n,'android:scheme')).lower() for n in children if n['tag']=='data'}
   if 'android.intent.action.VIEW' in actions and {'android.intent.category.DEFAULT','android.intent.category.BROWSABLE'}<=categories and '@'+ids['rustore_PayClientSettings_deeplinkScheme'] in schemes:return_filter=True
  check(return_filter,'ActualViewBrowsablePaymentSchemeBinding')
  report['sdkResourceIds']=ids
  with zipfile.ZipFile(apk) as z:
   check(z.testzip() is None and len(z.namelist())==len(set(z.namelist())),'ZipCrcAndUniquePaths')
   metadata_path='assets/bin/Data/Managed/Metadata/global-metadata.dat'
   check(metadata_path in z.namelist() and z.getinfo(metadata_path).file_size<=128*1024*1024,'BoundedActualIl2CppMetadata127')
   metadata=z.read(metadata_path)
   for name in (b'PaymentDiagnostics127\0',b'PaymentDiagnosticSnapshot127\0'):check(name in metadata,'ActualPrivateDiagnosticType_'+name[:-1].decode())
   check(b'SigninLayout127Verification\0' not in metadata,'EditorLayoutFixtureAbsentFromPlayer127')
   definitions=[];jni=[];libraries=[]
   for entry in z.infolist():
    if re.fullmatch(r'classes[0-9]*\.dex',entry.filename):
     need(entry.file_size<=96*1024*1024,'BoundedDexEntry126');result=dex.dex_method(z.read(entry),definitions)
     if result:jni.append(result)
    if entry.filename.startswith('lib/') and entry.filename.endswith('.so'):
     need(re.fullmatch(r'lib/arm64-v8a/[A-Za-z0-9_.+-]+\.so',entry.filename),'UnexpectedNativeAbi126')
     body=z.read(entry);z.fp.seek(entry.header_offset);header=z.fp.read(30);length,extra=struct.unpack_from('<HH',header,26);offset=entry.header_offset+30+length+extra
     if entry.compress_type==zipfile.ZIP_STORED:need(offset%16384==0,'StoredLibraryNot16KiBAligned126')
     libraries.append({'path':entry.filename,'segments':primitive.elf_segments(body)})
   check(len(jni)==1 and jni[0]['public'] and jni[0]['static'],'PinnedYandexJniMethodDefined')
   counts={p:sum(v.startswith(p) for v in definitions) for p in ('Lcom/yandex/mobile/ads/','Lio/appmetrica/','Lru/rustore/sdk/pay/','Lru/rustore/sdk/core/','Lru/rustore/unitysdk/')}
   check(all(counts.values()),'ActualYandexAppMetricaRuStoreAndUnityBridgeDefined');report['sdkDefinitions']=counts
   check('Lcom/heartoftherain/identity/DeviceIdentity82;' in definitions,'ActualProtectedManagedIdentityBridgeDefined')
   forbidden=('Lcom/applovin/','Lcom/unity3d/ads/','Lcom/ironsource/','Lcom/vungle/','Lcom/facebook/ads/','Lcom/mbridge/','Lcom/google/ads/','Lcom/google/android/ump/')
   check(not any(v.startswith(forbidden) for v in definitions),'NoUnapprovedAdvertisingSdkDefinitions')
   check({'lib/arm64-v8a/libil2cpp.so','lib/arm64-v8a/libunity.so'}<={v['path'] for v in libraries},'ActualArm64UnityAndIl2CppElf');report['libraries']=libraries
  locks=list((project/'Library/Bee/Android/Prj/IL2CPP/Gradle').rglob('gradle.lockfile'));check(bool(locks),'ResolvedDependencyLocksPresent')
  text='\n'.join(p.read_text('utf-8') for p in locks)
  for dep in ('com.yandex.android:mobileads:8.6.0=','io.appmetrica.analytics:analytics:8.6.0=','ru.rustore.sdk:pay:11.1.0=','ru.rustore.sdk:core:10.5.0='):check(dep in text,'ResolvedPinned_'+dep)
  report['dependencyLocks']={p.relative_to(project).as_posix():sha(p) for p in locks}
  check(sha(apk)==native['apkSHA256'],'ApkUnchangedByAudit');report['status']='PASS_PAYMENT_DIAGNOSTIC_APK127';report['certificateSHA256']=cert['sha256']
 except Exception as e:report['error']=str(e) if re.fullmatch('[A-Za-z0-9_.:=/-]{1,150}',str(e)) else type(e).__name__
 report['toolSHA256']=sha(__file__);report['nativeReportSHA256']=sha(path);report['sourceDerivativeSHA256']='cfeea57935604719136a07f67553818694b527005675e872d1104842e43becdb';report['versionCode']=127;report['diagnosticOnly']=True
 with (output/'Audit.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({'status':report['status'],'checks':len(report['checks']),'report':str((output/'Audit.json').relative_to(ROOT))}))
 return 0 if report['status'].startswith('PASS_') else 1
if __name__=='__main__':raise SystemExit(main())
