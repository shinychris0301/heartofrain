"""Prepare and audit an alternate Git index from the selected tested copies.

Never read newer main app bytes into that index, change HEAD, or overwrite the
ordinary index. Committing is a separate explicit operation after verification.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / '.verification-cache/Review116/Git'
OUT = ROOT / 'Verification/Evidence/Review116/Repository'
INDEX = BASE / 'tested.index'
INITIAL_HEAD = '196f606d025ac1d8f51b0653bdd1e94245811860'
APP = ROOT / '.verification-cache/Review116/NativeSnapshot/Game'
NON_UNITY = ROOT / '.verification-cache/Review116/CommitSource'
CUT_SECONDS = datetime.fromisoformat('2026-10-29T13:09:35.627802+00:00').timestamp()
EVIDENCE_SUFFIXES = {'.json', '.csv', '.txt', '.md', '.html', '.css', '.js', '.py', '.cs',
                     '.meta', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.patch', '.diff'}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def git(*arguments, data=None, index=False):
    env = dict(os.environ)
    if index:
        env['GIT_INDEX_FILE'] = str(INDEX)
    result = subprocess.run(['git', '-c', 'core.longpaths=true', *arguments], cwd=ROOT,
                            env=env, input=data, capture_output=True)
    if result.returncode:
        raise RuntimeError('GitSnapshotOperationFailed: ' + result.stderr.decode('utf-8', errors='replace')[:1500])
    return result.stdout


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def whitespace_review(proof):
    """Keep tested serialization/history bytes; reject active-code warnings."""
    env = dict(os.environ, GIT_INDEX_FILE=str(INDEX))
    result = subprocess.run(['git', '-c', 'core.longpaths=true', '-c', 'core.quotepath=false',
        '-c', 'core.whitespace=cr-at-eol', 'diff', '--cached', '--check'],
        cwd=ROOT, env=env, capture_output=True)
    if result.returncode not in (0, 2):
        raise RuntimeError('WhitespaceCommandFailed')
    permitted, unexpected, parsed = {}, [], 0
    for line in result.stdout.decode('utf-8').splitlines():
        match = re.match(r'^([^+].*):(\d+): (.+)\.$', line)
        if not match:
            if line and not line.startswith('+'):
                unexpected.append(dict(diagnostic='UnparsedWhitespaceOutput',
                    lineSHA256=hashlib.sha256(line.encode('utf-8')).hexdigest()))
            continue
        path, number, kind = match[1], int(match[2]), match[3]
        parsed += 1
        row, reason = proof['files'].get(path), None
        if (row and path.startswith('Verification/Evidence/') and row['selection'] == 'prior-cut-evidence'
              and kind in {'trailing whitespace', 'new blank line at EOF'}):
            reason = 'ByteBoundHistoricalOrRetainedEvidence'
        elif (row and path == 'Verification/Evidence/Review116/Backend/HarnessCorrection.patch'
              and row['sha256'] == 'aacd91b433dc6b73cb4502cc29027262f6458885bee61f6250f268edc5509836'
              and kind == 'trailing whitespace'):
            reason = 'ExactRetainedSchemaHarnessPatchContext'
        elif (row and row['selection'] == 'canonical-app' and path.endswith(('.meta', '.asset'))
              and kind == 'trailing whitespace'):
            source = ROOT / row['source']
            content = source.read_bytes()
            if hashlib.sha256(content).hexdigest() != row['sha256']:
                raise RuntimeError('SerializedWhitespaceSourceChanged')
            lines = content.splitlines()
            if number <= len(lines) and re.fullmatch(rb'[ \t]*[A-Za-z_][A-Za-z_0-9]*:[ \t]+', lines[number-1]):
                reason = 'ByteBoundUnityEmptySerializedField'
        elif (row and path == 'Backend/tests/test_leaderboard_refresh115.py'
              and row['selection'] == 'sealed-non-unity' and kind == 'new blank line at EOF'):
            reason = 'ExactFullSuiteTestBytesWithFinalBlankLine'
        if reason:
            permitted[reason] = permitted.get(reason, 0) + 1
        else:
            unexpected.append(dict(path=path, line=number, diagnostic=kind))
    if result.returncode and not parsed:
        raise RuntimeError('UnclassifiedWhitespaceOutput')
    if result.stderr.strip():
        unexpected.append(dict(diagnostic='WhitespaceCommandStderr',
            sha256=hashlib.sha256(result.stderr).hexdigest()))
    return dict(status='PASS_CR_AWARE' if not unexpected else 'REVIEW_OUTPUT',
        fullRawDiffCheckExitCode=result.returncode, fullRawDiffCheckPassed=result.returncode == 0,
        parsedDiagnostics=parsed, preservedDiagnosticsByPolicy=permitted,
        unexpectedActiveCodeOrUnboundDiagnostics=unexpected,
        policy='CR-aware complete diagnostic review. Preserve only frozen prior-cut evidence, one exact retained patch context, empty Unity serialized fields, and one exact full-suite test EOF. Active116 helpers, unknown output and all other warnings fail. No source bytes normalized.')


def prepare(manifest_path, tag):
    if not tag.isalnum() or len(tag) > 20:
        raise ValueError('FreshSafeSnapshotStageTagRequired')
    BASE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    app_manifest = json.loads(manifest_path.read_text('utf-8'))
    non = json.loads((OUT / 'NonUnityCommitSource116.json').read_text('utf-8'))
    default_index = ROOT / '.git/index'
    ordinary_index_before = sha(default_index) if default_index.is_file() else None
    head = git('rev-parse', 'HEAD').decode().strip()
    if head != INITIAL_HEAD:
        raise RuntimeError('HeadChangedReviewBeforePreparingSelectedSnapshot')
    selected = {}
    for relative, metadata in app_manifest['files'].items():
        source = APP / relative.removeprefix('Unity/')
        if sha(source) != metadata['sha256']:
            raise RuntimeError('CanonicalAppInputChanged: ' + relative)
        selected[relative] = (source, '100644', 'canonical-app')
    for relative, metadata in non['files'].items():
        source = NON_UNITY / metadata['snapshotRelativePath']
        if sha(source) != metadata['copiedSHA256']:
            raise RuntimeError('SealedNonUnityInputChanged: ' + relative)
        selected[relative] = (source, metadata['gitMode'], 'sealed-non-unity')
    # Root-owned explicit overrides contain final handoff documentation only.
    overrides = OUT / 'CommitOverrides116.json'
    if overrides.is_file():
        for relative, metadata in json.loads(overrides.read_text('utf-8'))['files'].items():
            source = ROOT / metadata['source']
            if sha(source) != metadata['sha256']:
                raise RuntimeError('FinalDocumentationOverrideChanged')
            selected[relative] = (source, '100644', 'explicit-final-review-override')
    for source in (ROOT / 'Verification/Tools/Review116').rglob('*'):
        if source.is_file() and source.suffix in {'.py', '.ps1', '.json', '.cs', '.template', '.txt'}:
            selected[source.relative_to(ROOT).as_posix()] = (source, '100644', 'owned-review116-tool')
    tracked = set(git('ls-files', '-z').decode('utf-8').split('\0'))
    candidates = git('ls-files', '--others', '--exclude-standard', '-z').decode('utf-8').split('\0')
    candidates += git('diff', '--name-only', '-z').decode('utf-8').split('\0')
    excluded = []
    for relative in sorted(set(candidates)):
        if not relative or not relative.startswith('Verification/Evidence/'):
            continue
        source = ROOT / relative
        if not source.is_file() or source.is_symlink():
            excluded.append(dict(path=relative, reason='not-regular-evidence'))
            continue
        owned = relative.startswith('Verification/Evidence/Review116/') or relative.startswith(
            'Verification/Evidence/Review93/Backend/Review116_Operational')
        newer = source.stat().st_mtime > CUT_SECONDS
        if newer and not owned:
            excluded.append(dict(path=relative, reason='newer-than-selected-cut'))
            continue
        if '/003_reward_long_path_diagnostic/' in relative:
            excluded.append(dict(path=relative, reason='raw-historical-long-path-diagnostic'))
            continue
        if relative not in tracked and source.name.lower() in {'stdout.txt', 'stderr.txt'}:
            excluded.append(dict(path=relative, reason='raw-stdout-stderr-local-only'))
            continue
        if source.suffix.lower() == '.log':
            if 'sanitized' not in relative.lower():
                excluded.append(dict(path=relative, reason='raw-log-local-only'))
                continue
        elif source.suffix.lower() not in EVIDENCE_SUFFIXES:
            excluded.append(dict(path=relative, reason='raw-binary-archive-or-unclassified-evidence'))
            continue
        if owned and source.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
            # The source of selected, visually reviewed images is explicit.
            choice = OUT / 'SelectedImages116.json'
            chosen = set(json.loads(choice.read_text('utf-8'))['paths']) if choice.is_file() else set()
            if relative not in chosen:
                excluded.append(dict(path=relative, reason='unselected-full-capture-local-only'))
                continue
        selected[relative] = (source, '100644', 'owned-review116-evidence' if owned else 'prior-cut-evidence')
    secret_suffixes = {'.keystore', '.jks', '.p12', '.pfx', '.key', '.apk', '.aab', '.db', '.sqlite3'}
    for relative, (source, _, _) in selected.items():
        if source.suffix.lower() in secret_suffixes or '/.verification-cache/' in relative or '/.venv/' in relative:
            raise RuntimeError('PrivateArtifactRejectedFromSnapshotIndex: ' + relative)
        if source.is_symlink():
            raise RuntimeError('SourceSymlinkRejectedFromSnapshotIndex')
    rows = sorted(selected.items())
    source_lines = ''.join(json.dumps(str(source.resolve()).replace('\\', '/'), ensure_ascii=False) + '\n'
                           for _, (source, _, _) in rows).encode('utf-8')
    hashes = git('hash-object', '-w', '--no-filters', '--stdin-paths', data=source_lines).decode().splitlines()
    if len(hashes) != len(rows):
        raise RuntimeError('ExactGitBlobCountRequired')
    git('read-tree', INITIAL_HEAD, index=True)
    payload = b''.join((mode + ' ' + blob + '\t' + relative).encode('utf-8') + b'\0'
                       for ((relative, (_, mode, _)), blob) in zip(rows, hashes))
    git('update-index', '-z', '--index-info', data=payload, index=True)
    records = {relative: dict(source=source.relative_to(ROOT).as_posix(), sha256=sha(source),
                             bytes=source.stat().st_size, gitBlob=blob, mode=mode, selection=reason)
               for ((relative, (source, mode, reason)), blob) in zip(rows, hashes)}
    if head != git('rev-parse', 'HEAD').decode().strip() or ordinary_index_before != (sha(default_index) if default_index.is_file() else None):
        raise RuntimeError('OrdinaryGitHeadOrIndexChangedDuringSnapshotStaging')
    report = dict(status='PREPARED_ALTERNATE_TESTED_SNAPSHOT_INDEX', tag=tag, head=head,
        ordinaryIndexSHA256=ordinary_index_before, indexPath=INDEX.relative_to(ROOT).as_posix(),
        indexSHA256=sha(INDEX), appManifest=manifest_path.relative_to(ROOT).as_posix(),
        appManifestSHA256=sha(manifest_path), fileCount=len(records),
        sourceBytes=sum(r['bytes'] for r in records.values()), files=records, exclusions=excluded,
        workingTreeAndOrdinaryIndexUnchanged=True, commitPerformed=False,
        trackedEvidenceBasePreserved=True, initialTrackedPathCount=len(tracked))
    save(OUT / ('StagedSnapshot_' + tag + '.json'), report)
    print(json.dumps(dict(status=report['status'], files=len(records), bytes=report['sourceBytes'],
                          report='Verification/Evidence/Review116/Repository/StagedSnapshot_' + tag + '.json')))


def audit(stage_path):
    proof = json.loads(stage_path.read_text('utf-8'))
    entries = git('ls-files', '--stage', '-z', index=True).decode('utf-8').split('\0')
    actual = {}
    for entry in entries:
        if entry:
            info, name = entry.split('\t', 1)
            mode, blob, level = info.split()
            if level != '0':
                raise RuntimeError('UnmergedIndexRejected')
            actual[name] = (mode, blob)
    mismatches = [name for name, row in proof['files'].items()
                  if actual.get(name) != (row['mode'], row['gitBlob']) or sha(ROOT / row['source']) != row['sha256']]
    # Verify Git's stored bytes as well as the index names. This catches an
    # evidence file changing between the batch hash and its manifest read.
    process = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    blob_hashes, blob_bytes = {}, 0
    try:
        for name, row in proof['files'].items():
            blob = row['gitBlob']
            if blob not in blob_hashes:
                process.stdin.write((blob + '\n').encode('ascii'))
                process.stdin.flush()
                header = process.stdout.readline().decode('ascii').strip().split()
                if len(header) != 3 or header[0] != blob or header[1] != 'blob':
                    raise RuntimeError('ExactStoredGitBlobRequired')
                remaining = int(header[2])
                blob_bytes += remaining
                value = hashlib.sha256()
                while remaining:
                    chunk = process.stdout.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise RuntimeError('StoredGitBlobTruncated')
                    value.update(chunk)
                    remaining -= len(chunk)
                if process.stdout.read(1) != b'\n':
                    raise RuntimeError('StoredGitBlobFramingInvalid')
                blob_hashes[blob] = value.hexdigest()
            if blob_hashes[blob] != row['sha256']:
                mismatches.append(name)
    finally:
        process.stdin.close()
        process.wait(timeout=30)
        process.stdout.close()
        process.stderr.close()
    whitespace = whitespace_review(proof)
    stat = git('diff', '--cached', '--stat', index=True).decode('utf-8')
    report = dict(status='PASS_ALTERNATE_INDEX_BYTE_AUDIT' if not mismatches and whitespace['status'] == 'PASS_CR_AWARE' else 'FAIL_ALTERNATE_INDEX_BYTE_AUDIT',
                  stagedManifest=stage_path.relative_to(ROOT).as_posix(), stagedManifestSHA256=sha(stage_path),
                  selectedFileCount=len(proof['files']), totalIndexEntries=len(actual), mismatches=mismatches,
                  storedUniqueBlobCount=len(blob_hashes), storedBlobBytesVerified=blob_bytes,
                  whitespaceCheck=whitespace['status'], whitespaceReview=whitespace, diffStat=stat,
                  scope='Exact alternate-index blob/mode and source-copy comparison. Secret scan and required execution evidence are separate final gates.')
    save(OUT / ('IndexAudit_' + proof['tag'] + '.json'), report)
    print(json.dumps(dict(status=report['status'], mismatches=len(mismatches))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'audit'))
    parser.add_argument('--app-manifest', type=Path)
    parser.add_argument('--tag')
    parser.add_argument('--staged-manifest', type=Path)
    args = parser.parse_args()
    if args.operation == 'prepare':
        if not args.app_manifest or not args.tag:
            parser.error('ExplicitAppManifestAndFreshTagRequired')
        prepare(args.app_manifest.resolve(), args.tag)
    else:
        if not args.staged_manifest:
            parser.error('ExplicitStagedManifestRequired')
        audit(args.staged_manifest.resolve())
