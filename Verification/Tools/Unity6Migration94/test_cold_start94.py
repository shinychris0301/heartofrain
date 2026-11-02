"""Host-only cold-start scope/privacy counterexamples; no ADB or ffmpeg calls."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('cold_start94_under_host_test', Path(__file__).with_name('cold_start94.py'))
VIDEO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VIDEO)


class ColdStartHostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr94_coldstart_host_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public = self.root / 'Evidence/ColdStart'
        self.private = self.root / 'Private/ColdStart'
        for name, value in (('ROOT', self.root), ('PUBLIC', self.public), ('PRIVATE', self.private)):
            active = patch.object(VIDEO, name, value)
            active.start()
            self.addCleanup(active.stop)

    def test_foreground_guard_rejects_another_app_before_recording(self):
        candidate = Mock()
        candidate.owner.adb.return_value = 'topResumedActivity=other.package/Activity'
        with self.assertRaisesRegex(RuntimeError, 'CandidateForegroundRequired'):
            VIDEO.foreground_unlocked(candidate)
        self.assertEqual(candidate.owner.adb.call_count, 1)

    def test_locked_candidate_is_refused_without_other_device_actions(self):
        candidate = Mock()
        candidate.owner.adb.side_effect = ['topResumedActivity=' + VIDEO.PACKAGE + '/Activity',
                                          'KeyguardServiceDelegate\n showing=true\n']
        with self.assertRaisesRegex(RuntimeError, 'UnlockedScreenRequired'):
            VIDEO.foreground_unlocked(candidate)
        self.assertEqual(candidate.owner.adb.call_count, 2)

    def test_screenrecord_is_bounded_and_only_candidate_files_are_accepted(self):
        candidate = SimpleNamespace(owner=SimpleNamespace(serial='HOSTTESTPRIVATESELECTOR'))
        api = SimpleNamespace(phone=SimpleNamespace(ADB=Path('host-fixture-adb-never-executed')))
        remote = '/sdcard/Android/data/' + VIDEO.PACKAGE + '/files/ColdStart94/' + 'a' * 32 + '/startup.mp4'
        command = VIDEO.recording_command(candidate, remote, api)
        self.assertEqual(command[-1], remote)
        self.assertEqual(command[command.index('--time-limit') + 1], '20')
        self.assertNotIn('force-stop', command)
        for bad in ('/sdcard/startup.mp4', remote.replace(VIDEO.PACKAGE, 'com.heartoftherain.verification'),
                    remote.replace('/startup.mp4', '/../startup.mp4')):
            with self.assertRaisesRegex(RuntimeError, 'CandidateVideoPathRequired'):
                VIDEO.recording_command(candidate, bad, api)

    def test_subprocess_exception_never_exposes_selector_or_captured_text(self):
        error = subprocess.CalledProcessError(1, ['adb', '-s', 'HOSTTESTPRIVATESELECTOR'],
                                             output=b'HOSTTESTPRIVATESELECTOR private response')
        safe = json.dumps(VIDEO.safe_failure(error))
        self.assertNotIn('HOSTTESTPRIVATESELECTOR', safe)
        self.assertNotIn('private response', safe)
        self.assertEqual(VIDEO.safe_failure(error), {'failureType': 'CalledProcessError'})

    def test_fresh_output_guard_refuses_existing_or_outside_capture(self):
        good = self.public / ('a' * 32)
        self.assertEqual(VIDEO.fresh_path(good, self.public), good.resolve())
        good.mkdir(parents=True)
        for path in (good, self.public, self.root / 'Outside'):
            with self.assertRaisesRegex(RuntimeError, 'FreshContainedPathRequired'):
                VIDEO.fresh_path(path, self.public)

    def test_completed_install_and_prior_ordinary_launch_are_required(self):
        directory = self.public.parent
        directory.mkdir(parents=True)
        apk = self.root / 'HostSyntheticNotAnApk.apk'
        apk.write_bytes(b'host-only schema fixture')
        current = VIDEO.bound(apk)
        candidate = SimpleNamespace(out=directory, build={'apk': apk})
        api = SimpleNamespace(phone=SimpleNamespace(_read_record=lambda path: json.loads(path.read_text('utf-8'))), binding=VIDEO.bound)
        install = {'status': 'PASS_FRESH_SIDE_BY_SIDE_INSTALL94', 'apk': current, 'ownerDataUnchanged': True}
        launch = {'status': 'RECORDED_ORDINARY_CANDIDATE_LAUNCH94_REQUIRES_VISUAL_REVIEW', 'apk': current, 'ownerDataUnchanged': True}
        (directory / 'Installation.json').write_text(json.dumps(install), encoding='utf-8')
        (directory / 'Launch.json').write_text(json.dumps(launch), encoding='utf-8')
        VIDEO.require_install_and_launch(candidate, api)
        launch['ownerDataUnchanged'] = False
        (directory / 'Launch.json').write_text(json.dumps(launch), encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'PriorOrdinaryCandidateLaunchRequired'):
            VIDEO.require_install_and_launch(candidate, api)

    def publication_fixture(self):
        token = 'b' * 32
        public = self.public / token
        private = self.private / token
        public.mkdir(parents=True)
        private.mkdir(parents=True)
        video = private / 'startup.mp4'
        video.write_bytes(b'Host-only artifact binding fixture. Never an Android video.')
        samples = []
        for name, count in (('Whole20s_1fps', 20), ('First6s_4fps', 24)):
            folder = private / name
            folder.mkdir()
            frames = []
            for index in range(count):
                image = folder / ('Frame_' + str(index + 1).zfill(3) + '.png')
                image.write_bytes(b'Host-only binding fixture, not a PNG')
                frames.append({'sampleIndex': index, 'nominalVideoSeconds': index if name == 'Whole20s_1fps' else index / 4,
                               'png': VIDEO.bound(image)})
            contact = private / (name + '_ContactSheet.png')
            contact.write_bytes(b'Host-only contact sheet binding fixture')
            samples.append({'name': name, 'frameCount': count, 'frames': frames, 'contactSheet': VIDEO.bound(contact)})
        report = {'status': 'RECORDED_CANDIDATE_COLD_START94_REQUIRES_VISUAL_REVIEW', 'captureId': token,
                  'ownerDataUnchanged': True, 'candidateDataUnchanged': True,
                  'ownerPreservedAtExit': True, 'candidatePreservedAtExit': True,
                  'privateOriginalVideo': VIDEO.bound(video), 'derivedReviewImages': {'samples': samples}}
        record_path = public / 'Recording.json'
        record_path.write_text(json.dumps(report), encoding='utf-8')
        review = {'schemaVersion': 2, 'status': 'ROOT_REVIEWED_CANDIDATE_STARTUP_PRIVACY94', 'reviewer': 'root',
                  'recording': VIDEO.bound(record_path), 'approvedForPublication': True,
                  'noUnrelatedPersonalContent': True, 'reviewedArtifacts': VIDEO.selected_publication_artifacts(report),
                  'privateArtifactInventory': VIDEO.publication_artifacts(report)}
        review_path = public / 'RootPrivacyReview.json'
        review_path.write_text(json.dumps(review), encoding='utf-8')
        return record_path, review_path, report, review

    def test_publication_selects_only_four_and_retains_all47_private_bindings(self):
        record_path, review_path, report, review = self.publication_fixture()
        checked, artifacts, source = VIDEO.validate_publication(record_path, review_path)
        self.assertEqual(len(artifacts), 4)
        self.assertEqual(len(VIDEO.publication_artifacts(report)), 47)
        self.assertEqual([Path(row['path']).name for row in artifacts],
                         ['startup.mp4', 'Whole20s_1fps_ContactSheet.png', 'First6s_4fps_ContactSheet.png', 'Frame_020.png'])
        self.assertEqual(checked, report)
        review['approvedForPublication'] = False
        review_path.write_text(json.dumps(review), encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'ExplicitRootPrivacyApprovalRequired'):
            VIDEO.validate_publication(record_path, review_path)
        self.assertFalse((record_path.parent / 'Published').exists())

    def test_modified_private_video_is_refused_after_root_review(self):
        record_path, review_path, report, _ = self.publication_fixture()
        (self.root / report['privateOriginalVideo']['path']).write_bytes(b'changed after privacy review')
        with self.assertRaisesRegex(RuntimeError, 'PrivateArtifactChangedOrOutsideCapture'):
            VIDEO.validate_publication(record_path, review_path)

    def test_incomplete_samples_and_failed_preservation_cannot_be_published(self):
        record_path, review_path, report, review = self.publication_fixture()
        partial = copy.deepcopy(report)
        partial['derivedReviewImages']['samples'][0]['frames'].pop()
        with self.assertRaisesRegex(RuntimeError, 'CompletePrivateReviewArtifactSetRequired'):
            VIDEO.publication_artifacts(partial)
        report['ownerPreservedAtExit'] = False
        record_path.write_text(json.dumps(report), encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'SuccessfulPreservedRecordingRequired'):
            VIDEO.validate_publication(record_path, review_path)

    def test_unknown_or_changed_recording_receipt_cannot_reuse_privacy_approval(self):
        record_path, review_path, report, review = self.publication_fixture()
        report['extraUnreviewedObservation'] = 'host-only fixture'
        record_path.write_text(json.dumps(report), encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'ExplicitRootPrivacyApprovalRequired'):
            VIDEO.validate_publication(record_path, review_path)

    def test_unpublished_private_frame_is_still_hash_validated(self):
        record_path, review_path, report, _ = self.publication_fixture()
        unselected = report['derivedReviewImages']['samples'][0]['frames'][0]['png']
        self.assertNotIn(unselected, VIDEO.selected_publication_artifacts(report))
        (self.root / unselected['path']).write_bytes(b'changed unpublished original')
        with self.assertRaisesRegex(RuntimeError, 'PrivateArtifactChangedOrOutsideCapture'):
            VIDEO.validate_publication(record_path, review_path)

    def test_old_all47_publication_approval_cannot_be_reused(self):
        record_path, review_path, report, review = self.publication_fixture()
        review['reviewedArtifacts'] = VIDEO.publication_artifacts(report)
        review_path.write_text(json.dumps(review), encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'ExplicitRootPrivacyApprovalRequired'):
            VIDEO.validate_publication(record_path, review_path)

    def test_missing_full_private_inventory_is_rejected(self):
        record_path, review_path, report, review = self.publication_fixture()
        review['privateArtifactInventory'].pop()
        review_path.write_text(json.dumps(review), encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'ExplicitRootPrivacyApprovalRequired'):
            VIDEO.validate_publication(record_path, review_path)

    def test_representative_frame_cannot_be_replaced_by_arbitrary_sample(self):
        _, _, report, _ = self.publication_fixture()
        report['derivedReviewImages']['samples'][0]['frames'][-1]['sampleIndex'] = 0
        with self.assertRaisesRegex(RuntimeError, 'FinalRepresentativeFrameRequired'):
            VIDEO.selected_publication_artifacts(report)

    def test_publish_copies_exactly_four_without_altering_any_private_artifact_or_recording(self):
        record_path, review_path, report, review = self.publication_fixture()
        inventory = VIDEO.publication_artifacts(report)
        before = [VIDEO.bound(self.root / row['path']) for row in inventory]
        record_bytes = record_path.read_bytes()
        synthetic_runner = self.root / 'synthetic_host_publisher.py'
        synthetic_runner.write_text('Host-only publication test; not a device runner.', encoding='utf-8')

        def save(path, value):
            with Path(path).open('x', encoding='utf-8') as stream:
                json.dump(value, stream)

        api = SimpleNamespace(phone=SimpleNamespace(utc=lambda: 'HOST_ONLY_SYNTHETIC_TIME'), save=save)
        with patch.object(VIDEO, 'helper', return_value=api), patch.object(VIDEO, '__file__', str(synthetic_runner)):
            receipt, path = VIDEO.publish(record_path, review_path)
        self.assertEqual(receipt['schemaVersion'], 2)
        self.assertEqual(receipt['privateArtifactCount'], 47)
        self.assertEqual(receipt['publishedArtifactCount'], 4)
        self.assertEqual(receipt['unpublishedPrivateArtifactCount'], 43)
        self.assertEqual(len(receipt['publishedArtifacts']), 4)
        self.assertEqual(receipt['privateArtifactInventory'], inventory)
        self.assertEqual(receipt['selectedPrivateArtifacts'], VIDEO.selected_publication_artifacts(report))
        self.assertEqual(len(list(path.parent.rglob('*.mp4'))), 1)
        self.assertEqual(len(list(path.parent.rglob('*.png'))), 3)
        self.assertEqual(record_path.read_bytes(), record_bytes)
        self.assertEqual([VIDEO.bound(self.root / row['path']) for row in inventory], before)
        self.assertEqual(len(list((self.private / report['captureId']).rglob('*.png'))), 46)


if __name__ == '__main__':
    unittest.main(verbosity=2)
