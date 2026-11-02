#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections.Generic;
using System.Text;
using HeartOfTheRain.App.TeamsInvites;
using HeartOfTheRain.App.Teams;
using UnityEditor;
using UnityEngine;
namespace HeartOfTheRain.Verification {
 public static class TeamsInvites112Verification {
  [Serializable] sealed class Report { public string status="RUNNING",utc,unity,scope="Pinned Unity Editor import, exact glyph roles and Resources lookup; no HTTP, share sheet, device, build or production acceptance."; public int checks; public List<string> errors=new List<string>(); }
  static Report report;
  static void Check(bool good,string label){report.checks++;if(!good)throw new InvalidOperationException(label);}
  static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}
  public static void RunImport(){
   string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW112_OUT")??"../Verification/Evidence/Review112");Directory.CreateDirectory(Path.Combine(output,"Native"));
   report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};Application.logMessageReceived+=Log;
   try{
    Check(Application.unityVersion=="2022.3.62f3","Pinned Unity engine");
    string root="Assets/HeartOfTheRain/App/TeamsInvites/Art/";
    var files=Directory.GetFiles(root,"TI_*.png");Check(files.Length==2,"Exactly two new supplied invitation glyphs");
    var roles=AssetDatabase.LoadAssetAtPath<TeamsInvitesAssets112>("Assets/HeartOfTheRain/Resources/HOTR_TeamsInvites112/Assets.asset");Check(roles,"Exact lazy invitation role asset exists");
    var teams=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(teams,"Existing Teams asset is available");
    string[] names={"TI_Icon_Copy","TI_Icon_Share"},guids={"beae9c7c01d25a1bbf0d48b9ad9a2b98","27000b95772851c1ab71904f33dd5f2f"};
    for(int i=0;i<names.Length;i++){
     string name=names[i],path=root+name+".png";var importer=AssetImporter.GetAtPath(path) as TextureImporter;var sprite=AssetDatabase.LoadAssetAtPath<Sprite>(path);
     Check(importer&&sprite,"Invitation glyph imported "+name);Check(AssetDatabase.AssetPathToGUID(path)==guids[i],"Package GUID preserved "+name);
     Check(importer.textureType==TextureImporterType.Sprite&&!importer.isReadable&&importer.alphaIsTransparency,"Sprite alpha and no Read/Write "+name);
     Check(!importer.mipmapEnabled&&importer.filterMode==FilterMode.Bilinear&&importer.wrapMode==TextureWrapMode.Clamp,"Utility glyph filtering and clamped edges "+name);
     Check(importer.textureCompression==TextureImporterCompression.Uncompressed&&importer.maxTextureSize>=256&&importer.sRGBTexture,"Uncompressed sRGB and full source pixel budget "+name);
     Check(sprite.texture.width==256&&sprite.texture.height==256,"Unity imported exact source dimensions "+name);Check(sprite.border==Vector4.zero&&Mathf.Approximately(sprite.pixelsPerUnit,100),"Simple glyph at approved PPU "+name);
     Check(roles.Find(name)==sprite&&teams.Find(name)==sprite,"Actual Teams lazy role resolves exact asset "+name);
     foreach(string platform in new[]{"DefaultTexturePlatform","Standalone","Android"}){var value=importer.GetPlatformTextureSettings(platform);Check(!value.overridden||(value.maxTextureSize>=256&&value.textureCompression==TextureImporterCompression.Uncompressed),"No lossy/small platform override "+name+" "+platform);}
    }
   }catch(Exception error){report.errors.Add(error.ToString());}
   finally{Application.logMessageReceived-=Log;report.status=report.errors.Count==0?"PASS_NATIVE_TEAMS_INVITES_IMPORT112":"FAIL_NATIVE_TEAMS_INVITES_IMPORT112";File.WriteAllText(Path.Combine(output,"Native","TeamsInvites112_Import.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));}EditorApplication.Exit(report.errors.Count==0?0:1);
  }
 }
}
#endif
