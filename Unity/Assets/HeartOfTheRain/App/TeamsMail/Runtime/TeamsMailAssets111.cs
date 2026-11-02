using HeartOfTheRain.App.Home;
using UnityEngine;
namespace HeartOfTheRain.App.TeamsMail { public sealed class TeamsMailAssets111 : ScriptableObject { public HomeSprite[] sprites; public Sprite Find(string id) { if(sprites!=null) foreach(var value in sprites) if(value.id==id) return value.sprite; return null; } } }
