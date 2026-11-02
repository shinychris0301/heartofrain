"""Index accepted preparation evidence without activating services or providers."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'Verification/Evidence/Review122'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt(relative):
    path = EVIDENCE / relative
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    return value, {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inactive-receipt', required=True)
    args = parser.parse_args()
    backend, backend_pin = receipt('Backend/Full05/Service_Tests.json')
    assert backend['status'] == 'PASS_BACKEND_SERVICE_TESTS'
    assert backend['tests'] == backend['executedTests'] == len(backend['passed']) == 888
    assert len(set(backend['passed'])) == 888
    assert not (backend['failures'] or backend['errors'] or backend['skipped'] or
                backend['sourceInputsChangedDuringRun'])
    assert backend['actualPinnedWorkerIntegration'] is True
    assert backend['sourceSHA256'] == backend['sourceSHA256After']
    assert all((ROOT / path).is_file() and digest(ROOT / path) == sha
               for path, sha in backend['sourceSHA256'].items())
    native, native_pin = receipt('NativeClient/FinalClientSource122.json')
    fresh, fresh_pin = receipt('NativeClient/FinalMainFreshness122.json')
    assert native['checksPassed'] == fresh['acceptedNativeChecks'] == 4047
    assert native['casesPassed'] == fresh['acceptedNativeCases'] == 90
    assert fresh['status'] == 'PASS_FINAL_SCOPED_MAIN_FRESHNESS122'
    assert fresh['productionOwnedCsPathCount'] == 20 and fresh['sealedGuidCount'] == 3153
    for row in fresh['productionOwnedSources']:
        assert digest(ROOT / row['path']) == row['currentSHA256'] == row['sealedSHA256']
    controls, controls_pin = receipt('Preparation/FinalControls122_03.json')
    assert controls['tests'] == 45 and controls['inputsUnchanged'] is True
    assert controls['status'] == 'PASS_PREPARATION122_CONTROLS'
    pages, pages_pin = receipt('PublicPages/PublicPagesSummary122.json')
    assert pages['status'] == 'PASS_ACTUAL_OWNED_VPS_TEMPORARY_PUBLIC_PAGES122'
    inactive, inactive_pin = receipt(args.inactive_receipt)
    assert inactive['status'] == 'inactive_production_files_staged_and_verified'
    assert inactive['productionActivated'] is False
    summary = {
        'schemaVersion': 1,
        'status': 'PREPARED_WITH_OPEN_PROVIDER_AND_RELEASE_GATES122',
        'checkedAtUtc': datetime.now(timezone.utc).isoformat(),
        'backend': {'testsExecuted': 888, 'failures': 0, 'errors': 0, 'skips': 0,
                    'actualApprovedWorkerIntegration': True,
                    'unchangedSourceInputs': len(backend['sourceSHA256']), 'receipt': backend_pin},
        'native': {'engine': '2022.3.62f3', 'assertions': 4047, 'cases': 90,
                   'productionOwnedSourceFilesMatched': 20, 'sealedGuidsMatched': 3153,
                   'newerUnrelatedPathsPreservedUnverified': fresh['newerUnrelatedMainPathCount'],
                   'wholeCurrentMainCertified': False,
                   'receipt': native_pin, 'freshnessReceipt': fresh_pin},
        'focusedControls': {'preparationProviderMonitor': 45, 'receipt': controls_pin,
                            'countsOverlapFullBackendSuite': True},
        'host': {'origin': 'https://api.novamind-it.ru', 'authorityMode': 'staging',
                 'windowsMonitorInstalled': True, 'monitorChecksPassed': 9,
                 'externalAlertConfigured': False,
                 'temporaryPagesPublished': True, 'operatorAndSupportDetailsPending': True,
                 'pageReceipt': pages_pin, 'inactiveSourceStaged': True,
                 'inactiveReceipt': inactive_pin, 'productionActivated': False},
        'commerce': {'ownerConfirmedRegisteredProducts': 12,
                     'wellkeeperProductId': 'hotr_bundle_wellkeeper_c',
                     'otherElevenProductIdsChanged': False,
                     'historicalPendingOrderTermsPreserved': True,
                     'publicationVerified': False},
        'advertising': {'rewardedUnitId': 'R-M-20291714-1',
                        'interstitialUnitId': 'R-M-20291714-2',
                        'rewardCoins': 400, 'claimsPerPlayerLocalDay': 3,
                        'cooldownSeconds': 600, 'interstitialPlacementAdded': False,
                        'serverVerifiedImpressions': False, 'liveAdsActivated': False},
        'remaining': [
            'Actual numeric RuStore and optional VK application IDs.',
            'API key ID and restricted server-only private API and notification key files.',
            'Final registered package, return scheme, release signer and version metadata.',
            'Factual final operator/contact/privacy/support/terms content.',
            'Qualified production worker/campaign parity, ingress, recovery and reboot rehearsal.',
            'Encrypted off-host backup and restore rehearsal.',
            'Actual twelve-product sandbox checkout, VK and Android advertising acceptance.',
            'SDK-enabled signed release artifact and separate production cutover.',
        ],
        'scopeLimits': [
            'No final APK, fresh vendor SDK compile, Android or real provider test by Review122.',
            'No VPS production authority/database/service activation or provider secrets created.',
            'VPS HTTPS/page observations are from the VPS; independent external reachability remains open.',
            'Same-host monitoring cannot report a complete host outage from that host.',
            'Earlier failed epochs are retained and are not counted as accepted passes.',
            'No Git commit was requested or created for this production-preparation workstream.',
        ],
        'guidance': ['Release/Production122/WHY_THESE_INPUTS122.md',
                     'Release/Production122/SETUP.md',
                     'Codex_Handoff/Documentation/122_PRODUCTION_PROVIDER_PREPARATION.md'],
    }
    output = EVIDENCE / 'Review122Summary.json'
    with output.open('x', encoding='utf-8') as stream:
        json.dump(summary, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': summary['status'], 'path': str(output), 'sha256': digest(output)}))


if __name__ == '__main__':
    main()
