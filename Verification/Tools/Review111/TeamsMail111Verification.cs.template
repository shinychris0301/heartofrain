#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Collections.Generic;
using HeartOfTheRain.App.TeamsMail;
using HeartOfTheRain.App.Teams;
using UnityEditor;
using UnityEngine;
namespace HeartOfTheRain.Verification {
 public static class TeamsMail111Verification {
  [Serializable] sealed class Report { public string status="RUNNING",utc,unity,scope="Actual pinned Unity Editor import and Resources lookup; no HTTP, device, build or production acceptance."; public int checks; public List<string> errors=new List<string>(); }
  static Report report;
  static void Check(bool good,string label){report.checks++;if(!good)throw new InvalidOperationException(label);}
  static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}
  public static void RunImport(){
   string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW111_OUT")??"../Verification/Evidence/Review111");Directory.CreateDirectory(Path.Combine(output,"Native"));
   report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};Application.logMessageReceived+=Log;
   try{
    Check(Application.unityVersion=="2022.3.62f3","Pinned Unity engine");
    string root="Assets/HeartOfTheRain/App/TeamsMail/Art/";
    var files=Directory.GetFiles(root,"TM_*.png");Check(files.Length==3,"Exactly three new supplied Mail sprites");
    var roles=AssetDatabase.LoadAssetAtPath<TeamsMailAssets111>("Assets/HeartOfTheRain/Resources/HOTR_TeamsMail111/Assets.asset");Check(roles,"Exact lazy Mail roles asset exists");
    var teams=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");Check(teams,"Existing Teams asset is available");
    foreach(string name in new[]{"TM_Coin","TM_Letter_Closed","TM_Letter_Open"}){
     string path=root+name+".png";var importer=AssetImporter.GetAtPath(path) as TextureImporter;var sprite=AssetDatabase.LoadAssetAtPath<Sprite>(path);int size=name=="TM_Coin"?256:1024;
     Check(importer&&sprite,"Mail sprite imported "+name);Check(importer.textureType==TextureImporterType.Sprite&&!importer.isReadable&&importer.alphaIsTransparency,"Mail sprite imported with alpha and no Read/Write "+name);
     Check(importer.mipmapEnabled&&importer.filterMode==FilterMode.Trilinear,"Detailed-art mip and filtering "+name);Check(importer.textureCompression==TextureImporterCompression.Uncompressed&&importer.maxTextureSize>=size,"Uncompressed comparison baseline and full source pixel budget "+name);
     Check(sprite.texture.width==size&&sprite.texture.height==size,"Unity imported exact source dimensions "+name);Check(sprite.border==Vector4.zero,"Letter and coin remain simple illustrations "+name);Check(roles.Find(name)==sprite&&teams.Find(name)==sprite,"Actual Teams lazy role resolves exact asset "+name);
     foreach(string platform in new[]{"DefaultTexturePlatform","Standalone","Android"}){var value=importer.GetPlatformTextureSettings(platform);Check(!value.overridden||(value.maxTextureSize>=size&&value.textureCompression==TextureImporterCompression.Uncompressed),"No lossy/small platform override "+name+" "+platform);}
    }
   }catch(Exception error){report.errors.Add(error.ToString());}
   finally{Application.logMessageReceived-=Log;report.status=report.errors.Count==0?"PASS_NATIVE_TEAMS_MAIL_IMPORT111":"FAIL_NATIVE_TEAMS_MAIL_IMPORT111";File.WriteAllText(Path.Combine(output,"Native","TeamsMail111_Import.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));}EditorApplication.Exit(report.errors.Count==0?0:1);
  }
 }
}
#endif
