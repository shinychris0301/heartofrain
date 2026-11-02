"""Prepare an isolated Android IL2CPP parity fixture from exact worker inputs."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / '.verification-cache/ServerReplay83Android/Project'

BOOT = r'''using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using HeartOfTheRain.App.ServerVerification;

public sealed class Replay83AndroidProof : MonoBehaviour {
    [Serializable] sealed class Index { public Item[] fixtures; public string pinsSHA256; }
    [Serializable] sealed class Item { public string name,jobSHA256,expectedSHA256; }
    [Serializable] sealed class Case { public string name,checkpointSHA256,outcome; public int actions; }
    [Serializable] sealed class Report { public string status,utc,unity,scopeHash,pinsSHA256,error; public int pid,levels,actions,tools,continues,starting; public bool androidIl2cpp,ordinaryGameMutated; public List<Case> cases=new List<Case>(); }
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Boot() {
#if UNITY_ANDROID && !UNITY_EDITOR && HOTR_REPLAY83_ANDROID_PROOF
        new GameObject("ExplicitReplay83AndroidProof").AddComponent<Replay83AndroidProof>();
#endif
    }
    IEnumerator Start() {
        var report=new Report{status="FAIL_ANDROID_IL2CPP_REPLAY83_PARITY",utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
        string scope=null;
        try {
            using(var player=new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
            using(var activity=player.GetStatic<AndroidJavaObject>("currentActivity"))
            using(var intent=activity.Call<AndroidJavaObject>("getIntent")) scope=intent.Call<string>("getStringExtra","replay83_scope");
            if(scope==null||!Regex.IsMatch(scope,@"\Aqa83-[0-9a-f]{32}\z"))throw new InvalidOperationException("ExplicitScopeRequired");
            report.scopeHash=PinnedReplayEngine.SHA(scope);report.androidIl2cpp=true;
            using(var process=new AndroidJavaClass("android.os.Process"))report.pid=process.CallStatic<int>("myPid");
        }catch(Exception){yield break;}
        string output=Path.Combine(Application.persistentDataPath,"Replay83","Report.json");
        var seen=new HashSet<int>(); Index index=null; ReplayPins pins=null;string directory=null;
        try {
            index=JsonUtility.FromJson<Index>(Resources.Load<TextAsset>("Replay83/Index").text);
            directory=Path.Combine(Application.temporaryCachePath,"Replay83",scope);Directory.CreateDirectory(Path.Combine(directory,"Levels"));
            File.WriteAllBytes(Path.Combine(directory,"manifest.json"),Resources.Load<TextAsset>("Replay83/Pins").bytes);
            for(int n=1;n<=50;n++)File.WriteAllBytes(Path.Combine(directory,"Levels","C01_L"+n.ToString("000")+".json"),Resources.Load<TextAsset>("Replay83/Levels/C01_L"+n.ToString("000")).bytes);
            string hash;pins=PinnedReplayEngine.ReadPins(directory,out hash);report.pinsSHA256=hash;
            if(index==null||index.fixtures==null||index.fixtures.Length!=371||hash!=index.pinsSHA256)throw new InvalidOperationException("FixturePinsDiffer");
        }catch(Exception error){report.error="FixtureSetup:"+error.GetType().Name;}
        if(report.error==null)foreach(var item in index.fixtures){
            try {
                byte[] bytes=Resources.Load<TextAsset>("Replay83/Jobs/"+item.name).bytes;
                byte[] expectedBytes=Resources.Load<TextAsset>("Replay83/Expected/"+item.name).bytes;
                if(PinnedReplayEngine.SHA(bytes)!=item.jobSHA256||PinnedReplayEngine.SHA(expectedBytes)!=item.expectedSHA256)throw new InvalidOperationException("FixtureBytesDiffer");
                var job=PinnedReplayEngine.ParseJob(Encoding.UTF8.GetString(bytes));
                var expected=JsonUtility.FromJson<ReplayOutput>(Encoding.UTF8.GetString(expectedBytes));
                var result=PinnedReplayEngine.Execute(job,PinnedReplayEngine.Level(directory,pins.levels[job.level-1]),pins.levels[job.level-1],report.pinsSHA256,item.jobSHA256).output;
                if(JsonUtility.ToJson(result)!=JsonUtility.ToJson(expected))throw new InvalidOperationException("FullCheckpointOrOutcomeDiffers");
                seen.Add(job.level);report.actions+=job.actions.Length;report.tools+=job.actions.Count(x=>x.kind=="Tool");report.continues+=job.actions.Count(x=>x.kind=="Continue");report.starting+=job.starting.Sum();
                report.cases.Add(new Case{name=item.name,checkpointSHA256=result.checkpointSHA256,outcome=result.outcome,actions=result.actions});
            }catch(Exception error){report.error=item.name+":"+error.GetType().Name;break;}
            yield return null;
        }
        report.levels=seen.Count;
        if(report.error==null&&report.cases.Count==371&&report.levels==50&&report.tools==20&&report.continues>0)report.status="PASS_ANDROID_IL2CPP_REPLAY83_FULL_NATIVE_CORPUS";
        Directory.CreateDirectory(Path.GetDirectoryName(output));File.WriteAllText(output,JsonUtility.ToJson(report,true),new UTF8Encoding(false));
        Debug.Log("REPLAY83_EXPLICIT_ANDROID_PROOF_COMPLETE");
    }
}
'''

BUILD = r'''#if UNITY_EDITOR
using System;
using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
public static class Replay83AndroidBuild {
    [Serializable] sealed class Report {public string status,unity,package,result;public int errors,warnings;public bool il2cpp,development;}
    public static void Build(){
        Directory.CreateDirectory("Build");var output=new Report{unity=Application.unityVersion,package="com.heartoftherain.replay83fixture",il2cpp=true,development=false,status="FAIL_ANDROID_REPLAY83_ASSEMBLY"};
        try {
            if(Application.unityVersion!="2022.3.62f3")throw new InvalidOperationException();
            EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Android,BuildTarget.Android);
            PlayerSettings.companyName="HeartOfTheRainVerification";PlayerSettings.productName="Replay83QA";
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android,output.package);PlayerSettings.bundleVersion="83.0";PlayerSettings.Android.bundleVersionCode=83;
            PlayerSettings.Android.minSdkVersion=AndroidSdkVersions.AndroidApiLevel26;PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)35;
            PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;PlayerSettings.Android.useCustomKeystore=false;
            PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android,ScriptingImplementation.IL2CPP);PlayerSettings.defaultInterfaceOrientation=UIOrientation.Portrait;
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorSceneManager.SaveScene(scene,"Assets/Fixture.unity");
            var build=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{"Assets/Fixture.unity"},locationPathName="Build/Replay83.apk",target=BuildTarget.Android,options=BuildOptions.None,extraScriptingDefines=new[]{"HOTR_REPLAY83_ANDROID_PROOF"}});
            output.result=build.summary.result.ToString();output.errors=(int)build.summary.totalErrors;output.warnings=(int)build.summary.totalWarnings;
            if(build.summary.result==BuildResult.Succeeded)output.status="PASS_ANDROID_REPLAY83_ASSEMBLY";
        }catch(Exception error){output.result=error.GetType().Name;}
        File.WriteAllText("Build/Build.json",JsonUtility.ToJson(output,true));EditorApplication.Exit(output.status.StartsWith("PASS_")?0:1);
    }
}
#endif
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if PROJECT.exists():
        raise SystemExit('Preserve the previous project; select a new fixture attempt before preparing again')
    worker = ROOT / '.verification-cache/PinnedReplay83/Project'
    native_path = ROOT / 'Verification/Evidence/ServerReplay83/Native/ReplayNative.json'
    native = json.loads(native_path.read_text('utf-8'))
    if native['status'] != 'PASS_PINNED_NATIVE_REPLAY_CORPUS':
        raise SystemExit('Verified native fixtures required')
    PROJECT.mkdir(parents=True)
    model = PROJECT / 'Assets/PinnedReplayModel'
    shutil.copytree(worker / 'Assets/PinnedReplayModel', model)
    (model / 'Replay83AndroidProof.cs').write_text(BOOT, encoding='utf-8')
    editor = PROJECT / 'Assets/Editor'
    editor.mkdir(parents=True)
    (editor / 'Replay83AndroidBuild.cs').write_text(BUILD, encoding='utf-8')
    resources = PROJECT / 'Assets/Resources/Replay83'
    for path in ('Levels', 'Jobs', 'Expected'):
        (resources / path).mkdir(parents=True)
    shutil.copy2(worker / 'ReplayPins/manifest.json', resources / 'Pins.bytes')
    for path in (worker / 'ReplayPins/Levels').glob('*.json'):
        shutil.copy2(path, resources / 'Levels' / (path.stem + '.bytes'))
    fixtures = []
    for fixture in native['fixtures']:
        job, expected = native_path.parent / fixture['job'], native_path.parent / fixture['expected']
        if sha(job) != fixture['jobSHA256']:
            raise SystemExit('Native fixture bytes changed')
        shutil.copy2(job, resources / 'Jobs' / (fixture['name'] + '.bytes'))
        shutil.copy2(expected, resources / 'Expected' / (fixture['name'] + '.bytes'))
        fixtures.append({'name': fixture['name'], 'jobSHA256': sha(job), 'expectedSHA256': sha(expected)})
    (resources / 'Index.json').write_text(json.dumps({'fixtures': fixtures, 'pinsSHA256': native['pinsSHA256']}), encoding='utf-8')
    settings, packages = PROJECT / 'ProjectSettings', PROJECT / 'Packages'
    settings.mkdir(); packages.mkdir()
    shutil.copy2(ROOT / 'Unity/ProjectSettings/ProjectVersion.txt', settings / 'ProjectVersion.txt')
    (packages / 'manifest.json').write_text('{"dependencies":{"com.unity.modules.jsonserialize":"1.0.0","com.unity.modules.androidjni":"1.0.0"}}', encoding='utf-8')
    inputs = {p.relative_to(PROJECT).as_posix(): sha(p) for p in sorted(PROJECT.rglob('*')) if p.is_file()}
    report = {'status': 'PREPARED_ANDROID_REPLAY83_PARITY_FIXTURE_NOT_BUILT', 'unity': '2022.3.62f3',
              'package': 'com.heartoftherain.replay83fixture', 'pinsSHA256': native['pinsSHA256'],
              'nativeReportSHA256': sha(native_path), 'fixtures': len(fixtures), 'inputSHA256': inputs,
              'scope': 'Exact isolated worker model sources and actual native synthetic fixtures; release Android IL2CPP build, no game UI or payment SDK'}
    (PROJECT.parent / 'Preparation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'inputs': len(inputs), 'fixtures': len(fixtures)}))


if __name__ == '__main__':
    main()
