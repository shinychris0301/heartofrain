using System;using System.Linq;using System.Collections.Generic;
namespace HeartOfTheRain.App.Journey
{
 [Serializable] public sealed class JourneyChapter {public int number,sourcePage;public string title,sourceTitle,art,opening,ending;}
 [Serializable] public sealed class JourneyCatalog {public JourneyChapter[] chapters;}
 [Serializable] public sealed class JourneyState {public int completedLevels=17,readingChapter,beat;}
 // Read-only projection of campaign progress: never writes to economy or board state.
 public sealed class JourneySession
 {
  public const int LevelsPerChapter=50;
  public JourneyCatalog Catalog {get;private set;}public JourneyState State {get;private set;}=new JourneyState();
  public bool Reading=>State.readingChapter>0;
  public JourneyChapter Current=>Catalog.chapters.FirstOrDefault(c=>c.number==State.readingChapter);
  public JourneySession(JourneyCatalog catalog){if(catalog==null||catalog.chapters==null||catalog.chapters.Length==0)throw new ArgumentException("Journey catalog is empty");Catalog=catalog;}
  public static int FirstLevel(int chapter)=>1+(chapter-1)*LevelsPerChapter;
  public static int LastLevel(int chapter)=>chapter*LevelsPerChapter;
  public bool Unlocked(int number)=>number>0&&State.completedLevels>=FirstLevel(number)-1;
  public bool Complete(int number)=>State.completedLevels>=LastLevel(number);
  public void SetProgress(int completed){State.completedLevels=Math.Max(0,Math.Min(Catalog.chapters.Length*LevelsPerChapter,completed));if(Reading&&!Unlocked(State.readingChapter))Close();if(Reading&&!Complete(State.readingChapter))State.beat=0;}
  public bool Open(int chapter){if(!Catalog.chapters.Any(c=>c.number==chapter)||!Unlocked(chapter))return false;State.readingChapter=chapter;State.beat=0;return true;}
  public bool Next(){if(!Reading||State.beat!=0||!Complete(State.readingChapter))return false;State.beat=1;return true;}
  public bool Previous(){if(!Reading||State.beat==0)return false;State.beat=0;return true;}
  public void Close(){State.readingChapter=0;State.beat=0;}
  public JourneyChapter[] Cards()
  {
   var unlocked=Catalog.chapters.Where(c=>Unlocked(c.number)).OrderByDescending(c=>c.number);
   var next=Catalog.chapters.FirstOrDefault(c=>!Unlocked(c.number));
   return next==null?unlocked.ToArray():unlocked.Concat(new[]{next}).ToArray();
  }
 }
}
