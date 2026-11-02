"""Root-operated isolated real identity/wallet/replay fixture.

The operator-only L8 unlock and fixed native seed are synthetic fixtures. Public
requests still cannot select a seed, board, financial receipt or outcome. The
real pinned Unity worker verifies every submitted action and paid continuation.
No commerce provider or external listener is installed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Backend'))
import uvicorn
from starlette.responses import Response
from hotr_backend.api import create_app
from hotr_backend.replay_contract import ApprovedWorker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--approval', required=True)
    parser.add_argument('--approval-sha256', required=True)
    parser.add_argument('--continue-job', required=True)
    args = parser.parse_args()
    directory = Path(args.directory).resolve()
    allowed = (ROOT / '.verification-cache/ServerGameplay83/HTTP').resolve()
    if not directory.is_relative_to(allowed) or len(args.run_id) != 32 or any(c not in '0123456789abcdef' for c in args.run_id):
        raise SystemExit('Invalid isolated fixture binding')
    directory.mkdir(parents=True, exist_ok=True)
    database = directory / 'authority.sqlite3'
    if database.exists() or (directory / 'connection.json').exists():
        raise SystemExit('Use a fresh isolated fixture directory')
    fixture_path = Path(args.continue_job).resolve()
    fixture_bytes = fixture_path.read_bytes()
    fixture = json.loads(fixture_bytes)
    if fixture['level'] != 8 or fixture['starting'] != [0, 0, 0, 0] or not any(a['kind'] == 'Continue' for a in fixture['actions']):
        raise SystemExit('Expected the sealed native L8 natural Continue fixture')
    jobs = directory / 'jobs'
    jobs.mkdir()
    worker = ApprovedWorker(args.bundle, args.approval, args.approval_sha256, jobs, enabled=True)
    os.environ['HOTR_BACKEND_MODE'] = 'local'
    app = create_app(database, ROOT / 'Backend/config', identity_enabled=True,
                     notifications_enabled=False, social_enabled=True,
                     replay_enabled=True, replay_worker=worker)

    @app.middleware('http')
    async def operator_fixture(request, call_next):
        # This setup is private to the root-owned test process. It changes no
        # real profile and exposes no privileged HTTP endpoint or verifier key.
        if request.url.path == '/v1/wallet':
            with app.state.authority.database.transaction() as db:
                db.execute('UPDATE players SET completed=7 WHERE completed=0')
        response = await call_next(request)
        if request.url.path == '/v1/attempts/reserve' and response.status_code == 200:
            raw = b''.join([part async for part in response.body_iterator])
            value = json.loads(raw)
            attempt = value.get('attempt')
            if attempt and attempt['level'] == 8 and attempt['state'] == 'Reserved':
                with app.state.authority.database.transaction() as db:
                    db.execute("UPDATE gameplay_attempts SET seed=? WHERE id=? AND state='Reserved' AND NOT EXISTS(SELECT 1 FROM replay_attempts WHERE attempt_id=?)",
                               (fixture['seed'], attempt['attemptId'], attempt['attemptId']))
                # Return the server-owned value that Start and the worker use.
                attempt['seed'] = fixture['seed']
                if value['wallet'].get('activeAttempt'):
                    value['wallet']['activeAttempt']['seed'] = fixture['seed']
                raw = json.dumps(value, separators=(',', ':')).encode()
            headers = {key: item for key, item in response.headers.items() if key.lower() not in ('content-length', 'content-type')}
            return Response(raw, status_code=response.status_code, headers=headers, media_type='application/json')
        return response

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(128)
    listener.setblocking(False)
    metadata = {'runId': args.run_id, 'origin': f'http://127.0.0.1:{listener.getsockname()[1]}',
                'pid': os.getpid(), 'continueJobSHA256': hashlib.sha256(fixture_bytes).hexdigest(),
                'approvalSHA256': args.approval_sha256,
                'scope': 'Isolated real managed identity/server wallet/pinned Windows model worker; synthetic operator L8 unlock and native seed; no live IAP or production activation'}
    temporary = directory / 'connection.tmp'
    temporary.write_text(json.dumps(metadata), encoding='utf-8')
    temporary.replace(directory / 'connection.json')
    uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning', proxy_headers=False, server_header=False)).run(sockets=[listener])


if __name__ == '__main__':
    main()
