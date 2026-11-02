"""Validate/publish current86 review evidence; never run services or Unity."""
import argparse
from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review86'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_native86 import SUITES, delta, freeze, sha, unchanged, utc

STATUS = 'COMPLETED_TARGETED_APP_BACKEND_REVIEW86_WITH_UNRESOLVED_GATES'
DEFAULT_SUITES = ('Lifecycle', 'Recovery', 'Checkout', 'Capacity', 'Guard', 'Identity', 'ServerCore', 'Account', 'Rubles', 'AdFlow')
CONNECTED_SUITES = ('IdentityHttp', 'AccountHttp', 'SocialHttp', 'ServerHttp', 'PayHttp')
ACCOUNT_ERROR = 'approved_modal_code_is_clipboard_only_and_actions_are_confirmed: InvalidOperationException: explicit Copy real clipboard readback matches'
ACCOUNT_HTTP_ERROR = 'Stage3: InvalidOperationException: Explicit Copy returns a valid recovery code only to clipboard'


def read(path):
    return json.loads(path.read_text('utf-8-sig'))


def require(value, code):
    if not value:
        raise RuntimeError(code)


def bound(relative):
    path = (ROOT / relative).resolve()
    require(path.is_relative_to(ROOT), 'InputOutsideRepository')
    return path


def clipboard_proof():
    path = OUT / 'Environment/ClipboardAccess.json'
    value = read(path)
    require(value.get('schema') == 1 and value.get('status') == 'RECORDED_WINDOWS_CLIPBOARD_ACQUISITION_METADATA86', 'ClipboardMetadataMissing')
    require(value.get('probeSHA256') == sha(Path(__file__).with_name('probe_clipboard86.py')), 'ClipboardProbeCodeDrift')
    require(all(value.get(k) is False for k in ('clipboardContentRead', 'clipboardContentWritten', 'clipboardTitlesRead', 'userInformationRecorded')), 'ClipboardProbeContentScopeInvalid')
    require(value.get('attemptCount') == 5 and value.get('spacingMilliseconds') == 100
            and value.get('allAcquisitionsDenied') is True and value.get('allAcquisitionErrorsAccessDenied') is True, 'ClipboardDenialNotEstablished')
    rows = value.get('attempts', [])
    require(len(rows) == 5, 'ClipboardAttemptCountInvalid')
    for i, row in enumerate(rows):
        require(row.get('index') == i and row.get('opened') is False and row.get('openError') == 5
                and row.get('closedByProbe') is False and row.get('closeError') == 0
                and row.get('openWindowPresentAfterAttempt') is False, 'ClipboardAcquisitionNotDenied')
        if i:
            require((datetime.fromisoformat(row['utc'].replace('Z', '+00:00')) - datetime.fromisoformat(rows[i-1]['utc'].replace('Z', '+00:00'))).total_seconds() >= .09, 'ClipboardProbeSpacingInvalid')
    return {'report': path.relative_to(ROOT).as_posix(), 'reportSHA256': sha(path),
            'probeSHA256': value['probeSHA256'], 'status': value['status'],
            'attempts': 5, 'openError': 5,
            'scope': 'Separate current Windows Python acquisition metadata; no clipboard content access. Does not prove an Android defect or establish the exited Unity process desktop.'}


