"""Configuration-bound payment preparation; no provider or device claims."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from hotr_backend.payment_readiness122 import (
    APPROVED_CATALOG, TECHNICAL_BLOCKERS, evaluate_payment_readiness,
    load_public_json, main, prepare_payment_bundle,
)


class PaymentReadiness122Tests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_public_json(APPROVED_CATALOG)
        self.catalog.update(enabled=True, appId=123, sandbox=True)
        for product in self.catalog['products']:
            product['enabled'] = True
        self.checkout = {'version': 1, 'enabled': True, 'sandbox': True, 'consoleAppId': '123'}
        self.inventory = {'schemaVersion': 1, 'appId': 123, 'environment': 'sandbox',
                          'products': [{'storeProductId': p['storeProductId'], 'type': 'CONSUMABLE',
                                        'amountMinor': p['amountMinor'], 'currency': p['currency'],
                                        'registered': True, 'published': False}
                                       for p in self.catalog['products']]}

    def review(self, **kwargs):
        return evaluate_payment_readiness(self.catalog, self.checkout,
                                         console_inventory=self.inventory, **kwargs)

    def test_valid_sandbox_bindings_keep_live_and_provider_acceptance_blocked(self):
        value = self.review(expected_app_id=123, expected_sandbox=True)
        self.assertTrue(value['configurationValid'])
        self.assertEqual(value['enabledItemCount'], 12)
        self.assertFalse(value['productionReady'])
        self.assertFalse(value['sandboxProviderAcceptanceVerified'])
        self.assertFalse(value['consoleInventoryAuthenticityVerified'])
        self.assertEqual(value['technicalBlockers'], list(TECHNICAL_BLOCKERS))
        self.assertFalse(value['secretsRead'])
        self.assertFalse(value['featuresActivated'])

    def test_matching_production_configuration_never_claims_activation(self):
        self.catalog['sandbox'] = self.checkout['sandbox'] = False
        self.inventory['environment'] = 'production'
        for product in self.inventory['products']:
            product['published'] = True
        value = self.review(expected_sandbox=False)
        self.assertTrue(value['configurationValid'])
        self.assertFalse(value['productionReady'])
        self.assertTrue(value['technicalBlockers'])

    def test_unpublished_products_fail_production_but_are_allowed_in_sandbox(self):
        self.assertTrue(self.review()['configurationValid'])
        self.catalog['sandbox'] = self.checkout['sandbox'] = False
        self.inventory['environment'] = 'production'
        self.assertIn('console_product_binding:coins-1000', self.review()['configurationBlockers'])

    def test_deleted_wellkeeper_id_cannot_be_reintroduced_into_new_catalog(self):
        self.catalog['products'][6]['storeProductId'] = 'hotr_bundle_wellkeeper'
        self.inventory['products'][6]['storeProductId'] = 'hotr_bundle_wellkeeper'
        self.assertIn('approved_offer_store_binding:wellkeeper', self.review()['configurationBlockers'])

    def test_different_account_or_environment_is_rejected(self):
        cases = [('checkout', 'consoleAppId', '124', 'checkout_and_commerce_app_id_match'),
                 ('checkout', 'sandbox', False, 'checkout_and_commerce_environment_match'),
                 ('inventory', 'appId', 124, 'console_and_commerce_app_id_match'),
                 ('inventory', 'environment', 'production', 'console_and_commerce_environment_match')]
        for owner, key, value, code in cases:
            target = getattr(self, owner)
            before = target[key]
            with self.subTest(owner=owner, key=key):
                target[key] = value
                self.assertIn(code, self.review()['configurationBlockers'])
                target[key] = before

    def test_expected_target_rejects_consistently_wrong_deployment(self):
        self.assertIn('expected_app_id_matches', self.review(expected_app_id=124)['configurationBlockers'])
        self.assertIn('expected_environment_matches', self.review(expected_sandbox=False)['configurationBlockers'])
        self.assertIn('expected_app_id_matches', self.review(expected_app_id=True)['configurationBlockers'])
        self.assertIn('expected_environment_matches', self.review(expected_sandbox=1)['configurationBlockers'])

    def test_reward_price_and_one_time_limit_changes_fail_before_activation(self):
        changes = [{'coins': 2001, 'grant': {'coins': 2001, 'stars': 0, 'starting': [1] * 4, 'tools': [1] * 4}},
                   {'amountMinor': 10000}, {'currency': 'USD'}, {'purchaseLimitPerPlayer': None},
                   {'grant': {'coins': 2000, 'stars': 0, 'starting': [2] * 4, 'tools': [1] * 4}}]
        original = copy.deepcopy(self.catalog['products'][6])
        for change in changes:
            with self.subTest(change=change):
                self.catalog['products'][6] = original | change
                self.assertIn('approved_offer_terms:wellkeeper', self.review()['configurationBlockers'])
        self.catalog['products'][6] = original

    def test_store_sku_type_price_currency_registration_or_absence_is_rejected(self):
        original = copy.deepcopy(self.inventory['products'][0])
        for change in ({'type': 'NON_CONSUMABLE'}, {'amountMinor': 10000}, {'currency': 'USD'},
                       {'registered': False}, {'storeProductId': 'different.registered.sku'}):
            with self.subTest(change=change):
                self.inventory['products'][0] = original | change
                self.assertIn('console_product_binding:coins-1000', self.review()['configurationBlockers'])
        self.inventory['products'].pop(0)
        self.assertIn('console_product_binding:coins-1000', self.review()['configurationBlockers'])

    def test_duplicate_inventory_never_picks_an_arbitrary_product(self):
        self.inventory['products'].append(copy.deepcopy(self.inventory['products'][0]))
        blockers = self.review()['configurationBlockers']
        self.assertIn('console_inventory_product_ids_unique', blockers)
        self.assertIn('console_product_binding:coins-1000', blockers)

    def test_disabled_duplicate_catalog_skus_are_detected(self):
        self.catalog['products'][0]['enabled'] = False
        self.catalog['products'][1]['enabled'] = False
        self.catalog['products'][1]['storeProductId'] = self.catalog['products'][0]['storeProductId']
        self.assertIn('store_product_ids_unique', self.review()['configurationBlockers'])

    def test_enabled_subset_of_approved_products_is_supported(self):
        for product in self.catalog['products'][1:]:
            product['enabled'] = False
        self.inventory['products'] = self.inventory['products'][:1]
        value = self.review()
        self.assertTrue(value['configurationValid'])
        self.assertEqual(value['enabledItemCount'], 1)

    def test_disabled_default_configs_report_missing_ids_and_inventory(self):
        value = evaluate_payment_readiness(load_public_json(APPROVED_CATALOG),
                     {'version': 1, 'enabled': False, 'sandbox': True, 'consoleAppId': None})
        self.assertFalse(value['configurationValid'])
        self.assertIn('console_inventory_required', value['configurationBlockers'])
        self.assertIn('commerce_app_id_configured', value['configurationBlockers'])
        self.assertIn('checkout_enabled', value['configurationBlockers'])

    def test_unknown_and_sensitive_input_is_not_reflected_in_diagnostics(self):
        marker = 'SYNTHETIC_DO_NOT_ECHO_CREDENTIAL'
        for target in (self.catalog, self.checkout, self.inventory):
            with self.subTest(target=type(target).__name__):
                target['privateKey'] = marker
                report = self.review()
                self.assertFalse(report['configurationValid'])
                self.assertNotIn(marker, json.dumps(report))
                del target['privateKey']
        self.catalog['products'][0]['id'] = marker
        report = self.review()
        self.assertIn('catalog_has_only_approved_offers', report['configurationBlockers'])
        self.assertNotIn(marker, json.dumps(report))

    def test_malformed_identifiers_and_non_strict_types_fail(self):
        for value in ('00123', '+123', '123\n', '9223372036854775808', 123, True):
            with self.subTest(value=value):
                self.checkout['consoleAppId'] = value
                self.assertFalse(self.review()['configurationValid'])
        self.checkout['consoleAppId'] = '123'
        self.catalog['products'][0]['enabled'] = 'true'
        self.assertIn('commerce_schema_valid', self.review()['configurationBlockers'])

    def test_boolean_schema_versions_are_not_treated_as_integer_one(self):
        self.checkout['version'] = True
        self.assertIn('checkout_schema_valid', self.review()['configurationBlockers'])
        self.checkout['version'] = 1
        self.inventory['schemaVersion'] = True
        self.assertIn('console_inventory_schema_valid', self.review()['configurationBlockers'])

    def test_read_rejects_duplicate_nonfinite_oversized_and_nonobject_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            for raw in (b'{"enabled":true,"enabled":false}', b'{"value":NaN}', b'[]',
                        b'{' + b' ' * 262_145 + b'}', b'\xff'):
                with self.subTest(raw_length=len(raw)):
                    path.write_bytes(raw)
                    with self.assertRaisesRegex(ValueError, '^payment_public_configuration_unreadable$'):
                        load_public_json(path)

    def test_prepare_preserves_all_approved_grants_prices_and_limits_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'fresh'
            result = prepare_payment_bundle(output, app_id=123, sandbox=False)
            self.assertEqual(result['filesWritten'], 4)
            candidate = load_public_json(output / 'commerce.candidate.json')
            self.assertFalse(candidate['enabled'])
            self.assertFalse(candidate['sandbox'])
            self.assertEqual(candidate['appId'], 123)
            self.assertEqual(candidate['products'], load_public_json(APPROVED_CATALOG)['products'])
            checkout = load_public_json(output / 'checkout.candidate.json')
            self.assertEqual(checkout, {'version': 1, 'enabled': False, 'sandbox': False, 'consoleAppId': '123'})
            inventory = load_public_json(output / 'console-inventory.template.json')
            self.assertTrue(all(p['registered'] and p['published'] is None for p in inventory['products']))
            rows = (output / 'console-products.csv').read_text('utf-8').splitlines()
            self.assertEqual(len(rows), 13)
            self.assertIn('wellkeeper,hotr_bundle_wellkeeper_c,CONSUMABLE,9900,RUB,2000,1/1/1/1,1/1/1/1,1,True,', rows)

    def test_prepare_refuses_existing_directory_and_preserves_its_files(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'owner-file.txt'
            marker.write_bytes(b'preserve')
            with self.assertRaises(FileExistsError):
                prepare_payment_bundle(directory, app_id=123)
            self.assertEqual(marker.read_bytes(), b'preserve')
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_prepare_rejects_invalid_app_ids_and_environment_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'fresh'
            for app_id in (True, 0, -1, 9_223_372_036_854_775_808, '123'):
                with self.subTest(app_id=app_id), self.assertRaises(ValueError):
                    prepare_payment_bundle(output, app_id=app_id)
            with self.assertRaises(ValueError):
                prepare_payment_bundle(output, sandbox=1)
            self.assertFalse(output.exists())

    def test_production_cli_never_returns_success_as_launch_approval(self):
        self.catalog['sandbox'] = self.checkout['sandbox'] = False
        self.inventory['environment'] = 'production'
        for product in self.inventory['products']:
            product['published'] = True
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, value in (('commerce', self.catalog), ('checkout', self.checkout), ('console', self.inventory)):
                path = Path(directory) / (name + '.json')
                path.write_text(json.dumps(value), encoding='utf-8')
                paths.append(str(path))
            args = ['check', '--commerce', paths[0], '--checkout', paths[1],
                    '--console-inventory', paths[2], '--environment', 'production']
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(args)
            self.assertEqual(code, 2)
            report = json.loads(output.getvalue())
            self.assertTrue(report['configurationValid'])
            self.assertFalse(report['productionReady'])


if __name__ == '__main__':
    unittest.main()
