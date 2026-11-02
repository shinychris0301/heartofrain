"""Freeze/revalidate a native engineering checkpoint without claiming an APK build."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/ProfileEvents'
MODES = {
    'ProfileEventChecks': ('PASS_NATIVE_PROFILE_EVENTS', 478),
    'ProfileEventPlay': ('PASS_NATIVE_PROFILE_EVENTS', 13),
    'ProfileChecks': ('PASS_NATIVE_PROFILE_TRANSACTIONS', 10099),
    'RainCupChecks': ('PASS_NATIVE_RAIN_CUP', 13227),
    'RainCupPlay': ('PASS_NATIVE_RAIN_CUP', 34),
    'DailyGiftPlay': ('PASS_NATIVE_DAILY_GIFT', 51),
    'WellworksChecks': ('PASS_NATIVE_WELLWORKS', 11046),
    'WellworksPlay': ('PASS_NATIVE_WELLWORKS', 13),
    'Checks': ('PASS_NATIVE_EDITOR_CHECKS', 530),
}


def sha(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def sources():
    return {p.relative_to(ROOT).as_posix(): sha(p)
            for p in sorted((ROOT / 'Unity/Assets').rglob('*')) if p.is_file()}


def utc(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    prior = read(ROOT / 'Verification/Evidence/RainCup/Player_Source_SHA256.json')
    current = sources()
    player = {name: digest for name, digest in current.items() if 'Editor' not in Path(name).parts}
    changed = sorted(name for name, digest in prior['files'].items() if player.get(name) != digest)
    added = sorted(set(player) - set(prior['files']))
    expected_host = 'Unity/Assets/HeartOfTheRain/App/Profile/Runtime/PlayerProfileHost.cs'
    prefix = 'Unity/Assets/HeartOfTheRain/App/Profile/Runtime/'
    expected_new = {prefix + stem + suffix for stem in ('ProfileEventFeed', 'LocalProfileEventArchive') for suffix in ('.cs', '.cs.meta')}
    assert changed == [expected_host], changed
    assert set(added) == expected_new, added
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if args.freeze:
        write('Source_SHA256.json', {'utc': now, 'scope': 'All Unity assets/metadata before native suites. Native source checkpoint only; no APK binding.', 'files': current})
        write('Changed_Player_Inputs.json', {'previous_apk': prior['apk_sha256'], 'changed': changed, 'added': added, 'deleted': [], 'player_input_count': len(player)})
        print(f'Frozen {len(current)} assets/metadata; {len(player)} player inputs; one changed runtime file and four added inputs.')
        return
    frozen = read(OUT / 'Source_SHA256.json')
    assert current == frozen['files'], 'Source changed after freeze; freeze and rerun affected verification.'
    checks = 0
    suites = {}
    for mode, (status, minimum) in MODES.items():
        path = OUT / 'Native_Checkpoints' / (mode + '.json')
        report = read(path)
        process = read(path.with_name(mode + '_Process.json'))
        count = report['checks'] if isinstance(report['checks'], int) else len(report['checks'])
        assert report['status'] == status and not report.get('failures') and not report.get('failed'), (mode, report['status'])
        assert count >= minimum and utc(report['utc']) >= utc(frozen['utc']), mode
        assert process['exitCode'] == 0 and not process['timedOut'] and process['version'].startswith('2022.3.62f3'), mode
        assert utc(process['startedUtc']) >= utc(frozen['utc']), mode
        suites[mode] = {'checks': count, 'report_sha256': sha(path), 'process_sha256': sha(path.with_name(mode + '_Process.json'))}
        checks += count
    integrity = read(OUT / 'Integrity.json')
    assert integrity['status'].startswith('PASS'), integrity['status']
    apk = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    assert sha(apk) == prior['apk_sha256'], 'Unexpected APK change; checkpoint does not build or certify a new APK.'
    summary = {
        'utc': now, 'status': 'PASS_NATIVE_PROFILE_EVENT_CHECKPOINT',
        'scope': 'Unity 2022.3.62f3 native source verification. No new Android build, install, device, visual, FPS or balance certification.',
        'total_checks': checks, 'suites': suites, 'source_sha256': sha(OUT / 'Source_SHA256.json'),
        'changed_player_files': changed, 'added_player_inputs': added,
        'unchanged_player_inputs': len(prior['files']) - len(changed),
        'unchanged_prior_apk_sha256': prior['apk_sha256'],
        'production_sender': 'Not connected; no network or automatic diagnostic export.',
        'boundaries': ['Local pseudonymous audit data, not anonymous analytics or an authoritative wallet.',
                       'Opening balances are inferred; unjournaled historical changes cannot be assigned provenance.',
                       'No wall-clock or total cross-journal chronology is invented.',
                       'Profile rollback/archive divergence fails explicit delivery for investigation.',
                       'Long-lived journal archival, consent/privacy and backend delivery remain open.'],
    }
    write('Verification_Summary.json', summary)
    # Keep the Android summary's original APK scope; publish the newer source
    # checkpoint separately so native-only checks cannot masquerade as an install.
    (OUT.parent / 'Native_Source_Checkpoint.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': summary['status'], 'native_suites': len(suites), 'checks': checks, 'apk': 'unchanged previous Rain Cup build'}))


if __name__ == '__main__':
    main()
