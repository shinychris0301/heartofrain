"""Root-only serial native UI/state suites; no Android or provider access."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Progress92'
CASES = [
    ('Progress', 'Progress92Verification', 'Report.json', 'PASS_NATIVE_PROGRESS92', 'HOTR_PROGRESS92_OUT'),
    ('DisplaySmoke', 'Display88Verification', 'Report.json', 'PASS_NATIVE_DISPLAY88', 'HOTR_DISPLAY88_OUT')]



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--list-name', default='NativeRuns.json')
    args = parser.parse_args()
    if not args.tag.isalnum() or len(args.tag) > 16:
        parser.error('Short fresh alphanumeric tag required')
    if Path(args.list_name).name != args.list_name or not args.list_name.endswith('.json') or not args.list_name.replace('_', '').replace('.', '').isalnum():
        parser.error('Simple JSON list filename required')
    destination = OUT / args.list_name
    if destination.exists():
        parser.error('Existing accepted native list preserved; choose a fresh list name')
    folder = OUT / 'Native' / args.tag
    folder.mkdir(parents=True, exist_ok=False)
    result = {'schemaVersion': 1, 'checkpoint': 92, 'status': 'RUNNING', 'runs': []}
    process_report = folder / 'SuiteSet.json'
    for name, entry, report, expected, variable in CASES:
        case = folder / name
        child = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('run_native.py')),
            '--out', str(case), '--entry', 'HeartOfTheRain.Verification.' + entry + '.Run',
            '--report', report, '--expected', expected, '--output-env', variable, '--timeout', '600'],
            cwd=ROOT, timeout=660)
        result['runs'].append({'name': name, 'invocation': (case / 'Invocation.json').relative_to(ROOT).as_posix(),
            'report': (case / report).relative_to(ROOT).as_posix(), 'expectedStatus': expected})
        process_report.write_text(json.dumps(result, indent=2) + '\n')
        if child.returncode:
            result['status'] = 'FAIL_NATIVE92_SET'
            process_report.write_text(json.dumps(result, indent=2) + '\n')
            return 1
    result['status'] = 'PASS_NATIVE92_SET'
    process_report.write_text(json.dumps(result, indent=2) + '\n')
    if destination.exists():
        raise RuntimeError('ExistingAcceptedNativeListPreserved')
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'suites': len(result['runs'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
