#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.Verification
{
    public static class SwapCreationVerification
    {
        [Serializable] class Report {public string status,utc,scope="Native Unity model and sampled presentation checks; device input/rendering is separate.";public int checks;public List<string> failures=new List<string>();}
        public static void Run(){
            var r=new Report{utc=DateTime.UtcNow.ToString("o")};void Check(bool ok,string n){r.checks++;if(!ok)r.failures.Add(n);}
            try{
                foreach(bool vertical in new[]{false,true})foreach(bool reverse in new[]{false,true})foreach(bool otherEndpoint in new[]{false,true}){
                    var board=new BoardModel(SwapCreationFixtures.Rocket(vertical,reverse));var from=SwapCreationFixtures.From(vertical,reverse);var to=SwapCreationFixtures.To();var source=board.At(from.x,from.y).Copy();int moves=board.Moves;
                    var turn=otherEndpoint?board.Swap(to.x,to.y,from.x,from.y):board.Swap(from.x,from.y,to.x,to.y);string label=vertical+"/"+reverse+"/"+otherEndpoint;
                    Check(turn.accepted,"Accepted fixture "+label);var match=turn.steps.First(s=>s.kind=="match");var made=match.created.Single();
                    Check(made.id==source.id&&made.x==to.x&&made.y==to.y,"Creation anchors to matching swap endpoint "+label);
                    Check(made.power==(vertical?5:4),"Rocket follows gesture axis "+label);
                    Check(board.Moves==moves-1&&board.Turn==1,"Exactly one move/turn "+label);board.Validate();
                    var swap=BoardPlayback.Build(turn.steps,board.Level).First();var view=new BoardPresentation();
                    foreach(float u in new[]{0f,.25f,.5f,.75f,1f}){
                        var pose=view.Sample(swap,swap.before,u*swap.duration,0).Single(d=>d.pieceId==source.id);
                        Check(Math.Abs(pose.x-(from.x+(to.x-from.x)*(u*u*(3-2*u))))<.001f&&Math.Abs(pose.y-(from.y+(to.y-from.y)*(u*u*(3-2*u))))<.001f,"Accepted swap interpolates "+label+"/"+u);
                    }
                    var created=view.Sample(match,match.before,.08f,0).Single(d=>d.pieceId==made.id);Check(created.atlas==(vertical?10:9)&&created.x==4&&created.y==4,"Created body uses correct atlas and cell "+label);
                    foreach(var step in new[]{swap,match}){
                        float elapsed=0;int samples=0;
                        while(elapsed<step.duration-.0001f){elapsed+=BoardPlayback.VisibleAdvance(step,.5f);if(elapsed<step.duration-.0001f)samples++;}
                        Check(samples>=2,"Long frame retains intermediate "+step.kind+" poses "+label);
                        Check(BoardPlayback.VisibleAdvance(step,.01f)==.01f,"Normal frame keeps original speed "+step.kind);
                    }
                    Check(BoardPlayback.VisibleAdvance(new BoardStep{kind="gravity",duration=.1f},.5f)==.5f,"Fall clock retains existing catch-up");
                }
                foreach(bool vertical in new[]{false,true}){
                    var board=new BoardModel(SwapCreationFixtures.Rocket(vertical,false,5));var from=SwapCreationFixtures.From(vertical,false);var turn=board.Swap(from.x,from.y,4,4);
                    Check(turn.steps.First(s=>s.kind=="match").created.Single().power==7,"Five-line Orb has priority over gesture Rocket");
                }
            }catch(Exception e){r.failures.Add(e.ToString());}
            r.status=r.failures.Count==0?"PASS_NATIVE_SWAP_CREATION":"FAIL_NATIVE_SWAP_CREATION";string folder=Path.GetFullPath("../Verification/Evidence/SwapCreation");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"Native_Checks.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.failures.Count==0?0:1);
        }
    }
}
#endif
