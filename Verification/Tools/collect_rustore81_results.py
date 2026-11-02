"""Read-only RuStore81 foundation evidence collector; publication is explicit.

This never executes Unity/ADB, calls a payment endpoint, or interprets mocked
payments as store acceptance. Missing external integrations remain release gates.
"""
import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/RuStore81'
STATUS = 'PASS_RUSTORE81_PORTABLE_FOUNDATION_WITH_RELEASE_GATES'
BASELINE = 'PASS_RUSSIAN_BRANDING_WITH_UNITY_SPLASH_LICENSE_GATE'
PREFIX = 'Unity/Assets/HeartOfTheRain/'
ADDED = {PREFIX + 'App/RuStore' + suffix for suffix in ('.meta', '/Editor.meta', '/Runtime.meta')}
ADDED |= {PREFIX + path + suffix for path in (
    'App/RuStore/Editor/RuStoreReleasePreflight.cs',
    'App/RuStore/Runtime/FilePayJournal.cs',
    'App/RuStore/Runtime/PayDeliveryCoordinator.cs',
    'App/RuStore/Runtime/PayStoreContracts.cs',
    'App/RuStore/Runtime/RuStoreBackendClient.cs',
    'App/RuStore/Runtime/RuStorePayAdapter.cs',
    'Verification/Editor/RuStore81Verification.cs',
) for suffix in ('', '.meta')}
SUITES = {
    'Guard': ('Native/RuStore81.json', 'PASS_NATIVE_RUSTORE81_RELEASE_GUARD'),
    'Http': ('Native/HTTP.json', 'PASS_NATIVE_RUSTORE81_HTTP_STAGING_CLIENT'),
    'Preflight': ('Native/Release_Preflight.json', 'BLOCKED_RUSTORE_EXTERNAL_CONFIGURATION_AND_INTEGRATION'),
    'Checks': ('Native/Checks.json', 'PASS_NATIVE_EDITOR_CHECKS'),
    'ProfileChecks': ('Native/ProfileChecks.json', 'PASS_NATIVE_PROFILE_TRANSACTIONS'),
    'PlaySmoke': ('Native/PlaySmoke.json', 'PASS_NATIVE_PLAY_SMOKE'),
    'PortraitChecks': ('Native/PortraitChecks.json', 'PASS_NATIVE_PORTRAIT_CHECKS'),
}


def need(value, message):
    if not value:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def clean(value, label):
    need(not any(value.get(k) for k in ('error', 'errors', 'failures', 'failed')), label + ' contains failures')


class Proof:
    def __init__(self):
        self.artifacts, self.external = {}, {}

    def file(self, name):
        path = (OUT / name).resolve()
        need(path.is_relative_to(OUT.resolve()) and path.is_file(), 'Missing/unsafe evidence: ' + name)
        self.artifacts[path.relative_to(OUT).as_posix()] = sha(path)
        return path

    def read(self, name):
        return json.loads(self.file(name).read_text('utf-8-sig'))

    def ext(self, name, expected=None):
        path = (ROOT / name).resolve()
        need(path.is_relative_to(ROOT.resolve()) and path.is_file(), 'Missing/unsafe external evidence: ' + name)
        digest = sha(path)
        need(expected is None or digest == expected, 'Changed external evidence: ' + name)
        self.external[path.relative_to(ROOT).as_posix()] = digest
        return path


def source_and_baseline(proof):
    old = proof.read('Baseline80_Summary.json')
    archived = proof.read('Baseline80_Source_SHA256.json')
    old_apk = proof.read('Baseline80_APK_Artifact.json')
    checkpoint = proof.read('Baseline80_Native_Source_Checkpoint.json')
    need(old['status'] == BASELINE and old['source_checkpoint'] == 80
         and old['source_sha256'] == sha(proof.file('Baseline80_Source_SHA256.json'))
         and old['apk_sha256'] == old_apk['sha256'], 'Sealed checkpoint80 source/APK identity differs')
    need(checkpoint['source_checkpoint'] == checkpoint['last_verified_source_checkpoint'] == 80
         and checkpoint['source_sha256'] == old['source_sha256'] and checkpoint['android_apk_sha256'] == old['apk_sha256']
         and checkpoint['isolated_qa_installed_checkpoint'] == 80 and checkpoint['qa_installed_checkpoint'] == 78
         and checkpoint['installed_checkpoint'] == 64 and checkpoint['original_qa_active_attempt_preserved'] is True,
         'Baseline deployment/unfinished-original-attempt record differs')
    proof.ext('.verification-cache/RuStore81/Baseline80/HeartOfTheRain_Development.apk', old['apk_sha256'])
    for name, original in (('Baseline80_Summary.json', 'Summary.json'), ('Baseline80_Source_SHA256.json', 'Source_SHA256.json'),
                           ('Baseline80_APK_Artifact.json', 'APK_Artifact.json')):
        need(proof.file(name).read_bytes() == proof.ext('Verification/Evidence/LaunchRuStoreR3/' + original).read_bytes(),
             'Baseline80 archive differs: ' + name)
    current = proof.read('Source_SHA256.json')
    files = current['files']
    need(len(files) > len(archived['files']) and len(archived['files']) == 5165, 'Unexpected source input counts')
    actual = {p.relative_to(ROOT).as_posix(): sha(p) for folder in ('Assets', 'Packages', 'ProjectSettings')
              for p in (ROOT / 'Unity' / folder).rglob('*') if p.is_file()}
    need(files == actual, 'Current Unity inputs differ from frozen source81')
    changed = sorted(p for p in archived['files'] if files.get(p) != archived['files'][p])
    added = sorted(files.keys() - archived['files'].keys())
    need(not changed, 'A checkpoint80 existing gameplay/art/settings/package input changed')
    allowed = 'Unity/Assets/HeartOfTheRain/App/RuStore'
    guard = 'Unity/Assets/HeartOfTheRain/Verification/Editor/RuStore81Verification.cs'
    need(all(p == allowed + '.meta' or p.startswith(allowed + '/') or p in (guard, guard + '.meta') for p in added),
         'Source81 adds files outside the reviewed integration boundary')
    need(all(Path(p).suffix in ('.cs', '.meta') for p in added),
         'Source81 unexpectedly adds artwork, serialized settings, SDK binaries or other assets')
    need(set(added) == ADDED and len(files) == 5182,
         'Source81 differs from the independently reviewed17-file addition boundary')
    delta = proof.read('Source_Delta.json')
    need(delta['baseline'] == 80 and delta['changed_existing'] == [] and delta['added'] == added and delta['removed'] == [],
         'Reported source81 delta differs from exact baseline comparison')
    return old, current, delta


