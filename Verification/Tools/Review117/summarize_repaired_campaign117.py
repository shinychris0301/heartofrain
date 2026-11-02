"""Bind recorded solver wins to the staged 50-level candidate by exact hash.

The summary uses existing reports only. It does not rerun Unity or a device.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
NATIVE=ROOT/'Verification/Evidence/Review117/Native'
STAGE=ROOT/'.verification-cache/Review117/CampaignRepaired117'
EVIDENCE=ROOT/'Verification/Evidence/Review117'


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    manifest=read(STAGE/'Report.json');expected={x['level']:x for x in manifest['levels']}
    picks=[('FirstLevels01',list(range(1,10))),('LegacySolver01',[10]),
           ('SolverSafe01',[n for n in range(11,51) if n not in (44,49)]),('SolverTuned01',[44,49])]
    results=[];runs=[];errors=[];epochs=[]
    for name,selected in picks:
        folder=NATIVE/name;report=read(folder/'CampaignSolver117.json');inv=read(folder/'Invocation.json')
        source_bytes=(folder/'MainSources_before.json').read_bytes();epochs.append(sha(source_bytes))
        if not inv['mainInputsUnchanged'] or not inv['assetGuidsUnchanged'] or inv['exitCode']!=0:errors.append(name+': invocation not isolated/passing')
        candidates={row['level']:row for row in report['levels']}
        chosen=[]
        for n in selected:
            row=candidates.get(n);actual=sha((STAGE/'Levels'/f'C01_L{n:03}.json').read_bytes())
            if row is None or row['status']!='WIN_REPLAY_VERIFIED' or row['levelSHA256']!=expected[n]['levelSHA256'] or actual!=expected[n]['levelSHA256']:
                errors.append(f'{name} L{n}: no hash-matched verified win');continue
            chosen.append(row);results.append({'level':n,'levelSHA256':actual,'run':name,'seed':row['replay']['seed'],
                                                'actions':len(row['replay']['actions'])})
        trials=[t for row in chosen for t in row['trials']]
        runs.append({'run':name,'levels':len(chosen),'trials':len(trials),'trialWins':sum(t['status']=='Won' for t in trials),
                     'trialsWithGaps':sum(t['turnsWithEmptyCells']>0 for t in trials),'gapTurns':sum(t['turnsWithEmptyCells'] for t in trials),
                     'discardedHazards':sum(t['discardedHazards'] for t in trials),'trialErrors':sum(t['status']=='ERROR' for t in trials),
                     'sourceEpochSHA256':sha(source_bytes)})
    if len(results)!=50 or sorted(x['level'] for x in results)!=list(range(1,51)):errors.append('Missing/duplicate level win')
    if len(set(epochs))!=1:errors.append('Selected solver input epochs differ')
    # The additional opening test added only its own Editor fixture and meta.
    baseline=read(NATIVE/'FirstLevels01/MainSources_before.json')['files'];opening=read(NATIVE/'FirstLevels02/MainSources_before.json')['files']
    changed=[k for k in baseline if opening.get(k)!=baseline[k]];added=sorted(set(opening)-set(baseline));removed=sorted(set(baseline)-set(opening))
    expected_added=['Unity/Assets/HeartOfTheRain/Verification/Editor/FirstLevels117Verification.cs','Unity/Assets/HeartOfTheRain/Verification/Editor/FirstLevels117Verification.cs.meta']
    if changed or removed or added!=expected_added:errors.append('Opening suite source epoch differs beyond fixture')
    opening_report=read(NATIVE/'FirstLevels02/FirstLevelsUnity117.json')
    if opening_report['status']!='PASS_BOUNDED_MODEL_CHECKS' or opening_report['openings']!=9:errors.append('First-level opening suite failed')
    for row in opening_report['levels']:
        if row['sourceSHA256']!=expected[row['level']]['levelSHA256']:errors.append(f"Opening L{row['level']} hash mismatch")
    growth=read(NATIVE/'Growth04/CampaignGrowth117.json')
    growth_inv=read(NATIVE/'Growth04/Invocation.json')
    growth_source=read(NATIVE/'Growth04/MainSources_before.json')['files']
    growth_changed=sorted(k for k in baseline if k in growth_source and baseline[k]!=growth_source[k])
    growth_added=sorted(set(growth_source)-set(baseline));growth_removed=sorted(set(baseline)-set(growth_source))
    if (growth['status']!='PASS_BOUNDED_GROWTH_RUNS' or growth['errors'] or growth['gapTrials'] or
            not growth_inv['mainInputsUnchanged'] or not growth_inv['assetGuidsUnchanged'] or growth_inv['exitCode']!=0):
        errors.append('Hash-bound growth suite did not pass')
    if (growth_changed!=['Unity/Assets/HeartOfTheRain/Verification/Editor/CampaignGrowth117Verification.cs'] or
            growth_added!=expected_added or growth_removed):errors.append('Growth source epoch differs beyond test fixtures')
    if sorted(r['level'] for r in growth['levels'])!=[27,44]:errors.append('Growth suite level coverage differs')
    for row in growth['levels']:
        if row['levelSHA256']!=expected[row['level']]['levelSHA256']:errors.append(f"Growth L{row['level']} hash mismatch")
    growth_summary=[{'level':r['level'],'trials':len(r['trials']),'trialsWithGrowth':r['growthTrials'],
                     'growthEvents':sum(t['growth'] for t in r['trials']),'gapTrials':r['gapTrials'],
                     'levelSHA256':r['levelSHA256']} for r in growth['levels']]
    model_path='Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs'
    out={'status':'PASS_HASH_MATCHED_SOLVER_WINS' if not errors else 'FAIL','scope':'Existing bounded Unity Editor model reports and source/art hashes only; not device, human balance or production verification.',
         'errors':errors,'unity':'2022.3.62f3','solverSourceEpochSHA256':epochs[0] if epochs else None,'solverSourceInputCount':len(baseline),
         'modelSourceSHA256':baseline[model_path]['sha256'],'openingEpochSHA256':sha((NATIVE/'FirstLevels02/MainSources_before.json').read_bytes()),
         'openingOnlyAddedFiles':added,'runs':runs,'winningLevels':results,'growth04':growth_summary,
         'growthSourceEpochSHA256':sha((NATIVE/'Growth04/MainSources_before.json').read_bytes()),
         'growthOnlyAddedFiles':growth_added,'growthOnlyChangedFiles':growth_changed,
         'historicalGrowth03Note':'The earlier Growth03 report did not record input level hashes; Growth04 independently binds the final candidate.',
         'limitations':['Level configurations and assets remain staged; production level files and backend catalog remain unchanged.',
                        'One bounded verified win per level establishes an example clear, not fair difficulty or complete behavioral coverage.',
                        'Random/greedy diagnostic trials are selected adaptively and are not a human win-rate or performance benchmark.',
                        'Safe-growth rule changes model source hash; old and new server replay workers require immutable version routing before rollout.',
                        'No current phone/device, production service, purchase recovery or launch certification is established by these reports.']}
    (EVIDENCE/'RepairedCampaignTestSummary117.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':out['status'],'levels':len(results),'epoch':out['solverSourceEpochSHA256'],'errors':errors,'runs':runs},indent=2))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
