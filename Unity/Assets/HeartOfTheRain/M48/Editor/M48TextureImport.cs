using UnityEditor;
using UnityEngine;
namespace HeartOfTheRain.M48 {
    // Preserve original atlas coordinates. Resolution reduction would break Sprite.Create rects.
    public sealed class M48TextureImport:AssetPostprocessor {
        void OnPreprocessTexture(){
            if(!assetPath.Contains("/M48/Resources/M48Textures/"))return;
            var importer=(TextureImporter)assetImporter;
            importer.mipmapEnabled=false;importer.isReadable=false;importer.sRGBTexture=true;
            importer.npotScale=TextureImporterNPOTScale.None;importer.alphaIsTransparency=true;
            importer.filterMode=FilterMode.Bilinear;importer.wrapMode=TextureWrapMode.Clamp;
            foreach(var platform in new[]{"Android","iPhone"}){
                var settings=importer.GetPlatformTextureSettings(platform);settings.name=platform;settings.overridden=true;
                settings.maxTextureSize=importer.maxTextureSize;settings.format=TextureImporterFormat.ASTC_6x6;settings.compressionQuality=100;
                importer.SetPlatformTextureSettings(settings);
            }
        }
    }
}
