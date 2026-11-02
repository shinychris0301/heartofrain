using System;
using UnityEngine;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.App.Profile {
    [Serializable] public sealed class LegacyLevelGraphics117 {
        public int level,width,height;public string config,surface,mask,surfaceSHA256,maskSHA256;
    }
    [Serializable] sealed class LegacyGraphicsManifest117 {public LegacyLevelGraphics117[] entries;}
    // An attempt is bound to the exact source JSON hash, not board dimensions.
    // Retained versions are read-only and never silently replace unknown hashes.
    public static class VersionedLevel117 {
        public static void ValidateGraphics(LegacyLevelGraphics117 graphics,int number,string config){
            if(graphics==null||graphics.level!=number||graphics.config!=config||graphics.width<1||graphics.height<1||
               string.IsNullOrEmpty(graphics.surface)||string.IsNullOrEmpty(graphics.mask)||graphics.surface==graphics.mask||
               !graphics.surface.StartsWith("M48Textures/",StringComparison.Ordinal)||!graphics.mask.StartsWith("M48Textures/",StringComparison.Ordinal))
                throw new InvalidOperationException("Saved board graphics are unavailable");
            var surface=Resources.Load<Texture2D>(graphics.surface);var mask=Resources.Load<Texture2D>(graphics.mask);
            if(!surface||!mask||surface.width!=graphics.width||surface.height!=graphics.height||mask.width!=graphics.width||mask.height!=graphics.height)
                throw new InvalidOperationException("Saved board graphics do not match");
        }
        // A null result uses the active graphics. A historical JSON uses only
        // the matching original pair; a missing binding never silently falls back.
        public static LegacyLevelGraphics117 ResolveGraphics(M46Assets assets,int number,string config){
            if(!assets||assets.levels==null||number<1||number>assets.levels.Length||string.IsNullOrEmpty(config))throw new InvalidOperationException("Saved board configuration is unavailable");
            var current=assets.levels[number-1];if(current&&ProfileJson.Hash(current.text)==config)return null;
            var original=Resources.Load<TextAsset>("HOTR_LegacyLevels117/C01_L"+number.ToString("D3"));
            if(!original||ProfileJson.Hash(original.text)!=config)throw new InvalidOperationException("Saved board configuration is unavailable");
            var text=Resources.Load<TextAsset>("HOTR_LegacyLevels117/Graphics");
            var manifest=text?JsonUtility.FromJson<LegacyGraphicsManifest117>(text.text):null;
            if(manifest==null||manifest.entries==null||manifest.entries.Length!=50)throw new InvalidOperationException("Saved board graphics are unavailable");
            var graphics=manifest.entries[number-1];ValidateGraphics(graphics,number,config);return graphics;
        }
        public static LevelData Resolve(M46Assets assets,int number,string config){
            if(!assets||assets.levels==null||number<1||number>assets.levels.Length||string.IsNullOrEmpty(config))
                throw new InvalidOperationException("Saved board configuration is unavailable");
            var current=assets.levels[number-1];
            TextAsset selected=current&&ProfileJson.Hash(current.text)==config?current:null;
            if(!selected){
                var legacy=Resources.Load<TextAsset>("HOTR_LegacyLevels117/C01_L"+number.ToString("D3"));
                if(legacy&&ProfileJson.Hash(legacy.text)==config)selected=legacy;
            }
            if(!selected)throw new InvalidOperationException("Saved board configuration is unavailable");
            var level=JsonUtility.FromJson<LevelData>(selected.text);
            if(level==null||level.globalLevel!=number||level.id!="C01_L"+number.ToString("D3"))
                throw new InvalidOperationException("Saved board configuration is invalid");
            return level;
        }
    }
}
