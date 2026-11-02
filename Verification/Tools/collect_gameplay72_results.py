"""Validate checkpoint 72 evidence before publishing its current-source summary.

This collector never launches Unity/ADB or changes the game, saves, or historical
branches. Incomplete, discarded, older-APK, and unreviewed captures fail closed.
"""
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Gameplay72'
APK = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
NATIVE_NOT_BEFORE = datetime.fromisoformat('2026-10-24T15:30:00+00:00')
ONSET_NOT_BEFORE = datetime.fromisoformat('2026-10-24T16:41:00+00:00')
ONSET_RERUN_MODES = {'PlaybackOnset', 'TimingChecks', 'WarmupChecks', 'PlaySmoke'}
NATIVE_STATUSES = {
    'MixedSwapChecks': 'PASS_NATIVE_MIXED_POWER_SWAP',
    'ResourceScan': 'PASS_NATIVE_RESOURCE_SCAN',
    'ProfileChecks': 'PASS_NATIVE_PROFILE_TRANSACTIONS',
    'Checks': 'PASS_NATIVE_EDITOR_CHECKS',
    'TimingChecks': 'PASS_NATIVE_TIMING_CHECKS',
    'IndividualFallChecks': 'PASS_NATIVE_INDIVIDUAL_FALL',
    'FallChecks': 'PASS_NATIVE_OBSTACLE_FALL',
    'SwapChecks': 'PASS_NATIVE_SWAP_CREATION',
    'M70R2Checks': 'PASS_NATIVE_M70R2_CREATION',
    'M70Checks': 'PASS_NATIVE_M70_CHECKS',
    'GameplayAuditChecks': 'PASS_NATIVE_GAMEPLAY_AUDIT_WITH_DIAGNOSTICS',
    'GameplayPerfChecks': 'PASS_NATIVE_GAMEPLAY_PERFORMANCE',
    'ModelPerfChecks': 'PASS_NATIVE_MODEL_COMMANDS',
    'EffectBatchChecks': 'PASS_NATIVE_EFFECT_BATCH',
    'WarmupChecks': 'PASS_NATIVE_PRESENTATION_WARMUP',
    'PlaySmoke': 'PASS_NATIVE_PLAY_SMOKE',
    'HomeLivesUI': 'PASS_NATIVE_HOME_LIVES_R1',
    'PlaybackOnset': 'PASS_NATIVE_PLAYBACK_ONSET',
}
EXPECTED_CHANGED = {
    'Unity/Assets/HeartOfTheRain/' + p for p in [
        'Verification/FluidityDeviceProbe.cs', 'Verification/GameplayAuditTouchProbe.cs',
        'Verification/ObstacleDensityProbe.cs', 'Verification/PlayerRegressionSuite.cs',
        'App/Profile/Runtime/PlayerProfile.cs', 'M46/Runtime/BoardModel.cs',
        'M46/Runtime/LivePowerPlan.cs', 'M47/Runtime/GameplayScreen.cs',
        'M48/Runtime/EffectResourcesPure.cs', 'Verification/Editor/GameplayPerformanceVerification.cs',
        'Verification/Editor/HomeLivesR1Review.cs', 'Verification/Editor/HomeLivesR1Transactions.cs',
        'Verification/Editor/MixedPowerSwapVerification.cs', 'Verification/Editor/NativeVerification.cs',
        'Verification/Editor/ProfileTransactionVerification.cs',
    ]
}
EXPECTED_ADDED = {
    'Unity/Assets/HeartOfTheRain/Verification/Editor/' + name + suffix
    for name in ['ResourceScanVerification.cs', 'PlaybackOnsetVerification.cs'] for suffix in ['', '.meta']
}
MIXED_MODES = {'MixedH', 'MixedV', 'MixedBomb', 'MixedOrb', 'MixedSeeker', 'MixedChain'}
TOUCH_MODES = MIXED_MODES | {'ObstaclePartial', 'ObstacleClear'}
TOOLS = {'Fluidity', 'Touch', 'Cascade', 'CascadeVisual', 'Regression'} | {
    'Density_' + family for family in ['crate', 'stone', 'gate', 'tiles']}
