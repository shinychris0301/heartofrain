#if UNITY_EDITOR
using System;using System.IO;using UnityEngine;using UnityEditor;using UnityEditor.SceneManagement;
namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class DailyGiftPlayVerification {
        const string Key="HOTR.DailyGift.Native";static double started;
        static DailyGiftPlayVerification(){if(SessionState.GetBool(Key,false)){started=EditorApplication.timeSinceStartup;EditorApplication.update+=Tick;}}
        public static void Run(){string id=Guid.NewGuid().ToString("N");SessionState.SetBool(Key,true);SessionState.SetString(Key+".id",id);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");Directory.CreateDirectory(Application.persistentDataPath);File.WriteAllText(Path.Combine(Application.persistentDataPath,DailyGiftVerificationProbe.RequestName),JsonUtility.ToJson(new DailyGiftVerificationProbe.Request{runId=id,mode="Auto"}));EditorApplication.isPlaying=true;}
        static void Tick(){if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;string path=Path.Combine(DailyGiftVerificationProbe.Folder(SessionState.GetString(Key+".id",""),"Auto"),"Report.json");if(File.Exists(path)){var report=JsonUtility.FromJson<DailyGiftVerificationProbe.Report>(File.ReadAllText(path));if(report.status.StartsWith("PASS")||report.status.StartsWith("FAIL")){string output=Path.GetFullPath("../Verification/Evidence/DailyGift/Native_Play_Checks.json");Directory.CreateDirectory(Path.GetDirectoryName(output));File.Copy(path,output,true);Finish(report.status.StartsWith("PASS")?0:1);}}else if(EditorApplication.timeSinceStartup-started>330){Debug.LogError("Daily Gift connected verification timed out");Finish(1);}}
        static void Finish(int code){SessionState.EraseBool(Key);EditorApplication.update-=Tick;EditorApplication.Exit(code);}
    }
}
#endif
