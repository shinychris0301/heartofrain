"""Explore top-source-only layouts for five observed capped-gap cases.

Fixed bodies are limited to the bottom of each mask segment, preserving each
goal family and retaining all cabinet bodies. Original move budgets and HP
are kept; substantial goal-count reductions are recorded. This is an isolated
diagnostic proposal, not a claim of good balance or complete solvability.
"""
import argparse
import collections
import copy
import hashlib
import json
import random
from pathlib import Path

from propose_nine_row import has_legal_swap, opening_matches


LEVELS = (20, 31, 35, 39, 40)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bottom_segment(active, x, y):
    while (x, y - 1) in active:
        y -= 1
    return x, y


def adjust(level):
    level = copy.deepcopy(level)
    if any(o['family'] in ('pail', 'crystal') for o in level['obstacles']):
        raise ValueError('special_route_or_crystal_requires_separate_authoring')
    if level.get('mossRegrowth', {}).get('enabled'):
        raise ValueError('dynamic_growth_requires_separate_analysis')
    active = {(c['x'], c['y']) for c in level['activeCells']}
    segments = {(x, y) for x, y in active if (x, y - 1) not in active}
    occupied, used_segments, placed = set(), set(), []
    cabinets = [o for o in level['obstacles'] if o['family'] == 'cabinet']
    for o in cabinets:
        options = []
        for x, y in sorted(segments):
            footprint = {(x + dx, y + dy) for dx in (0, 1) for dy in (0, 1)}
            cols = {(x, y), (x + 1, y)}
            if cols <= segments and not cols & used_segments and footprint <= active and not footprint & occupied:
                options.append((abs(x - o['x']) + abs(y - o['y']), x, y))
        if not options:
            raise ValueError('cabinet_bottom_placement_unavailable')
        _, x, y = min(options)
        q = copy.deepcopy(o); q.update(x=x, y=y); placed.append(q)
        used_segments.update(((x, y), (x + 1, y)))
        occupied.update((x + dx, y + dy) for dx in (0, 1) for dy in (0, 1))
    groups = collections.defaultdict(list)
    for o in level['obstacles']:
        if o['family'] not in ('crate', 'cabinet'):
            groups[o['family']].append(o)
    available = sorted(segments - used_segments)
    if len(available) < len(groups):
        raise ValueError('not_enough_segments_for_all_families')
    quotas = {f: 1 for f in groups}
    while sum(quotas.values()) < len(available):
        options = [f for f in groups if quotas[f] < len(groups[f])]
        if not options:
            break
        f = min(options, key=lambda f: (quotas[f] / len(groups[f]), f))
        quotas[f] += 1
    chosen = []
    for family, objects in sorted(groups.items()):
        objects = sorted(objects, key=lambda o: (o['y'], o['x']))
        count = quotas[family]
        chosen.extend(objects[min(len(objects) - 1, int((i + .5) * len(objects) / count))] for i in range(count))
    for o in sorted(chosen, key=lambda q: (q['y'], q['x'], q['family'])):
        x, y = min(available, key=lambda p: (abs(p[0] - o['x']) + abs(p[1] - o['y']), p))
        available.remove((x, y));used_segments.add((x, y));occupied.add((x, y))
        q = copy.deepcopy(o);q.update(x=x, y=y);placed.append(q)
    for o in (x for x in level['obstacles'] if x['family'] == 'crate'):
        free = active - occupied
        if not free:
            raise ValueError('crate_placement_unavailable')
        x, y = min(free, key=lambda p: (abs(p[0] - o['x']) + abs(p[1] - o['y']), p))
        q = copy.deepcopy(o);q.update(x=x, y=y);placed.append(q);occupied.add((x, y))
    cells = sorted(active - occupied, key=lambda p: (p[1], p[0]))
    colors = level['activeColors']
    gems = None
    for attempt in range(1200):
        rng = random.Random(level['globalLevel'] * 1973 + attempt)
        trial = {}
        for cell in cells:
            shuffled = list(colors);rng.shuffle(shuffled)
            for color in shuffled:
                trial[cell] = color
                if not opening_matches(trial):
                    break
            else:
                break
        if len(trial) == len(cells) and not opening_matches(trial) and has_legal_swap(trial):
            gems = trial;break
    if gems is None:
        raise ValueError('no_opening_match_free_playable_arrangement')
    counts = collections.Counter()
    for o in placed:
        counts['rainlight' if o['family'] == 'cabinet' else o['family']] += min(4, o['hp']) if o['family'] == 'cabinet' else 1
    goals = copy.deepcopy(level['goals'])
    if set(counts) != {g['family'] for g in goals}:
        raise ValueError('goal_family_changed')
    old_goals = copy.deepcopy(goals)
    for g in goals:g['count'] = counts[g['family']]
    level['obstacles'] = placed
    level['goals'] = goals
    level['initialTiles'] = [{'x': x, 'y': y, 'color': gems[(x, y)]} for x, y in cells]
    level['metrics']['occupiedObstacleCells'] = len(occupied)
    level['metrics']['coveragePercent'] = round(100 * len(occupied) / len(active), 2)
    level['balancePass']['scope'] = 'Single bottom fixed obstacle per segment; provisional count rebalance, not playtest approval'
    return level, {'oldGoals': old_goals, 'newGoals': goals, 'coveragePercent': level['metrics']['coveragePercent'],
                   'segments': len(segments), 'fixedSegmentsUsed': len(used_segments)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args();root, output = a.root.resolve(), a.output.resolve();cache = (root / '.verification-cache').resolve()
    if not output.is_relative_to(cache) or output == cache or output.exists():
        raise ValueError('Output must be a new directory inside .verification-cache')
    prior = cache / 'Review117/CampaignVaried03';output.mkdir(parents=True)
    rows=[]
    for n in range(11, 51):
        name=f'C01_L{n:03}.json';before=(prior/name).read_bytes()
        if n in LEVELS:
            draft, changes=adjust(json.loads(before.decode('utf-8')));after=(json.dumps(draft,indent=2)+'\n').encode()
            rows.append({'level':n,'priorSHA256':sha(before),'draftSHA256':sha(after),**changes})
        else:after=before
        (output/name).write_bytes(after)
    report={'scope':'Five fixed-gap experiments only; no Unity, replay, visual, difficulty or backend approval.',
            'toolSHA256':sha(Path(__file__).read_bytes()),'levels':rows}
    (output/'Report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(rows,indent=2))


if __name__ == '__main__':main()
