"""Apply the reproduced Teams asset-prefix fallback repair to the tested cut.

Preserve the original source and exact line endings. Merge into the working
tree only if that one file still equals the tested pre-fix bytes; newer user
edits are never replaced.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RELATIVE = 'Assets/HeartOfTheRain/App/Teams/Runtime/TeamsAssets.cs'
SNAPSHOT = ROOT / '.verification-cache/Review116/NativeSnapshot/Game'
OUT = ROOT / 'Verification/Evidence/Review116/App/Fixes/TeamsAssetFallback'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    path, working = SNAPSHOT / RELATIVE, ROOT / 'Unity' / RELATIVE
    before = path.read_bytes()
    replacements = [
        (b'return invites?invites.Find(id):null;', b'var extra=invites?invites.Find(id):null;if(extra)return extra;'),
        (b'return mail?mail.Find(id):null;', b'var extra=mail?mail.Find(id):null;if(extra)return extra;'),
        (b'return social?social.Find(id):null;', b'var extra=social?social.Find(id):null;if(extra)return extra;'),
    ]
    after = before
    for old, new in replacements:
        if after.count(old) != 1:
            raise RuntimeError('ExactReproducedTeamsSourceRequired116')
        after = after.replace(old, new)
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / 'TeamsAssets_before.cs').write_bytes(before)
    meta_before = Path(str(path) + '.meta').read_bytes()
    working_before = working.read_bytes()
    path.write_bytes(after)
    merged = working_before == before
    if merged:
        working.write_bytes(after)
    if Path(str(path) + '.meta').read_bytes() != meta_before:
        raise RuntimeError('TeamsMetadataChanged116')
    report = dict(status='APPLIED_TEAMS_FALLBACK116_PENDING_NATIVE_RETEST',
        snapshotPath=path.relative_to(ROOT).as_posix(), beforeSHA256=digest(before),
        afterSHA256=digest(after), retainedBefore='TeamsAssets_before.cs',
        workingTreeBeforeSHA256=digest(working_before), workingTreeMergedWithoutOverwritingNewerEdits=merged,
        metaUnchanged=True, preservedCRLF=before.count(b'\r\n') == after.count(b'\r\n'),
        preservedLF=before.count(b'\n') == after.count(b'\n'),
        changes='Keep TI_/TM_/TC_ resource precedence when found; otherwise use the original Teams/Leaderboard sprite lookup. No artwork, palette, GUID, state or service rule change.',
        scope='Snapshot runtime repair after an actual Android Teams review-render NullReferenceException. Test results are separate receipts.')
    (OUT / 'FixReceipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
