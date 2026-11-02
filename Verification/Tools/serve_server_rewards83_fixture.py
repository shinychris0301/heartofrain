"""Isolated reward-service fixtures for root-operated native Unity HTTP checks.

Progression and the fixed clock below are explicitly operator-owned synthetic
test state, not model-verifier acceptance. No control endpoints are mounted.
Credentials stay in the ignored private directory; public metadata is redacted.
"""
import argparse
import json
import os
import socket
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Backend'))

import uvicorn
from hotr_backend.api import create_app
from hotr_backend.schemas import Command


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    directory = Path(args.directory).resolve()
    allowed = (ROOT / '.verification-cache/ServerRewards83/HTTP').resolve()
    if not directory.is_relative_to(allowed) or len(args.run_id) != 32 or any(c not in '0123456789abcdef' for c in args.run_id):
        raise SystemExit('Invalid isolated reward fixture location or run ID')
    directory.mkdir(parents=True, exist_ok=True)
    credentials_file, connection_file = directory / 'credentials.private.json', directory / 'connection.json'
    database = directory / 'authority.sqlite3'
    now = [1_800_000_000]
    os.environ['HOTR_BACKEND_MODE'] = 'local'
    app = create_app(database, ROOT / 'Backend/config', clock=lambda: now[0], identity_enabled=False,
                     notifications_enabled=False, social_enabled=False, replay_enabled=False)
    if args.resume:
        private = json.loads(credentials_file.read_text('utf-8'))
        prior = json.loads(connection_file.read_text('utf-8'))
        if private['runId'] != args.run_id or prior['runId'] != args.run_id:
            raise SystemExit('Wrong isolated reward fixture run')
        now[0] = private['serverUtc']
        port = prior['port']
    else:
        if credentials_file.exists() or connection_file.exists():
            raise SystemExit('Reward fixture exists; explicit resume required')
        identities = {name: app.state.authority.provision(lifetime=2_592_000) for name in ('gift', 'projection', 'expired', 'locked', 'milestone', 'cup', 'finished')}
        expired_offer = app.state.authority.daily_offer(app.state.authority.authenticate(identities['expired']['token']))
        with app.state.authority.database.transaction() as db:
            for name in ('milestone', 'cup', 'finished'):
                db.execute('UPDATE players SET completed=10 WHERE id=?', (identities[name]['playerId'],))
        actor = app.state.authority.authenticate(identities['finished']['token'])
        finished_run = uuid.uuid4().hex
        app.state.authority.cup_join(actor, Command(commandId=finished_run))
        now[0] += app.state.authority.cup.durationSeconds + 1
        private = {'runId': args.run_id, 'serverUtc': now[0], 'expiredOffer': expired_offer, **{name: {'playerId': value['playerId'], 'token': value['token']} for name, value in identities.items()}}
        port = 0
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', port))
    listener.listen(128)
    listener.setblocking(False)
    port = listener.getsockname()[1]
    origin = f'http://127.0.0.1:{port}/'
    private['origin'] = origin
    with credentials_file.open('w', encoding='utf-8') as file:
        json.dump(private, file)
    try:
        credentials_file.chmod(0o600)
    except OSError:
        pass  # The ignored fixture directory remains the Windows access boundary.
    metadata = {'runId': args.run_id, 'origin': origin, 'port': port, 'pid': os.getpid(), 'serverUtc': now[0],
                'scope': 'Synthetic operator progression and fixed clock; actual reward service/SQLite/HTTP; no gameplay or payment acceptance'}
    connection_file.write_text(json.dumps(metadata), encoding='utf-8')
    server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning', proxy_headers=False, server_header=False))
    server.run(sockets=[listener])


if __name__ == '__main__':
    main()
