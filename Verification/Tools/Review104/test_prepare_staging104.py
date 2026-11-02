"""Host-only preparation/ownership tests. No Unity, build, network or real host."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('prepare_staging104_tested', Path(__file__).with_name('prepare_staging104.py'))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class StagingPreparation104Tests(unittest.TestCase):
    def config(self, **changes):
        value = dict(version=1, mode='ManagedGuestServer', origin='https://never-contacted.hotr-fixture.net', identityScope='review-vk-staging', allowDevelopmentLoopback=False, socialEnabled=True)
        value.update(changes)
        return json.dumps(value)

    def source(self, root):
        (root / 'AGENTS.md').write_text('synthetic fixture', encoding='utf-8')
        for part in ('Assets/HeartOfTheRain/Resources', 'Packages', 'ProjectSettings'):
            (root / 'Unity' / part).mkdir(parents=True, exist_ok=True)
        (root / 'Unity/Assets/fixture.txt').write_text('synthetic', encoding='utf-8')
        (root / 'Unity/Assets/fixture.txt.meta').write_text('guid: unchanged', encoding='utf-8')
        (root / 'Unity/ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 2022.3.62f3\n', encoding='utf-8')
        (root / 'Unity/ProjectSettings/ProjectSettings.asset').write_text('  companyName: Original\n  productName: Original\n  applicationIdentifier:\n    Android: com.owner.original\n  androidUseCustomKeystore: 1\n', encoding='utf-8')
        (root / 'Unity/Packages/manifest.json').write_text('{}', encoding='utf-8')

    def test_canonical_fields_and_normalized_origin(self):
        value = json.loads(api.canonical_configuration(self.config(origin='https://Never-Contacted.Hotr-Fixture.net:443/')))
        self.assertEqual(value['origin'], 'https://never-contacted.hotr-fixture.net')
        self.assertEqual(tuple(value), api.FIELDS)

    def test_reject_unknown_secret_duplicate_and_wrong_types(self):
        rows = [self.config(accessToken='synthetic-must-never-copy'), self.config(version=True), self.config(socialEnabled=1), self.config(allowDevelopmentLoopback=True), self.config(identityScope='production'), self.config()[:-1] + ',"origin":"https://second.hotr-fixture.net"}']
        for raw in rows:
            with self.subTest(raw=raw), self.assertRaises(api.Blocked):
                api.canonical_configuration(raw)

    def test_reject_placeholder_loopback_path_userinfo(self):
        for origin in ('', 'https://example.com', 'https://api.example.org', 'https://backend.invalid', 'http://real.hotr-fixture.net', 'https://127.0.0.1', 'https://user@real.hotr-fixture.net', 'https://real.hotr-fixture.net/api'):
            with self.subTest(origin=origin), self.assertRaises(api.Blocked):
                api.canonical_configuration(self.config(origin=origin))

    def test_unconfigured_template_blocks_before_candidate_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'config.json'
            config.write_text(self.config(origin=''), encoding='utf-8')
            with self.assertRaises(api.Blocked):
                api.prepare(root, config, 'blocked', True)
            self.assertFalse((root / '.verification-cache').exists())

    def test_prepare_isolates_identity_preserves_sources_and_guid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.source(root)
            before = api._sources(root)
            config = root / 'config.json'
            config.write_text(self.config(), encoding='utf-8')
            result = api.prepare(root, config, 'isolated', True)
            self.assertEqual(result['status'], 'PREPARED_STAGING104')
            self.assertEqual(api._sources(root), before)
            project = Path(result['project'])
            settings = (project / 'ProjectSettings/ProjectSettings.asset').read_text(encoding='utf-8')
            self.assertIn('HeartRainStaging104', settings)
            self.assertIn(api.PACKAGE, settings)
            self.assertIn('androidUseCustomKeystore: 0', settings)
            self.assertEqual(api.sha(project / 'Assets/fixture.txt.meta'), before['Assets/fixture.txt.meta'])
            self.assertFalse((project / api.RESOURCE).exists())
            with self.assertRaises(api.Blocked):
                api.prepare(root, config, 'isolated', True)

    def test_explicit_recovery_removes_only_exact_owned_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.source(root)
            config = root / 'config.json'
            config.write_text(self.config(), encoding='utf-8')
            result = api.prepare(root, config, 'recover', True)
            project = Path(result['project'])
            receipt = json.loads(Path(result['receipt']).read_text(encoding='utf-8'))
            asset = project / api.RESOURCE
            asset.parent.mkdir(parents=True)
            asset.write_text(api.canonical_configuration(self.config()), encoding='utf-8')
            am, fm = Path(str(asset) + '.meta'), Path(str(asset.parent) + '.meta')
            am.write_text('asset metadata', encoding='utf-8')
            fm.write_text('folder metadata', encoding='utf-8')
            marker = project / '.hotr-staging104-lease.json'
            marker.write_text(json.dumps(dict(version=1, ownerPid=2147483000, nonce=receipt['nonce'], payloadSHA256=api.sha(asset), assetMetaSHA256=api.sha(am), folderMetaSHA256=api.sha(fm))), encoding='utf-8')
            expected = api.sha(marker)
            asset.write_text('foreign bytes', encoding='utf-8')
            with self.assertRaises(api.Blocked):
                api.recover(root, 'recover', expected)
            self.assertTrue(marker.exists())
            self.assertEqual(asset.read_text(encoding='utf-8'), 'foreign bytes')
            asset.write_text(api.canonical_configuration(self.config()), encoding='utf-8')
            recovered = api.recover(root, 'recover', expected)
            self.assertEqual(recovered['status'], 'RECOVERED_OWNED_STAGING_RESOURCE104')
            self.assertFalse(marker.exists())
            self.assertFalse(asset.parent.exists())
            self.assertTrue((project / 'Assets/fixture.txt').exists())


if __name__ == '__main__':
    unittest.main()
