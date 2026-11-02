import json
from pathlib import Path
import unittest

from board_mosaic117 import donors, generate, pixel_diff, PAD, PITCH

ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / 'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117'


class BoardMosaicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index, cls.images = donors(ROOT)

    def test_three_original_sizes_reconstruct_exact_pixels(self):
        for n in (1, 11, 21):
            with self.subTest(level=n):
                level = json.loads((LEGACY / f'C01_L{n:03}.json').read_text(encoding='utf-8-sig'))
                actual = generate(level, self.index, self.images)
                for got, expected in zip(actual, self.images[n]):
                    self.assertEqual(pixel_diff(got, expected), 0)

    def test_new_widths_keep_cell_centers_aligned_with_mask(self):
        folder = ROOT / '.verification-cache/Review117/CampaignVaried03'
        if not folder.exists():
            self.skipTest('Generate local candidate drafts first')
        for n in (11, 22, 21):
            with self.subTest(level=n):
                level = json.loads((folder / f'C01_L{n:03}.json').read_text())
                surface, mask = generate(level, self.index, self.images)
                self.assertEqual(surface.size, (level['columns'] * 64 + 30, 9 * 64 + 30))
                active = {(c['x'], c['y']) for c in level['activeCells']}
                for y in range(9):
                    for x in range(level['columns']):
                        center = (PAD + x * PITCH + PITCH // 2,
                                  PAD + (8 - y) * PITCH + PITCH // 2)
                        alpha = mask.getpixel(center)[3]
                        self.assertEqual(alpha == 255, (x, y) in active)


if __name__ == '__main__':
    unittest.main()
