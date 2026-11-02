"""Scoped isolated Unity2022 advertising checks; no Play Mode/provider/profile IO."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'Verification/Evidence/Review126/Advertising'
EDITOR=Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe')
SPEC=importlib.util.spec_from_file_location('client125_inventory',ROOT/'Verification/Tools/Review125/native_client125.py')
INVENTORY=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(INVENTORY)
SUITES={
 'journal':('HeartOfTheRain.Verification.RewardedAdsJournal85Verification.Run','HOTR_REWARDED_ADS85_OUTPUT','Native/RewardedAdsJournal85.json','PASS_NATIVE_REWARDED_ADS_JOURNAL85'),
 'flow':('HeartOfTheRain.Verification.RewardedAdsFlow85Verification.Run','HOTR_ADS85_OUTPUT','Native/RewardedAdsFlow85.json','PASS_NATIVE_REWARDED_ADS_FLOW85'),
 'parser':('HeartOfTheRain.Verification.RewardedAdsParser85Verification.Run','HOTR_REWARDED_ADS85_OUTPUT','Native/RewardedAdsParser85.json','PASS_NATIVE_REWARDED_ADS85_PARSER'),
 'boundary':('HeartOfTheRain.App.Advertising.Editor.AdvertisingCombined126Verification.Run','HOTR_REVIEW126_ADVERTISING_OUT','AdvertisingCombined126.json','PASS_NATIVE_COMBINED_ADVERTISING126')}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def seal(tag,previous):
 previous=(ROOT/previous).resolve();prior=json.loads(previous.read_bytes());project=Path(prior['project'])
 if project.resolve()==(ROOT/'Unity').resolve() or INVENTORY.inventory(project)!=prior['inputs']:raise RuntimeError('OwnedPreviouslySealedIsolatedSourceRequired')
 current=INVENTORY.inventory(ROOT/'Unity');retain=ROOT/'.verification-cache/Review126/AdvertisingRetained'/tag;retain.mkdir(parents=True,exist_ok=False);changed=[]
 for name,value in current.items():
  if name=='ProjectSettings/ProjectSettings.asset':
   if value!=prior['mainSettingsSHA256']:raise RuntimeError('MainSettingsChanged')
   continue
  if value==prior['mainInputs'].get(name):continue
  target=project/name
  if target.exists():old=retain/name;old.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,old)
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'Unity'/name,target);changed.append(name)
 if set(prior['mainInputs'])-set(current):raise RuntimeError('RemovedMainSourceNeedsNewProject')
 if current!=INVENTORY.inventory(ROOT/'Unity'):raise RuntimeError('ConcurrentMainSourceEdit')
 sealed=INVENTORY.inventory(project)
 result={'status':'SEALED_PRIVATE_ADVERTISING126_SOURCE','utc':datetime.now(timezone.utc).isoformat(),'project':str(project),'inputs':sealed,'mainInputs':current,'mainSettingsSHA256':current['ProjectSettings/ProjectSettings.asset'],
 'previousManifestSHA256':sha(previous),'sourceDelta':changed,'scope':'Reuses only a previously sealed private2022 project/cache. Current main source copied/pinned; original main settings and foreign Editor untouched. Existing private Standalone package fixture overlay preserved.'}
 output=OUT/f'SourceManifest126_{tag}.json';write(output,result);print(json.dumps({'status':result['status'],'manifest':str(output.relative_to(ROOT)),'changedPaths':changed,'inputs':len(sealed)}))
def run(suite,tag,manifest):
 manifest=(ROOT/manifest).resolve();cut=json.loads(manifest.read_bytes());project=Path(cut['project'])
 if INVENTORY.inventory(project)!=cut['inputs']:raise RuntimeError('SealedSourceChanged')
 output=OUT/(suite+'_'+tag);private=ROOT/'.verification-cache/Review126/AdvertisingLogs'/(suite+'_'+tag);output.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False)
 method,variable,filename,expected=SUITES[suite];env={k:v for k,v in os.environ.items() if not k.startswith('HOTR_')};env[variable]=str(output)
 report={'status':'RUNNING','startedUtc':datetime.now(timezone.utc).isoformat(),'sourceManifestSHA256':sha(manifest),'toolSHA256':sha(__file__),'method':method,'project':str(project),'actualEditor':True,'actualProviderRequest':False,'actualAndroid':False,'actualHttp':False,'sharedProfilesOrPreferencesUsed':False}
 with (private/'Console.log').open('xb') as stream:result=subprocess.run([str(EDITOR),'-batchmode','-projectPath',str(project),'-executeMethod',method,'-logFile',str(private/'Unity.log')],cwd=project,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
 native=json.loads((output/filename).read_text('utf-8-sig')) if (output/filename).is_file() else {};after=INVENTORY.inventory(project);changed=sorted(name for name in set(after)|set(cut['inputs']) if after.get(name)!=cut['inputs'].get(name))
 report.update(exitCode=result.returncode,nativeStatus=native.get('status','MISSING'),checks=native.get('checks',0),cases=native.get('cases',0),errors=native.get('errors',[]),sourceUnchanged=not changed,changedSourcePaths=changed,finishedUtc=datetime.now(timezone.utc).isoformat())
 report['status']='PASS_NATIVE_ADVERTISING126' if result.returncode==0 and native.get('status')==expected and not report['errors'] and not changed else 'FAIL_NATIVE_ADVERTISING126'
 if (output/filename).is_file():report['nativeReportSHA256']=sha(output/filename)
 write(output/'Invocation126.json',report);print(json.dumps(report));return 0 if report['status'].startswith('PASS') else 1
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=['seal']+list(SUITES));p.add_argument('--tag',required=True);p.add_argument('--manifest',required=True);a=p.parse_args()
 if not a.tag.replace('_','').isalnum():p.error('Safe fresh tag required')
 if a.operation=='seal':seal(a.tag,a.manifest);return 0
 return run(a.operation,a.tag,a.manifest)
if __name__=='__main__':raise SystemExit(main())
