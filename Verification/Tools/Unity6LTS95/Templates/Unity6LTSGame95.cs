#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Launch;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.M46;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace HeartOfTheRain.Verification {
    // Import only into .verification-cache/Unity6LTS95/Game after the actual smoke passes.
    public static class Unity6LTSGame95 {
        const string Package="com.heartoftherain.unity6lts95",Company="HeartRainUnity6LTSReview95";
        const string RussianName="\u0421\u0435\u0440\u0434\u0446\u0435 \u0434\u043e\u0436\u0434\u044f";
        [Serializable] public sealed class Check {public string name;public bool passed;}
        [Serializable] public sealed class Settings {
            public string packageName,companyName,productName,backend,architectures,applicationEntry,orientation;
            public int minApi,targetApi;public bool showSplashScreen,showUnityLogo,portraitOnly,bundle,customKeystore,sdkFreeDefines;
            public string[] enabledScenes,legacyIconGuids;
        }
        [Serializable] public sealed class Report {
            public string status,operation,utc,unity,project,error,apk,apkSHA256,buildResult,buildPackageName,sdk,jdk,ndk,gradle;
            public string scope="Isolated full-game LTS95 settings/startup-model inspection and optional Development Android compile. Original2022 API implementations are preserved. No original main/6000.6 project migration, game-playthrough, pixel/performance, provider/backend, device or production acceptance.";
            public int exitCode=1,errors,warnings;public long bytes;public bool development;
            public Settings before,after;public List<Check> checks=new List<Check>();
        }
        sealed class MemorySettings:ISettingsStore {
            public int stage,complete,writes,flushes;
            public int Read(string key,int fallback)=>key==FirstStartSession.StageKey?stage:key==FirstStartSession.CompleteKey?complete:fallback;
            public void Write(string key,int value){writes++;throw new InvalidOperationException("Read-only startup fixture must not write tutorial state");}
            public void Flush(){flushes++;throw new InvalidOperationException("Read-only startup fixture must not flush tutorial state");}
        }
        static void CheckThat(Report report,bool passed,string name){report.checks.Add(new Check{name=name,passed=passed});if(!passed)throw new InvalidOperationException(name);}
        static string Full(string path)=>Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar);
        static bool Under(string path,string parent)=>Full(path).StartsWith(Full(parent)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase);
        static string Hash(string path){using(var input=File.OpenRead(path))using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(input)).Replace("-","").ToLowerInvariant();}
        public static void Configure()=>Run("Configure",true,false);
        public static void Inspect()=>Run("Inspect",false,false);
        public static void BuildDevelopment()=>Run("BuildDevelopment",false,true);
        static Settings ReadSettings(){
            var defines=PlayerSettings.GetScriptingDefineSymbols(NamedBuildTarget.Android).Split(';');
            // Keep the exact2022 legacy icon API until an actual6.3 compiler proves a port necessary.
            var icons=PlayerSettings.GetPlatformIcons(BuildTargetGroup.Android,AndroidPlatformIconKind.Legacy);
            return new Settings{packageName=PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android),companyName=PlayerSettings.companyName,productName=PlayerSettings.productName,
                backend=PlayerSettings.GetScriptingBackend(NamedBuildTarget.Android).ToString(),architectures=PlayerSettings.Android.targetArchitectures.ToString(),
                minApi=(int)PlayerSettings.Android.minSdkVersion,targetApi=(int)PlayerSettings.Android.targetSdkVersion,applicationEntry=PlayerSettings.Android.applicationEntry.ToString(),
                orientation=PlayerSettings.defaultInterfaceOrientation.ToString(),portraitOnly=HeartOfTheRain.App.Editor.PortraitBuildPolicy.IsPortraitOnly,
                showSplashScreen=PlayerSettings.SplashScreen.show,showUnityLogo=PlayerSettings.SplashScreen.showUnityLogo,bundle=EditorUserBuildSettings.buildAppBundle,customKeystore=PlayerSettings.Android.useCustomKeystore,
                sdkFreeDefines=!defines.Contains("HOTR_RUSTORE_PAY")&&!defines.Contains("HOTR_YANDEX_ADS"),enabledScenes=EditorBuildSettings.scenes.Where(s=>s.enabled).Select(s=>s.path).ToArray(),
                legacyIconGuids=icons.Select(slot=>{var texture=slot.GetTexture();return texture?AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(texture)):"";}).ToArray()};
        }
        static void Run(string operation,bool configure,bool build){
            var report=new Report{operation=operation,utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,status="FAIL_NATIVE_LTS95_GAME_"+operation.ToUpperInvariant()};string output=null;
            try{
                string project=Full(Path.Combine(Application.dataPath,".."));report.project=project;var info=new DirectoryInfo(project);var migration=info.Parent;var cache=migration==null?null:migration.Parent;var workspace=cache==null?null:cache.Parent;
                CheckThat(report,info.Name=="Game"&&migration!=null&&migration.Name=="Unity6LTS95"&&cache!=null&&cache.Name==".verification-cache"&&workspace!=null&&File.Exists(Path.Combine(workspace.FullName,"AGENTS.md")),"Only exact isolated LTS95 full-game project permitted");
                CheckThat(report,report.unity=="6000.3.27f1","Exact approved LTS engine required");
                string supplied=Environment.GetEnvironmentVariable("HOTR_LTS95_GAME_OUT");CheckThat(report,!string.IsNullOrEmpty(supplied)&&Path.IsPathRooted(supplied),"Explicit output required");output=Full(supplied);
                CheckThat(report,Under(output,Path.Combine(workspace.FullName,"Verification","Evidence","Unity6LTS95","GameRuns")),"Fresh contained95 full-game evidence required");Directory.CreateDirectory(output);
                report.before=ReadSettings();CheckThat(report,report.before.companyName==Company,"Company identity was isolated before first Editor import");
                if(configure){
                    PlayerSettings.companyName=Company;PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,Package);
                    PlayerSettings.SplashScreen.showUnityLogo=false;PlayerSettings.SplashScreen.show=false;
                    PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android,ScriptingImplementation.IL2CPP);PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;
                    PlayerSettings.Android.minSdkVersion=(AndroidSdkVersions)26;PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)36;PlayerSettings.Android.applicationEntry=AndroidApplicationEntry.Activity;
                    PlayerSettings.Android.useCustomKeystore=false;EditorUserBuildSettings.buildAppBundle=false;HeartOfTheRain.App.Editor.PortraitBuildPolicy.Configure();AssetDatabase.SaveAssets();
                }
                Verify(report);Startup(report);
                if(build){
                    CheckThat(report,EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android&&BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Android,BuildTarget.Android),"Actual matching Android target support required");
                    string requested=Environment.GetEnvironmentVariable("HOTR_LTS95_GAME_APK");CheckThat(report,!string.IsNullOrEmpty(requested)&&Path.IsPathRooted(requested),"Explicit private Development APK required");report.apk=Full(requested);
                    CheckThat(report,Under(report.apk,Path.Combine(project,"Builds"))&&Path.GetFileName(report.apk)=="HeartOfTheRain_LTS95_Development.apk"&&!File.Exists(report.apk),"Fresh private full-game Development APK only");Directory.CreateDirectory(Path.GetDirectoryName(report.apk));
                    report.buildPackageName=PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android);CheckThat(report,report.buildPackageName==Package,"Only isolated review package may be built");
                    var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=EditorBuildSettings.scenes.Where(s=>s.enabled).Select(s=>s.path).ToArray(),locationPathName=report.apk,target=BuildTarget.Android,options=BuildOptions.Development|BuildOptions.AllowDebugging});
                    report.buildResult=result.summary.result.ToString();report.errors=(int)result.summary.totalErrors;report.warnings=(int)result.summary.totalWarnings;report.development=(result.summary.options&BuildOptions.Development)!=0;
                    CheckThat(report,result.summary.result==BuildResult.Succeeded&&report.errors==0&&report.development&&File.Exists(report.apk),"Actual Development Android build must succeed with zero errors");
                    report.bytes=new FileInfo(report.apk).Length;report.apkSHA256=Hash(report.apk);CheckThat(report,report.bytes>0,"Actual full-game APK must be nonempty");Verify(report);
                }
                report.after=ReadSettings();report.status="PASS_NATIVE_LTS95_GAME_"+operation.ToUpperInvariant();report.exitCode=0;
            }catch(Exception error){report.error=error.ToString();try{report.after=ReadSettings();}catch{}}
            if(output!=null)using(var file=new FileStream(Path.Combine(output,operation+".json"),FileMode.CreateNew,FileAccess.Write,FileShare.Read))using(var writer=new StreamWriter(file,new UTF8Encoding(false)))writer.Write(JsonUtility.ToJson(report,true));
            else Debug.LogError("LTS95 game fixture refused before safe evidence output available");EditorApplication.Exit(report.exitCode);
        }
        static void Verify(Report report){
            string android=Path.Combine(EditorApplication.applicationContentsPath,"PlaybackEngines","AndroidPlayer");
            report.sdk=Full(AndroidExternalToolsSettings.sdkRootPath);report.jdk=Full(AndroidExternalToolsSettings.jdkRootPath);report.ndk=Full(AndroidExternalToolsSettings.ndkRootPath);report.gradle=Full(AndroidExternalToolsSettings.gradlePath);
            CheckThat(report,Under(report.sdk,android)&&Under(report.jdk,android)&&Under(report.ndk,android)&&Under(report.gradle,android),"Actual full-game tool paths remain embedded in this LTS Editor; getters only");
            var settings=ReadSettings();CheckThat(report,settings.companyName==Company&&settings.packageName==Package,"Distinct LTS95 Editor and Android identities");
            CheckThat(report,settings.productName==RussianName,"Approved Russian visible app name preserved");
            CheckThat(report,!settings.showSplashScreen&&!settings.showUnityLogo,"Both supported native Unity splash getters disabled");
            CheckThat(report,settings.portraitOnly&&settings.applicationEntry==AndroidApplicationEntry.Activity.ToString(),"Portrait-only original UnityPlayerActivity retained");
            CheckThat(report,settings.backend=="IL2CPP"&&settings.architectures=="ARM64"&&settings.minApi==26&&settings.targetApi==36,"Exact ARM64 IL2CPP API26 to36 configuration");
            CheckThat(report,!settings.bundle&&!settings.customKeystore&&settings.sdkFreeDefines,"Internal SDK-free APK; no custom signing or provider defines");
            var expected=new[]{LaunchPage.ScenePath,LaunchPage.GameScenePath};CheckThat(report,settings.enabledScenes.SequenceEqual(expected)&&expected.All(path=>AssetDatabase.LoadAssetAtPath<SceneAsset>(path)),"Original Launch then First Start scene routing preserved");
            string icon=AssetDatabase.AssetPathToGUID("Assets/HeartOfTheRain/App/Launch/Art/App_Icon_R1.png");CheckThat(report,!string.IsNullOrEmpty(icon)&&settings.legacyIconGuids.Length>0&&settings.legacyIconGuids.All(value=>value==icon),"Existing legacy icon slots retain exact approved artwork GUID");
            CheckThat(report,AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/HeartOfTheRain/App/Launch/Art/Title_Logo_RU_R1.png")&&AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/HeartOfTheRain/App/Launch/Art/Opening_Key_Art_R1.png"),"Approved Russian title and original opening art import");
            CheckThat(report,GameLocale.DefaultIndex==4&&GameLocale.Codes[4]=="ru"&&GameLocale.DisplayIndexAt(0)==4&&GameLocale.ResolveStored(-1)==4&&GameLocale.ResolveStored(999)==4,"Russian default and first language row preserved");
            for(int index=0;index<5;index++)CheckThat(report,GameLocale.ResolveStored(index)==index,"Existing valid saved language index retained: "+index);
        }
        static void Startup(Report report){
            var asset=AssetDatabase.LoadAssetAtPath<FirstStartAssets>("Assets/HeartOfTheRain/App/FirstStart/FirstStartAssets.asset");CheckThat(report,asset&&asset.lessons!=null&&asset.lessons.Length==3&&asset.lessons.All(value=>value),"Three approved tutorial lessons import");
            var lessons=asset.lessons.Select(value=>JsonUtility.FromJson<LevelData>(value.text)).ToArray();
            Route(report,"Fresh",new MemorySettings(),lessons,0,FirstStartStage.Prologue);Route(report,"Rocket",new MemorySettings{stage=(int)FirstStartStage.Rocket},lessons,0,FirstStartStage.Rocket);
            Route(report,"Returning",new MemorySettings(),lessons,8,FirstStartStage.Complete);Route(report,"Completed",new MemorySettings{complete=1},lessons,0,FirstStartStage.Complete);
        }
        static void Route(Report report,string label,MemorySettings store,LevelData[] lessons,int completed,FirstStartStage expected){
            var session=new FirstStartSession(store,lessons,completed);CheckThat(report,session.Stage==expected&&store.writes==0&&store.flushes==0,label+" preserves original model route without state writes");
            if(session.Practice){CheckThat(report,session.Board!=null&&session.Board.Moves>0,label+" constructs approved tutorial board");session.Board.Validate();}
            else CheckThat(report,session.Board==null,label+" avoids unrelated practice allocation");
        }
    }
}
#endif
