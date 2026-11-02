"""Check final cache-only candidate bindings and unchanged shipped levels."""
import hashlib
import json
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[3];stage=root/'.verification-cache/Review117/CampaignFinal117';report=json.loads((stage/'Report.json').read_text());errors=[]
    for row in report['levels']:
        n=row['level'];file=stage/'Levels'/f'C01_L{n:03}.json'
        if hashlib.sha256(file.read_bytes()).hexdigest()!=row['levelSHA256']:errors.append(f'L{n} JSON')
        for art in row['art']:
            path=Path(art['path'])
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=art['sha256']:errors.append(f'L{n} art {path.name}')
        original=root/'Unity/Assets/HeartOfTheRain/M47/Data/Levels'/file.name;legacy=root/'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117'/file.name
        if original.read_bytes()!=legacy.read_bytes():errors.append(f'L{n} production level changed')
        if n<=10 and file.read_bytes()!=legacy.read_bytes():errors.append(f'L{n} changed')
    opted=[]
    for n in range(1,51):
        level=json.loads((stage/'Levels'/f'C01_L{n:03}.json').read_text(encoding='utf-8-sig'))
        if (level.get('mossRegrowth') or {}).get('safeSegmentBottom'):opted.append(n)
    if opted!=[27,44]:errors.append('Wrong growth opt-ins')
    result={'status':'PASS' if not errors else 'FAIL','scope':'Byte equality and opt-in audit only; no model, device, production or balance acceptance.',
            'levels':len(report['levels']),'optedIn':opted,'errors':errors}
    (root/'Verification/Evidence/Review117/CampaignFinalAudit117.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
