using System;
using System.Collections;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.App.ServerGameplay {
    public sealed partial class ServerGameSession {
        [Serializable] class WalletRequest{public string commandId;public long expectedRevision;}
        [Serializable] sealed class ReserveRequest:WalletRequest{public int level;public int[] starting;}
        public void Reserve(int level,int[] selected,Action<bool,string> done,bool settled=false){
            if(selected==null||selected.Length!=4||selected.Any(v=>v<0||v>1)||level<1||level>50){Deliver(done,false,"InvalidServerReservation");return;}
            if(busy&&Ready&&!closed&&journal!=null){StartCoroutine(AfterGate(()=>Reserve(level,selected,done),done));return;}
            // A forfeit that failed at launch has nothing else to retry it. Finish it before starting
            // the next level, or every Play fails against the attempt the server still holds.
            if(document?.hasPending==true&&document.pending.operation!="Reserve"){Reconcile((ok,why)=>{if(ok)Reserve(level,selected,done);else Deliver(done,false,why);});return;}
            if(!settled&&document?.hasPending!=true&&Ready&&wallet?.activeAttempt!=null&&!HasRestorableContinue){
                try{if(document.attemptId!=wallet.activeAttempt.attemptId)BindActiveAttempt();}catch(Exception){Deliver(done,false,"ServerIntentSaveUnconfirmed");return;}
                Quit((ok,why)=>{if(ok)Reserve(level,selected,done,true);else Deliver(done,false,why);});return;
            }
            if(document?.hasPending==true&&document.pending.operation=="Reserve"){
                var prior=JsonUtility.FromJson<ReserveRequest>(document.pending.payload);
                if(prior.level!=level||prior.starting==null||!prior.starting.SequenceEqual(selected)){Deliver(done,false,"PendingServerReservationChanged");return;}
            }
            BeginFinancial("Reserve",()=>new ReserveRequest{commandId=NewId(),expectedRevision=wallet.revision,level=level,starting=(int[])selected.Clone()},done);
        }
        public void StartAttempt(Action<bool,string> done)=>BeginFinancial("Start",()=>new WalletRequest{commandId=NewId(),expectedRevision=wallet.revision},done);
        public void Quit(Action<bool,string> done){
            if(!Ready||busy||closed||document==null){Deliver(done,false,"ServerSessionUnavailable");return;}
            if(document.hasPending&&document.pending.operation!="Quit"){
                if(document.pending.operation=="Reserve"){Reconcile((ok,why)=>{if(ok)Quit(done);else Deliver(done,false,why);});return;}
                busy=true;StartCoroutine(PrepareAbandon(done));return;
            }
            if(document.hasAttempt&&new[]{"Won","Lost","Released","Cancelled"}.Contains(document.attempt.state)){Deliver(done,true,null);return;}
            BeginFinancial("Quit",()=>new WalletRequest{commandId=NewId(),expectedRevision=wallet.revision},done);
        }
        IEnumerator PrepareAbandon(Action<bool,string> done){
            bool fresh=false;string why=null;yield return FetchWallet((ok,message)=>{fresh=ok;why=message;});
            if(!fresh){busy=false;Deliver(done,false,why);yield break;}
            if(wallet.activeAttempt==null){yield return FinishPending(done);yield break;}
            try{
                // Preserve the unresolved intent for diagnosis. The server's
                // explicit abandon transaction fences it before charging once.
                document.hasAbandonedPending=true;document.abandonedPending=Copy(document.pending);document.hasPending=false;Save();
            }catch(Exception){busy=false;Deliver(done,false,"ServerForfeitIntentSaveUnconfirmed");yield break;}
            busy=false;Quit(done);
        }
        public void CancelReservation(Action<bool,string> done)=>Quit(done);
        public void RefillLives(Action<bool,string> done)=>BeginFinancial("Refill",()=>new WalletRequest{commandId=NewId(),expectedRevision=wallet.revision},done);
        void BeginFinancial(string operation,Func<WalletRequest> create,Action<bool,string> done){
            if(busy&&Ready&&!closed&&journal!=null){StartCoroutine(AfterGate(()=>BeginFinancial(operation,create,done),done));return;}
            if(!Ready||closed||journal==null){Deliver(done,false,"ServerSessionUnavailable");return;}
            if(document.hasPending){if(document.pending.operation!=operation){Deliver(done,false,"AnotherServerCommandRequiresReconciliation");return;}busy=true;StartCoroutine(FinishPending(done));return;}
            busy=true;StartCoroutine(FinancialBegin(operation,create,done));
        }
        IEnumerator FinancialBegin(string operation,Func<WalletRequest> create,Action<bool,string> done){
            bool fresh=false;string why=null;yield return FetchWallet((ok,message)=>{fresh=ok;why=message;});
            if(!fresh){busy=false;Deliver(done,false,why);yield break;}
            if(operation=="Quit"&&wallet.activeAttempt==null&&document.hasAttempt){
                PayReply<RuStoreServerAttempt> ended=null;walletClient.GetAttempt(document.attemptId,r=>ended=r);float ask=Time.unscaledTime+StallSeconds;while(ended==null&&!closed&&Time.unscaledTime<ask)yield return null;
                if(ended!=null&&ended.Succeeded&&new[]{"Won","Lost","Released","Cancelled"}.Contains(ended.value.state)){
                    try{BindAttempt(ended.value);document.phase="";document.checkpoint="";Save();Publish(wallet);busy=false;Deliver(done,true,null);}catch(Exception){busy=false;Deliver(done,false,"ServerConfirmationSaveUnconfirmed");}yield break;
                }
            }
            try{
                var request=create();document.hasPending=true;document.pending=new ServerPendingCommand{operation=operation,commandId=request.commandId,attemptId=document.attemptId,payload=JsonUtility.ToJson(request),expectedRevision=request.expectedRevision};Save();
            }catch(Exception){busy=false;error="ServerIntentSaveUnconfirmed";Deliver(done,false,error);yield break;}
            yield return FinishPending(done,true);
        }
        IEnumerator FinishPending(Action<bool,string> done,bool walletFresh=false){
            bool ok=false;string why=null;yield return ResumePending((value,message)=>{ok=value;why=message;},walletFresh);busy=false;error=why;Changed?.Invoke();Deliver(done,ok,why);
        }
        public void Reconcile(Action<bool,string> done){if(busy&&Ready&&!closed&&document!=null){StartCoroutine(AfterGate(()=>Reconcile(done),done));return;}if(!Ready||closed||document==null){Deliver(done,false,"ServerSessionUnavailable");return;}busy=true;StartCoroutine(FinishPending(done));}
        IEnumerator ResumePending(Action<bool,string> done,bool walletFresh=false){
            if(journalDirty){try{Save();}catch(Exception){done(false,"ServerIntentSaveUnconfirmed");yield break;}}
            if(document==null||!document.hasPending){done(true,null);yield break;}
            string operation=document.pending.operation;
            if(operation=="Verify"||operation=="Tool"||operation=="Continue"){yield return ResumeBroker(done);yield break;}
            // A command saved just now already read the wallet it was built from.
            bool fresh=walletFresh;string why=null;if(!fresh)yield return FetchWallet((ok,message)=>{fresh=ok;why=message;});if(!fresh){done(false,why);yield break;}
            var pending=Copy(document.pending);var request=JsonUtility.FromJson<WalletRequest>(pending.payload);PayReply<RuStoreWalletMutation> reply=null;
            try{
                switch(operation){
                    case "Reserve":var reserve=JsonUtility.FromJson<ReserveRequest>(pending.payload);walletClient.Reserve(reserve.commandId,reserve.expectedRevision,reserve.level,reserve.starting,r=>reply=r);break;
                    case "Start":walletClient.Start(request.commandId,request.expectedRevision,pending.attemptId,r=>reply=r);break;
                    case "Quit":walletClient.Quit(request.commandId,request.expectedRevision,pending.attemptId,r=>reply=r);break;
                    case "Refill":walletClient.Refill(request.commandId,request.expectedRevision,r=>reply=r);break;
                    default:throw new InvalidOperationException();
                }
            }catch(Exception){done(false,"ServerDispatchUnavailable");yield break;}
            float limit=Time.unscaledTime+StallSeconds;while(reply==null&&!closed&&Time.unscaledTime<limit)yield return null;
            if(closed){done(false,"ServerSessionClosed");yield break;}
            if(reply==null||!reply.Succeeded){
                string code=reply?.error?.code??"ServerCommandUnknown";
                // Cached successes are returned before revision/rule checks.
                // A concrete409 is an authoritative refusal, not a timeout.
                if(code=="StagingHttp409"||code=="StagingHttp422"||code=="StagingHttp400"){
                    try{document.hasPending=false;Save();}catch(Exception){done(false,"ServerRefusalSaveUnconfirmed");yield break;}
                }
                done(false,code);yield break;
            }
            try{
                var mutation=reply.value;
                if(mutation.attempt!=null){
                    if(operation=="Reserve"){
                        document.prefixRevision=0;document.acceptedActions=0;document.delta.Clear();document.phase="";document.checkpoint="";document.hasLastOperation=false;
                    }
                    BindAttempt(mutation.attempt);
                }
                if(operation=="Quit"){document.phase="";document.checkpoint="";document.delta.Clear();}
                document.hasPending=false;Save();Publish(mutation.wallet);done(true,null);
            }catch(Exception){
                // The exact immutable command remains recoverable even if its
                // local acknowledgement write failed after remote commit.
                try{document=journal.Read();}catch(Exception){}
                done(false,"ServerConfirmationSaveUnconfirmed");
            }
        }
        public bool ConsumeContinueCheckpoint(){
            if(document==null||document.phase!="Purchased")return true;
            try{document.phase="";document.checkpoint="";Save();return true;}catch(Exception){error="ServerCheckpointSaveUnconfirmed";return false;}
        }
        public void SetContinueView(string view){if(view!="offer"&&view!="shop")throw new ArgumentException();document.view=view;Save();}
    }
}
