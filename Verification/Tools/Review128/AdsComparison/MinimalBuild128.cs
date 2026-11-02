#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class MinimalBuild128 {
    public static void Run(){
        string output=Environment.GetEnvironmentVariable("HOTR_ADSMIN_OUT");
        int code=1;
        try{
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android,"com.heartoftherain.adsmin128");
            PlayerSettings.productName="Ads Minimal 128";
            PlayerSettings.Android.useCustomKeystore=false;
            PlayerSettings.Android.bundleVersionCode=128;PlayerSettings.bundleVersion="128.0";
            PlayerSettings.Android.minSdkVersion=(AndroidSdkVersions)26;
            PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)int.Parse(Environment.GetEnvironmentVariable("HOTR_ADSMIN_TARGET")??"36");
            PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android,ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;
            PlayerSettings.defaultInterfaceOrientation=UIOrientation.Portrait;
            PlayerSettings.SplashScreen.show=false;
            PlayerSettings.SetScriptingDefineSymbolsForGroup(BuildTargetGroup.Android,"APPMETRICA_ADAPTER_ADREVENUE_AUTOCOLLECTION_DISABLED;APPMETRICA_ADAPTER_ADREVENUE_AUTO_COLLECTION_DISABLED");
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var camera=new GameObject("Camera",typeof(Camera)).GetComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.12f,.2f,.3f);
            new GameObject("MinimalRewarded128",typeof(MinimalRewarded128));
            const string path="Assets/Minimal128/Minimal128.unity";EditorSceneManager.SaveScene(scene,path);
            string apk=Path.GetFullPath("Builds/AdsMinimal128_"+Environment.GetEnvironmentVariable("HOTR_ADSMIN_TAG")+".apk");Directory.CreateDirectory(Path.GetDirectoryName(apk));
            var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{path},locationPathName=apk,target=BuildTarget.Android,options=BuildOptions.Development});
            File.WriteAllText(Path.Combine(output,"result.txt"),result.summary.result+" errors="+result.summary.totalErrors+" warnings="+result.summary.totalWarnings+" bytes="+result.summary.totalSize+"\n"+apk+"\n");
            code=result.summary.result==BuildResult.Succeeded?0:1;
        }catch(Exception error){File.WriteAllText(Path.Combine(output,"result.txt"),"EXCEPTION "+error.GetType().Name+" "+error.Message);}
        if(Application.isBatchMode)EditorApplication.Exit(code);
    }
}
#endif
