"""Root-run source audit of the isolated migration; never modifies its inputs.

Writes fresh manifests and narrow text diffs only. API compatibility edits are
validated exactly; serialized settings/importer changes remain for root review.
This audit is not a Unity, device, provider, or performance test.
"""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'Verification/Evidence/Unity6Migration94'
MAIN = ROOT / 'Unity'
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'
BASELINE = EVIDENCE / 'MainSources_Before.json'
PREPARATION = EVIDENCE / 'Preparation.json'
SUMMARY93 = ROOT / 'Verification/Evidence/Review93/Summary.json'
GUID = re.compile(rb'^guid:\s*([0-9a-fA-F]{32})\s*$', re.MULTILINE)
ART_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.tga', '.tif', '.tiff', '.psd',
    '.svg', '.exr', '.hdr', '.bmp', '.ttf', '.otf', '.woff', '.woff2', '.mp3', '.wav',
    '.ogg', '.aif', '.aiff', '.flac', '.mp4', '.webm'}
ICON_REPORT = EVIDENCE / 'IconApiPreparation/Set02/Report.json'
ICON_PATHS = {'Assets/HeartOfTheRain/App/Launch/Editor/LaunchSetup.cs',
              'Assets/HeartOfTheRain/Verification/Editor/LaunchReview.cs'}
ENTITY_PATHS = {
    'Assets/HeartOfTheRain/M47/Runtime/EffectMeshBatcher.cs',
    'Assets/HeartOfTheRain/Verification/Editor/EffectBatchVerification.cs',
    'Assets/HeartOfTheRain/Verification/Editor/DenseSubmissionVerification.cs',
    'Assets/HeartOfTheRain/Verification/Execution78Probe.cs',
    'Assets/HeartOfTheRain/Verification/ProfileM71Verification.cs',
    'Assets/HeartOfTheRain/Verification/Editor/PresentationWarmupVerification.cs',
    'Assets/HeartOfTheRain/Verification/Editor/HomeLivesR1Review.cs',
    'Assets/HeartOfTheRain/Chapter01M04/Scripts/RocketSpritePlayer.cs',
    'Assets/HeartOfTheRain/Chapter01M05/Scripts/RenderedSpritePlayer.cs',
}
PIN_PATHS = {'Assets/HeartOfTheRain/Verification/Editor/NativeVerification.cs',
             'Assets/HeartOfTheRain/Verification/Editor/Display88Verification.cs',
             'Assets/HeartOfTheRain/Verification/Editor/Progress92Verification.cs'}
FIXTURES = {
    'Assets/HeartOfTheRain/Verification/Editor/Unity6Migration94.cs':
        ('Templates/Unity6Migration94.cs', 'main'),
    'Assets/HeartOfTheRain/Verification/Editor/Unity6BatchKey94.cs':
        ('Templates/Unity6BatchKey94.cs', 'batch'),
    'Assets/HeartOfTheRain/Verification/Editor/Unity6Importer94.cs':
        ('Templates/Unity6Importer94.cs', 'importer'),
}


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def reject_links(path):
    path = Path(path)
    for node in (path, *path.parents):
        if node.exists() or node.is_symlink():
            info = node.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Linked or reparse input refused')
            if node.is_file() and info.st_nlink != 1:
                raise ValueError('Hard-linked input refused')


def inventory(project, prefix=''):
    project = Path(project)
    reject_links(project)
    result = {}
    for category in ('Assets', 'Packages', 'ProjectSettings'):
        folder = project / category
        if not folder.is_dir():
            raise ValueError('Project input category is missing: ' + category)
        for parent, directories, files in os.walk(folder, followlinks=False):
            directories.sort()
            files.sort()
            for name in directories:
                reject_links(Path(parent) / name)
            for name in files:
                path = Path(parent) / name
                reject_links(path)
                if not stat.S_ISREG(path.stat().st_mode):
                    raise ValueError('Nonregular project input refused')
                before = path.stat()
                relative = prefix + path.relative_to(project).as_posix()
                result[relative] = {'sha256': sha(path), 'bytes': before.st_size}
                after = path.stat()
                if after.st_size != before.st_size or after.st_mtime_ns != before.st_mtime_ns:
                    raise ValueError('Input changed while hashing: ' + relative)
    return {'schemaVersion': 1, 'scope': 'Exact Unity Assets, Packages and ProjectSettings bytes',
            'inputCount': len(result), 'files': dict(sorted(result.items()))}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def without_unity_prefix(baseline):
    result = {}
    for key, value in baseline.items():
        if not key.startswith('Unity/'):
            raise ValueError('Unexpected main manifest key')
        result[key[len('Unity/'):]] = value
    return result


