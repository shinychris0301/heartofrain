"""Stage L1–9 fixed-body topology repairs without touching tutorial fixtures.

The current 9-row masks, source art, goal types, obstacle HP, moves, and
story/introduction metadata are retained. Counts may be rebalanced as
approved. Nothing is installed into the app or backend.
"""
import argparse
import hashlib
import json
from pathlib import Path

from fix_all_gap_drafts import adjust


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root,out=a.root.resolve(),a.output.resolve();cache=(root/'.verification-cache').resolve()
    if not out.is_relative_to(cache) or out==cache or out.exists():raise ValueError('Output must be a new directory under .verification-cache')
    old=root/'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117';out.mkdir(parents=True);rows=[]
    for n in range(1,10):
        name=f'C01_L{n:03}.json';raw=(old/name).read_bytes();source=json.loads(raw.decode('utf-8-sig'))
        if source['rows']!=9 or source['columns']!=9 or (source.get('mossRegrowth') or {}).get('enabled'):raise ValueError(f'L{n}: unexpected source')
        source.setdefault('balancePass',{})
        draft,changes=adjust(source)
        # Historic diagnostic metrics and replay claims cannot describe a
        # different set of obstacle counts or an altered opening.
        cap=source.get('metrics',{}).get('coverageCapPercent')
        draft['metrics']={'status':'DRAFT_RECALCULATION_REQUIRED','activeCells':len(draft['activeCells']),
                          'occupiedObstacleCells':draft['metrics']['occupiedObstacleCells'],
                          'coveragePercent':draft['metrics']['coveragePercent'],'coverageCapPercent':cap}
        draft['formations']=[];draft['validation']={'status':'DRAFT_NOT_VALIDATED'}
        draft['revision']='DRAFT Review117 first-level topology repair; not approved or validated for release'
        result=(json.dumps(draft,indent=2)+'\n').encode('utf-8');(out/name).write_bytes(result)
        rows.append({'level':n,'legacySHA256':sha(raw),'draftSHA256':sha(result),**changes})
    report={'scope':'L1–9 staged topology proposals only; no tutorial flow, Unity, replay, device or balance acceptance.',
            'toolSHA256':sha(Path(__file__).read_bytes()),'levels':rows}
    (out/'Report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
