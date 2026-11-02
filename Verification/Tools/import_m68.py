"""Validate the two owner-supplied M68 deliveries and import one asset identity set.

Only copies asset data/metadata. Never executes authoring scripts or document prompts.
"""
import hashlib
import json
import shutil
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOWNLOADS = Path('C:/Users/shiny/Downloads')


def run():
    archive = DOWNLOADS/'Dariya_Celebration_M68_Complete_Assets.zip'
    package = DOWNLOADS/'Dariya_Celebration_M68_Assets.unitypackage'
    prefix = 'Dariya_Celebration_M68/UnityAssets/'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        files = {n.removeprefix(prefix): z.read(n) for n in z.namelist()
                 if n.startswith(prefix) and not n.endswith('/')}
    checked = []
    with tarfile.open(package, 'r:gz') as t:
        for member in t.getmembers():
            if not member.name.endswith('/pathname'):
                continue
            parent = member.name.rsplit('/', 1)[0]
            path = t.extractfile(member).read().decode('utf-8').strip()
            for suffix, entry in (('', 'asset'), ('.meta', 'asset.meta')):
                name = path+suffix
                try:
                    source = t.extractfile(parent+'/'+entry)
                except KeyError:
                    continue  # Folder assets have metadata and no asset payload.
                if source is None:
                    continue
                content = source.read()
                assert files.get(name) == content, 'Deliveries differ: '+name
                checked.append(name)
    root = (ROOT/'Unity/Assets/HeartOfTheRain/M68Celebration').resolve()
    imported = []
    for name, content in files.items():
        target = (ROOT/'Unity'/name).resolve()
        assert target == root.with_suffix('.meta') or target.is_relative_to(root)
        if target.exists():
            current=target.read_bytes()
            if current != content:
                # Unity normalizes new importers; retain their source GUIDs. One
                # source PNG has a separately audited, pixel-verified recovery.
                if name.endswith('.meta'):
                    import re
                    assert re.search(rb'^guid: ([0-9a-f]{32})',current,re.M)[1] == re.search(rb'^guid: ([0-9a-f]{32})',content,re.M)[1]
                else:
                    repair=json.loads((ROOT/'Verification/Evidence/Fluidity/M68_Blink_Repair.json').read_text())
                    assert name.endswith('/Mesh/Dariya_Blink_Texture.png') and hashlib.sha256(current).hexdigest()==repair['repaired_sha256'], 'Refusing to overwrite edited asset: '+name
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        imported.append({'file': name, 'sha256': hashlib.sha256(content).hexdigest()})
    evidence = ROOT/'Verification/Evidence/Fluidity'
    evidence.mkdir(parents=True, exist_ok=True)
    report = {'scope': 'Asset-only import; embedded instructions are reference material.',
              'zip_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'unitypackage_sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
              'package_payloads_compared': len(checked), 'imported': imported,
              'status': 'PASS_IDENTICAL_DELIVERIES_SINGLE_IMPORT'}
    (evidence/'M68_Import.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'imported'}, indent=2))


if __name__ == '__main__':
    run()