def package_review(proof):
    audit, inventory = proof.read('Package_Audit.json'), proof.read('Package_Inventory.json')
    need(audit['status'] == 'READ_ONLY_RUSTORE81_HANDOFF_AUDIT_NOT_IMPLEMENTATION_OR_NATIVE_TEST'
         and inventory['status'] == 'READ_ONLY_RUSTORE81_PACKAGE_INVENTORY_NOT_EXECUTED'
         and audit['inventory']['sha256'] == sha(proof.file('Package_Inventory.json'))
         and audit['content']['regularFiles'] == len(inventory['files']) == 18
         and audit['content']['textFilesRead'] == 17 and audit['content']['docxParagraphsRead'] == 327,
         'Complete package review proof differs')
    need(not audit['safety']['scriptsExecuted'] and not audit['safety']['sdkImported']
         and inventory['scriptsExecuted'] is False, 'Package scripts were mislabeled as review-only')
    need(audit['zip']['sha256'] == inventory['zip']['sha256']
         and all(inventory[k] is True for k in ('crcVerified', 'pathTraversalChecked', 'caseInsensitiveCollisionsRejected', 'symlinksRejected'))
         and all(audit['safety'][k] is True for k in ('zipCRCVerified', 'pathTraversalChecked', 'caseInsensitiveCollisionsRejected', 'symlinksRejected', 'nestedDOCXCRCVerified'))
         and audit['safety']['nestedDOCXActiveContentMembers'] == audit['safety']['nestedDOCXExternalRelationships'] == [],
         'Original archive safety/provenance checks differ')
    for row in inventory['files']:
        need(proof.ext(row['cachePath'], row['sha256']).stat().st_size == row['bytes'], 'Extracted package size differs')
    return {'files_reviewed': 18, 'text_files': 17, 'docx_paragraphs': 327,
            'archive_sha256': inventory['zip']['sha256'], 'package_scripts_executed': False}


def release_configuration(proof):
    proposal = json.loads(proof.ext('Release/RuStore/release.example.json').read_text('utf-8-sig'))
    need(proposal['status'] == 'UNCONFIGURED_NOT_A_REGISTERED_APPLICATION'
         and proposal['environment'] == 'sandbox' and proposal['minimumApiLevel'] == 26
         and all(proposal[name] is None for name in ('packageName', 'consoleApplicationId', 'paymentReturnScheme',
                                                    'backendOrigin', 'privacyPolicyUrl', 'supportUrl', 'termsUrl',
                                                    'versionCode', 'signingCertificateSha256')),
         'A candidate/configured value was silently presented as a registered release identity')
    need(proposal['candidateIdentifiers']['packageName'] == 'com.heartoftherain.game'
         and proposal['candidateIdentifiers']['paymentReturnScheme'] == 'heartoftherain-pay'
         and proposal['notificationPaths']['status'] == 'RESERVED_NOT_IMPLEMENTED_OR_REGISTERED',
         'Unregistered identifier/callback proposals differ')
    need(len(proposal['candidateProducts']) == 6 and all(p['enabled'] is False for p in proposal['candidateProducts']),
         'Draft product mappings became activated')
    proof.ext('Release/RuStore/README.md')
    return {'registered': False, 'hosted': False, 'production_enabled': False,
            'proposed_package_name': 'com.heartoftherain.game', 'proposed_return_scheme': 'heartoftherain-pay',
            'real_console_id': None, 'real_https_origin': None, 'enabled_products': 0}


def backend_review(proof):
    report = proof.read('Backend/Service_Tests.json')
    clean(report, 'Backend service')
    need(report['status'] == 'PASS_BACKEND_SERVICE_TESTS' and report['tests'] == len(report['passed']) >= 90
         and len(set(report['passed'])) == report['tests'] and report['sourceInputsChangedDuringRun'] == []
         and report['sourceSHA256'] == report['sourceSHA256After'], 'Backend test/source proof differs')
    need(report['pythonVersion'].startswith('3.12.') and report['dependencies']['pycryptodome'] == '4.2.0'
         and utc(report['startedUtc']) < utc(report['utc']), 'Backend interpreter/dependency/chronology differs')
    paths = [p for folder in ('hotr_backend', 'tests', 'tools', 'config') for p in (ROOT / 'Backend' / folder).rglob('*')
             if p.is_file() and p.suffix in ('.py', '.json')]
    paths += [ROOT / 'Backend' / p for p in ('requirements.in', 'requirements.lock', 'README.md', 'Run-Local.ps1')]
    actual = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}
    need(actual == report['sourceSHA256After'], 'Backend changed after its source-bound service test')
    for name, digest in actual.items():
        proof.ext(name, digest)
    for module, minimum in (('tests.test_authority.', 23), ('tests.test_commerce.', 32),
                            ('tests.test_wallet.', 24), ('tests.test_rustore_auth.', 11)):
        need(sum(name.startswith(module) for name in report['passed']) >= minimum, 'Backend missing required scope: ' + module)
    config = json.loads((ROOT / 'Backend/config/commerce.json').read_text('utf-8-sig'))
    need(config['enabled'] is False and config['appId'] is None and config['sandbox'] is True
         and all(p['enabled'] is False for p in config['products']), 'Default commerce is no longer disabled/unregistered')
    levels = json.loads((ROOT / 'Backend/config/levels.json').read_text('utf-8-sig'))['levels']
    need([r['level'] for r in levels] == list(range(1, 51)), 'Server catalog omitted an approved level')
    for row in levels:
        path = proof.ext(row['source'], row['sourceSHA256'])
        body = path.read_bytes().decode('utf-8-sig')
        value = json.loads(body)
        need(hashlib.sha256(body.encode()).hexdigest() == row['configHash']
             and row['moves'] == value['movesProposal'] and row['goals'] == value['goals']
             and row['reward'] == {'coins': 50, 'stars': 1}, 'Server attempt catalog differs from Unity')
    cleanup = proof.read('Attempts/backend_001_cleanup/Service_Tests.json')
    prior = proof.read('Attempts/backend_002_precredit_terminal_review/Service_Tests.json')
    need(cleanup['status'] == 'FAIL_BACKEND_SERVICE_TESTS' and cleanup['tests'] == 48
         and not cleanup['failures'] and len(cleanup['errors']) == 1,
         'Failed SQLite fixture-cleanup attempt was not preserved as a failure')
    need(prior['status'] == 'PASS_BACKEND_SERVICE_TESTS' and prior['tests'] == 50,
         'Earlier pre-credit refund coverage review was rewritten')
    proof.file('Attempts/backend_001_cleanup/Reason.txt')
    proof.file('Attempts/backend_002_precredit_terminal_review/Reason.txt')
    refund = proof.read('Backend/RefundFix52/Service_Tests.json')
    need(refund['status'] == 'PASS_BACKEND_SERVICE_TESTS' and refund['tests'] == 52
         and refund['sourceSHA256'] == refund['sourceSHA256After'] and not refund['sourceInputsChangedDuringRun'],
         'Pre-wallet sticky refund race proof is missing')
    old_wallet = proof.read('Backend/Wallet89_PreAdditionalCase/Service_Tests.json')
    need(old_wallet['status'] == 'PASS_BACKEND_SERVICE_TESTS' and old_wallet['tests'] == 89
         and old_wallet['sourceSHA256'] == old_wallet['sourceSHA256After']
         and not old_wallet['sourceInputsChangedDuringRun']
         and utc(refund['utc']) < utc(old_wallet['startedUtc']) < utc(old_wallet['utc']) < utc(report['startedUtc']),
         'Preserved pre-additional-case wallet proof/chronology differs')
    proof.file('Backend/Wallet89_PreAdditionalCase/Reason.txt')
    before_scope = proof.read('Backend/Wallet90_BeforeScopeClarification/Service_Tests.json')
    need(before_scope['status'] == 'PASS_BACKEND_SERVICE_TESTS' and before_scope['tests'] == 90
         and before_scope['sourceSHA256'] == before_scope['sourceSHA256After']
         and not before_scope['sourceInputsChangedDuringRun']
         and utc(before_scope['utc']) < utc(report['startedUtc']), 'Earlier90-case scope-clarification proof differs')
    proof.file('Backend/Wallet90_BeforeScopeClarification/Source_Current_Review.json')
    proof.file('Backend/Wallet90_BeforeScopeClarification/Reason.txt')
    current_review = proof.read('Backend/Source_Current_Review.json')
    need(current_review['status'] == 'READ_ONLY_POST_TEST_BACKEND_SOURCE_REVIEW'
         and current_review['testReportSHA256'] == sha(proof.file('Backend/Service_Tests.json'))
         and current_review['sourceSHA256'] == actual and current_review['sourceInputs'] == len(actual)
         and current_review['allCurrentSourcesMatchRecordedEnd'] is True
         and utc(report['utc']) <= utc(current_review['utc']), 'Current backend source readback differs')
    contract, origin = proof.read('Backend/OpenAPI.json'), proof.read('Backend/Contract_Source.json')
    need(origin['status'] == 'EXPORTED_CURRENT_BACKEND_API_CONTRACT_NOT_NETWORK_TEST'
         and origin['testReportSHA256'] == sha(proof.file('Backend/Service_Tests.json'))
         and origin['openAPISHA256'] == sha(proof.file('Backend/OpenAPI.json'))
         and utc(report['utc']) <= utc(origin['utc']), 'API contract export source/chronology differs')
    need(all(name in contract['paths'] for name in ('/v1/wallet', '/v1/wallet/ledger', '/v1/wallet/refill',
                                                   '/v1/attempts/reserve', '/internal/v1/attempts/settle',
                                                   '/v1/commerce/orders/{order_id}/reconcile')),
         'Current exported API omitted a required authority boundary')
    return {'status': report['status'], 'tests': report['tests'], 'seconds': report['seconds'],
            'scope': report['scope'], 'schema': 3, 'source_inputs': len(actual),
            'wallet': 'real portable staging ledger/typed attempt spends; no normal Unity profile migration',
            'store_scope': 'ephemeral RSA/mocked HTTPS and synthetic verified invoices; no real RuStore payment'}


