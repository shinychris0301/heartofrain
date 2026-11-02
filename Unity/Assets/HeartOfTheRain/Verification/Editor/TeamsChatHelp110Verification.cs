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
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
namespace HeartOfTheRain.Verification {
 // Independent actual-client/scripted transport and separately labelled visual fixture.
 public static class TeamsChatHelp110Verification {
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
   byte[] data;public int writes,reads;public bool failNext;
   public byte[] Read(){reads++;return data==null?null:(byte[])data.Clone();}
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
  static void ImportRoles(){
   string[] files=Directory.GetFiles("Assets/HeartOfTheRain/App/TeamsSocial/Art","TC_*.png");Check(files.Length==10,"Exactly ten new approved TC PNGs are present");
   foreach(string path in files){var importer=AssetImporter.GetAtPath(path) as TextureImporter;var sprite=AssetDatabase.LoadAssetAtPath<Sprite>(path);Check(importer&&sprite&&importer.textureType==TextureImporterType.Sprite&&!importer.isReadable&&importer.alphaIsTransparency,"Imported TC role is a non-readable alpha sprite "+path);bool bubble=Path.GetFileName(path).StartsWith("TC_Bubble_",StringComparison.Ordinal);Check(bubble?!importer.mipmapEnabled&&importer.filterMode==FilterMode.Bilinear&&sprite.border.sqrMagnitude>0:importer.mipmapEnabled&&importer.filterMode==FilterMode.Trilinear,"TC role keeps appropriate sliced/detailed filtering "+path);Check(importer.textureCompression==TextureImporterCompression.Uncompressed,"TC artwork keeps its source pixel clarity "+path);byte[] png=File.ReadAllBytes(path);int w=png[16]<<24|png[17]<<16|png[18]<<8|png[19],h=png[20]<<24|png[21]<<16|png[22]<<8|png[23];Check(importer.maxTextureSize>=Math.Max(w,h),"TC source pixel budget is retained "+path);Check(assets.Find(Path.GetFileNameWithoutExtension(path))==sprite,"Actual Teams lookup resolves the exact TC sprite "+path);}
   foreach(string id in new[]{"TA_Stat_heart","TA_Stat_star","TA_Icon_Help"}){var sprite=assets.Find(id);var importer=AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(sprite)) as TextureImporter;Check(sprite&&importer&&importer.mipmapEnabled&&importer.filterMode==FilterMode.Trilinear,"Original detailed R4 feedback role remains intact "+id);}
  }
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
                string relative="Native/TeamsChatHelp110/"+name;File.WriteAllBytes(Path.Combine(output,relative),pixels.EncodeToPNG());report.captures.Add(relative);
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
  sealed class Scripted:IDisposable {
   public readonly MemoryStore store;public SocialBackendClient82 client;public SocialPageSession82 session;
   public long generation=1;public double clock;public bool member=true,unknownNext,rejectNext,failReads;public string memberTeam=Team,getError,wireOverride;public int exchanges,posts,accessChecks;public string path,body,method;public string lastPostPath,lastPostBody;
   public SocialLifeRequest110 own,other=Life();public SocialMessages82 messages=Messages();public SocialLifeRequest110[] owned=new SocialLifeRequest110[0];public bool ownedMore;public long ownedCursor;
   public SocialMutation82 nextReceipt;public readonly Dictionary<string,string> receipts=new Dictionary<string,string>();public readonly List<string> readPaths=new List<string>();
   public Scripted(MemoryStore shared=null){store=shared??new MemoryStore();Open();}
   public void Open(){var access=new SocialAccess82(Player,IdentityProtocol82.NewSecret());client=new SocialBackendClient82(Origin,()=>{accessChecks++;return access;},Dispatch,store,true,false);session=new SocialPageSession82(client,null,()=>generation,()=>clock);}
   public void Reopen(){report.actualHttpRequests+=client.VerificationRequests;session.Dispose();Open();}
   static string IteratorText(IEnumerator value,string name)=>(string)value.GetType().GetField(name,Private|BindingFlags.Public).GetValue(value);
   public void Dispatch(IEnumerator exchange){
    if(exchange.GetType().Name.StartsWith("<Exchange>",StringComparison.Ordinal)){
     exchanges++;method=IteratorText(exchange,"method");path=IteratorText(exchange,"path");body=IteratorText(exchange,"body");string json=null,error=null;bool unknown=false;
     if(method=="POST"){posts++;lastPostBody=body;lastPostPath=path;if(unknownNext){unknownNext=false;error="SocialNetworkUnavailable";unknown=true;}else if(rejectNext){rejectNext=false;error="SocialHttp409";}else json=Response();}
     else {readPaths.Add(path);if(failReads){error="SocialNetworkUnavailable";}else if(getError!=null){error=getError;getError=null;}else if(wireOverride!=null){json=wireOverride;wireOverride=null;}else json=Response();}
     CompleteScripted(client,exchange,json,error,unknown);return;
    }
    int steps=0;try{while(exchange.MoveNext()){Check(++steps<120,"Only bounded actual component refresh orchestration is advanced");if(exchange.Current is IEnumerator child)Dispatch(child);else Check(exchange.Current==null,"Scripted component yields no real network/native wait");}}finally{(exchange as IDisposable)?.Dispose();}
   }
   string Response(){
    if(method=="POST"){
     if(receipts.TryGetValue(body+path,out var prior))return prior;
     if(path.Contains("life-requests")){var r=nextReceipt??Receipt(path.EndsWith("/claim",StringComparison.Ordinal)?"life.claim":path.EndsWith("/help",StringComparison.Ordinal)?"life.help":"life.request",path.EndsWith("/claim",StringComparison.Ordinal)?"Deferred":path.EndsWith("/help",StringComparison.Ordinal)?"Sent":"Requested");nextReceipt=null;string reply=JsonUtility.ToJson(r);receipts.Add(body+path,reply);return reply;}
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
    if(path.StartsWith("/v1/teams/"+Team+"/mail?",StringComparison.Ordinal))return JsonUtility.ToJson(new SocialMailList111{teamId=Team,serverUtc=Utc,olderCursor=0,unreadCount=0,messages=new SocialMailMessage111[0]});
    if(path.StartsWith("/v1/messages/Team/",StringComparison.Ordinal))return JsonUtility.ToJson(messages);
    throw new InvalidOperationException("UnexpectedSynthetic110Read");
   }
   public void Select(){session.Show(SocialPane82.Teams);Check(session.RefreshTeams(),"Actual session accepts directory request");Check(session.SelectTeam(Team),"Actual session selects a projected team");session.Show(SocialPane82.TeamChat);Check(session.RefreshTeamMessages()&&session.Snapshot<SocialMessages82>(SocialPane82.TeamChat)?.nextCursor==2&&session.Status(SocialPane82.TeamChat).state==SocialViewState82.Ready,"Actual strict transport accepts the complete scripted history cursor contract");}
   public void Dispose(){report.actualHttpRequests+=client.VerificationRequests;session.Dispose();store.Dispose();}
  }
  static void Protocol(){
   string clean;string emoji=string.Concat(Enumerable.Repeat("\U0001F327",1000));Check(SocialBackendClient82.TryMessageDraft110(emoji,out clean)&&clean==emoji,"Approved1000 scalar message accepts2000 UTF16 units");foreach(string bad in new[]{"",new string('x',1001),"\ud800","a\u0001b",new string('x',2001)})Check(!SocialBackendClient82.TryMessageDraft110(bad,out clean),"Invalid/oversized message rejected before dispatch");
   var raw=JsonUtility.FromJson<SocialLifeRequests110>(JsonUtility.ToJson(new SocialLifeRequests110{ownRequest=null,requests=new SocialLifeRequest110[0]}));report.rawJsonNullOwnRequestMaterializes=raw.ownRequest!=null;Check(raw.ownRequest==null||string.IsNullOrEmpty(raw.ownRequest.requestId),"Real JsonUtility null custom-class behavior is characterized");
   using(var f=new Scripted()){
    f.Select();Check(f.session.RefreshTeamLives110()&&f.session.Snapshot<SocialLifeRequests110>(SocialPane82.TeamLives110)?.ownRequest==null,"Session clone normalizes genuinely absent ownRequest back to null");
    int count=f.exchanges;SocialReply82<SocialLifeRequests110> r=null;f.client.GetTeamLives110(Team,1,new[]{Message},x=>r=x);Check(r!=null&&!r.Succeeded&&count==f.exchanges,"Cursor and message-ID lookups are exclusive before dispatch");
    foreach(string malformed in new[]{LifeJson(null,new[]{Life()}).Replace("\"ownRequest\":null","\"ownRequest\":{}"),LifeJson(null,new[]{Life()}).Replace("\"capacity\":5","\"capacity\":6"),LifeJson(null,new[]{Life()}).Replace("\"helpSpendsDonorLives\":false","\"helpSpendsDonorLives\":true"),LifeJson(null,new[]{Life()}).Replace("\"remaining\":2","\"remaining\":1"),LifeJson(null,new[]{Life()}).Replace("\"received\":2","\"received\":6"),LifeJson(null,new[]{Life()}).Replace("\"requests\":[","\"requests\":[{},"),LifeJson(null,new[]{Life()}).Replace("\"serverUtc\":"+Utc,"\"serverUtc\":"+Utc+",\"serverUtc\":"+Utc)}){f.wireOverride=malformed;r=null;f.client.GetTeamLives110(Team,0,null,x=>r=x);Check(r!=null&&!r.Succeeded,"Malformed non-null request/policy/receipt or duplicate field is rejected strictly");}
    var second=Life();second.requestId="77777777777777777777777777777777";second.eventId="99999999999999999999999999999999";second.sequence=3;f.wireOverride=LifeJson(null,new[]{Life(),second});r=null;f.client.GetTeamLives110(Team,0,null,x=>r=x);Check(r!=null&&!r.Succeeded,"Distinct request IDs with duplicate message IDs reject before renderer dictionary");second.messageId="88888888888888888888888888888888";second.sequence=2;f.wireOverride=LifeJson(null,new[]{Life(),second});r=null;f.client.GetTeamLives110(Team,0,null,x=>r=x);Check(r!=null&&!r.Succeeded,"Duplicate/nonascending life message sequences reject at transport");second.sequence=3;f.wireOverride=LifeJson(null,new[]{Life(),second});r=null;f.client.GetTeamLives110(Team,0,null,x=>r=x);Check(r!=null&&r.Succeeded&&r.value.requests.Length==2,"Distinct ascending selected-message hydration remains valid");
    f.own=Life(true);f.session.RefreshTeamLives110();f.clock=25;Check(f.session.LifeServerNow110>=Utc+25,"Trusted clock advances from server anchor");f.nextReceipt=Receipt("life.request");f.session.RequestTeamLives110(Id());Check(f.session.LastLifeReceipt110?.operation=="life.request"&&f.session.LifeServerNow110>=Utc+25,"Old immutable receipt cannot rewind trusted cooldown");
    f.getError="SocialNetworkUnavailable";f.session.RefreshTeamLives110();Check(f.session.Status(SocialPane82.TeamLives110).state==SocialViewState82.Offline&&f.session.Snapshot<SocialLifeRequests110>(SocialPane82.TeamLives110)!=null,"Network loss preserves cached life projection");
    f.getError="SocialHttp404";f.session.RefreshTeamLives110();Check(f.session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)!=null&&f.session.Snapshot<SocialMessages82>(SocialPane82.TeamChat)!=null,"Unimplemented help404 does not remove ordinary chat/member authority");
    f.getError="SocialHttp403";f.session.RefreshTeamLives110();Check(f.session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)==null&&f.session.Snapshot<SocialMessages82>(SocialPane82.TeamChat)==null&&f.session.Snapshot<SocialLifeRequests110>(SocialPane82.TeamLives110)==null,"Permission removal clears affected private views");report.cases+=12;
   }
   using(var f=new Scripted()){
    f.Select();f.owned=new[]{Life(true,"Claimable",5,2)};f.ownedMore=true;f.ownedCursor=2;f.session.RefreshOwnedLives110();var first=f.session.Snapshot<SocialOwnedLives110>(SocialPane82.OwnedLives110);Check(first?.hasMore==true&&first.nextCursor==2&&first.requests[0].remaining==3,"Owned entitlements expose bounded server pagination");f.session.LeaveTeam(Id());f.member=false;f.session.RefreshTeams();Check(f.session.SelectedTeamId==null,"Confirmed leave clears selected team");f.owned=new[]{Life(true,"Claimable",4,1)};f.owned[0].requestId="77777777777777777777777777777777";f.owned[0].messageId="88888888888888888888888888888888";f.owned[0].eventId="99999999999999999999999999999999";f.owned[0].sequence=3;f.ownedMore=false;f.ownedCursor=0;f.session.RefreshOwnedLives110(2);Check(f.path.Contains("after=2")&&f.session.Snapshot<SocialOwnedLives110>(SocialPane82.OwnedLives110)?.requests[0].remaining==3,"Paged banked entitlement stays owner-readable after leaving team");
    string claim=Id();f.nextReceipt=Receipt("life.claim","Deferred",5,2,0);Check(f.session.ClaimTeamLives110(claim,Request)&&f.session.LastLifeReceipt110?.state=="Deferred"&&f.client.PendingCommand==null,"Confirmed Deferred0 clears exact intent without inventing a reward");f.nextReceipt=Receipt("life.claim","PartiallyCollected",5,4,2);f.session.ClaimTeamLives110(Id(),Request);Check(f.session.LastLifeReceipt110?.creditedLives==2&&f.session.LastLifeReceipt110.remaining==1,"Later explicit new claim ID can collect within capacity");
    f.unknownNext=true;string lost=Id();f.session.ClaimTeamLives110(lost,Request);var pending=f.client.PendingCommand;Check(pending?.commandId==lost&&pending.operation=="life.claim","Unknown claim remains in durable protected journal");string body=pending.body,path=pending.path;int posts=f.posts;f.Reopen();Check(f.client.PendingCommand?.body==body&&f.client.PendingCommand.path==path,"Reconstructed client reads exact prior intent from retained CAS store");f.nextReceipt=Receipt("life.claim","Collected",5,5,1);f.session.ResumePending();Check(f.posts==posts+1&&f.lastPostBody==body&&f.lastPostPath==path&&f.client.PendingCommand==null&&f.session.LastLifeReceipt110?.remaining==0,"Reconstructed same-ID retry confirms exact claim and clears journal");
    f.store.failNext=true;posts=f.posts;SocialReply82<SocialMutation82> bad=null;f.client.RequestTeamLives110(Id(),Team,x=>bad=x);Check(bad!=null&&!bad.Succeeded&&f.posts==posts,"CAS prepare failure cannot dispatch a life mutation");
    f.nextReceipt=Receipt("life.help","Sent",3);f.nextReceipt.requestId=Other;bad=null;f.client.HelpTeamLife110(Id(),Team,Request,x=>bad=x);Check(bad!=null&&!bad.Succeeded&&f.client.PendingCommand!=null,"Wrong-target confirmed receipt cannot clear exact pending help");string why;f.client.AcknowledgeAndDiscardPending(f.client.PendingCommand.commandId,true,out why);
    f.generation++;Check(f.session.LastLifeReceipt110==null&&f.session.Snapshot<SocialOwnedLives110>(SocialPane82.OwnedLives110)==null,"Owner epoch change hides prior receipts and owned cache");report.cases+=10;
   }
   foreach(string transition in new[]{"leave","directory-none","directory-other","select-other"})using(var f=new Scripted()){
    f.Select();f.owned=new[]{Life(true,"Claimable",5,2)};f.session.RefreshOwnedLives110();f.messages=Messages();f.messages.messages[0].sequence=3;f.messages.olderCursor=f.messages.nextCursor=3;Check(f.session.ProbeTeamMessages110()&&f.session.Snapshot<SocialMessages82>(SocialPane82.TeamTail110)!=null&&f.session.HasNewTeamMessages110,"Actual latest-message probe populates separate tail without replacing history");Check(f.session.Snapshot<SocialMessages82>(SocialPane82.TeamChat).nextCursor==2,"Probe preserves older visible history projection");
    if(transition=="leave")f.session.LeaveTeam(Id());else if(transition=="directory-none"){f.member=false;f.session.RefreshTeams();}else if(transition=="directory-other"){f.memberTeam=Other;f.session.RefreshTeams();}else f.session.SelectTeam(Other);
    Check(f.session.Snapshot<SocialMessages82>(SocialPane82.TeamTail110)==null&&!f.session.HasNewTeamMessages110,"Confirmed team transition clears old private probe and new-message flag: "+transition);Check(f.session.Snapshot<SocialOwnedLives110>(SocialPane82.OwnedLives110)?.requests[0].remaining==3,"Team transition preserves owner-bank entitlement: "+transition);report.cases++;
   }
  }
  static void RegionControls(){
   foreach(string region in new[]{"","RU"}){
    var view=new OnlineTeamsView82{connected=true,tab=2,team=TeamView(),regionCode=region};
    var frame=OnlineTeamsLayout82.Build(360,640,view);
    Check(!frame.chrome.elements.Any(e=>e.action=="choose-country"),"Teams rankings never offer country selection");
    Check(frame.chrome.elements.Any(e=>e.action=="scope-regional")==region.Length>0,"Teams regional scope appears only for a saved region");
   }
   var cached=Visual("Chat");cached.busy=true;cached.composerAvailable110=true;
   var chat=TeamsSocialLayout110.Build(360,800,cached);
   Check(chat.chrome.elements.Any(e=>e.id=="online-compose"&&e.action=="compose"),"Cached chat can open composer while a replaceable background read is busy");
   cached.composing110=true;cached.messageDraft110="A valid cached draft";
   chat=TeamsSocialLayout110.Build(360,800,cached);
   Check(chat.chrome.elements.Any(e=>e.id=="online-compose-send"&&e.action=="send"),"Cached composer can send during a replaceable background read");
   report.cases++;
  }
  static void ComponentActions(){
   var prior=EventSystem.current;var selected=prior?prior.currentSelectedGameObject:null;var eventRoot=new GameObject("Teams110 explicit isolated EventSystem");var events=eventRoot.AddComponent<EventSystem>();typeof(EventSystem).GetMethod("OnEnable",Private).Invoke(events,null);EventSystem.current=events;
   var root=new GameObject("Teams110 actual controller with scripted transport");
   try{using(var f=new Scripted()){
    var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;page.ConfigureForVerification(assets,f.session,f.Dispatch);page.VerificationViewport(720,1600);page.Show();page.VerificationPump();Check(page.VerificationNodes.ContainsKey("online-request-lives")&&f.session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)?.isMember==true,"Actual member Chat route renders request action and server member state");
    int directoryRead=f.readPaths.FindIndex(path=>path.StartsWith("/v1/teams?",StringComparison.Ordinal));int detailRead=f.readPaths.FindIndex(path=>path=="/v1/teams/"+Team);int chatRead=f.readPaths.FindIndex(path=>path.StartsWith("/v1/messages/Team/",StringComparison.Ordinal));int savedLivesRead=f.readPaths.FindIndex(path=>path.StartsWith("/v1/life-requests/owned?",StringComparison.Ordinal));int savedMailRead=f.readPaths.FindIndex(path=>path.StartsWith("/v1/mail/rewards/owned?",StringComparison.Ordinal));
    Check(directoryRead==0&&detailRead>directoryRead&&chatRead>detailRead&&savedLivesRead>chatRead&&savedMailRead>chatRead,"Cold member entry fetches team and chat before independent saved-life and saved-mail reads");
    int posts=f.posts;f.own=Life(true);f.session.RefreshTeamLives110();page.Request("request-lives");Check(f.posts==posts,"Existing open request scroll action sends no duplicate write");
    f.own=null;f.session.RefreshTeamLives110();f.nextReceipt=Receipt("life.request");page.Request("request-lives");page.VerificationPump();Check(f.posts==posts+1&&f.session.LastLifeReceipt110?.operation=="life.request","Actual request action sends one service command only after availability");
    f.other=Life();f.session.RefreshTeamLives110();f.nextReceipt=Receipt("life.help","Sent",3);page.Request("help-life:"+Request);page.VerificationPump();Check(f.session.LastLifeReceipt110?.operation=="life.help"&&f.session.LastLifeReceipt110.creditedLives==0,"Actual Help action confirms no donor reward or wallet projection");
    var fx=page.VerificationFeedback110;if(fx){string receipt=fx.ReceiptId;page.VerificationAdvance110(.3f);Check(fx.Heart&&fx.Heart.localScale.x<=1.251f&&fx.Heart.localScale.x>=1,"Confirmed presentation pulse respects1.25 scale budget");page.VerificationPump();Check(page.VerificationFeedback110==fx&&fx.ReceiptId==receipt,"Same receipt does not start a duplicate animation");page.Hide(false);Check(!page.VerificationFeedback110,"Hiding actual page cancels transient confirmed feedback");page.Show();page.VerificationPump();}
    page.Request("compose");Check(page.VerificationNodes.ContainsKey("online-message-input")&&events.currentSelectedGameObject==page.VerificationNodes["online-message-input"].gameObject,"Actual compose action creates and selects editor");page.VerificationNodes["online-message-input"].GetComponent<InputField>().text="Typed actual input\nkeeps its draft";var activeInput=page.VerificationNodes["online-message-input"];Set(page,"verificationKeyboard110",500f);page.VerificationPump();Check(page.VerificationNodes["online-message-input"]==activeInput,"Live keyboard keeps the exact composer InputField during typing");Set(page,"verificationKeyboard110",0f);page.VerificationPump();Check(page.VerificationNodes["online-message-input"]!=activeInput,"Keyboard close restores layout without preserving the stale InputField");float fullHeight=page.VerificationFrame.height;page.VerificationKeyboard110(500);Check(page.VerificationFrame.height<fullHeight&&Field<string>(page,"messageDraft")=="Typed actual input\nkeeps its draft"&&page.VerificationNodes["online-message-input"].GetComponent<InputField>().text==Field<string>(page,"messageDraft"),"Actual InputField onValueChanged draft survives simulated keyboard reflow exactly");Check(events.currentSelectedGameObject!=page.VerificationNodes["online-message-input"].gameObject,"Keyboard resize never reactivates the replaced input connection");bool invalidCount;Check(page.VerificationNodes["online-message-count"].GetComponent<Text>().text==TeamsSocialLayout110.DraftCount110(Field<string>(page,"messageDraft"),out invalidCount)&&!invalidCount,"Actual visible composer counter matches retained typed draft after keyboard reflow");page.VerificationKeyboard110(0);Check(events.currentSelectedGameObject!=page.VerificationNodes["online-message-input"].gameObject,"Closing keyboard does not reactivate composer input");page.Request("cancel-compose");page.Request("compose");Set(page,"messageDraft","Cancelled draft remains");var oldFocus=events.currentSelectedGameObject;f.session.RefreshTeamLives110();Check(!oldFocus&&page.VerificationNodes.ContainsKey("online-message-input")&&Field<string>(page,"messageDraft")=="Cancelled draft remains","Background reflow retains composer draft without reopening a closed keyboard");int cancelPosts=f.posts;page.Request("cancel-compose");Check(Field<string>(page,"modal")==""&&Field<string>(page,"messageDraft")=="Cancelled draft remains"&&f.posts==cancelPosts,"Cancel safely handles destroyed Unity focus and retains draft without write");page.Request("compose");foreach(string invalid in new[]{new string('x',1001),string.Concat(Enumerable.Repeat("\U0001F327",1001))}){Set(page,"messageDraft",invalid);int before=f.posts;page.Request("send");Check(f.posts==before&&Field<string>(page,"messageDraft")==invalid&&f.client.PendingCommand==null,"More than1000 ASCII/supplementary scalars preserve draft and cannot send");}Set(page,"messageDraft","Retained uncertain message");f.unknownNext=true;page.Request("send");string pending=f.client.PendingCommand?.body;Check(pending!=null&&Field<string>(page,"messageDraft")=="Retained uncertain message","Synchronous Send/Reflow safely handles focus while unknown reply preserves exact outbox and draft");page.Hide(false);page.Show();Check(Field<string>(page,"messageDraft")=="Retained uncertain message"&&f.client.PendingCommand?.body==pending,"Page hide/show preserves unconfirmed message text and intent");page.Request("resume-pending");page.VerificationPump();Check(f.client.PendingCommand==null&&Field<string>(page,"messageDraft")=="","Only acknowledged message receipt clears matching draft");
    f.messages=new SocialMessages82{messages=new SocialMessage82[0],nextCursor=0,hasNewer=false,hasOlder=false};f.session.RefreshTeamMessages();page.VerificationPump();Invoke(page,"ObserveRead");Check(Field<bool>(f.session,"messageViewportAtLatest"),"Empty team chat remains at latest so another member's first message is polled");page.Request("tab-mail");Check(page.VerificationNodes.ContainsKey("mail-unread")||page.VerificationNodes.ContainsKey("mail-load"),"Mail routes to the new server-backed inbox or its loading/error state");page.Request("tab-chat");page.Request("tab-info");Check(page.VerificationFrame.content.elements.Any(e=>e.action=="leave"),"Existing member info/leave route remains available");page.Hide(false);report.cases+=10;
   }}finally{if(events)events.SetSelectedGameObject(null);UnityEngine.Object.DestroyImmediate(root);typeof(EventSystem).GetMethod("OnDisable",Private).Invoke(events,null);UnityEngine.Object.DestroyImmediate(eventRoot);if(prior){EventSystem.current=prior;prior.SetSelectedGameObject(selected);}Check(EventSystem.current==(prior?prior:null)&&(!prior||prior.currentSelectedGameObject==selected),"Prior EventSystem and selection are restored");}
  }
  static void OfflineShortCircuit(){
   var root=new GameObject("Teams110 offline refresh contract");
   try{using(var f=new Scripted()){
    f.failReads=true;var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;page.ConfigureForVerification(assets,f.session,f.Dispatch);page.VerificationViewport(720,1600);page.Show();
    Check(f.exchanges==1&&f.session.Status(SocialPane82.Teams).state==SocialViewState82.Offline&&!page.VerificationPending,"First offline team read stops serialized initial Teams loading");
    Check(Field<string>(page,"localNotice")==OnlineTeamsText82.T("Offline")&&page.VerificationNodes.ContainsKey("online-retry"),"Initial offline response renders the retry notice and enabled retry control");
    page.Hide(false);report.cases++;
   }}finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  static void ColdDirectoryOrder(){
   var root=new GameObject("Teams110 cold directory and saved rewards contract");
   try{using(var f=new Scripted()){
    f.member=false;f.owned=new[]{Life(true,"Claimable",5,2)};
    var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;page.ConfigureForVerification(assets,f.session,f.Dispatch);page.VerificationViewport(720,1600);page.Show();
    int directory=f.readPaths.FindIndex(path=>path.StartsWith("/v1/teams?",StringComparison.Ordinal));int lives=f.readPaths.FindIndex(path=>path.StartsWith("/v1/life-requests/owned?",StringComparison.Ordinal));int mail=f.readPaths.FindIndex(path=>path.StartsWith("/v1/mail/rewards/owned?",StringComparison.Ordinal));
    Check(directory==0&&lives>directory&&mail>lives,"Cold directory appears before saved entitlement reads without skipping them");
    Check(f.session.Snapshot<SocialOwnedLives110>(SocialPane82.OwnedLives110)?.requests?.Length==1&&f.session.Snapshot<SocialOwnedMail111>(SocialPane82.OwnedMail111)!=null,"No-team player retains owned lives and mail projections after reordered refresh");page.Hide(false);report.cases++;
   }}finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  static void WarmEntryAndNavigation(){
   foreach(bool member in new[]{true,false}){
    var root=new GameObject("Teams124 background read and local navigation contract");
    try{using(var f=new Scripted()){
     f.member=member;f.other=null;var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;
     page.ConfigureForVerification(assets,f.session,f.Dispatch);page.VerificationViewport(720,1600);page.VerificationWarm();
     int directory=f.readPaths.FindIndex(path=>path.StartsWith("/v1/teams?",StringComparison.Ordinal));
     int detail=f.readPaths.FindIndex(path=>path=="/v1/teams/"+Team);
     int chat=f.readPaths.FindIndex(path=>path.StartsWith("/v1/messages/Team/",StringComparison.Ordinal));
     int saved=f.readPaths.FindIndex(path=>path.StartsWith("/v1/life-requests/owned?",StringComparison.Ordinal));
     Check(directory==0&&saved>directory&&(!member||detail>directory&&chat>detail&&saved>chat),"Only confirmed members prefetch private chat before owner entitlements");
     Check(member||detail<0&&chat<0,"No-team warm read never requests private team detail or chat");
     Check(!f.session.IsVisible&&!page.IsVisible&&f.posts==0,"Warmup issues reads only and never opens a page or mutates team state");
     int reads=f.readPaths.Count;string cachedChat=member?JsonUtility.ToJson(f.session.Snapshot<SocialMessages82>(SocialPane82.TeamChat)):"";page.Show();Check(f.readPaths.Count==reads&&!page.VerificationPending,"Fresh warm cache opens Teams without a second directory or loading pass reads="+reads+" after="+f.readPaths.Count+" pending="+page.VerificationPending+" warming="+Field<bool>(page,"warming")+" fresh="+Field<double>(page,"warmFreshUntil")+" now="+System.Diagnostics.Stopwatch.GetTimestamp()/(double)System.Diagnostics.Stopwatch.Frequency);Check(!member||cachedChat==JsonUtility.ToJson(f.session.Snapshot<SocialMessages82>(SocialPane82.TeamChat)),"Read-only chat layout does not mutate the authoritative cached messages");
     if(member){
      Check(page.VerificationNodes.ContainsKey("online-compose"),"Warm member entry renders server chat immediately");
      var original=page.VerificationNodes["online-chat-tabs-base"];
      page.VerificationViewport(720,1600);Check(ReferenceEquals(original,page.VerificationNodes["online-chat-tabs-base"]),"Identical Teams model reuses the actual UGUI objects instead of rebuilding them");
      page.Hide(false);page.Show();Check(ReferenceEquals(original,page.VerificationNodes["online-chat-tabs-base"]),"Returning to the same cached chat keeps its UGUI hierarchy");
      Set(f.session,"inFlight",true);page.Hide(false);page.Show();Check(ReferenceEquals(original,page.VerificationNodes["online-chat-tabs-base"]),"Cancelling a replaceable cached read during Home navigation keeps the chat hierarchy");
      f.messages.messages[0].text="Updated server message";Check(f.session.RefreshTeamMessages()&&f.session.Snapshot<SocialMessages82>(SocialPane82.TeamChat)?.messages?[0].text=="Updated server message","Changed scripted message reaches the real session cache");
      Check(!ReferenceEquals(original,page.VerificationNodes["online-chat-tabs-base"]),"Changed server chat data invalidates the reusable frame and renders new content");
      Set(f.session,"inFlight",true);int posts=f.posts;
      page.Request("tab-info");Check(Field<int>(page,"tab")==1,"Info navigation responds during a background read");
      page.Request("tab-ranks");Check(Field<int>(page,"tab")==2,"Ranks navigation responds during a background read");
      page.Request("tab-chat");page.Request("tab-mail");Check(Field<bool>(page,"mail110")&&f.posts==posts,"Mail navigation responds without submitting a write during a read");
      Set(f.session,"inFlight",false);
     }
     page.Hide(false);report.cases++;
    }}finally{UnityEngine.Object.DestroyImmediate(root);}
   }
  }
  static void StatusPlacement(){
   var view=new OnlineTeamsView82{tab=0,connected=true,team=new SocialTeam82{isMember=true},status="Offline"};
   var frame=TeamsSocialLayout110.Build(360,640,view);
   var action=frame.chrome.elements.First(e=>e.id=="online-compose");var status=frame.chrome.elements.First(e=>e.id=="online-status");
   Check(status.y>=action.y+action.height-0.1f,"Team status appears below the chat actions instead of overlapping their hit targets");report.cases++;
  }
  static void PendingViewCache(){
   using(var store=new MemoryStore()){
    var owner=new ProtectedSocialCommandJournal82(store,Player,"https://api.example.test");int before=store.reads;
    for(int i=0;i<100;i++)Check(owner.CachedPending==null,"UI polling uses the already loaded pending state");
    Check(store.reads==before,"Repeated UI polling performs no protected-store reads");
    string id=Guid.NewGuid().ToString("N");var command=new SocialPendingCommand82{operation="message.send",path="/v1/messages/Team/"+Team,commandId=id,body="{\"commandId\":\""+id+"\",\"text\":\"hi\"}"};
    owner.Prepare(command);Check(owner.CachedPending?.commandId==id&&owner.Pending?.commandId==id,"A committed prepare updates both cached UI state and durable outbox");
    var copy=owner.CachedPending;copy.operation="modified";Check(owner.CachedPending.operation=="message.send","UI receives a copy of cached pending intent");
    var reopened=new ProtectedSocialCommandJournal82(store,Player,"https://api.example.test");Check(reopened.CachedPending?.commandId==id,"Restart loads pending intent from the protected store");
    reopened.Confirm(command);Check(reopened.CachedPending==null&&reopened.Pending==null,"Confirmed intent clears cached and durable state");report.cases++;
   }
  }
  static void PresentationOwnerRead(){
   using(var f=new Scripted()){
    int before=f.accessChecks;
    using(f.session.BeginPresentationRead()){
     Check(f.accessChecks==before+1,"Presentation entry checks the live authenticated owner once");
     for(int i=0;i<10;i++){
      Check(f.session.Status(SocialPane82.TeamChat).state==SocialViewState82.NotLoaded,"Read-only presentation retains cached pane status");
      Check(f.session.PlayerId==Player&&f.session.PendingCommand==null,"Read-only presentation retains the bound owner and pending state");
     }
     Check(f.accessChecks==before+1,"Repeated pane presentation performs no extra credential reads");
    }
    Check(f.session.Status(SocialPane82.TeamChat).state==SocialViewState82.NotLoaded&&f.accessChecks>before+1,"Outside presentation, owner checks are live again");
    f.generation++;
    Check(f.session.Status(SocialPane82.TeamChat).state==SocialViewState82.Unauthenticated,"A changed account generation invalidates cached presentation after the scope closes");
    report.cases++;
   }
  }
  static void DurableOwnerGuard(){
   using(var store=new MemoryStore())using(var client=new SocialBackendClient82(Origin,()=>new SocialAccess82(Player,IdentityProtocol82.NewSecret()),_=>throw new InvalidOperationException("UnexpectedDispatch"),store,true,false,()=>false)){
    SocialReply82<SocialMutation82> reply=null;
    client.SendMessage(Guid.NewGuid().ToString("N"),"Team",Team,"Hello",result=>reply=result);
    Check(reply?.error=="SocialOwnerChanged"&&!reply.unknown,"A stale durable identity blocks a social write before transport");
    Check(store.writes==0&&client.PendingCommand==null,"Blocked owner writes neither protected outbox nor network command");
    report.cases++;
   }
  }
  static void NavigationDiagnostics(){
   string path=Path.Combine(output,"Native","NavigationDiagnostics124.log");
   var log=new NavigationDiagnostics124(path);
   for(int i=0;i<300;i++)log.Record(NavigationEvent124.TeamsShow,i);
   log.Record((NavigationEvent124)999,12);
   Check(log.Read().Length==256,"Only a bounded number of fixed-code navigation samples remain in memory");
   Check(log.Save()&&new FileInfo(path).Length<=32768,"Bounded navigation samples save to a small local file");
   var restored=new NavigationDiagnostics124(path);
   Check(restored.Read().Length==256&&restored.Read()[0].milliseconds==44&&restored.Read()[255].milliseconds==299,"Navigation samples load across service reconstruction in order");
   Check(!File.ReadAllText(path).Contains("token")&&!File.ReadAllText(path).Contains("message"),"Navigation log stores no arbitrary private payload");
   report.cases++;
  }
  static void ReadWatchdog(){
   double now=0;IEnumerator held=null;var access=new SocialAccess82(Player,IdentityProtocol82.NewSecret());
   using(var store=new MemoryStore()){
    var client=new SocialBackendClient82(Origin,()=>access,iterator=>held=iterator,store,true,false);
    var session=new SocialPageSession82(client,null,()=>1,()=>now);
    try{
     session.Show(SocialPane82.Teams);Check(session.RefreshTeams()&&session.Busy&&held!=null,"Uncompleted actual read owns one client lease");
     now=19.9;Check(!session.FailStalledRead()&&session.Busy,"Read watchdog preserves an in-flight request before its deadline");
     now=20.1;Check(session.FailStalledRead()&&!session.Busy&&session.Status(SocialPane82.Teams).state==SocialViewState82.Offline,"Read watchdog releases a stalled GET and exposes an offline state");
     Check(!session.FailStalledRead(),"Completed timeout cannot cancel a second request");report.cases++;
     Check(session.RefreshTeams()&&session.ReadInFlight,"A second replaceable Teams read acquires the client");
     Check(session.YieldReadForForeground()&&!session.Busy&&!session.ReadInFlight&&session.Status(SocialPane82.Teams).state==SocialViewState82.Cancelled,"Foreground chat can cancel only an in-flight GET and release its lease");
     Check(session.RefreshTeams()&&session.Busy,"A fresh read can immediately use the released transport");
     Check(session.YieldReadForForeground()&&!session.Busy,"Repeated foreground preemption leaves no stuck loading lease");report.cases++;
     Check(session.CreateTeam(Id(),"QA team","Test team","drop")&&session.Busy&&!session.ReadInFlight,"Durable mutation holds a distinct write lease");
     Check(!session.YieldReadForForeground()&&session.Busy,"Foreground chat never cancels or supersedes a durable mutation");report.cases++;
    }finally{(held as IDisposable)?.Dispose();session.Dispose();}
   }
  }
  static void Animations(){
   foreach(bool reduced in new[]{false,true})foreach(string operation in new[]{"life.request","life.help","life.claim"}){
    var root=new GameObject("Teams110 presentation-only animation fixture",typeof(RectTransform));try{
     var fx=root.AddComponent<TeamsHelpFeedback110>();var start=new Vector3(-40,-20,0);var end=new Vector3(40,20,0);fx.Begin(Id(),operation,start,end,assets.Find("TA_Stat_heart"),assets.Find("TA_Stat_star"),reduced);Check(fx.Running&&fx.Reduced==reduced&&fx.ReceiptId.Length==32,"Animation accepts confirmed receipt identity and explicit motion policy");Check(root.GetComponent<CanvasGroup>()&&!root.GetComponent<CanvasGroup>().blocksRaycasts,"FX never captures input or changes fixed controls");RectTransform card=null;if(operation=="life.request"){var item=new GameObject("Explicit request card",typeof(RectTransform));item.transform.SetParent(root.transform,false);card=(RectTransform)item.transform;fx.AnimateRequest(new[]{card},12);Check(!fx.Heart.gameObject.activeSelf&&Math.Abs(card.localPosition.y-(reduced?0:12))<.01f&&card.GetComponent<CanvasGroup>().alpha==0,"Request feedback uses actual whole-card fade and optional12-unit rise");}float duration=reduced?.1f:operation=="life.request"?.18f:.6f;fx.Advance(duration/2);Check(fx.Running&&fx.Heart.localScale.x<=1.251f,"Midpoint stays inside approved animation budget");if(reduced)Check(Vector3.Distance(fx.Heart.localPosition,end)<.001f&&fx.Heart.localScale==Vector3.one,"Reduced motion uses stationary crossfade without travel/pulse");else Check(fx.Heart.localPosition.y>Vector3.Lerp(start,end,.5f).y,"Normal motion uses bounded rise/arc");fx.Advance(duration);Check(!fx.Running&&!root.activeSelf,"Presentation finishes at approved bounded duration");if(card)Check(card.localPosition==Vector3.zero&&card.GetComponent<CanvasGroup>().alpha==1,"Completed request animation restores exact card geometry and full alpha");report.animationCases++;
    }finally{UnityEngine.Object.DestroyImmediate(root);}
   }
  }
  static void DiscardRecovery(){
   foreach(bool claim in new[]{false,true}){
    var root=new GameObject("Teams110 explicit uncertain-discard controller fixture");try{using(var f=new Scripted()){
     var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;page.ConfigureForVerification(assets,f.session,f.Dispatch);page.VerificationViewport(720,1600);page.Show();page.VerificationPump();f.unknownNext=true;if(claim)f.session.ClaimTeamLives110(Id(),Request);else f.session.RequestTeamLives110(Id());var pending=f.client.PendingCommand;Check(pending!=null&&f.session.LastLifeReceipt110==null,"Synthetic uncertain mutation remains pending without success receipt");int posts=f.posts;page.Request("forget");Check(f.client.PendingCommand?.commandId==pending.commandId&&f.posts==posts,"Forget prompt alone never discards or resubmits a command");page.Request("confirm");Check(f.client.PendingCommand==null&&f.posts==posts&&page.VerificationWalletRefresh110==claim,"Explicit discard refreshes authoritative wallet only for a possibly committed claim");Check(f.session.LastLifeReceipt110==null&&!page.VerificationFeedback110,"Discard fabricates neither success receipt nor reward animation");page.Hide(false);page.VerificationPump();Check(!page.IsVisible&&page.VerificationWalletRefresh110==claim&&f.posts==posts,"Hidden actual page preserves queued refresh obligation without fabricated gateway success or new mutation");report.cases++;
    }}finally{UnityEngine.Object.DestroyImmediate(root);}
   }
  }
  static OnlineTeamsView82 Visual(string state){
   var v=new OnlineTeamsView82{connected=true,selfId=Player,team=TeamView(),tab=0,status="",chat=Messages(),life110=new SocialLifeRequests110{teamId=Team,serverUtc=Utc,policy=Policy(),requests=new[]{Life()},ownRequest=null},ownedLives110=new SocialOwnedLives110{serverUtc=Utc,policy=Policy(),requests=new SocialLifeRequest110[0]},now110=Utc,serviceReady110=true};
   if(state=="Empty")v.chat.messages=new SocialMessage82[0];
   if(state=="LongMessage")v.chat.messages[0].text=string.Join(" ",Enumerable.Repeat("Long village message with wrapped lines and plain <b>UGC</b>.",15));
   if(state=="Unbroken")v.chat.messages[0].text=new string('W',1000);
   if(state=="Unicode")v.chat.messages[0].text=string.Concat(Enumerable.Repeat("\U0001F327",1000));
   if(state=="OwnWaiting"){v.life110.ownRequest=Life(true);v.life110.requests=new[]{v.life110.ownRequest};v.life110.nextRequestAt=Utc+14340;}
   if(state=="HelpSent"){v.life110.requests[0].canHelp=false;v.life110.requests[0].helped=true;}
   if(state=="Expired"){v.life110.requests[0]=Life(false,"Expired");}
   if(state=="Claim"||state=="Partial"||state=="FullLives"){var life=Life(true,"Claimable",5,state=="Partial"?2:0);if(state=="FullLives"){life.canCollect=false;life.collectBlockedReason="FullLives";}v.life110.ownRequest=life;v.life110.requests=new[]{life};}
   if(state=="Pending"||state=="PendingError"){v.pending=true;v.lifePendingOperation110="life.help";v.lifePendingRequestId110=Request;if(state=="PendingError")v.lifeError110=TeamsSocialText110.T("help_error");}
   if(state=="Offline"){v.offline110=true;v.lifeError110=TeamsSocialText110.T("service_unavailable");}
   if(state=="Mail")v.mail110=true;
   if(state=="Saved"){v.giftsOpen110=true;v.ownedLives110.requests=new[]{Life(true,"Claimable",5,2)};v.ownedLives110.requests[0].teamId=Other;v.ownedLives110.hasMore=true;v.ownedLives110.nextCursor=5;}
   if(state=="Composer"||state=="Keyboard"){v.composing110=true;v.messageDraft110="A retained draft.\nSecond line.";v.keyboard110=state=="Keyboard";}
   if(state=="History"){v.chat.hasOlder=true;v.chat.hasNewer=true;v.hasNewMessages110=true;}
   return v;
  }
  static void Layouts(bool diagnostics=false){
   var root=new GameObject("Teams110 explicitly synthetic visual snapshots");bool capturedFailure=false;
   try{var page=root.AddComponent<OnlineTeamsPage82>();page.enabled=false;
    foreach(int locale in Enumerable.Range(0,5))foreach(var size in new[]{new Vector2Int(360,800),new Vector2Int(720,1600),new Vector2Int(768,1024)})foreach(string state in new[]{"Empty","Chat","LongMessage","Unbroken","Unicode","OwnWaiting","HelpSent","Expired","Claim","Partial","FullLives","Pending","PendingError","Offline","Mail","Saved","Composer","Keyboard","History"}){
     if(diagnostics&&!((locale==0&&size.x==360&&state=="Empty")||(locale==1&&size.x==360&&state=="OwnWaiting")||(locale==3&&size.x==360&&state=="Chat")||(locale==4&&size.x==768&&state=="Pending")))continue;
     GameLocale.Select(locale);var view=Visual(state);page.ConfigureViewForVerification(assets,view);page.VerificationViewport(size.x,size.y);page.VerificationSafeArea(size.x==360?new Rect(0,24,size.x,size.y-54):new Rect(0,0,size.x,size.y));page.VerificationKeyboard110(state=="Keyboard"?size.y*.35f:0);page.Show();PrepareCanvas(page,size);page.VerificationViewport(size.x,size.y);Canvas.ForceUpdateCanvases();ScrollTo(Field<ScrollRect>(page,"scroll"),1);
     var row=new Row{state=state,locale=locale,width=size.x,height=size.y,inset=size.x==360};report.rows.Add(row);report.layoutsAttempted++;
     try{ValidateGeometry(page,view,state);if(locale==4&&((size.x==720&&new[]{"Chat","OwnWaiting","Claim","Saved","Composer","Keyboard"}.Contains(state))||(size.x==768&&new[]{"Chat","PendingError"}.Contains(state))))Capture(page,size,state+"_ru_"+size.x+".png");row.passed=true;report.layouts++;}
     catch(Exception error){report.errors.Add("Visual-only "+state+"/locale"+locale+"/"+size+": "+error.Message);if(!capturedFailure){capturedFailure=true;try{Capture(page,size,"FirstFailure_"+state+"_locale"+locale+"_"+size.x+".png");}catch(Exception e){report.errors.Add("First failure capture: "+e.Message);}}}
     finally{if(diagnostics)Capture(page,size,"Diagnostic_"+state+"_locale"+locale+"_"+size.x+".png");page.Hide(false);page.ClearViewForVerification();}
    }
   }finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  static void ValidateGeometry(OnlineTeamsPage82 page,OnlineTeamsView82 view,string state){
   var frame=page.VerificationFrame;Check(frame.width>0&&frame.height>0&&frame.viewportHeight>0,"Safe chat viewport budget stays positive: frame="+frame.width+"x"+frame.height+" viewportY="+frame.viewportY+" height="+frame.viewportHeight+" dock="+MainNavigationLayout.ReservedHeight(frame.width,frame.height));
   var backdrop=Field<RectTransform>(page,"backdrop");var viewport=Field<RectTransform>(page,"viewport");var chrome=Field<RectTransform>(page,"chrome");var overlay=Field<RectTransform>(page,"overlay");
   Check(backdrop.GetSiblingIndex()<viewport.GetSiblingIndex()&&viewport.GetSiblingIndex()<chrome.GetSiblingIndex()&&chrome.GetSiblingIndex()<overlay.GetSiblingIndex(),"Chat backdrop stays below scrolling history while controls and dialogs stay above it");
   if(page.VerificationNodes.TryGetValue("online-teams-background",out var background))Check(background.IsChildOf(backdrop)&&!backdrop.GetComponent<CanvasGroup>().blocksRaycasts,"Full-screen team art cannot cover history or intercept touches");
   foreach(var layer in new[]{frame.chrome,frame.content,frame.overlay})foreach(var e in layer.elements){
    Check(e.width>0&&e.height>0&&!float.IsNaN(e.x+e.y+e.width+e.height),"Finite positive chat element "+e.id);Check(page.VerificationNodes.TryGetValue(e.id,out var node),"Actual chat element has a native node "+e.id);
    if(e.id.StartsWith("online-message-",StringComparison.Ordinal)&&e.id.EndsWith("-timestamp",StringComparison.Ordinal)){
     var bubble=frame.content.elements.FirstOrDefault(item=>item.id==e.id.Substring(0,e.id.Length-"-timestamp".Length)+"-base");
     Check(bubble!=null&&e.y+e.height<=bubble.y+bubble.height-12,"Message timestamp clears painted bubble border "+e.id);
    }
    if(e.kind=="text"||e.kind=="lefttext"||e.kind=="chatbody110"||e.kind=="chatname110"){
     var text=node.GetComponent<Text>();Check(text&&!text.supportRichText&&text.font,"UGC/localized label is plain native text "+e.id);bool wrap=e.kind=="chatbody110";Check((wrap||text.preferredWidth<=text.rectTransform.rect.width+1.5f)&&text.preferredHeight<=text.rectTransform.rect.height+1.5f,"Localized chat text fits "+state+"/"+GameLocale.Current+"/"+e.id+" preferred="+text.preferredWidth+"x"+text.preferredHeight+" box="+text.rectTransform.rect.size);var mesh=text.canvasRenderer.GetMesh();if(mesh&&mesh.vertexCount>0)GlyphBounds(page,e,node,text,mesh);
    }
    if(!string.IsNullOrEmpty(e.asset)&&(e.asset.StartsWith("TA_",StringComparison.Ordinal)||e.asset.StartsWith("TC_",StringComparison.Ordinal))){if(e.kind=="cover109"){var raw=node.GetComponent<RawImage>();Check(raw&&raw.texture==assets.Find(e.asset).texture&&!raw.maskable,"Background uses approved full-viewport texture without clipping");}else{var image=node.GetComponent<Image>();Check(image&&image.sprite==assets.Find(e.asset),"Native chat image uses exact approved sprite "+e.id);if(e.sliced)Check(image.type==Image.Type.Sliced&&image.sprite.border.sqrMagnitude>0,"Chat chrome retains real sliced borders "+e.id);if(e.asset=="TA_Stat_heart"&&e.color=="#FFFFFF")Check(image.color==Color.white,"Confirmed filled pink heart artwork is not tinted");}}
    if(layer!=frame.content&&e.id!="online-teams-background"&&e.id!="online-modal-shade"&&e.id!="country-shade")Check(e.x>=-.2f&&e.y>=-.2f&&e.x+e.width<=frame.width+.2f&&e.y+e.height<=frame.height+.2f,"Pinned chat node stays inside safe logical frame "+state+"/"+e.id);
   }
   Check(!view.keyboard110||!page.VerificationNodes.ContainsKey("dock-bg"),"Simulated keyboard state removes dock from reduced viewport");
   foreach(var e in frame.content.elements.Concat(frame.chrome.elements).Where(e=>!string.IsNullOrEmpty(e.action)&&e.action!="disabled"&&!e.id.StartsWith("nav-",StringComparison.Ordinal)&&e.kind=="group"))Check(e.height>=47.9f,"Chat/help actionable control retains48 logical touch height "+e.id);
   if(view.composing110){var input=page.VerificationNodes["online-message-input"].GetComponent<InputField>();Check(input&&input.characterLimit==2000&&input.lineType!=InputField.LineType.SingleLine,"Actual composer exposes multiline raw2000UTF16 budget");Check(input.text==view.messageDraft110,"Explicit visual fixture presents the same draft as its counter");}
   if(view.pending)foreach(string id in new[]{"online-check","online-resume","online-forget"}){var hit=frame.chrome.elements.Single(e=>e.id==id);var label=page.VerificationNodes[id+"-label"].GetComponent<Text>();Check(Words(label.text)==Words(hit.label)&&label.cachedTextGenerator.lineCount<=2,"Pending recovery keeps all words and at most2 actual lines "+id);}
   var scroll=Field<ScrollRect>(page,"scroll");Check(scroll&&scroll.vertical&&!scroll.horizontal&&scroll.viewport==scroll.transform&&scroll.viewport.GetComponent<RectMask2D>(),"Actual chat uses clipped vertical history scroll");
   if(state=="LongMessage"||state=="Saved"){var canvas=(RectTransform)page.VerificationCanvas.transform;var fixedNodes=page.VerificationNodes.Where(p=>p.Key=="dock-bg"||p.Key=="online-team-header"||p.Key=="online-request-lives"||p.Key=="online-saved-close").ToDictionary(p=>p.Key,p=>Bounds(p.Value,canvas));ScrollTo(scroll,0);foreach(var p in fixedNodes)Check(Vector2.Distance(Bounds(page.VerificationNodes[p.Key],canvas).position,p.Value.position)<.1f,"History scrolling never moves fixed header/action/dock "+p.Key);ScrollTo(scroll,1);}
  }
  static void GlyphBounds(OnlineTeamsPage82 page,HomeElement element,RectTransform node,Text text,Mesh mesh){
   Rect box=text.rectTransform.rect;var vertices=mesh.vertices;bool ordinary=vertices.All(v=>v.x>=box.xMin-1&&v.x<=box.xMax+1&&v.y>=box.yMin-1&&v.y<=box.yMax+1);
   float bearing=0;foreach(var line in text.cachedTextGenerator.lines){int index=line.startCharIdx;while(index<text.text.Length&&char.IsWhiteSpace(text.text[index]))index++;if(index<text.text.Length&&text.font.GetCharacterInfo(text.text[index],out var metric,text.fontSize,text.fontStyle))bearing=Math.Min(bearing,metric.minX);}
   // A measured negative first-glyph bearing is typography, not clipping.
   // Permit it only inside the actual painted parent or padded content area;
   // vertical/right bounds and every control/safe/overlap test remain intact.
   bool measured=vertices.All(v=>v.x>=box.xMin+bearing-.25f&&v.x<=box.xMax+1&&v.y>=box.yMin-1&&v.y<=box.yMax+1);RectTransform parent=null;float padding=0;
   const string lifePrefix="online-life-";string art=element.id.EndsWith("-label",StringComparison.Ordinal)?element.id.Substring(0,element.id.Length-6)+"-art":element.id.StartsWith(lifePrefix,StringComparison.Ordinal)&&element.id.Length>lifePrefix.Length+32?element.id.Substring(0,lifePrefix.Length+32)+"-base":null;
   if(art!=null&&page.VerificationNodes.TryGetValue(art,out parent))padding=4;
   else if(element.id=="online-chat-welcome"){parent=Field<RectTransform>(page,"content");padding=8;}
   bool painted=false;if(parent){var p=vertices.Select(v=>parent.InverseTransformPoint(node.TransformPoint(v))).ToArray();Rect inner=parent.rect;inner.xMin+=padding;inner.xMax-=padding;inner.yMin+=padding;inner.yMax-=padding;painted=p.All(v=>v.x>=inner.xMin-.25f&&v.x<=inner.xMax+.25f&&v.y>=inner.yMin-.25f&&v.y<=inner.yMax+.25f);}
   Check(ordinary||bearing<0&&measured&&painted,"Actual chat glyph vertices remain contained "+element.id+" rect="+box+" mesh="+vertices.Min(v=>v.x)+","+vertices.Min(v=>v.y)+".."+vertices.Max(v=>v.x)+","+vertices.Max(v=>v.y)+" actualFirstGlyphBearing="+bearing+" paintedParent="+painted+" font="+text.fontSize+" lines="+text.cachedTextGenerator.lineCount);
  }
  public static void Run()=>RunCore(false);
  public static void RunImport()=>RunCore(true);
  public static void RunDiagnostics()=>RunCore(false,true);
  static void RunCore(bool importOnly,bool diagnostics=false){
   output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW110_OUT")??"../Verification/Evidence/Review110");Directory.CreateDirectory(Path.Combine(output,"Native","TeamsChatHelp110"));report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};int locale=GameLocale.Current;bool hadLanguage=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int savedLanguage=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);string profiles=null,server=null,settings=null;Application.logMessageReceived+=Log;
   try{profiles=Digest(Path.Combine(Application.persistentDataPath,"Profiles"));server=Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));settings=Digest("ProjectSettings");Check(Application.unityVersion=="2022.3.62f3","Main engine remains pinned2022");EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);assets=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(assets,"Actual existing Teams asset loads");ImportRoles();if(diagnostics){report.scope="Actual Unity Editor bounded four synthetic-UGUI failure diagnostics only; no functional/HTTP/device acceptance.";Layouts(true);}else if(!importOnly){Protocol();RegionControls();ComponentActions();OfflineShortCircuit();ColdDirectoryOrder();WarmEntryAndNavigation();StatusPlacement();PendingViewCache();PresentationOwnerRead();DurableOwnerGuard();NavigationDiagnostics();ReadWatchdog();DiscardRecovery();Animations();Layouts();}Check(report.actualHttpRequests==0,"Scripted/native visual suite constructs no HTTP/DNS request");}
   catch(Exception error){report.errors.Add(error.ToString());}
   finally{GameLocale.Select(locale);try{report.ordinaryProfilesPreserved=profiles==Digest(Path.Combine(Application.persistentDataPath,"Profiles"));Check(report.ordinaryProfilesPreserved,"Ordinary profiles stay byte-identical");report.serverReviewPreserved=server==Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));Check(report.serverReviewPreserved,"Ordinary managed records stay byte-identical");report.settingsPreserved=settings==Digest("ProjectSettings");Check(report.settingsPreserved,"Project settings stay byte-identical");report.languagePreferencePreserved=PlayerPrefs.HasKey(GameLocale.PreferenceKey)==hadLanguage&&PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue)==savedLanguage;Check(report.languagePreferencePreserved,"Saved language key presence/value unchanged");}catch(Exception error){report.errors.Add(error.ToString());}Application.logMessageReceived-=Log;report.status=(report.errors.Count==0?"PASS_NATIVE_TEAMS_CHAT_HELP":"FAIL_NATIVE_TEAMS_CHAT_HELP")+(importOnly?"_IMPORT110":diagnostics?"_DIAGNOSTICS110":"110");File.WriteAllText(Path.Combine(output,"Native",importOnly?"TeamsChatHelp110_Import.json":diagnostics?"TeamsChatHelp110_Diagnostics.json":"TeamsChatHelp110.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));}EditorApplication.Exit(report.errors.Count==0?0:1);
  }
  static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}

 }
}
#endif
