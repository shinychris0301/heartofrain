import json
from pathlib import Path
import unittest

from fix_gap_drafts import LEVELS, adjust, bottom_segment
from propose_nine_row import opening_matches, has_legal_swap

ROOT = Path(__file__).resolve().parents[3]


class GapVariantTests(unittest.TestCase):
    def test_single_fixed_body_per_active_segment_on_observed_levels(self):
        folder = ROOT / '.verification-cache/Review117/CampaignVaried03'
        if not folder.exists():
            self.skipTest('Generate varied drafts first')
        for n in LEVELS:
            with self.subTest(level=n):
                original = json.loads((folder / f'C01_L{n:03}.json').read_text())
                draft, _ = adjust(original)
                active = {(c['x'], c['y']) for c in draft['activeCells']}
                self.assertEqual(draft['activeCells'], original['activeCells'])
                self.assertEqual(draft['spawnPoints'], original['spawnPoints'])
                self.assertEqual(draft['movesProposal'], original['movesProposal'])
                self.assertFalse(draft.get('mossRegrowth', {}).get('enabled'))
                self.assertEqual({g['family'] for g in draft['goals']}, {g['family'] for g in original['goals']})
                owners = {}
                for o in draft['obstacles']:
                    if o['family'] == 'crate':
                        continue
                    width = 2 if o['family'] == 'cabinet' else 1
                    height = 2 if o['family'] == 'cabinet' else 1
                    for dx in range(width):
                        seg = bottom_segment(active, o['x'] + dx, o['y'])
                        self.assertEqual(seg[1], o['y'])
                        self.assertNotIn(seg, owners)
                        owners[seg] = o['instanceId']
                        self.assertTrue(all((o['x'] + dx, o['y'] + dy) in active for dy in range(height)))
                gems = {(p['x'], p['y']): p['color'] for p in draft['initialTiles']}
                self.assertFalse(opening_matches(gems))
                self.assertTrue(has_legal_swap(gems))


if __name__ == '__main__':
    unittest.main()
