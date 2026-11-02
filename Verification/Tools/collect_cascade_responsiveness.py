"""Bind cascade verification to its source/APK; keep historical reports intact."""
import hashlib,json,statistics
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/CascadeResponsiveness'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    before,after=read(OUT/'Before.json'),read(OUT/'After.json')
    assert before['status']==after['status']=='PASS_NATIVE_CASCADE_TIMING'
    assert len(before['rows'])==len(after['rows'])==350 and not after['errors']
    assert all((a['name'],a['turnHash'],a['finalHash'])==(b['name'],b['turnHash'],b['finalHash']) for a,b in zip(before['rows'],after['rows']))
    source=read(OUT/'Source_SHA256.json');assert all(sha(ROOT/p)==v for p,v in source['files'].items()),'Source changed since build freeze'
    current={str(p.relative_to(ROOT)).replace('\\','/') for part in ['Unity/Assets','Unity/Packages','Unity/ProjectSettings'] for p in (ROOT/part).rglob('*') if p.is_file()}
    assert current==set(source['files']),'Unity input inventory changed after build'
    reports={n:read(OUT/(n+'.json')) for n in ['TimingChecks','IndividualFallChecks','FallChecks','M70R2Checks','SwapChecks','Checks','PlaySmoke','NativePlay']}
    assert all(r['status'].startswith('PASS') for r in reports.values())
    assert read(OUT/'Android_Build.json')['status']=='PASS_ANDROID_DEVELOPMENT_BUILD'
    artifact=read(OUT/'APK_Artifact.json');apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    assert sha(apk)==artifact['sha256']==read(OUT/'APK_Packaging.json')['afterSHA256']
    device=read(OUT/'Android/measure/Report.json');install=read(OUT/'Android/measure/Installation.json')
    visual=read(OUT/'Android/visual/Report.json');visual_install=read(OUT/'Android/visual/Installation.json')
    assert device['status']==visual['status']=='PASS_CASCADE_PLAYBACK'
    assert install['data_unchanged'] and visual_install['data_unchanged']
    assert install['apk_sha256']==visual_install['apk_sha256']==artifact['sha256']
    assert len(device['rows'])==6 and len(visual['rows'])==1 and not device['errors']
    native=reports['NativePlay']['rows'];assert len(native)==6
    assert all((a['name'],a['finalHash'],a['matches'])==(b['name'],b['finalHash'],b['matches']) and abs(a['scheduledSeconds']-b['scheduledSeconds'])<.00001 for a,b in zip(native,device['rows']))
    raw_differences=[a['name'] for a,b in zip(native,device['rows']) if a['turnHash']!=b['turnHash']]
    gaps=[]
    for row in device['rows'][:3]:
        for a,b in zip(row['phases'],row['phases'][1:]):
            if a['label']=='Match and refill' and b['label']=='Match and refill':
                gap=b['clock']-a['clock']-a['lastContact'];assert abs(gap)<.001
                gaps.append(gap)
    assert len(gaps)>=12,'Natural repeated cascades were not exercised'
    for row in device['rows'][:3]:
        assert row['wallSeconds']<row['scheduledSeconds']+.6,'Unexpected real cascade slowdown'
    visual_review=read(OUT/'Visual_Review.json')
    assert visual_review['status']=='REVIEWED_NATIVE_ANDROID_SEQUENCE'
    assert all(sha(OUT/p)==v for p,v in visual_review['artifactSHA256'].items())
    result={'status':'PASS_TARGETED_CASCADE_VERIFICATION','utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(OUT/'Source_SHA256.json'),'apk_sha256':artifact['sha256'],'model_turns_unchanged':350,'native_timing_checks':after['checks'],'frame_simulation_median_wall_over_schedule':{phase:{fps:statistics.median(r['wall'+fps]/r['seconds'] for r in report['rows']) for fps in ['15','30','60']} for phase,report in [('before',before),('after',after)]},'actual_android':device['rows'],'actual_native_play':native,'zero_extra_cascade_wait_transitions':len(gaps),'qa_data_unchanged':True,'owner_apk_updated':False,'limits':['Main instance retains its existing APK and active attempt; new APK verified on the dedicated QA instance only.','Editor/native clock simulations are separate from actual Android wall measurements.','Different boards and obstacles; no competitor pixel/physics identity claim.','No physical-device, shipping memory, all-features or production-backend certification.']}
    result['cross_platform_raw_turn_hash_differences']=raw_differences
    result['native_checks_by_suite']={name:(len(r['checks']) if isinstance(r.get('checks'),list) else r.get('checks',len(r.get('rows',[])))) for name,r in reports.items()}
    result['cross_platform_comparison_scope']='All six final model snapshots are byte-identical between Editor and Android, with equal match counts and schedules within 10 microseconds. Raw turns also serialize floating-point presentation plans; their byte hashes differ in two power fixtures. The exact differing fields were not exported; cross-backend raw byte identity is not certified. All 350 before/after native raw turn hashes are identical.'
    (OUT/'Summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (OUT.parent/'Verification_Summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    checkpoint={'utc':result['utc'],'status':result['status'],'source_checkpoint':67,'installed_checkpoint':64,'qa_installed_checkpoint':67,'source_sha256':result['source_sha256'],'review':'Codex_Handoff/Documentation/67_CASCADE_RESPONSIVENESS_REVIEW.md','summary':'Verification/Evidence/CascadeResponsiveness/Summary.json','android_apk_sha256':artifact['sha256'],'android_apk_matches_current_source':True,'main_installed_apk_matches_current_source':False,'scope':'Checkpoint67 source/APK verified natively and on dedicated QA LDPlayer; main deployment64 was not replaced.'}
    (OUT.parent/'Native_Source_Checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n',encoding='utf-8')
    rows=''.join(f"<tr><td>{r['name']}</td><td>{r['scheduledSeconds']:.3f}</td><td>{r['wallSeconds']:.3f}</td><td>{r['matches']}</td></tr>" for r in device['rows'])
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cascade responsiveness review</title>
<style>body{{background:#121e2d;color:#edf4fa;font:16px/1.55 system-ui,sans-serif;max-width:1120px;margin:auto;padding:24px}}h1,h2{{color:#f5d38c}}a{{color:#9cd9ff}}.videos{{display:flex;gap:24px;flex-wrap:wrap}}article{{flex:1;min-width:240px}}video{{width:100%;max-height:650px;background:#000}}img{{max-width:100%}}table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;border-bottom:1px solid #425064;padding:8px}}button,select{{padding:8px;margin:8px}}code{{overflow-wrap:anywhere}}small{{color:#bdcedd}}</style>
<h1>Fall and cascade responsiveness</h1><p>Checkpoint 67 · Unity 2022.3.62f3 · targeted verification</p>
<p>The fall clock previously discarded elapsed time on ordinary frames. Every refill also held the board for a landing tail, and some goal flights held intermediate phases. Normal frames now follow elapsed time; matches react at contact while landing, break and collection art continues independently.</p>
<p><b>350 model results unchanged.</b> In deterministic 30 fps simulation, the six-match level-four cascade improves from 6.33 to 3.67 seconds. These are simulated playback-clock values, distinct from the actual Android measurements below. One-cell flight remains 141 ms.</p>
<label>Video playback <select onchange="document.querySelectorAll('video').forEach(v=>v.playbackRate=Number(this.value))"><option value="1">1× original speed</option><option value="0.5">0.5× review</option><option value="0.25">0.25× detail</option></select></label>
<div class="videos"><article><h2>Reference: normal match</h2><video controls preload="metadata" src="Reference/MV_NaturalMatch.mp4"></video><p>Installed Match Villains, level 450. Bodies fall while gem fragments remain visible.</p></article><article><h2>Reference: Seeker refill</h2><video controls preload="metadata" src="Reference/MV_SeekerRefill.mp4"></video><p>Refill proceeds during remaining Seeker effects. Different board and mechanics; no physics/pixel identity claim.</p></article><article><h2>Heart of the Rain: six cascades</h2><video controls preload="metadata" src="Android/visual/HR_NaturalCascade.mp4"></video><p>Final APK, isolated live Android GameplayScreen on QA. Unaccelerated playback, 30 fps target. Recording overhead is excluded from the timing table.</p></article></div>
<h2>Actual Android measurements</h2><table><tr><th>Fixture (level / kind / fps target)</th><th>Scheduled seconds</th><th>Actual wall seconds</th><th>Matches</th></tr>{rows}</table>
<p>Kind 0 = normal swap; 21 = Bomb; 8 = Orb/Rocket fixture; 16 = Golden Seeker. Frame targets do not certify sustained device fps. Native renderer fixtures have no campaign attempt or inventory hooks. QA save/preference hashes remain unchanged.</p>
<h2>Selected native frames</h2><p>Reference crops are exact frame details; sheets are labelled contact sheets, not altered game assets.</p><img src="Reference/MV_Natural_Detail.png" alt="Reference fall during remaining fragments"><p><a href="Android/visual/HR_NaturalCascade_Sheet.png">Our final Android sequence contact sheet</a> · <a href="Reference/MV_SeekerRefill_Sheet.png">Reference Seeker contact sheet</a></p>
<p><a href="Summary.json">Final results</a> · <a href="After.json">2,858 native timing checks</a> · <a href="IndividualFallChecks.json">81,325 route checks</a> · <a href="Android/measure/Report.json">Android phase timestamps</a> · <a href="Source_SHA256.json">Frozen Unity inputs</a> · <a href="../../..//Codex_Handoff/Documentation/67_CASCADE_RESPONSIVENESS_REVIEW.md">Review notes</a></p>
<p><small>APK SHA256 <code>{artifact['sha256']}</code>. QA-only installation; main deployment64 remains older. No physical-device, all-feature or production-service certification.</small></p></html>'''
    html=html.replace('../../..//Codex_Handoff','../../../Codex_Handoff')
    (OUT/'Comparison.html').write_text(html,encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['status','model_turns_unchanged','zero_extra_cascade_wait_transitions','qa_data_unchanged']}))
if __name__=='__main__':main()
