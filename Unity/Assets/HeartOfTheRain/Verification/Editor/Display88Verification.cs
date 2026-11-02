#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;

namespace HeartOfTheRain.Verification
{
    // Synchronous pinned-Editor geometry and native rendering checks. No ordinary
    // profile, PlayerPrefs, service, Play Mode session or Android device is used.
    public static class Display88Verification
    {
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        const string Entry="Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity";
        const int DiagnosticLayer=30;
        [Serializable] sealed class Capture {public string file,scope;public int width,height;}
        [Serializable] sealed class GeometryRow {public string name;public int width,height,columns,rows,points;public Rect safe;public float maximumScreenError,maximumInverseError;}
        [Serializable] sealed class Report
        {
            public string status,utc,unity,scope="Native Unity Editor Camera viewport projection/inverse with explicit framebuffer/safe-rectangle mapping, actual HomePage.Build UGUI hierarchy and synthetic RenderTexture composition. Each geometry case uses its own full-resolution render target; viewport APIs avoid treating the Editor window as an arbitrary physical screen. Injected insets are test geometry, not a device Screen.safeArea override. No Android, physical touch, ordinary save, backend, timing or campaign acceptance.";
            public int checks,oldBandMarkerPixels,newBandMarkerPixels;
            public List<string> failures=new List<string>(),errors=new List<string>();
            public List<GeometryRow> geometry=new List<GeometryRow>();
            public List<Capture> captures=new List<Capture>();
        }
        struct Case
        {
            public string name;public int width,height;public Rect safe;
            public Case(string n,int w,int h,Rect s){name=n;width=w;height=h;safe=s;}
        }
        static readonly Case[] Cases={
            new Case("Phone_no_insets",720,1600,new Rect(0,0,720,1600)),
            new Case("Realme_top64",720,1600,new Rect(0,0,720,1536)),
            new Case("Phone_bottom80",720,1600,new Rect(0,80,720,1520)),
            new Case("Phone_top_and_bottom",1080,2400,new Rect(0,96,1080,2200)),
            new Case("Phone_asymmetric",1080,2400,new Rect(31,82,1027,2211)),
            new Case("Compact_portrait",320,568,new Rect(0,20,320,524)),
            new Case("Tablet_portrait",1200,1600,new Rect(0,48,1200,1496)),
            new Case("Tablet_asymmetric",1536,2048,new Rect(36,74,1472,1873))
        };
        static Report report;static string output;
        static void Check(bool ok,string reason){report.checks++;if(!ok)report.failures.Add(reason);}
        static void Log(string message,string stack,LogType type)
        {if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(message+"\n"+stack);}
        static void Section(string name,Action action)
        {try{action();}catch(Exception e){report.failures.Add(name+": "+e);}}
        public static void Run()
        {
            output=Environment.GetEnvironmentVariable("HOTR_DISPLAY88_OUT");
            if(string.IsNullOrWhiteSpace(output))output=Path.GetFullPath("../Verification/Evidence/Display88/Editor");
            output=Path.GetFullPath(output);Directory.CreateDirectory(output);
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
            Application.logMessageReceived+=Log;
            try
            {
                Check(Application.unityVersion=="2022.3.62f3","Pinned Unity 2022.3.62f3");
                Check(!Application.isPlaying,"Editor checks must not enter ordinary Play Mode");
                Section("Projection and inverse",ProjectionChecks);
                Section("Invalid safe fallback",FallbackChecks);
                Section("Entry cameras",EntryChecks);
                Section("Native Home hierarchy",HomeChecks);
                Section("Native band rendering",RenderingChecks);
            }
            catch(Exception e){report.failures.Add(e.ToString());}
            finally{Application.logMessageReceived-=Log;}
            int code=report.failures.Count==0&&report.errors.Count==0?0:1;
            report.status=code==0?"PASS_NATIVE_DISPLAY88":"FAIL_NATIVE_DISPLAY88";
            File.WriteAllText(Path.Combine(output,"Report.json"),JsonUtility.ToJson(report,true));
            EditorApplication.Exit(code);
        }
        static Camera MakeCamera(string name)
        {
            var camera=new GameObject(name).AddComponent<Camera>();camera.enabled=false;camera.orthographic=true;
            camera.nearClipPlane=.1f;camera.farClipPlane=100;camera.clearFlags=CameraClearFlags.SolidColor;
            camera.backgroundColor=new Color(.025f,.12f,.3f,1);camera.allowHDR=false;camera.allowMSAA=false;
            camera.cullingMask=1<<DiagnosticLayer;return camera;
        }
        static void Configure(Camera camera,RenderTexture target,Rect pixels,float half,Vector2 center)
        {camera.targetTexture=target;camera.rect=new Rect(0,0,1,1);camera.aspect=pixels.width/pixels.height;camera.orthographicSize=half;camera.transform.position=new Vector3(center.x,center.y,-10);}
        static Vector3 ToScreen(Camera camera,Vector3 point,Rect pixels)
        {var viewport=camera.WorldToViewportPoint(point);return new Vector3(pixels.x+viewport.x*pixels.width,pixels.y+viewport.y*pixels.height,viewport.z);}
        static Vector3 FromScreen(Camera camera,Vector3 screen,Rect pixels)
        {return camera.ViewportToWorldPoint(new Vector3((screen.x-pixels.x)/pixels.width,(screen.y-pixels.y)/pixels.height,screen.z));}
        static void ProjectionChecks()
        {
            var old=MakeCamera("Display88 original safe projection");var current=MakeCamera("Display88 full projection");
            try
            {
                foreach(var c in Cases)
                {
                    var target=new RenderTexture(c.width,c.height,24,RenderTextureFormat.ARGB32);target.Create();
                    try{foreach(int columns in new[]{5,8,9})foreach(int rows in new[]{5,8,10}){
                    var layout=ReviewLayout.Compute(c.safe.width,c.safe.height,columns,rows);
                    float half=layout.height/(2*layout.cell),centerY=20/layout.cell;
                    var view=FullDisplayBoardView.Compute(c.width,c.height,c.safe,half,centerY);
                    var display=new Rect(0,0,c.width,c.height);
                    Configure(old,target,c.safe,half,new Vector2(0,centerY));Configure(current,target,display,view.halfHeight,view.center);
                    Check(Mathf.Abs(old.aspect-c.safe.width/c.safe.height)<.00001f&&Mathf.Abs(current.aspect-c.width/(float)c.height)<.00001f,c.name+": native camera aspect matches the explicit pixel rectangle");
                    var row=new GeometryRow{name=c.name,width=c.width,height=c.height,columns=columns,rows=rows,safe=c.safe};
                    var points=new List<Vector3>();
                    for(int y=0;y<rows;y++)for(int x=0;x<columns;x++)points.Add(new Vector3(x-(columns-1)*.5f,y-(rows-1)*.5f,0));
                    // Collection anchors and input boundaries include half-cell points,
                    // asymmetric inset edges and positions just inside the safe area.
                    foreach(float x in new[]{c.safe.xMin+.01f,c.safe.center.x,c.safe.xMax-.01f})
                    foreach(float y in new[]{c.safe.yMin+.01f,c.safe.yMin+c.safe.height*.12f,c.safe.center.y,c.safe.yMax-c.safe.height*.14f,c.safe.yMax-.01f})
                        points.Add(FromScreen(old,new Vector3(x,y,10),c.safe));
                    foreach(var point in points)
                    {
                        Vector3 before=ToScreen(old,point,c.safe),after=ToScreen(current,point,display);
                        float screenError=Vector2.Distance(before,after);row.maximumScreenError=Mathf.Max(row.maximumScreenError,screenError);
                        Check(screenError<.01f,c.name+" "+columns+"x"+rows+": board/collection anchor moved "+screenError+"px");
                        Vector3 originalWorld=FromScreen(old,before,c.safe),currentWorld=FromScreen(current,before,display);
                        float inverseError=Vector3.Distance(originalWorld,currentWorld);row.maximumInverseError=Mathf.Max(row.maximumInverseError,inverseError);
                        Check(inverseError<.0002f,c.name+": screen input maps to a different board position "+inverseError);
                        // Cell rounding is checked on actual cell centres, without a
                        // tie at an arbitrary half-cell input boundary.
                        if(row.points<columns*rows)
                        {
                            int bx=Mathf.RoundToInt(originalWorld.x+(columns-1)*.5f),by=Mathf.RoundToInt(originalWorld.y+(rows-1)*.5f);
                            int ax=Mathf.RoundToInt(currentWorld.x+(columns-1)*.5f),ay=Mathf.RoundToInt(currentWorld.y+(rows-1)*.5f);
                            Check(ax==bx&&ay==by,c.name+": cell selection changed");
                        }
                        row.points++;
                    }
                    Check(view.halfHeight>=half-.00001f,c.name+": full view cropped the original safe projection");
                    // Independent native screen corners establish that the expanded
                    // backdrop dimensions really cover the entire camera viewport.
                    float fullWidth=2*view.halfHeight*c.width/c.height;
                    var bounds=new Bounds(new Vector3(view.center.x,view.center.y,1),new Vector3(fullWidth,2*view.halfHeight,0));
                    foreach(var pixel in new[]{new Vector2(0,0),new Vector2(c.width,0),new Vector2(0,c.height),new Vector2(c.width,c.height)})
                    {
                        var world=FromScreen(current,new Vector3(pixel.x,pixel.y,11),display);
                        Check(world.x>=bounds.min.x-.0001f&&world.x<=bounds.max.x+.0001f&&world.y>=bounds.min.y-.0001f&&world.y<=bounds.max.y+.0001f,c.name+": backdrop misses a full-display corner");
                    }
                    report.geometry.Add(row);
                    }}finally{old.targetTexture=current.targetTexture=null;target.Release();UnityEngine.Object.DestroyImmediate(target);}
                }
            }
            finally{UnityEngine.Object.DestroyImmediate(old.gameObject);UnityEngine.Object.DestroyImmediate(current.gameObject);}
        }
        static void FallbackChecks()
        {
            var expected=FullDisplayBoardView.Compute(720,1600,new Rect(0,0,720,1600),8,.3f);
            foreach(var safe in new[]{new Rect(),new Rect(20,30,0,800),new Rect(20,30,700,-1)})
            {
                var actual=FullDisplayBoardView.Compute(720,1600,safe,8,.3f);
                Check(Mathf.Abs(actual.halfHeight-expected.halfHeight)<.00001f&&Vector2.Distance(actual.center,expected.center)<.00001f,"Empty/negative safe area falls back to the full display");
            }
            foreach(var value in new[]{0f,-1f})
            {
                bool rejected=false;try{FullDisplayBoardView.Compute(value,1600,new Rect(0,0,720,1600),8,0);}catch(ArgumentOutOfRangeException){rejected=true;}Check(rejected,"Reject invalid display width "+value);
                rejected=false;try{FullDisplayBoardView.Compute(720,value,new Rect(0,0,720,1600),8,0);}catch(ArgumentOutOfRangeException){rejected=true;}Check(rejected,"Reject invalid display height "+value);
                rejected=false;try{FullDisplayBoardView.Compute(720,1600,new Rect(0,0,720,1600),value,0);}catch(ArgumentOutOfRangeException){rejected=true;}Check(rejected,"Reject invalid safe projection "+value);
            }
        }
        static void EntryChecks()
        {
            var previous=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            var scene=UnityEngine.SceneManagement.SceneManager.GetSceneByPath(Entry);
            bool opened=!scene.IsValid()||!scene.isLoaded;
            if(opened)scene=EditorSceneManager.OpenScene(Entry,OpenSceneMode.Additive);
            try
            {
                var cameras=scene.GetRootGameObjects().SelectMany(go=>go.GetComponentsInChildren<Camera>(true)).Where(c=>c.name=="Home Review Camera").ToArray();
                Check(cameras.Length==1,"Live first-start entry has exactly one Home background camera");
                foreach(var camera in cameras)
                {
                    Check(camera.cullingMask==0,"Home background camera cannot draw gameplay sprites");
                    Check(camera.clearFlags==CameraClearFlags.SolidColor,"Home background camera clears its framebuffer");
                    Check(camera.rect==new Rect(0,0,1,1),"Home background camera clears the whole display");
                    Check(camera.depth<0,"Home background camera remains below gameplay");
                }
            }
            finally
            {
                if(previous.IsValid()&&previous.isLoaded)UnityEngine.SceneManagement.SceneManager.SetActiveScene(previous);
                if(opened)EditorSceneManager.CloseScene(scene,true);
            }
        }
        static T Field<T>(object owner,string name)=>(T)owner.GetType().GetField(name,Private).GetValue(owner);
        static void SetField(object owner,string name,object value)=>owner.GetType().GetField(name,Private).SetValue(owner,value);
        static void HomeChecks()
        {
            var previous=UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            bool replaceDefault=UnityEngine.SceneManagement.SceneManager.sceneCount==1&&string.IsNullOrEmpty(previous.path);
            if(replaceDefault&&!Application.isBatchMode)throw new InvalidOperationException("An untitled scene may only be replaced in the isolated batch verification process.");
            // A fresh batch Editor begins with an unsaved untitled scene. Unity
            // refuses additive NewScene in that state; replace it only in this
            // isolated batch process, without saving or modifying any asset scene.
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,replaceDefault?NewSceneMode.Single:NewSceneMode.Additive);GameObject instance=null,events=null;
            try
            {
                var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab");Check(prefab,"Actual Home prefab exists");
                instance=(GameObject)PrefabUtility.InstantiatePrefab(prefab,scene);var home=instance.GetComponent<HomePage>();
                // Home's optional Profile route is outside this test. Pre-bind only
                // its owner, so Build cannot read appearance preferences or start its
                // background preparation coroutine in an Edit Mode fixture.
                var profile=instance.AddComponent<ProfilePage>();SetField(profile,"home",home);
                if(!EventSystem.current){events=new GameObject("Display88 isolated EventSystem",typeof(EventSystem));UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(events,scene);}
                home.Build();Canvas.ForceUpdateCanvases();Canvas.ForceUpdateCanvases();
                var canvas=Field<Canvas>(home,"canvas");var artwork=Field<RawImage>(home,"background");var safe=Field<RectTransform>(home,"safeViewport");
                Check(canvas&&artwork&&artwork.texture&&safe,"Actual Home constructs its canvas, chapter art and safe viewport");
                Check(artwork.transform.parent==canvas.transform,"Chapter artwork belongs to the full canvas");
                Check(!artwork.GetComponentsInParent<RectMask2D>().Any(),"Safe masks cannot clip the chapter artwork");
                Check(artwork.transform.GetSiblingIndex()<safe.GetSiblingIndex(),"Safe controls render above chapter artwork");
                Check(!artwork.raycastTarget,"Full-screen artwork cannot intercept controls");
                Check(safe.GetComponent<RectMask2D>()&&safe.GetComponent<ScrollRect>(),"Controls retain their safe-area mask and scrolling");
                var canvasRect=(RectTransform)canvas.transform;var artCorners=new Vector3[4];var canvasCorners=new Vector3[4];
                artwork.rectTransform.GetWorldCorners(artCorners);canvasRect.GetWorldCorners(canvasCorners);
                for(int i=0;i<4;i++)Check(Vector3.Distance(artCorners[i],canvasCorners[i])<.02f,"Actual Home art covers native canvas corner "+i);
                Check(artwork.uvRect.width>0&&artwork.uvRect.height>0&&artwork.uvRect.xMin>=-.0001f&&artwork.uvRect.yMin>=-.0001f&&artwork.uvRect.xMax<=1.0001f&&artwork.uvRect.yMax<=1.0001f,"Cover-cropped artwork samples only approved source pixels");
                var originalPosition=safe.anchoredPosition;var originalSize=safe.sizeDelta;
                // Explicit injected mask changes verify separation of decorative
                // coverage and safe controls; this does not override Screen.safeArea.
                foreach(var inset in new[]{new Rect(0,0,Screen.width,Screen.height-64),new Rect(12,48,Screen.width-30,Screen.height-128)})
                {
                    float scale=canvas.scaleFactor;safe.anchoredPosition=new Vector2(inset.x/scale,-(Screen.height-inset.yMax)/scale);safe.sizeDelta=inset.size/scale;Canvas.ForceUpdateCanvases();
                    var corners=new Vector3[4];artwork.rectTransform.GetWorldCorners(corners);
                    for(int i=0;i<4;i++)Check(Vector3.Distance(corners[i],artCorners[i])<.02f,"Injected safe mask cannot uncover a Home art band "+i);
                }
                safe.anchoredPosition=originalPosition;safe.sizeDelta=originalSize;Canvas.ForceUpdateCanvases();
                CaptureCanvas(canvas,"Home_actual_native_editor.png");
            }
            finally
            {
                if(instance)
                {
                    var home=instance.GetComponent<HomePage>();var slices=home?Field<HomeHeaderSprites>(home,"headerSprites"):null;
                    // The production disposer correctly uses delayed destruction in
                    // Play Mode. This Edit Mode fixture owns and immediately releases
                    // those temporary slices without touching asset sprites.
                    if(slices!=null){foreach(var sprite in new[]{slices.Panel,slices.DefaultAvatar,slices.Connector})if(sprite)UnityEngine.Object.DestroyImmediate(sprite);SetField(home,"headerSprites",null);}
                    if(home)SetField(home,"ownedEvents",null);
                    UnityEngine.Object.DestroyImmediate(instance);
                }
                if(events)UnityEngine.Object.DestroyImmediate(events);
                if(!replaceDefault)
                {
                    if(previous.IsValid()&&previous.isLoaded)UnityEngine.SceneManagement.SceneManager.SetActiveScene(previous);
                    EditorSceneManager.CloseScene(scene,true);
                }
                // In the batch-only replacement case leave the now-empty last
                // scene until EditorApplication.Exit; Unity cannot remove it.
            }
        }
        static void CaptureCanvas(Canvas canvas,string filename)
        {
            var camera=MakeCamera("Display88 Home UI capture");camera.transform.position=new Vector3(-10000,0,-10);camera.cullingMask=~0;
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(camera.gameObject,canvas.gameObject.scene);
            var target=new RenderTexture(Mathf.Max(1,Screen.width),Mathf.Max(1,Screen.height),24,RenderTextureFormat.ARGB32);target.Create();
            var mode=canvas.renderMode;var previousCamera=canvas.worldCamera;float distance=canvas.planeDistance;
            try
            {
                camera.targetTexture=target;camera.rect=new Rect(0,0,1,1);canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;
                Canvas.ForceUpdateCanvases();camera.Render();Canvas.ForceUpdateCanvases();camera.Render();
                var pixels=Save(target,filename,"Actual HomePage.Build native UGUI; Editor window geometry, not a phone capture.");
                var colours=new HashSet<uint>();for(int i=0;i<pixels.Length;i+=17){var p=pixels[i];colours.Add((uint)((p.r/8)<<10|(p.g/8)<<5|p.b/8));}
                Check(colours.Count>50,"Actual Home native UI capture contains rendered artwork, not a flat clear colour");
            }
            finally
            {
                canvas.renderMode=mode;canvas.worldCamera=previousCamera;canvas.planeDistance=distance;camera.targetTexture=null;
                target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(camera.gameObject);Canvas.ForceUpdateCanvases();
            }
        }
        static SpriteRenderer Quad(string name,Sprite sprite,Material material,Vector3 position,Vector3 scale,Color color,int order)
        {
            var go=new GameObject(name);go.layer=DiagnosticLayer;go.transform.position=position;go.transform.localScale=scale;
            var renderer=go.AddComponent<SpriteRenderer>();renderer.sprite=sprite;renderer.sharedMaterial=material;renderer.color=color;renderer.sortingOrder=order;return renderer;
        }
        static void RenderingChecks()
        {
            const int width=720,height=1600;var safe=new Rect(0,0,width,height-64);
            var layout=ReviewLayout.Compute(safe.width,safe.height,9,9);float oldHalf=layout.height/(2*layout.cell),oldCenter=20/layout.cell;
            var full=FullDisplayBoardView.Compute(width,height,safe,oldHalf,oldCenter);
            var baseCamera=MakeCamera("Display88 old full-screen Home camera");var oldCamera=MakeCamera("Display88 old safe gameplay camera");var newCamera=MakeCamera("Display88 corrected full-screen gameplay camera");
            var before=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32);before.Create();
            var safeTexture=new RenderTexture((int)safe.width,(int)safe.height,24,RenderTextureFormat.ARGB32);safeTexture.Create();
            var after=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32);after.Create();
            var texture=new Texture2D(1,1,TextureFormat.RGBA32,false);texture.SetPixel(0,0,Color.white);texture.Apply();
            var sprite=Sprite.Create(texture,new Rect(0,0,1,1),Vector2.one*.5f,1);var material=new Material(Shader.Find("Sprites/Default"));
            var background=Quad("Display88 diagnostic backdrop",sprite,material,new Vector3(0,0,1),new Vector3(100,100,1),new Color(.02f,.27f,.55f),-100);
            // At y=4.8 the old unrelated ortho-5 camera puts the marker in the
            // top unsafe band. Correct gameplay projection places it inside safe.
            var marker=Quad("Display88 diagnostic board marker",sprite,material,new Vector3(0,4.8f,0),new Vector3(.5f,.16f,1),Color.red,10);
            var active=RenderTexture.active;
            try
            {
                baseCamera.targetTexture=before;baseCamera.orthographicSize=5;baseCamera.aspect=width/(float)height;baseCamera.transform.position=new Vector3(0,0,-10);baseCamera.rect=new Rect(0,0,1,1);baseCamera.Render();
                oldCamera.targetTexture=safeTexture;oldCamera.orthographicSize=oldHalf;oldCamera.aspect=safe.width/safe.height;oldCamera.transform.position=new Vector3(0,oldCenter,-10);oldCamera.rect=new Rect(0,0,1,1);oldCamera.Render();
                // RenderTexture cameras use their complete texture. Composite that
                // actual native safe projection at its framebuffer rectangle to
                // reproduce the old pair of camera viewports without assuming that
                // targetTexture honours Camera.rect on every graphics backend.
                Graphics.SetRenderTarget(before);GL.PushMatrix();
                try{GL.LoadPixelMatrix(0,width,0,height);Graphics.DrawTexture(safe,safeTexture);}
                finally{GL.PopMatrix();Graphics.SetRenderTarget(active);}
                newCamera.targetTexture=after;newCamera.rect=new Rect(0,0,1,1);newCamera.aspect=width/(float)height;newCamera.orthographicSize=full.halfHeight;newCamera.transform.position=new Vector3(full.center.x,full.center.y,-10);
                background.transform.position=new Vector3(full.center.x,full.center.y,1);background.transform.localScale=new Vector3(2*full.halfHeight*width/height,2*full.halfHeight,1);newCamera.Render();
                var beforePixels=Save(before,"Diagnostic_old_duplicate_band.png","Synthetic native-camera rendering and viewport composition reproducing the original two-camera mechanism; not an archived app or phone screenshot.");
                var afterPixels=Save(after,"Diagnostic_corrected_full_display.png","Synthetic native corrected-camera rendering with unchanged marker/board projection and full-display backdrop; not a phone screenshot.");
                report.oldBandMarkerPixels=RedPixels(beforePixels,width,(int)safe.yMax,height);
                report.newBandMarkerPixels=RedPixels(afterPixels,width,(int)safe.yMax,height);
                Check(report.oldBandMarkerPixels>100,"Negative control reproduces an unrelated board marker in the top band");
                Check(report.newBandMarkerPixels==0,"Correct full-screen camera removes duplicate gameplay in the top band");
                Check(RedPixels(afterPixels,width,0,(int)safe.yMax)>100,"Correct camera preserves the original marker in its proper safe position");
                foreach(var p in new[]{new Vector2Int(3,3),new Vector2Int(width-4,3),new Vector2Int(3,height-4),new Vector2Int(width-4,height-4)})
                {var color=afterPixels[p.y*width+p.x];Check(color.b>60&&color.b>color.r+20,"Native backdrop fills framebuffer corner "+p);}
            }
            finally
            {
                RenderTexture.active=active;
                baseCamera.targetTexture=oldCamera.targetTexture=newCamera.targetTexture=null;
                foreach(var camera in new[]{baseCamera,oldCamera,newCamera})UnityEngine.Object.DestroyImmediate(camera.gameObject);
                UnityEngine.Object.DestroyImmediate(marker.gameObject);UnityEngine.Object.DestroyImmediate(background.gameObject);UnityEngine.Object.DestroyImmediate(material);UnityEngine.Object.DestroyImmediate(sprite);UnityEngine.Object.DestroyImmediate(texture);
                foreach(var target in new[]{before,safeTexture,after}){target.Release();UnityEngine.Object.DestroyImmediate(target);}
            }
        }
        static int RedPixels(Color32[] pixels,int width,int bottom,int top)
        {int count=0;for(int y=bottom;y<top;y++)for(int x=0;x<width;x++){var color=pixels[y*width+x];if(color.r>180&&color.g<60&&color.b<60)count++;}return count;}
        static Color32[] Save(RenderTexture target,string filename,string scope)
        {
            var previous=RenderTexture.active;var pixels=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);
            try{RenderTexture.active=target;pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(output,filename),pixels.EncodeToPNG());report.captures.Add(new Capture{file=filename,scope=scope,width=target.width,height=target.height});return pixels.GetPixels32();}
            finally{RenderTexture.active=previous;UnityEngine.Object.DestroyImmediate(pixels);}
        }
    }
}
#endif
