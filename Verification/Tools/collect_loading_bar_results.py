"""Bind loading-bar source, native rendering, Android artifact and installation."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/LoadingBar'
def read(path):return json.loads((ROOT/path).read_text('utf-8-sig'))
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def write(path,value):(ROOT/path).write_text(json.dumps(value,indent=2)+'\n','utf-8')

def main():
    source=read(OUT/'Source_SHA256.json')['files'];assert all(sha(p)==h for p,h in source.items()),'Source/configuration changed after native review/build'
    baseline=read('Verification/Evidence/ProfileClarity/Source_SHA256.json')['files']
    changed=sorted(p for p,h in baseline.items() if sha(p)!=h)
    assert set(changed)=={'Unity/Assets/HeartOfTheRain/App/Launch/Runtime/LaunchPage.cs','Unity/Assets/HeartOfTheRain/App/Launch/Runtime/LaunchLayout.cs',
        'Unity/Assets/HeartOfTheRain/App/Launch/Editor/LaunchSetup.cs','Unity/Assets/HeartOfTheRain/App/Launch/Scenes/Launch.unity',
        'Unity/Assets/HeartOfTheRain/Verification/Editor/LaunchReview.cs','Verification/Run-UnityVerification.ps1'},changed
    package=read(OUT/'Package_Review.json')
    for asset in package['assets']:
        assert sha('Unity/Assets/HeartOfTheRain/App/Launch/Art/'+asset['id']+'.png')==asset['sha256']
    native=read(OUT/'Native/Native_Review.json');np=read(OUT/'Native/Native_Process.json')
    assert native['status']=='PASS_NATIVE_LAUNCH_INTEGRATION' and not native['error'] and len(native['frames'])==19 and len(native['bars'])==25 and len(native['routes'])==4
    assert np['exitCode']==0 and not np['timedOut']
    assert datetime.fromisoformat(native['utc'].replace('Z','+00:00'))>=datetime.fromisoformat(np['startedUtc'])
    assert all(abs(b['fillWidth']-b['expectedWidth'])<.01 and b['visible']==(b['progress']>0) for b in native['bars'])
    assert all(all(r[k] for k in ['launchReleased','artUnloaded','logoUnloaded','loadingSkinsUnloaded','settingsUnchanged','walletUnchanged']) for r in native['routes'])
    artifact=read(OUT/'APK_Artifact.json');build=read(OUT/'Android_Build.json');bp=read(OUT/'AndroidBuild_Process.json')
    apk='Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    assert sha(apk)==artifact['sha256'] and (ROOT/apk).stat().st_size==artifact['bytes']
    assert all(artifact[k] for k in ['developmentSignatureVerifies','zipalign4KiBPass','elf16KiBLoadSegmentsPass'])
    assert build['status']=='PASS_ANDROID_DEVELOPMENT_BUILD' and build['errors']==0 and not build['error'] and bp['exitCode']==0 and not bp['timedOut']
    install=read(OUT/'Android/Main_Installation.json')
    assert install['status']=='PASS_INSTALLED_DATA_PRESERVED_LAUNCHED' and install['apk_sha256']==artifact['sha256']==install['installed_apk_sha256']
    assert install['preferences_before']==install['preferences_after_install']==install['preferences_after_launch']
    assert install['player_saves_before']==install['player_saves_after_install']==install['player_saves_after_launch']
    assert install['data_unchanged_after_launch'] and install['pid'] and install['final_foreground_activity']
    assert not install['fatal_log_signatures'] and not install['runtime_error_signatures']
    assert all(install['touch_observation'].values()) and install['startup_recording_observed']
    visual=read(OUT/'Visual_Review.json');assert len(visual['native_frames'])==19 and len(visual['android_frames'])==4
    assert all(sha(OUT/p)==h for group in ['native_frames','android_frames'] for p,h in visual[group].items())
    summary={'utc':datetime.now(timezone.utc).isoformat(),'status':'PASS_LOADING_BAR_REBUILT_INSTALLED',
        'scope':'Native Editor loading states/locales/routing plus rebuilt ARM64 development APK, replacement install, recorded startup and direct Home/Profile/Stats screenshots on main LDPlayer. Saved data preserved; not exhaustive gameplay or physical-device performance certification.',
        'source_inputs':len(source),'source_sha256':sha(OUT/'Source_SHA256.json'),'changed_existing_inputs':changed,
        'native_checks':native['checks'],'native_frames':19,'progress_geometry_cases':25,'routing_cases':4,
        'android_frames_reviewed':4,'black_footer_plate_removed':True,'apk_sha256':artifact['sha256'],'apk_bytes':artifact['bytes'],
        'serial':install['serial'],'data_unchanged':True,'qa_instance_updated':False,'build_warnings':build['warnings'],
        'preceding_source_updates_included':['41 Launch integration and legacy icon','42 Profile clarity R2'],
        'collector_sha256':sha(Path(__file__)),
        'limitations':'Startup frame is decoded from a compressed landscape recording with portrait letterboxing; Home/Profile/Stats are direct 900x1600 screenshots. Another app briefly foregrounded; app restored and taps foreground guarded. Mobile compression/memory/FPS, physical devices, adaptive icons and larger launch master remain open.'}
    write(OUT/'Verification_Summary.json',summary)
    write(ROOT/'Verification/Evidence/Native_Source_Checkpoint.json',{'utc':summary['utc'],'status':summary['status'],'scope':summary['scope'],
        'review':'Codex_Handoff/Documentation/43_LOADING_BAR_ANDROID_REVIEW.md','summary':'Verification/Evidence/LoadingBar/Verification_Summary.json',
        'source_sha256':summary['source_sha256'],'android_apk_sha256':artifact['sha256'],'android_apk_matches_current_source':True,'installed_checkpoint':43,'preceding_suites_rerun':False})
    print(json.dumps({k:summary[k] for k in ['status','native_checks','apk_bytes','apk_sha256','data_unchanged']}))

if __name__=='__main__':main()
