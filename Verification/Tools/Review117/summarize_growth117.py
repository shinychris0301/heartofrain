"""Summarize bounded, growth-seeking model trials; not player statistics."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
NATIVE=ROOT/'Verification/Evidence/Review117/Native'


def main():
    summaries=[]
    for name in ('Growth01','Growth02'):
        p=NATIVE/name/'CampaignGrowth117.json';data=json.loads(p.read_text(encoding='utf-8-sig'))
        for row in data['levels']:
            trials=row['trials']
            summaries.append({'run':name,'level':row['level'],'trials':len(trials),
                              'trialsWithGrowth':row['growthTrials'],'totalGrowthEvents':sum(t['growth'] for t in trials),
                              'trialsWithGaps':row['gapTrials'],'wins':sum(t['status']=='Won' for t in trials),
                              'moves':sum(t['actions'] for t in trials),'errors':row['errors'],
                              'seeds':[{'seed':t['seed'],'growth':t['growth'],'gaps':t['turnsWithGaps'],'status':t['status']} for t in trials]})
    result={'scope':'Growth-seeking diagnostic policies on corresponding seeds; action histories diverge after policy change. Not natural-player rates, a controlled difficulty study, or device evidence.',
            'summaries':summaries}
    (ROOT/'Verification/Evidence/Review117/GrowthFrequency117.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{k:x[k] for k in ('run','level','trialsWithGrowth','totalGrowthEvents','trialsWithGaps','wins')} for x in summaries],indent=2))


if __name__=='__main__':main()
