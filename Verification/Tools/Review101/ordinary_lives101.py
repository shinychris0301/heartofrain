"""Reversible ordinary Home heart and original Level-button observations."""
import argparse
import json
from pathlib import Path
import re
import time

from phone101 import Device101, ROOT, previous, PACKAGE, OWNER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute or not re.fullmatch('[A-Za-z0-9_]{1,30}', args.tag):
        parser.error('Explicit ordinary header/Level observation required')
    out = ROOT / 'Verification/Evidence/Review101/Phone' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    record = dict(status='RUNNING_ORDINARY_LIVES101', utc=previous.utc(), runner=previous.bound(Path(__file__)),
                  build=previous.bound(args.build), captures=[], inputs=[],
                  scope='Ordinary saved full-life candidate: actual heart opens information sheet; explicit Level opens its original start preview. Neither Play nor refill is tapped. One physical phone, no provider or financial operation.')
    phone = None
    try:
        phone = Device101(out, args.build)
        phone.guard()
        record['ownerBefore'] = phone.stable(OWNER)
        record['candidateBefore'] = phone.installed()
        if phone.adb('shell', 'wm', 'size') != 'Physical size: 720x1600':
            raise ValueError('VerifiedOrdinaryTouchGeometryRequired101')
        record['captures'].append(phone.capture('Ordinary_Home_Before_OS'))

        def tap(purpose, x, y):
            phone.adb('shell', 'input', 'tap', x, y)
            record['inputs'].append(dict(purpose=purpose, x=x, y=y))
            time.sleep(1)

        def close(purpose):
            phone.adb('shell', 'input', 'keyevent', '4')
            record['inputs'].append(dict(purpose=purpose, key='BACK'))
            time.sleep(.8)

        tap('Existing header heart icon', 445, 140)
        record['captures'].append(phone.capture('Ordinary_Full_Lives_OS'))
        close('Close information sheet without starting gameplay')
        tap('Explicit existing Level1 button', 360, 1320)
        record['captures'].append(phone.capture('Original_Level_Preview_OS'))
        close('Close level preview without Play')
        record['captures'].append(phone.capture('Ordinary_Home_After_OS'))
        record['candidateAfter'] = phone.stable(PACKAGE)
        record['candidateDataPreserved'] = record['candidateBefore'] == record['candidateAfter']
        record['status'] = 'RECORDED_ORDINARY_LIVES101_REQUIRES_REVIEW' if record['candidateDataPreserved'] else 'FAIL_ORDINARY_LIVES101_SAVE_CHANGED'
    except Exception as error:
        record.update(status='STOPPED_ORDINARY_LIVES101', errorType=type(error).__name__)
        if re.fullmatch('[A-Za-z0-9_]{1,120}', str(error)):
            record['errorCategory'] = str(error)
    finally:
        if phone:
            try:
                record['ownerAfter'] = phone.stable(OWNER)
                record['ownerStatePreserved'] = record.get('ownerBefore') == record['ownerAfter']
                if not record['ownerStatePreserved']:
                    record['status'] = 'FAIL_ORDINARY_LIVES101_OWNER_CHANGED'
            except Exception as error:
                record['ownerReadbackErrorType'] = type(error).__name__
        record['finishedUtc'] = previous.utc()
        previous.save(out / 'Report.json', record)
    print(json.dumps(dict(status=record['status'], report=(out / 'Report.json').relative_to(ROOT).as_posix())))
    return 0 if record['status'].startswith('RECORDED_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
