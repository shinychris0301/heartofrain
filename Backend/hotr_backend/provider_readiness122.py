"""Offline VK/Yandex configuration checks for deployment preparation.

This module neither enables providers nor verifies a console account, privacy
publication, ad impression or live OAuth exchange. Reports contain fixed codes
and booleans only; rejected input values are never reflected into evidence.
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

from .newads_schemas import RewardedAdsConfig
from .vk_provider import VkConfiguration


REWARDED_UNIT = 'R-M-20291714-1'
INTERSTITIAL_UNIT = 'R-M-20291714-2'
CALLBACK_PATH = '/v1/identity/vk/callback'
_RESERVED = ('example.com', 'example.org', 'example.net', 'example', 'invalid',
             'test', 'local', 'localhost')
_AD_FIELDS = {'version', 'enabled', 'rewardedUnitId', 'interstitialUnitId',
              'privacyUrl', 'privacyVersion'}
_VK_FIELDS = {'enabled', 'clientId', 'redirectUri'}


def _public_https(value, *, origin=False):
    """Match public DNS URL constraints without performing DNS or HTTP IO."""
    if (type(value) is not str or not value or len(value) > (512 if origin else 500)
            or any(c.isspace() or ord(c) < 32 for c in value) or '\\' in value):
        return None
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if (parsed.scheme != 'https' or not host or parsed.username is not None
                or parsed.password is not None or parsed.query or parsed.fragment
                or '?' in value or '#' in value or len(host) > 253):
            return None
        # Reading .port also rejects malformed and out-of-range explicit ports.
        port = parsed.port
        if origin and (port not in (None, 443) or parsed.path not in ('', '/')):
            return None
        host = host.lower()
        if ('.' not in host or re.fullmatch(r'[0-9.]+', host)
                or any(host == item or host.endswith('.' + item) for item in _RESERVED)
                or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part)
                       for part in host.split('.'))):
            return None
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            return None
        return 'https://' + host if origin else value
    except (TypeError, ValueError):
        return None


def _vk_report(origin, value):
    errors = []
    enabled = False
    callback_matches = False
    if (type(value) is not dict or set(value) != _VK_FIELDS
            or type(value.get('enabled')) is not bool
            or any(type(value.get(key)) is not str for key in ('clientId', 'redirectUri'))):
        errors.append('vk_fields_invalid')
    else:
        enabled = value['enabled']
        if not enabled:
            if value['clientId'] or value['redirectUri']:
                errors.append('vk_disabled_fields_must_be_empty')
        else:
            try:
                VkConfiguration(True, value['clientId'], value['redirectUri'])
            except (TypeError, ValueError):
                errors.append('vk_configuration_invalid')
            callback_matches = bool(origin and value['redirectUri'] == origin + CALLBACK_PATH)
            if not callback_matches:
                errors.append('vk_callback_origin_mismatch')
    blockers = list(errors)
    if not enabled:
        blockers.append('vk_disabled')
    return {'configurationValid': not errors, 'enabled': enabled,
            'callbackMatchesOrigin': callback_matches,
            'readyForProviderTest': not blockers, 'blockers': blockers,
            'liveAcceptanceVerified': False}


def _advertising_report(value, backend):
    errors = []
    client_enabled = backend_enabled = False
    privacy_configured = False
    if (type(value) is not dict or set(value) != _AD_FIELDS
            or type(value.get('version')) is not int or value.get('version') != 2
            or type(value.get('enabled')) is not bool
            or any(type(value.get(key)) is not str for key in
                   ('rewardedUnitId', 'interstitialUnitId', 'privacyUrl', 'privacyVersion'))):
        errors.append('advertising_public_fields_invalid')
    else:
        client_enabled = value['enabled']
        if (value['rewardedUnitId'] != REWARDED_UNIT
                or value['interstitialUnitId'] != INTERSTITIAL_UNIT):
            errors.append('advertising_approved_units_mismatch')
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', value['privacyVersion']):
            errors.append('advertising_privacy_version_invalid')
        privacy_configured = _public_https(value['privacyUrl']) is not None
        if value['privacyUrl'] and not privacy_configured or client_enabled and not privacy_configured:
            errors.append('advertising_privacy_url_required')
    policy = None
    try:
        if type(backend) is not dict:
            raise ValueError
        policy = RewardedAdsConfig.model_validate(backend)
        backend_enabled = policy.enabled
    except (TypeError, ValueError):
        errors.append('advertising_backend_policy_invalid')
    if policy is not None and policy.completionMode != 'sdk_client_reported_capped':
        errors.append('yandex_trusted_completion_unsupported')
    if client_enabled != backend_enabled:
        errors.append('advertising_client_backend_enablement_mismatch')
    blockers = list(errors)
    if not client_enabled or not backend_enabled:
        blockers.append('advertising_disabled')
    return {'configurationValid': not errors, 'clientEnabled': client_enabled,
            'backendEnabled': backend_enabled, 'privacyConfigured': privacy_configured,
            'readyForProviderTest': not blockers, 'blockers': blockers,
            'completionMode': 'sdk_client_reported_capped',
            'completionAuthoritative': False, 'rewardCoins': 400, 'dailyLimit': 3,
            'cooldownSeconds': 600, 'interstitialPlacementAdded': False,
            'liveAcceptanceVerified': False}


def assess_ads_and_vk(*, public_origin, vk, advertising, backend_ads):
    """Return a non-secret configuration assessment, never activation approval.

    ``vk`` uses enabled/clientId/redirectUri. ``advertising`` is the exact six
    public V2 Unity fields; ``backend_ads`` uses the existing RewardedAdsConfig
    schema. Disabled well-formed configurations are valid but not ready for a
    provider test. Readiness cannot establish actual SDK/provider acceptance.
    """
    origin = _public_https(public_origin, origin=True)
    vk_result = _vk_report(origin, vk)
    ad_result = _advertising_report(advertising, backend_ads)
    blockers = ([] if origin else ['public_https_origin_required'])
    blockers += vk_result['blockers'] + ad_result['blockers']
    return {'status': 'provider_configuration_ready' if not blockers else 'provider_configuration_blocked',
            'configurationValid': bool(origin and vk_result['configurationValid'] and ad_result['configurationValid']),
            'readyForProviderTest': not blockers, 'blockers': blockers,
            'vk': vk_result, 'advertising': ad_result,
            'productionEnabled': False, 'providerAcceptanceVerified': False,
            'networkContacted': False}