def expected_csharp(main_files):
    """Return exact expected bytes, rather than accepting arbitrary allowed paths."""
    entity_path = Path(__file__).with_name('prepare_entity_ids.py')
    pins_path = Path(__file__).with_name('adapt_test_pins.py')
    entity = load_module('audit94_exact_entity_transform', entity_path)
    pins = load_module('audit94_exact_version_transform', pins_path)
    if (len(entity.FILES) != 9 or set(entity.FILES) != ENTITY_PATHS or
            len(pins.ADAPTATIONS) != 3 or {row[0] for row in pins.ADAPTATIONS} != PIN_PATHS):
        raise ValueError('Exact independent nine-file and three-file path allowlists required')
    expected, reasons = {}, {}
    for relative in entity.FILES:
        original = (MAIN / relative).read_bytes()
        if sha_bytes(original) != main_files[relative]['sha256']:
            raise ValueError('EntityId source does not equal protected main')
        expected[relative] = entity.transform(relative, original)
        reasons[relative] = 'Exact opaque EntityId API compatibility adapter; rendering identity/cache key only, with complete archived control normalization where declared.'
    for relative, before, after in pins.ADAPTATIONS:
        original = (MAIN / relative).read_bytes()
        if relative in expected or original.count(before) != 1:
            raise ValueError('Overlapping or ambiguous exact test-pin adapter')
        expected[relative] = original.replace(before, after, 1)
        reasons[relative] = 'Single exact test engine assertion adapted to the tested Unity 6 version; all substantive assertions retained.'
    icon = json.loads(ICON_REPORT.read_text('utf-8'))
    if (icon.get('status') != 'APPLIED_ISOLATED_LEGACY_ICON_API_PORT94' or
            {row['path'] for row in icon.get('changes', [])} != ICON_PATHS or
            len(icon['changes']) != 2):
        raise ValueError('Exact two-file icon API review receipt required')
    for row in icon['changes']:
        relative = row['path']
        if relative in expected or row['beforeSHA256'] != main_files[relative]['sha256']:
            raise ValueError('Icon API receipt baseline mismatch')
        actual = (PROJECT / relative).read_bytes()
        if sha_bytes(actual) != row['afterSHA256']:
            raise ValueError('Candidate icon API bytes differ from reviewed port: ' + relative)
        expected[relative] = actual
        reasons[relative] = 'Exact hash-bound removed legacy icon API port from the Set02 receipt; same approved artwork and original icon assertion.'
    if len(expected) != 14:
        raise ValueError('Expected exactly nine EntityId, three test-pin and two icon API edits')
    return expected, reasons, {
        'entityAdapterSHA256': sha(entity_path), 'testPinAdapterSHA256': sha(pins_path),
        'iconPortReceiptSHA256': sha(ICON_REPORT),
        'entityPortFileCount': 9, 'testPinFileCount': 3, 'legacyIconApiFileCount': 2}


def fixture_expectations(preparation):
    batch_path = EVIDENCE / 'BatchKeyPreparation/Report.json'
    batch = json.loads(batch_path.read_text('utf-8'))
    if batch.get('status') != 'PREPARED_ISOLATED_INDEPENDENT_BATCH_KEY_NATIVE_FIXTURE':
        raise ValueError('Independent new fixture preparation receipt required')
    importer_path = EVIDENCE / 'ImporterPreparation/Report.json'
    importer = json.loads(importer_path.read_text('utf-8'))
    if (importer.get('status') != 'PREPARED_ISOLATED_READ_ONLY_IMPORTER_PROBE94'
            or importer.get('expectedRows') != 438 or importer.get('expectedNonzeroBorders') != 105
            or importer.get('mainInputsUnchanged') is not True):
        raise ValueError('Exact isolated read-only importer fixture preparation required')
    importer_correction = None
    if importer.get('templateSHA256') != sha(Path(__file__).parent / 'Templates/Unity6Importer94.cs'):
        correction = load_module('audit94_exact_ppu_assertion', Path(__file__).with_name('correct_importer_ppu94.py'))
        correction.validated_correction(importer)
        importer_correction = sha(correction.CORRECTION)
    identifiers = {'main': preparation['newTemplateGuid'], 'batch': batch['newFixtureGuid'],
                   'importer': importer['newFixtureGuid']}
    fixtures, guids, bindings = {}, {}, {}
    for relative, (tail, group) in FIXTURES.items():
        template = Path(__file__).parent / tail
        fixtures[relative] = template.read_bytes()
        guids[relative + '.meta'] = identifiers[group]
        bindings[relative] = {'template': template.relative_to(ROOT).as_posix(),
                              'templateSHA256': sha(template), 'guid': identifiers[group]}
    return fixtures, guids, {'fixtures': bindings, 'batchReceiptSHA256': sha(batch_path),
                            'importerReceiptSHA256': sha(importer_path),
                            'importerCorrectionReceiptSHA256': importer_correction}


