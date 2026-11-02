"""Describe matched construction/effect controls without certifying smooth gameplay.

build() only reads evidence. The CLI writes the two reports after all required
inputs validate; no Unity, Android, visual approval or collector is invoked.
"""
import argparse
import hashlib
import json
import math
import runpy
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Gameplay76'
BASE = ROOT / 'Verification/Evidence/Gameplay75'
COMMAND = runpy.run_path(str(Path(__file__).with_name('run_smoothness_command_device.py')), run_name='command_contract_only')
PRIOR = runpy.run_path(str(Path(__file__).with_name('collect_gameplay75_results.py')), run_name='prior_contract_only')
PROFILE = PRIOR['PROFILE_CONTRACT']
STAGES = ('renderMs', 'updateMs', 'sampleMs', 'bodySampleMs', 'effectsSampleMs', 'sortMs',
          'lookupMs', 'batchAddMs', 'batchUploadMs', 'spriteUpdateMs', 'bankEndMs')


def need(value, message):
    if not value:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def stats(values):
    values = sorted(values)
    need(values and all(PROFILE['finite_nonnegative'](v) for v in values), 'Invalid native span samples')
    return {'samples': len(values), 'median': statistics.median(values),
            'p95': values[math.ceil(len(values) * .95) - 1], 'max': max(values)}


def differences(old, new, keys):
    return {key: {'baseline75': old[key], 'current76': new[key],
                  'currentMinusBaseline75': new[key] - old[key]} for key in keys}


def transform_differences(old, new, keys):
    return {key: {'control75Transform': old[key], 'current76Transform': new[key],
                  'currentMinusControl75Transform': new[key] - old[key]} for key in keys}


def normalize_cascade_cadence(report):
    """Describe actual intervals against each fixture's requested cadence."""
    rows = []
    for index, row in enumerate(report['rows']):
        target = row['targetFps']
        need(target in [15, 30, 60] and target == int(row['baseCase'].rsplit('_', 1)[1]),
             'Cascade requested cadence differs from its fixture identity')
        frames = [f for f in report['frameSamples'] if f['row'] == index and f['timingWindow']]
        need(len(frames) == row['frames'] > 0
             and all(PROFILE['finite_nonnegative'](f['intervalMs']) for f in frames),
             'Cascade cadence lacks complete timing-window intervals')
        maximum = max(f['intervalMs'] for f in frames)
        need(abs(maximum - row['maxIntervalMs']) < .001, 'Cascade raw maximum interval differs from frames')
        budget = 1000.0 / target
        rows.append({'name': row['name'], 'baseCase': row['baseCase'], 'targetFps': target,
            'targetIntervalMs': budget, 'maxIntervalMs': maximum,
            'maxIntervalBudgetRatio': maximum / budget,
            'maxExcessOverTargetMs': max(0, maximum - budget), 'timedFrames': len(frames),
            'framesOver1_5TargetBudget': sum(f['intervalMs'] > budget * 1.5 for f in frames),
            'rawLateFramesOver100Ms': row['lateFrames']})
    need(len(rows) == 6 and {r['targetFps'] for r in rows} == {15, 30, 60},
         'Cadence description omits an ordinary target rate')
    return {'rows': rows, 'maxRow': max(rows, key=lambda r: r['maxIntervalMs']),
            'maxByTargetFps': {str(fps): max((r for r in rows if r['targetFps'] == fps), key=lambda r: r['maxIntervalMs'])
                               for fps in [15, 30, 60]},
            'lateFrameCountByTargetFps': {str(fps): sum(r['framesOver1_5TargetBudget'] for r in rows if r['targetFps'] == fps)
                                         for fps in [15, 30, 60]},
            'scope': 'Each timing-window interval is compared with1000/targetFps. The diagnostic late count '
                     'uses an explicit1.5x target-interval threshold; the original fixed100ms count is retained '
                     'separately. A normal15fps interval is about66.67ms and is not intrinsically a stall. '
                     'These counts describe observed cadence, not touch latency, GPU timing or sustained60fps certification.'}


