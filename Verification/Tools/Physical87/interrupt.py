"""Test the approved interruption rule on this run's newly started test attempt.

Requires the exact ordinary Play evidence hash. Never accepts an existing owner
attempt, a configured backend, a continuation purchase or a stale profile.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from phone import Phone, PACKAGE, utc, write, sha
from ordinary import state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--started-record', required=True)
    args = parser.parse_args()
    phone = Phone(args.out)
    assert phone.target['packageAbsentBefore'] and phone.target['persistentDirectoryAbsentBefore']
    path = (phone.run_dir / 'Ordinary' / args.started_record).resolve()
    assert path.is_relative_to((phone.run_dir / 'Ordinary').resolve()) and path.suffix == '.json'
    entry = json.loads(path.read_text('utf-8'))
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(entry['utc'])).total_seconds()
    assert 0 <= age <= 1200, 'Use the freshly recorded test Play only'
    before = entry['before']['profile']; started = entry['after']['profile']
    assert not any(a in ('Reserved', 'Started') for a in before['attemptStates'])
    assert len(started['attemptStates']) == len(before['attemptStates']) + 1
    assert started['attemptStates'][-1] == 'Started' and started['attemptStates'].count('Started') == 1
    assert not phone.exists(phone.base + '/ServerReview/configuration.json')
    assert phone.foreground() and phone.snapshot() == entry['after']['savedFiles']
    raw = json.loads(json.loads(phone.adb('exec-out', 'cat', phone.base + '/Profiles/Development-v1/profile.json'))['payload'])
    attempt = raw['attempts'][-1]
    assert attempt['state'] == 'Started'
    journal = attempt.get('continuation') or {}
    assert not journal.get('pending') and not journal.get('count', 0), 'Never terminate a Continue/purchase test as an ordinary interruption'
    assert not journal.get('phase') and not journal.get('checkpoint'), 'Preserve an awaiting Continue/Shop board even before its first purchase'
    folder = phone.run_dir / 'Interruption'
    folder.mkdir(exist_ok=False)
    record = {'utc': utc(), 'status': 'RUNNING', 'playRecord': path.relative_to(phone.run_dir).as_posix(),
              'playRecordSHA256': sha(path), 'runnerSHA256': sha(__file__), 'before': state(phone),
              'scope': 'Deliberate force-stop of this fresh physical test session ordinary Started attempt, followed by two normal launches; not OS power loss or Continue/Shop recovery.'}
    write(folder / 'Invocation.json', record)
    try:
        phone.adb('shell', 'am', 'force-stop', PACKAGE)
        assert not phone.adb('shell', 'pidof', PACKAGE, check=False)
        phone.launch()
        time.sleep(7)
        record['afterRecovery'] = state(phone)
        result = record['afterRecovery']['profile']
        assert result['attemptStates'] == started['attemptStates'][:-1] + ['Interrupted']
        assert result['lives'] == started['lives'] - 1
        for key in ('coins', 'stars', 'completed', 'currentLevel', 'starting', 'tools', 'giftClaims', 'rewardCount'):
            assert result[key] == started[key], 'Interruption changed an unrelated balance/record'
        phone.assert_no_active_attempt()
        capture = phone.capture('Interruption/Recovered_Home.png')
        record['capture'] = {'path': capture.relative_to(phone.run_dir).as_posix(), 'sha256': sha(capture)}
        phone.finish_probe()
        record['afterSecondRelaunch'] = state(phone)
        assert record['afterSecondRelaunch']['savedFiles'] == record['afterRecovery']['savedFiles']
        record['appLog'] = phone.app_log('Interruption/Runtime.log')
        assert not record['appLog']['selectedErrorCount']
        record['status'] = 'PASS_FRESH_TEST_ATTEMPT_INTERRUPTED_LOSS_ONCE'
    except Exception as error:
        record.update(status='FAIL_INTERRUPTION_CHECK', failureType=type(error).__name__)
    record['finishedUtc'] = utc()
    write(folder / 'Invocation.json', record)
    print(json.dumps({'status': record['status'], 'profile': record.get('afterSecondRelaunch', record.get('afterRecovery', {})).get('profile')}))
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
