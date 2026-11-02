"""Verify an official metadata route for this one Unity SDK-manager process.

No OS DNS/hosts/trust, Java-wide options, SDK version or security changes.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import socket
import ssl
import uuid

ROOT = Path(__file__).resolve().parents[3]
HOST = 'dl.google.com'
URI = '/android/repository/repository2-3.xml'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag')
    args = parser.parse_args()
    if args.tag is not None and not re.fullmatch('[A-Za-z0-9_]{1,30}', args.tag):
        parser.error('Bounded resolver receipt tag required')
    name = 'SDKResolverPreparation' + ('_' + args.tag if args.tag else '') + '.json'
    output = ROOT / 'Verification/Evidence/Review101' / name
    if not args.execute or output.exists():
        parser.error('Explicit fresh process-only preparation required')
    probes = []
    for address in ('142.250.102.190', '142.250.102.136'):
        context = ssl.create_default_context()
        with socket.create_connection((address, 443), timeout=10) as raw:
            with context.wrap_socket(raw, server_hostname=HOST) as channel:
                channel.settimeout(12)
                channel.sendall(('GET ' + URI + ' HTTP/1.1\r\nHost: ' + HOST + '\r\nConnection: close\r\n\r\n').encode('ascii'))
                received = b''
                while b'\r\n' not in received and len(received) < 4096:
                    chunk = channel.recv(1024)
                    if not chunk:
                        raise ValueError('OfficialMetadataRouteClosed101')
                    received += chunk
                status = received.split(b'\r\n', 1)[0].decode('ascii')
                if status != 'HTTP/1.1 200 OK':
                    raise ValueError('OfficialMetadataRouteNotVerified101')
                probes.append(dict(address=address, host=HOST, defaultTLSVerification=True, statusLine=status,
                                   tls=channel.version(), success=True))
    private = ROOT / '.verification-cache/Review101/SDKResolver' / uuid.uuid4().hex
    private.mkdir(parents=True, exist_ok=False)
    hosts = private / 'sdk_hosts.txt'
    hosts.write_text('\n'.join(p['address'] + ' ' + HOST for p in probes) + '\n', encoding='ascii')
    now = datetime.now(timezone.utc)
    record = dict(status='PREPARED_PROCESS_LOCAL_SDK_RESOLVER98', utc=now.isoformat(), expiresUtc=(now + timedelta(hours=1)).isoformat(),
                  host=HOST, uri=URI, freshTLSProbes=probes,
                  privateHostsFile=dict(path=hosts.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(hosts.read_bytes()).hexdigest()),
                  scope='Fresh certificate-verified official metadata route; process-only SDKMANAGER_OPTS. No OS/global networking, trust, Java-wide option, SDK or security change.')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=record['status'], expiresUtc=record['expiresUtc'], verifiedRoutes=len(probes))))


if __name__ == '__main__':
    main()
