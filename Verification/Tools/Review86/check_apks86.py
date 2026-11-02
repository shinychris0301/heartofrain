"""Static current86 internal APK checks; never installs or starts an app."""
import json
import re
from pathlib import Path
import subprocess
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools'))
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
import check_apk
from run_ads85_native import sha, write


def main():
    output = ROOT / 'Verification/Evidence/Review86/StaticAndroid' / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    aapt = check_apk.ANDROID / 'SDK/build-tools/34.0.0/aapt.exe'
    artifacts = []
    for name in ('HeartOfTheRain_Development.apk', 'HeartOfTheRain_ReleaseCompile.apk'):
        path = ROOT / 'Unity/Builds/Verification' / name
        folder = output / ('Development' if 'Development' in name else 'NonDevelopment')
        folder.mkdir()
        check_apk.APK, check_apk.OUT = path, folder
        check_apk.run()
        badging = subprocess.check_output([str(aapt), 'dump', 'badging', str(path)], timeout=30).decode('utf-8')
        manifest = subprocess.check_output([str(aapt), 'dump', 'xmltree', str(path), 'AndroidManifest.xml'], timeout=30).decode('utf-8')
        assert "package: name='com.heartoftherain.verification'" in badging
        assert "application-label:'\u0421\u0435\u0440\u0434\u0446\u0435 \u0434\u043e\u0436\u0434\u044f'" in badging
        orientations = re.findall(r'android:screenOrientation\([^\n]+?=\(type 0x10\)0x([0-9a-fA-F]+)', manifest)
        assert orientations and set(orientations) == {'1'}, 'PortraitOnlyActivityRequired'
        minimum = int(re.search(r"^sdkVersion:'(\d+)'\r?$", badging, re.M).group(1))
        target = int(re.search(r"^targetSdkVersion:'(\d+)'\r?$", badging, re.M).group(1))
        assert "native-code: 'arm64-v8a'" in badging
        assert not any(v in manifest for v in ('RuStorePayContentProvider', 'heartoftherain-pay', 'com.yandex.mobile.ads', 'io.appmetrica'))
        with zipfile.ZipFile(path) as archive:
            dex = [archive.read(n) for n in archive.namelist() if n.endswith('.dex')]
            assert dex and any(b'Lcom/heartoftherain/identity/DeviceIdentity82;' in value for value in dex)
            assert all(not any(p in value for p in (b'Lru/rustore/sdk/pay/', b'Lru/rustore/sdk/core/', b'Lcom/yandex/mobile/ads/', b'Lio/appmetrica/')) for value in dex)
        (folder / 'Badging.txt').write_text(badging, encoding='utf-8')
        (folder / 'Manifest.txt').write_text(manifest, encoding='utf-8')
        artifacts.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size,
                          'nativePaymentAndAdvertisingSdkAbsent': True, 'deviceIdentityPresent': True,
                          'minimumApi': minimum, 'targetApi': target, 'portraitOnly': True,
                          'releaseApi26BaselineApplied': minimum >= 26,
                          'staticReport': (folder / 'APK_Artifact.json').relative_to(output).as_posix()})
    report = {'status': 'PASS_SDK_FREE_INTERNAL_APKS_STATIC86', 'artifacts': artifacts,
              'runnerSHA256': sha(Path(__file__)),
              'scope': 'Actual APK CRC, signature, alignment, ELF, label/package, manifest and DEX checks only. No install, SDK, gameplay, ad, payment or production acceptance.'}
    write(output / 'Report.json', report)
    print(json.dumps({'status': report['status'], 'report': (output / 'Report.json').relative_to(ROOT).as_posix()}))


if __name__ == '__main__':
    main()