def known_clipboard_failure(suite, proof):
    require(not proof.get('error'), 'UnexpectedNativeErrorField')
    if suite == 'Account':
        require(proof.get('status') == 'FAIL_NATIVE_SERVER_ACCOUNT83_CONTRACTS'
                and proof.get('errors') == [ACCOUNT_ERROR] and proof.get('checks') == 44 and proof.get('cases') == 8
                and proof.get('copyCalls') == 1 and proof.get('copyScreen') == 'backup'
                and proof.get('clipboardReadbackLength') == 0 and proof.get('clipboardReadbackMatched') is False
                and proof.get('actualHttp') is False and proof.get('androidKeystore') is False, 'AccountFailureNotExactClipboardPattern')
        require(proof.get('passed') == [
            'managed_guest_status_is_not_provider_link', 'encrypted_selector_reopens_fixed_pending_scope_and_id',
            'encrypted_selector_pre_and_post_commit_cuts', 'closed_gateway_never_automatically_creates_guest',
            'selector_lost_ack_requires_exact_successor_content', 'disposed_service_and_busy_recovery_cannot_dispatch',
            'recovered_attempt_decision_is_durable_and_id_scoped'], 'AccountPriorCasesIncomplete')
    elif suite == 'AccountHttp':
        require(proof.get('status') == 'FAIL_NATIVE_SERVER_ACCOUNT83_CONNECTED_HTTP'
                and proof.get('errors') == [ACCOUNT_HTTP_ERROR] and proof.get('checks') == 12
                and proof.get('actualHttp') is True and proof.get('editorIdentityEphemeral') is True
                and proof.get('android') is False and proof.get('productionEnabled') is False
                and proof.get('selectedThroughOrdinaryHost') is True, 'AccountHttpFailureNotExactClipboardPattern')
        require(proof.get('ordinaryProfilesBefore') == proof.get('ordinaryProfilesAfter')
                and len(proof.get('ordinaryProfilesBefore', '')) == 64, 'FailedAccountHttpChangedOrdinaryProfiles')
        require(all(proof.get(k) is False for k in (
            'clipboardOnly', 'maskedRecovery', 'explicitLogout', 'explicitRecovery', 'explicitDeletion',
            'explicitFreshGuest', 'settingsReturn', 'localAppearanceUnchanged', 'recoveredRemoteAttemptPreserved',
            'remoteAttemptExplicitlyForfeited', 'rejectedRecoveryBlocked', 'rejectedRecoveryReady', 'rejectedRecoveryCanRestart'))
            and proof.get('rejectedRecoveryHttpStatuses') == [], 'AccountHttpLaterAcceptanceMustRemainIncomplete')
        require(proof.get('passed') == [
            'Ordinary host selected explicit server factory', 'Server genesis starts1250 coins5 lives',
            'Reserve actual server attempt', 'Start spends selected Rocket once', 'Active attempt blocks identity close',
            'Explicit forfeit settles one loss before identity transition', 'Account portrait capture900x1600',
            'Ordinary Save Progress opens truthful managed guest', 'Suspended Settings is not invisible blocking input',
            'Account portrait capture900x1600', 'Account portrait capture900x1600']
            and proof.get('captures') == ['Native/Account/Settings_Save_Progress.png', 'Native/Account/Server_Saved.png', 'Native/Account/Backup_Warning.png'], 'AccountHttpPreClipboardPathIncomplete')
    else:
        raise RuntimeError('UnapprovedNativeFailure')
    return {'suite': suite, 'nativeStatus': proof['status'], 'errors': proof['errors'],
            'failedRunChecks': proof['checks'], 'classification': 'UNRESOLVED_WINDOWS_CLIPBOARD_ACCEPTANCE',
            'acceptancePassed': False,
            'blockedAcceptance': ['Clipboard backup readback', 'Remaining account modal actions and confirmations'] if suite == 'Account' else [
                'Clipboard-only backup', 'Subsequent connected logout/recovery/deletion/fresh-guest/settings-return acceptance'],
            'scope': 'Failure retained exactly. Separate Win32 acquisition denial supports an environment gate; it is not a waiver or Android defect proof.'}