def native_process(proof, mode, report_name, current, source_utc, build=False):
    run = proof.read('Native/' + mode + '_Process.json')
    report = proof.read(report_name)
    clean(report, mode)
    before, after = proof.read(run['sourceManifest']), proof.read(run['afterSourceManifest'])
    need(run['mode'] == mode and run['exitCode'] == 0 and run['timedOut'] is False
         and run['version'].startswith('2022.3.62f3') and run['inputCount'] == len(current), 'Native process failed: ' + mode)
    need(before['files'] == after['files'] == current
         and sha(proof.file(run['sourceManifest'])) == run['sourceSHA256']
         and sha(proof.file(run['afterSourceManifest'])) == run['afterSourceSHA256'], 'Native source binding differs: ' + mode)
    need(source_utc <= utc(before['utc']) <= utc(run['startedUtc']) <= utc(report['utc'])
         <= utc(after['utc']) <= utc(run['finishedUtc']), 'Native chronology differs: ' + mode)
    need(run['report'] == report_name and run['reportSHA256'] == sha(proof.file(report_name))
         and run['logSHA256'] == sha(proof.file(run['log'])), 'Native report/log binding differs: ' + mode)
    need(run['historicalReportsRestored'] is True and run['intentionalConfigurationMutation'] is False
         and run['temporaryBuildSettingsRestored'] is build, 'Native restoration differs: ' + mode)
    need(not any(proof.read('Native/' + mode + '_Input_Delta.json').values()), 'Native input delta nonempty: ' + mode)
    if run.get('delegatedProcess'):
        delegated = run['delegatedProcess']
        original = 'Native/' + mode + '/Artifacts/Native/' + mode
        need(proof.read(original + '_Process.json') == delegated and sha(proof.file(original + '.log')) == run['logSHA256'],
             'Original delegated process/log was not preserved: ' + mode)
        need(delegated['exitCode'] == 0 and delegated['timedOut'] is False
             and utc(run['startedUtc']) <= utc(delegated['startedUtc']) <= utc(report['utc'])
             <= utc(delegated['finishedUtc']) <= utc(run['finishedUtc']), 'Delegated process failed: ' + mode)
    else:
        need(mode in ('Guard', 'Http', 'Preflight'), 'Missing delegated process: ' + mode)
    return report, run


def preserved_native_attempts(proof, current):
    results = []
    for name, checks in (('001_packageinfo_ambiguity', 0), ('002_inline_json_nulls', 267)):
        base = 'Attempts/' + name + '/'
        reason, frozen = proof.read(base + 'Reason.json'), proof.read(base + 'Source_SHA256.json')
        process = proof.read(base + 'Native/Guard_Process.json')
        before, after = proof.read(base + process['sourceManifest']), proof.read(base + process['afterSourceManifest'])
        need(reason['countedAsPass'] is False and reason['reason'] and process['exitCode'] == 1
             and process['timedOut'] is False and process['inputCount'] == 5182
             and before['files'] == after['files'] == frozen['files']
             and set(frozen['files']) == set(current)
             and all(current[p] == digest for p, digest in frozen['files'].items() if p not in ADDED),
             'Failed attempt source/status was not preserved: ' + name)
        need(sha(proof.file(base + process['sourceManifest'])) == process['sourceSHA256']
             and sha(proof.file(base + process['afterSourceManifest'])) == process['afterSourceSHA256']
             and sha(proof.file(base + process['log'])) == process['logSHA256']
             and utc(frozen['utc']) <= utc(before['utc']) <= utc(process['startedUtc'])
             <= utc(after['utc']) <= utc(process['finishedUtc']) <= utc(reason['utc']),
             'Failed attempt chronology/hash differs: ' + name)
        for path in ADDED:
            need(sha(proof.file(base + 'Inputs/' + path)) == frozen['files'][path], 'Failed source copy differs: ' + name)
        if checks:
            report = proof.read(base + 'Native/RuStore81.json')
            need(report['status'] == 'FAIL_NATIVE_RUSTORE81_RELEASE_GUARD' and report['checks'] == checks
                 and len(report['errors']) == 6
                 and utc(process['startedUtc']) <= utc(report['utc']) <= utc(process['finishedUtc'])
                 and sha(proof.file(base + 'Native/RuStore81.json')) == process['reportSHA256'],
                 'Failed native assertions were counted/replaced: ' + name)
        else:
            need('error CS0104' in proof.file(base + process['log']).read_text('utf-8-sig'), 'Original compile failure missing')
        proof.file(base + 'Source_Delta.json')
        results.append({'attempt': name, 'checks_executed': checks, 'exit_code': 1, 'counted_as_pass': False,
                        'source_sha256': sha(proof.file(base + 'Source_SHA256.json'))})
    return results


