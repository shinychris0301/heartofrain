"""Validate/seal native UI Clarity R1 evidence. Does not run Unity or build an APK."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/UIClarityR1'


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def main(seal=False):
    reports = {n: read(OUT / p) for n, p in {
        'Before': 'Before/Report.json', 'Apply': 'Apply.json', 'Checks': 'Checks.json',
        'After': 'After/Report.json', 'General': 'General.json', 'WellworksPlay': 'WellworksPlay.json',
    }.items()}
    for name, r in reports.items():
        assert r['status'].startswith('PASS_') and not r.get('error') and not r.get('failures'), name
        process = read(OUT / (name + '_Process.json'))
        assert process['exitCode'] == 0 and not process['timedOut'], name
        assert datetime.fromisoformat(r['utc'].replace('Z', '+00:00')) >= datetime.fromisoformat(process['startedUtc'].replace('Z', '+00:00')), name + ' stale'
    assert len(reports['Before']['frames']) == 20 and len(reports['After']['frames']) == 37
    assert reports['After']['checks'] == 177 and reports['Checks']['checks'] == 15
    assert reports['General']['passed'] == 533 and reports['General']['failed'] == 0
    assert reports['WellworksPlay']['checks'] == 13
    audit = read(OUT / 'Asset_Audit.json')
    assert audit['all_registered_guids_retained'] and audit['gameplay_levels_scenes_fonts_schedules_project_settings_unchanged']
    assert len(audit['registered_assets']) == 22 and len(audit['changed_existing_inputs']) == 29
    for asset in audit['registered_assets']:
        assert sha(ROOT / 'Unity' / asset['path']) == asset['sha256']
    package = read(OUT / 'Package_Review.json')
    assert package['zip_crc_error'] is None and package['unitypackage_patch_file_matches'] == 84 and package['manifest_asset_occurrences_verified'] == 43
    budget = read(OUT / 'Measured_Budgets.json')
    assert budget['rocket_peaks'][0]['fits'] and not budget['rocket_peaks'][1]['fits']
    visual = read(OUT / 'Visual_Review.json')
    assert len(visual['frames']) == 11 and all(sha(OUT / p) == h for p, h in visual['frames'].items())
    if seal:
        files = {}
        for base in ['Unity/Assets', 'Unity/ProjectSettings', 'Unity/Packages']:
            for p in (ROOT / base).rglob('*'):
                if p.is_file():
                    files[p.relative_to(ROOT).as_posix()] = sha(p)
        for n in ['Verification/Run-UIClarityR1.ps1', 'Verification/Run-UnityVerification.ps1', 'Verification/Tools/collect_ui_clarity_r1_results.py', 'Verification/Tools/collect_results.py']:
            files[n] = sha(ROOT / n)
        retained = {p.relative_to(OUT).as_posix(): sha(p) for p in OUT.rglob('*.png') if p.parent.name == 'Reviewed' or '393x852' in p.name or 'Day2_PeakFixture' in p.name}
        write(OUT / 'Source_SHA256.json', {'scope': 'Frozen source inputs and retained native images/crops. Other raw sweep images stay local; hashes recorded separately.', 'files': dict(sorted(files.items())), 'retained_capture_sha256': retained})
    source = read(OUT / 'Source_SHA256.json')
    assert all(sha(ROOT / p) == h for p, h in source['files'].items()), 'Reviewed source changed'
    assert all(sha(OUT / p) == h for p, h in source['retained_capture_sha256'].items()), 'Reviewed image changed'
    summary = {
        'utc': datetime.now(timezone.utc).isoformat(), 'status': 'PASS_NATIVE_UI_CLARITY_WITH_RECORDED_PIXEL_LIMITS',
        'scope': 'Registered UI import correction and native UGUI comparison; real pre-build callback tested with injected regressions. No APK build, installation or device certification.',
        'registered_assets': 22, 'native_render_checks': 177, 'guard_checks': 15, 'before_captures': 20, 'after_captures': 37,
        'inspected_images': 11, 'general_checks': 533, 'connected_wellworks_checks': 13,
        'source_inputs': len(source['files']), 'source_sha256': sha(OUT / 'Source_SHA256.json'),
        'pixel_limit': budget['known_limits'], 'apk_built': False, 'apk_installed': False,
        'remaining': ['Android/device memory, effect performance, input and native framebuffer validation.', 'The package WellworksDesign renderer is not installed. Current Wellworks layout retained; its active reward art now uses filtered standalone UI sprites.', 'The development reward disclosure remains. No economy, account backend, portrait policy, gameplay atlas or font-system changes.'],
    }
    write(OUT / 'Verification_Summary.json', summary)
    prior = read(ROOT / 'Verification/Evidence/Checkpoint53/Android/Main_Installation.json')
    write(ROOT / 'Verification/Evidence/Native_Source_Checkpoint.json', {
        'utc': summary['utc'], 'status': summary['status'], 'scope': summary['scope'], 'source_checkpoint': 57,
        'review': 'Codex_Handoff/Documentation/57_UI_CLARITY_R1_REVIEW.md', 'summary': 'Verification/Evidence/UIClarityR1/Verification_Summary.json',
        'source_sha256': summary['source_sha256'], 'installed_checkpoint': 54,
        'deployment_scope': 'Last recorded deployment, not rechecked this turn. Current UI changes are source-only.',
        'android_apk_sha256': prior['apk_sha256'], 'android_apk_matches_current_source': False,
    })
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seal', action='store_true', help='Freeze inputs after native checks and inspection of the listed images.')
    main(parser.parse_args().seal)
