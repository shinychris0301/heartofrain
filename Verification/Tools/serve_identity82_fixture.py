"""Explicit isolated managed-identity HTTP fixture; no preprovisioned credentials.

Only local loopback is bound, no proxy headers/access logs are trusted, and no
real commerce provider is installed. Connection metadata contains no secrets.
All account/session state remains in ignored verification storage.
"""
import argparse
import json
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Backend'))

import uvicorn
from hotr_backend.api import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--social', action='store_true')
    args = parser.parse_args()
    directory = Path(args.directory).resolve()
    allowed = (ROOT / '.verification-cache/Launch82/HTTP').resolve()
    if not directory.is_relative_to(allowed) or len(args.run_id) != 32 or any(c not in '0123456789abcdef' for c in args.run_id):
        raise SystemExit('Invalid isolated fixture location or run ID')
    directory.mkdir(parents=True, exist_ok=True)
    connection = directory / 'connection.json'
    database = directory / 'authority.sqlite3'
    if args.resume:
        prior = json.loads(connection.read_text('utf-8'))
        if prior['runId'] != args.run_id or not database.is_file():
            raise SystemExit('Wrong isolated fixture run')
    elif connection.exists() or database.exists():
        raise SystemExit('Fixture exists; use explicit resume')
    os.environ['HOTR_BACKEND_MODE'] = 'local'
    app = create_app(database, ROOT / 'Backend/config', identity_enabled=True,
                     notifications_enabled=False, social_enabled=args.social)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(128)
    listener.setblocking(False)
    metadata = {'runId': args.run_id, 'origin': f'http://127.0.0.1:{listener.getsockname()[1]}/',
                'pid': os.getpid(), 'scope': 'Managed identity on isolated SQLite; no live payment provider'}
    temporary = connection.with_suffix('.tmp')
    temporary.write_text(json.dumps(metadata), encoding='utf-8')
    temporary.replace(connection)
    server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning',
                                         proxy_headers=False, server_header=False))
    server.run(sockets=[listener])


if __name__ == '__main__':
    main()
