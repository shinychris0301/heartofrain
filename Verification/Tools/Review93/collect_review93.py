"""Publish/verify the scoped current93 review; never execute app/backend tests.

Fresh reports remain under Review93. A completed review can retain only the
explicitly reviewed, exact Account clipboard failures; they remain FAIL and
their attempted checks never enter passing totals. Unclassified failures block
completion. Missing proof produces Draft.json, never a selectable Summary.json.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review93'
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import PINNED_UNITY, delta, freeze, sha, unchanged

STATUS = 'COMPLETED_SCOPED_APP_BACKEND_REVIEW93_WITH_UNRESOLVED_GATES'
DRAFT = 'IN_PROGRESS_APP_BACKEND_REVIEW93'
ACCOUNT_ERROR = 'approved_modal_code_is_clipboard_only_and_actions_are_confirmed: InvalidOperationException: explicit Copy real clipboard readback matches'
ACCOUNT_HTTP_ERROR = 'Stage3: InvalidOperationException: Explicit Copy returns a valid recovery code only to clipboard'
GENERATED = {'Summary.json', 'Draft.json', 'ArtifactInventory.json', 'Comparison.html'}
GATES = [
    'Historical Account FAILs remain retained; current clipboard/later-stage results are separate. Any unreached actions and ordinary configured Android account acceptance remain open.',
    'Configured ordinary Android managed-account startup, recovery/logout/deletion, social touch workflows and genuine version upgrade remain separate from Editor fixtures.',
    'Owner Console ID/products, production package/signer, owned HTTPS hosting, legal/support policies and staffed moderation are not supplied by local tests.',
    'Pay11.1/Core10.5 vendor manifests declare Unity6000 while the game remains pinned2022.3.62f3; isolated compatibility work does not resolve vendor support or configured Android/provider acceptance.',
    'Actual sandbox success/cancel/unknown outcome/process-death/duplicate/refund/external-bank return and controlled real payments are unverified; production checkout stays blocked.',
    'Real Yandex video/privacy/restart/reward acceptance is unverified; capped client-reported completion is not provider-verified impression proof.',
    'VK registration/provider consent/return acceptance is unverified; cross-device VK journey selection and Google sign-in are not implemented.',
    'Deployed HTTPS/load/worker saturation/monitoring/backup restoration and rollback must be rehearsed on the chosen host; loopback TCP is not production capacity.',
    'Physical low-memory/Android8/tablet/long-session/human campaign and dense-effect performance/fresh-reference gates remain open.',
]


def require(value, code):
    if not value:
        raise RuntimeError(code)


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def bound(value, fresh=False):
    path = (ROOT / value).resolve()
    require(path.is_relative_to(OUT if fresh else ROOT), 'PathOutsideAllowedScope')
    require(path.is_file(), 'RequiredFileMissing:' + path.name)
    return path


def binding(path):
    path = bound(path)
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def verify_binding(item, fresh=False):
    path = bound(item['path'], fresh)
    require(binding(path) == item, 'BoundFileDrift:' + item['path'])
    return path


def sources_match(path, current):
    recorded = read(path)
    require(recorded.get('inputCount') == current['inputCount']
            and unchanged(delta(recorded, current)), 'UnitySourcesNotCurrent:' + Path(path).name)
    return recorded


def backend_sources():
    backend = ROOT / 'Backend'
    paths = [p for name in ('hotr_backend', 'tests', 'tools', 'config')
             for p in (backend / name).rglob('*') if p.is_file() and p.suffix in ('.py', '.json')]
    paths += [backend / name for name in ('requirements.in', 'requirements.lock', 'README.md', 'Run-Local.ps1')]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def configured_cases():
    configuration = read(TOOLS / 'suites.json')
    require(configuration.get('checkpoint') == 93, 'NativeCatalogCheckpointInvalid')
    rows = configuration['cases'] + configuration.get('connectedCases', [])
    names = [row['name'] for row in rows]
    require(len(names) == len(set(names)) and names, 'NativeCatalogDuplicateOrEmpty')
    return {row['name']: row for row in rows}, {row['name'] for row in configuration.get('connectedCases', [])}


def exact_clipboard_failure(name, proof):
    require(not proof.get('error') and not proof.get('failures') and not proof.get('failed'), 'UnexpectedAccountFailureField')
    if name == 'Account':
        require(proof.get('status') == 'FAIL_NATIVE_SERVER_ACCOUNT83_CONTRACTS'
                and proof.get('errors') == [ACCOUNT_ERROR] and proof.get('checks') == 44
                and proof.get('cases') == 8 and proof.get('copyCalls') == 1
                and proof.get('copyScreen') == 'backup' and proof.get('clipboardReadbackLength') == 0
                and proof.get('clipboardReadbackMatched') is False and proof.get('actualHttp') is False
                and proof.get('androidKeystore') is False, 'AccountFailureNotExactClipboardPattern')
        require(proof.get('passed') == [
            'managed_guest_status_is_not_provider_link', 'encrypted_selector_reopens_fixed_pending_scope_and_id',
            'encrypted_selector_pre_and_post_commit_cuts', 'closed_gateway_never_automatically_creates_guest',
            'selector_lost_ack_requires_exact_successor_content', 'disposed_service_and_busy_recovery_cannot_dispatch',
            'recovered_attempt_decision_is_durable_and_id_scoped'], 'AccountPriorCasesIncomplete')
    elif name == 'AccountHttp':
        require(proof.get('status') == 'FAIL_NATIVE_SERVER_ACCOUNT83_CONNECTED_HTTP'
                and proof.get('errors') == [ACCOUNT_HTTP_ERROR] and proof.get('checks') == 12
                and proof.get('actualHttp') is True and proof.get('editorIdentityEphemeral') is True
                and proof.get('android') is False and proof.get('productionEnabled') is False
                and proof.get('selectedThroughOrdinaryHost') is True, 'AccountHttpFailureNotExactClipboardPattern')
        require(proof.get('ordinaryProfilesBefore') == proof.get('ordinaryProfilesAfter')
                and len(proof.get('ordinaryProfilesBefore', '')) == 64, 'AccountHttpOrdinaryDataChanged')
        require(all(proof.get(key) is False for key in (
            'clipboardOnly', 'maskedRecovery', 'explicitLogout', 'explicitRecovery', 'explicitDeletion',
            'explicitFreshGuest', 'settingsReturn', 'localAppearanceUnchanged', 'recoveredRemoteAttemptPreserved',
            'remoteAttemptExplicitlyForfeited', 'rejectedRecoveryBlocked', 'rejectedRecoveryReady',
            'rejectedRecoveryCanRestart')) and proof.get('rejectedRecoveryHttpStatuses') == [],
            'AccountHttpUnreachedStagesRelabelled')
        require(proof.get('passed') == [
            'Ordinary host selected explicit server factory', 'Server genesis starts1250 coins5 lives',
            'Reserve actual server attempt', 'Start spends selected Rocket once', 'Active attempt blocks identity close',
            'Explicit forfeit settles one loss before identity transition', 'Account portrait capture900x1600',
            'Ordinary Save Progress opens truthful managed guest', 'Suspended Settings is not invisible blocking input',
            'Account portrait capture900x1600', 'Account portrait capture900x1600'], 'AccountHttpPriorCasesIncomplete')
    else:
        raise RuntimeError('UnclassifiedNativeFailure:' + name)


def native_check_count(proof, passed):
    """Normalize a scalar or actual labelled-check array without changing it."""
    raw = proof.get('checks', proof.get('total', 0))
    if isinstance(raw, list):
        require(type(proof.get('passed')) is int and type(proof.get('failed')) is int
                and proof['passed'] >= 0 and proof['failed'] >= 0
                and len(raw) == proof['passed'] + proof['failed'], 'NativeLabelledCheckCountInvalid')
        require(all(isinstance(row, dict) and isinstance(row.get('name'), str) and row['name']
                    and row.get('status') in ('PASS', 'FAIL')
                    and (row.get('error') is None or isinstance(row.get('error'), str)) for row in raw),
                'NativeLabelledCheckShapeInvalid')
        require(sum(row['status'] == 'PASS' for row in raw) == proof['passed']
                and sum(row['status'] == 'FAIL' for row in raw) == proof['failed'], 'NativeLabelledCheckTotalsMismatch')
        if passed:
            require(proof['failed'] == 0 and all(row['status'] == 'PASS' and not row.get('error') for row in raw),
                    'NativeLabelledFailureInsidePassingReport')
        return len(raw)
    require(type(raw) is int and raw >= 0, 'NativeCheckCountInvalid')
    return raw


def native_proof(paths, current):
    cases, connected_names = configured_cases()
    rows, sets, seen = [], [], set()
    for path in paths:
        path = bound(path, True)
        record = read(path)
        require(record.get('checkpoint') == 93 and record.get('status') in
                ('PASS_CURRENT_NATIVE_REVIEW93', 'REVIEW93_NATIVE_WITH_FAILURES'), 'NativeSetIncompleteOrInvalid')
        require(record.get('runnerSHA256') == sha(TOOLS / 'run_suites.py')
                and record.get('suiteConfigurationSHA256') == sha(TOOLS / 'suites.json'), 'NativeSetRunnerOrCatalogDrift')
        manifest = path.parent / 'FrozenSources.json'
        require(sha(manifest) == record.get('sourceSHA256'), 'NativeSetManifestBindingInvalid')
        sources_match(manifest, current)
        require(record.get('unityInputCount') == current['inputCount'] and not record.get('sourceDrift'), 'NativeSetSourceDrift')
        require(record.get('runs'), 'NativeSetEmpty')
        for row in record['runs']:
            name = row['name']
            require(name in cases and name not in seen, 'NativeSuiteUnknownOrDuplicate:' + name)
            seen.add(name)
            expected = cases[name]
            require(all(row.get(key) == expected.get(key) for key in ('entry', 'report', 'expected', 'environment', 'quit')),
                    'NativeSuiteConfigurationDrift:' + name)
            invocation_path = bound(row['invocation'], True)
            report_path = bound(row['reportPath'], True)
            require(invocation_path.parent == path.parent / name and report_path == invocation_path.parent / expected['report'],
                    'NativeSuitePathBindingInvalid:' + name)
            invocation, proof = read(invocation_path), read(report_path)
            require(invocation.get('entry') == expected['entry']
                    and invocation.get('outputEnvironmentVariable') == expected['environment']
                    and invocation.get('runnerSHA256') == sha(TOOLS / 'run_native.py')
                    and invocation.get('hashProcessHelperSHA256') == sha(ROOT / 'Verification/Tools/Ads85/run_ads85_native.py')
                    and invocation.get('processSelectorSHA256') == sha(ROOT / 'Verification/Tools/PageBackdrop90/process90.py')
                    and invocation.get('unityExeSHA256') == sha(PINNED_UNITY),
                    'NativeRunnerBindingInvalid:' + name)
            require(type(invocation.get('pid')) is int and invocation['pid'] > 0
                    and invocation.get('inputsUnchanged') is True and invocation.get('unityPidsAfter') == []
                    and not invocation.get('timedOut') and not invocation.get('errorType')
                    and invocation.get('elapsedSeconds', 0) > 0, 'NativeProcessOrInputsInvalid:' + name)
            require(sha(invocation_path.parent / 'FrozenSources.json') == invocation.get('sourceSHA256')
                    and invocation.get('inputCount') == current['inputCount'], 'NativeSuiteManifestBindingInvalid:' + name)
            sources_match(invocation_path.parent / 'FrozenSources.json', current)
            sources_match(invocation_path.parent / 'Sources_after.json', current)
            require(unchanged(read(invocation_path.parent / 'Source_Delta.json')), 'NativeSuiteDeltaChanged:' + name)
            require(sha(invocation_path.parent / 'Unity.log') == invocation.get('unityLogSHA256')
                    and sha(invocation_path.parent / 'Console.log') == invocation.get('consoleSHA256')
                    and sha(report_path) == invocation.get('nativeReportSHA256'), 'NativeReportOrLogDrift:' + name)
            require(proof.get('unity', '2022.3.62f3') == '2022.3.62f3'
                    and invocation.get('nativeStatus') == proof.get('status')
                    and invocation.get('checks') == proof.get('checks', proof.get('total', 0)), 'NativeStatusOrCountDrift:' + name)
            passed = invocation.get('status') == 'PASS_NATIVE_REVIEW93_INVOCATION'
            checks = native_check_count(proof, passed)
            require(row.get('status') == invocation.get('status'), 'NativeSetChildStatusDrift:' + name)
            if passed:
                require(row.get('exitCode') == invocation.get('exitCode') == 0
                        and proof.get('status') == expected['expected']
                        and not any(proof.get(key) for key in ('errors', 'error', 'failures', 'failed')), 'NativeUnexpectedFailure:' + name)
            else:
                require(invocation.get('status') == 'FAIL_NATIVE_REVIEW93_INVOCATION'
                        and row.get('exitCode') == invocation.get('exitCode') == 1, 'NativeUnexpectedProcessFailure:' + name)
            rows.append({'name': name, 'passed': passed, 'checks': checks, 'nativeStatus': proof['status'],
                         'invocation': binding(invocation_path), 'report': binding(report_path),
                         'scope': proof.get('scope', invocation.get('scope')), 'connected': name in connected_names})
        require((record['status'] == 'PASS_CURRENT_NATIVE_REVIEW93') == all(row.get('exitCode') == 0 for row in record['runs']),
                'NativeSetPassStatusInvalid')
        sets.append({'set': binding(path), 'sourceManifest': binding(manifest), 'status': record['status']})
    missing = sorted(set(cases) - seen)
    return {'sets': sets, 'suites': rows, 'configuredSuiteCount': len(cases), 'missingSuites': missing,
            'passedSuites': sum(row['passed'] for row in rows), 'failedSuites': sum(not row['passed'] for row in rows),
            'passedSuiteChecks': sum(row['checks'] for row in rows if row['passed']),
            'failedRunChecks': sum(row['checks'] for row in rows if not row['passed']),
            'scope': 'Actual pinned Editor processes with exact source/log/report bindings. Fixtures, disk state, GPU rendering and connected HTTP retain each native report scope; no physical or live-provider acceptance.'}


def classifications(path, native):
    failures = [row for row in native['suites'] if not row['passed']]
    if not failures:
        require(path is None or read(bound(path, True)).get('failures') == [], 'SpuriousFailureClassification')
        return {'failures': [], 'report': binding(path) if path else None, 'clipboardEnvironment': None}
    if path is None:
        return {'failures': [], 'unclassified': [row['name'] for row in failures]}
    path = bound(path, True)
    record = read(path)
    require(record.get('schemaVersion') == 1 and record.get('status') == 'EXPLICIT_REVIEW93_NATIVE_FAILURES_RETAINED',
            'FailureClassificationStatusInvalid')
    declared = record.get('failures', [])
    require(len(declared) == len(failures) and {row.get('suite') for row in declared} == {row['name'] for row in failures},
            'FailureClassificationSetMismatch')
    result = []
    for actual in failures:
        entry = next(row for row in declared if row['suite'] == actual['name'])
        require(entry.get('acceptancePassed') is False and entry.get('reviewed') is True
                and entry.get('classification') == 'UNRESOLVED_WINDOWS_CLIPBOARD_ACCEPTANCE'
                and entry.get('report') == actual['report'] and entry.get('scope'), 'FailureWasWaivedOrUnbound')
        exact_clipboard_failure(actual['name'], read(verify_binding(actual['report'], True)))
        result.append(dict(entry, failedRunChecks=actual['checks'], nativeStatus=actual['nativeStatus']))
    environment_path = verify_binding(record['clipboardEnvironment'], True)
    environment = read(environment_path)
    require(environment.get('schema') == 1
            and environment.get('status') in ('RECORDED_WINDOWS_CLIPBOARD_ACQUISITION_METADATA86', 'RECORDED_WINDOWS_CLIPBOARD_ACQUISITION_METADATA93')
            and environment.get('probeSHA256') == sha(ROOT / 'Verification/Tools/Review86/probe_clipboard86.py')
            and all(environment.get(key) is False for key in
                    ('clipboardContentRead', 'clipboardContentWritten', 'clipboardTitlesRead', 'userInformationRecorded')),
            'ClipboardMetadataScopeInvalid')
    attempts = environment.get('attempts', [])
    require(environment.get('attemptCount') == len(attempts) == 5
            and [row.get('index') for row in attempts] == list(range(5)), 'ClipboardMetadataAttemptsInvalid')
    return {'report': binding(path), 'failures': result, 'clipboardEnvironment': binding(environment_path),
            'scope': 'Exact failed native assertions remain failed. Separate current Windows acquisition metadata does not prove the exited Unity process cause or an Android defect.'}


def connected_proof(paths, native, backend):
    connected_sets = {item['set']['path'] for item in native['sets']
                      if any(row['connected'] and row['invocation']['path'].startswith(str(Path(item['set']['path']).parent).replace('\\', '/') + '/')
                             for row in native['suites'])}
    covered, result = set(), []
    for path in paths:
        path = bound(path, True)
        record = read(path)
        require(record.get('servicesStopped') is True and record.get('startedSuspendedAndJobAssigned') is True
                and record.get('actualLoopbackListenersClosed') is True and not record.get('errorType'), 'ConnectedServicesNotStopped')
        native_path = bound(record['nativeInvocation'], True)
        require(native_path.relative_to(ROOT).as_posix() in connected_sets
                and sha(native_path) == record.get('nativeInvocationSHA256'), 'ConnectedNativeSetUnbound')
        require(record.get('runnerSHA256') == sha(TOOLS / 'run_connected.py'), 'ConnectedRunnerDrift')
        if record.get('nativeRunnerLogSHA256'):
            require(sha(path.parent / 'NativeRunner.log') == record['nativeRunnerLogSHA256'], 'ConnectedNativeRunnerLogDrift')
        require(record.get('backendReport') == backend['report']['path']
                and record.get('backendReportSHA256') == backend['report']['sha256'], 'ConnectedBackendReportMismatch')
        require(len(record.get('services', [])) == 3 and {row['kind'] for row in record['services']} == {'Gateway', 'Social', 'Payment'},
                'ConnectedServiceKindsIncomplete')
        require(all(row.get('connection', {}).get('ownedKillOnCloseJobAssignedBeforeResume') is True for row in record['services']),
                'ConnectedServicesNotOwnedBeforeExecution')
        fixture_names = {'Gateway': 'serve_server_gameplay83_fixture.py',
                         'Social': 'serve_identity82_fixture.py', 'Payment': 'serve_rustore81_fixture.py'}
        require(all(row.get('fixtureSHA256') == sha(ROOT / 'Verification/Tools' / fixture_names[row['kind']])
                    for row in record['services'])
                and record.get('approvalSHA256') == sha(ROOT / 'Verification/Evidence/ServerGameplay83/Backend/Verified324/Local_Approval.json')
                and record.get('continueFixtureSHA256') == sha(ROOT / 'Verification/Evidence/ServerReplay83/Native/Fixtures/L08_Continue1.job.json'),
                'ConnectedFixtureOrWorkerApprovalDrift')
        selected = read(native_path)
        all_passed = selected.get('status') == 'PASS_CURRENT_NATIVE_REVIEW93'
        require(record.get('status') == ('PASS_CONNECTED_REVIEW93' if all_passed else 'FAIL_CONNECTED_REVIEW93')
                and record.get('nativeRunnerExitCode') == (0 if all_passed else 1), 'ConnectedExitStatusRelabelled')
        covered.add(native_path.relative_to(ROOT).as_posix())
        result.append({'invocation': binding(path), 'status': record.get('status'),
                       'nativeSet': binding(native_path), 'scope': record.get('scope')})
    return {'runs': result, 'uncoveredSets': sorted(connected_sets - covered),
            'scope': 'Separate disposable loopback fixtures and exact native process bindings; no hosted HTTPS or real payment/provider traffic.'}


def backend_proof(path):
    path = bound(path, True)
    record, invocation = read(path), read(path.parent / 'Invocation.json')
    current = backend_sources()
    require(record.get('status') == 'PASS_BACKEND_SERVICE_TESTS' and record.get('skipped') == []
            and record.get('failures') == [] and record.get('errors') == []
            and record.get('sourceInputsChangedDuringRun') == []
            and record.get('sourceSHA256') == record.get('sourceSHA256After') == current,
            'BackendSuiteNotPassedOrSourceDrift')
    require(record.get('actualPinnedWorkerIntegration') is True
            and type(record.get('executedTests')) is int
            and record['executedTests'] == record.get('tests') == len(record.get('passed', [])), 'BackendCountsOrWorkerInvalid')
    require(invocation.get('status') == 'PASS_BACKEND93_FULL_SUITE' and invocation.get('exitCode') == 0
            and invocation.get('runnerSHA256') == sha(TOOLS / 'run_backend.py')
            and invocation.get('serviceReportSHA256') == sha(path)
            and invocation.get('consoleSHA256') == sha(path.parent / 'Console.log')
            and invocation.get('archiveSourceChanges') == []
            and invocation.get('approvalSHA256') == sha(ROOT / 'Verification/Evidence/ServerGameplay83/Backend/Verified324/Local_Approval.json'),
            'BackendInvocationBindingInvalid')
    for relative, digest in current.items():
        require(sha(path.parent / 'Inputs' / relative) == digest, 'BackendSourceArchiveMissing:' + relative)
    return {'report': binding(path), 'invocation': binding(path.parent / 'Invocation.json'),
            'tests': record['executedTests'], 'skips': 0, 'actualPinnedWorkerIntegration': True,
            'sourceSHA256': current, 'scope': record['scope']}


def operations_proof(path, backend):
    path = bound(path, True)
    record = read(path)
    require(record.get('status') == 'PASS_OPERATIONAL_REHEARSAL93'
            and not record.get('failureCode') and record.get('sourceInputsChangedDuringRun') == []
            and record.get('sourceSHA256') == record.get('sourceSHA256After') == backend['sourceSHA256'],
            'OperationsNotPassedOrSourceDrift')
    require(type(record.get('checks')) is int and record['checks'] == len(record.get('passed', []))
            and record['checks'] > 0 and record.get('requests'), 'OperationsChecksInvalid')
    processes = record.get('processes', [])
    require(len(processes) >= 3 and len({row['pid'] for row in processes}) == len(processes)
            and all(row.get('boundToLoopback') is True and row.get('separateProcess') is True
                    and row.get('ownedProcessTerminated') is True and row.get('exitCode') is not None
                    for row in processes), 'OperationsProcessCleanupInvalid')
    details = record.get('details')
    require(isinstance(details, dict) and details.get('parallelReads') == 72
            and details.get('parallelClaimRetries') == 12 and details.get('backup') and details.get('restore'),
            'OperationsScenarioIncomplete')
    require(details.get('realPayments') is False and details.get('realAds') is False
            and details.get('trustedProgressionForged') is False, 'OperationsScopeOverclaimed')
    for label in ('backup', 'restore'):
        action = details[label]
        require(action.get('status') == 'completed' and action.get('operation') == label
                and action.get('destinationWasNew') is True and action.get('inPlaceRestore') is False
                and action.get('fileFsynced') is True, 'OperationsBackupRestoreNotCompleted')
    return {'report': binding(path), 'checks': record['checks'], 'requests': len(record['requests']),
            'processes': len(processes), 'details': details, 'scope': record['scope'], 'limits': record.get('limits', [])}


def backend_supplements(backend, regression_path=None):
    regression_path = bound(regression_path or OUT / 'Backend/Regressions/Service_Regressions.json', True)
    regression = read(regression_path)
    fixed, old = regression.get('fixed', {}), regression.get('oldBehaviorNegativeControls', {})
    require(regression.get('status') == 'PASS_BOUNDARY_REGRESSIONS93'
            and regression.get('runnerSHA256') == sha(regression_path.parent / 'Run.py')
            and regression.get('sourceSHA256') == regression.get('sourceSHA256After') == backend['sourceSHA256']
            and regression.get('sourceInputsChangedDuringRun') == []
            and regression.get('expectedOldBehaviorFailuresObserved') is True, 'BoundaryRegressionSourceOrControlInvalid')
    require(type(fixed.get('tests')) is int and fixed['tests'] > 0
            and fixed.get('tests') == fixed.get('executedTests') == len(fixed.get('passed', []))
            and len(set(fixed['passed'])) == fixed['tests']
            and fixed.get('errors') == fixed.get('failures') == fixed.get('skipped') == [], 'BoundaryFixedCasesNotPassed')
    expected_failures = regression.get('expectedOldBehaviorFailures')
    require(isinstance(expected_failures, list) and expected_failures
            and len(set(expected_failures)) == len(expected_failures)
            and old.get('failures') == expected_failures
            and old.get('tests') == old.get('executedTests') == fixed['tests']
            and len(old.get('failures', [])) + len(old.get('passed', [])) == fixed['tests']
            and old.get('errors') == old.get('skipped') == []
            and set(old['failures']).isdisjoint(old['passed'])
            and set(old['failures'] + old['passed']) == set(fixed['passed']), 'OldBehaviorFailuresMissingOrRelabelled')
    dependency_path = OUT / 'Backend/DependencyAudit/Report.json'
    dependency = read(dependency_path)
    require(dependency.get('status') == 'PASS_DEPENDENCY_OBSERVATION93_NO_MATCHING_ADVISORIES_RETURNED'
            and dependency.get('runnerSHA256') == sha(dependency_path.parent / 'Run.py')
            and dependency.get('allInstalledVersionsMatchLock') is True
            and dependency.get('lock', {}).get('sha256') == sha(ROOT / 'Backend/requirements.lock')
            and dependency.get('pipCheck', {}).get('exitCode') == 0
            and dependency.get('query', {}).get('completed') is True
            and dependency.get('query', {}).get('httpStatus') == 200 and dependency.get('advisories') == [],
            'DependencyObservationInvalid')
    require(dependency.get('packageCount') == len(dependency.get('packages', []))
            and dependency['packageCount'] > 0
            and all(row.get('version') == row.get('installedVersion') for row in dependency['packages']), 'InstalledDependencyMismatch')
    response = dependency_path.parent / 'OSV_Response.json'
    require(sha(response) == dependency['query']['responseSHA256']
            and response.stat().st_size == dependency['query']['responseBytes'], 'DependencyResponseDrift')
    return {'regressions': {'report': binding(regression_path), 'passingCases': fixed['tests'],
                            'expectedOldBehaviorFailures': len(expected_failures), 'scope': regression['scope']},
            'dependencies': {'report': binding(dependency_path), 'packages': dependency['packageCount'],
                             'response': binding(response), 'scope': dependency['scope'], 'limits': dependency['limits']}}


def build_proof(path, current):
    path = bound(path, True)
    wrapper = read(path)
    require(wrapper.get('status') == 'PASS_INTERNAL_ANDROID_BUILDS93'
            and wrapper.get('wrapperSHA256') == sha(TOOLS / 'run_builds.py')
            and wrapper.get('buildHelperSHA256') == sha(ROOT / 'Verification/Tools/Ads85/run_ads85_internal_build.py')
            and wrapper.get('processSelectorSHA256') == sha(ROOT / 'Verification/Tools/PageBackdrop90/process90.py'),
            'BuildWrapperBindingInvalid')
    invocation_path = bound(wrapper['invocation'], True)
    require(sha(invocation_path) == wrapper.get('invocationSHA256'), 'BuildInvocationDrift')
    record = read(invocation_path)
    require(record.get('status') == 'PASS_SDK_FREE_INTERNAL_ANDROID_BUILDS85'
            and record.get('allHistoricalNativeRestored') is True
            and record.get('inputsUnchangedAfterSettingsRestore') is True and record.get('unityPidsAfter') == []
            and record.get('apkInstalledOrLaunched') is False and record.get('servicesStarted') is False,
            'InternalBuildsNotPassed')
    require(record.get('sourceSHA256') == sha(path.parent / 'FrozenSources.json')
            and record.get('sourcesFinalSHA256') == sha(path.parent / 'Sources_final.json')
            and record.get('inputCount') == current['inputCount']
            and record.get('runnerSHA256') == wrapper['buildHelperSHA256']
            and record.get('unityExeSHA256') == sha(PINNED_UNITY), 'BuildSourceOrRunnerBindingInvalid')
    sources_match(path.parent / 'FrozenSources.json', current)
    sources_match(path.parent / 'Sources_final.json', current)
    runs = record.get('runs', [])
    require(len(runs) == 2 and {row['build'] for row in runs} == {'Development', 'NonDevelopment'}, 'BuildPairIncomplete')
    apks = []
    for row in runs:
        folder = invocation_path.parent / row['build']
        require(read(folder / 'Process.json') == row and row.get('status') == 'PASS_INTERNAL_BUILD85'
                and row.get('exitCode') == 0 and row.get('timedOut') is False
                and row.get('processStopped') is True and row.get('exactSettingsRestored') is True
                and row.get('inputsUnchangedAfterRestoration') is True
                and row.get('ownedKillOnCloseJobAssigned') is True, 'BuildChildNotPassed')
        require(sha(folder / 'Unity.log') == row.get('unityLogSHA256')
                and sha(folder / 'Console.log') == row.get('consoleSHA256')
                and sha(folder / 'Sources_after_restore.json') == row.get('sourcesAfterSHA256'), 'BuildChildBindingInvalid')
        sources_match(folder / 'Sources_before.json', current)
        sources_match(folder / 'Sources_after_restore.json', current)
        require(unchanged(read(folder / 'Source_Delta.json')), 'BuildChildSourceDeltaChanged')
        filename = 'Android_Build.json' if row['build'] == 'Development' else 'Android_Release_Build.json'
        require(sha(folder / filename) == row.get('nativeReportSHA256'), 'BuildNativeReportDrift')
        native = read(folder / filename)
        expected = 'PASS_ANDROID_DEVELOPMENT_BUILD' if row['build'] == 'Development' else 'PASS_ANDROID_RELEASE_COMPILE_BUILD'
        require(native.get('status') == row.get('nativeStatus') == expected
                and native.get('unity') == '2022.3.62f3' and native.get('errors') == 0, 'BuildNativeStatusInvalid')
        verify_binding(row['apk'])
        apks.append(dict(row['apk'], development=row['build'] == 'Development'))
    return {'wrapper': binding(path), 'invocation': binding(invocation_path), 'apks': apks, 'scope': wrapper['scope']}


def static_proof(path, builds):
    path = bound(path, True)
    record = read(path)
    require(record.get('status') == 'PASS_REVIEW93_SDK_FREE_INTERNAL_APKS_STATIC'
            and len(record.get('artifacts', [])) == 2
            and {row['sha256'] for row in record['artifacts']} == {row['sha256'] for row in builds['apks']}, 'StaticBuildPairMismatch')
    reports = []
    for row in record['artifacts']:
        require(row.get('package') == 'com.heartoftherain.verification'
                and row.get('nativePaymentAndAdvertisingSdkAbsent') is True
                and row.get('deviceIdentityClassPresent') is True, 'StaticProfileInvalid')
        verify_binding({key: row[key] for key in ('path', 'sha256', 'bytes')})
        artifact_path = bound(path.parent / row['staticArtifactReport'], True)
        artifact = read(artifact_path)
        require(artifact.get('sha256') == row['sha256'] and artifact.get('bytes') == row['bytes']
                and all(artifact.get(key) is True for key in
                        ('zipalign4KiBPass', 'developmentSignatureVerifies', 'elf16KiBLoadSegmentsPass')),
                'StaticArtifactChecksNotPassed')
        reports.append(binding(artifact_path))
    return {'profile': binding(path), 'artifactReports': reports, 'scope': record['scope']}


def pricing_proof():
    path = OUT / 'Pricing/FocusedTests.json'
    record = read(path)
    require(record.get('status') == 'PASS_FOCUSED_HOST_PRICE_CONSISTENCY93'
            and record.get('exitCode') == 0 and record.get('testsRun') == 4
            and record.get('approvedRubles') == [99, 299, 699, 1099, 2099, 4099]
            and record.get('coinRewards') == [1000, 5000, 10000, 25000, 50000, 100000], 'PricingControlsNotPassed')
    for item in record['inputs']:
        verify_binding(item)
    require(sha(bound(record['log']['path'], True)) == record['log']['sha256'], 'PricingLogDrift')
    return {'report': binding(path), 'tests': 4, 'approvedRubles': record['approvedRubles'],
            'coinRewards': record['coinRewards'], 'scope': record['scope']}


def native_visual_proof(native):
    path = OUT / 'NativeVisualReview.json'
    if not path.is_file():
        return None
    record = read(path)
    require(record.get('schemaVersion') == 1 and record.get('status') == 'ROOT_REVIEWED_SELECTED_NATIVE93_FRAMES'
            and record.get('scope') and record.get('captures'), 'NativeVisualReviewScopeInvalid')
    folders = [bound(row['invocation']['path'], True).parent for row in native['suites']]
    for row in record['captures']:
        image = verify_binding(row['image'], True)
        require(row.get('reviewed') is True and row.get('scope') and image.suffix.lower() == '.png'
                and any(image.is_relative_to(folder) for folder in folders), 'NativeVisualFrameNotBoundToSelectedRun')
    verify_binding(record['smallProfileAssessment'], True)
    return {'report': binding(path), 'captures': record['captures'], 'scope': record['scope'],
            'smallProfileAssessment': record['smallProfileAssessment'], 'limitations': record.get('limitations', [])}


def tool_bindings():
    paths = list(TOOLS.glob('*.py')) + [TOOLS / 'suites.json', ROOT / 'Verification/Tools/collect_results.py',
        ROOT / 'Verification/Tools/Ads85/run_ads85_native.py', ROOT / 'Verification/Tools/Ads85/run_ads85_internal_build.py',
        ROOT / 'Verification/Tools/PageBackdrop90/process90.py', ROOT / 'Verification/Tools/check_apk.py',
        ROOT / 'Verification/Tools/Review86/probe_clipboard86.py']
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def assemble(args, current):
    components, missing = {}, []
    if args.native:
        components['native'] = native_proof(args.native, current)
        missing += ['NativeSuite:' + name for name in components['native']['missingSuites']]
        components['classifications'] = classifications(args.classification, components['native'])
        missing += ['UnclassifiedNativeFailure:' + name for name in components['classifications'].get('unclassified', [])]
        visual = native_visual_proof(components['native'])
        if visual:
            components['nativeVisual'] = visual
    else:
        missing.append('CurrentNativeSuites')
    if args.backend:
        components['backend'] = backend_proof(args.backend)
        components['backendSupplements'] = backend_supplements(components['backend'], getattr(args, 'regressions', None))
    else:
        missing.append('FullBackendSuite')
    if args.operations and 'backend' in components:
        components['operations'] = operations_proof(args.operations, components['backend'])
    else:
        missing.append('TCPRestartRestoreOperations')
    if 'native' in components and 'backend' in components:
        components['connected'] = connected_proof(args.connected, components['native'], components['backend'])
        missing += ['ConnectedWrapper:' + name for name in components['connected']['uncoveredSets']]
    else:
        missing.append('ConnectedNativeServices')
    if args.builds:
        components['builds'] = build_proof(args.builds, current)
    else:
        missing.append('BothCurrentAndroidBuilds')
    if args.android and 'builds' in components:
        components['androidStatic'] = static_proof(args.android, components['builds'])
    else:
        missing.append('CurrentAndroidStaticChecks')
    if getattr(args, 'phone', None):
        require('builds' in components and 'androidStatic' in components, 'PhoneRequiresAcceptedBuildsAndStaticChecks')
        sys.path.insert(0, str(TOOLS))
        from phone_proof import verify_phone
        development = next(row for row in components['builds']['apks'] if row['development'])
        components['physical'] = verify_phone(bound_directory(args.phone), current, development)
    if getattr(args, 'regression', None):
        require('physical' in components, 'PhysicalRegressionRequiresCurrentPhoneProof')
        sys.path.insert(0, str(TOOLS))
        from phone_regression_proof import verify_regression
        development = next(row for row in components['builds']['apks'] if row['development'])
        components['physicalRegression'] = verify_regression(bound(args.regression, True), current, development)
    components['pricing'] = pricing_proof()
    return components, missing


def inventory():
    return {path.relative_to(ROOT).as_posix(): {'sha256': sha(path), 'bytes': path.stat().st_size}
            for path in sorted(OUT.rglob('*')) if path.is_file() and path.relative_to(OUT).as_posix() not in GENERATED}


def render(summary):
    def a(relative, label):
        href = Path(relative).relative_to('Verification/Evidence/Review93').as_posix()
        return '<a href="' + html.escape(href, quote=True) + '">' + html.escape(label) + '</a>'
    rows = []
    c = summary['components']
    if 'native' in c:
        n = c['native']
        rows.append(('Pinned Unity Editor', f"{n['passedSuites']} passing suites / {n['passedSuiteChecks']:,} checks; "
                     f"{n['failedSuites']} failed suites / {n['failedRunChecks']} attempted checks kept separate."))
    if 'backend' in c:
        rows.append(('Backend service tests', str(c['backend']['tests']) + ' passed, zero skips; approved real Windows gameplay worker.'))
    if 'operations' in c:
        o = c['operations']
        rows.append(('Loopback TCP operations', f"{o['checks']} checks / {o['requests']} timed requests / {o['processes']} owned server processes; restart and fresh-path restore. Not hosted capacity."))
    rows += [('Android', 'Both current SDK-free internal builds and static artifact checks.' if 'androidStatic' in c else 'Pending; no current Android acceptance inferred.'),
             ('Shop prices', '99 / 299 / 699 / 1,099 / 2,099 / 4,099 RUB. Actual configured checkout still uses SDK amountLabel.')]
    failures = c.get('classifications', {}).get('failures', [])
    body = ''.join('<tr><td>' + html.escape(k) + '</td><td>' + html.escape(v) + '</td></tr>' for k, v in rows)
    failed = ''.join('<li>' + html.escape(f["suite"] + ': ' + f['classification'] + '. ' + f['scope']) + '</li>' for f in failures)
    pending = ''.join('<li>' + html.escape(x) + '</li>' for x in summary['completionBlockers'])
    gates = ''.join('<li>' + html.escape(x) + '</li>' for x in summary['remainingGates'])
    def figure(item, caption):
        href = Path(item['path']).relative_to('Verification/Evidence/Review93').as_posix()
        safe = html.escape(href, quote=True)
        return '<figure><a href="' + safe + '"><img loading="lazy" src="' + safe + '"></a><figcaption>' + html.escape(caption) + '</figcaption></figure>'
    native_gallery = ''
    if 'nativeVisual' in c:
        native_gallery = ('<h2>Selected native renders actually reviewed</h2><p>'
                          + html.escape(c['nativeVisual']['scope']) + ' '
                          + a(c['nativeVisual']['report']['path'], 'Root review and image hashes') + '</p><div class="gallery">'
                          + ''.join(figure(row['image'], row['scope']) for row in c['nativeVisual']['captures']) + '</div>')
    phone_gallery = ''
    if 'physical' in c:
        physical = c['physical']
        captions = {name: row['scope'] for row in physical['cases'] for name in row['captures']}
        displayed = set()
        pictures = []
        for row in physical['captures']:
            item = row['image']
            if item['path'] not in displayed:
                pictures.append(figure(item, captions.get(item['path'], 'Root-reviewed original Android OS screenshot.')))
                displayed.add(item['path'])
        phone_gallery = ('<h2>Current APK on the real phone</h2><p>' + html.escape(physical['scope']) + ' '
                         + a(physical['visualAssessment']['path'], 'Root phone review and preservation evidence')
                         + '</p><div class="gallery">' + ''.join(pictures) + '</div>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>App and backend operational review93</title><style>body{max-width:1120px;margin:36px auto;padding:0 22px;font:17px/1.5 system-ui;color:#183448;background:#faf7ef}'
            'table{border-collapse:collapse;width:100%}th,td{border:1px solid #bdc8ca;text-align:left;padding:12px}a{color:#12648a}code{overflow-wrap:anywhere}'
            '.gallery{display:flex;flex-wrap:wrap;gap:20px}figure{margin:0;width:245px}img{width:100%;height:auto}figcaption{font-size:14px}</style>'
            '<h1>App and backend operational review · 93</h1><p><strong>' + html.escape(summary['status']) + '</strong></p>'
            '<p>Production is not approved. Prior and current failed tests remain separate from passing counts; rendered pages do not establish live providers or hosted operations.</p>'
            '<table><tr><th>Area</th><th>Evidence scope</th></tr>' + body + '</table>'
            '<p>' + a('Verification/Evidence/Review93/Summary.json' if summary['status'] == STATUS else 'Verification/Evidence/Review93/Draft.json', 'Bound current review')
            + ' · <a href="../../../Release/RuStore/Launch_Readiness93.md">Detailed owner launch checklist</a>'
            ' · <a href="../../../Codex_Handoff/Documentation/93_APP_BACKEND_OPERATIONAL_REVIEW.md">Findings and modification plan</a>'
            ' · <a href="FeatureCoverage.json">25-area feature coverage and remaining acceptance</a></p>'
            '<h2>Retained failures</h2><ul>' + failed + '</ul><h2>Review work pending</h2><ul>' + pending
            + '</ul>' + native_gallery + phone_gallery + '<h2>Production and broader acceptance gates</h2><ul>' + gates + '</ul>'
            '<p>There is no new automatic visual approval in this report. Historical phone captures retain their original exact source and device scopes. '
            'Current native screenshots are render artifacts until explicitly reviewed.</p></html>')


def serial_args(args):
    return {'native': [str(bound(p, True).relative_to(ROOT).as_posix()) for p in args.native],
            'connected': [str(bound(p, True).relative_to(ROOT).as_posix()) for p in args.connected],
            **{name: bound(getattr(args, name), True).relative_to(ROOT).as_posix() if getattr(args, name) else None
               for name in ('backend', 'operations', 'builds', 'android', 'classification', 'regression', 'regressions')},
            'phone': bound_directory(args.phone).relative_to(ROOT).as_posix() if getattr(args, 'phone', None) else None}


def bound_directory(value):
    path = (ROOT / value).resolve()
    require(path.is_relative_to(OUT) and path != OUT and path.is_dir(), 'PhoneDirectoryOutsideReview93')
    return path


def publish(args):
    current = freeze()
    components, missing = assemble(args, current)
    complete = not missing
    native = components.get('native', {})
    summary = {'schemaVersion': 1, 'checkpoint': 93, 'source_checkpoint': 93,
               'status': STATUS if complete else DRAFT, 'utc': datetime.now(timezone.utc).isoformat(),
               'proofArguments': serial_args(args), 'components': components, 'completionBlockers': missing,
               'unityInputCount': current['inputCount'], 'sourceManifest': None, 'sourceSHA256': None,
               'toolSHA256': tool_bindings(), 'allNativeSuitesPassed': native.get('failedSuites', 1) == 0 and not native.get('missingSuites', [1]),
               'allAcceptancePassed': False, 'allHistoricalFailuresClosed': False, 'releaseApproved': False,
               'productionReady': False, 'publicBackendDeployed': False, 'realPaymentsVerified': False,
               'realAdsVerified': False, 'wholeGameSmoothnessCertified': False, 'currentApkInstalled': 'physical' in components,
               'remainingGates': GATES,
               'scope': 'Current scoped app/backend engineering review, exact source-bound Editor/HTTP/service/internal Android evidence and local TCP operations. This is not exhaustive real-world production, provider, human campaign or physical-performance certification.'}
    if native.get('sets'):
        summary['sourceManifest'] = native['sets'][0]['sourceManifest']
        summary['sourceSHA256'] = summary['sourceManifest']['sha256']
    OUT.mkdir(parents=True, exist_ok=True)
    if complete:
        require(not (OUT / 'Summary.json').exists(), 'FinalReviewAlreadyPublished')
        files = inventory()
        (OUT / 'ArtifactInventory.json').write_text(json.dumps(files, indent=2) + '\n', encoding='utf-8')
        summary['artifactInventory'] = binding(OUT / 'ArtifactInventory.json')
    path = OUT / ('Summary.json' if complete else 'Draft.json')
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (OUT / 'Comparison.html').write_text(render(summary), encoding='utf-8')
    return summary


def verify():
    summary = read(OUT / 'Summary.json')
    require(summary.get('status') == STATUS and summary.get('checkpoint') == summary.get('source_checkpoint') == 93
            and summary.get('completionBlockers') == [], 'ReviewNotComplete')
    require(all(summary.get(key) is False for key in ('allAcceptancePassed', 'allHistoricalFailuresClosed', 'releaseApproved',
                'productionReady', 'publicBackendDeployed', 'realPaymentsVerified', 'realAdsVerified', 'wholeGameSmoothnessCertified')),
            'ReviewOverclaimsAcceptance')
    current = freeze()
    sources_match(verify_binding(summary['sourceManifest'], True), current)
    require(summary.get('unityInputCount') == current['inputCount']
            and summary.get('sourceSHA256') == summary['sourceManifest']['sha256']
            and summary.get('toolSHA256') == tool_bindings(), 'ReviewSourceOrToolDrift')
    files = read(verify_binding(summary['artifactInventory'], True))
    require(files == inventory(), 'ReviewArtifactInventoryDrift')
    for relative, item in files.items():
        verify_binding(dict(path=relative, **item), True)
    args = argparse.Namespace(**summary['proofArguments'])
    components, missing = assemble(args, current)
    require(missing == [] and components == summary['components'], 'PublishedComponentProofDrift')
    require(summary.get('currentApkInstalled') == ('physical' in components), 'PhoneInstallationClaimUnbound')
    require(summary.get('allNativeSuitesPassed') == (components['native']['failedSuites'] == 0), 'NativeAggregatePassRelabelled')
    require(summary.get('remainingGates') == GATES, 'RemainingGatesRemoved')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--native', action='append', default=[])
    parser.add_argument('--connected', action='append', default=[])
    for name in ('backend', 'operations', 'builds', 'android', 'classification', 'phone', 'regression', 'regressions'):
        parser.add_argument('--' + name)
    args = parser.parse_args()
    value = publish(args) if args.publish else verify()
    print(json.dumps({'status': value['status'], 'unityInputs': value['unityInputCount'],
                      'completionBlockers': value['completionBlockers'],
                      'nativePassingChecks': value['components'].get('native', {}).get('passedSuiteChecks'),
                      'backendTests': value['components'].get('backend', {}).get('tests')}))


if __name__ == '__main__':
    main()
