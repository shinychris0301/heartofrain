"""Bind completed107/108 native and SDK proofs; no new tests/build/device action."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
from run_ads85_native import sha,utc,write

OUT=ROOT/'Verification/Evidence/Review107'
TAGS=('AdvertisingMain02','AdvertisingMain03','Nav108Main01','BuildPolicyMain01','BuildPolicyMain02',
      'AdsParserMain01','AdsJournalMain01','AdsFlowMain01','AdsUiMain01','GeneralMain01',
      'Configuration104Main01','After108Main01','PackagingLts01','AndroidBuildLts01')
FAILED={'AdvertisingMain02','BuildPolicyMain01'}
def load(p):return json.loads(p.read_text('utf-8-sig'))
def bind(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
def delta(a,b):return dict(added=sorted(b.keys()-a.keys()),removed=sorted(a.keys()-b.keys()),changed=sorted(k for k in a.keys()&b.keys() if a[k]!=b[k]))
def main():
    final=load(OUT/'Native/AndroidBuildLts01/MainSources_after.json')['files']
    rows=[];logs=[];records={};epochs=[]
    for tag in TAGS:
        folder=OUT/'Native'/tag;inv=load(folder/'Invocation.json');report_path=folder/inv['nativeReport'];report=load(report_path) if report_path.exists() else None
        before=load(folder/'MainSources_before.json')['files'];after=load(folder/'MainSources_after.json')['files']
        assert before==after and inv['mainInputsUnchanged'] and inv['originalPrivateAssetAndSourceBytesPreserved'] and inv['originalPrivateMetaGuidsPreserved'] and not inv['unityPidsAfter']
        assert inv['ownedChildClosure']['observed'] and inv['ownedChildClosure']['allObservedHandlesSignaled']
        assert inv['status']==('FAIL_NATIVE107_INVOCATION' if tag in FAILED else 'PASS_NATIVE107_INVOCATION')
        if report is not None:assert sha(report_path)==inv['nativeReportSHA256']
        checks=report.get('checks',report.get('passed',0)) if report else 0
        if not isinstance(checks,int):checks=report.get('passed',0)
        row=dict(tag=tag,invocation=bind(folder/'Invocation.json'),nativeReport=bind(report_path) if report else None,
            status=inv['status'],nativeStatus=inv['nativeStatus'],checks=checks,cases=report.get('cases',0) if report else 0,
            engine=inv['actualEngine'],scope=report.get('scope','Compile failed before suite entry') if report else 'Compile failed before suite entry',
            elapsedSeconds=inv['elapsedSeconds'],mainInputsUnchanged=True,originalProjectAssetBytesAndGuidsPreserved=True,
            ownedChildClosure=inv['ownedChildClosure'],mainSourcesBefore=bind(folder/'MainSources_before.json'),mainSourcesAfter=bind(folder/'MainSources_after.json'))
        rows.append(row);records[tag]=(inv,report,folder)
        epochs.append(dict(tag=tag,fullMainEpochMatchesFinal=after==final,deltaToFinal=delta(after,final),
            sources=bind(folder/'MainSources_after.json'),originalProofUnmodified=True))
        log=ROOT/next(p['path'] for p in inv['privateLogs'] if p['path'].endswith('/Unity.log'));text=log.read_text('utf-8-sig',errors='replace')
        warning_lines=re.findall(r'(?m)^.*\bwarning CS[0-9]+\b.*$',text);error_lines=re.findall(r'(?m)^.*\berror CS[0-9]+\b.*$',text)
        codes=sorted(set(re.findall(r'\bwarning (CS[0-9]+)\b',text)));error_codes=sorted(set(re.findall(r'\berror (CS[0-9]+)\b',text)))
        unique_warnings=sorted(set(v.strip().replace('\\','/') for v in warning_lines))
        logs.append(dict(tag=tag,privateLog=bind(log),csharpWarningLines=len(warning_lines),csharpWarningCodes=codes,
            uniqueCSharpWarningMessages=unique_warnings,csharpErrorLines=len(error_lines),csharpErrorCodes=error_codes,
            buildResultErrors=report.get('errors') if report and report.get('actualBuild') else None,
            buildResultWarnings=report.get('warnings') if report and report.get('actualBuild') else None,
            duplicateInternetManifestNotice='INTERNET but it is already declared by the user' in text,
            clangUnusedCommandLineNotices=text.count("'-x c++' after last input file has no effect"),
            il2cppLargeMethodCompileCostNotices=text.count("Method was given it's own cpp file because it is large and costly to compile"),
            licensingRefreshDiagnostic='Access token is unavailable; failed to update' in text,
            shutdownAllocatorDiagnostic='m_LastAlloc not NULL' in text))
    verification=dict(schemaVersion=1,status='PASS_TARGETED_NATIVE107_108_WITH_RETAINED_EPOCHS',utc=utc(),
        actualEditorInvocations=len(rows),passingInvocations=len(rows)-len(FAILED),retainedFailedNativeInvocations=len(FAILED),
        native=[r for r in rows if r['tag'] not in FAILED],mainEngine='2022.3.62f3',isolatedBuildEngine='6000.3.27f1',
        obsoleteNavigation106SuiteRerun=False,matchedCaptureFixture='Unity/Assets/HeartOfTheRain/Verification/Editor/BaselineCapture106.cs',
        actualSdkAdRequests=False,appInstalledOrLaunched=False,realProviderVerified=False,productionApproved=False,
        scope='Actual Editor assertions and actual isolated Android compilation only. Legacy parser/flow include explicit scripted API/provider data; no claim that fake callbacks are provider proof. General count535 is nativeReport.passed; its Invocation.checks preserves the original check array.')
    write(OUT/'NativeVerification107.json',verification)
    final_main_logs=[v for v in logs if v['tag'] not in FAILED and v['tag'] not in ('PackagingLts01','AndroidBuildLts01')]
    warnings=dict(schemaVersion=1,status='MEASURED_NATIVE_AND_SDK_WARNINGS107',utc=utc(),logs=logs,
        successfulMainCSharpWarningLines=sum(v['csharpWarningLines'] for v in final_main_logs),
        successfulMainCSharpErrorLines=sum(v['csharpErrorLines'] for v in final_main_logs),
        retainedCompileFailure=dict(tag='AdvertisingMain02',uniqueCode='CS0117',reason='Unity6-only Gradle getter was referenced by a main2022 Editor compilation; now preprocessor guarded.'),
        actualAndroidBuild=dict(report=bind(OUT/'Native/AndroidBuildLts01/AndroidBuild107.json'),errors=0,warnings=4,
            classification=[dict(count=3,type='Vendor CS0414',reason='Three unmodified Yandex Dummy loader OnAdFailedToLoad fields are assigned but not read. SDK fallback implementation warnings, not rewarded-provider failure.'),
                dict(count=1,type='Redundant INTERNET manifest declaration',reason='Unity also adds INTERNET already declared by this private SDK manifest. Final merged permission remains correct; no runtime failure.')],
            broadWarningSuppressionApplied=False,vendorBytesEdited=False,
            remainingWarningsResolved=False),
        scope='Recorded compiler lines are separate from unique warnings and actual BuildReport counts. SDK warnings remain documented, not erased. Stock clang option notices, existing IL2CPP large-method compilation notices, Editor licensing refresh and shutdown allocator text are separate from gameplay/performance acceptance.')
    write(OUT/'CompilerWarnings107.json',warnings)

    build=OUT/'Native/AndroidBuildLts01/AndroidBuild107.json';native=load(build);audit_path=build.parent/'Static/Audit02/StaticApk107.json';audit=load(audit_path)
    assert audit['status']=='PASS_STATIC_ADS107_APK' and len(audit['checks'])==19 and audit['apkSHA256']==native['apkSHA256']
    assert audit['jniTarget']['public'] and audit['jniTarget']['static'] and audit['jniTarget']['descriptor']=='(Z)V'
    receipt=ROOT/'.verification-cache/Review107/Candidates/SDK01/Preparation.json';prepared=load(receipt);project=Path(prepared['project'])
    copied_locks=[];inputs=OUT/'SDKInputs';inputs.mkdir(exist_ok=False)
    for item in audit['dependencyLocks']:
        source=project/item['path'];assert sha(source)==item['sha256'];module=Path(item['path']).parent.name;target=inputs/(module+'.gradle.lockfile');shutil.copyfile(source,target);assert sha(target)==sha(source);copied_locks.append(dict(source=bind(source),retainedCopy=bind(target)))
    sdk=dict(schemaVersion=1,status='PASS_ISOLATED_SDK107_PACKAGING_BUILD_AND_STATIC_AUDIT',utc=utc(),
        vendorVersion='8.6.0',vendorArchiveSHA256=prepared['vendorSHA256'],preparation=bind(receipt),preparationStarted=bind(receipt.parent/'PreparationStarted.json'),
        preparationTool=bind(ROOT/'Verification/Tools/Review107/prepare_ads107.py'),selectedInitialInputs=bind(ROOT/'Verification/Tools/Review107/SelectedInputs107.json'),
        candidateCount=1,candidateEngine='6000.3.27f1',mainPromoted=False,mainVendorSdkImported=False,
        copiedPreparationInputs=len(prepared['copiedSHA256']),retainedMigratedMetaGuids=prepared['retainedMigratedMetaGuids'],
        configuredPackaging=dict(report=bind(OUT/'Native/PackagingLts01/Packaging107.json'),checks=12,syntheticMetadataOnly=True,
            actualAssetDatabaseAndRuntimeResourcesReaders=True,adsEnabledReaderTested=True,managedReaderTested=True,
            successAndThrowCleanupVerified=True,bootstrapCalled=False,hostnameResolvedOrContacted=False,buildPipelineInvoked=False),
        build=bind(build),actualAndroidBuild=True,development=True,scriptDebugging=False,adsEnabledInDeliveredApk=False,
        managedPayloadIncludedInDeliveredApk=False,apiMinimum=26,apiTarget=36,architecture='arm64-v8a',scriptingBackend='IL2CPP',
        staticAudit=bind(audit_path),staticChecks=19,jniTarget=audit['jniTarget'],sdkClassPolicy=audit['sdkClassPolicy'],retainedDependencyLocks=copied_locks,
        priorRejectedAudit=bind(build.parent/'StaticApk107.json'),
        actualSdkInitializationOrAdRequest=False,realAdShown=False,actualRewardGranted=False,actualHostedBackend=False,
        appMetricaCaveat='AppMetrica remains a required transitive SDK dependency. No claim of zero processing, runtime network/privacy compliance or provider-authenticated completion; Yandex does not provide server-side reward verification.',
        productionApproved=False,scope='One owned fresh SDK candidate; actual LTS configuration delivery and development APK, plus independent read-only bytecode/manifest/lock/ELF checks. No install, device or live publisher acceptance.')
    write(OUT/'SDKVerification107.json',sdk)

    prelaunch=OUT/'Native/AdvertisingMain01/PrelaunchFailure107.json'
    failure_rows=[dict(classification='PRELAUNCH_METADATA_REJECTED',proof=bind(prelaunch),nativeEditorStarted=False,
        reason='Two newly authored107 metadata GUIDs had33characters; strict preflight rejected them before any Editor launch. Both corrected to unique32hex values; original metas/runner preserved.'),
        dict(classification='NATIVE_EDITOR_COMPILE_FAILURE',proof=bind(OUT/'Native/AdvertisingMain02/Invocation.json'),
            reason='CS0117 Unity6-only Gradle getter in main2022 compile. Helper-only conditional compilation fixed the actual engine boundary; no SDK/toolchain gate relaxed.',finalPass=bind(OUT/'Native/AdvertisingMain03/Invocation.json')),
        dict(classification='POLICY_FIXTURE_PATH_ERROR',proof=bind(OUT/'Native/BuildPolicyMain01/BuildPolicy107.json'),
            reason='The negative control appended child.txt to a filename ending.json. Corrected to the extensionless Resources key child path; actual guard unchanged.',finalPass=bind(OUT/'Native/BuildPolicyMain02/Invocation.json')),
        dict(classification='SDK_FREE_AUDITOR_POLICY_FALSE_POSITIVE',proof=bind(build.parent/'StaticApk107.json'),
            reason='Fourteen SDK checks passed, then the historical94 SDK-free ZIP policy rejected the intentionally bundledYandex/AppMetrica DEX. Audit-only replacement uses independent ELF/manifest/ZIP plus explicit expected/forbidden SDKclass definitions. Historical94tool/APK/runtime unchanged; no rebuild.',finalPass=bind(audit_path))]
    failures=dict(schemaVersion=1,status='RETAINED_NATIVE_AND_AUDIT_FAILURES107',utc=utc(),failures=failure_rows,epochs=epochs,
        retainedSourceFiles=[bind(p) for p in sorted((OUT/'RetainedSources').iterdir()) if p.is_file()],
        originalReportsOverwritten=False,
        laterPackagingAssertion=dict(oldHelper=bind(OUT/'RetainedSources/AdvertisingBuild107_before_runtime_ads_reader_assertion.cs'),
            scope='Test-only positive runtime ads Resources/TryRead assertion added after Flow closed and before fresh SDK copy. Earlier config/nav/policy/legacy passes retain their actual epochs; no unrelated runtime/guard change or rerun is inferred.'),
        scope='One prelaunch rejection, two failed actual Editor attempts and one failed read-only audit remain separate. Final passing results do not relabel initial failures.')
    write(OUT/'FailuresAndEpochs107.json',failures)

    delivered=ROOT/'Unity/Builds/Review107/HeartOfTheRain_107_108_Android_Test.apk';source=Path(native['apk'])
    assert sha(source)==sha(delivered)==native['apkSHA256'] and delivered.stat().st_size==native['bytes']==308031545
    delivery=dict(schemaVersion=1,status='DELIVERED_EXACT_INTERNAL_ANDROID107_108',utc=utc(),source=bind(source),delivered=bind(delivered),
        nativeBuild=bind(build),staticAudit=bind(audit_path),packageName='com.heartoftherain.ads107review',
        development=True,scriptDebugging=False,sdkIncluded=True,advertisingEnabled=False,managedBackendPayloadIncluded=False,
        apkInstalled=False,appLaunched=False,realAdsVerified=False,releaseSigningUsed=False,productionApproved=False,
        scope='Exact development test APK retained for review, not a RuStore release or verified live-ad/account build. Owner privacy URL/backend configuration and live/provider/device gates remain open.')
    write(OUT/'APKDelivery107.json',delivery)
    diagnostics=dict(schemaVersion=1,status='MEASURED107_PROCESS_AND_PRESERVATION_BOUNDARIES',utc=utc(),
        actualEditorInvocations=14,passingNativeInvocations=12,retainedFailedNativeInvocations=2,prelaunchRejections=1,staticAuditAttempts=2,
        allRecordedMainInputsUnchanged=True,allOriginalPrivateAssetSourceBytesAndGuidsPreserved=True,
        ownedChildClosures=[dict(tag=tag,closure=records[tag][0]['ownedChildClosure']) for tag in TAGS],
        ordinaryGuardReports=[dict(tag=tag,nativeReport=bind(records[tag][2]/records[tag][0]['nativeReport']),
            guards={k:v for k,v in records[tag][1].items() if k in ('ordinaryProfilesPreserved','serverReviewPreserved','advertisingFilePreserved','languagePreferencePreserved','profilesPreserved','projectSettingsPreserved','gameViewRestored')}) for tag in ('AdvertisingMain03','Nav108Main01','After108Main01')],
        scope='Guard booleans are reported only where actual native suites populate them. Parser default unpopulated preservation booleans are not promoted into measurements. Retained owned WindowsJob members are waited after closure; unrelated existing processes are not adopted/killed.',
        mainEngine='2022.3.62f3',mainEnginePromoted=False,mainVendorSdkImported=False,
        explicitAdbCommandInvoked=False,apkInstalled=False,physicalPhoneFreshlyTested=False,
        appOrProviderNetworkRequests=False,realPublisherOrRevenueAccepted=False,fullyVetted=False,productionApproved=False)
    write(OUT/'Diagnostics107.json',diagnostics)
    print(json.dumps(dict(status='BOUND_COMPLETED_NATIVE_SDK107_108_PROOFS',actualEditorInvocations=14,passingNative=12,
        retainedFailures=len(failure_rows),staticChecks=19,apkSHA256=native['apkSHA256'],bytes=native['bytes'],buildWarnings=4)))
if __name__=='__main__':main()
