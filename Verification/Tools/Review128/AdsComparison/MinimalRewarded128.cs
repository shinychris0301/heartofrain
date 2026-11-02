using System;
using UnityEngine;
using YandexMobileAds;
using YandexMobileAds.Base;

// Comparison app for the stuck rewarded close. Only the pinned SDK, its demo unit and the
// documented load/show/destroy sequence. No server, journal, consent flow or reward logic.
// Each switch applies one setting our shipping provider sets before it creates the loader.
public sealed class MinimalRewarded128:MonoBehaviour {
    const string Unit="demo-rewarded-yandex";
    static readonly string[] Names={"analytics off","location off","age restricted","consent false","cancel after load","drop loader","show at once"};
    RewardedAdLoader loader;RewardedAd ad;string status="ready";int shown,rewarded,dismissed,failed,mask;
    void Awake(){Application.targetFrameRate=60;Note("ready");}
    void Note(string text){status=text;Debug.Log("HOTRMIN "+text);}
    void Load(){
        if((mask&1)!=0)using(var native=new AndroidJavaClass("com.yandex.mobile.ads.common.YandexAds"))native.CallStatic("setAppAdAnalyticsReporting",false);
        if((mask&2)!=0)YandexAds.SetLocationTracking(false);
        if((mask&4)!=0)YandexAds.SetAgeRestricted(true);
        if((mask&8)!=0)YandexAds.SetUserConsent(false);
        Note("loading mask="+mask);
        if(loader==null)loader=new RewardedAdLoader();
        loader.LoadAd(new AdRequest(Unit),value=>{ad=value;if((mask&16)!=0)loader.CancelLoading();if((mask&32)!=0)loader=null;Note("loaded");if((mask&64)!=0)Show();},failure=>Note("load failed "+failure.Message));
    }
    void Show(){
        if(ad==null){Note("nothing loaded");return;}
        ad.OnAdShown+=(s,e)=>{shown++;Note("OnAdShown");};
        ad.OnAdImpression+=(s,e)=>Note("OnAdImpression");
        ad.OnAdClicked+=(s,e)=>Note("OnAdClicked");
        ad.OnRewarded+=(s,e)=>{rewarded++;Note("OnRewarded "+e.amount+" "+e.type);};
        ad.OnAdFailedToShow+=(s,e)=>{failed++;Note("OnAdFailedToShow "+e.Message);Release();};
        ad.OnAdDismissed+=(s,e)=>{dismissed++;Note("OnAdDismissed");Release();};
        Note("show");ad.Show();
    }
    void Release(){if(ad!=null){ad.Destroy();ad=null;}}
    void OnGUI(){
        GUI.skin.label.fontSize=GUI.skin.button.fontSize=34;
        GUI.Label(new Rect(30,100,660,60),"Minimal Yandex rewarded 128");
        GUI.Label(new Rect(30,170,660,60),status);
        GUI.Label(new Rect(30,240,660,60),"shown "+shown+" rewarded "+rewarded+" dismissed "+dismissed+" failed "+failed);
        if(GUI.Button(new Rect(30,340,660,120),"Load"))Load();
        if(GUI.Button(new Rect(30,500,660,120),"Show"))Show();
        for(int i=0;i<Names.Length;i++)if(GUI.Button(new Rect(30,650+i*95,660,85),((mask&(1<<i))!=0?"ON  ":"off ")+Names[i]))mask^=1<<i;
    }
}
