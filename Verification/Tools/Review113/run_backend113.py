"""Run bounded Review113 backend regression against disposable test fixtures."""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[3]
backend = root / 'Backend'
out = root / 'Verification/Evidence/Review113/Backend'
modules = [
    'tests.test_team_leave113', 'tests.test_messaging', 'tests.test_teams_access109',
    'tests.test_team_life110', 'tests.test_team_mail111', 'tests.test_team_invites112',
    'tests.test_social_operations', 'tests.test_operations', 'tests.test_staging_upgrade112',
]


def freeze():
    paths = sorted([*backend.glob('hotr_backend/*.py'), *backend.glob('tests/*.py'),
                    *backend.glob('config/*.json')])
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


out.mkdir(parents=True, exist_ok=True)
before = freeze()
started = time.monotonic()
proc = subprocess.run([sys.executable, '-B', '-m', 'unittest', *modules, '-v'], cwd=backend,
                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
log = proc.stdout.decode('utf-8', errors='replace')
after = freeze()
import re
found = re.search(r'Ran (\d+) tests? in ([\d.]+)s', log)
ok = proc.returncode == 0 and found is not None and re.search(r'(?m)^OK\s*$', log) is not None and before == after
(out / 'Focused05.log').write_text(log, encoding='utf-8')
(out / 'InputsFinal113_05.json').write_text(json.dumps(before, indent=2, sort_keys=True) + '\n', encoding='utf-8')
report = dict(status='PASS' if ok else 'FAIL', scope='In-process ASGI, temporary SQLite and stopped staging fixtures; no external service, Unity or device.',
              modules=modules, testsRun=int(found.group(1)) if found else None,
              elapsedSeconds=round(time.monotonic()-started, 2), exitCode=proc.returncode,
              sourcesUnchanged=before == after, inputCount=len(before),
              warning='Existing Starlette TestClient/httpx deprecation.',
              log='Focused05.log', inputs='InputsFinal113_05.json')
(out / 'Focused05.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report))
sys.exit(0 if ok else 1)
