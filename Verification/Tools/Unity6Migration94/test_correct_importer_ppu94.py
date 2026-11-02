"""Host mathematical/transform controls; actual paired-native proof is separate."""
import importlib.util
from pathlib import Path
import unittest

SPEC=importlib.util.spec_from_file_location('correct_importer_ppu94',Path(__file__).with_name('correct_importer_ppu94.py'))
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)


class PPUAssertionControls(unittest.TestCase):
    def test_unscaled_geometry_retains_original_ppu(self):
        self.assertEqual(MODULE.expected_runtime_ppu(100,937,1678,937,1678),100)

    def test_actual_quantized_downsample_matches_native_binary32(self):
        self.assertEqual(MODULE.bits(MODULE.expected_runtime_ppu(100,2170,725,2048,684)),'42bcb08e')

    def test_wrong_width_factor_and_unscaled_assumption_are_rejected(self):
        correct=MODULE.expected_runtime_ppu(100,2170,725,2048,684)
        width_only=MODULE.f32(100*MODULE.f32(2048/2170))
        self.assertGreater(abs(width_only-correct),.001)
        self.assertGreater(abs(100-correct),.001)

    def test_another_quantized_rect_uses_smaller_scale(self):
        self.assertEqual(MODULE.expected_runtime_ppu(100,257,129,128,64),MODULE.f32(100*MODULE.f32(64/129)))

    def test_zero_negative_and_nonfinite_geometry_refused(self):
        for value in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):MODULE.expected_runtime_ppu(100,2170,725,value,684)

    def test_exact_template_correction_preserves_original_border_assertion(self):
        archive=MODULE.CORRECTION.parent/'Template_before.cs'
        before=archive.read_bytes() if archive.is_file() else MODULE.TEMPLATE.read_bytes()
        after=MODULE.transform(before)
        self.assertIn(b'Near(actual.importerBorder, expected.border) && actual.borderMatchesOriginal',after)
        self.assertIn(b'Mathf.Abs(actual.importerPPU - expected.pixelsPerUnit) < .001f',after)
        self.assertNotIn(b'TM_WellRally',after)
        with self.assertRaises(ValueError):MODULE.transform(after)


if __name__=='__main__':unittest.main(verbosity=2)
