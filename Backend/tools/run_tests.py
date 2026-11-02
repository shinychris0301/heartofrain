"""Write a credential-free service test report, separate from native Unity reports."""
import datetime as dt
import argparse
import hashlib
import importlib.metadata
import io
import json
import os
import re
import sys
import time
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))


def case_id(test):
    # A few application fixtures legitimately store an attempt as self.id.
    # Report the unittest identity rather than calling or exposing that value.
    if isinstance(test, unittest.TestCase):
        return unittest.TestCase.id(test)
    return type(test).__module__ + '.' + type(test).__qualname__


def child_import_path():
    # CLI checks launch ``python -m hotr_backend...`` from the caller's cwd.
    # Unlike sys.path, PYTHONPATH reaches those fresh Windows interpreters.
    entries = [str(root), str(root / 'tests')]
    for entry in reversed(entries):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    entries.extend(p for p in os.environ.get('PYTHONPATH', '').split(os.pathsep) if p)
    os.environ['PYTHONPATH'] = os.pathsep.join(dict.fromkeys(entries))


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = []

    def addSuccess(self, test):
        self.passed.append(case_id(test))
        super().addSuccess(test)


def failure_locations(entries):
    # Export static file/line/function locations only, never assertion values,
    # input bodies or exception strings that may contain credentials.
    locations = []
    for test, trace in entries:
        frames = []
        for filename, line, method in re.findall(r'File "([^"]+)", line ([0-9]+), in ([A-Za-z_0-9]+)', trace):
            path = Path(filename).resolve()
            if path.is_relative_to(root):
                frames.append({'file': path.relative_to(root.parent).as_posix(), 'line': int(line), 'method': method})
        locations.append({'test': case_id(test), 'frames': frames})
    return locations


def source_hashes():
    paths = [p for folder in ('hotr_backend', 'tests', 'tools', 'config')
             for p in (root / folder).rglob('*') if p.is_file() and p.suffix in ('.py', '.json')]
    paths += [root / name for name in ('requirements.in', 'requirements.lock', 'README.md', 'Run-Local.ps1')]
    return {p.relative_to(root.parent).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=root.parent / 'Verification/Evidence/Backend')
    output = parser.parse_args(argv).out.resolve()
    child_import_path()
    source_before = source_hashes()
    started_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    started = time.monotonic()
    suite = unittest.defaultTestLoader.discover(str(root / 'tests'), top_level_dir=str(root))
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0, resultclass=Result).run(suite)
    source_after = source_hashes()
    source_changed = sorted(p for p in source_before.keys() | source_after.keys() if source_before.get(p) != source_after.get(p))
    passed = result.wasSuccessful() and not source_changed
    report = {
        'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'startedUtc': started_utc,
        'status': 'PASS_BACKEND_SERVICE_TESTS' if passed else 'FAIL_BACKEND_SERVICE_TESTS',
        'scope': 'Python service/ASGI and real SQLite transaction tests. The separately opt-in native integration invokes the approved real Unity worker only when its named test passes; other scripted progression/worker controls remain synthetic. Not an ordinary app, Android UI or real payment test.',
        'pythonVersion': sys.version.split()[0],
        'dependencies': {name: importlib.metadata.version(name) for name in ('fastapi', 'httpx', 'pydantic', 'pycryptodome', 'tzdata')},
        'tests': result.testsRun, 'executedTests': result.testsRun - len(result.skipped),
        'skipped': [case_id(test) for test, _ in result.skipped],
        'actualPinnedWorkerIntegration': any('test_replay_native_integration.' in name for name in result.passed),
        'seconds': round(time.monotonic() - started, 3), 'passed': result.passed,
        'failures': [case_id(test) for test, _ in result.failures], 'errors': [case_id(test) for test, _ in result.errors],
        'failureLocations': failure_locations(result.failures + result.errors),
        'sourceSHA256': source_before, 'sourceSHA256After': source_after,
        'sourceInputsChangedDuringRun': source_changed,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / 'Service_Tests.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors)}))
    if not passed:
        # Exception text is intentionally not exported; no credentials in reports.
        print('Failing cases:', ', '.join(report['failures'] + report['errors']))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
