"""Artifact/secret/path controls with synthetic report fixtures; not production runtime tests."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

SPEC = importlib.util.spec_from_file_location('inactive122', Path(__file__).with_name('build_inactive_vps122.py'))
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class InactiveBundle122Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='hotr-inactive122-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for folder in ('Backend/hotr_backend', 'Backend/config', 'Release/RuStore'):
            (self.root / folder).mkdir(parents=True)
        (self.root / 'Backend/hotr_backend/__init__.py').write_bytes(b'')
        (self.root / 'Backend/hotr_backend/production_runtime122.py').write_bytes(b'# synthetic source fixture\n')
        for name in tool.CONFIGS:
            (self.root / 'Backend/config' / name).write_text('{}\n', encoding='utf-8')
        for name in ('requirements.lock', 'requirements.in'):
            (self.root / 'Backend' / name).write_text('sample-package==1.0\n', encoding='utf-8')
        (self.root / 'Release/RuStore/commerce.example.json').write_text(json.dumps({'enabled': False, 'sandbox': True,
             'appId': None, 'products': [{'id': 'synthetic', 'enabled': False, 'coins': 1000}]}), encoding='utf-8')
        (self.root / 'Release/RuStore/registered-products122.json').write_text('{"applicationId":null}', encoding='utf-8')
        (self.root / 'Release/RuStore/production-runtime.example122.json').write_text('{"provider":{"keyId":""}}', encoding='utf-8')
        self.report_path = self.root / 'synthetic-test-report.json'
        self.destination = self.root / 'inactive.zip'
        self.report()

    def report(self):
        pins = {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.root / 'Backend').rglob('*') if p.is_file() and p.suffix in ('.py', '.json', '.in', '.lock')}
        value = {'status': 'PASS_BACKEND_SERVICE_TESTS', 'tests': 1, 'executedTests': 1,
                 'passed': ['synthetic.artifact.fixture'], 'actualPinnedWorkerIntegration': True,
                 'failures': [], 'errors': [], 'skipped': [], 'sourceInputsChangedDuringRun': [],
                 'sourceSHA256': pins, 'sourceSHA256After': pins}
        self.report_path.write_text(json.dumps(value), encoding='utf-8')
        review = self.root / tool.ANCILLARY_REPORT
        review.parent.mkdir(parents=True, exist_ok=True)
        review.write_text(json.dumps({'schemaVersion': 1,
             'scope': 'owned_production_discovery_and_fixed_origin_scripted_HTTP_SQLite_compatibility',
             'successful': True, 'sourcesStable': True, 'testsRun': 1, 'failures': [], 'errors': [], 'skipped': [],
             'inputSha256': {'Release/RuStore/' + name: hashlib.sha256((self.root / 'Release/RuStore' / name).read_bytes()).hexdigest()
                            for name in tool.ANCILLARY_NAMES}}), encoding='utf-8')
        return value

    def test_source_bound_payload_has_no_activation_or_key_files(self):
        result = tool.build(self.root, self.report_path, self.destination)
        self.assertEqual(result['status'], 'BUILT_INACTIVE_PRODUCTION_FILES122')
        self.assertFalse(result['keysCreated'])
        with zipfile.ZipFile(self.destination) as archive:
            manifest = json.loads(archive.read('ProductionFiles122.json'))
            self.assertEqual(set(archive.namelist()), set(manifest['files']) | {'ProductionFiles122.json'})
            for name, pin in manifest['files'].items():
                raw = archive.read(name)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), pin['sha256'])
                self.assertEqual(len(raw), pin['bytes'])
            self.assertFalse(manifest['authorityInitializationAllowed'])
            self.assertFalse(manifest['serviceInstallationAllowed'])
            self.assertFalse(manifest['providerActivationAllowed'])
            self.assertFalse(any(name.startswith('Secrets/') or name.endswith('rustore-private-key') for name in archive.namelist()))
            candidate = json.loads(archive.read('Services/production-manifest.INCOMPLETE.json'))
            self.assertEqual(candidate['configDirectory'], tool.BACKEND_ROOT + r'\config')
            self.assertEqual(candidate['provider']['keyId'], '')
            self.assertNotIn('Services/production-manifest.json', archive.namelist())
            self.assertFalse(json.loads(archive.read('Services/commerce.candidate.json'))['enabled'])

    def test_changed_runtime_rejects_before_any_archive_creation(self):
        (self.root / 'Backend/hotr_backend/production_runtime122.py').write_bytes(b'# newer untested bytes\n')
        with self.assertRaises(tool.BundleError):
            tool.build(self.root, self.report_path, self.destination)
        self.assertFalse(self.destination.exists())

    def test_deleted_tested_module_cannot_silently_disappear_from_bundle(self):
        optional = self.root / 'Backend/hotr_backend/optional_fixture.py'
        optional.write_bytes(b'# synthetic tested module\n')
        self.report()
        optional.unlink()
        with self.assertRaises(tool.BundleError) as failed:
            tool.build(self.root, self.report_path, self.destination)
        self.assertEqual(str(failed.exception), 'runtime_inventory_does_not_match_tested_snapshot')
        self.assertFalse(self.destination.exists())

    def test_failed_or_changed_test_report_is_not_a_bundle_authorization(self):
        for variant in ('status', 'failure', 'changed'):
            value = self.report()
            if variant == 'status':
                value['status'] = 'FAIL_BACKEND_SERVICE_TESTS'
            elif variant == 'failure':
                value['failures'] = ['synthetic']
            else:
                value['sourceInputsChangedDuringRun'] = ['synthetic.py']
            self.report_path.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaises(tool.BundleError):
                tool.build(self.root, self.report_path, self.destination)
            self.assertFalse(self.destination.exists())

    def test_credentials_and_complete_private_key_marker_rejected_even_if_hash_pinned(self):
        private = self.root / 'Backend/config/ads.json'
        private.write_text('{"accessToken":"synthetic-token-never-package"}', encoding='utf-8')
        self.report()
        with self.assertRaises(tool.BundleError):
            tool.build(self.root, self.report_path, self.destination)
        private.write_text('{}', encoding='utf-8')
        (self.root / 'Backend/hotr_backend/production_runtime122.py').write_bytes(b'# -----BEGIN PRIVATE KEY-----\n')
        self.report()
        with self.assertRaises(tool.BundleError):
            tool.build(self.root, self.report_path, self.destination)
        self.assertFalse(self.destination.exists())

    def test_prefixed_secret_fields_are_rejected_but_file_references_are_public(self):
        private = self.root / 'Backend/config/ads.json'
        for name in ('HOTR_VK_CLIENT_SECRET', 'HOTR_RUSTORE_PRIVATE_KEY'):
            private.write_text(json.dumps({name: 'synthetic-not-a-key'}), encoding='utf-8')
            self.report()
            with self.assertRaises(tool.BundleError):
                tool.build(self.root, self.report_path, self.destination)
            self.assertFalse(self.destination.exists())
        private.write_text('{"HOTR_RUSTORE_PRIVATE_KEY_FILE":"C:\\\\private\\\\key-reference"}', encoding='utf-8')
        self.report()
        tool.build(self.root, self.report_path, self.destination)

    def test_partial_or_skipped_run_and_missing_actual_worker_are_not_accepted(self):
        for name, item in (('executedTests', 0), ('skipped', ['synthetic']),
                           ('actualPinnedWorkerIntegration', False), ('passed', [])):
            value = self.report()
            value[name] = item
            self.report_path.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaises(tool.BundleError):
                tool.build(self.root, self.report_path, self.destination)
            self.assertFalse(self.destination.exists())

    def test_ancillary_public_metadata_must_match_its_separate_review(self):
        (self.root / 'Release/RuStore/registered-products122.json').write_text('{"applicationId":123}', encoding='utf-8')
        with self.assertRaises(tool.BundleError) as failed:
            tool.build(self.root, self.report_path, self.destination)
        self.assertEqual(str(failed.exception), 'ancillary_input_does_not_match_reviewed_snapshot')
        self.assertFalse(self.destination.exists())

    def test_existing_archive_is_preserved(self):
        self.destination.write_bytes(b'existing operator archive')
        with self.assertRaises(tool.BundleError):
            tool.build(self.root, self.report_path, self.destination)
        self.assertEqual(self.destination.read_bytes(), b'existing operator archive')

    def test_extra_env_database_log_and_virtualenv_never_enter_archive(self):
        for name in ('.env', 'authority.sqlite3', 'private.log'):
            (self.root / 'Backend' / name).write_bytes(b'synthetic never-selected payload')
        env = self.root / 'Backend/.venv'
        env.mkdir()
        (env / 'do-not-copy.py').write_bytes(b'not a deployment source')
        tool.build(self.root, self.report_path, self.destination)
        with zipfile.ZipFile(self.destination) as archive:
            names = archive.namelist()
            self.assertFalse(any('/.env' in name or '/.venv' in name or name.endswith(('.sqlite3', '.log')) for name in names))

    def test_service_examples_use_separate_source_readonly_environment_and_manual_start(self):
        tool.build(self.root, self.report_path, self.destination)
        with zipfile.ZipFile(self.destination) as archive:
            for name in ('HOTRProduction122', 'HOTRReconciliation122'):
                root = ET.fromstring(archive.read('Services/' + name + '.xml.example'))
                self.assertEqual(root.findtext('workingdirectory'), tool.BACKEND_ROOT)
                self.assertEqual(root.findtext('executable'), tool.PYTHON)
                self.assertEqual(root.findtext('serviceaccount/user'), 'LocalService')
                self.assertEqual(root.findtext('startmode'), 'Manual')
                self.assertEqual({item.attrib['name']: item.attrib['value'] for item in root.findall('env')},
                                 {'PYTHONPATH': tool.BACKEND_ROOT, 'PYTHONNOUSERSITE': '1'})

    def test_hardlinked_source_is_rejected_without_copy(self):
        source = self.root / 'Backend/hotr_backend/production_runtime122.py'
        link = self.root / 'linked.py'
        os.link(source, link)
        with self.assertRaises(tool.BundleError):
            tool.build(self.root, self.report_path, self.destination)
        self.assertFalse(self.destination.exists())

    def test_unreviewed_config_inventory_rejected(self):
        (self.root / 'Backend/config/unknown.json').write_bytes(b'{}')
        self.report()
        with self.assertRaises(tool.BundleError):
            tool.build(self.root, self.report_path, self.destination)
        self.assertFalse(self.destination.exists())


if __name__ == '__main__':
    unittest.main()
