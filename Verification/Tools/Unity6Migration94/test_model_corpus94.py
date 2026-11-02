"""Meaningful host guards for diagnostics; no Unity execution or native pass claim."""
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

import diagnose_json94 as diagnostic
import model_corpus94 as corpus


class DiagnosticHostTests(unittest.TestCase):
    def test_decimal_difference_is_not_hidden_by_same_binary64_or_binary32_value(self):
        result = diagnostic.compare(b'{"duration":0.18000000715255738}', b'{"duration":0.18000000715255737}')
        self.assertFalse(result['rawBytesEqual']); self.assertFalse(result['exactDecimalScalarsEqual'])
        row = result['numericTokenDifferences'][0]
        self.assertFalse(row['exactDecimalEqual']); self.assertTrue(row['binary64BitsEqual']); self.assertTrue(row['binary32BitsEqual'])
        self.assertEqual(row['binary32BaselineBits'], '3e3851ec')

    def test_one_float32_ulp_change_is_detected_without_tolerance(self):
        result = diagnostic.compare('{"duration":0.18000000715255738}', '{"duration":0.18000002205371857}')
        self.assertFalse(result['allDifferentNumericTokensHaveIdenticalBinary32Bits'])
        self.assertFalse(result['numericTokenDifferences'][0]['binary32BitsEqual'])

    def test_integer_change_is_never_treated_as_float32_formatting(self):
        result = diagnostic.compare('{"coins":9007199254740992}', '{"coins":9007199254740993}')
        self.assertFalse(result['exactDecimalScalarsEqual']); self.assertFalse(result['allDifferentNumericTokensHaveIdenticalBinary32Bits'])
        self.assertNotIn('binary32BitsEqual', result['numericTokenDifferences'][0])

    def test_object_order_and_non_numeric_scalars_are_retained(self):
        result = diagnostic.compare('{"a":true,"b":"old"}', '{"b":"new","a":true}')
        self.assertEqual(len(result['objectOrderDifferences']), 1)
        self.assertEqual(result['structuralOrNonNumericDifferences'][0]['path'], '/b')

    def test_duplicate_keys_and_non_finite_numbers_are_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ValueError): diagnostic.compare(raw, raw)

    def test_array_length_order_and_numeric_type_changes_are_detected(self):
        result = diagnostic.compare('{"a":[1,2],"b":1}', '{"a":[2,1,3],"b":"1"}')
        self.assertEqual(len(result['numericTokenDifferences']), 2)
        self.assertEqual(len(result['structuralOrNonNumericDifferences']), 2)

    def test_raw_payload_tampering_is_rejected_before_diagnostics(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_corpus_host_') as folder:
            directory = Path(folder); sha = hashlib.sha256(b'{}').hexdigest(); rows = []; references = []
            for name in sorted(corpus.historical.expected_names()):
                payloads = []
                for kind in ('RawTurn', 'FinalSnapshot', 'FinalCheckpoint'):
                    path = directory / (name + '_' + kind + '.json'); path.write_bytes(b'{}')
                    payloads.append({'name': kind, 'file': path.name, 'sha256': sha, 'bytes': 2})
                rows.append({'name': name, 'payloads': payloads})
                references.append({'name': name, **{field: sha for field in (*corpus.historical.HASH_FIELDS, *corpus.historical.EXTRA_FIELDS)}})
            report = {'status': 'PASS_ACTUAL_SERIALIZATION_CORPUS94', 'rows': rows}
            reference = {'status': 'PASS_NATIVE_LOCAL_CASCADE73', 'errors': [], 'rawTurnParity': True,
                         'finalSnapshotParity': True, 'modelCases': 350, 'checks': 1, 'rows': references}
            class API:
                @staticmethod
                def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(len(corpus.native_rows(report, directory, API(), reference)), 350)
            (directory / rows[0]['payloads'][0]['file']).write_bytes(b'{"changed":true}')
            with self.assertRaisesRegex(RuntimeError, 'NativePayloadTampered'):
                corpus.native_rows(report, directory, API(), reference)

    def test_template_uses_exact_model_selection_and_complete_native_typed_signature(self):
        text = corpus.TEMPLATE.read_text('utf-8-sig')
        for expression in ('new BoardModel(data)', 'board.LegalSwaps().First()', 'board.Pieces.Values.First(p=>p.family=="gem")',
                           'new[]{-1,4,5,7,11,16,21}', 'FinalCheckpoint', 'typedSHA256', 'BindingFlags.Public|BindingFlags.Instance',
                           'field.DeclaringType.FullName', 'writer.Write((float)value)', 'writer.Write((double)value)',
                           'Typed94 refuses untraversed private serialized field'):
            self.assertIn(expression, text)
        self.assertNotIn('Math.Round', text); self.assertNotIn('GetHashCode', text); self.assertNotIn('PinnedReplayEngine.Execute', text)


if __name__ == '__main__': unittest.main(verbosity=2)
