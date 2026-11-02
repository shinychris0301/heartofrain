"""Fail-closed checkpoint74 collector; does not build, install, or grant visual approval.

Draft contracts deliberately require fresh proof. A cache-only prototype, old
checkpoint73 device run, or unmeasured gap cannot publish a checkpoint74 pass.
"""
import hashlib
import json
import re
import runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Gameplay74'
BASE = ROOT / 'Verification/Evidence/LocalCascade73'
APK = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
BASE_CONTRACT = runpy.run_path(str(Path(__file__).with_name('collect_gameplay72_results.py')),
                              run_name='checkpoint72_contract_only')
NATIVE = dict(BASE_CONTRACT['NATIVE_STATUSES']) | {
    'LocalCascade': 'PASS_NATIVE_LOCAL_CASCADE73', 'CascadeTiming': 'PASS_NATIVE_CASCADE_TIMING',
    'LocalContinuation': 'PASS_NATIVE_LOCAL_CONTINUATION74',
    'LegalSwapExistence': 'PASS_NATIVE_LEGAL_SWAP_EXISTENCE74'}
TOOLS = BASE_CONTRACT['TOOLS']
MIXED = BASE_CONTRACT['MIXED_MODES']
TOUCH = BASE_CONTRACT['TOUCH_MODES']
PROFILE_CONTRACT = runpy.run_path(str(Path(__file__).with_name('validate_gameplay74_profile.py')),
                                 run_name='profiling_contract_only')
ALLOWED_CHANGED = {
    'Unity/Assets/HeartOfTheRain/' + name for name in [
        'M46/Runtime/BoardModel.cs', 'M46/Runtime/BoardPlayback.cs',
        'M46/Runtime/BoardPresentation.cs', 'M46/Runtime/M46AtlasBank.cs',
        'M47/Runtime/GameplayScreen.cs',
        'M47/Runtime/FeedbackPlanPure.cs', 'M47/Runtime/EffectMeshBatcher.cs',
        'Verification/CascadeTimingProbe.cs', 'Verification/ObstacleDensityProbe.cs',
        'Verification/Editor/LocalCascadeVerification.cs',
        'Verification/Editor/EffectBatchVerification.cs',
        'Verification/Editor/PresentationWarmupVerification.cs',
    ]
}
ADDED = {
    'Unity/Assets/HeartOfTheRain/' + name + suffix for name in [
        'M46/Runtime/LocalCascadeContinuation.cs',
        'Verification/Editor/LegalSwapExistenceVerification.cs',
        'Verification/Editor/LocalContinuationVerification.cs',
    ] for suffix in ['', '.meta']
}

evidence = {}


