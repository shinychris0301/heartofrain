"""Bind the current source checkpoint to the rebuilt APK and main LDPlayer install."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/HomeHeaderAndroid'

def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))

def main():
    source=read(OUT/'Source_SHA256.json')
    assert source['files']==read('Verification/Evidence/HomeHeaderAvatar/Source_SHA256.json')['files']
    assert all(sha(p)==h for p,h in source['files'].items()),'Verified source/configuration changed'
    apk='Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    artifact=read(OUT/'APK_Artifact.json')
    assert artifact['sha256']==sha(apk) and artifact['bytes']==(ROOT/apk).stat().st_size
    assert artifact['developmentSignatureVerifies'] and artifact['zipalign4KiBPass'] and artifact['elf16KiBLoadSegmentsPass']
    build=read(OUT/'Android_Build.json');process=read(OUT/'AndroidBuild_Process.json')
    assert build['status']=='PASS_ANDROID_DEVELOPMENT_BUILD' and build['errors']==0 and not build['error']
    assert process['exitCode']==0 and not process['timedOut']
    assert datetime.fromisoformat(build['utc'].replace('Z','+00:00'))>=datetime.fromisoformat(process['startedUtc'])
    install=read(OUT/'Main_Installation.json')
    assert install['status']=='PASS_INSTALLED_DATA_PRESERVED_LAUNCHED'
    assert install['apk_sha256']==artifact['sha256']==install['installed_apk_sha256']
    assert install['preferences_before']==install['preferences_after_install'] and install['player_saves_before']==install['player_saves_after_install']
    assert install['pid'] and install['foreground_activity'] and not install['fatal_log_signatures']
    assert install['campaign_unchanged_after_touch_smoke'] and install['existing_preferences_unchanged_except_new_default_profile'] and not install['final_fatal_log_signatures']
    assert install['touch_observation']['profile_opened'] and install['touch_observation']['profile_closed_to_home']
    visual=read(OUT/'Visual_Review.json')
    assert visual['status']=='PASS_REVIEWED_LDPLAYER_HOME_PROFILE'
    assert all(sha(OUT/p)==h for p,h in visual['frames'].items())
    summary={'utc':datetime.now(timezone.utc).isoformat(),'status':'PASS_REBUILT_INSTALLED_LDPLAYER',
             'scope':'Current development APK built with Unity 2022.3.62f3, signature/alignment/ELF checked, replacement-installed and launched on the active main LDPlayer instance. Normal saved data retained. Targeted Home/Profile visual observation, not full campaign regression or physical-device certification.',
             'source_checkpoint':'36_HOME_HEADER_AVATAR_REVIEW.md','source_sha256':sha(OUT/'Source_SHA256.json'),
             'apk_sha256':artifact['sha256'],'apk_bytes':artifact['bytes'],'serial':install['serial'],
             'build_warnings':build['warnings'],'data_unchanged_after_launch':install['data_unchanged_after_launch'],
             'campaign_unchanged_after_touch_smoke':True,'new_default_appearance_preference_saved_during_touch_smoke':True,
             'installation_sha256':sha(OUT/'Main_Installation.json'),'visual_review_sha256':sha(OUT/'Visual_Review.json'),
             'runtime_code_changed':False,'qa_instance_updated':False,'collector_sha256':sha(Path(__file__)),
             'limitations':'Main LDPlayer only; QA instance was stopped. No store publishing, real account/backend activation or exhaustive gameplay/device testing.'}
    (OUT/'Verification_Summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    (ROOT/'Verification/Evidence/Native_Source_Checkpoint.json').write_text(json.dumps({
        'utc':summary['utc'],'status':summary['status'],'scope':summary['scope'],
        'review':'Codex_Handoff/Documentation/37_HOME_HEADER_ANDROID_INSTALL.md',
        'summary':'Verification/Evidence/HomeHeaderAndroid/Verification_Summary.json',
        'source_sha256':summary['source_sha256'],'android_apk_sha256':artifact['sha256'],
        'preceding_source_review':'Verification/Evidence/HomeHeaderAvatar/Verification_Summary.json',
        'preceding_suites_rerun':False},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ['status','serial','apk_bytes','apk_sha256','data_unchanged_after_launch']}))

if __name__=='__main__':
    main()
