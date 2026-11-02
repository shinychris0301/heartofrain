"""Freeze and collect the asynchronous Daily Gift UI checkpoint; no cloud or APK claim."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/BackendGiftUI'
MODES = {
    'BackendGiftLayout': ('PASS_NATIVE_BACKEND_GIFT_LAYOUT', 9691),
    'BackendGiftPlay': ('PASS_NATIVE_BACKEND_GIFT_UI', 50),
    'BackendGiftRestart': ('PASS_NATIVE_BACKEND_GIFT_UI', 9),
    'BackendChecks': ('PASS_NATIVE_BACKEND_HTTP', 24),
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


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def sources():
    paths = [p for p in (ROOT / 'Unity/Assets').rglob('*') if p.is_file()]
    paths.extend(p for p in (ROOT / 'Backend').rglob('*') if p.is_file() and not {'.venv', '.local', '__pycache__'} & set(p.relative_to(ROOT / 'Backend').parts))
    paths.extend(ROOT / p for p in ('Verification/Run-UnityVerification.ps1', 'Verification/Run-BackendGiftUI.ps1', 'Verification/Tools/collect_backend_gift_ui_results.py'))
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def utc(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    current = sources()
    prior = read(ROOT / 'Verification/Evidence/Backend/Source_SHA256.json')
    player = {name: value for name, value in current.items() if name.startswith('Unity/Assets/') and 'Editor' not in Path(name).parts}
    previous_player = {name: value for name, value in prior['files'].items() if name.startswith('Unity/Assets/') and 'Editor' not in Path(name).parts}
    changed = sorted(name for name, value in previous_player.items() if player.get(name) != value)
    prefix = 'Unity/Assets/HeartOfTheRain/App/Profile/Runtime/'
    expected_changed = {prefix + name + '.cs' for name in ('BackendGiftSession', 'DailyGiftLayout', 'DailyGiftPage', 'PlayerProfileHost')}
    assert set(changed) == expected_changed, changed
    expected_new = {'Unity/Assets/HeartOfTheRain/Verification/BackendGiftUIProbe.cs' + suffix for suffix in ('', '.meta')}
    backend_changed = sorted(name for name, value in prior['files'].items() if name.startswith('Backend/') and current.get(name) != value)
    assert backend_changed == ['Backend/README.md', 'Backend/tools/check_restart.py', 'Backend/tools/serve_fixture.py'], backend_changed
    added = sorted(set(player) - set(previous_player))
    assert set(added) == expected_new, added
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if args.freeze:
        write('Source_SHA256.json', {'utc': now, 'scope': 'All Unity assets, portable backend source/config/lock and verification entry points before native/service verification. No APK binding.', 'files': current})
        write('Changed_Player_Inputs.json', {'changed': changed, 'added': added, 'backend_test_and_documentation_changes': backend_changed, 'deleted': [], 'player_input_count': len(player), 'unchanged_previous_player_inputs': len(previous_player)-len(changed)})
        print(json.dumps({'frozen_sources': len(current), 'player_inputs': len(player), 'existing_player_changes': len(changed), 'added_player_inputs': len(added)}))
        return
    frozen = read(OUT / 'Source_SHA256.json')
    # This collector does not execute inside Unity or the service. Its own fixes
    # are recorded separately; every tested input and entry point stays frozen.
    collector_path = 'Verification/Tools/collect_backend_gift_ui_results.py'
    assert {k: v for k, v in current.items() if k != collector_path} == {k: v for k, v in frozen['files'].items() if k != collector_path}, 'Tested sources changed after freeze; rerun affected verification'
    suites, total = {}, 0
    for mode, (status, minimum) in MODES.items():
        path = OUT / 'Native_Checkpoints' / (mode + '.json')
        report = read(path)
        process = read(path.with_name(mode + '_Process.json'))
        count = report['checks'] if isinstance(report['checks'], int) else len(report['checks'])
        assert report['status'] == status and not report.get('failures') and not report.get('failed') and count >= minimum, mode
        assert utc(report['utc']) >= utc(frozen['utc']) and utc(process['startedUtc']) >= utc(frozen['utc']), mode
        assert process['exitCode'] == 0 and not process['timedOut'] and process['version'].startswith('2022.3.62f3'), mode
        total += count
        suites[mode] = {'checks': count, 'report_sha256': sha(path), 'process_sha256': sha(path.with_name(mode + '_Process.json'))}
    service = read(OUT / 'Service_Tests.json')
    assert service['status'] == 'PASS_BACKEND_SERVICE_TESTS' and service['tests'] >= 23 and not service['failures'] and not service['errors']
    assert utc(service['utc']) >= utc(frozen['utc'])
    restart = read(OUT / 'HTTP_Process_Restart.json')
    assert restart['status'] == 'PASS_REAL_HTTP_PROCESS_RESTART' and restart['checks'] == 9 and not restart['failures']
    assert utc(restart['utc']) >= utc(frozen['utc'])
    integrity = read(OUT / 'Integrity.json')
    assert integrity['status'].startswith('PASS') and not integrity['unexpected_changed_baseline_files']
    contract = read(ROOT / 'Verification/Evidence/Backend/OpenAPI.json')
    assert '/internal/v1/verified-first-clear' in contract['paths'] and contract['paths']['/v1/daily-gift/claim']['post']['security']
    play = read(OUT / 'Native_Checkpoints/BackendGiftPlay.json')
    resumed = read(OUT / 'Native_Checkpoints/BackendGiftRestart.json')
    assert (play['width'], play['height']) == (900, 1600) and play['framesDuringDelay'] >= 3
    assert (resumed['width'], resumed['height']) == (320, 568)
    frames = play['frames'] + resumed['frames']
    assert len(frames) == 12 and len(set(frames)) == 12
    reviewed = read(OUT / 'Visual_Review.json')
    assert reviewed['scope'] == 'Explicit visual review of native camera-rendered runtime UGUI; not Android/device screenshots.'
    assert set(reviewed['frames']) == set(frames)
    for name in frames:
        assert reviewed['frames'][name] == sha(OUT / name), name
    old_apk = read(ROOT / 'Verification/Evidence/RainCup/Player_Source_SHA256.json')['apk_sha256']
    assert sha(ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk') == old_apk
    # Check actual fixture secrets against source and exported evidence without
    # printing the token or copying private bootstrap files into reports.
    exported = [ROOT / name for name in current]
    exported.extend(p for p in OUT.rglob('*.json') if p.is_file())
    text = '\n'.join(p.read_text(encoding='utf-8', errors='ignore') for p in exported if p.suffix in ('.py', '.cs', '.json', '.md', '.ps1', '.lock', '.in'))
    secret_count = 0
    for path in (ROOT / '.verification-cache/Backend').glob('HTTP-*/connection.json'):
        private = read(path)
        for name in ('primary', 'recovery', 'ui'):
            if name not in private:
                continue
            assert private[name]['token'] not in text, 'Credential leakage detected in exported material'
            secret_count += 1
    summary = {
        'utc': now, 'status': 'PASS_BACKEND_DAILY_GIFT_UI_CHECKPOINT',
        'scope': 'Native Unity Play Mode Daily Gift UI and real loopback HTTP with isolated review accounts; camera-rendered runtime UGUI evidence and compatibility. No ordinary-account migration, hosted deployment, new APK or Android certification.',
        'service_scenarios': service['tests'], 'native_suites': suites, 'native_checks': total,
        'actual_http_process_restart_checks': restart['checks'], 'source_sha256': sha(OUT / 'Source_SHA256.json'),
        'collection_tool_sha256': current[collector_path], 'collection_tool_at_freeze_sha256': frozen['files'][collector_path],
        'openapi_sha256': sha(ROOT / 'Verification/Evidence/Backend/OpenAPI.json'), 'service_report_sha256': sha(OUT / 'Service_Tests.json'),
        'restart_report_sha256': sha(OUT / 'HTTP_Process_Restart.json'), 'integrity_report_sha256': sha(OUT / 'Integrity.json'),
        'credential_export_guard': {'status': 'PASS', 'fixture_tokens_checked': secret_count},
        'unchanged_prior_player_inputs': len(previous_player) - len(changed), 'changed_player_inputs': changed, 'added_player_inputs': added, 'backend_core_and_approved_configs_changed': False,
        'unchanged_previous_apk_sha256': old_apk,
        'production_enabled': False, 'ordinary_profile_backend_enabled': False, 'automatic_audit_upload': False,
        'remaining': ['Hosting/HTTPS and managed identity/onboarding/recovery',
                      'Gameplay verifier, server attempt settlement and offline-deadline reconciliation',
                      'Full wallet/account migration and secure client credential storage',
                      'Production service selection, secure onboarding and Android integration',
                      'Real competition, purchases and production privacy/retention/operations'],
    }
    summary['visual_reviewed_frames'] = len(frames)
    summary['visual_review_sha256'] = sha(OUT / 'Visual_Review.json')
    write('Verification_Summary.json', summary)
    cards = ''.join('<article><h2>' + name.replace('_',' ').replace('.png','') + '</h2><a href="' + name + '"><img loading="lazy" src="' + name + '" alt="' + name + '"></a></article>' for name in frames)
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Backend Daily Gift UI review</title><style>body{font:16px system-ui;background:#142839;color:#edf4fa;margin:24px;max-width:1500px}p{max-width:1000px;line-height:1.5}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}article{background:#20394c;padding:14px;border-radius:12px}h2{font-size:16px}img{width:100%;height:auto}a{color:#99d7ff}</style><h1>Backend Daily Gift UI</h1><p>Native Unity Play Mode and real loopback HTTP with isolated accounts. Images are camera-rendered runtime UGUI, not Android screenshots. Loading, close/reopen, a protected save dialog, unavailable offers, an unconfirmed claim, recovery, five languages and a 320x568 restart at 100% UI scale are reviewed. Buttons are dispatched programmatically; no physical tap or FPS certification is claimed. Saved-frame Home counters are mid-animation; the checked model balance is already 1300.</p><p><a href="Verification_Summary.json">Verification summary</a> | <a href="Native_Play_Checks.json">Connected UI checks</a> | <a href="Native_Restart_Checks.json">Restart checks</a></p><main>' + cards + '</main></html>'
    (OUT / 'Comparison.html').write_text(html, encoding='utf-8')
    (OUT.parent / 'Native_Source_Checkpoint.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': summary['status'], 'service_scenarios': service['tests'], 'native_suites': len(suites), 'native_checks': total, 'actual_process_restart_checks': restart['checks'], 'apk': 'unchanged'}))


if __name__ == '__main__':
    main()
