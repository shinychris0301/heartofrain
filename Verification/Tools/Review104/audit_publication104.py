"""Local104 evidence/hash/link audit only; does not run Unity or the game."""
import hashlib
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review104'
proofs = {}


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def bindings(value):
    if isinstance(value, dict):
        if all(key in value for key in ('path', 'sha256', 'bytes')):
            path = (ROOT / value['path']).resolve()
            assert path.is_relative_to(ROOT), value['path']
            assert path.is_file() and path.stat().st_size == value['bytes'], value['path']
            if path not in proofs:
                proofs[path] = digest(path)
            assert proofs[path] == value['sha256'].lower(), value['path']
        for child in value.values():
            bindings(child)
    elif isinstance(value, list):
        for child in value:
            bindings(child)


names = ['Summary.json', 'SourceDelta104.json', 'CompilerWarnings104.json',
         'FailuresAndEpochs104.json', 'Preparation/Host02/Report.json',
         'Preparation/Clone01/Report.json']
data = {name: read(OUT / name) for name in names}
for document in data.values():
    bindings(document)
summary = data['Summary.json']
assert summary['targetedImplementationAndEditorChecksPassed'] is True
assert summary['fullyVetted'] is False and summary['productionApproved'] is False
expected = dict(ConfigurationMain01=149, PolicyMain02=41, ServerCoreMain01=55,
                TeamsMain01=268, ConfigurationIsolated01=158, PackagingIsolated01=36)
assert {row['tag']: row['checks'] for row in summary['native']} == expected
for row in summary['native']:
    report = read(ROOT / row['nativeReport']['path'])
    assert report['checks'] == expected[row['tag']] and report['status'].startswith('PASS')
assert summary['deliveredResource']['actualRuntimeTryRead'] is True
assert summary['deliveredResource']['buildPipelineInvoked'] is False
assert summary['android']['apkBuiltThisCheckpoint'] is False
assert summary['backend']['unchangedFrom103'] is True
host = data['Preparation/Host02/Report.json']
assert host['executedTests'] == 6 and host['testsPassed'] is True
assert host['untouchedExampleBlocked'] is True
assert host['exampleReply']['code'] == 'MISSING_OR_PLACEHOLDER_STAGING_ORIGIN'
assert read(OUT / 'Native/PolicyMain01/StagingPolicy104.json')['status'].startswith('FAIL')
assert read(OUT / 'Preparation/Host01/Report.json')['testExitCode'] != 0


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count = 0

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key not in ('href', 'src') or not value:
                continue
            url = urlsplit(value)
            if url.scheme or url.netloc or not url.path:
                continue
            path = (OUT / unquote(url.path)).resolve()
            assert path.is_relative_to(ROOT) and path.is_file(), value
            self.count += 1


links = Links()
links.feed((OUT / 'Comparison.html').read_text(encoding='utf-8'))
outputs = names + ['Comparison.html',
    '../../../Codex_Handoff/Documentation/104_STAGING_BUILD_CONFIGURATION_REVIEW.txt',
    '../../../Codex_Handoff/Documentation/00_START_HERE.md',
    '../../../Codex_Handoff/Documentation/01_STATUS_AND_DECISIONS.md',
    '../../../Release/RuStore/STAGING_BUILD_CONFIGURATION104.txt',
    '../../../Release/RuStore/staging-build.example.json']
result = dict(schemaVersion=1, status='PASS_LOCAL_PUBLICATION_INTEGRITY104',
    utc=datetime.now(timezone.utc).isoformat(),
    scope='Filesystem hashes, metadata and local links only. Historical source epochs use sealed manifests; no Unity, app, backend/provider, APK or device operation.',
    uniqueBoundProofFilesVerified=len(proofs), localLinksChecked=links.count,
    selectedNativePasses=6, hostTests=6, retainedFailedAttempts=2,
    fullyVetted=False, productionApproved=False,
    outputHashes=[dict(path=(OUT / name).resolve().relative_to(ROOT).as_posix(),
                       sha256=digest(OUT / name), bytes=(OUT / name).stat().st_size)
                  for name in outputs])
(OUT / 'PublicationAudit104.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: value for key, value in result.items() if key != 'outputHashes'}))
