#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 [InitializeOnLoad] public static class CrateBurstPlayVerification {
  const string Key="HOTR.CrateBurst.NativePlay";static bool launched;static double deadline;
  static CrateBurstPlayVerification(){if(SessionState.GetBool(Key,false)){EditorApplication.update+=Tick;deadline=EditorApplication.timeSinceStartup+240;}}
  public static void Run(){SessionState.SetBool(Key,true);EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.isPlaying=true;}
  static void Tick(){if(!EditorApplication.isPlaying||EditorApplication.isCompiling||launched)return;if(EditorApplication.timeSinceStartup>deadline){EditorApplication.Exit(1);return;}launched=true;var probe=new GameObject("Crate burst native lifecycle verification").AddComponent<CrateBurstProbe>();probe.suppliedAssets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");probe.Completed=report=>{bool ok=report.status=="PASS_CRATE_BURST_PLAYBACK"&&report.rows.Count==6&&report.rows.TrueForAll(r=>r.renderersCreated==0&&r.crateSpritesCreated==0&&r.poolReady==r.poolEnd);string path=Path.GetFullPath("../Verification/Evidence/CrateBurst/NativePlay.json");File.WriteAllText(path,JsonUtility.ToJson(report,true));SessionState.EraseBool(Key);EditorApplication.Exit(ok?0:1);};}
 }
}
#endif
