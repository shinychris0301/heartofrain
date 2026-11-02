"""Publish/verify checkpoint89 receipts; never run Unity, ADB or old verifiers.

Publication requires --backend Service_Tests.json, --native-list NativeRuns.json,
--builds RegionalAccounts89_Builds.json, --phone a current89 phone run directory,
and --visual a root-assessed VisualReview.json. An omitted/failed/pending receipt
cannot be promoted to acceptance. Failed attempts remain in artifact inventory.

NativeRuns: {schemaVersion:1, checkpoint:89, runs:[{name, invocation, report,
expectedStatus}]}; exactly Regional, Provider, AdsParser, AdsUi, AdsFlow and
DisplaySmoke. Paths are repository-relative strings inside current89 evidence.

VisualReview: {schemaVersion:1,status:'REVIEWED_REGIONAL_ACCOUNTS89_PHONE',
apkSHA256,sourceManifest:{path,sha256,bytes},scope,ordinaryDataUnchanged:true,
ordinaryDataUnchangedAfterRelaunch:true,noActiveAttempt:true,
ordinaryBefore:<snapshot path>,ordinaryAfter:<snapshot path>,
ordinaryAfterRelaunch:<snapshot path>,cases:[{name,captures:[PNG paths],
passed:true,scope}],warnings:[],limitations:[nonempty...]}. Five required cases:
CountryPicker, PlayerGlobalRegional, TeamGlobalRegional, ShopRewardNote,
VkUnavailable. Ranking phone cases explicitly concern offline/demo pages;
real filtering is checked separately in backend/native fixture evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/RegionalAccounts89'
TOOLS = ROOT / 'Verification/Tools/RegionalAccounts89'
STATUS = 'COMPLETED_REGIONAL_ACCOUNTS89_WITH_OPEN_GATES'
GENERATED = {'Summary.json', 'Current.json', 'ArtifactInventory.json', 'Comparison.html'}
HISTORICAL = ROOT / 'Verification/Evidence/Display88/Summary.json'
HISTORICAL_SHA = '29ae9cb7dd39f6fb5dde5af0988cb11e9e524cb16739e37172aa3945584e1cb5'
SUITES = {
    'Regional': ('Regional89Verification.Run', 'HOTR_REGION89_OUTPUT', 'PASS_NATIVE_REGIONAL89'),
    'Provider': ('ProviderIdentity89Verification.Run', 'HOTR_PROVIDER89_OUT', 'PASS_NATIVE_PROVIDER_IDENTITY89'),
    'AdsParser': ('RewardedAdsParser85Verification.Run', 'HOTR_REWARDED_ADS85_OUTPUT', 'PASS_NATIVE_REWARDED_ADS85_PARSER'),
    'AdsUi': ('RewardedAdsUi85Verification.Run', 'HOTR_REWARDED_ADS85_OUTPUT', 'PASS_NATIVE_REWARDED_ADS85_UI'),
    'AdsFlow': ('RewardedAdsFlow85Verification.Run', 'HOTR_ADS85_OUTPUT', 'PASS_NATIVE_REWARDED_ADS_FLOW85'),
    'DisplaySmoke': ('Display88Verification.Run', 'HOTR_DISPLAY88_OUT', 'PASS_NATIVE_DISPLAY88'),
}
PHONE_CASES = {'CountryPicker', 'PlayerGlobalRegional', 'TeamGlobalRegional', 'ShopRewardNote', 'VkUnavailable'}
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import PINNED_UNITY, freeze


def need(value, code):
    if not value:
        raise RuntimeError(code)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def bound(value, *, inside=None):
    path = Path(value)
    need('..' not in path.parts, 'ParentTraversalRefused')
    path = (ROOT / path).resolve()
    need(path.is_relative_to((inside or ROOT).resolve()), 'EvidencePathOutsideScope')
    return path


def _unique(pairs):
    value = {}
    for key, child in pairs:
        need(key not in value, 'DuplicateJsonKey')
        value[key] = child
    return value


def read(path):
    path = Path(path)
    need(path.is_file() and path.stat().st_size <= 40 * 1024 * 1024, 'MissingOrOversizedJsonReport')
    return json.loads(path.read_text('utf-8-sig'), object_pairs_hook=_unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NonfiniteJson')))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def binding(path):
    path = bound(path)
    need(path.is_file(), 'BoundFileMissing')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def check_binding(value, *, inside=None):
    need(isinstance(value, dict) and set(value) == {'path', 'sha256', 'bytes'}, 'InvalidArtifactBinding')
    path = bound(value['path'], inside=inside)
    need(path.is_file() and path.stat().st_size == value['bytes'] and sha(path) == value['sha256'], 'BoundArtifactChanged:' + value['path'])
    return path


def current_manifest(path, current):
    value = read(path)
    need(value.get('schemaVersion') == current['schemaVersion'] and value.get('inputCount') == current['inputCount']
         and value.get('files') == current['files'], 'CurrentUnitySourceMapMismatch')


def source_tools():
    files = list(TOOLS.glob('*.py')) + [ROOT / 'Verification/Tools/collect_results.py']
    return {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(files)}


def backend_sources():
    base = ROOT / 'Backend'
    paths = [path for folder in ('hotr_backend', 'tests', 'tools', 'config') for path in (base / folder).rglob('*')
             if path.is_file() and path.suffix in ('.py', '.json')]
    paths += [base / name for name in ('requirements.in', 'requirements.lock', 'README.md', 'Run-Local.ps1')]
    return {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(paths)}


def backend_proof(path):
    path = bound(path, inside=OUT)
    report = read(path)
    invocation_path = path.parent / 'Invocation.json'
    invocation = read(invocation_path)
    need(report.get('status') == 'PASS_BACKEND_SERVICE_TESTS' and not report.get('failures') and not report.get('errors')
         and report.get('skipped') == [] and report.get('actualPinnedWorkerIntegration') is True
         and report.get('sourceInputsChangedDuringRun') == [], 'BackendFullSuiteNotPassed')
    need(type(report.get('tests')) is int and report['tests'] > 0 and report.get('executedTests') == report['tests']
         and len(report.get('passed', [])) == report['tests'] and len(set(report['passed'])) == report['tests']
         and any('test_replay_native_integration.' in name for name in report['passed']), 'BackendCoverageReceiptInvalid')
    need(invocation.get('status') == 'PASS_BACKEND89_FULL_SUITE' and invocation.get('exitCode') == 0
         and invocation.get('executedTests') == report['executedTests'] and invocation.get('archiveSourceChanges') == []
         and invocation.get('serviceReportSHA256') == sha(path)
         and invocation.get('consoleSHA256') == sha(path.parent / 'Console.log')
         and invocation.get('runnerSHA256') == sha(TOOLS / 'run_backend.py'), 'BackendInvocationNotPassedOrChanged')
    current = backend_sources()
    need(report.get('sourceSHA256') == report.get('sourceSHA256After') == current, 'BackendCurrentSourceMismatch')
    for relative, digest in current.items():
        archived = bound(path.parent / 'Inputs' / relative, inside=path.parent / 'Inputs')
        need(sha(archived) == digest, 'BackendArchivedInputChanged:' + relative)
    approval = ROOT / 'Verification/Evidence/ServerGameplay83/Backend/Verified324/Local_Approval.json'
    need(invocation.get('approvalSHA256') == sha(approval), 'ApprovedWorkerReceiptChanged')
    return {'invocation': binding(invocation_path), 'report': binding(path), 'tests': report['tests'],
            'actualPinnedWorkerIntegration': True, 'skipped': [], 'scope': report.get('scope', '')}


def png_dimensions(path):
    """Independently require intact CRC/IEND and a decodable original PNG."""
    path = Path(path)
    need(path.stat().st_size <= 24 * 1024 * 1024, 'PngTooLarge')
    raw = path.read_bytes()
    need(raw[:8] == b'\x89PNG\r\n\x1a\n', 'NotPng')
    cursor, dimensions, ended = 8, None, False
    while cursor < len(raw):
        need(cursor + 12 <= len(raw), 'TruncatedPngChunk')
        length = struct.unpack('>I', raw[cursor:cursor + 4])[0]
        kind = raw[cursor + 4:cursor + 8]
        finish = cursor + 12 + length
        need(finish <= len(raw), 'TruncatedPngBody')
        payload = raw[cursor + 8:cursor + 8 + length]
        checksum = struct.unpack('>I', raw[cursor + 8 + length:finish])[0]
        need(zlib.crc32(kind + payload) & 0xffffffff == checksum, 'PngCrcMismatch')
        if cursor == 8:
            need(kind == b'IHDR' and length == 13, 'MissingPngIhdr')
            dimensions = struct.unpack('>II', payload[:8])
            need(0 < dimensions[0] <= 8192 and 0 < dimensions[1] <= 8192, 'PngDimensionsInvalid')
        cursor = finish
        if kind == b'IEND':
            need(length == 0 and cursor == len(raw), 'TrailingOrMalformedPng')
            ended = True
            break
    need(ended and dimensions, 'IncompletePngIend')
    from PIL import Image
    with Image.open(path) as decoded:
        need(decoded.format == 'PNG' and decoded.size == dimensions, 'PngDecodedDimensionsMismatch')
        decoded.verify()
    return dimensions


def native_proof(list_path, current):
    list_path = bound(list_path, inside=OUT)
    listing = read(list_path)
    need(listing.get('schemaVersion') == 1 and listing.get('checkpoint') == 89, 'NativeListScopeInvalid')
    rows = listing.get('runs', [])
    need(len(rows) == len(SUITES) and {row.get('name') for row in rows} == set(SUITES), 'SixNativeSuitesRequired')
    result = []
    for row in rows:
        name = row['name']
        method, environment, expected = SUITES[name]
        need(row.get('expectedStatus') == expected, 'NativeExpectedStatusChanged:' + name)
        invocation_path = bound(row['invocation'], inside=OUT)
        report_path = bound(row['report'], inside=invocation_path.parent)
        invocation, report = read(invocation_path), read(report_path)
        need(invocation.get('status') == 'PASS_NATIVE_REGIONAL89_INVOCATION' and invocation.get('exitCode') == 0
             and not invocation.get('timedOut') and invocation.get('inputsUnchanged') is True
             and invocation.get('unityPidsAfter') == [] and invocation.get('entry') == 'HeartOfTheRain.Verification.' + method
             and invocation.get('outputEnvironmentVariable') == environment, 'NativeInvocationNotPassed:' + name)
        need(report.get('status') == invocation.get('nativeStatus') == expected and report.get('unity') == '2022.3.62f3'
             and type(report.get('checks')) is int and report['checks'] > 0
             and not report.get('failures') and not report.get('errors') and not report.get('error'), 'NativeReportNotPassed:' + name)
        need(invocation.get('nativeReportSHA256') == sha(report_path) and invocation.get('checks') == report['checks'], 'NativeReportBindingChanged:' + name)
        before = invocation_path.parent / 'FrozenSources.json'
        need(invocation.get('sourceSHA256') == sha(before) and invocation.get('inputCount') == current['inputCount'], 'NativeSourceBindingChanged:' + name)
        current_manifest(before, current)
        current_manifest(invocation_path.parent / 'Sources_after.json', current)
        need(not any(read(invocation_path.parent / 'Source_Delta.json').values()), 'NativeSourceDeltaNotEmpty:' + name)
        for key, artifact in [('runnerSHA256', TOOLS / 'run_native.py'),
                              ('unityExeSHA256', PINNED_UNITY),
                              ('hashProcessHelperSHA256', ROOT / 'Verification/Tools/Ads85/run_ads85_native.py'),
                              ('processSelectorSHA256', ROOT / 'Verification/Tools/Review86/run_native86.py'),
                              ('unityLogSHA256', invocation_path.parent / 'Unity.log'),
                              ('consoleSHA256', invocation_path.parent / 'Console.log')]:
            need(invocation.get(key) == sha(artifact), 'NativeHelperOrLogChanged:' + name + ':' + key)
        captures = []
        for capture in report.get('captures', []):
            relative = capture if isinstance(capture, str) else capture['file']
            path = bound(invocation_path.parent / relative, inside=invocation_path.parent)
            need(path.suffix.lower() == '.png', 'NativeCaptureNotPng')
            png_dimensions(path)
            captures.append(binding(path))
        result.append({'name': name, 'invocation': binding(invocation_path), 'report': binding(report_path),
                       'checks': report['checks'], 'captures': captures, 'scope': report.get('scope', '')})
    result.sort(key=lambda row: row['name'])
    return {'list': binding(list_path), 'runs': result, 'totalChecks': sum(row['checks'] for row in result)}


def build_proof(wrapper, current):
    wrapper = bound(wrapper, inside=OUT)
    value = read(wrapper)
    need(value.get('status') == 'PASS_INTERNAL_ANDROID_BUILDS89', 'BuildWrapperNotPassed')
    invocation = bound(value['invocation'], inside=OUT)
    need(value.get('invocationSHA256') == sha(invocation), 'BuildInvocationBindingMismatch')
    report = read(invocation)
    need(report.get('status') == 'PASS_SDK_FREE_INTERNAL_ANDROID_BUILDS85' and report.get('allHistoricalNativeRestored') is True
         and report.get('inputsUnchangedAfterSettingsRestore') is True and report.get('unityPidsAfter') == [], 'InternalBuildsNotPassed')
    frozen = invocation.parent / 'FrozenSources.json'
    need(report.get('sourceSHA256') == sha(frozen) and report.get('inputCount') == current['inputCount'], 'BuildSourceBindingMismatch')
    current_manifest(frozen, current)
    current_manifest(invocation.parent / 'Sources_final.json', current)
    need(report.get('sourcesFinalSHA256') == sha(invocation.parent / 'Sources_final.json'), 'BuildFinalSourceReceiptChanged')
    for key, path in [('wrapperSHA256', TOOLS / 'run_builds.py'),
                      ('buildHelperSHA256', ROOT / 'Verification/Tools/Ads85/run_ads85_internal_build.py'),
                      ('processSelectorSHA256', ROOT / 'Verification/Tools/Review86/run_native86.py')]:
        need(value.get(key) == sha(path), 'BuildHelperChanged')
    need(report.get('runnerSHA256') == sha(ROOT / 'Verification/Tools/Ads85/run_ads85_internal_build.py')
         and report.get('sharedNativeRunnerSHA256') == sha(ROOT / 'Verification/Tools/Ads85/run_ads85_native.py')
         and report.get('unityExeSHA256') == sha(PINNED_UNITY), 'BuildUnderlyingHelperChanged')
    rows = report.get('runs', [])
    need(len(rows) == 2 and {row['build'] for row in rows} == {'Development', 'NonDevelopment'}, 'BothInternalBuildsRequired')
    apks = []
    for row in rows:
        need(row.get('status') == 'PASS_INTERNAL_BUILD85' and row.get('exitCode') == 0 and not row.get('timedOut')
             and row.get('processStopped') is True and row.get('exactSettingsRestored') is True
             and row.get('inputsUnchangedAfterRestoration') is True and row.get('ownedKillOnCloseJobAssigned') is True, 'InternalBuildProcessNotPassed')
        folder = invocation.parent / row['build']
        need(read(folder / 'Process.json') == row, 'BuildProcessRecordMismatch')
        current_manifest(folder / 'Sources_before.json', current)
        current_manifest(folder / 'Sources_after_restore.json', current)
        need(not any(read(folder / 'Source_Delta.json').values()), 'BuildSourceDeltaNotEmpty')
        need(row.get('sourcesAfterSHA256') == sha(folder / 'Sources_after_restore.json'), 'BuildAfterSourceReceiptChanged')
        filename = 'Android_Build.json' if row['build'] == 'Development' else 'Android_Release_Build.json'
        expected = 'PASS_ANDROID_DEVELOPMENT_BUILD' if row['build'] == 'Development' else 'PASS_ANDROID_RELEASE_COMPILE_BUILD'
        native = read(folder / filename)
        need(row.get('nativeReportSHA256') == sha(folder / filename) and native.get('status') == row.get('nativeStatus') == expected
             and native.get('unity') == '2022.3.62f3' and not native.get('errors') and not native.get('error'), 'NativeAndroidBuildNotPassed')
        check_binding(row['apk'], inside=ROOT / 'Unity/Builds/Verification')
        need(row.get('unityLogSHA256') == sha(folder / 'Unity.log') and row.get('consoleSHA256') == sha(folder / 'Console.log'), 'BuildLogsChanged')
        apks.append(dict(row['apk'], development=row['build'] == 'Development'))
    apks.sort(key=lambda row: not row['development'])
    return {'wrapper': binding(wrapper), 'invocation': binding(invocation)}, apks


def historical_reference():
    need(sha(HISTORICAL) == HISTORICAL_SHA, 'Historical88SummaryChanged')
    value = read(HISTORICAL)
    need(value.get('checkpoint') == 88 and value.get('releaseApproved') is False
         and value.get('allChecklistRowsPassed') is False and value.get('wholeGameSmoothnessCertified') is False,
         'Historical88ScopeChanged')
    # Validate only the old immutable receipts, never old source maps against
    # current code or old APK output paths after a replacement build.
    check_binding(value['physical']['target'], inside=ROOT / 'Verification/Evidence/Display88')
    check_binding(value['physical']['installation'], inside=ROOT / 'Verification/Evidence/Display88')
    return {'summary': binding(HISTORICAL), 'status': value['status'],
            'scope': 'Immutable checkpoint88 reference only. Its historical failures and source scope are retained; no old current-tree verifier is called.'}, value


def _snapshot(value, apk):
    need(value.get('activeAttempts') == 0 and value.get('installedSHA256') == apk
         and isinstance(value.get('profiles'), dict) and value['profiles']
         and isinstance(value.get('preferences'), dict) and value['preferences'], 'PhoneSnapshotScopeInvalid')
    for field in ('profiles', 'preferences'):
        for relative, digest in value[field].items():
            need(not Path(relative).is_absolute() and '..' not in Path(relative).parts
                 and re.fullmatch('[0-9a-f]{64}', digest), 'PhoneSnapshotHashInvalid')
    for row in value.get('profileSummaries', []):
        need(row.get('activeAttempts') == 0, 'PhoneActiveAttemptPresent')
    return value['profiles'], value['preferences'], value.get('profileSummaries', [])


def physical_proof(phone, visual_path, apks, current, history):
    phone = bound(phone, inside=OUT)
    visual_path = bound(visual_path, inside=phone)
    development = next(row for row in apks if row['development'])
    target_path, install_path = phone / 'Target.json', phone / 'Installation.json'
    target, installed = read(target_path), read(install_path)
    old_target_path = check_binding(history['physical']['target'], inside=ROOT / 'Verification/Evidence/Display88')
    old_target = read(old_target_path)
    old_installation = check_binding(history['physical']['installation'], inside=ROOT / 'Verification/Evidence/Display88')
    old_apk = next(row for row in history['apks'] if row['development'])
    need(target.get('authorization') == 'OWNER_REQUESTED_REGIONAL_ACCOUNTS89'
         and target.get('package') == old_target.get('package') == 'com.heartoftherain.verification'
         and target.get('serialSHA256') == old_target.get('serialSHA256')
         and re.fullmatch('[0-9a-f]{64}', target.get('serialSHA256', ''))
         and target.get('model') == old_target.get('model'), 'ExplicitSameOwnerPhysicalTargetMissing')
    need(check_binding(target['priorTarget']) == old_target_path and check_binding(target['priorInstallation']) == old_installation,
         'Immutable88AncestryNotEstablished')
    need(target.get('baselineInstalledSHA256') == old_apk['sha256']
         and target.get('candidateApk') == development['path'] and target.get('candidateApkSHA256') == development['sha256'], 'PhoneCandidateNotCurrentBuild')
    need(installed.get('status') == 'PASS_SAVE_PRESERVING_REPLACEMENT', 'SavePreservingInstallNotPassed')
    before_path = phone / 'Install_Before.json'
    before, after = read(before_path), installed['after']
    need(_snapshot(before, old_apk['sha256']) == _snapshot(after, development['sha256']), 'InstallationChangedOrdinaryData')
    visual = read(visual_path)
    need(visual.get('schemaVersion') == 1 and visual.get('status') == 'REVIEWED_REGIONAL_ACCOUNTS89_PHONE'
         and visual.get('apkSHA256') == development['sha256'] and bool(visual.get('scope'))
         and visual.get('ordinaryDataUnchanged') is True and visual.get('ordinaryDataUnchangedAfterRelaunch') is True
         and visual.get('noActiveAttempt') is True and isinstance(visual.get('warnings'), list)
         and isinstance(visual.get('limitations'), list) and visual['limitations'], 'ExplicitPhoneVisualAssessmentMissing')
    current_manifest(check_binding(visual['sourceManifest'], inside=OUT), current)
    snapshots = []
    baseline = None
    for field in ('ordinaryBefore', 'ordinaryAfter', 'ordinaryAfterRelaunch'):
        path = bound(visual[field], inside=phone)
        data = _snapshot(read(path), development['sha256'])
        need(data == _snapshot(after, development['sha256']), 'ReviewChangedInstalledOwnerData')
        if baseline is None:
            baseline = data
        need(data == baseline, 'PhoneReviewOrdinaryDataChanged')
        snapshots.append(binding(path))
    cases = visual.get('cases', [])
    need(len(cases) == len(PHONE_CASES) and {row.get('name') for row in cases} == PHONE_CASES, 'FiveAssessedPhoneCasesRequired')
    captures, reviewed = {}, []
    for case in cases:
        need(case.get('passed') is True and bool(case.get('scope')) and case.get('captures'), 'PhoneVisualCaseNotPassed')
        if case['name'] in ('PlayerGlobalRegional', 'TeamGlobalRegional'):
            need(any(word in case['scope'].lower() for word in ('offline', 'demo')), 'OfflineRankingPhoneScopeMustBeExplicit')
        images = []
        for relative in case['captures']:
            path = bound(relative, inside=phone)
            need(path.suffix.lower() == '.png', 'PhoneCaptureNotPng')
            metadata_path = path.with_suffix('.json')
            metadata = read(metadata_path)
            dimensions = png_dimensions(path)
            need(metadata.get('kind') == 'ACTUAL_ANDROID_OS_FRAMEBUFFER'
                 and metadata.get('pngValidation') == 'COMPLETE_CHUNKS_IEND_CRC_AND_DECODE'
                 and metadata.get('installedSHA256') == development['sha256']
                 and metadata.get('sha256') == sha(path) and bound(phone / metadata['png'], inside=phone) == path
                 and dimensions == (metadata.get('width'), metadata.get('height')) and dimensions[1] > dimensions[0], 'PhoneFramebufferReceiptInvalid')
            captures[path.relative_to(ROOT).as_posix()] = {'image': binding(path), 'metadata': binding(metadata_path)}
            images.append(binding(path))
        reviewed.append({'name': case['name'], 'captures': images, 'scope': case['scope'], 'passed': True})
    reviewed.sort(key=lambda row: row['name'])
    return {'target': binding(target_path), 'installation': binding(install_path), 'installBefore': binding(before_path),
            'visualAssessment': binding(visual_path), 'sourceManifest': visual['sourceManifest'], 'ordinarySnapshots': snapshots,
            'cases': reviewed, 'captures': [captures[key] for key in sorted(captures)], 'ordinaryDataPreserved': True,
            'actualLiveVkTested': False, 'configuredOnlineRankingsTestedOnPhone': False,
            'scope': visual['scope'], 'warnings': visual['warnings'], 'limitations': visual['limitations']}


def public_fields(value):
    private = {'serial', 'password', 'token', 'accesstoken', 'refreshtoken', 'recoverycode', 'apikey', 'privatekey', 'secret'}
    if isinstance(value, dict):
        for key, child in value.items():
            need(str(key).replace('_', '').replace('-', '').lower() not in private or not child, 'PrivateFieldInPublicEvidence')
            public_fields(child)
    elif isinstance(value, list):
        for child in value:
            public_fields(child)


def inventory():
    files = {}
    for path in sorted(OUT.rglob('*')):
        if not path.is_file() or path.parent == OUT and path.name in GENERATED:
            continue
        need(not path.is_symlink() and path.resolve().is_relative_to(OUT.resolve()), 'EvidenceSymlinkOutsideScope')
        if path.suffix.lower() == '.json':
            public_fields(read(path))
        if path.suffix.lower() in ('.json', '.log', '.txt'):
            text = path.read_text('utf-8-sig', errors='replace')
            need(not re.search(r'Bearer\s+[A-Za-z0-9_./+=-]{32,}|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', text), 'SecretValueInPublicEvidence')
        files[path.relative_to(ROOT).as_posix()] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    need(0 < len(files) < 30000, 'EvidenceInventoryCountInvalid')
    return {'schemaVersion': 1, 'checkpoint': 89, 'files': files}


def verify(summary=None):
    summary = read(OUT / 'Summary.json') if summary is None else summary
    need(summary.get('schemaVersion') == 1 and summary.get('checkpoint') == summary.get('source_checkpoint') == 89
         and summary.get('status') == STATUS and summary.get('currentApkInstalled') is True, 'Current89ScopeInvalid')
    for key in ('releaseApproved', 'allChecklistRowsPassed', 'wholeGameSmoothnessCertified', 'productionReady',
                'actualVkProviderVerified', 'googleSignInImplemented', 'publicBackendDeployed', 'realAdsVerified'):
        need(summary.get(key) is False, 'UnsupportedProductionClaim:' + key)
    current = freeze()
    current_manifest(check_binding(summary['sourceManifest'], inside=OUT), current)
    need(summary.get('sourceSHA256') == summary['sourceManifest']['sha256'] and summary.get('unityInputCount') == current['inputCount'], 'PublishedCurrentSourceMismatch')
    need(summary.get('toolSHA256') == source_tools(), 'Current89CollectorOrHelperChanged')
    history, historical = historical_reference()
    need(summary.get('historicalReference') == history, 'HistoricalReferenceChanged')
    need(summary.get('backend') == backend_proof(summary['backend']['report']['path']), 'PublishedBackendProofChanged')
    need(summary.get('native') == native_proof(summary['native']['list']['path'], current), 'PublishedNativeProofChanged')
    builds, apks = build_proof(summary['builds']['wrapper']['path'], current)
    need(summary.get('builds') == builds and summary.get('apks') == apks, 'PublishedBuildProofChanged')
    need(summary.get('physical') == physical_proof(bound(summary['physical']['target']['path']).parent,
         summary['physical']['visualAssessment']['path'], apks, current, historical), 'PublishedPhysicalProofChanged')
    need(read(check_binding(summary['artifactManifest'], inside=OUT)) == inventory(), 'Current89ArtifactInventoryChanged')
    return summary


def publish(args):
    current = freeze()
    backend = backend_proof(args.backend)
    native = native_proof(args.native_list, current)
    builds, apks = build_proof(args.builds, current)
    historical, history = historical_reference()
    physical = physical_proof(args.phone, args.visual, apks, current, history)
    write(OUT / 'Sources.json', current)
    write(OUT / 'ArtifactInventory.json', inventory())
    summary = {'schemaVersion': 1, 'checkpoint': 89, 'source_checkpoint': 89, 'utc': datetime.now(timezone.utc).isoformat(),
               'status': STATUS, 'sourceManifest': binding(OUT / 'Sources.json'), 'sourceSHA256': sha(OUT / 'Sources.json'),
               'unityInputCount': current['inputCount'], 'artifactManifest': binding(OUT / 'ArtifactInventory.json'),
               'toolSHA256': source_tools(), 'backend': backend, 'native': native, 'builds': builds, 'apks': apks,
               'physical': physical, 'historicalReference': historical, 'currentApkInstalled': True,
               'releaseApproved': False, 'allChecklistRowsPassed': False, 'wholeGameSmoothnessCertified': False,
               'productionReady': False, 'actualVkProviderVerified': False, 'googleSignInImplemented': False,
               'publicBackendDeployed': False, 'realAdsVerified': False,
               'scope': 'Targeted country-scoped standings, conditional secure VK signup/link and local-day rewarded-ad engineering. Exact backend/current native/internal-build evidence and five scoped physical offline/demo UI observations; no real VK/Google authentication, configured online phone rankings, hosted operations, live ad/payment, performance or store approval.'}
    verify(summary)
    write(OUT / 'Summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    for name in ('backend', 'native-list', 'builds', 'phone', 'visual'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    if args.publish and not all(getattr(args, name) for name in ('backend', 'native_list', 'builds', 'phone', 'visual')):
        parser.error('Publishing requires all completed backend/native/build/phone/root-visual proofs')
    result = publish(args) if args.publish else verify()
    print(json.dumps({'status': result['status'], 'summary': 'Verification/Evidence/RegionalAccounts89/Summary.json',
                      'sourceSHA256': result['sourceSHA256'], 'tests': result['backend']['tests'], 'nativeChecks': result['native']['totalChecks']}))


if __name__ == '__main__':
    main()
