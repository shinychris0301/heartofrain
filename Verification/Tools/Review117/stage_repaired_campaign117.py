"""Bind the revised first nine and earlier staged 11–50 to existing art.

Creates a new ignored-cache candidate only. No production assets, backend
catalog, profiles, or replay data are changed.
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
    prior=cache/'Review117/CampaignFinal117';first=cache/'Review117/FirstLevelsDraft01';legacy=root/'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117'
    first_rows={r['level']:r for r in json.loads((first/'Report.json').read_text())['levels']}
    previous=json.loads((prior/'Report.json').read_text());old_rows={r['level']:r for r in previous['levels']}
    out.mkdir(parents=True);(out/'Levels').mkdir();(out/'Art').mkdir();rows=[];unique=set();widths={9:0,10:0,11:0};before_count=after_count=0
    for n in range(1,51):
        name=f'C01_L{n:03}';original=json.loads((legacy/(name+'.json')).read_text(encoding='utf-8-sig'))
        path=(first if n<=9 else prior/'Levels')/(name+'.json');raw=path.read_bytes();d=json.loads(raw.decode('utf-8-sig'))
        expected=first_rows[n]['draftSHA256'] if n<=9 else old_rows[n]['levelSHA256']
        if sha(raw)!=expected or d['rows']!=9 or d['columns'] not in widths:raise ValueError(f'L{n}: invalid level hash or geometry')
        if {g['family'] for g in d['goals']}!={g['family'] for g in original['goals']}:raise ValueError(f'L{n}: goal types changed')
        if n<=9 and (d['activeCells']!=original['activeCells'] or d['spawnPoints']!=original['spawnPoints'] or d['movesProposal']!=original['movesProposal']):raise ValueError(f'L{n}: original authored geometry or move budget changed')
        if bool((d.get('mossRegrowth') or {}).get('safeSegmentBottom',False))!=(n in (27,44)):raise ValueError(f'L{n}: growth opt-in mismatch')
        active={(x['x'],x['y']) for x in d['activeCells']};signature=(d['columns'],tuple(sorted(active)),tuple(sorted((o['x'],o['y'],o['family'],o['hp']) for o in d['obstacles'])))
        if signature in unique:raise ValueError(f'L{n}: duplicate configuration')
        unique.add(signature);widths[d['columns']]+=1
        art=[]
        for suffix,key in (('_Surface.png','surfaceSHA256'),('_AlphaMask.png','maskSHA256')):
            oldart=prior/'Art'/(name+suffix);rawart=oldart.read_bytes();item=old_rows[n]['art'][0 if key=='surfaceSHA256' else 1]
            if sha(rawart)!=item['sha256']:raise ValueError(f'L{n}: prior art hash changed')
            image=Image.open(oldart).convert('RGBA')
            if image.size!=(d['columns']*64+30,9*64+30):raise ValueError(f'L{n}: art dimensions')
            if key=='maskSHA256':
                for x in range(d['columns']):
                    for y in range(9):
                        if (image.getpixel((15+x*64+32,15+(8-y)*64+32))[3]==255)!=((x,y) in active):raise ValueError(f'L{n}: mask alignment')
            dest=out/'Art'/(name+suffix);dest.write_bytes(rawart);art.append({'path':dest.as_posix(),'sha256':sha(rawart)})
        (out/'Levels'/(name+'.json')).write_bytes(raw);before_count+=sum(g['count'] for g in original['goals']);after_count+=sum(g['count'] for g in d['goals'])
        rows.append({'level':n,'rows':d['rows'],'columns':d['columns'],'levelSHA256':sha(raw),'art':art})
    result={'scope':'Staged candidate with nine repaired early boards; static checks only, no production/backend/device/balance approval.',
            'toolSHA256':sha(Path(__file__).read_bytes()),'widthCounts':widths,'uniqueConfigurations':len(unique),'growthOptInLevels':[27,44],
            'objectiveUnitsOriginal':before_count,'objectiveUnitsStaged':after_count,'levels':rows}
    (out/'Report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('widthCounts','uniqueConfigurations','growthOptInLevels','objectiveUnitsOriginal','objectiveUnitsStaged')}))


if __name__=='__main__':main()
