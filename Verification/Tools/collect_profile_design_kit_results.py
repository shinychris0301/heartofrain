"""Collect the design-kit source review; retain the separate deployed-APK checkpoint."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/ProfileDesignKit'

def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

def write(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def main():
    previous=read('Verification/Evidence/HomeHeaderAndroid/Source_SHA256.json')['files']
    changed=sorted(p for p,h in previous.items() if sha(p)!=h)
    base='Unity/Assets/HeartOfTheRain/App/Profile/'
    assert set(changed)=={base+'Editor/ProfileReview.cs',base+'Resources/HeartOfTheRainProfile/Config.asset',base+'Runtime/ProfileAssets.cs',base+'Runtime/ProfileData.cs',base+'Runtime/ProfilePage.cs',base+'Runtime/ProfileText.cs','Verification/Run-UnityVerification.ps1'},changed
    added={p.relative_to(ROOT).as_posix() for p in (ROOT/'Unity/Assets').rglob('*') if p.is_file()}-set(previous)
    art=base+'Art/DesignKitR1'
    editor='Unity/Assets/HeartOfTheRain/Verification/Editor/ProfileDesignKitReview.cs'
    manifest=read(OUT/'Asset_Manifest.json')
    imports=[a for a in manifest['assets'] if a['origin']=='new_generated' or a['id'] in ('Progress_Track','Progress_Fill')]
    expected={art+'.meta',editor,editor+'.meta'}
    for asset in imports:
        path=art+'/'+asset['id']+'.png';expected.update([path,path+'.meta']);assert sha(path)==asset['sha256'],'Imported art differs from package: '+path
    assert added==expected,sorted(added-expected)
    files={p:sha(p) for p in sorted(set(previous)|added)}
    frozen=OUT/'Source_SHA256.json'
    if frozen.exists():
        assert read(frozen)['files']==files,'Verified source changed'
    report=read(OUT/'Native_Review.json');process=read('Verification/Evidence/Native/ProfileDesignKit_Process.json')
    assert report['status']=='PASS_NATIVE_PROFILE_DESIGN_KIT' and not report['error'] and len(report['frames'])==18
    assert process['exitCode']==0 and not process['timedOut']
    assert datetime.fromisoformat(report['utc'].replace('Z','+00:00'))>=datetime.fromisoformat(process['startedUtc'])
    review=read(OUT/'Visual_Review.json')
    assert set(review['frames'])==set(report['frames']) and all(sha(OUT/p)==h for p,h in review['frames'].items())
    apk='Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    assert sha(apk)=='e9309dde06f86031057f981120ad2e92be29b14d738f53c41c57f06d6afb3cc0'
    write('Source_SHA256.json',{'scope':'Exact source/configuration for the targeted design-kit native Editor review; not yet bound to a rebuilt APK.','files':files})
    summary={'utc':datetime.now(timezone.utc).isoformat(),'status':'PASS_PROFILE_DESIGN_KIT_CHECKPOINT','scope':report['scope'],
             'package_sha256':'80570acb20c9bcd338f77f13895632f7653e7545df9f2d333b64f404a417da24',
             'changed_existing_inputs':changed,'added_inputs':sorted(added),'native_checks':report['checks'],'reviewed_frames':18,
             'imported_pngs':12,'new_art_pngs':10,'reused_existing_pngs':10,'existing_metadata_preserved':True,
             'source_inputs':len(files),'native_report_sha256':sha(OUT/'Native_Review.json'),'native_process_sha256':sha('Verification/Evidence/Native/ProfileDesignKit_Process.json'),
             'collector_sha256':sha(Path(__file__)),'apk_sha256_unchanged':sha(apk),
             'limitations':'Targeted native Editor verification and review-memory fixtures. No new APK, Android/device/compression/performance validation or full campaign/service regression. New texture imports are uncompressed references pending mobile evaluation.'}
    write('Verification_Summary.json',summary)
    captions=['Village / Rainkeeper Gold','Lantern / Lantern Sapphire','Twilight / Garden Ivory','Six frames (scrolled collection)','Three banners (scrolled collection)','Spanish stats','French stats','German stats','Russian stats','320×480: single column, top','320×480: single column, bottom','Tablet stats (page scrolled)','Tall phone: frames','Tall phone: stats','320×568: single column','Live fixture update: level 50 / 88 stars','Zero-denominator guard','Injected unloaded-state guard']
    cards=''.join(f'<figure><figcaption>{caption}</figcaption><a href="{file}"><img src="{file}" alt="Native Profile design-kit review" loading="lazy"></a></figure>' for caption,file in zip(captions,report['frames']))
    (OUT/'Comparison.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Profile Design Kit R1</title><style>body{background:#101b2b;color:#eee;font:16px system-ui;margin:30px auto;padding:0 20px;max-width:1500px}.frames{display:flex;flex-wrap:wrap;gap:20px}figure{margin:0 0 24px;width:min(320px,100%)}img{width:100%;height:auto}figcaption{margin-bottom:8px}a{color:#a9d8ff}</style><h1>Profile Design Kit R1 | native integration</h1><p>Three revised center-cover banners, three additional decorative frames alongside the three classics, normalized frame bounds, and layered live stats cards. The existing Profile shell, Home Header R2 square footprint and Level button are preserved. Earlier source artwork and GUIDs remain intact.</p><p>18 inspected native Unity 2022.3.62f3 Play Mode UGUI captures cover five languages and five portrait sizes. Programmatic selections/serialization reload, save-failure handling, native text fitting, live model presentation, progress clamps, zero denominator and injected unloaded-state checks pass. The 12/1/11-of-50/24 values are isolated campaign fixtures; live values are read from Home state.</p><p>Camera-rendered native UGUI, not device screenshots or physical taps. Narrow layouts scroll vertically; some captures intentionally show the bottom of a collection/page. The readiness fault is an injected UI condition, not a backend outage test. No APK was rebuilt or installed. Uncompressed reference imports still need Android memory/compression evaluation.</p><div class="frames">'''+cards+'</div></html>',encoding='utf-8')
    (ROOT/'Verification/Evidence/Native_Source_Checkpoint.json').write_text(json.dumps({'utc':summary['utc'],'status':summary['status'],'scope':summary['scope'],
        'review':'Codex_Handoff/Documentation/38_PROFILE_DESIGN_KIT_REVIEW.md','summary':'Verification/Evidence/ProfileDesignKit/Verification_Summary.json',
        'source_sha256':sha(OUT/'Source_SHA256.json'),'preceding_deployment':'Verification/Evidence/HomeHeaderAndroid/Verification_Summary.json',
        'preceding_suites_rerun':False,'android_apk_sha256_unchanged':sha(apk)},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ['status','native_checks','reviewed_frames','source_inputs']}))

if __name__=='__main__':
    main()
