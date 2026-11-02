#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.U2D;
using UnityEngine;
using UnityEngine.U2D;
using UnityEngine.UI;

namespace HeartOfTheRain.App.Profile.Editor
{
    // Explicit menu actions only. No automatic postprocessor; no dependency on ProfilePage.
    // Unity 2022.3 target. Does not change artwork, GUIDs, sprite rects or runtime layout.
    public static class ProfileClarityTools
    {
        enum Policy { Unknown, Artwork, Interface }
        static readonly HashSet<string> Art = new HashSet<string>(StringComparer.OrdinalIgnoreCase) {
            "Stat_Level_R1", "Stat_Chapter_R1", "Stat_Progress_R1", "Stat_Stars_R1",
            "Banner_Village_R3", "Banner_Lantern_R3", "Banner_Twilight_R3",
            "Frame_Rainkeeper_R1", "Frame_Lantern_R1", "Frame_Garden_R1",
            "Frame_Gold_Approved", "Frame_Sapphire_Approved", "Frame_Ivory_Approved",
            "FrameGold", "FrameSapphire", "FrameIvory", "ProfileChrome", "RenameChrome",
            "Banner_Village", "Banner_Lantern", "Banner_Twilight"
        };
        static readonly HashSet<string> Interface = new HashSet<string>(StringComparer.OrdinalIgnoreCase) {
            "Stat_Card_Ivory", "Stat_Inset", "Avatar_Mask", "RoundMask", "Selection_Check",
            "Tab_Active", "Tab_Inactive", "TabActive", "TabInactive", "Progress_Track", "Progress_Fill",
            "Ivory", "Input", "Primary", "Check", "CheckSource", "Close", "CloseSource", "Pencil", "PencilSource", "Team"
        };
        const string Menu = "Heart of the Rain/Profile Clarity/";
        static Policy Classify(string path, int w, int h)
        {
            var name = Path.GetFileNameWithoutExtension(path);
            if (Art.Contains(name)) return Policy.Artwork;
            if (name.StartsWith("Avatar_", StringComparison.OrdinalIgnoreCase))
                return Math.Max(w, h) >= 512 ? Policy.Artwork : Policy.Interface;
            return Interface.Contains(name) ? Policy.Interface : Policy.Unknown;
        }