def native_proof(invocation, current, expected, allowed_failure):
    record = read(invocation)
    require(record['status'] == 'FAIL_NATIVE_REVIEW86' and record['unityPidsAfter'] == [], 'NativeInvocationStatusUnexpected')
    require(len(record['runs']) == len(expected) and set(r['suite'] for r in record['runs']) == set(expected), 'NativeSuitesIncompleteOrDuplicated')
    require(sha(invocation.parent / 'FrozenSources.json') == record['sourceSHA256'], 'NativeManifestDrift')
    require(unchanged(delta(read(invocation.parent / 'FrozenSources.json'), current)), 'NativeInputsNotCurrent')
    require(record['inputCount'] == current['inputCount'], 'NativeInputCountInvalid')
    require(record['runnerSHA256'] == sha(invocation.parent / 'RunnerInputs/run_native86.py')
            == sha(Path(__file__).with_name('run_native86.py')), 'NativeRunnerDrift')
    require(record['processHelperSHA256'] == sha(invocation.parent / 'RunnerInputs/run_ads85_native.py')
            == sha(ROOT / 'Verification/Tools/Ads85/run_ads85_native.py'), 'NativeProcessHelperDrift')
    count = failed_checks = passed_suites = 0
    failures = []
    captures = {}
    for row in record['runs']:
        require(row['inputsUnchanged'] and row['processStopped']
                and not row['timedOut'] and row['ownedKillOnCloseJobAssigned'], 'NativeProcessNotPassed')
        folder = invocation.parent / 'Suites' / row['suite']
        require(read(folder / 'Process.json') == row, 'NativeProcessRecordDrift')
        require(sha(folder / 'Unity.log') == row['unityLogSHA256'] and sha(folder / 'Console.log') == row['consoleSHA256'], 'NativeLogDrift')
        for stage in ('Before', 'After'):
            manifest = folder / ('Sources_' + stage.lower() + '.json')
            require(sha(manifest) == row['sources' + stage + 'SHA256'] and unchanged(delta(read(manifest), current)), 'NativeSuiteInputsNotCurrent')
        require(unchanged(read(folder / 'Source_Delta.json')), 'NativeSuiteSourceDeltaChanged')
        matches = [p for p in (invocation.parent / 'Native').glob('*.json') if sha(p) == row['nativeReportSHA256']]
        require(len(matches) == 1, 'NativeReportMissingOrDrifted')
        proof = read(matches[0])
        require(proof.get('unity') == '2022.3.62f3' and row['checks'] == proof.get('checks')
                and row.get('cases') == proof.get('cases'), 'NativeCountsOrEngineDrift')
        entry, _, success, play, _ = SUITES[row['suite']]
        require(row['entry'] == 'HeartOfTheRain.Verification.' + entry and row['playMode'] == play, 'NativeEntryOrModeInvalid')
        if row['suite'] == allowed_failure:
            require(row['status'] == 'FAIL_NATIVE' and row['exitCode'] == 1 and row['nativeErrorsEmpty'] is False
                    and row['nativeStatus'] == proof['status'], 'ExpectedFailureWasRelabelled')
            failed = known_clipboard_failure(row['suite'], proof)
            failed.update(report=matches[0].relative_to(ROOT).as_posix(), reportSHA256=sha(matches[0]))
            failures.append(failed)
            failed_checks += proof['checks']
        else:
            require(row['status'] == 'PASS' and row['exitCode'] == 0 and row['nativeStatus'] == success
                    and row['nativeErrorsEmpty'] is True and not proof.get('errors') and not proof.get('error'), 'NativeUnexpectedFailure')
            passed_suites += 1
            if type(row.get('checks')) is int:
                count += row['checks']
        for relative, digest in row.get('captures', {}).items():
            capture = invocation.parent / relative
            require(sha(capture) == digest, 'NativeCaptureDrift')
            captures[capture.relative_to(ROOT).as_posix()] = digest
    require(len(failures) == 1 and passed_suites == len(expected)-1, 'NativeKnownFailureCountInvalid')
    return {'invocation': invocation.relative_to(ROOT).as_posix(), 'invocationSHA256': sha(invocation),
            'invocationStatus': record['status'], 'checks': count, 'passedSuiteChecks': count,
            'passedSuites': passed_suites, 'failedSuites': 1, 'failedRunChecks': failed_checks,
            'knownFailures': failures, 'suites': record['runs'], 'captures': captures}


