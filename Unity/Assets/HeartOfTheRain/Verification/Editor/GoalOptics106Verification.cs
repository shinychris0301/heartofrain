#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    public static class GoalOptics106Verification {
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static readonly string[] Families={"crate","moss","stone","pail","case","gate","crystal","pod","rainlight"};
        [Serializable] sealed class Row {public string family;public int slots,width,height;public Rect icon;public float physicalScale;}
        [Serializable] sealed class Report {
            public string status,utc,unity,scope="Actual Editor GameplayHUD.Build/UpdateState, approved imported sprites, static source-alpha verification and isolated GPU icon/glyph/painted-panel checks. Synthetic boundary counts and safe areas; real50-level goal definitions are read only. No gameplay board, Android/device, human playtest or runtime performance certification.";
            public int checks,layouts,gpuLayouts,sourceAssets,levels;public bool profilesPreserved,serverReviewPreserved,languagePreferencePreserved,settingsPreserved;
            public bool failureCaptured;
            public List<string> errors=new List<string>(),captures=new List<string>();public List<Row> alpha=new List<Row>();
        }
        sealed class Fixture:IDisposable {
            public GameObject owner;public GameplayHUD hud;public Canvas canvas;public int width,height;public float scale;public Goal[] goals;
            public Fixture(GameplayUIAssets assets,Goal[] goals,int width,int height,Rect area){
                this.width=width;this.height=height;this.goals=goals;scale=area.width/720;
                owner=new GameObject("106 actual objective HUD fixture");hud=owner.AddComponent<GameplayHUD>();hud.enabled=false;hud.assets=assets;hud.feedback=owner.AddComponent<GameplayFeedback>();hud.feedback.assets=assets;hud.feedback.soundEnabled=false;hud.feedback.hapticsEnabled=false;hud.Build();
                canvas=Field<Canvas>(hud,"canvas");canvas.renderMode=RenderMode.WorldSpace;canvas.GetComponent<CanvasScaler>().enabled=false;canvas.scaleFactor=scale;
                var root=(RectTransform)canvas.transform;root.anchorMin=root.anchorMax=root.pivot=Vector2.one*.5f;root.localPosition=Vector3.zero;root.localScale=Vector3.one;root.sizeDelta=new Vector2(width/scale,height/scale);
                var safe=Field<RectTransform>(hud,"safe");safe.anchoredPosition=new Vector2(area.x/scale,-(height-area.yMax)/scale);safe.sizeDelta=new Vector2(720,area.height/scale);Set(hud,"<Height>k__BackingField",area.height/scale);Field<RectTransform>(hud,"bar").anchoredPosition=new Vector2(0,-(area.height/scale-166));Set(hud,"first",false);Set(hud,"previousSafe",Screen.safeArea);
                hud.UpdateState(1,25,goals,new BoosterInventory(),-1,false,"");Canvas.ForceUpdateCanvases();
            }
            public Image Icon(string family)=>Field<Dictionary<string,RectTransform>>(hud,"goalRects")[family].GetComponentsInChildren<Image>().Single();
            public List<Text> Counters=>Field<List<Text>>(hud,"goalCounters");
            public Image Panel=>canvas.GetComponentsInChildren<Image>().Single(v=>v.name=="Panel_Goals");
            public void Peak(bool completed){
                if(completed){foreach(var goal in goals)goal.count=0;hud.UpdateState(1,25,goals,new BoosterInventory(),-1,false,"");}
                var pulse=Field<List<float>>(hud,"goalPulse");for(int i=0;i<pulse.Count;i++)pulse[i]=Time.unscaledTime-.12f;
                typeof(GameplayHUD).GetMethod("Update",Private).Invoke(hud,null);Canvas.ForceUpdateCanvases();
            }
            public void Dispose(){if(owner)UnityEngine.Object.DestroyImmediate(owner);}
        }
        static Report report;static string output;static GameplayUIAssets assets;
        static T Field<T>(object value,string name)=>(T)value.GetType().GetField(name,Private).GetValue(value);
        static void Set(object value,string name,object next)=>value.GetType().GetField(name,Private).SetValue(value,next);
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        static void Case(string name,Action action){try{action();}catch(Exception e){report.errors.Add(name+": "+e);}}
        static string Digest(string path){using(var sha=SHA256.Create())return Convert.ToBase64String(sha.ComputeHash(File.ReadAllBytes(path)));}
        static string Tree(string root)=>!Directory.Exists(root)?"Absent":"Present:"+string.Join("\n",Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(v=>v,StringComparer.Ordinal).Select(v=>v.Substring(root.Length)+":"+Digest(v)));
        public static void Run(){
            output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW106_OUT")??"../Verification/Evidence/Review106");Directory.CreateDirectory(Path.Combine(output,"Native","GoalOptics106"));report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
            int locale=GameLocale.Current;bool had=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int saved=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);
            string profiles=Path.Combine(Application.persistentDataPath,"Profiles"),server=Path.Combine(Application.persistentDataPath,"ServerReview"),beforeProfiles=Tree(profiles),beforeServer=Tree(server),settings=Digest("ProjectSettings/ProjectSettings.asset");Application.logMessageReceived+=Log;
            try {
                Check(Application.unityVersion=="2022.3.62f3","Pinned main editor engine");EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");Check(assets&&assets.boards&&assets.boards.levels.Length==50,"Actual active Chapter1 M48 UI and fifty boards");
                foreach(string family in Families)Case("Source alpha "+family,()=>Source(family));
                GameLocale.Select(4);
                foreach(var size in new[]{new Vector2Int(720,1600),new Vector2Int(360,800),new Vector2Int(768,1024)})foreach(int slots in Enumerable.Range(1,4))foreach(int family in Enumerable.Range(0,Families.Length)){
                    int start=family;Case("Actual HUD "+size+" "+slots+" "+Families[start],()=>Layout(start,slots,size));
                }
                foreach(var resource in assets.boards.levels)Case("Campaign "+resource.name,()=>{
                    string raw=resource.text;var level=JsonUtility.FromJson<LevelData>(raw);Check(level.goals.Length>=1&&level.goals.Length<=4,"Actual campaign retains1–4 objective slots");
                    using(var f=new Fixture(assets,level.goals,720,1600,new Rect(0,0,720,1600))){Geometry(f);Check(f.Counters.Select(v=>v.text).SequenceEqual(level.goals.Select(v=>v.count==0?"\u2713":v.count.ToString())),"Actual campaign goal counts preserved");}
                    Check(resource.text==raw,"Campaign definitions/masks/counts remain byte-identical");report.levels++;
                });
                foreach(int language in Enumerable.Range(0,5))Case("Localized header "+language,()=>{GameLocale.Select(language);using(var f=new Fixture(assets,Goals(0,4),360,800,new Rect(0,24,360,744))){Geometry(f);Check(f.canvas.GetComponentsInChildren<Text>().All(v=>!v.text.Contains("<size=")),"Existing header text is retained without new markup");}});
            }catch(Exception e){report.errors.Add(e.ToString());}
            finally {
                GameLocale.Select(locale);Case("Preservation",()=>{report.profilesPreserved=Tree(profiles)==beforeProfiles;report.serverReviewPreserved=Tree(server)==beforeServer;report.languagePreferencePreserved=PlayerPrefs.HasKey(GameLocale.PreferenceKey)==had&&PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue)==saved;report.settingsPreserved=Digest("ProjectSettings/ProjectSettings.asset")==settings;Check(report.profilesPreserved&&report.serverReviewPreserved&&report.languagePreferencePreserved&&report.settingsPreserved,"Ordinary profiles, protected journals, saved language and project settings preserved");});
                Application.logMessageReceived-=Log;report.status=report.errors.Count==0&&report.levels==50?"PASS_NATIVE_GOAL_OPTICS106":"FAIL_NATIVE_GOAL_OPTICS106";File.WriteAllText(Path.Combine(output,"Native","GoalOptics106.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));
            }
            EditorApplication.Exit(report.status=="PASS_NATIVE_GOAL_OPTICS106"?0:1);
        }
        static Goal[] Goals(int start,int count)=>Enumerable.Range(0,count).Select(i=>new Goal{family=Families[(start+i)%Families.Length],count=new[]{1,88,999,4}[i]}).ToArray();
        static void Source(string family){
            string id=GameplayHUD.GoalSprite(family);var sprite=assets.Get(id);Check(sprite,"Approved goal sprite is bound: "+family);string path=AssetDatabase.GetAssetPath(sprite);var importer=(TextureImporter)AssetImporter.GetAtPath(path);Check(!importer.isReadable,"Original goal texture stays non-readable");
            var texture=new Texture2D(2,2,TextureFormat.RGBA32,false,true);
            try{
                Check(texture.LoadImage(File.ReadAllBytes(path)),"Editor-only source alpha decoded without import mutation");var pixels=texture.GetPixels32();Rect bounds=Bounds(pixels,texture.width,texture.height);
                var normalized=new Rect(bounds.x/texture.width,1-bounds.yMax/texture.height,bounds.width/texture.width,bounds.height/texture.height);var actual=GoalIconLayout106.VisibleBounds(id);
                Check(Math.Abs(normalized.x-actual.x)<.00001f&&Math.Abs(normalized.y-actual.y)<.00001f&&Math.Abs(normalized.width-actual.width)<.00001f&&Math.Abs(normalized.height-actual.height)<.00001f,"Runtime optical constants match approved visible source alpha: "+family);report.sourceAssets++;
            }finally{UnityEngine.Object.DestroyImmediate(texture);}
        }
        static void Geometry(Fixture f){
            var roots=Field<Dictionary<string,RectTransform>>(f.hud,"goalRects");var header=Field<RectTransform>(f.hud,"header");
            Check(header.anchoredPosition==new Vector2(30,-38)&&header.sizeDelta==new Vector2(660,192),"Existing header bounds remain unchanged");
            Check(f.Panel.rectTransform.anchoredPosition==new Vector2(136,-44)&&f.Panel.rectTransform.sizeDelta==new Vector2(324,122),"Only sliced objective panel height extends120→122 within its existing painted backplate");
            var move=Field<Image>(f.hud,"movesPanel").rectTransform;Check(move.anchoredPosition==new Vector2(12,-44)&&move.sizeDelta==new Vector2(112,120),"Moves panel remains unchanged");
            var avatar=header.GetComponentsInChildren<Image>().Single(v=>v.name=="Avatar_Frame").rectTransform;Check(avatar.anchoredPosition==new Vector2(472,-6)&&avatar.sizeDelta==new Vector2(180,180),"Portrait remains unchanged");
            for(int i=0;i<f.goals.Length;i++){
                var goal=f.goals[i];var image=f.Icon(goal.family);var slot=(RectTransform)image.transform.parent;Check(slot.GetComponent<RectMask2D>()&&slot.rect.size==new Vector2(60,60),"Optical artwork is bounded in its own60px cell");
                Check(image.preserveAspect&&!image.raycastTarget&&Math.Abs(image.rectTransform.rect.width/image.rectTransform.rect.height-image.sprite.rect.width/image.sprite.rect.height)<.0001f,"Approved artwork keeps its imported aspect and never intercepts input");
                Check(Inside(slot,f.Panel.rectTransform)&&Inside(f.Counters[i].rectTransform,roots[goal.family]),"Icon cell and bounded count pulse remain in their designated objective space");
                Vector2 point;Check(f.hud.TryGoalScreenPoint(goal.family,out point)&&Vector2.Distance(point,RectTransformUtility.WorldToScreenPoint(null,slot.TransformPoint(slot.rect.center)))<.02f,"Collection target follows the optical cell center");
            }
        }
        static void Layout(int start,int slots,Vector2Int size){
            Rect area=size.x==360?new Rect(0,24,360,744):size.x==768?new Rect(0,24,768,976):new Rect(0,0,720,1600);var goals=Goals(start,slots);string original=JsonUtility.ToJson(new GoalWrapper{goals=goals});
            using(var f=new Fixture(assets,goals,size.x,size.y,area)){
                try{
                Geometry(f);Check(original==JsonUtility.ToJson(new GoalWrapper{goals=goals}),"HUD presentation preserves supplied goal counts/families");
                // All108 layouts exercise the actual component hierarchy/pulse.
                // GPU checks use three four-goal groups covering all nine art
                // families on each viewport, plus representative1–3 goal rows.
                bool gpu=slots==4&&(start==0||start==4||start==8)||size.x==720&&start==0;var panel=gpu?Render(f,f.Panel):null;var iconBounds=new List<Rect>();
                if(gpu){var backplate=f.canvas.GetComponentsInChildren<Image>().Single(v=>v.name=="Panel_Header");PanelInsideBackplate(f,panel,Render(f,backplate));}
                for(int i=0;gpu&&i<goals.Length;i++){
                    var data=Render(f,f.Icon(goals[i].family));var bounds=Bounds(data,f.width,f.height);float extent=Math.Max(bounds.width,bounds.height);Check(Math.Abs(extent-58*f.scale)<=Math.Max(2,2*f.scale),"Actual imported visible icon extent is uniformly58 logical pixels: "+goals[i].family);
                    Painted(f,data,bounds,panel,1,"Icon remains inside painted cream/frame interior");iconBounds.Add(bounds);
                    report.alpha.Add(new Row{family=goals[i].family,slots=slots,width=f.width,height=f.height,icon=bounds,physicalScale=f.scale});
                }
                for(int i=0;i<iconBounds.Count;i++)for(int j=i+1;j<iconBounds.Count;j++)Check(!Overlap(iconBounds[i],iconBounds[j]),"Adjacent visible objective icons remain separate");
                for(int state=0;state<2;state++){
                    f.Peak(state==1);Geometry(f);var countBounds=new List<Rect>();
                    for(int i=0;i<goals.Length;i++){
                        var counter=f.Counters[i];Check(Math.Abs(counter.rectTransform.localScale.x-1.16f)<.002f,"Existing count pulse is verified at its actual peak");
                        if(state==1)Check(counter.text=="\u2713"&&counter.font.HasCharacter('\u2713'),"Completed objective uses a supported check glyph");
                        if(!gpu)continue;
                        var data=Render(f,counter);var bounds=Bounds(data,f.width,f.height);Painted(f,data,bounds,panel,2,"Pulsing count/check stays clear of the actual lower bevel/shadow");countBounds.Add(bounds);
                        foreach(var icon in iconBounds)Check(!Overlap(bounds,icon),"Actual count/check glyph never overlaps any visible goal artwork");
                        float gap=iconBounds[i].yMin-bounds.yMax;Check(gap>=Math.Min(1,f.scale),"Visible icon and actual count/check retain a clear peak gap; family="+goals[i].family+"; gapPixels="+gap+"; icon="+iconBounds[i]+"; glyph="+bounds);
                    }
                    for(int i=0;i<countBounds.Count;i++)for(int j=i+1;j<countBounds.Count;j++)Check(!Overlap(countBounds[i],countBounds[j]),"Adjacent goal counters remain separate at pulse peak");
                    if(state==0&&start==0&&slots==4&&(size.x==720||size.x==768))Capture(f,"Goals_ObstaclePeak_ru_"+size.x+".png");
                    if(state==0&&start==4&&slots==4&&size.x==720)Capture(f,"Goals_DeliveryPeak_ru_720.png");
                    if(state==1&&start==0&&slots==4&&size.x==360)Capture(f,"Goals_CompletedPeak_ru_360.png");
                }
                report.layouts++;if(gpu)report.gpuLayouts++;
                }catch{
                    if(!report.failureCaptured){report.failureCaptured=true;try{Capture(f,"Goals_FirstFailure.png");}catch(Exception capture){report.errors.Add("First failure capture: "+capture.GetType().Name);}}
                    throw;
                }
            }
        }
        [Serializable] sealed class GoalWrapper {public Goal[] goals;}
        static bool Overlap(Rect a,Rect b)=>Math.Min(a.xMax,b.xMax)-Math.Max(a.xMin,b.xMin)>.1f&&Math.Min(a.yMax,b.yMax)-Math.Max(a.yMin,b.yMin)>.1f;
        static bool Inside(RectTransform inner,RectTransform outer){var points=new Vector3[4];inner.GetWorldCorners(points);return points.All(v=>{Vector3 p=outer.InverseTransformPoint(v);return p.x>=outer.rect.xMin-.02f&&p.x<=outer.rect.xMax+.02f&&p.y>=outer.rect.yMin-.02f&&p.y<=outer.rect.yMax+.02f;});}
        static Rect Bounds(Color32[] data,int width,int height){int left=width,right=-1,bottom=height,top=-1;for(int y=0;y<height;y++)for(int x=0;x<width;x++)if(data[y*width+x].a>24){left=Math.Min(left,x);right=Math.Max(right,x);bottom=Math.Min(bottom,y);top=Math.Max(top,y);}Check(right>=left&&top>=bottom,"Actual native graphic paints visible alpha");return new Rect(left,bottom,right-left+1,top-bottom+1);}
        static bool Cream(Color32 p)=>p.a>220&&p.r>180&&p.g>160&&p.b>140&&p.r-p.g>=3&&p.g-p.b>=4;
        static void PanelInsideBackplate(Fixture f,Color32[] panel,Color32[] backplate){
            bool contained=true;int first=-1;for(int i=0;i<panel.Length;i++)if(panel[i].a>24){var p=backplate[i];bool blue=p.a>200&&p.g>=p.r+5&&p.b>=p.g+5;if(!blue&&contained)first=i;contained&=blue;}
            Check(contained,"Objective panel actual alpha stays inside the painted blue header; first failing framebuffer pixel="+(first<0?-1:first%f.width)+","+(first<0?-1:first/f.width)+"; panelRGBA="+(first<0?"none":panel[first].ToString())+"; backplateRGBA="+(first<0?"none":backplate[first].ToString()));
        }
        static void Painted(Fixture f,Color32[] graphic,Rect bounds,Color32[] panel,int margin,string label){
            bool contained=true;int failedX=-1,failedY=-1;Color32 failedPanel=default(Color32),failedGraphic=default(Color32);var offsets=new[]{new Vector2Int(0,0),new Vector2Int(-margin,0),new Vector2Int(margin,0),new Vector2Int(0,-margin),new Vector2Int(0,margin)};
            for(int y=(int)bounds.yMin;y<(int)bounds.yMax;y++)for(int x=(int)bounds.xMin;x<(int)bounds.xMax;x++)if(graphic[y*f.width+x].a>24){
                foreach(var delta in offsets){int px=x+delta.x,py=y+delta.y;bool inFrame=px>=0&&px<f.width&&py>=0&&py<f.height;bool valid=inFrame&&Cream(panel[py*f.width+px]);if(!valid&&contained){failedX=px;failedY=py;failedGraphic=graphic[y*f.width+x];if(inFrame)failedPanel=panel[py*f.width+px];}contained&=valid;}
            }
            Check(contained,label+"; first failing framebuffer pixel="+failedX+","+failedY+"; panelRGBA="+failedPanel+"; graphicRGBA="+failedGraphic);
        }
        static Color32[] Render(Fixture f,Graphic only=null,bool whole=false){
            var graphics=f.canvas.GetComponentsInChildren<Graphic>();var enabled=graphics.Select(v=>v.enabled).ToArray();var owner=new GameObject("106 exact native objective camera");var camera=owner.AddComponent<Camera>();camera.enabled=false;camera.orthographic=true;camera.orthographicSize=f.height/(2*f.scale);camera.aspect=f.width/(float)f.height;camera.transform.position=f.canvas.transform.position-new Vector3(0,0,10);camera.nearClipPlane=.1f;camera.farClipPlane=100;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=whole?new Color(.035f,.08f,.14f,1):Color.clear;
            var target=new RenderTexture(f.width,f.height,24);target.Create();var active=RenderTexture.active;var old=f.canvas.worldCamera;Texture2D pixels=null;
            try{if(only){foreach(var g in graphics)g.enabled=false;only.enabled=true;}camera.targetTexture=target;f.canvas.worldCamera=camera;Canvas.ForceUpdateCanvases();camera.Render();camera.Render();RenderTexture.active=target;pixels=new Texture2D(f.width,f.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,f.width,f.height),0,0);pixels.Apply();return pixels.GetPixels32();}
            finally{for(int i=0;i<graphics.Length;i++)graphics[i].enabled=enabled[i];f.canvas.worldCamera=old;camera.targetTexture=null;RenderTexture.active=active;if(pixels)UnityEngine.Object.DestroyImmediate(pixels);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(owner);Canvas.ForceUpdateCanvases();}
        }
        static void Capture(Fixture f,string file){var data=Render(f,null,true);var pixels=new Texture2D(f.width,f.height,TextureFormat.RGBA32,false);try{pixels.SetPixels32(data);pixels.Apply();File.WriteAllBytes(Path.Combine(output,"Native","GoalOptics106",file),pixels.EncodeToPNG());report.captures.Add("Native/GoalOptics106/"+file);}finally{UnityEngine.Object.DestroyImmediate(pixels);}}
        static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}
    }
}
#endif