def need(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file(name, base=OUT):
    path = (base / name).resolve()
    need(path.is_relative_to(base.resolve()) and not {'Discarded', 'BeforeOnset', 'BeforeCPURefinement'} & set(path.parts),
         'Unsafe/historical proof path: ' + str(name))
    need(path.is_file(), 'Missing proof: ' + str(path))
    if path.is_relative_to(OUT):
        evidence[path.relative_to(OUT).as_posix()] = sha(path)
    return path


def read(name, base=OUT):
    return json.loads(file(name, base).read_text('utf-8-sig'))


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def clean(report, label):
    need(not any(report.get(k) for k in ['error', 'errors', 'failures', 'failed']), label + ' failed')


def preserved(report, before, label):
    need(report.get('data_unchanged') is True and report.get('before') == report.get('after') == before,
         label + ' did not preserve the real QA save/preferences')


def bound_visual(name, status, digest):
    report = read(name)
    need(report['status'] == status and report['apk_sha256'] == digest, name + ' is not final/reviewed')
    need(report.get('artifactSHA256'), name + ' has no bound artifacts')
    for path, expected in report['artifactSHA256'].items():
        need(sha(file(path)) == expected, name + ' artifact changed: ' + path)
    for path, expected in report.get('externalEvidenceSHA256', {}).items():
        need(sha(file(path, ROOT)) == expected, name + ' external baseline/reference changed: ' + path)
    return report


def installation(name, digest, build_finished, before=None):
    report = read(name)
    need(report['serial'] == 'emulator-5556'
         and report.get('sha256', report.get('apk_sha256')) == digest
         and utc(report['utc']) >= build_finished, name + ' is stale/not the final QA APK')
    if 'installed_apk_sha256' in report:
        need(report['installed_apk_sha256'] == digest, name + ' installed identity differs')
    if before is not None:
        preserved(report, before, name)
    need(report.get('runtime_errors', 0) == 0, name + ' has runtime errors')
    return report


def repeat_profiles(digest, build_finished, before):
    """Revalidate raw traces; the precomputed descriptive summary is not proof alone."""
    summary = read('RepeatProfiling/Summary.json')
    need(summary['status'] == 'VALIDATED_THREE_PROCESS_REPEATS_WITH_REMAINING_PERFORMANCE_GATES'
         and summary['apk_sha256'] == digest and summary['processes'] == 3 and summary['rows'] == 36,
         'Repeated final process controls are incomplete/stale')
    expected_paths, actual_profiles, previous_finished = set(), [], build_finished
    old = read('Android/Cascade/measure/Report.json', BASE)
    hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
    for number in range(1, 4):
        folder = 'RepeatProfiling/Process' + str(number).zfill(2) + '/measure/'
        install = installation(folder + 'Installation.json', digest, build_finished, before)
        report = read(folder + 'Report.json')
        # Android's COLD launch label describes this process launch only. The
        # runner prepares each board/bank; OS/storage/GPU caches are not flushed.
        need(install['variant'] == report['variant'] == 'measure' and install['repeats'] == report['repeats'] == 2
             and install['profilingAvailable'] is True and 'LaunchState: COLD' in install['launch']
             and previous_finished <= utc(install['utc']) <= utc(report['utc']),
             'Repeat controls are not three ordered separate final-APK launches')
        previous_finished = utc(report['utc'])
        actual_profiles.append({'process': number, 'profile': PROFILE_CONTRACT['validate'](report, 'measure', hashes)})
        expected_paths.update({folder + 'Installation.json', folder + 'Report.json'})
    need(summary['profiles'] == actual_profiles and set(summary['artifactSHA256']) == expected_paths,
         'Repeated summary differs from validated raw spans or omits an input')
    for path, expected in summary['artifactSHA256'].items():
        need(sha(file(path)) == expected, 'Repeated profiling input changed: ' + path)
    need('not cold-device' in summary['scope'] and 'causal speedup' in summary['scope'],
         'Repeated controls omit process/cache and causal limitations')
    return summary


def candidate_comparison(digest, profiling, density_profiling, fluidity):
    """Archived candidate data is comparison-only, never final-APK acceptance proof."""
    comparison = read('Candidate_Final_Profile_Comparison.json')
    need(comparison['status'] == 'DESCRIPTIVE_CANDIDATE_FINAL74_PROFILING_WITH_CAUSALITY_LIMITS'
         and comparison['apk_sha256'] == digest and comparison['candidate_apk_sha256'] != digest
         and comparison['sourceSchema'] == 1 and comparison['limits']
         and 'No performance pass threshold' in comparison['scope']
         and comparison['analyzerSHA256'] == sha(Path(__file__).with_name('compare_gameplay74_profiles.py'))
         and comparison['profilingValidatorSHA256'] == sha(Path(__file__).with_name('validate_gameplay74_profile.py')),
         'Candidate/final comparison is stale or overstates causal performance evidence')

    def comparison_file(name):
        path = (ROOT / name).resolve()
        allowed = path.is_relative_to(OUT / 'BeforeCPURefinement') or path.is_relative_to(BASE)
        if not allowed:
            return file(name, ROOT)
        need(path.is_file(), 'Missing archived comparison input: ' + name)
        if path.is_relative_to(OUT):
            evidence[path.relative_to(OUT).as_posix()] = sha(path)
        return path

    def archived(name):
        path = 'Verification/Evidence/Gameplay74/BeforeCPURefinement/' + name
        need(path in comparison['artifactSHA256'], 'Candidate comparison omits input: ' + name)
        return json.loads(comparison_file(path).read_text('utf-8-sig'))

    for path, expected in comparison['artifactSHA256'].items():
        need(sha(comparison_file(path)) == expected, 'Candidate comparison input changed: ' + path)
    candidate_sha = archived('APK_Artifact.json')['sha256']
    need(candidate_sha == comparison['candidate_apk_sha256'], 'Wrong archived candidate identity')

    def equal_difference(actual, old, new, fields):
        expected = {key: {'candidate': old[key], 'final': new[key],
                          'finalMinusCandidate': new[key] - old[key]} for key in fields}
        need(actual == expected, 'Descriptive candidate/final values differ from raw validated inputs')

    old_raw = archived('Android/Cascade/measure/Report.json')
    old_install = archived('Android/Cascade/measure/Installation.json')
    need(old_install['apk_sha256'] == old_install['installed_apk_sha256'] == candidate_sha
         and old_install['serial'] == 'emulator-5556' and old_install['data_unchanged'],
         'Archived candidate cascade identity/data guard failed')
    baseline_raw = read('Android/Cascade/measure/Report.json', BASE)
    hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in baseline_raw['rows']}
    old_profile = PROFILE_CONTRACT['validate'](old_raw, 'measure', hashes)
    need(old_raw['repeats'] == 1 and len(comparison['cascade']) == 6, 'Candidate comparison cascade scope changed')
    old_rows = {r['name']: r for r in old_profile['rows']}
    for actual, new in zip(comparison['cascade'], profiling['rows']):
        old = old_rows[new['name']]
        need(actual['name'] == new['name'], 'Candidate comparison case order differs')
        equal_difference(actual['command'], old, new, ['legalSearchMs', 'fixtureSetupMs', 'modelMs', 'acceptMs', 'commandMs',
                         'queueInspectionMs', 'totalSynchronousProbeMs', 'firstCommandRenderMs', 'commandFrameAfterUpdateElapsedMs'])
        equal_difference(actual['enqueue'], old['enqueueCost'], new['enqueueCost'], PROFILE_CONTRACT['COMMAND_STAGES'])
        for key in ['medianRenderStageMs', 'maxRenderStageMs']:
            equal_difference(actual[key], old[key], new[key], PROFILE_CONTRACT['FRAME_STAGES'])
        equal_difference(actual['resourceActivity'], old, new, ['geometryMisses', 'meshSlotsCreated'])
        equal_difference({'maxIntervalMs': actual['maxIntervalMs']}, old, new, ['maxIntervalMs'])
    old_fluidity = archived('Android/Fluidity/Measurement.json')
    old_fluidity_install = archived('Android/Fluidity/Installation.json')
    need(old_fluidity_install.get('apk_sha256', old_fluidity_install.get('sha256')) == candidate_sha
         and old_fluidity['launchCleared'] and old_fluidity['isolatedProfile']
         and len(comparison['fluidity']) == len(old_fluidity['phases']) == 8, 'Candidate fluidity scope/identity changed')
    old_phases = {r['name']: r for r in old_fluidity['phases']}
    for actual, new in zip(comparison['fluidity'], fluidity['phases']):
        old = old_phases[new['name']]
        need(actual['name'] == new['name'], 'Candidate fluidity case order differs')
        equal_difference(actual['metrics'], old, new, ['modelMs', 'acceptMs', 'commandMs', 'firstPresentationMs',
                         'preparationSeconds', 'settleSeconds', 'p95Ms', 'worstMs', 'spriteCreates', 'synchronousTextureLoads',
                         'gen0Collections', 'poolAtReady', 'poolAtEnd', 'peakCachedSprites', 'bankSpriteHighWater'])
        need(actual['additionalFirstUseFields'] == {
            'candidate': {k: v for k, v in old.items() if 'warm' in k.lower()},
            'final': {k: v for k, v in new.items() if 'warm' in k.lower()}}, 'Candidate preparation diagnostics differ')
    missing = []
    for family in ['crate', 'stone', 'gate', 'tiles']:
        folder = 'Android/Density/candidate_review-' + family + '/'
        if not (OUT / 'BeforeCPURefinement' / folder / 'Report.json').is_file():
            missing.append(family)
            continue
        old_raw = archived(folder + 'Report.json')
        old_install = archived(folder + 'Installation.json')
        need(old_install['apk_sha256'] == old_install['installed_apk_sha256'] == candidate_sha,
             'Candidate density identity differs')
        baseline_raw = read(folder + 'Report.json', BASE)
        hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in baseline_raw['rows']}
        old_rows = {r['name']: r for r in PROFILE_CONTRACT['validate_density'](old_raw, family, hashes)['rows']}
        old_native = {r['name']: r for r in old_raw['rows']}
        new_native = {r['name']: r for r in read(folder + 'Report.json')['rows']}
        need(len(comparison['density'][family]) == 10, 'Candidate density coverage differs')
        for actual, new in zip(comparison['density'][family], density_profiling[family]['rows']):
            old = old_rows[new['name']]
            need(actual['name'] == new['name'], 'Candidate density case order differs')
            equal_difference(actual['command'], old, new, ['modelMs', 'acceptMs', 'commandMs'])
            equal_difference(actual['enqueue'], old['enqueueCost'], new['enqueueCost'], PROFILE_CONTRACT['COMMAND_STAGES'])
            equal_difference({'preparationSeconds': actual['preparationSeconds']}, old_native[new['name']],
                             new_native[new['name']], ['preparationSeconds'])
            for key in ['medianRenderStageMs', 'maxRenderStageMs']:
                equal_difference(actual[key], old[key], new[key], PROFILE_CONTRACT['FRAME_STAGES'])
            equal_difference(actual['resourceActivity'], old, new, ['geometryMisses', 'meshSlotsCreated'])
            need(actual['worstRenderMs'] == {'candidate': old['worstRenderFrame']['cost']['renderMs'],
                                            'final': new['worstRenderFrame']['cost']['renderMs']},
                 'Candidate density worst-frame provenance differs')
    need(set(comparison['density']) == set(density_profiling) - set(missing)
         and comparison['unavailableDensityComparisons'] == {'candidateNotRecorded': missing, 'finalNotReady': []},
         'Candidate density availability is overstated')
    need(comparison['repeatedFinalControl'] is None,
         'Embedded repeat comparison requires an explicit additional raw-control contract')
    return comparison


