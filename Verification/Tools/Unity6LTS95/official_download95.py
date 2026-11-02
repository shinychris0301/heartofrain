"""Root-only independent official installers; never write Hub cache or execute installers.

Prepare only after the recorded CLI PID has ended. Copy its one installer into a
fresh private output. Download resumes that independent copy with strict ranges;
only a complete publisher-MD5 and Windows signature PASS produces an install plan.
"""
import argparse
import base64
import ctypes
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[3]
PRIVATE = ROOT / '.verification-cache/Unity6LTS95/OfficialDownloads'
PUBLIC = ROOT / 'Verification/Evidence/Unity6LTS95/OfficialDownloads'
METADATA = ROOT / 'Verification/Evidence/Unity6LTS95/Research/SDKComparisonSet01/Release_6000.3.27f1.json'
TARGET = Path('E:/HeartRainUnity6LTS95/6000.3.27f1')
VERSION = '6000.3.27f1'
REVISION = '672d562a42a7'
CHUNK = 8 * 1024 * 1024
PREFIX = 1024 * 1024
EXPECTED = {
    'editor': ('UnitySetup64-6000.3.27f1.exe', 4235893440, 'e5QStPCXCBTa8atkaZRINg==', 'Windows64EditorInstaller'),
    'android': ('UnitySetup-Android-Support-for-Editor-6000.3.27f1.exe', 1549360256, 'z+RdrwNYaxhAdS1i4HBLiw==', 'TargetSupportInstaller'),
}


def need(value, code):
    if not value:
        raise ValueError(code)


def digest(path, kind='sha256', deadline=None):
    value = hashlib.new(kind)
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            if deadline is not None:
                need(time.monotonic() < deadline, 'Download95OverallDeadline')
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def finish(report, started):
    report['finishedUtc'] = utc_now()
    report['elapsedSeconds'] = round(time.monotonic() - started, 6)


