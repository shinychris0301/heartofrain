using System;
using UnityEngine;
using HeartOfTheRain.App.LevelComplete;
namespace HeartOfTheRain.App.Celebrations
{
    [Serializable] public sealed class ChapterCelebrationArt
    {
        public int chapter=1;
        public Sprite restoration, hook;
        public string title="The Village Well";
        public string[] captions={"The village well is restored.","You did it! The well is working again.","A messenger arrives: the Heart of Ancient Moscow is faltering."};
    }
    [CreateAssetMenu(menuName="Heart of the Rain/App/Celebration assets")]
    public sealed class CelebrationAssets:ScriptableObject
    {
        public Texture2D dariaAtlas;
        public Shader dariaBlend;
        public LevelCompleteAssets ui;
        public AudioClip music;
        public ChapterCelebrationArt[] chapters;
        public ChapterCelebrationArt Chapter(int number)
        {return chapters==null?null:Array.Find(chapters,c=>c!=null&&c.chapter==number);}
        public static CelebrationAssets Load() {return Resources.Load<CelebrationAssets>("M67_CelebrationAssets");}
    }
}
