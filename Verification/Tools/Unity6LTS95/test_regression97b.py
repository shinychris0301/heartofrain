"""Synthetic host controls only; never contact Android, Unity or native tools."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import regression97b as M


def native():
    passed=[]
    for level in range(1,51):
        passed.append('L'+str(level)+' accepts natural move')
        for tool in range(4):
            passed.extend(('L'+str(level)+' tool '+str(tool)+' spends one stock','L'+str(level)+' tool '+str(tool)+' preserves moves'))
    passed.extend(M.LIFECYCLE)
    return dict(status='PASS_NATIVE_REGRESSION',failures=[],unity=M.VERSION,platform='Android',boards=50,actions=408,clips=354,
                checks=len(passed),passed=passed,labels=1,damageFamilies=sorted(M.FAMILIES),width=540,height=960,
                utc='2026-10-27T10:00:01Z')


def profile(state=None):
    return json.dumps({'payload':json.dumps({'attempts':[] if state is None else [{'state':state}],
        'currentLevel':1,'completed':0,'coins':1250,'lives':5,'revision':0})})


class MarkerTarget:
    def __init__(self,files):self.files=dict(files);self.commands=[]
    def exists(self,path):return path in self.files
    def adb(self,*args,**kwargs):
        self.commands.append(args)
        if args[:2]==('exec-out','cat'):return self.files[args[2]]
        if args[:2]==('shell','rm'):del self.files[args[2]];return ''
        raise AssertionError('Unexpected fake command')


class OrdinaryTarget:
    def __init__(self,package=M.PACKAGE):
        self.package=package;self.base=M.base_for(package);self.commands=[]
        self.files={self.base+'/Profiles/Development-v1/profile.json':profile(),
                    self.base+'/Profiles/Development-v1/Authority/profile.json':'not a PlayerProfile envelope',
                    self.base+'/Durable/other.json':'all ordinary files are protected',
                    self.base+'/Regression/Old.png':'generated output is excluded'}
    def installed_paths(self,package):return ['/data/app/fake/base.apk']
    def remote_hash(self,path):return 'a'*64
    def exists(self,path):return path==self.base or path in self.files
    def adb(self,*args,**kwargs):
        self.commands.append(args)
        if args[:2]==('shell','find'):return '\n'.join(self.files)
        if args[:2]==('shell','sha256sum'):return '\n'.join(hashlib.sha256(self.files[path].encode()).hexdigest()+'  '+path for path in args[2:])
        if args[:2]==('exec-out','cat'):return self.files[args[2]]
        if args[:3]==('shell','run-as',self.package) and args[3]=='sh':return 'PRESENT'
        if args[:4]==('shell','run-as',self.package,'ls'):return self.package+'.v2.playerprefs.xml'
        if args[:4]==('exec-out','run-as',self.package,'sha256sum'):return 'b'*64+'  '+args[4]
        if args[:2]==('shell','pidof'):return ''
        raise AssertionError('Unexpected fake command: '+repr(args))


class Regression97Guards(unittest.TestCase):
    def exercise_lifecycle(self,root,change_boot):
        public=root/'public';private=root/'private';public.mkdir();private.mkdir()
        inputs=[]
        for name in ('Build.json','NativeBuild.json','GameSources.json','Game.apk'):
            path=root/name;path.write_bytes(name.encode());inputs.append(path)
        build={'invocationPath':inputs[0],'nativePath':inputs[1],'gameSources':inputs[2],'apk':inputs[3]}
        context={'build':build,'binding':{'launch':'bound'},'static':{'static':'bound'},'installation':{'installation':'bound'},'report':{'identity':{'boot':'old'}}}
        before={'installedSHA256':'a'*64,'activeAttempts':0,'durable':'same'};owner={'installed':True,'durable':'owner-same'}
        report=native();raw=json.dumps(report).encode();commands=[]
        class FakeTarget:
            def __init__(self,build,installation=None):self.deadline=0;self.current='99';self.boot='old';self.files={}
            def identity(self):return {'boot':self.boot}
            def exists(self,path):return path in self.files
            def remote_hash(self,path):return hashlib.sha256(self.files[path]).hexdigest()
            def adb(self,*args,**kwargs):
                commands.append(args)
                if args[:4]==('shell','pm','list','packages'):return 'package:/data/app/owner/base.apk='+M.OWNER+'\npackage:/data/app/candidate/base.apk='+M.PACKAGE
                if args[:2]==('shell','pidof'):return self.current
                if args[:3]==('shell','am','force-stop'):self.current='';return ''
                if args[0]=='push':self.files[args[2]]=Path(args[1]).read_bytes();return ''
                if args[:3]==('shell','am','start'):
                    self.current='102' if getattr(self,'launched',False) else '101';self.launched=True;self.files.pop(M.BASE+'/'+M.MARKER,None);return 'Status: ok'
                if args[:2]==('exec-out','cat') and args[2]==M.REMOTE+'/Regression.json':
                    if change_boot:self.boot='new'
                    return raw
                if args[:2]==('exec-out','cat'):return self.files[args[2]]
                if args[:2]==('shell','rm'):del self.files[args[2]];return ''
                raise AssertionError('Unexpected fake command '+repr(args))
        def bounded(path):
            path=Path(path);return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
        with patch.object(M,'reviewed_launch',return_value=(context,{'visual':'root'})),patch.object(M,'fixture_bindings',return_value=['bound-source']),\
             patch.object(M,'outputs',return_value=(public,private)),patch.object(M,'Target',FakeTarget),patch.object(M,'bound',side_effect=bounded),\
             patch.object(M.launch97,'unlocked'),patch.object(M,'ordinary',side_effect=lambda target,package,expected_apk=None:copy.deepcopy(before if package==M.PACKAGE else owner)),\
             patch.object(M,'markers',side_effect=lambda target,package=M.PACKAGE:sorted(path.removeprefix(M.BASE+'/') for path in target.files)),\
             patch.object(M,'geometry',return_value=(540,960)),patch.object(M.ld,'build',return_value=build),\
             patch.object(M,'seconds',return_value=int(M.when('2026-10-27T10:00:00Z').timestamp())),\
             patch.object(M,'modified',return_value=int(M.when('2026-10-27T10:00:01Z').timestamp())),\
             patch.object(M,'collect',return_value={'nativeReport':{'synthetic':'host-control'}}),patch.object(M.time,'sleep'):
            result=M.run(inputs[0],root/'Installation.json',root/'Launch.json',public,60)
        return result,commands,public

    def test_complete_fake_lifecycle_only_stops_launches_candidate_and_writes_final_receipt_once(self):
        with tempfile.TemporaryDirectory() as folder:
            result,commands,public=self.exercise_lifecycle(Path(folder),False)
            self.assertEqual(result['status'],'PASS_LTS97_ANDROID_TRANSIENT_REGRESSION')
            self.assertTrue(result['candidateDurableDataUnchanged']);self.assertTrue(result['ownerDurableDataUnchanged'])
            self.assertEqual(result['actualNativeCounts']['checks'],native()['checks']);self.assertNotEqual(result['actualNativeCounts']['checks'],1716)
            stops=[row for row in commands if row[:3]==('shell','am','force-stop')]
            starts=[row for row in commands if row[:3]==('shell','am','start')]
            self.assertEqual(len(stops),2);self.assertEqual(len(starts),2)
            self.assertTrue(all(row[-1]==M.PACKAGE for row in stops));self.assertTrue(all(row[-1].startswith(M.PACKAGE+'/') for row in starts))
            self.assertTrue((public/'Invocation.json').is_file());self.assertTrue((public/'Authorization.json').is_file())

    def test_boot_change_after_native_pass_blocks_wrapper_without_cleanup_or_normal_relaunch(self):
        with tempfile.TemporaryDirectory() as folder:
            result,commands,public=self.exercise_lifecycle(Path(folder),True)
            self.assertEqual(result['status'],'BLOCKED_LTS97_REGRESSION_PRESERVATION');self.assertTrue(result['requiresOperatorCleanup'])
            self.assertEqual(result['lastNativeStatus'],'PASS_NATIVE_REGRESSION')
            self.assertEqual(len([row for row in commands if row[:3]==('shell','am','force-stop')]),1)
            self.assertEqual(len([row for row in commands if row[:3]==('shell','am','start')]),1)
            self.assertFalse(any(row[:2]==('shell','rm') for row in commands));self.assertNotIn('normalCandidateRelaunch',result)
            self.assertFalse((public/'CandidateAfterRelaunch.json').exists());self.assertTrue((public/'Invocation.json').is_file())

    def test_exact_new_engine_native_coverage_accepts_actual_count_without_1716_assumption(self):
        value=native();self.assertNotEqual(value['checks'],1716);M.native_scope(value)

    def test_old_engine_wrong_platform_missing_family_or_failed_native_refused(self):
        for change in ({'unity':'2022.3.62f3'},{'unity':'6000.6.6f1'},{'platform':'WindowsPlayer'},
                       {'damageFamilies':sorted(M.FAMILIES-{'crate'})},{'failures':['actual failure']},{'failures':None},{'checks':1}):
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'ActualNativeCoverageRequired'):M.native_scope({**native(),**change})
        absent=native();del absent['failures']
        with self.assertRaisesRegex(ValueError,'ActualNativeCoverageRequired'):M.native_scope(absent)

    def test_every_board_natural_move_and_all_four_tool_semantics_are_required(self):
        for name in ('L50 accepts natural move','L27 tool 3 spends one stock','L1 tool 0 preserves moves'):
            value=native();value['passed'].remove(name);value['checks']-=1
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'MoveMissing|ToolCoverageMissing'):M.native_scope(value)

    def test_continuation_refill_and_completion_lifecycle_cases_are_required(self):
        for name in M.LIFECYCLE:
            value=native();value['passed'].remove(name);value['checks']-=1
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'LifecycleCaseMissing'):M.native_scope(value)

    def test_fresh_native_requires_exact_engine_geometry_new_hash_utc_and_mtime(self):
        value=native();raw=json.dumps(value).encode();start=int(M.when('2026-10-27T10:00:00Z').timestamp())
        M.fresh_report(value,raw,None,start,start+1,540,960)
        for report,old,mtime,width in ((value,hashlib.sha256(raw).hexdigest(),start+1,540),
                                      (value,None,start-1,540),(value,None,start+1,720),
                                      ({**value,'unity':'2022.3.62f3'},None,start+1,540),
                                      ({**value,'utc':'2026-10-27T09:59:59Z'},None,start+1,540)):
            with self.subTest(report=report['utc'],old=old,mtime=mtime,width=width),self.assertRaises(ValueError):
                M.fresh_report(report,raw,old,start,mtime,width,960)

    def test_profile_parser_blocks_active_or_unknown_states_without_parsing_nested_authority(self):
        self.assertIsNone(M.canonical_profile('Profiles/Development-v1/Authority/profile.json','not parsed'))
        self.assertEqual(M.canonical_profile('Profiles/Development-v1/profile.json',profile())['activeAttempts'],0)
        for state in ('Reserved','Started','Unknown'):
            with self.subTest(state=state),self.assertRaisesRegex(ValueError,'Attempt'):M.canonical_profile('Profiles/Development-v1/profile.json',profile(state))

    def test_snapshot_hashes_all_durable_files_authority_and_preferences_excluding_generated_only(self):
        target=OrdinaryTarget();result=M.ordinary(target,M.PACKAGE,'a'*64)
        self.assertEqual(len(result['ordinaryExternalFileHashes']),3);self.assertEqual(len(result['profiles']),1);self.assertEqual(len(result['preferences']),1)
        protected=hashlib.sha256('Profiles/Development-v1/Authority/profile.json'.encode()).hexdigest()
        self.assertIn(protected,result['ordinaryExternalFileHashes'])
        target.files[target.base+'/Durable/other.json']='changed';self.assertNotEqual(result,M.ordinary(target,M.PACKAGE,'a'*64))

    def test_installed_candidate_must_match_actual_bound_build_apk(self):
        target=OrdinaryTarget()
        with self.assertRaisesRegex(ValueError,'ExactInstalledAPKRequired'):M.ordinary(target,M.PACKAGE,'c'*64)
        self.assertFalse(any('force-stop' in command or 'push' in command for command in target.commands))

    def test_compiled_candidate_fixture_bytes_must_match_build_manifest_and_protected_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);project=root/'Game';files={}
            for relative in M.FIXTURES:
                original=root/'Unity'/relative;candidate=project/relative
                for path in (original,candidate):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(relative.encode())
                files[relative]={'sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'bytes':candidate.stat().st_size}
            manifest=root/'Sources.json';manifest.write_text(json.dumps({'files':files}))
            def bounded(path):
                path=Path(path);return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
            with patch.object(M,'ROOT',root),patch.object(M.ld.game95,'PROJECT',project),patch.object(M,'bound',side_effect=bounded):
                self.assertEqual(len(M.fixture_bindings({'gameSources':manifest})),5)
                path=project/M.FIXTURES[0];raw=path.read_bytes();path.write_bytes(b'candidate changed')
                with self.assertRaisesRegex(ValueError,'OriginalRuntimeFixtureSourceChanged'):M.fixture_bindings({'gameSources':manifest})
                path.write_bytes(raw);(root/'Unity'/M.FIXTURES[0]).write_bytes(b'original changed')
                with self.assertRaisesRegex(ValueError,'OriginalRuntimeFixtureSourceChanged'):M.fixture_bindings({'gameSources':manifest})

    def test_owner_running_server_configuration_or_pending_marker_prevents_fixture_snapshot(self):
        for mode in ('owner','server','marker'):
            target=OrdinaryTarget(M.OWNER if mode=='owner' else M.PACKAGE)
            if mode=='server':target.files[target.base+'/ServerReview/configuration.json']='{}'
            if mode=='marker':target.files[target.base+'/HOTR_RunOther']='foreign'
            with self.subTest(mode=mode):
                if mode=='owner':
                    with patch.object(M,'pid',return_value='42'),self.assertRaisesRegex(ValueError,'OwnerStopped'):M.ordinary(target,M.OWNER)
                else:
                    with self.assertRaisesRegex(ValueError,'LocalOnly|PendingMarker'):M.ordinary(target,M.PACKAGE,'a'*64)
            self.assertFalse(any('force-stop' in command for command in target.commands))

    def test_durable_data_drift_or_foreign_marker_prevents_candidate_stop(self):
        target=MarkerTarget({})
        with patch.object(M,'markers',return_value=['HOTR_Foreign']),self.assertRaisesRegex(ValueError,'ForeignMarker'):M.stop_idle(target,{})
        with patch.object(M,'markers',return_value=[]),patch.object(M,'ordinary',return_value={'changed':True}),self.assertRaisesRegex(ValueError,'DurableDataChanged'):
            M.stop_idle(target,{'installedSHA256':'a'*64})
        self.assertEqual(target.commands,[])

    def test_only_exact_owned_marker_is_removed_and_foreign_content_is_preserved(self):
        path=M.BASE+'/'+M.MARKER;payload=b'owned';receipt={'sha256':hashlib.sha256(payload).hexdigest()}
        target=MarkerTarget({path:b'foreign'})
        with patch.object(M,'markers',side_effect=lambda target:sorted(path.removeprefix(M.BASE+'/') for path in target.files)),self.assertRaisesRegex(ValueError,'ForeignMarkerContent'):
            M.cleanup_marker(target,payload,receipt)
        self.assertIn(path,target.files);self.assertFalse(any(command[:2]==('shell','rm') for command in target.commands))
        target=MarkerTarget({path:payload})
        with patch.object(M,'markers',side_effect=lambda target:sorted(path.removeprefix(M.BASE+'/') for path in target.files)):M.cleanup_marker(target,payload,receipt)
        self.assertEqual([command for command in target.commands if command[:2]==('shell','rm')],[('shell','rm',path)])

    def test_foreign_marker_survives_owned_cleanup_and_blocks_relaunch(self):
        path=M.BASE+'/'+M.MARKER;foreign=M.BASE+'/HOTR_RunOther';payload=b'owned';target=MarkerTarget({path:payload,foreign:b'foreign'})
        with patch.object(M,'markers',side_effect=lambda target:sorted(path.removeprefix(M.BASE+'/') for path in target.files)),self.assertRaisesRegex(ValueError,'ForeignMarkersPreservedNoRelaunch'):
            M.cleanup_marker(target,payload,{'sha256':hashlib.sha256(payload).hexdigest()})
        self.assertIn(foreign,target.files);self.assertNotIn(path,target.files)

    def test_boot_change_blocks_before_cleanup_or_launch_mutation(self):
        target=types.SimpleNamespace(identity=lambda:{'boot':'new'})
        with self.assertRaisesRegex(ValueError,'BootOrDeviceChangedNoCleanup'):M.assert_identity(target,{'boot':'old'})

    def test_boot_recheck_immediately_before_stop_launch_and_marker_removal(self):
        before={'installedSHA256':'a'*64};target=MarkerTarget({});target.identity=lambda:{'boot':'new'}
        with patch.object(M,'markers',return_value=[]),patch.object(M,'ordinary',return_value=before),self.assertRaisesRegex(ValueError,'BootOrDeviceChangedNoCleanup'):
            M.stop_idle(target,before,{'boot':'old'})
        with self.assertRaisesRegex(ValueError,'BootOrDeviceChangedNoCleanup'):M.launch(target,{'boot':'old'})
        self.assertEqual(target.commands,[])
        payload=b'owned';path=M.BASE+'/'+M.MARKER;target=MarkerTarget({path:payload});target.identity=lambda:{'boot':'new'}
        with patch.object(M,'markers',return_value=[M.MARKER]),self.assertRaisesRegex(ValueError,'BootOrDeviceChangedNoCleanup'):
            M.cleanup_marker(target,payload,{'sha256':hashlib.sha256(payload).hexdigest()},{'boot':'old'})
        self.assertIn(path,target.files);self.assertFalse(any(row[:2]==('shell','rm') for row in target.commands))

    def test_frame_inventory_rejects_duplicates_traversal_and_incomplete_metadata(self):
        for names in ([],['A.png','A.png'],['../A.png'],['A.txt']):
            with self.subTest(names=names),self.assertRaisesRegex(ValueError,'ExactDeclaredFramesRequired'):M.frame_names({'frames':names})
        self.assertEqual(M.frame_names({'frames':['A.png']}),['A.png']);path=M.REMOTE+'/A.png';digest='a'*64
        for text in ('',digest+'  '+path+'\n'+digest+'  '+path,digest+'  '+M.REMOTE+'/Other.png'):
            with self.subTest(text=text),self.assertRaises(ValueError):M.metadata(text,[path],r'([0-9a-f]{64})\s+(.+)','Invalid')

    def test_actual_geometry_not_phone_hardcode_and_landscape_refused(self):
        target=types.SimpleNamespace(adb=lambda *args:'Physical size: 720x1280\nOverride size: 900x1600')
        self.assertEqual(M.geometry(target),(900,1600))
        with self.assertRaisesRegex(ValueError,'ActualPortrait'):M.geometry(types.SimpleNamespace(adb=lambda *args:'Physical size: 1600x900'))

    def test_m70_failures_or_stale_atlas_are_not_accepted_as_coverage(self):
        start=int(M.when('2026-10-27T10:00:00Z').timestamp())
        base={'status':'PASS_NATIVE_M70_DEVICE','failures':[],'utc':'2026-10-27T10:00:01Z',
              'textures':[{}]*7,'idleAdvancement':[{'passed':True}]*3}
        for change in ({'status':'FAIL_NATIVE_M70_DEVICE'},{'failures':['native failure']},{'failures':None},
                       {'utc':'2026-10-27T09:59:59Z'},{'textures':[{}]*6},
                       {'idleAdvancement':[{'passed':True},{'passed':False},{'passed':True}]}):
            atlas=json.dumps({**base,**change}).encode();target=types.SimpleNamespace(adb=lambda *args,**kwargs:atlas)
            with self.subTest(change=change),patch.object(M,'modified',return_value=start+1),self.assertRaisesRegex(ValueError,'FreshM70CoverageRequired'):
                M.collect(target,Path('unused-public'),Path('unused-private'),{'frames':['A.png']},b'host',start,540,960)

    def test_capture_collection_records_all_hashes_and_retains_four_fresh_originals(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);public=root/'public';private=root/'private';public.mkdir();private.mkdir()
            report=native();report['frames']=[choices[0] for choices in M.SELECTED];raw=json.dumps(report).encode()
            atlas=json.dumps({'status':'PASS_NATIVE_M70_DEVICE','failures':[],'utc':'2026-10-27T10:00:01Z',
                              'textures':[{}]*7,'idleAdvancement':[{'passed':True}]*3}).encode()
            files={M.REMOTE+'/'+name:('host-png-'+name).encode() for name in report['frames']}
            files.update({M.REMOTE+'/Regression.json':raw,M.REMOTE+'/M70_Device.json':atlas})
            start=int(M.when('2026-10-27T10:00:00Z').timestamp())
            class Captures:
                def exists(self,path):return path==M.REMOTE or path in files
                def adb(self,*args,**kwargs):
                    if args[:2]==('exec-out','cat'):return files[args[2]]
                    if args[:2]==('shell','find'):return '\n'.join(files)
                    if args[:2]==('shell','sha256sum'):return '\n'.join(hashlib.sha256(files[path]).hexdigest()+'  '+path for path in args[2:])
                    if args[:3]==('shell','stat','-c'):
                        fmt=args[3]
                        return '\n'.join(str(len(files[path]) if fmt=='%s:%n' else start+1)+':'+path for path in args[4:])
                    raise AssertionError('Unexpected synthetic capture command')
            def bounded(path):
                path=Path(path);return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
            with patch.object(M,'modified',return_value=start+1),patch.object(M,'png_size',return_value=(540,960)),patch.object(M,'bound',side_effect=bounded):
                result=M.collect(Captures(),public,private,report,raw,start,540,960)
            self.assertEqual(result['capturedPngCount'],4);self.assertEqual(result['retainedPrivatePngCount'],4)
            inventory=json.loads((public/'CaptureInventory.json').read_text());self.assertEqual(len(inventory['frames']),4)
            for row in inventory['frames']:
                self.assertEqual((private/row['file']).read_bytes(),files[M.REMOTE+'/'+row['file']]);self.assertGreaterEqual(row['deviceMtimeUnix'],start)

    def test_root_visual_sidecar_requires_video_end_capture_clean_log_and_exact_bindings(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);public=root/'public'/('a'*32);public.mkdir(parents=True)
            private=root/'.verification-cache/Unity6LTS95/ColdLaunch97'/public.name;private.mkdir(parents=True)
            launch=public/'Report.json';launch.write_text('{}');video=private/'Startup.mp4';video.write_bytes(b'host-video');image=private/'AfterLaunch_OS.png';image.write_bytes(b'host-image')
            def bound(path):return {'path':Path(path).relative_to(root).as_posix(),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'bytes':Path(path).stat().st_size}
            report={'selectedRuntimeErrorCount':0,'privateOriginalVideo':bound(video),'endOSCapture':bound(image)}
            context={'report':report,'binding':bound(launch)}
            review={'schemaVersion':1,'status':'ROOT_VISUALLY_REVIEWED_LTS_COLD_RELAUNCH97','launchReceipt':bound(launch),'reviewer':'root',
                    'splashAbsent':True,'firstStartRouteCorrect':True,'reviewScope':'Synthetic host validation only','reviewedArtifacts':[bound(video),bound(image)]}
            sidecar=public/'VisualReview.json'
            helpers={'ldHelper':{'host':'ld'},'launchPrimitives':{'host':'launch'},'statePrimitives':{'host':'state'}}
            report.update(helpers)
            with patch.object(M,'ROOT',root),patch.object(M,'bound',side_effect=bound),patch.object(M.cold_launch97,'validate_launch_receipt',return_value=context),patch.object(M,'cold_helper_bindings',return_value=helpers):
                sidecar.write_text(json.dumps(review));self.assertEqual(M.reviewed_launch(launch,'build','install')[0],context)
                report['ldHelper']={'host':'changed'}
                with self.assertRaisesRegex(ValueError,'ColdHelperBindingsChanged'):M.reviewed_launch(launch,'build','install')
                report['ldHelper']=helpers['ldHelper']
                for changes in ({'reviewer':'auto'},{'splashAbsent':False},{'firstStartRouteCorrect':False},{'launchReceipt':{'wrong':'binding'}}):
                    sidecar.write_text(json.dumps({**review,**changes}))
                    with self.subTest(changes=changes),self.assertRaisesRegex(ValueError,'RootReviewedCleanColdRelaunchRequired'):M.reviewed_launch(launch,'build','install')
                sidecar.write_text(json.dumps(review));report['selectedRuntimeErrorCount']=1
                with self.assertRaisesRegex(ValueError,'RootReviewedCleanColdRelaunchRequired'):M.reviewed_launch(launch,'build','install')
                report['selectedRuntimeErrorCount']=0;image.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'ReviewedArtifactChanged'):M.reviewed_launch(launch,'build','install')


if __name__=='__main__':unittest.main(verbosity=2)
