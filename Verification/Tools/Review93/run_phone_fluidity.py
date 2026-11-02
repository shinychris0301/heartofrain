"""Root-only bounded current-phone diagnostics; recording is not smoothness approval.

The marker is audited separately here. Frozen Phone93's general allowlist is
unchanged. There are no device calls on import and no ADB observations during
the 255-second quiet window after launch (native timeout210 plus45 launch/flush).
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import time
import uuid

import phone
import phone_regression_proof as proof
import run_phone_regression as regression

ROOT, OUT = phone.ROOT, phone.EVIDENCE
PROBE = ROOT / 'Unity/Assets/HeartOfTheRain/Verification/FluidityDeviceProbe.cs'
PARSER = ROOT / 'Verification/Tools/Physical87/probes.py'
QUIET_SECONDS = 255
POST_QUIET_SECONDS = 90
MAX_REPORT_BYTES = 32 * 1024 * 1024
MARKER = 'HOTR_RunFluidity'


def parser():
    spec = importlib.util.spec_from_file_location('hotr93_shared_fluidity_metrics_only', PARSER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quiet_wait(seconds=QUIET_SECONDS):
    """Local clock/output only. Never invoke a phone/ADB method while waiting."""
    until, progress = time.monotonic() + seconds, time.monotonic() + 30
    while time.monotonic() < until:
        time.sleep(min(10, max(0, until - time.monotonic())))
        if time.monotonic() >= progress:
            print(json.dumps({'status': 'QUIET_NATIVE_WINDOW_NO_ADB_OBSERVATIONS', 'remainingSeconds': max(0, round(until - time.monotonic()))}), flush=True)
            progress = time.monotonic() + 30


def observe(report):
    shared = parser()
    shared.validate('Fluidity', report)
    summary = shared.measurements('Fluidity', report)
    phases = report['phases']
    samples = report['frameSamples']
    proof.need([row.get('name') for row in phases] == ['idle_including_hint_search', 'natural_first', 'natural_second', 'rocket', 'three_rocket_chain', 'orb_rocket', 'golden_bomb', 'victory_animation'], 'Fluidity93CandidatePhasesRequired')
    for row in phases:
        for field in ('p50Ms', 'p95Ms', 'worstMs', 'modelMs', 'acceptMs', 'commandMs', 'settleSeconds'):
            value = row.get(field)
            proof.need(type(value) in (int, float) and math.isfinite(value) and value >= 0, 'Fluidity93FinitePhaseMeasurementsRequired')
    for row in samples:
        proof.need(type(row.get('phase')) is int and 0 <= row['phase'] < len(phases)
                   and type(row.get('frame')) is int and row['frame'] >= 0
                   and all(type(row.get(field)) in (int, float) and math.isfinite(row[field]) and row[field] >= 0
                           for field in ('intervalMs', 'updateMs', 'renderMs', 'sampleMs')), 'Fluidity93FiniteFrameMeasurementsRequired')
    slow = [dict(row, phaseName=phases[row['phase']]['name']) for row in samples if row['intervalMs'] > 33.34]
    summary.update(status='RECORDED_DIAGNOSTICS_NOT_A_SMOOTHNESS_PASS', frameSampleCount=len(samples),
        allFramesOver33ms=slow, allFramesOver50msCount=sum(row['intervalMs'] > 50 for row in samples),
        worstRecordedIntervalMs=max(row['intervalMs'] for row in samples),
        worstRecordedCommandMs=max(row['commandMs'] for row in phases),
        commandSamples=[{key: row.get(key) for key in ('name', 'modelMs', 'acceptMs', 'commandMs', 'firstPresentationMs', 'settleSeconds')} for row in phases],
        limitations=['Every raw frame/slow sample remains in Measurement.json; this summary does not discard slower phases.',
                     'StepStarted firstPresentationMs is dispatch timing, not first visible frame, presentation latency or touch latency.',
                     'Native scope has historical emulator wording; this run is identified as the physical phone by its current sixth-link target and APK/build receipts.',
                     'Development instrumentation and platform scheduling affect measurements. No universal frame budget, comparison speedup or whole-game smoothness approval is inferred.'])
    return summary


def start(reader, folder):
    reader.assert_installed()
    before = reader.require_idle()
    proof.need(not reader.pending_markers(), 'PendingDevelopmentProbeRequestPreserved')
    reader.adb('shell', 'am', 'force-stop', phone.PACKAGE)
    proof.need(not reader.adb('shell', 'pidof', phone.PACKAGE, check=False), 'Fluidity93AppDidNotStop')
    after = reader.require_idle()
    proof.need(proof.ordinary(before, reader.target['candidateApkSHA256']) == proof.ordinary(after, reader.target['candidateApkSHA256']), 'Fluidity93OwnerDataChangedBeforeMarker')
    proof.need(not reader.pending_markers(), 'PendingDevelopmentProbeRequestPreserved')
    private = ROOT / '.verification-cache/Review93/FluidityMarkers' / folder.name / MARKER
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text('candidate', encoding='ascii')
    reader.adb('shell', 'mkdir', '-p', reader.base)
    reader.adb('push', private, reader.base + '/' + MARKER)
    began = datetime.now(timezone.utc)
    # If launch transport has an unknown outcome, still leave the potential
    # native measurement undisturbed before any failure diagnostics/relaunch.
    reader._fluidity93_quiet_until = time.monotonic() + QUIET_SECONDS
    launch = reader.launch()
    proof.need(re.search(r'(?m)^Status:\s*ok\s*$', launch), 'Fluidity93LaunchNotAccepted')
    return began, launch


def run(reader, source_path, builds):
    source_module = regression.load_source_module()
    frozen = source_module.freeze()
    build = regression.matching_build(builds, source_path, frozen, reader)
    reader.assert_installed()
    before = reader.require_idle()
    folder = reader.out / 'Fluidity' / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    regression.write(folder / 'Sources_before.json', frozen)
    regression.write(folder / 'OrdinaryBefore.json', before)
    record = {'schemaVersion': 1, 'checkpoint': 93, 'status': 'RUNNING', 'startedUtc': phone.utc(),
        'runner': phone.public_binding(Path(__file__)), 'phoneHelper': phone.public_binding(Path(phone.__file__)),
        'sharedMetricsParser': phone.public_binding(PARSER), 'sharedBuildReader': phone.public_binding(Path(regression.__file__)),
        'nativeProbeSource': phone.public_binding(PROBE), 'sourceManifest': phone.public_binding(folder / 'Sources_before.json'),
        'target': phone.public_binding(reader.out / 'Target.json'), 'apk': phone.public_binding(reader.apk), 'matchingBuild': build,
        'ordinaryBefore': phone.public_binding(folder / 'OrdinaryBefore.json'), 'quietWindowSeconds': QUIET_SECONDS,
        'nativeTimeoutSeconds': 210, 'postQuietPollSeconds': POST_QUIET_SECONDS,
        'scope': 'One current actual phone, candidate-only unaccelerated isolated native diagnostic fixture. All raw slow frames retained. No screenshot/video, graphics/log/memory/thermal or filesystem queries during the255-second quiet native window. Post-window report polling is separate. Recording is not a smoothness PASS, production benchmark, touch-latency measure or multi-device certification.'}
    regression.write(folder / 'Manifest.json', record)
    report = None
    try:
        began, launch = start(reader, folder)
        record.update(nativeLaunchUtc=began.isoformat(), launchResult=launch)
        regression.write(folder / 'Manifest.json', record)
        quiet_wait()
        record['quietWindowFinishedUtc'] = phone.utc()
        deadline = time.monotonic() + POST_QUIET_SECONDS
        remote = reader.base + '/Fluidity/Measurement.json'
        while time.monotonic() < deadline:
            stamp = reader.adb('shell', 'stat', '-c', '%s:%Y', remote, check=False)
            if re.fullmatch(r'\d+:\d+', stamp):
                size = int(stamp.split(':', 1)[0])
                proof.need(size <= MAX_REPORT_BYTES, 'Fluidity93ReportTooLarge')
                raw = reader.adb('exec-out', 'cat', remote, binary=True)
                proof.need(len(raw) <= MAX_REPORT_BYTES, 'Fluidity93ReportTooLarge')
                try:
                    candidate = json.loads(raw)
                    fresh = isinstance(candidate, dict) and proof.when(candidate.get('utc', '')) >= began
                except (ValueError, TypeError, AttributeError, RuntimeError):
                    candidate, fresh = {}, False
                if fresh:
                    report = candidate
                    (folder / 'Measurement.json').write_bytes(raw)
                    record.update(nativeStatus=report.get('status'), nativeErrors=report.get('errors'), nativeReport=phone.public_binding(folder / 'Measurement.json'))
                    if report.get('status') != 'RUNNING':
                        observations = observe(report)
                        regression.write(folder / 'Observations.json', observations)
                        record.update(status='RECORDED_PHYSICAL_FLUIDITY93_NOT_SMOOTHNESS_CERTIFIED', observations=phone.public_binding(folder / 'Observations.json'))
                        break
            time.sleep(10)
        else:
            raise TimeoutError('Fluidity93FreshCompletionDeadline')
    except Exception as error:
        record.update(status='FAIL_PHYSICAL_FLUIDITY93_RECORDING', failureType=type(error).__name__)
        if isinstance(error, (ValueError, RuntimeError, TimeoutError)):
            # Export only controlled categories, never a potentially sensitive transport command.
            record['failureCategory'] = str(error) if re.fullmatch(r'[A-Za-z0-9 _;,.:-]{1,200}', str(error)) else 'NativeOrBoundedHostValidationFailed'
    finally:
        remaining_quiet = getattr(reader, '_fluidity93_quiet_until', 0) - time.monotonic()
        if remaining_quiet > 0:
            quiet_wait(remaining_quiet)
            record['quietWindowFinishedUtc'] = phone.utc()
        try:
            # This happens strictly after the quiet window or after a launch failure.
            record['appLog'] = reader.app_log('Fluidity/' + folder.name + '/Player.log')
            if record['appLog'].get('selectedErrorCount', 0):
                record['status'] = 'FAIL_PHYSICAL_FLUIDITY93_RECORDING'
                record['selectedRuntimeErrorsRequireReview'] = True
        except Exception as error:
            record.update(status='FAIL_PHYSICAL_FLUIDITY93_RECORDING', logFailureType=type(error).__name__)
        try:
            after = reader.require_idle()
            regression.write(folder / 'OrdinaryAfter.json', after)
            record['ordinaryAfter'] = phone.public_binding(folder / 'OrdinaryAfter.json')
            record['ordinaryDataUnchanged'] = proof.ordinary(before, reader.target['candidateApkSHA256']) == proof.ordinary(after, reader.target['candidateApkSHA256'])
            proof.need(record['ordinaryDataUnchanged'], 'Fluidity93OwnerDataChangedNoMoreMutations')
            record['normalRelaunch'] = reader.finish_probe()
            final = reader.require_idle()
            regression.write(folder / 'OrdinaryAfterNormalRelaunch.json', final)
            record['ordinaryAfterNormalRelaunch'] = phone.public_binding(folder / 'OrdinaryAfterNormalRelaunch.json')
            record['ordinaryDataUnchangedAfterNormalRelaunch'] = proof.ordinary(before, reader.target['candidateApkSHA256']) == proof.ordinary(final, reader.target['candidateApkSHA256'])
            proof.need(record['ordinaryDataUnchangedAfterNormalRelaunch'], 'Fluidity93OwnerDataChangedAfterRelaunch')
            record['finalMarkers'] = reader.pending_markers()
            proof.need(not record['finalMarkers'], 'Fluidity93PendingProbeMarker')
        except Exception as error:
            record.update(status='BLOCKED_PHYSICAL_FLUIDITY93_PRESERVATION', preservationFailureType=type(error).__name__)
        after_source = source_module.freeze()
        regression.write(folder / 'Sources_after.json', after_source)
        record.update(inputsUnchanged=frozen == after_source, sourcesAfter=phone.public_binding(folder / 'Sources_after.json'), finishedUtc=phone.utc())
        if not record['inputsUnchanged']:
            record['status'] = 'FAIL_PHYSICAL_FLUIDITY93_RECORDING'
        regression.write(folder / 'Manifest.json', record)
    return folder, record


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--execute', action='store_true')
    cli.add_argument('--phone', type=Path, required=True)
    cli.add_argument('--sources', type=Path, required=True)
    cli.add_argument('--builds', type=Path, required=True)
    args = cli.parse_args()
    if not args.execute or os.name != 'nt':
        cli.error('Explicit root Windows device execution required')
    folder, record = run(phone.Phone(args.phone), args.sources, args.builds)
    print(json.dumps({'status': record['status'], 'manifest': (folder / 'Manifest.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if record['status'] == 'RECORDED_PHYSICAL_FLUIDITY93_NOT_SMOOTHNESS_CERTIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
