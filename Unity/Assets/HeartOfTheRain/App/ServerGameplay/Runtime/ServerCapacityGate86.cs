using System;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.App.ServerGameplay {
    // The service's bounded replay history is checked before a model command.
    // Reuse the approved explicit-forfeit dialog; merely opening/backing out
    // never settles an attempt or charges a life.
    public sealed class ServerCapacityGate86 {
        public bool Showing {get;private set;}
        public static bool IsCapacityError(string code)=>code=="ReviewReplayActionLimit"||code=="gameplay_history_capacity";
        public bool BeforeCommand(ServerGameSession session,GameplayScreen source,Func<bool> current,Action confirm){
            // A previously committed Tool already owns its history entry.
            // Its immediate deterministic local application creates no entry.
            if(session.ToolPermitPending||session.RemainingActionCapacity>0)return true;
            Show(source,current,confirm);return false;
        }
        public void Show(GameplayScreen source,Func<bool> current,Action confirm){
            if(Showing||!source||!current())return;
            Showing=true;source.ReviewInputBlocked=true;source.SetPause(true);
            source.GetComponent<GameplayHUD>().ShowExitConfirmation(()=>{
                Showing=false;if(source&&current()){source.SetPause(false);source.ReviewInputBlocked=false;}
            },()=>{
                if(!Showing)return;Showing=false;
                if(source&&current())confirm?.Invoke();
            });
        }
    }
}
