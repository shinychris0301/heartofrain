using System;using System.Collections.Generic;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.App.Home {
    // Session-scoped cosmetics. Durable attempt/credit journals own the economy.
    // Seed old receipts on first read; a lower initial balance is never a loss event.
    public sealed class HomeLivesPresentation {
        readonly HashSet<string> seen=new HashSet<string>();readonly Queue<int> pending=new Queue<int>();
        string player;bool seeded;long revision=-1;int previousLives;
        public int Lives{get;private set;}public int Max{get;private set;}public bool Ready{get;private set;}
        long due,anchor;double monotonic;
        public int PendingCount=>pending.Count;
        public void Seed(PlayerProfile p){if(seeded&&player==p.playerId)return;seen.Clear();pending.Clear();player=p.playerId;seeded=true;revision=-1;previousLives=p.lives;foreach(var a in p.attempts)if(a.state=="Lost"||a.state=="Interrupted")seen.Add("loss/"+a.id);foreach(var c in p.lifeCredits)seen.Add("credit/"+c.key);foreach(var c in p.lifeRefills)seen.Add("refill/"+c.key);}
        void Enqueue(int amount){if(pending.Count<16)pending.Enqueue(amount);}
        public bool Accept(PlayerProfile p,long now,double elapsed){
            Seed(p);if(p.revision<revision)return false;
            foreach(var a in p.attempts)if((a.state=="Lost"||a.state=="Interrupted")&&seen.Add("loss/"+a.id)&&previousLives>0)Enqueue(-1);
            foreach(var c in p.lifeCredits)if(seen.Add("credit/"+c.key)&&c.lives==1)Enqueue(1);
            foreach(var c in p.lifeRefills)if(seen.Add("refill/"+c.key)&&c.livesAfter-c.livesBefore==1)Enqueue(1);
            // A cue queued before a new attempt began is stale once that attempt runs; it must not float over a later outcome.
            if(HasActiveAttempt(p))pending.Clear();
            revision=p.revision;Lives=previousLives=p.lives;Max=p.maxLives;due=p.livesRefillDueUnix;anchor=now;monotonic=elapsed;Ready=true;return true;
        }
        static bool HasActiveAttempt(PlayerProfile p){foreach(var a in p.attempts)if(a.state=="Reserved"||a.state=="Started")return true;return false;}
        // A cue interrupted by a Home rebuild plays again next.
        public void Requeue(int amount){if(amount==0)return;var rest=pending.ToArray();pending.Clear();pending.Enqueue(amount);foreach(var r in rest)pending.Enqueue(r);}
        public void Unavailable(){Ready=false;}
        public long Remaining(double elapsed){if(!Ready||Lives>=Max||due<=0)return -1;return (long)Math.Ceiling(Math.Max(0,due-anchor-Math.Max(0,elapsed-monotonic)));}
        public string Status(double elapsed){if(!Ready)return "\u2026";if(Lives>=Max)return HomeLivesText.T("full");long s=Remaining(elapsed);return s<=0?"\u2026":Format(s);}
        public bool Clock(double elapsed)=>!Ready||Lives<Max&&Remaining(elapsed)<3600;
        public static string Format(long s)=>s>=3600?(s/3600)+":"+(s%3600/60).ToString("00")+":"+(s%60).ToString("00"):(s/60).ToString("00")+":"+(s%60).ToString("00");
        public int Take()=>pending.Count==0?0:pending.Dequeue();
    }
}