def http_proof(proof, report, native_run):
    process, restart = proof.read('Backend/HTTP_Process.json'), proof.read('Backend/HTTP_Restart.json')
    tests = proof.read('Backend/Service_Tests.json')
    clean(process, 'HTTP fixture process')
    clean(report, 'Native HTTP client')
    need(process['status'] == 'PASS_RUSTORE81_NATIVE_HTTP_AND_PROCESS_RESTART'
         and restart['status'] == 'PASS_RUSTORE81_ACTUAL_HTTP_PROCESS_RESTART'
         and process['runId'] == restart['runId'] == report['runId']
         and process['backendTestReportSHA256'] == sha(proof.file('Backend/Service_Tests.json'))
         and process['nativeReportSHA256'] == restart['nativeReportSHA256'] == sha(proof.file('Native/HTTP.json'))
         and process['restartReportSHA256'] == sha(proof.file('Backend/HTTP_Restart.json'))
         and restart['sourceSHA256'] == tests['sourceSHA256After'], 'HTTP process/report/source binding differs')
    need(report['checks'] == len(report['passed']) and report['checks'] > 0
         and report['requests'] >= 20 and report['duplicateCommands'] == 5
         and report['finalCoins'] == 2250 and report['finalLives'] == 4 and report['finalRevision'] == 6
         and report['finalStarting'] == [4, 5, 3, 2] and report['finalTools'] == [2, 3, 3, 3]
         and report['ordinaryProfileIntegrationDisabled'] is True, 'Actual typed HTTP result/coverage differs')
    stages = process['stages']
    need(len(stages) == 2 and stages[0]['resume'] is False and stages[1]['resume'] is True
         and type(stages[0]['pid']) is int and type(stages[1]['pid']) is int
         and stages[0]['pid'] != stages[1]['pid'] and min(s['pid'] for s in stages) > 0,
         'No actual separate server process restart was recorded')
    need(utc(process['startedUtc']) <= utc(stages[0]['startedUtc']) <= utc(native_run['startedUtc'])
         <= utc(native_run['finishedUtc']) <= utc(restart['startedUtc']) <= utc(stages[0]['stoppedUtc'])
         <= utc(stages[1]['startedUtc']) <= utc(restart['afterStartedUtc']) <= utc(restart['utc'])
         <= utc(stages[1]['stoppedUtc']) <= utc(process['finishedUtc']), 'HTTP server/native/restart chronology differs')
    need(restart['before'] == restart['after'], 'State changed across real server restart')
    state = restart['after']
    wallet, ledger, order = state['wallet'], state['ledger'], state['order']
    need(wallet['initialized'] is True and wallet['balanceScope'] == 'server_wallet' and wallet['coins'] == 2250
         and wallet['lives'] == 4 and wallet['revision'] == 6 and wallet['starting'] == [4, 5, 3, 2]
         and wallet['tools'] == [2, 3, 3, 3] and wallet['activeAttempt'] is None
         and wallet['productionEnabled'] is False and wallet['normalUnityProfileIntegrated'] is False
         and wallet['localProfileMutated'] is False and wallet['refundReviewRequired'] is False,
         'HTTP restart wallet scope/balance differs')
    need(order['orderId'] == report['orderId'] and order['state'] == 'Confirmed'
         and order['credit']['coins'] == 1000 and order['availableToSpend'] is True
         and order['balanceScope'] == 'server_wallet' and order['localProfileMutated'] is False
         and ledger['hasMore'] is False and len(ledger['entries']) == 6
         and sum(e['origin'].startswith('commerce/') for e in ledger['entries']) == 1,
         'HTTP restart purchase/ledger result differs')
    totals = [sum(e['delta'][i] for e in ledger['entries']) for i in range(11)]
    need(totals == [wallet['coins'], wallet['stars'], *wallet['starting'], *wallet['tools'], wallet['lives']]
         and [e['revision'] for e in ledger['entries']] == list(range(1, 7)), 'HTTP ledger does not reconcile')
    proof.ext(process['fixtureSource'], process['fixtureSHA256'])
    proof.ext(process['probeSource'], process['probeSHA256'])
    proof.ext('Verification/Run-RuStore81Http.ps1')
    return {'status': process['status'], 'native_checks': report['checks'], 'requests': report['requests'],
            'exact_command_retries': report['duplicateCommands'], 'different_server_processes': True,
            'durable_coins': 2250, 'durable_lives': 4, 'durable_ledger_entries': 6,
            'scope': process['scope'], 'real_store_payment': False}


def sdk_spike(proof):
    report, process = proof.read('SDK_Editor/Report.json'), proof.read('SDK_Editor/Process.json')
    clean(report, 'Isolated SDK spike')
    need(report['status'] == 'PASS_ISOLATED_EDITOR_RUSTORE81_SDK_API'
         and report['unity'] == '2022.3.62f3' and report['payVersion'] == '11.1.0'
         and report['coreVersion'] == '10.5.0' and process['exitCode'] == 0
         and utc(process['startedUtc']) <= utc(report['utc']) <= utc(process['finishedUtc']), 'Isolated SDK compile proof differs')
    need(report['payPackageUnity'] == report['corePackageUnity'] == '6000.0',
         'Stock official package Editor support metadata was silently changed')
    need(all(report[k] is True for k in ('appUserIdSupported', 'requestCorrelationRetained', 'productsMethod',
                                          'recoveryMethods', 'confirmationAndAcknowledgementSeparate')),
         'Verified SDK API surface missing')
    proof.file('SDK_Editor/Unity.log')
    manifest, lock = proof.read('SDK_Editor/manifest.json'), proof.read('SDK_Editor/packages-lock.json')
    for name, version, field in (('ru.rustore.pay', '11.1.0', 'pay'), ('ru.rustore.core', '10.5.0', 'core')):
        need(manifest['dependencies'][name] == lock['dependencies'][name]['version'] == version
             and lock['dependencies'][name]['source'] == 'registry', 'Isolated official SDK dependency differs')
        package = Path(report[field + 'ResolvedPath']) / 'package.json'
        relative = package.resolve().relative_to(ROOT.resolve()).as_posix()
        metadata = json.loads(proof.ext(relative, report[field + 'ManifestSHA256']).read_text('utf-8-sig'))
        need(metadata['name'] == name and metadata['version'] == version and metadata['unity'] == '6000.0',
             'Isolated official package metadata differs')
    proof.file('SDK_Editor/RuStoreSdkSpike81.cs')
    failed = 'Attempts/sdk_001_spike_namespace/'
    prior = proof.read(failed + 'Process.json')
    need(prior['exitCode'] == 1 and utc(prior['finishedUtc']) < utc(process['startedUtc']),
         'Initial failed SDK namespace probe was reclassified or lost')
    for name in ('Reason.txt', 'RunSpike.ps1', 'Unity.log', 'Assets/Editor/RuStoreSdkSpike81.cs',
                 'Packages/manifest.json', 'Packages/packages-lock.json'):
        proof.file(failed + name)
    return {'status': report['status'], 'pay': report['payVersion'], 'core': report['coreVersion'],
            'stock_package_unity_metadata': '6000.0', 'scope': report['scope'],
            'native_payment_executed': False, 'main_project_sdk_installed': False}


