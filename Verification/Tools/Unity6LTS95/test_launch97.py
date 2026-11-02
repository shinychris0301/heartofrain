"""Synthetic host controls only. No device, recorder, native build or SDK runs."""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent))
SPEC=importlib.util.spec_from_file_location('launch97_host',Path(__file__).with_name('launch97.py'))
api=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(api)


class Process:
    def __init__(self):self.returncode=None
    def poll(self):return self.returncode
    def wait(self,timeout):self.returncode=0;return 0
    def kill(self):self.returncode=-9


class FakeTarget:
    def __init__(self,root):
        self.serial='emulator-5558';self.deadline=time.monotonic()+600
        self.build={'invocationPath':root/'Invocation.json','nativePath':root/'BuildDevelopment.json','apk':root/'game.apk',
                    'native':{'after':{'showSplashScreen':False,'showUnityLogo':False}}}
        for key in ('invocationPath','nativePath','apk'):self.build[key].write_bytes(b'fixture')
        self.static={'path':'StaticApk95.json','sha256':'a'*64,'bytes':1}
        self.owner={'installed':True,'ownerStopped':True,'activeAttempts':0,'externalFileHashes':{'a':'b'},'preferences':{'c':'d'},'apkHashes':['e'*64]}
        self.identity_value={'index':0,'consoleAndADBCurrentBootMatch':True,'bootSHA256':'f'*64}
        self.packages={api.ld.OWNER:'/data/app/owner/base.apk',api.PACKAGE:'/data/app/candidate/base.apk','org.fixture.other':'/data/app/other/base.apk'}
        self.started=False;self.recorder=False;self.foreign_file=False;self.preferences=False;self.video=b'\x00\x00\x00\x18ftypisom'+b'x'*2048
        self.paths=['/data/app/candidate/base.apk']
    def header(self):
        return {'runner':api.ld.bound(Path(api.ld.__file__)),'apk':api.ld.bound(self.build['apk']),
                'nativeReport':api.ld.bound(self.build['nativePath']),'buildInvocation':api.ld.bound(self.build['invocationPath']),
                'staticReport':self.static,'package':api.PACKAGE}
    def identity(self):return deepcopy(self.identity_value)
    def owner_snapshot(self):return deepcopy(self.owner)
    def installed_paths(self,package):return self.paths
    def remote_hash(self,path):
        import hashlib
        return hashlib.sha256(self.video).hexdigest() if path.endswith('.mp4') else api.ld.sha(self.build['apk'])
    def exists(self,path):
        return self.recorder if path.startswith('/data/local/tmp/') else self.foreign_file
    def adb(self,*args,**kwargs):
        if args[:4]==('shell','pm','list','packages'):return '\n'.join('package:'+path+'='+name for name,path in self.packages.items())
        if args[:2]==('shell','pidof'):
            return ('42' if self.recorder else '') if args[2]=='screenrecord' else ('1234' if self.started else '')
        if args[:2]==('shell','find'):return '/fixture/foreign-data' if self.foreign_file else ''
        if args[:3]==('shell','run-as',api.PACKAGE):
            return ('PRESENT' if self.preferences else 'ABSENT') if args[3]=='sh' else 'saved.xml'
        if args[:3]==('shell','dumpsys','window'):return 'KeyguardServiceDelegate\n showing=false\n'
        if args[:3]==('shell','dumpsys','activity'):return 'mResumedActivity: '+api.ACTIVITY
        if args[:2]==('shell','stat'):return str(len(self.video))
        raise AssertionError('Unexpected synthetic transport read')


class LaunchControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.stack=ExitStack();self.addCleanup(self.stack.close)
        evidence=self.root/'Evidence'
        for module,key,value in [(api,'ROOT',self.root),(api.ld,'ROOT',self.root),(api.ld,'EVIDENCE',evidence),
                                 (api,'PUBLIC',evidence/'FirstLaunch97'),(api,'PRIVATE',self.root/'private'),
                                 (api,'__file__',str(self.root/'launch97.py')),(api.ld,'__file__',str(self.root/'ldplayer95.py'))]:
            self.stack.enter_context(patch.object(module,key,value))
        Path(api.__file__).write_bytes(b'host fixture launch');Path(api.ld.__file__).write_bytes(b'host fixture LD')
        self.stack.enter_context(patch.object(api,'LD_HELPER_SHA',api.ld.sha(Path(api.ld.__file__))))
        self.target=FakeTarget(self.root)
        self.output=api.PUBLIC/('a'*32)
        self.installation=evidence/'LDPlayerRuns'/('b'*32)/'Installation.json'
        owner=deepcopy(self.target.owner);header=self.target.header();before={k:v for k,v in self.target.packages.items() if k!=api.PACKAGE}
        preflight={**header,'status':'PASS_READ_ONLY_LDPLAYER95_FULL_GAME_PREFLIGHT','identity':self.target.identity(),
                   'ownerBefore':owner,'packagesBefore':before}
        installed={**header,'status':'PASS_FRESH_FULL_GAME_LDPLAYER95_INSTALL','identity':self.target.identity(),
                   'ownerBefore':owner,'ownerAfter':owner,'ownerFinal':owner,'packagesBefore':before,'packagesAfter':self.target.packages,
                   'ownerDataUnchanged':True,'ownerPreservedAtExit':True,'otherInstalledPackagesUnchanged':True,
                   'gameAutomaticallyLaunched':False,'installResult':'Success'}
        api.ld.write(self.installation.parent/'Preflight.json',preflight);api.ld.write(self.installation,installed)

    def rewrite_install(self,key,value):
        record=api.ld.read(self.installation);record[key]=value;self.installation.write_text(json.dumps(record))

    def pipeline(self,mutate=None):
        def popen(*args,**kwargs):self.target.recorder=True;return Process()
        def raw(target,*args,**kwargs):
            if args[:2]==('exec-out','cat'):
                remote=api.remote_path(self.output.name)
                return ('screenrecord\x00--time-limit\x0030\x00--bit-rate\x008000000\x00'+remote+'\x00').encode(),b'',0
            if args[:3]==('shell','am','start'):
                self.assertEqual(args,('shell','am','start','-W','-n',api.ACTIVITY))
                self.target.started=True
                if mutate:mutate()
                return b'Status: ok\n',b'',0
            if args[0]=='pull':
                Path(args[2]).write_bytes(self.target.video);return b'fixture pulled',b'',0
            if args[0]=='logcat':
                self.assertEqual(args,('logcat','-d','--pid=1234','-v','brief'))
                return b'fixture runtime',b'',0
            raise AssertionError('Unexpected synthetic binary transport read')
        def capture(target,private,name,foreground):
            path=private/name;api.raw_file(path,b'host PNG fixture')
            return {**api.ld.bound(path),'width':900,'height':1600,'capturedUtc':api.ld.utc()}
        with patch.object(api,'make_target',return_value=self.target),patch.object(api.subprocess,'Popen',side_effect=popen) as process, \
             patch.object(api,'raw_adb',side_effect=raw) as command,patch.object(api,'wait_recorder',return_value=42), \
             patch.object(api,'capture_png',side_effect=capture),patch.object(api.ld,'build',return_value=self.target.build), \
             patch.object(api.ld,'validated_static',return_value=self.target.static):
            result=api.record(self.target.build['invocationPath'],self.installation,self.output)
        return result,process,command

    def test_build_or_frozen_helper_failure_precedes_any_device_command(self):
        with patch.object(api.ld,'sha',return_value='0'*64),patch.object(api.ld,'LDPlayer') as constructor,patch.object(api.ld,'run') as command:
            with self.assertRaisesRegex(ValueError,'FrozenLDCandidateHelper'):api.make_target(self.root/'Invocation.json')
        constructor.assert_not_called();command.assert_not_called()
        with patch.object(api.ld,'LDPlayer',side_effect=ValueError('FixtureNoActualBuild')),patch.object(api.ld,'run') as command:
            with self.assertRaisesRegex(ValueError,'FixtureNoActualBuild'):api.make_target(self.root/'Invocation.json')
        command.assert_not_called()

    def test_physical_phone_selector_is_rejected_by_frozen_ld_constructor_without_commands(self):
        with patch.object(api.ld,'build',return_value=self.target.build),patch.object(api.ld,'validated_static',return_value=self.target.static), \
             patch.dict(api.ld.os.environ,{'HOTR_LDPLAYER95_SERIAL':'fixture-physical-phone','HOTR_LDPLAYER95_INDEX':'0'}),patch.object(api.ld,'run') as command:
            with self.assertRaisesRegex(ValueError,'ExplicitEmulatorSelector'):api.make_target(self.root/'Invocation.json')
        command.assert_not_called()

    def test_installation_requires_pass_exact_build_static_and_preserved_owner(self):
        original=api.ld.read(self.installation)
        for key,value in [('status','FAIL'),('apk',{}),('staticReport',{}),('ownerPreservedAtExit',False),
                          ('gameAutomaticallyLaunched',True),('package',api.ld.OWNER)]:
            self.installation.write_text(json.dumps({**original,key:value}))
            with self.subTest(key=key),self.assertRaises(ValueError):api.require_install(self.target,self.installation)

    def test_native_getter_evidence_must_be_false_but_does_not_certify_video(self):
        api.require_install(self.target,self.installation)
        for value in (True,'false',None):
            self.target.build['native']['after']['showSplashScreen']=value
            with self.assertRaisesRegex(ValueError,'SplashGetterConfiguration'):api.require_install(self.target,self.installation)

    def test_split_or_wrong_installed_candidate_apk_is_refused(self):
        self.target.paths=['/data/app/candidate/base.apk','/data/app/candidate/split.apk']
        with self.assertRaisesRegex(ValueError,'SingleInstalledCandidate'):api.installed_candidate(self.target,'a'*64)
        self.target.paths=['/data/app/candidate/base.apk']
        with self.assertRaisesRegex(ValueError,'SingleInstalledCandidate'):api.installed_candidate(self.target,'a'*64)

    def test_owner_active_or_changed_identity_blocks_before_recording(self):
        self.target.owner['activeAttempts']=1
        with patch.object(api,'make_target',return_value=self.target),patch.object(api.subprocess,'Popen') as popen:
            with self.assertRaisesRegex(ValueError,'OwnerChangedSinceInstall'):api.record(self.target.build['invocationPath'],self.installation,self.output)
        popen.assert_not_called()
        self.target.owner['activeAttempts']=0;self.target.identity_value['bootSHA256']='0'*64
        with patch.object(api,'make_target',return_value=self.target),patch.object(api.subprocess,'Popen') as popen:
            with self.assertRaisesRegex(ValueError,'LDIdentityChangedSinceInstall'):api.record(self.target.build['invocationPath'],self.installation,self.output)
        popen.assert_not_called()

    def test_existing_candidate_files_preferences_and_running_process_are_preserved(self):
        for field in ('foreign_file','preferences','started'):
            setattr(self.target,field,True)
            with self.subTest(field=field),self.assertRaises(ValueError):api.pristine_candidate(self.target)
            setattr(self.target,field,False)

    def test_recording_command_refuses_foreign_owner_paths_and_shell_content(self):
        good=api.remote_path('a'*32);args=api.recorder_args(self.target,good)
        self.assertEqual(args[-5:],['--time-limit','30','--bit-rate','8000000',good])
        for wrong in ['/sdcard/Android/data/'+api.ld.OWNER+'/files/startup.mp4',good+';anything','/data/local/tmp/foreign.mp4']:
            with self.subTest(path=wrong),self.assertRaisesRegex(ValueError,'OwnedRemoteVideoOnly'):api.recorder_args(self.target,wrong)

    def test_recorder_pid_requires_exact_owned_cmdline_not_foreign_recording(self):
        remote=api.remote_path('a'*32)
        good=('screenrecord\x00--time-limit\x0030\x00--bit-rate\x008000000\x00'+remote+'\x00').encode()
        self.assertTrue(api.recorder_matches(good,remote))
        for bad in [good.replace(b'30\x00',b'31\x00'),good.replace(remote.encode(),b'/data/local/tmp/foreign.mp4'),b'',b'other\x00'+good]:
            self.assertFalse(api.recorder_matches(bad,remote))
        process=Process();process.returncode=1
        with self.assertRaisesRegex(ValueError,'RecorderExitedBeforeCandidateLaunch'):api.wait_recorder(self.target,process,remote)

    def test_remote_recording_start_is_verified_using_exact_live_pid_cmdline(self):
        remote=api.remote_path('a'*32);self.target.recorder=True
        cmdline=('screenrecord\x00--time-limit\x0030\x00--bit-rate\x008000000\x00'+remote+'\x00').encode()
        with patch.object(api,'raw_adb',return_value=(cmdline,b'',0)) as read:
            self.assertEqual(api.wait_recorder(self.target,Process(),remote),42)
        read.assert_called_once_with(self.target,'exec-out','cat','/proc/42/cmdline')
        with patch.object(api,'raw_adb',return_value=(cmdline.replace(remote.encode(),b'/data/local/tmp/foreign.mp4'),b'',0)), \
             patch.object(api.time,'monotonic',side_effect=[0,0,7]),patch.object(api.time,'sleep'):
            with self.assertRaisesRegex(ValueError,'OwnedRecorderStartUnverified'):
                api.wait_recorder(self.target,Process(),remote)

    def test_existing_remote_video_is_refused_without_truncation_or_recorder_start(self):
        original=self.target.exists
        self.target.exists=lambda path:True if path.startswith('/data/local/tmp/') else original(path)
        with patch.object(api,'make_target',return_value=self.target),patch.object(api.subprocess,'Popen') as popen:
            with self.assertRaisesRegex(ValueError,'ExistingRemoteRecordingPreserved'):api.record(self.target.build['invocationPath'],self.installation,self.output)
        popen.assert_not_called()

    def test_mocked_recording_preserves_owner_packages_and_requires_visual_review(self):
        result,process,command=self.pipeline()
        self.assertEqual(result['status'],'RECORDED_FIRST_OBSERVED_LTS_LAUNCH97_REQUIRES_VISUAL_REVIEW')
        self.assertFalse(result['rootVisualReviewCompleted']);self.assertFalse(result['splashAbsenceAutomaticallyCertified'])
        self.assertFalse(result['privateEvidencePublished']);self.assertFalse(result['remoteRecordingDeletionAttempted'])
        self.assertTrue(result['ownerDataUnchanged']);self.assertEqual(result['ownerBefore'],result['ownerAfter'])
        self.assertEqual(result['packagesBefore'],result['packagesAfter'])
        self.assertEqual(result['selectedRuntimeErrorCount'],0)
        self.assertIn('private/',result['privateOriginalVideo']['path'])
        self.assertEqual(process.call_args.kwargs['creationflags'],subprocess.CREATE_NO_WINDOW)
        with patch.object(api.ld,'build',return_value=self.target.build),patch.object(api.ld,'validated_static',return_value=self.target.static),patch.object(api.ld,'run') as device:
            receipt=api.validate_launch_receipt(self.output/'Report.json',self.target.build['invocationPath'],self.installation)
        self.assertFalse(receipt['visualApproval']);device.assert_not_called()

    def test_owner_change_at_exit_fails_without_clear_stop_or_rollback(self):
        result,_,commands=self.pipeline(lambda:self.target.owner['preferences'].update({'foreign':'changed'}))
        self.assertEqual(result['status'],'FAIL_FIRST_OBSERVED_LTS_LAUNCH97')
        self.assertEqual(result['finalGuard']['errorCategory'],'Launch97OwnerChangedAtExit')
        self.assertTrue((self.output/'Report.json').is_file())
        for call in commands.call_args_list:
            self.assertFalse(any(str(arg) in ('force-stop','clear','uninstall') for arg in call.args))

    def test_other_package_change_fails_without_acceptance(self):
        result,_,_=self.pipeline(lambda:self.target.packages.update({'org.fixture.extra':'/extra.apk'}))
        self.assertEqual(result['status'],'FAIL_FIRST_OBSERVED_LTS_LAUNCH97')
        self.assertEqual(result['finalGuard']['errorCategory'],'Launch97InstalledPackageInventoryChanged')

    def test_malformed_video_cannot_be_accepted_from_successful_recorder_exit(self):
        self.target.video=b'not an mp4 header'+b'x'*2048
        result,_,_=self.pipeline()
        self.assertEqual(result['status'],'FAIL_FIRST_OBSERVED_LTS_LAUNCH97')
        self.assertEqual(result['errorCategory'],'Launch97MP4HeaderRequired')
        self.assertFalse(result['rootVisualReviewCompleted'])

    def test_existing_private_video_is_preserved_instead_of_overwritten_by_pull(self):
        path=api.PRIVATE/self.output.name/'Startup.mp4'
        result,_,commands=self.pipeline(lambda:path.write_bytes(b'keep foreign local file'))
        self.assertEqual(result['status'],'FAIL_FIRST_OBSERVED_LTS_LAUNCH97')
        self.assertEqual(result['errorCategory'],'Launch97ExistingPrivateVideoPreserved')
        self.assertEqual(path.read_bytes(),b'keep foreign local file')
        self.assertFalse(any(len(call.args)>1 and call.args[1]=='pull' for call in commands.call_args_list))

    def test_foreign_or_tampered_private_artifact_cannot_validate_recording(self):
        result,_,_=self.pipeline();path=self.output/'Report.json'
        original=api.ld.read(path);foreign=self.root/'Foreign.mp4'
        foreign.write_bytes((api.ROOT/result['privateOriginalVideo']['path']).read_bytes())
        redirected=deepcopy(original);redirected['privateOriginalVideo']=api.ld.bound(foreign)
        path.write_text(json.dumps(redirected))
        with patch.object(api.ld,'build',return_value=self.target.build),patch.object(api.ld,'validated_static',return_value=self.target.static):
            with self.assertRaisesRegex(ValueError,'PrivateRecordingArtifactChanged'):
                api.validate_launch_receipt(path,self.target.build['invocationPath'],self.installation)
        path.write_text(json.dumps(original))
        (api.ROOT/result['privateOriginalVideo']['path']).write_bytes(b'tampered')
        with patch.object(api.ld,'build',return_value=self.target.build),patch.object(api.ld,'validated_static',return_value=self.target.static):
            with self.assertRaisesRegex(ValueError,'PrivateRecordingArtifactChanged'):
                api.validate_launch_receipt(path,self.target.build['invocationPath'],self.installation)


if __name__=='__main__':unittest.main()
