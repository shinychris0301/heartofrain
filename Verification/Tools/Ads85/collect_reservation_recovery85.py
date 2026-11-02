"""Read-only by default: validate the narrowly scoped SDK85 reservation repair.

--publish writes only ReservationRecovery85/Summary.json and Comparison.html.
Earlier checkpoint85 and full-game SDK reports remain immutable historical proof.
No builds, services, Unity, ADB, APK installation, SDK execution or ads are run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'Verification/Evidence/ShopAds85'
OUT = BASE / 'ReservationRecovery85'
STATUS = 'PASS_TARGETED_RESERVATION_RECOVERY85_WITH_RELEASE_GATES'
BASE_COMMIT = 'a97bf683'
UNITY_CHANGES = {
    'Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/RewardedAdsContracts85.cs',
    'Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/RewardedAdsClient85.cs',
    'Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/RewardedAdsFlow85.cs',
    'Unity/Assets/HeartOfTheRain/Verification/Editor/RewardedAdsFlow85Verification.cs',
}
BACKEND_TEST = 'Backend/tests/test_newads.py'
PROVIDER = 'Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/YandexRewardedAdsProvider85.cs'
FROZEN = BASE / 'Runs/ec3e507dd06148629d7e9cefdcf533b5/FrozenSources.json'
REQUIRED_FLOW_ROWS = {
    'CompletionAndDuplicates', 'ClaimReplyLostAcrossFreshFlow',
    'ReportReplyLostBeforeCommit', 'ReportReplyLostAfterCommit',
    'ReserveReplyLostAcrossFreshFlow', 'NoFillAndUnknownCancellation',
    'ReserveDenialStrictClassifier', 'FreshReserveCooldownDenialResolves',
    'FreshReserveDailyLimitDenialResolves', 'FreshReservePlacementDenialResolves',
    'FreshReserveOpportunityPendingDenialResolves', 'FreshReserveDisabledDenialResolves',
    'FreshReserveUnconfiguredTrustedDenialResolves', 'UnprovenReserveDenialsRetainExactIntent',
    'UnknownReserveThenDefinitiveDenialRetainsExactIntent', 'IncompleteQuotaAndConsent',
    'WalletBeforeReceipt', 'DiskBeforeCommit', 'DiskAfterCommitAcknowledgement',
    'SameProcessCompletionBeforeCommitRetry', 'DiskCorruptionFailsClosed',
    'StaleOwnerAndInterleavedUnwind', 'MissingJournalServerReportedCompletion',
    'MissingJournalServerVerifiedCompletion', 'AccessExpiryDuringExternalAdPresentation',
}
DENIAL_DIAGNOSTICS = {
    'reserveDenialClassifierAccepted': 6, 'reserveDenialClassifierRejected': 36,
    'freshReserveDenialsResolved': 6, 'unprovenReserveDenialsRetained': 6,
    'recoveredReserveDenialsRetained': 3,
}
NEW_BACKEND_TEST = 'tests.test_newads.RewardedAdTests.test_34_reserve_denial_rollback_and_cached_receipt_precede_eligibility_but_not_wallet_guards'


def load_module():
    path = Path(__file__).with_name('collect_ads85.py')
    spec = importlib.util.spec_from_file_location('ads85_original_collector_helpers', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OLD = load_module()
require, sha, when, read = OLD.require, OLD.sha, OLD.when, OLD.strict_json


def rooted(relative):
    path = (ROOT / relative).resolve()
    require(path.is_relative_to(ROOT), 'EvidenceOutsideWorkspace')
    return path


def relative_base(path):
    path = Path(path).resolve()
    require(path.is_relative_to(BASE), 'FollowupEvidenceOutsideCheckpoint85')
    return path.relative_to(BASE).as_posix()


def git_blob(path):
    process = subprocess.run(['git', 'show', BASE_COMMIT + ':' + path], cwd=ROOT,
                             capture_output=True, timeout=30, check=True,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return hashlib.sha256(process.stdout).hexdigest()


def diff(before, after):
    require(set(before) == set(after), 'AddedOrRemovedInputsOutsideRepairScope')
    return {k for k in before if before[k] != after[k]}


def validate_flow(e, native_run, current):
    invocation, frozen = OLD.invocation(e, native_run)
    require(invocation['status'] == 'PASS_TARGETED_NATIVE_SHOP_ADS85'
            and OLD.source_map(frozen) == current, 'FreshCurrentFlowInvocationRequired')
    rows = [row for row in invocation['runs'] if row['suite'] == 'Flow']
    require(len(rows) == 1, 'ExactlyOneFreshFlowSuiteRequired')
    row = rows[0]
    prefix = 'Runs/' + native_run
    process = e.read(prefix + '/Suites/Flow/Process.json')
    report = e.read(prefix + '/Native/RewardedAdsFlow85.json')
    require(process == row and row['status'] == 'PASS' and row['exitCode'] == 0
            and type(row['pid']) is int and row['pid'] > 0 and row['processStopped'] is True
            and row['timedOut'] is False and row['ownedKillOnCloseJobAssigned'] is True
            and row['playMode'] is False and row['quitFlag'] is False
            and row['nativeErrorsEmpty'] is True, 'FreshFlowActualOwnedProcessPassRequired')
    require(when(invocation['startedUtc']) <= when(row['startedUtc']) <= when(report['utc'])
            <= when(row['finishedUtc']) <= when(invocation['finishedUtc']), 'FlowChronologyMismatch')
    e.bind(e.path(prefix + '/Native/RewardedAdsFlow85.json'), row['reportSHA256'])
    e.bind(e.path(prefix + '/Suites/Flow/Unity.log'), row['unityLogSHA256'])
    e.bind(e.path(prefix + '/Suites/Flow/Console.log'), row['consoleSHA256'])
    for label, field in [('Sources_before.json', 'sourcesBeforeSHA256'), ('Sources_after.json', 'sourcesAfterSHA256')]:
        p = prefix + '/Suites/Flow/' + label
        require(OLD.source_map(e.read(p)) == current, 'FlowSourceBeforeAfterMismatch')
        e.bind(e.path(p), row[field])
    p = prefix + '/Suites/Flow/Source_Delta.json'
    require(e.read(p) == {'added': [], 'removed': [], 'changed': []}
            and row['inputsUnchanged'] is True, 'FlowRuntimeDriftDuringSuite')
    e.bind(e.path(p), row['sourceDeltaSHA256'])
    require(report['status'] == row['nativeStatus'] == 'PASS_NATIVE_REWARDED_ADS_FLOW85'
            and report['unity'] == OLD.PINNED and report['errors'] == []
            and report['actualDiskJournal'] is True and report['scriptedApi'] is True
            and report['scriptedProvider'] is True and report['checks'] == 191,
            'FlowRepairNativeRegressionProofMissing')
    cases = report['rows']
    require(len(cases) == report['cases'] == 25 and len({x['name'] for x in cases}) == len(cases)
            and REQUIRED_FLOW_ROWS == {x['name'] for x in cases}
            and all(x['passed'] is True and type(x['checks']) is int and x['checks'] > 0 for x in cases)
            # The suite executes one pinned-Editor precondition outside Case().
            and sum(x['checks'] for x in cases) + 1 == report['checks'], 'RequiredFlowRepairCasesMissingOrFailed')
    require(all(type(report.get(k)) is int and report[k] == v for k, v in DENIAL_DIAGNOSTICS.items()),
            'TypedReserveDenialRegressionDiagnosticsMissing')
    require(row['captures'] == {} and report.get('captures', []) == [], 'UnexpectedVisualApprovalScope')
    return {'runId': native_run, 'status': report['status'], 'checks': report['checks'], 'cases': report['cases'],
            'requiredRepairCases': sorted(REQUIRED_FLOW_ROWS), 'rows': cases,
            'reserveDenialDiagnostics': {k: report[k] for k in DENIAL_DIAGNOSTICS},
            'processId': row['pid'], 'sourceSHA256': invocation['sourceSHA256'],
            'report': prefix + '/Native/RewardedAdsFlow85.json', 'scope': report['scope']}


def validate_backend(e, report_path, inputs_path, prior):
    report_path, inputs_path = Path(report_path).resolve(), Path(inputs_path).resolve()
    require(report_path.is_relative_to(OUT) and inputs_path.is_relative_to(OUT), 'FreshBackendFollowupEvidenceLocationRequired')
    e.bind(report_path)
    report = read(report_path)
    require(report['status'] == 'PASS_BACKEND_SERVICE_TESTS' and report['tests'] == report['executedTests'] == 358
            and report['skipped'] == [] and report['actualPinnedWorkerIntegration'] is True
            and all(report[k] == [] for k in ('failures', 'errors', 'failureLocations', 'sourceInputsChangedDuringRun')),
            'Fresh358ActualBackendTestsRequired')
    require(when(report['startedUtc']) < when(report['utc']) and len(set(report['passed'])) == len(report['passed']) == 358
            and 'tests.test_replay_native_integration.NativeReplayBrokerIntegration.test_authenticated_native_full_history_continue_win_recovery' in report['passed'],
            'FreshBackendChronologyOrWorkerProofMissing')
    sources = report['sourceSHA256']
    require(len(sources) == 79 and sources == report['sourceSHA256After']
            and set(sources) == set(prior['sourceSHA256']), 'BackendFreshExactInputSetRequired')
    changed = diff(prior['sourceSHA256'], sources)
    require(BACKEND_TEST in changed and changed <= {BACKEND_TEST, 'Backend/README.md'}, 'BackendRuntimeConfigOrUnrelatedTestChanged')
    added = set(report['passed']) - set(prior['passed'])
    require(added == {NEW_BACKEND_TEST}, 'ExactlyOneNewAdsBackendRegressionRequired')
    require({p.relative_to(inputs_path).as_posix() for p in inputs_path.rglob('*') if p.is_file()} == set(sources),
            'FreshBackendInputArchiveIncomplete')
    documentation = []
    for name, digest in sources.items():
        require(name.startswith('Backend/'), 'BackendSourceOutsideScope')
        e.bind(inputs_path / name, digest)
        actual = sha(rooted(name))
        if actual != digest:
            require(name == 'Backend/README.md', 'PostTestBackendExecutableConfigOrTestsDrift')
            documentation.append({'path': name, 'testedSHA256': digest, 'currentSHA256': actual, 'scope': 'Documentation only'})
        e.bind(rooted(name))
    actual_set = set()
    for category in ('hotr_backend', 'tests', 'tools', 'config'):
        actual_set.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'Backend' / category).rglob('*')
                          if p.is_file() and p.suffix in ('.py', '.json'))
    actual_set.update('Backend/' + name for name in ('requirements.in', 'requirements.lock', 'README.md', 'Run-Local.ps1'))
    require(actual_set == set(sources), 'PostTestBackendExecutableOrConfigAdded')
    config = read(ROOT / 'Backend/config/ads.json')
    require(config['enabled'] is False and config['completionMode'] == 'sdk_client_reported_capped'
            and (config['rewardCoins'], config['dailyLimit'], config['utcOffsetSeconds'], config['cooldownSeconds']) == (400, 3, 36000, 600),
            'ApprovedPolicyOrDisabledRolloutChanged')
    return {'tests': 358, 'skipped': 0, 'actualPinnedWorkerIntegration': True, 'archivedInputCount': 79,
            'newRegression': sorted(added), 'changedTestInputs': sorted(changed),
            'report': relative_base(report_path), 'scope': report['scope'], 'documentationOnlyDrift': documentation}


def validate_static(e, profile_path, builds):
    profile_path = Path(profile_path).resolve()
    require(profile_path.is_relative_to(OUT / 'Android'), 'FreshStaticProfileMustBeSeparateFromHistorical85')
    e.bind(profile_path)
    value = read(profile_path)
    require(value['status'] == 'PASS_ADS85_SDK_FREE_INTERNAL_APKS_STATIC', 'FreshStaticProfileNotPassed')
    expected = {x['apk']['path']: x['apk'] for x in builds['variants']}
    require(len(value['artifacts']) == 2 and {x['path'] for x in value['artifacts']} == set(expected), 'FreshStaticVariantSetMismatch')
    for row in value['artifacts']:
        target = expected[row['path']]
        require(row['sha256'] == target['sha256'] and row['bytes'] == target['bytes']
                and row['package'] == 'com.heartoftherain.verification'
                and row['nativePaymentAndAdvertisingSdkAbsent'] is True and row['deviceIdentityClassPresent'] is True,
                'FreshStaticApkIdentityMismatch')
        artifact_path = (profile_path.parent / row['staticArtifactReport']).resolve()
        require(artifact_path.is_relative_to(profile_path.parent), 'StaticArtifactPathEscape')
        e.bind(artifact_path)
        artifact = read(artifact_path)
        require(artifact['sha256'] == row['sha256'] and artifact['bytes'] == row['bytes']
                and Path(artifact['path']).resolve() == rooted(row['path'])
                and all(artifact[k] is True for k in ('zipalign4KiBPass', 'developmentSignatureVerifies', 'elf16KiBLoadSegmentsPass')),
                'FreshStaticSignatureOrAlignmentProofInvalid')
        badging, manifest = artifact_path.parent / 'Badging.txt', artifact_path.parent / 'Manifest.txt'
        e.bind(badging); e.bind(manifest)
        b, m = badging.read_text('utf-8-sig'), manifest.read_text('utf-8-sig')
        require("package: name='com.heartoftherain.verification'" in b and "application-label:'Сердце дождя'" in b
                and not any(x in m for x in ('YandexAdsInitializeProvider', 'AppMetricaService', 'RuStorePayContentProvider', 'heartoftherain-pay')),
                'FreshStaticLabelOrSdkAbsenceFailed')
        with zipfile.ZipFile(OLD.disk(rooted(row['path']))) as archive:
            require(archive.testzip() is None, 'FreshInternalApkCrcFailed')
            dex = [archive.read(n) for n in archive.namelist() if re.fullmatch(r'classes[0-9]*\.dex', n)]
            require(dex and any(b'Lcom/heartoftherain/identity/DeviceIdentity82;' in body for body in dex)
                    and not any(prefix in body for body in dex for prefix in (b'Lcom/yandex/mobile/ads/', b'Lio/appmetrica/', b'Lru/rustore/sdk/')),
                    'FreshInternalApkDexShapeInvalid')
    return {'report': relative_base(profile_path), **value}


def historical_evidence(e, new_build_id, accepted, current):
    summary_path = BASE / 'Summary.json'
    anchors = {}
    for relative in ('Verification/Evidence/ShopAds85/Summary.json',
                     'Verification/Evidence/ShopAds85/Comparison.html',
                     'Verification/Evidence/ShopAds85/SDK/FullGameBuild/Report.json'):
        committed = git_blob(relative)
        e.bind(ROOT / relative, committed)
        anchors[relative] = committed
    original = e.read('Summary.json')
    require(original['status'] == OLD.STATUS and original['sourceSHA256'] == sha(FROZEN)
            and original['unityInputCount'] == 5349, 'Original85PublishedEvidenceMissing')
    # Preserve every local historical evidence file, including old static APK
    # reports. Their default output paths now identify newer artifacts; the old
    # actual APK bytes are checked in the build wrapper's immutable archive.
    for path, digest in original['artifactSHA256'].items():
        e.bind(e.path(path), digest)
    new_inv = e.read('Builds/' + new_build_id + '/Invocation.json')
    old_builds = original['internalBuilds']['variants']
    archives = new_inv['archivedPriorApks']
    archived_apks = []
    for row in old_builds:
        previous = row['apk']
        copy = archives[Path(previous['path']).name]
        require(copy['existed'] is True and copy['sha256'] == previous['sha256'] and copy['bytes'] == previous['bytes'],
                'Historical85ApkArchiveDoesNotMatchPublishedArtifact')
        p = rooted(copy['path'])
        require(p.is_relative_to((ROOT / '.verification-cache/Ads85/InternalBuilds').resolve()) and p.stat().st_size == copy['bytes'],
                'Historical85ApkArchiveScopeOrSizeInvalid')
        e.bind(p, copy['sha256']); archived_apks.append(copy)
    full = e.read('SDK/FullGameBuild/Report.json')
    require(full['status'] == 'PASS_STATIC_UNLAUNCHED_YANDEX85_FULL_GAME_WITH_RELEASE_GATES'
            and full['mainAcceptedFrozenManifestSHA256'] == sha(FROZEN)
            and full['mainSourceInputCount'] == 5349 and full['apkLaunched'] is False
            and full['sdkAdRequested'] is False and full['configurationProvisioned'] is False,
            'EarlierExactFullGameSdkProofMissing')
    for path, digest in full['artifactSHA256'].items():
        e.bind(e.path('SDK/FullGameBuild/' + path), digest)
    provider_digest = accepted[PROVIDER]['sha256']
    require(current[PROVIDER] == accepted[PROVIDER], 'ProviderChangedOutsideRepairScope')
    e.bind(ROOT / PROVIDER, provider_digest)
    audit = e.read('SDK/Provider_Privacy_Audit.json')
    require(audit['compiledProviderSHA256'] == audit['currentProviderSHA256'] == provider_digest, 'HistoricalSdkProviderBindingMismatch')
    clone = ROOT / '.verification-cache/Ads85/G85_0be1f085'
    archived_sources = {}
    for path in sorted(UNITY_CHANGES):
        expected = accepted[path]['sha256']
        require(git_blob(path) == expected, 'Baseline85GitSourceDoesNotMatchPublishedManifest')
        archived = clone / path.removeprefix('Unity/')
        e.bind(archived, expected)
        archived_sources[path] = {'baselineGitBlobSHA256': expected, 'archivedClonePath': archived.relative_to(ROOT).as_posix(),
                                  'currentSHA256': current[path]['sha256']}
    full_apk = rooted(full['apk']['path'])
    e.bind(full_apk, full['apk']['sha256'])
    require(full_apk.stat().st_size == full['apk']['bytes'], 'EarlierFullGameSdkApkChanged')
    return {'baseSummarySHA256': sha(summary_path), 'baseCommit': BASE_COMMIT,
            'immutableCommittedAnchors': anchors,
            'baseSourceSHA256': original['sourceSHA256'], 'archivedPriorInternalApks': archived_apks,
            'reusedBackendTests': 357, 'reusedNative': original['native'],
            'fullGameSdkReport': 'SDK/FullGameBuild/Report.json', 'fullGameSdkApk': full['apk'],
            'scope': 'Earlier exact source only: backend357, prior parser/journal/HTTP/UI captures and SDK fixture/full-game static proof are not rerun or relabelled as currentFlow tests. Provider bytes remain exact; the full-game SDK clone contains the four pre-repair source files.',
            'archivedChangedSources': archived_sources}


def build(native_run, build_run, static_profile, backend_report, backend_inputs):
    e = OLD.Evidence(BASE)
    e.bind(Path(__file__))
    e.bind(Path(__file__).with_name('collect_ads85.py'))
    owner_steps_sha = e.bind(ROOT / 'Release/Advertising/README.md')
    e.bind(ROOT / 'Backend/config/ads.json')
    e.bind(Path(__file__).with_name('check_reservation_recovery85_apks.py'))
    accepted = OLD.source_map(e.read(relative_base(FROZEN)))
    current = OLD.current_inputs()
    require(len(accepted) == len(current) == 5349 and diff(accepted, current) == UNITY_CHANGES,
            'ExactlyFourApprovedUnityInputChangesRequired')
    for name in sorted(UNITY_CHANGES):
        e.bind(ROOT / name, current[name]['sha256'])
    native = validate_flow(e, native_run, current)
    builds = OLD.internal_builds(e, build_run, current)
    native_inv = read(BASE / 'Runs' / native_run / 'Invocation.json')
    build_inv = read(BASE / 'Builds' / build_run / 'Invocation.json')
    require(when(native_inv['finishedUtc']) <= when(build_inv['startedUtc']), 'FinalFlowMustPrecedeBothBuilds')
    static = validate_static(e, static_profile, builds)
    prior_backend = e.read('Backend/Service_Tests.json')
    backend = validate_backend(e, backend_report, backend_inputs, prior_backend)
    prior = historical_evidence(e, build_run, accepted, current)
    require(OLD.current_inputs() == current, 'SourceChangedDuringFollowupCollection')
    return {'status': STATUS, 'utc': datetime.now(timezone.utc).isoformat(), 'source_checkpoint': 85,
            'followup': 'ReservationRecovery85', 'sourceSHA256': native['sourceSHA256'],
            'verificationInputs': {
                'nativeRun': native_run, 'buildRun': build_run,
                'staticProfile': Path(static_profile).resolve().relative_to(ROOT).as_posix(),
                'backendReport': Path(backend_report).resolve().relative_to(ROOT).as_posix(),
                'backendInputs': Path(backend_inputs).resolve().relative_to(ROOT).as_posix(),
            },
            'unityVersion': OLD.PINNED, 'unityInputCount': 5349,
            'scope': 'Targeted definitive first-send reservation-denial recovery repair. Fresh native scripted state/transport regressions, backend358 and SDK-free internal Android compile/static checks. No fresh UI, SDK-enabled full-game runtime, device, ad impression or production acceptance.',
            'sourceDeltaFromPublished85': sorted(UNITY_CHANGES),
            'backend': backend, 'native': native, 'internalBuilds': builds, 'internalApkStatic': static,
            'historicalEvidence': prior, 'artifactRoot': 'Verification/Evidence/ShopAds85',
            'artifactSHA256': e.local, 'externalEvidenceSHA256': e.external,
            'ownerSteps': 'Release/Advertising/README.md', 'ownerStepsSHA256': owner_steps_sha,
            'remainingGates': [
                'Only a narrowly typed definitive reserve denial on the fresh first send can release a reservation intent. Unknown, malformed, lost-response, reloaded and recovered histories must retain their exact idempotency intent.',
                'Earlier parser/journal/HTTP/UI and SDK proofs retain their original source scope. The full-game SDK clone predates these four changed files and is not a latestFlow SDK compile.',
                'Both fresh ordinary APKs remain SDK-free and uninstalled. No advertising SDK was initialized, loaded, shown or launched by this followup.',
                'The capped SDK-client completion mode is lower trust and not provider impression verification. Publisher IDs, public HTTPS/backend configuration, consent/privacy and rollout remain unprovisioned or disabled.',
                'Actual ads, lifecycle/device tests, production revenue, store payments, signing/legal/hosting and all existing release/performance gates remain open.'
            ]}


def verify_published():
    """Rebuild the exact accepted scope for the generic read-only dispatcher."""
    summary = OUT / 'Summary.json'
    published = read(summary)
    require(published['status'] == STATUS and published['followup'] == 'ReservationRecovery85',
            'PublishedReservationRepairIdentityMismatch')
    inputs = published['verificationInputs']
    require(set(inputs) == {'nativeRun', 'buildRun', 'staticProfile', 'backendReport', 'backendInputs'},
            'PublishedReservationRepairInputsMismatch')
    rebuilt = build(inputs['nativeRun'], inputs['buildRun'], rooted(inputs['staticProfile']),
                    rooted(inputs['backendReport']), rooted(inputs['backendInputs']))
    require({k: v for k, v in published.items() if k != 'utc'} == {k: v for k, v in rebuilt.items() if k != 'utc'},
            'PublishedReservationRepairNoLongerMatchesActualEvidence')
    require((OUT / 'Comparison.html').read_text('utf-8') == gallery(published),
            'PublishedReservationRepairGalleryMismatch')
    return published


def gallery(value):
    rows = ''.join('<tr><td>' + html.escape(x['name']) + '</td><td>' + str(x['checks']) + '</td><td>PASS</td></tr>'
                   for x in value['native']['rows'])
    gates = ''.join('<li>' + html.escape(x) + '</li>' for x in value['remainingGates'])
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reservation recovery85</title><style>body{font:16px system-ui;max-width:1000px;margin:auto;padding:24px;background:#102c40;color:#f4ecd9}a{color:#b9ddff}td,th{border:1px solid #577489;padding:8px}table{border-collapse:collapse}li{margin:12px 0}</style><h1>Rewarded-video reservation recovery</h1><p>Fresh first-send definitive denials release only the corresponding intent; uncertain/recovered requests retain their exact command. No provider impression or advertising revenue is claimed.</p><p>' + str(value['backend']['tests']) + ' backend tests; ' + str(value['native']['checks']) + ' native checks/' + str(value['native']['cases']) + ' cases; both SDK-free internal builds and static APK checks.</p><table><tr><th>Native case</th><th>Checks</th><th>Result</th></tr>' + rows + '</table><h2>Historical scopes</h2><p>The <a href="../Comparison.html">original85 review</a> and <a href="../SDK/FullGameBuild/Report.json">earlier full-game SDK compile/static proof</a> remain immutable. The SDK clone predates the four-file repair; it is not a latestFlow SDK compile.</p><h2>Remaining gates</h2><ul>' + gates + '</ul><p><a href="Summary.json">Bound followup summary</a></p></html>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-run', required=True)
    parser.add_argument('--build-run', required=True)
    parser.add_argument('--static-profile', type=Path, default=OUT / 'Android/APK_Profile.json')
    parser.add_argument('--backend-report', type=Path, default=OUT / 'Backend358/Service_Tests.json')
    parser.add_argument('--backend-inputs', type=Path, default=OUT / 'Backend358/Inputs')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    value = build(args.native_run, args.build_run, args.static_profile, args.backend_report, args.backend_inputs)
    if args.publish:
        require(not (OUT / 'Summary.json').exists() and not (OUT / 'Comparison.html').exists(), 'FollowupPublicationAlreadyExists')
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'Summary.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (OUT / 'Comparison.html').write_text(gallery(value), encoding='utf-8')
    print(json.dumps({k: value[k] for k in ('status', 'sourceSHA256', 'unityInputCount', 'sourceDeltaFromPublished85')}, indent=2))


if __name__ == '__main__':
    main()
