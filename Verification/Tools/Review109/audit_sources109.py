"""Read source/evidence bytes only; no Unity/backend/test/process-control operation."""
from pathlib import Path
import datetime as dt
import difflib
import hashlib
import json
import os
import re

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'Verification/Evidence/Review109'
BASE=ROOT/'Verification/Tools/Review109/BaselineMain109.json'
GUIDS=ROOT/'Verification/Tools/Review109/BaselineGuids109.json'
PKG=ROOT/'.verification-cache/Teams109/Package/Heart_of_the_Rain_Teams_Access_Assets_R4'
PREFIX='Unity/Assets/HeartOfTheRain/'
CHANGED=tuple(PREFIX+p for p in ('App/Teams/Runtime/TeamsAssets.cs','App/OnlineSocial/Runtime/OnlineTeamsPage82.cs','App/OnlineSocial/Runtime/OnlineTeamsLayout82.cs','App/OnlineSocial/Runtime/SocialBackendClient82.cs','App/OnlineSocial/Runtime/SocialContracts82.cs','App/OnlineSocial/Runtime/SocialPageSession82.cs'))
TEST=PREFIX+'Verification/Editor/TeamsAccess109Verification.cs'

def need(value,code):
    if not value:raise ValueError(code)
def disk(p):
    text=str(Path(p).absolute())
    return '\\\\?\\'+text if os.name=='nt' and not text.startswith('\\\\?\\') else text
def raw(p):
    with open(disk(p),'rb') as f:return f.read()
