"""Synthetic host guards only; no Unity, SDK, ADB or emulator commands execute."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('ldplayer95_host_guard', Path(__file__).with_name('ldplayer95.py'))
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)

BADGING = """package: name='com.heartoftherain.unity6lts95' versionCode='1'
sdkVersion:'26'
targetSdkVersion:'36'
application-label:'Сердце дождя'
application-debuggable
launchable-activity: name='com.unity3d.player.UnityPlayerActivity'
native-code: 'arm64-v8a'
"""
TREE = """E: manifest (line=1)
  E: uses-sdk (line=2)
    A: android:minSdkVersion(0x0101020c)=(type 0x10)0x1a
    A: android:targetSdkVersion(0x01010270)=(type 0x10)0x24
  E: application (line=3)
    A: android:debuggable(0x0101000f)=(type 0x12)0xffffffff
    E: activity (line=4)
      A: android:name(0x01010003)="com.unity3d.player.UnityPlayerActivity"
      A: android:screenOrientation(0x0101001e)=(type 0x10)0x1
"""


class LD95HostGuards(unittest.TestCase):
    def test_actual_manifest_contract_accepts_exact_approved_settings(self):
        result = api.manifest(BADGING, TREE)
        self.assertEqual((result['minApi'], result['targetApi'], result['development']), (26, 36, True))

    def test_api_target_must_be_exact36_not_merely_above_minimum(self):
        for target in ('26', '34', '35', '37'):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'ExactActualAPI'):
                api.manifest(BADGING.replace("targetSdkVersion:'36'", "targetSdkVersion:'" + target + "'"), TREE)
        with self.assertRaisesRegex(ValueError, 'ExactManifestAPI'):
            api.manifest(BADGING, TREE.replace('0x24', '0x23'))

    def test_smoke_owner_package_nondev_landscape_and_wrong_abi_are_rejected(self):
        controls = [
            (BADGING.replace(api.PACKAGE, 'com.heartoftherain.toolchain95'), TREE),
            (BADGING.replace(api.PACKAGE, 'com.heartoftherain.verification'), TREE),
            (BADGING.replace('application-debuggable\n', ''), TREE),
            (BADGING, TREE.replace('0xffffffff', '0x0')),
            (BADGING, TREE.replace('0x1\n', '0x0\n')),
            (BADGING.replace("'arm64-v8a'", "'x86_64'"), TREE),
        ]
        for badging, tree in controls:
            with self.subTest(control=controls.index((badging, tree))), self.assertRaises((ValueError, RuntimeError)):
                api.manifest(badging, tree)

    def test_device_construction_requires_real_passed_build_before_any_commands(self):
        with patch.object(api.game95, 'validate_development_build', side_effect=ValueError('FixtureNoActualBuild')), patch.object(api, 'run') as command:
            with self.assertRaisesRegex(ValueError, 'FixtureNoActualBuild'):
                api.LDPlayer(Path('Invocation.json'))
            command.assert_not_called()

    def test_build_bridge_rejects_wrong_normalized_package_engine_or_target(self):
        good = {'package': api.PACKAGE, 'unity': api.smoke95.VERSION, 'native': {'after': {'targetApi': 36}}}
        for key, wrong in [('package', 'com.heartoftherain.toolchain95'), ('unity', '6000.6.6f1'), ('target', 34)]:
            value = json.loads(json.dumps(good))
            if key == 'target':
                value['native']['after']['targetApi'] = wrong
            else:
                value[key] = wrong
            with patch.object(api.game95, 'validate_development_build', return_value=value):
                with self.assertRaisesRegex(ValueError, 'FullGameBuildOnly'):
                    api.build(Path('Invocation.json'))

    def test_explicit_emulator_selector_index_required_no_physical_or_implicit_target(self):
        self.assertEqual(api.selector({'HOTR_LDPLAYER95_SERIAL': 'emulator-5558', 'HOTR_LDPLAYER95_INDEX': '2'}), ('emulator-5558', 2))
        controls = [{}, {'HOTR_LDPLAYER95_SERIAL': 'fixture-usb123456', 'HOTR_LDPLAYER95_INDEX': '0'},
                    {'HOTR_LDPLAYER95_SERIAL': '127.0.0.1:5555', 'HOTR_LDPLAYER95_INDEX': '0'},
                    {'HOTR_LDPLAYER95_SERIAL': 'emulator-5558', 'HOTR_LDPLAYER95_INDEX': '32'},
                    {'HOTR_LDPLAYER95_SERIAL': 'emulator-5558;anything', 'HOTR_LDPLAYER95_INDEX': '2'}]
        for value in controls:
            with self.assertRaisesRegex(ValueError, 'ExplicitEmulatorSelector'):
                api.selector(value)

    def test_ldconsole_requires_exact_running_instance_not_spoofed_phone_model(self):
        good = '0,fixture-stopped,0,0,0,-1,-1\n2,fixture-title,1,2,1,123,456\n'
        self.assertEqual(api.console_instance(good, 2)['androidStarted'], True)
        for text in (good.replace(',1,123,456', ',0,123,456'), good.replace(',123,456', ',-1,456'), good + good, ''):
            with self.assertRaisesRegex(ValueError, 'RunningConsoleInstance'):
                api.console_instance(text, 2)

    def test_advertised_arm64_must_exist_in_both_full_and_64bit_abi_lists(self):
        proof = api.advertised_arm64('x86_64,arm64-v8a,x86,armeabi-v7a', 'x86_64,arm64-v8a')
        self.assertTrue(proof['arm64Advertised'])
        for full, wide in [('x86_64,x86', 'x86_64'), ('x86_64,arm64-v8a', 'x86_64'),
                           ('x86_64', 'arm64-v8a'), ('arm64-v8a', 'arm64-v8a,x86_64'),
                           ('arm64-v8a-unsupported', 'arm64-v8a-unsupported')]:
            with self.subTest(full=full, wide=wide), self.assertRaisesRegex(ValueError, 'AdvertisedARM64Required'):
                api.advertised_arm64(full, wide)

    def test_empty_malformed_duplicate_or_legacy_abi_properties_are_refused(self):
        for full, wide in [('', ''), ('arm64', 'arm64'), ('arm64-v8a, arm64-v8a', 'arm64-v8a'),
                           ('arm64-v8a,arm64-v8a', 'arm64-v8a'), ('arm64-v8a', '')]:
            with self.subTest(full=full, wide=wide), self.assertRaises(ValueError):
                api.advertised_arm64(full, wide)

    def test_console_and_adb_boot_must_match_without_publishing_private_values(self):
        target = object.__new__(api.LDPlayer)
        target.serial = 'emulator-5558'
        target.index = 2
        first = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        second = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
        target.adb = lambda *args, **kw: 'device' if args == ('get-state',) else second
        console = [(b'2,fixture-title,1,2,1,123,456', b'', 0), (first.encode(), b'', 0)]
        with patch.object(api.socket, 'create_connection', return_value=SimpleNamespace(__enter__=lambda: None)):
            # A plain context-manager object avoids actual host socket contact.
            class Connected:
                def __enter__(self): return self
                def __exit__(self, *args): return False
            with patch.object(api.socket, 'create_connection', return_value=Connected()), patch.object(api, 'run', side_effect=console):
                with self.assertRaisesRegex(ValueError, 'ConsoleADBTargetMismatch'):
                    target.identity()

    def test_other_packages_and_paths_cannot_change_or_disappear(self):
        before = {'android': '/system/framework/framework-res.apk', api.OWNER: '/data/app/owner/base.apk'}
        api.packages_preserved(before, dict(before, **{api.PACKAGE: '/data/app/candidate/base.apk'}))
        for after in (before, {api.PACKAGE: '/data/app/candidate/base.apk'},
                      dict(before, **{api.PACKAGE: '/data/app/candidate/base.apk', 'other.new': '/data/app/new/base.apk'}),
                      dict(before, **{api.PACKAGE: '/data/app/candidate/base.apk', api.OWNER: '/data/app/replaced/base.apk'})):
            with self.assertRaisesRegex(ValueError, 'OtherInstalledPackagesChanged'):
                api.packages_preserved(before, after)

    def test_static_report_requires_all_eight_outputs_and_exact_byte_bindings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = root / 'GameRuns/test/BuildDevelopment.json'
            native.parent.mkdir(parents=True)
            native.write_text('{}')
            raw = native.parent / 'AndroidStatic95'
            raw.mkdir()
            files = []
            with patch.object(api, 'ROOT', root), patch.object(api, 'static_bindings', return_value={'buildInvocation': {'fixture': True}}):
                for name in ('Signature', 'Zipalign', 'Badging', 'Manifest'):
                    for stream in ('stdout', 'stderr'):
                        path = raw / (name + '_' + stream + '.txt')
                        path.write_bytes(b'fixture')
                        files.append(api.bound(path))
                report = {'status': 'PASS_LTS95_INTERNAL_FULL_GAME_APK', 'errors': [], 'package': api.PACKAGE,
                          'development': True, 'checks': dict.fromkeys(api.REQUIRED_STATIC, True),
                          'toolExitCodes': dict.fromkeys(('Signature', 'Zipalign', 'Badging', 'Manifest'), 0),
                          'buildInvocation': {'fixture': True}, 'artifacts': files}
                path = native.parent / 'StaticApk95.json'
                api.write(path, report)
                api.validated_static({'invocationPath': native.parent / 'Invocation.json'})
                (raw / 'Manifest_stdout.txt').write_bytes(b'changed fixture')
                with self.assertRaisesRegex(ValueError, 'StaticOutputChanged'):
                    api.validated_static({'invocationPath': native.parent / 'Invocation.json'})

    def test_existing_candidate_is_refused_without_replacement_or_reset(self):
        target = object.__new__(api.LDPlayer)
        target.installed_paths = lambda package: ['/data/app/fixture/base.apk']
        target.adb = lambda *args, **kwargs: self.fail('No mutating command allowed')
        with self.assertRaisesRegex(ValueError, 'ExistingCandidatePreservedNoUpgrade'):
            target.absent()

    def test_inventory_hashes_nested_authority_profile_without_parsing_player_attempts(self):
        target = object.__new__(api.LDPlayer)
        owner_apk = '/data/app/owner/base.apk'
        base = '/sdcard/Android/data/' + api.OWNER + '/files'
        canonical = base + '/Profiles/Development-v1/profile.json'
        authority = base + '/Profiles/Development-v1/DailyGiftDevelopmentAuthority/profile.json'
        target.installed_paths = lambda package: [owner_apk]
        target.exists = lambda path: path == base
        hashed, payload_reads = [], []
        def remote_hash(path, *, owner_private=False):
            hashed.append((path, owner_private))
            return 'b' * 64
        target.remote_hash = remote_hash
        def adb(*args, **kwargs):
            if args == ('shell', 'pidof', api.OWNER):
                return ''
            if args == ('shell', 'find', base, '-type', 'f'):
                return canonical + '\n' + authority
            if args[:2] == ('exec-out', 'cat'):
                payload_reads.append(args[2])
                if args[2] == canonical:
                    return json.dumps({'payload': json.dumps({'attempts': []})})
                if args[2] == authority:
                    return json.dumps({'authorityDay': 1, 'claims': []})  # Different schema, no payload/attempts.
            if args[:4] == ('shell', 'run-as', api.OWNER, 'sh'):
                return 'PRESENT'
            if args == ('shell', 'run-as', api.OWNER, 'ls', 'shared_prefs'):
                return 'fixture.xml'
            self.fail('Unexpected inventory transport action')
        target.adb = adb
        snapshot = target.owner_snapshot()
        self.assertEqual(payload_reads, [canonical])
        self.assertIn((authority, False), hashed)
        self.assertIn((canonical, False), hashed)
        self.assertIn(('shared_prefs/fixture.xml', True), hashed)
        self.assertEqual(len(snapshot['externalFileHashes']), 2)
        self.assertEqual(len(snapshot['preferences']), 1)
        self.assertEqual(snapshot['activeAttempts'], 0)

    def synthetic_install(self, *, owner_changes=False):
        """Drive the actual phase logic with an in-memory transport double."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        evidence = Path(temporary.name)
        output = evidence / 'LDPlayerRuns' / ('a' * 32)
        output.mkdir(parents=True)
        owner = {'installed': True, 'externalFileHashes': {'fixture': 'original'}, 'preferences': {'fixture': 'original'}}
        changed = dict(owner, preferences={'fixture': 'changed'}) if owner_changes else owner
        header = {'runner': {'fixture': True}, 'apk': {'sha256': 'b' * 64}, 'nativeReport': {'fixture': True},
                  'buildInvocation': {'fixture': True}, 'staticReport': {'fixture': True}}
        before = {api.OWNER: '/data/app/owner/base.apk', 'fixture.other': '/data/app/other/base.apk'}
        after = dict(before, **{api.PACKAGE: '/data/app/candidate/base.apk'})
        calls, inventories = [], iter((before, after))
        def adb(*args, **kwargs):
            calls.append(args)
            if args == ('install', Path('fixture-candidate.apk')):
                return 'Success'
            if args == ('shell', 'pm', 'list', 'packages', '-f'):
                return '\n'.join('package:' + path + '=' + package for package, path in next(inventories).items())
            if args == ('shell', 'pidof', api.PACKAGE):
                return ''
            self.fail('Unexpected transport action in synthetic installation')
        target = SimpleNamespace(header=lambda: dict(header), identity=lambda: {'fixtureIdentity': True},
                                 absent=Mock(), owner_snapshot=Mock(side_effect=(owner, changed, changed)), adb=adb,
                                 build={'apk': Path('fixture-candidate.apk')},
                                 installed_paths=lambda package: ['/data/app/candidate/base.apk'], remote_hash=lambda path: 'b' * 64)
        previous = dict(header, status='PASS_READ_ONLY_LDPLAYER95_FULL_GAME_PREFLIGHT', identity={'fixtureIdentity': True},
                        ownerBefore=owner, packagesBefore=before)
        api.write(output / 'Preflight.json', previous)
        with patch.object(api, 'EVIDENCE', evidence), patch.object(api, 'LDPlayer', return_value=target), \
             patch.object(api, 'build', return_value=target.build), patch.object(api, 'validated_static', return_value=header['staticReport']):
            result = api.install(Path('fixture-Invocation.json'), output)
        self.assertEqual(json.loads((output / 'Installation.json').read_text()), result)
        return result, calls

    def test_install_phase_is_fresh_only_and_owner_state_preserved(self):
        result, calls = self.synthetic_install()
        self.assertEqual(result['status'], 'PASS_FRESH_FULL_GAME_LDPLAYER95_INSTALL')
        self.assertTrue(result['ownerPreservedAtExit'])
        self.assertEqual([args for args in calls if args[0] == 'install'], [('install', Path('fixture-candidate.apk'))])
        self.assertFalse(any('force-stop' in args or 'clear' in args or 'uninstall' in args for args in calls))

    def test_owner_change_causes_failure_without_rollback_or_owner_mutation(self):
        result, calls = self.synthetic_install(owner_changes=True)
        self.assertEqual(result['status'], 'FAIL_FULL_GAME_LDPLAYER95_INSTALL')
        self.assertEqual(result['errorCategory'], 'LD95OwnerSaveOrPreferencesChanged')
        self.assertEqual(result['finalGuard']['errorCategory'], 'LD95OwnerChangedAtExit')
        self.assertFalse(any('force-stop' in args or 'clear' in args or 'uninstall' in args for args in calls))

    def test_subprocess_errors_never_expose_selector_or_payload(self):
        private = 'fixture-private-selector'
        error = subprocess.CalledProcessError(1, ['adb', '-s', private], output=b'fixture-private-token')
        public = json.dumps(api.safe_error(error))
        self.assertNotIn(private, public)
        self.assertNotIn('fixture-private-token', public)
        self.assertEqual(api.safe_error(ValueError('LD95SafeCategory')), {'errorType': 'ValueError', 'errorCategory': 'LD95SafeCategory'})

    def test_host_command_is_argument_list_bounded_hidden_never_shell(self):
        result = SimpleNamespace(stdout=b'ok', stderr=b'', returncode=0)
        with patch.object(api.subprocess, 'run', return_value=result) as command:
            api.run(['fixture-tool', 'literal with spaces'], 20)
            args, kwargs = command.call_args
            self.assertEqual(args[0], ['fixture-tool', 'literal with spaces'])
            self.assertEqual(kwargs['timeout'], 20)
            self.assertNotIn('shell', kwargs)
            self.assertEqual(kwargs['creationflags'], subprocess.CREATE_NO_WINDOW)
        with self.assertRaisesRegex(ValueError, 'BoundedArgumentList'):
            api.run('fixture shell text', 20)
        with self.assertRaisesRegex(ValueError, 'BoundedArgumentList'):
            api.run(['fixture-tool'], 181)


if __name__ == '__main__':
    unittest.main()