def no_links(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.exists():
            need(not item.is_symlink() and not getattr(item, 'is_junction', lambda: False)(), 'Download95LinkRefused')
    return path


def contained(path, base):
    path = no_links(path).resolve()
    base = no_links(base).resolve()
    need(path != base and path.is_relative_to(base), 'Download95OutputBoundary')
    return path


def component_info(component):
    record = read(METADATA)
    need(record['version'] == VERSION and record['revision'] == REVISION, 'Download95ReleaseChanged')
    item = record[component]
    name, size, md5, directory = EXPECTED[component]
    url = f'https://download.unity3d.com/download_unity/{REVISION}/{directory}/{name}'
    need(item['url'] == url and item['downloadSize'] == {'value': size, 'unit': 'BYTE'}
         and item['integrity'] == 'md5-' + md5, 'Download95OfficialMetadataChanged')
    return {'component': component, 'filename': name, 'bytes': size, 'url': url,
            'md5': base64.b64decode(md5, validate=True).hex()}


def stopped_pid(pid):
    need(os.name == 'nt' and isinstance(pid, int) and pid > 0, 'Download95WindowsStoppedPIDRequired')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE, no mutation.
    if not handle:
        need(ctypes.get_last_error() == 87, 'Download95CannotProveCLIStopped')
        return
    try:
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        need(kernel.WaitForSingleObject(handle, 0) == 0, 'Download95CLIStillRunning')
    finally:
        kernel.CloseHandle(handle)


def partial_source(path):
    cache = no_links(Path(os.environ['APPDATA']) / 'UnityHub/downloads').resolve()
    path = no_links(path).resolve()
    need(path.is_file() and path.is_relative_to(cache) and path.name == EXPECTED['editor'][0]
         and 2 <= len(path.relative_to(cache).parts) <= 4, 'Download95ExactHubInstallerOnly')
    need(PREFIX <= path.stat().st_size <= EXPECTED['editor'][1], 'Download95PartialSizeInvalid')
    return path


def stable_copy(source, target):
    before = source.stat()
    source_md5 = digest(source, 'md5')
    with source.open('rb') as handle:
        prefix_sha = hashlib.sha256(handle.read(PREFIX)).hexdigest()
    with source.open('rb') as src, target.open('xb') as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
    after = source.stat()
    need((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Download95SourceStillChanging')
    need(target.stat().st_size == before.st_size and digest(target, 'md5') == source_md5, 'Download95PartialCopyMismatch')
    with target.open('rb') as handle:
        prefix = handle.read(PREFIX)
    need(prefix.startswith(b'MZ') and hashlib.sha256(prefix).hexdigest() == prefix_sha, 'Download95PartialPrefixMismatch')
    return {'bytes': before.st_size, 'sourceMTimeNS': before.st_mtime_ns, 'partialMD5': source_md5,
            'prefixBytes': PREFIX, 'prefixSHA256': prefix_sha, 'trustedInstaller': False}


def prepare(partial, pid, out, public_out):
    started = time.monotonic()
    out = contained(out, PRIVATE)
    public_out = contained(public_out, PUBLIC)
    need(not out.exists() and not public_out.exists(), 'Download95FreshPreparationRequired')
    out.mkdir(parents=True, exist_ok=False)
    public_out.mkdir(parents=True, exist_ok=False)
    report = {'schemaVersion': 2, 'status': 'PREPARING_UNTRUSTED_INDEPENDENT_COPY95', 'startedUtc': utc_now(),
              'helperSHA256': digest(__file__), 'metadataSHA256': digest(METADATA), 'recordedCLIPID': pid,
              'trustedInstaller': False, 'installerExecuted': False,
              'scope': 'Only one stopped task installer read/copied; no Hub cache write, installation, registry or security change.'}
    try:
        stopped_pid(pid)
        source = partial_source(partial)
        info = {key: component_info(key) for key in EXPECTED}
        report['components'] = info
        for key in EXPECTED:
            (out / key).mkdir()
        report['partialCopy'] = stable_copy(source, out / 'editor' / info['editor']['filename'])
        stopped_pid(pid)
        report['status'] = 'PREPARED_UNTRUSTED_INDEPENDENT_COPY95'
        report['privateOriginalPath'] = str(source)
    except Exception as error:
        report.update(status='FAIL_PREPARATION95', error=str(error))
        raise
    finally:
        finish(report, started)
        write(out / 'Preparation.json', report)
        public_report = {key: value for key, value in report.items() if key != 'privateOriginalPath'}
        public_report['privatePreparationSHA256'] = digest(out / 'Preparation.json')
        write(public_out / 'Report.json', public_report)
    return out / 'Preparation.json'


def safe_url(url):
    value = urllib.parse.urlsplit(url)
    need(value.scheme == 'https' and value.hostname == 'download.unity3d.com'
         and value.port in (None, 443) and not value.username and not value.password
         and not value.query and not value.fragment, 'Download95OfficialHTTPSOnly')
    return url


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_range(status, headers, start, end, total):
    need(status == 206, 'Download95HTTP206Required')
    need(headers.get('Content-Encoding', 'identity').lower() == 'identity', 'Download95EncodedResponseRefused')
    need(headers.get('Content-Range') == f'bytes {start}-{end}/{total}', 'Download95ContentRangeMismatch')
    need(headers.get('Content-Length') == str(end - start + 1), 'Download95ContentLengthMismatch')


def range_bytes(opener, url, start, end, total, deadline):
    need(time.monotonic() < deadline, 'Download95OverallDeadline')
    request = urllib.request.Request(safe_url(url), headers={
        'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity', 'User-Agent': 'HeartRain-OfficialInstaller95/1.0'})
    with opener.open(request, timeout=min(30, max(1, deadline - time.monotonic()))) as response:
        safe_url(response.geturl())
        validate_range(response.status, response.headers, start, end, total)
        block = bytearray(end - start + 1)
        position = 0
        while position < len(block):
            need(time.monotonic() < deadline, 'Download95OverallDeadline')
            count = response.readinto(memoryview(block)[position:position + 1024 * 1024])
            need(count, 'Download95TruncatedRange')
            position += count
        need(not response.read(1), 'Download95ExcessRangeBytes')
    return block


def fetch_range(info, start, end, deadline):
    opener = urllib.request.build_opener(OfficialRedirect())
    for retry in range(3):
        try:
            return range_bytes(opener, info['url'], start, end, info['bytes'], deadline)
        except (OSError, urllib.error.URLError) as error:
            if retry == 2 or time.monotonic() + 2 ** retry >= deadline:
                raise RuntimeError('Download95BoundedTransferFailure:' + type(error).__name__) from error
            time.sleep(2 ** retry)


def ordered_batch(info, start, workers, deadline, fetch=fetch_range):
    need(workers in (1, 4), 'Download95WorkersMustBeOneOrFour')
    ranges = [(offset, min(info['bytes'], offset + CHUNK) - 1)
              for offset in range(start, min(info['bytes'], start + workers * CHUNK), CHUNK)]
    need(ranges, 'Download95EmptyRangeBatch')
    # Each response owns one <=8MiB bytearray. No append occurs until every
    # range of this <=32MiB payload batch is validated in its original order.
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch, info, first, last, deadline) for first, last in ranges]
        result = []
        try:
            for (first, last), future in zip(ranges, futures):
                remaining = deadline - time.monotonic()
                need(remaining > 0, 'Download95OverallDeadline')
                block = future.result(timeout=remaining)
                need(len(block) == last - first + 1, 'Download95BatchLengthMismatch')
                result.append((first, block))
        except Exception:
            for future in futures:
                future.cancel()
            raise
    return result


def authenticode(path, deadline=None):
    need(os.name == 'nt', 'Download95WindowsSignatureRequired')
    literal = str(Path(path).resolve()).replace("'", "''")
    script = ("$ErrorActionPreference='Stop'; $s=Get-AuthenticodeSignature -LiteralPath '" + literal
              + "'; [pscustomobject]@{Status=[string]$s.Status; SignerSubject=[string]$s.SignerCertificate.Subject} | ConvertTo-Json -Compress")
    encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    remaining = 120 if deadline is None else min(120, deadline - time.monotonic())
    need(remaining > 0, 'Download95OverallDeadline')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                            capture_output=True, text=True, timeout=remaining, check=False,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    need(result.returncode == 0, 'Download95SignatureObserverFailed')
    value = json.loads(result.stdout)
    need(value.get('Status') == 'Valid' and re.search(r'Unity Technologies', value.get('SignerSubject', ''), re.I),
         'Download95PublisherSignatureInvalid')
    return value


def verified_file(path, info, signature=None, deadline=None):
    need(path.stat().st_size == info['bytes'], 'Download95InstallerIncomplete')
    need(digest(path, 'md5', deadline) == info['md5'], 'Download95FullPublisherMD5Mismatch')
    result = authenticode(path, deadline) if signature is None else signature(path)
    return {'filename': path.name, 'bytes': path.stat().st_size, 'md5': info['md5'],
            'sha256': digest(path, deadline=deadline), 'authenticode': result}


def download(prepared, component, seconds, public_out, workers=1):
    started = time.monotonic()
    out = contained(public_out, PUBLIC)
    need(not out.exists(), 'Download95FreshEvidenceRequired')
    out.mkdir(parents=True, exist_ok=False)
    report = {'schemaVersion': 2, 'status': 'RUNNING_UNTRUSTED_INDEPENDENT_DOWNLOAD95', 'component': component,
              'startedUtc': utc_now(), 'helperSHA256': digest(__file__), 'maxSeconds': seconds,
              'workers': workers, 'maxPayloadBytes': workers * CHUNK,
              'trustedInstaller': False, 'installerExecuted': False,
              'scope': 'Independent copied/downloaded file only. Original Hub cache preserved. No installer executed.'}
    try:
        need(workers in (1, 4), 'Download95WorkersMustBeOneOrFour')
        return _download(prepared, component, seconds, out, started, report, workers)
    except Exception as error:
        report.update(status='FAIL_INDEPENDENT_DOWNLOAD95', error=str(error))
        raise
    finally:
        if 'finishedUtc' not in report:
            finish(report, started)
        write(out / 'Report.json', report)


def _download(prepared, component, seconds, out, started, report, workers):
    prepared = contained(prepared, PRIVATE)
    need(prepared.name == 'Preparation.json' and prepared.is_file(), 'Download95PreparationRequired')
    record = read(prepared)
    need(record['status'] == 'PREPARED_UNTRUSTED_INDEPENDENT_COPY95'
         and record['helperSHA256'] == digest(__file__) and record['metadataSHA256'] == digest(METADATA), 'Download95PreparationBindingChanged')
    stopped_pid(record['recordedCLIPID'])
    need(60 <= seconds <= 5400, 'Download95BoundedSecondsRequired')
    info = component_info(component)
    need(info == record['components'][component], 'Download95ComponentChanged')
    target = contained(prepared.parent / component / info['filename'], prepared.parent)
    attempt = prepared.parent / ('Attempt_' + uuid.uuid4().hex)
    attempt.mkdir()
    report.update(preparationSHA256=digest(prepared), metadataSHA256=digest(METADATA), url=info['url'])
    write(out / 'Report.json', report)
    deadline = started + seconds
    try:
        if not target.exists():
            with target.open('xb'):
                pass
        need(target.stat().st_size <= info['bytes'], 'Download95OversizedPartial')
        if component == 'editor':
            with target.open('rb') as handle:
                need(hashlib.sha256(handle.read(PREFIX)).hexdigest() == record['partialCopy']['prefixSHA256'], 'Download95CopiedPrefixChanged')
        with target.open('ab') as handle:
            while handle.tell() < info['bytes']:
                start = handle.tell()
                batch = ordered_batch(info, start, workers, deadline)
                for first, block in batch:
                    need(first == handle.tell(), 'Download95NonContiguousAppendRefused')
                    need(time.monotonic() < deadline, 'Download95OverallDeadline')
                    handle.write(block)
                handle.flush()
                os.fsync(handle.fileno())
                write(attempt / 'Progress.json', {'bytes': handle.tell(), 'total': info['bytes'], 'trustedInstaller': False})
                print(json.dumps({'component': component, 'bytes': handle.tell(), 'total': info['bytes']}), flush=True)
                del batch, block  # Release this batch before allocating the next <=32MiB payload.
        proof = verified_file(target, info, deadline=deadline)
        report.update(status='PASS_COMPLETE_OFFICIAL_INSTALLER95', trustedInstaller=True, installer=proof,
                      normalInstallPlan={'executable': str(target), 'arguments': ['/S', '/D=' + str(TARGET)],
                          'note': '/D must be last and unquoted. Ordinary installer elevation applies; no bypass or automatic execution.'})
    except Exception as error:
        report.update(status='FAIL_INDEPENDENT_DOWNLOAD95', error=str(error), retainedBytes=target.stat().st_size if target.exists() else 0)
        raise
    finally:
        finish(report, started)
        write(out / 'Report.json', report)
        write(attempt / 'Report.json', report)
    return out / 'Report.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'download'])
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--partial', type=Path)
    parser.add_argument('--stopped-cli-pid', type=int)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--public-out', type=Path)
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--component', choices=EXPECTED)
    parser.add_argument('--max-seconds', type=int, default=5400)
    parser.add_argument('--workers', type=int, choices=[1, 4], default=1)
    args = parser.parse_args()
    need(args.execute, 'Download95ExplicitRootExecutionRequired')
    if args.action == 'prepare':
        need(args.partial is not None and args.stopped_cli_pid is not None and args.public_out is not None,
             'Download95StoppedPartialAndPublicReceiptRequired')
        result = prepare(args.partial, args.stopped_cli_pid, args.out, args.public_out)
    else:
        need(args.prepared is not None and args.component is not None, 'Download95PreparedComponentRequired')
        result = download(args.prepared, args.component, args.max_seconds, args.out, args.workers)
    print(result)


if __name__ == '__main__':
    main()
