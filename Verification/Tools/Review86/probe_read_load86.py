"""Isolated80-read/four-thread ASGI/SQLite diagnostic, not hosted capacity proof.

Creates four temporary operator-provisioned accounts, never logs credentials or
raw responses, and removes its private database after comparing business state.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Backend'))

from fastapi.testclient import TestClient
from hotr_backend.api import create_app


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    paths = list((ROOT / 'Backend/hotr_backend').rglob('*.py')) + list((ROOT / 'Backend/config').rglob('*.json'))
    paths += [p for name in ('requirements.txt', 'pyproject.toml') if (p := ROOT / 'Backend' / name).is_file()]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def state(database):
    # Include every ordinary table except documented authentication clock/rate
    # counters; only hashes/counts leave the temporary DB, never row contents.
    excluded = ('clock_state', 'rate_windows', 'identity_rate_windows')
    with database.connect() as db:
        names = sorted(row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                       if row[0] not in excluded)
        rows = {name: sorted(json.dumps(dict(row), sort_keys=True, ensure_ascii=True, separators=(',', ':'))
                             for row in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')) for name in names}
    canonical = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return {'sha256': hashlib.sha256(canonical).hexdigest(), 'tableRowCounts': {name: len(value) for name, value in rows.items()},
            'excludedAuthMetadata': list(excluded)}


def distribution(values):
    ordered = sorted(values)
    return {'count': len(values), 'medianMs': round(statistics.median(values), 3),
            'p95Ms': round(ordered[math.ceil(.95 * len(ordered)) - 1], 3), 'maxMs': round(ordered[-1], 3),
            'p95Definition': 'Nearest rank, ceil(0.95*n), including all collected requests'} if values else {'count': 0}


def main():
    run_id = uuid.uuid4().hex
    folder = ROOT / '.verification-cache/Review86/ReadLoad' / run_id
    folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    before_sources = sources()
    report = {'schemaVersion': 1, 'runId': run_id, 'status': 'FAIL_ISOLATED_ASGI_READ_LOAD86',
        'utc': datetime.now(timezone.utc).isoformat(), 'threads': 4, 'requestsPerThread': 20, 'plannedReads': 80,
        'operatorProvisionedTemporaryPlayers': 4, 'actualAsgiSqlite': True, 'tcp': False, 'productionCapacityCertification': False,
        'scope': 'Actual FastAPI/Starlette TestClient in-process ASGI and temporary real SQLite/WAL. Four distinct operator-provisioned owners, four concurrent client threads,80 total wallet/profile/time reads. Includes HTTP client/ASGI/thread/SQLite overhead; not TCP, hosted throughput, payment, Unity/device performance or a production load threshold.',
        'host': {'os': platform.system(), 'release': platform.release(), 'architecture': platform.machine(),
                 'cpu': platform.processor(), 'logicalCpuCount': os.cpu_count(), 'python': platform.python_version(),
                 'sqlite': sqlite3.sqlite_version, 'otherReviewProcessesMayBeActive': True},
        'toolSHA256': sha(Path(__file__)), 'sourcesBefore': before_sources, 'errors': [],
        'privateDatabaseRemoved': False, 'sourceFilesChanged': [], 'readOnlyBusinessState': False}
    rows = []
    try:
        with tempfile.TemporaryDirectory(prefix='private-', dir=folder) as private:
            app = create_app(Path(private) / 'authority.sqlite3', social_enabled=True, identity_enabled=False,
                             replay_enabled=False, notifications_enabled=False)
            owners = [app.state.authority.provision(lifetime=600) for _ in range(4)]
            before = state(app.state.authority.database)
            report['businessBefore'] = before
            barrier = threading.Barrier(4)
            endpoints = ('/v1/wallet', '/v1/profile', '/v1/time')

            def read(worker):
                samples = []
                with TestClient(app, raise_server_exceptions=False) as client:
                    barrier.wait(timeout=5)
                    for index in range(20):
                        endpoint = endpoints[(index + worker) % len(endpoints)]
                        at = time.perf_counter()
                        response = client.get(endpoint, headers={'Authorization': 'Bearer ' + owners[worker]['token']})
                        elapsed = (time.perf_counter() - at) * 1000
                        owner_valid = False
                        if response.status_code == 200:
                            try:
                                value = response.json()
                                owner_valid = (type(value.get('serverUtc')) is int and type(value.get('day')) is int
                                               if endpoint == '/v1/time' else value.get('playerId') == owners[worker]['playerId'])
                            except (ValueError, TypeError):
                                pass
                        samples.append({'thread': worker, 'ordinal': index, 'endpoint': endpoint,
                                        'status': response.status_code, 'latencyMs': elapsed, 'ownerOrTimeContract': owner_valid})
                return samples

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                futures = [pool.submit(read, worker) for worker in range(4)]
                for future in futures:
                    rows.extend(future.result(timeout=60))
            after = state(app.state.authority.database)
            report['businessAfter'] = after
            report['readOnlyBusinessState'] = before == after
            report['completedReads'] = len(rows)
            report['allOwnerOrTimeContractsMatched'] = all(row['ownerOrTimeContract'] for row in rows)
            report['statuses'] = {str(status): sum(row['status'] == status for row in rows) for status in sorted({r['status'] for r in rows})}
            report['latencies'] = distribution([row['latencyMs'] for row in rows])
            report['endpoints'] = {endpoint: {'statuses': {str(status): sum(row['endpoint'] == endpoint and row['status'] == status for row in rows)
                                                            for status in sorted({r['status'] for r in rows if r['endpoint'] == endpoint})},
                                             'latencies': distribution([row['latencyMs'] for row in rows if row['endpoint'] == endpoint])}
                                   for endpoint in endpoints}
        report['privateDatabaseRemoved'] = not Path(private).exists()
    except Exception as error:
        report['errors'].append(type(error).__name__)  # No body/token/exception text.
    finally:
        after_sources = sources()
        report['sourcesAfter'] = after_sources
        report['sourceFilesChanged'] = sorted(name for name in before_sources.keys() | after_sources.keys()
                                              if before_sources.get(name) != after_sources.get(name))
        report['elapsedSeconds'] = round(time.monotonic() - started, 3)
        if (not report['errors'] and report.get('completedReads') == 80 and report.get('statuses') == {'200': 80}
                and report.get('allOwnerOrTimeContractsMatched') and report['readOnlyBusinessState']
                and report['privateDatabaseRemoved'] and not report['sourceFilesChanged']):
            report['status'] = 'PASS_ISOLATED_ASGI_READ_LOAD86'
        # Request timings/statuses contain no IDs, credentials, payloads or raw
        # response bodies. Retain every sample, including slower requests.
        (folder / 'Samples.json').write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
        report['samplesSHA256'] = sha(folder / 'Samples.json')
        (folder / 'Report.json').write_text(json.dumps(report, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
        print(json.dumps({'status': report['status'], 'report': str(folder / 'Report.json'),
                          'statuses': report.get('statuses'), 'latencies': report.get('latencies'),
                          'readOnlyBusinessState': report['readOnlyBusinessState'],
                          'privateDatabaseRemoved': report['privateDatabaseRemoved']}))
    return 0 if report['status'] == 'PASS_ISOLATED_ASGI_READ_LOAD86' else 1


if __name__ == '__main__':
    raise SystemExit(main())
