#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Leaderboard;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Teams;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification
{
    public static partial class Regional89Verification
    {
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity;
            public string scope="Pinned native Unity Editor: country/demo filtering, actual UGUI components/fonts in explicit layout fixtures, selected offscreen camera-rendered PNGs and durable region request/response binding. No HTTP service, production rankings, Android/device touch or human visual approval claim.";
            public int checks,cases;public bool ordinaryCountryPreferencePreserved;public List<string> errors=new List<string>(),captures=new List<string>();
        }
        static Report report;static string output;
        static void Check(bool condition,string label){report.checks++;if(!condition)throw new InvalidOperationException(label);}
        public static void Run(){
            string path=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REGION89_OUTPUT")??"../Verification/Evidence/Regional89/Native");Directory.CreateDirectory(path);
            output=path;report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};int language=GameLocale.Current;
            bool existed=PlayerPrefs.HasKey(CountryRegion89.PreferenceKey);string preference=PlayerPrefs.GetString(CountryRegion89.PreferenceKey,"");GameObject root=null;
            try {
                Check(Application.unityVersion=="2022.3.62f3","Pinned engine");
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                var assets=AssetDatabase.LoadAssetAtPath<LeaderboardAssets>("Assets/HeartOfTheRain/App/Leaderboard/LeaderboardAssets.asset");
                var teamAssets=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(assets&&teamAssets,"Approved artwork bound");
                foreach(string value in new[]{"RU","US","GB","DE","FR","ES","CA","AU","NZ","ZA","KZ","BR","AX","BQ","SS"})Check(CountryRegion89.Normalize(value)==value,"Known country "+value);
                Check(CountryRegion89.Normalize(" ru ")=="RU","Country preference normalized explicitly");
                foreach(string value in new[]{"XX","USA","РФ","","en","10","UTC+10","R\nU"})Check(CountryRegion89.Normalize(value)=="","Invalid country "+value);
                GameLocale.Select(4);Check(CountryRegion89.Countries("Россия").SequenceEqual(new[]{"RU"}),"Country searchable by localized human name");Check(CountryRegion89.Countries("Russia").Contains("RU"),"Country searchable by English name");Check(CountryRegion89.Countries("RU").First()=="RU","Country code is optional search fallback");Check(CountryRegion89.Countries().First()=="RU"&&CountryRegion89.CountryName("RU")=="Россия","Friendly Russian option present without automatic selection");
                var demo=new LeaderboardSession(JsonUtility.FromJson<LeaderboardSnapshot>(assets.demoData.text));string original=assets.demoData.text;
                demo.SetRegion("");demo.SetLocal(true);Check(!demo.Local&&demo.Players().Length==demo.Data.players.Length&&demo.Teams().Length==demo.Data.teams.Length,"Missing country cannot enable local scope or infer a default");
                demo.SetLocal(false);Check(demo.Players().Length==demo.Data.players.Length&&demo.Teams().Length==demo.Data.teams.Length,"Global remains available without a country");
                demo.SetRegion("RU");demo.SetLocal(true);Check(demo.Players().All(v=>v.region=="RU")&&demo.Players().Single().isSelf,"Demo self follows explicitly chosen region");Check(demo.Teams().Length==0,"No fabricated Russian sample teams");
                demo.SetRegion("GB");Check(demo.Teams().All(v=>v.region=="GB")&&demo.Teams().Length>0,"Demo teams filtered by country");Check(assets.demoData.text==original,"Approved sample JSON unchanged");
                Transport();ControlledRecovery(assets,teamAssets);
                root=new GameObject("Explicit Regional89 UGUI layout fixture");
                var surface=new OnlineSocialSurface82(root.transform,assets.Find,assets.journey.home.regularFont,assets.journey.home.boldFont,_=>{},_=>"RU",(_,__)=>{});
                foreach(int locale in Enumerable.Range(0,5))foreach(var size in new[]{new Vector2Int(320,568),new Vector2Int(420,900),new Vector2Int(768,1024),new Vector2Int(900,1600)})foreach(int state in Enumerable.Range(0,4)){
                    GameLocale.Select(locale);bool regional=(state&1)!=0,pending=state==3;string region=state==1?"":"RU";
                    var players=new OnlinePlayersView82{connected=true,ownProfileLoaded=true,ownOptIn=true,regional=regional,teamRanking=state==2,pending=pending,regionCode=region,selfId=new string('1',32),ranks=new SocialLeaderboard82{scope=regional?"regional":"global",regionCode=region,entries=new SocialRank82[0]},teamRanks=Ranks(region,regional)};
                    Inspect(OnlinePlayersLayout82.Build(size.x,size.y,players),surface,size,"players",pending);
                    if(locale==4&&state==0&&(size.x==420||size.x==768))Capture(surface,size,"Players_Global_Russian_"+size.x);
                    players.modal="country";Inspect(OnlinePlayersLayout82.Build(size.x,size.y,players),surface,size,"country",pending);
                    if(state==0&&((locale==4&&(size.x==320||size.x==420||size.x==768))||(locale==0&&size.x==420)))Capture(surface,size,"Country_"+GameLocale.Codes[locale]+"_"+size.x);
                    var teams=new OnlineTeamsView82{connected=true,tab=2,pending=pending,regional=regional,regionCode=region,ranks=Ranks(region,regional)};
                    Inspect(OnlineTeamsLayout82.Build(size.x,size.y,teams),surface,size,"teams",pending);
                    if(locale==4&&state==0&&(size.x==420||size.x==768))Capture(surface,size,"Teams_Global_Russian_"+size.x);
                    var fixtureTeams=new TeamsSession(JsonUtility.FromJson<TeamsSnapshot>(teamAssets.demoData.text)){Rankings=demo};fixtureTeams.Select(TeamsTab.Rankings);demo.SetRegion(region);demo.SetLocal(regional);
                    var frame=TeamsLayout.Build(size.x,size.y,fixtureTeams);
                    Check(!regional||region!="RU"||!frame.content.elements.Any(v=>demo.Data.teams.Any(team=>v.id=="team-"+team.id)),"Demo RU does not reuse foreign team rows");
                    demo.Select(LeaderboardTab.Teams);var lf=LeaderboardLayout.Build(size.x,size.y,demo);Check(lf.chrome.elements.Any(v=>v.action=="world")&&!lf.chrome.elements.Any(v=>v.action=="choose-country")&&(lf.chrome.elements.Any(v=>v.action=="local")==(region.Length>0)),"Demo Leaderboard has World, no country picker, and regional only for an already-selected region");
                    report.cases++;
                }
                // An old region response cannot be painted under a new label.
                var stale=new OnlinePlayersView82{connected=true,tab=0,teamRanking=true,regional=true,regionCode="RU",teamRanks=Ranks("US",true)};var sf=OnlinePlayersLayout82.Build(420,900,stale);
                Check(!sf.content.elements.Any(v=>v.id.StartsWith("online-team-rank-",StringComparison.Ordinal)),"Mismatched country team cache hidden");
                stale.teamRanking=false;stale.ranks=new SocialLeaderboard82{scope="regional",regionCode="US",entries=new[]{new SocialRank82{playerId=new string('2',32),displayName="Wrong region",score=50,rank=1}}};sf=OnlinePlayersLayout82.Build(420,900,stale);
                Check(!sf.content.elements.Any(v=>v.id.StartsWith("online-rank-",StringComparison.Ordinal)),"Mismatched country player cache hidden");
                report.ordinaryCountryPreferencePreserved=PlayerPrefs.HasKey(CountryRegion89.PreferenceKey)==existed&&PlayerPrefs.GetString(CountryRegion89.PreferenceKey,"")==preference;
                Check(report.ordinaryCountryPreferencePreserved,"No country preference changed by fixtures");report.status="PASS_NATIVE_REGIONAL89";
            }catch(Exception error){report.status="FAIL_NATIVE_REGIONAL89";report.errors.Add(error.ToString());}
            finally {if(root)UnityEngine.Object.DestroyImmediate(root);GameLocale.Select(language);File.WriteAllText(Path.Combine(path,"Report.json"),JsonUtility.ToJson(report,true));}
            EditorApplication.Exit(report.status=="PASS_NATIVE_REGIONAL89"?0:1);
        }
        static SocialTeamLeaderboard89 Ranks(string country,bool local)=>new SocialTeamLeaderboard89{scope=local?"regional":"global",regionCode=local?country:"",entries=new[]{new SocialTeamRank89{teamId=new string('3',32),name="Verified team",score=30,memberCount=2,rank=1}}};
        static void Inspect(OnlineTeamsFrame82 frame,OnlineSocialSurface82 surface,Vector2Int size,string scope,bool pending){
            float dock=MainNavigationLayout.ReservedHeight(size.x,size.y),status=pending?108:0;
            Check(frame.viewportY+frame.viewportHeight<=size.y-dock-status+.1f,"Viewport contains ranking content: "+scope+" "+size);
            surface.Apply(frame.width,frame.height,1,new Rect(0,0,size.x,size.y),size.y,frame.viewportY,frame.viewportHeight,frame.chrome,frame.content,frame.overlay,scope=="country",true);
            foreach(var element in frame.chrome.elements.Where(v=>v.id.Contains("region-")||v.id.StartsWith("online-rank-",StringComparison.Ordinal)||v.id=="online-ranking-consent")){
                Check(element.x>=0&&element.y>=0&&element.x+element.width<=size.x+.1f&&element.y+element.height<=frame.viewportY+.1f,"Country/rank control contained "+element.id);
            }
            if(scope=="country"){
                Check(surface.nodes["country-code-input"].GetComponent<InputField>().characterLimit==80,"Country-name search is bounded");
                Check(surface.nodes["country-option-RU"].GetComponent<Button>().interactable,"Friendly Russia option selectable without typing a code");
                foreach(string id in new[]{"country-title","country-hint","country-cancel-label","country-search-label","country-previous-label","country-next-label","country-option-RU-label","country-option-US-label","country-option-GB-label","country-option-DE-label"}){
                    var text=surface.nodes[id].GetComponent<Text>();Check(text&&!text.supportRichText,"Country native text has no rich text "+id);
                    Check(text.preferredHeight<=text.rectTransform.rect.height+1,"Native country text fits "+id+" "+size+" locale "+GameLocale.Current);
                    Check(text.preferredWidth<=text.rectTransform.rect.width+1,"Native country text width fits "+id+" "+size+" locale "+GameLocale.Current);
                }
                var panel=NativeRect(surface.nodes["country-panel"]);
                string[] controls={"country-title","country-hint","country-code-input-art","country-search","country-option-RU","country-option-US","country-option-GB","country-option-DE","country-previous","country-next","country-cancel"};
                foreach(string id in controls){var rect=NativeRect(surface.nodes[id]);Check(rect.xMin>=panel.xMin+8&&rect.xMax<=panel.xMax-8&&rect.yMin>=panel.yMin+8&&rect.yMax<=panel.yMax-8,"Country modal native control stays inside panel "+id+" "+size);}
                for(int i=0;i<controls.Length;i++)for(int j=i+1;j<controls.Length;j++){
                    var first=NativeRect(surface.nodes[controls[i]]);var second=NativeRect(surface.nodes[controls[j]]);
                    bool intersects=Math.Min(first.xMax,second.xMax)-Math.Max(first.xMin,second.xMin)>.1f&&Math.Min(first.yMax,second.yMax)-Math.Max(first.yMin,second.yMin)>.1f;
                    Check(!intersects,"Country modal native controls do not overlap: "+controls[i]+" / "+controls[j]+" "+size+" locale "+GameLocale.Current);
                }
            }
        }
        static Rect NativeRect(RectTransform node)=>new Rect(node.anchoredPosition.x,-node.anchoredPosition.y,node.rect.width,node.rect.height);
        static void Capture(OnlineSocialSurface82 surface,Vector2Int size,string name){
            var go=new GameObject("Regional89 offscreen UI camera");var camera=go.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;camera.orthographic=true;camera.orthographicSize=size.y/2f;camera.aspect=size.x/(float)size.y;camera.nearClipPlane=.1f;camera.farClipPlane=100;camera.transform.position=surface.canvas.transform.position-new Vector3(0,0,10);
            var target=new RenderTexture(size.x,size.y,24,RenderTextureFormat.ARGB32);var previous=RenderTexture.active;Texture2D pixels=null;
            try{target.Create();camera.targetTexture=target;surface.canvas.renderMode=RenderMode.WorldSpace;surface.canvas.GetComponent<CanvasScaler>().enabled=false;var cr=(RectTransform)surface.canvas.transform;cr.anchorMin=cr.anchorMax=cr.pivot=Vector2.one*.5f;cr.localPosition=Vector3.zero;cr.localScale=Vector3.one;cr.sizeDelta=new Vector2(size.x,size.y);camera.transform.position=surface.canvas.transform.position-new Vector3(0,0,10);surface.canvas.worldCamera=camera;Canvas.ForceUpdateCanvases();if(surface.nodes.TryGetValue("online-players-background",out var bg))PageBackdrop90.Fill(bg.GetComponent<Image>(),surface.canvas);Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels=new Texture2D(size.x,size.y,TextureFormat.RGB24,false);pixels.ReadPixels(new Rect(0,0,size.x,size.y),0,0);pixels.Apply();Check(pixels.GetPixels32().Count(v=>v.r+v.g+v.b>40)>size.x*size.y/3,"Native UGUI capture contains painted artwork");string file=name+".png";File.WriteAllBytes(Path.Combine(output,file),pixels.EncodeToPNG());report.captures.Add(file);}
            finally{surface.canvas.renderMode=RenderMode.ScreenSpaceOverlay;surface.canvas.GetComponent<CanvasScaler>().enabled=true;surface.canvas.worldCamera=null;camera.targetTexture=null;RenderTexture.active=previous;if(pixels)UnityEngine.Object.DestroyImmediate(pixels);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(go);Canvas.ForceUpdateCanvases();}
        }
        static void Transport(){
            const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Static;var method=typeof(SocialBackendClient82).GetMethod("ValidateCommand",flags);var server=typeof(SocialBackendClient82).GetMethod("ServerOperation",flags);
            string id=new string('4',32);var command=new SocialPendingCommand82{commandId=id,operation="region.set",path="/v1/region",body="{\"commandId\":\""+id+"\",\"regionCode\":\"RU\"}"};
            Check(method.Invoke(null,new object[]{command})!=null&&((string)server.Invoke(null,new object[]{command}))=="social.region.set","Durable region command and recovery map to same operation");
            foreach(string body in new[]{"{\"commandId\":\""+id+"\",\"regionCode\":\"XX\"}","{\"commandId\":\""+id+"\",\"regionCode\":\"RU\",\"playerId\":\""+id+"\"}"}){
                command.body=body;bool rejected=false;try{method.Invoke(null,new object[]{command});}catch(TargetInvocationException){rejected=true;}Check(rejected,"Malformed/forged region durable command rejected");
            }
        }
    }
}
#endif
