"""Public payment configuration preparation; never authorizes a purchase.

No provider requests, key reads, database writes or feature activation occur.
Console inventory is an operator-normalized observation, not a signed receipt
or a native RuStore export format. All emitted diagnostics use fixed codes.
"""
import argparse
import copy
import csv
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from .commerce_schemas import CommerceConfig, ProductCode
from .schemas import INT_MAX, Model


APP_ID_MAX = 9_223_372_036_854_775_807
ROOT = Path(__file__).resolve().parents[2]
APPROVED_CATALOG = ROOT / 'Release/RuStore/commerce.example.json'
REGISTERED_PRODUCTS = ROOT / 'Release/RuStore/registered-products122.json'
TECHNICAL_BLOCKERS = (
    'owned_production_authority_and_approved_worker_deployment_required',
    'issued_provider_credentials_and_console_binding_acceptance_required',
    'configured_production_android_identity_wallet_checkout_acceptance_required',
    'trusted_notification_ingress_and_reconciliation_acceptance_required',
    'release_signing_and_ordinary_android_provider_acceptance_required',
)


class CheckoutConfiguration(Model):
    version: int = Field(ge=1, le=1)
    enabled: bool
    sandbox: bool
    consoleAppId: str | None


class ConsoleProduct(Model):
    storeProductId: ProductCode
    type: Literal['CONSUMABLE', 'NON_CONSUMABLE', 'SUBSCRIPTION']
    amountMinor: int = Field(gt=0, le=INT_MAX)
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    registered: bool
    published: bool | None


class ConsoleInventory(Model):
    schemaVersion: int = Field(ge=1, le=1)
    appId: int = Field(gt=0, le=APP_ID_MAX)
    environment: Literal['sandbox', 'production']
    products: list[ConsoleProduct] = Field(max_length=100)


class RegisteredProduct(Model):
    id: ProductCode
    storeProductId: ProductCode
    type: Literal['CONSUMABLE']
    registered: bool
    published: bool | None


class RegisteredProducts(Model):
    schemaVersion: int = Field(ge=1, le=1)
    status: Literal['OWNER_CONFIRMED_REGISTERED_PUBLICATION_UNVERIFIED']
    ownerConfirmedOn: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    applicationId: int | None = Field(ge=1, le=APP_ID_MAX)
    products: list[RegisteredProduct] = Field(min_length=12, max_length=12)


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate_json_field')
        value[key] = item
    return value


def load_public_json(path):
    """Bounded JSON with duplicate/nonfinite fields rejected; no raw errors."""
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(262_145)
        if len(raw) > 262_144:
            raise ValueError()
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise ValueError('payment_public_configuration_unreadable') from None


def _app_id(value):
    return (isinstance(value, str) and re.fullmatch(r'[1-9][0-9]{0,18}', value)
            and int(value) <= APP_ID_MAX)


