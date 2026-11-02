"""Validate the targeted importer correction without claiming an Android fix."""
import hashlib
import json
import re
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/ProfileClarity'
def read(path):return json.loads((ROOT/path).read_text('utf-8-sig'))
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def write(path,value):(ROOT/path).write_text(json.dumps(value,indent=2)+'\n','utf-8')

def main():
    before=read(OUT/'Before/Native_Review.json');after=read(OUT/'After/Native_Review.json')
    assert before['frames']==after['frames'] and len(after['frames'])==14
    for phase,report in [('Before',before),('After',after)]:
        process=read(OUT/phase/'Native_Process.json')
        assert report['status']=='PASS_NATIVE_PROFILE_CLARITY' and not report['error'] and len(report['textures'])==13
        assert process['exitCode']==0 and not process['timedOut']
        assert datetime.fromisoformat(report['utc'].replace('Z','+00:00'))>=datetime.fromisoformat(process['startedUtc'])
    baseline=read('Verification/Evidence/LaunchIntegration/Source_SHA256.json')['files']
    changed=sorted(p for p,h in baseline.items() if sha(p)!=h)
    expected={'Unity/'+t['path']+'.meta' for t in after['textures']}|{'Verification/Run-UnityVerification.ps1'}
    assert set(changed)==expected,changed
    for old,new in zip(before['textures'],after['textures']):
        assert old['path']==new['path'] and old['guid']==new['guid'] and old['width']==new['width'] and old['height']==new['height']
        assert old['mips']==1 and old['filter']=='Bilinear' and new['mips']>1 and new['filter']=='Trilinear'
        assert not new['readable'] and not new['packed']
        meta=(ROOT/'Unity'/(new['path']+'.meta')).read_text('utf-8')
        assert re.search(r'^guid: '+new['guid']+'$',meta,re.M)
    assert len(before['graphics'])==len(after['graphics'])
    for old,new in zip(before['graphics'],after['graphics']):
        for field in ['frame','name','texture','sourceWidth','sourceHeight','physicalWidth','physicalHeight','white','preserveAspect','packed']:
            assert old[field]==new[field],(field,old,new)
    visual=read(OUT/'Visual_Review.json')
    assert set(visual['frames'])=={f'{phase}/{file}' for phase in ['Before','After'] for file in after['frames']}
    assert all(sha(OUT/path)==digest for path,digest in visual['frames'].items())
    added={p.relative_to(ROOT).as_posix() for p in (ROOT/'Unity/Assets').rglob('*') if p.is_file()}-set(baseline)
    assert added=={'Unity/Assets/HeartOfTheRain/App/Profile/Editor/ProfileClarityTools.cs',
                   'Unity/Assets/HeartOfTheRain/App/Profile/Editor/ProfileClarityTools.cs.meta',
                   'Unity/Assets/HeartOfTheRain/Verification/Editor/ProfileClarityReview.cs',
                   'Unity/Assets/HeartOfTheRain/Verification/Editor/ProfileClarityReview.cs.meta'},added
    files={p:sha(p) for p in sorted(set(baseline)|added)}
    frozen=OUT/'Source_SHA256.json'
    if frozen.exists():assert read(frozen)['files']==files,'Verified clarity source changed'
    write(frozen,{'scope':'Exact importer/source configuration for the native Editor before/after review; not bound to a new APK.','files':files})
    apk='Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    assert sha(apk)=='afa3358260924d7c85bfeaa7f877827aa2bea0a4867974f662add98a7dbaac29'
    summary={'utc':datetime.now(timezone.utc).isoformat(),'status':'PASS_PROFILE_CLARITY_EDITOR_CHECKPOINT','scope':after['scope'],
        'package_sha256':'4bf9549341315014a13fcc1a66767d92d8e65b93c4fff3aa03d0c36cf46103e2',
        'pngs_byte_identical_to_package':22,'pngs_replaced':0,'modified_texture_importers':13,'preserved_original_guids':True,
        'native_checks':before['checks']+after['checks'],'reviewed_frames':28,'source_inputs':len(files),
        'texture_memory_editor_before_bytes':before['textureBytes'],'texture_memory_editor_after_bytes':after['textureBytes'],
        'texture_memory_editor_delta_bytes':after['textureBytes']-before['textureBytes'],
        'graphics_geometry_tint_aspect_unchanged':True,'changed_existing_inputs':changed,'added_inputs':sorted(added),
        'apk_sha256_unchanged':sha(apk),'runtime_profile_code_unchanged':True,
        'collector_sha256':sha(Path(__file__)),
        'limitations':'Editor sampling/visual baseline, not Android/device acceptance. Uncompressed mipmapped reference textures increase memory; Editor counters are not device GPU residency. Larger portrait/control originals and mobile compression/memory/performance validation remain open.'}
    write(OUT/'Verification_Summary.json',summary)
    write(ROOT/'Verification/Evidence/Native_Source_Checkpoint.json',{'utc':summary['utc'],'status':summary['status'],
        'scope':summary['scope'],'review':'Codex_Handoff/Documentation/42_PROFILE_CLARITY_R2_REVIEW.md',
        'summary':'Verification/Evidence/ProfileClarity/Verification_Summary.json','source_sha256':sha(frozen),
        'android_apk_sha256':sha(apk),'android_apk_matches_current_source':False,'installed_checkpoint':39,'preceding_suites_rerun':False})
    print(json.dumps({k:summary[k] for k in ['status','native_checks','reviewed_frames','source_inputs','texture_memory_editor_delta_bytes']}))

if __name__=='__main__':main()
