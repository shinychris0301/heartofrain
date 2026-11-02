"""Host-only counterexamples for the candidate-only mutation guard; no Unity runs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('adapt_test_pins94_under_test', Path(__file__).with_name('adapt_test_pins.py'))
ADAPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPT)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='hotr94_testpin_host_')
        self.root = Path(self.temporary.name)
        self.project = self.root / '.verification-cache/Unity6Migration94/Project'
        self.project.mkdir(parents=True)
        self.evidence = self.root / 'Verification/Evidence/Unity6Migration94'
        self.evidence.mkdir(parents=True)
        self.patches = [patch.object(ADAPT, name, value) for name, value in (
            ('ROOT', self.root), ('PROJECT', self.project), ('EVIDENCE', self.evidence))]
        for item in self.patches:
            item.start()
        self.baseline = {'files': {}}
        for relative, old, _ in ADAPT.ADAPTATIONS:
            content = b'// Host fixture with CRLF\r\nif (' + old + b') Check(true);\r\n'
            for parent in (self.root / 'Unity', self.project):
                target = parent / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            self.baseline['files']['Unity/' + relative] = {'sha256': ADAPT.sha_bytes(content), 'bytes': len(content)}

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temporary.cleanup()

    def test_main_and_neighbor_project_are_refused(self):
        for wrong in (self.root / 'Unity', self.root / '.verification-cache/Unity6Migration94/ProjectSibling'):
            wrong.mkdir(parents=True, exist_ok=True)
            with self.assertRaises(ValueError):
                ADAPT.exact_project(wrong)

    def test_fresh_evidence_must_be_contained_and_unique(self):
        good = self.evidence / 'TestPins/Set01'
        self.assertEqual(ADAPT.fresh_output(good), good.resolve())
        good.mkdir(parents=True)
        for invalid in (good, self.evidence, self.root / 'Outside', self.project / 'Evidence'):
            with self.assertRaises(ValueError):
                ADAPT.fresh_output(invalid)

    def test_preparation_is_read_only_and_changes_only_three_version_literals(self):
        before = {path: path.read_bytes() for path in self.root.rglob('*.cs')}
        changes = ADAPT.prepare_changes(ADAPT.exact_project(self.project), self.baseline)
        self.assertEqual(len(changes), 3)
        for change, (relative, old, new) in zip(changes, ADAPT.ADAPTATIONS):
            self.assertEqual(change['relative'], relative)
            self.assertEqual(change['after'].replace(new, old, 1), change['before'])
            self.assertEqual(change['before'].count(b'\r\n'), change['after'].count(b'\r\n'))
        self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob('*.cs')})

    def test_candidate_api_or_assertion_edit_is_rejected_before_any_writes(self):
        path = self.project / ADAPT.ADAPTATIONS[-1][0]
        path.write_bytes(path.read_bytes() + b'// Unreviewed API change\r\n')
        before = {node: node.read_bytes() for node in self.root.rglob('*.cs')}
        with self.assertRaisesRegex(ValueError, 'ExactApprovedMainBytes'):
            ADAPT.prepare_changes(self.project, self.baseline)
        self.assertEqual(before, {node: node.read_bytes() for node in self.root.rglob('*.cs')})

    def test_main_change_is_rejected_even_if_candidate_matches_old_baseline(self):
        path = self.root / 'Unity' / ADAPT.ADAPTATIONS[0][0]
        path.write_bytes(path.read_bytes() + b'// Changed main\r\n')
        with self.assertRaisesRegex(ValueError, 'ExactApprovedMainBytes'):
            ADAPT.prepare_changes(self.project, self.baseline)

    def test_duplicate_version_assertion_cannot_be_adapted(self):
        relative, old, _ = ADAPT.ADAPTATIONS[0]
        duplicate = b'if (' + old + b') {}\r\nif (' + old + b') {}\r\n'
        for base in (self.root / 'Unity', self.project):
            (base / relative).write_bytes(duplicate)
        self.baseline['files']['Unity/' + relative] = {'sha256': ADAPT.sha_bytes(duplicate), 'bytes': len(duplicate)}
        with self.assertRaisesRegex(ValueError, 'SingleExactVersionAssertionRequired'):
            ADAPT.prepare_changes(self.project, self.baseline)

    def test_hard_linked_candidate_cannot_modify_main_inode(self):
        import os
        relative = ADAPT.ADAPTATIONS[0][0]
        target = self.project / relative
        target.unlink()
        os.link(self.root / 'Unity' / relative, target)
        with self.assertRaisesRegex(ValueError, 'HardLinkedInputRefused'):
            ADAPT.prepare_changes(self.project, self.baseline)

    def test_focused_plan_has_no_trusted_worker_entry_and_exact_candidate(self):
        plan = json.loads(Path(__file__).with_name('suites94.json').read_text('utf-8'))
        self.assertEqual(plan['candidateUnity'], '6000.6.6f1')
        self.assertEqual(len(plan['cases']), 9)
        self.assertEqual({x['name'] for x in plan['cases'] if not x['reportHasUnity']},
                         {'ProfileTransactions', 'MixedPowerSwap', 'LocalCascade'})
        for case in plan['cases']:
            self.assertNotIn('PinnedReplay', case['entry'])
            self.assertTrue(30 <= case['timeoutSeconds'] <= 900)
            self.assertFalse(case['quit'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
