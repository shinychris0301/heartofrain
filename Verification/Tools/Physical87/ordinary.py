"""Record deliberate ordinary-app touches on the explicitly authorized phone.

No fixture, profile edit, account secret export or implicit device selection.
One command per invocation lets the operator inspect each resulting screen.
Recorded dispatch is not an assertion that the intended UI action succeeded.
"""
import argparse
import json
from pathlib import Path
import re
import time
import xml.etree.ElementTree as ET

from phone import Phone, PACKAGE, utc, write, sha


def state(phone):
    result = {"utc": utc(), "savedFiles": phone.snapshot(), "profile": phone.profile_summary()}
    path = phone.base + '/Profiles/Development-v1/profile.json'
    if phone.exists(path):
        profile = json.loads(json.loads(phone.adb('exec-out', 'cat', path))['payload'])
        result['profile'].update({key: profile.get(key) for key in ('stars', 'starting', 'tools', 'giftClaims', 'lastGiftDay')})
        result['profile']['attempts'] = [{key: attempt.get(key) for key in
            ('state', 'level', 'firstClear', 'awardedCoins', 'awardedStars', 'livesAfter', 'selected')}
            for attempt in profile['attempts']]
        result['profile']['rewardCount'] = len(profile.get('rewards', []))
    result['savedSettings'] = {}
    for name in result['savedFiles']['preferences']:
        raw = phone.adb('exec-out', 'run-as', PACKAGE, 'cat', 'shared_prefs/' + name)
        for entry in ET.fromstring(raw):
            key = entry.get('name', '')
            if entry.tag == 'int' and re.fullmatch(r'HeartOfTheRain\.Settings\.v[12]\.(music|sound|hints|language|reduceMotion)', key):
                result['savedSettings'][key] = int(entry.get('value'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--label', required=True)
    parser.add_argument('action', choices=['capture', 'tap', 'swipe', 'state', 'background-resume', 'relaunch'])
    parser.add_argument('coordinates', nargs='*', type=int)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,85}', args.label):
        parser.error('Use a simple unique evidence label')
    phone = Phone(args.out)
    folder = phone.run_dir / 'Ordinary'
    folder.mkdir(exist_ok=True)
    record_path = folder / (args.label + '.json')
    if record_path.exists():
        parser.error('Evidence label already exists')
    record = {'utc': utc(), 'action': args.action, 'coordinates': args.coordinates,
              'toolSHA256': sha(__file__), 'before': state(phone),
              'scope': 'Ordinary app; ADB dispatch and observed saved state. Screenshot requires visual interpretation.'}
    write(record_path, record)
    assert phone.foreground(), 'Ordinary input only while our app is foreground'
    if args.action in ('tap', 'swipe'):
        size = phone.adb('shell', 'wm', 'size')
        width, height = map(int, re.findall(r'(\d+)x(\d+)', size)[-1])
        count = 2 if args.action == 'tap' else 5
        assert len(args.coordinates) == count
        coords = args.coordinates[:4] if count == 5 else args.coordinates
        assert all(0 <= value < (width if i % 2 == 0 else height) for i, value in enumerate(coords))
        if count == 5:
            assert 50 <= args.coordinates[4] <= 2000
        phone.adb('shell', 'input', 'touchscreen', args.action, *args.coordinates)
        time.sleep(2.5)
    elif args.action == 'background-resume':
        assert not args.coordinates
        phone.adb('shell', 'input', 'keyevent', '3')
        time.sleep(3)
        phone.launch()
        time.sleep(3)
    elif args.action == 'relaunch':
        assert not args.coordinates
        phone.assert_no_active_attempt()
        phone.finish_probe()
    else:
        assert not args.coordinates
    record['after'] = state(phone)
    if args.action != 'state':
        image = phone.capture('Ordinary/' + args.label + '.png')
        record['capture'] = {'path': image.relative_to(phone.run_dir).as_posix(), 'sha256': sha(image)}
    record['status'] = 'RECORDED_ORDINARY_ACTION_REQUIRES_INTERPRETATION'
    write(record_path, record)
    print(json.dumps({'record': record_path.relative_to(phone.run_dir).as_posix(),
                      'profile': record['after']['profile'], 'savedSettings': record['after']['savedSettings']}))


if __name__ == '__main__':
    main()
