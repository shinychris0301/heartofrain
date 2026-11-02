"""Describe checkpoint78 execution controls without approving whole-game speed.

build() is read-only. The CLI writes Execution_Analysis.json only after every
required input validates; it never runs Unity, ADB, a collector or visual review.
"""
import argparse
import hashlib
import json
import math
import re
import runpy
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'Verification/Evidence/Gameplay78'
OUTER = ('outerSetupMs', 'outerSampleMs', 'outerBeginMs', 'outerDrawMs',
         'outerDisableMs', 'outerUploadMs', 'outerEndCollectionsMs',
         'outerBankEndMs', 'outerSelectionMs', 'outerWrapperResidualMs')
METRICS = ('updateMs', 'renderMs', 'outerSampleMs', 'bodySampleMs',
           'effectsSampleMs', 'sortMs', 'outerDrawMs', 'outerUploadMs')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def need(value, message):
    if not value:
        raise AssertionError(message)


def utc(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(parsed.tzinfo is not None, 'UTC lacks timezone')
    return parsed.astimezone(timezone.utc)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def stats(values):
    values = list(values)
    if not values:
        return {'samples': 0, 'median': None, 'p95': None, 'max': None}
    need(all(finite(v) for v in values), 'Nonfinite descriptive sample')
    ordered = sorted(values)
    return {'samples': len(values), 'median': statistics.median(values),
            'p95': ordered[math.ceil(len(ordered) * .95) - 1], 'max': max(values)}


def paired(values, left, right):
    """Signed differences include every pair, regardless of timing direction."""
    pairs = [{'index': p['index'], 'controlFirst': p['controlFirst'],
              'control77': left(p), 'current78': right(p),
              'currentMinusControl77': right(p) - left(p)} for p in values]
    return {'control77': stats(p['control77'] for p in pairs),
            'current78': stats(p['current78'] for p in pairs),
            'differenceOfMedians': statistics.median(p['current78'] for p in pairs) - statistics.median(p['control77'] for p in pairs),
            'signedPairDifferences': stats(p['currentMinusControl77'] for p in pairs),
            'currentSlowerPairs': sum(p['currentMinusControl77'] > 0 for p in pairs),
            'pairs': pairs}


def span_collections(span):
    return {str(gen): span[f'gc{gen}After'] - span[f'gc{gen}Before']
            if gen <= span['gcMax'] else None for gen in range(3)}


def cost_collections(value, before='BeforeUpdate', after='AfterUpdate'):
    return {str(gen): value[f'gc{gen}{after}'] - value[f'gc{gen}{before}']
            if gen <= value['gcMaxGeneration'] else None for gen in range(3)}


def collection_totals(values):
    values = list(values)
    return {str(gen): sum(v[str(gen)] for v in values if v[str(gen)] is not None)
            if any(v[str(gen)] is not None for v in values) else None for gen in range(3)}


def frame_summary(frames, target_fps=60):
    frames = list(frames)
    budget = 1000 / target_fps
    return {'frames': len(frames), 'requestedFps': target_fps,
            'intervalMs': stats(f['intervalMs'] for f in frames),
            'framesOver1_5TargetInterval': sum(f['intervalMs'] > budget * 1.5 for f in frames),
            'framesOver100Ms': sum(f['intervalMs'] > 100 for f in frames),
            'renderMs': stats(f['cost']['renderMs'] for f in frames),
            'updateMs': stats(f['cost']['updateMs'] for f in frames),
            'nestedSampleMetrics': {k: stats(f['cost'][k] for f in frames)
                                    for k in ('sampleMs', 'bodySampleMs', 'effectsSampleMs', 'sortMs')},
            'disjointOuterRenderSpans': {k: stats(f['cost'][k] for f in frames) for k in OUTER},
            'demandSpriteCreates': sum(f['cost']['spriteCreated'] for f in frames),
            'demandGeometryMisses': sum(f['cost']['geometryMisses'] for f in frames),
            'rendererCreates': sum(f['cost']['poolCreated'] for f in frames),
            'meshSlotCreates': sum(f['cost']['meshSlotsCreated'] for f in frames),
            'completedGCWithinUpdate': collection_totals(cost_collections(f['cost']) for f in frames),
            'completedGCWithinRender': collection_totals(cost_collections(f['cost'], 'BeforeRender', 'AfterRender') for f in frames)}


def frame_analysis(row, frames, target_fps=60, with_preparation=False):
    """Attribute Render by its wall brackets; intervals retain separate context."""
    frames = list(frames)
    before, after, overlapping = [], [], []
    for frame in frames:
        if frame['cost']['renderFinishedWall'] <= row['commandStartedWall']:
            before.append(frame)
        elif frame['cost']['renderStartedWall'] >= row['commandFinishedWall']:
            after.append(frame)
        else:
            overlapping.append(frame)
    need(len(before) + len(after) + len(overlapping) == len(frames), 'Render wall classification does not partition retained frames')
    batches = {}
    if with_preparation:
        for frame in frames:
            if frame['preparationBatches'] and frame['preparation']['frame'] == frame['frame']:
                batch = frame['preparation']
                key = (batch['frame'], batch['startedWall'], batch['finishedWall'])
                batches[key] = batch
    between = {}
    for gen in range(3):
        counts = [b['cost'][f'gc{gen}BeforeUpdate'] - a['cost'][f'gc{gen}AfterUpdate']
                  for a, b in zip(frames, frames[1:])
                  if min(a['cost']['gcMaxGeneration'], b['cost']['gcMaxGeneration']) >= gen]
        need(all(c >= 0 for c in counts), 'GC counters regress between Update brackets')
        between[str(gen)] = sum(counts) if counts else None

    def context(frame):
        if frame is None:
            return None
        at = frames.index(frame)
        previous = frames[at - 1] if at else None
        begin = previous['cost']['updateStartedWall'] if previous else None
        end = frame['cost']['updateStartedWall']

        def overlaps(start, finish):
            return None if begin is None else start < end and finish > begin

        cost = frame['cost']
        before_command = cost['updateFinishedWall'] <= row['commandStartedWall']
        return {'frame': frame, 'neighbors': frames[max(0, at - 2):at + 3],
                'previousUpdateStartedWall': begin, 'currentUpdateStartedWall': end,
                'updateStartBracketMs': None if begin is None else (end - begin) * 1000,
                'reportedIntervalMs': frame['intervalMs'],
                'commandOverlapsUpdateStartBracket': overlaps(row['commandStartedWall'], row['commandFinishedWall']),
                'preparationTelemetryAvailable': with_preparation,
                'preparationBatchesOverlappingUpdateStartBracket':
                    [b for b in batches.values() if overlaps(b['startedWall'], b['finishedWall'])]
                    if with_preparation and begin is not None else None,
                'costPredatesCommand': before_command,
                'costFollowsCommand': cost['updateStartedWall'] >= row['commandFinishedWall'],
                'afterUpdateToLateUpdateMs': (frame['absoluteWall'] - cost['updateFinishedWall']) * 1000,
                'isCommandFrameTail': frame['frame'] == row['commandFrame'] and before_command,
                'completedGCWithinUpdate': cost_collections(cost),
                'scope': 'Render and Update belong to the tagged current call. Previous/current recorded Update starts only bracket work preceding this frame; they are not exact engine deltaTime endpoints. The interval may include prior command/preparation, engine, observer or host scheduling. Missing preceding data or unavailable preparation telemetry is unknown, not a zero-overlap assertion.'}

    def worst(selected, metric):
        return context(max(selected, key=metric)) if selected else None

    result = {'allRetained': frame_summary(frames, target_fps),
              'preCommandRender': frame_summary(before, target_fps),
              'commandOverlappingRender': frame_summary(overlapping, target_fps),
              'postCommandRender': frame_summary(after, target_fps),
              'postCommandPlayback': frame_summary([f for f in after if f['cost']['kind'] != 'idle'], target_fps),
              'postCommandPowerFall': frame_summary([f for f in after if f['cost']['kind'] == 'powerFall'], target_fps),
              'betweenUpdateCompletedCollections': between,
              'commandFrameSamples': [f for f in frames if f['frame'] == row['commandFrame']],
              'worstRetainedRender': worst(frames, lambda f: f['cost']['renderMs']),
              'worstRetainedInterval': worst(frames, lambda f: f['intervalMs']),
              'worstPostCommandRender': worst(after, lambda f: f['cost']['renderMs']),
              'worstPostCommandInterval': worst(after, lambda f: f['intervalMs']),
              'renderAttributionScope': 'The three Render wall partitions are exhaustive. A post-command Render label never means its interval contains only post-command work. Nested sample costs are not added to disjoint outer Render spans.'}
    if with_preparation:
        result['preparationBatchesObserved'] = list(batches.values())
        result['postCommandPowerFallAfterObservedWorkerCompletion'] = frame_summary(
            [f for f in after if f['cost']['kind'] == 'powerFall' and f['preparationFrames'] > 0 and not f['preparationPending']], target_fps)
        result['workerScope'] = 'Recorded pending flags/counters belong to the bank worker at LateUpdate. Batch durations are cooperative spans, separate from Update/Render. This is not proof of universal residency or absence of later requests/eviction.'
    return result


def build(out=DEFAULT):
    out = Path(out).resolve()
    need(out.is_relative_to((ROOT / 'Verification/Evidence').resolve()), 'Analysis output is outside evidence')
    artifacts = {}
    external = {}

    def local_path(name):
        path = (out / name).resolve()
        need(path.is_relative_to(out) and path.is_file(), 'Missing/unsafe current proof: ' + name)
        artifacts[path.relative_to(out).as_posix()] = sha(path)
        return path

    def read(name):
        return json.loads(local_path(name).read_text('utf-8-sig'))

    def root_path(name):
        path = (ROOT / name).resolve()
        need(path.is_relative_to(ROOT) and path.is_file(), 'Missing/unsafe external proof: ' + name)
        external[path.relative_to(ROOT).as_posix()] = sha(path)
        return path

    source = read('Source_SHA256.json')
    artifact = read('APK_Artifact.json')
    need(re.fullmatch(r'[0-9a-f]{64}', artifact['sha256']) and artifact['bytes'] > 0, 'Invalid current APK identity')
    build_process = read('AndroidBuild_Process.json')
    build_report = read('Android_Build.json')
    build_source = read('Build_Source_SHA256.json')
    need(build_process['exitCode'] == 0 and not build_process['timedOut']
         and build_report['status'] == 'PASS_ANDROID_DEVELOPMENT_BUILD' and build_report['errors'] == 0
         and not build_report.get('error') and build_source['files'] == source['files'], 'Current development build/source binding failed')
    need(utc(build_process['startedUtc']) <= utc(build_report['utc']) <= utc(build_process['finishedUtc']), 'Development build chronology differs')
    baseline = read('Baseline77.json')
    sealed77 = read('Baseline77_Summary.json')
    read('Baseline77_Source_SHA256.json')
    need(baseline['status'] == 'PRESERVED_VERIFIED77_BASELINE' and baseline['source_inputs'] == 5125,
         'Wrong sealed baseline scope')
    need(artifacts['Baseline77_Summary.json'] == baseline['summary_sha256']
         and artifacts['Baseline77_Source_SHA256.json'] == baseline['source_sha256'], 'Copied baseline seals differ')
    need(sealed77['source_checkpoint'] == 77 and sealed77['apk_sha256'] == baseline['apk_sha256']
         and sealed77['source_sha256'] == baseline['source_sha256'], 'Baseline parent identity differs')

    def historical77(name):
        path = root_path('Verification/Evidence/Gameplay77/' + name)
        expected = baseline['summary_sha256'] if name == 'Summary.json' else baseline['source_sha256'] if name == 'Source_SHA256.json' else sealed77['evidence_sha256'].get(name)
        need(sha(path) == expected, 'Historical77 input is changed/unsealed: ' + name)
        return json.loads(path.read_text('utf-8-sig'))

    historical77('Summary.json')
    historical77('Source_SHA256.json')
    old_power = historical77('PowerFall/Report.json')
    need(old_power['status'] == 'PASS_NATIVE_POWER_FALL77' and len(old_power['frozenRows']) == 4, 'Wrong sealed Android77 power-fall baseline')
    baseline_hashes = {(r['family'], r['count']): (r['turnHash'], r['finalHash']) for r in old_power['frozenRows']}
    runner_path = root_path('Verification/Tools/run_execution78_device.py')
    runner = runpy.run_path(str(runner_path), run_name='execution78_contract_only')
    report = read('Execution/Report.json')
    installed = read('Execution/Installation.json')
    runtime = local_path('Execution/Runtime.log').read_text('utf-8', errors='replace')
    need(not re.search(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException', runtime), 'Execution runtime log contains native errors')
    validated = runner['validate_report'](report, baseline_hashes)
    need(installed['status'] == 'PASS_EXECUTION78_DEVICE_AUDIT' and installed['serial'] == 'emulator-5556'
         and installed['runtime_errors'] == 0 and not installed.get('error'), 'Execution transport/runtime failed')
    need(installed['apk_sha256'] == installed['installed_apk_sha256'] == artifact['sha256']
         and installed['baseline_android77_report_sha256'] == external['Verification/Evidence/Gameplay77/PowerFall/Report.json'], 'Execution APK/baseline binding differs')
    need(installed['data_unchanged'] and installed['before'] == installed['after'] and installed['validated'] == validated, 'Execution raw audit changed or real data mutated')
    need(utc(build_process['finishedUtc']) <= utc(installed['utc']) <= utc(report['utc']) <= utc(installed['finishedUtc']), 'Execution build/process/report chronology differs')

    model = []
    for row in report['modelRows']:
        timings = paired(row['pairs'], lambda p: p['control']['milliseconds'], lambda p: p['current']['milliseconds'])
        branches = {}
        for branch in ('control', 'current'):
            maximum = max(row['pairs'], key=lambda p: p[branch]['milliseconds'])
            branches[branch] = {'completedGCWithinTimedCall': collection_totals(span_collections(p[branch]) for p in row['pairs']),
                                'maximumCallPair': maximum,
                                'maximumCallNeighbors': row['pairs'][max(0, maximum['index'] - 1):maximum['index'] + 2]}
        model.append({'name': row['name'], 'timingMs': timings, 'rawPairs': row['pairs'],
                      'control77InclusiveStageDiagnostics': row['controlStages'],
                      'current78InclusiveStageDiagnostics': row['currentStages'],
                      'outliersAndCompletedCollections': branches,
                      'scope': 'Eight primary paired Solve calls, constructor/fixture setup outside timing. Stage diagnostics are separately instrumented runs with inclusive/overlapping scopes; their children must not be summed as a command total. Both prepared branch objects coexist in the development process; release peak heap is not measured.'})

    resources = []
    for row in report['resourceRows']:
        initial = paired(row['pairs'], lambda p: p['controlInitial']['milliseconds'], lambda p: p['currentInitial']['milliseconds'])
        traversal = paired(row['pairs'], lambda p: p['controlTraversal']['milliseconds'], lambda p: p['currentTraversal']['milliseconds'])
        total = paired(row['pairs'], lambda p: p['controlInitial']['milliseconds'] + p['controlTraversal']['milliseconds'],
                       lambda p: p['currentInitial']['milliseconds'] + p['currentTraversal']['milliseconds'])
        maximums = {branch: max(row['pairs'], key=lambda p: p[branch + 'Initial']['milliseconds'] + p[branch + 'Traversal']['milliseconds'])
                    for branch in ('control', 'current')}
        resources.append({'name': row['name'], 'phases': row['pairs'][0]['phases'],
                          'initialMs': initial, 'remainingPhaseTraversalMs': traversal,
                          'initialPlusTraversalMs': total, 'rawPairs': row['pairs'],
                          'maximumTotalWorkPairs': maximums,
                          'completedGCWithinTimedCalls': {branch: collection_totals(span_collections(p[branch + stage]) for p in row['pairs'] for stage in ('Initial', 'Traversal')) for branch in ('control', 'current')},
                          'scope': 'Initial includes first-phase dependencies plus whole-queue dependencies, and current eager plan construction plus real identity guards. Traversal is only later phase entries (1..N), not the full workload; Initial+Traversal is the complete dependency workload. Context setup, hashes, readiness, texture loads, callbacks and live coroutine waits are excluded. No phase-residency result is cached.'})

    natural = []
    for row in report['naturalRows']:
        frames = report['frames'][row['frameStart']:row['frameStart'] + row['frameCount']]
        natural.append({'name': row['name'], 'fixture': row['fixture'], 'repeat': row['repeat'],
                        'checkpoint77CombinedControl': row['checkpoint77'], 'rawRow': row,
                        **frame_analysis(row, frames, with_preparation=True)})
    natural_pairs = []
    for left, right in zip(natural[::2], natural[1::2]):
        control, current = (left, right) if left['checkpoint77CombinedControl'] else (right, left)
        need((control['fixture'], control['repeat']) == (current['fixture'], current['repeat']), 'Natural pair identity differs')
        differences = {k: current['rawRow'][k] - control['rawRow'][k] for k in ('modelMs', 'acceptMs', 'commandMs', 'settleSeconds')}
        scoped = {}
        for scope in ('allRetained', 'preCommandRender', 'commandOverlappingRender', 'postCommandRender', 'postCommandPlayback', 'postCommandPowerFall'):
            scoped[scope] = {key: {stat: current[scope][key][stat] - control[scope][key][stat]
                                  if current[scope][key][stat] is not None and control[scope][key][stat] is not None else None
                                  for stat in ('median', 'p95', 'max')}
                             for key in ('renderMs', 'updateMs', 'intervalMs')}
        def first_post_command(data):
            raw = data['rawRow']
            selected = report['frames'][raw['frameStart']:raw['frameStart'] + raw['frameCount']]
            at = next(i for i, f in enumerate(selected) if f['cost']['renderStartedWall'] >= raw['commandFinishedWall'])
            frame = selected[at]
            previous = selected[at - 1] if at else None
            return {'frame': frame, 'synchronousTextureLoadDeltaFromPreviousSample':
                    frame['synchronousLoads'] - previous['synchronousLoads'] if previous else None,
                    'cumulativeSpriteCreateDeltaFromPreviousSample':
                    frame['spriteCreates'] - previous['spriteCreates'] if previous else None}

        first_control, first_current = first_post_command(control), first_post_command(current)
        natural_pairs.append({'fixture': control['fixture'], 'repeat': control['repeat'],
                              'control77': control['name'], 'current78': current['name'],
                              'currentMinusControl77Command': differences,
                              'currentMinusControl77FrameSummary': scoped,
                              'firstPostCommandRender': {'control77': first_control, 'current78': first_current,
                                  'currentMinusControl77RenderMs': first_current['frame']['cost']['renderMs'] - first_control['frame']['cost']['renderMs']},
                              'scope': 'Combined same-APK model/resource/submission controls on separate fresh banks after two untimed warmups. These are natural playback distributions, not CPU measurements of identical frame poses or the entire old APK. Injected starting powers are installed after loading the base level; first-use gating remains part of this synthetic command fixture.'})

    frozen = []
    for row in report['frozenRows']:
        metrics = {metric: paired(row['pairs'], lambda p, k=metric: p['controlCost'][k], lambda p, k=metric: p['currentCost'][k]) for metric in METRICS}
        metrics['timedCallMs'] = paired(row['pairs'], lambda p: p['control']['milliseconds'], lambda p: p['current']['milliseconds'])
        collections = {branch: {'withinTimedCall': collection_totals(span_collections(p[branch]) for p in row['pairs']),
                                'withinUpdate': collection_totals(cost_collections(p[branch + 'Cost']) for p in row['pairs']),
                                'withinRender': collection_totals(cost_collections(p[branch + 'Cost'], 'BeforeRender', 'AfterRender') for p in row['pairs'])}
                       for branch in ('control', 'current')}
        frozen.append({'name': row['name'], 'family': row['family'], 'count': row['count'],
                       'age': row['age'], 'metricsMs': metrics, 'rawRow': row,
                       'completedCollections': collections,
                       'maximumRenderPairs': {branch: max(row['pairs'], key=lambda p: p[branch + 'Cost']['renderMs']) for branch in ('control', 'current')},
                       'scope': 'Eight warmed same-bank, fixed-clock pairs of actual GameplayScreen Update/Render calls. Only effect submission selects exact77 control versus78. Sampling and bank are common. Exact draw/upload/binding/transform hashes are captured outside timing. No demand Sprite/geometry/renderer/slot creation is permitted in these calls. Calls do not measure GPU completion or natural frame intervals.'})

    # The unchanged77 probe is rerun on the current APK, so its coarse maxima
    # remain mandatory alongside the new78 execution controls. Its natural
    # branches vary preparation; its frozen branches vary76/77 sampling.
    power_runner_path = root_path('Verification/Tools/run_power_fall77_device.py')
    power_runner = runpy.run_path(str(power_runner_path), run_name='current78_power_fall_contract_only')
    power_report = read('PowerFall/Report.json')
    power_audit = read('PowerFall/Installation.json')
    power_log = local_path('PowerFall/Runtime.log').read_text('utf-8', errors='replace')
    need(not re.search(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException', power_log), 'Current PowerFall runtime log contains native errors')
    power_validated = power_runner['validate_report'](power_report, baseline_hashes)
    need(power_audit['status'] == 'PASS_POWER_FALL77_DEVICE_AUDIT' and power_audit['serial'] == 'emulator-5556'
         and power_audit['runtime_errors'] == 0 and not power_audit.get('error')
         and power_audit['apk_sha256'] == power_audit['installed_apk_sha256'] == artifact['sha256'], 'Current PowerFall audit/APK identity failed')
    need(power_audit['data_unchanged'] and power_audit['before'] == power_audit['after'] == installed['before']
         and power_audit['validated'] == power_validated, 'Current PowerFall changed real data or raw audit summary differs')
    need(utc(build_process['finishedUtc']) <= utc(power_audit['utc']) <= utc(power_report['utc']) <= utc(power_audit['finishedUtc']), 'Current PowerFall build/process/report chronology differs')
    power_natural = []
    power_by_branch = {'prepared': [], 'skipped': []}
    power_post_by_branch = {'prepared': [], 'skipped': []}
    power_batches = []
    for row in power_report['naturalRows']:
        frames = power_report['frames'][row['frameStart']:row['frameStart'] + row['frameCount']]
        analysis = frame_analysis(row, frames, with_preparation=True)
        branch = 'skipped' if row['skipTurnPreparation'] else 'prepared'
        post = [f for f in frames if f['cost']['renderStartedWall'] >= row['commandFinishedWall']]
        late = [f for f in post if f['cost']['kind'] == 'powerFall' and 2.44 <= f['cost']['age'] <= 2.62]
        completed = [f for f in post if f['cost']['kind'] == 'powerFall' and f['preparationFrames'] > 0 and not f['preparationPending']]
        power_by_branch[branch].extend(frames)
        power_post_by_branch[branch].extend(post)
        power_batches.extend(analysis['preparationBatchesObserved'])
        power_natural.append({'name': row['name'], 'family': row['family'], 'count': row['count'],
                              'repeat': row['repeat'], 'branch': branch, 'rawRow': row,
                              **analysis, 'latePowerFall2440To2620ms': frame_summary(late),
                              'powerFallAfterObservedWorkerCompletion': frame_summary(completed),
                              'lateWindowSamples': [{'frame': f['frame'], 'age': f['cost']['age'],
                                  'spriteCreated': f['cost']['spriteCreated'], 'geometryMisses': f['cost']['geometryMisses'],
                                  'preparationPending': f['preparationPending']} for f in late]})
    power_frozen = []
    for row in power_report['frozenRows']:
        # These older fields spell the new-sampler branch "refined". Do not
        # confuse it with the78 submission branch "current" above.
        pair_rows = []
        for pair in row['pairs']:
            pair_rows.append({'index': pair['index'], 'controlFirst': pair['controlFirst'],
                              'samplerControl76RenderMs': pair['controlCost']['renderMs'],
                              'samplerCurrent77RenderMs': pair['refinedCost']['renderMs'],
                              'currentSamplerMinusControlRenderMs': pair['refinedCost']['renderMs'] - pair['controlCost']['renderMs'],
                              'samplerControl76UpdateMs': pair['controlCost']['updateMs'],
                              'samplerCurrent77UpdateMs': pair['refinedCost']['updateMs'],
                              'controlCompletedGCWithinUpdate': cost_collections(pair['controlCost']),
                              'currentCompletedGCWithinUpdate': cost_collections(pair['refinedCost'])})
        power_frozen.append({'name': row['name'], 'age': row['age'], 'pairs': pair_rows,
                             'samplerControl76RenderMs': stats(p['samplerControl76RenderMs'] for p in pair_rows),
                             'samplerCurrent77RenderMs': stats(p['samplerCurrent77RenderMs'] for p in pair_rows),
                             'signedRenderDifferencesMs': stats(p['currentSamplerMinusControlRenderMs'] for p in pair_rows),
                             'currentSamplerSlowerPairs': sum(p['currentSamplerMinusControlRenderMs'] > 0 for p in pair_rows)})
    power_extremes = {}
    for branch in ('prepared', 'skipped'):
        all_frames, post = power_by_branch[branch], power_post_by_branch[branch]
        power_extremes[branch + 'AllRetainedMaxRenderMs'] = max(f['cost']['renderMs'] for f in all_frames)
        power_extremes[branch + 'AllRetainedMaxIntervalMs'] = max(f['intervalMs'] for f in all_frames)
        power_extremes[branch + 'PostCommandMaxRenderMs'] = max(f['cost']['renderMs'] for f in post)
        power_extremes[branch + 'PostCommandMaxIntervalMs'] = max(f['intervalMs'] for f in post)
    power_extremes['maximumObservedWorkerBatchMs'] = max((b['milliseconds'] for b in power_batches), default=None)
    power_totals = {branch: {
        'naturalRows': sum(row['branch'] == branch for row in power_natural),
        'allRetained': frame_summary(power_by_branch[branch]),
        'postCommandRender': frame_summary(power_post_by_branch[branch]),
        'lateWindowFrames': sum(row['latePowerFall2440To2620ms']['frames'] for row in power_natural if row['branch'] == branch),
        'lateWindowDemandSpriteCreates': sum(row['latePowerFall2440To2620ms']['demandSpriteCreates'] for row in power_natural if row['branch'] == branch),
        'lateWindowDemandGeometryMisses': sum(row['latePowerFall2440To2620ms']['demandGeometryMisses'] for row in power_natural if row['branch'] == branch),
        'afterObservedWorkerCompletionFrames': sum(row['powerFallAfterObservedWorkerCompletion']['frames'] for row in power_natural if row['branch'] == branch),
        'afterObservedWorkerCompletionDemandSpriteCreates': sum(row['powerFallAfterObservedWorkerCompletion']['demandSpriteCreates'] for row in power_natural if row['branch'] == branch),
        'afterObservedWorkerCompletionDemandGeometryMisses': sum(row['powerFallAfterObservedWorkerCompletion']['demandGeometryMisses'] for row in power_natural if row['branch'] == branch)}
        for branch in ('prepared', 'skipped')}
    power_rerun = {'validated': power_validated, 'naturalRows': power_natural,
                   'preparedAndSkipped': power_totals, 'performanceExtremes': power_extremes,
                   'frozenSamplerPairs': power_frozen,
                   'scope': f"The existing77 PowerFall probe rerun on this final78 APK:16 natural preparation-on/off turns,{len(power_report['frames'])} recorded frames and16 warmed fixed-pose sampler76/77 pairs. Counts are revalidated from actual raw data. These sampler controls are distinct from the32 new78 effect-submission pairs; both run inside the current APK and neither restores the whole old application. Missing demand in a targeted prepared window is not a universal cache/first-use guarantee."}

    native = {}
    expected_native = {'ModelWork78': 'PASS_NATIVE_MODEL_WORK78',
                       'DenseSubmission': 'PASS_NATIVE_DENSE_SUBMISSION78',
                       'CommandPreparation78': 'PASS_NATIVE_COMMAND_PREPARATION78'}
    for name, status in expected_native.items():
        proof = read('Native/' + name + '.json')
        process = read('Native/' + name + '_Process.json')
        manifest_name = process['sourceManifest'].replace('\\', '/')
        manifest = read(manifest_name)
        need(proof['status'] == status and not any(proof.get(k) for k in ('errors', 'error', 'failed', 'failures')),
             'New native suite failed: ' + name)
        need(process['exitCode'] == 0 and not process['timedOut']
             and artifacts[manifest_name] == process['sourceSHA256'] and manifest['files'] == source['files'],
             'Native suite was not compiled from final frozen source: ' + name)
        need(utc(process['startedUtc']) <= utc(proof['utc']) <= utc(process['finishedUtc']), 'Native process/report chronology differs: ' + name)
        native[name] = proof
    native_descriptive = {
        'model': {'scope': native['ModelWork78']['scope'], 'checks': native['ModelWork78']['checks'],
                  'modelCases': native['ModelWork78']['modelCases'], 'timings': native['ModelWork78']['timings'],
                  'rawParity': native['ModelWork78']['rawParity'], 'finalParity': native['ModelWork78']['finalParity'],
                  'checkpointParity': native['ModelWork78']['checkpointParity'], 'dictionaryParity': native['ModelWork78']['dictionaryParity']},
        'submission': {k: native['DenseSubmission'][k] for k in ('scope', 'memoryScope', 'checks', 'fixtures', 'parityFrames', 'pixelRows', 'timings')},
        'resourcePreparation': {k: native['CommandPreparation78'][k] for k in ('scope', 'checks', 'authoredTurns', 'queues', 'phaseComparisons', 'compositePhases', 'continuedMotions', 'pathSetParity', 'pathOrderParity', 'evictionReadinessPreserved', 'ownerReloadPreserved', 'benchmarks')},
        'scope': 'Three separate pinned Unity Editor suites, same native domain and exact compiled controls. Their clocks/driver/runtime differ from Android. All timing rows and slower blocks remain, including initial eager-planning regressions. Native resource block values are means of16 calls per alternating block, not128 independent primary frame samples. These scopes do not measure the entire old APK, device touch latency, heap churn or physical hardware.'}

    profile_path = root_path('Verification/Tools/validate_gameplay74_profile.py')
    profile = runpy.run_path(str(profile_path), run_name='corrected_profile_contract_only')
    root_path('Verification/Tools/run_cascade_timing_device.py')

    def bind_stage(stage, installation_name, raw):
        audit = read('Android/' + stage + '_Data_Audit.json')
        install = read(installation_name)
        need(install['serial'] == 'emulator-5556' and install.get('apk_sha256', install.get('sha256')) == artifact['sha256'], 'Ordinary stage APK/device identity differs: ' + stage)
        if 'installed_apk_sha256' in install:
            need(install['installed_apk_sha256'] == artifact['sha256'], 'Installed ordinary-stage APK differs: ' + stage)
        need(audit['exit_code'] == 0 and audit['apk_sha256'] == artifact['sha256'] and audit['data_unchanged']
             and audit['before'] == audit['after'] == installed['before'], 'Ordinary stage changed real data: ' + stage)
        need(utc(raw['utc']) >= utc(install['utc']), 'Ordinary stage report predates launch: ' + stage)

    fluidity = read('Android/Fluidity/Measurement.json')
    bind_stage('Fluidity', 'Android/Fluidity/Installation.json', fluidity)
    need(fluidity['status'] == 'RECORDED_NATIVE_FLUIDITY' and not fluidity['errors']
         and fluidity['isolatedProfile'] and fluidity['launchCleared'] and len(fluidity['phases']) == 8, 'Ordinary Fluidity scope failed')
    fluidity_rows = []
    for index, row in enumerate(fluidity['phases']):
        samples = [f for f in fluidity['frameSamples'] if f['phase'] == index]
        need(samples and all(finite(f[k]) and f[k] >= 0 for f in samples for k in ('intervalMs', 'renderMs', 'updateMs', 'sampleMs')), 'Invalid ordinary Fluidity samples')
        fluidity_rows.append({'rawRow': row, 'capturedCosts': len(samples),
                              'renderMs': stats(f['renderMs'] for f in samples), 'updateMs': stats(f['updateMs'] for f in samples),
                              'worstCapturedRender': max(samples, key=lambda f: f['renderMs']),
                              'worstCapturedInterval': max(samples, key=lambda f: f['intervalMs'])})
    cascade = read('Android/Cascade/measure/Report.json')
    bind_stage('Cascade', 'Android/Cascade/measure/Installation.json', cascade)
    old_cascade = historical77('Android/Cascade/measure/Report.json')
    cascade_hashes = {r['baseCase']: (r['turnHash'], r['finalHash']) for r in old_cascade['rows']}
    cascade_validated = profile['validate'](cascade, 'measure', cascade_hashes)
    need(len(cascade['rows']) == 6 and not cascade['modelWorkEnabled'] and not cascade['checkpoint74Continuation'], 'Wrong ordinary Cascade control mode')
    cascade_rows = []
    for index, row in enumerate(cascade['rows']):
        frames = [f for f in cascade['frameSamples'] if f['row'] == index]
        for frame in frames:
            runner['validate_cost'](frame['cost'])
        timed = [f for f in frames if f['timingWindow']]
        budget = 1000 / row['targetFps']
        cascade_rows.append({'rawRow': row, **frame_analysis(row, frames, row['targetFps']),
                             'timingWindow': frame_summary(timed, row['targetFps']),
                             'maximumIntervalToRequestedCadenceRatio': max(f['intervalMs'] for f in timed) / budget})
    density = []
    for family in ('crate', 'stone', 'gate', 'tiles'):
        raw = read('Android/Density/candidate_review-' + family + '/Report.json')
        bind_stage('Density_' + family, 'Android/Density/candidate_review-' + family + '/Installation.json', raw)
        old = historical77('Android/Density/candidate_review-' + family + '/Report.json')
        hashes = {}
        for row in old['rows']:
            key = (family, row['crates'])
            outcome = (row['turnHash'], row['finalHash'])
            need(hashes.setdefault(key, outcome) == outcome, 'Sealed density deterministic outcomes disagree')
        old_hashes = {r['name']: (r['turnHash'], r['finalHash']) for r in old['rows']}
        # The existing corrected-profile helper expects every named repeat;
        # repeated density counts above are also checked for determinism.
        validated_density = profile['validate_density'](raw, family, old_hashes)
        rows = []
        for index, row in enumerate(raw['rows']):
            frames = [f for f in raw['frames'] if f['phase'] == index]
            for frame in frames:
                runner['validate_cost'](frame['cost'])
            rows.append({'rawRow': row, **frame_analysis(row, frames)})
        density.append({'family': family, 'detailedDrawCosts': raw['detailedDrawCosts'],
                        'validated': validated_density, 'rows': rows})
    ordinary = {'fluidity': {'rows': fluidity_rows, 'scope': fluidity['scope'],
                             'limitation': 'This legacy probe retains frame IDs and costs but lacks absolute Update wall brackets. Its command-frame/interval costs are not re-labelled by causal command ownership here.'},
                'cascade': {'validated': cascade_validated, 'rows': cascade_rows},
                'density': density,
                'scope': 'Separate current-APK ordinary probes, not matched same-bank CPU experiments. Fluidity has8 phases, Cascade6 requested-cadence cases and density40 turns. Their observer modes differ; detailed per-draw density timings cannot be equated with coarse Execution controls. Normal15fps cadence is about66.67ms, not intrinsically a stall. No older-APK performance speedup is inferred from different launches.'}

    recorded = []
    for level, folder in ((4, 'Android/Cascade/visual'),
                          (14, 'ContinuationVisual/L14/visual'),
                          (31, 'ContinuationVisual/L31/visual'),
                          (33, 'ContinuationVisual/L33/visual')):
        raw = read(folder + '/Report.json')
        install = read(folder + '/Installation.json')
        movie = local_path(folder + '/HR_NaturalCascade.mp4')
        need(profile['RUNNER']['validate_report'](raw, 'visual', 1, require_profiling=True), 'Current recorded visual timing provenance failed')
        need(raw['visualLevel'] == install['visual_level'] == level and raw['variant'] == install['variant'] == 'visual'
             and not raw['checkpoint74Continuation'] and not install['checkpoint74_continuation']
             and not raw['modelWorkEnabled'] and not install['profile_model_work'], 'Recorded visual fixture/control mode differs')
        need(install['serial'] == 'emulator-5556' and install['apk_sha256'] == install['installed_apk_sha256'] == artifact['sha256']
             and install['data_unchanged'] and install['before'] == install['after'] == installed['before'], 'Recorded visual APK/save binding differs')
        need(utc(build_process['finishedUtc']) <= utc(install['utc']) <= utc(raw['utc']), 'Recorded visual report predates current build/launch')
        old = historical77(folder + '/Report.json')
        old_row, row = old['rows'][0], raw['rows'][0]
        need(row['baseCase'] == f'L{level}_0_30' == old_row['baseCase']
             and (row['turnHash'], row['finalHash']) == (old_row['turnHash'], old_row['finalHash']), 'Recorded same-platform model outcome differs from sealed77')
        schedule = lambda value: [(p['kind'], p['label'], p['duration'], p['lastContact']) for p in value['phases']]
        need(schedule(row) == schedule(old_row) and row['queuedSteps'] == old_row['queuedSteps']
             and abs(row['scheduledSeconds'] - old_row['scheduledSeconds']) < .000001, 'Recorded ideal schedule differs from sealed77')
        frames = raw['frameSamples']
        for frame in frames:
            runner['validate_cost'](frame['cost'])
        timed = [f for f in frames if f['timingWindow']]
        recorded.append({'level': level, 'sourceFolder': folder,
                         'movie': movie.relative_to(out).as_posix(), 'rawRow': row,
                         'sealedAndroid77ModelAndScheduleParity': True,
                         **frame_analysis(row, frames, row['targetFps']),
                         'timingWindow': frame_summary(timed, row['targetFps']),
                         'scope': 'Current source/APK recorded instrumented playback. The movie is hash-bound, not visually approved by this analyzer. Model outputs and ideal phase durations/contacts match sealed77 within the same Android domain. Recording, observer, command and engine/host work can coexist; these spans are not directly comparable to unrecorded medians and do not establish an exclusive capture/host cause.'})
    recorded_section = {'rows': recorded,
                        'maxCommand': max(recorded, key=lambda r: r['rawRow']['commandMs']),
                        'maxInterval': max(recorded, key=lambda r: r['timingWindow']['intervalMs']['max']),
                        'scope': 'All four fresh source78 recordings are retained separately from unrecorded controls. They provide timestamped frame/command neighborhoods; actual image inspection and original-PTS endpoint review are separate required evidence.'}

    first_idle_pairs = [{'fixture': p['fixture'], 'repeat': p['repeat'], **p['firstPostCommandRender']} for p in natural_pairs]
    l4_row = next(r for r in report['modelRows'] if r['name'] == 'L4_match')
    l4_timing = next(r for r in model if r['name'] == 'L4_match')['timingMs']
    no_completed_gc = [p for p in l4_row['pairs']
                       if not any(n for branch in ('control', 'current') for n in span_collections(p[branch]).values() if n is not None)]
    l4_without = paired(no_completed_gc, lambda p: p['control']['milliseconds'], lambda p: p['current']['milliseconds']) if no_completed_gc else None
    residuals = {'firstPostCommandIdle': {'pairs': first_idle_pairs,
                    'currentHigherRenderPairs': sum(p['currentMinusControl77RenderMs'] > 0 for p in first_idle_pairs),
                    'scope': 'The first post-command calls are idle while the injected starting powers become presentable. Both branches expose two new synchronous textures and two Sprite creations in this fixture. These counter/timing coincidences do not isolate the cause or prove a production input regression.'},
                 'L4PrimaryModel': {'timingMs': l4_timing,
                    'medianCurrentMinusControlPercent': 100 * (l4_timing['current78']['median'] / l4_timing['control77']['median'] - 1),
                    'pairsWithoutCompletedGCInEitherSpan': l4_without,
                    'scope': 'The slower primary L4 model median remains visible, including the subset with no completed collection in either call. Collection counters do not measure all GC slices and do not justify dismissing the regression as GC; more repetitions/production traces would be required for cause or stability.'}}

    control_frames = [f for row in report['naturalRows'] if row['checkpoint77']
                      for f in report['frames'][row['frameStart']:row['frameStart'] + row['frameCount']]]
    current_frames = [f for row in report['naturalRows'] if not row['checkpoint77']
                      for f in report['frames'][row['frameStart']:row['frameStart'] + row['frameCount']]]
    control_post = [f for row in report['naturalRows'] if row['checkpoint77']
                    for f in report['frames'][row['frameStart']:row['frameStart'] + row['frameCount']]
                    if f['cost']['renderStartedWall'] >= row['commandFinishedWall']]
    current_post = [f for row in report['naturalRows'] if not row['checkpoint77']
                    for f in report['frames'][row['frameStart']:row['frameStart'] + row['frameCount']]
                    if f['cost']['renderStartedWall'] >= row['commandFinishedWall']]
    density_worst = [r['worstRetainedRender'] for family in density for r in family['rows']]
    worker_batches = [b for row in natural for b in row['preparationBatchesObserved']]
    extremes = {
        'naturalControl77AllRetainedMaxRenderMs': max(f['cost']['renderMs'] for f in control_frames),
        'naturalCurrent78AllRetainedMaxRenderMs': max(f['cost']['renderMs'] for f in current_frames),
        'naturalControl77AllRetainedMaxIntervalMs': max(f['intervalMs'] for f in control_frames),
        'naturalCurrent78AllRetainedMaxIntervalMs': max(f['intervalMs'] for f in current_frames),
        'naturalControl77PostCommandMaxRenderMs': max(f['cost']['renderMs'] for f in control_post),
        'naturalCurrent78PostCommandMaxRenderMs': max(f['cost']['renderMs'] for f in current_post),
        'naturalControl77PostCommandMaxIntervalMs': max(f['intervalMs'] for f in control_post),
        'naturalCurrent78PostCommandMaxIntervalMs': max(f['intervalMs'] for f in current_post),
        'naturalControl77MaxCommandMs': max(r['commandMs'] for r in report['naturalRows'] if r['checkpoint77']),
        'naturalCurrent78MaxCommandMs': max(r['commandMs'] for r in report['naturalRows'] if not r['checkpoint77']),
        'observedWorkerMaxBatchMs': max((b['milliseconds'] for b in worker_batches), default=None),
        'pureModelCurrent78MaxCallMs': max(p['current']['milliseconds'] for r in report['modelRows'] for p in r['pairs']),
        'resourceCurrent78MaxInitialMs': max(p['currentInitial']['milliseconds'] for r in report['resourceRows'] for p in r['pairs']),
        'resourceCurrent78MaxInitialPlusTraversalMs': max(p['currentInitial']['milliseconds'] + p['currentTraversal']['milliseconds'] for r in report['resourceRows'] for p in r['pairs']),
        'frozenControl77MaxRenderMs': max(p['controlCost']['renderMs'] for r in report['frozenRows'] for p in r['pairs']),
        'frozenCurrent78MaxRenderMs': max(p['currentCost']['renderMs'] for r in report['frozenRows'] for p in r['pairs']),
        'ordinaryFluidityMaxCommandMs': max(r['commandMs'] for r in fluidity['phases']),
        'ordinaryFluidityMaxIntervalMs': max(r['worstMs'] for r in fluidity['phases']),
        'ordinaryCascadeMaxCommandMs': max(r['commandMs'] for r in cascade['rows']),
        'ordinaryCascadeMaxIntervalMs': max(r['maxIntervalMs'] for r in cascade['rows']),
        'ordinaryDensityMaxRenderMs': max(r['frame']['cost']['renderMs'] for r in density_worst),
        'ordinaryDensityMaxIntervalMs': max(r['worstRetainedInterval']['frame']['intervalMs'] for family in density for r in family['rows']),
        'powerFallCurrentPreparedAllRetainedMaxRenderMs': power_extremes['preparedAllRetainedMaxRenderMs'],
        'powerFallCurrentPreparedAllRetainedMaxIntervalMs': power_extremes['preparedAllRetainedMaxIntervalMs'],
        'powerFallCurrentSkippedAllRetainedMaxRenderMs': power_extremes['skippedAllRetainedMaxRenderMs'],
        'powerFallCurrentSkippedAllRetainedMaxIntervalMs': power_extremes['skippedAllRetainedMaxIntervalMs'],
        'powerFallCurrentMaximumObservedWorkerBatchMs': power_extremes['maximumObservedWorkerBatchMs'],
        'recordedVisualMaxCommandMs': max(r['rawRow']['commandMs'] for r in recorded),
        'recordedVisualMaxAcceptMs': max(r['rawRow']['acceptMs'] for r in recorded),
        'recordedVisualMaxIntervalMs': max(r['timingWindow']['intervalMs']['max'] for r in recorded)}
    remaining = [
        f"Current78 natural turns still reach {extremes['naturalCurrent78MaxCommandMs']:.3f}ms synchronous command spans; all retained Render/interval maxima are {extremes['naturalCurrent78AllRetainedMaxRenderMs']:.3f}/{extremes['naturalCurrent78AllRetainedMaxIntervalMs']:.3f}ms. Post-command Render maxima are {extremes['naturalCurrent78PostCommandMaxRenderMs']:.3f}ms; their reported intervals still reach {extremes['naturalCurrent78PostCommandMaxIntervalMs']:.3f}ms and can include preceding command/worker/engine/host work. Raw wall brackets and neighborhoods remain visible.",
        f"Frozen same-pose current78 Render reaches {extremes['frozenCurrent78MaxRenderMs']:.3f}ms versus control77 {extremes['frozenControl77MaxRenderMs']:.3f}ms; all signed/slower pairs are retained. These are fixed-pose submission controls with no demand creation, not natural frame pacing or proof that one stage exclusively caused historical stalls.",
        f"Separate ordinary probes retain Fluidity command/interval maxima {extremes['ordinaryFluidityMaxCommandMs']:.3f}/{extremes['ordinaryFluidityMaxIntervalMs']:.3f}ms, Cascade command {extremes['ordinaryCascadeMaxCommandMs']:.3f}ms and density Render {extremes['ordinaryDensityMaxRenderMs']:.3f}ms. Different requested cadences and observer modes prevent a single sustained-frame-rate conclusion.",
        f"The mandatory current-APK PowerFall rerun reaches {power_extremes['preparedAllRetainedMaxRenderMs']:.3f}ms Render/{power_extremes['preparedAllRetainedMaxIntervalMs']:.3f}ms reported interval with preparation and {power_extremes['skippedAllRetainedMaxRenderMs']:.3f}/{power_extremes['skippedAllRetainedMaxIntervalMs']:.3f}ms without. These all-retained values, post-command partitions and worst-frame contexts remain distinct from the78 submission controls. Worker batches reach {power_extremes['maximumObservedWorkerBatchMs']:.3f}ms; nominal cooperative budgets do not certify a frame-time bound.",
        f"Fresh recorded visual controls retain command/accept/interval maxima {extremes['recordedVisualMaxCommandMs']:.3f}/{extremes['recordedVisualMaxAcceptMs']:.3f}/{extremes['recordedVisualMaxIntervalMs']:.3f}ms, with the maximum command in {recorded_section['maxCommand']['sourceFolder']}. All four recordings and raw neighborhoods are bound separately. Recording is an additional condition, not a proven exclusive cause or a reason to omit these stalls.",
        f"First post-command idle Render is higher in {residuals['firstPostCommandIdle']['currentHigherRenderPairs']} of4 current combined-control pairs, with two texture loads/two Sprite creations in both branches after synthetic fixture-power injection. The raw frames remain visible; this is not a proven production regression. The primary L4 model median is {l4_timing['control77']['median']:.3f} to {l4_timing['current78']['median']:.3f}ms ({residuals['L4PrimaryModel']['medianCurrentMinusControlPercent']:+.1f}%), and its slower no-completed-GC subset is retained rather than dismissing it as GC.",
        'Resource plans trade eager initial work for reused dependencies. Initial and full traversal are measured independently; any slower initial or total pairs remain. Plans cache paths only and must continue to recheck real residency after eviction, errors, reloads and callbacks. Native lifecycle proofs do not turn the dependency-only device benchmark into a live coroutine/fault timing test.',
        'Natural combined control restores only the targeted archived77 model helpers, resource scanning and effect submission inside the current APK. It does not restore the entire77 application, release layout, driver state, heap or startup. Pure model constructors and fixture injection are outside timed calls; natural/frozen controls answer different questions.',
        'Detailed model stage spans overlap and are separately instrumented; they must not be summed with each other or compared as if they were the primary uninstrumented Solve pairs. Coarse per-draw zeros mean timers are disabled, not zero lookup/submission work.',
        'Supported completed-collection counters bracket Update/Render or pure calls. They do not measure incremental GC slices, allocations, total GC CPU, GPU completion or exclusive scheduler/driver/GC causes. Preparation remains cooperative and may perform a native operation beyond its nominal1ms batch budget.',
        'Native Editor and Android serialized raw outputs are separate domains. Exact same-platform controls are required; historical Android77 density raw/final outcomes are sealed separately. Historical183ms/150ms intervals cannot be retroactively assigned an exclusive cause by current maxima.',
        'Ideal swap/fall schedules, power birth protection, obstacle ownership and narrow continuation eligibility are unchanged. Rapid-next-input decorative landing replacement, physical devices, long sessions, sustained60fps, first-use touch-to-display and fresh Match Villains reference parity remain open.'
    ]
    return {'status': 'ANALYZED_EXECUTION78_WITH_REMAINING_GATES',
            'utc': datetime.now(timezone.utc).isoformat(), 'apk_sha256': artifact['sha256'],
            'source_sha256': artifacts['Source_SHA256.json'], 'qa_serial': 'emulator-5556',
            'executionValidation': validated, 'modelPairs': model, 'resourcePairs': resources,
            'naturalRows': natural, 'naturalPairs': natural_pairs, 'frozenRows': frozen,
            'powerFallCurrentRerun': power_rerun, 'recordedVisualCurrentQA': recorded_section,
            'observedRegressionsAndLimitations': residuals,
            'nativeDescriptive': native_descriptive, 'ordinaryCurrentQA': ordinary,
            'performanceExtremes': extremes, 'remainingGates': remaining,
            'artifactSHA256': dict(sorted(artifacts.items())),
            'externalEvidenceSHA256': dict(sorted(external.items())),
            'analyzerSHA256': sha(Path(__file__)), 'validatorSHA256': sha(runner_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT)
    args = parser.parse_args()
    result = build(args.out)
    destination = args.out.resolve() / 'Execution_Analysis.json'
    destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'apk_sha256': result['apk_sha256'],
                      'performanceExtremes': result['performanceExtremes']}), flush=True)


if __name__ == '__main__':
    main()