        static string[] SelectedPaths()
        {
            var paths = new HashSet<string>(StringComparer.Ordinal);
            foreach (var item in Selection.objects)
            {
                var p = AssetDatabase.GetAssetPath(item);
                if (!p.StartsWith("Assets/", StringComparison.Ordinal)) continue;
                if (AssetDatabase.IsValidFolder(p))
                    foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { p })) paths.Add(AssetDatabase.GUIDToAssetPath(guid));
                else if (AssetImporter.GetAtPath(p) is TextureImporter) paths.Add(p);
            }
            return paths.OrderBy(p => p).ToArray();
        }

        static List<string> AtlasOwners(string path)
        {
            var owners = new List<string>();
            foreach (var guid in AssetDatabase.FindAssets("t:SpriteAtlas"))
            {
                string atlasPath = AssetDatabase.GUIDToAssetPath(guid);
                var atlas = AssetDatabase.LoadAssetAtPath<SpriteAtlas>(atlasPath);
                if (!atlas) continue;
                foreach (var obj in atlas.GetPackables())
                {
                    string p = AssetDatabase.GetAssetPath(obj);
                    if (p == path || (AssetDatabase.IsValidFolder(p) && path.StartsWith(p + "/", StringComparison.Ordinal)))
                    { owners.Add(atlasPath); break; }
                }
            }
            return owners;
        }

        static string ReportDirectory()
        {
            string path = Path.GetFullPath(Path.Combine(Application.dataPath, "../ProfileClarityReports", DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")));
            Directory.CreateDirectory(path); return path;
        }

        [MenuItem(Menu + "1 Audit selected textures")]
        public static void AuditSelected() { Process(false); }

        [MenuItem(Menu + "2 Apply clarity settings to selected textures")]
        public static void FixSelected() { Process(true); }

        static void Process(bool apply)
        {
            var paths = SelectedPaths();
            if (paths.Length == 0) { Debug.LogWarning("Select the four statistics PNGs or the Profile artwork folder in the Project window."); return; }
            string reportDir = ReportDirectory(); var report = new StringBuilder(); int changed = 0, skipped = 0;
            report.AppendLine("Profile clarity " + (apply ? "apply" : "audit") + " | Unity " + Application.unityVersion);
            report.AppendLine("Target " + EditorUserBuildSettings.activeBuildTarget + "; texture limit " + QualitySettings.globalTextureMipmapLimit);
            report.AppendLine("Native source sizes are retained. RGBA32 is a diagnostic quality baseline, not a final memory budget.");
            foreach (string path in paths)
            {
                var importer = AssetImporter.GetAtPath(path) as TextureImporter;
                if (!importer) continue;
                try
                {
                    importer.GetSourceTextureWidthAndHeight(out int w, out int h);
                    Policy policy = Classify(path, w, h); var atlasOwners = AtlasOwners(path);
                    var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                    report.AppendLine("\n" + path + " | source " + w + "x" + h + " | policy " + policy);
                    report.AppendLine("Imported " + (texture ? texture.width + "x" + texture.height + " " + texture.format + " mips=" + texture.mipmapCount : "not loaded"));
                    report.AppendLine("Before: mipmaps=" + importer.mipmapEnabled + " filter=" + importer.filterMode + " max=" + importer.maxTextureSize + " compression=" + importer.textureCompression);
                    foreach (string platform in new[] { "Android", "iPhone", "Standalone" })
                    {
                        var ps = importer.GetPlatformTextureSettings(platform);
                        report.AppendLine(platform + ": override=" + ps.overridden + " max=" + ps.maxTextureSize + " format=" + ps.format + " compression=" + ps.textureCompression);
                    }
                    if (w < 256 || h < 128) report.AppendLine("Review pixel budget: compact source may need larger ORIGINAL artwork if upscaled on high-density devices.");
                    if (policy == Policy.Unknown || atlasOwners.Count > 0 || HeartOfTheRain.App.UIClarity.LegacySpritePackingTag.HasTag(importer) || importer.spriteImportMode == SpriteImportMode.Multiple)
                    {
                        skipped++;
                        report.AppendLine("SKIPPED: unknown name, packed texture, legacy packing tag or multisprite sheet. Preserve atlas/slice configuration.");
                        foreach (string owner in atlasOwners) report.AppendLine("ATLAS OWNER: " + owner + " (review its effective filter, mipmaps, platform format, padding and variant scale)");
                        continue;
                    }
                    if (!apply) { report.AppendLine("Eligible for explicit apply."); continue; }
                    if (importer.textureType != TextureImporterType.Sprite && importer.textureType != TextureImporterType.Default)
                    { skipped++; report.AppendLine("SKIPPED: unsupported texture type."); continue; }
                    // Back up exact metadata before changes. The source PNG is never touched.
                    string backup = Path.Combine(reportDir, "Before", path + ".meta");
                    Directory.CreateDirectory(Path.GetDirectoryName(backup)); File.Copy(path + ".meta", backup, true);
                    string guidBefore = AssetDatabase.AssetPathToGUID(path);
                    Vector4 borderBefore = importer.spriteBorder;
                    var settings = new TextureImporterSettings(); importer.ReadTextureSettings(settings);
                    bool mipmaps = policy == Policy.Artwork && Math.Max(w, h) >= 512 && borderBefore == Vector4.zero;
                    settings.mipmapEnabled = mipmaps;
                    settings.mipmapFilter = TextureImporterMipFilter.BoxFilter;
                    settings.filterMode = mipmaps ? FilterMode.Trilinear : FilterMode.Bilinear;
                    settings.mipmapBias = 0;
                    settings.ignoreMipmapLimit = true;
                    settings.npotScale = TextureImporterNPOTScale.None;
                    settings.wrapMode = TextureWrapMode.Clamp;
                    importer.SetTextureSettings(settings);
                    importer.alphaIsTransparency = importer.DoesSourceTextureHaveAlpha();
                    importer.sRGBTexture = true;
                    importer.streamingMipmaps = false;
                    int maxSize = Mathf.Max(importer.maxTextureSize, Mathf.NextPowerOfTwo(Mathf.Max(w, h)));
                    importer.maxTextureSize = maxSize;
                    importer.textureCompression = TextureImporterCompression.Uncompressed;
                    importer.crunchedCompression = false;
                    var defaults = importer.GetDefaultPlatformTextureSettings();
                    defaults.maxTextureSize = maxSize; defaults.format = TextureImporterFormat.RGBA32;
                    defaults.textureCompression = TextureImporterCompression.Uncompressed; defaults.crunchedCompression = false;
                    importer.SetPlatformTextureSettings(defaults);
                    foreach (string platform in new[] { "Android", "iPhone", "Standalone" })
                    {
                        var ps = importer.GetPlatformTextureSettings(platform);
                        ps.name = platform; ps.overridden = true; ps.maxTextureSize = Mathf.Max(ps.maxTextureSize, maxSize);
                        ps.format = TextureImporterFormat.RGBA32; ps.textureCompression = TextureImporterCompression.Uncompressed;
                        ps.crunchedCompression = false; ps.allowsAlphaSplitting = false;
                        importer.SetPlatformTextureSettings(ps);
                    }
                    importer.SaveAndReimport();
                    if (AssetDatabase.AssetPathToGUID(path) != guidBefore || importer.spriteBorder != borderBefore)
                        throw new InvalidOperationException("GUID or sprite border unexpectedly changed. Restore the metadata backup.");
                    changed++;
                    report.AppendLine("APPLIED: mipmaps=" + mipmaps + ", filter=" + importer.filterMode + ", uncompressed platform baselines. GUID/border preserved.");
                }
                catch (Exception e) { skipped++; report.AppendLine("ERROR: " + e); Debug.LogError("Profile clarity: " + path + "\n" + e.Message); }
            }
            report.AppendLine("\nApplied " + changed + "; skipped/errors " + skipped + ". Native game-view comparison and device rebuild are still required.");
            string file = Path.Combine(reportDir, "Texture_Audit.txt"); File.WriteAllText(file, report.ToString());
            Debug.Log("Profile clarity report: " + file + " | applied " + changed + ", skipped/errors " + skipped);
        }

        [MenuItem(Menu + "3 Audit active Profile graphics in Play Mode")]
        public static void AuditGraphics()
        {
            if (!Application.isPlaying) { Debug.LogWarning("Enter Play Mode and open Profile first."); return; }
            Canvas.ForceUpdateCanvases(); var report = new StringBuilder(); int count = 0;
            report.AppendLine("Active Profile graphics | screen " + Screen.width + "x" + Screen.height + " | Unity " + Application.unityVersion);
            foreach (var graphic in Resources.FindObjectsOfTypeAll<Graphic>())
            {
                if (!graphic.gameObject.scene.IsValid() || !graphic.gameObject.activeInHierarchy) continue;
                var ancestry = new List<string>(); for (Transform t = graphic.transform; t; t = t.parent) ancestry.Add(t.name);
                if (!ancestry.Any(n => n.IndexOf("profile", StringComparison.OrdinalIgnoreCase) >= 0)) continue;
                var im = graphic as Image; var raw = graphic as RawImage;
                if (!im && !raw) continue;
                var sprite = im ? im.overrideSprite : null; var texture = graphic.mainTexture;
                if (!texture) continue;
                var corners = new Vector3[4]; graphic.rectTransform.GetWorldCorners(corners);
                var canvas = graphic.canvas; Camera cam = canvas && canvas.renderMode != RenderMode.ScreenSpaceOverlay ? canvas.worldCamera : null;
                var screenPoints = corners.Select(c => RectTransformUtility.WorldToScreenPoint(cam, c)).ToArray();
                float dw = screenPoints.Max(p => p.x) - screenPoints.Min(p => p.x), dh = screenPoints.Max(p => p.y) - screenPoints.Min(p => p.y);
                float sw = sprite ? sprite.rect.width : texture.width, sh = sprite ? sprite.rect.height : texture.height;
                if (raw) { sw *= Mathf.Abs(raw.uvRect.width); sh *= Mathf.Abs(raw.uvRect.height); }
                var tex2d = texture as Texture2D;
                report.AppendLine("\n" + string.Join("/", ancestry.AsEnumerable().Reverse()));
                report.AppendLine("Source region=" + sw + "x" + sh + "; slot physical pixels=" + dw.ToString("F1") + "x" + dh.ToString("F1") + "; canvas scale=" + (canvas ? canvas.scaleFactor.ToString("F3") : "none"));
                report.AppendLine("Texture=" + texture.name + " " + texture.width + "x" + texture.height + " filter=" + texture.filterMode + " mips=" + (tex2d ? tex2d.mipmapCount : 0) + "; material=" + graphic.materialForRendering.name + "; tint=" + graphic.color);
                if (sprite && sprite.packed) report.AppendLine("PACKED: effective runtime atlas must be inspected.");
                if (dw > sw * 1.2f || dh > sh * 1.2f) report.AppendLine("CHECK UPSCALING: slot exceeds source region (preserve-aspect may reduce actual visible size).");
                if (Mathf.Max(sw / Mathf.Max(1, dw), sh / Mathf.Max(1, dh)) > 4 && tex2d && tex2d.mipmapCount <= 1)
                    report.AppendLine("CHECK MINIFICATION: more than 4x reduction without mipmaps; sliced panels need separate interpretation.");
                count++;
            }
            report.AppendLine("\nGraphics found=" + count + ". Inspect final sprite atlas and capture the native framebuffer at 1:1; do not judge a scaled Game-view thumbnail.");
            string file = Path.Combine(ReportDirectory(), "Runtime_Graphics_Audit.txt"); File.WriteAllText(file, report.ToString()); Debug.Log("Profile runtime audit: " + file);
        }
    }
}
#endif
