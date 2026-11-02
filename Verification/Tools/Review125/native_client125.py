"""Seal a fresh private source cut and run scoped native Unity 2022 checks."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[3]
EDITOR=Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe')
OUT=ROOT/'Verification/Evidence/Review125/NativeClient'
SUITES={
 'sdk':('HeartOfTheRain.App.ServerGameplay.Editor.SdkCheckout125Verification.Run','HOTR_REVIEW125_OUT','SdkCheckout125.json','PASS_NATIVE_SDK_CHECKOUT125'),
 'http':('HeartOfTheRain.App.ServerGameplay.Editor.SdkCheckout125HttpVerification.Run','HOTR_REVIEW125_OUT','SdkHttp125.json','PASS_NATIVE_SDK_HTTP125'),
 'production':('HeartOfTheRain.App.ServerGameplay.Editor.ProductionClient122Verification.Run','HOTR_REVIEW122_OUT','ProductionClient122.json','PASS_NATIVE_PRODUCTION_CLIENT122'),
 'identity':('HeartOfTheRain.Verification.Identity82Verification.Run','HOTR_IDENTITY82_OUTPUT','Native/Identity82.json','PASS_NATIVE_IDENTITY82'),
 'checkout':('HeartOfTheRain.Verification.ShopCheckout86Verification.Run','HOTR_CHECKOUT86_OUTPUT','Native/ShopCheckout86.json','PASS_NATIVE_SHOP_CHECKOUT86'),
 'rustore':('HeartOfTheRain.Verification.RuStore81Verification.Run','HOTR_RUSTORE81_OUTPUT','Native/RuStore81.json','PASS_NATIVE_RUSTORE81_RELEASE_GUARD'),
 'configuration':('HeartOfTheRain.Verification.ServerConfiguration104Verification.Run','HOTR_REVIEW104_OUT','Native/ServerConfiguration104.json','PASS_NATIVE_SERVER_CONFIGURATION104'),
}
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def inventory(project):
 return {p.relative_to(project).as_posix():digest(p) for tree in ('Assets','Packages','ProjectSettings') for p in sorted((project/tree).rglob('*')) if p.is_file()}
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def snapshot(tag):
 project=Path(r'E:\HR125U')/tag/'Game'
 if project.exists():raise RuntimeError('FreshPrivateProjectRequired')
 before=inventory(ROOT/'Unity');project.mkdir(parents=True)
 for name,sha in before.items():
  source=ROOT/'Unity'/name;target=project/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
  if digest(target)!=sha:raise RuntimeError('SourceChangedDuringCopy')
 if inventory(ROOT/'Unity')!=before:raise RuntimeError('ConcurrentMainSourceChangeDuringSnapshot')
 settings=project/'ProjectSettings/ProjectSettings.asset';raw=settings.read_bytes()
 normalized=raw.decode().replace('\r\n','\n')
 block=re.search(r'^  applicationIdentifier:\n(?:    .*\n)+',normalized,re.M)
 if block is None:raise RuntimeError('ApplicationIdentifierBlockRequired')
 text=block.group()
 if '    Standalone:' in text:updated=re.sub(r'^    Standalone:.*$', '    Standalone: com.heartoftherain.productionfixture',text,flags=re.M)
 else:updated=text+'    Standalone: com.heartoftherain.productionfixture\n'
 normalized=normalized[:block.start()]+updated+normalized[block.end():]
 settings.write_bytes(normalized.replace('\n','\r\n' if b'\r\n' in raw else '\n').encode())
 private=inventory(project)
 guids={name:re.search(rb'^guid: ([0-9a-f]{32})', (project/name).read_bytes(),re.M).group(1).decode() for name in private if name.endswith('.meta') and re.search(rb'^guid: ([0-9a-f]{32})', (project/name).read_bytes(),re.M)}
 longest=max((str(project/name) for name in private),key=len)
 if len(longest)>=260:raise RuntimeError('WindowsPathTooLong')
 release={p.relative_to(ROOT).as_posix():digest(p) for p in sorted((ROOT/'Release').rglob('*')) if p.is_file() and p.suffix.lower() in ('.json','.txt','.md')}
 manifest={'status':'SEALED_PRIVATE_UNITY125_SOURCE','createdUtc':datetime.now(timezone.utc).isoformat(),'project':str(project),'mainInputs':before,'inputs':private,'GUIDs':guids,'publicReleaseInputs':release,
 'privateSettingsOverlay':'Standalone package only: com.heartoftherain.productionfixture for inherited122 resource checks; Android package and main settings unchanged.',
 'mainSettingsSHA256':before['ProjectSettings/ProjectSettings.asset'],'maximumPathLength':len(longest),'scope':'Source snapshot, not acceptance. Current unrelated work is preserved in the cut and may change later.'}
 path=OUT/f'SourceManifest125_{tag}.json';write(path,manifest)
 print(json.dumps({'manifest':str(path.relative_to(ROOT)),'project':str(project),'inputs':len(private),'GUIDs':len(guids),'maximumPathLength':len(longest)}))
def rebase(tag,manifest_path):
 prior_path=(ROOT/manifest_path).resolve();prior=json.loads(prior_path.read_bytes());project=Path(prior['project'])
 if inventory(project)!=prior['inputs']:raise RuntimeError('PriorPrivateSourceChanged')
 current=inventory(ROOT/'Unity');removed=sorted(set(prior['mainInputs'])-set(current))
 if removed:raise RuntimeError('RemovedMainInputsRequireNewSnapshot')
 retain=ROOT/'.verification-cache/Review125/RetainedSources'/tag;retain.mkdir(parents=True,exist_ok=False)
 changed=[]
 for name,sha in current.items():
  if name=='ProjectSettings/ProjectSettings.asset':
   if sha!=prior['mainSettingsSHA256']:raise RuntimeError('MainSettingsChangedRequiresNewSnapshot')
   continue
  if sha==prior['mainInputs'].get(name):continue
  target=project/name
  if target.exists():
   old=retain/name;old.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,old)
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'Unity'/name,target);changed.append(name)
 if current!=inventory(ROOT/'Unity'):raise RuntimeError('ConcurrentMainSourceChangeDuringRebase')
 private=inventory(project);guids={name:re.search(rb'^guid: ([0-9a-f]{32})',(project/name).read_bytes(),re.M).group(1).decode() for name in private if name.endswith('.meta') and re.search(rb'^guid: ([0-9a-f]{32})',(project/name).read_bytes(),re.M)}
 result=dict(prior,createdUtc=datetime.now(timezone.utc).isoformat(),mainInputs=current,inputs=private,GUIDs=guids,previousManifestSHA256=digest(prior_path),sourceDelta=changed,
 publicReleaseInputs={p.relative_to(ROOT).as_posix():digest(p) for p in sorted((ROOT/'Release').rglob('*')) if p.is_file() and p.suffix.lower() in ('.json','.txt','.md')})
 path=OUT/f'SourceManifest125_{tag}.json';write(path,result);print(json.dumps({'manifest':str(path.relative_to(ROOT)),'changedPaths':changed,'inputs':len(private),'GUIDs':len(guids)}))
def run(suite,tag,manifest_path,descriptor=None,checkpoint=None,phase=None):
 manifest_path=(ROOT/manifest_path).resolve();manifest=json.loads(manifest_path.read_bytes());project=Path(manifest['project'])
 if project.resolve()==(ROOT/'Unity').resolve() or not EDITOR.is_file():raise RuntimeError('IsolatedPinnedEditorRequired')
 if inventory(project)!=manifest['inputs']:raise RuntimeError('SealedPrivateSourceChangedBeforeInvocation')
 output=OUT/(suite+'_'+tag);private=ROOT/'.verification-cache/Review125/NativeLogs'/(suite+'_'+tag)
 output.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False)
 method,variable,filename,expected=SUITES[suite]
 env={k:v for k,v in os.environ.items() if not k.startswith('HOTR_')};env[variable]=str(output)
 env['HOTR_REVIEW125_ISOLATED_PROJECT']=str(project);env['HOTR_REVIEW122_ISOLATED_PROJECT']=str(project)
 receipt={'status':'RUNNING','startedUtc':datetime.now(timezone.utc).isoformat(),'method':method,'project':str(project),'editorVersion':'2022.3.62f3','editorSHA256':digest(EDITOR),
 'sourceManifestSHA256':digest(manifest_path),'toolSHA256':digest(__file__),'actualUnityEditor':True,'actualHttp':False,'actualSdkPayment':False,'actualAndroid':False,'productionActivated':False}
 if suite=='rustore':
  name='Release/RuStore/release.example.json';source=ROOT/name;target=project.parent/name;expected_fixture=manifest['publicReleaseInputs'][name]
  if digest(source)!=expected_fixture:raise RuntimeError('PinnedPublicReleaseFixtureChanged')
  if target.exists():
   if digest(target)!=expected_fixture:raise RuntimeError('ForeignPrivateReleaseFixturePreserved')
  else:target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
  receipt['externalPublicFixtures']={name:expected_fixture}
 if suite=='http':
  descriptor=Path(descriptor).resolve();checkpoint=Path(checkpoint).resolve();allowed=(ROOT/'.verification-cache/Review125').resolve()
  if not descriptor.is_relative_to(allowed) or not checkpoint.is_relative_to(allowed) or phase not in ('initial','resume'):raise RuntimeError('PrivateHttpFixtureRequired')
  config=json.loads(descriptor.read_bytes());origin=config['origin'];parts=urlsplit(origin)
  if parts.scheme!='http' or parts.hostname!='127.0.0.1' or parts.path or parts.query or parts.fragment or not config.get('syntheticSdkObservationsOnly'):raise RuntimeError('SyntheticLoopbackOnly')
  for path in ('/healthz','/readyz'):
   with urllib.request.urlopen(origin+path,timeout=5) as response:
    if response.status!=200:raise RuntimeError('HealthyReadyFixtureRequired')
    if len(response.read(65537))>65536:raise RuntimeError('BoundedProbeRequired')
  env.update(HOTR_REVIEW125_HTTP_DESCRIPTOR=str(descriptor),HOTR_REVIEW125_HTTP_CHECKPOINT=str(checkpoint),HOTR_REVIEW125_HTTP_PHASE=phase)
  receipt.update(actualHttp=True,syntheticSdk=True,privateDescriptorSHA256=digest(descriptor),healthAndReadinessHttp200=True,phase=phase)
 try:
  with (private/'Console.log').open('xb') as console:
   completed=subprocess.run([str(EDITOR),'-batchmode','-projectPath',str(project),'-executeMethod',method,'-logFile',str(private/'Unity.log')],cwd=project,env=env,stdout=console,stderr=subprocess.STDOUT,timeout=1200,creationflags=subprocess.CREATE_NO_WINDOW)
  receipt['exitCode']=completed.returncode;native=json.loads((output/filename).read_text('utf-8-sig')) if (output/filename).is_file() else {}
  cases=native.get('cases',0)
  receipt.update(nativeStatus=native.get('status','MISSING'),checks=native.get('checks',0),cases=len(cases) if isinstance(cases,list) else cases,errors=native.get('errors',[]))
  after=inventory(project);changed=[name for name in set(after)|set(manifest['inputs']) if after.get(name)!=manifest['inputs'].get(name)]
  receipt['sourceUnchanged']=not changed;receipt['changedSourcePaths']=sorted(changed)
  receipt['status']='PASS_UNITY_EDITOR_CLIENT125' if completed.returncode==0 and native.get('status')==expected and not native.get('errors') and not changed else 'FAIL_UNITY_EDITOR_CLIENT125'
  if (output/filename).is_file():receipt['nativeReportSHA256']=digest(output/filename)
 except subprocess.TimeoutExpired:receipt['status']='TIMEOUT_UNITY_EDITOR_CLIENT125'
 receipt['finishedUtc']=datetime.now(timezone.utc).isoformat();write(output/'Invocation125.json',receipt);print(json.dumps(receipt))
 return 0 if receipt['status']=='PASS_UNITY_EDITOR_CLIENT125' else 1
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=['snapshot','rebase']+list(SUITES));parser.add_argument('--tag',required=True);parser.add_argument('--manifest');parser.add_argument('--descriptor');parser.add_argument('--checkpoint');parser.add_argument('--phase',choices=['initial','resume'])
 args=parser.parse_args()
 if not re.fullmatch(r'[A-Za-z0-9_]{1,24}',args.tag):parser.error('Fresh safe tag required')
 if args.operation=='snapshot':snapshot(args.tag);return 0
 if not args.manifest:parser.error('--manifest required')
 if args.operation=='rebase':rebase(args.tag,args.manifest);return 0
 if args.operation=='http' and (not args.descriptor or not args.checkpoint or not args.phase):parser.error('Private HTTP descriptor, checkpoint and phase required')
 return run(args.operation,args.tag,args.manifest,args.descriptor,args.checkpoint,args.phase)
if __name__=='__main__':raise SystemExit(main())
