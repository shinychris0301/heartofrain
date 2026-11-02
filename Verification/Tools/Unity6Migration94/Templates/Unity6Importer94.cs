#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification
{
    // Read-only probe for the explicitly approved isolated project. No import,
    // SaveAndReimport, asset edit, PlayerSettings or account operation occurs.
    public static class Unity6Importer94
    {
        [Serializable] public sealed class ExpectedRow
        {
            public string path, guid, mainMetaSHA256, candidateMetaSHA256, assetSHA256;
            public int sourceWidth, sourceHeight, alignment, filterMode, wrapU, wrapV, wrapW;
            public bool hasBorder, hasFilter, hasWrapU, hasWrapV, hasWrapW, mipmaps;
            public Vector4 border;
            public Vector2 pivot, effectivePivot;
            public float pixelsPerUnit;
            public long[] referencedSpriteFileIDs;
        }
        [Serializable] public sealed class Expected
        {
            public int schemaVersion, rowsExpected, nonzeroBordersExpected;
            public string authority, mainManifestSHA256;
            public ExpectedRow[] rows;
        }
        [Serializable] public sealed class Preparation
        {
            public string status, expectedPath, expectedSHA256, newFixtureGuid, templateSHA256;
        }
        [Serializable] public sealed class Actual
        {
            public string path, assetGuid, spriteGuid, textureGuid, textureFormat, error;
            public long spriteFileID, textureFileID;
            public int spriteImportMode, spriteCount, sourceWidth, sourceHeight, textureWidth, textureHeight, mipmapCount;
            public int filterMode, wrapU, wrapV, wrapW, alignment, vertices, triangles;
            public Vector4 importerBorder, spriteBorder;
            public Vector2 importerPivot, normalizedSpritePivot;
            public Rect spriteRect;
            public float importerPPU, spritePPU, expectedRuntimePPU;
            public bool runtimePPUWasRescaled;
            public bool importerMipmaps, borderMatchesOriginal, originalReferencedFileIDsPreserved;
        }
        [Serializable] public sealed class Report
        {
            public string status, utc, unity, expectedSHA256, expectedPath, error, correctionSHA256;
            public int checks, rowsExpected, rowsRead, nonzeroBordersExpected, nonzeroBordersRead;
            public bool sourceMetadataUnchanged;
            public List<Actual> rows = new List<Actual>();
            public List<string> failures = new List<string>(), errors = new List<string>();
            public string scope = "Actual read-only Unity6 Editor AssetDatabase/TextureImporter/Sprite/Texture2D readbacks for all438 changed SingleSprite assets, including105 nonzero original sliced borders. Original source metadata/PNG bytes and any existing serialized Sprite local-fileID references are authoritative. No import writes, device pixels, Android frame pacing, all-importer-property equivalence, backend or main promotion acceptance.";
        }
        static Report report;
        static string workspace, project;

        public static void Run()
        {
            string output = Guard();
            report = new Report { status = "FAIL_NATIVE_UNITY6_94_IMPORTER_GEOMETRY", utc = DateTime.UtcNow.ToString("o"), unity = Application.unityVersion };
            try
            {
                var preparation = JsonUtility.FromJson<Preparation>(File.ReadAllText(Path.Combine(workspace, "Verification/Evidence/Unity6Migration94/ImporterPreparation/Report.json")));
                Check(preparation.status == "PREPARED_ISOLATED_READ_ONLY_IMPORTER_PROBE94", "Explicit root preparation receipt");
                string expectedPath = Path.GetFullPath(Path.Combine(workspace, preparation.expectedPath));
                RequireInside(expectedPath, Path.Combine(workspace, ".verification-cache/Unity6Migration94/ImporterExpected"));
                Check(Hash(expectedPath) == preparation.expectedSHA256, "Private expected metadata hash is bound to preparation");
                string self = Path.Combine(Application.dataPath, "HeartOfTheRain/Verification/Editor/Unity6Importer94.cs");
                Check(Hash(self) == ValidatedPPUTemplateHash94(preparation), "Native probe equals root-reviewed corrected template");
                report.expectedSHA256 = preparation.expectedSHA256; report.expectedPath = preparation.expectedPath;
                var expected = JsonUtility.FromJson<Expected>(File.ReadAllText(expectedPath));
                Check(expected.schemaVersion == 1 && expected.authority == "ORIGINAL_MAIN_META_AND_PNG_BYTES94" && expected.rowsExpected == 438
                      && expected.nonzeroBordersExpected == 105 && expected.rows != null && expected.rows.Length == 438
                      && expected.rows.Select(row => row.path).Distinct().Count() == 438, "Complete438 unique original assets and105 sliced borders");
                report.rowsExpected = expected.rowsExpected; report.nonzeroBordersExpected = expected.nonzeroBordersExpected;
                foreach (var row in expected.rows) Read(row);
                Check(report.rowsRead == 438 && report.nonzeroBordersRead == 105, "Every original target and nonzero border read");
                Check(Hash(expectedPath) == preparation.expectedSHA256, "Expected-data file unchanged during native probe");
                report.sourceMetadataUnchanged = !report.failures.Any(value => value.Contains("metadata bytes"));
                if (report.failures.Count == 0 && report.errors.Count == 0) report.status = "PASS_NATIVE_UNITY6_94_IMPORTER_GEOMETRY";
            }
            catch (Exception error) { report.error = error.ToString(); report.errors.Add(error.GetType().Name + ": " + error.Message); }
            finally
            {
                using (var stream = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
                using (var writer = new StreamWriter(stream, new UTF8Encoding(false))) writer.Write(JsonUtility.ToJson(report, true));
                EditorApplication.Exit(report.status.StartsWith("PASS_", StringComparison.Ordinal) ? 0 : 1);
            }
        }

        [Serializable] sealed class PPURuleCorrection94
        {
            public string status, originalPreparationSHA256, templateBeforeSHA256, templateAfterSHA256, expectedPath, expectedSHA256;
        }
        static string ValidatedPPUTemplateHash94(Preparation original)
        {
            string path = Path.Combine(workspace, "Verification/Evidence/Unity6Migration94/ImporterPPUCorrection/Set01/Report.json");
            RequireInside(path, Path.Combine(workspace, "Verification/Evidence/Unity6Migration94/ImporterPPUCorrection"));
            var correction = JsonUtility.FromJson<PPURuleCorrection94>(File.ReadAllText(path));
            string preparation = Path.Combine(workspace, "Verification/Evidence/Unity6Migration94/ImporterPreparation/Report.json");
            Check(correction.status == "APPLIED_EXACT_IMPORTER_PPU_ASSERTION_CORRECTION94"
                  && correction.originalPreparationSHA256 == Hash(preparation)
                  && correction.templateBeforeSHA256 == original.templateSHA256
                  && correction.expectedPath == original.expectedPath && correction.expectedSHA256 == original.expectedSHA256,
                  "Immutable original preparation/expected data and paired-native PPU correction receipt");
            report.correctionSHA256 = Hash(path);
            return correction.templateAfterSHA256;
        }

        static void Read(ExpectedRow expected)
        {
            var actual = new Actual { path = expected.path };
            report.rows.Add(actual);
            try
            {
                if (!expected.path.StartsWith("Assets/", StringComparison.Ordinal) || expected.path.Contains("..") || expected.path.Contains("\\"))
                    throw new InvalidOperationException("Scoped canonical asset path required");
                string candidateAsset = Path.GetFullPath(Path.Combine(project, expected.path));
                string mainAsset = Path.GetFullPath(Path.Combine(workspace, "Unity", expected.path));
                RequireInside(candidateAsset, Application.dataPath);
                RequireInside(mainAsset, Path.Combine(workspace, "Unity/Assets"));
                Check(Hash(mainAsset + ".meta") == expected.mainMetaSHA256, expected.path + " original metadata bytes before read");
                Check(Hash(candidateAsset + ".meta") == expected.candidateMetaSHA256, expected.path + " candidate metadata bytes before read");
                Check(Hash(mainAsset) == expected.assetSHA256 && Hash(candidateAsset) == expected.assetSHA256, expected.path + " exact original PNG bytes");
                var importer = AssetImporter.GetAtPath(expected.path) as TextureImporter;
                var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(expected.path);
                var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(expected.path);
                Check(importer != null && sprite != null && texture != null, expected.path + " importer/Sprite/Texture2D resolve");
                if (importer == null || sprite == null || texture == null) return;
                var settings = new TextureImporterSettings(); importer.ReadTextureSettings(settings);
                actual.spriteImportMode = (int)importer.spriteImportMode;
                actual.assetGuid = AssetDatabase.AssetPathToGUID(expected.path);
                actual.spriteCount = AssetDatabase.LoadAllAssetsAtPath(expected.path).OfType<Sprite>().Count();
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(sprite, out actual.spriteGuid, out actual.spriteFileID);
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(texture, out actual.textureGuid, out actual.textureFileID);
                actual.originalReferencedFileIDsPreserved = expected.referencedSpriteFileIDs.All(value => value == actual.spriteFileID);
                importer.GetSourceTextureWidthAndHeight(out actual.sourceWidth, out actual.sourceHeight);
                actual.importerBorder = importer.spriteBorder; actual.spriteBorder = sprite.border;
                actual.importerPivot = importer.spritePivot; actual.alignment = settings.spriteAlignment;
                actual.importerPPU = importer.spritePixelsPerUnit; actual.spritePPU = sprite.pixelsPerUnit;
                actual.importerMipmaps = importer.mipmapEnabled;
                actual.filterMode = (int)importer.filterMode;
                actual.wrapU = (int)importer.wrapModeU; actual.wrapV = (int)importer.wrapModeV; actual.wrapW = (int)importer.wrapModeW;
                actual.textureWidth = texture.width; actual.textureHeight = texture.height; actual.mipmapCount = texture.mipmapCount;
                actual.textureFormat = texture.format.ToString(); actual.spriteRect = sprite.rect;
                actual.normalizedSpritePivot = new Vector2(sprite.pivot.x / sprite.rect.width, sprite.pivot.y / sprite.rect.height);
                actual.vertices = sprite.vertices.Length; actual.triangles = sprite.triangles.Length / 3;
                actual.borderMatchesOriginal = Near(actual.spriteBorder, expected.border);
                Check(actual.spriteImportMode == (int)SpriteImportMode.Single && actual.spriteCount == 1, expected.path + " remains one SingleSprite");
                Check(actual.assetGuid == expected.guid && actual.spriteGuid == expected.guid && actual.textureGuid == expected.guid
                      && actual.spriteFileID != 0 && actual.textureFileID != 0, expected.path + " original GUID and actual nonzero local IDs");
                Check(actual.originalReferencedFileIDsPreserved, expected.path + " original serialized Sprite local-fileID references resolve");
                Check(actual.sourceWidth == expected.sourceWidth && actual.sourceHeight == expected.sourceHeight, expected.path + " original PNG source dimensions");
                if (expected.hasBorder) Check(Near(actual.importerBorder, expected.border) && actual.borderMatchesOriginal, expected.path + " original importer and runtime Sprite borders");
                Check(Near(actual.importerPivot, expected.pivot) && actual.alignment == expected.alignment
                      && Near(actual.normalizedSpritePivot, expected.effectivePivot), expected.path + " original importer and effective runtime pivot");
                float nativeScale = Mathf.Min(actual.spriteRect.width / actual.sourceWidth, actual.spriteRect.height / actual.sourceHeight);
                actual.runtimePPUWasRescaled = nativeScale > 0f && nativeScale < 1f;
                actual.expectedRuntimePPU = expected.pixelsPerUnit * (actual.runtimePPUWasRescaled ? nativeScale : 1f);
                Check(nativeScale > 0f && Mathf.Abs(actual.importerPPU - expected.pixelsPerUnit) < .001f
                      && Mathf.Abs(actual.spritePPU - actual.expectedRuntimePPU) < .001f,
                      expected.path + " original importer PPU and native downsample-adjusted runtime PPU");
                Check(actual.importerMipmaps == expected.mipmaps, expected.path + " original mipmap switch");
                if (expected.hasFilter) Check(actual.filterMode == expected.filterMode, expected.path + " original filter mode");
                if (expected.hasWrapU) Check(actual.wrapU == expected.wrapU, expected.path + " original U wrap mode");
                if (expected.hasWrapV) Check(actual.wrapV == expected.wrapV, expected.path + " original V wrap mode");
                if (expected.hasWrapW) Check(actual.wrapW == expected.wrapW, expected.path + " original W wrap mode");
                Check(actual.textureWidth > 0 && actual.textureHeight > 0 && actual.mipmapCount >= 1
                      && (expected.mipmaps || actual.mipmapCount == 1), expected.path + " imported texture dimensions and mip count are meaningful");
                if (expected.border != Vector4.zero) report.nonzeroBordersRead++;
                report.rowsRead++;
                Check(Hash(mainAsset + ".meta") == expected.mainMetaSHA256 && Hash(candidateAsset + ".meta") == expected.candidateMetaSHA256,
                      expected.path + " main/candidate metadata bytes unchanged after read");
            }
            catch (Exception error) { actual.error = error.ToString(); report.errors.Add(expected.path + ": " + error.GetType().Name + ": " + error.Message); }
        }

        static bool Near(Vector2 a, Vector2 b) { return Mathf.Abs(a.x - b.x) < .001f && Mathf.Abs(a.y - b.y) < .001f; }
        static bool Near(Vector4 a, Vector4 b) { return Mathf.Abs(a.x-b.x)<.001f && Mathf.Abs(a.y-b.y)<.001f && Mathf.Abs(a.z-b.z)<.001f && Mathf.Abs(a.w-b.w)<.001f; }
        static void Check(bool condition, string message) { report.checks++; if (!condition) report.failures.Add(message); }
        static string Hash(string path)
        {
            RequireNoLinks(path);
            using (var sha = SHA256.Create()) using (var stream = File.OpenRead(path))
                return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }
        static void RequireNoLinks(string path)
        {
            for (var info = new FileInfo(path) as FileSystemInfo; info != null; info = Directory.GetParent(info.FullName))
                if (info.Exists && (info.Attributes & FileAttributes.ReparsePoint) != 0) throw new InvalidOperationException("Linked/reparse path refused");
        }
        static void RequireInside(string path, string parent)
        {
            RequireNoLinks(path);
            if (!Path.GetFullPath(path).StartsWith(Path.GetFullPath(parent).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Path escaped required directory");
        }
        static string Guard()
        {
            project = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            var info = new DirectoryInfo(project);
            if (info.Name != "Project" || info.Parent == null || info.Parent.Name != "Unity6Migration94" || info.Parent.Parent == null || info.Parent.Parent.Name != ".verification-cache")
                throw new InvalidOperationException("Explicit approved isolated project required");
            workspace = info.Parent.Parent.Parent.FullName;
            if (Application.unityVersion != "6000.6.6f1" || Environment.GetEnvironmentVariable("HOTR_UNITY6_94_VERSION") != Application.unityVersion)
                throw new InvalidOperationException("Exact pinned Unity6 required");
            string output = Environment.GetEnvironmentVariable("HOTR_UNITY6_94_OUT");
            if (string.IsNullOrEmpty(output) || !Path.IsPathRooted(output)) throw new InvalidOperationException("Explicit root native output required");
            RequireInside(output, Path.Combine(workspace, "Verification/Evidence/Unity6Migration94"));
            Directory.CreateDirectory(output);
            string path = Path.Combine(output, "Importers.json");
            if (File.Exists(path)) throw new InvalidOperationException("Prior native report preserved");
            return path;
        }
    }
}
#endif
