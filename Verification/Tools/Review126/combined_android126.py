"""Fresh private combined SDK sandbox preparation/build. Never installs an APK.

Signing passwords are child-process-only. Raw build state has owner+SYSTEM ACLs;
only sanitized logs, public metadata and the verified APK enter repo outputs.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[3]
PRIVATE=Path('E:/.verification-cache/HOTR126')
EDITOR=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Unity.exe')
ANDROID=EDITOR.parent/'Data/PlaybackEngines/AndroidPlayer'
CUSTODY=Path(os.environ.get('LOCALAPPDATA',''))/'HeartOfTheRain/ReleaseSigning/RuStore'
PROFILES=ROOT/'Release/Monetization126'
OUT=ROOT/'Verification/Evidence/Review126/Android'

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(value,code):
 if not value:raise RuntimeError(code)
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def inventory(project):
 return {p.relative_to(project).as_posix():sha(p) for name in ('Assets','Packages','ProjectSettings') for p in sorted((project/name).rglob('*')) if p.is_file()}
def guids(project):
 values={}
 for p in sorted((project/'Assets').rglob('*.meta')):
  found=re.findall(rb'(?m)^guid:\s*([a-fA-F0-9]{32})\s*$',p.read_bytes());need(len(found)==1,'UniqueAssetGuidRequired126')
  values[p.relative_to(project).as_posix()]=found[0].decode().lower()
 need(len(set(values.values()))==len(values),'UniqueGuidSetRequired126');return values
def replace(path,pattern,value):
 data,count=re.subn(pattern,lambda _:value,path.read_bytes());need(count==1,'PrivateSettingsShapeChanged126');path.write_bytes(data)
def prepare(tag):
 need(re.fullmatch('[A-Za-z0-9_]{1,24}',tag or ''),'FreshSafeTagRequired126')
 signing=module('signing126',ROOT/'Release/Signing/manage_release_signing.py')
 parent=signing.private_directory(PRIVATE/tag)
 ads=module('prepare_ads126',ROOT/'Verification/Tools/Review107/prepare_ads107.py')
 initial=ads.prepare('M126_'+tag,True)
 initial_project=ROOT/initial['project'];project=parent/'Game'
 for name in ('Assets','Packages','ProjectSettings'):shutil.copytree(initial_project/name,project/name)
 main=inventory(ROOT/'Unity');need(main==json.loads((initial_project.parent/'Preparation.json').read_text('utf-8'))['mainSourceSHA256'],'MainChangedSincePreparation126')
 settings=project/'ProjectSettings/ProjectSettings.asset'
 replace(settings,rb'(?m)^    Android: com\.heartoftherain\.ads107review',b'    Android: com.heartoftherain.game')
 replace(settings,rb'(?m)^  AndroidBundleVersionCode: [^\r\n]*',b'  AndroidBundleVersionCode: 126')
 defines=ads.SYMBOLS+';HOTR_RUSTORE_PAY;HOTR_RUSTORE_SDK_ONLY125'
 replace(settings,rb'(?m)^    Android: HOTR_YANDEX_ADS[^\r\n]*',b'    Android: '+defines.encode())
 (project/'Assets/csc.rsp').write_text('-define:'+defines+'\n',encoding='utf-8')
 # Add exact official registry versions; do not alter vendor metadata or upgrade.
 manifest_path=project/'Packages/manifest.json';manifest=json.loads(manifest_path.read_text('utf-8-sig'))
 official=json.loads((ROOT/'.verification-cache/RuStore81/Spike/Packages/manifest.json').read_text('utf-8'))
 manifest['scopedRegistries']=official['scopedRegistries']
 for name in ('ru.rustore.pay','ru.rustore.core'):manifest['dependencies'][name]=official['dependencies'][name]
 manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 lock_path=project/'Packages/packages-lock.json';lock=json.loads(lock_path.read_text('utf-8-sig'))
 sdk_lock=json.loads((ROOT/'.verification-cache/RuStore81/Spike/Packages/packages-lock.json').read_text('utf-8'))
 for name in ('ru.rustore.pay','ru.rustore.core'):lock['dependencies'][name]=sdk_lock['dependencies'][name]
 lock_path.write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
 gradle=project/'Assets/Plugins/Android/mainTemplate.gradle';text=gradle.read_text('utf-8')
 text=text.replace('**DEPS**',"    implementation('ru.rustore.sdk:pay:11.1.0') { version { strictly '11.1.0' } }\n    implementation('ru.rustore.sdk:core:10.5.0') { version { strictly '10.5.0' } }\n**DEPS**",1)
 gradle.write_text(text,encoding='utf-8')
 settings_gradle=project/'Assets/Plugins/Android/settingsTemplate.gradle'
 settings_text=settings_gradle.read_text('utf-8')
 need(settings_text.count('        flatDir {')==1,'StockSettingsRepositoriesRequired126')
 settings_text=settings_text.replace('        flatDir {',"        maven { url 'https://nexus-external.vkteam.ru/repository/maven-rustore-exposed' }\n        flatDir {",1)
 settings_gradle.write_text(settings_text,encoding='utf-8')
 with (project/'Assets/Plugins/Android/gradleTemplate.properties').open('a',encoding='utf-8') as f:f.write('\norg.gradle.daemon=false\norg.gradle.workers.max=2\n')
 selected={'checkout-sdk.sandbox.json':'Assets/HeartOfTheRain/Resources/HOTR_RuStore/CheckoutSdk125.json',
           'managed-staging.json':'Assets/HeartOfTheRain/Resources/HOTR_Server/ManagedStaging.json',
           'advertising.sandbox.json':'Assets/HeartOfTheRain/Resources/HOTR_Advertising/Configuration.json'}
 for name,relative in selected.items():
  target=project/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((PROFILES/name).read_bytes())
  if not Path(str(target)+'.meta').exists():Path(str(target)+'.meta').write_bytes(ads.meta(relative))
  folder=target.parent
  while folder!=project/'Assets':
   fm=Path(str(folder)+'.meta')
   if not fm.exists():fm.write_bytes(ads.meta(folder.relative_to(project).as_posix(),True))
   folder=folder.parent
 template=Path(__file__).with_name('MonetizationBuild126.cs.template')
 folder=project/'Assets/Review126Editor';folder.mkdir();Path(str(folder)+'.meta').write_bytes(ads.meta('Assets/Review126Editor',True))
 folder=folder/'Editor';folder.mkdir();Path(str(folder)+'.meta').write_bytes(ads.meta('Assets/Review126Editor/Editor',True))
 target=folder/'MonetizationBuild126.cs';shutil.copyfile(template,target);Path(str(target)+'.meta').write_bytes(ads.meta('Assets/Review126Editor/Editor/MonetizationBuild126.cs'))
 private=inventory(project);pins={p:h for p,h in private.items() if p.startswith('Assets/') and not p.endswith('.meta') and p!='Assets/Plugins/Android/AndroidManifest.xml'}
 guid=guids(project)
 need(max(len(str(project/p)) for p in private)<260,'ShortWindowsProjectRequired126')
 receipt={'version':1,'status':'PREPARED_MONETIZATION126','sourceRoot':str(ROOT),'project':str(project),'nonce':uuid.uuid4().hex,'unity':'6000.3.27f1','packageName':'com.heartoftherain.game',
          'paths':list(pins),'sha256':list(pins.values()),'metaPaths':list(guid),'metaGuids':list(guid.values()),'mainInputs':main,'inputs':private,'profiles':{p.name:sha(p) for p in PROFILES.glob('*.json')},
          'initialPublicPreparation':initial,'toolSHA256':sha(__file__),'templateSHA256':sha(template),'actualBuild':False,'scope':'Combined enabled SDK sandbox configuration only; no provider/device/production acceptance.'}
 write(parent/'Preparation126.json',receipt)
 need(inventory(ROOT/'Unity')==main,'MainChangedDuringPrivatePreparation126')
 return {'status':receipt['status'],'project':str(project),'receipt':str(parent/'Preparation126.json'),'inputs':len(private),'guids':len(guid)}

def refresh(receipt_path,tag):
 need(re.fullmatch('[A-Za-z0-9_]{1,24}',tag or ''),'FreshSafeRefreshTagRequired126')
 receipt_path=receipt_path.resolve();receipt=json.loads(receipt_path.read_text('utf-8'));project=Path(receipt['project']).resolve()
 need(project.is_relative_to(PRIVATE.resolve()) and receipt_path.parent==project.parent,'OwnedPreparedProjectRequired126')
 need(not (project/'Builds/HeartOfTheRain_SDK126_Sandbox.apk').exists(),'CannotRebaseCompletedApk126')
 archive=project.parent/'Epochs'/tag;archive.mkdir(parents=True,exist_ok=False);shutil.copyfile(receipt_path,archive/'Preparation126.json')
 ads=module('refresh_ads126',ROOT/'Verification/Tools/Review107/prepare_ads107.py')
 changed=[]
 refresh_paths=['Assets/HeartOfTheRain/App/Advertising/Editor/'+name for name in ('AdvertisingCombinedBoundary126.cs','AdvertisingCombined126Verification.cs')]
 refresh_paths += ['Assets/HeartOfTheRain/App/ServerGameplay/Editor/'+name for name in ('SdkCheckoutBuild125.cs','SdkCheckout125Verification.cs')]
 refresh_paths += ['Assets/HeartOfTheRain/App/RuStore/Editor/SdkVendorBindings125.cs']
 for relative in refresh_paths:
  source=ROOT/'Unity'/relative;target=project/relative
  if sha(source)==sha(target):continue
  old=archive/relative;old.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,old);shutil.copyfile(source,target)
  receipt['mainInputs'][relative]=sha(source);changed.append(relative)
 old=project/'Assets/Review126Editor/MonetizationBuild126.cs';target=project/'Assets/Review126Editor/Editor/MonetizationBuild126.cs'
 if old.exists():
  need(old.resolve().is_relative_to((project/'Assets/Review126Editor').resolve()),'ContainedPrivateBuilderRequired126')
  shutil.copyfile(old,archive/'MonetizationBuild126.cs');target.parent.mkdir(exist_ok=False)
  Path(str(target.parent)+'.meta').write_bytes(ads.meta('Assets/Review126Editor/Editor',True))
  shutil.copyfile(old,target);shutil.copyfile(Path(str(old)+'.meta'),Path(str(target)+'.meta'))
  old.unlink();Path(str(old)+'.meta').unlink();changed.append('TechnicalBuilderMovedToEditorAssembly')
 template=Path(__file__).with_name('MonetizationBuild126.cs.template')
 if sha(target)!=sha(template):shutil.copyfile(target,archive/'PriorBuilder.cs');shutil.copyfile(template,target);changed.append('TechnicalBuilderSourceUpdated')
 private=inventory(project);pins={p:h for p,h in private.items() if p.startswith('Assets/') and not p.endswith('.meta') and p!='Assets/Plugins/Android/AndroidManifest.xml'
  and not p.startswith('Assets/RustoreSDK/') and not p.startswith('Assets/Plugins/Android/RuStoreSDKSettings.androidlib/')}
 guid=guids(project);receipt.update(paths=list(pins),sha256=list(pins.values()),metaPaths=list(guid),metaGuids=list(guid.values()),inputs=private,previousReceiptSHA256=sha(archive/'Preparation126.json'),sourceDelta=changed,toolSHA256=sha(__file__),templateSHA256=sha(template))
 receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 return {'status':'REFRESHED_PRIVATE_MONETIZATION126','changed':changed,'receipt':str(receipt_path)}

def run(receipt_path,tag,build,timeout):
 need(re.fullmatch('[A-Za-z0-9_]{1,30}',tag or ''),'FreshSafeRunTagRequired126')
 receipt_path=receipt_path.resolve();receipt=json.loads(receipt_path.read_text('utf-8'));project=Path(receipt['project']).resolve()
 need(project.is_relative_to(PRIVATE.resolve()) and receipt_path.parent==project.parent,'OwnedPreparedProjectRequired126')
 need(receipt['status']=='PREPARED_MONETIZATION126' and sha(Path(__file__).with_name('MonetizationBuild126.cs.template'))==receipt['templateSHA256'],'PreparedTemplateChanged126')
 # The first vendor configuration/import adds technical generated settings;
 # all original source pins and GUIDs remain checked natively on each run.
 for p,digest in zip(receipt['paths'],receipt['sha256']):need(sha(project/p)==digest,'PreparedSourceChanged126')
 output=OUT/tag;output.mkdir(parents=True,exist_ok=False)
 raw=project.parent/'Runs'/tag;raw.mkdir(parents=True,exist_ok=False)
 password=None;signing=None
 env={k:v for k,v in os.environ.items() if not k.startswith('HOTR_')}
 need(not any(env.get(k) for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')),'UnreviewedJavaOptionsRejected126')
 env.update(HOTR_MONETIZATION126_RECEIPT=str(receipt_path),HOTR_MONETIZATION126_OUT=str(output),HOTR_SDK125_PACKAGING_PROJECT=str(project),HOTR_RUSTORE_RELEASE_CONFIG=str(PROFILES/'release.sandbox.json'))
 # Keep Maven's long artifact names within Windows' path limit. This private
 # cache is separate from ordinary projects and is bound to this candidate.
 gradle_home=Path('E:/G126A');cache_marker=gradle_home/'.hotr-combined126-cache.json'
 if not gradle_home.exists():
  cache_custody=module('cache_signing126',ROOT/'Release/Signing/manage_release_signing.py')
  cache_custody.private_directory(gradle_home)
  write(cache_marker,{'version':1,'project':str(project),'nonce':receipt['nonce']})
  cached=Path('E:/HR107G/caches/modules-2')
  if cached.exists():shutil.copytree(cached,gradle_home/'caches/modules-2',ignore=shutil.ignore_patterns('*.lock','*.lck','gc.properties'))
 need(cache_marker.exists() and json.loads(cache_marker.read_text('utf-8'))=={'version':1,'project':str(project),'nonce':receipt['nonce']},'UnknownPrivateGradleCacheRejected126')
 env['GRADLE_USER_HOME']=str(gradle_home)
 apk=project/'Builds/HeartOfTheRain_SDK126_Sandbox.apk'
 if build:
  need(not apk.exists(),'FreshApkRequired126')
  signing=module('signing126',ROOT/'Release/Signing/manage_release_signing.py');password=signing.local_password(CUSTODY)
  signing.verify(CUSTODY,ANDROID/'OpenJDK',password)
  env.update(HOTR_RELEASE_SIGNING_PASSWORD=password,HOTR_RELEASE_KEYSTORE=str(CUSTODY/signing.KEYSTORE),HOTR_MONETIZATION126_APK=str(apk))
 sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'));from run_ads85_native import OwnedJob
 before=inventory(ROOT/'Unity');write(output/'MainBefore.json',before)
 entry='HeartOfTheRain.Verification.MonetizationBuild126.'+('BuildSandbox' if build else 'RunPackaging')
 command=[str(EDITOR),'-batchmode','-projectPath',str(project),'-buildTarget','Android','-executeMethod',entry,'-logFile',str(raw/'Unity.log')]
 snapshot_delta=sorted(k for k in set(receipt['mainInputs'])|set(before) if receipt['mainInputs'].get(k)!=before.get(k))
 shutil.copyfile(__file__,output/'Runner126.py')
 process=job=None;started=time.monotonic();record={'status':'RUNNING','entry':entry,'project':str(project),'receiptSHA256':sha(receipt_path),'runnerSHA256':sha(__file__),'startedUtc':datetime.now(timezone.utc).isoformat(),'actualBuildRequested':build,'newerMainPathsBeforeInvocation':snapshot_delta,'sourceScope':'Sealed private source snapshot. Newer concurrent Main edits are retained separately and not certified by this APK.'}
 try:
  job=OwnedJob()
  with (raw/'Console.log').open('xb') as stream:
   process=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);job.assign(process.pid);record['pid']=process.pid
   process.wait(timeout=timeout)
  record['exitCode']=process.returncode
 finally:
  if job:job.close()
  if process and process.poll() is None:
   try:process.wait(timeout=20)
   except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
  # Ended, ACL-protected generated Gradle state can contain Unity's temporary
  # signing config. Remove the literal password before retaining diagnostics.
  scrubbed=[]
  if password:
   secret=password.encode('ascii')
   for base in (project/'Library',project/'Temp',gradle_home,raw):
    if not base.exists():continue
    for p in base.rglob('*'):
     if not p.is_file() or p.suffix.lower() not in ('.gradle','.properties','.json','.txt','.log','.yaml','.xml','.bat','.cmd','.rsp'):continue
     data=p.read_bytes()
     if secret in data:
      p.write_bytes(data.replace(secret,b'<private-signing-password-removed>'))
      scrubbed.append(p.relative_to(project.parent).as_posix() if p.is_relative_to(project.parent) else 'PrivateGradleHome/'+p.relative_to(gradle_home).as_posix())
  for name in ('Unity.log','Console.log'):
   p=raw/name
   if p.is_file():shutil.copyfile(p,output/name)
  if password:
   for p in output.rglob('*'):
    if p.is_file():
     data=p.read_bytes()
     if secret in data:p.write_bytes(data.replace(secret,b'<private-signing-password-removed>'))
  record.update(processStopped=process is None or process.poll() is not None,elapsedSeconds=round(time.monotonic()-started,3),signingDiagnosticsScrubbed=scrubbed)
  native=json.loads((output/'Native.json').read_text('utf-8')) if (output/'Native.json').exists() else {}
  after=inventory(ROOT/'Unity');record['mainInputsUnchanged']=before==after
  record['mainPathsChangedDuringInvocation']=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
  record['mainSettingsUnchanged']=all(before.get(k)==after.get(k) for k in ('ProjectSettings/ProjectSettings.asset','ProjectSettings/ProjectVersion.txt'))
  expected='PASS_COMBINED_MONETIZATION126_ANDROID_BUILD' if build else 'PASS_COMBINED_MONETIZATION126_PACKAGING'
  record['nativeStatus']=native.get('status','MISSING');record['status']='PASS' if record.get('exitCode')==0 and native.get('status')==expected and native.get('sourcePinsPreserved') and native.get('metaGuidsPreserved') and record['mainSettingsUnchanged'] else 'FAIL'
  record['nativeSHA256']=sha(output/'Native.json') if native else None
  write(output/'Process.json',record)
 need(record['status']=='PASS','CombinedNativeInvocationFailed126')
 return {'status':record['status'],'output':str(output.relative_to(ROOT)),'nativeStatus':record['nativeStatus'],'apk':str(apk) if build else None}

def main():
 parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
 p=sub.add_parser('prepare');p.add_argument('--tag',required=True)
 p=sub.add_parser('refresh');p.add_argument('--receipt',required=True,type=Path);p.add_argument('--tag',required=True)
 p=sub.add_parser('run');p.add_argument('--receipt',required=True,type=Path);p.add_argument('--tag',required=True);p.add_argument('--build',action='store_true');p.add_argument('--timeout',type=int,default=2400)
 args=parser.parse_args()
 if args.command=='prepare':return prepare(args.tag)
 if args.command=='refresh':return refresh(args.receipt,args.tag)
 need(60<=args.timeout<=3600,'BoundedNativeTimeoutRequired126');return run(args.receipt,args.tag,args.build,args.timeout)
if __name__=='__main__':
 try:print(json.dumps(main()))
 except Exception as e:
  print(json.dumps({'status':'BLOCKED_COMBINED126','reason':str(e) if re.fullmatch('[A-Za-z0-9_]{1,120}',str(e)) else type(e).__name__}));raise SystemExit(1)
