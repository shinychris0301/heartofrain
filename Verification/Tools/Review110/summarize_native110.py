"""Seal only native110 invocation/HTTP/warning evidence; no testing or mutation."""
from pathlib import Path
import hashlib
import json
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'Verification/Evidence/Review110'


def read(path):
    return json.loads(path.read_text('utf-8-sig'))


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)


def main():
    rows = []
    warning_rows = []
    diagnostic_rows = []
    for invocation in sorted((EVIDENCE / 'Native').glob('*/Invocation.json')):
        record = read(invocation)
        path = invocation.parent / record['nativeReport']
        report = read(path) if path.is_file() else {}
        entry = dict(tag=invocation.parent.name, invocation=bind(invocation), report=bind(path) if path.is_file() else None,
            status=record['status'], nativeStatus=report.get('status'), engine=record.get('actualEngine'),
            checks=report.get('checks') if isinstance(report.get('checks'), int) else report.get('passed'),
            cases=report.get('cases'), layouts=report.get('layouts'), layoutsAttempted=report.get('layoutsAttempted'),
            animationCases=report.get('animationCases'), scriptedExchanges=report.get('scriptedExchanges'),
            mainInputsUnchanged=record['mainInputsUnchanged'], guidPreserved=record['assetGuidsUnchanged'],
            sourceDelta=record['sourceDelta'],
            sourceBefore=bind(invocation.parent / 'MainSources_before.json'),
            sourceAfter=bind(invocation.parent / 'MainSources_after.json'),
            importNormalizationAccepted=record.get('importNormalizationAccepted', False),
            ownedChildClosure=record['ownedChildClosure'], unityPidsAfter=record['unityPidsAfter'])
        entry['ordinaryPreservation'] = {key: value for key, value in report.items() if key.endswith('Preserved')}
        rows.append(entry)
        log = ROOT / '.verification-cache/Review110/RawNative' / invocation.parent.name / 'Unity.log'
        text = log.read_text('utf-8-sig', errors='replace') if log.is_file() else ''
        warnings = sorted(set(re.findall(r'(?m)^.*\.cs\(\d+,\d+\): warning CS\d+:.*$', text)))
        errors = sorted(set(re.findall(r'(?m)^.*\.cs\(\d+,\d+\): error CS\d+:.*$', text)))
        warning_rows.append(dict(tag=invocation.parent.name, privateLog=bind(log) if log.is_file() else None,
            uniqueCompilerWarnings=warnings, uniqueCompilerErrors=errors))
        diagnostic_rows.append(dict(tag=invocation.parent.name,
            engineStackAllocatorTeardownMessage='~StackAllocator(ALLOC_TEMP_MAIN) m_LastAlloc not NULL' in text,
            scope='Editor teardown diagnostic, separately classified from C# compile and app/runtime assertions; no Android inference.'))
    required = ['ImportMain02', 'TeamsMain05', 'HelpHttpMain03', 'Access109Main01', 'Access109ScrollMain01', 'Nav108Main01', 'GeneralMain01']
    lookup = {row['tag']: row for row in rows}
    if any(lookup.get(tag, {}).get('status') != 'PASS_NATIVE110_INVOCATION' for tag in required):
        raise ValueError('AllSevenFinalScopedNativeGatesRequired110')
    if any(row['unityPidsAfter'] or not row['ownedChildClosure'].get('allObservedHandlesSignaled') for row in rows):
        raise ValueError('ObservedOwnedProcessClosureRequired110')
    for tag in required:
        if not lookup[tag]['mainInputsUnchanged'] or not lookup[tag]['guidPreserved']:
            raise ValueError('FinalNativeSourceAndGuidPreservationRequired110')
    flow = EVIDENCE / 'Connected/HelpHttpMain03/Flow110.json'
    audit = EVIDENCE / 'Connected/HelpHttpMain03/SQLiteAudit110.json'
    http = EVIDENCE / 'Native/HelpHttpMain03/Native/TeamsChatHelp110_HTTP.json'
    service, database, native_http = read(flow), read(audit), read(http)
    if service['status'] != 'PASS_CONNECTED_HELP110_HTTP' or database['status'] != 'PASS_HELP110_SQLITE_AUDIT':
        raise ValueError('ActualHttpAndIndependentSqliteAuditRequired110')
    failures = [
        dict(epoch='ImporterCorrectionToolPrecondition110', kind='source-preparation tool only',
            reason='Structured manifest record compared to bare digest; rejected before any metadata write or Unity start.',
            retained='RetainedSources/ImporterCorrectionToolPrecondition110/Attempt.json', resolution='Corrected exact sha256 field comparison before the ten authorized new-meta writes.'),
        dict(epoch='ImportMain01', kind='actual importer setting defect',
            reason='Unity normalized the thin TC metas to compressed/default2048 platform settings, ignoring top-level intent.',
            resolution='Only ten NEW metas corrected in native serialized Default/Standalone/Android settings; ImportMain02 passed61.',
            retained='ImporterRoleCorrection110.json'),
        dict(epoch='TeamsMain01', kind='scripted fixture cursor defect',
            reason='Synthetic one-message tail declared olderCursor0 instead of first sequence2; strict transport correctly rejected history.',
            resolution='Corrected cursor contract and strengthened setup assertion; no runtime change.',
            retained='RetainedSources/BeforeHistoryCursorFixtureFix110/TeamsChatHelp110Verification.cs'),
        dict(epoch='TeamsMain02', kind='actual Unity controller defect',
            reason='Synchronous Send/Changed/Reflow destroyed selected composer, then CLR null-conditional dereferenced destroyed Unity object.',
            resolution='Unity-truthy focus release before write/cancel; actual synchronous Send and destroyed-focus Cancel passed later.'),
        dict(epoch='TeamsMain03', kind='actual pending viewport defect plus conservative glyph-classifier failures',
            reason='Tablet pending feed had zero logical height. Font T left bearing(-2) was compared to nominal label box despite painted padding.',
            resolution='Compact pending-only layout restores positive feed; exact font CharacterInfo line bearing must still fit actual painted parent/padded content.'),
        dict(epoch='GlyphDiagnostics01', kind='bounded retained diagnostic invocation, not acceptance',
            reason='Four deliberately selected failing originals recorded exact mesh/box/font/pending dimensions before repair.',
            resolution='Preserved all four originals and failed diagnostic receipt; no pass relabel.'),
        dict(epoch='TeamsMain04', kind='actual German recovery caption defect plus fixture parent-lookup omission',
            reason='Narrow German forget caption remained one line; three Spanish capacity hints needed the same painted request-card lookup as names.',
            resolution='Whole-word at-most-two-line recovery captions, unchanged48-unit hits; measured bearing rule extended to same card. TeamsMain05 passed285/285.'),
        dict(epoch='HelpHttpMain01', kind='pre-Unity owned-service harness rejection',
            reason='Windows venv launcher PID differs from actual owned Python child listener PID.',
            resolution='Require live listener membership in exact assigned-before-resume JobObject plus fresh runId/origin; first service closed, zero enrollment.'),
        dict(epoch='HelpHttpMain02', kind='actual Editor test-fixture boundary rejection before HTTP enrollment',
            reason='Existing ephemeral protected-store helper rejects paths outside its ignored Launch82 fixture root.',
            resolution='Fresh Launch82/TeamHelp110/runId encrypted journals; existing runtime helper guard unchanged. HelpHttpMain03 passed.'),
    ]
    connections = []
    for path in sorted((EVIDENCE / 'Connected').glob('*/Flow110.json')):
        value = read(path)
        connections.append(dict(tag=path.parent.name, report=bind(path), status=value['status'],
            serviceClosure=value.get('serviceClosure'), ownedLoopbackPortClosed=value.get('ownedLoopbackPortClosed'),
            backendRuntimeInputsUnchanged=value.get('backendRuntimeInputsUnchanged'),
            listenerLiveMembershipInExactOwnedJobVerified=value.get('listenerLiveMembershipInExactOwnedJobVerified', False)))
    summary = dict(schemaVersion=1, status='PASS_SCOPED_NATIVE_AND_LOOPBACK110', utc=datetime.now(timezone.utc).isoformat(),
        scope='Actual pinned Unity2022 Editor verification, explicitly scripted component/protocol tests and synthetic UGUI captures, plus separately actual owned-loopback managed HTTP/SQLite. No APK/device/real hosting/provider or production acceptance.',
        mainEngine='2022.3.62f3', nativeInvocationCount=len(rows), passingInvocations=sum(row['status'].startswith('PASS_') for row in rows),
        retainedFailedOrDiagnosticInvocations=sum(not row['status'].startswith('PASS_') for row in rows), finalScopedPassTags=required,
        invocations=rows,
        finalFeature=dict(checks=lookup['TeamsMain05']['checks'], functionalCases=lookup['TeamsMain05']['cases'],
            visualLayouts=lookup['TeamsMain05']['layouts'], locales=5, editorGpuCapturePixelDimensions=[[720,1600],[768,1024]],
            syntheticViewportDimensions=[[360,800],[720,1600],[768,1024]], animationCases=6,
            note='Reported checks include repeated per-node/mesh assertions; they are not75799 distinct product test cases. Captures are actual Editor GPU output of explicitly synthetic state, not physical device photographs.'),
        actualHttp=dict(flow=bind(flow), native=bind(http), independentDatabaseAudit=bind(audit),
            checks=native_http['checks'], cases=native_http['cases'], managedGuests=native_http['managedGuests'],
            identityRequests=native_http['signedRequests'], socialRequests=native_http['socialRequests'], walletReads=native_http['walletReads'],
            totalObservedHttpRequests=database['requestCountHttp'], protectedClientReconstructions=native_http['protectedReconstructionCount'],
            capacityFixtureDebits=[-2,-3], actualLifeCredits=[2,3], naturalCooldownTested=False,
            fixtureRestartIsClientReconstruction=True, operatingSystemProcessRestartClaim=False,
            historicalAndFinalServiceClosures=connections),
        compiler=dict(scannedLogs=warning_rows, uniqueCompilerWarningCount=len(set(line for row in warning_rows for line in row['uniqueCompilerWarnings'])),
            uniqueCompilerErrorCount=len(set(line for row in warning_rows for line in row['uniqueCompilerErrors'])),
            note='C# diagnostics only. Retained runtime/fixture failures and stock Editor teardown messages are classified separately.'),
        editorDiagnostics=diagnostic_rows, retainedFailureAndCorrectionEpochs=failures,
        sourceEpochs=dict(preEdit=bind(ROOT/'Verification/Tools/Review110/Baseline110.json'),
            currentAudit=bind(EVIDENCE/'SourceDelta110_04.json'),
            note='Each invocation binds before/after manifests. Initial ten-new-meta native import normalization is distinct. Subsequent runtime repairs, independent fixture corrections and final HTTP-only path/retry addition retain their earlier bytes; no unchanged suite is relabelled as a later rerun.'),
        preserved=dict(originalMetaAndGuidCount=2958, finalGuidCount=2990, finalMainInputCount=5724,
            ordinaryProfilesAndManagedStoresVerifiedByFinalFeatureAndHttp=True, exactSavedLanguageVerified=True,
            engineSdkOrGlobalSettingsUpgradePerformed=False, approvedNewTcArtworkImported=True, originalR4ArtworkAndMetasChanged=False,
            actualPhysicalDeviceOperation110=False, apkBuiltOrInstalled110=False, installed109BuildUnchanged=True),
        remainingLimitations=['No live staging host or real account/provider service acceptance.',
            'No Android build, install, physical keyboard or device visual acceptance for110; installed109 remains the earlier build.',
            'Scripted hidden-page check proves queued-refresh retention without a gateway; authoritative wallet reads are independently proven by the actual HTTP flow, not a PlayMode gateway refresh dispatch.',
            'Controlled fixed clock and negative capacity fixture ledger entries do not simulate actual gameplay losses or natural four-hour passage.'])
    target = EVIDENCE / 'NativeSummary110.json'
    with target.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(summary, handle, indent=2)
        handle.write('\n')
    print(json.dumps(dict(status=summary['status'], report=target.relative_to(ROOT).as_posix(), nativeInvocations=len(rows),
        passed=summary['passingInvocations'], retained=summary['retainedFailedOrDiagnosticInvocations'],
        compilerWarnings=summary['compiler']['uniqueCompilerWarningCount'], compilerErrors=summary['compiler']['uniqueCompilerErrorCount'])))


if __name__ == '__main__':
    main()
