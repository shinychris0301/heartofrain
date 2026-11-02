"""Propose 9x9 campaign layouts into a new ignored cache directory.

Candidates preserve every objective family but provisionally reduce counts to
the original coverage cap. They are NOT validated by Unity, human play, replay,
backend compatibility or device testing, and must not be shipped as-is.
"""
import argparse
import collections
import copy
import hashlib
import json
import math
import random
from pathlib import Path

from propose_nine_row import opening_matches, has_legal_swap


def dimensions(o):
    if o['family'] == 'cabinet':
        return 2, 2
    if o['family'] == 'crystal':
        return 1, o['hp']
    return 1, 1


def projected(x, y, columns):
    return round(x * 8 / (columns - 1)), round(y * 8 / 10)


def select_obstacles(obstacles, capacity):
    groups = collections.defaultdict(list)
    for o in obstacles:
        groups[o['family']].append(o)
    for values in groups.values():
        values.sort(key=lambda o: (o['y'], o['x'], o.get('instanceId', '')))
    # Delivery targets and unique multi-cell objects remain intact. Each
    # ordinary family retains at least one representative.
    quotas = {f: len(items) if f in ('pail', 'cabinet', 'crystal') else 1
              for f, items in groups.items()}
    def cost():
        return sum(quotas[f] * math.prod(dimensions(items[0])) for f, items in groups.items())
    if cost() > capacity:
        raise ValueError('mandatory_families_exceed_coverage_cap')
    while True:
        options = [f for f, items in groups.items()
                   if quotas[f] < len(items) and cost() + math.prod(dimensions(items[0])) <= capacity]
        if not options:
            break
        family = min(options, key=lambda f: (quotas[f] / len(groups[f]), f))
        quotas[family] += 1
    result = []
    for f, items in sorted(groups.items()):
        count = quotas[f]
        indices = [min(len(items) - 1, int((i + .5) * len(items) / count)) for i in range(count)]
        result.extend(copy.deepcopy(items[i]) for i in indices)
    return result


