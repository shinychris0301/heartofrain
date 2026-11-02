"""Run unchanged native entries serially against current98 source, retaining failures."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--tag',required=True)
    p.add_argument('--only')
    args=p.parse_args()
    if not args.execute or not args.tag.isalnum() or len(args.tag)>16:
        p.error('Explicit short fresh native set required')
    config=ROOT/'Verification/Tools/Review93/suites.json'
    configured=json.loads(config.read_text('utf-8'))
    cases=configured['cases']
    if args.only:cases+=configured.get('connectedCases',[])
    cases += [dict(name='ObstacleIntro98',entry='HeartOfTheRain.Verification.ObstacleIntroduction98Verification.Run',
                   report='ObstacleIntroduction98.json',expected='PASS_NATIVE_OBSTACLE_INTRODUCTION98_RULES',environment='HOTR_REVIEW98_OUT',quit=False),
              dict(name='NoMovesTransactions',entry='HeartOfTheRain.Verification.NoMovesVerification.Run',
                   report='Transactions.json',expected='PASS_NO_MOVES_TRANSACTIONS',environment='HOTR_NO_MOVES_OUTPUT',quit=False),
              dict(name='ProfileClarity',entry='HeartOfTheRain.Verification.ProfileClarityReview.After',
                   report='Native_Review.json',expected='PASS_NATIVE_PROFILE_CLARITY',environment='HOTR_REVIEW98_OUT',quit=False),
              dict(name='ProfileM71',entry='HeartOfTheRain.Verification.ProfileM71Verification.Play',
                   report='Native_Play_Checks.json',expected='PASS_NATIVE_M71_PROFILE',environment='HOTR_REVIEW98_OUT',quit=False)]
    if args.only:
        names=args.only.split(',')
        lookup={c['name']:c for c in cases}
        if len(set(names))!=len(names) or any(n not in lookup for n in names):
            p.error('Unique configured native cases required')
        cases=[lookup[n] for n in names]
    out=ROOT/'Verification/Evidence/Review98/SuiteSets'/args.tag
    out.mkdir(parents=True,exist_ok=False)
    frozen=api.freeze();api.write(out/'FrozenSources.json',frozen)
    result=dict(schemaVersion=1,status='RUNNING_NATIVE_SUITE_SET98',startedUtc=api.utc(),runs=[],
                runnerSHA256=api.sha(Path(__file__)),configurationSHA256=api.sha(config),inputCount=frozen['inputCount'],
                scope='Actual serial pinned2022 native suites on current98 sources. Native scope/counts remain per-report; failures are retained, no Android/backend/provider/production acceptance inferred.')
    for case in cases:
        if frozen!=api.freeze():
            result['sourceDrift']=True;break
        tag=args.tag+'_'+case['name']
        command=[sys.executable,'-B',str(Path(__file__).with_name('run_native.py')),'--execute','--engine','2022','--tag',tag,
                 '--entry',case['entry'],'--report',case['report'],'--expected',case['expected'],
                 '--output-env',case['environment'],'--timeout','900']
        if case.get('quit'):command.append('--quit')
        print('START '+case['name'],flush=True)
        child=subprocess.run(command,cwd=ROOT,timeout=1020)
        invocation=ROOT/'Verification/Evidence/Review98/Native'/tag/'Invocation.json'
        row=dict(case,exitCode=child.returncode)
        if invocation.is_file():
            native=json.loads(invocation.read_text('utf-8'))
            row.update(status=native['status'],invocation=invocation.relative_to(ROOT).as_posix(),invocationSHA256=api.sha(invocation))
        else:
            native={};row['status']='MISSING_NATIVE_INVOCATION98'
        result['runs'].append(row)
        (out/'SuiteSet.json').write_text(json.dumps(result,indent=2)+'\n')
        print('FINISH '+case['name']+' '+row['status'],flush=True)
        if not native.get('mainInputsUnchanged') or native.get('unityPidsAfter') or native.get('nativeStatus')=='MISSING':break
    result.update(status='PASS_CURRENT_NATIVE_SUITE_SET98' if len(result['runs'])==len(cases) and all(r['exitCode']==0 for r in result['runs']) else 'NATIVE_SUITE_SET98_WITH_FAILURES',finishedUtc=api.utc())
    (out/'SuiteSet.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'runs':len(result['runs']),'report':(out/'SuiteSet.json').relative_to(ROOT).as_posix()}),flush=True)
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':raise SystemExit(main())
