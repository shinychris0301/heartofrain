#if UNITY_EDITOR
using System;using System.IO;using UnityEngine;
using HeartOfTheRain.App.Home;using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.Verification {
    public static class HomeLivesR1Transactions {
        public static void Run(Action<bool,string> check){
            string root=Path.GetFullPath("../.verification-cache/HomeLivesR1/Transactions/"+Guid.NewGuid().ToString("N"));
            foreach(string operation in new[]{"loss","regeneration","refill"})foreach(string phase in new[]{"TempFlushed","Committed"}){
                string folder=Path.Combine(root,operation+phase),id=Guid.NewGuid().ToString("N");var repo=new FileProfileRepository(folder,()=>PlayerProfile.New(new[]{5,5,3,2}));var service=new ProfileService(repo);var view=new HomeLivesPresentation();service.Read();
                if(operation=="loss"){service.Reserve(id,1,"confirmed-loss",new int[4],50,1);service.CommitStart(id);}
                else if(operation=="regeneration"){service.Change(p=>{p.lives=4;p.livesRefillDueUnix=2800;return true;});}
                else service.Change(p=>{p.lives=0;p.livesRefillDueUnix=2800;return true;});
                view.Accept(service.Read(),1000,0);repo.Checkpoint=s=>{if(s==phase)throw new IOException("Injected "+operation+phase);};bool threw=false;
                try{if(operation=="loss")service.Lose(id);else if(operation=="regeneration")service.RegenerateLives(2800);else service.RefillLives(id,1000);}catch(IOException){threw=true;}
                check(threw,"File fault injected "+operation+phase);
                service=new ProfileService(new FileProfileRepository(folder,()=>throw new Exception("Must not reset")));var after=service.Read();
                check(after.lives==(phase=="Committed"?(operation=="loss"?4:5):(operation=="loss"?5:operation=="regeneration"?4:0)),"Atomic saved balance "+operation+phase);
                if(operation=="refill")check(after.coins==1250-(phase=="Committed"?900:0)&&after.lifeRefills.Count==(phase=="Committed"?1:0),"Atomic 900-coin debit/receipt "+phase);
                if(operation=="loss")service.Lose(id);else if(operation=="regeneration")service.RegenerateLives(2800);else service.RefillLives(id,1000);
                view.Accept(service.Read(),1000,0);check(view.Take()==(operation=="loss"?-1:operation=="regeneration"?1:0),"Reconciled semantic effect "+operation+phase);
                if(operation=="loss")service.Lose(id);else if(operation=="regeneration")service.RegenerateLives(2800);else service.RefillLives(id,1000);
                view.Accept(service.Read(),1000,0);check(view.Take()==0,"Duplicate confirmation has no replay "+operation+phase);
                check(service.Read().lives==(operation=="loss"?4:5),"Duplicate command does not alter balance "+operation+phase);
                if(operation=="refill")check(service.Read().coins==350&&service.Read().lifeRefills.Count==1&&service.Read().lifeRefills[0].coins==900,"Recovery/retry spends exactly 900 once "+phase);
                var reopened=new HomeLivesPresentation();reopened.Accept(service.Read(),1000,0);check(reopened.Take()==0,"Fresh presentation does not infer old loss/refill "+operation+phase);
            }
            var model=new ProfileService(new MemoryProfileRepository(PlayerProfile.New(new[]{5,5,3,2})));string attempt=Guid.NewGuid().ToString("N");model.Reserve(attempt,1,"ongoing-timer",new int[4],50,1);model.CommitStart(attempt);model.Lose(attempt);model.RegenerateLives(1000);long deadline=model.Read().livesRefillDueUnix;attempt=Guid.NewGuid().ToString("N");model.Reserve(attempt,1,"second-loss",new int[4],50,1);model.CommitStart(attempt);model.Lose(attempt);model.RegenerateLives(1100);check(model.Read().livesRefillDueUnix==deadline,"Second loss retains existing refill deadline");model.RegenerateLives(deadline+1800);check(model.Read().lives==5&&model.Read().lifeCredits[0].lives==2,"Catch-up and cap remain service responsibilities");
            attempt=Guid.NewGuid().ToString("N");model.Reserve(attempt,1,"interrupted",new int[4],50,1);model.CommitStart(attempt);var feedback=new HomeLivesPresentation();feedback.Accept(model.Read(),1000,0);model.RecoverInterrupted();feedback.Accept(model.Read(),1000,0);check(feedback.Take()==-1&&model.Read().lives==4,"New interrupted attempt settles one semantic loss");model.RecoverInterrupted();feedback.Accept(model.Read(),1000,0);check(feedback.Take()==0&&model.Read().lives==4,"Repeated recovery neither debits nor animates twice");
            // Review 65: a cue queued before a new attempt begins never replays after that attempt's own outcome.
            var flush=new ProfileService(new MemoryProfileRepository(PlayerProfile.New(new[]{5,5,3,2})));var cues=new HomeLivesPresentation();cues.Accept(flush.Read(),1000,0);
            string lost=Guid.NewGuid().ToString("N");flush.Reserve(lost,1,"stale-cue",new int[4],50,1);flush.CommitStart(lost);flush.Lose(lost);cues.Accept(flush.Read(),1000,0);check(cues.PendingCount==1,"A loss queues one cue while the pre-level is open");
            string again=Guid.NewGuid().ToString("N");flush.Reserve(again,1,"retry",new int[4],50,1);flush.CommitStart(again);cues.Accept(flush.Read(),1000,0);check(cues.Take()==0,"A started attempt flushes the stale cue");flush.Win(again);cues.Accept(flush.Read(),1000,0);check(cues.Take()==0,"No stale minus-one after the retry's win");
            cues.Requeue(-1);check(cues.Take()==-1&&cues.Take()==0,"An interrupted cue is requeued once");
        }
    }
}
#endif
