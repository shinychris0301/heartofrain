"""Host-only negative controls for static APK parsers; no SDK command or APK inspection."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('apk94_host_parser_test', Path(__file__).with_name('check_apk94.py'))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def elf():
    body = bytearray(128)
    body[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', body, 18, 183)
    struct.pack_into('<Q', body, 32, 64)
    struct.pack_into('<HH', body, 54, 56, 1)
    struct.pack_into('<IIQQQQQQ', body, 64, 1, 5, 0, 0, 0, 128, 128, 16384)
    return body


def manifest():
    return '''N: android=http://schemas.android.com/apk/res/android
  E: manifest (line=2)
    A: package="com.heartoftherain.unity6review94"
    E: uses-sdk (line=4)
      A: android:minSdkVersion(0x0101020c)=(type 0x10)0x1a
    E: application (line=8)
      A: android:debuggable(0x0101000f)=(type 0x12)0xffffffff
      E: activity (line=12)
        A: android:name(0x01010003)="com.unity3d.player.UnityPlayerActivity"
        A: android:screenOrientation(0x0101001e)=(type 0x10)0x1
'''


def badging():
    return "\n".join(("package: name='com.heartoftherain.unity6review94' versionCode='1'",
        "application-label:'Сердце дождя'", "sdkVersion:'26'", "targetSdkVersion:'36'", "native-code: 'arm64-v8a'",
        'application-debuggable', "launchable-activity: name='com.unity3d.player.UnityPlayerActivity'"))


class StaticParsers94(unittest.TestCase):
    def test_aarch64_16k_elf_fixture(self):
        self.assertEqual(api.elf_segments(elf())[0]['alignment'], 16384)

    def test_old_4k_load_alignment_is_rejected(self):
        body = elf()
        struct.pack_into('<Q', body, 64 + 48, 4096)
        with self.assertRaisesRegex(RuntimeError, 'Elf16KiBAlignmentFailed'):
            api.elf_segments(body)

    def test_incongruent_load_offset_is_rejected(self):
        body = elf()
        struct.pack_into('<Q', body, 64 + 16, 1)
        with self.assertRaisesRegex(RuntimeError, 'Elf16KiBAlignmentFailed'):
            api.elf_segments(body)

    def test_truncated_program_headers_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'ElfProgramHeaderBoundsInvalid'):
            api.elf_segments(elf()[:90])

    def test_non_arm64_machine_is_rejected(self):
        body = elf()
        struct.pack_into('<H', body, 18, 62)
        with self.assertRaisesRegex(RuntimeError, 'ExpectedAarch64Machine'):
            api.elf_segments(body)

    def test_actual_manifest_node_and_badging_rules(self):
        result = api.manifest_profile(badging(), manifest(), api.ISOLATED, True)
        self.assertEqual(result['orientation'], 'portrait')
        self.assertEqual(result['minApi'], 26)

    def test_landscape_activity_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'ActualPortraitActivityRequired'):
            api.manifest_profile(badging(), manifest().replace('0x10)0x1\n', '0x10)0x0\n'), api.ISOLATED, True)

    def test_owner_package_cannot_be_misreported_as_isolated(self):
        with self.assertRaisesRegex(RuntimeError, 'ActualPackageMismatch'):
            api.manifest_profile(badging().replace(api.ISOLATED, api.INTERNAL), manifest(), api.ISOLATED, True)

    def test_development_mismatch_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'DevelopmentFlagMismatch'):
            api.manifest_profile(badging(), manifest(), api.ISOLATED, False)

    def test_unknown_bool_encoding_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'UnknownDevelopmentFlagEncoding'):
            api.manifest_profile(badging(), manifest().replace('(type 0x12)0xffffffff', '"unknown"'), api.ISOLATED, True)

    def test_api_22_is_not_api_26(self):
        with self.assertRaisesRegex(RuntimeError, 'ActualMinimumApiMismatch'):
            api.manifest_profile(badging().replace("sdkVersion:'26'", "sdkVersion:'22'"), manifest(), api.ISOLATED, True)

    def archive(self, directory, *, library='lib/arm64-v8a/libfixture.so', dex=b'Lcom/heartoftherain/identity/DeviceIdentity82;', stored=False):
        path = Path(directory) / 'synthetic.zip'
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(library, elf())
            archive.writestr('classes.dex', dex)
        return path

    def test_zip_crc_elf_and_identity_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            result = api.zip_profile(self.archive(directory))
            self.assertEqual(len(result['libraries']), 1)
            self.assertEqual(result['compressedNativeLibraryCount'], 1)

    def test_wrong_zip_abi_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'UnexpectedNativeAbiOrPath'):
                api.zip_profile(self.archive(directory, library='lib/x86_64/libfixture.so'))

    def test_ad_sdk_in_dex_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'UnexpectedPaymentOrAdDex'):
                api.zip_profile(self.archive(directory, dex=b'Lcom/heartoftherain/identity/DeviceIdentity82;Lcom/yandex/mobile/ads/Test;'))

    def test_missing_identity_bridge_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'IdentityBridgeMissing'):
                api.zip_profile(self.archive(directory, dex=b'Lsome/unrelated/Class;'))

    def test_unaligned_stored_library_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'StoredNativeLibraryNot16KiBAligned'):
                api.zip_profile(self.archive(directory, stored=True))


if __name__ == '__main__':
    unittest.main()
