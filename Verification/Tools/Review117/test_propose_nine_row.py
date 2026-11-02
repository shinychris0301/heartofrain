import copy
import json
from pathlib import Path
import unittest

from propose_nine_row import make_candidate, opening_matches, has_legal_swap


ROOT = Path(__file__).resolve().parents[3]


class CandidateTests(unittest.TestCase):
    def test_eligible_level_preserves_goals_and_obstacle_identity(self):
        path = ROOT / 'Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L011.json'
        source = json.loads(path.read_text(encoding='utf-8-sig'))
        before = copy.deepcopy(source)
        candidate, status = make_candidate(source)
        self.assertEqual(source, before)
        self.assertEqual(status, 'static_preflight_pass_not_playtest')
        self.assertEqual((candidate['columns'], candidate['rows']), (9, 9))
        self.assertEqual(candidate['goals'], source['goals'])
        self.assertEqual(candidate['obstacles'], source['obstacles'])
        self.assertEqual(candidate['deliveryRoutes'], source['deliveryRoutes'])
        self.assertTrue(all(p['y'] < 9 for p in candidate['spawnPoints']))
        self.assertEqual(candidate['validation']['status'], 'DRAFT_NOT_VALIDATED')

    def test_rejects_top_objective_or_route_instead_of_discarding_it(self):
        path = ROOT / 'Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L011.json'
        level = json.loads(path.read_text(encoding='utf-8-sig'))
        level['obstacles'].append({'family': 'crate', 'hp': 1, 'x': 0, 'y': 9})
        self.assertEqual(make_candidate(level), (None, 'objective_footprint_above_row8'))
        level['obstacles'].pop()
        level['deliveryRoutes'][0]['cells'].append({'x': 0, 'y': 9})
        self.assertEqual(make_candidate(level), (None, 'delivery_route_above_row8'))

    def test_opening_checker_includes_squares_and_swap_creation(self):
        self.assertTrue(opening_matches({(0, 0): 1, (1, 0): 1, (0, 1): 1, (1, 1): 1}))
        tiles = {(0, 0): 0, (1, 0): 1, (2, 0): 0, (1, 1): 0}
        self.assertFalse(opening_matches(tiles))
        self.assertTrue(has_legal_swap(tiles))


if __name__ == '__main__':
    unittest.main()
