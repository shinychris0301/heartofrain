#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace HeartOfTheRain.App.ServerVerification.Editor {
    // This generic builder is also copied into the isolated project. It must
    // never depend on a model assembly excluded from that project's Editor.
    public static class PinnedReplayBuild {
        const string WorkerRoot="Unity/Assets/HeartOfTheRain/App/ServerVerification/";
        public static readonly string[] ModelSources={
            "Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs",
            "Unity/Assets/HeartOfTheRain/M46/Runtime/BoardContinuation.cs",
            "Unity/Assets/HeartOfTheRain/M46/Runtime/StartingPowersPure.cs",
            "Unity/Assets/HeartOfTheRain/M48/Runtime/AdvancedObstacleRulesPure.cs",
            "Unity/Assets/HeartOfTheRain/Boosters/Runtime/BoosterRulesPure.cs",
            "Unity/Assets/HeartOfTheRain/M46/Runtime/ReviewPlan.cs",
            "Unity/Assets/HeartOfTheRain/M46/Runtime/LivePowerPlan.cs",
            "Unity/Assets/HeartOfTheRain/M46/Runtime/GoldenSeekerComboPlan.cs",
            "Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPlayback.cs",
            "Unity/Assets/HeartOfTheRain/M46/Runtime/LocalCascadePlayback.cs",
            "Unity/Assets/HeartOfTheRain/M46/Runtime/LocalCascadeContinuation.cs"};
        public static readonly string[] WorkerSources={"Runtime/PinnedReplayContract.cs","Runtime/ReplayStrictJson.cs","Runtime/PinnedReplayEngine.cs","Runtime/PinnedReplayWorker.cs"};
        [Serializable] sealed class Source {public string path,sha256;public long bytes;}
        [Serializable] sealed class Level {public int level,moves,columns,rows,tileSeed;public string id,path,sha256;}
        [Serializable] sealed class Pins {public int version=1;public string unity,scope;public Source[] sources;public Level[] levels;}
        [Serializable] sealed class Authored {public int globalLevel,movesProposal,columns,rows,tileSeed;public string id;}
        [Serializable] sealed class Catalog {public CatalogLevel[] levels;}
        [Serializable] sealed class CatalogLevel {public int level,moves,tileSeed;public string source,sourceSHA256,configHash;}
        [Serializable] sealed class Report {public string status="FAIL",code="",unity,project,output,pinsSHA256,executableSHA256,sceneRestoreError="";public int errors,warnings,modelFiles,workerFiles,levels;public bool settingsRestored,sceneSetupRestored,initialSceneSetupValid,emptySetupRecovered,ordinaryProjectUntouched,productionEnabled=false;}
        static string SHA(string path){using(var sha=SHA256.Create())using(var file=File.OpenRead(path))return BitConverter.ToString(sha.ComputeHash(file)).Replace("-","").ToLowerInvariant();}
        static void Write(string path,string text){Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllText(path,text,new System.Text.UTF8Encoding(false));}
        static void Copy(string from,string to){Directory.CreateDirectory(Path.GetDirectoryName(to));File.Copy(from,to,false);}
        static string Project(string root){string path=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REPLAY_PROJECT")??Path.Combine(root,".verification-cache/PinnedReplay83/Project"));string allowed=Path.GetFullPath(Path.Combine(root,".verification-cache"))+Path.DirectorySeparatorChar;if(!path.StartsWith(allowed,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Project must be a new ignored cache directory");return path;}
        public static void Prepare(){
            string root=Path.GetFullPath(".."),project=Project(root);var report=new Report{unity=Application.unityVersion,project=project};
            string result=Path.Combine(Path.GetDirectoryName(project),"Preparation.json");
            try{
                if(Application.unityVersion!="2022.3.62f3"||!File.Exists(Path.Combine(root,"AGENTS.md")))throw new InvalidOperationException("Wrong pinned source project");
                if(Directory.Exists(project)&&Directory.EnumerateFileSystemEntries(project).Any())throw new InvalidOperationException("Use a new project directory; preserve previous attempts");
                Directory.CreateDirectory(project);var sources=new List<Source>();
                foreach(string relative in ModelSources.Concat(WorkerSources.Select(p=>WorkerRoot+p))){string from=Path.Combine(root,relative);string to=Path.Combine(project,"Assets/PinnedReplayModel",Path.GetFileName(relative));Copy(from,to);Copy(from+".meta",to+".meta");if(SHA(from)!=SHA(to))throw new InvalidOperationException("Copy mismatch");sources.Add(new Source{path=relative,sha256=SHA(from),bytes=new FileInfo(from).Length});}
                string builder=WorkerRoot+"Editor/PinnedReplayBuild.cs";Copy(Path.Combine(root,builder),Path.Combine(project,"Assets/Editor/PinnedReplayBuild.cs"));Copy(Path.Combine(root,builder+".meta"),Path.Combine(project,"Assets/Editor/PinnedReplayBuild.cs.meta"));
                Write(Path.Combine(project,"Assets/PinnedReplayModel/PinnedReplayModel.asmdef"),"{\"name\":\"HeartOfTheRain.PinnedReplayWorker\",\"excludePlatforms\":[\"Editor\"],\"autoReferenced\":true}");
                Write(Path.Combine(project,"Packages/manifest.json"),"{\"dependencies\":{\"com.unity.modules.jsonserialize\":\"1.0.0\"}}");
                Copy(Path.Combine(root,"Unity/ProjectSettings/ProjectVersion.txt"),Path.Combine(project,"ProjectSettings/ProjectVersion.txt"));
                var catalog=JsonUtility.FromJson<Catalog>(File.ReadAllText(Path.Combine(root,"Backend/config/levels.json")));if(catalog?.levels==null||catalog.levels.Length!=50)throw new InvalidOperationException("Server catalog missing");var levels=new List<Level>();string pinsDirectory=Path.Combine(project,"ReplayPins");
                for(int i=1;i<=50;i++){
                    string id="C01_L"+i.ToString("000"),relative="Unity/Assets/HeartOfTheRain/M47/Data/Levels/"+id+".json",from=Path.Combine(root,relative),hash=SHA(from);var definition=JsonUtility.FromJson<Authored>(File.ReadAllText(from));var bound=catalog.levels[i-1];
                    if(definition.id!=id||definition.globalLevel!=i||bound.level!=i||bound.source!=relative||bound.sourceSHA256!=hash||bound.configHash!=hash||bound.moves!=definition.movesProposal||bound.tileSeed!=definition.tileSeed)throw new InvalidOperationException("Authored/server parameter mismatch");
                    string destination="Levels/"+id+".json";Copy(from,Path.Combine(pinsDirectory,destination));levels.Add(new Level{level=i,id=id,path=destination,sha256=hash,moves=definition.movesProposal,columns=definition.columns,rows=definition.rows,tileSeed=definition.tileSeed});
                }
                var pins=new Pins{unity=Application.unityVersion,scope="Exact approved model/planner dependency closure and50authored configurations; no art, UI, credentials, payment calls or gameplay-rule rewrite.",sources=sources.ToArray(),levels=levels.ToArray()};
                Write(Path.Combine(pinsDirectory,"manifest.json"),JsonUtility.ToJson(pins,true));report.pinsSHA256=SHA(Path.Combine(pinsDirectory,"manifest.json"));report.modelFiles=ModelSources.Length;report.workerFiles=WorkerSources.Length;report.levels=50;report.ordinaryProjectUntouched=true;report.status="PASS_PREPARED_PINNED_REPLAY_PROJECT";
            }catch(Exception){report.code="preparation_failed_preserve_attempt";}
            Write(result,JsonUtility.ToJson(report,true));if(report.status.StartsWith("FAIL",StringComparison.Ordinal))EditorApplication.Exit(1);
        }
        public static void Build(){
            string project=Path.GetFullPath("."),parent=Path.GetDirectoryName(project);var report=new Report{unity=Application.unityVersion,project=project};string result=Path.Combine(parent,"Build.json");var setup=EditorSceneManager.GetSceneManagerSetup();var originalBackend=PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone);
            try{
                if(Application.unityVersion!="2022.3.62f3"||!File.Exists("Assets/PinnedReplayModel/PinnedReplayModel.asmdef")||!Directory.Exists("ReplayPins"))throw new InvalidOperationException("Only the isolated pinned project may build this worker");
                if(!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone,BuildTarget.StandaloneWindows64))throw new InvalidOperationException("Pinned Windows module required");
                for(int i=0;i<UnityEngine.SceneManagement.SceneManager.sceneCount;i++)if(UnityEngine.SceneManagement.SceneManager.GetSceneAt(i).isDirty)throw new InvalidOperationException("Refusing unsaved editor scene changes");
                Directory.CreateDirectory("Assets/GeneratedReplayScene");var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);const string scenePath="Assets/GeneratedReplayScene/PinnedReplayWorker.unity";EditorSceneManager.SaveScene(scene,scenePath);
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x);report.output=Path.Combine(parent,"Worker/PinnedReplayWorker.exe");Directory.CreateDirectory(Path.GetDirectoryName(report.output));
                var build=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scenePath},locationPathName=report.output,target=BuildTarget.StandaloneWindows64,options=BuildOptions.None,extraScriptingDefines=new[]{"HOTR_SERVER_REPLAY_WORKER"}});report.errors=(int)build.summary.totalErrors;report.warnings=(int)build.summary.totalWarnings;if(build.summary.result!=BuildResult.Succeeded)throw new InvalidOperationException("Build failed");
                string destination=Path.Combine(Path.GetDirectoryName(report.output),"ReplayPins");if(Directory.Exists(destination))throw new InvalidOperationException("Preserve existing built pins; choose a new attempt");
                foreach(string from in Directory.GetFiles("ReplayPins","*",SearchOption.AllDirectories))Copy(from,Path.Combine(destination,from.Substring("ReplayPins".Length+1)));
                report.pinsSHA256=SHA(Path.Combine(destination,"manifest.json"));report.executableSHA256=SHA(report.output);report.status="PASS_PINNED_WINDOWS_REPLAY_BUILD";
            }catch(Exception){report.code="worker_build_failed_preserve_attempt";}
            finally{
                try{PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,originalBackend);report.settingsRestored=PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone)==originalBackend;}
                catch(Exception){report.status="FAIL";report.code="isolated_settings_restore_failed";}
                try{
                    report.initialSceneSetupValid=setup.Length>0&&setup.Count(s=>s.isActive&&s.isLoaded)==1&&setup.Where(s=>s.isLoaded).All(s=>!string.IsNullOrEmpty(s.path));
                    if(report.initialSceneSetupValid){EditorSceneManager.RestoreSceneManagerSetup(setup);report.sceneSetupRestored=true;}
                    else{EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);report.emptySetupRecovered=true;}
                }catch(Exception){report.status="FAIL";report.code="isolated_scene_restore_failed";report.sceneRestoreError="restore_failed";try{EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);report.emptySetupRecovered=true;}catch(Exception){report.sceneRestoreError="restore_and_empty_scene_recovery_failed";}}
                finally{Write(result,JsonUtility.ToJson(report,true));}
            }
            if(report.status.StartsWith("FAIL",StringComparison.Ordinal))EditorApplication.Exit(1);
        }
    }
}
#endif
