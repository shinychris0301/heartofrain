"""Verify/publish current88 evidence without running Unity, ADB or old verifiers.

Root publishes only after actual native/build/device work and visual review:
  --publish --native <Invocation.json> --native-report <Report.json>
  --builds <Display88_Builds.json> --phone <new phone run directory>
  --visual <VisualAssessment.json>

All input paths are repository-relative or absolute inside Display88 evidence.
VisualAssessment schemaVersion1/status REVIEWED_DISPLAY88_PHONE requires:
  home: {capture: <root-relative PNG>, safeAreaFill: true, noGameplayLeak: true}
  gameplay: {capture: <root-relative PNG>, safeAreaFill: true,
             noDuplicateRendering: true}
  geometryReport: <root-relative collected Display88 observer Report.json>
  warnings: [...], limitations: [nonempty ...], scope: <nonempty text>
Each reviewed PNG must have its original phone.capture() JSON beside it.

Summary records the current Unity source map, two actual internal builds,
save-preserving phone update and explicit narrow visual observations. Publication
also requires the specified current native/phone tutorial, regression and twelve
continuation cases. No pending report is read merely by importing this module.
Historical86/87 summaries remain byte-frozen references with their failures;
their current-source verifiers are deliberately never imported or invoked.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Display88'
STATUS = 'COMPLETED_DISPLAY88_REPAIR_WITH_OPEN_GATES'
GENERATED = {'Summary.json', 'Current.json', 'ArtifactInventory.json', 'Comparison.html'}
HISTORICAL = {
    'Verification/Evidence/Review86/Summary.json': '088338fce86804b5f8c327645a787b0642b9198827385342e5d9f61531e6bb5b',
    'Verification/Evidence/Physical87/20261026_e71bc9d09515/Summary.json': 'eb91b37fac594ec950cb94d58b79bcea2820e4b4caf020ffcd055795e5219031'
}
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import freeze
sys.path.insert(0, str(ROOT / 'Verification/Tools'))
from Display88.phone import validate_upgrade_chain


def need(value, code):
    if not value:
        raise RuntimeError(code)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def bound(value, *, inside=None):
    path = Path(value)
    need('..' not in path.parts, 'ParentTraversalRefused')
    result = (ROOT / path).resolve()
    need(result.is_relative_to((inside or ROOT).resolve()), 'EvidencePathOutsideScope')
    return result


def read(path):
    path = Path(path)
    need(path.stat().st_size <= 40 * 1024 * 1024, 'JsonReportTooLarge')
    return json.loads(path.read_text('utf-8-sig'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NonfiniteJson')))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def binding(path):
    path = bound(path)
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def check_binding(value, *, inside=None):
    path = bound(value['path'], inside=inside)
    need(path.is_file() and sha(path) == value['sha256'] and path.stat().st_size == value['bytes'], 'BoundArtifactChanged:' + value['path'])
    return path


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
            # Check values, not loose words such as the status "token missing".
            text = path.read_text('utf-8-sig', errors='replace')
            need(not re.search(r'Bearer\s+[A-Za-z0-9_./+=-]{32,}|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', text), 'SecretValueInPublicEvidence')
        files[path.relative_to(ROOT).as_posix()] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    need(0 < len(files) < 20000, 'EvidenceFileCountInvalid')
    return {'schemaVersion': 1, 'checkpoint': 88, 'files': files}


def current_manifest(path, current):
    value = read(path)
    need(value.get('inputCount') == current['inputCount'] and value.get('files') == current['files'], 'CurrentUnitySourceMapMismatch')


def native_proof(invocation, native_report, current, expected='PASS_NATIVE_DISPLAY88'):
    invocation, native_report = bound(invocation, inside=OUT), bound(native_report, inside=OUT)
    value, native = read(invocation), read(native_report)
    need(value.get('status') == 'PASS_NATIVE_DISPLAY88_INVOCATION' and value.get('exitCode') == 0 and not value.get('timedOut')
         and value.get('inputsUnchanged') is True and value.get('unityPidsAfter') == [], 'NativeInvocationNotPassed')
    need(native.get('status') == expected and native.get('unity') == '2022.3.62f3'
         and native.get('checks', 0) > 0 and not native.get('errors') and not native.get('failures'), 'NativeReportNotPassed')
    need(value.get('nativeReportSHA256') == sha(native_report) and value.get('checks') == native['checks'], 'NativeReportBindingMismatch')
    before = invocation.parent / 'FrozenSources.json'
    need(value.get('sourceSHA256') == sha(before) and value.get('inputCount') == current['inputCount'], 'NativeSourceBindingMismatch')
    current_manifest(before, current)
    current_manifest(invocation.parent / 'Sources_after.json', current)
    need(not any(read(invocation.parent / 'Source_Delta.json').values()), 'NativeSourceDeltaNotEmpty')
    for key, path in [('runnerSHA256', ROOT / 'Verification/Tools/Display88/run_native.py'),
                      ('hashProcessHelperSHA256', ROOT / 'Verification/Tools/Ads85/run_ads85_native.py'),
                      ('processSelectorSHA256', ROOT / 'Verification/Tools/Review86/run_native86.py'),
                      ('unityLogSHA256', invocation.parent / 'Unity.log'), ('consoleSHA256', invocation.parent / 'Console.log')]:
        need(value.get(key) == sha(path), 'NativeHelperOrLogChanged')
    for capture in native.get('captures', []):
        path = bound(invocation.parent / capture['file'], inside=invocation.parent)
        need(path.is_file() and path.suffix.lower() == '.png', 'NativeCaptureMissing')
    return {'invocation': binding(invocation), 'report': binding(native_report), 'checks': native['checks'],
            'scope': native.get('scope', '')}


def phone_check_receipt(path, current, apk, target, builds, mode):
    """Shared exact source/APK/tool receipts produced by run_phone_checks.py."""
    path = bound(path, inside=OUT)
    value = read(path)
    need(value.get('checkpoint') == 88 and value.get('mode') == mode and value.get('inputsUnchanged') is True
         and value.get('runnerUnchanged') is True and value.get('phoneHelperUnchanged') is True, 'PhoneCheckInputsNotPreserved')
    for key, expected in [('runner', ROOT / 'Verification/Tools/Display88/run_phone_checks.py'),
                          ('phoneHelper', ROOT / 'Verification/Tools/Display88/phone.py')]:
        need(check_binding(value[key]) == expected.resolve(), 'PhoneCheckToolReceiptMismatch')
    need(value.get('apk') == {key: apk[key] for key in ('path', 'sha256', 'bytes')} and value.get('target') == target,
         'PhoneCheckCurrentApkOrTargetMismatch')
    manifest = check_binding(value['sourceManifest'], inside=path.parent)
    current_manifest(manifest, current)
    current_manifest(path.parent / 'Sources_after.json', current)
    need(value.get('inputCount') == current['inputCount'], 'PhoneCheckSourceCountMismatch')
    matching = value['matchingBuild']
    need(matching.get('wrapper') == builds['wrapper'] and matching.get('invocation') == builds['invocation'], 'PhoneCheckBuildReceiptMismatch')
    current_manifest(check_binding(matching['sourceManifest'], inside=OUT), current)
    return value


def recovered_regression_collection(original_path, original, current, apk, target):
    """Accept additive read-only collection while retaining the failed receipt."""
    need(original.get('status') == 'FAIL_PHYSICAL_TRANSIENT_REGRESSION88'
         and original.get('failureCategory') == 'UnexpectedNativeRegressionFilesPreserved', 'UnapprovedRegressionHostFailure')
    path = original_path.parent / 'Recollection/Invocation.json'
    value = read(path)
    need(value.get('status') == 'PASS_PHYSICAL_REGRESSION88_READ_ONLY_RECOLLECTION'
         and all(value.get(key) is True for key in ('inputsUnchanged', 'runnerUnchanged', 'collectionAlgorithmUnchanged',
                                                   'phoneHelperUnchanged', 'originalInvocationUnchanged', 'ordinaryDataUnchanged')),
         'ReadOnlyRegressionRecollectionNotPassed')
    need(value.get('originalInvocation') == binding(original_path)
         and value.get('nativeSnapshot') == binding(original_path.parent / 'Latest.json'), 'RecollectionOriginalReceiptChanged')
    need(value.get('apk') == {key: apk[key] for key in ('path', 'sha256', 'bytes')} and value.get('target') == target
         and value.get('matchingBuild') == original.get('matchingBuild'), 'RecollectionApkTargetOrBuildMismatch')
    for key, expected in [('runner', ROOT / 'Verification/Tools/Display88/recover_regression_collection.py'),
                          ('collectionAlgorithm', ROOT / 'Verification/Tools/Display88/run_phone_checks.py'),
                          ('phoneHelper', ROOT / 'Verification/Tools/Display88/phone.py')]:
        need(check_binding(value[key]) == expected.resolve(), 'RecollectionToolReceiptChanged')
    current_manifest(check_binding(value['sourceManifest'], inside=path.parent), current)
    current_manifest(path.parent / 'Sources_after.json', current)
    before = check_binding(value['remoteBefore'], inside=path.parent)
    after = check_binding(value['remoteAfter'], inside=path.parent)
    need(sha(before) == sha(after) and read(before) == read(original_path.parent / 'Latest.json'), 'RemoteRegressionChangedDuringReadOnlyCollection')
    need(value.get('ordinaryBefore') == value.get('ordinaryAfter'), 'ReadOnlyRecollectionChangedOrdinaryData')
    remote_inventory = read(check_binding(value['remoteInventory'], inside=path.parent))
    unlisted = read(check_binding(value['unlistedCaptures'], inside=path.parent))
    need(all(row.get('retained') is False and row.get('freshnessEstablished') is False and row.get('acceptanceEvidence') is False
             for row in unlisted.get('files', [])), 'UnlistedNativeFilesPromotedToAcceptance')
    need({row['file'] for row in unlisted.get('files', [])} == set(remote_inventory.get('unlistedSafeGeneratedPngs', [])),
         'UnlistedNativeCaptureInventoryMismatch')
    return value['collection'], {'invocation': binding(path), 'status': value['status'],
                                 'originalHostStatusRetained': original['status'], 'scope': value['scope']}


def additional_proof(current, apks, physical, builds):
    phone = bound(physical['target']['path']).parent
    apk = next(row for row in apks if row['development'])

    tutorial_folder = OUT / 'Native/Tutorial04'
    native_tutorial = native_proof(tutorial_folder / 'Invocation.json', tutorial_folder / 'Report.json', current,
                                   'PASS_NATIVE_TUTORIAL_GESTURE88')
    invocation, tutorial = read(tutorial_folder / 'Invocation.json'), read(tutorial_folder / 'Report.json')
    cases = tutorial.get('cases', [])
    need(invocation.get('entry') == 'HeartOfTheRain.Verification.TutorialGesture88Verification.Run'
         and tutorial.get('checks') == 319 and len(cases) == 11 and len({row['name'] for row in cases}) == 11
         and all(row.get('passed') is True and not row.get('error') for row in cases)
         and tutorial.get('isolatedProfile') is True and tutorial.get('ordinaryPreferencesPreserved') is True,
         'NativeTutorial319ChecksNotPassed')
    native_tutorial.update(cases=11, isolatedProfile=True, ordinaryPreferencesPreserved=True)

    regression_folder = phone / 'Regression'
    regression_path = regression_folder / 'Invocation.json'
    regression = phone_check_receipt(regression_path, current, apk, physical['target'], builds, 'regression')
    native_path = regression_folder / 'Native/Regression.json'
    native = read(native_path)
    recovery = None
    if regression.get('status') == 'PASS_PHYSICAL_TRANSIENT_REGRESSION88':
        collection = regression['collection']
    else:
        collection, recovery = recovered_regression_collection(regression_path, regression, current, apk, physical['target'])
    need(native.get('status') == 'PASS_NATIVE_REGRESSION'
         and native.get('unity') == '2022.3.62f3' and native.get('platform') == 'Android' and not native.get('failures')
         and regression.get('nativeStatus') == native['status'] and regression.get('failures') == native['failures']
         and regression.get('checks') == native.get('checks') and native.get('checks', 0) > 0, 'PhysicalRegressionNotPassed')
    for key, count in [('boards', 50), ('actions', 408), ('clips', 354)]:
        need(regression.get(key) == native.get(key) == count, 'PhysicalRegressionCoverageMismatch')
    need(regression.get('ordinaryDataUnchanged') is True and regression.get('ordinaryDataUnchangedAfterNormalRelaunch') is True
         and regression.get('ordinaryBefore') == regression.get('ordinaryAfter') == regression.get('ordinaryAfterNormalRelaunch'),
         'PhysicalRegressionOrdinaryDataChanged')
    need(check_binding(collection['nativeReport'], inside=regression_folder) == native_path.resolve(), 'RegressionNativeReportBindingMismatch')
    atlas = read(check_binding(collection['atlasReport'], inside=regression_folder))
    need(atlas.get('status') == 'PASS_NATIVE_M70_DEVICE' and not atlas.get('failures'), 'RegressionAtlasNotPassed')
    capture_path = check_binding(collection['captureInventory'], inside=regression_folder)
    captures = read(capture_path)
    rows = captures.get('files', [])
    need(captures.get('status') == 'RECORDED_NATIVE_REGRESSION_CAPTURE_RETENTION88' and len(rows) == len(native['frames'])
         and {row['file'] for row in rows} == set(native['frames']) and len({row['file'] for row in rows}) == len(rows)
         and captures.get('capturedPngCount') == collection.get('capturedPngCount') == len(rows)
         and captures.get('retainedPngCount') == collection.get('retainedPngCount') == sum(row.get('retained') is True for row in rows) == 12,
         'RegressionCaptureRetentionInventoryInvalid')
    for row in rows:
        need(re.fullmatch('[0-9a-f]{64}', row.get('sha256', '')) and row.get('bytes', 0) > 0, 'RegressionCaptureHashMissing')
        if row['retained']:
            check_binding({'path': row['retainedEvidence'], 'sha256': row['sha256'], 'bytes': row['bytes']}, inside=regression_folder)
        else:
            need(row.get('retainedEvidence') is None, 'UnretainedRegressionImagePresentedAsPortableEvidence')
    regression_proof = {'invocation': binding(regression_path), 'nativeReport': binding(native_path),
                        'captureInventory': binding(capture_path), 'checks': native['checks'], 'boards': 50, 'actions': 408, 'clips': 354,
                        'retainedPngCount': 12, 'capturedPngCount': len(rows), 'ordinaryDataPreserved': True,
                        'originalHostStatus': regression['status'], 'collectionRecovery': recovery, 'scope': regression['scope']}

    no_moves_folder = phone / 'NoMoves'
    no_moves_path, no_moves_invocation_path = no_moves_folder / 'Summary.json', no_moves_folder / 'Invocation.json'
    no_moves = phone_check_receipt(no_moves_path, current, apk, physical['target'], builds, 'no-moves')
    no_moves_invocation = read(no_moves_invocation_path)
    if no_moves_invocation != no_moves:
        need(no_moves_invocation.get('status') == 'PASS_PHYSICAL_NO_MOVES88_CURRENT' and no_moves_invocation.get('exitCode') == 0
             and check_binding(no_moves_invocation['summary'], inside=no_moves_folder) == no_moves_path.resolve(), 'NoMovesProcessInvocationNotPassed')
    need(no_moves.get('status') == 'PASS_PHYSICAL_NO_MOVES88_REQUIRES_VISUAL_REVIEW', 'TwelveNoMovesCasesNotPassed')
    need(check_binding(no_moves['caseAlgorithm']) == (ROOT / 'Verification/Tools/Physical87/no_moves.py').resolve(), 'ApprovedNoMovesAlgorithmChanged')
    fixture_rows = []
    for key in ('noMovesR3', 'shopBounds'):
        reference = no_moves['fixtureInputs'][key]
        path = bound(reference['path'])
        need(sha(path) == reference['sha256'], 'ApprovedNoMovesFixtureChanged')
        fixture_rows.extend(row for row in read(path)['entries'] if key == 'noMovesR3' or row['scenario'] == 'shop_bounds')
    fixtures = {row['scenario']: row for row in fixture_rows}
    rows = no_moves.get('cases', [])
    need(len(fixtures) == len(rows) == 12 and {row['scenario'] for row in rows} == set(fixtures), 'NoMovesTwelveScenarioInventoryMismatch')
    taps = swipes = 0
    for row in rows:
        case_folder = no_moves_folder / 'Cases' / row['scenario']
        need(read(case_folder / 'Result.json') == row and row.get('status') == 'PASS_PHYSICAL_NO_MOVES_CASE'
             and row.get('safeToContinue') is True and row.get('ordinaryDataUnchanged') is True
             and row.get('ordinaryDataUnchangedAfterNormalRelaunch') is True
             and row.get('ordinaryBefore') == row.get('ordinaryAfter') == row.get('ordinaryAfterNormalRelaunch'), 'NoMovesCaseOrOrdinaryPreservationFailed')
        fixture = fixtures[row['scenario']]
        expected_sha = hashlib.sha256(json.dumps(fixture, ensure_ascii=True, separators=(',', ':')).encode('ascii')).hexdigest()
        need(row.get('fixtureSHA256') == expected_sha, 'NoMovesCaseFixtureBindingMismatch')
        report = read(case_folder / 'Report.json')
        need(report.get('status') == row.get('nativeStatus') == 'PASS_ANDROID_NO_MOVES' and report.get('boardPreserved') is True
             and report.get('scenario') == row['scenario'] and not report.get('error'), 'NativeNoMovesCaseNotPassed')
        for key, count in [('coins', fixture['coinsAfter']), ('moves', fixture['movesAfter']), ('purchases', fixture['countAfter']),
                           ('lives', 4 if row['scenario'] == 'end' else 5)]:
            need(report.get(key) == count, 'NoMovesWalletMovesOrLifeMismatch')
        for action in row['inputs']:
            need(action.get('dispatch') == 'ADB_COMPLETED' and action.get('kind') in ('tap', 'swipe'), 'NoMovesInputNotDispatched')
            taps += action['kind'] == 'tap'
            swipes += action['kind'] == 'swipe'
        for capture in row['captures']:
            path = bound(phone / capture['path'], inside=case_folder)
            metadata = read(path.with_suffix('.json'))
            need(sha(path) == capture['sha256'] == metadata.get('sha256') and metadata.get('kind') == 'ACTUAL_ANDROID_OS_FRAMEBUFFER'
                 and metadata.get('installedSHA256') == apk['sha256'], 'NoMovesActualCaptureChanged')
    need(no_moves.get('actualTaps') == taps == 12 and no_moves.get('actualSwipes') == swipes == 1, 'NoMovesActualInputTotalsMismatch')
    continuation = {'invocation': binding(no_moves_invocation_path), 'summary': binding(no_moves_path), 'cases': 12,
                    'actualTaps': taps, 'actualSwipes': swipes, 'ordinaryDataPreserved': True, 'scope': no_moves['scope']}

    touch_path = phone / 'Tutorial/Review.json'
    touch = read(touch_path)
    need(touch.get('status') == 'PASS_PHYSICAL_TUTORIAL_TOUCH88_CURRENT' and touch.get('apkSHA256') == apk['sha256']
         and touch.get('ordinaryDataUnchanged') is True and touch.get('ordinaryDataUnchangedAfterRelaunch') is True,
         'CurrentPhysicalTutorialTouchNotPassed')
    touch_native_path = check_binding(touch['nativeReport'], inside=phone / 'Tutorial')
    need(touch_native_path == (phone / 'Tutorial/Report.json').resolve(), 'PhysicalTutorialNativeReportPathMismatch')
    current_manifest(check_binding(touch['sourceManifest'], inside=OUT), current)
    touch_native = read(touch_native_path)
    lessons = touch_native.get('lessons', [])
    need(touch_native.get('status') == 'PASS_NATIVE_TUTORIAL_TOUCH88' and touch_native.get('unity') == '2022.3.62f3'
         and touch_native.get('platform') == 'Android' and touch_native.get('isolatedProfile') is True and not touch_native.get('error')
         and len(lessons) == 3 and {row['stage'] for row in lessons} == {'Match', 'Rocket', 'Clear'}
         and all(row.get('solved') is True for row in lessons), 'ThreePhysicalTutorialLessonsNotSolved')
    physical_tutorial = {'review': binding(touch_path), 'nativeReport': binding(touch_native_path), 'lessonsSolved': 3,
                         'ordinaryDataPreserved': True, 'scope': touch_native.get('scope', '')}
    return {'nativeTutorial': native_tutorial, 'physicalRegression': regression_proof,
            'physicalNoMoves': continuation, 'physicalTutorial': physical_tutorial}


def build_proof(wrapper, current):
    wrapper = bound(wrapper, inside=OUT)
    value = read(wrapper)
    need(value.get('status') == 'PASS_INTERNAL_ANDROID_BUILDS88', 'BuildWrapperNotPassed')
    invocation = bound(value['invocation'], inside=OUT)
    need(value.get('invocationSHA256') == sha(invocation), 'BuildInvocationBindingMismatch')
    report = read(invocation)
    need(report.get('status') == 'PASS_SDK_FREE_INTERNAL_ANDROID_BUILDS85' and report.get('allHistoricalNativeRestored') is True
         and report.get('inputsUnchangedAfterSettingsRestore') is True and report.get('unityPidsAfter') == [], 'InternalBuildsNotPassed')
    frozen = invocation.parent / 'FrozenSources.json'
    need(report.get('sourceSHA256') == sha(frozen) and report.get('inputCount') == current['inputCount'], 'BuildSourceBindingMismatch')
    current_manifest(frozen, current)
    current_manifest(invocation.parent / 'Sources_final.json', current)
    for key, path in [('wrapperSHA256', ROOT / 'Verification/Tools/Display88/run_builds.py'),
                      ('buildHelperSHA256', ROOT / 'Verification/Tools/Ads85/run_ads85_internal_build.py'),
                      ('processSelectorSHA256', ROOT / 'Verification/Tools/Review86/run_native86.py')]:
        need(value.get(key) == sha(path), 'BuildHelperChanged')
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
        filename = 'Android_Build.json' if row['build'] == 'Development' else 'Android_Release_Build.json'
        expected_status = 'PASS_ANDROID_DEVELOPMENT_BUILD' if row['build'] == 'Development' else 'PASS_ANDROID_RELEASE_COMPILE_BUILD'
        native = read(folder / filename)
        need(row.get('nativeReportSHA256') == sha(folder / filename) and native.get('status') == row.get('nativeStatus') == expected_status
             and native.get('unity') == '2022.3.62f3' and not native.get('errors') and not native.get('error'), 'NativeAndroidBuildNotPassed')
        apk = row['apk']
        check_binding(apk, inside=ROOT / 'Unity/Builds/Verification')
        need(row.get('unityLogSHA256') == sha(folder / 'Unity.log') and row.get('consoleSHA256') == sha(folder / 'Console.log'), 'BuildLogsChanged')
        apks.append(dict(apk, development=row['build'] == 'Development'))
    apks.sort(key=lambda row: not row['development'])
    return {'wrapper': binding(wrapper), 'invocation': binding(invocation)}, apks


def physical_proof(phone, visual_path, apks):
    phone, visual_path = bound(phone, inside=OUT), bound(visual_path, inside=OUT)
    target_path, install_path = phone / 'Target.json', phone / 'Installation.json'
    target, installed = read(target_path), read(install_path)
    chain = validate_upgrade_chain(target_path)
    historical_phone = read(ROOT / 'Verification/Evidence/Physical87/20261026_e71bc9d09515/Summary.json')
    development = next(row for row in apks if row['development'])
    need(target.get('authorization') == 'OWNER_REQUESTED_DISPLAY_REPAIR88' and target.get('package') == 'com.heartoftherain.verification'
         and re.fullmatch('[0-9a-f]{64}', target.get('serialSHA256', '')), 'ExplicitPhysicalTargetMissing')
    need(target.get('serialSHA256') == historical_phone['device']['serialSHA256'] and target.get('model') == historical_phone['device']['model']
         and chain['links'][0]['baselineInstalledSHA256'] == historical_phone['sourceBinding']['apk']['sha256'], 'SameOwnerPhoneAndBaselineNotEstablished')
    need(target.get('candidateApk') == development['path'] and target.get('candidateApkSHA256') == development['sha256'], 'PhysicalCandidateNotCurrentBuild')
    need(installed.get('status') == 'PASS_SAVE_PRESERVING_REPLACEMENT', 'SavePreservingInstallNotPassed')
    before, after = read(phone / 'Install_Before.json'), installed['after']
    need(before.get('activeAttempts') == after.get('activeAttempts') == 0 and before.get('profiles') == after.get('profiles')
         and before.get('preferences') == after.get('preferences') and after.get('installedSHA256') == development['sha256'], 'InstallSaveOrApkMismatch')
    need(before.get('installedSHA256') == target.get('baselineInstalledSHA256'), 'InstalledBaselineMismatch')
    visual = read(visual_path)
    need(visual.get('schemaVersion') == 1 and visual.get('status') == 'REVIEWED_DISPLAY88_PHONE'
         and isinstance(visual.get('warnings'), list) and isinstance(visual.get('limitations'), list) and visual['limitations']
         and bool(visual.get('scope')), 'ExplicitVisualReviewMissing')
    need(visual['home'].get('safeAreaFill') is True and visual['home'].get('noGameplayLeak') is True
         and visual['gameplay'].get('safeAreaFill') is True and visual['gameplay'].get('noDuplicateRendering') is True, 'ReportedDisplayDefectsNotVisuallyClosed')
    captures = []
    for area in ('home', 'gameplay'):
        capture = bound(visual[area]['capture'], inside=phone)
        metadata = read(capture.with_suffix('.json'))
        need(metadata.get('kind') == 'ACTUAL_ANDROID_OS_FRAMEBUFFER' and metadata.get('installedSHA256') == development['sha256']
             and metadata.get('sha256') == sha(capture) and (phone / metadata['png']).resolve() == capture
             and metadata.get('width') == 720 and metadata.get('height') == 1600, 'ActualPhoneCaptureBindingMismatch')
        captures.append(binding(capture))
    geometry_path = bound(visual['geometryReport'], inside=phone)
    geometry = read(geometry_path)
    need(geometry.get('status') in ('OBSERVING_DISPLAY88', 'RECORDED_DISPLAY88_OBSERVATION')
         and geometry.get('unity') == '2022.3.62f3' and geometry.get('platform') == 'Android'
         and not geometry.get('errorTypes'), 'OrdinaryGeometryObserverMissingOrFailed')
    snapshots = geometry.get('snapshots', [])
    need(snapshots and all(row['geometry'].get('width') == 720 and row['geometry'].get('height') == 1600 for row in snapshots), 'PhoneGeometryDimensionsMismatch')
    home_states = [row['geometry']['home'] for row in snapshots if row['geometry'].get('home', {}).get('presentationVisible')]
    need(home_states, 'OrdinaryHomeGeometryNotObserved')
    for home in home_states:
        corners = home.get('background', {}).get('screenCorners', [])
        need(len(corners) == 4 and min(point['x'] for point in corners) <= .5 and max(point['x'] for point in corners) >= 719.5
             and min(point['y'] for point in corners) <= .5 and max(point['y'] for point in corners) >= 1599.5, 'HomeArtworkDoesNotCoverFramebuffer')
    gameplay_cameras = [camera for row in snapshots for camera in row['geometry'].get('cameras', []) if camera.get('name') == 'M46 Review Camera']
    need(gameplay_cameras, 'OrdinaryGameplayCameraNotObserved')
    for camera in gameplay_cameras:
        rect = camera.get('rect', {})
        need(all(abs(rect.get(key, -10) - expected) < .001 for key, expected in [('x', 0), ('y', 0), ('width', 1), ('height', 1)])
             and camera.get('hasTargetTexture') is False, 'OrdinaryGameplayCameraNotFullFramebuffer')
    return {'target': binding(target_path), 'installation': binding(install_path), 'visualAssessment': binding(visual_path),
            'geometryReport': binding(geometry_path), 'captures': captures, 'upgradeChain': chain, 'scope': visual['scope']}


def historical_references():
    result = []
    for relative, digest in HISTORICAL.items():
        path = bound(relative)
        need(sha(path) == digest, 'HistoricalSummaryChanged')
        value = read(path)
        if 'Review86/' in relative:
            need(value.get('allNativeSuitesPassed') is False and value.get('allAcceptancePassed') is False
                 and {row['suite'] for row in value['knownFailures']} == {'Account', 'AccountHttp'}
                 and all(row.get('acceptancePassed') is False for row in value['knownFailures']), 'HistoricalAccountFailuresNotRetained')
        else:
            need(value.get('releaseApproved') is False and value.get('allChecklistRowsPassed') is False
                 and value.get('wholeGameSmoothnessCertified') is False and len(value.get('knownFailures', [])) == 3, 'HistoricalPhysicalFailuresNotRetained')
        result.append(dict(binding(path), status=value['status'], scope='Historical frozen reference only; no assertion that its source map matches current88.'))
    return result


def verify(summary=None):
    summary = read(OUT / 'Summary.json') if summary is None else summary
    need(summary.get('schemaVersion') == 1 and summary.get('checkpoint') == summary.get('source_checkpoint') == 88
         and summary.get('status') == STATUS and summary.get('releaseApproved') is False
         and summary.get('allChecklistRowsPassed') is False and summary.get('wholeGameSmoothnessCertified') is False, 'Current88ScopeInvalid')
    current = freeze()
    source = check_binding(summary['sourceManifest'], inside=OUT)
    current_manifest(source, current)
    need(summary.get('sourceSHA256') == sha(source) and summary.get('unityInputCount') == current['inputCount'], 'PublishedSourceBindingMismatch')
    recorded_inventory = check_binding(summary['artifactManifest'], inside=OUT)
    need(read(recorded_inventory) == inventory(), 'New88ArtifactInventoryChanged')
    need(summary['historicalReferences'] == historical_references(), 'HistoricalReferenceBindingMismatch')
    native = native_proof(summary['native']['invocation']['path'], summary['native']['report']['path'], current)
    builds, apks = build_proof(summary['builds']['wrapper']['path'], current)
    physical = physical_proof(bound(summary['physical']['target']['path']).parent, summary['physical']['visualAssessment']['path'], apks)
    need(summary['native'] == native and summary['builds'] == builds and summary['apks'] == apks and summary['physical'] == physical, 'PublishedProofChanged')
    need(summary.get('additionalVerification') == additional_proof(current, apks, physical, builds), 'AdditionalCurrent88VerificationChanged')
    current_tools = {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(Path(__file__).parent.glob('*.py'))}
    need(summary['toolSHA256'] == current_tools, 'CollectorOrDisplayHelperChanged')
    return summary


def publish(args):
    current = freeze()
    native = native_proof(args.native, args.native_report, current)
    builds, apks = build_proof(args.builds, current)
    physical = physical_proof(args.phone, args.visual, apks)
    additional = additional_proof(current, apks, physical, builds)
    history = historical_references()
    write(OUT / 'Sources.json', current)
    tools = {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(Path(__file__).parent.glob('*.py'))}
    write(OUT / 'ArtifactInventory.json', inventory())
    summary = {'schemaVersion': 1, 'checkpoint': 88, 'source_checkpoint': 88, 'utc': datetime.now(timezone.utc).isoformat(),
               'status': STATUS, 'releaseApproved': False, 'allChecklistRowsPassed': False, 'wholeGameSmoothnessCertified': False,
               'sourceManifest': binding(OUT / 'Sources.json'), 'sourceSHA256': sha(OUT / 'Sources.json'), 'unityInputCount': current['inputCount'],
               'artifactManifest': binding(OUT / 'ArtifactInventory.json'), 'native': native, 'builds': builds, 'apks': apks,
               'physical': physical, 'additionalVerification': additional, 'historicalReferences': history, 'toolSHA256': tools,
               'currentApkInstalled': True, 'productionReady': False,
               'scope': 'Targeted full-display rendering repair,319-check tutorial recognizer regression, three physical tutorial lessons, current-source internal builds and transient50-board/twelve-Continue-case phone checks. Wider touch, performance, human campaign, service/provider and release gates remain; historical86/87 failures are preserved, not revalidated against this changed tree.'}
    verify(summary)
    write(OUT / 'Summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    for name in ('native', 'native-report', 'builds', 'phone', 'visual'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    if args.publish and not all(getattr(args, name) for name in ('native', 'native_report', 'builds', 'phone', 'visual')):
        parser.error('Publishing requires completed native/build/phone/visual inputs')
    result = publish(args) if args.publish else verify()
    print(json.dumps({'status': result['status'], 'summary': 'Verification/Evidence/Display88/Summary.json', 'sourceSHA256': result['sourceSHA256']}))


if __name__ == '__main__':
    main()
