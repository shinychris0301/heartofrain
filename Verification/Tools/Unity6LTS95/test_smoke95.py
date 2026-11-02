"""Host-only smoke guards. No Editor, SDK command, real APK build or device action."""
from pathlib import Path
import re
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

import smoke95 as smoke


class SmokeHostTests(unittest.TestCase):
    def test_only_fresh_contained_evidence_children_are_allowed(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_fresh_host_') as folder:
            root=Path(folder)
            with patch.object(smoke,'EVIDENCE',root):
                self.assertEqual(smoke.contained_output(root/'SmokePreparation/Set01','SmokePreparation'),(root/'SmokePreparation/Set01').resolve())
                for path in (root/'Other',root/'SmokePreparation'):
                    with self.assertRaises(ValueError):smoke.contained_output(path,'SmokePreparation')
                old=root/'SmokePreparation/Old';old.mkdir(parents=True)
                with self.assertRaises(ValueError):smoke.contained_output(old,'SmokePreparation')

    def test_marker_gate_rejects_other_editor_or_missing_embedded_children(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_tools_host_') as folder:
            editor=Path(folder)/'Editor/Unity.exe';editor.parent.mkdir();editor.write_bytes(b'host-fixture')
            with self.assertRaisesRegex(ValueError,'ExactInstalledEditorRequired'):smoke.tool_markers(editor)
            with patch.object(smoke,'EDITOR',editor),self.assertRaisesRegex(ValueError,'CompleteEmbeddedOfficialChildrenRequired'):
                smoke.tool_markers(editor)

    def test_real_temp_apk_container_requires_both_il2cpp_and_unity_arm64(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_apk_host_') as folder:
            path=Path(folder)/'host-only.apk'
            with zipfile.ZipFile(path,'x') as archive:
                for name in ('AndroidManifest.xml','lib/arm64-v8a/libunity.so','lib/arm64-v8a/libil2cpp.so'):archive.writestr(name,b'host-only-not-ELF')
            proof=smoke.validate_apk(path)
            self.assertTrue(proof['crcVerified']);self.assertEqual(proof['entryCount'],3)

    def test_wrong_architecture_and_missing_il2cpp_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_abi_host_') as folder:
            for index,names in enumerate((('lib/arm64-v8a/libunity.so',),('lib/arm64-v8a/libunity.so','lib/arm64-v8a/libil2cpp.so','lib/x86/libbad.so'))):
                path=Path(folder)/('host-only'+str(index)+'.apk')
                with zipfile.ZipFile(path,'x') as archive:
                    archive.writestr('AndroidManifest.xml',b'host')
                    for name in names:archive.writestr(name,b'host')
                with self.assertRaisesRegex(ValueError,'ARM64IL2CPPOnlyRequired'):smoke.validate_apk(path)

    def test_apk_crc_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_crc_host_') as folder:
            path=Path(folder)/'broken.apk';marker=b'unique-host-only-container-marker'
            with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as archive:archive.writestr('AndroidManifest.xml',marker)
            raw=path.read_bytes();offset=raw.index(marker);path.write_bytes(raw[:offset]+b'X'+raw[offset+1:])
            with self.assertRaises((ValueError,zipfile.BadZipFile)):smoke.validate_apk(path)

    def test_native_fixture_never_sets_global_external_tools_or_editorprefs(self):
        text=smoke.TEMPLATE.read_text('utf-8-sig')
        self.assertNotRegex(text,r'AndroidExternalToolsSettings\.(?:sdkRootPath|jdkRootPath|ndkRootPath|gradlePath)\s*=')
        self.assertNotIn('EditorPrefs.',text)
        self.assertIn('All resolved tools must be embedded',text)
        self.assertIn('External tool resolved paths unchanged',text)

    def test_empty_scene_arm64_development_api_and_splash_requirements_are_explicit(self):
        text=smoke.TEMPLATE.read_text('utf-8-sig')
        for expected in ('6000.3.27f1','com.heartoftherain.toolchain95','NewSceneSetup.EmptyScene','scene.rootCount==0',
                         'ScriptingImplementation.IL2CPP','AndroidArchitecture.ARM64','(AndroidSdkVersions)26','(AndroidSdkVersions)36',
                         'PlayerSettings.SplashScreen.show=false','PlayerSettings.SplashScreen.showUnityLogo=false','BuildOptions.Development'):
            self.assertIn(expected,text)
        self.assertNotIn('BuildOptions.AutoRunPlayer',text)
        self.assertNotIn('AssetDatabase.LoadAssetAtPath',text)

    def test_runner_has_no_adb_install_pref_write_or_tool_install_path(self):
        text=Path(smoke.__file__).read_text('utf-8-sig')
        self.assertIn('job.assign(process.pid);jobs.resume_owned_primary(process)',text)
        self.assertIn("'-buildTarget','Android'",text)
        self.assertIn('subprocess.CREATE_NO_WINDOW|0x4',text)
        self.assertNotIn('winreg.SetValue',text);self.assertNotIn('winreg.Delete',text)
        self.assertNotRegex(text,r"\['adb'|adb\.exe|sdkmanager|--install-modules")
        self.assertIn('candidate66InputsUnchanged',text);self.assertIn('mainInputsUnchanged',text)

    def test_registry_fingerprints_hash_values_and_do_not_expose_tool_paths(self):
        import sys
        class Handle:
            def __enter__(self):return self
            def __exit__(self,*args):pass
        hidden='C:/private-user/SDK'
        def enum(_,index):
            if index==0:return ('AndroidSdkRoot_h123',hidden,1)
            if index==1:return ('UnrelatedSetting',hidden,1)
            error=OSError('end');error.winerror=259;raise error
        registry=types.SimpleNamespace(HKEY_CURRENT_USER=1,KEY_READ=2,OpenKey=lambda *args:Handle(),EnumValue=enum)
        with patch.dict(sys.modules,{'winreg':registry}):
            result=smoke.external_pref_fingerprints()
        self.assertTrue(result['exists']);self.assertEqual(len(result['matchingValues']),1)
        self.assertNotIn(hidden,str(result));self.assertEqual(len(result['matchingValues']['AndroidSdkRoot_h123']['valueSHA256']),64)

    def test_registry_access_error_is_not_misreported_as_complete_snapshot(self):
        import sys
        class Handle:
            def __enter__(self):return self
            def __exit__(self,*args):pass
        def enum(*args):
            error=OSError('denied');error.winerror=5;raise error
        registry=types.SimpleNamespace(HKEY_CURRENT_USER=1,KEY_READ=2,OpenKey=lambda *args:Handle(),EnumValue=enum)
        with patch.dict(sys.modules,{'winreg':registry}),self.assertRaises(OSError):smoke.external_pref_fingerprints()

    def test_entire_four_file_input_set_is_required_before_native_smoke(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_exact_smoke_host_') as folder:
            project=Path(folder)
            for relative in ('Assets/Editor/ToolchainSmoke95.cs','Assets/Editor/ToolchainSmoke95.cs.meta','Packages/manifest.json','ProjectSettings/ProjectVersion.txt'):
                path=project/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'host-only-fixture')
            proof={'inputManifest':smoke.source_manifest(project)}
            guards=smoke.readers()[4]
            smoke.validate_prepared_inputs(proof,project,guards.inventory)
            for relative in ('Assets/Editor/UnexpectedInitializeOnLoad.cs','Assets/Resources/Hidden.txt'):
                extra=project/relative;extra.parent.mkdir(parents=True,exist_ok=True);extra.write_bytes(b'unexpected-host-only')
                with self.subTest(relative=relative),self.assertRaisesRegex(ValueError,'ExactFreshPreparedInputSetRequired'):
                    smoke.validate_prepared_inputs(proof,project,guards.inventory)
                extra.unlink()
            (project/'Assets/Editor/ToolchainSmoke95.cs').write_bytes(b'changed-host-only')
            with self.assertRaisesRegex(ValueError,'ExactFreshPreparedInputSetRequired'):
                smoke.validate_prepared_inputs(proof,project,guards.inventory)

    def test_post_import_generated_inputs_require_explicit_fresh_preparation(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_smoke_retry_host_') as folder:
            project=Path(folder)
            for relative in ('Assets/Editor/ToolchainSmoke95.cs','Assets/Editor/ToolchainSmoke95.cs.meta','Packages/manifest.json','ProjectSettings/ProjectVersion.txt'):
                path=project/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'prepared')
            proof={'inputManifest':smoke.source_manifest(project)}
            (project/'Assets/ToolchainSmoke95.unity').write_bytes(b'generated-scene')
            with self.assertRaisesRegex(ValueError,'NoImplicitPostImportRetry'):
                smoke.validate_prepared_inputs(proof,project,smoke.readers()[4].inventory)


if __name__=='__main__':unittest.main(verbosity=2)
