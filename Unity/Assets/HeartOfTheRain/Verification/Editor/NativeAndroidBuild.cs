#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace HeartOfTheRain.Verification
{
    public static class NativeAndroidBuild
    {
        [Serializable] sealed class Report
        {
            public string status, utc, unity, output, error;
            public string scope = "Internal development APK using Launch then the supplied first-start scene; no store signing, publishing or physical-device certification.";
            public int errors, warnings;
            public long bytes;
            public string productName;
            public bool showSplashScreen, showUnityLogo, hasProLicense;
        }
        public static void Run() => Build(false);
        // Non-development build: DEVELOPMENT_BUILD is undefined, so every
        // review/QA script behind that guard must compile out cleanly. It uses
        // the same internal identifier and signing; it is not a store release.
        public static void RunRelease() => Build(true);
        static void Build(bool release)
        {
            string failed = release ? "FAIL_ANDROID_RELEASE_COMPILE_BUILD" : "FAIL_ANDROID_DEVELOPMENT_BUILD";
            string passed = release ? "PASS_ANDROID_RELEASE_COMPILE_BUILD" : "PASS_ANDROID_DEVELOPMENT_BUILD";
            var report = new Report { utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion, status = failed };
            if (release) report.scope = "Internal non-development APK proving the release compile (review/QA scripts excluded) using Launch then the supplied first-start scene; same internal identifier and signing as the development build; not a store release.";
            string root = Path.GetFullPath("../Verification/Evidence/Native");
            Directory.CreateDirectory(root);
            string appId = PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android);
            string company = PlayerSettings.companyName, product = PlayerSettings.productName;
            var backend = PlayerSettings.GetScriptingBackend(NamedBuildTarget.Android);
            var architectures = PlayerSettings.Android.targetArchitectures;
            bool appBundle = EditorUserBuildSettings.buildAppBundle;
            try
            {
                if (Application.unityVersion != "2022.3.62f3") throw new InvalidOperationException("Wrong editor version.");
                if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Android, BuildTarget.Android))
                    throw new InvalidOperationException("Install Android Build Support and matching SDK/NDK/OpenJDK first.");
                PlayerSettings.companyName = "Heart of the Rain";
                // Keep the approved visible name. Package identity remains the
                // internal verification ID; localization must not fork saves.
                report.productName = PlayerSettings.productName;
                report.showSplashScreen = PlayerSettings.SplashScreen.show;
                report.showUnityLogo = PlayerSettings.SplashScreen.showUnityLogo;
                report.hasProLicense = UnityEditorInternal.InternalEditorUtility.HasPro();
                PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, "com.heartoftherain.verification");
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
                PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
                EditorUserBuildSettings.buildAppBundle = false;
                report.output = Path.GetFullPath(release ? "Builds/Verification/HeartOfTheRain_ReleaseCompile.apk" : "Builds/Verification/HeartOfTheRain_Development.apk");
                Directory.CreateDirectory(Path.GetDirectoryName(report.output));
                var build = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
                    scenes = new[] { HeartOfTheRain.App.Launch.LaunchPage.ScenePath, HeartOfTheRain.App.Launch.LaunchPage.GameScenePath },
                    locationPathName = report.output, target = BuildTarget.Android,
                    options = release ? BuildOptions.None : BuildOptions.Development | BuildOptions.AllowDebugging
                });
                report.errors = (int)build.summary.totalErrors;
                report.warnings = (int)build.summary.totalWarnings;
                report.bytes = (long)build.summary.totalSize;
                if (build.summary.result != BuildResult.Succeeded) throw new InvalidOperationException("Android build result: " + build.summary.result);
                report.status = passed;
            }
            catch (Exception ex) { report.error = ex.ToString(); }
            finally
            {
                PlayerSettings.companyName = company; PlayerSettings.productName = product;
                PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, appId);
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, backend);
                PlayerSettings.Android.targetArchitectures = architectures;
                EditorUserBuildSettings.buildAppBundle = appBundle;
                File.WriteAllText(Path.Combine(root, release ? "Android_Release_Build.json" : "Android_Build.json"), JsonUtility.ToJson(report, true));
            }
            if (Application.isBatchMode) EditorApplication.Exit(report.status.StartsWith("PASS", StringComparison.Ordinal) ? 0 : 1);
        }
    }
}
#endif
