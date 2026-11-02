"""Cross-surface launch prices, not live Console/provider payment acceptance."""
import copy
import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from hotr_backend.commerce_schemas import CommerceConfig, CommerceProduct


ROOT = Path(__file__).resolve().parents[2]
QUANTITIES = (1000, 5000, 10000, 25000, 50000, 100000)
RUBLES = (99, 299, 499, 899, 1599, 2999)
BUNDLES = (
    ('wellkeeper', 2000, 99, 1, 1),
    ('rainy-day', 3500, 199, 2, 2),
    ('rainlight', 6000, 299, 3, 3),
    ('village', 5000, 399, 2, 3),
    ('festival', 10000, 599, 4, 6),
    ('keepers', 25000, 999, 8, 12),
)


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8-sig'))


class ReleasePricingTests(unittest.TestCase):
    def test_approved_amounts_rewards_and_ids_agree_across_all_current_surfaces(self):
        shop = read('Unity/Assets/HeartOfTheRain/App/Shop/Data/ShopCatalog.json')
        no_moves = read('Unity/Assets/HeartOfTheRain/App/NoMovesDesign/Data/Shop_Preview_Products.json')
        proposal = read('Release/RuStore/pricing.proposal.json')
        deployment = read('Release/RuStore/commerce.example.json')
        release = read('Release/RuStore/release.example.json')
        offers = {p['id']: p for p in shop['offers'] if p['section'] == 'coins'}
        previews = {p['id']: p for p in no_moves['products']}
        planned = {p['shopOfferId']: p for p in proposal['products']}
        backend = {p['id']: p for p in deployment['products'] if p['id'].startswith('coins-')}
        registrations = {p['shopOfferId']: p for p in release['candidateProducts']}
        expected = {'coins-' + str(q) for q in QUANTITIES}
        for surface in (offers, previews, planned, backend, registrations):
            self.assertEqual(set(surface), expected)
        for quantity, rubles in zip(QUANTITIES, RUBLES):
            product_id = 'coins-' + str(quantity)
            store_id = 'hotr_coins_' + str(quantity)
            label = str(rubles) + ' \u20bd'
            with self.subTest(product=product_id):
                self.assertEqual(offers[product_id]['priceLabel'], label)
                self.assertEqual(previews[product_id]['priceLabel'], label)
                self.assertEqual(planned[product_id]['proposedPriceMinor'], rubles * 100)
                self.assertEqual(backend[product_id]['amountMinor'], rubles * 100)
                self.assertEqual(backend[product_id]['currency'], 'RUB')
                for surface in (offers, previews, planned, backend, registrations):
                    self.assertEqual(surface[product_id]['coins'], quantity)
                self.assertEqual(planned[product_id]['proposedStoreProductId'], store_id)
                self.assertEqual(backend[product_id]['storeProductId'], store_id)
                self.assertEqual(registrations[product_id]['proposedStoreProductId'], store_id)

    def test_approved_bundle_prices_do_not_enable_purchase_or_change_rewards(self):
        shop = read('Unity/Assets/HeartOfTheRain/App/Shop/Data/ShopCatalog.json')
        bundles = {p['id']: p for p in shop['offers'] if p['section'] != 'coins'}
        self.assertEqual(len(bundles), 6)
        self.assertEqual(set(bundles), {p[0] for p in BUNDLES})
        for product_id, coins, rubles, tools_each, starting_each in BUNDLES:
            with self.subTest(bundle=product_id):
                bundle = bundles[product_id]
                self.assertEqual(bundle['priceLabel'], str(rubles) + ' \u20bd')
                self.assertIs(bundle['available'], False)
                self.assertEqual(bundle['coins'], coins)
                self.assertEqual(bundle['boostersEach'], tools_each)
                self.assertEqual([bundle[key] for key in ('rockets', 'bombs', 'rainbowOrbs', 'goldenSeekers')], [starting_each] * 4)
        for coin in (p for p in shop['offers'] if p['section'] == 'coins'):
            for field in ('boostersEach', 'rockets', 'bombs', 'rainbowOrbs', 'goldenSeekers'):
                self.assertEqual(coin[field], 0)

    def test_price_configuration_cannot_enable_unregistered_commerce(self):
        data = read('Release/RuStore/commerce.example.json')
        config = CommerceConfig.model_validate(data)
        self.assertIs(config.enabled, False)
        self.assertIs(config.sandbox, True)
        self.assertIsNone(config.appId)
        self.assertTrue(all(not p.enabled for p in config.products))
        # A mistaken top-level switch alone must not activate an unregistered app.
        for activate_products in (False, True):
            changed = copy.deepcopy(data)
            changed['enabled'] = True
            for product in changed['products']:
                product['enabled'] = activate_products
            with self.subTest(products_enabled=activate_products):
                with self.assertRaises(ValidationError):
                    CommerceConfig.model_validate(changed)
        default = CommerceConfig.model_validate(read('Backend/config/commerce.json'))
        self.assertIs(default.enabled, False)
        self.assertIsNone(default.appId)
        self.assertEqual(default.products, [])

    def test_pending_bundle_registrations_preserve_rewards_without_enabling_checkout(self):
        shop = read('Unity/Assets/HeartOfTheRain/App/Shop/Data/ShopCatalog.json')
        pending = read('Release/RuStore/bundles.pending.json')
        self.assertEqual(pending['status'], 'FULL_GRANT_IMPLEMENTED_UNCONFIGURED_NOT_PRODUCTION_VERIFIED')
        self.assertEqual(pending['decisionDate'], '2026-10-27')
        self.assertEqual(pending['currency'], 'RUB')
        self.assertIs(pending['checkoutEnabled'], False)
        bundles = {p['id']: p for p in shop['offers'] if p['section'] != 'coins'}
        registrations = {p['shopOfferId']: p for p in pending['products']}
        self.assertEqual(set(registrations), set(bundles))
        self.assertEqual(len({p['proposedStoreProductId'] for p in pending['products']}), 6)
        for product_id, bundle in bundles.items():
            with self.subTest(bundle=product_id):
                registration = registrations[product_id]
                self.assertEqual(registration['displayName'], bundle['title'])
                self.assertEqual(registration['section'], bundle['section'])
                approved = next(p for p in BUNDLES if p[0] == product_id)
                self.assertEqual(registration['proposedPriceMinor'], approved[2] * 100)
                self.assertIs(registration['enabled'], False)
                self.assertEqual(registration['grant'], {
                    'coins': bundle['coins'],
                    'stars': 0,
                    'tools': [bundle['boostersEach']] * 4,
                    'starting': [bundle[key] for key in ('rockets', 'bombs', 'rainbowOrbs', 'goldenSeekers')],
                })
        # Registration notes are not directly accepted as a deployment file.
        with self.assertRaises(ValidationError):
            CommerceConfig.model_validate(pending)

    def test_deployment_example_preserves_full_bundle_grant_and_policy(self):
        pending = read('Release/RuStore/bundles.pending.json')
        deployment = CommerceConfig.model_validate(read('Release/RuStore/commerce.example.json'))
        self.assertEqual(len(deployment.products), 12)
        self.assertFalse(deployment.enabled)
        for bundle in pending['products']:
            with self.subTest(bundle=bundle['shopOfferId']):
                product = next(p for p in deployment.products if p.id == bundle['shopOfferId'])
                self.assertEqual(product.grant.model_dump(), bundle['grant'])
                self.assertEqual(product.coins, bundle['grant']['coins'])
                self.assertEqual(product.amountMinor, bundle['proposedPriceMinor'])
                self.assertEqual(product.storeProductId, bundle['proposedStoreProductId'])
                self.assertEqual(product.purchaseLimitPerPlayer, bundle['purchaseLimitPerPlayer'])
                self.assertFalse(product.enabled)

    def test_special_once_per_player_and_mega_repeatability_remain_disabled_configuration(self):
        pending = read('Release/RuStore/bundles.pending.json')
        self.assertEqual(pending['eligibilityKey'], ['internalPlayerId', 'shopOfferId'])
        self.assertIs(pending['purchasePolicyEnforced'], False)
        self.assertIs(pending['purchasePolicyImplemented'], True)
        for bundle in pending['products']:
            with self.subTest(bundle=bundle['shopOfferId']):
                self.assertIs(bundle['enabled'], False)
                if bundle['section'] == 'special':
                    self.assertEqual(bundle['purchaseLimitPerPlayer'], 1)
                    self.assertIs(bundle['repeatable'], False)
                else:
                    self.assertEqual(bundle['section'], 'mega')
                    self.assertIsNone(bundle['purchaseLimitPerPlayer'])
                    self.assertIs(bundle['repeatable'], True)

    def test_preview_amounts_are_explicitly_not_checkout_quotations(self):
        shop = read('Unity/Assets/HeartOfTheRain/App/Shop/Data/ShopCatalog.json')
        no_moves = read('Unity/Assets/HeartOfTheRain/App/NoMovesDesign/Data/Shop_Preview_Products.json')
        proposal = read('Release/RuStore/pricing.proposal.json')
        self.assertIs(shop['isPreview'], True)
        self.assertIs(no_moves['isPreview'], True)
        self.assertIs(no_moves['checkoutEnabled'], False)
        self.assertIs(proposal['checkoutEnabled'], False)
        self.assertEqual(no_moves['currency'], 'RUB')
        self.assertEqual(proposal['currency'], 'RUB')
        self.assertEqual(proposal['status'], 'CONFIGURABLE_LAUNCH_PROPOSAL_NOT_CONSOLE_PRICES')
        self.assertIn('amountLabel', proposal['integrationRule'])
