"""Stage new board surfaces by assembling exact patches of approved M47 art.

The 64 px grid and 15 px pad come from the M47 handoff. For each center,
edge and corner patch we select original pixels with the same local active
cell topology and checker parity. No artwork or Unity asset is overwritten.
The reconstruction must be compared with original golden images and native
playback; matching palette alone is not visual approval.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

from PIL import Image

PITCH, PAD = 64, 15
BOUNDS = ((0, 20), (20, 44), (44, 64))


def shape(level):
    return {(c['x'], level['rows'] - 1 - c['y']) for c in level['activeCells']}


def key(active, x, y, ix, iy):
    xs = (-1, 0) if ix == 0 else (0, 1) if ix == 2 else (0,)
    ys = (-1, 0) if iy == 0 else (0, 1) if iy == 2 else (0,)
    return ix, iy, (x + y) % 2, tuple((x + dx, y + dy) in active for dy in ys for dx in xs)


def donors(root):
    source = root / 'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117'
    art = root / 'Unity/Assets/HeartOfTheRain/M47/Art/Boards'
    index = collections.defaultdict(list)
    images = {}
    for n in range(1, 51):
        name = f'C01_L{n:03}'
        level = json.loads((source / (name + '.json')).read_text(encoding='utf-8-sig'))
        active = shape(level)
        images[n] = tuple(Image.open(art / (name + suffix)).convert('RGBA')
                          for suffix in ('_Surface.png', '_AlphaMask.png'))
        for x in range(level['columns']):
            for y in range(level['rows']):
                for ix in range(3):
                    for iy in range(3):
                        index[key(active, x, y, ix, iy)].append((n, x, y))
    return index, images


def generate(level, index, images):
    columns, rows = level['columns'], level['rows']
    size = (PITCH * columns + 2 * PAD, PITCH * rows + 2 * PAD)
    surface, mask = (Image.new('RGBA', size, (0, 0, 0, 0)) for _ in range(2))
    active = shape(level)
    for x in range(-1, columns + 1):
        for y in range(-1, rows + 1):
            for ix, (x0, x1) in enumerate(BOUNDS):
                for iy, (y0, y1) in enumerate(BOUNDS):
                    left, top = PAD + x * PITCH + x0, PAD + y * PITCH + y0
                    right, bottom = PAD + x * PITCH + x1, PAD + y * PITCH + y1
                    left, top, right, bottom = max(0, left), max(0, top), min(size[0], right), min(size[1], bottom)
                    if left >= right or top >= bottom:
                        continue
                    candidates = index.get(key(active, x, y, ix, iy), [])
                    if not candidates:
                        raise ValueError(f'No original art patch for {level["id"]} cell {x},{y} region {ix},{iy}')
                    n, sx, sy = candidates[0]
                    dx, dy = left - (PAD + x * PITCH), top - (PAD + y * PITCH)
                    source_box = (PAD + sx * PITCH + dx, PAD + sy * PITCH + dy,
                                  PAD + sx * PITCH + dx + right - left,
                                  PAD + sy * PITCH + dy + bottom - top)
                    for target, donor in zip((surface, mask), images[n]):
                        target.paste(donor.crop(source_box), (left, top))
    return surface, mask


def pixel_diff(a, b):
    if a.size != b.size:
        return -1
    return sum(1 for x, y in zip(a.get_flattened_data(), b.get_flattened_data()) if x != y)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--golden', action='store_true')
    a = p.parse_args()
    root, inp, out = a.root.resolve(), a.input.resolve(), a.output.resolve()
    cache = (root / '.verification-cache').resolve()
    if not out.is_relative_to(cache) or out == cache or out.exists():
        raise ValueError('Output must be a new directory under .verification-cache')
    out.mkdir(parents=True)
    index, images = donors(root)
    report = {'scope': 'Derived pixel artifacts; not Unity or device verification.', 'levels': []}
    for path in sorted(inp.glob('C01_L*.json')):
        raw = path.read_bytes()
        level = json.loads(raw.decode('utf-8-sig'))
        surface, mask = generate(level, index, images)
        name = path.stem
        paths = [out / (name + suffix) for suffix in ('_Surface.png', '_AlphaMask.png')]
        for image, target in zip((surface, mask), paths): image.save(target)
        row = {'level': level['globalLevel'], 'levelSHA256': hashlib.sha256(raw).hexdigest(),
               'surfaceSHA256': hashlib.sha256(paths[0].read_bytes()).hexdigest(),
               'maskSHA256': hashlib.sha256(paths[1].read_bytes()).hexdigest(), 'dimensions': surface.size}
        if a.golden:
            old_surface, old_mask = images[level['globalLevel']]
            row['surfaceDifferentPixels'] = pixel_diff(surface, old_surface)
            row['maskDifferentPixels'] = pixel_diff(mask, old_mask)
        report['levels'].append(row)
    report['toolSHA256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out / 'Report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'levels': len(report['levels']),
                      'surfaceDiffs': sum(r.get('surfaceDifferentPixels', 0) > 0 for r in report['levels']),
                      'maskDiffs': sum(r.get('maskDifferentPixels', 0) > 0 for r in report['levels'])}, indent=2))


if __name__ == '__main__':
    main()
