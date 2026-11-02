"""Validate the crate optimization, keeping device timing and native proof distinct."""
import hashlib,json,statistics
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/CrateBurst'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n','utf-8')
def pct(values,p):return sorted(values)[min(len(values)-1,int(len(values)*p))]

def main():
    source=read(OUT/'Source_SHA256.json')['files'];assert all(sha(ROOT/p)==h for p,h in source.items()),'Inputs changed'
    baseline=read(ROOT/'Verification/Evidence/LoadingBar/Source_SHA256.json')['files']
    changed=sorted(p for p,h in baseline.items() if source[p]!=h)
    assert set(changed)=={'Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPresentation.cs','Unity/Assets/HeartOfTheRain/M46/Runtime/M46AtlasBank.cs','Unity/Assets/HeartOfTheRain/M47/Runtime/GameplayScreen.cs','Unity/Assets/HeartOfTheRain/Verification/Editor/NativeVerification.cs'},changed
    before=read(OUT/'Before/Report.json');after=read(OUT/'After/Report.json');play=read(OUT/'NativePlay.json')
    assert all(r['status']=='PASS_NATIVE_CRATE_BURST' and not r['error'] and len(r['rows'])==15 for r in [before,after])
    assert after['pressureProtection'] and after['noCrateSkip']
    for old,new in zip(before['rows'],after['rows']):
        assert all(old[k]==new[k] for k in ['name','turnHash','finalHash','poseHash'])
        assert new['playbackCrateCreates']==0 and new['reserve']>=new['peakDraws']
    assert play['status']=='PASS_CRATE_BURST_PLAYBACK' and len(play['rows'])==6 and not play['errors']
    assert all(r['renderersCreated']==r['crateSpritesCreated']==0 and r['poolReady']==r['poolEnd'] for r in play['rows'])
    warm=read(OUT/'Warmup_Checks.json');general=read(OUT/'General_Checks.json')
    assert warm['status']=='PASS_NATIVE_PRESENTATION_WARMUP' and not warm['failures']
    assert general['status']=='PASS_NATIVE_EDITOR_CHECKS' and general['failed']==0
    for name in ['After','NativePlay','Warmup','Checks']:
        p=read(OUT/(name+'_Process.json'));assert p['exitCode']==0 and not p['timedOut']
    artifact=read(OUT/'APK_Artifact.json');build=read(OUT/'Android_Build.json')
    assert sha(ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk')==artifact['sha256']
    assert all(artifact[k] for k in ['developmentSignatureVerifies','zipalign4KiBPass','elf16KiBLoadSegmentsPass'])
    assert build['status']=='PASS_ANDROID_DEVELOPMENT_BUILD' and build['errors']==0 and not build['error']
    bp=read(OUT/'AndroidBuild_Process.json');assert bp['exitCode']==0 and not bp['timedOut']
    groups={};android_turn_hashes={}
    for variant in ['baseline_1','candidate_1','candidate_2','baseline_2']:
        d=OUT/'Android'/variant;r=read(d/'Report.json');install=read(d/'Installation.json')
        assert r['status']=='PASS_CRATE_BURST_PLAYBACK' and not r['errors'] and len(r['rows'])==6
        assert install['apk_sha256']==install['installed_apk_sha256']==artifact['sha256'] and install['before']==install['after'] and install['runtime_errors']==0
        for i,row in enumerate(r['rows']):
            key=row['name'].rsplit('_',1)[0];group=groups.setdefault(key,{'baseline':{'rows':[],'frames':[]},'candidate':{'rows':[],'frames':[]}})[variant.split('_')[0]]
            group['rows'].append(row);group['frames'] += [f for f in r['frames'] if f['phase']==i]
            native=next(x for x in after['rows'] if x['name']==key)
            # Serialized effect floats can differ between Mono/Windows and
            # IL2CPP/ARM. Compare raw turns within the same Android build;
            # logical final snapshots also match the native fixture exactly.
            assert row['turnHash']==android_turn_hashes.setdefault(key,row['turnHash']) and row['finalHash']==native['finalHash']
            if variant.startswith('candidate'):assert row['renderersCreated']==row['crateSpritesCreated']==0
    comparisons=[]
    for name,group in groups.items():
        result={'name':name}
        for variant,data in group.items():
            frames=data['frames'];rows=data['rows'];intervals=[f['intervalMs'] for f in frames]
            result[variant]={'turns':len(rows),'frames':len(frames),'p95_render_ms':pct([f['renderMs'] for f in frames],.95),'p95_sample_ms':pct([f['sampleMs'] for f in frames],.95),'p95_interval_ms':pct(intervals,.95),'worst_interval_ms':max(intervals),'intervals_above_41_7ms':sum(v>41.7 for v in intervals),'renderers_created':sum(r['renderersCreated'] for r in rows),'crate_sprites_created':sum(r['crateSpritesCreated'] for r in rows),'median_preparation_seconds':statistics.median(r['preparationSeconds'] for r in rows),'worst_command_ms':max(r['commandMs'] for r in rows)}
        comparisons.append(result)
    write(OUT/'Performance_Comparison.json',{'scope':'Same APK, QA LDPlayer, baseline/candidate/candidate/baseline process order, six timed fixtures per process, no screenshots or recording. Control skips crate sprite/draw preparation and damage-aware renderer capacity; both branches prefetch crate texture pages through current common-resource discovery. Elapsed CPU/frame intervals include scheduling; native Editor signatures verify exact semantics. Not an exact checkpoint-43 dependency/startup reproduction, sustained-60-fps or physical-device claim.','groups':comparisons})
    main=read(OUT/'Android/Main_Installation.json');assert main['status']=='PASS_INSTALLED_DATA_PRESERVED_LAUNCHED' and main['apk_sha256']==main['installed_apk_sha256']==artifact['sha256'] and main['data_unchanged'] and main['before']==main['after'] and not main['active_attempts_before'] and main['runtime_errors']==0 and main['foreground']
    vr=read(OUT/'Android/visual_review/Report.json');vi=read(OUT/'Android/visual_review/Installation.json')
    assert vr['status']=='PASS_CRATE_BURST_PLAYBACK' and not vr['errors'] and len(vr['rows'])==6 and vi['apk_sha256']==artifact['sha256'] and vi['before']==vi['after'] and vi['runtime_errors']==0
    visual=read(OUT/'Visual_Review.json');assert len(visual['frames'])==9 and all(sha(OUT/p)==h for p,h in visual['frames'].items())
    summary={'utc':datetime.now(timezone.utc).isoformat(),'status':'PASS_CRATE_BURST_FIX_INSTALLED','scope':'Targeted crate presentation preparation, deterministic native stress replays and same-APK Android control measurements; installed on main LDPlayer with data preserved. Not whole-campaign or physical-device performance certification.','source_inputs':len(source),'source_sha256':sha(OUT/'Source_SHA256.json'),'changed_existing_inputs':changed,'native_sampler_checks':after['checks'],'native_play_turns':6,'native_warmup_checks':warm['checks'],'native_general_checks':general['passed'],'android_timed_turns':24,'apk_sha256':artifact['sha256'],'apk_bytes':artifact['bytes'],'data_unchanged':True,'collector_sha256':sha(Path(__file__))}
    write(OUT/'Verification_Summary.json',summary)
    write(ROOT/'Verification/Evidence/Native_Source_Checkpoint.json',{'utc':summary['utc'],'status':summary['status'],'scope':summary['scope'],'review':'Codex_Handoff/Documentation/44_CRATE_BURST_PERFORMANCE_REVIEW.md','summary':'Verification/Evidence/CrateBurst/Verification_Summary.json','source_sha256':summary['source_sha256'],'android_apk_sha256':artifact['sha256'],'android_apk_matches_current_source':True,'installed_checkpoint':44,'preceding_suites_rerun':False})
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
