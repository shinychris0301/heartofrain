#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Teams;
using HeartOfTheRain.App.TeamsLifecycle;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
 public static class TeamsVisual115Verification {
  [Serializable] sealed class Report { public string status="RUNNING",scope,unity; public int checks,cases; public List<string> errors=new List<string>(); }
  static Report report;
  static void Check(bool condition,string message){report.checks++;if(!condition)throw new InvalidOperationException(message);}
  static HomeElement Element(OnlineTeamsFrame82 frame,string id)=>frame.overlay.elements.Single(e=>e.id==id);
  static void ImageRole(OnlineTeamsPage82 page,TeamsAssets assets,string id,string asset){
   var e=Element(page.VerificationFrame,id);Check(e.asset==asset,id+" role");var sprite=assets.Find(asset);Check(sprite,id+" sprite resolves");
   Check(page.VerificationNodes.TryGetValue(id,out var node),id+" node");var image=node.GetComponent<Image>();Check(image&&image.sprite==sprite,id+" uses loaded sprite");
  }
  static void Close(OnlineTeamsPage82 page,TeamsAssets assets,string id,string expectedLabel){
   ImageRole(page,assets,id+"-art","TA_Close_Disc");ImageRole(page,assets,id+"-icon","TA_Icon_Close");
   var element=Element(page.VerificationFrame,id);Check(element.action==id&&element.width>=80&&element.height>=48,id+" target and route");
   Check(element.label==expectedLabel,id+" accessible text");Check(page.VerificationNodes[id].GetComponent<Button>(),id+" actual button");
  }
  static void Prepare(OnlineTeamsPage82 page,Vector2Int size){
   var canvas=page.VerificationCanvas;canvas.renderMode=RenderMode.WorldSpace;canvas.GetComponent<CanvasScaler>().enabled=false;
   float scale=canvas.scaleFactor;var rect=(RectTransform)canvas.transform;rect.anchorMin=rect.anchorMax=rect.pivot=Vector2.one*.5f;
   rect.localPosition=Vector3.zero;rect.localScale=Vector3.one;rect.sizeDelta=new Vector2(size.x/scale,size.y/scale);
  }
  static OnlineTeamsView82 View(string mode){
   const string friend="22222222222222222222222222222222";
   var team=new SocialTeam82{teamId="11111111111111111111111111111111",name="Example team",badgeId="drop",capacity=30,memberCount=2,isMember=true};
   var v=new OnlineTeamsView82{connected=true,team=team,details=team,detailsOpen=true,status="",modal=mode,leaveState113="confirm",leaveTeamName113="Example team",leaveBadge113="drop",inviteNotice112="",inviteQuery112="",inviteReady112=true,mailReady111=true,mailStatus111="",now110=1800000000};
   v.inviteFriends112=new SocialInviteFriends112{teamId=team.teamId,teamName=team.name,badgeId="drop",publicTeamCode="AABBCCDDEEFF",capacity=30,memberCount=2,canInvite=true,nextCursor="",friends=new[]{new SocialInvitableFriend112{friendId=friend,displayName="Friend",inviteState="Ready",inviteId="",completedLevels=8}}};
   v.mailDetail111=new SocialMailMessage111{messageId="33333333333333333333333333333333",title="Team reward",body="Example message",senderLabel="Team",rewardCoins=300,rewardLives=2,claimState="Ready",claimBlockedReason="None",canClaim=true,expiresAtUtc=1800003600};
   if(mode=="mail-detail111"){v.details=null;v.detailsOpen=false;v.tab=0;v.mail110=true;v.mailList111=new SocialMailList111{messages=new[]{v.mailDetail111}};}
   return v;
  }
  static void Case(TeamsAssets assets,int locale,Vector2Int size,string mode,bool pending){
   GameLocale.Select(locale);var root=new GameObject("TeamsVisual115 fixture");var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;
   try {var view=View(mode);view.pending=pending;page.ConfigureViewForVerification(assets,view);page.VerificationViewport(size.x,size.y);
    page.VerificationSafeArea(size.x==360?new Rect(0,20,size.x,size.y-40):new Rect(0,0,size.x,size.y));page.Show();Prepare(page,size);page.VerificationViewport(size.x,size.y);Canvas.ForceUpdateCanvases();
    if(mode=="leave113")Close(page,assets,"leave-close113",TeamsLifecycleText113.T("close_accessibility"));
    else if(mode=="mail-detail111"){
     Close(page,assets,"mail-close",HeartOfTheRain.App.TeamsMail.TeamsMailText111.T("close"));
     ImageRole(page,assets,"mail-detail-crest","TM_Letter_Closed");ImageRole(page,assets,"mail-detail-coin-card","TA_Field");ImageRole(page,assets,"mail-detail-life-card","TA_Field");
     Check(Element(page.VerificationFrame,"mail-detail-coins").text==300.ToString("N0")&&Element(page.VerificationFrame,"mail-detail-lives").text=="2","Actual reward quantities remain intact");
    } else {
     Close(page,assets,"invite-close",HeartOfTheRain.App.TeamsInvites.TeamsInvitesText112.T("close"));
     if(!pending){ImageRole(page,assets,"invite-friend-22222222222222222222222222222222-action-art","TA_Button_Blue");
      var footer=Element(page.VerificationFrame,"invite-footer-close");Check(footer.action=="invite-close"&&footer.height>=48,"Footer closes without sending");}
     else Check(!page.VerificationNodes.ContainsKey("invite-footer-close")&&page.VerificationNodes.ContainsKey("invite-check")&&page.VerificationNodes.ContainsKey("invite-retry"),"Pending recovery keeps footer space");
     var frame=page.VerificationFrame;var subtitle=frame.overlay.elements.FirstOrDefault(e=>e.id=="invite-subtitle");
     if(subtitle!=null){var tabs=Element(frame,"invite-tabs");Check(subtitle.y+subtitle.height<=tabs.y+.01f,"Subtitle and tabs do not overlap");Check(!string.IsNullOrEmpty(subtitle.text),"Subtitle is localized");}
    }
    report.cases++;
   } finally {page.Hide(false);page.ClearViewForVerification();UnityEngine.Object.DestroyImmediate(root);}
  }
  public static void Run(){
   string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW115_OUT")??"../Verification/Evidence/Review115");
   report=new Report{scope="Unity Editor synthetic UGUI roles and targets; not device or live service verification",unity=Application.unityVersion};
   int locale=GameLocale.Current;bool had=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int saved=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);
   try {Check(Application.unityVersion=="2022.3.62f3","Pinned editor");EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
    var assets=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(assets,"Teams assets");
    foreach(int lang in Enumerable.Range(0,5))foreach(var size in new[]{new Vector2Int(360,640),new Vector2Int(390,844),new Vector2Int(720,1600),new Vector2Int(768,1024)}){
     Case(assets,lang,size,"leave113",false);Case(assets,lang,size,"mail-detail111",false);Case(assets,lang,size,"invite",false);Case(assets,lang,size,"invite",true);
    }
   }catch(Exception e){report.errors.Add(e.ToString());}
   finally {GameLocale.Select(locale);if(had)PlayerPrefs.SetInt(GameLocale.PreferenceKey,saved);else PlayerPrefs.DeleteKey(GameLocale.PreferenceKey);
    report.status=report.errors.Count==0?"PASS_NATIVE_TEAMS_VISUAL115":"FAIL_NATIVE_TEAMS_VISUAL115";Directory.CreateDirectory(Path.Combine(output,"Native"));
    File.WriteAllText(Path.Combine(output,"Native","TeamsVisual115.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));}
   EditorApplication.Exit(report.errors.Count==0?0:1);
  }
 }
}
#endif
