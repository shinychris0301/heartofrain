"""Validate/seal Home Lives R1 native evidence; never runs Unity or a device."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/HomeLivesR1'


def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, v): p.write_text(json.dumps(v, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def main(seal=False):
    native, general, connected = (read(OUT / n) for n in ['Native_Review.json', 'General_Checks.json', 'Connected_Flow.json'])
    assert native['status'] == 'PASS_NATIVE_HOME_LIVES_R1' and not native['error']
    assert native['checks'] == 3266 and native['layouts'] == 168 and len(native['frames']) == 73
    assert general['passed'] == 534 and general['failed'] == 0
    assert connected['status'] == 'PASS_NATIVE_PLAY_SMOKE' and len(connected['checks']) == 17 and not connected['errors']
    for name, result in [('Import', read(OUT / 'Import.json')), ('Native', native), ('General', general), ('Connected', connected)]:
        process = read(OUT / (name + '_Process.json'))
        assert process['exitCode'] == 0 and not process['timedOut'] and result['status'].startswith('PASS_'), name
        if result.get('utc'):
            assert datetime.fromisoformat(result['utc'].replace('Z', '+00:00')) >= datetime.fromisoformat(process['startedUtc'].replace('Z', '+00:00')), name + ' stale'
    package, audit, visual = (read(OUT / n) for n in ['Package_Review.json', 'Asset_Audit.json', 'Visual_Review.json'])
    assert package['crcError'] is None and package['bundlePatchPairs'] == 14
    assert len(package['assets']) == 5 and all(a['manifestMatches'] and a['liveSameBytes'] for a in package['assets'])
    assert audit['existing_art_fonts_guids_levels_economy_settings_unchanged'] and len(audit['changed_existing_inputs']) == 8
    assert len(visual['frames']) >= 12 and all(sha(OUT / n) == h for n, h in visual['frames'].items())
    if seal:
        files = {p.relative_to(ROOT).as_posix(): sha(p) for base in ['Unity/Assets', 'Unity/ProjectSettings', 'Unity/Packages'] for p in (ROOT / base).rglob('*') if p.is_file()}
        for n in ['Verification/Run-HomeLivesR1.ps1', 'Verification/Run-HomeLivesR1Flow.ps1', 'Verification/Run-UnityVerification.ps1', 'Verification/Tools/collect_home_lives_r1_results.py', 'Verification/Tools/collect_results.py']:
            files[n] = sha(ROOT / n)
        write(OUT / 'Source_SHA256.json', {'files': dict(sorted(files.items())), 'captures': {n: sha(OUT / n) for n in native['frames']}})
    source = read(OUT / 'Source_SHA256.json')
    assert all(sha(ROOT / p) == h for p, h in source['files'].items()), 'Reviewed source changed'
    assert all(sha(OUT / p) == h for p, h in source['captures'].items()), 'Reviewed captures changed'
    summary = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'PASS_NATIVE_HOME_LIVES_R1_SOURCE_ONLY',
        'scope': 'Native Editor UGUI plus isolated life projection/file transactions; confirmed loss and single-regeneration motion use real local receipts. No new device validation or trusted time service.',
        'native_checks': native['checks'], 'locale_size_state_cases': native['layouts'], 'captures': len(native['frames']), 'inspected_images': len(visual['frames']),
        'included_transaction_checks': 40, 'general_checks': general['passed'], 'connected_flow_checks': len(connected['checks']),
        'source_inputs': len(source['files']), 'source_sha256': sha(OUT / 'Source_SHA256.json'), 'apk_built': False, 'apk_installed': False,
        'remaining': ['Android/iOS native device rendering, notches/touch, animation performance and texture memory/compression review.',
            'Regeneration authority remains the approved existing device-UTC service. The UI uses monotonic elapsed time between snapshots; changing wall time can still affect service grants until trusted time is integrated.',
            'Cosmetic pending events are session-scoped. Reopening a process seeds old receipts without replay; the correct durable balance survives, but an unshown animation is not persisted.',
            'Existing local receipt data does not add remote life synchronization or an OS screen-reader provider; localized announcement hooks and control labels are exposed.']}
    write(OUT / 'Verification_Summary.json', summary)
    deployed = read(ROOT / 'Verification/Evidence/EffectBatch/Android/Main_Installation.json')
    write(ROOT / 'Verification/Evidence/Native_Source_Checkpoint.json', {'utc': summary['utc'], 'status': summary['status'], 'scope': summary['scope'], 'source_checkpoint': 61,
        'review': 'Codex_Handoff/Documentation/61_HOME_LIVES_R1_REVIEW.md', 'summary': 'Verification/Evidence/HomeLivesR1/Verification_Summary.json', 'source_sha256': summary['source_sha256'],
        'installed_checkpoint': 60, 'deployment_scope': 'Last recorded main LDPlayer installation, not rechecked this turn. Home Lives source awaits deployment.', 'android_apk_sha256': deployed['apk_sha256'], 'android_apk_matches_current_source': False})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--seal', action='store_true'); main(parser.parse_args().seal)
