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
using HeartOfTheRain.App.TeamsMail;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
namespace HeartOfTheRain.Verification {
 // Independent actual-client/scripted transport and separately labelled visual fixture.
 public static class TeamsMail111FunctionalVerification {
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
                string relative="Native/TeamsMail111/"+name;File.WriteAllBytes(Path.Combine(output,relative),pixels.EncodeToPNG());report.captures.Add(relative);
                Check(Enumerable.Range(0,size.x).All(x=>Painted(data[x])&&Painted(data[(size.y-1)*size.x+x])),"R4 GPU top/bottom edges contain no unpainted sentinel");Check(Enumerable.Range(0,size.y).All(y=>Painted(data[y*size.x])&&Painted(data[y*size.x+size.x-1])),"R4 GPU side edges contain no unpainted sentinel");Check(data.All(Painted),"Opaque full-canvas R4 background leaves zero unpainted sentinel pixels");
            }finally{canvas.worldCamera=oldCamera;camera.targetTexture=null;RenderTexture.active=oldActive;if(pixels)UnityEngine.Object.DestroyImmediate(pixels);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(root);}
        }
  const string Request="44444444444444444444444444444444",Message="55555555555555555555555555555555",Event="66666666666666666666666666666666";
  const long Utc=1800000000;
  static string Id()=>Guid.NewGuid().ToString("N");
  static void Invoke(object owner,string name)=>owner.GetType().GetMethod(name,Private).Invoke(owner,null);
  static SocialLifePolicy110 Policy()=>new SocialLifePolicy110{version="team_help110_review_v1",capacity=5,cooldownSeconds=14400,lifetimeSeconds=14400,helpSpendsDonorLives=false};
  static SocialTeam82 TeamView(bool member=true)=>new SocialTeam82{teamId=Team,ownerId=Other,name="Rain Guardians",description="Explicit synthetic verification team",badgeId="drop",capacity=30,memberCount=2,isMember=member,members=member?new[]{new SocialTeamMember82{playerId=Player,displayName="Ivan",isOwner=false},new SocialTeamMember82{playerId=Other,displayName="Dariya",isOwner=true}}:null};
  static SocialLifeRequest110 Life(bool own=false,string state="Open",int received=2,int claimed=0)=>new SocialLifeRequest110{requestId=Request,messageId=Message,eventId=Event,teamId=Team,playerId=own?Player:Other,displayName=own?"Ivan":"Dariya",state=state,closeReason=state=="Open"?"None":state=="Expired"?"Expired":"Full",collectBlockedReason=own&&state!="Open"&&received>claimed?"None":own?"NotClosed":"NotOwner",sequence=2,createdAt=Utc-60,closesAt=Utc+14340,nextRequestAt=Utc+14340,required=5,received=received,claimed=claimed,remaining=received-claimed,canHelp=!own&&state=="Open"&&received<5,helped=false,canCollect=own&&state!="Open"&&received>claimed};
  static SocialMutation82 Receipt(string operation,string state="Requested",int received=0,int claimed=0,int credit=0)=>new SocialMutation82{operation=operation,state=state,receiptId=Id(),requestId=Request,messageId=Message,eventId=Event,teamId=Team,createdAt=Utc,serverUtc=Utc,received=received,claimed=claimed,remaining=received-claimed,creditedLives=credit,walletRevision=2,lives=5,maxLives=5,nextLifeAt=0};
  static SocialMessages82 Messages(bool older=false)=>new SocialMessages82{messages=new[]{new SocialMessage82{messageId=Message,authorId=Other,displayName="Dariya",text="A village message with <b>plain</b> user text.\nA second line.",sequence=2,createdAt=Utc-60}},olderCursor=2,nextCursor=2,hasOlder=older,hasMore=false,hasNewer=false,unreadCount=1};
  static string LifeJson(SocialLifeRequest110 own,SocialLifeRequest110[] rows,long utc=Utc){string json=JsonUtility.ToJson(new SocialLifeRequests110{teamId=Team,serverUtc=utc,nextRequestAt=own?.nextRequestAt??0,ownRequest=own,requests=rows,policy=Policy()});if(own==null){int start=json.IndexOf("\"ownRequest\":",StringComparison.Ordinal);int end=json.IndexOf(",\"requests\"",start,StringComparison.Ordinal);if(end<0)end=json.IndexOf(",\"policy\"",start,StringComparison.Ordinal);if(start>=0&&end>start)json=json.Substring(0,start)+"\"ownRequest\":null"+json.Substring(end);}return json;}
  static SocialMailMessage111 Mail()=>new SocialMailMessage111{messageId=Message,teamId=Team,sequence=2,senderLabel="Leader",title="Team reward",body="A letter with <b>untrusted markup</b> and wrapped content.",sentAtUtc=Utc-100,readAtUtc=0,expiresAtUtc=Utc+3600,rewardCoins=300,rewardLives=2,claimState="Ready",claimBlockedReason="None",canClaim=true};
  sealed class Scripted:IDisposable {
   public readonly MemoryStore store;public SocialBackendClient82 client;public SocialPageSession82 session;
   public long generation=1;public double clock;public bool member=true,unknownNext,rejectNext;public string memberTeam=Team,getError,wireOverride;public int exchanges,posts;public string path,body,method;public string lastPostPath,lastPostBody;
   public SocialLifeRequest110 own,other=Life();public SocialMailMessage111 mail=Mail();public SocialMessages82 messages=Messages();public SocialLifeRequest110[] owned=new SocialLifeRequest110[0];public bool ownedMore;public long ownedCursor;
   public SocialMutation82 nextReceipt;public readonly Dictionary<string,string> receipts=new Dictionary<string,string>();
   public Scripted(MemoryStore shared=null){store=shared??new MemoryStore();Open();}
   public void Open(){var access=new SocialAccess82(Player,IdentityProtocol82.NewSecret());client=new SocialBackendClient82(Origin,()=>access,Dispatch,store,true,false);session=new SocialPageSession82(client,null,()=>generation,()=>clock);}
   public void Reopen(){report.actualHttpRequests+=client.VerificationRequests;session.Dispose();Open();}
   static string IteratorText(IEnumerator value,string name)=>(string)value.GetType().GetField(name,Private|BindingFlags.Public).GetValue(value);
   public void Dispatch(IEnumerator exchange){
    if(exchange.GetType().Name.StartsWith("<Exchange>",StringComparison.Ordinal)){
     exchanges++;method=IteratorText(exchange,"method");path=IteratorText(exchange,"path");body=IteratorText(exchange,"body");string json=null,error=null;bool unknown=false;
     if(method=="POST"){posts++;lastPostBody=body;lastPostPath=path;if(unknownNext){unknownNext=false;error="SocialNetworkUnavailable";unknown=true;}else if(rejectNext){rejectNext=false;error="SocialHttp409";}else json=Response();}
     else if(getError!=null){error=getError;getError=null;}else if(wireOverride!=null){json=wireOverride;wireOverride=null;}else json=Response();
     CompleteScripted(client,exchange,json,error,unknown);return;
    }
    int steps=0;try{while(exchange.MoveNext()){Check(++steps<120,"Only bounded actual component refresh orchestration is advanced");if(exchange.Current is IEnumerator child)Dispatch(child);else Check(exchange.Current==null,"Scripted component yields no real network/native wait");}}finally{(exchange as IDisposable)?.Dispose();}
   }
   string Response(){
    if(method=="POST"){
     if(receipts.TryGetValue(body+path,out var prior))return prior;
     if(path.Contains("life-requests")){var r=nextReceipt??Receipt(path.EndsWith("/claim",StringComparison.Ordinal)?"life.claim":path.EndsWith("/help",StringComparison.Ordinal)?"life.help":"life.request",path.EndsWith("/claim",StringComparison.Ordinal)?"Deferred":path.EndsWith("/help",StringComparison.Ordinal)?"Sent":"Requested");nextReceipt=null;string reply=JsonUtility.ToJson(r);receipts.Add(body+path,reply);return reply;}
     if(path.Contains("/mail/")||path.StartsWith("/v1/mail/rewards/",StringComparison.Ordinal)) {var r=nextReceipt??new SocialMutation82{operation=path.EndsWith("/read",StringComparison.Ordinal)?"mail.read":"mail.claim",state="Claimed",receiptId=Id(),teamId=Team,messageId=Message,serverUtc=Utc,readAtUtc=Utc,rewardCoins=300,rewardLives=2,walletRevision=2,coins=1550,lives=5,maxLives=5,nextLifeAt=0};nextReceipt=null;string reply=JsonUtility.ToJson(r);receipts.Add(body+path,reply);return reply;}
     if(path.EndsWith("/leave",StringComparison.Ordinal)){member=false;return "{\"teamId\":\""+Team+"\",\"state\":\"Left\"}";}
     if(path.EndsWith("/read",StringComparison.Ordinal))return "{\"through\":2}";
     if(path.StartsWith("/v1/messages/",StringComparison.Ordinal))return "{\"messageId\":\""+Message+"\",\"state\":\"Sent\",\"sequence\":2,\"createdAt\":"+Utc+"}";
     throw new InvalidOperationException("UnexpectedSynthetic110Write");
    }
    if(path.StartsWith("/v1/teams?",StringComparison.Ordinal)){string json=JsonUtility.ToJson(new SocialTeams82{teams=new[]{TeamView(false)},myTeamId=member?memberTeam:null,nextCursor="",hasMore=false});return member?json:json.Replace("\"myTeamId\":\"\"","\"myTeamId\":null");}
    if(path=="/v1/teams/"+Team)return JsonUtility.ToJson(TeamView(member));
    if(path=="/v1/teams/"+Other){var team=TeamView(member);team.teamId=Other;return JsonUtility.ToJson(team);}
    if(path.StartsWith("/v1/teams/"+Team+"/life-requests",StringComparison.Ordinal))return LifeJson(own,other==null?new SocialLifeRequest110[0]:new[]{other});
    if(path.StartsWith("/v1/life-requests/owned?",StringComparison.Ordinal))return JsonUtility.ToJson(new SocialOwnedLives110{serverUtc=Utc,nextCursor=ownedCursor,hasMore=ownedMore,policy=Policy(),requests=owned});
    if(path.StartsWith("/v1/mail/rewards/owned?",StringComparison.Ordinal))return JsonUtility.ToJson(new SocialOwnedMail111{serverUtc=Utc,nextCursor=0,rewards=new SocialMailReward111[0]});
    if(path.StartsWith("/v1/teams/"+Team+"/mail?",StringComparison.Ordinal))return JsonUtility.ToJson(new SocialMailList111{teamId=Team,serverUtc=Utc,olderCursor=mail.sequence,unreadCount=mail.readAtUtc==0?1:0,messages=new[]{mail}});
    if(path=="/v1/teams/"+Team+"/mail/"+Message)return JsonUtility.ToJson(new SocialMailDetail111{serverUtc=Utc,message=mail});
    if(path.StartsWith("/v1/messages/Team/",StringComparison.Ordinal))return JsonUtility.ToJson(messages);
    throw new InvalidOperationException("UnexpectedSynthetic110Read");
   }
   public void Select(){session.Show(SocialPane82.Teams);Check(session.RefreshTeams(),"Actual session accepts directory request");Check(session.SelectTeam(Team),"Actual session selects a projected team");session.Show(SocialPane82.TeamChat);Check(session.RefreshTeamMessages()&&session.Snapshot<SocialMessages82>(SocialPane82.TeamChat)?.nextCursor==2&&session.Status(SocialPane82.TeamChat).state==SocialViewState82.Ready,"Actual strict transport accepts the complete scripted history cursor contract");}
   public void Dispose(){report.actualHttpRequests+=client.VerificationRequests;session.Dispose();store.Dispose();}
  }
  static void MailProtocol(){
   using(var f=new Scripted()){
    f.Select();SocialReply82<SocialMailList111> list=null;f.client.GetTeamMail111(Team,0,x=>list=x);Check(list!=null&&list.Succeeded&&list.value.unreadCount==1&&list.value.messages[0].readAtUtc==0,"Strict inbox parser reads unread from server");
    f.wireOverride=JsonUtility.ToJson(new SocialMailList111{teamId=Team,serverUtc=Utc,olderCursor=2,unreadCount=1,messages=new[]{Mail(),Mail()}});list=null;f.client.GetTeamMail111(Team,0,x=>list=x);Check(list!=null&&!list.Succeeded,"Duplicate message/sequence is rejected");
    Check(f.session.RefreshTeamMail111()&&f.session.Snapshot<SocialMailList111>(SocialPane82.TeamMail111).unreadCount==1,"Session caches server inbox");
    f.getError="SocialNetworkUnavailable";f.session.RefreshTeamMail111();Check(f.session.Status(SocialPane82.TeamMail111).state==SocialViewState82.Offline&&f.session.Snapshot<SocialMailList111>(SocialPane82.TeamMail111)!=null,"Offline retains previously confirmed cache");
    Check(f.session.RefreshMailDetail111(Message)&&f.session.Snapshot<SocialMailDetail111>(SocialPane82.TeamMailDetail111).message.readAtUtc==0,"Detail opens without a grant or implicit read");
    string read=Id();SocialReply82<SocialMutation82> got=null;f.client.ReadTeamMail111(read,Team,Message,x=>got=x);Check(got!=null&&got.Succeeded&&got.value.operation=="mail.read"&&got.value.readAtUtc==Utc,"Read acknowledgement separate from claim");f.mail.readAtUtc=Utc;f.session.RefreshTeamMail111();Check(f.session.Snapshot<SocialMailList111>(SocialPane82.TeamMail111).unreadCount==0,"Unread count comes from reconciled server projection");
    f.unknownNext=true;string command=Id();f.session.ClaimMail111(command,Message);var pending=f.client.PendingCommand;Check(pending!=null&&pending.commandId==command&&pending.operation=="mail.claim","Unknown claim is retained");string body=pending.body,path=pending.path;int posts=f.posts;f.Reopen();Check(f.client.PendingCommand?.body==body,"Reconstructed protected journal keeps exact intent");f.session.ResumePending();Check(f.posts==posts+1&&f.lastPostBody==body&&f.lastPostPath==path&&f.client.PendingCommand==null&&f.session.LastMailReceipt111?.state=="Claimed","Same ID retry confirms only once and clears journal");
    f.getError="SocialHttp403";f.session.RefreshTeamMail111();Check(f.session.Snapshot<SocialMailList111>(SocialPane82.TeamMail111)==null,"Membership loss clears private inbox cache");report.cases+=8;
   }
  }
  static void MailActions(){
   var prior=EventSystem.current;var selected=prior?prior.currentSelectedGameObject:null;var eventRoot=new GameObject("Mail111 isolated EventSystem");var events=eventRoot.AddComponent<EventSystem>();typeof(EventSystem).GetMethod("OnEnable",Private).Invoke(events,null);EventSystem.current=events;var root=new GameObject("Mail111 actual controller with scripted transport");
   try{using(var f=new Scripted()){
    f.mail.readAtUtc=Utc;var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;page.ConfigureForVerification(assets,f.session,f.Dispatch);page.VerificationViewport(720,1600);page.Show();page.VerificationPump();page.Request("tab-mail");page.VerificationPump();Check(page.VerificationNodes.ContainsKey("mail-row-"+Message),"Actual member page routes Mail to live inbox");
    page.Request("mail-open:"+Message);page.VerificationPump();Check(page.VerificationNodes.ContainsKey("mail-detail-scroll"),"Actual row opens detail");page.Request("mail-close");Check(!page.VerificationNodes.ContainsKey("mail-detail-scroll"),"Actual close returns to inbox");
    page.Request("mail-open:"+Message);page.VerificationPump();f.getError="SocialNetworkUnavailable";f.session.RefreshTeamMail111();int count=f.posts;page.Request("mail-claim");Check(f.posts==count&&f.client.PendingCommand==null,"Actual offline claim is disabled without write");
    f.session.RefreshTeamMail111();f.unknownNext=true;page.Request("mail-claim");var pending=f.client.PendingCommand;Check(pending!=null&&pending.operation=="mail.claim","Actual unknown claim retains operation");Check(page.VerificationNodes.ContainsKey("mail-detail-pending-notice")&&page.VerificationNodes["mail-detail-pending-notice"].GetComponent<Text>().text.Length>0,"Unknown result shows actionable pending notice");count=f.posts;page.Request("mail-claim");Check(f.posts==count&&f.client.PendingCommand?.commandId==pending.commandId,"Double tap cannot create second claim");page.Request("mail-close");Check(f.client.PendingCommand?.commandId==pending.commandId,"Closing pending detail does not cancel or repeat claim");
    page.Request("mail-open:"+Message);page.Request("mail-retry");page.VerificationPump();Check(f.client.PendingCommand==null&&f.session.LastMailReceipt111?.state=="Claimed","Actual retry accepts confirmed claim receipt");Check(page.VerificationWalletRefresh110&&page.GetComponentsInChildren<TeamsMailFeedback111>(true).Length==0,"Without an authoritative gateway refresh no success animation plays");page.Hide(false);page.VerificationPump();Check(page.VerificationWalletRefresh110&&page.GetComponentsInChildren<TeamsMailFeedback111>(true).Length==0,"Hidden page retains wallet refresh obligation without success animation");report.cases+=6;
   }}finally{if(events)events.SetSelectedGameObject(null);UnityEngine.Object.DestroyImmediate(root);typeof(EventSystem).GetMethod("OnDisable",Private).Invoke(events,null);UnityEngine.Object.DestroyImmediate(eventRoot);if(prior){EventSystem.current=prior;prior.SetSelectedGameObject(selected);}}
  }
  static void MailRejection(){var root=new GameObject("Mail111 rejected-claim controller fixture");try{using(var f=new Scripted()){
    f.mail.readAtUtc=Utc;var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;page.ConfigureForVerification(assets,f.session,f.Dispatch);page.VerificationViewport(720,1600);page.Show();page.VerificationPump();page.Request("tab-mail");page.VerificationPump();page.Request("mail-open:"+Message);page.VerificationPump();f.rejectNext=true;int posts=f.posts;page.Request("mail-claim");Check(f.posts==posts+1&&f.client.PendingCommand?.operation=="mail.claim","Rejected result keeps exact protected operation");Check(page.VerificationNodes.ContainsKey("mail-detail-pending-notice")&&page.VerificationNodes["mail-detail-pending-notice"].GetComponent<Text>().text.Length>0,"Rejected result shows actionable confirmation notice");Check(!page.VerificationWalletRefresh110&&page.GetComponentsInChildren<TeamsMailFeedback111>(true).Length==0,"Rejected claim neither updates wallet nor plays success");report.cases++;
   }}finally{UnityEngine.Object.DestroyImmediate(root);}}
  static OnlineTeamsView82 MailView(string state){
   var m=Mail();var v=new OnlineTeamsView82{connected=true,selfId=Player,team=TeamView(),tab=0,status="",mail110=true,mailReady111=true,mailStatus111="",mailList111=new SocialMailList111{teamId=Team,serverUtc=Utc,olderCursor=2,unreadCount=1,messages=new[]{m}},now110=Utc,serviceReady110=true};
   if(state=="Empty"){v.mailList111.messages=new SocialMailMessage111[0];v.mailList111.unreadCount=0;v.mailList111.olderCursor=0;}
   if(state=="Offline"){v.mailOffline111=true;v.mailReady111=false;v.mailStatus111="Offline";}
   if(state=="Error"){v.mailList111=null;v.mailStatus111="Could not load";v.mailReady111=false;}
   if(state=="Detail"||state=="Long"||state=="Pending"||state=="Full"||state=="Expired"||state=="Claimed"||state=="OfflineDetail"||state=="Unbroken"||state=="Multiline"||state=="Maximum") {v.modal="mail-detail111";v.mailDetail111=m;}
   if(state=="Long")m.body=string.Join(" ",Enumerable.Repeat("A long letter with plain <b>markup</b> and unbroken "+new string('W',60),20));
   if(state=="Unbroken")m.body=new string('W',2000);
   if(state=="Multiline")m.body=string.Join("\n",Enumerable.Repeat("Repeated wrapped line",80));
   if(state=="Maximum"){m.title=new string('W',120);m.body=new string('W',2000);m.rewardCoins=1000000;m.rewardLives=5;}
   if(state=="Pending")v.pending=true;
   if(state=="Full"){m.claimState="CapacityBlocked";m.claimBlockedReason="FullLives";m.canClaim=false;}
   if(state=="Expired"){m.claimState="Expired";m.canClaim=false;}
   if(state=="Claimed"){m.claimState="Claimed";m.canClaim=false;}
   if(state=="OfflineDetail"){v.mailOffline111=true;v.mailReady111=false;}
   if(state=="Owned"){v.ownedMailOpen111=true;v.ownedMailReady111=true;v.ownedMail111=new SocialOwnedMail111{serverUtc=Utc,rewards=new[]{new SocialMailReward111{messageId=Message,sequence=2,sentAtUtc=Utc-100,expiresAtUtc=Utc+3600,rewardCoins=300,rewardLives=2,claimState="Ready",claimBlockedReason="None",canClaim=true}}};}
   return v;
  }
  static void MailLayouts(){
   var root=new GameObject("Teams111 explicit synthetic layout fixtures");try{var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;
    foreach(int locale in Enumerable.Range(0,5))foreach(var size in new[]{new Vector2Int(360,640),new Vector2Int(390,844),new Vector2Int(720,1600),new Vector2Int(768,1024)})foreach(string state in new[]{"Inbox","Empty","Offline","Error","Detail","Long","Pending","Full","Expired","Claimed","OfflineDetail","Owned","Unbroken","Multiline","Maximum"}){
     GameLocale.Select(locale);var view=MailView(state);page.ConfigureViewForVerification(assets,view);page.VerificationViewport(size.x,size.y);page.VerificationSafeArea(size.x==360?new Rect(0,20,size.x,size.y-40):new Rect(0,0,size.x,size.y));page.Show();PrepareCanvas(page,size);page.VerificationViewport(size.x,size.y);Canvas.ForceUpdateCanvases();
     var row=new Row{state=state,locale=locale,width=size.x,height=size.y,inset=size.x==360};report.rows.Add(row);report.layoutsAttempted++;
     try{
      var frame=page.VerificationFrame;Check(frame.width>0&&frame.height>0&&frame.viewportHeight>0,"Mail viewport has usable height "+state);
      foreach(var layer in new[]{frame.chrome,frame.content,frame.overlay})foreach(var e in layer.elements){
       Check(e.width>0&&e.height>0&&!float.IsNaN(e.x+e.y+e.width+e.height),"Positive finite geometry "+e.id);Check(page.VerificationNodes.TryGetValue(e.id,out var node),"Actual native node "+e.id);
       if(!string.IsNullOrEmpty(e.action)&&e.action!="disabled"&&!e.id.StartsWith("nav-",StringComparison.Ordinal)&&e.kind=="group")Check(e.height>=47.9f,"Action has 48-unit height "+e.id);
       if(e.kind=="text"||e.kind=="lefttext"||e.kind=="chatbody110"||e.kind=="chatname110"){var t=node.GetComponent<Text>();Check(t&&t.font&&!t.supportRichText,"Actual label uses a font and plain text "+e.id);if(e.kind=="chatbody110")Check(t.preferredHeight<=t.rectTransform.rect.height+1.5f,"Scrollable body not vertically truncated "+e.id);}
       if(e.id.StartsWith("mail-row-",StringComparison.Ordinal)&&e.id.EndsWith("-reward-status",StringComparison.Ordinal)){string prefix=e.id.Substring(0,e.id.Length-"-reward-status".Length);var card=page.VerificationNodes[prefix+"-base"];var t=node.GetComponent<Text>();var mesh=t.canvasRenderer.GetMesh();Check(mesh&&mesh.vertexCount>0,"Actual reward status emits glyphs");var verts=mesh.vertices.Select(v=>card.InverseTransformPoint(node.TransformPoint(v))).ToArray();var inner=card.rect;Check(verts.All(v=>v.y>=inner.yMin+6&&v.y<=inner.yMax-6&&v.x>=inner.xMin+6&&v.x<=inner.xMax-6),"Reward status actual glyphs stay inside painted card inset");}
       if(e.id.EndsWith("-preview",StringComparison.Ordinal)){var t=node.GetComponent<Text>();Check(t.cachedTextGenerator.lineCount<=2,"Preview produces at most two real lines");var mesh=t.canvasRenderer.GetMesh();if(mesh&&mesh.vertexCount>0){Rect b=t.rectTransform.rect;Check(mesh.vertices.All(v=>v.x>=b.xMin-3&&v.x<=b.xMax+1&&v.y>=b.yMin-1&&v.y<=b.yMax+1),"Preview emitted glyphs stay within the designated box");}}
       if(!string.IsNullOrEmpty(e.asset)&&e.asset.StartsWith("TM_",StringComparison.Ordinal)){var image=node.GetComponent<Image>();Check(image&&image.sprite==assets.Find(e.asset)&&image.color==Color.white&&image.preserveAspect,"Mail image uses exact untinted artwork "+e.id);}
       if(layer!=frame.content&&string.IsNullOrEmpty(e.parent)&&e.id!="online-teams-background"&&e.id!="online-modal-shade")Check(e.x>=-.25f&&e.y>=-.25f&&e.x+e.width<=frame.width+.25f&&e.y+e.height<=frame.height+.25f,"Fixed node remains in safe logical bounds "+e.id);
      }
      if(state=="Detail"||state=="Long"||state=="Pending"||state=="Full"||state=="Expired"||state=="Claimed"||state=="OfflineDetail"||state=="Unbroken"||state=="Multiline"||state=="Maximum"){var sr=page.VerificationNodes["mail-detail-scroll"].GetComponent<ScrollRect>();Check(sr&&sr.vertical&&!sr.horizontal&&sr.viewport.GetComponent<RectMask2D>(),"Actual detail uses masked vertical scroll");if(state=="Long"||state=="Unbroken"||state=="Multiline"||state=="Maximum"){Check(sr.content.rect.height>sr.viewport.rect.height,"Long message remains scrollable");var body=page.VerificationNodes["mail-detail-body"].GetComponent<Text>();if(state=="Long")Check(view.mailDetail111.body.Contains("<b>markup</b>"),"Original untrusted server body remains intact in the model");Check(body.text==TeamsSocialLayout110.DisplayText110(view.mailDetail111.body,body.font)&&!body.supportRichText,"Full long server body is displayed as plain text without truncation");}if(state=="Detail")Check(page.VerificationNodes["mail-detail-state"].GetComponent<Text>().text.Contains("01:00:00"),"Countdown derives from explicit server clock anchor");if(state=="OfflineDetail")Check(!page.VerificationNodes["mail-detail-action"].GetComponent<Button>().interactable,"Offline detail cannot claim");}
      if(locale==4&&((size.x==720&&new[]{"Inbox","Empty","Detail","Long","Full","OfflineDetail","Claimed"}.Contains(state))||(size.x==768&&new[]{"Inbox","Pending","Owned"}.Contains(state))))Capture(page,size,state+"_ru_"+size.x+".png");
      if(state=="Owned"&&locale==4&&size.x==720){Check(page.VerificationMailFeedbackTarget111(Message,true)==page.VerificationNodes["mail-owned-"+Message+"-action"],"Present owned reward uses its actual action anchor");view.ownedMail111.rewards=new SocialMailReward111[0];page.ConfigureViewForVerification(assets,view);Canvas.ForceUpdateCanvases();Check(page.VerificationMailFeedbackTarget111(Message,true)==page.VerificationNodes["mail-owned-feedback-anchor"],"Refreshed empty owner list uses stable feedback anchor");}
      row.passed=true;report.layouts++;
     }catch(Exception ex){report.errors.Add("Visual "+state+"/"+locale+"/"+size+": "+ex.Message);}finally{page.Hide(false);page.ClearViewForVerification();}
    }
   }finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  static void MailAnimations(){foreach(bool reduced in new[]{false,true}){var go=new GameObject("Confirmed mail motion",typeof(RectTransform));var fx=go.AddComponent<TeamsMailFeedback111>();fx.Begin(Id(),assets.Find("TM_Letter_Open"),assets.Find("TA_Icon_Check"),assets.Find("TA_Stat_star"),reduced);Check(fx.Running&&fx.ReceiptId.Length==32&&!go.GetComponent<CanvasGroup>().blocksRaycasts,"Confirmed feedback has no input or mutation");Check(go.transform.childCount==(reduced?2:4),"Reduced motion omits both star particles");fx.Advance(reduced?.06f:.09f);Check(fx.Running,"Feedback remains active halfway");fx.Advance(1);Check(!go,"Feedback finishes safely and destroys only presentation");report.animationCases++;}}
  public static void Run(){
   output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW111_OUT")??"../Verification/Evidence/Review111");Directory.CreateDirectory(Path.Combine(output,"Native","TeamsMail111"));report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,scope="Actual Unity Editor scripted social/parser/journal and synthetic UGUI layout; no HTTP, APK, device, provider or production acceptance."};int locale=GameLocale.Current;bool had=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int saved=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);string profiles=Digest(Path.Combine(Application.persistentDataPath,"Profiles")),server=Digest(Path.Combine(Application.persistentDataPath,"ServerReview")),settings=Digest("ProjectSettings");Application.logMessageReceived+=Log;
   try{Check(Application.unityVersion=="2022.3.62f3","Pinned engine");EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);assets=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(assets,"Existing Teams asset");MailProtocol();MailActions();MailRejection();MailAnimations();MailLayouts();Check(report.actualHttpRequests==0,"Scripted suite makes no real HTTP");}catch(Exception e){report.errors.Add(e.ToString());}
   finally{GameLocale.Select(locale);report.ordinaryProfilesPreserved=profiles==Digest(Path.Combine(Application.persistentDataPath,"Profiles"));report.serverReviewPreserved=server==Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));report.settingsPreserved=settings==Digest("ProjectSettings");report.languagePreferencePreserved=had==PlayerPrefs.HasKey(GameLocale.PreferenceKey)&&saved==PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);if(!report.ordinaryProfilesPreserved||!report.serverReviewPreserved||!report.settingsPreserved||!report.languagePreferencePreserved)report.errors.Add("Preservation check failed");Application.logMessageReceived-=Log;report.status=report.errors.Count==0?"PASS_NATIVE_TEAMS_MAIL111":"FAIL_NATIVE_TEAMS_MAIL111";File.WriteAllText(Path.Combine(output,"Native","TeamsMail111.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));}EditorApplication.Exit(report.errors.Count==0?0:1);
  }
  static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}
 }
}
#endif
