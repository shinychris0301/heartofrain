"""Root opt-in read-only comparison of350 accepted2022 and actual6000 model rows."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Unity6Migration94'
PROJECT = ROOT / '.verification-cache/Unity6Migration94/Project'
BASELINE = ROOT / 'Verification/Evidence/Review93/Native/Set01/Cascade/LocalCascade.json'
SUMMARY = ROOT / 'Verification/Evidence/Review93/Summary.json'
ACCEPTED_SUMMARY_SHA = 'e6b761f46bd57a6d7b0c3c69a0cf00a3411fad4c700ce31e44598199a9432cfd'
BASELINE_REPORT_SHA = '4b95138a03c17337df458d766925844825ce8cdb046a6ae5ff50a9a74bf77dbb'
VERSION = '6000.6.6f1'
ENTRY = 'HeartOfTheRain.Verification.LocalCascadeVerification.Run'
HASH_FIELDS = ('turnHash', 'finalHash')
EXTRA_FIELDS = ('sequentialTurnHash', 'refinedTurnHash', 'sequentialFinalHash', 'refinedFinalHash')
WORKER_SOURCE = 'Assets/HeartOfTheRain/App/ServerVerification/Runtime/PinnedReplayEngine.cs'


def need(condition, code):
    if not condition:
        raise ValueError(code)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def binding(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT), 'Model94BoundWorkspacePathRequired')
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path), 'bytes': path.stat().st_size}


def bound_matches(path, expected):
    need(binding(path) == expected, 'Model94HistoricalBoundArtifactChanged')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def expected_names():
    return {'L' + str(level) + '_' + suffix for level in range(1, 51)
            for suffix in ('match', 'power4', 'power5', 'power7', 'power11', 'power16', 'power21')}


def validate_rows(report):
    need(isinstance(report, dict) and report.get('status') == 'PASS_NATIVE_LOCAL_CASCADE73'
         and report.get('errors') == [] and report.get('rawTurnParity') is True
         and report.get('finalSnapshotParity') is True and report.get('modelCases') == 350
         and type(report.get('checks')) is int and report['checks'] > 0, 'Model94PassedNativeModelCorpusRequired')
    rows = report.get('rows')
    need(isinstance(rows, list) and len(rows) == 350, 'Model94Exactly350RowsRequired')
    names = [row.get('name') if isinstance(row, dict) else None for row in rows]
    need(all(isinstance(name, str) for name in names) and len(set(names)) == 350, 'Model94Unique350RowNamesRequired')
    need(set(names) == expected_names(), 'Model94Exact50BySevenCorpusRequired')
    for row in rows:
        need(all(isinstance(row.get(field), str) and re.fullmatch(r'[a-f0-9]{64}', row[field]) is not None
                 for field in (*HASH_FIELDS, *EXTRA_FIELDS)), 'Model94FullRawHashFieldsRequired')
    return {row['name']: row for row in rows}


def compare_rows(baseline, candidate):
    left, right = validate_rows(baseline), validate_rows(candidate)
    rows, differences, supplemental = [], [], []
    for level in range(1, 51):
        for suffix in ('match', 'power4', 'power5', 'power7', 'power11', 'power16', 'power21'):
            name = 'L' + str(level) + '_' + suffix
            a, b = left[name], right[name]
            detail = {'name': name, 'rawTurnEqual': a['turnHash'] == b['turnHash'],
                      'finalSnapshotEqual': a['finalHash'] == b['finalHash'],
                      'baselineTurnHash': a['turnHash'], 'candidateTurnHash': b['turnHash'],
                      'baselineFinalHash': a['finalHash'], 'candidateFinalHash': b['finalHash']}
            rows.append(detail)
            if not detail['rawTurnEqual'] or not detail['finalSnapshotEqual']:
                differences.append(detail)
            changed = {field: {'baseline': a[field], 'candidate': b[field]}
                       for field in EXTRA_FIELDS if a[field] != b[field]}
            if changed:
                supplemental.append({'name': name, 'fields': changed})
    return {'rows': rows, 'differences': differences, 'supplementalPlannerHashDifferences': supplemental,
            'comparedRows': len(rows), 'rawTurnMatches': sum(row['rawTurnEqual'] for row in rows),
            'finalSnapshotMatches': sum(row['finalSnapshotEqual'] for row in rows),
            'all350RawTurnsAndFinalSnapshotsEqual': not differences}


def validate_candidate_invocation(invocation, report, report_path, log):
    need(invocation.get('status') == 'PASS_ISOLATED_UNITY6_94_NATIVE' and invocation.get('exitCode') == 0
         and invocation.get('entry') == ENTRY and invocation.get('expectedVersion') == VERSION
         and invocation.get('actualEngineVersionFromProcessLog') == VERSION
         and invocation.get('legacyReportWithoutUnityField') is True
         and invocation.get('mainInputsUnchanged') is True and invocation.get('unityPidsAfter') == []
         and invocation.get('nativeStatus') == 'PASS_NATIVE_LOCAL_CASCADE73'
         and invocation.get('nativeReportSHA256') == digest(report_path)
         and invocation.get('nativeReport') == report_path.resolve().relative_to(ROOT).as_posix()
         and invocation.get('unityLogSHA256') == digest(log), 'Model94PassedBoundCandidateProcessRequired')
    match = re.search(r'Initialize engine version:\s*(\S+)', Path(log).read_text('utf-8-sig', errors='replace'))
    need(match is not None and match.group(1) == VERSION and 'unity' not in report,
         'Model94ActualCandidateEngineAndLegacySchemaRequired')


def validate_baseline():
    preparation = read(OUT / 'Preparation.json')
    need(preparation.get('status') == 'PASS_EXACT_MAIN_COPY94'
         and preparation.get('accepted93SummarySHA256') == ACCEPTED_SUMMARY_SHA
         and digest(SUMMARY) == ACCEPTED_SUMMARY_SHA, 'Model94AcceptedHistorical93SummaryChanged')
    summary = read(SUMMARY)
    rows = [row for row in summary['components']['native']['suites'] if row.get('name') == 'Cascade']
    need(len(rows) == 1 and rows[0].get('passed') is True, 'Model94AcceptedHistoricalCascadeRequired')
    accepted = rows[0]
    invocation_path = BASELINE.parent / 'Invocation.json'
    bound_matches(BASELINE, accepted['report'])
    bound_matches(invocation_path, accepted['invocation'])
    need(digest(BASELINE) == BASELINE_REPORT_SHA, 'Model94HistoricalRawNativeReportChanged')
    invocation = read(invocation_path)
    sources = BASELINE.parent / 'FrozenSources.json'
    after = BASELINE.parent / 'Sources_after.json'
    log = BASELINE.parent / 'Unity.log'
    need(invocation.get('status') == 'PASS_NATIVE_REVIEW93_INVOCATION' and invocation.get('entry') == ENTRY
         and invocation.get('exitCode') == 0 and invocation.get('inputsUnchanged') is True
         and invocation.get('unityPidsAfter') == [] and invocation.get('nativeReportSHA256') == digest(BASELINE)
         and invocation.get('sourceSHA256') == digest(sources) and invocation.get('inputCount') == 5407
         and invocation.get('unityLogSHA256') == digest(log), 'Model94HistoricalNativeProcessOrSourceChanged')
    before = read(sources)
    need(before == read(after) == read(OUT / 'MainSources_Before.json')
         and preparation.get('mainManifestSHA256') == digest(sources), 'Model94HistoricalSourceManifestChanged')
    version = re.search(r'Initialize engine version:\s*(\S+)', log.read_text('utf-8-sig', errors='replace'))
    need(version is not None and version.group(1) == '2022.3.62f3', 'Model94Historical2022ProcessRequired')
    native = read(BASELINE)
    validate_rows(native)
    return native, before, {'accepted93Summary': binding(SUMMARY), 'baselineNativeReport': binding(BASELINE),
                           'baselineInvocation': binding(invocation_path), 'baselineSourceManifest': binding(sources),
                           'baselineSourcesAfter': binding(after), 'baselineUnityLog': binding(log),
                           'baselineEngine': '2022.3.62f3'}


def verify_unchanged_model_sources(main, candidate):
    prefixes = ('Assets/HeartOfTheRain/M46/Runtime/', 'Assets/HeartOfTheRain/M48/Runtime/',
                'Assets/HeartOfTheRain/Boosters/Runtime/')
    files = main['files']
    paths = sorted(path.removeprefix('Unity/') for path in files
                   if path.startswith('Unity/') and path.endswith('.cs')
                   and path.removeprefix('Unity/').startswith(prefixes))
    need(len(paths) >= 10, 'Model94BoundCoreSourceSetRequired')
    rows = []
    for relative in paths + [WORKER_SOURCE]:
        expected = files['Unity/' + relative]
        source, actual = ROOT / 'Unity' / relative, PROJECT / relative
        need(source.is_file() and actual.is_file() and digest(source) == digest(actual) == expected['sha256']
             and source.stat().st_size == actual.stat().st_size == expected['bytes']
             and candidate['files'].get(relative) == expected, 'Model94CoreOrTrustedWorkerSourceChanged')
        rows.append({'path': relative, **expected})
    worker = (ROOT / 'Unity' / WORKER_SOURCE).read_text('utf-8-sig')
    need('pins.unity!="2022.3.62f3"' in worker and 'Application.unityVersion=="2022.3.62f3"' in worker,
         'Model94TrustedWorker2022PinMustRemain')
    return {'sourceFiles': rows, 'modelRuntimeFiles': len(paths), 'trustedWorkerSourcePinUnchanged': True,
            'scope': 'Current main/candidate M46, M48 and Booster Runtime C# files match the accepted2022 manifest byte-for-byte; trusted replay source still rejects non2022. This is a source audit, not a new deployed worker/backend invocation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt':
        parser.error('Explicit root Windows read-only collection required')
    candidate_path = args.candidate.resolve()
    need(candidate_path.is_relative_to(OUT / 'Native') and candidate_path.name == 'LocalCascade.json',
         'Model94CandidateNativeCorpusPathRequired')
    api = module('model94_source_reader', ROOT / 'Verification/Tools/Ads85/run_ads85_native.py')
    runner = module('model94_candidate_source_reader', Path(__file__).with_name('run_native.py'))
    baseline, main_sources, historical = validate_baseline()
    invocation_path = candidate_path.parent / 'Invocation.json'
    invocation = read(invocation_path)
    native = read(candidate_path)
    validate_candidate_invocation(invocation, native, candidate_path, candidate_path.parent / 'Unity.log')
    before_path, after_path = candidate_path.parent / 'CandidateSources_before.json', candidate_path.parent / 'CandidateSources_after.json'
    candidate_sources = read(after_path)
    need(candidate_sources == read(before_path) == runner.candidate_sources(api), 'Model94CandidateSourceDriftSinceNativeRun')
    need(read(candidate_path.parent / 'MainSources_before.json') == read(candidate_path.parent / 'MainSources_after.json')
         == main_sources == api.freeze(), 'Model94MainSourceDriftSinceNativeRun')
    source_audit = verify_unchanged_model_sources(main_sources, candidate_sources)
    directory = OUT / 'ModelParity' / uuid.uuid4().hex
    directory.mkdir(parents=True, exist_ok=False)
    record = {'schemaVersion': 1, 'status': 'RUNNING_CROSS_ENGINE_MODEL_CORPUS94', 'startedUtc': api.utc(),
              'runnerSHA256': digest(Path(__file__)), **historical,
              'candidateNativeReport': binding(candidate_path), 'candidateInvocation': binding(invocation_path),
              'candidateUnityLog': binding(candidate_path.parent / 'Unity.log'),
              'candidateSourcesBefore': binding(before_path), 'candidateSourcesAfter': binding(after_path),
              'candidateEngine': VERSION, 'sourceAudit': source_audit,
              'scope': 'Read-only exact raw turn/final snapshot SHA256 comparison of350 sampled commands:50 authored boards times one natural match and six injected powers. Both original2022 and actual6000 native processes/source manifests are bound. Zero hash differences are waived. Same sampled corpus only; not every possible board/seed/action, server transaction/Continue/tool chain, backend acceptance, cross-engine pixels, performance or production certification. Trusted backend worker remains pinned2022 and is not rebuilt or executed.'}
    api.write(directory / 'Authorization.json', record)
    record.update(compare_rows(baseline, native))
    need(api.freeze() == main_sources and runner.candidate_sources(api) == candidate_sources,
         'Model94SourcesChangedWhileComparing')
    record.update(status='PASS_CROSS_ENGINE_350_MODEL_ROWS94' if record['all350RawTurnsAndFinalSnapshotsEqual']
                  else 'FAIL_CROSS_ENGINE_MODEL_HASH_DIFFERENCES94', completedUtc=api.utc(), mainInputsUnchanged=True,
                  candidateInputsUnchanged=True, trustedWorkerNotRepinned=True)
    api.write(directory / 'Comparison.json', record)
    print(json.dumps({'status': record['status'], 'rows': record['comparedRows'],
                      'rawTurnMatches': record['rawTurnMatches'], 'finalSnapshotMatches': record['finalSnapshotMatches'],
                      'differences': len(record['differences']),
                      'report': (directory / 'Comparison.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
