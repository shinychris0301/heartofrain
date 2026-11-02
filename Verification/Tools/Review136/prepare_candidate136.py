"""Prepare the review 136 device candidate: an isolated Unity 6 copy of the first-moderation project
with the current main-tree game sources.

  prepare_candidate136.py clone [--no-library]   Copy the Moderation04 project (Library/Bee, Builds, Temp, Logs and Raw excluded)
  prepare_candidate136.py sync                   Copy every differing file under Assets/HeartOfTheRain from the main tree,
                                                 remove files the main tree no longer has, and write Release136.json

The candidate keeps its own packaged staging and advertising configuration, csc.rsp, ProjectSettings and
Android manifest: those are the first-moderation profile, not game sources. Nothing in the main tree changes.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'Unity/Assets/HeartOfTheRain'
BASE = Path(r'E:\.verification-cache\HOTR130\Moderation04')
HOME = Path(r'E:\.verification-cache\HOTR136\Candidate01')
PROJECT = HOME / 'Game'
TARGET = PROJECT / 'Assets/HeartOfTheRain'
KEEP = ('Resources/HOTR_Advertising/Configuration.json', 'Resources/HOTR_RuStore', 'Resources/HOTR_Server')
EVIDENCE = ROOT / 'Verification/Evidence/Review136'
VERSION_CODE = 131


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def kept(relative):
    return any(relative == k or relative == k + '.meta' or relative.startswith(k + '/') for k in KEEP)


def clone():
    if PROJECT.exists():
        raise SystemExit('candidate already exists: ' + str(PROJECT))
    skip_library = '--no-library' in sys.argv

    def ignore(directory, names):
        rel = Path(directory).relative_to(BASE / 'Game').as_posix() if Path(directory) != BASE / 'Game' else ''
        drop = set()
        for name in names:
            path = (rel + '/' + name) if rel else name
            if path in ('Builds', 'Temp', 'Logs', 'Library/Bee', 'Library/PackageCache/.tmp') or (skip_library and path == 'Library'):
                drop.add(name)
        return drop
    HOME.mkdir(parents=True, exist_ok=True)
    shutil.copytree(BASE / 'Game', PROJECT, ignore=ignore)
    print('cloned', PROJECT, 'library', 'skipped' if skip_library else 'copied without Bee')


def sync():
    if not TARGET.is_dir():
        raise SystemExit('clone first')
    copied, removed, same = [], [], 0
    for path in sorted(p for p in SOURCE.rglob('*') if p.is_file()):
        rel = path.relative_to(SOURCE).as_posix()
        if kept(rel):
            continue
        dest = TARGET / rel
        # Unity 6 re-serialises every .meta it imports, so an existing .meta is the candidate's own;
        # only a .meta for a file the candidate lacks is copied.
        if dest.is_file() and (rel.endswith('.meta') or dest.stat().st_size == path.stat().st_size and sha(dest) == sha(path)):
            same += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        copied.append(rel)
    for path in sorted(p for p in TARGET.rglob('*') if p.is_file()):
        rel = path.relative_to(TARGET).as_posix()
        if kept(rel) or (SOURCE / rel).is_file():
            continue
        path.unlink()
        removed.append(rel)
    for directory in sorted((p for p in TARGET.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    release = json.loads((BASE / 'Release130.json').read_text('utf-8-sig'))
    release['versionCode'] = VERSION_CODE
    release['note'] = 'Review 136 device candidate on the first-moderation profile: paid checkout compiled out; staging backend; not for publication.'
    (HOME / 'Release136.json').write_text(json.dumps(release, indent=4, ensure_ascii=False) + '\n', encoding='utf-8')
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    receipt = {'base': str(BASE), 'project': str(PROJECT), 'versionCode': VERSION_CODE, 'unchanged': same,
               'copied': {rel: sha(TARGET / rel) for rel in copied}, 'removed': removed, 'kept': list(KEEP)}
    (EVIDENCE / 'Candidate136_Preparation.json').write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print('copied', len(copied), 'removed', len(removed), 'unchanged', same)


{'clone': clone, 'sync': sync}[sys.argv[1]]()
