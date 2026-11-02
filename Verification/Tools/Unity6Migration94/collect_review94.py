"""Collect explicitly selected isolated Unity 6 evidence; no Unity/ADB execution.

Missing stages create an INCOMPLETE draft. Completion requires bound source and
visual assessments authored by root. It never promotes or changes the main app.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'Verification/Evidence/Unity6Migration94'
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'
VERSION = '6000.6.6f1'
COMPLETE = 'COMPLETED_ISOLATED_UNITY6_SPLASH_REVIEW94_WITH_OPEN_GATES'
OPEN_GATES = [
    'The ordinary main project remains Unity2022.3.62f3 and its installed APK/save is not migrated. Main promotion requires a separate decision.',
    'Historical Review93 Account clipboard failures remain retained. Current Editor diagnostics do not establish Android account recovery/deletion acceptance.',
    'The trusted backend replay worker remains pinned2022; sampled model parity is not deployment or server-authority acceptance.',
    'RuStore/Yandex/VK configuration, supported configured Android provider tests, hosted backend/HTTPS operations, signing, legal/moderation and store submission remain open.',
    'Residual physical frame stalls and whole-game smoothness remain unaccepted. Native warmed CPU spans are not Android frame pacing.',
    'Broader phone/tablet/API26/low-memory coverage, human campaign and long-session testing remain separate gates.',
]
REQUIRED_COMPONENTS = {'environment', 'source', 'sourceReview', 'native', 'config', 'batch',
    'effects', 'dense', 'model', 'buildDevelopment', 'buildNonDevelopment', 'device',
    'coldstart', 'visualReview', 'preservation'}
_DIGEST_CACHE = {}


def utc():
    return datetime.now(timezone.utc).isoformat()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    path = Path(path)
    value = path.stat()
    key = (str(path.resolve()), value.st_size, value.st_mtime_ns)
    if key not in _DIGEST_CACHE:
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                digest.update(block)
        _DIGEST_CACHE[key] = digest.hexdigest()
    return _DIGEST_CACHE[key]


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def contained(path, parent=None):
    parent = OUT if parent is None else parent
    path = Path(path).absolute()
    for node in (path, *path.parents):
        if node.exists() or node.is_symlink():
            info = node.lstat()
            need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                 'Linked/reparse evidence path refused')
    path = path.resolve()
    need(path.is_relative_to(Path(parent).resolve()), 'Evidence path is outside its declared scope')
    return path


def binding(path):
    path = contained(path, ROOT)
    need(path.is_file(), 'Bound artifact is missing')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def validate_binding(value, parent=None):
    parent = ROOT if parent is None else parent
    need(isinstance(value, dict) and set(value) == {'path', 'sha256', 'bytes'}, 'Exact artifact binding required')
    path = contained(ROOT / value['path'], parent)
    need(binding(path) == value, 'Bound artifact bytes changed')
    return path


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def files(value):
    need(isinstance(value, dict) and isinstance(value.get('files'), dict)
         and value.get('inputCount') == len(value['files']), 'Actual source manifest required')
    return value['files']


def completed_status(components, issues):
    return COMPLETE if (not issues and REQUIRED_COMPONENTS.issubset(components)
        and all(components[key].get('passed') is True for key in REQUIRED_COMPONENTS)) else 'INCOMPLETE_ISOLATED_UNITY6_REVIEW94'


def environment(path):
    path = contained(path)
    record = read(path)
    need(record.get('status') == 'PASS_PORTABLE_UNITY6_ANDROID_TOOLCHAIN94_ONLY'
         and record.get('version') == VERSION and record.get('changeset') == 'd20c9ac777da'
         and record.get('verifiedModuleCount') == record.get('expectedModuleCount') == 11
         and record.get('originalEditorExecutableAndMetadataUnchanged') is True
         and record.get('cli', {}).get('version') == '1.0.0-beta.14'
         and record['cli'].get('actualSHA256') == record['cli'].get('expectedSHA256')
            == '78761a0547cd4a9bc212e27a217c66e6a621bf48c753ba440e4b2327ee7ff8ac'
         and record.get('java', {}).get('runtimeBuild') == '17.0.18+8'
         and record.get('installer', {}).get('cliReportedSuccess') is True
         and record['installer'].get('cliReportedErrors') == [], 'Verified official portable toolchain receipt required')
    need(record.get('runnerSHA256') == sha(HERE / 'record_environment.py')
         and set(record.get('originalEditorChecks', {})) == {'modules.json', 'metadata.hub.json', 'Editor/Unity.exe'}
         and len(record.get('modules', {})) == 11, 'Complete unchanged environment proof required')
    for relative, row in record['originalEditorChecks'].items():
        original = Path('C:/Program Files/Unity/Hub/Editor/6000.6.6f1') / relative
        need(row.get('unchanged') is True and sha(original) == row.get('actualSHA256')
             == row.get('beforeSHA256'), 'Original Editor metadata/executable changed')
    for group in record['modules'].values():
        need(group.get('installedMetadataSelected') is True, 'Module metadata selection absent')
        for row in group['artifacts']:
            artifact = contained(Path('E:/HeartRainUnity6_94/6000.6.6f1') / row['path'],
                                 Path('E:/HeartRainUnity6_94/6000.6.6f1'))
            need(artifact.is_file() and sha(artifact) == row['sha256'] and artifact.stat().st_size == row['bytes'],
                 'Recorded portable toolchain artifact changed')
    return {'passed': True, 'report': binding(path), 'moduleCount': 11,
        'installerWarnings': record['installer']['cliWarnings'],
        'wrapperExitCode': record['installer']['wrapperExitCode'],
        'scope': 'Official private CLI/toolchain/version/artifact proof only. The PowerShell wrapper exit and recovered installer warning remain separate; no Unity project/device acceptance inferred.'}


def verify_native(report_path, expected_status, entry, baseline, candidate, *, configure=False,
                  allow_account_failure=False):
    report_path = contained(report_path)
    report = read(report_path)
    directory = report_path.parent
    # A report may be in a Native/ child of its invocation folder.
    if not (directory / 'Invocation.json').is_file() and directory.name == 'Native':
        directory = directory.parent
    invocation_path = directory / 'Invocation.json'
    invocation = read(invocation_path)
    need(invocation.get('entry') == entry and invocation.get('expectedVersion') == VERSION
         and invocation.get('expectedNativeStatus') == expected_status
         and invocation.get('actualEngineVersionFromProcessLog') == VERSION
         and invocation.get('nativeReport') == report_path.relative_to(ROOT).as_posix()
         and invocation.get('nativeReportSHA256') == sha(report_path)
         and invocation.get('mainInputsUnchanged') is True and invocation.get('unityPidsAfter') == []
         and invocation.get('ownedJobAssignedBeforeResume') is True,
         'Actual completed bounded Unity6 invocation/report binding required')
    command = invocation.get('command', [])
    need(isinstance(command, list) and '-projectPath' in command
         and Path(command[command.index('-projectPath') + 1]).resolve() == PROJECT.resolve()
         and Path(command[0]).resolve() == Path('E:/HeartRainUnity6_94/6000.6.6f1/Editor/Unity.exe').resolve()
         and sha(command[0]) == invocation.get('editorSHA256'), 'Exact isolated Editor/project required')
    log = directory / 'Unity.log'
    console = directory / 'Console.log'
    need(sha(log) == invocation.get('unityLogSHA256')
         and sha(console) == invocation.get('consoleLogSHA256'), 'Native process logs changed')
    engine = re.search(r'Initialize engine version:\s*(\S+)', log.read_text('utf-8-sig', errors='replace'))
    need(engine is not None and engine.group(1) == VERSION, 'Actual engine process log required')
    for name in ('MainSources_before.json', 'MainSources_after.json'):
        need(files(read(directory / name)) == baseline, 'Protected main changed in native invocation')
    before = files(read(directory / 'CandidateSources_before.json'))
    after = files(read(directory / 'CandidateSources_after.json'))
    need(after == candidate and (configure or before == after), 'Candidate source differs from selected final candidate')
    if 'unity' in report:
        need(report['unity'] == VERSION, 'Native report engine differs')
    else:
        need(invocation.get('legacyReportWithoutUnityField') is True, 'Known versionless legacy schema declaration required')
    account = module('collect94_account_schema', 'run_suites.py')
    case = dict(account.ACCOUNT_DIAGNOSTIC)
    classification = account.account_classification(report, case) if allow_account_failure else None
    passed = (invocation.get('status') == 'PASS_ISOLATED_UNITY6_94_NATIVE'
              and invocation.get('exitCode') == 0 and report.get('status') == expected_status
              and not any(report.get(key) for key in ('error', 'errors', 'failures', 'failed')))
    accepted_failure = allow_account_failure and classification == 'RETAINED_FAIL_ACCOUNT_CLIPBOARD_ACCEPTANCE_UNRESOLVED'
    need(passed or accepted_failure, 'Required native assertion/process did not pass')
    if accepted_failure:
        need(invocation.get('status') == 'FAIL_ISOLATED_UNITY6_94_NATIVE', 'Retained Account failure invocation must remain FAIL')
    return {'passed': passed, 'retainedDiagnosticFailure': bool(accepted_failure),
        'diagnosticClassification': classification, 'status': report.get('status'),
        'report': binding(report_path), 'invocation': binding(invocation_path),
        'log': binding(log), 'candidateSources': binding(directory / 'CandidateSources_after.json'),
        'actualEngine': VERSION, 'raw': report}


def native_suites(paths, replacements, baseline, candidate):
    runner = module('collect94_native_schemas', 'run_suites.py')
    configuration = read(HERE / 'suites94.json')
    cases = {case['name']: case for case in configuration['cases']}
    cases['Account'] = dict(runner.ACCOUNT_DIAGNOSTIC)
    selected, retained, sets = {}, [], []
    for path in paths:
        path = contained(path)
        record = read(path)
        need(path.name == 'SuiteSet.json' and record.get('candidateUnity') == VERSION
             and record.get('mainInputsUnchanged') is True and record.get('unityPidsAfter') == []
             and not any(record.get('mainSourceDelta', {}).values())
             and not any(record.get('candidateSourceDelta', {}).values())
             and record.get('suiteConfigurationSHA256') == sha(HERE / 'suites94.json'),
             'Completed source-preserving suite set required')
        need(files(read(path.parent / 'MainSources_before.json')) == baseline
             and files(read(path.parent / 'MainSources_after.json')) == baseline
             and files(read(path.parent / 'CandidateSources_before.json')) == candidate
             and files(read(path.parent / 'CandidateSources_after.json')) == candidate,
             'Suite-set source maps differ from final candidate')
        sets.append(binding(path))
        for row in record.get('runs', []):
            name = row.get('name')
            if name not in cases:
                continue
            invocation_path = contained(ROOT / row['invocation'])
            report_path = contained(ROOT / row['reportPath'])
            need(sha(invocation_path) == row.get('invocationSHA256')
                 and sha(report_path) == row.get('reportSHA256'), 'Suite row artifact changed')
            if row.get('acceptedNativePass') is not True:
                retained.append({'name': name, 'report': binding(report_path),
                    'invocation': binding(invocation_path), 'nativeStatus': row.get('nativeStatus'),
                    'invocationStatus': row.get('invocationStatus'),
                    'diagnosticOnly': row.get('diagnosticOnly') is True})
            need(name not in selected, 'Duplicate suite selection requires an explicit --select-native override')
            selected[name] = report_path
    for replacement in replacements:
        need('=' in replacement, 'Native override must be NAME=Invocation.json')
        name, text = replacement.split('=', 1)
        need(name in cases, 'Unknown explicit native override name')
        invocation_path = contained(text)
        need(invocation_path.name == 'Invocation.json', 'Override must name an explicit invocation receipt')
        invocation = read(invocation_path)
        selected[name] = contained(ROOT / invocation['nativeReport'])
    need(set(selected) == set(cases), 'All nine required suites and separate Account diagnostic must be selected explicitly')
    result, passing_checks = [], 0
    for name, case in cases.items():
        row = verify_native(selected[name], case['expected'], case['entry'], baseline, candidate,
                            allow_account_failure=name == 'Account')
        counters = runner.count_native(row['raw'], case)
        row.update(counters, name=name, diagnosticOnly=name == 'Account')
        if name != 'Account':
            need(row['passed'], 'Required suite must pass')
            passing_checks += row['attemptedChecks'] or 0
        row.pop('raw')
        result.append(row)
    return {'passed': True, 'requiredSuites': 9, 'requiredPassingChecks': passing_checks,
            'diagnosticSuites': 1, 'selected': result, 'suiteSets': sets,
            'retainedUnselectedOrDiagnosticFailures': retained,
            'scope': 'Explicit selected current-source actual Unity6 invocations. Original failed sets remain linked; a selected passing repeat never rewrites their failures.'}


def verify_source(path, preparation, baseline):
    path = contained(path)
    record = read(path)
    need(record.get('status') == 'PASS_ISOLATED_CANDIDATE_SOURCE_AUDIT94_WITH_CONFIGURATION_REVIEW_REQUIRED'
         and record.get('violations') == [] and record.get('mainInputCount') == 5407
         and record.get('mainInputsUnchanged') is True and record.get('candidateInputsStable') is True
         and record.get('allOriginalGuidsPreserved') is True
         and record.get('backendHeadSourceUnchanged') is True
         and record.get('exactCSharpPortCount') == 14 and record.get('newEditorFixtureCount') == 3
         and record.get('accepted93SummarySHA256') == preparation['accepted93SummarySHA256']
         and record.get('runnerSHA256') == sha(HERE / 'audit_candidate94.py'), 'Passing exact source audit required')
    for name, expected in record['reportFileSHA256'].items():
        need(Path(name).name == name and sha(path.parent / name) == expected, 'Source audit companion changed')
    need(files(read(path.parent / 'MainSources_before.json')) == baseline
         and files(read(path.parent / 'MainSources_after.json')) == baseline, 'Source audit main map differs')
    candidate_path = path.parent / 'CandidateSources.json'
    candidate = files(read(candidate_path))
    need(files(read(path.parent / 'CandidateSources_after.json')) == candidate, 'Source audit candidate map unstable')
    groups = read(path.parent / 'ProtectedGroups.json')
    need(all(row.get('bytesUnchanged') is True for row in groups.values())
         and groups['sixShaders']['originalCount'] == 6, 'Protected source groups changed')
    backend = read(path.parent / 'BackendInputs.json')
    need(backend.get('unchanged') is True and not backend.get('violations'), 'Backend source audit failed')
    return {'passed': True, 'report': binding(path), 'candidateSources': binding(candidate_path),
            'mainInputs': 5407, 'candidateInputs': len(candidate), 'protectedGroups': groups,
            'existingGuidCount': record['existingGuidCount'],
            'changedExistingMetadataCount': record['changedExistingMetadataCount'],
            'backendTrackedFiles': backend['trackedFiles'], 'configurationApproved': False}, candidate


def source_review(path, source):
    path = contained(path)
    record = read(path)
    need(record.get('status') == 'ROOT_REVIEWED_ISOLATED_UNITY6_94_SOURCE_AND_SETTINGS'
         and record.get('reviewer') == 'root' and record.get('sourceAudit') == source['report']
         and record.get('candidateSources') == source['candidateSources']
         and record.get('packageAndSerializedSettingsApprovedForIsolatedTest') is True
         and record.get('importerChangesReviewed') is True
         and record.get('mainPromotionApproved') is False, 'Explicit root isolated settings/source review required')
    source_path = ROOT / source['report']['path']
    diffs = read(source_path.parent / 'TextDiffIndex.json')
    expected = [binding(ROOT / item['diff']) for item in diffs if not item['binaryDiffOmitted']]
    need(record.get('reviewedDiffs') == expected, 'Root must bind every exported narrow text diff explicitly')
    return {'passed': True, 'report': binding(path), 'reviewedDiffCount': len(expected),
            'mainPromotionApproved': False}


def effects(path, baseline, candidate):
    row = verify_native(path, 'PASS_NATIVE_EFFECT_BATCH',
        'HeartOfTheRain.Verification.EffectBatchVerification.Run', baseline, candidate)
    raw = row.pop('raw')
    need(raw.get('checks') == 344 and raw.get('exactDifferingPixels') == 0
         and raw.get('preparedDifferingPixels') == 0 and raw.get('optimizedBaselineDifferingPixels') == 0
         and raw.get('transformParityFrames') == 65 and raw.get('constructionParityFrames') == 45,
         'Declared strict effect controls missing')
    row.update(checks=344, transformStates=65, constructionStates=45,
        exactDifferingPixels=raw['exactDifferingPixels'], exactMaxChannelDelta=raw['exactMaxChannelDelta'],
        groupedDifferingPixels=raw['groupedDifferingPixels'], unityDifferingPixels=raw['unityDifferingPixels'],
        scope='Same Unity6 engine, declared native comparison threshold and exact prepared/control geometry only. Composition differences and maximum channel delta remain reported; no cross-engine pixel or Android frame-pacing claim.')
    return row


def configuration(path, baseline, candidate):
    row = verify_native(path, 'PASS_ISOLATED_UNITY6_94_CONFIGURE',
        'HeartOfTheRain.Verification.Unity6Migration94.Configure', baseline, candidate, configure=True)
    raw = row.pop('raw')
    after = raw.get('after', {})
    need(after.get('showSplashScreen') is False and after.get('showUnityLogo') is False
         and after.get('companyName') == 'HeartOfTheRainUnity6Review94'
         and after.get('packageName') == 'com.heartoftherain.unity6review94'
         and after.get('portraitOnly') is True and after.get('sdkFreeDefines') is True
         and after.get('backend') == 'IL2CPP' and after.get('architectures') == 'ARM64'
         and after.get('minApi') == 26 and after.get('targetApi') == 'AndroidApiLevel36'
         and after.get('applicationEntry') == 'Activity', 'Final isolated splash/data settings differ')
    need(raw.get('checks') and all(item.get('passed') is True for item in raw['checks']),
         'Actual native configure checks must all pass')
    row['checks'] = len(raw['checks'])
    return row


def batch_keys(path, baseline, candidate):
    row = verify_native(path, 'PASS_NATIVE_UNITY6_94_BATCH_KEYS',
        'HeartOfTheRain.Verification.Unity6BatchKey94.Run', baseline, candidate)
    raw = row.pop('raw')
    need(raw.get('checks') == 275 and raw.get('negativeControls') == 4
         and len(raw.get('passed', [])) == 275, 'Independent batch controls incomplete')
    row['checks'] = 275
    return row


def dense(path, baseline, candidate):
    row = verify_native(path, 'PASS_NATIVE_DENSE_SUBMISSION78',
        'HeartOfTheRain.Verification.DenseSubmissionVerification.Run', baseline, candidate)
    raw = row.pop('raw')
    need(raw.get('fixtures') == 9 and raw.get('parityFrames') == 135
         and len(raw.get('pixelRows', [])) == 2 and len(raw.get('timings', [])) == 9
         and raw.get('compiledSourceMatchesArchive') is True
         and all(item.get('differingPixels') == 0 and item.get('maxChannelDelta') == 0 for item in raw['pixelRows']),
         'Declared dense upload and strict pixel controls missing')
    row.update(checks=raw['checks'], fixtures=9, uploadStates=135, strictPixelRows=2,
               scope='Same-engine strict upload/pixel controls; warmed CPU timing samples remain diagnostic and do not certify Android smoothness.')
    return row


def model(path, candidate):
    path = contained(path)
    record = read(path)
    need(record.get('status') == 'PASS_CROSS_ENGINE_350_MODEL_ROWS94'
         and record.get('comparedRows') == record.get('rawTurnMatches') == record.get('finalSnapshotMatches') == 350
         and record.get('all350RawTurnsAndFinalSnapshotsEqual') is True and record.get('differences') == []
         and record.get('mainInputsUnchanged') is True and record.get('candidateInputsUnchanged') is True
         and record.get('trustedWorkerNotRepinned') is True
         and record.get('candidateEngine') == VERSION and record.get('baselineEngine') == '2022.3.62f3'
         and record.get('sourceAudit', {}).get('trustedWorkerSourcePinUnchanged') is True,
         'Exact 350-row cross-engine model comparison required')
    for key in ('accepted93Summary', 'baselineNativeReport', 'baselineInvocation', 'baselineSourceManifest',
                'baselineSourcesAfter', 'baselineUnityLog', 'candidateNativeReport', 'candidateInvocation',
                'candidateUnityLog', 'candidateSourcesBefore', 'candidateSourcesAfter'):
        validate_binding(record[key])
    need(files(read(ROOT / record['candidateSourcesAfter']['path'])) == candidate,
         'Model comparison does not bind current candidate')
    comparer = module('collect94_model_schema', 'compare_model94.py')
    need(record.get('runnerSHA256') == sha(HERE / 'compare_model94.py'), 'Model comparer changed')
    a, b = read(ROOT / record['baselineNativeReport']['path']), read(ROOT / record['candidateNativeReport']['path'])
    recalculated = comparer.compare_rows(a, b)
    need(all(record.get(key) == value for key, value in recalculated.items()), 'Actual model rows differ from comparison receipt')
    return {'passed': True, 'report': binding(path), 'rows': 350,
            'trustedWorkerNotRepinned': True,
            'scope': '350 sampled raw-turn/final-snapshot hashes only; not all actions/seeds, server deployment, pixels, or performance.'}


def build(path, baseline, candidate, development):
    static = module('collect94_build_schema', 'check_apk94.py')
    loaded = static.load_build(path)
    need(loaded['development'] is development, 'Explicit build role mismatch')
    native = loaded['native']
    operation = 'BuildDevelopment' if development else 'BuildNonDevelopment'
    row = verify_native(path, 'PASS_ISOLATED_UNITY6_94_' + operation.upper(),
        'HeartOfTheRain.Verification.Unity6Migration94.' + operation, baseline, candidate)
    row.pop('raw')
    need(native['after'].get('companyName') == 'HeartOfTheRainUnity6Review94', 'Editor data isolation company changed')
    profile_path = Path(path).parent / 'StaticApk94.json'
    profile = read(profile_path)
    required = ('zipCrcPass', 'signatureVerifies', 'zipAlignFourBytePass', 'elf16KiBLoadSegmentsPass',
        'storedNative16KiBAligned', 'abiArm64Only', 'packageMatchesNativeBuild', 'portraitActivity', 'minApi26',
        'developmentFlagMatches', 'sdkFreeDex', 'identityBridgePresent', 'sourcesUnchanged', 'apkUnchanged')
    need(profile.get('status') == 'PASS_INTERNAL_UNITY6_94_APK' and profile.get('errors') == []
         and profile.get('development') is development and profile.get('nonDevelopmentCompileOnly') is (not development)
         and profile.get('apk') == binding(loaded['apk']) and profile.get('nativeReport') == binding(path)
         and profile.get('buildInvocation') == row['invocation']
         and profile.get('candidateSources') == binding(loaded['candidateSources'])
         and profile.get('runner') == binding(HERE / 'check_apk94.py')
         and all(profile.get('checks', {}).get(key) is True for key in required), 'Actual current static APK checks required')
    for item in profile.get('artifacts', []):
        validate_binding(item, profile_path.parent / 'AndroidStatic94')
    need(len(profile.get('artifacts', [])) == 8, 'All eight bound static command streams required')
    row.update(apk=binding(loaded['apk']), staticReport=binding(profile_path), package=loaded['package'],
        development=development, nonDevelopmentCompileOnly=not development,
        finishedUtc=read(loaded['invocation'])['finishedUtc'],
        scope='Actual SDK-free ARM64 internal Android compilation and static artifact inspection. Debug signing; no provider or store-release acceptance. Non-development artifact must not be installed.')
    return row


def stable(snapshot):
    need(snapshot.get('activeAttempts') == 0, 'Ordinary active attempt must remain absent')
    return {key: snapshot[key] for key in ('profiles', 'preferences', 'profileSummaries', 'installedSHA256')}


def device(path, development, candidate):
    path = contained(path, OUT / 'Phone/Device01/Regression')
    need(path.name == 'Invocation.json', 'Explicit physical regression invocation required')
    record = read(path)
    need(record.get('status') == 'PASS_ISOLATED_PHYSICAL_TRANSIENT_REGRESSION94'
         and record.get('package') == 'com.heartoftherain.unity6review94'
         and record.get('unity') == VERSION and record.get('apk') == development['apk']
         and record.get('ownerMutation') is False and record.get('ownerDataUnchanged') is True
         and record.get('candidateDataUnchanged') is True and record.get('dataUnchangedAfterNormalRelaunch') is True
         and record.get('ownerPreservedAtExit') is True and record.get('finalMarkers') == [],
         'Passed save-preserving isolated physical regression required')
    for key in ('buildReport', 'buildInvocation', 'staticReport', 'nativeReport', 'atlasReport', 'captureInventory'):
        validate_binding(record[key])
    need(record['buildReport'] == development['report'] and record['staticReport'] == development['staticReport'],
         'Phone build/static identity differs')
    for key in ('sources', 'sourcesAfter'):
        source = record[key]
        validate_binding(source['mainManifest'])
        validate_binding(source['candidateSources'])
        need(files(read(ROOT / source['candidateSources']['path'])) == candidate, 'Phone candidate source changed')
    phone = module('collect94_physical_regression_schema', 'phone94.py')
    native = read(ROOT / record['nativeReport']['path'])
    phone.native_scope(native, VERSION)
    for stem in ('Owner', 'Candidate'):
        values = [stable(read(path.parent / (stem + suffix + '.json')))
                  for suffix in ('Before', 'After', 'AfterRelaunch')]
        need(values[0] == values[1] == values[2], 'Owner or ordinary candidate data changed')
    install_path = OUT / 'Phone/Device01/Installation.json'
    launch_path = OUT / 'Phone/Device01/Launch.json'
    installation, launch = read(install_path), read(launch_path)
    need(installation.get('status') == 'PASS_FRESH_SIDE_BY_SIDE_INSTALL94'
         and installation.get('apk') == development['apk'] and installation.get('ownerDataUnchanged') is True
         and launch.get('status') == 'RECORDED_ORDINARY_CANDIDATE_LAUNCH94_REQUIRES_VISUAL_REVIEW'
         and launch.get('apk') == development['apk'] and launch.get('ownerDataUnchanged') is True,
         'Actual side-by-side install and ordinary launch required')
    capture_inventory = read(ROOT / record['captureInventory']['path'])
    retained = [row for row in capture_inventory['files'] if row['retained']]
    need(len(retained) == capture_inventory.get('retainedPngCount') == 4
         and len(capture_inventory['files']) == capture_inventory.get('capturedPngCount'),
         'Physical capture retention inventory incomplete')
    for row in retained:
        actual = binding(ROOT / row['retainedEvidence'])
        need(actual['sha256'] == row['sha256'] and actual['bytes'] == row['bytes'], 'Physical retained image changed')
    log = record['fixtureAppLog']
    validate_binding(log['log'], path.parent)
    need(log.get('selectedErrorCount') == 0, 'Physical selected runtime errors remain')
    return {'passed': True, 'report': binding(path), 'installation': binding(install_path),
        'ordinaryLaunch': binding(launch_path), 'checks': native['checks'], 'boards': 50,
        'actions': 408, 'clips': 354, 'ownerDataUnchanged': True,
        'scope': 'Transient native fixture on the isolated side-by-side Android package; ordinary candidate/owner saves preserved through relaunch. Not human campaign or performance acceptance.'}


def validate_startup_inventory(publication, recording, privacy, private, selected, public_parent):
    """All private samples remain bound; publication is only four approved files."""
    public = publication['publishedArtifacts']
    need(publication.get('schemaVersion') == privacy.get('schemaVersion') == 2
         and len(private) == 47 and len(selected) == len(public) == 4
         and len({item['path'] for item in private}) == 47
         and len({item['path'] for item in selected}) == 4
         and len({item['path'] for item in public}) == 4
         and all(item in private for item in selected)
         and privacy.get('reviewedArtifacts') == selected
         and privacy.get('privateArtifactInventory') == private
         and publication.get('privateArtifactInventory') == private
         and publication.get('selectedPrivateArtifacts') == selected
         and publication.get('privateArtifactCount') == 47
         and publication.get('publishedArtifactCount') == 4
         and publication.get('unpublishedPrivateArtifactCount') == 43,
         'Exact schema-2 private 47/public 4 reviewed startup inventory required')
    token = recording.get('captureId', '')
    need(re.fullmatch(r'[0-9a-f]{32}', token) is not None, 'Bound startup capture identifier required')
    private_parent = ROOT / '.verification-cache/Unity6Migration94/ColdStart' / token
    for item in private:
        validate_binding(item, private_parent)
    for source, target in zip(selected, public):
        validate_binding(target, public_parent)
        need(source['sha256'] == target['sha256'] and source['bytes'] == target['bytes'],
             'Published startup artifact differs from reviewed source')
    return public


def coldstart(path, development):
    path = contained(path, OUT / 'Phone/Device01/ColdStart')
    need(path.name == 'Publication.json', 'Explicit privacy-reviewed cold-start publication required')
    publication = read(path)
    need(publication.get('status') == 'PUBLISHED_ROOT_PRIVACY_REVIEWED_CANDIDATE_COLD_START94', 'Cold-start publication incomplete')
    recording_path = validate_binding(publication['recording'], OUT / 'Phone/Device01/ColdStart')
    privacy_path = validate_binding(publication['rootPrivacyReview'], OUT / 'Phone/Device01/ColdStart')
    recording, privacy = read(recording_path), read(privacy_path)
    need(recording_path.parent.name == recording.get('captureId'), 'Startup recording capture directory differs')
    need(recording.get('status') == 'RECORDED_CANDIDATE_COLD_START94_REQUIRES_VISUAL_REVIEW'
         and recording.get('apk') == development['apk'] and recording.get('ownerMutation') is False
         and recording.get('ownerDataUnchanged') is True and recording.get('candidateDataUnchanged') is True
         and recording.get('ownerPreservedAtExit') is True and recording.get('candidatePreservedAtExit') is True
         and recording.get('finalCandidateMarkers') == []
         and privacy.get('status') == 'ROOT_REVIEWED_CANDIDATE_STARTUP_PRIVACY94'
         and privacy.get('reviewer') == 'root' and privacy.get('recording') == publication['recording']
         and privacy.get('approvedForPublication') is True and privacy.get('noUnrelatedPersonalContent') is True,
         'Bound root privacy review and unchanged data required')
    capture = module('collect94_startup_inventory_schema', 'cold_start94.py')
    private = capture.publication_artifacts(recording)
    selected = capture.selected_publication_artifacts(recording)
    public = validate_startup_inventory(publication, recording, privacy, private, selected, path.parent)
    return {'passed': True, 'publication': binding(path), 'recording': publication['recording'],
        'privacyReview': publication['rootPrivacyReview'], 'publishedArtifacts': public,
        'videoSeconds': 20, 'privateArtifactCount': 47, 'publishedArtifactCount': 4,
        'unpublishedPrivateArtifactCount': 43,
        'scope': 'Actual initialized-candidate restart recording with all 47 private artifacts hash-validated; only the original video, two contact sheets and final representative frame are published after root privacy review. No individual full-resolution review of all 44 frames, startup SLA or automatic splash-absence claim.'}


def visual_review(path, source, development, cold, native, effect):
    path = contained(path)
    record = read(path)
    need(record.get('status') == 'ROOT_REVIEWED_ISOLATED_UNITY6_94_VISUALS'
         and record.get('reviewer') == 'root' and record.get('candidateSources') == source['candidateSources']
         and record.get('developmentApk') == development['apk']
         and record.get('startupPublication') == cold['publication']
         and record.get('sampledStartupShowsNoUnitySplash') is True,
         'Explicit bound root visual/startup assessment required')
    rows = record.get('artifacts', [])
    need(isinstance(rows, list) and rows and len({item['artifact']['path'] for item in rows}) == len(rows),
         'Unique explicitly reviewed visual artifacts required')
    counts = {}
    native_roots = [(ROOT / row['report']['path']).parent for row in native['selected']]
    for row in rows:
        kind = row.get('kind')
        need(row.get('passed') is True and isinstance(row.get('scope'), str) and row['scope']
             and isinstance(row.get('name'), str), 'Every displayed image requires actual root assessment and scope')
        image = validate_binding(row['artifact'], OUT)
        if kind == 'native-effect':
            effect_report = ROOT / effect['report']['path']
            need(image.parent == effect_report.parent and image.name in read(effect_report).get('frames', []),
                 'Native effect image from wrong invocation or undeclared frame')
        elif kind == 'native-ui':
            need(any(image.is_relative_to(parent) for parent in native_roots), 'Native UI image from unselected suite')
        elif kind == 'android-os':
            need(image.parent == OUT / 'Phone/Device01/Screens', 'Actual phone image must have its capture receipt')
            capture = read(image.with_suffix('.json'))
            need(capture.get('status') == 'RECORDED_ACTUAL_CANDIDATE_OS_FRAME94_REQUIRES_VISUAL_REVIEW'
                 and capture.get('kind') == 'ACTUAL_ANDROID_OS_FRAMEBUFFER'
                 and capture.get('png') == row['artifact'] and capture.get('apk') == development['apk']
                 and capture.get('ownerDataUnchanged') is True, 'Actual OS capture binding differs')
        elif kind == 'android-native-fixture':
            need(image.is_relative_to(OUT / 'Phone/Device01/Regression') and image.suffix == '.png', 'Wrong device fixture image scope')
        elif kind in ('startup-contact-sheet', 'startup-video'):
            need(row['artifact'] in cold['publishedArtifacts'], 'Startup media lacks privacy-reviewed publication')
        else:
            raise ValueError('Unrecognized explicit visual evidence kind')
        need(image.suffix.lower() == ('.mp4' if kind == 'startup-video' else '.png'), 'Visual media type differs')
        counts[kind] = counts.get(kind, 0) + 1
    need(counts.get('native-effect', 0) >= 2 and counts.get('native-ui', 0) >= 1
         and counts.get('android-os', 0) >= 1 and counts.get('startup-contact-sheet', 0) >= 1,
         'Two effects plus selected UI, actual OS and published startup samples must be reviewed')
    return {'passed': True, 'report': binding(path), 'counts': counts, 'artifacts': rows,
            'sampledStartupShowsNoUnitySplash': True,
            'scope': 'Only the explicitly named source images/video samples were reviewed. No claim that all generated frames, devices or features were visually inspected.'}


def html_page(record, directory):
    def link(item, label):
        target = ROOT / item['path']
        relative = Path(os.path.relpath(target, directory)).as_posix()
        return '<a href="' + html.escape(relative, quote=True) + '">' + html.escape(label) + '</a>'
    rows = []
    for name, component in record['components'].items():
        item = component.get('report') or component.get('publication')
        label = link(item, name) if isinstance(item, dict) and 'path' in item else html.escape(name)
        rows.append('<tr><td>' + label + '</td><td>' + html.escape('PASS within declared scope' if component.get('passed') else 'INCOMPLETE') + '</td><td>' + html.escape(component.get('scope', 'Bound source/assessment evidence only.')) + '</td></tr>')
    gallery = []
    visual = record['components'].get('visualReview', {})
    for item in visual.get('artifacts', []):
        relative = Path(os.path.relpath(ROOT / item['artifact']['path'], directory)).as_posix()
        url = html.escape(relative, quote=True)
        media = ('<video controls preload="metadata" src="' + url + '"></video>'
                 if item['kind'] == 'startup-video' else '<a href="' + url + '"><img loading="lazy" src="' + url + '" alt="' + html.escape(item['name'], quote=True) + '"></a>')
        gallery.append('<figure>' + media + '<figcaption><strong>' + html.escape(item['name']) + '</strong> · ' + html.escape(item['kind']) + '<p>' + html.escape(item['scope']) + '</p></figcaption></figure>')
    failures = ''.join('<li>' + html.escape(item['component'] + ': ' + item['reason']) + '</li>' for item in record['issues'])
    gates = ''.join('<li>' + html.escape(item) + '</li>' for item in record['openGates'])
    selected_rows = []
    native = record['components'].get('native', {})
    for row in native.get('selected', []):
        result = 'PASS selected native invocation' if row['passed'] else 'FAIL retained diagnostic; unresolved'
        selected_rows.append('<tr><td>' + link(row['report'], row['name']) + '</td><td>' + html.escape(result) + '</td><td>' + html.escape(str(row.get('attemptedChecks'))) + '</td></tr>')
    retained = ''.join('<li>' + link(row['invocation'], row['name']) + ': ' + html.escape(str(row.get('invocationStatus'))) + ' / ' + html.escape(str(row.get('nativeStatus'))) + '</li>' for row in native.get('retainedUnselectedOrDiagnosticFailures', []))
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Isolated Unity 6 splash review 94</title><style>body{font:16px system-ui;background:#101e2a;color:#f5f2e7;margin:24px auto;max-width:1200px;padding:0 18px}a{color:#82cff5}table{border-collapse:collapse;width:100%}td,th{border:1px solid #496273;padding:10px;text-align:left;vertical-align:top}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}figure{margin:0;background:#1c3547;padding:12px;border-radius:10px}img,video{width:100%;height:auto;max-height:780px;object-fit:contain}figcaption p{font-size:14px}li{margin:8px 0}</style>'
        '<h1>Isolated Unity 6 splash review 94</h1><p><strong>' + html.escape(record['status']) + '</strong></p>'
        '<p>The ordinary Unity 2022 project, backend worker and owner app remain separate. This page records an isolated candidate; it does not approve main promotion, production release or whole-game smoothness.</p>'
        '<table><thead><tr><th>Evidence</th><th>Result</th><th>Scope</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
        + ('<h2>Selected native suites</h2><table><tr><th>Suite</th><th>Result</th><th>Actual attempted checks</th></tr>' + ''.join(selected_rows) + '</table>' if selected_rows else '')
        + ('<h2>Retained original failures</h2><ul>' + retained + '</ul>' if retained else '')
        + ('<h2>Incomplete or failed evidence</h2><ul>' + failures + '</ul>' if failures else '')
        + '<h2>Explicitly reviewed media</h2><div class="gallery">' + ''.join(gallery) + '</div>'
        + '<h2>Remaining gates</h2><ul>' + gates + '</ul></html>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='Fresh child under checkpoint94/Publication')
    parser.add_argument('--publish', action='store_true')
    for name in ('environment', 'config', 'batch', 'effects', 'dense', 'model', 'source', 'builddev', 'buildnondev'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--native', type=Path, action='append', required=True)
    parser.add_argument('--select-native', action='append', default=[])
    parser.add_argument('--source-review', type=Path)
    parser.add_argument('--visual-review', type=Path)
    parser.add_argument('--device', type=Path, help='Explicit physical regression Invocation.json')
    parser.add_argument('--coldstart', type=Path, help='Explicit published startup Publication.json')
    args = parser.parse_args()
    directory = contained(args.out, OUT / 'Publication')
    need(directory != (OUT / 'Publication').resolve() and not directory.exists(), 'Fresh unique publication output required')
    directory.mkdir(parents=True, exist_ok=False)
    preparation = read(OUT / 'Preparation.json')
    baseline_record = read(OUT / 'MainSources_Before.json')
    baseline = files(baseline_record)
    record = {'schemaVersion': 1, 'checkpoint': 94, 'status': 'INCOMPLETE_ISOLATED_UNITY6_REVIEW94',
        'startedUtc': utc(), 'collector': binding(__file__), 'candidateUnity': VERSION,
        'mainUnity': '2022.3.62f3', 'mainPromoted': False, 'productionApproved': False,
        'wholeGameSmoothnessApproved': False, 'components': {}, 'issues': [], 'openGates': list(OPEN_GATES),
        'scope': 'Explicit current-source isolated migration/settings, selected native controls, internal APKs and reviewed phone/startup evidence only. No main-project replacement or production approval.'}

    def collect(name, call):
        try:
            value = call()
            record['components'][name] = value
            return value
        except Exception as error:
            reason = 'Required artifact missing' if isinstance(error, FileNotFoundError) else (str(error) if isinstance(error, ValueError) else type(error).__name__)
            record['issues'].append({'component': name, 'reason': reason})
            record['components'][name] = {'passed': False, 'scope': 'Incomplete; no acceptance inferred.'}
            return None

    collect('environment', lambda: environment(args.environment))
    source_pair = collect('source', lambda: verify_source(args.source, preparation, baseline))
    candidate = None
    if source_pair:
        source, candidate = source_pair
        record['components']['source'] = source
    if candidate is not None:
        source_review_result = collect('sourceReview', lambda: source_review(args.source_review, source)) if args.source_review else None
        if not args.source_review:
            record['issues'].append({'component': 'sourceReview', 'reason': 'Explicit root source/settings review missing'})
        native = collect('native', lambda: native_suites(args.native, args.select_native, baseline, candidate))
        collect('config', lambda: configuration(args.config, baseline, candidate))
        collect('batch', lambda: batch_keys(args.batch, baseline, candidate))
        effect = collect('effects', lambda: effects(args.effects, baseline, candidate))
        collect('dense', lambda: dense(args.dense, baseline, candidate))
        collect('model', lambda: model(args.model, candidate))
        development = collect('buildDevelopment', lambda: build(args.builddev, baseline, candidate, True))
        nondevelopment = collect('buildNonDevelopment', lambda: build(args.buildnondev, baseline, candidate, False))
        if development and nondevelopment:
            if development['finishedUtc'] < nondevelopment['finishedUtc']:
                record['issues'].append({'component': 'buildOrder', 'reason': 'Development build must be last'})
        physical = collect('device', lambda: device(args.device, development, candidate)) if args.device and development else None
        if not physical:
            record['issues'].append({'component': 'device', 'reason': 'Completed current isolated physical regression missing'})
        startup = collect('coldstart', lambda: coldstart(args.coldstart, development)) if args.coldstart and development else None
        if not startup:
            record['issues'].append({'component': 'coldstart', 'reason': 'Published root privacy-reviewed startup recording missing'})
        if args.visual_review and all((development, startup, native, effect)):
            collect('visualReview', lambda: visual_review(args.visual_review, source, development, startup, native, effect))
        else:
            record['issues'].append({'component': 'visualReview', 'reason': 'Explicit bound root visual assessment or its prerequisites missing'})
        def current_preservation():
            auditor = module('collect94_current_source_auditor', 'audit_candidate94.py')
            need(files(auditor.inventory(ROOT / 'Unity', 'Unity/')) == baseline
                 and files(auditor.inventory(PROJECT)) == candidate, 'Current main/candidate sources changed since selected evidence')
            backend = auditor.audit_backend(preparation['baselineCommit'])
            need(backend.get('unchanged') is True, 'Backend source changed since source audit')
            return {'passed': True, 'mainInputs': 5407, 'backendSourceUnchanged': True,
                    'scope': 'Current main and candidate bytes rehashed; Backend current HEAD blobs/baseline tree compared. No runtime tests performed by this collector.'}
        collect('preservation', current_preservation)
    need(len(baseline) == 5407 and sha(OUT / 'MainSources_Before.json') == preparation['mainManifestSHA256']
         and sha(ROOT / 'Verification/Evidence/Review93/Summary.json') == preparation['accepted93SummarySHA256'],
         'Protected baseline or accepted Review93 summary changed')
    record['accepted93Summary'] = binding(ROOT / 'Verification/Evidence/Review93/Summary.json')
    record['preparation'] = binding(OUT / 'Preparation.json')
    record['mainBaseline'] = binding(OUT / 'MainSources_Before.json')
    record['status'] = completed_status(record['components'], record['issues'])
    record['finishedUtc'] = utc()
    record['published'] = bool(args.publish and record['status'] == COMPLETE)
    path = directory / ('Summary.json' if record['published'] else 'Draft.json')
    write_new(path, record)
    with (directory / 'Comparison.html').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(html_page(record, directory))
    print(json.dumps({'status': record['status'], 'published': record['published'],
                      'issues': len(record['issues']), 'report': path.relative_to(ROOT).as_posix()}), flush=True)
    return 0 if record['published'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
