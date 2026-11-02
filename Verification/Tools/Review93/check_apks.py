"""Inspect current SDK-free internal APKs; never install, launch or publish."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools'))
import check_apk


def main():
    out = ROOT / 'Verification/Evidence/Review93/Android'
    out.mkdir(parents=True, exist_ok=True)
    aapt = check_apk.ANDROID / 'SDK/build-tools/34.0.0/aapt.exe'
    rows = []
    for name in ('HeartOfTheRain_Development.apk', 'HeartOfTheRain_ReleaseCompile.apk'):
        path = ROOT / 'Unity/Builds/Verification' / name
        folder = out / ('Development' if 'Development' in name else 'NonDevelopment')
        folder.mkdir(parents=True, exist_ok=False)
        check_apk.APK, check_apk.OUT = path, folder
        check_apk.run()
        badging = subprocess.check_output([str(aapt), 'dump', 'badging', str(path)], timeout=30).decode('utf-8')
        manifest = subprocess.check_output([str(aapt), 'dump', 'xmltree', str(path), 'AndroidManifest.xml'], timeout=30).decode('utf-8')
        assert "package: name='com.heartoftherain.verification'" in badging
        assert "application-label:'\u0421\u0435\u0440\u0434\u0446\u0435 \u0434\u043e\u0436\u0434\u044f'" in badging
        assert 'android:screenOrientation' in manifest
        assert not any(value in manifest for value in ('RuStorePayContentProvider', 'heartoftherain-pay', 'com.yandex.mobile.ads', 'io.appmetrica'))
        with zipfile.ZipFile(path) as archive:
            dex = [archive.read(n) for n in archive.namelist() if n.endswith('.dex')]
            assert dex and any(b'Lcom/heartoftherain/identity/DeviceIdentity82;' in data for data in dex)
            assert all(not any(prefix in data for prefix in (b'Lru/rustore/sdk/pay/', b'Lru/rustore/sdk/core/', b'Lcom/yandex/mobile/ads/', b'Lio/appmetrica/')) for data in dex)
        (folder / 'Badging.txt').write_text(badging, encoding='utf-8')
        (folder / 'Manifest.txt').write_text(manifest, encoding='utf-8')
        rows.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'bytes': path.stat().st_size, 'package': 'com.heartoftherain.verification',
                     'nativePaymentAndAdvertisingSdkAbsent': True, 'deviceIdentityClassPresent': True,
                     'staticArtifactReport': (folder / 'APK_Artifact.json').relative_to(out).as_posix()})
    result = {'status': 'PASS_REVIEW93_SDK_FREE_INTERNAL_APKS_STATIC', 'artifacts': rows,
              'scope': 'Actual APK CRC/signature/alignment/ELF/label/package/manifest/DEX checks only. Optional SDK profile is verified separately. No installation, real ad, payment or production claim.'}
    (out / 'APK_Profile.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['status'])


if __name__ == '__main__':
    main()
