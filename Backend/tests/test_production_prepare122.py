import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hotr_backend import production_prepare122 as setup


class ProductionPreparation122Tests(unittest.TestCase):
    def configured_candidate(self, output, *, sandbox=False):
        """Consistent public fixture; no real registrations or provider calls."""
        setup.prepare(output, app_id=12345, sandbox=sandbox)

        def change(name, mutate):
            path = output / name
            value = json.loads(path.read_bytes())
            mutate(value)
            path.write_text(json.dumps(value), encoding='utf-8')

        def enable_catalogue(value):
            value['enabled'] = True
            for product in value['products']:
                product['enabled'] = True

        def register_inventory(value):
            for product in value['products']:
                product.update(registered=True, published=True)

        policy = 'https://www.hotr-fixture-provider.net/privacy'
        change('release.candidate.json', lambda value: value.update(
            packageName='com.heartoftherain.readinessfixture',
            paymentReturnScheme='heartoftherain-pay', versionCode=1,
            signingCertificateSha256='ab' * 32, privacyPolicyUrl=policy,
            supportUrl='https://www.hotr-fixture-provider.net/support',
            termsUrl='https://www.hotr-fixture-provider.net/terms'))
        change('payments/commerce.candidate.json', enable_catalogue)
        change('payments/checkout.candidate.json', lambda value: value.update(enabled=True))
        change('payments/console-inventory.template.json', register_inventory)
        change('providers.candidate.json', lambda value: value['vk'].update(
            enabled=True, clientId='123456',
            redirectUri=setup.ORIGIN + '/v1/identity/vk/callback'))
        change('advertising.candidate.json', lambda value: value.update(
            enabled=True, privacyUrl=policy))
        change('rewarded-policy.candidate.json', lambda value: value.update(enabled=True))
        change('ManagedProduction.template.json', lambda value: value.update(
            packageName='com.heartoftherain.readinessfixture'))
        change('CheckoutProduction.template.json', lambda value: value.update(
            enabled=True, packageName='com.heartoftherain.readinessfixture'))

    def test_prepares_complete_disabled_bundle_without_touching_existing_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority = root / 'authority.sqlite3'
            authority.write_bytes(b'existing authority must stay exact')
            with patch('socket.socket', side_effect=AssertionError('unexpected network')):
                result = setup.prepare(root / 'candidate')
                report = setup.assess(root / 'candidate')
            self.assertEqual(authority.read_bytes(), b'existing authority must stay exact')
            self.assertFalse(result['productionEnabled'])
            self.assertFalse(report['configurationConsistent'])
            self.assertFalse(report['secretsRead'])
            self.assertEqual(report['payments']['plannedItemCount'], 12)
            self.assertEqual(report['payments']['enabledItemCount'], 0)
            self.assertIn('vk_disabled', report['providers']['blockers'])
            self.assertIn('advertising_disabled', report['providers']['blockers'])
            plan = json.loads((root / 'candidate/deployment.plan.json').read_bytes())
            self.assertNotEqual(plan['currentDeployment']['dataDirectory'],
                                plan['productionCandidate']['dataDirectory'])
            self.assertFalse(plan['productionCandidate']['activationSupported'])
            self.assertTrue(all(v == '' for v in plan['serverCredentialReferences'].values()))
            self.assertEqual(set(plan['serverCredentialReferences']), {
                'HOTR_RUSTORE_KEY_ID', 'HOTR_RUSTORE_PRIVATE_KEY_FILE',
                'HOTR_RUSTORE_NOTIFICATION_KEY_FILE',
            })

    def test_preserves_existing_candidate_and_rejects_invalid_arguments_before_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / 'candidate'
            output.mkdir()
            sentinel = output / 'operator.txt'
            sentinel.write_bytes(b'preserve this')
            with self.assertRaises(FileExistsError):
                setup.prepare(output)
            self.assertEqual(list(output.iterdir()), [sentinel])
            self.assertEqual(sentinel.read_bytes(), b'preserve this')
            for kwargs in ({'public_origin': 'http://api.novamind-it.ru'},
                           {'public_origin': 'https://user:private@api.novamind-it.ru'},
                           {'app_id': True}, {'app_id': -1}, {'sandbox': 'false'}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    setup.prepare(root / 'invalid', **kwargs)
                self.assertFalse((root / 'invalid').exists())

    def test_refuses_server_config_inside_packaged_unity_assets(self):
        with self.assertRaisesRegex(ValueError, '^server_plan_must_remain_outside_unity_assets$'):
            setup.prepare(setup.ROOT / 'Unity/Assets/DoNotCreateProduction122')

    def test_detects_release_binding_mismatch_and_never_opens_secret_references(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'candidate'
            setup.prepare(output, app_id=12345)
            plan_path = output / 'deployment.plan.json'
            plan = json.loads(plan_path.read_bytes())
            plan['serverCredentialReferences']['HOTR_RUSTORE_PRIVATE_KEY_FILE'] = str(output / 'missing-secret')
            plan_path.write_text(json.dumps(plan), encoding='utf-8')
            release_path = output / 'release.candidate.json'
            release = json.loads(release_path.read_bytes())
            release.update(backendOrigin='https://different.novamind-it.ru', consoleApplicationId=67890)
            release_path.write_text(json.dumps(release), encoding='utf-8')
            report = setup.assess(output)
            self.assertFalse(report['releaseChecks']['backend_origin_matches'])
            self.assertFalse(report['releaseChecks']['registered_console_application_matches'])
            self.assertFalse(report['secretsRead'])
            self.assertNotIn('missing-secret', json.dumps(report))

    def test_production_candidate_remains_disabled_and_environment_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'candidate'
            setup.prepare(output, app_id=12345, sandbox=False)
            catalogue = json.loads((output / 'payments/commerce.candidate.json').read_bytes())
            self.assertFalse(catalogue['sandbox'])
            self.assertFalse(catalogue['enabled'])
            self.assertTrue(all(not p['enabled'] for p in catalogue['products']))
            report = setup.assess(output)
            self.assertFalse(report['productionEnabled'])
            self.assertTrue(report['productionLauncherImplemented'])
            self.assertTrue(report['productionClientImplemented'])
            self.assertFalse(report['productionClientChecks']['package_bound'])
            self.assertFalse(report['productionClientChecks']['checkout_enabled'])
            self.assertIn('owned_production_authority_and_approved_worker_deployment_required',
                          report['payments']['technicalBlockers'])

    def test_complete_public_configuration_still_does_not_assert_live_activation(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'candidate'
            self.configured_candidate(output)
            report = setup.assess(output)
            self.assertTrue(report['configurationConsistent'])
            self.assertTrue(report['releaseChecks']['payment_environment_valid'])
            self.assertFalse(report['productionEnabled'])
            self.assertTrue(report['productionLauncherImplemented'])
            self.assertFalse(report['providerAcceptanceVerified'])
            self.assertFalse(report['payments']['consoleInventoryAuthenticityVerified'])

    def test_unknown_missing_or_nonstring_environment_cannot_be_treated_as_production(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'candidate'
            self.configured_candidate(output)
            path = output / 'release.candidate.json'
            release = json.loads(path.read_bytes())
            self.assertTrue(setup.assess(output)['configurationConsistent'])
            for environment in ('prodution', '', None, True, False, 0, [], {}):
                with self.subTest(environment=environment):
                    path.write_text(json.dumps(dict(release, environment=environment)), encoding='utf-8')
                    report = setup.assess(output)
                    self.assertFalse(report['configurationConsistent'])
                    self.assertFalse(report['releaseChecks']['payment_environment_valid'])
            del release['environment']
            path.write_text(json.dumps(release), encoding='utf-8')
            self.assertFalse(setup.assess(output)['configurationConsistent'])

    def test_plan_schema_version_must_be_an_integer_not_a_boolean(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'candidate'
            setup.prepare(output)
            path = output / 'deployment.plan.json'
            plan = json.loads(path.read_bytes())
            for version in (True, False, '1', 1.0, None):
                with self.subTest(version=version):
                    path.write_text(json.dumps(dict(plan, schemaVersion=version)), encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, '^provider_preparation_plan_invalid$'):
                        setup.assess(output)

    def test_sandbox_catalogue_cannot_be_combined_with_production_packaged_client(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'candidate'
            self.configured_candidate(output, sandbox=True)
            report = setup.assess(output)
            self.assertFalse(report['configurationConsistent'])
            self.assertFalse(report['releaseChecks']['production_environment_required'])

    def test_production_client_rejects_unknown_fields_disabled_social_and_foreign_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'candidate'
            self.configured_candidate(output)
            path = output / 'ManagedProduction.template.json'
            original = json.loads(path.read_bytes())
            for changes, failed in (({'privateKey': 'never-echo-this'}, 'managed_fields_exact'),
                                    ({'socialEnabled': False}, 'social_enabled'),
                                    ({'identityScope': 'review-staging'}, 'production_identity_scope_required')):
                with self.subTest(failed=failed):
                    path.write_text(json.dumps(dict(original, **changes)), encoding='utf-8')
                    report = setup.assess(output)
                    self.assertFalse(report['configurationConsistent'])
                    self.assertFalse(report['productionClientChecks'][failed])
                    self.assertNotIn('never-echo-this', json.dumps(report))

    def test_native_release_constraints_and_string_app_id_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'candidate'
            self.configured_candidate(output)
            path = output / 'release.candidate.json'
            original = json.loads(path.read_bytes())
            self.assertIsInstance(original['consoleApplicationId'], str)
            cases = [({'consoleApplicationId': 12345}, 'registered_console_application_matches'),
                     ({'packageName': 'com.Example.game'}, 'registered_package_required'),
                     ({'paymentReturnScheme': 'https'}, 'payment_return_scheme_required'),
                     ({'signingCertificateSha256': 'a' * 64}, 'release_certificate_required'),
                     ({'minimumApiLevel': 22}, 'minimum_api_required'),
                     ({'targetApiLevel': 25}, 'target_api_required'),
                     ({'versionCode': 2_147_483_648}, 'release_version_code_required')]
            for changes, failed in cases:
                with self.subTest(failed=failed):
                    path.write_text(json.dumps(dict(original, **changes)), encoding='utf-8')
                    report = setup.assess(output)
                    self.assertFalse(report['configurationConsistent'])
                    self.assertFalse(report['releaseChecks'][failed])


if __name__ == '__main__':
    unittest.main()