def sdk_android(proof):
    base = 'SDK_Android/'
    exported = proof.read(base + 'Export/AndroidExport.json')
    process = proof.read(base + 'Export/AndroidExportProcess.json')
    inputs = proof.read(base + 'Inputs/Manifest.json')
    clean(exported, 'Isolated Android export')
    clean(process, 'Isolated Android export process')
    need(exported['status'] == 'PASS_ISOLATED_ANDROID_RUSTORE81_GRADLE_EXPORT'
         and exported['unity'] == '2022.3.62f3' and exported['errors'] == 0
         and exported['actualAdapterSdkBranchCompiled'] is True and exported['syntheticConfiguration'] is True
         and exported['apkLaunched'] is False and exported['jdkSettingsUnchanged'] is True
         and exported['jdkRootBefore'] == exported['jdkRootDuring'] == exported['jdkRootAfter']
         and all(exported[k] is True for k in ('jdkEmbeddedBefore', 'jdkEmbeddedDuring', 'jdkEmbeddedAfter'))
         and 'JAVA_VERSION="11.' in exported['jdkRelease']
         and exported['gradleVersion'] == '7.5.1' and exported['agpVersion'] == '7.4.2'
         and exported['payVersion'] == '11.1.0' and exported['coreVersion'] == '10.5.0'
         and exported['minApi'] == 26 and exported['targetApi'] == 34,
         'Isolated supported-Java11 export/SDK branch proof differs')
    need(process['exitCode'] == 0 and process['timedOut'] is False and process['pid'] > 0
         and process['unity'].startswith('2022.3.62f3') and process['sdkManagerOptionsRestored'] is True
         and utc(process['startedUtc']) <= utc(exported['utc']) <= utc(process['finishedUtc']),
         'Actual isolated Unity export process failed')
    proof.file(base + 'Export/AndroidExportUnity.log')
    need(inputs['fixtureRevision'] == 'R2_manifest_label_fix_fresh_export' and len(inputs['files']) == 17,
         'Final R2 fixture input archive differs')
    for row in inputs['files']:
        need(sha(proof.file(base + 'Inputs/' + row['path'])) == row['sha256'], 'Archived SDK fixture input changed')
    need(sha(proof.file(base + 'Inputs/RunAndroidExportSpike.ps1')) == process['scriptSHA256'],
         'Isolated export runner source differs')
    indexed = {r['path']: r['sha256'] for r in inputs['files']}
    for row in exported['sourceBindings']:
        need(indexed.get('Spike/' + row['path']) == row['sha256'], 'Export no longer corresponds to archived R2 source')
        if row['path'].startswith('Assets/Integration/'):
            main = 'Unity/Assets/HeartOfTheRain/App/RuStore/Runtime/' + Path(row['path']).name
            proof.ext(main, row['sha256'])
    assembly = proof.read(base + 'Assembly/AndroidAssembly.json')
    clean(assembly, 'Isolated standalone Android assembly')
    need(assembly['status'] == 'PASS_ISOLATED_ANDROID_RUSTORE81_STANDALONE_ASSEMBLY'
         and assembly['apkLaunched'] is False and assembly['syntheticConfiguration'] is True
         and assembly['sourceBindings'] == exported['sourceBindings']
         and assembly['exportBindings'] == exported['exportBindings']
         and assembly['exportReportSHA256'] == sha(proof.file(base + 'Export/AndroidExport.json'))
         and assembly['exportProcessSHA256'] == sha(proof.file(base + 'Export/AndroidExportProcess.json')),
         'Standalone SDK assembly is not the actual final export')
    need(utc(process['finishedUtc']) <= utc(assembly['startedUtc']) <= utc(assembly['finishedUtc'])
         and [s['name'] for s in assembly['steps']] == ['GradleVersion17', 'GradleDependencies17', 'GradleAssemble17'],
         'Standalone assembly steps/chronology differ')
    for step in assembly['steps']:
        need(step['exitCode'] == 0 and step['timedOut'] is False and step['handleRetained'] is True and step['pid'] > 0
             and utc(assembly['startedUtc']) <= utc(step['startedUtc']) <= utc(step['finishedUtc']) <= utc(assembly['finishedUtc']),
             'Standalone Gradle has no actual successful process exit')
        for stream in ('stdout', 'stderr'):
            need(sha(proof.file(base + 'Assembly/' + Path(step[stream]).name)) == step[stream + 'SHA256'],
                 'Standalone Gradle raw log differs')
    version = proof.file(base + 'Assembly/GradleVersion17.stdout.log').read_text('utf-8-sig')
    need('Gradle 7.5.1' in version and re.search(r'JVM:\s+17\.', version), 'Actual standalone Java/Gradle version differs')
    apk = Path(assembly['apk']).resolve()
    need(apk.is_relative_to((ROOT / '.verification-cache/RuStore81').resolve())
         and proof.ext(apk.relative_to(ROOT).as_posix(), assembly['apkSHA256']).stat().st_size == assembly['apkBytes'],
         'Standalone fixture APK artifact differs')
    # Binary-manifest/graph checks are validated from the final inspector/raw
    # AAPT files below, not inferred merely from a successful Gradle exit.
    inspection = proof.read(base + 'Assembly/APK_Inspection.json')
    clean(inspection, 'Static isolated APK inspection')
    need(inspection['status'] == 'PASS_STATIC_UNLAUNCHED_RUSTORE81_SDK_APK_INSPECTION'
         and inspection['apkSHA256'] == assembly['apkSHA256'] and inspection['apkBytes'] == assembly['apkBytes']
         and inspection['packageId'] == 'com.heartoftherain.sdkspike'
         and inspection['minApi'] == 26 and inspection['targetApi'] == 34
         and inspection['payVersion'] == '11.1.0' and inspection['coreVersion'] == '10.5.0'
         and inspection['apkLaunched'] is False and inspection['syntheticConfiguration'] is True
         and len(inspection['checks']) == 88 and len(inspection['bindings']) == 17
         and utc(assembly['finishedUtc']) <= utc(inspection['utc']), 'Isolated final APK inspection is incomplete')
    proof.ext('Verification/Tools/Inspect-RuStore81SdkApk.ps1', inspection['toolSHA256'])
    for row in inspection['bindings']:
        need(sha(proof.file(base + 'Assembly/' + row['path'])) == row['sha256'], 'Static SDK APK input changed')
    tree = proof.file(base + 'Assembly/APK_Manifest.xmltree.txt').read_text('utf-8-sig')
    badging = proof.file(base + 'Assembly/APK_Badging.txt').read_text('utf-8-sig')
    need("sdkVersion:'26'" in badging and "targetSdkVersion:'34'" in badging and 'arm64-v8a' in badging,
         'Actual fixture APK API/ABI badging differs')
    need("package: name='com.heartoftherain.sdkspike'" in badging
         and re.search(r'(?m)^native-code: \'arm64-v8a\'\s*$', badging)
         and re.search(r'RuStorePayContentProvider[^\r\n]*\r?\n[^\r\n]*enabled[^\r\n]*0xffffffff\r?\n[^\r\n]*exported[^\r\n]*0x0', tree)
         and 'com.heartoftherain.sdkspike.sdk.pay' in tree
         and 'RuStoreDeeplinkActivityDefault' in tree, 'Actual binary SDK provider/deeplink is missing')
    resources = proof.file(base + 'Assembly/APK_Resources.txt').read_text('utf-8-sig')
    expected_resources = {'rustore_PayClientSettings_consoleApplicationId': '123456',
                          'rustore_PayClientSettings_deeplinkScheme': 'hotr-spike-build-only',
                          'rustore_PayClientSettings_internalConfigKey': 'unity'}
    need({r['name']: r['value'] for r in inspection['resources']} == expected_resources, 'Synthetic APK resource values differ')
    ids = {r['name']: r['id'] for r in inspection['resources']}
    for name, expected in expected_resources.items():
        need(re.search(r'resource\s+' + re.escape(ids[name]) + r'\s+[^\r\n]*:string/' + re.escape(name)
                       + r':[^\r\n]*(?:\r?\n(?![^\r\n]*\bresource\s+0x)[^\r\n]*){0,8}?'
                       + r'\(string(?:8|16)\)\s+"' + re.escape(expected) + '"', resources),
             'Actual binary resource does not match SDK synthetic metadata: ' + name)
    for name, key in (('console_app_id_value', 'rustore_PayClientSettings_consoleApplicationId'),
                      ('sdk_pay_scheme_value', 'rustore_PayClientSettings_deeplinkScheme'),
                      ('internal_config_key', 'rustore_PayClientSettings_internalConfigKey')):
        need(re.search(r'android:name[^\r\n]*"' + name + r'"[^\r\n]*\r?\n\s+A: android:value[^\r\n]*=@'
                       + re.escape(ids[key]), tree), 'Binary metadata/resource binding differs')
    need(re.search(r'android:scheme[^\r\n]*=@' + re.escape(ids['rustore_PayClientSettings_deeplinkScheme']), tree),
         'Binary deep-link scheme uses another resource')
    graph = proof.file(base + 'Assembly/GradleDependencies17.stdout.log').read_text('utf-8-sig')
    for module, version in (('pay', '11.1.0'), ('core', '10.5.0')):
        found = re.findall(r'ru\.rustore\.sdk:' + module + r':([^\s]+)(?:\s+->\s+([^\s]+))?', graph)
        need(found and all((resolved or requested) == version for requested, resolved in found), 'Resolved native SDK graph differs')
    for row in assembly['generatedManifestBindings']:
        need(sha(proof.file(base + 'Assembly/MergedManifests/' + row['path'])) == row['sha256'], 'Merged native manifest differs')
    with zipfile.ZipFile(apk) as archive:
        need({'lib/arm64-v8a/libil2cpp.so', 'lib/arm64-v8a/libunity.so', 'classes.dex'} <= set(archive.namelist()),
             'Actual SDK fixture APK omitted IL2CPP/Unity/DEX')
    attempts = proof.read(base + 'Attempts/Manifest.json')
    need([r['attempt'] for r in attempts['attempts']] == ['001_jdk17_setter', '002_sdkmanager_query',
                                                        '003_short_process_exitcode', '004_manifest_label']
         and attempts['noFailedAttemptReclassified'] is True
         and sum(len(r['files']) for r in attempts['attempts']) == 131, 'SDK failure archive index differs')
    for attempt in attempts['attempts']:
        for row in attempt['files']:
            path = proof.file(base + 'Attempts/' + row['path'])
            need(row['path'].startswith(attempt['attempt'] + '/') and sha(path) == row['sha256']
                 and path.stat().st_size == row['bytes'], 'Preserved SDK failure artifact differs')
    return {'export': exported['status'], 'standalone_assembly': assembly['status'],
            'inspection': inspection['status'], 'static_checks': 88, 'fixture_apk_sha256': assembly['apkSHA256'],
            'embedded_unity_java': 11, 'standalone_java': 17, 'gradle': '7.5.1', 'agp': '7.4.2',
            'api': {'min': 26, 'target': 34}, 'actual_current_adapter_sdk_branch_compiled': True,
            'apk_launched': False, 'real_payment': False, 'vendor_support_certified': False,
            'scope': assembly['scope']}


