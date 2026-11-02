"""Collect the independent-review follow-up without overwriting historical source/APK evidence."""
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/IndependentReview66'


def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, obj): p.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    native = read(OUT / 'Loading_Art_Lifetime.json')
    assert native['status'] == 'PASS_NATIVE_LOADING_ART_LIFETIME' and not native['error'] and native['cycles'] == 4
    assert all(native[k] for k in ['staleRecoveryIgnored', 'rainCupFocus', 'accountRetryFocus', 'resourcesBound'])
    general, profile, flow = (read(OUT / n) for n in ['Checks.json', 'ProfileChecks.json', 'PlaySmoke.json'])
    assert general['passed'] == 534 and general['failed'] == 0
    assert profile['status'] == 'PASS_NATIVE_PROFILE_TRANSACTIONS' and not profile['failures']
    assert flow['status'] == 'PASS_NATIVE_PLAY_SMOKE' and len(flow['checks']) == 17 and not flow['errors']
    for n in ['Native_Process.json', 'Checks_Process.json', 'ProfileChecks_Process.json', 'PlaySmoke_Process.json']:
        assert read(OUT / n)['exitCode'] == 0
    bindings = read(OUT / 'Resource_Audit.json')
    assert len(bindings['assets']) == 7 and bindings['all_meta_present'] and bindings['references_resolved'] == 71
    source = read(OUT / 'Source_SHA256.json')
    assert all(sha(ROOT / n) == h for n, h in source['files'].items()), 'Reviewed Unity source changed'
    deployed = read(ROOT / 'Verification/Evidence/GameplayLoadingAndroid/Verification_Summary.json')
    summary = {'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'status': 'PASS_REVIEWED_CORRECTIONS_SOURCE_ONLY',
               'source_checkpoint': 66, 'source_sha256': sha(OUT / 'Source_SHA256.json'), 'source_inputs': len(source['files']),
               'general_checks': general['passed'], 'profile_checks': profile['checks'], 'connected_checks': len(flow['checks']),
               'resources': 7, 'loading_art_reopen_cycles': native['cycles'], 'stale_recovery_and_focus': True,
               'scope': 'Re-read checkpoint65 corrections, preserve them, add generation guard/focus completion and accurate gift font verification; native isolated tests. Prior visual/device reports remain historical.',
               'remaining': ['RGBA32/compression and device memory/GPU validation.', 'No APK rebuilt: installed deployment64 predates the independent corrections.', 'No remote account/cloud service or production event authority added.']}
    write(OUT / 'Verification_Summary.json', summary)
    write(ROOT / 'Verification/Evidence/Native_Source_Checkpoint.json', {
        'utc': summary['utc'], 'status': summary['status'], 'scope': summary['scope'], 'source_checkpoint': 66,
        'installed_checkpoint': 64, 'source_sha256': summary['source_sha256'],
        'review': 'Codex_Handoff/Documentation/66_INDEPENDENT_REVIEW_FOLLOWUP.md',
        'summary': 'Verification/Evidence/IndependentReview66/Verification_Summary.json',
        'android_apk_sha256': deployed['apk_sha256'], 'android_apk_matches_current_source': False})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__': main()
