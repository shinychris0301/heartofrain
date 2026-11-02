"""Bind the scoped Teams103 native proofs without another test or device action.

Main01 assertions passed but its stale-canvas captures were visually rejected.
Only the new test fixture changed before Main02. Earlier regression invocations
retain their actual source epochs; their runtime bytes match final Main02.
"""
import json
from pathlib import Path
import re
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import freeze, sha, utc, write

EVIDENCE = ROOT / 'Verification/Evidence/Review103'
TEST = 'Unity/Assets/HeartOfTheRain/Verification/Editor/TeamsDiscovery103Verification.cs'


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
    baseline = ROOT / 'Verification/Evidence/Review102/Native/Flow01_Native/MainSources_after.json'
    final = EVIDENCE / 'Native/TeamsMain02/MainSources_after.json'
    before, after = load(baseline)['files'], load(final)['files']
    if freeze()['files'] != after:
        raise ValueError('FinalSealedMain103Required')
    epoch = load(EVIDENCE / 'Native/RegionalMain01/MainSources_after.json')['files']
    general_epoch = load(EVIDENCE / 'Native/GeneralMain01/MainSources_after.json')['files']
    epoch_delta = changes(epoch, after)
    if general_epoch != epoch or epoch_delta != dict(added=[], removed=[], changed=[TEST]):
        raise ValueError('OnlyCaptureTestChangedBetweenRegressionEpochs103')
    backend_path = EVIDENCE / 'Backend/Messaging01/Report.json'
    backend = load(backend_path)
    backend_sources = backend['sourceSHA256After']
    if (backend['status'] != 'PASS_BACKEND_MESSAGING103' or backend['executedTests'] != 18
            or not backend['sourceMatchesSealed102Before'] or not backend['sourceInputsUnchanged']
            or not all(sha(ROOT / name) == digest for name, digest in backend_sources.items())
            or sha(ROOT / backend['guide']['path']) != backend['guide']['sha256']):
        raise ValueError('UnchangedPassingBackend103Required')
    delta = dict(schemaVersion=1, status='VERIFIED_FINAL_TEAMS103_SOURCE_DELTA', utc=utc(),
        baselineMain=bind(baseline), finalMain=bind(final), mainInputCount=len(after), main=changes(before, after),
        currentMainExactlyMatchesSealedFinal=True,
        earlierRegionalAndGeneralEpoch=bind(EVIDENCE / 'Native/RegionalMain01/MainSources_after.json'),
        earlierRegressionEpochToFinal=epoch_delta, onlyTestCaptureFixtureChangedAfterRegressions=True,
        regressionRuntimeBytesMatchFinal=True,
        backendProof=bind(backend_path), backendInputCount=len(backend_sources),
        currentBackendMatchesUnchangedPassingMessagingInputs=True,
        backendFullSuiteRerun=False, actualReplayWorkerRun=False,
        engineSettingsPackages=unchanged(before, after, lambda name: '/ProjectSettings/' in name or '/Packages/' in name),
        existingMetaBytes=unchanged(before, after, lambda name: name.endswith('.meta')),
        approvedNonCodeAssets=unchanged(before, after, lambda name: '/Assets/' in name and not name.endswith(('.cs', '.java', '.meta'))),
        gameplayM46M48=unchanged(before, after, lambda name: '/M46/' in name or '/M48/' in name),
        profileEconomyAndShop=unchanged(before, after, lambda name: any(part in name for part in ('/App/Profile/', '/App/Shop/', '/App/ShopCheckout86/', '/App/ServerGameplay/', '/App/ServerAccount/', '/App/NoMovesDesign/'))),
        scope='Compared with sealed102, not dirty GitHEAD. The final fixture-only epoch differs from the passed Regional/General epoch only in TeamsDiscovery103Verification.cs. No backend, artwork, gameplay, economy, engine, SDK or device change is inferred.')
    for key in ('engineSettingsPackages', 'existingMetaBytes', 'approvedNonCodeAssets', 'gameplayM46M48', 'profileEconomyAndShop'):
        if not delta[key]['unchanged']:
            raise ValueError('UnrelatedBoundaryChanged103:' + key)
    write(EVIDENCE / 'SourceDelta103.json', delta)

    reviewed = EVIDENCE / 'Reviewed'
    reviewed.mkdir(exist_ok=False)
    selection = dict(schemaVersion=1, status='ROOT_REVIEWED_FINAL_EDITOR_CAPTURES103', utc=utc(),
        sourceTag='TeamsMain02', reviewer='Root agent individually viewed both final native PNGs.',
        scope='Actual Unity Editor UGUI/camera framebuffer readback using fixed WorldSpace mapping. Unconfigured social service; no fabricated team, live hosting, touch, Android or physical device claim.', images=[])
    for width in (420, 768):
        source = EVIDENCE / ('Native/TeamsMain02/Native/TeamsDiscovery103/Unavailable_ru_' + str(width) + '.png')
        target = reviewed / ('Teams_Unconfigured_ru_' + str(width) + '.png')
        shutil.copyfile(source, target)
        if sha(source) != sha(target):
            raise ValueError('ReviewedImageCopyMustBeByteIdentical103')
        image_width, image_height = struct.unpack('>II', source.read_bytes()[16:24])
        selection['images'].append(dict(source=bind(source), reviewedCopy=bind(target), width=image_width, height=image_height,
            accepted=True, physicalDevice=False, locale='ru', state='Unconfigured online Teams'))
    selection['invocation'] = bind(EVIDENCE / 'Native/TeamsMain02/Invocation.json')
    write(reviewed / 'Selection103.json', selection)

    initial_review = dict(schemaVersion=1, status='ASSERTIONS_PASS_VISUAL_REJECTED', utc=utc(),
        invocation=bind(EVIDENCE / 'Native/TeamsMain01/Invocation.json'),
        nativeReport=bind(EVIDENCE / 'Native/TeamsMain01/Native/TeamsDiscovery103.json'),
        nativeChecks=254, layouts=15,
        reason='Root individually viewed both initial PNGs and rejected large black lower/right areas. Capture switched an Overlay canvas to a different camera framebuffer after production Fill, retaining stale background bounds.',
        remedy='Test-only fixed WorldSpace canvas before production Reflow/Fill, exact orthographic camera, all-corner containment and complete-edge/>99% painted GPU assertions. Runtime was not changed for this capture defect.',
        finalInvocation=bind(EVIDENCE / 'Native/TeamsMain02/Invocation.json'),
        originalProofsUnmodified=True, initialVisualAcceptance=False)
    write(EVIDENCE / 'InitialVisualReview103.json', initial_review)

    native = []
    warning_rows = []
    for tag in ('TeamsMain01', 'TeamsMain02', 'RegionalMain01', 'GeneralMain01'):
        invocation_path = EVIDENCE / 'Native' / tag / 'Invocation.json'
        invocation = load(invocation_path)
        report_path = invocation_path.parent / invocation['nativeReport']
        report = load(report_path)
        if invocation['status'] != 'PASS_NATIVE103_INVOCATION' or not invocation['mainInputsUnchanged'] or not invocation['projectInputsUnchanged']:
            raise ValueError('PassingNativeSourceBoundInvocationRequired103')
        checks = report.get('checks', report.get('passed', 0))
        checks = checks if isinstance(checks, int) else report.get('passed', 0)
        if tag != 'TeamsMain01':
            native.append(dict(tag=tag, invocation=bind(invocation_path), nativeReport=bind(report_path),
                status=report['status'], checks=checks, cases=report.get('cases', 0), layouts=report.get('layouts', 0),
                scope=report.get('scope', ''), mainSourcesBefore=bind(invocation_path.parent / 'MainSources_before.json'),
                mainSourcesAfter=bind(invocation_path.parent / 'MainSources_after.json'),
                finalSourceEpoch=tag == 'TeamsMain02', runtimeMatchesFinal=True))
        log = ROOT / next(item['path'] for item in invocation['privateLogs'] if item['path'].endswith('/Unity.log'))
        text = log.read_text('utf-8-sig', errors='replace')
        warning_rows.append(dict(tag=tag, invocation=bind(invocation_path), privateLog=bind(log),
            csharpWarningLines=len(re.findall(r'\bwarning CS[0-9]+\b', text)),
            csharpErrorLines=len(re.findall(r'\berror CS[0-9]+\b', text)),
            editorShutdownStackAllocatorDiagnosticObserved='m_LastAlloc not NULL' in text))
    warnings = dict(schemaVersion=1, status='MEASURED_SELECTED_EDITOR_COMPILER_WARNINGS103', utc=utc(),
        selectedCSharpWarningLines=sum(row['csharpWarningLines'] for row in warning_rows),
        selectedCSharpErrorLines=sum(row['csharpErrorLines'] for row in warning_rows), logs=warning_rows,
        buildInvoked=False, buildReportCountsAvailable=False, prior101Il2cppCompileCostNotices=3, priorNoticesRerun=False,
        backendExternalStarletteDeprecationObserved=backend['backendExternalStarletteDeprecationObserved'],
        scope='Four actual Unity2022 Editor invocations, including the retained initial visual failure. C# diagnostics are counted separately from retained Editor shutdown allocator text and external Starlette/httpx deprecation. No Android/IL2CPP or SDK operation was run.')
    write(EVIDENCE / 'CompilerWarnings103.json', warnings)

    final_report = load(EVIDENCE / 'Native/TeamsMain02/Native/TeamsDiscovery103.json')
    prior_summary = load(ROOT / 'Verification/Evidence/Review102/Summary.json')
    summary = dict(schemaVersion=1, status='REVIEWED_TARGETED_TEAMS_FIX_WITH_OPEN_GATES', utc=utc(),
        targetedCodeAndEditorVerificationPassed=True, fullyVetted=False, taskComplete=False, productionApproved=False,
        mainEngine='2022.3.62f3', enginePromoted=False, sdkAddedOrUpgraded=False,
        native=native, sourceDelta=bind(EVIDENCE / 'SourceDelta103.json'),
        compilerWarnings=bind(EVIDENCE / 'CompilerWarnings103.json'), reviewedImages=bind(reviewed / 'Selection103.json'),
        initialRejectedVisuals=bind(EVIDENCE / 'InitialVisualReview103.json'),
        nativeMatrix=dict(locales=['en','es','fr','de','ru'], viewports=[[320,568],[420,900],[768,1024]],
            layouts=15, capturedFinalViewports=[[420,900],[768,1024]], actualEditorUGUI=True,
            physicalDevice=False, connectedFixtureScope='Layout-builder pending/full-team/Create/Join/member guards, not live HTTP mutations or connected UGUI captures.'),
        ordinaryProfileAndPreferences=dict(
            persistentProfilesByteDigestPreserved=final_report['ordinaryProfilesPreserved'],
            exactLanguagePreferencePresenceAndValuePreserved=final_report['languagePreferencePreserved'],
            countryPreferencePreserved=load(EVIDENCE / 'Native/RegionalMain01/Report.json')['ordinaryCountryPreferencePreserved'],
            scope='Actual Editor assertions in the individually bound native suites. No phone profile was inspected or modified.'),
        backend=dict(report=bind(backend_path), executedTests=backend['executedTests'], passedTests=backend['passedTests'],
            failures=backend['failures'], errors=backend['errors'], skipped=backend['skipped'], sourceFiles=backend['sourceFileCount'],
            sourceMatchesSealed102=True, actualReplayWorkerRun=False, fullSuiteRerun=False,
            scope=backend['scope'], guide=backend['guide']),
        android=dict(apkBuiltThisCheckpoint=False, apkInstalledThisCheckpoint=False,
            adbOrDeviceActionThisCheckpoint=False, physicalDeviceInspectedThisCheckpoint=False,
            previous101Artifact=prior_summary['android']['previous101Artifact'],
            previousDeviceVerification='Checkpoint101 historical only. This task does not freshly inspect the phone or certify103 Teams code on Android.'),
        remainingGates=[
            'Hosted managed HTTPS backend and explicit app service configuration are required before online Create/Join are available.',
            'Social service/operator moderation must be configured and verified; rendering a page does not implement a hosted service.',
            'Actual configured Android networking, input, team mutations, reconnect and cross-player acceptance were not run in103.',
            'VK/provider/payment credentials and prior production, performance and all-device gates remain open.'],
        reviewPath='Codex_Handoff/Documentation/103_TEAMS_DISCOVERY_AND_BACKEND_SETUP_REVIEW.txt',
        galleryPath='Verification/Evidence/Review103/Comparison.html',
        scope='Narrow Teams availability/routing repair with actual Editor behavior/layout checks and one focused unchanged-backend module. No APK/device, full backend rerun, new worker, live provider or production acceptance.')
    write(EVIDENCE / 'Summary.json', summary)
    print(json.dumps(dict(status=summary['status'], nativeChecks=[row['checks'] for row in native], backendTests=18,
        changedMain=len(delta['main']['changed']), addedMain=len(delta['main']['added']),
        csharpWarnings=warnings['selectedCSharpWarningLines'], reviewedImages=len(selection['images']))))


if __name__ == '__main__':
    main()
