#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Celebrations;
namespace HeartOfTheRain.Verification
{
    public static class M68RenderVerification
    {
        [Serializable] class AtlasPage {public string file;}
        [Serializable] class AtlasFrame {public int page;public int[] rect_unity_bottom_left;}
        [Serializable] class Atlas {public AtlasPage[] pages;public AtlasFrame[] frames;}
        [Serializable] class Row {public float seconds;public int nativeVisiblePixels,referenceVisiblePixels;public double normalizedRgbaError;}
        [Serializable] class Report {public string scope="Native 768px camera composition versus supplied baked frame. Rasterization/filtering differences are expected; not physical-device or art approval.";public Row[] samples;}
        static RectTransform Rect(string name,Transform parent,float x,float y,float w,float h)
        {var o=new GameObject(name,typeof(RectTransform));o.layer=31;o.transform.SetParent(parent,false);var r=(RectTransform)o.transform;r.anchorMin=r.anchorMax=r.pivot=Vector2.zero;r.anchoredPosition=new Vector2(x,y);r.sizeDelta=new Vector2(w,h);return r;}
        static RawImage Image(string name,Transform parent,Texture texture,float x,float y,float w,float h,Color color,float angle=0)
        {var r=Rect(name,parent,x,y,w,h);r.anchoredPosition+=new Vector2(w/2,h/2);r.pivot=new Vector2(.5f,.5f);r.localRotation=Quaternion.Euler(0,0,angle);var im=r.gameObject.AddComponent<RawImage>();im.texture=texture;im.color=color;return im;}
        public static void Run()
        {
            string output=Path.GetFullPath("../Verification/Evidence/Fluidity/M68");Directory.CreateDirectory(output);
            var data=M68CelebrationAssets.Load();var atlas=JsonUtility.FromJson<Atlas>(File.ReadAllText("Assets/HeartOfTheRain/M68Celebration/Data/Dariya_Celebration.json"));
            var cameraGo=new GameObject("M68 probe camera");var camera=cameraGo.AddComponent<Camera>();camera.orthographic=true;camera.orthographicSize=384;camera.transform.position=new Vector3(0,0,-10);camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.clear;camera.cullingMask=1<<31;
            var target=new RenderTexture(768,768,24,RenderTextureFormat.ARGB32);camera.targetTexture=target;var previous=RenderTexture.active;
            var pixels=new Texture2D(768,768,TextureFormat.RGBA32,false);var rows=new List<Row>();
            GameObject canvasGo=null;
            try{foreach(float t in new[]{.20f,.65f,1.15f,1.55f,1.88f,2.75f}){
                canvasGo=new GameObject("M68 visual probe",typeof(RectTransform),typeof(Canvas));canvasGo.layer=31;var canvas=canvasGo.GetComponent<Canvas>();canvas.renderMode=RenderMode.WorldSpace;canvas.vertexColorAlwaysGammaSpace=true;var root=(RectTransform)canvas.transform;root.sizeDelta=new Vector2(768,768);root.position=Vector3.zero;
                int frame=M68CelebrationAssets.Frame(t);var sample=data.Effects.samples[frame];float size=sample.halo_size*768;
                Image("Halo",root,data.halo,sample.halo_center[0]*768-size/2,(1-sample.halo_center[1])*768-size/2,size,size,new Color(1,1,1,sample.halo_alpha),sample.halo_angle);
                foreach(var p in sample.particles){float w=p.size*768,h=w*p.height_ratio;var c=data.Design.seeds[p.id].star?Color.white:data.Colors[p.id];c.a=p.opacity;Image("Particle",root,data.Design.seeds[p.id].star?data.star:Texture2D.whiteTexture,p.x*768-w/2,(1-p.y)*768-h/2,w,h,c,p.angle);}
                var actor=Rect("Authored mesh",root,0,0,768,768).gameObject.AddComponent<M68MeshGraphic>();actor.Configure(data);actor.Sample(frame,data.Clip.samples[frame].opacity);
                Canvas.ForceUpdateCanvases();var debugMesh=actor.canvasRenderer.GetMesh();Debug.Log("M68 native probe "+t+" vertices="+debugMesh.vertexCount+" opacity="+data.Clip.samples[frame].opacity+" master="+data.master.width+"x"+data.master.height+" supported="+data.blendShader.isSupported);
                camera.Render();RenderTexture.active=target;pixels.ReadPixels(new Rect(0,0,768,768),0,0);pixels.Apply();var actual=pixels.GetPixels32();File.WriteAllBytes(Path.Combine(output,"Mesh_"+t.ToString("F2",System.Globalization.CultureInfo.InvariantCulture)+".png"),pixels.EncodeToPNG());
                actor.material=null;Canvas.ForceUpdateCanvases();camera.Render();pixels.ReadPixels(new Rect(0,0,768,768),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(output,"Default_"+t.ToString("F2",System.Globalization.CultureInfo.InvariantCulture)+".png"),pixels.EncodeToPNG());UnityEngine.Object.DestroyImmediate(canvasGo);canvasGo=null;
                canvasGo=new GameObject("Baked reference probe",typeof(RectTransform),typeof(Canvas));canvasGo.layer=31;canvas=canvasGo.GetComponent<Canvas>();canvas.renderMode=RenderMode.WorldSpace;canvas.vertexColorAlwaysGammaSpace=true;root=(RectTransform)canvas.transform;root.sizeDelta=new Vector2(768,768);root.position=Vector3.zero;
                var f=atlas.frames[frame];var texture=AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/HeartOfTheRain/M68Celebration/"+atlas.pages[f.page].file);var reference=Image("Reference",root,texture,0,0,768,768,Color.white);var rect=f.rect_unity_bottom_left;reference.uvRect=new Rect(rect[0]/(float)texture.width,rect[1]/(float)texture.height,rect[2]/(float)texture.width,rect[3]/(float)texture.height);
                Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels.ReadPixels(new Rect(0,0,768,768),0,0);pixels.Apply();var expected=pixels.GetPixels32();File.WriteAllBytes(Path.Combine(output,"Reference_"+t.ToString("F2",System.Globalization.CultureInfo.InvariantCulture)+".png"),pixels.EncodeToPNG());double error=0;int visible=0,refVisible=0;
                for(int i=0;i<actual.Length;i++){var a=actual[i];var b=expected[i];if(a.a>8)visible++;if(b.a>8)refVisible++;error+=Math.Abs(a.r-b.r)+Math.Abs(a.g-b.g)+Math.Abs(a.b-b.b)+Math.Abs(a.a-b.a);}
                rows.Add(new Row{seconds=t,nativeVisiblePixels=visible,referenceVisiblePixels=refVisible,normalizedRgbaError=error/(actual.Length*4d*255)});UnityEngine.Object.DestroyImmediate(canvasGo);canvasGo=null;
            }}finally{if(canvasGo)UnityEngine.Object.DestroyImmediate(canvasGo);camera.targetTexture=null;RenderTexture.active=previous;UnityEngine.Object.DestroyImmediate(pixels);UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(cameraGo);}
            File.WriteAllText(Path.Combine(output,"Comparison.json"),JsonUtility.ToJson(new Report{samples=rows.ToArray()},true));
            foreach(var row in rows)if(row.nativeVisiblePixels<10000||row.normalizedRgbaError>.01)throw new Exception("M68 render differs from reference at "+row.seconds+": "+row.normalizedRgbaError);
        }
    }
}
#endif
