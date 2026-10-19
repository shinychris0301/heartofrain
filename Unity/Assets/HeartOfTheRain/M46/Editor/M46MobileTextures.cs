#if UNITY_EDITOR
using System.Linq;using UnityEditor;using UnityEngine;
namespace HeartOfTheRain.M46.Editor {
    public static class M46MobileTextures {
        // Optional device-review preset. PNGs, dimensions and GUIDs stay unchanged.
        // The editor's default imports remain uncompressed for visual comparison.
        [MenuItem("Heart of the Rain/M46/Mobile Textures/Apply ASTC 6x6 Overrides")]
        public static void Apply(){Set(true);}
        [MenuItem("Heart of the Rain/M46/Mobile Textures/Clear Mobile Overrides")]
        public static void Clear(){Set(false);}
        static void Set(bool enable){var a=AssetDatabase.LoadAssetAtPath<M46Assets>("Assets/HeartOfTheRain/M46/M46Assets.asset");var textures=a.powerAtlases.Concat(a.obstacleClips.SelectMany(c=>c.pages)).Concat(a.bodies.Select(b=>b.texture)).Concat(a.surfaces).Distinct().ToArray();int count=0;
            foreach(var texture in textures){string path=AssetDatabase.GetAssetPath(texture);var importer=(TextureImporter)AssetImporter.GetAtPath(path);foreach(string platform in new[]{"Android","iPhone"}){if(!enable){importer.ClearPlatformTextureSettings(platform);continue;}var settings=importer.GetPlatformTextureSettings(platform);settings.name=platform;settings.overridden=true;settings.maxTextureSize=Mathf.Max(importer.maxTextureSize,Mathf.NextPowerOfTwo(Mathf.Max(texture.width,texture.height)));settings.format=TextureImporterFormat.ASTC_6x6;settings.compressionQuality=100;importer.SetPlatformTextureSettings(settings);}importer.SaveAndReimport();count++;}
            Debug.Log("M46: "+(enable?"ASTC 6x6 enabled":"mobile overrides cleared")+" for "+count+" textures. Masks remain uncompressed. Profile and compare on target devices; the review scene loads the full library.");
        }
    }
}
#endif
