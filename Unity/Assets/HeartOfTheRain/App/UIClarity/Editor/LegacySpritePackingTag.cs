#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;

namespace HeartOfTheRain.App.UIClarity
{
    // Keep the existing legacy-tag audit while avoiding the obsolete packing
    // API. Modern SpriteAtlas ownership is checked separately by both callers.
    public static class LegacySpritePackingTag
    {
        public static bool HasTag(TextureImporter importer)
        {
            if (!importer) throw new ArgumentNullException(nameof(importer));
            using (var serialized = new SerializedObject(importer))
            {
                var property = serialized.FindProperty("spritePackingTag");
                if (property != null)
                {
                    if (property.propertyType != SerializedPropertyType.String)
                        throw new InvalidOperationException("Unexpected legacy sprite tag representation");
                    return !string.IsNullOrEmpty(property.stringValue);
                }
            }
            // Engines which removed the serialized importer field may still
            // receive old metadata. Preserve the refusal of any nonempty tag.
            string metadata = AssetDatabase.GetTextMetaFilePathFromAssetPath(importer.assetPath);
            const string prefix = "  spritePackingTag:";
            foreach (string line in File.ReadLines(metadata))
            {
                if (!line.StartsWith(prefix, StringComparison.Ordinal)) continue;
                string value = line.Substring(prefix.Length).Trim();
                return value.Length != 0 && value != "\"\"" && value != "''";
            }
            return false;
        }
    }
}
#endif
