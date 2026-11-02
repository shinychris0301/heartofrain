"""Host parser/dispatch guards; synthetic collection is not an Android run."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest import mock
import zlib

import run_phone_regression as run
import phone_regression_proof as proof


class RegressionControls(unittest.TestCase):
    def setUp(self):
        self.historical = run.ROOT / 'Verification/Evidence/Display88/Phone/Device02/Regression/Native/Regression.json'
        self.report = json.loads(self.historical.read_text('utf-8-sig'))
        parent = run.ROOT / '.verification-cache/Review93/RegressionHostControls'
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='host_only_', dir=parent)
        self.folder = Path(self.temporary.name).resolve()
        if not self.folder.is_relative_to(parent.resolve()):
            raise RuntimeError('HostFixtureOutsideOwnedCache')
        self.addCleanup(self.temporary.cleanup)

    def test_unchanged_historical_shape_is_only_a_parser_positive_control(self):
        proof.native_scope(self.report)

    def test_check_count_is_dynamic_but_must_equal_real_passed_rows(self):
        self.report['passed'].append('Host parser additional synthetic assertion, not a native result')
        self.report['checks'] += 1
        proof.native_scope(self.report)
        self.report['checks'] += 1
        with self.assertRaisesRegex(RuntimeError, 'Regression93NativeCoverageNotPassed'):
            proof.native_scope(self.report)

    def test_failed_or_incomplete_scope_cannot_pass(self):
        for field, value in (('status', 'FAIL_NATIVE_REGRESSION'), ('failures', ['host fixture failure']),
                             ('boards', 49), ('actions', 407), ('clips', 353), ('platform', 'WindowsEditor')):
            data = copy.deepcopy(self.report)
            data[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'Regression93NativeCoverageNotPassed'):
                proof.native_scope(data)

    def test_missing_board_or_tool_check_cannot_hide_behind_counters(self):
        for text in ('L50 accepts natural move', 'L27 tool 2 preserves moves'):
            data = copy.deepcopy(self.report)
            data['passed'].remove(text)
            data['checks'] -= 1
            with self.subTest(check=text), self.assertRaisesRegex(RuntimeError, 'Regression93Board(NaturalMoveMissing|ToolCoverageMissing)'):
                proof.native_scope(data)

    def test_declared_frame_names_are_unique_and_cannot_escape(self):
        for frames in ([], ['../secret.png'], ['/outside.png'], ['A.png', 'A.png'], ['A.png;id']):
            with self.subTest(frames=frames), self.assertRaisesRegex(RuntimeError, 'Regression93DeclaredFramesInvalid'):
                run.frame_names({'frames': frames})

    def test_existing_probe_or_active_owner_prevents_any_dispatch(self):
        reader = mock.Mock(spec=run.phone.Phone)
        reader.pending_markers.return_value = ['existing']
        with self.assertRaisesRegex(RuntimeError, 'PendingDevelopmentProbeRequestPreserved'):
            run.start_regression(reader, self.folder)
        reader.adb.assert_not_called()
        reader.require_idle.side_effect = RuntimeError('PreserveActiveAttemptNoStopInstallOrFixture')
        with self.assertRaisesRegex(RuntimeError, 'PreserveActiveAttemptNoStopInstallOrFixture'):
            run.start_regression(reader, self.folder)
        reader.adb.assert_not_called()

    def test_import_and_syntax_do_not_execute_any_process(self):
        with mock.patch.object(subprocess, 'run', side_effect=AssertionError('Host import cannot execute processes')):
            spec = importlib.util.spec_from_file_location('hotr93_regression_import_control', Path(run.__file__))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

    def test_fresh_time_requires_timezone(self):
        with self.assertRaisesRegex(RuntimeError, 'Regression93TimezoneRequired'):
            proof.when('2026-10-26T00:00:00')

    @staticmethod
    def png():
        def chunk(kind, body):
            return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
        raw = (b'\0' + b'\x44\x55\x66\xff' * 720) * 1600
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 720, 1600, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')

    def test_collection_hashes_all_declared_but_downloads_only_four_selected(self):
        names = [choices[0] for _, choices in run.SELECTED] + ['Unretained_A.png', 'Unretained_B.png']
        report = {'utc': '2026-10-26T00:00:00+00:00', 'frames': names}
        png = self.png()
        digest = hashlib.sha256(png).hexdigest()
        requests = []
        class Reader:
            base = '/host_synthetic_fixture'
            def adb(self, *args, **kwargs):
                requests.append(args)
                remote = self.base + '/Regression'
                if args == ('exec-out', 'cat', remote + '/Regression.json'):
                    return json.dumps(report).encode()
                if args == ('exec-out', 'cat', remote + '/M70_Device.json'):
                    return b'{"utc":"2026-10-26T00:00:00+00:00"}'
                if args[:2] == ('exec-out', 'cat') and args[2].endswith('.png'):
                    return png
                if args == ('shell', 'find', remote, '-type', 'f'):
                    return '\n'.join(remote + '/' + name for name in names + ['Regression.json', 'M70_Device.json', 'Old_Unlisted.png'])
                if args[:2] == ('shell', 'sha256sum'):
                    return '\n'.join(digest + '  ' + name for name in args[2:])
                if args[:4] == ('shell', 'stat', '-c', '%s:%n'):
                    return '\n'.join(str(len(png)) + ':' + name for name in args[4:])
                raise AssertionError('Unexpected synthetic reader operation: ' + str(args[:2]))
        result = run.collect(Reader(), self.folder, report, proof.when(report['utc']))
        inventory = proof.read(run.ROOT / result['captureInventory']['path'])
        self.assertEqual((inventory['capturedPngCount'], inventory['retainedPngCount']), (6, 4))
        pulled = [args[2].rsplit('/', 1)[-1] for args in requests if args[:2] == ('exec-out', 'cat') and args[2].endswith('.png')]
        self.assertEqual(set(pulled), set(names[:4]))
        self.assertEqual(len(pulled), 4)
        self.assertTrue(all(row['sha256'] == digest for row in inventory['files']))
        self.assertFalse((self.folder / 'Native/Old_Unlisted.png').exists())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RegressionControls))
    print(stream.getvalue(), end='')
    record = {'schemaVersion': 1, 'checkpoint': 93, 'utc': datetime.now(timezone.utc).isoformat(),
        'status': 'PASS_HOST_REGRESSION93_CONTROLS' if result.wasSuccessful() else 'FAIL_HOST_REGRESSION93_CONTROLS',
        'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'scope': 'Pure host parser/dispatch guards, historical report shape and synthetic PNG metadata/retention tests. No ADB, installation, app launch, Unity, Android, backend or provider execution.',
        'tools': [run.phone.public_binding(Path(__file__)), run.phone.public_binding(Path(run.__file__)), run.phone.public_binding(Path(proof.__file__))]}
    if args.report:
        path = args.report.resolve()
        if not path.is_relative_to(run.OUT.resolve()) or path.exists():
            raise RuntimeError('FreshReview93HostReportRequired')
        run.phone.write(path, record)
    print(json.dumps({key: value for key, value in record.items() if key != 'tools'}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
