using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.M69
{
    // Explicit check after import; never rewrites current project bindings or code.
    public static class M70PowerupAssetCheck
    {
        [Serializable] sealed class Entry {
            public string name, texture, manifest, resourceTexture, resourceKey, textureSHA256, manifestSHA256;
            public int atlasIndex, width, height;
        }
        [Serializable] sealed class Contract { public Entry[] entries; }
        [Serializable] sealed class Result { public string scope; public bool passed; public string[] errors; }
        static string Hash(string path) {
            using (var sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
        }
        [MenuItem("Heart of the Rain/M70/Validate power-up asset installation")]
        public static void Validate()
        {
            var errors = new List<string>();
            var contractAsset = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/HeartOfTheRain/M69/Data/M70_PowerupContract.json");
            if (contractAsset == null) throw new InvalidOperationException("M70 contract is missing. Import the complete asset package.");
            var contract = JsonUtility.FromJson<Contract>(contractAsset.text);
            var boards = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>("Assets/HeartOfTheRain/M48/M48Chapter01Boards.asset");
            var binding = boards == null ? null : new SerializedObject(boards);
            if (binding == null) errors.Add("Saved M48 board binding is absent; verify the current app's replacement binding manually.");
            foreach (var e in contract.entries)
            {
                foreach (var path in new[] { e.texture, e.resourceTexture })
                {
                    if (!File.Exists(path)) { errors.Add("Missing texture: " + path); continue; }
                    if (Hash(path) != e.textureSHA256) errors.Add("Old or modified texture bytes: " + path);
                    var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                    if (tex == null || tex.width != e.width || tex.height != e.height) errors.Add("Imported atlas dimensions are incorrect: " + path);
                    var importer = AssetImporter.GetAtPath(path) as TextureImporter;
                    if (importer == null) { errors.Add("Missing texture importer: " + path); continue; }
                    if (importer.mipmapEnabled || importer.maxTextureSize < 2048 || importer.filterMode != FilterMode.Bilinear) errors.Add("Texture sampling policy is incorrect: " + path);
                    foreach (var platform in new[] { "Android", "iPhone" })
                    {
                        var settings = importer.GetPlatformTextureSettings(platform);
                        if (!settings.overridden || settings.format != TextureImporterFormat.ASTC_4x4 || settings.maxTextureSize < 2048) errors.Add(platform + " body import policy is incorrect: " + path);
                    }
                }
                if (!File.Exists(e.manifest) || Hash(e.manifest) != e.manifestSHA256) errors.Add("Old or modified frame manifest: " + e.name);
                if (binding == null) continue;
                var manifests = binding.FindProperty("powerManifests");
                var atlases = binding.FindProperty("powerAtlases");
                var resources = binding.FindProperty("powerResources");
                if (manifests == null || manifests.arraySize <= e.atlasIndex || AssetDatabase.GetAssetPath(manifests.GetArrayElementAtIndex(e.atlasIndex).objectReferenceValue) != e.manifest)
                    errors.Add("Incorrect M48 manifest binding: " + e.name);
                var direct = atlases != null && atlases.arraySize > e.atlasIndex ? atlases.GetArrayElementAtIndex(e.atlasIndex).objectReferenceValue : null;
                if (direct != null)
                {
                    var path = AssetDatabase.GetAssetPath(direct);
                    if (path != e.texture && path != e.resourceTexture) errors.Add("Incorrect direct texture binding: " + e.name);
                }
                else if (resources == null || resources.arraySize <= e.atlasIndex || resources.GetArrayElementAtIndex(e.atlasIndex).stringValue != e.resourceKey)
                    errors.Add("Incorrect streamed texture binding: " + e.name);
            }
            var result = new Result {
                scope = "Imported assets and saved M48 binding only; not a device test or proof of the current scene's active binding.",
                passed = errors.Count == 0, errors = errors.ToArray()
            };
            Directory.CreateDirectory("Temp");
            File.WriteAllText("Temp/M70_Powerup_Validation.json", JsonUtility.ToJson(result, true));
            if (result.passed) Debug.Log("M70 asset installation passed. Verify idle motion and live/replay clarity in the active app and on device.");
            else Debug.LogError("M70 asset installation failed:\n" + string.Join("\n", result.errors));
        }
    }
}
