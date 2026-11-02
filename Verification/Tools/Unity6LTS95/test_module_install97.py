"""Host-only installer receipt/state guards; no installer or native tools run."""
import copy
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import module_install97 as M


def module_record():
    info=M.download.component_info('android')
    value={'status':'PASS_COMPLETE_OFFICIAL_INSTALLER95','component':'android','trustedInstaller':True,
           'schemaVersion':2,'helperSHA256':M.COMPONENT_HELPER_SHA,'officialHelperSHA256':M.OFFICIAL_HELPER_SHA,
           'metadataSHA256':M.METADATA_SHA,'protectedSourcesUnchanged':True,'sectionCount':16,
           'maxAttemptsPerSection':16,'maxSeconds':5400,
           'installerExecuted':False,'url':info['url'],
           'installer':{'filename':info['filename'],'bytes':info['bytes'],'md5':info['md5'],
                        'sha256':'a'*64,'authenticode':{'Status':'Valid','SignerSubject':'CN=Unity Technologies SF'}},
           'normalInstallPlan':{'arguments':['/S','/D='+str(M.TARGET)]}}
    return value,info


def stock_record():
    binding={'path':'same','sha256':'a'*64,'bytes':123}
    record={'status':'PASS_NORMAL_STOCK_EDITOR_INSTALL95','runnerSHA256':'runner','target':str(M.TARGET),
            'installedEditor':binding,'editorProductVersion':M.EXACT_VERSION,'installerExecuted':True,
            'normalUacRequired':False,'mainInputsUnchanged':True,'candidate66InputsUnchanged':True,'unityPidsAfter':[],
            'launch':{'outcome':'Completed','exitCode':0,'ownedJobAssignedBeforeResume':True}}
    return record,binding


