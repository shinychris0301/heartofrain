"""Root opt-in serial actual native suites in the approved isolated Unity6 copy."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'Verification/Evidence/Unity6Migration94'
VERSION = '6000.6.6f1'
ACCOUNT_DIAGNOSTIC = {
    'name': 'Account', 'entry': 'HeartOfTheRain.Verification.ServerAccount83Verification.Run',
    'report': 'Native/AccountContracts.json', 'expected': 'PASS_NATIVE_SERVER_ACCOUNT83_CONTRACTS',
    'environment': 'HOTR_SERVER_GAMEPLAY_OUTPUT', 'timeoutSeconds': 480, 'quit': False,
    'reportHasUnity': True, 'checksShape': 'integer', 'diagnosticOnly': True,
    'scope': 'Separate strict Account UI/encrypted-selection diagnostic. Previous2022 clipboard failures are retained as failures; neither they nor a passing repeat establish Android Account acceptance.'}
ACCOUNT_CLIPBOARD_ERROR = ('approved_modal_code_is_clipboard_only_and_actions_are_confirmed: '
                           'InvalidOperationException: explicit Copy real clipboard readback matches')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_delta(before, after):
    left, right = before['files'], after['files']
    return {'added': sorted(set(right) - set(left)), 'removed': sorted(set(left) - set(right)),
            'changed': sorted(key for key in set(left) & set(right) if left[key] != right[key])}


def unchanged(delta):
    return not any(delta.values())


def select_cases(configuration, only=None, account=False):
    required = configuration['cases']
    optional = configuration.get('optionalCases', [])
    available = required + optional + [ACCOUNT_DIAGNOSTIC]
    if (configuration.get('candidateUnity') != VERSION or len(required) != 9
            or len({case['name'] for case in available}) != len(available)):
        raise ValueError('ExactFocusedSuitePlanRequired')
    if only:
        names = only.split(',')
        if len(set(names)) != len(names) or any(name not in {row['name'] for row in available} for name in names):
            raise ValueError('UniqueConfiguredSuiteNamesRequired')
        chosen = [dict(case) for case in available if case['name'] in names]
    else:
        chosen = [dict(case) for case in required]
    if account and not any(row['name'] == 'Account' for row in chosen):
        chosen.append(dict(ACCOUNT_DIAGNOSTIC))
    for row in chosen:
        row.setdefault('diagnosticOnly', False)
        if (not re.fullmatch(r'[A-Za-z][A-Za-z0-9]+', row['name'])
                or not re.fullmatch(r'HeartOfTheRain\.[A-Za-z0-9_.]+', row['entry'])
                or not re.fullmatch(r'HOTR_[A-Z0-9_]+', row['environment'])
                or not 30 <= row['timeoutSeconds'] <= 900
                or type(row['reportHasUnity']) is not bool):
            raise ValueError('ExplicitBoundedSuiteSchemaRequired')
        relative = Path(row['report'])
        if relative.is_absolute() or '..' in relative.parts or relative.suffix != '.json':
            raise ValueError('ContainedNativeReportRequired')
    return chosen


def count_native(report, case):
    """Preserve actual counters; do not infer passed numeric assertions in a fail."""
    if not isinstance(report, dict):
        raise ValueError('NativeReportMustBeObject')
    raw = report.get('checks')
    if case['checksShape'] == 'array':
        if (not isinstance(raw, list) or not raw
                or any(not isinstance(row, dict) or row.get('status') not in ('PASS', 'FAIL') for row in raw)):
            raise ValueError('ActualNativeCheckArrayRequired')
        passed = sum(row['status'] == 'PASS' for row in raw)
        failed = sum(row['status'] == 'FAIL' for row in raw)
        if type(report.get('passed')) is not int or type(report.get('failed')) is not int or report['passed'] != passed or report['failed'] != failed:
            raise ValueError('NativeArrayCountersMismatch')
        return {'attemptedChecks': len(raw), 'explicitPassedChecks': passed, 'explicitFailedChecks': failed,
                'counterKind': 'actual-array'}
    if case['checksShape'] == 'integer':
        if type(raw) is not int or raw < 1:
            raise ValueError('PositiveActualNativeCheckCountRequired')
        return {'attemptedChecks': raw, 'counterKind': 'actual-integer',
                'passedCountInferred': False}
    if 'checks' in report:
        raise ValueError('UnexpectedUnconfiguredCheckCounter')
    if case['name'] != 'LoadingLifetime' or type(report.get('cycles')) is not int:
        raise ValueError('ExplicitKnownCounterlessReportRequired')
    return {'attemptedChecks': None, 'counterKind': 'absent-known-lifetime-schema',
            'actualCycles': report['cycles']}


def native_passed(report, case):
    if report.get('status') != case['expected']:
        return False
    if case['reportHasUnity']:
        if report.get('unity') != VERSION:
            return False
    elif 'unity' in report:
        return False
    if any(report.get(key) for key in ('error', 'errors', 'failures', 'failed')):
        return False
    if case['name'] == 'LoadingLifetime':
        return all(report.get(key) is True for key in ('staleRecoveryIgnored', 'rainCupFocus', 'accountRetryFocus', 'resourcesBound'))
    return True


def account_classification(report, case):
    if not case.get('diagnosticOnly'):
        return None
    if native_passed(report, case):
        return 'PASS_STRICT_ACCOUNT_DIAGNOSTIC_ONLY'
    if (report.get('status') == 'FAIL_NATIVE_SERVER_ACCOUNT83_CONTRACTS'
            and report.get('unity') == VERSION and report.get('errors') == [ACCOUNT_CLIPBOARD_ERROR]
            and report.get('clipboardReadbackMatched') is False):
        return 'RETAINED_FAIL_ACCOUNT_CLIPBOARD_ACCEPTANCE_UNRESOLVED'
    return 'RETAINED_UNCLASSIFIED_ACCOUNT_DIAGNOSTIC_FAILURE'


def summarize(runs, selected, preservation_ok, completed):
    required = [row for row in runs if not row['diagnosticOnly']]
    diagnostics = [row for row in runs if row['diagnosticOnly']]
    requested_required = [row for row in selected if not row['diagnosticOnly']]
    required_pass = bool(requested_required) and len(required) == len(requested_required) and all(row['acceptedNativePass'] for row in required)
    diagnostic_failures = sum(not row['acceptedNativePass'] for row in diagnostics)
    if not preservation_ok:
        status = 'FAIL_ISOLATED_SUITESET94_SOURCE_OR_PROCESS_PRESERVATION'
    elif not completed:
        status = 'INCOMPLETE_ISOLATED_SUITESET94'
    elif not requested_required:
        status = 'COMPLETED_DIAGNOSTIC_ONLY94_WITH_FAILURES' if diagnostic_failures else 'COMPLETED_DIAGNOSTIC_ONLY94'
    elif not required_pass:
        status = 'FAIL_ISOLATED_FOCUSED_NATIVE_SUITES94'
    elif diagnostic_failures:
        status = 'COMPLETED_FOCUSED_NATIVE_SUITES94_WITH_RETAINED_DIAGNOSTIC_FAILURES'
    else:
        status = 'PASS_ISOLATED_FOCUSED_NATIVE_SUITES94'
    return {'status': status, 'requiredSuitesPassed': required_pass,
            'requiredSuitesRequested': len(requested_required),
            'requiredSuitesExecuted': len(required), 'requiredSuitesPassing': sum(row['acceptedNativePass'] for row in required),
            'requiredSuitesFailing': sum(not row['acceptedNativePass'] for row in required),
            'requiredPassingChecks': sum(row.get('attemptedChecks') or 0 for row in required if row['acceptedNativePass']),
            'requiredAttemptedChecksInFailedSuites': sum(row.get('attemptedChecks') or 0 for row in required if not row['acceptedNativePass']),
            'diagnosticSuitesExecuted': len(diagnostics), 'diagnosticSuitesFailing': diagnostic_failures,
            'diagnosticAttemptedChecks': sum(row.get('attemptedChecks') or 0 for row in diagnostics)}


def write_progress(api, output, record):
    """Immutable per-case snapshots; never overwrite the final suite receipt."""
    count = len(record['runs'])
    if count < 1 or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]+', record['runs'][-1]['name']):
        raise ValueError('CompletedNamedCaseRequiredForProgress')
    path = Path(output) / 'Progress' / (f'{count:04d}_' + record['runs'][-1]['name'] + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    api.write(path, record)
    return path


def write_final(api, output, record):
    # The shared writer deliberately uses exclusive creation. A second final
    # write is an error and must preserve the original receipt.
    path = Path(output) / 'SuiteSet.json'
    api.write(path, record)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--only', help='Unique comma-separated configured cases for an explicit focused repeat.')
    parser.add_argument('--account-diagnostic', action='store_true')
    parser.add_argument('--set-id', help='Optional fresh32-character UUID hex folder; otherwise generated.')
    args = parser.parse_args()
    if not args.execute or os.name != 'nt':
        parser.error('Explicit root Windows execution required')
    set_id = args.set_id or uuid.uuid4().hex
    if not re.fullmatch(r'[0-9a-f]{32}', set_id):
        parser.error('Fresh lowercase32-character UUID hex required')
    configuration_path = HERE / 'suites94.json'
    configuration = json.loads(configuration_path.read_text('utf-8-sig'))
    selected = select_cases(configuration, args.only, args.account_diagnostic)
    native = module('migration94_serial_native_runner', HERE / 'run_native.py')
    api = module('migration94_serial_source_reader', ROOT / 'Verification/Tools/Ads85/run_ads85_native.py')
    sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
    processes = module('migration94_serial_process_reader', ROOT / 'Verification/Tools/PageBackdrop90/process90.py')
    if processes.unity_pids() or not native.EDITOR.is_file() or not native.PROJECT.is_dir():
        parser.error('Prepared isolated Editor/project and no running Unity required')
    version = (native.PROJECT / 'ProjectSettings/ProjectVersion.txt').read_text('utf-8-sig')
    if not re.search(r'^m_EditorVersion:\s*6000\.6\.6f1\s*$', version, re.MULTILINE):
        parser.error('Candidate must already be imported/configured with exact6000.6.6f1')
    before_main = api.freeze()
    if before_main != json.loads((OUT / 'MainSources_Before.json').read_text('utf-8-sig')):
        parser.error('Main inputs must equal the approved5407-input baseline')
    output = native.fresh_child(OUT / 'Native' / set_id, OUT / 'Native')
    output.mkdir(parents=True, exist_ok=False)
    before_candidate = native.candidate_sources(api)
    api.write(output / 'MainSources_before.json', before_main)
    api.write(output / 'CandidateSources_before.json', before_candidate)
    record = {'schemaVersion': 1, 'checkpoint': 94, 'status': 'RUNNING_ISOLATED_FOCUSED_NATIVE_SUITES94',
              'startedUtc': api.utc(), 'candidateUnity': VERSION, 'setId': set_id,
              'runnerSHA256': file_hash(Path(__file__)), 'nativeRunnerSHA256': file_hash(HERE / 'run_native.py'),
              'suiteConfigurationSHA256': file_hash(configuration_path),
              'mainManifestSHA256': file_hash(output / 'MainSources_before.json'),
              'candidateManifestSHA256': file_hash(output / 'CandidateSources_before.json'),
              'mainInputCount': before_main['inputCount'], 'candidateInputCount': before_candidate['inputCount'],
              'selectedCases': selected, 'focusedRepeat': bool(args.only), 'runs': [],
              'scope': 'Actual serial isolated Unity6.6.6f1 Editor invocations, distinct fresh output per suite. Raw legacy schemas and every failure retained; actual process logs bind engine versions. Account diagnostics remain separate. No trusted server-worker re-pinning, backend provider, SDK, Android/device, physical input, startup video or whole-game smoothness acceptance.'}
    api.write(output / 'Authorization.json', record)
    preservation_ok = True
    try:
        for case in selected:
            current_main = api.freeze()
            current_candidate = native.candidate_sources(api)
            if (current_main != before_main or current_candidate != before_candidate or processes.unity_pids()
                    or file_hash(HERE / 'run_native.py') != record['nativeRunnerSHA256']
                    or file_hash(configuration_path) != record['suiteConfigurationSHA256']
                    or file_hash(Path(__file__)) != record['runnerSHA256']):
                record['stoppedBeforeSuite'] = case['name']
                preservation_ok = False
                break
            folder = output / 'Suites' / case['name']
            command = [sys.executable, '-B', str(HERE / 'run_native.py'), '--execute', '--out', str(folder),
                       '--entry', case['entry'], '--report', case['report'], '--expected', case['expected'],
                       '--output-env', case['environment'], '--timeout', str(case['timeoutSeconds'])]
            if not case['reportHasUnity']:
                command.append('--legacy-report-no-version')
            if case.get('quit'):
                command.append('--quit')
            row = dict(case, acceptedNativePass=False, wrapperExitCode=None, command=command,
                       invocation=(folder / 'Invocation.json').relative_to(ROOT).as_posix(),
                       reportPath=(folder / case['report']).relative_to(ROOT).as_posix())
            print(json.dumps({'status': 'START_NATIVE_SUITE94', 'name': case['name'], 'set': set_id}), flush=True)
            try:
                child = subprocess.run(command, cwd=ROOT, timeout=case['timeoutSeconds'] + 120,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                row['wrapperExitCode'] = child.returncode
            except subprocess.TimeoutExpired:
                row['wrapperTimeout'] = True
            except Exception as error:
                row['wrapperErrorType'] = type(error).__name__
            invocation_path = folder / 'Invocation.json'
            report_path = folder / case['report']
            try:
                invocation = json.loads(invocation_path.read_text('utf-8-sig')) if invocation_path.is_file() else {}
                report = json.loads(report_path.read_text('utf-8-sig')) if report_path.is_file() else {}
                row.update(invocationStatus=invocation.get('status', 'MISSING'), nativeStatus=report.get('status', 'MISSING'),
                           actualEngineVersionFromProcessLog=invocation.get('actualEngineVersionFromProcessLog'),
                           invocationSHA256=file_hash(invocation_path) if invocation_path.is_file() else None,
                           reportSHA256=file_hash(report_path) if report_path.is_file() else None)
                if report:
                    row.update(count_native(report, case))
                    row['diagnosticClassification'] = account_classification(report, case)
                row['acceptedNativePass'] = (row['wrapperExitCode'] == 0
                    and invocation.get('status') == 'PASS_ISOLATED_UNITY6_94_NATIVE'
                    and invocation.get('actualEngineVersionFromProcessLog') == VERSION
                    and invocation.get('mainInputsUnchanged') is True and invocation.get('unityPidsAfter') == []
                    and invocation.get('nativeReportSHA256') == row['reportSHA256']
                    and native_passed(report, case))
            except Exception as error:
                row['reportValidationErrorType'] = type(error).__name__
            after_main = api.freeze()
            after_candidate = native.candidate_sources(api)
            row['mainInputsUnchanged'] = after_main == before_main
            row['candidateSourceDelta'] = source_delta(current_candidate, after_candidate)
            row['unityPidsAfter'] = processes.unity_pids()
            record['runs'].append(row)
            write_progress(api, output, record)
            print(json.dumps({'status': 'FINISH_NATIVE_SUITE94', 'name': case['name'],
                              'acceptedNativePass': row['acceptedNativePass'], 'nativeStatus': row.get('nativeStatus')}), flush=True)
            if not row['mainInputsUnchanged'] or not unchanged(row['candidateSourceDelta']) or row['unityPidsAfter']:
                preservation_ok = False
                record['stoppedAfterSuite'] = case['name']
                break
            # Real assertion failures remain failures. Independent suites still run.
    except Exception as error:
        record['suiteRunnerErrorType'] = type(error).__name__
    finally:
        after_main = api.freeze()
        after_candidate = native.candidate_sources(api)
        api.write(output / 'MainSources_after.json', after_main)
        api.write(output / 'CandidateSources_after.json', after_candidate)
        record.update(mainInputsUnchanged=after_main == before_main,
                      mainSourceDelta=source_delta(before_main, after_main),
                      candidateSourceDelta=source_delta(before_candidate, after_candidate),
                      unityPidsAfter=processes.unity_pids(), finishedUtc=api.utc())
        preservation_ok = preservation_ok and record['mainInputsUnchanged'] and unchanged(record['candidateSourceDelta']) and not record['unityPidsAfter']
        record.update(summarize(record['runs'], selected, preservation_ok,
                                len(record['runs']) == len(selected) and 'suiteRunnerErrorType' not in record))
        write_final(api, output, record)
    print(json.dumps({'status': record['status'], 'requiredSuitesPassing': record['requiredSuitesPassing'],
                      'requiredSuitesFailing': record['requiredSuitesFailing'],
                      'passingChecks': record['requiredPassingChecks'],
                      'diagnosticSuitesFailing': record['diagnosticSuitesFailing'],
                      'report': (output / 'SuiteSet.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if record['status'] == 'PASS_ISOLATED_FOCUSED_NATIVE_SUITES94' else 1


if __name__ == '__main__':
    raise SystemExit(main())
