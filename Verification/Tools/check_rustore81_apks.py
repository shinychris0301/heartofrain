"""Static checks for ordinary SDK-free regression artifacts, not a store release."""
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import check_apk

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/RuStore81'


def main():
    check_apk.OUT = OUT
    check_apk.run()
    aapt = check_apk.ANDROID / 'SDK/build-tools/34.0.0/aapt.exe'
    rows = []
    for name in ('HeartOfTheRain_Development.apk', 'HeartOfTheRain_ReleaseCompile.apk'):
        path = ROOT / 'Unity/Builds/Verification' / name
        def dump(*arguments):
            return subprocess.check_output([str(aapt), 'dump', *arguments], timeout=30).decode('utf-8')
        badging = dump('badging', str(path))
        manifest = dump('xmltree', str(path), 'AndroidManifest.xml')
        assert "package: name='com.heartoftherain.verification'" in badging
        assert "application-label:'\u0421\u0435\u0440\u0434\u0446\u0435 \u0434\u043e\u0436\u0434\u044f'" in badging
        assert 'android:screenOrientation' in manifest and 'ru.rustore' not in manifest.lower()
        assert 'RuStorePayContentProvider' not in manifest and 'heartoftherain-pay' not in manifest
        with zipfile.ZipFile(path) as archive:
            for entry in archive.namelist():
                if entry.endswith('.dex'):
                    body = archive.read(entry)
                    assert b'Lru/rustore/sdk/pay/' not in body and b'Lru/rustore/sdk/core/' not in body
        stem = 'Development' if 'Development' in name else 'ReleaseCompile'
        (OUT / (stem + '_Badging.txt')).write_text(badging, encoding='utf-8')
        (OUT / (stem + '_Manifest.txt')).write_text(manifest, encoding='utf-8')
        rows.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'bytes': path.stat().st_size, 'package': 'com.heartoftherain.verification',
                     'displayName': '\u0421\u0435\u0440\u0434\u0446\u0435 \u0434\u043e\u0436\u0434\u044f',
                     'nativePayProviderAbsent': True, 'nativeRuStorePayCoreClassesAbsent': True})
    report = {'status': 'PASS_RUSTORE81_INTERNAL_APKS_SDK_FREE', 'utc': datetime.now(timezone.utc).isoformat(),
              'artifacts': rows, 'scope': 'Actual internal APK label/package, manifest and DEX inspection. SDK-free verification builds only; no real RuStore release, initialization or payment.'}
    (OUT / 'APK_Profile.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(report['status'])


if __name__ == '__main__':
    main()
