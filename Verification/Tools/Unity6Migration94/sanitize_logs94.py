"""Create bound, explicitly redacted public derivatives; never rewrite raw logs.

Host privacy preparation only. No Unity, SDK, device, credential, or Git operation.
Run only after the selected native invocations have finished writing their logs.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_REL = Path('Verification/Evidence/Unity6Migration94')
PRIVATE_REL = Path('.verification-cache/Unity6Migration94/PrivateEvidence')
NAMES = {'unity.log', 'console.log'}
MARKER = '<redacted:{}>'

# Only the value span is replaced. Prefixes, unrelated text, BOM, and line endings
# remain exact. A value-bearing licensing header is different from a status such
# as "Access token is unavailable"; the latter has no colon/value and is retained.
FIELD_NAMES = {
    'machine_id': r'Machine[ _-]?Id',
    'session_id': r'Session[ _-]?Id',
    'correlation_id': r'(?:External[ _-]?)?Correlation[ _-]?Id',
    'license_serial': r'(?:License[ _-]?)?Serial[ _-]?(?:No\.?|Number)(?:\s+assigned\s+to)?',
    'device_id': r'(?:Device[ _-]?(?:Id|Identifier|Serial)|USB[ _-]?Serial|Android[ _-]?Id|IMEI|IMSI|UDID)',
    'credential_value': r'(?:Access[ _-]?Token|Refresh[ _-]?Token|Session[ _-]?(?:Token|Key)|API[ _-]?Key|Client[ _-]?Secret|Password|License[ _-]?(?:Key|Token))',
}
FIELDS = {
    category: re.compile(r'(?i)(?P<prefix>\b' + names + r'\s*["\']?\s*[:=]\s*["\']?)(?P<value>[^\r\n]+)')
    for category, names in FIELD_NAMES.items()
}
ADB_SERIAL = re.compile(r'(?i)(?P<prefix>\badb(?:\.exe)?["\']?[^\r\n]{0,180}?\s-s\s+)(?P<value>"[^"\r\n]+"|\'[^\'\r\n]+\'|[^\s\r\n]+)')
UNSUPPORTED = (
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'),
    re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'),
    re.compile(r'(?<![A-Za-z0-9])(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16}|AIza[0-9A-Za-z_-]{30,}|sk-[A-Za-z0-9_-]{24,})'),
    re.compile(r'(?i)\bBearer\s+(?!<redacted:)[A-Za-z0-9_./+=-]{8,}'),
    re.compile(r'https?://[^\s/@:]+:[^\s/@]+@'),
    re.compile(r'(?i)[?&](?:access_token|token|api_key|secret|password|sessionid)=[^&\s"\']{6,}'),
)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def redact(raw):
    """Return the derivative and category/line-only audit; no sensitive values."""
    text = raw.decode('utf-8')  # Strict, preserves UTF-8 BOM; refuse lossy decoding.
    if '\x00' in text:
        raise RuntimeError('UnsupportedLogEncoding')
    changes = []
    result = []
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        for category, pattern in FIELDS.items():
            def replace(match):
                value = match.group('value')
                if value.startswith(MARKER.format(category)):
                    return match.group(0)
                # Explicit empty/status-only credential fields carry no secret.
                if category == 'credential_value' and re.fullmatch(r'(?i)(?:none|null|false|unavailable|\[redacted\]|<redacted>)["\']?\s*', value):
                    return match.group(0)
                changes.append({'line': number, 'category': category})
                return match.group('prefix') + MARKER.format(category)
            line = pattern.sub(replace, line)
        def replace_adb(match):
            if match.group('value').startswith(MARKER.format('adb_serial')):
                return match.group(0)
            changes.append({'line': number, 'category': 'adb_serial'})
            return match.group('prefix') + MARKER.format('adb_serial')
        line = ADB_SERIAL.sub(replace_adb, line)
        result.append(line)
    public = ''.join(result)
    if any(pattern.search(public) for pattern in UNSUPPORTED):
        raise RuntimeError('UnsupportedSensitiveValueRequiresSeparateReview')
    return public.encode('utf-8'), changes


def require_within(path, parent):
    target, base = path.resolve(), parent.resolve()
    if not target.is_relative_to(base) or target == base:
        raise RuntimeError('PathOutside94Scope')
    return target


def source_logs(evidence):
    """Snapshot exact raw basenames, including all casing and baseline copies."""
    found = []
    for path in evidence.rglob('*'):
        if path.is_file() and path.name.casefold() in NAMES:
            require_within(path, evidence)
            if path.is_symlink():
                raise RuntimeError('RawLogSymlinkRefused')
            found.append(path)
    return sorted(found, key=lambda p: p.as_posix().casefold())


def write_new(path, body, readonly=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(body)
    if readonly:
        os.chmod(path, stat.S_IREAD)


def publish(out, *, workspace=ROOT, private_id=None):
    workspace = workspace.resolve()
    evidence = workspace / EVIDENCE_REL
    out = require_within(Path(out), evidence / 'Privacy')
    if out.exists():
        raise RuntimeError('FreshPublicOutputRequired')
    private_id = private_id or uuid.uuid4().hex
    if not re.fullmatch(r'[a-f0-9]{32}', private_id):
        raise RuntimeError('InvalidPrivateSetIdentifier')
    private = require_within(workspace / PRIVATE_REL / private_id, workspace / PRIVATE_REL)
    if private.exists():
        raise RuntimeError('FreshPrivateOutputRequired')
    logs = source_logs(evidence)
    if not logs:
        raise RuntimeError('NoRaw94Logs')
    # Fully validate before creating outputs. An unsupported credential shape
    # refuses publication; it cannot be hidden in an opaque "sanitized" file.
    prepared = []
    for source in logs:
        raw = source.read_bytes()
        derivative, changes = redact(raw)
        prepared.append((source, raw, derivative, changes))
    out.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    entries = []
    for source, raw, derivative, changes in prepared:
        if source.read_bytes() != raw:
            raise RuntimeError('RawLogChangedDuringPreparation')
        relative = source.relative_to(evidence)
        private_copy = private / 'Logs' / relative
        public_copy = out / 'Public' / relative.parent / (relative.stem + '.sanitized.log')
        write_new(private_copy, raw, readonly=True)
        write_new(public_copy, derivative)
        if private_copy.read_bytes() != raw or source.read_bytes() != raw:
            raise RuntimeError('RawLogPreservationFailed')
        expected, repeated = redact(raw)
        if expected != public_copy.read_bytes() or repeated != changes:
            raise RuntimeError('DerivativeTransformationMismatch')
        entries.append({
            'rawSource': source.relative_to(workspace).as_posix(),
            'rawSHA256': sha(raw), 'rawBytes': len(raw),
            'privateCopy': private_copy.relative_to(workspace).as_posix(),
            'privateSHA256': sha(private_copy.read_bytes()),
            'publicDerivative': public_copy.relative_to(workspace).as_posix(),
            'publicSHA256': sha(derivative), 'publicBytes': len(derivative),
            'redactions': changes, 'categoryCounts': dict(Counter(c['category'] for c in changes)),
            'changedLineCount': len({c['line'] for c in changes}),
        })
    # Final whole-set check also catches an earlier log changing while later
    # files were copied. Existing native raw-log hashes are never rewritten.
    if source_logs(evidence) != logs or any(source.read_bytes() != raw for source, raw, _, _ in prepared):
        raise RuntimeError('RawLogSetChangedDuringPublication')
    receipt = {
        'schemaVersion': 1, 'status': 'PASS_HOST_94_REDACTED_LOG_DERIVATIVES',
        'completedUtc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Host privacy preparation only. Native raw logs remain byte-exact at their original paths and in new read-only private copies. Public files are explicitly sanitized derivatives, not replacement native evidence. No Unity/device/provider/runtime verification is claimed. Future raw logs require another fresh set.',
        'rawLogCount': len(entries), 'redactedLogCount': sum(bool(e['redactions']) for e in entries),
        'privateRoot': private.relative_to(workspace).as_posix(),
        'files': entries, 'errors': [],
    }
    write_new(out / 'Receipt.json', (json.dumps(receipt, indent=2) + '\n').encode('utf-8'))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        parser.error('--execute is required; raw logs are never modified')
    if not args.out.is_absolute():
        parser.error('--out must be an absolute fresh path below new94 Privacy')
    receipt = publish(args.out)
    print(json.dumps({key: receipt[key] for key in ('status', 'rawLogCount', 'redactedLogCount')}))


if __name__ == '__main__':
    main()
