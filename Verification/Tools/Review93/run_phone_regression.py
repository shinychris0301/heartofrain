"""Explicit root-only current APK transient regression; no device work on import.

Run after the accepted sixth-link install, with HOTR_PHYSICAL_SERIAL supplied
privately. The dedicated marker is audited here; Phone93's general marker
allowlist remains unchanged. No uninstall, data clear or ordinary game action.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import time
import uuid

import phone
import phone_regression_proof as proof

ROOT, OUT = phone.ROOT, phone.EVIDENCE
MARKER = 'HOTR_RunRegression'
SELECTED = (
    ('Gameplay HUD', ('Gameplay_English_HUD.png',)),
    ('Rocket effect', ('Power_4_Effect_0.png', 'Power_4_Effect_1.png', 'Power_4_Effect_2.png')),
    ('Stacked obstacle refill', ('Stacked_Stones_Diagonal_0.png', 'Stacked_Stones_Diagonal_1.png', 'Stacked_Stones_Diagonal_2.png')),
    ('Chapter completion Home', ('Home_Reward_L50.png',)),
)


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def load_source_module():
    spec = importlib.util.spec_from_file_location('hotr93_physical_source_inventory', ROOT / 'Verification/Tools/Ads85/run_ads85_native.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def matching_build(wrapper_path, source_path, manifest, reader):
    wrapper_path, source_path = Path(wrapper_path).resolve(), Path(source_path).resolve()
    proof.need(wrapper_path.is_relative_to((OUT / 'Builds').resolve()) and source_path == wrapper_path.parent / 'FrozenSources.json', 'Regression93CurrentBuildSourcePathRequired')
    wrapper = proof.read(wrapper_path)
    invocation_path = (ROOT / wrapper['invocation']).resolve()
    proof.need(invocation_path == wrapper_path.parent / 'Invocation.json'
               and phone.sha(invocation_path) == wrapper['invocationSHA256']
               and wrapper.get('status') == 'PASS_INTERNAL_ANDROID_BUILDS93', 'Regression93CompletedBuildWrapperRequired')
    invocation = proof.read(invocation_path)
    proof.need(invocation.get('status') == 'PASS_SDK_FREE_INTERNAL_ANDROID_BUILDS85'
               and invocation.get('sourceSHA256') == phone.sha(source_path)
               and proof.read(source_path) == manifest, 'Regression93CompletedBuildSourcesRequired')
    row = next((row for row in invocation.get('runs', []) if row.get('build') == 'Development'), {})
    proof.need(row.get('status') == 'PASS_INTERNAL_BUILD85' and row.get('apk') == phone.public_binding(reader.apk), 'Regression93ExactDevelopmentBuildRequired')
    return {'wrapper': phone.public_binding(wrapper_path), 'invocation': phone.public_binding(invocation_path), 'sourceManifest': phone.public_binding(source_path)}


def start_regression(reader, folder):
    """One audited marker launch on an idle owner; no fallback or replacement."""
    reader.assert_installed()
    before = reader.require_idle()
    if reader.pending_markers():
        raise RuntimeError('PendingDevelopmentProbeRequestPreserved')
    reader.adb('shell', 'am', 'force-stop', phone.PACKAGE)
    proof.need(not reader.adb('shell', 'pidof', phone.PACKAGE, check=False), 'Regression93AppDidNotStop')
    stopped = reader.require_idle()
    proof.need(proof.ordinary(stopped, reader.target['candidateApkSHA256']) == proof.ordinary(before, reader.target['candidateApkSHA256']), 'Regression93OwnerDataChangedBeforeMarker')
    proof.need(not reader.pending_markers(), 'PendingDevelopmentProbeRequestPreserved')
    private = ROOT / '.verification-cache/Review93/RegressionMarkers' / folder.name / MARKER
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text(phone.utc(), encoding='ascii')
    reader.adb('shell', 'mkdir', '-p', reader.base)
    reader.adb('push', private, reader.base + '/' + MARKER)
    began = datetime.now(timezone.utc)
    reader.launch()
    return began


def frame_names(report):
    names = report.get('frames', [])
    proof.need(isinstance(names, list) and names and len(names) <= 1000 and len(names) == len(set(names))
               and all(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_-]+\.png', name) for name in names), 'Regression93DeclaredFramesInvalid')
    return names


def collect(reader, folder, report, began):
    """Hash every declared current image remotely; download only four originals."""
    remote = reader.base + '/Regression'
    names = frame_names(report)
    raw_before = reader.adb('exec-out', 'cat', remote + '/Regression.json', binary=True)
    proof.need(json.loads(raw_before) == report, 'Regression93CompletedReportChangedBeforeCollection')
    native = folder / 'Native'
    native.mkdir(exist_ok=False)
    (native / 'Regression.json').write_bytes(raw_before)
    raw_atlas = reader.adb('exec-out', 'cat', remote + '/M70_Device.json', binary=True)
    (native / 'M70_Device.json').write_bytes(raw_atlas)
    atlas = json.loads(raw_atlas)
    proof.need(proof.when(atlas['utc']) >= began, 'Regression93StaleAtlasReportRefused')
    all_paths = reader.adb('shell', 'find', remote, '-type', 'f').splitlines()
    proof.need(len(all_paths) <= 1500 and all(path.startswith(remote + '/') for path in all_paths), 'Regression93RemoteInventoryOutsideScope')
    actual = {path.removeprefix(remote + '/') for path in all_paths}
    proof.need(set(names) <= actual, 'Regression93DeclaredNativeFrameMissing')
    unlisted = actual - set(names) - {'Regression.json', 'M70_Device.json'}
    write(folder / 'RemoteInventory.json', {'declaredPngCount': len(names), 'remoteFileCount': len(all_paths),
        'excludedUnlistedSafeGeneratedPngs': sorted(name for name in unlisted if re.fullmatch(r'[A-Za-z0-9_-]+\.png', name)),
        'excludedOtherFileCount': sum(not re.fullmatch(r'[A-Za-z0-9_-]+\.png', name) for name in unlisted),
        'scope': 'Old undeclared outputs are never treated as current, deleted or downloaded. Only fresh report-declared filenames enter the current inventory.'})
    selected = {}
    for label, candidates in SELECTED:
        found = next((name for name in candidates if name in names), None)
        if found is not None:
            selected[found] = label
    hashes, sizes = {}, {}
    for offset in range(0, len(names), 32):
        paths = [remote + '/' + name for name in names[offset:offset + 32]]
        for line in reader.adb('shell', 'sha256sum', *paths).splitlines():
            match = re.fullmatch(r'([0-9a-fA-F]{64})\s+(.+)', line)
            proof.need(match is not None and match.group(2) in paths, 'Regression93RemoteImageHashInvalid')
            hashes[match.group(2).removeprefix(remote + '/')] = match.group(1).lower()
        for line in reader.adb('shell', 'stat', '-c', '%s:%n', *paths).splitlines():
            match = re.fullmatch(r'([0-9]+):(.+)', line)
            proof.need(match is not None and match.group(2) in paths, 'Regression93RemoteImageSizeInvalid')
            sizes[match.group(2).removeprefix(remote + '/')] = int(match.group(1))
    proof.need(set(hashes) == set(sizes) == set(names), 'Regression93RemoteMetadataIncomplete')
    rows = []
    for name in sorted(names):
        retained = name in selected
        if retained:
            data = reader.adb('exec-out', 'cat', remote + '/' + name, binary=True)
            destination = native / name
            destination.write_bytes(data)
            proof.need(phone.sha(destination) == hashes[name] and len(data) == sizes[name]
                       and phone.validate_png(data) == (720, 1600), 'Regression93RetainedNativeFrameChanged')
        rows.append({'file': name, 'sha256': hashes[name], 'bytes': sizes[name], 'retained': retained,
                     'retainedEvidence': (native / name).relative_to(ROOT).as_posix() if retained else None,
                     'selection': selected.get(name)})
    write(folder / 'CaptureInventory.json', {'schemaVersion': 1, 'checkpoint': 93, 'status': 'RECORDED_NATIVE_REGRESSION_CAPTURE_RETENTION93',
        'capturedPngCount': len(rows), 'retainedPngCount': len(selected), 'files': rows,
        'scope': 'All fresh report-declared native camera capture hashes/sizes are recorded. Four representative originals are retained; others remain app-local and are not portable repository images. These are offscreen native camera/UGUI captures, not OS screenshots or visual approval.'})
    proof.need(reader.adb('exec-out', 'cat', remote + '/Regression.json', binary=True) == raw_before, 'Regression93CompletedReportChangedDuringCollection')
    return {'nativeReport': phone.public_binding(native / 'Regression.json'), 'atlasReport': phone.public_binding(native / 'M70_Device.json'),
            'captureInventory': phone.public_binding(folder / 'CaptureInventory.json'), 'remoteInventory': phone.public_binding(folder / 'RemoteInventory.json')}


def run(reader, source_path, builds):
    source_module = load_source_module()
    frozen = source_module.freeze()
    build = matching_build(builds, source_path, frozen, reader)
    reader.assert_installed()
    before = reader.require_idle()
    folder = reader.out / 'Regression' / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'Sources_before.json', frozen)
    write(folder / 'OrdinaryBefore.json', before)
    record = {'schemaVersion': 1, 'checkpoint': 93, 'status': 'RUNNING', 'startedUtc': phone.utc(),
        'runner': phone.public_binding(Path(__file__)), 'phoneHelper': phone.public_binding(Path(phone.__file__)),
        'proofHelper': phone.public_binding(Path(proof.__file__)), 'target': phone.public_binding(reader.out / 'Target.json'),
        'apk': phone.public_binding(reader.apk), 'sourceManifest': phone.public_binding(folder / 'Sources_before.json'),
        'matchingBuild': build, 'ordinaryBefore': phone.public_binding(folder / 'OrdinaryBefore.json'),
        'historicalCheckCountForComparisonOnly': 1716,
        'scope': 'Actual current SDK-free APK on the authorized phone. Explicit opt-in native transient memory-profile/settings fixture with accelerated programmatic actions across50 authored boards,408 actions and354 clips. No human50-level wins, physical swipe acceptance, ordinary saved rewards, hosted services, genuine provider commerce/ads, or whole-game smoothness acceptance.'}
    write(folder / 'Invocation.json', record)
    try:
        began = start_regression(reader, folder)
        record['nativeLaunchUtc'] = began.isoformat()
        write(folder / 'Invocation.json', record)
        deadline = time.monotonic() + 2100
        while time.monotonic() < deadline:
            raw = reader.adb('exec-out', 'cat', reader.base + '/Regression/Regression.json', binary=True, check=False)
            try:
                report = json.loads(raw)
                fresh = isinstance(report, dict) and proof.when(report.get('utc', '')) >= began
            except (ValueError, TypeError, AttributeError, RuntimeError):
                report, fresh = {}, False
            if fresh:
                (folder / 'Latest.json').write_bytes(raw)
                print(json.dumps({key: report.get(key) for key in ('status', 'checks', 'boards', 'actions', 'clips')}), flush=True)
                if report.get('status') != 'RUNNING':
                    record.update(nativeStatus=report.get('status'), checks=report.get('checks'), boards=report.get('boards'),
                                  actions=report.get('actions'), clips=report.get('clips'), failures=report.get('failures'))
                    record.update(collect(reader, folder, report, began))
                    proof.native_scope(report)
                    proof.need(all(any(name in report['frames'] for name in choices) for _, choices in SELECTED), 'Regression93FourRepresentativeGroupsMissing')
                    record['status'] = 'PASS_PHYSICAL_TRANSIENT_REGRESSION93'
                    break
            time.sleep(10)
        else:
            raise TimeoutError('Regression93HostDeadline')
    except Exception as error:
        record.update(status='FAIL_PHYSICAL_TRANSIENT_REGRESSION93', failureType=type(error).__name__)
        if isinstance(error, (RuntimeError, TimeoutError)) and re.fullmatch('[A-Za-z0-9]+', str(error)):
            record['failureCategory'] = str(error)
    finally:
        try:
            record['fixtureAppLog'] = reader.app_log('Regression/' + folder.name + '/Fixture_Runtime.log')
        except Exception as error:
            record.update(status='FAIL_PHYSICAL_TRANSIENT_REGRESSION93', fixtureLogFailureType=type(error).__name__)
        try:
            after = reader.require_idle()
            write(folder / 'OrdinaryAfter.json', after)
            record['ordinaryAfter'] = phone.public_binding(folder / 'OrdinaryAfter.json')
            record['ordinaryDataUnchanged'] = proof.ordinary(before, reader.target['candidateApkSHA256']) == proof.ordinary(after, reader.target['candidateApkSHA256'])
            proof.need(record['ordinaryDataUnchanged'], 'Regression93OwnerDataChangedNoMoreMutations')
            record['normalRelaunch'] = reader.finish_probe()
            final = reader.require_idle()
            write(folder / 'OrdinaryAfterNormalRelaunch.json', final)
            record['ordinaryAfterNormalRelaunch'] = phone.public_binding(folder / 'OrdinaryAfterNormalRelaunch.json')
            record['ordinaryDataUnchangedAfterNormalRelaunch'] = proof.ordinary(before, reader.target['candidateApkSHA256']) == proof.ordinary(final, reader.target['candidateApkSHA256'])
            proof.need(record['ordinaryDataUnchangedAfterNormalRelaunch'], 'Regression93OwnerDataChangedAfterRelaunch')
            record['finalMarkers'] = reader.pending_markers()
            proof.need(not record['finalMarkers'], 'Regression93PendingProbeMarker')
        except Exception as error:
            record.update(status='BLOCKED_PHYSICAL_REGRESSION93_PRESERVATION', preservationFailureType=type(error).__name__)
        after_source = source_module.freeze()
        write(folder / 'Sources_after.json', after_source)
        record.update(sourcesAfter=phone.public_binding(folder / 'Sources_after.json'), inputsUnchanged=after_source == frozen, finishedUtc=phone.utc())
        if not record['inputsUnchanged']:
            record['status'] = 'FAIL_PHYSICAL_TRANSIENT_REGRESSION93'
        write(folder / 'Invocation.json', record)
        if record['status'] == 'PASS_PHYSICAL_TRANSIENT_REGRESSION93':
            try:
                proof.verify_regression(folder / 'Invocation.json', frozen, dict(record['apk'], development=True))
                record['proofVerified'] = True
            except Exception as error:
                record.update(status='FAIL_PHYSICAL_TRANSIENT_REGRESSION93', proofFailureType=type(error).__name__)
                if isinstance(error, RuntimeError) and re.fullmatch('[A-Za-z0-9]+', str(error)):
                    record['proofFailureCategory'] = str(error)
            write(folder / 'Invocation.json', record)
    return folder, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--phone', type=Path, required=True)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--builds', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt':
        parser.error('Explicit root Windows device execution required')
    reader = phone.Phone(args.phone)
    folder, report = run(reader, args.sources, args.builds)
    print(json.dumps({'status': report['status'], 'invocation': (folder / 'Invocation.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if report['status'] == 'PASS_PHYSICAL_TRANSIENT_REGRESSION93' else 1


if __name__ == '__main__':
    raise SystemExit(main())
