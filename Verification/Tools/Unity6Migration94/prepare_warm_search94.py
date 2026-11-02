"""Prepare a reviewed template-only Search first-use warmup; never edit/import a project."""
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / 'Verification/Tools/Unity6Migration94/Templates/Unity6Migration94.cs'
OUT = ROOT / 'Verification/Evidence/Unity6Migration94/WarmSearchPreparation/Set02'

FIELDS = '''            public string searchIndexPath, searchIndexSHA256, searchSettingsBeforeSHA256, searchSettingsAfterSHA256;
            public long searchIndexBytes;
            public bool searchIndexExistedBefore, searchStayedOutOfPlay;
            public int searchStableTicks;
            public List<string> searchErrors = new List<string>();
'''

METHODS = '''
        [Serializable] sealed class WarmIndexDocument { public string type; public string[] roots; public WarmIndexOptions options; }
        [Serializable] sealed class WarmIndexOptions { public bool disabled; }
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
            if (System.Text.RegularExpressions.Regex.IsMatch(text, @"[""']?indexOnEditorStartup[""']?\\s*[:=]\\s*false\\b", System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                throw new InvalidOperationException("Search startup was explicitly disabled; this observer does not change the preference.");
        }

        static void WarmSearchLog94(string message, string stack, LogType type)
        {
            if (type != LogType.Error && type != LogType.Exception && type != LogType.Assert) return;
            warmSearchReport.errors++;
            warmSearchReport.searchErrors.Add(message + "\\n" + stack);
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
                CheckThat(warmSearchReport, document != null && document.type == "asset" && document.options != null && !document.options.disabled,
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
'''


def sha(body):
    return hashlib.sha256(body).hexdigest()


def transform(raw):
    text = raw.decode('utf-8-sig')
    newline = '\r\n' if text.count('\r\n') > text.count('\n') / 2 else '\n'
    fields_anchor = '            public Settings before, after;'
    methods_anchor = '        static void Run(string operation, bool configure, bool? nonDevelopment)'
    if 'public static void WarmSearch()' in text or text.count(fields_anchor) != 1 or text.count(methods_anchor) != 1:
        raise RuntimeError('ExactUnmodifiedWarmSearchAnchorsRequired')
    return text.replace(fields_anchor, FIELDS.replace('\n', newline) + fields_anchor, 1).replace(
        methods_anchor, METHODS.replace('\n', newline) + newline + methods_anchor, 1).encode('utf-8')


def main():
    if OUT.exists():
        raise RuntimeError('ExistingWarmSearchPreparationPreserved')
    before = TEMPLATE.read_bytes()
    after = transform(before)
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / 'Before.cs').write_bytes(before)
    (OUT / 'After.cs').write_bytes(after)
    patch = ''.join(difflib.unified_diff(before.decode('utf-8-sig').splitlines(keepends=True), after.decode('utf-8-sig').splitlines(keepends=True),
        fromfile='Templates/Unity6Migration94.cs before', tofile='Templates/Unity6Migration94.cs proposed WarmSearch only'))
    (OUT / 'WarmSearch.patch').write_text(patch, encoding='utf-8')
    record = {'status': 'PREPARED_WARM_SEARCH94_REQUIRES_ROOT_APPLICATION', 'template': TEMPLATE.relative_to(ROOT).as_posix(),
        'beforeSHA256': sha(before), 'afterSHA256': sha(after), 'runnerSHA256': sha(Path(__file__).read_bytes()),
        'candidateMutated': False, 'mainMutated': False,
        'scope': 'Proposed existing isolated-template augmentation only. No project copy/import, Unity/ADB, Search settings write, global EditorPrefs write, callback suppression, engine patch or cache deletion.',
        'primarySources': ['https://raw.githubusercontent.com/Unity-Technologies/UnityCsReference/master/Modules/QuickSearch/Editor/SearchInit.cs',
            'https://raw.githubusercontent.com/Unity-Technologies/UnityCsReference/master/Modules/QuickSearch/Editor/SearchSettings.cs',
            'https://raw.githubusercontent.com/Unity-Technologies/UnityCsReference/master/Modules/QuickSearch/Editor/Indexing/SearchDatabase.cs']}
    (OUT / 'Preparation.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    if TEMPLATE.read_bytes() != before:
        raise RuntimeError('TemplateChangedDuringReadOnlyPreparation')
    print(json.dumps({'status': record['status'], 'afterSHA256': record['afterSHA256']}), flush=True)


if __name__ == '__main__':
    main()
