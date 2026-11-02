"""Stage varied 9-row drafts with fixed obstacles kept low where possible.

Does not add interior refill sources, edit Unity levels or establish balance.
Any remaining static caps and all potential dynamically grown blockers must be
reviewed with real BoardModel/playback runs.
"""
import argparse
import hashlib
import json
from pathlib import Path

from generate_campaign_varied import candidate, dimensions


def sha(b):
    return hashlib.sha256(b).hexdigest()


def caps(level):
    active = {(p['x'], p['y']) for p in level['activeCells']}
    fixed = set()
    for o in level['obstacles']:
        if o['family'] in ('crate', 'pail'):
            continue
        width, height = dimensions(o)
        fixed.update((o['x'] + dx, o['y'] + dy)
                     for dx in range(width) for dy in range(height))
    capped = []
    for gem in level['initialTiles']:
        x, y = gem['x'], gem['y']
        top = y + 1
        while (x, top) in active:
            if (x, top) in fixed:
                capped.append({'x': x, 'y': y, 'blockerY': top})
                break
            top += 1
    return capped


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    root, output = a.root.resolve(), a.output.resolve()
    cache = (root / '.verification-cache').resolve()
    if not output.is_relative_to(cache) or output == cache or output.exists():
        raise ValueError('Output must be a new directory in .verification-cache')
    previous = cache / 'Review117/CampaignVaried02'
    output.mkdir(parents=True)
    rows = []
    for n in range(11, 51):
        name = f'C01_L{n:03}.json'
        before = (previous / name).read_bytes()
        previous_level = json.loads(before.decode('utf-8'))
        source_path = root / 'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117' / name
        source = json.loads(source_path.read_text(encoding='utf-8-sig'))
        choices = []
        errors = []
        for salt in range(12):
            try:
                draft, detail = candidate(source, salt=salt, bottom_fixed=True)
                if [(g['family'], g['count']) for g in draft['goals']] != [(g['family'], g['count']) for g in previous_level['goals']]:
                    raise ValueError('goal_count_changed')
                choices.append((len(caps(draft)), salt, draft, detail))
            except ValueError as e:
                errors.append(str(e))
        if not choices:
            rows.append({'level': n, 'status': 'DRAFT_FAILED', 'errors': sorted(set(errors))})
            continue
        risk, salt, draft, detail = min(choices, key=lambda x: (x[0], x[1]))
        draft['balancePass']['scope'] = 'Fixed obstacles placed low where possible; diagnostic only, no balance approval'
        after = (json.dumps(draft, indent=2) + '\n').encode('utf-8')
        (output / name).write_bytes(after)
        rows.append({'level': n, 'status': 'DRAFT_STATIC_PASS', 'sourceSHA256': sha(source_path.read_bytes()),
                     'priorSHA256': sha(before), 'draftSHA256': sha(after),
                     'priorCappedGemCount': len(caps(previous_level)), 'cappedGemCount': risk,
                     'cappedGems': caps(draft), 'details': detail})
    report = {'scope': 'Static placement candidates; no Unity, replay, playback, device or balance approval.',
              'toolSHA256': sha(Path(__file__).read_bytes()), 'levels': rows}
    (output / 'Report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'total': len(rows), 'failed': [x['level'] for x in rows if x['status'] != 'DRAFT_STATIC_PASS'],
                      'priorCappedGems': sum(x.get('priorCappedGemCount', 0) for x in rows),
                      'cappedGems': sum(x.get('cappedGemCount', 0) for x in rows),
                      'levelsWithRemainingCaps': [x['level'] for x in rows if x.get('cappedGemCount', 0)]}, indent=2))


if __name__ == '__main__':
    main()
