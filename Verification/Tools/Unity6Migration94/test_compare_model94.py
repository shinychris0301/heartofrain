"""Host-only corpus/provenance counterexamples; no Editor or backend execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('model94_under_host_test', Path(__file__).with_name('compare_model94.py'))
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


def corpus():
    rows = []
    for name in sorted(MODEL.expected_names()):
        row = {'name': name}
        for field in (*MODEL.HASH_FIELDS, *MODEL.EXTRA_FIELDS):
            row[field] = hashlib.sha256(('HOST-ONLY-FIXTURE:' + name + ':' + field).encode()).hexdigest()
        rows.append(row)
    return {'status': 'PASS_NATIVE_LOCAL_CASCADE73', 'errors': [], 'rawTurnParity': True,
            'finalSnapshotParity': True, 'modelCases': 350, 'checks': 700, 'rows': rows}


class ModelComparisonHostTests(unittest.TestCase):
    def test_equal350_sample_rows_are_compared_by_name_without_fabricated_native_execution(self):
        left = corpus()
        right = copy.deepcopy(left)
        right['rows'].reverse()
        result = MODEL.compare_rows(left, right)
        self.assertEqual(result['comparedRows'], 350)
        self.assertEqual(result['rawTurnMatches'], 350)
        self.assertEqual(result['finalSnapshotMatches'], 350)
        self.assertTrue(result['all350RawTurnsAndFinalSnapshotsEqual'])

    def test_duplicate_row_cannot_replace_an_unseen_level_or_power(self):
        report = corpus()
        report['rows'][-1] = copy.deepcopy(report['rows'][0])
        with self.assertRaisesRegex(ValueError, 'Unique350RowNamesRequired'):
            MODEL.validate_rows(report)

    def test_missing_row_and_wrong_named_row_are_refused(self):
        report = corpus()
        report['rows'].pop()
        with self.assertRaisesRegex(ValueError, 'Exactly350RowsRequired'):
            MODEL.validate_rows(report)
        report = corpus()
        report['rows'][0]['name'] = 'L999_unapproved'
        with self.assertRaisesRegex(ValueError, 'Exact50BySevenCorpusRequired'):
            MODEL.validate_rows(report)

    def test_every_raw_turn_and_final_hash_difference_is_retained_and_fails_parity(self):
        left, right = corpus(), corpus()
        changed = right['rows'][9]
        changed['turnHash'] = '1' * 64
        changed['finalHash'] = '2' * 64
        result = MODEL.compare_rows(left, right)
        self.assertFalse(result['all350RawTurnsAndFinalSnapshotsEqual'])
        self.assertEqual(result['rawTurnMatches'], 349)
        self.assertEqual(result['finalSnapshotMatches'], 349)
        self.assertEqual(result['differences'][0]['name'], changed['name'])
        self.assertEqual(result['differences'][0]['candidateTurnHash'], '1' * 64)

    def test_invalid_hash_or_nonpassing_native_corpus_is_refused(self):
        report = corpus()
        report['rows'][0]['turnHash'] = 'not-a-hash'
        with self.assertRaisesRegex(ValueError, 'FullRawHashFieldsRequired'):
            MODEL.validate_rows(report)
        report = corpus()
        report['errors'] = ['actual native failure']
        with self.assertRaisesRegex(ValueError, 'PassedNativeModelCorpusRequired'):
            MODEL.validate_rows(report)

    def test_historical_bound_file_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_model_hash_host_') as directory:
            root = Path(directory)
            path = root / 'historical-native-fixture.json'
            path.write_bytes(b'Host-only provenance counterexample')
            with patch.object(MODEL, 'ROOT', root):
                expected = MODEL.binding(path)
                path.write_bytes(b'changed historical source')
                with self.assertRaisesRegex(ValueError, 'HistoricalBoundArtifactChanged'):
                    MODEL.bound_matches(path, expected)

    def test_actual_candidate_process_version_and_report_log_hashes_are_required(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_model_process_host_') as directory:
            root = Path(directory)
            path = root / 'LocalCascade.json'
            log = root / 'Unity.log'
            native = corpus()
            path.write_text(json.dumps(native), encoding='utf-8')
            log.write_text('HOST FIXTURE ONLY\nInitialize engine version: 6000.6.6f1 (fixture)\n', encoding='utf-8')
            invocation = {'status': 'PASS_ISOLATED_UNITY6_94_NATIVE', 'exitCode': 0, 'entry': MODEL.ENTRY,
                          'expectedVersion': MODEL.VERSION, 'actualEngineVersionFromProcessLog': MODEL.VERSION,
                          'legacyReportWithoutUnityField': True, 'mainInputsUnchanged': True, 'unityPidsAfter': [],
                          'nativeStatus': 'PASS_NATIVE_LOCAL_CASCADE73', 'nativeReportSHA256': MODEL.digest(path),
                          'nativeReport': 'LocalCascade.json', 'unityLogSHA256': MODEL.digest(log)}
            with patch.object(MODEL, 'ROOT', root):
                MODEL.validate_candidate_invocation(invocation, native, path, log)
                wrong = dict(invocation, actualEngineVersionFromProcessLog='2022.3.62f3')
                with self.assertRaisesRegex(ValueError, 'PassedBoundCandidateProcessRequired'):
                    MODEL.validate_candidate_invocation(wrong, native, path, log)
                log.write_text('Initialize engine version: 2022.3.62f3\n', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'PassedBoundCandidateProcessRequired'):
                    MODEL.validate_candidate_invocation(invocation, native, path, log)

    def test_real_accepted93_native_and_source_bindings_are_current(self):
        # Read-only observation of accepted artifacts; no native test rerun.
        report, sources, proof = MODEL.validate_baseline()
        self.assertEqual(len(report['rows']), 350)
        self.assertEqual(sources['inputCount'], 5407)
        self.assertEqual(proof['baselineEngine'], '2022.3.62f3')

    def test_current_core_source_change_is_rejected_and_worker_is_never_repinned(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_model_source_host_') as directory:
            root = Path(directory)
            project = root / 'Candidate'
            paths = ['Assets/HeartOfTheRain/M46/Runtime/HostFixture' + str(i) + '.cs' for i in range(10)]
            paths.append(MODEL.WORKER_SOURCE)
            main, candidate = {'files': {}}, {'files': {}}
            for relative in paths:
                content = (b'// HOST FIXTURE, never native model source\n' if relative != MODEL.WORKER_SOURCE else
                           b'pins.unity!="2022.3.62f3";Application.unityVersion=="2022.3.62f3";')
                for base in (root / 'Unity', project):
                    path = base / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
                expected = {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}
                main['files']['Unity/' + relative] = expected
                candidate['files'][relative] = expected
            with patch.object(MODEL, 'ROOT', root), patch.object(MODEL, 'PROJECT', project):
                proof = MODEL.verify_unchanged_model_sources(main, candidate)
                self.assertTrue(proof['trustedWorkerSourcePinUnchanged'])
                (project / paths[0]).write_bytes(b'changed model')
                with self.assertRaisesRegex(ValueError, 'CoreOrTrustedWorkerSourceChanged'):
                    MODEL.verify_unchanged_model_sources(main, candidate)


if __name__ == '__main__':
    unittest.main(verbosity=2)
