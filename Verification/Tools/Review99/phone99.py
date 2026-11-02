"""Bounded99 startup/icon inspection of the existing separate review98 app.

Reuses98's read-only save/identity primitives; all new output is under99.
No owner installation, clearing, security configuration or global ADB reset.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Verification/Tools/Review98'))
import physical as previous
PACKAGE=previous.PACKAGE
OWNER=previous.OWNER

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')

class Device99(previous.Physical):
    def __init__(self,out,build):
        self.out=out;self.private=ROOT/'.verification-cache/Review99/Phone'/out.name
        self.private.mkdir(parents=True,exist_ok=False);self.counter=0
        inventory=json.loads(previous.INVENTORY.read_text('utf-8'))
        matches=[d for d in inventory['devices'] if d['state']=='device' and d['transport']=='physicalOrNetwork']
        if len(matches)!=1:raise ValueError('ExactInventoriedPhysicalPhoneRequired99')
        self.device=matches[0]
        self.serial=(ROOT/inventory['privateEvidenceDirectory']/'selected_device.txt').read_text()
        if hashlib.sha256(self.serial.encode()).hexdigest()!=self.device['selectorSHA256']:raise ValueError('PhysicalSelectorChanged99')
        self.build=json.loads(build.read_text('utf-8-sig'))
        if self.build.get('status') not in ('PASS_NATIVE_REVIEW98_BUILDDEVELOPMENT','PASS_NATIVE_REVIEW99_BUILDDEVELOPMENT') or self.build.get('unity')!='6000.3.27f1' or self.build.get('packageName')!=PACKAGE or self.build.get('errors'):raise ValueError('ExactApprovedDevelopmentBuildRequired99')
        self.apk=Path(self.build['apk']);self.expected=self.build['apkSHA256']
        if previous.sha(self.apk)!=self.expected:raise ValueError('CandidateApkChanged99')
        self.base='/sdcard/Android/data/'+PACKAGE+'/files';self.identity()
        if self.adb('shell','am','get-current-user')!='0':raise ValueError('UnexpectedPhoneUser99')
    def unlocked(self):
        self.adb('shell','input','keyevent','KEYCODE_WAKEUP')
        policy=self.adb('shell','dumpsys','window','policy').split('KeyguardServiceDelegate',1)[-1]
        if not re.search(r'(?m)^\s*showing=false\s*$',policy):raise ValueError('OwnerUnlockRequired99')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true');p.add_argument('--tag',required=True)
    p.add_argument('--build',type=Path,required=True);p.add_argument('action',choices=('baseline','launcher','upgrade','intro','shop','relaunch'))
    p.add_argument('--previous-build',type=Path);p.add_argument('--background',action='store_true')
    args=p.parse_args()
    if not args.execute or not re.fullmatch('[A-Za-z0-9_]{1,40}',args.tag):p.error('Explicit bounded99 action required')
    out=ROOT/'Verification/Evidence/Review99/Phone'/args.tag;out.mkdir(parents=True,exist_ok=False)
    source=Path(__file__);snapshot=ROOT/'.verification-cache/Review99/ToolSources'/(previous.sha(source)+'.py');snapshot.parent.mkdir(parents=True,exist_ok=True)
    if not snapshot.exists():shutil.copyfile(source,snapshot)
    if previous.sha(snapshot)!=previous.sha(source):raise ValueError('Frozen99ToolSourceChanged')
    record=dict(schemaVersion=1,status='RUNNING_PHYSICAL99',action=args.action,utc=previous.utc(),runner=previous.bound(snapshot),runnerOriginalPath=source.relative_to(ROOT).as_posix(),build=previous.bound(args.build),captures=[],scope='One inventoried physical phone, existing separate review98 candidate. Bounded startup/launcher/Shop observations and opt-in memory introduction fixtures; no whole-device, human campaign or production certification.')
    phone=None;recorder=None;logger=None;logstream=None;watcher=None;watchstream=None
    try:
        phone=Device99(out,args.build);record['selectorSHA256']=phone.device['selectorSHA256'];phone.unlocked()
        record['ownerBefore']=phone.stable(OWNER);record['candidateBefore']=phone.stable(PACKAGE) if args.action=='upgrade' else phone.installed()
        if args.action=='upgrade':
            if not args.previous_build:raise ValueError('ExactPreviousNativeBuildRequired99')
            prior=json.loads(args.previous_build.read_text('utf-8-sig'));before=record['candidateBefore']
            if prior.get('status') not in ('PASS_NATIVE_REVIEW98_BUILDDEVELOPMENT','PASS_NATIVE_REVIEW99_BUILDDEVELOPMENT') or prior.get('packageName')!=PACKAGE or prior.get('errors') or previous.sha(prior['apk'])!=prior['apkSHA256']:raise ValueError('PreviousCandidateArtifactInvalid99')
            if before['installedSHA256']!=prior['apkSHA256'] or before['activeAttempts']:raise ValueError('ExactIdlePreviousCandidateRequired99')
            android=Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer');certs=[]
            for index,apk in enumerate((Path(prior['apk']),phone.apk)):
                result=subprocess.run([str(android/'OpenJDK/bin/java.exe'),'-jar',str(android/'SDK/build-tools/36.0.0/lib/apksigner.jar'),'verify','--print-certs',str(apk)],capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
                (phone.private/('Signer'+str(index)+'.out')).write_bytes(result.stdout);(phone.private/('Signer'+str(index)+'.err')).write_bytes(result.stderr)
                found=re.findall(r'(?m)^Signer #1 certificate SHA-256 digest: ([0-9a-f]{64})\s*$',result.stdout.decode('utf-8','replace'))
                if result.returncode or len(found)!=1:raise ValueError('SigningIdentityUnknown99')
                certs.append(found[0])
            if certs[0]!=certs[1]:raise ValueError('CandidateSigningIdentityChanged99')
            phone.adb('shell','am','force-stop',PACKAGE)
            if phone.adb('shell','pidof',PACKAGE,check=False) or phone.stable(PACKAGE)!=before:raise ValueError('CandidateChangedBeforeUpgrade99')
            phone.adb('install','-r','-t',str(phone.apk),timeout=180);phone.installed()
            record.update(previousBuild=previous.bound(args.previous_build),sameSigner=True,status='PASS_PHYSICAL99_PRESERVED_CANDIDATE_UPGRADE')
        elif args.action=='intro':
            phone.stop()
            if phone.adb('shell','find',phone.base,'-maxdepth','1','-type','f','-name','HOTR_Run*',check=False):raise ValueError('PendingCandidateMarkerPreserved99')
            phone.push('HOTR_RunReview98','obstacle_intro');began=datetime.now(timezone.utc)
            phone.adb('shell','mkdir','-p',phone.base+'/Review99');remote=phone.base+'/Review99/'+args.tag+'.mp4'
            if args.background:
                # Trigger on the phone: host screenshots/dumps take too long for
                # this1.5s card. Old Background01 remains a gameplay-pause case.
                watchdir=phone.base+'/Review99/'+args.tag
                script=phone.private/'IntroPauseWatcher.sh'
                script.write_text('''#!/system/bin/sh
set -eu
p="'''+phone.base+'''/Review98Device/Report.json"
d="'''+watchdir+'''"
mkdir -p "$d"
end=$(( $(date +%s) + 160 ))
while [ "$(date +%s)" -lt "$end" ]; do
  if [ -f "$p" ]; then
    cat "$p" > "$d/Sample.json"
    if grep -q '"status": "OBSERVING_OBSTACLE_AUTO"' "$d/Sample.json" && grep -Eq '"visibleForegroundSeconds": (0[.]0*[1-9]|[1-9])' "$d/Sample.json"; then
      cp "$d/Sample.json" "$d/BeforePause.json"
      cat /proc/uptime > "$d/BeforeHome.uptime"
      input keyevent KEYCODE_HOME
      cat /proc/uptime > "$d/AfterHome.uptime"
      sleep 3
      cat "$p" > "$d/WhilePaused.json"
      cat /proc/uptime > "$d/BeforeResume.uptime"
      am start -W -n '''+PACKAGE+'''/com.unity3d.player.UnityPlayerActivity
      cat /proc/uptime > "$d/AfterResume.uptime"
      echo COMPLETED_VISIBLE_INTRO_PAUSE99
      exit 0
    fi
  fi
  sleep .02
done
exit 23
''',encoding='ascii',newline='\n')
                phone.adb('push',str(script),watchdir+'.sh')
                record['prearmedWatcher']=previous.bound(script)
                watchstream=(phone.private/'Watcher.out').open('xb')
                watcher=subprocess.Popen([str(previous.old.ADB),'-s',phone.serial,'shell','sh',watchdir+'.sh'],stdout=watchstream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            with (phone.private/'Screenrecord.out').open('xb') as stream:
                recorder=subprocess.Popen([str(previous.old.ADB),'-s',phone.serial,'shell','screenrecord','--time-limit','30','--bit-rate','4000000',remote],stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(1);phone.launch();deadline=time.monotonic()+190;observed=False;raw=b''
                if watcher:
                    watcher.wait(timeout=175)
                    if watcher.returncode:raise ValueError('PrearmedIntroPauseTriggerFailed99')
                    record['backgroundSnapshots']={}
                    for name in ('BeforePause','WhilePaused'):
                        body=phone.adb('exec-out','cat',watchdir+'/'+name+'.json',binary=True)
                        path=out/(name+'Native.json');path.write_bytes(body)
                        record['backgroundSnapshots'][name]=previous.bound(path)
                    for name in ('BeforeHome','AfterHome','BeforeResume','AfterResume'):
                        stamp=phone.adb('exec-out','cat',watchdir+'/'+name+'.uptime').split()[0]
                        record.setdefault('backgroundUptime',{})[name]=float(stamp)
                    observed=True
                while time.monotonic()<deadline:
                    raw=phone.adb('exec-out','cat',phone.base+'/Review98Device/Report.json',binary=True,check=False)
                    try:
                        native=json.loads(raw);fresh=datetime.fromisoformat(native['utc'].replace('Z','+00:00'))>=began
                    except (ValueError,TypeError,KeyError):fresh=False
                    if not fresh:time.sleep(.1);continue
                    status=native.get('status','')
                    if status=='OBSERVING_OBSTACLE_AUTO' and not observed:
                        observed=True;record['captures'].append(phone.capture('Timed_Obstacle_OS'))
                    if status.startswith(('PASS','FAIL')):break
                    time.sleep(.1)
                else:raise TimeoutError('TimedObstacleFixtureDeadline99')
                recorder.wait(timeout=40)
            if recorder.returncode:raise ValueError('TimedObstacleRecordingFailed99')
            video=phone.private/'Timed_Obstacle.mp4';phone.adb('pull',remote,str(video),timeout=60)
            report=out/'NativeReport.json';report.write_bytes(raw)
            record.update(video=previous.bound(video),nativeReport=previous.bound(report),observationStateSeen=observed,backgroundRequested=args.background)
            record['captures'].append(phone.capture('Timed_Obstacle_Final_OS'))
            if status!='PASS_NATIVE_REVIEW99_OBSTACLE_FIXTURE' or native.get('error') or not native.get('autoDismissed') or native.get('rocketBefore')!=5 or native.get('rocketAfter')!=4:raise ValueError('ActualTimedObstacleFixtureFailed99')
            if args.background and (native.get('backgroundEntries',0)<1 or native.get('resumes',0)<1):raise ValueError('ActualIntroBackgroundBoundaryNotObserved99')
            if args.background:
                before=json.loads((out/'BeforePauseNative.json').read_bytes());paused=json.loads((out/'WhilePausedNative.json').read_bytes())
                for snapshot in (before,paused):
                    if snapshot.get('utc')!=native['utc'] or snapshot.get('status')!='OBSERVING_OBSTACLE_AUTO' or snapshot.get('attemptState')!='Reserved' or snapshot.get('rocketBefore')!=5 or snapshot.get('coins')!=1250 or snapshot.get('lives')!=5:raise ValueError('VisibleReservedIntroPauseSnapshotRequired99')
                if not 0<float(before.get('visibleForegroundSeconds',-1))<.75 or not paused.get('paused') or paused.get('backgroundEntries',0)<1 or not float(before['visibleForegroundSeconds'])<=float(paused['visibleForegroundSeconds'])<1.5:raise ValueError('IntroMustRemainVisibleReservedWhileBackgrounded99')
                record['backgroundHeldSeconds']=record['backgroundUptime']['BeforeResume']-record['backgroundUptime']['AfterHome']
                if record['backgroundHeldSeconds']<3:raise ValueError('ThreeSecondActualBackgroundRequired99')
                record['introPauseBoundaryNativeVerified']=True
            record['status']='PASS_PHYSICAL99_TIMED_OBSTACLE_FIXTURE'
        elif args.action=='shop':
            record['inputs']=[]
            phone.adb('shell','input','tap',648,1530);time.sleep(2)
            record['captures'].append(phone.capture('Shop_Top_OS'))
            for index in range(2):
                phone.adb('shell','input','swipe',620,800,90,800,550);time.sleep(1)
                record['inputs'].append(dict(kind='swipe',coordinates=[620,800,90,800],purpose='Observe next Special offer'))
                record['captures'].append(phone.capture('Shop_Special_'+str(index+2)+'_OS'))
            for index in range(4):
                phone.adb('shell','input','swipe',350,1250,350,670,650);time.sleep(1)
                record['inputs'].append(dict(kind='swipe',coordinates=[350,1250,350,670],purpose='Observe Mega offers and unchanged coin packs'))
                record['captures'].append(phone.capture('Shop_Vertical_'+str(index+1)+'_OS'))
            phone.adb('shell','input','tap',360,1530);time.sleep(1)
            record['captures'].append(phone.capture('Home_AfterShop_OS'))
            record['status']='RECORDED_PHYSICAL99_SHOP_PRICES_REQUIRES_REVIEW'
        elif args.action=='relaunch':
            phone.stop()
            if phone.adb('shell','find',phone.base,'-maxdepth','1','-type','f','-name','HOTR_Run*',check=False):raise ValueError('PendingCandidateMarkerPreserved99')
            logstream=(phone.private/'Startup_Logcat.txt').open('xb')
            logger=subprocess.Popen([str(previous.old.ADB),'-s',phone.serial,'logcat','-T','1','-v','monotonic','Unity:I','HOTR99:I','*:S'],stdout=logstream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            phone.launch();deadline=time.monotonic()+50;ready=False
            while time.monotonic()<deadline:
                text=(phone.private/'Startup_Logcat.txt').read_text('utf-8',errors='replace')
                ready=any(re.match(r'^\s*[0-9.]+\s+'+str(phone.candidate_pid)+r'\s+',line) and 'HOTR_STARTUP99 stage=route_home ' in line for line in text.splitlines())
                if ready:break
                time.sleep(.1)
            if not ready:raise ValueError('FreshNormalHomeRouteSignalRequired99')
            record['normalUnmarkedHomeRouteObserved']=True
            record['captures'].append(phone.capture('Normal_Home_OS'))
            record['status']='RECORDED_PHYSICAL99_NORMAL_HOME_RELAUNCH_REQUIRES_REVIEW'
        elif args.action=='baseline':
            phone.stop()
            if phone.adb('shell','find',phone.base,'-maxdepth','1','-type','f','-name','HOTR_Run*',check=False):raise ValueError('PendingCandidateMarkerPreserved99')
            phone.adb('shell','mkdir','-p',phone.base+'/Review99')
            remote=phone.base+'/Review99/'+args.tag+'.mp4'
            logstream=(phone.private/'Startup_Logcat.txt').open('xb')
            logger=subprocess.Popen([str(previous.old.ADB),'-s',phone.serial,'logcat','-T','1','-v','monotonic','Unity:V','UnityPlayer:V','ActivityTaskManager:I','ActivityManager:I','HOTR99:I','*:S'],stdout=logstream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            with (phone.private/'Screenrecord.out').open('xb') as stream:
                recorder=subprocess.Popen([str(previous.old.ADB),'-s',phone.serial,'shell','screenrecord','--time-limit','45','--bit-rate','4000000',remote],stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(1)
                record['phoneUptimeBeforeRequest']=phone.adb('shell','cat','/proc/uptime').split()[0]
                record['launchRequestedUtc']=previous.utc();started=time.monotonic()
                record['amStartResult']=phone.launch();record['amStartWallSeconds']=time.monotonic()-started
                print(json.dumps({'status':'RECORDING_PHYSICAL99_STARTUP','tag':args.tag}),flush=True)
                recorder.wait(timeout=60)
            if recorder.returncode:raise ValueError('PhysicalStartupRecordingFailed99')
            video=phone.private/'Startup.mp4';phone.adb('pull',remote,str(video),timeout=60)
            record['video']=previous.bound(video);record['captures'].append(phone.capture('Startup_End_OS'))
            record['status']='RECORDED_PHYSICAL99_STARTUP_REQUIRES_REVIEW'
        elif args.action=='launcher':
            # Only the own-app icon crop leaves the private full launcher frame.
            packages=phone.adb('shell','pm','list','packages','--user','0','com.heartoftherain').splitlines()
            if packages!=['package:'+PACKAGE]:raise ValueError('LauncherLabelAmbiguousAcrossHeartRainPackages99')
            phone.adb('shell','input','keyevent','KEYCODE_HOME');time.sleep(1)
            nodes=[]
            for attempt in range(13):
                dump=phone.adb('exec-out','uiautomator','dump','/dev/tty',timeout=45)
                xml=dump[dump.find('<?xml'):dump.rfind('</hierarchy>')+len('</hierarchy>')]
                tree=ET.fromstring(xml)
                def own(n):return any(' '.join(n.attrib.get(k,'').split())=='Сердце дождя' for k in ('text','content-desc'))
                nodes=[n for n in tree.iter('node') if own(n)]
                if nodes:break
                if attempt==12:break
                phone.adb('shell','input','swipe',360,1450 if attempt==0 else 1300,360,400,550);time.sleep(.5)
                record.setdefault('launcherSearchSwipes',0);record['launcherSearchSwipes']+=1
            clickable=[n for n in nodes if n.attrib.get('clickable')=='true']
            if clickable:nodes=clickable
            unique={n.attrib.get('bounds'):n for n in nodes};nodes=list(unique.values())
            if len(nodes)!=1:raise ValueError('OwnLauncherIconNotUniquelyVisible99')
            bounds=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',nodes[0].attrib['bounds'])
            if not bounds:raise ValueError('OwnLauncherIconBoundsUnknown99')
            box=tuple(map(int,bounds.groups()))
            if not 0<=box[0]<box[2]<=720 or not 0<=box[1]<box[3]<=1600:raise ValueError('OwnLauncherBoundsInvalid99')
            if box[2]-box[0]>240 or box[3]-box[1]>300:raise ValueError('OwnIconCropWouldIncludeOtherContent99')
            raw=phone.private/'Launcher_Private.png';raw.write_bytes(phone.adb('exec-out','screencap','-p',binary=True))
            from PIL import Image
            crop=phone.private/'Own_Launcher_Icon.png'
            with Image.open(raw) as frame:frame.crop(box).save(crop)
            record.update(iconCrop=previous.bound(crop),iconBounds=box,privateFullLauncher=previous.bound(raw),status='RECORDED_PHYSICAL99_LAUNCHER_ICON_REQUIRES_REVIEW')
            phone.launch()
        record['candidateAfter']=phone.stable(PACKAGE)
        def data(value):return {k:v for k,v in value.items() if k!='installedSHA256'} if args.action=='upgrade' else value
        record['candidateDataPreserved']=data(record['candidateBefore'])==data(record['candidateAfter'])
        if not record['candidateDataPreserved']:record['status']='REVIEW_PHYSICAL99_CANDIDATE_STATE_CHANGE'
    except Exception as error:
        record.update(status='STOPPED_PHYSICAL99',errorType=type(error).__name__)
        if re.fullmatch('[A-Za-z0-9_]{1,120}',str(error)):record['errorCategory']=str(error)
    finally:
        if logger:
            logger.terminate()
            try:logger.wait(timeout=10)
            except subprocess.TimeoutExpired:logger.kill();logger.wait(timeout=10)
        if logstream:logstream.close();record['privateStartupLog']=previous.bound(phone.private/'Startup_Logcat.txt')
        if watcher and watcher.poll() is None:
            watcher.terminate();watcher.wait(timeout=10)
        if watchstream:watchstream.close();record['privateWatcherOutput']=previous.bound(phone.private/'Watcher.out')
        if recorder and recorder.poll() is None:recorder.wait(timeout=60)
        if phone:
            if args.action=='launcher':
                try:phone.launch()
                except Exception as error:record['returnToCandidateErrorType']=type(error).__name__
            try:
                record['ownerAfter']=phone.stable(OWNER);record['ownerStatePreserved']=record['ownerBefore']==record['ownerAfter']
                if not record['ownerStatePreserved']:record['status']='STOPPED_PHYSICAL99_OWNER_STATE_CHANGED'
            except Exception as error:record['ownerReadbackErrorType']=type(error).__name__
        record['finishedUtc']=previous.utc();save(out/'Report.json',record)
    print(json.dumps({'status':record['status'],'report':(out/'Report.json').relative_to(ROOT).as_posix()}),flush=True)
    return 0 if record['status'].startswith(('RECORDED_','PASS_')) else 1

if __name__=='__main__':raise SystemExit(main())
