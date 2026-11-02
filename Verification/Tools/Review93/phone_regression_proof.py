"""Read-only current Android regression receipt checks; never run ADB/tests."""
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re

_spec = importlib.util.spec_from_file_location('hotr93_regression_phone_reader', Path(__file__).with_name('phone.py'))
phone = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(phone)
ROOT, OUT = phone.ROOT, phone.EVIDENCE
EXPECTED_FAMILIES = {'cabinet', 'case', 'crate', 'crystal', 'gate', 'moss', 'pod', 'stone'}


def need(value, code):
    if not value:
        raise RuntimeError(code)


def read(path):
    return phone._read_record(path)


def when(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(result.tzinfo is not None, 'Regression93TimezoneRequired')
    return result


def binding(path):
    return phone.public_binding(path)


def checked(item, inside=OUT):
    path = (ROOT / item['path']).resolve()
    need(path.is_relative_to(Path(inside).resolve()) and path.is_file() and binding(path) == item, 'Regression93BoundArtifactChanged')
    return path


def native_scope(report):
    need(report.get('status') == 'PASS_NATIVE_REGRESSION' and not report.get('failures')
         and report.get('unity') == '2022.3.62f3' and report.get('platform') == 'Android'
         and report.get('boards') == 50 and report.get('actions') == 408 and report.get('clips') == 354
         and report.get('checks', 0) == len(report.get('passed', [])) > 0
         and report.get('labels', 0) > 0 and set(report.get('damageFamilies', [])) == EXPECTED_FAMILIES,
         'Regression93NativeCoverageNotPassed')
    passed = set(report['passed'])
    for level in range(1, 51):
        need('L' + str(level) + ' accepts natural move' in passed, 'Regression93BoardNaturalMoveMissing')
        for tool in range(4):
            need('L' + str(level) + ' tool ' + str(tool) + ' spends one stock' in passed
                 and 'L' + str(level) + ' tool ' + str(tool) + ' preserves moves' in passed,
                 'Regression93BoardToolCoverageMissing')
    for key in ('Practice Match solved through page commands and real animation playback',
                'Practice Rocket solved through page commands and real animation playback',
                'Practice Clear solved through page commands and real animation playback',
                'Exactly 900 coins shows the enabled native refill button and price',
                'Repeated native refill callback charges exactly once',
                'Connected Continue exposes the approved five-move/900-coin offer',
                'Confirmed decline charges exactly one life, no coins, and opens retry pre-level',
                'Celebration completion cannot grant a duplicate reward L50',
                'Celebration returns Home without next-level modal L50'):
        need(key in passed, 'Regression93ExpectedLifecycleCaseMissing')


def ordinary(value, apk):
    need(value.get('installedSHA256') == apk and value.get('activeAttempts') == 0
         and value.get('profiles') and value.get('preferences') and value.get('profileSummaries')
         and all(row.get('activeAttempts') == 0 for row in value['profileSummaries']), 'Regression93IdleOwnerSnapshotRequired')
    return {key: value[key] for key in ('profiles', 'preferences', 'profileSummaries')}


def verify_regression(path, current_manifest, expected_development_apk):
    path = Path(path).resolve()
    need(path.is_relative_to((OUT / 'Phone').resolve()) and path.name == 'Invocation.json', 'Regression93ScopedInvocationRequired')
    record, folder = read(path), path.parent
    need(record.get('status') == 'PASS_PHYSICAL_TRANSIENT_REGRESSION93'
         and record.get('runner') == binding(Path(__file__).with_name('run_phone_regression.py'))
         and record.get('phoneHelper') == binding(Path(__file__).with_name('phone.py'))
         and record.get('proofHelper') == binding(Path(__file__)), 'Regression93InvocationNotAccepted')
    target = read(checked(record['target']))
    chain = phone.validate_upgrade_chain(ROOT / record['target']['path'])
    need(chain['depth'] == 6 and len(chain['links']) == 6, 'Regression93SixthOwnerPhoneRequired')
    apk = expected_development_apk
    need(apk.get('development') is True and record.get('apk') == {key: apk[key] for key in ('path', 'sha256', 'bytes')}
         and target.get('candidateApkSHA256') == apk['sha256'], 'Regression93CurrentApkRequired')
    checked(record['apk'], ROOT / 'Unity/Builds')
    for field in ('sourceManifest', 'sourcesAfter'):
        source = read(checked(record[field], folder))
        need(source.get('files') == current_manifest.get('files') and source.get('inputCount') == current_manifest.get('inputCount'), 'Regression93SourcesNotCurrent')
    build = record['matchingBuild']
    wrapper = read(checked(build['wrapper']))
    invocation = read(checked(build['invocation']))
    need(wrapper.get('status') == 'PASS_INTERNAL_ANDROID_BUILDS93'
         and wrapper.get('invocationSHA256') == build['invocation']['sha256']
         and invocation.get('status') == 'PASS_SDK_FREE_INTERNAL_ANDROID_BUILDS85'
         and invocation.get('sourceSHA256') == build['sourceManifest']['sha256']
         and read(checked(build['sourceManifest'])).get('files') == current_manifest['files'], 'Regression93MatchingBuildMissing')
    need(any(row.get('build') == 'Development' and row.get('status') == 'PASS_INTERNAL_BUILD85'
             and row.get('apk') == record['apk'] for row in invocation['runs']), 'Regression93DevelopmentBuildNotBound')
    native_path = checked(record['nativeReport'], folder)
    report = read(native_path)
    native_scope(report)
    need(record.get('nativeStatus') == report['status'] and record.get('checks') == report['checks']
         and when(report['utc']) >= when(record['nativeLaunchUtc'])
         and target['model'] in report.get('device', '') and (report.get('width'), report.get('height')) == (720, 1600), 'Regression93FreshPhoneNativeReportRequired')
    atlas = read(checked(record['atlasReport'], folder))
    need(atlas.get('status') == 'PASS_NATIVE_M70_DEVICE' and not atlas.get('failures')
         and when(atlas['utc']) >= when(record['nativeLaunchUtc']) and len(atlas.get('textures', [])) == 7
         and len(atlas.get('idleAdvancement', [])) == 3 and all(row.get('passed') is True for row in atlas['idleAdvancement']), 'Regression93FreshAtlasReportRequired')
    inventory = read(checked(record['captureInventory'], folder))
    rows = inventory.get('files', [])
    need(inventory.get('status') == 'RECORDED_NATIVE_REGRESSION_CAPTURE_RETENTION93'
         and len(rows) == len(report['frames']) == inventory.get('capturedPngCount')
         and {row['file'] for row in rows} == set(report['frames']) and len({row['file'] for row in rows}) == len(rows)
         and sum(row.get('retained') is True for row in rows) == inventory.get('retainedPngCount') == 4,
         'Regression93CaptureInventoryIncomplete')
    for row in rows:
        need(re.fullmatch(r'[A-Za-z0-9_-]+\.png', row.get('file', ''))
             and re.fullmatch('[0-9a-f]{64}', row.get('sha256', '')) and row.get('bytes', 0) > 0, 'Regression93CaptureMetadataInvalid')
        if row['retained']:
            image = checked({'path': row['retainedEvidence'], 'sha256': row['sha256'], 'bytes': row['bytes']}, folder)
            need(phone.validate_png(image.read_bytes()) == (720, 1600), 'Regression93NativeImageDimensionsChanged')
        else:
            need(row.get('retainedEvidence') is None, 'Regression93UnretainedImageClaimed')
    baseline = None
    for field in ('ordinaryBefore', 'ordinaryAfter', 'ordinaryAfterNormalRelaunch'):
        snapshot = ordinary(read(checked(record[field], folder)), apk['sha256'])
        if baseline is None:
            baseline = snapshot
        need(snapshot == baseline, 'Regression93OwnerDataChanged')
    need(record.get('ordinaryDataUnchanged') is True and record.get('ordinaryDataUnchangedAfterNormalRelaunch') is True
         and record.get('inputsUnchanged') is True and record.get('finalMarkers') == []
         and re.search(r'(?m)^Status:\s*ok\s*$', record.get('normalRelaunch', {}).get('launchResult', '')), 'Regression93PreservationAndRelaunchRequired')
    return {'invocation': binding(path), 'nativeReport': binding(native_path), 'atlasReport': record['atlasReport'],
            'captureInventory': record['captureInventory'], 'checks': report['checks'], 'boards': 50, 'actions': 408, 'clips': 354,
            'retainedPngCount': 4, 'capturedPngCount': len(rows), 'ordinaryDataPreserved': True,
            'scope': 'Actual current APK on one phone with programmatic accelerated transient fixtures, all authored boards and explicit live local flows. Four original native camera captures require visual review; no human campaign, ordinary saved rewards, configured backend/provider or smoothness certification.'}
