"""Root-only separate-package LTS Android transient regression; import is inert."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import time

import ldplayer95 as ld
import launch97

ROOT,EVIDENCE=ld.ROOT,ld.EVIDENCE
OUT=EVIDENCE/'Regression97'
PRIVATE=ROOT/'.verification-cache/Unity6LTS95/Regression97'
PACKAGE,OWNER=ld.PACKAGE,ld.OWNER
VERSION='6000.3.27f1'
BASE='/sdcard/Android/data/'+PACKAGE+'/files'
REMOTE=BASE+'/Regression'
MARKER='HOTR_RunRegression'
FAMILIES={'cabinet','case','crate','crystal','gate','moss','pod','stone'}
ATTEMPTS={'Reserved','Started','Won','Lost','Interrupted','Cancelled','Released'}
SELECTED=(('Gameplay_English_HUD.png',),('Power_4_Effect_0.png','Power_4_Effect_1.png','Power_4_Effect_2.png'),
          ('Stacked_Stones_Diagonal_0.png','Stacked_Stones_Diagonal_1.png','Stacked_Stones_Diagonal_2.png'),('Home_Reward_L50.png',))
FIXTURES=('Assets/HeartOfTheRain/Verification/PlayerRegressionSuite.cs',
          'Assets/HeartOfTheRain/Verification/PowerupDeviceVerification.cs',
          'Assets/HeartOfTheRain/App/Profile/Runtime/PlayerProfileHost.cs',
          'Assets/HeartOfTheRain/App/FirstStart/Runtime/FirstStartPage.cs',
          'Assets/HeartOfTheRain/M48/Resources/HOTR_Playtests/Campaign_Replays.json')
LIFECYCLE=('Practice Match solved through page commands and real animation playback',
           'Practice Rocket solved through page commands and real animation playback',
           'Practice Clear solved through page commands and real animation playback',
           'Exactly 900 coins shows the enabled native refill button and price',
           'Repeated native refill callback charges exactly once',
           'Connected Continue exposes the approved five-move/900-coin offer',
           'Confirmed decline charges exactly one life, no coins, and opens retry pre-level',
           'Celebration completion cannot grant a duplicate reward L50',
           'Celebration returns Home without next-level modal L50')


def need(value,code):ld.need(value,code)
def read(path):return ld.read(path)
def bound(path):return ld.bound(path)
def base_for(package):
    need(package in (PACKAGE,OWNER),'Regression97FixedPackageRequired')
    return '/sdcard/Android/data/'+package+'/files'


def when(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    need(result.tzinfo is not None,'Regression97TimezoneRequired');return result


def core_binding(item):return {key:item[key] for key in ('path','sha256','bytes')}


def reviewed_launch(path,build,installation):
    context=launch97.validate_launch_receipt(path,build,installation)
    report=context['report'];review_path=Path(path).resolve().parent/'VisualReview.json'
    launch97.no_links(review_path);review=read(review_path)
    need(review.get('schemaVersion')==1 and review.get('status')=='ROOT_VISUALLY_REVIEWED_LTS_FIRST_LAUNCH97'
         and review.get('launchReceipt')==context['binding'] and review.get('reviewer')=='root'
         and review.get('splashAbsent') is True and review.get('firstStartRouteCorrect') is True
         and isinstance(review.get('reviewScope'),str) and review['reviewScope'].strip()
         and report.get('selectedRuntimeErrorCount')==0,'Regression97RootReviewedCleanFirstLaunchRequired')
    artifacts=review.get('reviewedArtifacts',[])
    need(isinstance(artifacts,list) and 2<=len(artifacts)<=200,'Regression97ReviewedArtifactsRequired')
    allowed=(Path(path).resolve().parent,(ROOT/'.verification-cache/Unity6LTS95/FirstLaunch97'/Path(path).parent.name).resolve())
    seen=set()
    for item in artifacts:
        actual=launch97.no_links(ROOT/item['path'])
        need(any(actual.is_relative_to(folder) for folder in allowed) and bound(actual)==core_binding(item)
             and item['path'] not in seen,'Regression97ReviewedArtifactChanged')
        seen.add(item['path'])
    for key in ('privateOriginalVideo','endOSCapture'):
        need(core_binding(report[key]) in [core_binding(item) for item in artifacts],'Regression97StartupVideoAndEndOSReviewRequired')
    return context,bound(review_path)


def fixture_bindings(build):
    manifest=read(build['gameSources']);project=ld.game95.PROJECT
    rows=[]
    for relative in FIXTURES:
        actual=project/relative;original=ROOT/'Unity'/relative
        need(relative in manifest['files'] and actual.is_file() and original.is_file()
             and ld.sha(actual)==manifest['files'][relative]['sha256']==ld.sha(original)
             and actual.stat().st_size==manifest['files'][relative]['bytes']==original.stat().st_size,
             'Regression97OriginalRuntimeFixtureSourceChanged')
        rows.append({'original':bound(original),'compiledCandidateInput':bound(actual)})
    return rows


def native_scope(report):
    # Same coverage conditions as accepted93 native_scope, with an explicit new
    # engine target. Never rewrite a report or fake its old engine/phone identity.
    need(report.get('status')=='PASS_NATIVE_REGRESSION' and report.get('failures')==[]
         and report.get('unity')==VERSION and report.get('platform')=='Android'
         and report.get('boards')==50 and report.get('actions')==408 and report.get('clips')==354
         and report.get('checks',0)==len(report.get('passed',[]))>0 and report.get('labels',0)>0
         and set(report.get('damageFamilies',[]))==FAMILIES,'Regression97ActualNativeCoverageRequired')
    passed=set(report['passed'])
    for level in range(1,51):
        need('L'+str(level)+' accepts natural move' in passed,'Regression97NaturalMoveMissing')
        for tool in range(4):
            need('L'+str(level)+' tool '+str(tool)+' spends one stock' in passed
                 and 'L'+str(level)+' tool '+str(tool)+' preserves moves' in passed,'Regression97ToolCoverageMissing')
    need(all(name in passed for name in LIFECYCLE),'Regression97LifecycleCaseMissing')


def fresh_report(report,raw,old_hash,started,modified,width,height):
    need(isinstance(report,dict) and report.get('unity')==VERSION and report.get('platform')=='Android'
         and (report.get('width'),report.get('height'))==(width,height),'Regression97ActualEngineAndDisplayRequired')
    need(hashlib.sha256(raw).hexdigest()!=old_hash and when(report.get('utc','')).timestamp()>=started
         and modified>=started,'Regression97FreshNativeReportRequired')


def frame_names(report):
    names=report.get('frames',[])
    need(isinstance(names,list) and 0<len(names)<=1000 and len(names)==len(set(names))
         and all(isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9_-]+\.png',name) for name in names),
         'Regression97ExactDeclaredFramesRequired')
    return names


def metadata(raw,paths,pattern,code):
    rows={}
    for line in raw.splitlines():
        match=re.fullmatch(pattern,line)
        need(match is not None and match[2] in paths and match[2] not in rows,code);rows[match[2]]=match[1]
    need(set(rows)==set(paths),code);return rows


class Target(ld.LDPlayer):
    def adb(self,*args,accepted=(0,),timeout=30,binary=False):
        remaining=int(self.deadline-time.monotonic());need(remaining>0,'Regression97BoundedDeviceDeadline')
        raw=ld.run([ld.ADB,'-s',self.serial,*args],min(timeout,remaining),accepted)[0]
        return raw if binary else raw.decode('utf-8','strict').strip()
    def exists(self,path):
        remaining=int(self.deadline-time.monotonic());need(remaining>0,'Regression97BoundedDeviceDeadline')
        return ld.run([ld.ADB,'-s',self.serial,'shell','test','-e',path],min(30,remaining),(0,1))[2]==0


def remote_files(target,directory,maximum=4096):
    if not target.exists(directory):return []
    rows=target.adb('shell','find',directory,'-type','f').splitlines()
    need(len(rows)<=maximum and len(rows)==len(set(rows)),'Regression97BoundedRemoteInventoryRequired')
    for path in rows:
        need(re.fullmatch(re.escape(directory)+r'/[A-Za-z0-9_./-]+',path)
             and '..' not in path.removeprefix(directory+'/').split('/'),'Regression97RemotePathInvalid')
    return rows


def markers(target,package=PACKAGE):
    base=base_for(package)
    return sorted(path.removeprefix(base+'/') for path in remote_files(target,base)
                  if '/' not in path.removeprefix(base+'/') and path.removeprefix(base+'/').startswith('HOTR_'))


def canonical_profile(relative,raw):
    if not re.fullmatch(r'Profiles/[A-Za-z0-9_.-]+/profile\.json',relative):return None
    envelope=json.loads(raw);profile=json.loads(envelope['payload']);attempts=profile['attempts']
    need(isinstance(attempts,list) and all(row.get('state') in ATTEMPTS for row in attempts),'Regression97KnownAttemptStatesRequired')
    need(not any(row['state'] in ('Reserved','Started') for row in attempts),'Regression97ActiveAttemptPreserved')
    return {'activeAttempts':0,'currentLevel':profile['currentLevel'],'completed':profile['completed'],
            'coins':profile['coins'],'lives':profile['lives'],'revision':profile['revision']}


def ordinary(target,package,expected_apk=None):
    paths=target.installed_paths(package)
    if not paths:
        need(package==OWNER,'Regression97InstalledCandidateRequired');return {'installed':False}
    need(len(paths)==1,'Regression97SingleInstalledAPKRequired');apk=target.remote_hash(paths[0])
    if expected_apk:need(apk==expected_apk,'Regression97ExactInstalledAPKRequired')
    if package==OWNER:need(not pid(target,OWNER),'Regression97OwnerStoppedRequired')
    base=base_for(package);need(not markers(target,package),'Regression97PendingMarkerPreserved')
    need(not target.exists(base+'/ServerReview/configuration.json'),'Regression97LocalOnlyNoServerConfiguration')
    paths=[path for path in remote_files(target,base) if not path.startswith(base+'/Regression/')]
    files={};profiles={}
    for offset in range(0,len(paths),32):
        batch=paths[offset:offset+32]
        hashes=metadata(target.adb('shell','sha256sum',*batch),batch,r'([0-9a-fA-F]{64})\s+(.+)','Regression97OrdinaryFileHashesInvalid')
        for path in batch:
            relative=path.removeprefix(base+'/');key=hashlib.sha256(relative.encode()).hexdigest();files[key]=hashes[path].lower()
            if re.fullmatch(r'Profiles/[A-Za-z0-9_.-]+/profile\.json',relative):
                profiles[key]=canonical_profile(relative,target.adb('exec-out','cat',path))
    if package==PACKAGE:need(profiles,'Regression97FirstOrdinaryLaunchProfileRequired')
    state=target.adb('shell','run-as',package,'sh','-c','"if test -d shared_prefs; then echo PRESENT; else echo ABSENT; fi"')
    need(state in ('PRESENT','ABSENT'),'Regression97PreferenceAccessRequired');preferences={}
    if state=='PRESENT':
        for name in target.adb('shell','run-as',package,'ls','shared_prefs').split():
            need(re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',name),'Regression97PreferencePathInvalid')
            text=target.adb('exec-out','run-as',package,'sha256sum','shared_prefs/'+name)
            match=re.fullmatch(r'([0-9a-fA-F]{64})\s+[^\r\n]+',text);need(match,'Regression97PreferenceHashInvalid')
            preferences[hashlib.sha256(name.encode()).hexdigest()]=match[1].lower()
    return {'installed':True,'installedSHA256':apk,'ordinaryExternalFileHashes':files,'profiles':profiles,
            'preferences':preferences,'activeAttempts':0,'excludedGeneratedTree':'Regression/'}


def same(before,after):need(before==after,'Regression97DurableDataChangedNoFurtherMutation')


def pid(target,package=PACKAGE):
    need(package in (PACKAGE,OWNER),'Regression97FixedPackageRequired')
    value=target.adb('shell','pidof',package,accepted=(0,1))
    need(not value or re.fullmatch(r'[1-9][0-9]*',value),'Regression97SinglePackagePIDRequired');return value


def assert_identity(target,identity):need(target.identity()==identity,'Regression97BootOrDeviceChangedNoCleanup')


def stop_idle(target,before,identity=None):
    need(not markers(target),'Regression97ForeignMarkerPreserved');same(before,ordinary(target,PACKAGE,before['installedSHA256']))
    if identity is not None:assert_identity(target,identity)
    target.adb('shell','am','force-stop',PACKAGE);need(not pid(target),'Regression97CandidateDidNotStop')
    same(before,ordinary(target,PACKAGE,before['installedSHA256']));need(not markers(target),'Regression97MarkerAppearedAfterStop')
    if identity is not None:assert_identity(target,identity)


def launch(target,identity=None):
    if identity is not None:assert_identity(target,identity)
    result=target.adb('shell','am','start','-W','-n',PACKAGE+'/com.unity3d.player.UnityPlayerActivity',timeout=60)
    need(re.search(r'(?m)^Status:\s*ok\s*$',result),'Regression97CandidateLaunchFailed')
    current=pid(target);need(current,'Regression97CandidatePIDRequired');return current


def cleanup_marker(target,payload,receipt,identity=None):
    found=markers(target)
    if MARKER in found:
        need(receipt and receipt.get('sha256')==hashlib.sha256(payload).hexdigest(),'Regression97OwnedMarkerReceiptRequired')
        need(target.adb('exec-out','cat',BASE+'/'+MARKER,binary=True)==payload,'Regression97ForeignMarkerContentPreserved')
        if identity is not None:assert_identity(target,identity)
        target.adb('shell','rm',BASE+'/'+MARKER);need(not target.exists(BASE+'/'+MARKER),'Regression97OwnedMarkerCleanupFailed')
    need(not markers(target),'Regression97ForeignMarkersPreservedNoRelaunch')


def seconds(target):
    value=target.adb('shell','date','-u','+%s');need(re.fullmatch(r'[0-9]{10}',value),'Regression97DeviceClockRequired');return int(value)


def modified(target,path):
    value=target.adb('shell','stat','-c','%Y',path);need(re.fullmatch(r'[0-9]{10}',value),'Regression97NativeMtimeRequired');return int(value)


def geometry(target):
    rows=re.findall(r'(?m)^(?:Physical|Override) size: ([0-9]+)x([0-9]+)\s*$',target.adb('shell','wm','size'))
    need(rows,'Regression97DisplayGeometryRequired');width,height=map(int,rows[-1])
    need(320<=width<height<=8192,'Regression97ActualPortraitGeometryRequired');return width,height


def png_size(raw):
    # Reuse a pure parser, never construct a physical Phone or spoof its identity.
    parser=ld.smoke95.module('regression97_png_parser',ROOT/'Verification/Tools/Review93/phone.py')
    return parser.validate_png(raw)


def collect(target,public,private,report,raw,started,width,height):
    names=frame_names(report);atlas_raw=target.adb('exec-out','cat',REMOTE+'/M70_Device.json',binary=True);atlas=json.loads(atlas_raw)
    need(atlas.get('status')=='PASS_NATIVE_M70_DEVICE' and atlas.get('failures')==[]
         and when(atlas['utc']).timestamp()>=started and modified(target,REMOTE+'/M70_Device.json')>=started
         and len(atlas.get('textures',[]))==7 and len(atlas.get('idleAdvancement',[]))==3
         and all(row.get('passed') is True for row in atlas['idleAdvancement']),'Regression97FreshM70CoverageRequired')
    inventory=set(remote_files(target,REMOTE,1500));need({REMOTE+'/'+name for name in names}<=inventory,'Regression97DeclaredCaptureMissing')
    selected={next((name for name in choices if name in names),'') for choices in SELECTED}
    need(len(selected)==4 and '' not in selected,'Regression97FourRepresentativeCapturesRequired');rows=[]
    for offset in range(0,len(names),32):
        paths=[REMOTE+'/'+name for name in names[offset:offset+32]]
        hashes=metadata(target.adb('shell','sha256sum',*paths),paths,r'([0-9a-fA-F]{64})\s+(.+)','Regression97CaptureHashInvalid')
        sizes=metadata(target.adb('shell','stat','-c','%s:%n',*paths),paths,r'([0-9]+):(.+)','Regression97CaptureSizeInvalid')
        mtimes=metadata(target.adb('shell','stat','-c','%Y:%n',*paths),paths,r'([0-9]+):(.+)','Regression97CaptureMtimeInvalid')
        for path in paths:
            name=path.removeprefix(REMOTE+'/');size=int(sizes[path]);need(size>0 and int(mtimes[path])>=started,'Regression97FreshNonemptyCaptureRequired')
            row={'file':name,'sha256':hashes[path].lower(),'bytes':size,'deviceMtimeUnix':int(mtimes[path]),'retainedPrivately':name in selected}
            if name in selected:
                data=target.adb('exec-out','cat',path,binary=True)
                need(len(data)==size and hashlib.sha256(data).hexdigest()==row['sha256'] and png_size(data)==(width,height),'Regression97RetainedCaptureChanged')
                destination=private/name;destination.write_bytes(data);row['privateArtifact']=bound(destination)
            rows.append(row)
    need(target.adb('exec-out','cat',REMOTE+'/Regression.json',binary=True)==raw,'Regression97CompletedNativeReportChanged')
    (private/'Regression.json').write_bytes(raw);(private/'M70_Device.json').write_bytes(atlas_raw)
    ld.write(public/'CaptureInventory.json',{'frames':rows,'capturedPngCount':len(rows),'retainedPrivatePngCount':4,
        'scope':'Actual native offscreen camera/UGUI captures, not OS screenshots or a visual approval. Only four representative original PNGs retained privately; every declared capture hash/size/mtime recorded.'})
    return {'nativeReport':bound(private/'Regression.json'),'atlasReport':bound(private/'M70_Device.json'),
            'captureInventory':bound(public/'CaptureInventory.json'),'capturedPngCount':len(rows),'retainedPrivatePngCount':4}


def outputs(path):
    path=launch97.no_links(path)
    need(path.parent==OUT.resolve() and re.fullmatch(r'[0-9a-f]{32}',path.name) and not path.exists(),'Regression97FreshUUIDOutputRequired')
    private=launch97.no_links(PRIVATE/path.name);need(not private.exists(),'Regression97PrivateOutputPreserved')
    path.mkdir(parents=True,exist_ok=False);private.mkdir(parents=True,exist_ok=False);return path,private


def run(build_path,installation,launch_path,output,timeout=2100):
    need(type(timeout) is int and 60<=timeout<=2100,'Regression97BoundedTimeoutRequired')
    context,review=reviewed_launch(launch_path,build_path,installation);build=context['build'];fixtures=fixture_bindings(build)
    public,private=outputs(output)
    record={'schemaVersion':1,'status':'RUNNING_LTS97_TRANSIENT_REGRESSION','runId':public.name,'startedUtc':ld.utc(),
            'runner':bound(Path(__file__)),'package':PACKAGE,'engineTarget':VERSION,'launchReceipt':context['binding'],'visualReview':review,
            'buildInvocation':bound(build['invocationPath']),'nativeBuildReport':bound(build['nativePath']),'apk':bound(build['apk']),
            'staticReport':context['static'],'installation':context['installation'],'fixtureSources':fixtures,
            'helpers':{name:bound(Path(module.__file__)) for name,module in (('ld',ld),('launch',launch97),('build',ld.game95))},
            'coverageReference':bound(ROOT/'Verification/Tools/Review93/phone_regression_proof.py'),
            'purePNGParser':bound(ROOT/'Verification/Tools/Review93/phone.py'),
            'nativeSessionNonceAvailable':False,'rawEvidencePublished':False,'visualApproval':False,'ownerMutation':False,
            'scope':'Actual source-bound separate-package Unity6000.3 Android accelerated transient memory-profile fixtures on proved LDPlayer. Native check total comes from the actual report. Not a human campaign, physical-phone/swipe, real backend/provider, ordinary saved rewards, production or whole-game smoothness acceptance.'}
    target=None;before=owner=None;identity=None;payload=request=None;fixture_pid=None;stopped=False
    try:
        target=Target(build_path);target.deadline=time.monotonic()+timeout+480;identity=target.identity()
        need(identity==context['report']['identity'],'Regression97ReviewedLaunchTargetAndBootRequired');record['identity']=identity
        launch97.unlocked(target,True)
        before=ordinary(target,PACKAGE,record['apk']['sha256']);owner=ordinary(target,OWNER)
        need(not markers(target) and not markers(target,OWNER),'Regression97PendingMarkerPreserved')
        packages=ld.package_map(target.adb('shell','pm','list','packages','-f'))
        record['packagesBefore']=packages
        for name,value in (('CandidateBefore',before),('OwnerBefore',owner)):ld.write(public/(name+'.json'),value)
        record.update(candidateBefore=bound(public/'CandidateBefore.json'),ownerBefore=bound(public/'OwnerBefore.json'))
        old_pid=pid(target);old_hash=target.remote_hash(REMOTE+'/Regression.json') if target.exists(REMOTE+'/Regression.json') else None
        width,height=geometry(target);record['display']={'width':width,'height':height};record['previousNativeReportSHA256']=old_hash
        payload=json.dumps({'runId':public.name,'utc':ld.utc()},sort_keys=True).encode('ascii');request_path=private/MARKER;request_path.write_bytes(payload);request=bound(request_path)
        record['request']=request;ld.write(public/'Authorization.json',record)
        assert_identity(target,identity);same(owner,ordinary(target,OWNER));stop_idle(target,before,identity);stopped=True
        need(ld.build(build_path)['gameSources']==build['gameSources'] and fixture_bindings(build)==fixtures,'Regression97BuildChangedBeforeMarker')
        assert_identity(target,identity);same(owner,ordinary(target,OWNER))
        assert_identity(target,identity)
        target.adb('push',request_path,BASE+'/'+MARKER)
        need(target.remote_hash(BASE+'/'+MARKER)==request['sha256'],'Regression97OwnedPushedMarkerMismatch')
        started=seconds(target);fixture_pid=launch(target,identity);need(fixture_pid!=old_pid,'Regression97FreshCandidateProcessRequired')
        record.update(fixturePID=int(fixture_pid),deviceStartUnix=started);deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            need(pid(target)==fixture_pid,'Regression97FixtureProcessChanged')
            raw=target.adb('exec-out','cat',REMOTE+'/Regression.json',accepted=(0,1),binary=True)
            try:report=json.loads(raw)
            except (ValueError,UnicodeDecodeError):report={}
            if report and hashlib.sha256(raw).hexdigest()!=old_hash:
                fresh_report(report,raw,old_hash,started,modified(target,REMOTE+'/Regression.json'),width,height)
                need(not target.exists(BASE+'/'+MARKER),'Regression97TriggerNotConsumed')
                record.update(lastNativeStatus=report.get('status'),actualNativeChecks=report.get('checks'))
                if report.get('status')!='RUNNING':
                    completed=private/'CompletedNative.json';completed.write_bytes(raw);record['completedNativeReport']=bound(completed)
                    native_scope(report);record['actualNativeCounts']={key:report[key] for key in ('checks','labels','boards','actions','clips')}
                    record.update(collect(target,public,private,report,raw,started,width,height))
                    record['status']='PASS_LTS97_ANDROID_TRANSIENT_REGRESSION';break
            time.sleep(10)
        else:raise TimeoutError('Regression97NativeDeadline')
    except Exception as error:record.update(status='FAIL_LTS97_ANDROID_TRANSIENT_REGRESSION',failure=ld.safe_error(error))
    finally:
        try:
            current_build=ld.build(build_path)
            need(bound(current_build['invocationPath'])==record['buildInvocation'] and bound(current_build['apk'])==record['apk']
                 and fixture_bindings(current_build)==fixtures,'Regression97BuildOrSourcesChangedAtExit')
            need(bound(Path(__file__))==record['runner'] and all(bound(Path(module.__file__))==record['helpers'][name]
                 for name,module in (('ld',ld),('launch',launch97),('build',ld.game95))),'Regression97ExecutingHelpersChangedAtExit')
            need(bound(ROOT/'Verification/Tools/Review93/phone_regression_proof.py')==record['coverageReference']
                 and bound(ROOT/'Verification/Tools/Review93/phone.py')==record['purePNGParser'],'Regression97CoverageReferenceOrPNGParserChanged')
            final_context,final_review=reviewed_launch(launch_path,build_path,installation)
            need(final_context['binding']==record['launchReceipt'] and final_review==record['visualReview'],
                 'Regression97ReviewedStartupEvidenceChangedAtExit')
            record['sourcesAndAPKUnchanged']=True
            if target is not None and before is not None and owner is not None:
                # Never clean up or relaunch on a new boot/target. Retain the
                # original wrapper BLOCK until explicit separate recovery.
                assert_identity(target,identity);same(owner,ordinary(target,OWNER))
                assert_identity(target,identity)
                if payload is not None and request is not None:cleanup_marker(target,payload,request,identity)
                else:need(not markers(target),'Regression97PendingMarkerPreserved')
                same(before,ordinary(target,PACKAGE,record['apk']['sha256']))
                if stopped:
                    current_pid=pid(target);need(not current_pid or current_pid==fixture_pid,'Regression97UnexpectedProcessPreserved')
                    stop_idle(target,before,identity);normal=launch(target,identity);time.sleep(8)
                    record['normalCandidateRelaunch']={'pid':int(normal),'fixedObservationSeconds':8,'readinessOrPerformanceClaim':False}
                assert_identity(target,identity)
                after=ordinary(target,PACKAGE,record['apk']['sha256']);after_owner=ordinary(target,OWNER)
                same(before,after);same(owner,after_owner)
                need(ld.package_map(target.adb('shell','pm','list','packages','-f'))==record['packagesBefore'],'Regression97InstalledPackagesChanged')
                for name,value in (('CandidateAfterRelaunch',after),('OwnerAfter',after_owner)):ld.write(public/(name+'.json'),value)
                record.update(candidateAfterRelaunch=bound(public/'CandidateAfterRelaunch.json'),ownerAfter=bound(public/'OwnerAfter.json'),
                              candidateDurableDataUnchanged=True,ownerDurableDataUnchanged=True,otherInstalledPackagesUnchanged=True,finalMarkers=[])
        except Exception as error:
            record.update(status='BLOCKED_LTS97_REGRESSION_PRESERVATION',preservationFailure=ld.safe_error(error),requiresOperatorCleanup=True)
        record['finishedUtc']=ld.utc();ld.write(public/'Invocation.json',record)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true')
    for name in ('build','installation','launch','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--timeout',type=int,default=2100);args=parser.parse_args()
    if not args.execute or os.name!='nt' or not all(path.is_absolute() for path in (args.build,args.installation,args.launch,args.out)):
        parser.error('Explicit root Windows action with absolute bound build/install/reviewed-launch/fresh output paths required')
    try:
        report=run(args.build,args.installation,args.launch,args.out,args.timeout)
        print(json.dumps({'status':report['status'],'package':PACKAGE,'ownerMutation':False,'rawEvidencePublished':False}))
        return 0 if report['status']=='PASS_LTS97_ANDROID_TRANSIENT_REGRESSION' else 1
    except Exception as error:
        print(json.dumps({'status':'FAIL_ROOT_LTS97_REGRESSION_ACTION',**ld.safe_error(error)}));return 1


if __name__=='__main__':raise SystemExit(main())
