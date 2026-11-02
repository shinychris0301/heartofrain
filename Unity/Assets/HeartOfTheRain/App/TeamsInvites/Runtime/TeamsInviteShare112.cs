using System;
using System.Text.RegularExpressions;
using UnityEngine;
namespace HeartOfTheRain.App.TeamsInvites {
 // Dormant until a backend supplies an authenticated share URL and the release
 // config supplies its exact HTTPS host. A chooser is not a delivery receipt.
 public static class TeamsInviteShare112 {
  public static bool ValidServerUrl(string url,string approvedHost){
   if(string.IsNullOrWhiteSpace(url)||string.IsNullOrWhiteSpace(approvedHost)||url.Length>2048||approvedHost.Length>253||Uri.CheckHostName(approvedHost)!=UriHostNameType.Dns||approvedHost.EndsWith(".",StringComparison.Ordinal))return false;
   if(!url.StartsWith("https://",StringComparison.OrdinalIgnoreCase)||url.IndexOf('\\')>=0||Regex.IsMatch(url,@"(?i)(/\.{1,2}(/|$)|%2e|%2f|%5c)"))return false;
   Uri parsed;if(!Uri.TryCreate(url,UriKind.Absolute,out parsed)||parsed.Scheme!=Uri.UriSchemeHttps||!parsed.IsDefaultPort||!string.IsNullOrEmpty(parsed.UserInfo)||!string.IsNullOrEmpty(parsed.Fragment))return false;
   return string.Equals(parsed.IdnHost,approvedHost,StringComparison.OrdinalIgnoreCase)&&!url.Contains("\r")&&!url.Contains("\n");
  }
  public static bool CanOffer(string serverUrl,string approvedHost,string publicCode){return ValidServerUrl(serverUrl,approvedHost)&&Regex.IsMatch(publicCode??"","\\A[0-9A-F]{12}\\z");}
  public static bool OpenFromExplicitTap(string serverUrl,string approvedHost,string publicCode,string chooserTitle){
   if(!CanOffer(serverUrl,approvedHost,publicCode)||string.IsNullOrWhiteSpace(chooserTitle)||chooserTitle.Length>100||chooserTitle.IndexOfAny(new[]{'\r','\n','\0'})>=0)return false;
#if UNITY_ANDROID && !UNITY_EDITOR
   try {
    using(var unity=new AndroidJavaClass("com.unity3d.player.UnityPlayer")){
     var activity=unity.GetStatic<AndroidJavaObject>("currentActivity");if(activity==null)return false;
     activity.Call("runOnUiThread",new AndroidJavaRunnable(()=>{try{using(var intent=new AndroidJavaObject("android.content.Intent","android.intent.action.SEND"))using(var intentClass=new AndroidJavaClass("android.content.Intent")){
       intent.Call<AndroidJavaObject>("setType","text/plain");intent.Call<AndroidJavaObject>("putExtra","android.intent.extra.TEXT",publicCode+"\n"+serverUrl);using(var chooser=intentClass.CallStatic<AndroidJavaObject>("createChooser",intent,chooserTitle))activity.Call("startActivity",chooser);
     }}catch(Exception){}finally{activity.Dispose();}}));
     return true;
    }
   }catch(Exception){return false;}
#else
   return false;
#endif
  }
 }
}
