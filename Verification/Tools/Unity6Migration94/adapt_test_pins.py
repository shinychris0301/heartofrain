"""Root opt-in: adapt three exact engine assertions only in the isolated copy."""
import argparse
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'
EVIDENCE = ROOT / 'Verification/Evidence/Unity6Migration94'
VERSION = '6000.6.6f1'
ADAPTATIONS = (
    ('Assets/HeartOfTheRain/Verification/Editor/NativeVerification.cs',
     b'Application.unityVersion == "2022.3.62f3"',
     b'Application.unityVersion == "6000.6.6f1"'),
    ('Assets/HeartOfTheRain/Verification/Editor/Display88Verification.cs',
     b'Application.unityVersion=="2022.3.62f3"',
     b'Application.unityVersion=="6000.6.6f1"'),
    ('Assets/HeartOfTheRain/Verification/Editor/Progress92Verification.cs',
     b'Application.unityVersion=="2022.3.62f3"',
     b'Application.unityVersion=="6000.6.6f1"'),
)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def reject_links(path):
    for node in (path, *path.parents):
        if node.exists():
            info = node.stat()
            if node.is_symlink() or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError('LinkedOrReparsePathRefused')
            if node.is_file() and info.st_nlink != 1:
                raise ValueError('HardLinkedInputRefused')


def exact_project(path):
    path = Path(path)
    reject_links(path)
    if path.resolve() != PROJECT.resolve() or not path.is_dir():
        raise ValueError('ExactApprovedIsolatedProjectRequired')
    if path.resolve() == (ROOT / 'Unity').resolve():
        raise ValueError('MainProjectNeverWritable')
    return path.resolve()


def fresh_output(path):
    path = Path(path)
    reject_links(path)
    resolved = path.resolve()
    if not resolved.is_relative_to(EVIDENCE.resolve()) or resolved == EVIDENCE.resolve() or path.exists():
        raise ValueError('FreshContainedEvidenceRequired')
    if resolved.is_relative_to(PROJECT.resolve()):
        raise ValueError('EvidenceOutsideCandidateRequired')
    return resolved


def prepare_changes(project, baseline):
    changes = []
    for relative, old, new in ADAPTATIONS:
        if not relative.startswith('Assets/HeartOfTheRain/Verification/Editor/') or not relative.endswith('.cs'):
            raise ValueError('TestFilesOnly')
        source = ROOT / 'Unity' / relative
        target = project / relative
        reject_links(source)
        reject_links(target)
        expected = baseline['files']['Unity/' + relative]
        before = target.read_bytes()
        original = source.read_bytes()
        if (sha_bytes(before) != expected['sha256'] or len(before) != expected['bytes']
                or original != before):
            raise ValueError('CandidateTestMustEqualExactApprovedMainBytes')
        if before.count(old) != 1 or old == new or new in before:
            raise ValueError('SingleExactVersionAssertionRequired')
        after = before.replace(old, new, 1)
        if after.replace(new, old, 1) != before:
            raise ValueError('VersionOnlyRoundTripRequired')
        changes.append({'relative': relative, 'target': target, 'before': before, 'after': after})
    return changes


def load_baseline():
    baseline_path = EVIDENCE / 'MainSources_Before.json'
    preparation_path = EVIDENCE / 'Preparation.json'
    baseline = json.loads(baseline_path.read_text('utf-8-sig'))
    preparation = json.loads(preparation_path.read_text('utf-8-sig'))
    if (preparation.get('status') != 'PASS_EXACT_MAIN_COPY94'
            or preparation.get('authorization') != 'USER_APPROVED_ISOLATED_UNITY6_MIGRATION'
            or preparation.get('project') != '.verification-cache/Unity6Migration94/Project'
            or preparation.get('mainManifestSHA256') != sha_bytes(baseline_path.read_bytes())
            or baseline.get('inputCount') != 5407):
        raise ValueError('ApprovedExactMainCopyProofRequired')
    return baseline


def shared():
    spec = importlib.util.spec_from_file_location('migration94_test_pin_source_reader', ROOT / 'Verification/Tools/Ads85/run_ads85_native.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--execute', action='store_true')
    cli.add_argument('--project', type=Path, required=True)
    cli.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    if not args.execute or os.name != 'nt':
        cli.error('Explicit root Windows execution is required')
    project = exact_project(args.project)
    out = fresh_output(args.out)
    baseline = load_baseline()
    api = shared()
    before_main = api.freeze()
    if before_main != baseline:
        raise ValueError('MainInputsMustRemainApprovedBaseline')
    changes = prepare_changes(project, baseline)
    out.mkdir(parents=True, exist_ok=False)
    report = {'schemaVersion': 1, 'status': 'RUNNING_ISOLATED_TEST_PIN_ADAPTATION94',
              'startedUtc': api.utc(), 'project': project.relative_to(ROOT).as_posix(),
              'expectedUnity': VERSION, 'runnerSHA256': sha_bytes(Path(__file__).read_bytes()),
              'scope': 'Three exact test engine-comparison literals in the approved isolated copy only. Substantive assertions, check counts, rendering/gameplay logic, trusted backend worker/pins, original main tests and all meta files are unchanged. Legacy assertion labels and scope strings can still name2022; actual candidate engine evidence must be checked separately.',
              'changes': []}
    api.write(out / 'MainSources_before.json', before_main)
    api.write(out / 'Authorization.json', report)
    try:
        for change in changes:
            relative = change['relative']
            for label in ('before', 'after'):
                archived = out / label / relative
                archived.parent.mkdir(parents=True, exist_ok=True)
                with archived.open('xb') as stream:
                    stream.write(change[label])
            difference = ''.join(difflib.unified_diff(
                change['before'].decode('utf-8-sig').splitlines(keepends=True),
                change['after'].decode('utf-8-sig').splitlines(keepends=True),
                fromfile='before/' + relative, tofile='after/' + relative))
            patch = out / 'diffs' / (Path(relative).name + '.diff')
            patch.parent.mkdir(parents=True, exist_ok=True)
            with patch.open('x', encoding='utf-8', newline='') as stream:
                stream.write(difference)
            target = change['target']
            if target.read_bytes() != change['before']:
                raise ValueError('CandidateChangedDuringPreparation')
            temporary = target.with_name(target.name + '.migration94.tmp')
            reject_links(temporary)
            with temporary.open('xb') as stream:
                stream.write(change['after'])
            os.replace(temporary, target)
            if target.read_bytes() != change['after']:
                raise ValueError('CandidateAdaptationReadbackFailed')
            report['changes'].append({'path': relative, 'beforeSHA256': sha_bytes(change['before']),
                                      'afterSHA256': sha_bytes(change['after']), 'replacementCount': 1,
                                      'diff': patch.relative_to(ROOT).as_posix()})
        report['status'] = 'PASS_ISOLATED_TEST_PIN_ADAPTATION94'
    except Exception as error:
        report.update(status='FAIL_ISOLATED_TEST_PIN_ADAPTATION94', errorType=type(error).__name__)
        raise
    finally:
        after_main = api.freeze()
        api.write(out / 'MainSources_after.json', after_main)
        report.update(mainInputsUnchanged=after_main == before_main, finishedUtc=api.utc())
        if not report['mainInputsUnchanged']:
            report['status'] = 'FAIL_PROTECTED_MAIN_INPUTS_CHANGED94'
        api.write(out / 'Adaptation.json', report)
    print(json.dumps({'status': report['status'], 'adaptedTests': len(report['changes']),
                      'mainInputsUnchanged': report['mainInputsUnchanged']}), flush=True)
    return 0 if report['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