def connected_proof(path, current):
    record = read(path)
    require(record['status'] == 'FAIL_CONNECTED_REVIEW86' and record['servicesStopped'] is True
            and record.get('nativeRunnerExitCode') == 1 and not record.get('errorType'), 'ConnectedInvocationUnexpected')
    require(sha(bound(record['nativeInvocation'])) == record['nativeInvocationSHA256']
            and sha(path.parent / 'NativeRunner.log') == record['nativeRunnerLogSHA256'], 'ConnectedNativeBindingDrift')
    require(record['runnerSHA256'] == sha(Path(__file__).with_name('run_connected86.py')), 'ConnectedRunnerDrift')
    require(len(record.get('services', [])) == 3 and {r['kind'] for r in record['services']} == {'Gateway', 'Social', 'Payment'}, 'ConnectedServicesIncomplete')
    proof = native_proof(bound(record['nativeInvocation']), current, CONNECTED_SUITES, 'AccountHttp')
    return record, proof


def verify(summary):
    require(summary['status'] == STATUS and summary.get('allNativeSuitesPassed') is False
            and summary.get('allAcceptancePassed') is False, 'ReviewStatusInvalid')
    current = freeze()
    require(unchanged(delta(read(bound(summary['sourceManifest'])), current)), 'CurrentUnityInputsDrifted')
    for relative, digest in summary['evidenceSHA256'].items():
        require(sha(bound(relative)) == digest, 'EvidenceDrift:' + relative)
    for relative, digest in summary['backendSourceSHA256'].items():
        require(sha(bound(relative)) == digest, 'BackendInputsDrifted:' + relative)
    for row in summary['apks']:
        require(sha(bound(row['path'])) == row['sha256'], 'CurrentApkDrifted')
    clipboard = clipboard_proof()
    native = native_proof(bound(summary['native']['invocation']), current, DEFAULT_SUITES, 'Account')
    connected_record, connected = connected_proof(bound(summary['connectedInvocation']), current)
    require(native == summary['native'] and connected == summary['connectedNative'], 'PublishedNativeProofDrift')
    require(clipboard == summary['clipboardEnvironment'], 'PublishedClipboardProofDrift')
    known = native['knownFailures'] + connected['knownFailures']
    require(summary['knownFailures'] == known and len(known) == 2, 'KnownFailuresOmittedOrRelabelled')
    require(summary['passedNativeSuites'] == native['passedSuites'] + connected['passedSuites'] == 13
            and summary['failedNativeSuites'] == native['failedSuites'] + connected['failedSuites'] == 2
            and summary['passedNativeSuiteChecks'] == native['checks'] + connected['checks']
            and summary['failedNativeRunChecks'] == native['failedRunChecks'] + connected['failedRunChecks'], 'NativeTalliesInvalid')
    require(connected_record['backendReport'] == summary['backendReport']
            and connected_record['backendReportSHA256'] == sha(bound(summary['backendReport'])), 'ConnectedBackendBindingDrift')
    return summary


