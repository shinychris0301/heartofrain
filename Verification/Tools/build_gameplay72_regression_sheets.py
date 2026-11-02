"""Present final regression captures for inspection; this grants no approval."""
import hashlib
import json
import argparse
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/Gameplay72'


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=OUT)
    OUT = parser.parse_args().out.resolve()
    assert OUT.is_relative_to((ROOT / 'Verification/Evidence').resolve())
    folder = OUT / 'Android/Regression'
    report = json.loads((folder / 'Regression.json').read_text('utf-8-sig'))
    assert report['status'] == 'PASS_NATIVE_REGRESSION'
    files = report['frames']
    groups = {
        'BoardMasks': [n for n in files if n.startswith(('Board_L', 'M70_'))],
        'TilesTools': [n for n in files if n.startswith(('L1_', 'L50_'))],
        'Powers': [n for n in files if n.startswith('Power_')],
        'PowerPairs': [n for n in files if n.startswith('Pair_')],
        'ObstacleRoutes': [n for n in files if n.startswith(('Cabinet_', 'Stacked_'))],
        'ConnectedFlow': [n for n in files if n.startswith(('LifeRefill_', 'Connected_', 'Home_Reward_', 'Finale_'))],
    }
    dest = OUT / 'RegressionVisual'
    dest.mkdir(exist_ok=True)
    manifest = {'status': 'PRESENTED_FOR_VISUAL_REVIEW', 'groups': {}, 'sheets': {}, 'artifactSHA256': {}}
    for name, names in groups.items():
        assert names
        width, height, columns = 225, 400, 4
        manifest['groups'][name] = names
        manifest['sheets'][name] = []
        for start in range(0, len(names), 12):
            page = names[start:start + 12]
            sheet = Image.new('RGB', (width * columns, (height + 40) * ((len(page) + columns - 1) // columns)), '#10283c')
            draw = ImageDraw.Draw(sheet)
            for index, filename in enumerate(page):
                path = folder / filename
                manifest['artifactSHA256'][path.relative_to(OUT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
                with Image.open(path) as source:
                    if name in ['TilesTools', 'Powers', 'PowerPairs', 'ObstacleRoutes']:
                        # Board-only presentation; original full captures stay hashed.
                        source = source.crop((0, int(source.height * .16), source.width, int(source.height * .86)))
                    source.thumbnail((width, height), Image.Resampling.LANCZOS)
                    x, y = (index % columns) * width, (index // columns) * (height + 40)
                    sheet.paste(source, (x + (width - source.width) // 2, y))
                    draw.text((x + 4, y + height + 3), filename[:30], fill='white')
                    if len(filename) > 30:
                        draw.text((x + 4, y + height + 17), filename[30:], fill='white')
            path = dest / (name + '_' + str(start // 12 + 1).zfill(2) + '.png')
            sheet.save(path)
            manifest['sheets'][name].append(path.relative_to(OUT).as_posix())
            manifest['artifactSHA256'][path.relative_to(OUT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (dest / 'Manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({name: len(names) for name, names in groups.items()}))


if __name__ == '__main__':
    main()
