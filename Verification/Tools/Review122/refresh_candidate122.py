"""Refresh only our unchanged generated candidate, preserving its prior bytes."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Backend'))
from hotr_backend.production_prepare122 import prepare


def main():
    current = ROOT / 'Release/Production122/Candidate'
    original = json.loads((ROOT / 'Verification/Evidence/Review122/Preparation/CandidateReceipt122.json').read_bytes())
    expected_files = sorted(original['files'])
    actual = sorted(p.relative_to(current).as_posix() for p in current.rglob('*') if p.is_file())
    if actual != expected_files:
        raise RuntimeError('candidate changed; preserve operator files')
    for name, digest in original['hashes'].items():
        if hashlib.sha256((current / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('candidate changed; preserve operator files')
    fresh = ROOT / '.verification-cache/Review122/CandidateRuntimeFinal'
    history = ROOT / '.verification-cache/Review122/CandidateBeforeRuntimeRefresh'
    prepare(fresh, sandbox=False)
    history.mkdir(exist_ok=False)
    for name in actual:
        target = history / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write((current / name).read_bytes())
    changed = []
    for source in sorted(fresh.rglob('*')):
        if not source.is_file():
            continue
        name = source.relative_to(fresh).as_posix()
        target = current / name
        data = source.read_bytes()
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
            changed.append(name)
        elif target.read_bytes() != data:
            target.write_bytes(data)
            changed.append(name)
    files = {p.relative_to(fresh).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(fresh.rglob('*')) if p.is_file()}
    if any(hashlib.sha256((current / name).read_bytes()).hexdigest() != value for name, value in files.items()):
        raise RuntimeError('generated candidate mismatch')
    report = {'status': 'EXACT_RUNTIME_AND_CLIENT_TEMPLATES_PREPARED',
              'files': files, 'changedGeneratedFiles': changed,
              'previousCandidateBytesPreservedPrivately': True,
              'operatorEditsOverwritten': False, 'productionEnabled': False,
              'providerAcceptanceVerified': False, 'secretsRead': False}
    destination = ROOT / 'Verification/Evidence/Review122/Preparation/RuntimeCandidateReceipt122.json'
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'fileCount': len(files), 'changedGeneratedFiles': changed,
                      'productionEnabled': False}))


if __name__ == '__main__':
    main()
