#if UNITY_EDITOR
using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.Verification {
 // Protect historical checkpoint rendering before packaging; this reads only
 // source files at build time and does not add any player-frame readback.
 public sealed class LegacyGraphicsBuildGuard117:IPreprocessBuildWithReport {
  [Serializable] sealed class Manifest {public LegacyLevelGraphics117[] entries;}
  public int callbackOrder=>-18000;
  public void OnPreprocessBuild(BuildReport report)=>Validate(File.ReadAllBytes);
  public static void Validate(Func<string,byte[]> read){
   try{
    if(read==null)throw new InvalidOperationException("Missing reader");
    var manifest=JsonUtility.FromJson<Manifest>(Encoding.UTF8.GetString(read("Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/Graphics.json")));
    if(manifest==null||manifest.entries==null||manifest.entries.Length!=50)throw new InvalidOperationException("Legacy graphics manifest is invalid");
    string Hash(byte[] bytes){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
    for(int i=0;i<50;i++){
     int n=i+1;var e=manifest.entries[i];
     if(e==null||e.level!=n||e.width<1||e.height<1||e.surface==e.mask||!Regex.IsMatch(e.surface??"",@"\AM48Textures/[0-9a-f]{32}\z")||!Regex.IsMatch(e.mask??"",@"\AM48Textures/[0-9a-f]{32}\z"))throw new InvalidOperationException("Invalid original graphics binding L"+n);
     string level="Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/C01_L"+n.ToString("D3")+".json";
     string surface="Assets/HeartOfTheRain/M48/Resources/"+e.surface+".png",mask="Assets/HeartOfTheRain/M48/Resources/"+e.mask+".png";
     if(Hash(read(level))!=e.config||Hash(read(surface))!=e.surfaceSHA256||Hash(read(mask))!=e.maskSHA256)throw new InvalidOperationException("Legacy board source or graphics hash mismatch L"+n);
    }
   }catch(Exception e){throw new BuildFailedException("Legacy board graphics validation failed: "+e.Message);}
  }
 }
}
#endif
