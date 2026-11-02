"""Collect only fresh, hash-bound Wellworks evidence; visual review is explicit."""
from pathlib import Path
import datetime as dt,hashlib,html,json
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Verification/Evidence/Wellworks'
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run():
    apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk';digest=sha(apk);freeze=read('Player_Source_SHA256.json');assert freeze['apk_sha256']==digest
    assert all(sha(ROOT/n)==h for n,h in freeze['files'].items());actual={p.as_posix() for p in (ROOT/'Unity/Assets').rglob('*') if p.is_file() and 'Editor' not in p.parts};assert actual=={(ROOT/n).as_posix() for n in freeze['files']}
    rows=[]
    for mode,expected in [('WellworksChecks',11046),('WellworksPlay',13),('ProfileChecks',10099),('DailyGiftPlay',51),('Checks',530)]:
        r=read('Native_Checkpoints/'+mode+'.json');assert r['status'].startswith('PASS') and not r.get('failures');count=r.get('checks');count=count if isinstance(count,int) else len(count);assert count>=expected;rows.append({'mode':mode,'checks':count,'status':r['status']})
    assert read('Integrity.json')['status']=='PASS_STATIC_INTEGRITY_WITH_DOCUMENTED_REPAIRS';assert read('APK_Packaging.json')['afterSHA256']==digest
    artifact=read('APK_Artifact.json');assert artifact['sha256']==digest and artifact['zipalign4KiBPass'] and artifact['developmentSignatureVerifies'] and artifact['elf16KiBLoadSegmentsPass']
    device=read('Device/Report.json');assert device['apk_sha256']==digest and device['status']=='PASS_NATIVE_ANDROID_WELLWORKS_REQUIRES_VISUAL_REVIEW';assert [c['mode'] for c in device['cases']]==['Tap','Restart','Auto'];assert sum(c['actual_android_taps'] for c in device['cases'])==3
    assert all(c['status']=='PASS_NATIVE_WELLWORKS' and not c['failures'] for c in device['cases']);assert device['preferences_before']==device['preferences_after'] and device['player_saves_before']==device['player_saves_after']
    profiles=read('Device_Profiles.json');assert profiles['apk_sha256']==digest and profiles['preferences_before']==profiles['preferences_after'] and profiles['original_wm_size']==profiles['restored_wm_size'] and len(profiles['cases'])==2
    visual=read('Visual_Review.json');assert visual['apk_sha256']==digest and visual['status']=='PASS_NATIVE_WELLWORKS_VISUAL_REVIEW';assert all(sha(OUT/f['path'])==f['sha256'] for f in visual['frames'])
    required={'Device/'+c['mode']+'/'+name for c in device['cases'] for name in c['frames']}
    for name in ['Compact','Tablet']:
        extra=read(name+'/Report.json');assert extra['apk_sha256']==digest and extra['player_saves_before']==extra['player_saves_after']
        required.update(name+'/Restart/'+frame for c in extra['cases'] for frame in c['frames']);required.update([name+'/After_Scroll.png',name+'/After_Back.png'])
    required.update(['Main_Home.png','QA_Home.png']);assert required=={f['path'] for f in visual['frames']}
    for name in ['Main','QA']:
        installation=read(name+'_Installation.json');assert installation['apk_sha256']==digest and installation['status']=='PASS_APK_INSTALLED_DATA_PRESERVED';assert installation['preferences_before']==installation['preferences_after'] and installation['player_saves_before']==installation['player_saves_after']
    final=read('Final_Runtime_Status.json');assert all(s['apk_sha256']==digest and s['pid'] for s in final['instances']) and len(final['instances'])==2
    result={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'PASS_WELLWORKS_DEVELOPMENT_REVIEW','apk_sha256':digest,'apk_bytes':apk.stat().st_size,'player_inputs':len(freeze['files']),'native':rows,'android_cases':len(device['cases']),'android_checks':sum(c['checks'] for c in device['cases']),'actual_android_taps':3,'portrait_profiles':profiles['cases'],'reviewed_native_frames':len(visual['frames']),'installations':'Both LDPlayer instances, replacement install; real profiles/preferences preserved','limits':['Local development rewards; release claims disabled pending production authority.','Campaign progress in the Wellworks fixtures is simulated through the attempt service; not a new natural-play campaign pass.','No fresh full Android campaign regression, physical-device/FPS or long-session certification.','Rain Cup remains demo content.'],'implementation':'Codex_Handoff/Documentation/28_WELLWORKS_REVIEW.md'}
    (OUT/'Verification_Summary.json').write_text(json.dumps(result,indent=2)+'\n');(ROOT/'Verification/Evidence/Verification_Summary.json').write_text(json.dumps(result,indent=2)+'\n')
    h=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wellworks review</title><style>body{margin:0;background:#132d42;color:#f5f0e4;font:16px system-ui}main{max-width:1160px;margin:auto;padding:28px}a{color:#b9e0ff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));gap:18px}figure{margin:0;padding:12px;background:#203e53;border-radius:12px}img{width:100%;height:430px;object-fit:contain}figcaption{padding:10px 0;font-size:14px}p{line-height:1.6}code{overflow-wrap:anywhere}</style><main><h1>Wellworks</h1><p>Permanent Chapter 1 first-clear milestones. Replays do not advance progress; stars are preserved. Claims and inventory are committed before reward animation.</p><p>Approved provisional schedule: 10 → 100 coins; 20 → Rocket + Bomb; 30 → 150 coins + Hammer; 40 → Orb; 50 → 250 coins + Golden Seeker.</p>']
    h.append('<p>'+str(sum(r['checks'] for r in rows))+' native assertions/checks across the listed suites; '+str(result['android_checks'])+' targeted Android checks, three actual taps, restart recovery and two additional portrait sizes. Ordinary player saves and preferences preserved.</p>')
    h.append('<p><a href="Verification_Summary.json">Verification summary</a> · <a href="../../../Codex_Handoff/Documentation/28_WELLWORKS_REVIEW.md">Implementation and limits</a></p><p><code>APK SHA-256 '+digest+'</code></p><div class="grid">')
    for f in visual['frames']:h.append('<figure><a href="'+html.escape(f['path'])+'"><img loading="lazy" src="'+html.escape(f['path'])+'"></a><figcaption>'+html.escape(f['note'])+'</figcaption></figure>')
    h.append('</div><p>'+html.escape(' '.join(result['limits']))+'</p></main></html>');(OUT/'Comparison.html').write_text('\n'.join(h),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':run()
