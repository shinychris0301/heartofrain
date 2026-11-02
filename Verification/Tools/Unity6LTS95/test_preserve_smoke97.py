"""Host-only failed-smoke preservation guards; no native/process/registry call."""
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).parent))
SPEC=importlib.util.spec_from_file_location('preserve_smoke97_host',Path(__file__).with_name('preserve_smoke97.py'))
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


class PreservationControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).absolute();self.addCleanup(self.clear_owned_temp)
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        private=self.root/'private';source=private/'Smoke';evidence=self.root/'evidence';old=evidence/'SmokeRuns'/M.OLD_ID
        for module,key,value in [(M,'ROOT',self.root),(M.smoke,'ROOT',self.root),(M.smoke,'PRIVATE',private),
            (M.smoke,'PROJECT',source),(M.smoke,'EVIDENCE',evidence),(M,'SOURCE',source),(M,'DESTINATION',private/'SF2'),
            (M,'OLD',old),(M,'PUBLIC',evidence/'SmokePreservation97'),(M.smoke,'EDITOR',self.root/'editor/Unity.exe'),
            (M.smoke,'TEMPLATE',self.root/'template.cs'),(M.smoke,'__file__',str(self.root/'smoke.py')),
            (M,'__file__',str(self.root/'preserve.py'))]:self.stack.enter_context(patch.object(module,key,value))
        for path in (M.smoke.EDITOR,M.smoke.TEMPLATE,Path(M.smoke.__file__),Path(M.__file__)):
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
        manifest={}
        for relative,raw in [('Assets/Editor/ToolchainSmoke95.cs',b'fixture'),('Assets/Editor/ToolchainSmoke95.cs.meta',b'meta'),
            ('Packages/manifest.json',b'{}'),('ProjectSettings/ProjectVersion.txt',b'm_EditorVersion: 6000.3.27f1\nm_EditorVersionWithRevision: 6000.3.27f1 (672d562a42a7)\n')]:
            path=source/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            manifest[relative]={'sha256':M.smoke.sha(path),'bytes':path.stat().st_size}
        prep=evidence/'SmokePreparation/Set02/Preparation.json'
        self.write(prep,{'status':'PASS_FRESH_MINIMAL_LTS95_SMOKE_PREPARATION','version':M.smoke.VERSION,
                        'project':source.relative_to(self.root).as_posix(),'templateSHA256':M.smoke.sha(M.smoke.TEMPLATE),
                        'inputManifest':{'files':manifest}})
        command=[str(M.smoke.EDITOR),'-batchmode','-nographics','-buildTarget','Android','-projectPath',str(source),
                 '-executeMethod',M.smoke.ENTRY,'-logFile',str(old/'Unity.log')]
        auth={'status':'RUNNING_ACTUAL_LTS95_TOOLCHAIN_SMOKE','command':command,'runnerSHA256':M.smoke.sha(Path(M.smoke.__file__)),
              'editor':M.smoke.binding(M.smoke.EDITOR),'preparation':M.smoke.binding(prep)}
        for name in M.OLD_FILES:
            if name=='Authorization.json':value=auth
            elif name=='Native.json':value={'status':'FAIL_ACTUAL_LTS95_EMPTY_ANDROID_BUILD','unity':M.smoke.VERSION}
            elif name.startswith('MainSources_'):value={'fixture':'main'}
            elif name.startswith('Candidate66Sources_'):value={'fixture':'candidate'}
            elif name.startswith('ExternalTools'):value={'fixture':'preferences'}
            else:value={'fixture':name}
            self.write(old/name,value)
        report={**auth,'status':'FAIL_ACTUAL_LTS95_TOOLCHAIN_SMOKE','exitCode':1,'nativeStatus':'FAIL_ACTUAL_LTS95_EMPTY_ANDROID_BUILD',
                'actualEngineVersionFromLog':M.smoke.VERSION,'ownedJobAssignedBeforeResume':True,'pid':77,'unityPidsAfter':[],
                'nativeReport':M.smoke.binding(old/'Native.json'),**dict.fromkeys(('mainInputsUnchanged','candidate66InputsUnchanged',
                'externalToolPrefFingerprintsUnchanged','embeddedToolMarkersUnchanged'),True)}
        (old/'Invocation.json').write_text(json.dumps(report))
        for key,name in [('INVOCATION_SHA','Invocation.json'),('NATIVE_SHA','Native.json'),('AUTH_SHA','Authorization.json')]:
            self.stack.enter_context(patch.object(M,key,M.binding(old/name)['sha256']))
        self.processes=SimpleNamespace(unity_pids=Mock(return_value=[]))
        self.writer=SimpleNamespace(write=self.write,utc=lambda:'2026-10-27T14:30:00Z')
        self.output=M.PUBLIC/('a'*32)

    def clear_owned_temp(self):
        # Exact fresh TemporaryDirectory only; extended paths also remove long fixture names.
        assert self.root.parent==Path(tempfile.gettempdir()).absolute() and self.root.name.startswith('tmp')
        if os.path.isdir(M.extended(self.root)):shutil.rmtree(M.extended(self.root))

    @staticmethod
    def write(path,value):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x',encoding='utf-8') as stream:json.dump(value,stream)

    def execute(self):
        with patch.object(M.smoke,'readers',return_value=(self.writer,None,self.processes,None,None)), \
             patch.object(M.download,'stopped_pid') as stopped, \
             patch.object(M.smoke,'protected_sources',return_value=({'fixture':'main'},{'fixture':'candidate'})), \
             patch.object(M.smoke,'external_pref_fingerprints',return_value={'fixture':'preferences'}):
            result=M.preserve(self.output)
        return result,stopped

    def test_exact_failed_attempt_moves_once_to_short_path_with_every_byte_retained(self):
        before=M.inventory(M.SOURCE);old=M.evidence();result,stopped=self.execute()
        self.assertEqual(result['status'],'PASS_COMPLETED_FAILED_SMOKE97_PRESERVED_READY_FOR_FRESH_PREPARATION')
        self.assertEqual(M.inventory(M.DESTINATION),before);self.assertFalse(M.present(M.SOURCE));self.assertEqual(M.evidence(),old)
        self.assertFalse(result['oldResultRewritten']);self.assertFalse(result['processStopOrDeleteExecuted'])
        self.assertEqual({call.args[0] for call in stopped.call_args_list},{77})
        self.assertEqual(M.smoke.read(M.OLD/'Invocation.json')['status'],'FAIL_ACTUAL_LTS95_TOOLCHAIN_SMOKE')

    def test_existing_short_destination_wrong_source_and_receipt_collision_are_refused(self):
        M.DESTINATION.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError,'FreshShortDestination'):M.paths(self.output)
        with patch.object(M,'SOURCE',self.root/'vendor'):
            with self.assertRaisesRegex(ValueError,'FixedOwnedSource'):M.paths(self.output)

    def test_completed_fail_is_required_not_running_pass_missing_or_timed_out(self):
        original=M.smoke.read(M.OLD/'Invocation.json')
        for key,value in [('status','RUNNING'),('status','PASS_ACTUAL_LTS95_TOOLCHAIN_SMOKE_WITH_NO_GAME_ACCEPTANCE'),
                          ('timedOut',True),('ownedJobAssignedBeforeResume',False),('mainInputsUnchanged',False)]:
            (M.OLD/'Invocation.json').write_text(json.dumps({**original,key:value}))
            with patch.object(M,'INVOCATION_SHA',M.binding(M.OLD/'Invocation.json')['sha256']):
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'CompletedFailedNativeAttempt'):
                    M.completed(M.SOURCE)

    def test_source_template_version_or_original_receipt_tamper_blocks(self):
        M.completed(M.SOURCE)
        (M.SOURCE/'Assets/Editor/ToolchainSmoke95.cs').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'PreparedSourceChanged'):M.completed(M.SOURCE)
        (M.OLD/'Native.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'FrozenFailedReceipts'):M.completed(M.SOURCE)

    def test_lstat_rejects_dangling_symlink_and_reparse_even_when_exists_would_be_false(self):
        for mode,attributes in [(stat.S_IFLNK,0),(stat.S_IFREG,0x400)]:
            info=SimpleNamespace(st_mode=mode,st_file_attributes=attributes,st_nlink=1)
            with patch.object(M.os,'lstat',return_value=info),self.assertRaisesRegex(ValueError,'LinkOrReparse'):
                M.safe(self.root/'dangling')

    def test_regular_hardlinked_files_and_ancestors_are_refused(self):
        info=SimpleNamespace(st_mode=stat.S_IFREG,st_file_attributes=0,st_nlink=2)
        with patch.object(M.os,'lstat',return_value=info),self.assertRaisesRegex(ValueError,'HardLinkedFile'):
            M.safe(self.root/'evidence.json')

    def test_no_unity_and_actual_recorded_pid_ended_are_mandatory(self):
        self.processes.unity_pids.return_value=[88]
        with patch.object(M.download,'stopped_pid') as stopped:
            with self.assertRaisesRegex(ValueError,'NoRunningUnity'):M.idle(self.processes,77)
        stopped.assert_not_called()
        self.processes.unity_pids.return_value=[]
        with patch.object(M.download,'stopped_pid',side_effect=ValueError('FixtureRunningOldPID')):
            with self.assertRaisesRegex(ValueError,'FixtureRunningOldPID'):M.idle(self.processes,77)

    def test_main_candidate_or_preference_drift_is_refused(self):
        with patch.object(M.smoke,'protected_sources',return_value=({'fixture':'main'},{'fixture':'candidate'})), \
             patch.object(M.smoke,'external_pref_fingerprints',return_value={'changed':True}):
            with self.assertRaisesRegex(ValueError,'PreferenceFingerprintDrift'):M.protected(None,None)
        with patch.object(M.smoke,'protected_sources',return_value=({'changed':True},{'fixture':'candidate'})):
            with self.assertRaisesRegex(ValueError,'ProtectedSourceDrift'):M.protected(None,None)

    def test_long_names_are_fully_hashed_before_and_after_short_rename(self):
        path=M.SOURCE/'Library'/('a'*180)/('b'*100+'.bin')
        os.makedirs(M.extended(path.parent),exist_ok=True)
        with open(M.extended(path),'wb') as stream:stream.write(b'long path bytes preserved')
        before=M.inventory(M.SOURCE);result,_=self.execute()
        self.assertTrue(any(len(str(M.SOURCE/name))>=260 for name in before['files']))
        self.assertEqual(result['status'],'PASS_COMPLETED_FAILED_SMOKE97_PRESERVED_READY_FOR_FRESH_PREPARATION')
        self.assertEqual(M.inventory(M.DESTINATION),before)

    def test_fresh_ancestor_reparse_at_rename_is_rejected(self):
        with patch.object(M,'safe',side_effect=ValueError('SmokePreserve97LinkOrReparseRefused')):
            with self.assertRaisesRegex(ValueError,'LinkOrReparse'):M.paths_for_rename(M.SOURCE,M.DESTINATION)


if __name__=='__main__':unittest.main()
