"""Current89 wrapper around generic SDK-free internal build machinery; no ADB.

Produces both internal APKs serially, archives previous bytes, restores all
ProjectSettings exactly and restores historical fixed native reports. This is
not store signing or release approval. Underlying85 status names are historical.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
import run_ads85_internal_build as build
sys.path.insert(0, str(ROOT / 'Verification/Tools/Review86'))
from run_native86 import unity_pids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute or os.name != 'nt':
        parser.error('Explicit root Windows execution required')
    settings = (ROOT / 'Unity/ProjectSettings/ProjectSettings.asset').read_text('utf-8-sig')
    if 'HOTR_RUSTORE_PAY' in settings or any('HOTR_RUSTORE_PAY' in p.read_text('utf-8-sig') for p in (ROOT / 'Unity/Assets').rglob('*.rsp')):
        parser.error('Ordinary current build must remain payment-SDK-free')
    build.EVIDENCE = ROOT / 'Verification/Evidence/RegionalAccounts89'
    build.unity_pids = unity_pids
    output, report = build.run(argparse.Namespace(execute=True, unity=build.PINNED_UNITY))
    result = {'status': 'PASS_INTERNAL_ANDROID_BUILDS89' if report['status'] == 'PASS_SDK_FREE_INTERNAL_ANDROID_BUILDS85' else 'FAIL_INTERNAL_ANDROID_BUILDS89',
              'wrapperSHA256': build.sha(Path(__file__)),
              'buildHelperSHA256': build.sha(ROOT / 'Verification/Tools/Ads85/run_ads85_internal_build.py'),
              'processSelectorSHA256': build.sha(ROOT / 'Verification/Tools/Review86/run_native86.py'),
              'invocation': (output / 'Invocation.json').relative_to(ROOT).as_posix(),
              'invocationSHA256': build.sha(output / 'Invocation.json'),
              'scope': 'Current89 SDK-free development and non-development Android IL2CPP ARM64 compilation. Exact helper/configuration/source manifests are bound; no install, device or production acceptance.'}
    build.write(output / 'RegionalAccounts89_Builds.json', result)
    print(json.dumps(result), flush=True)
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
