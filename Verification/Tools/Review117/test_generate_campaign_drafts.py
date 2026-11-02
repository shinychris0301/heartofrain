import collections
import json
from pathlib import Path
import unittest

from generate_campaign_drafts import candidate, dimensions
from propose_nine_row import has_legal_swap, opening_matches

ROOT = Path(__file__).resolve().parents[3]


class CampaignDraftTests(unittest.TestCase):
    def test_all_40_candidate_shapes_goals_and_routes(self):
        masks = set()
        for n in range(11, 51):
            with self.subTest(level=n):
                path = ROOT / f'Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L{n:03}.json'
                original = json.loads(path.read_text(encoding='utf-8-sig'))
                draft, info = candidate(original)
                self.assertEqual((draft['columns'], draft['rows']), (9, 9))
                self.assertEqual({g['family'] for g in original['goals']}, {g['family'] for g in draft['goals']})
                cells = {(p['x'], p['y']) for p in draft['activeCells']}
                self.assertEqual(len(cells), len(draft['activeCells']))
                self.assertTrue(all(0 <= x < 9 and 0 <= y < 9 for x, y in cells))
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

    def test_determinism_for_fixed_salt(self):
        path = ROOT / 'Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L050.json'
        source = json.loads(path.read_text(encoding='utf-8-sig'))
        self.assertEqual(candidate(source), candidate(source))


if __name__ == '__main__':
    unittest.main()
