#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
namespace HeartOfTheRain.App.Home.Editor
{
    // Scoped to Home: do not change gameplay textures, render pipeline or project color space.
    public sealed class HomeArtImportPolicy : AssetPostprocessor
    {
        private void OnPreprocessTexture()
        {
            if(!assetPath.StartsWith("Assets/HeartOfTheRain/App/Home/Art/",System.StringComparison.Ordinal))return;
            var t=(TextureImporter)assetImporter;
            t.textureType=TextureImporterType.Sprite;t.spriteImportMode=SpriteImportMode.Single;
            t.sRGBTexture=true;t.mipmapEnabled=false;t.alphaIsTransparency=true;
            t.textureCompression=TextureImporterCompression.Uncompressed;t.crunchedCompression=false;
            t.npotScale=TextureImporterNPOTScale.None;t.maxTextureSize=4096;t.filterMode=FilterMode.Bilinear;t.wrapMode=TextureWrapMode.Clamp;
            foreach(string platform in new[]{"Android","iPhone","Standalone"})
            {
                var p=t.GetPlatformTextureSettings(platform);p.overridden=false;t.SetPlatformTextureSettings(p);
            }
        }
        [MenuItem("Heart of the Rain/App/M55/Report Home Color Settings")]
        public static void Report()
        {
            Debug.Log("Home fidelity correction R4. Project color space: "+QualitySettings.activeColorSpace+". Home uses sRGB sprites, uncompressed textures, white image tint and built-in uGUI materials. Compare the review scene at matching aspect ratio and safe area; no project-wide color-space change is applied.");
        }
    }
}
#endif
