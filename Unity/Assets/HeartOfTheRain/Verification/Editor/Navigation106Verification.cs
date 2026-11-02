#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    // Real UGUI geometry/meshes and unchanged source PNG alpha. The canvas is
    // an isolated nav fixture, not an Android screen or a live social page.
    public static class Navigation106Verification {
        static readonly string[] Names={"journey","leaderboard","home","teams","shop"};
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Row {public int width,height,active,locale;public float scale;public bool inset,reduced;public float iconCenterSpread;}
        [Serializable] sealed class FailurePixel {public string check,asset;public int x,y,r,g,b,a,meshVertices,rowBlueLeft,rowBlueRight;public Rect painted,panel;public Vector2 uv;}
        [Serializable] sealed class FailureLabel {public string id,text;public int fontSize,meshVertices;public float preferredWidth,preferredHeight;public Rect box,glyphs;}
        [Serializable] sealed class Report {
            public string status="FAIL_NATIVE_NAVIGATION106",unity,scope="Actual pinned Editor UGUI nav fixtures, source PNG alpha mapped through CanvasRenderer meshes, shared layout and interaction handlers. Synthetic viewport/safe inset/scale fixtures only; not device, APK, gameplay, backend or full-page visual acceptance.";
            public int checks,cases;public List<Row> rows=new List<Row>();public List<string> errors=new List<string>(),captures=new List<string>();
            public Row failedCase;public FailurePixel failedPixel;public List<FailureLabel> failedLabels=new List<FailureLabel>();
            public string blueMaskRule="Source row span between strong-blue pixels (A>128,B>R+20,B>G+10); sampled pixels must remain inside that span with A>128 and B>=R and B>=G. This admits enclosed pale cyan highlights and rejects warm gold, transparency and outside coordinates.";
        }
        static Report report;static string output;static HomePageAssets assets;
        static readonly Dictionary<string,Rect> alpha=new Dictionary<string,Rect>();
        static readonly Dictionary<string,Color32[]> colours=new Dictionary<string,Color32[]>();
        static readonly Dictionary<string,Vector2Int> pixelSizes=new Dictionary<string,Vector2Int>();
        static readonly Dictionary<string,Vector2Int[]> blueRows=new Dictionary<string,Vector2Int[]>();
        static void Check(bool ok,string code){report.checks++;if(!ok)throw new InvalidOperationException(code);}
        static RectTransform RectNode(string name,Transform parent,float x,float y,float w,float h){var go=new GameObject(name,typeof(RectTransform));var r=(RectTransform)go.transform;r.SetParent(parent,false);r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);return r;}
        static Rect Bounds(RectTransform value,RectTransform root){var corners=new Vector3[4];value.GetWorldCorners(corners);var p=corners.Select(v=>root.InverseTransformPoint(v)).ToArray();return Rect.MinMaxRect(p.Min(v=>v.x),-p.Max(v=>v.y),p.Max(v=>v.x),-p.Min(v=>v.y));}
        static bool Contains(Rect outer,Rect inner,float pad=0)=>inner.xMin>=outer.xMin+pad-.05f&&inner.xMax<=outer.xMax-pad+.05f&&inner.yMin>=outer.yMin+pad-.05f&&inner.yMax<=outer.yMax-pad+.05f;
        static Rect Alpha(Sprite sprite){
            string path=AssetDatabase.GetAssetPath(sprite);if(alpha.TryGetValue(path,out var cached))return cached;
            var t=new Texture2D(2,2,TextureFormat.RGBA32,false);try{
                Check(t.LoadImage(File.ReadAllBytes(path)),"decode_approved_png");var pixels=t.GetPixels32();int left=t.width,right=0,bottom=t.height,top=0;
                for(int y=0;y<t.height;y++)for(int x=0;x<t.width;x++)if(pixels[y*t.width+x].a>24){left=Math.Min(left,x);right=Math.Max(right,x+1);bottom=Math.Min(bottom,y);top=Math.Max(top,y+1);}
                Check(right>left&&top>bottom,"visible_source_alpha");colours[path]=pixels;pixelSizes[path]=new Vector2Int(t.width,t.height);cached=Rect.MinMaxRect(left/(float)t.width,bottom/(float)t.height,right/(float)t.width,top/(float)t.height);alpha[path]=cached;return cached;
            }finally{UnityEngine.Object.DestroyImmediate(t);}
        }
        static Vector2Int[] BlueRows(string path){
            if(blueRows.TryGetValue(path,out var rows))return rows;var size=pixelSizes[path];var pixels=colours[path];rows=new Vector2Int[size.y];
            for(int y=0;y<size.y;y++){
                int left=size.x,right=-1;for(int x=0;x<size.x;x++){Color32 c=pixels[y*size.x+x];if(c.a>128&&c.b>c.r+20&&c.b>c.g+10){left=Math.Min(left,x);right=Math.Max(right,x);}}
                rows[y]=new Vector2Int(left,right);
            }
            blueRows[path]=rows;return rows;
        }
        static bool InsideBlue(string path,int x,int y){
            var size=pixelSizes[path];if(x<0||y<0||x>=size.x||y>=size.y)return false;var span=BlueRows(path)[y];Color32 c=colours[path][y*size.x+x];
            return x>=span.x&&x<=span.y&&c.a>128&&c.b>=c.r&&c.b>=c.g;
        }
        static void MaskControls(){
            foreach(string name in new[]{"R3_Dock","Nav_Active"}){
                var sprite=assets.Find(name);Alpha(sprite);string path=AssetDatabase.GetAssetPath(sprite);var pixels=colours[path];var size=pixelSizes[path];
                int gold=Array.FindIndex(pixels,c=>c.a>220&&c.r>c.b+80&&c.r>c.g+20),clear=Array.FindIndex(pixels,c=>c.a<=24);
                Check(gold>=0&&!InsideBlue(path,gold%size.x,gold/size.x),"real_warm_gold_is_not_interior_"+name);
                Check(clear>=0&&!InsideBlue(path,clear%size.x,clear/size.x),"real_transparent_edge_is_not_interior_"+name);
                Check(!InsideBlue(path,-1,0)&&!InsideBlue(path,size.x,size.y),"outside_source_is_not_interior_"+name);
                Check(InsideBlue(path,size.x/2,size.y/2),"real_central_sapphire_is_interior_"+name);
            }
            string dock=AssetDatabase.GetAssetPath(assets.Find("R3_Dock"));var cyan=colours[dock][157*pixelSizes[dock].x+56];
            Check(cyan.r==237&&cyan.g==252&&cyan.b==255&&cyan.a==253,"known_pale_cyan_source_pixel_retained");
            Check(InsideBlue(dock,56,157),"enclosed_pale_cyan_is_usable_interior");
        }
        static void BlueInterior(Image panel,RectTransform root,Rect painted,string name){
            Alpha(panel.sprite);string path=AssetDatabase.GetAssetPath(panel.sprite);var pixels=colours[path];var size=pixelSizes[path];var mesh=panel.canvasRenderer.GetMesh();var vertices=mesh.vertices;var uv=mesh.uv;
            float xl=vertices.Min(v=>v.x),xr=vertices.Max(v=>v.x),yb=vertices.Min(v=>v.y),yt=vertices.Max(v=>v.y),ul=uv.Min(v=>v.x),ur=uv.Max(v=>v.x),ub=uv.Min(v=>v.y),ut=uv.Max(v=>v.y);
            foreach(float x in new[]{painted.xMin,painted.center.x,painted.xMax})foreach(float y in new[]{painted.yMin,painted.center.y,painted.yMax}){
                Vector3 point=panel.transform.InverseTransformPoint(root.TransformPoint(new Vector3(x,-y,0)));
                float u=Mathf.LerpUnclamped(ul,ur,(point.x-xl)/(xr-xl)),v=Mathf.LerpUnclamped(ub,ut,(point.y-yb)/(yt-yb));
                Check(u>=0&&u<=1&&v>=0&&v<=1,"art_inside_panel_native_uv_"+name);int px=Mathf.Clamp(Mathf.FloorToInt(u*size.x),0,size.x-1),py=Mathf.Clamp(Mathf.FloorToInt(v*size.y),0,size.y-1);Color32 c=pixels[py*size.x+px];
                bool blue=InsideBlue(path,px,py);var span=BlueRows(path)[py];
                if(!blue&&report.failedPixel==null)report.failedPixel=new FailurePixel{check=name,asset=path,x=px,y=py,r=c.r,g=c.g,b=c.b,a=c.a,meshVertices=mesh.vertexCount,rowBlueLeft=span.x,rowBlueRight=span.y,painted=painted,panel=Bounds(panel.rectTransform,root),uv=new Vector2(u,v)};
                Check(blue,"painted_art_clears_actual_gold_border_"+name+"_"+px+"_"+py);
            }
        }
        static Rect Glyphs(Text text,RectTransform root){
            var mesh=text.canvasRenderer.GetMesh();Check(mesh&&mesh.vertexCount>0,"actual_selected_label_mesh");var vertices=mesh.vertices;var points=vertices.Select(v=>root.InverseTransformPoint(text.transform.TransformPoint(v))).ToArray();return Rect.MinMaxRect(points.Min(v=>v.x),-points.Max(v=>v.y),points.Max(v=>v.x),-points.Min(v=>v.y));
        }
        static Rect Painted(Image image,RectTransform root){
            var mesh=image.canvasRenderer.GetMesh();Check(mesh&&mesh.vertexCount>=4,"actual_native_mesh");var vertices=mesh.vertices;var uv=mesh.uv;Rect a=Alpha(image.sprite);
            float ul=uv.Min(v=>v.x),ur=uv.Max(v=>v.x),ub=uv.Min(v=>v.y),ut=uv.Max(v=>v.y),xl=vertices.Min(v=>v.x),xr=vertices.Max(v=>v.x),yb=vertices.Min(v=>v.y),yt=vertices.Max(v=>v.y);
            Check(ur>ul&&ut>ub&&a.xMin>=ul-.002f&&a.xMax<=ur+.002f&&a.yMin>=ub-.002f&&a.yMax<=ut+.002f,"source_alpha_inside_native_uv");
            var points=new[]{new Vector2(a.xMin,a.yMin),new Vector2(a.xMax,a.yMin),new Vector2(a.xMin,a.yMax),new Vector2(a.xMax,a.yMax)}.Select(v=>root.InverseTransformPoint(image.transform.TransformPoint(new Vector3(Mathf.LerpUnclamped(xl,xr,(v.x-ul)/(ur-ul)),Mathf.LerpUnclamped(yb,yt,(v.y-ub)/(ut-ub)),0)))).ToArray();
            return Rect.MinMaxRect(points.Min(v=>v.x),-points.Max(v=>v.y),points.Max(v=>v.x),-points.Min(v=>v.y));
        }
        static void RunCase(Vector2Int size,float scale,bool inset,int active,bool reduced){
            var owner=new GameObject("Navigation106 disposable UGUI fixture",typeof(RectTransform));Canvas canvas=null;RectTransform safe=null;Dictionary<string,RectTransform> nodes=null;
            try{
                canvas=owner.AddComponent<Canvas>();canvas.renderMode=RenderMode.WorldSpace;var root=(RectTransform)canvas.transform;root.pivot=new Vector2(0,1);root.sizeDelta=size;root.position=new Vector3(-size.x/2f,size.y/2f,0);root.localScale=Vector3.one;
                var background=RectNode("Fixture background",root,0,0,size.x,size.y).gameObject.AddComponent<Image>();background.color=new Color(.025f,.09f,.16f);background.raycastTarget=false;
                float left=inset?18:0,right=inset?24:0,top=inset?46:0,bottom=inset?34:0;
                float width=(size.x-left-right)/scale,height=(size.y-top-bottom)/scale;
                safe=RectNode("Actual safe mask",root,left,top,width,height);safe.localScale=Vector3.one*scale;safe.gameObject.AddComponent<RectMask2D>();
                float frameW=Math.Max(320,width),frameH=Math.Max(568,height);var chrome=RectNode("Minimum layout chrome",safe,0,0,frameW,frameH);
                var model=new HomeFrame{width=frameW,height=frameH};MainNavigationLayout.AddDock(model,frameW,frameH,active);
                nodes=new Dictionary<string,RectTransform>();string clicked=null;
                foreach(var e in model.elements){
                    var r=RectNode(e.id,chrome,e.x,e.y,e.width,e.height);nodes.Add(e.id,r);
                    if(e.kind=="group"){
                        var image=r.gameObject.AddComponent<Image>();image.color=Color.clear;var b=r.gameObject.AddComponent<Button>();b.targetGraphic=image;b.transition=Selectable.Transition.None;string action=e.action;b.onClick.AddListener(()=>clicked=action);
                        var accessible=r.gameObject.AddComponent<HomeControlLabel>();accessible.action=e.action;accessible.label=e.label;
                    }else if(e.kind=="text"){
                        var t=r.gameObject.AddComponent<Text>();t.font=assets.boldFont;t.text=e.text;t.fontSize=e.fontSize;t.alignment=TextAnchor.MiddleCenter;t.supportRichText=false;t.horizontalOverflow=HorizontalWrapMode.Overflow;t.verticalOverflow=VerticalWrapMode.Truncate;ColorUtility.TryParseHtmlString(e.color,out var color);t.color=color;t.raycastTarget=false;LabelFit.Apply(t,e.width,e.height,9);if(e.shadow){var shadow=r.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color(0,.035f,.08f,.9f);shadow.effectDistance=new Vector2(0,-1);}
                    }else{
                        var image=r.gameObject.AddComponent<Image>();image.sprite=assets.Find(e.asset);image.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;image.preserveAspect=e.preserveAspect;ColorUtility.TryParseHtmlString(e.color,out var color);image.color=color;image.raycastTarget=false;SpriteFit.Center(image);
                    }
                }
                MainNavigationFeedback.Bind(nodes,reduced);Canvas.ForceUpdateCanvases();
                var panelImage=nodes["dock-bg"].GetComponent<Image>();var panel=Painted(panelImage,safe);Check(Contains(new Rect(0,0,width,height),panel),"painted_panel_fits_safe_viewport");
                var centers=new List<float>();
                foreach(string name in Names){
                    string id="nav-"+name;var hit=nodes[id];var hitBefore=Bounds(hit,safe);var image=nodes[id+"-icon"].GetComponent<Image>();var painted=Painted(image,safe);centers.Add(painted.center.y);
                    Check(Contains(panel,painted,.3f),"icon_alpha_inside_panel_"+name);Check(Contains(hitBefore,painted),"icon_alpha_inside_equal_slot_"+name);Check(Math.Abs(painted.center.x-hitBefore.center.x)<.7f,"icon_visible_horizontal_center_"+name);
                    BlueInterior(panelImage,safe,painted,"icon_"+name);Check(Bounds(hit,root).width>=44,"physical_touch_column_at_least_44_"+name);
                    Check(painted.center.y>=panel.yMin+panel.height*.35f&&painted.center.y<=panel.yMin+panel.height*.65f,"icon_visible_vertical_middle_"+name);
                    if(Array.IndexOf(Names,name)==active){var restPlate=Painted(nodes[id+"-plate"].GetComponent<Image>(),safe);Check(Contains(panel,restPlate,.1f)&&Contains(hitBefore,restPlate),"resting_active_plate_alpha_contained");Check(Math.Abs(restPlate.center.y-panel.center.y)<1,"active_plate_visible_vertical_center");BlueInterior(panelImage,safe,restPlate,"rest_plate");BlueInterior(nodes[id+"-plate"].GetComponent<Image>(),safe,painted,"selected_icon_own_plate");}
                    var text=nodes[id+"-label"].GetComponent<Text>();if(text.color.a>.5f&&text.text.Length>0){Check(text.preferredWidth<=text.rectTransform.rect.width+.1f&&text.preferredHeight<=text.rectTransform.rect.height+.1f,"visible_selected_label_fits");var glyphs=Glyphs(text,safe);BlueInterior(panelImage,safe,glyphs,"selected_label_main_panel");BlueInterior(nodes[id+"-plate"].GetComponent<Image>(),safe,painted,"selected_icon_own_plate");BlueInterior(nodes[id+"-plate"].GetComponent<Image>(),safe,glyphs,"selected_label_own_plate");Check(glyphs.yMin>=painted.yMax+.05f,"selected_icon_and_label_do_not_overlap");}
                    var feedback=hit.GetComponent<MainNavigationFeedback>();Check(feedback,"actual_feedback_binding");
                    var rest=Painted(image,safe);var plateBefore=Bounds(nodes[id+"-plate"],safe);feedback.OnPointerDown(new PointerEventData(EventSystem.current));typeof(MainNavigationFeedback).GetField("amount",Private).SetValue(feedback,1f);typeof(MainNavigationFeedback).GetMethod("LateUpdate",Private).Invoke(feedback,null);Canvas.ForceUpdateCanvases();
                    var pressed=Painted(image,safe);Check(Contains(panel,pressed,.3f)&&Contains(hitBefore,pressed),"pressed_alpha_contained_"+name);BlueInterior(panelImage,safe,pressed,"pressed_icon_"+name);Check(Vector2.Distance(rest.center,pressed.center)<.15f,"press_keeps_visual_center_"+name);Check(Bounds(hit,safe)==hitBefore,"press_keeps_hit_rect_"+name);Check(Bounds(nodes[id+"-plate"],safe)==plateBefore,"press_keeps_frame_and_label_space_fixed_"+name);
                    if(Array.IndexOf(Names,name)==active){var plateImage=nodes[id+"-plate"].GetComponent<Image>();var plate=Painted(plateImage,safe);Check(Contains(panel,plate,.1f)&&Contains(hitBefore,plate),"active_plate_alpha_contained");Check(Math.Abs(plate.center.x-hitBefore.center.x)<.7f,"active_plate_horizontal_center");BlueInterior(plateImage,safe,pressed,"pressed_icon_own_plate");if(text.text.Length>0)BlueInterior(plateImage,safe,Glyphs(text,safe),"pressed_label_own_plate");}
                    feedback.OnPointerUp(null);feedback.enabled=false;Canvas.ForceUpdateCanvases();Check(Vector2.Distance(Painted(image,safe).center,rest.center)<.15f,"release_restores_center_"+name);hit.GetComponent<Button>().onClick.Invoke();Check(clicked==name&&hit.GetComponent<HomeControlLabel>().label==GameLocale.T(name=="leaderboard"?"Leaderboard":char.ToUpperInvariant(name[0])+name.Substring(1)),"click_and_accessibility_route_preserved_"+name);
                }
                float spread=centers.Max()-centers.Min();Check(spread<.7f,"all_five_visible_icon_centers_align");
                var hits=Names.Select(n=>Bounds(nodes["nav-"+n],safe)).ToArray();Check(hits.All(r=>Math.Abs(r.width-hits[0].width)<.01f),"five_equal_columns");
                report.rows.Add(new Row{width=size.x,height=size.y,scale=scale,inset=inset,active=active,reduced=reduced,locale=GameLocale.Current,iconCenterSpread=spread});report.cases++;
                if(scale==1&&!inset&&active==4&&!reduced&&(size.x==393||size.x==768))Capture(canvas,size,"Navigation_ru_"+size.x+".png");
            }catch{
                if(report.failedCase==null){
                    report.failedCase=new Row{width=size.x,height=size.y,scale=scale,inset=inset,active=active,reduced=reduced,locale=GameLocale.Current};
                    try{
                        if(safe&&nodes!=null)foreach(string name in Names)if(nodes.TryGetValue("nav-"+name+"-label",out var node)){
                            var text=node.GetComponent<Text>();var mesh=text.canvasRenderer.GetMesh();Rect glyph=default;
                            if(mesh&&mesh.vertexCount>0){var points=mesh.vertices.Select(v=>safe.InverseTransformPoint(text.transform.TransformPoint(v))).ToArray();glyph=Rect.MinMaxRect(points.Min(v=>v.x),-points.Max(v=>v.y),points.Max(v=>v.x),-points.Min(v=>v.y));}
                            report.failedLabels.Add(new FailureLabel{id=name,text=text.text,fontSize=text.fontSize,meshVertices=mesh?mesh.vertexCount:0,preferredWidth=text.preferredWidth,preferredHeight=text.preferredHeight,box=Bounds(node,safe),glyphs=glyph});
                        }
                        if(canvas)Capture(canvas,size,"FirstFailure.png");
                    }catch(Exception diagnostic){report.errors.Add("First-failure diagnostic capture: "+diagnostic.Message);}
                }
                throw;
            }finally{UnityEngine.Object.DestroyImmediate(owner);}
        }
        static void Capture(Canvas canvas,Vector2Int size,string file){
            var cameraOwner=new GameObject("Navigation106 offscreen camera");var camera=cameraOwner.AddComponent<Camera>();camera.enabled=false;camera.orthographic=true;camera.orthographicSize=size.y/2f;camera.aspect=size.x/(float)size.y;camera.transform.position=new Vector3(0,0,-10);camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.magenta;camera.nearClipPlane=.1f;camera.farClipPlane=100;
            var target=new RenderTexture(size.x,size.y,24);target.Create();var previous=RenderTexture.active;Texture2D pixels=null;
            try{camera.targetTexture=target;canvas.worldCamera=camera;Canvas.ForceUpdateCanvases();camera.Render();camera.Render();RenderTexture.active=target;pixels=new Texture2D(size.x,size.y,TextureFormat.RGB24,false);pixels.ReadPixels(new Rect(0,0,size.x,size.y),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(output,file),pixels.EncodeToPNG());report.captures.Add(file);}
            finally{camera.targetTexture=null;RenderTexture.active=previous;if(pixels)UnityEngine.Object.DestroyImmediate(pixels);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(cameraOwner);}
        }
        public static void Run(){
            output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW106_OUT")??"../Verification/Evidence/Review106/Native");Directory.CreateDirectory(output);report=new Report{unity=Application.unityVersion};int locale=GameLocale.Current;GameObject events=null;
            try{
                Check(Application.unityVersion=="2022.3.62f3","pinned_editor");EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);events=new GameObject("Navigation106 events");events.AddComponent<EventSystem>();assets=AssetDatabase.LoadAssetAtPath<HomePageAssets>("Assets/HeartOfTheRain/App/Home/HomePageAssets.asset");Check(assets,"approved_home_assets");MaskControls();GameLocale.Select(4);
                foreach(var size in new[]{new Vector2Int(320,568),new Vector2Int(393,852),new Vector2Int(720,1600),new Vector2Int(768,1024),new Vector2Int(1024,1366)})foreach(float scale in new[]{1f,1.5f,2.5f,5f})foreach(bool inset in new[]{false,true})foreach(int active in Enumerable.Range(0,5))foreach(bool reduced in new[]{false,true})RunCase(size,scale,inset,active,reduced);
                foreach(int language in Enumerable.Range(0,4)){GameLocale.Select(language);foreach(int active in Enumerable.Range(0,5))RunCase(new Vector2Int(393,852),1,false,active,true);}
                report.status="PASS_NATIVE_NAVIGATION106";
            }catch(Exception e){report.errors.Add(e.ToString());}
            finally{GameLocale.Select(locale);if(events)UnityEngine.Object.DestroyImmediate(events);File.WriteAllText(Path.Combine(output,"Navigation106.json"),JsonUtility.ToJson(report,true));}
            if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif
