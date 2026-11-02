"""Run the existing transient regression on the explicitly authorized phone."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import time
from phone import Phone, sha, utc, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    phone = Phone(args.out)
    folder = phone.run_dir/'Regression'
    folder.mkdir(exist_ok=False)
    before = phone.snapshot()
    record = {'status': 'RUNNING', 'startedUtc': utc(), 'ordinaryBefore': before,
              'runnerSHA256': sha(__file__), 'phoneHelperSHA256': sha(Path(__file__).with_name('phone.py')),
              'scope': 'Actual selected physical ARM64 phone; unchanged86 APK; transient profile/settings, programmatic actions and accelerated playback. Not human campaign wins, manual touch, provider or general performance certification.'}
    write(folder/'Invocation.json', record)
    error = None
    try:
        began = phone.start_marker('HOTR_RunRegression', utc())
        deadline = time.monotonic()+2100
        while time.monotonic() < deadline:
            body = phone.adb('shell', 'cat', phone.base+'/Regression/Regression.json', check=False)
            try:
                report = json.loads(body)
                fresh = datetime.fromisoformat(report['utc'].replace('Z', '+00:00')) >= began
            except (ValueError, KeyError, TypeError):
                report, fresh = {}, False
            if fresh:
                print(json.dumps({k: report.get(k) for k in ('status', 'checks', 'labels', 'clips', 'actions', 'boards')}), flush=True)
                write(folder/'Latest.json', report)
                if report['status'] != 'RUNNING':
                    allowed = set(report['frames']) | {'Regression.json', 'M70_Device.json'}
                    remote = phone.base+'/Regression'
                    names = phone.adb('shell', 'find', remote, '-type', 'f').splitlines()
                    assert len(names) <= 1000 and all(n.startswith(remote+'/') and n.removeprefix(remote+'/') in allowed for n in names)
                    assert all(re.fullmatch(r'[A-Za-z0-9_-]+\.(?:png|json)', n) for n in allowed)
                    phone.adb('pull', remote+'/.', folder/'Native')
                    assert json.loads((folder/'Native/Regression.json').read_text('utf-8')) == report
                    record.update(nativeStatus=report['status'], checks=report['checks'], boards=report['boards'], actions=report['actions'], clips=report['clips'], failures=report['failures'])
                    record['appLog'] = phone.app_log('Regression/Runtime.log')
                    phone.capture('Regression/Final.png')
                    assert report['status'] == 'PASS_NATIVE_REGRESSION' and not report['failures']
                    assert report['boards'] == 50 and report['actions'] >= 400 and report['clips'] >= 350
                    record['status'] = 'PASS_PHYSICAL_TRANSIENT_REGRESSION87'
                    break
            time.sleep(15)
        else:
            raise TimeoutError('Physical transient regression host deadline')
    except Exception as exc:
        error = exc
        record.update(status='FAIL_PHYSICAL_TRANSIENT_REGRESSION87', errorType=type(exc).__name__)
    finally:
        after = phone.snapshot()
        record.update(ordinaryAfter=after, ordinaryDataUnchanged=before == after)
        if before == after:
            phone.finish_probe()
            final = phone.snapshot()
            record.update(ordinaryAfterNormalRelaunch=final, ordinaryDataUnchangedAfterRelaunch=before == final)
            if final != before:
                record['status'] = 'FAIL_ORDINARY_DATA_PRESERVATION87'
        else:
            record['status'] = 'FAIL_ORDINARY_DATA_PRESERVATION87'
        record['finishedUtc'] = utc()
        record['artifactsSHA256'] = {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob('*') if p.is_file() and p.name != 'Invocation.json'}
        write(folder/'Invocation.json', record)
    print(json.dumps({'status': record['status'], 'evidence': str(folder.relative_to(phone.root))}), flush=True)
    return 0 if record['status'] == 'PASS_PHYSICAL_TRANSIENT_REGRESSION87' else 1


if __name__ == '__main__':
    raise SystemExit(main())