def compare_sources(main_files, candidate_files, expected_cs, cs_reasons, fixtures):
    """Pure policy: all original Assets except exact C# ports/meta stay byte equal."""
    changes, violations = [], []
    for relative in sorted(set(main_files) | set(candidate_files)):
        before, after = main_files.get(relative), candidate_files.get(relative)
        if before == after:
            continue
        kind = 'added' if before is None else 'deleted' if after is None else 'changed'
        reason, review = '', False
        if relative.startswith(('Packages/', 'ProjectSettings/')):
            reason = ('Unity 6 package/dependency resolution or serialized project configuration. '
                      'Root must review the actual diff; this source audit does not approve its keys or behavior.')
            review = True
        elif relative.startswith('Assets/'):
            if before is not None and after is None:
                violations.append('OriginalAssetDeleted:' + relative)
            elif relative.endswith('.meta'):
                if before is not None:
                    reason = 'Existing importer serialization delta; original GUID must remain exact. Importer field changes require root review.'
                    review = True
                elif relative[:-5] in fixtures:
                    reason = 'Metadata for one explicitly prepared, new Editor-only verification fixture.'
                else:
                    violations.append('UnknownAssetMetadataAdded:' + relative)
            elif before is None:
                if relative not in fixtures:
                    violations.append('UnknownAssetAdded:' + relative)
                elif after['sha256'] != sha_bytes(fixtures[relative]) or after['bytes'] != len(fixtures[relative]):
                    violations.append('NewFixtureDiffersFromTemplate:' + relative)
                else:
                    reason = 'New Editor-only native verification fixture; bytes match its current review template.'
            elif relative.endswith('.cs'):
                if relative not in expected_cs:
                    violations.append('UnknownCSharpChanged:' + relative)
                elif after['sha256'] != sha_bytes(expected_cs[relative]) or after['bytes'] != len(expected_cs[relative]):
                    violations.append('NonExactCSharpPort:' + relative)
                else:
                    reason = cs_reasons[relative]
            else:
                violations.append('ProtectedAssetBytesChanged:' + relative)
        else:
            violations.append('UnknownInputCategory:' + relative)
        changes.append({'path': relative, 'kind': kind, 'before': before, 'after': after,
                        'reason': reason or 'Rejected by source protection policy',
                        'requiresRootConfigurationReview': review})
    for relative in expected_cs:
        if candidate_files.get(relative, {}).get('sha256') != sha_bytes(expected_cs[relative]):
            violations.append('RequiredExactPortMissing:' + relative)
    for relative, content in fixtures.items():
        if candidate_files.get(relative, {}).get('sha256') != sha_bytes(content):
            violations.append('RequiredNewFixtureMissing:' + relative)
    return changes, sorted(set(violations))


def one_guid(raw):
    matches = GUID.findall(raw)
    if len(matches) != 1:
        raise ValueError('Each asset metadata file must contain exactly one valid GUID')
    return matches[0].decode('ascii')


