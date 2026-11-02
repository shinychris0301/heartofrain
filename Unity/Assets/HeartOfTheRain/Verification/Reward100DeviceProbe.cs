#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerRewards;

namespace HeartOfTheRain.Verification {
    // Opt-in synthetic projection followed by the ordinary shared Home renderer.
    // Never selects or writes an owner repository or claims a real purchase.
    public sealed class Reward100DeviceProbe:MonoBehaviour {
        const string Marker="HOTR_RunReward100";
        [Serializable] public sealed class Report {
            public string status="STARTING",utc,unity,platform,error,profileHashBeforeReveal,profileHashAfterReveal;
            public string scope="Development-only disposable memory profile. Public ProfileService.Grant applies one approved Wellkeeper grant before shared Home presentation. A separate synthetic public-receipt journal under the transient player is reconstructed, deduplicated and acknowledged only on completion. No real purchase/provider, durable owner credit, HTTP, crash durability or performance acceptance.";
            public int checks,coins,stars,quantityLabels,completions;public int[] starting,tools;
            public double revealElapsed;public bool modelCreditedBeforeReveal,homeInteractive,isolatedMemory,journalReconstructed,journalDedupe,journalAcknowledged;
        }
        static bool pending;
        Report report;HomePage home;PlayerProfileHost host;RewardGrant grant;int phase;float deadline,at;bool completed;string frozen,journalPath,transientPlayer;
        RewardPresentationJournal Journal()=>new RewardPresentationJournal(journalPath,"https://verification.invalid",transientPlayer);
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)] static void Boot(){
            string path=Path.Combine(Application.persistentDataPath,Marker);
            try{if(!File.Exists(path)||new FileInfo(path).Length>64||File.ReadAllText(path).Trim()!="wellkeeper")return;File.Delete(path);pending=true;SceneManager.sceneLoaded+=Attach;}catch(IOException){}catch(UnauthorizedAccessException){}
        }
        static void Attach(Scene scene,LoadSceneMode mode){
            var first=FindFirstObjectByType<FirstStartPage>();if(!pending||!first)return;pending=false;SceneManager.sceneLoaded-=Attach;first.reviewAlways=true;
            var profile=first.home.GetComponent<PlayerProfileHost>();if(!profile)profile=first.home.gameObject.AddComponent<PlayerProfileHost>();profile.VerificationCupClock=()=>1000;profile.VerificationLivesClock=()=>1000;
            var node=new GameObject("Opt-in shared reward100 memory fixture");DontDestroyOnLoad(node);var probe=node.AddComponent<Reward100DeviceProbe>();probe.report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,platform=Application.platform.ToString()};
        }
        void Start(){deadline=Time.realtimeSinceStartup+150;}
        void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        string Digest()=>ProfileJson.Hash(JsonUtility.ToJson(host.Service.Read()));
        void Save(){
            if(host&&host.Ready){var p=host.Service.Read();report.coins=p.coins;report.stars=p.stars;report.starting=(int[])p.starting.Clone();report.tools=(int[])p.tools.Clone();}
            if(home)report.homeInteractive=home.PresentationInteractable;
            string directory=Path.Combine(Application.persistentDataPath,"Reward100Device");Directory.CreateDirectory(directory);File.WriteAllText(Path.Combine(directory,"Report.json"),JsonUtility.ToJson(report,true));
        }
        void Update(){
            if(report==null||report.status.StartsWith("PASS",StringComparison.Ordinal)||report.status.StartsWith("FAIL",StringComparison.Ordinal))return;
            try{
                if(Time.realtimeSinceStartup>deadline)throw new TimeoutException("MemoryRewardFixtureDeadline");
                if(phase==0){
                    var first=FindFirstObjectByType<FirstStartPage>();if(!first||!first.Initialized)return;home=first.home;host=home.GetComponent<PlayerProfileHost>();if(!host||!host.Ready)return;
                    Check(first.reviewAlways&&host.IsTransient&&!host.ServerSession,"Only disposable memory is selected before grant");report.isolatedMemory=true;first.Request("skip");first.Request("skip");
                    if(!home.PresentationInteractable)return;
                    var before=host.Service.Read();Check(before.coins==1250&&before.stars==0,"Known uncredited fixture baseline");grant=new RewardGrant{coins=2000,starting=new[]{1,1,1,1},tools=new[]{1,1,1,1}};
                    Check(host.Service.Grant("verification100/wellkeeper","controlled-memory-presentation",grant),"Model service commits one synthetic approved bundle before animation");
                    var after=host.Service.Read();Check(after.coins==3250&&after.stars==0&&after.starting.SequenceEqual(new[]{6,6,4,3})&&after.tools.SequenceEqual(new[]{4,4,4,4}),"Full nine nonzero dimensions are already credited");
                    int rewards=after.rewards.Count;Check(!host.Service.Grant("verification100/wellkeeper","controlled-memory-presentation",grant),"Duplicate service receipt returns no new grant");
                    var duplicate=host.Service.Read();Check(duplicate.coins==after.coins&&duplicate.stars==after.stars&&duplicate.starting.SequenceEqual(after.starting)&&duplicate.tools.SequenceEqual(after.tools)&&duplicate.rewards.Count==rewards,"Duplicate receipt leaves all financial dimensions and receipt count unchanged");
                    Check(host.Refresh(),"Home receives committed projection before reveal");frozen=Digest();var modal=home.GetComponent<PreLevelModal>();Check(modal&&modal.assets,"Approved shared sprite bank exists");
                    transientPlayer=after.playerId;journalPath=Path.Combine(Application.persistentDataPath,"Reward100Device",transientPlayer,"receipts.json");
                    Journal().Enqueue("reward","verification100/wellkeeper",grant);var reconstructed=Journal().Peek();Check(reconstructed!=null&&reconstructed.channel=="reward"&&reconstructed.id=="verification100/wellkeeper"&&reconstructed.grant.coins==2000&&reconstructed.grant.starting.SequenceEqual(grant.starting)&&reconstructed.grant.tools.SequenceEqual(grant.tools),"Android filesystem reconstructs exact synthetic public full receipt");report.journalReconstructed=true;
                    Journal().Enqueue("reward","verification100/wellkeeper",grant);Check(Journal().Peek()?.id==reconstructed.id&&Digest()==frozen,"Duplicate pending receipt cannot change model or pending identity");report.journalDedupe=true;
                    report.profileHashBeforeReveal=frozen;report.modelCreditedBeforeReveal=true;at=Time.realtimeSinceStartup;
                    home.PlayCommittedReward(reconstructed.grant,modal.assets,()=>{report.completions++;Journal().MarkPresented("reward","verification100/wellkeeper");completed=true;});phase=1;return;
                }
                Check(Digest()==frozen,"Presentation cannot mutate wallet inventory or revision");Check(home.PresentationInteractable,"Shared reward feedback leaves Home interactive");
                var labels=home.GetComponentsInChildren<Text>().Where(t=>t.isActiveAndEnabled&&t.name.StartsWith("Receipt quantity ",StringComparison.Ordinal)).ToArray();
                if(phase==1){if(labels.Length==0)return;Check(Journal().Peek()?.id=="verification100/wellkeeper","Visible synthetic receipt remains pending before completion");Check(labels.Length==9,"Actual shared receipt renders every nonzero bundle dimension");foreach(var text in labels){Check(text.text=="+2000"||text.text=="+1","Actual quantity labels use frozen grant values");Check(text.preferredHeight<=text.rectTransform.rect.height+1.5f,"Actual quantity label fits");}
                    report.quantityLabels=labels.Length;report.status="OBSERVING_COMMITTED_REWARD100";Save();phase=2;return;}
                if(phase==2){if(!completed)return;Check(report.completions==1,"Presentation completion is called once");Check(Journal().Peek()==null,"Reconstructed Android receipt is acknowledged only after completion");Journal().Enqueue("reward","verification100/wellkeeper",grant);Check(Journal().Peek()==null,"Duplicate acknowledged synthetic receipt cannot create another notification");report.journalAcknowledged=true;Check(labels.Length==0,"Receipt nodes close after automatic presentation");report.revealElapsed=Time.realtimeSinceStartup-at;report.profileHashAfterReveal=Digest();Check(report.profileHashAfterReveal==report.profileHashBeforeReveal,"Completed animation leaves full committed state unchanged");report.status="PASS_NATIVE_REWARD100_MEMORY_PRESENTATION";Save();phase=3;}
            }catch(Exception error){report.status="FAIL_NATIVE_REWARD100_MEMORY_PRESENTATION";report.error=error.GetType().Name+": "+error.Message;Save();}
        }
    }
}
#endif
