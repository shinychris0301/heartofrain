"""Read-only Unity source audit against final Review112; no Unity execution."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review113'
BASE = ROOT / 'Verification/Evidence/Review112/MainSourcesFinal112_03.json'
BASE_GUID = ROOT / 'Verification/Evidence/Review112/AssetGuidsFinal112_03.json'
PKG = ROOT / '.verification-cache/Teams113/Package/Heart_of_the_Rain_Teams_Leave_R1/Unity'
SCRIPT = ROOT / 'Verification/Tools/Ads85/run_ads85_native.py'
spec = importlib.util.spec_from_file_location('source_audit113', SCRIPT)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def record(path):
    data = path.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def guids():
    values = {}
    for path in (ROOT / 'Unity/Assets').rglob('*.meta'):
        match = re.findall(rb'(?m)^guid:\s*([0-9a-fA-F]{32})\s*$', path.read_bytes())
        if len(match) != 1:
            raise ValueError('Invalid metadata: ' + str(path))
        values[path.relative_to(ROOT / 'Unity').as_posix()] = match[0].decode('ascii').lower()
    if len(values) != len(set(values.values())):
        raise ValueError('GUID collision')
    return values


prior = load(BASE)['files']
old_guids = load(BASE_GUID)
first = api.freeze()
now = first['files']
guid = guids()
changed = [key for key in sorted(prior.keys() & now.keys()) if prior[key] != now[key]]
added = sorted(now.keys() - prior.keys())
removed = sorted(prior.keys() - now.keys())
old_meta = [key for key in prior if key.endswith('.meta')]
old_art = [key for key in prior if key.endswith(('.png', '.jpg', '.jpeg', '.psd', '.asset', '.prefab', '.unity', '.mat'))]
if removed or any(now.get(key) != prior[key] for key in old_meta + old_art):
    raise ValueError('Original Unity metadata or artwork changed')
if any(guid.get(key) != value for key, value in old_guids.items()):
    raise ValueError('Original GUID changed')

client = load(OUT / 'ClientFreeze113_07.json')['files']
if any(now.get(row['path']) != {'sha256': row['sha256'], 'bytes': row['bytes']} for row in client):
    raise ValueError('Client freeze differs')
package = load(OUT / 'PackageReview113.json')
payloads = []
for item in package['newPayloads']:
    path = ROOT / 'Unity' / item['path']
    payloads.append({'path': path.relative_to(ROOT).as_posix(),
                     'matches': record(path) == {'sha256': item['sha256'], 'bytes': item['bytes']}})
package_guids = []
for item in package['newMetas']:
    package_guids.append({'path': item['path'], 'guid': item['guid'],
                          'matches': guid.get(item['path']) == item['guid']})
if not all(item['matches'] for item in payloads + package_guids):
    raise ValueError('Supplied payload/GUID mismatch')

# Match bytes by digest, rather than assuming a similarly named copy is exact.
lookup = {}
for folder in (OUT / 'RetainedSources', OUT / 'ClientBefore'):
    if folder.exists():
        for path in folder.rglob('*'):
            if path.is_file():
                lookup.setdefault(record(path)['sha256'], []).append(path.relative_to(ROOT).as_posix())
changes = []
for key in changed:
    changes.append({'path': key, 'before': prior[key], 'after': now[key],
                    'exactPriorCopies': lookup.get(prior[key]['sha256'], [])})
second = api.freeze()
guid2 = guids()
if first != second or guid != guid2:
    raise ValueError('Concurrent Unity source changes')

(OUT / 'MainSourcesFinal113_03.json').write_text(json.dumps(first, indent=2) + '\n', encoding='utf-8')
(OUT / 'AssetGuidsFinal113_03.json').write_text(json.dumps(guid, indent=2, sort_keys=True) + '\n', encoding='utf-8')
result = {'status': 'PASS_READ_ONLY_SOURCE_AUDIT',
          'scope': 'Twice scanned Unity Assets/Packages/ProjectSettings. No Unity/device/service action; prior copies are hash-verified.',
          'baseline': BASE.relative_to(ROOT).as_posix(), 'baselineRecord': record(BASE),
          'baselineGuids': BASE_GUID.relative_to(ROOT).as_posix(), 'baselineGuidsRecord': record(BASE_GUID),
          'clientFreeze': 'Verification/Evidence/Review113/ClientFreeze113_07.json',
          'final': 'Verification/Evidence/Review113/MainSourcesFinal113_03.json',
          'finalGuids': 'Verification/Evidence/Review113/AssetGuidsFinal113_03.json',
          'baselineInputs': len(prior), 'finalInputs': len(now), 'oldGuidCount': len(old_guids),
          'finalGuidCount': len(guid), 'unchangedOriginalMetadataCount': len(old_meta),
          'unchangedOriginalArtworkAndSerializedCount': len(old_art), 'changed': changes,
          'added': added, 'removed': removed, 'packagePayloads': payloads,
          'packageNewGuids': package_guids, 'doubleScanStable': True,
          'missingRetainedPriorBytes': [row['path'] for row in changes if not row['exactPriorCopies']]}
earlier = load(OUT / 'MainSourcesFinal113.json')['files']
result['sinceEpoch01'] = {'changed': [key for key in sorted(earlier.keys() & now.keys()) if earlier[key] != now[key]],
                          'added': sorted(now.keys() - earlier.keys()), 'removed': sorted(earlier.keys() - now.keys())}
result['earlierAuditRecord'] = record(OUT / 'SourceDelta113.json')
prior_freeze = {row['path']: row for row in load(OUT / 'ClientFreeze113_05.json')['files']}
prior_retained = OUT / 'RetainedSources/BeforeDeferredToast'
result['priorClientCopies'] = []
for name in ('OnlineTeamsLeave113.cs', 'OnlineTeamsPage82.cs'):
    found = [row for path, row in prior_freeze.items() if Path(path).name == name]
    if len(found) != 1: raise ValueError('Prior client record missing: ' + name)
    path = prior_retained / name
    match = record(path) == {'sha256': found[0]['sha256'], 'bytes': found[0]['bytes']}
    result['priorClientCopies'].append({'path': path.relative_to(ROOT).as_posix(), 'matches': match})
if not all(item['matches'] for item in result['priorClientCopies']): raise ValueError('Prior client copy mismatch')
epoch02 = load(OUT / 'MainSourcesFinal113_02.json')['files']
result['sinceEpoch02'] = {'changed': [key for key in sorted(epoch02.keys() & now.keys()) if epoch02[key] != now[key]],
                          'added': sorted(now.keys() - epoch02.keys()), 'removed': sorted(epoch02.keys() - now.keys())}
result['epoch02AuditRecord'] = record(OUT / 'SourceDelta113_02.json')
prior06 = {row['path']: row for row in load(OUT / 'ClientFreeze113_06.json')['files']}
result['beforeNameEllipsisCopies'] = []
for name in ('OnlineTeamsPage82.cs', 'TeamsLifecycleLayout113.cs'):
    found = [row for path, row in prior06.items() if Path(path).name == name]
    if len(found) != 1: raise ValueError('Prior client record missing: ' + name)
    path = OUT / 'RetainedSources/BeforeNameEllipsis' / name
    match = record(path) == {'sha256': found[0]['sha256'], 'bytes': found[0]['bytes']}
    result['beforeNameEllipsisCopies'].append({'path': path.relative_to(ROOT).as_posix(), 'matches': match})
if not all(item['matches'] for item in result['beforeNameEllipsisCopies']): raise ValueError('Prior name-ellipsis copy mismatch')
(OUT / 'SourceDelta113_03.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': result['status'], 'baseline': len(prior), 'final': len(now),
                  'changed': len(changed), 'added': len(added), 'oldGuids': len(old_guids),
                  'finalGuids': len(guid), 'newPackageGuids': len(package_guids),
                  'missingPriorBytes': result['missingRetainedPriorBytes']}, indent=2))
