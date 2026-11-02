"""Synthetic host guards; no Unity, SDK, ADB, emulator or phone is invoked."""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('accepted93_ld_host', Path(__file__).with_name('accepted93_ld.py'))
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


def envelope(state=None):
    return json.dumps({'payload': json.dumps({'attempts': [] if state is None else [{'state': state}],
        'coins': 1250, 'lives': 5, 'currentLevel': 1, 'completed': [], 'revision': 7})})


class FakeTarget:
    def __init__(self):
        self.selector = {'serial': 'emulator-5558'}
        self.value = {'installedSHA256': '1' * 64, 'externalFileHashes': {'a' * 64: 'b' * 64},
                      'preferences': {'c' * 64: 'd' * 64}, 'profiles': {'a' * 64: {'coins': 1250}}, 'activeAttempts': 0}

    def identity(self):
        return {'index': 0, 'sameLDConsoleAndADBBoot': True}

    def snapshot(self, stopped=True):
        return deepcopy(self.value)

    def packages(self):
        return {api.PACKAGE: '/data/app/owner/base.apk', 'org.fixture.other': '/data/app/other/base.apk'}


class Accepted93HostGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for key, value in {'ROOT': self.root, 'OUT': self.root / 'public', 'PRIVATE': self.root / 'private',
                           'SELECTOR': self.root / 'selector.json', 'APK': self.root / 'game.apk',
                           'SUMMARY': self.root / 'summary.json', 'ADB': self.root / 'adb.exe',
                           'CONSOLE': self.root / 'console.exe', '__file__': str(self.root / 'runner.py')}.items():
            self.stack.enter_context(patch.object(api, key, value))
        for path in (api.APK, api.SUMMARY, api.ADB, api.CONSOLE, Path(api.__file__)):
            path.write_text('fixture', encoding='utf-8')
        self.output = api.OUT / ('a' * 32)
        self.proof = {'fixture': True, 'unityInputs': 5407, 'apk': api.bound(api.APK)}
        self.target = FakeTarget()

    def make_preflight(self):
        with patch.object(api, 'accepted_proof', return_value=deepcopy(self.proof)), patch.object(api, 'Target', return_value=self.target):
            result = api.preflight(self.output)
        self.assertEqual(result['status'], 'PASS_READ_ONLY_ACCEPTED93_LD_PREFLIGHT95')
        return result

    def run_update(self, command=None, proof=None):
        def install(arguments, timeout, accepted):
            self.assertEqual(arguments, [api.ADB, '-s', 'emulator-5558', 'install', '-r', api.APK])
            self.assertEqual((timeout, accepted), (180, None))
            self.target.value['installedSHA256'] = api.APK_SHA
            return b'Streamed install\nSuccess\n', b'', 0
        with patch.object(api, 'accepted_proof', side_effect=proof) if proof else patch.object(api, 'accepted_proof', return_value=deepcopy(self.proof)), \
             patch.object(api, 'Target', return_value=self.target), patch.object(api, 'command', side_effect=command or install) as invoked:
            result = api.update(self.output)
        return result, invoked

    def test_source_failure_precedes_any_target_or_device_command(self):
        with patch.object(api, 'accepted_proof', side_effect=ValueError('FixtureSourceDrift')), patch.object(api, 'Target') as target, patch.object(api, 'command') as command:
            result = api.preflight(self.output)
        self.assertEqual(result['status'], 'FAIL_ACCEPTED93_LD_PREFLIGHT95')
        target.assert_not_called()
        command.assert_not_called()

    def test_actual_proof_guard_checks_fixed_artifact_and_exact5407_source_count(self):
        manifest, collector_file = self.root / 'manifest.json', self.root / 'collector.py'
        manifest.write_text('{}', encoding='utf-8')
        collector_file.write_text('fixture', encoding='utf-8')
        summary = {'status': 'FIXTURE_ACCEPTED93', 'unityInputCount': 5407, 'sourceManifest': api.bound(manifest),
                   'proofArguments': {'builds': 'builds.json', 'android': 'android.json'}}
        api.SUMMARY.write_text(json.dumps(summary), encoding='utf-8')
        collector = SimpleNamespace(__file__=str(collector_file), STATUS='FIXTURE_ACCEPTED93',
            freeze=Mock(return_value={'inputCount': 5407}), verify_binding=Mock(), sources_match=Mock(),
            build_proof=Mock(return_value={'apks': [{**api.bound(api.APK), 'development': True}]}),
            static_proof=Mock(return_value={'fixtureStatic': True}))
        with patch.object(api, 'SUMMARY_SHA', api.sha(api.SUMMARY)), patch.object(api, 'APK_SHA', api.sha(api.APK)), \
             patch.object(api, 'APK_BYTES', api.APK.stat().st_size), patch.object(api, 'module', return_value=collector) as imported:
            self.assertEqual(api.accepted_proof()['unityInputs'], 5407)
            collector.freeze.return_value = {'inputCount': 5408}
            with self.assertRaisesRegex(ValueError, 'SourceCountOrStatusChanged'):
                api.accepted_proof()
            collector.freeze.return_value = {'inputCount': 5407}
            api.APK.write_text('different fixture', encoding='utf-8')
            imported.reset_mock()
            with self.assertRaisesRegex(ValueError, 'FixedSummaryOrAPKChanged'):
                api.accepted_proof()
            imported.assert_not_called()

    def test_only_canonical_profiles_are_parsed_and_active_or_unknown_states_block(self):
        self.assertEqual(api.canonical_attempts('Profiles/local/profile.json', envelope())['coins'], 1250)
        self.assertIsNone(api.canonical_attempts('Profiles/local/DailyGiftDevelopmentAuthority/profile.json', '{other schema'))
        for state in ('Reserved', 'Started', 'SurpriseState'):
            with self.subTest(state=state), self.assertRaises(ValueError):
                api.canonical_attempts('Profiles/local/profile.json', envelope(state))

    def real_snapshot(self, files=None, state=None, running=False, version=1):
        target = api.Target.__new__(api.Target)
        canonical = api.BASE + '/Profiles/local/profile.json'
        nested = api.BASE + '/Profiles/local/DailyGiftDevelopmentAuthority/profile.json'
        files = files or [canonical, nested, api.BASE + '/Other/data.json']
        def fake_adb(*args, **kwargs):
            if args[:2] == ('shell', 'pidof'): return '1234' if running else ''
            if args[:3] == ('shell', 'pm', 'path'): return 'package:/data/app/fixture/base.apk'
            if args[:3] == ('shell', 'dumpsys', 'package'): return '  versionCode=' + str(version) + ' minSdk=22 targetSdk=36'
            if args[:2] == ('shell', 'find'): return '\n'.join(files)
            if args[:2] == ('exec-out', 'cat'):
                self.assertEqual(args[2], canonical, 'Authority schema must be hashed without interpreting it')
                return envelope(state)
            if args[:3] == ('shell', 'run-as', api.PACKAGE):
                return 'PRESENT' if args[3] == 'sh' else 'fixture.xml'
            raise AssertionError('Unexpected mocked command')
        target.adb = Mock(side_effect=fake_adb)
        target.exists = Mock(return_value=True)
        target.file_hash = Mock(return_value='e' * 64)
        return target

    def test_snapshot_hashes_nested_authority_and_preferences_without_parsing_nested_schema(self):
        target = self.real_snapshot()
        result = target.snapshot()
        self.assertEqual((len(result['externalFileHashes']), len(result['profiles']), len(result['preferences'])), (3, 1, 1))
        self.assertEqual(target.file_hash.call_count, 5)
        self.assertEqual(result['activeAttempts'], 0)

    def test_snapshot_refuses_running_active_pending_and_downgrade_targets(self):
        cases = [dict(running=True), dict(state='Started'), dict(version=2),
                 dict(files=[api.BASE + '/Profiles/local/profile.json', api.BASE + '/HOTR_RunRegression'])]
        for value in cases:
            with self.subTest(case=value), self.assertRaises(ValueError):
                self.real_snapshot(**value).snapshot()

    def test_exact_private_emulator_selector_rejects_phone_wrong_package_index_and_tools(self):
        good = {'serial': 'emulator-5558', 'index': 0, 'package': api.PACKAGE, 'adb': str(api.ADB),
                'console': str(api.CONSOLE), 'bootID': '12345678-1234-1234-1234-123456789abc'}
        api.write(api.SELECTOR, good)
        self.assertEqual(api.load_selector(), good)
        for key, wrong in [('serial', 'fixture-physical-usb'), ('serial', '127.0.0.1:5555'), ('index', True),
                           ('index', 1), ('package', 'com.heartoftherain.unity6lts95'), ('adb', str(self.root / 'other.exe')),
                           ('bootID', 'changed-private-identity')]:
            api.SELECTOR.write_text(json.dumps({**good, key: wrong}), encoding='utf-8')
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, 'ExactPrivateLDTargetRequired'):
                api.load_selector()

    def test_identity_requires_actual_console_boot_match_and_advertised_arm64(self):
        target = api.Target.__new__(api.Target)
        target.selector = {'serial': 'emulator-5558', 'bootID': '12345678-1234-1234-1234-123456789abc'}
        api.SELECTOR.write_text('{}', encoding='utf-8')
        values = {('get-state',): 'device', ('shell', 'cat', '/proc/sys/kernel/random/boot_id'): target.selector['bootID'],
                  ('shell', 'getprop', 'ro.product.cpu.abilist'): 'x86_64,arm64-v8a',
                  ('shell', 'getprop', 'ro.product.cpu.abilist64'): 'x86_64,arm64-v8a',
                  ('shell', 'getprop', 'ro.build.version.sdk'): '30'}
        target.adb = Mock(side_effect=lambda *args: values[args])
        def owned_command(args, timeout):
            return ((b'0,fixture-title,1,2,1,123,456\n' if args[1] == 'list2'
                     else target.selector['bootID'].encode()), b'', 0)
        with patch.object(api.socket, 'create_connection'), patch.object(api, 'command', side_effect=owned_command):
            self.assertTrue(target.identity()['sameLDConsoleAndADBBoot'])
            values[('shell', 'getprop', 'ro.product.cpu.abilist64')] = 'x86_64'
            with self.assertRaisesRegex(ValueError, 'AdvertisedARM64Required'):
                target.identity()
            values[('shell', 'getprop', 'ro.product.cpu.abilist64')] = 'arm64-v8a'
            values[('shell', 'cat', '/proc/sys/kernel/random/boot_id')] = 'different-fixture-boot'
            with self.assertRaisesRegex(ValueError, 'PrivateBootLinkChanged'):
                target.identity()

    def test_installed_hash_or_save_drift_after_preflight_prevents_install(self):
        self.make_preflight()
        self.target.value['installedSHA256'] = '2' * 64
        with patch.object(api, 'accepted_proof', return_value=self.proof), patch.object(api, 'Target', return_value=self.target), patch.object(api, 'command') as command:
            with self.assertRaisesRegex(ValueError, 'InstalledHashOrSaveChanged'):
                api.update(self.output)
        command.assert_not_called()
        self.target.value['installedSHA256'] = '1' * 64
        self.target.value['preferences']['c' * 64] = 'f' * 64
        with patch.object(api, 'accepted_proof', return_value=self.proof), patch.object(api, 'Target', return_value=self.target), patch.object(api, 'command') as command:
            with self.assertRaisesRegex(ValueError, 'InstalledHashOrSaveChanged'):
                api.update(self.output)
        command.assert_not_called()

    def test_only_save_preserving_install_r_allowed_and_other_data_remains_exact(self):
        before = self.make_preflight()['before']
        result, command = self.run_update()
        self.assertEqual(result['status'], 'PASS_ACCEPTED93_LD_UPDATE95_SAVES_PRESERVED')
        command.assert_called_once()
        self.assertEqual(result['after'], {**before, 'installedSHA256': api.APK_SHA})
        self.assertTrue(result['savePreservedAtExit'])
        self.assertEqual((api.PRIVATE / self.output.name / 'Install_stdout.txt').read_bytes(), b'Streamed install\nSuccess\n')
        with patch.object(api, 'accepted_proof', return_value=self.proof), patch.object(api, 'Target') as target:
            validated = api.validate_update_receipt(self.output)
        self.assertEqual(validated['after'], result['after'])
        target.assert_not_called()

    def test_existing_target_hash_skips_install_without_stopping_or_clearing(self):
        self.target.value['installedSHA256'] = api.APK_SHA
        self.make_preflight()
        result, command = self.run_update()
        self.assertFalse(result['installAttempted'])
        self.assertEqual(result['status'], 'PASS_ACCEPTED93_LD_UPDATE95_SAVES_PRESERVED')
        command.assert_not_called()

    def test_source_drift_at_last_pre_mutation_guard_stops_install(self):
        self.make_preflight()
        result, command = self.run_update(proof=[self.proof, {'drift': True}, self.proof])
        self.assertEqual(result['status'], 'FAIL_ACCEPTED93_LD_UPDATE95')
        self.assertEqual(result['errorCategory'], 'Accepted93SourceChangedBeforeMutation')
        command.assert_not_called()

    def test_success_text_without_installed_apk_hash_is_not_accepted(self):
        self.make_preflight()
        result, command = self.run_update(command=lambda *args: (b'Success\n', b'', 0))
        self.assertEqual(result['status'], 'FAIL_ACCEPTED93_LD_UPDATE95')
        self.assertEqual(result['errorCategory'], 'Accepted93InstalledTargetHashMismatch')
        command.assert_called_once()

    def test_receipt_tamper_or_later_source_drift_prevents_pure_acceptance(self):
        self.make_preflight()
        self.run_update()
        path = self.output / 'Update.json'
        value = api.read(path)
        value['final']['preferences'] = {}
        path.write_text(json.dumps(value), encoding='utf-8')
        with patch.object(api, 'accepted_proof', return_value=self.proof), patch.object(api, 'Target') as target:
            with self.assertRaisesRegex(ValueError, 'InstalledHashOrSaveChanged'):
                api.validate_update_receipt(self.output)
        target.assert_not_called()

    def test_launch_only_ordinary_start_with_private_capture_no_visual_or_migration_pass(self):
        self.make_preflight()
        self.run_update()
        def adb(*args, **kwargs):
            if args[:2] == ('shell', 'pidof'): return '1234'
            if args[:3] == ('shell', 'dumpsys', 'activity'): return 'mResumedActivity: ' + api.ACTIVITY
            if args[:3] == ('shell', 'dumpsys', 'window'): return 'KeyguardServiceDelegate\n showing=false\n'
            if args[:2] == ('exec-out', 'screencap'): return b'fixture-png'
            if args[0] == 'logcat':
                self.assertEqual(args, ('logcat', '-d', '--pid=1234', '-v', 'brief'))
                return b'fixture ordinary runtime\n'
            raise AssertionError('Unexpected mocked launch read')
        self.target.adb = Mock(side_effect=adb)
        with patch.object(api, 'accepted_proof', return_value=self.proof), patch.object(api, 'Target', return_value=self.target), \
             patch.object(api, 'command', return_value=(b'Status: ok\n', b'', 0)) as command, \
             patch.object(api.time, 'sleep'), patch.object(api, 'module', return_value=SimpleNamespace(validate_png=lambda data: (360, 640))):
            result = api.launch(self.output, 2)
        command.assert_called_once_with([api.ADB, '-s', 'emulator-5558', 'shell', 'am', 'start', '-W', '-n', api.ACTIVITY], 60, None)
        self.assertEqual(result['status'], 'RECORDED_ACCEPTED93_LD_LAUNCH95_REQUIRES_REVIEW')
        self.assertFalse(result['rootVisualReviewCompleted'])
        self.assertEqual(result['selectedRuntimeErrorCount'], 0)
        self.assertTrue(result['actualAndroidOSCapture']['path'].startswith('private/'))
        self.assertTrue(result['proof']['fixture'])

    def test_other_package_mutation_cannot_be_hidden_by_owner_update(self):
        before = {api.PACKAGE: '/old.apk', 'org.fixture.other': '/other.apk'}
        api.unchanged_other_packages(before, {**before, api.PACKAGE: '/new.apk'})
        for after in ({**before, 'org.fixture.other': '/changed.apk'}, {api.PACKAGE: '/old.apk'},
                      {**before, 'org.fixture.extra': '/extra.apk'}):
            with self.assertRaisesRegex(ValueError, 'OtherPackagesChanged'):
                api.unchanged_other_packages(before, after)

    def test_immutable_phase_paths_refuse_reuse_and_wrong_roots(self):
        self.make_preflight()
        with self.assertRaisesRegex(ValueError, 'ScopedFreshRunRequired'):
            api.output_paths(self.output, True)
        with self.assertRaisesRegex(ValueError, 'ScopedFreshRunRequired'):
            api.output_paths(self.root / 'outside' / ('b' * 32), True)
        with self.assertRaises(FileExistsError):
            api.write(self.output / 'Preflight.json', {'overwrite': True})

    def test_subprocess_bounds_list_execution_and_private_error_redaction(self):
        with patch.object(api.subprocess, 'run', return_value=SimpleNamespace(stdout=b'fixture', stderr=b'', returncode=0)) as run:
            api.command([api.ADB, '-s', 'emulator-5558', 'get-state'], 12)
        self.assertEqual(run.call_args.kwargs['timeout'], 12)
        self.assertNotIn('shell', run.call_args.kwargs)
        self.assertEqual(run.call_args.kwargs['creationflags'], subprocess.CREATE_NO_WINDOW)
        for arguments, timeout in [('text command', 10), ([], 181), ([], 0)]:
            with self.assertRaisesRegex(ValueError, 'BoundedArgumentsRequired'):
                api.command(arguments, timeout)
        sensitive = subprocess.CalledProcessError(1, ['adb', '-s', 'private-serial'], output='private-token')
        self.assertEqual(api.safe(sensitive), {'errorType': 'CalledProcessError'})
        self.assertEqual(api.safe(ValueError('private-token=value')), {'errorType': 'ValueError'})


if __name__ == '__main__':
    unittest.main()
