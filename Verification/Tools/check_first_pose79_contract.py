"""Reject corrupted copies of an actual FirstPose79 report.

These are Python evidence-contract checks, not Unity or Android executions.
The original bytes are read only. No acceptance threshold requires a speedup.
"""
import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from run_first_pose79_device import validate_report

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / 'Verification/Evidence/Gameplay79/FirstPose/Report.json'
DEFAULT_OUTPUT = ROOT / '.verification-cache/Gameplay79/FirstPose79_Validator_RawChecks.json'
RUNNER = ROOT / 'Verification/Tools/run_first_pose79_device.py'
FRAME_VALIDATOR = ROOT / 'Verification/Tools/run_execution78_device.py'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def need(value, message):
    if not value:
        raise AssertionError(message)


def _set(report, path, value):
    target = report
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def _trace(report, change, row=1, field='startupTraceJson'):
    value = json.loads(report['rows'][row][field])
    change(value)
    report['rows'][row][field] = json.dumps(value, separators=(',', ':'))


def _frame(report, row=1, pending=False):
    item = report['rows'][row]
    values = report['frames'][item['frameStart']:item['frameStart'] + item['frameCount']]
    return next(value for value in values if not pending or value['pending'])


def mutation_specs():
    """Return bounded independent mutations; no report is read or changed here."""
    specs = []

    def add(name, category, transform):
        specs.append((name, category, transform))

    def set_value(name, category, path, value):
        add(name, category, lambda report: _set(report, path, value))

    def trace_value(name, category, field, value, row=1, trace_field='startupTraceJson'):
        add(name, category, lambda report: _trace(report, lambda trace: trace.__setitem__(field, value), row, trace_field))

    set_value('failed_status', 'report_identity', ('status',), 'FAIL_NATIVE_FIRST_POSE79')
    set_value('unreported_error', 'report_identity', ('errors',), ['Deliberate contract counterexample'])
    set_value('stale_checkpoint', 'report_identity', ('sourceCheckpoint',), 78)
    set_value('unknown_schema', 'report_identity', ('schema',), 2)
    set_value('nonisolated_profile', 'report_identity', ('isolatedProfile',), False)
    set_value('launch_overlay_not_cleared', 'report_identity', ('launchCleared',), False)
    set_value('frame_drop_hidden', 'frame_provenance', ('droppedFrames',), 1)
    set_value('unsupported_cadence', 'report_identity', ('targetFps',), 30)
    add('missing_natural_row', 'scope', lambda report: report['rows'].pop(1))
    add('orphaned_frame', 'frame_provenance', lambda report: report['frames'].append(copy.deepcopy(report['frames'][-1])))

    add('camera_before_submitted_head', 'camera_witness', lambda report: _trace(report, lambda trace: trace.__setitem__('cameraWitnessTicks', trace['headSubmittedTicks'] - 1)))
    add('wrong_camera_frame', 'camera_witness', lambda report: _trace(report, lambda trace: trace.__setitem__('cameraWitnessFrame', trace['headSubmittedFrame'] - 1)))
    add('worker_before_camera', 'worker_chronology', lambda report: _trace(report, lambda trace: trace.__setitem__('workerStartedTicks', trace['cameraWitnessTicks'] - 1)))
    add('worker_on_main_thread', 'thread_ownership', lambda report: _trace(report, lambda trace: trace.__setitem__('workerThreadId', trace['callerThreadId'])))
    trace_value('missing_worker_thread', 'thread_ownership', 'workerThreadId', 0)
    trace_value('pending_trace_after_ready', 'pending_ownership', 'pending', True)
    trace_value('cancelled_natural_job', 'pending_ownership', 'cancelled', True)
    trace_value('failed_natural_job', 'pending_ownership', 'workerFailed', True)
    trace_value('unexpected_resumed_generation', 'pending_ownership', 'resumed', True)
    add('metadata_generation_changed', 'metadata_ownership', lambda report: _trace(report, lambda trace: trace.__setitem__('generation', trace['generation'] + 1), field='metadataTraceJson'))
    add('metadata_worker_ticks_changed', 'metadata_ownership', lambda report: _trace(report, lambda trace: trace.__setitem__('workerFinishedTicks', trace['workerFinishedTicks'] + 1), field='metadataTraceJson'))
    trace_value('sync_control_started_worker', 'thread_ownership', 'jobStartedFrame', 1, row=0)

    set_value('current_branch_not_initially_pending', 'pending_ownership', ('rows', 1, 'initialPending'), False)
    add('accept_return_precedes_command', 'command_ticks', lambda report: report['rows'][1].__setitem__('commandFinishedTicks', report['rows'][1]['commandStartedTicks'] - 1))
    add('model_callback_after_command_return', 'command_ticks', lambda report: report['rows'][1].__setitem__('modelAcceptedTicks', report['rows'][1]['commandFinishedTicks'] + 1))
    add('command_duration_disagrees_with_ticks', 'command_ticks', lambda report: report['rows'][1].__setitem__('commandMs', report['rows'][1]['commandMs'] + 1))
    add('inspection_was_done_before_settlement', 'inspection_timing', lambda report: report['rows'][1].__setitem__('queueInspectionStartedTicks', report['rows'][1]['settledTicks'] - 1))
    add('queue_inspection_duration_disagrees', 'inspection_timing', lambda report: report['rows'][1].__setitem__('queueInspectionMs', report['rows'][1]['queueInspectionMs'] + 1))
    set_value('head_object_replaced', 'queue_ownership', ('rows', 1, 'headReferenceRetained'), False)
    set_value('head_duration_changed', 'phase_schedule', ('rows', 1, 'headDuration'), .22)
    add('phase_count_changed', 'phase_schedule', lambda report: report['rows'][1].__setitem__('queuedSteps', report['rows'][1]['queuedSteps'] + 1))
    set_value('first_phase_is_not_swap', 'phase_schedule', ('rows', 1, 'phases', 0, 'kind'), 'power')
    set_value('first_swap_duration_changed', 'phase_schedule', ('rows', 1, 'phases', 0, 'duration'), .22)
    add('ideal_schedule_changed', 'phase_schedule', lambda report: report['rows'][1].__setitem__('scheduledSeconds', report['rows'][1]['scheduledSeconds'] + .1))

    set_value('malformed_raw_hash', 'hash_parity', ('rows', 1, 'turnHash'), 'not-a-sha256')
    for field in ('turnHash', 'finalHash', 'checkpointHash', 'dictionaryOrderHash', 'queueHash', 'resourceHash'):
        add('changed_paired_' + field, 'hash_parity', lambda report, key=field: report['rows'][1].__setitem__(key, ('0' if report['rows'][1][key][0] != '0' else '1') + report['rows'][1][key][1:]))
    set_value('duplicate_model_callback', 'settlement', ('rows', 1, 'modelCallbacks'), 2)
    set_value('duplicate_settlement', 'settlement', ('rows', 1, 'settlementCallbacks'), 2)
    set_value('missing_action_callback', 'settlement', ('rows', 1, 'actionCallbacks'), 0)
    set_value('settled_before_gate_release', 'settlement', ('rows', 16, 'settledBeforeRelease'), True)

    trace_value('hold_not_marked_held', 'gate_control', 'held', False, row=16)
    trace_value('hold_has_no_head_end', 'gate_control', 'headEndedFrame', 0, row=16)
    set_value('hold_gate_not_entered', 'gate_control', ('rows', 16, 'gateEnteredTicks'), 0)
    add('gate_exited_before_release', 'gate_control', lambda report: report['rows'][16].__setitem__('gateExitedTicks', report['rows'][16]['holdReleasedTicks'] - 1))
    set_value('hold_has_too_few_samples', 'gate_control', ('rows', 16, 'holdSamples'), 2)
    set_value('hold_pose_changed', 'gate_control', ('rows', 16, 'holdPoseAfterHash'), '0' * 64)
    add('hold_final_state_changed', 'hold_normal_parity', lambda report: report['rows'][16].__setitem__('finalHash', ('0' if report['rows'][16]['finalHash'][0] != '0' else '1') + report['rows'][16]['finalHash'][1:]))
    add('hold_resource_plan_changed', 'hold_normal_parity', lambda report: report['rows'][16].__setitem__('resourceHash', ('0' if report['rows'][16]['resourceHash'][0] != '0' else '1') + report['rows'][16]['resourceHash'][1:]))

    add('pending_frame_exposes_action', 'pending_input_gate', lambda report: _frame(report, pending=True).__setitem__('canAct', True))
    add('pending_frame_exposes_buffer', 'pending_input_gate', lambda report: _frame(report, pending=True).__setitem__('canBuffer', True))
    add('pending_frame_not_busy', 'pending_input_gate', lambda report: _frame(report, pending=True).__setitem__('busy', False))
    add('frame_ownership_changed', 'frame_provenance', lambda report: _frame(report).__setitem__('row', 99))
    add('cost_tagged_to_different_frame', 'frame_provenance', lambda report: _frame(report)['cost'].__setitem__('frame', _frame(report)['frame'] + 1))
    add('negative_frame_interval', 'frame_provenance', lambda report: _frame(report).__setitem__('intervalMs', -1))
    add('cost_timestamp_escapes_observer', 'frame_provenance', lambda report: _frame(report)['cost'].__setitem__('updateFinishedWall', _frame(report)['wall'] + 1))
    add('nested_render_span_escaped', 'frame_provenance', lambda report: _frame(report)['cost'].__setitem__('renderMs', _frame(report)['cost']['updateMs'] + 100))
    add('detailed_draw_observer_substituted', 'observer_mode', lambda report: _frame(report)['cost'].__setitem__('lookupMs', .01))
    return specs


