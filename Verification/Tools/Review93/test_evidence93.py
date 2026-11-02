"""Host-only negative controls for review93 evidence; no native/device claims."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('collect_review93', Path(__file__).with_name('collect_review93.py'))
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
ACCOUNT = ROOT / 'Verification/Evidence/Review86/NativeRuns/a72a5dafcbff4dbd90de7d1881c8c3d6/Native/AccountContracts.json'
OPERATIONS = ROOT / 'Verification/Evidence/Review93/Backend/Operations/Set02/Operational_Rehearsal.json'


class CollectorControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.account = review.read(ACCOUNT)
        cls.operations = review.read(OPERATIONS)
        cls.backend = {'sourceSHA256': review.backend_sources()}

    def test_01_exact_historical_account_shape_is_only_a_host_classification_fixture(self):
        review.exact_clipboard_failure('Account', copy.deepcopy(self.account))

    def account_rejects(self, key, value):
        report = copy.deepcopy(self.account)
        report[key] = value
        with self.assertRaises(RuntimeError):
            review.exact_clipboard_failure('Account', report)

    def test_02_unknown_suite_failure_is_never_classified(self):
        with self.assertRaises(RuntimeError):
            review.exact_clipboard_failure('Checkout', self.account)

    def test_03_different_error_cannot_be_waived_as_clipboard(self):
        self.account_rejects('errors', ['unrelated failure'])

    def test_04_extra_error_cannot_be_hidden(self):
        self.account_rejects('errors', self.account['errors'] + ['unrelated failure'])

    def test_05_failed_count_cannot_be_inflated(self):
        self.account_rejects('checks', 45)

    def test_06_nonempty_readback_is_not_exact_observed_failure(self):
        self.account_rejects('clipboardReadbackLength', 43)

    def test_07_successful_readback_cannot_keep_failed_classification(self):
        self.account_rejects('clipboardReadbackMatched', True)

    def test_08_missing_copy_is_not_environment_acceptance(self):
        self.account_rejects('copyCalls', 0)

    def test_09_duplicate_copy_is_not_environment_acceptance(self):
        self.account_rejects('copyCalls', 2)

    def test_10_missing_prior_case_blocks_classification(self):
        self.account_rejects('passed', self.account['passed'][:-1])

    def test_11_host_fixture_cannot_be_relabelled_android(self):
        self.account_rejects('androidKeystore', True)

    def test_12_extra_error_field_is_not_ignored(self):
        self.account_rejects('error', 'unexpected')

    def test_13_actual_operations_proof_passes_in_its_host_scope(self):
        result = review.operations_proof(OPERATIONS, self.backend)
        self.assertEqual(result['checks'], 199)
        self.assertEqual(result['requests'], 162)

    def operations_rejects(self, change):
        report = copy.deepcopy(self.operations)
        change(report)
        with patch.object(review, 'read', return_value=report):
            with self.assertRaises(RuntimeError):
                review.operations_proof(OPERATIONS, self.backend)

    def test_14_operations_source_drift_blocks_acceptance(self):
        self.operations_rejects(lambda r: r['sourceSHA256After'].update({'unexpected': '0' * 64}))

    def test_15_live_process_blocks_operations_acceptance(self):
        self.operations_rejects(lambda r: r['processes'][1].update(ownedProcessTerminated=False))

    def test_16_nonloopback_process_blocks_local_scope_claim(self):
        self.operations_rejects(lambda r: r['processes'][0].update(boundToLoopback=False))

    def test_17_missing_restart_blocks_operations_acceptance(self):
        self.operations_rejects(lambda r: r['processes'].pop())

    def test_18_incomplete_parallel_claim_case_blocks_acceptance(self):
        self.operations_rejects(lambda r: r['details'].update(parallelClaimRetries=0))

    def test_19_failed_restore_blocks_acceptance(self):
        self.operations_rejects(lambda r: r['details']['restore'].update(status='failed'))

    def test_20_overwriting_restore_is_not_new_path_proof(self):
        self.operations_rejects(lambda r: r['details']['restore'].update(inPlaceRestore=True))

    def test_21_live_payment_cannot_be_claimed_by_loopback_report(self):
        self.operations_rejects(lambda r: r['details'].update(realPayments=True))

    def test_22_check_count_cannot_exceed_actual_passing_labels(self):
        self.operations_rejects(lambda r: r.update(checks=r['checks'] + 1))

    def test_23_bound_file_digest_change_is_rejected(self):
        item = review.binding(OPERATIONS)
        item['sha256'] = '0' * 64
        with self.assertRaises(RuntimeError):
            review.verify_binding(item, True)

    def test_24_historical_report_cannot_be_a_current93_input(self):
        with self.assertRaises(RuntimeError):
            review.bound(ACCOUNT, True)

    def test_25_actual_labelled_general_checks_are_counted_without_rewriting_report(self):
        path = ROOT / 'Verification/Evidence/Review93/Native/Set01/General/Native_Checks.json'
        report = review.read(path)
        before = copy.deepcopy(report)
        self.assertEqual(review.native_check_count(report, True), 534)
        self.assertEqual(report, before)

    def labelled(self):
        return {'checks': [{'name': 'positive control', 'status': 'PASS', 'error': ''}], 'passed': 1, 'failed': 0}

    def test_26_labelled_declared_count_mismatch_is_rejected(self):
        report = self.labelled()
        report['passed'] = 2
        with self.assertRaises(RuntimeError):
            review.native_check_count(report, True)

    def test_27_labelled_failed_row_cannot_enter_passing_total(self):
        report = self.labelled()
        report.update(passed=0, failed=1)
        report['checks'][0]['status'] = 'FAIL'
        with self.assertRaises(RuntimeError):
            review.native_check_count(report, True)

    def test_28_labelled_pass_with_error_is_rejected(self):
        report = self.labelled()
        report['checks'][0]['error'] = 'unexpected'
        with self.assertRaises(RuntimeError):
            review.native_check_count(report, True)

    def test_29_labelled_unknown_status_is_rejected(self):
        report = self.labelled()
        report['checks'][0]['status'] = 'SKIPPED'
        with self.assertRaises(RuntimeError):
            review.native_check_count(report, True)

    def test_30_boolean_is_not_a_native_check_count(self):
        with self.assertRaises(RuntimeError):
            review.native_check_count({'checks': True}, True)


def main():
    global OPERATIONS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--operations', type=Path, default=OPERATIONS)
    args = parser.parse_args()
    OPERATIONS = args.operations.resolve()
    out = args.out.resolve()
    if not out.is_relative_to((ROOT / 'Verification/Evidence/Review93').resolve()) or out.exists():
        parser.error('Fresh Review93 host-control report required')
    out.parent.mkdir(parents=True, exist_ok=True)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(CollectorControls))
    report = {'schemaVersion': 1, 'status': 'PASS_REVIEW93_HOST_EVIDENCE_CONTROLS' if result.wasSuccessful() else 'FAIL_REVIEW93_HOST_EVIDENCE_CONTROLS',
              'tests': result.testsRun, 'failures': [test.id() for test, _ in result.failures],
              'errors': [test.id() for test, _ in result.errors], 'skipped': [test.id() for test, _ in result.skipped],
              'testSHA256': review.sha(Path(__file__)), 'collectorSHA256': review.sha(Path(__file__).with_name('collect_review93.py')),
              'fixtureInputs': [review.binding(ACCOUNT), review.binding(OPERATIONS)],
              'scope': 'Host-only classification/hash/source/cleanup/restore negative controls. The historical Account JSON is data for a strict-pattern control, not a current93 native run or acceptance waiver. No Unity, device, provider or service is executed.'}
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'tests': report['tests'], 'failures': report['failures'], 'errors': report['errors']}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