def density_costs(report):
    """Generic tagged-cost proof for real16-row pairs or ordinary10-row reports."""
    need(report['status'] == 'PASS_OBSTACLE_DENSITY_PLAYBACK' and not report['errors']
         and report['profilingSchemaVersion'] == 1, 'Density native status/schema failed')
    frames = report['frames']
    need(frames and {f['phase'] for f in frames} == set(range(len(report['rows'])))
         and all(a['frame'] < b['frame'] and a['absoluteWall'] <= b['absoluteWall']
                 for a, b in zip(frames, frames[1:])), 'Density frame ownership/order failed')
    summaries = []
    for index, row in enumerate(report['rows']):
        selected = [f for f in frames if f['phase'] == index]
        need(selected and selected[0]['frame'] == row['commandFrame']
             and 0 < row['commandStartedWall'] <= row['commandFinishedWall']
             and row['commandMs'] + .1 >= row['modelMs'] + row['acceptMs']
             and (row['commandFinishedWall'] - row['commandStartedWall']) * 1000 + .1 >= row['commandMs'],
             'Density command-frame/span ownership failed')
        need(row['enqueueCost']['frame'] == row['commandFrame']
             and row['enqueueCost']['phases'] > 0
             and row['acceptMs'] + .1 >= row['enqueueCost']['totalMs'], 'Density enqueue provenance failed')
        for f in selected:
            cost = f['cost']
            need(cost['frame'] == f['frame']
                 and 0 < cost['updateStartedWall'] <= cost['renderStartedWall'] <= cost['renderFinishedWall']
                 <= cost['updateFinishedWall'] <= f['absoluteWall']
                 and all(PROFILE['finite_nonnegative'](cost[k]) for k in STAGES)
                 and all(f[k] == cost[k] for k in ['renderMs', 'updateMs', 'sampleMs', 'bodySampleMs', 'effectsSampleMs', 'sortMs'])
                 and PROFILE['finite_nonnegative'](f['intervalMs']), 'Mixed/nonfinite density frame costs')
            if report.get('detailedDrawCosts') is False:
                need(all(cost[k] == 0 for k in ['lookupMs', 'batchAddMs', 'spriteUpdateMs']),
                     'Coarse report still records detailed per-draw timers')
        command = selected[0]
        prior = command['cost']['updateFinishedWall'] <= row['commandStartedWall']
        after = command['cost']['updateStartedWall'] >= row['commandFinishedWall']
        need(prior or after, 'Density command overlaps a differently owned native cost')
        if prior:
            need((command['absoluteWall'] - command['cost']['updateFinishedWall']) * 1000 + .1 >= row['commandMs'],
                 'Density command tail lost')
        playback = [f for f in selected if f['cost']['updateStartedWall'] >= row['commandFinishedWall'] and f['cost']['kind'] != 'idle']
        need(playback, 'No tagged post-command density playback')
        worst_render = max(selected, key=lambda f: f['cost']['renderMs'])
        worst_interval = max(selected, key=lambda f: f['intervalMs'])
        stages = {key: stats([f['cost'][key] for f in playback]) for key in STAGES}
        summary = {k: row[k] for k in ['name', 'family', 'crates', 'turnHash', 'finalHash', 'commandMs', 'modelMs', 'acceptMs',
                                      'preparationSeconds', 'settleSeconds', 'commandFrame', 'commandStartedWall', 'commandFinishedWall']}
        summary.update(checkpoint75Transform=row.get('checkpoint75Transform', False),
                       enqueueCost=row['enqueueCost'], capturedFrames=len(selected),
                       playbackCostFrames=len(playback), renderStageStats=stages,
                       worstCapturedRenderMs=worst_render['cost']['renderMs'],
                       maxIntervalMs=worst_interval['intervalMs'],
                       worstRenderFrame=worst_render, worstIntervalFrame=worst_interval,
                       worstRenderNeighbors=[f for f in selected if abs(f['frame'] - worst_render['frame']) <= 2],
                       worstIntervalNeighbors=[f for f in selected if abs(f['frame'] - worst_interval['frame']) <= 2],
                       commandFrameTail=command,
                       resourceActivity={k: row[k] for k in ['renderersCreated', 'crateSpritesCreated', 'gen0Collections']})
        summaries.append(summary)
    return summaries


