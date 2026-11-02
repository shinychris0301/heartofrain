"""Read-only proof of the sixth owner-phone update; never dispatch ADB."""
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import re

_spec = importlib.util.spec_from_file_location('hotr_review93_phone_proof_reader', Path(__file__).with_name('phone.py'))
phone = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(phone)
ROOT = phone.ROOT
OUT = phone.EVIDENCE
SELECTED = r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException|DllNotFoundException'


def need(value, code):
    if not value:
        raise RuntimeError(code)


def read(path):
    return phone._read_record(path)


def binding(path):
    return phone.public_binding(path)


def when(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def snapshot(value, apk):
    need(value.get('installedSHA256') == apk and value.get('activeAttempts') == 0
         and value.get('profiles') and value.get('preferences') and value.get('profileSummaries'), 'Phone93IdleSavedSnapshotRequired')
    need(all(row.get('activeAttempts') == 0 for row in value['profileSummaries']), 'Phone93ActiveSummaryRefused')
    return {key: value[key] for key in ('profiles', 'preferences', 'profileSummaries')}


def verify_phone(directory, current_manifest, expected_development_apk):
    """Require actual scoped phone receipts plus explicit root visual review.

    This function only verifies existing files. A successful return does not
    execute a device test or imply hosted service/payment/performance acceptance.
    """
    directory = Path(directory).resolve()
    need(directory.is_relative_to((OUT / 'Phone').resolve()), 'Phone93EvidenceDirectoryRequired')
    target_path = directory / 'Target.json'
    target = read(target_path)
    chain = phone.validate_upgrade_chain(target_path)
    need(target.get('authorization') == 'OWNER_REQUESTED_REVIEW93' and target.get('upgradeChainDepth') == 6
         and chain['depth'] == 6 and len(chain['links']) == 6
         and all(row.get('installation') and row.get('before') for row in chain['links']), 'Phone93CompleteSixthLinkRequired')
    expected = expected_development_apk
    need(expected.get('development') is True and target.get('candidateApkSHA256') == expected.get('sha256')
         and target.get('candidateApk') == expected.get('path'), 'Phone93CurrentDevelopmentApkRequired')
    apk = (ROOT / expected['path']).resolve()
    need(apk.is_relative_to((ROOT / 'Unity/Builds').resolve()) and apk.is_file()
         and phone.sha(apk) == expected['sha256'] and apk.stat().st_size == expected['bytes'], 'Phone93CurrentApkBytesChanged')
    install = read(directory / 'Installation.json')
    baseline = snapshot(read(directory / 'Install_Before.json'), target['baselineInstalledSHA256'])
    need(install.get('status') == 'PASS_SAVE_PRESERVING_REPLACEMENT'
         and snapshot(install['after'], expected['sha256']) == baseline, 'Phone93InstallationDidNotPreserveOwner')
    snapshots = [directory / name for name in ('OrdinaryBefore.json', 'OrdinaryAfter.json', 'OrdinaryAfterRelaunch.json')]
    for path in snapshots:
        need(snapshot(read(path), expected['sha256']) == baseline, 'Phone93OrdinaryDataChanged:' + path.name)
    source_path = directory / 'SourceManifest.json'
    source = read(source_path)
    need(source.get('inputCount') == current_manifest.get('inputCount') and source.get('files') == current_manifest.get('files'), 'Phone93SourcesNotCurrent')
    need(read(directory / 'FinalMarkerState.json') == {'pendingOptInMarkers': []}, 'Phone93PendingProbeMarker')
    relaunch = read(directory / 'Relaunch.json')
    need(re.search(r'(?m)^Status:\s*ok\s*$', relaunch.get('launchResult', ''))
         and relaunch.get('fixedObservationWaitSeconds') == 8, 'Phone93OrdinaryRelaunchRequired')
    log_review = read(directory / 'Log_Review.json')
    need(re.fullmatch(r'\d+', str(log_review.get('pid', ''))) and log_review.get('log') == 'Runtime.log', 'Phone93ScopedLogRequired')
    log_path = directory / 'Runtime.log'
    need(phone.sha(log_path) == log_review.get('sha256'), 'Phone93ScopedLogChanged')
    selected_count = len(re.findall(SELECTED, log_path.read_text('utf-8-sig')))
    need(selected_count == 0 and log_review.get('selectedErrorCount') == 0, 'Phone93SelectedRuntimeErrorPresent')
    journal_path = directory / 'UI_Actions.json'
    journal = read(journal_path)
    need(journal.get('status') == 'OBSERVING_UI93_REQUIRES_VISUAL_REVIEW'
         and journal.get('runner') == binding(Path(__file__).with_name('phone_review.py')), 'Phone93UiRunnerChanged')
    actions = journal.get('actions', [])
    need(actions and len({row['name'] for row in actions}) == len(actions)
         and all(row.get('dispatch') == 'ADB_COMPLETED' and when(row['completedUtc']) >= when(row['utc']) for row in actions), 'Phone93IncompleteOrDuplicateUiAction')
    observer_path = directory / 'Observer_Final.json'
    observer = read(observer_path)
    need(when(observer['startedUtc']) >= when(journal['nativeLaunchUtc'])
         and when(observer['lastSampleUtc']) >= when(actions[-1]['completedUtc']), 'Phone93FreshNativeObserverRequired')
    visual_path = directory / 'RootVisualReview.json'
    visual = read(visual_path)
    need(visual.get('status') == 'ROOT_REVIEWED_CURRENT93_PHONE'
         and visual.get('apkSHA256') == expected['sha256'] and visual.get('sourceManifest') == binding(source_path)
         and visual.get('nativeObserver') == binding(observer_path)
         and visual.get('ordinaryDataUnchanged') is True and visual.get('ordinaryDataUnchangedAfterRelaunch') is True
         and visual.get('noActiveAttempt') is True, 'Phone93RootVisualAssessmentRequired')
    cases = visual.get('cases', [])
    need({row.get('name') for row in cases} >= {'Home', 'ShopCoins', 'Profile', 'Teams', 'Settings'}, 'Phone93RequiredVisualCasesMissing')
    captures = []
    home_relaunch = False
    journal_captures = journal.get('captures', [])
    for row in cases:
        need(row.get('passed') is True and row.get('controlsSafe') is True and row.get('scope') and row.get('captures'), 'Phone93VisualCaseNotAccepted')
        for name in row['captures']:
            image = (ROOT / name).resolve()
            need(image.is_relative_to((directory / 'Screens').resolve()) and image.suffix == '.png', 'Phone93ActualCaptureScopeRequired')
            meta_path = image.with_suffix('.json')
            metadata = read(meta_path)
            raw = image.read_bytes()
            width, height = phone.validate_png(raw)
            need(metadata.get('kind') == 'ACTUAL_ANDROID_OS_FRAMEBUFFER'
                 and metadata.get('pngValidation') == 'COMPLETE_CHUNKS_IEND_CRC_AND_DECODE'
                 and metadata.get('sha256') == phone.sha(image) and metadata.get('installedSHA256') == expected['sha256']
                 and metadata.get('png') == image.relative_to(directory).as_posix()
                 and (metadata.get('width'), metadata.get('height')) == (width, height) == (720, 1600)
                 and binding(image) in journal_captures, 'Phone93CaptureProvenanceInvalid')
            captures.append({'image': binding(image), 'metadata': binding(meta_path)})
            if row['name'] == 'Home' and image.name == 'Relaunch_Observed.png':
                home_relaunch = True
    need(home_relaunch, 'Phone93ActualOrdinaryRelaunchHomeRequired')
    return {'status': 'PASS_SCOPED_REVIEW93_OWNER_PHONE', 'currentApkInstalled': True,
            'target': binding(target_path), 'installation': binding(directory / 'Installation.json'),
            'sourceManifest': binding(source_path), 'visualAssessment': binding(visual_path),
            'ordinarySnapshots': [binding(path) for path in snapshots], 'ownerUpgradeChain': chain,
            'nativeObserver': binding(observer_path), 'uiJournal': binding(journal_path), 'cases': cases,
            'captures': captures, 'completion': {name: binding(directory / name) for name in
                ('FinalMarkerState.json', 'Relaunch.json', 'Log_Review.json', 'Runtime.log')},
            'scope': 'Sixth same-owner compatible internal APK replacement, five scoped ordinary local-mode visual surfaces and unchanged profile/preferences through relaunch. Not configured managed services, provider/payment/ads or whole-app/performance certification.'}
