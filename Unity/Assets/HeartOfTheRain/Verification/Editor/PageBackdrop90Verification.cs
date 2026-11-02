#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Journey;
using HeartOfTheRain.App.Leaderboard;
using HeartOfTheRain.App.Teams;
using HeartOfTheRain.App.Shop;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.AccountDesign;
using HeartOfTheRain.App.GameplayLoading;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using UnityEngine.EventSystems;

namespace HeartOfTheRain.Verification
{
    // Explicit native UGUI fixtures. Production Build/Render and layout builders
    // run without Start, ordinary services, PlayerPrefs writes or a game attempt.
    public static class PageBackdrop90Verification
    {
        const BindingFlags Fields=BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.Public;
        [Serializable] sealed class SurfaceRow {public string name,kind,scope;public int width,height,state,decorations,controls;public float scale;public Rect safe;public bool passed;}
        [Serializable] sealed class InventoryRow {public string family,status,scope;}
        [Serializable] sealed class Report {
            public string status,utc,unity,scope="Pinned Unity 2022.3.62f3 native Editor. Actual production page Build/Render/layout primitives under explicit native canvas/camera framebuffer mappings and injected inset transforms. Initial Overlay Build is checked before an external canvas update. Masking/ordering negative controls are actual GPU readback. Fixtures do not override Android Screen.safeArea, drive input, read/write ordinary profiles, invoke HTTP/providers, measure timing or certify physical rendering. Source-only inventory entries are explicitly separate.";
            public int checks,cases,oldBandPixels,newBandPixels,maskedControlLeaks,modalBandPixels,homeDrawerBandPixels,hudLossBandPixels;
            public List<string> failures=new List<string>(),errors=new List<string>(),captures=new List<string>();
            public List<SurfaceRow> surfaces=new List<SurfaceRow>();public List<InventoryRow> inventory=new List<InventoryRow>();
        }
        struct Geometry {public string name;public int width,height;public float scale;public Rect safe;public Geometry(string n,int w,int h,float q,Rect s){name=n;width=w;height=h;scale=q;safe=s;}}
        sealed class Memory:ISettingsStore {readonly Dictionary<string,int> values=new Dictionary<string,int>();public int Read(string k,int f)=>values.TryGetValue(k,out int v)?v:f;public void Write(string k,int v){values[k]=v;}public void Flush(){}}
        static readonly Geometry[] Cases={
            new Geometry("Phone_no_insets",720,1600,720f/393,new Rect(0,0,720,1600)),
            new Geometry("Realme_top64",720,1600,720f/393,new Rect(0,0,720,1536)),
            new Geometry("Phone_top_bottom",1080,2400,1080f/393,new Rect(0,96,1080,2200)),
            new Geometry("Phone_asymmetric",1080,2400,2.5f,new Rect(31,82,1027,2211)),
            new Geometry("Compact_portrait",320,568,1,new Rect(0,20,320,524)),
            new Geometry("Tablet_asymmetric",1536,2048,2,new Rect(36,74,1472,1873))};
        static readonly string[] Families={"Journey","Leaderboard","Teams","Shop","OnlineTeams","OnlinePlayers","FirstStart","AppSettings"};
        static Report report;static string output;static GameObject owner;static HomePage home;static FirstStartAssets firstAssets;
        static ShopAssets shopAssets;static TeamsAssets teamAssets;static LeaderboardAssets rankAssets;static JourneyAssets journeyAssets;static AppSettingsAssets settingsAssets;
        static void Check(bool ok,string reason){report.checks++;if(!ok)report.failures.Add(reason);}
        static void Section(string name,Action action){try{action();}catch(Exception e){report.failures.Add(name+": "+e);}}
        static void Logged(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(message+"\n"+stack);}
        static object Field(object target,string name)=>target.GetType().GetField(name,Fields)?.GetValue(target);
        static T Field<T>(object target,string name)=>(T)Field(target,name);
        static void Set(object target,string name,object value){var field=target.GetType().GetField(name,Fields);if(field==null)throw new MissingFieldException(target.GetType().Name,name);field.SetValue(target,value);}
        static void Invoke(object target,string name,params object[] values)=>target.GetType().GetMethod(name,Fields).Invoke(target,values);
        static T Asset<T>(string path)where T:UnityEngine.Object {var value=AssetDatabase.LoadAssetAtPath<T>(path);if(!value)throw new InvalidOperationException("Missing approved binding: "+path);return value;}
        public static void Run(){
            output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_PAGE_BACKDROP90_OUT")??"../Verification/Evidence/PageBackdrop90/Native");Directory.CreateDirectory(output);
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};int locale=GameLocale.Current;Application.logMessageReceived+=Logged;
            try {
                Check(Application.unityVersion=="2022.3.62f3","Pinned engine");Check(!Application.isPlaying,"Separate Editor fixture, no ordinary Play Mode");
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);GameLocale.Select(4);
                firstAssets=Asset<FirstStartAssets>("Assets/HeartOfTheRain/App/FirstStart/FirstStartAssets.asset");settingsAssets=firstAssets.shared;shopAssets=settingsAssets.shop;teamAssets=shopAssets.teams;rankAssets=teamAssets.leaderboard;journeyAssets=rankAssets.journey;
                owner=new GameObject("PageBackdrop90 disposable native owner");home=owner.AddComponent<HomePage>();Set(home,"assets",journeyAssets.home);home.State.reduceMotion=true;
                foreach(string family in Families){int before=report.failures.Count;Section(family+" initial Overlay",()=>InitialOverlay(family));foreach(var c in Cases)for(int state=0;state<2;state++)Section(family+" "+c.name+" state"+state,()=>ActualPage(family,c,state));report.inventory.Add(new InventoryRow{family=family,status=before==report.failures.Count?"PASS_NATIVE_ACTUAL_UGUI":"FAIL_NATIVE_ACTUAL_UGUI",scope="Actual production Build/Render, actual layout builders, explicit native canvas geometry; isolated local/connected view fixtures, no services."});}
                Section("Masking/ordering pixel negative controls",PixelControls);
                Section("Home Events drawer and actual HUD loss dimmers",AdditionalDimmers);
                Section("Unaffected production backdrop construction",Unaffected);
                Section("Launch/gameplay/celebration source inventory",SourceInventory);
            }catch(Exception error){report.failures.Add(error.ToString());}
            finally {if(owner)UnityEngine.Object.DestroyImmediate(owner);GameLocale.Select(locale);Application.logMessageReceived-=Logged;report.status=report.failures.Count==0&&report.errors.Count==0?"PASS_NATIVE_PAGE_BACKDROP90":"FAIL_NATIVE_PAGE_BACKDROP90";File.WriteAllText(Path.Combine(output,"Report.json"),JsonUtility.ToJson(report,true));}
            EditorApplication.Exit(report.status=="PASS_NATIVE_PAGE_BACKDROP90"?0:1);
        }
        static MonoBehaviour Page(string family,GameObject node){
            MonoBehaviour page;
            switch(family){
                case "Journey":page=node.AddComponent<JourneyPage>();Set(page,"assets",journeyAssets);break;
                case "Leaderboard":page=node.AddComponent<LeaderboardPage>();Set(page,"assets",rankAssets);break;
                case "Teams":page=node.AddComponent<TeamsPage>();Set(page,"assets",teamAssets);break;
                case "Shop":page=node.AddComponent<ShopPage>();Set(page,"assets",shopAssets);break;
                case "OnlineTeams":page=node.AddComponent<OnlineTeamsPage82>();Set(page,"assets",teamAssets);break;
                case "FirstStart":page=node.AddComponent<FirstStartPage>();Set(page,"assets",firstAssets);break;
                case "AppSettings":page=node.AddComponent<AppSettingsPage>();Set(page,"assets",settingsAssets);break;
                default:throw new ArgumentException(family);
            }
            Set(page,"home",home);Invoke(page,"Build");return page;
        }
        static object Frame(string family,float width,float height,int state){
            switch(family){
                case "Journey":var j=new JourneySession(JsonUtility.FromJson<JourneyCatalog>(journeyAssets.catalog.text));if(state==1)j.Open(1);return JourneyLayout.Build(width,height,j);
                case "Leaderboard":var r=new LeaderboardSession(JsonUtility.FromJson<LeaderboardSnapshot>(rankAssets.demoData.text));r.SetRegion("");if(state==1)r.OpenRegion();return LeaderboardLayout.Build(width,height,r);
                case "Teams":var t=new TeamsSession(JsonUtility.FromJson<TeamsSnapshot>(teamAssets.demoData.text));if(state==1)t.BeginCompose();return TeamsLayout.Build(width,height,t);
                case "Shop":var s=new ShopSession(JsonUtility.FromJson<ShopCatalog>(shopAssets.catalog.text));if(state==1)s.Open(s.Specials.First().id);return ShopLayout.Build(width,height,s,1350);
                case "OnlineTeams":return OnlineTeamsLayout82.Build(width,height,new OnlineTeamsView82{connected=true,tab=2,regionCode="",modal=state==1?"country":""});
                case "OnlinePlayers":return OnlinePlayersLayout82.Build(width,height,new OnlinePlayersView82{connected=true,ownProfileLoaded=true,tab=1,modal=state==1?"country":""});
                case "FirstStart":var f=new FirstStartSession(new Memory(),firstAssets.lessons.Select(a=>JsonUtility.FromJson<LevelData>(a.text)).ToArray());return FirstStartLayout.Build(width,height,f,"The village well",true,state==1);
                case "AppSettings":var a=new AppSettingsSession(new Memory(),JsonUtility.FromJson<AppSettingsLinks>(settingsAssets.destinations.text));a.Open(new int[4],new int[4]);if(state==1)a.Navigate("language");return AppSettingsLayout.Build(width,height,a);
                default:throw new ArgumentException(family);
            }
        }
        static float Number(object target,string name,float fallback=0){var v=Field(target,name);return v==null?fallback:Convert.ToSingle(v);}
        static HomeFrame Block(object frame,string field)=>Field(frame,field)as HomeFrame;
        static Dictionary<string,RectTransform> Elements(object renderer)=>Field<Dictionary<string,RectTransform>>(renderer,"nodes");
        static void ConfigureCanvas(Canvas canvas,Geometry c){canvas.renderMode=RenderMode.WorldSpace;canvas.scaleFactor=c.scale;var scaler=canvas.GetComponent<CanvasScaler>();if(scaler)scaler.enabled=false;var root=(RectTransform)canvas.transform;root.anchorMin=root.anchorMax=root.pivot=Vector2.one*.5f;root.localPosition=Vector3.zero;root.localScale=Vector3.one;root.sizeDelta=new Vector2(c.width/c.scale,c.height/c.scale);}
        static void LayoutParents(object page,object frame,Geometry c){
            float w=Number(frame,"width"),h=Number(frame,"height");var safe=Field<RectTransform>(page,"safe");Place(safe,c.safe.x/c.scale,(c.height-c.safe.yMax)/c.scale,w,h);
            foreach(string name in new[]{"chrome","overlay"}){var root=Field(page,name)as RectTransform;if(root)Place(root,0,0,w,h);}
            float vx=Number(frame,"viewportX"),vy=Number(frame,"viewportY"),vw=Number(frame,"viewportWidth",w),vh=Number(frame,"viewportHeight",h);
            var viewport=Field(page,"viewport")as RectTransform;if(viewport)Place(viewport,vx,vy,vw,vh);
            var content=Field(page,"content")as RectTransform;if(content){var model=Block(frame,"content");Place(content,0,0,model?.width??w,model?.height??h);}
        }
        static void RenderBlocks(object page,object frame){foreach(string name in new[]{"chrome","content","overlay"}){var model=Block(frame,name);var root=Field(page,name)as RectTransform;if(model!=null&&root)Invoke(page,"Render",model,root);}}
        static void InitialOverlay(string family){
            var node=new GameObject("Initial Overlay "+family);object page=null;Canvas canvas=null;
            try{
                var c=new Geometry("nativeEditorScreen",Screen.width,Screen.height,1,new Rect(0,0,Screen.width,Screen.height));var frame=Frame(family,Mathf.Max(320,Screen.width),Mathf.Max(568,Screen.height),0);
                if(family=="OnlinePlayers"){
                    var surface=new OnlineSocialSurface82(node.transform,rankAssets.Find,journeyAssets.home.regularFont,journeyAssets.home.boldFont,_=>{},_=>"",(_,__)=>{});page=surface;canvas=surface.canvas;
                    var native=(OnlineTeamsFrame82)frame;surface.Apply(native.width,native.height,1,c.safe,c.height,native.viewportY,native.viewportHeight,native.chrome,native.content,native.overlay,false,true);
                }else{page=Page(family,node);canvas=Field<Canvas>(page,"canvas");LayoutParents(page,frame,c);RenderBlocks(page,frame);}
                // No externally forced layout occurred between Build and Render.
                Canvas.ForceUpdateCanvases();InspectDecorations(Elements(page),canvas,family+" initial Overlay",false);
            }finally{UnityEngine.Object.DestroyImmediate(node);}
        }
        static void ActualPage(string family,Geometry c,int state){
            var node=new GameObject(family+" "+c.name+" state"+state);object page=null;Canvas canvas=null;var row=new SurfaceRow{name=family,kind="actual-production-render-explicit-native-canvas",scope=c.name,width=c.width,height=c.height,scale=c.scale,safe=c.safe,state=state};int before=report.failures.Count;bool completed=false;
            try{
                object frame=Frame(family,c.safe.width/c.scale,c.safe.height/c.scale,state);
                if(family=="OnlinePlayers"){
                    var surface=new OnlineSocialSurface82(node.transform,rankAssets.Find,journeyAssets.home.regularFont,journeyAssets.home.boldFont,_=>{},_=>"",(_,__)=>{});page=surface;canvas=surface.canvas;ConfigureCanvas(canvas,c);
                    var f=(OnlineTeamsFrame82)frame;surface.Apply(f.width,f.height,c.scale,c.safe,c.height,f.viewportY,f.viewportHeight,f.chrome,f.content,f.overlay,state==1,true,false);
                }else{page=Page(family,node);canvas=Field<Canvas>(page,"canvas");ConfigureCanvas(canvas,c);LayoutParents(page,frame,c);RenderBlocks(page,frame);}
                Canvas.ForceUpdateCanvases();var nodes=Elements(page);row.decorations=InspectDecorations(nodes,canvas,family+" "+c.name+" state"+state,true);
                foreach(string blockName in new[]{"chrome","content","overlay"}){var block=Block(frame,blockName);if(block==null)continue;foreach(var element in block.elements.Where(e=>!string.IsNullOrEmpty(e.action))){RectTransform control;if(!nodes.TryGetValue(element.id,out control)||!control.GetComponent<Button>())continue;row.controls++;Check(Vector2.Distance(control.anchoredPosition,new Vector2(element.x,-element.y))<.02f&&Vector2.Distance(control.sizeDelta,new Vector2(element.width,element.height))<.02f,family+" "+c.name+": control layout changed "+element.id);var graphic=control.GetComponent<MaskableGraphic>();Check(!graphic||graphic.maskable,family+": interactive control lost masking "+element.id);}}
                Check(row.controls>0,family+" actual controls exist");
                if(c.name=="Realme_top64"&&state==0)Capture(canvas,c,family+"_Native_Top64.png");completed=true;
            }finally{row.passed=completed&&before==report.failures.Count;report.surfaces.Add(row);report.cases++;UnityEngine.Object.DestroyImmediate(node);}
        }
        static bool Decoration(string id)=>new[]{"background","backdrop","online-teams-background","online-players-background","scene-art","scene-shade","language-shade","modal-shade","country-shade","online-modal-shade","online-player-modal-shade","ad-shade"}.Contains(id);
        static int InspectDecorations(Dictionary<string,RectTransform> nodes,Canvas canvas,string scope,bool controls){
            int count=0;foreach(var pair in nodes.Where(p=>Decoration(p.Key))){var g=pair.Value.GetComponent<MaskableGraphic>();Check(g,scope+": decorative graphic exists "+pair.Key);if(!g)continue;count++;Check(!g.maskable&&!g.raycastTarget,scope+": backdrop escapes mask without intercepting controls "+pair.Key);Check(Covers(pair.Value,(RectTransform)canvas.transform),scope+": backdrop covers all native canvas corners "+pair.Key);}
            Check(count>0,scope+": at least one actual backdrop path checked");
            RectTransform top;if(nodes.TryGetValue("top-bar",out top)){var a=Bounds((RectTransform)canvas.transform,top);var outer=((RectTransform)canvas.transform).rect;Check(Math.Abs(a.xMin-outer.xMin)<.05f&&Math.Abs(a.xMax-outer.xMax)<.05f&&Math.Abs(a.yMax-outer.yMax)<.05f,scope+": Journey header continues through top/side insets");Check(!top.GetComponent<MaskableGraphic>().maskable,scope+": Journey top background escapes safe mask");}
            return count;
        }
        static Rect Bounds(RectTransform root,RectTransform target){var corners=new Vector3[4];target.GetWorldCorners(corners);Vector2 lo=Vector2.one*float.MaxValue,hi=Vector2.one*float.MinValue;foreach(var corner in corners){Vector2 p=root.InverseTransformPoint(corner);lo=Vector2.Min(lo,p);hi=Vector2.Max(hi,p);}return UnityEngine.Rect.MinMaxRect(lo.x,lo.y,hi.x,hi.y);}
        static bool Covers(RectTransform graphic,RectTransform root){var b=Bounds(root,graphic);var r=root.rect;return b.xMin<=r.xMin+.1f&&b.xMax>=r.xMax-.1f&&b.yMin<=r.yMin+.1f&&b.yMax>=r.yMax-.1f;}
        static RectTransform Rect(string name,Transform parent){var r=new GameObject(name,typeof(RectTransform)).GetComponent<RectTransform>();r.SetParent(parent,false);return r;}
        static void Place(RectTransform r,float x,float y,float w,float h){r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);}
        static void Stretch(RectTransform r){r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=r.offsetMax=Vector2.zero;}
        static Image Image(string name,Transform parent,Color color){var image=Rect(name,parent).gameObject.AddComponent<Image>();image.color=color;return image;}
        static Color32[] Capture(Canvas canvas,Geometry c,string file){
            var cameraObject=new GameObject("PageBackdrop90 explicit native framebuffer camera");var camera=cameraObject.AddComponent<Camera>();camera.orthographic=true;camera.orthographicSize=c.height/(2*c.scale);camera.aspect=c.width/(float)c.height;camera.transform.position=new Vector3(0,0,-10);camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.red;camera.nearClipPlane=.1f;camera.farClipPlane=100;
            var target=new RenderTexture(c.width,c.height,24,RenderTextureFormat.ARGB32);var previous=RenderTexture.active;Texture2D pixels=null;var mode=canvas.renderMode;var old=canvas.worldCamera;
            try{target.Create();camera.targetTexture=target;canvas.worldCamera=camera;Canvas.ForceUpdateCanvases();camera.Render();camera.Render();RenderTexture.active=target;pixels=new Texture2D(c.width,c.height,TextureFormat.RGB24,false);pixels.ReadPixels(new Rect(0,0,c.width,c.height),0,0);pixels.Apply();var result=pixels.GetPixels32();File.WriteAllBytes(Path.Combine(output,file),pixels.EncodeToPNG());report.captures.Add(file);return result;}
            finally{canvas.renderMode=mode;canvas.worldCamera=old;camera.targetTexture=null;RenderTexture.active=previous;if(pixels)UnityEngine.Object.DestroyImmediate(pixels);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(cameraObject);}
        }
        static void PixelControls(){
            var node=new GameObject("Native RectMask2D regression controls");try{
                var root=Rect("Native canvas",node.transform);var canvas=root.gameObject.AddComponent<Canvas>();var c=new Geometry("pixel",360,800,1,new Rect(24,38,317,698));ConfigureCanvas(canvas,c);
                var safe=Rect("Safe mask",root);Place(safe,24,64,317,698);safe.gameObject.AddComponent<RectMask2D>();var group=safe.gameObject.AddComponent<CanvasGroup>();group.alpha=1;
                var backdrop=Image("Decorative blue backdrop",safe,new Color(.1f,.45f,.75f,1));Place(backdrop.rectTransform,-24,-64,360,800);backdrop.raycastTarget=false;
                var clipped=Image("Control that must remain clipped",safe,Color.magenta);Place(clipped.rectTransform,30,-54,40,30);clipped.gameObject.AddComponent<Button>();
                var inside=Image("Safe control",safe,Color.green);Place(inside.rectTransform,30,30,40,30);inside.gameObject.AddComponent<Button>();
                Canvas.ForceUpdateCanvases();var old=Capture(canvas,c,"Mask_Old_Clipped_Top.png");
                var parent=backdrop.transform.parent;int sibling=backdrop.transform.GetSiblingIndex();var control=clipped.rectTransform.anchoredPosition;var insidePos=inside.rectTransform.anchoredPosition;
                PageBackdrop90.Fill(backdrop,canvas);var current=Capture(canvas,c,"Mask_New_Full_Top.png");
                Check(backdrop.transform.parent==parent&&backdrop.transform.GetSiblingIndex()==sibling,"Fill preserves decoration draw parent/order");Check(group.alpha==1&&clipped.rectTransform.anchoredPosition==control&&inside.rectTransform.anchoredPosition==insidePos,"Fill preserves ancestor fade and sibling controls");
                for(int y=750;y<790;y++)for(int x=40;x<320;x++){int i=y*360+x;var a=old[i];var b=current[i];if(a.r>200&&a.g<30&&a.b<30)report.oldBandPixels++;if(b.b>b.r+40&&b.b>b.g)report.newBandPixels++;if(b.r>150&&b.b>150&&b.g<40)report.maskedControlLeaks++;}
                Check(report.oldBandPixels>10000,"Negative control reproduces clipped top band before repair");Check(report.newBandPixels>10000,"Unmasked decorative graphic really paints outside RectMask2D");Check(report.maskedControlLeaks==0,"Interactive sibling remains clipped outside safe area");
                var shade=Image("Later modal shade",safe,new Color(0,0,0,.5f));Place(shade.rectTransform,0,0,317,698);PageBackdrop90.Fill(shade,canvas);var panel=Image("Dialog above dimmer",safe,Color.white);Place(panel.rectTransform,100,150,100,100);
                var modal=Capture(canvas,c,"Mask_Modal_Order_Top.png");for(int y=750;y<790;y++)for(int x=40;x<320;x++){var a=current[y*360+x];var b=modal[y*360+x];if(b.b<a.b-20&&b.b>20)report.modalBandPixels++;}
                Check(report.modalBandPixels>10000,"Modal scrim shades the newly extended top band with original draw order");var centre=modal[(800-64-200)*360+(24+150)];Check(centre.r>220&&centre.g>220&&centre.b>220,"Modal panel stays above its scrim");
                float bottom=Bounds(root,inside.rectTransform).yMin;int order=inside.transform.GetSiblingIndex();PageBackdrop90.ExtendTop(inside,canvas);var header=Bounds(root,inside.rectTransform);Check(Math.Abs(header.yMin-bottom)<.02f&&inside.transform.GetSiblingIndex()==order,"ExtendTop preserves original bottom edge and order");Check(Math.Abs(header.xMin-root.rect.xMin)<.02f&&Math.Abs(header.xMax-root.rect.xMax)<.02f&&Math.Abs(header.yMax-root.rect.yMax)<.02f,"ExtendTop reaches top and asymmetric side edges");
            }finally{UnityEngine.Object.DestroyImmediate(node);}
        }
        sealed class ControlPose {
            public RectTransform rect;public Transform parent;public Vector2 position,size;
        }
        static List<ControlPose> ControlPoses(Canvas canvas)=>canvas.GetComponentsInChildren<Button>(true).Select(button=>new ControlPose{rect=(RectTransform)button.transform,parent=button.transform.parent,position=((RectTransform)button.transform).anchoredPosition,size=((RectTransform)button.transform).sizeDelta}).ToList();
        static void CheckControlPoses(List<ControlPose> poses,string scope){foreach(var pose in poses)Check(pose.rect&&pose.rect.parent==pose.parent&&Vector2.Distance(pose.rect.anchoredPosition,pose.position)<.02f&&Vector2.Distance(pose.rect.sizeDelta,pose.size)<.02f,scope+": decorative fill preserves control parent/position/size "+pose.rect.name);}
        static int DarkenedBand(Color32[] before,Color32[] after,int width,int height,int top){int count=0;for(int y=height-top+8;y<height-8;y++)for(int x=32;x<width-32;x++){int i=y*width+x;var a=before[i];var b=after[i];if(a.r+a.g+a.b>b.r+b.g+b.b+40)count++;}return count;}
        static void AdditionalDimmers(){
            int failures=report.failures.Count;foreach(var c in Cases)Section("Home Events drawer "+c.name,()=>HomeDrawer(c));report.inventory.Add(new InventoryRow{family="HomeEventsDrawer",status=failures==report.failures.Count?"PASS_NATIVE_ACTUAL_UGUI":"FAIL_NATIVE_ACTUAL_UGUI",scope="Actual Home prefab Build with drawer already open; initial production dimmer inspection, explicit inset/canvas remapping and actual native top64 pixel dimming. No requests or ordinary profile/preferences."});
            failures=report.failures.Count;foreach(var c in Cases)Section("Actual HUD loss "+c.name,()=>HudLoss(c));report.inventory.Add(new InventoryRow{family="HUDLoss",status=failures==report.failures.Count?"PASS_NATIVE_ACTUAL_UGUI":"FAIL_NATIVE_ACTUAL_UGUI",scope="Actual GameplayHUD.Build/ShowLoss, isolated presentation only, disabled sound and uninvoked acknowledgement. Native full-display dimmer/unchanged safe parent and controls plus top64 readback over diagnostic backdrop. No gameplay/model attempt or loss settlement."});
        }
        static void HomeDrawer(Geometry c){
            GameObject instance=null;HomePage page=null;bool completed=false;int failed=report.failures.Count;var row=new SurfaceRow{name="HomeEventsDrawer",kind="actual-home-build-and-injected-safe-geometry",scope=c.name,width=c.width,height=c.height,scale=c.scale,safe=c.safe};
            try{
                var prefab=Asset<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab");instance=(GameObject)PrefabUtility.InstantiatePrefab(prefab);page=instance.GetComponent<HomePage>();var profile=instance.AddComponent<ProfilePage>();Set(profile,"home",page);
                // Set the initial presentation state before Build. Calling ShowEvents
                // on an existing tree would use normal delayed runtime destruction
                // in this Edit Mode fixture; no such command is dispatched here.
                Set(page,"drawer",true);page.State.reduceMotion=true;page.Build();Canvas.ForceUpdateCanvases();
                var canvas=Field<Canvas>(page,"canvas");var nodes=Field<Dictionary<string,RectTransform>>(page,"nodes");var safe=Field<RectTransform>(page,"safeViewport");var art=Field<RawImage>(page,"background");var shade=nodes["drawer-shade"].GetComponent<Image>();
                Check(!shade.maskable&&!shade.raycastTarget&&Covers(shade.rectTransform,(RectTransform)canvas.transform),"Actual first Home Build paints its drawer shade to the complete native canvas");
                Check(shade.transform.parent==nodes["drawer-scrim"]&&safe.GetComponent<RectMask2D>(),"Drawer retains its original interaction/safe-mask hierarchy");
                var controls=ControlPoses(canvas);var originalParent=shade.transform.parent;int sibling=shade.transform.GetSiblingIndex();ConfigureCanvas(canvas,c);Place(safe,c.safe.x/c.scale,(c.height-c.safe.yMax)/c.scale,c.safe.width/c.scale,c.safe.height/c.scale);
                // The production call above proves integration. This explicit
                // native remapping exercises the same helper after a safe change;
                // it is not an Android Screen.safeArea override or Home reflow.
                PageBackdrop90.Fill(art,canvas);PageBackdrop90.Fill(shade,canvas);Canvas.ForceUpdateCanvases();
                Check(Covers(shade.rectTransform,(RectTransform)canvas.transform)&&Covers(art.rectTransform,(RectTransform)canvas.transform),"Home artwork and drawer dimmer cover explicit inset canvas "+c.name);
                Check(shade.transform.parent==originalParent&&shade.transform.GetSiblingIndex()==sibling,"Home dimmer keeps draw parent/order "+c.name);CheckControlPoses(controls,"Home drawer "+c.name);row.controls=controls.Count;row.decorations=2;
                if(c.name=="Realme_top64"){
                    shade.enabled=false;var before=Capture(canvas,c,"Home_Drawer_Dimmer_Disabled_Native.png");shade.enabled=true;var after=Capture(canvas,c,"Home_Drawer_Full_Top64_Native.png");report.homeDrawerBandPixels=DarkenedBand(before,after,c.width,c.height,64);Check(report.homeDrawerBandPixels>(c.width-64)*48/2,"Actual Home drawer shades the injected64px upper band instead of exposing bright artwork");
                }
                completed=true;
            }finally{
                row.passed=completed&&failed==report.failures.Count;report.surfaces.Add(row);report.cases++;
                if(page){var slices=Field<HomeHeaderSprites>(page,"headerSprites");if(slices!=null){foreach(var sprite in new[]{slices.Panel,slices.DefaultAvatar,slices.Connector})if(sprite)UnityEngine.Object.DestroyImmediate(sprite);Set(page,"headerSprites",null);}var events=Field<EventSystem>(page,"ownedEvents");Set(page,"ownedEvents",null);if(events)UnityEngine.Object.DestroyImmediate(events.gameObject);}
                if(instance)UnityEngine.Object.DestroyImmediate(instance);
            }
        }
        static void HudLoss(Geometry input){
            var node=new GameObject("Actual HUD loss backdrop "+input.name);bool completed=false,acknowledged=false;int failed=report.failures.Count;var c=input;c.scale=c.safe.width/720f;
            var row=new SurfaceRow{name="HUDLoss",kind="actual-gameplay-hud-build-showloss",scope=c.name,width=c.width,height=c.height,scale=c.scale,safe=c.safe};
            try{
                var hud=node.AddComponent<GameplayHUD>();hud.assets=firstAssets.Gameplay;hud.feedback=node.AddComponent<GameplayFeedback>();hud.feedback.soundEnabled=false;hud.Build();
                var canvas=Field<Canvas>(hud,"canvas");ConfigureCanvas(canvas,c);var safe=Field<RectTransform>(hud,"safe");float h=c.safe.height/c.scale;Place(safe,c.safe.x/c.scale,(c.height-c.safe.yMax)/c.scale,720,h);Set(hud,"<Height>k__BackingField",h);
                var diagnostic=Image("Diagnostic gameplay background",canvas.transform,new Color(.1f,.45f,.75f,1));Stretch(diagnostic.rectTransform);diagnostic.rectTransform.SetAsFirstSibling();diagnostic.raycastTarget=false;
                hud.ShowLoss("No moves left",()=>acknowledged=true);Canvas.ForceUpdateCanvases();var modal=Field<RectTransform>(hud,"modal");var shade=modal.Find("Full display modal shade").GetComponent<Image>();var panel=(RectTransform)modal.Find("Dialog");
                Check(hud.LossPending&&hud.IsBlocking&&!acknowledged,"Actual HUD loss remains pending without invoking settlement "+c.name);
                Check(modal.parent==safe&&Vector2.Distance(modal.sizeDelta,new Vector2(720,h))<.02f&&modal.anchoredPosition==Vector2.zero,"HUD modal keeps the exact safe-area control parent dimensions "+c.name);
                var shield=modal.GetComponent<Image>();Check(shield&&shield.color.a==0&&shield.raycastTarget,"HUD modal retains a clear input shield rather than resizing its control parent "+c.name);
                Check(!shade.maskable&&!shade.raycastTarget&&Covers(shade.rectTransform,(RectTransform)canvas.transform),"Actual HUD ShowLoss dimmer covers complete native canvas "+c.name);
                Check(shade.transform.parent==modal&&shade.transform.GetSiblingIndex()<panel.GetSiblingIndex(),"HUD shade remains below the actual Dialog panel "+c.name);
                Check(Vector2.Distance(panel.anchoredPosition,new Vector2(80,-(h-584)/2))<.02f&&Vector2.Distance(panel.sizeDelta,new Vector2(560,584))<.02f,"HUD loss panel keeps approved safe-area coordinates and dimensions "+c.name);
                var button=panel.GetComponentsInChildren<Button>().Single();var buttonRect=(RectTransform)button.transform;Check(Vector2.Distance(buttonRect.anchoredPosition,new Vector2(64,-446))<.02f&&Vector2.Distance(buttonRect.sizeDelta,new Vector2(432,94))<.02f,"HUD loss acknowledgement retains its approved local touch bounds "+c.name);
                var poses=ControlPoses(canvas);PageBackdrop90.Fill(shade,canvas);CheckControlPoses(poses,"HUD loss "+c.name);row.controls=poses.Count;row.decorations=1;
                if(c.name=="Realme_top64"){
                    shade.enabled=false;var before=Capture(canvas,c,"HUD_Loss_Dimmer_Disabled_Native.png");shade.enabled=true;var after=Capture(canvas,c,"HUD_Loss_Full_Top64_Native.png");report.hudLossBandPixels=DarkenedBand(before,after,c.width,c.height,64);Check(report.hudLossBandPixels>(c.width-64)*48*9/10,"Actual HUD loss dimmer shades the64px upper band while its safe panel/button stay fixed");
                }
                Check(!acknowledged,"Native HUD loss fixture never acknowledged or settled an attempt");completed=true;
            }finally{row.passed=completed&&failed==report.failures.Count;report.surfaces.Add(row);report.cases++;UnityEngine.Object.DestroyImmediate(node);}
        }
        static void Unaffected(){
            foreach(Type type in new[]{typeof(DailyGiftPage),typeof(WellworksPage),typeof(RainCupPage),typeof(AccountModal),typeof(GameplayLoadingPage),typeof(HeartOfTheRain.App.NoMoves.NoMovesPage)}){
                var node=new GameObject("Actual unchanged backdrop "+type.Name);int before=report.failures.Count;
                try{var component=node.AddComponent(type);if(type==typeof(AccountModal))((AccountModal)component).Configure(home,AccountDesignAssets.Load());if(type==typeof(GameplayLoadingPage)){var loading=(GameplayLoadingPage)component;loading.home=home;loading.font=journeyAssets.home.boldFont;}
                    Invoke(component,"Build");var canvas=Field<Canvas>(component,"canvas");var c=Cases[1];ConfigureCanvas(canvas,c);Canvas.ForceUpdateCanvases();var graphics=canvas.GetComponentsInChildren<MaskableGraphic>(true).Where(g=>g.transform.parent==canvas.transform&&g.rectTransform.anchorMin==Vector2.zero&&g.rectTransform.anchorMax==Vector2.one).ToArray();
                    Check(graphics.Length>0,type.Name+": actual root-level full-screen backdrop/shield exists");foreach(var g in graphics)Check(Covers(g.rectTransform,(RectTransform)canvas.transform),type.Name+": full-screen graphic remains independent of safe root: "+g.name);
                    report.inventory.Add(new InventoryRow{family=type.Name,status=before==report.failures.Count?"PASS_NATIVE_ACTUAL_BUILD_BACKDROP":"FAIL_NATIVE_ACTUAL_BUILD_BACKDROP",scope="Actual production Build only; native full-canvas artwork/shield bounds, no content/service/error-state transitions."});
                }finally{UnityEngine.Object.DestroyImmediate(node);}
            }
        }
        static void SourceInventory(){
            Audit("Home","Assets/HeartOfTheRain/App/Home/Runtime/HomePage.cs",new[]{"background=","canvasRect","Cover"});
            Audit("Profile","Assets/HeartOfTheRain/App/Profile/Runtime/ProfilePage.cs",new[]{"Profile backdrop","Stretch(bg)","Profile Safe Area"});
            Audit("PreLevel","Assets/HeartOfTheRain/App/PreLevel/Runtime/PreLevelModal.cs",new[]{"Modal shade","dim.anchorMax=Vector2.one","Safe area"});
            Audit("GameplaySettings","Assets/HeartOfTheRain/App/Settings/Runtime/GameplaySettingsModal.cs",new[]{"Modal shade","dim.anchorMax=Vector2.one","Safe area"});
            Audit("EndLevel","Assets/HeartOfTheRain/App/EndLevel/Runtime/EndLevelModal.cs",new[]{"Modal shade","dim.anchorMax=Vector2.one","Safe area"});
            Audit("Launch","Assets/HeartOfTheRain/App/Launch/Runtime/LaunchPage.cs",new[]{"Launch matte and input shield","matte.anchorMax=Vector2.one","LaunchLayout.Build(Screen.width,Screen.height,safe)"});
            Audit("Gameplay","Assets/HeartOfTheRain/M47/Runtime/GameplayScreen.cs",new[]{"FullDisplayBoardView"});
            Audit("VictoryCelebration","Assets/HeartOfTheRain/App/Celebrations/Runtime/VictoryCelebrationPlayer.cs",new[]{"Tap to skip animation","Stretch(shade.rectTransform)","Safe area"});
            Audit("ChapterCelebration","Assets/HeartOfTheRain/App/Celebrations/Runtime/ChapterCelebrationPlayer.cs",new[]{"Input shield","matte.anchorMax=Vector2.one","Safe area"});
            Audit("DailyGiftSaveError","Assets/HeartOfTheRain/App/Profile/Runtime/DailyGiftPage.cs",new[]{"backdrop.gameObject.SetActive(!view.error)","view.error?.74f:.439f","Stretch(dim)"});
            foreach(var c in Cases){var frame=HeartOfTheRain.App.Launch.LaunchLayout.Build(c.width,c.height,c.safe);Check(frame.art.width>0&&frame.art.height>0&&frame.uv.xMin>=0&&frame.uv.yMin>=0&&frame.uv.xMax<=1.0001f&&frame.uv.yMax<=1.0001f,"Launch artwork valid full-display contain/cover geometry "+c.name);Check(frame.logo.xMin>=c.safe.xMin-.1f&&frame.logo.xMax<=c.safe.xMax+.1f&&frame.logo.yMax<=c.safe.yMax+.1f,"Launch interactive/title content retains safe placement "+c.name);}
        }
        static void Audit(string family,string path,string[] tokens){var full=Path.GetFullPath(path);if(!File.Exists(full)){report.inventory.Add(new InventoryRow{family=family,status="NOT_RUN_SOURCE_PATH_MISSING",scope=path});Check(false,family+": source inventory path exists");return;}var source=File.ReadAllText(full);bool ok=true;foreach(string token in tokens){bool has=source.Contains(token);Check(has,family+": audited backdrop source invariant "+token);ok&=has;}report.inventory.Add(new InventoryRow{family=family,status=ok?"PASS_SOURCE_INVARIANT_ONLY":"FAIL_SOURCE_INVARIANT",scope="Source-only full-display/safe-layout invariant, plus separate current Display88 native suite for Home/gameplay; not actual page-state rendering or device acceptance."});}
    }
}
#endif