def paired_density_extremes(paired_density):
    """Retain branch/mode extrema and their actual cost/command ownership."""
    records = [dict(row, mode=mode, folder='PairedDensity/' + data[mode]['variant'] + '/')
               for data in paired_density.values() for mode in ['detailed', 'coarse'] for row in data[mode]['rows']]

    def attribution(row, interval=False):
        frame = row['worstIntervalFrame'] if interval else row['worstRenderFrame']
        cost = frame['cost']
        components = {k: cost[k] for k in ['sampleMs', 'lookupMs', 'batchAddMs', 'batchUploadMs', 'spriteUpdateMs', 'bankEndMs']}
        return {'family': row['family'], 'mode': row['mode'], 'folder': row['folder'], 'name': row['name'],
            'checkpoint75Transform': row['checkpoint75Transform'],
            'commandFrame': row['commandFrame'], 'commandStartedWall': row['commandStartedWall'],
            'commandFinishedWall': row['commandFinishedWall'],
            'commandMs': row['commandMs'], 'modelMs': row['modelMs'], 'acceptMs': row['acceptMs'],
            'enqueueCost': row['enqueueCost'], 'costPredatesCommand': cost['updateFinishedWall'] <= row['commandStartedWall'],
            'costFollowsCommand': cost['updateStartedWall'] >= row['commandFinishedWall'],
            'secondsFromCommandFinishToCostStart': cost['updateStartedWall'] - row['commandFinishedWall'],
            'frame': frame, 'neighbors': row['worstIntervalNeighbors'] if interval else row['worstRenderNeighbors'],
            'perDrawTimersEnabled': row['mode'] == 'detailed',
            'rowGen0Collections': row['resourceActivity']['gen0Collections'],
            'resourceActivity': row['resourceActivity'], 'topLevelRenderComponentsMs': components,
            'unclassifiedRenderElapsedMs': cost['renderMs'] - sum(components.values()),
            'renderWallSpanMs': (cost['renderFinishedWall'] - cost['renderStartedWall']) * 1000,
            'scope': 'The nested FrameCost owns its timestamped Update/Render; the following interval includes '
                     'other frame/host scheduling work. Sampling children are nested and must not be added again '
                     'to sampleMs. The remaining Render elapsed value includes unbracketed work and timer/host '
                     'effects, not an exclusive CPU category. Coarse per-draw zeros mean disabled timers, '
                     'not absent lookup/Add/SpriteRenderer execution. Gen0 is recorded only for the entire row; no '
                     'frame-local collection or exclusive CPU/OS/driver cause is established.'}

    result = {}
    for label, control in [('current76', False), ('control75Transform', True)]:
        selected = [r for r in records if r['checkpoint75Transform'] is control]
        need(len(selected) == 32, 'Paired density branch extrema omit rows')
        result[label] = {'worstRender': attribution(max(selected, key=lambda r: r['worstCapturedRenderMs'])),
                         'worstInterval': attribution(max(selected, key=lambda r: r['maxIntervalMs']), True),
                         'byFamilyMode': []}
        for family in ['crate', 'stone']:
            for mode in ['detailed', 'coarse']:
                group = [r for r in selected if r['family'] == family and r['mode'] == mode]
                need(len(group) == 8, 'Paired density mode extrema omit rows')
                render = max(group, key=lambda r: r['worstCapturedRenderMs'])
                interval = max(group, key=lambda r: r['maxIntervalMs'])
                result[label]['byFamilyMode'].append({'family': family, 'mode': mode,
                    'worstRenderName': render['name'], 'worstRenderMs': render['worstCapturedRenderMs'],
                    'worstIntervalName': interval['name'], 'worstIntervalMs': interval['maxIntervalMs']})
    return result


