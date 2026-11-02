"""Host counterexamples for scoped collection; no Unity, Java, ADB or SDK runs."""
import importlib.util
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('collect_review94',
    Path(__file__).with_name('collect_review94.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


class ScopedCollectorGuards(unittest.TestCase):
    def test_missing_any_required_layer_never_completes(self):
        for missing in MODULE.REQUIRED_COMPONENTS:
            components = {name: {'passed': True} for name in MODULE.REQUIRED_COMPONENTS - {missing}}
            self.assertNotEqual(MODULE.completed_status(components, []), MODULE.COMPLETE)

    def test_failed_native_layer_never_completes(self):
        components = {name: {'passed': True} for name in MODULE.REQUIRED_COMPONENTS}
        components['native']['passed'] = False
        self.assertNotEqual(MODULE.completed_status(components, []), MODULE.COMPLETE)

    def test_an_issue_prevents_completion_even_with_all_true_flags(self):
        components = {name: {'passed': True} for name in MODULE.REQUIRED_COMPONENTS}
        self.assertNotEqual(MODULE.completed_status(components, [{'component': 'source', 'reason': 'drift'}]),
                            MODULE.COMPLETE)

    def test_all_explicit_scoped_layers_can_complete_without_production_approval(self):
        components = {name: {'passed': True} for name in MODULE.REQUIRED_COMPONENTS}
        self.assertEqual(MODULE.completed_status(components, []), MODULE.COMPLETE)
        self.assertIn('ISOLATED', MODULE.COMPLETE)
        self.assertIn('OPEN_GATES', MODULE.COMPLETE)

    def test_bound_artifact_modification_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'report.json'
            target.write_bytes(b'original')
            with mock.patch.object(MODULE, 'ROOT', root):
                expected = MODULE.binding(target)
                target.write_bytes(b'modified')
                with self.assertRaisesRegex(ValueError, 'bytes changed'):
                    MODULE.validate_binding(expected, root)

    def test_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            with self.assertRaisesRegex(ValueError, 'outside'):
                MODULE.contained(parent / '..' / 'unrelated', parent)

    def source_case(self, root):
        evidence = root / 'Evidence94'
        source_path = evidence / 'SourceAudit' / 'Report.json'
        candidate_path = source_path.parent / 'CandidateSources.json'
        diff = source_path.parent / 'Diffs' / 'ProjectSettings.asset.diff'
        source_path.parent.mkdir(parents=True)
        source_path.write_text('{}', encoding='utf-8')
        candidate_path.write_text('{}', encoding='utf-8')
        diff.parent.mkdir()
        diff.write_text('+ isolated splash setting\n', encoding='utf-8')
        index = [{'path': 'ProjectSettings/ProjectSettings.asset', 'binaryDiffOmitted': False,
                  'diff': diff.relative_to(root).as_posix()}]
        write(source_path.parent / 'TextDiffIndex.json', index)
        source = {'report': MODULE.binding(source_path), 'candidateSources': MODULE.binding(candidate_path)}
        review = {'status': 'ROOT_REVIEWED_ISOLATED_UNITY6_94_SOURCE_AND_SETTINGS',
                  'reviewer': 'root', 'sourceAudit': source['report'],
                  'candidateSources': source['candidateSources'], 'reviewedDiffs': [MODULE.binding(diff)],
                  'packageAndSerializedSettingsApprovedForIsolatedTest': True,
                  'importerChangesReviewed': True, 'mainPromotionApproved': False}
        review_path = evidence / 'RootSourceReview.json'
        write(review_path, review)
        return evidence, source, review, review_path

    def test_source_review_requires_every_bound_diff(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(MODULE, 'ROOT', root):
                evidence, source, review, path = self.source_case(root)
                with mock.patch.object(MODULE, 'OUT', evidence):
                    self.assertTrue(MODULE.source_review(path, source)['passed'])
                    review['reviewedDiffs'] = []
                    write(path, review)
                    with self.assertRaisesRegex(ValueError, 'every exported'):
                        MODULE.source_review(path, source)

    def test_source_review_cannot_silently_approve_main_promotion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(MODULE, 'ROOT', root):
                evidence, source, review, path = self.source_case(root)
                review['mainPromotionApproved'] = True
                write(path, review)
                with mock.patch.object(MODULE, 'OUT', evidence):
                    with self.assertRaisesRegex(ValueError, 'Explicit root'):
                        MODULE.source_review(path, source)

    def test_no_gallery_images_are_invented_without_manual_visual_list(self):
        record = {'status': 'INCOMPLETE', 'components': {}, 'issues': [], 'openGates': ['open']}
        page = MODULE.html_page(record, MODULE.OUT)
        self.assertNotIn('<img ', page)
        self.assertNotIn('<video ', page)

    def test_gallery_escapes_labels_and_keeps_failed_diagnostic_visible(self):
        native = {'selected': [{'name': 'Account <script>', 'passed': False,
                  'report': {'path': 'Verification/Evidence/Unity6Migration94/Account.json'},
                  'attemptedChecks': 44}], 'retainedUnselectedOrDiagnosticFailures': []}
        record = {'status': 'INCOMPLETE', 'components': {'native': native},
                  'issues': [{'component': 'test', 'reason': '<script>alert(1)</script>'}],
                  'openGates': ['Production remains open']}
        page = MODULE.html_page(record, MODULE.OUT)
        self.assertIn('FAIL retained diagnostic; unresolved', page)
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)

    def test_missing_sampled_startup_assessment_cannot_pass_visual_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'visual.json'
            reference = {'path': 'unused', 'sha256': '0' * 64, 'bytes': 1}
            review = {'status': 'ROOT_REVIEWED_ISOLATED_UNITY6_94_VISUALS', 'reviewer': 'root',
                'candidateSources': reference, 'developmentApk': reference,
                'startupPublication': reference, 'sampledStartupShowsNoUnitySplash': False,
                'artifacts': []}
            write(path, review)
            with mock.patch.object(MODULE, 'OUT', root):
                with self.assertRaisesRegex(ValueError, 'Explicit bound root'):
                    MODULE.visual_review(path, {'candidateSources': reference}, {'apk': reference},
                                         {'publication': reference}, {'selected': []}, {})

    def test_partial_model_corpus_cannot_be_labelled_passed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'Comparison.json'
            write(path, {'status': 'PASS_CROSS_ENGINE_350_MODEL_ROWS94',
                         'comparedRows': 349, 'rawTurnMatches': 349, 'finalSnapshotMatches': 349})
            with mock.patch.object(MODULE, 'OUT', root):
                with self.assertRaisesRegex(ValueError, 'Exact 350-row'):
                    MODULE.model(path, {})

    def startup_inventory(self):
        private = [{'path': f'private/{index}', 'sha256': f'{index:064x}', 'bytes': index + 1}
                   for index in range(47)]
        selected = [private[index] for index in (0, 1, 22, 21)]
        public = [dict(item, path=f'public/{index}') for index, item in enumerate(selected)]
        publication = {'schemaVersion': 2, 'privateArtifactInventory': private,
            'selectedPrivateArtifacts': selected, 'publishedArtifacts': public,
            'privateArtifactCount': 47, 'publishedArtifactCount': 4,
            'unpublishedPrivateArtifactCount': 43}
        privacy = {'schemaVersion': 2, 'reviewedArtifacts': selected, 'privateArtifactInventory': private}
        recording = {'captureId': 'a' * 32}
        return publication, recording, privacy, private, selected

    def test_startup_retains_47_but_validates_only_four_public_copies(self):
        values = self.startup_inventory()
        with mock.patch.object(MODULE, 'validate_binding') as validate:
            result = MODULE.validate_startup_inventory(*values, Path('public'))
        self.assertEqual(len(result), 4)
        self.assertEqual(validate.call_count, 51)
        self.assertEqual([call.args[0] for call in validate.call_args_list[:47]], values[3])

    def test_startup_legacy_publish_every_sample_rejected(self):
        publication, recording, privacy, private, selected = self.startup_inventory()
        publication['publishedArtifacts'] = copy.deepcopy(private)
        with self.assertRaisesRegex(ValueError, 'schema-2'):
            MODULE.validate_startup_inventory(publication, recording, privacy, private, selected, Path('public'))

    def test_startup_unselected_private_sample_tampering_is_rejected(self):
        values = self.startup_inventory()
        def check(item, parent):
            if item == values[3][46]:
                raise ValueError('Bound artifact bytes changed')
        with mock.patch.object(MODULE, 'validate_binding', side_effect=check):
            with self.assertRaisesRegex(ValueError, 'bytes changed'):
                MODULE.validate_startup_inventory(*values, Path('public'))

    def test_startup_selected_public_copy_tampering_is_rejected(self):
        publication, recording, privacy, private, selected = self.startup_inventory()
        publication['publishedArtifacts'][3]['sha256'] = 'f' * 64
        with mock.patch.object(MODULE, 'validate_binding'):
            with self.assertRaisesRegex(ValueError, 'differs'):
                MODULE.validate_startup_inventory(publication, recording, privacy, private, selected, Path('public'))

    def test_startup_privacy_cannot_claim_all47_were_selected_for_publication(self):
        publication, recording, privacy, private, selected = self.startup_inventory()
        privacy['reviewedArtifacts'] = private
        with self.assertRaisesRegex(ValueError, 'schema-2'):
            MODULE.validate_startup_inventory(publication, recording, privacy, private, selected, Path('public'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
