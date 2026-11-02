#if UNITY_EDITOR
using System;using System.IO;using System.Linq;using System.Collections.Generic;using UnityEngine;using UnityEditor;using UnityEditor.SceneManagement;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class ProfileEventPlayVerification {
        const string Key="HOTR.ProfileEvents.Native";static double started;
        [Serializable] sealed class Report {public string utc,status,unity,scope="Native Unity Play Mode: existing isolated Rain Cup Auto fixture uses seeded test tools on authored level 11; event feed then reconciles live model-win and reward receipts. No natural-play balance, Android or rendering certification.";public int checks,fixtureChecks,eventCount;public List<string> passed=new List<string>(),failures=new List<string>();}
        static ProfileEventPlayVerification(){if(SessionState.GetBool(Key,false)){started=EditorApplication.timeSinceStartup;EditorApplication.update+=Tick;}}
        public static void Run(){string id=Guid.NewGuid().ToString("N");SessionState.SetBool(Key,true);SessionState.SetString(Key+".id",id);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");Directory.CreateDirectory(Application.persistentDataPath);File.WriteAllText(Path.Combine(Application.persistentDataPath,RainCupVerificationProbe.RequestName),JsonUtility.ToJson(new RainCupVerificationProbe.Request{runId=id,mode="Auto"}));EditorApplication.isPlaying=true;}
        static void Check(Report r,bool ok,string name){r.checks++;if(!ok)throw new InvalidOperationException(name);r.passed.Add(name);}
        static void Tick(){
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
            string id=SessionState.GetString(Key+".id",""),path=Path.Combine(RainCupVerificationProbe.Folder(id,"Auto"),"Report.json");
            if(!File.Exists(path)){if(EditorApplication.timeSinceStartup-started>300)Finish(new Report{failures=new List<string>{"Fixture timed out"}});return;}
            var fixture=JsonUtility.FromJson<RainCupVerificationProbe.Report>(File.ReadAllText(path));if(!fixture.status.StartsWith("PASS")&&!fixture.status.StartsWith("FAIL"))return;
            var r=new Report{fixtureChecks=fixture.checks};
            try{
                Check(r,fixture.status.StartsWith("PASS"),"Live save-retry/level-win/Home/claim fixture passes");var host=UnityEngine.Object.FindFirstObjectByType<PlayerProfileHost>();Check(r,host&&host.Ready&&host.Events!=null&&!host.IsTransient,"Event feed attached to the isolated durable live host");
                string before=JsonUtility.ToJson(host.Service.Read());var p=host.Service.Read();var snapshot=host.Events.Capture();r.eventCount=snapshot.events.Count;
                Check(r,p.completed==11&&p.coins==1850&&p.lives==5,"Expected durable staged level-11 outcome");
                Check(r,snapshot.events.Count(e=>e.kind=="level_completed")==11,"One progression event per actual or staged first clear");
                Check(r,snapshot.events.Count(e=>e.kind=="reward_granted"&&e.category=="campaign")==11,"Each first-clear credit projected once");
                Check(r,snapshot.events.Count(e=>e.kind=="cup_point")==1,"Win retried after deadline still has only one point event");
                Check(r,snapshot.events.Count(e=>e.kind=="reward_granted"&&e.category=="rain_cup")==1,"Lost claim confirmation creates one prize event");
                Check(r,snapshot.events.Count(e=>e.kind=="tool_spent")==p.attempts.Sum(a=>a.toolCommands.Count),"Live seeded tool debits match persisted commands");
                Check(r,snapshot.events.All(e=>e.kind!="attempt_lost"&&e.kind!="attempt_interrupted"),"Completed live win is never reported as a loss");
                var balances=(long[])snapshot.opening.Clone();foreach(var e in snapshot.events)for(int i=0;i<12;i++)balances[i]+=e.delta[i];Check(r,balances.SequenceEqual(snapshot.current),"All saved balances reconcile after actual gameplay presentation");
                string folder=Path.Combine(Application.persistentDataPath,"ProfileEventVerification",id);var archive=new LocalProfileEventArchive(folder);Check(r,archive.Flush(host.Events,1000).written==snapshot.events.Count,"Explicit local delivery archives every live event");Check(r,new LocalProfileEventArchive(folder).Flush(host.Events,1000).written==0,"Recreated delivery sink deduplicates live events");
                Check(r,JsonUtility.ToJson(host.Service.Read())==before,"Audit capture and delivery never mutate the player profile");
            }catch(Exception e){r.failures.Add(e.ToString());}Finish(r);
        }
        static void Finish(Report r){SessionState.EraseBool(Key);EditorApplication.update-=Tick;r.utc=DateTime.UtcNow.ToString("o");r.unity=Application.unityVersion;r.status=r.failures.Count==0?"PASS_NATIVE_PROFILE_EVENTS":"FAIL_NATIVE_PROFILE_EVENTS";string output=Path.GetFullPath("../Verification/Evidence/ProfileEvents/Native_Play_Checks.json");Directory.CreateDirectory(Path.GetDirectoryName(output));File.WriteAllText(output,JsonUtility.ToJson(r,true));EditorApplication.Exit(r.failures.Count==0?0:1);}
    }
}
#endif
