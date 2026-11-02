"""Bounded normal-preview observation/input; never accesses the original app.

Screen captures are private, may contain OS overlays, and must be manually
reviewed before publication. Taps are accepted only while the audited preview
APK is foreground, phone is unlocked and no original game process is running.
"""
import argparse
import json
import re
import struct
from datetime import datetime,timezone
from pathlib import Path
import device117 as d

ROOT=Path(__file__).resolve().parents[3]
d.PACKAGE='com.heartoftherain.review117preview'


def guard(receipt):
    serial,state=d.phone();d.require(state['testPackagePresent'] and not state['existingGameProcessRunning'],'PreviewOnlyRequired')
    receipt=receipt.resolve();d.require(receipt.is_relative_to(d.EVIDENCE.resolve()) and receipt.name=='Install.json','InstallReceiptRequired')
    value=json.loads(receipt.read_text(encoding='utf-8'));d.require(value.get('status')=='PASS_ISOLATED_TEST_INSTALL' and value.get('package')==d.PACKAGE,'InstallReceiptRequired')
    path,_=d.adb('shell','pm','path','--user','0',d.PACKAGE,serial=serial);path=path.removeprefix('package:')
    d.require(re.fullmatch(r'[A-Za-z0-9/_+~=.\-]+',path),'InstalledPathInvalid')
    actual,_=d.adb('shell','sha256sum',path,serial=serial);d.require(actual.split() and actual.split()[0].lower()==value['apkSHA256'],'InstalledApkHashMismatch')
    top,_=d.adb('shell','dumpsys','activity','activities',serial=serial)
    resumed=[line for line in top.splitlines() if 'mResumedActivity' in line or 'topResumedActivity' in line]
    d.require(any(d.PACKAGE+'/' in line for line in resumed),'PreviewMustBeForeground')
    return serial,state,value


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['capture','tap']);parser.add_argument('--execute',action='store_true');parser.add_argument('--tag',required=True);parser.add_argument('--receipt',type=Path,required=True);parser.add_argument('--x',type=int);parser.add_argument('--y',type=int);a=parser.parse_args()
    d.require(a.execute and re.fullmatch('[A-Za-z0-9_]{1,35}',a.tag),'ExplicitFreshTagRequired')
    output=ROOT/'Verification/Evidence/Review117/Device'/a.tag;private=ROOT/'.verification-cache/Review117/Normal'/a.tag
    d.require(not output.exists() and not private.exists(),'PreserveExistingEvidence')
    serial,state,receipt=guard(a.receipt)
    size,_=d.adb('shell','wm','size',serial=serial);match=re.search(r'Physical size:\s*(\d+)x(\d+)',size)
    d.require(match is not None,'ScreenSizeUnknown');width,height=map(int,match.groups())
    output.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False)
    report={'status':'FAILED','mode':a.mode,'utc':datetime.now(timezone.utc).isoformat(),'package':d.PACKAGE,'apkSHA256':receipt['apkSHA256'],'screen':[width,height],'originalAppTouched':False,'scope':'Actual physical phone, independent preview package only. Any screenshot is private pending manual review.'}
    try:
        if a.mode=='capture':
            raw=d.adb_bytes('exec-out','screencap','-p',serial=serial,maximum=16*1024*1024)
            serial2,_,_=guard(a.receipt);d.require(serial2==serial,'PhoneChanged')
            d.require(len(raw)>=24 and raw[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',raw[16:24])==(width,height),'ScreenCaptureInvalid')
            import hashlib
            (private/'screen.png').write_bytes(raw);report.update(status='PASS_PRIVATE_PREVIEW_SCREEN_CAPTURE',sha256=hashlib.sha256(raw).hexdigest(),privateEvidenceDirectory=private.relative_to(ROOT).as_posix(),visualApproved=False)
        else:
            d.require(a.x is not None and a.y is not None and 0<=a.x<width and 0<=a.y<height,'ScreenTapInvalid')
            serial2,_,_=guard(a.receipt);d.require(serial2==serial,'PhoneChanged')
            d.adb('shell','input','tap',str(a.x),str(a.y),serial=serial);report.update(status='PASS_BOUNDED_PREVIEW_TAP',x=a.x,y=a.y)
    except Exception as e:report.update(errorType=type(e).__name__,code=str(e) if re.fullmatch('[A-Za-z0-9]{1,100}',str(e)) else 'PreviewOperationUnavailable')
    (output/'Report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'report':(output/'Report.json').relative_to(ROOT).as_posix()}));return 0 if report['status'].startswith('PASS_') else 1

if __name__=='__main__':raise SystemExit(main())