def build(out=OUT):
    out = Path(out).resolve()
    bindings, external = {}, {}

    def read(name, base=None):
        base = out if base is None else base
        path = (base / name).resolve()
        need(path.is_relative_to(base.resolve()) and path.is_file(), 'Missing/unsafe performance input: ' + str(path))
        data = json.loads(path.read_text('utf-8-sig'))
        need(not any(data.get(k) for k in ['error', 'errors', 'failures', 'failed']), 'Failed performance input: ' + str(path))
        if base == out:
            bindings[path.relative_to(out).as_posix()] = sha(path)
        else:
            external[path.relative_to(ROOT).as_posix()] = sha(path)
        return data

    artifact = read('APK_Artifact.json')
    digest = artifact['sha256']
    source_path = out / 'Source_SHA256.json'
    source = read('Source_SHA256.json')
    source_sha = sha(source_path)
    build_process = read('AndroidBuild_Process.json')
    need(build_process['exitCode'] == 0 and not build_process['timedOut']
         and utc(source['utc']) <= utc(build_process['startedUtc']) <= utc(build_process['finishedUtc']),
         'Performance data lacks a successful final-source build')
    finished = utc(build_process['finishedUtc'])
    baseline = read('Baseline75.json')
    old_summary = read('Summary.json', BASE)
    old_source = read('Source_SHA256.json', BASE)
    need(sha(BASE / 'Summary.json') == baseline['summary_sha256']
         and sha(BASE / 'Source_SHA256.json') == baseline['source_sha256']
         and old_summary['source_sha256'] == baseline['source_sha256']
         and old_summary['apk_sha256'] == baseline['apk_sha256'] != digest,
         'Sealed75 baseline/source/APK binding failed')
    before = read('Android/Before.json')

    def installed(folder, report, expected_digest=digest, base=None):
        install = read(folder + 'Installation.json', base)
        need(install['serial'] == 'emulator-5556'
             and install.get('apk_sha256', install.get('sha256')) == expected_digest
             and install.get('installed_apk_sha256', expected_digest) == expected_digest
             and utc(report['utc']) >= utc(install['utc']), 'Performance report predates its APK/device installation')
        if base is None or base.resolve() == out:
            need(utc(install['utc']) >= finished, 'Performance report uses an older build')
            if 'data_unchanged' in install:
                need(install['data_unchanged'] is True and install['before'] == install['after'] == before,
                     'Performance control changed real QA data')
        need(install.get('runtime_errors', 0) == 0, 'Runtime error in performance control')
        return install

    command = read('CommandPairs/Report.json')
    command_install = installed('CommandPairs/', command)
    need(command_install['status'] == 'PASS_SAME_APK_COMMAND_DEVICE_AUDIT76'
         and command_install['data_unchanged'] is True
         and utc(command_install['finishedUtc']) >= utc(command['utc']), 'Command pair process/save audit failed')
    validation = COMMAND['validate_report'](command)
    command_rows = []
    for row in command['rows']:
        item = {k: row[k] for k in ['name', 'turnHash', 'finalHash', 'baselineMedianMs', 'currentMedianMs',
                'baselineP95Ms', 'currentP95Ms', 'baselineMaxMs', 'currentMaxMs']}
        deltas = [p['currentMs'] - p['baselineMs'] for p in row['pairs']]
        item.update(pairCount=12, medianPairedDifferenceMs=statistics.median(deltas),
                    medianDifferenceMs=row['currentMedianMs'] - row['baselineMedianMs'],
                    currentSlowerPairs=sum(v > 0 for v in deltas),
                    baselinePairsWithGen0=sum(p['baselineGc0After'] > p['baselineGc0Before'] for p in row['pairs']),
                    currentPairsWithGen0=sum(p['currentGc0After'] > p['currentGc0Before'] for p in row['pairs']),
                    baselineGen0Collections=sum(p['baselineGc0After'] - p['baselineGc0Before'] for p in row['pairs']),
                    currentGen0Collections=sum(p['currentGc0After'] - p['currentGc0Before'] for p in row['pairs']))
        command_rows.append(item)

    paired_density = {}
    for family in ['crate', 'stone']:
        variants = {}
        for label, variant in [('detailed', 'paired_1-' + family), ('coarse', 'paired_coarse_1-' + family)]:
            folder = 'PairedDensity/' + variant + '/'
            raw = read(folder + 'Report.json')
            installed(folder, raw)
            need(raw['variant'] == variant and raw['family'] == family and len(raw['rows']) == 16
                 and raw['detailedDrawCosts'] is (label == 'detailed'), 'Paired density mode/coverage differs')
            rows = density_costs(raw)
            pairs = []
            for index, (a, b) in enumerate(zip(rows[::2], rows[1::2])):
                repeat, count = index // 2, [1, 45][index % 2]
                need(a['checkpoint75Transform'] is (repeat % 2 == 0)
                     and b['checkpoint75Transform'] is (repeat % 2 != 0), 'Paired density order is not balanced AB/BA')
                old, new = (a, b) if a['checkpoint75Transform'] else (b, a)
                need(old['name'] == family + '_' + str(count) + '_' + str(repeat) + '_control75'
                     and new['name'] == family + '_' + str(count) + '_' + str(repeat) + '_current76'
                     and (old['turnHash'], old['finalHash'], old['crates']) == (new['turnHash'], new['finalHash'], new['crates'])
                     and old['crates'] == count, 'Paired density changes raw/final model fixture')
                pairs.append({'family': family, 'count': count, 'repeat': repeat,
                    'control75': old['name'], 'current76': new['name'],
                    'command': transform_differences(old, new, ['commandMs', 'modelMs', 'acceptMs', 'worstCapturedRenderMs', 'maxIntervalMs']),
                    'renderStageStats': {key: transform_differences(old['renderStageStats'][key], new['renderStageStats'][key], ['median', 'p95', 'max']) for key in STAGES}})
            variants[label] = {'variant': variant, 'rows': rows, 'pairs': pairs}
        coarse_rows = {r['name']: r for r in variants['coarse']['rows']}
        cross = []
        for row in variants['detailed']['rows']:
            other = coarse_rows[row['name']]
            need((row['turnHash'], row['finalHash']) == (other['turnHash'], other['finalHash']), 'Detailed/coarse density model differs')
            cross.append({'name': row['name'], 'detailedRenderMedianMs': row['renderStageStats']['renderMs']['median'],
                          'coarseRenderMedianMs': other['renderStageStats']['renderMs']['median'],
                          'coarseMinusDetailedRenderMedianMs': other['renderStageStats']['renderMs']['median'] - row['renderStageStats']['renderMs']['median'],
                          'detailedWorstCapturedRenderMs': row['worstCapturedRenderMs'], 'coarseWorstCapturedRenderMs': other['worstCapturedRenderMs']})
        variants['detailedVersusCoarse'] = cross
        variants['scope'] = 'Only the checkpoint75/current effect transform implementation alternates within one process per mode; all other code remains current76. Fresh boards/banks are prepared per branch. Detailed/coarse reports are separate process launches; their difference does not isolate timer overhead or a causal speedup. Playback frame counts/poses need not align.'
        paired_density[family] = variants

    def cascade(base, expected_digest):
        report = read('Android/Cascade/measure/Report.json', base)
        installed('Android/Cascade/measure/', report, expected_digest, base)
        need(report['repeats'] == 1 and report['modelWorkEnabled'] is False
             and report['checkpoint74Continuation'] is False, 'Ordinary cascade enables a different diagnostic/control')
        hashes = {r['baseCase']: (r['turnHash'], r['finalHash']) for r in read('Android/Cascade/measure/Report.json', BASE)['rows']}
        return PROFILE['validate'](report, 'measure', hashes)

    old_cascade, current_cascade = cascade(BASE, baseline['apk_sha256']), cascade(out, digest)
    cadence = normalize_cascade_cadence(read('Android/Cascade/measure/Report.json'))
    prior_rows = {r['baseCase']: r for r in old_cascade['rows']}
    cascade_rows = []
    for row in current_cascade['rows']:
        old = prior_rows[row['baseCase']]
        cascade_rows.append({'name': row['baseCase'],
            'command': differences(old, row, ['modelMs', 'acceptMs', 'commandMs', 'firstCommandRenderMs', 'maxIntervalMs', 'commandFrameAfterUpdateElapsedMs']),
            'enqueue': differences(old['enqueueCost'], row['enqueueCost'], PROFILE['COMMAND_STAGES']),
            'medianRenderStageMs': differences(old['medianRenderStageMs'], row['medianRenderStageMs'], PROFILE['FRAME_STAGES']),
            'maxRenderStageMs': differences(old['maxRenderStageMs'], row['maxRenderStageMs'], PROFILE['FRAME_STAGES'])})
    old_fluid = read('Android/Fluidity/Measurement.json', BASE)
    fluid = read('Android/Fluidity/Measurement.json')
    installed('Android/Fluidity/', old_fluid, baseline['apk_sha256'], BASE)
    installed('Android/Fluidity/', fluid)
    for raw in [old_fluid, fluid]:
        need(raw['status'] == 'RECORDED_NATIVE_FLUIDITY' and raw['isolatedProfile'] and raw['launchCleared']
             and len(raw['phases']) == 8 and {r['name'] for r in raw['phases']} == PRIOR['FLUIDITY_PHASES'], 'Ordinary fluidity cases differ')
    old_phases = {r['name']: r for r in old_fluid['phases']}
    fluid_rows = [{'name': r['name'], 'metrics': differences(old_phases[r['name']], r,
                  ['modelMs', 'acceptMs', 'commandMs', 'firstPresentationMs', 'preparationSeconds', 'settleSeconds', 'p95Ms', 'worstMs'])} for r in fluid['phases']]
    ordinary_density, current_density = {}, {}
    for family in ['crate', 'stone', 'gate', 'tiles']:
        folder = 'Android/Density/candidate_review-' + family + '/'
        old_raw, raw = read(folder + 'Report.json', BASE), read(folder + 'Report.json')
        installed(folder, old_raw, baseline['apk_sha256'], BASE)
        installed(folder, raw)
        hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old_raw['rows']}
        PROFILE['validate_density'](old_raw, family, hashes)
        PROFILE['validate_density'](raw, family, hashes)
        old_rows = {r['name']: r for r in density_costs(old_raw)}
        current_density[family] = density_costs(raw)
        ordinary_density[family] = [{'name': r['name'],
            'metrics': differences(old_rows[r['name']], r, ['commandMs', 'modelMs', 'acceptMs', 'preparationSeconds', 'settleSeconds', 'worstCapturedRenderMs', 'maxIntervalMs']),
            'renderStageStats': {key: differences(old_rows[r['name']]['renderStageStats'][key], r['renderStageStats'][key], ['median', 'p95', 'max']) for key in STAGES}}
            for r in current_density[family]]

    targeted = {}
    for name in ['SmoothnessCommand', 'EffectBatchChecks', 'LocalContinuation']:
        report, process = read('Native/' + name + '.json'), read('Native/' + name + '_Process.json')
        inputs = read(process['sourceManifest'])
        need(process['exitCode'] == 0 and not process['timedOut'] and inputs['files'] == source['files']
             and sha(out / process['sourceManifest']) == process['sourceSHA256']
             and utc(source['utc']) <= utc(process['startedUtc']) <= utc(report['utc']) <= utc(process['finishedUtc']) <= finished,
             'Native matched control is stale or compiled against different inputs')
        targeted[name] = report
    native_command, native_effect = targeted['SmoothnessCommand'], targeted['EffectBatchChecks']
    need(native_command['status'] == 'PASS_NATIVE_SMOOTHNESS_COMMAND76' and native_command['modelCases'] == 350
         and native_command['queueComparisons'] == 1400 and native_command['sourceFiles'] == 3
         and len(native_command['sourceBindings']) == 3
         and all(r['compiledExactAdaptation'] is True and r['sha256'] == old_source['files'][r['path']]
                 for r in native_command['sourceBindings'])
         and len(native_command['timings']) == 8 and all(len(r['pairs']) == 12 for r in native_command['timings'])
         and all(native_command[k] is True for k in ['exactQueueParity', 'rawInputUnchanged', 'rawTurnParity', 'finalSnapshotParity', 'compiledSourceMatchesArchive']), 'Compiled command control parity incomplete')
    need(native_effect['status'] == 'PASS_NATIVE_EFFECT_BATCH' and native_effect['transformParityFrames'] == 65
         and len(native_effect['transformParityRows']) == 65
         and all(r['baselineHash'] == r['optimizedHash'] for r in native_effect['transformParityRows'])
         and {r['name'] for r in native_effect['transformPixelRows']} == {'actual_peak', 'mixed_zero_rotation_flip_scale_tint'}
         and all(r['differingPixels'] == r['maxChannelDelta'] == 0 for r in native_effect['transformPixelRows'])
         and native_effect['frozen75SourceSHA256'] == old_source['files']['Unity/Assets/HeartOfTheRain/M47/Runtime/EffectMeshBatcher.cs']
         and len(native_effect['transformRows']) == 15
         and all(r['iterations'] == 64 and r['draws'] == r['zeroAngleDraws'] + r['nonzeroAngleDraws'] > 0
                 for r in native_effect['transformRows']), 'Native strict75 transform mesh/pixel/CPU controls failed')

    native_continuation = targeted['LocalContinuation']
    need(native_continuation['modelCases'] == 350 and native_continuation['rawTurnParity']
         and native_continuation['finalSnapshotParity'], 'Recorded controls lack final native model parity')
    native_turns = {r['name']: r for r in native_continuation['rows']}
    recorded = []
    for level in [4, 14, 31, 33]:
        folder = 'Android/Cascade/visual/' if level == 4 else 'ContinuationVisual/L' + str(level) + '/visual/'
        report = read(folder + 'Report.json')
        install = installed(folder, report)
        need(PROFILE['RUNNER']['validate_report'](report, 'visual', 1, require_profiling=True)
             and report['variant'] == install['variant'] == 'visual'
             and report['visualLevel'] == install['visual_level'] == level
             and report['checkpoint74Continuation'] is False and install['checkpoint74_continuation'] is False
             and report['modelWorkEnabled'] is False and install['profile_model_work'] is False,
             'Recorded current continuation request/control differs: ' + folder)
        row = report['rows'][0]
        native_row = native_turns['L' + str(level) + '_match']
        need(row['name'] == row['baseCase'] == 'L' + str(level) + '_0_30'
             and row['targetFps'] == 30
             and (row['turnHash'], row['finalHash'])
             == (native_row['refinedTurnHash'], native_row['refinedFinalHash'])
             == (native_row['sequentialTurnHash'], native_row['sequentialFinalHash']),
             'Recorded continuation raw/final model result differs: ' + folder)
        movie = (out / folder / 'HR_NaturalCascade.mp4').resolve()
        need(movie.is_relative_to(out) and movie.is_file() and movie.stat().st_size > 65536,
             'Recorded continuation lacks usable movie bytes: ' + folder)
        bindings[movie.relative_to(out).as_posix()] = sha(movie)
        trace = [f for f in report['frameSamples'] if f['row'] == 0]
        timed = [f for f in trace if f['timingWindow']]
        need(len(timed) == row['frames'] > 0, 'Recorded continuation timing window is incomplete')
        worst = max(timed, key=lambda f: f['intervalMs'])
        need(abs(worst['intervalMs'] - row['maxIntervalMs']) < .001,
             'Recorded maximum interval differs from raw timing-window frames')
        command_frame = [f for f in trace if f['frame'] == row['commandFrame']]
        need(len(command_frame) == 1, 'Recorded command frame lost')
        item = {key: row[key] for key in ['name', 'turnHash', 'finalHash', 'commandFrame', 'modelMs', 'acceptMs',
                'commandMs', 'legalSearchMs', 'queueInspectionMs', 'totalSynchronousProbeMs',
                'maxIntervalMs', 'firstDispatchFromAcceptMs', 'firstCommandRenderMs', 'enqueueCost', 'commandSpans']}
        item.update(level=level, folder=folder, buildMs=row['enqueueCost']['buildMs'],
                    commandFrameTail=command_frame[0], worstIntervalFrame=worst,
                    commandAndWorstFrameNeighborhood=[f for f in trace
                        if abs(f['frame'] - row['commandFrame']) <= 2 or abs(f['frame'] - worst['frame']) <= 2])
        recorded.append(item)
    continuation_recorded = [r for r in recorded if r['level'] != 4]

    density_all = [r for rows in current_density.values() for r in rows]
    paired_extremes = paired_density_extremes(paired_density)
    extrema = {'ordinaryMaxCommandMs': max(r['commandMs'] for r in current_cascade['rows']),
               'ordinaryMaxIntervalMs': max(r['maxIntervalMs'] for r in current_cascade['rows']),
               'ordinaryMaxIntervalRow': cadence['maxRow'],
               'ordinary60FpsMaxIntervalMs': cadence['maxByTargetFps']['60']['maxIntervalMs'],
               'ordinary30FpsMaxIntervalMs': cadence['maxByTargetFps']['30']['maxIntervalMs'],
               'ordinaryNormalizedLateFrameCounts': cadence['lateFrameCountByTargetFps'],
               'ordinaryMaxFluidityP95Ms': max(r['p95Ms'] for r in fluid['phases']),
               'ordinaryMaxFluidityCommandMs': max(r['commandMs'] for r in fluid['phases']),
               'ordinaryMaxFluidityWorstIntervalMs': max(r['worstMs'] for r in fluid['phases']),
               'ordinaryFluidityWorstIntervalRow': {k: max(fluid['phases'], key=lambda r: r['worstMs'])[k]
                                                    for k in ['name', 'worstMs', 'p95Ms']},
               'ordinaryWorstDensityCapturedRenderMs': max(r['worstCapturedRenderMs'] for r in density_all),
               'sameProcessCurrentBuildMaxMs': max(r['currentMaxMs'] for r in command_rows),
               'sameProcessControl75BuildMaxMs': max(r['baselineMaxMs'] for r in command_rows),
               'recordedContinuationMaxCommandMs': max(r['commandMs'] for r in continuation_recorded),
               'recordedContinuationMaxBuildMs': max(r['buildMs'] for r in continuation_recorded),
               'recordedContinuationMaxIntervalMs': max(r['maxIntervalMs'] for r in continuation_recorded),
               'allRecordedMaxCommandMs': max(r['commandMs'] for r in recorded),
               'allRecordedMaxBuildMs': max(r['buildMs'] for r in recorded),
               'allRecordedMaxIntervalMs': max(r['maxIntervalMs'] for r in recorded),
               'pairedDensityWorstCapturedRenderMs': max(r['worstCapturedRenderMs'] for f in paired_density.values() for mode in ['detailed', 'coarse'] for r in f[mode]['rows']),
               'pairedCurrentWorstCapturedRenderMs': paired_extremes['current76']['worstRender']['frame']['cost']['renderMs'],
               'pairedCurrentWorstIntervalMs': paired_extremes['current76']['worstInterval']['frame']['intervalMs'],
               'pairedControl75TransformWorstCapturedRenderMs': paired_extremes['control75Transform']['worstRender']['frame']['cost']['renderMs'],
               'pairedControl75TransformWorstIntervalMs': paired_extremes['control75Transform']['worstInterval']['frame']['intervalMs']}
    remaining = [
        f"Ordinary six-case command elapsed maximum {extrema['ordinaryMaxCommandMs']:.3f}ms remains separate from pure paired construction spans. Its raw interval maximum {extrema['ordinaryMaxIntervalMs']:.3f}ms belongs to {cadence['maxRow']['name']} at target{cadence['maxRow']['targetFps']}fps (budget{cadence['maxRow']['targetIntervalMs']:.3f}ms, ratio{cadence['maxRow']['maxIntervalBudgetRatio']:.3f}); that maximum alone does not establish a stall.",
        f"The separate60fps fixture reaches {extrema['ordinary60FpsMaxIntervalMs']:.3f}ms and30fps fixtures reach {extrema['ordinary30FpsMaxIntervalMs']:.3f}ms. Counts over1.5x each requested interval are {cadence['lateFrameCountByTargetFps']}; all raw maxima and original100ms counts remain available. Requested15fps pacing must not be compared with a16.67ms60fps budget.",
        f"Ordinary Fluidity maximum p95 {extrema['ordinaryMaxFluidityP95Ms']:.3f}ms and density captured Render maximum {extrema['ordinaryWorstDensityCapturedRenderMs']:.3f}ms remain measured limits; no sustained60fps or whole-game hitch-free certification.",
        f"The separate eight-phase Fluidity run retains its command maximum {extrema['ordinaryMaxFluidityCommandMs']:.3f}ms and worst interval {extrema['ordinaryMaxFluidityWorstIntervalMs']:.3f}ms in {extrema['ordinaryFluidityWorstIntervalRow']['name']} (that phase p95{extrema['ordinaryFluidityWorstIntervalRow']['p95Ms']:.3f}ms); it is not interchangeable with the six-case Cascade timing run.",
        f"Paired live-effect controls retain a CURRENT76 Render maximum {extrema['pairedCurrentWorstCapturedRenderMs']:.3f}ms in {paired_extremes['current76']['worstRender']['name']} ({paired_extremes['current76']['worstRender']['mode']}) and interval maximum {extrema['pairedCurrentWorstIntervalMs']:.3f}ms. The CONTROL75-TRANSFORM branch retains its separate Render/interval maxima {extrema['pairedControl75TransformWorstCapturedRenderMs']:.3f}/{extrema['pairedControl75TransformWorstIntervalMs']:.3f}ms. These larger paired-run stalls remain open; ordinary density and recording maxima do not replace them. All other code remains current76, and extrema from different calls/modes do not isolate an exclusive cause.",
        f"Current paired pure Build reaches {extrema['sameProcessCurrentBuildMaxMs']:.3f}ms versus archived75 control maximum {extrema['sameProcessControl75BuildMaxMs']:.3f}ms. All signed per-fixture changes and slower pairs are retained; maxima from different calls do not establish exclusive causality.",
        f"Separate current recordings retain command/Build/interval maxima {extrema['allRecordedMaxCommandMs']:.3f}/{extrema['allRecordedMaxBuildMs']:.3f}/{extrema['allRecordedMaxIntervalMs']:.3f}ms across L4/L14/L31/L33. The three new continuation recordings alone retain {extrema['recordedContinuationMaxCommandMs']:.3f}/{extrema['recordedContinuationMaxBuildMs']:.3f}/{extrema['recordedContinuationMaxIntervalMs']:.3f}ms. These recording-overhead spans are not unrecorded timing results, pure Build samples or automatic visible-reaction approval.",
        'Per-draw instrumentation, development/debug code, GC/cache state and emulator/host scheduling remain measurement costs. Outside-span signature allocations can bias when a subsequent timed branch collects; all twelve primary pairs remain included, without censoring GC rows or claiming GC is the sole cause. Detailed/coarse density modes use separate processes and cannot isolate timer overhead.',
        'No first-use input-to-display, GPU-completion, allocation-saving, physical-device, full-campaign smoothness or fresh Match Villains parity claim. Conservative continuation fallbacks and rapid next-input decorative-landing transitions remain outside these CPU controls.'
    ]
    now = datetime.now(timezone.utc).isoformat()
    common = {'utc': now, 'apk_sha256': digest, 'source_sha256': source_sha,
              'artifactSHA256': dict(sorted(bindings.items())), 'externalEvidenceSHA256': dict(sorted(external.items())),
              'analyzerSHA256': sha(Path(__file__)), 'commandValidatorSHA256': sha(Path(__file__).with_name('run_smoothness_command_device.py')),
              'profilingValidatorSHA256': sha(Path(__file__).with_name('validate_gameplay74_profile.py'))}
    paired = dict(common, status='ANALYZED_SAME_APK_SMOOTHNESS76', baseline_checkpoint=75,
        commandConstruction={'fixtureCount': 8, 'pairCount': 96, 'validated': validation, 'rows': command_rows, 'scope': command['scope']},
        nativeMatchedControls={'constructionRows': native_command['timings'], 'effectTransformRows': native_effect['transformRows'],
            'scope': 'Native Editor primary all-pair/batch diagnostics, including slower fixtures and GC events. No samples are excluded. Separate from Android same-process controls; no allocation-saving or device-speedup inference.'},
        recordedDefaultL4=recorded[0],
        recordedContinuationControls={'rows': continuation_recorded,
            'maxCommand': max(continuation_recorded, key=lambda r: r['commandMs']),
            'maxBuild': max(continuation_recorded, key=lambda r: r['buildMs']),
            'maxInterval': max(continuation_recorded, key=lambda r: r['maxIntervalMs']),
            'scope': 'Three separately recorded current76 continuations, plus separately listed default L4. '
                     'Model+Accept includes real Enqueue/Next/dependency/prefetch and probe wrapper costs; '
                     'enqueue buildMs wraps Build plus queue.AddRange, unlike pure paired construction. '
                     'Intervals retain command-tail/phase ownership and recording/debug/OS overhead. '
                     'Nested spans are inclusive and must not be summed. Movie binding is not visual approval.'},
        pairedDensity=paired_density, pairedDensityExtremes=paired_extremes,
        ordinaryComparison75={'cascade': cascade_rows, 'fluidity': fluid_rows, 'density': ordinary_density},
        ordinaryCadence=cadence,
        observedPerformanceExtremes=extrema, remainingGates=remaining,
        scopes={'command': 'Same-process pure Build CPU; archived/current queues remain isolated from live gameplay.',
                'effects': 'Same-process alternating transform controls within each live density report; fresh banks/preparation per branch.',
                'ordinary': 'Separate archived75/final76 builds and processes, same seeded raw/final outcomes and diagnostic schema. Every sign is descriptive, not a causal speedup verdict.',
                'frames': 'No frame-by-frame pose alignment assumed between separately played controls; phase-tagged costs and per-row distributions retain their actual provenance.'})
    gates = dict(common, status='MEASURED_REMAINING_SMOOTHNESS76_GATES', observedPerformanceExtremes=extrema,
                 remainingGates=remaining, scope='Measured limits and unresolved acceptance gates, not an all-features performance pass.')
    return paired, gates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    paired, gates = build(args.out)
    for name, data in [('Paired_Performance.json', paired), ('Performance_Gates.json', gates)]:
        (args.out / name).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': paired['status'], 'apk_sha256': paired['apk_sha256'],
                      'commandPairs': 96, 'pairedDensityRows': 64, 'ordinaryDensityRows': 40,
                      'remainingGates': gates['remainingGates']}, indent=2))


if __name__ == '__main__':
    main()
