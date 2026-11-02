"""Generate limited, non-deployable 9x9 layout candidates for inspection.

Only 9-column boards whose top two rows contain no objective footprints or
delivery route are considered. No authored file or server catalog is edited.
The emitted drafts still require the production Unity validator, gameplay and
balance review and versioned persistence; they are not release candidates.
"""
import argparse
import copy
import json
from pathlib import Path


def opening_matches(gems):
    for (x, y), color in gems.items():
        for dx, dy in ((1, 0), (0, 1)):
            if all(gems.get((x + dx * n, y + dy * n)) == color for n in (1, 2)):
                return True
        if all(gems.get((x + dx, y + dy)) == color for dx, dy in ((1, 0), (0, 1), (1, 1))):
            return True
    return False


def has_legal_swap(gems):
    for x, y in gems:
        for target in ((x + 1, y), (x, y + 1)):
            if target not in gems:
                continue
            copy_gems = dict(gems)
            copy_gems[(x, y)], copy_gems[target] = copy_gems[target], copy_gems[(x, y)]
            if opening_matches(copy_gems):
                return True
    return False


def make_candidate(level):
    if (level['columns'], level['rows']) != (9, 11):
        return None, 'not_nine_columns_and_eleven_rows'
    if level.get('initialPowerUps'):
        return None, 'initial_powerups_require_manual_review'
    for obstacle in level['obstacles']:
        family = obstacle['family']
        height = 2 if family == 'cabinet' else obstacle['hp'] if family == 'crystal' else 1
        if obstacle['y'] + height > 9:
            return None, 'objective_footprint_above_row8'
    for route in level.get('deliveryRoutes', []):
        if any(point['y'] >= 9 for point in [route['start'], route['exit']] + route['cells']):
            return None, 'delivery_route_above_row8'
    if any(exit['y'] >= 9 for exit in level['deliveryExits']):
        return None, 'delivery_exit_above_row8'

    result = copy.deepcopy(level)
    active_original = {(p['x'], p['y']) for p in result['activeCells']}
    result['rows'] = 9
    result['activeCells'] = [p for p in result['activeCells'] if p['y'] < 9]
    result['initialTiles'] = [p for p in result['initialTiles'] if p['y'] < 9]
    spawns = set()
    for point in result['spawnPoints']:
        x, y = point['x'], point['y']
        if y < 9:
            spawns.add((x, y))
        elif all((x, yy) in active_original for yy in range(8, y + 1)):
            spawns.add((x, 8))
    result['spawnPoints'] = [{'x': x, 'y': y} for x, y in sorted(spawns)]
    for formation in result.get('formations', []):
        formation['cells'] = [p for p in formation.get('cells', []) if p['y'] < 9]
    # The package's balance metrics are historical, not valid for this draft.
    result['validation'] = {'status': 'DRAFT_NOT_VALIDATED'}
    result['metrics'] = {'status': 'DRAFT_RECALCULATION_REQUIRED'}
    result['revision'] = 'DRAFT Review117; not approved or validated for release'

    cells = {(p['x'], p['y']) for p in result['activeCells']}
    gems = {(p['x'], p['y']): p['color'] for p in result['initialTiles']}
    if (len(cells) != len(result['activeCells']) or
            len(gems) != len(result['initialTiles']) or not set(gems).issubset(cells) or
            not spawns.issubset(cells)):
        return None, 'invalid_gem_positions'
    obstacle_cells = set()
    for o in result['obstacles']:
        width = 2 if o['family'] == 'cabinet' else 1
        height = 2 if o['family'] == 'cabinet' else o['hp'] if o['family'] == 'crystal' else 1
        for dy in range(height):
            for dx in range(width):
                cell = (o['x'] + dx, o['y'] + dy)
                if cell not in cells or cell in obstacle_cells or cell in gems:
                    return None, 'invalid_obstacle_footprint'
                obstacle_cells.add(cell)
    if cells != obstacle_cells | set(gems):
        return None, 'unfilled_active_cells'
    if opening_matches(gems):
        return None, 'opening_match'
    if not has_legal_swap(gems):
        return None, 'no_opening_swap'
    return result, 'static_preflight_pass_not_playtest'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    allowed = (root / '.verification-cache').resolve()
    if not output.is_relative_to(allowed) or output == allowed or output.exists():
        raise ValueError('Output must be a new directory inside .verification-cache')
    output.mkdir(parents=True)
    results = []
    for n in range(11, 51):
        src = root / f'Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L{n:03}.json'
        level = json.loads(src.read_text(encoding='utf-8-sig'))
        candidate, status = make_candidate(level)
        if candidate is not None:
            (output / src.name).write_text(json.dumps(candidate, indent=2) + '\n', encoding='utf-8')
        results.append({'level': n, 'status': status})
    report = {'scope': 'Static draft only; not Unity, gameplay, replay, balance or device verification.',
              'candidates': sum(r['status'].startswith('static_preflight_pass') for r in results),
              'levels': results}
    (output / 'Report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
