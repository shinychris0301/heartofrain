using System;
using UnityEngine;

namespace HeartOfTheRain.App.Home
{
    [Serializable] public sealed class HomeSprite { public string id; public Sprite sprite; }
    [CreateAssetMenu(menuName = "Heart of the Rain/App/Home Assets")]
    public sealed class HomePageAssets : ScriptableObject
    {
        public Sprite chapterBackground;
        public Font regularFont;
        public Font boldFont;
        public TextAsset layout;
        public TextAsset previewState;
        public HomeSprite[] sprites;
        public Sprite Find(string id)
        {
            if (sprites != null) foreach (var item in sprites) if (item.id == id) return item.sprite;
            throw new InvalidOperationException("Home sprite missing: " + id);
        }
    }
    [Serializable] public sealed class HomeLayout
    {
        public float referenceWidth = 720, referenceHeight = 1280;
        public HomeNode[] nodes;
    }
    [Serializable] public sealed class HomeNode
    {
        public string id, kind, asset, anchor, action, visibility, binding, text, color;
        public float x, y, width, height;
        public int fontSize;
        public bool sliced, bold, shadow;
    }
}
