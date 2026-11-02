"""Current86 wrapper around the immutable generic85 internal build machinery.

Both current default APKs are rebuilt serially, prior APKs archived, settings
restored exactly, and historical reports restored by that helper. No install.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
import run_ads85_internal_build as build
from run_native86 import unity_pids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute or os.name != 'nt':
        parser.error('Explicit root Windows execution required')
    settings = (ROOT / 'Unity/ProjectSettings/ProjectSettings.asset').read_text('utf-8-sig')
    if 'HOTR_RUSTORE_PAY' in settings or any('HOTR_RUSTORE_PAY' in p.read_text('utf-8-sig')
                                           for p in (ROOT / 'Unity/Assets').rglob('*.rsp')):
        parser.error('Ordinary project must remain payment-SDK-free')
    build.EVIDENCE = ROOT / 'Verification/Evidence/Review86'
    build.unity_pids = unity_pids
    output, report = build.run(argparse.Namespace(execute=True, unity=build.PINNED_UNITY))
    result = {'status': 'PASS_INTERNAL_ANDROID_BUILDS86' if report['status'] == 'PASS_SDK_FREE_INTERNAL_ANDROID_BUILDS85' else 'FAIL_INTERNAL_ANDROID_BUILDS86',
              'wrapperSHA256': build.sha(Path(__file__)),
              'helperSHA256': build.sha(ROOT / 'Verification/Tools/Ads85/run_ads85_internal_build.py'),
              'invocation': (output / 'Invocation.json').relative_to(ROOT).as_posix(),
              'invocationSHA256': build.sha(output / 'Invocation.json'),
              'scope': 'Current86 SDK-free internal development/non-development Android compile; exact helper source/configuration and source manifests are bound. Historical helper status names contain85. No Android installation or production acceptance.'}
    build.write(output / 'Review86_Builds.json', result)
    print(json.dumps(result), flush=True)
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
