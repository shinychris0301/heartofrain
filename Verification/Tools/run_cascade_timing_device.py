"""Opt-in isolated Android playback on the QA instance, preserving its save files."""
import argparse, hashlib, json, math, re, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from qa_android_target import validate_qa_target

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Verification/Evidence/CascadeResponsiveness/Android'
ADB=Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe')
PKG='com.heartoftherain.verification'
BASE=f'/sdcard/Android/data/{PKG}/files'
APK=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'

def validate_report(report, variant, repeats=1, require_profiling=False):
    """Validate provenance structure; this does not itself execute Unity/Android."""
    assert report['status']=='PASS_CASCADE_PLAYBACK' and not report['errors'],report.get('errors')
    assert len(report['rows'])==(1 if variant=='visual' else 6)*repeats
    available=report.get('profilingSchemaVersion',0)>=1
    assert available or not require_profiling,'Installed APK has no detailed timing instrumentation'
    if not available:
        assert repeats==1,'Legacy probe cannot repeat fixtures'
        return False
    assert report['repeats']==repeats and report['droppedFrameSamples']==0
    samples=report['frameSamples']
    assert samples and len(samples)<=report['frameLimit']
    signatures={}
    for index,row in enumerate(report['rows']):
        frames=[f for f in samples if f['row']==index]
        assert len(frames)==row['recordedFrames'] and frames
        assert {'pre_roll','playback','post_roll'}.issubset({f['stage'] for f in frames})
        assert all(a['absoluteWall']<=b['absoluteWall'] for a,b in zip(frames,frames[1:]))
        assert all(f['cost']['frame']==f['frame'] and f['cost']['updateStartedWall']>0
                   and f['cost']['updateStartedWall']<=f['cost']['renderStartedWall']
                   <=f['cost']['renderFinishedWall']<=f['cost']['updateFinishedWall']<=f['absoluteWall']
                   for f in frames),'Missing/mixed native cost timestamps'
        assert any(f['frame']==row['commandFrame'] and f['commandFrame']
                   and f['costPredatesCommand'] and f['afterUpdateElapsedMs']>0 for f in frames), 'Command-frame tail was lost'
        assert row['queuedSteps']==len(row['phases'])>0
        if report['profilingSchemaVersion'] == 1:
            assert row['enqueueCost']['frame']==row['commandFrame'] and row['enqueueCost']['phases']==row['queuedSteps']
        else:
            assert report['profilingSchemaVersion'] == 2 and report['sourceCheckpoint'] >= 79
            initial = row['initialEnqueueCost']
            assert initial['frame'] == row['commandFrame'] and 0 < initial['phases'] <= row['queuedSteps']
            assert isinstance(row['deferredStartup'], bool) and isinstance(json.loads(row['startupTraceJson']), dict)
            assert row['queueInspectionFrame'] >= row['commandFrame']
            assert row['acceptFinishedWall'] <= row['metadataReadyWall'] <= row['queueInspectionStartedWall'] <= row['queueInspectionFinishedWall']
            assert row['initialCommandFinishedWall'] == row['commandFinishedWall'] == row['acceptFinishedWall']
            assert abs((row['commandFinishedWall']-row['commandStartedWall'])*1000-row['commandMs']) < .01
            assert row['totalSynchronousProbeMs'] + .01 >= row['modelMs'] + row['acceptMs'] + row['queueInspectionMs']
        assert abs(sum(p['duration'] for p in row['phases'])-row['scheduledSeconds'])<.001
        spans=row['commandSpans']
        assert len(spans)==4 and {s['kind'] for s in spans}>={'model','real_accept','accepted_queue_inspection'}
        assert all(s['startedWall']<=s['finishedWall'] and math.isfinite(s['milliseconds']) and s['milliseconds']>=0 for s in spans)
        if report['profilingSchemaVersion'] == 1:
            assert all(s['frame']==row['commandFrame'] for s in spans)
        else:
            assert all(s['frame']==row['commandFrame'] for s in spans if s['kind']!='accepted_queue_inspection')
            inspections=[s for s in spans if s['kind']=='accepted_queue_inspection']
            assert len(inspections)==1 and inspections[0]['frame']==row['queueInspectionFrame']
            assert inspections[0]['startedWall'] >= row['metadataReadyWall']
        assert all(a['finishedWall']<=b['startedWall'] for a,b in zip(spans,spans[1:]))
        assert row['commandStartedWall']<=row['acceptStartedWall']<=row['acceptFinishedWall']<=row['commandFinishedWall']
        assert row['firstCommandRenderFinishedWall']>=row['acceptStartedWall'] and row['firstCommandRenderMs']>0
        assert 0<=row['repeatIndex']<repeats
        signature=(row['turnHash'],row['finalHash'])
        assert signatures.setdefault(row['baseCase'],signature)==signature,'Repeated model result differs'
    return True

