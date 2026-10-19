using System;
using System.Collections.Generic;
namespace HeartOfTheRain.App.PreLevel
{
    [Serializable] public sealed class PreLevelGoal { public string family;public int count; }
    [Serializable] public sealed class PreLevelViewData
    {
        public int level=18,lives=5,rewardCoins=50,rewardStars=1;
        public string difficulty="",message="";public bool busy,retry;
        public PreLevelGoal[] goals=new PreLevelGoal[0];
        public int[] stock={5,5,3,2};public bool[] selected=new bool[4];
    }
    public sealed class PreLevelTicket
    {
        public int id,level;public int[] powerKinds;internal bool[] chosen;
    }
    // Selection is a reservation. Inventory changes only after successful gameplay initialization.
    public sealed class PreLevelSession
    {
        public PreLevelViewData View {get;private set;}=new PreLevelViewData();
        public bool IsOpen {get;private set;}
        int serial;PreLevelTicket pending;readonly int[] stock;
        public PreLevelSession(int[] initialStock)
        {
            if(initialStock==null||(initialStock.Length!=3&&initialStock.Length!=4))throw new ArgumentException("Four starting booster counts are required: Rocket, Bomb, Rainbow Orb, Golden Seeker.");
            // Upgrade legacy [Rocket+Bomb pack, Orb, Seeker] without losing either item.
            stock=initialStock.Length==3?new[]{initialStock[0],initialStock[0],initialStock[1],initialStock[2]}:(int[])initialStock.Clone();
            for(int i=0;i<4;i++)stock[i]=Math.Max(0,stock[i]);
        }
        public void Open(int level,int lives,PreLevelGoal[] goals,int coins,int stars,string difficulty="",bool retry=false)
        {
            if(pending!=null)throw new InvalidOperationException("A level is already launching.");
            View=new PreLevelViewData{level=Math.Max(1,level),lives=Math.Max(0,lives),goals=goals??new PreLevelGoal[0],rewardCoins=Math.Max(0,coins),rewardStars=Math.Max(0,stars),difficulty=difficulty??"",retry=retry,stock=(int[])stock.Clone()};
            IsOpen=true;
        }
        public void RefreshLives(int lives){if(IsOpen&&pending==null)View.lives=Math.Max(0,lives);}
        public bool Toggle(int index)
        {
            if(!IsOpen||pending!=null||index<0||index>=4||(View.retry&&View.lives<=0))return false;
            if(stock[index]<=0){View.message="No boosters remaining";return false;}
            View.selected[index]=!View.selected[index];View.message="";return true;
        }
        public bool Close(){if(pending!=null)return false;IsOpen=false;View.selected=new bool[4];return true;}
        public bool TryBegin(out PreLevelTicket ticket)
        {
            ticket=null;if(!IsOpen||pending!=null)return false;
            if(View.lives<=0){View.message="No lives remaining";return false;}
            var kinds=new List<int>();
            for(int i=0;i<4;i++)if(View.selected[i])
            {
                if(stock[i]<=0){View.message="A selected booster is unavailable";return false;}
                kinds.Add(new[]{4,21,7,16}[i]);
            }
            pending=new PreLevelTicket{id=++serial,level=View.level,powerKinds=kinds.ToArray(),chosen=(bool[])View.selected.Clone()};ticket=pending;View.busy=true;View.message="";return true;
        }
        public bool Complete(PreLevelTicket ticket)
        {
            if(ticket==null||!ReferenceEquals(ticket,pending))return false;
            for(int i=0;i<4;i++)if(pending.chosen[i])stock[i]--;
            View.stock=(int[])stock.Clone();pending=null;View.busy=false;IsOpen=false;return true;
        }
        public bool Fail(PreLevelTicket ticket,string reason)
        {
            if(ticket==null||!ReferenceEquals(ticket,pending))return false;
            pending=null;View.busy=false;View.message=reason;return true;
        }
        public int Count(int index){return stock[index];}
    }
}
