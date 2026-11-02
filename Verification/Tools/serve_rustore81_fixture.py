"""Disposable native HTTP fixture; synthetic store provider, never a live payment.

All credentials and the database stay in ignored verification storage. This
module is not imported by the backend launcher or exposed as an HTTP control.
"""
import argparse
import json
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Backend'))

import uvicorn
from hotr_backend.api import create_app
from hotr_backend.rustore_provider import InvalidProviderResponse, VerifiedInvoice

PURCHASE = '11111111-1111-4111-8111-111111111111'
INVOICE = '8100001'


class SyntheticProvider:
    configured = True

    def __init__(self):
        self.authority = None

    def lookup(self, invoice_id, sandbox):
        if invoice_id != INVOICE or sandbox is not True:
            raise InvalidProviderResponse()
        with self.authority.database.connect() as db:
            rows = db.execute('SELECT * FROM commerce_orders ORDER BY rowid').fetchall()
        if len(rows) != 1:
            raise InvalidProviderResponse()
        row = rows[0]
        return VerifiedInvoice(INVOICE, PURCHASE, row['app_id'], True, row['id'],
                               row['store_product'], row['player_id'], row['binding'],
                               row['amount_minor'], row['currency'], 'CONFIRMED', 'PENDING')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    directory = Path(args.directory).resolve()
    allowed = (ROOT / '.verification-cache/RuStore81').resolve()
    if not directory.is_relative_to(allowed) or len(args.run_id) != 32 or any(c not in '0123456789abcdef' for c in args.run_id):
        raise SystemExit('Invalid isolated fixture location or run ID')
    directory.mkdir(parents=True, exist_ok=True)
    config = directory / 'commerce.json'
    connection = directory / 'connection.json'
    if not args.resume:
        if connection.exists() or (directory / 'authority.sqlite3').exists():
            raise SystemExit('Fixture already exists; use explicit resume')
        config.write_text(json.dumps({'version': 'native-http81-synthetic-only', 'enabled': True,
            'appId': 123456, 'sandbox': True, 'products': [{'id': 'coins-1000',
            'storeProductId': 'hotr_coins_1000', 'enabled': True, 'coins': 1000,
            'amountMinor': 9900, 'currency': 'RUB'}]}), encoding='utf-8')
    provider = SyntheticProvider()
    app = create_app(directory / 'authority.sqlite3', ROOT / 'Backend/config',
                     commerce_provider=provider, commerce_config_path=config)
    provider.authority = app.state.authority
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(128)
    listener.setblocking(False)
    port = listener.getsockname()[1]
    if args.resume:
        private = json.loads(connection.read_text('utf-8'))
        if private['runId'] != args.run_id:
            raise SystemExit('Wrong isolated fixture run')
        # Authenticate the old credential rather than silently creating another.
        actor = app.state.authority.authenticate(private['token'])
        if actor.player != private['playerId']:
            raise SystemExit('Fixture player mismatch')
    else:
        identity = app.state.authority.provision(lifetime=3600)
        private = {'runId': args.run_id, 'playerId': identity['playerId'], 'token': identity['token'],
                   'expectedPurchaseId': PURCHASE, 'invoiceId': INVOICE}
    private['origin'] = f'http://127.0.0.1:{port}/'
    temporary = connection.with_suffix('.tmp')
    temporary.write_text(json.dumps(private), encoding='utf-8')
    temporary.replace(connection)
    # Access logging and proxy trust stay off. Never print the connection record.
    server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning',
                                         proxy_headers=False, server_header=False))
    server.run(sockets=[listener])


if __name__ == '__main__':
    main()
