"""Read-only validation/summary of the corrected native checkpoint74 probe.

This module never launches Unity/ADB or writes an approval. Elapsed native CPU
spans include diagnostic overhead and emulator scheduling; a frame interval is
not attributed to a command merely because it follows that command.
"""
import math
import runpy
import statistics
from pathlib import Path

RUNNER = runpy.run_path(str(Path(__file__).with_name('run_cascade_timing_device.py')),
                       run_name='cascade_provenance_contract_only')
BASE_CASES = {'L4_0_60', 'L4_0_30', 'L4_0_15', 'L1_21_30', 'L26_8_30', 'L48_16_30'}
FRAME_STAGES = ('lookupMs', 'batchAddMs', 'batchUploadMs', 'spriteUpdateMs', 'bankEndMs')
COMMAND_STAGES = ('buildMs', 'nextMs', 'dependenciesMs', 'prefetchMs', 'totalMs')


def finite_nonnegative(value):
    return isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def validate(report, variant, baseline_hashes):
    repeats = report.get('repeats', 0)
    assert isinstance(repeats, int) and 1 <= repeats <= 5
    assert variant != 'visual' or repeats == 1
    assert RUNNER['validate_report'](report, variant, repeats, require_profiling=True)
    expected_cases = {'L4_0_30'} if variant == 'visual' else BASE_CASES
    assert {r['baseCase'] for r in report['rows']} == expected_cases
    assert all(sum(r['baseCase'] == name for r in report['rows']) == repeats for name in expected_cases)
    rows = []
    for index, row in enumerate(report['rows']):
        name = row['baseCase']
        assert (row['turnHash'], row['finalHash']) == baseline_hashes[name], 'Changed model result: ' + row['name']
        assert all(finite_nonnegative(row[k]) for k in (
            'legalSearchMs', 'fixtureSetupMs', 'modelMs', 'acceptMs', 'commandMs',
            'queueInspectionMs', 'totalSynchronousProbeMs', 'firstDispatchFromAcceptMs',
            'firstCommandRenderMs', 'wallSeconds', 'totalCommandToSettledSeconds'))
        assert all(finite_nonnegative(row['enqueueCost'][k]) for k in COMMAND_STAGES)
        assert row['commandMs'] + .1 >= row['modelMs'] + row['acceptMs']
        assert row['totalSynchronousProbeMs'] + .1 >= (
            row['legalSearchMs'] + row['fixtureSetupMs'] + row['modelMs'] + row['acceptMs'] + row['queueInspectionMs'])
        assert row['acceptMs'] + .1 >= row['enqueueCost']['totalMs']
        spans = {s['kind']: s for s in row['commandSpans']}
        setup_kind = 'legal_search' if name.startswith('L4_0_') else 'fixture_setup'
        assert set(spans) == {setup_kind, 'model', 'real_accept', 'accepted_queue_inspection'}
        for span in spans.values():
            assert abs((span['finishedWall'] - span['startedWall']) * 1000 - span['milliseconds']) < .01
            assert span['gc0After'] >= span['gc0Before']
            assert span['spritesAfter'] >= span['spritesBefore']
            assert span['synchronousLoadsAfter'] >= span['synchronousLoadsBefore']
        frames = [f for f in report['frameSamples'] if f['row'] == index]
        assert all(all(finite_nonnegative(f['cost'][key]) for key in FRAME_STAGES) for f in frames)
        costs = [f['cost'] for f in frames if f['timingWindow'] and not f['costPredatesCommand']]
        assert costs, 'No post-command native render costs: ' + row['name']
        tails = [f for f in frames if f['commandFrame'] and f['costPredatesCommand']]
        assert tails
        rows.append({
            'name': row['name'], 'baseCase': name, 'repeatIndex': row['repeatIndex'],
            'recordedFrames': len(frames), 'timedCostFrames': len(costs),
            'legalSearchMs': row['legalSearchMs'], 'fixtureSetupMs': row['fixtureSetupMs'],
            'modelMs': row['modelMs'], 'acceptMs': row['acceptMs'], 'commandMs': row['commandMs'],
            'queueInspectionMs': row['queueInspectionMs'], 'totalSynchronousProbeMs': row['totalSynchronousProbeMs'],
            'firstCommandRenderMs': row['firstCommandRenderMs'],
            'commandFrameAfterUpdateElapsedMs': max(f['afterUpdateElapsedMs'] for f in tails),
            'enqueueCost': row['enqueueCost'],
            'medianRenderStageMs': {k: statistics.median(f[k] for f in costs) for k in FRAME_STAGES},
            'maxRenderStageMs': {k: max(f[k] for f in costs) for k in FRAME_STAGES},
            'geometryMisses': sum(f['geometryMisses'] for f in costs),
            'meshSlotsCreated': sum(f['meshSlotsCreated'] for f in costs),
            'maxIntervalMs': row['maxIntervalMs'],
        })
    return {
        'status': 'VALIDATED_CORRECTED_NATIVE_PROFILING74', 'variant': variant,
        'rows': rows, 'sourceSchema': report['profilingSchemaVersion'],
        'scope': 'Native command/renderer span attribution with complete frame provenance. '
                 'Diagnostics add overhead; board preparation is complete before each command. '
                 'Repeated rows reload fresh banks and only warm process/code/driver paths. '
                 'Render completion is not displayed-pixel or touch latency.',
        'causalityLimit': 'The historical checkpoint73 183 ms interval lacks these detailed spans. '
                          'It cannot be assigned an exact cause from later instrumented samples.',
    }


