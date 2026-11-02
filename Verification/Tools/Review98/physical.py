"""Explicit tests of the separate98 APK on the inventoried physical phone.

Only the fixed candidate can be stopped, installed or receive input/markers.
The owner package is read-only. Raw command output/video stays private.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Review93'))
import phone as old
PACKAGE='com.heartoftherain.review98'
OWNER='com.heartoftherain.verification'
INVENTORY=ROOT/'Verification/Evidence/Review98/DeviceInventory.json'


def sha(p):return old.sha(Path(p))
def utc():return datetime.now(timezone.utc).isoformat()
def bound(p):
    p=Path(p).resolve()
    return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
def save(p,r):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def observe_fluidity98(report):
    # Separate contract for the explicitly authorized Unity6 copy. Historical
    # 87/93 validators and their Unity2022 runtime pins remain unchanged.
    def require(value,message):
        if not value:raise ValueError(message)
    require(report.get('status')=='RECORDED_NATIVE_FLUIDITY' and report.get('errors')==[], 'Fluidity98NativeCompletionRequired')
    require(report.get('unity')=='6000.3.27f1' and report.get('platform')=='Android' and report.get('variant')=='candidate','Fluidity98ExactRuntimeRequired')
    require(report.get('isolatedProfile') is True and report.get('launchCleared') is True,'Fluidity98IsolationRequired')
    phases=report.get('phases',[]);samples=report.get('frameSamples',[])
    names=['idle_including_hint_search','natural_first','natural_second','rocket','three_rocket_chain','orb_rocket','golden_bomb','victory_animation']
    require([p.get('name') for p in phases]==names and samples,'Fluidity98PhaseInventoryRequired')
    for phase in phases:
        require(type(phase.get('frames')) is int and phase['frames']>0,'Fluidity98PhaseFramesRequired')
        for key in ('p50Ms','p95Ms','worstMs','modelMs','acceptMs','commandMs','settleSeconds'):
            value=phase.get(key);require(type(value) in (int,float) and math.isfinite(value) and value>=0,'Fluidity98FinitePhaseRequired')
    for frame in samples:
        require(type(frame.get('phase')) is int and 0<=frame['phase']<8 and type(frame.get('frame')) is int and frame['frame']>=0,'Fluidity98FrameIdentityRequired')
        for key in ('intervalMs','updateMs','renderMs','sampleMs'):
            value=frame.get(key);require(type(value) in (int,float) and math.isfinite(value) and value>=0,'Fluidity98FiniteFrameRequired')
    return dict(status='RECORDED_DIAGNOSTICS_NOT_SMOOTHNESS_APPROVAL',unity=report['unity'],platform='Android',
        phases=phases,frameSampleCount=len(samples),allFramesOver33msCount=sum(f['intervalMs']>33.34 for f in samples),
        allFramesOver50msCount=sum(f['intervalMs']>50 for f in samples),worstRecordedIntervalMs=max(f['intervalMs'] for f in samples),
        worstRecordedCommandMs=max(p['commandMs'] for p in phases),
        slowestFrames=[dict(f,phaseName=names[f['phase']]) for f in sorted(samples,key=lambda f:f['intervalMs'],reverse=True)[:20]],
        limitations=['Every raw frame and all eight phases remain in the bound original NativeReport.json; slower phases are retained.',
            'Command duration, player-loop wall interval, rendering sample and first-presentation dispatch are distinct measurements; no touch latency or universal frame-budget acceptance inferred.',
            'One Development build on one physical phone, before loading-copy correction. No recording/ADB queries during the255-second quiet interval; no production benchmark or smoothness certification.'])


class Physical:
    def __init__(self,out,build):
        self.out=out;self.private=ROOT/'.verification-cache/Review98/Physical'/out.name
        self.private.mkdir(parents=True,exist_ok=False);self.counter=0
        inventory=json.loads(INVENTORY.read_text('utf-8'))
        matches=[d for d in inventory['devices'] if d['state']=='device' and d['transport']=='physicalOrNetwork']
        if len(matches)!=1:raise ValueError('ExactSingleInventoriedPhysicalDeviceRequired')
        self.device=matches[0]
        self.serial=(ROOT/inventory['privateEvidenceDirectory']/'selected_device.txt').read_text()
        if hashlib.sha256(self.serial.encode()).hexdigest()!=self.device['selectorSHA256']:raise ValueError('PhysicalSelectorChanged')
        self.build=json.loads(build.read_text('utf-8-sig'))
        if self.build['status']!='PASS_NATIVE_REVIEW98_BUILDDEVELOPMENT' or self.build['unity']!='6000.3.27f1' or self.build['packageName']!=PACKAGE or self.build['errors']:
            raise ValueError('ActualSuccessful98DevelopmentBuildRequired')
        self.apk=Path(self.build['apk']);self.expected=self.build['apkSHA256']
        if sha(self.apk)!=self.expected:raise ValueError('CandidateApkChanged')
        self.base='/sdcard/Android/data/'+PACKAGE+'/files'
        self.identity()
    def adb(self,*args,binary=False,check=True,timeout=30):
        self.counter+=1;path=self.private/('%04d.out'%self.counter);err=self.private/('%04d.err'%self.counter)
        with path.open('xb') as o,err.open('xb') as e:
            result=subprocess.run([str(old.ADB),'-s',self.serial,*map(str,args)],stdout=o,stderr=e,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
        self.last_exit=result.returncode;self.last_error=err.read_bytes()
        if check and result.returncode:raise RuntimeError('OwnedPhysicalCommandFailed')
        data=path.read_bytes();return data if binary else data.decode('utf-8','replace').strip()
    def identity(self):
        if self.adb('get-state')!='device' or self.adb('shell','getprop','ro.product.model')!=self.device['model'] or self.adb('shell','getprop','ro.kernel.qemu')=='1':raise ValueError('InventoriedPhysicalPhoneUnavailable')
    def inventory(self,package):
        # Reuse only the original read-only hash/parser methods. The legacy
        # owner upgrade constructor and every legacy mutation method are unused.
        previous=old.PACKAGE;old.PACKAGE=package
        try:
            view=old.Phone.__new__(old.Phone);view.serial=self.serial
            view.base='/sdcard/Android/data/'+package+'/files'
            def read(*args,**kwargs):
                if package==PACKAGE and args==('shell','run-as',package,'ls','shared_prefs'):
                    value=self.adb(*args,check=False)
                    if self.last_exit==0:return value
                    if self.last_exit==1 and b'No such file or directory' in self.last_error:return ''
                    raise ValueError('CandidatePreferencesReadUnknown')
                return self.adb(*args,**kwargs)
            view.adb=read
            return view.inventory()
        finally:old.PACKAGE=previous
    def stable(self,package):
        if package==OWNER:
            value=self.adb('shell','pm','path',OWNER,check=False)
            if not value and self.last_exit==1 and not self.last_error:
                # The owner package disappeared externally between test turns.
                # Preserve this observed state and any remaining external files;
                # never recreate an earlier installation/profile to run tests.
                directory='/sdcard/Android/data/'+OWNER+'/files/Profiles'
                self.adb('shell','test','-e',directory,check=False)
                if self.last_exit not in (0,1) or self.last_error:raise ValueError('AbsentOwnerExternalStateUnknown')
                exists=self.last_exit==0;hashes={}
                if exists:
                    paths=self.adb('shell','find',directory,'-type','f').splitlines()
                    if len(paths)>4096:raise ValueError('AbsentOwnerExternalStateTooLarge')
                    for path in paths:
                        if not re.fullmatch(re.escape(directory)+r'/[A-Za-z0-9_./-]+',path):raise ValueError('AbsentOwnerExternalPathUnknown')
                        hashes[path.removeprefix(directory+'/')]=self.adb('shell','sha256sum',path).split()[0]
                return dict(installed=False,observedState='OWNER_PACKAGE_NOT_INSTALLED',externalProfilesDirectoryExists=exists,externalProfiles=hashes,scope='Fresh read-only absence baseline after external device state change; no owner reconstruction or mutation.')
            if not value or self.last_exit or not value.startswith('package:'):raise ValueError('OwnerInstallationStateUnknown')
        r=self.inventory(package)
        return {k:r[k] for k in ('profiles','preferences','profileSummaries','activeAttempts','installedSHA256')}
    def installed(self):
        r=self.stable(PACKAGE)
        if r['installedSHA256']!=self.expected or r['activeAttempts']:raise ValueError('ExactIdleSeparateCandidateRequired')
        return r
    def stop(self):
        self.identity();self.installed();self.adb('shell','am','force-stop',PACKAGE)
        if self.adb('shell','pidof',PACKAGE,check=False):raise ValueError('CandidateDidNotStop')
    def launch(self):
        self.identity();value=self.adb('shell','am','start','-W','-n',PACKAGE+'/com.unity3d.player.UnityPlayerActivity',timeout=45)
        pid=self.adb('shell','pidof',PACKAGE,check=False)
        self.candidate_pid=pid if re.fullmatch('[0-9]+',pid) else None
        return value
    def capture(self,name):
        raw=self.adb('shell','dumpsys','activity','activities')
        resumed=[s for s in raw.splitlines() if 'mResumedActivity:' in s or 'topResumedActivity=' in s]
        if not any(PACKAGE+'/' in s for s in resumed):raise ValueError('CandidateMustBeForegroundForCapture')
        # Android16's windows subcommand omits display-focus fields. Read the
        # actual WindowManager focus summary, retaining the strict app check.
        windows=self.adb('shell','dumpsys','window')
        focus=[s for s in windows.splitlines() if 'mCurrentFocus=' in s]
        if not any(PACKAGE+'/' in s for s in focus):raise ValueError('CandidateWindowMustHaveFocusForCapture')
        policy=self.adb('shell','dumpsys','window','policy').split('KeyguardServiceDelegate',1)[-1]
        if not re.search(r'(?m)^\s*showing=false\s*$',policy):raise ValueError('OwnerUnlockRequiredBeforeCapture')
        p=self.private/(name+'.png');p.write_bytes(self.adb('exec-out','screencap','-p',binary=True))
        if p.read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('ActualOsPngRequired')
        return bound(p)
    def push(self,name,data):
        if name not in ('HOTR_RunReview98','HOTR_Review98Step','HOTR_RunRegression','HOTR_RunNoMovesR2','HOTR_RunFluidity'):raise ValueError('ExactReviewedMarkerRequired')
        content=data.encode() if isinstance(data,str) else data
        if len(content)>2*1024*1024:raise ValueError('BoundedMarkerRequired')
        local=self.private/(name+'_'+str(self.counter));local.write_bytes(content)
        self.adb('shell','mkdir','-p',self.base)
        self.adb('push',str(local),self.base+'/'+name)
    def start(self,marker,content):
        self.stop();before=self.stable(PACKAGE)
        pending=self.adb('shell','find',self.base,'-maxdepth','1','-type','f','-name','HOTR_Run*',check=False)
        if pending:raise ValueError('PendingCandidateMarkerPreserved')
        self.push(marker,content);began=datetime.now(timezone.utc);self.launch();return began,before
    def tap(self,r):
        x,y=r['x'],r['y']
        if type(x)!=int or type(y)!=int or not 0<=x<720 or not 0<=y<1600:raise ValueError('NativePhysicalCoordinateBounds')
        self.adb('shell','input','tap',x,y)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true');p.add_argument('--tag',required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('action',choices=('install','upgrade','cold','fixture','extras','nomoves','regression','connected','fluidity'))
    p.add_argument('--previous-build',type=Path,help='Exact passing prior98 Development build for a candidate-only preserved upgrade')
    p.add_argument('--from-run',type=Path,help='Completed same-build memory-refill run retained in the current app process')
    p.add_argument('--mode',choices=('prelevel_899','prelevel_900','obstacle_intro'))
    p.add_argument('--fixtures',type=Path)
    p.add_argument('--scenario',choices=('offer','insufficient','shop','prepared','committed','repeat','repeat_insufficient','end','zero','below','exact','shop_bounds'))
    p.add_argument('--shop',action='store_true')
    p.add_argument('--record',action='store_true',help='30-second private capture during the actual repeat-move exhaustion case')
    args=p.parse_args()
    if not args.execute or not re.fullmatch(r'[A-Za-z0-9_]{1,40}',args.tag):p.error('Explicit short fresh physical test required')
    out=ROOT/'Verification/Evidence/Review98/Phone/Runs'/args.tag;out.mkdir(parents=True,exist_ok=False)
    result=dict(schemaVersion=1,status='RUNNING_PHYSICAL98',utc=utc(),action=args.action,mode=args.mode,
                runner=bound(Path(__file__)),buildReport=bound(args.build),captures=[],inputs=[],scope='Actual inventoried physical phone, separate98 internal app only. Native fixtures and programmatic regression do not certify human campaign, performance or live providers.')
    phone=None;repeat_recorder=None;record_remote=None
    try:
        phone=Physical(out,args.build);result['deviceSelectorSHA256']=phone.device['selectorSHA256']
        result['ownerBefore']=phone.stable(OWNER)
        if args.action=='install':
            existing=phone.adb('shell','pm','path',PACKAGE,check=False)
            if existing:raise ValueError('ExistingCandidatePreservedNoReplacement')
            if phone.last_exit not in (0,1) or phone.last_error:raise ValueError('CandidateAbsenceQueryUnknown')
            phone.adb('install','-t',str(phone.apk),timeout=180)
            result['candidateAfter']=phone.installed();result['status']='PASS_SEPARATE_PHYSICAL98_INSTALL'
        elif args.action=='upgrade':
            if not args.previous_build or not args.previous_build.resolve().is_relative_to((ROOT/'Verification/Evidence/Review98/Native').resolve()):raise ValueError('ExactPreviousNative98BuildRequired')
            previous=json.loads(args.previous_build.read_text('utf-8-sig'))
            if previous.get('status')!='PASS_NATIVE_REVIEW98_BUILDDEVELOPMENT' or previous.get('packageName')!=PACKAGE or previous.get('errors') or sha(previous['apk'])!=previous['apkSHA256']:raise ValueError('PreviousNative98ArtifactInvalid')
            before=phone.stable(PACKAGE)
            if before['installedSHA256']!=previous['apkSHA256'] or before['activeAttempts']:raise ValueError('PreviousIdleCandidateRequired')
            # Compare actual signer certificates; keys remain outside this script.
            android=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer');certs=[]
            for index,apk in enumerate((Path(previous['apk']),phone.apk)):
                r=subprocess.run([str(android/'OpenJDK/bin/java.exe'),'-jar',str(android/'SDK/build-tools/36.0.0/lib/apksigner.jar'),'verify','--print-certs',str(apk)],capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
                (phone.private/('Signer'+str(index)+'.out')).write_bytes(r.stdout);(phone.private/('Signer'+str(index)+'.err')).write_bytes(r.stderr)
                found=re.findall(r'(?m)^Signer #1 certificate SHA-256 digest: ([0-9a-f]{64})\s*$',r.stdout.decode('utf-8','replace'))
                if r.returncode or len(found)!=1:raise ValueError('ActualCandidateSigningIdentityUnknown')
                certs.append(found[0])
            if certs[0]!=certs[1]:raise ValueError('CandidateSigningIdentityChanged')
            result.update(previousBuild=bound(args.previous_build),candidateBefore=before,sameSigner=True)
            phone.adb('shell','am','force-stop',PACKAGE)
            if phone.adb('shell','pidof',PACKAGE,check=False) or phone.stable(PACKAGE)!=before:raise ValueError('CandidateChangedBeforeUpgrade')
            phone.adb('install','-r','-t',str(phone.apk),timeout=180)
            after=phone.installed();result['candidateAfter']=after
            result['candidateDataPreserved']={k:v for k,v in before.items() if k!='installedSHA256'}=={k:v for k,v in after.items() if k!='installedSHA256'}
            result['status']='PASS_SEPARATE_PHYSICAL98_PRESERVED_UPGRADE' if result['candidateDataPreserved'] else 'FAIL_PHYSICAL98_CANDIDATE_UPGRADE_PRESERVATION'
        elif args.action=='cold':
            phone.stop();result['candidateBefore']=phone.stable(PACKAGE)
            if phone.adb('shell','find',phone.base,'-maxdepth','1','-type','f','-name','HOTR_Run*',check=False):raise ValueError('PendingCandidateMarkerPreserved')
            result['normalUnmarkedLaunch']=True
            phone.adb('shell','input','keyevent','KEYCODE_WAKEUP')
            policy=phone.adb('shell','dumpsys','window','policy').split('KeyguardServiceDelegate',1)[-1]
            if not re.search(r'(?m)^\s*showing=false\s*$',policy):raise ValueError('OwnerUnlockRequiredBeforeRecording')
            result['normalWakeRequested']=True
            phone.adb('shell','mkdir','-p',phone.base+'/Review98')
            remote=phone.base+'/Review98/ColdLaunch.mp4';log=phone.private/'screenrecord.out'
            with log.open('xb') as stream:
                recorder=subprocess.Popen([str(old.ADB),'-s',phone.serial,'shell','screenrecord','--time-limit','20','--bit-rate','4000000',remote],stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(1);result['nativeLaunchUtc']=utc();phone.launch();recorder.wait(timeout=30)
            if recorder.returncode:raise ValueError('ActualPhysicalScreenrecordFailed')
            video=phone.private/'ColdLaunch.mp4';phone.adb('pull',remote,str(video),timeout=45)
            result['privateVideo']=bound(video);result['captures'].append(phone.capture('ColdLaunch_End_OS'))
            result['candidateAfter']=phone.stable(PACKAGE)
            result['candidatePreserved']=result['candidateBefore']==result['candidateAfter']
            result['status']='RECORDED_PHYSICAL98_COLD_LAUNCH_REQUIRES_VISUAL_REVIEW'
        elif args.action=='extras':
            if not args.from_run or not args.from_run.resolve().is_relative_to((ROOT/'Verification/Evidence/Review98/Phone/Runs').resolve()):raise ValueError('ExplicitMemoryHomePredecessorRequired')
            previous=json.loads(args.from_run.read_text('utf-8'))
            before=phone.installed()
            if previous.get('status')!='PASS_PHYSICAL98_FIXTURE' or previous.get('mode')!='prelevel_900' or previous.get('candidateAfter')!=before or previous.get('buildReport')!=result['buildReport']:raise ValueError('SamePreservedMemoryHomePredecessorRequired')
            result.update(precedingRun=bound(args.from_run),candidateBefore=before)
            phone.candidate_pid=phone.adb('shell','pidof',PACKAGE)
            result['captures'].append(phone.capture('Home_BeforeExtras_OS'))
            for name,x,y in (('DailyGift',90,400),('RainCup',640,400),('Wellworks',90,600),('Quest',640,600),('Profile',85,130),('Settings',650,140)):
                phone.adb('shell','input','tap',x,y);result['inputs'].append(dict(kind='tap',purpose=name,x=x,y=y,utc=utc()));time.sleep(1.5)
                result['captures'].append(phone.capture(name+'_OS'))
                phone.adb('shell','input','keyevent','4');result['inputs'].append(dict(kind='AndroidBack',purpose=name,utc=utc()));time.sleep(1)
                result['captures'].append(phone.capture('AfterBack_'+name+'_OS'))
            result['candidateAfter']=phone.stable(PACKAGE);result['candidatePreserved']=before==result['candidateAfter']
            result['status']='RECORDED_PHYSICAL98_EXTRA_UI_REQUIRES_VISUAL_REVIEW' if result['candidatePreserved'] else 'FAIL_PHYSICAL98_CANDIDATE_PRESERVATION'
            result['extraUiScope']='Actual fixed-target taps and OS frames in the existing transient review process. No claim/purchase/provider action; routing and visual correctness require independent review.'
        else:
            if args.action=='fixture':
                if not args.mode:raise ValueError('ExactReviewedFixtureModeRequired')
                marker,content,remote='HOTR_RunReview98',args.mode,'Review98Device/Report.json';deadline=200
            elif args.action=='nomoves':
                if not args.fixtures or not args.scenario or not args.fixtures.resolve().is_relative_to((ROOT/'Verification/Evidence/Review98/Native').resolve()):
                    raise ValueError('FreshNative98NoMovesFixtureRequired')
                entries=json.loads(args.fixtures.read_text('utf-8-sig'))['entries']
                rows=[row for row in entries if row['scenario']==args.scenario]
                if len(rows)!=1:raise ValueError('ExactSingleNoMovesScenarioRequired')
                result['fixtureSource']=bound(args.fixtures);result['scenario']=args.scenario
                marker,content,remote='HOTR_RunNoMovesR2',json.dumps(rows[0],ensure_ascii=True),'NoMovesR2Device/Report.json';deadline=200
            elif args.action=='fluidity':marker,content,remote='HOTR_RunFluidity','candidate','Fluidity/Measurement.json';deadline=90
            elif args.action=='connected':marker,content,remote='HOTR_RunRegression','connected-only98','Regression/Regression.json';deadline=900
            else:marker,content,remote='HOTR_RunRegression','run','Regression/Regression.json';deadline=1800
            began,before=phone.start(marker,content);result['candidateBefore']=before;result['nativeLaunchUtc']=began.isoformat()
            if args.action=='fluidity':
                # No ADB polling, screenshots, recording or readbacks while
                # any phase can still be measured by this bounded native probe.
                quiet_until=time.monotonic()+255;progress=time.monotonic()+30
                while time.monotonic()<quiet_until:
                    time.sleep(min(10,max(0,quiet_until-time.monotonic())))
                    if time.monotonic()>=progress:
                        print(json.dumps({'status':'QUIET_NATIVE_FLUIDITY98_NO_ADB','remainingSeconds':max(0,round(quiet_until-time.monotonic()))}),flush=True);progress+=30
                result['quietObservationSeconds']=255
            sent=set();until=time.monotonic()+deadline;native=None
            while time.monotonic()<until:
                raw=phone.adb('exec-out','cat',phone.base+'/'+remote,binary=True,check=False)
                try:
                    native=json.loads(raw);stamp=native.get('utc','');fresh=datetime.fromisoformat(stamp.replace('Z','+00:00'))>=began
                except (ValueError,TypeError):fresh=False
                if not fresh:time.sleep(1);continue
                status=native.get('status','')
                if status.startswith('READY_') and status not in sent:
                    result['captures'].append(phone.capture(status))
                    if args.record and repeat_recorder is None:
                        if args.action!='nomoves' or args.scenario!='repeat':raise ValueError('OnlyRepeatExhaustionRecordingReviewed')
                        phone.adb('shell','mkdir','-p',phone.base+'/Review98');record_remote=phone.base+'/Review98/RepeatMoves.mp4'
                        with (phone.private/'repeat_screenrecord.out').open('xb') as stream:
                            repeat_recorder=subprocess.Popen([str(old.ADB),'-s',phone.serial,'shell','screenrecord','--time-limit','30','--bit-rate','4000000',record_remote],stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                        time.sleep(1)
                        result['repeatRecordingScope']='Actual taps and unaccelerated repeated exhaustion, with recording overhead; no frame-time/smoothness certification.'
                    if status=='READY_FOR_SCROLL':
                        values=[native.get(k) for k in ('x','y','endX','endY')]
                        if any(type(v)!=int for v in values) or not all(0<=x<720 and 0<=y<1600 for x,y in zip(values[::2],values[1::2])):
                            raise ValueError('NativePhysicalScrollCoordinateBounds')
                        phone.adb('shell','input','swipe',*values,650)
                        result['inputs'].append(dict(kind='swipe',status=status,coordinates=values,utc=utc()))
                    else:
                        phone.tap(native)
                        result['inputs'].append(dict(kind='tap',status=status,x=native['x'],y=native['y'],utc=utc()))
                    sent.add(status)
                    if status=='READY_FOR_DISABLED_REFILL_TAP':phone.push('HOTR_Review98Step','verify')
                if status.startswith(('PASS','FAIL')) or args.action=='fluidity' and status=='RECORDED_NATIVE_FLUIDITY':break
                time.sleep(1)
            else:raise TimeoutError('ActualPhysicalFixtureDeadline')
            native_path=out/'NativeReport.json';native_path.write_bytes(raw);result['nativeReport']=bound(native_path)
            result['captures'].append(phone.capture('Final_OS'));result['candidateAfter']=phone.stable(PACKAGE)
            result['candidatePreserved']=before==result['candidateAfter']
            good=(status.startswith('PASS') or status=='RECORDED_NATIVE_FLUIDITY') and not native.get('error') and not native.get('errors') and not native.get('failures') and result['candidatePreserved']
            if args.action=='connected':good=good and status=='PASS_NATIVE_CONNECTED_REGRESSION98' and native.get('connectedOnly') is True and native.get('boards')==0 and native.get('clips')==0
            if args.action=='regression':good=good and status=='PASS_NATIVE_REGRESSION' and not native.get('connectedOnly',False) and native.get('boards')==50
            result['status']='PASS_PHYSICAL98_'+args.action.upper() if good else 'FAIL_PHYSICAL98_'+args.action.upper()
            if args.action=='fluidity' and good:
                result['observations']=observe_fluidity98(native);result['status']='RECORDED_PHYSICAL98_FLUIDITY_NOT_SMOOTHNESS_APPROVAL'
            if args.shop and good:
                if args.action!='fixture' or args.mode!='prelevel_900':raise ValueError('ShopCaptureRequiresMemoryRefillFixture')
                phone.adb('shell','input','keyevent','4');result['inputs'].append(dict(kind='AndroidBack',utc=utc()));time.sleep(1)
                result['captures'].append(phone.capture('Home_AfterRefill'))
                phone.adb('shell','input','tap','650','1530');result['inputs'].append(dict(kind='tap',x=650,y=1530,purpose='Shop navigation observation',utc=utc()));time.sleep(2)
                result['captures'].append(phone.capture('Shop_Top_OS'))
                for i in range(3):
                    phone.adb('shell','input','swipe','350','1260','350','410','700');result['inputs'].append(dict(kind='swipe',coordinates=[350,1260,350,410],utc=utc()));time.sleep(1)
                    result['captures'].append(phone.capture('Shop_Scroll_'+str(i+1)+'_OS'))
                # The five real navigation hit targets on this exact720x1600
                # device. Images require independent visual review of routing.
                for name,x in (('Journey',72),('Leaderboard',216),('Home',360),('Teams',504),('Shop',648),('Home_Return',360)):
                    phone.adb('shell','input','tap',x,1530);result['inputs'].append(dict(kind='tap',x=x,y=1530,purpose='Normal page observation '+name,utc=utc()));time.sleep(1.25)
                    result['captures'].append(phone.capture('NormalPage_'+name+'_OS'))
                result['shopVisualApproval']=False;result['shopScope']='Explicit navigation/scroll observations require separate root image review; no live checkout or automatically inferred Shop success.'
                result['candidateAfter']=phone.stable(PACKAGE);result['candidatePreserved']=before==result['candidateAfter']
                if not result['candidatePreserved']:result['status']='FAIL_PHYSICAL98_CANDIDATE_PRESERVATION'
    except Exception as error:
        result.update(status='FAIL_PHYSICAL98_'+args.action.upper(),errorType=type(error).__name__)
        if re.fullmatch(r'[A-Za-z0-9_]{1,100}',str(error)):result['errorCategory']=str(error)
    finally:
        if repeat_recorder:
            try:
                repeat_recorder.wait(timeout=40)
                if repeat_recorder.returncode:raise ValueError('RepeatRecordingFailed')
                video=phone.private/'RepeatMoves.mp4';phone.adb('pull',record_remote,str(video),timeout=45)
                result['privateRepeatVideo']=bound(video)
            except Exception as error:
                if repeat_recorder.poll() is None:repeat_recorder.kill();repeat_recorder.wait(timeout=10)
                result['repeatRecordingErrorType']=type(error).__name__
        if phone:
            if getattr(phone,'candidate_pid',None):
                try:
                    logs=phone.adb('logcat','-d','--pid',phone.candidate_pid,'-v','threadtime',binary=True,timeout=45)
                    logpath=phone.private/'Candidate_Logcat.txt';logpath.write_bytes(logs);result['privateCandidateLogcat']=bound(logpath)
                    text=logs.decode('utf-8','replace')
                    result['selectedUnityErrorLines']=len(re.findall(r'(?m)^.*\bE\s+Unity\s*:.*$',text))
                    result['selectedUnityWarningLines']=len(re.findall(r'(?m)^.*\bW\s+Unity\s*:.*$',text))
                    result['fatalSignatureCount']=len(re.findall(r'FATAL EXCEPTION|Fatal signal',text))
                    if (result['selectedUnityErrorLines'] or result['fatalSignatureCount']) and result['status'].startswith(('PASS_','RECORDED_')):
                        result['status']='FAIL_PHYSICAL98_UNEXPECTED_RUNTIME_ERROR'
                except Exception as error:result['logcatReadErrorType']=type(error).__name__
            try:
                result['ownerAfter']=phone.stable(OWNER);result['ownerPreserved']=result['ownerBefore']==result['ownerAfter']
                if not result['ownerPreserved']:result['status']='FAIL_PHYSICAL98_OWNER_PRESERVATION'
            except Exception as error:result['ownerAfterErrorType']=type(error).__name__;result['status']='FAIL_PHYSICAL98_FINAL_OWNER_READBACK'
        result['finishedUtc']=utc();save(out/'Report.json',result)
    print(json.dumps({'status':result['status'],'report':(out/'Report.json').relative_to(ROOT).as_posix()}),flush=True)
    return 0 if result['status'].startswith(('PASS_','RECORDED_')) else 1


if __name__=='__main__':raise SystemExit(main())
