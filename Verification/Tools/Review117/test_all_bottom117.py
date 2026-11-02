import collections
import json
from pathlib import Path
import unittest

from fix_all_gap_drafts import LEVELS, adjust, bottom_segment
from propose_nine_row import has_legal_swap, opening_matches

ROOT = Path(__file__).resolve().parents[3]


class AllBottomTests(unittest.TestCase):
    def test_all_candidates_preserve_types_and_use_only_bottom_fixed_owners(self):
        source = ROOT / '.verification-cache/Review117/CampaignVaried03'
        if not source.exists():
            self.skipTest('Generate varied drafts first')
        unique = set()
        for n in LEVELS:
            with self.subTest(level=n):
                before = json.loads((source / f'C01_L{n:03}.json').read_text())
                level, _ = adjust(before)
                active = {(p['x'], p['y']) for p in level['activeCells']}
                self.assertEqual(level['activeCells'], before['activeCells'])
                self.assertEqual(level['spawnPoints'], before['spawnPoints'])
                self.assertEqual(level['deliveryExits'], before['deliveryExits'])
                self.assertEqual(level['deliveryRoutes'], before['deliveryRoutes'])
                self.assertEqual(level['mossRegrowth'], before['mossRegrowth'])
                self.assertEqual(level['movesProposal'], before['movesProposal'])
                self.assertEqual({g['family'] for g in level['goals']}, {g['family'] for g in before['goals']})
                source_ids = {o['instanceId']: o for o in before['obstacles']}
                fixed_segments, occupied, counts = {}, set(), collections.Counter()
                crystal_lanes = {o['x'] for o in level['obstacles'] if o['family'] == 'crystal'}
                for o in level['obstacles']:
                    self.assertIn(o['instanceId'], source_ids)
                    self.assertEqual((o['family'], o['hp']), (source_ids[o['instanceId']]['family'], source_ids[o['instanceId']]['hp']))
                    counts['rainlight' if o['family'] == 'cabinet' else o['family']] += min(4, o['hp']) if o['family'] == 'cabinet' else 1
                    width = 2 if o['family'] == 'cabinet' else 1
                    height = 2 if o['family'] == 'cabinet' else o['hp'] if o['family'] == 'crystal' else 1
                    if o['family'] != 'crystal':
                        self.assertNotIn(o['x'], crystal_lanes)
                    for dx in range(width):
                        if o['family'] not in ('crate', 'pail'):
                            segment = bottom_segment(active, o['x'] + dx, o['y'])
                            self.assertEqual(segment[1], o['y'])
                            self.assertNotIn(segment, fixed_segments)
                            fixed_segments[segment] = o['instanceId']
                        for dy in range(height):
                            pos = (o['x'] + dx, o['y'] + dy)
                            self.assertIn(pos, active)
                            self.assertNotIn(pos, occupied)
                            occupied.add(pos)
                self.assertEqual(dict(counts), {g['family']: g['count'] for g in level['goals']})
                gems = {(p['x'], p['y']): p['color'] for p in level['initialTiles']}
                self.assertEqual(occupied | set(gems), active)
                self.assertFalse(occupied & set(gems))
                self.assertFalse(opening_matches(gems))
                self.assertTrue(has_legal_swap(gems))
                sig = (level['columns'], tuple(sorted(active)),
                       tuple(sorted((o['x'], o['y'], o['family'], o['hp']) for o in level['obstacles'])))
                self.assertNotIn(sig, unique)
                unique.add(sig)


if __name__ == '__main__':
    unittest.main()
