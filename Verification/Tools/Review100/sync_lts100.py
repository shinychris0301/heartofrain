"""Copy frozen current Assets into the already approved private LTS candidate.

Preserve migrated importer bodies and exact source GUIDs. Never promote settings,
change the main engine or recreate the isolated project.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0, str(ROOT / 'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not args.execute or not re.fullmatch('[A-Za-z0-9_]{1,30}', args.tag) or unity_pids():
        parser.error('Explicit bounded copy and idle Unity required')
    project = ROOT / '.verification-cache/Review98/Game'
    if json.loads((project / 'Packages/manifest.json').read_text())['dependencies'].get('com.unity.modules.tilemap') != '1.0.0':
        parser.error('Approved retained SpriteMask module dependency required')
    output = ROOT / 'Verification/Evidence/Review100/Preparation' / (args.tag + '.json')
    if output.exists():
        parser.error('Fresh receipt required')
    before, changes, guids = api.freeze(), [], 0
    for source in sorted((ROOT / 'Unity/Assets').rglob('*')):
        if not source.is_file():
            continue
        if source.is_symlink() or source.stat().st_file_attributes & 0x400:
            raise ValueError('LinkedSourceRejected100')
        target = project / source.relative_to(ROOT / 'Unity')
        if source.suffix == '.meta' and target.exists():
            expected = re.findall(rb'(?m)^guid:\s*([a-fA-F0-9]{32})\s*$', source.read_bytes())
            actual = re.findall(rb'(?m)^guid:\s*([a-fA-F0-9]{32})\s*$', target.read_bytes())
            if len(expected) != 1 or expected != actual:
                raise ValueError('ExistingAssetGuidChanged100')
            guids += 1
            continue
        old = api.sha(target) if target.exists() else None
        expected = api.sha(source)
        if old != expected:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if target.stat().st_nlink != 1 or api.sha(target) != expected:
                raise ValueError('OrdinaryExactCopyFailed100')
            changes.append(dict(path=source.relative_to(ROOT).as_posix(), beforeSHA256=old, afterSHA256=expected))
    after = api.freeze()
    if before != after:
        raise ValueError('MainInputsChanged100')
    api.write(output, dict(status='PREPARED_EXACT_PRIVATE100_SOURCE', utc=api.utc(), mainInputsUnchanged=True,
                          mainInputCount=before['inputCount'], copied=changes, preservedExistingMetaGuids=guids,
                          tilemapDependency='1.0.0', scope='Ordinary source copies only; existing isolated engine/settings and migrated importer bodies retained, no compile/device claim.'))
    print(json.dumps(dict(status='PREPARED_EXACT_PRIVATE100_SOURCE', copied=len(changes), report=output.relative_to(ROOT).as_posix())))


if __name__ == '__main__':
    main()
