"""Fail-closed checkpoint75 collector; does not build, install, or grant visual approval.

Draft contracts deliberately require fresh proof. A cache-only prototype, old
checkpoint73 device run, or unmeasured gap cannot publish a checkpoint75 pass.
"""
import hashlib
import json
import re
import runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Gameplay75'
BASE = ROOT / 'Verification/Evidence/Gameplay74'
HISTORICAL73 = ROOT / 'Verification/Evidence/LocalCascade73'
APK = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
BASE_CONTRACT = runpy.run_path(str(Path(__file__).with_name('collect_gameplay72_results.py')),
                              run_name='checkpoint72_contract_only')
NATIVE = dict(BASE_CONTRACT['NATIVE_STATUSES']) | {
    'LocalCascade': 'PASS_NATIVE_LOCAL_CASCADE73', 'CascadeTiming': 'PASS_NATIVE_CASCADE_TIMING',
    'LocalContinuation': 'PASS_NATIVE_LOCAL_CONTINUATION75',
    'ModelCommands': 'PASS_NATIVE_MODEL_COMMANDS75', 'FrameLookup': 'PASS_NATIVE_FRAME_LOOKUP75',
    'PlaybackConstruction': 'PASS_NATIVE_PLAYBACK_CONSTRUCTION75',
    'LegalSwapExistence': 'PASS_NATIVE_LEGAL_SWAP_EXISTENCE74'}
TOOLS = BASE_CONTRACT['TOOLS']
MIXED = BASE_CONTRACT['MIXED_MODES']
TOUCH = BASE_CONTRACT['TOUCH_MODES']
FLUIDITY_PHASES = {'idle_including_hint_search', 'natural_first', 'natural_second', 'rocket',
                  'three_rocket_chain', 'orb_rocket', 'golden_bomb', 'victory_animation'}
PROFILE_CONTRACT = runpy.run_path(str(Path(__file__).with_name('validate_gameplay74_profile.py')),
                                 run_name='profiling_contract_only')
