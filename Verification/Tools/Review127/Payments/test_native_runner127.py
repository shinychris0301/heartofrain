"""Pure helper/AST privacy guards. Never calls runner.run or any signing tool."""
from __future__ import annotations
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
PATH=HERE/'run_payment_diagnostics127_02.py'
spec=importlib.util.spec_from_file_location('native_runner127_guard_tests',PATH);runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
SOURCE=PATH.read_text('utf-8');TREE=ast.parse(SOURCE)

class NativeRunnerGuard127(unittest.TestCase):
    def test_only_explicit_build_branch_can_retrieve_password(self):
        parents={child:node for node in ast.walk(TREE) for child in ast.iter_child_nodes(node)}
        calls=[node for node in ast.walk(TREE) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='local_password']
        self.assertEqual(len(calls),1)
        current=calls[0];guards=[]
        while current in parents:
            current=parents[current]
            if isinstance(current,ast.If):guards.append(ast.unparse(current.test))
        self.assertIn('build',guards)

    def test_password_is_child_environment_only_no_shell_or_argv(self):
        self.assertIn('env.update(HOTR_RELEASE_SIGNING_PASSWORD=password',SOURCE)
        command=SOURCE.split('command=[',1)[1].split(']\n',1)[0]
        self.assertNotIn('password',command);self.assertNotIn('shell=True',SOURCE)
        self.assertIn("env.pop('HOTR_RELEASE_SIGNING_PASSWORD',None)",SOURCE)

    def test_gui_layout_does_not_disable_graphics(self):
        command=SOURCE.split('command=[',1)[1].split(']\n',1)[0]
        self.assertNotIn('-nographics',command)
        self.assertIn('SigninLayout127Verification.Run',SOURCE)

    def test_known_hub_only_exclusion_and_owned_job(self):
        self.assertIn('if executable==HUB.resolve()',SOURCE)
        self.assertIn('SameProjectEditorBlocksNative127',SOURCE)
        self.assertIn('UnknownEditorProjectBlocksNative127',SOURCE)
        self.assertIn('job.assign(process.pid)',SOURCE)
        self.assertIn('if job:job.close()',SOURCE)

    def test_only_public_download_cache_subtree_is_seeded(self):
        self.assertIn("Path('E:/G126A/caches/modules-2/files-2.1')",SOURCE)
        self.assertIn("GRADLE/'caches/modules-2/files-2.1'",SOURCE)
        self.assertIn("'nonce':receipt['nonce']",SOURCE)
        self.assertNotIn("shutil.copytree(previous,GRADLE/'caches')",SOURCE)

    def test_scrub_finishes_before_public_log_copy(self):
        final=SOURCE.split('finally:',1)[1]
        self.assertLess(final.index('scrub_generated(project,raw,password)'),final.index('shutil.copyfile(path,output/name)'))
        self.assertIn('if scrubbed:',final)
        with tempfile.TemporaryDirectory(prefix='hotr-diagnostic-scrub-') as tmp:
            root=Path(tmp);project=root/'Game';raw=root/'Raw';cache=root/'Cache'
            for folder in (project/'Library',project/'Temp',raw,cache):folder.mkdir(parents=True,exist_ok=True)
            token='DEMONSTRATION_SIGNING_PLACEHOLDER_ONLY'
            for file in (project/'Library/example.gradle',raw/'Unity.log',cache/'example.properties'):file.write_text('before '+token+' after')
            with patch.object(runner,'GRADLE',cache):result=runner.scrub_generated(project,raw,token)
            self.assertTrue(result['complete']);self.assertEqual(result['files'],3)
            for file in (project/'Library/example.gradle',raw/'Unity.log',cache/'example.properties'):self.assertNotIn(token,file.read_text())

    def test_asset_path_rejects_traversal_and_windows_separator(self):
        with tempfile.TemporaryDirectory(prefix='hotr-diagnostic-path-') as tmp:
            project=Path(tmp);(project/'Assets').mkdir();(project/'Assets/good.cs').write_text('example')
            self.assertEqual(runner.asset_path(project,'Assets/good.cs'),(project/'Assets/good.cs').resolve())
            for bad in ('Assets/../secret','Assets/..\\secret','Assets/C:/secret','Assets//good.cs','Assets/secret\n.cs','C:/secret'):
                with self.assertRaises(RuntimeError):runner.asset_path(project,bad)

    def test_layout_report_requires_exact_source_pins_and_complete_actual_matrix(self):
        with tempfile.TemporaryDirectory(prefix='hotr-layout-report-') as tmp:
            root=Path(tmp);public=root/'Public';public.mkdir();project=root/'Game'
            names=sorted(runner.LAYOUT_BOUND_PATHS)
            pins=[]
            for name in names:
                path=project/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(name);pins.append({'path':name,'sha256':runner.sha(path)})
            report=public/'Native.json';value={'status':runner.LAYOUT_STATUS,'project':str(project),'unity':'6000.3.27f1','actualNativeLayout':True,'actualProvider':False,'deviceTouched':False,'errors':[],'cases':180,'layouts':540,'visibleBodyRaycasts':1,'bodyRaycastRejects':1,'sourceBindings':pins}
            def save():report.write_text(json.dumps(value));return runner.sha(report)
            with patch.object(runner,'PUBLIC',public):
                digest=save();self.assertEqual(runner.accepted_layout(report,digest,project),digest)
                value['actualNativeLayout']=False
                with self.assertRaises(RuntimeError):runner.accepted_layout(report,save(),project)
                value['actualNativeLayout']=True;value['layouts']=539
                with self.assertRaises(RuntimeError):runner.accepted_layout(report,save(),project)
                value['layouts']=540;digest=save();(project/names[0]).write_text('changed')
                with self.assertRaises(RuntimeError):runner.accepted_layout(report,digest,project)

    def test_foreign_project_and_missing_server_text_pin_fail_before_credentials(self):
        with tempfile.TemporaryDirectory(prefix='hotr-layout-complete-') as tmp:
            root=Path(tmp);public=root/'Public';public.mkdir();project=root/'Game';pins=[]
            for name in sorted(runner.LAYOUT_BOUND_PATHS):
                path=project/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(name);pins.append({'path':name,'sha256':runner.sha(path)})
            report=public/'Native.json';value={'status':runner.LAYOUT_STATUS,'project':str(project),'unity':'6000.3.27f1','actualNativeLayout':True,'actualProvider':False,'deviceTouched':False,'errors':[],'cases':180,'layouts':540,'visibleBodyRaycasts':1,'bodyRaycastRejects':1,'sourceBindings':pins}
            def save():report.write_text(json.dumps(value));return runner.sha(report)
            with patch.object(runner,'PUBLIC',public):
                digest=save();self.assertEqual(runner.accepted_layout(report,digest,project),digest)
                value['project']=str(root/'ForeignGame')
                with self.assertRaisesRegex(RuntimeError,'SameCanonicalNativeLayoutProjectRequired127'):runner.accepted_layout(report,save(),project)
                value['project']=str(project);value['sourceBindings']=[pin for pin in pins if not pin['path'].endswith('/ServerAccountText83.cs')]
                with self.assertRaisesRegex(RuntimeError,'ExactNativeLayoutSourcePinsRequired127'):runner.accepted_layout(report,save(),project)

    def test_receipt_pin_length_duplicate_and_hash_shape_cannot_be_truncated(self):
        paths=['Assets/Source'+str(index)+'.cs' for index in range(2001)];hashes=['0'*64]*len(paths)
        self.assertEqual(len(runner.source_pin_pairs({'paths':paths,'sha256':hashes})),2001)
        with self.assertRaisesRegex(RuntimeError,'CompleteUniqueNativeSourcePinListsRequired127'):runner.source_pin_pairs({'paths':paths,'sha256':hashes[:-1]})
        duplicate=list(paths);duplicate[1]=duplicate[0].upper()
        with self.assertRaisesRegex(RuntimeError,'CompleteUniqueNativeSourcePinListsRequired127'):runner.source_pin_pairs({'paths':duplicate,'sha256':hashes})
        malformed=list(hashes);malformed[-1]='not-a-sha'
        with self.assertRaisesRegex(RuntimeError,'CanonicalNativeSourceHashesRequired127'):runner.source_pin_pairs({'paths':paths,'sha256':malformed})

    def test_apk_checker_retains_strict_provider_signature_and_privacy_audits(self):
        source=(HERE/'check_payment_apk127.py').read_text('utf-8');ast.parse(source)
        for check in ('ActualApkUsesDeveloperOwnedReleaseCertificate','ActualApkSha1MatchesVkRegistrationMaterial','ApkZipAndNative16KiBAlignment','HttpsTrafficOnly','YandexAutomaticInitializationDisabled','NoUnapprovedAdvertisingSdkDefinitions','ActualProtectedManagedIdentityBridgeDefined','ActualYandexAppMetricaRuStoreAndUnityBridgeDefined','ActualViewBrowsablePaymentSchemeBinding'):
            self.assertIn(check,source)
        for dependency in ('com.yandex.android:mobileads:8.6.0=','io.appmetrica.analytics:analytics:8.6.0=','ru.rustore.sdk:pay:11.1.0=','ru.rustore.sdk:core:10.5.0='):self.assertIn(dependency,source)

    def test_apk_checker_binds_version127_source_epoch_and_actual_diagnostic_types(self):
        source=(HERE/'check_payment_apk127.py').read_text('utf-8')
        self.assertIn("versionCode='127'",source);self.assertNotIn("versionCode='126'",source)
        self.assertIn('PASS_PAYMENT_DIAGNOSTIC127_ANDROID_BUILD',source)
        self.assertIn('SourceEpochAndNativeLayoutReportBindingRequired127',source)
        self.assertIn('PaymentDiagnosticSnapshot127',source);self.assertIn('EditorLayoutFixtureAbsentFromPlayer127',source)

if __name__=='__main__':unittest.main()
