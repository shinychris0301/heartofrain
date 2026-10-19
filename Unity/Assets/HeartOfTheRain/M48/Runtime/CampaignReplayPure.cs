using System;using System.Linq;using System.Globalization;using HeartOfTheRain.M46;
namespace HeartOfTheRain.M48 {
 [Serializable] public class ReplayMove {public string kind,before,after;public int ax,ay,bx,by;}
 [Serializable] public class CampaignReplay {public int level,seed,budget;public string expectedStatus;public ReplayMove[] actions;}
 [Serializable] public class CampaignReplaySet {public string milestone,scope;public CampaignReplay[] runs;}
 public static class CampaignReplayRules {
  public static string Fingerprint(BoardModel b){
   var state=string.Join(";",b.Pieces.Values.OrderBy(p=>p.y).ThenBy(p=>p.x).Select(p=>$"{p.x},{p.y},{p.family},{p.color},{p.hp},{p.power}"))+"|"+string.Join(";",b.Goals.OrderBy(x=>x.Key).Select(x=>x.Key+":"+x.Value))+"|"+b.Moves+"|"+b.Status;
   ulong hash=14695981039346656037UL;unchecked{foreach(char c in state){hash^=c;hash*=1099511628211UL;}}return hash.ToString("x16",CultureInfo.InvariantCulture);
  }
  public static bool Apply(BoardModel board,ReplayMove move,out TurnResult result,out string error){
   result=null;error="";
   if(move==null||Fingerprint(board)!=move.before){error="Replay stopped: board differs before action.";return false;}
   if(move.kind!="tap"&&move.kind!="swap"){error="Replay stopped: unsupported action.";return false;}
   result=move.kind=="tap"?board.Tap(move.ax,move.ay):board.Swap(move.ax,move.ay,move.bx,move.by);
   if(!result.accepted){error="Replay stopped: action rejected — "+result.reason;return false;}
   if(Fingerprint(board)!=move.after){error="Replay stopped: board differs after action.";return false;}return true;
  }
 }
}