def evaluate_payment_readiness(catalog, checkout, *, console_inventory=None,
                               expected_app_id=None, expected_sandbox=None,
                               approved_catalog=None):
    """Compare public deployment inputs with approved grants and prices.

    A valid result describes configuration consistency only. Existing app and
    backend production gates remain visible even for completely matching input.
    Unknown/malformed input is never copied into the returned report.
    """
    checks = []

    def check(code, passed):
        checks.append({'id': code, 'passed': bool(passed)})
        return bool(passed)

    config = client = inventory = baseline = None
    for code, model, value in (
        ('commerce_schema_valid', CommerceConfig, catalog),
        ('checkout_schema_valid', CheckoutConfiguration, checkout),
        ('approved_catalog_schema_valid', CommerceConfig,
         load_public_json(APPROVED_CATALOG) if approved_catalog is None else approved_catalog),
    ):
        try:
            parsed = model.model_validate(value)
            check(code, True)
        except (ValidationError, TypeError, ValueError):
            parsed = None
            check(code, False)
        if code == 'commerce_schema_valid':
            config = parsed
        elif code == 'checkout_schema_valid':
            client = parsed
        else:
            baseline = parsed

    if console_inventory is not None:
        try:
            inventory = ConsoleInventory.model_validate(console_inventory)
            check('console_inventory_schema_valid', True)
        except (ValidationError, TypeError, ValueError):
            check('console_inventory_schema_valid', False)
    else:
        check('console_inventory_required', False)

    if config is not None:
        check('commerce_enabled', config.enabled)
        check('commerce_app_id_configured', config.appId is not None)
        check('commerce_has_enabled_products', any(p.enabled for p in config.products))
        mapped = [p.storeProductId for p in config.products]
        check('store_product_ids_unique', len(set(mapped)) == len(mapped))
        if baseline is not None:
            known = {p.id: p for p in baseline.products}
            check('catalog_has_only_approved_offers', all(p.id in known for p in config.products))
            for product in config.products:
                approved = known.get(product.id)
                if approved is None:
                    continue  # Never include an unknown operator-supplied ID.
                check('approved_offer_terms:' + product.id,
                      product.coins == approved.coins
                      and product.grant.model_dump() == approved.grant.model_dump()
                      and product.amountMinor == approved.amountMinor
                      and product.currency == approved.currency
                      and product.purchaseLimitPerPlayer == approved.purchaseLimitPerPlayer)
                check('approved_offer_store_binding:' + product.id,
                      product.storeProductId == approved.storeProductId)
        if expected_app_id is not None:
            check('expected_app_id_matches', type(expected_app_id) is int
                  and config.appId == expected_app_id)
        if expected_sandbox is not None:
            check('expected_environment_matches', type(expected_sandbox) is bool
                  and config.sandbox is expected_sandbox)

    if client is not None:
        check('checkout_enabled', client.enabled)
        check('checkout_app_id_configured', _app_id(client.consoleAppId))
    if config is not None and client is not None:
        check('checkout_and_commerce_app_id_match', _app_id(client.consoleAppId)
              and int(client.consoleAppId) == config.appId)
        check('checkout_and_commerce_environment_match', client.sandbox is config.sandbox)
    if inventory is not None:
        ids = [p.storeProductId for p in inventory.products]
        unique = check('console_inventory_product_ids_unique', len(set(ids)) == len(ids))
        if config is not None:
            check('console_and_commerce_app_id_match', inventory.appId == config.appId)
            check('console_and_commerce_environment_match',
                  (inventory.environment == 'sandbox') is config.sandbox)
            products = {p.storeProductId: p for p in inventory.products} if unique else {}
            for product in config.products:
                if not product.enabled:
                    continue
                # IDs are from the trusted approved offer set only.
                if baseline is None or product.id not in {p.id for p in baseline.products}:
                    continue
                observed = products.get(product.storeProductId)
                check('console_product_binding:' + product.id,
                      observed is not None and observed.registered
                      and observed.type == 'CONSUMABLE'
                      and observed.amountMinor == product.amountMinor
                      and observed.currency == product.currency
                      and (config.sandbox or observed.published is True))

    invalid = [c['id'] for c in checks if not c['passed']]
    return {
        'schemaVersion': 1,
        'scope': 'public_payment_configuration_only',
        'configurationValid': not invalid,
        'configurationBlockers': invalid,
        'checks': checks,
        'plannedItemCount': len(baseline.products) if baseline is not None else 0,
        'configuredItemCount': len(config.products) if config is not None else 0,
        'enabledItemCount': sum(p.enabled for p in config.products) if config is not None else 0,
        'consoleInventorySupplied': console_inventory is not None,
        'consoleInventoryAuthenticityVerified': False,
        'sandboxProviderAcceptanceVerified': False,
        'productionReady': False,
        'technicalBlockers': list(TECHNICAL_BLOCKERS),
        'providerRequestsMade': False,
        'secretsRead': False,
        'featuresActivated': False,
    }


