"""Inspect both SDK-free internal Android artifacts without installing them."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

import check_apk

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/Evidence/ServerGameplay83/VerifiedCompatibility/Android'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    aapt = check_apk.ANDROID / 'SDK/build-tools/34.0.0/aapt.exe'
    rows = []
    for name in ('HeartOfTheRain_Development.apk', 'HeartOfTheRain_ReleaseCompile.apk'):
        path = ROOT / 'Unity/Builds/Verification' / name
        stem = 'Development' if 'Development' in name else 'ReleaseCompile'
        folder = OUT / stem
        folder.mkdir(parents=True, exist_ok=True)
        check_apk.APK, check_apk.OUT = path, folder
        check_apk.run()
        badging = subprocess.check_output([str(aapt), 'dump', 'badging', str(path)], timeout=30).decode('utf-8')
        manifest = subprocess.check_output([str(aapt), 'dump', 'xmltree', str(path), 'AndroidManifest.xml'], timeout=30).decode('utf-8')
        assert "package: name='com.heartoftherain.verification'" in badging
        assert "application-label:'Сердце дождя'" in badging
        assert 'android:screenOrientation' in manifest and 'ru.rustore' not in manifest.lower()
        assert 'RuStorePayContentProvider' not in manifest and 'heartoftherain-pay' not in manifest
        with zipfile.ZipFile(path) as archive:
            dex = [archive.read(n) for n in archive.namelist() if n.endswith('.dex')]
            assert dex and any(b'Lcom/heartoftherain/identity/DeviceIdentity82;' in data for data in dex)
            assert all(b'Lru/rustore/sdk/pay/' not in data and b'Lru/rustore/sdk/core/' not in data for data in dex)
        (folder / 'Badging.txt').write_text(badging, encoding='utf-8')
        (folder / 'Manifest.txt').write_text(manifest, encoding='utf-8')
        rows.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'bytes': path.stat().st_size, 'package': 'com.heartoftherain.verification',
                     'displayName': 'Сердце дождя', 'deviceIdentityJavaClassPresent': True,
                     'nativePayProviderAbsent': True, 'nativeRuStorePayCoreClassesAbsent': True,
                     'staticArtifactReport': (folder / 'APK_Artifact.json').relative_to(OUT.parent).as_posix()})
    report = {'status': 'PASS_CONNECTED84_INTERNAL_APKS_STATIC_INSPECTION', 'artifacts': rows,
              'scope': 'Actual internal APK CRC/signature/alignment/ELF/label/package/manifest/DEX checks. No installation, actual identity operation, store release or payment claim.'}
    (OUT.parent / 'APK_Profile.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(report['status'])


if __name__ == '__main__':
    main()
