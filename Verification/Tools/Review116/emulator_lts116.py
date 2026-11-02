"""Fail-closed device entry for the actual approved116 LTS no-splash build.

The shared device harness is configured only inside this Python process. Every
launch requires the reusable actual-build/profile validator again; diagnostic
Unity2022 artifacts are never eligible through this entry point.
"""
import argparse
import json
from pathlib import Path
import re
import sys

import emulator116 as device
import launch_profile116 as launch

PACKAGE = 'com.heartoftherain.review116lts'
CANONICAL_SHA = 'b0bc2b91f3a22b9b8bcc6ab230ffa28a7a8f9a8f4972038fd9eeb3c66dfbe28d'


def validate_static(path):
    path = Path(path).resolve()
    device.need(path.is_relative_to(device.ROOT / 'Verification/Evidence/Review116/LTSNoSplash'),
        'ApprovedLtsStaticProofRequired')
    proof = device.read(path)
    device.need(proof.get('status') == 'PASS_STATIC_APK116_LTS'
        and proof.get('package') == PACKAGE and proof.get('unity') == '6000.3.27f1'
        and proof.get('development') is True and proof.get('showSplashScreen') is False
        and proof.get('showUnityLogo') is False and proof.get('checks')
        and all(value is True for value in proof['checks'].values()) and proof.get('errors') == [],
        'SuccessfulActualLtsStaticChecksRequired')
    for field in ('apk', 'nativeBuild', 'invocation', 'preparation', 'launchValidator'):
        reference = proof[field]
        device.need(device.bind(device.ROOT / reference['path']) == reference,
            'ImmutableLtsStaticBindingRequired')
    canonical = proof['canonicalSnapshot']['manifest']
    device.need(canonical['sha256'] == CANONICAL_SHA
        and device.bind(device.ROOT / canonical['path']) == canonical
        and proof['canonicalSnapshot']['runtimeAndArtByteEquality'] is True,
        'ExactApprovedLtsCanonicalSourceRequired')
    eligibility = launch.qualify(device.ROOT / proof['nativeBuild']['path'],
        device.ROOT / proof['invocation']['path'])
    device.need(eligibility == proof['launchEligibility']
        and eligibility['ordinaryUserVisibleLaunchAllowed'] is True
        and eligibility['diagnosticOnly'] is False and eligibility['packageName'] == PACKAGE
        and eligibility['apk'] == proof['apk'], 'FreshActualLtsLaunchQualificationRequired')
    # The app/art were built from the user's explicit immutable source cut.
    # Newer working-tree changes remain outside this acceptance scope.
    proof['immutableSnapshotMode'] = True
    proof['currentPassingBuild'] = False
    return device.ROOT / proof['apk']['path'], proof


def require_launch_profile(context):
    if 'staticProof' in context:
        reference = context['staticProof']
        path = device.ROOT / reference['path']
        device.need(device.bind(path) == reference, 'UnchangedInstalledLtsStaticProofRequired')
        _, proof = validate_static(path)
        device.need(context.get('package') == PACKAGE and context.get('apk') == proof['apk'],
            'SameInstalledApprovedLtsArtifactRequired')
    else:
        device.need(context.get('package') == PACKAGE and 'nativeBuild' in context,
            'ApprovedLtsLaunchContextRequired')
        eligibility = launch.qualify(device.ROOT / context['nativeBuild']['path'],
            device.ROOT / context['invocation']['path'])
        device.need(eligibility == context['launchEligibility'] and eligibility['apk'] == context['apk'],
            'FreshLtsArtifactAndEligibilityRequired')
        proof = context
    eligibility = proof['launchEligibility']
    device.need(eligibility['ordinaryUserVisibleLaunchAllowed'] is True
        and eligibility['diagnosticOnly'] is False, 'DiagnosticLaunchRejectedForOrdinaryLts')
    return eligibility


def configure():
    device.PACKAGE = PACKAGE
    device.BASE = '/sdcard/Android/data/' + PACKAGE + '/files'
    device.ACTIVITY = PACKAGE + '/com.unity3d.player.UnityPlayerActivity'
    device.validate_static = validate_static
    device.LAUNCH_PROFILE_VALIDATOR = require_launch_profile
    device.DIAGNOSTIC_2022_OPT_IN = False
    return device


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('inventory', 'install', 'regression', 'cold-start', 'home'))
    parser.add_argument('--name', required=True)
    parser.add_argument('--static', type=Path)
    parser.add_argument('--installation', type=Path)
    parser.add_argument('--timeout', type=int, default=2100)
    args = parser.parse_args()
    configure()
    if args.operation == 'inventory':
        device.inventory(args.name)
    elif args.operation == 'install':
        device.need(args.static is not None, 'ActualLtsStaticReportRequired')
        device.install(args.name, args.static, no_streaming=False, internal=False)
    elif args.operation == 'regression':
        device.need(args.installation is not None, 'ActualLtsInstallationReceiptRequired')
        device.regression(args.name, args.installation, args.timeout)
    else:
        device.need(args.installation is not None, 'ActualLtsInstallationReceiptRequired')
        sys.argv = [sys.argv[0], '--name', args.name, '--installation', str(args.installation)]
        if args.operation == 'cold-start':
            import cold_start_lts116
            cold_start_lts116.main()
        else:
            import home116
            home116.main()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        print(json.dumps(dict(status='BLOCKED_APPROVED_LTS116_DEVICE', errorType=type(error).__name__,
            code=code if re.fullmatch('[A-Za-z0-9]{1,100}', code) else 'PrivateEvidenceRequired')), flush=True)
        raise SystemExit(1)
