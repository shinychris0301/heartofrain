"""Describe first-pose79 controls without approving overall gameplay speed.

build() performs reads only. The CLI also remains read-only unless --out is
explicitly supplied; it never starts Unity, ADB, a collector or visual review.
"""
import argparse
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

from run_first_pose79_device import validate_report
from qa_android_target import validate_qa_target

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'Verification/Evidence/Gameplay79'
BASE = ROOT / 'Verification/Evidence/Gameplay78'
MODEL = 'Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs'
SNAPSHOT_SOURCES = {
    'currentModelSHA256': MODEL,
    'controlSourceSHA256': 'Unity/Assets/HeartOfTheRain/Verification/Snapshot78Control79.cs',
    'proofSourceSHA256': 'Unity/Assets/HeartOfTheRain/Verification/Snapshot79Proof.cs',
    'verificationSourceSHA256': 'Unity/Assets/HeartOfTheRain/Verification/Editor/Snapshot79Verification.cs',
}
METRICS = ('updateMs', 'renderMs', 'outerSampleMs', 'bodySampleMs', 'effectsSampleMs',
           'sortMs', 'outerDrawMs', 'outerUploadMs', 'outerWrapperResidualMs')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def need(value, message):
    if not value:
        raise AssertionError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def utc(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(parsed.tzinfo is not None, 'Missing UTC timezone')
    return parsed.astimezone(timezone.utc)


def stats(values):
    values = list(values)
    need(all(finite(v) for v in values), 'Nonfinite descriptive measurement')
    if not values:
        return {'samples': 0, 'median': None, 'p95': None, 'max': None}
    ordered = sorted(values)
    return {'samples': len(values), 'median': statistics.median(values),
            'p95': ordered[math.ceil(len(ordered) * .95) - 1], 'max': ordered[-1]}


def overlap(start, end, begin, finish):
    return start < finish and end > begin


def collections(cost, before='BeforeUpdate', after='AfterUpdate'):
    return {str(g): cost[f'gc{g}{after}'] - cost[f'gc{g}{before}']
            if g <= cost['gcMaxGeneration'] else None for g in range(3)}


def total_collections(frames, before='BeforeUpdate', after='AfterUpdate'):
    entries = [collections(f['cost'], before, after) for f in frames]
    return {str(g): sum(e[str(g)] for e in entries if e[str(g)] is not None)
            if any(e[str(g)] is not None for e in entries) else None for g in range(3)}


def frame_stats(frames, target_fps=60):
    frames = list(frames)
    return {'frames': len(frames), 'targetFps': target_fps,
            'intervalMs': stats(f['intervalMs'] for f in frames),
            'intervalsOver1_5Target': sum(f['intervalMs'] > 1500 / target_fps for f in frames),
            'intervalsOver100Ms': sum(f['intervalMs'] > 100 for f in frames),
            'metrics': {key: stats(f['cost'][key] for f in frames) for key in METRICS},
            'demandSpriteCreates': sum(f['cost']['spriteCreated'] for f in frames),
            'demandGeometryMisses': sum(f['cost']['geometryMisses'] for f in frames),
            'rendererCreates': sum(f['cost']['poolCreated'] for f in frames),
            'meshSlotCreates': sum(f['cost']['meshSlotsCreated'] for f in frames),
            'completedCollectionsWithinUpdate': total_collections(frames),
            'completedCollectionsWithinRender': total_collections(frames, 'BeforeRender', 'AfterRender')}


def frame_context(frames, at, row, trace):
    frame = frames[at]
    previous = frames[at - 1] if at else None
    start = previous['cost']['updateStartedWall'] if previous else None
    end = frame['cost']['updateStartedWall']
    command_overlap = None if start is None else overlap(row['commandStartedWall'], row['commandFinishedWall'], start, end)
    preparation_overlap = None
    if not row['checkpoint78'] and start is not None:
        preparation_overlap = overlap(trace['jobStartedWall'], trace['jobCompletedWall'], start, end)
    return {'frame': frame, 'neighbors': frames[max(0, at - 2):at + 3],
            'previousUpdateStartedWall': start, 'currentUpdateStartedWall': end,
            'updateStartBracketMs': None if start is None else (end - start) * 1000,
            'inputCommandOverlapsUpdateStartBracket': command_overlap,
            'queuedJobThroughMainPollOverlapsUpdateStartBracket': preparation_overlap,
            'scope': 'The interval and main queue-to-poll window include unrelated scheduling and work. They are not exclusive method, worker CPU, GC-duration or physical-display attribution.'}


def row_analysis(row, frames, frequency):
    trace = json.loads(row['startupTraceJson'])
    current = not row['checkpoint78']
    # A cost-tagged head Render starts before the end-of-Render submit stamp.
    # Include that whole frame, then distinguish subsequent camera frames.
    tagged_swap = [f for f in frames if f['cost']['kind'] == 'swap' and f['cost']['renderStartedWall'] >= row['phases'][0]['wall']]
    need(tagged_swap, 'Missing cost-tagged swap Render: ' + row['name'])
    first_frame = trace['headSubmittedFrame'] if current else tagged_swap[0]['frame']
    post = [f for f in frames if f['frame'] >= first_frame]
    after_camera = [f for f in frames if current and f['frame'] > trace['cameraWitnessFrame']]
    installed = [f for f in frames if current and f['frame'] >= trace['tailInstalledFrame']]
    first_head = [f for f in frames if f['frame'] == first_frame]
    idle = [f for f in frames if not f['busy'] and not f['pending'] and f['cost']['kind'] == 'idle' and f['cost']['renderStartedWall'] >= row['settledWall']]
    pending = [f for f in frames if f['pending']]
    need(first_head and post and first_head[0]['cost']['kind'] == 'swap', 'Missing actual first-head CPU frame: ' + row['name'])
    if current:
        from_command = lambda key: (trace[key] - row['commandStartedTicks']) * 1000 / frequency
        first_latencies = {'firstHeadSubmittedMs': from_command('headSubmittedTicks'),
                           'ownCameraWitnessMs': from_command('cameraWitnessTicks'),
                           'workerStartedMs': from_command('workerStartedTicks'),
                           'workerFinishedMs': from_command('workerFinishedTicks'),
                           'mainTailInstalledMs': from_command('tailInstalledTicks'),
                           'metadataObservedMs': (row['metadataReadyTicks'] - row['commandStartedTicks']) * 1000 / frequency,
                           'scope': 'CPU submission and actual own-camera onPostRender are measured separately. Neither measures panel scan-out or OS touch latency.'}
    else:
        first_latencies = {'firstHeadSubmittedMs': None, 'ownCameraWitnessMs': None,
                           'firstPhaseDispatchedMs': (row['phases'][0]['ticks'] - row['commandStartedTicks']) * 1000 / frequency,
                           'scope': 'Synchronous78 control retains its eager path and has no startup camera trace; StepStarted is dispatch, not proof of rendered pixels.'}
    first_latencies['firstCostTaggedSwapRenderStartedMs'] = (tagged_swap[0]['cost']['renderStartedWall'] - row['commandStartedWall']) * 1000
    first_latencies['firstCostTaggedSwapRenderFinishedMs'] = (tagged_swap[0]['cost']['renderFinishedWall'] - row['commandStartedWall']) * 1000
    worst = {}
    for name, key in [('interval', lambda f: f['intervalMs']), ('render', lambda f: f['cost']['renderMs']), ('update', lambda f: f['cost']['updateMs'])]:
        chosen = max(post, key=key)
        worst[name] = frame_context(frames, frames.index(chosen), row, trace)
    return {'name': row['name'], 'fixture': row['fixture'], 'dispatch': row['dispatch'],
            'checkpoint78': row['checkpoint78'], 'controlledHold': row['holdWorker'],
            'commandMs': row['commandMs'], 'preAcceptMs': row['preAcceptMs'],
            'presentationAcceptMs': row['presentationAcceptMs'], 'metadataWaitMs': row['metadataWaitMs'],
            'postPlaybackInspectionMs': row['queueInspectionMs'], 'commandToSettledSeconds': row['settleSeconds'],
            'idealScheduledSeconds': row['scheduledSeconds'], 'wallMinusIdealSeconds': row['settleSeconds'] - row['scheduledSeconds'],
            'initialEnqueueCost': row['initialEnqueueCost'], 'completedEnqueueCost': row['completedEnqueueCost'],
            'firstPoseLatencies': first_latencies, 'startupTrace': trace,
            'controlledGateWaitMs': (row['gateExitedTicks'] - row['gateEnteredTicks']) * 1000 / frequency if row['holdWorker'] else None,
            'allFrames': frame_stats(frames), 'firstHeadCpuFrame': first_head,
            'atAndAfterFirstHeadFrame': frame_stats(post), 'afterOwnCameraFrame': frame_stats(after_camera),
            'atAndAfterTailInstalledFrame': frame_stats(installed), 'pendingPlanFrames': frame_stats(pending),
            'postTurnIdleFrames': frame_stats(idle), 'worstPostHeadNeighborhoods': worst,
            'outcomeHashes': {key: row[key] for key in ('turnHash', 'finalHash', 'checkpointHash', 'dictionaryOrderHash', 'queueHash', 'resourceHash')}}


def snapshot_analysis(report, baseline):
    need(report['status'] == 'PASS_NATIVE_SNAPSHOT79' and not report['errors'], 'Snapshot79 native proof failed')
    need(report['exact78Control'] and all(report[key] for key in ('rawParity', 'finalParity', 'checkpointParity', 'dictionaryParity')), 'Snapshot raw/control parity incomplete')
    need(report['modelCases'] == len(report['rows']) == 350 and len(report['traces']) == 8 and len(report['timings']) == 24, 'Snapshot proof scope incomplete')
    archived = {r['name']: r for r in baseline['rows']}
    for row in report['rows']:
        need(all(row[k] == archived[row['name']][k] for k in ('rawHash', 'finalHash', 'checkpointHash', 'dictionaryOrder')), 'Native Snapshot79 differs from sealed same-platform78 outcome')
    timings = []
    for row in report['timings']:
        need(row['mode'] in ('cold', 'warm') and len(row['pairs']) == 12, 'Snapshot direct pairing incomplete')
        pairs = []
        for index, p in enumerate(row['pairs']):
            need(p['index'] == index and p['controlFirst'] is (index % 2 == 0), 'Snapshot pair order changed')
            need(p['controlHash'] == p['currentHash'], 'Snapshot direct outputs differ')
            need(all(finite(p[k]) and p[k] >= 0 for k in ('controlMs', 'currentMs')), 'Invalid direct timing')
            for branch in ('control', 'current'):
                calls, counts = p[branch + 'Calls'], p[branch + 'CallCollections']
                need(len(calls) == len(counts) == row['calls'] and all(finite(v) and v >= 0 for v in calls), 'Snapshot direct calls were truncated')
                need(all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in counts), 'Invalid direct collection counters')
                need(abs(sum(calls) - p[branch + 'Ms']) < .000001 and sum(counts) == p[branch + 'Collections'], 'Snapshot direct totals differ')
            pairs.append({'index': index, 'controlFirst': p['controlFirst'], 'control78Ms': p['controlMs'], 'current79Ms': p['currentMs'],
                          'currentMinusControl78Ms': p['currentMs'] - p['controlMs'], 'controlCompletedCollections': p['controlCollections'], 'currentCompletedCollections': p['currentCollections'],
                          'controlCalls': p['controlCalls'], 'currentCalls': p['currentCalls'], 'controlCallCollections': p['controlCallCollections'], 'currentCallCollections': p['currentCallCollections']})
        control = stats(p['control78Ms'] for p in pairs)
        current = stats(p['current79Ms'] for p in pairs)
        slower = sum(p['currentMinusControl78Ms'] > 0 for p in pairs)
        need(abs(control['median'] - row['controlMedianMs']) < 1e-8 and abs(current['median'] - row['currentMedianMs']) < 1e-8 and slower == row['slowerPairs'], 'Snapshot report omitted slower results or changed medians')
        timings.append({'name': row['name'], 'mode': row['mode'], 'traceHash': row['traceHash'], 'calls': row['calls'], 'control78': control, 'current79': current,
                        'differenceOfMedians': current['median'] - control['median'], 'signedPairDifferences': stats(p['currentMinusControl78Ms'] for p in pairs),
                        'currentSlowerPairs': slower, 'pairs': pairs, 'controlDiagnostic': row['controlDiagnostic'], 'currentDiagnostic': row['currentDiagnostic']})
    need(len({(r['name'], r['mode']) for r in timings}) == 24, 'Snapshot workload repeated instead of covered')
    return {'status': report['status'], 'checks': report['checks'], 'modelCases': report['modelCases'], 'workloads': 24, 'pairs': 288,
            'traceDiagnostics': report['traces'], 'directTimings': timings, 'invalidStateTransitions': report['transitions'],
            'presentationFaultCases': report['presentationFaultCases'], 'scope': report['scope'],
            'limits': ['Pinned Unity Editor direct Snapshot timing is separate from Android commands and frame pacing.', 'Cold means a new diagnostic model/cache, not OS process or player cold start.', 'State application, trace capture, hashing, diagnostics and construction are outside primary timed calls.', 'Completed collection counters do not measure GC CPU; no allocation-byte claim.']}


