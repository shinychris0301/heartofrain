"""Root-only current88 phone regression or approved twelve continuation cases.

No operation occurs on import. --phone is an existing explicitly authorized
Display88 phone run. The operator must finish ordinary active attempts first.
Native regression uses transient memory profiles and accelerated/programmatic
actions. Its RenderTexture images are not actual full-screen phone proof,
human campaign wins, provider acceptance or performance certification.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


phone_module = load_module('display88_phone_checks_current_helper', HERE / 'phone.py')
source_module = load_module('display88_phone_checks_hash_helper', ROOT / 'Verification/Tools/Ads85/run_ads85_native.py')
Phone, CapturePathPhone = phone_module.Phone, phone_module.CapturePathPhone
sha, utc = phone_module.sha, phone_module.utc


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def when(value):
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('NativeUtcMustIncludeTimezone')
    return result.astimezone(timezone.utc)


def binding(path):
    path = Path(path).resolve()
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def current_build(phone, frozen):
    """Bind this installed APK to an actual completed matching build source map."""
    matches = []
    for wrapper in sorted((phone_module.EVIDENCE / 'Builds').glob('*/Display88_Builds.json')):
        value = json.loads(wrapper.read_text('utf-8-sig'))
        if value.get('status') != 'PASS_INTERNAL_ANDROID_BUILDS88':
            continue
        invocation = (ROOT / value['invocation']).resolve()
        if not invocation.is_relative_to(phone_module.EVIDENCE.resolve()) or sha(invocation) != value.get('invocationSHA256'):
            raise RuntimeError('CurrentBuildInvocationBindingInvalid')
        report = json.loads(invocation.read_text('utf-8-sig'))
        development = next((row for row in report.get('runs', []) if row.get('build') == 'Development'), {})
        if development.get('apk', {}).get('sha256') != phone.target['candidateApkSHA256']:
            continue
        manifest = invocation.parent / 'FrozenSources.json'
        if report.get('status') != 'PASS_SDK_FREE_INTERNAL_ANDROID_BUILDS85' or sha(manifest) != report.get('sourceSHA256'):
            raise RuntimeError('CurrentBuildSourceBindingInvalid')
        if json.loads(manifest.read_text('utf-8-sig')) != frozen:
            raise RuntimeError('InstalledApkDoesNotMatchCurrentUnitySources')
        matches.append((report.get('finishedUtc', ''), wrapper, invocation, manifest))
    if not matches:
        raise RuntimeError('CompletedCurrentApkBuildProofRequired')
    _, wrapper, invocation, manifest = sorted(matches)[-1]
    return {'wrapper': binding(wrapper), 'invocation': binding(invocation), 'sourceManifest': binding(manifest)}


def begin(phone, mode):
    phone.assert_installed()
    phone.assert_no_active_attempt()
    folder = phone.out / ('Regression' if mode == 'regression' else 'NoMoves')
    folder.mkdir(parents=True, exist_ok=False)
    frozen = source_module.freeze()
    build = current_build(phone, frozen)
    write(folder / 'SourceManifest.json', frozen)
    record = {'checkpoint': 88, 'mode': mode, 'status': 'RUNNING', 'startedUtc': utc(),
              'runner': binding(Path(__file__)), 'phoneHelper': binding(HERE / 'phone.py'),
              'sourceManifest': binding(folder / 'SourceManifest.json'), 'inputCount': frozen['inputCount'],
              'apk': binding(phone.apk), 'target': binding(phone.out / 'Target.json'), 'matchingBuild': build}
    return folder, frozen, record


def close_source(folder, frozen, record):
    after = source_module.freeze()
    write(folder / 'Sources_after.json', after)
    record['inputsUnchanged'] = frozen == after
    record['runnerUnchanged'] = sha(Path(__file__)) == record['runner']['sha256']
    record['phoneHelperUnchanged'] = sha(HERE / 'phone.py') == record['phoneHelper']['sha256']
    if not record['inputsUnchanged'] or not record['runnerUnchanged'] or not record['phoneHelperUnchanged']:
        record['status'] = 'FAIL_PHYSICAL88_INPUT_MUTATION'
    record['finishedUtc'] = utc()


def approved_no_moves_module():
    # The unchanged case algorithm imports "phone". Give only that import the
    # current helper; do not modify historical files or another caller's module.
    previous = sys.modules.get('phone')
    sys.modules['phone'] = phone_module
    try:
        return load_module('display88_approved_no_moves_algorithm', ROOT / 'Verification/Tools/Physical87/no_moves.py')
    finally:
        if previous is None:
            sys.modules.pop('phone', None)
        else:
            sys.modules['phone'] = previous


def no_moves(phone):
    folder, frozen, record = begin(phone, 'no-moves')
    record['scope'] = 'Current88 APK on the same authorized physical phone; approved memory-only Continue/Shop fixtures, real Android taps and one swipe. Original twelve-case algorithm remains unchanged. No ordinary account substitution, live purchase, human campaign or performance claim; actual screenshots require separate visual review.'
    algorithm = approved_no_moves_module()
    record['caseAlgorithm'] = binding(ROOT / 'Verification/Tools/Physical87/no_moves.py')
    fixtures, inputs = algorithm.fixtures()
    record.update(fixtureInputs=inputs, cases=[])
    write(folder / 'Summary.json', record)
    try:
        for fixture in fixtures:
            result = algorithm.run_case(phone, fixture, phone.out)
            record['cases'].append(result)
            write(folder / 'Summary.json', record)
            print(json.dumps({'scenario': result['scenario'], 'status': result['status'], 'safeToContinue': result['safeToContinue']}), flush=True)
            if not result['safeToContinue']:
                record['status'] = 'BLOCKED_PHYSICAL_NO_MOVES88_PRESERVATION'
                break
        else:
            record['status'] = 'PASS_PHYSICAL_NO_MOVES88_REQUIRES_VISUAL_REVIEW' if all(row['status'] == 'PASS_PHYSICAL_NO_MOVES_CASE' for row in record['cases']) else 'FAIL_PHYSICAL_NO_MOVES88'
    except Exception as error:
        record.update(status='FAIL_PHYSICAL_NO_MOVES88_RUNNER', failureType=type(error).__name__)
    finally:
        record['actualTaps'] = sum(action['kind'] == 'tap' and action['dispatch'] == 'ADB_COMPLETED' for row in record['cases'] for action in row['inputs'])
        record['actualSwipes'] = sum(action['kind'] == 'swipe' and action['dispatch'] == 'ADB_COMPLETED' for row in record['cases'] for action in row['inputs'])
        close_source(folder, frozen, record)
        write(folder / 'Summary.json', record)
    return record


SELECTED_CAPTURE_GROUPS = (
    ('Russian Home', ('Home_ru.png',)),
    ('Gameplay HUD', ('Gameplay_English_HUD.png',)),
    ('Rocket tutorial', ('FirstStart_Rocket_ru.png',)),
    ('Clear tutorial', ('FirstStart_Clear_ru.png',)),
    ('Rocket effect', ('Power_4_Effect_0.png', 'Power_4_Effect_1.png', 'Power_4_Effect_2.png')),
    ('Orb/Rocket combo', ('Pair_7_4_False_False_Effect_0.png', 'Pair_7_4_False_False_Effect_1.png', 'Pair_7_4_False_False_Effect_2.png')),
    ('Stacked obstacle diagonal fall', ('Stacked_Stones_Diagonal_0.png', 'Stacked_Stones_Diagonal_1.png', 'Stacked_Stones_Diagonal_2.png')),
    ('Exactly900 life-refill offer', ('LifeRefill_Exactly900.png',)),
    ('Full lives after900 coins', ('LifeRefill_Full_After900.png',)),
    ('Dariya finale', ('Finale_Daria.png',)),
    ('City finale', ('Finale_City_Hook.png',)),
    ('Chapter1 completion Home', ('Home_Reward_L50.png',)),
)


def collect_regression(phone, folder, report, cache):
    names = report.get('frames', [])
    if not names or len(names) > 1000 or len(set(names)) != len(names) or any(not re.fullmatch(r'[A-Za-z0-9_-]+\.png', name) for name in names):
        raise RuntimeError('NativeRegressionCaptureInventoryInvalid')
    allowed = set(names) | {'Regression.json', 'M70_Device.json'}
    remote = phone.base + '/Regression'
    remote_paths = phone.adb('shell', 'find', remote, '-type', 'f').splitlines()
    if len(remote_paths) > 1002 or any(not path.startswith(remote + '/') or path.removeprefix(remote + '/') not in allowed for path in remote_paths):
        raise RuntimeError('UnexpectedNativeRegressionFilesPreserved')
    cache.mkdir(parents=True, exist_ok=False)
    phone.adb('pull', remote + '/.', cache)
    if json.loads((cache / 'Regression.json').read_text('utf-8-sig')) != report:
        raise RuntimeError('PulledNativeRegressionReportChanged')
    missing = [name for name in names if not (cache / name).is_file()]
    if missing:
        raise RuntimeError('NativeRegressionCapturesMissingFromPull')
    selected = {}
    for label, candidates in SELECTED_CAPTURE_GROUPS:
        found = next((name for name in candidates if name in names), None)
        if found is None:
            raise RuntimeError('RepresentativeRegressionCaptureMissing')
        selected[found] = label
    native = folder / 'Native'
    native.mkdir()
    for name in ('Regression.json', 'M70_Device.json'):
        shutil.copy2(cache / name, native / name)
    atlas = json.loads((cache / 'M70_Device.json').read_text('utf-8-sig'))
    if atlas.get('status') != 'PASS_NATIVE_M70_DEVICE' or atlas.get('failures'):
        raise RuntimeError('NativeM70DeviceRegressionNotPassed')
    rows = []
    for name in sorted(names):
        source = cache / name
        retained = name in selected
        if retained:
            phone_module.validate_png(source.read_bytes())
            shutil.copy2(source, native / name)
            if sha(source) != sha(native / name):
                raise RuntimeError('RetainedRegressionCaptureChanged')
        rows.append({'file': name, 'sha256': sha(source), 'bytes': source.stat().st_size,
                     'retained': retained, 'retainedEvidence': (native / name).relative_to(ROOT).as_posix() if retained else None,
                     'localCache': source.relative_to(ROOT).as_posix(), 'localCacheAvailableAtCollection': True,
                     'selection': selected.get(name)})
    inventory = {'schemaVersion': 1, 'checkpoint': 88, 'status': 'RECORDED_NATIVE_REGRESSION_CAPTURE_RETENTION88',
                 'capturedPngCount': len(rows), 'retainedPngCount': len(selected), 'files': rows,
                 'scope': 'All native regression PNG hashes are recorded. Twelve representative original files are retained in public evidence; the remaining originals are only in ignored local cache and are not portable repository proof. These offscreen/camera captures do not establish actual OS full-screen acceptance or visual review.'}
    write(folder / 'CaptureInventory.json', inventory)
    return {'nativeReport': binding(native / 'Regression.json'), 'atlasReport': binding(native / 'M70_Device.json'),
            'captureInventory': binding(folder / 'CaptureInventory.json'), 'capturedPngCount': len(rows),
            'retainedPngCount': len(selected), 'localCache': cache.relative_to(ROOT).as_posix()}


def retain_partial_inventory(folder, cache):
    """A failed pull/selection still leaves an honest manifest of local bytes."""
    if not cache.is_dir() or (folder / 'CaptureInventory.json').exists():
        return
    rows = []
    for path in sorted(cache.glob('*.png')):
        if not path.is_file() or path.is_symlink() or not re.fullmatch(r'[A-Za-z0-9_-]+\.png', path.name):
            continue
        retained = folder / 'Native' / path.name
        same = retained.is_file() and sha(retained) == sha(path)
        rows.append({'file': path.name, 'sha256': sha(path), 'bytes': path.stat().st_size, 'retained': same,
                     'retainedEvidence': retained.relative_to(ROOT).as_posix() if same else None,
                     'localCache': path.relative_to(ROOT).as_posix(), 'localCacheAvailableAtCollection': True})
    write(folder / 'CaptureInventory.json', {'schemaVersion': 1, 'checkpoint': 88, 'status': 'PARTIAL_FAILED_REGRESSION_CAPTURE_RETENTION88',
          'capturedPngCount': len(rows), 'retainedPngCount': sum(row['retained'] for row in rows), 'files': rows,
          'scope': 'Only files actually present after the failed collection are listed. Bytes are retained without a complete/decode or visual assertion. Missing native outputs remain missing; unretained files are ignored local cache, not portable repository proof.'})


def regression(phone):
    folder, frozen, record = begin(phone, 'regression')
    record['scope'] = 'Current88 APK on the authorized physical ARM64 phone; existing transient memory-profile/settings regression with programmatic accelerated actions, all50 boards,408 actions and354 clips. Not human campaign wins, natural swipe acceptance, ordinary saved rewards, provider/backend acceptance, whole-game smoothness or actual OS full-screen visual certification.'
    before = phone.snapshot()
    record['ordinaryBefore'] = before
    cache = ROOT / '.verification-cache/Display88' / phone.out.name / 'Regression' / uuid.uuid4().hex
    write(folder / 'Invocation.json', record)
    try:
        began = when(phone.start_marker('HOTR_RunRegression', utc()))
        record['nativeLaunchUtc'] = began.isoformat()
        deadline = time.monotonic() + 2100
        while time.monotonic() < deadline:
            raw = phone.adb('shell', 'cat', phone.base + '/Regression/Regression.json', check=False)
            try:
                report = json.loads(raw)
                fresh = isinstance(report, dict) and when(report.get('utc', '')) >= began
            except (ValueError, TypeError, AttributeError):
                report, fresh = {}, False
            if fresh:
                write(folder / 'Latest.json', report)
                print(json.dumps({key: report.get(key) for key in ('status', 'checks', 'boards', 'actions', 'clips')}), flush=True)
                if report.get('status') != 'RUNNING':
                    record.update(nativeStatus=report.get('status'), checks=report.get('checks'), boards=report.get('boards'),
                                  actions=report.get('actions'), clips=report.get('clips'), failures=report.get('failures'))
                    record['collection'] = collect_regression(phone, folder, report, cache)
                    if report.get('status') != 'PASS_NATIVE_REGRESSION' or report.get('failures') or report.get('unity') != '2022.3.62f3' or report.get('platform') != 'Android':
                        raise RuntimeError('NativeRegressionNotPassed')
                    if report.get('boards') != 50 or report.get('actions') != 408 or report.get('clips') != 354:
                        raise RuntimeError('NativeRegressionCoverageChanged')
                    record['status'] = 'PASS_PHYSICAL_TRANSIENT_REGRESSION88'
                    break
            time.sleep(10)
        else:
            raise TimeoutError('PhysicalRegressionHostDeadline')
    except Exception as error:
        record.update(status='FAIL_PHYSICAL_TRANSIENT_REGRESSION88', failureType=type(error).__name__)
        if isinstance(error, RuntimeError) and re.fullmatch('[A-Za-z0-9]+', str(error)):
            record['failureCategory'] = str(error)
        record['localCacheIfCreated'] = cache.relative_to(ROOT).as_posix() if cache.exists() else None
    finally:
        retain_partial_inventory(folder, cache)
        try:
            record['appLog'] = phone.app_log('Regression/Runtime.log')
        except Exception as error:
            record['appLogFailureType'] = type(error).__name__
        try:
            frame = phone.capture('Regression/Final_OS.png')
            record['finalOsCapture'] = binding(frame)
            record['finalOsCaptureScope'] = 'Actual OS image of a transient fixture state; requires separate human visual assessment.'
        except Exception as error:
            record['finalOsCaptureFailureType'] = type(error).__name__
        try:
            after = phone.snapshot()
            record.update(ordinaryAfter=after, ordinaryDataUnchanged=before == after)
            if before != after:
                raise RuntimeError('OrdinaryDataChangedNoFurtherMutation')
            phone.assert_no_active_attempt()
            record['normalRelaunch'] = phone.finish_probe()
            final = phone.snapshot()
            record.update(ordinaryAfterNormalRelaunch=final, ordinaryDataUnchangedAfterNormalRelaunch=before == final)
            if before != final:
                raise RuntimeError('OrdinaryDataChangedAfterNormalRelaunch')
            phone.assert_no_active_attempt()
        except Exception as error:
            record.update(status='BLOCKED_PHYSICAL_REGRESSION88_PRESERVATION', preservationFailureType=type(error).__name__)
        close_source(folder, frozen, record)
        write(folder / 'Invocation.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phone', type=Path, required=True)
    parser.add_argument('--mode', choices=('regression', 'no-moves'), required=True)
    args = parser.parse_args()
    # CapturePathPhone preserves positive JSON validation metadata while making
    # unchanged historical run_case() receive the PNG Path it expects.
    phone = CapturePathPhone(args.phone)
    result = regression(phone) if args.mode == 'regression' else no_moves(phone)
    print(json.dumps({'status': result['status'], 'phoneRun': phone.out.relative_to(ROOT).as_posix(), 'mode': args.mode}), flush=True)
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
