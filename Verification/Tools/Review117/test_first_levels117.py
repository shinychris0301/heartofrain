import collections
import json
from pathlib import Path
import unittest

from fix_all_gap_drafts import bottom_segment
from propose_nine_row import has_legal_swap, opening_matches

ROOT=Path(__file__).resolve().parents[3]


class FirstLevelsTests(unittest.TestCase):
    def test_first_nine_keep_contract_and_bottom_fixed_geometry(self):
        draftdir=ROOT/'.verification-cache/Review117/FirstLevelsDraft01'
        if not draftdir.exists():self.skipTest('Stage first-level drafts first')
        legacy=ROOT/'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117'
        for n in range(1,10):
            with self.subTest(level=n):
                name=f'C01_L{n:03}.json';old=json.loads((legacy/name).read_text(encoding='utf-8-sig'));d=json.loads((draftdir/name).read_text())
                for key in ('id','globalLevel','rows','columns','activeCells','spawnPoints','movesProposal','storyBeat','introduces','introducedFamilies','mossRegrowth'):
                    self.assertEqual(d.get(key),old.get(key),key)
                self.assertEqual({g['family'] for g in d['goals']},{g['family'] for g in old['goals']})
                active={(p['x'],p['y']) for p in d['activeCells']};gems={(g['x'],g['y']):g['color'] for g in d['initialTiles']}
                fixed={};occupied=set();counts=collections.Counter();old_ids={o['instanceId']:o for o in old['obstacles']}
                for o in d['obstacles']:
                    self.assertIn(o['instanceId'],old_ids);self.assertEqual((o['family'],o['hp']),(old_ids[o['instanceId']]['family'],old_ids[o['instanceId']]['hp']))
                    counts[o['family']]+=1;pos=(o['x'],o['y']);self.assertIn(pos,active);self.assertNotIn(pos,occupied);occupied.add(pos)
                    if o['family']!='crate':
                        segment=bottom_segment(active,*pos);self.assertEqual(segment[1],pos[1]);self.assertNotIn(segment,fixed);fixed[segment]=o['instanceId']
                self.assertEqual(dict(counts),{g['family']:g['count'] for g in d['goals']})
                self.assertEqual(occupied|set(gems),active);self.assertFalse(occupied&set(gems))
                self.assertFalse(opening_matches(gems));self.assertTrue(has_legal_swap(gems))


if __name__=='__main__':unittest.main()
