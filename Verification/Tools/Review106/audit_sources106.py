"""Seal source/evidence metadata after the exclusive native106 owner finishes.

Reads exact bytes only; never imports Unity/backend code, runs a test, launches
a process or edits Unity inputs. Summary, galleries and native reports belong to
their existing owners. Historical reports and first-epoch patches are retained.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review106'
BASELINE105 = ROOT / 'Verification/Evidence/Review105/TCP/Flow02/MainSources_after.json'
BASELINE106 = ROOT / 'Verification/Tools/Review106/BaselineMain106.json'
BACKEND105 = ROOT / 'Verification/Evidence/Review105/TCP/Flow02/Report.json'
SUPPORT105 = ROOT / 'Verification/Evidence/Review105/SourceDelta105.json'
PRIVATE105 = ROOT / '.verification-cache/Review98/Game'
CHANGED = (
    'Unity/Assets/HeartOfTheRain/M47/Runtime/GameplayHUD.cs',
    'Unity/Assets/HeartOfTheRain/App/Home/Runtime/HomeLayoutEngine.cs',
    'Unity/Assets/HeartOfTheRain/App/Home/Runtime/MainNavigationFeedback.cs',
)
ADDED = tuple(sorted(path + suffix for path in (
    'Unity/Assets/HeartOfTheRain/M47/Runtime/GoalIconLayout106.cs',
    'Unity/Assets/HeartOfTheRain/Verification/Editor/BaselineCapture106.cs',
    'Unity/Assets/HeartOfTheRain/Verification/Editor/GoalOptics106Verification.cs',
    'Unity/Assets/HeartOfTheRain/Verification/Editor/Navigation106Verification.cs',
) for suffix in ('', '.meta')))
GOAL = (
    CHANGED[0], ADDED[0],
    ADDED[0] + '.meta',
    'Unity/Assets/HeartOfTheRain/Verification/Editor/GoalOptics106Verification.cs',
    'Unity/Assets/HeartOfTheRain/Verification/Editor/GoalOptics106Verification.cs.meta',
)
CAPTURE = 'Unity/Assets/HeartOfTheRain/Verification/Editor/BaselineCapture106.cs'


class AuditBlocked(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise AuditBlocked(code)


def load(path):
    with open(disk(path), encoding='utf-8-sig') as stream:
        return json.load(stream)


def disk(path):
    value = str(path.absolute())
    return '\\\\?\\' + value if os.name == 'nt' and not value.startswith('\\\\?\\') else value


def sha(path):
    digest = hashlib.sha256()
    with open(disk(path), 'rb') as stream:
        for data in iter(lambda: stream.read(1_048_576), b''):
            digest.update(data)
    return digest.hexdigest()


def bind(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': os.stat(disk(path)).st_size}


def change(before, after):
    return {'added': sorted(set(after) - set(before)), 'removed': sorted(set(before) - set(after)),
            'changed': sorted(k for k in set(before) & set(after) if before[k] != after[k])}


def current_unity():
    result = {}
    for part in ('Assets', 'Packages', 'ProjectSettings'):
        for folder, _, names in os.walk(disk(ROOT / 'Unity' / part)):
            for name in names:
                path = Path(str(Path(folder) / name).removeprefix('\\\\?\\'))
                result[path.relative_to(ROOT).as_posix()] = {'sha256': sha(path), 'bytes': os.stat(disk(path)).st_size}
    return dict(sorted(result.items()))


def current_backend():
    # Same inventory as the105 proof's Backend/tools/run_tests.source_hashes;
    # no importing its unittest harness or application factory.
    base = ROOT / 'Backend'
    paths = [p for folder in ('hotr_backend', 'tests', 'tools', 'config')
             for p in (base / folder).rglob('*') if p.is_file() and p.suffix in ('.py', '.json')]
    paths += [base / p for p in ('requirements.in', 'requirements.lock', 'README.md', 'Run-Local.ps1')]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def native(tag, *, passed=False, final=None):
    require(re.fullmatch(r'[A-Za-z0-9_]{1,40}', tag), 'invalid_native_tag')
    folder = OUT / 'Native' / tag
    invocation = load(folder / 'Invocation.json')
    before, after = (load(folder / name) for name in ('MainSources_before.json', 'MainSources_after.json'))
    project_before, project_after = (load(folder / name) for name in ('ProjectSources_before.json', 'ProjectSources_after.json'))
    require(before == after and project_before == project_after and before == project_before, 'native_source_epoch_not_preserved')
    report_path = (folder / invocation['nativeReport']).resolve()
    require(report_path.is_relative_to(folder.resolve()), 'native_report_outside_epoch')
    require(sha(report_path) == invocation['nativeReportSHA256'], 'native_report_digest_mismatch')
    report = load(report_path)
    if passed:
        require(invocation['status'] == 'PASS_NATIVE106_INVOCATION' and invocation['exitCode'] == 0
                and invocation['actualEngine'] == '2022.3.62f3' and not invocation.get('unityPidsAfter')
                and invocation.get('mainInputsUnchanged') is True and invocation.get('projectInputsUnchanged') is True,
                'required_native_invocation_not_passed')
        require(report.get('status') == invocation['expectedNativeStatus'] and report['status'].startswith('PASS_')
                and not any(report.get(k) for k in ('error', 'errors', 'failed', 'failures')), 'required_native_report_not_passed')
    if final is not None:
        require(after['files'] == final, 'required_native_proof_not_final_source')
    evidence = {'tag': tag, 'entry': invocation['entry'], 'startedUtc': invocation['startedUtc'],
                'invocationStatus': invocation['status'], 'nativeStatus': report.get('status'),
                'checks': invocation.get('checks'), 'invocation': bind(folder / 'Invocation.json'),
                'report': bind(report_path), 'manifest': bind(folder / 'MainSources_after.json'),
                'inputCount': after['inputCount'], 'withinRunSourcesPreserved': True}
    return evidence, after['files'], report


def exclusive(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def retain(path):
    if not path.exists():
        return None
    target = OUT / 'RetainedSources' / (path.stem + '_before_final_audit' + path.suffix)
    raw = path.read_bytes()
    if target.exists():
        require(target.read_bytes() == raw, 'retained_metadata_name_already_owned')
    else:
        exclusive(target, raw)
    return bind(target)


def replacement(path, raw):
    temporary = path.with_name(path.name + '.audit106.tmp')
    exclusive(temporary, raw)
    os.replace(temporary, path)


def ending_counts(raw):
    crlf, lf, bare = raw.count(b'\r\n'), raw.count(b'\n'), raw.count(b'\r') - raw.count(b'\r\n')
    style = 'CRLF' if crlf == lf else 'LF' if crlf == 0 else 'mixed'
    return {'bytes': len(raw), 'CRLF': crlf, 'LF': lf, 'bareCR': bare, 'style': style,
            'utf8Bom': raw.startswith(b'\xef\xbb\xbf')}


def patch_and_endings(baseline, final):
    patch, rows = [], []
    for relative in CHANGED:
        old = PRIVATE105 / relative.removeprefix('Unity/')
        new = ROOT / relative
        require(sha(old) == baseline[relative]['sha256'] and old.stat().st_size == baseline[relative]['bytes'],
                'private_copy_not_exact105')
        require(sha(new) == final[relative]['sha256'], 'current_source_changed_before_patch')
        a, b = old.read_bytes(), new.read_bytes()
        lines_a = a.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n').splitlines(keepends=True)
        lines_b = b.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n').splitlines(keepends=True)
        patch.extend(difflib.unified_diff(lines_a, lines_b, fromfile=relative + ' (exact105)',
                                          tofile=relative + ' (final106)'))
        before, after = ending_counts(a), ending_counts(b)
        rows.append({'path': relative, 'exact105BytesRecoveredReadOnly': True,
                     'private105': bind(old), 'baselineSHA256': baseline[relative]['sha256'], 'finalSHA256': final[relative]['sha256'],
                     'oldBytes': before['bytes'], 'newBytes': after['bytes'], 'oldCRLF': before['CRLF'], 'oldLF': before['LF'],
                     'newCRLF': after['CRLF'], 'newLF': after['LF'], 'old': before, 'new': after,
                     'lineEndingConventionPreserved': before['style'] == after['style']
                     and before['bareCR'] == after['bareCR'] and before['utf8Bom'] == after['utf8Bom']})
    helper = 'Unity/Assets/HeartOfTheRain/M47/Runtime/GoalIconLayout106.cs'
    require(sha(ROOT / helper) == final[helper]['sha256'], 'helper_changed_before_patch')
    lines = (ROOT / helper).read_text(encoding='utf-8-sig').replace('\r\n', '\n').splitlines(keepends=True)
    patch.extend(difflib.unified_diff([], lines, fromfile='/dev/null', tofile=helper + ' (added106)'))
    return ''.join(patch).encode('utf-8'), rows


def seal(args):
    baseline = load(BASELINE105)
    require(baseline == load(BASELINE106) and baseline['inputCount'] == 5482, 'baseline105_not_exact5482')
    before = baseline['files']
    final_record = OUT / 'Native' / args.after / 'MainSources_after.json'
    final = load(final_record)['files']
    require(len(final) == 5490 and current_unity() == final, 'final106_not_exact_current5490')
    require(change(before, final) == {'added': list(ADDED), 'removed': [], 'changed': sorted(CHANGED)},
            'unexpected106_unity_delta')
    required = {}
    for role, tag in (('navigation', args.nav), ('after', args.after), ('general', args.general), ('backdrop', args.backdrop)):
        required[role], _, _ = native(tag, passed=True, final=final)
    goal, goal_sources, _ = native('GoalMain03', passed=True)
    require(all(goal_sources[p] == final[p] for p in GOAL), 'goal_inputs_changed_after_goal_suite')
    prior, prior_sources, _ = native('BeforeMain01', passed=True)
    require(prior_sources[CAPTURE] == final[CAPTURE] and prior_sources[CAPTURE + '.meta'] == final[CAPTURE + '.meta'],
            'capture_fixture_changed_before_after')
    epochs = []
    for path in (OUT / 'Native').glob('*/Invocation.json'):
        entry, files, _ = native(path.parent.name)
        entry['deltaToFinal'] = change(files, final)
        epochs.append(entry)
    epochs.sort(key=lambda value: value['startedUtc'])
    failed = [value['tag'] for value in epochs if not value['invocationStatus'].startswith('PASS_')]
    require(all(tag in failed for tag in ('GoalMain01', 'GoalMain02', *(f'NavMain{i:02}' for i in range(1, 7)))),
            'historical_failed_run_missing')
    backend_proof = load(BACKEND105)
    backend_before, backend_after = backend_proof['sourceSHA256After'], current_backend()
    require(len(backend_before) == 105 and backend_before == backend_after, 'backend105_inputs_changed')
    for support in load(SUPPORT105)['supplementalSupport']:
        require(sha(ROOT / support['path']) == support['sha256'], 'backend105_support_changed')
    patch, endings = patch_and_endings(before, final)
    require(all(row['lineEndingConventionPreserved'] for row in endings), 'existing_line_ending_convention_changed')
    require(current_unity() == final and current_backend() == backend_after, 'source_changed_during_audit')
    final_out = OUT / 'SourceDelta106.json'
    require(not final_out.exists(), 'preserve_existing_sealed_audit')
    retained_metadata = [value for value in (retain(OUT / 'SourceChanges106.patch'), retain(OUT / 'LineEndings106.json')) if value]
    replacement(OUT / 'SourceChanges106.patch', patch)
    replacement(OUT / 'LineEndings106.json', (json.dumps(endings, indent=2) + '\n').encode('utf-8'))
    protected = [p for p in before if p not in CHANGED]
    metas = [p for p in before if p.endswith('.meta')]
    settings = [p for p in before if p.startswith(('Unity/Packages/', 'Unity/ProjectSettings/'))]
    gameplay = [p for p in before if p.startswith(('Unity/Assets/HeartOfTheRain/M46/', 'Unity/Assets/HeartOfTheRain/M48/'))
                or p.startswith('Unity/Assets/HeartOfTheRain/M47/Runtime/') and p != CHANGED[0]]
    result = {'schemaVersion': 1, 'status': 'VERIFIED_UI106_SOURCE_DELTA', 'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'auditTool': bind(Path(__file__)), 'baseline105': bind(BASELINE105), 'baseline106Crosscheck': bind(BASELINE106),
              'final106': bind(final_record), 'baselineUnityInputs': 5482, 'finalUnityInputs': 5490,
              'unity': change(before, final), 'allExistingExceptThreePreserved': all(before[p] == final[p] for p in protected),
              'protectedExistingCount': len(protected), 'allExistingMetaPreserved': all(before[p] == final[p] for p in metas),
              'existingMetaCount': len(metas), 'packagesAndProjectSettingsPreserved': all(before[p] == final[p] for p in settings),
              'packageAndSettingsCount': len(settings), 'gameplayAndLevelsExceptHUDPreserved': all(before[p] == final[p] for p in gameplay),
              'gameplayScopeCount': len(gameplay), 'backend105Proof': bind(BACKEND105), 'backendInputCount': len(backend_before),
              'allBackend105InputsPreserved': True, 'backendDelta': change(backend_before, backend_after),
              'backendTestsRerun': False, 'backendServiceOrWorkerRun': False,
              'finalNativeProofs': required, 'earlierGoalProof': goal,
              'goalRuntimeAndFixtureStillExactFinal': True, 'wholeGoalSuiteWasRerunAfterNavOnlyEdits': False,
              'goalEpochDeltaToFinal': change(goal_sources, final), 'beforeProof': prior, 'beforeAfterCaptureFixtureExact': True,
              'nativeEpochs': epochs, 'historicalFailedRunsRetained': failed,
              'retainedSourceArtifacts': [bind(p) for p in sorted((OUT / 'RetainedSources').iterdir()) if p.is_file()],
              'previousRootMetadataRetained': retained_metadata, 'sourcePatch': bind(OUT / 'SourceChanges106.patch'),
              'patchRuntimeFiles': [*CHANGED, 'Unity/Assets/HeartOfTheRain/M47/Runtime/GoalIconLayout106.cs'],
              'lineEndings': bind(OUT / 'LineEndings106.json'),
              'scope': 'Source-byte and existing evidence binding only. Exactly3 existing Unity UI scripts plus8 additions; all other105 Unity inputs and105 backend inputs preserved. Earlier goal and failed source epochs remain distinct from final navigation/After/general/backdrop proofs. No tests, Unity, compiler, service, process control, APK or device action is performed by this audit.'}
    exclusive(final_out, (json.dumps(result, indent=2) + '\n').encode('utf-8'))
    return {'status': result['status'], 'report': final_out.relative_to(ROOT).as_posix(), 'sha256': sha(final_out)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', action='store_true')
    for name in ('nav', 'after', 'general', 'backdrop'):
        parser.add_argument('--' + name)
    args = parser.parse_args()
    if not args.seal:
        print(json.dumps({'status': 'PREPARED_SOURCE_AUDIT106', 'sealed': False, 'testsRun': False}))
        return 0
    try:
        require(all(getattr(args, name) for name in ('nav', 'after', 'general', 'backdrop')), 'final_native_tags_required')
        result = seal(args)
    except AuditBlocked as error:
        print(json.dumps({'status': 'BLOCKED_SOURCE_AUDIT106', 'code': str(error), 'sealed': False}))
        return 1
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({'status': 'BLOCKED_SOURCE_AUDIT106', 'code': 'source_audit_inputs_unavailable', 'sealed': False}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
