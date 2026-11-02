"""Collect targeted continuation evidence without rerunning Unity or a device."""
import hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/RepeatMoves'

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source = read(OUT / 'Source_SHA256.json')['files']
    inventory = {p.relative_to(ROOT).as_posix() for folder in ['Unity/Assets', 'Unity/Packages', 'Unity/ProjectSettings'] for p in (ROOT/folder).rglob('*') if p.is_file()}
    assert inventory == set(source), 'Unity input inventory changed after build'
    assert all(sha(ROOT/p) == h for p,h in source.items()), 'Unity input changed after build'
    suites = {n: read(OUT/(n+'.json')) for n in ['Transactions','NativePlay','Checks','ProfileChecks','PlaySmoke','TimingChecks','IndividualFallChecks','RepeatTransactions']}
    assert all(r['status'].startswith('PASS') and not r.get('error') and not r.get('errors') for r in suites.values())
    assert suites['Transactions']['boards'] == 350 and suites['Transactions']['restarts'] == 6
    assert suites['NativePlay']['layouts'] == 125
    assert suites['RepeatTransactions']['restarts']==18 and suites['RepeatTransactions']['purchases']==5
    assert read(OUT/'Android_Build.json')['status'] == 'PASS_ANDROID_DEVELOPMENT_BUILD'
    artifact = read(OUT/'APK_Artifact.json')
    assert artifact['zipalign4KiBPass'] and artifact['developmentSignatureVerifies'] and artifact['elf16KiBLoadSegmentsPass']
    assert artifact['sha256'] == sha(ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk') == read(OUT/'APK_Packaging.json')['afterSHA256']
    device = read(OUT/'Android/Summary.json')
    assert device['status'] == 'PASS_ANDROID_REPEAT_MOVES' and device['apk_sha256'] == artifact['sha256']
    assert device['data_unchanged'] and device['ordinary_startup_data_unchanged'] and device['before'] == device['after']
    assert {r['scenario'] for r in device['cases']} == {'offer','insufficient','shop','prepared','committed','repeat','repeat_insufficient','end'}
    assert all(c['report']['status']=='PASS_ANDROID_NO_MOVES' and not c['report']['error'] for c in device['cases'])
    cases={c['scenario']:c for c in device['cases']}
    assert cases['repeat']['actual_ui_taps']==2 and cases['repeat']['report']['playedMoves']==5
    assert all(cases[n]['report']['purchases']==3 and cases[n]['report']['coins']==350 and cases[n]['report']['lives']==5 for n in ['repeat','prepared','committed'])
    assert cases['repeat_insufficient']['report']['purchases']==2 and cases['repeat_insufficient']['report']['coins']==710
    assert cases['end']['report']['lives']==4
    package = read(OUT.parent/'NoMovesR2/Package_Review.json')
    registry_path = 'Unity/Assets/HeartOfTheRain/App/UIClarity/Editor/UIClarityRegistry.json'
    registry = read(ROOT/registry_path)['assets']
    old = json.loads(subprocess.check_output(['git','show','HEAD:'+registry_path],cwd=ROOT))['assets']
    assert all(e in registry for e in old) and len(registry)==59
    art = ROOT/'Unity/Assets/HeartOfTheRain/App/NoMovesDesign'
    for name,h in package['imported'].items():
        if name.endswith('.png'): assert sha(art/name)==h, name
    for entry in package['verified_imported_sprites']:
        meta=(art/'Art'/(entry['name']+'.meta')).read_text('utf-8-sig')
        assert re.search(r'^guid: ([a-f0-9]{32})$',meta,re.M)[1] == entry['guid']
    assert 'Errors: 0' in (OUT/'Build_Import_Audit.txt').read_text('utf-8-sig')
    guids={}
    for p in (ROOT/'Unity/Assets').rglob('*.meta'):
        m=re.search(r'^guid: ([a-f0-9]{32})$',p.read_text('utf-8-sig'),re.M)
        if m:
            assert m[1] not in guids, f'Duplicate GUID: {p} / {guids.get(m[1])}'
            guids[m[1]]=str(p)
    visual=read(OUT/'Visual_Review.json')
    assert visual['status']=='REVIEWED_NATIVE_AND_ANDROID_REPEAT_MOVES'
    assert all(sha(OUT/p)==h for p,h in visual['artifactSHA256'].items())
    counts={n:len(r['checks']) if isinstance(r.get('checks'),list) else r.get('checks') for n,r in suites.items()}
    result={'status':'PASS_TARGETED_REPEAT_MOVES','utc':datetime.now(timezone.utc).isoformat(),'source_checkpoint':69,'source_sha256':sha(OUT/'Source_SHA256.json'),'apk_sha256':artifact['sha256'],'native_checks':counts,'layouts':125,'board_roundtrips':350,'disk_cut_restarts':24,'repeat_purchase_restarts':18,'repeat_purchases_one_attempt':5,'android_cases':8,'qa_data_unchanged':True,'main_apk_updated':False,'scope':'Native Editor transactions/layouts and QA Android continuation with memory-only scenario profiles and actual ADB button taps. Ordinary QA startup preserves real saved data.','limits':['Development-only +5 moves / 900 coins per purchase, repeat purchases enabled. Production continuation quotes remain disabled.','In-level Shop preserves the board but cannot sell coins until real store and authoritative wallet integration exist.','No physical-device, production server, IAP, campaign-wide or all-feature certification.','Main LDPlayer retains deployment64; the QA instance has source69.']}
    for p in [OUT/'Summary.json', OUT.parent/'Verification_Summary.json']:
        p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    checkpoint={'utc':result['utc'],'status':result['status'],'source_checkpoint':69,'installed_checkpoint':64,'qa_installed_checkpoint':69,'source_sha256':result['source_sha256'],'review':'Codex_Handoff/Documentation/69_REPEAT_MOVE_PURCHASE_REVIEW.md','summary':'Verification/Evidence/RepeatMoves/Summary.json','android_apk_sha256':artifact['sha256'],'android_apk_matches_current_source':True,'main_installed_apk_matches_current_source':False,'scope':result['scope']}
    (OUT.parent/'Native_Source_Checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__': main()
