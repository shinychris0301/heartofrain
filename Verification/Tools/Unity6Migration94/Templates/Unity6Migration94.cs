#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Launch;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.M46;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace HeartOfTheRain.Verification
{
    // TEMPLATE: copy only into the approved, ignored Unity 6 project. This file
    // must never be imported into the pinned main Unity project.
    public static class Unity6Migration94
    {
        public const string IsolatedPackage = "com.heartoftherain.unity6review94";
        const string ApprovedName = "Сердце дождя";
        const string OutVariable = "HOTR_UNITY6_94_OUT";
        const string VersionVariable = "HOTR_UNITY6_94_VERSION";
        const string ApkVariable = "HOTR_UNITY6_94_APK";

        [Serializable] public sealed class Check
        {
            public string name;
            public bool passed;
        }

        [Serializable] public sealed class Settings
        {
            public string packageName, productName, companyName, backend, architectures;
            public string orientation, applicationEntry, targetApi;
            public int minApi;
            public int[] legacyIconSizes;
            public string[] legacyIconGuids;
            public bool showSplashScreen, showUnityLogo, portraitOnly;
            public bool bundle, customKeystore, sdkFreeDefines;
            public string[] enabledScenes;
        }

        [Serializable] public sealed class Report
        {
            public int schemaVersion = 1;
            public string status, operation, startedUtc, completedUtc, unity;
            public string expectedUnity, project, error, output, apkSHA256;
            public string scope = "Approved isolated Unity 6 migration only. Native settings getters, imported startup-model routing, and optional internal Android compilation. No main-project migration, license inspection, SDK/provider acceptance, device, visual, startup-latency or production-release certification.";
            public int exitCode = 1, errors, warnings;
            public long bytes;
            public double buildSeconds;
            public string buildResult, buildPackageName;
            public bool nonDevelopmentCompileOnly;
            public string searchIndexPath, searchIndexSHA256, searchSettingsBeforeSHA256, searchSettingsAfterSHA256;
            public long searchIndexBytes;
            public bool searchIndexExistedBefore, searchStayedOutOfPlay;
            public int searchStableTicks;
            public List<string> searchErrors = new List<string>();
            public Settings before, after;
            public List<Check> checks = new List<Check>();
        }

        sealed class MemorySettings : ISettingsStore
        {
            public int stage, complete, writes, flushes;
            public int Read(string key, int fallback) => key == FirstStartSession.StageKey ? stage : key == FirstStartSession.CompleteKey ? complete : fallback;
            public void Write(string key, int value) { writes++; throw new InvalidOperationException("Startup inspection must not write tutorial state."); }
            public void Flush() { flushes++; throw new InvalidOperationException("Startup inspection must not flush tutorial state."); }
        }

        public static void Configure() => Run("Configure", true, null);
        public static void Inspect() => Run("Inspect", false, null);
        public static void BuildDevelopment() => Run("BuildDevelopment", false, false);
        public static void BuildNonDevelopment() => Run("BuildNonDevelopment", false, true);


        [Serializable] sealed class WarmIndexDocument { public string name, type; public string[] roots; public WarmIndexOptions options; }
        [Serializable] sealed class WarmIndexOptions { public bool disabled, types, properties, dependencies; }
        static Report warmSearchReport;
        static string warmSearchOutput, warmSearchIndex, warmSearchSettings, warmSearchStamp;
        static double warmSearchStarted, warmSearchStableSince;
        static int warmSearchStableTicks;

        // Deliberately return to the normal Editor loop without entering Play.
        // Unity's own SearchInit startup callback creates its missing default
        // UserSettings/Search.index. No Search internals, callback suppression,
        // EditorPrefs writes, cache deletion, or exception filtering is used.
        public static void WarmSearch()
        {
            warmSearchReport = new Report {
                status = "FAIL_ISOLATED_UNITY6_94_SEARCH_PREPARATION", operation = "WarmSearch",
                startedUtc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion,
                scope = "Isolated native Unity6 Editor first-use Search preparation outside Play. Normal engine startup creates its default index settings; this method only observes the resulting nonempty JSON and stable idle Editor ticks. Does not prove background indexing completion, app runtime behavior, device startup or production acceptance. No PlayerSettings/search preference/asset/cache mutation is performed by this method."
            };
            try
            {
                string workspace = GuardProject(warmSearchReport);
                warmSearchOutput = GuardReport(workspace, "WarmSearch");
                warmSearchReport.before = ReadSettings();
                CheckThat(warmSearchReport, !EditorApplication.isPlayingOrWillChangePlaymode, "Search first-use preparation begins outside Play");
                warmSearchIndex = Path.Combine(warmSearchReport.project, "UserSettings", "Search.index");
                warmSearchSettings = Path.Combine(warmSearchReport.project, "UserSettings", "Search.settings");
                warmSearchReport.searchIndexPath = "UserSettings/Search.index";
                warmSearchReport.searchIndexExistedBefore = File.Exists(warmSearchIndex);
                warmSearchReport.searchSettingsBeforeSHA256 = OptionalFileHash94(warmSearchSettings);
                RequireSearchStartupEnabled94();
                warmSearchStarted = warmSearchStableSince = EditorApplication.timeSinceStartup;
                warmSearchStamp = null; warmSearchStableTicks = 0;
                warmSearchReport.searchStayedOutOfPlay = true;
                Application.logMessageReceived += WarmSearchLog94;
                EditorApplication.update += WarmSearchTick94;
            }
            catch (Exception error)
            {
                warmSearchReport.error = error.ToString();
                FinishWarmSearch94(false);
            }
        }

        static string OptionalFileHash94(string path)
        {
            if (!File.Exists(path)) return null;
            using (var sha = SHA256.Create())
            using (var stream = File.OpenRead(path)) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }

        static void RequireSearchStartupEnabled94()
        {
            if (!File.Exists(warmSearchSettings)) return;
            string text = File.ReadAllText(warmSearchSettings);
            if (System.Text.RegularExpressions.Regex.IsMatch(text, @"[""']?indexOnEditorStartup[""']?\s*[:=]\s*false\b", System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                throw new InvalidOperationException("Search startup was explicitly disabled; this observer does not change the preference.");
        }

        static void WarmSearchLog94(string message, string stack, LogType type)
        {
            if (type != LogType.Error && type != LogType.Exception && type != LogType.Assert) return;
            warmSearchReport.errors++;
            warmSearchReport.searchErrors.Add(message + "\n" + stack);
        }

        static void WarmSearchTick94()
        {
            try
            {
                if (EditorApplication.timeSinceStartup - warmSearchStarted > 120) throw new TimeoutException("Native Search first-use preparation exceeded 120 seconds.");
                if (warmSearchReport.errors != 0) throw new InvalidOperationException("An unfiltered native Editor error occurred during Search preparation.");
                if (EditorApplication.isPlayingOrWillChangePlaymode) { warmSearchReport.searchStayedOutOfPlay = false; throw new InvalidOperationException("Search preparation must remain outside Play."); }
                if (EditorApplication.isCompiling || EditorApplication.isUpdating || !File.Exists(warmSearchIndex)) { warmSearchStableTicks = 0; return; }
                var info = new FileInfo(warmSearchIndex);
                if (info.Length == 0) { warmSearchStableTicks = 0; return; }
                string stamp = info.Length + ":" + info.LastWriteTimeUtc.Ticks;
                if (stamp != warmSearchStamp) { warmSearchStamp = stamp; warmSearchStableTicks = 0; warmSearchStableSince = EditorApplication.timeSinceStartup; return; }
                warmSearchStableTicks++;
                if (warmSearchStableTicks < 8 || EditorApplication.timeSinceStartup - warmSearchStableSince < .75) return;
                var document = JsonUtility.FromJson<WarmIndexDocument>(File.ReadAllText(warmSearchIndex));
                CheckThat(warmSearchReport, document != null && document.name == "Assets" && (string.IsNullOrEmpty(document.type) || document.type == "asset") && document.roots != null && document.roots.SequenceEqual(new[] { "Assets", "Packages" }) && document.options != null && !document.options.disabled && document.options.types && document.options.properties && document.options.dependencies,
                          "Normal engine startup produced a nonempty valid enabled asset-index JSON document");
                RequireSearchStartupEnabled94();
                warmSearchReport.searchIndexBytes = info.Length;
                warmSearchReport.searchIndexSHA256 = OptionalFileHash94(warmSearchIndex);
                warmSearchReport.searchStableTicks = warmSearchStableTicks;
                CheckThat(warmSearchReport, warmSearchStableTicks >= 8 && warmSearchReport.searchStayedOutOfPlay && warmSearchReport.errors == 0,
                          "Default index settings persist over stable idle Editor ticks without Play or ignored errors");
                FinishWarmSearch94(true);
            }
            catch (Exception error)
            {
                warmSearchReport.error = error.ToString();
                FinishWarmSearch94(false);
            }
        }

        static void FinishWarmSearch94(bool success)
        {
            EditorApplication.update -= WarmSearchTick94;
            Application.logMessageReceived -= WarmSearchLog94;
            warmSearchReport.completedUtc = DateTime.UtcNow.ToString("o");
            warmSearchReport.after = ReadSettings();
            warmSearchReport.searchSettingsAfterSHA256 = string.IsNullOrEmpty(warmSearchSettings) ? null : OptionalFileHash94(warmSearchSettings);
            if (JsonUtility.ToJson(warmSearchReport.before) != JsonUtility.ToJson(warmSearchReport.after)) {
                success = false; warmSearchReport.error = "Native PlayerSettings changed during Search observation.";
            }
            warmSearchReport.exitCode = success && warmSearchReport.errors == 0 ? 0 : 1;
            warmSearchReport.status = warmSearchReport.exitCode == 0 ? "PASS_ISOLATED_UNITY6_94_SEARCH_PREPARATION" : "FAIL_ISOLATED_UNITY6_94_SEARCH_PREPARATION";
            if (warmSearchOutput != null)
                using (var stream = new FileStream(warmSearchOutput, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
                using (var writer = new StreamWriter(stream, new UTF8Encoding(false))) writer.Write(JsonUtility.ToJson(warmSearchReport, true));
            EditorApplication.Exit(warmSearchReport.exitCode);
        }

        static void Run(string operation, bool configure, bool? nonDevelopment)
        {
            var report = new Report
            {
                operation = operation,
                status = "FAIL_ISOLATED_UNITY6_94_" + operation.ToUpperInvariant(),
                startedUtc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion
            };
            string reportPath = null;
            try
            {
                string workspace = GuardProject(report);
                reportPath = GuardReport(workspace, operation);
                report.before = ReadSettings();
                if (configure)
                {
                    // Supported Unity 6 APIs; never change YAML to bypass a
                    // restricted setting and never inspect license data.
                    PlayerSettings.companyName = "HeartOfTheRainUnity6Review94";
                    PlayerSettings.SplashScreen.showUnityLogo = false;
                    PlayerSettings.SplashScreen.show = false;
                    PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, IsolatedPackage);
                    PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
                    PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
                    PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel26;
                    PlayerSettings.Android.targetSdkVersion = AndroidSdkVersions.AndroidApiLevel36;
                    // Preserve the existing UnityPlayerActivity/native bridge
                    // and portrait manifest validator, rather than changing to
                    // Unity 6's optional GameActivity entry point.
                    PlayerSettings.Android.applicationEntry = AndroidApplicationEntry.Activity;
                    PlayerSettings.Android.useCustomKeystore = false;
                    var approvedIcon = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/HeartOfTheRain/App/Launch/Art/App_Icon_R1.png");
                    var iconSizes = PlayerSettings.GetIconSizes(NamedBuildTarget.Android, IconKind.Application);
                    if (!approvedIcon || iconSizes.Length == 0) throw new InvalidOperationException("Approved flat icon and native legacy icon sizes must resolve.");
                    PlayerSettings.SetIcons(NamedBuildTarget.Android, Enumerable.Repeat(approvedIcon, iconSizes.Length).ToArray(), IconKind.Application);
                    EditorUserBuildSettings.buildAppBundle = false;
                    HeartOfTheRain.App.Editor.PortraitBuildPolicy.Configure();
                    AssetDatabase.SaveAssets();
                }
                VerifySettings(report);
                VerifyStartupModels(report);
                if (nonDevelopment.HasValue) Build(report, nonDevelopment.Value);
                report.after = ReadSettings();
                report.status = "PASS_ISOLATED_UNITY6_94_" + operation.ToUpperInvariant();
                report.exitCode = 0;
            }
            catch (Exception ex)
            {
                report.error = ex.ToString();
                try { report.after = ReadSettings(); } catch { }
            }
            finally
            {
                report.completedUtc = DateTime.UtcNow.ToString("o");
                if (reportPath != null)
                {
                    // A previous report must never be overwritten or upgraded
                    // into a passing receipt by a later invocation.
                    using (var stream = new FileStream(reportPath, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
                    using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
                        writer.Write(JsonUtility.ToJson(report, true));
                }
                else Debug.LogError("Isolated migration refused before obtaining a safe fresh report path.");
            }
            if (Application.isBatchMode) EditorApplication.Exit(report.exitCode);
            else if (report.exitCode != 0) throw new InvalidOperationException("Isolated migration inspection/build failed; inspect its native report.");
        }

        static string GuardProject(Report report)
        {
            string project = Path.GetFullPath(Path.Combine(Application.dataPath, "..")).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            var info = new DirectoryInfo(project);
            if (info.Name != "Project" || info.Parent == null || info.Parent.Name != "Unity6Migration94" || info.Parent.Parent == null || info.Parent.Parent.Name != ".verification-cache" || info.Parent.Parent.Parent == null)
                throw new InvalidOperationException("Only .verification-cache/Unity6Migration94/Project is authorized.");
            string workspace = info.Parent.Parent.Parent.FullName;
            if (!File.Exists(Path.Combine(workspace, "AGENTS.md")) || !File.Exists(Path.Combine(workspace, "Unity", "ProjectSettings", "ProjectVersion.txt")))
                throw new InvalidOperationException("Cannot identify the protected main project beside the isolated cache.");
            RejectReparseAncestors(project);
            report.project = project;
            report.expectedUnity = Environment.GetEnvironmentVariable(VersionVariable);
            if (string.IsNullOrWhiteSpace(report.expectedUnity) || !report.expectedUnity.StartsWith("6000.", StringComparison.Ordinal) || report.unity != report.expectedUnity)
                throw new InvalidOperationException("Require exact explicitly pinned Unity 6 version via " + VersionVariable + ".");
            return workspace;
        }

        static string GuardReport(string workspace, string operation)
        {
            string supplied = Environment.GetEnvironmentVariable(OutVariable);
            if (string.IsNullOrWhiteSpace(supplied) || !Path.IsPathRooted(supplied))
                throw new InvalidOperationException("Absolute explicit " + OutVariable + " required.");
            string directory = Path.GetFullPath(supplied);
            RequireChild(Path.Combine(workspace, "Verification", "Evidence"), directory);
            RejectReparseAncestors(directory);
            Directory.CreateDirectory(directory);
            string result = Path.Combine(directory, operation + ".json");
            if (File.Exists(result)) throw new InvalidOperationException("Native report already exists; use a fresh output directory.");
            return result;
        }

        static void RequireChild(string parent, string child)
        {
            string prefix = Path.GetFullPath(parent).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!Path.GetFullPath(child).StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Output path is outside its authorized parent.");
        }

        static void RejectReparseAncestors(string path)
        {
            for (var node = new DirectoryInfo(path); node != null; node = node.Parent)
                if (node.Exists && (node.Attributes & FileAttributes.ReparsePoint) != 0)
                    throw new InvalidOperationException("Reparse-point paths are not accepted for isolated migration.");
        }

        static Settings ReadSettings()
        {
            string[] defines = PlayerSettings.GetScriptingDefineSymbols(NamedBuildTarget.Android).Split(';');
            return new Settings
            {
                packageName = PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android),
                productName = PlayerSettings.productName,
                companyName = PlayerSettings.companyName,
                backend = PlayerSettings.GetScriptingBackend(NamedBuildTarget.Android).ToString(),
                architectures = PlayerSettings.Android.targetArchitectures.ToString(),
                minApi = (int)PlayerSettings.Android.minSdkVersion,
                legacyIconSizes = PlayerSettings.GetIconSizes(NamedBuildTarget.Android, IconKind.Application),
                legacyIconGuids = PlayerSettings.GetIcons(NamedBuildTarget.Android, IconKind.Application).Select(t => t ? AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(t)) : "").ToArray(),
                targetApi = PlayerSettings.Android.targetSdkVersion.ToString(),
                applicationEntry = PlayerSettings.Android.applicationEntry.ToString(),
                orientation = PlayerSettings.defaultInterfaceOrientation.ToString(),
                showSplashScreen = PlayerSettings.SplashScreen.show,
                showUnityLogo = PlayerSettings.SplashScreen.showUnityLogo,
                portraitOnly = HeartOfTheRain.App.Editor.PortraitBuildPolicy.IsPortraitOnly,
                bundle = EditorUserBuildSettings.buildAppBundle,
                customKeystore = PlayerSettings.Android.useCustomKeystore,
                sdkFreeDefines = !defines.Contains("HOTR_RUSTORE_PAY") && !defines.Contains("HOTR_YANDEX_ADS"),
                enabledScenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray()
            };
        }

        static void CheckThat(Report report, bool condition, string name)
        {
            report.checks.Add(new Check { name = name, passed = condition });
            if (!condition) throw new InvalidOperationException(name);
        }

        static void VerifySettings(Report report)
        {
            var settings = ReadSettings();
            CheckThat(report, settings.companyName == "HeartOfTheRainUnity6Review94", "Isolated Editor company prevents sharing ordinary main Editor save/preferences");
            CheckThat(report, settings.packageName == IsolatedPackage, "Isolated Android identifier is distinct from the owner's installed app");
            CheckThat(report, settings.productName == ApprovedName, "Approved Russian visible name is unchanged");
            CheckThat(report, !settings.showSplashScreen && !settings.showUnityLogo, "Native Unity 6 splash and Unity logo getters are both disabled");
            CheckThat(report, settings.portraitOnly, "Approved portrait-only policy is retained");
            CheckThat(report, settings.applicationEntry == AndroidApplicationEntry.Activity.ToString(), "Single Activity entry retains existing Android bridges and portrait validator");
            CheckThat(report, settings.backend == ScriptingImplementation.IL2CPP.ToString() && PlayerSettings.Android.targetArchitectures == AndroidArchitecture.ARM64, "Android uses IL2CPP and exactly ARM64");
            CheckThat(report, settings.minApi == 26, "Internal migration APK uses approved API 26 baseline");
            CheckThat(report, PlayerSettings.Android.targetSdkVersion == AndroidSdkVersions.AndroidApiLevel36, "Isolated migration explicitly targets API 36 rather than latest installed SDK");
            CheckThat(report, !settings.bundle && !settings.customKeystore, "Internal APK uses default development signing without private release keys");
            CheckThat(report, settings.sdkFreeDefines, "SDK-free fixture has neither payment nor advertising SDK define enabled");
            string iconGuid = AssetDatabase.AssetPathToGUID("Assets/HeartOfTheRain/App/Launch/Art/App_Icon_R1.png");
            CheckThat(report, settings.legacyIconSizes.Length > 0 && settings.legacyIconGuids.Length == settings.legacyIconSizes.Length && settings.legacyIconGuids.All(g => g == iconGuid), "All native Android legacy icon slots retain the approved flat artwork GUID");
            string[] expectedScenes = { LaunchPage.ScenePath, LaunchPage.GameScenePath };
            CheckThat(report, settings.enabledScenes.SequenceEqual(expectedScenes), "Enabled scenes retain Launch then approved First Start");
            foreach (string scene in expectedScenes)
                CheckThat(report, AssetDatabase.LoadAssetAtPath<SceneAsset>(scene) != null, "Imported startup scene resolves: " + scene);
            CheckThat(report, GameLocale.DefaultIndex == 4 && GameLocale.Codes[GameLocale.DefaultIndex] == "ru" && GameLocale.DisplayIndexAt(0) == 4, "Russian remains missing-preference default and first language row");
            CheckThat(report, GameLocale.ResolveStored(-1) == 4 && GameLocale.ResolveStored(999) == 4, "Invalid stored language resolves to Russian without writing preferences");
            for (int index = 0; index < 5; index++)
                CheckThat(report, GameLocale.ResolveStored(index) == index, "Existing valid saved language index is preserved: " + index);
        }

        static void VerifyStartupModels(Report report)
        {
            var asset = AssetDatabase.LoadAssetAtPath<FirstStartAssets>("Assets/HeartOfTheRain/App/FirstStart/FirstStartAssets.asset");
            CheckThat(report, asset && asset.lessons != null && asset.lessons.Length == 3 && asset.lessons.All(v => v), "Three original imported tutorial lessons resolve");
            LevelData[] lessons = asset.lessons.Select(v => JsonUtility.FromJson<LevelData>(v.text)).ToArray();
            VerifyRoute(report, "Fresh player", new MemorySettings(), lessons, 0, FirstStartStage.Prologue);
            VerifyRoute(report, "Saved rocket lesson", new MemorySettings { stage = (int)FirstStartStage.Rocket }, lessons, 0, FirstStartStage.Rocket);
            VerifyRoute(report, "Returning first-clear progress", new MemorySettings(), lessons, 8, FirstStartStage.Complete);
            VerifyRoute(report, "Completed tutorial without a first clear", new MemorySettings { complete = 1 }, lessons, 0, FirstStartStage.Complete);
        }

        static void VerifyRoute(Report report, string name, MemorySettings settings, LevelData[] lessons, int completed, FirstStartStage expected)
        {
            var session = new FirstStartSession(settings, lessons, completed);
            CheckThat(report, session.Stage == expected, name + " selects its original tutorial/Home model route");
            CheckThat(report, settings.writes == 0 && settings.flushes == 0, name + " routing does not alter saved tutorial state");
            if (session.Practice)
            {
                CheckThat(report, session.Board != null && session.Board.Moves > 0, name + " builds the original tutorial model");
                session.Board.Validate();
            }
            else CheckThat(report, session.Board == null, name + " does not allocate an unrelated practice board");
        }

        static void Build(Report report, bool nonDevelopment)
        {
            CheckThat(report, BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Android, BuildTarget.Android), "Editor has matching Android Build Support");
            CheckThat(report, EditorUserBuildSettings.activeBuildTarget == BuildTarget.Android, "Editor was explicitly started for Android");
            string supplied = Environment.GetEnvironmentVariable(ApkVariable);
            if (string.IsNullOrWhiteSpace(supplied) || !Path.IsPathRooted(supplied))
                throw new InvalidOperationException("Absolute explicit " + ApkVariable + " required.");
            string apk = Path.GetFullPath(supplied);
            RequireChild(Path.Combine(report.project, "Builds"), apk);
            RejectReparseAncestors(Path.GetDirectoryName(apk));
            if (!apk.EndsWith(".apk", StringComparison.OrdinalIgnoreCase) || File.Exists(apk))
                throw new InvalidOperationException("Build requires a fresh .apk inside the isolated project's Builds directory.");
            Directory.CreateDirectory(Path.GetDirectoryName(apk));
            report.output = apk;
            string originalPackage = PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android);
            report.nonDevelopmentCompileOnly = nonDevelopment;
            // The established SDK-free non-development compile uses the exact
            // existing internal identifier recognized by the unchanged release
            // guard. This APK is never a candidate for installation. Only the
            // development build uses the separate side-by-side review identity.
            report.buildPackageName = nonDevelopment ? "com.heartoftherain.verification" : IsolatedPackage;
            if (nonDevelopment)
                report.scope += " This non-development APK is compile-only, uses the established original internal verification identifier, and must not be installed or distributed. The production preflight guard remains unchanged. The isolated project's identifier is restored after compilation.";
            try
            {
                if (nonDevelopment)
                    PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, report.buildPackageName);
                CheckThat(report, PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android) == report.buildPackageName, "Native build identifier matches the declared APK scope");
                var build = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                {
                    scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray(),
                    locationPathName = apk,
                    target = BuildTarget.Android,
                    options = nonDevelopment ? BuildOptions.None : BuildOptions.Development | BuildOptions.AllowDebugging
                });
                if (build == null) throw new InvalidOperationException("BuildPipeline did not return a native build report.");
                report.buildResult = build.summary.result.ToString();
                report.errors = (int)build.summary.totalErrors;
                report.warnings = (int)build.summary.totalWarnings;
                report.buildSeconds = build.summary.totalTime.TotalSeconds;
                report.bytes = (long)build.summary.totalSize;
                CheckThat(report, build.summary.result == BuildResult.Succeeded && report.errors == 0, "Native Android BuildReport result is Succeeded with zero errors");
                CheckThat(report, File.Exists(apk) && new FileInfo(apk).Length > 0, "Current build created the requested nonempty APK");
                CheckThat(report, (long)build.summary.totalSize == new FileInfo(apk).Length, "BuildReport byte count matches the resulting APK");
                using (var sha = SHA256.Create())
                using (var stream = File.OpenRead(apk)) report.apkSHA256 = BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
            }
            finally
            {
                PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, originalPackage);
                CheckThat(report, PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android) == IsolatedPackage, "Isolated Android identifier is restored after the native build");
            }
            VerifySettings(report);
        }
    }
}
#endif
