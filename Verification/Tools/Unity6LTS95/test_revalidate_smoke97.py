"""Host-only alias and failed-native rejection controls; no native execution."""
import unittest
import revalidate_smoke97 as subject


class RevalidationTests(unittest.TestCase):
    def badging(self, minimum="minSdkVersion:'26'"):
        return "package: name='com.heartoftherain.toolchain95' versionCode='95'\n"+minimum+"\ntargetSdkVersion:'36'\n"

    def tree(self):
        return ' A: package="com.heartoftherain.toolchain95"\n A: android:minSdkVersion(0x0101020c)=26\n A: android:targetSdkVersion(0x01010270)=36\n'

    def test_current_and_legacy_names_have_equal_values(self):
        for alias in ('minSdkVersion', 'sdkVersion'):
            self.assertEqual(subject.validate_manifest(self.badging(alias+":'26'"), self.tree())['minSdk'], 26)

    def test_missing_wrong_duplicate_or_conflicting_minimum_is_rejected(self):
        for value in ('', "minSdkVersion:'25'", "minSdkVersion:'26'\nsdkVersion:'26'", "minSdkVersion:'26'\nsdkVersion:'25'"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                subject.validate_manifest(self.badging(value), self.tree())

    def test_target_and_package_and_binary_manifest_are_independently_required(self):
        for badging, tree in ((self.badging().replace("'36'", "'35'"), self.tree()),
                              (self.badging().replace('toolchain95', 'other'), self.tree()),
                              (self.badging(), self.tree().replace('=26', '=25')),
                              (self.badging(), self.tree().replace('toolchain95', 'other'))):
            with self.assertRaises(ValueError): subject.validate_manifest(badging, tree)

    def original(self):
        return dict(status='FAIL_ACTUAL_LTS95_TOOLCHAIN_SMOKE', error='Smoke95ActualAPKPackageAndAPIValidationFailed',
                    exitCode=0, actualEngineVersionFromLog='6000.3.27f1', nativeStatus='PASS_ACTUAL_LTS95_EMPTY_ANDROID_BUILD',
                    unityPidsAfter=[], **{flag: True for flag in subject.FLAGS})

    def test_only_exact_post_native_static_failure_can_be_revalidated(self):
        subject.validate_original(self.original())
        for key, value in dict(error='ActualBuildFailed', exitCode=1, timedOut=True, nativeStatus='FAIL_NATIVE',
                               actualEngineVersionFromLog='2022.3.62f3', unityPidsAfter=[42],
                               **{flag: False for flag in subject.FLAGS}).items():
            bad = self.original(); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): subject.validate_original(bad)


if __name__ == '__main__': unittest.main(verbosity=2)
