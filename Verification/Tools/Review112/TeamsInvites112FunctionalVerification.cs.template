#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Teams;
using HeartOfTheRain.App.TeamsSocial;
using HeartOfTheRain.App.TeamsInvites;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
namespace HeartOfTheRain.Verification {
 // Independent actual-client/scripted transport and separately labelled visual fixture.
 public static class TeamsInvites112FunctionalVerification {
  const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  const string Player="11111111111111111111111111111111",Other="33333333333333333333333333333333",Team="22222222222222222222222222222222";
  const string Origin="https://staging.hotr-native-fixture.net";
  [Serializable] sealed class Row {public string state;public int locale,width,height;public bool inset,passed;}
  [Serializable] sealed class Report {
   public string status="RUNNING",utc,unity;
   public string scope="Actual Unity Editor client/parser/session/outbox/controller and UGUI under explicit in-memory scripted responses; visual snapshots separate. No real server, HTTP/DNS, APK/device, provider or production acceptance.";
   public int checks,cases,layoutsAttempted,layouts,scriptedExchanges,actualHttpRequests,animationCases,capturedSentinelPixels;
   public bool rawJsonNullOwnRequestMaterializes;
   public bool ordinaryProfilesPreserved,serverReviewPreserved,settingsPreserved,languagePreferencePreserved;
   public List<Row> rows=new List<Row>();public List<string> errors=new List<string>(),captures=new List<string>();
  }
  // Deliberately ephemeral CAS: exercises the real protected-journal contract,
  // without pretending a memory store is device encryption or a process restart.
  sealed class MemoryStore:IProtectedSessionStore82 {
   byte[] data;public int writes;public bool failNext;
   public byte[] Read()=>data==null?null:(byte[])data.Clone();
   public void CompareExchange(string expected,byte[] replacement){if(failNext){failNext=false;throw new InvalidOperationException("SyntheticCASFailure110");}if((data==null||data.Length==0?"":IdentityProtocol82.Sha(data))!=expected)throw new InvalidOperationException("SyntheticCASConflict110");data=(byte[])replacement.Clone();writes++;}
   public void Dispose(){if(data!=null)Array.Clear(data,0,data.Length);data=null;}
  }
  static Report report;static string output;static TeamsAssets assets;
  static void Check(bool yes,string label){report.checks++;if(!yes)throw new InvalidOperationException(label);}
  static T Field<T>(object value,string name)=>(T)value.GetType().GetField(name,Private).GetValue(value);
  static void Set(object value,string name,object replacement)=>value.GetType().GetField(name,Private).SetValue(value,replacement);
  static string Words(string text)=>string.Join(" ",(text??"").Split((char[])null,StringSplitOptions.RemoveEmptyEntries));
  static string Digest(string path){if(!Directory.Exists(path))return "Absent";using(var sha=SHA256.Create()){string rows=string.Join("\n",Directory.GetFiles(path,"*",SearchOption.AllDirectories).OrderBy(v=>v,StringComparer.Ordinal).Select(p=>p.Substring(path.Length)+":"+BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(p)))));return IdentityProtocol82.Sha(Encoding.UTF8.GetBytes(rows));}}
  static Rect Bounds(RectTransform child,RectTransform root){var p=new Vector3[4];child.GetWorldCorners(p);var v=p.Select(root.InverseTransformPoint).ToArray();return Rect.MinMaxRect(v.Min(x=>x.x),v.Min(x=>x.y),v.Max(x=>x.x),v.Max(x=>x.y));}
  static bool Contains(Rect a,Rect b,float tolerance=.5f)=>b.xMin>=a.xMin-tolerance&&b.xMax<=a.xMax+tolerance&&b.yMin>=a.yMin-tolerance&&b.yMax<=a.yMax+tolerance;
  static void ScrollTo(ScrollRect scroll,float position){Canvas.ForceUpdateCanvases();scroll.Rebuild(CanvasUpdate.Prelayout);scroll.Rebuild(CanvasUpdate.PostLayout);scroll.verticalNormalizedPosition=position;Canvas.ForceUpdateCanvases();}
  static bool Painted(Color32 p)=>!(p.r>245&&p.g<10&&p.b>245);
  // Complete only the private captured client request; never MoveNext Exchange.
  // Its method/path/body and pending token are read from the compiler-generated
  // iterator so actual strict parsing and journal acknowledgement still run.
  static void CompleteScripted(SocialBackendClient82 client,IEnumerator exchange,string json,string error=null,bool unknown=false){
   Check(exchange.GetType().Name.StartsWith("<Exchange>",StringComparison.Ordinal),"Only explicit scripted HTTP iterator boundary is intercepted");var pending=typeof(SocialBackendClient82).GetField("active",Private).GetValue(client);Check(pending!=null,"Actual social client owns the scripted pending request");typeof(SocialBackendClient82).GetMethod("Complete",Private).Invoke(client,new[]{pending,json,error,(object)unknown});pending.GetType().GetMethod("Release",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).Invoke(pending,null);(exchange as IDisposable)?.Dispose();report.scriptedExchanges++;
  }
        static void PrepareCanvas(OnlineTeamsPage82 page,Vector2Int size){var canvas=page.VerificationCanvas;canvas.renderMode=RenderMode.WorldSpace;canvas.GetComponent<CanvasScaler>().enabled=false;float scale=canvas.scaleFactor;var rect=(RectTransform)canvas.transform;rect.anchorMin=rect.anchorMax=rect.pivot=Vector2.one*.5f;rect.localPosition=Vector3.zero;rect.localScale=Vector3.one;rect.sizeDelta=new Vector2(size.x/scale,size.y/scale);}
        static void Capture(OnlineTeamsPage82 page,Vector2Int size,string name){
            var canvas=page.VerificationCanvas;var rect=(RectTransform)canvas.transform;float scale=canvas.scaleFactor;rect.sizeDelta=new Vector2(size.x/scale,size.y/scale);Canvas.ForceUpdateCanvases();
            var background=page.VerificationNodes["online-teams-background"];Check(!background.GetComponent<RawImage>().maskable,"Full R4 background bypasses safe-content clipping");var corners=new Vector3[4];rect.GetWorldCorners(corners);foreach(var corner in corners){var p=background.InverseTransformPoint(corner);Check(p.x>=background.rect.xMin-.1f&&p.x<=background.rect.xMax+.1f&&p.y>=background.rect.yMin-.1f&&p.y<=background.rect.yMax+.1f,"Actual R4 background covers fixed capture canvas corners");}
            var root=new GameObject("Teams110 fixed offscreen camera");var camera=root.AddComponent<Camera>();camera.enabled=false;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.magenta;camera.orthographic=true;camera.orthographicSize=size.y/(2*scale);camera.aspect=size.x/(float)size.y;camera.transform.position=canvas.transform.position-new Vector3(0,0,10);camera.nearClipPlane=.1f;camera.farClipPlane=100;
            var target=new RenderTexture(size.x,size.y,24);target.Create();var oldActive=RenderTexture.active;var oldCamera=canvas.worldCamera;Texture2D pixels=null;
            try{camera.targetTexture=target;canvas.worldCamera=camera;Canvas.ForceUpdateCanvases();camera.Render();camera.Render();RenderTexture.active=target;pixels=new Texture2D(size.x,size.y,TextureFormat.RGB24,false);pixels.ReadPixels(new Rect(0,0,size.x,size.y),0,0);pixels.Apply();var data=pixels.GetPixels32();report.capturedSentinelPixels+=data.Count(p=>!Painted(p));
                string relative="Native/TeamsInvites112/"+name;File.WriteAllBytes(Path.Combine(output,relative),pixels.EncodeToPNG());report.captures.Add(relative);
                Check(Enumerable.Range(0,size.x).All(x=>Painted(data[x])&&Painted(data[(size.y-1)*size.x+x])),"R4 GPU top/bottom edges contain no unpainted sentinel");Check(Enumerable.Range(0,size.y).All(y=>Painted(data[y*size.x])&&Painted(data[y*size.x+size.x-1])),"R4 GPU side edges contain no unpainted sentinel");Check(data.All(Painted),"Opaque full-canvas R4 background leaves zero unpainted sentinel pixels");
            }finally{canvas.worldCamera=oldCamera;camera.targetTexture=null;RenderTexture.active=oldActive;if(pixels)UnityEngine.Object.DestroyImmediate(pixels);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(root);}
        }
  const string Friend="44444444444444444444444444444444", Invite="55555555555555555555555555555555";
  const long Utc=1800000000;
  static string Id()=>Guid.NewGuid().ToString("N");
  static SocialTeam82 TeamView(bool member=true)=>new SocialTeam82{teamId=Team,ownerId=Player,name="Rain Guardians",description="Synthetic verification team",badgeId="drop",capacity=30,memberCount=2,isMember=member,members=member?new[]{new SocialTeamMember82{playerId=Player,displayName="Ivan",isOwner=true},new SocialTeamMember82{playerId=Friend,displayName="Dariya",isOwner=false}}:null};
  static SocialInviteFriends112 Friends()=>new SocialInviteFriends112{teamId=Team,teamName="Rain Guardians",badgeId="drop",publicTeamCode="AABBCCDDEEFF",serverUtc=Utc,memberCount=2,capacity=30,canInvite=true,nextCursor=Friend,hasMore=false,friends=new[]{new SocialInvitableFriend112{friendId=Friend,displayName="Dariya",completedLevels=8,inviteState="Ready",inviteId="",expiresAtUtc=0}}};
  static SocialInvitation112 Invitation(string state="Ready")=>new SocialInvitation112{inviteId=Invite,teamId=state=="Unavailable"?"":Team,teamName=state=="Unavailable"?"":"Rain Guardians",badgeId=state=="Unavailable"?"":"drop",senderName=state=="Unavailable"?"":"Ivan",memberCount=state=="Unavailable"?0:2,capacity=state=="Unavailable"?0:30,sequence=2,expiresAtUtc=Utc+3600,state=state};
  sealed class Scripted:IDisposable {
   public readonly MemoryStore store; public SocialBackendClient82 client; public SocialPageSession82 session;public long generation=1;public double clock;public int posts,exchanges;public bool unknownNext;public string path,body,method,lastPostPath,lastPostBody,wireOverride,getError;public SocialInviteFriends112 friends=Friends();public SocialInvitation112 received=Invitation();
   public Scripted(MemoryStore shared=null){store=shared??new MemoryStore();Open();}
   public void Open(){var access=new SocialAccess82(Player,IdentityProtocol82.NewSecret());client=new SocialBackendClient82(Origin,()=>access,Dispatch,store,true,false);session=new SocialPageSession82(client,null,()=>generation,()=>clock);}
   public void Reopen(){report.actualHttpRequests+=client.VerificationRequests;session.Dispose();Open();}
   static string IteratorText(IEnumerator value,string name)=>(string)value.GetType().GetField(name,Private|BindingFlags.Public).GetValue(value);
   public void Dispatch(IEnumerator exchange){
    if(exchange.GetType().Name.StartsWith("<Exchange>",StringComparison.Ordinal)){exchanges++;method=IteratorText(exchange,"method");path=IteratorText(exchange,"path");body=IteratorText(exchange,"body");string json=null,error=null;bool unknown=false;
     if(method=="POST"){posts++;lastPostBody=body;lastPostPath=path;if(unknownNext){unknownNext=false;error="SocialNetworkUnavailable";unknown=true;}else json=Response();}
     else if(getError!=null){error=getError;getError=null;}else if(wireOverride!=null){json=wireOverride;wireOverride=null;}else json=Response();
     CompleteScripted(client,exchange,json,error,unknown);return;}
    int steps=0;try{while(exchange.MoveNext()){Check(++steps<120,"Only bounded synthetic orchestration");if(exchange.Current is IEnumerator child)Dispatch(child);else Check(exchange.Current==null,"No native/network wait");}}finally{(exchange as IDisposable)?.Dispose();}
   }
   string Response(){
    if(method=="POST"&&path.StartsWith("/v1/teams/"+Team+"/invitations/",StringComparison.Ordinal)){return JsonUtility.ToJson(new SocialMutation82{operation="invite.send",receiptId=Id(),teamId=Team,friendId=Friend,inviteId=Invite,state="Invited",createdAtUtc=Utc,expiresAtUtc=Utc+3600,serverUtc=Utc});}
    if(method=="POST")throw new InvalidOperationException("UnexpectedInviteWrite");
    if(path.StartsWith("/v1/teams?",StringComparison.Ordinal))return JsonUtility.ToJson(new SocialTeams82{teams=new[]{TeamView(false)},myTeamId=Team,nextCursor="",hasMore=false});
    if(path=="/v1/teams/"+Team)return JsonUtility.ToJson(TeamView());
    if(path.StartsWith("/v1/teams/"+Team+"/life-requests",StringComparison.Ordinal))return "{\"teamId\":\""+Team+"\",\"serverUtc\":"+Utc+",\"nextRequestAt\":0,\"ownRequest\":null,\"requests\":[],\"olderCursor\":0,\"hasOlder\":false,\"policy\":{\"version\":\"team_help110_review_v1\",\"capacity\":5,\"cooldownSeconds\":14400,\"lifetimeSeconds\":14400,\"helpSpendsDonorLives\":false}}";
    if(path.StartsWith("/v1/life-requests/owned?",StringComparison.Ordinal))return "{\"serverUtc\":"+Utc+",\"nextCursor\":0,\"hasMore\":false,\"requests\":[],\"policy\":{\"version\":\"team_help110_review_v1\",\"capacity\":5,\"cooldownSeconds\":14400,\"lifetimeSeconds\":14400,\"helpSpendsDonorLives\":false}}";
    if(path.StartsWith("/v1/mail/rewards/owned?",StringComparison.Ordinal))return "{\"serverUtc\":"+Utc+",\"nextCursor\":0,\"hasMore\":false,\"rewards\":[]}";
    if(path.StartsWith("/v1/messages/Team/",StringComparison.Ordinal))return "{\"messages\":[],\"olderCursor\":0,\"nextCursor\":0,\"hasOlder\":false,\"hasMore\":false,\"hasNewer\":false,\"unreadCount\":0}";
    if(path.StartsWith("/v1/teams/"+Team+"/invitations?",StringComparison.Ordinal))return JsonUtility.ToJson(friends);
    if(path.StartsWith("/v1/invitations/received?",StringComparison.Ordinal))return JsonUtility.ToJson(new SocialInvitations112{serverUtc=Utc,nextCursor=2,hasMore=false,invitations=new[]{received}});
    if(path=="/v1/invitations/"+Invite)return JsonUtility.ToJson(new SocialInvitationDetail112{serverUtc=Utc,invitation=received});
    throw new InvalidOperationException("UnexpectedInviteRead "+path);
   }
   public void Select(){session.Show(SocialPane82.Teams);Check(session.RefreshTeams(),"Actual session accepts directory request");Check(session.SelectTeam(Team),"Actual session selects projected team");}
   public void Dispose(){report.actualHttpRequests+=client.VerificationRequests;session.Dispose();store.Dispose();}
  }
  static void LocaleIntegrity(){
   foreach(int locale in Enumerable.Range(0,5)){GameLocale.Select(locale);foreach(string key in new[]{"more","first","no_invites","unconfirmed","share_not_configured","detail_unavailable"}){string value=TeamsInvitesText112.T(key);Check(!string.IsNullOrWhiteSpace(value)&&value!=key&&!value.Contains("?"),"New localized label has real characters "+locale+"/"+key);if(locale==4)Check(value.Any(c=>c>=0x0400&&c<=0x04ff),"Russian label keeps Cyrillic "+key);}}
   report.cases++;
  }
  static void ShareGate(){
   const string host="invite.example.test",good="https://invite.example.test/i/abc123",code="AABBCCDDEEFF";
   Check(TeamsInviteShare112.CanOffer(good,host,code),"Valid exact HTTPS fixture accepted by pure gate");
   foreach(var pair in new[]{Tuple.Create((string)null,host),Tuple.Create(good,(string)null),Tuple.Create(good,"other.example.test"),Tuple.Create("http://invite.example.test/i/token",host),Tuple.Create("https://evil.test/i/token",host),Tuple.Create("https://invite.example.test.evil.test/i/token",host),Tuple.Create("https://user@invite.example.test/i/token",host),Tuple.Create("https://invite.example.test/i/token#fragment",host),Tuple.Create("https://invite.example.test:444/i/token",host),Tuple.Create("https://invite.example.test/a/../token",host),Tuple.Create("https://invite.example.test/a/%2e%2e/token",host),Tuple.Create("https://invite.example.test/a/%2f/token",host),Tuple.Create("not a url",host)}) Check(!TeamsInviteShare112.ValidServerUrl(pair.Item1,pair.Item2),"Malformed or unapproved URL rejected by pure gate");
   Check(!TeamsInviteShare112.CanOffer(good,host,""),"Missing public code disables sharing");Check(!TeamsInviteShare112.CanOffer(good,host,"NOT-A-CODE"),"Malformed public code disables sharing");report.cases++;
  }
  static void Protocol(){using(var f=new Scripted()){
    f.Select();SocialReply82<SocialInviteFriends112> list=null;f.client.GetInvitableFriends112(Team,"","",x=>list=x);Check(list!=null&&list.Succeeded&&list.value.friends.Length==1&&list.value.friends[0].inviteState=="Ready","Strict friends parser accepts server identity");
    var duplicate=Friends();duplicate.friends=new[]{duplicate.friends[0],duplicate.friends[0]};f.wireOverride=JsonUtility.ToJson(duplicate);list=null;f.client.GetInvitableFriends112(Team,"","",x=>list=x);Check(list!=null&&!list.Succeeded,"Duplicate friend identity rejected");
    SocialReply82<SocialInvitations112> received=null;f.client.GetReceivedInvitations112(0,x=>received=x);Check(received!=null&&received.Succeeded&&received.value.invitations[0].inviteId==Invite,"Global recipient parser accepts server invitation");
    var malformed=new SocialInvitations112{serverUtc=Utc,nextCursor=2,invitations=new[]{Invitation(),Invitation()}};f.wireOverride=JsonUtility.ToJson(malformed);received=null;f.client.GetReceivedInvitations112(0,x=>received=x);Check(received!=null&&!received.Succeeded,"Duplicate incoming invitation rejected");
    f.unknownNext=true;string id=Id();Check(f.session.SendInvite112(id,Friend),"Actual session dispatches explicit invite");var p=f.client.PendingCommand;Check(p!=null&&p.operation=="invite.send"&&p.commandId==id,"Unknown outcome retains journaled operation");string path=p.path,body=p.body;int posts=f.posts;f.Reopen();Check(f.client.PendingCommand?.body==body,"Reconstructed journal preserves exact invite intent");Check(f.session.ResumePending(),"Explicit retry is dispatched");Check(f.posts==posts+1&&f.lastPostPath==path&&f.lastPostBody==body&&f.client.PendingCommand==null,"Retry reuses immutable path/body and clears journal on receipt");report.cases+=4;
  }}
  static void Actions(){
   var prior=EventSystem.current;var selected=prior?prior.currentSelectedGameObject:null;var eventRoot=new GameObject("Invite112 isolated EventSystem");var events=eventRoot.AddComponent<EventSystem>();typeof(EventSystem).GetMethod("OnEnable",Private).Invoke(events,null);EventSystem.current=events;var root=new GameObject("Invite112 actual controller fixture");
   try{using(var f=new Scripted()){
    f.Select();var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;page.ConfigureForVerification(assets,f.session,f.Dispatch);page.VerificationViewport(720,1600);page.Show();page.VerificationPump();page.Request("invite");page.VerificationPump();
    Check(page.VerificationNodes.ContainsKey("invite-friend-"+Friend+"-action"),"Actual member invitation opens confirmed friend list");
    float originalHeight=page.VerificationFrame.height;page.VerificationKeyboard110(400);page.VerificationPump();Canvas.ForceUpdateCanvases();var input=page.VerificationNodes["invite-search-input"];var list=page.VerificationNodes["invite-list"].GetComponent<ScrollRect>();var frame=page.VerificationFrame;
    Check(frame.height<originalHeight,"Synthetic keyboard inset reduces actual usable canvas");Check(list&&list.viewport&&list.viewport.rect.height>0,"Search results retain a scrollable viewport above synthetic keyboard");var inputElement=frame.overlay.elements.Single(e=>e.id=="invite-search-input");Check(inputElement.y>=0&&inputElement.y+inputElement.height<=frame.height,"Search field remains inside keyboard-adjusted canvas");page.VerificationKeyboard110(0);page.VerificationPump();Check(page.VerificationFrame.height>=originalHeight-.1f,"Hiding synthetic keyboard restores viewport");
    int posts=f.posts;f.unknownNext=true;page.Request("invite-friend:"+Friend);var pending=f.client.PendingCommand;Check(f.posts==posts+1&&pending?.operation=="invite.send","Explicit tap starts one journaled invite");Check(!page.VerificationInviteFeedback112,"Unknown pending request has no confirmed feedback");page.Request("invite-friend:"+Friend);Check(f.posts==posts+1&&f.client.PendingCommand?.commandId==pending.commandId,"Repeated tap cannot create second invite");page.Request("invite-close");Check(f.client.PendingCommand?.commandId==pending.commandId,"Closing modal cannot cancel or resend unknown invite");Check(!page.VerificationInviteFeedback112,"Closing during pending has no success feedback");
    Check(f.session.ResumePending(),"Explicit journal recovery starts");page.VerificationPump();Check(f.client.PendingCommand==null,"Confirmed retry clears protected intent");
    page.Request("invite-received");page.VerificationPump();page.Request("invite-open:"+Invite);page.VerificationPump();Check(page.VerificationNodes.ContainsKey("invite-detail-view"),"Actual global received list opens detail");
    f.getError="SocialNetworkUnavailable";page.Request("invite-view");page.VerificationPump();Check(page.VerificationNodes.ContainsKey("invite-detail-view"),"Failed fresh detail cannot open stale team");
    page.Request("invite-refresh");page.VerificationPump();Check(page.VerificationNodes["invite-detail-status"].GetComponent<Text>().text.Contains("01:00:00"),"Fresh server anchor produces one-hour countdown");
    f.clock=15;page.VerificationPump();Check(page.VerificationNodes["invite-detail-status"].GetComponent<Text>().text.Contains("00:59:45"),"Detail countdown advances using monotonic server anchor");
    f.received=Invitation("Expired");f.clock=3601;int before=f.exchanges;page.VerificationPump();Check(f.exchanges>before,"Reaching expiry refreshes actual detail from service");Check(!page.VerificationNodes["invite-detail-view"].GetComponent<Button>().interactable,"Refreshed expired invitation cannot open team");report.cases+=4;
   }}finally{if(events)events.SetSelectedGameObject(null);UnityEngine.Object.DestroyImmediate(root);typeof(EventSystem).GetMethod("OnDisable",Private).Invoke(events,null);UnityEngine.Object.DestroyImmediate(eventRoot);if(prior){EventSystem.current=prior;prior.SetSelectedGameObject(selected);}}
  }
  static void Motion(){
   foreach(bool reduced in new[]{false,true}){var root=new GameObject("Invite112 confirmed feedback controller");try{using(var f=new Scripted()){
    f.Select();var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;page.ConfigureForVerification(assets,f.session,f.Dispatch);page.VerificationReducedMotion110(reduced);page.VerificationViewport(720,1600);page.Show();page.VerificationPump();page.Request("invite");page.VerificationPump();
    page.Request("invite-share");var tab=page.VerificationInviteTabFeedback112;Check(tab&&tab.Running&&Math.Abs(tab.Duration-(reduced?.12f:.14f))<.001f,"Tab transition respects reduced-motion timing");page.VerificationAdvanceInvite112(1);Check(!page.VerificationInviteTabFeedback112,"Tab transition completes presentation only");page.Request("invite-friends");page.VerificationAdvanceInvite112(1);
    page.Request("invite-friend:"+Friend);page.VerificationPump();Check(f.session.LastInviteReceipt112?.inviteId==Invite,"Validated send receipt is available");Check(!page.VerificationInviteFeedback112,"Confirmed receipt alone cannot animate stale ready row");
    f.friends.friends[0].inviteState="Invited";f.friends.friends[0].inviteId=Invite;f.friends.friends[0].expiresAtUtc=Utc+3600;page.Request("invite-refresh");page.VerificationPump();var feedback=page.VerificationInviteFeedback112;
    Check(feedback&&feedback.Running&&feedback.ReceiptId==f.session.LastInviteReceipt112.receiptId&&Math.Abs(feedback.Duration-(reduced?.12f:.14f))<.001f,"Only matching refreshed Invited row starts confirmed feedback");int sent=f.posts;page.VerificationAdvanceInvite112(reduced?.06f:.07f);Check(feedback&&feedback.Running,"Confirmed opacity transition is still running halfway");page.VerificationAdvanceInvite112(1);Check(!page.VerificationInviteFeedback112&&f.posts==sent&&f.session.LastInviteReceipt112?.inviteId==Invite,"Completed feedback cannot mutate server state");page.VerificationPump();Check(!page.VerificationInviteFeedback112,"Same receipt does not animate twice");report.animationCases++;
   }}finally{UnityEngine.Object.DestroyImmediate(root);}}
  }
  static OnlineTeamsView82 InviteView(string state){
   var v=new OnlineTeamsView82{connected=true,selfId=Player,team=TeamView(),tab=1,detailsOpen=true,details=TeamView(),status="",modal="invite",inviteFriends112=Friends(),inviteQuery112="",inviteNotice112="",inviteReady112=true,now110=Utc};
   if(state=="Share"){v.inviteShare112=true;}
   if(state=="Offline"){v.inviteOffline112=true;}
   if(state=="OfflineDetail"){v.detailsOpen=false;v.team=null;v.details=null;v.modal="invite-detail112";v.inviteDetail112=Invitation();v.inviteOffline112=true;v.inviteReady112=false;}
   if(state=="Error"){v.inviteFriends112=null;}
   if(state=="Loading"){v.inviteFriends112=null;v.inviteLoading112=true;}
   if(state=="Empty"){v.inviteFriends112.friends=new SocialInvitableFriend112[0];v.inviteFriends112.nextCursor="";}
   if(state=="NoResults"){v.inviteFriends112.friends=new SocialInvitableFriend112[0];v.inviteFriends112.nextCursor="";v.inviteQuery112="search";}
   if(state=="Pending"){v.pending=true;v.invitePendingFriend112=Friend;}
   if(state=="Sent"){v.inviteFriends112.friends[0].inviteState="Invited";v.inviteFriends112.friends[0].inviteId=Invite;v.inviteFriends112.friends[0].expiresAtUtc=Utc+3600;}
   if(state=="Member"){v.inviteFriends112.friends[0].inviteState="Member";}
   if(state=="Full"){v.inviteFriends112.memberCount=30;v.inviteFriends112.canInvite=false;}
   if(state=="LongName"){v.inviteFriends112.friends[0].displayName=string.Join("",Enumerable.Repeat("VeryLongDisplayName",3));}
   if(state=="IncomingError"){v.detailsOpen=false;v.team=null;v.details=null;v.modal="invitations112";v.inviteReceived112=null;v.inviteLoading112=false;}
   if(state=="ReceivedList"){v.detailsOpen=false;v.team=null;v.details=null;v.modal="invitations112";v.inviteReceived112=new SocialInvitations112{serverUtc=Utc,nextCursor=2,invitations=new[]{Invitation()}};}
   if(new[]{"Received","Expired","AlreadyMember","TeamFull","Unavailable"}.Contains(state)){v.detailsOpen=false;v.team=null;v.details=null;v.modal="invite-detail112";v.inviteDetail112=Invitation(state=="Received"?"Ready":state);}
   return v;
  }
  static void Layouts(){
   var root=new GameObject("Invite112 synthetic layout fixtures");try{var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;
    foreach(int locale in Enumerable.Range(0,5))foreach(var size in new[]{new Vector2Int(360,640),new Vector2Int(390,844),new Vector2Int(720,1600),new Vector2Int(768,1024)})foreach(string state in new[]{"Friends","Share","Offline","Error","Loading","Empty","NoResults","Pending","Sent","Member","Full","LongName","ReceivedList","IncomingError","Received","Expired","AlreadyMember","TeamFull","Unavailable","OfflineDetail"}){
     GameLocale.Select(locale);var view=InviteView(state);page.ConfigureViewForVerification(assets,view);page.VerificationViewport(size.x,size.y);page.VerificationSafeArea(size.x==360?new Rect(0,20,size.x,size.y-40):new Rect(0,0,size.x,size.y));page.Show();PrepareCanvas(page,size);page.VerificationViewport(size.x,size.y);Canvas.ForceUpdateCanvases();
     var row=new Row{state=state,locale=locale,width=size.x,height=size.y,inset=size.x==360};report.rows.Add(row);report.layoutsAttempted++;
     try{
      var frame=page.VerificationFrame;Check(frame.width>0&&frame.height>0,"Finite canvas");
      Check(page.VerificationNodes.ContainsKey("invite-shade")&&page.VerificationNodes.ContainsKey("invite-close"),"Modal shade and close present");
      foreach(var e in frame.overlay.elements){Check(e.width>0&&e.height>0&&!float.IsNaN(e.x+e.y+e.width+e.height),"Positive finite modal geometry "+e.id);Check(page.VerificationNodes.TryGetValue(e.id,out var node),"Native modal node "+e.id);
       if(!string.IsNullOrEmpty(e.action)&&e.action!="disabled"&&e.kind=="group")Check(e.height>=47.9f,"Modal action has 48-unit height "+e.id);
       if(e.kind=="text"||e.kind=="lefttext"||e.kind=="chatbody110"||e.kind=="chatname110"){var t=node.GetComponent<Text>();Check(t&&t.font&&!t.supportRichText,"Plain text label "+e.id);}
       if(!string.IsNullOrEmpty(e.asset)&&e.asset.StartsWith("TI_",StringComparison.Ordinal)){var image=node.GetComponent<Image>();Check(image&&image.sprite==assets.Find(e.asset)&&image.color==Color.white&&image.preserveAspect,"Actual untinted invitation glyph "+e.id);}
       if(string.IsNullOrEmpty(e.parent)&&e.id!="invite-shade")Check(e.x>=-.25f&&e.y>=-.25f&&e.x+e.width<=frame.width+.25f&&e.y+e.height<=frame.height+.25f,"Modal fixed element in safe bounds "+e.id);
      }
      if(new[]{"Friends","Offline","Empty","NoResults","Loading","Error","Pending","Sent","Member","Full","LongName"}.Contains(state)){var sr=page.VerificationNodes["invite-list"].GetComponent<ScrollRect>();Check(sr&&sr.vertical&&!sr.horizontal&&sr.viewport.GetComponent<RectMask2D>(),"Friend list is masked and scrollable");}
      if(new[]{"Friends","LongName"}.Contains(state)){var action=frame.overlay.elements.Single(e=>e.id=="invite-friend-"+Friend+"-action");Check(action.label.Contains(view.inviteFriends112.friends[0].displayName),"Accessible invite label contains full friend name");}
      if(state=="Full")Check(page.VerificationNodes.ContainsKey("invite-disabled-reason"),"Full team explains why invite actions disabled");
      if(new[]{"Friends","Share","Pending"}.Contains(state)){var selected=page.VerificationNodes["invite-tab-selected"].GetComponent<Image>();Check(selected&&selected.sprite==assets.Find("TA_Tab_Selected"),"Selected tab uses approved sapphire sprite");Check(page.VerificationNodes["invite-friends-tab"].GetComponent<Button>().interactable&&page.VerificationNodes["invite-share-tab"].GetComponent<Button>().interactable,"Tabs remain usable while invite is pending");}
      if(state=="Received")Check(page.VerificationNodes["invite-detail-status"].GetComponent<Text>().text.Contains("01:00:00"),"Ready invite expiry is derived from server clock");
      if(state=="Offline"){Check(page.VerificationNodes.ContainsKey("invite-offline-notice")&&page.VerificationNodes.ContainsKey("invite-offline-retry"),"Cached offline Friends shows notice/retry");Check(!page.VerificationNodes["invite-friend-"+Friend+"-action"].GetComponent<Button>().interactable,"Offline cached friend cannot be invited");}
      if(state=="IncomingError"){Check(page.VerificationNodes.ContainsKey("invite-incoming-retry"),"Incoming-list load failure offers retry");Check(page.VerificationNodes["invite-incoming-loading"].GetComponent<Text>().text==TeamsInvitesText112.T("incoming_error"),"Incoming-list failure shows localized error instead of loading");}
      if(state=="OfflineDetail"){var detailAction=frame.overlay.elements.Single(e=>e.id=="invite-detail-view");Check(detailAction.action=="invite-refresh","Offline cached detail offers Retry, not View Team");Check(page.VerificationNodes["invite-detail-status"].GetComponent<Text>().text.Length>0,"Offline detail explains revalidation");}
      if(state=="Share"){var notice=page.VerificationNodes["invite-share-notice"].GetComponent<Text>();Check(notice&&!notice.text.Contains("?"),"Localized unavailable notice contains no replacement question marks");if(locale==4)Check(notice.text.Any(c=>c>=0x0400&&c<=0x04ff),"Russian unavailable notice retains Cyrillic");var copy=page.VerificationNodes["invite-copy"].GetComponent<Button>();Check(copy&&copy.interactable,"Verified public code may be copied");Check(page.VerificationNodes["invite-code"].GetComponent<Text>().text=="AABBCCDDEEFF","Exact public code displayed, no token");var share=page.VerificationNodes["invite-share-disabled"].GetComponent<Button>();Check(share&&!share.interactable,"Share unavailable without host configuration");}
      if(new[]{"Expired","Unavailable"}.Contains(state))Check(!page.VerificationNodes["invite-detail-view"].GetComponent<Button>().interactable,"Expired or unavailable cannot view stale team");
      if(state=="TeamFull")Check(page.VerificationNodes["invite-detail-view"].GetComponent<Button>().interactable,"A full team can still be inspected");
      if(locale==4&&((size.x==720&&new[]{"Friends","Share","Offline","Pending","Received","Expired","OfflineDetail","IncomingError"}.Contains(state))||(size.x==768&&new[]{"Friends","Share","ReceivedList"}.Contains(state))))Capture(page,size,state+"_ru_"+size.x+".png");
      row.passed=true;report.layouts++;
     }catch(Exception ex){report.errors.Add("Visual "+state+"/"+locale+"/"+size+": "+ex.Message);}finally{page.Hide(false);page.ClearViewForVerification();}
    }
   }finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  public static void Run(){
   output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW112_OUT")??"../Verification/Evidence/Review112");Directory.CreateDirectory(Path.Combine(output,"Native","TeamsInvites112"));report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,scope="Actual Unity Editor scripted social/parser/protected journal and synthetic invitation UGUI; no HTTP, OS share, APK, device or production acceptance."};int locale=GameLocale.Current;bool had=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int saved=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);string profiles=Digest(Path.Combine(Application.persistentDataPath,"Profiles")),server=Digest(Path.Combine(Application.persistentDataPath,"ServerReview")),settings=Digest("ProjectSettings");Application.logMessageReceived+=Log;
   try{Check(Application.unityVersion=="2022.3.62f3","Pinned engine");EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);assets=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(assets,"Existing Teams asset");LocaleIntegrity();ShareGate();Protocol();Actions();Motion();Layouts();Check(report.actualHttpRequests==0,"Scripted suite makes no real HTTP");}catch(Exception e){report.errors.Add(e.ToString());}
   finally{GameLocale.Select(locale);report.ordinaryProfilesPreserved=profiles==Digest(Path.Combine(Application.persistentDataPath,"Profiles"));report.serverReviewPreserved=server==Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));report.settingsPreserved=settings==Digest("ProjectSettings");report.languagePreferencePreserved=had==PlayerPrefs.HasKey(GameLocale.PreferenceKey)&&saved==PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);if(!report.ordinaryProfilesPreserved||!report.serverReviewPreserved||!report.settingsPreserved||!report.languagePreferencePreserved)report.errors.Add("Preservation check failed");Application.logMessageReceived-=Log;report.status=report.errors.Count==0?"PASS_NATIVE_TEAMS_INVITES112":"FAIL_NATIVE_TEAMS_INVITES112";File.WriteAllText(Path.Combine(output,"Native","TeamsInvites112.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));}EditorApplication.Exit(report.errors.Count==0?0:1);
  }
  static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}
 }
}
#endif
