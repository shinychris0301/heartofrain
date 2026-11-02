"""Seal/validate the Daily Gift R1 source review. Runs no Unity or service tests."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/DailyGiftR1'
MODES = {
    'BackendGiftLayout': 'PASS_NATIVE_BACKEND_GIFT_LAYOUT',
    'BackendGiftPlay': 'PASS_NATIVE_BACKEND_GIFT_UI',
    'BackendGiftRestart': 'PASS_NATIVE_BACKEND_GIFT_UI',
    'ProfileChecks': 'PASS_NATIVE_PROFILE_TRANSACTIONS',
    'DailyGiftPlay': 'PASS_NATIVE_DAILY_GIFT',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def main(seal=False):
    native = read(OUT / 'Native_Review.json')
    general = read(OUT / 'General_Checks.json')
    audit = read(OUT / 'Asset_Audit.json')
    package = read(OUT / 'Package_Review.json')
    visual = read(OUT / 'Visual_Review.json')
    assert native['status'] == 'PASS_NATIVE_DAILY_GIFT_R1' and not native['error']
    assert native['checks'] == 2966 and native['layouts'] == 30 and len(native['frames']) == 45
    assert general['status'] == 'PASS_NATIVE_EDITOR_CHECKS' and general['failed'] == 0 and general['passed'] == 533
    assert package['zip_crc_error'] is None and package['supplied_manifest_verified_files'] == 103 and package['unitypackage_patch_byte_matches'] == 52
    assert audit['original_metadata_unchanged'] and audit['original_art_fonts_schedule_levels_settings_unchanged']
    assert len(audit['new_images']) == 11 and len(audit['changed_existing_inputs']) == 5
    claims = {}
    for mode, expected in MODES.items():
        r = read(OUT / 'Claims' / (mode + '.json'))
        assert r['status'] == expected and not r.get('failures'), mode
        claims[mode] = r['checks']
    service = read(OUT / 'Claims/Service_Tests.json')
    assert service['status'] == 'PASS_BACKEND_SERVICE_TESTS' and service['tests'] == 23 and not service['failures'] and not service['errors']
    for name, report_name in [('Import', 'Import'), ('Native', 'Native_Review'), ('General', 'General_Checks')] + [('Claims/' + n, 'Claims/' + n) for n in MODES]:
        process = read(OUT / (name + '_Process.json'))
        assert process['exitCode'] == 0 and not process['timedOut'], name
        r = read(OUT / (report_name + '.json'))
        if r.get('utc'):
            assert datetime.fromisoformat(r['utc'].replace('Z', '+00:00')) >= datetime.fromisoformat(process['startedUtc'].replace('Z', '+00:00')), name + ' stale'
    assert len(visual['frames']) == 13 and all(sha(OUT / p) == h for p, h in visual['frames'].items())
    captures = {p: sha(OUT / p) for p in native['frames']}
    for mode in ['BackendGiftPlay', 'BackendGiftRestart']:
        for p in read(OUT / 'Claims' / (mode + '.json'))['frames']:
            captures['Claims/' + p] = sha(OUT / 'Claims' / p)
    if seal:
        files = {}
        for base in ['Unity/Assets', 'Unity/ProjectSettings', 'Unity/Packages']:
            for path in (ROOT / base).rglob('*'):
                if path.is_file():
                    files[path.relative_to(ROOT).as_posix()] = sha(path)
        for base in ['Backend/hotr_backend', 'Backend/tests', 'Backend/tools']:
            for path in (ROOT / base).rglob('*.py'):
                files[path.relative_to(ROOT).as_posix()] = sha(path)
        for name in ['Verification/Run-DailyGiftR1.ps1', 'Verification/Run-DailyGiftR1Claims.ps1', 'Verification/Run-BackendGiftUI.ps1', 'Verification/Run-UnityVerification.ps1', 'Verification/Tools/collect_daily_gift_r1_results.py', 'Verification/Tools/collect_results.py']:
            files[name] = sha(ROOT / name)
        write(OUT / 'Source_SHA256.json', {'utc': datetime.now(timezone.utc).isoformat(), 'scope': 'Frozen source/tool inputs and native captures; not a deployment manifest.', 'files': dict(sorted(files.items())), 'capture_sha256': captures})
    source = read(OUT / 'Source_SHA256.json')
    assert all(sha(ROOT / p) == h for p, h in source['files'].items()), 'Reviewed inputs changed'
    assert source['capture_sha256'] == captures, 'Native captures changed'
    summary = {
        'utc': datetime.now(timezone.utc).isoformat(), 'status': 'PASS_NATIVE_DAILY_GIFT_R1_SOURCE_ONLY',
        'scope': 'Native UGUI design integration, local development claim sequence, actual isolated HTTP delay/loss/retry/restart tests. Day/locale design snapshots use labelled visual fixtures. No APK or physical-device validation.',
        'native_design_checks': native['checks'], 'locale_size_cases': native['layouts'], 'native_design_frames': len(native['frames']),
        'inspected_design_frames': len(visual['frames']), 'claim_compatibility_checks': claims, 'backend_service_tests': service['tests'],
        'general_editor_checks': general['passed'], 'imported_images': len(audit['new_images']), 'changed_existing_inputs': audit['changed_existing_inputs'],
        'source_inputs': len(source['files']), 'source_sha256': sha(OUT / 'Source_SHA256.json'),
        'apk_built': False, 'apk_installed': False,
        'limitations': ['Android/physical-device rendering, touch, notches and effect performance remain unverified for this design.', 'Production reward authentication/trusted time/hosting remain a separate backend gate. Default release authority remains unavailable; no claim simulation shipped as production.', 'Native uses existing dynamic UGUI fonts and portrait-clamped scrolling layout; the browser TMP suggestion and supplemental wide two-column layout are not a framework/orientation change.'],
    }
    write(OUT / 'Verification_Summary.json', summary)
    deployment = read(ROOT / 'Verification/Evidence/Checkpoint53/Android/Main_Installation.json')
    write(ROOT / 'Verification/Evidence/Native_Source_Checkpoint.json', {
        'utc': summary['utc'], 'status': summary['status'], 'scope': summary['scope'], 'source_checkpoint': 56,
        'review': 'Codex_Handoff/Documentation/56_DAILY_GIFT_R1_REVIEW.md', 'summary': 'Verification/Evidence/DailyGiftR1/Verification_Summary.json',
        'source_sha256': summary['source_sha256'], 'installed_checkpoint': 54, 'deployment_scope': 'Last recorded deployment, not rechecked this turn. Daily Gift R1 and Account R6 are source-only.',
        'android_apk_sha256': deployment['apk_sha256'], 'android_apk_matches_current_source': False,
    })
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seal', action='store_true', help='Freeze current inputs after the native reports and inspected-frame manifest have passed.')
    main(parser.parse_args().seal)
