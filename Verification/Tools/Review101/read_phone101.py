"""Read-only preflight of the existing authorized physical test installation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Review98'))
import physical as api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    if not args.execute or not re.fullmatch('[A-Za-z0-9_]{1,30}', args.tag):
        parser.error('Explicit short read-only preflight required')
    out = ROOT / 'Verification/Evidence/Review101/Phone' / args.tag
    private = ROOT / '.verification-cache/Review101/Phone' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    source = Path(__file__)
    snapshot = ROOT / '.verification-cache/Review101/ToolSources' / (api.sha(source) + '.py')
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if not snapshot.exists():
        shutil.copyfile(source, snapshot)
    if api.sha(source) != api.sha(snapshot):
        raise ValueError('ExactReadOnlyReaderArchiveRequired101')
    record = dict(schemaVersion=1, status='PREFLIGHT_PENDING101', utc=api.utc(), runner=api.bound(snapshot),
                  scope='Read-only inventoried phone/keyguard/candidate state. No wake/unlock/install/launch/input/security or owner data mutation.')
    try:
        inventory = json.loads(api.INVENTORY.read_text('utf-8'))
        devices = [d for d in inventory['devices'] if d['state'] == 'device' and d['transport'] == 'physicalOrNetwork']
        if len(devices) != 1:
            raise ValueError('SingleInventoriedPhoneRequired101')
        phone = api.Physical.__new__(api.Physical)
        phone.out, phone.private, phone.counter, phone.device = out, private, 0, devices[0]
        phone.serial = (ROOT / inventory['privateEvidenceDirectory'] / 'selected_device.txt').read_text()
        if hashlib.sha256(phone.serial.encode()).hexdigest() != phone.device['selectorSHA256']:
            raise ValueError('InventoriedSelectorChanged101')
        phone.identity()
        record['selectorSHA256'] = phone.device['selectorSHA256']
        policy = phone.adb('shell', 'dumpsys', 'window', 'policy').split('KeyguardServiceDelegate', 1)[-1]
        record['keyguardShowing'] = not bool(re.search(r'(?m)^\s*showing=false\s*$', policy))
        record['interactiveAwake'] = 'mWakefulness=Awake' in phone.adb('shell', 'dumpsys', 'power')
        candidate = phone.stable(api.PACKAGE)
        record['installedSHA256'] = candidate['installedSHA256']
        expected = 'a476d2a36fa52d72aa9289bab4b40a099f49ccde4030a6f4d71e93a47c361aea'
        if args.build:
            build = json.loads(args.build.read_text('utf-8-sig'))
            if (build.get('status') != 'PASS_NATIVE_REVIEW101_BUILDDEVELOPMENT' or build.get('packageName') != api.PACKAGE
                    or build.get('errors') or api.sha(Path(build['apk'])) != build['apkSHA256']):
                raise ValueError('ExactNativePreviousBuildRequired101')
            expected = build['apkSHA256']
            record['expectedPreviousBuild'] = api.bound(args.build)
        if candidate['installedSHA256'] != expected:
            raise ValueError('ExactBoundPreviousCandidateRequired101')
        record['hasActiveAttempt'] = bool(candidate['activeAttempts'])
        record['ownerState'] = phone.stable(api.OWNER)
        record['status'] = 'READY_PHYSICAL101' if not record['keyguardShowing'] and record['interactiveAwake'] else 'AWAITING_PHONE_UNLOCK101'
    except Exception as error:
        record.update(status='STOPPED_READONLY_PHONE_PREFLIGHT101', errorType=type(error).__name__)
        if re.fullmatch('[A-Za-z0-9_]{1,100}', str(error)):
            record['errorCategory'] = str(error)
    api.save(out / 'Report.json', record)
    print(json.dumps(record))
    return 0 if record['status'] == 'READY_PHYSICAL101' else 1


if __name__ == '__main__':
    raise SystemExit(main())
