#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.M46;
using UnityEngine;
namespace HeartOfTheRain.Verification {
    public static class Snapshot79Proof {
        public enum Branch {Current79,Checkpoint78,Checkpoint77}
        public sealed class Frame {public BoardSnapshot state;public int[] keys,order;}
        public sealed class Trace {
            public string name,rawHash,finalHash,checkpointHash,dictionaryOrder;
            public LevelData level;public Frame[] frames;public BoardModel.Snapshot79Work work;
        }
        public sealed class PreparedDirect {public BoardModel model;public Trace trace;public Branch branch;}
        public sealed class DirectSample {
            public BoardSnapshot[] values;public double[] milliseconds;public int[] completedCollections;
            public double totalMilliseconds;public BoardModel.Snapshot79Work work;
        }
        public static string Hash(string value){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
        public static string JsonHash(object value)=>Hash(JsonUtility.ToJson(value));
        public static void Select(BoardModel board,Branch branch){board.VerificationUseLegacySnapshot=false;board.VerificationUseCheckpoint77Model78=branch==Branch.Checkpoint77;board.VerificationUseCheckpoint78Snapshot79=branch==Branch.Checkpoint78;}
        public static Frame CaptureFrame(BoardModel board,BoardSnapshot state){
            var entries=board.Pieces.ToArray();if(entries.Length!=state.pieces.Length)throw new InvalidOperationException("Snapshot79 trace changed during capture");
            var ranks=new Dictionary<int,int>();for(int i=0;i<state.pieces.Length;i++)ranks.Add(state.pieces[i].id,i);
            var frame=new Frame{state=state,keys=new int[entries.Length],order=new int[entries.Length]};
            for(int i=0;i<entries.Length;i++){frame.keys[i]=entries[i].Key;frame.order[i]=ranks[entries[i].Value.id];}return frame;
        }
        public static Trace Capture(M46Assets assets,string fixture,Branch branch=Branch.Current79){
            var p=ModelWork78Proof.Prepare(assets,fixture);Select(p.model,branch);var frames=new List<Frame>();p.model.VerificationResetSnapshot79();p.model.VerificationMeasureSnapshot79=true;
            p.model.VerificationSnapshot79Observer=value=>{if(frames.Count==512)throw new InvalidOperationException("Snapshot79 trace cap exceeded");frames.Add(CaptureFrame(p.model,value));};
            TurnResult turn;try{turn=p.Solve();}finally{p.model.VerificationSnapshot79Observer=null;p.model.VerificationMeasureSnapshot79=false;}
            if(!turn.accepted)throw new InvalidOperationException("Snapshot79 trace command rejected: "+fixture);
            return new Trace{name=fixture,level=p.model.Level,frames=frames.ToArray(),work=p.model.VerificationGetSnapshot79(),rawHash=JsonHash(turn),finalHash=JsonHash(p.model.Snapshot()),checkpointHash=JsonHash(p.model.Checkpoint()),dictionaryOrder=string.Join(";",p.model.Pieces.Select(v=>v.Key+":"+v.Value.id))};
        }
        public static readonly string[] SyntheticNames={"L4_stable32","L4_same_count_new_ids32","L4_shrink_regrow32","L4_reordered_dictionary32"};
        public static Trace Synthetic(M46Assets assets,string name){
            if(!SyntheticNames.Contains(name))throw new ArgumentException("Unknown Snapshot79 workload: "+name);
            var board=new BoardModel(JsonUtility.FromJson<LevelData>(assets.levels[3].text));var frame=CaptureFrame(board,board.Snapshot());var frames=new Frame[32];
            for(int index=0;index<frames.Length;index++){
                var state=JsonUtility.FromJson<BoardSnapshot>(JsonUtility.ToJson(frame.state));var keys=(int[])frame.keys.Clone();var order=(int[])frame.order.Clone();
                if(name=="L4_same_count_new_ids32")state.pieces[order[0]].id=200000+index;
                if(name=="L4_shrink_regrow32"&&index%2!=0){int removed=order[order.Length-1];state.pieces=state.pieces.Where((p,i)=>i!=removed).ToArray();keys=keys.Take(keys.Length-1).ToArray();order=order.Take(order.Length-1).Select(i=>i>removed?i-1:i).ToArray();}
                if(name=="L4_reordered_dictionary32"&&index%2!=0){Array.Reverse(keys);Array.Reverse(order);}
                // A returned Snapshot is ID-sorted, while its dictionary order
                // is a separate input. Changing an ID can change that sorted
                // output position; retain the same bodies/keys when remapping.
                var dictionaryBodies=order.Select(i=>state.pieces[i]).ToArray();state.pieces=state.pieces.OrderBy(p=>p.id).ToArray();
                order=dictionaryBodies.Select(piece=>Array.IndexOf(state.pieces,piece)).ToArray();
                frames[index]=new Frame{state=state,keys=keys,order=order};
            }
            return new Trace{name=name,level=board.Level,frames=frames};
        }
        public static PreparedDirect PrepareDirect(Trace trace,Branch branch){var board=new BoardModel(trace.level);Select(board,branch);return new PreparedDirect{model=board,trace=trace,branch=branch};}
        public static DirectSample MeasureDirect(PreparedDirect p,bool diagnostics=false){
            var board=p.model;board.VerificationMeasureWork=false;board.VerificationMeasureSnapshot79=diagnostics;board.VerificationSnapshot79Observer=null;board.VerificationResetSnapshot79();
            var result=new DirectSample{values=new BoardSnapshot[p.trace.frames.Length],milliseconds=new double[p.trace.frames.Length],completedCollections=new int[p.trace.frames.Length]};
            try{for(int i=0;i<p.trace.frames.Length;i++){
                var frame=p.trace.frames[i];board.VerificationApplySnapshot79(frame.state,frame.keys,frame.order);
                int gc=GC.CollectionCount(0);long began=Stopwatch.GetTimestamp();result.values[i]=board.Snapshot();long end=Stopwatch.GetTimestamp();
                result.completedCollections[i]=GC.CollectionCount(0)-gc;result.milliseconds[i]=(end-began)*1000.0/Stopwatch.Frequency;result.totalMilliseconds+=result.milliseconds[i];
            }}finally{board.VerificationMeasureSnapshot79=false;}
            result.work=board.VerificationGetSnapshot79();return result;
        }
        public static string ResultHash(DirectSample sample)=>Hash(string.Join("\n",sample.values.Select(JsonHash)));
        public static string TraceHash(Trace trace)=>Hash(string.Join("\n",trace.frames.Select(frame=>JsonHash(frame.state)+":"+string.Join(",",frame.keys)+":"+string.Join(",",frame.order))));
    }
}
#endif
