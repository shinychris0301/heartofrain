"""Build a source-bound, credential-free production file bundle; never deploy or activate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / 'Release/Production122/InactiveVps'
SOURCE_ROOT = r'C:\Apps\HeartOfTheRain\Production122'
BACKEND_ROOT = SOURCE_ROOT + r'\Backend'
SERVICES_ROOT = r'C:\ProgramData\HeartOfTheRain\production-services'
SECRETS_ROOT = r'C:\ProgramData\HeartOfTheRain\production-secrets'
AUTHORITY_ROOT = r'C:\ProgramData\HeartOfTheRain\production-authority'
PYTHON = r'C:\Apps\HeartOfTheRain\Backend\.venv-service\Scripts\python.exe'
BASE_PYTHON = r'C:\Program Files\Python314\python.exe'
VENV_CONFIG = r'C:\Apps\HeartOfTheRain\Backend\.venv-service\pyvenv.cfg'
HOST_PYTHON_VERSION = '3.14.10'
CONFIGS = {'ads.json', 'commerce.json', 'daily_gift.json', 'levels.json', 'rain_cup.json',
           'team_help.json', 'team_invites.json', 'wellworks.json'}
SECRET_FIELDS = {'privatekey', 'secret', 'apikey', 'accesstoken', 'refreshtoken', 'password',
                 'keystorepassword', 'clientsecret', 'notificationkey', 'paymenttoken'}
ANCILLARY_NAMES = ('commerce.example.json', 'registered-products122.json', 'production-runtime.example122.json')
ANCILLARY_REPORT = 'Verification/Evidence/Review122/Payments/DiscoveryFocused122.json'


class BundleError(Exception):
    pass


def need(value, code):
    if not value:
        raise BundleError(code)


def read_plain(path):
    path = Path(path)
    for entry in reversed((path, *path.parents)):
        info = entry.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
             'linked_bundle_source_rejected')
    info = path.stat()
    need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= 1_048_576,
         'regular_bounded_bundle_source_required')
    return path.read_bytes()


def _object(pairs):
    value = {}
    for key, item in pairs:
        need(key not in value, 'duplicate_json_key')
        value[key] = item
    return value


def parse(raw):
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(BundleError('nonfinite_json')))


def public_bytes(raw, *, is_json=False):
    # Actual complete key headers are rejected, including an accidental key in code.
    need(not re.search(rb'-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----', raw),
         'private_key_material_rejected')
    if is_json:
        def visit(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    normalized = re.sub('[^a-z]', '', key.lower())
                    need(not any(normalized.endswith(field) for field in SECRET_FIELDS) or item in (None, ''),
                         'credential_value_rejected')
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)
        visit(parse(raw))
    return raw


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8')


def _service(executable, operation, service_id):
    root = ET.Element('service')
    fields = {'id': service_id, 'name': service_id, 'description': 'INACTIVE production file candidate; not installed or started.',
              'executable': executable,
              'arguments': '-B -m hotr_backend.' + operation + ' --manifest "' + SERVICES_ROOT + r'\production-manifest.json"',
              'workingdirectory': BACKEND_ROOT, 'logpath': SERVICES_ROOT + r'\logs',
              'startmode': 'Manual', 'stoptimeout': '90sec'}
    for key, value in fields.items():
        ET.SubElement(root, key).text = value
    account = ET.SubElement(root, 'serviceaccount')
    ET.SubElement(account, 'domain').text = 'NT AUTHORITY'
    ET.SubElement(account, 'user').text = 'LocalService'
    ET.SubElement(root, 'env', name='PYTHONPATH', value=BACKEND_ROOT)
    ET.SubElement(root, 'env', name='PYTHONNOUSERSITE', value='1')
    log = ET.SubElement(root, 'log', mode='roll-by-size')
    ET.SubElement(log, 'sizeThreshold').text = '1024'
    ET.SubElement(log, 'keepFiles').text = '4'
    ET.SubElement(root, 'onfailure', action='restart', delay='30 sec')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True) + b'\n'


def payload(source_root, report_path, ancillary_report_path=None):
    source_root = Path(source_root).resolve()
    report_raw = read_plain(report_path)
    report = parse(report_raw)
    need(isinstance(report, dict), 'backend_report_object_required')
    need(report.get('status') == 'PASS_BACKEND_SERVICE_TESTS' and report.get('failures') == []
         and report.get('errors') == [] and report.get('sourceInputsChangedDuringRun') == []
         and type(report.get('tests')) is int and report['tests'] > 0
         and type(report.get('executedTests')) is int and report['executedTests'] == report['tests']
         and report.get('skipped') == [] and report.get('actualPinnedWorkerIntegration') is True
         and isinstance(report.get('passed'), list) and len(report['passed']) == report['tests']
         and all(isinstance(name, str) and name for name in report['passed'])
         and len(set(report['passed'])) == report['tests'],
         'passing_source_bound_backend_report_required')
    before, after = report.get('sourceSHA256'), report.get('sourceSHA256After')
    need(isinstance(before, dict) and before == after, 'unchanged_test_source_pins_required')
    package = source_root / 'Backend/hotr_backend'
    runtime = sorted(package.rglob('*.py'))
    need(runtime and (package / '__init__.py').is_file() and (package / 'production_runtime122.py').is_file(),
         'production_runtime_source_required')
    expected_runtime = {name for name in before if name.startswith('Backend/hotr_backend/') and name.endswith('.py')}
    actual_runtime = {path.relative_to(source_root).as_posix() for path in runtime}
    need(actual_runtime == expected_runtime, 'runtime_inventory_does_not_match_tested_snapshot')
    need({p.name for p in (source_root / 'Backend/config').glob('*.json')} == CONFIGS,
         'reviewed_configuration_inventory_required')
    paths = runtime + [source_root / 'Backend/config' / name for name in sorted(CONFIGS)]
    paths += [source_root / 'Backend/requirements.lock', source_root / 'Backend/requirements.in']
    files, originals = {}, {}
    for path in paths:
        relative = path.relative_to(source_root).as_posix()
        need(all(part not in ('.venv', '__pycache__') and not part.startswith('.') for part in path.relative_to(source_root).parts),
             'private_bundle_path_rejected')
        raw = public_bytes(read_plain(path), is_json=path.suffix == '.json')
        need(before.get(relative) == hashlib.sha256(raw).hexdigest(), 'runtime_does_not_match_tested_snapshot')
        files['Source/' + relative] = raw
        originals[relative] = hashlib.sha256(raw).hexdigest()
    ancillary_raw = read_plain(ancillary_report_path or source_root / ANCILLARY_REPORT)
    ancillary = parse(ancillary_raw)
    need(isinstance(ancillary, dict) and ancillary.get('schemaVersion') == 1
         and ancillary.get('scope') == 'owned_production_discovery_and_fixed_origin_scripted_HTTP_SQLite_compatibility'
         and ancillary.get('successful') is True and ancillary.get('sourcesStable') is True
         and ancillary.get('failures') == [] and ancillary.get('errors') == [] and ancillary.get('skipped') == []
         and type(ancillary.get('testsRun')) is int and ancillary['testsRun'] > 0
         and isinstance(ancillary.get('inputSha256'), dict), 'passing_ancillary_source_review_required')
    ancillary_files, ancillary_inputs = {}, {}
    for name in ANCILLARY_NAMES:
        path = source_root / 'Release/RuStore' / name
        raw = public_bytes(read_plain(path), is_json=True)
        relative = path.relative_to(source_root).as_posix()
        digest = hashlib.sha256(raw).hexdigest()
        need(ancillary['inputSha256'].get(relative) == digest, 'ancillary_input_does_not_match_reviewed_snapshot')
        ancillary_files[name] = raw
        ancillary_inputs[relative] = digest
        if name != 'production-runtime.example122.json':
            files['Source/' + relative] = raw
    catalog = parse(files['Source/Release/RuStore/commerce.example.json'])
    catalog.update(enabled=False, sandbox=False, appId=None)
    for product in catalog.get('products', []):
        product['enabled'] = False
    files['Services/commerce.candidate.json'] = encoded(catalog)
    manifest = parse(ancillary_files['production-runtime.example122.json'])
    manifest['configDirectory'] = BACKEND_ROOT + r'\config'
    manifest['commerceConfig'] = SERVICES_ROOT + r'\commerce.json'
    manifest['provider']['privateKeyFile'] = SECRETS_ROOT + r'\rustore-private-key'
    manifest['provider']['notificationKeyFile'] = SECRETS_ROOT + r'\rustore-notification-key'
    files['Services/production-manifest.INCOMPLETE.json'] = encoded(manifest)
    for name in ('HOTRProduction122.xml.example', 'HOTRReconciliation122.xml.example'):
        operation = ('production_runtime122 start' if name.startswith('HOTRProduction') else
                     'production_ops122 supervise-reconciliation --max-jobs 5 --seed-limit 20 --poll-seconds 300 --interval-seconds 30')
        service_id = name.removesuffix('.xml.example')
        files['Services/' + name] = _service(PYTHON, operation, service_id)
    files['Services/KEY_DESTINATIONS122.txt'] = read_plain(ASSETS / 'KEY_DESTINATIONS122.txt')
    files['Services/INACTIVE_SETUP122.txt'] = read_plain(ASSETS / 'SETUP122.txt')
    files['Services/Caddyfile.production122.example'] = read_plain(ROOT / 'Release/Production122/operations/Caddyfile.production122.example')
    need(sum(map(len, files.values())) <= 16_777_216 and len(files) <= 512, 'bounded_bundle_required')
    for name, raw in files.items():
        need(re.fullmatch(r'(Source|Services)/[A-Za-z0-9_./-]+', name) and '..' not in name.split('/'), 'invalid_bundle_entry')
        public_bytes(raw, is_json=name.endswith('.json'))
    body = {'version': 1, 'kind': 'HeartOfTheRainInactiveProductionFiles122',
            'state': 'InactiveFilesOnly', 'authorityInitializationAllowed': False,
            'serviceInstallationAllowed': False, 'providerActivationAllowed': False,
            'sourceRoot': SOURCE_ROOT, 'backendRoot': BACKEND_ROOT, 'servicesRoot': SERVICES_ROOT,
            'secretsRoot': SECRETS_ROOT, 'authorityRoot': AUTHORITY_ROOT, 'pythonExecutable': PYTHON,
            'basePythonExecutable': BASE_PYTHON, 'venvConfiguration': VENV_CONFIG,
            'onHostPythonVersionRequired': HOST_PYTHON_VERSION,
            'requirementsLockSHA256': originals['Backend/requirements.lock'],
            'testReport': {'sha256': hashlib.sha256(report_raw).hexdigest(), 'tests': report['tests'],
                           'executedTests': report.get('executedTests'), 'skippedTests': report.get('skipped', []),
                           'actualPinnedWorkerIntegration': report.get('actualPinnedWorkerIntegration', False)},
            'testedBackendSourceSHA256': originals,
            'reviewedAncillaryInputSHA256': ancillary_inputs,
            'ancillaryReview': {'sha256': hashlib.sha256(ancillary_raw).hexdigest(),
                                'tests': ancillary['testsRun'], 'scope': ancillary['scope'],
                                'providerAcceptanceVerified': False, 'realUnityWorkerExecutionClaimed': False},
            'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in sorted(files.items())}}
    return files, body


def build(source_root, report_path, destination, ancillary_report_path=None):
    target = Path(destination).absolute()
    need(target.suffix.lower() == '.zip' and not target.exists() and target.parent.is_dir(), 'fresh_archive_destination_required')
    files, manifest = payload(source_root, report_path, ancillary_report_path)
    # Every source is materialized before exclusive archive creation; no source
    # is re-read into a different epoch while the archive is being written.
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(files.items()):
            archive.writestr(name, raw)
        archive.writestr('ProductionFiles122.json', encoded(manifest))
    return {'status': 'BUILT_INACTIVE_PRODUCTION_FILES122', 'files': len(files), 'bytes': target.stat().st_size,
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'manifestSHA256': hashlib.sha256(encoded(manifest)).hexdigest(),
            'testReportSHA256': manifest['testReport']['sha256'], 'productionActivated': False,
            'authorityInitialized': False, 'servicesInstalled': False, 'keysCreated': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--test-report', type=Path, required=True)
    parser.add_argument('--ancillary-review', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build(args.source_root, args.test_report, args.out, args.ancillary_review)
    except (OSError, ValueError, BundleError, zipfile.BadZipFile):
        print(json.dumps({'status': 'BLOCKED_INACTIVE_PRODUCTION_FILES122'}))
        return 1
    print(json.dumps(result, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