evidence = {}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_path(name, base=OUT):
    path = (base / name).resolve()
    require(path.is_relative_to(base.resolve()) and 'Discarded' not in path.parts,
            'Unsafe/discarded evidence path: ' + str(name))
    require(path.is_file(), 'Missing evidence: ' + str(path))
    return path


def record(name):
    path = artifact_path(name)
    evidence[path.relative_to(OUT).as_posix()] = sha(path)
    return path


def read(name):
    return json.loads(record(name).read_text(encoding='utf-8-sig'))


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def checks(report):
    value = report.get('checks', 0)
    return len(value) if isinstance(value, list) else value


def clean(report, label):
    for key in ['error', 'errors', 'failures']:
        require(not report.get(key), label + ' has ' + key)
    require(not report.get('failed'), label + ' has failed checks')


def preserved(report, before, label):
    require(report.get('data_unchanged') is True and report.get('before') == before
            and report.get('after') == before, label + ' changed/mismatched QA saves')


def install(name, digest, after, before=None):
    report = read(name)
    require(report['serial'] == 'emulator-5556', name + ' is not QA')
    require(report.get('sha256', report.get('apk_sha256')) == digest,
            name + ' belongs to a different APK')
    if 'installed_apk_sha256' in report:
        require(report['installed_apk_sha256'] == digest, name + ' installed APK differs')
    require(utc(report['utc']) >= after, name + ' predates the final build')
    if before is not None:
        preserved(report, before, name)
    if 'runtime_errors' in report:
        require(report['runtime_errors'] == 0, name + ' has runtime errors')
    return report


def visual(name, status, digest):
    report = read(name)
    require(report['status'] == status and report['apk_sha256'] == digest,
            name + ' is unfinished or belongs to a different APK')
    hashes = report['artifactSHA256']
    require(isinstance(hashes, dict) and hashes, name + ' has no reviewed artifacts')
    for filename, expected in hashes.items():
        require('BeforeOnset' not in Path(filename).parts, name + ' uses an earlier APK capture')
        require(sha(record(filename)) == expected, name + ' reviewed artifact changed: ' + filename)
    return report


def percentile(values, share):
    return sorted(values)[max(0, math.ceil(len(values) * share) - 1)]


