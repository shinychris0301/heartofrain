"""Read-only USB preflight or explicit isolated test-APK install/launch.

Never reads, stops, clears, replaces, uninstalls, or restores any existing game
package or its files. Raw device output, logs and identifiers are not saved;
opt-in fixture screenshots are retained privately from the separate test app.
Installation requires a freshly absent distinct package and a passed static
audit. Launch requires its installation receipt and the prior app not running.
No device action occurs at import or without a command-line mode.
"""
import argparse
import hashlib
import json
import re
import struct
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
ADB=Path('C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe')
PACKAGE='com.heartoftherain.review117'
EVIDENCE=ROOT/'Verification/Evidence/Review117/Device'


def require(ok, code):
    if not ok: raise ValueError(code)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda:stream.read(1024*1024),b''): h.update(part)
    return h.hexdigest()


def adb(*args, serial=None, timeout=30, ok=(0,)):
    command=[str(ADB)]+(['-s',serial] if serial else [])+list(args)
    p=subprocess.run(command,capture_output=True,text=True,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
    require(p.returncode in ok,'AdbQueryFailed')
    return p.stdout.strip(),p.returncode


def adb_bytes(*args, serial, maximum):
    p=subprocess.run([str(ADB),'-s',serial,*args],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    require(p.returncode==0 and len(p.stdout)<=maximum,'FixtureReadFailed')
    return p.stdout


def process_identity(serial):
    """Hash boot, PID and kernel start tick; never save a raw device identifier."""
    pids,code=adb('shell','pidof',PACKAGE,serial=serial,ok=(0,1))
    require(code==0 and re.fullmatch(r'[0-9]+',pids) is not None,'SinglePreviewProcessRequired')
    stat,_=adb('shell','cat','/proc/'+pids+'/stat',serial=serial)
    end=stat.rfind(')');tail=stat[end+1:].split() if end>=0 else []
    require(len(tail)>19 and tail[19].isdigit(),'PreviewProcessIdentityUnavailable')
    boot,_=adb('shell','cat','/proc/sys/kernel/random/boot_id',serial=serial)
    require(re.fullmatch(r'[0-9a-fA-F-]{36}',boot) is not None,'PreviewProcessIdentityUnavailable')
    return hashlib.sha256((boot.lower()+'|'+pids+'|'+tail[19]).encode('ascii')).hexdigest()


def phone():
    require(ADB.is_file(),'AdbUnavailable')
    listing,_=adb('devices','-l')
    rows=[line.split() for line in listing.splitlines()[1:] if len(line.split())>=2]
    usb=[r[0] for r in rows if r[1]=='device' and not r[0].startswith('emulator-') and ':' not in r[0]]
    require(len(usb)==1,'ExactlyOneAuthorizedUsbPhoneRequired')
    s=usb[0]
    require(re.fullmatch(r'[A-Za-z0-9._-]{1,100}',s) is not None,'InvalidUsbSelector')
    q=lambda *args,**kw:adb(*args,serial=s,**kw)
    require(q('shell','getprop','ro.kernel.qemu')[0]!='1','PhysicalPhoneRequired')
    model=q('shell','getprop','ro.product.model')[0]; api=q('shell','getprop','ro.build.version.sdk')[0]
    require(api.isdigit() and int(api)>=26,'SupportedAndroidRequired')
    require(q('shell','am','get-current-user')[0]=='0','OwnerAndroidUserRequired')
    policy=q('shell','dumpsys','window','policy')[0].split('KeyguardServiceDelegate',1)[-1]
    match=re.search(r'(?m)^\s*showing=(true|false)\s*$',policy)
    power=q('shell','dumpsys','power')[0]
    require(match and match.group(1)=='false' and 'mWakefulness=Awake' in power,'UnlockedAwakePhoneRequired')
    raw=q('shell','pm','list','packages','--user','0')[0]
    names={line.removeprefix('package:') for line in raw.splitlines() if line.startswith('package:')}
    # Existing project app processes may contain active attempts. Do not stop,
    # inspect their files, or launch a second app over an active game.
    running=[]
    for name in names:
        if name==PACKAGE or not (name.lower().startswith('com.heartoftherain.') or name=='com.DefaultCompany.Unity'):continue
        require(re.fullmatch(r'[A-Za-z0-9_.]+',name) is not None,'UnexpectedGamePackage')
        output,code=q('shell','pidof',name,ok=(0,1))
        if code==0 and output:running.append(name)
    return s, {'physicalDevices':1,'model':model,'api':int(api),'user':0,'unlocked':True,'existingGameProcessRunning':bool(running),'testPackagePresent':PACKAGE in names}


def load_build(build):
    build=build.resolve();root=(ROOT/'Verification/Evidence/Review117/Native').resolve()
    require(build.is_relative_to(root) and build.name=='BuildDevelopment117.json','ExactNativeBuildRequired')
    invocation=build.parent/'Invocation.json';audit=build.parent/'Static/Audit01/StaticApk117.json'
    native=json.loads(build.read_text(encoding='utf-8-sig'));iv=json.loads(invocation.read_text(encoding='utf-8-sig'));av=json.loads(audit.read_text(encoding='utf-8-sig'))
    require(native.get('status')=='PASS_NATIVE_TEAMS117_BUILD_DEVELOPMENT' and native.get('actualBuild') and native.get('errors')==0 and native.get('packageName')==PACKAGE,'PassingIsolatedBuildRequired')
    require(iv.get('status')=='PASS_NATIVE117_LTS_INVOCATION' and iv.get('mainInputsUnchanged') is True and iv.get('nativeReportSHA256')==sha(build),'MatchingNativeInvocationRequired')
    require(av.get('status')=='PASS_STATIC_TEAMS117_APK' and av.get('nativeBuildSHA256')==sha(build) and av.get('invocationSHA256')==sha(invocation),'MatchingStaticAuditRequired')
    needed={'NoSharedAndroidUser','ProviderAuthoritiesArePackageScoped','NoSharedPlayerAccountOrPaymentDeepLinks','NoAndroidBackupOrRestore','PackageApiArm64AndDevelopment'}
    require(needed.issubset(set(av.get('checks',[]))),'IsolationAuditRequired')
    apk=Path(native['apk']).resolve();candidates=(ROOT/'.verification-cache/Review117/Candidates').resolve()
    require(apk.is_relative_to(candidates) and apk.is_file() and sha(apk)==native.get('apkSHA256')==av.get('apkSHA256'),'ExactAuditedApkRequired')
    return apk, native['apkSHA256'],sha(audit)


def main():
    global PACKAGE
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['inspect','install','launch','collect','reset']);p.add_argument('--execute',action='store_true');p.add_argument('--tag');p.add_argument('--build',type=Path);p.add_argument('--receipt',type=Path);p.add_argument('--launch-receipt',type=Path);p.add_argument('--collect-receipt',type=Path);p.add_argument('--fixture',choices=['shuffle','notice','all']);p.add_argument('--level',type=int,default=1);p.add_argument('--preview',action='store_true');a=p.parse_args()
    require(1<=a.level<=50 and (a.mode=='launch' and a.fixture is not None or a.level==1),'InvalidFixtureLevel')
    PACKAGE='com.heartoftherain.review117preview' if a.preview else 'com.heartoftherain.review117'
    if a.mode=='inspect':
        _,state=phone();print(json.dumps({'status':'READ_ONLY_DEVICE_PREFLIGHT','device':state,'profileAccessed':False,'installed':False}));return 0
    require(a.execute and a.tag and re.fullmatch('[A-Za-z0-9_]{1,35}',a.tag),'ExplicitFreshTagRequired')
    serial,state=phone();require(not state['existingGameProcessRunning'],'ExistingGameMustBeClosedWithoutInterruptingAnAttempt')
    out=EVIDENCE/a.tag;require(not out.exists(),'PreserveExistingEvidence');out.mkdir(parents=True,exist_ok=False)
    report={'status':'FAILED','mode':a.mode,'utc':datetime.now(timezone.utc).isoformat(),'device':state,'package':PACKAGE,'existingProfileAccessed':False,'otherPackageStopped':False,'uninstalled':False}
    try:
        if a.mode=='install':
            require(a.fixture is None and a.build is not None and not state['testPackagePresent'],'FreshTestPackageRequired')
            apk,digest,audit=load_build(a.build);report.update(apkSHA256=digest,staticAuditSHA256=audit)
            fresh_serial,fresh_state=phone()
            require(fresh_serial==serial and not fresh_state['existingGameProcessRunning'] and not fresh_state['testPackagePresent'],'FreshPhoneStateRequired')
            # No -r: an unexpected installed package is never replaced.
            output,_=adb('install','-t',str(apk),serial=serial,timeout=240)
            require('Success' in output.splitlines(),'InstallNotConfirmed')
            fresh,_=adb('shell','pm','path','--user','0',PACKAGE,serial=serial)
            path=fresh.removeprefix('package:')
            require(fresh.startswith('package:') and re.fullmatch(r'[A-Za-z0-9/_+~=.\-]+',path),'InstalledPackagePathInvalid')
            checked,_=adb('shell','sha256sum',path,serial=serial)
            require(checked.split() and checked.split()[0].lower()==digest,'InstalledApkHashMismatch')
            report.update(status='PASS_ISOLATED_TEST_INSTALL',installed=True,launched=False)
        else:
            require(a.receipt is not None and state['testPackagePresent'],'FreshInstalledTestReceiptRequired')
            receipt=a.receipt.resolve();require(receipt.is_relative_to(EVIDENCE.resolve()) and receipt.name=='Install.json','ExactInstallReceiptRequired')
            value=json.loads(receipt.read_text(encoding='utf-8'));require(value.get('status')=='PASS_ISOLATED_TEST_INSTALL' and value.get('package')==PACKAGE,'ValidInstallReceiptRequired')
            paths,_=adb('shell','pm','path','--user','0',PACKAGE,serial=serial);path=paths.removeprefix('package:')
            require(paths.startswith('package:') and re.fullmatch(r'[A-Za-z0-9/_+~=.\-]+',path),'InstalledPackagePathInvalid')
            checked,_=adb('shell','sha256sum',path,serial=serial)
            require(checked.split() and checked.split()[0].lower()==value['apkSHA256'],'InstalledApkHashMismatch')
            if a.mode=='launch':
                fresh_serial,fresh_state=phone()
                require(fresh_serial==serial and not fresh_state['existingGameProcessRunning'] and fresh_state['testPackagePresent'],'FreshPhoneStateRequired')
                if a.fixture:
                    running,code=adb('shell','pidof',PACKAGE,serial=serial,ok=(0,1))
                    require(code==1 and not running,'FixtureRequiresFreshTestProcess')
                args=['shell','am','start','-n',PACKAGE+'/com.unity3d.player.UnityPlayerActivity']
                nonce=uuid.uuid4().hex if a.fixture else ''
                if a.fixture:args+=['--es','hotr.review117.fixture',a.fixture,'--es','hotr.review117.nonce',nonce,'--ei','hotr.review117.level',str(a.level)]
                output,_=adb(*args,serial=serial)
                require('Error' not in output and 'Starting:' in output,'LaunchNotConfirmed')
                deadline=time.monotonic()+5;identity=None
                while time.monotonic()<deadline:
                    try:identity=process_identity(serial);break
                    except ValueError:time.sleep(.2)
                require(identity is not None,'PreviewProcessIdentityUnavailable')
                report.update(status='PASS_ISOLATED_TEST_LAUNCH_REQUESTED',apkSHA256=value['apkSHA256'],installed=True,launched=True,fixture=a.fixture or '',fixtureLevel=a.level if a.fixture else 0,runNonce=nonce,processSHA256=identity)
            elif a.mode=='collect':
                require(a.fixture is None and a.launch_receipt is not None,'FixtureLaunchReceiptRequired')
                launched=a.launch_receipt.resolve();require(launched.is_relative_to(EVIDENCE.resolve()) and launched.name=='Launch.json','FixtureLaunchReceiptRequired')
                launch=json.loads(launched.read_text(encoding='utf-8'))
                require(launch.get('status')=='PASS_ISOLATED_TEST_LAUNCH_REQUESTED' and launch.get('apkSHA256')==value['apkSHA256'] and launch.get('fixture') in ('shuffle','notice','all') and re.fullmatch('[a-f0-9]{32}',launch.get('runNonce','')),'FixtureLaunchReceiptRequired')
                base='/sdcard/Android/data/'+PACKAGE+'/files/Review117Probe/'+launch['runNonce']+'/'
                raw=adb_bytes('exec-out','cat',base+'Report.json',serial=serial,maximum=65536)
                fixture=json.loads(raw.decode('utf-8'));scenario=fixture.get('scenario')
                expected={'shuffle':['Shuffle_0.png','Shuffle_1.png','Shuffle_2.png'],
                          'notice':['OutOfMovesNotice.png','ContinueOffer.png'],
                          'all':['Shuffle_0.png','Shuffle_1.png','Shuffle_2.png','OutOfMovesNotice.png','ContinueOffer.png']}
                require(fixture.get('status')=='PASS_DEVICE_FIXTURE' and scenario==launch['fixture'] and fixture.get('level')==launch.get('fixtureLevel') and fixture.get('runNonce')==launch['runNonce'] and fixture.get('screenshots')==expected[scenario],'CompletedFixtureRequired')
                private=ROOT/'.verification-cache/Review117/Physical'/a.tag;private.mkdir(parents=True,exist_ok=False)
                image_rows=[]
                for name in expected[scenario]:
                    data=adb_bytes('exec-out','cat',base+name,serial=serial,maximum=16*1024*1024)
                    require(len(data)>=24 and data[:8]==b'\x89PNG\r\n\x1a\n' and data[12:16]==b'IHDR','FixtureImageInvalid')
                    width,height=struct.unpack('>II',data[16:24]);require(width==fixture['width'] and height==fixture['height'],'FixtureImageSizeMismatch')
                    (private/name).write_bytes(data);image_rows.append({'name':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
                (private/'Report.json').write_bytes(raw)
                report.update(status='PASS_ISOLATED_DEVICE_FIXTURE_COLLECTED',apkSHA256=value['apkSHA256'],fixture=scenario,fixtureReportSHA256=hashlib.sha256(raw).hexdigest(),images=image_rows,privateEvidenceDirectory=private.relative_to(ROOT).as_posix(),physicalVisualApproved=False,performanceMeasured=False)
            else:
                require(a.preview and a.fixture is None and a.launch_receipt is not None and a.collect_receipt is not None,'CompletedPreviewFixtureRequired')
                launched=a.launch_receipt.resolve();collected=a.collect_receipt.resolve()
                require(launched.is_relative_to(EVIDENCE.resolve()) and launched.name=='Launch.json' and collected.is_relative_to(EVIDENCE.resolve()) and collected.name=='Collect.json','CompletedPreviewFixtureRequired')
                launch=json.loads(launched.read_text(encoding='utf-8'));collection=json.loads(collected.read_text(encoding='utf-8'))
                require(launch.get('status')=='PASS_ISOLATED_TEST_LAUNCH_REQUESTED' and launch.get('fixture') in ('shuffle','notice','all') and launch.get('apkSHA256')==value['apkSHA256'] and collection.get('status')=='PASS_ISOLATED_DEVICE_FIXTURE_COLLECTED' and collection.get('apkSHA256')==value['apkSHA256'] and collection.get('fixture')==launch['fixture'],'CompletedPreviewFixtureRequired')
                private=(ROOT/collection.get('privateEvidenceDirectory','')).resolve();require(private.is_relative_to((ROOT/'.verification-cache/Review117/Physical').resolve()),'CompletedPreviewFixtureRequired')
                raw=(private/'Report.json').read_bytes();fixture=json.loads(raw)
                require(hashlib.sha256(raw).hexdigest()==collection.get('fixtureReportSHA256') and fixture.get('status')=='PASS_DEVICE_FIXTURE' and fixture.get('runNonce')==launch.get('runNonce') and fixture.get('level')==launch.get('fixtureLevel'),'CompletedPreviewFixtureRequired')
                require(re.fullmatch('[a-f0-9]{64}',launch.get('processSHA256','')) is not None,'FixtureProcessIdentityRequired')
                fresh_serial,fresh_state=phone();require(fresh_serial==serial and not fresh_state['existingGameProcessRunning'] and fresh_state['testPackagePresent'],'FreshPhoneStateRequired')
                current,_=adb('shell','dumpsys','activity','activities',serial=serial)
                foreground=[line for line in current.splitlines() if 'mResumedActivity' in line or 'topResumedActivity' in line]
                require(any(PACKAGE+'/' in line for line in foreground),'PreviewMustBeForeground')
                require(process_identity(serial)==launch['processSHA256'],'FixtureProcessIdentityMismatch')
                adb('shell','am','force-stop',PACKAGE,serial=serial)
                running,code=adb('shell','pidof',PACKAGE,serial=serial,ok=(0,1));require(code==1 and not running,'PreviewStopNotConfirmed')
                report.update(status='PASS_SYNTHETIC_PREVIEW_STOPPED',apkSHA256=value['apkSHA256'],fixture=launch['fixture'],fixtureLevel=launch['fixtureLevel'],syntheticMemoryOnly=True,stoppedOnlyPreview=True)
    except Exception as error:
        report['errorType']=type(error).__name__;report['code']=str(error) if re.fullmatch('[A-Za-z0-9]{1,100}',str(error)) else 'DeviceOperationUnavailable'
    filename={'install':'Install.json','launch':'Launch.json','collect':'Collect.json','reset':'Reset.json'}[a.mode]
    (out/filename).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'report':(out/filename).relative_to(ROOT).as_posix()}))
    return 0 if report['status'].startswith('PASS_') else 1

if __name__=='__main__': raise SystemExit(main())
