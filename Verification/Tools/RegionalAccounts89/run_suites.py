"""Root-only serial native UI/state suites; no Android or provider access."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/RegionalAccounts89'
CASES = [
    ('Regional', 'Regional89Verification', 'Report.json', 'PASS_NATIVE_REGIONAL89', 'HOTR_REGION89_OUTPUT'),
    ('Provider', 'ProviderIdentity89Verification', 'Report.json', 'PASS_NATIVE_PROVIDER_IDENTITY89', 'HOTR_PROVIDER89_OUT'),
    ('AdsParser', 'RewardedAdsParser85Verification', 'Native/RewardedAdsParser85.json', 'PASS_NATIVE_REWARDED_ADS85_PARSER', 'HOTR_REWARDED_ADS85_OUTPUT'),
    ('AdsUi', 'RewardedAdsUi85Verification', 'Native/RewardedAdsUi85.json', 'PASS_NATIVE_REWARDED_ADS85_UI', 'HOTR_REWARDED_ADS85_OUTPUT'),
    ('AdsFlow', 'RewardedAdsFlow85Verification', 'Native/RewardedAdsFlow85.json', 'PASS_NATIVE_REWARDED_ADS_FLOW85', 'HOTR_ADS85_OUTPUT'),
    ('DisplaySmoke', 'Display88Verification', 'Report.json', 'PASS_NATIVE_DISPLAY88', 'HOTR_DISPLAY88_OUT')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not args.tag.isalnum() or len(args.tag) > 16:
        parser.error('Short fresh alphanumeric tag required')
    folder = OUT / 'Native' / args.tag
    folder.mkdir(parents=True, exist_ok=False)
    result = {'schemaVersion': 1, 'checkpoint': 89, 'status': 'RUNNING', 'runs': []}
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
            result['status'] = 'FAIL_NATIVE89_SET'
            process_report.write_text(json.dumps(result, indent=2) + '\n')
            return 1
    result['status'] = 'PASS_NATIVE89_SET'
    process_report.write_text(json.dumps(result, indent=2) + '\n')
    destination = OUT / 'NativeRuns.json'
    if destination.exists():
        raise RuntimeError('ExistingAcceptedNativeListPreserved')
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'suites': len(result['runs'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
