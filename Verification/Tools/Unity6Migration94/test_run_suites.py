"""Host-only aggregation/selection counterexamples; never starts Unity."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('migration94_suite_runner_under_test', Path(__file__).with_name('run_suites.py'))
RUN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN)
PLAN = json.loads(Path(__file__).with_name('suites94.json').read_text('utf-8-sig'))


class SuiteHostTests(unittest.TestCase):
    def exclusive_writer(self):
        def write(path, value):
            with Path(path).open('x', encoding='utf-8') as stream:
                json.dump(value, stream)
        return SimpleNamespace(write=write)

    def test_two_case_io_lifecycle_uses_fresh_progress_then_one_final(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_suite_exclusive_host_') as directory:
            output = Path(directory)
            api = self.exclusive_writer()
            record = {'status': 'RUNNING_HOST_IO_FIXTURE', 'runs': []}
            api.write(output / 'Authorization.json', record)
            for name in ('General', 'Display'):
                record['runs'].append({'name': name, 'acceptedNativePass': True})
                path = RUN.write_progress(api, output, record)
                self.assertEqual(len(json.loads(path.read_text())['runs']), len(record['runs']))
                self.assertFalse((output / 'SuiteSet.json').exists())
            record['status'] = 'HOST_IO_FIXTURE_FINISHED_NOT_NATIVE_EVIDENCE'
            final = RUN.write_final(api, output, record)
            self.assertEqual(json.loads(final.read_text())['status'], record['status'])
            self.assertEqual(len(list((output / 'Progress').glob('*.json'))), 2)
            self.assertEqual(json.loads((output / 'Authorization.json').read_text())['runs'], [])

    def test_exclusive_final_and_progress_receipts_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_suite_receipt_host_') as directory:
            output = Path(directory)
            api = self.exclusive_writer()
            record = {'status': 'HOST_IO_FIXTURE_ONLY', 'runs': [{'name': 'General'}]}
            progress = RUN.write_progress(api, output, record)
            final = RUN.write_final(api, output, record)
            progress_bytes, final_bytes = progress.read_bytes(), final.read_bytes()
            record['status'] = 'UNAPPROVED_SECOND_WRITE'
            with self.assertRaises(FileExistsError):
                RUN.write_progress(api, output, record)
            with self.assertRaises(FileExistsError):
                RUN.write_final(api, output, record)
            self.assertEqual(progress.read_bytes(), progress_bytes)
            self.assertEqual(final.read_bytes(), final_bytes)

    def test_default_selection_is_nine_required_and_no_account(self):
        selected = RUN.select_cases(PLAN)
        self.assertEqual(len(selected), 9)
        self.assertFalse(any(row['diagnosticOnly'] for row in selected))

    def test_explicit_focus_rejects_unknown_or_duplicate_case(self):
        for names in ('General,General', 'General,Unknown', '../General', 'General, Display'):
            with self.assertRaises(ValueError):
                RUN.select_cases(PLAN, names)
        self.assertEqual([row['name'] for row in RUN.select_cases(PLAN, 'Progress,Display')], ['Display', 'Progress'])

    def test_account_remains_diagnostic_and_is_not_duplicated(self):
        selected = RUN.select_cases(PLAN, 'Account,General', True)
        self.assertEqual(len(selected), 2)
        self.assertTrue(next(row for row in selected if row['name'] == 'Account')['diagnosticOnly'])

    def test_general_actual_array_count_and_counters_are_verified(self):
        case = RUN.select_cases(PLAN, 'General')[0]
        report = {'checks': [{'name': 'one', 'status': 'PASS'}, {'name': 'two', 'status': 'FAIL'}], 'passed': 1, 'failed': 1}
        counted = RUN.count_native(report, case)
        self.assertEqual(counted['attemptedChecks'], 2)
        self.assertEqual(counted['explicitPassedChecks'], 1)
        self.assertEqual(counted['explicitFailedChecks'], 1)
        report['passed'] = 2
        with self.assertRaisesRegex(ValueError, 'CountersMismatch'):
            RUN.count_native(report, case)

    def test_array_and_numeric_schema_cannot_fabricate_counts(self):
        general = RUN.select_cases(PLAN, 'General')[0]
        numeric = RUN.select_cases(PLAN, 'ProfileTransactions')[0]
        for bad in (0, [], True, [{'status': 'UNKNOWN'}]):
            with self.assertRaises(ValueError):
                RUN.count_native({'checks': bad}, general)
        for bad in (True, 0, -3, 2.4, '44', []):
            with self.assertRaises(ValueError):
                RUN.count_native({'checks': bad}, numeric)
        self.assertFalse(RUN.count_native({'checks': 44}, numeric)['passedCountInferred'])

    def test_versionless_legacy_report_cannot_claim_a_fabricated_unity_field(self):
        case = RUN.select_cases(PLAN, 'ProfileTransactions')[0]
        report = {'status': case['expected'], 'checks': 13, 'failures': []}
        self.assertTrue(RUN.native_passed(report, case))
        report['unity'] = RUN.VERSION
        self.assertFalse(RUN.native_passed(report, case))

    def test_retained_account_clipboard_failure_never_becomes_pass(self):
        account = dict(RUN.ACCOUNT_DIAGNOSTIC)
        report = {'status': 'FAIL_NATIVE_SERVER_ACCOUNT83_CONTRACTS', 'unity': RUN.VERSION,
                  'errors': [RUN.ACCOUNT_CLIPBOARD_ERROR], 'clipboardReadbackMatched': False, 'checks': 44}
        self.assertEqual(RUN.account_classification(report, account), 'RETAINED_FAIL_ACCOUNT_CLIPBOARD_ACCEPTANCE_UNRESOLVED')
        self.assertFalse(RUN.native_passed(report, account))
        required = RUN.select_cases(PLAN, 'General')[0]
        rows = [dict(required, acceptedNativePass=True, attemptedChecks=534),
                dict(account, acceptedNativePass=False, attemptedChecks=44)]
        summary = RUN.summarize(rows, [required, account], True, True)
        self.assertEqual(summary['status'], 'COMPLETED_FOCUSED_NATIVE_SUITES94_WITH_RETAINED_DIAGNOSTIC_FAILURES')
        self.assertEqual(summary['requiredPassingChecks'], 534)
        self.assertEqual(summary['diagnosticAttemptedChecks'], 44)
        report['errors'].append('Unexpected second failure')
        self.assertEqual(RUN.account_classification(report, account), 'RETAINED_UNCLASSIFIED_ACCOUNT_DIAGNOSTIC_FAILURE')

    def test_real_native_failure_keeps_attempted_checks_out_of_passing_total(self):
        selected = RUN.select_cases(PLAN, 'General,Display')
        rows = [dict(selected[0], acceptedNativePass=True, attemptedChecks=534),
                dict(selected[1], acceptedNativePass=False, attemptedChecks=700)]
        summary = RUN.summarize(rows, selected, True, True)
        self.assertEqual(summary['status'], 'FAIL_ISOLATED_FOCUSED_NATIVE_SUITES94')
        self.assertEqual(summary['requiredPassingChecks'], 534)
        self.assertEqual(summary['requiredAttemptedChecksInFailedSuites'], 700)

    def test_source_or_process_preservation_failure_overrides_all_passing_suites(self):
        selected = RUN.select_cases(PLAN, 'General')
        rows = [dict(selected[0], acceptedNativePass=True, attemptedChecks=534)]
        self.assertEqual(RUN.summarize(rows, selected, False, True)['status'],
                         'FAIL_ISOLATED_SUITESET94_SOURCE_OR_PROCESS_PRESERVATION')
        self.assertEqual(RUN.summarize(rows, selected, True, False)['status'], 'INCOMPLETE_ISOLATED_SUITESET94')

    def test_account_only_cannot_look_like_full_focused_suites_pass(self):
        selected = RUN.select_cases(PLAN, 'Account')
        rows = [dict(selected[0], acceptedNativePass=True, attemptedChecks=55)]
        summary = RUN.summarize(rows, selected, True, True)
        self.assertEqual(summary['status'], 'COMPLETED_DIAGNOSTIC_ONLY94')
        self.assertFalse(summary['requiredSuitesPassed'])
        self.assertEqual(summary['requiredPassingChecks'], 0)

    def test_source_delta_retains_added_removed_and_changed_paths(self):
        before = {'files': {'old': {'sha256': 'a'}, 'edit': {'sha256': 'b'}, 'same': {'sha256': 'c'}}}
        after = {'files': {'new': {'sha256': 'd'}, 'edit': {'sha256': 'e'}, 'same': {'sha256': 'c'}}}
        delta = RUN.source_delta(before, after)
        self.assertEqual(delta, {'added': ['new'], 'removed': ['old'], 'changed': ['edit']})
        self.assertFalse(RUN.unchanged(delta))


if __name__ == '__main__':
    unittest.main(verbosity=2)
