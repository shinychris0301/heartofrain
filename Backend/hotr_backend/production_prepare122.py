"""Prepare a separate, disabled provider configuration bundle for the VPS.

This is configuration preparation, not a production launcher. In particular it
does not repurpose the existing staging authority, read credentials, migrate a
database, enable live payments, or accept operator assertions as provider proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from .payment_readiness122 import (
    evaluate_payment_readiness, load_public_json, prepare_payment_bundle,
)
from .provider_readiness122 import _public_https, assess_ads_and_vk


ROOT = Path(__file__).resolve().parents[2]
ORIGIN = 'https://api.novamind-it.ru'
BUNDLE_KIND = 'HeartOfTheRainProviderPreparation122'


def _write(directory, name, value):
    with (directory / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.write('\n')


def assess(directory):
    """Read only named public configuration files, never credential references."""
    directory = Path(directory)
    plan = load_public_json(directory / 'deployment.plan.json')
    if (plan.get('kind') != BUNDLE_KIND or type(plan.get('schemaVersion')) is not int
            or plan.get('schemaVersion') != 1
            or _public_https(plan.get('publicOrigin'), origin=True) is None):
        raise ValueError('provider_preparation_plan_invalid')
    release = load_public_json(directory / 'release.candidate.json')
    providers = load_public_json(directory / 'providers.candidate.json')
    catalogue = load_public_json(directory / 'payments/commerce.candidate.json')
    checkout = load_public_json(directory / 'payments/checkout.candidate.json')
    inventory = load_public_json(directory / 'payments/console-inventory.template.json')
    managed = load_public_json(directory / 'ManagedProduction.template.json')
    packaged_checkout = load_public_json(directory / 'CheckoutProduction.template.json')
    runtime_template = load_public_json(directory / 'production-runtime.template.json')
    environment = release.get('environment')
    environment_valid = type(environment) is str and environment in ('sandbox', 'production')
    payments = evaluate_payment_readiness(
        catalogue, checkout, console_inventory=inventory,
        expected_sandbox=(environment == 'sandbox') if environment_valid else None,
    )
    provider_report = assess_ads_and_vk(
        public_origin=plan['publicOrigin'], vk=providers.get('vk'),
        advertising=load_public_json(directory / 'advertising.candidate.json'),
        backend_ads=load_public_json(directory / 'rewarded-policy.candidate.json'),
    )
    release_checks = {
        'release_schema_version_valid': type(release.get('schemaVersion')) is int and release['schemaVersion'] == 1,
        'payment_environment_valid': environment_valid,
        'production_environment_required': environment == 'production',
        'backend_origin_matches': release.get('backendOrigin') == plan['publicOrigin'],
        'registered_package_required': (
            type(release.get('packageName')) is str
            and re.fullmatch(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,}',
                             release['packageName']) is not None
            and not any(word in release['packageName'] for word in ('verification', 'defaultcompany', 'example'))
            and release['packageName'] != 'com.heartoftherain.stagingreview'),
        'registered_console_application_matches': (
            type(release.get('consoleApplicationId')) is str
            and re.fullmatch(r'[1-9][0-9]{0,18}', release['consoleApplicationId']) is not None
            and int(release['consoleApplicationId']) <= 9_223_372_036_854_775_807
            and int(release['consoleApplicationId']) == catalogue.get('appId')),
        'payment_return_scheme_required': (
            type(release.get('paymentReturnScheme')) is str
            and re.fullmatch(r'[a-z][a-z0-9+.-]{2,62}', release['paymentReturnScheme']) is not None
            and release['paymentReturnScheme'] not in ('http', 'https', 'file', 'intent', 'content', 'javascript')),
        'release_version_code_required': (
            type(release.get('versionCode')) is int and 0 < release['versionCode'] <= 2_147_483_647),
        'minimum_api_required': type(release.get('minimumApiLevel')) is int and release['minimumApiLevel'] >= 26,
        'target_api_required': type(release.get('minimumApiLevel')) is int
                               and type(release.get('targetApiLevel')) is int
                               and release['minimumApiLevel'] <= release['targetApiLevel'] <= 1000,
        'release_certificate_required': (
            type(release.get('signingCertificateSha256')) is str
            and re.fullmatch(r'[A-Fa-f0-9]{64}', release['signingCertificateSha256']) is not None
            and len(set(release['signingCertificateSha256'].lower())) >= 2),
        **{key + '_required': _public_https(release.get(key)) is not None
           for key in ('privacyPolicyUrl', 'supportUrl', 'termsUrl')},
    }
    client_checks = {
        'managed_fields_exact': set(managed) == {'version', 'mode', 'runtimeMode', 'origin',
            'identityScope', 'packageName', 'consoleAppId', 'socialEnabled', 'allowDevelopmentLoopback'},
        'checkout_fields_exact': set(packaged_checkout) == {'version', 'enabled', 'sandbox',
            'consoleAppId', 'runtimeMode', 'packageName', 'backendOrigin'},
        'managed_schema_version': type(managed.get('version')) is int and managed['version'] == 2,
        'checkout_schema_version': type(packaged_checkout.get('version')) is int and packaged_checkout['version'] == 2,
        'production_modes': managed.get('mode') == 'ManagedGuestServer'
                            and managed.get('runtimeMode') == packaged_checkout.get('runtimeMode') == 'production',
        'origins_bound': managed.get('origin') == packaged_checkout.get('backendOrigin') == plan['publicOrigin'],
        'identity_scope_bound': managed.get('identityScope') == runtime_template.get('identityScope'),
        'production_identity_scope_required': type(managed.get('identityScope')) is str
                                             and re.fullmatch(r'prod-[a-z0-9.-]{1,50}', managed['identityScope']) is not None,
        'social_enabled': managed.get('socialEnabled') is True,
        'package_bound': bool(release.get('packageName'))
                         and managed.get('packageName') == packaged_checkout.get('packageName') == release['packageName'],
        'application_bound': catalogue.get('appId') is not None
                             and managed.get('consoleAppId') == packaged_checkout.get('consoleAppId') == str(catalogue['appId']),
        'checkout_enabled': packaged_checkout.get('enabled') is True,
        'live_environment': packaged_checkout.get('sandbox') is False,
        'loopback_disabled': managed.get('allowDevelopmentLoopback') is False,
    }
    all_configured = (all(release_checks.values()) and payments['configurationValid']
                      and provider_report['readyForProviderTest'] and all(client_checks.values()))
    return {
        'schemaVersion': 1,
        'status': 'configuration_consistent_not_activated' if all_configured else 'external_inputs_and_integration_required',
        'configurationConsistent': all_configured,
        'releaseChecks': release_checks,
        'productionClientChecks': client_checks,
        'payments': payments,
        'providers': provider_report,
        'productionEnabled': False,
        'productionLauncherImplemented': True,
        'productionClientImplemented': True,
        'existingStagingAuthorityChanged': False,
        'providerAcceptanceVerified': False,
        'monitoringInstallationVerifiedByThisOfflineCheck': False,
        'secretsRead': False,
        'networkContacted': False,
        'remainingEngineering': [
            'production_authority_proxy_and_reconciliation_deployment_acceptance',
            'approved_gameplay_worker_deployment_and_campaign_parity',
            'configured_android_provider_interruption_and_recovery_tests',
            'release_signer_sdk_build_and_final_legal_content',
            'encrypted_off_host_restore_and_reboot_acceptance',
        ],
    }


def prepare(directory, *, public_origin=ORIGIN, app_id=None, sandbox=True):
    """Create reviewable files exclusively in a new directory; no deployment."""
    origin = _public_https(public_origin, origin=True)
    if origin is None:
        raise ValueError('public_https_origin_required')
    if type(sandbox) is not bool:
        raise ValueError('explicit_payment_environment_required')
    if app_id is not None and (type(app_id) is not int or not 0 < app_id <= 9_223_372_036_854_775_807):
        raise ValueError('registered_application_id_invalid')
    output = Path(directory)
    # Never allow a generated server plan to become a Unity packaged resource.
    if output.resolve().is_relative_to((ROOT / 'Unity/Assets').resolve()):
        raise ValueError('server_plan_must_remain_outside_unity_assets')
    output.mkdir(parents=False, exist_ok=False)
    prepare_payment_bundle(output / 'payments', app_id=app_id, sandbox=sandbox)
    advertising = load_public_json(ROOT / 'Release/Advertising/advertising.example.json')
    advertising['enabled'] = False
    policy = load_public_json(ROOT / 'Backend/config/ads.json')
    policy['enabled'] = False
    release = load_public_json(ROOT / 'Release/RuStore/release.example.json')
    release.update(status='CANDIDATE_NOT_REGISTERED_OR_ACTIVATED', backendOrigin=origin,
                   consoleApplicationId=None if app_id is None else str(app_id),
                   environment='sandbox' if sandbox else 'production')
    runtime_template = load_public_json(ROOT / 'Release/RuStore/production-runtime.example122.json')
    runtime_template['publicOrigin'] = origin
    plan = {
        'schemaVersion': 1, 'kind': BUNDLE_KIND, 'publicOrigin': origin,
        'currentDeployment': {
            'mode': 'staging', 'serviceName': 'HOTRStaging',
            'identityScope': 'review-novamind-vps-1',
            'dataDirectory': 'C:\\ProgramData\\HeartOfTheRain\\staging-data',
            'loopbackPort': 8751,
        },
        'productionCandidate': {
            'status': 'NOT_A_RUNTIME_MANIFEST', 'activationSupported': False,
            'runtimeImplementationPresent': True,
            'requiresSeparateAuthority': True,
            'dataDirectory': runtime_template['dataDirectory'],
            'loopbackPort': 8752,
            'note': 'Preserve the existing staging database, scope and services. Do not initialize or copy it as a production wallet.',
        },
        'serverCredentialReferences': {
            'HOTR_RUSTORE_KEY_ID': '',
            'HOTR_RUSTORE_PRIVATE_KEY_FILE': '',
            'HOTR_RUSTORE_NOTIFICATION_KEY_FILE': '',
        },
        'notificationIngress': {
            'sandboxPath': '/v1/commerce/notifications/rustore/sandbox',
            'productionPath': '/v1/commerce/notifications/rustore/production',
            'senderNetworksVerified': False,
            'note': 'Never trust loopback or client Forwarded headers as a RuStore sender. Current staging proxy cannot establish sender identity.',
        },
        'monitoring': {
            'publicOrigin': origin, 'loopbackOrigin': 'http://127.0.0.1:8751',
            'expectedMode': 'staging', 'checkEveryMinutes': 1,
            'alertDestinationConfigured': False,
        },
    }
    _write(output, 'deployment.plan.json', plan)
    _write(output, 'production-runtime.template.json', runtime_template)
    _write(output, 'ManagedProduction.template.json', {
        'version': 2, 'mode': 'ManagedGuestServer', 'runtimeMode': 'production',
        'origin': origin, 'identityScope': runtime_template['identityScope'],
        'packageName': '', 'consoleAppId': '' if app_id is None else str(app_id),
        'socialEnabled': True, 'allowDevelopmentLoopback': False,
    })
    _write(output, 'CheckoutProduction.template.json', {
        'version': 2, 'enabled': False, 'sandbox': False,
        'consoleAppId': '' if app_id is None else str(app_id),
        'runtimeMode': 'production', 'packageName': '', 'backendOrigin': origin,
    })
    _write(output, 'release.candidate.json', release)
    _write(output, 'advertising.candidate.json', advertising)
    _write(output, 'rewarded-policy.candidate.json', policy)
    _write(output, 'providers.candidate.json', {
        'vk': {'enabled': False, 'clientId': '', 'redirectUri': ''},
        'registration': {'vkRedirectUri': origin + '/v1/identity/vk/callback',
                         'yandexRewardedUnitId': advertising['rewardedUnitId'],
                         'yandexInterstitialUnitId': advertising['interstitialUnitId'],
                         'interstitialPlacementEnabled': False},
    })
    report = assess(output)
    _write(output, 'readiness.json', report)
    hashes = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(output.rglob('*')) if p.is_file()}
    _write(output, 'files.sha256.json', hashes)
    return {'status': 'provider_bundle_prepared_not_activated', 'fileCount': len(hashes) + 1,
            'configurationConsistent': report['configurationConsistent'],
            'productionEnabled': False, 'existingStagingAuthorityChanged': False,
            'secretsRead': False, 'networkContacted': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'check'))
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--app-id', type=int)
    parser.add_argument('--environment', choices=('sandbox', 'production'), default='sandbox')
    args = parser.parse_args(argv)
    try:
        result = (prepare(args.directory, app_id=args.app_id, sandbox=args.environment == 'sandbox')
                  if args.command == 'prepare' else assess(args.directory))
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({'status': 'blocked_provider_preparation', 'productionEnabled': False}))
        return 2
    print(json.dumps(result, separators=(',', ':')))
    return 0 if args.command == 'prepare' or result['configurationConsistent'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
