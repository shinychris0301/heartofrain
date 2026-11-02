"""Hash preferences at the beginning/end of this verification span; never save contents."""
import argparse,datetime as dt,hashlib,json,re,subprocess
from pathlib import Path
from measure_fluidity import ROOT,ADB,PACKAGE

def run():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['before','after']);args=parser.parse_args()
    path=ROOT/'Verification/Evidence/PowerWarmup/Test_Span_Preferences.json'
    result=json.loads(path.read_text()) if path.exists() else {'scope':'Both LDPlayer instances, complete testing span, shared preference hashes only; no durable campaign/inventory claim.'}
    values={}
    for serial in ['127.0.0.1:5555','127.0.0.1:5557']:
        subprocess.run([str(ADB),'connect',serial],check=True,capture_output=True)
        def adb(*parts):return subprocess.run([str(ADB),'-s',serial,*parts],check=True,capture_output=True).stdout
        names=adb('shell','run-as',PACKAGE,'ls','shared_prefs').decode().split()
        values[serial]={name:hashlib.sha256(adb('exec-out','run-as',PACKAGE,'cat','shared_prefs/'+name)).hexdigest() for name in names if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',name)}
        assert values[serial]
    result[args.stage]=values;result[args.stage+'Utc']=dt.datetime.now(dt.timezone.utc).isoformat()
    if args.stage=='after':
        result['status']='PASS_IDENTICAL_PREFERENCE_FILES' if result['before']==values else 'PREFERENCE_HASH_REVIEW_REQUIRED'
        assert result['status']=='PASS_IDENTICAL_PREFERENCE_FILES'
    path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'stage':args.stage,'status':result.get('status','BASELINE_HASHED')}))

if __name__=='__main__':run()
