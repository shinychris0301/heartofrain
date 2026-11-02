#if UNITY_EDITOR
using System;using System.IO;using UnityEngine;using UnityEditor;using UnityEditor.SceneManagement;
namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class RainCupPlayVerification {
        const string Key="HOTR.RainCup.Native";static double started;
        static RainCupPlayVerification(){if(SessionState.GetBool(Key,false)){started=EditorApplication.timeSinceStartup;EditorApplication.update+=Tick;}}
        public static void Run(){string id=Guid.NewGuid().ToString("N");SessionState.SetBool(Key,true);SessionState.SetString(Key+".id",id);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");Directory.CreateDirectory(Application.persistentDataPath);File.WriteAllText(Path.Combine(Application.persistentDataPath,RainCupVerificationProbe.RequestName),JsonUtility.ToJson(new RainCupVerificationProbe.Request{runId=id,mode="Auto"}));EditorApplication.isPlaying=true;}
        static void Tick(){if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;string path=Path.Combine(RainCupVerificationProbe.Folder(SessionState.GetString(Key+".id",""),"Auto"),"Report.json");if(File.Exists(path)){var report=JsonUtility.FromJson<RainCupVerificationProbe.Report>(File.ReadAllText(path));if(report.status.StartsWith("PASS")||report.status.StartsWith("FAIL")){string output=Path.GetFullPath("../Verification/Evidence/RainCup/Native_Play_Checks.json");Directory.CreateDirectory(Path.GetDirectoryName(output));File.Copy(path,output,true);Finish(report.status.StartsWith("PASS")?0:1);}}else if(EditorApplication.timeSinceStartup-started>270){Debug.LogError("RainCup verification timed out");Finish(1);}}
        static void Finish(int code){SessionState.EraseBool(Key);EditorApplication.update-=Tick;EditorApplication.Exit(code);}
    }
}
#endif
