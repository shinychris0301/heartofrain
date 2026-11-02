"""Host-only counterexamples for one-asset diagnostic preparation and parity."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('sprite_scale94', Path(__file__).with_name('sprite_scale94.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SpriteScaleHostGuards(unittest.TestCase):
    def test_exact_five_new_files_preserve_every_existing_input(self):
        before = {'Assets/Model.cs': {'sha256': 'model', 'bytes': 5}}
        added = {path: {'sha256': str(index), 'bytes': index + 1}
                 for index, path in enumerate(sorted(MODULE.COPY_FILES))}
        after = dict(before, **added)
        MODULE.exactly_five_additions(before, after, added)
        after['Assets/Model.cs'] = {'sha256': 'changed', 'bytes': 7}
        with self.assertRaisesRegex(RuntimeError, 'OnlyFive'):
            MODULE.exactly_five_additions(before, after, added)

    def test_unknown_extra_fixture_and_deletion_are_rejected(self):
        added = {path: {'sha256': path, 'bytes': 1} for path in MODULE.COPY_FILES}
        with self.assertRaisesRegex(RuntimeError, 'OnlyFive'):
            MODULE.exactly_five_additions({}, dict(added, **{'Assets/Other.cs': {'sha256': 'other', 'bytes': 1}}), added)
        with self.assertRaisesRegex(RuntimeError, 'OnlyFive'):
            MODULE.exactly_five_additions({'Assets/Old.cs': {'sha256': 'old', 'bytes': 1}}, added, added)

    def test_fresh_file_with_wrong_bytes_is_rejected(self):
        added = {path: {'sha256': path, 'bytes': 1} for path in MODULE.COPY_FILES}
        after = dict(added)
        after[MODULE.ASSET] = {'sha256': 'corrupted', 'bytes': 1}
        with self.assertRaisesRegex(RuntimeError, 'ExactFive'):
            MODULE.exactly_five_additions({}, after, added)

    def test_native_float_bits_must_match_without_tolerance(self):
        baseline = {key: 1 for key in MODULE.PARITY_FIELDS}
        candidate = dict(baseline)
        self.assertEqual(MODULE.compare_readbacks(baseline, candidate), [])
        candidate['spritePPUBits'] = '42bcb08f'
        self.assertEqual(MODULE.compare_readbacks(baseline, candidate)[0]['field'], 'spritePPUBits')

    def test_missing_native_readback_cannot_be_accepted(self):
        baseline = {key: 1 for key in MODULE.PARITY_FIELDS}
        with self.assertRaisesRegex(RuntimeError, 'CompleteNative'):
            MODULE.compare_readbacks(baseline, {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
