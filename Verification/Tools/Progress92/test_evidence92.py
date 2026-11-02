"""Host-only provenance rejection controls; never dispatch Unity, ADB or input."""
import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import zlib

import collect_progress92 as collect
import phone
from baseline import BaselinePhone


class EvidenceControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='hotr-evidence92-')
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def data(self, text):
        path = self.folder / 'report.json'
        path.write_text(text, encoding='utf-8')
        return path

    def test_duplicate_json_cannot_override_failure(self):
        with self.assertRaisesRegex(RuntimeError, 'DuplicateJsonKey'):
            collect.read(self.data('{"status":"FAIL","status":"PASS"}'))

    def test_nonfinite_measurement_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'NonfiniteJson'):
            collect.read(self.data('{"ratio":NaN}'))

    def test_parent_and_absolute_path_escapes_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'ParentTraversalRefused'):
            collect.bound('../outside.json')
        with self.assertRaisesRegex(RuntimeError, 'EvidencePathOutsideScope'):
            collect.bound(self.folder / 'outside.json')

    def test_bound_receipt_mutation_is_rejected(self):
        path = self.data('{"status":"PASS"}')
        with mock.patch.object(collect, 'ROOT', self.folder):
            value = collect.binding(path)
            path.write_text('{"status":"FAIL"}', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'BoundArtifactChanged'):
                collect.check_binding(value)

    def test_public_secrets_are_rejected_but_serial_hash_is_allowed(self):
        for field in ('serial', 'access_token', 'privateKey', 'recovery-code'):
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'PrivateFieldInPublicEvidence'):
                collect.public_fields({'nested': [{field: 'value'}]})
        collect.public_fields({'serialSHA256': 'a' * 64})

    def test_incomplete_native_set_is_rejected(self):
        value = {'schemaVersion': 1, 'checkpoint': 92, 'status': 'PASS_NATIVE92_SET', 'runs': []}
        with mock.patch.object(collect, 'bound', return_value=self.data(json.dumps(value))):
            with self.assertRaisesRegex(RuntimeError, 'TwoNativeSuitesRequired'):
                collect.native_proof('unused', {})

    def test_failed_native_set_is_rejected(self):
        value = {'schemaVersion': 1, 'checkpoint': 92, 'status': 'FAIL_NATIVE92_SET', 'runs': []}
        with mock.patch.object(collect, 'bound', return_value=self.data(json.dumps(value))):
            with self.assertRaisesRegex(RuntimeError, 'NativeListScopeInvalid'):
                collect.native_proof('unused', {})

    def progress(self):
        families = ('RainCup', 'Wellworks', 'ProfileStats', 'TeamRally', 'TeamLife', 'Home')
        return {'cases': 120, 'ordinaryServicesConstructed': False, 'ordinaryProfileWrites': False,
                'oldRainPixelHeight': 2, 'newRainPixelHeight': 10, 'oldProfilePixelCount': 0, 'newProfilePixelCount': 8,
                'captures': ['RainCup_OneOfTen_Native.png', 'RainCup_Fixed_OneOfTen_Bar.png',
                             'RainCup_Old_Aspect_Bar_NegativeControl.png', 'Profile_OneOfFifty_Fixed_Bar.png'],
                'audits': [{'family': family, 'kind': 'actual-production-ugui-mesh-and-gpu', 'status': 'PASS', 'scope': 'Host schema fixture only'} for family in families]
                          + [{'family': family, 'kind': kind, 'status': status, 'scope': 'Host schema fixture only'}
                             for family, kind, status in (('Launch', 'source-invariant-only', 'REVIEWED_UNCHANGED'),
                                 ('LevelComplete', 'legacy-source-review-only', 'NOT_ACTIVE_WIN_ROUTE'),
                                 ('OnlineTeams', 'source-inventory-only', 'NO_SHARED_PROGRESS_BAR'))],
                'bars': [{'family': family, 'passed': True, 'width': width, 'height': height,
                          'ratio': ratio, 'fillHeight': 12, 'sliceMultiplier': 4, 'type': 'Sliced',
                          'preserveAspect': False, 'zeroHidden': ratio == 0}
                         for family in families for width, height in ((320, 568), (393, 852), (720, 1600), (768, 1024))
                         for ratio in (0, .02, .1, .5, 1)]}

    def test_six_actual_bar_families_are_required(self):
        collect.progress_scope(self.progress())
        value = self.progress()
        value['bars'] = [row for row in value['bars'] if row['family'] != 'Home']
        with self.assertRaisesRegex(RuntimeError, 'NativeAffectedProgressFamilyMissing'):
            collect.progress_scope(value)

    def test_failed_bar_geometry_cannot_be_promoted(self):
        value = self.progress()
        value['bars'][0]['passed'] = False
        with self.assertRaisesRegex(RuntimeError, 'NativeProgressFamilyNotPassed:RainCup'):
            collect.progress_scope(value)

    def test_full_only_or_zero_height_raincup_proof_is_rejected(self):
        for change in ({'ratio': 1}, {'ratio': 0}, {'fillHeight': 0}):
            value = self.progress()
            value['bars'][2].update(change)
            with self.subTest(change=change), self.assertRaisesRegex(RuntimeError, 'NativeProgress(RatioMatrixIncomplete|ShapeContractMissing):RainCup'):
                collect.progress_scope(value)

    def test_missing_matrix_row_and_negative_controls_are_rejected(self):
        value = self.progress()
        value['bars'].pop()
        with self.assertRaisesRegex(RuntimeError, 'NativeProgressMatrixIncomplete'):
            collect.progress_scope(value)
        value = self.progress()
        value['newRainPixelHeight'] = value['oldRainPixelHeight']
        with self.assertRaisesRegex(RuntimeError, 'NativeNegativeControlsNotEstablished'):
            collect.progress_scope(value)

    def test_old_owner_frames_cannot_be_claimed_matched(self):
        history = {'apks': [{'development': True, 'sha256': 'a' * 64}],
                   'physical': {'target': {'path': 'Verification/Evidence/PageBackdrop90/Phone/Device01/Target.json'}}}
        with self.assertRaisesRegex(RuntimeError, 'MatchedRainCupAndProfileBeforeRequired'):
            collect.before_proof({'beforeReferences': [{'name': 'RainCup', 'matchedOwnerState': False}]}, collect.OUT / 'Phone/Device01', history)

    def test_baseline_reader_cannot_install(self):
        reader = BaselinePhone.__new__(BaselinePhone)
        with self.assertRaisesRegex(RuntimeError, 'BaselineReaderCannotInstall'):
            reader.install()

    def test_png_crc_and_truncation_are_rejected(self):
        def chunk(kind, body):
            return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
        raw = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 3, 8, 6, 0, 0, 0))
               + chunk(b'IDAT', zlib.compress((b'\0' + b'\xff\0\0\xff' * 2) * 3)) + chunk(b'IEND', b''))
        self.assertEqual(phone.validate_png(raw), (2, 3))
        for damaged in (raw[:-12], raw[:-1], raw[:-1] + bytes([raw[-1] ^ 1])):
            with self.subTest(size=len(damaged)), self.assertRaises(RuntimeError):
                phone.validate_png(damaged)

    def test_owner_progress_equality_includes_profile_revision(self):
        value = {'activeAttempts': 0, 'installedSHA256': 'a' * 64,
                 'profiles': {'Profiles/local/profile.json': 'b' * 64},
                 'preferences': {'prefs.xml': 'c' * 64},
                 'profileSummaries': [{'revision': 36, 'activeAttempts': 0}]}
        before = collect._snapshot(value, 'a' * 64)
        value['profileSummaries'] = [{'revision': 37, 'activeAttempts': 0}]
        self.assertNotEqual(before, collect._snapshot(value, 'a' * 64))

    def test_missing_or_empty_profile_summaries_are_rejected(self):
        value = {'activeAttempts': 0, 'installedSHA256': 'a' * 64,
                 'profiles': {'Profiles/local/profile.json': 'b' * 64}, 'preferences': {'prefs.xml': 'c' * 64}}
        for summaries in (None, []):
            candidate = dict(value)
            if summaries is not None:
                candidate['profileSummaries'] = summaries
            with self.subTest(summaries=summaries), self.assertRaisesRegex(RuntimeError, 'PhoneSnapshotScopeInvalid'):
                collect._snapshot(candidate, 'a' * 64)

    def test_fifth_chain_requires_complete_matching_depth_and_links(self):
        target = {'upgradeChainDepth': 5, 'candidateApkSHA256': 'a' * 64}
        proof = {'depth': 5, 'candidateApkSHA256': 'a' * 64, 'links': [{}] * 5}
        with mock.patch.object(collect, 'validate_upgrade_chain', return_value=proof):
            collect.fifth_chain('unused', target)
            with self.assertRaisesRegex(RuntimeError, 'CompleteFifthOwnerPhoneLinkRequired'):
                collect.fifth_chain('unused', dict(target, upgradeChainDepth=4))
        for change in ({'depth': 4}, {'links': [{}] * 4}, {'candidateApkSHA256': 'b' * 64}):
            with self.subTest(change=change), mock.patch.object(collect, 'validate_upgrade_chain', return_value=dict(proof, **change)):
                with self.assertRaisesRegex(RuntimeError, 'CompleteFifthOwnerPhoneLinkRequired'):
                    collect.fifth_chain('unused', target)

    def finish_files(self):
        phone_dir = self.folder / 'phone'
        phone_dir.mkdir(exist_ok=True)
        body = {'FinalMarkerState.json': {'pendingOptInMarkers': []},
                'Relaunch.json': {'launchResult': 'Status: ok\nComplete', 'fixedObservationWaitSeconds': 8,
                                 'scope': 'Host fixture only; no actual launch.'}}
        for name, data in body.items():
            (phone_dir / name).write_text(json.dumps(data), encoding='utf-8')
        (phone_dir / 'Runtime.log').write_text('Host fixture, not an actual app log.\n', encoding='utf-8')
        review = {'pid': '123', 'log': 'Runtime.log', 'sha256': collect.sha(phone_dir / 'Runtime.log'),
                  'selectedErrorCount': 0, 'scope': 'Host parser fixture only.'}
        (phone_dir / 'Log_Review.json').write_text(json.dumps(review), encoding='utf-8')
        return phone_dir

    def test_finish_proof_requires_all_completion_receipts(self):
        phone_dir = self.finish_files()
        with mock.patch.object(collect, 'ROOT', self.folder):
            collect.finish_proof(phone_dir)
            for name in ('FinalMarkerState.json', 'Relaunch.json', 'Log_Review.json'):
                path = phone_dir / name
                original = path.read_bytes()
                path.unlink()
                try:
                    with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, 'MissingOrOversizedJsonReport'):
                        collect.finish_proof(phone_dir)
                finally:
                    path.write_bytes(original)

    def test_pending_final_marker_and_unsuccessful_relaunch_are_rejected(self):
        phone_dir = self.finish_files()
        with mock.patch.object(collect, 'ROOT', self.folder):
            (phone_dir / 'FinalMarkerState.json').write_text('{"pendingOptInMarkers":["unconsumed"]}', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'PhoneFinalMarkersNotEmpty'):
                collect.finish_proof(phone_dir)
            (phone_dir / 'FinalMarkerState.json').write_text('{"pendingOptInMarkers":[]}', encoding='utf-8')
            (phone_dir / 'Relaunch.json').write_text('{"launchResult":"Error: not launched","fixedObservationWaitSeconds":8,"scope":"Host only"}', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'OrdinaryRelaunchReceiptMissing'):
                collect.finish_proof(phone_dir)

    def test_scoped_log_tamper_and_selected_errors_are_rejected(self):
        phone_dir = self.finish_files()
        with mock.patch.object(collect, 'ROOT', self.folder):
            (phone_dir / 'Runtime.log').write_text('NullReferenceException\n', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'PhoneScopedLogChanged'):
                collect.finish_proof(phone_dir)
            path = phone_dir / 'Log_Review.json'
            value = json.loads(path.read_text('utf-8'))
            value['sha256'] = collect.sha(phone_dir / 'Runtime.log')
            path.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'PhoneSelectedLogErrorsPresent'):
                collect.finish_proof(phone_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(EvidenceControls))
    print(stream.getvalue(), end='')
    record = {'schemaVersion': 1, 'checkpoint': 92, 'utc': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS_HOST_EVIDENCE92_CONTROLS' if result.wasSuccessful() else 'FAIL_HOST_EVIDENCE92_CONTROLS',
              'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'scope': 'Host-only evidence parser, scope, tamper/privacy, native-family and owner-state rejection controls; original PNG decoding. No Unity, process, Android/ADB, UI, backend or provider execution.'}
    if args.report:
        path = args.report.resolve()
        if path.exists() or not path.is_relative_to(collect.OUT.resolve()):
            raise RuntimeError('FreshCurrent92HostReportRequired')
        collect.write(path, record)
    print(json.dumps(record))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
