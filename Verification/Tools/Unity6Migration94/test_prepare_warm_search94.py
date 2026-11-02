"""Host-only narrow proposal guards; never apply a template or execute Unity."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('warm_search94_proposal_guard', Path(__file__).with_name('prepare_warm_search94.py'))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class WarmSearchProposalGuards(unittest.TestCase):
    def setUp(self):
        self.original = (api.OUT / 'Before.cs').read_bytes()

    def test_prepared_full_after_is_reproducible(self):
        self.assertEqual(api.transform(self.original), (api.OUT / 'After.cs').read_bytes())

    def test_existing_configure_and_build_implementation_is_byte_preserved(self):
        marker = b'        static void Run(string operation, bool configure, bool? nonDevelopment)'
        after = api.transform(self.original)
        self.assertEqual(after[after.index(marker):], self.original[self.original.index(marker):])

    def test_repeated_application_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'ExactUnmodifiedWarmSearchAnchorsRequired'):
            api.transform(api.transform(self.original))

    def test_unexpected_report_shape_is_refused(self):
        altered = self.original.replace(b'            public Settings before, after;', b'            public Settings unexpected;')
        with self.assertRaisesRegex(RuntimeError, 'ExactUnmodifiedWarmSearchAnchorsRequired'):
            api.transform(altered)


if __name__ == '__main__':
    unittest.main()