def load(p):return json.loads(raw(p).decode('utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with open(disk(p),'rb') as f:
        for part in iter(lambda:f.read(1048576),b''):h.update(part)
    return h.hexdigest()
def bind(p):
    p=Path(p).resolve();need(p.is_relative_to(ROOT.resolve()),'EvidenceOutsideWorkspace109')
    return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=os.stat(disk(p)).st_size)
def delta(a,b):return dict(added=sorted(set(b)-set(a)),removed=sorted(set(a)-set(b)),changed=sorted(p for p in set(a)&set(b) if a[p]!=b[p]))
def inventory():
    found={}
    for part in ('Assets','Packages','ProjectSettings'):
        for directory,_,names in os.walk(disk(ROOT/'Unity'/part)):
            for name in names:
                p=Path(str(Path(directory)/name).removeprefix('\\\\?\\'))
                found[p.relative_to(ROOT).as_posix()]=dict(sha256=sha(p),bytes=os.stat(disk(p)).st_size)
    return dict(sorted(found.items()))
def endings(b):
    crlf,lf=b.count(b'\r\n'),b.count(b'\n')
    return dict(CRLF=crlf,LF=lf,bareCR=b.count(b'\r')-crlf,utf8Bom=b.startswith(b'\xef\xbb\xbf'),style='CRLF' if crlf==lf else 'LF' if crlf==0 else 'mixed')
def exclusive(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())

def main():
    base=load(BASE);baseline=base['files'];baseline_guids=load(GUIDS)
    receipt=load(ROOT/'Verification/Tools/Review109/Baseline109.json')
    need(receipt['status']=='SEALED_PREINTEGRATION_BASELINE109' and receipt['matchesSealed107108'] and len(baseline)==5502 and len(baseline_guids)==2874,'Pre109BaselineInvalid')
    need(sha(BASE)==receipt['sources']['sha256'] and sha(GUIDS)==receipt['guids']['sha256'],'Pre109BaselineHashMismatch')
    current=inventory();change=delta(baseline,current)
    package_paths={p.relative_to(PKG).as_posix() for p in (PKG/'Unity').rglob('*') if p.is_file()}
    need(len(package_paths)==151,'DeliveredPackage151Changed')
    other_additions={PREFIX+'App/TeamsAccess/Runtime.meta',PREFIX+'Resources/HOTR_TeamsAccess109.meta',PREFIX+'Resources/HOTR_TeamsAccess109/Assets.asset',PREFIX+'Resources/HOTR_TeamsAccess109/Assets.asset.meta',TEST,TEST+'.meta'}
    for name in ('TeamsAccessAssets109','TeamsAccessLayout109','TeamsAccessText109'):
        for suffix in ('.cs','.cs.meta'):other_additions.add(PREFIX+'App/TeamsAccess/Runtime/'+name+suffix)
    expected_added=sorted(package_paths|other_additions)
    need(change==dict(added=expected_added,removed=[],changed=sorted(CHANGED)) and len(current)==5665,'UnexpectedExistingUnityChangeOrAddition109')
    original_meta=[p for p in baseline if p.endswith('.meta')]
    need(all(current[p]==baseline[p] for p in original_meta),'OriginalMetaBytesChanged109')
    current_guids={}
    for relative in current:
        if relative.startswith('Unity/Assets/') and relative.endswith('.meta'):
            found=re.findall(rb'(?m)^guid:\s*([0-9a-f]{32})\s*$',raw(ROOT/relative));need(len(found)==1,'CurrentGuidMalformed109');current_guids[relative.removeprefix('Unity/')]=found[0].decode()
    need(len(current_guids)==2958 and len(set(current_guids.values()))==len(current_guids),'CurrentGuidCollision109')
    need(all(current_guids[p]==g for p,g in baseline_guids.items()),'OriginalGuidChanged109')
    pngs=[];data=[];package_metas=[]
    for relative in sorted(package_paths):
        source=PKG/relative;target=ROOT/relative
        if relative.endswith(('.png','.json')):
            need(raw(source)==raw(target),'DeliveredPackageArtworkOrDataChanged109')
            (pngs if relative.endswith('.png') else data).append(dict(source=bind(source),installed=bind(target),byteIdentical=True))
        elif relative.endswith('.meta'):
            a=re.findall(rb'(?m)^guid:\s*([0-9a-f]{32})\s*$',raw(source));b=re.findall(rb'(?m)^guid:\s*([0-9a-f]{32})\s*$',raw(target));need(len(a)==len(b)==1 and a==b,'SuppliedPackageGuidChanged109')
            package_metas.append(dict(path=relative,guid=a[0].decode(),sourceSHA256=sha(source),finalSHA256=sha(target),sourceMetaBytesEqual=raw(source)==raw(target)))
    need(len(pngs)==69 and len(data)==5 and len(package_metas)==77,'DeliveredPackageRoleCountsChanged109')
    impdir=OUT/'Native/ImportMain01';imp=load(impdir/'ImportNormalization109.json');ib=load(impdir/'MainSources_before.json')['files'];ia=load(impdir/'MainSources_after.json')['files']
    idelta=delta(ib,ia)
    need(imp['status']=='ACCEPTED_NEW_META_IMPORT109' and imp['originalMetasPreserved'] and imp['guidPreserved'],'ImportEpochNotAccepted109')
    need(not idelta['added'] and not idelta['removed'] and len(idelta['changed'])==69 and all(p not in baseline and p.startswith(PREFIX+'App/TeamsAccess/Art/') and p.endswith('.png.meta') for p in idelta['changed']),'ImportEpochChangedNonNewPngMeta109')
    for p in idelta['changed']:
        retained=impdir/'ImportMetaBefore'/Path(p).name
        need(sha(retained)==ib[p]['sha256'] and ia[p]==current[p],'ImportedMetaEpochNotRetainedOrChangedAgain109')
    epochs=[]
    for path in sorted((OUT/'Native').glob('*/Invocation.json')):
        inv=load(path)
        if inv.get('expectedEngine')!='2022.3.62f3':continue
        directory=path.parent;b=load(directory/'MainSources_before.json');a=load(directory/'MainSources_after.json')
        if inv.get('importEpoch'):
            need(directory.name=='ImportMain01' and inv['importNormalizationAccepted'],'UnexpectedImportEpoch109')
        else:need(a==b and inv['mainInputsUnchanged'],'NativeSourceMutatedWithinRun109')
        need(load(directory/'AssetGuids_before.json')==load(directory/'AssetGuids_after.json') and inv['assetGuidsUnchanged'],'NativeGuidMutation109')
        report=(directory/inv['nativeReport']).resolve();need(report.is_relative_to(directory.resolve()) and sha(report)==inv['nativeReportSHA256'],'NativeReportPathOrHashMismatch109');r=load(report)
        passed=inv['status']=='PASS_NATIVE109_INVOCATION'
        if passed:need(inv['exitCode']==0 and inv['actualEngine']=='2022.3.62f3' and r['status']==inv['expectedNativeStatus'] and not r.get('errors') and not inv.get('unityPidsAfter'),'PassedNativeProofInvalid109')
        count=r.get('checks');count=count if type(count) is int else r.get('passed',0)
        epochs.append(dict(tag=directory.name,status=inv['status'],nativeStatus=r['status'],checks=count,entry=inv['entry'],invocation=bind(path),report=bind(report),before=bind(directory/'MainSources_before.json'),after=bind(directory/'MainSources_after.json'),deltaToCurrent=delta(a['files'],current),withinRunPreserved=not inv.get('importEpoch'),importEpoch=inv.get('importEpoch',False)))
    required={'ImportMain01','TeamsMain06','ScrollMain01','GeneralMain01','Nav108Main01','Configuration104Main01'}
    need(required<={e['tag'] for e in epochs if e['status']=='PASS_NATIVE109_INVOCATION'},'RequiredPassedMainNativeEpochMissing109')
    team=next(e for e in epochs if e['tag']=='TeamsMain06')
    need(team['deltaToCurrent'] in (dict(added=[],removed=[],changed=[]),dict(added=[],removed=[],changed=[TEST])),'FinalTeamsRuntimeChangedAfterPass109')
    for e in epochs:
        if e['tag'] in required-{'ImportMain01'}:need(not e['deltaToCurrent']['added'] and not e['deltaToCurrent']['removed'] and set(e['deltaToCurrent']['changed'])<={TEST},'CalledRuntimeChangedAfterPassedMainProof109')
    testr=OUT/'RetainedSources/TeamsAccess109Verification_BeforeScrollEntry.cs.txt'
    tested=load(OUT/'Native/TeamsMain06/MainSources_after.json')['files'][TEST]
    if current[TEST]!=tested:need(sha(testr)==tested['sha256'],'EarlierPassedTestEpochNotRetained109')
    protected=[p for p in baseline if p not in CHANGED]
    teamasset=PREFIX+'App/Teams/TeamsAssets.asset';need(current[teamasset]==baseline[teamasset],'OriginalTeamsAssetGainedEagerDependency109')
    patch=[];changed_records=[]
    for relative in CHANGED:
        retained=OUT/'RetainedSources'/relative.removeprefix(PREFIX)
        need(sha(retained)==baseline[relative]['sha256'],'OriginalSourceNotRetained109')
        before,after=raw(retained),raw(ROOT/relative);old,new=endings(before),endings(after)
        need(all(old[k]==new[k] for k in ('style','bareCR','utf8Bom')),'ExistingLineEndingConventionChanged109')
        lines=lambda value:value.decode('utf-8-sig').replace('\r\n','\n').splitlines(keepends=True)
        patch.extend(difflib.unified_diff(lines(before),lines(after),fromfile=relative+' (pre109)',tofile=relative+' (final109)'))
        changed_records.append(dict(path=relative,before=baseline[relative],after=current[relative],retained=bind(retained),oldEndings=old,newEndings=new,lineEndingConventionPreserved=True))
    for relative in sorted(other_additions):
        if relative.endswith('.cs') and relative!=TEST or relative.endswith('/Assets.asset'):
            patch.extend(difflib.unified_diff([],raw(ROOT/relative).decode('utf-8-sig').replace('\r\n','\n').splitlines(keepends=True),fromfile='/dev/null',tofile=relative+' (added109)'))
    need(inventory()==current,'MainInputsChangedDuringReadOnlyAudit109')
    target=OUT/'SourceDelta109.json';patch_path=OUT/'SourceChanges109.patch';need(not target.exists() and not patch_path.exists(),'PreserveExistingSourceAudit109')
    exclusive(patch_path,''.join(patch).encode('utf-8'))
    result=dict(schemaVersion=1,status='VERIFIED_UNITY_TEAMS109_SOURCE_DELTA',utc=dt.datetime.now(dt.timezone.utc).isoformat(),auditTool=bind(Path(__file__)),baselineReceipt=bind(ROOT/'Verification/Tools/Review109/Baseline109.json'),baselineSources=bind(BASE),baselineGuids=bind(GUIDS),baselineInputCount=5502,finalInputCount=5665,unityDelta=change,existingChanges=changed_records,additions=[dict(path=p,**current[p]) for p in expected_added],allOtherOriginalInputsPreserved=True,protectedOriginalInputCount=len(protected),allOriginalMetasAndGuidsPreserved=True,originalGuidCount=2874,currentUniqueGuidCount=2958,originalTeamsAssetsByteIdentical=True,shared108NavigationAnd106GoalsAndOriginalArtworkLevelsSettingsPreserved=True,packageArchiveReview=bind(OUT/'ArchiveReview109.json'),packageIntegrity=bind(OUT/'PackageIntegrity109.json'),packagePngs=pngs,packageJson=data,packageMetas=package_metas,packagePngBytesIdentical=True,packageAll77GuidsPreserved=True,importEpoch=dict(proof=bind(impdir/'ImportNormalization109.json'),sourceDelta=idelta,normalizedNewPngMetaCount=69,originalMetasChanged=0,allGuidsPreserved=True,postImportMetasStillExactCurrent=True),nativeMainEpochs=epochs,requiredPassedMainScopes=sorted(required),retainedFailedMainTags=[e['tag'] for e in epochs if e['status']!='PASS_NATIVE109_INVOCATION'],testOnlyEpoch=dict(earlierPassedTeams=bind(OUT/'Native/TeamsMain06/MainSources_after.json'),currentTest=bind(ROOT/TEST),retainedEarlierTest=bind(testr),addedScrollEntryTestedSeparately=bind(OUT/'Native/ScrollMain01/Invocation.json'),runtimeStillExact=True),sourcePatch=bind(patch_path),scope='Read-only Unity source and existing evidence metadata audit. Exactly six existing Teams/social source files changed,163 additions. No suite, compiler, Unity, backend, build, SDK, network, process-control or device operation performed. First new69 PNG meta import normalization and later test-only epochs remain distinct. Backend and isolated build/device proofs are owned separately; this audit makes no production or physical acceptance claim.')
    exclusive(target,(json.dumps(result,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(status=result['status'],report=target.relative_to(ROOT).as_posix(),sha256=sha(target),changes=len(CHANGED),additions=len(expected_added))))
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,TypeError) as error:
        print(json.dumps(dict(status='BLOCKED_TEAMS109_SOURCE_AUDIT',code=str(error) if isinstance(error,ValueError) else type(error).__name__,sealed=False)));raise SystemExit(1)