def main():
    p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--variant',choices=['measure','visual'],default='measure');p.add_argument('--install',action='store_true');p.add_argument('--out',type=Path,default=OUT);p.add_argument('--repeats',type=int,choices=range(1,6),default=1);p.add_argument('--require-profiling',action='store_true');p.add_argument('--profile-model-work',action='store_true');p.add_argument('--visual-level',type=int,choices=range(1,51),default=4);p.add_argument('--checkpoint74-continuation',action='store_true');args=p.parse_args()
    target=validate_qa_target(args.serial,args.out)
    assert args.variant!='visual' or args.repeats==1,'Visual recording has one unchanged fixture'
    assert not args.profile_model_work or args.variant=='measure','Model stage profiling is separate from visual timing'
    out=args.out.resolve()/args.variant;out.mkdir(parents=True,exist_ok=True)
    def adb(*cmd,check=True):return subprocess.run([str(ADB),'-s',args.serial,*map(str,cmd)],capture_output=True,check=check,timeout=120).stdout
    def state():
        names=adb('shell','run-as',PKG,'ls','shared_prefs').decode().split()
        prefs={n:adb('shell','run-as',PKG,'sha256sum','shared_prefs/'+n).decode().split()[0] for n in names if re.fullmatch(r'[A-Za-z0-9_.-]+\.xml',n)}
        names=adb('shell','find',BASE+'/Profiles','-type','f','-name','*.json').decode().splitlines()
        saves={n.removeprefix(BASE+'/'):adb('shell','sha256sum',n).decode().split()[0] for n in names if re.fullmatch(re.escape(BASE)+r'/Profiles/[A-Za-z0-9_./-]+\.json',n)}
        return {'preferences':prefs,'saves':saves}
    assert adb('get-state').strip()==b'device'
    profile=json.loads(json.loads(adb('shell','cat',BASE+'/Profiles/Development-v1/profile.json'))['payload'])
    assert not any(a['state'] in ['Started','Reserved'] for a in profile['attempts']),'Keep an active attempt intact'
    adb('shell','am','force-stop',PKG);before=state()
    sha=hashlib.sha256(APK.read_bytes()).hexdigest();installation=None
    if args.install:
        installation=adb('install','-r',APK).decode().strip();assert 'Success' in installation
        assert state()==before,'Install changed save data'
    remote=adb('shell','pm','path',PKG).decode().splitlines()[0].removeprefix('package:').strip()
    installed=adb('shell','sha256sum',remote).decode().split()[0];assert installed==sha,'Wrong QA APK'
    cache=ROOT/'.verification-cache/CascadeResponsiveness';cache.mkdir(parents=True,exist_ok=True)
    request=cache/'Request';request.write_text(args.variant if args.repeats==1 and not args.profile_model_work and args.visual_level==4 and not args.checkpoint74_continuation else json.dumps({'variant':args.variant,'repeats':args.repeats,'profileModelWork':args.profile_model_work,'visualLevel':args.visual_level,'checkpoint74Continuation':args.checkpoint74_continuation}),'ascii')
    adb('shell','rm','-f',BASE+'/CascadeTiming/Report.json',BASE+'/HOTR_CascadeTiming_Continue')
    adb('push',request,BASE+'/HOTR_RunCascadeTiming')
    utc=datetime.now(timezone.utc).isoformat()
    launch=adb('shell','am','start','-W','-n',PKG+'/com.unity3d.player.UnityPlayerActivity').decode().strip()
    video=None;deadline=time.monotonic()+260+150*(args.repeats-1)
    while time.monotonic()<deadline:
        raw=adb('shell','cat',BASE+'/CascadeTiming/Report.json',check=False)
        try:report=json.loads(raw)
        except (ValueError,UnicodeError):time.sleep(1);continue
        if report['status']=='READY_FOR_CAPTURE' and args.variant=='visual' and video is None:
            video=out/'HR_NaturalCascade.mp4'
            adb('exec-out','screencap','-p') # warm screenshot path before the recording
            proc=subprocess.Popen([str(ADB),'-s',args.serial,'shell','screenrecord','--size','720x1280','--time-limit','7','--bit-rate','8000000','/sdcard/HOTR_Cascade.mp4'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(.8);adb('push',request,BASE+'/HOTR_CascadeTiming_Continue')
            _,err=proc.communicate(timeout=25);assert proc.returncode==0,err
            adb('pull','/sdcard/HOTR_Cascade.mp4',video)
        if report['status'].startswith(('PASS','FAIL')):break
        time.sleep(1)
    else:raise TimeoutError('Cascade probe report unavailable')
    (out/'Report.json').write_bytes(raw)
    profiling=validate_report(report,args.variant,args.repeats,args.require_profiling)
    if args.visual_level!=4 or args.checkpoint74_continuation:
        assert report.get('visualLevel')==args.visual_level and report.get('checkpoint74Continuation') is args.checkpoint74_continuation,'Requested continuation control/level was not executed'
    if args.variant=='visual':
        assert report['rows'][0]['name']=='L'+str(args.visual_level)+'_0_30','Wrong recorded level'
    if args.profile_model_work:
        assert report.get('modelWorkEnabled') is True and all(row.get('modelWork',{}).get('snapshotCalls',0)>0 for row in report['rows']),'Detailed model work was not measured'
    assert datetime.fromisoformat(report['utc'].replace('Z','+00:00'))>=datetime.fromisoformat(utc)
    after=state();assert before==after,'Isolated fixture changed saved state'
    result={'utc':utc,'serial':args.serial,'variant':args.variant,'repeats':args.repeats,'profilingAvailable':profiling,'profile_model_work':args.profile_model_work,'visual_level':args.visual_level,'checkpoint74_continuation':args.checkpoint74_continuation,'apk_sha256':sha,'installed_apk_sha256':installed,'install':installation,'launch':launch,'before':before,'after':after,'data_unchanged':True,'scope':'Isolated native GameplayScreen; no campaign attempt/progression hooks or screen-input claim. Visual run has recording overhead and is excluded from timing measurements. Optional repeats reload boards and banks; only process/code/driver paths are warm. Legacy APKs lack detailed provenance unless --require-profiling is specified.'}
    result['qa_target']=target
    (out/'Installation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'variant':args.variant,'data_unchanged':True,'rows':[(r['name'],round(r['wallSeconds'],3),r['lateFrames']) for r in report['rows']]}))

if __name__=='__main__':main()
