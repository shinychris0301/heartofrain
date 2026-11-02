"""Host counterexamples for migration source protections; no Unity/SDK actions."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('audit_candidate94',
    Path(__file__).with_name('audit_candidate94.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def entry(content):
    return {'sha256': MODULE.sha_bytes(content), 'bytes': len(content)}


def changed(path, before=b'original', after=b'changed'):
    return MODULE.compare_sources({path: entry(before)}, {path: entry(after)}, {}, {}, {})


class MigrationSourceGuards(unittest.TestCase):
    def test_artwork_byte_change_fails(self):
        self.assertIn('ProtectedAssetBytesChanged:Assets/Art/Background.png',
                      changed('Assets/Art/Background.png')[1])

    def test_scene_byte_change_fails(self):
        self.assertIn('ProtectedAssetBytesChanged:Assets/Scenes/Bootstrap.unity',
                      changed('Assets/Scenes/Bootstrap.unity')[1])

    def test_level_and_mask_json_change_fails(self):
        path = 'Assets/HeartOfTheRain/M46/Levels/Level01.json'
        self.assertIn('ProtectedAssetBytesChanged:' + path, changed(path)[1])

    def test_shader_byte_change_fails(self):
        self.assertIn('ProtectedAssetBytesChanged:Assets/Shaders/Effect.shader',
                      changed('Assets/Shaders/Effect.shader')[1])

    def test_model_runtime_change_fails(self):
        path = 'Assets/HeartOfTheRain/M46/Runtime/Board.cs'
        self.assertIn('UnknownCSharpChanged:' + path, changed(path)[1])

    def test_unknown_csharp_change_fails(self):
        path = 'Assets/HeartOfTheRain/App/Home.cs'
        self.assertIn('UnknownCSharpChanged:' + path, changed(path)[1])

    def test_known_csharp_path_requires_exact_adapter_bytes(self):
        path = 'Assets/HeartOfTheRain/M47/Runtime/EffectMeshBatcher.cs'
        before, allowed, extra = b'original', b'exact API port', b'exact API port plus behavior change'
        baseline = {path: entry(before)}
        reasons = {path: 'Exact identity adapter'}
        rows, violations = MODULE.compare_sources(baseline, {path: entry(allowed)},
                                                  {path: allowed}, reasons, {})
        self.assertFalse(violations)
        self.assertEqual(rows[0]['reason'], reasons[path])
        self.assertIn('NonExactCSharpPort:' + path, MODULE.compare_sources(
            baseline, {path: entry(extra)}, {path: allowed}, reasons, {})[1])

    def test_existing_guid_change_fails_even_when_meta_edits_are_allowed(self):
        path = 'Assets/Art/Background.png.meta'
        before = b'fileFormatVersion: 2\nguid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n'
        after = b'fileFormatVersion: 2\nguid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n'
        rows, policy_violations = changed(path, before, after)
        self.assertFalse(policy_violations)
        self.assertTrue(rows[0]['requiresRootConfigurationReview'])
        report = MODULE.audit_guids({path: entry(before)}, {path: entry(after)}, {},
                                    lambda _: before, lambda _: after)
        self.assertIn('OriginalGuidChanged:' + path, report['violations'])
        self.assertFalse(report['allOriginalGuidsPreserved'])

    def test_meta_field_change_preserves_guid_but_is_not_approved(self):
        path = 'Assets/Art/Background.png.meta'
        before = b'guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\nserializedVersion: 12\n'
        after = b'guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\nserializedVersion: 13\n'
        rows, violations = changed(path, before, after)
        self.assertFalse(violations)
        self.assertTrue(rows[0]['requiresRootConfigurationReview'])
        report = MODULE.audit_guids({path: entry(before)}, {path: entry(after)}, {},
                                    lambda _: before, lambda _: after)
        self.assertTrue(report['allOriginalGuidsPreserved'])
        self.assertEqual(report['changedExistingMetadataCount'], 1)
        self.assertEqual(report['exactExistingMetadataUnchanged'], 0)

    def test_deleted_original_and_unknown_added_assets_fail(self):
        deleted = MODULE.compare_sources({'Assets/Hero.png': entry(b'hero')}, {}, {}, {}, {})[1]
        self.assertIn('OriginalAssetDeleted:Assets/Hero.png', deleted)
        added = MODULE.compare_sources({}, {'Assets/New.cs': entry(b'new')}, {}, {}, {})[1]
        self.assertIn('UnknownAssetAdded:Assets/New.cs', added)

    def test_packages_and_settings_are_reported_for_root_review(self):
        for path in ('Packages/manifest.json', 'ProjectSettings/ProjectSettings.asset'):
            rows, violations = changed(path)
            self.assertFalse(violations)
            self.assertTrue(rows[0]['requiresRootConfigurationReview'])

    def test_binary_diff_is_omitted_and_nonempty_secret_is_not_exported(self):
        self.assertIsNone(MODULE.text_diff(b'\x00binary', b'\x00different', 'Assets/a.png'))
        with self.assertRaisesRegex(ValueError, 'credential'):
            MODULE.text_diff(b'', b'clientSecret: dummy-test-value\n', 'ProjectSettings/a.asset')

    def test_importer_probe_is_one_exact_prepared_editor_fixture(self):
        path = 'Assets/HeartOfTheRain/Verification/Editor/Unity6Importer94.cs'
        self.assertEqual(set(MODULE.FIXTURES), {
            'Assets/HeartOfTheRain/Verification/Editor/Unity6Migration94.cs',
            'Assets/HeartOfTheRain/Verification/Editor/Unity6BatchKey94.cs', path})
        content = b'reviewed read-only Editor probe'
        self.assertFalse(MODULE.compare_sources({}, {path: entry(content)}, {}, {}, {path: content})[1])
        self.assertIn('NewFixtureDiffersFromTemplate:' + path, MODULE.compare_sources(
            {}, {path: entry(content + b' extra behavior')}, {}, {}, {path: content})[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
