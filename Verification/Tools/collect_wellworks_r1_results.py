"""Seal/validate Wellworks R1 native source evidence; does not run Unity."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/WellworksR1'


def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, v): p.write_text(json.dumps(v, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def main(seal=False):
    native = read(OUT / 'Native_Review.json')
    assert native['status'] == 'PASS_NATIVE_WELLWORKS_R1' and not native['error']
    assert native['checks'] == 5415 and native['layouts'] == 75 and len(native['frames']) == 85
    for n, report_name in [('Import', 'Import'), ('Native', 'Native_Review'), ('General', 'General_Checks'), ('WellworksChecks', 'WellworksChecks'), ('WellworksPlay', 'WellworksPlay')]:
        process = read(OUT / (n + '_Process.json')); r = read(OUT / (report_name + '.json'))
        assert process['exitCode'] == 0 and not process['timedOut'] and r['status'].startswith('PASS_') and not r.get('error') and not r.get('failures'), n
        if r.get('utc'): assert datetime.fromisoformat(r['utc'].replace('Z', '+00:00')) >= datetime.fromisoformat(process['startedUtc'].replace('Z', '+00:00')), n + ' stale'
    assert read(OUT / 'General_Checks.json')['passed'] == 533 and read(OUT / 'General_Checks.json')['failed'] == 0
    assert read(OUT / 'WellworksChecks.json')['checks'] == 696 and read(OUT / 'WellworksPlay.json')['checks'] == 17
    audit = read(OUT / 'Asset_Audit.json'); package = read(OUT / 'Package_Review.json'); visual = read(OUT / 'Visual_Review.json')
    assert audit['original_art_fonts_metadata_settings_levels_schedules_unchanged'] and len(audit['changed_existing_inputs']) == 4
    assert package['zip_crc_error'] is None and package['asset_manifest_verified'] == 24 and package['unitypackage_patch_matches'] == 68
    assert package['checksum_list_matching'] == 70 and len(package['checksum_list_stale']) == 55 and package['milestone_rewards_match_approved_service']
    assert len(visual['frames']) == 13 and all(sha(OUT / p) == h for p, h in visual['frames'].items())
    if seal:
        files = {}
        for base in ['Unity/Assets', 'Unity/ProjectSettings', 'Unity/Packages']:
            for p in (ROOT / base).rglob('*'):
                if p.is_file(): files[p.relative_to(ROOT).as_posix()] = sha(p)
        for name in ['Verification/Run-WellworksR1.ps1', 'Verification/Run-UnityVerification.ps1', 'Verification/Tools/collect_wellworks_r1_results.py', 'Verification/Tools/collect_results.py']: files[name] = sha(ROOT / name)
        write(OUT / 'Source_SHA256.json', {'files': dict(sorted(files.items())), 'capture_sha256': {p: sha(OUT / p) for p in native['frames']}})
    source = read(OUT / 'Source_SHA256.json')
    assert all(sha(ROOT / p) == h for p, h in source['files'].items()), 'Reviewed source changed'
    assert all(sha(OUT / p) == h for p, h in source['capture_sha256'].items()), 'Reviewed captures changed'
    summary = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'PASS_NATIVE_WELLWORKS_R1_SOURCE_ONLY',
        'scope': 'Native UGUI design integration and isolated local service/file fault recovery. Design snapshots use labelled fixtures; confirmed collection uses actual local receipts. No production backend, Android build or device validation.',
        'native_ui_checks': 5415, 'locale_size_state_cases': 75, 'captures': 85, 'inspected_frames': 13,
        'model_checks': 696, 'connected_fault_checks': 17, 'general_checks': 533,
        'package_issue': 'Supplied SHA256SUMS.txt has 55 stale entries; 70 match. All 24 asset-manifest hashes and 68 bundle/patch file pairs match; existing corrected PNGs reused. Actual package hashes recorded separately.',
        'source_inputs': len(source['files']), 'source_sha256': sha(OUT / 'Source_SHA256.json'), 'apk_built': False, 'apk_installed': False,
        'remaining': ['Physical device/notch/touch, native framebuffer and animation memory/performance verification.', 'Production reward authority remains gated; no remote Wellworks request or backend is added. Current claims are synchronous local service transactions.', 'Existing clarity reference remains RGBA32/mipmapped; prior high-density source limits and future compression review remain applicable.']}
    write(OUT / 'Verification_Summary.json', summary)
    deployment = read(ROOT / 'Verification/Evidence/Checkpoint53/Android/Main_Installation.json')
    write(ROOT / 'Verification/Evidence/Native_Source_Checkpoint.json', {'utc': summary['utc'], 'status': summary['status'], 'scope': summary['scope'], 'source_checkpoint': 58,
        'review': 'Codex_Handoff/Documentation/58_WELLWORKS_R1_REVIEW.md', 'summary': 'Verification/Evidence/WellworksR1/Verification_Summary.json',
        'source_sha256': summary['source_sha256'], 'installed_checkpoint': 54, 'deployment_scope': 'Last recorded deployment, not rechecked this turn. UI source changes await deployment.',
        'android_apk_sha256': deployment['apk_sha256'], 'android_apk_matches_current_source': False})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--seal', action='store_true'); main(p.parse_args().seal)
