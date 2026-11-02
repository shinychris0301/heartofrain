#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using HeartOfTheRain.App.Advertising;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification {
    // Actual policy and host state in the Editor with a scripted provider. No SDK, ad or device.
    public static class Interstitial129Verification {
        [Serializable] sealed class Report {public string status="FAIL_NATIVE_INTERSTITIAL129",utc,unity,error;public int checks;public List<string> passed=new List<string>();}
        static Report report;
        static void Check(bool value,string name){if(!value)throw new InvalidOperationException(name);report.checks++;report.passed.Add(name);}
        sealed class Memory {
            public readonly Dictionary<string,int> values=new Dictionary<string,int>();
            public int Read(string key,int fallback){int value;return values.TryGetValue(key,out value)?value:fallback;}
            public void Write(string key,int value)=>values[key]=value;
        }
        sealed class Scripted:IInterstitialProvider129 {
            public int loads,shows,disposed;public bool installed=true,answerLoad=true,loadResult=true,throwOnShow;public Action<bool> pendingLoad;public Action pendingShown,pendingShow;
            public bool Installed=>installed;
            public void Load(Action<bool> done){loads++;if(answerLoad)done(loadResult);else pendingLoad=done;}
            public void Show(Action shown,Action done){shows++;if(throwOnShow)throw new InvalidOperationException();pendingShown=shown;pendingShow=done;}
            public void Dispose()=>disposed++;
        }
        static InterstitialAds129 Host(Memory memory,Scripted provider,GameObject owner){
            var host=owner.AddComponent<InterstitialAds129>();
            host.Configure(new InterstitialPolicy129(memory.Read,memory.Write),_=>provider);
            return host;
        }
        static void Drain(IEnumerator routine,int limit=8){for(int i=0;i<limit&&routine.MoveNext();i++){}}
        static void Policy(){
            var memory=new Memory();var policy=new InterstitialPolicy129(memory.Read,memory.Write);
            for(int level=1;level<=60;level++){bool expected=level==1||level==6||level==11||level==16||level==21||level==26||level==31||level==36||level==41||level==46||level==51||level==56;Check(policy.Due(level,level-1)==expected,"Progressing player: level "+level+(expected?" owes an ad":" owes none"));}
            Check(!policy.Due(6,10)&&!policy.Due(1,3),"Replaying an old milestone level owes no ad");
            Check(!policy.Due(6,4),"A level ahead of the player's progress owes no ad");
            policy.Mark(1);Check(!policy.Due(1,0),"Level 1's ad shows once, even if the level is retried");
            Check(policy.Due(6,5),"Showing Level 1's ad leaves Level 6's due");
            policy.Mark(6);Check(!policy.Due(6,5),"Level 6's ad shows once, even if the level is retried");
            Check(policy.Due(11,10),"Level 11's ad follows");
            memory=new Memory();policy=new InterstitialPolicy129(memory.Read,memory.Write);
            Check(!policy.Due(18,17)&&!policy.Due(19,18),"An existing player between milestones owes nothing");
            Check(policy.Due(21,20),"An existing player gets the ad at the next milestone level");
            memory=new Memory();policy=new InterstitialPolicy129(memory.Read,memory.Write){AnyLevel=true};
            Check(policy.Due(3,2),"Test mode covers a level that is not a milestone");policy.Mark(3);Check(!policy.Due(4,3),"Test mode ends after one ad");
        }
        static void LevelStart(GameObject owner,int level){
            string name="Level "+level+": ";
            var memory=new Memory();var provider=new Scripted();var host=Host(memory,provider,owner);
            host.Prepare(level,level-1);Check(provider.loads==1&&host.Loaded,name+"opening the pre-level preloads");
            host.Prepare(level,level-1);Check(provider.loads==1,name+"reopening does not load a second ad");
            bool ended=false;IEnumerator Wrap(){yield return host.ShowForLevel(level,level-1,3);ended=true;}
            var stack=new Stack<IEnumerator>();stack.Push(Wrap());
            void Step(){for(int i=0;i<6&&stack.Count>0;i++){if(!stack.Peek().MoveNext()){stack.Pop();continue;}if(stack.Peek().Current is IEnumerator nested){stack.Push(nested);continue;}break;}}
            Step();
            Check(provider.shows==1&&host.Showing&&!ended,name+"the level waits while the ad is open");
            Check(!memory.values.ContainsKey(InterstitialPolicy129.LastLevelKey),name+"loading alone does not mark an impression");
            provider.pendingShown();
            Check(memory.values[InterstitialPolicy129.LastLevelKey]==level,name+"the show event records the impression before the ad closes");
            provider.pendingShow();Step();
            Check(ended&&!host.Showing&&provider.disposed==1,name+"closing the ad continues into the level and releases the ad");
            UnityEngine.Object.DestroyImmediate(host);
            memory=new Memory();provider=new Scripted{loadResult=false};host=Host(memory,provider,owner);
            host.Prepare(level,level-1);Drain(host.ShowForLevel(level,level-1,3));
            Check(provider.shows==0&&!memory.values.ContainsKey(InterstitialPolicy129.LastLevelKey),name+"no ad available: the level starts and the ad stays due");
            UnityEngine.Object.DestroyImmediate(host);
        }
        static void Limits(GameObject owner){
            var memory=new Memory();var provider=new Scripted{installed=false};var host=Host(memory,provider,owner);
            host.Prepare(1,0);Drain(host.ShowForLevel(1,0,3));Check(provider.shows==0,"An unavailable SDK never shows or blocks");
            UnityEngine.Object.DestroyImmediate(host);
            memory=new Memory();provider=new Scripted();host=Host(memory,provider,owner);
            host.Prepare(4,3);Drain(host.ShowForLevel(4,3,3));Check(provider.loads==0&&provider.shows==0,"A level that owes no ad neither loads nor shows");
            UnityEngine.Object.DestroyImmediate(host);
            memory=new Memory();provider=new Scripted();host=Host(memory,provider,owner);
            host.Prepare(6,5);host.Prepare(7,5);Check(provider.disposed==1&&!host.Loaded,"An ad loaded for a level the player left is released");
            UnityEngine.Object.DestroyImmediate(host);
            memory=new Memory();provider=new Scripted{answerLoad=false};host=Host(memory,provider,owner);
            host.Prepare(1,0);var late=host.ShowForLevel(1,0,0);while(late.MoveNext()){}
            Check(provider.shows==0&&provider.disposed==1&&!host.Loading,"A slow load cannot hold the level past its limit");
            provider.pendingLoad(true);Check(!host.Loaded,"An abandoned load's late answer is ignored");
            UnityEngine.Object.DestroyImmediate(host);
            memory=new Memory();provider=new Scripted{throwOnShow=true};host=Host(memory,provider,owner);
            host.Prepare(1,0);var failing=host.ShowForLevel(1,0,3);failing.MoveNext();
            Check(!host.Showing&&!memory.values.ContainsKey(InterstitialPolicy129.LastLevelKey),"A failing show cannot strand the level start or consume its impression");
            UnityEngine.Object.DestroyImmediate(host);
            memory=new Memory();provider=new Scripted();host=Host(memory,provider,owner);
            host.Prepare(1,0);var rejected=host.ShowForLevel(1,0,3);rejected.MoveNext();provider.pendingShow();
            Check(!host.Showing&&!memory.values.ContainsKey(InterstitialPolicy129.LastLevelKey),"A native failed-to-show callback leaves the level's ad due");
            UnityEngine.Object.DestroyImmediate(host);
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
            var owner=new GameObject("Interstitial129 verification");
            try{
                Policy();LevelStart(owner,1);LevelStart(owner,6);LevelStart(owner,11);Limits(owner);
                report.status="PASS_NATIVE_INTERSTITIAL129";
            }catch(Exception failure){report.error=failure.Message;}
            finally{UnityEngine.Object.DestroyImmediate(owner);}
            string output=Environment.GetEnvironmentVariable("HOTR_REVIEW128_OUT");
            if(!string.IsNullOrEmpty(output)){Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Interstitial129.json"),JsonUtility.ToJson(report,true));}
            if(Application.isBatchMode)EditorApplication.Exit(report.status.StartsWith("PASS_",StringComparison.Ordinal)?0:1);
        }
    }
}
#endif