class ModuleControls(unittest.TestCase):
    def test_only_exact_matching_publisher_android_metadata_is_accepted(self):
        value,info=module_record();M.verify_download_record(value,info)
        self.assertEqual(info['bytes'],1549360256)
        self.assertEqual(info['md5'],'cfe45daf03586b1840752d62e0704b8b')
        self.assertIn('/672d562a42a7/',info['url'])

    def test_wrong_component_or_untrusted_incomplete_receipt_rejected(self):
        value,info=module_record()
        for key,change in [('component','editor'),('status','RUNNING'),('trustedInstaller',False),('installerExecuted',True),('url','https://untrusted.invalid/installer.exe')]:
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'VerifiedMatching'):
                M.verify_download_record({**value,key:change},info)

    def test_publisher_integrity_size_or_sha_change_rejected(self):
        value,info=module_record()
        for key,change in [('md5','0'*32),('bytes',1),('filename','other.exe'),('sha256','not-sha')]:
            bad=copy.deepcopy(value);bad['installer'][key]=change
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'VerifiedMatching'):
                M.verify_download_record(bad,info)

    def test_invalid_or_non_unity_signature_rejected(self):
        value,info=module_record()
        for signature in [{'Status':'NotSigned','SignerSubject':'Unity Technologies'},{'Status':'Valid','SignerSubject':'Different Company'}]:
            bad=copy.deepcopy(value);bad['installer']['authenticode']=signature
            with self.subTest(signature=signature),self.assertRaisesRegex(ValueError,'VerifiedMatching'):
                M.verify_download_record(bad,info)

    def test_download_plan_cannot_redirect_or_add_installer_switches(self):
        value,info=module_record()
        for args in [['/S','/D=E:/Other'],['/D='+str(M.TARGET),'/S'],['/S','/D='+str(M.TARGET),'/extra']]:
            bad=copy.deepcopy(value);bad['normalInstallPlan']['arguments']=args
            with self.subTest(args=args),self.assertRaisesRegex(ValueError,'VerifiedMatching'):
                M.verify_download_record(bad,info)

    def test_actual_publisher_recheck_cannot_be_replaced_by_a_valid_receipt(self):
        value,info=module_record()
        with tempfile.TemporaryDirectory() as temporary:
            evidence=Path(temporary)/'Evidence';private=Path(temporary)/'Private'
            receipt=evidence/'ComponentDownloads'/('a'*32)/'Report.json';receipt.parent.mkdir(parents=True);receipt.write_text('{}')
            executable=private/('a'*32)/info['filename'];executable.parent.mkdir(parents=True);executable.write_bytes(b'MZ changed')
            value['normalInstallPlan']['executable']=str(executable)
            guards=types.SimpleNamespace(reject_links=lambda path:None)
            with patch.object(M,'COMPONENT_PUBLIC',evidence/'ComponentDownloads'),patch.object(M,'COMPONENT_PRIVATE',private),patch.object(M.smoke,'read',return_value=value),patch.object(M.download,'verified_file',side_effect=ValueError('FullPublisherMismatch')) as actual,patch.object(M.stock,'launch_owned') as launch:
                with self.assertRaisesRegex(ValueError,'FullPublisherMismatch'):
                    M.verified_module(receipt,guards)
            actual.assert_called_once_with(executable.resolve(),info);launch.assert_not_called()

    def test_new_receipt_scope_rejects_old_official_root_nested_uuid_and_mismatched_private_run(self):
        value,info=module_record()
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);public=root/'ComponentDownloads';private=root/'Private'
            guards=types.SimpleNamespace(reject_links=lambda p:None)
            with patch.object(M,'COMPONENT_PUBLIC',public),patch.object(M,'COMPONENT_PRIVATE',private):
                for relative in ['OfficialDownloads/'+('a'*32)+'/Report.json','ComponentDownloads/Set01/Report.json',
                                 'ComponentDownloads/'+('a'*32)+'/nested/Report.json']:
                    path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{}')
                    with self.subTest(path=relative),self.assertRaisesRegex(ValueError,'ExactComponentDownloadUUID'):
                        M.verified_module(path,guards)
                path=public/('b'*32)/'Report.json';path.parent.mkdir(parents=True);path.write_text('{}')
                wrong=private/('c'*32)/info['filename'];wrong.parent.mkdir(parents=True);wrong.write_bytes(b'MZ changed')
                value['normalInstallPlan']['executable']=str(wrong)
                with patch.object(M.smoke,'read',return_value=value),patch.object(M.download,'verified_file') as verify:
                    with self.assertRaisesRegex(ValueError,'ExactIndependentOfficial'):
                        M.verified_module(path,guards)
                verify.assert_not_called()

    def test_new_download_proof_rejects_helper_drift_false_source_guard_and_unbounded_transfer(self):
        value,info=module_record()
        for key,change in [('schemaVersion',1),('helperSHA256','0'*64),('officialHelperSHA256','0'*64),
                           ('metadataSHA256','0'*64),('protectedSourcesUnchanged',False),('sectionCount',4),
                           ('maxAttemptsPerSection',100),('maxSeconds',5401),('maxSeconds',True)]:
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'FrozenComponentDownloadProof'):
                M.verify_download_record({**value,key:change},info)

    def test_actual_stock63_layout_requires_netcorerun_not_an_invented_dotnetsdk_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);editor=root/'Editor/Unity.exe';editor.parent.mkdir();editor.write_bytes(b'fixture')
            old=root/'Editor/Data/DotNetSdk/dotnet.exe';old.parent.mkdir(parents=True);old.write_bytes(b'wrong layout')
            files=M.stock_core.stock_paths(editor)
            self.assertEqual(files['netcorerun'],editor.parent/'Data/netcorerun/netcorerun.exe')
            self.assertNotIn('DotNetSdk',str(files['netcorerun']))
            with self.assertRaisesRegex(ValueError,'CompleteInstalledCore'):
                M.stock_core.validate_runtime(files)

    def test_core_snapshot_retains_all790_frozen_files_and_unity_dll(self):
        with tempfile.TemporaryDirectory() as temporary:
            editor=Path(temporary)/'Editor/Unity.exe';editor.parent.mkdir();editor.write_bytes(b'editor')
            unity=editor.parent/'Unity.dll';unity.write_bytes(b'unity')
            files=M.stock_core.stock_paths(editor)
            snapshot={str(index):{'fixture':index} for index in range(790)}
            baseline={'stockCoreFilesBefore':snapshot,'stockCoreFilesAfter':snapshot}
            guards=types.SimpleNamespace(reject_links=lambda p:None)
            actual_sha=M.core.sha
            def digest(path):
                path=Path(path)
                if path==Path(M.stock_core.__file__):return M.CORE_READER_SHA
                if path==M.CORE_BASELINE:return M.CORE_BASELINE_SHA
                return actual_sha(path)
            with patch.object(M.smoke,'EDITOR',editor),patch.object(M.core,'sha',side_effect=digest), \
                 patch.object(M.stock_core,'validate_runtime') as runtime,patch.object(M.stock_core,'core_snapshot',return_value=copy.deepcopy(snapshot)), \
                 patch.object(M.smoke,'read',return_value=baseline):
                result=M.protected_core(guards)
            runtime.assert_called_once_with(files)
            self.assertEqual(len(result),791)
            self.assertEqual(result['Unity.dll']['sha256'],actual_sha(unity))
            self.assertEqual({k:v for k,v in result.items() if k!='Unity.dll'},snapshot)

    def test_core_snapshot_rejects_missing_or_changed_file_even_when_top_level_pins_pass(self):
        with patch.object(M.core,'sha',side_effect=lambda p:M.CORE_READER_SHA if Path(p)==Path(M.stock_core.__file__) else M.CORE_BASELINE_SHA), \
             patch.object(M.stock_core,'validate_runtime'),patch.object(M.stock_core,'core_snapshot',return_value={'one':{}}), \
             patch.object(M.smoke,'read',return_value={'stockCoreFilesBefore':{},'stockCoreFilesAfter':{}}):
            guards=types.SimpleNamespace(reject_links=lambda p:None)
            with self.assertRaisesRegex(ValueError,'Actual790StockCoreFilesChanged'):
                M.protected_core(guards)

    def test_platform_payload_uses_verified_stock63_shared_runtime_without_invented_local_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);editor=root/'Editor/Unity.exe';editor.parent.mkdir();editor.write_bytes(b'editor')
            android=editor.parent/'Data/PlaybackEngines/AndroidPlayer'
            files=['UnityEditor.Android.Extensions.dll','Unity.Android.Gradle.dll','modules.asset',
                   'AndroidPlayerBuildProgram.exe','AndroidPlayerBuildProgram.Data.dll',
                   'Variations/il2cpp/Release/Libs/arm64-v8a/libunity.so',
                   'Variations/il2cpp/Release/Libs/arm64-v8a/libmain.so',
                   'Variations/il2cpp/Development/Libs/arm64-v8a/libunity.so']
            header=bytearray(20);header[:6]=b'\x7fELF\x02\x01';header[18:20]=(183).to_bytes(2,'little')
            for relative in files:
                path=android/relative;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(header if path.suffix=='.so' else b'fixture')
            (android/'Tools/gradle').mkdir(parents=True)
            runtime=M.stock_core.stock_paths(editor)['runtimeconfig'];runtime.parent.mkdir(parents=True)
            runtime.write_text('{"runtimeOptions":{"tfm":"net6.0"}}')
            guards=types.SimpleNamespace(reject_links=lambda p:None)
            with patch.object(M,'ANDROID',android),patch.object(M.smoke,'EDITOR',editor), \
                 patch.object(M.stock_core,'validate_runtime',return_value={'tfm':'net6.0'}) as validate:
                result=M.installed_android(guards)
            validate.assert_called_once_with(M.stock_core.stock_paths(editor))
            self.assertEqual(result['fileCount'],8)
            self.assertEqual(result['runtimeOptionsSource'],M.smoke.binding(runtime))
            self.assertFalse(result['sdkChildrenVerified'])
            self.assertFalse((android/'AndroidPlayerBuildProgram.runtimeconfig.json').exists())
            self.assertEqual(set(result['files']),set(files))

    def test_stock_editor_binding_and_exact_version_required(self):
        value,binding=stock_record();M.verify_stock_record(value,binding,M.EXACT_VERSION,'runner')
        for version in ['6000.6.6f1','6000.3.27f1_other','6000.3.27f1_672d562a42a7-extra']:
            with self.subTest(version=version),self.assertRaisesRegex(ValueError,'CurrentVerified'):
                M.verify_stock_record(value,binding,version,'runner')

    def test_stock_editor_failed_partial_or_modified_inputs_rejected(self):
        value,binding=stock_record()
        for key,change in [('status','FAIL'),('runnerSHA256','changed'),('target','E:/wrong'),('installedEditor',{}),('installerExecuted',False),('normalUacRequired',True),('mainInputsUnchanged',False),('candidate66InputsUnchanged',False),('unityPidsAfter',[123])]:
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'CurrentVerified'):
                M.verify_stock_record({**value,key:change},binding,M.EXACT_VERSION,'runner')

    def test_unowned_timeout_or_nonzero_editor_install_receipt_rejected(self):
        value,binding=stock_record()
        for key,change in [('outcome','TimedOut'),('exitCode',1),('ownedJobAssignedBeforeResume',False)]:
            bad=copy.deepcopy(value);bad['launch'][key]=change
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'CurrentVerified'):
                M.verify_stock_record(bad,binding,M.EXACT_VERSION,'runner')

    def test_target_is_editor_root_unquoted_destination_last(self):
        command=M.installer_command('C:/fixture path/module.exe')
        self.assertEqual(command,[str(Path('C:/fixture path/module.exe')),'/S','/D='+str(M.TARGET)])
        self.assertNotIn('"',command[-1]);self.assertNotIn('AndroidPlayer',command[-1])

    def test_wrong_target_refused_before_normal_installer(self):
        with patch.object(M,'TARGET',Path('E:/Other')):
            with self.assertRaisesRegex(ValueError,'ExactUnquoted'):M.installer_command('module.exe')

    def test_existing_partial_android_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory);android=target/'AndroidPlayer';android.mkdir()
            existing=android/'partial.txt';existing.write_bytes(b'keep')
            process=types.SimpleNamespace(unity_pids=lambda:[])
            guards=types.SimpleNamespace(reject_links=lambda p:None)
            with patch.object(M,'TARGET',target),patch.object(M,'ANDROID',android),patch.object(M.smoke,'readers',return_value=(None,None,process,None,guards)),patch.object(M.smoke,'contained_output',return_value=target/'out'),patch.object(M,'verified_module',side_effect=AssertionError('must not verify or install')):
                with self.assertRaisesRegex(ValueError,'ExistingOrPartial'):
                    M.install(target/'module.json',target/'editor.json',target/'out',60)
            self.assertEqual(existing.read_bytes(),b'keep')

    def test_running_editor_fences_install(self):
        readers=(None,None,types.SimpleNamespace(unity_pids=lambda:[42]),None,None)
        with patch.object(M.smoke,'readers',return_value=readers),patch.object(M.stock,'launch_owned') as launch:
            with self.assertRaisesRegex(ValueError,'NoRunningEditor'):M.install(Path('m'),Path('e'),Path('o'),60)
        launch.assert_not_called()

    def test_bad_timeout_refused_before_readers_or_process(self):
        with patch.object(M.smoke,'readers',side_effect=AssertionError('must not call')):
            for timeout in (0,59,3601,True):
                with self.subTest(timeout=timeout),self.assertRaisesRegex(ValueError,'BoundedInstaller'):
                    M.install(Path('m'),Path('e'),Path('o'),timeout)

    def test_arm64_static_header_accepts_only_correct_elf_architecture(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'libunity.so';header=bytearray(20);header[:6]=b'\x7fELF\x02\x01';header[18:20]=(183).to_bytes(2,'little')
            path.write_bytes(header);M.arm64_elf(path)
            for index,value in [(0,0),(4,1),(5,2),(18,62)]:
                wrong=header.copy();wrong[index]=value;path.write_bytes(wrong)
                with self.subTest(index=index),self.assertRaisesRegex(ValueError,'ActualARM64'):M.arm64_elf(path)

    def test_launcher_reuses_frozen_owned_uac_aware_stock_helper(self):
        # Existing stock helper is independently covered by its six host tests.
        text=Path(M.__file__).read_text('utf-8')
        self.assertIn('stock.launch_owned(command,output,timeout,api,jobs)',text)
        self.assertNotIn('subprocess.Popen(',text)
        self.assertNotIn('ShellExecute',text)
        self.assertNotIn('__COMPAT_LAYER',text)
        self.assertNotIn('rmtree(',text)
        self.assertNotIn('RunAsInvoker',text)
        self.assertIn('REQUIRES_NORMAL_UAC_STOCK_ANDROID_MODULE_INSTALL95',text)


if __name__=='__main__':unittest.main(verbosity=2)
