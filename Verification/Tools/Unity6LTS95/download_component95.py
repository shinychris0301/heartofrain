"""Root-only fresh official LTS95 Android-component download; never installs.

Sixteen owned section files retain partial read1 bytes across bounded retries.
Only the complete publisher checksum AND Valid Unity signature permit PASS.
No Hub cache, existing partial file, installer, SDK or device is mutated.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.request

import official_download95 as dl
import smoke95

ROOT = Path(__file__).resolve().parents[3]
PRIVATE = ROOT / '.verification-cache/Unity6LTS95/ComponentDownloads'
PUBLIC = ROOT / 'Verification/Evidence/Unity6LTS95/ComponentDownloads'
BACKEND = ROOT / 'Verification/Evidence/Unity6LTS95/ProtectedBackend/Before/BackendInputs.json'
BACKEND_SHA = 'd533b762c093274ba123f00de612cafe18b9964222c6443346de3f3d3f5aecdf'
OFFICIAL_SHA = '0dcf067e2e92f6b6e8c51e36a4ebeea802e44997541bc2c86fcfb0601a9de0fb'
METADATA_SHA = '20b0336f3950a89aeafafb2b58dc173c0774aca91e7c91fac6cd1ff2fe32e63f'
ANDROID_MD5 = 'cfe45daf03586b1840752d62e0704b8b'
SECTION_COUNT = 16
ATTEMPTS = 16


def need(value, code):
    if not value:
        raise ValueError(code)


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def no_links(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.exists():
            need(not item.is_symlink() and not getattr(item.stat(), 'st_file_attributes', 0) & 0x400,
                 'Component95LinkedPathRefused')
    return path.resolve()


def fresh_paths(output):
    output = no_links(output)
    need(output.parent == no_links(PUBLIC) and re.fullmatch(r'[a-f0-9]{32}', output.name)
         and not output.exists(), 'Component95FreshPublicUUIDRequired')
    private = no_links(PRIVATE / output.name)
    need(private.parent == no_links(PRIVATE) and not private.exists(), 'Component95FreshPrivateUUIDRequired')
    return output, private


def component_info(component):
    need(component == 'android', 'Component95FreshAndroidOnly')
    need(dl.digest(Path(dl.__file__)) == OFFICIAL_SHA and dl.digest(dl.METADATA) == METADATA_SHA,
         'Component95FrozenOfficialReaderOrMetadataChanged')
    info = dl.component_info(component)
    need(info['component'] == 'android' and info['filename'] == 'UnitySetup-Android-Support-for-Editor-6000.3.27f1.exe'
         and info['bytes'] == 1549360256 and info['md5'] == ANDROID_MD5, 'Component95ExactAndroidInstallerRequired')
    dl.safe_url(info['url'])
    return info


def protected_sources():
    api, candidate, _, _, _ = smoke95.readers()
    main, current66 = smoke95.protected_sources(api, candidate)
    need(dl.digest(BACKEND) == BACKEND_SHA, 'Component95ProtectedBackendManifestChanged')
    record, files = dl.read(BACKEND), {}
    need(record['trackedFiles'] == len(record['files']) == 95, 'Component95ProtectedBackendCountChanged')
    for row in record['files']:
        relative = row['path']
        need(relative.startswith('Backend/') and '..' not in Path(relative).parts and relative not in files,
             'Component95ProtectedBackendPathInvalid')
        path = no_links(ROOT / relative)
        need(path.is_relative_to((ROOT / 'Backend').resolve()) and path.is_file(), 'Component95ProtectedBackendFileRequired')
        item = {'sha256': dl.digest(path), 'bytes': path.stat().st_size}
        need(item == {key: row[key] for key in ('sha256', 'bytes')}, 'Component95ProtectedBackendSourceChanged')
        files[relative] = item
    return {'main': main, 'candidate66': current66, 'backendTrackedSources': files}


def section_ranges(total):
    need(type(total) is int and total >= SECTION_COUNT, 'Component95PositiveSectionTotalRequired')
    width = (total + SECTION_COUNT - 1) // SECTION_COUNT
    result = [(index, start, min(total, start + width) - 1)
              for index, start in enumerate(range(0, total, width))]
    need(len(result) == SECTION_COUNT and result[0][1] == 0 and result[-1][2] == total - 1
         and sum(last - first + 1 for _, first, last in result) == total, 'Component95SixteenContiguousSectionsRequired')
    return result


def check_deadline(deadline, cancelled):
    need(not cancelled.is_set(), 'Component95OtherSectionFailed')
    need(time.monotonic() < deadline, 'Component95OverallDeadline')


def download_section(info, spec, private, deadline, cancelled):
    index, first, last = spec
    path = private / ('Part' + str(index).zfill(2) + '.bin')
    with path.open('xb'):
        pass
    opener = urllib.request.build_opener(dl.OfficialRedirect())
    for attempt in range(1, ATTEMPTS + 1):
        check_deadline(deadline, cancelled)
        received = path.stat().st_size
        need(0 <= received <= last - first + 1, 'Component95SectionSizeInvalid')
        if received == last - first + 1:
            break
        start = first + received
        try:
            request = urllib.request.Request(dl.safe_url(info['url']), headers={
                'Range': f'bytes={start}-{last}', 'Accept-Encoding': 'identity',
                'User-Agent': 'HeartRain-OfficialAndroidComponent95/1.0'})
            with opener.open(request, timeout=min(30, deadline - time.monotonic())) as response:
                dl.safe_url(response.geturl())
                dl.validate_range(response.status, response.headers, start, last, info['bytes'])
                remaining = last - start + 1
                with path.open('ab') as stream:
                    while remaining:
                        check_deadline(deadline, cancelled)
                        block = response.read1(min(65536, remaining))
                        if not block:
                            raise EOFError('Component95InterruptedSection')
                        need(len(block) <= remaining, 'Component95ExcessSectionBytes')
                        stream.write(block)
                        remaining -= len(block)
                    stream.flush()
                check_deadline(deadline, cancelled)
                need(not response.read1(1), 'Component95ExcessResponseBytes')
            break
        except (OSError, urllib.error.URLError, EOFError):
            if attempt == ATTEMPTS:
                raise RuntimeError('Component95SectionRetriesExhausted') from None
            check_deadline(deadline, cancelled)
            cancelled.wait(min(3, attempt, max(0, deadline - time.monotonic())))
    check_deadline(deadline, cancelled)
    need(path.stat().st_size == last - first + 1, 'Component95SectionIncomplete')
    if first == 0:
        with path.open('rb') as stream:
            need(stream.read(2) == b'MZ', 'Component95InvalidPEPrefix')
    return {'index': index, 'first': first, 'last': last, 'bytes': path.stat().st_size,
            'sha256': dl.digest(path, deadline=deadline), 'attempts': attempt}


def assemble(info, specs, parts, private, deadline):
    need(len(parts) == len(specs) == SECTION_COUNT, 'Component95AllSixteenPartsRequired')
    ordered = sorted(parts, key=lambda item: item['index'])
    target = private / info['filename']
    with target.open('xb') as destination:
        for spec, part in zip(specs, ordered):
            index, first, last = spec
            need((part['index'], part['first'], part['last'], part['bytes']) == (index, first, last, last - first + 1)
                 and destination.tell() == first, 'Component95OrderedAssemblyBoundaryMismatch')
            path = no_links(private / ('Part' + str(index).zfill(2) + '.bin'))
            need(path.stat().st_size == part['bytes'] and dl.digest(path, deadline=deadline) == part['sha256'],
                 'Component95PartChangedBeforeAssembly')
            with path.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    need(time.monotonic() < deadline, 'Component95OverallDeadline')
                    destination.write(block)
            need(destination.tell() == last + 1, 'Component95AssemblyLengthMismatch')
    need(target.stat().st_size == info['bytes'], 'Component95AssembledSizeMismatch')
    return target


def download(component, output, seconds=5400):
    need(type(seconds) is int and 60 <= seconds <= 5400, 'Component95BoundedSecondsRequired')
    info = component_info(component)
    output, private = fresh_paths(output)
    before = protected_sources()  # Full selected source maps, before any HTTP.
    output.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    write(output / 'Sources_before.json', before)
    started, cancelled = time.monotonic(), threading.Event()
    deadline = started + seconds
    report = {'schemaVersion': 2, 'status': 'RUNNING_FRESH_OFFICIAL_ANDROID_SECTIONS95', 'component': component,
              'startedUtc': dl.utc_now(), 'helperSHA256': dl.digest(__file__), 'officialHelperSHA256': OFFICIAL_SHA,
              'metadataSHA256': METADATA_SHA, 'url': info['url'], 'maxSeconds': seconds, 'sectionCount': SECTION_COUNT,
              'maxAttemptsPerSection': ATTEMPTS, 'parts': [], 'trustedInstaller': False, 'installerExecuted': False,
              'scope': 'Fresh independent official Android installer bytes only. Main/candidate66 source maps and95 tracked backend sources are read-only. No existing partial, Hub cache, installer, SDK, device or security setting is mutated.'}
    write(output / 'Authorization.json', report)
    try:
        specs = section_ranges(info['bytes'])
        with ThreadPoolExecutor(max_workers=SECTION_COUNT) as pool:
            futures = [pool.submit(download_section, info, spec, private, deadline, cancelled) for spec in specs]
            try:
                for future in as_completed(futures, timeout=max(0, deadline - time.monotonic())):
                    part = future.result()
                    report['parts'].append(part)
                    print(json.dumps({'component': component, 'sectionCompleted': part['index'],
                                      'bytes': part['bytes'], 'attempts': part['attempts']}), flush=True)
            except Exception:
                cancelled.set()
                for future in futures:
                    future.cancel()
                raise
        report['parts'].sort(key=lambda item: item['index'])
        target = assemble(info, specs, report['parts'], private, deadline)
        verified = dl.verified_file(target, info, deadline=deadline)
        report.update(status='PASS_COMPLETE_OFFICIAL_INSTALLER95', trustedInstaller=True, installer=verified,
                      normalInstallPlan={'executable': str(target), 'arguments': ['/S', '/D=' + str(dl.TARGET)],
                          'note': 'Ordinary stock installer only; /D is last. Not executed by this tool.'})
    except Exception as error:
        report.update(status='FAIL_FRESH_OFFICIAL_ANDROID_SECTIONS95', errorType=type(error).__name__)
    finally:
        try:
            after = protected_sources()
            write(output / 'Sources_after.json', after)
            need(before == after, 'Component95ProtectedSourcesChangedDuringDownload')
            need(component_info(component) == info and dl.digest(__file__) == report['helperSHA256'],
                 'Component95ReaderChangedDuringDownload')
            report['protectedSourcesUnchanged'] = True
        except Exception as error:
            report.update(status='FAIL_FRESH_OFFICIAL_ANDROID_SECTIONS95_INVARIANT', invariantErrorType=type(error).__name__)
        if report['status'] != 'PASS_COMPLETE_OFFICIAL_INSTALLER95':
            report['trustedInstaller'] = False
            report.pop('normalInstallPlan', None)
        report['retainedSections'] = [{'index': i, 'bytes': (private / ('Part' + str(i).zfill(2) + '.bin')).stat().st_size}
                                      for i in range(SECTION_COUNT) if (private / ('Part' + str(i).zfill(2) + '.bin')).is_file()]
        dl.finish(report, started)
        write(output / 'Report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--component', choices=('android',), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--max-seconds', type=int, default=5400)
    args = parser.parse_args()
    if not args.execute or os.name != 'nt' or not args.out.is_absolute():
        parser.error('Explicit root Windows execution and absolute fresh public UUID output required')
    report = download(args.component, args.out, args.max_seconds)
    print(json.dumps({'status': report['status'], 'component': report['component'],
                      'trustedInstaller': report['trustedInstaller'], 'installerExecuted': False}), flush=True)
    return 0 if report['status'] == 'PASS_COMPLETE_OFFICIAL_INSTALLER95' else 1


if __name__ == '__main__':
    raise SystemExit(main())