def check(report):
    """I/O-free original validation and independent deep-copy counterexamples."""
    original_semantic_hash = digest(canonical(report))
    original_validation = validate_report(report)
    specs = mutation_specs()
    need(len(specs) >= 30, 'Fewer than30 deliberate counterexamples')
    need(len({name for name, _, _ in specs}) == len(specs), 'Duplicate counterexample names')
    rows, failures = [], []
    for name, category, mutate in specs:
        damaged = copy.deepcopy(report)
        mutate(damaged)
        need(digest(canonical(damaged)) != original_semantic_hash, 'Counterexample had no effect: ' + name)
        rejected, exception, detail = False, None, None
        try:
            validate_report(damaged)
        except (AssertionError, KeyError, TypeError, ValueError, IndexError) as error:
            rejected, exception, detail = True, type(error).__name__, str(error)
        rows.append({'name': name, 'category': category, 'rejected': rejected, 'exception': exception, 'detail': detail})
        if not rejected:
            failures.append(name)
        need(digest(canonical(report)) == original_semantic_hash, 'Original in-memory report was changed')
    # Revalidation after every deep-copy mutation also preserves complete signed
    # performance summaries; a slower result is never made a negative control.
    need(validate_report(report) == original_validation, 'Original validation changed')
    return {'status': 'PASS_PYTHON_FIRST_POSE79_CONTRACT_CONTROLS' if not failures else 'FAIL_PYTHON_FIRST_POSE79_CONTRACT_CONTROLS',
            'scope': 'Python-only validation of one actual Android report and deliberately corrupted deep copies. This does not execute Unity, Android, rendering, gameplay or a performance experiment. No favorable timing threshold.',
            'positiveOriginalAccepted': True, 'originalInMemoryUnchanged': True,
            'negativeControls': len(rows), 'rejectedControls': sum(row['rejected'] for row in rows),
            'categories': sorted({row['category'] for row in rows}), 'controls': rows, 'failures': failures,
            'originalSemanticSHA256': original_semantic_hash, 'originalValidation': original_validation}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = args.report.resolve()
    if not source.is_relative_to((ROOT / 'Verification/Evidence/Gameplay79').resolve()):
        raise AssertionError('Use the actual checkpoint79 evidence report')
    raw = source.read_bytes()
    value = check(json.loads(raw.decode('utf-8-sig')))
    after = source.read_bytes()
    if raw != after:
        raise AssertionError('Original report bytes changed')
    value.update({'utc': datetime.now(timezone.utc).isoformat(), 'report': source.relative_to(ROOT).as_posix(),
                  'reportSHA256': digest(raw), 'originalBytesUnchanged': True,
                  'runnerSHA256': digest(RUNNER.read_bytes()), 'frameCostValidatorSHA256': digest(FRAME_VALIDATOR.read_bytes()),
                  'toolSHA256': digest(Path(__file__).read_bytes())})
    output = args.out.resolve()
    allowed = ((ROOT / '.verification-cache/Gameplay79').resolve(), (ROOT / 'Verification/Evidence/Gameplay79').resolve())
    if not any(output.is_relative_to(root) for root in allowed) or output == source:
        raise AssertionError('Unsafe output or attempted input replacement')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value[key] for key in ('status', 'negativeControls', 'rejectedControls', 'reportSHA256', 'originalBytesUnchanged', 'failures')}), flush=True)
    if value['failures']:
        raise AssertionError('Corrupted copies were accepted: ' + ', '.join(value['failures']))


if __name__ == '__main__':
    main()
