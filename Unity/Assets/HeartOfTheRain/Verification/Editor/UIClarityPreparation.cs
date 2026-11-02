#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.UIClarity;
namespace HeartOfTheRain.Verification {
    public static class UIClarityPreparation {
        static string Output=>Path.GetFullPath("../Verification/Evidence/UIClarityR1");
        [Serializable] class Report {public string utc,status,error;public int checks;public string[] failures;}
        public static void Apply(){var r=new Report{utc=DateTime.UtcNow.ToString("o")};try{
            AssetDatabase.Refresh();
            foreach(string n in new[]{"DG_Card_Bonus","DG_Card_Collected","DG_Card_Today","DG_Card_Upcoming","DG_Hero_Well"}){
                string p="Assets/HeartOfTheRain/App/DailyGiftDesign/Art/"+n+".png";var ti=(TextureImporter)AssetImporter.GetAtPath(p);ti.spriteBorder=Vector4.one*108;ti.SaveAndReimport();
            }
            UIClarityGuard.Apply();var errors=UIClarityGuard.Validate(out var log);if(errors.Count>0)throw new Exception(string.Join("\n",errors));File.WriteAllText(Path.Combine(Output,"Import_Audit.txt"),log.ToString());
            string path="Assets/HeartOfTheRain/Resources/HOTR_UIClarity/Config.asset";Directory.CreateDirectory(Path.GetDirectoryName(path));AssetDatabase.Refresh();var a=AssetDatabase.LoadAssetAtPath<UIClarityAssets>(path);if(!a){a=ScriptableObject.CreateInstance<UIClarityAssets>();AssetDatabase.CreateAsset(a,path);}a.goldenSeeker=AssetDatabase.LoadAssetAtPath<Sprite>("Assets/HeartOfTheRain/App/WellworksDesign/Art/Reward_Golden_Seeker.png");if(!a.goldenSeeker)throw new Exception("Missing Golden Seeker UI art");EditorUtility.SetDirty(a);AssetDatabase.SaveAssets();r.status="PASS_NATIVE_UI_CLARITY_APPLY";
        }catch(Exception e){r.error=e.ToString();r.status="FAIL_NATIVE_UI_CLARITY_APPLY";}File.WriteAllText(Path.Combine(Output,"Apply.json"),JsonUtility.ToJson(r,true));if(r.error!=null)throw new Exception(r.error);}
        public static void Checks(){var r=new Report{utc=DateTime.UtcNow.ToString("o")};Action<bool,string> check=(ok,m)=>{r.checks++;if(!ok)throw new Exception(m);};try{
            check(UIClarityGuard.Validate(out var log).Count==0,"Registered baseline valid");File.WriteAllText(Path.Combine(Output,"Guard_Import_Audit.txt"),log.ToString());new UIClarityBuildGate().OnPreprocessBuild(null);check(true,"Real build preprocessor accepts current baseline");
            string p="Assets/HeartOfTheRain/App/DailyGiftDesign/Art/DG_Gift_Chest.png";byte[] original=File.ReadAllBytes(p+".meta");try{
                var ti=(TextureImporter)AssetImporter.GetAtPath(p);ti.mipmapEnabled=false;ti.SaveAndReimport();check(UIClarityGuard.Validate(out _).Any(e=>e.Contains("sampling policy")),"No-mipmap regression detected");bool rejected=false;try{new UIClarityBuildGate().OnPreprocessBuild(null);}catch(BuildFailedException){rejected=true;}check(rejected,"Build preprocessor rejects regression");
            }finally{File.WriteAllBytes(p+".meta",original);AssetDatabase.ImportAsset(p,ImportAssetOptions.ForceUpdate);}
            original=File.ReadAllBytes(p+".meta");try{var ti=(TextureImporter)AssetImporter.GetAtPath(p);var ps=ti.GetPlatformTextureSettings("Android");ps.maxTextureSize=256;ti.SetPlatformTextureSettings(ps);ti.SaveAndReimport();check(UIClarityGuard.Validate(out _).Any(e=>e.Contains("Android")),"Android downscale detected");}finally{File.WriteAllBytes(p+".meta",original);AssetDatabase.ImportAsset(p,ImportAssetOptions.ForceUpdate);}
            string registry="Assets/HeartOfTheRain/App/UIClarity/Editor/UIClarityRegistry.json";original=File.ReadAllBytes(registry);try{File.WriteAllText(registry,"{\"assets\":[]}");bool failed=false;try{UIClarityGuard.Validate(out _);}catch(InvalidOperationException){failed=true;}check(failed,"Invalid registry fails closed");}finally{File.WriteAllBytes(registry,original);AssetDatabase.ImportAsset(registry,ImportAssetOptions.ForceUpdate);}
            check(UIClarityGuard.Validate(out _).Count==0,"Fault probes restore clean baseline");new UIClarityBuildGate().OnPreprocessBuild(null);
            var a=DailyGiftDesignAssets.Load();foreach(var sprite in new[]{a.chest,a.hammer,a.rocket,a.bomb,a.orb,a.check})check(sprite.texture.mipmapCount>1&&sprite.texture.filterMode==FilterMode.Trilinear,"Filtered native texture "+sprite.name);
            check(a.check.rect.width==232&&a.check.rect.height==236,"High-resolution shared badge bound");check(a.hero.border.x/6==18,"Physical slice corner unchanged");
            File.WriteAllText(Path.Combine(Output,"Build_Import_Audit.txt"),log.ToString());r.status="PASS_NATIVE_UI_CLARITY_CHECKS";
        }catch(Exception e){r.error=e.ToString();r.status="FAIL_NATIVE_UI_CLARITY_CHECKS";}File.WriteAllText(Path.Combine(Output,"Checks.json"),JsonUtility.ToJson(r,true));if(r.error!=null)throw new Exception(r.error);}
    }
}
#endif
