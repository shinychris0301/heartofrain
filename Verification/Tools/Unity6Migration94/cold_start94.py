"""Root-only candidate cold-start video; private until an explicit privacy review."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / 'Verification/Evidence/Unity6Migration94/Phone/Device01/ColdStart'
PRIVATE = ROOT / '.verification-cache/Unity6Migration94/ColdStart'
PACKAGE = 'com.heartoftherain.unity6review94'
ACTIVITY = PACKAGE + '/com.unity3d.player.UnityPlayerActivity'
SECONDS = 20
BIT_RATE = 8000000
MAXIMUM_VIDEO_BYTES = 100 * 1024 * 1024


def helper():
    spec = importlib.util.spec_from_file_location('cold_start94_candidate', Path(__file__).with_name('phone94.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def need(condition, code):
    if not condition:
        raise RuntimeError(code)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def reject_links(path):
    for node in (Path(path), *Path(path).parents):
        if node.exists():
            value = node.stat()
            need(not node.is_symlink() and not getattr(value, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT,
                 'ColdStart94LinkedPathRefused')
            need(not node.is_file() or value.st_nlink == 1, 'ColdStart94HardLinkedFileRefused')


def fresh_path(path, parent):
    path, parent = Path(path), Path(parent)
    reject_links(path)
    need(path.resolve().is_relative_to(parent.resolve()) and path.resolve() != parent.resolve() and not path.exists(),
         'ColdStart94FreshContainedPathRequired')
    return path.resolve()


def bound(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT), 'ColdStart94WorkspaceArtifactRequired')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path), 'bytes': path.stat().st_size}


def safe_failure(error):
    # Never serialize subprocess repr, args, stdout, stderr or a USB selector.
    value = {'failureType': type(error).__name__}
    if isinstance(error, (RuntimeError, ValueError)) and re.fullmatch(r'[A-Za-z0-9]{1,120}', str(error)):
        value['failureCategory'] = str(error)
    return value


def foreground_unlocked(candidate):
    activities = candidate.owner.adb('shell', 'dumpsys', 'activity', 'activities', timeout=30)
    resumed = [line for line in activities.splitlines() if 'topResumedActivity=' in line or 'mResumedActivity:' in line]
    need(any(PACKAGE + '/' in line for line in resumed), 'ColdStart94CandidateForegroundRequired')
    policy = candidate.owner.adb('shell', 'dumpsys', 'window', 'policy', timeout=30)
    policy = policy.split('KeyguardServiceDelegate', 1)[-1]
    need(re.search(r'(?m)^\s*showing=false\s*$', policy) is not None
         and re.search(r'(?m)^\s*showing=true\s*$', policy) is None, 'ColdStart94UnlockedScreenRequired')


def require_install_and_launch(candidate, api):
    installation_path = candidate.out / 'Installation.json'
    launch_path = candidate.out / 'Launch.json'
    installation = api.phone._read_record(installation_path)
    launch = api.phone._read_record(launch_path)
    current_apk = api.binding(candidate.build['apk'])
    need(installation.get('status') == 'PASS_FRESH_SIDE_BY_SIDE_INSTALL94'
         and installation.get('apk') == current_apk and installation.get('ownerDataUnchanged') is True,
         'ColdStart94CompletedCurrentCandidateInstallRequired')
    need(launch.get('status') == 'RECORDED_ORDINARY_CANDIDATE_LAUNCH94_REQUIRES_VISUAL_REVIEW'
         and launch.get('apk') == current_apk and launch.get('ownerDataUnchanged') is True,
         'ColdStart94PriorOrdinaryCandidateLaunchRequired')
    return {'candidateInstallation': bound(installation_path), 'candidateOrdinaryLaunch': bound(launch_path)}


def recording_command(candidate, remote, api):
    expected = '/sdcard/Android/data/' + PACKAGE + '/files/ColdStart94/'
    need(remote.startswith(expected) and re.fullmatch(re.escape(expected) + r'[0-9a-f]{32}/startup\.mp4', remote) is not None,
         'ColdStart94CandidateVideoPathRequired')
    # This list contains a private selector. Never serialize it in evidence/logs.
    return [str(api.phone.ADB), '-s', candidate.owner.serial, 'shell', 'screenrecord',
            '--time-limit', str(SECONDS), '--bit-rate', str(BIT_RATE), remote]


def extract_frames(video, private, api):
    # Imported only for explicit root recording execution, never by host tests.
    import imageio_ffmpeg
    from PIL import Image, ImageDraw
    executable = Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
    need(executable.is_file(), 'ColdStart94FfmpegRequired')
    decoder_hash = digest(executable)
    rows = []
    for name, fps, limit, expected in (('Whole20s_1fps', 1, 20, 20), ('First6s_4fps', 4, 6, 24)):
        folder = fresh_path(private / name, private)
        folder.mkdir()
        command = [str(executable), '-nostdin', '-hide_banner', '-loglevel', 'error', '-n', '-i', str(video),
                   '-t', str(limit), '-vf', 'fps=' + str(fps), '-frames:v', str(expected), str(folder / 'Frame_%03d.png')]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        need(result.returncode == 0, 'ColdStart94ReadOnlyFrameDecodeFailed')
        images = sorted(folder.glob('Frame_*.png'))
        need(len(images) == expected, 'ColdStart94CompleteRequestedFrameSamplesRequired')
        width, height = api.phone.validate_png(images[0].read_bytes())
        need(0 < width < height <= 5000, 'ColdStart94PortraitVideoFramesRequired')
        columns = 5 if fps == 1 else 6
        thumb_width = 240
        thumb_height = round(height * thumb_width / width)
        label_height = 24
        sheet = Image.new('RGB', (columns * thumb_width, ((expected + columns - 1) // columns) * (thumb_height + label_height)), (10, 17, 27))
        draw = ImageDraw.Draw(sheet)
        frames = []
        for index, path in enumerate(images):
            need(api.phone.validate_png(path.read_bytes()) == (width, height), 'ColdStart94InconsistentVideoFrameSize')
            with Image.open(path) as original:
                original.load()
                image = original.convert('RGB').resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            x, y = index % columns * thumb_width, index // columns * (thumb_height + label_height)
            sheet.paste(image, (x, y + label_height))
            seconds = index / fps
            draw.text((x + 4, y + 4), f'video {seconds:.2f} s', fill=(255, 255, 255))
            frames.append({'sampleIndex': index, 'nominalVideoSeconds': seconds, 'png': bound(path)})
        sheet_path = private / (name + '_ContactSheet.png')
        need(not sheet_path.exists(), 'ColdStart94FreshContactSheetRequired')
        sheet.save(sheet_path)
        rows.append({'name': name, 'fps': fps, 'requestedSeconds': limit, 'frameCount': len(frames),
                     'sourceWidth': width, 'sourceHeight': height, 'frames': frames, 'contactSheet': bound(sheet_path),
                     'scope': 'Decoded samples from the retained original Android video, labelled by nominal decoder sampling time. Contact sheet thumbnails are for review; full-resolution sampled frames and original video remain authoritative.'})
    need(digest(executable) == decoder_hash, 'ColdStart94DecoderChanged')
    return {'imageioFfmpegVersion': imageio_ffmpeg.__version__, 'ffmpegSHA256': decoder_hash, 'samples': rows}


def record(build):
    api = helper()
    candidate = api.Candidate(build)
    install = require_install_and_launch(candidate, api)
    candidate.assert_installed()
    owner_before = candidate.owner_snapshot()
    candidate_before = candidate.idle(initialized=True)
    foreground_unlocked(candidate)
    token = uuid.uuid4().hex
    directory = fresh_path(PUBLIC / token, PUBLIC)
    private = fresh_path(PRIVATE / token, PRIVATE)
    directory.mkdir(parents=True)
    private.mkdir(parents=True)
    remote_directory = '/sdcard/Android/data/' + PACKAGE + '/files/ColdStart94/' + token
    remote = remote_directory + '/startup.mp4'
    need(not candidate.owner.exists(remote_directory), 'ColdStart94FreshRemoteVideoRequired')
    record = candidate.header('cold-start-video')
    record.update(install, status='RUNNING_ISOLATED_CANDIDATE_COLD_START94', captureId=token,
                  coldStartRunner=bound(Path(__file__)), privateVideoPublicationApproved=False,
                  videoTimeLimitSeconds=SECONDS, requestedBitRate=BIT_RATE, candidateOnlyRestart=True,
                  scope='Actual Android screenrecord of the already initialized isolated candidate, followed by am start -S -W for that candidate only. Original video and derived frames are private pending root privacy/visual review. No owner launch/stop/update, data clear, unrelated app intent, diagnostic marker or reward action. Video dispatch and encoded frame clocks are unsynchronized; neither this recording nor am start duration establishes a startup SLA or automatically proves splash absence.')
    api.save(directory / 'OwnerBefore.json', owner_before)
    api.save(directory / 'CandidateBefore.json', candidate_before)
    api.save(directory / 'Authorization.json', record)
    process = None
    video = private / 'startup.mp4'
    try:
        # A freshly owned directory under candidate external files only.
        candidate.owner.adb('shell', 'mkdir', '-p', remote_directory, timeout=30)
        foreground_unlocked(candidate)
        need(api.stable(candidate.owner_snapshot()) == api.stable(owner_before), 'ColdStart94OwnerChangedBeforeRecording')
        need(api.stable(candidate.idle()) == api.stable(candidate_before), 'ColdStart94CandidateChangedBeforeRecording')
        command = recording_command(candidate, remote, api)
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        with (private / 'screenrecord.stdout').open('xb') as stdout, (private / 'screenrecord.stderr').open('xb') as stderr:
            began = time.monotonic()
            record['recordCommandUtc'] = api.phone.utc()
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr,
                                       creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startup)
            time.sleep(1)
            need(process.poll() is None, 'ColdStart94ScreenRecorderExitedBeforeRestart')
            record['candidateRestartDispatchUtc'] = api.phone.utc()
            record['restartDispatchSecondsAfterRecordCommand'] = round(time.monotonic() - began, 6)
            result = candidate.owner.adb('shell', 'am', 'start', '-S', '-W', '-n', ACTIVITY, timeout=45)
            need(re.search(r'(?m)^Status:\s*ok\s*$', result) is not None, 'ColdStart94CandidateColdStartFailed')
            # Keep original command output only privately; it is not a timing SLA.
            with (private / 'candidate_am_start.txt').open('x', encoding='utf-8') as stream:
                stream.write(result.replace(candidate.owner.serial, 'physical-phone-1'))
            process.wait(timeout=45)
            need(process.returncode == 0, 'ColdStart94ScreenRecordFailed')
            record['recordCommandElapsedSeconds'] = round(time.monotonic() - began, 6)
        size = candidate.owner.adb('shell', 'stat', '-c', '%s', remote, timeout=30)
        need(re.fullmatch(r'[0-9]+', size) is not None and 1024 <= int(size) <= MAXIMUM_VIDEO_BYTES,
             'ColdStart94BoundedRemoteVideoRequired')
        remote_hash = candidate.owner.adb('shell', 'sha256sum', remote, timeout=30)
        need(re.fullmatch(r'[0-9a-f]{64}\s+' + re.escape(remote), remote_hash) is not None,
             'ColdStart94RemoteVideoHashInvalid')
        candidate.owner.adb('pull', remote, video, timeout=120)
        need(video.is_file() and video.stat().st_size == int(size) and digest(video) == remote_hash.split()[0],
             'ColdStart94PulledOriginalVideoMismatch')
        record['privateOriginalVideo'] = bound(video)
        record['derivedReviewImages'] = extract_frames(video, private, api)
        record['remoteVideoSHA256'] = remote_hash.split()[0]
        foreground_unlocked(candidate)
        owner_after = candidate.owner_snapshot()
        candidate_after = candidate.idle(initialized=True)
        api.save(directory / 'OwnerAfter.json', owner_after)
        api.save(directory / 'CandidateAfter.json', candidate_after)
        need(api.stable(owner_after) == api.stable(owner_before), 'ColdStart94OwnerChangedDuringRecording')
        need(api.stable(candidate_after) == api.stable(candidate_before), 'ColdStart94CandidateStateChangedDuringColdStart')
        record.update(status='RECORDED_CANDIDATE_COLD_START94_REQUIRES_VISUAL_REVIEW', ownerDataUnchanged=True,
                      candidateDataUnchanged=True, finalCandidateMarkers=candidate.pending_markers(),
                      rootVisualReviewCompleted=False, splashAbsenceAutomaticallyCertified=False)
    except Exception as error:
        record.update(status='FAIL_ISOLATED_CANDIDATE_COLD_START94', **safe_failure(error))
    finally:
        if process and process.poll() is None:
            # Only our host adb screenrecord process; remote recording has a20s cap.
            process.kill()
            try:
                process.wait(timeout=10)
            except Exception:
                record['screenrecordHostTerminationUnconfirmed'] = True
        try:
            record['sourcesAfter'] = candidate.source_guard()
            owner_final = candidate.owner_snapshot()
            candidate_final = candidate.idle(initialized=True)
            record['ownerPreservedAtExit'] = api.stable(owner_final) == api.stable(owner_before)
            record['candidatePreservedAtExit'] = api.stable(candidate_final) == api.stable(candidate_before)
            need(record['ownerPreservedAtExit'] and record['candidatePreservedAtExit'], 'ColdStart94DataPreservationAtExitFailed')
            need(candidate.pending_markers() == [], 'ColdStart94FinalCandidateMarkersPresent')
        except Exception as error:
            record.update(status='FAIL_ISOLATED_CANDIDATE_COLD_START94', finalGuardFailure=safe_failure(error))
        record['completedUtc'] = api.phone.utc()
        api.save(directory / 'Recording.json', record)
    return record, directory / 'Recording.json'


def publication_artifacts(record):
    """Complete immutable private inventory; retention is separate from copying."""
    artifacts = [record['privateOriginalVideo']]
    for sample in record['derivedReviewImages']['samples']:
        artifacts.append(sample['contactSheet'])
        artifacts.extend(frame['png'] for frame in sample['frames'])
    need(len(artifacts) == 47 and len({row['path'] for row in artifacts}) == 47,
         'ColdStart94CompletePrivateReviewArtifactSetRequired')
    return artifacts


def selected_publication_artifacts(record):
    """Fixed four reviewable public originals; never publish all44 samples."""
    complete = publication_artifacts(record)
    samples = record['derivedReviewImages']['samples']
    need(len(samples) == 2 and {sample.get('name') for sample in samples} == {'Whole20s_1fps', 'First6s_4fps'},
         'ColdStart94NamedPrivateSamplesRequired')
    whole = next(sample for sample in samples if sample['name'] == 'Whole20s_1fps')
    early = next(sample for sample in samples if sample['name'] == 'First6s_4fps')
    need(len(whole['frames']) == whole.get('frameCount') == 20
         and len(early['frames']) == early.get('frameCount') == 24,
         'ColdStart94CompleteNamedPrivateSamplesRequired')
    final = whole['frames'][-1]
    need(final.get('sampleIndex') == 19 and final.get('nominalVideoSeconds') == 19
         and Path(final['png']['path']).name == 'Frame_020.png', 'ColdStart94FinalRepresentativeFrameRequired')
    result = [record['privateOriginalVideo'], whole['contactSheet'], early['contactSheet'], final['png']]
    need(len({row['path'] for row in result}) == 4 and all(row in complete for row in result),
         'ColdStart94FixedPublicationSelectionRequired')
    return result


def validate_publication(record_path, review_path):
    record_path, review_path = Path(record_path).resolve(), Path(review_path).resolve()
    reject_links(record_path)
    reject_links(review_path)
    need(record_path.is_relative_to(PUBLIC.resolve()) and record_path.name == 'Recording.json'
         and review_path.is_relative_to(PUBLIC.resolve()) and review_path.is_file(), 'ColdStart94ScopedPublicationReviewRequired')
    record = json.loads(record_path.read_text('utf-8-sig'))
    review = json.loads(review_path.read_text('utf-8-sig'))
    need(record.get('status') == 'RECORDED_CANDIDATE_COLD_START94_REQUIRES_VISUAL_REVIEW'
         and record.get('ownerDataUnchanged') is True and record.get('candidateDataUnchanged') is True
         and record.get('ownerPreservedAtExit') is True and record.get('candidatePreservedAtExit') is True,
         'ColdStart94SuccessfulPreservedRecordingRequired')
    private = publication_artifacts(record)
    artifacts = selected_publication_artifacts(record)
    need(review.get('schemaVersion') == 2 and review.get('status') == 'ROOT_REVIEWED_CANDIDATE_STARTUP_PRIVACY94'
         and review.get('reviewer') == 'root' and review.get('recording') == bound(record_path)
         and review.get('approvedForPublication') is True and review.get('noUnrelatedPersonalContent') is True
         and review.get('reviewedArtifacts') == artifacts and review.get('privateArtifactInventory') == private,
         'ColdStart94ExplicitRootPrivacyApprovalRequired')
    token = record.get('captureId', '')
    need(re.fullmatch(r'[0-9a-f]{32}', token) is not None and record_path.parent.name == token,
         'ColdStart94CaptureBindingRequired')
    source_root = (PRIVATE / token).resolve()
    # All47 originals remain hash-validated even though only four are copied.
    for artifact in private:
        source = (ROOT / artifact['path']).resolve()
        reject_links(source)
        need(source.is_relative_to(source_root) and source.is_file() and bound(source) == artifact,
             'ColdStart94PrivateArtifactChangedOrOutsideCapture')
    return record, artifacts, source_root


def publish(record_path, review_path):
    # Host-only copy of exactly reviewed captures; no ADB or Candidate constructor.
    api = helper()
    record, artifacts, source_root = validate_publication(record_path, review_path)
    destination = fresh_path(Path(record_path).resolve().parent / 'Published', PUBLIC)
    destination.mkdir()
    copied = []
    for artifact in artifacts:
        source = ROOT / artifact['path']
        target = destination / source.resolve().relative_to(source_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        need(not target.exists(), 'ColdStart94FreshPublishedArtifactRequired')
        shutil.copyfile(source, target)
        need(digest(target) == artifact['sha256'] and target.stat().st_size == artifact['bytes'],
             'ColdStart94PublishedCopyMismatch')
        copied.append(bound(target))
    private = publication_artifacts(record)
    receipt = {'schemaVersion': 2, 'status': 'PUBLISHED_ROOT_PRIVACY_REVIEWED_CANDIDATE_COLD_START94',
               'utc': api.phone.utc(), 'recording': bound(record_path), 'rootPrivacyReview': bound(review_path),
               'publishedArtifacts': copied, 'runner': bound(Path(__file__)),
               'privateArtifactInventory': private, 'selectedPrivateArtifacts': artifacts,
               'privateArtifactCount': len(private), 'publishedArtifactCount': len(copied),
               'unpublishedPrivateArtifactCount': len(private) - len(copied),
               'selectionPolicy': 'Original video, two contact sheets and final full-resolution representative frame; all47 private artifacts are preserved unchanged.',
               'scope': 'Only the four exact artifacts explicitly reviewed by root for privacy are copied. Remaining43 sampled originals stay private and hash-bound; publication claims no individual full-resolution visual review of all44 frames. Publication does not itself assert splash absence, startup latency, gameplay or release acceptance.'}
    api.save(destination / 'Publication.json', receipt)
    return receipt, destination / 'Publication.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('record', 'publish'))
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--build', type=Path)
    parser.add_argument('--recording', type=Path)
    parser.add_argument('--privacy-review', type=Path)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt':
        parser.error('Explicit root Windows execution required')
    if args.action == 'record' and (not args.build or args.recording or args.privacy_review):
        parser.error('record requires only --build plus --execute')
    if args.action == 'publish' and (args.build or not args.recording or not args.privacy_review):
        parser.error('publish requires only --recording and --privacy-review plus --execute')
    try:
        result, path = record(args.build) if args.action == 'record' else publish(args.recording, args.privacy_review)
        print(json.dumps({'status': result['status'], 'receipt': path.relative_to(ROOT).as_posix(), 'ownerMutation': False}), flush=True)
        return 1 if result['status'].startswith('FAIL_') else 0
    except Exception as error:
        result = {'status': 'FAIL_ROOT_COLD_START94_ACTION', 'action': args.action, **safe_failure(error), 'ownerMutation': False}
        # Safe categories only; no subprocess exception text/selector is printed.
        print(json.dumps(result), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
