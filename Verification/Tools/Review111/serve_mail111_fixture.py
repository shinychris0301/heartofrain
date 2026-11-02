"""Owned loopback fixture running the real111 service and SQLite transactions.

Capacity setup is an explicitly labelled private ledger debit, not gameplay.
One selected reply may be replaced by503 only AFTER the real claim commits.
There are no test routes, providers, external requests or shipped test hooks.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Backend'))
import uvicorn
from fastapi.responses import JSONResponse
from hotr_backend.api import create_app
from hotr_backend.wallet import ZERO, project


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, separators=(',', ':')), encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if (not directory.is_relative_to((ROOT / '.verification-cache/Review111/MailHTTP').resolve())
            or not re.fullmatch('[a-f0-9]{32}', args.run_id)):
        parser.error('Exact fresh owned Help111 directory required')
    directory.mkdir(parents=True, exist_ok=True)
    if any((directory / p).exists() for p in ('authority.sqlite3', 'connection.json', 'operator.json')):
        parser.error('Fresh private database required')
    for name in tuple(os.environ):
        if name.startswith('HOTR_'):
            os.environ.pop(name)
    os.environ['HOTR_BACKEND_MODE'] = 'local'
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    sock.listen(128)
    host, port = sock.getsockname()
    app = create_app(directory / 'authority.sqlite3', ROOT / 'Backend/config', lambda: 1800000000,
        identity_enabled=True, social_enabled=True, replay_enabled=False, notifications_enabled=False)
    control = directory / 'operator.json'
    save(control, dict(capacityPlayer='', capacityLives=-1, capacityTag='', dropClaimCommand='', seedPlayer='', seedTeam=''))
    capacities = []
    requests = []
    drops = []

    @app.middleware('http')
    async def observe(request, call_next):
        if control.stat().st_size > 4096:
            raise RuntimeError('BoundedPrivateControlRequired111')
        value = json.loads(control.read_text('utf-8'))
        if request.method == 'GET' and re.fullmatch('/v1/teams/[a-f0-9]{32}/mail', request.url.path) and value.get('seedPlayer'):
            player, team = value['seedPlayer'], value['seedTeam']
            if not re.fullmatch('[a-f0-9]{32}', player) or not re.fullmatch('[a-f0-9]{32}', team) or request.url.path != '/v1/teams/' + team + '/mail':
                raise RuntimeError('ExactSeedBindingRequired111')
            actor = app.state.authority.authenticate(request.headers.get('authorization', '').removeprefix('Bearer '))
            if actor.player != player: raise RuntimeError('ExactManagedSeedOwnerRequired111')
            with app.state.authority.database.transaction() as db:
                ids = [app.state.team_mail.issue_in_transaction(db, issuer='fixture', source_key=key,
                    team_id=team, player_id=player, sender_label='Test', title=title, body='Disposable fixture.',
                    coins=coins, lives=lives, expires_at=1800003600)
                    for key,title,coins,lives in [('mail_reward','Reward',300,2),('mail_later','Later',100,0),('mail_plain','Plain',0,0)]]
            save(directory/'SeededMail.json',dict(player=player,team=team,ids=ids,scope='explicit private trusted-source fixture; never a public issuance endpoint'))
            value.update(seedPlayer='',seedTeam='');save(control,value)
        if request.method == 'GET' and request.url.path == '/v1/wallet' and value['capacityPlayer']:
            player, wanted, tag = value['capacityPlayer'], value['capacityLives'], value['capacityTag']
            if (not re.fullmatch('[a-f0-9]{32}', player) or type(wanted) is not int or not 0 <= wanted < 5
                    or not re.fullmatch('[a-z0-9_]{1,32}', tag)):
                raise RuntimeError('ExactCapacityFixtureRequired111')
            header = request.headers.get('authorization', '')
            actor = app.state.authority.authenticate(header.removeprefix('Bearer '))
            if actor.player != player:
                raise RuntimeError('ExactManagedCapacityOwnerRequired111')
            with app.state.authority.database.transaction() as db:
                current = app.state.authority._transaction_actor(db, actor)
                wallet = app.state.wallet
                wallet._regenerate(db, current)
                row = wallet._guard(db, current, wallet._row(db, current.player)['revision'])
                before = json.loads(row['balances'])[10]
                if wanted >= before:
                    raise RuntimeError('CapacityFixtureMustBeNegativeLedgerDebit111')
                delta = ZERO.copy()
                delta[10] = wanted - before
                project(db, current.player, 'fixture111/capacity/' + tag, delta, current.now)
                wallet._life_timer(db, current, wanted)
            capacities.append(dict(playerSHA256=hashlib.sha256(player.encode()).hexdigest(),
                before=before, after=wanted, delta=wanted-before, tag=tag,
                scope='Private controlled capacity debit through actual ledger/life timer; no gameplay attempt/outcome.'))
            save(directory / 'CapacityReceipts.json', capacities)
            value.update(capacityPlayer='', capacityLives=-1, capacityTag='')
            save(control, value)
        selected = False
        if (request.method == 'POST' and re.fullmatch('/v1/teams/[a-f0-9]{32}/mail/[a-f0-9]{32}/claim', request.url.path)
                and value['dropClaimCommand']):
            body = json.loads((await request.body()).decode('utf-8'))
            selected = body.get('commandId') == value['dropClaimCommand']
        response = await call_next(request)
        lose = selected and response.status_code == 200
        if lose:
            drops.append(dict(afterActualCommit=True, originalStatus=200, clientStatus=503))
            save(directory / 'DroppedClaimResponses.json', drops)
            value['dropClaimCommand'] = ''
            save(control, value)
        if len(requests) >= 512:
            raise RuntimeError('BoundedOwnedHttpFlowRequired111')
        requests.append(dict(method=request.method,
            path=re.sub(r'/[a-f0-9]{32}(?=/|$)', '/{id}', request.url.path),
            status=503 if lose else response.status_code, committedResponseSuppressed=lose))
        save(directory / 'RequestCounts.json', requests)
        return JSONResponse({'error': 'synthetic_after_commit_reply_loss111'}, status_code=503) if lose else response

    metadata = dict(runId=args.run_id, pid=os.getpid(), origin=f'http://{host}:{port}',
        clock=1800000000, actualBackend=True, replayEnabled=False, providersEnabled=False,
        productionEnabled=False, scope='Owned loopback-only real service; controlled fixed clock and ledger capacity fixtures.')
    save(directory / 'connection.json', metadata)
    config = uvicorn.Config(app, host=host, port=port, log_level='warning', access_log=False)
    uvicorn.Server(config).run(sockets=[sock])


if __name__ == '__main__':
    main()
