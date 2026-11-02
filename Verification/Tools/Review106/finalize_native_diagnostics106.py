"""Bind already completed106 Editor proofs; run no suite, build or device action.

This agent owns only compiler, retained-failure/epoch and process/preservation
metadata. Root owns publication/images/summary; the client owns source delta.
"""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import sha, utc, write
sys.path.insert(0, str(ROOT / 'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids

OUT = ROOT / 'Verification/Evidence/Review106'
FINAL_TAG = 'BackdropMain01'
TAGS = ('BeforeMain01', 'GoalMain01', 'GoalMain02', 'GoalMain03',
        'NavMain01', 'NavMain02', 'NavMain03', 'NavMain04', 'NavMain05',
        'NavMain06', 'NavMain07', 'AfterMain01', 'GeneralMain01', 'BackdropMain01')
PASS_TAGS = ('BeforeMain01', 'GoalMain03', 'NavMain07', 'AfterMain01',
             'GeneralMain01', 'BackdropMain01')
GOAL_FILES = (
    'Unity/Assets/HeartOfTheRain/M47/Runtime/GameplayHUD.cs',
    'Unity/Assets/HeartOfTheRain/M47/Runtime/GoalIconLayout106.cs',
    'Unity/Assets/HeartOfTheRain/Verification/Editor/GoalOptics106Verification.cs')
CAPTURE = 'Unity/Assets/HeartOfTheRain/Verification/Editor/BaselineCapture106.cs'
CAPTURE_SHA = 'e9329f43e1accf4e2a9e79647aa568b7ba63cced44ef2ac2020fb22448ab4a86'


def load(path):
    return json.loads(path.read_text('utf-8-sig'))


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path),
                bytes=path.stat().st_size)


def delta(before, after):
    return dict(added=sorted(after.keys() - before.keys()),
                removed=sorted(before.keys() - after.keys()),
                changed=sorted(n for n in before.keys() & after.keys()
                               if before[n] != after[n]))


