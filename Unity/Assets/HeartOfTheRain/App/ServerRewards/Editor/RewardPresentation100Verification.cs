#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.OnlineIdentity;

namespace HeartOfTheRain.App.ServerRewards.Editor {
    public static class RewardPresentation100Verification {
        [Serializable] sealed class Report {
            public string status,utc,unity;
            public string scope="Native Unity serialization/filesystem tests of public receipt presentation only. No wallet authority, Android rendering, live payment or backend transaction is certified by this suite.";
            public int checks;public List<string> passed=new List<string>(),failures=new List<string>();
        }
        static Report report;static string directory;
        [Serializable] sealed class FixtureDocument {public int version=1;public long revision=0;public string origin="https://backend.invalid",player="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";public List<RewardPresentation> receipts=new List<RewardPresentation>();}
        [Serializable] sealed class FixtureEnvelope {public string payload,sha256;}
        static void Check(bool test,string label){report.checks++;if(!test)throw new InvalidOperationException(label);report.passed.Add(label);}
        static void Reject(Action action,string label){bool rejected=false;try{action();}catch(Exception){rejected=true;}Check(rejected,label);}
        static RewardGrant Grant()=>new RewardGrant{coins=2000,starting=new[]{1,1,1,1},tools=new[]{1,1,1,1}};
        static RewardPresentationJournal Journal(string name="receipts",string origin="https://backend.invalid",string player="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")=>new RewardPresentationJournal(Path.Combine(directory,name+".json"),origin,player);
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};directory=Path.GetFullPath("../.verification-cache/RewardPresentation100/"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(directory);
            try{Checks();report.status="PASS";}catch(Exception error){report.status="FAIL";report.failures.Add(error.GetType().Name+": "+error.Message);}
            string output=Environment.GetEnvironmentVariable("HOTR_REWARD_PRESENTATION100_OUTPUT")??Path.GetFullPath("../Verification/Evidence/Review100/Native/RewardPresentation100.json");Directory.CreateDirectory(Path.GetDirectoryName(output));File.WriteAllText(output,JsonUtility.ToJson(report,true));EditorApplication.Exit(report.status=="PASS"?0:1);
        }
        static void Checks(){
            var journal=Journal();Check(journal.Peek()==null,"Fresh owner has no synthetic receipt");
            var frozen=Grant();journal.Enqueue("commerce","credit-1",frozen);frozen.coins=1;
            var receipt=Journal().Peek();Check(receipt.id=="credit-1"&&receipt.grant.coins==2000&&receipt.grant.starting.SequenceEqual(new[]{1,1,1,1})&&receipt.grant.tools.SequenceEqual(new[]{1,1,1,1}),"Restart reads all ten frozen grant dimensions");
            receipt.grant.tools[0]=99;Check(journal.Peek().grant.tools[0]==1,"Presentation reads are detached from durable contents");
            journal.Enqueue("commerce","credit-1",Grant());journal.MarkPresented("commerce","credit-1");Check(Journal().Peek()==null,"Duplicate receipt produces one presentation");
            journal.Enqueue("commerce","credit-1",Grant());Check(journal.Peek()==null,"Already presented receipt stays acknowledged on replay");
            var changed=Grant();changed.tools[3]++;Reject(()=>journal.Enqueue("commerce","credit-1",changed),"Conflicting full grant for one receipt rejected");
            Reject(()=>journal.MarkPresented("commerce","missing"),"Unknown receipt cannot be acknowledged");
            var negative=Grant();negative.starting[2]=-1;Reject(()=>journal.Enqueue("reward","negative",negative),"Negative inventory grant rejected");
            var malformed=Grant();malformed.tools=new int[3];Reject(()=>journal.Enqueue("reward","malformed",malformed),"Malformed inventory dimensions rejected");
            Reject(()=>journal.Enqueue("reward",new string('x',257),Grant()),"Unbounded receipt identity rejected");
            Reject(()=>Journal("receipts","https://different.invalid").Peek(),"Receipt file cannot be reused by a different origin");
            Reject(()=>Journal("receipts",player:"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb").Peek(),"Receipt file cannot be reused by a different player");
            Reject(()=>Journal("unsafe","https://user:password@backend.invalid"),"Credential-bearing presentation origin rejected");
            Reject(()=>Journal("unsafe",player:"../wrong"),"Malformed player binding rejected");
            journal.VerificationCheckpoint=stage=>{if(stage=="BeforeCommit")throw new IOException("InjectedBeforeCommit");};
            Reject(()=>journal.Enqueue("reward","claim-1",Grant()),"Interrupted write reports failure before commit");Check(Journal().Peek()==null,"Pre-commit interruption leaves previous journal intact");
            journal.VerificationCheckpoint=null;journal.Enqueue("reward","claim-1",Grant());Check(Journal().Peek()?.id=="claim-1","Retry persists original receipt after save recovers");
            Check(Journal().Peek()?.id=="claim-1","Reading or closing presentation does not acknowledge it");
            journal.VerificationCheckpoint=stage=>{if(stage=="BeforeCommit")throw new IOException("InjectedAckBeforeCommit");};
            Reject(()=>journal.MarkPresented("reward","claim-1"),"Failed presentation acknowledgement reports failure");Check(Journal().Peek()?.id=="claim-1","Failed acknowledgement preserves receipt for replay");
            journal.VerificationCheckpoint=null;journal.MarkPresented("reward","claim-1");
            journal.VerificationCheckpoint=stage=>{if(stage=="AfterCommit")throw new IOException("InjectedAfterCommit");};
            Reject(()=>journal.Enqueue("reward","claim-2",Grant()),"Lost local save acknowledgement is surfaced");Check(Journal().Peek()?.id=="claim-2","Post-commit crash preserves durable receipt");
            journal.VerificationCheckpoint=null;journal.Enqueue("reward","claim-2",Grant());journal.MarkPresented("reward","claim-2");Check(journal.Peek()==null,"Post-commit retry neither duplicates nor loses notification");
            journal.Enqueue("reward","first",Grant());journal.Enqueue("commerce","second",Grant());Check(journal.Peek().id=="first","Receipts drain in commit order across grant sources");journal.MarkPresented("reward","first");Check(journal.Peek().id=="second","Only the displayed receipt is removed from pending queue");
            var corrupt=Journal("corrupt");corrupt.Enqueue("reward","corrupt",Grant());string path=Path.Combine(directory,"corrupt.json");var bytes=File.ReadAllBytes(path);bytes[bytes.Length/2]^=1;File.WriteAllBytes(path,bytes);Reject(()=>corrupt.Peek(),"Corrupt metadata is not interpreted as a new financial grant");
            var history=new FixtureDocument();for(int i=0;i<513;i++)history.receipts.Add(new RewardPresentation{channel="reward",id="history-"+i,grant=Grant(),presented=true});history.receipts.Add(new RewardPresentation{channel="reward",id="older-pending",grant=Grant()});
            string payload=JsonUtility.ToJson(history);File.WriteAllText(Path.Combine(directory,"history.json"),JsonUtility.ToJson(new FixtureEnvelope{payload=payload,sha256=IdentityProtocol82.Sha(System.Text.Encoding.UTF8.GetBytes(payload))}));
            var bounded=Journal("history");bounded.Enqueue("reward","new-pending",Grant());var saved=JsonUtility.FromJson<FixtureDocument>(JsonUtility.FromJson<FixtureEnvelope>(File.ReadAllText(Path.Combine(directory,"history.json"))).payload);
            Check(saved.receipts.Count(r=>r.presented)==512&&!saved.receipts.Any(r=>r.id=="history-0"),"Viewed history is bounded without a lifetime claim cap");Check(bounded.Peek().id=="older-pending","Compaction preserves unseen receipts and their commit order");bounded.MarkPresented("reward","older-pending");Check(bounded.Peek().id=="new-pending","History retirement never discards a pending notification");
            Check(!Directory.GetFiles(directory,"*.tmp").Any(),"Interrupted saves clean their own temporary files");
        }
    }
}
#endif
