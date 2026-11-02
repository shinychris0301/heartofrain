#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.Journey;
using HeartOfTheRain.App.Leaderboard;
using HeartOfTheRain.App.Teams;
using HeartOfTheRain.App.Shop;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Celebrations;
using HeartOfTheRain.App.NoMoves;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;
using Manifest = HeartOfTheRain.M05.SpriteManifest;

namespace HeartOfTheRain.Verification
{
    // Explicit opt-in only. Absent from non-development players. Uses transient
    // fixtures and the onboarding memory store; never clears player preferences.
    public sealed class PlayerRegressionSuite : MonoBehaviour
    {
        public const string RequestFile = "HOTR_RunRegression";
        public static string Output => Path.Combine(Application.persistentDataPath,"Regression");
        [Serializable] public sealed class Result
        {
            public string status="RUNNING",utc,unity,platform,graphics,device,scope;
            public int width,height,checks,labels,clips,actions,boards,introductions;public bool connectedOnly;
            public List<string> passed=new List<string>(),failures=new List<string>(),frames=new List<string>(),damageFamilies=new List<string>();
        }
        public static Result Latest {get;private set;}
        HomePage home; FirstStartPage first; GameplayScreen game; GameplayUIAssets ui;
        readonly HashSet<string> textFailures=new HashSet<string>(),damage=new HashSet<string>();
        readonly HashSet<string> effectFrames=new HashSet<string>();
        int oldLocale; string context="boot"; float deadline;bool connectedOnly;
        Vector3[] homeDockCorners;readonly Vector3[] navCorners=new Vector3[4];
        sealed class MemorySettings:ISettingsStore
        {
            readonly Dictionary<string,int> values=new Dictionary<string,int>();
            public int Read(string key,int fallback)=>values.ContainsKey(key)?values[key]:fallback;
            public void Write(string key,int value){values[key]=value;}public void Flush(){}
        }
        static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static T Field<T>(object o,string name)=>(T)o.GetType().GetField(name,Private).GetValue(o);
        static void Invoke(object o,string name,params object[] args)=>o.GetType().GetMethod(name,Private).Invoke(o,args);

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Boot()
        {
            string request=Path.Combine(Application.persistentDataPath,RequestFile);
            if(!File.Exists(request))return;
            string mode;
            try{if(new FileInfo(request).Length>64)return;mode=File.ReadAllText(request).Trim();if(mode!=""&&mode!="run"&&mode!="connected-only98")return;File.Delete(request);}
            catch(IOException){return;}catch(UnauthorizedAccessException){return;}
            // Since checkpoint 41 the first scene is Launch, which then loads the
            // game scene. Survive that switch, and switch First Start to its
            // review memory store as soon as its scene loads (before any Start),
            // so the suite never touches the saved profile or preferences.
            foreach(var page in FindObjectsByType<FirstStartPage>(UnityEngine.FindObjectsSortMode.InstanceID))page.reviewAlways=true;
            UnityEngine.SceneManagement.SceneManager.sceneLoaded+=UseReviewMemory;
            var suite=new GameObject("Opt-in development regression suite");DontDestroyOnLoad(suite);suite.AddComponent<PlayerRegressionSuite>().connectedOnly=mode=="connected-only98";
        }
        static void UseReviewMemory(UnityEngine.SceneManagement.Scene scene,UnityEngine.SceneManagement.LoadSceneMode mode)
        {
            foreach(var page in FindObjectsByType<FirstStartPage>(UnityEngine.FindObjectsSortMode.InstanceID))page.reviewAlways=true;
        }
        void OnDestroy(){UnityEngine.SceneManagement.SceneManager.sceneLoaded-=UseReviewMemory;}
        void Start()
        {
            Directory.CreateDirectory(Output);oldLocale=GameLocale.Current;
            Latest=new Result{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,platform=Application.platform.ToString(),graphics=SystemInfo.graphicsDeviceType+" / "+SystemInfo.graphicsDeviceName,device=SystemInfo.deviceModel,width=Screen.width,height=Screen.height,
                connectedOnly=this.connectedOnly,scope=connectedOnly?"Focused connected-only98 memory-profile launch/introduction/refill/loss/replay-win fixtures with timed automatic obstacle cards. No standalone50-board or354-clip campaign, physical touch, performance or provider acceptance.":"Native rendered fixtures and programmatic live app actions. Accelerated playback; not manual touch coverage, physical-device certification, production services or native-language approval."};
            Application.logMessageReceived+=Log;deadline=Time.realtimeSinceStartup+1800;
            StartCoroutine(Guard(Run()));
        }
        IEnumerator Guard(IEnumerator routine)
        {
            var stack=new Stack<IEnumerator>();stack.Push(routine);
            while(stack.Count>0)
            {
                object value=null;bool moved=false;
                try {if(Time.realtimeSinceStartup>deadline)throw new TimeoutException(context);moved=stack.Peek().MoveNext();if(moved)value=stack.Peek().Current;}
                catch(Exception ex){Fail(context+": "+ex);break;}
                if(!moved){stack.Pop();continue;}
                if(value is IEnumerator nested){stack.Push(nested);continue;}
                yield return value;
            }
            GameLocale.Select(oldLocale);Latest.damageFamilies=damage.OrderBy(v=>v).ToList();
            Latest.status=connectedOnly?(Latest.failures.Count==0?"PASS_NATIVE_CONNECTED_REGRESSION98":"FAIL_NATIVE_CONNECTED_REGRESSION98"):(Latest.failures.Count==0?"PASS_NATIVE_REGRESSION":"FAIL_NATIVE_REGRESSION");
            Save();Debug.Log("HOTR_REGRESSION_COMPLETE "+Latest.status+" checks="+Latest.checks+" failures="+Latest.failures.Count+" output="+Output);
            Application.logMessageReceived-=Log;
        }
        void Log(string message,string trace,LogType type){if(type==LogType.Exception||type==LogType.Error||type==LogType.Assert)Fail(context+": "+message+"\n"+trace);}
        void Fail(string message){if(!Latest.failures.Contains(message))Latest.failures.Add(message);}
        void Check(bool ok,string name){Latest.checks++;if(ok)Latest.passed.Add(name);else Fail(name);}
        void Save(){File.WriteAllText(Path.Combine(Output,"Regression.json"),JsonUtility.ToJson(Latest,true));}
        IEnumerator Wait(Func<bool> ready,float seconds=30)
        {
            float until=Time.realtimeSinceStartup+seconds;
            while(!ready()){if(Time.realtimeSinceStartup>until)throw new TimeoutException(context);yield return null;}
            yield return null;
        }
        IEnumerator Page(string name,bool capture=true)
        {
            context=name;yield return new WaitForSecondsRealtime(.4f);Canvas.ForceUpdateCanvases();
            var dock=FindObjectsByType<RectTransform>(UnityEngine.FindObjectsSortMode.InstanceID).FirstOrDefault(r=>r.name=="dock-bg"&&r.gameObject.activeInHierarchy);
            if(dock){dock.GetWorldCorners(navCorners);if(name=="Home_en")homeDockCorners=(Vector3[])navCorners.Clone();if(homeDockCorners!=null)Check(Enumerable.Range(0,4).All(i=>Vector3.Distance(homeDockCorners[i],navCorners[i])<.6f),"Navigation dock remains fixed on "+name);}
            foreach(var text in FindObjectsByType<Text>(UnityEngine.FindObjectsSortMode.InstanceID))
            {
                if(!text.isActiveAndEnabled||text.color.a<.05f||string.IsNullOrWhiteSpace(text.text))continue;
                if(text.GetComponentsInParent<CanvasGroup>().Any(g=>g.alpha<.05f))continue;
                Latest.labels++;
                var generator=new TextGenerator();generator.Populate(text.text,text.GetGenerationSettings(text.rectTransform.rect.size));
                if(generator.vertexCount==0)
                {
                    string issue=name+" / "+text.name+": invisible text '"+text.text+"' size="+text.fontSize+" box="+text.rectTransform.rect.size;
                    if(textFailures.Add(issue))Fail(issue);
                }
            }
            if(capture)Capture(name);Save();
        }
        void Capture(string name)
        {
            string filename=string.Concat(name.Select(c=>char.IsLetterOrDigit(c)||c=='-'||c=='_'?c:'_'))+".png";
            var canvases=FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).ToArray();
            var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();
            var camera=game?game.GetComponentsInChildren<Camera>().FirstOrDefault():null;
            GameObject owned=null;
            if(!camera){owned=new GameObject("UI evidence camera");camera=owned.AddComponent<Camera>();camera.transform.position=new Vector3(-10000,0,-10);camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;}
            var previous=camera.targetTexture;var active=RenderTexture.active;
            var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);
            var pixels=new Texture2D(Screen.width,Screen.height,TextureFormat.RGBA32,false);
            try
            {
                camera.targetTexture=target;
                foreach(var canvas in canvases){canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;}
                Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;
                pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(Output,filename),pixels.EncodeToPNG());Latest.frames.Add(filename);
            }
            finally
            {
                for(int i=0;i<canvases.Length;i++){canvases[i].renderMode=RenderMode.ScreenSpaceOverlay;canvases[i].worldCamera=cameras[i];canvases[i].planeDistance=distances[i];}
                camera.targetTexture=previous;RenderTexture.active=active;RenderTexture.ReleaseTemporary(target);Destroy(pixels);if(owned)Destroy(owned);
            }
        }
        IEnumerator Run()
        {
            yield return Wait(()=>FindFirstObjectByType<FirstStartPage>()&&FindFirstObjectByType<FirstStartPage>().IsVisible);
            // Launch observes the initial page readiness before releasing its
            // cover. Leave that page visible until the real handoff completes.
            yield return Wait(()=>!FindFirstObjectByType<HeartOfTheRain.App.Launch.LaunchPage>());
            first=FindFirstObjectByType<FirstStartPage>();home=first.home;ui=first.assets.Gameplay;
            if(connectedOnly){
                Check(home.GetComponent<PlayerProfileHost>().IsTransient,"Focused connected suite requires its disposable memory profile");
                first.Request("skip");first.Request("skip");yield return Wait(()=>!first.IsVisible&&home.PresentationInteractable);
                yield return LifeRefill();yield return ConnectedFlows();yield break;
            }
            yield return Onboarding();yield return AppPages();
            home.SetPresentation(false,false);
            yield return ClipPixels();yield return Gameplay();
            if(game){game.gameObject.SetActive(false);Destroy(game.gameObject);game=null;}
            yield return null;home.SetPresentation(true,true);yield return LifeRefill();yield return ConnectedFlows();
        }
        IEnumerator Onboarding()
        {
            while(first.Stage!=FirstStartStage.Complete)
            {
                for(int locale=0;locale<5;locale++){GameLocale.Select(locale);yield return Page("FirstStart_"+first.Stage+"_"+GameLocale.Codes[locale]);}
                if(first.Stage==FirstStartStage.Prologue){first.Request("language");yield return Page("FirstStart_Languages");first.Request("language");}
                var session=Field<FirstStartSession>(first,"session");
                if(session.Practice)
                {
                    context="Practice action "+first.Stage;
                    var hint=session.Hint;
                    foreach(var cell in hint)first.Request("cell:"+cell.x+","+cell.y);
                    yield return Wait(()=>!session.Busy);
                    Check(session.Solved,"Practice "+first.Stage+" solved through page commands and real animation playback");
                    if(!session.Solved)throw new InvalidOperationException("Practice did not solve: "+first.Stage);
                    yield return Page("FirstStart_"+first.Stage+"_Solved");
                }
                if(first.Stage==FirstStartStage.Ready)first.Request("skip");else first.Request("next");
            }
            Check(!first.IsVisible,"Onboarding returns Home");
        }
        IEnumerator AppPages()
        {
            var journey=home.GetComponent<JourneyPage>();var ranks=home.GetComponent<LeaderboardPage>();var teams=home.GetComponent<TeamsPage>();var shop=home.GetComponent<ShopPage>();var settings=home.GetComponent<AppSettingsPage>();
            // Exercise settings against the same store contract without changing
            // the user's music/language preferences during this opt-in suite.
            var memory=new MemorySettings();
            settings.GetType().GetField("session",Private).SetValue(settings,new AppSettingsSession(memory,JsonUtility.FromJson<AppSettingsLinks>(settings.assets.destinations.text)));
            for(int locale=0;locale<5;locale++)
            {
                GameLocale.Select(locale);string suffix="_"+GameLocale.Codes[locale];
                yield return Page("Home"+suffix);home.ShowEvents(true);yield return Page("Events"+suffix);home.ShowEvents(false);
                if(locale==0){foreach(var feedback in FindObjectsByType<MainNavigationFeedback>(UnityEngine.FindObjectsSortMode.InstanceID)){
                    var hit=(RectTransform)feedback.transform;var before=hit.anchoredPosition;var data=new UnityEngine.EventSystems.PointerEventData(UnityEngine.EventSystems.EventSystem.current);
                    feedback.OnPointerDown(data);yield return new WaitForSecondsRealtime(.08f);var icon=Field<Graphic>(feedback,"icon");Check(icon.rectTransform.localScale.x<.999f,"Navigation press animates "+hit.name);Check(hit.anchoredPosition==before,"Navigation hit bounds stay fixed "+hit.name);feedback.OnPointerUp(data);
                }yield return new WaitForSecondsRealtime(.35f);}
                journey.Show();yield return Page("Journey"+suffix);journey.Request("view:1");yield return Page("Journey_Opening"+suffix);journey.Request("reader-close");journey.Hide();
                ranks.Show();
#if UNITY_EDITOR
                for(int tab=0;tab<3;tab++){ranks.Request("tab:"+tab);yield return Page("Ranks_"+tab+suffix);}
                ranks.Request("tab:0");ranks.Request("find");Check(ranks.ReviewSession.Finding,"Friends search opened "+suffix);yield return Page("Ranks_Search"+suffix);ranks.Request("list");
                var friend=ranks.ReviewSession.Data.friendIds.FirstOrDefault();if(friend!=null){ranks.Request("remove:"+friend);yield return Page("Ranks_Remove"+suffix);ranks.Request("cancel-remove");}ranks.Hide();
                teams.ResetDemo();teams.Show();for(int tab=0;tab<3;tab++){teams.Request("tab:"+tab);yield return Page("Teams_"+tab+suffix);}teams.Hide();
                teams.Show();teams.Request("tab:0");teams.Request("compose");Check(teams.ReviewSession.Composing,"Demo message editor opens "+suffix);yield return Page("Teams_Compose"+suffix);teams.Request("cancel-compose");
                foreach(var letter in teams.ReviewSession.Data.mail){teams.Request("mail:"+letter.id);yield return Page("Teams_Mail_"+letter.id+suffix,locale==0);teams.Request("close-mail");}teams.Hide();
#else
                // Player builds have no serialized social sample data. Keep the
                // opt-in device sweep on the real unavailable/service pages.
                yield return Page("Ranks_Service"+suffix);ranks.Hide();
                teams.Show();Check(ranks.ReviewSession==null&&teams.ReviewSession==null,"Development Android social pages do not resurrect sample sessions");yield return Page("Teams_Service"+suffix);teams.Hide();
#endif
                shop.Show();yield return Page("Shop"+suffix);
                foreach(var offer in shop.ReviewSession.Specials.Concat(shop.ReviewSession.Mega).Concat(shop.ReviewSession.Coins))
                {var carousel=Field<ShopCarouselInput>(shop,"carousel");yield return Wait(()=>!carousel||!carousel.Busy);shop.Request("offer:"+offer.id);Check(shop.ReviewSession.Modal&&shop.ReviewSession.OpenOfferId==offer.id,"Offer details "+offer.id+suffix);yield return Page("Shop_"+offer.id+suffix,locale==0);shop.Request("close");}
                shop.Hide();memory.Write(GameLocale.PreferenceKey,locale);settings.Show();yield return Page("Settings"+suffix);
                foreach(string section in new[]{"inventory","language","help","follow"}){settings.Request(section);yield return Page("Settings_"+section+suffix);settings.Request("back");}
                settings.Hide();
                var flow=home.GetComponent<HomeLevelFlow>();flow.Open(1);yield return Page("PreLevel"+suffix);home.GetComponent<PreLevelModal>().Requested("close");
            }
        }
        IEnumerator ClipPixels()
        {
            context="Atlas clip render comparison";
            var bank=new M46AtlasBank(ui.boards);var draws=new List<DrawSprite>();
            for(int i=0;i<ui.boards.powerManifests.Length;i++)
            {
                var manifest=JsonUtility.FromJson<Manifest>(ui.boards.powerManifests[i].text);
                foreach(var clip in manifest.clips)draws.Add(new DrawSprite{bank="power",atlas=i,key=clip.name,age=(clip.count/2f)/clip.fps});
            }
            foreach(var clip in ui.boards.obstacleClips){var data=JsonUtility.FromJson<ClipData>(clip.metadata.text);draws.Add(new DrawSprite{bank="obstacle",key=clip.key,age=(data.frames.Length/2f)/data.fps});}
            foreach(var body in ui.boards.bodies)draws.Add(new DrawSprite{bank="body",key=body.key});
            var go=new GameObject("Clip render fixture");go.transform.position=new Vector3(-20000,0,0);var sr=go.AddComponent<SpriteRenderer>();
            var cameraGo=new GameObject("Clip evidence camera");var camera=cameraGo.AddComponent<Camera>();camera.transform.position=new Vector3(-20000,0,-10);camera.orthographic=true;camera.backgroundColor=Color.black;camera.clearFlags=CameraClearFlags.SolidColor;
            var target=new RenderTexture(96,96,24);camera.targetTexture=target;var pixels=new Texture2D(96,96,TextureFormat.RGB24,false);var standard=new Material(ui.bodyShader);
            var block=new MaterialPropertyBlock();int tested=0;
            foreach(var draw in draws)
            {
                bank.BeginFrame();sr.sprite=bank.Get(draw);if(!sr.sprite)continue;
                camera.orthographicSize=Mathf.Max(sr.sprite.bounds.size.x,sr.sprite.bounds.size.y)*.55f;
                sr.GetPropertyBlock(block);block.SetTexture("_MainTex",sr.sprite.texture);block.SetFloat("_Glow",0);sr.SetPropertyBlock(block);
                sr.sharedMaterial=standard;int expected=LitPixels(camera,target,pixels);
                sr.sharedMaterial=ui.boards.effectsMaterial;int actual=LitPixels(camera,target,pixels);
                Check(expected==actual,"Rendered clip "+draw.bank+"/"+draw.atlas+"/"+draw.key+" pixels "+actual+" reference "+expected);
                Latest.clips++;bank.EndFrame(true);
                if(++tested%10==0){Save();yield return null;}
            }
            sr.sprite=null;bank.Dispose();camera.targetTexture=null;Destroy(standard);Destroy(pixels);Destroy(target);Destroy(go);Destroy(cameraGo);yield return null;
        }
        static int LitPixels(Camera camera,RenderTexture target,Texture2D pixels)
        {
            var previous=RenderTexture.active;camera.Render();RenderTexture.active=target;pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();RenderTexture.active=previous;
            return pixels.GetPixels32().Count(p=>p.r>5||p.g>5||p.b>5);
        }
        IEnumerator Gameplay()
        {
            GameLocale.Select(0); // Include English HUD fitting in live playback checks.
            var go=new GameObject("Live gameplay regression fixture");game=go.AddComponent<GameplayScreen>();game.uiAssets=ui;game.showLevelIntro=false;game.playbackSpeed=5;
            yield return Wait(()=>game.InitializationComplete);
            game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;
            yield return Page("Gameplay_English_HUD");
            yield return PowerupDeviceVerification.Run(game,ui,Capture,Check);
            game.StepStarted+=step=>{foreach(var hit in step.damage)damage.Add(hit.family);};
            for(int level=1;level<=50;level++)
            {
                context="Level "+level;game.Load(level-1);yield return Wait(()=>game.InitializationComplete);game.Model.Validate();Latest.boards++;
                if(level==1||level==21||level==28||level==36||level==49||level==50)yield return Page("Board_L"+level);
                Check(game.ReviewNaturalMove(),"L"+level+" accepts natural move");yield return Playback("L"+level+"_Match",level==1);
                for(int tool=0;tool<4;tool++)
                {
                    if(game.Model.Status!="Playing"){game.Load(level-1);yield return Wait(()=>game.InitializationComplete);}
                    var target=game.Model.Pieces.Values.Where(p=>p.IsAnchor&&p.family!="pail").OrderBy(p=>p.family=="gem"||p.family=="power"?1:0).First();
                    int moves=game.Model.Moves;var inventory=Field<BoosterInventory>(game,"inventory");int stock=inventory.Count((BoosterKind)tool);
                    game.UseBooster((BoosterKind)tool,target.x,target.y);
                    Check(inventory.Count((BoosterKind)tool)==stock-1,"L"+level+" tool "+tool+" spends one stock");
                    yield return Playback("L"+level+"_Tool"+tool,level==1||level==50);
                    Check(game.Model.Moves==moves,"L"+level+" tool "+tool+" preserves moves");
                }
                Save();
            }
            game.Load(0);yield return Wait(()=>game.InitializationComplete);var cabinetFixture=new BoardModel(PlaybackFixtures.ClearingCabinet());game.GetType().GetField("board",Private).SetValue(game,cabinetFixture);game.GetType().GetField("idle",Private).SetValue(game,cabinetFixture.Snapshot());yield return null;
            game.UseBooster(BoosterKind.Hammer,3,0);var cabinetStep=Field<BoardStep>(game,"current");if(cabinetStep==null)yield return Wait(()=>Field<BoardStep>(game,"current")!=null);cabinetStep=Field<BoardStep>(game,"current");
            Check(cabinetStep.motion.Where(m=>m.toX==3||m.toX==4).All(m=>m.delay>=1.6f-.001f),"Native cabinet fixture reserves its complete footprint");Check(cabinetStep.collections.All(c=>c.arrival<=cabinetStep.duration+.001f),"Native goal flights finish before result");yield return Playback("Cabinet_Reservation",true);
            game.Load(0);yield return Wait(()=>game.InitializationComplete);var stackFixture=new BoardModel(PlaybackFixtures.StackedStones());game.GetType().GetField("board",Private).SetValue(game,stackFixture);game.GetType().GetField("idle",Private).SetValue(game,stackFixture.Snapshot());game.playbackSpeed=1;yield return null;Capture("Stacked_Stones_Before");
            game.UseBooster(BoosterKind.Hammer,4,2);int diagonalFrames=0;float stackDeadline=Time.realtimeSinceStartup+30;Latest.actions++;
            while(game.Busy){if(Time.realtimeSinceStartup>stackDeadline)throw new TimeoutException("Stacked stone refill");var active=Field<BoardStep>(game,"current");var moving=active?.motion.FirstOrDefault(m=>m.fromX!=m.toX);float age=Field<float>(game,"clock")-Field<float>(game,"started");if(diagonalFrames<3&&moving!=null&&age>=moving.delay+moving.seconds*.1f&&age<=moving.delay+moving.seconds*.95f){Capture("Stacked_Stones_Diagonal_"+diagonalFrames);diagonalFrames++;}yield return null;}
            Check(game.Model.At(4,2)!=null,"Android cleared cell below stacked stones is occupied");Check(game.Model.At(4,3)?.family=="stone"&&game.Model.At(4,4)?.family=="stone","Android fixed upper stones remain in place");Check(game.Model.Moves==20&&game.Model.Goals["stone"]==2,"Android refill preserves moves and obstacle goals");Check(diagonalFrames>0,"Android rendered explicit diagonal refill");game.Model.Validate();yield return Page("Stacked_Stones_Settled");game.playbackSpeed=5;
            foreach(int power in new[]{4,5,7,11,16,21})
            {
                game.Load(0);yield return Wait(()=>game.InitializationComplete);Check(game.ReviewActivate(power),"Standalone power "+power+" accepted");yield return Playback("Power_"+power,true);
            }
            int[][] pairs={new[]{4,4},new[]{4,21},new[]{21,21},new[]{7,4},new[]{7,21},new[]{7,7},new[]{11,4},new[]{11,21},new[]{11,11},new[]{7,11},new[]{16,4},new[]{16,21},new[]{16,11},new[]{7,16}};
            foreach(var pair in pairs)foreach(bool vertical in new[]{false,true})foreach(bool reverse in new[]{false,true})
            {
                game.Load(0);yield return Wait(()=>game.InitializationComplete);
                var board=game.Model;var a=board.Pieces.Values.First(p=>p.family=="gem"&&board.At(p.x+(vertical?0:1),p.y+(vertical?1:0))?.family=="gem");var b=board.At(a.x+(vertical?0:1),a.y+(vertical?1:0));
                board.InjectReviewPower(a.x,a.y,pair[0]==4&&vertical?5:pair[0]);board.InjectReviewPower(b.x,b.y,pair[1]==4&&vertical?5:pair[1]);
                var turn=reverse?board.Swap(b.x,b.y,a.x,a.y):board.Swap(a.x,a.y,b.x,b.y);Check(turn.accepted,"Pair accepted "+pair[0]+"+"+pair[1]+" "+vertical+" "+reverse);
                Invoke(game,"Accept",turn);yield return Playback("Pair_"+pair[0]+"_"+pair[1]+"_"+vertical+"_"+reverse,!vertical&&!reverse);
            }
            Check(damage.Count==8,"Live actions damage all eight damageable obstacle families (pail is delivered)");
            var settings=game.gameObject.AddComponent<GameplaySettingsController>();settings.Configure(game,first.assets.shared.gameplaySettings,home,decision=>{},home.GetComponent<HomeLevelFlow>().endLevelAssets);
            settings.Show();yield return Page("Gameplay_Settings");game.GetComponent<GameplaySettingsModal>().Requested("resume");
        }
        IEnumerator Playback(string name,bool capture)
        {
            context=name;Latest.actions++;int captured=0;float until=Time.realtimeSinceStartup+90;
            while(game&&game.Busy)
            {
                if(Time.realtimeSinceStartup>until)throw new TimeoutException("Playback "+name);
                if(capture&&captured<3)
                {
                    var current=Field<BoardStep>(game,"current");float age=Field<float>(game,"clock")-Field<float>(game,"started");
                    float wanted=current?.booster!=null ? .80f+captured*.25f : current?.powerPlan!=null ? current.powerPlan.primary+.04f+captured*.18f : .09f+captured*.15f;
                    if(current!=null&&age>=wanted&&(current.booster!=null||current.powerPlan!=null||current.removed.Count>0))
                    {Capture(name+"_Effect_"+captured);captured++;}
                }
                yield return null;
            }
            // Terminal UI intentionally pauses the board. Ordinary exhausted
            // moves now open Continue; failed reshuffles retain the loss dialog.
            if(game){game.Model.Validate();var continuation=game.GetComponent<NoMovesController>();Check((!game.Paused||game.Model.Status=="Won"||game.GetComponent<GameplayHUD>().LossPending||(continuation&&continuation.Active))&&game.Ready,name+" settled without unexpected pause/exception");}
            if(capture&&game)yield return Page(name+"_Settled");
        }
        IEnumerator LifeRefill()
        {
            var host=home.GetComponent<PlayerProfileHost>();
            if(!host||!host.IsTransient)throw new InvalidOperationException("Life refill fixture requires the disposable review profile");
            var saved=host.Service.Read();var flow=home.GetComponent<HomeLevelFlow>();var modal=home.GetComponent<PreLevelModal>();
            try
            {
                host.Service.Change(p=>{p.coins=899;p.lives=0;p.livesRefillDueUnix=host.Now()+1800;return true;});
                if(!host.Refresh())throw new InvalidOperationException("Refill fixture refresh failed");flow.Open(1);yield return Page("LifeRefill_Below900");
                var nodes=Field<Dictionary<string,RectTransform>>(modal,"nodes");var buy=nodes["play"].GetComponent<Button>();
                Check(flow.Preview.refillCoins==900&&!flow.Preview.canRefill&&!buy.interactable,"899 coins cannot buy the 900-coin full-life refill");
                Check(host.Service.Read().coins==899&&host.Service.Read().lives==0&&host.Service.Read().lifeRefills.Count==saved.lifeRefills.Count,"Unaffordable refill creates no debit or receipt");modal.Requested("close");
                host.Service.Change(p=>{p.coins=900;return true;});if(!host.Refresh())throw new InvalidOperationException("Exact refill fixture refresh failed");flow.Open(1);yield return Page("LifeRefill_Exactly900");
                nodes=Field<Dictionary<string,RectTransform>>(modal,"nodes");buy=nodes["play"].GetComponent<Button>();
                Check(flow.Preview.canRefill&&buy.interactable&&nodes["play-text"].GetComponent<Text>().text.Contains("900"),"Exactly 900 coins shows the enabled native refill button and price");
                buy.onClick.Invoke();buy.onClick.Invoke();var after=host.Service.Read();
                Check(after.coins==0&&after.lives==after.maxLives&&after.maxLives==5&&after.livesRefillDueUnix==0,"Native refill button spends 900 and fills all five lives");
                Check(after.lifeRefills.Count==saved.lifeRefills.Count+1&&after.lifeRefills.Last().coins==900,"Repeated native refill callback charges exactly once");yield return Page("LifeRefill_Full_After900");
            }
            finally
            {
                if(modal.IsVisible)modal.Requested("close");
                // Restore only this suite's disposable model balances/journal;
                // no owner profile, preferences or repository is substituted.
                host.Service.Change(p=>{p.coins=saved.coins;p.lives=saved.lives;p.livesRefillDueUnix=saved.livesRefillDueUnix;p.lifeRefills=saved.lifeRefills;return true;});host.Refresh();
            }
        }
        IEnumerator ConnectedLaunch(HomeLevelFlow flow,string name)
        {
            context=name;var host=home.GetComponent<PlayerProfileHost>();
            if(!host||!host.IsTransient)throw new InvalidOperationException("Connected launch fixture requires disposable memory");
            var opening=host.Service.Read();var seen=new HashSet<string>();float until=Time.realtimeSinceStartup+30;string activeFamily=null;int moves=0;
            while(true)
            {
                if(Time.realtimeSinceStartup>until)throw new TimeoutException(name+" launch/introduction");
                game=FindFirstObjectByType<GameplayScreen>();var hud=game?game.GetComponent<GameplayHUD>():null;
                if(activeFamily!=null&&hud&&(!hud.ObstacleIntroductionVisible||hud.ObstacleIntroductionFamily!=activeFamily)){
                    Check(hud.LastObstacleIntroductionFamily==activeFamily&&hud.LastObstacleIntroductionVisibleSeconds>=1.5,"Card completed its full foreground dwell before launch can advance: "+activeFamily);Latest.introductions++;activeFamily=null;
                }
                if(flow.Playing&&game&&!game.ReviewInputBlocked)break;
                if(flow.Loading&&flow.Loading.IsFailure)throw new InvalidOperationException(name+" gameplay preparation failed");
                if(hud&&hud.ObstacleIntroductionVisible)
                {
                    string family=hud.ObstacleIntroductionFamily;string attemptId=Field<string>(flow,"attemptId");var before=host.Service.Read();var attempt=before.attempts.Single(a=>a.id==attemptId);
                    Check(attempt.state=="Reserved"&&game.ReviewInputBlocked&&!game.CanAct,"Timed introduction blocks player commands before financial start: "+family);
                    Check(before.coins==opening.coins&&before.stars==opening.stars&&before.lives==opening.lives&&before.starting.SequenceEqual(opening.starting)&&before.tools.SequenceEqual(opening.tools),"Timed introduction has not spent wallet/life/stock: "+family);
                    if(activeFamily==null){
                        if(!seen.Add(family))throw new InvalidOperationException("Introduction repeated without a new launch: "+family);
                        activeFamily=family;moves=game.Model.Moves;
                        var dialog=Field<RectTransform>(hud,"modal").Find("Dialog");Check(dialog.GetComponentsInChildren<Button>().Length==0,"Timed obstacle card has no manual Continue action: "+family);
                        yield return Page(name+"_Introduction_"+family);
                    }
                    Check(game.Model.Moves==moves,"Waiting for automatic introduction dismissal preserves moves: "+family);
                }
                yield return null;
            }
            var started=host.Service.Read();string currentId=Field<string>(flow,"attemptId");
            Check(started.attempts.Single(a=>a.id==currentId).state=="Started","Connected launch commits Started only after timed introductions: "+name);
            Check(started.coins==opening.coins&&started.stars==opening.stars&&started.lives==opening.lives&&started.starting.SequenceEqual(opening.starting)&&started.tools.SequenceEqual(opening.tools),"Connected launch/intro dismissal preserves unselected stock and balances: "+name);
            yield return null;
        }
        IEnumerator ConnectedFlows()
        {
            var flow=home.GetComponent<HomeLevelFlow>();var modal=home.GetComponent<PreLevelModal>();
            home.State.currentLevel=1;home.State.completedLevelsInChapter=0;home.State.lives=5;home.ApplyState(home.State);
            flow.Open(1);modal.Requested("play");yield return ConnectedLaunch(flow,"Connected_Launch");
            game=FindFirstObjectByType<GameplayScreen>();game.playbackSpeed=10;
            var target=game.Model.Pieces.Values.First(p=>p.family=="gem");game.UseBooster(BoosterKind.Hammer,target.x,target.y);yield return Playback("Connected_Tool",false);
            int stock=flow.ToolStockSnapshot()[0];game.Load(0);yield return Wait(()=>game.InitializationComplete);
            Check(Field<BoosterInventory>(game,"inventory").hammer==stock,"Connected reload retains tool stock");
            // Deterministic loss fixture: the first legal move in the authored
            // level can eventually win. Use a transient one-move model with the
            // same board geometry/content; never edit the authored level asset.
            var lossData=JsonUtility.FromJson<LevelData>(JsonUtility.ToJson(game.Model.Level));lossData.movesProposal=1;
            var lossBoard=new BoardModel(lossData);
            game.GetType().GetField("board",Private).SetValue(game,lossBoard);
            game.GetType().GetField("idle",Private).SetValue(game,lossBoard.Snapshot());
            Check(game.Model.Moves==1,"Transient loss fixture has one move; authored level is unchanged");
            int lives=home.State.lives;
            while(flow.Playing&&game.Model.Status=="Playing")
            {if(!game.ReviewNaturalMove())throw new InvalidOperationException("Cannot drive failure fixture");yield return Playback("Connected_Failure_Move",false);}
            // Checkpoint 68+: exhaustion preserves the board in Continue.
            // Decline through the actual controller and confirmation before
            // asserting the unified loss settlement; no purchase is dispatched.
            var noMoves=game.GetComponent<NoMovesController>();var exhausted=game.Model;int coins=home.State.coins;
            yield return Wait(()=>noMoves&&noMoves.Active&&noMoves.Page&&noMoves.Page.Screen=="offer");
            Check(game.Model.Status=="Out of moves"&&ReferenceEquals(game.Model,exhausted)&&home.State.lives==lives&&home.State.coins==coins,"Continue offers the exhausted board before any life or coin charge");
            Check(noMoves.Offer!=null&&noMoves.Offer.moves==5&&noMoves.Offer.cost==900,"Connected Continue exposes the approved five-move/900-coin offer");yield return Page("Connected_OutOfMoves_Continue");
            noMoves.Request("back");Check(noMoves.Page.Screen=="confirm"&&home.State.lives==lives&&home.State.coins==coins,"Closing Continue asks for confirmation without charging");
            noMoves.Request("end");yield return Wait(()=>flow.RetryVisible);game=null;
            Check(home.State.lives==lives-1&&home.State.coins==coins,"Confirmed decline charges exactly one life, no coins, and opens retry pre-level");yield return Page("Connected_OutOfMoves_Retry");
            yield return new WaitForSecondsRealtime(.3f);Check(home.State.lives==lives-1,"Repeated settled frames do not charge another life");
            modal.Requested("play");yield return ConnectedLaunch(flow,"Connected_Retry");game=FindFirstObjectByType<GameplayScreen>();
            Check(Field<BoosterInventory>(game,"inventory").hammer==stock,"Retry retains spent tool stock");
            var settings=game.GetComponent<GameplaySettingsController>();settings.ShowEndLevel();yield return Page("Connected_Exit");game.GetComponent<HeartOfTheRain.App.EndLevel.EndLevelModal>().Requested("cancel");
            Check(home.State.lives==lives-1&&!game.Paused,"Exit cancellation preserves life and resumes");
            flow.ReturnHomeForReview();game=null;yield return null;
            var replays=JsonUtility.FromJson<CampaignReplaySet>(Resources.Load<TextAsset>("HOTR_Playtests/Campaign_Replays").text);
            foreach(var run in replays.runs)
            {
                home.State.currentLevel=run.level;home.State.completedLevelsInChapter=run.level-1;home.State.coins=1250;home.State.stars=0;home.ApplyState(home.State);
                flow.Open(run.level);modal.Requested("play");yield return ConnectedLaunch(flow,"Connected_Replay_L"+run.level);
                game=FindFirstObjectByType<GameplayScreen>();game.playbackSpeed=10;game.Load(run.level-1,(uint)run.seed,"regression-replay");yield return Wait(()=>game.InitializationComplete);
                foreach(var action in run.actions)
                {
                    string error;bool accepted=game.ReviewReplayMove(action,out error);Check(accepted,"Connected replay L"+run.level+" "+action.before);if(!accepted)throw new InvalidOperationException(error);
                    yield return Playback("Connected_Replay_L"+run.level,false);
                }
                yield return Wait(()=>VictoryCelebrationPlayer.IsPlaying(home)||ChapterCelebrationPlayer.IsPlaying(home));
                Check(home.State.coins==1300&&home.State.stars==1,"Connected L"+run.level+" grants one first-clear reward");
                yield return new WaitForSecondsRealtime(.8f);yield return Page("Connected_Win_L"+run.level);
                var victory=home.GetComponent<VictoryCelebrationPlayer>();var finale=home.GetComponent<ChapterCelebrationPlayer>();
                if(finale&&finale.IsVisible)
                {
                    yield return new WaitForSecondsRealtime(3);yield return Page("Finale_Daria");
                    yield return new WaitForSecondsRealtime(5);yield return Page("Finale_City_Hook");finale.Finish();finale.Finish();
                }
                else if(victory){yield return Wait(()=>!victory.IsVisible,10);victory.Finish();}
                Check(home.State.coins==1300&&home.State.stars==1,"Celebration completion cannot grant a duplicate reward L"+run.level);
                Check(!modal.IsVisible&&!flow.Playing,"Celebration returns Home without next-level modal L"+run.level);
                yield return Page("Home_Reward_Increase_L"+run.level);
                yield return Wait(()=>!home.RewardRevealPlaying,4);yield return Page("Home_Reward_L"+run.level);
                game=null;if(modal.IsVisible)modal.Requested("close");home.GetComponent<JourneyPage>().Hide();yield return null;
            }
        }
    }
}
#endif
