"""Host-only phone94 authorization/coverage guards; no device or Unity tests."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('phone94_under_host_test', Path(__file__).with_name('phone94.py'))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def state():
    return {'activeAttempts': 0, 'profiles': {'Profiles/isolated/profile.json': 'a' * 64},
            'preferences': {'prefs.xml': 'b' * 64}, 'profileSummaries': [{'activeAttempts': 0}],
            'installedSHA256': 'c' * 64}


def synthetic_coverage():
    passed = []
    for level in range(1, 51):
        passed.append('L' + str(level) + ' accepts natural move')
        for tool in range(4):
            passed.extend(('L' + str(level) + ' tool ' + str(tool) + ' spends one stock',
                           'L' + str(level) + ' tool ' + str(tool) + ' preserves moves'))
    passed.extend(('Practice Match solved through page commands and real animation playback',
                   'Practice Rocket solved through page commands and real animation playback',
                   'Practice Clear solved through page commands and real animation playback',
                   'Exactly 900 coins shows the enabled native refill button and price',
                   'Repeated native refill callback charges exactly once',
                   'Connected Continue exposes the approved five-move/900-coin offer',
                   'Confirmed decline charges exactly one life, no coins, and opens retry pre-level',
                   'Celebration completion cannot grant a duplicate reward L50',
                   'Celebration returns Home without next-level modal L50'))
    return {'status': 'PASS_NATIVE_REGRESSION', 'failures': [], 'unity': '6000.6.6f1', 'platform': 'Android',
            'boards': 50, 'actions': 408, 'clips': 354, 'labels': 1, 'checks': len(passed), 'passed': passed,
            'damageFamilies': sorted(api.legacy_scope.EXPECTED_FAMILIES)}


class Phone94Guards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-phone94-host-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / 'Evidence'
        self.project = self.root / 'Project'
        self.directory = self.out / 'Build'
        self.directory.mkdir(parents=True)
        self.apk = self.project / 'Builds/Development.apk'
        self.apk.parent.mkdir(parents=True)
        self.apk.write_bytes(b'synthetic host guard fixture, never an Android APK')
        self.native_path = self.directory / 'BuildDevelopment.json'
        self.native = {'status': 'PASS_ISOLATED_UNITY6_94_BUILDDEVELOPMENT', 'operation': 'BuildDevelopment',
            'exitCode': 0, 'errors': 0, 'buildResult': 'Succeeded', 'nonDevelopmentCompileOnly': False,
            'buildPackageName': api.PACKAGE, 'unity': '6000.6.6f1', 'expectedUnity': '6000.6.6f1',
            'output': str(self.apk), 'apkSHA256': api.phone.sha(self.apk), 'bytes': self.apk.stat().st_size,
            'after': {'packageName': api.PACKAGE, 'showSplashScreen': False, 'showUnityLogo': False,
                      'portraitOnly': True, 'applicationEntry': 'Activity', 'backend': 'IL2CPP',
                      'architectures': 'ARM64', 'minApi': 26}}
        for name, value in (('ROOT', self.root), ('OUT', self.out), ('PROJECT', self.project)):
            active = patch.object(api, name, value)
            active.start()
            self.addCleanup(active.stop)
        active = patch.object(api, 'binding', lambda path: {'path': Path(path).relative_to(self.root).as_posix(),
                              'sha256': api.phone.sha(path), 'bytes': Path(path).stat().st_size})
        active.start()
        self.addCleanup(active.stop)

    def write_build(self, *, invocation_update=None):
        self.native_path.write_text(json.dumps(self.native), encoding='utf-8')
        invocation = {'status': 'PASS_ISOLATED_UNITY6_94_NATIVE', 'exitCode': 0,
            'entry': 'HeartOfTheRain.Verification.Unity6Migration94.BuildDevelopment',
            'mainInputsUnchanged': True, 'unityPidsAfter': [], 'nativeReportSHA256': api.phone.sha(self.native_path),
            'nativeReport': self.native_path.relative_to(self.root).as_posix(),
            'actualEngineVersionFromProcessLog': '6000.6.6f1'}
        invocation.update(invocation_update or {})
        (self.directory / 'Invocation.json').write_text(json.dumps(invocation), encoding='utf-8')
        (self.directory / 'CandidateSources_after.json').write_text('{}', encoding='utf-8')
        raw = self.directory / 'AndroidStatic94'
        raw.mkdir(exist_ok=True)
        for name in ('Signature', 'Zipalign', 'Badging', 'Manifest'):
            for stream in ('stdout', 'stderr'):
                (raw / (name + '_' + stream + '.txt')).write_text('host schema guard fixture only', encoding='utf-8')
        runner = self.root / 'Verification/Tools/Unity6Migration94/check_apk94.py'
        runner.parent.mkdir(parents=True, exist_ok=True)
        runner.write_text('synthetic host runner-binding fixture only', encoding='utf-8')
        report = {'status': 'PASS_INTERNAL_UNITY6_94_APK', 'errors': [], 'package': api.PACKAGE,
                  'development': True, 'nonDevelopmentCompileOnly': False, 'apk': api.binding(self.apk),
                  'nativeReport': api.binding(self.native_path), 'buildInvocation': api.binding(self.directory / 'Invocation.json'),
                  'candidateSources': api.binding(self.directory / 'CandidateSources_after.json'),
                  'runner': api.binding(runner), 'artifacts': [api.binding(path) for path in sorted(raw.iterdir())],
                  'checks': {key: True for key in ('zipCrcPass', 'signatureVerifies', 'zipAlignFourBytePass',
                      'elf16KiBLoadSegmentsPass', 'storedNative16KiBAligned', 'abiArm64Only', 'packageMatchesNativeBuild', 'portraitActivity',
                      'minApi26', 'developmentFlagMatches', 'sdkFreeDex', 'identityBridgePresent', 'sourcesUnchanged', 'apkUnchanged')}}
        (self.directory / 'StaticApk94.json').write_text(json.dumps(report), encoding='utf-8')

    def candidate(self):
        result = api.Candidate.__new__(api.Candidate)
        result.out = self.out / 'Phone'
        result.out.mkdir(parents=True)
        result.base = '/sdcard/Android/data/' + api.PACKAGE + '/files'
        result.owner = Mock()
        result.owner_snapshot = Mock(return_value=state())
        result.header = Mock(return_value={'apk': {'sha256': 'd' * 64}, 'scope': 'synthetic host fixture'})
        result.build = {'apk': self.apk}
        return result

    def test_correct_explicit_development_build_schema(self):
        self.write_build()
        self.assertEqual(api.validate_build(self.native_path)['apk'], self.apk)

    def test_non_development_apk_cannot_be_installed(self):
        self.native['nonDevelopmentCompileOnly'] = True
        self.write_build()
        with self.assertRaisesRegex(RuntimeError, 'PassedSideBySideDevelopmentBuildRequired'):
            api.validate_build(self.native_path)

    def test_owner_identifier_is_never_a_candidate(self):
        self.native['buildPackageName'] = 'com.heartoftherain.verification'
        self.write_build()
        with self.assertRaisesRegex(RuntimeError, 'PassedSideBySideDevelopmentBuildRequired'):
            api.validate_build(self.native_path)

    def test_visible_unity_logo_is_rejected(self):
        self.native['after']['showUnityLogo'] = True
        self.write_build()
        with self.assertRaisesRegex(RuntimeError, 'NativeSplashPackageOrAndroidSettingsInvalid'):
            api.validate_build(self.native_path)

    def test_changed_apk_bytes_are_rejected(self):
        self.write_build()
        self.apk.write_bytes(b'changed artifact')
        with self.assertRaisesRegex(RuntimeError, 'CurrentCandidateApkChanged'):
            api.validate_build(self.native_path)

    def test_failed_unity_process_cannot_authorize_device_work(self):
        self.write_build(invocation_update={'exitCode': 1})
        with self.assertRaisesRegex(RuntimeError, 'RealCompletedUnity6ProcessRequired'):
            api.validate_build(self.native_path)

    def test_current_build_source_preservation_is_required(self):
        self.write_build(invocation_update={'mainInputsUnchanged': False})
        with self.assertRaisesRegex(RuntimeError, 'RealCompletedUnity6ProcessRequired'):
            api.validate_build(self.native_path)

    def test_missing_static_proof_blocks_phone_actions(self):
        self.write_build()
        (self.directory / 'StaticApk94.json').unlink()
        with self.assertRaises(RuntimeError):
            api.validate_build(self.native_path)

    def test_changed_static_raw_artifact_blocks_phone_actions(self):
        self.write_build()
        (self.directory / 'AndroidStatic94/Signature_stdout.txt').write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'StaticRawArtifactChanged'):
            api.validate_build(self.native_path)

    def test_failed_static_check_blocks_phone_actions(self):
        self.write_build()
        path = self.directory / 'StaticApk94.json'
        value = json.loads(path.read_text('utf-8'))
        value['checks']['portraitActivity'] = False
        path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'PassedCurrentStaticApkRequired'):
            api.validate_build(self.native_path)

    def test_existing_candidate_is_preserved_before_install(self):
        candidate = self.candidate()
        candidate.installed_path = Mock(return_value='/data/app/existing/base.apk')
        with self.assertRaisesRegex(RuntimeError, 'ExistingCandidatePreservedNoReplacement'):
            candidate.preflight()
        candidate.owner.adb.assert_not_called()

    def test_candidate_stop_never_targets_owner(self):
        candidate = self.candidate()
        candidate.assert_installed = Mock()
        candidate.owner.adb.side_effect = ['', '']
        candidate.stop_candidate()
        self.assertEqual(candidate.owner.adb.call_args_list[0].args, ('shell', 'am', 'force-stop', api.PACKAGE))
        self.assertEqual(candidate.owner.adb.call_args_list[1].args, ('shell', 'pidof', api.PACKAGE))
        candidate.owner.install.assert_not_called()
        candidate.owner.launch.assert_not_called()

    def test_fresh_install_uses_no_replacement_or_owner_stop(self):
        candidate = self.candidate()
        api.save(candidate.out / 'Preflight.json', {'status': 'PASS_READ_ONLY_SIDE_BY_SIDE_PREFLIGHT94',
                 'apk': {'sha256': 'd' * 64}, 'ownerBefore': state()})
        candidate.installed_path = Mock(return_value=None)
        candidate.owner.exists.return_value = False
        candidate.owner.adb.return_value = 'Success'
        candidate.assert_installed = Mock()
        candidate.idle = Mock(return_value=state())
        result = candidate.install()
        self.assertEqual(result['status'], 'PASS_FRESH_SIDE_BY_SIDE_INSTALL94')
        candidate.owner.adb.assert_called_once_with('install', self.apk)
        candidate.owner.install.assert_not_called()
        candidate.owner.launch.assert_not_called()

    def test_owner_changes_block_install_before_mutation(self):
        candidate = self.candidate()
        changed = state()
        changed['profiles'] = {'changed': 'e' * 64}
        api.save(candidate.out / 'Preflight.json', {'status': 'PASS_READ_ONLY_SIDE_BY_SIDE_PREFLIGHT94',
                 'apk': {'sha256': 'd' * 64}, 'ownerBefore': changed})
        with self.assertRaisesRegex(RuntimeError, 'OwnerChangedSincePreflight'):
            candidate.install()
        candidate.owner.adb.assert_not_called()

    def test_locked_screen_never_captured(self):
        candidate = self.candidate()
        candidate.idle = Mock(return_value=state())
        candidate.owner.adb.side_effect = ['topResumedActivity=' + api.PACKAGE + '/Activity',
                                          'KeyguardServiceDelegate\n showing=true\n']
        with self.assertRaisesRegex(RuntimeError, 'UnlockedCandidateRequired'):
            candidate.capture('Locked')
        self.assertEqual(candidate.owner.adb.call_count, 2)
        self.assertFalse((candidate.out / 'Screens').exists())

    def test_synthetic_coverage_requires_exact_new_engine(self):
        api.native_scope(synthetic_coverage(), '6000.6.6f1')
        with self.assertRaisesRegex(RuntimeError, 'NativeCoverageNotPassed'):
            api.native_scope(synthetic_coverage(), '2022.3.62f3')

    def test_native_partial_counter_cannot_claim_full_campaign(self):
        report = synthetic_coverage()
        report['boards'] = 49
        with self.assertRaisesRegex(RuntimeError, 'NativeCoverageNotPassed'):
            api.native_scope(report, '6000.6.6f1')

    def test_count_and_passed_list_must_agree(self):
        report = synthetic_coverage()
        report['checks'] += 1
        with self.assertRaisesRegex(RuntimeError, 'NativeCoverageNotPassed'):
            api.native_scope(report, '6000.6.6f1')

    def test_missing_lifecycle_case_is_rejected(self):
        report = synthetic_coverage()
        report['passed'].remove('Celebration returns Home without next-level modal L50')
        report['checks'] -= 1
        with self.assertRaisesRegex(RuntimeError, 'LifecycleCoverageMissing'):
            api.native_scope(report, '6000.6.6f1')


if __name__ == '__main__':
    unittest.main()
