using UnityEngine;
using System.Collections.Generic;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.Profile
{
    [CreateAssetMenu(menuName="Heart of the Rain/App/Profile Assets")]
    public sealed class ProfileAssets:ScriptableObject
    {
        public HomePageAssets home;
        public Font profileFont;
        public HomeSprite[] sprites;
        readonly Dictionary<string,Sprite> presentation=new Dictionary<string,Sprite>();
        public Sprite Find(string id)
        {
            Sprite cached;if(presentation.TryGetValue(id,out cached)&&cached)return cached;
            foreach(var entry in sprites)if(entry.id==id)
            {
                // The manifest's alpha bounds define UV regions, never the display size.
                // Keep existing source textures, GUIDs and importer settings intact.
                Vector4 bounds=Bounds(id);bool card=id=="Ivory";
                if(bounds==Vector4.zero&&!card)return entry.sprite;
                var source=entry.sprite;if(source.packed)throw new System.InvalidOperationException("Profile presentation regions require unpacked source sprites.");
                Rect rect=source.textureRect;
                if(bounds!=Vector4.zero)rect=new Rect(rect.x+bounds.x,rect.y+rect.height-bounds.w,bounds.z-bounds.x,bounds.w-bounds.y);
                var sprite=Sprite.Create(source.texture,rect,new Vector2(.5f,.5f),source.pixelsPerUnit,0,SpriteMeshType.FullRect,card?new Vector4(80,80,80,80):Vector4.zero);
                sprite.name=id+" presentation";sprite.hideFlags=HideFlags.DontSave;presentation[id]=sprite;return sprite;
            }
            throw new System.InvalidOperationException("Missing profile sprite: "+id);
        }
        static Vector4 Bounds(string id)
        {
            switch(id)
            {
                case "FrameGold":return new Vector4(2,2,1105,1068);
                case "FrameSapphire":return new Vector4(2,2,1108,1070);
                case "FrameIvory":return new Vector4(2,1,1109,1069);
                case "FrameRainkeeperGold":return new Vector4(3,5,1250,1213);
                case "FrameLanternSapphire":return new Vector4(0,0,1254,1224);
                case "FrameGardenIvory":return new Vector4(0,2,1254,1235);
                case "Stat_Level":return new Vector4(183,92,1119,1165);
                case "Stat_Chapter":return new Vector4(24,191,1237,1081);
                case "Stat_Progress":return new Vector4(166,75,1109,1137);
                case "Stat_Stars":return new Vector4(100,124,1154,1126);
                default:return Vector4.zero;
            }
        }
        void OnDisable(){foreach(var sprite in presentation.Values)if(sprite){if(Application.isPlaying)Destroy(sprite);else DestroyImmediate(sprite);}presentation.Clear();}
    }
}
