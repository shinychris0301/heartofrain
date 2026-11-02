#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 [InitializeOnLoad] public static class CascadeTimingPlayVerification {
  const string Key="HOTR.CascadeTiming.Play";static bool launched;
  static CascadeTimingPlayVerification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
  public static void Run(){SessionState.SetBool(Key,true);EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.isPlaying=true;}
  static void Tick(){if(!EditorApplication.isPlaying||EditorApplication.isCompiling||launched)return;launched=true;var probe=new GameObject("Native cascade playback review").AddComponent<CascadeTimingProbe>();probe.suppliedAssets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");probe.Completed=r=>{File.WriteAllText(Path.GetFullPath("../Verification/Evidence/CascadeResponsiveness/NativePlay.json"),JsonUtility.ToJson(r,true));SessionState.EraseBool(Key);EditorApplication.Exit(r.errors.Count==0&&r.rows.Count==6?0:1);};}
 }
}
#endif
