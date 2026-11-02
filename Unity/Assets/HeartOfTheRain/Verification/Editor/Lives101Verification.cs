#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Settings;

namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class Lives101Verification {
        const string Key="HOTR.Lives101";const BindingFlags Hidden=BindingFlags.Instance|BindingFlags.NonPublic;
        static readonly Vector2Int[] Sizes={new Vector2Int(393,852),new Vector2Int(320,480),new Vector2Int(768,1024)};
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity,error;
            public string scope="Actual Editor PlayMode heart-position UGUI raycast/click, imported approved modal artwork and isolated memory profile.75locale/size/life states, model/controller command barriers, zero-only900-coin refill, natural regeneration and due-time refill race. Synthetic clocks and callbacks; not physical input, Android, real server or human visual acceptance.";
            public int checks,layouts,cases;public List<string> captures=new List<string>(),geometryFailures=new List<string>();
        }
        sealed class Settings:ISettingsStore {public int Read(string key,int fallback)=>fallback;public void Write(string key,int value){}public void Flush(){}}
        static Report report;static HomePage home;static HomeLevelFlow flow;static PreLevelModal modal;static PlayerProfileHost host;
        static long now=1000;static int phase,index,initialReceipts,seedFrame;static double began,next;static string digest;
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW101_OUT")??"../Verification/Evidence/Review101/Lives");
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static object Group(){var a=typeof(Editor).Assembly;var t=a.GetType("UnityEditor.GameViewSizes");var singleton=typeof(ScriptableSingleton<>).MakeGenericType(t).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);return t.GetMethod("GetGroup").Invoke(singleton,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":"Standalone")});}
        static Lives101Verification(){if(SessionState.GetBool(Key,false)){report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};began=EditorApplication.timeSinceStartup;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;SceneManager.sceneLoaded+=Isolate;}}
        static void Isolate(Scene scene,LoadSceneMode mode){var first=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();if(!first)return;first.reviewAlways=true;var profile=first.home.GetComponent<PlayerProfileHost>();if(!profile)profile=first.home.gameObject.AddComponent<PlayerProfileHost>();profile.VerificationLivesClock=()=>now;profile.VerificationCupClock=()=>now;foreach(var settings in UnityEngine.Object.FindObjectsByType<AppSettingsPage>(FindObjectsSortMode.InstanceID))settings.VerificationStore=new Settings();}
        public static void Run(){
            if(!Application.isBatchMode)throw new InvalidOperationException("Explicit batch-only memory fixture");
            SessionState.SetBool(Key,true);SessionState.SetInt(Key+".locale",GameLocale.Current);
            var group=Group();int first=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);SessionState.SetInt(Key+".first",first);SessionState.SetInt(Key+".previous",(int)View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).GetValue(View()));
            var assembly=typeof(Editor).Assembly;foreach(var size in Sizes){var item=Activator.CreateInstance(assembly.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(assembly.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),size.x,size.y,"HOTR lives101"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{item});}
            SetSize(0);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;EditorApplication.isPlaying=true;
        }
        static void SetSize(int size){View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(View(),SessionState.GetInt(Key+".first",0)+size);View().Repaint();next=EditorApplication.timeSinceStartup+.25;}
        static void Need(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.error=message+"\n"+stack;}
        static T Field<T>(object value,string name)=>(T)value.GetType().GetField(name,Hidden).GetValue(value);
        static Vector2 VerticalBounds(RectTransform panel,RectTransform node){var corners=new Vector3[4];node.GetWorldCorners(corners);float min=float.PositiveInfinity,max=float.NegativeInfinity;foreach(var corner in corners){float y=panel.InverseTransformPoint(corner).y;min=Mathf.Min(min,y);max=Mathf.Max(max,y);}return new Vector2(panel.rect.yMax-max,panel.rect.yMax-min);}
        static string Digest()=>ProfileJson.Hash(JsonUtility.ToJson(host.Service.Read()));
        static void Seed(int lives,int coins,long due){now=1000;host.Service.Change(p=>{p.coins=coins;p.lives=lives;p.livesRefillDueUnix=due;return true;});Need(host.Refresh(),"Authoritative local fixture refresh succeeds");home.State.reduceMotion=true;digest=Digest();seedFrame=Time.frameCount;}
        static void TapHeart(){
            Canvas.ForceUpdateCanvases();var nodes=Field<Dictionary<string,RectTransform>>(home,"nodes");var header=nodes["header"];var button=nodes["lives"].GetComponent<Button>();
            var point=RectTransformUtility.WorldToScreenPoint(null,header.TransformPoint(new Vector3(header.rect.width*.60f,-header.rect.height*.5f,0)));
            var data=new PointerEventData(EventSystem.current){position=point,button=PointerEventData.InputButton.Left};var hits=new List<RaycastResult>();EventSystem.current.RaycastAll(data,hits);
            Need(hits.Count>0&&hits[0].gameObject.GetComponentInParent<Button>()==button,"Actual healthy-heart position reaches the lives route [frame="+Time.frameCount+", seedFrame="+seedFrame+", hits="+hits.Count+", first="+(hits.Count>0?hits[0].gameObject.name:"none")+"]");ExecuteEvents.Execute(button.gameObject,data,ExecuteEvents.pointerClickHandler);
        }
        static void Core(){
            var session=new PreLevelSession(new[]{5,4,3,2});session.OpenLives(3,5);PreLevelTicket play=null;
            Need(session.IsOpen&&session.View.livesOnly&&!session.TryBegin(out play),"Lives-only session cannot reserve gameplay");
            for(int i=0;i<4;i++)Need(!session.Toggle(i)&&!session.View.selected[i]&&session.Count(i)==new[]{5,4,3,2}[i],"Lives-only session cannot select or spend booster"+i);
            PreLevelRefillTicket refill;Need(!session.TryBeginRefill(out refill),"Partial lives cannot purchase a zero-only refill");Need(session.Close(),"Information-only lives panel can close");
            session.Open(1,3,new[]{new PreLevelGoal{family="crate",count=2}},50,1);Need(!session.View.livesOnly&&session.Toggle(0)&&session.TryBegin(out play),"Explicit level preview retains booster selection and Play");Need(session.Fail(play,"fixture")&&session.Close(),"Ordinary launch reservation can be released");
            session.OpenLives(0,5);session.RefreshLifeTimer(1800,true,900);Need(session.TryBeginRefill(out refill)&&!session.Close()&&!session.TryBegin(out play)&&!session.Toggle(0),"Refill ticket retains all presentation barriers in lives-only mode");Need(session.CompleteRefill(refill)&&!session.CompleteRefill(refill),"Matching refill ticket completes once");
            report.cases++;
        }
        static void Inspect(int state){
            Need(modal.IsVisible&&flow.Preview.livesOnly,"Heart opens the dedicated lives view");Need(!flow.Playing&&!flow.Loading.IsVisible&&!flow.Loading.art&&Field<ResourceRequest>(flow,"artRequest")==null,"Heart does not start or prepare gameplay artwork");
            var nodes=Field<Dictionary<string,RectTransform>>(modal,"nodes");Need(!nodes.Keys.Any(k=>k.StartsWith("booster-",StringComparison.Ordinal)||k.StartsWith("target-",StringComparison.Ordinal)||k.StartsWith("reward-",StringComparison.Ordinal))&&!nodes.ContainsKey("level"),"Lives panel contains no level, goals, rewards or boosters");
            var data=flow.Preview;Need(nodes["lives-heart"].GetComponent<Image>().sprite==HomeLivesAssets.Load().heart,"Approved healthy-heart artwork is reused");Need(nodes["lives-count"].GetComponent<Text>().text==data.lives+" / 5","Current and maximum lives are accurate");Need(nodes.ContainsKey("lives-clock")== (data.lives<5),"Countdown clock appears only below full");
            if(data.lives>0){
                var panel=nodes["panel"];var heart=VerticalBounds(panel,nodes["lives-heart"]);var count=VerticalBounds(panel,nodes["lives-count"]);var status=VerticalBounds(panel,nodes["lives-status"]);
                bool separated=heart.y+2<=count.x+.01f&&count.y+2<=status.x+.01f,cream=count.x>=60-.01f&&status.x>=60-.01f&&status.y<=200+.01f;
                Vector2 clock=nodes.ContainsKey("lives-clock")?VerticalBounds(panel,nodes["lives-clock"]):Vector2.zero;bool clockInside=!nodes.ContainsKey("lives-clock")||clock.x>=60-.01f&&clock.y<=200+.01f;
                if(!separated||!cream||!clockInside){report.geometryFailures.Add("state="+state+", heart="+heart+", count="+count+", status="+status+", clock="+clock);Capture("Failure_Positive_"+state+"_"+Screen.width+"x"+Screen.height);}
                Need(separated,"Actual heart, count and status retain separate vertical space");
                Need(cream,"Positive-life dark text stays inside the approved cream region and above its gold/footer seam");
                if(nodes.ContainsKey("lives-clock"))Need(clockInside,"Actual clock stays inside the cream region");
            }
            if(data.lives>0)Need(!nodes.ContainsKey("play"),"Remaining or full lives have no purchase or Play control");else{var button=nodes["play"].GetComponent<Button>();Need(nodes["play-text"].GetComponent<Text>().text.Contains("900")&&button.interactable==(state==4),"Zero-life900 offer stays visible at899 and900 balances");Need(nodes["play"].GetComponent<HomeControlLabel>().action=="refill","Zero-life primary action refills without starting a level");}
            foreach(var text in nodes.Values.Select(n=>n.GetComponent<Text>()).Where(t=>t)){
                var mesh=text.canvasRenderer.GetMesh();float area=0;if(mesh){var vertices=mesh.vertices;var triangles=mesh.triangles;for(int t=0;t+2<triangles.Length;t+=3)area+=Vector3.Cross(vertices[triangles[t+1]]-vertices[triangles[t]],vertices[triangles[t+2]]-vertices[triangles[t]]).magnitude*.5f;}
                Need(mesh&&mesh.vertexCount>=4&&area>0&&!text.canvasRenderer.cull&&text.color.a>.9f,"Native life label has visible geometry: "+text.name);Need(text.preferredWidth<=text.rectTransform.rect.width+1&&text.preferredHeight<=text.rectTransform.rect.height+1,"Native life label fits: "+text.name);
            }
            modal.Requested("toggle:0");modal.Requested("play");Need(!flow.Preview.selected.Any(v=>v)&&!flow.Preview.busy&&!flow.Playing&&!flow.Loading.IsVisible&&Digest()==digest,"Synthetic hidden commands cannot select, launch, or mutate model");
        }
        static void Capture(string name){
            var canvases=UnityEngine.Object.FindObjectsByType<Canvas>(FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).ToArray();var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();
            var node=new GameObject("Lives101 capture");node.transform.position=new Vector3(-10000,0,-10);var camera=node.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;var prior=RenderTexture.active;var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);Texture2D image=null;
            try{camera.targetTexture=target;foreach(var canvas in canvases){canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;}Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;image=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);image.ReadPixels(new Rect(0,0,target.width,target.height),0,0);image.Apply();string relative="Native/Lives101/"+name+".png";Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(Output,relative)));File.WriteAllBytes(Path.Combine(Output,relative),image.EncodeToPNG());report.captures.Add(relative);}
            finally{for(int i=0;i<canvases.Length;i++){canvases[i].renderMode=RenderMode.ScreenSpaceOverlay;canvases[i].worldCamera=cameras[i];canvases[i].planeDistance=distances[i];}camera.targetTexture=null;RenderTexture.active=prior;RenderTexture.ReleaseTemporary(target);if(image)UnityEngine.Object.Destroy(image);UnityEngine.Object.Destroy(node);}
        }
        static void Tick(){try{
            if(EditorApplication.timeSinceStartup-began>240)throw new TimeoutException("Lives101 native deadline");if(report.error!=null)throw new InvalidOperationException("Native logged error");if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup<next)return;
            if(phase==0){var first=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();if(!first||!first.Initialized)return;home=first.home;host=home.GetComponent<PlayerProfileHost>();if(!host||!host.Ready)return;Need(first.reviewAlways&&host.IsTransient&&!host.ServerSession,"Only disposable memory is selected");first.Request("skip");first.Request("skip");flow=home.GetComponent<HomeLevelFlow>();modal=home.GetComponent<PreLevelModal>();Core();phase=1;next=EditorApplication.timeSinceStartup+.25;return;}
            if(phase==1){int size=index/25;if(Screen.width!=Sizes[size].x||Screen.height!=Sizes[size].y)return;GameLocale.Select(index/5%5);int state=index%5;Seed(state==0?5:state==1?3:state==2?1:0,state==3?899:state==4?900:1250,state==0?0:2800);phase=2;next=EditorApplication.timeSinceStartup+.15;return;}
            if(phase==2){if(Time.frameCount<=seedFrame)return;digest=Digest();TapHeart();phase=3;next=EditorApplication.timeSinceStartup+.15;return;}
            if(phase==3){int state=index%5;Inspect(state);if(index/5%5==4&&index/25!=1)Capture("Lives_"+state+"_ru_"+Screen.width+"x"+Screen.height);modal.Requested("close");Need(!modal.IsVisible&&home.PresentationInteractable&&Digest()==digest,"Closing lives keeps model unchanged and returns Home");report.layouts++;index++;if(index==75){SetSize(0);phase=4;}else{if(index%25==0)SetSize(index/25);phase=1;}next=EditorApplication.timeSinceStartup+.1;return;}
            if(phase==4){if(Screen.width!=393||Screen.height!=852)return;GameLocale.Select(4);Seed(0,900,2800);initialReceipts=host.Service.Read().lifeRefills.Count;phase=40;next=EditorApplication.timeSinceStartup+.15;return;}
            if(phase==40){if(Time.frameCount<=seedFrame)return;TapHeart();phase=5;next=EditorApplication.timeSinceStartup+.15;return;}
            if(phase==5){var nodes=Field<Dictionary<string,RectTransform>>(modal,"nodes");var button=nodes["play"].GetComponent<Button>();ExecuteEvents.Execute(button.gameObject,new PointerEventData(EventSystem.current){button=PointerEventData.InputButton.Left},ExecuteEvents.pointerClickHandler);var after=host.Service.Read();Need(after.coins==0&&after.lives==5&&after.lifeRefills.Count==initialReceipts+1,"Actual refill control commits900 coins for all five lives once");modal.Requested("refill");modal.Requested("play");modal.Requested("toggle:0");after=host.Service.Read();Need(after.coins==0&&after.lives==5&&after.lifeRefills.Count==initialReceipts+1&&after.attempts.Count==0&&flow.Preview.livesOnly,"Refill and repeated hidden commands never auto-start or debit twice");modal.Requested("close");report.cases++;phase=6;return;}
            if(phase==6){Seed(0,900,1001);initialReceipts=host.Service.Read().lifeRefills.Count;phase=60;next=EditorApplication.timeSinceStartup+.15;return;}
            if(phase==60){if(Time.frameCount<=seedFrame)return;TapHeart();now=1001;modal.Requested("refill");var after=host.Service.Read();Need(after.coins==900&&after.lives==1&&after.lifeRefills.Count==initialReceipts&&flow.Preview.lives==1&&string.IsNullOrEmpty(flow.Preview.message),"Life due at refill tap refreshes to one life without charge or contradictory denial");modal.Requested("close");report.cases++;phase=7;return;}
            if(phase==7){Seed(3,900,1001);phase=70;next=EditorApplication.timeSinceStartup+.15;return;}
            if(phase==70){if(Time.frameCount<=seedFrame)return;TapHeart();now=1001;phase=8;next=EditorApplication.timeSinceStartup+1.2;return;}
            if(phase==8){Need(host.Service.Read().lives==4&&flow.Preview.lives==4&&Field<Dictionary<string,RectTransform>>(modal,"nodes")["lives-count"].GetComponent<Text>().text=="4 / 5","Open partial-lives sheet updates natural regeneration and visible count");Need(host.Service.Read().coins==900&&host.Service.Read().attempts.Count==0,"Countdown refresh does not spend or reserve gameplay");modal.Requested("close");report.cases++;flow.Open(1);Need(!flow.Preview.livesOnly&&flow.Preview.goals.Length>0&&Field<Dictionary<string,RectTransform>>(modal,"nodes").ContainsKey("booster-0"),"Explicit Level route retains original start preview");modal.Requested("close");Finish(true);}
        }catch(Exception error){if(report.error==null)report.error=error.GetType().Name+": "+error.Message;Finish(false);}}
        static void Finish(bool ok){
            EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SceneManager.sceneLoaded-=Isolate;GameLocale.Select(SessionState.GetInt(Key+".locale",4));
            try{View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(View(),SessionState.GetInt(Key+".previous",0));var group=Group();int first=SessionState.GetInt(Key+".first",0);for(int i=0;i<Sizes.Length;i++)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{first});}catch(Exception error){report.error=report.error??error.GetType().Name;ok=false;}
            report.status=ok?"PASS_NATIVE_LIVES101":"FAIL_NATIVE_LIVES101";SessionState.EraseBool(Key);Directory.CreateDirectory(Path.Combine(Output,"Native"));File.WriteAllText(Path.Combine(Output,"Native/Lives101.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(ok?0:1);
        }
    }
}
#endif