def audit_guids(main_files, candidate_files, fixture_guids, read_main, read_candidate):
    original, changed, violations, identifiers = [], [], [], {}
    for relative in sorted(candidate_files):
        if not relative.startswith('Assets/') or not relative.endswith('.meta'):
            continue
        value = one_guid(read_candidate(relative))
        folded = value.lower()
        if folded in identifiers:
            violations.append('DuplicateCandidateGuid:' + relative)
        identifiers[folded] = relative
        if relative in main_files:
            before = one_guid(read_main(relative))
            same = before == value
            original.append({'path': relative, 'guid': before, 'preserved': same})
            if not same:
                violations.append('OriginalGuidChanged:' + relative)
            if main_files[relative] != candidate_files[relative]:
                changed.append(relative)
        elif fixture_guids.get(relative) != value:
            violations.append('UnexpectedNewFixtureGuid:' + relative)
    for relative in main_files:
        if relative.startswith('Assets/') and relative.endswith('.meta') and relative not in candidate_files:
            violations.append('OriginalMetadataMissing:' + relative)
    for relative in fixture_guids:
        if relative not in candidate_files:
            violations.append('NewFixtureMetadataMissing:' + relative)
    return {'originalGuidCount': len(original), 'allOriginalGuidsPreserved': all(row['preserved'] for row in original),
            'exactExistingMetadataUnchanged': len(original) - len(changed),
            'changedExistingMetadataCount': len(changed), 'changedExistingMetadata': changed,
            'newFixtureMetadataCount': len(fixture_guids),
            'originalGuidBindings': original, 'violations': sorted(set(violations))}


def protected_groups(main_files, candidate_files):
    predicates = {
        'binaryArtworkFontsAudio': lambda path: path.startswith('Assets/') and Path(path).suffix.lower() in ART_EXTENSIONS,
        'scenes': lambda path: path.startswith('Assets/') and path.lower().endswith('.unity'),
        'assetJsonIncludingLevelsAndMasks': lambda path: path.startswith('Assets/') and path.lower().endswith('.json'),
        'sixShaders': lambda path: path.startswith('Assets/') and path.lower().endswith('.shader'),
        'M46RuntimeModelCSharp': lambda path: path.startswith('Assets/HeartOfTheRain/M46/Runtime/') and path.endswith('.cs'),
        'M48RuntimeCSharp': lambda path: path.startswith('Assets/HeartOfTheRain/M48/Runtime/') and path.endswith('.cs'),
    }
    groups = {}
    for name, predicate in predicates.items():
        selected = [path for path in main_files if predicate(path)]
        altered = [path for path in selected if main_files[path] != candidate_files.get(path)]
        groups[name] = {'originalCount': len(selected), 'bytesUnchanged': not altered, 'changedOrMissing': altered}
    if groups['sixShaders']['originalCount'] != 6:
        raise ValueError('Expected exactly six original shader inputs')
    return groups


