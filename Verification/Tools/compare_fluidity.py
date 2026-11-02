"""Compare observed emulator phases without claiming physical-device approval."""
import csv
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/Fluidity'


def run():
    parser=argparse.ArgumentParser();parser.add_argument('--before',type=Path,default=OUT/'Before');parser.add_argument('--after',type=Path,default=OUT/'After');parser.add_argument('--out',type=Path,default=OUT);args=parser.parse_args();destination=args.out.resolve();destination.mkdir(parents=True,exist_ok=True)
    def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
    before=read(args.before/'Measurement.json');after=read(args.after/'Measurement.json')
    assert before['status']==after['status']=='RECORDED_NATIVE_FLUIDITY'
    assert not before['errors'] and not after['errors']
    install=read(args.after/'Installation.json')
    apk=Path(install['apk']);assert hashlib.sha256(apk.read_bytes()).hexdigest()==install['sha256']
    assert before['graphics']==after['graphics']
    rows=[]
    for a,b in zip(before['phases'],after['phases']):
        assert a['name']==b['name']
        row={'phase':a['name']}
        for label,key in [('command_ms','commandMs'),('first_step_ms','firstPresentationMs'),('settle_seconds','settleSeconds'),('p95_frame_ms','p95Ms'),('worst_frame_ms','worstMs'),('collection_counter','gen0Collections')]:
            row['before_'+label]=round(a[key],3);row['after_'+label]=round(b[key],3)
        rows.append(row)
    with (destination/'Performance_Comparison.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    report={'status':'RECORDED_COMPARATIVE_EMULATOR_MEASUREMENT','apk_sha256':install['sha256'],
            'scope':after['scope'],'first_step_definition':'GameplayScreen.StepStarted event, not instrumented physical display latency.',
            'limits':['One run per variant; no confidence interval or physical-device approval.',
                      'ARM translation, host contention and Android scheduling affect timings.',
                      'GC.CollectionCount(0) is a collection counter, not a generational heap-allocation measurement.',
                      'First-step timing does not measure power ignition; inspect native contact/ignition checks and actual video separately. No claim that all hitches are eliminated.'],
            'phases':rows}
    (destination/'Performance_Comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'status':report['status'],'phases':len(rows),'apk_sha256':install['sha256']},indent=2))


if __name__=='__main__':run()
