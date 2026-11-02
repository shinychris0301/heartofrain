"""Validate the frozen Home Lives source/build and main LDPlayer deployment."""
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/HomeLivesAndroid'


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p, v): p.write_text(json.dumps(v, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    source = read(OUT / 'Source_SHA256.json')
    assert source == read(ROOT / 'Verification/Evidence/HomeLivesR1/Source_SHA256.json')
    assert all(sha(ROOT / p) == h for p, h in source['files'].items()), 'Reviewed inputs changed'
    build, process, artifact, packaging, install, visual = (read(OUT / p) for p in [
        'Android_Build.json', 'AndroidBuild_Process.json', 'APK_Artifact.json',
        'APK_Packaging.json', 'Main_Installation.json', 'Visual_Review.json'])
    assert build['status'] == 'PASS_ANDROID_DEVELOPMENT_BUILD' and not build['errors'] and not build['error']
    assert process['exitCode'] == 0 and not process['timedOut']
    assert dt.datetime.fromisoformat(build['utc'].replace('Z', '+00:00')) >= dt.datetime.fromisoformat(process['startedUtc'])
    apk = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    assert sha(apk) == artifact['sha256'] == packaging['afterSHA256'] == install['apk_sha256'] == install['installed_apk_sha256']
    assert artifact['bytes'] == apk.stat().st_size
    assert all(artifact[k] for k in ['zipalign4KiBPass', 'developmentSignatureVerifies', 'elf16KiBLoadSegmentsPass'])
    assert packaging['status'] == 'PASS_CLEAN_GRADLE_APK_PACKAGING' and not packaging['changedNonSignatureEntries'] and packaging['sameSignerCertificate']
    assert install['status'] == 'PASS_INSTALLED_DATA_PRESERVED_LAUNCHED'
    assert install['before'] == install['after_install'] == install['after_launch']
    assert install['profile_before'] == install['profile_after_launch'] and not install['runtime_error_lines']
    assert visual['status'] == 'PASS_LDPLAYER_HOME_LIVES_VISUAL_REVIEW'
    assert all(sha(OUT / n) == h for n, h in visual['frames'].items())
    manifest = (OUT / 'APK_Manifest.txt').read_text()
    assert 'android:screenOrientation(0x0101001e)=(type 0x10)0x1' in manifest
    summary = {'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'status': 'PASS_REBUILT_INSTALLED_LDPLAYER',
               'source_checkpoint': 61, 'deployment_checkpoint': 62, 'source_inputs': len(source['files']),
               'source_sha256': sha(OUT / 'Source_SHA256.json'), 'apk_sha256': artifact['sha256'],
               'apk_bytes': artifact['bytes'], 'build_errors': build['errors'], 'build_warnings': build['warnings'],
               'serial': install['serial'], 'data_preserved': True, 'runtime_code_changed': False,
               'scope': 'Current development ARM64 APK: native Unity build, clean Gradle packaging, signature/ZIP/ELF checks, replacement installation and portrait Home Full-state observation on main LDPlayer. All reviewed source inputs unchanged. Saves/preferences byte-identical through installation and initial launch.',
               'limitations': 'Gameplay became active during the later visual check; no further input or forced return to Home. No verified heart/pre-level touch smoke, fresh campaign regression, device loss/refill/countdown animation coverage, physical-device certification or trusted-time backend. Existing source61 Editor coverage remains historical. QA emulator remains stopped.'}
    write(OUT / 'Verification_Summary.json', summary)
    write(ROOT / 'Verification/Evidence/Native_Source_Checkpoint.json', {
        'utc': summary['utc'], 'status': summary['status'], 'scope': summary['scope'],
        'source_checkpoint': 61, 'installed_checkpoint': 62,
        'review': 'Codex_Handoff/Documentation/62_HOME_LIVES_ANDROID_INSTALL.md',
        'summary': 'Verification/Evidence/HomeLivesAndroid/Verification_Summary.json',
        'source_sha256': summary['source_sha256'], 'android_apk_sha256': artifact['sha256'],
        'android_apk_matches_current_source': True})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__': main()
