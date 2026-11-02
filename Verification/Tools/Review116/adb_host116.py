"""Keep one newly started localhost adb server outside transient Unity jobs.

Never stops an existing server, targets a device, changes security/settings, or
reboots anything. Raw server output stays private. The owner releases only this
helper's process through an exact scoped control marker after device work.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import time
import os

ROOT = Path(__file__).resolve().parents[3]
ADB = Path(r'C:/Program Files/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe')
BASE = ROOT / '.verification-cache/Review116/AdbHost'
PUBLIC = ROOT / 'Verification/Evidence/Review116/Emulator/AdbHost'
PAYLOAD = b'release-owned-server116\n'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def listening(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=.5):
            return True
    except OSError:
        return False


def listener_pid(port):
    result = subprocess.run(['netstat', '-ano', '-p', 'tcp'], capture_output=True,
        timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    matches = re.findall(r'(?m)^\s*TCP\s+127\.0\.0\.1:' + str(port) + r'\s+\S+\s+LISTENING\s+([0-9]+)\s*$',
                         result.stdout.decode('utf-8', errors='replace'))
    return int(matches[0]) if len(matches) == 1 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('hold', 'release'))
    parser.add_argument('--name', required=True)
    parser.add_argument('--port', type=int, default=5037)
    parser.add_argument('--emulator-only', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]{1,40}', args.name):
        raise RuntimeError('ScopedAdbHostNameRequired')
    private, public = BASE / args.name, PUBLIC / args.name
    marker = private / 'ReleaseOwnedServer'
    if args.operation == 'release':
        if not (public / 'Started.json').is_file() or marker.exists():
            raise RuntimeError('OwnedRunningServerReceiptRequired')
        marker.write_bytes(PAYLOAD)
        return
    if args.port not in (5037, 5041) or (args.emulator_only and args.port != 5041):
        raise RuntimeError('ApprovedLocalhostPortRequired')
    if private.exists() or public.exists():
        raise RuntimeError('FreshAdbHostEvidenceRequired')
    if listening(args.port):
        raise RuntimeError('ExistingAdbServerPreservedNoTakeover')
    private.mkdir(parents=True)
    public.mkdir(parents=True)
    started = dict(status='STARTING_OWNED_ADB_HOST116', utc=utc(),
        runnerSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), port=args.port,
        scope='Newly started localhost adb host server only; no device command, server takeover, security/settings/mount change or reboot.')
    process = None
    with (private / 'Server.private').open('xb') as log:
        try:
            # This stock Windows adb accepts the reserved localhost spelling;
            # a numeric host in -L is rejected by its listener implementation.
            command = [str(ADB), '-L', 'tcp:localhost:' + str(args.port)]
            env = dict(os.environ)
            if args.emulator_only:
                command += ['--one-device', 'HOTR_REVIEW116_NO_USB_TRANSPORT']
                env['ADB_LOCAL_TRANSPORT_MAX_PORT'] = '5555'
                env['ADB_MDNS_AUTO_CONNECT'] = ''
            command += ['server', 'nodaemon']
            process = subprocess.Popen(command, stdout=log, stderr=log, env=env,
                creationflags=subprocess.CREATE_NO_WINDOW)
            deadline = time.monotonic() + 15
            while process.poll() is None and listener_pid(args.port) != process.pid and time.monotonic() < deadline:
                time.sleep(.25)
            if process.poll() is not None or listener_pid(args.port) != process.pid:
                raise RuntimeError('OwnedAdbServerDidNotBind')
            started.update(status='RUNNING_OWNED_ADB_HOST116', serverPid=process.pid,
                exactListenerPidVerified=True, usbRestrictedToNonMatchingSentinel=args.emulator_only,
                defaultServerUntouched=args.port != 5037)
            (public / 'Started.json').write_text(json.dumps(started, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(started), flush=True)
            deadline = time.monotonic() + 7200
            while process.poll() is None and time.monotonic() < deadline:
                if marker.exists():
                    if marker.read_bytes() != PAYLOAD:
                        raise RuntimeError('ForeignReleaseMarkerPreserved')
                    break
                time.sleep(.5)
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
            result = dict(status='CLOSED_OWNED_ADB_HOST116', utc=utc(), serverPid=process.pid if process else None,
                exitCode=process.returncode if process else None, ownedReleaseRequested=marker.exists(),
                scope='Only the exact process started by this helper was closed. No kill-server, device lifecycle or settings command.')
            (public / 'Finished.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
