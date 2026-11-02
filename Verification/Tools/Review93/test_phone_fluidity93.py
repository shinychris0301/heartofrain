"""Host-only diagnostic parser and quiet-window guards; no Android execution."""
import argparse
import copy
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

import run_phone_fluidity as fluidity


class FluidityControls(unittest.TestCase):
    def setUp(self):
        self.path = fluidity.ROOT / 'Verification/Evidence/Physical87/20261026_e71bc9d09515/Probes/Fluidity/Report.json'
        self.report = json.loads(self.path.read_text('utf-8-sig'))

    def test_historical_report_is_only_a_parser_positive_control(self):
        result = fluidity.observe(self.report)
        self.assertEqual(result['status'], 'RECORDED_DIAGNOSTICS_NOT_A_SMOOTHNESS_PASS')
        self.assertEqual(result['frameSampleCount'], len(self.report['frameSamples']))

    def test_all_slow_samples_are_retained_without_approving_performance(self):
        expected = [row for row in self.report['frameSamples'] if row['intervalMs'] > 33.34]
        result = fluidity.observe(self.report)
        self.assertEqual(len(result['allFramesOver33ms']), len(expected))
        self.assertEqual([row['frame'] for row in result['allFramesOver33ms']], [row['frame'] for row in expected])
        self.assertEqual(result['worstRecordedIntervalMs'], max(row['intervalMs'] for row in self.report['frameSamples']))
        self.assertEqual(result['worstRecordedCommandMs'], max(row['commandMs'] for row in self.report['phases']))
        self.assertFalse(result['status'].startswith('PASS'))

    def test_wrong_variant_errors_and_incomplete_native_scope_are_rejected(self):
        for field, value in (('variant', 'baseline'), ('errors', ['host fixture error']), ('platform', 'WindowsEditor'), ('phases', []), ('frameSamples', [])):
            value_report = copy.deepcopy(self.report)
            value_report[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                fluidity.observe(value_report)

    def test_phase_identity_and_nonfinite_samples_are_rejected(self):
        changed = copy.deepcopy(self.report)
        changed['phases'][0]['name'] = 'different'
        with self.assertRaisesRegex(RuntimeError, 'Fluidity93CandidatePhasesRequired'):
            fluidity.observe(changed)
        for field, value in (('intervalMs', float('nan')), ('renderMs', -1), ('phase', 8)):
            changed = copy.deepcopy(self.report)
            changed['frameSamples'][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'Fluidity93FiniteFrameMeasurementsRequired'):
                fluidity.observe(changed)

    def test_quiet_window_uses_only_local_time_and_no_subprocess(self):
        now = [0.0]
        def sleep(seconds):
            self.assertGreater(seconds, 0)
            self.assertLessEqual(seconds, 10)
            now[0] += seconds
        with mock.patch.object(fluidity.time, 'monotonic', side_effect=lambda: now[0]), mock.patch.object(fluidity.time, 'sleep', side_effect=sleep), mock.patch.object(subprocess, 'run', side_effect=AssertionError('No ADB/process in quiet window')):
            fluidity.quiet_wait(25)
        self.assertEqual(now[0], 25)

    def test_pending_probe_or_active_owner_prevents_any_device_dispatch(self):
        reader = mock.Mock(spec=fluidity.phone.Phone)
        reader.pending_markers.return_value = ['existing']
        with self.assertRaisesRegex(RuntimeError, 'PendingDevelopmentProbeRequestPreserved'):
            fluidity.start(reader, Path('unused'))
        reader.adb.assert_not_called()
        reader.require_idle.side_effect = RuntimeError('PreserveActiveAttemptNoStopInstallOrFixture')
        with self.assertRaisesRegex(RuntimeError, 'PreserveActiveAttemptNoStopInstallOrFixture'):
            fluidity.start(reader, Path('unused'))
        reader.adb.assert_not_called()

    def test_helper_import_executes_no_process_or_device_action(self):
        with mock.patch.object(subprocess, 'run', side_effect=AssertionError('Import cannot dispatch ADB')):
            spec = importlib.util.spec_from_file_location('hotr93_fluidity_host_import', Path(fluidity.__file__))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.parser()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--report', type=Path)
    args = cli.parse_args()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FluidityControls))
    print(stream.getvalue(), end='')
    record = {'schemaVersion': 1, 'checkpoint': 93, 'utc': datetime.now(timezone.utc).isoformat(),
        'status': 'PASS_HOST_FLUIDITY93_CONTROLS' if result.wasSuccessful() else 'FAIL_HOST_FLUIDITY93_CONTROLS',
        'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'scope': 'Pure host diagnostic parser, complete slow-frame retention, no-performance-PASS, import/dispatch and simulated local quiet-window controls. Historical physical report supplies parser input only. No ADB, app launch, Unity, Android or new performance execution.',
        'tools': [fluidity.phone.public_binding(Path(__file__)), fluidity.phone.public_binding(Path(fluidity.__file__)), fluidity.phone.public_binding(fluidity.PARSER)]}
    if args.report:
        path = args.report.resolve()
        if path.exists() or not path.is_relative_to(fluidity.OUT.resolve()):
            raise RuntimeError('FreshReview93HostReportRequired')
        fluidity.phone.write(path, record)
    print(json.dumps({key: value for key, value in record.items() if key != 'tools'}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
