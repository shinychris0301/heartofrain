using HeartOfTheRain.App.Localization;
using System;using System.Globalization;using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.Shop
{
 [Serializable] public sealed class ShopFrame
 {public float width,height,viewportY,viewportHeight,carouselX,carouselY,carouselWidth,carouselHeight,carouselStride,carouselOffset;
  public HomeFrame chrome=new HomeFrame(),content=new HomeFrame(),specials=new HomeFrame(),overlay=new HomeFrame();}
 public static class ShopLayout
 {
  public const float OfferHeight=218;
  static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent=""){var e=new HomeElement{id=id,kind=kind,parent=parent,x=x,y=y,width=w,height=h};f.elements.Add(e);return e;}
  static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,string p="",bool slice=false,bool aspect=false){var e=Add(f,id,"sprite",x,y,w,h,p);e.asset=asset;e.sliced=slice;e.preserveAspect=aspect;}
  static void Text(HomeFrame f,string id,string text,float x,float y,float w,float h,int size,string p="",string color="#21465E",bool sub=false,bool left=false){var e=Add(f,id,sub?(left?"leftsubtext":"subtext"):(left?"lefttext":"text"),x,y,w,h,p);e.text=GameLocale.Element(id,text);e.fontSize=size;e.color=color;}
  static void Hit(HomeFrame f,string id,string action,float x,float y,float w,float h,string label,string p=""){var e=Add(f,id,"group",x,y,w,h,p);e.action=action;e.label=GameLocale.T(label);}
  static void Button(HomeFrame f,string id,string action,string label,float x,float y,float w,float h,string p="",string asset="TM_Green",int size=17)
  {Art(f,id+"-art",asset,x,y,w,h,p,true);Text(f,id+"-label",label,x+8,y+4,w-16,h-10,size,p,asset=="LB2_ButtonNeutral"?"#21465E":"#FFFFFF");Hit(f,id,action,x,y,w,h,label,p);}
  static string Number(int n)=>n.ToString("N0",CultureInfo.InvariantCulture);
  static void Rewards(HomeFrame f,string id,ShopOffer o,float x,float y,float w,float h,string p)
  {
   if(o.section=="coins")
   {float coinSize=Math.Min(80,h-30);Art(f,id+"-treasure","RewardCoin",x+(w-coinSize)/2,y,coinSize,coinSize,p,false,true);Text(f,id+"-coins",Number(o.coins)+" coins",x,y+h-28,w,28,24,p);return;}
   float coinW=Math.Min(86,w*.26f),gridX=x+coinW+8,gridW=w-coinW-8,row=h/2,size=Math.Min(40,row-20);
   Art(f,id+"-treasure",o.art,x,y+9,coinW,h-37,p,false,true);
   Text(f,id+"-coins",Number(o.coins),x,y+h-27,coinW,25,coinW<80?19:22,p);
   for(int i=0;i<4;i++)
   {float cell=gridW/4,cx=gridX+i*cell;RewardIconLayout.Tool(f,id+"-tool-"+i,i,cx+(cell-size)/2,y,size,p);Text(f,id+"-tool-count-"+i,"×"+o.boostersEach,cx,y+size+2,cell,16,12,p);}
   float startW=gridW/4;
   for(int i=0;i<4;i++)
   {float bx=gridX+i*startW;RewardIconLayout.StartingBooster(f,id+"-power-"+i,i,bx+(startW-size)/2,y+row,size,p);Text(f,id+"-power-count-"+i,"×"+o.StartingCount(i),bx,y+row+size+2,startW,16,12,p);}
  }
  static void Card(HomeFrame f,ShopSession s,ShopOffer o,float x,float y,float w,string prefix="")
  {
   string id=prefix+"offer-"+o.id;float h=OfferHeight;Add(f,id,"group",x,y,w,h);
   Art(f,id+"-base","SP_Mega",0,0,w,h,id,true);Art(f,id+"-ribbon",o.section=="special"?"SP_Special":"SP_Header",4,4,w-8,33,id,true);
   Text(f,id+"-title",o.title,12,7,w-24,26,w<310?17:19,id,"#FFF3D7");
   Rewards(f,id,o,10,42,w-20,120,id);
   Art(f,id+"-line","SP_Separator",12,167,w-24,1,id);
   Text(f,id+"-caption","Bundle contents",14,175,w-165,31,11,id,"#66808B",true,true);
   Button(f,id+"-view","offer:"+o.id,s.Price(o),w-147,h-49,135,44,id,o.available&&o.priceLabel.Length>0?"TM_Green":"LB2_ButtonNeutral",17);
   f.elements[f.elements.Count-1].label="Preview "+o.title+", "+Number(o.coins)+" coins, "+o.boostersEach+" of each tool and "+o.rockets+" Rockets, "+o.bombs+" Bombs, "+o.rainbowOrbs+" Rainbow Orbs, "+o.goldenSeekers+" Golden Seekers. "+s.Price(o);
  }
  static void CoinRow(HomeFrame f,ShopSession s,ShopOffer o,float x,float y,float w)
  {
   string id="offer-"+o.id;Add(f,id,"group",x,y,w,72);Art(f,id+"-base","SP_Mega",0,0,w,72,id,true);
   Art(f,id+"-coin","RewardCoin",12,11,48,48,id,false,true);Text(f,id+"-amount",Number(o.coins),66,20,w-202,30,w<330?19:22,id,"#21465E",false,true);
   Button(f,id+"-view","offer:"+o.id,s.Price(o),w-126,14,114,44,id,o.available&&o.priceLabel.Length>0?"TM_Green":"LB2_ButtonNeutral",17);
   f.elements[f.elements.Count-1].label="Preview "+Number(o.coins)+" coins. "+s.Price(o);
  }
  static void Empty(HomeFrame f,float x,float y,float w)
  {Art(f,"empty-art","SP_CoinPouch",x+w/2-52,y+30,104,104,"",false,true);Text(f,"empty-title","The market is resting",x,y+155,w,30,23,"","#FFF3D7");Text(f,"empty-detail","Please check back later.",x,y+193,w,25,14,"","#B9D6E5",true);}
  public static ShopFrame Build(float width,float height,ShopSession s,int coinBalance)
  {
   bool wide=width/Math.Max(1,height)>1.4f;var r=new ShopFrame{width=Math.Max(320,width),height=Math.Max(320,height)};
   float w=r.width,h=r.height,dh=MainNavigationLayout.Height(w,h),head=62,cw=Math.Min(w-28,840),cx=(w-cw)/2;
   foreach(var f in new[]{r.chrome,r.overlay}){f.width=w;f.height=h;}r.content.width=w;
   Art(r.chrome,"background","LB2_Background",0,0,w,h);
   Art(r.chrome,"balance-panel","LB2_RowTop",14,11,106,40,"",true);Art(r.chrome,"balance-icon","RewardCoin",18,14,34,34,"",false,true);
   Text(r.chrome,"balance",HomeLayoutEngine.CompactNumber(Math.Max(0,coinBalance)),51,17,61,25,16);
   Text(r.chrome,"title","Shop",126,9,w-252,42,29,"","#FFFFFF");
   r.viewportY=head;r.viewportHeight=Math.Max(44,h-head-dh-22);
   bool columns=cw>=650;float colw=columns?(cw-16)/2:cw,leftY=4,rightY=4,rightX=columns?cx+colw+16:cx;
   var specials=s.Specials;var mega=s.Mega;var coins=s.Coins;
   if(specials.Length>0)
   {
    Text(r.content,"special-heading","Special Offers",cx,leftY,colw,30,23,"","#FFE2A0");leftY+=32;
    r.carouselX=cx;r.carouselY=leftY;r.carouselWidth=colw;r.carouselHeight=OfferHeight;
    float cardW=colw-(specials.Length>1?24:0);r.carouselStride=cardW+10;r.carouselOffset=specials.Length>1?(s.SpecialIndex+1)*r.carouselStride:0;
    int n=specials.Length>1?specials.Length+3:1;r.specials.width=(n-1)*r.carouselStride+cardW;r.specials.height=OfferHeight;
    for(int slot=0;slot<n;slot++){int index=specials.Length>1?(slot-1+specials.Length)%specials.Length:0;Card(r.specials,s,specials[index],slot*r.carouselStride,0,cardW,"slide-"+slot+"-");}
    leftY+=OfferHeight+8;
   }
   if(!columns)rightY=leftY;
   if(mega.Length>0)
   {Text(r.content,"mega-heading","Mega Offers",rightX,rightY,colw,30,23,"","#EDF7FC");rightY+=32;foreach(var o in mega){Card(r.content,s,o,rightX,rightY,colw);rightY+=OfferHeight+12;}}
   float coinsX=columns?cx:rightX,coinsY=columns?leftY+4:rightY+4;
   if(coins.Length>0)
   {Text(r.content,"coins-heading","Coins",coinsX,coinsY,colw,30,23,"","#FFE2A0");coinsY+=36;foreach(var o in coins){CoinRow(r.content,s,o,coinsX,coinsY,colw);coinsY+=80;}}
   if(specials.Length==0&&mega.Length==0&&coins.Length==0){Empty(r.content,cx,8,cw);coinsY=270;}
   r.content.height=Math.Max(r.viewportHeight,Math.Max(coinsY,rightY)+8);
   Text(r.chrome,"preview-note",s.IsPreview?"Shop preview · sample prices":"Purchases currently unavailable",cx,h-dh-23,cw,20,10,"","#B4D2E1",true);
   float dw=Math.Min(w,620);MainNavigationLayout.Add(r.chrome,(w-dw)/2,h-dh,dw,dh,4);
   if(s.Modal)
   {
    var f=r.overlay;var shade=Add(f,"modal-shade","color",0,0,w,h);shade.color="#061423C8";Hit(f,"modal-block","disabled",0,0,w,h,"Offer details");
    bool horizontal=w>=600&&h<500,shortModal=h<430&&!horizontal;float mw=Math.Min(w-24,horizontal?620:370),mh=Math.Min(h-24,horizontal||shortModal?292:396),mx=(w-mw)/2,my=(h-mh)/2;string p="detail";var offer=s.OpenOffer;
    Add(f,p,"group",mx,my,mw,mh);Art(f,"detail-base","LB2_Dialog",0,0,mw,mh,p,true);
    Text(f,"detail-title",offer.title,18,18,mw-90,30,23,p,"#21465E",false,true);
    Art(f,"detail-close-art","TM_Close",mw-57,10,44,44,p,false,true);Hit(f,"detail-close","close",mw-57,10,44,44,"Close offer details",p);
    Text(f,"detail-kicker","Offer contents",18,49,mw-36,21,12,p,"#69818E",true,true);
    float rw=horizontal?350:mw-36;Rewards(f,"detail-rewards",offer,18,shortModal?75:80,rw,shortModal?88:126,p);
    if(shortModal)
    {
     Text(f,"detail-price",s.Price(offer),18,169,110,30,24,p);
     Text(f,"detail-price-note",s.IsPreview?"Sample price":"Store unavailable",18,201,110,18,10,p,"#69818E",true);
     Text(f,"detail-status-1","Purchases are not available",141,175,mw-159,18,11,p,"#58778A",true);
     Text(f,"detail-status-2",s.IsPreview?"in this preview.":"Please try again later.",141,193,mw-159,18,11,p,"#58778A",true);
     Button(f,"detail-back","close","Back to Shop",18,mh-62,mw-36,48,p,"LB2_TabActive",16);
    }
    else
    {
     float fx=horizontal?390:18,fw=horizontal?mw-410:mw-36,fy=horizontal?77:mh-177;
     Text(f,"detail-price",s.Price(offer),fx,fy,fw,34,27,p);
     Text(f,"detail-price-note",s.IsPreview?"Sample price":"Store unavailable",fx,fy+35,fw,20,11,p,"#69818E",true);
     Text(f,"detail-status-1","Purchases are not available",fx,fy+65,fw,19,12,p,"#58778A",true);
     Text(f,"detail-status-2",s.IsPreview?"in this preview.":"Please try again later.",fx,fy+84,fw,19,12,p,"#58778A",true);
     Button(f,"detail-back","close","Back to Shop",fx,mh-62,fw,48,p,"LB2_TabActive",16);
    }

   }
   return r;
  }
 }
}
