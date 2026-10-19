using System;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.LevelComplete {
 [Serializable] public sealed class LevelCompleteViewData {
  public int level,chapter=1,coins,stars,completedBefore,completedAfter,total=50,nextLevel;
  public bool firstClear,chapterComplete,hasNext;
 }
 // A local first-clear receipt. No grants are made by animation frames or UI clicks.
 public sealed class LevelCompleteSession {
  int attempt,level,settledAttempt;
  public bool IsOpen {get;private set;}
  public LevelCompleteViewData View {get;private set;}
  public bool Arm(int id,int number) {
   if(IsOpen||id<=attempt||number<1)return false;
   attempt=id;level=number;return true;
  }
  public bool TrySettle(int number,string status,bool busy,HomeState home,int available,int coins,int stars) {
   if(home==null||attempt<=0||settledAttempt==attempt||IsOpen||number!=level||status!="Won"||busy||available<1||number>available)return false;
   int completed=Math.Min(available,Math.Max(home.currentLevel-1,(home.chapterNumber-1)*50+home.completedLevelsInChapter));
   if(number>completed+1)return false;
   bool first=number==completed+1;int after=first?completed+1:completed;
   View=new LevelCompleteViewData{level=number,chapter=(number-1)/50+1,coins=first?Math.Max(0,coins):0,stars=first?Math.Max(0,stars):0,completedBefore=completed,completedAfter=after,total=50,nextLevel=Math.Min(available,after+1),firstClear=first,chapterComplete=number%50==0&&after>=((number-1)/50+1)*50,hasNext=after<available};
   if(first) {
    home.coins=(int)Math.Min(int.MaxValue,(long)Math.Max(0,home.coins)+View.coins);
    home.stars=(int)Math.Min(int.MaxValue,(long)Math.Max(0,home.stars)+View.stars);
    home.currentLevel=View.nextLevel;
    home.chapterNumber=Math.Max(1,(Math.Max(1,after)-1)/50+1);
    home.completedLevelsInChapter=after-(home.chapterNumber-1)*50;home.Normalize();
   }
   settledAttempt=attempt;IsOpen=true;return true;
  }
  public bool Close(){if(!IsOpen)return false;IsOpen=false;return true;}
 }
}
