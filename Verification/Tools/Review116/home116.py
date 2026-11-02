"""Leave only the separately owned116 test app at ordinary Home.

Uses normal, guarded Skip intro/tutorial controls for this disposable package.
No profile/preference file is written by the harness; existing apps stay intact.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import time
import xml.etree.ElementTree as ET

import emulator116 as device
from upgrade116 import own_installation, installed_hash


def onboarding(target):
    path = 'shared_prefs/' + device.PACKAGE + '.v2.playerprefs.xml'
    raw = target.query('exec-out', 'run-as', device.PACKAGE, 'cat', path, binary=True)
    root = ET.fromstring(raw)
    values = {item.attrib.get('name'): item.attrib.get('value') for item in root if item.tag == 'int'}
    return dict(stage=int(values.get('HeartOfTheRain.FirstStart.v1.stage', '0')),
        complete=int(values.get('HeartOfTheRain.FirstStart.v1.complete', '0')))


def foreground_own(target):
    activity = target.query('shell', 'dumpsys', 'activity', 'activities')
    return any(device.PACKAGE + '/' in line for line in activity.splitlines() if 'topResumedActivity' in line)


def capture(target, public, name):
    raw = target.query('exec-out', 'screencap', '-p', binary=True)
    device.need(raw.startswith(b'\x89PNG\r\n\x1a\n'), 'ActualOwnOsPngRequired')
    width, height = struct.unpack('>II', raw[16:24])
    device.need(320 <= width < height <= 4096, 'OwnPortraitPlayerScreenshotRequired')
    path = public / name
    path.write_bytes(raw)
    return width, height


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--installation', type=Path, required=True)
    args = parser.parse_args()
    installed = own_installation(args.installation)
    device.require_launch_profile(installed)
    public, private = device.directories(args.name)
    target = device.Target(private)
    device.need(target.identity == installed['identity'] and installed_hash(target) == installed['apk']['sha256'],
        'ExactOwnedInstalledArtifactAndTargetRequired')
    before = target.snapshot()
    device.write(public / 'Before.json', before)
    device.need(all(row['idleProof']['idle'] for row in before['games'].values()), 'ExistingProfilesMustBeIdleBeforeOwnHome')
    own_before = target.files(device.PACKAGE)
    device.need(target.idle(device.PACKAGE, own_before)['idle'], 'OwnProfileMustBeIdleBeforeOrdinaryHome')
    device.need(not target.exists(device.BASE + '/' + device.MARKER), 'NoOwnPendingRegressionMarkerAllowed')
    launch = target.query('shell', 'am', 'start', '-W', '-n', device.ACTIVITY, timeout=120)
    device.need(re.search(r'(?m)^Status:\s*ok\s*$', launch), 'OwnOrdinaryLaunchFailed')
    time.sleep(8)
    steps = []
    for number in range(2):
        device.need(foreground_own(target), 'OnlyOwnForegroundMayReceiveInput')
        state = onboarding(target)
        width, height = capture(target, public, 'BeforeSkip' + str(number) + '_OS.png')
        if state['complete'] == 1:
            break
        device.need(0 <= state['stage'] <= 5 and state['complete'] == 0, 'KnownOwnOnboardingStateRequired')
        # Actual reviewed900x1600 Prologue places Skip at x≈790,y≈75.
        x, y = round(width * 0.875), round(height * 0.047)
        target.query('shell', 'input', 'tap', str(x), str(y))
        time.sleep(2)
        steps.append(dict(before=state, tap=[x, y], after=onboarding(target)))
    state = onboarding(target)
    device.need(state['complete'] == 1 and state['stage'] == 6, 'OwnNormalOnboardingMustCompleteViaControls')
    time.sleep(2)
    device.need(foreground_own(target), 'OwnFinalForegroundRequired')
    capture(target, public, 'Final_Home_OS.png')
    own_after = target.files(device.PACKAGE)
    profiles_before = {name: value for name, value in own_before['files'].items() if '/Profiles/' in name}
    profiles_after = {name: value for name, value in own_after['files'].items() if '/Profiles/' in name}
    after = target.snapshot(before)
    checks = device.compare_existing(before, after)
    device.write(public / 'After.json', after)
    result = dict(status='PASS_OWN116_ORDINARY_HOME' if checks['passExistingPackageAndGameData'] and profiles_before == profiles_after else 'FAIL_OWN116_FINAL_INVARIANT',
        utc=device.utc(), package=device.PACKAGE, apk=installed['apk'], installation=device.bind(args.installation),
        runner=device.bind(Path(__file__)), steps=steps, onboarding=state,
        ownProfileBytesUnchanged=profiles_before == profiles_after, ownPreferenceChange='Normal first-start Skip controls complete onboarding for the new disposable package only.',
        existingState=checks, foregroundOwn=True, visualReviewRequired=True,
        scope='Ordinary new116 app at Home after normal Skip intro/tutorial controls. Existing packages/settings/profile bytes are independently compared; no third-party foreground restoration or physical-phone operation.')
    device.write(public / 'Home.json', result)
    print(json.dumps(result), flush=True)
    device.need(result['status'].startswith('PASS_'), 'OwnHomeFinalInvariantFailed')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        print(json.dumps(dict(status='BLOCKED_OWN116_HOME', errorType=type(error).__name__,
            code=code if re.fullmatch('[A-Za-z0-9]{1,100}', code) else 'PrivateEvidenceRequired')), flush=True)
        raise SystemExit(1)
