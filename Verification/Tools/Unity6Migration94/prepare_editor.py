"""Prepare a fresh, private Unity 6 Editor copy for root-controlled module setup.

No Unity/Hub/installer processes are launched. No Hub preferences, identity stores,
licensing data, main project files, or existing destination files are modified.
The separate official CLI must select this portable directory explicitly.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[3]
VERSION = '6000.6.6f1'
REVISION = 'd20c9ac777da'
SOURCE = Path('C:/Program Files/Unity/Hub/Editor') / VERSION
# Root-approved short portable location. The first deep-cache attempt retained
# a FAIL receipt after Windows rejected a long bundled WebGL/npm directory.
# Keep that partial directory untouched; never overlay or resume either target.
CACHE = Path('E:/HeartRainUnity6_94')
EDITOR_BASE = CACHE
DESTINATION = EDITOR_BASE / VERSION
EVIDENCE = ROOT / 'Verification/Evidence/Unity6Migration94/Environment/PortableEditor'
RELEASE_URL = ('https://services.api.unity.com/unity/editor/release/v1/releases'
               '?version=6000.6.6f1&architecture=X86_64&platform=WINDOWS')
EXPECTED_MODULES = {
    'android', 'android-open-jdk-17.0.18+8', 'android-sdk-ndk-tools',
    'android-ndk-r27c', 'cmake-3.22.1', 'android-sdk-build-tools-36.0.0',
    'android-sdk-platform-tools-37.0.1', 'android-sdk-platforms-34',
    'android-sdk-platforms-36', 'android-sdk-platforms-37.0',
    'android-sdk-command-line-tools-16.0',
}


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def is_linklike(path):
    entry = Path(path).lstat()
    return (stat.S_ISLNK(entry.st_mode) or
            bool(getattr(entry, 'st_file_attributes', 0) & 0x400))


def reject_links_to_root(path):
    current = Path(os.path.abspath(path))
    while True:
        if current.exists() or current.is_symlink():
            if is_linklike(current):
                raise ValueError('Junction, symlink, or reparse point refused: ' + str(current))
        if current.parent == current:
            break
        current = current.parent


def bounded(path, parent):
    """Reject lexical escapes and existing link ancestors before resolving paths."""
    candidate = Path(os.path.abspath(path))
    boundary = Path(os.path.abspath(parent))
    if candidate == boundary or not candidate.is_relative_to(boundary):
        raise ValueError('Expected a strict descendant of the intended directory')
    reject_links_to_root(candidate)
    if not candidate.resolve().is_relative_to(boundary.resolve()):
        raise ValueError('Resolved path escapes the intended directory')
    return candidate


def walk_tree(root):
    root = Path(root)
    reject_links_to_root(root)
    if not root.is_dir():
        raise ValueError('Source Editor directory is absent')
    files, directories = [], []
    for parent, names, filenames in os.walk(root, followlinks=False):
        names.sort()
        filenames.sort()
        for name in names:
            child = Path(parent) / name
            if is_linklike(child):
                raise ValueError('Source directory contains a link/reparse point: ' + str(child))
            directories.append(child.relative_to(root).as_posix())
        for name in filenames:
            child = Path(parent) / name
            if is_linklike(child) or not stat.S_ISREG(child.lstat().st_mode):
                raise ValueError('Source contains a nonregular or linked file: ' + str(child))
            files.append((child.relative_to(root).as_posix(), child.stat().st_size))
    return sorted(files), sorted(directories)


def flatten_modules(module):
    yield module
    for child in module.get('subModules', []):
        yield from flatten_modules(child)


def select_release(document):
    results = document.get('results', [])
    if len(results) != 1:
        raise ValueError('Expected exactly one official release result')
    release = results[0]
    if release.get('version') != VERSION or release.get('shortRevision') != REVISION:
        raise ValueError('Official release version/changeset mismatch')
    downloads = [item for item in release.get('downloads', [])
                 if item.get('platform') == 'WINDOWS' and item.get('architecture') == 'X86_64']
    if len(downloads) != 1:
        raise ValueError('Expected exactly one Windows x86_64 Editor download')
    android = [item for item in downloads[0].get('modules', []) if item.get('id') == 'android']
    if len(android) != 1:
        raise ValueError('Official Android module is absent or ambiguous')
    modules = list(flatten_modules(android[0]))
    if len(modules) != len(EXPECTED_MODULES) or {item['id'] for item in modules} != EXPECTED_MODULES:
        raise ValueError('Official module tree changed; review it before installation')
    for module in modules:
        url = urllib.parse.urlsplit(module['url'])
        if (url.scheme != 'https' or url.hostname not in {'download.unity3d.com', 'dl.google.com'}
                or url.username or url.password or url.fragment):
            raise ValueError('Unexpected official module URL')
        for size in ('downloadSize', 'installedSize'):
            value = module[size]
            if value.get('unit') != 'BYTE' or not isinstance(value.get('value'), int) or value['value'] < 0:
                raise ValueError('Unexpected size metadata')
    return release, android[0], modules


def fetch_release():
    request = urllib.request.Request(RELEASE_URL, headers={'User-Agent': 'HOTR-Unity6Migration94'})
    with urllib.request.urlopen(request, timeout=45) as response:
        parsed = urllib.parse.urlsplit(response.url)
        if parsed.scheme != 'https' or parsed.hostname != 'services.api.unity.com':
            raise ValueError('Unexpected release metadata redirect')
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Release metadata exceeds the bounded input limit')
    document = json.loads(raw)
    return raw, select_release(document)


def copy_fresh(source, destination, expected_files, expected_directories):
    """Copy regular files without hardlinks, overlays, moves, or deletion."""
    source, destination = Path(source), Path(destination)
    reject_links_to_root(source)
    reject_links_to_root(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination must be fresh; existing contents are never overlaid')
    destination.mkdir(parents=True, exist_ok=False)
    for relative in expected_directories:
        target = bounded(destination / relative, destination)
        target.mkdir(exist_ok=False)
    records = []
    for index, (relative, expected_size) in enumerate(expected_files, 1):
        origin = bounded(source / relative, source)
        target = bounded(destination / relative, destination)
        before = origin.stat()
        if before.st_size != expected_size or is_linklike(origin):
            raise ValueError('Source changed before copy: ' + relative)
        hasher = hashlib.sha256()
        total = 0
        with origin.open('rb') as reader, target.open('xb') as writer:
            for block in iter(lambda: reader.read(4 * 1024 * 1024), b''):
                writer.write(block)
                hasher.update(block)
                total += len(block)
        after = origin.stat()
        if (total != expected_size or after.st_size != before.st_size or
                after.st_mtime_ns != before.st_mtime_ns or is_linklike(origin)):
            raise ValueError('Source changed during copy: ' + relative)
        copied_digest = digest(target)
        if copied_digest != hasher.hexdigest():
            raise ValueError('Copied bytes failed verification: ' + relative)
        shutil.copystat(origin, target, follow_symlinks=False)
        records.append({'path': relative, 'bytes': total, 'sha256': copied_digest})
        if index % 250 == 0:
            print(json.dumps({'stage': 'COPY_VERIFY_EDITOR', 'files': index,
                              'totalFiles': len(expected_files)}), flush=True)
    if walk_tree(source) != (expected_files, expected_directories):
        raise ValueError('Source Editor inventory changed during the copy')
    if walk_tree(destination) != (expected_files, expected_directories):
        raise ValueError('Destination Editor inventory differs')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true',
                        help='Create the fresh private copy and public metadata receipts')
    args = parser.parse_args()
    bounded(DESTINATION, CACHE)
    reject_links_to_root(SOURCE)
    files, directories = walk_tree(SOURCE)
    required = {'Editor/Unity.exe', 'modules.json', 'metadata.hub.json'}
    if not required.issubset({relative for relative, _ in files}):
        parser.error('Existing Editor executable and Hub metadata files are required')
    if DESTINATION.exists():
        parser.error('Portable Editor already exists; use its receipt or choose a separately reviewed location')
    if not args.execute:
        print(json.dumps({'status': 'INSPECT_ONLY_NO_COPY_OR_NETWORK', 'version': VERSION,
                          'source': str(SOURCE), 'destination': str(DESTINATION),
                          'files': len(files), 'bytes': sum(size for _, size in files),
                          'note': 'Root must use --execute explicitly. No process is launched.'}))
        return 0
    output = bounded(EVIDENCE / uuid.uuid4().hex, ROOT / 'Verification/Evidence/Unity6Migration94')
    output.mkdir(parents=True, exist_ok=False)
    record = {'schemaVersion': 1, 'status': 'PREPARING_PRIVATE_EDITOR94', 'startedUtc': utc(),
              'runnerSHA256': digest(__file__), 'version': VERSION, 'changeset': REVISION,
              'source': str(SOURCE), 'destination': str(DESTINATION),
              'portableCLIBaseDirectory': str(EDITOR_BASE), 'hubPreferencesChanged': False,
              'shortPortablePathReason': 'Avoid Windows WinError 206 in bundled WebGL/npm paths. The earlier deep-cache partial directory and FAIL receipt are retained unchanged.',
              'credentialsCopied': False, 'processesLaunched': False,
              'scope': 'Verified byte copy of the installed Editor distribution and exact official Android module metadata. No modules are downloaded or installed and no project is migrated by this helper.'}
    try:
        raw, (release, android, modules) = fetch_release()
        (output / 'ReleaseAPI.json').write_bytes(raw)
        write_new(output / 'AndroidModules.json', {'version': VERSION, 'changeset': REVISION,
                  'releaseAPI': RELEASE_URL, 'releaseAPISHA256': hashlib.sha256(raw).hexdigest(),
                  'releaseDate': release.get('releaseDate'), 'android': android,
                  'downloadBytes': sum(item['downloadSize']['value'] for item in modules),
                  'installedBytes': sum(item['installedSize']['value'] for item in modules),
                  'moduleIds': [item['id'] for item in modules],
                  'missingIntegrityIds': [item['id'] for item in modules if not item.get('integrity')]})
        needed = sum(size for _, size in files) + sum(item['installedSize']['value'] for item in modules)
        free = shutil.disk_usage(ROOT.anchor).free
        if free < needed + 5 * 1024 ** 3:
            raise ValueError('Insufficient disk space for Editor, Android modules, and a 5 GiB reserve')
        copied = copy_fresh(SOURCE, DESTINATION, files, directories)
        write_new(output / 'Inventory.json', {'schemaVersion': 1, 'files': copied,
                                            'directories': directories})
        record.update(status='PASS_PRIVATE_EDITOR_COPY94_MODULES_NOT_INSTALLED',
                      files=len(copied), bytes=sum(item['bytes'] for item in copied),
                      sourceAndCopyContentEqual=True, sourceInventoryUnchanged=True,
                      distributionMetadataSHA256={name: digest(DESTINATION / name)
                          for name in ('modules.json', 'metadata.hub.json', 'Editor/Unity.exe')},
                      inventorySHA256=digest(output / 'Inventory.json'),
                      releaseAPISHA256=digest(output / 'ReleaseAPI.json'),
                      androidModulesSHA256=digest(output / 'AndroidModules.json'))
    except Exception as error:
        record.update(status='FAIL_PRIVATE_EDITOR_PREPARATION94', errorType=type(error).__name__,
                      error=str(error), partialCopyRetained=True)
        raise
    finally:
        record['finishedUtc'] = utc()
        write_new(output / 'Preparation.json', record)
        print(json.dumps({'status': record['status'], 'receipt': str(output / 'Preparation.json'),
                          'destination': str(DESTINATION)}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