ALLOWED_CHANGED = {
    'Unity/Assets/HeartOfTheRain/' + name for name in [
        'M46/Runtime/BoardModel.cs', 'M46/Runtime/BoardPlayback.cs', 'M46/Runtime/M46AtlasBank.cs',
        'M46/Runtime/LocalCascadeContinuation.cs',
        'M47/Runtime/EffectMeshBatcher.cs',
        'Verification/CascadeTimingProbe.cs',
        'Verification/PowerupDeviceVerification.cs',
        'Verification/Editor/LocalContinuationVerification.cs',
        'Verification/Editor/EffectBatchVerification.cs',
    ]
}
ADDED = {
    'Unity/Assets/HeartOfTheRain/' + name + suffix for name in [
        'Verification/Editor/ModelCommandPerformanceVerification.cs',
        'Verification/Editor/FrameLookupVerification.cs',
        'Verification/Editor/PlaybackConstructionVerification.cs',
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


def touch_provenance(report, build_finished):
    need(report['status'] == 'CAPTURED_GAMEPLAY_AUDIT_REQUIRES_VISUAL_REVIEW'
         and utc(report['utc']) >= build_finished, 'Touch aggregate predates the final build or has the wrong stage status')
    for row in report['cases']:
        need(row['mode'] in TOUCH and utc(row['utc']) >= utc(report['utc']),
             'Touch case predates its final aggregate launch: ' + row['mode'])
        need(row == read('Android/Touch/' + row['mode'] + '_Report.json'),
             'Touch aggregate case differs from its native raw report: ' + row['mode'])


def idle_device_controls(report, regression, installed):
    """Recompute bounded idle advancement from actual per-frame observations."""
    clean(report, 'Native M70 idle device controls')
    need(report['status'] == 'PASS_NATIVE_M70_DEVICE'
         and utc(report['utc']) >= utc(regression['utc']) >= utc(installed['utc']),
         'Native M70 device report is stale or failed')
    shapes = report['idleAdvancement']
    need(len(shapes) == 3 and {(r['columns'], r['rows']) for r in shapes} == {(9, 9), (9, 11), (11, 11)},
         'Idle observer does not cover all three authored shapes')
    samples = 0
    for shape in shapes:
        label = str(shape['columns']) + 'x' + str(shape['rows'])
        need(shape['passed'] is True and shape['timedOut'] is False and shape['sampleCapReached'] is False
             and shape['sampleLimit'] == 96 and shape['wallLimitSeconds'] == 1.25
             and 3 <= shape['sampleCount'] <= shape['sampleLimit']
             and PROFILE_CONTRACT['finite_nonnegative'](shape['elapsedWall'])
             and len(shape['powers']) == 3
             and {(r['power'], r['atlas']) for r in shape['powers']} == {(4, 9), (5, 10), (21, 6)}
             and len({r['pieceId'] for r in shape['powers']}) == 3,
             'Idle observer shape/bounds/power coverage differs: ' + label)
        for power in shape['powers']:
            trace = power['samples']
            need(len(trace) == shape['sampleCount'] and power['pieceId'] > 0
                 and all(isinstance(s['frame'], int) and isinstance(s['logicalFrame'], int)
                         and s['frame'] >= 0 and s['logicalFrame'] >= 0
                         and PROFILE_CONTRACT['finite_nonnegative'](s['clock'])
                         and PROFILE_CONTRACT['finite_nonnegative'](s['drawAge'])
                         and s['key'] == 'Idle' and s['sprite']
                         and set(s['rect']) == {'serializedVersion', 'x', 'y', 'width', 'height'}
                         and str(s['rect']['serializedVersion']) == '2'
                         and all(PROFILE_CONTRACT['finite_nonnegative'](s['rect'][k])
                                 for k in ['x', 'y', 'width', 'height'])
                         and s['rect']['width'] > 0 and s['rect']['height'] > 0 for s in trace),
                 'Idle observer has incomplete/nonfinite pose samples: ' + label)
            first = trace[0]
            ordered = all(b['frame'] > a['frame'] and b['clock'] >= a['clock']
                          and b['drawAge'] >= a['drawAge'] and b['key'] == first['key']
                          for a, b in zip(trace, trace[1:]))
            clock = any(s['clock'] > first['clock'] + .00001 for s in trace[1:])
            logical = any(s['drawAge'] > first['drawAge'] + .00001
                          and s['logicalFrame'] != first['logicalFrame'] for s in trace[1:])
            rectangle = any(s['rect'] != first['rect'] for s in trace[1:])
            need(ordered and clock and logical and rectangle
                 and power['invalidSequence'] is False and power['passed'] is True
                 and power['clockAdvanced'] is clock and power['frameAdvanced'] is logical
                 and power['rectChanged'] is rectangle,
                 'Idle observer flags disagree with its actual advancing poses: ' + label)
            samples += len(trace)
        need({'M70 Bomb/Rocket live idle advances ' + label, 'M70 idle respects pause ' + label,
              'M70 idle resumes ' + label}.issubset(regression['passed']),
             'Native M70 advancing/pause/resume assertion missing: ' + label)
    need(len(report['textures']) == 7 and {t['atlas'] for t in report['textures']} == {9, 10, 6, 29, 40, 19, 26}
         and all(t['width'] == t['height'] == 2048 and t['loadedCopies'] == 1
                 and (not report['astcSupported'] or t['format'] == 'ASTC_4x4') for t in report['textures']),
         'Native M70 texture ownership/import controls failed')
    return {'shapes': 3, 'powers': 9, 'samples': samples, 'sample_limit_per_shape': 96,
            'wall_limit_seconds': 1.25}


def idle_native_controls(report):
    rows = report['idleObserverRows']
    need(report['idleAliasControls'] == report['idleObserverPositiveControls'] == 6
         and report['idleObserverNegativeControls'] == 18 and len(rows) == 6
         and {(r['power'], r['atlas'], r['firstFrame']) for r in rows}
         == {(p, a, f) for p, a in [(4, 9), (5, 10), (21, 6)] for f in [6, 30]},
         'Native idle controls do not cover all six authored alias pairs and eighteen frozen/stuck controls')
    for row in rows:
        trace = row['samples']
        need(row['middleFrame'] == row['firstFrame'] + 6 and row['lastFrame'] == row['firstFrame'] + 12
             and all(row[k] is True for k in ['endpointRectsEqual', 'passedWithIntermediate',
                         'frozenClockRejected', 'frozenFrameRejected', 'constantRectRejected'])
             and len(trace) == 3 and all(s['key'] == 'Idle' and s['sprite'] for s in trace)
             and trace[0]['rect'] == trace[2]['rect'] != trace[1]['rect']
             and [s['logicalFrame'] - trace[0]['logicalFrame'] for s in trace] == [0, 6, 12]
             and all(b['frame'] > a['frame'] and b['clock'] > a['clock']
                     and b['drawAge'] > a['drawAge'] for a, b in zip(trace, trace[1:]))
             and abs(trace[2]['drawAge'] - trace[0]['drawAge'] - .4) < .00001,
             'Native idle alias/intermediate/frozen control trace is incomplete')
    return {'authored_alias_pairs': 6, 'intermediate_advancement_controls': 6,
            'frozen_or_stuck_negative_controls': 18}


def historical_idle_failure(current, digest, before):
    """Keep the superseded failed run visible; it cannot satisfy a final gate."""
    folder = 'IdleSamplingFailure/'
    artifact = read(folder + 'APK_Artifact.json')
    source_path = file(folder + 'Source_SHA256.json')
    old_source = read(folder + 'Source_SHA256.json')['files']
    install = read(folder + 'Installation.json')
    regression = read(folder + 'Regression.json')
    device = read(folder + 'M70_Device.json')
    audit = read(folder + 'Regression_Data_Audit.json')
    old_digest = 'fbb8da8424bbef330c33d03b4bae4283a4f33231e2542bb2a227a19ef94ed5a2'
    old_apk_path = '.verification-cache/Gameplay75/BeforeIdleSamplingFix/HeartOfTheRain_Development.apk'
    old_apk = file(old_apk_path, ROOT)
    expected_changes = {'Unity/Assets/HeartOfTheRain/Verification/' + name for name in [
        'PowerupDeviceVerification.cs', 'Editor/FrameLookupVerification.cs']}
    need(artifact['sha256'] == install['sha256'] == audit['apk_sha256'] == old_digest != digest
         and sha(old_apk) == old_digest and old_apk.stat().st_size == artifact['bytes'] == 301909877
         and install['serial'] == audit['serial'] == 'emulator-5556'
         and sha(source_path) == '5a9435ebd7cb5bdd1e934910ed3ecc91120f2eb3bdaa233e4c10bbd5124c786e'
         and set(old_source) == set(current)
         and {p for p in current if current[p] != old_source[p]} == expected_changes,
         'Historical failed idle proof/source differs, or final changes extend beyond the observer/native controls')
    need(regression['status'] == 'FAIL_NATIVE_REGRESSION'
         and regression['failures'] == ['M70 Bomb/Rocket live idle advances 9x9']
         and (regression['checks'], regression['labels'], regression['clips'], regression['actions'], regression['boards'])
         == (1716, 14105, 354, 408, 50) and len(regression['passed']) == 1715
         and device['status'] == 'FAIL_NATIVE_M70_DEVICE'
         and device['failures'] == ['Bomb/Rocket live idle advances 9x9']
         and utc(device['utc']) >= utc(regression['utc']) >= utc(install['utc'])
         and audit['exit_code'] == 1,
         'The first failed idle attempt was hidden, relabelled or changed')
    preserved(audit, before, 'Historical failed idle run')
    for name in ['Player.log', 'M70_9x9_Idle_A.png', 'M70_9x9_Idle_B.png']:
        need(file(folder + name).stat().st_size > 0, 'Historical idle capture missing')
    return {'status': regression['status'], 'apk_sha256': old_digest, 'apk_archive': old_apk_path,
            'apk_bytes': old_apk.stat().st_size,
            'source_sha256': sha(source_path), 'failure': regression['failures'][0],
            'scope': 'Preserved failed two-endpoint idle assertion. Authored rectangles can recur after 12 frames; '
                     'the old run has no per-frame trace proving which alias pair occurred. '
                     'Its failure remains historical and does not waive any final passing regression requirement.'}


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
             and report['modelWorkEnabled'] is False and report['checkpoint74Continuation'] is False
             and install['profile_model_work'] is False and install['checkpoint74_continuation'] is False
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


def extra_controls(digest, build_finished, before, continuation, model_hashes):
    """Separate recorded controls and expensive model diagnostics from default timing."""
    corpus = {r['name']: r for r in continuation['rows']}
    cases = []
    for level in [14, 31, 33]:
        expected_hashes = model_hashes['L' + str(level) + '_match']
        for mode, control in [('control74', True), ('refined75', False)]:
            folder = 'ExtraContinuation/L' + str(level) + '/' + mode + '/visual/'
            install = installation(folder + 'Installation.json', digest, build_finished, before)
            report = read(folder + 'Report.json')
            need(install['visual_level'] == report['visualLevel'] == level
                 and install['checkpoint74_continuation'] is control and report['checkpoint74Continuation'] is control
                 and install['profile_model_work'] is False and report['modelWorkEnabled'] is False
                 and utc(report['utc']) >= utc(install['utc'])
                 and PROFILE_CONTRACT['RUNNER']['validate_report'](report, 'visual', 1, require_profiling=True),
                 'Extra continuation video/control/provenance differs: ' + folder)
            row = report['rows'][0]
            need(row['name'] == row['baseCase'] == 'L' + str(level) + '_0_30'
                 and (row['turnHash'], row['finalHash']) == expected_hashes,
                 'Extra continuation changed seeded command outcome')
            native = corpus['L' + str(level) + '_match']
            scheduled = native['checkpoint74Seconds'] if control else native['refinedSeconds']
            need(abs(row['scheduledSeconds'] - scheduled) < .001, 'Recorded extra control uses wrong native schedule')
            video = file(folder + 'HR_NaturalCascade.mp4')
            need(video.stat().st_size > 65536, 'Extra recorded continuation has no usable movie')
            cases.append({'level': level, 'mode': mode, 'folder': folder, 'scheduledSeconds': scheduled})
    folder = 'ExtraModelStages/measure/'
    install = installation(folder + 'Installation.json', digest, build_finished, before)
    report = read(folder + 'Report.json')
    need(install['profile_model_work'] is True and report['modelWorkEnabled'] is True
         and install['checkpoint74_continuation'] is False and report['checkpoint74Continuation'] is False
         and install['visual_level'] == report['visualLevel'] == 4 and utc(report['utc']) >= utc(install['utc']),
         'Separate model-stage diagnostic mode did not run or reused an old report')
    old = read('Android/Cascade/measure/Report.json', BASE)
    hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
    profile = PROFILE_CONTRACT['validate'](report, 'measure', hashes)
    need(len(profile['rows']) == 6 and all(r['modelWork']['snapshotCalls'] > 0 and r['modelWork']['validationCalls'] > 0
         and all(PROFILE_CONTRACT['finite_nonnegative'](v) for v in r['modelWork'].values()) for r in report['rows']),
         'Detailed model-stage diagnostics are absent/invalid')
    return {'continuation_cases': cases, 'model_stage_rows': 6}


def recorded_extra_performance(cases):
    """Keep recorded-video costs distinct from default and repeated measurements."""
    rows = []
    for case in cases:
        report = read(case['folder'] + 'Report.json')
        row = report['rows'][0]
        trace = [f for f in report['frameSamples'] if f['row'] == 0]
        timed = [f for f in trace if f['timingWindow']]
        need(len(timed) == row['frames'] > 0, 'Recorded extra timing window lacks its raw frames')
        worst = max(timed, key=lambda f: f['intervalMs'])
        need(abs(worst['intervalMs'] - row['maxIntervalMs']) < .001,
             'Recorded extra maximum interval differs from its raw timing window')
        detail = {'level': case['level'], 'mode': case['mode'], 'folder': case['folder'],
                  'name': row['name'], 'targetFps': row['targetFps'], 'commandFrame': row['commandFrame'],
                  'modelMs': row['modelMs'], 'acceptMs': row['acceptMs'], 'commandMs': row['commandMs'],
                  'maxIntervalMs': row['maxIntervalMs'], 'worstIntervalFrame': worst['frame'],
                  'worstIntervalKind': worst['kind'], 'worstIntervalStage': worst['stage'],
                  'firstDispatchFromAcceptMs': row['firstDispatchFromAcceptMs'],
                  'firstCommandRenderMs': row['firstCommandRenderMs']}
        neighborhood = []
        for f in trace:
            if abs(f['frame'] - row['commandFrame']) <= 1 or abs(f['frame'] - worst['frame']) <= 1:
                item = {k: f[k] for k in ['frame', 'absoluteWall', 'stage', 'kind', 'timingWindow',
                                         'commandFrame', 'costPredatesCommand', 'intervalMs', 'afterUpdateElapsedMs']}
                item['cost'] = {k: f['cost'][k] for k in ['frame', 'kind', 'updateMs', 'renderMs',
                    'updateStartedWall', 'updateFinishedWall', 'renderStartedWall', 'renderFinishedWall']}
                neighborhood.append(item)
        need(any(f['frame'] == row['commandFrame'] for f in neighborhood)
             and any(f['frame'] == worst['frame'] for f in neighborhood),
             'Recorded extra command/worst-interval neighborhood is missing')
        detail['commandAndWorstFrameNeighborhood'] = neighborhood
        rows.append(detail)
    need(len(rows) == 6 and {(r['level'], r['mode']) for r in rows}
         == {(level, mode) for level in [14, 31, 33] for mode in ['control74', 'refined75']},
         'Recorded extra performance omits a control/refined case')
    return {'rows': rows, 'maxCommand': max(rows, key=lambda r: r['commandMs']),
            'maxInterval': max(rows, key=lambda r: r['maxIntervalMs']),
            'scope': 'Separate recorded30fps continuation controls, including their actual command and '
                     'frame-interval neighborhoods. Recording and development diagnostics add overhead; '
                     'these are not unrecorded timings or a causal comparison with default/repeated fixtures. '
                     'A long interval contains prior work and scheduling; the tagged following Render cost '
                     'alone does not explain the interval.'}


def direct_comparison(digest, baseline_digest):
    report = read('Profile_Comparison74_75.json')
    helper = Path(__file__).with_name('compare_gameplay75_profiles.py')
    build = runpy.run_path(str(helper), run_name='direct75_comparison_read_only')['build']
    expected = build(OUT)
    need({k: v for k, v in report.items() if k != 'utc'} == {k: v for k, v in expected.items() if k != 'utc'}
         and report['apk_sha256'] == digest and report['baseline_apk_sha256'] == baseline_digest
         and report['status'] == 'DESCRIPTIVE_GAMEPLAY74_75_WITH_REMAINING_PERFORMANCE_GATES'
         and len(report['cascade']) == 6 and len(report['fluidity']) == 8
         and set(report['density']) == {'crate', 'stone', 'gate', 'tiles'}
         and all(len(v) == 10 for v in report['density'].values()),
         'Descriptive74/75 comparison differs from full raw controls or omits worse rows')
    for name, expected_hash in report['artifactSHA256'].items():
        need(sha(file(name, ROOT)) == expected_hash, 'Direct74/75 comparison input changed: ' + name)
    return report


def main(publish=True):
    evidence.clear()
    baseline = read('Baseline_74.json')
    need(baseline['status'] == 'ARCHIVED_VERIFIED_BASELINE74_BEFORE75_EDITS' and baseline['baseline'] == 74,
         'Missing independently archived checkpoint74 baseline')
    for path, expected in baseline['artifacts'].items():
        need(sha(file(path, ROOT)) == expected, 'Archived74 proof changed: ' + path)
    baseline_source_path = file('Source_SHA256.json', BASE)
    baseline_source = read('Source_SHA256.json', BASE)['files']
    baseline_summary, baseline_artifact = read('Summary.json', BASE), read('APK_Artifact.json', BASE)
    need(baseline['source_files'] == len(baseline_source) == baseline_summary['source_inputs']
         and baseline_summary['source_checkpoint'] == 74
         and baseline_summary['status'] == 'PASS_TARGETED_GAMEPLAY74_WITH_REMAINING_PERFORMANCE_GATES'
         and baseline_summary['source_sha256'] == sha(baseline_source_path), 'Invalid74 source/summary baseline')
    old_apk = file('.verification-cache/Gameplay75/Baseline74.apk', ROOT)
    need(sha(old_apk) == baseline['apk_sha256'] == baseline_artifact['sha256'] == baseline_summary['apk_sha256']
         and old_apk.stat().st_size == baseline['apk_bytes'] == baseline_artifact['bytes'], 'Archived74 APK differs')
    # Baseline report hashes are taken from the sealed74 summary, not an old75 candidate.
    for name in ['Timing_Visual_Notes.json', 'Native/ModelPerfChecks.json', 'Native/LocalCascade.json',
                 'Native/LegalSwapExistence.json', 'Native/LocalContinuation.json', 'Native/CascadeTiming.json',
                 'Android/Fluidity/Measurement.json', 'Android/Cascade/measure/Report.json',
                 'Android/Cascade/visual/Report.json'] + [
                     'Android/Density/candidate_review-' + family + '/Report.json'
                     for family in ['crate', 'stone', 'gate', 'tiles']]:
        need(sha(file(name, BASE)) == baseline_summary['evidence_sha256'][name], 'Frozen74 report changed: ' + name)

    freeze = read('Source_SHA256.json')
    current = freeze['files']
    inventory = {p.relative_to(ROOT).as_posix() for name in ['Unity/Assets', 'Unity/Packages', 'Unity/ProjectSettings']
                 for p in (ROOT / name).rglob('*') if p.is_file()}
    need(inventory == set(current) and all(sha(ROOT / p) == h for p, h in current.items()), 'Final source freeze differs')
    changed = {p for p in baseline_source if p in current and baseline_source[p] != current[p]}
    added, removed = set(current) - set(baseline_source), set(baseline_source) - set(current)
    delta = read('Source_Delta.json')
    need(delta['baseline'] == 74 and changed == set(delta['changed_existing'])
         and added == set(delta['added']) and removed == set(delta['removed']), 'Stale75 source delta')
    need(changed == ALLOWED_CHANGED
         and added == ADDED and not removed, 'Unreviewed runtime, data, metadata or SDK change')
    for path in changed:
        archived = file(baseline['source_archive'] + '/' + path, ROOT)
        need(sha(archived) == baseline_source[path], 'Original74 source archive differs: ' + path)
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
         'Final75 APK identity differs or is still74')
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
    need(old_hashes == new_hashes, 'Authored command results differ from final74')
    need(native['MixedSwapChecks']['protectedBirths'] == 360 and native['MixedSwapChecks']['chainedBirths'] == 0,
         'Newborn protection regressed')
    cascade_native = native['CascadeTiming']
    need(len(cascade_native['rows']) == 350, 'Cascade15/30/60 native coverage incomplete')
    old_local = read('Native/LocalCascade.json', BASE)
    old_model_hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old_local['rows']}
    need({r['name']: (r['turnHash'], r['finalHash']) for r in local['rows']} == old_model_hashes,
         'Existing350 model command outcomes differ from checkpoint74')
    continuation = native['LocalContinuation']
    need(continuation['modelCases'] == len(continuation['rows']) == 350
         and continuation['mixedCases'] == 30 and continuation['existingChainCases'] == 4
         and continuation['guardCases'] >= 24 and continuation['acceptedHandoffs'] > 0
         and continuation['rawTurnParity'] and continuation['finalSnapshotParity'],
         'Local continuation/model/fallback coverage incomplete')
    need(continuation['checkpoint74Comparisons'] == 350
         and continuation['qualifyingTurns'] == continuation['acceptedHandoffs'] == 4
         and continuation['newQualifyingTurns'] == continuation['terminalHandoffs'] == 3
         and continuation['guardCases'] == 44 and continuation['seededCases'] == len(continuation['seededRows']) == 4
         and continuation['seededAcceptedHandoffs'] == 4,
         'New75 terminal-only eligibility/control coverage incomplete')
    prior_continuation = {r['name']: r for r in read('Native/LocalContinuation.json', BASE)['rows']}
    for row in continuation['rows']:
        need((row['sequentialTurnHash'], row['sequentialFinalHash']) == old_model_hashes[row['name']]
             == (row['refinedTurnHash'], row['refinedFinalHash']),
             'Continuation changed raw model result: ' + row['name'])
        need(row['accepted'] in [0, 1] and 0 < row['refinedSeconds'] <= row['checkpoint74Seconds'] + .0001
             <= row['sequentialSeconds'] + .0002, 'Continuation schedule grows from74: ' + row['name'])
        need(abs(row['checkpoint74Seconds'] - prior_continuation[row['name']]['refinedSeconds']) < .0002
             and row['checkpoint74Accepted'] == prior_continuation[row['name']]['accepted'],
             'Preserved74 continuation control differs from archived duration/eligibility')
    need({r['name'] for r in continuation['rows'] if r['accepted']} == {'L4_match', 'L14_match', 'L31_match', 'L33_match'},
         'Unexpected75 continuation eligibility expansion')
    need(all(r['accepted'] == 1 and r['checkpoint74Accepted'] == 0
             and r['sequentialTurnHash'] == r['refinedTurnHash'] and r['sequentialFinalHash'] == r['refinedFinalHash']
             and r['refinedSeconds'] < r['checkpoint74Seconds'] for r in continuation['seededRows']),
         'New seeded native terminal controls fail raw/final/schedule parity')
    continued_renderers = continuation['rendererRows']
    need(any(row['caseName'] == 'L4_confirmation' for row in continued_renderers)
         and all(row['continuedCount'] > 0 and row['poseSamples'] > 0 and row['routeSamples'] > 0
                 and row['collisionSamples'] > 0 and row['secondsSavedVs73'] > 0
                 and row['minimumColumnClearance'] >= .90
                 and row['maxBoundaryPositionJump'] < .001 and row['maxBoundaryScaleJump'] < .001
                 for row in continued_renderers), 'Continuation body/route/landing/column continuity incomplete')
    terminal_renderers = [r for r in continued_renderers if r['terminalIdleLanding']]
    need({'L14_match', 'L31_match', 'L33_match'} <= {r['caseName'] for r in terminal_renderers}
         and all(r['landingTailsBeyondSuccessor'] > 0 and r['priorEffectSamples'] > 0
                 and r['successorExtension'] <= .1202 and r['secondsSavedVs74'] > .01 for r in terminal_renderers),
         'Actual terminal landing/idle/prior-effects native sampling is incomplete')
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
         and Path(legal['baselineReportPath']).resolve() == (HISTORICAL73 / 'Native/LocalCascade.json').resolve()
         and legal['baselineReportSHA256'] == read('Native/LegalSwapExistence.json', BASE)['baselineReportSHA256']
         == sha(file('Native/LocalCascade.json', HISTORICAL73)),
         'Existing74 legal-swap control lost its deliberately retained73 baseline binding')
    for row in legal['modelParity']:
        need((row['turnHash'], row['finalHash']) == (row['archivedTurnHash'], row['archivedFinalHash'])
             == old_model_hashes[row['name']], 'Lazy gravity/model changed archived result: ' + row['name'])
    need(legal['gravityCases'] == 9 and len(legal['gravityRows']) == 27
         and all(row['legacyResultHash'] == row['optimizedResultHash']
                 and row['legacySteps'] == row['optimizedSteps'] and row['checkpointHash']
                 for row in legal['gravityRows'])
         and legal['gravityTimings'] and all(row['iterations'] > 0 for row in legal['gravityTimings']),
         'Lazy gravity snapshot, dictionary/RNG or no-op proof incomplete')
    model = native['ModelCommands']
    model_baseline = read('Native/LegalSwapExistence.json', BASE)
    model_hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in model_baseline['modelParity']}
    need(model['modelCases'] == len(model['rows']) == 350 and model['rawTurnParity'] and model['finalSnapshotParity']
         and model['baselineReportSHA256'] == sha(file('Native/LegalSwapExistence.json', BASE))
         and Path(model['baselineReportPath']).resolve() == (BASE / 'Native/LegalSwapExistence.json').resolve(),
         'New75 model profiling is not bound to all350 frozen74 commands')
    need(model['pairedCheckpointParity'] and model['pairedDictionaryParity'] and model['snapshotControls'] == 13
         and model['snapshotControlMatchesArchived74']
         and model['baselineModelSourceSHA256'] == baseline_source['Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs']
         and model['allocationCounter'] in {'GC.GetAllocatedBytesForCurrentThread', 'MonoUsedHeapWithGCDisabled', 'UNAVAILABLE'}
         and model['allocationCounterUsable'] == (model['allocationCounter'] != 'UNAVAILABLE')
         and (not model['allocationCounterUsable'] or model['allocationPositiveControlBytes'] >= 65536),
         'Stable snapshot/source/dictionary/culture or allocation-counter positive control incomplete')
    need({r['name']: (r['turnHash'], r['finalHash']) for r in model['rows']} == model_hashes
         and all((r['baselineTurnHash'], r['baselineFinalHash']) == (r['legacyTurnHash'], r['legacyFinalHash'])
                 == model_hashes[r['name']] and r['checkpointHash'] == r['legacyCheckpointHash']
                 and r['dictionaryOrder'] == r['legacyDictionaryOrder'] for r in model['rows'])
         and len(model['repeated']) == 4
         and all(r['iterations'] == len(r['samples']) == len(r['legacySamples']) == 20
                 and all((s['turnHash'], s['finalHash']) == model_hashes[s['name']]
                 for s in r['samples'] + r['legacySamples']) for r in model['repeated']),
         'Model profiler changed raw/checkpoint/dictionary outcomes or paired repeated controls')
    need(len(model['snapshotRepeated']) == 4
         and all(r['batch'] == 64 and r['iterations'] == len(r['samples']) == len(r['legacySamples']) == 20
                 and all(s['finalHash'] == model_hashes[r['name'].split('/')[0]][1]
                         and s['perSnapshotMs'] >= 0
                         and abs(s['batchMilliseconds'] / r['batch'] - s['perSnapshotMs']) < .000001
                         for s in r['samples'] + r['legacySamples']) for r in model['snapshotRepeated']),
         'Isolated actual post-command Snapshot controls/hash arithmetic are incomplete')
    lookup = native['FrameLookup']
    need(lookup['lookups'] == (lookup['powerClips'] + lookup['obstacleClips']) * 5 > 0
         and lookup['checks'] >= lookup['lookups'] * 2 + 9 and len(lookup['timings']) == 32
         and all(r['iteration'] == i and r['lookups'] > 0 and r['legacyMs'] >= 0 and r['directMs'] >= 0
                 for i, r in enumerate(lookup['timings'])), 'Direct frame lookup identity/LRU/lifecycle controls incomplete')
    idle_native = idle_native_controls(lookup)
    playback_construction = native['PlaybackConstruction']
    need(playback_construction['modelCases'] == 350 and playback_construction['queueComparisons'] == 1400
         and all(playback_construction[k] is True for k in ['exactQueueParity', 'rawInputUnchanged',
                 'compiledSourceMatchesArchive', 'comparedNonserializedTracks', 'comparedContinuationSegments'])
         and playback_construction['baselineSourceSHA256'] == baseline_source['Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPlayback.cs']
         and {r['name'] for r in playback_construction['timings']} == {'L4/-1', 'L48/16', 'L26/7'}
         and all(r['iterations'] == len(r['legacyMs']) == len(r['currentMs']) == 24
                 and all(PROFILE_CONTRACT['finite_nonnegative'](v) for v in r['legacyMs'] + r['currentMs'])
                 for r in playback_construction['timings']),
         'Playback allocation refinements lack exact1400 archived74 queues/hidden tracks/segments and matched CPU proof')
    effects = native['EffectBatchChecks']
    need(effects['preparedDifferingPixels'] == 0 and effects['preparedMaxChannelDelta'] == 0
         and effects['authoredPreparationPlans'] == 50 and 1 <= effects['largestPreparationLevel'] <= 50
         and effects['largestPlannedFrames'] > 0 and effects['futurePressureSprites'] == 1400,
         'Prepared effects change pixels or lack largest-board/cache-headroom proof')
    batcher_source = 'Unity/Assets/HeartOfTheRain/M47/Runtime/EffectMeshBatcher.cs'
    original = file(baseline['source_archive'] + '/' + batcher_source, ROOT).read_text('utf-8-sig')
    original = original[original.index('namespace HeartOfTheRain.M47 {'):].strip().replace(
        'namespace HeartOfTheRain.M47 {', 'namespace HeartOfTheRain.Verification.Baseline74 {').replace(
        'EffectMeshBatcher', 'ArchivedEffectMeshBatcher74')
    need(effects['frozenBaselineSourceSHA256'] == baseline_source[batcher_source]
         and effects['compiledBaselineBodySHA256'] == hashlib.sha256(original.encode('utf-8')).hexdigest()
         and effects['optimizedBaselineDifferingPixels'] == effects['optimizedBaselineMaxChannelDelta'] == 0
         and effects['constructionParityFrames'] == len(effects['constructionParityRows']) == 45
         and all(r['baselineHash'] == r['optimizedHash'] for r in effects['constructionParityRows']),
         'Batch topology/key optimization lacks exact archived74 source/mesh/pixel proof')
    expected_construction = {'level42_double_orb_peak'} | {'density_' + f + '_45_peak' for f in ['crate', 'stone', 'gate', 'tiles']}
    need({r['name'] for r in effects['constructionRows']} == expected_construction
         and all(r['iterations'] == 64 and r['draws'] > 0 and r['baselineMeshes'] == r['optimizedMeshes'] > 0
                 and all(v >= 0 for k, v in r.items() if k.endswith('Ms')) for r in effects['constructionRows']),
         'Matched batch construction CPU controls incomplete')
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
    idle_history = historical_idle_failure(current, digest, before)
    need({p.name.removesuffix('_Data_Audit.json') for p in (OUT / 'Android').glob('*_Data_Audit.json')} == TOOLS,
         'Not all nine final75 Android tools completed')
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
         and len(fluidity['phases']) == 8 and {r['name'] for r in fluidity['phases']} == FLUIDITY_PHASES
         and utc(fluidity['utc']) >= utc(fluidity_install['utc']), 'Fluidity75 incomplete/duplicated/stale')
    touch = read('Android/Touch/Report.json')
    need(touch['apk_sha256'] == digest and touch['serial'] == 'emulator-5556'
         and {row['mode'] for row in touch['cases']} == TOUCH and len(touch['cases']) == 8, 'Touch75 incomplete')
    touch_provenance(touch, build_finished)
    for row in touch['cases']:
        clean(row, row['mode'])
        need(row['status'] == 'PASS_NATIVE_DEVICE_GAMEPLAY_AUDIT' and row['launchCleared'] and row['accepted'], 'Touch rejected/hidden')
        if row['mode'] in MIXED:
            need(row['sourceActivated'] and row['protectedBirth'] and not row['chained'], 'Power protection failed on75')
        need(sha(file('Android/Touch/' + row['mode'] + '_Before.png')) != sha(file('Android/Touch/' + row['mode'] + '_After.png')),
             'Touch75 unchanged/obscured screenshots')
    cascade, profiling = {}, {}
    for variant, count in [('measure', 6), ('visual', 1)]:
        cascade_install = installation('Android/Cascade/' + variant + '/Installation.json', digest, build_finished, before)
        report = read('Android/Cascade/' + variant + '/Report.json')
        clean(report, 'Cascade ' + variant)
        need(report['status'] == 'PASS_CASCADE_PLAYBACK' and len(report['rows']) == count
             and report.get('repeats') == 1 and report['modelWorkEnabled'] is False
             and report['checkpoint74Continuation'] is False and report['visualLevel'] == 4
             and cascade_install['profile_model_work'] is False and cascade_install['checkpoint74_continuation'] is False,
             'Default nine-stage Cascade75 evidence incomplete or enables optional diagnostics/control')
        need(utc(report['utc']) >= utc(cascade_install['utc']), 'Default Cascade report predates final installation')
        cascade[variant] = report
        old = read('Android/Cascade/' + variant + '/Report.json', BASE)
        old_hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
        profiling[variant] = PROFILE_CONTRACT['validate'](report, variant, old_hashes)
    density_profiling = {}
    for family in ['crate', 'stone', 'gate', 'tiles']:
        folder = 'Android/Density/candidate_review-' + family + '/'
        density_install = installation(folder + 'Installation.json', digest, build_finished, before)
        report = read(folder + 'Report.json')
        clean(report, family)
        need(report['status'] == 'PASS_OBSTACLE_DENSITY_PLAYBACK' and report['family'] == family and len(report['rows']) == 10,
             'Density75 incomplete')
        need(utc(report['utc']) >= utc(density_install['utc']), 'Density report predates final installation')
        old = read(folder + 'Report.json', BASE)
        old_hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
        need({r['name']: (r['turnHash'], r['finalHash']) for r in report['rows']} == old_hashes,
             'Density model changed from final73')
        density_profiling[family] = PROFILE_CONTRACT['validate_density'](report, family, old_hashes)
    repeats = repeat_profiles(digest, build_finished, before)
    extras = extra_controls(digest, build_finished, before, continuation, model_hashes)
    comparison = direct_comparison(digest, baseline['apk_sha256'])
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
        'recorded_extra_continuation': recorded_extra_performance(extras['continuation_cases']),
        'fluidity_orb_rocket_p95_ms': next(r['p95Ms'] for r in fluidity['phases'] if r['name'] == 'orb_rocket'),
        'scope': 'Descriptive measured open performance gates. These commands exceed a single60fps frame; '
                 'repeated fresh banks isolate neither a causal optimization nor cold-device conditions. '
                 'Recorded continuation controls retain their separate larger command/interval extremes. '
                 'The development timers add overhead; native Render completion is not displayed-pixel latency.'}
    reg_install = installation('Android/Regression/Installation.json', digest, build_finished)
    regression = read('Android/Regression/Regression.json')
    clean(regression, 'Full regression75')
    need(regression['status'] == 'PASS_NATIVE_REGRESSION' and regression['boards'] == 50 and regression['clips'] >= 354
         and regression['checks'] >= 1716 and regression['labels'] >= 14105
         and regression['actions'] >= 408 and len(regression['damageFamilies']) == 8
         and utc(regression['utc']) >= utc(reg_install['utc']), 'Full50-board Android regression75 incomplete')
    need({'Native refill button spends 900 and fills all five lives', 'Repeated native refill callback charges exactly once',
          'Confirmed decline charges exactly one life, no coins, and opens retry pre-level'}.issubset(regression['passed']),
         'Life/Continue settlement device controls missing on75')
    idle_controls = idle_device_controls(read('Android/Regression/M70_Device.json'), regression, reg_install)

    # Final visual contracts are supplied by actual post-build inspection, never this collector.
    review = bound_visual('Visual_Review.json', 'REVIEWED_VISIBLE_ANDROID_GAMEPLAY75', digest)
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
    need(tool_review['sourceCheckpoint'] == 75 and tool_review['apk_bytes'] == artifact['bytes']
         and set(method['contact_sheets']) == tool_sheets
         and set(method['constituent_originals']) == tool_originals
         and set(method['full_originals_also_inspected']) == full_tool_originals
         and tool_originals | tool_sheets <= set(tool_review['artifactSHA256'])
         and not tool_review['new_confirmed_rendering_discrepancies']
         and tool_review['remaining_gameplay_defects'], 'Final75 power-pair/tool inspection incomplete or failed')
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
    need(power_review['sourceCheckpoint'] == 75 and power_review['baselineOnly'] is False
         and power_review['currentFinalAPKCertified'] is True and len(power_review['cases']) == 6
         and {row['mode'] for row in power_review['cases']} == MIXED,
         'Power visual review is not the six final75 gestures')
    need(all(row['sourceActivated'] and row['protectedBirth'] and row['launchCleared'] and not row['chained']
             and row['creationPoseKeys'] and row['lastRewardPose']['phase'] == 'idle'
             for row in power_review['cases']), 'Final75 visual power survival is incomplete')
    need(all('Android/Touch/' + mode + '.mp4' in power_review['artifactSHA256']
             and 'Android/Touch/' + mode + '_Report.json' in power_review['artifactSHA256'] for mode in MIXED),
         'Power visual review does not bind all six current movies/reports')
    timing = bound_visual('Timing_Visual_Notes.json', 'REVIEWED_LOCAL_CONTINUATION75_WITH_REMAINING_GATES', digest)
    need(timing.get('remainingGates') and timing.get('localMatch'), 'Timing review omits residual gates/local measurement')
    match = timing['localMatch']
    new_gap = match['contactToReactionBoundMs']
    need(match['case'] == 'L4_0_30' and len(new_gap) == 2 and 0 <= new_gap[0] <= new_gap[1]
         and match['baselineContactToReactionBoundMs'] == old_gap, 'Visible L4 control bounds do not bind archived74')
    continuation_visual = timing['newContinuationCases']
    need({r['level'] for r in continuation_visual} == {14, 31, 33} and len(continuation_visual) == 3
         and all(r['control74Folder'] == 'ExtraContinuation/L' + str(r['level']) + '/control74/visual/'
                 and r['refined75Folder'] == 'ExtraContinuation/L' + str(r['level']) + '/refined75/visual/'
                 and r['routeContinuityReviewed'] is True and r['landingIntoIdleReviewed'] is True and r['visualFinding']
                 and r['measurementLimitations']
                 for r in continuation_visual), 'Three actual new continuation control/route/landing reviews are missing')
    for row in continuation_visual:
        for mode in ['control74', 'refined75']:
            observation = row[mode]
            contact, reaction = observation['contactBracketPts'], observation['firstVisibleReactionBracketPts']
            need(len(contact) == len(reaction) == len(observation['contactToReactionBoundMs']) == 2 and 0 <= contact[0] <= contact[1]
                 and 0 <= reaction[0] <= reaction[1] and reaction[1] >= contact[0]
                 and observation['ptsIndex'] in timing['artifactSHA256']
                 and all(abs(a - b) <= .002 for a, b in zip(observation['contactToReactionBoundMs'],
                     [max(0, (reaction[0] - contact[1]) * 1000), (reaction[1] - contact[0]) * 1000])),
                 'New continuation visible bounds fail two-endpoint arithmetic or lack original-PTS binding')
    for row in extras['continuation_cases']:
        for name in ['HR_NaturalCascade.mp4', 'Report.json', 'Installation.json']:
            need(row['folder'] + name in timing['artifactSHA256'], 'New continuation review omits actual source movie/report')
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
    analysis = bound_visual('Timing_Analysis.json', 'ANALYZED_LOCAL_CONTINUATION75_WITH_REMAINING_GATES', digest)
    need(analysis.get('remainingGates') and analysis['localMatch'] == match
         and analysis['acceptedSwap'] == swap
         and analysis['newContinuationCases'] == continuation_visual
         and analysis['analyzerSHA256'] == sha(Path(__file__).with_name('analyze_gameplay75_timing.py'))
         and analysis['profilingValidatorSHA256'] == sha(Path(__file__).with_name('validate_gameplay74_profile.py'))
         and set(timing['remainingGates']) <= set(analysis['remainingGates'])
         and analysis['nativeLocalHandoff'] == continued_renderers
         and analysis['counts'] == {'fluidity': 8, 'cascadeMeasure': len(cascade['measure']['rows']), 'cascadeVisual': 1,
                                    'density': 40, 'nativeModelCases': 350},
         'Timing analysis drops remaining gates or does not match final source measurements')
    recorded = performance_gates['recorded_extra_continuation']
    need(abs(analysis['observedPerformanceExtremes']['largestRecordedExtraCommandMs']
             - recorded['maxCommand']['commandMs']) < .000001
         and abs(analysis['observedPerformanceExtremes']['largestRecordedExtraIntervalMs']
                 - recorded['maxInterval']['maxIntervalMs']) < .000001,
         'Timing analysis omits or understates recorded continuation command/interval extremes')
    for label, report in [('Timing review', timing), ('Timing analysis', analysis)]:
        gates = ' '.join(report['remainingGates'])
        need('record' in gates.lower() and 'L31' in gates
             and format(recorded['maxCommand']['commandMs'], '.3f') in gates
             and format(recorded['maxInterval']['maxIntervalMs'], '.3f') in gates,
             label + ' remaining gates omit the separately recorded L31 command/interval stall')

    result = {
        'status': 'PASS_TARGETED_GAMEPLAY75_WITH_REMAINING_PERFORMANCE_GATES',
        'utc': datetime.now(timezone.utc).isoformat(), 'source_checkpoint': 75,
        'source_inputs': len(current), 'source_sha256': sha(file('Source_SHA256.json')),
        'baseline_checkpoint': 74, 'baseline_apk_sha256': baseline['apk_sha256'],
        'apk_sha256': digest, 'apk_bytes': artifact['bytes'],
        'non_development_compile_build_passed': True, 'non_development_apk_installed': False,
        'native_suites': len(native), 'native_checks': sum(BASE_CONTRACT['checks'](r) for r in native.values()),
        'raw_turn_and_final_hash_parity': True, 'native_model_cases': 350, 'native_mixed_cases': 30,
        'native_accepted_handoffs': continuation['acceptedHandoffs'], 'native_guard_cases': continuation['guardCases'],
        'new_qualifying_authored_turns': continuation['newQualifyingTurns'],
        'seeded_terminal_controls': continuation['seededCases'],
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
        'stable_snapshot_controls': model['snapshotControls'],
        'model_allocation_counter': model['allocationCounter'],
        'model_allocation_counter_usable': model['allocationCounterUsable'],
        'matched_native_effect_cpu_cases': len(effects['constructionRows']),
        'native_direct_lookup_identities': lookup['lookups'],
        'bounded_native_idle_device_observations': idle_controls,
        'native_idle_observer_controls': idle_native,
        'historical_idle_sampling_failure': idle_history,
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
                    'extra_continuation_movies': len(extras['continuation_cases']),
                    'extra_model_stage_rows': extras['model_stage_rows'],
                    'independently_reviewed_power_movies': 6,
                    'independently_reviewed_power_tool_sheets': len(tool_sheets),
                    'power_tool_sheet_constituent_captures': len(tool_originals),
                    'boards': 50, 'checks': regression['checks'], 'clips': regression['clips'], 'actions': regression['actions']},
        'qa_data_unchanged': True, 'main_apk_updated': False,
        'scope': 'Native frame lookup caches preserve sprite identity and LRU/disposal ownership; effect texture keys '
                 'and retained triangle prefixes preserve archived74 uploaded geometry/material/order and pixels. '
                 'Stable model snapshots retain detached ownership, exact raw/checkpoint/dictionary outcomes and culture/tie rules. '
                 'Guarded terminal-only continuation expands the established authored corpus from one to four qualifying turns, '
                 'at most one handoff per turn. Fresh25-suite native proof, actual non-development compilation, nine same-APK '
                 'QA tools,36 repeated process-control rows, six separately recorded continuation controls and six separate '
                 'model-stage diagnostics retain their distinct scopes. Existing birth protection,900-coin refill, '
                 'warmup/pinned budgets and conservative unsupported-case fallbacks remain intact.',
        'profiling': profiling['measure'],
        'density_profiling': density_profiling,
        'repeated_process_profiling': {'processes': repeats['processes'], 'rows': repeats['rows'], 'scope': repeats['scope']},
        'remaining_performance_measurements': performance_gates,
        'direct_profile_comparison': {'path': 'Profile_Comparison74_75.json', 'status': comparison['status'],
                                     'scope': comparison['scope'], 'limits': comparison['limits']},
        'new_continuation_visual_controls': continuation_visual,
        'reference_scope': 'Direct build comparisons use the final checkpoint74 reports; new continuation controls '
                           'use the preserved74 planner and refined75 planner within the same final75 APK. '
                           'Match Villains comparisons remain archived observations with original sampling/version limits; '
                           'no fresh reference gameplay, identical-board physics, or competitor parity is established.',
        'remaining_gameplay_defects': analysis['remainingGates'],
        'limits': ['Three new guarded terminal fixtures reduce local reaction; '
                   'L4 is unchanged within sampling uncertainty; fallback waits remain.',
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
    checkpoint = {'utc': result['utc'], 'status': result['status'], 'source_checkpoint': 75, 'installed_checkpoint': 64,
                  'qa_installed_checkpoint': 75, 'source_sha256': result['source_sha256'],
                  'review': 'Codex_Handoff/Documentation/75_DENSE_EFFECTS_CPU_REVIEW.md',
                  'summary': 'Verification/Evidence/Gameplay75/Summary.json', 'android_apk_sha256': digest,
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
