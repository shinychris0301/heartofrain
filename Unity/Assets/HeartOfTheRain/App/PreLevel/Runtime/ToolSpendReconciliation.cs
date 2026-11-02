using System;
using System.Linq;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.App.PreLevel
{
    // Durable tool debit with exactly-once reconciliation. When a debit's save
    // and its confirming read both fail, the exact command stays pending for
    // that attempt, tool and target; every other tool input is refused until
    // the same target is retried and the saved command is found or repeated.
    // The pending command belongs to one attempt and never survives into the
    // next: BeginAttempt clears it.
    public sealed class ToolSpendReconciliation
    {
        string attemptId,command;BoosterKind kind;int x,y;
        public string AttemptId=>attemptId;
        public bool HasPending=>command!=null;
        public void BeginAttempt(string id){attemptId=id;command=null;}
        public bool Matches(BoosterKind k,int px,int py)=>command!=null&&kind==k&&x==px&&y==py;
        // True: the debit is durable (saved now, or found saved by the confirming
        // read). False with unconfirmed: both the save and the read failed, so
        // the caller must have the player retry this exact target. False without
        // unconfirmed: refused (no attempt, another command pending, or the
        // service rejected the debit and the read confirmed nothing was saved).
        public bool TryCommit(ProfileService service,BoosterKind k,int px,int py,out bool unconfirmed)
        {
            unconfirmed=false;
            if(service==null||string.IsNullOrEmpty(attemptId))return false;
            if(command!=null&&!Matches(k,px,py))return false;
            string id=command??Guid.NewGuid().ToString("N");
            try{service.SpendTool(attemptId,id,(int)k);command=null;return true;}
            catch(Exception){
                try{bool saved=service.Read().attempts.Any(a=>a.id==attemptId&&a.toolCommands.Contains((int)k+":"+id));command=null;return saved;}
                catch(Exception){command=id;kind=k;x=px;y=py;unconfirmed=true;return false;}
            }
        }
    }
}
