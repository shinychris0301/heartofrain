"""Collect Daily Gift evidence only when the current APK/source/device checks agree."""
import datetime as dt,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Verification/Evidence';BRANCH=OUT/'DailyGift'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def passed(report):
    assert report['status'].startswith('PASS'),report['status']
    assert not report.get('failures') and not report.get('errors') and not report.get('error')
def run():
    apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk';digest=sha(apk);source=read(BRANCH/'Player_Source_SHA256.json')
    assert source['apk_sha256']==digest and all(sha(ROOT/n)==v for n,v in source['files'].items()),'Built player inputs changed'
    changes=read(BRANCH/'Changed_Player_Inputs.json');assert not changes['removed'] and len(changes['changed'])==6
    checks={name:read(BRANCH/'Native_Checkpoints'/f'{name}.json') for name in ['ProfileChecks','DailyGiftPlay','Checks','PlaySmoke','M70Checks','M70R2Checks','WarmupChecks']}
    for report in checks.values():passed(report)
    assert checks['ProfileChecks']['checks']>=10099 and checks['DailyGiftPlay']['checks']>=51
    artifact=read(BRANCH/'APK_Artifact.json');assert artifact['sha256']==digest and artifact['developmentSignatureVerifies'] and artifact['zipalign4KiBPass'] and artifact['elf16KiBLoadSegmentsPass']
    for name in ['Android_Build.json','Integrity.json','APK_Orientation.json','APK_Payloads.json','APK_Packaging.json']:
        report=read(BRANCH/name);passed(report)
        if name.startswith('APK_') and name!='APK_Packaging.json':assert report['apk_sha256']==digest
    packaging=read(BRANCH/'APK_Packaging.json');assert packaging['afterSHA256']==digest and packaging['sameSignerCertificate'] and not packaging['changedNonSignatureEntries']
    device=read(BRANCH/'Device/Report.json');passed(device);assert device['apk_sha256']==digest
    assert {c['mode'] for c in device['cases']}=={'Tap','Restart','StartAttempt','Recover','RecoverAgain','Auto','WonRestart'}
    assert device['preferences_before']==device['preferences_after'] and device['player_saves_before']==device['player_saves_after']
    for case in device['cases']:passed(case)
    assert next(c for c in device['cases'] if c['mode']=='Tap')['actual_android_taps']==2
    profiles=read(BRANCH/'Device_Profiles.json');passed(profiles);assert profiles['apk_sha256']==digest and profiles['preferences_before']==profiles['preferences_after'] and profiles['original_wm_size']==profiles['restored_wm_size']
    assert {(c['width'],c['height']) for c in profiles['cases']}=={(320,568),(768,1024)}
    visual=read(BRANCH/'Visual_Review.json');passed(visual);assert visual['apk_sha256']==digest and visual['artifactSHA256']
    assert all(sha(BRANCH/n)==v for n,v in visual['artifactSHA256'].items())
    regression=read(BRANCH/'LDPlayer/Regression.json');install=read(BRANCH/'LDPlayer/Installation.json');passed(regression)
    assert install['sha256']==digest and regression['boards']==50 and regression['height']>regression['width']
    assert dt.datetime.fromisoformat(regression['utc'].replace('Z','+00:00'))>=dt.datetime.fromisoformat(install['utc'])
    assert all((BRANCH/'LDPlayer'/n).is_file() for n in regression['frames'])
    frames=read(BRANCH/'Device_Frame_Manifest.json');passed(frames);assert frames['apk_sha256']==digest and set(frames['frameSHA256'])==set(regression['frames']) and all(sha(BRANCH/'LDPlayer'/n)==v for n,v in frames['frameSHA256'].items())
    selected=read(BRANCH/'Regression_Visual_Review.json');passed(selected);assert selected['apk_sha256']==digest and all(sha(BRANCH/n)==v for n,v in selected['artifactSHA256'].items())
    installations=[read(BRANCH/n) for n in ['MainInstance_Final_Installation.json','QA_Final_Installation.json']]
    for report in installations:passed(report);assert report['apk_sha256']==digest and report['preferences_status']=='PASS_IDENTICAL_PREFERENCE_FILES'
    assert {r['serial'] for r in installations}=={'127.0.0.1:5555','127.0.0.1:5557'}
    launch_visual=read(BRANCH/'Installation_Visual_Review.json');passed(launch_visual);assert launch_visual['apk_sha256']==digest and all(sha(BRANCH/n)==v for n,v in launch_visual['artifactSHA256'].items())
    summary={'status':'PASS_DAILY_GIFT_DEVELOPMENT_REVIEW_WITH_OPEN_RELEASE_GATES','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'current_evidence_branch':'DailyGift','unity':'2022.3.62f3','apk':{'path':str(apk),'sha256':digest,'bytes':apk.stat().st_size},'changed_player_inputs':changes,'native_checks':checks,'android_daily_gift':device,'portrait_profiles':profiles,'visual_review':visual,'android_regression':{k:regression[k] for k in ['status','utc','checks','boards','actions','labels','clips','width','height','scope']},'manifested_regression_frames':len(regression['frames']),'installations':installations,'remaining':['Real authenticated reward service, trusted UTC, account/cloud recovery and production authority integration; release claims stay unavailable.','Life regeneration/continues and exact board resume; approved interruption is one loss on reopening.','Wellworks and Rain Cup remain demo content, pending separate component work/review.','Local checksum/backup is corruption recovery, not anti-cheat or a server wallet; last-known-good backup may roll back one commit.','Physical-device performance, human balance/native-language review, billing/social/store release gates.']}
    summary['frame_manifest']=frames;summary['selected_regression_visual_review']=selected;summary['installation_visual_review']=launch_visual
    for path in [BRANCH/'Verification_Summary.json',OUT/'Verification_Summary.json']:path.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'status':summary['status'],'apk_sha256':digest,'transaction_checks':checks['ProfileChecks']['checks'],'android_checks':regression['checks']}))
if __name__=='__main__':run()
