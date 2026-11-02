"""Bind checkpoint102 code/test proofs without running another test or device.

Historical failures and source epochs remain immutable. Documentation/gallery
links intentionally carry no hashes, allowing their owner to finish the prose
without a hash-reference cycle or another native invocation.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import freeze, sha, utc, write
EVIDENCE = ROOT / 'Verification/Evidence/Review102'


def load(path):
    return json.loads(path.read_text('utf-8-sig'))


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


def changes(before, after):
    return dict(added=sorted(after.keys() - before.keys()), removed=sorted(before.keys() - after.keys()),
                changed=sorted(name for name in before.keys() & after.keys() if before[name] != after[name]))


def unchanged(before, after, predicate):
    names = [name for name in before if predicate(name)]
    return dict(files=len(names), unchanged=bool(names) and all(after.get(name) == before[name] for name in names))


def main():
    baseline_main = ROOT / 'Verification/Evidence/Review101/Native/LTSBuildDefault01/MainSources_after.json'
    final_main = EVIDENCE / 'Native/Flow01_Native/MainSources_after.json'
    baseline_backend = ROOT / 'Verification/Evidence/Review100/Backend/Full02/Service_Tests.json'
    final_backend = EVIDENCE / 'Backend/Full02/Service_Tests.json'
    main_before, main_after = load(baseline_main)['files'], load(final_main)['files']
    backend_before, backend_after = load(baseline_backend)['sourceSHA256'], load(final_backend)['sourceSHA256']
    main_match = freeze()['files'] == main_after
    backend_match = all(sha(ROOT / name) == digest for name, digest in backend_after.items())
    if not main_match or not backend_match:
        raise ValueError('FinalSealedSourceEpochRequired102')
    delta = dict(schemaVersion=1, status='VERIFIED_FINAL_VK102_SOURCE_DELTA', utc=utc(),
        baselineMain=bind(baseline_main), finalMain=bind(final_main),
        baselineBackend=bind(baseline_backend), finalBackend=bind(final_backend),
        mainInputCount=len(main_after), backendInputCount=len(backend_after),
        main=changes(main_before, main_after), backend=changes(backend_before, backend_after),
        currentMainExactlyMatchesSealedFinal=main_match, currentBackendExactlyMatchesPassingFullSuite=backend_match,
        engineSettingsPackages=unchanged(main_before, main_after, lambda name: '/ProjectSettings/' in name or '/Packages/' in name),
        existingMetaBytes=unchanged(main_before, main_after, lambda name: name.endswith('.meta')),
        approvedNonCodeAssets=unchanged(main_before, main_after, lambda name: '/Assets/' in name and not name.endswith(('.cs', '.java', '.meta'))),
        gameplayM46M48=unchanged(main_before, main_after, lambda name: '/M46/' in name or '/M48/' in name),
        existingShopCatalog=unchanged(main_before, main_after, lambda name: name.endswith('/App/Shop/Data/ShopCatalog.json')),
        existingCommerceWalletConfig=unchanged(backend_before, backend_after,
            lambda name: name.startswith('Backend/config/') or name.startswith('Backend/hotr_backend/commerce') or name.startswith('Backend/hotr_backend/wallet')),
        sourceScope='Main baseline is the restored working101 seal, not dirty GitHEAD or rejected pre-draw source. Backend baseline is accepted100 full suite;101 changed no backend runtime. Auth/API/schema and focused tests are the intended delta; prior commerce/wallet work remains preserved.')
    java = ROOT / 'Unity/Assets/HeartOfTheRain/App/Launch/Plugins/Android/HeartRainLaunch99.androidlib/src/main/java/com/heartoftherain/launch99/LaunchCurtain99.java'
    delta['workingStartupJava'] = bind(java)
    delta['workingStartupJavaUnchanged'] = sha(java) == '1de78774460c27255e52ce87efd24d05c8398ad6d23353564d9d2ff9131c8222'
    for name in ('engineSettingsPackages', 'existingMetaBytes', 'approvedNonCodeAssets', 'gameplayM46M48', 'existingShopCatalog', 'existingCommerceWalletConfig'):
        if not delta[name]['unchanged']:
            raise ValueError('UnrelatedSourceBoundaryChanged102')
    if not delta['workingStartupJavaUnchanged']:
        raise ValueError('WorkingStartupRestorationMustRemain102')
    write(EVIDENCE / 'SourceDelta102.json', delta)

    native = []
    warnings = []
    for tag in ('VkMain02', 'IdentityMain01', 'ProviderMain01', 'AccountMain01', 'Flow01_Native'):
        invocation_path = EVIDENCE / 'Native' / tag / 'Invocation.json'
        invocation = load(invocation_path)
        report_path = invocation_path.parent / invocation['nativeReport']
        report = load(report_path)
        if invocation['status'] != 'PASS_NATIVE102_INVOCATION' or not invocation['mainInputsUnchanged']:
            raise ValueError('AcceptedNativeInvocationRequired102')
        native.append(dict(tag=tag, invocation=bind(invocation_path), nativeReport=bind(report_path),
            status=report['status'], checks=report.get('checks', 0), cases=report.get('cases', 0),
            layouts=report.get('layouts', 0), scope=report.get('scope', ''),
            mainSourcesBefore=bind(invocation_path.parent / 'MainSources_before.json'),
            mainSourcesAfter=bind(invocation_path.parent / 'MainSources_after.json')))
        log = ROOT / next(item['path'] for item in invocation['privateLogs'] if item['path'].endswith('/Unity.log'))
        text = log.read_text('utf-8-sig', errors='replace')
        warnings.append(dict(tag=tag, invocation=bind(invocation_path), privateLog=bind(log),
            csharpWarningLines=len(re.findall(r'\bwarning CS[0-9]+\b', text)),
            csharpErrorLines=len(re.findall(r'\berror CS[0-9]+\b', text))))
    backend_invocation = EVIDENCE / 'Backend/Full02/Invocation.json'
    backend = load(backend_invocation)
    connected_path = EVIDENCE / 'Connected/Flow01/Report.json'
    connected = load(connected_path)
    if backend['status'] != 'PASS_FULL_BACKEND102_WITH_APPROVED_WORKER' or connected['status'] != 'PASS_CONNECTED_VK_SIGNIN102_HTTP' or not connected['ownedListenerClosed']:
        raise ValueError('AcceptedBackendAndConnectedProofRequired102')
    backend_log = ROOT / backend['privateConsole']['path']
    backend_text = backend_log.read_text('utf-8-sig', errors='replace')
    warning_report = dict(schemaVersion=1, status='MEASURED_SELECTED_NATIVE_COMPILER_WARNINGS102', utc=utc(),
        selectedCSharpWarningLines=sum(item['csharpWarningLines'] for item in warnings),
        selectedCSharpErrorLines=sum(item['csharpErrorLines'] for item in warnings), logs=warnings,
        buildInvoked=False, buildReportCountsAvailable=False,
        prior101Il2cppCompileCostNotices=3, priorNoticesRerun=False,
        backendExternalStarletteDeprecationObserved='StarletteDeprecationWarning' in backend_text,
        backendPrivateConsole=bind(backend_log),
        scope='Selected actual Unity2022 Editor compilation only. No Android/IL2CPP build or SDK upgrade. Prior101 IL2CPP notices and the external Starlette/httpx TestClient deprecation are not silently reported fixed.')
    write(EVIDENCE / 'CompilerWarnings102.json', warning_report)
    apk = ROOT / 'Unity/Builds/Review101/HeartOfTheRain_Review101_Android_Test.apk'
    summary = dict(schemaVersion=1, status='REVIEWED_WITH_OPEN_ACCEPTANCE_GATES', utc=utc(),
        codeImplementationVerified=True, fullyVetted=False, taskComplete=False, productionApproved=False,
        mainEngine='2022.3.62f3', enginePromoted=False, sdkAddedOrUpgraded=False,
        native= native, sourceDelta=bind(EVIDENCE / 'SourceDelta102.json'),
        backend=dict(invocation=bind(backend_invocation), serviceReport=bind(final_backend),
            executedTests=backend['executedTests'], failures=backend['failures'], errors=backend['errors'],
            skipped=backend['skips'], actualApprovedWorker=backend['actualPinnedWorkerIntegration'], approvedWorkerFiles=176),
        connectedHttp=dict(report=bind(connected_path), nativeChecks=native[-1]['checks'],
            sourceWalletCoins=connected['databaseAudit']['wallets']['source']['coins'],
            targetWalletCoins=connected['databaseAudit']['wallets']['target']['coins'],
            actualVkProvider=False, syntheticProviderTransport=True, browserOpened=False,
            ordinaryProfileFilesPreserved=True, ownedListenerClosed=True),
        selectedNativeWarningAudit=bind(EVIDENCE / 'CompilerWarnings102.json'),
        reviewedImages=bind(EVIDENCE / 'Reviewed/Selection102.json'),
        reviewedViewport=dict(width=720, height=1600, physicalDevice=False, tabletCoverage=False,
            states=45, cases=51, sourceTag='VkMain02', syntheticProviderAndClock=True),
        retainedHistory=[
            dict(scope='Earlier718-check native pass before the root-found footer ambiguity was corrected; not final visual acceptance.', invocation=bind(EVIDENCE / 'Native/VkMain01/Invocation.json')),
            dict(scope='Actual Full01 failed new-module import and wrapper final-write error. Earlier proofs are retained; no newVK pass inferred.', completion=bind(EVIDENCE / 'Backend/Full01/CompletionFailure.json'))],
        android=dict(apkBuiltThisCheckpoint=False, apkInstalledThisCheckpoint=False,
            adbOrDeviceActionThisCheckpoint=False, physicalDeviceInspectedThisCheckpoint=False,
            previous101Artifact=bind(apk), previousDeviceVerification='Checkpoint101 historical only; this task does not freshly inspect the phone or certify new VK code on Android.'),
        remainingGates=[
            'Real VK ID client registration and exact allowed HTTPS callback configuration.',
            'Hosted HTTPS managed backend, operator privacy/logging/secret configuration and app origin selection.',
            'Real VK consent/cancel/browser return and configured signed Android build/device acceptance.',
            'Ordinary local saves remain separate; there is no silent local wallet/progression import or account merge.',
            'No native VK SDK is added; production browser/provider compatibility and live credentials remain unverified.',
            'Prior brief startup flash, broad performance, all-device and provider/payment/production gates remain open.'],
        reviewPath='Codex_Handoff/Documentation/102_VK_REGISTRATION_AND_SIGNIN_REVIEW.md',
        galleryPath='Verification/Evidence/Review102/Comparison.html',
        scope='Code and individually bound actual Editor/backend/controlled-HTTP proofs. Provider HTTP is synthetic, encrypted Editor keys are CNG, not Android Keystore. No live VK/cloud/device/production acceptance, app build/install or extra reward.')
    write(EVIDENCE / 'Summary.json', summary)
    print(json.dumps(dict(status=summary['status'], nativePasses=len(native), backendTests=backend['executedTests'],
        httpChecks=native[-1]['checks'], changedMain=len(delta['main']['changed']), addedMain=len(delta['main']['added']),
        changedBackend=len(delta['backend']['changed']), addedBackend=len(delta['backend']['added']),
        csharpWarnings=warning_report['selectedCSharpWarningLines'], csharpErrors=warning_report['selectedCSharpErrorLines'])))


if __name__ == '__main__':
    main()
