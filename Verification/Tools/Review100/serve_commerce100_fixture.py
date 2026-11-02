"""Private loopback full-Grant fixture; publisher/SDK behavior is controlled.

The real backend owns transactions and eligibility. Operator controls are files
inside this ignored run directory, never HTTP endpoints or shipped client code.
No real SDK, publisher credential, notification or external network is used.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import sys
import re
from urllib.parse import urlparse
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Backend'))

import uvicorn
from fastapi.responses import JSONResponse
from hotr_backend.api import create_app
from hotr_backend.commerce_schemas import CommerceConfig, CreateCommerceOrder
from hotr_backend.rustore_provider import InvalidProviderResponse, ProviderUnavailable, VerifiedInvoice


def invoice_id(order_id):
    return str(810_000_000_000_000 + int(order_id[:12], 16))


def controlled(path):
    if not path.is_file() or path.stat().st_size > 131_072:
        raise RuntimeError('BoundedPrivateControlRequired')
    value = json.loads(path.read_text('utf-8'))
    rows = value.get('orders') if isinstance(value, dict) else None
    if not isinstance(rows, list) or len(rows) > 256 or any(not isinstance(r, dict) or not re.fullmatch('[0-9a-f]{32}', r.get('orderId', '')) for r in rows) or len({r['orderId'] for r in rows}) != len(rows):
        raise RuntimeError('PrivateControlInvalid')
    return value


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, separators=(',', ':')), encoding='utf-8')
    temporary.replace(path)


def fixture_catalog():
    coins = json.loads((ROOT / 'Release/RuStore/pricing.proposal.json').read_text('utf-8'))['products']
    bundles = json.loads((ROOT / 'Release/RuStore/bundles.pending.json').read_text('utf-8'))['products']
    products = [dict(id=p['shopOfferId'], storeProductId=p['proposedStoreProductId'], enabled=True,
                     coins=p['coins'], amountMinor=p['proposedPriceMinor'], currency='RUB') for p in coins]
    products += [dict(id=p['shopOfferId'], storeProductId=p['proposedStoreProductId'], enabled=True,
                      coins=p['grant']['coins'], grant=p['grant'], purchaseLimitPerPlayer=p['purchaseLimitPerPlayer'],
                      amountMinor=p['proposedPriceMinor'], currency='RUB') for p in bundles]
    value = dict(version='controlled-native100-only', enabled=True, appId=123456, sandbox=True, products=products)
    return CommerceConfig.model_validate(value).model_dump()


class ControlledProvider:
    configured = True

    def __init__(self, control):
        self.control, self.authority = control, None

    def lookup(self, supplied_invoice, sandbox):
        if sandbox is not True:
            raise InvalidProviderResponse()
        with self.authority.database.connect() as db:
            rows = [dict(r) for r in db.execute('SELECT * FROM commerce_orders').fetchall()]
        matches = [r for r in rows if invoice_id(r['id']) == supplied_invoice]
        if len(matches) != 1:
            raise InvalidProviderResponse()
        row = matches[0]
        behavior = next((r for r in controlled(self.control)['orders'] if r['orderId'] == row['id']), {})
        if behavior.get('unavailable'):
            raise ProviderUnavailable()
        return VerifiedInvoice(supplied_invoice, str(uuid.UUID(hex=row['id'])), row['app_id'], True,
                               row['id'], row['store_product'], row['player_id'], row['binding'],
                               row['amount_minor'] + (1 if behavior.get('mismatchAmount') else 0), row['currency'],
                               behavior.get('status', 'CONFIRMED'), behavior.get('acknowledgement', 'PENDING'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_relative_to((ROOT / '.verification-cache/Review100/CommerceHTTP').resolve()) or not (
            len(args.run_id) == 32 and all(c in '0123456789abcdef' for c in args.run_id)):
        raise SystemExit('ExactPrivateRunRequired100')
    directory.mkdir(parents=True, exist_ok=True)
    database, connection = directory / 'authority.sqlite3', directory / 'connection.json'
    config, control = directory / 'commerce.json', directory / 'provider_control.json'
    if not args.resume:
        if database.exists() or connection.exists():
            raise SystemExit('FreshFixtureRequired100')
        save(config, fixture_catalog())
        save(control, dict(orders=[], dropNextReconcile=0, catalogMode='', legacyWire=False))
    elif not all(p.is_file() for p in (database, connection, config, control)):
        raise SystemExit('ExactExistingFixtureRequired100')
    os.environ['HOTR_BACKEND_MODE'] = 'local'
    provider = ControlledProvider(control)
    app = create_app(database, ROOT / 'Backend/config', commerce_provider=provider, commerce_config_path=config,
                     identity_enabled=False, notifications_enabled=False, social_enabled=False, replay_enabled=False)
    provider.authority = app.state.authority
    initial_catalog = CommerceConfig.model_validate_json(config.read_text('utf-8'))

    @app.middleware('http')
    async def operator_controls(request, call_next):
        behavior = controlled(control)
        if behavior.get('catalogMode') == 'retire-rainlight':
            # Trusted test-operator catalog replacement; existing order terms
            # still come from the ordinary backend's immutable order snapshot.
            replacement = initial_catalog.model_dump()
            replacement['version'] = 'controlled-native100-repriced-after-order'
            replacement['products'] = [p for p in replacement['products'] if p['id'] != 'rainlight']
            next(p for p in replacement['products'] if p['id'] == 'coins-1000')['amountMinor'] = 77700
            app.state.commerce.config = CommerceConfig.model_validate(replacement)
        else:
            app.state.commerce.config = initial_catalog
        response = await call_next(request)
        if (request.method == 'POST' and request.url.path.endswith('/reconcile')
                and response.status_code == 200 and behavior.get('dropNextReconcile', 0) > 0):
            # The real SQLite transaction already committed. Drain its response
            # and replace only this controlled reply to exercise unknown outcome.
            _ = b''.join([part async for part in response.body_iterator])
            latest = controlled(control)
            latest['dropNextReconcile'] = max(0, latest.get('dropNextReconcile', 0) - 1)
            save(control, latest)
            return JSONResponse({'error': {'code': 'controlled_postcommit_unavailable'}}, status_code=503)
        if behavior.get('legacyWire') and request.url.path.startswith('/v1/commerce/') and response.status_code == 200:
            raw = b''.join([part async for part in response.body_iterator])
            value = json.loads(raw)
            def legacy(item):
                if isinstance(item, list):
                    for child in item: legacy(child)
                elif isinstance(item, dict):
                    if (item.get('id', '').startswith('coins-') or item.get('productId', '').startswith('coins-')
                            or item.get('balanceScope') == 'commerce_receipt_audit'):
                        for key in ('grant', 'purchaseLimitPerPlayer', 'repeatable', 'eligible', 'pendingOrderId', 'eligibility'):
                            item.pop(key, None)
                    for child in item.values(): legacy(child)
            legacy(value)
            return JSONResponse(value)
        return response

    if args.resume:
        private = json.loads(connection.read_text('utf-8'))
        if private['runId'] != args.run_id:
            raise SystemExit('FixtureRunChanged100')
        for credential in private['players']:
            if app.state.authority.authenticate(credential['token']).player != credential['playerId']:
                raise SystemExit('FixturePlayerChanged100')
        port = urlparse(private['origin']).port
    else:
        players = []
        for name in ('full', 'unknown', 'discovery', 'frozen', 'cancel', 'legacy', 'paging', 'foreign', 'creator', 'daily'):
            identity = app.state.authority.provision(lifetime=3600)
            players.append(dict(name=name, playerId=identity['playerId'], token=identity['token']))
        private = dict(runId=args.run_id, players=players, providerControlPath=str(control), catalogPath=str(config))
        # Trusted recovery backlog fixture, not101 orders submitted by Unity.
        actor = app.state.authority.authenticate(next(p['token'] for p in players if p['name'] == 'paging'))
        app.state.wallet.view(actor)
        for _ in range(101):
            app.state.commerce.create(actor, CreateCommerceOrder(commandId=uuid.uuid4().hex, productId='coins-1000'))
        private['trustedPendingSeedCount'] = 101
        port = 0
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', port))
    listener.listen(128)
    listener.setblocking(False)
    private['origin'] = 'http://127.0.0.1:' + str(listener.getsockname()[1])
    private['pid'] = os.getpid()
    private['scope'] = 'Actual loopback backend/SQLite; operator-provisioned guests and101-order recovery seed; controlled publisher and SDK, no real money/provider/production.'
    save(connection, private)
    uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning', proxy_headers=False,
                                 server_header=False)).run(sockets=[listener])


if __name__ == '__main__':
    main()
