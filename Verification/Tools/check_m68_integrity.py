"""Audit delivered M68 bytes, importer GUIDs and the single PNG recovery."""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/Fluidity'


def run():
    imported=json.loads((OUT/'M68_Import.json').read_text())
    repair=json.loads((OUT/'M68_Blink_Repair.json').read_text())
    normalized=[];recovered=[];unchanged=0;failures=[]
    # Read metadata originals from the owner archive, never from a live importer.
    import zipfile
    with zipfile.ZipFile('C:/Users/shiny/Downloads/Dariya_Celebration_M68_Complete_Assets.zip') as archive:
        for entry in imported['imported']:
            path=ROOT/'Unity'/entry['file'];current=path.read_bytes()
            actual=hashlib.sha256(current).hexdigest()
            if actual==entry['sha256']:unchanged+=1;continue
            if path.suffix=='.meta':
                original=archive.read('Dariya_Celebration_M68/UnityAssets/'+entry['file'])
                guid=lambda value:re.search(rb'^guid: ([0-9a-f]{32})',value,re.M)[1].decode()
                if guid(original)!=guid(current):failures.append(entry['file']+' GUID changed')
                normalized.append({'file':entry['file'],'guid':guid(current),'sha256':actual})
            elif entry['file'].endswith('/Mesh/Dariya_Blink_Texture.png') and actual==repair['repaired_sha256']:
                recovered.append(entry['file'])
            else:failures.append(entry['file']+' unexpected content change')
    report={'status':'PASS_M68_ASSET_INTEGRITY' if not failures else 'FAIL_M68_ASSET_INTEGRITY',
            'scope':'Delivered asset bytes; native importer normalization retains all source GUIDs. PNG recovery is separately pixel-verified.',
            'unchanged_files':unchanged,'normalized_importers':normalized,'recovered_pngs':recovered,'failures':failures}
    (OUT/'M68_Integrity.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'status':report['status'],'unchanged_files':unchanged,'normalized_importers':len(normalized),'recovered_pngs':len(recovered),'failures':failures},indent=2))
    assert not failures


if __name__=='__main__':run()
