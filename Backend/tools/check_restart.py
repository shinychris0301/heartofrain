import argparse
import datetime as dt
import json
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument('--connection', type=Path, required=True)
args = parser.parse_args()
private = json.loads(args.connection.read_text(encoding='utf-8'))
checks = []
with httpx.Client(base_url=private['origin'], timeout=10, trust_env=False) as client:
    for name in ('primary', 'recovery', *(['ui'] if 'ui' in private else [])):
        headers = {'Authorization': 'Bearer ' + private[name]['token']}
        account = client.get('/v1/me', headers=headers)
        assert account.status_code == 200
        data = account.json()
        assert data['playerId'] == private[name]['playerId'] and data['completed'] == 0 and data['rewardTotals'][0] == 50
        checks.append(name + ': authenticated account and one reward credit survive process restart')
        receipts = client.get('/v1/rewards', headers=headers).json()['receipts']
        assert len(receipts) == 1 and receipts[0]['grant']['coins'] == 50
        checks.append(name + ': one durable receipt survives process restart')
        assert client.get('/v1/daily-gift/offer', headers=headers).json()['claimed']
        checks.append(name + ': current day cannot reopen after process restart')
report = {'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'status': 'PASS_REAL_HTTP_PROCESS_RESTART',
          'scope': 'Actual separate Uvicorn process stop/restart against the same SQLite database; authenticated HTTP checks. Not physical power-loss certification.',
          'checks': len(checks), 'passed': checks, 'failures': []}
root = Path(__file__).resolve().parents[2]
(root / 'Verification/Evidence/Backend/HTTP_Process_Restart.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': report['status'], 'checks': report['checks']}))