def build_proof(proof, current, source_utc, native_runs):
    builds = {}
    for mode, report_name, expected, source_name in (
        ('AndroidReleaseBuild', 'Android_Release_Build.json', 'PASS_ANDROID_RELEASE_COMPILE_BUILD', 'Release_Source_SHA256.json'),
        ('AndroidBuild', 'Android_Build.json', 'PASS_ANDROID_DEVELOPMENT_BUILD', 'Build_Source_SHA256.json'),
    ):
        report, process = native_process(proof, mode, report_name, current, source_utc, build=True)
        need(report['status'] == expected and report['unity'] == '2022.3.62f3' and report['errors'] == 0,
             'Internal Android branch did not build: ' + mode)
        need(report['productName'] == '\u0421\u0435\u0440\u0434\u0446\u0435 \u0434\u043e\u0436\u0434\u044f'
             and report['showSplashScreen'] is True and report['showUnityLogo'] is True
             and report['hasProLicense'] is False, 'Approved branding/license-required splash differs')
        need(proof.read(source_name)['files'] == current, 'Build source binding differs: ' + mode)
        temporary = proof.read('Native/' + mode + '_Temporary_Input_Delta.json')
        need(not temporary['added'] and not temporary['removed']
             and all(p.startswith('Unity/ProjectSettings/') for p in temporary['changed_existing']),
             'Temporary build changed non-settings inputs: ' + mode)
        builds[mode] = process
    need(max(utc(run['finishedUtc']) for run in native_runs.values()) <= utc(builds['AndroidReleaseBuild']['startedUtc'])
         <= utc(builds['AndroidReleaseBuild']['finishedUtc']) <= utc(builds['AndroidBuild']['startedUtc']),
         'Native/release/development build chronology differs')
    for name in ('Build_Import_Audit.txt', 'Release_Build_Import_Audit.txt'):
        need('Errors: 0' in proof.file(name).read_text('utf-8-sig'), 'Import guard failed: ' + name)
    artifact, packaging = proof.read('APK_Artifact.json'), proof.read('APK_Packaging.json')
    apk = ROOT / 'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
    digest = sha(apk)
    need(digest == artifact['sha256'] == packaging['afterSHA256']
         and apk.stat().st_size == artifact['bytes'] == packaging['afterBytes']
         and all(artifact[k] is True for k in ('zipalign4KiBPass', 'developmentSignatureVerifies', 'elf16KiBLoadSegmentsPass'))
         and packaging['status'] == 'PASS_CLEAN_GRADLE_APK_PACKAGING' and packaging['sameSignerCertificate'] is True
         and not packaging['changedNonSignatureEntries'], 'Final development APK integrity/packaging differs')
    need(utc(builds['AndroidBuild']['finishedUtc']) <= utc(packaging['utc']), 'Packaging predates its build')
    proof.ext('.verification-cache/RuStore81/Unity_Incremental.apk', packaging['beforeSHA256'])
    proof.file('Gradle_Clean.log')
    profile = proof.read('APK_Profile.json')
    need(profile['status'] == 'PASS_RUSTORE81_INTERNAL_APKS_SDK_FREE' and len(profile['artifacts']) == 2,
         'Actual SDK-free regression APK profile missing')
    need({Path(r['path']).name for r in profile['artifacts']} == {'HeartOfTheRain_Development.apk', 'HeartOfTheRain_ReleaseCompile.apk'},
         'One actual Android build branch was omitted')
    for row in profile['artifacts']:
        path = proof.ext(row['path'], row['sha256'])
        prefix = 'Development' if path.name == 'HeartOfTheRain_Development.apk' else 'ReleaseCompile'
        need(path.stat().st_size == row['bytes'] and row['package'] == 'com.heartoftherain.verification'
             and row['displayName'] == '\u0421\u0435\u0440\u0434\u0446\u0435 \u0434\u043e\u0436\u0434\u044f'
             and row['nativePayProviderAbsent'] is True and row['nativeRuStorePayCoreClassesAbsent'] is True,
             'Ordinary APK identity/SDK absence differs')
        badging = proof.file(prefix + '_Badging.txt').read_text('utf-8-sig')
        manifest = proof.file(prefix + '_Manifest.txt').read_text('utf-8-sig')
        need("package: name='com.heartoftherain.verification'" in badging
             and "application-label:'\u0421\u0435\u0440\u0434\u0446\u0435 \u0434\u043e\u0436\u0434\u044f'" in badging
             and 'RuStorePayContentProvider' not in manifest and 'android:screenOrientation' in manifest,
             'Actual ordinary APK manifest/label differs')
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if re.fullmatch(r'classes\d*\.dex', name):
                    body = archive.read(name)
                    need(b'Lru/rustore/sdk/pay/' not in body and b'Lru/rustore/sdk/core/' not in body,
                         'Unconfigured main APK contains the native RuStore SDK')
    return {'development_sha256': digest, 'development_bytes': artifact['bytes'],
            'release_compile': 'PASS_ANDROID_RELEASE_COMPILE_BUILD', 'development': 'PASS_ANDROID_DEVELOPMENT_BUILD',
            'store_release': False, 'production_sdk_activated': False}, packaging