def render(summary):
    def a(path, label):
        return '<a href="' + html.escape(str(Path(path).relative_to('Verification/Evidence/Review86')).replace('\\', '/')) + '">' + html.escape(label) + '</a>'
    cards = ''.join('<figure><a href="' + html.escape(str(Path(p).relative_to('Verification/Evidence/Review86')).replace('\\', '/')) + '"><img src="' + html.escape(str(Path(p).relative_to('Verification/Evidence/Review86')).replace('\\', '/')) + '"></a><figcaption>' + html.escape(Path(p).name) + '</figcaption></figure>' for p in summary['reviewedCaptures'])
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>App and backend review86</title><style>body{max-width:1100px;margin:40px auto;padding:0 22px;font:17px/1.5 system-ui;color:#183448;background:#faf7ef}table{border-collapse:collapse;width:100%}td,th{border:1px solid #c1c8c9;padding:12px;text-align:left}a{color:#12648a}.images{display:flex;flex-wrap:wrap;gap:20px}figure{margin:0;max-width:250px}img{width:100%;height:auto}code{overflow-wrap:anywhere}</style><h1>App and backend review · 86</h1><p>Targeted review completed with unresolved acceptance gates. Two Account suites retain FAIL status; this is not an all-tests pass. Production remains disabled.</p><table><tr><th>Area</th><th>Actual evidence</th></tr><tr><td>Backend</td><td>' + str(summary['backendTests']) + ' passing tests, zero skips; real approved Windows gameplay worker; exact inputs archived.</td></tr><tr><td>Pinned Unity</td><td>' + str(summary['native']['checks'] + summary['connectedNative']['checks']) + ' checks in 13 passing Editor suites; two Account suites remain failed at clipboard readback. Their later checks are incomplete. Native reports retain scripted, real HTTP, disk and UGUI scope separately.</td></tr><tr><td>Android</td><td>Current SDK-free development and non-development IL2CPP compile/static checks. No installation/device or physical performance pass.</td></tr><tr><td>Payment SDK</td><td>Four exact current payment-core files compiled with actual Pay11.1/Core10.5 packages. No SDK initialization, checkout or bank return.</td></tr></table><p>' + a(summary['backendReport'], 'Backend report') + ' · ' + a(summary['native']['invocation'], 'Editor processes') + ' · ' + a(summary['connectedInvocation'], 'Connected processes') + ' · <a href="Summary.json">Bound source/evidence summary</a></p><h2>Repairs</h2><p>Startup retry recursion; invoice URL and refund initiation; transaction-bound identity/auth clocks; bounded strict JSON reception; real database writer readiness; durable purchase recovery and sandbox Shop integration; action-cap guards and contained localized purchase controls.</p><h2>Reviewed native captures</h2><p>These are actual Editor renders. Payment and catalog responses are controlled fixtures. They are not Android or live-provider screenshots.</p><div class="images">' + cards + '</div><h2>Remaining launch gates</h2><ul>' + ''.join('<li>' + html.escape(x) + '</li>' for x in summary['remainingGates']) + '</ul></html>'


def publish(args):
    current = freeze()
    clipboard = clipboard_proof()
    native = native_proof(args.native.resolve(), current, DEFAULT_SUITES, 'Account')
    connected, connected_native = connected_proof(args.connected, current)
    backend = read(args.backend)
    require(backend['status'] == 'PASS_BACKEND_SERVICE_TESTS' and not backend['skipped'] and backend['actualPinnedWorkerIntegration']
            and not backend['sourceInputsChangedDuringRun'], 'BackendNotPassed')
    for relative, digest in backend['sourceSHA256'].items():
        require(sha(bound(relative)) == digest, 'BackendSourceNotCurrent')
        require(sha(args.backend.parent / 'Inputs' / relative) == digest, 'BackendArchiveMissing')
    build = read(args.build)
    require(build['status'] == 'PASS_SDK_FREE_INTERNAL_ANDROID_BUILDS85' and build['allHistoricalNativeRestored']
            and build['inputsUnchangedAfterSettingsRestore'] and not build['unityPidsAfter'], 'InternalBuildsNotPassed')
    require(unchanged(delta(read(args.build.parent / 'FrozenSources.json'), current)), 'BuildInputsNotCurrent')
    sdk = read(args.sdk)
    require(sdk['status'] == 'PASS_CURRENT_RUSTORE_SDK86_EDITOR_COMPILE' and sdk['mainInputsUnchanged']
            and sdk['old81InputsUnchanged'] and not sdk['sdkInitialized'] and not sdk['paymentCalls'], 'SdkCompileNotPassed')
    require(unchanged(delta(read(args.sdk.parent / 'Sources_before.json'), current)), 'SdkProofInputsNotCurrent')
    apk_report = read(args.static)
    require(apk_report['status'] == 'PASS_SDK_FREE_INTERNAL_APKS_STATIC86', 'StaticApksNotPassed')
    require({r['apk']['sha256'] for r in build['runs']} == {r['sha256'] for r in apk_report['artifacts']}, 'StaticBuildBindingsDiffer')
    visuals = read(OUT / 'VisualReview.json')
    for relative, item in visuals['captures'].items():
        require(sha(bound(relative)) == item['sha256'] and relative in native['captures'], 'VisualReviewNotBoundToCurrentNativeRun')
    summary = {'status': STATUS, 'utc': utc(), 'source_checkpoint': 86,
               'allNativeSuitesPassed': False, 'allAcceptancePassed': False,
               'passedNativeSuites': native['passedSuites'] + connected_native['passedSuites'],
               'failedNativeSuites': native['failedSuites'] + connected_native['failedSuites'],
               'passedNativeSuiteChecks': native['checks'] + connected_native['checks'],
               'failedNativeRunChecks': native['failedRunChecks'] + connected_native['failedRunChecks'],
               'knownFailures': native['knownFailures'] + connected_native['knownFailures'],
               'clipboardEnvironment': clipboard,
               'sourceManifest': (args.native.parent / 'FrozenSources.json').relative_to(ROOT).as_posix(),
               'sourceSHA256': sha(args.native.parent / 'FrozenSources.json'), 'unityInputCount': current['inputCount'],
               'backendTests': backend['executedTests'], 'backendReport': args.backend.relative_to(ROOT).as_posix(),
               'backendSourceSHA256': backend['sourceSHA256'], 'native': native, 'connectedNative': connected_native,
               'connectedInvocation': args.connected.relative_to(ROOT).as_posix(), 'apks': apk_report['artifacts'],
               'reviewedCaptures': visuals['captures'], 'productionReady': False, 'currentApkInstalled': False,
               'remainingGates': ['Two strict Account suites fail at clipboard readback. Windows acquisition is denied; subsequent connected recovery/logout/deletion acceptance remains incomplete. Rerun with usable clipboard or actual device; no assertions were waived.',
                   'Registered Console/products, owner signing, hosted HTTPS/backend, legal/support and moderation operations.',
                   'These internal APKs retain the existing API22 minimum and auto-selected target; they are not store releases. Production preflight requires the configured API26-or-higher minimum and explicit matching target.',
                   'Live commerce activation remains blocked; ordinary configured Android startup/touch and real sandbox payment/SDK return, cancellation, restart and update acceptance.',
                   'Stock Pay11.1/Core10.5 packages declare Unity6000.0 while the game remains pinned to2022.3.62f3. Editor API compilation does not resolve vendor support or native Android integration acceptance; no automatic upgrade is authorized.',
                   'Unknown purchases without an invoice/purchase hint and cross-process total protected-store loss need provider/device recovery acceptance.',
                   'Publisher/unit/consent and real rewarded-ad SDK/device acceptance; capped client completion does not prove an ad impression.',
                   'Physical-device, fresh-reference, long-session and dense-effect performance review. Historical gameplay79 timing limits are not closed.',
                   'Production load/worker saturation, deployed backups/restore and operational monitoring; RuStore moderation timing is external.'],
               'scope': 'Current targeted source/service/Editor/HTTP/internal Android compile and SDK API review. No live payment, deployed backend, current device installation or full-game smoothness certification.'}
    evidence = {}
    for path in OUT.rglob('*'):
        if path.is_file() and path.name not in ('Summary.json', 'Comparison.html'):
            evidence[path.relative_to(ROOT).as_posix()] = sha(path)
    summary['evidenceSHA256'] = evidence
    require(not (OUT / 'Summary.json').exists(), 'ReviewAlreadyPublished')
    verify(summary)
    (OUT / 'Summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (OUT / 'Comparison.html').write_text(render(summary), encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    for name in ('native', 'connected', 'backend', 'build', 'sdk', 'static'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    if args.publish:
        require(all(getattr(args, n) for n in ('native', 'connected', 'backend', 'build', 'sdk', 'static')), 'ExplicitProofPathsRequired')
        for name in ('native', 'connected', 'backend', 'build', 'sdk', 'static'):
            setattr(args, name, getattr(args, name).resolve())
        result = publish(args)
    else:
        result = verify(read(OUT / 'Summary.json'))
    print(json.dumps({'status': result['status'], 'backendTests': result['backendTests'], 'unityInputs': result['unityInputCount']}))


if __name__ == '__main__':
    main()
