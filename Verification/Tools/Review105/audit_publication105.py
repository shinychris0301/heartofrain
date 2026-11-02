"""Independent local105 evidence integrity check; never starts an application."""
import hashlib
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review105'
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


names = ['Summary.json', 'SourceDelta105.json', 'FailuresAndEpochs105.json', 'Diagnostics105.json']
data = {name: read(OUT / name) for name in names}
for document in data.values():
    bindings(document)
summary = data['Summary.json']
assert summary['targetedCodeAndLocalOperationalVerificationPassed'] is True
assert not summary['fullyVetted'] and not summary['productionApproved']
assert summary['tests']['distinctPassedTests'] == 52 and summary['tests']['repeatedOpsTests'] == 12
assert sum(summary['tests']['passedByModule'].values()) == 52
tcp = summary['actualTcp']
assert (tcp['checks'], tcp['requests'], tcp['actualUvicornStarts']) == (116, 29, 3)
assert tcp['observedServerTerminations'] == tcp['observedClosedPorts'] == 3
assert tcp['servicesLeftRunning'] is False and tcp['coinsEach'] == 1250
assert (tcp['teamCount'], tcp['memberCount'], tcp['messageCount']) == (1, 2, 1)
assert not tcp['automaticActivationPerformed'] and not tcp['gracefulShutdownClaim']
assert data['SourceDelta105.json']['all5482UnityInputsUnchanged']
assert data['SourceDelta105.json']['all101ExistingBackendInputsPreserved']
final_report = read(OUT / 'TCP/Flow02/Report.json')
assert final_report['status'] == 'PASS_STAGING105_TCP' and final_report['checks'] == 116
assert read(OUT / 'TCP/Flow01/Report.json')['status'] == 'FAIL_STAGING105_TCP_CLEANUP'
power = read(OUT / 'PowerShell/Example01/Report.json')
assert power['pythonBootstrapReached'] is False and power['executionPolicyOverridden'] is False
assert power['exitCode'] != 0


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
    '../../../Codex_Handoff/Documentation/105_STAGING_SERVER_OPERATIONS_REVIEW.txt',
    '../../../Codex_Handoff/Documentation/00_START_HERE.md',
    '../../../Codex_Handoff/Documentation/01_STATUS_AND_DECISIONS.md',
    '../../../Release/RuStore/STAGING_SERVER_OPERATIONS105.txt',
    '../../../Release/RuStore/staging-server.example.json',
    '../../../Backend/Start-Staging105.ps1']
result = dict(schemaVersion=1, status='PASS_LOCAL_PUBLICATION_INTEGRITY105',
    utc=datetime.now(timezone.utc).isoformat(),
    scope='Filesystem hashes, metadata and local links only; historical sources are bound to their recorded epochs. No tests, process start, network, provider, Unity or device operation.',
    uniqueBoundProofFilesVerified=len(proofs), localLinksChecked=links.count,
    distinctTests=52, repeatedOpsTests=12, tcpChecks=116,
    retainedFailedTcpAttempts=1, retainedPowerShellPolicyGate=True,
    fullyVetted=False, productionApproved=False,
    outputHashes=[dict(path=(OUT / name).resolve().relative_to(ROOT).as_posix(),
                       sha256=digest(OUT / name), bytes=(OUT / name).stat().st_size)
                  for name in outputs])
(OUT / 'PublicationAudit105.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: value for key, value in result.items() if key != 'outputHashes'}))
