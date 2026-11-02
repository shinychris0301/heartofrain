"""Seal immutable native/build/static evidence; physical acceptance is separate."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];E=ROOT/'Verification/Evidence/Review109'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bind(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
 tags=['ImportMain01','TeamsMain01','TeamsMain02','TeamsMain03','TeamsMain04','TeamsMain05','TeamsMain06','GeneralMain01','ScrollMain01','Configuration104Main01','Nav108Main01','BuildPolicyLts01','AndroidBuildLts01']
 records=[];warnings=[];compiler_errors=[];notices=[]
 final=read(E/'Native/AndroidBuildLts01/MainSources_after.json')['files']
 for tag in tags:
  folder=E/'Native'/tag;inv=read(folder/'Invocation.json');native=read(folder/inv['nativeReport']);manifest=read(folder/'MainSources_after.json')['files']
  changed=sorted(k for k in set(manifest)|set(final) if manifest.get(k)!=final.get(k))
  runtime_equivalent=all('/Verification/' in k for k in changed)
  records.append(dict(tag=tag,invocation=bind(folder/'Invocation.json'),native=bind(folder/inv['nativeReport']),status=inv['status'],nativeStatus=native['status'],checks=inv['checks'],cases=native.get('cases'),layouts=native.get('layouts'),elapsedSeconds=inv['elapsedSeconds'],mainInputsUnchanged=inv['mainInputsUnchanged'],assetGuidsUnchanged=inv.get('assetGuidsUnchanged'),ownedProcessesClosed=inv['ownedChildClosure']['observed'] and inv['ownedChildClosure']['allObservedHandlesSignaled'],fullMainManifestEqualsFinal=not changed,runtimeAndAssetInputsEqualFinal=runtime_equivalent,changedMainPathsSinceInvocation=changed))
  log=ROOT/'.verification-cache/Review109/RawNative'/tag/'Unity.log';text=log.read_text('utf-8-sig',errors='replace')
  matches=re.findall(r'([^\r\n]+?): (warning|error) (CS\d+): ([^\r\n]+)',text)
  cs=[dict(source=m[0],severity=m[1],code=m[2],message=m[3]) for m in matches]
  warnings.extend(dict(tag=tag,**v) for v in cs if v['severity']=='warning');compiler_errors.extend(dict(tag=tag,**v) for v in cs if v['severity']=='error')
  notices.append(dict(tag=tag,editorLicensingTokenNotice='Access token is unavailable' in text,editorShutdownAllocatorNotice='m_LastAlloc not NULL' in text,editorDebuggerListenNotice='Unable to listen on' in text,clangUnusedArgumentNotices=text.count("warning: '-x c++' after last input file has no effect"),redundantInternetManifestNotice='Unity is trying to add element uses-permission#android.permission.INTERNET' in text))
 passes=[v for v in records if v['status'].startswith('PASS_')];failed=[v for v in records if v['status'].startswith('FAIL_')]
 if len(records)!=13 or len(passes)!=8 or len(failed)!=5 or compiler_errors:raise ValueError('ExactReviewedNativeInventoryRequired109')
 ordinary=[]
 for tag in ['TeamsMain06','ScrollMain01','GeneralMain01','Configuration104Main01','Nav108Main01']:
  inv=read(E/'Native'/tag/'Invocation.json');report=read(E/'Native'/tag/inv['nativeReport']);ordinary.append(dict(tag=tag,declaredGuards={k:v for k,v in report.items() if k.endswith(('Preserved','Unchanged')) and isinstance(v,bool)},scope='Only guards explicitly declared in this original report are counted; absence is not a passed check.'))
 write(E/'NativeVerification109.json',dict(status='PASS_SCOPED_NATIVE109_WITH_RETAINED_FAILURES',baseline=bind(ROOT/'Verification/Tools/Review109/Baseline109.json'),invocations=records,actualInvocations=13,passingInvocations=8,failedInvocations=5,finalTeams=dict(checks=22456,functionalCases=36,layouts=135,scriptedExchanges=41,actualHttpRequests=0),scrollReachability=dict(checks=723,cases=20,actualHttpRequests=0),generalChecks=535,configurationChecks=149,navigationChecks=6451,ordinaryGuards=ordinary,sourceEpochNote='Main06 and General predate only the independent Scroll entry. Their called runtime/art/settings inputs match final; no rerun or uniform full-manifest claim. Earlier failed runtime/layout epochs and the69-new-meta import epoch remain distinct.',physicalAcceptance='Separate guarded physical reports; these records do not certify real online teams, devices or production.'))
 unique={(v['source'],v['code'],v['message']) for v in warnings};project=[v for v in warnings if 'YandexMobileAds' not in v['source']]
 if project or len(unique)!=3:raise ValueError('UnexpectedCompilerWarningsRequireReview109')
 write(E/'CompilerWarnings109.json',dict(status='AUDITED_SCOPED_COMPILER_WARNINGS109',csharpErrors=compiler_errors,newProjectCsharpWarnings=project,main2022CsharpWarnings=0,pinnedVendorUniqueWarnings=[dict(source=s,code=c,message=m) for s,c,m in sorted(unique)],warningLogOccurrences=len(warnings),actualBuildReport=dict(errors=0,warnings=4,binding=bind(E/'Native/AndroidBuildLts01/BuildDevelopment109.json')),classification='Three unchanged pinned Yandex Dummy-loader CS0414 warnings plus one redundant INTERNET manifest notice in BuildReport. Two clang command-line notices and Editor shutdown/licensing/debugger notices are separate; none are silently suppressed or described as whole-app warning-free.',logWarnings=warnings,environmentNotices=notices))
 build=E/'Native/AndroidBuildLts01/BuildDevelopment109.json';static=build.parent/'Static/Audit01/StaticApk109.json';audit=read(static);receipt=ROOT/'.verification-cache/Review109/Candidates/SDK01/Preparation.json';prep=read(receipt)
 write(E/'SDKVerification109.json',dict(status='PASS_OWNED_SDK109_BUILD_AND_STATIC_AUDIT',preparation=bind(receipt),copiedInputs=len(prep['copiedSHA256']),mainInputs=len(prep['mainSourceSHA256']),vendorSHA256=prep['vendorSHA256'],privateOnly107Delegation=prep['private107GuardDelegation'],policy=bind(E/'Native/BuildPolicyLts01/BuildPolicy109.json'),actualBuild=bind(build),staticAudit=bind(static),staticChecks=len(audit['checks']),delivery=bind(E/'APKDelivery109.json'),mainEngine='2022.3.62f3',isolatedEngine='6000.3.27f1',sdkVersion='Official pinned Yandex lite8.6.0 and AppMetrica8.6.0',samePhoneSigner=audit['signerCertificateSHA256'],adsEnabled=False,managedPayload=False,scriptDebugging=False,productionApproved=False,scope='One fresh owned isolated development candidate. Main107 authority and historical101/107 candidates remain unchanged. Actual Android compile/static proof does not establish load/show/impression, reward, backend/provider/privacy or production acceptance. AppMetrica remains a dependency; this is not a zero-processing claim.'))
 print(json.dumps(dict(status='SEALED_NONDEVICE109',records=len(records),passes=len(passes),retainedFailures=len(failed),files=['NativeVerification109.json','CompilerWarnings109.json','SDKVerification109.json'])))
if __name__=='__main__':main()
