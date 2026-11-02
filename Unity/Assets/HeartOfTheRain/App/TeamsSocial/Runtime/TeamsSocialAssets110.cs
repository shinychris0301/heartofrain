using System;
using HeartOfTheRain.App.Home;
using UnityEngine;

namespace HeartOfTheRain.App.TeamsSocial
{
    // Loaded only by the member-chat renderer. Existing Teams and R4 startup
    // assets do not acquire references to the new chat textures.
    [CreateAssetMenu(menuName = "Heart of the Rain/App/Teams Chat Help Assets")]
    public sealed class TeamsSocialAssets110 : ScriptableObject
    {
        public HomeSprite[] sprites;
        public Sprite Find(string id) { if(sprites != null) foreach(var item in sprites) if(item.id == id) return item.sprite; return null; }
        public float SliceMultiplier(float referenceScale) => 1 / Mathf.Max(.001f, .32f * referenceScale);
    }
}
