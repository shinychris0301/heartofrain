"""Fail-closed checkpoint73 collector; does not build, install, or grant visual approval.

Draft contracts deliberately require fresh proof. A cache-only prototype, old
checkpoint72 device run, or unmeasured gap cannot publish a checkpoint73 pass.
"""
import hashlib
import json
import re
import runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/LocalCascade73'
BASE = ROOT / 'Verification/Evidence/Gameplay72'
APK = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
BASE_CONTRACT = runpy.run_path(str(Path(__file__).with_name('collect_gameplay72_results.py')),
                              run_name='checkpoint72_contract_only')
NATIVE = dict(BASE_CONTRACT['NATIVE_STATUSES']) | {
    'LocalCascade': 'PASS_NATIVE_LOCAL_CASCADE73', 'CascadeTiming': 'PASS_NATIVE_CASCADE_TIMING'}
TOOLS = BASE_CONTRACT['TOOLS']
MIXED = BASE_CONTRACT['MIXED_MODES']
TOUCH = BASE_CONTRACT['TOUCH_MODES']
ALLOWED_CHANGED = {
    'Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPlayback.cs',
    'Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPresentation.cs',
    'Unity/Assets/HeartOfTheRain/Verification/Editor/IndividualFallVerification.cs',
}
REQUIRED_RUNTIME_CHANGED = {p for p in ALLOWED_CHANGED if '/M46/Runtime/' in p}
ADDED = {
    'Unity/Assets/HeartOfTheRain/' + name + suffix for name in [
        'M46/Runtime/LocalCascadePlayback.cs',
        'Verification/Editor/LocalCascadeVerification.cs',
        'Verification/Editor/LocalCascadeRendererChecks.cs',
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
    need(path.is_relative_to(base.resolve()) and not {'Discarded', 'BeforeOnset'} & set(path.parts),
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


def main():
    baseline = read('Baseline_72.json')
    baseline_source_path = file(baseline['source_manifest'], ROOT)
    baseline_source = json.loads(baseline_source_path.read_text('utf-8-sig'))['files']
    baseline_summary = read('Summary.json', BASE)
    baseline_artifact = read('APK_Artifact.json', BASE)
    need(baseline['checkpoint'] == 72 and sha(baseline_source_path) == baseline['source_manifest_sha256']
         and sha(file('Summary.json', BASE)) == baseline['summary_sha256']
         and sha(file('APK_Artifact.json', BASE)) == baseline['artifact_sha256'], 'Historical72 manifests changed')
    need(baseline_summary['status'] == 'PASS_TARGETED_FIXES_WITH_OPEN_GAMEPLAY_GATES'
         and baseline_summary['source_sha256'] == baseline['source_manifest_sha256'], 'Invalid checkpoint72 baseline')
    for name in ['Timing_Visual_Notes.json', 'Native/ModelPerfChecks.json',
                 'Android/Cascade/measure/Report.json', 'Android/Cascade/visual/Report.json']:
        need(sha(file(name, BASE)) == baseline_summary['evidence_sha256'][name],
             'Checkpoint72 comparison evidence changed: ' + name)
    old_apk = file(baseline['apk_path'], ROOT)
    need(sha(old_apk) == baseline['apk_sha256'] == baseline_artifact['sha256'] == baseline_summary['apk_sha256']
         and old_apk.stat().st_size == baseline['apk_bytes'] == baseline_artifact['bytes'], 'Archived72 APK differs')

    freeze = read('Source_SHA256.json')
    current = freeze['files']
    inventory = {p.relative_to(ROOT).as_posix() for name in ['Unity/Assets', 'Unity/Packages', 'Unity/ProjectSettings']
                 for p in (ROOT / name).rglob('*') if p.is_file()}
    need(inventory == set(current) and all(sha(ROOT / p) == h for p, h in current.items()), 'Final source freeze differs')
    changed = {p for p in baseline_source if p in current and baseline_source[p] != current[p]}
    added, removed = set(current) - set(baseline_source), set(baseline_source) - set(current)
    delta = read('Source_Delta.json')
    need(delta['baseline'] == 72 and changed == set(delta['changed_existing'])
         and added == set(delta['added']) and removed == set(delta['removed']), 'Stale73 source delta')
    need(REQUIRED_RUNTIME_CHANGED.issubset(changed) and changed.issubset(ALLOWED_CHANGED)
         and added == ADDED and not removed, 'Unreviewed runtime, data, metadata or SDK change')
    for path in changed:
        archived = file(baseline['archived_csharp_sources'][path], ROOT)
        need(sha(archived) == baseline_source[path], 'Original72 source archive differs: ' + path)
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
    artifact, packaging = read('APK_Artifact.json'), read('APK_Packaging.json')
    digest = sha(APK)
    need(digest == artifact['sha256'] == packaging['afterSHA256'] and digest != baseline['apk_sha256'],
         'Final73 APK identity differs or is still72')
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
    need(old_hashes == new_hashes, 'Authored command results differ from final72')
    need(native['MixedSwapChecks']['protectedBirths'] == 360 and native['MixedSwapChecks']['chainedBirths'] == 0,
         'Newborn protection regressed')
    cascade_native = native['CascadeTiming']
    need(len(cascade_native['rows']) == 350, 'Cascade15/30/60 native coverage incomplete')
    old_gap = read('Timing_Visual_Notes.json', BASE)['verifiedRemainingGap']['observations']['contactToReactionBoundMs']

    before = read('Android/Before.json')
    need({p.name.removesuffix('_Data_Audit.json') for p in (OUT / 'Android').glob('*_Data_Audit.json')} == TOOLS,
         'Not all nine final73 Android tools completed')
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
         and len(fluidity['phases']) == 8 and utc(fluidity['utc']) >= utc(fluidity_install['utc']), 'Fluidity73 incomplete')
    touch = read('Android/Touch/Report.json')
    need(touch['apk_sha256'] == digest and touch['serial'] == 'emulator-5556'
         and {row['mode'] for row in touch['cases']} == TOUCH and len(touch['cases']) == 8, 'Touch73 incomplete')
    for row in touch['cases']:
        clean(row, row['mode'])
        need(row['status'] == 'PASS_NATIVE_DEVICE_GAMEPLAY_AUDIT' and row['launchCleared'] and row['accepted'], 'Touch rejected/hidden')
        if row['mode'] in MIXED:
            need(row['sourceActivated'] and row['protectedBirth'] and not row['chained'], 'Power protection failed on73')
        need(sha(file('Android/Touch/' + row['mode'] + '_Before.png')) != sha(file('Android/Touch/' + row['mode'] + '_After.png')),
             'Touch73 unchanged/obscured screenshots')
    cascade = {}
    for variant, count in [('measure', 6), ('visual', 1)]:
        installation('Android/Cascade/' + variant + '/Installation.json', digest, build_finished, before)
        report = read('Android/Cascade/' + variant + '/Report.json')
        clean(report, 'Cascade ' + variant)
        need(report['status'] == 'PASS_CASCADE_PLAYBACK' and len(report['rows']) == count, 'Cascade73 incomplete')
        cascade[variant] = report
        old = read('Android/Cascade/' + variant + '/Report.json', BASE)
        need({r['name']: (r['turnHash'], r['finalHash']) for r in report['rows']}
             == {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}, 'Device cascade changed final72 model outcome')
    for family in ['crate', 'stone', 'gate', 'tiles']:
        folder = 'Android/Density/candidate_review-' + family + '/'
        installation(folder + 'Installation.json', digest, build_finished, before)
        report = read(folder + 'Report.json')
        clean(report, family)
        need(report['status'] == 'PASS_OBSTACLE_DENSITY_PLAYBACK' and report['family'] == family and len(report['rows']) == 10,
             'Density73 incomplete')
        old = read(folder + 'Report.json', BASE)
        need({r['name']: (r['turnHash'], r['finalHash']) for r in report['rows']}
             == {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}, 'Density model changed from final72')
    reg_install = installation('Android/Regression/Installation.json', digest, build_finished)
    regression = read('Android/Regression/Regression.json')
    clean(regression, 'Full regression73')
    need(regression['status'] == 'PASS_NATIVE_REGRESSION' and regression['boards'] == 50 and regression['clips'] >= 354
         and regression['actions'] >= 408 and len(regression['damageFamilies']) == 8
         and utc(regression['utc']) >= utc(reg_install['utc']), 'Full50-board Android regression73 incomplete')
    need({'Native refill button spends 900 and fills all five lives', 'Repeated native refill callback charges exactly once',
          'Confirmed decline charges exactly one life, no coins, and opens retry pre-level'}.issubset(regression['passed']),
         'Life/Continue settlement device controls missing on73')

    # Final visual contracts are supplied by actual post-build inspection, never this collector.
    review = bound_visual('Visual_Review.json', 'REVIEWED_VISIBLE_ANDROID_LOCAL_CASCADE73', digest)
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
    need(tool_review['sourceCheckpoint'] == 73 and tool_review['apk_bytes'] == artifact['bytes']
         and set(method['contact_sheets']) == tool_sheets
         and set(method['constituent_originals']) == tool_originals
         and set(method['full_originals_also_inspected']) == full_tool_originals
         and tool_originals | tool_sheets <= set(tool_review['artifactSHA256'])
         and not tool_review['new_confirmed_rendering_discrepancies']
         and tool_review['remaining_gameplay_defects'], 'Final73 power-pair/tool inspection incomplete or failed')
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
    need(power_review['sourceCheckpoint'] == 73 and power_review['baselineOnly'] is False
         and power_review['currentFinalAPKCertified'] is True and len(power_review['cases']) == 6
         and {row['mode'] for row in power_review['cases']} == MIXED,
         'Power visual review is not the six final73 gestures')
    need(all(row['sourceActivated'] and row['protectedBirth'] and row['launchCleared'] and not row['chained']
             and row['creationPoseKeys'] and row['lastRewardPose']['phase'] == 'idle'
             for row in power_review['cases']), 'Final73 visual power survival is incomplete')
    need(all('Android/Touch/' + mode + '.mp4' in power_review['artifactSHA256']
             and 'Android/Touch/' + mode + '_Report.json' in power_review['artifactSHA256'] for mode in MIXED),
         'Power visual review does not bind all six current movies/reports')
    timing = bound_visual('Timing_Visual_Notes.json', 'REVIEWED_LOCAL_CASCADE73_WITH_REMAINING_GATES', digest)
    need(timing.get('remainingGates') and timing.get('localMatch'), 'Timing review omits residual gates/local measurement')
    match = timing['localMatch']
    new_gap = match['contactToReactionBoundMs']
    need(match['case'] == 'L4_0_30' and len(new_gap) == 2 and 0 <= new_gap[0] <= new_gap[1]
         and match['baselineContactToReactionBoundMs'] == old_gap, 'Visible local bounds are not comparable to72')
    need(new_gap[1] < old_gap[0], 'Visible local reaction improvement is not resolved beyond baseline sampling bounds')
    analysis = bound_visual('Timing_Analysis.json', 'ANALYZED_LOCAL_CASCADE73_WITH_REMAINING_GATES', digest)
    need(analysis.get('remainingGates') and analysis['localMatch'] == match
         and analysis['nativeLocalHandoff'] == renderers
         and analysis['counts'] == {'fluidity': 8, 'cascadeMeasure': 6, 'cascadeVisual': 1,
                                    'density': 40, 'nativeModelCases': 350},
         'Timing analysis drops remaining gates or does not match final source measurements')

    result = {
        'status': 'PASS_CONSERVATIVE_LOCAL_HANDOFF_WITH_REMAINING_GAMEPLAY_GATES',
        'utc': datetime.now(timezone.utc).isoformat(), 'source_checkpoint': 73,
        'source_inputs': len(current), 'source_sha256': sha(file('Source_SHA256.json')),
        'baseline_checkpoint': 72, 'baseline_apk_sha256': baseline['apk_sha256'],
        'apk_sha256': digest, 'apk_bytes': artifact['bytes'],
        'native_suites': len(native), 'native_checks': sum(BASE_CONTRACT['checks'](r) for r in native.values()),
        'raw_turn_and_final_hash_parity': True, 'native_model_cases': 350, 'native_mixed_cases': 30,
        'native_accepted_handoffs': local['acceptedHandoffs'], 'native_guard_cases': local['guardCases'],
        'renderer_continuity_cases': len(renderers),
        'local_reaction': {'baseline_visible_ms': old_gap, 'final_visible_ms': new_gap,
                           'native_residual_phase_wait_seconds': [r['residualLocalWait'] for r in renderers if r['caseName'] == 'L4_match']},
        'android': {'data_audits': 9, 'touch_cases': 8, 'density_turns': 40, 'cascade_timing_cases': 6,
                    'independently_reviewed_power_movies': 6,
                    'independently_reviewed_power_tool_sheets': len(tool_sheets),
                    'power_tool_sheet_constituent_captures': len(tool_originals),
                    'boards': 50, 'checks': regression['checks'], 'clips': regression['clips'], 'actions': regression['actions']},
        'qa_data_unchanged': True, 'main_apk_updated': False,
        'scope': 'Restricted safe local presentation handoff, with raw model/seeded outcomes preserved. '
                 'Fresh20-suite native source proof, nine final-APK QA Android tools, actual original-PTS local reaction '
                 'comparison and reviewed route/body/counter continuity. One conservative eligible handoff per turn; '
                 'unqualified power/advanced-obstacle/overlap cases retain the sequential fallback.',
        'reference_scope': 'The direct timing control is the final checkpoint72 capture of this same seeded app fixture. '
                           'Match Villains comparisons remain archived observations with original sampling/version limits; '
                           'no fresh reference gameplay, identical-board physics, or competitor parity is established.',
        'remaining_gameplay_defects': timing['remainingGates'],
        'limits': ['The measured local wait is reduced in the verified fixture; residual delays and fallback cases remain.',
                   'No whole-game hitch-free, sustained60fps, physical-device, production billing or fresh competitor parity claim.',
                   'QA only; main retains deployment64. Native deterministic hashes do not certify human campaign balance.'],
        'evidence_sha256': dict(sorted(evidence.items())), 'collector_sha256': sha(Path(__file__)),
    }
    checkpoint = {'utc': result['utc'], 'status': result['status'], 'source_checkpoint': 73, 'installed_checkpoint': 64,
                  'qa_installed_checkpoint': 73, 'source_sha256': result['source_sha256'],
                  'review': 'Codex_Handoff/Documentation/73_LOCAL_CASCADE_OVERLAP_REVIEW.md',
                  'summary': 'Verification/Evidence/LocalCascade73/Summary.json', 'android_apk_sha256': digest,
                  'android_apk_matches_current_source': True, 'main_installed_apk_matches_current_source': False,
                  'scope': result['scope']}
    for path, value in [(OUT / 'Summary.json', result), (OUT.parent / 'Verification_Summary.json', result),
                        (OUT.parent / 'Native_Source_Checkpoint.json', checkpoint)]:
        path.write_text(json.dumps(value, indent=2) + '\n', 'utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'evidence_sha256'}, indent=2))


if __name__ == '__main__':
    main()
