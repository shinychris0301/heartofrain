"""Host semantic counterexamples; no Unity/importer/SDK/device operations."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('review_importers94',
    Path(__file__).with_name('review_importers94.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def texture():
    return {'fileFormatVersion': 2, 'guid': 'a' * 32, 'TextureImporter': {
        'serializedVersion': 12, 'spriteMode': 1, 'spriteBorder': {'x': 9, 'y': 9, 'z': 9, 'w': 9},
        'mipmaps': {'enableMipMap': 1}, 'internalIDToNameTable': [],
        'platformSettings': [{'serializedVersion': 3, 'buildTarget': 'Android',
                              'overridden': 1, 'maxTextureSize': 2048, 'textureCompression': 0}],
        'spriteSheet': {'spriteID': 'b' * 32, 'sprites': []}}}


class ImporterSemanticGuards(unittest.TestCase):
    def test_safe_yaml_reads_nested_unity_document(self):
        value = MODULE.parse_yaml(b'%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n--- !u!129 &1\nPlayerSettings:\n  a: [{b: 3}]\n')
        self.assertEqual(value, {'PlayerSettings': {'a': [{'b': 3}]}})

    def test_duplicate_yaml_keys_and_aliases_rejected(self):
        for raw in (b'a: 1\na: 2\n', b'a: &anchor [1]\nb: *anchor\n'):
            with self.assertRaises(ValueError):
                MODULE.parse_yaml(raw)

    def test_numeric_equivalence_never_rounds_large_internal_ids(self):
        self.assertTrue(MODULE.equal(0, 0.0))
        self.assertFalse(MODULE.equal(True, 1))
        self.assertFalse(MODULE.equal(0, -0.0))
        self.assertFalse(MODULE.equal(11111111111111111111111111111111,
                                      11111111111111111111111111111112))
        self.assertFalse(MODULE.equal({1: 'a'}, {'1': 'a'}))

    def test_schema_only_version_is_separate_from_yaml_equality(self):
        before = texture()
        after = copy.deepcopy(before)
        after['TextureImporter']['serializedVersion'] = 13
        result = MODULE.review_meta(before, after)
        self.assertFalse(result['semanticYamlEqual'])
        self.assertFalse(result['remainingImporterFieldChangesRequiringReview'])

    def test_guid_and_original_sprite_id_changes_remain_visible(self):
        before = texture()
        after = copy.deepcopy(before)
        after['guid'] = 'c' * 32
        after['TextureImporter']['spriteSheet']['spriteID'] = 'd' * 32
        result = MODULE.review_meta(before, after)
        self.assertFalse(result['assetGuidPreserved'])
        self.assertFalse(result['topLevelSpriteIDPreserved'])
        self.assertTrue(result['remainingImporterFieldChangesRequiringReview'])

    def test_mipmap_change_is_actual_runtime_importer_delta(self):
        before = texture()
        after = copy.deepcopy(before)
        after['TextureImporter']['mipmaps']['enableMipMap'] = 0
        result = MODULE.review_meta(before, after)
        self.assertEqual(result['remainingImporterFieldChangesRequiringReview'][0]['path'], 'mipmaps/enableMipMap')

    def test_android_override_change_is_not_hidden_by_schema_version(self):
        before = texture()
        after = copy.deepcopy(before)
        after['TextureImporter']['platformSettings'][0]['serializedVersion'] = 4
        after['TextureImporter']['platformSettings'][0]['maxTextureSize'] = 1024
        result = MODULE.review_meta(before, after)
        self.assertFalse(result['androidSettingsUnchanged'])
        self.assertFalse(result['existingPlatforms']['Android']['settingsEqualIgnoringSchemaVersion'])

    def test_added_webgl_override_is_explicit_and_never_default_approved(self):
        before = texture()
        after = copy.deepcopy(before)
        after['TextureImporter']['platformSettings'].append({'serializedVersion': 4,
            'buildTarget': 'WebGL', 'overridden': 1, 'maxTextureSize': 1024})
        result = MODULE.review_meta(before, after)
        self.assertIn('WebGL', result['addedPlatforms'])
        self.assertFalse(result['allAddedPlatformsAreNonOverridden'])

    def test_new_subasset_mapping_is_not_reported_as_full_mapping_equality(self):
        before = texture()
        after = copy.deepcopy(before)
        after['TextureImporter']['internalIDToNameTable'] = [{'first': {213: 17}, 'second': 'Art_0'}]
        after['TextureImporter']['spriteSheet']['sprites'] = [{'name': 'Art_0', 'internalID': 17,
            'border': {'x': 0, 'y': 0, 'z': 0, 'w': 0}}]
        result = MODULE.review_meta(before, after)
        self.assertTrue(result['topLevelSpriteIDPreserved'])
        self.assertTrue(result['internalIDToNameTable']['existingEntriesPreserved'])
        self.assertFalse(result['internalIDToNameTable']['exactEntriesEqual'])
        self.assertEqual(result['internalIDToNameTable']['introducedOrChangedEntries'], 1)
        self.assertEqual(len(result['nonzeroTopBorderAndGeneratedZeroChildBorder']), 1)

    def test_mapping_multiplicity_preserved_counterexample(self):
        value = {'first': {213: 17}, 'second': 'Art_0'}
        result = MODULE.list_mapping_delta([value, value], [value])
        self.assertFalse(result['existingEntriesPreserved'])
        self.assertEqual(result['removedOrChangedExistingEntries'], 1)

    def test_known_new_unity_field_wrong_value_is_unresolved(self):
        before = texture()
        after = copy.deepcopy(before)
        after['TextureImporter']['spriteTessellationMethod'] = 1
        result = MODULE.review_meta(before, after)
        self.assertEqual(result['remainingImporterFieldChangesRequiringReview'][0]['path'], 'spriteTessellationMethod')

    def test_new_platform_fields_do_not_claim_exact_settings_equality(self):
        before = texture()
        after = copy.deepcopy(before)
        after['TextureImporter']['platformSettings'][0]['ignorePlatformSupport'] = 0
        result = MODULE.review_meta(before, after)
        self.assertFalse(result['androidSettingsUnchanged'])
        self.assertTrue(result['androidExistingFieldsPreserved'])
        self.assertEqual(result['existingPlatforms']['Android']['addedFields'][0]['after'], 0)

    def test_nonempty_credentials_refused_without_export(self):
        MODULE.refuse_credentials({'password': ''})
        with self.assertRaisesRegex(ValueError, 'credential'):
            MODULE.refuse_credentials({'nested': [{'clientSecret': 'synthetic-test-value'}]})

    def test_audit_companion_cannot_be_modified_after_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory / 'FileChanges.json'
            path.write_text('[]', encoding='utf-8')
            audit = {'reportFileSHA256': {'FileChanges.json': MODULE.sha(path)}}
            self.assertEqual(MODULE.bound_audit_json(directory, audit, 'FileChanges.json'), [])
            path.write_text('[{}]', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'companion hash differs'):
                MODULE.bound_audit_json(directory, audit, 'FileChanges.json')


if __name__ == '__main__':
    unittest.main(verbosity=2)
