"""Host-only temporary-directory recovery guards; no PID/registry/native calls."""
from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).parent))
SPEC=importlib.util.spec_from_file_location('recover_smoke97_host',Path(__file__).with_name('recover_smoke97.py'))
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


class RecoveryControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.stack=ExitStack();self.addCleanup(self.stack.close)
        private=self.root/'private';source=private/'Smoke';old=self.root/'evidence/SmokeRuns'/M.OLD_ID
        prep=self.root/'evidence/SmokePreparation/Set01/Preparation.json'
        for module,key,value in [(M,'ROOT',self.root),(M.smoke,'ROOT',self.root),(M.smoke,'PRIVATE',private),
            (M.smoke,'PROJECT',source),(M,'SOURCE',source),(M,'DESTINATION',private/'SmokeFailed97'/M.OLD_ID),
            (M,'OLD',old),(M,'PREPARED',prep),(M,'PUBLIC',self.root/'evidence/SmokeRecovery97'),
            (M.smoke,'EDITOR',self.root/'editor/Unity.exe'),(M.smoke,'TEMPLATE',self.root/'template.cs'),
            (M.smoke,'__file__',str(self.root/'smoke95.py')),(M,'__file__',str(self.root/'recover97.py'))]:
            self.stack.enter_context(patch.object(module,key,value))
        for path in (M.smoke.EDITOR,M.smoke.TEMPLATE,Path(M.smoke.__file__),Path(M.__file__)):
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
        self.manifest={}
        for relative,raw in [('Assets/Editor/ToolchainSmoke95.cs',b'fixture'),('Assets/Editor/ToolchainSmoke95.cs.meta',b'fixture meta'),
                             ('Packages/manifest.json',b'{}'),('ProjectSettings/ProjectVersion.txt',b'm_EditorVersion: 6000.3.27f1\nm_EditorVersionWithRevision: 6000.3.27f1 (672d562a42a7)\n')]:
            path=source/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            self.manifest[relative]={'sha256':M.smoke.sha(path),'bytes':path.stat().st_size}
        cache=source/'Library/cache.bin';cache.parent.mkdir();cache.write_bytes(b'preserve generated cache')
        proof={'status':'PASS_FRESH_MINIMAL_LTS95_SMOKE_PREPARATION','project':source.relative_to(self.root).as_posix(),
               'version':M.smoke.VERSION,'templateSHA256':M.smoke.sha(M.smoke.TEMPLATE),'inputManifest':{'files':self.manifest}}
        self.write(prep,proof)
        auth={'status':'RUNNING_ACTUAL_LTS95_TOOLCHAIN_SMOKE','runnerSHA256':M.smoke.sha(Path(M.smoke.__file__)),
              'preparation':M.smoke.binding(prep),'editor':M.smoke.binding(M.smoke.EDITOR),
              'command':[str(M.smoke.EDITOR),'-batchmode','-nographics','-buildTarget','Android','-projectPath',str(source),
                         '-executeMethod',M.smoke.ENTRY,'-logFile',str(old/'Unity.log')]}
        for name in M.OLD_FILES:self.write(old/name,auth if name=='Authorization.json' else {'fixture':name})
        self.stack.enter_context(patch.object(M,'AUTH_SHA',M.download.digest(old/'Authorization.json')))
        self.stack.enter_context(patch.object(M,'PREP_SHA',M.download.digest(prep)))
        self.processes=SimpleNamespace(unity_pids=Mock(return_value=[]))
        self.writer=SimpleNamespace(write=self.write,utc=lambda:'2026-10-27T14:00:00Z')
        self.output=M.PUBLIC/('a'*32)

    @staticmethod
    def write(path,value):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x',encoding='utf-8') as stream:json.dump(value,stream)

    def execute(self,**kwargs):
        with patch.object(M.smoke,'readers',return_value=(self.writer,None,self.processes,None,None)), \
             patch.object(M.download,'stopped_pid') as stopped,patch.object(M,'protected',return_value=('main','candidate')):
            value=M.recover(self.output)
        return value,stopped

    def test_atomic_preservation_retains_every_project_byte_and_old_receipt_without_fake_fail(self):
        before=M.tree_inventory(M.SOURCE);old=M.old_inventory()
        value,stopped=self.execute()
        self.assertEqual(value['status'],'PRESERVED_INCOMPLETE_INTERRUPTED_SMOKE97_READY_FOR_FRESH_PREPARATION')
        self.assertFalse(M.SOURCE.exists());self.assertEqual(M.tree_inventory(M.DESTINATION),before)
        self.assertEqual(M.old_inventory(),old);self.assertFalse((M.OLD/'Invocation.json').exists())
        self.assertFalse((M.OLD/'Native.json').exists());self.assertFalse(value['oldFailureOrFinalResultFabricated'])
        self.assertFalse(value['processStopOrKillExecuted']);self.assertEqual(value['interruptionCause'],'UNPROVEN')
        self.assertEqual({call.args[0] for call in stopped.call_args_list},set(M.OBSERVED_PIDS.values()))
        self.assertEqual(M.smoke.read(self.output/'InterruptedAttempt.json')['status'],'INCOMPLETE_INTERRUPTED_LTS95_SMOKE_OBSERVED97')

    def test_existing_preserved_destination_and_wrong_source_are_refused(self):
        M.DESTINATION.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError,'FreshFixedPrivateDestination'):M.checked_paths(self.output)
        with patch.object(M,'SOURCE',self.root/'vendor'):
            with self.assertRaisesRegex(ValueError,'ExactOwnedSmoke'):M.checked_paths(self.output)

    def test_wrong_public_path_or_repeat_receipt_cannot_overwrite_evidence(self):
        with self.assertRaisesRegex(ValueError,'FreshReceiptUUID'):M.checked_paths(self.root/'outside'/('a'*32))
        self.output.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError,'FreshReceiptUUID'):M.checked_paths(self.output)

    def test_reparse_and_symlink_paths_are_refused(self):
        with patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaisesRegex(ValueError,'ReparsePoint'):M.no_links(M.SOURCE)
        with patch.object(Path,'stat',return_value=SimpleNamespace(st_file_attributes=0x400,st_mode=0o40755)):
            with self.assertRaisesRegex(ValueError,'ReparsePoint'):M.no_links(M.SOURCE)

    def test_running_editor_or_observed_pid_prevents_any_move(self):
        self.processes.unity_pids.return_value=[999]
        with patch.object(M.download,'stopped_pid') as stopped:
            with self.assertRaisesRegex(ValueError,'NoRunningEditor'):M.idle(self.processes)
        stopped.assert_not_called()
        self.processes.unity_pids.return_value=[]
        with patch.object(M.download,'stopped_pid',side_effect=ValueError('FixturePIDStillRunning')):
            with self.assertRaisesRegex(ValueError,'FixturePIDStillRunning'):M.idle(self.processes)
        self.assertTrue(M.SOURCE.exists());self.assertFalse(M.DESTINATION.exists())

    def test_final_receipt_appearance_refuses_interrupted_classification(self):
        self.write(M.OLD/'Invocation.json',{'status':'PASS_OR_FAIL_DO_NOT_REWRITE'})
        with self.assertRaisesRegex(ValueError,'MissingFinalReceiptRequired'):M.old_inventory()

    def test_prepared_template_or_generated_version_drift_is_refused(self):
        (M.SOURCE/'Assets/Editor/ToolchainSmoke95.cs').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'OwnedPreparedInputChanged'):M.ownership(M.SOURCE)
        (M.SOURCE/'Assets/Editor/ToolchainSmoke95.cs').write_bytes(b'fixture')
        (M.SOURCE/'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 6000.6.6f1')
        with self.assertRaisesRegex(ValueError,'ExactGeneratedLTSVersion'):M.ownership(M.SOURCE)

    def test_old_log_change_during_preflight_prevents_move(self):
        original=M.old_inventory;counter=[0]
        def changing():
            counter[0]+=1
            result=original()
            if counter[0]>=2:result['Unity.log']['sha256']='0'*64
            return result
        with patch.object(M.smoke,'readers',return_value=(self.writer,None,self.processes,None,None)), \
             patch.object(M.download,'stopped_pid'),patch.object(M,'protected',return_value=('main','candidate')), \
             patch.object(M,'old_inventory',side_effect=changing):
            with self.assertRaisesRegex(ValueError,'AttemptStillChanging'):M.recover(self.output)
        self.assertTrue(M.SOURCE.exists());self.assertFalse(M.DESTINATION.exists())


if __name__=='__main__':unittest.main()
