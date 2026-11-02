"""Host-only probe preparation guards; never launches either Editor."""
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('payload94_under_host_test', Path(__file__).with_name('model_payload94.py'))
PAYLOAD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PAYLOAD)


class PayloadHostTests(unittest.TestCase):
    def test_approved_pure_closure_is11_exact_model_sources_plus_two_editor_dependencies(self):
        sources = PAYLOAD.sources()
        self.assertEqual(len(sources), 13)
        self.assertEqual(tuple(sources[-2:]), PAYLOAD.EXTRA)
        self.assertTrue(all((PAYLOAD.ROOT / path).is_file() and (PAYLOAD.ROOT / (path + '.meta')).is_file() for path in sources))
        self.assertFalse(any('PinnedReplayEngine' in path or '/M47/Runtime/' in path for path in sources))

    def test_only_two_fresh_private_probe_roots_are_valid(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_payload_path_host_') as directory:
            base = Path(directory) / 'ModelProbe'
            with patch.object(PAYLOAD, 'PROBES', base):
                self.assertEqual(PAYLOAD.relative_project(base / 'Baseline2022'), (base / 'Baseline2022').resolve())
                self.assertEqual(PAYLOAD.relative_project(base / 'Candidate6'), (base / 'Candidate6').resolve())
                for name in ('Project', 'Unity', 'Baseline2022/../Other'):
                    with self.assertRaisesRegex(RuntimeError, 'OnlyTwoMinimalProjectsAllowed'):
                        PAYLOAD.relative_project(base / name)

    def test_identical_template_exports_all11_named_raw_payloads(self):
        source = PAYLOAD.TEMPLATE.read_text('utf-8-sig')
        exported = re.findall(r'Export\(report,output,"([A-Za-z0-9]+)"', source)
        self.assertEqual(len(exported), 11)
        self.assertEqual(len(set(exported)), 11)
        self.assertTrue({'RawTurn', 'FinalSnapshot', 'FinalCheckpoint', 'InitialSnapshot', 'InitialCheckpoint',
                         'PlainPiece', 'PlainCell', 'InheritedFixture', 'LevelRoundtrip'}.issubset(exported))
        self.assertIn('new BoardModel(level,(uint)report.seed)', source)
        self.assertIn('HOTR_SERIALIZATION94_COORDINATES', source)
        self.assertNotIn('PinnedReplayEngine.Execute', source)
        self.assertNotIn('PlayerPrefs', source)

    def test_exact_versions_project_names_and_model_only_manifest_are_declared(self):
        self.assertEqual([(name, version) for name, version, _ in PAYLOAD.TARGETS],
                         [('Baseline2022', '2022.3.62f3'), ('Candidate6', '6000.6.6f1')])
        source = Path(PAYLOAD.__file__).read_text('utf-8-sig')
        self.assertIn('com.unity.modules.jsonserialize', source)
        self.assertNotIn('com.unity.ugui', source)
        self.assertNotIn('com.unity.recorder', source)
        self.assertIn('Payload94OldProbeMustReproduceAcceptedL1Corpus', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
