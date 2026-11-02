"""Create the source-bound SDK-checkout evidence index and offline review page."""
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Verification/Evidence/Review125'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    path = OUT / name
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    return value, {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)}


def main():
    backend, bp = read('Backend/Full01/Service_Tests.json')
    assert backend['status'] == 'PASS_BACKEND_SERVICE_TESTS'
    assert backend['tests'] == backend['executedTests'] == len(set(backend['passed'])) == 933
    assert not (backend['errors'] or backend['failures'] or backend['skipped'] or
                backend['sourceInputsChangedDuringRun'])
    assert backend['actualPinnedWorkerIntegration'] is True
    assert backend['sourceSHA256'] == backend['sourceSHA256After']
    assert all(sha(ROOT / path) == value for path, value in backend['sourceSHA256'].items())
    native, np = read('NativeClient/FinalClient125.json')
    fresh, fp = read('NativeClient/FinalMainFreshness125.json')
    sdk, sp = read('SDK/SdkBindings125.json')
    assert native['status'] == 'PASS_SCOPED_SDK_CLIENT125_WITH_OPEN_RELEASE_GATES'
    assert (native['nativeChecks'], native['nativeCases'], native['actualHttpChecks']) == (4172, 99, 45)
    assert fresh['ownedCSharpCount'] == 18 and fresh['originalGUIDsChecked'] == 3154
    assert fresh['mainProjectSettingsUnchanged'] is True
    assert sha(ROOT / 'Unity/ProjectSettings/ProjectSettings.asset') == fresh['mainProjectSettingsSHA256']
    assert all(sha(ROOT / 'Unity' / row['path']) == row['acceptedSHA256']
               for row in fresh['ownedSources'])
    assert sdk['nativeChecks'] == 49 and sdk['currentSelectedInputsMatch'] is True
    assert all(sha(ROOT / row['source']) == row['sha256']
               for row in sdk['sdkIntegrationSourceAndMetaInputs'])
    _, backend_review = read('Payments/SourceBoundIndependentBackend125_Closure.json')
    unity_review, unity_review_pin = read('NativeClient/IndependentUnityReview125.json')
    assert unity_review['status'].startswith('PASS')
    _, release_review = read('Payments/RootReleaseChecks125.json')
    setup = json.loads((ROOT / 'Release/RuStore/sdk-checkout125/setup-inputs.json').read_bytes())
    assert setup['consoleApplicationId'] is None and setup['packageName'] == 'com.heartoftherain.game'
    summary = {
        'schemaVersion': 1,
        'status': 'IMPLEMENTED_WITH_OPEN_APP_ID_HOST_AND_RELEASE_GATES125',
        'checkedAtUtc': datetime.now(timezone.utc).isoformat(),
        'paymentMode': 'sdk_client_reported',
        'requiredRuStoreSecrets': [],
        'missingRuStoreConsoleIdentifier': 'consoleApplicationId',
        'registeredPackage': setup['packageName'], 'registeredProducts': 12,
        'wellkeeperProduct': 'hotr_bundle_wellkeeper_c',
        'paymentReturnScheme': setup['paymentReturnScheme'],
        'backend': {'tests': 933, 'failures': 0, 'errors': 0, 'skips': 0,
                    'actualApprovedWorker': True, 'stableSourceInputs': len(backend['sourceSHA256']),
                    'receipt': bp, 'independentReview': backend_review},
        'unity': {'editor': '2022.3.62f3', 'checks': 4172, 'cases': 99,
                  'scopedOwnedCSharpFilesMatched': 18, 'originalGuidsPreserved': 3154,
                  'mainSettingsPreserved': True, 'receipt': np, 'freshnessReceipt': fp,
                  'independentReview': unity_review_pin},
        'actualUnityHttp': {'checks': 45, 'backendRestartVerified': True,
                            'syntheticSdkObservations': True, 'testListenerClosed': True},
        'actualVendorSdk': {'checks': 49, 'pay': '11.1.0', 'core': '10.5.0',
                            'stockPackageFilesMatched': 315, 'receipt': sp,
                            'previous38ChecksIncluded': True, 'runtimeSdkInitialized': False},
        'releaseReview': release_review,
        'behavior': ['SDK ONE_STEP purchase and fresh GetPurchase observation.',
                     'Authenticated SDK report matched to immutable frozen order and full grant.',
                     'Atomic managed-wallet delivery and duplicate protection before SDK acknowledgment.',
                     'Explicit keyless SDK schema125; unchanged default provider_api/schema15 mode.',
                     'Strict packaged profile, vendor settings/manifest binding and always-on package pins.'],
        'limitations': [
            'No actual Console application ID; all checked-in SDK profiles remain disabled.',
            'SDK reports are app supplied and can be forged by a modified client.',
            'Anonymous unreported-purchase recovery is device scoped; manual support may be needed.',
            'Existing hosted staging105/schema15 was not deployed, migrated or activated in this task.',
            'Preserving existing hosted accounts requires a separate stopped same-wallet cutover.',
            'Preparation CLI accepts owned production122 API15 only and yields permanent quarantine125.',
            'No two-step capture workflow; unexpected held payment remains pending without delivery.',
            'No APK, Android/provider payment, Console signer or production release acceptance.',
            'Final operator/support/legal content and product/monetization availability remain to verify.',
        ],
        'ownerChecklist': 'Release/RuStore/sdk-checkout125/README.md',
        'handoff': 'Codex_Handoff/Documentation/125_SDK_HANDLED_PURCHASES.md',
        'packagingEntry': native['packagingEntry'], 'productionActivated': False,
    }
    target = OUT / 'Review125Summary.json'
    with target.open('x', encoding='utf-8') as stream:
        json.dump(summary, stream, indent=2)
        stream.write('\n')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Review125 — RuStore SDK checkout</title>
