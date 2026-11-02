"""Private real managed HTTP/SQLite service with an explicit synthetic VK peer.

No production test routes or credentials are added to the app/backend. The
system-browser/OAuth provider is deliberately not contacted. Callback requests
reach the real local route and execute the real transport-validation code.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sys
import time
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Backend'))
import httpx
import uvicorn
from fastapi.responses import JSONResponse
from hotr_backend.api import create_app
from hotr_backend.vk_provider import VkConfiguration, VkProvider
from hotr_backend.wallet import GENESIS, project


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, separators=(',', ':')), encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if (not directory.is_relative_to((ROOT / '.verification-cache/Review102/VkHTTP').resolve())
            or not re.fullmatch('[a-f0-9]{32}', args.run_id)):
        parser.error('Exact fresh private VK102 directory required')
    directory.mkdir(parents=True, exist_ok=True)
    database = directory / 'authority.sqlite3'
    connection = directory / 'connection.json'
    control = directory / 'operator.json'
    if database.exists() or connection.exists():
        parser.error('Fresh isolated managed identity fixture required')
    os.environ['HOTR_BACKEND_MODE'] = 'local'
    # Values are fixed fixture configuration, never an issued/live VK identity.
    configuration = VkConfiguration(True, '102102', 'https://fixture.example/v1/identity/vk/callback')
    provider_calls = []

    def provider_http(request):
        if request.method != 'POST' or request.url.host != 'id.vk.com':
            raise ValueError('UnexpectedSyntheticProviderRequest102')
        form = parse_qs(request.content.decode('utf-8'))
        if form.get('client_id') != ['102102']:
            raise ValueError('SyntheticProviderClientBindingFailed102')
        provider_calls.append(request.url.path)
        save(directory / 'ProviderCounts.json', dict(total=len(provider_calls),
            tokenExchanges=provider_calls.count('/oauth2/auth'), userInfoReads=provider_calls.count('/oauth2/user_info'),
            scope='Explicit in-process httpx.MockTransport; no actual VK request or account.'))
        if request.url.path == '/oauth2/auth':
            if (form.get('grant_type') != ['authorization_code']
                    or form.get('redirect_uri') != [configuration.redirect_uri]
                    or form.get('device_id') != ['fixture-browser']
                    or not re.fullmatch('[A-Za-z0-9_-]{43}', form.get('state', [''])[0])
                    or not re.fullmatch('[A-Za-z0-9_-]{64}', form.get('code_verifier', [''])[0])):
                raise ValueError('SyntheticProviderExchangeBindingFailed102')
            code = form.get('code', [''])[0]
            if code == 'fixture-first':
                subject = '1357911'
            elif code == 'fixture-second':
                subject = '1357912'
            else:
                return httpx.Response(200, json={'error': 'invalid_grant'})
            return httpx.Response(200, json={'access_token': 'fixture-vk102-' + subject,
                'state': form['state'][0], 'user_id': int(subject)})
        if request.url.path == '/oauth2/user_info':
            access = form.get('access_token', [''])[0]
            if access not in ('fixture-vk102-1357911', 'fixture-vk102-1357912'):
                raise ValueError('SyntheticProviderTokenBindingFailed102')
            return httpx.Response(200, json={'user': {'user_id': access.rsplit('-', 1)[1]}})
        raise ValueError('UnexpectedSyntheticProviderEndpoint102')

    provider = VkProvider(configuration, httpx.MockTransport(provider_http))
    app = create_app(database, ROOT / 'Backend/config', identity_enabled=True,
        vk_configuration=configuration, vk_provider=provider, notifications_enabled=False,
        social_enabled=False, replay_enabled=False)
    save(control, dict(seed=False, seedPlayerId=None, dropCompleteOnce=False, expireReadyFlow=''))
    seeded = False
    dropped = False
    expired = False
    requests = []

    @app.middleware('http')
    async def observe(request, call_next):
        nonlocal seeded, dropped, expired
        if control.stat().st_size > 2048:
            raise RuntimeError('BoundedPrivateOperatorControlRequired102')
        value = json.loads(control.read_text('utf-8'))
        if (request.method == 'POST' and request.url.path == '/v1/identity/vk/complete'
                and value.get('expireReadyFlow') and not expired):
            flow = value['expireReadyFlow']
            if not isinstance(flow, str) or not re.fullmatch('[a-f0-9]{32}', flow):
                raise RuntimeError('ExactPrivateExpiryFlowRequired102')
            with app.state.authority.database.transaction() as db:
                row = db.execute('SELECT phase FROM account_provider_signins WHERE id=?', (flow,)).fetchone()
                if row is None or row['phase'] != 'Ready':
                    raise RuntimeError('ExactReadyFlowRequiredForExpiry102')
                db.execute('UPDATE account_provider_signins SET expires_at=? WHERE id=?', (int(time.time()) - 1, flow))
            expired = True
            save(directory / 'ExpiredBeforeCompletion.json', dict(flowIdSHA256=hashlib.sha256(flow.encode()).hexdigest(),
                trustedOperatorExpiry=True, walletOrIdentityMutation=False))
            value['expireReadyFlow'] = ''
            save(control, value)
        if request.method == 'GET' and request.url.path == '/v1/wallet' and value.get('seed') is True and not seeded:
            player = value.get('seedPlayerId')
            if not isinstance(player, str) or not re.fullmatch('[a-f0-9]{32}', player):
                raise RuntimeError('ExactManagedSeedPlayerRequired102')
            with app.state.authority.database.transaction() as db:
                row = db.execute('SELECT initialized,balances FROM wallets WHERE player_id=?', (player,)).fetchone()
                if row is None or not row['initialized'] or json.loads(row['balances']) != GENESIS:
                    raise RuntimeError('FreshActualManagedGenesisRequired102')
                delta = [137] + [0] * 10
                project(db, player, 'verification102/operator-seed', delta, int(time.time()))
            seeded = True
            save(directory / 'SeedReceipt.json', dict(playerIdSHA256=hashlib.sha256(player.encode()).hexdigest(),
                coins=1387, addedCoins=137, trustedOperatorSeed=True))
            value['seed'] = False
            save(control, value)
        response = await call_next(request)
        # Loss happens AFTER the real signed completion transaction committed.
        # The native client must recover its durable exact pending intent.
        lose = (request.method == 'POST' and request.url.path == '/v1/identity/vk/complete'
                and response.status_code == 200 and value.get('dropCompleteOnce') is True and not dropped)
        if lose:
            dropped = True
            save(directory / 'DroppedCompletion.json', dict(afterActualCommit=True, clientStatus=503))
            value['dropCompleteOnce'] = False
            save(control, value)
        if len(requests) < 512:
            path = re.sub(r'/[a-f0-9]{32}(?=/|$)', '/{id}', request.url.path)
            requests.append(dict(method=request.method, path=path, status=503 if lose else response.status_code,
                                 committedResponseSuppressed=lose))
            save(directory / 'RequestCounts.json', requests)
        return JSONResponse({'error': 'fixture_reply_lost_after_commit'}, status_code=503) if lose else response

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(128)
    listener.setblocking(False)
    origin = 'http://127.0.0.1:' + str(listener.getsockname()[1])
    config = directory / 'server-configuration.json'
    save(config, dict(version=1, mode='ManagedGuestServer', origin=origin,
        identityScope='review-vk102-' + args.run_id[:16], allowDevelopmentLoopback=True, socialEnabled=False))
    save(connection, dict(runId=args.run_id, origin=origin, serverConfigurationPath=str(config),
        operatorControlPath=str(control), scope='Actual local managed guest, device signatures, VK callback route and SQLite account operations. VK HTTP is an explicit in-process synthetic transport; no real VK/browser/SDK, ordinary account or production activation.'))
    uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning', proxy_headers=False,
                                 server_header=False)).run(sockets=[listener])


if __name__ == '__main__':
    main()
