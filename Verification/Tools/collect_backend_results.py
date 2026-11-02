"""Freeze and collect the portable backend checkpoint; no cloud or APK claim."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Backend'
MODES = {
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
    paths.extend(ROOT / p for p in ('Verification/Run-UnityVerification.ps1', 'Verification/Run-BackendVerification.ps1', 'Verification/Tools/collect_backend_results.py'))
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def utc(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    current = sources()
    prior = read(ROOT / 'Verification/Evidence/ProfileEvents/Source_SHA256.json')
    player = {name: value for name, value in current.items() if name.startswith('Unity/Assets/') and 'Editor' not in Path(name).parts}
    previous_player = {name: value for name, value in prior['files'].items() if 'Editor' not in Path(name).parts}
    assert all(player.get(name) == value for name, value in previous_player.items()), 'An existing player input changed'
    prefix = 'Unity/Assets/HeartOfTheRain/App/Profile/Runtime/'
    expected_new = {prefix + stem + suffix for stem in ('BackendClient', 'BackendGiftSession') for suffix in ('.cs', '.cs.meta')}
    added = sorted(set(player) - set(previous_player))
    assert set(added) == expected_new, added
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if args.freeze:
        write('Source_SHA256.json', {'utc': now, 'scope': 'All Unity assets, portable backend source/config/lock and verification entry points before native/service verification. No APK binding.', 'files': current})
        write('Changed_Player_Inputs.json', {'changed': [], 'added': added, 'deleted': [], 'player_input_count': len(player), 'unchanged_previous_player_inputs': len(previous_player)})
        print(json.dumps({'frozen_sources': len(current), 'player_inputs': len(player), 'existing_player_changes': 0, 'added_player_inputs': len(added)}))
        return
    frozen = read(OUT / 'Source_SHA256.json')
    # This collector does not execute inside Unity or the service. Its own fixes
    # are recorded separately; every tested input and entry point stays frozen.
    collector_path = 'Verification/Tools/collect_backend_results.py'
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
    assert restart['status'] == 'PASS_REAL_HTTP_PROCESS_RESTART' and restart['checks'] == 6 and not restart['failures']
    assert utc(restart['utc']) >= utc(frozen['utc'])
    integrity = read(OUT / 'Integrity.json')
    assert integrity['status'].startswith('PASS') and not integrity['unexpected_changed_baseline_files']
    contract = read(OUT / 'OpenAPI.json')
    assert '/internal/v1/verified-first-clear' in contract['paths'] and contract['paths']['/v1/daily-gift/claim']['post']['security']
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
        for name in ('primary', 'recovery'):
            assert private[name]['token'] not in text, 'Credential leakage detected in exported material'
            secret_count += 1
    summary = {
        'utc': now, 'status': 'PASS_PORTABLE_BACKEND_CHECKPOINT',
        'scope': 'Local/staging service, native Unity HTTP transport and compatibility only. No hosted deployment, ordinary-account migration, new APK or Android certification.',
        'service_scenarios': service['tests'], 'native_suites': suites, 'native_checks': total,
        'actual_http_process_restart_checks': restart['checks'], 'source_sha256': sha(OUT / 'Source_SHA256.json'),
        'collection_tool_sha256': current[collector_path], 'collection_tool_at_freeze_sha256': frozen['files'][collector_path],
        'openapi_sha256': sha(OUT / 'OpenAPI.json'), 'service_report_sha256': sha(OUT / 'Service_Tests.json'),
        'restart_report_sha256': sha(OUT / 'HTTP_Process_Restart.json'), 'integrity_report_sha256': sha(OUT / 'Integrity.json'),
        'credential_export_guard': {'status': 'PASS', 'fixture_tokens_checked': secret_count},
        'unchanged_prior_player_inputs': len(previous_player), 'added_player_inputs': added,
        'unchanged_previous_apk_sha256': old_apk,
        'production_enabled': False, 'ordinary_client_factory_changed': False, 'automatic_audit_upload': False,
        'remaining': ['Hosting/HTTPS and managed identity/onboarding/recovery',
                      'Gameplay verifier, server attempt settlement and offline-deadline reconciliation',
                      'Full wallet/account migration and secure client credential storage',
                      'Asynchronous UI service selection and Android integration',
                      'Real competition, purchases and production privacy/retention/operations'],
    }
    write('Verification_Summary.json', summary)
    (OUT.parent / 'Native_Source_Checkpoint.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': summary['status'], 'service_scenarios': service['tests'], 'native_suites': len(suites), 'native_checks': total, 'actual_process_restart_checks': restart['checks'], 'apk': 'unchanged'}))


if __name__ == '__main__':
    main()
