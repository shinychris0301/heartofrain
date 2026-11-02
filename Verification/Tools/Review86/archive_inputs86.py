"""Archive changed review code and verify preserved baseline Unity inputs."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review86/Inputs'
BASE = 'e3fc9865'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    changed = set(git('diff', '--name-only', BASE, '--', 'Unity/Assets', 'Unity/Packages', 'Unity/ProjectSettings').decode().splitlines())
    changed.update(git('ls-files', '--others', '--exclude-standard', '--', 'Unity/Assets', 'Unity/Packages', 'Unity/ProjectSettings').decode().splitlines())
    assert changed and all(p.endswith('.cs') or p.endswith('.meta') for p in changed), 'NonCodeUnityChange'
    preserved = {}
    with tarfile.open(fileobj=io.BytesIO(git('archive', BASE, 'Unity/Assets', 'Unity/Packages', 'Unity/ProjectSettings'))) as snapshot:
        for member in snapshot:
            if not member.isfile():
                continue
            relative = member.name
            original = snapshot.extractfile(member).read()
            current = (ROOT / relative).read_bytes()
            if relative not in changed:
                assert original == current, 'BaselineInputChanged:' + relative
                preserved[relative] = sha(current)
            elif relative.endswith('.meta'):
                assert original == current, 'ExistingGuidChanged:' + relative
    paths = changed | {p.relative_to(ROOT).as_posix() for p in (ROOT / 'Verification/Tools/Review86').glob('*') if p.is_file()}
    archive = {}
    for relative in sorted(paths):
        source = ROOT / relative
        target = OUT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        archive[relative] = sha(source.read_bytes())
        assert sha(target.read_bytes()) == archive[relative]
    report = {'baseline': BASE, 'archivedSHA256': archive, 'changedUnityPaths': sorted(changed),
              'unchangedBaselineInputsSHA256': preserved,
              'scope': 'Exact changed Unity code/new metadata and review tools; existing artwork, GUIDs, level/model/timing inputs and settings are compared with committed baseline. Full current source manifests are separately bound by each execution.'}
    (OUT / 'Archive.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'archived': len(archive), 'preserved': len(preserved)}))


if __name__ == '__main__':
    main()
