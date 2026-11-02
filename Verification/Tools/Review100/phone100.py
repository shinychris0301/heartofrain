"""Bounded100 verification of the same separately signed physical candidate.

Only its own test package can be updated or receive input. Saves/preferences and
the original package state are read before/after; no clear/uninstall is offered.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Review98'))
import physical as old
PACKAGE, OWNER = old.PACKAGE, old.OWNER


class Phone(old.Physical):
    def __init__(self, out, build):
        self.out, self.private, self.counter = out, ROOT / '.verification-cache/Review100/Phone' / out.name, 0
        self.private.mkdir(parents=True, exist_ok=False)
        inventory = json.loads(old.INVENTORY.read_text('utf-8'))
        matches = [d for d in inventory['devices'] if d['state'] == 'device' and d['transport'] == 'physicalOrNetwork']
        if len(matches) != 1:
            raise ValueError('InventoriedPhysicalPhoneRequired100')
        self.device = matches[0]
        self.serial = (ROOT / inventory['privateEvidenceDirectory'] / 'selected_device.txt').read_text()
        if hashlib.sha256(self.serial.encode()).hexdigest() != self.device['selectorSHA256']:
            raise ValueError('PhoneSelectorChanged100')
        self.build = json.loads(build.read_text('utf-8-sig'))
        if (self.build.get('status') != 'PASS_NATIVE_REVIEW100_BUILDDEVELOPMENT' or self.build.get('unity') != '6000.3.27f1'
                or self.build.get('packageName') != PACKAGE or self.build.get('errors') or self.build.get('lz4hc') or self.build.get('scriptDebugging')):
            raise ValueError('ApprovedCompact100DevelopmentBuildRequired')
        self.apk, self.expected = Path(self.build['apk']), self.build['apkSHA256']
        if old.sha(self.apk) != self.expected:
            raise ValueError('Exact100ArtifactRequired')
        self.base = '/sdcard/Android/data/' + PACKAGE + '/files'
        self.identity()

    def push(self, name, content):
        if name != 'HOTR_RunReward100' or content != 'wellkeeper':
            raise ValueError('ExactMemoryReward100MarkerRequired')
        path = self.private / 'RewardMarker.txt'
        path.write_text(content, encoding='ascii')
        self.adb('push', str(path), self.base + '/' + name)

    def guard(self):
        policy = self.adb('shell', 'dumpsys', 'window', 'policy').split('KeyguardServiceDelegate', 1)[-1]
        if not re.search(r'(?m)^\s*showing=false\s*$', policy):
            raise ValueError('OwnerUnlockRequired100')
        if 'mWakefulness=Awake' not in self.adb('shell', 'dumpsys', 'power'):
            raise ValueError('OwnerAwakePhoneRequired100')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--previous-build', type=Path)
    parser.add_argument('action', choices=('upgrade', 'reward', 'details', 'relaunch'))
    args = parser.parse_args()
    if not args.execute or not re.fullmatch('[A-Za-z0-9_]{1,30}', args.tag):
        parser.error('Explicit short100 action required')
    out = ROOT / 'Verification/Evidence/Review100/Phone' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    result = dict(schemaVersion=1, status='RUNNING_PHYSICAL100', utc=old.utc(), action=args.action,
                  runner=old.bound(Path(__file__)), build=old.bound(args.build), captures=[], inputs=[],
                  scope='One authorized inventoried physical phone and SDK-free candidate. Reversible Shop preview or memory-only committed-reward fixture; no live purchase/provider, human campaign or performance certification.')
    phone, recorder = None, None
    try:
        phone = Phone(out, args.build)
        phone.guard()
        result['ownerBefore'] = phone.stable(OWNER)
        result['candidateBefore'] = phone.stable(PACKAGE) if args.action == 'upgrade' else phone.installed()
        if args.action == 'upgrade':
            if not args.previous_build:
                raise ValueError('ExactPreviousCandidateBuildRequired100')
            previous = json.loads(args.previous_build.read_text('utf-8-sig'))
            if (previous.get('packageName') != PACKAGE or previous.get('errors') or old.sha(previous['apk']) != previous['apkSHA256']
                    or result['candidateBefore']['installedSHA256'] != previous['apkSHA256'] or result['candidateBefore']['activeAttempts']):
                raise ValueError('PreservedIdlePreviousCandidateRequired100')
            android = Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer')
            certs = []
            for index, apk in enumerate((Path(previous['apk']), phone.apk)):
                completed = subprocess.run([str(android / 'OpenJDK/bin/java.exe'), '-jar', str(android / 'SDK/build-tools/36.0.0/lib/apksigner.jar'), 'verify', '--print-certs', str(apk)], capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
                (phone.private / ('Signer' + str(index) + '.out')).write_bytes(completed.stdout)
                found = re.findall(r'(?m)^Signer #1 certificate SHA-256 digest: ([0-9a-f]{64})\s*$', completed.stdout.decode('utf-8', 'replace'))
                if completed.returncode or len(found) != 1:
                    raise ValueError('CandidateSignerUnknown100')
                certs.append(found[0])
            if certs[0] != certs[1]:
                raise ValueError('CandidateSignerChanged100')
            phone.adb('shell', 'am', 'force-stop', PACKAGE)
            if phone.stable(PACKAGE) != result['candidateBefore']:
                raise ValueError('CandidateChangedBeforeUpgrade100')
            phone.adb('install', '-r', '-t', str(phone.apk), timeout=180)
            phone.installed()
            result.update(sameSigner=True, previousBuild=old.bound(args.previous_build), status='PASS_PHYSICAL100_PRESERVED_CANDIDATE_UPGRADE')
        elif args.action == 'reward':
            phone.stop()
            if phone.adb('shell', 'find', phone.base, '-maxdepth', '1', '-type', 'f', '-name', 'HOTR_Run*', check=False):
                raise ValueError('PendingCandidateMarkerPreserved100')
            phone.push('HOTR_RunReward100', 'wellkeeper')
            began = datetime.now(timezone.utc)
            phone.adb('shell', 'mkdir', '-p', phone.base + '/Review100')
            remote = phone.base + '/Review100/' + args.tag + '.mp4'
            with (phone.private / 'Screenrecord.out').open('xb') as stream:
                recorder = subprocess.Popen([str(old.old.ADB), '-s', phone.serial, 'shell', 'screenrecord', '--time-limit', '25', '--bit-rate', '4000000', remote], stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(1)
                phone.launch()
                deadline = time.monotonic() + 170
                while time.monotonic() < deadline:
                    raw = phone.adb('exec-out', 'cat', phone.base + '/Reward100Device/Report.json', binary=True, check=False)
                    try:
                        native = json.loads(raw)
                        fresh = datetime.fromisoformat(native['utc'].replace('Z', '+00:00')) >= began
                    except (ValueError, TypeError, KeyError):
                        fresh = False
                    if fresh and native.get('status', '').startswith(('PASS', 'FAIL')):
                        break
                    time.sleep(.1)
                else:
                    raise TimeoutError('NativeMemoryRewardDeadline100')
                recorder.wait(timeout=35)
            report = out / 'NativeReport.json'
            report.write_bytes(raw)
            video = phone.private / 'SharedReward.mp4'
            phone.adb('pull', remote, str(video), timeout=60)
            result.update(nativeReport=old.bound(report), privateVideo=old.bound(video))
            if (recorder.returncode or native.get('status') != 'PASS_NATIVE_REWARD100_MEMORY_PRESENTATION' or native.get('error')
                    or not native.get('isolatedMemory') or not native.get('modelCreditedBeforeReveal') or native.get('quantityLabels') != 9
                    or not native.get('journalReconstructed') or not native.get('journalDedupe') or not native.get('journalAcknowledged')
                    or native.get('completions') != 1 or native.get('profileHashBeforeReveal') != native.get('profileHashAfterReveal')):
                raise ValueError('ActualMemoryRewardPresentationFailed100')
            result['captures'].append(phone.capture('Memory_Reward_Final_OS'))
            result['status'] = 'PASS_PHYSICAL100_MEMORY_REWARD_REQUIRES_VISUAL_REVIEW'
        elif args.action == 'details':
            def tap(name, x, y):
                phone.adb('shell', 'input', 'tap', x, y)
                result['inputs'].append(dict(kind='tap', purpose=name, x=x, y=y))
                time.sleep(1)
            def back():
                phone.adb('shell', 'input', 'keyevent', '4')
                time.sleep(.8)
            tap('Ordinary SDK-free Shop navigation', 648, 1530)
            result['captures'].append(phone.capture('Shop_Preview_Top_OS'))
            tap('Wellkeeper preview details', 520, 911)
            result['captures'].append(phone.capture('Wellkeeper_Preview_Details_OS'))
            back()
            for _ in range(2):
                phone.adb('shell', 'input', 'swipe', 620, 800, 90, 800, 550)
                time.sleep(.8)
            tap('Rainlight preview details', 520, 911)
            result['captures'].append(phone.capture('Rainlight_Preview_Details_OS'))
            back()
            phone.adb('shell', 'input', 'swipe', 350, 1250, 350, 670, 650)
            time.sleep(1)
            result['captures'].append(phone.capture('Shop_Mega_Before_Details_OS'))
            tap('Village preview details', 520, 435)
            result['captures'].append(phone.capture('Village_Preview_Details_OS'))
            back()
            tap('Home after preview observations', 360, 1530)
            result['captures'].append(phone.capture('Home_After_Previews_OS'))
            result['status'] = 'RECORDED_PHYSICAL100_PREVIEW_DETAILS_REQUIRES_REVIEW'
        else:
            phone.stop()
            if phone.adb('shell', 'find', phone.base, '-maxdepth', '1', '-type', 'f', '-name', 'HOTR_Run*', check=False):
                raise ValueError('PendingCandidateMarkerPreserved100')
            phone.launch()
            time.sleep(15)
            result['captures'].append(phone.capture('Normal_Home_OS'))
            result['status'] = 'RECORDED_PHYSICAL100_NORMAL_RELAUNCH_REQUIRES_REVIEW'
        result['candidateAfter'] = phone.stable(PACKAGE)
        def data(value):
            return {k: v for k, v in value.items() if k != 'installedSHA256'} if args.action == 'upgrade' else value
        result['candidateDataPreserved'] = data(result['candidateBefore']) == data(result['candidateAfter'])
        if not result['candidateDataPreserved']:
            result['status'] = 'FAIL_PHYSICAL100_CANDIDATE_PRESERVATION'
    except Exception as error:
        result.update(status='STOPPED_PHYSICAL100', errorType=type(error).__name__)
        if re.fullmatch('[A-Za-z0-9_]{1,100}', str(error)):
            result['errorCategory'] = str(error)
    finally:
        if recorder and recorder.poll() is None:
            recorder.wait(timeout=40)
        if phone:
            try:
                result['ownerAfter'] = phone.stable(OWNER)
                result['ownerStatePreserved'] = result.get('ownerBefore') == result['ownerAfter']
                if not result['ownerStatePreserved']:
                    result['status'] = 'FAIL_PHYSICAL100_OWNER_STATE_CHANGED'
            except Exception as error:
                result['ownerReadbackErrorType'] = type(error).__name__
        result['finishedUtc'] = old.utc()
        old.save(out / 'Report.json', result)
    print(json.dumps(dict(status=result['status'], report=(out / 'Report.json').relative_to(ROOT).as_posix())))
    return 0 if result['status'].startswith(('PASS_', 'RECORDED_')) else 1


if __name__ == '__main__':
    raise SystemExit(main())
