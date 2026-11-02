"""Check local diagonal candidates for recorded settled model gaps.

This mirrors the current DiagonalGravity neighbor/corner preconditions on the
recorded snapshots. It is a read-only analysis, not a model execution.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / 'Verification/Evidence/Review117/Native/Gaps01/CampaignGaps117.json'
LEVELS = ROOT / '.verification-cache/Review117/CampaignVaried03'


def main():
    source = json.loads(REPORT.read_text(encoding='utf-8-sig'))
    rows = []
    movable = {'gem', 'power', 'crate', 'pail'}
    for row in source['levels']:
        level = json.loads((LEVELS / f'C01_L{row["level"]:03}.json').read_text())
        active = {(c['x'], c['y']) for c in level['activeCells']}
        exits = {(c['x'], c['y']) for c in level['deliveryExits']}
        for gap in row['gaps']:
            pieces = {(p['x'], p['y']): p for p in gap['snapshot']['pieces']}
            crystal_lanes = {p['x'] for p in pieces.values() if p['family'] == 'crystal'}
            for cell in gap['cells']:
                x, y = cell['x'], cell['y']
                sides = []
                for dx in (-1, 1):
                    sx = x + dx
                    corner, source_piece = pieces.get((sx, y)), pieces.get((sx, y + 1))
                    source_family = source_piece['family'] if source_piece else None
                    corner_family = corner['family'] if corner else None
                    allowed = ((sx, y) in active and source_family in movable and
                               (corner_family is None or corner_family in movable) and
                               not (source_family == 'pail' and (sx, y + 1) in exits) and
                               not (x in crystal_lanes and source_family not in ('gem', 'power')))
                    sides.append({'offset': dx, 'cornerActive': (sx, y) in active,
                                  'cornerFamily': corner_family, 'sourceFamily': source_family,
                                  'locallyAllowed': allowed})
                rows.append({'level': row['level'], 'turn': gap['turn'], 'x': x, 'y': y,
                             'blockerFamily': cell['blockerFamily'], 'hasSpawn': cell['hasSpawn'],
                             'sides': sides})
    result = {'scope': 'Read-only local neighbor preconditions on recorded settled gaps; not a new Unity or device test.',
              'source': str(REPORT.relative_to(ROOT)).replace('\\', '/'),
              'cells': rows, 'cellsWithLocalPath': sum(any(s['locallyAllowed'] for s in r['sides']) for r in rows)}
    out = ROOT / 'Verification/Evidence/Review117/GapPathAnalysis117.json'
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'recordedCells': len(rows), 'cellsWithLocalPath': result['cellsWithLocalPath']}))


if __name__ == '__main__':
    main()