def build(out=DEFAULT):
    out = Path(out).resolve()
    need(out.is_relative_to((ROOT / 'Verification/Evidence').resolve()), 'Unsafe evidence root')
    artifacts, external = {}, {}

    def read(name):
        path = (out / name).resolve()
        need(path.is_relative_to(out) and path.is_file(), 'Missing current evidence: ' + name)
        artifacts[path.relative_to(out).as_posix()] = sha(path)
        return json.loads(path.read_text('utf-8-sig'))

    def prior(name, expected):
        path = BASE / name
        need(path.is_file() and sha(path) == expected, 'Changed sealed78 evidence: ' + name)
        external[path.relative_to(ROOT).as_posix()] = expected
        return json.loads(path.read_text('utf-8-sig'))

    source = read('Source_SHA256.json')
    source_sha = artifacts['Source_SHA256.json']
    baseline = read('Baseline78.json')
    sealed = read('Baseline78_Summary.json')
    old_source = read('Baseline78_Source_SHA256.json')
    need(baseline['status'] == 'PRESERVED_VERIFIED78_BASELINE' and sealed['source_checkpoint'] == 78, 'Wrong baseline identity')
    need(artifacts['Baseline78_Summary.json'] == baseline['summary_sha256'] and artifacts['Baseline78_Source_SHA256.json'] == baseline['source_sha256'], 'Baseline copies differ')
    need(sealed['source_sha256'] == baseline['source_sha256'] and sealed['apk_sha256'] == baseline['apk_sha256'], 'Baseline source/APK domains differ')
    prior('Summary.json', baseline['summary_sha256'])
    prior('Source_SHA256.json', baseline['source_sha256'])
    archived_model = prior('Native/ModelWork78.json', sealed['evidence_sha256']['Native/ModelWork78.json'])
    snapshot = read('Native/Snapshot79.json')
    process = read('Native/Snapshot79_Process.json')
    need(process['exitCode'] == 0 and not process['timedOut'] and process['version'].startswith('2022.3.62f3'), 'Snapshot suite did not pass pinned Unity')
    need(utc(source['utc']) <= utc(process['startedUtc']) <= utc(snapshot['utc']) <= utc(process['finishedUtc']), 'Snapshot process chronology differs')
    manifest = read(process['sourceManifest'])
    need(manifest['files'] == source['files'] and artifacts[process['sourceManifest']] == process['sourceSHA256'], 'Snapshot ran other source inputs')
    need(snapshot['archived78ModelSHA256'] == old_source['files'][MODEL] and snapshot['baseline78ModelReportSHA256'] == sealed['evidence_sha256']['Native/ModelWork78.json'], 'Snapshot archived control domain differs')
    need(all(snapshot[k] == source['files'][p] for k, p in SNAPSHOT_SOURCES.items()), 'Snapshot proof source fields differ')
    native = snapshot_analysis(snapshot, archived_model)
    artifact = read('APK_Artifact.json')
    build_process = read('AndroidBuild_Process.json')
    build_source = read('Build_Source_SHA256.json')
    need(build_process['exitCode'] == 0 and not build_process['timedOut'] and build_source['files'] == source['files'], 'Device build source failed/differs')
    need(utc(process['finishedUtc']) <= utc(build_process['startedUtc']), 'Device build predates current native proof')
    digest = artifact['sha256']
    built_apk = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    need(built_apk.is_file() and built_apk.stat().st_size == artifact['bytes'] and sha(built_apk) == digest, 'Current development APK differs from the analyzed artifact')
    report = read('FirstPose/Report.json')
    installation = read('FirstPose/Installation.json')
    validated = validate_report(report)
    target = validate_qa_target(installation['serial'], out)
    need(target['isolated_clone'] is True and target['serial'] == 'emulator-5558', 'Current79 requires the authorized isolated clone')
    read('QA_Target.json')
    need(target['target_record_sha256'] == artifacts['QA_Target.json'] and installation.get('qa_target') == target, 'Clone authorization/audit binding differs')
    need(installation['status'] == 'PASS_FIRST_POSE79_DEVICE_AUDIT', 'First-pose device audit missing')
    need(installation['apk_sha256'] == installation['installed_apk_sha256'] == digest and installation['runtime_errors'] == 0, 'Wrong current first-pose APK/runtime')
    need(installation['validated'] == validated, 'Transport raw-validation result differs')
    need(installation['data_unchanged'] and installation['before'] == installation['after'], 'First-pose changed real saved data')
    need(utc(build_process['finishedUtc']) <= utc(installation['utc']) <= utc(report['utc']) <= utc(installation['finishedUtc']), 'Device/build/report chronology differs')
    log = out / 'FirstPose/Runtime.log'
    need(log.is_file(), 'Missing actual first-pose runtime log')
    artifacts['FirstPose/Runtime.log'] = sha(log)
    rows = [row_analysis(row, report['frames'][row['frameStart']:row['frameStart'] + row['frameCount']], report['stopwatchFrequency']) for row in report['rows']]
    normal = [r for r in rows if not r['controlledHold']]
    holds = [r for r in rows if r['controlledHold']]
    current = [r for r in normal if not r['checkpoint78']]
    pairs = validated['pairs']
    slower = [p for p in pairs if p['currentMinusControlCommandMs'] > 0]
    maxima = {}
    for label, metric in [('maxPostHeadRender', 'render'), ('maxPostHeadUpdate', 'update'), ('maxPostHeadInterval', 'interval')]:
        def value(r):
            frame = r['worstPostHeadNeighborhoods'][metric]['frame']
            return frame['intervalMs'] if metric == 'interval' else frame['cost'][metric + 'Ms']
        peak = max(current, key=value)
        maxima[label] = {'row': peak['name'], 'milliseconds': value(peak), 'context': peak['worstPostHeadNeighborhoods'][metric]}
    maxima['maxCurrentCommandMs'] = max(r['commandMs'] for r in current)
    maxima['maxSynchronousPreAcceptMs'] = max(r['preAcceptMs'] for r in current)
    maxima['maxCurrentPresentationAcceptMs'] = max(r['presentationAcceptMs'] for r in current)
    maxima['maxMainInstallMs'] = max(r['startupTrace']['mainInstallMs'] for r in current)
    maxima['maxUncontrolledHoldMs'] = max(r['startupTrace']['holdMs'] for r in current)
    gates = [
        {'gate': 'synchronous_model_before_first_pose', 'measuredMaximumPreAcceptMs': maxima['maxSynchronousPreAcceptMs'], 'scope': 'The real command guard/model remains synchronous. This is the runtime PlayerSwap span before ModelTurnAccepted, not an exclusive BoardModel timer.'},
        {'gate': 'work_after_first_pose_remains_visible', 'postHeadExtremes': maxima, 'scope': 'A smaller initial Accept does not erase worker elapsed, main installation, rendering or later frame intervals. All post-head maxima/neighborhoods are retained.'},
        {'gate': 'single_pair_and_observer_limits', 'currentSlowerCommandPairs': slower, 'scope': 'One pair per level/dispatch in one process with fresh banks; no statistical, cold-process, universal speedup, sustained60fps or exclusive scheduling/GC claim.'},
        {'gate': 'head_end_wait_and_cancellation_scope', 'maxUncontrolledHoldMs': maxima['maxUncontrolledHoldMs'], 'scope': 'Two induced waits are correctness controls and excluded from natural performance maxima. Native lifecycle/fault controls are separate from device performance and durable service receipts.'},
        {'gate': 'wider_gameplay_and_devices', 'scope': 'Dense effects, long sessions, memory pressure, broader continuation, fresh reference-app comparison and physical Android hardware remain separate gates.'},
    ]
    return {'status': 'ANALYZED_FIRST_POSE79_WITH_REMAINING_GATES', 'sourceCheckpoint': 79, 'source_sha256': source_sha, 'apk_sha256': digest, 'qa_serial': installation['serial'], 'qa_target': target,
            'firstPoseValidation': validated, 'naturalRows': normal, 'controlledHoldRows': holds, 'startupPairs': pairs,
            'snapshotNative': native, 'observedExtremes': maxima, 'remainingGates': gates,
            'scope': 'Signed same-APK startup-only comparisons inside current79: Snapshot79 stays active in both synchronous78-startup and deferred79 branches. This does not restore the whole old78 application/model. Exact78-control native Snapshot isolation is separate. No moved stall is discarded and no timing direction is an acceptance threshold. Pure worker elapsed is not thread CPU; CPU/head/camera/physical-display boundaries are distinct. No fresh visual or reference approval is inferred.',
            'artifactSHA256': dict(sorted(artifacts.items())), 'externalEvidenceSHA256': dict(sorted(external.items())),
            'analyzerSHA256': sha(Path(__file__)), 'validatorSHA256': sha(ROOT / 'Verification/Tools/run_first_pose79_device.py'),
            'frameCostValidatorSHA256': sha(ROOT / 'Verification/Tools/run_execution78_device.py'), 'qaTargetValidatorSHA256': sha(ROOT / 'Verification/Tools/qa_android_target.py')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=DEFAULT)
    parser.add_argument('--out', type=Path, help='Explicit JSON output; omitted means read-only validation/summary')
    args = parser.parse_args()
    value = build(args.evidence)
    if args.out is not None:
        path = args.out.resolve()
        need(path.is_relative_to((ROOT / 'Verification/Evidence').resolve()), 'Unsafe analysis output')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': value['status'], 'source_sha256': value['source_sha256'], 'apk_sha256': value['apk_sha256'], 'naturalRows': len(value['naturalRows']), 'controlledHoldRows': len(value['controlledHoldRows']), 'startupPairs': len(value['startupPairs']), 'snapshotWorkloads': value['snapshotNative']['workloads'], 'snapshotPairs': value['snapshotNative']['pairs'], 'written': str(args.out) if args.out is not None else None}), flush=True)


if __name__ == '__main__':
    main()
