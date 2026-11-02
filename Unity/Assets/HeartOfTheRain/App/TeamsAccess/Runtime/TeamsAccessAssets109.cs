using System;
using HeartOfTheRain.App.Home;
using UnityEngine;
namespace HeartOfTheRain.App.TeamsAccess {
 [Serializable] public sealed class TeamsAccessSlice109 {public string id;public float proofScale=.6f;}
 [CreateAssetMenu(menuName="Heart of the Rain/App/Teams Access R4 Assets")]
 public sealed class TeamsAccessAssets109:ScriptableObject {
  public HomeSprite[] sprites;public TeamsAccessSlice109[] slices;
  public Sprite Find(string id){if(sprites!=null)foreach(var item in sprites)if(item.id==id)return item.sprite;return null;}
  public float SliceMultiplier(string id,float referenceScale){float value=.6f;if(slices!=null)foreach(var item in slices)if(item.id==id){value=item.proofScale;break;}return 1/Mathf.Max(.001f,value*referenceScale);}
 }
 public static class TeamsAccessBadges109 {
  public static readonly string[] Ids={"drop","lantern","well","sun","wave","crystal","book","oak","moon","cottage","banners","raincloud"};
  public static bool Valid(string id)=>Array.IndexOf(Ids,id)>=0;
  public static string Resolve(string id)=>Valid(id)?id:"drop";
  public static string Asset(string id)=>"TA_Badge_"+Resolve(id);
 }
}
