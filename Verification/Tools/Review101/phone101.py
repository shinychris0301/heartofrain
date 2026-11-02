"""Bounded startup observations of the approved separate Android test package.

No installation/clearing, security changes, artificial loading duration or engine
promotion. Cold means force-stopped process; hot is same-process Home/resume.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Review98'))
import physical as previous
PACKAGE, OWNER = previous.PACKAGE, previous.OWNER


class Device101(previous.Physical):
    def __init__(self, out, build):
        self.out, self.private, self.counter = out, ROOT / '.verification-cache/Review101/Phone' / out.name, 0
        self.private.mkdir(parents=True, exist_ok=False)
        inventory = json.loads(previous.INVENTORY.read_text('utf-8'))
        devices = [d for d in inventory['devices'] if d['state'] == 'device' and d['transport'] == 'physicalOrNetwork']
        if len(devices) != 1:
            raise ValueError('SingleInventoriedPhysicalPhoneRequired101')
        self.device = devices[0]
        self.serial = (ROOT / inventory['privateEvidenceDirectory'] / 'selected_device.txt').read_text()
        if hashlib.sha256(self.serial.encode()).hexdigest() != self.device['selectorSHA256']:
            raise ValueError('InventoriedSelectorChanged101')
        self.build = json.loads(build.read_text('utf-8-sig'))
        if (self.build.get('status') not in ('PASS_NATIVE_REVIEW100_BUILDDEVELOPMENT', 'PASS_NATIVE_REVIEW101_BUILDDEVELOPMENT')
                or self.build.get('unity') != '6000.3.27f1' or self.build.get('packageName') != PACKAGE
                or self.build.get('errors') or self.build.get('scriptDebugging') or self.build.get('lz4hc')):
            raise ValueError('ApprovedCompactDevelopmentArtifactRequired101')
        self.apk, self.expected = Path(self.build['apk']), self.build['apkSHA256']
        if previous.sha(self.apk) != self.expected:
            raise ValueError('ExactCandidateArtifactRequired101')
        self.base = '/sdcard/Android/data/' + PACKAGE + '/files'
        self.identity()
        if self.adb('shell', 'am', 'get-current-user') != '0':
            raise ValueError('UnexpectedPhoneUser101')

    def guard(self):
        policy = self.adb('shell', 'dumpsys', 'window', 'policy').split('KeyguardServiceDelegate', 1)[-1]
        if not re.search(r'(?m)^\s*showing=false\s*$', policy):
            raise ValueError('OwnerUnlockRequired101')
        if 'mWakefulness=Awake' not in self.adb('shell', 'dumpsys', 'power'):
            raise ValueError('OwnerAwakePhoneRequired101')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('action', choices=('cold', 'hot'))
    args = parser.parse_args()
    if not args.execute or not re.fullmatch('[A-Za-z0-9_]{1,30}', args.tag):
        parser.error('Explicit bounded startup observation required')
    out = ROOT / 'Verification/Evidence/Review101/Phone' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    source = Path(__file__)
    snapshot = ROOT / '.verification-cache/Review101/ToolSources' / (previous.sha(source) + '.py')
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if not snapshot.exists():
        shutil.copyfile(source, snapshot)
    if previous.sha(source) != previous.sha(snapshot):
        raise ValueError('ExactObservationToolArchiveRequired101')
    record = dict(schemaVersion=1, status='RUNNING_PHYSICAL_STARTUP101', action=args.action, utc=previous.utc(),
                  runner=previous.bound(snapshot), runnerOriginalPath=source.relative_to(ROOT).as_posix(), build=previous.bound(args.build), captures=[],
                  scope='One inventoried physical phone; same idle separate candidate and ordinary saved routing. Cold is process force-stop; hot is same-process Home/resume, not Activity-recreated warm launch. Exact decoder PTS and parent visual review are separate. No cache eviction, fake duration, provider or global performance acceptance.')
    phone = recorder = logger = logstream = None
    try:
        phone = Device101(out, args.build)
        phone.guard()
        record['selectorSHA256'] = phone.device['selectorSHA256']
        record['ownerBefore'] = phone.stable(OWNER)
        record['candidateBefore'] = phone.installed()
        marker = phone.adb('shell', 'find', phone.base, '-maxdepth', '1', '-type', 'f', '-name', 'HOTR_Run*', check=False)
        if phone.last_exit != 0 or marker:
            raise ValueError('CandidateMarkersMustBeKnownAndAbsent101')
        if args.action == 'cold':
            phone.stop()
            phone.adb('shell', 'input', 'keyevent', '3')
            time.sleep(1)
        else:
            prior_pid = phone.adb('shell', 'pidof', PACKAGE, check=False)
            if not re.fullmatch('[0-9]+', prior_pid):
                raise ValueError('ExistingProcessRequiredForWarm101')
            record['priorCandidatePid'] = int(prior_pid)
            phone.adb('shell', 'input', 'keyevent', '3')
            time.sleep(.5)
        phone.adb('shell', 'mkdir', '-p', phone.base + '/Review101')
        remote = phone.base + '/Review101/' + args.tag + '.mp4'
        logstream = (phone.private / 'Startup_Logcat.txt').open('xb')
        logger = subprocess.Popen([str(previous.old.ADB), '-s', phone.serial, 'logcat', '-T', '1', '-v', 'monotonic',
                                   'Unity:I', 'UnityPlayer:I', 'HOTR99:I', 'ActivityTaskManager:I', 'AndroidRuntime:E', 'libc:F', '*:S'],
                                  stdout=logstream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        with (phone.private / 'Screenrecord.out').open('xb') as stream:
            recorder = subprocess.Popen([str(previous.old.ADB), '-s', phone.serial, 'shell', 'screenrecord', '--time-limit', '25',
                                         '--bit-rate', '4000000', remote], stdout=stream, stderr=subprocess.STDOUT,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
            # Recorder-only pre-roll: allow the virtual display to begin before
            # requesting launch; this never changes app loading duration.
            time.sleep(3)
            record['phoneUptimeBeforeRequest'] = phone.adb('shell', 'cat', '/proc/uptime').split()[0]
            record['launchRequestedUtc'] = previous.utc()
            began = time.monotonic()
            result = phone.launch()
            record['amStartWallSeconds'] = time.monotonic() - began
            record['amStartTimingFields'] = [x for x in result.splitlines() if re.match(r'^(LaunchState|ThisTime|TotalTime|WaitTime):', x)]
            record['candidatePidAfterRequest'] = int(phone.candidate_pid) if phone.candidate_pid else None
            record['reportedLaunchState'] = next((x.split(':', 1)[1].strip() for x in record['amStartTimingFields'] if x.startswith('LaunchState:')), None)
            if args.action == 'hot' and (record['candidatePidAfterRequest'] != record['priorCandidatePid'] or record['reportedLaunchState'] != 'HOT'):
                raise ValueError('HotProcessOrLaunchStateChanged101')
            print(json.dumps(dict(status='RECORDING_STARTUP101', tag=args.tag, action=args.action)), flush=True)
            recorder.wait(timeout=40)
        if recorder.returncode:
            raise ValueError('ActualScreenRecordingFailed101')
        video = phone.private / 'Startup.mp4'
        phone.adb('pull', remote, str(video), timeout=60)
        record['video'] = previous.bound(video)
        route_ready = True
        if args.action == 'cold':
            text = (phone.private / 'Startup_Logcat.txt').read_text('utf-8', errors='replace')
            route_ready = bool(re.search(r'^\s*\d+\.\d+\s+' + str(record['candidatePidAfterRequest']) + r'\s+\d+\s+I\s+Unity\s*:\s*HOTR_STARTUP99 stage=route_home\b', text, re.MULTILINE))
            record['managedHomeRouteObserved'] = route_ready
        record['captures'].append(phone.capture('Startup_End_OS'))
        record['candidateAfter'] = phone.stable(PACKAGE)
        record['candidateDataPreserved'] = record['candidateBefore'] == record['candidateAfter']
        record['status'] = ('RECORDED_PHYSICAL_STARTUP101_REQUIRES_REVIEW' if route_ready else 'FAIL_PHYSICAL_STARTUP101_READY_STAGE_ABSENT') if record['candidateDataPreserved'] else 'FAIL_PHYSICAL_STARTUP101_SAVE_CHANGED'
    except Exception as error:
        record.update(status='STOPPED_PHYSICAL_STARTUP101', errorType=type(error).__name__)
        if re.fullmatch('[A-Za-z0-9_]{1,120}', str(error)):
            record['errorCategory'] = str(error)
    finally:
        if logger:
            logger.terminate()
            try:
                logger.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.kill()
                logger.wait(timeout=10)
        if logstream:
            logstream.close()
            record['privateStartupLog'] = previous.bound(phone.private / 'Startup_Logcat.txt')
        if recorder and recorder.poll() is None:
            recorder.wait(timeout=40)
        if phone:
            try:
                record['ownerAfter'] = phone.stable(OWNER)
                record['ownerStatePreserved'] = record.get('ownerBefore') == record['ownerAfter']
                if not record['ownerStatePreserved']:
                    record['status'] = 'FAIL_PHYSICAL_STARTUP101_OWNER_STATE_CHANGED'
            except Exception as error:
                record['ownerReadbackErrorType'] = type(error).__name__
        record['finishedUtc'] = previous.utc()
        previous.save(out / 'Report.json', record)
    print(json.dumps(dict(status=record['status'], report=(out / 'Report.json').relative_to(ROOT).as_posix())), flush=True)
    return 0 if record['status'].startswith('RECORDED_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
