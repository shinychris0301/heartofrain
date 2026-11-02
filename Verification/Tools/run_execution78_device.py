"""Run opt-in checkpoint78 execution controls on QA, preserving real saved data.

The importable validator is read-only. It accepts slower pairs and retains all
measurements; native and Android serialized model hashes are separate domains.
"""
import argparse
import hashlib
import json
import math
import re
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from qa_android_target import validate_qa_target

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Gameplay78/Execution'
ADB = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
APK = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
PKG = 'com.heartoftherain.verification'
BASE = f'/sdcard/Android/data/{PKG}/files'
FIXTURES = ('L4_match', 'L14_match', 'L31_match', 'L33_match',
            'L1_three_rocket_chain', 'L1_orb_rocket', 'L1_golden_bomb', 'L26_power7')
OUTER = ('outerSetupMs', 'outerSampleMs', 'outerBeginMs', 'outerDrawMs',
         'outerDisableMs', 'outerUploadMs', 'outerEndCollectionsMs',
         'outerBankEndMs', 'outerSelectionMs')
COST_TIMES = ('updateMs', 'renderMs', 'outerSpanMs', 'outerWrapperResidualMs',
              'sampleMs', 'bodySampleMs', 'effectsSampleMs', 'sortMs',
              'lookupMs', 'batchAddMs', 'batchUploadMs', 'spriteUpdateMs', 'bankEndMs')
COUNTERS = ('poolCreated', 'spriteCreated', 'draws', 'crateDraws', 'meshQuads',
            'meshes', 'geometryMisses', 'meshSlotsCreated')
FRAME_COUNTERS = ('spriteCreates', 'spriteEvictions', 'synchronousLoads',
                  'cachedSprites', 'cachedTextures', 'preparationBatches',
                  'preparationFrames', 'preparationCreates')
MONOTONIC_FRAME_COUNTERS = tuple(k for k in FRAME_COUNTERS
                                 if k not in ('cachedSprites', 'cachedTextures'))
WORK_COUNTS = ('snapshotCalls', 'copiedPieces', 'validationCalls', 'footprintCalls',
               'matchCalls', 'gravityCalls', 'verticalCalls', 'activationCalls',
               'planningCalls', 'legalQueryCalls')