def main():
    records, warnings, epochs = {}, [], []
    final = load(OUT / 'Native' / FINAL_TAG / 'MainSources_after.json')['files']
    for tag in TAGS:
        base = OUT / 'Native' / tag
        invocation_path = base / 'Invocation.json'
        invocation = load(invocation_path)
        report_path = base / invocation['nativeReport']
        report = load(report_path)
        before = load(base / 'MainSources_before.json')['files']
        after = load(base / 'MainSources_after.json')['files']
        if (not invocation['mainInputsUnchanged'] or not invocation['projectInputsUnchanged']
                or before != after or invocation['unityPidsAfter']
                or invocation['actualEngine'] != '2022.3.62f3'
                or not invocation['ownedJobAssignedBeforeResume']):
            raise ValueError('PreservedNativeSourceAndProcessEpochRequired106:' + tag)
        passed = tag in PASS_TAGS
        if invocation['status'] != ('PASS_NATIVE106_INVOCATION' if passed else 'FAIL_NATIVE106_INVOCATION'):
            raise ValueError('ExpectedRecordedOutcomeRequired106:' + tag)
        if sha(report_path) != invocation['nativeReportSHA256']:
            raise ValueError('UnchangedNativeReportRequired106:' + tag)
        records[tag] = dict(invocation=invocation, report=report, base=base, sources=after)
        epochs.append(dict(tag=tag, invocation=bind(invocation_path), nativeReport=bind(report_path),
            status=invocation['status'], nativeStatus=report['status'],
            checks=invocation['checks'], completedCases=report.get('cases', 0),
            completedLayouts=report.get('layouts', 0), completedGpuLayouts=report.get('gpuLayouts', 0),
            mainSourcesBefore=bind(base / 'MainSources_before.json'),
            mainSourcesAfter=bind(base / 'MainSources_after.json'),
            fullMainEpochMatchesFinal=after == final, recordedEpochToFinal=delta(after, final),
            originalReportAndInputsPreserved=True))
        entry = next(p for p in invocation['privateLogs'] if p['path'].endswith('/Unity.log'))
        log = ROOT / entry['path']
        if sha(log) != entry['sha256']:
            raise ValueError('UnmodifiedPrivateEditorLogRequired106:' + tag)
        text = log.read_text('utf-8-sig', errors='replace')
        warnings.append(dict(tag=tag, invocation=bind(invocation_path), privateLog=bind(log),
            csharpWarningLines=len(re.findall(r'\bwarning CS[0-9]+\b', text)),
            csharpErrorLines=len(re.findall(r'\berror CS[0-9]+\b', text)),
            licensingRefreshAccessTokenDiagnosticObserved='Access token is unavailable; failed to update' in text,
            editorShutdownStackAllocatorDiagnosticObserved='m_LastAlloc not NULL' in text))

    compiler = dict(schemaVersion=1, status='MEASURED_RECORDED_EDITOR_COMPILER_WARNINGS106',
        utc=utc(), actualEditorInvocations=len(TAGS), mainEngine='2022.3.62f3',
        selectedCSharpWarningLines=sum(v['csharpWarningLines'] for v in warnings),
        selectedCSharpErrorLines=sum(v['csharpErrorLines'] for v in warnings),
        logs=warnings, buildInvoked=False, buildReportCountsAvailable=False,
        il2cppOrAndroidCompilerInvoked=False, apkBuilt=False,
        scope='Fourteen actual main Unity2022 Editor invocations, including eight retained failed rendering assertions. C# diagnostics are counted independently from non-blocking Editor licensing-refresh and shutdown allocator diagnostics. No claim that every Unity/runtime/platform warning is resolved, and no Android/IL2CPP/build warning result is inferred.')

    failures = [
        ('GoalMain01', 'ACTUAL_RENDERED_PANEL_CONTAINMENT_FAILURE',
         'All12 GPU layouts rejected the enlarged126px objective panel against the painted blue outer-header boundary; first720px framebuffer point183,1395.',
         'Reduce objective panel to122px, common visible art58px inside60px cell and bounded count geometry. Strict outer-header/cream assertions retained.', 'GoalMain03'),
        ('GoalMain02', 'ACTUAL_NARROW_ICON_COUNT_GAP_FAILURE',
         'One360x800 four-goal rainlight layout has insufficient actual icon/count gap at the1.16 count pulse peak;107 layouts and11 GPU layouts completed.',
         'Move count center from134 to136 logical pixels; keep artwork/panel/font and strict painted-margin/gap tests.', 'GoalMain03'),
        ('NavMain01', 'ACTUAL_PRESSED_LABEL_FRAME_BUDGET_FAILURE',
         'Pressed Teams label reaches the selected frame shadow/border when that frame shrinks beneath fixed text;6 cases completed.',
         'Keep selected frame bounds stationary; retain animated tint and centered icon pulse and add a frame-bounds invariant.', 'NavMain07'),
        ('NavMain02', 'CONSERVATIVE_PALE_CYAN_CLASSIFIER_FALSE_POSITIVE',
         'Resting selected-frame rectangle point maps to dock42,149. Root independent source read found pale cyan234,250,255,253; strict chroma threshold incorrectly rejected an enclosed highlight.10 cases completed; this does not establish an opaque-art spill.',
         'Final8percent side inset adds deliberate end clearance. Later source row-span classifier includes enclosed pale cyan with real gold/transparent/outside negative controls; containment criteria stay.', 'NavMain07'),
        ('NavMain03', 'ACTUAL_TINY_LABEL_BORDER_BUDGET_FAILURE',
         'A320px/inset/1.5scale label box is only about5.4 logical pixels high but still paints a minimum-font glyph/shadow into the own-frame dark border; source225,156 is5,2,3,253.30 cases completed.',
         'Omit only visual text in too-small logical label boxes; preserve accessible full name, button action and fixed hit rectangle. Final cutoff is10 logical pixels.', 'NavMain07'),
        ('NavMain04', 'CONSERVATIVE_PALE_CYAN_CLASSIFIER_FALSE_POSITIVE',
         '393x852 resting frame bounding rectangle maps to dock56,157 pale cyan237,252,255,253 inside strong-blue row span38..551. Root viewed diagnostic image and accepted frame containment.80 cases completed.',
         'Test-only source row-span rule admits enclosed cyan highlights and retains real gold/transparent/outside negatives. No further runtime shrink. Rectangular alpha-bounds sampling remains conservative.', 'NavMain07'),
        ('NavMain05', 'ACTUAL_LOCALIZED_ACCENT_ICON_LABEL_OVERLAP',
         'All400 RU cases and13 other locale cases completed before French selectedTeams E-accent glyph/shadow overlaps the icon at393x852; the UTF8 label is correctly encoded.',
         'Move selected-label top from.63 to.66 of frame height, preserving all other geometry and strict overlap checks.', 'NavMain07'),
        ('NavMain06', 'ACTUAL_SMALL_FRAME_LOWER_CORNER_BUDGET_FAILURE',
         'At768x1024/2.5scale the9.014px label box still paints a31x9.72px glyph/shadow into the own-frame lower gold corner242,119 (248,159,63,253);280 cases completed before French cases were reached.',
         'Raise the too-small visual-label cutoff9 to10 logical pixels; ordinary393px and larger default labels remain. Full accessibility/action and geometry unchanged.', 'NavMain07')]
    failure_rows = []
    for tag, classification, observed, remedy, final_tag in failures:
        record = records[tag]
        failure_rows.append(dict(tag=tag, classification=classification, observed=observed,
            remedy=remedy, invocation=bind(record['base'] / 'Invocation.json'),
            nativeReport=bind(record['base'] / record['invocation']['nativeReport']),
            failedAssertions=len(record['report'].get('errors', [])),
            retainedCaptures=[bind(record['base'] / name) for name in record['report'].get('captures', [])],
            finalPassingInvocation=bind(OUT / 'Native' / final_tag / 'Invocation.json'),
            originalFailurePreserved=True, originalFailureRelabelledAsPass=False))
    goal_final = records['GoalMain03']['sources']
    goal_scope_equal = all(goal_final[name] == final[name] for name in GOAL_FILES)
    if not goal_scope_equal:
        raise ValueError('AcceptedGoalScopeMustMatchFinal106')
    capture_equal = all(records[tag]['sources'][CAPTURE]['sha256'] == CAPTURE_SHA
                        for tag in ('BeforeMain01', 'AfterMain01')) and sha(ROOT / CAPTURE) == CAPTURE_SHA
    if not capture_equal or any(records[tag]['sources'] != final
                                for tag in ('NavMain07', 'AfterMain01', 'GeneralMain01', 'BackdropMain01')):
        raise ValueError('FinalNativeAndFrozenCaptureEpochRequired106')
    epoch_report = dict(schemaVersion=1, status='RETAINED_NATIVE_FAILURES_AND_EXACT_EPOCHS106', utc=utc(),
        actualInvocations=len(TAGS), passingInvocations=len(PASS_TAGS), retainedFailedInvocations=len(failures),
        failures=failure_rows, invocations=epochs,
        retainedSourceSnapshots=[bind(p) for p in sorted((OUT / 'RetainedSources').glob('*.cs'))],
        goalMain03=dict(fullMainEpochMatchesFinal=False, explicitGoalRuntimeAndTestFilesMatchFinal=goal_scope_equal,
            files=list(GOAL_FILES), sourceDeltaToFinal=delta(goal_final, final),
            repeatedAfterNavigationChanges=False,
            limitation='GoalMain03 precedes later navigation-only edits. Its goal helper/HUD/test bytes match final; the entire Unity source epoch is intentionally reported as different.'),
        matchedBeforeAfter=dict(fixturePath=CAPTURE, sha256=CAPTURE_SHA, exactSameFixtureBytes=capture_equal,
            actualEditorScreen=[720,1600], before=bind(OUT / 'Native/BeforeMain01/Native/BaselineCapture106.json'),
            after=bind(OUT / 'Native/AfterMain01/Native/BaselineCapture106.json'), reconstructedBefore=False),
        finalFourNativeEpochsIdentical=True,
        scope='Failures remain failed immutable original records. Pale-cyan classifier false positives are distinct from actual rendered geometry/text defects. Counts describe assertions and completed layouts/cases, not independent devices or production acceptance.')

    guarded = []
    for tag in ('BeforeMain01', 'GoalMain01', 'GoalMain02', 'GoalMain03', 'AfterMain01'):
        record = records[tag]
        r = record['report']
        keys = ('profilesPreserved', 'serverReviewPreserved', 'languagePreferencePreserved',
                'projectSettingsPreserved' if tag.endswith('BeforeMain01') or tag == 'AfterMain01' else 'settingsPreserved')
        if not all(r[key] for key in keys):
            raise ValueError('ActualNativePreservationAssertionRequired106:' + tag)
        guarded.append(dict(tag=tag, nativeReport=bind(record['base'] / record['invocation']['nativeReport']),
            guards={key:r[key] for key in keys}, gameViewRestored=r.get('gameViewRestored'),
            scope='Exact before/after comparisons within this native invocation. Digests/body data are not exported.'))
    before_report = records['BeforeMain01']['report']
    after_report = records['AfterMain01']['report']
    old = {row['id']:row for row in before_report['alpha']}
    optical_rows = []
    for row in after_report['alpha']:
        previous = old[row['id']]
        a, b = previous['opaquePixels'], row['opaquePixels']
        optical_rows.append(dict(id=row['id'], sprite=row['sprite'],
            before=dict(x=a['x'],y=a['y'],width=a['width'],height=a['height'],
                        maxExtent=max(a['width'],a['height']), centerY=a['y']+a['height']/2),
            after=dict(x=b['x'],y=b['y'],width=b['width'],height=b['height'],
                       maxExtent=max(b['width'],b['height']),centerY=b['y']+b['height']/2),
            measurement='Actual isolated imported-image GPU alpha >24/255; bottom-origin720x1600 framebuffer pixels.'))
    pids = unity_pids()
    if pids:
        raise ValueError('NoBlockingEditorProcessExpected106')
    diagnostics = dict(schemaVersion=1, status='MEASURED_NATIVE_PROCESS_AND_PRESERVATION106', utc=utc(),
        initialReadOnlyInventory=bind(ROOT / 'Verification/Tools/Review106/ProcessInventory106.json'),
        runner=bind(ROOT / 'Verification/Tools/Review106/run_native106.py'),
        finalizer=bind(Path(__file__)), actualEditorInvocations=len(TAGS),
        processes=[dict(tag=tag,pid=records[tag]['invocation']['pid'],
            exitCode=records[tag]['invocation']['exitCode'],
            ownedJobAssignedBeforeResume=True, ownedEditorExited=True,
            reportedBlockingUnityPidsAfter=records[tag]['invocation']['unityPidsAfter'],
            elapsedSeconds=records[tag]['invocation']['elapsedSeconds']) for tag in TAGS],
        blockingUnityPidsAtFinalAudit=pids, unknownExistingProcessesStoppedOrAdopted=False,
        initialPid4068WasKnownHubImage=True,
        unknownProcessScope='The initial six82/83 Python helpers and Hub service were read only and neither adopted nor terminated. The guard excludes the exact known Hub service image; it does not label that service a project Editor.',
        allFourteenInvocationsSourceAndProjectInputsPreserved=True,
        ordinaryPreservationAssertions=guarded,
        preservationScope='Five bound native reports independently compare ordinary Profiles/ServerReview trees, exact saved-language key presence/value and project settings. Other suites use isolated presentation/model fixtures; no blanket physical-device/profile certification is inferred.',
        matchedCaptureFixtureUnchanged=True, gameViewRestoredBeforeAndAfter=True,
        opticalBeforeAfter=optical_rows,
        cameraAndStateScope='Same actual Home.Build and HUD.Build/UpdateState fixture on confirmed720x1600 Editor Screen. Home uses syntheticLevel18/events/1250coins without ProfileHost; the HUD-only empty center deliberately has no board/background. Ordinary profile bytes are hashed only for preservation; no ordinary player profile is loaded through a model factory and no gameplay attempt is started.',
        engine='2022.3.62f3', engineOrSdkMigration=False,
        buildPipelineInvoked=False, apkBuilt=False, apkInstalled=False,
        adbOrPhysicalDeviceAction=False, backendOrWorkerTestsRun=False,
        appBackendHttpOrExternalProviderInvoked=False, timingOrSmoothnessCertification=False,
        fullyVetted=False, productionApproved=False)

    write(OUT / 'CompilerWarnings106.json', compiler)
    write(OUT / 'FailuresAndEpochs106.json', epoch_report)
    write(OUT / 'Diagnostics106.json', diagnostics)
    print(json.dumps(dict(status='BOUND_COMPLETED_NATIVE_DIAGNOSTICS106',
        invocations=len(TAGS), retainedFailures=len(failures),
        csharpWarnings=compiler['selectedCSharpWarningLines'],
        csharpErrors=compiler['selectedCSharpErrorLines'],
        goalScopeMatchesFinal=goal_scope_equal, matchedFixtureUnchanged=capture_equal)))


if __name__ == '__main__':
    main()
