"""Seal and validate Rain Cup R1 evidence. Does not run Unity or a device."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/RainCupR1'


def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, v): p.write_text(json.dumps(v, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def main(seal=False):
    native = read(OUT / 'Native_Review.json')
    assert native['status'] == 'PASS_NATIVE_RAIN_CUP_R1' and not native['error']
    assert native['layouts'] == 140 and len(native['frames']) == 150 and native['checks'] >= 8000
    for name, report in [('Import', 'Import'), ('Native', 'Native_Review'), ('General', 'General_Checks'), ('RainCupChecks', 'RainCupChecks'), ('RainCupPlay', 'RainCupPlay')]:
        process, result = read(OUT / (name + '_Process.json')), read(OUT / (report + '.json'))
        assert process['exitCode'] == 0 and not process['timedOut'], name
        assert result['status'].startswith('PASS_') and not result.get('error') and not result.get('failures'), name
        if result.get('utc'):
            assert datetime.fromisoformat(result['utc'].replace('Z', '+00:00')) >= datetime.fromisoformat(process['startedUtc'].replace('Z', '+00:00')), name + ' stale'
    general, model, connected = (read(OUT / n) for n in ['General_Checks.json', 'RainCupChecks.json', 'RainCupPlay.json'])
    assert general['passed'] == 533 and general['failed'] == 0
    assert model['checks'] == 822 and len(set(connected['passed'])) == 23
    assert 'Lost claim reply reconciles collected state and notice' in connected['passed']
    assert 'Precommit claim failure preserves prize eligibility' in connected['passed']
    package, audit, visual = (read(OUT / n) for n in ['Package_Review.json', 'Asset_Audit.json', 'Visual_Review.json'])
    assert package['zipCRCError'] is None and package['manifestMatches'] == package['manifestCount'] == 29
    assert package['bundlePatchMatch'] and package['bundlePatchPairs'] == 38 and all(p['sameBytes'] for p in package['remappedShared'])
    assert audit['existing_art_fonts_metadata_settings_levels_rules_unchanged'] and len(audit['changed_existing_inputs']) == 6 and not audit['missing_inputs']
    assert len(visual['frames']) >= 15 and all(sha(OUT / p) == h for p, h in visual['frames'].items())
    if seal:
        files = {}
        for base in ['Unity/Assets', 'Unity/ProjectSettings', 'Unity/Packages']:
            for p in (ROOT / base).rglob('*'):
                if p.is_file(): files[p.relative_to(ROOT).as_posix()] = sha(p)
        for n in ['Verification/Run-RainCupR1.ps1', 'Verification/Run-RainCupR1Services.ps1', 'Verification/Run-UnityVerification.ps1', 'Verification/Tools/collect_rain_cup_r1_results.py', 'Verification/Tools/collect_results.py']:
            files[n] = sha(ROOT / n)
        write(OUT / 'Source_SHA256.json', {'files': dict(sorted(files.items())), 'capture_sha256': {p: sha(OUT / p) for p in native['frames']}})
    source = read(OUT / 'Source_SHA256.json')
    assert all(sha(ROOT / p) == h for p, h in source['files'].items()), 'Reviewed source changed'
    assert all(sha(OUT / p) == h for p, h in source['capture_sha256'].items()), 'Reviewed captures changed'
    summary = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'PASS_NATIVE_RAIN_CUP_R1_SOURCE_ONLY',
        'scope': 'Native UGUI design and isolated local practice services. State screenshots are fixtures; collection effects follow an actual saved first-prize grant. No Android/device or production competition certification.',
        'native_ui_checks': native['checks'], 'locale_size_state_cases': native['layouts'], 'captures': len(native['frames']), 'inspected_frames': len(visual['frames']),
        'model_checks': model['checks'], 'connected_fault_checks': connected['checks'], 'general_checks': general['passed'],
        'source_inputs': len(source['files']), 'source_sha256': sha(OUT / 'Source_SHA256.json'), 'apk_built': False, 'apk_installed': False,
        'remaining': ['Android/iOS physical safe areas, touch, native device rendering, animation performance and texture memory/compression review.',
            'Ordinary production Rain Cup remains unavailable. No real competitors, hosted authority, provider identity or remote join/claim request is added.',
            'Existing four-rival practice model is preserved. A future production population requires a separate standings/service contract.',
            'High-density checks cover measured Editor layouts and an idle live audit. They are not GPU-residency/FPS certification; chrome still exceeds its 1:1 border budget slightly at 4x.']}
    write(OUT / 'Verification_Summary.json', summary)
    deployed = read(ROOT / 'Verification/Evidence/Checkpoint53/Android/Main_Installation.json')
    write(ROOT / 'Verification/Evidence/Native_Source_Checkpoint.json', {'utc': summary['utc'], 'status': summary['status'], 'scope': summary['scope'], 'source_checkpoint': 59,
        'review': 'Codex_Handoff/Documentation/59_RAIN_CUP_R1_REVIEW.md', 'summary': 'Verification/Evidence/RainCupR1/Verification_Summary.json', 'source_sha256': summary['source_sha256'],
        'installed_checkpoint': 54, 'deployment_scope': 'Last recorded deployment; not rechecked this turn. Current UI source awaits deployment.', 'android_apk_sha256': deployed['apk_sha256'], 'android_apk_matches_current_source': False})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--seal', action='store_true'); main(parser.parse_args().seal)
