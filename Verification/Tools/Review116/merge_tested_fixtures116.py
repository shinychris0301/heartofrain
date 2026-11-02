"""Apply exact tested repairs only where main still has the recorded old bytes.

Newer main changes are preserved, and all originals are retained before writes.
This does not stage or commit and never changes asset metadata.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--source-delta', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not args.execute or not args.tag.isalnum():
        parser.error('ExplicitOwnedExactMergeRequired')
    proof = args.source_delta.resolve()
    proof.relative_to(ROOT)
    proof_bytes = proof.read_bytes()
    delta = json.loads(proof_bytes.decode('utf-8-sig'))
    if delta['status'] != 'CLASSIFIED_EXACT_CANONICAL_SOURCE_DELTA116':
        raise ValueError('ReviewedExactSourceDeltaRequired')
    out = ROOT / 'Verification/Evidence/Review116/Repository' / ('SafeMainMerge_' + args.tag + '.json')
    backup = ROOT / '.verification-cache/Review116/BeforeMainMerge' / args.tag
    if out.exists() or backup.exists():
        raise ValueError('PreserveEarlierMergeReceipt')
    backup.mkdir(parents=True)
    planned = []
    for row in delta['changes']:
        path = ROOT / row['path']
        source = ROOT / row['snapshotSource']
        for candidate in (path, source):
            candidate.resolve().relative_to(ROOT)
            if candidate.is_symlink() or not candidate.is_file():
                raise ValueError('RegularContainedSourceRequired')
        if not row['path'].startswith('Unity/Assets/') or path.suffix != '.cs' or not row['metaUnchanged']:
            raise ValueError('ClassifiedCSharpRepairOnly')
        desired, before = source.read_bytes(), path.read_bytes()
        if digest(desired) != row['afterSHA256']:
            raise ValueError('ExactFinalCanonicalBytesRequired')
        planned.append((row, path, before, desired))
    results = []
    if proof.read_bytes() != proof_bytes:
        raise ValueError('SourceDeltaChangedBeforeMerge')
    for row, path, before, desired in planned:
        current = path.read_bytes()
        if current == desired:
            result = 'AlreadyExactTestedBytes'
        elif digest(before) == row['beforeSHA256'] and current == before:
            retained = backup / row['path']
            retained.parent.mkdir(parents=True, exist_ok=True)
            retained.write_bytes(before)
            # Recheck immediately before the narrow write; any observed newer
            # bytes are preserved instead of merging guessed user intent.
            if path.read_bytes() != before:
                result = 'ConcurrentNewerMainPreserved'
            else:
                path.write_bytes(desired)
                result = 'AppliedExactTestedRepair'
        else:
            result = 'NewerMainPreserved'
        results.append(dict(path=row['path'], result=result, beforeSHA256=digest(before),
                            desiredSHA256=digest(desired), observedMainSHA256=digest(path.read_bytes())))
    value = dict(status='COMPLETED_GUARDED_MAIN_REPAIR_MERGE116',
                 sourceDelta=proof.relative_to(ROOT).as_posix(), sourceDeltaSHA256=digest(proof_bytes),
                 assetMetadataWritten=False, stageOrCommitPerformed=False, files=results)
    out.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=value['status'], results=results)))


if __name__ == '__main__':
    main()