def device_proof(proof, baseline, source_digest, apk_digest, packaging_utc):
    target = proof.read('QA_Target.json')
    need(target['status'] == 'AUTHORIZED_ISOLATED_RUSTORE81_REGRESSION_QA'
         and target['serial'] == 'emulator-5558' and target['index'] == 2
         and target['name'] == 'Heart of the Rain QA79 isolated' and target['activeAttempts'] == 0
         and target['mainAndOriginalQAStopped'] is True,
         'QA2 target/active-attempt protection differs')
    prior_path = proof.ext('Verification/Evidence/Gameplay79/QA_Target.json', target['priorTargetSHA256'])
    prior = json.loads(prior_path.read_text('utf-8-sig'))
    need(prior['target'] == {'index': 2, 'serial': 'emulator-5558', 'name': target['name']}, 'Original QA2 authorization differs')
    rows = target['list2'].splitlines()
    need(rows[0].startswith('0,LDPlayer,0,0,0,-1,-1,')
         and rows[1].startswith('1,Heart of the Rain QA,0,0,0,-1,-1,')
         and rows[2].startswith('2,Heart of the Rain QA79 isolated,'), 'Main/original QA isolation evidence differs')
    device = proof.read('Android/Installation.json')
    clean(device, 'Android device')
    need(device['status'] == 'PASS_RUSTORE81_REGRESSION_DEVICE_AUDIT' and device['serial'] == target['serial']
         and device['activeAttempts'] == 0 and device['installedBeforeSHA256'] == baseline['apk_sha256']
         and device['apk_sha256'] == device['installed_apk_sha256'] == apk_digest
         and device['source_sha256'] == source_digest and device['targetSHA256'] == sha(proof.file('QA_Target.json'))
         and device['data_unchanged'] is True and device['before'] == device['after']
         and device['before']['preferences'] and device['before']['saves']
         and device['portrait'] is True and device['runtime_errors'] == 0 and 'Success' in device['install'],
         'Android save/install/runtime regression proof differs')
    need(packaging_utc <= utc(target['utc']) <= utc(device['utc']) <= utc(device['finishedUtc']), 'Android proof chronology differs')
    logs = proof.file('Android/Runtime.log').read_text('utf-8-sig')
    need(not re.search(r'FATAL EXCEPTION|Fatal signal|NullReferenceException|MissingReferenceException|IndexOutOfRangeException', logs),
         'Android raw runtime log contradicts zero-error audit')
    review = proof.read('Device_Visual_Notes.json')
    required = {'Android/FirstStart_Russian.png', 'Android/FirstStart_Language_Menu.png'}
    inspected = {r['file'] for r in review['reviewed']}
    need(review['status'] == 'REVIEWED_RUSTORE81_ACTUAL_ANDROID_STARTUP_AND_LANGUAGE' and review['source_sha256'] == source_digest
         and review['apk_sha256'] == apk_digest and review['serial'] == target['serial']
         and inspected == required and all(r['observation'] for r in review['reviewed']) and review['scope']
         and utc(device['finishedUtc']) <= utc(review['utc']), 'Actual current device visual review is incomplete/stale')
    need(inspected <= review['artifactSHA256'].keys(), 'Reviewed media lacks hash binding')
    for name, digest in review['artifactSHA256'].items():
        need(sha(proof.file(name)) == digest, 'Changed device review input: ' + name)
    proof.file('Android/Cold_Start.mp4')  # Retained recording; no timing/visual verdict is inferred from its presence.
    return {'status': device['status'], 'serial': device['serial'], 'qa_index': 2, 'data_unchanged': True,
            'runtime_errors': 0, 'portrait': True, 'installed_checkpoint': 81,
            'original_qa_checkpoint': 78, 'main_checkpoint': 64, 'native_payment_tested': False,
            'review': review['status'], 'actually_reviewed_screenshots': 2, 'startup_movie_reviewed_for_timing': False}


def implementation_and_presentation(proof, source_digest):
    review = proof.read('Implementation_Review.json')
    required = {'Source_SHA256.json', 'Source_Delta.json', 'Backend/Service_Tests.json',
                'Backend/HTTP_Restart.json', 'Backend/HTTP_Process.json', 'Native/RuStore81.json',
                'Native/HTTP.json', 'Native/Release_Preflight.json',
                'SDK_Android/Assembly/APK_Inspection.json', 'APK_Profile.json', 'Device_Visual_Notes.json'}
    need(review['status'] == 'REVIEWED_RUSTORE81_PORTABLE_AUTHORITY_WITH_RELEASE_GATES'
         and review['source_sha256'] == source_digest and review['checks']
         and review['independentReview'] and review['scope']
         and required <= review['evidenceSHA256'].keys(), 'Current bounded implementation review is incomplete')
    for name, digest in review['evidenceSHA256'].items():
        need(sha(proof.file(name)) == digest, 'Changed implementation-review evidence: ' + name)
    required_sources = {'Backend/hotr_backend/' + name + '.py' for name in (
        'api', 'commerce', 'commerce_schemas', 'rustore_auth', 'rustore_provider', 'service',
        'storage', 'wallet', 'wallet_schemas')}
    required_sources |= {p for p in ADDED if p.endswith('.cs') and '/App/RuStore/' in p}
    required_sources |= {'Release/RuStore/README.md', 'Release/RuStore/release.example.json', 'Release/RuStore/sdk-lock.json'}
    need(required_sources <= review['reviewedSourceSHA256'].keys(), 'Implementation review omitted an authority/client boundary')
    for name, digest in review['reviewedSourceSHA256'].items():
        proof.ext(name, digest)
    need(max(utc(proof.read(name)['utc']) for name in (
        'Device_Visual_Notes.json', 'SDK_Android/Assembly/APK_Inspection.json')) <= utc(review['utc']),
        'Implementation review predates its actual proof')
    index = proof.read('Review_Index.json')
    need(index['status'] == 'GENERATED_FROM_ACTUAL_RUSTORE81_PROOF_NOT_NEW_TEST'
         and required - {'Backend/HTTP_Process.json', 'Native/Release_Preflight.json'} <= index['inputSHA256'].keys()
         and {'Implementation_Review.json', 'APK_Artifact.json', 'Android/Installation.json'} <= index['inputSHA256'].keys()
         and index['scope'] and utc(review['utc']) <= utc(index['utc']), 'Actual-proof gallery index is incomplete/stale')
    proof.ext('Verification/Tools/build_rustore81_review.py', index['toolSHA256'])
    for name, digest in index['inputSHA256'].items():
        need(sha(proof.file(name)) == digest, 'Changed gallery input: ' + name)
    need(sha(proof.file('Comparison.html')) == index['htmlSHA256'], 'Gallery HTML differs from its generated index')
    return {'status': review['status'], 'reviewed_source_inputs': len(review['reviewedSourceSHA256']),
            'presentation': index['status'], 'new_test_claim_from_gallery': False}


