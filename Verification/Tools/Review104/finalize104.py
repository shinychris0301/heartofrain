"""Bind actual104 proofs and retained failures without another test or device.

The private2022 project proves Editor resource import/selection/cleanup, never
APK inclusion or real host access. Earlier main suites keep their source epochs.
"""
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
from run_ads85_native import freeze,sha,utc,write
EVIDENCE=ROOT/'Verification/Evidence/Review104'
EDITOR='Unity/Assets/HeartOfTheRain/App/ServerGameplay/Editor/'
BUILD=EDITOR+'StagingServerBuild104.cs'
PACKAGING_TEST=EDITOR+'StagingServerPackagingVerification104.cs'


def load(path):
    return json.loads(path.read_text('utf-8-sig'))


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)


def changes(before,after):
    return dict(added=sorted(after.keys()-before.keys()),removed=sorted(before.keys()-after.keys()),
                changed=sorted(name for name in before.keys()&after.keys() if before[name]!=after[name]))


def unchanged(before,after,predicate):
    names=[name for name in before if predicate(name)]
    return dict(files=len(names),unchanged=bool(names) and all(after.get(name)==before[name] for name in names))


def main():
    baseline=ROOT/'Verification/Evidence/Review103/Native/TeamsMain02/MainSources_after.json'
    final=EVIDENCE/'Native/PackagingIsolated01/MainSources_after.json'
    before,after=load(baseline)['files'],load(final)['files']
    if freeze()['files']!=after:
        raise ValueError('FinalSealedMain104Required')
    early_path=EVIDENCE/'Native/ConfigurationMain01/MainSources_after.json'
    middle_path=EVIDENCE/'Native/TeamsMain01/MainSources_after.json'
    early,middle=load(early_path)['files'],load(middle_path)['files']
    first_delta,second_delta=changes(early,middle),changes(middle,after)
    if first_delta!=dict(added=[],removed=[],changed=sorted([BUILD,PACKAGING_TEST])) or second_delta!=dict(added=[],removed=[],changed=[PACKAGING_TEST]):
        raise ValueError('ExplicitReviewedEditorOnlyEpochDifferencesRequired104')
    for tag in ('PolicyMain02','ServerCoreMain01'):
        if load(EVIDENCE/'Native'/tag/'MainSources_after.json')['files']!=middle:
            raise ValueError('EarlierMainRegressionEpochMismatch104')
    backend_path=ROOT/'Verification/Evidence/Review103/Backend/Messaging01/Report.json'
    backend=load(backend_path)
    backend_files=backend['sourceSHA256After']
    if not all(sha(ROOT/name)==digest for name,digest in backend_files.items()):
        raise ValueError('UnchangedBackend103BoundaryRequired104')
    host_path=EVIDENCE/'Preparation/Host02/Report.json'
    host=load(host_path)
    clone_path=EVIDENCE/'Preparation/Clone01/Report.json'
    clone=load(clone_path)
    if host['status']!='PASS_PREPARATION104_CHECKS' or not host['untouchedExampleBlocked'] or clone['status']!='PASS_ONE_ISOLATED104_PREPARATION':
        raise ValueError('PassingHostAndSingleClone104Required')
    candidate=ROOT/clone['project']
    candidates=ROOT/'.verification-cache/Review104/Candidates'
    if len([p for p in candidates.iterdir() if p.is_dir()])!=1:
        raise ValueError('ExactlyOneActualCandidate104Required')
    guide=ROOT/'Release/RuStore/STAGING_BUILD_CONFIGURATION104.txt'
    example=ROOT/'Release/RuStore/staging-build.example.json'
    frozen_support={item['path']:item for item in host['sourceFilesAfter']}
    if any(bind(ROOT/name)!=row for name,row in frozen_support.items()):
        raise ValueError('HostToolsAndGuidesMustRemainFrozen104')
    delta=dict(schemaVersion=1,status='VERIFIED_FINAL_STAGING104_SOURCE_DELTA',utc=utc(),
        baselineMain=bind(baseline),finalMain=bind(final),mainInputCount=len(after),main=changes(before,after),
        currentMainExactlyMatchesSealedFinal=True,
        configurationMainEarlierEpoch=bind(early_path),earlierConfigurationToRegressionEpoch=first_delta,
        regressionMainEarlierEpoch=bind(middle_path),regressionToFinalEpoch=second_delta,
        earlierConfigurationRuntimeAndTestBytesMatchFinal=True,earlierPolicyCoreTeamsCalledCodeMatchesFinal=True,
        earlierMainSuitesRerunAfterFinalTestChange=False,
        engineSettingsPackages=unchanged(before,after,lambda name:'/ProjectSettings/' in name or '/Packages/' in name),
        existingMetaBytes=unchanged(before,after,lambda name:name.endswith('.meta')),
        approvedNonCodeAssets=unchanged(before,after,lambda name:'/Assets/' in name and not name.endswith(('.cs','.java','.meta'))),
        gameplayM46M48=unchanged(before,after,lambda name:'/M46/' in name or '/M48/' in name),
        profileEconomyAndShop=unchanged(before,after,lambda name:any(part in name for part in ('/App/Profile/','/App/Shop/','/App/ShopCheckout86/','/App/ServerAccount/','/App/NoMovesDesign/'))),
        existingRuStoreProductionGuard=unchanged(before,after,lambda name:name.endswith('/App/RuStore/Editor/RuStoreReleasePreflight.cs')),
        backend=dict(sourceFiles=len(backend_files),matchesSealed103=True,historicalProof=bind(backend_path),testsRerun104=False),
        isolatedPreparation=bind(clone_path),privateInputCount=clone['copiedInputCount'],
        independentPrivateIdentityBoundary=clone['independentBoundary'],
        privateSourceAndSettingsRestoredAfterBothInvocations=True,
        scope='Sealed103 versus final main104. Only private clone identity/settings fields differ from main; no engine promotion. Main149 and later main41/55/268 results retain their exact earlier Editor-test source epochs. Backend101 inputs match103; no backend rerun is claimed.')
    for key in ('engineSettingsPackages','existingMetaBytes','approvedNonCodeAssets','gameplayM46M48','profileEconomyAndShop','existingRuStoreProductionGuard'):
        if not delta[key]['unchanged']:
            raise ValueError('UnrelatedBoundaryChanged104:'+key)
    write(EVIDENCE/'SourceDelta104.json',delta)

    failure=dict(schemaVersion=1,status='RETAINED_FAILURES_AND_SOURCE_EPOCHS104',utc=utc(),
        policyFirst=dict(invocation=bind(EVIDENCE/'Native/PolicyMain01/Invocation.json'),
            report=bind(EVIDENCE/'Native/PolicyMain01/StagingPolicy104.json'),checksAttempted=18,
            outcome='Actual native failure: raw mixed slash/case paths misclassified owned files as foreign during nominal cleanup.',
            correction='Normalize all stored/compared paths with Full and Windows-aware equality; preserve foreign-byte guards.',
            successor=bind(EVIDENCE/'Native/PolicyMain02/Invocation.json'),originalProofsUnmodified=True),
        hostFirst=dict(report=bind(EVIDENCE/'Preparation/Host01/Report.json'),executedTests=6,passed=5,errors=1,
            outcome='Recovery test fixture mkdir lacked synthetic parent directories; no preparer/runtime defect inferred.',
            correction='Test-only mkdir(parents=True); ownership/foreign preservation assertions retained.',
            successor=bind(host_path),untouchedExampleWasAlreadyBlocked=True,originalProofsUnmodified=True),
        epochs=dict(configuration149=bind(early_path),mainPolicy41Core55Teams268=bind(middle_path),finalIsolated=bind(final),
            firstDifference=first_delta,secondDifference=second_delta,noHistoricalRerunClaim=True))
    historical_fixture=ROOT/'.verification-cache/Review104/LeaseCases/c672552f080e49bba1542c8ac8f6356e/success'
    if not historical_fixture.is_dir():
        raise ValueError('RetainedInitialLeaseFixtureRequired104')
    failure['retainedInitialPrivateLeaseFiles']=[bind(p) for p in sorted(historical_fixture.rglob('*')) if p.is_file()]
    write(EVIDENCE/'FailuresAndEpochs104.json',failure)

    native=[]
    warnings=[]
    final_tags=('ConfigurationMain01','PolicyMain02','ServerCoreMain01','TeamsMain01','ConfigurationIsolated01','PackagingIsolated01')
    for tag in ('PolicyMain01',)+final_tags:
        invocation_path=EVIDENCE/'Native'/tag/'Invocation.json'
        invocation=load(invocation_path)
        report_path=invocation_path.parent/invocation['nativeReport']
        report=load(report_path)
        if tag!='PolicyMain01':
            if invocation['status']!='PASS_NATIVE104_INVOCATION' or not invocation['mainInputsUnchanged'] or not invocation['projectInputsUnchanged']:
                raise ValueError('PassingSourceBoundNative104Required')
            native.append(dict(tag=tag,invocation=bind(invocation_path),nativeReport=bind(report_path),
                status=report['status'],checks=report['checks'],cases=report.get('cases',0),layouts=report.get('layouts',0),
                projectScope=invocation['projectScope'],finalMainSourceEpoch=tag in ('ConfigurationIsolated01','PackagingIsolated01'),
                runtimeMatchesFinal=True,scope=report['scope'],mainSourcesBefore=bind(invocation_path.parent/'MainSources_before.json'),
                mainSourcesAfter=bind(invocation_path.parent/'MainSources_after.json')))
        log=ROOT/next(row['path'] for row in invocation['privateLogs'] if row['path'].endswith('/Unity.log'))
        text=log.read_text('utf-8-sig',errors='replace')
        warnings.append(dict(tag=tag,invocation=bind(invocation_path),privateLog=bind(log),
            csharpWarningLines=len(re.findall(r'\bwarning CS[0-9]+\b',text)),
            csharpErrorLines=len(re.findall(r'\berror CS[0-9]+\b',text)),
            editorShutdownStackAllocatorDiagnosticObserved='m_LastAlloc not NULL' in text))
    warning_report=dict(schemaVersion=1,status='MEASURED_SELECTED_EDITOR_COMPILER_WARNINGS104',utc=utc(),
        selectedCSharpWarningLines=sum(row['csharpWarningLines'] for row in warnings),
        selectedCSharpErrorLines=sum(row['csharpErrorLines'] for row in warnings),logs=warnings,
        buildInvoked=False,buildReportCountsAvailable=False,prior101Il2cppCompileCostNotices=3,priorNoticesRerun=False,
        backendExternalStarletteDeprecationHistorical103=True,backendTestsRerun104=False,
        scope='Seven actual Unity2022 Editor logs including the retained failed policy run and one fresh private project import. Counts apply to C# diagnostics; retained Editor shutdown allocator text and historical IL2CPP/Starlette notices are not silently declared fixed. No APK/IL2CPP build occurred.')
    write(EVIDENCE/'CompilerWarnings104.json',warning_report)

    main_config=load(EVIDENCE/'Native/ConfigurationMain01/Native/ServerConfiguration104.json')
    isolated_config=load(EVIDENCE/'Native/ConfigurationIsolated01/Native/ServerConfiguration104_Isolated.json')
    packaging=load(EVIDENCE/'Native/PackagingIsolated01/StagingPackaging104.json')
    expected_absent=[Path('Assets/HeartOfTheRain/Resources/HOTR_Server'),Path('Assets/HeartOfTheRain/Resources/HOTR_Server.meta'),
                     Path('.hotr-staging104-lease.json')]
    main_and_candidate_absent=all(not (project/path).exists() for project in (ROOT/'Unity',candidate) for path in expected_absent)
    if not main_and_candidate_absent or not all(packaging[key] for key in ('successCleanup','exceptionCleanup','settingsRestored')):
        raise ValueError('FinalGeneratedResourceAbsenceAndCleanupRequired104')
    prior=load(ROOT/'Verification/Evidence/Review103/Summary.json')
    summary=dict(schemaVersion=1,status='REVIEWED_STAGING_CONFIGURATION_WITH_OPEN_ACCEPTANCE_GATES',utc=utc(),
        targetedImplementationAndEditorChecksPassed=True,fullyVetted=False,taskComplete=False,productionApproved=False,
        mainEngine='2022.3.62f3',enginePromoted=False,sdkAddedOrUpgraded=False,
        native=native,sourceDelta=bind(EVIDENCE/'SourceDelta104.json'),compilerWarnings=bind(EVIDENCE/'CompilerWarnings104.json'),
        retainedFailuresAndEpochs=bind(EVIDENCE/'FailuresAndEpochs104.json'),
        preparation=dict(hostReport=bind(host_path),executedHostTests=6,untouchedExampleBlocked=True,
            missingOriginCode='MISSING_OR_PLACEHOLDER_STAGING_ORIGIN',example=bind(example),guide=bind(guide),
            cloneReport=bind(clone_path),actualCandidateCount=1,privateEngine='2022.3.62f3',
            separateCompanyAndProduct='HeartRainStaging104',separatePackage='com.heartoftherain.stagingreview',
            configuredBackendAssigned=False,fixtureOriginNeverContacted=True),
        deliveredResource=dict(actualEditorAssetDatabaseImport=True,actualResourcesLoad=True,actualRuntimeTryRead=True,
            successCleanup=True,throwingDelegateCleanup=True,privateSettingsRestored=True,
            mainAndActualCandidateGeneratedResourcesAbsent=main_and_candidate_absent,
            diskForeignFixturesIntentionallyRetainedPrivate=True,buildPipelineInvoked=False,apkInclusionProven=False,
            providerOrBackendRequestPerformed=False,productionGuardBypassed=False),
        isolation=dict(mainProfilesPreserved=main_config['profilesPreserved'],mainServerReviewPreserved=main_config['serverReviewPreserved'],
            mainLanguageAndOverridePreserved=main_config['languagePreferencePreserved'] and main_config['externalOverridePreserved'],
            privateProfilesPreserved=isolated_config['profilesPreserved'],privateServerReviewPreserved=isolated_config['serverReviewPreserved'],
            privateLanguageAndOverridePreserved=isolated_config['languagePreferencePreserved'] and isolated_config['externalOverridePreserved'],
            actualProfileHostComponentVerified=isolated_config['componentCaseVerified'],
            componentUsedInvalidMetadataOnly=True,validGatewayBootstrapRun=False,localWalletImported=False),
        backend=dict(sourceFiles=len(backend_files),unchangedFrom103=True,testsRerun104=False,workerRun104=False,liveServiceUsed=False),
        android=dict(apkBuiltThisCheckpoint=False,apkInstalledThisCheckpoint=False,adbOrDeviceActionThisCheckpoint=False,
            physicalDeviceInspectedThisCheckpoint=False,previous101Artifact=prior['android']['previous101Artifact'],
            previousDeviceVerification='Checkpoint101 historical only.104 does not freshly inspect the phone or certify packaged staging delivery on Android.'),
        remainingGates=[
            'An assigned HTTPS staging backend, actual nonsecret origin/config and service-side identity/social activation are still required.',
            'A separately authorized Android build must prove actual APK resource inclusion, configured network/TLS/connectivity and device identity behavior.',
            'Live VK/client callback, payments/ads, hosting, signing, moderation and production acceptance remain open.',
            'The staging-only builder does not remove the existing nondevelopment/RuStore production guard.',
            'Prior startup-flash, broader gameplay performance, all-device and full release gates remain open.'],
        reviewPath='Codex_Handoff/Documentation/104_STAGING_BUILD_CONFIGURATION_REVIEW.txt',
        galleryPath='Verification/Evidence/Review104/Comparison.html',
        scope='Main/private Unity2022 parser, selected-invalid isolation, actual Editor resource adapter/import/cleanup and source-bound Python preparation checks. The synthetic host is never contacted and is not assigned/owned. No new APK, device, real backend/provider or production acceptance.')
    write(EVIDENCE/'Summary.json',summary)
    print(json.dumps(dict(status=summary['status'],nativeChecks=[row['checks'] for row in native],hostTests=6,
        changedMain=len(delta['main']['changed']),addedMain=len(delta['main']['added']),unchangedBackend=len(backend_files),
        csharpWarnings=warning_report['selectedCSharpWarningLines'],csharpErrors=warning_report['selectedCSharpErrorLines'],actualClones=1)))


if __name__=='__main__':
    main()
