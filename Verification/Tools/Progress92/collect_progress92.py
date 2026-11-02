"""Publish/verify targeted progress92 proofs; never run Unity, ADB or old verifiers.

Requires native-list (Progress/DisplaySmoke), both internal builds/static checks,
the same-owner phone run and explicit root VisualReview. Root phone case names:
RainCup, Wellworks, Profile, Teams, Home. Cases require passed/progressReviewed/
controlsSafe true, original PNGs and honest scope. beforeReferences must include
RainCup, with image/metadata bindings, reviewed true and scope. Before images may
reuse immutable90 accepted frames without copying as historical context. Matched
RainCup/Profile before frames must come from the owner-preserved Baseline90 run.
Profile/preferences
and progress must match through replacement, walkthrough and normal relaunch.
Native-only model/demo fixtures do not become provider or device acceptance.
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
OUT = ROOT / 'Verification/Evidence/Progress92'
TOOLS = ROOT / 'Verification/Tools/Progress92'
STATUS = 'COMPLETED_PROGRESS92_WITH_OPEN_GATES'
GENERATED = {'Summary.json', 'Current.json', 'ArtifactInventory.json', 'Comparison.html'}
HISTORICAL = ROOT / 'Verification/Evidence/PageBackdrop90/Summary.json'
HISTORICAL_SHA = '10352d3592c35d51f29d031ca6b70107140d54e5078db94065788f4dbd796557'
SUITES = {
    'Progress': ('Progress92Verification.Run', 'HOTR_PROGRESS92_OUT', 'PASS_NATIVE_PROGRESS92'),
    'DisplaySmoke': ('Display88Verification.Run', 'HOTR_DISPLAY88_OUT', 'PASS_NATIVE_DISPLAY88'),
}
PHONE_CASES = {'RainCup', 'Wellworks', 'Home', 'Profile', 'Teams'}
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import PINNED_UNITY, freeze
if __package__:
    from .phone import validate_upgrade_chain
else:
    from phone import validate_upgrade_chain


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
    shared = ('collect_results.py', 'check_apk.py', 'Ads85/run_ads85_native.py',
              'Ads85/run_ads85_internal_build.py', 'PageBackdrop90/process90.py')
    files = set(TOOLS.glob('*.py')) | {ROOT / 'Verification/Tools' / name for name in shared}
    return {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(files)}


def backend_sources():
    base = ROOT / 'Backend'
    paths = [path for folder in ('hotr_backend', 'tests', 'tools', 'config') for path in (base / folder).rglob('*')
             if path.is_file() and path.suffix in ('.py', '.json')]
    paths += [base / name for name in ('requirements.in', 'requirements.lock', 'README.md', 'Run-Local.ps1')]
    return {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(paths)}



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


def progress_scope(report):
    bars = report.get('bars', [])
    need(isinstance(bars, list) and bars, 'NativeProgressRowsMissing')
    families = {'RainCup', 'Wellworks', 'ProfileStats', 'TeamRally', 'TeamLife', 'Home'}
    need(families.issubset({row.get('family') for row in bars}), 'NativeAffectedProgressFamilyMissing')
    need(len(bars) == report.get('cases') == 120, 'NativeProgressMatrixIncomplete')
    need(report.get('ordinaryServicesConstructed') is False and report.get('ordinaryProfileWrites') is False,
         'NativeOrdinaryStateIsolationMissing')
    sizes = {(320, 568), (393, 852), (720, 1600), (768, 1024)}
    for family in families:
        rows = [row for row in bars if row.get('family') == family]
        need(all(row.get('passed') is True for row in rows), 'NativeProgressFamilyNotPassed:' + family)
        need(len(rows) == 20 and {(row.get('width'), row.get('height')) for row in rows} == sizes,
             'NativeProgressScreenMatrixIncomplete:' + family)
        for width, height in sizes:
            group = [row for row in rows if (row['width'], row['height']) == (width, height)]
            ratios = sorted(row.get('ratio', -1) for row in group)
            need(len(ratios) == 5 and ratios[0] == 0 and .015 <= ratios[1] <= .03
                 and abs(ratios[2] - .1) < .0001 and abs(ratios[3] - .5) < .0001
                 and ratios[4] == 1, 'NativeProgressRatioMatrixIncomplete:' + family)
        need(all(row.get('type') == 'Sliced' and row.get('preserveAspect') is False
                 and row.get('fillHeight', 0) > 0 and row.get('sliceMultiplier', 0) > 0
                 and (row.get('ratio') != 0 or row.get('zeroHidden') is True) for row in rows),
             'NativeProgressShapeContractMissing:' + family)
    need(any(0 < row.get('ratio', 0) < 1 and row.get('fillHeight', 0) > 0 for row in bars if row.get('family') == 'RainCup'), 'NativePartialRainCupCoverageMissing')
    need(type(report.get('oldRainPixelHeight')) is int and type(report.get('newRainPixelHeight')) is int
         and report['oldRainPixelHeight'] >= 0 and report['newRainPixelHeight'] >= report['oldRainPixelHeight'] + 2
         and type(report.get('oldProfilePixelCount')) is int and type(report.get('newProfilePixelCount')) is int
         and report['oldProfilePixelCount'] >= 0 and report['newProfilePixelCount'] > report['oldProfilePixelCount'],
         'NativeNegativeControlsNotEstablished')
    captures = {'RainCup_OneOfTen_Native.png', 'RainCup_Fixed_OneOfTen_Bar.png',
                'RainCup_Old_Aspect_Bar_NegativeControl.png', 'Profile_OneOfFifty_Fixed_Bar.png'}
    need(set(report.get('captures', [])) == captures and len(report['captures']) == 4, 'NativeSelectedProgressCapturesMissing')
    audits = report.get('audits', [])
    need(all(any(row.get('family') == family and row.get('kind') == 'actual-production-ugui-mesh-and-gpu'
                 and row.get('status') == 'PASS' and row.get('scope') for row in audits) for family in families),
         'NativeActualProgressAuditsMissing')
    for family, kind, status in (('Launch', 'source-invariant-only', 'REVIEWED_UNCHANGED'),
                                 ('LevelComplete', 'legacy-source-review-only', 'NOT_ACTIVE_WIN_ROUTE'),
                                 ('OnlineTeams', 'source-inventory-only', 'NO_SHARED_PROGRESS_BAR')):
        need(any(row.get('family') == family and row.get('kind') == kind and row.get('status') == status
                 and row.get('scope') for row in audits), 'NativeSourceOnlyAuditScopeMissing:' + family)
    return {'families': sorted(families), 'cases': len(bars), 'screenSizes': [list(size) for size in sorted(sizes)],
            'oldRainPixelHeight': report['oldRainPixelHeight'], 'newRainPixelHeight': report['newRainPixelHeight'],
            'oldProfilePixelCount': report['oldProfilePixelCount'], 'newProfilePixelCount': report['newProfilePixelCount'],
            'scope': 'Native six-family production renderer matrix; old-aspect/old-Filled controls. Launch/legacy/connected inventory stays source-only.'}


def native_proof(list_path, current):
    list_path = bound(list_path, inside=OUT)
    listing = read(list_path)
    need(listing.get('schemaVersion') == 1 and listing.get('checkpoint') == 92 and listing.get('status') == 'PASS_NATIVE92_SET', 'NativeListScopeInvalid')
    rows = listing.get('runs', [])
    need(len(rows) == len(SUITES) and {row.get('name') for row in rows} == set(SUITES), 'TwoNativeSuitesRequired')
    result = []
    for row in rows:
        name = row['name']
        method, environment, expected = SUITES[name]
        need(row.get('expectedStatus') == expected, 'NativeExpectedStatusChanged:' + name)
        invocation_path = bound(row['invocation'], inside=OUT)
        report_path = bound(row['report'], inside=invocation_path.parent)
        invocation, report = read(invocation_path), read(report_path)
        need(invocation.get('status') == 'PASS_NATIVE_PROGRESS92_INVOCATION' and invocation.get('exitCode') == 0
             and not invocation.get('timedOut') and invocation.get('inputsUnchanged') is True
             and invocation.get('unityPidsAfter') == [] and invocation.get('entry') == 'HeartOfTheRain.Verification.' + method
             and invocation.get('outputEnvironmentVariable') == environment, 'NativeInvocationNotPassed:' + name)
        need(report.get('status') == invocation.get('nativeStatus') == expected and report.get('unity') == '2022.3.62f3'
             and type(report.get('checks')) is int and report['checks'] > 0
             and not report.get('failures') and not report.get('errors') and not report.get('error'), 'NativeReportNotPassed:' + name)
        need(invocation.get('nativeReportSHA256') == sha(report_path) and invocation.get('checks') == report['checks'], 'NativeReportBindingChanged:' + name)
        progress = progress_scope(report) if name == 'Progress' else None
        before = invocation_path.parent / 'FrozenSources.json'
        need(invocation.get('sourceSHA256') == sha(before) and invocation.get('inputCount') == current['inputCount'], 'NativeSourceBindingChanged:' + name)
        current_manifest(before, current)
        current_manifest(invocation_path.parent / 'Sources_after.json', current)
        need(not any(read(invocation_path.parent / 'Source_Delta.json').values()), 'NativeSourceDeltaNotEmpty:' + name)
        for key, artifact in [('runnerSHA256', TOOLS / 'run_native.py'),
                              ('unityExeSHA256', PINNED_UNITY),
                              ('hashProcessHelperSHA256', ROOT / 'Verification/Tools/Ads85/run_ads85_native.py'),
                              ('processSelectorSHA256', ROOT / 'Verification/Tools/PageBackdrop90/process90.py'),
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
        proof = {'name': name, 'invocation': binding(invocation_path), 'report': binding(report_path),
                 'checks': report['checks'], 'captures': captures, 'scope': report.get('scope', '')}
        if progress is not None:
            proof['progressAudit'] = progress
        result.append(proof)
    result.sort(key=lambda row: row['name'])
    return {'list': binding(list_path), 'runs': result, 'totalChecks': sum(row['checks'] for row in result)}


def build_proof(wrapper, current):
    wrapper = bound(wrapper, inside=OUT)
    value = read(wrapper)
    need(value.get('status') == 'PASS_INTERNAL_ANDROID_BUILDS92', 'BuildWrapperNotPassed')
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
                      ('processSelectorSHA256', ROOT / 'Verification/Tools/PageBackdrop90/process90.py')]:
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
    need(sha(HISTORICAL) == HISTORICAL_SHA, 'Historical90SummaryChanged')
    value = read(HISTORICAL)
    need(value.get('checkpoint') == 90 and value.get('releaseApproved') is False
         and value.get('wholeGameSmoothnessCertified') is False, 'Historical90ScopeChanged')
    for field in ('target', 'installation'):
        check_binding(value['physical'][field], inside=ROOT / 'Verification/Evidence/PageBackdrop90')
    previous = read(check_binding(value['historicalReference']['summary'], inside=ROOT / 'Verification/Evidence/RegionalAccounts89'))
    backend = read(check_binding(previous['backend']['report']))
    need(backend.get('status') == 'PASS_BACKEND_SERVICE_TESTS' and backend.get('tests') == 448
         and backend.get('sourceSHA256') == backend.get('sourceSHA256After') == backend_sources(),
         'BackendSourceChangedRequiresNewServiceAcceptance')
    return {'summary': binding(HISTORICAL), 'status': value['status'], 'backendSourceUnchanged': True,
            'backendTestsRerun': False,
            'scope': 'Immutable checkpoint90 reference and before images only; its source scope/failures stay unchanged. Backend bytes remain identical to accepted448-test inputs. No old current-tree verifier or overwritten old APK path is re-evaluated.'}, value


def static_apks(apks):
    path = OUT / 'Android/APK_Profile.json'
    value = read(path)
    need(value.get('status') == 'PASS_PROGRESS92_SDK_FREE_INTERNAL_APKS_STATIC', 'Current92StaticApksNotPassed')
    rows = value.get('artifacts', [])
    need(len(rows) == len(apks) == 2, 'BothStaticApkReportsRequired')
    artifacts = []
    for apk in apks:
        matches = [row for row in rows if row.get('path') == apk['path']]
        need(len(matches) == 1, 'StaticApkBindingMissing')
        row = matches[0]
        need(row.get('sha256') == apk['sha256'] and row.get('bytes') == apk['bytes']
             and row.get('package') == 'com.heartoftherain.verification'
             and row.get('nativePaymentAndAdvertisingSdkAbsent') is True
             and row.get('deviceIdentityClassPresent') is True, 'StaticApkScopeOrHashMismatch')
        artifact_path = bound(path.parent / row['staticArtifactReport'], inside=path.parent)
        artifact = read(artifact_path)
        need(artifact.get('sha256') == apk['sha256'] and artifact.get('bytes') == apk['bytes']
             and artifact.get('zipalign4KiBPass') is True and artifact.get('developmentSignatureVerifies') is True
             and artifact.get('elf16KiBLoadSegmentsPass') is True, 'StaticApkChecksNotPassed')
        artifacts.append(binding(artifact_path))
    return {'profile': binding(path), 'artifacts': artifacts, 'scope': value.get('scope', '')}


def _snapshot(value, apk):
    need(value.get('activeAttempts') == 0 and value.get('installedSHA256') == apk
         and isinstance(value.get('profiles'), dict) and value['profiles']
         and isinstance(value.get('preferences'), dict) and value['preferences']
         and isinstance(value.get('profileSummaries'), list) and value['profileSummaries'], 'PhoneSnapshotScopeInvalid')
    for field in ('profiles', 'preferences'):
        for relative, digest in value[field].items():
            need(not Path(relative).is_absolute() and '..' not in Path(relative).parts
                 and re.fullmatch('[0-9a-f]{64}', digest), 'PhoneSnapshotHashInvalid')
    for row in value.get('profileSummaries', []):
        need(row.get('activeAttempts') == 0, 'PhoneActiveAttemptPresent')
    return value['profiles'], value['preferences'], value.get('profileSummaries', [])


def fifth_chain(target_path, target):
    chain = validate_upgrade_chain(target_path)
    need(target.get('upgradeChainDepth') == chain.get('depth') == 5
         and chain.get('candidateApkSHA256') == target.get('candidateApkSHA256')
         and len(chain.get('links', [])) == 5, 'CompleteFifthOwnerPhoneLinkRequired')
    return chain


def finish_proof(phone):
    markers_path, relaunch_path, review_path = (phone / name for name in
        ('FinalMarkerState.json', 'Relaunch.json', 'Log_Review.json'))
    need(read(markers_path).get('pendingOptInMarkers') == [], 'PhoneFinalMarkersNotEmpty')
    relaunch = read(relaunch_path)
    need(isinstance(relaunch.get('launchResult'), str) and 'Status: ok' in relaunch['launchResult']
         and type(relaunch.get('fixedObservationWaitSeconds')) in (int, float)
         and 0 < relaunch['fixedObservationWaitSeconds'] <= 60 and bool(relaunch.get('scope')),
         'OrdinaryRelaunchReceiptMissing')
    review = read(review_path)
    log_path = bound(phone / review['log'], inside=phone)
    need(log_path.suffix == '.log' and review.get('sha256') == sha(log_path), 'PhoneScopedLogChanged')
    body = log_path.read_text('utf-8-sig')
    signatures = len(re.findall(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException|DllNotFoundException', body))
    need(type(review.get('selectedErrorCount')) is int and review['selectedErrorCount'] == signatures == 0
         and re.fullmatch(r'\d+', str(review.get('pid', ''))) and bool(review.get('scope')), 'PhoneSelectedLogErrorsPresent')
    return {'finalMarkerState': binding(markers_path), 'ordinaryRelaunch': binding(relaunch_path),
            'scopedLogReview': binding(review_path), 'scopedLog': binding(log_path), 'selectedErrorCount': 0,
            'scope': 'Final marker inventory is empty; ordinary relaunch was requested. Current app-PID log has zero selected signatures only, not a whole-app or performance PASS.'}


def before_proof(visual, phone, history):
    previous_apk = next(row['sha256'] for row in history['apks'] if row['development'])
    previous_phone = bound(history['physical']['target']['path']).parent
    references = visual.get('beforeReferences', [])
    need(isinstance(references, list) and {'RainCup', 'Profile'}.issubset(
        {row.get('name') for row in references if row.get('matchedOwnerState') is True}), 'MatchedRainCupAndProfileBeforeRequired')
    baseline = OUT / 'Baseline90'
    baseline_record = read(baseline / 'Invocation.json')
    need(baseline_record.get('status') == 'RECORDED_ACCEPTED90_BASELINE_OWNER_PRESERVED'
         and baseline_record.get('ownerDataUnchanged') is True
         and baseline_record.get('installedSHA256') == previous_apk
         and baseline_record.get('runner') == binding(TOOLS / 'baseline.py')
         and baseline_record.get('priorTarget') == history['physical']['target'], 'MatchedBaselineRunNotPreserved')
    install_before = _snapshot(read(phone / 'Install_Before.json'), previous_apk)
    for filename in ('OrdinaryBefore.json', 'OrdinaryAfter.json', 'OrdinaryAfterRelaunch.json'):
        need(_snapshot(read(baseline / filename), previous_apk) == install_before, 'BeforeAndAfterOwnerStateNotMatched')
    need(read(baseline / 'FinalMarkerState.json').get('pendingOptInMarkers') == [], 'BaselinePendingMarkers')
    accepted = {row['image']['path']: row for row in history['physical']['captures']}
    result = []
    for row in references:
        need(row.get('reviewed') is True and bool(row.get('scope')), 'BeforeReferenceNotAssessed')
        path = check_binding(row['image'])
        metadata_path = check_binding(row['metadata'])
        need(metadata_path == path.with_suffix('.json') and path.suffix.lower() == '.png', 'BeforeOriginalPngMetadataRequired')
        if path.is_relative_to(previous_phone):
            need(row['image']['path'] in accepted and accepted[row['image']['path']]['image'] == row['image']
                 and accepted[row['image']['path']]['metadata'] == row['metadata'], 'BeforeImageNotImmutable90AcceptedCapture')
            origin = previous_phone
            need(row.get('matchedOwnerState') is False, 'Historical90ImageCannotClaimMatchedCurrentOwnerState')
        else:
            need(path.is_relative_to(baseline), 'FreshBeforeCaptureOutsideMatchedBaselineRun')
            need(row['image'] in baseline_record.get('captures', []) and row.get('matchedOwnerState') is True,
                 'MatchedBaselineCaptureNotRecorded')
            origin = baseline
        metadata = read(metadata_path)
        need(metadata.get('kind') == 'ACTUAL_ANDROID_OS_FRAMEBUFFER'
             and metadata.get('pngValidation') == 'COMPLETE_CHUNKS_IEND_CRC_AND_DECODE'
             and metadata.get('installedSHA256') == previous_apk
             and metadata.get('sha256') == sha(path)
             and bound(origin / metadata['png'], inside=origin) == path
             and png_dimensions(path) == (metadata.get('width'), metadata.get('height')), 'BeforePhoneCaptureReceiptInvalid')
        result.append({'name': row['name'], 'image': binding(path), 'metadata': binding(metadata_path),
                       'scope': row['scope'], 'reviewed': True, 'matchedOwnerState': row['matchedOwnerState']})
    return result


def physical_proof(phone, visual_path, apks, current, history):
    phone = bound(phone, inside=OUT)
    visual_path = bound(visual_path, inside=phone)
    development = next(row for row in apks if row['development'])
    target_path, install_path = phone / 'Target.json', phone / 'Installation.json'
    target, installed = read(target_path), read(install_path)
    old_target_path = check_binding(history['physical']['target'], inside=ROOT / 'Verification/Evidence/PageBackdrop90')
    old_target = read(old_target_path)
    old_installation = check_binding(history['physical']['installation'], inside=ROOT / 'Verification/Evidence/PageBackdrop90')
    old_apk = next(row for row in history['apks'] if row['development'])
    need(target.get('authorization') == 'OWNER_REQUESTED_PROGRESS92'
         and target.get('package') == old_target.get('package') == 'com.heartoftherain.verification'
         and target.get('serialSHA256') == old_target.get('serialSHA256')
         and re.fullmatch('[0-9a-f]{64}', target.get('serialSHA256', ''))
         and target.get('model') == old_target.get('model'), 'ExplicitSameOwnerPhysicalTargetMissing')
    need(check_binding(target['priorTarget']) == old_target_path and check_binding(target['priorInstallation']) == old_installation,
         'Immutable90AncestryNotEstablished')
    need(target.get('baselineInstalledSHA256') == old_apk['sha256']
         and target.get('candidateApk') == development['path'] and target.get('candidateApkSHA256') == development['sha256'], 'PhoneCandidateNotCurrentBuild')
    chain = fifth_chain(target_path, target)
    need(installed.get('status') == 'PASS_SAVE_PRESERVING_REPLACEMENT', 'SavePreservingInstallNotPassed')
    before_path = phone / 'Install_Before.json'
    before, after = read(before_path), installed['after']
    need(_snapshot(before, old_apk['sha256']) == _snapshot(after, development['sha256']), 'InstallationChangedOrdinaryData')
    visual = read(visual_path)
    need(visual.get('schemaVersion') == 1 and visual.get('status') == 'REVIEWED_PROGRESS92_PHONE'
         and visual.get('apkSHA256') == development['sha256'] and bool(visual.get('scope'))
         and visual.get('ordinaryDataUnchanged') is True and visual.get('ordinaryDataUnchangedAfterRelaunch') is True
         and visual.get('noActiveAttempt') is True and isinstance(visual.get('warnings'), list)
         and isinstance(visual.get('limitations'), list) and visual['limitations'], 'ExplicitPhoneVisualAssessmentMissing')
    current_manifest(check_binding(visual['sourceManifest'], inside=OUT), current)
    observer_path = check_binding(visual['nativeObserver'], inside=phone)
    observer = read(observer_path)
    need(observer.get('status') in ('OBSERVING_PAGE_BACKDROP90', 'RECORDED_PAGE_BACKDROP90_OBSERVATION')
         and observer.get('startedUtc') and observer.get('lastSampleUtc') and observer.get('snapshots'), 'CurrentPhoneNativeObserverMissing')
    journal_path = phone / 'UI_Actions.json'
    journal = read(journal_path)
    need(journal.get('status') == 'OBSERVING_UI92_REQUIRES_VISUAL_REVIEW'
         and journal.get('runner') == binding(TOOLS / 'phone_review.py') and journal.get('nativeLaunchUtc'),
         'CurrentPhoneUiJournalMissing')
    observed_start = datetime.fromisoformat(observer['startedUtc'].replace('Z', '+00:00'))
    observed_last = datetime.fromisoformat(observer['lastSampleUtc'].replace('Z', '+00:00'))
    requested_start = datetime.fromisoformat(journal['nativeLaunchUtc'].replace('Z', '+00:00'))
    need(all(value.tzinfo is not None for value in (observed_start, observed_last, requested_start))
         and requested_start <= observed_start <= observed_last, 'PhoneObserverFromPreviousLaunch')
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
    need(len(cases) >= len(PHONE_CASES) and len(cases) == len({row.get('name') for row in cases}) and PHONE_CASES.issubset({row.get('name') for row in cases}), 'AffectedAndHomePhoneCasesRequired')
    captures, reviewed = {}, []
    for case in cases:
        need(case.get('passed') is True and case.get('progressReviewed') is True and case.get('controlsSafe') is True
             and bool(case.get('scope')) and case.get('captures'), 'PhoneVisualCaseNotPassed')
        if case['name'] == 'Home':
            need((phone / 'Screens/Relaunch_Observed.png').relative_to(ROOT).as_posix() in case['captures'],
                 'OrdinaryRelaunchHomeCaptureRequired')
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
        reviewed.append({'name': case['name'], 'captures': images, 'scope': case['scope'], 'passed': True,
                         'progressReviewed': True, 'controlsSafe': True})
    reviewed.sort(key=lambda row: row['name'])
    return {'target': binding(target_path), 'installation': binding(install_path), 'installBefore': binding(before_path),
            'visualAssessment': binding(visual_path), 'sourceManifest': visual['sourceManifest'], 'ordinarySnapshots': snapshots,
            'beforeReferences': before_proof(visual, phone, history),
            'nativeObserver': binding(observer_path), 'uiJournal': binding(journal_path),
            'ownerUpgradeChain': chain, 'completion': finish_proof(phone),
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
    return {'schemaVersion': 1, 'checkpoint': 92, 'files': files}


def verify(summary=None):
    summary = read(OUT / 'Summary.json') if summary is None else summary
    need(summary.get('schemaVersion') == 1 and summary.get('checkpoint') == summary.get('source_checkpoint') == 92
         and summary.get('status') == STATUS and summary.get('currentApkInstalled') is True, 'Current92ScopeInvalid')
    for key in ('releaseApproved', 'allChecklistRowsPassed', 'wholeGameSmoothnessCertified', 'productionReady',
                'actualVkProviderVerified', 'googleSignInImplemented', 'publicBackendDeployed', 'realAdsVerified'):
        need(summary.get(key) is False, 'UnsupportedProductionClaim:' + key)
    current = freeze()
    current_manifest(check_binding(summary['sourceManifest'], inside=OUT), current)
    need(summary.get('sourceSHA256') == summary['sourceManifest']['sha256'] and summary.get('unityInputCount') == current['inputCount'], 'PublishedCurrentSourceMismatch')
    need(summary.get('toolSHA256') == source_tools(), 'Current92CollectorOrHelperChanged')
    history, historical = historical_reference()
    need(summary.get('historicalReference') == history, 'HistoricalReferenceChanged')
    need(summary.get('native') == native_proof(summary['native']['list']['path'], current), 'PublishedNativeProofChanged')
    builds, apks = build_proof(summary['builds']['wrapper']['path'], current)
    need(summary.get('builds') == builds and summary.get('apks') == apks, 'PublishedBuildProofChanged')
    need(summary.get('androidStatic') == static_apks(apks), 'PublishedAndroidStaticProofChanged')
    need(summary.get('physical') == physical_proof(bound(summary['physical']['target']['path']).parent,
         summary['physical']['visualAssessment']['path'], apks, current, historical), 'PublishedPhysicalProofChanged')
    need(read(check_binding(summary['artifactManifest'], inside=OUT)) == inventory(), 'Current92ArtifactInventoryChanged')
    return summary


def publish(args):
    current = freeze()
    native = native_proof(args.native_list, current)
    builds, apks = build_proof(args.builds, current)
    historical, history = historical_reference()
    physical = physical_proof(args.phone, args.visual, apks, current, history)
    write(OUT / 'Sources.json', current)
    write(OUT / 'ArtifactInventory.json', inventory())
    summary = {'schemaVersion': 1, 'checkpoint': 92, 'source_checkpoint': 92, 'utc': datetime.now(timezone.utc).isoformat(),
               'status': STATUS, 'sourceManifest': binding(OUT / 'Sources.json'), 'sourceSHA256': sha(OUT / 'Sources.json'),
               'unityInputCount': current['inputCount'], 'artifactManifest': binding(OUT / 'ArtifactInventory.json'),
               'toolSHA256': source_tools(), 'native': native, 'builds': builds, 'apks': apks, 'androidStatic': static_apks(apks),
               'physical': physical, 'historicalReference': historical, 'currentApkInstalled': True,
               'releaseApproved': False, 'allChecklistRowsPassed': False, 'wholeGameSmoothnessCertified': False,
               'productionReady': False, 'actualVkProviderVerified': False, 'googleSignInImplemented': False,
               'publicBackendDeployed': False, 'realAdsVerified': False,
               'scope': 'Targeted partial-progress artwork thickness and clipping repairs, with a scoped production progress-bar audit. Exact native/internal Android/static proofs and current phone observations preserve owner state. Historical90 before-image references remain separate; no provider, backend deployment, gameplay, performance or store acceptance.'}
    verify(summary)
    write(OUT / 'Summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    for name in ('native-list', 'builds', 'phone', 'visual'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    if args.publish and not all(getattr(args, name) for name in ('native_list', 'builds', 'phone', 'visual')):
        parser.error('Publishing requires all completed native/build/phone/root-visual proofs')
    result = publish(args) if args.publish else verify()
    print(json.dumps({'status': result['status'], 'summary': 'Verification/Evidence/Progress92/Summary.json',
                      'sourceSHA256': result['sourceSHA256'], 'nativeChecks': result['native']['totalChecks']}))


if __name__ == '__main__':
    main()
