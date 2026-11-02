import hashlib
import unittest

from audit_board_geometry import audit_level, layout


class BoardGeometryAuditTests(unittest.TestCase):
    def test_detects_unmappable_geometry_and_catalog_mismatch(self):
        source = b'level'
        level = {
            'globalLevel': 1, 'id': 'fixture', 'rows': 11, 'columns': 11,
            'activeCells': [{'x': i % 11, 'y': i // 11} for i in range(110)],
            'initialTiles': [{'x': 0, 'y': 9}],
            'obstacles': [{'family': 'crystal', 'x': 0, 'y': 1, 'hp': 9,
                           'footprint': {'height': 9}},
                          {'family': 'crate', 'x': 1, 'y': 10}],
            'spawnPoints': [{'x': 1, 'y': 10}], 'deliveryExits': [],
            'deliveryRoutes': [{'start': {'x': 0, 'y': 9}, 'exit': {'x': 0, 'y': 0},
                                'cells': [{'x': 0, 'y': 9}]}],
        }
        digest = hashlib.sha256(source).hexdigest()
        result = audit_level(level, source, {'sourceSHA256': digest, 'configHash': 'wrong'})
        self.assertTrue(result['exceeds9x11Capacity'])
        self.assertEqual(result['initialTilesAboveRow8'], 1)
        self.assertEqual(result['obstacleAnchorsAboveRow8'], 1)
        self.assertEqual(len(result['obstacleFootprintsCrossingRow8']), 1)
        self.assertEqual(result['deliveryRoutesAboveRow8'], [0])
        self.assertFalse(result['catalogMatches'])

    def test_portrait_width_limits_both_11_column_boards(self):
        self.assertEqual(layout(720, 1600, 11, 11), layout(720, 1600, 11, 9))
        self.assertEqual(layout(720, 1600, 9, 11), layout(720, 1600, 9, 9))
        self.assertGreater(layout(720, 1600, 9, 9), layout(720, 1600, 11, 9))


if __name__ == '__main__':
    unittest.main()
