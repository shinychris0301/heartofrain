#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Leaderboard;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineSocial;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
 public static class LeaderboardParity118Verification {
  [Serializable] sealed class Report {public string status="RUNNING",unity,scope;public int checks;public List<string> errors=new List<string>(),captures=new List<string>();}
  static Report report;static string output;
  static void Check(bool okay,string label){report.checks++;if(!okay)throw new InvalidOperationException(label);}
  static string Id(int i)=>i.ToString("x32");
  static SocialRank82 Player(int n,string name,int score,long rank)=>new SocialRank82{playerId=Id(n),displayName=name,score=score,rank=rank};
  static SocialTeamRankRefresh115 Team(int n,string name,int score,long rank)=>new SocialTeamRankRefresh115{teamId=Id(n),name=name,badgeId=n==1?"drop":n==2?"lantern":n==3?"well":n==4?"sun":"wave",score=score,rank=rank,memberCount=n==4?28:n==5?39:1};
  static OnlinePlayersView82 View(){return new OnlinePlayersView82{tab=0,connected=true,selfId=Id(12),ownProfileLoaded=true,ownOptIn=true,ranks115=new SocialRankRefresh115{scope="global",entries=new[]{Player(1,"Aurora",50,1),Player(2,"Old Oak",49,2),Player(3,"Riverlight",47,3),Player(4,"Mira",43,4),Player(5,"Northstar",41,5)},nextOffset=5,hasSelfEntry=true,selfEntry=Player(12,"You",1,12)},teamRanks115=new SocialTeamRanksRefresh115{scope="global",hasTeam=true,entries=new[]{Team(1,"Rainkeepers",24800,1),Team(2,"Lantern Guild",23400,2),Team(3,"Well Guardians",22150,3),Team(4,"Golden Dawn",19700,4),Team(5,"Silver Wells",18450,5)},nextOffset=5,hasSelfEntry=true,selfEntry=Team(1,"Rainkeepers",24800,1)}};}
  static HomeElement One(HomeFrame f,string id)=>f.elements.Single(e=>e.id==id);
  static IEnumerable<HomeElement> All(OnlineTeamsFrame82 f)=>f.chrome.elements.Concat(f.content.elements).Concat(f.overlay.elements);
  static int SourceSide(string path){
   byte[] header=new byte[24];using(var file=File.OpenRead(path))Check(file.Read(header,0,header.Length)==header.Length,"PNG header readable "+path);
   Check(header[0]==137&&header[1]==80&&header[2]==78&&header[3]==71,"PNG signature "+path);
   int width=(header[16]<<24)|(header[17]<<16)|(header[18]<<8)|header[19];
   int height=(header[20]<<24)|(header[21]<<16)|(header[22]<<8)|header[23];
   return Math.Max(width,height);
  }
  static void ImportBinding(LeaderboardAssets art,string id,string guid,bool sliced){
   var sprite=art.Find(id);Check(sprite!=null,"R3 asset resolves "+id);
   string path=AssetDatabase.GetAssetPath(sprite);Check(!string.IsNullOrEmpty(path)&&AssetDatabase.AssetPathToGUID(path)==guid,"R3 source GUID "+id);
   var importer=AssetImporter.GetAtPath(path) as TextureImporter;Check(importer!=null&&importer.textureType==TextureImporterType.Sprite,"R3 Sprite importer "+id);
   Check(importer.spriteImportMode==SpriteImportMode.Single&&importer.filterMode==FilterMode.Bilinear,"R3 single bilinear sprite "+id);
   Check(!importer.mipmapEnabled,"R3 UI source has no mipmaps "+id);
   var border=sprite.border;Check(sliced?border.x>0&&border.y>0&&border.z>0&&border.w>0:border==Vector4.zero,"R3 border role "+id);
   int source=SourceSide(path);var android=importer.GetPlatformTextureSettings("Android");
   Check(importer.maxTextureSize>=source,"R3 default import keeps source pixels "+id);
   Check(android.maxTextureSize>=source,"R3 Android import keeps source pixels "+id);
  }
  static void Imports(LeaderboardAssets art){
   ImportBinding(art,"TA_Panel_Cream","a724adc1ea22513b989c2fb2bc47dcff",true);
   ImportBinding(art,"TA_Panel_Blue","37115ad250e55f9bb468f3d7c877c590",true);
   ImportBinding(art,"TA_Tab_Track","68897fac3fb05f0fa254f4818fb71525",true);
   ImportBinding(art,"TA_Tab_Selected","bcaf1bee4c2354ee94007122c20c6724",true);
   ImportBinding(art,"TA_Button_Blue","6ee27d40ee7b5f55b56e4c348299382d",true);
   ImportBinding(art,"TA_Button_Green","be3faa8ee94157e88353cf034fcd3bbe",true);
   ImportBinding(art,"TA_Button_Disabled","d5e91c499e105fe1955476b7b990f46e",true);
   ImportBinding(art,"TA_Field","e4252a5439b850f2846bd370656bf7b2",true);
   ImportBinding(art,"TA_Stat","1e3db83303fa5e99a8218f170edaf339",true);
   ImportBinding(art,"TA_Panel_Inner","d0d0476756095bc0a67b4c38199c1ee4",true);
   ImportBinding(art,"Portrait_Weaver_R2","8fe6eb19da015963a876cbfe24481399",false);
   ImportBinding(art,"Portrait_Scholar_R2","757119ee8ad05696930f9d8235d858cc",false);
   ImportBinding(art,"Portrait_Ivan_R2","cc4d8b06e33b56e69b6ae5a90b0c126d",false);
  }
  static void RenderBindings(OnlineSocialSurface82 surface,OnlineTeamsFrame82 frame,LeaderboardAssets art){
   foreach(var e in All(frame)){
    if(e.kind!="sprite"&&e.kind!="mask")continue;
    RectTransform node;if(!surface.nodes.TryGetValue(e.id,out node))continue;
    var image=node.GetComponent<Image>();
    if(e.sliced&&e.asset!=null&&(e.asset.StartsWith("TA_Panel_",StringComparison.Ordinal)||e.asset.StartsWith("TA_Button_",StringComparison.Ordinal)||e.asset.StartsWith("TA_Tab_",StringComparison.Ordinal)||e.asset=="TA_Field"||e.asset=="TA_Stat"))
     Check(image!=null&&image.sprite==art.Find(e.asset)&&image.type==Image.Type.Sliced,"R3 sliced UI binding "+e.id);
    if(e.id.EndsWith("-portrait",StringComparison.Ordinal))
     Check(image!=null&&image.sprite==art.Find(e.asset)&&image.type==Image.Type.Simple&&image.preserveAspect,"R3 portrait Simple/preserveAspect "+e.id);
   }
  }
  static void Contained(OnlineTeamsFrame82 f,int width,int height){
   float dock=MainNavigationLayout.ReservedHeight(f.width,f.height);
   Check(f.width<=width+.1f&&f.height<=height+.1f,"safe-area frame contained");
   Check(f.viewportY>=0&&f.viewportHeight>0&&f.viewportY+f.viewportHeight<=f.height-dock+.1f,"ranking viewport above dock");
   foreach(var e in f.chrome.elements.Where(e=>e.kind=="group")){Check(e.x>=-.1f&&e.y>=-.1f&&e.x+e.width<=f.width+.1f&&e.y+e.height<=f.height+.1f,"fixed hit bounds "+e.id);if(!e.id.StartsWith("nav-",StringComparison.Ordinal))Check(e.width>=48&&e.height>=48,"fixed touch target "+e.id);}
  }
  static void Ranks(LeaderboardAssets art,int width,int height){
   var view=View();view.ranks115.entries=new[]{Player(1,"Aurora",50,1),Player(2,"Old Oak",49,2),Player(3,"Riverlight",47,3),Player(4,"Mira",43,4),Player(5,"Northstar",41,5)};
   view.editorVisualFixture118=true;var f=LeaderboardR3Layout118.Build(width,height,view);Contained(f,width,height);
   Check(All(f).Any(e=>e.action=="scope-global"),"World scope always available");
   Check(!All(f).Any(e=>e.action=="scope-regional"),"My region hidden without previously saved region");
   Check(!All(f).Any(e=>e.action!=null&&e.action.IndexOf("country",StringComparison.OrdinalIgnoreCase)>=0),"no country selection control");
   var list=f.content;
   string[] medal={"TA_Rank_Gold","TA_Rank_Silver","TA_Rank_Bronze"};string[] portraits={"Portrait_Weaver_R2","Portrait_Scholar_R2","Portrait_Ivan_R2"};
   for(int i=1;i<=3;i++){string id="online-rank-"+Id(i);Check(One(list,id+"-medal").asset==medal[i-1],"rank-to-medal assignment "+i);Check(One(list,id+"-avatar-portrait").asset==portraits[i-1],"Editor-only R3 portrait "+i);Check(art.Find(medal[i-1])&&art.Find(portraits[i-1]),"bound R3 art resolves "+i);}
   var levelLabel=One(list,"online-rank-"+Id(1)+"-score-label");Check(levelLabel.text.Length>0&&levelLabel.y+levelLabel.height<=One(list,"online-rank-"+Id(1)+"-score-icon").y,"podium level label does not collide with score");
   var gold=One(list,"online-rank-"+Id(1)+"-base");var silver=One(list,"online-rank-"+Id(2)+"-base");var bronze=One(list,"online-rank-"+Id(3)+"-base");
   Check(gold.x>silver.x&&gold.x<bronze.x&&gold.y<silver.y,"R3 centered first, side second and third");
   foreach(int n in new[]{4,5}){var row=One(list,"online-rank-"+Id(n)+"-base");Check(row.y+row.height<=f.viewportHeight+.5f,"ranks 4/5 fully visible at "+width+"x"+height);}
   Check(One(f.chrome,"online-pin-rank").text=="12"&&One(f.chrome,"online-pin-score").text=="1","server self rank and score pinned");
   view.editorVisualFixture118=false;f=LeaderboardR3Layout118.Build(width,height,view);
   Check(!f.content.elements.Any(e=>e.id.EndsWith("-avatar-portrait",StringComparison.Ordinal)),"review portraits absent without explicit Editor gate");
   view.ranks115.entries=new[]{Player(1,"One",50,1),Player(2,"Tie",50,1),Player(3,"Tie 2",50,1),Player(4,"Next",49,4)};view.ranks115.nextOffset=4;
   f=LeaderboardR3Layout118.Build(width,height,view);for(int i=1;i<=3;i++)Check(One(f.content,"online-rank-"+Id(i)+"-medal").asset=="TA_Rank_Gold","authoritative shared tie retains gold "+i);
   Check(One(f.content,"online-rank-"+Id(4)+"-rank").text=="4","rank four not renumbered after tie");
   view.ranks115=null;view.status=OnlinePlayersText82.T("Unavailable");f=LeaderboardR3Layout118.Build(width,height,view);
   Check(view.status!=OnlineTeamsText82.T("Unavailable"),"leaderboard offline message is not a team error");
   Check(OnlinePlayersText82.Status(new SocialPageSession82.ViewStatus(SocialViewState82.Loading,"",false))=="","cached navigation hides transient loading text");
   Check(!f.content.elements.Any(e=>e.id.StartsWith("online-rank-",StringComparison.Ordinal)),"offline path has no synthetic roster");
   Check(f.chrome.elements.Any(e=>e.action=="retry"),"offline path offers retry");
   view=View();view.tab=1;view.friends=null;view.status=OnlinePlayersText82.T("Unavailable");f=LeaderboardR3Layout118.Build(width,height,view);
   Check(One(f.content,"online-friends-unavailable118").text=="","Friends offline error appears only in the footer");
   Check(One(f.chrome,"online-players-status").text==view.status,"Friends footer retains the actionable error");
   view.busy=true;view.status="";f=LeaderboardR3Layout118.Build(width,height,view);
   Check(One(f.content,"online-friends-unavailable118").text=="","Friends transient fetch has no Loading text");
   view=View();view.teamRanking=true;f=LeaderboardR3Layout118.Build(width,height,view);
   Check(One(f.content,"online-team-rank-"+Id(1)+"-badge").asset=="TA_Badge_drop","team crest uses authenticated badge ID");
   Check(One(f.content,"online-team-rank-"+Id(1)+"-star").asset=="TA_Stat_star","team metric uses painted star");
   Check(One(f.content,"online-team-rank-"+Id(1)+"-score-label").text.Length>0,"team podium score label present");
   Check(One(f.content,"online-team-rank-"+Id(4)+"-member-icon").asset=="TA_Icon_People","team row shows verified member-count icon");
   Check(One(f.content,"online-team-rank-"+Id(2)+"-medal").asset=="TA_Rank_Silver","team rank 2 silver");
   view=View();view.regionCode="RU";view.regional=true;f=LeaderboardR3Layout118.Build(width,height,view);
   Check(All(f).Any(e=>e.action=="scope-regional"),"saved region selectable");
   Check(!All(f).Any(e=>e.action!=null&&e.action.IndexOf("country",StringComparison.OrdinalIgnoreCase)>=0),"saved-region view has no country selector");
   Check(!f.content.elements.Any(e=>e.id.StartsWith("online-rank-",StringComparison.Ordinal)),"global cache not displayed as regional data");
   view=View();f=LeaderboardR3Layout118.Build(360,612,view,28);Contained(f,360,612);
   Check(One(f.chrome,"online-players-title").y==0&&One(f.chrome,"online-tabs").y==46&&One(f.chrome,"online-scopes").y==91,"measured Android inset compacts header within safe area");
   foreach(int n in new[]{4,5}){var row=One(f.content,"online-rank-"+Id(n)+"-base");Check(row.y+row.height<=f.viewportHeight+.5f,"short safe-area viewport shows row "+n);}
   view=View();view.tab=1;f=LeaderboardR3Layout118.Build(360,612,view,28);Contained(f,360,612);Check(f.viewportY==95,"Friends list uses the same measured safe-area compaction");
  }
  static void Fallback(LeaderboardAssets art){
   var go=new GameObject("Leaderboard118 offline route");try{var page=go.AddComponent<LeaderboardPage>();page.enabled=false;page.assets=art;page.editorOnlyReviewFixture=false;
    var use=typeof(LeaderboardPage).GetMethod("UseOnline",BindingFlags.NonPublic|BindingFlags.Instance);
    Check(use!=null&&(bool)use.Invoke(page,null),"unconfigured service routes to honest online/offline surface");
    Check(page.ReviewSession==null,"demo snapshot never constructed by offline route");
    var offline=go.GetComponent<OnlinePlayersPage82>();Check(offline!=null,"offline component exists without backend credentials");
    offline.VerificationViewport(360,640);page.Show();Check(offline.IsVisible,"offline page opens without a service");
    offline.Request("primary-friends115");Check(offline.VerificationFrame.content.elements.Any(e=>e.id=="online-friends-summary118"),"offline Friends tab responds without a request or fake roster");
    offline.Request("friends-open-search118");Check(offline.VerificationFrame.chrome.elements.Any(e=>e.action=="search-back115"),"offline Find exposes fixed Friends return action");
    offline.Request("search-back115");Check(offline.VerificationFrame.content.elements.Any(e=>e.id=="online-friends-summary118")&&!offline.VerificationFrame.content.elements.Any(e=>e.id=="online-player-code-input"),"offline search return restores Friends list without a service");
    offline.Request("primary-teams115");Check(offline.VerificationFrame.chrome.elements.Any(e=>e.id=="online-primary-teams-selected")&&!offline.VerificationFrame.content.elements.Any(e=>e.id.StartsWith("online-team-rank-",StringComparison.Ordinal)),"offline Teams tab responds without synthetic ranks");
    offline.Request("primary-players115");Check(offline.VerificationFrame.chrome.elements.Any(e=>e.id=="online-primary-players-selected")&&!offline.VerificationFrame.content.elements.Any(e=>e.id.StartsWith("online-rank-",StringComparison.Ordinal)),"offline Players tab responds without synthetic ranks");
   }finally{UnityEngine.Object.DestroyImmediate(go);}
  }
  static void FriendSubtitle(){
   var profile=new SocialProfile82{playerId=Id(21),displayName="Review QA",completedLevels=34,leaderboardOptIn=true};
   var v=View();v.tab=1;v.friends=new SocialFriends82{friends=new[]{profile}};
   var frame=LeaderboardR3Layout118.Build(360,640,v);string id="online-friend-"+profile.playerId;
   Check(One(frame.content,id+"-cleared").text=="\u0423\u0440\u043e\u0432\u0435\u043d\u044c"&&One(frame.content,id+"-level").text=="34","Production friend row labels the verified level once");
   Check(!frame.content.elements.Any(e=>e.id==id+"-team"),"Production friend row does not invent peer team membership");
   v.searchOpen115=true;v.searchReady115=true;v.searchQuery115="QA";v.searchCursor115="";
   v.searchResults115=new SocialPlayerSearch115{players=new[]{profile},relationships=new[]{new SocialRelationship82{playerId=profile.playerId,state="None"}},requestQuery="QA",requestCursor=""};
   id="online-search-result115-"+profile.playerId;
   foreach(var size in new[]{new Vector2Int(360,640),new Vector2Int(390,844)}){
    frame=LeaderboardR3Layout118.Build(size.x,size.y,v);
    Check(One(frame.content,id+"-cleared").text=="\u0423\u0440\u043e\u0432\u0435\u043d\u044c"&&One(frame.content,id+"-level").text=="34","Production Find row labels the verified level once "+size);
    Check(!frame.content.elements.Any(e=>e.id==id+"-team"),"Production Find row does not invent peer team membership "+size);
    var heading=One(frame.content,"online-find-heading118");var first=One(frame.content,id+"-base");var back=One(frame.chrome,"online-primary-friends");
    Check(first.y>=heading.y+heading.height&&back.action=="search-back115"&&back.y+back.height<=frame.viewportY,"Fixed Friends tab returns from search and first result clears heading "+size);
    Check(!frame.content.elements.Any(e=>e.id.StartsWith("online-search-back115",StringComparison.Ordinal))&&!frame.chrome.elements.Any(e=>e.id=="online-friends-secondary118"),"R3 Find has no overlapping close disc or overflow "+size);
    v.searchResults115.relationships[0].state="Outgoing";frame=LeaderboardR3Layout118.Build(size.x,size.y,v);
    Check(One(frame.content,id+"-state-base").asset=="TA_Button_Disabled"&&One(frame.content,id+"-state").color=="#FFFFFF"&&!frame.content.elements.Any(e=>e.action=="search-add115:"+profile.playerId),"Sent status remains disabled with high-contrast text "+size);
    v.searchResults115.relationships[0].state="None";
   }
   v=View();v.tab=1;v.editorVisualFixture118=true;frame=LeaderboardR3Layout118.Build(360,640,v);
   Check(frame.content.elements.Any(e=>e.id.EndsWith("-team",StringComparison.Ordinal)&&e.text=="Rainkeepers"),"Editor-only fixture retains the R3 team subtitle");
  }
  static void Capture(OnlineSocialSurface82 surface,int width,int height,string name){
   var camObject=new GameObject("Leaderboard R3 Editor capture camera");var camera=camObject.AddComponent<Camera>();camera.enabled=false;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;camera.orthographic=true;camera.orthographicSize=height/2f;camera.aspect=width/(float)height;camera.nearClipPlane=.1f;camera.farClipPlane=100;
   var target=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32);var previous=RenderTexture.active;Texture2D png=null;
   try{target.Create();camera.targetTexture=target;surface.canvas.renderMode=RenderMode.WorldSpace;var scaler=surface.canvas.GetComponent<CanvasScaler>();scaler.enabled=false;var root=(RectTransform)surface.canvas.transform;root.anchorMin=root.anchorMax=root.pivot=Vector2.one*.5f;root.localPosition=Vector3.zero;root.localScale=Vector3.one;root.sizeDelta=new Vector2(width,height);camera.transform.position=surface.canvas.transform.position-new Vector3(0,0,10);surface.canvas.worldCamera=camera;Canvas.ForceUpdateCanvases();PageBackdrop90.Fill(surface.nodes["online-players-background"].GetComponent<MaskableGraphic>(),surface.canvas);Canvas.ForceUpdateCanvases();camera.Render();camera.Render();RenderTexture.active=target;png=new Texture2D(width,height,TextureFormat.RGB24,false);png.ReadPixels(new Rect(0,0,width,height),0,0);png.Apply();File.WriteAllBytes(Path.Combine(output,name+".png"),png.EncodeToPNG());report.captures.Add(name+".png");Check(png.GetPixels32().Count(p=>p.r+p.g+p.b>40)>width*height/3,"Editor capture painted "+name);}
   finally{surface.canvas.renderMode=RenderMode.ScreenSpaceOverlay;surface.canvas.GetComponent<CanvasScaler>().enabled=true;surface.canvas.worldCamera=null;camera.targetTexture=null;RenderTexture.active=previous;if(png)UnityEngine.Object.DestroyImmediate(png);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(camObject);}
  }
  static void Paint(OnlineSocialSurface82 surface,int width,int height,OnlinePlayersView82 view,string name){
   var frame=LeaderboardR3Layout118.Build(width,height,view);
   var sliceIds=frame.chrome.elements.Concat(frame.content.elements).Where(e=>e.sliced&&e.asset!=null&&e.asset.StartsWith("TA_",StringComparison.Ordinal)).Select(e=>e.id).Distinct().ToArray();
   Check(sliceIds.Length>=3,"R3 page has sliced panels/tabs to compare");
   surface.Apply(frame.width,frame.height,1,new Rect(0,0,width,height),height,frame.viewportY,frame.viewportHeight,frame.chrome,frame.content,frame.overlay,false,true,false,1,1,frame.r3SliceScale118);
   var proofPpu=sliceIds.ToDictionary(id=>id,id=>surface.nodes[id].GetComponent<Image>().pixelsPerUnitMultiplier);
   surface.Apply(frame.width,frame.height,1,new Rect(0,0,width,height),height,frame.viewportY,frame.viewportHeight,frame.chrome,frame.content,frame.overlay,false,true,false,1,frame.artScale,frame.r3SliceScale118);
   foreach(var id in sliceIds)Check(Mathf.Abs(surface.nodes[id].GetComponent<Image>().pixelsPerUnitMultiplier*frame.artScale-proofPpu[id])<.0005f,"R3 native slice follows authored proof scale "+id);
   RenderBindings(surface,frame,AssetDatabase.LoadAssetAtPath<LeaderboardAssets>("Assets/HeartOfTheRain/App/Leaderboard/LeaderboardAssets.asset"));Canvas.ForceUpdateCanvases();Capture(surface,width,height,name);
  }
  static void Captures(LeaderboardAssets art){
   var root=new GameObject("Leaderboard R3 Editor Game fixture");
   try{var surface=new OnlineSocialSurface82(root.transform,art.Find,art.journey.home.regularFont,art.journey.home.boldFont,_=>{},_=>"",(_,__)=>{});
    foreach(var size in new[]{new Vector2Int(360,640),new Vector2Int(390,844)}){
     var v=View();v.editorVisualFixture118=true;v.regionCode="RU";v.ranks115.entries=new[]{Player(1,"Aurora",50,1),Player(2,"Old Oak",49,2),Player(3,"Riverlight",47,3),Player(4,"Mira",43,4),Player(5,"Northstar",41,5)};
     string suffix=size.x+"x"+size.y;
     Paint(surface,size.x,size.y,v,"Players_World_"+suffix);
     v.regionCode="RU";v.regional=true;v.ranks115.scope="regional";v.ranks115.regionCode="RU";Paint(surface,size.x,size.y,v,"Players_Region_"+suffix);
     v=View();v.tab=1;v.editorVisualFixture118=true;Paint(surface,size.x,size.y,v,"Friends_"+suffix);
     v.searchOpen115=true;v.searchQuery115="Rain";Paint(surface,size.x,size.y,v,"Find_Friends_"+suffix);
     v=View();v.teamRanking=true;v.regionCode="RU";Paint(surface,size.x,size.y,v,"Teams_"+suffix);
    }
   }finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  public static void Run(){
   var root=Environment.GetEnvironmentVariable("HOTR_REVIEW118_OUT");if(string.IsNullOrEmpty(root))throw new InvalidOperationException("Set HOTR_REVIEW118_OUT to a separate verification folder.");
   output=Path.Combine(root,"Native","LeaderboardParity118");Directory.CreateDirectory(output);report=new Report{unity=Application.unityVersion,scope="Unity Editor offscreen UGUI Game captures and model/asset/binding checks; no Android parity or live service claim."};
   int saved=GameLocale.Current;bool had=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int pref=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);
   try{var art=AssetDatabase.LoadAssetAtPath<LeaderboardAssets>("Assets/HeartOfTheRain/App/Leaderboard/LeaderboardAssets.asset");Check(art&&art.journey&&art.demoData,"asset binder exists");Check(AssetDatabase.GetAssetPath(art.demoData)=="Assets/HeartOfTheRain/App/Leaderboard/Editor/LeaderboardDemo.json","sample roster is Editor-only");Check(!File.ReadAllText("Assets/HeartOfTheRain/App/Leaderboard/LeaderboardAssets.asset").Contains("demoData:"),"runtime asset has no serialized sample binding");Imports(art);GameLocale.Select(4);Fallback(art);FriendSubtitle();Ranks(art,360,640);Ranks(art,390,844);Captures(art);
    var medals=Resources.Load<LeaderboardMedals115>("HOTR_Leaderboard115/Medals");Check(medals&&medals.gold&&medals.silver&&medals.bronze,"three medal bindings exist");Check(medals.gold!=medals.silver&&medals.gold!=medals.bronze&&medals.silver!=medals.bronze,"three medal sprites distinct");
   }catch(Exception e){report.errors.Add(e.ToString());}finally{GameLocale.Select(saved);if(had!=PlayerPrefs.HasKey(GameLocale.PreferenceKey)||pref!=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue))report.errors.Add("locale preference changed");report.status=report.errors.Count==0?"PASS_NATIVE_LEADERBOARD118":"FAIL_NATIVE_LEADERBOARD118";File.WriteAllText(Path.Combine(output,"LeaderboardParity118.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));}
   EditorApplication.Exit(report.errors.Count==0?0:1);
  }
 }
}
#endif

