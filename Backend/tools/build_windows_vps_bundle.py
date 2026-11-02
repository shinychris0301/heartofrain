"""Build an allowlisted, non-secret Windows VPS staging source archive."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile


ROOT = Path(__file__).resolve().parents[2]


def _files() -> list[Path]:
    entries = [
        *ROOT.glob('Backend/hotr_backend/**/*.py'),
        *ROOT.glob('Backend/tests/**/*.py'),
        *ROOT.glob('Backend/tools/**/*.py'),
        *ROOT.glob('Backend/config/*.json'),
        ROOT / 'Backend/requirements.lock',
        ROOT / 'Backend/requirements.in',
        ROOT / 'Backend/README.md',
        ROOT / 'Release/RuStore/WindowsVps/DEPLOY.md',
        ROOT / 'Release/RuStore/WindowsVps/staging-build.novamind.json',
    ]
    result = sorted(set(entries), key=lambda path: path.relative_to(ROOT).as_posix())
    for path in result:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('non_regular_bundle_source')
    return result


def build(destination: Path) -> dict:
    destination = destination.resolve()
    if destination.exists() or destination.suffix.lower() != '.zip' or not destination.parent.is_dir():
        raise ValueError('fresh_zip_destination_required')
    files = _files()
    digests = {}
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            digests[relative] = hashlib.sha256(data).hexdigest()
            archive.writestr(relative, data)
        archive.writestr('SHA256SUMS.json', json.dumps(digests, sort_keys=True, indent=2) + '\n')
    return {'status': 'bundle_built', 'fileCount': len(files), 'bytes': destination.stat().st_size,
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'path': str(destination)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build(args.destination), separators=(',', ':')))
    except (OSError, ValueError):
        print(json.dumps({'status': 'blocked_bundle_build'}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
