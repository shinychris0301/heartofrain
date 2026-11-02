"""Root-only actual phone navigation captures; no operation occurs on import."""
import sys,json,time,argparse
from pathlib import Path
from datetime import datetime,timezone

def main():
    root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root/'Verification/Tools/Display88'))
    from phone import CapturePathPhone,public_binding,utc
    import run_phone_checks as checks
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phone',type=Path,required=True);args=parser.parse_args()
    p=CapturePathPhone(args.phone)
    p.assert_installed();p.assert_no_active_attempt()
    out=p.out/'Navigation';out.mkdir(exist_ok=False)
    def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    frozen=checks.source_module.freeze();build=checks.current_build(p,frozen)
    before=p.snapshot();record={'status':'RUNNING','startedUtc':utc(),'apkSHA256':p.target['candidateApkSHA256'],'sourceManifest':build['sourceManifest'],'runner':public_binding(Path(__file__)),'ordinaryBefore':before,'actions':[],'captures':[],'scope':'Actual Android bottom-navigation touches and full-frame OS captures on the final88 APK. Ordinary services/settings unchanged. Read-only observer readiness is bound to this fresh launch. No purchases, rewards, provider/social requests or gameplay attempts.'}
    write(out/'Review.json',record)
    began=checks.when(p.start_marker('HOTR_RunDisplay88','observe'))
    def observe(expected):
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            raw=p.adb('shell','cat',p.base+'/Display88/Report.json',check=False)
            try:
                d=json.loads(raw);fresh=datetime.fromisoformat(d['startedUtc'].replace('Z','+00:00'))>=began
                g=d['snapshots'][-1]['geometry'];types=g['visibleOverlayTypes']
                ok=(g['home']['presentationVisible'] and not any(x.endswith('LaunchPage') for x in types)) if expected=='Home' else any(x.endswith('.'+expected+'Page') for x in types)
                if fresh and ok:return d
            except (ValueError,KeyError,IndexError,TypeError):pass
            time.sleep(1)
        raise RuntimeError('FreshNavigationReadinessDeadline'+expected)
    def capture(name,geometry):
        path=p.capture('Navigation/'+name+'.png');write(out/(name+'_Geometry.json'),geometry)
        record['captures'].append(public_binding(path));write(out/'Review.json',record)
    try:
        capture('Home_Initial',observe('Home'))
        for page,x in [('Journey',72),('Leaderboard',216),('Teams',504),('Shop',648),('Home',360)]:
            action={'page':page,'kind':'tap','x':x,'y':1500,'dispatch':'PENDING','utc':utc()};record['actions'].append(action);write(out/'Review.json',record)
            p.adb('shell','input','tap',str(x),'1500');action['dispatch']='ADB_COMPLETED';write(out/'Review.json',record)
            capture(page,observe(page))
        record['status']='RECORDED_PHYSICAL_NAVIGATION88_REQUIRES_VISUAL_REVIEW'
    except Exception as e:
        record.update(status='FAIL_PHYSICAL_NAVIGATION88',failureType=type(e).__name__,failureCategory=str(e) if isinstance(e,RuntimeError) else None)
    finally:
        after=p.snapshot();record.update(ordinaryAfter=after,ordinaryDataUnchanged=before==after,inputsUnchanged=frozen==checks.source_module.freeze(),finishedUtc=utc())
        record['inventoryAfter']=p.inventory();record['appLog']=p.app_log('Navigation/Runtime.log')
        if not record['ordinaryDataUnchanged'] or not record['inputsUnchanged']:record['status']='FAIL_PHYSICAL_NAVIGATION88_PRESERVATION'
        write(out/'Review.json',record)
    print(json.dumps({'status':record['status'],'captures':len(record['captures']),'savedDataPreserved':record['ordinaryDataUnchanged']}))
    raise SystemExit(0 if record['status'].startswith('RECORDED') else 1)

if __name__=="__main__":
    main()
