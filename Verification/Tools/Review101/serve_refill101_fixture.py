"""Private managed-guest HTTP service for the focused refill renewal regression.

Real identity signatures/rotation and wallet transactions; trusted test-operator
wallet setup is a bounded local file, never a route or production configuration.
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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Backend'))
import uvicorn
from hotr_backend.api import create_app
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
    if not directory.is_relative_to((ROOT / '.verification-cache/Review101/RefillHTTP').resolve()) or not re.fullmatch('[a-f0-9]{32}', args.run_id):
        parser.error('Exact fresh private refill101 directory required')
    directory.mkdir(parents=True, exist_ok=True)
    database = directory / 'authority.sqlite3'
    connection = directory / 'connection.json'
    control = directory / 'operator.json'
    if database.exists() or connection.exists():
        parser.error('Fresh managed identity fixture required')
    os.environ['HOTR_BACKEND_MODE'] = 'local'
    app = create_app(database, ROOT / 'Backend/config', identity_enabled=True, notifications_enabled=False,
                     social_enabled=False, replay_enabled=False)
    save(control, dict(seed=False, seedPlayerId=None))
    seeded = False
    timer_seeded = False
    requests = []

    @app.middleware('http')
    async def setup(request, call_next):
        nonlocal seeded, timer_seeded
        if request.method == 'GET' and request.url.path == '/v1/wallet':
            if control.stat().st_size > 2048:
                raise RuntimeError('BoundedPrivateSeedControlRequired101')
            value = json.loads(control.read_text('utf-8'))
            if value.get('seed') is True and not seeded:
                player = value.get('seedPlayerId')
                if not isinstance(player, str) or not re.fullmatch('[a-f0-9]{32}', player):
                    raise RuntimeError('ExactManagedPlayerRequired101')
                with app.state.authority.database.transaction() as db:
                    row = db.execute('SELECT initialized,balances FROM wallets WHERE player_id=?', (player,)).fetchone()
                    if row is None or not row['initialized'] or json.loads(row['balances']) != GENESIS:
                        raise RuntimeError('FreshActualManagedGenesisRequired101')
                    delta = [0] * 11
                    delta[0], delta[10] = -350, -5
                    now = int(time.time())
                    project(db, player, 'verification101/operator-seed', delta, now)
                    db.execute('UPDATE wallets SET next_life_at=? WHERE player_id=?', (now + 1800, player))
                seeded = True
                save(directory / 'SeedReceipt.json', dict(playerIdSHA256=hashlib.sha256(player.encode()).hexdigest(),
                                                         coins=900, lives=0, trustedOperatorSeed=True))
                save(control, dict(seed=False, seedPlayerId=player))
            if value.get('timerSeed') is True and not timer_seeded:
                player = value.get('timerPlayerId')
                if not isinstance(player, str) or not re.fullmatch('[a-f0-9]{32}', player):
                    raise RuntimeError('ExactTimerManagedPlayerRequired101')
                with app.state.authority.database.transaction() as db:
                    row = db.execute('SELECT initialized,balances FROM wallets WHERE player_id=?', (player,)).fetchone()
                    if row is None or not row['initialized'] or json.loads(row['balances']) != GENESIS:
                        raise RuntimeError('FreshTimerManagedGenesisRequired101')
                    delta = [0] * 11
                    delta[10] = -2
                    now = int(time.time())
                    project(db, player, 'verification101/operator-timer-seed', delta, now)
                    db.execute('UPDATE wallets SET next_life_at=? WHERE player_id=?', (now + 2, player))
                timer_seeded = True
                save(directory / 'TimerSeedReceipt.json', dict(playerIdSHA256=hashlib.sha256(player.encode()).hexdigest(),
                                                              coins=1250, lives=3, dueOffsetSeconds=2,
                                                              trustedOperatorSeed=True))
                save(control, dict(timerSeed=False, timerPlayerId=player))
        response = await call_next(request)
        if len(requests) < 256:
            requests.append(dict(method=request.method, path=request.url.path, status=response.status_code))
            save(directory / 'RequestCounts.json', requests)
        return response

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(128)
    listener.setblocking(False)
    origin = 'http://127.0.0.1:' + str(listener.getsockname()[1])
    config = directory / 'server-configuration.json'
    save(config, dict(version=1, mode='ManagedGuestServer', origin=origin,
                      identityScope='review-refill101-' + args.run_id[:16], allowDevelopmentLoopback=True, socialEnabled=False))
    save(connection, dict(runId=args.run_id, origin=origin, serverConfigurationPath=str(config), operatorControlPath=str(control),
                          scope='Real local managed guest/refresh and SQLite refill; private trusted operator genesis adjustment. No SDK/provider, gameplay replay worker, ordinary profile or production activation.'))
    uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning', proxy_headers=False,
                                 server_header=False)).run(sockets=[listener])


if __name__ == '__main__':
    main()
