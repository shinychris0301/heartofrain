"""Owner-approved Level 17 change, review 136: open the top spawn cell (4,10).

  level17_change.py apply      Edit the client level and the server catalog in this repo.
  level17_change.py bundle     Make a local replay worker copy with the new pins and approval.
  level17_change.py payload    Write the two files the VPS cutover script installs.

The original stays in Resources/HOTR_LegacyLevels117, so attempts bound to it still play.
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEVEL = ROOT / 'Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L017.json'
LEGACY = ROOT / 'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/C01_L017.json'
CATALOG = ROOT / 'Backend/config/levels.json'
OLD_HASH = '9b196ae5a76366a1f9c9ba1ac2b6c7ec882ad690524471f2c07ea057f0b8323a'
OLD_BUNDLE = ROOT / '.verification-cache/PinnedReplay83/Worker'
NEW_BUNDLE = ROOT / '.verification-cache/PinnedReplay136/Worker'
EVIDENCE = ROOT / 'Verification/Evidence/Review136'
PAYLOAD = ROOT / 'Release/RuStore/WindowsVps/Level17Cutover136'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise SystemExit(f'expected one match, found {text.count(old)}: {old[:80]}')
    return text.replace(old, new)


def apply():
    raw = LEVEL.read_bytes()
    if sha(raw) != OLD_HASH or sha(LEGACY.read_bytes()) != OLD_HASH:
        raise SystemExit('level or retained original is not the expected version')
    text = raw.decode('utf-8')
    text = once(text, '''    {
      "instanceId": "C01_L017_moss_4_10",
      "family": "moss",
      "layer": "body",
      "hp": 1,
      "x": 4,
      "y": 10,
      "art": "OB_MOSS_HP1",
      "motion": "anchored"
    },
''', '')
    # Tiles are listed by column, then row; (4,10) is the last of column 4.
    tile = re.search(r'    \{\n      "x": 4,\n      "y": 9,\n      "color": \d+\n    \},\n', text)
    if not tile:
        raise SystemExit('tile (4,9) not found')
    text = text[:tile.end()] + '    {\n      "x": 4,\n      "y": 10,\n      "color": 3\n    },\n' + text[tile.end():]
    text = once(text, '"family": "moss",\n      "count": 13', '"family": "moss",\n      "count": 12')
    for old, new in (('"bodyCells": 60', '"bodyCells": 59'), ('"occupiedObstacleCells": 60', '"occupiedObstacleCells": 59'),
                     ('"coveragePercent": 63.2', '"coveragePercent": 62.1'), ('"damageUnits": 90', '"damageUnits": 89'),
                     ('"minimumDamageUnitsPerMove": 2.81', '"minimumDamageUnitsPerMove": 2.78'), ('"moss": 13', '"moss": 12')):
        text = once(text, old, new)
    new_raw = text.encode('utf-8')
    json.loads(new_raw)
    LEVEL.write_bytes(new_raw)
    new_hash = sha(new_raw)
    catalog = CATALOG.read_bytes().decode('utf-8-sig')
    bom = CATALOG.read_bytes().startswith(b'\xef\xbb\xbf')
    block = re.search(r'"level": 17,.*?"reward"', catalog, re.S)
    row = block.group(0)
    row = once(row, f'"sourceSHA256": "{OLD_HASH}"', f'"sourceSHA256": "{new_hash}"')
    row = once(row, f'"configHash": "{OLD_HASH}"', f'"configHash": "{new_hash}"')
    row, count = re.subn(r'("family": "moss",\s+"count": )13', r'\g<1>12', row)
    if count != 1:
        raise SystemExit('catalog moss goal not found')
    catalog = catalog[:block.start()] + row + catalog[block.end():]
    json.loads(catalog)
    CATALOG.write_bytes((b'\xef\xbb\xbf' if bom else b'') + catalog.encode('utf-8'))
    print('level', new_hash)


def bundle():
    new_raw = LEVEL.read_bytes()
    new_hash = sha(new_raw)
    if new_hash == OLD_HASH:
        raise SystemExit('apply the level change first')
    if not NEW_BUNDLE.exists():
        shutil.copytree(OLD_BUNDLE, NEW_BUNDLE)
    (NEW_BUNDLE / 'ReplayPins/Levels/C01_L017.json').write_bytes(new_raw)
    pins_path = NEW_BUNDLE / 'ReplayPins/manifest.json'
    pins_raw = pins_path.read_bytes()
    pins = pins_raw.decode('utf-8')
    if OLD_HASH in pins:
        pins = once(pins, OLD_HASH, new_hash)
        pins_path.write_bytes(pins.encode('utf-8'))
    files = {}
    for path in sorted(p for p in NEW_BUNDLE.rglob('*') if p.is_file()):
        files[path.relative_to(NEW_BUNDLE).as_posix()] = sha(path.read_bytes())
    approval = {'version': 1, 'kind': 'PinnedUnityReplayWorker', 'unity': '2022.3.62f3', 'executable': 'PinnedReplayWorker.exe',
                'pins': 'ReplayPins/manifest.json', 'files': files}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / 'Worker136_Approval.json'
    out.write_text(json.dumps(approval, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print('bundle', NEW_BUNDLE, 'files', len(files), 'approval', sha(out.read_bytes()))


def payload():
    PAYLOAD.mkdir(parents=True, exist_ok=True)
    (PAYLOAD / 'C01_L017.json').write_bytes(LEVEL.read_bytes())
    (PAYLOAD / 'levels.json').write_bytes(CATALOG.read_bytes())
    print('level', sha(LEVEL.read_bytes()), 'catalog', sha(CATALOG.read_bytes()))


{'apply': apply, 'bundle': bundle, 'payload': payload}[sys.argv[1]]()
