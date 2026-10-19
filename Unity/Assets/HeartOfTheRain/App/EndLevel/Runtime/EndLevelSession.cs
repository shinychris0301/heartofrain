using System;
namespace HeartOfTheRain.App.EndLevel
{
    [Serializable] public sealed class EndLevelViewData
    {public int level=18,lives=5;}
    public sealed class EndLevelDecision
    {
        public int Level {get;private set;} public int LivesBefore {get;private set;} public int LivesAfter {get;private set;}
        public int Cost {get{return LivesBefore-LivesAfter;}}
        internal EndLevelDecision(int level,int lives){Level=level;LivesBefore=Math.Max(0,lives);LivesAfter=Math.Max(0,LivesBefore-1);}
    }
    // Opening and canceling are side-effect-free. The caller applies the single committed decision.
    public sealed class EndLevelSession
    {
        public EndLevelViewData View {get;private set;}=new EndLevelViewData();
        public bool IsOpen {get;private set;} public bool Committed {get;private set;}
        public bool Open(int level,int lives)
        {if(IsOpen||Committed)return false;View=new EndLevelViewData{level=Math.Max(1,level),lives=Math.Max(0,lives)};IsOpen=true;return true;}
        public void RefreshLives(int lives){if(IsOpen)View.lives=Math.Max(0,lives);}
        public bool Cancel(){if(!IsOpen||Committed)return false;IsOpen=false;return true;}
        public bool Confirm(int currentLives,out EndLevelDecision result)
        {result=null;if(!IsOpen||Committed)return false;Committed=true;IsOpen=false;result=new EndLevelDecision(View.level,currentLives);return true;}
    }
}
