"""Root-only accepted93 transient Android regression on the proved LDPlayer0.

No device operation occurs on import. Physical-phone tools remain unchanged.
Raw native reports/four camera frames remain private until separately reviewed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

import accepted93_ld as accepted

ROOT = accepted.ROOT
OUT = ROOT / 'Verification/Evidence/AndroidTesting95/Regression'
PRIVATE = ROOT / '.verification-cache/AndroidTesting95/Regression'
MARKER = 'HOTR_RunRegression'
REMOTE = accepted.BASE + '/Regression'
SELECTED = (
    ('Gameplay_English_HUD.png',),
    ('Power_4_Effect_0.png', 'Power_4_Effect_1.png', 'Power_4_Effect_2.png'),
    ('Stacked_Stones_Diagonal_0.png', 'Stacked_Stones_Diagonal_1.png', 'Stacked_Stones_Diagonal_2.png'),
    ('Home_Reward_L50.png',),
)
SOURCE_FILES = (
    'Unity/Assets/HeartOfTheRain/Verification/PlayerRegressionSuite.cs',
    'Unity/Assets/HeartOfTheRain/Verification/PowerupDeviceVerification.cs',
    'Unity/Assets/HeartOfTheRain/App/Profile/Runtime/PlayerProfileHost.cs',
    'Unity/Assets/HeartOfTheRain/App/FirstStart/Runtime/FirstStartPage.cs',
    'Unity/Assets/HeartOfTheRain/M48/Resources/HOTR_Playtests/Campaign_Replays.json',
)

need, read, sha, bound, utc = accepted.need, accepted.read, accepted.sha, accepted.bound, accepted.utc


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def modules():
    directory = str(ROOT / 'Verification/Tools/Review93')
    if directory not in sys.path:
        sys.path.insert(0, directory)
    runner = accepted.module('regression95_pure_frame_rules', 'Verification/Tools/Review93/run_phone_regression.py')
    return runner, runner.proof, runner.phone


def outputs(path):
    path = Path(path)
    for item in (path, *path.parents):
        if item.exists():
            need(not item.is_symlink() and not getattr(item.stat(), 'st_file_attributes', 0) & 0x400, 'Regression95LinkedOutputRefused')
    path = path.resolve()
    need(path.parent == OUT.resolve() and re.fullmatch('[0-9a-f]{32}', path.name) is not None
         and not path.exists(), 'Regression95FreshUUIDOutputRequired')
    private = PRIVATE / path.name
    for item in (private, *private.parents):
        if item.exists():
            need(not item.is_symlink() and not getattr(item.stat(), 'st_file_attributes', 0) & 0x400, 'Regression95LinkedPrivateOutputRefused')
    need(not private.exists(), 'Regression95PrivateOutputAlreadyExists')
    path.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    return path, private


def remote_files(target, directory, maximum=4096):
    if not target.exists(directory):
        return []
    paths = target.adb('shell', 'find', directory, '-type', 'f').splitlines()
    need(len(paths) <= maximum and len(paths) == len(set(paths)), 'Regression95RemoteInventoryBound')
    for path in paths:
        need(re.fullmatch(re.escape(directory) + r'/[A-Za-z0-9_./-]+', path) is not None
             and '..' not in path.removeprefix(directory+'/').split('/'), 'Regression95RemoteFilePathInvalid')
    return paths


def markers(target):
    if not target.exists(accepted.BASE):
        return []
    paths = target.adb('shell', 'find', accepted.BASE, '-maxdepth', '1', '-type', 'f').splitlines()
    need(len(paths) <= 4096, 'Regression95MarkerInventoryBound')
    result = []
    for path in paths:
        need(re.fullmatch(re.escape(accepted.BASE) + r'/[A-Za-z0-9_.-]+', path) is not None, 'Regression95AppRootPathInvalid')
        name = path.removeprefix(accepted.BASE+'/')
        if name.startswith('HOTR_'):
            result.append(name)
    return sorted(result)


def ordinary(target):
    # Deliberately exclude generated Regression output; hash every nested
    # profile/authority file and every preferences file instead.
    paths = target.adb('shell', 'pm', 'path', accepted.PACKAGE).splitlines()
    need(len(paths) == 1 and re.fullmatch(r'package:/data/app/[A-Za-z0-9_./=+~@-]+\.apk', paths[0]) is not None,
         'Regression95OneInstalledAPKRequired')
    installed = target.file_hash(paths[0].removeprefix('package:'))
    need(installed == accepted.APK_SHA, 'Regression95AcceptedInstalledAPKRequired')
    need(not target.exists(accepted.BASE+'/ServerReview/configuration.json'), 'Regression95LocalModeOnly')
    files, profiles = {}, {}
    for path in remote_files(target, accepted.BASE+'/Profiles'):
        relative = path.removeprefix(accepted.BASE+'/')
        key = hashlib.sha256(relative.encode()).hexdigest()
        files[key] = target.file_hash(path)
        if re.fullmatch(r'Profiles/[A-Za-z0-9_.-]+/profile\.json', relative):
            profiles[key] = accepted.canonical_attempts(relative, target.adb('exec-out', 'cat', path))
    need(profiles, 'Regression95CanonicalIdleProfileRequired')
    state = target.adb('shell', 'run-as', accepted.PACKAGE, 'sh', '-c',
                       '"if test -d shared_prefs; then echo PRESENT; else echo ABSENT; fi"')
    need(state == 'PRESENT', 'Regression95ExistingPreferencesRequired')
    preferences = {}
    for name in target.adb('shell', 'run-as', accepted.PACKAGE, 'ls', 'shared_prefs').split():
        need(re.fullmatch(r'[A-Za-z0-9_.-]+\.xml', name) is not None, 'Regression95PreferencePathInvalid')
        preferences[hashlib.sha256(name.encode()).hexdigest()] = target.file_hash('shared_prefs/'+name, True)
    need(preferences, 'Regression95PreferencesRequired')
    return dict(installedSHA256=installed, profileFileHashes=files, profiles=profiles,
                preferences=preferences, activeAttempts=0)


def same_ordinary(before, after):
    need(before == after and before.get('installedSHA256') == accepted.APK_SHA
         and before.get('activeAttempts') == 0, 'Regression95OrdinaryDataChangedNoFurtherMutation')


def pid(target):
    value = target.adb('shell', 'pidof', accepted.PACKAGE, accepted=(0,1))
    need(not value or re.fullmatch('[1-9][0-9]*', value) is not None, 'Regression95SingleOwnerPIDRequired')
    return value


def device_seconds(target):
    value = target.adb('shell', 'date', '-u', '+%s')
    need(re.fullmatch('[0-9]{10}', value) is not None, 'Regression95DeviceClockInvalid')
    return int(value)


def mtime(target, path):
    value = target.adb('shell', 'stat', '-c', '%Y', path)
    need(re.fullmatch('[0-9]{10}', value) is not None, 'Regression95OutputTimeInvalid')
    return int(value)


def geometry(target):
    rows = re.findall(r'(?m)^(?:Physical|Override) size: ([0-9]+)x([0-9]+)\s*$', target.adb('shell','wm','size'))
    need(rows, 'Regression95DisplayGeometryRequired')
    width, height = sorted(map(int, rows[-1]))
    need(320 <= width <= 4096 and width < height <= 8192, 'Regression95PortraitDisplayRequired')
    return width, height


def launch(target):
    value = target.adb('shell','am','start','-W','-n',accepted.ACTIVITY,timeout=60)
    need(re.search(r'(?m)^Status:\s*ok\s*$', value) is not None, 'Regression95OwnerLaunchFailed')
    current = pid(target)
    need(current, 'Regression95LaunchedPIDRequired')
    return current


def stop_idle(target, before):
    need(not markers(target), 'Regression95ForeignOrPendingMarkerPreserved')
    same_ordinary(before, ordinary(target))
    target.adb('shell','am','force-stop',accepted.PACKAGE)
    need(not pid(target), 'Regression95OwnerDidNotStop')
    same_ordinary(before, ordinary(target))
    need(not markers(target), 'Regression95MarkerAppearedAfterStop')


def fresh_report(report, raw, old_hash, started, modified, width, height, when):
    need(isinstance(report,dict) and report.get('unity')=='2022.3.62f3' and report.get('platform')=='Android'
         and (report.get('width'),report.get('height'))==(width,height), 'Regression95NativeDeviceScopeMismatch')
    need(hashlib.sha256(raw).hexdigest()!=old_hash and when(report.get('utc','')).timestamp() >= started
         and modified >= started, 'Regression95StaleNativeReportRefused')


def parse_metadata(raw, paths, pattern, code):
    found = {}
    for line in raw.splitlines():
        match = re.fullmatch(pattern,line)
        need(match is not None and match[2] in paths and match[2] not in found,code)
        found[match[2]]=match[1]
    need(set(found)==set(paths),code)
    return found


def collect(target, public, private, report, raw, started, width, height, rules, proof, png):
    names = rules.frame_names(report)
    atlas_raw=target.adb('exec-out','cat',REMOTE+'/M70_Device.json',binary=True)
    atlas=json.loads(atlas_raw)
    need(atlas.get('status')=='PASS_NATIVE_M70_DEVICE' and not atlas.get('failures')
         and proof.when(atlas['utc']).timestamp()>=started and mtime(target,REMOTE+'/M70_Device.json')>=started
         and len(atlas.get('textures',[]))==7 and len(atlas.get('idleAdvancement',[]))==3
         and all(row.get('passed') is True for row in atlas['idleAdvancement']), 'Regression95FreshAtlasCoverageRequired')
    inventory=set(remote_files(target,REMOTE,1500))
    need({REMOTE+'/'+name for name in names}<=inventory,'Regression95DeclaredFrameMissing')
    chosen={next((name for name in choices if name in names),'') for choices in SELECTED}
    need(len(chosen)==4 and '' not in chosen,'Regression95FourRepresentativeGroupsRequired')
    rows=[]
    for offset in range(0,len(names),32):
        paths=[REMOTE+'/'+name for name in names[offset:offset+32]]
        hashes=parse_metadata(target.adb('shell','sha256sum',*paths),paths,r'([0-9a-fA-F]{64})\s+(.+)','Regression95FrameHashInventoryInvalid')
        sizes=parse_metadata(target.adb('shell','stat','-c','%s:%n',*paths),paths,r'([0-9]+):(.+)','Regression95FrameSizeInventoryInvalid')
        for path in paths:
            name=path.removeprefix(REMOTE+'/');size=int(sizes[path]);need(size>0,'Regression95EmptyNativeFrame')
            row={'file':name,'sha256':hashes[path].lower(),'bytes':size,'retainedPrivately':name in chosen}
            if name in chosen:
                data=target.adb('exec-out','cat',path,binary=True)
                need(len(data)==size and hashlib.sha256(data).hexdigest()==row['sha256']
                     and png.validate_png(data)==(width,height),'Regression95NativeFrameChanged')
                destination=private/name;destination.write_bytes(data);row['privateArtifact']=bound(destination)
            rows.append(row)
    need(target.adb('exec-out','cat',REMOTE+'/Regression.json',binary=True)==raw,'Regression95CompletedNativeReportChanged')
    (private/'Regression.json').write_bytes(raw);(private/'M70_Device.json').write_bytes(atlas_raw)
    save(public/'CaptureInventory.json',{'frames':rows,'capturedPngCount':len(rows),'retainedPrivatePngCount':4,
         'scope':'Native offscreen camera/UGUI captures; no OS screenshot or root visual approval inferred.'})
    return {'nativeReport':bound(private/'Regression.json'),'atlasReport':bound(private/'M70_Device.json'),
            'captureInventory':bound(public/'CaptureInventory.json'),'checks':report['checks'],'boards':report['boards'],
            'actions':report['actions'],'clips':report['clips'],'width':width,'height':height}


def cleanup_marker(target, payload, request_bound):
    found=markers(target)
    if MARKER in found:
        need(request_bound.get('sha256')==hashlib.sha256(payload).hexdigest(),'Regression95OwnedRequestReceiptRequired')
        current=target.adb('exec-out','cat',accepted.BASE+'/'+MARKER,binary=True)
        need(current==payload,'Regression95ForeignMarkerContentPreserved')
        target.adb('shell','rm',accepted.BASE+'/'+MARKER)
        need(not target.exists(accepted.BASE+'/'+MARKER),'Regression95OwnedMarkerCleanupFailed')
    need(not markers(target),'Regression95ForeignMarkersPreservedNoRelaunch')


def run(update_directory, output, timeout=2100):
    need(type(timeout) is int and 60<=timeout<=2100,'Regression95BoundedTimeoutRequired')
    public,private=outputs(output)
    record={'schemaVersion':1,'status':'RUNNING_ACCEPTED93_LD_TRANSIENT_REGRESSION95','runId':public.name,
            'startedUtc':utc(),'runner':bound(Path(__file__)),'package':accepted.PACKAGE,
            'scope':'Accepted93 Unity2022 APK accelerated transient fixtures on proved LDPlayer0. Not Unity6, human50-level campaign, physical-touch, live backend/provider, whole-game smoothness or production acceptance.',
            'nativeSessionNonceAvailable':False,'rawEvidencePublished':False,'visualApproval':False}
    target=None;before=None;payload=None;request_bound=None;proof_before=None;identity=None;stopped_for_fixture=False
    try:
        update=accepted.validate_update_receipt(update_directory)
        record['acceptedUpdate']=update['update'];proof_before=update['proof']
        target=accepted.Target();target.deadline=time.monotonic()+timeout+480
        identity=target.identity();need(identity==update['identity'],'Regression95UpdatedLDTargetRequired')
        record['identity']=identity;record['proof']=proof_before
        rules,proof,png=modules()
        record['helpers']={name:bound(Path(value.__file__)) for name,value in [('transport',accepted),('frameRules',rules),('nativeRules',proof),('pngRules',png)]}
        record['fixtureSources']=[bound(ROOT/name) for name in SOURCE_FILES]
        before=ordinary(target);need(not markers(target),'Regression95PreexistingMarkersPreserved')
        save(public/'OrdinaryBefore.json',before);record['ordinaryBefore']=bound(public/'OrdinaryBefore.json')
        old_pid=pid(target);old_hash=target.file_hash(REMOTE+'/Regression.json') if target.exists(REMOTE+'/Regression.json') else None
        width,height=geometry(target);record['display']={'width':width,'height':height}
        stop_idle(target,before)
        stopped_for_fixture=True
        payload=json.dumps({'runId':public.name,'utc':utc()},sort_keys=True).encode('ascii')
        request=private/MARKER;request.write_bytes(payload);request_bound=bound(request)
        record['request']=request_bound;record['previousNativeReportSHA256']=old_hash
        record['priorPID']=int(old_pid) if old_pid else None
        save(public/'Authorization.json',record)
        need(accepted.accepted_proof()==proof_before,'Regression95SourceChangedBeforeMarker')
        target.adb('push',request,accepted.BASE+'/'+MARKER)
        need(target.file_hash(accepted.BASE+'/'+MARKER)==request_bound['sha256'],'Regression95PushedRequestMismatch')
        started=device_seconds(target);record['deviceStartUnix']=started
        new_pid=launch(target);need(new_pid!=old_pid,'Regression95NewFixtureProcessRequired')
        record['fixturePID']=int(new_pid)
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            need(pid(target)==new_pid,'Regression95FixtureProcessChanged')
            raw=target.adb('exec-out','cat',REMOTE+'/Regression.json',accepted=(0,1),binary=True)
            try: report=json.loads(raw)
            except (ValueError,UnicodeDecodeError): report={}
            if report:
                try:fresh_report(report,raw,old_hash,started,mtime(target,REMOTE+'/Regression.json'),width,height,proof.when)
                except (ValueError,RuntimeError,KeyError,TypeError):report={}
            if report:
                need(not target.exists(accepted.BASE+'/'+MARKER),'Regression95TriggerNotConsumed')
                record['lastNativeStatus']=report.get('status');record['lastNativeChecks']=report.get('checks')
                if report.get('status')!='RUNNING':
                    (private/'CompletedNative.json').write_bytes(raw)
                    record['completedNativeReport']=bound(private/'CompletedNative.json')
                    proof.native_scope(report)
                    record.update(collect(target,public,private,report,raw,started,width,height,rules,proof,png))
                    record['status']='PASS_ACCEPTED93_LD_TRANSIENT_REGRESSION95'
                    break
            time.sleep(10)
        else:raise TimeoutError('Regression95HostDeadline')
    except Exception as error:
        record.update(status='FAIL_ACCEPTED93_LD_TRANSIENT_REGRESSION95',failure=accepted.safe(error))
    finally:
        try:
            if proof_before is not None:
                need(accepted.accepted_proof()==proof_before,'Regression95MainSourcesOrAPKChanged')
                record['sourceProofsUnchanged']=True
            if target is not None and before is not None:
                need(target.identity()==identity,'Regression95LDIdentityChangedAtExit')
                if payload is not None and request_bound is not None:
                    cleanup_marker(target,payload,request_bound)
                else:need(not markers(target),'Regression95PendingMarkersPreserved')
                after=ordinary(target);same_ordinary(before,after)
                save(public/'OrdinaryAfter.json',after);record['ordinaryAfter']=bound(public/'OrdinaryAfter.json')
                if stopped_for_fixture:
                    stop_idle(target,before);normal_pid=launch(target);time.sleep(8)
                    final=ordinary(target);same_ordinary(before,final)
                    need(not markers(target),'Regression95FinalPendingMarkers')
                    record['normalRelaunch']={'pid':int(normal_pid),'fixedObservationSeconds':8,'readinessOrPerformanceClaim':False}
                else:final=after
                save(public/'OrdinaryAfterRelaunch.json',final);record['ordinaryAfterRelaunch']=bound(public/'OrdinaryAfterRelaunch.json')
                record['ordinaryDataUnchanged']=True;record['finalMarkers']=[]
        except Exception as error:
            record.update(status='BLOCKED_ACCEPTED93_LD_REGRESSION95_PRESERVATION',preservationFailure=accepted.safe(error),requiresOperatorCleanup=True)
        record['finishedUtc']=utc();save(public/'Invocation.json',record)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--update',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--timeout',type=int,default=2100)
    args=parser.parse_args()
    if not args.execute or os.name!='nt' or not args.out.is_absolute():
        parser.error('Explicit root Windows execution and absolute fresh95 output required')
    report=run(args.update,args.out,args.timeout)
    print(json.dumps({'status':report['status'],'runId':report['runId'],'unity6Accepted':False}))
    return 0 if report['status']=='PASS_ACCEPTED93_LD_TRANSIENT_REGRESSION95' else 1


if __name__=='__main__':raise SystemExit(main())
