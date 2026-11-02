using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification {
    // Measures the visual cost of the Android ASTC policy on the original PNGs with
    // Unity's own encoder, because a Standalone Editor capture never shows Android
    // formats. Pixel error is alpha-weighted: transparent texels are never drawn.
    public static class ArtCompression128Verification {
        [Serializable] sealed class Row {public string path,format;public int width,height;public float psnr,worstBlockError;public long beforeBytes,afterBytes;}
        [Serializable] sealed class Report {public string status,utc,unity,scope="Native Editor encoder comparison of original PNGs against ASTC. Not an on-device capture.";public int textures,keptLossless;public long beforeBytes,afterBytes;public float lowestPsnr;public List<Row> rows=new List<Row>();public List<string> errors=new List<string>();}
        const float MinimumPsnr=30;
        static readonly string[] Roots={"Assets/HeartOfTheRain/App/TeamsAccess/Art","Assets/HeartOfTheRain/App/Profile/Art"};
        public static void Run(){
            var report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
            string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW128_OUT")??"../Verification/Evidence/Review128/ArtCompression");Directory.CreateDirectory(output);
            var compared=new List<KeyValuePair<float,string>>();
            var registered=new HashSet<string>(System.Text.RegularExpressions.Regex.Matches(File.ReadAllText("Assets/HeartOfTheRain/App/UIClarity/Editor/UIClarityRegistry.json"),"\\b[0-9a-f]{32}\\b").Cast<System.Text.RegularExpressions.Match>().Select(m=>m.Value));
            try{
                foreach(string path in Roots.SelectMany(root=>Directory.GetFiles(root,"*.png",SearchOption.AllDirectories)).Select(p=>p.Replace('\\','/')).OrderBy(p=>p,StringComparer.Ordinal)){
                    var importer=AssetImporter.GetAtPath(path) as TextureImporter;if(!importer)continue;
                    var android=importer.GetPlatformTextureSettings("Android");
                    if(!android.overridden)continue;
                    bool background=Path.GetFileName(path)=="TA_Background.png";
                    if(android.format==TextureImporterFormat.RGBA32){
                        if(!registered.Contains(AssetDatabase.AssetPathToGUID(path)))report.errors.Add(path+" stayed uncompressed outside the clarity registry");
                        report.keptLossless++;continue;
                    }
                    if(android.format!=TextureImporterFormat.ASTC_4x4&&android.format!=TextureImporterFormat.ASTC_6x6)continue;
                    if(background&&(android.format!=TextureImporterFormat.ASTC_6x6||android.maxTextureSize!=2048))report.errors.Add(path+" Android policy mismatch");
                    if(registered.Contains(AssetDatabase.AssetPathToGUID(path)))report.errors.Add(path+" clarity-registered sprite was compressed");
                    Row row=Measure(path,background?TextureFormat.ASTC_6x6:TextureFormat.ASTC_4x4,background?2048:int.MaxValue,output,compared);
                    report.rows.Add(row);report.beforeBytes+=row.beforeBytes;report.afterBytes+=row.afterBytes;
                    if(row.psnr<MinimumPsnr)report.errors.Add(path+" PSNR "+row.psnr.ToString("0.0"));
                }
                report.textures=report.rows.Count;report.lowestPsnr=report.rows.Count==0?0:report.rows.Min(r=>r.psnr);
                if(report.rows.Count==0)report.errors.Add("No textures measured");
                report.status=report.errors.Count==0?"PASS_NATIVE_ART_COMPRESSION128":"FAIL_NATIVE_ART_COMPRESSION128";
            }catch(Exception problem){report.errors.Add(problem.GetType().Name+": "+problem.Message);report.status="FAIL_NATIVE_ART_COMPRESSION128";}
            File.WriteAllText(Path.Combine(output,"ArtCompression128.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));
            if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);
        }
        static Row Measure(string path,TextureFormat format,int maximum,string output,List<KeyValuePair<float,string>> compared){
            var source=new Texture2D(2,2,TextureFormat.RGBA32,false);RenderTexture target=null;Texture2D encoded=null,decoded=null;
            try{
                if(!source.LoadImage(File.ReadAllBytes(path)))throw new InvalidOperationException("Unreadable PNG "+path);
                int size=Math.Max(source.width,source.height),width=source.width,height=source.height;
                if(size>maximum){width=Math.Max(1,width*maximum/size);height=Math.Max(1,height*maximum/size);}
                var reference=Resize(source,width,height);
                // ASTC blocks need no power-of-two size, matching this project's NPOT sprites.
                encoded=new Texture2D(width,height,TextureFormat.RGBA32,false);encoded.SetPixels32(reference.GetPixels32());encoded.Apply(false,false);
                EditorUtility.CompressTexture(encoded,format,TextureCompressionQuality.Best);
                if(encoded.format!=format)throw new InvalidOperationException("Encoder returned "+encoded.format+" for "+path);
                target=RenderTexture.GetTemporary(width,height,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);
                var previous=RenderTexture.active;Graphics.Blit(encoded,target);RenderTexture.active=target;
                decoded=new Texture2D(width,height,TextureFormat.RGBA32,false);decoded.ReadPixels(new Rect(0,0,width,height),0,0);decoded.Apply(false,false);RenderTexture.active=previous;
                var a=reference.GetPixels32();var b=decoded.GetPixels32();double sum=0,weight=0;double worst=0;const int block=16;
                for(int y=0;y<height;y+=block)for(int x=0;x<width;x+=block){double local=0,localWeight=0;
                    for(int yy=y;yy<Math.Min(height,y+block);yy++)for(int xx=x;xx<Math.Min(width,x+block);xx++){var p=a[yy*width+xx];var q=b[yy*width+xx];double w=Math.Max(p.a,q.a)/255.0+.0001;
                        double e=((p.r-q.r)*(p.r-q.r)+(p.g-q.g)*(p.g-q.g)+(p.b-q.b)*(p.b-q.b))*w/3+(p.a-q.a)*(p.a-q.a);local+=e;localWeight+=w;}
                    sum+=local;weight+=localWeight;if(localWeight>block*block*.25)worst=Math.Max(worst,local/localWeight);}
                double mse=weight>0?sum/weight:0;float psnr=mse<=.0001?99:(float)(10*Math.Log10(255.0*255.0/mse));
                double mip=AssetImporter.GetAtPath(path) is TextureImporter i&&i.mipmapEnabled?1.3333:1;
                double bitsPerPixel=format==TextureFormat.ASTC_6x6?128.0/36:8;
                string name=Path.GetFileNameWithoutExtension(path);compared.Add(new KeyValuePair<float,string>(psnr,name));
                if(ShouldSave(name,psnr))File.WriteAllBytes(Path.Combine(output,name+"_compare.png"),SideBySide(reference,decoded));
                if(reference!=source)UnityEngine.Object.DestroyImmediate(reference);
                return new Row{path=path,format=format.ToString(),width=width,height=height,psnr=psnr,worstBlockError=(float)worst,beforeBytes=(long)(source.width*source.height*4*mip),afterBytes=(long)(width*height*bitsPerPixel/8*mip)};
            }finally{if(target)RenderTexture.ReleaseTemporary(target);UnityEngine.Object.DestroyImmediate(source);if(encoded)UnityEngine.Object.DestroyImmediate(encoded);if(decoded)UnityEngine.Object.DestroyImmediate(decoded);}
        }
        static bool ShouldSave(string name,float psnr)=>psnr<38||name=="TA_Background"||name=="Banner_Village_R3"||name=="Frame_Rainkeeper_R1"||name=="TA_Panel_Blue"||name=="TA_Button_Blue"||name=="Stat_Stars_R1";
        static Texture2D Resize(Texture2D source,int width,int height){
            if(source.width==width&&source.height==height)return source;
            var scaled=RenderTexture.GetTemporary(width,height,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);var previous=RenderTexture.active;
            try{source.filterMode=FilterMode.Bilinear;Graphics.Blit(source,scaled);RenderTexture.active=scaled;var result=new Texture2D(width,height,TextureFormat.RGBA32,false);result.ReadPixels(new Rect(0,0,width,height),0,0);result.Apply(false,false);return result;}
            finally{RenderTexture.active=previous;RenderTexture.ReleaseTemporary(scaled);}
        }
        // Original on the left, ASTC on the right, over mid grey so transparent edges are visible.
        static byte[] SideBySide(Texture2D a,Texture2D b){
            int limit=900,sw=a.width,sh=a.height;float scale=Math.Min(1,(float)limit/Math.Max(sw,sh));int w=Math.Max(1,(int)(sw*scale)),h=Math.Max(1,(int)(sh*scale));
            var sheet=new Texture2D(w*2+8,h,TextureFormat.RGB24,false);var pa=a.GetPixels32();var pb=b.GetPixels32();var row=new Color32[sheet.width*h];
            for(int y=0;y<h;y++)for(int x=0;x<w;x++){int sx=Math.Min(sw-1,(int)(x/scale)),sy=Math.Min(sh-1,(int)(y/scale));row[y*sheet.width+x]=Over(pa[sy*sw+sx]);row[y*sheet.width+w+8+x]=Over(pb[sy*sw+sx]);}
            sheet.SetPixels32(row);sheet.Apply(false,false);try{return sheet.EncodeToPNG();}finally{UnityEngine.Object.DestroyImmediate(sheet);}
        }
        static Color32 Over(Color32 c){int g=128*(255-c.a);return new Color32((byte)((c.r*c.a+g)/255),(byte)((c.g*c.a+g)/255),(byte)((c.b*c.a+g)/255),255);}
    }
}
