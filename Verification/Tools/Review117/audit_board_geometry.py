"""Read-only audit for the proposed 9-row Chapter 1 migration.

This does not reauthor levels, test playability, or change a campaign catalog.
"""
import argparse
import hashlib
import json
from pathlib import Path


def audit_level(level, source_bytes, catalog):
    rows = level['rows']
    columns = level['columns']
    active = level['activeCells']
    obstacles = level['obstacles']
    # Match the production model's initial multi-cell obstacle footprints.
    obstacle_cells = sum(4 if o['family'] == 'cabinet' else
                         o['hp'] if o['family'] == 'crystal' else 1
                         for o in obstacles)
    crossed = []
    for obstacle in obstacles:
        height = obstacle.get('footprint', {}).get('height', 1)
        if obstacle['y'] < 9 < obstacle['y'] + height:
            crossed.append({'family': obstacle['family'], 'x': obstacle['x'],
                            'y': obstacle['y'], 'height': height})
    routes = []
    for index, route in enumerate(level.get('deliveryRoutes', [])):
        if any(point['y'] >= 9 for point in
               [route['start'], route['exit']] + route['cells']):
            routes.append(index)
    digest = hashlib.sha256(source_bytes).hexdigest()
    return {
        'level': level['globalLevel'], 'id': level['id'],
        'rows': rows, 'columns': columns, 'activeCells': len(active),
        'initialObstacleFootprintCells': obstacle_cells,
        'minimumOccupancyOn9x9Percent': obstacle_cells * 100.0 / 81,
        'maximumGemCellsOn9x9': max(0, 81 - obstacle_cells),
        'exceeds9x11Capacity': len(active) > 99,
        'cellsAboveRow8': sum(c['y'] >= 9 for c in active),
        'initialTilesAboveRow8': sum(c['y'] >= 9 for c in level['initialTiles']),
        'obstacleAnchorsAboveRow8': sum(c['y'] >= 9 for c in obstacles),
        'obstacleFootprintsCrossingRow8': crossed,
        'spawnPointsAboveRow8': sum(c['y'] >= 9 for c in level['spawnPoints']),
        'deliveryExitsAboveRow8': sum(c['y'] >= 9 for c in level['deliveryExits']),
        'deliveryRoutesAboveRow8': routes,
        'sourceSHA256': digest,
        'catalogMatches': catalog['sourceSHA256'] == digest and catalog['configHash'] == digest,
    }


def layout(width, height, columns, rows):
    logical_height = height * 720.0 / width
    return min(676.0 / columns, (logical_height - 460.0) / rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    catalog = json.loads((root / 'Backend/config/levels.json').read_text(encoding='utf-8'))
    if len(catalog['levels']) != 50:
        raise ValueError('Expected 50 catalog levels')
    result = []
    for n in range(1, 51):
        path = root / f'Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L{n:03}.json'
        data = path.read_bytes()
        level = json.loads(data.decode('utf-8-sig'))
        entry = catalog['levels'][n - 1]
        if level['globalLevel'] != n or entry['level'] != n:
            raise ValueError('Unexpected level order')
        result.append(audit_level(level, data, entry))
    board_11x11 = layout(720, 1600, 11, 11)
    board_11x9 = layout(720, 1600, 11, 9)
    board_9x11 = layout(720, 1600, 9, 11)
    board_9x9 = layout(720, 1600, 9, 9)
    report = {
        'scope': 'Read-only authored-data and layout calculation; no runtime, device, migration or playability verification.',
        'levels': result,
        'summary': {
            'total': len(result), 'alreadyNineRows': sum(x['rows'] == 9 for x in result),
            'aboveNineRows': sum(x['rows'] > 9 for x in result),
            'outside9to11Columns': sum(not 9 <= x['columns'] <= 11 for x in result),
            'over9x11Capacity': sum(x['exceeds9x11Capacity'] for x in result),
            'topRowSpawnAffected': sum(x['spawnPointsAboveRow8'] > 0 for x in result),
            'topRowObstacleAnchorsAffected': sum(x['obstacleAnchorsAboveRow8'] > 0 for x in result),
            'crossBoundaryFootprints': sum(len(x['obstacleFootprintsCrossingRow8']) for x in result),
            'affectedDeliveryRoutes': sum(len(x['deliveryRoutesAboveRow8']) for x in result),
            'catalogMatches': sum(x['catalogMatches'] for x in result),
        },
        'layoutCalculation720x1600': {
            '11x11CellLogical': board_11x11, '11x9CellLogical': board_11x9,
            '9x11CellLogical': board_9x11,
            '9x9CellLogical': board_9x9,
            'gain9x9Vs11x11Percent': 100 * (board_9x9 / board_11x11 - 1),
        },
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
