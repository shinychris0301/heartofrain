"""Separate loopback HTTP process for native Unity verification; no credentials on stdout."""
import argparse
import asyncio
import json
import os
import socket
import sys
from pathlib import Path

import uvicorn
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hotr_backend.api import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--gift-ui', action='store_true', help='Isolated UI account and file-controlled response faults; never used by the service factory')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    directory = args.directory.resolve()
    if not directory.is_relative_to(repo / '.verification-cache/Backend'):
        raise SystemExit('Fixture storage must be in ignored backend verification cache')
    directory.mkdir(parents=True, exist_ok=True)
    app = create_app(directory / 'authority.sqlite3')
    authority = app.state.authority
    path = directory / 'connection.json'
    if args.resume:
        data = json.loads(path.read_text(encoding='utf-8'))
        if data['runId'] != args.run_id:
            raise SystemExit('Fixture identity mismatch')
    else:
        if path.exists():
            raise SystemExit('Fixture already exists; use a new run ID')
        data = {'runId': args.run_id, 'primary': authority.provision(), 'recovery': authority.provision()}
        if args.gift_ui:
            data['ui'] = authority.provision()
    if args.gift_ui:
        def take(name):
            flag = directory / (name + '.once')
            if flag.exists():
                flag.unlink()
                return True
            return False

        @app.middleware('http')
        async def explicit_fixture_faults(request, call_next):
            # Only operator-controlled ignored files can trigger these faults.
            # There is no HTTP fault/clock/reset endpoint in either factory.
            offer = request.url.path == '/v1/daily-gift/offer'
            claim = request.url.path == '/v1/daily-gift/claim'
            if offer and take('delay-offer') or claim and take('delay-claim'):
                await asyncio.sleep(2.5)
            if offer and take('offline-offer'):
                return JSONResponse({'error': 'fixture_unavailable'}, status_code=503)
            drop = claim and take('drop-claim')
            response = await call_next(request)
            if drop and response.status_code == 200:
                return JSONResponse({'error': 'fixture_confirmation_lost'}, status_code=503)
            return response
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    data['origin'] = 'http://127.0.0.1:' + str(listener.getsockname()[1]) + '/'
    temp = directory / 'connection.pending'
    with os.fdopen(os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as file:
        json.dump(data, file)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temp, path)
    server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning', proxy_headers=False, limit_concurrency=32))
    server.run(sockets=[listener])


if __name__ == '__main__':
    main()