def git_output(*arguments):
    completed = subprocess.run(['git', '-c', 'core.longpaths=true', *arguments], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45, check=False,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if completed.returncode:
        raise ValueError('Read-only Git source comparison failed')
    return completed.stdout


def audit_backend(baseline_commit):
    head = git_output('rev-parse', 'HEAD').decode().strip()
    baseline_tree = git_output('rev-parse', baseline_commit + ':Backend').decode().strip()
    head_tree = git_output('rev-parse', 'HEAD:Backend').decode().strip()
    if baseline_tree != head_tree:
        raise ValueError('Backend HEAD tree differs from the authorized migration baseline')
    records, violations = [], []
    for entry in git_output('ls-tree', '-r', '-z', 'HEAD', '--', 'Backend').split(b'\0'):
        if not entry:
            continue
        description, raw_path = entry.split(b'\t', 1)
        mode, kind, git_sha = description.decode().split(' ')
        relative = raw_path.decode('utf-8')
        if kind != 'blob' or mode not in ('100644', '100755') or not relative.startswith('Backend/'):
            raise ValueError('Unexpected Backend Git object or path')
        path = ROOT / relative
        reject_links(path)
        if not path.is_file():
            violations.append('TrackedBackendFileMissing:' + relative)
            continue
        content = path.read_bytes()
        current_git_sha = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        records.append({'path': relative, 'bytes': len(content), 'sha256': sha_bytes(content),
                        'headGitBlob': git_sha, 'currentGitBlob': current_git_sha})
        if current_git_sha != git_sha:
            violations.append('TrackedBackendBytesChanged:' + relative)
    untracked = [value.decode('utf-8') for value in git_output('ls-files', '--others',
                '--exclude-standard', '-z', '--', 'Backend').split(b'\0') if value]
    if untracked:
        violations.extend('UntrackedBackendSource:' + path for path in untracked)
    return {'scope': 'Whole tracked Backend tree compared with actual HEAD blobs and authorized baseline tree; nonignored untracked Backend files also rejected. Ignored environments/databases/caches are outside source scope.',
            'headCommit': head, 'baselineCommit': baseline_commit, 'headBackendTree': head_tree,
            'baselineBackendTree': baseline_tree, 'trackedFiles': len(records), 'files': records,
            'nonignoredUntracked': untracked, 'unchanged': not violations,
            'violations': violations}


def text_diff(before, after, relative):
    if b'\0' in before or b'\0' in after:
        return None
    try:
        left, right = before.decode('utf-8-sig'), after.decode('utf-8-sig')
    except UnicodeDecodeError:
        return None
    difference = ''.join(difflib.unified_diff(left.splitlines(True), right.splitlines(True),
        fromfile='main/' + relative, tofile='candidate/' + relative, n=3))
    for line in difference.splitlines():
        if line.startswith('+') and not line.startswith('+++') and re.search(
                r'(?i)(?:password|keystorepass|keyaliaspass|access.?token|api.?secret|client.?secret|private.?key)\s*[:=]\s*[^\s"\'}]', line):
            raise ValueError('Potential nonempty credential setting refused from text diff export')
    return difference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        print('Read-only source audit requires root --execute to create fresh evidence. No inputs are altered.')
        return 0
    reject_links(args.out)
    out = args.out.resolve()
    if not out.is_relative_to((EVIDENCE / 'SourceAudit').resolve()) or out.exists():
        parser.error('Fresh uniquely named checkpoint94 SourceAudit child required')
    preparation = json.loads(PREPARATION.read_text('utf-8'))
    baseline = json.loads(BASELINE.read_text('utf-8-sig'))
    if (preparation.get('status') != 'PASS_EXACT_MAIN_COPY94' or
            preparation.get('authorization') != 'USER_APPROVED_ISOLATED_UNITY6_MIGRATION' or
            preparation.get('project') != PROJECT.relative_to(ROOT).as_posix() or
            preparation.get('mainManifestSHA256') != sha(BASELINE) or
            baseline.get('inputCount') != 5407 or len(baseline.get('files', {})) != 5407):
        parser.error('Exact authorized 5,407-input migration preparation required')
    out.mkdir(parents=True, exist_ok=False)
    report = {'schemaVersion': 1, 'status': 'RUNNING_ISOLATED_SOURCE_AUDIT94',
        'startedUtc': utc(), 'runnerSHA256': sha(__file__),
        'preparationSHA256': sha(PREPARATION), 'mainBaselineSHA256': sha(BASELINE),
        'candidate': PROJECT.relative_to(ROOT).as_posix(),
        'scope': 'Read-only host byte/GUID/source-policy audit of the isolated Unity 6 candidate. Exact API adapters affect presentation identity and Editor verification only; no gameplay/model/economy change or whole-game smoothness approval is inferred. Serialized settings/importer deltas still require explicit root review.',
        'inputsModifiedByAudit': False, 'sdkOrUnityOrDeviceCommandsExecuted': False,
        'configurationChangesApprovedByThisAudit': False}
    try:
        main_before = inventory(MAIN, 'Unity/')
        write_new(out / 'MainSources_before.json', main_before)
        if main_before['files'] != baseline['files'] or main_before['inputCount'] != 5407:
            raise ValueError('Main Unity source differs from the exact approved 5,407-input baseline')
        if sha(SUMMARY93) != preparation['accepted93SummarySHA256']:
            raise ValueError('Historical accepted Review93 summary changed')
        report['accepted93SummarySHA256'] = sha(SUMMARY93)
        candidate = inventory(PROJECT)
        write_new(out / 'CandidateSources.json', candidate)
        main_files = without_unity_prefix(main_before['files'])
        expected, reasons, adapter_bindings = expected_csharp(main_files)
        fixtures, fixture_guids, fixture_bindings = fixture_expectations(preparation)
        report['exactAdapterBindings'] = adapter_bindings
        report['newFixtureBindings'] = fixture_bindings
        isolation_receipt = EVIDENCE / 'EditorDataIsolationPreparation/Report.json'
        if isolation_receipt.is_file():
            report['editorDataIsolationPreparationSHA256'] = sha(isolation_receipt)
        changes, violations = compare_sources(main_files, candidate['files'], expected, reasons, fixtures)
        write_new(out / 'FileChanges.json', changes)
        groups = protected_groups(main_files, candidate['files'])
        write_new(out / 'ProtectedGroups.json', groups)
        identifiers = audit_guids(main_files, candidate['files'], fixture_guids,
            lambda relative: (MAIN / relative).read_bytes(),
            lambda relative: (PROJECT / relative).read_bytes())
        write_new(out / 'GuidAudit.json', identifiers)
        violations.extend(identifiers['violations'])
        for name, value in groups.items():
            if not value['bytesUnchanged']:
                violations.append('ProtectedGroupChanged:' + name)
        backend = audit_backend(preparation['baselineCommit'])
        write_new(out / 'BackendInputs.json', backend)
        violations.extend(backend['violations'])
        diffs = []
        for row in changes:
            relative = row['path']
            before = (MAIN / relative).read_bytes() if row['before'] is not None else b''
            after = (PROJECT / relative).read_bytes() if row['after'] is not None else b''
            difference = text_diff(before, after, relative)
            entry = {'path': relative, 'binaryDiffOmitted': difference is None}
            if difference is not None:
                destination = out / 'Diffs' / (relative + '.diff')
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('x', encoding='utf-8', newline='') as stream:
                    stream.write(difference)
                entry.update(diff=destination.relative_to(ROOT).as_posix(), sha256=sha(destination))
            diffs.append(entry)
        write_new(out / 'TextDiffIndex.json', diffs)
        main_after = inventory(MAIN, 'Unity/')
        candidate_after = inventory(PROJECT)
        write_new(out / 'MainSources_after.json', main_after)
        write_new(out / 'CandidateSources_after.json', candidate_after)
        if main_before != main_after or main_after['files'] != baseline['files']:
            violations.append('MainSourceChangedDuringAudit')
        if candidate != candidate_after:
            violations.append('CandidateChangedDuringAudit')
        if sha(SUMMARY93) != preparation['accepted93SummarySHA256']:
            violations.append('Accepted93SummaryChangedDuringAudit')
        backend_after = audit_backend(preparation['baselineCommit'])
        if backend_after != backend:
            violations.append('BackendChangedDuringAudit')
        reviews = [row['path'] for row in changes if row['requiresRootConfigurationReview']]
        report.update(status=('FAIL_ISOLATED_CANDIDATE_SOURCE_AUDIT94' if violations else
            'PASS_ISOLATED_CANDIDATE_SOURCE_AUDIT94_WITH_CONFIGURATION_REVIEW_REQUIRED'),
            violations=sorted(set(violations)), mainInputCount=5407,
            mainInputsUnchanged=main_before == main_after,
            candidateInputCount=candidate['inputCount'], candidateInputsStable=candidate == candidate_after,
            exactCSharpPortCount=len(expected), newEditorFixtureCount=len(fixtures),
            existingGuidCount=identifiers['originalGuidCount'],
            allOriginalGuidsPreserved=identifiers['allOriginalGuidsPreserved'],
            exactExistingMetadataUnchanged=identifiers['exactExistingMetadataUnchanged'],
            changedExistingMetadataCount=identifiers['changedExistingMetadataCount'],
            changeCounts={kind: sum(row['kind'] == kind for row in changes)
                          for kind in ('added', 'changed', 'deleted')},
            requiresRootSerializedConfigurationReview=reviews,
            backendHeadSourceUnchanged=backend['unchanged'],
            reportFileSHA256={path.name: sha(path) for path in sorted(out.glob('*.json'))},
            limitations=['Known compatibility changes are exact-source checks, not cross-engine rendering equivalence.',
                'Packages, ProjectSettings and changed existing importer fields require root review of the bound diffs.',
                'No backend tests, Unity suite, APK build, device operation, provider integration or timing measurement is performed here.'])
    except Exception as error:
        report.update(status='FAIL_ISOLATED_CANDIDATE_SOURCE_AUDIT94',
                      errorType=type(error).__name__, error=str(error))
        raise
    finally:
        report['finishedUtc'] = utc()
        write_new(out / 'Report.json', report)
        print(json.dumps({'status': report['status'], 'report': str(out / 'Report.json'),
                          'violations': report.get('violations', [])}), flush=True)
    return 0 if not report['violations'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
