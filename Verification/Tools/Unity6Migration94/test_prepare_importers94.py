"""Host guards for the external geometry oracle and two-file-only preparation."""
import importlib.util
from pathlib import Path
import struct
import unittest

SPEC = importlib.util.spec_from_file_location('prepare_importers94',
    Path(__file__).with_name('prepare_importers94.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ImporterPreparationGuards(unittest.TestCase):
    def test_png_source_dimensions_and_corruption_guard(self):
        raw = b'\x89PNG\r\n\x1a\n' + b'\0\0\0\rIHDR' + struct.pack('>II', 1392, 1130)
        self.assertEqual(MODULE.png_size(raw), (1392, 1130))
        with self.assertRaises(ValueError):
            MODULE.png_size(b'not a PNG')

    def test_effective_pivot_uses_alignment_and_custom_pivot(self):
        self.assertEqual(MODULE.effective_pivot(0, {'x': 0, 'y': 0}), {'x': .5, 'y': .5})
        self.assertEqual(MODULE.effective_pivot(9, {'x': .2, 'y': .7}), {'x': .2, 'y': .7})
        with self.assertRaises(ValueError):
            MODULE.effective_pivot(10, {'x': 0, 'y': 0})

    def test_only_two_exact_new_fixture_files_are_allowed(self):
        before = {'Assets/original.png': {'sha256': 'old', 'bytes': 3}}
        after = dict(before, **{MODULE.RELATIVE: {'sha256': 'template', 'bytes': 5},
                               MODULE.RELATIVE + '.meta': {'sha256': 'meta', 'bytes': 4}})
        MODULE.exact_added_fixture(before, after, 'template', 'meta')
        after['Assets/original.png'] = {'sha256': 'changed', 'bytes': 7}
        with self.assertRaisesRegex(ValueError, 'only the two'):
            MODULE.exact_added_fixture(before, after, 'template', 'meta')

    def test_unknown_new_asset_is_rejected(self):
        after = {MODULE.RELATIVE: {'sha256': 'template', 'bytes': 5},
                 MODULE.RELATIVE + '.meta': {'sha256': 'meta', 'bytes': 4},
                 'Assets/Unapproved.cs': {'sha256': 'unknown', 'bytes': 5}}
        with self.assertRaisesRegex(ValueError, 'only the two'):
            MODULE.exact_added_fixture({}, after, 'template', 'meta')

    def test_fixture_with_unreviewed_extra_code_is_rejected(self):
        after = {MODULE.RELATIVE: {'sha256': 'wrong', 'bytes': 5},
                 MODULE.RELATIVE + '.meta': {'sha256': 'meta', 'bytes': 4}}
        with self.assertRaisesRegex(ValueError, 'hashes differ'):
            MODULE.exact_added_fixture({}, after, 'template', 'meta')


if __name__ == '__main__':
    unittest.main(verbosity=2)
