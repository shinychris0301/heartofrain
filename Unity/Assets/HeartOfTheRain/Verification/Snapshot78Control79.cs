#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections.Generic;
namespace HeartOfTheRain.M46 {
    public sealed partial class BoardModel {
        [NonSerialized] public bool VerificationUseCheckpoint78Snapshot79;
        [NonSerialized] public bool VerificationMeasureSnapshot79;
        [NonSerialized] public Action<BoardSnapshot> VerificationSnapshot79Observer;
        [Serializable] public struct Snapshot79Work {public int calls,copiedPieces,cacheHits,rebuilds,rebuiltPieces,notEligibleRebuilds,identityRebuilds,nonReusableBuilds;}
        Snapshot79Work snapshot79Work;
        public void VerificationResetSnapshot79(){snapshot79Work=default(Snapshot79Work);}
        public Snapshot79Work VerificationGetSnapshot79()=>snapshot79Work;
        void VerificationRecordSnapshot79(int count,bool hit,bool reusable,bool eligible){
            if(!VerificationMeasureSnapshot79)return;
            snapshot79Work.calls++;snapshot79Work.copiedPieces+=count;
            if(hit)snapshot79Work.cacheHits++;else{snapshot79Work.rebuilds++;snapshot79Work.rebuiltPieces+=count;if(eligible)snapshot79Work.identityRebuilds++;else snapshot79Work.notEligibleRebuilds++;}
            if(!reusable)snapshot79Work.nonReusableBuilds++;
        }
        BoardSnapshot SnapshotFromControl78Snapshot79(){
            // The exact78 helper shares scratch with the model. A later switch
            // back to production must rebuild its own proven-valid rank map.
            snapshotRanksReusable=false;
            if(!VerificationMeasureSnapshot79)return SnapshotFromCheckpoint78Snapshot79();
            int count=Pieces.Count;bool eligible=snapshotRanks.Count==count;
            var result=SnapshotFromCheckpoint78Snapshot79();
            // The old helper marks a visit only after accepting a rank, and
            // its generation advances once per call. Thus all ranks visited
            // in this generation identify its actual completed fast path.
            bool hit=eligible;for(int i=0;hit&&i<count;i++)hit=snapshotRankVisits[i]==snapshotGeneration;
            VerificationRecordSnapshot79(count,hit,snapshotRanks.Count==count,eligible);
            return result;
        }
        public void VerificationApplySnapshot79(BoardSnapshot value,int[] keys,int[] order){
            if(value==null||keys==null||order==null||keys.Length!=value.pieces.Length||order.Length!=keys.Length)throw new ArgumentException("Invalid snapshot79 fixture");
            Pieces.Clear();for(int i=0;i<keys.Length;i++)Pieces.Add(keys[i],value.pieces[order[i]].Copy());
            Goals.Clear();foreach(var goal in value.goals)Goals.Add(goal.family,goal.count);
            Moves=value.moves;Turn=value.turn;Status=value.status;
        }
// BEGIN EXACT78 SnapshotFromScratch
        BoardSnapshot SnapshotFromCheckpoint78Snapshot79(){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(VerificationUseCheckpoint77Model78)return SnapshotFromCheckpoint77Model78();
#endif
            // Stable merges compare IDs directly, avoiding comparer callbacks
            // and larger sort-entry swaps. Scratch never owns returned bodies.
            int count=Pieces.Count;if(snapshotPieces.Length<count){int capacity=Math.Max(count,snapshotPieces.Length*2);snapshotPieces=new Piece[capacity];snapshotMerge=new Piece[capacity];snapshotRankVisits=new int[capacity];}
            if(snapshotRankVisits.Length<count)snapshotRankVisits=new int[snapshotPieces.Length];
            int generation=unchecked(++snapshotGeneration);if(generation==0){Array.Clear(snapshotRankVisits,0,snapshotRankVisits.Length);generation=++snapshotGeneration;}
            // Public callers can replace, remove/reinsert or change IDs. Scan
            // every live identity before reusing ordering; duplicate IDs fall
            // back to the original stable sort instead of aliasing a slot.
            bool ordered=snapshotRanks.Count==count;
            if(ordered)foreach(var piece in Pieces.Values){int rank;if(!snapshotRanks.TryGetValue(piece.id,out rank)||snapshotRankVisits[rank]==generation){ordered=false;break;}snapshotRankVisits[rank]=generation;snapshotPieces[rank]=piece;}
            int index=0;if(!ordered)foreach(var piece in Pieces.Values)snapshotPieces[index++]=piece;
            var source=snapshotPieces;var target=snapshotMerge;
            for(int width=1;!ordered&&width<count;width*=2){
                for(int start=0;start<count;start+=width*2){
                    int middle=Math.Min(start+width,count),end=Math.Min(start+width*2,count),left=start,right=middle,write=start;
                    while(left<middle&&right<end){if(source[left].id<=source[right].id)target[write++]=source[left++];else target[write++]=source[right++];}
                    while(left<middle)target[write++]=source[left++];while(right<end)target[write++]=source[right++];
                }
                var swap=source;source=target;target=swap;
            }
            if(!ordered){snapshotRanks.Clear();for(int i=0;i<count;i++)if(!snapshotRanks.ContainsKey(source[i].id))snapshotRanks.Add(source[i].id,i);}
            var pieces=count==0?Array.Empty<Piece>():new Piece[count];for(int i=0;i<count;i++)pieces[i]=source[i].Copy();
            // Do not retain removed live bodies after the snapshot completes.
            Array.Clear(snapshotPieces,0,count);Array.Clear(snapshotMerge,0,count);
            count=Goals.Count;if(snapshotGoals.Length<count)snapshotGoals=new SnapshotGoal[Math.Max(count,snapshotGoals.Length*2)];index=0;
            foreach(var goal in Goals){int at=index++;while(at>0&&GoalSnapshotOrder.Compare(snapshotGoals[at-1].family,goal.Key)>0){snapshotGoals[at]=snapshotGoals[at-1];at--;}snapshotGoals[at]=new SnapshotGoal{family=goal.Key,count=goal.Value};}
            var goals=count==0?Array.Empty<Goal>():new Goal[count];for(int i=0;i<count;i++){var goal=snapshotGoals[i];goals[i]=new Goal{family=goal.family,count=goal.count};}Array.Clear(snapshotGoals,0,count);
            return new BoardSnapshot{pieces=pieces,goals=goals,moves=Moves,turn=Turn,status=Status};
        }
// END EXACT78 SnapshotFromScratch
    }
}
#endif
