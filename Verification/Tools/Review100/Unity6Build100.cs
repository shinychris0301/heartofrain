#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace HeartOfTheRain.Verification
{
    // Checkpoint99 fixture in the prepared private Unity6 copy. Never promotes the main engine or
    // writes the owner app's package, signing credentials or persistent data.
    public static class Unity6Build100
    {
        const string Package = "com.heartoftherain.review98";
        const string Company = "HeartRainReview98";
        const string ClearPath = "Assets/Review98Editor/TransparentIconForeground98.png";
        [Serializable] public sealed class Report
        {
            public string status, operation, utc, unity, error, apk, apkSHA256, packageName, sdk, jdk, ndk, gradle;
            public string scope = "Actual isolated Unity6.3 checkpoint100 configuration/build in the reviewed private98 workspace. Same test identity, no debugger attachment; actual compression option is reported. No main promotion or device/provider/startup acceptance inferred.";
            public int checks, errors, warnings, adaptiveSlots, legacySlots;
            public long bytes;
            public bool showSplash, showUnityLogo, portrait, sdkFree, development, scriptDebugging, lz4hc;
            public string[] adaptiveLabels, enabledScenes;
            public List<string> passed = new List<string>();
        }
        static void Check(Report r, bool condition, string message)
        {
            r.checks++;
            if (!condition) throw new InvalidOperationException(message);
            r.passed.Add(message);
        }
        static string Hash(string p)
        {
            using (var s = File.OpenRead(p)) using (var h = SHA256.Create())
                return BitConverter.ToString(h.ComputeHash(s)).Replace("-", "").ToLowerInvariant();
        }
        static string Project => Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
        public static void Configure() => Run("Configure", true, false);
        public static void Inspect() => Run("Inspect", false, false);
        public static void CoreChecks() => Run("CoreChecks", false, false);
        public static void BuildDevelopment() => Run("BuildDevelopment", false, true);
        public static void BuildDevelopmentDefault() => Run("BuildDevelopment", false, true, false);
        public static void BuildRelease() => Run("BuildRelease", false, true);
        static void Run(string operation, bool configure, bool build, bool useLz4hc = false)
        {
            var r = new Report { operation = operation, utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion, status = "FAIL_NATIVE_REVIEW100_" + operation.ToUpperInvariant() };
            string output = Environment.GetEnvironmentVariable("HOTR_REVIEW100_OUT");
            try
            {
                Check(r, Project.Replace('\\', '/').EndsWith("/.verification-cache/Review98/Game", StringComparison.Ordinal), "Exact isolated Review98 project required");
                Check(r, r.unity == "6000.3.27f1", "Approved stock LTS version required");
                Check(r, !string.IsNullOrEmpty(output) && Path.IsPathRooted(output), "Explicit98 output required");
                Check(r, PlayerSettings.companyName == Company, "Editor preferences isolated before initial import");
                if (configure)
                {
                    PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, Package);
                    PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
                    PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
                    PlayerSettings.Android.minSdkVersion = (AndroidSdkVersions)26;
                    PlayerSettings.Android.targetSdkVersion = (AndroidSdkVersions)36;
                    PlayerSettings.Android.applicationEntry = AndroidApplicationEntry.Activity;
                    PlayerSettings.Android.useCustomKeystore = false;
                    EditorUserBuildSettings.buildAppBundle = false;
                    PlayerSettings.SplashScreen.showUnityLogo = false;
                    PlayerSettings.SplashScreen.show = false;
                    HeartOfTheRain.App.Editor.PortraitBuildPolicy.Configure();
                    ConfigureIcons(r);
                    AssetDatabase.SaveAssets();
                }
                Inspect(r);
                if (operation == "CoreChecks")
                {
                    int prelevel = NativeVerification.PreLevelChecks98();
                    int obstacles = ObstacleIntroduction98Verification.Verify();
                    int timing = NativeVerification.ObstacleTimingChecks99();
                    r.checks += prelevel + obstacles + timing;
                    r.passed.Add("Native current-engine pre-level/refill presenter checks: " + prelevel);
                    r.passed.Add("Native current-engine actual campaign/obstacle checks: " + obstacles);
                }
                if (build)
                {
                    bool development = operation == "BuildDevelopment";
                    Check(r, EditorUserBuildSettings.activeBuildTarget == BuildTarget.Android, "Actual Android target selected");
                    string requested = Environment.GetEnvironmentVariable("HOTR_REVIEW100_APK");
                    r.apk = Path.GetFullPath(requested ?? "");
                    Check(r, r.apk.StartsWith(Project + Path.DirectorySeparatorChar + "Builds" + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)
                        && r.apk.EndsWith(development ? "HeartOfTheRain_Review100.apk" : "HeartOfTheRain_Review100_ReleaseCompile.apk", StringComparison.Ordinal) && !File.Exists(r.apk), "Fresh contained internal APK required");
                    Directory.CreateDirectory(Path.GetDirectoryName(r.apk));
                    var result = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
                        scenes = r.enabledScenes, locationPathName = r.apk, target = BuildTarget.Android,
                        options = (development ? BuildOptions.Development : BuildOptions.None) | (useLz4hc ? BuildOptions.CompressWithLz4HC : BuildOptions.None)
                    });
                    r.errors = (int)result.summary.totalErrors; r.warnings = (int)result.summary.totalWarnings;
                    r.development = (result.summary.options & BuildOptions.Development) != 0;
                    r.scriptDebugging = (result.summary.options & (BuildOptions.AllowDebugging | BuildOptions.ConnectWithProfiler | BuildOptions.EnableDeepProfilingSupport)) != 0;
                    r.lz4hc = (result.summary.options & BuildOptions.CompressWithLz4HC) != 0;
                    Check(r, !r.scriptDebugging && r.lz4hc == useLz4hc, "No remote script debugging/autoconnect/deep profiling; actual compression matches the explicit variant");
                    Check(r, result.summary.result == BuildResult.Succeeded && r.errors == 0 && r.development == development && File.Exists(r.apk), "Actual internal Android compilation succeeds without errors in the requested mode");
                    string registration = Path.Combine(Project, "Library/Bee/artifacts/Android/il2cppOutput/UnityClassRegistration.cpp");
                    Check(r, File.Exists(registration) && File.ReadAllLines(registration).Any(line => line.TrimStart().StartsWith("RegisterUnityClass<SpriteMask>(\"", StringComparison.Ordinal)), "Actual Android native class registration retains SpriteMask with engine stripping enabled");
                    string gradle = Path.Combine(Project,"Library/Bee/Android/Prj/IL2CPP/Gradle");
                    string nativeResources = Path.Combine(gradle,"unityLibrary/src/main/res");
                    Check(r, Hash(Path.Combine(nativeResources,"drawable-nodpi/hotr_icon_original99.png")) == Hash("Assets/HeartOfTheRain/App/Launch/Art/App_Icon_R1.png"), "Native icon generation preserves exact approved PNG bytes");
                    Check(r, File.ReadAllText(Path.Combine(gradle,"launcher/src/main/AndroidManifest.xml")).Contains("@mipmap/hotr_launcher_icon99")
                        && File.ReadAllText(Path.Combine(gradle,"unityLibrary/src/main/AndroidManifest.xml")).Contains("@style/HeartRainLaunch99"), "Actual generated Android manifests select safe launcher and black/icon native startup theme");
                    r.bytes = new FileInfo(r.apk).Length; r.apkSHA256 = Hash(r.apk);
                }
                r.status = "PASS_NATIVE_REVIEW100_" + operation.ToUpperInvariant();
            }
            catch (Exception error) { r.error = error.ToString(); }
            if (!string.IsNullOrEmpty(output))
            {
                Directory.CreateDirectory(output);
                using (var file = new FileStream(Path.Combine(output, operation + ".json"), FileMode.CreateNew, FileAccess.Write))
                using (var writer = new StreamWriter(file, new UTF8Encoding(false))) writer.Write(JsonUtility.ToJson(r, true));
            }
            EditorApplication.Exit(r.error == null ? 0 : 1);
        }
        static void ConfigureIcons(Report r)
        {
            var icon = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/HeartOfTheRain/App/Launch/Art/App_Icon_R1.png");
            Check(r, icon, "Exact approved flat icon is imported");
            if (!File.Exists(ClearPath))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(ClearPath));
                var clear = new Texture2D(icon.width, icon.height, TextureFormat.RGBA32, false);
                clear.SetPixels32(new Color32[icon.width * icon.height]); clear.Apply();
                File.WriteAllBytes(ClearPath, clear.EncodeToPNG()); UnityEngine.Object.DestroyImmediate(clear);
                AssetDatabase.ImportAsset(ClearPath, ImportAssetOptions.ForceSynchronousImport);
                var importer = (TextureImporter)AssetImporter.GetAtPath(ClearPath);
                importer.textureType = TextureImporterType.Default; importer.alphaIsTransparency = true;
                importer.mipmapEnabled = false; importer.npotScale = TextureImporterNPOTScale.None;
                importer.textureCompression = TextureImporterCompression.Uncompressed; importer.SaveAndReimport();
            }
            var foreground = AssetDatabase.LoadAssetAtPath<Texture2D>(ClearPath);
            Check(r, foreground, "Transparent technical foreground imported without editing approved artwork");
            // Read the exact installed platform's layer labels; supported
            // SetTextures remains the only configuration mutation. Fail if
            // this engine's actual layer ordering cannot be identified.
            var kind = AndroidPlatformIconKind.Adaptive;
            var property = typeof(PlatformIconKind).GetProperty("customLayerLabels", BindingFlags.Instance | BindingFlags.NonPublic);
            r.adaptiveLabels = property == null ? null : (string[])property.GetValue(kind);
            Check(r, r.adaptiveLabels != null && r.adaptiveLabels.Length >= 2
                && r.adaptiveLabels.Any(s => s == "Background") && r.adaptiveLabels.Any(s => s == "Foreground"), "Actual adaptive background/foreground layer order identified");
            var slots = PlayerSettings.GetPlatformIcons(NamedBuildTarget.Android, kind);
            Check(r, slots.Length > 0 && slots.All(slot => slot.maxLayerCount >= r.adaptiveLabels.Length && slot.minLayerCount <= 2), "Actual Android adaptive slots accept the two approved layers");
            foreach (var slot in slots)
            {
                var layers = new Texture2D[slot.maxLayerCount];
                for (int i = 0; i < r.adaptiveLabels.Length; i++)
                    layers[i] = r.adaptiveLabels[i] == "Background" ? icon : r.adaptiveLabels[i] == "Foreground" ? foreground : null;
                slot.SetTextures(layers);
            }
            PlayerSettings.SetPlatformIcons(NamedBuildTarget.Android, kind, slots);
            // This isolated build targets API26+, where adaptive icons apply.
            // Clear the deprecated legacy assignments through the supported API;
            // the approved source artwork remains unchanged in the adaptive layer.
            var legacyKind = HeartOfTheRain.App.Launch.Editor.LaunchSetup.LegacyIconKind;
            var legacy = PlayerSettings.GetPlatformIcons(NamedBuildTarget.Android, legacyKind);
            foreach (var slot in legacy) slot.SetTextures(new Texture2D[slot.maxLayerCount]);
            PlayerSettings.SetPlatformIcons(NamedBuildTarget.Android, legacyKind, legacy);
        }
        static void Inspect(Report r)
        {
            string tools = Path.GetFullPath(Path.Combine(EditorApplication.applicationContentsPath, "PlaybackEngines", "AndroidPlayer")) + Path.DirectorySeparatorChar;
            r.sdk = Path.GetFullPath(AndroidExternalToolsSettings.sdkRootPath);
            r.jdk = Path.GetFullPath(AndroidExternalToolsSettings.jdkRootPath);
            r.ndk = Path.GetFullPath(AndroidExternalToolsSettings.ndkRootPath);
            r.gradle = Path.GetFullPath(AndroidExternalToolsSettings.Gradle.path);
            Check(r, new[] { r.sdk, r.jdk, r.ndk, r.gradle }.All(path => path.StartsWith(tools, StringComparison.OrdinalIgnoreCase)), "Actual SDK/NDK/JDK/Gradle getters retain this stock matching Editor module");
            r.packageName = PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android);
            r.showSplash = PlayerSettings.SplashScreen.show; r.showUnityLogo = PlayerSettings.SplashScreen.showUnityLogo;
            r.portrait = HeartOfTheRain.App.Editor.PortraitBuildPolicy.IsPortraitOnly;
            r.sdkFree = !PlayerSettings.GetScriptingDefineSymbols(NamedBuildTarget.Android).Split(';').Any(s => s == "HOTR_RUSTORE_PAY" || s == "HOTR_YANDEX_ADS");
            r.enabledScenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
            Check(r, r.packageName == Package && PlayerSettings.companyName == Company, "Distinct98 app and Editor identities retained");
            Check(r, PlayerSettings.productName == "Сердце дождя", "Russian visible product name retained");
            Check(r, !r.showSplash && !r.showUnityLogo && r.portrait, "Native splash disabled and portrait-only policy retained");
            Check(r, r.sdkFree && !PlayerSettings.Android.useCustomKeystore, "SDK-free internal signing scope retained");
            Check(r, PlayerSettings.GetScriptingBackend(NamedBuildTarget.Android) == ScriptingImplementation.IL2CPP && PlayerSettings.Android.targetArchitectures == AndroidArchitecture.ARM64
                && (int)PlayerSettings.Android.minSdkVersion == 26 && (int)PlayerSettings.Android.targetSdkVersion == 36, "ARM64 IL2CPP API26 to36 retained");
            Check(r, PlayerSettings.stripEngineCode && UnityEditor.PackageManager.PackageInfo.GetAllRegisteredPackages().Any(package => package.name == "com.unity.modules.tilemap" && package.version == "1.0.0"), "Stock built-in Tilemap dependency explicitly retained for Unity6 SpriteMask without disabling engine stripping");
            Check(r, r.enabledScenes.SequenceEqual(new[] { HeartOfTheRain.App.Launch.LaunchPage.ScenePath, HeartOfTheRain.App.Launch.LaunchPage.GameScenePath }), "Approved launch/first-start scene order retained");
            var icon = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/HeartOfTheRain/App/Launch/Art/App_Icon_R1.png");
            var legacy = PlayerSettings.GetPlatformIcons(NamedBuildTarget.Android, HeartOfTheRain.App.Launch.Editor.LaunchSetup.LegacyIconKind);
            r.legacySlots = legacy.Length; Check(r, legacy.Length > 0 && legacy.All(s => s.GetTextures().All(t => !t)), "Deprecated legacy assignments cleared for the API26+ adaptive build");
            var adaptive = PlayerSettings.GetPlatformIcons(NamedBuildTarget.Android, AndroidPlatformIconKind.Adaptive);
            var kind = AndroidPlatformIconKind.Adaptive;
            var property = typeof(PlatformIconKind).GetProperty("customLayerLabels", BindingFlags.Instance | BindingFlags.NonPublic);
            r.adaptiveLabels = property == null ? null : (string[])property.GetValue(kind);
            var foreground = AssetDatabase.LoadAssetAtPath<Texture2D>(ClearPath);
            Check(r, icon && foreground && r.adaptiveLabels != null && r.adaptiveLabels.Contains("Background") && r.adaptiveLabels.Contains("Foreground"), "Required adaptive artwork and exact platform layer labels exist");
            r.adaptiveSlots = adaptive.Length; Check(r, adaptive.Length > 0 && adaptive.All(s => {
                var layers = s.GetTextures();
                return layers.Count(t => t) == 2 && layers[Array.IndexOf(r.adaptiveLabels, "Background")] == icon
                    && layers[Array.IndexOf(r.adaptiveLabels, "Foreground")] == foreground;
            }), "Adaptive layers bind unchanged approved background and transparent foreground in the actual platform order");
        }
    }
}
#endif
