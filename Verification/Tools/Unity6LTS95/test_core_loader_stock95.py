"""Host-only stock netcorerun guards; never invoke a vendor executable."""
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import core_loader_stock95 as loader


class StockLoaderTests(unittest.TestCase):
    def fake_runtime(self,root):
        files=loader.stock_paths(root/'Editor/Unity.exe')
        for key,path in files.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(key.encode())
        files['runtimeconfig'].write_text(json.dumps({'runtimeOptions':{'tfm':'net6.0','includedFrameworks':[{'name':'Microsoft.NETCore.App','version':'6.0.21'}]}}))
        files['deps'].write_text(json.dumps({'runtimeTarget':{'name':'.NETCoreApp,Version=v6.0/win-x64'},'libraries':{'runtimepack.Microsoft.NETCore.App.Runtime.win-x64/6.0.21':{}}}))
        return files,{key:loader.frozen.sha(files[key]) for key in loader.PINS}

    def fake_install(self,root):
        editor=root/'Editor/Unity.exe';editor.parent.mkdir();editor.write_bytes(b'host-editor-fixture')
        receipt=root/'Installation/Set02/Report.json';receipt.parent.mkdir(parents=True)
        official={'receipt':{'path':str(root/'official.json')},'installer':{'sha256':'a'*64}}
        value={'status':'PASS_NORMAL_STOCK_EDITOR_INSTALL95','installerExecuted':True,'target':str(editor.parent.parent),
               'editorProductVersion':loader.VERSION,'launch':{'exitCode':0,'ownedJobAssignedBeforeResume':True},
               'installedEditor':loader.frozen.bound(editor),'verifiedInstaller':official}
        receipt.write_text(json.dumps(value));return editor,receipt,value,official

    def test_layout_is_actual_stock_netcorerun_not_mono_or_dotnetsdk(self):
        paths=loader.stock_paths(Path('E:/host95/Editor/Unity.exe'))
        self.assertEqual(paths['netcorerun'].name,'netcorerun.exe')
        self.assertEqual(paths['runtimeconfig'].parent,paths['netcorerun'].parent)
        self.assertEqual(paths['corelib'].parent,paths['netcorerun'].parent)
        self.assertFalse(any('MonoBleedingEdge' in str(path) or 'DotNetSdk' in str(path) for path in paths.values()))

    def test_command_uses_stock_host_frontend_resolvers_and_absent_input_order(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);paths=loader.stock_paths(root/'Editor/Unity.exe');out=root/'out';out.mkdir()
            command=loader.command_for(paths,out)
            self.assertEqual(command[:3],[str(paths['netcorerun']),str(paths['frontend']),str(paths['frontend'].parent/'Bee')+';'+str(paths['playerLibrary'].parent)])
            self.assertEqual(command[3:],[str(out/name) for name in ('IntentionallyAbsent_DAG.json','IntentionallyAbsent_Input.json','Frontend.traceevents')])
            self.assertNotIn('-projectPath',command);self.assertNotIn('-executeMethod',command)

    def test_existing_input_or_dag_refuses_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);paths=loader.stock_paths(root/'Editor/Unity.exe');out=root/'out';out.mkdir()
            for name in ('IntentionallyAbsent_DAG.json','IntentionallyAbsent_Input.json'):
                path=out/name;path.write_text('{}')
                with self.assertRaisesRegex(ValueError,'DeliberatelyAbsentInputsRequired'):loader.command_for(paths,out)
                path.unlink()

    def test_exact_self_contained_runtime_and_all_pins_are_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            files,pins=self.fake_runtime(Path(folder))
            with patch.object(loader,'PINS',pins):self.assertEqual(loader.validate_runtime(files)['tfm'],'net6.0')

    def test_framework_or_runtime_dependency_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            files,pins=self.fake_runtime(Path(folder))
            with patch.object(loader,'PINS',pins):
                original=files['runtimeconfig'].read_bytes();files['runtimeconfig'].write_text('{"runtimeOptions":{"tfm":"net8.0"}}')
                with self.assertRaisesRegex(ValueError,'ExactBundledNetCoreRunRuntimeRequired'):loader.validate_runtime(files)
                files['runtimeconfig'].write_bytes(original);files['deps'].write_text('{"runtimeTarget":{"name":"other"}}')
                with self.assertRaisesRegex(ValueError,'MatchingRuntimeDependencyManifestRequired'):loader.validate_runtime(files)

    def test_stock_dll_replacement_and_missing_core_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            files,pins=self.fake_runtime(Path(folder))
            with patch.object(loader,'PINS',pins):
                files['beeVisualStudioSolution'].write_bytes(b'replaced')
                with self.assertRaisesRegex(ValueError,'InstalledCorePinChanged:beeVisualStudioSolution'):loader.validate_runtime(files)
                files['corelib'].unlink()
                with self.assertRaisesRegex(ValueError,'CompleteInstalledCoreRequired'):loader.validate_runtime(files)

    def test_completed_installation_is_hash_bound_and_failed_receipts_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);editor,receipt,value,official=self.fake_install(root)
            with patch.object(loader,'EDITOR',editor),patch.object(loader,'INSTALL',receipt),patch.object(loader,'INSTALL_SHA',loader.frozen.sha(receipt)),patch.object(loader.frozen,'verified_editor_installer',return_value=official):
                self.assertIn('receipt',loader.validate_installation(receipt))
                receipt.write_text(json.dumps({**value,'status':'FAIL_NORMAL_STOCK_EDITOR_INSTALL95'}))
                with self.assertRaisesRegex(ValueError,'ExactCompletedInstallationReceiptRequired'):loader.validate_installation(receipt)
                with patch.object(loader,'INSTALL_SHA',loader.frozen.sha(receipt)),self.assertRaisesRegex(ValueError,'SuccessfulNormalStockInstallationRequired'):
                    loader.validate_installation(receipt)

    def test_installation_chain_changed_editor_or_publisher_receipt_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);editor,receipt,_,official=self.fake_install(root)
            with patch.object(loader,'EDITOR',editor),patch.object(loader,'INSTALL',receipt),patch.object(loader,'INSTALL_SHA',loader.frozen.sha(receipt)):
                with patch.object(loader.frozen,'verified_editor_installer',return_value={**official,'other':True}),self.assertRaisesRegex(ValueError,'VerifiedInstallerChainChanged'):
                    loader.validate_installation(receipt)
                editor.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'InstalledEditorChanged'):loader.validate_installation(receipt)

    def test_official_environment_preserves_base_and_refuses_injected_runtime(self):
        base={'PATH':'host-path','TASK_VALUE':'keep'};result=loader.environment_for(Path('unused'),base)
        self.assertEqual(result,{**base,'DOTNET_SYSTEM_GLOBALIZATION_INVARIANT':'1'});self.assertNotIn('DOTNET_SYSTEM_GLOBALIZATION_INVARIANT',base)
        for key in ('DOTNET_STARTUP_HOOKS','CORECLR_ENABLE_PROFILING','COR_PROFILER','DOTNET_ADDITIONAL_DEPS'):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'NoInjectedRuntimeHooksRequired'):loader.environment_for(Path('unused'),{key:'injected'})

    def test_actual_application_control_error_is_block_and_timeout_is_unknown(self):
        blocked=loader.frozen.classify('',"FileLoadException: Bee.VisualStudioSolution.dll 0x800711C7",1,Path('absent95.json'))
        self.assertEqual(blocked['classification'],'BLOCK_APPLICATION_CONTROL_0x800711C7');self.assertTrue(blocked['beeVisualStudioSolutionNamed'])
        self.assertEqual(loader.frozen.classify('','0x800711C7',-1,Path('absent95.json'),True)['classification'],'UNKNOWN_TIMEOUT')

    def test_only_actual_intended_missing_input_counts_as_loader_reached(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'IntentionallyAbsent_Input.json';message="System.IO.FileNotFoundException: Could not find file '"+str(path)+"'."
            self.assertEqual(loader.frozen.classify('',message,1,path)['classification'],'LOADER_REACHED_DELIBERATE_INPUT_FAILURE')
            wrong="System.IO.FileNotFoundException: Could not load file or assembly 'Other'."
            self.assertEqual(loader.frozen.classify(str(path),wrong,1,path)['classification'],'UNKNOWN_RESULT')
            self.assertEqual(loader.frozen.classify('',message+'\n'+wrong,1,path)['classification'],'UNKNOWN_RESULT')

    def test_owned_suspended_launch_and_exclusive_final_receipt_without_native_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'CoreLoaderStock/Set01';receipt=root/'install.json';receipt.write_text('{}');events=[]
            files=loader.stock_paths(root/'Editor/Unity.exe');main={'files':{'main':'same'}};candidate={'files':{'candidate':'same'}}
            def write(path,value):
                with path.open('x',encoding='utf-8') as stream:json.dump(value,stream)
            class Job:
                def assign(self,pid):events.append(('assign',pid))
                def close(self):events.append(('close',))
            api=types.SimpleNamespace(utc=lambda:'host-test',write=write,OwnedJob=Job,freeze=lambda:main)
            processes=types.SimpleNamespace(unity_pids=lambda:[]);jobs=types.SimpleNamespace(resume_owned_primary=lambda process:events.append(('resume',process.pid)))
            guards=types.SimpleNamespace(reject_links=lambda path:None)
            def popen(command,**kwargs):
                events.append(('popen',kwargs['creationflags']));kwargs['stderr'].write(("System.IO.FileNotFoundException: Could not find file '"+str(out/'IntentionallyAbsent_Input.json')+"'.").encode())
                return types.SimpleNamespace(pid=95,returncode=1,wait=lambda timeout:events.append(('wait',timeout)),poll=lambda:1)
            with patch.object(loader,'ROOT',root),patch.object(loader,'INSTALL',receipt),patch.object(loader,'INSTALL_SHA',loader.frozen.sha(receipt)),\
                 patch.object(loader.smoke95,'readers',return_value=(api,types.SimpleNamespace(candidate_sources=lambda api:candidate),processes,jobs,guards)),\
                 patch.object(loader.smoke95,'contained_output',return_value=out),patch.object(loader,'validate_installation',return_value={}),\
                 patch.object(loader.frozen,'editor_product_version',return_value=loader.VERSION),patch.object(loader,'validate_runtime',return_value={}),\
                 patch.object(loader,'core_snapshot',return_value={'stock':'same'}),patch.object(loader.smoke95,'protected_sources',return_value=(main,candidate)),\
                 patch.object(loader.subprocess,'Popen',side_effect=popen),patch.dict(loader.os.environ,{},clear=True):
                self.assertEqual(loader.diagnose(receipt,out),0)
            self.assertEqual([event[0] for event in events[:4]],['popen','assign','resume','wait'])
            self.assertTrue(events[0][1]&0x4);self.assertEqual(events[3],('wait',60))
            report=json.loads((out/'Report.json').read_text());self.assertTrue(report['stockCoreUnchanged']);self.assertTrue(report['mainInputsUnchanged'])
            self.assertTrue(report['candidate66InputsUnchanged']);self.assertIn('NOT_ANDROID_ACCEPTANCE',report['status'])
            self.assertEqual(len(list(out.glob('Report.json'))),1)


if __name__=='__main__':unittest.main(verbosity=2)
