"""Actual taps in the opt-in disposable lives-only Android fixture.

Only the separate candidate receives markers/input. Ordinary save/preferences and
the observed absent owner package are read before/after; no clear/uninstall.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import time

from phone101 import Device101, ROOT, previous, PACKAGE, OWNER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('mode', choices=('full', 'partial', '899', '900'))
    args = parser.parse_args()
    if not args.execute or not re.fullmatch('[A-Za-z0-9_]{1,30}', args.tag):
        parser.error('Explicit disposable lives101 case required')
    out = ROOT / 'Verification/Evidence/Review101/Phone' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    source = Path(__file__)
    snapshot = ROOT / '.verification-cache/Review101/ToolSources' / (previous.sha(source) + '.py')
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if not snapshot.exists():
        shutil.copyfile(source, snapshot)
    if previous.sha(source) != previous.sha(snapshot):
        raise ValueError('ExactLivesToolArchiveRequired101')
    record = dict(schemaVersion=1, status='RUNNING_PHYSICAL_LIVES101', utc=previous.utc(), mode=args.mode,
                  runner=previous.bound(snapshot), build=previous.bound(args.build), captures=[], inputs=[],
                  scope='Actual physical taps and render observations in the explicitly opt-in disposable memory profile. Refill duplicate callbacks are synthetic; no owner balance mutation, real backend/provider, performance or whole-app acceptance.')
    phone = None
    try:
        phone = Device101(out, args.build)
        phone.guard()
        record['ownerBefore'] = phone.stable(OWNER)
        record['candidateBefore'] = phone.installed()
        phone.stop()
        pending = phone.adb('shell', 'find', phone.base, '-maxdepth', '1', '-type', 'f', '-name', 'HOTR_Run*', check=False)
        if phone.last_exit != 0 or pending:
            raise ValueError('CandidateMarkersMustBeKnownAbsent101')
        phone.adb('shell', 'test', '-e', phone.base + '/HOTR_Review98Step', check=False)
        if phone.last_exit != 1:
            raise ValueError('CandidateStepMustBeAbsent101')
        native_mode = 'lives_' + args.mode + '101'
        phone.push('HOTR_RunReview98', native_mode)
        began = datetime.now(timezone.utc)
        phone.launch()

        def wait(statuses):
            deadline = time.monotonic() + 100
            while time.monotonic() < deadline:
                raw = phone.adb('exec-out', 'cat', phone.base + '/Review98Device/Report.json', binary=True, check=False)
                try:
                    value = json.loads(raw)
                    fresh = datetime.fromisoformat(value['utc'].replace('Z', '+00:00')) >= began
                except (ValueError, KeyError, TypeError):
                    fresh = False
                if fresh and value.get('mode') == native_mode:
                    if value.get('status', '').startswith('FAIL'):
                        (out / 'NativeFailure.json').write_bytes(raw)
                        raise ValueError('NativeLivesFixtureFailed101')
                    if value.get('status') in statuses:
                        return value, raw
                time.sleep(.15)
            raise TimeoutError('ActualLivesReadyDeadline101')

        def tap(value, purpose):
            if not (0 <= value['x'] < value['width'] == 720 and 0 <= value['y'] < value['height'] == 1600):
                raise ValueError('NativeTapCoordinatesOutsideActualPhone101')
            phone.adb('shell', 'input', 'tap', value['x'], value['y'])
            record['inputs'].append(dict(purpose=purpose, x=value['x'], y=value['y']))

        ready, raw = wait({'READY_FOR_LIVES_TAP'})
        (out / 'HeaderReady.json').write_bytes(raw)
        record['captures'].append(phone.capture('Before_Header_Tap_OS'))
        tap(ready, 'Actual lives icon tap')
        value, raw = wait({'READY_FOR_LIVES_VERIFY', 'READY_FOR_DISABLED_REFILL_TAP', 'READY_FOR_REFILL_TAP'})
        (out / 'PanelReady.json').write_bytes(raw)
        record['captures'].append(phone.capture('Lives_Only_Panel_OS'))
        if args.mode in ('899', '900'):
            tap(value, 'Actual disabled refill tap' if args.mode == '899' else 'Actual900-coin refill tap')
        if args.mode != '900':
            # Publish only after transfer closes. The active probe must never
            # observe a partially opened adb-sync destination on emulated storage.
            local_step = phone.private / 'Completed_Verify.txt'
            local_step.write_bytes(b'verify')
            staging = phone.base + '/Review101/' + args.tag + '_verify.tmp'
            phone.adb('shell', 'mkdir', '-p', phone.base + '/Review101')
            phone.adb('push', str(local_step), staging)
            phone.adb('shell', 'mv', staging, phone.base + '/HOTR_Review98Step')
            record['verifyMarkerPublication'] = 'CompletedStagingFileAtomicRename'
        native, raw = wait({'PASS_NATIVE_LIVES101_FIXTURE'})
        path = out / 'NativeReport.json'
        path.write_bytes(raw)
        record['nativeReport'] = previous.bound(path)
        expected = {'full': (1250, 5), 'partial': (1250, 3), '899': (899, 0), '900': (0, 5)}[args.mode]
        if (native.get('error') or not native.get('livesOnly') or native.get('gameplayArtLoaded') or native.get('attempts')
                or (native.get('coins'), native.get('lives')) != expected or native.get('starting') != [5, 5, 3, 2]):
            raise ValueError('NativeLivesProjectionOrIsolationFailed101')
        record['captures'].append(phone.capture('Lives_Final_OS'))
        if phone.candidate_pid and re.fullmatch('[0-9]+', phone.candidate_pid):
            log = phone.private / 'AppWarningsErrors.log'
            log.write_bytes(phone.adb('logcat', '-d', '--pid=' + phone.candidate_pid, '-v', 'monotonic', 'Unity:W', 'UnityPlayer:W', 'AndroidRuntime:E', 'libc:F', '*:S', binary=True))
            record['privateAppWarningsErrors'] = previous.bound(log)
            record['candidatePid'] = int(phone.candidate_pid)
        record['candidateAfter'] = phone.stable(PACKAGE)
        record['candidateDataPreserved'] = record['candidateBefore'] == record['candidateAfter']
        record['status'] = 'PASS_PHYSICAL_LIVES101_REQUIRES_VISUAL_REVIEW' if record['candidateDataPreserved'] else 'FAIL_PHYSICAL_LIVES101_SAVE_CHANGED'
    except Exception as error:
        record.update(status='STOPPED_PHYSICAL_LIVES101', errorType=type(error).__name__)
        if re.fullmatch('[A-Za-z0-9_]{1,120}', str(error)):
            record['errorCategory'] = str(error)
    finally:
        if phone:
            try:
                record['ownerAfter'] = phone.stable(OWNER)
                record['ownerStatePreserved'] = record.get('ownerBefore') == record['ownerAfter']
                if not record['ownerStatePreserved']:
                    record['status'] = 'FAIL_PHYSICAL_LIVES101_OWNER_CHANGED'
            except Exception as error:
                record['ownerReadbackErrorType'] = type(error).__name__
        record['finishedUtc'] = previous.utc()
        previous.save(out / 'Report.json', record)
    print(json.dumps(dict(status=record['status'], report=(out / 'Report.json').relative_to(ROOT).as_posix())))
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
