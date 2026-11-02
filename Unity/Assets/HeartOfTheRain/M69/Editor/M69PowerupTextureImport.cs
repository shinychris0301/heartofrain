using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.M69
{
    // Runs after M48TextureImport, which otherwise forces ASTC 6x6 for all streamed textures.
    // M70 cumulative policy: keep all seven updated body sheets and JSON rects together.
    public sealed class M69PowerupTextureImport : AssetPostprocessor
    {
        static readonly string[] Names = { "RainSeekerBody", "GoldenSeekerBody", "RainbowOrbBody", "DoubleOrbBody", "Rocket_Horizontal", "Rocket_Vertical", "Bomb" };
        static readonly string[] SourceGuids = {
            "12e0128d50b15437ae6eafe7c82414c1", "3dac8f35a8b5585a92c98bee1b615c69",
            "5eef2a176c035fd0baeca7a5401859b7", "5b0fdb43a56f5ef7ad7d0429147349b1", "9089da0404f4518e8e5821eb7bdbc776", "52f8e7ab97045ba2aeb0f90bf4f7d0d3", "d12ae954dcc25f4c8479f650080d7efe"
        };
        static readonly string[] Chapters = { "Chapter01M07", "Chapter01M07", "Chapter01M07", "Chapter01M07", "Chapter01M04", "Chapter01M04", "Chapter01M05" };
        const string Root = "Assets/HeartOfTheRain/";
        public override int GetPostprocessOrder() { return 2000; }
        public override uint GetVersion() { return 2; }

        static bool IsBody(string path)
        {
            for (int i = 0; i < Names.Length; i++)
                if (path == Root + Chapters[i] + "/Sprites/" + Names[i] + "_Atlas.png" ||
                    path == Root + "M48/Resources/M48Textures/" + SourceGuids[i] + ".png") return true;
            return false;
        }

        void OnPreprocessTexture()
        {
            if (!IsBody(assetPath)) return;
            var importer = (TextureImporter)assetImporter;
            importer.maxTextureSize = 2048;
            importer.mipmapEnabled = false;
            importer.streamingMipmaps = false;
            importer.isReadable = false;
            importer.sRGBTexture = true;
            importer.alphaIsTransparency = true;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.filterMode = FilterMode.Bilinear;
            importer.wrapMode = TextureWrapMode.Clamp;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.crunchedCompression = false;
            foreach (var platform in new[] { "Android", "iPhone" })
            {
                var settings = importer.GetPlatformTextureSettings(platform);
                settings.name = platform;
                settings.overridden = true;
                settings.maxTextureSize = 2048;
                settings.format = TextureImporterFormat.ASTC_4x4;
                settings.compressionQuality = 100;
                settings.crunchedCompression = false;
                importer.SetPlatformTextureSettings(settings);
            }
        }

        [MenuItem("Heart of the Rain/M70/Reimport power-up clarity assets")]
        static void Reimport()
        {
            for (int i = 0; i < Names.Length; i++)
            {
                var original = Root + Chapters[i] + "/Sprites/" + Names[i] + "_Atlas.png";
                var streamed = Root + "M48/Resources/M48Textures/" + SourceGuids[i] + ".png";
                if (File.Exists(original)) AssetDatabase.ImportAsset(original, ImportAssetOptions.ForceUpdate);
                if (File.Exists(streamed)) AssetDatabase.ImportAsset(streamed, ImportAssetOptions.ForceUpdate);
            }
            Debug.Log("M70 body sheets reimported. Verify gameplay and replay on the target device.");
        }
    }
}
