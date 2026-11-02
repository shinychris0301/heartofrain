"""Synthetic host guards; no actual evidence, Unity, SDK, or device operations."""
import importlib.util
import json
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('sanitize_logs94_guard', Path(__file__).with_name('sanitize_logs94.py'))
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


class Redaction94Guards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = self.root / api.EVIDENCE_REL
        self.evidence.mkdir(parents=True)
        self.out = self.evidence / 'Privacy/Set01'

    def source(self, relative, raw):
        path = self.evidence / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def publish(self):
        result = api.publish(self.out, workspace=self.root, private_id='a' * 32)
        for entry in result['files']:
            self.addCleanup((self.root / entry['privateCopy']).chmod, stat.S_IWRITE)
        return result

    def test_only_values_change_and_crlf_bom_unrelated_status_are_exact(self):
        raw = b'\xef\xbb\xbfEngine header\r\n  Session Id: fixture-session\r\n[Licensing] Access token is unavailable\r\nordinary state: ready\r\n  Machine Id: fixture-machine\r\n'
        public, changes = api.redact(raw)
        self.assertEqual(public, b'\xef\xbb\xbfEngine header\r\n  Session Id: <redacted:session_id>\r\n[Licensing] Access token is unavailable\r\nordinary state: ready\r\n  Machine Id: <redacted:machine_id>\r\n')
        self.assertEqual(changes, [{'line': 2, 'category': 'session_id'}, {'line': 5, 'category': 'machine_id'}])

    def test_both_correlation_headers_and_baseline_serial_are_redacted(self):
        raw = b'Correlation Id: fixture-one\nExternal correlation Id: fixture-two\n[Licensing] Serial number: fixture-license\n[Licensing] Serial number assigned to: fixture-2022-license\n'
        public, changes = api.redact(raw)
        self.assertNotIn(b'fixture-', public)
        self.assertEqual([x['category'] for x in changes], ['correlation_id', 'correlation_id', 'license_serial', 'license_serial'])

    def test_concrete_credential_and_adb_serial_values_are_removed(self):
        raw = b'Access token: fixture-value\nadb.exe -s fixture-device shell echo ready\n'
        public, changes = api.redact(raw)
        self.assertEqual(public, b'Access token: <redacted:credential_value>\nadb.exe -s <redacted:adb_serial> shell echo ready\n')
        self.assertEqual(len(changes), 2)

    def test_no_silent_lossy_decode_or_unsupported_key_material(self):
        with self.assertRaises(UnicodeDecodeError):
            api.redact(b'\xff\x00')
        with self.assertRaisesRegex(RuntimeError, 'UnsupportedSensitiveValue'):
            api.redact(b'-----BEGIN PRIVATE KEY-----\nfixture\n')

    def test_derivative_is_idempotent_and_no_new_redactions_occur(self):
        first, changes = api.redact(b'Machine Id: fixture-id\n')
        second, again = api.redact(first)
        self.assertEqual(first, second)
        self.assertTrue(changes)
        self.assertEqual(again, [])

    def test_publishes_private_exact_copies_and_bound_derivatives_without_touching_raw(self):
        first = self.source('Native/Case/Unity.log', b'Machine Id: fixture-machine\nPASS native check\n')
        second = self.source('Baseline2022/Console.LOG', b'normal unchanged console\r\n')
        before = {p: p.read_bytes() for p in (first, second)}
        result = self.publish()
        self.assertEqual(result['rawLogCount'], 2)
        self.assertEqual(result['redactedLogCount'], 1)
        self.assertEqual(json.loads((self.out / 'Receipt.json').read_text()), result)
        for entry in result['files']:
            raw = self.root / entry['rawSource']
            private = self.root / entry['privateCopy']
            public = self.root / entry['publicDerivative']
            self.assertEqual(raw.read_bytes(), before[raw])
            self.assertEqual(private.read_bytes(), before[raw])
            self.assertEqual(api.sha(before[raw]), entry['rawSHA256'])
            self.assertEqual(api.sha(public.read_bytes()), entry['publicSHA256'])
            self.assertNotEqual(private, raw)
            self.assertTrue(public.name.endswith('.sanitized.log'))

    def test_fresh_public_and_private_outputs_cannot_be_overwritten(self):
        self.source('Unity.log', b'normal\n')
        self.publish()
        with self.assertRaisesRegex(RuntimeError, 'FreshPublicOutputRequired'):
            self.publish()
        self.out = self.evidence / 'Privacy/Set02'
        with self.assertRaisesRegex(RuntimeError, 'FreshPrivateOutputRequired'):
            self.publish()

    def test_outside_public_scope_and_private_id_traversal_are_refused(self):
        self.source('Unity.log', b'normal\n')
        with self.assertRaisesRegex(RuntimeError, 'PathOutside94Scope'):
            api.publish(self.root / 'Unity/Privacy/Set01', workspace=self.root)
        with self.assertRaisesRegex(RuntimeError, 'InvalidPrivateSetIdentifier'):
            api.publish(self.out, workspace=self.root, private_id='../escape')

    def test_unknown_sensitive_shape_refuses_all_public_output(self):
        self.source('Unity.log', b'Bearer fixture-secret-material\n')
        with self.assertRaisesRegex(RuntimeError, 'UnsupportedSensitiveValue'):
            self.publish()
        self.assertFalse(self.out.exists())
        self.assertFalse((self.root / api.PRIVATE_REL).exists())

    def test_derivatives_are_never_rescanned_as_raw_logs(self):
        self.source('Unity.log', b'normal\n')
        self.source('Privacy/Old/Public/Unity.sanitized.log', b'public derivative\n')
        self.assertEqual(len(api.source_logs(self.evidence)), 1)

    @unittest.skipUnless(shutil.which('git'), 'Git required to prove proposed ignore semantics')
    def test_proposed_ignore_covers_actual_casing_baselines_not_derivatives_or_93(self):
        subprocess.run(['git', 'init', '--quiet', str(self.root)], check=True, capture_output=True)
        proposed = Path(__file__).with_name('RawLogs.gitignore.proposed.txt').read_bytes()
        (self.root / '.gitignore').write_bytes(proposed)
        ignored = [str(api.EVIDENCE_REL / x).replace('\\', '/') for x in ('Native/Suite/Unity.log', 'Serialization/Baseline2022/UNITY.LOG', 'Case/cOnSoLe.LoG')]
        included = [str(api.EVIDENCE_REL / x).replace('\\', '/') for x in ('Privacy/Set01/Public/Unity.sanitized.log', 'Privacy/Set01/Receipt.json')]
        included += ['Verification/Evidence/Review93/Native/Unity.log']
        # Argument paths avoid Windows text-pipe CRLF changing --stdin names.
        result = subprocess.run(['git', '-C', str(self.root), 'check-ignore', '--no-index', '--'] + ignored + included, text=True, check=False, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(set(result.stdout.splitlines()), set(ignored))


if __name__ == '__main__':
    unittest.main()
