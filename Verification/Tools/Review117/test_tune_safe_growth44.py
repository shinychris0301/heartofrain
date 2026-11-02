import json
from pathlib import Path
import unittest

from tune_safe_growth44 import tune
from propose_nine_row import has_legal_swap, opening_matches

ROOT=Path(__file__).resolve().parents[3]


class SafeGrowthTuningTests(unittest.TestCase):
    def test_adds_safe_growth_options_without_changing_mask_or_policy(self):
        p=ROOT/'.verification-cache/Review117/CampaignSafeGrowth01/C01_L044.json'
        if not p.exists():self.skipTest('Stage opted-in draft first')
        before=json.loads(p.read_text());after,detail=tune(before)
        self.assertEqual(after['activeCells'],before['activeCells'])
        self.assertEqual(after['spawnPoints'],before['spawnPoints'])
        self.assertEqual(after['movesProposal'],before['movesProposal'])
        self.assertEqual(after['mossRegrowth'],before['mossRegrowth'])
        self.assertEqual(detail['newMossGoal'],detail['oldMossGoal']-2)
        active={(p['x'],p['y']) for p in after['activeCells']}
        moss={(p['x'],p['y']) for p in after['obstacles'] if p['family']=='moss'}
        gems={(p['x'],p['y']):p['color'] for p in after['initialTiles']}
        for p in ((2,0),(7,0)):
            self.assertIn(p,gems)
            self.assertNotIn((p[0],p[1]-1),active)
            self.assertTrue(any((p[0]+dx,p[1]+dy) in moss for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))))
        self.assertFalse(opening_matches(gems));self.assertTrue(has_legal_swap(gems))


if __name__=='__main__':unittest.main()
