#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Diagnostics;
using System.Linq;
using HeartOfTheRain.M46;
using UnityEngine;
namespace HeartOfTheRain.Verification {
    // Fixture setup is outside command timing. Both branches use live DTOs;
    // the development flag restores only exact archived77 model helper bodies.
    public static class ModelWork78Proof {
        public static readonly string[] BenchmarkNames={"L4_match","L14_match","L31_match","L33_match","L1_three_rocket_chain","L1_orb_rocket","L1_golden_bomb","L26_power7"};
        public sealed class Prepared {
            public string name;public BoardModel model;public Cell from,to;
            public TurnResult Solve()=>to==null?model.Tap(from.x,from.y):model.Swap(from.x,from.y,to.x,to.y);
        }
        public sealed class Sample {public Prepared prepared;public TurnResult turn;public double milliseconds;public BoardModel.ModelWork work;}
        static Prepared New(LevelData data,string name,bool checkpoint77){var model=new BoardModel(data){VerificationUseCheckpoint77Model78=checkpoint77};return new Prepared{name=name,model=model};}
        public static Prepared Corpus(M46Assets assets,int level,int kind,bool checkpoint77=false){
            var data=JsonUtility.FromJson<LevelData>(assets.levels[level].text);var p=New(data,"L"+(level+1)+"_"+(kind<0?"match":"power"+kind),checkpoint77);
            if(kind<0){var swap=p.model.LegalSwaps().First();p.from=swap[0];p.to=swap[1];}
            else {var gem=p.model.Pieces.Values.First(v=>v.family=="gem");p.from=new Cell(gem.x,gem.y);if(!p.model.InjectReviewPower(gem.x,gem.y,kind))throw new InvalidOperationException("Power fixture rejected: "+p.name);}
            return p;
        }
        public static Prepared Prepare(M46Assets assets,string name,bool checkpoint77=false){
            foreach(int level in new[]{3,13,30,32})if(name=="L"+(level+1)+"_match")return Corpus(assets,level,-1,checkpoint77);
            if(name=="L26_power7")return Corpus(assets,25,7,checkpoint77);
            var data=JsonUtility.FromJson<LevelData>(assets.levels[0].text);var p=New(data,name,checkpoint77);
            if(name=="L1_three_rocket_chain"){
                var row=p.model.Pieces.Values.Where(v=>v.family=="gem").GroupBy(v=>v.y).First(g=>g.Count()>=3).OrderBy(v=>v.x).Take(3).ToArray();p.from=new Cell(row[0].x,row[0].y);foreach(var piece in row)p.model.InjectReviewPower(piece.x,piece.y,4);return p;
            }
            if(name!="L1_orb_rocket"&&name!="L1_golden_bomb")throw new ArgumentException("Unknown model78 fixture: "+name);
            var source=p.model.Pieces.Values.First(v=>v.family=="gem"&&p.model.At(v.x+1,v.y)?.family=="gem");var partner=p.model.At(source.x+1,source.y);p.from=new Cell(source.x,source.y);p.to=new Cell(partner.x,partner.y);
            p.model.InjectReviewPower(source.x,source.y,name=="L1_orb_rocket"?7:16);p.model.InjectReviewPower(partner.x,partner.y,name=="L1_orb_rocket"?4:21);return p;
        }
        public static Sample Measure(Prepared p,bool stages=true){
            p.model.VerificationMeasureWork=stages;p.model.VerificationResetWork();long began=Stopwatch.GetTimestamp();var turn=p.Solve();long end=Stopwatch.GetTimestamp();
            return new Sample{prepared=p,turn=turn,milliseconds=(end-began)*(1000.0/Stopwatch.Frequency),work=p.model.VerificationGetWork()};
        }
    }
}
#endif
