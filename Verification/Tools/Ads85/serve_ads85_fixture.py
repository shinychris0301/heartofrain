"""Explicit loopback rewarded-ad HTTP fixture; no stored/preprovisioned bearer.

Native clients create real managed guests via signed identity HTTP. The capped
SDK-report policy deliberately proves no impression/provider signature/revenue.
The API never exposes trusted-completion or clock-control endpoints.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Backend'))

import uvicorn
from hotr_backend.api import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    directory = Path(args.directory).resolve()
    allowed = (ROOT / '.verification-cache/ShopAds85/HTTP').resolve()
    if (not directory.is_relative_to(allowed) or directory == allowed
            or len(args.run_id) != 32 or any(c not in '0123456789abcdef' for c in args.run_id)):
        raise SystemExit('Invalid isolated fixture directory or run ID')
    directory.mkdir(parents=True, exist_ok=True)
    connection, database = directory / 'connection.json', directory / 'authority.sqlite3'
    if args.resume:
        prior = json.loads(connection.read_text('utf-8'))
        if prior.get('runId') != args.run_id or not database.is_file():
            raise SystemExit('Wrong isolated fixture run')
    elif connection.exists() or database.exists():
        raise SystemExit('Fixture exists; use explicit resume')
    config = json.loads((ROOT / 'Backend/config/ads.json').read_text('utf-8'))
    config.update(enabled=True, completionMode='sdk_client_reported_capped')
    ads = directory / 'ads.json'
    ads.write_text(json.dumps(config), encoding='utf-8')
    os.environ['HOTR_BACKEND_MODE'] = 'local'
    app = create_app(database, ROOT / 'Backend/config', identity_enabled=True,
                     notifications_enabled=False, social_enabled=False, replay_enabled=False,
                     ads_config_path=ads)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(128)
    listener.setblocking(False)
    metadata = {'runId': args.run_id, 'origin': f'http://127.0.0.1:{listener.getsockname()[1]}/',
                'pid': os.getpid(), 'completionMode': config['completionMode'], 'realAdImpressionVerified': False,
                'scope': 'Isolated signed managed identity and capped client-reported ad claim; no SDK/network impression, payments, trusted-completion route or production activation'}
    temporary = connection.with_suffix('.tmp')
    temporary.write_text(json.dumps(metadata), encoding='utf-8')
    temporary.replace(connection)
    uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning',
                                  proxy_headers=False, server_header=False)).run(sockets=[listener])


if __name__ == '__main__':
    main()
