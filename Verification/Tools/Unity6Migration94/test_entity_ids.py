"""Host-only exact API-port and preserved-reference counterexamples; no Unity."""
import importlib.util
import difflib
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('entity_id94_under_test', Path(__file__).with_name('prepare_entity_ids.py'))
API = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(API)


class EntityApiHostTests(unittest.TestCase):
    def source(self, relative):
        return (API.ROOT / 'Unity' / relative).read_bytes()

    def transformed(self, relative):
        return API.transform(relative, self.source(relative)).decode('utf-8-sig').replace('\r\n', '\n')

    def test_all_nine_exact_main_sources_transform_without_mutating_them(self):
        before = {path: self.source(path) for path in API.FILES}
        for path in API.FILES:
            after = API.transform(path, before[path])
            self.assertNotEqual(after, before[path])
            original_lines = before[path].decode('utf-8-sig').splitlines(keepends=True)
            output_lines = after.decode('utf-8-sig').splitlines(keepends=True)
            a = [line.replace('\r\n', '\n') for line in original_lines]
            b = [line.replace('\r\n', '\n') for line in output_lines]
            for kind, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
                if kind == 'equal':
                    self.assertEqual(original_lines[i1:i2], output_lines[j1:j2])
        self.assertEqual(before, {path: self.source(path) for path in API.FILES})

    def test_mixed_endings_preserve_each_equal_line_and_use_nearest_previous_ending(self):
        source = b'first\r\nchanged\nthird\r\nfourth\n'
        after = API.preserve_unmodified_line_bytes(source, 'first\nreplacement\nthird\nfourth\n')
        self.assertEqual(after, b'first\r\nreplacement\r\nthird\r\nfourth\n')
        self.assertEqual(API.preserve_unmodified_line_bytes(source, source.decode().replace('\r\n', '\n')), source)

    def test_bom_final_no_newline_and_inserted_local_line_ending_are_preserved(self):
        source = b'\xef\xbb\xbffirst\nsecond\r\nlast'
        after = API.preserve_unmodified_line_bytes(source, 'first\nsecond\ninserted\nlast')
        self.assertEqual(after, b'\xef\xbb\xbffirst\nsecond\r\ninserted\r\nlast')

    def test_runtime_key_stores_full_opaque_entity_and_full_order(self):
        output = self.transformed(API.RUNTIME + 'M47/Runtime/EffectMeshBatcher.cs')
        self.assertIn('readonly EntityId texture;readonly int order;', output)
        self.assertIn('texture.Equals(other.texture)&&order==other.order', output)
        self.assertIn('Dictionary<BatchKey,Slot>', output)
        self.assertIn('var key=new BatchKey(g.textureId,order);', output)
        self.assertNotIn('((long)g.textureId<<32)', output)
        self.assertNotIn('(int)g.textureId', output)

    def test_atlas_manifest_caches_use_full_typed_pair_without_string_format(self):
        for suffix in ('Chapter01M04/Scripts/RocketSpritePlayer.cs', 'Chapter01M05/Scripts/RenderedSpritePlayer.cs'):
            output = self.transformed(API.RUNTIME + suffix)
            self.assertIn('Dictionary<(EntityId atlas,EntityId manifest), SharedFrames>', output)
            self.assertIn('cacheKey = (atlas.GetEntityId(), manifest.GetEntityId());', output)
            self.assertNotIn('GetEntityId().ToString()', output)

    def test_native_identity_comparisons_keep_strong_ids_and_diagnostic_ids_are_strings(self):
        profile = self.transformed(API.RUNTIME + 'Verification/ProfileM71Verification.cs')
        warm = self.transformed(API.EDITOR + 'PresentationWarmupVerification.cs')
        diagnostic = self.transformed(API.RUNTIME + 'Verification/Execution78Probe.cs')
        self.assertIn('EntityId blurId=default;', profile)
        self.assertIn('Check(texture.GetEntityId()==blurId', profile)
        self.assertIn('static EntityId[] ids;', warm)
        self.assertIn('public string name,materialId,textureId;public int order;', diagnostic)
        self.assertIn('material?material.GetEntityId().ToString():string.Empty', diagnostic)

    def test_raw_hash_assertions_and_complete_reference_comparisons_remain(self):
        effect = self.transformed(API.EDITOR + 'EffectBatchVerification.cs')
        dense = self.transformed(API.EDITOR + 'DenseSubmissionVerification.cs')
        for _, raw_hash in API.ARCHIVES[:2]:
            self.assertIn(raw_hash, effect)
        self.assertIn(API.ARCHIVES[2][1], dense)
        self.assertEqual(effect.count('Check(compiled==original,'), 2)
        self.assertIn('report.compiledSourceMatchesArchive=compiled==original;', dense)
        self.assertIn('Check(report.compiledSourceMatchesArchive,', dense)
        self.assertIn('original=AdaptArchivedEntityIdentity94(original);', effect)
        self.assertIn('original=EffectBatchVerification.AdaptArchivedEntityIdentity94(original);', dense)
        self.assertIn('public string entityIdAdapterScope=', effect)
        self.assertIn('public string entityIdAdapterScope=', dense)
        self.assertIn('not cross-engine pixel or performance proof', dense)

    def test_all_three_archived_reference_bodies_match_only_the_explicit_adapter(self):
        changes = [{'relative': path, 'after': API.transform(path, self.source(path))} for path in API.FILES]
        archives = API.raw_archive_inputs(self.source(API.EDITOR + 'EffectBatchVerification.cs'))
        proofs = API.prove_adapted_references(changes, archives)
        self.assertEqual(len(proofs), 3)
        self.assertTrue(all(row['fullCompiledBodyMatchesExactAdapter'] and row['nonApiBodyChangeRejected'] for row in proofs))

    def test_unexpected_math_color_index_order_and_geometry_edits_fail_complete_body_proof(self):
        changes = [{'relative': path, 'after': API.transform(path, self.source(path))} for path in API.FILES]
        archives = API.raw_archive_inputs(self.source(API.EDITOR + 'EffectBatchVerification.cs'))
        target = API.EDITOR + 'DenseSubmissionVerification.cs'
        index = next(i for i, row in enumerate(changes) if row['relative'] == target)
        original = changes[index]['after']
        mutations = [(b'position.x+l*cos-b*sin', b'position.x+l*cos+b*sin'),
                     (b'Color32 c=color;', b'Color32 c=Color.white;'),
                     (b'current.triangles.Add(v+2);', b'current.triangles.Add(v+1);'),
                     (b'slot.renderer.sortingOrder=order;', b'slot.renderer.sortingOrder=order+1;'),
                     (b'new Vector3(position.x+l*cos', b'new Vector3(position.x+.000001f+l*cos')]
        for before, after in mutations:
            self.assertIn(before, original)
            changes[index]['after'] = original.replace(before, after, 1)
            with self.assertRaisesRegex(ValueError, 'AdaptedCompiledReferenceMismatch'):
                API.prove_adapted_references(changes, archives)

    def test_duplicate_or_already_adapted_identity_shape_is_refused(self):
        original = self.source(API.RUNTIME + 'M47/Runtime/EffectMeshBatcher.cs').decode('utf-8-sig').replace('\r\n', '\n')
        with self.assertRaisesRegex(ValueError, 'AlreadyAdaptedBatchBodyRefused'):
            API.adapt_batch_body(API.adapt_batch_body(original))
        original += '\nreadonly Dictionary<long,Slot> open=new Dictionary<long,Slot>();\n'
        with self.assertRaisesRegex(ValueError, 'ExactSingleApiReplacementRequired'):
            API.adapt_batch_body(original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
