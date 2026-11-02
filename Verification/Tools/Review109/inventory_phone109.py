"""Read-only fresh USB phone/package/save inventory. No stop/start/install/input."""
from datetime import datetime,timezone
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Review93'))
import phone as old

def main():
    tag=sys.argv[1] if len(sys.argv)==2 else 'Inventory01'
    if not re.fullmatch(r'Inventory[0-9]{2}',tag):raise ValueError('SafeFreshInventoryTag109')
    out=ROOT/'Verification/Evidence/Review109/Physical'/tag
    private=ROOT/'.verification-cache/Review109/Physical'/tag
    out.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False)
    count=0
    def adb(*args,serial=None,binary=False,check=True,timeout=30):
        nonlocal count
        count+=1;p=private/('%04d.out'%count);e=private/('%04d.err'%count)
        cmd=[str(old.ADB)]+(['-s',serial] if serial else [])+list(args)
        with p.open('xb') as stdout,e.open('xb') as stderr:
            result=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
        if check and result.returncode:raise RuntimeError('ReadOnlyAdbQueryFailed109')
        value=p.read_bytes();return value if binary else value.decode('utf-8','replace').strip()
    report=dict(status='RUNNING_READ_ONLY_PHONE109',utc=datetime.now(timezone.utc).isoformat(),deviceMutationPerformed=False,packages=[])
    try:
        devices=[]
        for row in adb('devices','-l').splitlines()[1:]:
            parts=row.split()
            if len(parts)>=2:devices.append((parts[0],parts[1]))
        report['connectedDevices']=[dict(selectorSHA256=hashlib.sha256(s.encode()).hexdigest(),state=state,emulator=s.startswith('emulator-')) for s,state in devices]
        matches=[s for s,state in devices if state=='device' and not s.startswith('emulator-') and ':' not in s]
        if len(matches)!=1:raise ValueError('ExactlyOneAuthorizedPhysicalUsbPhoneRequired109')
        serial=matches[0];(private/'selected_device.txt').write_text(serial,encoding='ascii')
        query=lambda *args,**kw:adb(*args,serial=serial,**kw)
        if query('shell','getprop','ro.kernel.qemu')=='1':raise ValueError('PhysicalPhoneRequired109')
        report.update(serialSHA256=hashlib.sha256(serial.encode()).hexdigest(),model=query('shell','getprop','ro.product.model'),manufacturer=query('shell','getprop','ro.product.manufacturer'),android=query('shell','getprop','ro.build.version.release'),sdk=query('shell','getprop','ro.build.version.sdk'))
        policy=query('shell','dumpsys','window','policy');power=query('shell','dumpsys','power')
        report['keyguardShowing']=bool(re.search(r'(?:mShowingLockscreen|isStatusBarKeyguard|showing)=true',policy))
        report['awake']='mWakefulness=Awake' in power
        packages=[v.removeprefix('package:') for v in query('shell','pm','list','packages').splitlines() if 'heartoftherain' in v.lower()]
        for package in packages:
            if not re.fullmatch(r'com\.heartoftherain\.[a-z0-9]+',package):raise ValueError('UnexpectedGamePackage109')
            row=dict(package=package,pids=query('shell','pidof',package,check=False));report['packages'].append(row)
            path=query('shell','pm','path','--user','0',package,check=False)
            if not path.startswith('package:'):
                row.update(activeBaseApk=False,note='Registered package has no active base APK for current user; no app/data operation authorized from this row.');continue
            row['activeBaseApk']=True
            old.PACKAGE=package;view=old.Phone.__new__(old.Phone);view.serial=serial;view.base='/sdcard/Android/data/'+package+'/files';view.adb=query
            try:row['inventory']=view.inventory()
            except Exception as error:row['inventoryErrorType']=type(error).__name__;row['inventoryErrorCode']=str(error) if re.fullmatch('[A-Za-z0-9]+',str(error)) else 'ReadOnlyInventoryUnavailable109'
            row['baseApkPathSHA256']=hashlib.sha256(path.encode()).hexdigest()
            # Full package dumps remain private (may include unrelated OS data).
            dump=query('shell','dumpsys','package',package)
            for key in ('versionCode','versionName','targetSdk','minSdk'):
                match=re.search(r'\b'+key+r'=([^\s]+)',dump)
                if match:row[key]=match.group(1)
        report['status']='PASS_READ_ONLY_PHONE_INVENTORY109'
    except Exception as error:report.update(status='BLOCKED_READ_ONLY_PHONE_INVENTORY109',errorType=type(error).__name__,code=str(error) if re.fullmatch('[A-Za-z0-9]+',str(error)) else 'ReadOnlyPhoneQueryUnavailable109')
    report['privateEvidenceDirectory']=private.relative_to(ROOT).as_posix()
    report['queries']=count
    (out/'Inventory109.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','model','android','sdk','code') if k in report},ensure_ascii=False))
    print(json.dumps(dict(packages=[dict(package=v['package'],installedSHA256=v.get('inventory',{}).get('installedSHA256'),activeAttempts=v.get('inventory',{}).get('activeAttempts'),profileSummaries=v.get('inventory',{}).get('profileSummaries'),inventoryErrorCode=v.get('inventoryErrorCode')) for v in report['packages']],report=(out/'Inventory109.json').relative_to(ROOT).as_posix())))
    return 0 if report['status'].startswith('PASS') else 1
if __name__=='__main__':raise SystemExit(main())
