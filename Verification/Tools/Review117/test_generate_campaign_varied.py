import collections
import json
from pathlib import Path
import unittest

from generate_campaign_varied import candidate, dimensions
from place_blockers_low import caps
from propose_nine_row import has_legal_swap, opening_matches

ROOT = Path(__file__).resolve().parents[3]


class CampaignDraftTests(unittest.TestCase):
    def test_all_40_candidate_shapes_goals_and_routes(self):
        masks = set()
        widths = set()
        for n in range(11, 51):
            with self.subTest(level=n):
                path = ROOT / f'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/C01_L{n:03}.json'
                original = json.loads(path.read_text(encoding='utf-8-sig'))
                draft, info = candidate(original)
                self.assertEqual(draft['rows'], 9)
                self.assertIn(draft['columns'], (9, 10, 11))
                widths.add(draft['columns'])
                self.assertEqual({g['family'] for g in original['goals']}, {g['family'] for g in draft['goals']})
                cells = {(p['x'], p['y']) for p in draft['activeCells']}
                self.assertEqual(len(cells), len(draft['activeCells']))
                self.assertTrue(all(0 <= x < draft['columns'] and 0 <= y < 9 for x, y in cells))
                masks.add(tuple(sorted(cells)))
                occupied = set()
                counts = collections.Counter()
                original_obstacles = {o['instanceId']: o for o in original['obstacles']}
                for o in draft['obstacles']:
                    self.assertIn(o['instanceId'], original_obstacles)
                    self.assertEqual(o['family'], original_obstacles[o['instanceId']]['family'])
                    self.assertEqual(o['hp'], original_obstacles[o['instanceId']]['hp'])
                    width, height = dimensions(o)
                    for dx in range(width):
                        for dy in range(height):
                            pos = (o['x'] + dx, o['y'] + dy)
                            self.assertIn(pos, cells)
                            self.assertNotIn(pos, occupied)
                            occupied.add(pos)
                    counts['rainlight' if o['family'] == 'cabinet' else o['family']] += min(4, o['hp']) if o['family'] == 'cabinet' else 1
                self.assertEqual({g['family']: g['count'] for g in draft['goals']}, dict(counts))
                self.assertLessEqual(100 * len(occupied) / len(cells), info['coverageCapPercent'])
                gems = {(g['x'], g['y']): g['color'] for g in draft['initialTiles']}
                self.assertEqual(len(gems), len(draft['initialTiles']))
                self.assertEqual(occupied | set(gems), cells)
                self.assertFalse(opening_matches(gems))
                self.assertTrue(has_legal_swap(gems))
                spawns = {(s['x'], s['y']) for s in draft['spawnPoints']}
                self.assertEqual(spawns, {(x, y) for x, y in cells if (x, y + 1) not in cells})
                pails = {(o['x'], o['y']) for o in draft['obstacles'] if o['family'] == 'pail'}
                self.assertEqual(pails, {(r['start']['x'], r['start']['y']) for r in draft['deliveryRoutes']})
                for r in draft['deliveryRoutes']:
                    x, start, exit_y = r['start']['x'], r['start']['y'], r['exit']['y']
                    self.assertEqual(x, r['exit']['x'])
                    self.assertGreater(start, exit_y)
                    self.assertEqual(r['cells'], [{'x': x, 'y': y} for y in range(exit_y, start + 1)])
                    self.assertTrue(all((x, y) in cells for y in range(exit_y, start + 1)))
        self.assertGreaterEqual(len(masks), 20)
        self.assertEqual(widths, {9, 10, 11})

    def test_determinism_for_fixed_salt(self):
        path = ROOT / 'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/C01_L050.json'
        source = json.loads(path.read_text(encoding='utf-8-sig'))
        self.assertEqual(candidate(source), candidate(source))

    def test_level17_fixed_pieces_do_not_cap_initial_gem_column(self):
        path = ROOT / 'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/C01_L017.json'
        original = json.loads(path.read_text(encoding='utf-8-sig'))
        draft, _ = candidate(original, bottom_fixed=True)
        gems = {(g['x'], g['y']) for g in draft['initialTiles']}
        for obstacle in draft['obstacles']:
            if obstacle['family'] not in ('crate', 'pail'):
                self.assertFalse(any(x == obstacle['x'] and y < obstacle['y'] for x, y in gems),
                                 f"fixed {obstacle['family']} at {obstacle['x']},{obstacle['y']} caps lower gem")
        self.assertEqual({g['family'] for g in draft['goals']}, {g['family'] for g in original['goals']})

    def test_all_low_fixed_drafts_keep_only_top_sources(self):
        configurations = set()
        for n in range(11, 51):
            with self.subTest(level=n):
                path = ROOT / f'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/C01_L{n:03}.json'
                original = json.loads(path.read_text(encoding='utf-8-sig'))
                baseline, _ = candidate(original)
                draft, _ = candidate(original, bottom_fixed=True)
                self.assertEqual(draft['goals'], baseline['goals'])
                self.assertEqual(caps(draft), [])
                active = {(p['x'], p['y']) for p in draft['activeCells']}
                self.assertEqual({(p['x'], p['y']) for p in draft['spawnPoints']},
                                 {(x, y) for x, y in active if (x, y + 1) not in active})
                signature = (draft['columns'], tuple(sorted(active)),
                             tuple(sorted((o['x'], o['y'], o['family'], o['hp']) for o in draft['obstacles'])))
                self.assertNotIn(signature, configurations)
                configurations.add(signature)


if __name__ == '__main__':
    unittest.main()
