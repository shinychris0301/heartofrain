"""Bind fixed-density native/device controls to the deployed artifact."""
import hashlib,json,statistics
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Verification/Evidence/ObstacleDensity'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n','utf-8')
def percentile(values,p):return sorted(values)[min(len(values)-1,int(len(values)*p))]
def timing(frames):
    assert frames
    metrics={}
    for name in ['renderMs','sampleMs','bodySampleMs','effectsSampleMs','sortMs','updateMs','intervalMs']:
        values=[f[name] for f in frames];metrics[name]={'median':statistics.median(values),'p95':percentile(values,.95),'max':max(values)}
    metrics['otherRenderMs']={'median':statistics.median(f['renderMs']-f['sampleMs'] for f in frames),'p95':percentile([f['renderMs']-f['sampleMs'] for f in frames],.95)}
    return {'frames':len(frames),'intervals_above_41_7ms':sum(f['intervalMs']>41.7 for f in frames),'metrics':metrics}

def main():
    source=read(OUT/'Source_SHA256.json')['files'];assert all(sha(ROOT/p)==h for p,h in source.items()),'Frozen inputs changed'
    baseline=read(ROOT/'Verification/Evidence/CrateBurst/Source_SHA256.json')['files'];changed=sorted(p for p,h in baseline.items() if source[p]!=h)
    assert set(changed)=={'Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPresentation.cs','Unity/Assets/HeartOfTheRain/M47/Runtime/GameplayScreen.cs','Unity/Assets/HeartOfTheRain/M48/Runtime/AdvancedObstaclePresentationPure.cs'},changed
    before=read(OUT/'Before/Report.json');after=read(OUT/'After/Report.json');native=read(OUT/'NativePlay.json');pixels=read(OUT/'Native_Pixels.json');reg=read(OUT/'Regression_Checks.json')
    assert before['status']==after['status']=='PASS_NATIVE_OBSTACLE_DENSITY' and not before['error'] and not after['error'] and len(after['rows'])==5
    for a,b in zip(before['rows'],after['rows']):assert all(a[k]==b[k] for k in ['count','originX','originY','turnHash','finalHash','poseHash','cleared','damage'])
    assert native['status']=='PASS_OBSTACLE_DENSITY_PLAYBACK' and not native['errors'] and len(native['rows'])==10
    assert all(r['renderersCreated']==r['crateSpritesCreated']==0 and r['cleared']==r['crates'] and r['poolReady']==r['poolEnd']==1182 for r in native['rows'])
    assert pixels['status']=='PASS_NATIVE_PIXEL_PARITY' and pixels['changedPixels']==0
    assert reg['status']=='PASS_NATIVE_DENSITY_REGRESSION' and not reg['error'] and reg['damageQueries']==2860 and reg['sortCases']==32 and reg['realReplays']==15
    warm=read(OUT/'Warmup_Checks.json');general=read(OUT/'General_Checks.json')
    assert warm['status']=='PASS_NATIVE_PRESENTATION_WARMUP' and not warm['failures'] and general['status']=='PASS_NATIVE_EDITOR_CHECKS' and general['failed']==0
    assert all((r['originX'],r['originY'])==(5,5) for r in after['rows'])
    for name in ['Before','After','Regression','NativePlay','Warmup','Checks']:
        r=read(OUT/(name+'_Process.json'));assert r['exitCode']==0 and not r['timedOut']
    artifact=read(OUT/'APK_Artifact.json');build=read(OUT/'Android_Build.json');bp=read(OUT/'AndroidBuild_Process.json');pack=read(OUT/'APK_Packaging.json')
    assert sha(ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk')==artifact['sha256']==pack['afterSHA256']
    assert all(artifact[k] for k in ['developmentSignatureVerifies','zipalign4KiBPass','elf16KiBLoadSegmentsPass'])
    assert build['status']=='PASS_ANDROID_DEVELOPMENT_BUILD' and build['errors']==0 and not build['error'] and bp['exitCode']==0 and not bp['timedOut'] and not pack['changedNonSignatureEntries'] and pack['sameSignerCertificate']
    groups={};turns={};qa_initial=None
    for variant in ['baseline_1','candidate_1','candidate_2','baseline_2']:
        folder=OUT/'Android'/variant;r=read(folder/'Report.json');install=read(folder/'Installation.json')
        assert r['status']=='PASS_OBSTACLE_DENSITY_PLAYBACK' and not r['errors'] and len(r['rows'])==10
        assert install['apk_sha256']==install['installed_apk_sha256']==artifact['sha256'] and install['before']==install['after'] and install['runtime_errors']==0
        if qa_initial is None:qa_initial=install['before']
        assert install['before']==qa_initial
        for i,row in enumerate(r['rows']):
            assert (row['originX'],row['originY'])==(5,5)
            count=row['crates'];assert count in [1,8,16,32,45] and row['cleared']==count and row['poolReady']==row['poolEnd']==1182
            assert row['renderersCreated']==row['crateSpritesCreated']==0
            assert row['turnHash']==turns.setdefault(count,row['turnHash']) and row['finalHash']==next(n['finalHash'] for n in after['rows'] if n['count']==count)
            group=groups.setdefault(count,{}).setdefault(variant.split('_')[0],{'rows':[],'frames':[],'core':[],'matched':[]})
            frames=[f for f in r['frames'] if f['phase']==i];core=[f for f in frames if f['crateDraws']>=4*count];assert len(core)>10
            matched=[f for f in frames if f['step']=='powerFall' and 2.3<=f['playbackAge']<=2.8];assert len(matched)>=5
            group['rows'].append(row);group['frames']+=frames;group['core']+=core;group['matched']+=matched
    comparisons=[]
    for count,variants in sorted(groups.items()):
        row={'count':count}
        for variant,data in variants.items():
            rows=data['rows'];assert len(rows)==4
            row[variant]={'turns':4,'whole_turn':timing(data['frames']),'debris_window':timing(data['core']),'matched_peak_window':timing(data['matched']),'model_ms':[r['modelMs'] for r in rows],'accept_ms':[r['acceptMs'] for r in rows],'median_preparation_seconds':statistics.median(r['preparationSeconds'] for r in rows)}
        comparisons.append(row)
    comparison={'scope':'Same final development APK on QA LDPlayer, 40 measured turns; two repetitions at 1/8/16/32/45 one-layer crates per process. Fixed cloned level-26 geometry, seed, colors, swap (4,5)/(5,5), effect origin (5,5), Double Orb and 1182-slot reserve. One untimed 45-crate warm-up per process. Process order baseline/candidate/candidate/baseline; second pair reverses density order. Preparation is enabled in both variants; controls restore the prior damage/debris/sort/texture/rotation work. Transform caching is shared in this same-APK control. Elapsed CPU includes scheduling; other host/emulator activity was not held constant. Main was found closed after controls, so these observations are not a controlled physical-device frame-rate guarantee. No screenshots/video/report serialization inside timing. Not physical-device certification.',
        'matched_window_definition':'Same gameplay clock window at every density: powerFall age 2.3 through 2.8 seconds. Chosen from exploratory traces before the final fixed-origin device run; captures mass breakup without using a density-dependent threshold.',
        'window_definition':'Whole turn retains all measured frames. Debris window uses frames showing at least four crate effect sprites per configured crate, the same rule for both variants. This compares substantial simultaneous debris rather than the long idle tail; other tile/power effects remain present.',
        'groups':comparisons}
    write(OUT/'Performance_Comparison.json',comparison)
    qa=read(OUT/'Android/QA_Restoration.json');assert qa['status']=='PASS_QA_DATA_PRESERVED_STOPPED' and qa['first_before_equals_last_after']
    main=read(OUT/'Android/Main_Installation.json');assert main['status']=='PASS_INSTALLED_DATA_PRESERVED_LAUNCHED' and main['apk_sha256']==main['installed_apk_sha256']==artifact['sha256'] and main['before']==main['after'] and main['runtime_errors']==0 and not main['active_attempts_before'] and main['foreground']
    visual=read(OUT/'Visual_Review.json');assert all(sha(OUT/p)==h for p,h in visual['frames'].items())
    summary={'utc':datetime.now(timezone.utc).isoformat(),'status':'PASS_OBSTACLE_DENSITY_FIX_INSTALLED','scope':'Fixed-density CPU/frame analysis and optimization, exact native poses and camera pixel parity, native regression/lifecycle checks, same-APK Android controls, main LDPlayer replacement installation with data preserved. Not whole-campaign or physical-device certification.','source_inputs':len(source),'source_sha256':sha(OUT/'Source_SHA256.json'),'changed_existing_inputs':changed,'native_density_cases':5,'native_play_turns':10,'native_pixel_differences':0,'native_regression_checks':reg['checks'],'native_warmup_checks':warm['checks'],'native_general_checks':general['passed'],'android_timed_turns':40,'apk_sha256':artifact['sha256'],'apk_bytes':artifact['bytes'],'data_unchanged':True,'collector_sha256':sha(Path(__file__))}
    write(OUT/'Verification_Summary.json',summary)
    write(ROOT/'Verification/Evidence/Native_Source_Checkpoint.json',{'utc':summary['utc'],'status':summary['status'],'scope':summary['scope'],'review':'Codex_Handoff/Documentation/45_OBSTACLE_DENSITY_PERFORMANCE_REVIEW.md','summary':'Verification/Evidence/ObstacleDensity/Verification_Summary.json','source_sha256':summary['source_sha256'],'android_apk_sha256':artifact['sha256'],'android_apk_matches_current_source':True,'installed_checkpoint':45,'preceding_suites_rerun':False})
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
