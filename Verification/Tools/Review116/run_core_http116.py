"""Fresh owned Unity-to-backend HTTP checks; no production/provider operations.

Reuse established fixture implementations with fresh private databases. The
native116 runner independently binds source bytes and owns each Unity process.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
from run_ads85_native import OwnedJob, sha, utc, write
sys.path.insert(0, str(ROOT / 'Verification/Tools/Review93'))
from run_connected import resume_owned_primary, listener_closed


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bind(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


def legacy_listener_pid(origin):
    """Read the OS listener owner when the old fixture omits PID metadata."""
    from urllib.parse import urlparse
    endpoint = urlparse(origin)
    if endpoint.scheme != 'http' or endpoint.hostname != '127.0.0.1' or not endpoint.port:
        raise ValueError('ExactOwnedLoopbackRequiredForPidLookup')
    script = ("$ErrorActionPreference='Stop'; Get-NetTCPConnection -LocalAddress 127.0.0.1 "
              "-LocalPort " + str(endpoint.port) + " -State Listen | "
              "Select-Object -ExpandProperty OwningProcess -Unique | ConvertTo-Json -Compress")
    result = subprocess.run(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive',
                             '-Command', script], capture_output=True, timeout=30,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('OwnedListenerOperatingSystemLookupFailed')
    value = json.loads(result.stdout.decode('utf-8-sig').strip())
    if type(value) is not int or value <= 0:
        raise RuntimeError('OneExactOperatingSystemListenerRequired')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--backend-report', type=Path, required=True)
    parser.add_argument('--canonical-manifest', type=Path, required=True)
    parser.add_argument('--only', help='Comma-separated independent configured HTTP cases')
    args = parser.parse_args()
    if not args.execute or not args.tag.isalnum() or len(args.tag) > 20:
        parser.error('ExplicitFreshOwned116HttpRequired')
    proof_path = args.backend_report.resolve()
    proof = json.loads(proof_path.read_text('utf-8-sig'))
    if (proof.get('status') != 'PASS_BACKEND_SERVICE_TESTS' or proof.get('executedTests', 0) < 693
            or not proof.get('actualPinnedWorkerIntegration')
            or any(proof.get(k) for k in ('failures', 'errors', 'skipped', 'sourceInputsChangedDuringRun'))):
        parser.error('PassingFullActualWorkerBackendProofRequired')
    # Operational test-harness-only repairs can follow that proof; every runtime,
    # catalog and unit-test byte must still match the actual full execution.
    backend_root = ROOT / '.verification-cache/Review116/CommitSource/Backend'
    runtime_changes = [name for name, digest in proof['sourceSHA256'].items()
                       if name.startswith(('Backend/hotr_backend/', 'Backend/config/', 'Backend/tests/'))
                       and sha(backend_root / name.removeprefix('Backend/')) != digest]
    if runtime_changes:
        parser.error('BackendRuntimeOrTestSourcesChanged')
    native = load(ROOT / 'Verification/Evidence/Review116/App/run_snapshot_native116.py', 'core_native116')
    native.CANONICAL_MANIFEST = args.canonical_manifest.resolve()
    fixture_alias = load(ROOT / 'Verification/Evidence/Review116/App/snapshot_fixture_alias116.py', 'core_alias116')
    ownership = load(ROOT / 'Verification/Tools/Review113/run_leave_http113.py', 'core_ownership116')
    if native.editors()[0]:
        parser.error('MainEditorMustBeIdle')
    out = ROOT / 'Verification/Evidence/Review116/Connected' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    approval = ROOT / 'Verification/Evidence/ServerGameplay83/Backend/Verified324/Local_Approval.json'
    job_fixture = ROOT / 'Verification/Evidence/ServerReplay83/Native/Fixtures/L08_Continue1.job.json'
    services, owned = {}, []
    record = dict(status='RUNNING_CORE_HTTP116', startedUtc=utc(), backendProof=bind(proof_path),
                  runner=bind(Path(__file__)), nativeRunner=bind(Path(native.__file__)), runs=[],
                  scope='Actual Unity Editor HTTP over owned loopback services, temporary SQLite and real approved replay worker. Payment publisher/SDK are synthetic controls; no hosted provider/device/production acceptance.')

    def start(kind):
        ident = uuid.uuid4().hex
        locations = {'Gateway': ('.verification-cache/ServerGameplay83/HTTP', 'Verification/Tools/serve_server_gameplay83_fixture.py'),
                     'Social': ('.verification-cache/Launch82/HTTP', 'Verification/Tools/serve_identity82_fixture.py'),
                     'Payment': ('.verification-cache/RuStore81', 'Verification/Tools/serve_rustore81_fixture.py'),
                     'Commerce': ('.verification-cache/Review100/CommerceHTTP', 'Verification/Tools/Review100/serve_commerce100_fixture.py')}
        base, relative = locations[kind]
        private, script = ROOT / base / ident, ROOT / relative
        private.mkdir(parents=True, exist_ok=False)
        launcher = ROOT / 'Verification/Evidence/Review116/App/run_canonical_backend_fixture116.py'
        command = [str(ROOT / 'Backend/.venv/Scripts/python.exe'), '-B', str(launcher),
                   '--backend-root', str(backend_root), '--backend-proof', str(proof_path),
                   '--fixture', str(script), '--receipt', str(private / 'BackendImport116.json'), '--',
                   '--directory', str(private), '--run-id', ident]
        if kind == 'Gateway':
            command += ['--bundle', str(ROOT / '.verification-cache/PinnedReplay83/Worker'),
                        '--approval', str(approval), '--approval-sha256', sha(approval), '--continue-job', str(job_fixture)]
        elif kind == 'Social':
            command.append('--social')
        job = OwnedJob()
        with (private / 'Server.log').open('xb') as stream:
            process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW | 0x4)
        owned.append((job, process))
        job.assign(process.pid)
        resume_owned_primary(process)
        connection = private / 'connection.json'
        for _ in range(600):
            if connection.is_file():
                metadata = json.loads(connection.read_text('utf-8-sig'))
                listener_pid = metadata.get('pid')
                if kind == 'Payment' and listener_pid is None:
                    listener_pid = legacy_listener_pid(metadata['origin'])
                if (metadata.get('runId') != ident or listener_closed(metadata['origin'])
                        or not ownership.live_owned_pid(job, listener_pid)):
                    raise RuntimeError('Owned116ListenerMismatch')
                alias = fixture_alias.create(private)
                client_connection = alias['alias'] / 'connection.json'
                if kind == 'Commerce':
                    # The native fixture deliberately restricts operator controls
                    # to its own lexical root. Keep the original private config
                    # intact and project only fresh owned paths through the alias.
                    client_metadata = dict(metadata)
                    for field in ('providerControlPath', 'catalogPath'):
                        original = Path(metadata[field]).resolve()
                        relative_control = original.relative_to(private.resolve())
                        if not original.is_file():
                            raise RuntimeError('FreshCommerceControlFileRequired116')
                        client_metadata[field] = str(alias['alias'] / relative_control)
                    client_private = private / 'client_connection116.json'
                    with client_private.open('x', encoding='utf-8', newline='\n') as stream:
                        json.dump(client_metadata, stream, ensure_ascii=True)
                    client_connection = alias['alias'] / client_private.name
                services[kind] = dict(origin=metadata['origin'], connection=connection, private=private,
                                      metadata=metadata, script=script, alias=alias,
                                      clientConnection=client_connection,
                                      listenerPid=listener_pid,
                                      backendImportReceipt=private / 'BackendImport116.json')
                return services[kind]
            if process.poll() is not None:
                raise RuntimeError('Owned116FixtureStartupFailed')
            time.sleep(.1)
        raise TimeoutError('Owned116FixtureStartupDeadline')

    try:
        gateway, social, payment, commerce = [start(k) for k in ('Gateway', 'Social', 'Payment', 'Commerce')]
        env = dict(HOTR_SERVER_GAMEPLAY_HTTP_ALLOWED='1', HOTR_SERVER_GAMEPLAY_HTTP_ORIGIN=gateway['origin'],
                   HOTR_SERVER_GAMEPLAY_CONTINUE_JOB=str(job_fixture), HOTR_SOCIAL82_HTTP_ALLOWED='1',
                   HOTR_SOCIAL82_HTTP_ORIGIN=social['origin'], HOTR_IDENTITY82_HTTP_ALLOWED='1',
                   HOTR_IDENTITY82_HTTP_ORIGIN=social['origin'],
                   HOTR_RUSTORE81_HTTP_CONFIG=str(payment['alias']['alias'] / 'connection.json'),
                   HOTR_COMMERCE100_HTTP_CONFIG=str(commerce['clientConnection']))
        configured = json.loads((ROOT / 'Verification/Tools/Review93/suites.json').read_text('utf-8'))['connectedCases']
        configured.append(dict(name='CommerceHttp', entry='HeartOfTheRain.Verification.Commerce100HttpVerification.Run',
            report='Native/Commerce100Http.json', expected='PASS_NATIVE_COMMERCE_HTTP100', environment='HOTR_REVIEW100_OUT', timeout=600))
        if args.only:
            requested = args.only.split(',')
            lookup = {case['name']: case for case in configured}
            if len(set(requested)) != len(requested) or set(requested) - lookup.keys():
                raise ValueError('UniqueConfiguredCoreHttpCasesRequired')
            configured = [lookup[name] for name in requested]
        for case in configured:
            case = dict(case, fixtureEnvironment=env)
            state = native.execute(case, args.tag + '_' + case['name'])
            record['runs'].append(dict(name=case['name'], status=state['status'], checks=state.get('checks', 0),
                invocation='Verification/Evidence/Review116/App/Native/' + args.tag + '_' + case['name'] + '/Invocation.json'))
            if (state.get('nativeStatus') == 'MISSING' or not state.get('mainInputsUnchanged')
                    or state.get('mainEditorPidsAfter')):
                break
        commerce_audit = load(ROOT / 'Verification/Tools/Review100/run_commerce_http100.py', 'core_commerce116')
        record['commerceDatabaseAudit'] = commerce_audit.audit(commerce['private'] / 'authority.sqlite3', commerce['metadata'])
        record['status'] = ('PASS_CORE_HTTP116' if len(record['runs']) == len(configured) and
                            all(r['status'] == 'PASS_NATIVE116_INVOCATION' for r in record['runs']) else 'FAIL_CORE_HTTP116')
    except Exception as error:
        record.update(status='FAIL_CORE_HTTP116', errorType=type(error).__name__)
    finally:
        record['ownedChildClosures'] = [native.shared.owned_shutdown(job) for job, _ in owned]
        for _, process in owned:
            if process.poll() is None:
                process.wait(timeout=30)
        for _ in range(50):
            if all(listener_closed(row['origin']) for row in services.values()):
                break
            time.sleep(.1)
        record.update(services=[dict(kind=kind, origin=row['origin'], listenerPid=row['listenerPid'],
            listenerOwnerInExactOwnedJobVerified=True, fixture=bind(row['script']),
            privateConfig=bind(row['connection']),
            canonicalBackendImport=bind(row['backendImportReceipt']),
            fixtureAlias={k: str(v) if isinstance(v, Path) else v for k, v in row['alias'].items()},
            listenerClosed=listener_closed(row['origin'])) for kind, row in services.items()],
            ownedProcessesClosed=all(p.poll() is not None for _, p in owned), finishedUtc=utc())
        if (not record['ownedProcessesClosed'] or any(not r['listenerClosed'] for r in record['services'])
                or any(not c.get('observed') or not c.get('allObservedHandlesSignaled')
                       for c in record['ownedChildClosures'])):
            record['status'] = 'FAIL_CORE_HTTP116_CLEANUP'
        write(out / 'Report.json', record)
    print(json.dumps(dict(status=record['status'], report=(out / 'Report.json').relative_to(ROOT).as_posix())), flush=True)
    return 0 if record['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
