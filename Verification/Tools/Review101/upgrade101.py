"""Same-signer update of the one separately scoped test candidate only."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from phone101 import Device101, ROOT, previous, PACKAGE, OWNER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--previous-build', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute or not re.fullmatch('[A-Za-z0-9_]{1,30}', args.tag):
        parser.error('Explicit same-candidate upgrade required')
    out = ROOT / 'Verification/Evidence/Review101/Phone' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    result = dict(status='RUNNING_PHYSICAL_UPGRADE101', utc=previous.utc(), runner=previous.bound(Path(__file__)),
                  build=previous.bound(args.build), previousBuild=previous.bound(args.previous_build),
                  scope='Same inventoried separate candidate only. Exact native/static APK, same signer, guarded idle profile/preferences and original package state. No clear/uninstall/owner reconstruction or production signing.')
    phone = None
    try:
        phone = Device101(out, args.build)
        phone.guard()
        static = json.loads((args.build.parent / 'StaticApk101.json').read_text('utf-8'))
        if static.get('status') != 'PASS_STATIC_APK101' or static.get('apkSHA256') != phone.expected:
            raise ValueError('ExactPassingStaticArtifactRequired101')
        prior = json.loads(args.previous_build.read_text('utf-8-sig'))
        if prior.get('packageName') != PACKAGE or prior.get('errors') or previous.sha(prior['apk']) != prior['apkSHA256']:
            raise ValueError('ExactPreviousCandidateArtifactRequired101')
        result['ownerBefore'] = phone.stable(OWNER)
        before = phone.stable(PACKAGE)
        result['candidateBefore'] = before
        if before['installedSHA256'] != prior['apkSHA256'] or before['activeAttempts']:
            raise ValueError('ExactIdlePreviousCandidateRequired101')
        android = Path('E:/HeartRainUnity6LTS95/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer')
        certs = []
        for index, apk in enumerate((Path(prior['apk']), phone.apk)):
            command = [str(android / 'OpenJDK/bin/java.exe'), '-jar', str(android / 'SDK/build-tools/36.0.0/lib/apksigner.jar'), 'verify', '--print-certs', str(apk)]
            completed = subprocess.run(command, capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
            (phone.private / ('Signer' + str(index) + '.out')).write_bytes(completed.stdout)
            found = re.findall(r'(?m)^Signer #1 certificate SHA-256 digest: ([a-f0-9]{64})\s*$', completed.stdout.decode('utf-8', 'replace'))
            if completed.returncode or len(found) != 1:
                raise ValueError('ActualCandidateSignerUnknown101')
            certs.append(found[0])
        if certs[0] != certs[1]:
            raise ValueError('CandidateSignerChanged101')
        phone.adb('shell', 'am', 'force-stop', PACKAGE)
        if phone.stable(PACKAGE) != before:
            raise ValueError('CandidateChangedBeforeUpdate101')
        phone.adb('install', '-r', '-t', str(phone.apk), timeout=180)
        result['candidateAfter'] = phone.installed()
        strip = lambda value: {k: v for k, v in value.items() if k != 'installedSHA256'}
        result['candidateDataPreserved'] = strip(before) == strip(result['candidateAfter'])
        result['sameSigner'] = True
        result['status'] = 'PASS_PHYSICAL_CANDIDATE_UPGRADE101' if result['candidateDataPreserved'] else 'FAIL_PHYSICAL_UPGRADE101_SAVE_CHANGED'
    except Exception as error:
        result.update(status='STOPPED_PHYSICAL_UPGRADE101', errorType=type(error).__name__)
        if re.fullmatch('[A-Za-z0-9_]{1,120}', str(error)):
            result['errorCategory'] = str(error)
    finally:
        if phone:
            try:
                result['ownerAfter'] = phone.stable(OWNER)
                result['ownerStatePreserved'] = result.get('ownerBefore') == result['ownerAfter']
                if not result['ownerStatePreserved']:
                    result['status'] = 'FAIL_PHYSICAL_UPGRADE101_OWNER_CHANGED'
            except Exception as error:
                result['ownerReadbackErrorType'] = type(error).__name__
        result['finishedUtc'] = previous.utc()
        previous.save(out / 'Report.json', result)
    print(json.dumps(dict(status=result['status'], report=(out / 'Report.json').relative_to(ROOT).as_posix())))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