def prepare_payment_bundle(output_directory, *, app_id=None, sandbox=True):
    """Create a fresh disabled candidate bundle; never overwrite any directory."""
    if app_id is not None and (type(app_id) is not int or not 0 < app_id <= APP_ID_MAX):
        raise ValueError('payment_app_id_invalid')
    if type(sandbox) is not bool:
        raise ValueError('payment_environment_invalid')
    catalog = load_public_json(APPROVED_CATALOG)
    approved = CommerceConfig.model_validate(catalog)
    registry = RegisteredProducts.model_validate(load_public_json(REGISTERED_PRODUCTS))
    registered = {p.id: p for p in registry.products}
    if (len(registered) != len(approved.products)
            or any(p.id not in registered or not registered[p.id].registered
                   or registered[p.id].storeProductId != p.storeProductId
                   for p in approved.products)):
        raise ValueError('payment_registration_catalog_mismatch')
    catalog = copy.deepcopy(catalog)
    catalog.update(enabled=False, appId=app_id, sandbox=sandbox)
    for product in catalog['products']:
        product['enabled'] = False
    checkout = {'version': 1, 'enabled': False, 'sandbox': sandbox,
                'consoleAppId': None if app_id is None else str(app_id)}
    inventory = {'schemaVersion': 1, 'appId': app_id,
                 'environment': 'sandbox' if sandbox else 'production',
                 'products': [{'storeProductId': p['storeProductId'], 'type': 'CONSUMABLE',
                               'amountMinor': p['amountMinor'], 'currency': p['currency'],
                               'registered': registered[p['id']].registered,
                               'published': registered[p['id']].published}
                              for p in catalog['products']]}
    output = Path(output_directory)
    # Existing files, directories and symlinks all fail at mkdir. No key
    # generation, database mutation or deployment settings are touched.
    output.mkdir(parents=False, exist_ok=False)
    for name, data in (('commerce.candidate.json', catalog),
                       ('checkout.candidate.json', checkout),
                       ('console-inventory.template.json', inventory)):
        with (output / name).open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    with (output / 'console-products.csv').open('x', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(('offerId', 'proposedStoreProductId', 'type', 'amountMinor', 'currency',
                         'coins', 'startingRocketBombRainbowGolden', 'toolsHammerAxeRamAtlas',
                         'purchaseLimitPerPlayer', 'registered', 'published'))
        for product in CommerceConfig.model_validate(catalog).products:
            writer.writerow((product.id, product.storeProductId, 'CONSUMABLE', product.amountMinor,
                             product.currency, product.coins,
                             '/'.join(map(str, product.grant.starting)),
                             '/'.join(map(str, product.grant.tools)),
                             product.purchaseLimitPerPlayer, registered[product.id].registered,
                             registered[product.id].published))
    return {'status': 'DISABLED_PAYMENT_CANDIDATE_PREPARED', 'itemCount': len(catalog['products']),
            'filesWritten': 4, 'featuresActivated': False, 'productionReady': False,
            'technicalBlockers': list(TECHNICAL_BLOCKERS)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    prepare = actions.add_parser('prepare')
    prepare.add_argument('--output', required=True)
    prepare.add_argument('--app-id', type=int)
    prepare.add_argument('--environment', choices=('sandbox', 'production'), required=True)
    review = actions.add_parser('check')
    review.add_argument('--commerce', required=True)
    review.add_argument('--checkout', required=True)
    review.add_argument('--console-inventory')
    review.add_argument('--app-id', type=int)
    review.add_argument('--environment', choices=('sandbox', 'production'), required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == 'prepare':
            result = prepare_payment_bundle(args.output, app_id=args.app_id,
                                            sandbox=args.environment == 'sandbox')
            code = 0
        else:
            result = evaluate_payment_readiness(load_public_json(args.commerce),
                load_public_json(args.checkout),
                console_inventory=load_public_json(args.console_inventory) if args.console_inventory else None,
                expected_app_id=args.app_id, expected_sandbox=args.environment == 'sandbox')
            code = 0 if result['configurationValid'] and args.environment == 'sandbox' else 2
    except (OSError, ValueError, ValidationError):
        result, code = {'status': 'PAYMENT_PUBLIC_CONFIGURATION_REJECTED',
                        'productionReady': False, 'featuresActivated': False}, 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
