#if UNITY_EDITOR
// Unity 2022.3+ / Unity 6, uGUI. Editor only. No changes to game logic.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.U2D;
using UnityEngine;
using UnityEngine.Sprites;
using UnityEngine.U2D;
using UnityEngine.UI;

namespace HeartOfTheRain.App.UIClarity
{
    [Serializable] public class ClarityEntry
    {
        public string guid, name, path, policy;
        public int width, height;
        public bool mipmaps;
        public bool optional;
    }
    [Serializable] public class ClarityRegistry { public ClarityEntry[] assets; }

    public static class UIClarityGuard
    {
        const string RegistryGuid = "c791449d39b05c10a822cb831902c311";
        const string Menu = "Tools/Heart of the Rain/UI Clarity/";
        static readonly string[] Platforms = { "DefaultTexturePlatform", "Android", "iPhone", "Standalone" };
        static ClarityEntry[] Entries()
        {
            string path = AssetDatabase.GUIDToAssetPath(RegistryGuid);
            if (string.IsNullOrEmpty(path)) throw new InvalidOperationException("UI clarity registry is missing. Reimport the complete patch.");
            var registry = JsonUtility.FromJson<ClarityRegistry>(File.ReadAllText(path));
            if (registry == null || registry.assets == null || registry.assets.Length == 0)
                throw new InvalidOperationException("UI clarity registry is empty or invalid.");
            if (registry.assets.Any(e => e == null || string.IsNullOrEmpty(e.guid) || e.guid.Length != 32 || e.guid.Any(c => !Uri.IsHexDigit(c)) || string.IsNullOrEmpty(e.path) || !e.path.StartsWith("Assets/", StringComparison.Ordinal) || e.width <= 0 || e.height <= 0) || registry.assets.Select(e => e.guid).Distinct().Count() != registry.assets.Length)
                throw new InvalidOperationException("UI clarity registry has invalid or duplicate entries.");
            return registry.assets;
        }
        static string Report(string name, StringBuilder body)
        {
            string dir = Path.Combine("UIClarityReports", DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff"));
            Directory.CreateDirectory(dir);
            string path = Path.Combine(dir, name);
            File.WriteAllText(path, body.ToString());
            Debug.Log("UI clarity report: " + Path.GetFullPath(path));
            return dir;
        }
        static IEnumerable<string> Owners(string path)
        {
            foreach (string guid in AssetDatabase.FindAssets("t:SpriteAtlas"))
            {
                string ap = AssetDatabase.GUIDToAssetPath(guid);
                var atlas = AssetDatabase.LoadAssetAtPath<SpriteAtlas>(ap);
                if (atlas == null) continue;
                var master = atlas.isVariant ? atlas.GetMasterAtlas() : atlas;
                if (master == null) continue;
                foreach (UnityEngine.Object obj in master.GetPackables())
                {
                    string p = AssetDatabase.GetAssetPath(obj);
                    if (p == path || (AssetDatabase.IsValidFolder(p) && path.StartsWith(p + "/", StringComparison.Ordinal)))
                    { yield return ap + (atlas.isVariant ? " [variant]" : ""); break; }
                }
            }
        }

        public static List<string> Validate(out StringBuilder log)
        {
            var problems = new List<string>();
            log = new StringBuilder("UI Clarity / import baseline / " + Application.unityVersion + "\n");
            log.AppendLine("Target: " + EditorUserBuildSettings.activeBuildTarget);
            foreach (var e in Entries())
            {
                string p = AssetDatabase.GUIDToAssetPath(e.guid);
                // A registry may cover both pages while only one page is installed.
                if (string.IsNullOrEmpty(p))
                {
                    if (File.Exists(e.path)) problems.Add(e.path + ": registered GUID changed; restore the supplied metadata or review identity mapping");
                    else if (!e.optional) problems.Add(e.path + ": required registered asset is missing");
                    else log.AppendLine("Not installed (optional): " + e.name);
                    continue;
                }
                var ti = AssetImporter.GetAtPath(p) as TextureImporter;
                if (ti == null) { problems.Add(p + ": not a texture importer"); continue; }
                ti.GetSourceTextureWidthAndHeight(out int w, out int h);
                log.AppendLine(p + " | " + w + "x" + h + " | " + e.policy);
                if (w < e.width || h < e.height) problems.Add(p + ": source resolution below registered master");
                if (ti.textureType != TextureImporterType.Sprite || ti.spriteImportMode != SpriteImportMode.Single)
                    problems.Add(p + ": expected single sprite; review remapping instead of auto-converting");
                if (ti.mipmapEnabled != e.mipmaps || ti.filterMode != (e.mipmaps ? FilterMode.Trilinear : FilterMode.Bilinear))
                    problems.Add(p + ": sampling policy regressed");
                if (ti.mipmapFilter != TextureImporterMipFilter.BoxFilter || ti.mipMapBias != 0)
                    problems.Add(p + ": expected Box mip filter and zero bias");
                if (ti.npotScale != TextureImporterNPOTScale.None || ti.wrapMode != TextureWrapMode.Clamp || !ti.sRGBTexture)
                    problems.Add(p + ": NPOT/wrap/color-space mismatch");
                if (ti.streamingMipmaps) problems.Add(p + ": UI texture streaming enabled");
                if (ti.DoesSourceTextureHaveAlpha() && !ti.alphaIsTransparency) problems.Add(p + ": alpha transparency disabled");
                if (e.name.StartsWith("DG_Card_", StringComparison.Ordinal) || e.name == "DG_Hero_Well.png")
                    if (ti.spriteBorder != Vector4.one * 108) problems.Add(p + ": doubled vector slice border was not migrated");
                if (e.name == "RC_Tab_Active.png" || e.name == "RC_Tabs_Track.png")
                    if (ti.spriteBorder != new Vector4(96, 80, 96, 80)) problems.Add(p + ": Rain Cup tab requires its 32-pixel center strip");
#if UNITY_2022_2_OR_NEWER
                if (e.mipmaps && !ti.ignoreMipmapLimit) problems.Add(p + ": quality setting may discard UI mip levels");
#endif
                if (LegacySpritePackingTag.HasTag(ti)) problems.Add(p + ": legacy packing tag needs separate review");
                foreach (var owner in Owners(p)) problems.Add(p + ": packed atlas requires explicit native validation: " + owner);
                foreach (string platform in Platforms)
                {
                    var ps = platform == "DefaultTexturePlatform" ? ti.GetDefaultPlatformTextureSettings() : ti.GetPlatformTextureSettings(platform);
                    if ((platform != "DefaultTexturePlatform" && !ps.overridden) || ps.maxTextureSize < Math.Max(w, h) ||
                        ps.format != TextureImporterFormat.RGBA32 || ps.crunchedCompression || ps.allowsAlphaSplitting)
                        problems.Add(p + ": " + platform + " does not match the lossless reference baseline");
                }
            }
            log.AppendLine("\nErrors: " + problems.Count);
            foreach (string p in problems) log.AppendLine("ERROR " + p);
            log.AppendLine("This checks registered imports, not live pixel budgets, layout, fonts, render targets or all project assets.");
            return problems;
        }

        [MenuItem(Menu + "1 Audit registered imports")]
        public static void AuditImports()
        { var errors = Validate(out var text); Report("Import_Audit.txt", text); if (errors.Count != 0) Debug.LogError("UI clarity: " + errors.Count + " import errors."); }

        [MenuItem(Menu + "2 Apply registered import baseline")]
        public static void Apply()
        {
            var report = new StringBuilder("Explicit UI clarity apply. Source artwork and sprite geometry are not edited.\n");
            string backup = Report("Apply.txt", report);
            foreach (var e in Entries())
            {
                string p = AssetDatabase.GUIDToAssetPath(e.guid);
                if (string.IsNullOrEmpty(p)) continue;
                var ti = AssetImporter.GetAtPath(p) as TextureImporter;
                if (ti == null || ti.spriteImportMode != SpriteImportMode.Single || ti.textureType != TextureImporterType.Sprite ||
                    LegacySpritePackingTag.HasTag(ti) || Owners(p).Any())
                { report.AppendLine("SKIP atlas/unsupported: " + p); continue; }
                string dest = Path.Combine(backup, "Before", p + ".meta");
                Directory.CreateDirectory(Path.GetDirectoryName(dest)); File.Copy(p + ".meta", dest, true);
                Vector4 border = ti.spriteBorder; Vector2 pivot = ti.spritePivot; float ppu = ti.spritePixelsPerUnit;
                ti.GetSourceTextureWidthAndHeight(out int w, out int h);
                ti.mipmapEnabled = e.mipmaps; ti.mipmapFilter = TextureImporterMipFilter.BoxFilter;
                ti.filterMode = e.mipmaps ? FilterMode.Trilinear : FilterMode.Bilinear; ti.mipMapBias = 0;
                ti.npotScale = TextureImporterNPOTScale.None; ti.wrapMode = TextureWrapMode.Clamp;
                ti.sRGBTexture = true; ti.alphaIsTransparency = ti.DoesSourceTextureHaveAlpha(); ti.streamingMipmaps = false;
#if UNITY_2022_2_OR_NEWER
                ti.ignoreMipmapLimit = true;
#endif
                ti.maxTextureSize = Mathf.Max(32, Mathf.NextPowerOfTwo(Math.Max(w, h)));
                ti.textureCompression = TextureImporterCompression.Uncompressed; ti.crunchedCompression = false;
                foreach (string platform in Platforms)
                {
                    var ps = platform == "DefaultTexturePlatform" ? ti.GetDefaultPlatformTextureSettings() : ti.GetPlatformTextureSettings(platform);
                    ps.name = platform; ps.overridden = platform != "DefaultTexturePlatform";
                    ps.maxTextureSize = ti.maxTextureSize; ps.format = TextureImporterFormat.RGBA32;
                    ps.textureCompression = TextureImporterCompression.Uncompressed; ps.crunchedCompression = false; ps.allowsAlphaSplitting = false;
                    ti.SetPlatformTextureSettings(ps);
                }
                ti.SaveAndReimport();
                if (AssetDatabase.AssetPathToGUID(p) != e.guid || ti.spriteBorder != border || ti.spritePivot != pivot || ti.spritePixelsPerUnit != ppu)
                    throw new InvalidOperationException("Unexpected geometry/identity change: " + p + ". Restore metadata from " + dest);
                report.AppendLine("APPLIED " + p);
            }
            File.WriteAllText(Path.Combine(backup, "Apply.txt"), report.ToString());
            AuditImports();
        }

        static string Hierarchy(Transform t) { return t.parent == null ? t.name : Hierarchy(t.parent) + "/" + t.name; }
        static Vector2 ScreenSize(RectTransform rt, Camera camera)
        {
            var c = new Vector3[4]; rt.GetWorldCorners(c);
            return new Vector2(Vector2.Distance(RectTransformUtility.WorldToScreenPoint(camera, c[0]), RectTransformUtility.WorldToScreenPoint(camera, c[3])),
                               Vector2.Distance(RectTransformUtility.WorldToScreenPoint(camera, c[0]), RectTransformUtility.WorldToScreenPoint(camera, c[1])));
        }
        [MenuItem(Menu + "3 Audit visible UI in Play Mode")]
        public static void AuditLive()
        {
            if (!EditorApplication.isPlaying) { Debug.LogWarning("Enter Play Mode at a fixed native Game-view resolution; open the page and run again."); return; }
            Canvas.ForceUpdateCanvases();
            var log = new StringBuilder("LIVE UI / actual current Game-view pixels / " + Screen.width + "x" + Screen.height + "\n");
            log.AppendLine("Run at idle and peak animation scale. This is not a capture of a physical device.");
            log.AppendLine("Inspect camera/URP render scale, dynamic resolution and postprocessing in the actual project; no global settings are changed.");
            foreach (var canvas in UnityEngine.Object.FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID))
            {
                if (!canvas.isRootCanvas) continue;
                Camera cam = canvas.renderMode == RenderMode.ScreenSpaceOverlay ? null : canvas.worldCamera;
                var scaler = canvas.GetComponent<CanvasScaler>();
                log.AppendLine("CANVAS " + Hierarchy(canvas.transform) + " mode=" + canvas.renderMode + " scale=" + canvas.scaleFactor +
                    " reference=" + (scaler == null ? "none" : scaler.referenceResolution.ToString()) +
                    " cameraTarget=" + (cam != null && cam.targetTexture != null ? cam.targetTexture.width + "x" + cam.targetTexture.height : "screen"));
            }
            foreach (var g in UnityEngine.Object.FindObjectsByType<Graphic>(UnityEngine.FindObjectsSortMode.InstanceID))
            {
                if (!g.isActiveAndEnabled || g.canvas == null) continue;
                Camera camera = g.canvas.renderMode == RenderMode.ScreenSpaceOverlay ? null : g.canvas.worldCamera;
                Vector2 pixels = ScreenSize(g.rectTransform, camera);
                string name = Hierarchy(g.transform);
                Texture texture = g.mainTexture;
                log.AppendLine("\n" + name + " | slot=" + pixels + " | clipped=" + g.canvasRenderer.cull + " | tint=" + g.color + " | shader=" + (g.materialForRendering == null ? "none" : g.materialForRendering.shader.name));
                if (texture == null) continue;
                log.AppendLine("texture=" + texture.name + " " + texture.width + "x" + texture.height + " filter=" + texture.filterMode +
                    " mips=" + (texture is Texture2D t2 ? t2.mipmapCount.ToString() : "render target"));
                var im = g as UnityEngine.UI.Image;
                if (im != null)
                {
                    Sprite sp = im.overrideSprite != null ? im.overrideSprite : im.sprite;
                    if (sp == null) continue;
                    Vector4 uv = DataUtility.GetOuterUV(sp);
                    Vector2 texels = new Vector2(Mathf.Abs(uv.z - uv.x) * texture.width, Mathf.Abs(uv.w - uv.y) * texture.height);
                    if (sp.packed && (sp.packingMode == SpritePackingMode.Tight || sp.packingRotation != SpritePackingRotation.None))
                    { log.AppendLine("REVIEW tight/rotated packing: UV bounding box is approximate; use native pixel comparison."); }
                    if (im.type == UnityEngine.UI.Image.Type.Sliced || im.type == UnityEngine.UI.Image.Type.Tiled)
                    {
                        Vector2 local = g.rectTransform.rect.size;
                        float ratio = Mathf.Min(texels.x / sp.rect.width * im.pixelsPerUnit * im.pixelsPerUnitMultiplier * local.x / Mathf.Max(1, pixels.x),
                                                texels.y / sp.rect.height * im.pixelsPerUnit * im.pixelsPerUnitMultiplier * local.y / Mathf.Max(1, pixels.y));
                        log.AppendLine("SLICED/TILED border texels per display pixel=" + ratio.ToString("F3") + " (unclamped-border estimate)");
                        if (ratio < 1f) log.AppendLine("REVIEW border enlargement; re-export vector source or use a higher-resolution master.");
                        continue;
                    }
                    if (im.preserveAspect && pixels.x > 0 && pixels.y > 0)
                    { float fit = Mathf.Min(pixels.x / sp.rect.width, pixels.y / sp.rect.height); pixels = sp.rect.size * fit; }
                    else if (Mathf.Abs(pixels.x / Mathf.Max(1, pixels.y) - sp.rect.width / sp.rect.height) > .08f)
                        log.AppendLine("REVIEW aspect differs; verify intentional cropping/fill or enable Preserve Aspect.");
                    float density = Mathf.Min(texels.x / Mathf.Max(1, pixels.x), texels.y / Mathf.Max(1, pixels.y));
                    log.AppendLine("UV-region texels=" + texels + " displayed=" + pixels + " texels/display-pixel=" + density.ToString("F3"));
                    if (density < 1f) log.AppendLine("REVIEW source/atlas is enlarged at this size.");
                    if (density > 2f && texture is Texture2D tx && tx.mipmapCount == 1)
                        log.AppendLine("REVIEW substantial minification without mipmaps; detailed artwork can alias.");
                }
                else if (g is RawImage raw)
                {
                    float ratio = Mathf.Min(texture.width * Mathf.Abs(raw.uvRect.width) / Mathf.Max(1, pixels.x), texture.height * Mathf.Abs(raw.uvRect.height) / Mathf.Max(1, pixels.y));
                    log.AppendLine("RAW texels/display-pixel=" + ratio.ToString("F3"));
                }
                else if (g.GetType().FullName.StartsWith("TMPro.", StringComparison.Ordinal))
                {
                    log.AppendLine("TMP: verify SDF material, atlas coverage, fallback pages, padding and native-size legibility. Texture size alone is not a text-quality pass.");
                    foreach (string prop in new[] { "_GradientScale", "_FaceDilate", "_OutlineWidth", "_Softness" })
                        if (g.materialForRendering.HasProperty(prop)) log.AppendLine(prop + "=" + g.materialForRendering.GetFloat(prop));
                }
            }
            Report("Live_UI_Audit.txt", log);
        }
    }

    // Fail closed for known assets only. No automatic asset mutation on import/build.
    public sealed class UIClarityBuildGate : IPreprocessBuildWithReport
    {
        public int callbackOrder { get { return -1000; } }
        public void OnPreprocessBuild(BuildReport report)
        {
            var errors = UIClarityGuard.Validate(out var log);
            Directory.CreateDirectory("UIClarityReports");
            File.WriteAllText("UIClarityReports/Build_Import_Audit.txt", log.ToString());
            if (errors.Count > 0) throw new BuildFailedException("UI clarity baseline failed (" + errors.Count + "). Run Tools > Heart of the Rain > UI Clarity > 1 Audit registered imports. See UIClarityReports/Build_Import_Audit.txt.");
        }
    }
}
#endif
