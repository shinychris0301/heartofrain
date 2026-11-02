"""Validate the targeted Shop containment review without launching Unity or Android."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/ShopBounds'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    frozen = read(OUT/'Source_SHA256.json')['files']
    inventory = {p.relative_to(ROOT).as_posix() for folder in ['Unity/Assets','Unity/Packages','Unity/ProjectSettings'] for p in (ROOT/folder).rglob('*') if p.is_file()}
    assert inventory == set(frozen) and all(sha(ROOT/p)==h for p,h in frozen.items()), 'Built Unity source changed'
    baseline = read(OUT.parent/'NoMovesR3/Source_SHA256.json')['files']
    delta = {p for p,h in frozen.items() if baseline.get(p)!=h}
    assert delta == {
        'Unity/Assets/HeartOfTheRain/App/NoMovesDesign/NoMovesPage.cs',
        'Unity/Assets/HeartOfTheRain/Verification/NoMovesDeviceProbe.cs',
        'Unity/Assets/HeartOfTheRain/Verification/Editor/NoMovesPlayReview.cs',
    }, delta
    native = read(OUT/'NativePlay.json')
    assert native['status']=='PASS_NO_MOVES_NATIVE_PLAY' and not native['error'] and native['layouts']==175
    assert read(OUT/'NativePlay_Process.json')['exitCode']==0 and read(OUT/'Prefab_Process.json')['exitCode']==0
    artifact = read(OUT/'APK_Artifact.json')
    build = read(OUT/'Android_Build.json')
    assert build['status']=='PASS_ANDROID_DEVELOPMENT_BUILD' and build['errors']==0
    assert read(OUT/'AndroidBuild_Process.json')['exitCode']==0
    assert 'Errors: 0' in (OUT/'Build_Import_Audit.txt').read_text('utf-8-sig')
    assert artifact['zipalign4KiBPass'] and artifact['developmentSignatureVerifies'] and artifact['elf16KiBLoadSegmentsPass']
    assert artifact['sha256']==sha(ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk')==read(OUT/'APK_Packaging.json')['afterSHA256']
    device = read(OUT/'Android/Summary.json')
    assert device['status']=='PASS_ANDROID_SHOP_BOUNDS' and device['apk_sha256']==artifact['sha256']
    assert device['data_unchanged'] and device['ordinary_startup_data_unchanged'] and device['before']==device['after']
    cases = {c['scenario']:c for c in device['cases']}
    assert set(cases)=={'insufficient','shop','shop_bounds'}
    assert all(c['report']['status']=='PASS_ANDROID_NO_MOVES' and not c['report']['error'] and c['report']['boardPreserved'] and c['report']['coins']==700 and c['report']['lives']==5 for c in cases.values())
    assert cases['shop_bounds']['actual_ui_swipes']==1 and cases['shop_bounds']['actual_ui_taps']==1 and cases['shop_bounds']['report']['boundsChecks']>=70
    visual = read(OUT/'Visual_Review.json')
    assert visual['status']=='REVIEWED_NATIVE_AND_ANDROID_SHOP_BOUNDS'
    assert all(sha(OUT/p)==h for p,h in visual['artifactSHA256'].items())
    result = {
        'status':'PASS_TARGETED_SHOP_BOUNDS','utc':datetime.now(timezone.utc).isoformat(),
        'source_checkpoint':71,'source_sha256':sha(OUT/'Source_SHA256.json'),'apk_sha256':artifact['sha256'],
        'native_checks':native['checks'],'layouts':175,'android_cases':3,'android_scroll_checks':cases['shop_bounds']['report']['boundsChecks'],
        'qa_data_unchanged':True,'main_apk_updated':False,
        'scope':'Fresh native Editor connected/layout checks and QA Android containment, real swipe to final coin pack, Back and low-balance routing. Checkpoint70 transaction/model regression evidence is historical; only presentation and verification code changed.',
        'limits':['QA LDPlayer only; main retains deployment64.','Real coin purchases and production continuation remain unavailable.','No physical-device or full-campaign certification.'],
    }
    for path in [OUT/'Summary.json',OUT.parent/'Verification_Summary.json']:
        path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    checkpoint = {'utc':result['utc'],'status':result['status'],'source_checkpoint':71,'installed_checkpoint':64,'qa_installed_checkpoint':71,'source_sha256':result['source_sha256'],'review':'Codex_Handoff/Documentation/71_SHOP_CONTENT_BOUNDS_REVIEW.md','summary':'Verification/Evidence/ShopBounds/Summary.json','android_apk_sha256':artifact['sha256'],'android_apk_matches_current_source':True,'main_installed_apk_matches_current_source':False,'scope':result['scope']}
    (OUT.parent/'Native_Source_Checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':
    main()
