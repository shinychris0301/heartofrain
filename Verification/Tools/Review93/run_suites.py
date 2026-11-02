"""Root-only broad current-source review; failures remain distinct and retained."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import delta, freeze, sha, unchanged, utc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--only')
    args = parser.parse_args()
    if not args.tag.isalnum() or len(args.tag) > 20:
        parser.error('Fresh short alphanumeric run tag required')
    configuration = json.loads(Path(__file__).with_name('suites.json').read_text('utf-8'))
    cases = configuration['cases']
    if args.only:
        cases = cases + configuration.get('connectedCases', [])
    if args.only:
        requested = args.only.split(',')
        if len(set(requested)) != len(requested) or set(requested) - {r['name'] for r in cases}:
            parser.error('Unique configured cases required')
        cases = [r for r in cases if r['name'] in requested]
    output = ROOT / 'Verification/Evidence/Review93/Native' / args.tag
    output.mkdir(parents=True, exist_ok=False)
    frozen = freeze()
    (output / 'FrozenSources.json').write_text(json.dumps(frozen, indent=2) + '\n')
    record = {'schemaVersion': 1, 'checkpoint': 93, 'status': 'RUNNING', 'startedUtc': utc(),
              'runnerSHA256': sha(Path(__file__)), 'suiteConfigurationSHA256': sha(Path(__file__).with_name('suites.json')),
              'sourceSHA256': sha(output / 'FrozenSources.json'), 'unityInputCount': frozen['inputCount'],
              'scope': 'Actual serial pinned Unity Editor tests. Individual reports distinguish fixtures, local files, rendering and real HTTP. No physical device, hosted service, real provider or production acceptance.',
              'runs': []}
    for case in cases:
        if not unchanged(delta(frozen, freeze())):
            record['sourceDrift'] = True
            break
        folder = output / case['name']
        command = [sys.executable, '-B', str(Path(__file__).with_name('run_native.py')),
                   '--out', str(folder), '--entry', case['entry'], '--report', case['report'],
                   '--expected', case['expected'], '--output-env', case['environment'], '--timeout', '900']
        if case.get('quit'):
            command.append('--quit')
        print('START ' + case['name'], flush=True)
        child = subprocess.run(command, cwd=ROOT, timeout=960)
        invocation = json.loads((folder / 'Invocation.json').read_text('utf-8'))
        row = dict(case, invocation=(folder / 'Invocation.json').relative_to(ROOT).as_posix(),
                   reportPath=(folder / case['report']).relative_to(ROOT).as_posix(), exitCode=child.returncode,
                   status=invocation['status'])
        record['runs'].append(row)
        (output / 'SuiteSet.json').write_text(json.dumps(record, indent=2) + '\n')
        print('FINISH ' + case['name'] + ' ' + invocation['status'], flush=True)
        if not invocation.get('inputsUnchanged') or invocation.get('unityPidsAfter') or invocation.get('nativeStatus') == 'MISSING':
            break
    record['status'] = ('PASS_CURRENT_NATIVE_REVIEW93' if len(record['runs']) == len(cases)
                        and all(r['exitCode'] == 0 for r in record['runs']) else 'REVIEW93_NATIVE_WITH_FAILURES')
    record['finishedUtc'] = utc()
    (output / 'SuiteSet.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'status': record['status'], 'suites': len(record['runs']),
                      'report': (output / 'SuiteSet.json').relative_to(ROOT).as_posix()}), flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