def main():
    freeze = read('Source_SHA256.json')
    frozen = freeze['files']
    inventory = {p.relative_to(ROOT).as_posix()
                 for folder in ['Unity/Assets', 'Unity/Packages', 'Unity/ProjectSettings']
                 for p in (ROOT / folder).rglob('*') if p.is_file()}
    require(set(frozen) == inventory, 'Unity source inventory differs')
    require(all(sha(ROOT / filename) == expected for filename, expected in frozen.items()),
            'Current Unity source differs from the final build freeze')
    baseline = json.loads((OUT.parent / 'ShopBounds/Source_SHA256.json').read_text('utf-8-sig'))['files']
    delta = read('Source_Delta.json')
    changed = {p for p in baseline if p in frozen and baseline[p] != frozen[p]}
    added, removed = set(frozen) - set(baseline), set(baseline) - set(frozen)
    require(delta['baseline'] == 71 and changed == set(delta['changed_existing'])
            and added == set(delta['added']) and removed == set(delta['removed']), 'Source delta is stale')
    require(changed == EXPECTED_CHANGED and added == EXPECTED_ADDED and not removed,
            'Unexpected source scope')
    require(len(frozen) == len(baseline) + len(EXPECTED_ADDED), 'Final source inventory count differs')
    require(all(p.endswith('.cs') for p in changed), 'Artwork, metadata or project settings changed')
    require(delta['existing_meta_unchanged'] and delta['authored_levels_unchanged'], 'Preservation flags fail')
    before_onset = read('BeforeOnset/Source_SHA256.json')['files']
    retained_native_prefixes = (
        'Unity/Assets/HeartOfTheRain/M46/Runtime/',
        'Unity/Assets/HeartOfTheRain/App/Profile/Runtime/',
        'Unity/Assets/HeartOfTheRain/Verification/Editor/',
    )
    retained_native_inputs = {p for p in before_onset if p.startswith(retained_native_prefixes)}
    retained_native_inputs.add('Unity/Assets/HeartOfTheRain/M48/Runtime/EffectResourcesPure.cs')
    require(all(frozen.get(p) == before_onset[p] for p in retained_native_inputs),
            'Previously verified native model/service/suite source changed after the retained native runs')
    existing_meta = [(ROOT / p).read_text('utf-8-sig') for p in baseline if p.endswith('.meta')]
    new_guids = set()
    for filename in sorted(added):
        if not filename.endswith('.meta'):
            continue
        new_guid = re.search(r'^guid: ([0-9a-f]{32})$', (ROOT / filename).read_text('utf-8-sig'), re.M)
        require(new_guid is not None, 'New verification metadata has no GUID: ' + filename)
        require(new_guid.group(1) not in new_guids and all(new_guid.group(1) not in text for text in existing_meta),
                'New verification GUID duplicates an asset: ' + filename)
        new_guids.add(new_guid.group(1))

    build = read('Android_Build.json')
    process = read('AndroidBuild_Process.json')
    require(build['status'] == 'PASS_ANDROID_DEVELOPMENT_BUILD' and build['errors'] == 0,
            'Native Android build failed')
    require(process['exitCode'] == 0 and not process.get('timedOut'), 'Android build process failed')
    require(build['unity'] == '2022.3.62f3', 'Unity version changed')
    require(utc(freeze['utc']) <= utc(process['startedUtc']), 'APK build predates the final source freeze')
    build_finished = utc(process['finishedUtc'])
    artifact, packaging = read('APK_Artifact.json'), read('APK_Packaging.json')
    digest = sha(APK)
    require(digest == artifact['sha256'] == packaging['afterSHA256'],
            'Final APK identity differs; discarded/earlier APK evidence is not accepted')
    require(digest != read('BeforeOnset/APK_Artifact.json')['sha256'], 'APK still predates the onset-clock fix')
    require(APK.stat().st_size == artifact['bytes'] == packaging['afterBytes'] and artifact['bytes'] > 0,
            'Final APK byte count differs')
    require(all(artifact[k] is True for k in ['zipalign4KiBPass', 'developmentSignatureVerifies',
                                             'elf16KiBLoadSegmentsPass']), 'APK static checks failed')
    require(packaging['status'] == 'PASS_CLEAN_GRADLE_APK_PACKAGING'
            and packaging['sameSignerCertificate'] and not packaging['changedNonSignatureEntries'],
            'Clean packaging altered game entries/signing')
    require('Errors: 0' in record('Build_Import_Audit.txt').read_text('utf-8-sig'), 'Import guard failed')

    native, native_rows = {}, []
    for mode, status in NATIVE_STATUSES.items():
        report, run = read('Native/' + mode + '.json'), read('Native/' + mode + '_Process.json')
        require(report['status'] == status, mode + ' failed')
        clean(report, mode)
        require(run['exitCode'] == 0 and not run.get('timedOut'), mode + ' process failed')
        require(NATIVE_NOT_BEFORE <= utc(run['startedUtc']) <= utc(report['utc'])
                <= utc(run['finishedUtc']) <= build_finished, mode + ' is stale/outside its process window')
        if mode in ONSET_RERUN_MODES:
            require(utc(run['startedUtc']) >= ONSET_NOT_BEFORE, mode + ' predates the onset-clock correction')
        require(checks(report) > 0, mode + ' executed no checks')
        native[mode] = report
        native_rows.append({'mode': mode, 'status': status, 'checks': checks(report)})
    mixed = native['MixedSwapChecks']
    require(mixed['turns'] == mixed['protectedBirths'] == len(mixed['cases']) == 360
            and mixed['chainedBirths'] == 0 and mixed['sourceHitBirthCells'] == 240
            and mixed['existingChainControls'] == 4, 'Mixed-swap survival coverage differs')
    require(all(c['protectedBirth'] and not c['chained'] for c in mixed['cases']), 'A newborn was chained')
    require(native['ModelPerfChecks']['boardModelSHA256'] == frozen['Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs'],
            'Model CPU report refers to different gameplay code')
    require(native['ResourceScan']['authoredTurns'] == 350 and native['ResourceScan']['edgeCases'] == 62,
            'Dependency-walker parity coverage differs')
    require(native['HomeLivesUI']['layouts'] == 168, 'Life UI coverage differs')
    onset = native['PlaybackOnset']
    require(len(onset['cases']) == 8 and {row['name'] for row in onset['cases']} == {
        'swap_stall_before_accept', 'swap_stall_after_accept', 'rejected_swap', 'power_tap',
        'hammer', 'resource_wait', 'scaled_pause_continuity', 'reload'}, 'Onset controls are incomplete')
    require(all(row['firstAge'] == 0 and row['modelPreserved'] for row in onset['cases']),
            'First pose starts late or onset playback changes the model')
    require(all(abs(row['duration'] - .12) < .00001 and row['movingPoses'] >= 8
                and .12 <= row['contactBudget'] <= .122
                for row in onset['cases'] if row['name'] in {
                    'swap_stall_before_accept', 'swap_stall_after_accept', 'resource_wait',
                    'scaled_pause_continuity', 'reload'}), 'Accepted swap does not retain its full visible 120ms')
    require('Full-life refill costs 900 at the wallet boundary and preserves old receipts'
            in native['ProfileChecks']['cases'], '900-coin durable price tests are absent')
    campaign = native['Checks']['campaign']
    require(campaign['status'] == 'PASS_CAMPAIGN_LOGIC' and not campaign['errors']
            and len(campaign['levels']) == 50, 'Authored campaign validation failed')

    before = read('Android/Before.json')
    require(before == read('Baseline_Before.json'), 'Review no longer preserves its original QA data')
    require({p.name.removesuffix('_Data_Audit.json') for p in (OUT / 'Android').glob('*_Data_Audit.json')}
            == TOOLS, 'Not all nine Android fixture tools have completed')
    audits = {}
    for tool in sorted(TOOLS):
        audit = read('Android/' + tool + '_Data_Audit.json')
        require(audit['serial'] == 'emulator-5556' and audit['apk_sha256'] == digest
                and audit['exit_code'] == 0 and utc(audit['utc']) >= build_finished,
                tool + ' failed, predates the final build, or uses a different APK')
        preserved(audit, before, tool)
        audits[tool] = audit

    fluidity = read('Android/Fluidity/Measurement.json')
    fluidity_install = install('Android/Fluidity/Installation.json', digest, build_finished)
    require(fluidity['status'] == 'RECORDED_NATIVE_FLUIDITY' and fluidity['platform'] == 'Android'
            and fluidity['isolatedProfile'] and fluidity['launchCleared']
            and utc(fluidity['utc']) >= utc(fluidity_install['utc']), 'Fluidity probe is stale/obscured/unisolated')
    clean(fluidity, 'Fluidity')
    phases = fluidity['phases']
    require({p['name'] for p in phases} == {'idle_including_hint_search', 'natural_first', 'natural_second',
            'rocket', 'three_rocket_chain', 'orb_rocket', 'golden_bomb', 'victory_animation'}
            and len(phases) == 8 and fluidity['frameSamples'], 'Fluidity phases are incomplete')
    require(all(p['frames'] > 0 and p['settleSeconds'] > 0 for p in phases), 'Fluidity has empty phases')

    touch = read('Android/Touch/Report.json')
    require(touch['status'] == 'CAPTURED_GAMEPLAY_AUDIT_REQUIRES_VISUAL_REVIEW'
            and touch['apk_sha256'] == digest and touch['serial'] == 'emulator-5556'
            and {c['mode'] for c in touch['cases']} == TOUCH_MODES and len(touch['cases']) == 8,
            'Touch cases differ or refer to another APK')
    for case in touch['cases']:
        mode = case['mode']
        require(case == read('Android/Touch/' + mode + '_Report.json'), mode + ' summary/individual report differ')
        require(case['status'] == 'PASS_NATIVE_DEVICE_GAMEPLAY_AUDIT' and case['accepted']
                and case['launchCleared'] and case['poses'] and utc(case['utc']) >= utc(audits['Touch']['utc']),
                mode + ' was rejected, hidden, empty or stale')
        clean(case, mode)
        if mode in MIXED_MODES:
            require(case['sourceActivated'] and case['protectedBirth'] and not case['chained'],
                    mode + ' failed original activation/newborn protection')
        require(sha(record('Android/Touch/' + mode + '_Before.png'))
                != sha(record('Android/Touch/' + mode + '_After.png')), mode + ' capture did not visibly change')
        require(record('Android/Touch/' + mode + '.mp4').stat().st_size > 10000, mode + ' movie is empty')

    cascade = {}
    for variant, rows in [('measure', 6), ('visual', 1)]:
        report = read('Android/Cascade/' + variant + '/Report.json')
        installation = install('Android/Cascade/' + variant + '/Installation.json', digest, build_finished, before)
        require(report['status'] == 'PASS_CASCADE_PLAYBACK' and report['variant'] == variant
                and report['platform'] == 'Android' and len(report['rows']) == rows
                and utc(report['utc']) >= utc(installation['utc']), variant + ' cascade is incomplete/stale')
        clean(report, variant + ' cascade')
        cascade[variant] = report
    require({row['targetFps'] for row in cascade['measure']['rows']} == {15, 30, 60}, 'Cascade rate controls missing')
    repeated = cascade['measure']['rows'][:3]
    require(len({(row['turnHash'], row['finalHash']) for row in repeated}) == 1
            and all(row['matches'] == 6 and row['frames'] > 0 for row in repeated), 'Rate controls changed cascade outcome')

    density = {}
    for family in ['crate', 'stone', 'gate', 'tiles']:
        folder = 'Android/Density/candidate_review-' + family + '/'
        report = read(folder + 'Report.json')
        installation = install(folder + 'Installation.json', digest, build_finished, before)
        require(report['status'] == 'PASS_OBSTACLE_DENSITY_PLAYBACK' and report['family'] == family
                and report['platform'] == 'Android' and report['variant'] == 'candidate_review-' + family
                and utc(report['utc']) >= utc(installation['utc']), family + ' density is stale/wrong variant')
        clean(report, family + ' density')
        rows = report['rows']
        require(len(rows) == 10 and {r['name'] for r in rows} == {
            family + '_' + str(n) + '_' + str(repeat) for n in [1, 8, 16, 32, 45] for repeat in [0, 1]},
            family + ' density controls are incomplete')
        require(report['frames'] and all(r['renderersCreated'] == 0 and r['crateSpritesCreated'] == 0
                and r['poolReady'] == r['poolEnd'] for r in rows), family + ' density warmed resource growth')
        for n in [1, 8, 16, 32, 45]:
            pair = [r for r in rows if r['name'].startswith(family + '_' + str(n) + '_')]
            require(len({(r['turnHash'], r['finalHash']) for r in pair}) == 1, family + ' density is nondeterministic')
            if family != 'tiles':
                require(all(r['hits'] == r['cleared'] == r['crates'] == n for r in pair), family + ' damage count differs')
        density[family] = report

    regression_install = install('Android/Regression/Installation.json', digest, build_finished)
    regression = read('Android/Regression/Regression.json')
    require(regression['status'] == 'PASS_NATIVE_REGRESSION' and regression['platform'] == 'Android'
            and regression['unity'] == '2022.3.62f3' and regression['boards'] == 50
            and regression['clips'] >= 354 and regression['actions'] >= 408 and regression['checks'] >= 1706
            and utc(regression['utc']) >= utc(regression_install['utc']), 'Full Android regression is incomplete/stale')
    clean(regression, 'Android regression')
    require(set(regression['damageFamilies']) == {'cabinet', 'case', 'crate', 'crystal', 'gate', 'moss', 'pod', 'stone'},
            'Android regression did not exercise all eight damage families')
    required_passes = {
        '899 coins cannot buy the 900-coin full-life refill',
        'Exactly 900 coins shows the enabled native refill button and price',
        'Native refill button spends 900 and fills all five lives',
        'Repeated native refill callback charges exactly once',
        'Connected Continue exposes the approved five-move/900-coin offer',
        'Confirmed decline charges exactly one life, no coins, and opens retry pre-level',
    }
    require(required_passes.issubset(regression['passed']), 'Current life/Continue device assertions are absent')
    require({'LifeRefill_Below900.png', 'LifeRefill_Exactly900.png', 'LifeRefill_Full_After900.png',
             'Connected_OutOfMoves_Continue.png'}.issubset(regression['frames']), 'Current life/Continue captures missing')
    for filename in regression['frames']:
        require(record('Android/Regression/' + filename).stat().st_size > 1000, 'Empty regression capture: ' + filename)

    review = visual('Visual_Review.json', 'REVIEWED_VISIBLE_ANDROID_GAMEPLAY72', digest)
    power_review = visual('Power_Visual_Notes.json', 'REVIEWED_VISIBLE_ANDROID_POWER_PROTECTION', digest)
    power_tool_review = visual('RegressionVisual/Power_Tool_Review.json',
                              'REVIEWED_FINAL_ANDROID_POWER_PAIRS_AND_TOOLS_WITH_OPEN_GAMEPLAY_GATES', digest)
    require(len(power_tool_review['inspection_method']['contact_sheets']) == 8
            and len(power_tool_review['inspection_method']['constituent_originals']) == 89
            and not power_tool_review['new_confirmed_rendering_discrepancies'],
            'Independent pair/tool review is incomplete or has unreported rendering discrepancies')
    require({'Android/Regression/LifeRefill_Exactly900.png', 'Android/Regression/LifeRefill_Full_After900.png'}
            .issubset(review['artifactSHA256']), '900-coin UI has not been visually reviewed')
    require(all('Android/Touch/' + mode + '.mp4' in power_review['artifactSHA256'] for mode in MIXED_MODES),
            'Not all six mixed-swap movies have a bound visual review')
    timing_analysis = visual('Timing_Analysis.json', 'ANALYZED_ANDROID_TIMINGS_WITH_OPEN_PERFORMANCE_GATES', digest)
    timing_inputs = {'APK_Artifact.json', 'Android/Fluidity/Measurement.json',
                     'Android/Cascade/measure/Report.json', 'Reference_Analysis.json',
                     'Timing_Visual_Notes.json'} | {
        'Android/Density/candidate_review-' + family + '/Report.json'
        for family in ['crate', 'stone', 'gate', 'tiles']}
    require(timing_inputs.issubset(timing_analysis['artifactSHA256']),
            'Timing analysis does not bind every final source measurement')
    require(utc(timing_analysis['utc']) >= build_finished and timing_analysis['remainingGates']
            and {p['name'] for p in timing_analysis['fluidity']} == {p['name'] for p in phases}
            and len(timing_analysis['fluidity']) == 8 and len(timing_analysis['cascade']) == 6
            and len(timing_analysis['cascadeTransitions']) == 15
            and set(timing_analysis['density']) == set(density)
            and all(len(rows) == 10 for rows in timing_analysis['density'].values()),
            'Timing analysis is stale, incomplete or omits remaining performance gates')
    timing_visual = read('Timing_Visual_Notes.json')
    require(timing_visual['status'] == 'REVIEWED_EVIDENCE_WITH_OPEN_LOCAL_CASCADE_GAP',
            'Final timing visual review is absent or has an unrecognized disposition')
    timing_apk = timing_visual['apk']
    require(timing_apk['sha256'] == timing_apk['installedSha256'] == digest
            and timing_apk['bytes'] == artifact['bytes'] and timing_apk['qaSerial'] == 'emulator-5556'
            and timing_apk['profileDataUnchanged'] is True and utc(timing_visual['reviewedUtc']) >= build_finished,
            'Timing visual review is not bound to the final isolated QA APK')
    bound_paths = set()
    for bound in timing_visual['boundEvidence']:
        path = artifact_path(bound['path'], ROOT)
        require('BeforeOnset' not in path.parts and sha(path) == bound['sha256']
                and path.stat().st_size == bound['bytes'], 'Timing visual source changed: ' + bound['path'])
        bound_paths.add(bound['path'])
        if path.is_relative_to(OUT):
            record(path.relative_to(OUT).as_posix())
    require({
        'Verification/Evidence/Gameplay72/Android/Cascade/visual/HR_NaturalCascade.mp4',
        'Verification/Evidence/Gameplay72/Android/Cascade/visual/Report.json',
        'Verification/Evidence/Gameplay72/Android/Cascade/measure/Report.json',
        'Verification/Evidence/CascadeResponsiveness/Reference/MV_NaturalMatch.mp4',
        'Verification/Evidence/GameplayAudit/Reference/MV_Natural_Refill.mp4',
        'Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs',
        'Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPlayback.cs',
        'Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPresentation.cs',
        'Unity/Assets/HeartOfTheRain/M47/Runtime/GameplayScreen.cs',
    }.issubset(bound_paths), 'Timing visual review lacks source/video/reference bindings')
    local_gap = timing_visual['verifiedRemainingGap']
    require(local_gap['id'] == 'LOCAL_MATCH_WAITING_FOR_UNRELATED_LONG_REFILL'
            and local_gap in timing_analysis['remainingGameplayDefects'],
            'Timing analysis omits the independently verified local cascade defect')
    gap = local_gap['observations']['contactToReactionBoundMs']
    stable_gap = local_gap['observations']['postDeformationStableWaitBoundMs']
    require(len(gap) == len(stable_gap) == 2 and 0 < gap[0] <= gap[1]
            and 0 < stable_gap[0] <= stable_gap[1] and timing_visual['remainingGates'],
            'Local cascade wait bounds or remaining gates are missing')
    reference = read('Reference_Analysis.json')
    require(reference['status'] == 'OBSERVED_ARCHIVED_REFERENCE_FRAMES' and len(reference['clips']) == 7
            and reference['freshCapture'] and len(reference['observations']) == 7,
            'Archived reference review is incomplete')
    for clip in reference['clips']:
        path = artifact_path(clip['video'], ROOT)
        require(sha(path) == clip['sha256'] and path.stat().st_size == clip['bytes'], 'Archived reference clip changed')
        require(clip['originalFramePtsSeconds'] == sorted(clip['originalFramePtsSeconds'])
                and len(clip['originalFramePtsSeconds']) > 10, 'Reference timestamps missing/out of order')
        record(clip['contactSheet'])

    phase_rows = [{k: p[k] for k in ['name', 'frames', 'p95Ms', 'worstMs', 'modelMs', 'acceptMs',
                                   'commandMs', 'firstPresentationMs', 'settleSeconds', 'gen0Collections',
                                   'spriteCreates', 'synchronousTextureLoads', 'spriteEvictions']} for p in phases]
    density_rows = []
    for family, report in density.items():
        intervals = [f['intervalMs'] for f in report['frames']]
        density_rows.append({'family': family, 'turns': len(report['rows']), 'frames': len(intervals),
                             'p95_interval_ms': percentile(intervals, .95), 'worst_interval_ms': max(intervals),
                             'worst_command_ms': max(r['commandMs'] for r in report['rows']),
                             'new_renderers': sum(r['renderersCreated'] for r in report['rows'])})
    result = {
        'status': 'PASS_TARGETED_FIXES_WITH_OPEN_GAMEPLAY_GATES', 'utc': datetime.now(timezone.utc).isoformat(),
        'source_checkpoint': 72, 'source_inputs': len(frozen), 'source_sha256': sha(OUT / 'Source_SHA256.json'),
        'apk_sha256': digest, 'apk_bytes': artifact['bytes'], 'native_suites': native_rows,
        'native_checks': sum(row['checks'] for row in native_rows),
        'native_scope': 'The unchanged model, transaction, artwork and presentation-preparation suites retain '
                        'their checkpoint72 process evidence. PlaybackOnset, TimingChecks, WarmupChecks and '
                        'PlaySmoke are rerun after the onset-clock correction. All nine Android stages use '
                        'the final rebuilt APK; the earlier APK Android evidence is historical under BeforeOnset.',
        'retained_native_inputs_verified': len(retained_native_inputs),
        'mixed_power_creation': {'native_cases': 360, 'protected_births': 360, 'newborn_chains': 0,
                                 'source_contact_cases': 240, 'native_existing_chain_controls': 4,
                                 'actual_android_mixed_swipes': 6},
        'playback_onset': {'native_cases': 8, 'first_pose_age': 0, 'scheduled_swap_seconds': .12,
                           'pre_presentation_stall_controls_ms': 200,
                           'scope': 'First rendered pose owns command onset. Existing cascade/gravity clock continues '
                                    'without re-anchoring; native controlled frame budgets are separate from device pacing.'},
        'full_life_refill': {'coins': 900, 'requires_zero_lives': True, 'restores_lives': 5,
                            'native_boundary_crash_and_legacy_receipt_tests': True,
                            'android_899_900_and_duplicate_callback': True},
        'android': {'serial': 'emulator-5556', 'data_audits': 9, 'touch_cases': 8, 'cascade_timed_cases': 6,
                    'density_timed_turns': 40, 'fluidity_phases': 8,
                    'independently_reviewed_power_tool_sheets': 8,
                    'power_tool_review_scope': power_tool_review['scope'],
                    'qualified_visual_observations': power_tool_review['qualified_observations'],
                    'regression': {k: regression[k] for k in ['status', 'checks', 'boards', 'clips', 'actions',
                                                            'labels', 'damageFamilies', 'scope']}},
        'fluidity': phase_rows, 'density': density_rows,
        'timing_analysis': {'status': timing_analysis['status'], 'path': 'Timing_Analysis.json',
                            'scope': timing_analysis['scope'],
                            'remaining_gates': timing_analysis['remainingGates']},
        'remaining_gameplay_defects': [{
            'id': local_gap['id'], 'status': 'VERIFIED_OPEN',
            'severity': local_gap['severity'], 'evidence': 'Timing_Visual_Notes.json',
            'contact_to_reaction_ms': gap, 'stable_wait_after_landing_ms': stable_gap,
            'finding': 'A locally settled matching row waits for unrelated refill routes. '
                       'A zero extra gap after the global final contact does not resolve this local delay.',
            'required_followup': local_gap['implementationBoundary'],
        }],
        'reference': {'status': reference['status'], 'archived_clips': 7, 'fresh_gameplay_parity_verified': False,
                      'current_capture_limitation': reference['freshCapture']},
        'qa_data_unchanged': True, 'main_apk_updated': False, 'artwork_levels_existing_guids_unchanged': True,
        'scope': 'Current native Editor model/presentation/transaction tests; final-APK QA Android real swipes, '
                 'unaccelerated timing fixtures and accelerated all-50-board/scripted UI regression. '
                 'Visual review binds visible final-APK recordings. Reference comparison uses archived variable-rate '
                 'Match Villains recordings. A verified local cascade responsiveness defect remains open; '
                 'no whole-game smoothness, fresh version parity, identical-board, sustained FPS or physical-device claim.',
        'limits': [
            f"Verified gameplay defect remains: local row contact-to-reaction is {gap[0]:.0f}–{gap[1]:.0f} ms "
            f"in the recorded final-APK fixture; after landing deformation the stable wait is "
            f"{stable_gap[0]:.0f}–{stable_gap[1]:.0f} ms. It needs dependency-aware body/contact scheduling; "
            'shortening the global phase would abandon unrelated tile routes.',
            f"Emulator long frames remain: broad fluidity worst {max(p['worstMs'] for p in phases):.2f} ms; "
            f"worst synchronous command {max(p['commandMs'] for p in phases):.2f} ms. These include scheduling and "
            'cold preparation. This is a completed investigation/pass, not certification of hitch-free gameplay.',
            'StepStarted dispatch is not physical input-to-display latency. Screenrecord has overhead; density/cascade '
            'timing runs are separate from recorded visual runs. Allocation counters are unavailable; no zero-allocation claim.',
            'Only QA LDPlayer is rebuilt/installed at checkpoint72; main retains deployment64.',
            'Real coin purchases, trusted-time production wallet/continuation, physical-device/GPU/thermal certification '
            'and human campaign balance/native-language approval remain open.',
        ],
        'evidence_sha256': dict(sorted(evidence.items())), 'collector_sha256': sha(Path(__file__)),
    }
    checkpoint = {
        'utc': result['utc'], 'status': result['status'], 'source_checkpoint': 72, 'installed_checkpoint': 64,
        'qa_installed_checkpoint': 72, 'source_sha256': result['source_sha256'],
        'review': 'Codex_Handoff/Documentation/72_GAMEPLAY_POWER_PROTECTION_AND_FLOW_REVIEW.md',
        'summary': 'Verification/Evidence/Gameplay72/Summary.json', 'android_apk_sha256': digest,
        'android_apk_matches_current_source': True, 'main_installed_apk_matches_current_source': False,
        'scope': result['scope'],
    }
    # Publish only after every proof above has passed. Historical branches are untouched.
    for path, value in [(OUT / 'Summary.json', result), (OUT.parent / 'Verification_Summary.json', result),
                        (OUT.parent / 'Native_Source_Checkpoint.json', checkpoint)]:
        path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ['evidence_sha256', 'fluidity', 'density']}, indent=2))


if __name__ == '__main__':
    main()
