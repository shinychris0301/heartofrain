"""Collect current follow-up evidence, with explicit APK/source/freshness guards."""
import csv,datetime as dt,hashlib,json,subprocess
from pathlib import Path
from measure_fluidity import ROOT
OUT=ROOT/'Verification/Evidence';BRANCH=OUT/'PowerWarmup'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def passed(report):
    assert report['status'].startswith('PASS'),report['status']
    assert not report.get('failures') and not report.get('errors') and not report.get('error')
def time(value):return dt.datetime.fromisoformat(value.replace('Z','+00:00'))

def run():
    apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk';digest=sha(apk)
    source=read(BRANCH/'Player_Source_SHA256.json');assert len(source['files'])>=4273
    assert source['apk_sha256']==digest and all(sha(ROOT/n)==v for n,v in source['files'].items())
    changes=read(BRANCH/'Changed_Player_Inputs.json')
    assert set(changes['changed'])=={'Unity/Assets/HeartOfTheRain/M46/Runtime/M46AtlasBank.cs','Unity/Assets/HeartOfTheRain/M47/Runtime/GameplayScreen.cs','Unity/Assets/HeartOfTheRain/Verification/FluidityDeviceProbe.cs'} and not changes['removed']
    native=read(BRANCH/'Native_Checks.json');passed(native)
    assert native['initialPool']>=405 and native['retainedPool']>=605
    checkpoints={name:read(BRANCH/'Native_Checkpoints'/f'{name}.json') for name in ['GameplayPerfChecks','M70Checks','M70R2Checks','Checks','PlaySmoke']}
    for report in checkpoints.values():passed(report)
    for name in ['Android_Build.json','Integrity.json','APK_Orientation.json','APK_Payloads.json']:
        report=read(BRANCH/name);passed(report)
        if name.startswith('APK_'):assert report['apk_sha256']==digest
    packaging=read(BRANCH/'APK_Packaging.json');passed(packaging)
    assert packaging['afterSHA256']==digest and packaging['sameSignerCertificate'] and not packaging['changedNonSignatureEntries']
    controls={}
    for folder,variant in [('Baseline','baseline_focus'),('WarmOnly','warm_focus'),('CacheOnly','cache_focus'),('Candidate','candidate_focus'),('CandidateRepeat','candidate_focus'),('BaselineRepeat','baseline_focus')]:
        install=read(BRANCH/folder/'Installation.json');report=read(BRANCH/folder/'Measurement.json')
        assert install['sha256']==digest and install['variant']==report['variant']==variant
        assert report['status']=='RECORDED_NATIVE_FLUIDITY' and not report['errors'] and report['platform']=='Android'
        assert time(report['utc'])>=time(install['utc']) and len(report['phases'])==7
        assert len(report['frameSamples'])>1000
        assert all(p['synchronousTextureLoads']==0 for p in report['phases'])
        if folder in ['WarmOnly','Candidate','CandidateRepeat']:assert all(p['poolAtReady']>=405 and p['poolAtReady']==p['poolAtEnd'] for p in report['phases'])
        controls[folder]={'installation':install,'phases':report['phases']}
    assert len({c['installation']['serial'] for c in controls.values()})==1
    comparison=read(BRANCH/'Performance_Comparison.json');assert len(comparison['rows'])==12
    assert all(row['apk_sha256']==digest and row['repeats']==3 for row in comparison['rows'])
    touch=read(BRANCH/'Touch/Report.json');visual=read(BRANCH/'Visual_Review.json');ui=read(BRANCH/'UI_Review.json')
    for report in [touch,visual,ui]:passed(report);assert report['apk_sha256']==digest
    assert len(touch['cases'])==8 and all(c['status']=='PASS_NATIVE_DEVICE_GAMEPLAY_AUDIT' and not c['failures'] for c in touch['cases'])
    assert next(c for c in touch['cases'] if c['mode']=='MixedChain')['chained']
    starting=read(BRANCH/'Starting/Report.json');starting_visual=read(BRANCH/'Starting_Visual_Review.json')
    for report in [starting,starting_visual]:passed(report);assert report['apk_sha256']==digest
    assert {c['mode'] for c in starting['cases']}=={'GrantIntro','GrantNoIntro','FailureRetry'}
    assert all(c['status']=='PASS_NATIVE_DEVICE_M70R2_CREATION' and c['gateHeld'] and not c['failures'] for c in starting['cases'])
    assert next(c for c in starting['cases'] if c['mode']=='FailureRetry')['failureChecked']
    for report in [visual,ui]:
        assert report['artifactSHA256'] and all(sha(BRANCH/n)==v for n,v in report['artifactSHA256'].items())
    regression=read(BRANCH/'LDPlayer/Regression.json');passed(regression)
    install=read(BRANCH/'LDPlayer/Installation.json')
    assert install['sha256']==digest and time(regression['utc'])>=time(install['utc'])
    assert regression['boards']==50 and regression['height']>regression['width']
    frame_review=read(BRANCH/'Device_Frame_Manifest_Review.json');passed(frame_review);assert frame_review['apk_sha256']==digest
    previous_frames=set(read(OUT/'GameplayAudit/LDPlayer/Regression.json')['frames'])
    assert previous_frames-set(regression['frames'])<={'L1_Tool3_Effect_2.png'}
    assert len(regression['frames'])==frame_review['manifestedFrames']>=303
    assert set(frame_review['frameSHA256'])==set(regression['frames'])
    assert all(sha(BRANCH/'LDPlayer'/n)==v for n,v in frame_review['frameSHA256'].items())
    assert all((BRANCH/'LDPlayer'/n).is_file() for n in regression['frames'])
    installations=[read(BRANCH/n) for n in ['MainInstance_Final_Installation.json','QA_Final_Installation.json']]
    assert {r['serial'] for r in installations}=={'127.0.0.1:5555','127.0.0.1:5557'}
    for report in installations:passed(report);assert report['apk_sha256']==digest and report['preferences_status']=='PASS_IDENTICAL_PREFERENCE_FILES'
    prefs=read(BRANCH/'Test_Span_Preferences.json');passed(prefs);assert prefs['before']==prefs['after']
    candidate=[r for r in comparison['rows'] if r['folder'].startswith('Candidate')]
    summary={'status':'PASS_VERIFICATION_WITH_OPEN_RELEASE_GATES','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'current_evidence_branch':'PowerWarmup','unity':'2022.3.62f3','apk':{'path':str(apk),'sha256':digest,'bytes':apk.stat().st_size},'changed_player_inputs':changes,'native_warmup':native,'native_runtime_checks':checkpoints,'controlled_performance':comparison,'performance_controls':controls,'current_android_regression':{k:regression[k] for k in ['status','utc','checks','boards','actions','labels','clips','width','height','scope']},'current_android_frames':len(regression['frames']),'actual_android':touch,'starting_power_android':starting,'starting_power_visual_review':starting_visual,'visual_review':visual,'selected_ui_review':ui,'installations':installations,'preferences_preservation':prefs,'historical_evidence':{'branch':'GameplayAudit','apk_sha256':changes['previousAPK'],'scope':'Earlier full model audit and Match Villains v7307 captures retain their original date/APK scope. No fresh competitor parity claim.'},'remaining':[f"Heavy combos still have emulator long frames; candidate maximum {max(r['worstIntervalMs'] for r in candidate):.2f}ms. Sustained60fps and physical-device performance remain unverified.",'Physical Android/iOS performance, sensor and long-session checks','Human balance and exhaustive natural play','Durable profile/inventory and idempotent settlement; production billing/social/live services']}
    summary['device_frame_manifest_review']=frame_review
    for path in [BRANCH/'Verification_Summary.json',OUT/'Verification_Summary.json']:path.write_text(json.dumps(summary,indent=2)+'\n')
    status=subprocess.run(['git','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT,check=True,capture_output=True,text=True).stdout
    with (OUT/'Changed_Files.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(['status','path','scope'])
        for line in status.splitlines():
            path=line[3:];current=path in changes['changed'] or any(n in path for n in ['PowerWarmup','power_warmup','PresentationWarmup','26_POWER_PRESENTATION'])
            writer.writerow([line[:2],path,'Current presentation follow-up' if current else 'Existing project work or shared verification/documentation'])
    print(json.dumps({'status':summary['status'],'apk_sha256':digest,'androidChecks':regression['checks'],'boards':50,'touchCases':8,'nativeWarmupChecks':native['checks']},indent=2))

if __name__=='__main__':run()
