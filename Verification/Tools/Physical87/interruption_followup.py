"""Observe late recovery after the retained early checkpoint87 observation.

Never repeats an interruption or edits the initial failed report. A second
launch is permitted only after the already interrupted test attempt settles.
"""
import argparse
import json
from pathlib import Path
import time
from phone import Phone, PACKAGE, utc, write, sha
from ordinary import state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    phone = Phone(args.out)
    folder = phone.run_dir / 'Interruption'
    original = folder / 'Invocation.json'
    initial = json.loads(original.read_text('utf-8'))
    assert initial['status'] == 'FAIL_INTERRUPTION_CHECK'
    path = folder / 'Followup.json'
    assert not path.exists()
    before = state(phone)
    prior = initial['before']['profile']
    current = before['profile']
    assert current['attemptStates'] == prior['attemptStates'][:-1] + ['Interrupted']
    assert current['lives'] == prior['lives'] - 1
    for key in ('coins', 'stars', 'completed', 'currentLevel', 'starting', 'tools', 'giftClaims', 'rewardCount'):
        assert current[key] == prior[key]
    phone.assert_no_active_attempt()
    assert phone.foreground()
    report = {'utc': utc(), 'status': 'RUNNING', 'runnerSHA256': sha(__file__),
              'initialFailedObservationSHA256': sha(original), 'lateObservation': before,
              'ordinaryProfileMtimeEpochSeconds': int(phone.adb('shell', 'stat', '-c', '%Y', phone.base + '/Profiles/Development-v1/profile.json')),
              'scope': 'Read-only observation of the same already interrupted attempt after its initial seven-second observation failed. One later ordinary relaunch tests duplicate settlement. No repeated interruption, save edits, waiver of the initial failure or exact boot-ready timing claim.'}
    capture = phone.capture('Interruption/Recovered_Home.png')
    report['lateCaptureSHA256'] = sha(capture)
    report['initialProcessLog'] = phone.app_log('Interruption/InitialProcess.log')
    write(path, report)
    phone.adb('shell', 'am', 'force-stop', PACKAGE)
    report['secondLaunchRequestedUtc'] = utc()
    phone.launch()
    time.sleep(15)
    report['afterSecondRelaunch'] = state(phone)
    assert report['afterSecondRelaunch']['savedFiles'] == before['savedFiles']
    phone.assert_no_active_attempt()
    capture = phone.capture('Interruption/SecondRelaunch_Home.png')
    report['secondCaptureSHA256'] = sha(capture)
    report['secondProcessLog'] = phone.app_log('Interruption/SecondProcess.log')
    assert not report['initialProcessLog']['selectedErrorCount'] and not report['secondProcessLog']['selectedErrorCount']
    report['status'] = 'PASS_EVENTUAL_SINGLE_LOSS_AND_SECOND_RELAUNCH_PRESERVES_EARLY_OBSERVATION_FAILURE'
    report['finishedUtc'] = utc()
    write(path, report)
    print(json.dumps({'status': report['status'], 'lives': report['afterSecondRelaunch']['profile']['lives']}))


if __name__ == '__main__':
    main()
