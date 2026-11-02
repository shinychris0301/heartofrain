#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.Teams;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    public static class TeamsDiscovery103Verification {
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity;
            public string scope="Actual Unity Editor TeamsPage initialization/navigation and UGUI rendering; explicit unavailable and connected layout snapshots. No live social service, Android/device, real team creation or membership claim. Existing Social82 HTTP verification covers connected service mutations.";
            public int checks,layouts;public bool ordinaryProfilesPreserved,languagePreferencePreserved;
            public List<string> errors=new List<string>(),captures=new List<string>();
        }
        static Report report;static string output;
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        static T Field<T>(object owner,string name)=>(T)owner.GetType().GetField(name,Private).GetValue(owner);
        static void Set(object owner,string name,object value)=>owner.GetType().GetField(name,Private).SetValue(owner,value);
        static void Invoke(object owner,string name)=>owner.GetType().GetMethod(name,Private).Invoke(owner,null);
        static string ProfilesDigest(){
            string root=Path.Combine(Application.persistentDataPath,"Profiles");if(!Directory.Exists(root))return "Absent";
            using(var sha=SHA256.Create()){
                string rows=string.Join("\n",Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(v=>v,StringComparer.Ordinal).Select(file=>file.Substring(root.Length)+":"+BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(file)))));
                return "Present:"+Convert.ToBase64String(sha.ComputeHash(Encoding.UTF8.GetBytes(rows)));
            }
        }
        public static void Run(){
            output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW103_OUT")??"../Verification/Evidence/Review103");Directory.CreateDirectory(Path.Combine(output,"Native","TeamsDiscovery103"));
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};int locale=GameLocale.Current;
            bool hadLanguage=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int storedLanguage=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);
            string before=null;GameObject owner=null;Application.logMessageReceived+=Log;
            try {
                before=ProfilesDigest();Check(Application.unityVersion=="2022.3.62f3","Pinned editor engine");
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                owner=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));
                var home=owner.GetComponent<HomePage>();home.enabled=false;home.State.reduceMotion=true;
                // Bypass appearance persistence only, retaining the real Home and Teams initialization methods.
                var appearance=owner.AddComponent<ProfilePage>();appearance.enabled=false;Set(appearance,"home",home);
                var assets=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(assets&&assets.demoData,"Approved Teams artwork and explicit review fixture available");string demo=assets.demoData.text;
                var page=owner.AddComponent<TeamsPage>();page.enabled=false;page.home=home;page.assets=assets;Invoke(page,"Start");
                var online=owner.GetComponent<OnlineTeamsPage82>();Check(online&&page.ReviewSession==null,"Ordinary initialization selects honest online-unavailable renderer, without loading sample membership");
                online.enabled=false;Check(!page.IsVisible,"Teams stays closed until requested");
                home.NavigationRequested.Invoke("teams");Check(page.IsVisible&&online.IsVisible&&!home.PresentationVisible,"Actual Home Teams route opens unavailable page");
                Check(online.VerificationSession==null&&!online.VerificationPending,"No fabricated session or queued authorization in ordinary local mode");
                string localState=JsonUtility.ToJson(home.State);
                foreach(int language in Enumerable.Range(0,5))foreach(var size in new[]{new Vector2Int(320,568),new Vector2Int(420,900),new Vector2Int(768,1024)}){
                    GameLocale.Select(language);online.VerificationViewport(size.x,size.y);Canvas.ForceUpdateCanvases();
                    Unavailable(online);report.layouts++;
                    if(language==4&&(size.x==420||size.x==768))Capture(online,size,"Unavailable_ru_"+size.x+".png");
                }
                foreach(string action in new[]{"create","create-submit","join", "join:"+new string('a',32),"compose","send","leave","confirm","resume-pending","check-pending","retry"})page.Request(action);
                Check(page.ReviewSession==null&&online.VerificationSession==null&&!online.VerificationPending,"Unavailable requests cannot fabricate membership, network authorization or a pending write");
                Check(online.VerificationFrame.overlay.elements.Count==0,"Unavailable synthetic Create/Join cannot open a misleading writable modal");
                Check(JsonUtility.ToJson(home.State)==localState&&assets.demoData.text==demo,"Unavailable browsing and requests preserve local game state and sample JSON");
                page.Request("home");Check(!page.IsVisible&&home.PresentationVisible,"Home control restores actual home presentation");
                foreach(string destination in new[]{"shop","leaderboard","journey"}){
                    string routed=null;UnityEngine.Events.UnityAction<string> listener=value=>routed=value;home.NavigationRequested.AddListener(listener);
                    home.NavigationRequested.Invoke("teams");page.Request(destination);home.NavigationRequested.RemoveListener(listener);
                    Check(!page.IsVisible&&routed==destination,"Unavailable Teams retains bottom navigation to "+destination);
                }
                // A selected, unready managed gateway must stay managed and retryable, rather than showing the local setup diagnosis or a sample team.
                var host=owner.AddComponent<PlayerProfileHost>();host.enabled=false;var gateway=owner.AddComponent<ServerGameSession>();gateway.enabled=false;
                Set(host,"<ServerSession>k__BackingField",gateway);page.Show();
                Check(page.ReviewSession==null&&Field<ServerGameSession>(online,"gateway")==gateway&&!Field<bool>(online,"unconfigured"),"Selected managed gateway takes precedence over local and sample paths");
                Check(online.VerificationNodes.ContainsKey("online-retry")&&online.VerificationNodes["online-unavailable"].GetComponent<Text>().text!=OnlineTeamsText82.T("OnlineSetup"),"Transient managed unavailability retains recovery and a distinct diagnosis");
                page.Request("create");page.Request("join:"+new string('a',32));Check(online.VerificationSession==null&&!online.VerificationPending,"Unready managed gateway blocks mutations");page.Hide();
                Set(host,"<ServerSession>k__BackingField",null);page.Show();Unavailable(online);page.Hide();
                // Only this explicit review API opts into the historical sample team; no release configuration is changed.
                page.ResetDemo();Check(page.ReviewSession!=null&&page.ReviewSession.Data.isDemo,"Explicit review ResetDemo still opts into the historical sample fixture");
                Check(!page.IsVisible&&assets.demoData.text==demo,"Review opt-in alone neither opens UI nor rewrites sample data");
                LegacyReview116(page,home,assets);ProviderFallback116(assets);
                ConnectedGuards();
            }catch(Exception error){report.errors.Add(error.ToString());}
            finally {
                if(owner)UnityEngine.Object.DestroyImmediate(owner);GameLocale.Select(locale);
                try{report.ordinaryProfilesPreserved=before!=null&&ProfilesDigest()==before;Check(report.ordinaryProfilesPreserved,"Ordinary persistent Profiles remain byte-identical");report.languagePreferencePreserved=PlayerPrefs.HasKey(GameLocale.PreferenceKey)==hadLanguage&&PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue)==storedLanguage;Check(report.languagePreferencePreserved,"Exact saved language key presence/value preserved");}catch(Exception error){report.errors.Add(error.ToString());}
                Application.logMessageReceived-=Log;report.status=report.errors.Count==0&&report.checks>0?"PASS_NATIVE_TEAMS_DISCOVERY103":"FAIL_NATIVE_TEAMS_DISCOVERY103";
                File.WriteAllText(Path.Combine(output,"Native","TeamsDiscovery103.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));
            }
            EditorApplication.Exit(report.status=="PASS_NATIVE_TEAMS_DISCOVERY103"?0:1);
        }
        // Separate entry reaches the legacy cover regression without depending
        // on pre-R4 unavailable-page control names in the older103 matrix.
        public static void RunLegacy116(){
            output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW103_OUT")??throw new InvalidOperationException("Explicit legacy116 output required"));Directory.CreateDirectory(Path.Combine(output,"Native"));
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,scope="Actual Unity Editor legacy TeamsPage.Show, RawImage cover, scripted tab transitions and provider/fallback sprite identity. Transient explicit demo only; no service, device, reward or production acceptance."};
            int locale=GameLocale.Current;bool had=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int saved=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);string before=ProfilesDigest();GameObject owner=null;
            Application.logMessageReceived+=Log;
            try{
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);owner=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));
                var home=owner.GetComponent<HomePage>();home.enabled=false;home.State.reduceMotion=true;
                var appearance=owner.AddComponent<ProfilePage>();appearance.enabled=false;Set(appearance,"home",home);
                var assets=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(assets&&assets.demoData,"Approved legacy asset fixture available");
                var page=owner.AddComponent<TeamsPage>();page.enabled=false;page.home=home;page.assets=assets;Invoke(page,"Start");
                page.ResetDemo();Check(page.ReviewSession!=null&&page.ReviewSession.Data.isDemo&&!page.IsVisible,"Explicit ResetDemo selects only transient demo state before Show");
                LegacyReview116(page,home,assets);ProviderFallback116(assets);
            }catch(Exception error){report.errors.Add(error.ToString());}
            finally{
                if(owner)UnityEngine.Object.DestroyImmediate(owner);GameLocale.Select(locale);Application.logMessageReceived-=Log;
                report.ordinaryProfilesPreserved=before==ProfilesDigest();report.languagePreferencePreserved=had==PlayerPrefs.HasKey(GameLocale.PreferenceKey)&&saved==PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);
                if(!report.ordinaryProfilesPreserved||!report.languagePreferencePreserved)report.errors.Add("Legacy116 ordinary profile/locale preservation failed");
                report.status=report.errors.Count==0?"PASS_NATIVE_TEAMS_LEGACY116":"FAIL_NATIVE_TEAMS_LEGACY116";
                File.WriteAllText(Path.Combine(output,"Native","TeamsLegacy116.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));
            }
            EditorApplication.Exit(report.errors.Count==0?0:1);
        }
        static void LegacyReview116(TeamsPage page,HomePage home,TeamsAssets assets){
            page.Show();Check(page.IsVisible&&page.ReviewSession.Data.isDemo,"Actual legacy Show opens explicit demo page without a null cover");
            var rally=assets.Find("TM_WellRally");Check(rally,"Legacy TM_WellRally survives the new mail-provider prefix");
            var cover=page.GetComponentsInChildren<RawImage>(true).Single(v=>v.name=="rally-art");
            Check(cover.texture==rally.texture&&cover.rectTransform.rect.width>0&&cover.rectTransform.rect.height>0,"Actual legacy RawImage uses the approved rally texture with positive bounds");
            foreach(var tab in new[]{TeamsTab.Info,TeamsTab.Mail,TeamsTab.Rankings,TeamsTab.Chat}){
                // TeamsPage is a Play Mode renderer. Flush this fixture's old
                // children immediately in Edit Mode before its real Reflow,
                // avoiding deferred-Destroy Edit Mode errors unrelated to art.
                foreach(string field in new[]{"chrome","content","overlay"})foreach(Transform child in Field<RectTransform>(page,field).Cast<Transform>().ToArray())UnityEngine.Object.DestroyImmediate(child.gameObject);
                page.Request("tab:"+(int)tab);Check(page.IsVisible&&page.ReviewSession.Tab==tab,"Actual legacy transition renders "+tab);report.layouts++;
            }
            page.Hide();Check(!page.IsVisible&&home.PresentationVisible,"Legacy Hide returns actual Home presentation");
        }
        static void ProviderFallback116(TeamsAssets assets){
            var legacy=assets.sprites.Single(v=>v.id=="TM_WellRally").sprite;var fixture=UnityEngine.Object.Instantiate(assets);
            try{
                fixture.mail=Resources.Load<HeartOfTheRain.App.TeamsMail.TeamsMailAssets111>("HOTR_TeamsMail111/Assets");fixture.social=Resources.Load<HeartOfTheRain.App.TeamsSocial.TeamsSocialAssets110>("HOTR_TeamsSocial110/Assets");fixture.invites=Resources.Load<HeartOfTheRain.App.TeamsInvites.TeamsInvitesAssets112>("HOTR_TeamsInvites112/Assets");
                Check(fixture.mail&&fixture.social&&fixture.invites,"Current mail/chat/invite providers load");
                foreach(string prefix in new[]{"TM_","TC_","TI_"}){
                    string old=prefix+"Legacy116";var published=prefix=="TM_"?fixture.mail.sprites:prefix=="TC_"?fixture.social.sprites:fixture.invites.sprites;
                    var owned=published.First(v=>v.sprite&&v.sprite!=legacy);fixture.sprites=new[]{new HomeSprite{id=old,sprite=legacy},new HomeSprite{id=owned.id,sprite=legacy}};
                    Check(fixture.Find(old)==legacy,"Unowned "+prefix+" ID falls back to explicit legacy sprite");
                    Check(fixture.Find(owned.id)==owned.sprite,"Published "+prefix+" provider retains precedence over legacy collision");
                    Check(fixture.Find(prefix+"Unknown116")==null,"Unknown "+prefix+" ID still returns null");
                }
            }finally{UnityEngine.Object.DestroyImmediate(fixture);}
        }
        static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}
        static void Unavailable(OnlineTeamsPage82 page){
            var nodes=page.VerificationNodes;var frame=page.VerificationFrame;
            Check(page.IsVisible&&page.VerificationSession==null,"Unavailable page has no authenticated member/session");
            Check(nodes.ContainsKey("online-create")&&nodes.ContainsKey("online-join"),"Create and Join entry points are discoverable");
            Check(!nodes["online-create"].GetComponent<Button>().interactable&&!nodes["online-join"].GetComponent<Button>().interactable,"Unavailable actions are visibly and functionally disabled");
            Color muted;ColorUtility.TryParseHtmlString("#B9CAD2",out muted);Check(nodes["online-create-art"].GetComponent<Image>().color==muted&&nodes["online-join-art"].GetComponent<Image>().color==muted,"Unavailable entry artwork uses the existing muted palette");
            Check(!nodes.ContainsKey("online-retry")&&!nodes.ContainsKey("online-status"),"Unconfigured local mode has no ineffective retry control or repeated error footer");
            Check(nodes["online-no-team-hint"].GetComponent<Text>().text==OnlineTeamsText82.T("OnlineRequired"),"Header explains the actual online dependency");
            var body=nodes["online-unavailable"].GetComponent<Text>();Check(body.text.Replace("\n"," ")==OnlineTeamsText82.T("OnlineSetup"),"Localized setup explanation is present without an account-link requirement");
            foreach(string id in new[]{"online-create","online-join","online-no-team-hint"}){
                var e=frame.chrome.elements.Single(v=>v.id==id);Check(e.x>=0&&e.y>=0&&e.x+e.width<=frame.width+.1f&&e.y+e.height<=frame.viewportY+.1f,"Pinned entry fits viewport: "+id);
            }
            foreach(string id in new[]{"online-create-label","online-join-label","online-no-team-hint","online-unavailable"}){
                var text=nodes[id].GetComponent<Text>();Check(!text.supportRichText&&text.preferredWidth<=text.rectTransform.rect.width+1&&text.preferredHeight<=text.rectTransform.rect.height+1,"Actual localized UGUI text fits: "+id+" locale "+GameLocale.Current);
            }
        }
        static void ConnectedGuards(){
            string open=new string('a',32),full=new string('b',32);SocialTeam82 openTeam=new SocialTeam82{teamId=open,name="Open team",memberCount=2,capacity=30},fullTeam=new SocialTeam82{teamId=full,name="Full team",memberCount=30,capacity=30};
            foreach(bool pending in new[]{false,true}){
                var view=new OnlineTeamsView82{connected=true,pending=pending,directory=new SocialTeams82{teams=new[]{openTeam,fullTeam}}};var frame=OnlineTeamsLayout82.Build(420,900,view);
                Check(frame.chrome.elements.Single(v=>v.id=="online-create").action==(pending?"disabled":"create"),"Connected nonmember Create retains pending guard");
                Check(frame.content.elements.Single(v=>v.id=="online-directory-"+open).action==(pending?"disabled":"join:"+open),"Connected directory Join retains team binding and pending guard");
                Check(frame.content.elements.Single(v=>v.id=="online-directory-"+full).action=="disabled","Full teams cannot be joined");
            }
            var empty=OnlineTeamsLayout82.Build(420,900,new OnlineTeamsView82{connected=true,directory=new SocialTeams82{teams=new SocialTeam82[0]}});Check(empty.chrome.elements.Any(v=>v.action=="create")&&empty.content.elements.Any(v=>v.id=="online-empty-directory"),"Connected empty directory still offers Create");
            openTeam.isMember=true;openTeam.description="Server-owned membership fixture";openTeam.members=new SocialTeamMember82[0];
            var member=OnlineTeamsLayout82.Build(420,900,new OnlineTeamsView82{connected=true,team=openTeam,tab=1});Check(!member.chrome.elements.Any(v=>v.id=="online-create")&&member.content.elements.Any(v=>v.action=="leave")&&member.chrome.elements.Any(v=>v.action=="tab-chat"),"Connected member keeps Chat/Info/Leave without duplicate enrollment actions");
        }
        static void Capture(OnlineTeamsPage82 page,Vector2Int size,string file){
            // Fix the fixture's canvas geometry before the production Reflow/Fill call.
            // Changing an Overlay canvas to a new camera viewport after Fill would
            // test stale bounds and can create black areas absent from the app.
            var canvas=page.VerificationCanvas;float scale=canvas.scaleFactor;canvas.renderMode=RenderMode.WorldSpace;canvas.GetComponent<CanvasScaler>().enabled=false;
            var rect=(RectTransform)canvas.transform;rect.anchorMin=rect.anchorMax=rect.pivot=Vector2.one*.5f;rect.localPosition=Vector3.zero;rect.localScale=Vector3.one;rect.sizeDelta=new Vector2(size.x/scale,size.y/scale);
            page.VerificationViewport(size.x,size.y);Canvas.ForceUpdateCanvases();Check(Math.Abs(canvas.scaleFactor-scale)<.001f,"Fixed capture uses the actual page's unchanged UI scale");
            var backdrop=page.VerificationNodes["online-teams-background"];var corners=new Vector3[4];rect.GetWorldCorners(corners);
            foreach(var corner in corners){Vector3 point=backdrop.InverseTransformPoint(corner);Check(point.x>=backdrop.rect.xMin-.01f&&point.x<=backdrop.rect.xMax+.01f&&point.y>=backdrop.rect.yMin-.01f&&point.y<=backdrop.rect.yMax+.01f,"Production backdrop covers every fixed native canvas corner");}
            var root=new GameObject("Teams103 fixed native framebuffer camera");var camera=root.AddComponent<Camera>();camera.enabled=false;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.magenta;camera.orthographic=true;camera.orthographicSize=size.y/(2*scale);camera.aspect=size.x/(float)size.y;camera.transform.position=canvas.transform.position-new Vector3(0,0,10);camera.nearClipPlane=.1f;camera.farClipPlane=100;
            var target=new RenderTexture(size.x,size.y,24);target.Create();var active=RenderTexture.active;var old=canvas.worldCamera;Texture2D pixels=null;
            try{
                camera.targetTexture=target;canvas.worldCamera=camera;Canvas.ForceUpdateCanvases();camera.Render();camera.Render();RenderTexture.active=target;pixels=new Texture2D(size.x,size.y,TextureFormat.RGB24,false);pixels.ReadPixels(new Rect(0,0,size.x,size.y),0,0);pixels.Apply();var data=pixels.GetPixels32();
                Func<Color32,bool> painted=p=>p.r+p.g+p.b>24&&!(p.r>245&&p.g<10&&p.b>245);
                Check(Enumerable.Range(0,size.x).All(x=>painted(data[x])&&painted(data[(size.y-1)*size.x+x])),"GPU paints the entire top and bottom framebuffer edges");
                Check(Enumerable.Range(0,size.y).All(y=>painted(data[y*size.x])&&painted(data[y*size.x+size.x-1])),"GPU paints both full side edges, including the area away from the dock");
                Check(data.Count(painted)>size.x*size.y*99/100,"GPU background coverage leaves no large black or sentinel gaps");
                File.WriteAllBytes(Path.Combine(output,"Native","TeamsDiscovery103",file),pixels.EncodeToPNG());report.captures.Add("Native/TeamsDiscovery103/"+file);
            }
            finally{canvas.worldCamera=old;camera.targetTexture=null;RenderTexture.active=active;if(pixels)UnityEngine.Object.DestroyImmediate(pixels);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(root);Canvas.ForceUpdateCanvases();}
        }
    }
}
#endif
