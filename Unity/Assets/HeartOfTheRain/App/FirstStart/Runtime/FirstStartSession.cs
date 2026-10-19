using System;using System.Linq;using HeartOfTheRain.M46;using HeartOfTheRain.App.Settings;
namespace HeartOfTheRain.App.FirstStart {
 public enum FirstStartStage { Prologue,Chapter,Match,Rocket,Clear,Ready,Complete }
 public sealed class FirstStartSession {
  public const string StageKey="HeartOfTheRain.FirstStart.v1.stage",CompleteKey="HeartOfTheRain.FirstStart.v1.complete";
  readonly ISettingsStore store;readonly LevelData[] lessons;
  public FirstStartStage Stage{get;private set;}public BoardModel Board{get;private set;}public bool Solved{get;private set;}public bool Busy{get;private set;}
  public bool Practice=>Stage>=FirstStartStage.Match&&Stage<=FirstStartStage.Clear;
  public bool CanContinue=>!Busy&&Stage!=FirstStartStage.Complete&&(!Practice||Solved);
  public FirstStartSession(ISettingsStore storage,LevelData[] fixtures,int completedLevels=0){store=storage;lessons=fixtures;if(fixtures==null||fixtures.Length!=3)throw new ArgumentException("Three practice lessons required");int saved=store.Read(StageKey,0);Stage=store.Read(CompleteKey,0)==1||completedLevels>0?FirstStartStage.Complete:(FirstStartStage)Math.Max(0,Math.Min(5,saved));ResetBoard();}
  void ResetBoard(){Solved=false;Busy=false;Board=Practice?new BoardModel(lessons[(int)Stage-2]):null;if(Stage==FirstStartStage.Clear&&!Board.InjectReviewPower(2,2,4))throw new InvalidOperationException("Missing practice rocket cell");}
  void Save(){store.Write(StageKey,(int)Stage);store.Write(CompleteKey,Stage==FirstStartStage.Complete?1:0);store.Flush();}
  public bool Next(){if(!CanContinue)return false;Stage++;ResetBoard();Save();return true;}
  public void Skip(){Stage=Stage<FirstStartStage.Match?FirstStartStage.Match:FirstStartStage.Complete;ResetBoard();Save();}
  public void Retry(){if(!Practice)return;ResetBoard();}
  public Cell[] Hint=>Stage==FirstStartStage.Match?new[]{new Cell(2,3),new Cell(2,2)}:Stage==FirstStartStage.Rocket?new[]{new Cell(2,3),new Cell(2,2)}:Stage==FirstStartStage.Clear?new[]{new Cell(2,2)}:new Cell[0];
  public TurnResult Swap(int ax,int ay,int bx,int by){if(!Practice||Busy||Solved||Stage==FirstStartStage.Clear)return Reject();var h=Hint;if(!((ax==h[0].x&&ay==h[0].y&&bx==h[1].x&&by==h[1].y)||(bx==h[0].x&&by==h[0].y&&ax==h[1].x&&ay==h[1].y)))return Reject();var result=Board.Swap(ax,ay,bx,by);Busy=result.accepted;return result;}
  public TurnResult Tap(int x,int y){if(Stage!=FirstStartStage.Clear||Busy||Solved||x!=2||y!=2)return Reject();var result=Board.Tap(x,y);Busy=result.accepted;return result;}
  public void FinishAnimation(){if(!Busy)return;Busy=false;Solved=Stage==FirstStartStage.Match?Board.Turn>0:Stage==FirstStartStage.Rocket?Board.Pieces.Values.Any(p=>p.family=="power"&&(p.power==4||p.power==5)):Stage==FirstStartStage.Clear&&Board.Goals.Values.All(v=>v==0);}
  static TurnResult Reject()=>new TurnResult{accepted=false,reason="Follow the highlighted move"};
 }
}
