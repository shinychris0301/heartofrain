"""Read-only secret/private-artifact screen of exact alternate-index blobs.

No credential value, raw device selector or matching content is emitted. This
is a bounded screen and a review aid, not a guarantee that all secrets can be
recognized. Git's ordinary index, HEAD and working files are never changed.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
TEXT = {'.cs', '.py', '.json', '.xml', '.asset', '.meta', '.md', '.txt', '.html', '.js', '.css',
    '.yaml', '.yml', '.sql', '.toml', '.gradle', '.properties', '.sh', '.ps1', '.bat', '.cmd',
    '.unity', '.csproj', '.sln', '.config', '.template', '.diff', '.patch', '.csv', '.svg', '.log'}
PRIVATE_SUFFIXES = {'.keystore', '.jks', '.p12', '.pfx', '.key', '.p8', '.db', '.sqlite', '.sqlite3', '.dmp'}
RAW_SUFFIXES = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.log', '.zip', '.7z'}
PATTERNS = {
    'PrivateKeyPem': re.compile(rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'),
    'GithubCredential': re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'AwsAccessCredential': re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'SlackCredential': re.compile(rb'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
    'OpenAiCredential': re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{30,}\b'),
    'GoogleApiCredential': re.compile(rb'\bAIza[0-9A-Za-z_-]{35}\b'),
    'GoogleOauthCredential': re.compile(rb'\bya29\.[0-9A-Za-z_-]{30,}\b'),
    'LiteralJwt': re.compile(rb'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{20,}\b'),
}


def need(value, code):
    if not value:
        raise RuntimeError(code)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    need(re.fullmatch('[A-Za-z0-9]{1,25}', args.tag), 'FreshAuditTagRequired')
    stage = args.stage.resolve()
    need(stage.is_relative_to(ROOT / 'Verification/Evidence/Review116/Repository'), 'OwnedStageManifestRequired')
    metadata = json.loads(stage.read_text('utf-8-sig'))
    index = (ROOT / metadata['indexPath']).resolve()
    need(index.is_relative_to(ROOT / '.verification-cache/Review116/Git')
        and sha(index) == metadata['indexSHA256'], 'ExactAlternateIndexRequired')
    out = ROOT / 'Verification/Evidence/Review116/Repository' / ('SecretIndexAudit_' + args.tag + '.json')
    need(not out.exists(), 'RetainEarlierSecretScreen')
    env = dict(os.environ, GIT_INDEX_FILE=str(index))

    def git(*arguments):
        result = subprocess.run(['git', '-c', 'core.longpaths=true', *arguments], cwd=ROOT,
            env=env, capture_output=True)
        need(result.returncode == 0, 'ReadOnlyGitAuditCommandFailed')
        return result.stdout

    head_before = git('rev-parse', 'HEAD').decode().strip()
    need(head_before == metadata['head'], 'SamePrecommitHeadRequired')
    entries = {}
    for raw in git('ls-files', '--stage', '-z').split(b'\0'):
        if raw:
            info, name = raw.split(b'\t', 1)
            mode, oid, level = info.decode().split()
            need(level == '0', 'NoUnmergedIndexAllowed')
            entries[name.decode('utf-8')] = (mode, oid)
    changes = [name.decode('utf-8') for name in git('diff', '--cached', '--name-only', '-z', metadata['head']).split(b'\0') if name]
    deletions = [name for name in changes if name not in entries]
    findings = []
    text_files, decoded_profile_files, text_bytes, scanned_blobs = 0, 0, 0, set()

    def inspect(name, content):
        nonlocal text_files, text_bytes
        text_files += 1
        text_bytes += len(content)
        for category, pattern in PATTERNS.items():
            for match in pattern.finditer(content):
                findings.append(dict(path=name, category=category,
                    line=content.count(b'\n', 0, match.start()) + 1,
                    matchedBytes=match.end() - match.start()))

    process = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for name in changes:
            if name not in entries:
                continue
            mode, oid = entries[name]
            path = Path(name)
            suffix, leaf = path.suffix.lower(), path.name.lower()
            if suffix in PRIVATE_SUFFIXES or leaf == '.env' or '.private' in leaf:
                findings.append(dict(path=name, category='PrivateArtifactFilename'))
            if name.startswith('Verification/Evidence/') and (suffix in RAW_SUFFIXES
                and not (suffix == '.log' and 'sanitized' in leaf)
                or leaf in ('stdout.txt', 'stderr.txt')):
                findings.append(dict(path=name, category='RawNewEvidenceArtifact'))
            if mode not in ('100644', '100755'):
                findings.append(dict(path=name, category='NonRegularIndexMode'))
            if suffix not in TEXT and leaf not in ('.gitignore', '.gitattributes', '.editorconfig') and not leaf.startswith('.env'):
                continue
            if oid in scanned_blobs:
                continue
            scanned_blobs.add(oid)
            process.stdin.write((oid + '\n').encode('ascii'))
            process.stdin.flush()
            header = process.stdout.readline().decode('ascii').strip().split()
            need(len(header) == 3 and header[0] == oid and header[1] == 'blob', 'ExactIndexedBlobRequired')
            size = int(header[2])
            body = process.stdout.read(size)
            need(len(body) == size and process.stdout.read(1) == b'\n', 'IndexedBlobFramingRequired')
            inspect(name, body)
            if name == 'Verification/Tools/Review116/ApprovedLtsProfile116.json':
                profile = json.loads(body)
                for child, row in profile['files'].items():
                    data = base64.b64decode(row['dataBase64'], validate=True)
                    need(hashlib.sha256(data).hexdigest() == row['sha256'] and len(data) == row['bytes'],
                        'DecodedPublicProfileHashMismatch')
                    decoded_profile_files += 1
                    if Path(child).suffix.lower() in TEXT:
                        inspect(name + '#' + child, data)
    finally:
        process.stdin.close()
        process.wait(timeout=30)
        process.stdout.close()
        process.stderr.close()
    index_stable = sha(index) == metadata['indexSHA256']
    head_stable = git('rev-parse', 'HEAD').decode().strip() == head_before
    value = dict(status='PASS_EXACT_INDEX_SECRET_PRIVATE_ARTIFACT_SCREEN116'
        if not findings and not deletions and index_stable and head_stable else 'REVIEW_EXACT_INDEX_SECRET_SCREEN116',
        stageManifest=args.stage.as_posix(), stageManifestSHA256=sha(stage), expectedIndexSHA256=metadata['indexSHA256'],
        changedIndexPaths=len(changes), deletedIndexPaths=deletions, uniqueTextBlobs=len(scanned_blobs),
        textAndDecodedProfileFilesScreened=text_files, textBytesScreened=text_bytes,
        decodedPublicProfileFiles=decoded_profile_files, findings=findings,
        indexBytesUnchanged=index_stable, headUnchanged=head_stable, runnerSHA256=sha(Path(__file__)),
        ordinaryIndexWritePerformed=False, scope='Read-only exact changed/new alternate-index Git blobs, private artifact/log filenames and decoded public LTS profile screened with explicit high-signal credential patterns. Matching values are never emitted. Symbolic fixture assignments require context review separately; absence of a pattern match is not a universal secret-free guarantee. Existing unchanged tracked evidence remains untouched.')
    with out.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=value['status'], changedPaths=len(changes), findings=len(findings),
        decodedProfileFiles=decoded_profile_files, report=out.relative_to(ROOT).as_posix())))


if __name__ == '__main__':
    main()