def build():
    # Fail closed until all actual native/build/device/reviewer records exist.
    proof = Proof()
    baseline, source, delta = source_and_baseline(proof)
    package, backend, spike = package_review(proof), backend_review(proof), sdk_spike(proof)
    configuration = release_configuration(proof)
    failures = preserved_native_attempts(proof, source['files'])
    source_digest = sha(proof.file('Source_SHA256.json'))
    native, runs = {}, {}
    for mode, (path, status) in SUITES.items():
        report, process = native_process(proof, mode, path, source['files'], utc(source['utc']))
        need(report['status'] == status, 'Unexpected actual native status: ' + mode)
        native[mode], runs[mode] = report, process
    preflight = native['Preflight']
    need(preflight['activationReady'] is False and preflight['configStatus'] == 'not_configured'
         and preflight['projectSettingsUnchanged'] is True and preflight['blockers'], 'Release preflight stopped blocking missing integrations')
    guard = native['Guard']
    need(guard['checks'] >= 328 and guard['inputMutations'] == 102 and guard['coinMappings'] == 6
         and guard['continuedPurchases'] == 2 and guard['coordinatorCases'] == 13
         and guard['diskJournalCases'] == 6 and guard['clientCases'] == 4
         and all(guard[name] is True for name in ('settingsUnchanged', 'preferencesUnchanged', 'environmentRestored',
                                                'actualReleaseBlocked', 'ordinaryBuildChannelUnaffected', 'proposalNotRegistered'))
         and guard['projectSettingsBefore'] == guard['projectSettingsAfter'],
         'Native current release/journal/coordinator/client negative coverage differs')
    need(preflight['payVersion'] == preflight['coreVersion'] == 'not_installed'
         and set(('production_identity_and_secure_credential_recovery_not_connected',
                  'unified_server_gameplay_wallet_not_connected', 'provider_notification_authentication_not_configured',
                  'native_sandbox_and_external_bank_return_not_verified',
                  'production_signing_and_legal_hosting_review_not_complete')) <= set(preflight['blockers']),
         'Main SDK absence/real integration gates were falsely cleared')
    http = http_proof(proof, native['Http'], runs['Http'])
    build_result, packaging = build_proof(proof, source['files'], utc(source['utc']), runs)
    device = device_proof(proof, baseline, source_digest, build_result['development_sha256'], utc(packaging['utc']))
    android_sdk = sdk_android(proof)
    review = implementation_and_presentation(proof, source_digest)
    counts = {mode: len(r['checks']) if isinstance(r.get('checks'), list) else r.get('checks', 0)
              for mode, r in native.items()}
    need(counts == {'Guard': 328, 'Http': 38, 'Preflight': 0, 'Checks': 534,
                    'ProfileChecks': 13584, 'PlaySmoke': 18, 'PortraitChecks': 18},
         'Actual targeted native coverage/counts differ')
    for path in ('Verification/Run-RuStore81.ps1', 'Verification/Run-RuStore81Http.ps1',
                 'Verification/Tools/collect_rustore81_results.py', 'Verification/Tools/collect_results.py',
                 'Verification/Tools/run_rustore81_device.py', 'Verification/Tools/check_rustore81_apks.py',
                 'Verification/Tools/Inspect-RuStore81SdkApk.ps1',
                 'Codex_Handoff/Documentation/81_RUSTORE_BACKEND_AND_RELEASE_FOUNDATION_REVIEW.md'):
        proof.ext(path)
    gates = [
        'No registered RuStore Console application, production product IDs, signing identity, payment-return scheme, public HTTPS backend or hosted legal URLs is configured. Candidate identifiers are unregistered proposals; release preflight and live checkout remain blocked.',
        'The portable server wallet, typed spends and durable purchase/reward projection work in local/staging tests. Normal Unity profile/wallet routing remains unchanged and unmigrated; historical server accounts receive no invented genesis or imported local balance.',
        'Production identity/secure recovery, account linking/deletion and retention policy, authenticated gameplay verification, offline board recovery, production hosting/TLS and operational review remain required. Privileged synthetic verifier tests are not proof of real gameplay verification.',
        'Staging/sandbox wallets and credits must never be promoted to live balances. Refund/reversal quarantine is durable, but real refund/debt review and compensation policy remain unresolved.',
        'Authenticated provider notifications, deployed reconciliation/delivery workers and real SDK sandbox checkout, external bank return, process-kill recovery and store acceptance have not been tested.',
        'The isolated official SDK11.1/Core10.5 fixture compiled in pinned Unity and assembled using separate Java17, with88 actual static APK checks. Its APK was never launched; stock package metadata requests Unity6000.0. This is not runtime certification or a vendor-support claim for pinned2022.3.62f3.',
        'Both main internal APKs intentionally remain native RuStore-SDK-free and use verification identity/signing. No real store release or automatic profile-factory activation occurred.',
        'Device review covers two current isolated-QA2 Russian startup/language screenshots with unchanged saves and zero observed runtime errors. The retained cold-start movie was not reviewed for timing; full campaign, physical-device, bank-return and performance acceptance were not newly established.',
        'Existing source80 artwork, Resources, levels, gameplay and profile inputs are byte-unchanged. Prior79 unexplained359.614ms Update/366.029ms interval and dense-rendering limitations remain open; no new smoothness improvement is claimed.',
        'User confirmed no eligible Unity license is available; required splash remains enabled on pinned2022.3.62f3. No engine upgrade, splash bypass or license change occurred.',
    ]
    return {
        'status': STATUS, 'utc': datetime.now(timezone.utc).isoformat(), 'source_checkpoint': 81,
        'source_sha256': source_digest, 'source_inputs': len(source['files']),
        'apk_sha256': build_result['development_sha256'], 'apk_bytes': build_result['development_bytes'],
        'baseline_source_checkpoint': 80, 'baseline_source_sha256': baseline['source_sha256'],
        'baseline_apk_sha256': baseline['apk_sha256'], 'source_delta': delta,
        'package_review': package, 'backend': backend, 'actual_http': http,
        'native_suites': {mode: {'status': r['status'], 'checks': counts[mode]} for mode, r in native.items()},
        'native_suite_count': len(native), 'native_passed_suites': 6, 'native_expected_blocked_preflights': 1,
        'native_checks': sum(counts.values()), 'preserved_failed_native_attempts': failures,
        'configuration': configuration, 'sdk_editor': spike, 'sdk_android': android_sdk,
        'android_builds': build_result, 'android': device, 'implementation_review': review,
        'production_ready': False, 'normal_unity_profile_integrated': False,
        'real_store_payment_tested': False, 'release_activation_ready': False,
        'remainingGates': gates, 'evidence_sha256': dict(sorted(proof.artifacts.items())),
        'external_evidence_sha256': dict(sorted(proof.external.items())),
        'scope': 'Portable RuStore backend/release foundation with90 source-bound Python tests, seven targeted native entries (six passes and one intentionally blocked preflight),14520 native checks, real loopback Unity HTTP plus two-process restart proof, isolated official-SDK compile/export/Java17 assembly/static inspection, two SDK-free internal APK builds and save-preserving QA2 installation. Real payments, production wallet migration, public deployment and store release remain blocked.',
    }


def main(publish=False):
    result = build()
    if publish:
        text = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
        for path in (OUT / 'Summary.json', OUT.parent / 'Verification_Summary.json'):
            path.write_text(text, encoding='utf-8')
        checkpoint = {
            'utc': result['utc'], 'status': result['status'], 'source_checkpoint': 81,
            'last_verified_source_checkpoint': 81, 'installed_checkpoint': 64, 'qa_installed_checkpoint': 78,
            'isolated_qa_installed_checkpoint': 81, 'isolated_qa_serial': 'emulator-5558',
            'original_qa_active_attempt_preserved': True, 'source_sha256': result['source_sha256'],
            'android_apk_sha256': result['apk_sha256'], 'android_apk_matches_current_source': True,
            'main_installed_apk_matches_current_source': False, 'unity_splash_removal_complete': False,
            'production_ready': False, 'normal_unity_profile_integrated': False,
            'real_store_payment_tested': False, 'release_activation_ready': False,
            'review': 'Codex_Handoff/Documentation/81_RUSTORE_BACKEND_AND_RELEASE_FOUNDATION_REVIEW.md',
            'summary': 'Verification/Evidence/RuStore81/Summary.json', 'scope': result['scope'],
        }
        (OUT.parent / 'Native_Source_Checkpoint.json').write_text(
            json.dumps(checkpoint, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    print(json.dumps(main(args.publish), indent=2, ensure_ascii=False))
