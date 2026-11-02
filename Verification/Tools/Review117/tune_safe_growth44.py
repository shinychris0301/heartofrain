"""Stage an L44 comparison with two initially eligible safe moss-growth cells.

No runtime file is changed. Result is a balance experiment, not a release.
"""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path

from propose_nine_row import opening_matches, has_legal_swap


def sha(data):return hashlib.sha256(data).hexdigest()


def tune(level):
    d=copy.deepcopy(level)
    if d['globalLevel']!=44 or not d['mossRegrowth'].get('safeSegmentBottom'):
        raise ValueError('Not an opted-in L44 draft')
    removed=[]
    for pos in ((2,0),(7,0)):
        candidates=[o for o in d['obstacles'] if o['family']=='moss' and (o['x'],o['y'])==pos]
        if len(candidates)!=1:raise ValueError('Expected safe-space moss positions changed')
        d['obstacles'].remove(candidates[0]);removed.append(candidates[0])
    active={(p['x'],p['y']) for p in d['activeCells']}
    existing={(p['x'],p['y']):p['color'] for p in d['initialTiles']}
    added=None
    for colors in itertools.product(d['activeColors'],repeat=len(removed)):
        gems=dict(existing)
        for o,color in zip(removed,colors):gems[(o['x'],o['y'])]=color
        if not opening_matches(gems) and has_legal_swap(gems):added=colors;break
    if added is None:raise ValueError('No valid opening color choice')
    for o,color in zip(removed,added):d['initialTiles'].append({'x':o['x'],'y':o['y'],'color':color})
    goal=next(g for g in d['goals'] if g['family']=='moss');before=goal['count'];goal['count']-=len(removed)
    d['metrics']['occupiedObstacleCells']-=len(removed)
    d['metrics']['coveragePercent']=round(100*d['metrics']['occupiedObstacleCells']/len(active),2)
    d['balancePass']['scope']='Safe-growth L44 availability experiment; not balance or human-play approved'
    return d,{'removedMoss':[{'x':o['x'],'y':o['y'],'instanceId':o['instanceId']} for o in removed],
              'oldMossGoal':before,'newMossGoal':goal['count'],'newGemColors':added}


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root,out=a.root.resolve(),a.output.resolve();cache=(root/'.verification-cache').resolve()
    if not out.is_relative_to(cache) or out==cache or out.exists():raise ValueError('Output must be a new directory inside .verification-cache')
    old=cache/'Review117/CampaignSafeGrowth01';out.mkdir(parents=True);rows=[]
    for n in range(11,51):
        name=f'C01_L{n:03}.json';before=(old/name).read_bytes()
        if n==44:
            d,detail=tune(json.loads(before.decode()));after=(json.dumps(d,indent=2)+'\n').encode();rows.append({'level':n,'beforeSHA256':sha(before),'afterSHA256':sha(after),**detail})
        else:after=before
        (out/name).write_bytes(after)
    report={'scope':'L44 safe-growth availability experiment; no Unity, replay, human-balance, backend or device acceptance.',
            'toolSHA256':sha(Path(__file__).read_bytes()),'levels':rows}
    (out/'Report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
