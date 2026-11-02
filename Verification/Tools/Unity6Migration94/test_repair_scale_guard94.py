"""Host guard transformation counterexamples; no project or native operation."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('repair_scale_guard94', Path(__file__).with_name('repair_scale_guard94.py'))
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class ScaleGuardRepairTests(unittest.TestCase):
    def test_exact_previous_guard_roundtrips_to_reviewed_template(self):
        current = MODULE.scale.TEMPLATE.read_bytes()
        old = current.decode().replace(MODULE.NEW_OUTPUT, MODULE.OLD_OUTPUT, 1).replace(
            MODULE.NEW_PREPARED, MODULE.OLD_PREPARED, 1).encode()
        self.assertEqual(MODULE.corrected(old), current)

    def test_duplicate_anchor_is_rejected(self):
        old = (MODULE.OLD_OUTPUT + '\n' + MODULE.OLD_OUTPUT + '\n' + MODULE.OLD_PREPARED).encode()
        with self.assertRaisesRegex(RuntimeError, 'ExactOld'):
            MODULE.corrected(old)

    def test_already_corrected_input_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'ExactOld'):
            MODULE.corrected(MODULE.scale.TEMPLATE.read_bytes())


if __name__ == '__main__': unittest.main(verbosity=2)
