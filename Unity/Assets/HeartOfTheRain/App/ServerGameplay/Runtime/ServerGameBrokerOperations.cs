using System;
using System.Collections;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;

namespace HeartOfTheRain.App.ServerGameplay {
    public sealed partial class ServerGameSession {
        string toolPermit;int permitKind,permitX,permitY;
        public bool PrefixFlushRequired=>document!=null&&document.delta.Count>=120;
        public int RemainingActionCapacity=>document==null?0:Math.Max(0,1000-document.acceptedActions-document.delta.Count);
        public bool HasContinueActionCapacity=>RemainingActionCapacity>=6;
        public bool HasToolActionCapacity(int remainingMoves)=>RemainingActionCapacity>=1L+Math.Max(0,remainingMoves);
        public bool ToolPermitPending=>toolPermit!=null;
        public bool ConsumeToolPermit(BoosterKind kind,int x,int y){
            if(toolPermit==null||(int)kind!=permitKind||x!=permitX||y!=permitY)return false;toolPermit=null;return true;
        }
        public bool RecordAction(PlayerActionRecord action,BoardCheckpoint checkpoint){
            if(!action.accepted)return true;
            try{
                if(action.kind=="booster"){
                    if(document.phase!="ToolCommitted"||!document.hasLastOperation||document.lastOperation.model.checkpointSHA256!=IdentityProtocol82.Sha(JsonUtility.ToJson(checkpoint)))throw new InvalidOperationException();
                    document.phase="";document.checkpoint="";Save();return true;
                }
                if(action.kind!="swap"&&action.kind!="tap"||document.delta.Count>=128||RemainingActionCapacity==0)throw new InvalidOperationException();
                document.delta.Add(new ServerMove{index=document.acceptedActions+document.delta.Count,kind=action.kind=="swap"?"Swap":"Tap",x=action.x,y=action.y,toX=action.toX,toY=action.toY});return true;
            }catch(Exception){error="ServerActionJournalUnavailable";return false;}
        }
        public void Verify(BoardCheckpoint checkpoint,Action<bool,string> done){
            if(!Ready||busy||document==null||checkpoint==null){Deliver(done,false,"ServerSessionUnavailable");return;}
            string json=JsonUtility.ToJson(checkpoint);
            if(!document.hasPending&&document.delta.Count==0&&document.hasLastOperation&&document.lastOperation.state=="Committed"&&document.lastOperation.model?.checkpointSHA256==IdentityProtocol82.Sha(json)){Deliver(done,true,null);return;}
            // A won board is saved before anything can fail: its moves exist only in memory until
            // here, and the next launch would otherwise forfeit the attempt as a loss. The saved
            // intent carries no wallet revision, so it needs no read first.
            if(!document.hasPending&&checkpoint.board?.status=="Won"&&document.delta.Count<=128&&document.acceptedActions+document.delta.Count<=1000){
                try{SaveBrokerIntent("Verify",json,-1,0,0,wallet?.revision??0);}catch(Exception){Deliver(done,false,"ServerIntentSaveUnconfirmed");return;}
                busy=true;StartCoroutine(RunSavedBroker(done));return;
            }
            BeginBroker("Verify",json,-1,0,0,done);
        }
        IEnumerator RunSavedBroker(Action<bool,string> done){
            bool ok=false;string why=null;yield return ExecuteBroker(false,(value,message)=>{ok=value;why=message;});busy=false;error=why;
            Changed?.Invoke();Deliver(done,ok,why);
        }
        public void SpendTool(BoosterKind kind,int x,int y,BoardCheckpoint before,Action<bool,string> done){
            if(before?.board==null){Deliver(done,false,"ServerSessionUnavailable");return;}
            if(document!=null&&!document.hasPending&&!HasToolActionCapacity(before.board.moves)){Deliver(done,false,"ReviewReplayActionLimit");return;}
            BeginBroker("Tool",JsonUtility.ToJson(before),(int)kind,x,y,done);
        }
        public void PurchaseContinue(Action<bool,string> done){if(!HasRestorableContinue||document.phase!="Awaiting"){Deliver(done,false,"ServerContinueNotReady");return;}BeginBroker("Continue",document.checkpoint,-1,0,0,done);}
        void BeginBroker(string operation,string checkpoint,int tool,int x,int y,Action<bool,string> done){
            if(busy&&Ready&&!closed&&journal!=null){StartCoroutine(AfterGate(()=>BeginBroker(operation,checkpoint,tool,x,y,done),done));return;}
            if(!Ready||closed||journal==null){Deliver(done,false,"ServerSessionUnavailable");return;}
            if(document.hasPending){
                if(document.pending.operation!=operation){Deliver(done,false,"AnotherServerCommandRequiresReconciliation");return;}
                if(checkpoint!=document.checkpoint){Deliver(done,false,"PendingServerBoardChanged");return;}
                if(operation=="Tool"){var prior=JsonUtility.FromJson<ServerToolRequest>(document.pending.payload);if(prior.tool!=tool||prior.x!=x||prior.y!=y){Deliver(done,false,"PendingServerToolChanged");return;}}
                busy=true;StartCoroutine(FinishPending(done));return;
            }
            // A new Continue must fit both its authorization and all five
            // purchased moves. Already-pending paid requests above retain
            // their exact reconciliation path regardless of this guard.
            if(document.delta.Count>128||RemainingActionCapacity<(operation=="Continue"?6:operation=="Verify"?0:1)||document.acceptedActions+document.delta.Count>1000){Deliver(done,false,"ReviewReplayActionLimit");return;}
            busy=true;StartCoroutine(BrokerBegin(operation,checkpoint,tool,x,y,done));
        }
        IEnumerator BrokerBegin(string operation,string checkpoint,int tool,int x,int y,Action<bool,string> done){
            bool fresh=false;string why=null;yield return FetchWallet((ok,message)=>{fresh=ok;why=message;});if(!fresh){busy=false;Deliver(done,false,why);yield break;}
            try{SaveBrokerIntent(operation,checkpoint,tool,x,y,wallet.revision);}catch(Exception){busy=false;Deliver(done,false,"ServerIntentSaveUnconfirmed");yield break;}
            yield return ExecuteBroker(false,(ok,message)=>{fresh=ok;why=message;});busy=false;error=why;
            Changed?.Invoke();Deliver(done,fresh,why);
        }
        void SaveBrokerIntent(string operation,string checkpoint,int tool,int x,int y,long revision){
            string id=NewId();ServerVerifyRequest request;
            if(operation=="Tool")request=new ServerToolRequest{expectedWalletRevision=revision,tool=tool,x=x,y=y};
            else if(operation=="Continue")request=new ServerContinueRequest{expectedWalletRevision=revision};else request=new ServerVerifyRequest();
            request.commandId=id;request.expectedPrefixRevision=document.prefixRevision;request.actions=document.delta.Select(v=>Copy(v)).ToArray();
            document.checkpoint=checkpoint;document.hasPending=true;document.pending=new ServerPendingCommand{operation=operation,commandId=id,attemptId=document.attemptId,payload=JsonUtility.ToJson(request),expectedRevision=revision};Save();
        }
        const float PendingWaitSeconds=45,BrokerStallSeconds=60;
        IEnumerator ResumeBroker(Action<bool,string> done){yield return ExecuteBroker(true,done);}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public static bool VerificationBrokerOffline;
#endif
        IEnumerator ExecuteBroker(bool recovering,Action<bool,string> done){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(VerificationBrokerOffline){done(false,"BrokerOffline");yield break;}
#endif
            bool identified=false;string why=null;yield return EnsureIdentity((ok,message)=>{identified=ok;why=message;});if(!identified){done(false,why);yield break;}
            var pending=Copy(document.pending);ServerGameReply<ServerBrokerOperation> reply=null;
            if(recovering)broker.Operation(pending.attemptId,pending.commandId,true,r=>reply=r);
            else DispatchBroker(pending,r=>reply=r);
            float limit=Time.unscaledTime+BrokerStallSeconds;while(reply==null&&!closed&&Time.unscaledTime<limit)yield return null;
            if(reply==null&&!closed)broker.Cancel();
            // The intent may have survived a process death before its first
            // HTTP dispatch. An authenticated not-found is the only case that
            // resubmits its exact saved command; other errors remain unknown.
            if(!closed&&recovering&&reply?.error=="BrokerHttp404"){
                reply=null;DispatchBroker(pending,r=>reply=r);limit=Time.unscaledTime+BrokerStallSeconds;while(reply==null&&!closed&&Time.unscaledTime<limit)yield return null;
                if(reply==null&&!closed)broker.Cancel();
            }
            // Verification runs one at a time. Another player's run answers Pending
            // and the saved command stays valid, so resume it before asking the player.
            for(float wait=.5f,waited=0;!closed&&reply!=null&&reply.Succeeded&&reply.value.state=="Pending"&&waited<PendingWaitSeconds;waited+=wait,wait=Mathf.Min(wait*2,4)){
                yield return new WaitForSecondsRealtime(wait);if(closed)break;
                reply=null;broker.Operation(pending.attemptId,pending.commandId,true,r=>reply=r);limit=Time.unscaledTime+BrokerStallSeconds;while(reply==null&&!closed&&Time.unscaledTime<limit)yield return null;
                if(reply==null&&!closed)broker.Cancel();
            }
            // Cached successes return before rule checks, so these are final refusals, not unknowns.
            if(!closed&&(reply?.error=="BrokerHttp400"||reply?.error=="BrokerHttp409"||reply?.error=="BrokerHttp422")){
                try{document.hasPending=false;Save();}catch(Exception){done(false,"ServerRefusalSaveUnconfirmed");yield break;}
                done(false,reply.error);yield break;
            }
            if(reply?.error=="BrokerHttp401")identity.ExpireAccess();
            if(closed||reply==null||!reply.Succeeded){done(false,reply?.error??"ServerVerificationUnknown");yield break;}
            var operation=reply.value;
            if(operation.state=="Pending"){done(false,"ServerVerificationPending");yield break;}
            if(operation.state=="Rejected"){
                try{document.hasPending=false;Save();}catch(Exception){done(false,"ServerRefusalSaveUnconfirmed");yield break;}
                done(false,operation.code??"ServerVerificationRejected");yield break;
            }
            try{
                bool fault=operation.displayReceipt?.outcome=="Fault";
                if(!fault&&pending.operation=="Verify"&&operation.model.checkpointSHA256!=IdentityProtocol82.Sha(document.checkpoint))throw new InvalidOperationException("ServerModelMismatch");
                document.prefixRevision=operation.prefixRevision;document.acceptedActions=operation.acceptedActions;document.delta.Clear();document.hasLastOperation=true;document.lastOperation=Copy(operation);document.hasPending=false;
                BindAttempt(operation.attempt);
                document.phase=fault?"":pending.operation=="Tool"?"ToolCommitted":pending.operation=="Continue"?"Purchased":operation.model.outcome=="Out of moves"?"Awaiting":"";
                if(fault)document.checkpoint="";
                else if(pending.operation=="Tool"){var target=JsonUtility.FromJson<ServerToolRequest>(pending.payload);document.paidTool=target.tool;document.paidX=target.x;document.paidY=target.y;}
                Save();Publish(operation.wallet);done(true,null);
            }catch(Exception problem){try{document=journal.Read();}catch(Exception){}done(false,problem is InvalidOperationException&&problem.Message=="ServerModelMismatch"?"ServerModelMismatch":"ServerVerifiedReceiptSaveUnconfirmed");}
        }
        void DispatchBroker(ServerPendingCommand pending,Action<ServerGameReply<ServerBrokerOperation>> done){
            if(pending.operation=="Tool")broker.Tool(pending.attemptId,JsonUtility.FromJson<ServerToolRequest>(pending.payload),done);
            else if(pending.operation=="Continue")broker.Continue(pending.attemptId,JsonUtility.FromJson<ServerContinueRequest>(pending.payload),done);
            else broker.Verify(pending.attemptId,JsonUtility.FromJson<ServerVerifyRequest>(pending.payload),done);
        }
        public void ArmCommittedTool(BoosterKind kind,int x,int y){
            if(document==null||document.phase!="ToolCommitted"||!document.hasLastOperation||document.paidTool!=(int)kind||document.paidX!=x||document.paidY!=y)throw new InvalidOperationException("NoCommittedToolReceipt");
            permitKind=(int)kind;permitX=x;permitY=y;toolPermit=document.lastOperation.operationId;
        }
        public ContinueReceipt PrepareLocalContinue(LevelData level){
            if(document==null||document.phase!="Purchased"||!document.hasLastOperation||document.lastOperation.addedMoves!=5)throw new InvalidOperationException("NoServerContinueReceipt");
            var before=JsonUtility.FromJson<BoardCheckpoint>(document.checkpoint);var board=BoardModel.FromCheckpoint(level,before);string operation=document.lastOperation.paidReceiptId;
            if(string.IsNullOrEmpty(operation))throw new InvalidOperationException("ServerPaidContinueIdentityMissing");
            // Repeated local acknowledgement is deterministic; a saved
            // Purchased checkpoint may already include this exact operation.
            string prior=JsonUtility.ToJson(before);
            board.ApplyContinue(operation,5);string after=JsonUtility.ToJson(board.Checkpoint());
            if(IdentityProtocol82.Sha(after)!=document.lastOperation.model.checkpointSHA256)throw new InvalidOperationException("ServerContinueModelMismatch");
            return new ContinueReceipt{operation=operation,attempt=document.attemptId,quote=operation,outcome="Applied",cost=900,movesAfter=5,coinsAfter=wallet.coins,beforeHash=ProfileJson.Hash(prior),afterCheckpoint=after};
        }
        public void AcknowledgeLocalContinue(string checkpoint){document.checkpoint=checkpoint;Save();}
    }
}