def validate_density(report, family, baseline_hashes):
    """Validate tagged density costs without charging a coroutine tail to Render.

    The legacy live phase/age can change after GameplayScreen.Update. Only the
    nested FrameCost timestamps and kind identify the work that Render timed.
    """
    assert family in {'crate', 'stone', 'gate', 'tiles'}
    assert report['status'] == 'PASS_OBSTACLE_DENSITY_PLAYBACK' and not report['errors']
    assert report['family'] == family and report.get('profilingSchemaVersion', 0) == 1
    names = {family + '_' + str(count) + '_' + str(repeat)
             for count in [1, 8, 16, 32, 45] for repeat in [0, 1]}
    assert len(report['rows']) == 10 and {r['name'] for r in report['rows']} == names
    assert set(baseline_hashes) == names
    frames = report['frames']
    assert frames and {f['phase'] for f in frames} == set(range(10))
    assert all(a['frame'] < b['frame'] and a['absoluteWall'] <= b['absoluteWall']
               for a, b in zip(frames, frames[1:])), 'Duplicate/unordered density frame provenance'
    rows = []
    metric_copies = ('renderMs', 'sampleMs', 'updateMs', 'bodySampleMs', 'effectsSampleMs', 'sortMs')
    counter_copies = {'draws': 'draws', 'crateDraws': 'crateDraws', 'meshQuads': 'meshQuads',
                      'meshes': 'meshes', 'renderersCreated': 'poolCreated', 'spritesCreated': 'spriteCreated'}
    for index, row in enumerate(report['rows']):
        assert row['family'] == family
        assert (row['turnHash'], row['finalHash']) == baseline_hashes[row['name']], 'Density model changed: ' + row['name']
        assert all(finite_nonnegative(row[k]) for k in (
            'preparationSeconds', 'modelMs', 'acceptMs', 'commandMs', 'settleSeconds'))
        assert 0 < row['commandStartedWall'] <= row['commandFinishedWall']
        command_elapsed = (row['commandFinishedWall'] - row['commandStartedWall']) * 1000
        assert command_elapsed + .1 >= row['commandMs']
        assert row['commandMs'] + .1 >= row['modelMs'] + row['acceptMs']
        enqueue = row['enqueueCost']
        assert enqueue['frame'] == row['commandFrame'] and enqueue['phases'] > 0
        assert all(finite_nonnegative(enqueue[k]) for k in COMMAND_STAGES)
        assert row['acceptMs'] + .1 >= enqueue['totalMs']
        selected = [f for f in frames if f['phase'] == index]
        assert selected and selected[0]['frame'] == row['commandFrame'], 'Density command frame was lost'
        command_frames = [f for f in selected if f['frame'] == row['commandFrame']]
        assert len(command_frames) == 1
        for frame in selected:
            cost = frame['cost']
            assert cost['frame'] == frame['frame'] and cost['updateStartedWall'] > 0
            assert (cost['updateStartedWall'] <= cost['renderStartedWall'] <= cost['renderFinishedWall']
                    <= cost['updateFinishedWall'] <= frame['absoluteWall'])
            assert all(finite_nonnegative(cost[k]) for k in metric_copies + FRAME_STAGES)
            assert all(frame[k] == cost[k] for k in metric_copies), 'Legacy density timer no longer matches tagged cost'
            assert all(frame[k] == cost[v] for k, v in counter_copies.items()), 'Legacy density counter differs'
            assert all(isinstance(cost[k], int) and cost[k] >= 0 for k in (
                'geometryMisses', 'meshSlotsCreated', 'poolCreated', 'spriteCreated', 'draws', 'meshes', 'meshQuads'))
            assert finite_nonnegative(frame['intervalMs'])
        command_frame = command_frames[0]
        command_cost = command_frame['cost']
        prior_cost = command_cost['updateFinishedWall'] <= row['commandStartedWall']
        subsequent_cost = command_cost['updateStartedWall'] >= row['commandFinishedWall']
        assert prior_cost or subsequent_cost, 'Density Update/command spans overlap without an owner'
        after_update = (command_frame['absoluteWall'] - command_cost['updateFinishedWall']) * 1000
        if prior_cost:
            assert after_update + .1 >= row['commandMs'], 'Density command tail elapsed time was truncated'
        costs = [f['cost'] for f in selected
                 if f['cost']['updateStartedWall'] >= row['commandFinishedWall'] and f['cost']['kind'] != 'idle']
        assert costs, 'No actual post-command density playback costs'
        assert row['peakDraws'] == max(f['draws'] for f in selected)
        assert row['peakMeshes'] == max(f['meshes'] for f in selected)
        assert row['renderersCreated'] == sum(f['renderersCreated'] for f in selected)
        peak = max(range(len(selected)), key=lambda n: selected[n]['cost']['renderMs'])
        interval = max(range(len(selected)), key=lambda n: selected[n]['intervalMs'])
        rows.append({
            'name': row['name'], 'family': family, 'recordedFrames': len(selected),
            'taggedPlaybackCostFrames': len(costs),
            'modelMs': row['modelMs'], 'acceptMs': row['acceptMs'], 'commandMs': row['commandMs'],
            'enqueueCost': enqueue,
            'commandFrameTail': {
                'frame': row['commandFrame'], 'costPredatesCommand': prior_cost,
                'costFollowsCommand': subsequent_cost, 'afterUpdateElapsedMs': after_update,
                'commandStartedWall': row['commandStartedWall'], 'commandFinishedWall': row['commandFinishedWall'],
                'postCommandTimerElapsedMs': max(0, command_elapsed - row['commandMs']),
                'frameAbsoluteWall': command_frame['absoluteWall'], 'taggedCost': command_cost,
            },
            'medianRenderStageMs': {k: statistics.median(f[k] for f in costs) for k in FRAME_STAGES},
            'maxRenderStageMs': {k: max(f[k] for f in costs) for k in FRAME_STAGES},
            'geometryMisses': sum(f['geometryMisses'] for f in costs),
            'meshSlotsCreated': sum(f['meshSlotsCreated'] for f in costs),
            'legacyPhaseDiffersFromCostFrames': sum(f['step'] != f['cost']['kind'] for f in selected),
            'worstRenderFrame': selected[peak],
            'worstRenderNeighbors': selected[max(0, peak - 1):peak + 2],
            'worstIntervalFrame': selected[interval],
            'worstIntervalNeighbors': selected[max(0, interval - 1):interval + 2],
        })
    return {
        'status': 'VALIDATED_DENSITY_NATIVE_PROFILING74', 'family': family,
        'sourceSchema': report['profilingSchemaVersion'], 'rows': rows,
        'scope': 'Ten unchanged deterministic density turns with tagged native Update/Render costs and '
                 'actual command-frame tail ownership. Row live phase/age can change after the timed Update; '
                 'the nested FrameCost owns measured work. Diagnostic timers and emulator scheduling add overhead.',
        'causalityLimit': 'A following frame interval includes time outside Render and is not evidence that '
                          'Render caused the command tail or the historical183ms interval.',
    }
