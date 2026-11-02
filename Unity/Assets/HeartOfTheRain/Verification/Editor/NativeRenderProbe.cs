#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.Verification
{
    public static class NativeRenderProbe
    {
        public static void Run()=>Probe(false);
        public static void RunAfter()=>Probe(true);
        static void Probe(bool verify)
        {
            string output = Path.GetFullPath("../Verification/Evidence/Regression/"+(verify?"Probe_After.txt":"Probe.txt"));
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            var lines = new System.Collections.Generic.List<string>();
            var ui = AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
            var cameraObject = new GameObject("Render probe camera");
            var camera = cameraObject.AddComponent<Camera>();
            camera.orthographic = true; camera.orthographicSize = 1; camera.transform.position = new Vector3(1000,0,-10);
            camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = Color.black;
            var target = new RenderTexture(128,128,24); camera.targetTexture = target;
            var go = new GameObject("Shader probe"); go.transform.position = new Vector3(1000,0,0);
            var sr = go.AddComponent<SpriteRenderer>(); sr.sprite = ui.Get("Focus_Cell");
            foreach (var shader in new[] { Shader.Find("Sprites/Default"), ui.boards.effectsMaterial.shader, ui.boards.tileGlowMaterial.shader })
            {
                var material = new Material(shader); sr.sharedMaterial = material;
                camera.Render(); RenderTexture.active = target;
                var pixels = new Texture2D(128,128,TextureFormat.RGB24,false); pixels.ReadPixels(new Rect(0,0,128,128),0,0); pixels.Apply();
                int lit=pixels.GetPixels32().Count(p=>p.r>5||p.g>5||p.b>5);
                lines.Add(shader.name+" supported="+shader.isSupported+" litPixels="+lit);
                if(verify&&lit==0)throw new InvalidOperationException("Shader drew no pixels: "+shader.name);
                File.WriteAllBytes(Path.Combine(Path.GetDirectoryName(output),(verify?"After_":"")+shader.name.Replace('/','_')+".png"),pixels.EncodeToPNG());
                UnityEngine.Object.DestroyImmediate(material); UnityEngine.Object.DestroyImmediate(pixels);
            }
            if(verify){
                var material=new Material(Shader.Find("Sprites/Default"));sr.sharedMaterial=material;
                Color32[] Sample(){camera.Render();RenderTexture.active=target;var p=new Texture2D(128,128,TextureFormat.RGB24,false);p.ReadPixels(new Rect(0,0,128,128),0,0);p.Apply();var bytes=p.GetPixels32();UnityEngine.Object.DestroyImmediate(p);return bytes;}
                var expected=Sample();var block=new MaterialPropertyBlock();block.SetTexture("_MainTex",sr.sprite.texture);block.SetFloat("_Glow",.4f);sr.sharedMaterial=ui.boards.tileGlowMaterial;sr.SetPropertyBlock(block);Sample();
                sr.sharedMaterial=material;sr.SetPropertyBlock(null);var restored=Sample();
                if(!expected.SequenceEqual(restored))throw new InvalidOperationException("Clearing a glow block did not restore native automatic sprite texture binding.");
                lines.Add("Native sprite automatic texture binding survives glow-to-ordinary transition: identical RGB pixels.");UnityEngine.Object.DestroyImmediate(material);
            }
            var home = AssetDatabase.LoadAssetAtPath<HomePageAssets>("Assets/HeartOfTheRain/App/Home/HomePageAssets.asset");
            var label = new GameObject("Label probe",typeof(RectTransform)).AddComponent<Text>();
            label.font = home.boldFont; label.text = "Уровень 1"; label.fontSize = 24;
            foreach (int height in new[] { 22,28,32,40,48 })
            {
                label.rectTransform.sizeDelta = new Vector2(250,height);label.fontSize=24;
                if(verify)LabelFit.Apply(label,250,height);
                var settings=label.GetGenerationSettings(label.rectTransform.rect.size);
                var gen=new TextGenerator(); gen.Populate(label.text,settings);
                lines.Add("Label fontSize="+label.fontSize+" height="+height+" preferred="+label.preferredHeight+" verts="+gen.verts.Count+" fontLineHeight="+home.boldFont.lineHeight);
                if(verify&&gen.vertexCount==0)throw new InvalidOperationException("Native fitted text is invisible.");
            }
            File.WriteAllLines(output,lines); Debug.Log(string.Join("\n",lines));
            camera.targetTexture=null; RenderTexture.active=null;
            UnityEngine.Object.DestroyImmediate(label.gameObject); UnityEngine.Object.DestroyImmediate(go); UnityEngine.Object.DestroyImmediate(cameraObject); UnityEngine.Object.DestroyImmediate(target);
        }
    }
}
#endif
