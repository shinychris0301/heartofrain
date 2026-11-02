"""Metadata-only source/evidence seal, run only after the exclusive verifier finishes.

No Unity/backend import, test, compiler, subprocess, service, SDK, network or
device operation. Publication files and native/backend reports remain owned by
their authors. A prepared tool is not a completed source audit.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review107'
FINAL106 = ROOT / 'Verification/Evidence/Review106/Native/AfterMain01/MainSources_after.json'
BASE107 = ROOT / 'Verification/Tools/Review107/BaselineMain107.json'
DELTA106 = ROOT / 'Verification/Evidence/Review106/SourceDelta106.json'
BACKEND105 = ROOT / 'Verification/Evidence/Review105/TCP/Flow02/Report.json'
SUPPORT105 = ROOT / 'Verification/Evidence/Review105/SourceDelta105.json'
BACKEND107 = OUT / 'Backend/SourceDelta107.json'
CHANGED = {
    'Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/RewardedAdsConfiguration85.cs': OUT / 'RetainedSources/RewardedAdsConfiguration85.cs.before107',
    'Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/RewardedShop85.cs': OUT / 'RetainedSources/RewardedShop85.cs.before107',
    'Unity/Assets/HeartOfTheRain/App/ServerGameplay/Editor/StagingServerBuild104.cs': OUT / 'RetainedSources/StagingServerBuild104_before107.cs',
    'Unity/Assets/HeartOfTheRain/App/Home/Runtime/HomeLayoutEngine.cs': ROOT / 'Verification/Evidence/Review108/RetainedSources/HomeLayoutEngine_before108.cs',
    'Unity/Assets/HeartOfTheRain/App/Home/Runtime/MainNavigationFeedback.cs': ROOT / 'Verification/Evidence/Review108/RetainedSources/MainNavigationFeedback_before108.cs',
}
ADDED = tuple(sorted([
    'Unity/Assets/HeartOfTheRain/App/Advertising/Editor.meta',
    'Unity/Assets/HeartOfTheRain/Resources/HOTR_Advertising.meta',
    *(p + suffix for p in (
        'Unity/Assets/HeartOfTheRain/App/Advertising/Editor/AdvertisingBuild107.cs',
        'Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/AdvertisingConfiguration107.cs',
        'Unity/Assets/HeartOfTheRain/Resources/HOTR_Advertising/Configuration.json',
        'Unity/Assets/HeartOfTheRain/Verification/Editor/AdvertisingConfiguration107Verification.cs',
        'Unity/Assets/HeartOfTheRain/Verification/Editor/Navigation108Verification.cs',
    ) for suffix in ('', '.meta')),
]))
PATCH_ADDED = tuple(p for p in ADDED if '/Runtime/' in p and p.endswith('.cs')
                    or '/Advertising/Editor/' in p and p.endswith('.cs') or p.endswith('/Configuration.json'))


class Blocked(ValueError):
    pass


def need(value, code):
    if not value:
        raise Blocked(code)


def disk(path):
    value = str(Path(path).absolute())
    return '\\\\?\\' + value if os.name == 'nt' and not value.startswith('\\\\?\\') else value


def raw(path):
    with open(disk(path), 'rb') as stream:
        return stream.read()


def load(path):
    return json.loads(raw(path).decode('utf-8-sig'))


def sha(path):
    digest = hashlib.sha256()
    with open(disk(path), 'rb') as stream:
        for chunk in iter(lambda: stream.read(1_048_576), b''):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT.resolve()), 'bound_path_outside_workspace')
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=os.stat(disk(path)).st_size)


def difference(before, after):
    return dict(added=sorted(set(after) - set(before)), removed=sorted(set(before) - set(after)),
                changed=sorted(p for p in set(before) & set(after) if before[p] != after[p]))


def unity_inputs():
    result = {}
    for category in ('Assets', 'Packages', 'ProjectSettings'):
        for folder, _, names in os.walk(disk(ROOT / 'Unity' / category)):
            for name in names:
                path = Path(str(Path(folder) / name).removeprefix('\\\\?\\'))
                result[path.relative_to(ROOT).as_posix()] = dict(sha256=sha(path), bytes=os.stat(disk(path)).st_size)
    return dict(sorted(result.items()))


def backend_inputs():
    base = ROOT / 'Backend'
    paths = [p for part in ('hotr_backend', 'tests', 'tools', 'config') for p in (base / part).rglob('*')
             if p.is_file() and p.suffix in ('.py', '.json')]
    paths += [base / p for p in ('requirements.in', 'requirements.lock', 'README.md', 'Run-Local.ps1')]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def endings(data):
    crlf, lf = data.count(b'\r\n'), data.count(b'\n')
    return dict(bytes=len(data), CRLF=crlf, LF=lf, bareCR=data.count(b'\r') - crlf,
                style='CRLF' if crlf == lf else 'LF' if crlf == 0 else 'mixed', utf8Bom=data.startswith(b'\xef\xbb\xbf'))


def exclusive(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def patch_and_endings(before, final):
    patch, rows = [], []
    for relative, retained in CHANGED.items():
        need(sha(retained) == before[relative]['sha256'] and os.stat(disk(retained)).st_size == before[relative]['bytes'], 'retained_before_not_exact106')
        a, b = raw(retained), raw(ROOT / relative)
        need(sha(ROOT / relative) == final[relative]['sha256'], 'current_source_changed_before_patch')
        lines = lambda v: v.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n').splitlines(keepends=True)
        patch += list(difflib.unified_diff(lines(a), lines(b), fromfile=relative + ' (exact106)', tofile=relative + ' (final107_108)'))
        old, new = endings(a), endings(b)
        rows.append(dict(path=relative, retained106=bind(retained), before=old, after=new,
                         beforeSHA256=before[relative]['sha256'], afterSHA256=final[relative]['sha256'],
                         lineEndingConventionPreserved=all(old[k] == new[k] for k in ('style', 'bareCR', 'utf8Bom'))))
    for relative in PATCH_ADDED:
        lines = raw(ROOT / relative).decode('utf-8-sig').replace('\r\n', '\n').splitlines(keepends=True)
        patch += list(difflib.unified_diff([], lines, fromfile='/dev/null', tofile=relative + ' (added107_108)'))
    return ''.join(patch).encode('utf-8'), rows


def policy_reader_only_delta(epoch_files, final):
    relative = 'Unity/Assets/HeartOfTheRain/App/Advertising/Editor/AdvertisingBuild107.cs'
    retained = OUT / 'RetainedSources/AdvertisingBuild107_before_runtime_ads_reader_assertion.cs'
    need(sha(retained) == epoch_files[relative]['sha256'], 'policy_builder_epoch_not_retained')
    old, new = raw(retained).decode('utf-8-sig'), raw(ROOT / relative).decode('utf-8-sig')
    pattern = r'(?ms)^        static void CheckRuntimeAds\(Report r,RewardedAdsConfiguration85 expected\)\{\r?\n.*?^        \}\r?\n'
    helper = re.findall(pattern, new)
    need(len(helper) == 1 and new.count('CheckRuntimeAds(r,selectedAds);') == 1, 'packaging_reader_assertion_diff_ambiguous')
    reconstructed = re.sub(pattern, '', new).replace('CheckRuntimeAds(r,selectedAds);', '')
    need(reconstructed == old, 'later_builder_change_not_only_packaging_reader_assertions')
    return dict(retainedEpoch=bind(retained), finalBuilder=bind(ROOT / relative),
                exactDelta='Added CheckRuntimeAds verification helper and one call in Run packaging branch only.',
                policyAndLeaseLogicUnchanged=True, policySuiteNotRerunAfterAssertionAddition=True)


def native_epoch(folder, final, required):
    invocation = load(folder / 'Invocation.json')
    before, after = (load(folder / name) for name in ('MainSources_before.json', 'MainSources_after.json'))
    need(before == after and invocation.get('mainInputsUnchanged') is True, 'native_main_source_mutation')
    project_before, project_after = (load(folder / name) for name in ('ProjectSources_before.json', 'ProjectSources_after.json'))
    passed = invocation['status'] == 'PASS_NATIVE107_INVOCATION'
    report_path = (folder / invocation['nativeReport']).resolve()
    need(report_path.is_relative_to(folder.resolve()), 'native_report_outside_epoch')
    report = None
    if invocation.get('nativeReportSHA256'):
        need(sha(report_path) == invocation['nativeReportSHA256'], 'native_report_hash_mismatch')
        report = load(report_path)
    if required:
        need(passed and invocation['exitCode'] == 0 and not invocation.get('unityPidsAfter'), 'required_native_epoch_not_passed')
        need(report is not None and report.get('status') == invocation['expectedNativeStatus'], 'required_native_report_not_passed')
        need(invocation.get('projectInputsUnchanged') or invocation.get('originalPrivateAssetAndSourceBytesPreserved'), 'private_original_source_preservation_missing')
        delta = difference(after['files'], final)
        if delta != dict(added=[], removed=[], changed=[]):
            need(delta == dict(added=[], removed=[], changed=['Unity/Assets/HeartOfTheRain/App/Advertising/Editor/AdvertisingBuild107.cs']), 'required_called_source_changed')
            need(invocation['entry'] != 'HeartOfTheRain.App.Advertising.Editor.AdvertisingBuild107.BuildDevelopment', 'build_source_not_final')
    if invocation.get('projectScope') == 'main2022':
        need(project_before == project_after and project_before == before, 'main_project_epoch_mismatch')
    # The legacy general report uses a checks array and numeric passed count.
    # Preserve its invocation unchanged; use the actual report's numeric count.
    count = next((value for value in ((report or {}).get('checks'), (report or {}).get('passed'), invocation.get('checks')) if type(value) is int), 0)
    result = dict(tag=folder.name, kind='actual_native_invocation', status=invocation['status'],
                  entry=invocation['entry'], actualEngine=invocation.get('actualEngine'), checks=count,
                  legacyInvocationCountWasArray=isinstance(invocation.get('checks'), list),
                  projectScope=invocation.get('projectScope'), invocation=bind(folder / 'Invocation.json'),
                  mainBefore=bind(folder / 'MainSources_before.json'), mainAfter=bind(folder / 'MainSources_after.json'),
                  projectBefore=bind(folder / 'ProjectSources_before.json'), projectAfter=bind(folder / 'ProjectSources_after.json'),
                  mainDeltaToFinal=difference(after['files'], final), wholeMainManifestExactFinal=after['files'] == final,
                  projectDelta=difference(project_before['files'], project_after['files']))
    if required and after['files'] != final:
        if invocation['entry'] == 'HeartOfTheRain.App.Advertising.Editor.AdvertisingBuild107.RunPolicy':
            result['laterPackagingReaderAssertionOnly'] = policy_reader_only_delta(after['files'], final)
        else:
            result['calledRuntimeAndFixtureInputsStillExactFinal'] = True
            result['laterChangesAreToUncalledEditorBuilderOnly'] = True
    if report is not None:
        result['report'] = bind(report_path)
    return result


def sdk_artifact(final):
    folder = OUT / 'Native/AndroidBuildLts01'
    build_path = folder / 'AndroidBuild107.json'
    build = load(build_path)
    static_failed = folder / 'StaticApk107.json'
    static_path = folder / 'Static/Audit02/StaticApk107.json'
    failure, static = load(static_failed), load(static_path)
    need(failure['status'] == 'FAIL_STATIC_ADS107_APK' and len(failure['checks']) == 14, 'historical_static_failure_not_preserved')
    need(static['status'] == 'PASS_STATIC_ADS107_APK' and not static['errors'] and len(static['checks']) == 19, 'final_static_apk_audit_not_passed')
    need(static['nativeBuildSHA256'] == sha(build_path) and static['invocationSHA256'] == sha(folder / 'Invocation.json'), 'static_build_bindings_mismatch')
    apk = ROOT / build['apk']
    delivered = ROOT / 'Unity/Builds/Review107/HeartOfTheRain_107_108_Android_Test.apk'
    expected = '1e77c50cff0cf47fe55e7ae73b1507c457772a1bd3ca284acf0b4c6d93f59ecb'
    for path in (apk, delivered):
        need(path.resolve().is_relative_to(ROOT.resolve()) and sha(path) == expected and os.stat(disk(path)).st_size == 308031545, 'delivered_apk_not_exact_built_bytes')
    need(build['actualBuild'] and build['actualSdkBranchCompiled'] and not build['adsEnabled'] and not build['automaticSdkRequests'], 'actual_sdk_build_scope_mismatch')
    need(build['apkSHA256'] == static['apkSHA256'] == failure['apkSHA256'] == expected, 'static_apk_identity_mismatch')
    need(not any(static[k] for k in ('sdkInitialized', 'appLaunched', 'realAdVerified')), 'unapproved_sdk_device_claim')
    receipt_path = ROOT / '.verification-cache/Review107/Candidates/SDK01/Preparation.json'
    receipt = load(receipt_path)
    need(sha(receipt_path) == build['receiptSHA256'] and receipt['status'] == 'PREPARED_ADS107' and receipt['unity'] == '6000.3.27f1', 'sdk_candidate_receipt_mismatch')
    copied = {'Unity/' + p: digest for p, digest in receipt['mainSourceSHA256'].items()}
    need(copied == {p: record['sha256'] for p, record in final.items()}, 'sdk_candidate_not_prepared_from_final_main_source')
    return dict(preparation=bind(receipt_path), nativeBuild=bind(build_path), originalFailedStaticAudit=bind(static_failed),
                acceptedStaticAudit=bind(static_path), buildErrors=build['errors'], buildWarnings=build['warnings'],
                builtApk=bind(apk), deliveredApk=bind(delivered), sameExactApk=True,
                isolatedEngine='6000.3.27f1', mainEnginePromoted=False, sdkInitialized=False,
                appInstalledOrLaunched=False, realAdsOrRewardsVerified=False)


def backend_proof():
    old = load(BACKEND105)['sourceSHA256After']
    need(len(old) == 105, 'wrong_backend105_input_count')
    after = backend_inputs()
    need(difference(old, after) == dict(added=['Backend/tests/test_rewarded_optin107.py'], removed=[], changed=['Backend/README.md', 'Backend/hotr_backend/staging105.py']), 'unexpected_backend107_delta')
    proof = load(BACKEND107)
    need(proof.get('schemaChanged') is False and proof.get('rewardRulesChanged') is False and proof.get('productionGuardChanged') is False, 'backend107_guard_proof_missing')
    for row in proof['files']:
        need(sha(ROOT / row['path']) == row['sha256'] and os.stat(disk(ROOT / row['path'])).st_size == row['bytes'], 'backend107_source_hash_mismatch')
    retained_index = OUT / 'RetainedSources/Backend105_Additional.json'
    retained = load(retained_index)['files']
    for row in retained:
        need(sha(ROOT / row['retained']) == row['sha256'], 'backend105_retained_hash_mismatch')
        if row['path'] in old:
            need(old[row['path']] == row['sha256'], 'backend105_retained_not_baseline')
    supplemental = load(SUPPORT105)['supplementalSupport']
    extra = []
    for row in supplemental:
        if row['path'] == 'Backend/Start-Staging105.ps1':
            old_row = next(v for v in retained if v['path'] == row['path'])
            need(old_row['sha256'] == row['sha256'], 'staging_wrapper_not_exact105')
            extra.append(dict(path=row['path'], beforeSHA256=row['sha256'], after=bind(ROOT / row['path'])))
        else:
            need(sha(ROOT / row['path']) == row['sha256'], 'unrelated105_support_changed')
    focused = ROOT / proof['focusedReport']
    report = load(focused)
    need(report['status'] == 'PASS' and report['failures'] == report['errors'] == report['skipped'] == 0 and report['sourcesUnchanged'], 'backend107_focused_proof_not_passed')
    return dict(baseline105=bind(BACKEND105), baselineInputCount=len(old), finalInputCount=len(after), delta=difference(old, after),
                additional105SupportChanges=extra, backendOwnerDelta=bind(BACKEND107), retained105Index=bind(retained_index),
                focusedReport=bind(focused), testCount=report['testsRun'], testsRerunByThisAudit=False), after


def seal(args):
    previous = load(DELTA106)
    need(previous['status'] == 'VERIFIED_UI106_SOURCE_DELTA', '106_seal_missing')
    need(sha(FINAL106) == previous['final106']['sha256'], '106_final_manifest_binding_changed')
    baseline = load(FINAL106)
    crosscheck = load(BASE107)
    need(baseline['files'] == crosscheck['files'] and baseline['inputCount'] == crosscheck['inputCount'] == 5490, '107_baseline_not_exact106')
    final_path = OUT / 'Native' / args.final_tag / 'MainSources_after.json'
    final = load(final_path)['files']
    need(len(final) == 5502 and unity_inputs() == final, 'final_main_source_not_current5502')
    delta = difference(baseline['files'], final)
    need(delta == dict(added=list(ADDED), removed=[], changed=sorted(CHANGED)), 'unexpected_combined_unity_delta')
    required = set(args.required_tag)
    need(args.final_tag in required and 'AdvertisingMain03' in required and 'Nav108Main01' in required, 'explicit_final_configuration_navigation_tags_required')
    epochs = [native_epoch(path.parent, final, path.parent.name in required) for path in sorted((OUT / 'Native').glob('*/Invocation.json'))]
    need(required <= {v['tag'] for v in epochs}, 'required_native_tag_missing')
    failed = [v['tag'] for v in epochs if v['status'] != 'PASS_NATIVE107_INVOCATION']
    need('AdvertisingMain02' in failed, 'Unity2022_compile_failure_not_retained')
    prelaunch = OUT / 'Native/AdvertisingMain01/PrelaunchFailure107.json'
    stopped = load(prelaunch)
    need(stopped['status'] == 'FAIL_PRELAUNCH107_ASSET_GUID_VALIDATION' and stopped['actualEditorStarted'] is False and stopped['compilerInvoked'] is False, 'malformed_meta_prelaunch_not_distinct')
    before_bad = load(OUT / 'Native/AdvertisingMain01/PrelaunchSources107.json')
    bad_paths = stopped['invalidNewMetaPaths']
    need(set(bad_paths) == {'Unity/Assets/HeartOfTheRain/Resources/HOTR_Advertising/Configuration.json.meta', 'Unity/Assets/HeartOfTheRain/Verification/Editor/AdvertisingConfiguration107Verification.cs.meta'}, 'prelaunch_failure_scope_changed')
    bad_retained = []
    for relative, retained in zip(bad_paths, ('Configuration107_invalid_guid.meta', 'AdvertisingConfiguration107Verification_invalid_guid.meta')):
        path = OUT / 'RetainedSources' / retained
        need(sha(path) == before_bad['files'][relative]['sha256'], 'malformed_meta_original_not_retained')
        bad_retained.append(bind(path))
    metas = [p for p in baseline['files'] if p.endswith('.meta')]
    need(all(baseline['files'][p] == final[p] for p in metas), 'original_meta_changed')
    guid_values = []
    for relative in final:
        if relative.startswith('Unity/Assets/') and relative.endswith('.meta'):
            found = re.findall(rb'(?m)^guid:\s*([0-9a-f]{32})\s*$', raw(ROOT / relative))
            need(len(found) == 1, 'current_meta_guid_malformed')
            guid_values.append(found[0])
    need(len(guid_values) == len(set(guid_values)), 'current_guid_collision')
    resource = load(ROOT / 'Unity/Assets/HeartOfTheRain/Resources/HOTR_Advertising/Configuration.json')
    need(resource == dict(version=2, enabled=False, rewardedUnitId='R-M-20291714-1', interstitialUnitId='R-M-20291714-2', privacyUrl='', privacyVersion='launch-r1'), 'packaged_ads_not_disabled_owner_ids')
    patch, ending_rows = patch_and_endings(baseline['files'], final)
    need(all(v['lineEndingConventionPreserved'] for v in ending_rows), 'existing_source_line_endings_changed')
    backend, backend_after = backend_proof()
    sdk = sdk_artifact(final)
    aggregates = [OUT / name for name in ('NativeVerification107.json', 'SDKVerification107.json', 'CompilerWarnings107.json',
                                         'FailuresAndEpochs107.json', 'Diagnostics107.json', 'APKDelivery107.json')]
    need(all(path.is_file() for path in aggregates), 'native_final_aggregate_missing')
    need(unity_inputs() == final and backend_inputs() == backend_after, 'source_changed_during_audit')
    outputs = {name: OUT / name for name in ('SourceDelta107_108.json', 'SourceChanges107_108.patch', 'LineEndings107_108.json')}
    need(not any(path.exists() for path in outputs.values()), 'preserve_existing_combined_audit')
    exclusive(outputs['SourceChanges107_108.patch'], patch)
    exclusive(outputs['LineEndings107_108.json'], (json.dumps(ending_rows, indent=2) + '\n').encode())
    protected = [p for p in baseline['files'] if p not in CHANGED]
    result = dict(schemaVersion=1, status='VERIFIED_SOURCE107_108_METADATA', utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  auditTool=bind(Path(__file__)), previous106Seal=bind(DELTA106), baseline106=bind(FINAL106), baseline107Crosscheck=bind(BASE107),
                  finalMainManifest=bind(final_path), baselineUnityInputs=5490, finalUnityInputs=len(final), unityDelta=delta,
                  allUnrelatedExistingInputsPreserved=all(baseline['files'][p] == final[p] for p in protected), protectedExistingCount=len(protected),
                  allOriginalMetasPreserved=True, originalMetaCount=len(metas), currentGuidCount=len(guid_values), malformedCurrentGuids=0, duplicateCurrentGuids=0,
                  approvedArtworkImportsLevelsGoalsPackagesSettingsPreserved=True, previous106NavigationProofRetainedAndNotReinterpreted=True,
                  changedSourceRecords=[dict(path=p, before=baseline['files'][p], after=final[p], retained=bind(CHANGED[p])) for p in sorted(CHANGED)],
                  addedSourceRecords=[dict(path=p, **final[p]) for p in ADDED], backend=backend, isolatedSdkArtifact=sdk,
                  nativeEpochs=epochs, finalRequiredPassTags=sorted(required), historicalNativeFailedTags=failed,
                  nativeOwnerFinalAggregates=[bind(path) for path in aggregates],
                  separatePrelaunchFailure=dict(proof=bind(prelaunch), manifest=bind(OUT / 'Native/AdvertisingMain01/PrelaunchSources107.json'), retainedMalformedMetas=bad_retained, actualNativeRun=False),
                  sourcePatch=bind(outputs['SourceChanges107_108.patch']), sourcePatchFiles=[*CHANGED, *PATCH_ADDED], lineEndings=bind(outputs['LineEndings107_108.json']),
                  disabledAdvertisingResource=bind(ROOT / 'Unity/Assets/HeartOfTheRain/Resources/HOTR_Advertising/Configuration.json'),
                  scope='Exact source bytes and existing evidence metadata only. This audit runs no tests/Unity/compiler/build/service/SDK/network/device action. Original art/GUIDs/levels/106 goals/settings stay preserved; only explicit107 advertising/build support and108 shared navigation changes are accepted. Private LTS SDK/build epochs stay separate from main2022 and do not imply SDK initialization, impression, reward, deployment or device acceptance.')
    exclusive(outputs['SourceDelta107_108.json'], (json.dumps(result, indent=2) + '\n').encode())
    return dict(status=result['status'], report=outputs['SourceDelta107_108.json'].relative_to(ROOT).as_posix(), sha256=sha(outputs['SourceDelta107_108.json']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', action='store_true')
    parser.add_argument('--final-tag')
    parser.add_argument('--required-tag', action='append', default=[])
    args = parser.parse_args()
    if not args.seal:
        print(json.dumps(dict(status='PREPARED_SOURCE107_108_AUDIT', sealed=False, testsRun=False)))
        return 0
    try:
        need(args.final_tag and all(re.fullmatch('[A-Za-z0-9_]{1,40}', t) for t in [args.final_tag, *args.required_tag]), 'explicit_valid_final_tags_required')
        result = seal(args)
    except Blocked as error:
        print(json.dumps(dict(status='BLOCKED_SOURCE107_108_AUDIT', code=str(error), sealed=False)))
        return 1
    except (OSError, ValueError, TypeError, KeyError, StopIteration):
        print(json.dumps(dict(status='BLOCKED_SOURCE107_108_AUDIT', code='source_metadata_unavailable', sealed=False)))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
