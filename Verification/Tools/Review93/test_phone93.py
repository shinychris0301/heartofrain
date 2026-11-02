"""Host-only sixth-link guard controls; no ADB, Unity or phone actions."""
import argparse
import copy
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import phone
import phone_proof


class PhoneControls(unittest.TestCase):
    def setUp(self):
        parent = phone.ROOT / '.verification-cache/Review93/PhoneHostControls'
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='host_only_', dir=parent)
        self.folder = Path(self.temporary.name).resolve()
        if not self.folder.is_relative_to(parent.resolve()):
            raise RuntimeError('HostFixtureOutsideOwnedCache')
        self.addCleanup(self.temporary.cleanup)
        self.accepted = phone.accepted92()
        self.target = dict(self.accepted['value'], authorization='OWNER_REQUESTED_REVIEW93',
                           priorTarget=self.accepted['target'], priorInstallation=self.accepted['installation'],
                           baselineInstalledSHA256=self.accepted['value']['candidateApkSHA256'],
                           candidateApkSHA256='a' * 64, upgradeChainDepth=6)
        self.before = copy.deepcopy(json.loads((self.accepted['targetPath'].parent / 'OrdinaryAfterRelaunch.json').read_text('utf-8')))
        self.after = dict(copy.deepcopy(self.before), installedSHA256='a' * 64)
        self.installation = {'status': 'PASS_SAVE_PRESERVING_REPLACEMENT', 'after': self.after}
        self.store()
        self.scope = mock.patch.object(phone, 'EVIDENCE', self.folder)
        self.scope.start()
        self.addCleanup(self.scope.stop)

    def store(self):
        for name, value in (('Target.json', self.target), ('Install_Before.json', self.before), ('Installation.json', self.installation)):
            (self.folder / name).write_text(json.dumps(value), encoding='utf-8')

    def check(self, installed=True):
        return phone.validate_upgrade_chain(self.folder / 'Target.json', require_installation=installed)

    def test_frozen_five_link_predecessor_is_complete(self):
        self.assertEqual(self.accepted['chain']['depth'], 5)
        self.assertEqual(len(self.accepted['chain']['links']), 5)
        self.assertTrue(all(row['installation'] and row['before'] for row in self.accepted['chain']['links']))

    def test_sixth_link_requires_and_accepts_exact_five_completed_predecessors(self):
        value = self.check()
        self.assertEqual((value['depth'], len(value['links']), value['candidateApkSHA256']), (6, 6, 'a' * 64))

    def test_preinstallation_may_omit_only_current_installation(self):
        (self.folder / 'Installation.json').unlink()
        self.assertEqual(self.check(False)['depth'], 6)
        with self.assertRaises(FileNotFoundError):
            self.check(True)

    def test_invented_or_earlier_predecessor_cannot_authorize_sixth_update(self):
        self.target['priorTarget'] = self.accepted['chain']['links'][0]['target']
        self.target['priorInstallation'] = self.accepted['chain']['links'][0]['installation']
        self.store()
        with self.assertRaisesRegex(RuntimeError, 'SixthLinkMustFollowAccepted92'):
            self.check()

    def test_changed_historical_receipt_hash_is_rejected(self):
        real = phone.public_binding
        altered = self.accepted['chain']['links'][0]['installation']['path']
        def changed(path):
            result = real(path)
            return dict(result, sha256='0' * 64) if result['path'] == altered else result
        with mock.patch.object(phone, 'public_binding', side_effect=changed):
            with self.assertRaisesRegex(RuntimeError, 'UpgradeChainBoundRecordChanged'):
                self.check()

    def test_wrong_owner_or_package_is_rejected(self):
        for field, value in (('serialSHA256', '0' * 64), ('model', 'unrelated-phone'), ('package', 'other.package')):
            old = self.target[field]
            self.target[field] = value
            self.store()
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'UpgradeChain(OwnerPhoneMismatch|AuthorizationInvalid)'):
                self.check()
            self.target[field] = old

    def test_declared_depth_and_candidate_paths_cannot_escape_scope(self):
        for field, value in (('upgradeChainDepth', 5), ('upgradeChainDepth', 7),
                             ('candidateApk', '../outside.apk'), ('candidateApk', 'Backend/config/commerce.json')):
            old = self.target[field]
            self.target[field] = value
            self.store()
            with self.subTest(field=field, value=value), self.assertRaisesRegex(RuntimeError, 'SixthLink(MustFollowAccepted92|CandidateOutsideOwnedBuilds)'):
                self.check()
            self.target[field] = old

    def test_active_attempt_or_changed_owner_data_cannot_pass_installation(self):
        for field, changed in (('activeAttempts', 1), ('preferences', {'changed.xml': '0' * 64}),
                               ('profileSummaries', [{'revision': 37, 'activeAttempts': 0}])):
            old = self.after[field]
            self.after[field] = changed
            self.store()
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'UpgradeChain(InstallNotPreservedAndIdle|SavedDataChanged)'):
                self.check()
            self.after[field] = old

    def test_historical_apk_paths_are_never_rehashed(self):
        real = phone.sha
        def only_records(path):
            if Path(path).suffix == '.apk':
                raise AssertionError('Historical APK must not be rehashed')
            return real(path)
        with mock.patch.object(phone, 'sha', side_effect=only_records):
            self.assertEqual(self.check()['depth'], 6)

    def test_active_attempt_and_server_configuration_prevent_device_mutation(self):
        reader = phone.Phone.__new__(phone.Phone)
        reader.base = '/unused-host-fixture'
        reader.inventory = lambda: dict(self.before, activeAttempts=1)
        reader.adb = mock.Mock(side_effect=AssertionError('No ADB permitted'))
        with self.assertRaisesRegex(RuntimeError, 'PreserveActiveAttemptNoStopInstallOrFixture'):
            reader.require_idle()
        reader.inventory = lambda: self.before
        reader.exists = lambda path: True
        with self.assertRaisesRegex(RuntimeError, 'ManagedServerConfigurationNeedsSeparateAttemptAudit'):
            reader.require_idle()
        reader.adb.assert_not_called()

    def test_changed_installed_baseline_is_rejected_before_stop_or_install(self):
        reader = phone.Phone.__new__(phone.Phone)
        reader.out, reader.target = self.folder, self.target
        reader.require_idle = lambda: dict(self.before, installedSHA256='b' * 64)
        reader.adb = mock.Mock(side_effect=AssertionError('No ADB permitted'))
        with self.assertRaisesRegex(RuntimeError, 'InstalledBaselineChangedBeforeReplacement'):
            reader.install()
        reader.adb.assert_not_called()

    def test_duplicate_or_nonfinite_phone_json_is_rejected(self):
        path = self.folder / 'invalid.json'
        path.write_text('{"status":"FAIL","status":"PASS"}', encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'DuplicatePhoneJsonKey'):
            phone._read_record(path)
        path.write_text('{"value":NaN}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'NonfinitePhoneJson'):
            phone._read_record(path)

    def test_helper_import_has_no_process_or_device_side_effect(self):
        with mock.patch.object(subprocess, 'run', side_effect=AssertionError('Import cannot execute processes')):
            spec = importlib.util.spec_from_file_location('hotr93_import_host_control', Path(phone.__file__))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

    def test_phone_proof_requires_nonempty_exact_idle_snapshot(self):
        self.assertEqual(phone_proof.snapshot(self.before, self.before['installedSHA256'])['profileSummaries'], self.before['profileSummaries'])
        for field, value in (('activeAttempts', 1), ('profiles', {}), ('preferences', {}), ('profileSummaries', [])):
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'Phone93IdleSavedSnapshotRequired'):
                phone_proof.snapshot(dict(self.before, **{field: value}), self.before['installedSHA256'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PhoneControls))
    print(stream.getvalue(), end='')
    record = {'schemaVersion': 1, 'checkpoint': 93, 'utc': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS_HOST_PHONE93_CONTROLS' if result.wasSuccessful() else 'FAIL_HOST_PHONE93_CONTROLS',
              'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'scope': 'Pure host rejection/ancestry/import controls using temporary synthetic sixth-link records and immutable five-link predecessor receipts. No ADB, device input, installation, app launch, Unity, backend or provider execution.',
              'tools': [phone.public_binding(Path(__file__)), phone.public_binding(Path(phone.__file__)),
                        phone.public_binding(Path(phone_proof.__file__)), phone.public_binding(Path(__file__).with_name('phone_review.py'))],
              'immutable92Summary': phone.public_binding(phone.PRIOR92_EVIDENCE / 'Summary.json')}
    if args.report:
        path = args.report.resolve()
        if not path.is_relative_to(phone.EVIDENCE.resolve()) or path.exists():
            raise RuntimeError('FreshReview93HostReportRequired')
        phone.write(path, record)
    print(json.dumps({key: value for key, value in record.items() if key not in ('tools',)}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
