"""Host-only stock-loader guards; no dotnet/Editor/SDK/native command is executed."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import core_loader95 as loader


class CoreLoaderHostTests(unittest.TestCase):
    def test_actual_application_control_error_classifies_block_and_component(self):
        result=loader.classify('',"System.IO.FileLoadException Bee.VisualStudioSolution.dll blocked (0x800711C7)",1,Path('absent-host.json'))
        self.assertEqual(result['classification'],'BLOCK_APPLICATION_CONTROL_0x800711C7');self.assertTrue(result['beeVisualStudioSolutionNamed'])

    def test_other_loader_failures_are_not_relabelled_as_sac(self):
        result=loader.classify('','System.IO.FileLoadException: unrelated error (0x80070002)',1,Path('absent-host.json'))
        self.assertEqual(result['classification'],'UNKNOWN_RESULT')

    def test_exact_absent_input_failure_is_diagnostic_not_android_acceptance(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_core_input_host_') as folder:
            path=Path(folder)/'IntentionallyAbsent_Input.json'
            result=loader.classify('',"System.IO.FileNotFoundException: Could not find file '"+str(path.resolve())+"'.",1,path)
            self.assertEqual(result['classification'],'LOADER_REACHED_DELIBERATE_INPUT_FAILURE')
            self.assertIn('NOT_ANDROID_ACCEPTANCE',result['status'])

    def test_wrong_input_dag_or_existing_input_never_counts_as_loader_reached(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_core_wrong_host_') as folder:
            path=Path(folder)/'IntentionallyAbsent_Input.json'
            for other in ('Different.json','IntentionallyAbsent_DAG.json'):
                result=loader.classify('',"System.IO.FileNotFoundException: Could not find file '"+str(path.parent/other)+"'.",1,path)
                self.assertEqual(result['classification'],'UNKNOWN_RESULT')
            path.write_bytes(b'not-absent')
            result=loader.classify('',"System.IO.FileNotFoundException: Could not find file '"+str(path)+"'.",1,path)
            self.assertEqual(result['classification'],'UNKNOWN_RESULT')

    def test_echoed_intended_path_with_unrelated_missing_assembly_is_unknown(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_core_echo_host_') as folder:
            path=Path(folder)/'IntentionallyAbsent_Input.json'
            stdout='Arguments: '+str(path.resolve())
            for exception in ("System.IO.FileNotFoundException: Could not load file or assembly 'Missing.Dependency'.",
                              "System.IO.FileNotFoundException: Could not find file '"+str(path.parent/'Other.json')+"'."):
                with self.subTest(exception=exception):
                    self.assertEqual(loader.classify(stdout,exception,1,path)['classification'],'UNKNOWN_RESULT')

    def test_one_real_missing_input_plus_other_missing_file_is_not_accepted(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_core_multi_error_host_') as folder:
            path=Path(folder)/'IntentionallyAbsent_Input.json'
            message="System.IO.FileNotFoundException: Could not find file '"+str(path)+"'.\nSystem.IO.FileNotFoundException: Could not find file '"+str(path.parent/'Other.json')+"'."
            self.assertEqual(loader.classify('',message,1,path)['classification'],'UNKNOWN_RESULT')

    def test_nested_type_load_error_and_zero_exit_do_not_waive_failure(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_core_nested_host_') as folder:
            path=Path(folder)/'IntentionallyAbsent_Input.json';message="System.IO.FileNotFoundException: Could not find file '"+str(path)+"'."
            self.assertEqual(loader.classify('','ReflectionTypeLoadException\n'+message,1,path)['classification'],'UNKNOWN_RESULT')
            self.assertEqual(loader.classify('',message,0,path)['classification'],'UNKNOWN_RESULT')

    def test_timeout_is_unknown_even_with_partial_exception_output(self):
        self.assertEqual(loader.classify('','0x800711C7',-1,Path('absent.json'),True)['classification'],'UNKNOWN_TIMEOUT')

    def test_stock_command_uses_only_matching_frontend_resolvers_and_fresh_absent_inputs(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_core_command_host_') as folder:
            root=Path(folder);files={'dotnet':root/'Data/DotNetSdk/dotnet.exe','frontend':root/'Data/PlaybackEngines/windowsstandalonesupport/WinPlayerBuildProgram.exe',
                                     'playerLibrary':root/'Data/Tools/BuildPipeline/PlayerBuildProgramLibrary.dll'}
            output=root/'Evidence';output.mkdir();command=loader.command_for(files,output)
            self.assertEqual(len(command),6);self.assertTrue(command[2].endswith('windowsstandalonesupport\\Bee;'+str(files['playerLibrary'].parent)))
            self.assertEqual(command[3:], [str(output/name) for name in ('IntentionallyAbsent_DAG.json','IntentionallyAbsent_Input.json','Frontend.traceevents')])
            self.assertNotIn('-projectPath',command)
            (output/'IntentionallyAbsent_Input.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'DeliberatelyAbsentInputsRequired'):loader.command_for(files,output)

    def test_verified_installer_receipt_rejects_failed_untrusted_or_wrong_publisher(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_core_installer_host_') as folder:
            root=Path(folder);path=root/'OfficialDownloads/Set01/Report.json';path.parent.mkdir(parents=True)
            info={'filename':'Editor.exe','bytes':3,'md5':'f'*32}
            for changes in ({'status':'FAIL_DOWNLOAD'}, {'trustedInstaller':False},{'installer':{'authenticode':{'Status':'Invalid'}}}):
                base={'status':'PASS_COMPLETE_OFFICIAL_INSTALLER95','component':'editor','trustedInstaller':True,'installer':{'filename':'Editor.exe','bytes':3,'md5':'f'*32,'authenticode':{'Status':'Valid','SignerSubject':'Unity Technologies'}}}
                path.write_text(json.dumps({**base,**changes}))
                with patch.object(loader,'EVIDENCE',root),patch.object(loader.official_download95,'component_info',return_value=info),self.assertRaisesRegex(ValueError,'VerifiedPublisherEditorRequired'):
                    loader.verified_editor_installer(path)

    def test_changed_complete_installer_sha_is_refused_without_running_it(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_core_hash_host_') as folder:
            root=Path(folder);path=root/'OfficialDownloads/Set01/Report.json';path.parent.mkdir(parents=True);private=root/'Private';private.mkdir();installer=private/'Editor.exe';installer.write_bytes(b'abc')
            target=Path('E:/HeartRainUnity6LTS95/6000.3.27f1');info={'filename':'Editor.exe','bytes':3,'md5':'f'*32}
            report={'status':'PASS_COMPLETE_OFFICIAL_INSTALLER95','component':'editor','trustedInstaller':True,'installer':{**info,'sha256':hashlib.sha256(b'abc').hexdigest(),'authenticode':{'Status':'Valid','SignerSubject':'Unity Technologies'}},'normalInstallPlan':{'executable':str(installer),'arguments':['/S','/D='+str(target)]}}
            path.write_text(json.dumps(report))
            with patch.object(loader,'EVIDENCE',root),patch.object(loader.official_download95,'component_info',return_value=info),patch.object(loader.official_download95,'PRIVATE',private),patch.object(loader.official_download95,'TARGET',target):
                loader.verified_editor_installer(path)
                installer.write_bytes(b'abd')
                with self.assertRaisesRegex(ValueError,'VerifiedInstallerBytesChanged'):loader.verified_editor_installer(path)

    def test_code_has_fixed_owned_timeout_without_custom_assembly_compile_or_project_entry(self):
        text=Path(loader.__file__).read_text('utf-8-sig')
        self.assertIn('process.wait(timeout=60)',text);self.assertIn('job.assign(process.pid);jobs.resume_owned_primary(process)',text)
        self.assertIn('subprocess.CREATE_NO_WINDOW|0x4',text);self.assertIn('coreFilesUnchanged',text)
        self.assertNotIn('-projectPath',text);self.assertNotIn('-executeMethod',text)
        self.assertNotIn('Add-Type',text);self.assertNotIn('Assembly.Load',text);self.assertNotIn('EditorPrefs',text)


if __name__=='__main__':unittest.main(verbosity=2)