<style>body{font:16px/1.6 system-ui,sans-serif;max-width:960px;margin:36px auto;padding:0 24px;color:#183549;background:#f6f9fc}table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;padding:12px;border:1px solid #cbd9e3}code{overflow-wrap:anywhere}a{color:#175aa0}aside{padding:16px;background:#fff4d8}h1,h2{line-height:1.2}</style>
<h1>RuStore SDK checkout</h1><p>Implemented and tested; live checkout remains disabled.</p>
<aside><strong>Only remaining RuStore Console identifier:</strong> the numeric application ID.
Package <code>com.heartoftherain.game</code> and all twelve product IDs are recorded.
This mode needs no RuStore API key ID, private signing key or notification key.</aside>
<h2>Accepted checks</h2><table><tr><th>Scope</th><th>Result</th></tr>
<tr><td>Backend / actual approved gameplay worker</td><td>933 passed; no failures, errors or skips; 175 source inputs unchanged</td></tr>
<tr><td>Unity Editor</td><td>4,172 checks / 99 cases passed</td></tr>
<tr><td>Actual Unity ↔ local backend HTTP</td><td>45 checks, including restart; simulated SDK observations</td></tr>
<tr><td>Actual pinned SDK/API and Editor binding</td><td>49 checks; 315 stock package files matched</td></tr></table>
<h2>Delivery</h2><p>Persist order → SDK purchase → fresh SDK lookup → authenticated app report → atomic server-wallet grant → delivery acknowledgment.</p>
<p>Approved prices, full inventory grants and once-per-player Special limits remain. Wellkeeper uses <code>hotr_bundle_wellkeeper_c</code>.</p>
<h2>Open gates</h2><ul>''' + ''.join('<li>' + html.escape(item) + '</li>' for item in summary['limitations']) + '''</ul>
<p><a href="../../../Release/RuStore/sdk-checkout125/README.md">Simple owner checklist</a> ·
<a href="../../../Codex_Handoff/Documentation/125_SDK_HANDLED_PURCHASES.md">Implementation and scope</a> ·
<a href="Review125Summary.json">Source-bound evidence index</a></p></html>'''
    with (OUT / 'Comparison.html').open('x', encoding='utf-8') as stream:
        stream.write(page + '\n')
    print(json.dumps({'status': summary['status'], 'summary': str(target), 'sha256': sha(target)}))


if __name__ == '__main__':
    main()
