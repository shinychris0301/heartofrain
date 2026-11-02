"""Import-safe host controls for the non-batch Account diagnostic; no native run."""
import argparse
import copy
import ctypes
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import run_account_nonbatch as runner


class NonBatchAccountControls(unittest.TestCase):
    def setUp(self):
        base = runner.ROOT / '.verification-cache/Review93/NonBatchHostControls'
        base.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='Case_', dir=base)
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'AccountContracts.json'
        self.began = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.native = {'status': runner.EXPECTED, 'utc': datetime.now(timezone.utc).isoformat(),
            'unity': '2022.3.62f3', 'checks': 50, 'cases': 8, 'passed': ['HostFixtureCase' + str(i) for i in range(8)],
            'errors': [], 'copyCalls': 1, 'copyScreen': 'backup',
            'clipboardReadbackLength': 43, 'clipboardReadbackMatched': True}

    def write(self, value=None):
        self.path.write_text(json.dumps(self.native if value is None else value), encoding='utf-8')

    def test_exact_unchanged_entry_has_no_batch_headless_or_quit_arguments(self):
        values = runner.command(Path('PinnedEditor.exe'), Path('Project'), Path('Unity.log'))
        self.assertEqual(values, ['PinnedEditor.exe', '-projectPath', 'Project', '-executeMethod', runner.ENTRY, '-logFile', 'Unity.log'])
        self.assertFalse({'-batchmode', '-nographics', '-quit'}.intersection(value.lower() for value in values))

    def test_host_import_dispatches_no_process_clipboard_or_win32_action(self):
        with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('Host import must not start processes')), \
             mock.patch.object(subprocess, 'run', side_effect=AssertionError('Host import must not run processes')), \
             mock.patch.object(ctypes, 'WinDLL', side_effect=AssertionError('Host import must not access Win32')):
            spec = importlib.util.spec_from_file_location('hotr93_nonbatch_import_control', Path(runner.__file__))
            imported = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(imported)
            self.assertEqual(imported.ENTRY, runner.ENTRY)

    def test_fresh_completed_redacted_synthetic_report_is_read_without_clipboard_api(self):
        self.write()
        with mock.patch.object(ctypes, 'WinDLL', side_effect=AssertionError('Report read cannot access clipboard')):
            result = runner.read_native(self.path, self.began)
        self.assertEqual(result, self.native)
        self.assertTrue(runner.passed(result))

    def test_stale_and_unzoned_native_completion_are_rejected(self):
        for stamp in ((self.began - timedelta(seconds=1)).isoformat(), datetime.now().isoformat()):
            changed = dict(self.native, utc=stamp)
            self.write(changed)
            with self.subTest(stamp=stamp), self.assertRaisesRegex(ValueError, 'FreshTimezoneNativeReportRequired'):
                runner.read_native(self.path, self.began)

    def test_missing_incomplete_and_foreign_native_results_are_not_completion(self):
        self.assertIsNone(runner.read_native(self.path, self.began))
        self.write(dict(self.native, status='RUNNING'))
        self.assertIsNone(runner.read_native(self.path, self.began))
        self.write(dict(self.native, status='PASS_OTHER_SUITE'))
        self.assertIsNone(runner.read_native(self.path, self.began))
        self.path.write_text('{"status":', encoding='utf-8')
        with self.assertRaises(json.JSONDecodeError):
            runner.read_native(self.path, self.began)

    def test_duplicate_nonfinite_or_wrong_unity_reports_are_rejected(self):
        self.path.write_text('{"status": "RUNNING", "status": "RUNNING"}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'DuplicateNativeReportKey'):
            runner.read_native(self.path, self.began)
        self.path.write_text('{"status": NaN}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'NonfiniteNativeReport'):
            runner.read_native(self.path, self.began)
        for field, value in (('unity', 'different'), ('checks', True), ('checks', 0), ('errors', None)):
            self.write(dict(self.native, **{field: value}))
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, 'ActualContractsNativeReportRequired'):
                runner.read_native(self.path, self.began)

    def test_failed_assertions_and_empty_clipboard_readback_never_pass(self):
        for field, value in (('status', 'FAIL_NATIVE_SERVER_ACCOUNT83_CONTRACTS'), ('errors', ['Host assertion failure']),
                             ('copyCalls', 0), ('copyScreen', 'server'), ('clipboardReadbackLength', 0),
                             ('clipboardReadbackMatched', False), ('cases', 7), ('passed', [])):
            changed = copy.deepcopy(self.native)
            changed[field] = value
            with self.subTest(field=field):
                self.assertFalse(runner.passed(changed))

    def test_forced_cleanup_and_source_or_mode_drift_cannot_be_normal_acceptance(self):
        normal = runner.classify(True, False, True, True, True)
        self.assertEqual(normal, 'RECORDED_NONBATCH_ACCOUNT93_NATIVE_ASSERTIONS_PASSED')
        forced = runner.classify(True, True, False, True, True)
        self.assertEqual(forced, 'RECORDED_NONBATCH_ACCOUNT93_FORCED_CLEANUP')
        self.assertNotEqual(normal, forced)
        self.assertFalse(forced.startswith('PASS'))
        self.assertTrue(runner.classify(False, False, True, True, True).endswith('NATIVE_ASSERTIONS_FAILED'))
        self.assertEqual(runner.classify(True, False, False, True, True), 'FAIL_NONBATCH_ACCOUNT93_PROCESS_CLEANUP')
        for unchanged, zero in ((False, True), (True, False)):
            self.assertEqual(runner.classify(True, False, True, unchanged, zero), 'FAIL_NONBATCH_ACCOUNT93_SOURCE_OR_MODE')

    def test_close_does_nothing_after_exit_and_rejects_wrong_image_before_win32(self):
        process = mock.Mock(pid=12345)
        process.poll.return_value = 0
        reader = mock.Mock(side_effect=AssertionError('Exited process needs no inventory'))
        with mock.patch.object(ctypes, 'WinDLL', side_effect=AssertionError('No Win32 call expected')):
            self.assertTrue(runner.close_owned_windows(process, Path('Pinned.exe'), reader)['processAlreadyExited'])
        reader.assert_not_called()
        process.poll.return_value = None
        reader = mock.Mock(return_value=(str(Path('Other.exe').resolve()), []))
        with mock.patch.object(ctypes, 'WinDLL', side_effect=AssertionError('Wrong image must not reach window API')), \
             self.assertRaisesRegex(RuntimeError, 'OwnedEditorImageChangedBeforeClose'):
            runner.close_owned_windows(process, Path('Pinned.exe'), reader)
        reader.assert_called_once_with(process.pid)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--report', type=Path)
    args = cli.parse_args()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NonBatchAccountControls))
    print(stream.getvalue(), end='')
    def binding(path):
        path = Path(path)
        return {'path': path.resolve().relative_to(runner.ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
    report = {'schemaVersion': 1, 'checkpoint': 93, 'utc': datetime.now(timezone.utc).isoformat(),
        'status': 'PASS_HOST_NONBATCH_ACCOUNT93_CONTROLS' if result.wasSuccessful() else 'FAIL_HOST_NONBATCH_ACCOUNT93_CONTROLS',
        'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'scope': 'Pure host controls using synthetic JSON, mocked subprocess and mocked Win32 guards. Confirms import safety, non-batch arguments, fresh strict report parsing, failure preservation and exact owned-process close boundary. No Unity/Editor/process/window/clipboard/ADB/network action or native acceptance was executed.',
        'tools': [binding(__file__), binding(runner.__file__)]}
    if args.report:
        target = args.report.resolve()
        if target.exists() or not target.is_relative_to((runner.ROOT / 'Verification/Evidence/Review93').resolve()):
            raise RuntimeError('FreshReview93HostReportRequired')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x', encoding='utf-8') as output:
            json.dump(report, output, indent=2)
            output.write('\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'tools'}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
