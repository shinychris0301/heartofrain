"""Root-only preparation/serial Editor compile of the current real Pay adapter.

Only `prepare` copies isolated inputs; only `run` starts a pinned Editor. Never
uses the main project as an SDK project or invokes initialization/payments/builds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_native86 import (OwnedJob, PINNED_UNITY, delta, disk, freeze, sha,
                          unchanged, unity_pids, utc, write)

CACHE = ROOT / '.verification-cache/Review86'
EVIDENCE = ROOT / 'Verification/Evidence/Review86/SDK'
BASELINE = ROOT / '.verification-cache/RuStore81/Spike'
LOCK = ROOT / 'Release/RuStore/sdk-lock.json'
SOURCE_NAMES = ('RuStorePayAdapter', 'PayStoreContracts', 'PayDeliveryCoordinator', 'FilePayJournal')
EXPECTED = {'ru.rustore.pay': '11.1.0', 'ru.rustore.core': '10.5.0'}
SUCCESS = 'PASS_NATIVE_RUSTORE_SDK86_CURRENT_API'


def tree(project):
    values = {}
    for category in ('Assets', 'Packages', 'ProjectSettings'):
        for path in sorted((project / category).rglob('*')):
            if path.is_file():
                values[path.relative_to(project).as_posix()] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    return values


def source_mapping():
    return [{'source': f'Unity/Assets/HeartOfTheRain/App/RuStore/Runtime/{name}.cs{extension}',
             'copied': f'Assets/Integration/{name}.cs{extension}',
             'sha256': sha(ROOT / f'Unity/Assets/HeartOfTheRain/App/RuStore/Runtime/{name}.cs{extension}')}
            for name in SOURCE_NAMES for extension in ('', '.meta')]


def guards(preparation):
    project = Path(preparation['project']).resolve()
    if (not re.fullmatch(r'[0-9a-f]{32}', preparation['runId']) or project.parent != CACHE.resolve()
            or project.name != 'P86_' + preparation['runId'][:8]):
        raise RuntimeError('IsolatedProjectPathInvalid')
    if (sha(LOCK) != preparation['sdkLockSHA256'] or pins() != preparation['packages']
            or sha(Path(__file__)) != preparation['toolSHA256']
            or sha(Path(__file__).with_name('run_native86.py')) != preparation['guardSHA256']):
        raise RuntimeError('PreparationToolOrOfficialPinsChanged')
    if source_mapping() != preparation['sources']:
        raise RuntimeError('CurrentMainAdapterChangedSincePreparation')
    for item in preparation['sources']:
        if sha(project / item['copied']) != item['sha256']:
            raise RuntimeError('CopiedMainSourceChanged')
    if sha(project / 'ProofInputs86.json') != preparation['proofInputsSHA256']:
        raise RuntimeError('ProofInputsChanged')
    if sha(project / 'Assets/Editor/RuStoreSdk86Verification.cs') != preparation['probeSHA256']:
        raise RuntimeError('ProbeChanged')
    return project


def pins():
    lock = json.loads(LOCK.read_text('utf-8-sig'))
    values = lock['packages']
    if {p['name']: p['version'] for p in values} != EXPECTED:
        raise RuntimeError('UnexpectedPackagePins')
    result = []
    for value in values:
        if value['vendorMetadataModified'] is not False or value['vendorUnityMinimum'] != '6000.0':
            raise RuntimeError('VendorMetadataPolicyChanged')
        path = ROOT / '.verification-cache/RuStore81/Vendor' / f"{value['name']}-{value['version']}.tgz"
        if sha(path) != value['sha256']:
            raise RuntimeError('OfficialCachedTarballFingerprintMismatch')
        result.append({key: value[key] for key in ('name', 'version', 'packageManifestSHA256', 'vendorUnityMinimum', 'sha256', 'tarballUrl')})
    return result


def prepare():
    if unity_pids():
        raise RuntimeError('ConcurrentUnityRefused')
    run_id = uuid.uuid4().hex
    CACHE.mkdir(parents=True, exist_ok=True)
    project = CACHE / ('P86_' + run_id[:8])
    project.mkdir(exist_ok=False)
    before = freeze()
    baseline = tree(BASELINE)
    for category in ('Assets', 'Packages', 'ProjectSettings'):
        shutil.copytree(BASELINE / category, project / category)
    manifest = json.loads((project / 'Packages/manifest.json').read_text('utf-8-sig'))
    package_lock = json.loads((project / 'Packages/packages-lock.json').read_text('utf-8-sig'))
    if any(manifest['dependencies'].get(name) != version or package_lock['dependencies'][name]['version'] != version for name, version in EXPECTED.items()):
        raise RuntimeError('StockPackageResolutionPinChanged')
    if '-define:HOTR_RUSTORE_PAY' not in (project / 'Assets/csc.rsp').read_text('utf-8-sig'):
        raise RuntimeError('ExplicitSdkCompileDefineRequired')
    if 'm_EditorVersion: 2022.3.62f3' not in (project / 'ProjectSettings/ProjectVersion.txt').read_text('utf-8-sig'):
        raise RuntimeError('PinnedEditorVersionRequired')
    sources = source_mapping()
    for source in sources:
        shutil.copy2(ROOT / source['source'], project / source['copied'])
    probe = Path(__file__).with_name('RuStoreSdk86Verification.cs')
    shutil.copy2(probe, project / 'Assets/Editor/RuStoreSdk86Verification.cs')
    (project / 'Assets/Editor/RuStoreSdk86Verification.cs.meta').write_text(
        'fileFormatVersion: 2\nguid: ' + uuid.uuid4().hex + '\nMonoImporter:\n  externalObjects: {}\n  serializedVersion: 2\n  defaultReferences: []\n  executionOrder: 0\n  icon: {instanceID: 0}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n', encoding='utf-8')
    packages = pins()
    write(project / 'ProofInputs86.json', {'runId': run_id, 'sources': sources, 'packages': packages})
    after = freeze()
    if not unchanged(delta(before, after)) or tree(BASELINE) != baseline:
        raise RuntimeError('PreparationChangedProtectedInputs')
    write(project / 'MainSources_preparation.json', before)
    write(project / 'CloneInputs_preparation.json', tree(project))
    write(project / 'BaselineInputs_preparation.json', baseline)
    preparation = {'schemaVersion': 1, 'runId': run_id, 'status': 'PREPARED_NOT_EXECUTED', 'utc': utc(),
        'project': str(project), 'baseline': str(BASELINE), 'sources': sources, 'packages': packages,
        'mainSourcesSHA256': sha(project / 'MainSources_preparation.json'), 'inputCount': before['inputCount'],
        'proofInputsSHA256': sha(project / 'ProofInputs86.json'), 'probeSHA256': sha(probe),
        'sdkLockSHA256': sha(LOCK), 'toolSHA256': sha(Path(__file__)),
        'guardSHA256': sha(Path(__file__).with_name('run_native86.py')),
        'scope': 'Isolated SDK Editor C# compile/API only. Four current source files+metas replace old fixture copies. Old81 inputs are copied read-only, never mutated. No SDK singleton, Android/build, game profile or payment activation.'}
    write(project / 'Preparation.json', preparation)
    print('Preparation: ' + str(project / 'Preparation.json'))
    return 0


def verify_packages(preparation, report, project):
    result = []
    packages = report.get('packages', [])
    if {p['name']: p['version'] for p in packages} != EXPECTED:
        raise RuntimeError('ResolvedSdkVersionMismatch')
    for pin in preparation['packages']:
        actual = next(p for p in packages if p['name'] == pin['name'])
        path = Path(actual['resolvedPath']).resolve()
        if not path.is_relative_to((project / 'Library/PackageCache').resolve()):
            raise RuntimeError('UnexpectedSdkResolvedPath')
        if actual['source'] != 'Registry' or actual['manifestSHA256'] != pin['packageManifestSHA256'] or actual['unity'] != '6000.0':
            raise RuntimeError('SdkVendorMetadataChanged')
        archive = ROOT / '.verification-cache/RuStore81/Vendor' / f"{pin['name']}-{pin['version']}.tgz"
        if sha(archive) != pin['sha256']:
            raise RuntimeError('CachedSdkTarballChanged')
        files = {}
        with tarfile.open(archive, 'r:gz') as package:
            for member in package:
                if not member.isfile():
                    continue
                relative = Path(member.name.removeprefix('package/'))
                if relative.is_absolute() or '..' in relative.parts:
                    raise RuntimeError('InvalidVendorArchivePath')
                expected = hashlib.sha256(package.extractfile(member).read()).hexdigest()
                actual_file = (path / relative).resolve()
                if not actual_file.is_relative_to(path) or not actual_file.is_file() or sha(actual_file) != expected:
                    raise RuntimeError('ResolvedSdkDiffersFromOfficialTarball')
                files[relative.as_posix()] = expected
        result.append({'name': pin['name'], 'version': pin['version'], 'tarballSHA256': pin['sha256'],
                       'resolvedPath': str(path), 'verifiedOfficialFiles': files, 'fileCount': len(files)})
    return result


def run(preparation_path, timeout):
    if os.name != 'nt':
        raise RuntimeError('WindowsNativeProcessContainmentRequired')
    preparation_path = preparation_path.resolve()
    preparation = json.loads(preparation_path.read_text('utf-8-sig'))
    project = guards(preparation)
    if preparation_path != project / 'Preparation.json' or unity_pids():
        raise RuntimeError('PreparedPathOrSerialUnityGuardFailed')
    before = freeze()
    frozen = json.loads((project / 'MainSources_preparation.json').read_text('utf-8-sig'))
    if sha(project / 'MainSources_preparation.json') != preparation['mainSourcesSHA256'] or not unchanged(delta(frozen, before)):
        raise RuntimeError('MainInputsChangedSincePreparation')
    run_folder = EVIDENCE / preparation['runId']
    run_folder.mkdir(parents=True, exist_ok=False)
    write(run_folder / 'Preparation.json', preparation)
    write(run_folder / 'Sources_before.json', before)
    write(run_folder / 'CloneInputs_before.json', tree(project))
    shutil.copy2(project / 'ProofInputs86.json', run_folder / 'ProofInputs86.json')
    record = {'status': 'RUNNING', 'runId': preparation['runId'], 'startedUtc': utc(), 'pid': None,
        'entry': 'RuStoreSdk86Verification.Run', 'project': str(project), 'timeoutSeconds': timeout,
        'timedOut': False, 'quitFlag': False, 'sdkInitialized': False, 'paymentCalls': False, 'androidBuild': False,
        'mainSourcesSHA256': sha(run_folder / 'Sources_before.json'), 'preparationSHA256': sha(preparation_path),
        'runnerSHA256': sha(Path(__file__)), 'serialGuardSHA256': sha(Path(__file__).with_name('run_native86.py')),
        'scope': preparation['scope']}
    log = run_folder / 'Unity.log';console = run_folder / 'Console.log';native_path = run_folder / 'Native/RuStoreSdk86.json'
    process = job = None; began = time.monotonic()
    try:
        if not PINNED_UNITY.is_file() or unity_pids():
            raise RuntimeError('PinnedEditorMissingOrConcurrentUnity')
        env = dict(os.environ);env['HOTR_REVIEW86_SDK_OUTPUT'] = str(run_folder)
        job = OwnedJob()
        with open(disk(console), 'x', encoding='utf-8') as output:
            process = subprocess.Popen([str(PINNED_UNITY), '-batchmode', '-projectPath', str(project),
                '-executeMethod', record['entry'], '-logFile', str(log)], env=env, stdout=output,
                stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            record['pid'] = process.pid;job.assign(process.pid);record['ownedKillOnCloseJobAssigned'] = True
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                record['timedOut'] = True;job.close();process.wait(timeout=20)
        record['exitCode'] = process.returncode
        report = json.loads(native_path.read_text('utf-8-sig')) if native_path.is_file() else {}
        record.update(nativeStatus=report.get('status', 'MISSING'), reportSHA256=sha(native_path) if native_path.is_file() else None)
        if process.returncode != 0 or record['timedOut'] or report.get('status') != SUCCESS or report.get('error'):
            raise RuntimeError('SdkCompileOrApiVerificationFailed')
        if report.get('runId') != preparation['runId'] or report.get('sources') != preparation['sources'] or report.get('inputManifestSHA256') != preparation['proofInputsSHA256']:
            raise RuntimeError('NativeReportInputBindingMismatch')
        if report.get('unity') != '2022.3.62f3' or report.get('sdkDefineEnabled') is not True or any(report.get(flag) is not False for flag in ('sdkInitialized', 'paymentCalls', 'androidBuild', 'gameSdkEnabled')):
            raise RuntimeError('NativeProofScopeMismatch')
        guards(preparation)
        write(run_folder / 'Packages_Official_Source.json', verify_packages(preparation, report, project))
        record.update(status='PASS_CURRENT_RUSTORE_SDK86_EDITOR_COMPILE', checks=report.get('checks'))
    except Exception as error:
        record.update(status='FAIL_CURRENT_RUSTORE_SDK86_EDITOR_COMPILE', errorType=type(error).__name__, errorCode=str(error) if isinstance(error, RuntimeError) else 'RunnerFailure')
    finally:
        if job:
            job.close()
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
        record.update(exitCode=process.poll() if process else None, processStopped=process is None or process.poll() is not None,
            finishedUtc=utc(), elapsedSeconds=round(time.monotonic()-began,3),
            unityLogSHA256=sha(log) if log.is_file() else None, consoleSHA256=sha(console) if console.is_file() else None)
        record.update(mainInputsUnchanged=False,old81InputsUnchanged=False,unityPidsAfter=None)
        try:
            after = freeze();write(run_folder / 'Sources_after.json', after)
            changes = delta(before, after);write(run_folder / 'Source_Delta.json', changes)
            record['mainInputsUnchanged'] = unchanged(changes) and unchanged(delta(frozen, after))
            baseline_before = json.loads((project / 'BaselineInputs_preparation.json').read_text('utf-8-sig'))
            record['old81InputsUnchanged'] = tree(BASELINE) == baseline_before
            write(run_folder / 'CloneInputs_after.json', tree(project))
            record['unityPidsAfter'] = unity_pids()
        except Exception as error:
            record['finalGuardErrorType'] = type(error).__name__
        if not record['mainInputsUnchanged'] or not record['old81InputsUnchanged'] or record['unityPidsAfter'] is None or record['unityPidsAfter']:
            record['status'] = 'FAIL_PROTECTED_INPUT_OR_PROCESS_GUARD'
        write(run_folder / 'Process.json', record)
    print('Process: ' + str(run_folder / 'Process.json'))
    return 0 if record['status'] == 'PASS_CURRENT_RUSTORE_SDK86_EDITOR_COMPILE' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('prepare')
    execute = sub.add_parser('run');execute.add_argument('--preparation', type=Path, required=True)
    execute.add_argument('--timeout-seconds', type=int, default=600)
    args = parser.parse_args()
    if args.command == 'prepare':
        return prepare()
    if not 60 <= args.timeout_seconds <= 900:
        parser.error('Bounded timeout60..900seconds required')
    # Same serial lock as the established85 runner; the corrected86 image-path
    # guard distinguishes the Hub service without ever stopping it.
    import msvcrt
    guard = ROOT / '.verification-cache/ShopAds85/NativeRunner.lock';guard.parent.mkdir(parents=True, exist_ok=True)
    with guard.open('a+b') as lock:
        if os.fstat(lock.fileno()).st_size == 0:lock.write(b'0');lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:return run(args.preparation,args.timeout_seconds)
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)


if __name__ == '__main__':
    raise SystemExit(main())
