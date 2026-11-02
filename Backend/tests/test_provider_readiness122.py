"""Offline deployment configuration checks; no provider or device acceptance."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from hotr_backend.provider_readiness122 import assess_ads_and_vk


class ProviderReadiness122Tests(unittest.TestCase):
    def setUp(self):
        self.origin = 'https://api.novamind-it.ru'
        self.vk = {'enabled': True, 'clientId': '123456',
                   'redirectUri': self.origin + '/v1/identity/vk/callback'}
        self.advertising = {
            'version': 2, 'enabled': True, 'rewardedUnitId': 'R-M-20291714-1',
            'interstitialUnitId': 'R-M-20291714-2',
            'privacyUrl': 'https://www.hotr-fixture-provider.net/privacy',
            'privacyVersion': 'launch-r1',
        }
        self.policy = json.loads((Path(__file__).resolve().parents[1] / 'config/ads.json').read_text('utf-8'))
        self.policy['enabled'] = True

    def report(self, **changes):
        args = dict(public_origin=self.origin, vk=self.vk, advertising=self.advertising,
                    backend_ads=self.policy)
        args.update(changes)
        return assess_ads_and_vk(**args)

    def test_configured_provider_test_readiness_does_not_assert_live_or_production_acceptance(self):
        result = self.report()
        self.assertTrue(result['configurationValid'])
        self.assertTrue(result['readyForProviderTest'])
        self.assertFalse(result['networkContacted'])
        self.assertFalse(result['productionEnabled'])
        self.assertFalse(result['providerAcceptanceVerified'])
        self.assertFalse(result['advertising']['completionAuthoritative'])
        self.assertFalse(result['advertising']['interstitialPlacementAdded'])
        self.assertFalse(result['vk']['liveAcceptanceVerified'])

    def test_repository_disabled_examples_remain_valid_but_blocked(self):
        self.vk = {'enabled': False, 'clientId': '', 'redirectUri': ''}
        self.advertising.update(enabled=False, privacyUrl='')
        self.policy['enabled'] = False
        result = self.report()
        self.assertTrue(result['configurationValid'])
        self.assertFalse(result['readyForProviderTest'])
        self.assertEqual(result['blockers'], ['vk_disabled', 'advertising_disabled'])

    def test_callback_cannot_use_other_host_path_prefix_query_or_port(self):
        for callback in (
            'https://different.hotr-fixture-provider.net/v1/identity/vk/callback',
            self.origin + '/api/v1/identity/vk/callback',
            self.origin + '/v1/identity/vk/callback?code=sensitive',
            'https://api.novamind-it.ru:8443/v1/identity/vk/callback',
        ):
            with self.subTest(callback=callback):
                self.vk['redirectUri'] = callback
                result = self.report()
                self.assertFalse(result['readyForProviderTest'])
                self.assertIn('vk_callback_origin_mismatch', result['blockers'])

    def test_staging_canonical_origin_preserves_exact_registered_callback(self):
        result = self.report(public_origin='https://API.NOVAMIND-IT.RU:443/')
        self.assertTrue(result['vk']['callbackMatchesOrigin'])
        self.assertTrue(result['configurationValid'])

    def test_missing_or_invalid_vk_client_id_blocks_configuration(self):
        for value in ('', '0', 'sample', '123456789012345678901', 123456):
            with self.subTest(value=value):
                self.vk['clientId'] = value
                result = self.report()
                self.assertFalse(result['vk']['configurationValid'])

    def test_disabled_vk_cannot_carry_stale_activation_fields(self):
        self.vk['enabled'] = False
        self.assertIn('vk_disabled_fields_must_be_empty', self.report()['blockers'])

    def test_missing_public_privacy_blocks_enabled_sdk_configuration(self):
        self.advertising['privacyUrl'] = ''
        result = self.report()
        self.assertFalse(result['advertising']['configurationValid'])
        self.assertIn('advertising_privacy_url_required', result['blockers'])

    def test_privacy_rejects_nonpublic_urls_credentials_query_fragment_and_malformed_hosts(self):
        for value in (
            'http://www.hotr-fixture-provider.net/privacy', 'https://localhost/privacy',
            'https://127.0.0.1/privacy', 'https://127.1/privacy',
            'https://[::1]/privacy', 'https://10.0.0.1/privacy',
            'https://policy.example.com/privacy', 'https://policy.local/privacy',
            'https://user:password@www.hotr-fixture-provider.net/privacy',
            'https://www.hotr-fixture-provider.net/privacy?token=sensitive',
            'https://www.hotr-fixture-provider.net/privacy#token',
            'https://www.hotr-fixture-provider.net/privacy?',
            'https://www.hotr-fixture-provider.net/privacy#',
            'https://www.hotr-fixture-provider.net:99999/privacy',
            'https://bad..hotr-fixture-provider.net/privacy',
            'https://-bad.hotr-fixture-provider.net/privacy',
            'https://bad_.hotr-fixture-provider.net/privacy',
            'https://www.hotr-fixture-provider.net/white space',
            'https://www.hotr-fixture-provider.net\\privacy',
        ):
            with self.subTest(value=value):
                self.advertising['privacyUrl'] = value
                result = self.report()
                self.assertFalse(result['readyForProviderTest'])
                self.assertFalse(result['advertising']['privacyConfigured'])

    def test_privacy_version_is_required_and_bounded(self):
        for value in ('', 'x' * 65, 'contains spaces', 1):
            with self.subTest(value=value):
                self.advertising['privacyVersion'] = value
                self.assertFalse(self.report()['configurationValid'])

    def test_only_approved_units_are_accepted_and_formats_cannot_swap(self):
        for reward, interstitial in (
            ('demo-rewarded-yandex', 'R-M-20291714-2'),
            ('R-M-20291714-2', 'R-M-20291714-1'),
            ('R-M-9-1', 'R-M-20291714-2'),
        ):
            with self.subTest(reward=reward):
                self.advertising.update(rewardedUnitId=reward, interstitialUnitId=interstitial)
                self.assertIn('advertising_approved_units_mismatch', self.report()['blockers'])

    def test_strict_public_fields_reject_secret_material_without_reflecting_values(self):
        secret = 'private-fixture-value-never-emit'
        for name, base, added in (
            ('vk', self.vk, {'clientSecret': secret}),
            ('advertising', self.advertising, {'publisherPassword': secret}),
            ('backend_ads', self.policy, {'verificationKey': secret}),
        ):
            with self.subTest(name=name):
                result = self.report(**{name: dict(base, **added)})
                self.assertFalse(result['configurationValid'])
                self.assertNotIn(secret, json.dumps(result))
                self.assertNotIn('publisherPassword', json.dumps(result))

    def test_strings_and_numbers_cannot_enable_or_disable_public_flags(self):
        for value in ('true', 'false', 0, 1, None):
            for name, base in (('vk', self.vk), ('advertising', self.advertising), ('backend_ads', self.policy)):
                with self.subTest(name=name, value=value):
                    result = self.report(**{name: dict(base, enabled=value)})
                    self.assertFalse(result['configurationValid'])
                    self.assertFalse(result['readyForProviderTest'])

    def test_client_and_server_activation_must_match(self):
        for client, server in ((True, False), (False, True)):
            with self.subTest(client=client):
                self.advertising['enabled'], self.policy['enabled'] = client, server
                self.assertIn('advertising_client_backend_enablement_mismatch', self.report()['blockers'])

    def test_yandex_trust_cannot_be_presented_as_server_verified(self):
        self.policy['completionMode'] = 'trusted_completion'
        result = self.report()
        self.assertFalse(result['readyForProviderTest'])
        self.assertIn('yandex_trusted_completion_unsupported', result['blockers'])
        self.assertFalse(result['advertising']['completionAuthoritative'])

    def test_ad_economy_and_calendar_cannot_change_through_deployment_configuration(self):
        for key, value in (('rewardCoins', 401), ('dailyLimit', 4), ('cooldownSeconds', 0),
                           ('placement', 'interstitial_reward'), ('dayMode', 'utc'),
                           ('utcOffsetSeconds', 0), ('opportunityTtlSeconds', 0)):
            with self.subTest(key=key):
                result = self.report(backend_ads=dict(self.policy, **{key: value}))
                self.assertIn('advertising_backend_policy_invalid', result['blockers'])

    def test_public_api_origin_rejects_private_placeholder_and_credential_forms(self):
        for value in ('', 'http://api.novamind-it.ru', 'https://10.0.0.1',
                      'https://api.example.com', 'https://api.novamind-it.ru/api',
                      'https://api.novamind-it.ru?secret=value',
                      'https://user:password@api.novamind-it.ru',
                      'https://api.novamind-it.ru:8751', None):
            with self.subTest(value=value):
                result = self.report(public_origin=value)
                self.assertIn('public_https_origin_required', result['blockers'])
                self.assertFalse(result['readyForProviderTest'])

    def test_report_is_read_only_and_does_not_echo_configuration_values(self):
        before = deepcopy((self.vk, self.advertising, self.policy))
        with patch('socket.getaddrinfo', side_effect=AssertionError('network forbidden')):
            result = self.report()
        self.assertEqual(before, (self.vk, self.advertising, self.policy))
        encoded = json.dumps(result)
        for value in (self.origin, self.vk['clientId'], self.advertising['privacyUrl']):
            self.assertNotIn(value, encoded)


if __name__ == '__main__':
    unittest.main()
