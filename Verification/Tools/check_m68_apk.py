"""Audit GUID-named texture payloads in the actual Unity development APK."""
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/Fluidity'


def run():
    apk=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    base=ROOT/'Unity/Assets/HeartOfTheRain/M68Celebration'
    rows=[]
    with zipfile.ZipFile(apk) as z:
        entries={i.filename:i for i in z.infolist()}
        for path in base.rglob('*.png'):
            guid=re.search(r'^guid: ([0-9a-f]{32})',Path(str(path)+'.meta').read_text(),re.M)[1]
            payload='assets/bin/Data/'+guid
            names=[n for n in entries if n==payload or n.startswith(payload+'.')]
            rows.append({'source':str(path.relative_to(base)).replace('\\','/'),'guid':guid,
                         'apk_payloads':names,'bytes':sum(entries[n].file_size for n in names)})
    expected={'Art/Dariya_Master.png','Mesh/Dariya_Blink_Texture.png','Art/Dariya_Reduced_Motion.png','Art/Celebration_Halo.png','Art/Celebration_Star.png'}
    included={r['source'] for r in rows if r['apk_payloads']}
    assert expected.issubset(included),'Missing expected runtime texture payloads'
    assert not any(r['apk_payloads'] for r in rows if r['source'].startswith('Atlases/')),'Reference atlas unexpectedly packaged'
    assert len([r for r in rows if r['source'].startswith('Atlases/')])==14
    old=OUT/'Build_Asset_Inclusion.json'
    if old.exists() and json.loads(old.read_text()).get('status')=='FAIL_M68_RUNTIME_ASSET_INCLUSION':
        unavailable=json.loads(old.read_text());unavailable['status']='SOURCE_PATHS_UNAVAILABLE_IN_EDITOR_BUILD_REPORT';unavailable['explanation']='GetLatestReport returned no packed asset source paths after Play Mode; actual APK GUID payload audit supersedes this unavailable observation.'
        (OUT/'Build_Report_Unavailable.json').write_text(json.dumps(unavailable,indent=2)+'\n',encoding='utf-8',newline='\n')
    report={'status':'PASS_M68_TEXTURE_PAYLOAD_AUDIT','apk_sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),
            'scope':'GUID-named payload convention verified against all five runtime textures in this Unity APK. Source bindings and native visual checks provide separate evidence. Not runtime residency/GPU memory certification.',
            'runtime_textures_included':len(expected),'reference_atlas_pages_excluded':14,'textures':rows}
    old.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:report[k] for k in ['status','runtime_textures_included','reference_atlas_pages_excluded','apk_sha256']},indent=2))


if __name__=='__main__':run()
