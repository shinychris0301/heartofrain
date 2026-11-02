"""Pure host provenance rejection controls; never invoke Unity or a device."""
import argparse
import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import zlib

import collect_backdrop90 as collect
import phone
import process90


class EvidenceControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='hotr-evidence90-')
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def data(self, body):
        path = self.folder / 'report.json'
        path.write_text(body, encoding='utf-8')
        return path

    def test_duplicate_json_cannot_override_a_failure(self):
        with self.assertRaisesRegex(RuntimeError, 'DuplicateJsonKey'):
            collect.read(self.data('{"status":"FAIL","status":"PASS"}'))

    def test_nonfinite_json_is_not_an_accepted_measurement(self):
        with self.assertRaisesRegex(ValueError, 'NonfiniteJson'):
            collect.read(self.data('{"elapsed":NaN}'))

    def test_parent_path_escape_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'ParentTraversalRefused'):
            collect.bound('../outside.json')

    def test_absolute_path_escape_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'EvidencePathOutsideScope'):
            collect.bound(self.folder / 'outside.json')

    def test_published_receipt_mutation_is_rejected(self):
        path = self.data('{"status":"PASS"}')
        with mock.patch.object(collect, 'ROOT', self.folder):
            value = collect.binding(path)
            path.write_text('{"status":"FAIL"}', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'BoundArtifactChanged'):
                collect.check_binding(value)

    def test_public_secret_fields_are_rejected(self):
        for field in ('serial', 'access_token', 'recovery-code', 'privateKey'):
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'PrivateFieldInPublicEvidence'):
                collect.public_fields({'nested': [{field: 'private-value'}]})

    def test_serial_hash_is_safe_public_identity(self):
        collect.public_fields({'serialSHA256': 'a' * 64, 'tokenCount': 0})

    def test_native_incomplete_set_cannot_be_promoted(self):
        value = {'schemaVersion': 1, 'checkpoint': 90, 'status': 'PASS_NATIVE90_SET', 'runs': []}
        with mock.patch.object(collect, 'bound', return_value=self.data(json.dumps(value))):
            with self.assertRaisesRegex(RuntimeError, 'FourNativeSuitesRequired'):
                collect.native_proof('unused', {})

    def test_failed_native_set_cannot_be_promoted(self):
        value = {'schemaVersion': 1, 'checkpoint': 90, 'status': 'FAIL_NATIVE90_SET', 'runs': []}
        with mock.patch.object(collect, 'bound', return_value=self.data(json.dumps(value))):
            with self.assertRaisesRegex(RuntimeError, 'NativeListScopeInvalid'):
                collect.native_proof('unused', {})

    def test_png_truncation_and_crc_damage_are_rejected(self):
        def chunk(kind, body):
            return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
        raw = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 3, 8, 6, 0, 0, 0))
               + chunk(b'IDAT', zlib.compress((b'\0' + b'\xff\0\0\xff' * 2) * 3)) + chunk(b'IEND', b''))
        self.assertEqual(phone.validate_png(raw), (2, 3))
        for malformed in (raw[:-12], raw[:-1], raw[:-1] + bytes([raw[-1] ^ 1])):
            with self.subTest(size=len(malformed)), self.assertRaises(RuntimeError):
                phone.validate_png(malformed)

    def test_exact_broker_with_trusted_signer_is_the_only_new_exception(self):
        broker = self.folder / 'Unity/bin/unity.exe'
        signature = {'status': 'Valid', 'simpleName': 'Unity Technologies SF', 'subject': 'CN=Unity Technologies SF, O=Unity Technologies SF, C=US'}
        self.assertTrue(process90.approved_broker(broker, [str(broker), process90.BROKER_FLAG], signature, broker))
        other = self.folder / 'Editor/unity.exe'
        for image, arguments, signing in (
            (other, [str(other), process90.BROKER_FLAG], signature),
            (broker, [str(broker)], signature),
            (broker, [str(broker), process90.BROKER_FLAG, '-projectPath'], signature),
            (broker, [str(broker), '--internal-auth-broker-serve-extra'], signature),
            (broker, [str(other), process90.BROKER_FLAG], signature),
            (broker, [str(broker), process90.BROKER_FLAG], dict(signature, status='NotSigned')),
            (broker, [str(broker), process90.BROKER_FLAG], dict(signature, simpleName='Another Publisher')),
            (broker, [str(broker), process90.BROKER_FLAG], dict(signature, subject='CN=Unity Technologies SF Spoof, C=US'))):
            with self.subTest(image=image, arguments=arguments, signature=signing):
                self.assertFalse(process90.approved_broker(image, arguments, signing, broker))

    def test_unknown_editor_and_wrong_broker_arguments_still_block(self):
        broker = self.folder / 'Unity/bin/unity.exe'
        unknown = self.folder / 'Editor/unity.exe'
        def details(pid, include_command=False):
            image = {101: process90.HUB.resolve(), 102: unknown.resolve(), 103: broker.resolve()}[pid]
            return image, [str(image), process90.BROKER_FLAG, '-projectPath'] if include_command else None
        signature = {'status': 'Valid', 'simpleName': 'Unity Technologies SF', 'subject': 'CN=Unity Technologies SF, C=US'}
        with mock.patch.object(process90, 'local_app_data', return_value=self.folder), mock.patch.object(process90, 'named_unity_pids', return_value=[101, 102, 103]), mock.patch.object(process90, 'process_details', side_effect=details), mock.patch.object(process90, 'authenticode', return_value=signature):
            self.assertEqual(process90.unity_pids(), [102, 103])

    def test_exact_signed_broker_and_existing_hub_are_not_editors(self):
        broker = self.folder / 'Unity/bin/unity.exe'
        def details(pid, include_command=False):
            image = process90.HUB.resolve() if pid == 101 else broker.resolve()
            return image, [str(image), process90.BROKER_FLAG] if include_command else None
        signature = {'status': 'Valid', 'simpleName': 'Unity Technologies SF', 'subject': 'CN=Unity Technologies SF, C=US'}
        with mock.patch.object(process90, 'local_app_data', return_value=self.folder), mock.patch.object(process90, 'named_unity_pids', return_value=[101, 102]), mock.patch.object(process90, 'process_details', side_effect=details), mock.patch.object(process90, 'authenticode', return_value=signature):
            self.assertEqual(process90.unity_pids(), [])

    def test_unreadable_unity_identity_blocks_preflight(self):
        with mock.patch.object(process90, 'local_app_data', return_value=self.folder), mock.patch.object(process90, 'named_unity_pids', return_value=[101]), mock.patch.object(process90, 'process_details', side_effect=RuntimeError('UnityProcessImageUnavailable')):
            with self.assertRaisesRegex(RuntimeError, 'UnityProcessImageUnavailable'):
                process90.unity_pids()

    def test_unavailable_broker_trust_blocks_preflight(self):
        broker = self.folder / 'Unity/bin/unity.exe'
        with mock.patch.object(process90, 'local_app_data', return_value=self.folder), mock.patch.object(process90, 'named_unity_pids', return_value=[101]), mock.patch.object(process90, 'process_details', return_value=(broker.resolve(), [str(broker), process90.BROKER_FLAG])), mock.patch.object(process90, 'authenticode', side_effect=RuntimeError('UnityBrokerAuthenticodeUnavailable')):
            with self.assertRaisesRegex(RuntimeError, 'UnityBrokerAuthenticodeUnavailable'):
                process90.unity_pids()

    def test_actual_windows_argument_parser_preserves_exact_broker_flag(self):
        arguments = process90.command_arguments('"C:\\Users\\Example User\\AppData\\Local\\Unity\\bin\\unity.exe" --internal-auth-broker-serve')
        self.assertEqual(arguments, [r'C:\Users\Example User\AppData\Local\Unity\bin\unity.exe', process90.BROKER_FLAG])

    def backdrop(self):
        return {'cases': 108, 'surfaces': [{'name': name, 'passed': True} for name in collect.NATIVE_SURFACES for _ in range(6 if name in ('HomeEventsDrawer', 'HUDLoss') else 12)],
                'captures': ['fixture.png'], 'oldBandPixels': 11200, 'newBandPixels': 11200,
                'modalBandPixels': 11200, 'homeDrawerBandPixels': 11200, 'hudLossBandPixels': 11200, 'maskedControlLeaks': 0}

    def test_expanded_backdrop_scope_accepts_all_exercised_families(self):
        collect.backdrop_scope(self.backdrop())

    def test_prior_eight_family_scope_cannot_be_promoted(self):
        value = self.backdrop()
        value['surfaces'] = [row for row in value['surfaces'] if row['name'] not in ('HomeEventsDrawer', 'HUDLoss')]
        with self.assertRaisesRegex(RuntimeError, 'NativeExpandedAffectedSurfaceCoverageMissing'):
            collect.backdrop_scope(value)

    def test_zero_additional_dimmer_coverage_and_control_leaks_are_rejected(self):
        for field in ('homeDrawerBandPixels', 'hudLossBandPixels', 'newBandPixels', 'modalBandPixels'):
            value = self.backdrop()
            value[field] = 0
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'NativePixelCoverageNotEstablished'):
                collect.backdrop_scope(value)
        value = self.backdrop()
        value['maskedControlLeaks'] = 1
        with self.assertRaisesRegex(RuntimeError, 'NativeInteractiveMaskLeak'):
            collect.backdrop_scope(value)

    def test_incomplete_or_failed_new_dimmer_geometry_is_rejected(self):
        value = self.backdrop()
        value['surfaces'].pop()
        with self.assertRaisesRegex(RuntimeError, 'NativeAffectedSurfaceNotPassed'):
            collect.backdrop_scope(value)
        value = self.backdrop()
        next(row for row in value['surfaces'] if row['name'] == 'HUDLoss')['passed'] = False
        with self.assertRaisesRegex(RuntimeError, 'NativeAffectedSurfaceNotPassed:HUDLoss'):
            collect.backdrop_scope(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(EvidenceControls))
    print(stream.getvalue(), end='')
    record = {'schemaVersion': 1, 'checkpoint': 90, 'utc': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS_HOST_EVIDENCE90_CONTROLS' if result.wasSuccessful() else 'FAIL_HOST_EVIDENCE90_CONTROLS',
              'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'scope': 'Host evidence parser, scope, tamper, privacy, original PNG and strict Windows process-selector rejection controls. Selector policy fixtures are mocked; the Windows command-line tokenizer is called read-only. No Unity launch, process termination, Android, ADB, UI, backend or provider test.'}
    if args.report:
        path = args.report.resolve()
        if path.exists() or not path.is_relative_to(collect.OUT.resolve()):
            raise RuntimeError('FreshCurrent90HostReportRequired')
        collect.write(path, record)
    print(json.dumps(record))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
