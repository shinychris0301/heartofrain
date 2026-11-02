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
using HeartOfTheRain.App.TeamsMail;
using HeartOfTheRain.App.TeamsSocial;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
 public static class TeamsParity118Verification {
  [Serializable] sealed class Report {public string status="RUNNING",unity,scope="Editor-only visual fixtures and UGUI hierarchy; no live backend or Android claim";public int checks,cases;public List<string> captures=new List<string>(),errors=new List<string>();}
  static Report report;static string output;
  static void Check(bool value,string message){report.checks++;if(!value)throw new InvalidOperationException(message);}
  static HomeElement Element(HomeFrame frame,string id)=>frame.elements.Single(e=>e.id==id);
  static void RewardTileInside(IReadOnlyDictionary<string,RectTransform> nodes,string cardId,params string[] children){
   var card=nodes[cardId];var bounds=card.rect;
   foreach(var id in children){
    var child=nodes[id];var corners=new Vector3[4];child.GetWorldCorners(corners);
    Check(corners.All(point=>{var local=card.InverseTransformPoint(point);return local.x>=bounds.xMin-.5f&&local.x<=bounds.xMax+.5f&&local.y>=bounds.yMin-.5f&&local.y<=bounds.yMax+.5f;}),"Reward tile element fits painted art card: "+id);
    var label=child.GetComponent<Text>();if(!label)continue;var mesh=label.canvasRenderer.GetMesh();Check(mesh&&mesh.vertexCount>0,"Reward tile label emits glyphs: "+id);
    Check(mesh.vertices.All(point=>{var local=card.InverseTransformPoint(child.TransformPoint(point));return local.x>=bounds.xMin+4&&local.x<=bounds.xMax-4&&local.y>=bounds.yMin+4&&local.y<=bounds.yMax-4;}),"Reward tile label glyphs have a visible inset: "+id);
   }
  }
  static SocialTeam82 Team()=>new SocialTeam82{teamId=new string('1',32),ownerId=new string('2',32),name="Хранители дождя",description="Восстанавливаем деревню вместе. Помогаем друг другу каждый день.",badgeId="drop",memberCount=3,capacity=30,isMember=true,members=new[]{new SocialTeamMember82{playerId=new string('3',32),displayName="Иван",isOwner=false},new SocialTeamMember82{playerId=new string('2',32),displayName="Дарья",isOwner=true}}};
  static OnlineTeamsView82 View(string state){
   var team=Team();var v=new OnlineTeamsView82{connected=true,selfId=new string('3',32),team=team,details=team,detailsOpen=true,tab=1,modal="",status="",now110=1800000000};
   if(state=="Reward"){
    v.details=null;v.detailsOpen=false;v.tab=0;v.mail110=true;v.mailReady111=true;v.modal="mail-detail111";
    v.mailDetail111=new SocialMailMessage111{messageId=new string('4',32),teamId=team.teamId,senderLabel="Ведущий",title="Server title",body="Команда вернула свет. Ваша <b>награда</b> готова! 2 < 3 и 4 > 1.",rewardCoins=300,rewardLives=2,claimState="Ready",claimBlockedReason="None",canClaim=true,expiresAtUtc=1800003600};
    v.mailList111=new SocialMailList111{messages=new[]{v.mailDetail111}};
   } else if(state=="Invite"||state=="InviteSafe"){
    v.modal="invite";v.inviteReady112=true;
    v.inviteFriends112=new SocialInviteFriends112{teamId=team.teamId,teamName=team.name,badgeId="drop",publicTeamCode="RAIN7",memberCount=3,capacity=30,canInvite=true,friends=new[]{
     new SocialInvitableFriend112{friendId=new string('5',32),displayName="Мира",completedLevels=125,inviteState="Ready"},
     new SocialInvitableFriend112{friendId=new string('6',32),displayName="Лео",completedLevels=83,inviteState="Ready"},
     new SocialInvitableFriend112{friendId=new string('7',32),displayName="София",completedLevels=216,inviteState="Member"}}};
   } else if(state=="Leave"||state=="LeaveSafe"){
    v.modal="leave113";v.leaveState113="confirm";v.leaveTeamName113=team.name;v.leaveBadge113=team.badgeId;
   } else if(state=="DetailJoin"){
    team.isMember=false;team.members=null;v.details=team;
   } else if(state=="Chat"){
    v.details=null;v.detailsOpen=false;v.tab=0;v.chat=new SocialMessages82{messages=new[]{new SocialMessage82{messageId=new string('8',32),authorId=new string('2',32),displayName="Дарья",text="Помощь <b>готова</b>. 2 < 3 и 4 > 1.",createdAt=1799999950}}};
   }
   return v;
  }
  static void Prepare(OnlineTeamsPage82 page,Vector2Int size){var canvas=page.VerificationCanvas;canvas.renderMode=RenderMode.WorldSpace;canvas.GetComponent<CanvasScaler>().enabled=false;float scale=canvas.scaleFactor;var rect=(RectTransform)canvas.transform;rect.anchorMin=rect.anchorMax=rect.pivot=Vector2.one*.5f;rect.localPosition=Vector3.zero;rect.localScale=Vector3.one;rect.sizeDelta=new Vector2(size.x/scale,size.y/scale);}
  static void Capture(OnlineTeamsPage82 page,Vector2Int size,string state){
   var canvas=page.VerificationCanvas;float scale=canvas.scaleFactor;var cameraRoot=new GameObject("Teams118 offscreen camera");var camera=cameraRoot.AddComponent<Camera>();camera.enabled=false;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.magenta;camera.orthographic=true;camera.orthographicSize=size.y/(2*scale);camera.aspect=size.x/(float)size.y;camera.transform.position=canvas.transform.position-new Vector3(0,0,10);
   var target=new RenderTexture(size.x,size.y,24);target.Create();var prior=RenderTexture.active;var oldCamera=canvas.worldCamera;Texture2D image=null;
   try{camera.targetTexture=target;canvas.worldCamera=camera;Canvas.ForceUpdateCanvases();camera.Render();camera.Render();RenderTexture.active=target;image=new Texture2D(size.x,size.y,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,size.x,size.y),0,0);image.Apply();Check(image.GetPixels32().All(p=>!(p.r>245&&p.g<10&&p.b>245)),"Editor capture paints whole canvas without magenta sentinel");string relative="Native/TeamsParity118/"+state+"_RU_"+size.x+"x"+size.y+".png";string path=Path.Combine(output,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllBytes(path,image.EncodeToPNG());report.captures.Add(relative);}
   finally{canvas.worldCamera=oldCamera;camera.targetTexture=null;RenderTexture.active=prior;if(image)UnityEngine.Object.DestroyImmediate(image);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(cameraRoot);}
  }
  static void Case(TeamsAssets assets,string state,Vector2Int size){
   var root=new GameObject("Teams118 fixture "+state);var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;
   try{var view=View(state);page.ConfigureViewForVerification(assets,view);page.VerificationViewport(size.x,size.y);page.VerificationSafeArea(state=="InviteSafe"||state=="LeaveSafe"?new Rect(0,0,size.x,size.y-28):new Rect(0,0,size.x,size.y));page.Show();Prepare(page,size);page.VerificationViewport(size.x,size.y);Canvas.ForceUpdateCanvases();var frame=page.VerificationFrame;var nodes=page.VerificationNodes;
    Check(page.VerificationCanvas.GetComponent<CanvasScaler>().uiScaleMode==CanvasScaler.ScaleMode.ConstantPixelSize,"Single constant-pixel CanvasScaler");
    if(state=="Reward"){
     Check(Element(frame.overlay,"mail-detail-frame").parent=="mail-detail-root118","Reward panel grouped with header and footer");Check(Element(frame.overlay,"mail-detail-action").parent=="mail-detail-root118","Reward action fixed in modal root");Check(Element(frame.overlay,"mail-detail-scroll").parent=="mail-detail-root118","Only reward body scrolls");Check(nodes["mail-detail-scroll"].GetComponent<ScrollRect>()&&nodes["mail-detail-action"].GetComponent<Button>(),"Native reward scroll and action");
     var rewardPanel=Element(frame.overlay,"mail-detail-frame");var rewardRoot=Element(frame.overlay,"mail-detail-root118");Check(rewardPanel.height<=406&&rewardRoot.y+rewardPanel.y>=(frame.height-rewardPanel.height)/2+13,"Reward frame uses compact lower placement");
     var letter=Element(frame.overlay,"mail-detail-crest");var rewardCloseArt=Element(frame.overlay,"mail-close-art");var rewardCloseHit=Element(frame.overlay,"mail-close");
     Check(letter.parent==rewardRoot.id&&Math.Abs(letter.x+letter.width/2-(rewardPanel.x+rewardPanel.width/2))<.5f&&Math.Abs(letter.y-(rewardPanel.y-39))<.5f,"Reward letter stays centered and 39 units above panel top");
     Check(rewardCloseArt.parent==rewardRoot.id&&Math.Abs(rewardCloseArt.y-(rewardPanel.y-9))<.5f&&Math.Abs(rewardCloseArt.x+rewardCloseArt.width/2-(rewardPanel.x+rewardPanel.width-8))<.5f,"Reward close disc stays above panel near right edge");
     Check(rewardCloseHit.parent==rewardRoot.id&&rewardRoot.x+rewardCloseHit.x>=0&&rewardRoot.x+rewardCloseHit.x+rewardCloseHit.width<=frame.width&&rewardRoot.y+rewardCloseHit.y>=0,"Reward close hit target remains inside safe frame");
     Check(nodes["mail-detail-crest"].parent==nodes[rewardRoot.id]&&nodes["mail-close-art"].parent==nodes[rewardRoot.id]&&nodes["mail-close"].parent==nodes[rewardRoot.id],"Reward header art and hit target share native modal root");
     var title=nodes["mail-detail-title"].GetComponent<Text>();var body=nodes["mail-detail-body"].GetComponent<Text>();Check(title.text==TeamsMailText111.T("team_reward"),"Reward heading localized from selected language");Check(body&&!body.supportRichText&&!body.text.Contains("<b>")&&body.text.Contains("награда")&&body.text.Contains("2 < 3")&&body.text.Contains("4 > 1"),"Untrusted markup displayed as plain content without losing ordinary comparison symbols");Check(nodes["mail-detail-coins"].GetComponent<Text>().text==300.ToString("N0")&&nodes["mail-detail-lives"].GetComponent<Text>().text=="2","Authoritative quantities retained");
     RewardTileInside(nodes,"mail-detail-coin-card","mail-detail-coin","mail-detail-coins","mail-detail-coins-label");RewardTileInside(nodes,"mail-detail-life-card","mail-detail-heart","mail-detail-lives","mail-detail-lives-label");
    } else if(state=="Invite"||state=="InviteSafe"){
     Check(Element(frame.overlay,"invite-frame").parent=="invite-root118"&&Element(frame.overlay,"invite-close").parent=="invite-root118"&&Element(frame.overlay,"invite-footer-close").parent=="invite-root118","Invite art, close and footer share root");Check(Element(frame.overlay,"invite-list").parent=="invite-root118"&&Element(frame.overlay,"invite-list-content").parent=="invite-list","Only friend rows use nested scroll content");var list=nodes["invite-list"].GetComponent<ScrollRect>();Check(list&&list.content==nodes["invite-list-content"]&&!nodes["invite-footer-close"].IsChildOf(list.viewport),"Native list scroll excludes fixed footer");Check(Element(frame.overlay,"invite-frame").height<=size.y*.75f,"Compact Invite modal");
     var invitePanel=Element(frame.overlay,"invite-frame");var inviteRoot=Element(frame.overlay,"invite-root118");Check(invitePanel.height<=455&&inviteRoot.y+invitePanel.y>=(frame.height-invitePanel.height)/2+(state=="InviteSafe"?1:11),"Invite frame uses compact safe-area placement");
     var inviteCrest=Element(frame.overlay,"invite-crest");var inviteCloseArt=Element(frame.overlay,"invite-close-art");var inviteCloseHit=Element(frame.overlay,"invite-close");
     Check(inviteCrest.parent==inviteRoot.id&&Math.Abs(inviteCrest.x+inviteCrest.width/2-(invitePanel.x+invitePanel.width/2))<.5f&&Math.Abs(inviteCrest.y-(invitePanel.y-39))<.5f,"Invite crest stays centered and 39 units above panel top");
     Check(inviteCloseArt.parent==inviteRoot.id&&Math.Abs(inviteCloseArt.y-(invitePanel.y-9))<.5f&&Math.Abs(inviteCloseArt.x+inviteCloseArt.width/2-(invitePanel.x+invitePanel.width-8))<=4.5f&&inviteRoot.x+inviteCloseArt.x+inviteCloseArt.width<=frame.width+.1f,"Invite close disc stays above panel near right edge and inside safe frame");
     Check(inviteCloseHit.parent==inviteRoot.id&&inviteRoot.x+inviteCloseHit.x>=0&&inviteRoot.x+inviteCloseHit.x+inviteCloseHit.width<=frame.width&&inviteRoot.y+inviteCloseHit.y>=0,"Invite close hit target remains inside safe frame");
     Check(nodes["invite-crest"].parent==nodes[inviteRoot.id]&&nodes["invite-close-art"].parent==nodes[inviteRoot.id]&&nodes["invite-close"].parent==nodes[inviteRoot.id],"Invite header art and hit target share native modal root");
     var sampleLevel=nodes["invite-friend-"+new string('5',32)+"-level"].GetComponent<Text>();Check(sampleLevel&&sampleLevel.text.Contains("126"),"Editor fixture displays its sample progress without a 50-level cap");
     string memberId="invite-friend-"+new string('7',32);Check(nodes.ContainsKey(memberId+"-member-check")&&nodes.ContainsKey(memberId+"-member-label")&&!nodes.ContainsKey(memberId+"-action"),"Already-in-team row uses the reference check and text rather than a disabled invitation button");
     var memberCheck=nodes[memberId+"-member-check"].GetComponent<Image>();var memberLabel=nodes[memberId+"-member-label"].GetComponent<Text>();Check(memberCheck&&memberCheck.color.g>.45f&&memberCheck.color.r<.2f&&memberLabel&&memberLabel.color.r<.25f&&memberLabel.color.g<.4f,"Already-in-team status has visible green check and dark text on cream");
     if(state=="InviteSafe"){
      Check(Math.Abs(frame.height-(size.y-28))<.1f,"Inset fixture applies the physical 28-unit Android top safe area");
      list.verticalNormalizedPosition=1;Canvas.ForceUpdateCanvases();
      foreach(string id in new[]{memberId+"-card",memberId+"-level",memberId+"-member-check",memberId+"-member-label"}){
       var corners=new Vector3[4];nodes[id].GetWorldCorners(corners);
       Check(corners.All(point=>{var local=list.viewport.InverseTransformPoint(point);return local.y>=list.viewport.rect.yMin-.5f&&local.y<=list.viewport.rect.yMax+.5f;}),"Third friend row and status remain fully visible above fixed footer with Android safe area: "+id);
      }
     }
    } else if(state=="Leave"||state=="LeaveSafe"){
     Check(Element(frame.overlay,"leave-panel113").parent=="leave-motion113"&&Element(frame.overlay,"leave-action113").parent=="leave-motion113"&&Element(frame.overlay,"leave-cancel113").parent=="leave-motion113","Leave frame and actions share animated root");Check(Element(frame.overlay,"leave-body-content113").parent=="leave-body113","Only leave body content scrolls");Check(Element(frame.overlay,"leave-panel113").height<=size.y*.62f,"Compact Leave modal");
     var leavePanel=Element(frame.overlay,"leave-panel113");Check(leavePanel.height<=322&&leavePanel.y>=(frame.height-leavePanel.height)/2+8,"Leave frame uses compact lower placement");
     var crest=Element(frame.overlay,"leave-crest113");var closeArt=Element(frame.overlay,"leave-close113-art");var closeHit=Element(frame.overlay,"leave-close113");
     Check(Math.Abs(crest.x+crest.width/2-(leavePanel.x+leavePanel.width/2))<.5f&&Math.Abs(crest.y-(leavePanel.y-39))<.5f,"Leave crest is centered 39 units above panel top");
     Check(Math.Abs(closeArt.y-(leavePanel.y-9))<.5f&&Math.Abs(closeArt.x+closeArt.width/2-(leavePanel.x+leavePanel.width-16))<.5f,"Leave close disc is above and near panel right edge");
     Check(closeHit.parent=="leave-motion113"&&closeHit.height>=48&&closeHit.x>=0&&closeHit.x+closeHit.width<=frame.width&&closeHit.y>=0,"Leave close hit target stays grouped and inside the safe frame");
     var motion=nodes["leave-motion113"];Check(nodes["leave-crest113"].parent==motion&&nodes["leave-close113-art"].parent==motion&&nodes["leave-close113"].parent==motion,"Actual Leave UGUI crest and close move with the whole modal");
    } else if(state=="Detail"||state=="DetailJoin"){
     var detailsClose=Element(frame.chrome,"online-details-close-art");Check(detailsClose.asset=="TA_Close_Disc"&&!detailsClose.sliced,"Team Detail close uses circular approved disc");
     Check(Element(frame.chrome,"online-details-close-icon").asset=="TA_Icon_Close"&&nodes["online-details-close"].GetComponent<Button>()&&nodes["online-details-close"].rect.height>=48,"Team Detail close glyph and touch target remain bound");
     Check(frame.content.elements.Any(e=>e.id=="online-summary-base")&&frame.content.elements.Any(e=>e.id=="online-members"),"Live team detail model retains summary and members");Check(nodes["online-summary-name"].GetComponent<Text>().text==view.team.name,"Team identity bound from one team model");
     var rootScroll=page.VerificationCanvas.GetComponentsInChildren<ScrollRect>().Single(s=>s.name=="Online Teams viewport");Check(rootScroll.verticalNormalizedPosition>=.99f,"Team detail starts at the header rather than the member footer");
     string action=state=="DetailJoin"?"online-join":"online-invite";var target=nodes[action];var button=target.GetComponent<Button>();var accessible=target.GetComponent<HomeControlLabel>();Check(button&&button.interactable&&accessible&&!string.IsNullOrEmpty(accessible.label)&&target.rect.height>=48,"Team detail join/invite action remains usable and accessible");
     Canvas.ForceUpdateCanvases();rootScroll.Rebuild(CanvasUpdate.Prelayout);rootScroll.Rebuild(CanvasUpdate.PostLayout);rootScroll.verticalNormalizedPosition=0;Canvas.ForceUpdateCanvases();var corners=new Vector3[4];target.GetWorldCorners(corners);var bottom=rootScroll.viewport.InverseTransformPoint(corners[0]);var top=rootScroll.viewport.InverseTransformPoint(corners[1]);Check(bottom.y>=rootScroll.viewport.rect.yMin-.5f&&top.y<=rootScroll.viewport.rect.yMax+.5f,"Team detail join/invite action is fully reachable after scrolling");rootScroll.verticalNormalizedPosition=1;Canvas.ForceUpdateCanvases();
    } else if(state=="Chat"){
     var text=nodes["online-message-"+new string('8',32)+"-body"].GetComponent<Text>();Check(text&&!text.supportRichText&&!text.text.Contains("<b>")&&text.text.Contains("готова")&&text.text.Contains("2 < 3"),"Remote chat stays plain and preserves ordinary symbols");
    }
    foreach(var element in frame.overlay.elements.Where(e=>!string.IsNullOrEmpty(e.action)&&e.action!="disabled"&&e.kind=="group"))Check(element.height>=48,"Modal hit target >=48: "+element.id);
    Capture(page,size,state);report.cases++;
   }finally{page.Hide(false);page.ClearViewForVerification();UnityEngine.Object.DestroyImmediate(root);}
  }
  public static void Run(){
   output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW118_OUT")??"../Verification/Evidence/Review118");report=new Report{unity=Application.unityVersion};int saved=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);bool had=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int locale=GameLocale.Current;
   try{Check(Application.unityVersion=="2022.3.62f3","Pinned Unity 2022 baseline");EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);GameLocale.Select(4);Check(TeamsSocialLayout110.PlainText118("A <b>untrusted markup</b> and 2 < 3 > 1") == "A untrusted markup and 2 < 3 > 1","Narrow markup normalization");Check(TeamsSocialLayout110.PlainText118("<village> 2 < 3") == "<village> 2 < 3","Unknown bracketed words and comparisons remain literal");var assets=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(assets,"Team assets loaded");foreach(var size in new[]{new Vector2Int(360,640),new Vector2Int(390,844)})foreach(string state in new[]{"Chat","Reward","Invite","Leave","Detail","DetailJoin"})Case(assets,state,size);Case(assets,"InviteSafe",new Vector2Int(360,640));Case(assets,"LeaveSafe",new Vector2Int(360,640));
   }catch(Exception error){report.errors.Add(error.ToString());}
   finally{GameLocale.Select(locale);if(had)PlayerPrefs.SetInt(GameLocale.PreferenceKey,saved);else PlayerPrefs.DeleteKey(GameLocale.PreferenceKey);report.status=report.errors.Count==0?"PASS_EDITOR_TEAMS_PARITY118":"FAIL_EDITOR_TEAMS_PARITY118";string path=Path.Combine(output,"Native","TeamsParity118.json");Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllText(path,JsonUtility.ToJson(report,true),new UTF8Encoding(false));}
   EditorApplication.Exit(report.errors.Count==0?0:1);
  }
 }
}
#endif
