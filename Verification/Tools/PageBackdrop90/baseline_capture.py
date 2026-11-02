"""Root-invoked reproduction on accepted89; no model transactions or data reset."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/RegionalAccounts89'))
from phone import CapturePathPhone, public_binding, validate_png, write, utc


def main():
    out = ROOT / 'Verification/Evidence/PageBackdrop90/Baseline89'
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'Invocation.json').exists():
        raise RuntimeError('BaselineRunExistsPreserveOriginal')
    prior = ROOT / 'Verification/Evidence/RegionalAccounts89/Phone/Device01'
    p = CapturePathPhone(prior)
    p.assert_installed()
    p.assert_no_active_attempt()
    before = p.inventory()
    write(out / 'Before.json', before)
    record = {'status': 'RUNNING_ROOT_OS_BASELINE90', 'utc': utc(),
              'runner': public_binding(Path(__file__)), 'priorTarget': public_binding(prior / 'Target.json'),
              'apkSHA256': before['installedSHA256'], 'actions': [], 'captures': [],
              'scope': 'Actual accepted89 phone OS screenshots. Single navigation touches only; root must inspect screen identities. No readiness, gameplay or provider claim.'}
    def persist():
        (out / 'Invocation.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    persist()
    def capture(name):
        raw = p.adb('exec-out', 'screencap', '-p', binary=True)
        w, h = validate_png(raw)
        path = out / (name + '.png')
        with path.open('xb') as stream:
            stream.write(raw)
        row = dict(public_binding(path), width=w, height=h, kind='ACTUAL_ANDROID_OS_FRAMEBUFFER',
                   pngValidation='COMPLETE_CHUNKS_IEND_CRC_AND_DECODE', installedSHA256=p.installed_sha())
        write(path.with_suffix('.json'), row)
        record['captures'].append(row)
        persist()
    def tap(name, x, y):
        row = {'name': name, 'x': x, 'y': y, 'utc': utc(), 'dispatch': 'PENDING'}
        record['actions'].append(row)
        persist()
        p.adb('shell', 'input', 'tap', str(x), str(y))
        row.update(dispatch='ADB_COMPLETED', completedUtc=utc())
        persist()
        time.sleep(1)
    capture('Home')
    tap('OpenShop', 648, 1500)
    capture('Shop_TopBand')
    tap('ReturnHome', 360, 1500)
    capture('Home_Return')
    after = p.inventory()
    for field in ('profiles', 'preferences', 'profileSummaries'):
        if before[field] != after[field]:
            raise RuntimeError('OwnerDataChangedStop')
    write(out / 'After.json', after)
    record.update(status='RECORDED_ACTUAL_OS_BASELINE90_REQUIRES_ROOT_REVIEW', ownerDataUnchanged=True)
    persist()
    print(record['status'])


if __name__ == '__main__':
    main()
