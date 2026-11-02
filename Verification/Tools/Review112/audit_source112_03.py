"""Read-only Unity asset/source audit after final 112 freeze; no Unity invocation."""
from pathlib import Path
import hashlib,importlib.util,json,re
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'Verification/Evidence/Review112'
BASE=ROOT/'Verification/Evidence/Review111/MainSourcesFinal111.json'
BASE_GUID=ROOT/'Verification/Evidence/Review111/AssetGuidsFinal111.json'
PKG=ROOT/'.verification-cache/Teams112/Package/Heart_of_the_Rain_Teams_Invite_R1/Unity'
SCRIPT=ROOT/'Verification/Tools/Ads85/run_ads85_native.py'
spec=importlib.util.spec_from_file_location('scan112',SCRIPT);api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
def record(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def guids():
 values={}
 for p in (ROOT/'Unity/Assets').rglob('*.meta'):
  m=re.findall(rb'(?m)^guid:\s*([0-9a-fA-F]{32})\s*$',p.read_bytes())
  if len(m)!=1:raise RuntimeError('invalid metadata '+str(p))
  values[p.relative_to(ROOT/'Unity').as_posix()]=m[0].decode('ascii').lower()
 if len(values)!=len(set(values.values())):raise RuntimeError('guid collision')
 return values
before=load(BASE);prior=before['files'];oldguids=load(BASE_GUID);first=api.freeze();g=guids();now=first['files']
changed=[k for k in sorted(prior.keys()&now.keys()) if prior[k]!=now[k]]
added=sorted(now.keys()-prior.keys());removed=sorted(prior.keys()-now.keys())
oldmeta=[k for k in prior if k.endswith('.meta')];oldart=[k for k in prior if k.endswith(('.png','.jpg','.jpeg','.psd','.asset','.prefab','.unity','.mat'))]
metadiff=[k for k in oldmeta if now.get(k)!=prior[k]];artdiff=[k for k in oldart if now.get(k)!=prior[k]]
guiddiff=[k for k in oldguids if g.get(k)!=oldguids[k]]
client=load(OUT/'ClientFreeze112_11.json')['runtimeFiles'];clientdiff=[x['path'] for x in client if now.get(x['path'])!={'sha256':x['sha256'],'bytes':x['bytes']}]
package=load(OUT/'PackageReview112.json')['newPayloads'];packageChecks=[]
for x in package:
 p=ROOT/'Unity'/x['path'];packageChecks.append({'path':p.relative_to(ROOT).as_posix(),'matches':record(p)=={'sha256':x['sha256'],'bytes':x['bytes']}})
new_package_guids=[]
for p in PKG.rglob('*.meta'):
 rel=p.relative_to(PKG).as_posix()
 if rel not in oldguids:
  m=re.findall(rb'(?m)^guid:\s*([0-9a-fA-F]{32})\s*$',p.read_bytes())
  if len(m)!=1:raise RuntimeError('bad package meta '+rel)
  new_package_guids.append({'path':rel,'guid':m[0].decode('ascii').lower(),'matches':g.get(rel)==m[0].decode('ascii').lower()})
# Locate byte-exact pre-change sources if available. Do not claim a retained
# original merely because a same-named file exists.
retained=ROOT/'Verification/Evidence/Review112/RetainedSources';lookup={}
for p in retained.rglob('*'):
 if p.is_file():lookup.setdefault(record(p)['sha256'],[]).append(p.relative_to(ROOT).as_posix())
changed_rows=[]
for k in changed:
 old=prior[k];matches=lookup.get(old['sha256'],[])
 changed_rows.append({'path':k,'before':old,'after':now[k],'exactPriorCopies':matches})
second=api.freeze();g2=guids();stable=first==second and g==g2
if not stable or removed or metadiff or artdiff or guiddiff or clientdiff or not all(x['matches'] for x in packageChecks+new_package_guids):raise RuntimeError('source audit integrity failed')
OUT.joinpath('MainSourcesFinal112_03.json').write_text(json.dumps(first,indent=2)+'\n',encoding='utf-8')
OUT.joinpath('AssetGuidsFinal112_03.json').write_text(json.dumps(g,indent=2,sort_keys=True)+'\n',encoding='utf-8')
result={'status':'PASS_READ_ONLY_SOURCE_AUDIT','scope':'Twice scanned Unity Assets, Packages and ProjectSettings; no Unity/device/service action. Exact original-source hash manifest is preserved even where prior bytes were not retained.','baseline':str(BASE.relative_to(ROOT)),'baselineRecord':record(BASE),'baselineGuids':str(BASE_GUID.relative_to(ROOT)),'baselineGuidsRecord':record(BASE_GUID),'clientFreeze':'Verification/Evidence/Review112/ClientFreeze112_11.json','final':'Verification/Evidence/Review112/MainSourcesFinal112_03.json','finalGuids':'Verification/Evidence/Review112/AssetGuidsFinal112_03.json','baselineInputs':len(prior),'finalInputs':len(now),'oldGuidCount':len(oldguids),'finalGuidCount':len(g),'unchangedOriginalMetadataCount':len(oldmeta),'unchangedOriginalArtworkAndSerializedCount':len(oldart),'changed':changed_rows,'added':added,'removed':removed,'packagePayloads':packageChecks,'packageNewGuids':new_package_guids,'doubleScanStable':stable,'missingRetainedPriorBytes':[x['path'] for x in changed_rows if not x['exactPriorCopies']]}
earlier=load(OUT/'MainSourcesFinal112_02.json')['files']
result['sinceEpoch02']={'changed':[k for k in sorted(earlier.keys()&now.keys()) if earlier[k]!=now[k]],'added':sorted(now.keys()-earlier.keys()),'removed':sorted(earlier.keys()-now.keys())}
result['earlierAuditRecord']=record(OUT/'SourceDelta112_02.json')
OUT.joinpath('SourceDelta112_03.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':result['status'],'baseline':len(prior),'final':len(now),'changed':len(changed),'added':len(added),'oldGuids':len(oldguids),'finalGuids':len(g),'newPackageGuids':len(new_package_guids),'priorBytesMissing':result['missingRetainedPriorBytes']},indent=2))