WORK_TIMES = ('snapshotMs', 'validationMs', 'footprintMs', 'matchMs', 'gravityMs',
              'verticalMs', 'activationMs', 'planningMs', 'legalQueryMs')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def nonnegative(value):
    return number(value) and value >= 0


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def digest(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def validate_cost(value):
    """Check tagged Update/Render hierarchy, supported GC and wall brackets."""
    assert all(nonnegative(value[k]) for k in OUTER + COST_TIMES), 'Invalid CPU duration'
    assert abs(sum(value[k] for k in OUTER) - value['outerSpanMs']) < .001, 'Outer spans do not account for their disjoint sum'
    assert value['outerSpanMs'] <= value['renderMs'] + .15, 'Outer spans escaped Render'
    assert abs(value['renderMs'] - value['outerSpanMs'] - value['outerWrapperResidualMs']) < .001, 'Render wrapper accounting differs'
    assert sum(value[k] for k in ('bodySampleMs', 'effectsSampleMs', 'sortMs')) <= value['outerSampleMs'] + .15, 'Sampling spans escaped owner'
    assert sum(value[k] for k in ('lookupMs', 'batchAddMs', 'spriteUpdateMs')) <= value['outerDrawMs'] + .15, 'Per-draw spans escaped owner'
    assert value['batchUploadMs'] <= value['outerUploadMs'] + .15 and value['bankEndMs'] <= value['outerBankEndMs'] + .15, 'Upload/cache spans escaped owner'
    assert value['sampleMs'] <= value['outerSampleMs'] + value['outerBeginMs'] + .15 and value['renderMs'] <= value['updateMs'] + .15, 'Nested spans escaped Update/Render'
    walls = [value[k] for k in ('updateStartedWall', 'renderStartedWall', 'renderFinishedWall', 'updateFinishedWall')]
    assert all(nonnegative(v) for v in walls) and walls == sorted(walls), 'Cost wall chronology differs'
    assert integer(value['frame']) and integer(value['gcMaxGeneration']), 'Invalid frame or GC support'
    for gen in range(3):
        counts = [value['gc' + str(gen) + p] for p in ('BeforeUpdate', 'BeforeRender', 'AfterRender', 'AfterUpdate')]
        if gen > value['gcMaxGeneration']:
            assert counts == [-1] * 4, 'Unsupported GC generation has fabricated counts'
        else:
            assert all(integer(v) for v in counts) and counts == sorted(counts), 'Completed GC counts regress within Update'
    assert all(integer(value[k]) for k in COUNTERS), 'Invalid resource or draw counter'
    assert number(value['clock']) and number(value['age']), 'Invalid playback clock'
    assert value['crateDraws'] <= value['draws'] and value['meshQuads'] <= value['draws'], 'Impossible draw counts'
    assert isinstance(value['kind'], str) and value['kind'], 'Missing phase tag'
    return value


def validate_span(value, frequency):
    """GC counts bracket the timed call; they are not a collection duration."""
    assert integer(value['frame']) and integer(value['gcMax']), 'Invalid Span frame or GC support'
    assert integer(value['startedTicks']) and integer(value['finishedTicks']) and value['startedTicks'] <= value['finishedTicks'], 'Stopwatch ticks regress'
    assert all(nonnegative(value[k]) for k in ('startedWall', 'finishedWall', 'milliseconds')), 'Invalid Span time'
    assert value['startedWall'] <= value['finishedWall'], 'Span wall clock regresses'
    expected = (value['finishedTicks'] - value['startedTicks']) * 1000 / frequency
    assert abs(expected - value['milliseconds']) < .000001, 'Stopwatch conversion differs'
    # Wall reads sit immediately outside Stopwatch reads, but have distinct
    # native-call/clock precision. This is chronology, not a speed threshold.
    assert value['milliseconds'] <= (value['finishedWall'] - value['startedWall']) * 1000 + .15, 'Span ticks escaped their outer wall bracket'
    for gen in range(3):
        counts = [value['gc' + str(gen) + p] for p in ('Before', 'After')]
        if gen > value['gcMax']:
            assert counts == [-1, -1], 'Unsupported Span generation has fabricated counts'
        else:
            assert all(integer(v) for v in counts) and counts[0] <= counts[1], 'Span GC counts regress'
    return value


def ordered_spans(spans, frequency):
    last = None
    for value in spans:
        validate_span(value, frequency)
        if last:
            assert last['finishedTicks'] <= value['startedTicks'] and last['finishedWall'] <= value['startedWall'], 'Timed calls overlap or reorder'
            assert last['gcMax'] == value['gcMax'], 'GC support changes between paired calls'
            for gen in range(min(2, value['gcMax']) + 1):
                assert last['gc' + str(gen) + 'After'] <= value['gc' + str(gen) + 'Before'], 'GC counts regress between timed calls'
        last = value


def paired_summary(pairs, control, current):
    """Retain signed per-pair values, including slower current samples."""
    rows = [{'index': pair['index'], 'controlFirst': pair['controlFirst'],
             'controlMs': control(pair), 'currentMs': current(pair),
             'currentMinusControlMs': current(pair) - control(pair)} for pair in pairs]
    return {'pairs': rows,
            'controlMedianMs': statistics.median(r['controlMs'] for r in rows),
            'currentMedianMs': statistics.median(r['currentMs'] for r in rows),
            'slowerCurrentPairs': sum(r['currentMinusControlMs'] > 0 for r in rows)}


def validate_report(report, baseline_hashes=None):
    """Validate raw schema1 without I/O, device actions or speedup acceptance.

    Optional baseline_hashes: {(family, count): (turnHash, finalHash)} for the
    four *Android* checkpoint77 density outcomes. Other outcomes compare within
    their same-Android control/current pairs, never to native Editor JSON.
    """
    assert report['status'] == 'PASS_NATIVE_EXECUTION78' and integer(report['schema']) and report['schema'] == 1 and report['errors'] == [], 'Execution fixture failed or stale schema'
    assert report['platform'] == 'Android' and isinstance(report['graphics'], str) and report['graphics'], 'Wrong or missing device platform'
    assert report['isolatedProfile'] is True and report['launchCleared'] is True, 'Unisolated or launch-occluded fixture'
    assert report['targetFps'] == 60 and report['bufferCapacity'] == 8192 and report['pairsPerModel'] == report['pairsPerResource'] == 8, 'Control scope changed'
    assert integer(report['stopwatchFrequency']) and report['stopwatchFrequency'] > 0, 'Missing Stopwatch frequency'
    assert isinstance(report['scope'], str) and report['scope'], 'Missing experiment scope'
    utc = datetime.fromisoformat(report['utc'].replace('Z', '+00:00'))
    assert utc.tzinfo is not None, 'Report UTC lacks a timezone'
    assert [r['name'] for r in report['modelRows']] == list(FIXTURES), 'Model fixture order/scope changed'
    assert [r['name'] for r in report['resourceRows']] == list(FIXTURES), 'Resource fixture order/scope changed'
    assert len(report['naturalRows']) == 8 and len(report['frozenRows']) == 4, 'Natural or frozen scope incomplete'
    assert 0 < len(report['frames']) <= report['bufferCapacity'], 'Frame buffer empty or overflowed'
    frequency = report['stopwatchFrequency']
    last_wall = -1
    last_frame = -1
    offset = 0
    natural_hashes = {}
    natural_summary = []
    expected = [(fixture, repeat, (branch == 0) == (repeat % 2 == 0))
                for fixture in ('L1_golden_bomb', 'L1_orb_rocket')
                for repeat in (0, 1) for branch in (0, 1)]
    for index, (row, spec) in enumerate(zip(report['naturalRows'], expected)):
        fixture, repeat, old = spec
        assert (row['fixture'], row['repeat'], row['checkpoint77']) == spec and isinstance(row['checkpoint77'], bool), 'Natural AB/BA flags or ordering differ'
        assert row['name'] == f'{fixture}_{repeat}' + ('_control77' if old else '_current78'), 'Natural name does not identify its branch'
        assert all(integer(row[k]) for k in ('repeat', 'commandFrame', 'frameStart', 'frameCount')) and row['frameCount'] > 2, 'Natural frame metadata incomplete'
        assert all(digest(row[k]) for k in ('turnHash', 'finalHash')), 'Missing natural outcome hashes'
        outcome = (row['turnHash'], row['finalHash'])
        assert outcome == natural_hashes.setdefault(fixture, outcome), 'Natural same-platform outcome changed across branches/repeats'
        assert all(nonnegative(row[k]) for k in ('preparationSeconds', 'commandStartedWall', 'commandFinishedWall', 'modelMs', 'acceptMs', 'commandMs', 'settleSeconds')), 'Invalid natural command duration'
        assert last_wall <= row['commandStartedWall'] <= row['commandFinishedWall'], 'Natural commands overlap or reorder'
        assert abs((row['commandFinishedWall'] - row['commandStartedWall']) * 1000 - row['commandMs']) < .01, 'Command wall duration differs'
        assert row['modelMs'] + row['acceptMs'] <= row['commandMs'] + .15 and row['commandMs'] <= row['settleSeconds'] * 1000 + .15, 'Command components escaped their owner'
        command = row['enqueueCost']
        assert command['frame'] == row['commandFrame'] and integer(command['phases']) and command['phases'] > 0, 'Enqueue tag does not belong to command'
        parts = ('buildMs', 'resourcePlanMs', 'nextMs', 'dependenciesMs', 'prefetchMs')
        assert all(nonnegative(command[k]) for k in parts + ('totalMs',)), 'Invalid Enqueue timer'
        assert sum(command[k] for k in parts) <= command['totalMs'] + .15 and command['totalMs'] <= row['acceptMs'] + .15, 'Enqueue timers escaped their owner'
        assert row['frameStart'] == offset, 'Frame slices overlap or contain holes'
        frames = report['frames'][offset:offset + row['frameCount']]
        offset += row['frameCount']
        assert len(frames) == row['frameCount'] and all(f['row'] == index for f in frames), 'Natural frame ownership differs'
        assert frames[0]['frame'] == row['commandFrame'], 'Command-frame prior Render/tail was removed'
        previous = None
        for frame in frames:
            cost = validate_cost(frame['cost'])
            assert frame['frame'] == cost['frame'] > last_frame and integer(frame['row']), 'Frame IDs regress or disagree'
            last_frame = frame['frame']
            assert nonnegative(frame['absoluteWall']) and nonnegative(frame['intervalMs']) and cost['updateFinishedWall'] <= frame['absoluteWall'] + .001, 'LateUpdate snapshot predates Update'
            assert all(integer(frame[k]) for k in FRAME_COUNTERS) and isinstance(frame['preparationPending'], bool), 'Invalid preparation/resource counters'
            assert frame['preparationCreates'] <= frame['preparationFrames'], 'Preparation creates exceed visits'
            assert cost['lookupMs'] == cost['batchAddMs'] == cost['spriteUpdateMs'] == 0, 'Primary natural observer is not coarse'
            if previous:
                assert frame['frame'] == previous['frame'] + 1 and previous['absoluteWall'] <= frame['absoluteWall'], 'A primary natural frame was removed or reordered'
                assert all(previous[k] <= frame[k] for k in MONOTONIC_FRAME_COUNTERS), 'Natural cumulative counters regress'
                assert previous['cost']['gcMaxGeneration'] == cost['gcMaxGeneration'], 'GC support changed between frames'
                for gen in range(min(2, cost['gcMaxGeneration']) + 1):
                    assert previous['cost']['gc' + str(gen) + 'AfterUpdate'] <= cost['gc' + str(gen) + 'BeforeUpdate'], 'GC counts regress between Updates'
            else:
                assert cost['updateFinishedWall'] <= row['commandStartedWall'] + .001 and row['commandFinishedWall'] <= frame['absoluteWall'] + .001, 'Pre-command Update incorrectly owns command CPU'
            if frame['preparationBatches']:
                batch = frame['preparation']
                assert integer(batch['frame']) and batch['frame'] <= frame['frame'], 'Preparation has a future frame'
                assert integer(batch['frames']) and 0 < batch['frames'] <= 16 and integer(batch['spriteCreates']) and batch['spriteCreates'] <= batch['frames'], 'Invalid preparation batch counts'
                assert all(nonnegative(batch[k]) for k in ('startedWall', 'finishedWall', 'milliseconds')) and batch['startedWall'] <= batch['finishedWall'] <= frame['absoluteWall'] + .001, 'Preparation wall chronology differs'
            previous = frame
        end_wall = row['commandStartedWall'] + row['settleSeconds']
        assert frames[-1]['absoluteWall'] <= end_wall + .001 and frames[-1]['preparationPending'] is False, 'Natural frame slice exceeds settlement or preparation remains pending'
        assert any(f['cost']['kind'] == 'powerFall' for f in frames), 'Natural power-fall playback was not observed'
        last_wall = end_wall
        natural_summary.append({'name': row['name'], 'checkpoint77': old, 'modelMs': row['modelMs'],
                                'acceptMs': row['acceptMs'], 'commandMs': row['commandMs'],
                                'settleSeconds': row['settleSeconds'], 'frames': len(frames),
                                'maximumRenderMs': max(f['cost']['renderMs'] for f in frames),
                                'maximumIntervalMs': max(f['intervalMs'] for f in frames)})
    assert offset == len(report['frames']), 'Unowned extra natural frames'

    model_summary = []
    model_hashes = {}
    for row in report['modelRows']:
        assert len(row['pairs']) == 8, 'Model paired scope incomplete'
        outcomes = None
        previous_frame = None
        for index, pair in enumerate(row['pairs']):
            assert pair['index'] == index and integer(pair['index']) and pair['controlFirst'] is (index % 2 == 0), 'Model AB/BA ordering changed'
            first, second = ('control', 'current') if pair['controlFirst'] else ('current', 'control')
            spans = [pair[first], pair[second]]
            ordered_spans(spans, frequency)
            assert last_wall <= spans[0]['startedWall'], 'Model time precedes previous stage'
            assert spans[0]['frame'] == spans[1]['frame'] > last_frame, 'Model calls did not share one later Unity frame'
            if previous_frame is not None:
                assert spans[0]['frame'] == previous_frame + 1, 'A model pair was removed'
            previous_frame = last_frame = spans[0]['frame']
            last_wall = spans[-1]['finishedWall']
            hashes = []
            for kind in ('TurnHash', 'FinalHash', 'CheckpointHash', 'OrderHash'):
                a, b = pair['control' + kind], pair['current' + kind]
                assert digest(a) and a == b, 'Same-platform model outcome/order parity failed'
                hashes.append(a)
            outcomes = hashes if outcomes is None else outcomes
            assert hashes == outcomes, 'Model repeated deterministic outcome changed'
        model_hashes[row['name']] = outcomes
        if row['name'] in natural_hashes:
            assert tuple(outcomes[:2]) == natural_hashes[row['name']], 'Natural/pure same-platform fixture outcomes differ'
        for branch in ('controlStages', 'currentStages'):
            work = row[branch]
            assert all(integer(work[k]) for k in WORK_COUNTS) and all(nonnegative(work[k]) for k in WORK_TIMES), 'Invalid separate inclusive model diagnostic'
        model_summary.append({'name': row['name'], **paired_summary(row['pairs'], lambda p: p['control']['milliseconds'], lambda p: p['current']['milliseconds'])})

    resource_summary = []
    for row in report['resourceRows']:
        assert len(row['pairs']) == 8, 'Resource paired scope incomplete'
        assert all(digest(row[k]) for k in ('turnBeforeHash', 'turnAfterHash', 'queueBeforeHash', 'queueAfterHash')), 'Missing resource input signatures'
        assert row['turnBeforeHash'] == row['turnAfterHash'] and row['queueBeforeHash'] == row['queueAfterHash'], 'Resource planning mutated input'
        assert row['turnBeforeHash'] == model_hashes[row['name']][0], 'Resource/pure same-platform fixture outcomes differ'
        previous_frame = None
        outcome = None
        phases = None
        for index, pair in enumerate(row['pairs']):
            assert pair['index'] == index and integer(pair['index']) and pair['controlFirst'] is (index % 2 == 0), 'Resource AB/BA ordering changed'
            assert integer(pair['phases']) and pair['phases'] > 0, 'No resource phases traversed'
            phases = pair['phases'] if phases is None else phases
            assert pair['phases'] == phases, 'Resource phase count varies between pairs'
            first, second = ('control', 'current') if pair['controlFirst'] else ('current', 'control')
            spans = [pair[first + 'Initial'], pair[first + 'Traversal'], pair[second + 'Initial'], pair[second + 'Traversal']]
            ordered_spans(spans, frequency)
            assert last_wall <= spans[0]['startedWall'], 'Resource time precedes previous stage'
            assert len({s['frame'] for s in spans}) == 1 and spans[0]['frame'] > last_frame, 'Resource spans did not share one later Unity frame'
            if previous_frame is not None:
                assert spans[0]['frame'] == previous_frame + 1, 'A resource pair was removed'
            previous_frame = last_frame = spans[0]['frame']
            last_wall = spans[-1]['finishedWall']
            assert digest(pair['controlHash']) and pair['controlHash'] == pair['currentHash'], 'Ordered per-phase/whole resource path parity failed'
            outcome = pair['controlHash'] if outcome is None else outcome
            assert pair['controlHash'] == outcome, 'Repeated resource path enumeration changed'
        resource_summary.append({'name': row['name'], 'phases': phases,
                                 'initial': paired_summary(row['pairs'], lambda p: p['controlInitial']['milliseconds'], lambda p: p['currentInitial']['milliseconds']),
                                 'remainingPhaseTraversal': paired_summary(row['pairs'], lambda p: p['controlTraversal']['milliseconds'], lambda p: p['currentTraversal']['milliseconds']),
                                 'initialPlusTraversal': paired_summary(row['pairs'], lambda p: p['controlInitial']['milliseconds'] + p['controlTraversal']['milliseconds'], lambda p: p['currentInitial']['milliseconds'] + p['currentTraversal']['milliseconds'])})

    assert [(r['family'], r['count']) for r in report['frozenRows']] == [('crate', 1), ('crate', 45), ('stone', 1), ('stone', 45)], 'Frozen fixture order/scope changed'
    frozen_summary = []
    for row in report['frozenRows']:
        assert row['name'] == row['family'] + '_' + str(row['count']), 'Frozen row identity differs'
        assert all(digest(row[k]) for k in ('turnHash', 'finalHash', 'queueHash')), 'Missing frozen outcome signatures'
        if baseline_hashes is not None:
            assert (row['turnHash'], row['finalHash']) == tuple(baseline_hashes[(row['family'], row['count'])]), 'Android frozen outcome differs from sealed Android77'
        assert row['resourcesReady'] is True and row['preparationPending'] is False, 'Frozen resources were not ready'
        assert number(row['age']) and abs(row['age'] - 2.5761446952819824) < .000001 and number(row['clock']) and nonnegative(row['phaseDuration']) and row['phaseDuration'] >= row['age'] and integer(row['phaseIndex']), 'Frozen pose or phase changed'
        for suffix in ('DrawHash', 'MeshHash'):
            hashes = [row[p + suffix] for p in ('beforeControl', 'beforeCurrent', 'afterControl', 'afterCurrent')]
            assert all(digest(h) for h in hashes) and len(set(hashes)) == 1, 'Frozen same-pose draw/upload/binding parity failed'
        assert len(row['pairs']) == 8, 'Frozen paired scope incomplete'
        previous_frame = None
        for index, pair in enumerate(row['pairs']):
            assert pair['index'] == index and integer(pair['index']) and pair['controlFirst'] is (index % 2 == 0), 'Frozen AB/BA ordering changed'
            first, second = ('control', 'current') if pair['controlFirst'] else ('current', 'control')
            spans = [pair[first], pair[second]]
            ordered_spans(spans, frequency)
            assert last_wall <= spans[0]['startedWall'], 'Frozen time precedes previous stage'
            assert spans[0]['frame'] == spans[1]['frame'] > last_frame, 'Frozen calls did not share one later Unity frame'
            if previous_frame is not None:
                assert spans[0]['frame'] == previous_frame + 1, 'A frozen pair was removed'
            previous_frame = last_frame = spans[0]['frame']
            last_wall = spans[-1]['finishedWall']
            for branch in ('control', 'current'):
                timing = pair[branch]
                value = validate_cost(pair[branch + 'Cost'])
                assert value['frame'] == timing['frame'] and timing['startedWall'] <= value['updateStartedWall'] <= value['updateFinishedWall'] <= timing['finishedWall'] + .001, 'Frozen timer does not enclose its real Update'
                assert value['kind'] == 'powerFall' and abs(value['age'] - row['age']) < .00001 and abs(value['clock'] - row['clock']) < .00001, 'Frozen pose advanced'
                assert value['poolCreated'] == value['spriteCreated'] == value['geometryMisses'] == value['meshSlotsCreated'] == 0, 'Frozen branch is not warmed'
                assert value['lookupMs'] == value['batchAddMs'] == value['spriteUpdateMs'] == 0, 'Frozen observer is not coarse'
                assert value['gcMaxGeneration'] == timing['gcMax'], 'Span and Update GC support differ'
                for gen in range(min(2, timing['gcMax']) + 1):
                    assert timing['gc' + str(gen) + 'Before'] <= value['gc' + str(gen) + 'BeforeUpdate'] <= value['gc' + str(gen) + 'AfterUpdate'] <= timing['gc' + str(gen) + 'After'], 'Frozen GC counters escaped their enclosing call'
            assert all(pair['controlCost'][k] == pair['currentCost'][k] for k in ('draws', 'crateDraws', 'meshQuads', 'meshes')), 'Frozen geometry counts changed'
        frozen_summary.append({'name': row['name'], **paired_summary(row['pairs'], lambda p: p['controlCost']['renderMs'], lambda p: p['currentCost']['renderMs'])})
    return {'status': 'VALIDATED_EXECUTION78_RAW_CONTROLS',
            'natural_turns': 8, 'natural_frames': len(report['frames']),
            'model_fixtures': 8, 'model_pairs': 64, 'resource_fixtures': 8,
            'resource_pairs': 64, 'frozen_fixtures': 4, 'frozen_pairs': 32,
            'timed_render_calls': 64, 'frozen_android77_baseline_checked': baseline_hashes is not None,
            'natural': natural_summary, 'model': model_summary, 'resource': resource_summary,
            'frozenRender': frozen_summary,
            'scope': 'Same-APK same-platform controls; every signed/slower pair retained. Resource Initial+Traversal includes construction and identity guards, excludes Ready, loading and callbacks. Inclusive model stage diagnostics are separate from primary model timing. Natural command-frame prior Render is distinct from command tail. Frozen payload/binding hashes are captured outside timing. GC counts bracket completed collections, not GC duration. No exclusive stall-cause, cache-flush, sustained-frame-rate, physical-device, universal speedup or hitch-free claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    qa_target = validate_qa_target(args.serial, args.out)
    folder = args.out.resolve()
    assert folder.is_relative_to((ROOT / 'Verification/Evidence').resolve())
    folder.mkdir(parents=True, exist_ok=True)

    def adb(*cmd, check=True):
        return subprocess.run([str(ADB), '-s', args.serial, *map(str, cmd)], capture_output=True, check=check, timeout=180).stdout

    def state():
        names = adb('shell', 'run-as', PKG, 'ls', 'shared_prefs').decode().split()
        prefs = {n: adb('shell', 'run-as', PKG, 'sha256sum', 'shared_prefs/' + n).decode().split()[0]
                 for n in names if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', n)}
        names = adb('shell', 'find', BASE + '/Profiles', '-type', 'f', '-name', '*.json').decode().splitlines()
        saves = {n.removeprefix(BASE + '/'): adb('shell', 'sha256sum', n).decode().split()[0]
                 for n in names if re.fullmatch(re.escape(BASE) + r'/Profiles/[A-Za-z0-9_./-]+\.json', n)}
        return {'preferences': prefs, 'saves': saves}

    assert adb('get-state').strip() == b'device'
    profile = json.loads(json.loads(adb('shell', 'cat', BASE + '/Profiles/Development-v1/profile.json'))['payload'])
    assert not any(a['state'] in ['Reserved', 'Started'] for a in profile['attempts']), 'Preserve an active QA attempt'
    adb('shell', 'am', 'force-stop', PKG)
    before = state()
    started = datetime.now(timezone.utc).isoformat()
    result = {'utc': started, 'serial': args.serial, 'qa_target': qa_target, 'apk_sha256': sha(APK), 'before': before,
              'scope': 'Opt-in memory profile and isolated fixture boards, no real attempt/progression callbacks or screen taps. Real saves/preferences are hash-audited; no reset or physical-device claim.'}
    error = None
    try:
        if args.install:
            result['install'] = adb('install', '-r', APK).decode().strip()
            assert 'Success' in result['install'] and state() == before, 'Install failed or changed real saves'
        remote = adb('shell', 'pm', 'path', PKG).decode().splitlines()[0].removeprefix('package:').strip()
        result['installed_apk_sha256'] = adb('shell', 'sha256sum', remote).decode().split()[0]
        assert result['installed_apk_sha256'] == result['apk_sha256'], 'Wrong QA APK installed'
        request = ROOT / '.verification-cache/Gameplay78/ExecutionRequest'
        request.parent.mkdir(parents=True, exist_ok=True)
        request.write_text('all', encoding='ascii')
        adb('shell', 'mkdir', '-p', BASE)
        adb('shell', 'rm', '-f', BASE + '/Execution78/Report.json')
        adb('push', request, BASE + '/HOTR_RunExecution78')
        result['launch'] = adb('shell', 'am', 'start', '-W', '-n', PKG + '/com.unity3d.player.UnityPlayerActivity').decode().strip()
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            raw = adb('shell', 'cat', BASE + '/Execution78/Report.json', check=False)
            try:
                report = json.loads(raw)
            except (ValueError, UnicodeError):
                time.sleep(3)
                continue
            if report['status'] != 'RUNNING':
                break
            time.sleep(3)
        else:
            raise TimeoutError('Execution78 report unavailable; preserve logs and installed data')
        (folder / 'Report.json').write_bytes(raw)
        assert datetime.fromisoformat(report['utc'].replace('Z', '+00:00')) >= datetime.fromisoformat(started), 'Stale execution report'
        pid = adb('shell', 'pidof', PKG).decode().strip()
        assert re.fullmatch(r'[0-9]+', pid), 'Missing or ambiguous QA process'
        result['pid'] = pid
        logs = adb('logcat', '-d', '--pid=' + pid, '-v', 'brief').decode(errors='replace')
        (folder / 'Runtime.log').write_text(logs, encoding='utf-8')
        result['runtime_errors'] = len(re.findall(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException', logs))
        assert result['runtime_errors'] == 0, 'Native runtime error'
        # Only this transport layer reads the already-published Android77
        # density baseline. The importable validator itself performs no I/O.
        old_path = ROOT / 'Verification/Evidence/Gameplay77/PowerFall/Report.json'
        old_summary = json.loads((ROOT / 'Verification/Evidence/Gameplay77/Summary.json').read_text('utf-8-sig'))
        result['baseline_android77_report_sha256'] = sha(old_path)
        assert result['baseline_android77_report_sha256'] == old_summary['evidence_sha256']['PowerFall/Report.json'], 'Android77 density baseline is changed or unsealed'
        old = json.loads(old_path.read_text('utf-8-sig'))
        assert old['status'] == 'PASS_NATIVE_POWER_FALL77' and len(old['frozenRows']) == 4, 'Wrong Android77 baseline'
        baseline_hashes = {(r['family'], r['count']): (r['turnHash'], r['finalHash']) for r in old['frozenRows']}
        result['validated'] = validate_report(report, baseline_hashes)
    except Exception as exc:
        error = exc
        result['error'] = str(exc)
    finally:
        result['after'] = state()
        result['data_unchanged'] = result['after'] == before
        result['finishedUtc'] = datetime.now(timezone.utc).isoformat()
        result['status'] = 'PASS_EXECUTION78_DEVICE_AUDIT' if error is None and result['data_unchanged'] else 'FAIL_EXECUTION78_DEVICE_AUDIT'
        (folder / 'Installation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    assert result['data_unchanged'], 'Execution78 fixture changed real saved data'
    if error is not None:
        raise error
    print(json.dumps({k: result[k] for k in ('status', 'apk_sha256', 'data_unchanged', 'validated')}), flush=True)


if __name__ == '__main__':
    main()
