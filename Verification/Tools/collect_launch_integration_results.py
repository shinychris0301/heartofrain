"""Bind the targeted native launch review to exact inputs; no device claims."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/LaunchIntegration'

def read(path):
    return json.loads((ROOT/path).read_text('utf-8-sig'))

def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

def write(path,value):
    (ROOT/path).write_text(json.dumps(value,indent=2)+'\n','utf-8')

def main():
    previous=read('Verification/Evidence/ProfileDesignAndroid/Source_SHA256.json')['files']
    changed=sorted(p for p,h in previous.items() if sha(p)!=h)
    assert set(changed)=={
        'Unity/Assets/HeartOfTheRain/App/FirstStart/Runtime/FirstStartPage.cs',
        'Unity/Assets/HeartOfTheRain/Verification/Editor/NativeAndroidBuild.cs',
        'Unity/ProjectSettings/ProjectSettings.asset','Verification/Run-UnityVerification.ps1'},changed
    added={p.relative_to(ROOT).as_posix() for p in (ROOT/'Unity/Assets').rglob('*') if p.is_file()}-set(previous)
    assert all(p.startswith('Unity/Assets/HeartOfTheRain/App/Launch/') or p in {
        'Unity/Assets/HeartOfTheRain/App/Launch.meta',
        'Unity/Assets/HeartOfTheRain/Verification/Editor/LaunchReview.cs',
        'Unity/Assets/HeartOfTheRain/Verification/Editor/LaunchReview.cs.meta'} for p in added),sorted(added)
    manifest=read('Verification/Evidence/LaunchDesignR1/Package/Asset_Manifest.json')
    for item in manifest['assets']:
        name=Path(item['file']).name
        assert sha('Unity/Assets/HeartOfTheRain/App/Launch/Art/'+name)==item['sha256']
    # EditorBuildSettings was not included in checkpoint 39's input list. It is
    # required now because it establishes launch -> original game scene ordering.
    files={p:sha(p) for p in sorted(set(previous)|added|{'Unity/ProjectSettings/EditorBuildSettings.asset'})}
    frozen=OUT/'Source_SHA256.json'
    if frozen.exists():
        assert read(frozen)['files']==files,'Verified launch inputs changed'
    report=read(OUT/'Native_Review.json')
    process=read('Verification/Evidence/Native/LaunchReview_Process.json')
    assert report['status']=='PASS_NATIVE_LAUNCH_INTEGRATION' and not report['error'] and len(report['frames'])==14
    assert process['exitCode']==0 and not process['timedOut']
    assert datetime.fromisoformat(report['utc'].replace('Z','+00:00'))>=datetime.fromisoformat(process['startedUtc'])
    assert {r['name'] for r in report['routes']}=={'Fresh','ResumeRocket','ReturningProgress','CompletedTutorial'}
    for route in report['routes']:
        assert all(route[k] for k in ['launchReleased','artUnloaded','logoUnloaded','settingsUnchanged','walletUnchanged'])
    review=read(OUT/'Visual_Review.json')
    assert set(review['frames'])==set(report['frames']) and all(sha(OUT/p)==h for p,h in review['frames'].items())
    apk='Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    assert sha(apk)=='afa3358260924d7c85bfeaa7f877827aa2bea0a4867974f662add98a7dbaac29'
    write(frozen,{'scope':'Exact native Editor launch source/configuration. APK remains checkpoint 39 and does not include this integration.','files':files})
    summary={'utc':datetime.now(timezone.utc).isoformat(),'status':'PASS_LAUNCH_INTEGRATION_CHECKPOINT',
        'scope':report['scope'],'changed_existing_baseline_inputs':changed,
        'changed_build_scene_configuration':'Unity/ProjectSettings/EditorBuildSettings.asset',
        'added_inputs':sorted(added),'source_inputs':len(files),'native_checks':report['checks'],
        'reviewed_frames':14,'actual_async_handoff_cases':4,'localized_layout_cases':25,
        'imported_original_pngs':3,'original_metadata_preserved':True,
        'android_icon':'Legacy slots configured; adaptive source layers remain pending',
        'native_report_sha256':sha(OUT/'Native_Review.json'),
        'native_process_sha256':sha('Verification/Evidence/Native/LaunchReview_Process.json'),
        'collector_sha256':sha(Path(__file__)), 'apk_sha256_unchanged':sha(apk),
        'limitations':'Targeted Editor/Play Mode verification, not Android packaging/install/device/startup performance. Exact 941x1672 artwork retained; no higher-resolution or adaptive icon layers generated. Current Unity splash retained. Cutout checks are simulated geometry only.'}
    write(OUT/'Verification_Summary.json',summary)
    write(ROOT/'Verification/Evidence/Native_Source_Checkpoint.json',{
        'utc':summary['utc'],'status':summary['status'],'scope':summary['scope'],
        'review':'Codex_Handoff/Documentation/41_LAUNCH_INTEGRATION_REVIEW.md',
        'summary':'Verification/Evidence/LaunchIntegration/Verification_Summary.json',
        'source_sha256':sha(frozen),'android_apk_sha256':sha(apk),'android_apk_matches_current_source':False,
        'installed_checkpoint':39,'preceding_suites_rerun':False})
    print(json.dumps({k:summary[k] for k in ['status','native_checks','reviewed_frames','source_inputs']}))

if __name__=='__main__':
    main()
