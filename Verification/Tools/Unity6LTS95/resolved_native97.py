"""Root-only expiring, process-local resolver wrapper around frozen LTS95 runners."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re

import smoke95
import game95

ROOT, EVIDENCE, PRIVATE = smoke95.ROOT, smoke95.EVIDENCE, smoke95.PRIVATE
RESOLVER = EVIDENCE/'ResolverMap97/Set01/Preparation.json'
RESOLVER_SHA = 'e9def4d6ce4108f8317d7faab28d50c6687b5b8e58c4571ff8dbd38741cd815c'
FROZEN = {
    'smoke95.py': '83290e004b0be5026ad9f94db48f02e56a6cef42b25f212ef2d0767002569a22',
    'game95.py': '75f675897a14500c79cf0662a6030eacff08004db73de9f74c535802e52e414f',
    'Templates/ToolchainSmoke95.cs': 'da5d1d13f03ec1b752a3eb416eeeb64a174efa422032ec22d107f04bf675392f',
    'Templates/Unity6LTSGame95.cs': '35ca70da4d178714bd84320476ea4179a44702ef5d9e4cce146062e710694025',
}
DEPENDENCIES = (
    'Verification/Tools/Ads85/run_ads85_native.py',
    'Verification/Tools/Unity6Migration94/run_native.py',
    'Verification/Tools/PageBackdrop90/process90.py',
    'Verification/Tools/Review93/run_connected.py',
    'Verification/Tools/Unity6Migration94/audit_candidate94.py',
)


def need(value, code):
    if not value:
        raise ValueError(code)


def utc():
    return datetime.now(timezone.utc)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def bound(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.write('\n')


def no_links(path):
    path = Path(path).absolute()
    for current in (path, *path.parents):
        if current.exists():
            info = current.lstat()
            need(not current.is_symlink() and not (getattr(info, 'st_file_attributes', 0) & 0x400),
                 'Resolved97LinkedPathRejected')


def contained(path, base):
    no_links(path)
    path, base = Path(path).resolve(), Path(base).resolve()
    need(path.is_relative_to(base) and path != base, 'Resolved97ContainedPathRequired')
    return path


def checked_item(item, base):
    need(isinstance(item, dict) and isinstance(item.get('path'), str), 'Resolved97ArtifactBindingRequired')
    path = Path(item['path'])
    if not path.is_absolute():
        path = ROOT/path
    path = contained(path, base)
    need(path.is_file() and sha(path) == item.get('sha256') and path.stat().st_size == item.get('bytes'),
         'Resolved97ArtifactHashOrBytesChanged')
    return path


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(result.tzinfo is not None and result.utcoffset() is not None, 'Resolved97TimezoneRequired')
    return result.astimezone(timezone.utc)


def options_for(hosts):
    return ['-Djdk.net.hosts.file='+str(hosts), '-Dsun.net.client.defaultConnectTimeout=10000',
            '-Dsun.net.client.defaultReadTimeout=15000', '-Dorg.gradle.daemon=false']


def parse_hosts(path):
    result = {}
    for line in Path(path).read_text('ascii').splitlines():
        fields = line.split('#', 1)[0].split()
        if not fields:
            continue
        need(len(fields) >= 2, 'Resolved97InvalidHostsLine')
        address = str(ipaddress.ip_address(fields[0]))
        for name in fields[1:]:
            need(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name) is not None, 'Resolved97InvalidHostToken')
            name = name.lower()
            need(address not in result.setdefault(name, []), 'Resolved97DuplicateHostAddress')
            result[name].append(address)
    return result


def validate_resolver(timeout, now=None):
    now = now or utc()
    contained(RESOLVER, EVIDENCE/'ResolverMap97')
    need(RESOLVER.is_file() and sha(RESOLVER) == RESOLVER_SHA, 'Resolved97ExactReviewedResolverPreparationRequired')
    proof = read(RESOLVER)
    need(proof.get('schemaVersion') == 1 and proof.get('status') == 'PREPARED_PRIVATE_EXPIRING_JAVA_RESOLVER_TEST97',
         'Resolved97ReviewedResolverStatusRequired')
    created, expires = instant(proof['utc']), instant(proof['expiresUtc'])
    need(created <= now and 0 < (expires-created).total_seconds() <= 3600,
         'Resolved97NoFutureOrOverlongMapping')
    need((expires-now).total_seconds() >= timeout+60, 'Resolved97InsufficientResolverLifetime')
    hosts = checked_item(proof['hostsFile'], PRIVATE/'Retry97')
    routes = checked_item(proof['googleRouteAuthority'], PRIVATE/'Retry97')
    dns = checked_item(proof['earlierDnsObservation'], PRIVATE/'Retry97')
    need(proof.get('overriddenNetworkHostnames') == ['dl.google.com']
         and proof.get('localHostnamesIncluded') is True and proof.get('localHostValuesPrivate') is True
         and proof.get('ordinaryRepositoryDomainCount', 0) >= 1, 'Resolved97NarrowReviewedResolverScopeRequired')
    need(proof.get('requiredJavaOptions') == options_for(hosts), 'Resolved97ExactJavaOptionsRequiredNoTLSOverrides')
    route = read(routes)
    need(route.get('host') == 'dl.google.com' and route.get('uri') == '/dl/android/maven2/com/android/tools/build/gradle/9.1.1/gradle-9.1.1.pom',
         'Resolved97ExactOfficialGoogleArtifactProbeRequired')
    rows = route.get('results')
    need(isinstance(rows, list) and len(rows) == 4 and all(row.get('success') is True
         and row.get('statusLine') == 'HTTP/1.1 200 OK' and row.get('tls') == 'TLSv1.3' for row in rows),
         'Resolved97FourSuccessfulRecordedTLSRoutesRequired')
    addresses = [str(ipaddress.ip_address(row['address'])) for row in rows]
    need(len(set(addresses)) == 4 and instant(route['utc']) <= created
         and (created-instant(route['utc'])).total_seconds() <= 600, 'Resolved97RecentDistinctRouteProofRequired')
    mapping = parse_hosts(hosts)
    need(set(mapping.get('dl.google.com', [])) == set(addresses)
         and {'127.0.0.1', '::1'}.issubset(set(mapping.get('localhost', []))), 'Resolved97HostsMustMatchVerifiedRoutesAndLoopback')
    return {'preparation': bound(RESOLVER), 'hostsFile': bound(hosts), 'googleRouteAuthority': bound(routes),
            'earlierDnsObservation': bound(dns), 'expiresUtc': proof['expiresUtc'],
            'requiredJavaOptions': proof['requiredJavaOptions'],
            'scope': 'Exclusive build JVM resolver; no OS fallback. Original hostnames/default TLS/trust retained. No APK contents or global settings changed.'}


def helper_bindings():
    folder = Path(__file__).parent
    result = {}
    for name, expected in FROZEN.items():
        path = folder/name
        need(sha(path) == expected, 'Resolved97FrozenRunnerOrTemplateChanged')
        result[name] = bound(path)
    for relative in DEPENDENCIES:
        result[relative] = bound(ROOT/relative)
    result['wrapper'] = bound(Path(__file__))
    return result


@contextmanager
def process_environment(request):
    previous = {key: os.environ.get(key) for key in request}
    try:
        os.environ.update(request)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def validate_arguments(action, operation, timeout):
    need(action in ('smoke', 'game') and timeout in (600, 900), 'Resolved97ActionAndBoundedTimeoutRequired')
    need((action == 'smoke' and operation is None) or
         (action == 'game' and operation in ('Configure', 'Inspect', 'BuildDevelopment')), 'Resolved97OperationMatchesActionRequired')


def existing_invocations(folder):
    if not folder.exists():
        return {}
    return {path.parent.name: bound(path) for path in folder.glob('*/Invocation.json')}


def new_invocation(folder, before, action, operation, code):
    after = existing_invocations(folder)
    need(all(after.get(key) == value for key, value in before.items()), 'Resolved97HistoricalInvocationChanged')
    fresh = set(after)-set(before)
    need(len(fresh) == 1 and re.fullmatch('[a-f0-9]{32}', next(iter(fresh))) is not None,
         'Resolved97ExactlyOneFreshNativeInvocationRequired')
    binding = after[next(iter(fresh))]
    path = contained(Path(binding['path']), folder)
    native = read(path)
    expected = ('PASS_ACTUAL_LTS95_TOOLCHAIN_SMOKE_WITH_NO_GAME_ACCEPTANCE' if action == 'smoke'
                else 'PASS_ACTUAL_LTS95_GAME_'+operation.upper())
    passed = (code == 0 and native.get('status') == expected and native.get('exitCode') == 0
              and not native.get('timedOut') and native.get('actualEngineVersionFromLog') == smoke95.VERSION
              and all(native.get(key) is True for key in ('mainInputsUnchanged', 'candidate66InputsUnchanged',
                  'externalToolPrefFingerprintsUnchanged', 'embeddedToolMarkersUnchanged'))
              and native.get('unityPidsAfter') == [])
    return {'invocation': binding, 'actualStatus': native.get('status'), 'actualNativeExitCode': native.get('exitCode'),
            'runnerReturnCode': code, 'passed': passed,
            'nativeReport': native.get('nativeReport'), 'unityLog': native.get('unityLog')}


def run(action, prepared, operation, timeout, output):
    validate_arguments(action, operation, timeout)
    prepared = contained(prepared, EVIDENCE/('SmokePreparation' if action == 'smoke' else 'GamePreparation'))
    need(prepared.name == 'Preparation.json' and prepared.is_file(), 'Resolved97NativePreparationRequired')
    output = contained(output, EVIDENCE/'ResolvedNative97')
    need(re.fullmatch('[a-f0-9]{32}', output.name) is not None and not output.exists(), 'Resolved97FreshUUIDOutputRequired')
    helpers, resolver, preparation = helper_bindings(), validate_resolver(timeout), bound(prepared)
    gradle_home = PRIVATE/'Gradle97'
    no_links(gradle_home)
    need(gradle_home.is_dir(), 'Resolved97ExistingPrivateGradleHomeRequired')
    need(all(not os.environ.get(key) for key in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JAVA_OPTS', 'GRADLE_OPTS')),
         'Resolved97UnexpectedExistingJavaEnvironment')
    need(not os.environ.get('GRADLE_USER_HOME') or Path(os.environ['GRADLE_USER_HOME']).resolve() == gradle_home.resolve(),
         'Resolved97UnexpectedExistingGradleHome')
    request = {'JAVA_TOOL_OPTIONS': ' '.join(resolver['requiredJavaOptions']), 'GRADLE_USER_HOME': str(gradle_home)}
    original_environment = {key: os.environ.get(key) for key in request}
    folder = EVIDENCE/('SmokeRuns' if action == 'smoke' else 'GameRuns')
    before = existing_invocations(folder)
    output.mkdir(parents=True, exist_ok=False)
    report = {'schemaVersion': 1, 'status': 'RUNNING_PROCESS_LOCAL_RESOLVED_NATIVE97', 'startedUtc': utc().isoformat(),
              'action': action, 'operation': operation, 'timeoutSeconds': timeout, 'runner': helpers['wrapper'],
              'helpersBefore': helpers, 'resolverBefore': resolver, 'nativePreparation': preparation,
              'requestedChildEnvironment': request, 'scope': 'Actual frozen native runner result only. No source/vendor/global preference, Windows DNS/hosts/trust or persistent environment change; resolver not shipped. No device/backend/provider/production acceptance.'}
    write(output/'Authorization.json', report)
    result = None
    try:
        with process_environment(request):
            need(validate_resolver(timeout) == resolver and helper_bindings() == helpers and bound(prepared) == preparation,
                 'Resolved97PreNativeBindingsChanged')
            # Normal function imports/calls. No patched globals, constants, environment getter or process implementation.
            code = smoke95.run(prepared, timeout) if action == 'smoke' else game95.run(operation, prepared, timeout)
        result = new_invocation(folder, before, action, operation, code)
        actual = read(Path(result['invocation']['path']))
        need(actual.get('preparation') == preparation and actual.get('runnerSHA256') == FROZEN[action+'95.py'],
             'Resolved97ActualInvocationMustBindExactPreparationAndFrozenRunner')
        report.update(actualNative=result, status='PASS_PROCESS_LOCAL_RESOLVED_NATIVE97' if result['passed'] else 'FAIL_ACTUAL_PROCESS_LOCAL_RESOLVED_NATIVE97')
    except Exception as error:
        report.update(status='FAIL_PROCESS_LOCAL_RESOLVED_NATIVE97', errorType=type(error).__name__, error=str(error))
        try:
            report['actualNative'] = new_invocation(folder, before, action, operation, None)
        except Exception as collection_error:
            report.update(collectionErrorType=type(collection_error).__name__, collectionError=str(collection_error))
    finally:
        try:
            # Rehash immutable mappings even if their lifetime elapsed; do not grant a second run.
            unchanged_resolver = bound(RESOLVER) == resolver['preparation'] and all(
                bound(Path(resolver[key]['path'])) == resolver[key]
                for key in ('hostsFile', 'googleRouteAuthority', 'earlierDnsObservation'))
            report.update(resolverFilesUnchanged=unchanged_resolver, helpersUnchanged=helper_bindings() == helpers,
                          nativePreparationUnchanged=bound(prepared) == preparation,
                          processEnvironmentRestored=all(os.environ.get(key) == value for key, value in original_environment.items()))
            need(report['resolverFilesUnchanged'] and report['helpersUnchanged'] and report['nativePreparationUnchanged']
                 and report['processEnvironmentRestored'], 'Resolved97FinalBindingOrEnvironmentInvariantFailed')
        except Exception as error:
            report.update(status='FAIL_PROCESS_LOCAL_RESOLVED_NATIVE97_INVARIANT', invariantErrorType=type(error).__name__, invariantError=str(error))
        report['finishedUtc'] = utc().isoformat()
        write(output/'Report.json', report)
        print(json.dumps({'status': report['status'], 'report': str(output/'Report.json')}), flush=True)
    return 0 if report['status'] == 'PASS_PROCESS_LOCAL_RESOLVED_NATIVE97' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true'); parser.add_argument('--action', choices=('smoke', 'game'), required=True)
    parser.add_argument('--prepared', type=Path, required=True); parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--operation', choices=('Configure', 'Inspect', 'BuildDevelopment'))
    parser.add_argument('--timeout', type=int, choices=(600, 900), required=True)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt':
        parser.error('Explicit root Windows action required; preparation authors execute host tests only')
    return run(args.action, args.prepared, args.operation, args.timeout, args.out)


if __name__ == '__main__':
    raise SystemExit(main())
