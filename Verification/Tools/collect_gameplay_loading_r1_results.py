"""Seal/check the native gameplay-loading R2 integration; no Unity/device execution."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/GameplayLoadingR1'


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p, v): p.write_text(json.dumps(v, indent=2) + '\n', encoding='utf-8', newline='\n')


def main(seal=False):
    native, general, connected, package, audit, visual = (read(OUT / n) for n in [
        'Native_Review.json', 'General_Checks.json', 'Connected_Flow.json', 'Package_Review.json', 'Asset_Audit.json', 'Visual_Review.json'])
    assert native['status'] == 'PASS_NATIVE_GAMEPLAY_LOADING_R2' and not native['error']
    assert native['checks'] >= 8000 and native['layouts'] == 150 and native['readyFrames'] <= 1 and len(native['frames']) == 41
    assert len(native['flow']) == 3
    assert general['passed'] == 534 and general['failed'] == 0
    assert connected['status'] == 'PASS_NATIVE_PLAY_SMOKE' and len(connected['checks']) == 17 and not connected['errors']
    for n in ['Import', 'Native', 'General', 'Connected']:
        p = read(OUT / (n + '_Process.json'))
        assert p['exitCode'] == 0 and not p['timedOut'], n
    assert read(OUT / 'Import.json')['registered'] == 48
    assert package['crcError'] is None and package['internal_revision'] == 'R2' and package['verified_bundle_pairs'] == 28
    assert len(package['assets']) == 14 and audit['other_existing_art_fonts_metadata_guids_levels_settings_unchanged']
    assert len(audit['changed_existing_inputs']) == 3
    for a in package['assets']:
        p = ROOT / 'Unity' / a['path']
        assert sha(p) == a['sha256'] and ('guid: ' + a['guid']) in p.with_suffix('.png.meta').read_text()
    assert visual['status'] == 'PASS_REVIEWED_NATIVE_GAMEPLAY_LOADING_R2' and len(visual['frames']) >= 10
    assert all(sha(OUT / n) == h for n, h in visual['frames'].items())
    if seal:
        files = {p.relative_to(ROOT).as_posix(): sha(p) for base in ['Unity/Assets', 'Unity/ProjectSettings', 'Unity/Packages'] for p in (ROOT / base).rglob('*') if p.is_file()}
        for n in ['Verification/Run-GameplayLoadingR1.ps1', 'Verification/Run-GameplayLoadingR1Flow.ps1', 'Verification/Tools/collect_gameplay_loading_r1_results.py', 'Verification/Tools/collect_results.py']:
            files[n] = sha(ROOT / n)
        write(OUT / 'Source_SHA256.json', {'files': dict(sorted(files.items())), 'captures': {n: sha(OUT / n) for n in native['frames']}})
    source = read(OUT / 'Source_SHA256.json')
    assert all(sha(ROOT / n) == h for n, h in source['files'].items()), 'Reviewed inputs changed'
    assert all(sha(OUT / n) == h for n, h in source['captures'].items()), 'Reviewed captures changed'
    summary = {'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'status': 'PASS_NATIVE_GAMEPLAY_LOADING_R2_SOURCE_ONLY',
               'source_checkpoint': 63, 'package_internal_revision': 'R2', 'native_checks': native['checks'],
               'layouts': native['layouts'], 'captures': len(native['frames']), 'inspected_images': len(visual['frames']),
               'readiness_wait_rendered_frames_observed': native['readyFrames'], 'general_checks': general['passed'], 'connected_checks': len(connected['checks']),
               'source_inputs': len(source['files']), 'source_sha256': sha(OUT / 'Source_SHA256.json'), 'apk_built': False, 'apk_installed': False,
               'scope': 'Native Unity Editor loading UI and isolated launch/grant-failure/retry/token/starting-item checks. Immediate readiness handoff without dwell or fade. No current device or performance claim.',
               'remaining': ['New APK/device rendering and lifecycle verification, notches and native memory/GPU profiling.', 'No physical-device or full campaign regression performed this turn.', 'Current M46 enables both tip power kinds without progression unlock gates; future unlock service must supply actual eligibility.', 'Localized announcement hooks and tip labels are exposed; no OS screen-reader provider is added.']}
    write(OUT / 'Verification_Summary.json', summary)
    installed = read(ROOT / 'Verification/Evidence/HomeLivesAndroid/Verification_Summary.json')
    write(ROOT / 'Verification/Evidence/Native_Source_Checkpoint.json', {'utc': summary['utc'], 'status': summary['status'], 'scope': summary['scope'],
          'source_checkpoint': 63, 'installed_checkpoint': 62, 'source_sha256': summary['source_sha256'],
          'review': 'Codex_Handoff/Documentation/63_GAMEPLAY_LOADING_R2_REVIEW.md', 'summary': 'Verification/Evidence/GameplayLoadingR1/Verification_Summary.json',
          'android_apk_sha256': installed['apk_sha256'], 'android_apk_matches_current_source': False})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--seal', action='store_true'); main(p.parse_args().seal)