def main(publish=True):
    baseline = read('Baseline_73.json')
    baseline_source_path = file(baseline['source_manifest'], ROOT)
    baseline_source = json.loads(baseline_source_path.read_text('utf-8-sig'))['files']
    baseline_summary = read('Summary.json', BASE)
    baseline_artifact = read('APK_Artifact.json', BASE)
    need(baseline['checkpoint'] == 73 and sha(baseline_source_path) == baseline['source_manifest_sha256']
         and sha(file('Summary.json', BASE)) == baseline['summary_sha256']
         and sha(file('APK_Artifact.json', BASE)) == baseline_summary['evidence_sha256']['APK_Artifact.json'], 'Historical73 manifests changed')
    need(baseline_summary['status'] == 'PASS_CONSERVATIVE_LOCAL_HANDOFF_WITH_REMAINING_GAMEPLAY_GATES'
         and baseline_summary['source_sha256'] == baseline['source_manifest_sha256'], 'Invalid checkpoint73 baseline')
    for name in ['Timing_Visual_Notes.json', 'Native/ModelPerfChecks.json', 'Native/LocalCascade.json',
                 'Native/CascadeTiming.json', 'Android/Cascade/measure/Report.json',
                 'Android/Cascade/visual/Report.json'] + [
                     'Android/Density/candidate_review-' + family + '/Report.json'
                     for family in ['crate', 'stone', 'gate', 'tiles']]:
        need(sha(file(name, BASE)) == baseline_summary['evidence_sha256'][name],
             'Checkpoint73 comparison evidence changed: ' + name)
    old_apk = file(baseline['apk_path'], ROOT)
    need(sha(old_apk) == baseline['apk_sha256'] == baseline_artifact['sha256'] == baseline_summary['apk_sha256']
         and old_apk.stat().st_size == baseline['apk_bytes'] == baseline_artifact['bytes'], 'Archived73 APK differs')

    freeze = read('Source_SHA256.json')
    current = freeze['files']
    inventory = {p.relative_to(ROOT).as_posix() for name in ['Unity/Assets', 'Unity/Packages', 'Unity/ProjectSettings']
                 for p in (ROOT / name).rglob('*') if p.is_file()}
    need(inventory == set(current) and all(sha(ROOT / p) == h for p, h in current.items()), 'Final source freeze differs')
    changed = {p for p in baseline_source if p in current and baseline_source[p] != current[p]}
    added, removed = set(current) - set(baseline_source), set(baseline_source) - set(current)
    delta = read('Source_Delta.json')
    need(delta['baseline'] == 73 and changed == set(delta['changed_existing'])
         and added == set(delta['added']) and removed == set(delta['removed']), 'Stale74 source delta')
    need(changed == ALLOWED_CHANGED
         and added == ADDED and not removed, 'Unreviewed runtime, data, metadata or SDK change')
    for path in changed:
        archived = file(baseline['archived_csharp_sources'][path], ROOT)
        need(sha(archived) == baseline_source[path], 'Original73 source archive differs: ' + path)
    need(all(current[p] == h for p, h in baseline_source.items() if p not in changed),
         'Authored data/artwork/configuration/previous metadata changed')
    old_guids = {m.group(1) for p in baseline_source if p.endswith('.meta')
                 for m in [re.search(r'^guid: ([0-9a-f]{32})$', (ROOT / p).read_text('utf-8-sig'), re.M)] if m}
    new_guids = set()
    for path in added:
        if path.endswith('.meta'):
            match = re.search(r'^guid: ([0-9a-f]{32})$', (ROOT / path).read_text('utf-8-sig'), re.M)
            need(match and match.group(1) not in old_guids | new_guids, 'Invalid/duplicate new GUID: ' + path)
            new_guids.add(match.group(1))

    build, process = read('Android_Build.json'), read('AndroidBuild_Process.json')
    clean(build, 'Android build')
    need(build['status'] == 'PASS_ANDROID_DEVELOPMENT_BUILD' and build['unity'] == '2022.3.62f3'
         and process['exitCode'] == 0 and not process.get('timedOut')
         and utc(freeze['utc']) <= utc(process['startedUtc']), 'Final native Android build failed/stale')
    build_finished = utc(process['finishedUtc'])
    release, release_process = read('Android_Release_Build.json'), read('AndroidReleaseBuild_Process.json')
    release_artifact = read('Release_APK_Artifact.json')
    clean(release, 'Non-development Android compile/build')
    need(release['status'] == 'PASS_ANDROID_RELEASE_COMPILE_BUILD' and release['unity'] == '2022.3.62f3'
         and release['errors'] == 0 and release_process['exitCode'] == 0 and not release_process.get('timedOut')
         and utc(freeze['utc']) <= utc(release_process['startedUtc']) <= utc(release_process['finishedUtc'])
         <= utc(process['startedUtc']), 'Non-development compilation failed/stale')
    release_sources = read(release_artifact['sourceManifest'])
    need(release_sources['files'] == current
         and sha(file(release_artifact['sourceManifest'])) == release_artifact['sourceSHA256'],
         'Non-development build was not bound to the final source')
    release_apk = file(release_artifact['path'], ROOT)
    need(sha(release_apk) == release_artifact['sha256'] and release_apk.stat().st_size == release_artifact['bytes'] > 0,
         'Non-development build artifact changed')
    need('Errors: 0' in file('Release_Build_Import_Audit.txt').read_text('utf-8-sig'), 'Non-development import guard failed')
    artifact, packaging = read('APK_Artifact.json'), read('APK_Packaging.json')
    digest = sha(APK)
    need(digest == artifact['sha256'] == packaging['afterSHA256'] and digest != baseline['apk_sha256'],
         'Final74 APK identity differs or is still73')
    need(APK.stat().st_size == artifact['bytes'] == packaging['afterBytes']
         and all(artifact[k] for k in ['zipalign4KiBPass', 'developmentSignatureVerifies', 'elf16KiBLoadSegmentsPass'])
         and packaging['status'] == 'PASS_CLEAN_GRADLE_APK_PACKAGING'
         and packaging['sameSignerCertificate'] and not packaging['changedNonSignatureEntries'], 'APK packaging checks fail')
    need('Errors: 0' in file('Build_Import_Audit.txt').read_text('utf-8-sig'), 'Import guard failed')

    native = {}
    for mode, status in NATIVE.items():
        report, run = read('Native/' + mode + '.json'), read('Native/' + mode + '_Process.json')
        clean(report, mode)
        need(report['status'] == status and run['exitCode'] == 0 and not run.get('timedOut')
             and utc(baseline_summary['utc']) <= utc(run['startedUtc']) <= utc(report['utc'])
             <= utc(run['finishedUtc']) <= build_finished, mode + ' is stale or failed')
        sources = read(run['sourceManifest'])
        need(sources['files'] == current and sha(file(run['sourceManifest'])) == run['sourceSHA256'],
             mode + ' was not executed against the final source')
        need(BASE_CONTRACT['checks'](report) > 0, mode + ' ran no checks')
        native[mode] = report
    local = native['LocalCascade']
    need(local['modelCases'] == len(local['rows']) == 350 and local['mixedCases'] == 30
         and local['rawTurnParity'] and local['finalSnapshotParity'] and local['acceptedHandoffs'] > 0
         and local['guardCases'] >= 14, 'Local handoff/model/fallback coverage incomplete')
    for row in local['rows']:
        need(row['turnHash'] == row['sequentialTurnHash'] == row['refinedTurnHash']
             and row['finalHash'] == row['sequentialFinalHash'] == row['refinedFinalHash'], 'Raw model/hash parity failed: ' + row['name'])
        need(row['accepted'] in [0, 1] and 0 < row['refinedSeconds'] <= row['sequentialSeconds'] + .0001,
             'Invalid local schedule: ' + row['name'])
    renderers = local['rendererRows']
    need(renderers and any(row['caseName'] == 'L4_match' for row in renderers), 'Actual L4 renderer proof missing')
    need(all(row['samples'] > 0 and row['carryCount'] > 0 and row['secondsSaved'] > 0
             and row['residualLocalWait'] >= 0 and row['maxBoundaryPositionJump'] < .001
             and row['maxBoundaryScaleJump'] < .001 for row in renderers), 'Body/route/landing continuity failed')
    need(local['plannerTimings'] and all(row['iterations'] > 0 for row in local['plannerTimings']), 'Planner CPU diagnostics absent')
    old_commands = read('Native/ModelPerfChecks.json', BASE)['commands']
    old_hashes = {row['name']: (row['turnSHA256'], row['finalSHA256']) for row in old_commands}
    new_hashes = {row['name']: (row['turnSHA256'], row['finalSHA256']) for row in native['ModelPerfChecks']['commands']}
    need(old_hashes == new_hashes, 'Authored command results differ from final73')
    need(native['MixedSwapChecks']['protectedBirths'] == 360 and native['MixedSwapChecks']['chainedBirths'] == 0,
         'Newborn protection regressed')
    cascade_native = native['CascadeTiming']
    need(len(cascade_native['rows']) == 350, 'Cascade15/30/60 native coverage incomplete')
    old_local = read('Native/LocalCascade.json', BASE)
    old_model_hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old_local['rows']}
    need({r['name']: (r['turnHash'], r['finalHash']) for r in local['rows']} == old_model_hashes,
         'Existing350 model command outcomes differ from checkpoint73')
    continuation = native['LocalContinuation']
    need(continuation['modelCases'] == len(continuation['rows']) == 350
         and continuation['mixedCases'] == 30 and continuation['existingChainCases'] == 4
         and continuation['guardCases'] >= 24 and continuation['acceptedHandoffs'] > 0
         and continuation['rawTurnParity'] and continuation['finalSnapshotParity'],
         'Local continuation/model/fallback coverage incomplete')
    for row in continuation['rows']:
        need((row['sequentialTurnHash'], row['sequentialFinalHash']) == old_model_hashes[row['name']]
             == (row['refinedTurnHash'], row['refinedFinalHash']),
             'Continuation changed raw model result: ' + row['name'])
        need(row['accepted'] in [0, 1] and 0 < row['refinedSeconds'] <= row['checkpoint73Seconds'] + .0001
             <= row['sequentialSeconds'] + .0002, 'Continuation schedule grows: ' + row['name'])
    continued_renderers = continuation['rendererRows']
    need(any(row['caseName'] == 'L4_confirmation' for row in continued_renderers)
         and all(row['continuedCount'] > 0 and row['poseSamples'] > 0 and row['routeSamples'] > 0
                 and row['collisionSamples'] > 0 and row['secondsSavedVs73'] > 0
                 and row['minimumColumnClearance'] >= .90
                 and row['maxBoundaryPositionJump'] < .001 and row['maxBoundaryScaleJump'] < .001
                 for row in continued_renderers), 'Continuation body/route/landing/column continuity incomplete')
    legal = native['LegalSwapExistence']
    need(legal['boards'] == 50 and legal['naturalCommands'] == 50 and legal['powerCommands'] == 300
         and legal['toolCommands'] == 200 and legal['guardCases'] >= 13
         and len(legal['rows']) >= 913 and len(legal['timings']) >= 52,
         'Legal-swap parity, command/state or CPU coverage incomplete')
    need(all(row['exists'] == (row['legalSwaps'] > 0) for row in legal['rows']), 'Legal action existence differs')
    need({'guard/no_legal_move', 'guard/failed_shuffle', 'guard/golden_golden', 'guard/rejected_combo',
          'guard/multiple_matching_choices', 'guard/Engine fault', 'guard/zero_budget'}
         <= {row['name'] for row in legal['rows']}, 'Critical existence/terminal controls absent')
    need(legal['baselineModelCases'] == len(legal['modelParity']) == 350
         and legal['baselineRawTurnParity'] and legal['baselineFinalSnapshotParity']
         and Path(legal['baselineReportPath']).resolve() == (BASE / 'Native/LocalCascade.json').resolve()
         and legal['baselineReportSHA256'] == sha(file('Native/LocalCascade.json', BASE)),
         'Optimized model does not bind exact350 archived73 command outcomes')
    for row in legal['modelParity']:
        need((row['turnHash'], row['finalHash']) == (row['archivedTurnHash'], row['archivedFinalHash'])
             == old_model_hashes[row['name']], 'Lazy gravity/model changed archived result: ' + row['name'])
    need(legal['gravityCases'] == 9 and len(legal['gravityRows']) == 27
         and all(row['legacyResultHash'] == row['optimizedResultHash']
                 and row['legacySteps'] == row['optimizedSteps'] and row['checkpointHash']
                 for row in legal['gravityRows'])
         and legal['gravityTimings'] and all(row['iterations'] > 0 for row in legal['gravityTimings']),
         'Lazy gravity snapshot, dictionary/RNG or no-op proof incomplete')
    effects = native['EffectBatchChecks']
    need(effects['preparedDifferingPixels'] == 0 and effects['preparedMaxChannelDelta'] == 0
         and effects['authoredPreparationPlans'] == 50 and 1 <= effects['largestPreparationLevel'] <= 50
         and effects['largestPlannedFrames'] > 0 and effects['futurePressureSprites'] == 1400,
         'Prepared effects change pixels or lack largest-board/cache-headroom proof')
    need(effects['interleavedWarmupYields'] > 0 and effects['interleavedCommonRetained'] == 352
         and effects['interleavedSpriteEvictions'] == 0
         and effects['historicalCapCommonRetained'] < 352 and effects['historicalCapSpriteEvictions'] > 0,
         'Pinned-budget coroutine/frame-end race lacks a passing native control/counterexample')
    warmup = native['WarmupChecks']
    need(warmup['largestWarmupLevel'] == effects['largestPreparationLevel'] == 30
         and warmup['largestCommonCaptured'] == warmup['largestCommonRetained'] == 352
         and warmup['largestWarmupFrames'] > 1 and warmup['largestReadySpriteEvictions'] == 0,
         'Actual PlayMode largest-board readiness lost original common sprite identities')
    prepared = {row['name']: row for row in effects['preparationRows']}
    need({'approved_peak', 'snapshot_replay_and_slot_fallback', 'geometry_headroom',
          'largest_authored_level_' + str(effects['largestPreparationLevel'])} <= set(prepared)
         and all(0 <= row['preparedGeometry'] <= 2048 and 0 <= row['preparedSlots'] <= 32
                 and row['batches'] > 0 and row['yields'] >= 0
                 and row['milliseconds'] >= row['maxBatchMilliseconds'] > 0
                 for row in prepared.values())
         and prepared['snapshot_replay_and_slot_fallback']['firstReplayGeometryMisses'] == 0,
         'Preparation residency, real-work batching or first cached replay proof incomplete')
    old_gap = read('Timing_Visual_Notes.json', BASE)['localMatch']['contactToReactionBoundMs']

    before = read('Android/Before.json')
    need({p.name.removesuffix('_Data_Audit.json') for p in (OUT / 'Android').glob('*_Data_Audit.json')} == TOOLS,
         'Not all nine final74 Android tools completed')
    for tool in TOOLS:
        audit = read('Android/' + tool + '_Data_Audit.json')
        need(audit['serial'] == 'emulator-5556' and audit['apk_sha256'] == digest and audit['exit_code'] == 0
             and utc(audit['utc']) >= build_finished, tool + ' belongs to an older APK or failed')
        preserved(audit, before, tool)
    # Early --out tooling emitted flat stage folders. A pure relocation may be
    # retained only with the original byte hashes; canonical schemas stay fixed.
    for path in sorted(OUT.glob('*Layout_Normalization*.json')):
        normalization = read(path.name)
        need(normalization['bytes_unchanged'] is True and normalization['files'],
             'Evidence layout normalization has no byte-preservation proof')
        for moved in normalization['files']:
            need(moved['canonical_path'].startswith('Android/')
                 and sha(file(moved['canonical_path'])) == moved['sha256'],
                 'Normalized Android evidence changed: ' + moved['canonical_path'])
    fluidity_install = installation('Android/Fluidity/Installation.json', digest, build_finished)
    fluidity = read('Android/Fluidity/Measurement.json')
    clean(fluidity, 'Fluidity')
    need(fluidity['status'] == 'RECORDED_NATIVE_FLUIDITY' and fluidity['isolatedProfile'] and fluidity['launchCleared']
         and len(fluidity['phases']) == 8 and utc(fluidity['utc']) >= utc(fluidity_install['utc']), 'Fluidity74 incomplete')
    touch = read('Android/Touch/Report.json')
    need(touch['apk_sha256'] == digest and touch['serial'] == 'emulator-5556'
         and {row['mode'] for row in touch['cases']} == TOUCH and len(touch['cases']) == 8, 'Touch74 incomplete')
    for row in touch['cases']:
        clean(row, row['mode'])
        need(row['status'] == 'PASS_NATIVE_DEVICE_GAMEPLAY_AUDIT' and row['launchCleared'] and row['accepted'], 'Touch rejected/hidden')
        if row['mode'] in MIXED:
            need(row['sourceActivated'] and row['protectedBirth'] and not row['chained'], 'Power protection failed on74')
        need(sha(file('Android/Touch/' + row['mode'] + '_Before.png')) != sha(file('Android/Touch/' + row['mode'] + '_After.png')),
             'Touch74 unchanged/obscured screenshots')
    cascade, profiling = {}, {}
    for variant, count in [('measure', 6), ('visual', 1)]:
        installation('Android/Cascade/' + variant + '/Installation.json', digest, build_finished, before)
        report = read('Android/Cascade/' + variant + '/Report.json')
        clean(report, 'Cascade ' + variant)
        need(report['status'] == 'PASS_CASCADE_PLAYBACK' and len(report['rows']) == count
             and report.get('repeats') == 1, 'Default nine-stage Cascade74 evidence incomplete')
        cascade[variant] = report
        old = read('Android/Cascade/' + variant + '/Report.json', BASE)
        old_hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
        profiling[variant] = PROFILE_CONTRACT['validate'](report, variant, old_hashes)
    density_profiling = {}
    for family in ['crate', 'stone', 'gate', 'tiles']:
        folder = 'Android/Density/candidate_review-' + family + '/'
        installation(folder + 'Installation.json', digest, build_finished, before)
        report = read(folder + 'Report.json')
        clean(report, family)
        need(report['status'] == 'PASS_OBSTACLE_DENSITY_PLAYBACK' and report['family'] == family and len(report['rows']) == 10,
             'Density74 incomplete')
        old = read(folder + 'Report.json', BASE)
        old_hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
        need({r['name']: (r['turnHash'], r['finalHash']) for r in report['rows']} == old_hashes,
             'Density model changed from final73')
        density_profiling[family] = PROFILE_CONTRACT['validate_density'](report, family, old_hashes)
    repeats = repeat_profiles(digest, build_finished, before)
    comparison = candidate_comparison(digest, profiling['measure'], density_profiling, fluidity)
    repeat_rows = [dict(row, process=entry['process'])
                   for entry in repeats['profiles'] for row in entry['profile']['rows']]
    repeat_first = max((r for r in repeat_rows if r['baseCase'].startswith('L4_0_') and r['repeatIndex'] == 0),
                       key=lambda r: r['commandMs'])
    repeat_later = max((r for r in repeat_rows if r['baseCase'].startswith('L4_0_') and r['repeatIndex'] > 0),
                       key=lambda r: r['commandMs'])
    performance_gates = {
        'default_max_command': {k: v for k, v in max(profiling['measure']['rows'], key=lambda r: r['commandMs']).items()
                                if k in ['name', 'baseCase', 'modelMs', 'acceptMs', 'commandMs']},
        'repeated_first_pass_L4_max_command': {k: repeat_first[k] for k in ['process', 'name', 'commandMs']},
        'repeated_later_pass_L4_max_command': {k: repeat_later[k] for k in ['process', 'name', 'commandMs']},
        'fluidity_orb_rocket_p95_ms': next(r['p95Ms'] for r in fluidity['phases'] if r['name'] == 'orb_rocket'),
        'scope': 'Descriptive measured open performance gates. These commands exceed a single60fps frame; '
                 'repeated fresh banks isolate neither a causal optimization nor cold-device conditions. '
                 'The development timers add overhead; native Render completion is not displayed-pixel latency.'}
    reg_install = installation('Android/Regression/Installation.json', digest, build_finished)
    regression = read('Android/Regression/Regression.json')
    clean(regression, 'Full regression74')
    need(regression['status'] == 'PASS_NATIVE_REGRESSION' and regression['boards'] == 50 and regression['clips'] >= 354
         and regression['checks'] >= 1716 and regression['labels'] >= 14105
         and regression['actions'] >= 408 and len(regression['damageFamilies']) == 8
         and utc(regression['utc']) >= utc(reg_install['utc']), 'Full50-board Android regression74 incomplete')
    need({'Native refill button spends 900 and fills all five lives', 'Repeated native refill callback charges exactly once',
          'Confirmed decline charges exactly one life, no coins, and opens retry pre-level'}.issubset(regression['passed']),
         'Life/Continue settlement device controls missing on74')

    # Final visual contracts are supplied by actual post-build inspection, never this collector.
    review = bound_visual('Visual_Review.json', 'REVIEWED_VISIBLE_ANDROID_GAMEPLAY74', digest)
    tool_review = bound_visual('RegressionVisual/Power_Tool_Review.json',
                              'REVIEWED_FINAL_ANDROID_POWER_PAIRS_AND_TOOLS_WITH_OPEN_GAMEPLAY_GATES', digest)
    visual_manifest = read('RegressionVisual/Manifest.json')
    tool_originals = {'Android/Regression/' + p for group in ['PowerPairs', 'TilesTools']
                      for p in visual_manifest['groups'][group]}
    tool_sheets = {'RegressionVisual/' + group + '_' + str(n).zfill(2) + '.png'
                   for group, count in [('PowerPairs', 5), ('TilesTools', 3)] for n in range(1, count + 1)}
    full_tool_originals = {'Android/Regression/Pair_11_4_False_False_Settled.png',
                          'Android/Regression/L1_Tool2_Settled.png'}
    method = tool_review['inspection_method']
    need(tool_review['sourceCheckpoint'] == 74 and tool_review['apk_bytes'] == artifact['bytes']
         and set(method['contact_sheets']) == tool_sheets
         and set(method['constituent_originals']) == tool_originals
         and set(method['full_originals_also_inspected']) == full_tool_originals
         and tool_originals | tool_sheets <= set(tool_review['artifactSHA256'])
         and not tool_review['new_confirmed_rendering_discrepancies']
         and tool_review['remaining_gameplay_defects'], 'Final74 power-pair/tool inspection incomplete or failed')
    need(tool_review['capture_counts'] == {
        'power_pairs': len(visual_manifest['groups']['PowerPairs']),
        'tiles_tools': len(visual_manifest['groups']['TilesTools']),
        'sheets': len(tool_sheets), 'full_originals': len(full_tool_originals)}, 'Power/tool counts do not match inspected sources')
    for level in [1, 50]:
        for tool in range(4):
            prefix = 'Android/Regression/L' + str(level) + '_Tool' + str(tool)
            need(prefix + '_Settled.png' in tool_originals
                 and any(path.startswith(prefix + '_Effect_') for path in tool_originals),
                 'Tool inspection omits action/settled images: ' + prefix)
    power_review = bound_visual('Power_Visual_Notes.json', 'REVIEWED_VISIBLE_ANDROID_POWER_PROTECTION', digest)
    need(power_review['sourceCheckpoint'] == 74 and power_review['baselineOnly'] is False
         and power_review['currentFinalAPKCertified'] is True and len(power_review['cases']) == 6
         and {row['mode'] for row in power_review['cases']} == MIXED,
         'Power visual review is not the six final74 gestures')
    need(all(row['sourceActivated'] and row['protectedBirth'] and row['launchCleared'] and not row['chained']
             and row['creationPoseKeys'] and row['lastRewardPose']['phase'] == 'idle'
             for row in power_review['cases']), 'Final74 visual power survival is incomplete')
    need(all('Android/Touch/' + mode + '.mp4' in power_review['artifactSHA256']
             and 'Android/Touch/' + mode + '_Report.json' in power_review['artifactSHA256'] for mode in MIXED),
         'Power visual review does not bind all six current movies/reports')
    timing = bound_visual('Timing_Visual_Notes.json', 'REVIEWED_LOCAL_CONTINUATION74_WITH_REMAINING_GATES', digest)
    need(timing.get('remainingGates') and timing.get('localMatch'), 'Timing review omits residual gates/local measurement')
    match = timing['localMatch']
    new_gap = match['contactToReactionBoundMs']
    need(match['case'] == 'L4_0_30' and len(new_gap) == 2 and 0 <= new_gap[0] <= new_gap[1]
         and match['baselineContactToReactionBoundMs'] == old_gap, 'Visible local bounds are not comparable to73')
    need(new_gap[1] < old_gap[0], 'Visible local reaction improvement is not resolved beyond baseline sampling bounds')
    swap = timing['acceptedSwap']
    onset, completion = swap['onsetBracketPts'], swap['completionBracketPts']
    need(onset == [swap['lastStationaryPts'], swap['firstDisplacedPts']]
         and completion == [swap['intermediateProgressPts'][-1], swap['firstOppositeCellCentersPts']]
         and onset[0] < onset[1] < completion[0] < completion[1] < swap['confirmingPosePts']
         and swap['intermediateProgressPts'] == sorted(swap['intermediateProgressPts'])
         and all(onset[1] < p < completion[1] for p in swap['intermediateProgressPts'])
         and swap['visibleDurationBoundMs'] == [round((completion[0] - onset[1]) * 1000, 3),
                                                round((completion[1] - onset[0]) * 1000, 3)]
         and swap['observedFirstMovingToFirstCompleteSampleIntervalMs'] == round((completion[1] - onset[1]) * 1000, 3)
         and swap['visibleDurationBoundMs'][0] <= swap['nativeScheduledMs'] == 120 <= swap['visibleDurationBoundMs'][1],
         'Accepted swap duration does not conservatively bracket both sampled endpoints')
    analysis = bound_visual('Timing_Analysis.json', 'ANALYZED_LOCAL_CONTINUATION74_WITH_REMAINING_GATES', digest)
    need(analysis.get('remainingGates') and analysis['localMatch'] == match
         and analysis['acceptedSwap'] == swap
         and analysis['analyzerSHA256'] == sha(Path(__file__).with_name('analyze_gameplay74_timing.py'))
         and analysis['profilingValidatorSHA256'] == sha(Path(__file__).with_name('validate_gameplay74_profile.py'))
         and set(timing['remainingGates']) <= set(analysis['remainingGates'])
         and analysis['nativeLocalHandoff'] == continued_renderers
         and analysis['counts'] == {'fluidity': 8, 'cascadeMeasure': len(cascade['measure']['rows']), 'cascadeVisual': 1,
                                    'density': 40, 'nativeModelCases': 350},
         'Timing analysis drops remaining gates or does not match final source measurements')

    result = {
        'status': 'PASS_TARGETED_GAMEPLAY74_WITH_REMAINING_PERFORMANCE_GATES',
        'utc': datetime.now(timezone.utc).isoformat(), 'source_checkpoint': 74,
        'source_inputs': len(current), 'source_sha256': sha(file('Source_SHA256.json')),
        'baseline_checkpoint': 73, 'baseline_apk_sha256': baseline['apk_sha256'],
        'apk_sha256': digest, 'apk_bytes': artifact['bytes'],
        'non_development_compile_build_passed': True, 'non_development_apk_installed': False,
        'native_suites': len(native), 'native_checks': sum(BASE_CONTRACT['checks'](r) for r in native.values()),
        'raw_turn_and_final_hash_parity': True, 'native_model_cases': 350, 'native_mixed_cases': 30,
        'native_accepted_handoffs': continuation['acceptedHandoffs'], 'native_guard_cases': continuation['guardCases'],
        'checkpoint73_control_guard_cases': local['guardCases'],
        'renderer_continuity_cases': len(continued_renderers),
        'legal_swap_existence_states': len(legal['rows']),
        'lazy_gravity_reference_cases': legal['gravityCases'],
        'prepared_effect_geometry_cases': len(prepared),
        'prepared_effect_pixels_identical': effects['preparedMaxChannelDelta'] == 0,
        'pinned_budget_race': {'largest_level': warmup['largestWarmupLevel'],
                              'actual_playmode_common_sprites_retained': warmup['largestCommonRetained'],
                              'actual_playmode_frames': warmup['largestWarmupFrames'],
                              'interleaved_common_sprites_retained': effects['interleavedCommonRetained'],
                              'interleaved_evictions': effects['interleavedSpriteEvictions'],
                              'historical_cap_common_sprites_retained': effects['historicalCapCommonRetained'],
                              'historical_cap_evictions': effects['historicalCapSpriteEvictions']},
        'legal_swap_allocation_counter_usable': legal['allocationCounterUsable'],
        'local_reaction': {'baseline_visible_ms': old_gap, 'final_visible_ms': new_gap,
                           'native_residual_phase_wait_seconds': [r['residualLocalWait'] for r in continued_renderers if r['caseName'] == 'L4_confirmation']},
        'accepted_swap': {'scheduled_ms': swap['nativeScheduledMs'],
                          'visible_duration_bound_ms': swap['visibleDurationBoundMs'],
                          'scope': 'Both visible onset and completion are bracketed between source frames. '
                                   'The first-moving to first-complete sample interval is not the lower duration bound '
                                   'or an input-to-display latency measurement.'},
        'android': {'data_audits': 9, 'touch_cases': 8, 'density_turns': 40,
                    'cascade_timing_cases': len(cascade['measure']['rows']),
                    'separate_process_profile_rows': repeats['rows'],
                    'separate_profile_processes': repeats['processes'],
                    'independently_reviewed_power_movies': 6,
                    'independently_reviewed_power_tool_sheets': len(tool_sheets),
                    'power_tool_sheet_constituent_captures': len(tool_originals),
                    'boards': 50, 'checks': regression['checks'], 'clips': regression['clips'], 'actions': regression['actions']},
        'qa_data_unchanged': True, 'main_apk_updated': False,
        'scope': 'Restricted local presentation continuation, short-circuit legal-swap existence, '
                 'lazy no-op gravity snapshots and bounded preparation of cached effect geometry/disabled mesh slots, '
                 'with raw model/seeded outcomes and rendered pixels preserved. A pinned-sprite budget race is fixed '
                 'before coroutine yields and covered by a352-sprite negative control plus actual largest-board readiness. '
                 'Fresh22-suite native source proof, actual non-development compilation, nine final-APK '
                 'QA Android tools, corrected source-bound command/renderer profiling, original-PTS local reaction '
                 'comparison,36 repeated process-control rows and reviewed route/body/counter continuity. '
                 'At most one qualified continuation per turn; '
                 'unqualified power/advanced-obstacle/overlap cases retain checkpoint73 scheduling.',
        'profiling': profiling['measure'],
        'density_profiling': density_profiling,
        'repeated_process_profiling': {'processes': repeats['processes'], 'rows': repeats['rows'], 'scope': repeats['scope']},
        'descriptive_candidate_final_comparison': {'path': 'Candidate_Final_Profile_Comparison.json',
                                                  'status': comparison['status'],
                                                  'candidate_apk_sha256': comparison['candidate_apk_sha256'],
                                                  'available_density_families': list(comparison['density']),
                                                  'scope': comparison['scope'], 'limits': comparison['limits']},
        'remaining_performance_measurements': performance_gates,
        'reference_scope': 'The direct timing control is the final checkpoint73 capture of this same seeded app fixture. '
                           'Match Villains comparisons remain archived observations with original sampling/version limits; '
                           'no fresh reference gameplay, identical-board physics, or competitor parity is established.',
        'remaining_gameplay_defects': analysis['remainingGates'],
        'limits': ['The measured local wait is reduced in the verified fixture; residual delays and fallback cases remain.',
                   'Measured default/repeated command spikes and Orb+Rocket frame pacing remain open; '
                   'the targeted fixes do not establish smooth gameplay throughout every power/obstacle combination.',
                   'Effect preparation covers a bounded subset of already-cached common/obstacle frames. '
                   'New power frames still use demand geometry and the existing cache eviction policy; no universal zero-allocation claim.',
                   'Instrumented native CPU spans include per-draw diagnostic overhead and emulator scheduling. '
                   'The historical183ms interval has no exact causality claim.',
                   'No whole-game hitch-free, sustained60fps, physical-device, production billing or fresh competitor parity claim.',
                   'QA only; main retains deployment64. Native deterministic hashes do not certify human campaign balance.'],
        'evidence_sha256': dict(sorted(evidence.items())), 'collector_sha256': sha(Path(__file__)),
        'profiling_validator_sha256': sha(Path(__file__).with_name('validate_gameplay74_profile.py')),
        'cascade_runner_validator_sha256': sha(Path(__file__).with_name('run_cascade_timing_device.py')),
    }
    checkpoint = {'utc': result['utc'], 'status': result['status'], 'source_checkpoint': 74, 'installed_checkpoint': 64,
                  'qa_installed_checkpoint': 74, 'source_sha256': result['source_sha256'],
                  'review': 'Codex_Handoff/Documentation/74_GAMEPLAY_LOCAL_CONTINUATION_AND_CPU_REVIEW.md',
                  'summary': 'Verification/Evidence/Gameplay74/Summary.json', 'android_apk_sha256': digest,
                  'android_apk_matches_current_source': True, 'main_installed_apk_matches_current_source': False,
                  'scope': result['scope']}
    if publish:
        for path, value in [(OUT / 'Summary.json', result), (OUT.parent / 'Verification_Summary.json', result),
                            (OUT.parent / 'Native_Source_Checkpoint.json', checkpoint)]:
            path.write_text(json.dumps(value, indent=2) + '\n', 'utf-8')
    print(json.dumps({k: v for k, v in result.items()
                      if k not in {'evidence_sha256', 'profiling', 'density_profiling'}}, indent=2))


if __name__ == '__main__':
    main()
