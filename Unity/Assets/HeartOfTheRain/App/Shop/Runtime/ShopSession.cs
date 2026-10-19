using System;using System.Linq;
namespace HeartOfTheRain.App.Shop
{
 [Serializable] public sealed class ShopOffer
 {
  public string id,title,section,art,priceLabel;
  public int coins,boostersEach,rockets,bombs,rainbowOrbs,goldenSeekers;
  // Read only when upgrading an unversioned/v1 catalogue. New data uses the four fields above.
  public int powersEach;
  public bool available=true;
  public ShopOffer Copy(){return (ShopOffer)MemberwiseClone();}
  public int StartingCount(int index)
  {switch(index){case 0:return rockets;case 1:return bombs;case 2:return rainbowOrbs;case 3:return goldenSeekers;default:throw new ArgumentOutOfRangeException(nameof(index));}}
 }
 [Serializable] public sealed class ShopCatalog
 {public int schemaVersion;public bool isPreview=true;public ShopOffer[] offers=new ShopOffer[0];}
 // Presentation-only catalogue. No wallet, inventory, timer or purchase mutation.
 public sealed class ShopSession
 {
  ShopCatalog catalog;int specialIndex;
  public string OpenOfferId{get;private set;}="";
  public bool Modal=>OpenOfferId.Length>0;
  public bool IsPreview=>catalog.isPreview;
  public ShopOffer[] Specials=>catalog.offers.Where(o=>o.section=="special").Select(o=>o.Copy()).ToArray();
  public ShopOffer[] Mega=>catalog.offers.Where(o=>o.section=="mega").Select(o=>o.Copy()).ToArray();
  public ShopOffer[] Coins=>catalog.offers.Where(o=>o.section=="coins").Select(o=>o.Copy()).ToArray();
  public int SpecialIndex=>specialIndex;
  public ShopOffer CurrentSpecial=>Specials.Length==0?null:Specials[specialIndex];
  public ShopOffer OpenOffer=>catalog.offers.FirstOrDefault(o=>o.id==OpenOfferId)?.Copy();
  public ShopSession(ShopCatalog value){ApplyCatalog(value);}
  public void ApplyCatalog(ShopCatalog value)
  {
   if(value==null||value.offers==null||value.offers.Length>30||value.schemaVersion<0||value.schemaVersion>2)throw new ArgumentException("Invalid Shop catalogue");
   var copy=value.offers.Select(o=>o?.Copy()).ToArray();
   if(value.schemaVersion<2)
    foreach(var o in copy)if(o!=null){if(o.powersEach<0||o.powersEach>999)throw new ArgumentException("Invalid legacy starting-booster count");o.rockets=o.bombs=o.rainbowOrbs=o.goldenSeekers=o.powersEach;}
   foreach(var o in copy)if(o!=null)o.powersEach=0;
   if(copy.Any(o=>o==null||!Valid(o.id,64)||!Valid(o.title,40)||!Valid(o.art,64)||o.priceLabel==null||o.priceLabel.Length>24||o.priceLabel.Any(char.IsControl)||
      (o.section!="special"&&o.section!="mega"&&o.section!="coins")||o.coins<1||o.coins>10000000||o.boostersEach<0||o.boostersEach>999||
      Enumerable.Range(0,4).Any(i=>o.StartingCount(i)<0||o.StartingCount(i)>999)||
      (o.section=="coins"&&(o.boostersEach!=0||Enumerable.Range(0,4).Any(i=>o.StartingCount(i)!=0)))))throw new ArgumentException("Invalid offer");
   if(copy.Select(o=>o.id).Distinct().Count()!=copy.Length)throw new ArgumentException("Duplicate offer ID");
   catalog=new ShopCatalog{schemaVersion=2,isPreview=value.isPreview,offers=copy};specialIndex=0;OpenOfferId="";
  }
  static bool Valid(string s,int limit){return !string.IsNullOrWhiteSpace(s)&&s.Length<=limit&&!s.Any(char.IsControl);}
  public bool Cycle(int delta)
  {int n=Specials.Length;if(Modal||n<2||delta==0)return false;specialIndex=(int)(((long)specialIndex+delta)%n);if(specialIndex<0)specialIndex+=n;return true;}
  public bool SelectSpecial(int index)
  {if(Modal||index<0||index>=Specials.Length)return false;specialIndex=index;return true;}
  public bool Open(string id)
  {if(Modal||!catalog.offers.Any(o=>o.id==id))return false;OpenOfferId=id;return true;}
  public void Close(){OpenOfferId="";}
  public string Price(ShopOffer o){return o.available&&!string.IsNullOrWhiteSpace(o.priceLabel)?o.priceLabel:"Unavailable";}
 }
}
