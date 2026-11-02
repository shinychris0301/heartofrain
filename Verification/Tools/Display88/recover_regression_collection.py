"""Root-only read-only recovery of the already completed current88 regression.

Preserves the original failed host Invocation.json. No marker, input, install,
stop, launch, deletion or native rerun occurs. Unknown generated PNGs are kept
only in ignored cache with explicit freshness/acceptance exclusions. Other
unknown files are never pulled. Run only after the root finishes other device
operations: --phone Verification/Evidence/Display88/Phone/Device02
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('display88_completed_regression_collection', HERE / 'run_phone_checks.py')
checks = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checks
spec.loader.exec_module(checks)
sha, binding, write, utc = checks.sha, checks.binding, checks.write, checks.utc


def need(value, code):
    if not value:
        raise RuntimeError(code)


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


class DeclaredOutputReader:
    """Feed independently audited declared outputs to unchanged collection code.

    The complete remote inventory is retained separately. This adapter never
    represents unlisted files as current captures, and owns no mutation method.
    """
    def __init__(self, phone, remote, expected, all_public):
        self.phone, self.base, self.remote = phone, phone.base, remote
        self.expected, self.all_public = expected, all_public

    def adb(self, *args):
        if args == ('shell', 'find', self.remote, '-type', 'f'):
            return '\n'.join(self.remote + '/' + name for name in sorted(self.expected))
        if len(args) == 3 and args[:2] == ('pull', self.remote + '/.'):
            if self.all_public:
                return self.phone.adb(*args)
            for name in sorted(self.expected):
                self.phone.adb('pull', self.remote + '/' + name, Path(args[2]) / name)
            return 'Only explicitly declared native outputs pulled'
        raise RuntimeError('UnexpectedReadOnlyCollectionOperation')


def recover(phone):
    phone.assert_installed()
    phone.assert_no_active_attempt()
    folder = phone.out / 'Regression'
    original_path, latest_path = folder / 'Invocation.json', folder / 'Latest.json'
    original, latest = read(original_path), read(latest_path)
    need(original.get('status') == 'FAIL_PHYSICAL_TRANSIENT_REGRESSION88'
         and original.get('failureCategory') == 'UnexpectedNativeRegressionFilesPreserved', 'ExpectedOriginalCollectionFailureMissing')
    need(original.get('nativeStatus') == latest.get('status') == 'PASS_NATIVE_REGRESSION'
         and not latest.get('failures') and latest.get('boards') == 50 and latest.get('actions') == 408 and latest.get('clips') == 354,
         'CompletedNativeRegressionNotEstablished')
    need(original.get('ordinaryDataUnchanged') is True and original.get('ordinaryDataUnchangedAfterNormalRelaunch') is True,
         'OriginalOrdinarySavePreservationNotEstablished')
    need(original['runner'] == binding(HERE / 'run_phone_checks.py') and original['phoneHelper'] == binding(HERE / 'phone.py'), 'OriginalToolReceiptChanged')
    need(original['apk'] == binding(phone.apk) and original['target'] == binding(phone.out / 'Target.json'), 'OriginalCurrentApkOrTargetMismatch')
    current = checks.source_module.freeze()
    original_manifest = ROOT / original['sourceManifest']['path']
    need(binding(original_manifest) == original['sourceManifest'] and read(original_manifest) == current
         and original.get('inputsUnchanged') is True, 'OriginalSourceMapNotCurrent')
    need(checks.current_build(phone, current) == original['matchingBuild'], 'OriginalMatchingBuildChanged')
    need(not (folder / 'Native').exists() and not (folder / 'CaptureInventory.json').exists(), 'ExistingNativeCollectionPreserved')
    supplement = folder / 'Recollection'
    supplement.mkdir(parents=True, exist_ok=False)
    write(supplement / 'SourceManifest.json', current)
    before = phone.snapshot()
    record = {'checkpoint': 88, 'status': 'RUNNING', 'startedUtc': utc(),
              'runner': binding(Path(__file__)), 'collectionAlgorithm': binding(HERE / 'run_phone_checks.py'),
              'phoneHelper': binding(HERE / 'phone.py'), 'originalInvocation': binding(original_path), 'nativeSnapshot': binding(latest_path),
              'sourceManifest': binding(supplement / 'SourceManifest.json'), 'apk': binding(phone.apk),
              'target': binding(phone.out / 'Target.json'), 'matchingBuild': original['matchingBuild'], 'ordinaryBefore': before,
              'scope': 'Supplemental read-only collection of the exact already completed native regression. Original host collection FAIL remains unchanged. No native rerun, marker, input, install, stop, launch, deletion, human campaign or performance certification.'}
    write(supplement / 'Invocation.json', record)
    cache = ROOT / '.verification-cache/Display88' / phone.out.name / 'RegressionRecollection' / uuid.uuid4().hex
    remote = phone.base + '/Regression'
    try:
        raw_before = phone.adb('shell', 'cat', remote + '/Regression.json')
        need(json.loads(raw_before) == latest, 'RemoteCompletedRegressionChangedBeforeCollection')
        (supplement / 'Remote_Before.json').write_text(raw_before + '\n', encoding='utf-8')
        record['remoteBefore'] = binding(supplement / 'Remote_Before.json')
        names = latest.get('frames', [])
        need(names and len(names) <= 1000 and len(set(names)) == len(names)
             and all(re.fullmatch(r'[A-Za-z0-9_-]+\.png', name) for name in names), 'DeclaredCaptureInventoryInvalid')
        expected = set(names) | {'Regression.json', 'M70_Device.json'}
        paths = phone.adb('shell', 'find', remote, '-type', 'f').splitlines()
        need(len(paths) <= 1002 and all(path.startswith(remote + '/') for path in paths), 'RemoteOutputInventoryOutsideScope')
        relative = {path.removeprefix(remote + '/') for path in paths}
        need(expected <= relative, 'DeclaredNativeOutputMissing')
        unlisted = relative - expected
        safe_unlisted = sorted(name for name in unlisted if re.fullmatch(r'[A-Za-z0-9_-]+\.png', name))
        all_public = all(name in {'Regression.json', 'M70_Device.json'} or re.fullmatch(r'[A-Za-z0-9_-]+\.png', name) for name in relative)
        inventory = {'declaredFileCount': len(expected), 'remoteFileCount': len(paths), 'unlistedSafeGeneratedPngs': safe_unlisted,
                     'unlistedUnsafeCount': len(unlisted) - len(safe_unlisted), 'wholeDirectoryPullIntoIgnoredCache': all_public,
                     'scope': 'Only declared current captures and two public reports become acceptance evidence. Unlisted PNG names may be leftovers because the native output directory is not cleared. Their freshness is unestablished; unknown non-PNG files are excluded and never pulled.'}
        write(supplement / 'RemoteInventory.json', inventory)
        record['remoteInventory'] = binding(supplement / 'RemoteInventory.json')
        adapter = DeclaredOutputReader(phone, remote, expected, all_public)
        record['collection'] = checks.collect_regression(adapter, folder, latest, cache)
        unknown_rows = []
        for name in safe_unlisted:
            path = cache / name
            digest, size = (sha(path), path.stat().st_size) if path.is_file() else (None, None)
            if not path.is_file():
                # The targeted fallback does not download unknown PNGs, but
                # their app-local hashes/sizes remain read-only metadata.
                reply = phone.adb('shell', 'sha256sum', remote + '/' + name)
                match = re.fullmatch(r'([0-9a-fA-F]{64})[ \t]+[^\r\n]+', reply)
                byte_count = phone.adb('shell', 'stat', '-c', '%s', remote + '/' + name)
                need(match is not None and byte_count.isdigit(), 'UnlistedGeneratedPngMetadataUnavailable')
                digest, size = match.group(1).lower(), int(byte_count)
            unknown_rows.append({'file': name, 'sha256': digest, 'bytes': size,
                                 'localCache': path.relative_to(ROOT).as_posix() if path.is_file() else None,
                                 'retained': False, 'freshnessEstablished': False, 'acceptanceEvidence': False})
        write(supplement / 'UnlistedCaptureInventory.json', {'files': unknown_rows,
              'scope': 'Read-only metadata for unlisted generated PNGs, if pulled into ignored cache. These files are excluded from current native capture counts, public retained images and acceptance.'})
        record['unlistedCaptures'] = binding(supplement / 'UnlistedCaptureInventory.json')
        raw_after = phone.adb('shell', 'cat', remote + '/Regression.json')
        need(raw_after == raw_before and json.loads(raw_after) == latest, 'RemoteCompletedRegressionChangedDuringCollection')
        (supplement / 'Remote_After.json').write_text(raw_after + '\n', encoding='utf-8')
        record['remoteAfter'] = binding(supplement / 'Remote_After.json')
        record['status'] = 'PASS_PHYSICAL_REGRESSION88_READ_ONLY_RECOLLECTION'
    except Exception as error:
        record.update(status='FAIL_PHYSICAL_REGRESSION88_READ_ONLY_RECOLLECTION', failureType=type(error).__name__)
        if isinstance(error, RuntimeError) and re.fullmatch('[A-Za-z0-9]+', str(error)):
            record['failureCategory'] = str(error)
        record['localCacheIfCreated'] = cache.relative_to(ROOT).as_posix() if cache.exists() else None
    finally:
        checks.retain_partial_inventory(folder, cache)
        try:
            after = phone.snapshot()
            record.update(ordinaryAfter=after, ordinaryDataUnchanged=before == after)
            need(before == after, 'ReadOnlyCollectionOrdinaryDataChanged')
            phone.assert_installed()
        except Exception as error:
            record.update(status='FAIL_PHYSICAL_REGRESSION88_READ_ONLY_RECOLLECTION', preservationFailureType=type(error).__name__)
        after_source = checks.source_module.freeze()
        write(supplement / 'Sources_after.json', after_source)
        record.update(inputsUnchanged=current == after_source, runnerUnchanged=sha(Path(__file__)) == record['runner']['sha256'],
                      collectionAlgorithmUnchanged=sha(HERE / 'run_phone_checks.py') == record['collectionAlgorithm']['sha256'],
                      phoneHelperUnchanged=sha(HERE / 'phone.py') == record['phoneHelper']['sha256'],
                      originalInvocationUnchanged=sha(original_path) == record['originalInvocation']['sha256'], finishedUtc=utc())
        if not all(record[key] for key in ('inputsUnchanged', 'runnerUnchanged', 'collectionAlgorithmUnchanged', 'phoneHelperUnchanged', 'originalInvocationUnchanged')):
            record['status'] = 'FAIL_PHYSICAL_REGRESSION88_READ_ONLY_RECOLLECTION'
        write(supplement / 'Invocation.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phone', type=Path, required=True)
    args = parser.parse_args()
    result = recover(checks.CapturePathPhone(args.phone))
    print(json.dumps({'status': result['status'], 'recollection': str(args.phone / 'Regression/Recollection/Invocation.json')}), flush=True)
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
