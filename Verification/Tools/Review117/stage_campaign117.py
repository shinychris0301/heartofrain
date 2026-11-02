"""Bind all 50 draft levels to their approved-derived board art in cache.

This validates hashes, mask centers and structural uniqueness only. Nothing is
installed into Unity, a backend catalog, a worker, an APK or a live profile.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root,out=a.root.resolve(),a.output.resolve();cache=(root/'.verification-cache').resolve()
    if not out.is_relative_to(cache) or out==cache or out.exists():raise ValueError('Output must be a new directory inside .verification-cache')
    old=root/'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117'; current=cache/'Review117/CampaignGrowthTuned01'
    oldart=root/'Unity/Assets/HeartOfTheRain/M47/Art/Boards';newart=cache/'Review117/BoardVaried03'
    safe=json.loads((root/'Verification/Evidence/Review117/CampaignSafeGrowth01Manifest.json').read_text())
    tuning=json.loads((current/'Report.json').read_text());tuned=tuning['levels'][0]
    if tuned['level']!=44:raise ValueError('Unexpected tuned report')
    expected={r['level']:r for r in safe['levels']};out.mkdir(parents=True);(out/'Levels').mkdir();(out/'Art').mkdir()
    rows=[];unique=set();widths={9:0,10:0,11:0};goals_before=goals_after=0
    for n in range(1,51):
        name=f'C01_L{n:03}';source=(old if n<11 else current)/(name+'.json');raw=source.read_bytes();d=json.loads(raw.decode('utf-8-sig'));original=json.loads((old/(name+'.json')).read_text(encoding='utf-8-sig'))
        expected_sha=tuned['afterSHA256'] if n==44 else expected[n]['levelSHA256']
        if sha(raw)!=expected_sha:raise ValueError(f'L{n}: level hash mismatch')
        if d['rows']!=9 or d['columns'] not in widths:raise ValueError(f'L{n}: dimensions invalid')
        if {g['family'] for g in d['goals']}!={g['family'] for g in original['goals']}:raise ValueError(f'L{n}: goal types changed')
        if bool((d.get('mossRegrowth') or {}).get('safeSegmentBottom',False))!=(n in (27,44)):raise ValueError(f'L{n}: opt-in mismatch')
        active={(c['x'],c['y']) for c in d['activeCells']}
        sig=(d['columns'],tuple(sorted(active)),tuple(sorted((o['x'],o['y'],o['family'],o['hp']) for o in d['obstacles'])))
        if sig in unique:raise ValueError(f'L{n}: duplicate configuration')
        unique.add(sig);widths[d['columns']]+=1
        board_art=oldart if n<11 else newart;art_rows=[]
        for suffix,key in (('_Surface.png','surfaceSHA256'),('_AlphaMask.png','maskSHA256')):
            data=(board_art/(name+suffix)).read_bytes()
            if sha(data)!=expected[n][key]:raise ValueError(f'L{n}: art hash mismatch')
            image=Image.open(board_art/(name+suffix)).convert('RGBA')
            if image.size!=(d['columns']*64+30,9*64+30):raise ValueError(f'L{n}: art size mismatch')
            if key=='maskSHA256':
                for x in range(d['columns']):
                    for y in range(9):
                        if (image.getpixel((15+x*64+32,15+(8-y)*64+32))[3]==255)!=((x,y) in active):raise ValueError(f'L{n}: mask center mismatch')
            dest=out/'Art'/(name+suffix);dest.write_bytes(data);art_rows.append({'path':dest.as_posix(),'sha256':sha(data)})
        (out/'Levels'/(name+'.json')).write_bytes(raw)
        if n>=11:goals_before+=sum(g['count'] for g in original['goals']);goals_after+=sum(g['count'] for g in d['goals'])
        rows.append({'level':n,'rows':d['rows'],'columns':d['columns'],'levelSHA256':sha(raw),'art':art_rows})
    report={'scope':'Staged 50-level data/art binding and static checks only; no production, backend, device or human difficulty approval.',
            'toolSHA256':sha(Path(__file__).read_bytes()),'widthCounts':widths,'uniqueConfigurations':len(unique),
            'growthOptInLevels':[27,44],'objectiveUnitsOriginal11to50':goals_before,'objectiveUnitsStaged11to50':goals_after,'levels':rows}
    (out/'Report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:report[k] for k in ('widthCounts','uniqueConfigurations','growthOptInLevels','objectiveUnitsOriginal11to50','objectiveUnitsStaged11to50')}))


if __name__=='__main__':main()
