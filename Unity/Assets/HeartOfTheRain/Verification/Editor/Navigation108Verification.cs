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
using UnityEditor;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    // The 105 dimensions below are a controlled reconstruction of its exact
    // retained source, not a newly run old APK. Navigation106's proof remains
    // unchanged; its smaller blue-inset style was superseded by this request.
    public static class Navigation108Verification {
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static readonly string[] Names={"journey","leaderboard","home","teams","shop"};
        [Serializable] sealed class Row {public int width,height,locale,active;public float scale,offset,originalGap,newGap,groupCenter;public bool inset,compact,reduced;}
        [Serializable] sealed class Report {
            public string status="RUNNING",unity,utc;
            public string scope="Actual Editor shared layout, imported sprite meshes/alpha, UGUI labels, routes and interaction handlers in bounded navigation fixtures. Exact105 dimension reconstruction is source-controlled; original105 selected-frame protrusion is intentional. Compact under320 logical-width fallback retains106 bounds. No Android/APK/device, backend, impression, full-page extreme-scale acceptance or whole-app visual certification.";
            public int checks,cases;public bool ordinaryProfilesPreserved,serverReviewPreserved,languagePreferencePreserved;
            public List<Row> rows=new List<Row>();public List<string> captures=new List<string>(),errors=new List<string>();
        }
        static Report report;static HomePageAssets assets;static string output;
        static readonly Dictionary<string,Rect> alpha=new Dictionary<string,Rect>();
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        static bool Near(float a,float b,float tolerance=.025f)=>Math.Abs(a-b)<=tolerance;
        static RectTransform Node(string name,Transform parent,float x,float y,float w,float h){var r=(RectTransform)new GameObject(name,typeof(RectTransform)).transform;r.SetParent(parent,false);r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);return r;}
        static Rect Bounds(RectTransform r,RectTransform root){var corners=new Vector3[4];r.GetWorldCorners(corners);var p=corners.Select(v=>root.InverseTransformPoint(v)).ToArray();return Rect.MinMaxRect(p.Min(v=>v.x),-p.Max(v=>v.y),p.Max(v=>v.x),-p.Min(v=>v.y));}
        static bool Contains(Rect a,Rect b,float tolerance=.2f)=>b.xMin>=a.xMin-tolerance&&b.xMax<=a.xMax+tolerance&&b.yMin>=a.yMin-tolerance&&b.yMax<=a.yMax+tolerance;
        static Rect Alpha(Sprite sprite){
            string path=AssetDatabase.GetAssetPath(sprite);if(alpha.TryGetValue(path,out var found))return found;var t=new Texture2D(2,2,TextureFormat.RGBA32,false);
            try{Check(t.LoadImage(File.ReadAllBytes(path)),"Unchanged approved PNG decoded");var p=t.GetPixels32();int l=t.width,r=0,b=t.height,u=0;
                for(int y=0;y<t.height;y++)for(int x=0;x<t.width;x++)if(p[y*t.width+x].a>24){l=Math.Min(l,x);r=Math.Max(r,x+1);b=Math.Min(b,y);u=Math.Max(u,y+1);}
                Check(r>l&&u>b,"Approved artwork has visible alpha");found=Rect.MinMaxRect(l/(float)t.width,b/(float)t.height,r/(float)t.width,u/(float)t.height);alpha[path]=found;return found;
            }finally{UnityEngine.Object.DestroyImmediate(t);}
        }
        static Rect Painted(Image image,RectTransform root){
            var mesh=image.canvasRenderer.GetMesh();Check(mesh&&mesh.vertexCount>=4,"Actual UGUI sprite mesh exists");var v=mesh.vertices;var uv=mesh.uv;Rect a=Alpha(image.sprite);
            float xl=v.Min(p=>p.x),xr=v.Max(p=>p.x),yb=v.Min(p=>p.y),yt=v.Max(p=>p.y),ul=uv.Min(p=>p.x),ur=uv.Max(p=>p.x),ub=uv.Min(p=>p.y),ut=uv.Max(p=>p.y);
            var points=new[]{new Vector2(a.xMin,a.yMin),new Vector2(a.xMax,a.yMin),new Vector2(a.xMin,a.yMax),new Vector2(a.xMax,a.yMax)}.Select(p=>root.InverseTransformPoint(image.transform.TransformPoint(new Vector3(Mathf.LerpUnclamped(xl,xr,(p.x-ul)/(ur-ul)),Mathf.LerpUnclamped(yb,yt,(p.y-ub)/(ut-ub)),0)))).ToArray();
            return Rect.MinMaxRect(points.Min(p=>p.x),-points.Max(p=>p.y),points.Max(p=>p.x),-points.Min(p=>p.y));
        }
        static string Digest(string path){if(!Directory.Exists(path))return "Absent";using(var sha=SHA256.Create()){string rows=string.Join("\n",Directory.GetFiles(path,"*",SearchOption.AllDirectories).OrderBy(p=>p,StringComparer.Ordinal).Select(p=>p.Substring(path.Length)+":"+BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(p)))));return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(rows)));}}
        static void Geometry(HomeFrame frame,float width,float height,int active){
            float w=MainNavigationLayout.Width(width,height),h=MainNavigationLayout.Height(width,height),x=(width-w)/2,y=height-MainNavigationLayout.BottomInset(width,height)-h,dy=Math.Min(4,Math.Max(0,height-y-h));
            var byId=frame.elements.ToDictionary(e=>e.id);var dock=byId["dock-bg"];
            Check(Near(dock.x,x)&&Near(dock.y,y+dy+h*.22f)&&Near(dock.width,w)&&Near(dock.height,h*.78f),"Original105 dock dimensions with only bounded downward offset");
            if(w<320){Check(frame.elements.All(e=>e.width>0&&e.height>0),"Compact106 fallback has no negative original-size boxes");return;}
            float cw=w/5,s=Math.Min(cw-22,Math.Min(h*.5f,h-44)),pw=Math.Min(cw,h*.9f);var icons=Names.Select(n=>byId["nav-"+n+"-icon"]).ToArray();
            Check(Near((icons[0].x+icons[4].x+s)/2,x+w/2),"Original-size visual group remains horizontally centered");
            for(int i=0;i<5;i++){
                var icon=icons[i];var plate=byId["nav-"+Names[i]+"-plate"];var label=byId["nav-"+Names[i]+"-label"];var hit=byId["nav-"+Names[i]];
                Check(Near(icon.width,s)&&Near(icon.height,s)&&icon.preserveAspect&&Near(icon.y,y+dy+(i==active?18:30)),"Exact105 icon dimensions and selected vertical relationship "+i);
                Check(Near(plate.width,pw)&&Near(plate.height,h)&&!plate.preserveAspect&&Near(plate.y,y+dy),"Exact105 selected-frame size and original style "+i);
                Check(Near(label.width,pw*.78f)&&Near(label.height,18)&&Near(label.y,y+dy+h-26)&&label.fontSize==(pw<90?12:14),"Exact105 label box/font sizing "+i);
                Check(Near(hit.x,x+i*cw)&&Near(hit.y,y+dy)&&Near(hit.width,cw)&&Near(hit.height,h)&&hit.action==Names[i],"Original fixed full-size hit column and action "+i);
                Check(Near(icon.x+s/2,plate.x+pw/2)&&Near(icon.x+s/2,label.x+label.width/2),"Each original-size item shares its centered visual axis "+i);
                if(i>0)Check(Near(icon.x-(icons[i-1].x+s),.95f*(cw-s)),"Each intervening original icon-footprint gap is exactly95percent "+i);
            }
        }
        static void Case(Vector2Int size,float scale,bool inset,int active,bool reduced){
            var owner=new GameObject("Navigation108 isolated UGUI fixture",typeof(RectTransform));
            try{
                var canvas=owner.AddComponent<Canvas>();canvas.renderMode=RenderMode.WorldSpace;var root=(RectTransform)owner.transform;root.pivot=new Vector2(0,1);root.sizeDelta=size;root.position=new Vector3(-size.x/2f,size.y/2f,0);
                var bg=Node("Fixture background",root,0,0,size.x,size.y).gameObject.AddComponent<Image>();bg.color=new Color(.025f,.09f,.16f);bg.raycastTarget=false;
                float left=inset?18:0,right=inset?24:0,top=inset?46:0,bottom=inset?34:0,width=(size.x-left-right)/scale,height=(size.y-top-bottom)/scale;
                var safe=Node("Safe mask",root,left,top,width,height);safe.localScale=Vector3.one*scale;safe.gameObject.AddComponent<RectMask2D>();float fw=Math.Max(320,width),fh=Math.Max(568,height);var chrome=Node("Minimum chrome",safe,0,0,fw,fh);
                var frame=new HomeFrame();MainNavigationLayout.AddDock(frame,fw,fh,active);Geometry(frame,fw,fh,active);Check(frame.width==fw&&frame.height==fh,"AddDock supplies dimensions for formerly empty chrome callers");
                var nodes=new Dictionary<string,RectTransform>();string clicked=null;
                foreach(var e in frame.elements){var r=Node(e.id,chrome,e.x,e.y,e.width,e.height);nodes[e.id]=r;
                    if(e.kind=="group"){var g=r.gameObject.AddComponent<Image>();g.color=Color.clear;var b=r.gameObject.AddComponent<Button>();b.targetGraphic=g;b.transition=Selectable.Transition.None;string action=e.action;b.onClick.AddListener(()=>clicked=action);var a=r.gameObject.AddComponent<HomeControlLabel>();a.action=action;a.label=e.label;}
                    else if(e.kind=="text"){var t=r.gameObject.AddComponent<Text>();t.font=assets.boldFont;t.text=e.text;t.fontSize=e.fontSize;t.alignment=TextAnchor.MiddleCenter;t.horizontalOverflow=HorizontalWrapMode.Overflow;t.verticalOverflow=VerticalWrapMode.Truncate;t.supportRichText=false;t.raycastTarget=false;ColorUtility.TryParseHtmlString(e.color,out var c);t.color=c;LabelFit.Apply(t,e.width,e.height,9);if(e.shadow){var sh=r.gameObject.AddComponent<Shadow>();sh.effectDistance=new Vector2(0,-1);}}
                    else{var im=r.gameObject.AddComponent<Image>();im.sprite=assets.Find(e.asset);im.type=Image.Type.Simple;im.preserveAspect=e.preserveAspect;ColorUtility.TryParseHtmlString(e.color,out var c);im.color=c;im.raycastTarget=false;SpriteFit.Center(im);}
                }
                MainNavigationFeedback.Bind(nodes,reduced);Canvas.ForceUpdateCanvases();var viewport=new Rect(0,0,width,height);var bounds=Names.Select(n=>Bounds(nodes["nav-"+n],safe)).ToArray();var iconRects=Names.Select(n=>Bounds(nodes["nav-"+n+"-icon"],safe)).ToArray();
                Check(Contains(viewport,Painted(nodes["dock-bg"].GetComponent<Image>(),safe)),"Actual dock alpha remains inside the supplied safe viewport");
                bool compact=MainNavigationLayout.Width(width,height)<320;float h=MainNavigationLayout.Height(width,height),w=MainNavigationLayout.Width(width,height),s=Math.Min(w/5-22,Math.Min(h*.5f,h-44));
                for(int i=0;i<5;i++){
                    string id="nav-"+Names[i];var hit=nodes[id];var icon=nodes[id+"-icon"].GetComponent<Image>();var painted=Painted(icon,safe);var plate=nodes[id+"-plate"];
                    Check(Contains(viewport,bounds[i])&&Contains(bounds[i],painted),"Actual full touch column and opaque icon remain safe "+i);
                    Check(Contains(viewport,Bounds(plate,safe)),"Original selected-frame protrusion fits full reserved safe region "+i);
                    if(!compact){Check(Near(iconRects[i].width,s)&&Near(iconRects[i].height,s),"Renderer retains exact105 normal icon box "+i);if(i>0)Check(Near(iconRects[i].xMin-iconRects[i-1].xMax,.95f*(w/5-s)),"Renderer retains exact5percent footprint-gap reduction "+i);}
                    var label=nodes[id+"-label"].GetComponent<Text>();if(label.color.a>.5f&&label.text.Length>0){Check(label.preferredWidth<=label.rectTransform.rect.width+.1f&&label.preferredHeight<=label.rectTransform.rect.height+.1f,"Actual selected locale label fits original-size box");var mesh=label.canvasRenderer.GetMesh();Check(mesh&&mesh.vertexCount>0,"Selected label has actual glyphs");var points=mesh.vertices.Select(p=>safe.InverseTransformPoint(label.transform.TransformPoint(p))).ToArray();var glyphs=Rect.MinMaxRect(points.Min(p=>p.x),-points.Max(p=>p.y),points.Max(p=>p.x),-points.Min(p=>p.y));Check(Contains(viewport,glyphs)&&glyphs.yMin>=painted.yMax-.15f,"Original-size selected icon and actual glyphs remain separated and safe");}
                    var before=Bounds(hit,safe);var plateBefore=Bounds(plate,safe);var center=painted.center;var feedback=hit.GetComponent<MainNavigationFeedback>();feedback.OnPointerDown(new PointerEventData(EventSystem.current));typeof(MainNavigationFeedback).GetField("amount",Private).SetValue(feedback,1f);typeof(MainNavigationFeedback).GetMethod("LateUpdate",Private).Invoke(feedback,null);Canvas.ForceUpdateCanvases();
                    Check(Bounds(hit,safe)==before&&Bounds(plate,safe)==plateBefore,"Press does not shift fixed hit region or original selected frame "+i);Check(Vector2.Distance(Painted(icon,safe).center,center)<.15f,"Tap feedback preserves centered artwork "+i);Check(Contains(before,Painted(icon,safe)),"Tap animation remains inside full-size target "+i);
                    feedback.OnPointerUp(null);feedback.enabled=false;hit.GetComponent<Button>().onClick.Invoke();Check(clicked==Names[i]&&hit.GetComponent<HomeControlLabel>().action==Names[i],"Original action/accessibility route retained "+i);
                }
                Check(bounds.All(r=>Near(r.width,bounds[0].width))&&Names.All(n=>nodes["nav-"+n].GetComponents<MainNavigationFeedback>().Length==1),"Five stable touch columns and one feedback handler each");
                var previous=Names.Select(n=>Bounds(nodes["nav-"+n+"-icon"],safe)).ToArray();MainNavigationFeedback.Bind(nodes,reduced);Canvas.ForceUpdateCanvases();Check(Names.Select((n,i)=>Bounds(nodes["nav-"+n+"-icon"],safe)==previous[i]).All(v=>v),"Repeated binding does not compound viewport fitting or spacing");
                report.rows.Add(new Row{width=size.x,height=size.y,locale=GameLocale.Current,active=active,scale=scale,inset=inset,reduced=reduced,compact=compact,offset=Math.Min(4,MainNavigationLayout.BottomInset(width,height)),originalGap=compact?0:w/5-s,newGap=compact?0:.95f*(w/5-s),groupCenter=(iconRects[0].xMin+iconRects[4].xMax)/2});report.cases++;
                if(GameLocale.Current==4&&active==2&&!inset&&scale==1&&(size.x==393||size.x==768))Capture(canvas,size,"Navigation108_ru_"+size.x+".png");
            }finally{UnityEngine.Object.DestroyImmediate(owner);}
        }
        static void SharedAndClamp(){
            var unavailable=HomeLayoutEngine.Build(393,852,new HomeState{walletUnavailable=true});
            Check(unavailable.elements.Single(e=>e.id=="coin-count").text=="\u2014"&&unavailable.elements.Single(e=>e.id=="life-count").text=="\u2014/5","Unavailable server wallet is not presented as zero coins or depleted lives");
            Check(unavailable.elements.Single(e=>e.id=="start-label").text.Contains("\u2014")&&unavailable.elements.Single(e=>e.id=="progress-count").text=="\u2014 / 50"&&unavailable.elements.Single(e=>e.id=="progress-fill").width==0,"Unknown progress is not presented as Level 1");
            foreach(var size in new[]{new Vector2(393,852),new Vector2(768,1024)}){
                var home=HomeLayoutEngine.Build(size.x,size.y,new HomeState());var shared=new HomeFrame();MainNavigationLayout.AddDock(shared,size.x,size.y,2);
                foreach(var e in shared.elements){var actual=home.elements.Single(v=>v.id==e.id);Check(Near(actual.x,e.x)&&Near(actual.y,e.y)&&Near(actual.width,e.width)&&Near(actual.height,e.height),"Actual Home and shared page dock geometry match "+e.id);}
            }
            foreach(float remaining in new[]{0f,1f,3f,4f,20f}){var frame=new HomeFrame{width=393,height=852};MainNavigationLayout.Add(frame,0,852-100-remaining,393,100,2);var hit=frame.elements.Single(v=>v.id=="nav-home");Check(Near(hit.y,852-100-remaining+Math.Min(4,remaining))&&hit.y+hit.height<=852.001f,"Downward movement consumes only the actual remaining safe-bottom inset");}
        }
        static void Capture(Canvas canvas,Vector2Int size,string file){
            var owner=new GameObject("Navigation108 bounded offscreen camera");var camera=owner.AddComponent<Camera>();camera.enabled=false;camera.orthographic=true;camera.orthographicSize=size.y/2f;camera.aspect=size.x/(float)size.y;camera.transform.position=new Vector3(0,0,-10);camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.magenta;camera.nearClipPlane=.1f;camera.farClipPlane=100;
            var target=new RenderTexture(size.x,size.y,24);target.Create();var previous=RenderTexture.active;Texture2D pixels=null;
            try{camera.targetTexture=target;canvas.worldCamera=camera;Canvas.ForceUpdateCanvases();camera.Render();camera.Render();RenderTexture.active=target;pixels=new Texture2D(size.x,size.y,TextureFormat.RGB24,false);pixels.ReadPixels(new Rect(0,0,size.x,size.y),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(output,file),pixels.EncodeToPNG());report.captures.Add(file);}
            finally{camera.targetTexture=null;RenderTexture.active=previous;if(pixels)UnityEngine.Object.DestroyImmediate(pixels);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(owner);}
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW108_OUT")??"../Verification/Evidence/Review108/Native");Directory.CreateDirectory(output);
            bool had=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int saved=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue),locale=GameLocale.Current;string p=null,s=null;GameObject events=null;
            try{
                p=Digest(Path.Combine(Application.persistentDataPath,"Profiles"));s=Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));Check(Application.unityVersion=="2022.3.62f3","Pinned Editor retained");assets=AssetDatabase.LoadAssetAtPath<HomePageAssets>("Assets/HeartOfTheRain/App/Home/HomePageAssets.asset");Check(assets,"Approved navigation artwork and fonts available");events=new GameObject("Navigation108 events");events.AddComponent<EventSystem>();SharedAndClamp();
                foreach(int language in Enumerable.Range(0,5)){GameLocale.Select(language);foreach(var size in new[]{new Vector2Int(393,852),new Vector2Int(768,1024)})foreach(int active in Enumerable.Range(0,5))Case(size,1,false,active,active%2==0);}
                GameLocale.Select(4);foreach(int active in Enumerable.Range(0,5)){Case(new Vector2Int(393,852),1,true,active,false);Case(new Vector2Int(720,1600),1,false,active,true);Case(new Vector2Int(320,568),2.5f,false,active,false);Case(new Vector2Int(393,852),5,true,active,true);}
                report.status="PASS_NATIVE_NAVIGATION108";
            }catch(Exception e){report.errors.Add(e.ToString());}
            finally{
                GameLocale.Select(locale);if(events)UnityEngine.Object.DestroyImmediate(events);report.ordinaryProfilesPreserved=p!=null&&p==Digest(Path.Combine(Application.persistentDataPath,"Profiles"));report.serverReviewPreserved=s!=null&&s==Digest(Path.Combine(Application.persistentDataPath,"ServerReview"));report.languagePreferencePreserved=PlayerPrefs.HasKey(GameLocale.PreferenceKey)==had&&PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue)==saved;
                if(!report.ordinaryProfilesPreserved||!report.serverReviewPreserved||!report.languagePreferencePreserved)report.errors.Add("Ordinary profile/journals/exact locale changed");if(report.errors.Count>0)report.status="FAIL_NATIVE_NAVIGATION108";File.WriteAllText(Path.Combine(output,"Navigation108.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));
            }
            if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif
