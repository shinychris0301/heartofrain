"""Run bounded Review115 ASGI/SQLite regression and bind its input hashes."""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[3]
backend = root / 'Backend'
out = root / 'Verification' / 'Evidence' / 'Review115' / 'Backend'
out.mkdir(parents=True, exist_ok=True)
modules = ['test_friend_search_deletion115', 'test_staging_upgrade115', 'test_friend_search115', 'test_leaderboard_refresh115', 'test_records', 'test_regions89',
           'test_friends', 'test_teams_access109', 'test_team_life110',
           'test_team_mail111', 'test_team_invites112', 'test_team_leave113']
inputs = sorted(list((backend / 'hotr_backend').glob('*.py')) +
                list((backend / 'tests').glob('*.py')) +
                list((backend / 'config').glob('*.json')) + [Path(__file__).resolve()])

def hashes():
    return {str(p.relative_to(root)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in inputs}

before = hashes()
(out / 'InputsBeforeRelease115.json').write_text(json.dumps(before, indent=2) + '\n', encoding='utf-8')
start = time.monotonic()
log = out / 'FocusedRelease.log'
with log.open('xb') as stream:
    result = subprocess.run([sys.executable, '-B', '-m', 'unittest',
                             *('tests.' + m for m in modules)],
                            cwd=backend, stdout=stream, stderr=subprocess.STDOUT, timeout=480)
elapsed = time.monotonic() - start
after = hashes()
(out / 'InputsAfterRelease115.json').write_text(json.dumps(after, indent=2) + '\n', encoding='utf-8')
content = log.read_text(encoding='utf-8', errors='replace')
import re
match = re.search(r'Ran (\d+) tests in [\d.]+s\s+\nOK(?:\s|$)', content)
passing = result.returncode == 0 and before == after and match is not None
report = {'status': 'PASS' if passing else 'FAIL', 'testsRun': int(match.group(1)) if match else None,
          'elapsedSeconds': round(elapsed, 3), 'exitCode': result.returncode,
          'sourcesUnchanged': before == after, 'inputCount': len(inputs), 'modules': modules,
          'log': 'FocusedRelease.log', 'logSHA256': hashlib.sha256(log.read_bytes()).hexdigest(),
          'scope': 'Actual in-process ASGI and temporary SQLite; synthetic upstream verification; no hosted service, Unity or device.',
          'warning': 'Existing Starlette TestClient/httpx deprecation.'}
(out / 'FocusedRelease.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report), flush=True)
sys.exit(0 if passing else 1)
