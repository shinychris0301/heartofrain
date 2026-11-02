"""Host-only copy/config guards. Never creates the real Game copy or runs an Editor."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import types
import unittest
from unittest.mock import patch

import game95 as game


def item(raw):return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


class GameHostTests(unittest.TestCase):
    def test_preimport_identity_patch_preserves_every_other_byte_including_mixed_endings(self):
        raw=b'%YAML 1.1\r\n  companyName: DefaultCompany\n  productName: Original\r\n  m_ShowUnitySplashScreen: 1\r\n  m_ShowUnitySplashLogo: 1\n  applicationIdentifier:\r\n    Android: com.original.app\n  other: unchanged\r\n'
        actual=game.isolated_settings(raw)
        expected=raw.replace(b'companyName: DefaultCompany',('companyName: '+game.COMPANY).encode()).replace(b'Android: com.original.app',('Android: '+game.PACKAGE).encode())
        self.assertEqual(actual,expected)
        self.assertIn(b'm_ShowUnitySplashScreen: 1\r\n',actual)
        self.assertIn(b'm_ShowUnitySplashLogo: 1\n',actual)

    def test_ambiguous_missing_identity_yaml_is_rejected(self):
        for raw in (b'companyName: no indent\n',b'  companyName: one\n  companyName: two\n',b'  companyName: one\n  applicationIdentifier:\n    iPhone: wrong\n'):
            with self.assertRaises(ValueError):game.isolated_settings(raw)

    def test_actual_smoke_pass_is_required_before_any_copy_or_output_mutation(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_game_gate_host_') as folder:
            root=Path(folder);target=root/'Game';output=root/'Evidence'
            process=types.SimpleNamespace(unity_pids=lambda:[])
            with patch.object(game,'PROJECT',target),patch.object(game.smoke95,'readers',return_value=(None,None,process,None,None)),\
                 patch.object(game,'validate_smoke_receipt',side_effect=ValueError('actual-smoke-not-passed')):
                with self.assertRaisesRegex(ValueError,'actual-smoke-not-passed'):game.prepare(output,root/'missing.json')
            self.assertFalse(target.exists());self.assertFalse(output.exists())

    def test_failed_smoke_receipt_cannot_be_relabelled_by_path(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_failed_smoke_host_') as folder:
            root=Path(folder);path=root/'SmokeRuns/Set01/Invocation.json';path.parent.mkdir(parents=True);path.write_text(json.dumps({'status':'FAIL_ACTUAL_LTS95_TOOLCHAIN_SMOKE'}))
            with patch.object(game,'EVIDENCE',root),self.assertRaisesRegex(ValueError,'ActualSuccessfulMinimalSmokeRequired'):
                game.validate_smoke_receipt(path)

    def test_native_settings_accept_only_exact_isolated_portrait_splash_off_api_configuration(self):
        original={'packageName':game.PACKAGE,'companyName':game.COMPANY,'productName':'Сердце дождя','backend':'IL2CPP','architectures':'ARM64',
                  'applicationEntry':'Activity','orientation':'Portrait','minApi':26,'targetApi':36,'showSplashScreen':False,'showUnityLogo':False,
                  'portraitOnly':True,'bundle':False,'customKeystore':False,'sdkFreeDefines':True}
        game.validate_native_settings(original)
        for key,value in (('packageName','com.heartoftherain.toolchain95'),('architectures','ARMv7, ARM64'),('minApi',24),('targetApi',35),
                          ('applicationEntry','GameActivity'),('showUnityLogo',True),('showSplashScreen',True),('portraitOnly',False),('sdkFreeDefines',False)):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'ExactNativeGameSettingsRequired'):
                game.validate_native_settings({**original,key:value})

    def test_source_delta_retains_added_changed_deleted_paths_and_raw_bindings(self):
        original={'Assets/a.cs':item(b'old'),'Assets/drop.cs':item(b'drop')}
        changed={'Assets/a.cs':item(b'new'),'Assets/new.cs':item(b'new')}
        result=game.delta(original,changed)
        self.assertEqual({row['kind'] for row in result},{'added','changed','deleted'})
        self.assertEqual(next(row for row in result if row['path']=='Assets/a.cs')['before'],item(b'old'))

    def test_original_runtime_source_and_guid_changes_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_assets_host_') as folder:
            root=Path(folder);project=root/'Game';relative='Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs'
            guid=b'fileFormatVersion: 2\nguid: 11111111111111111111111111111111\n'
            originals={relative:b'original-runtime',relative+'.meta':guid}
            for tail,raw in originals.items():
                for directory in (root/'Unity',project):
                    path=directory/tail;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            fixture=project/game.RELATIVE_FIXTURE;fixture.parent.mkdir(parents=True);fixture.write_bytes(game.TEMPLATE.read_bytes());fixture.with_suffix('.cs.meta').write_bytes(guid)
            main={'files':{'Unity/'+tail:item(raw) for tail,raw in originals.items()}}
            def inventory():return {'files':{path.relative_to(project).as_posix():item(path.read_bytes()) for path in project.rglob('*') if path.is_file()}}
            guards=types.SimpleNamespace(one_guid=lambda raw:re.search(rb'guid: ([a-f0-9]{32})',raw)[1])
            with patch.object(game,'ROOT',root),patch.object(game,'PROJECT',project):
                self.assertTrue(game.protected_assets(main,inventory(),guards)['originalCSharpUnchangedIncludingGetInstanceIDAndTestPins'])
                (project/relative).write_bytes(b'ported-runtime')
                with self.assertRaisesRegex(ValueError,'OriginalArtLevelRuntimeOrTestSourceChanged'):game.protected_assets(main,inventory(),guards)
                (project/relative).write_bytes(originals[relative]);(project/(relative+'.meta')).write_bytes(guid.replace(b'11111111111111111111111111111111',b'22222222222222222222222222222222'))
                with self.assertRaisesRegex(ValueError,'OriginalAssetGUIDChanged'):game.protected_assets(main,inventory(),guards)

    def test_template_does_not_carry_entityid_ports_or_replace_2022_test_pins(self):
        text=game.TEMPLATE.read_text('utf-8-sig')
        self.assertIn('GetPlatformIcons(BuildTargetGroup.Android,AndroidPlatformIconKind.Legacy)',text)
        self.assertNotIn('GetEntityId',text);self.assertNotIn('AdaptArchivedEntityIdentity94',text)
        self.assertNotIn('NativeVerification',text);self.assertNotIn('EditorPrefs.',text)
        self.assertIn('report.unity=="6000.3.27f1"',text)

    def test_native_build_is_development_only_without_provider_or_release_guard_bypass(self):
        text=game.TEMPLATE.read_text('utf-8-sig')
        self.assertIn('BuildOptions.Development|BuildOptions.AllowDebugging',text)
        self.assertNotIn('AutoRunPlayer',text);self.assertNotIn('BuildNonDevelopment',text)
        self.assertNotIn('com.heartoftherain.verification',text)
        self.assertIn('showUnityLogo=false',text);self.assertIn('show=false',text)

    def test_readonly_build_validator_requires_bound_source_sha_and_never_runs_device_commands(self):
        text=Path(game.__file__).read_text('utf-8-sig')
        region=text.split('def validate_build_receipt(path):',1)[1].split('def run(',1)[0]
        self.assertIn('StoredSourceManifestSHAChanged',region)
        self.assertIn('CurrentSourcesDifferFromActualBuild',region)
        self.assertNotIn('subprocess.',region);self.assertNotIn('adb',region.lower())
        self.assertIn('def validate_development_build(path):',region)

    def test_native_report_project_must_equal_the_exact_game_root(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_native_root_host_') as folder:
            project=Path(folder)/'Game';apk=project/'Builds/run/Game.apk'
            good={'project':str(project),'apk':str(apk)}
            with patch.object(game,'PROJECT',project):
                game.validate_native_identity_paths(good,apk)
                for wrong in (str(Path(folder)/'Smoke'),str(Path(folder)/'OtherGame'),''):
                    with self.subTest(wrong=wrong),self.assertRaisesRegex(ValueError,'NativeReportProjectMustEqualExactGameRoot'):
                        game.validate_native_identity_paths({**good,'project':wrong},apk)

    def test_native_report_apk_must_equal_outer_bound_apk_even_with_same_file_name(self):
        with tempfile.TemporaryDirectory(prefix='hotr95_native_apk_host_') as folder:
            project=Path(folder)/'Game';apk=project/'Builds/run/Game.apk';wrong=project/'Builds/other/Game.apk'
            good={'project':str(project),'apk':str(apk)}
            with patch.object(game,'PROJECT',project),self.assertRaisesRegex(ValueError,'NativeReportAPKMustEqualOuterBoundAPK'):
                game.validate_native_identity_paths({**good,'apk':str(wrong)},apk)


if __name__=='__main__':unittest.main(verbosity=2)
