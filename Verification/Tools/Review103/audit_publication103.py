"""Local publication/hash audit only; does not execute the app or backend."""
import hashlib
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review103'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


proofs = {}


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


files = ['Summary.json', 'SourceDelta103.json', 'CompilerWarnings103.json',
         'InitialVisualReview103.json', 'Reviewed/Selection103.json']
data = {name: json.loads((OUT / name).read_text(encoding='utf-8-sig')) for name in files}
for document in data.values():
    bindings(document)
assert data['Summary.json']['targetedCodeAndEditorVerificationPassed'] is True
assert data['Summary.json']['fullyVetted'] is False
assert data['Summary.json']['productionApproved'] is False
assert [row['checks'] for row in data['Summary.json']['native']] == [268, 11665, 535]
assert data['Summary.json']['backend']['executedTests'] == 18
for selected in data['Reviewed/Selection103.json']['images']:
    assert selected['accepted'] and not selected['physicalDevice']
    assert selected['source']['sha256'] == selected['reviewedCopy']['sha256']


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
outputs = files + ['Comparison.html']
outputs += ['../../../Codex_Handoff/Documentation/103_TEAMS_DISCOVERY_AND_BACKEND_SETUP_REVIEW.txt',
            '../../../Codex_Handoff/Documentation/00_START_HERE.md',
            '../../../Codex_Handoff/Documentation/01_STATUS_AND_DECISIONS.md',
            '../../../Release/RuStore/VK_BACKEND_AND_CALLBACK_CONFIGURATION.txt']
report = dict(schemaVersion=1, status='PASS_LOCAL_PUBLICATION_INTEGRITY103',
              utc=datetime.now(timezone.utc).isoformat(),
              scope='Filesystem hashes, metadata and local links only. No app, Unity, backend service, provider, Android or device operation.',
              uniqueBoundProofFilesVerified=len(proofs), localLinksChecked=links.count,
              reviewedEditorImages=2, fullyVetted=False, productionApproved=False,
              outputHashes=[dict(path=(OUT / name).resolve().relative_to(ROOT).as_posix(),
                                 sha256=digest(OUT / name), bytes=(OUT / name).stat().st_size)
                            for name in outputs])
(OUT / 'PublicationAudit103.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: value for key, value in report.items() if key != 'outputHashes'}))