def candidate(level, salt=0):
    if level['rows'] != 11 or level['columns'] not in (9, 11) or level.get('initialPowerUps'):
        raise ValueError('unsupported_source')
    width = level['columns']
    active = {projected(p['x'], p['y'], width) for p in level['activeCells']}
    if len(active) < 20:
        raise ValueError('mask_too_small')
    metrics = level.get('metrics', {})
    cap = float(metrics.get('coverageCapPercent') or min(64, max(42, math.ceil(metrics.get('coveragePercent', 56) + 2))))
    cap = min(64, max(35, cap))
    budget = math.floor(len(active) * cap / 100)
    selected = select_obstacles(level['obstacles'], budget)
    selected.sort(key=lambda o: ({'crystal': 0, 'cabinet': 1, 'pail': 2}.get(o['family'], 3), o['y'], o['x']))
    occupied = set()
    exits = set()
    routes = []
    placed = []
    seed = level['globalLevel'] * 1009 + salt * 2027
    tie = random.Random(seed)
    # A stable per-cell order gives multiple candidate attempts without
    # nondeterminism across machines.
    tie_value = {(x, y): tie.random() for x in range(9) for y in range(9)}
    for old in selected:
        o = copy.deepcopy(old)
        px, py = projected(o['x'], o['y'], width)
        w, h = dimensions(o)
        positions = [(x, y) for x in range(10 - w) for y in range(10 - h)]
        if o['family'] == 'crystal':
            positions = [(x, 0) for x in (0, 8)]
        positions.sort(key=lambda xy: (abs(xy[0] - px) + abs(xy[1] - py), tie_value[xy]))
        location = None
        if o['family'] == 'pail':
            source_route = next((r for r in level.get('deliveryRoutes', [])
                                 if r['start']['x'] == old['x'] and r['start']['y'] == old['y']), None)
            if source_route is None:
                raise ValueError('missing_pail_route')
            ex, ey = projected(source_route['exit']['x'], source_route['exit']['y'], width)
            positions.sort(key=lambda xy: (abs(xy[0] - ex) * 4 + abs(xy[1] - py), tie_value[xy]))
            for x, y in positions:
                if y <= ey or (x, y) in occupied or (x, ey) in exits:
                    continue
                route_cells = {(x, yy) for yy in range(ey, y + 1)}
                if route_cells & occupied:
                    continue
                location = (x, y)
                active.update(route_cells)
                exits.add((x, ey))
                routes.append({'start': {'x': x, 'y': y}, 'exit': {'x': x, 'y': ey},
                               'cells': [{'x': x, 'y': yy} for yy in range(ey, y + 1)]})
                break
        else:
            # Prefer existing mask cells. For large objects only, add missing
            # cells when required to preserve the full object footprint.
            positions.sort(key=lambda xy: (sum((xy[0] + dx, xy[1] + dy) not in active
                                                for dx in range(w) for dy in range(h)),
                                           abs(xy[0] - px) + abs(xy[1] - py), tie_value[xy]))
            for x, y in positions:
                footprint = {(x + dx, y + dy) for dx in range(w) for dy in range(h)}
                if footprint & occupied or (w == 1 and h == 1 and (x, y) not in active):
                    continue
                location = (x, y)
                active.update(footprint)
                break
        if location is None:
            raise ValueError('unable_to_place_' + o['family'])
        o['x'], o['y'] = location
        occupied.update((o['x'] + dx, o['y'] + dy) for dx in range(w) for dy in range(h))
        placed.append(o)
    # Crystal owners must have an exposed bottom and not be enclosed on both
    # sides at their anchor, exactly as the live model requires.
    for o in placed:
        if o['family'] == 'crystal':
            x, y = o['x'], o['y']
            if (x, y - 1) in active or ((x - 1, y) in active and (x + 1, y) in active):
                raise ValueError('invalid_crystal_anchor')
    if len(occupied) > math.floor(len(active) * cap / 100):
        raise ValueError('coverage_cap_exceeded')
    gems_cells = sorted(active - occupied, key=lambda p: (p[1], p[0]))
    palette = level['activeColors']
    if len(palette) < 3:
        raise ValueError('palette_too_small')
    gem_colors = None
    for attempt in range(1200):
        rng = random.Random(seed * 1301 + attempt)
        trial = {}
        for cell in gems_cells:
            colors = list(palette)
            rng.shuffle(colors)
            for color in colors:
                trial[cell] = color
                if not opening_matches(trial):
                    break
            else:
                break
        if len(trial) == len(gems_cells) and not opening_matches(trial) and has_legal_swap(trial):
            gem_colors = trial
            break
    if gem_colors is None:
        raise ValueError('no_valid_initial_gem_arrangement')
    goals = copy.deepcopy(level['goals'])
    counts = collections.Counter()
    for o in placed:
        family = 'rainlight' if o['family'] == 'cabinet' else o['family']
        counts[family] += min(4, o['hp']) if o['family'] == 'cabinet' else 1
    if set(counts) != {g['family'] for g in goals}:
        raise ValueError('goal_families_changed')
    for goal in goals:
        goal['count'] = counts[goal['family']]
    result = copy.deepcopy(level)
    result.update(rows=9, columns=9, activeCells=[{'x': x, 'y': y} for x, y in sorted(active)],
                  initialTiles=[{'x': x, 'y': y, 'color': gem_colors[(x, y)]} for x, y in gems_cells],
                  obstacles=placed, goals=goals, deliveryExits=[{'x': x, 'y': y} for x, y in sorted(exits)],
                  deliveryRoutes=routes)
    # Spawn at each topmost contiguous active segment, including mask islands.
    result['spawnPoints'] = [{'x': x, 'y': y} for x, y in sorted(active) if (x, y + 1) not in active]
    result['formations'] = []
    result['metrics'] = {'status': 'DRAFT_RECALCULATION_REQUIRED', 'activeCells': len(active),
                         'occupiedObstacleCells': len(occupied),
                         'coveragePercent': round(100 * len(occupied) / len(active), 2),
                         'coverageCapPercent': cap}
    result['validation'] = {'status': 'DRAFT_NOT_VALIDATED'}
    result['balancePass'] = {'status': 'DRAFT_NOT_VALIDATED', 'scope': 'Provisional count changes; no human playability or difficulty assessment'}
    result['revision'] = 'DRAFT Review117; not approved or validated for release'
    changes = [{'family': old['family'], 'before': old['count'], 'after': new['count']}
               for old, new in zip(level['goals'], goals)]
    return result, {'salt': salt, 'changes': changes, 'activeCells': len(active),
                    'occupiedObstacleCells': len(occupied), 'coveragePercent': result['metrics']['coveragePercent'],
                    'coverageCapPercent': cap}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    allowed = (root / '.verification-cache').resolve()
    if not out.is_relative_to(allowed) or out == allowed or out.exists():
        raise ValueError('Output must be a new directory in .verification-cache')
    out.mkdir(parents=True)
    results = []
    for n in range(11, 51):
        src = root / f'Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L{n:03}.json'
        data = src.read_bytes()
        level = json.loads(data.decode('utf-8-sig'))
        errors = []
        for salt in range(12):
            try:
                draft, details = candidate(level, salt)
                result_bytes = (json.dumps(draft, indent=2) + '\n').encode('utf-8')
                (out / src.name).write_bytes(result_bytes)
                results.append({'level': n, 'status': 'DRAFT_STATIC_PASS',
                                'sourceSHA256': hashlib.sha256(data).hexdigest(),
                                'draftSHA256': hashlib.sha256(result_bytes).hexdigest(), **details})
                break
            except ValueError as e:
                errors.append(str(e))
        else:
            results.append({'level': n, 'status': 'DRAFT_FAILED', 'errors': sorted(set(errors)),
                            'sourceSHA256': hashlib.sha256(data).hexdigest()})
    report = {'scope': 'Static proposals only; no Unity, playability, difficulty, replay, backend or device acceptance.',
              'toolSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'levels': results}
    (out / 'Report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': sum(x['status'] == 'DRAFT_STATIC_PASS' for x in results),
                      'failed': [x for x in results if x['status'] != 'DRAFT_STATIC_PASS']}, indent=2))


if __name__ == '__main__':
    main()
