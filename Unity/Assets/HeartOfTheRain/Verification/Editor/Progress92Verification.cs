#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Teams;
using HeartOfTheRain.App.Localization;

namespace HeartOfTheRain.Verification
{
    // Empty-scene native Play Mode fixtures. No ordinary scene, service,
    // repository, backend, reward, click callback or saved profile is opened.
    [InitializeOnLoad] public static class Progress92Verification
    {
        const string Key="HOTR.Progress92.Native";
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.Public;
        static readonly Vector2Int[] Sizes={new Vector2Int(320,568),new Vector2Int(393,852),new Vector2Int(720,1600),new Vector2Int(768,1024)};
        static readonly string[] Families={"RainCup","Wellworks","ProfileStats","TeamRally","TeamLife","Home"};
        static readonly float[] Fractions={0,.02f,.1f,.5f,1};
        [Serializable] sealed class BarRow {
            public string family,type,scope;public int width,height,pixelWidth,pixelHeight,pixelCount,meshVertices;
            public float ratio,innerWidth,clipWidth,fillWidth,fillHeight,physicalHeight,sliceMultiplier,meshHeight;
            public bool preserveAspect,passed,zeroHidden;
        }
        [Serializable] sealed class Audit {public string family,kind,status,scope;}
        [Serializable] sealed class Report {
            public string utc,unity,status,scope="Pinned native Unity 2022.3.62f3 empty-scene Play Mode. Actual page Build/Render, real imported sprites, native UGUI meshes and GPU alpha readback at four real GameView framebuffer sizes. Explicit presentation snapshots include locked/full boundary and hypothetical tiny quota values; they do not invent live game rules. Inset tests translate the actual safe subtree and inspect invariant local geometry, without overriding Screen.safeArea. No Android/OS screenshot, physical input, ordinary profile/preferences writes, service/reward/account/backend, performance or release acceptance.";
            public int checks,cases,oldRainPixelHeight,newRainPixelHeight,oldProfilePixelCount,newProfilePixelCount;
            public bool ordinaryServicesConstructed=false,ordinaryProfileWrites=false;
            public List<string> failures=new List<string>(),errors=new List<string>(),captures=new List<string>();
            public List<BarRow> bars=new List<BarRow>();public List<Audit> audits=new List<Audit>();
        }
        sealed class Fixture {
            public GameObject owner;public HomePage home;public Canvas canvas;public RectTransform safe,track,clip;public Image fill;public float ratio,innerWidth,expectedHeight,minimumWidth,multiplier;public string scope;
        }
        sealed class Pixels {
            public Color32[] data;public int width,height,count,pixelWidth,pixelHeight;public float physicalHeight;public RectInt crop;
        }
        static Report report;static string output;static double began,next;static int index,sizeIndex=-1,oldLocale;static bool finishing;
        static PreLevelAssets pre;static FirstStartAssets first;static TeamsAssets teams;static GameObject homePrefab;
        static object Field(object owner,string name)=>owner.GetType().GetField(name,Private)?.GetValue(owner);
        static T Field<T>(object owner,string name)=>(T)Field(owner,name);
        static void Set(object owner,string name,object value){var f=owner.GetType().GetField(name,Private);if(f==null)throw new MissingFieldException(owner.GetType().Name,name);f.SetValue(owner,value);}
        static void Invoke(object owner,string name,params object[] args)=>owner.GetType().GetMethod(name,Private).Invoke(owner,args);
        static void Check(bool ok,string label){report.checks++;if(!ok)throw new InvalidOperationException(label);}
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static object Group(){var a=typeof(Editor).Assembly;var t=a.GetType("UnityEditor.GameViewSizes");var singleton=typeof(ScriptableSingleton<>).MakeGenericType(t).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);string group=EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":EditorUserBuildSettings.activeBuildTarget==BuildTarget.iOS?"iOS":"Standalone";return t.GetMethod("GetGroup").Invoke(singleton,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),group)});}
        static Progress92Verification(){
            if(!SessionState.GetBool(Key,false))return;
            output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_PROGRESS92_OUT")??"../Verification/Evidence/Progress92/Native");Directory.CreateDirectory(output);report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};began=EditorApplication.timeSinceStartup;oldLocale=GameLocale.Current;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;
        }
        public static void Run(){
            SessionState.SetBool(Key,true);var group=Group();var view=View();var property=view.GetType().GetProperty("selectedSizeIndex",Private);SessionState.SetInt(Key+".previous",(int)property.GetValue(view));int start=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);SessionState.SetInt(Key+".first",start);
            var a=typeof(Editor).Assembly;foreach(var s in Sizes){var size=Activator.CreateInstance(a.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),s.x,s.y,"HOTR Progress92"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{size});}
            property.SetValue(view,start);view.Repaint();EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.isPlaying=true;
        }
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(message+"\n"+stack);}
        static void Size(int number){View().GetType().GetProperty("selectedSizeIndex",Private).SetValue(View(),SessionState.GetInt(Key+".first",0)+number);View().Repaint();sizeIndex=number;next=EditorApplication.timeSinceStartup+.25;}
        static void Tick(){
            if(finishing)return;
            try{
                if(EditorApplication.timeSinceStartup-began>300)throw new TimeoutException("Progress92 native fixture deadline");
                if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup<next)return;
                if(!pre){Check(Application.unityVersion=="2022.3.62f3","Pinned engine");pre=AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");first=AssetDatabase.LoadAssetAtPath<FirstStartAssets>("Assets/HeartOfTheRain/App/FirstStart/FirstStartAssets.asset");teams=first.shared.shop.teams;homePrefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab");Check(pre&&first&&teams&&homePrefab,"Approved live asset bindings");GameLocale.Select(4);}
                int per=Families.Length*Fractions.Length;
                if(index>=Sizes.Length*per){Audits();Finish();return;}
                int wanted=index/per;if(sizeIndex!=wanted){Size(wanted);return;}if(Screen.width!=Sizes[wanted].x||Screen.height!=Sizes[wanted].y)return;
                string family=Families[index%per/Fractions.Length];int fraction=index%Fractions.Length;
                Case(family,fraction);index++;next=EditorApplication.timeSinceStartup+.02;
            }catch(Exception error){report.failures.Add(error.ToString());Finish();}
        }
        static HomePage Owner(GameObject root){var instance=UnityEngine.Object.Instantiate(homePrefab,root.transform);var home=instance.GetComponent<HomePage>();home.enabled=false;home.State.reduceMotion=true;return home;}
        static Dictionary<string,RectTransform> Nodes(object page)=>Field<Dictionary<string,RectTransform>>(page,"nodes");
        static Fixture Build(string family,int fraction){
            var f=new Fixture{owner=new GameObject("Isolated Progress92 "+family),ratio=Fractions[fraction]};f.home=Owner(f.owner);
            if(family=="RainCup"){
                var page=f.owner.AddComponent<RainCupPage>();page.enabled=false;page.Configure(f.home,pre,null);Invoke(page,"Build");
                var rules=JsonUtility.FromJson<RainCupRules>(Resources.Load<TextAsset>("HOTR_RainCup/Rules").text);int denominator=fraction==1?49:10,numerator=fraction==1?1:Mathf.RoundToInt(f.ratio*10);rules.unlockClears=denominator;f.ratio=numerator/(float)denominator;
                var view=new RainCupView{snapshot=new RainCupSnapshot{state="Locked",completed=numerator,development=true,rules=rules},avatarId="Dariya"};Set(page,"view",view);Invoke(page,"Render",false);var nodes=Nodes(page);
                f.canvas=Field<Canvas>(page,"canvas");f.safe=Field<RectTransform>(page,"safe");f.track=nodes["progress-track"];f.clip=nodes["progress-clip"];f.fill=nodes["fill"].GetComponent<Image>();f.innerWidth=f.track.rect.width-6;f.expectedHeight=10;f.minimumWidth=12;f.multiplier=8;
                Check(view.snapshot.completed==numerator&&view.snapshot.rules.unlockClears==denominator,"Rendering cannot change Rain Cup completion/threshold snapshot");f.scope="Actual RainCupPage.Build/Render; default1/10 uses approved10-clear rule. Verylow1/49 and locked/full are presentation boundary fixtures only.";
            }else if(family=="Wellworks"){
                var page=f.owner.AddComponent<WellworksPage>();page.enabled=false;page.Configure(f.home,pre,null);Invoke(page,"Build");var player=PlayerProfile.New(new[]{5,5,3,2});player.completed=Mathf.RoundToInt(f.ratio*50);f.ratio=player.completed/50f;var view=new WellworksView{player=player,schedule=JsonUtility.FromJson<WellworksSchedule>(Resources.Load<TextAsset>("HOTR_Wellworks/Schedule").text),enabled=true};Set(page,"view",view);Invoke(page,"Render");var nodes=Nodes(page);
                f.canvas=Field<Canvas>(page,"canvas");f.safe=Field<RectTransform>(page,"safe");f.track=nodes["progress-track"];f.clip=nodes["progress-clip"];f.fill=nodes["fill"].GetComponent<Image>();f.innerWidth=f.track.rect.width-8;f.expectedHeight=13;f.minimumWidth=12;f.multiplier=8;Check(player.completed==Mathf.RoundToInt(f.ratio*50),"Wellworks rendering preserves first-clear snapshot");f.scope="Actual unchanged Wellworks Build/Render with a plain PlayerProfile value; no repository/service/claim.";
            }else if(family=="ProfileStats"){
                f.home.State.completedLevelsInChapter=Mathf.RoundToInt(f.ratio*50);f.home.State.levelsPerChapter=50;f.ratio=f.home.State.completedLevelsInChapter/50f;
                var host=f.home.gameObject.AddComponent<PlayerProfileHost>();host.enabled=false;Set(host,"<Ready>k__BackingField",true);
                var page=f.home.gameObject.AddComponent<ProfilePage>();page.enabled=false;Set(page,"home",f.home);Set(page,"assets",Resources.Load<ProfileAssets>("HeartOfTheRainProfile/Config"));Set(page,"store",new ProfileStore(new MemoryAppearancePreferences()));Set(page,"tab",3);Invoke(page,"Build");Invoke(page,"Layout");var scroll=Field<ScrollRect>(page,"scroll");scroll.verticalNormalizedPosition=Screen.width<340?0:1;Canvas.ForceUpdateCanvases();
                f.canvas=Field<Canvas>(page,"canvas");f.safe=Field<RectTransform>(page,"safe");var card=Field<RectTransform>(page,"content").Find("Stat 2");f.track=(RectTransform)card.Find("Stats progress track");f.clip=(RectTransform)card.Find("Stats progress clip");f.fill=f.clip.Find("Stats progress fill").GetComponent<Image>();f.innerWidth=f.track.rect.width;f.expectedHeight=18;f.minimumWidth=12;f.multiplier=4;Check(host.Service==null&&host.ServerSession==null,"Profile stats readiness is an isolated presentation flag; no service initialized");f.scope="Actual Profile Build/Layout/RenderStats with memory-only appearance and Home state; disabled host has only a presentation-ready flag and no service. Compact Stats is scrolled to the actual progress card.";
            }else if(family=="TeamRally"||family=="TeamLife"){
                var page=f.owner.AddComponent<TeamsPage>();page.enabled=false;page.home=f.home;page.assets=teams;
                var data=JsonUtility.FromJson<TeamsSnapshot>(teams.demoData.text);data.eventGoal=1000;data.eventProgress=Mathf.RoundToInt(f.ratio*1000);var member=data.team.members.First();data.chat=new[]{new TeamChatEntry{id="progress-fixture",memberId=member.id,kind="life",goal=1000,received=Mathf.RoundToInt(f.ratio*1000),body="",timeLabel=""}};
                var session=new TeamsSession(data);Set(page,"session",session);Invoke(page,"Build");Invoke(page,"Reflow",family=="TeamLife"?0f:1f);var nodes=Nodes(page);string id=family=="TeamLife"?"chat-progress-fixture-progress":"rally-progress";
                f.canvas=Field<Canvas>(page,"canvas");f.safe=Field<RectTransform>(page,"safe");f.track=nodes[id];f.clip=nodes[id+"-clip"];f.fill=nodes[family=="TeamLife"?"chat-progress-fixture-fill":"rally-fill"].GetComponent<Image>();f.innerWidth=f.track.rect.width;f.expectedHeight=family=="TeamLife"?22:21;f.minimumWidth=22;f.multiplier=4;
                Check(session.Data.eventProgress==data.eventProgress&&session.Data.chat[0].received==data.chat[0].received,"Team rendering preserves sample event/life values without helping/sending");f.scope="Actual Teams Build/Reflow/Render with validated local demo snapshot.1000-unit quota is a renderer boundary fixture, not a new real life-request/event rule. No server/chat/help callback.";
            }else{
                var appearance=f.home.gameObject.AddComponent<ProfilePage>();appearance.enabled=false;Set(appearance,"home",f.home);f.home.State.levelsPerChapter=50;f.home.State.completedLevelsInChapter=Mathf.RoundToInt(f.ratio*50);f.ratio=f.home.State.completedLevelsInChapter/50f;Set(f.home,"usePreviewState",false);f.home.Build();Check(f.home.State.completedLevelsInChapter==Mathf.RoundToInt(f.ratio*50)&&f.home.State.levelsPerChapter==50,"Home fixture Build retains explicit progress instead of replacing it with the prefab preview");var nodes=Nodes(f.home);
                f.canvas=Field<Canvas>(f.home,"canvas");f.safe=Field<RectTransform>(f.home,"safeViewport");f.track=nodes["progress-track"];f.fill=nodes["progress-fill"].GetComponent<Image>();f.innerWidth=f.track.rect.width;f.expectedHeight=f.track.rect.height;f.minimumWidth=0;f.multiplier=f.fill.pixelsPerUnitMultiplier;f.scope="Actual Home Build with explicit state; optional appearance initialization bypassed. Existing sliced direct-width fill, no claim/win/reward animation callback.";
            }
            Canvas.ForceUpdateCanvases();return f;
        }
        static void Case(string family,int fraction){
            Fixture f=null;var row=new BarRow{family=family,width=Screen.width,height=Screen.height};int failures=report.failures.Count;bool completed=false;
            try{
                f=Build(family,fraction);row.ratio=f.ratio;row.scope=f.scope;row.innerWidth=f.innerWidth;row.clipWidth=f.clip?f.clip.rect.width:f.fill.rectTransform.rect.width;row.fillWidth=f.fill.rectTransform.rect.width;row.fillHeight=f.fill.rectTransform.rect.height;row.type=f.fill.type.ToString();row.preserveAspect=f.fill.preserveAspect;row.sliceMultiplier=f.fill.pixelsPerUnitMultiplier;
                Check(f.fill.sprite&&f.fill.type==Image.Type.Sliced&&!f.fill.preserveAspect,family+": actual fill is sliced and does not preserve whole-sprite aspect");Check(Math.Abs(row.fillHeight-f.expectedHeight)<.02f,family+": authored fill height remains unchanged");Check(Math.Abs(row.clipWidth-f.innerWidth*f.ratio)<.03f,family+": visible width is the exact ratio without a minimum positive fill");
                Check(Math.Abs(f.fill.pixelsPerUnitMultiplier-f.multiplier)<.001f,family+": actual slice multiplier retained");Check(!f.fill.raycastTarget,family+": progress artwork cannot intercept player input");
                if(f.clip){Check(f.clip.GetComponent<RectMask2D>()&&f.fill.transform.parent==f.clip,family+": exact-width clip owns the minimum-cap image");Check(f.clip.gameObject.activeSelf==(f.ratio>0),family+": zero width hides clip and all fill artwork");Check(row.fillWidth+0.01f>=Math.Max(f.minimumWidth,row.clipWidth),family+": cap image retains enough width without inflating visible progress");Check(f.fill.rectTransform.anchoredPosition==Vector2.zero,family+": cap image remains at clip origin");}
                CheckTrackGeometry(f,family);Mesh(f,row);InsetMapping(f,family);
                if(family=="RainCup"&&fraction==2&&Screen.width==720)CaptureWhole(f.canvas,"RainCup_OneOfTen_Native.png");
                var pixels=ReadFill(f);row.pixelWidth=pixels.pixelWidth;row.pixelHeight=pixels.pixelHeight;row.pixelCount=pixels.count;row.physicalHeight=pixels.physicalHeight;row.zeroHidden=f.ratio==0&&pixels.count==0;
                if(f.ratio==0)Check(pixels.count==0,family+": GPU renders no residual progress at zero");
                else{
                    Check(pixels.pixelHeight<=Mathf.CeilToInt(pixels.physicalHeight)+2,family+": GPU fill stays within authored vertical slot");
                    float visiblePhysicalWidth=PhysicalWidth(f.clip?f.clip:f.fill.rectTransform);
                    Check(pixels.pixelWidth<=Mathf.CeilToInt(visiblePhysicalWidth)+2,family+": GPU fill respects the exact fraction clip");
                    if(visiblePhysicalWidth>=2)Check(pixels.count>0,family+": positive visible progress produces real GPU pixels");
                    if(f.ratio>=.1f)Check(pixels.pixelHeight>=Math.Max(1,Mathf.FloorToInt(pixels.physicalHeight*.65f)),family+": positive fill keeps vertical body instead of aspect shrinking");
                }
                if(family=="RainCup"&&fraction==2&&Screen.width==720)RainNegative(f,pixels);
                if(family=="ProfileStats"&&fraction==1&&Screen.width==393)ProfileNegative(f,pixels);
                completed=true;
            }catch(Exception error){report.failures.Add(family+" fraction"+fraction+" "+Screen.width+"x"+Screen.height+": "+error);}
            finally{row.passed=completed&&failures==report.failures.Count;report.bars.Add(row);report.cases++;if(f!=null&&f.owner)UnityEngine.Object.DestroyImmediate(f.owner);}
        }
        static void CheckTrackGeometry(Fixture f,string family){
            if(family=="RainCup"){Check(Math.Abs(f.track.rect.height-16)<.01f&&Math.Abs(f.track.anchoredPosition.y+77)<.01f,"Rain Cup approved16-high track stays at hero y77");Check(Math.Abs(f.clip.anchoredPosition.x-(f.track.anchoredPosition.x+3))<.01f&&Math.Abs(f.clip.anchoredPosition.y-(f.track.anchoredPosition.y-3))<.01f,"Rain Cup fill keeps3-unit track inset");}
            if(family=="ProfileStats")Check(Vector2.Distance(f.track.anchoredPosition,new Vector2(36,-283))<.01f&&Vector2.Distance(f.clip.anchoredPosition,f.track.anchoredPosition)<.01f,"Profile progress keeps approved card placement");
            if(family=="TeamRally"||family=="TeamLife")Check(Vector2.Distance(f.clip.anchoredPosition,f.track.anchoredPosition)<.01f&&Math.Abs(f.track.rect.height-f.expectedHeight)<.01f,"Team progress track, value and height keep existing layout");
        }
        static void Mesh(Fixture f,BarRow row){using(var vertices=new VertexHelper()){
            typeof(Image).GetMethod("OnPopulateMesh",BindingFlags.NonPublic|BindingFlags.Instance,null,new[]{typeof(VertexHelper)},null).Invoke(f.fill,new object[]{vertices});row.meshVertices=vertices.currentVertCount;float low=float.MaxValue,high=float.MinValue;var vertex=new UIVertex();for(int i=0;i<vertices.currentVertCount;i++){vertices.PopulateUIVertex(ref vertex,i);low=Math.Min(low,vertex.position.y);high=Math.Max(high,vertex.position.y);}row.meshHeight=vertices.currentVertCount==0?0:high-low;
            if(f.ratio>=.1f)Check(row.meshHeight>=f.expectedHeight*.65f&&row.meshHeight<=f.expectedHeight+.02f,row.family+": actual native slice mesh keeps vertical body/cap geometry");
        }}
        static void InsetMapping(Fixture f,string family){
            if(!f.safe)return;var before=f.fill.rectTransform.rect;var clipBefore=f.clip?f.clip.rect:before;var pos=f.safe.anchoredPosition;
            foreach(var offset in new[]{new Vector2(0,-64),new Vector2(31,-107),new Vector2(0,80)}){
                f.safe.anchoredPosition=pos+offset/Math.Max(.1f,f.canvas.scaleFactor);Canvas.ForceUpdateCanvases();Check(f.fill.rectTransform.rect==before&&(!f.clip||f.clip.rect==clipBefore),family+": injected top/side/bottom translation preserves fill height/ratio");
            }f.safe.anchoredPosition=pos;Canvas.ForceUpdateCanvases();
        }
        static float PhysicalWidth(RectTransform rect){var corners=new Vector3[4];rect.GetWorldCorners(corners);return Vector2.Distance(RectTransformUtility.WorldToScreenPoint(null,corners[0]),RectTransformUtility.WorldToScreenPoint(null,corners[3]));}
        static Pixels ReadFill(Fixture f){var graphics=f.canvas.GetComponentsInChildren<Graphic>(true);var states=graphics.Select(g=>g.enabled).ToArray();try{foreach(var g in graphics)g.enabled=g==f.fill;return Render(f.canvas,f.fill.rectTransform,null);}finally{for(int i=0;i<graphics.Length;i++)if(graphics[i])graphics[i].enabled=states[i];}}
        static Pixels Render(Canvas canvas,RectTransform fill,string file){
            var go=new GameObject("Native progress92 framebuffer camera");var camera=go.AddComponent<Camera>();camera.enabled=false;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.clear;camera.orthographic=true;camera.transform.position=new Vector3(-10000,0,-10);camera.nearClipPlane=.1f;camera.farClipPlane=100;
            var target=new RenderTexture(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);var previous=RenderTexture.active;var mode=canvas.renderMode;var oldCamera=canvas.worldCamera;float distance=canvas.planeDistance;Texture2D texture=null;
            try{
                target.Create();camera.targetTexture=target;canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;Canvas.ForceUpdateCanvases();camera.Render();Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;texture=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);texture.ReadPixels(new Rect(0,0,target.width,target.height),0,0);texture.Apply();
                var result=new Pixels{width=target.width,height=target.height,data=texture.GetPixels32()};int left=result.width,right=-1,bottom=result.height,top=-1;
                for(int y=0;y<result.height;y++)for(int x=0;x<result.width;x++)if(result.data[y*result.width+x].a>16){result.count++;left=Math.Min(left,x);right=Math.Max(right,x);bottom=Math.Min(bottom,y);top=Math.Max(top,y);}
                result.pixelWidth=right<left?0:right-left+1;result.pixelHeight=top<bottom?0:top-bottom+1;
                if(fill){var corners=new Vector3[4];fill.GetWorldCorners(corners);var a=RectTransformUtility.WorldToScreenPoint(camera,corners[0]);var b=RectTransformUtility.WorldToScreenPoint(camera,corners[2]);result.physicalHeight=Math.Abs(b.y-a.y);result.crop=new RectInt(Math.Max(0,Mathf.FloorToInt(a.x)-4),Math.Max(0,Mathf.FloorToInt(a.y)-4),Math.Min(result.width,Mathf.CeilToInt(Math.Abs(b.x-a.x))+8),Math.Min(result.height,Mathf.CeilToInt(Math.Abs(b.y-a.y))+8));}
                if(file!=null){File.WriteAllBytes(Path.Combine(output,file),texture.EncodeToPNG());report.captures.Add(file);}return result;
            }finally{canvas.renderMode=mode;canvas.worldCamera=oldCamera;canvas.planeDistance=distance;camera.targetTexture=null;RenderTexture.active=previous;if(texture)UnityEngine.Object.DestroyImmediate(texture);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(go);Canvas.ForceUpdateCanvases();}
        }
        static void CaptureWhole(Canvas canvas,string file){Render(canvas,null,file);}
        static void SaveCrop(Pixels pixels,string file){var c=pixels.crop;int w=Math.Min(c.width,pixels.width-c.x),h=Math.Min(c.height,pixels.height-c.y);Check(w>0&&h>0,"Selected native progress crop is inside the original framebuffer");var texture=new Texture2D(w,h,TextureFormat.RGBA32,false);try{var data=new Color32[w*h];for(int y=0;y<h;y++)Array.Copy(pixels.data,(c.y+y)*pixels.width+c.x,data,y*w,w);texture.SetPixels32(data);texture.Apply();File.WriteAllBytes(Path.Combine(output,file),texture.EncodeToPNG());report.captures.Add(file);}finally{UnityEngine.Object.DestroyImmediate(texture);}}
        static void RainNegative(Fixture f,Pixels fixedPixels){
            report.newRainPixelHeight=fixedPixels.pixelHeight;SaveCrop(fixedPixels,"RainCup_Fixed_OneOfTen_Bar.png");var r=f.fill.rectTransform;var size=r.sizeDelta;var kind=f.fill.type;bool aspect=f.fill.preserveAspect;try{r.sizeDelta=new Vector2(f.clip.rect.width,f.expectedHeight);f.fill.type=Image.Type.Simple;f.fill.preserveAspect=true;var old=ReadFill(f);report.oldRainPixelHeight=old.pixelHeight;SaveCrop(old,"RainCup_Old_Aspect_Bar_NegativeControl.png");Check(fixedPixels.pixelHeight>=old.pixelHeight+2,"Native old Rain Cup preserveAspect negativecontrol reproduces the thinner1/10 body");}finally{r.sizeDelta=size;f.fill.type=kind;f.fill.preserveAspect=aspect;}}
        static void ProfileNegative(Fixture f,Pixels fixedPixels){
            report.newProfilePixelCount=fixedPixels.count;SaveCrop(fixedPixels,"Profile_OneOfFifty_Fixed_Bar.png");var r=f.fill.rectTransform;var size=r.sizeDelta;var kind=f.fill.type;float amount=f.fill.fillAmount;try{r.sizeDelta=new Vector2(f.innerWidth,f.expectedHeight);f.fill.type=Image.Type.Filled;f.fill.fillMethod=Image.FillMethod.Horizontal;f.fill.fillAmount=f.ratio;var old=ReadFill(f);report.oldProfilePixelCount=old.count;Check(fixedPixels.count>old.count,"Native low Profile progress becomes visible beyond the original padded-Filled sprite sliver");}finally{r.sizeDelta=size;f.fill.type=kind;f.fill.fillAmount=amount;}}
        static void Audits(){
            foreach(string family in Families)report.audits.Add(new Audit{family=family,kind="actual-production-ugui-mesh-and-gpu",status=report.bars.Where(r=>r.family==family).All(r=>r.passed)?"PASS":"FAIL",scope="Four actual native GameView sizes; ratios0/verylow/10/50/100 and explicit safe-root translations, with no live data mutations."});
            var launch=File.ReadAllText("Assets/HeartOfTheRain/App/Launch/Runtime/LaunchPage.cs");Check(launch.Contains("Image.Type.Sliced")&&launch.Contains("fill.gameObject.SetActive(Progress>0)")&&launch.Contains("r.anchorMax=new Vector2(Progress,1)"),"Launch uses existing sliced full-height progress and exact monotonic horizontal anchors; zero hidden");report.audits.Add(new Audit{family="Launch",kind="source-invariant-only",status="REVIEWED_UNCHANGED",scope="Source review of current launch bar. Its actual startup readiness, textures and device appearance remain outside this targeted progress fixture."});
            report.audits.Add(new Audit{family="LevelComplete",kind="legacy-source-review-only",status="NOT_ACTIVE_WIN_ROUTE",scope="Legacy M66 modal remains outside live HomeLevelFlow/M67 win route; no redesign or legacy runtime behavior change included."});
            Check(!File.ReadAllText("Assets/HeartOfTheRain/App/OnlineSocial/Runtime/OnlineTeamsLayout82.cs").Contains("rally-fill"),"Connected Teams layout has no equivalent local demo event/life progress primitive to change");report.audits.Add(new Audit{family="OnlineTeams",kind="source-inventory-only",status="NO_SHARED_PROGRESS_BAR",scope="Connected team messages/rankings have no local demo Rally/life-request bar; no connected data or social service acceptance claimed."});
        }
        static void Finish(){
            if(finishing)return;finishing=true;EditorApplication.update-=Tick;GameLocale.Select(oldLocale);
            try{var view=View();view.GetType().GetProperty("selectedSizeIndex",Private).SetValue(view,SessionState.GetInt(Key+".previous",0));var group=Group();for(int i=Sizes.Length-1;i>=0;i--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt(Key+".first",0)+i});}catch(Exception error){report.errors.Add("GameView restore: "+error.GetType().Name);}
            Application.logMessageReceived-=Log;SessionState.SetBool(Key,false);int code=report.failures.Count==0&&report.errors.Count==0&&report.cases==Sizes.Length*Families.Length*Fractions.Length?0:1;report.status=code==0?"PASS_NATIVE_PROGRESS92":"FAIL_NATIVE_PROGRESS92";File.WriteAllText(Path.Combine(output,"Report.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(code);
        }
    }
}
#endif
