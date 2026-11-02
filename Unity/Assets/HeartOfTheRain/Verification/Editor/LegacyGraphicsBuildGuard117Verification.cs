#if UNITY_EDITOR
using System;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.Verification {
 public static class LegacyGraphicsBuildGuard117Verification {
  [Serializable] sealed class Manifest {public LegacyLevelGraphics117[] entries;}
  [Serializable] sealed class Report {public string status,error="",scope="Actual Editor build preprocessor and injected file-reader failures; no player build or device test.";public int checks;}
  public static void Run(){
   var r=new Report();void Check(bool value,string name){r.checks++;if(!value)throw new Exception(name);}
   void Reject(Func<string,byte[]> read,string name){bool refused=false;try{LegacyGraphicsBuildGuard117.Validate(read);}catch(BuildFailedException){refused=true;}Check(refused,name);}
   try{
    new LegacyGraphicsBuildGuard117().OnPreprocessBuild(null);Check(true,"Actual build preprocessor accepts the original assets");
    var manifest=JsonUtility.FromJson<Manifest>(File.ReadAllText("Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/Graphics.json"));var entry=manifest.entries[49];
    string[] paths={"Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/C01_L050.json","Assets/HeartOfTheRain/M48/Resources/"+entry.surface+".png","Assets/HeartOfTheRain/M48/Resources/"+entry.mask+".png"};
    foreach(string target in paths){Reject(path=>{var b=File.ReadAllBytes(path);if(path==target)b[b.Length/2]^=1;return b;},"Corrupt source fails closed: "+target);}
    Reject(path=>path==paths[2]?throw new FileNotFoundException():File.ReadAllBytes(path),"Missing mask fails closed");
    entry.config=new string('0',64);byte[] changed=Encoding.UTF8.GetBytes(JsonUtility.ToJson(manifest));
    Reject(path=>path.EndsWith("HOTR_LegacyLevels117/Graphics.json",StringComparison.Ordinal)?changed:File.ReadAllBytes(path),"Mismatched config binding fails closed");
    r.status="PASS_LEGACY_GRAPHICS_BUILD_GUARD117";
   }catch(Exception e){r.status="FAIL_LEGACY_GRAPHICS_BUILD_GUARD117";r.error=e.ToString();}
   string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_GRAPHICS_GUARD117_OUTPUT")??"../Verification/Evidence/Review117/GraphicsGuard");Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"GraphicsGuard117.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.status=="PASS_LEGACY_GRAPHICS_BUILD_GUARD117"?0:1);
  }
 }
}
#endif
