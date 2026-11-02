#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using HeartOfTheRain.App.Teams;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace HeartOfTheRain.Verification {
 public static class TeamsLifecycle113Verification {
  [Serializable] sealed class Report {public string status="RUNNING",unity,scope="Actual pinned Unity Editor import and asset lookup only; no device or runtime acceptance.";public int checks;public List<string> errors=new List<string>();}
  public static void Run(){var report=new Report{unity=Application.unityVersion};string root=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW113_OUT")??throw new InvalidOperationException("ExplicitReview113OutputRequired"));
   try {if(Application.unityVersion!="2022.3.62f3")throw new InvalidOperationException("WrongUnityVersion");EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);string basePath="Assets/HeartOfTheRain/App/TeamsLifecycle/Data/";string[] files={"TeamsLifecycle_AssetRoles.json","TeamsLifecycle_Layout.json","TeamsLifecycle_Motion.json","TeamsLifecycle_ScreenRegistry.json","TeamsLifecycle_StateContract.json","TeamsLifecycle_Strings.json"};string[] guid={"03931055518d5c85a31ddd50e53b0e4f","8f2fdf81e5f650a7bd15d2a4fdd6c09d","71d0c26555615a4189cf80847ad94408","f2050d19f47650c8b786eb5f6dc5cc5a","6656a1b70f01507fb38ef03bba3558f3","1cb573a0d4ce5bdaae9b590884bc8fb5"};for(int i=0;i<files.Length;i++){var obj=AssetDatabase.LoadAssetAtPath<TextAsset>(basePath+files[i]);if(!obj||AssetDatabase.AssetPathToGUID(basePath+files[i])!=guid[i]||string.IsNullOrEmpty(obj.text))throw new InvalidOperationException("MissingOriginalPackageData:"+files[i]);report.checks+=3;}var assets=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");if(!assets||!assets.Find("TA_Panel_Blue")||!assets.Find("TA_Panel_Cream")||!assets.Find("TA_Button_Red")||!assets.Find("TA_Badge_banners"))throw new InvalidOperationException("MissingExistingApprovedArt");report.checks+=5;}
   catch(Exception ex){report.errors.Add(ex.ToString());}finally{report.status=report.errors.Count==0?"PASS_NATIVE_TEAMS_LIFECYCLE_IMPORT113":"FAIL_NATIVE_TEAMS_LIFECYCLE_IMPORT113";Directory.CreateDirectory(Path.Combine(root,"Native"));File.WriteAllText(Path.Combine(root,"Native","TeamsLifecycle113_Import.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));}EditorApplication.Exit(report.errors.Count==0?0:1);
  }
 }
}
#endif
