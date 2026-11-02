using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.M46;
using HeartOfTheRain.M48;
namespace HeartOfTheRain.M47 {
    // Dependency paths only. A plan owns no texture, sprite, residency result or
    // playback state. The compiled queue's snapshots/tracks remain immutable.
    public sealed class CommandResourcePreparation {
        sealed class ClipPaths {public readonly string Key;public readonly string[] Paths;public ClipPaths(string key,string[] paths){Key=key;Paths=paths;}}
        // Captured only on the caller/main thread. No Unity object or mutable
        // asset array is retained by the detached contexts used by workers.
        sealed class Metadata {
            public readonly string[] Powers;
            public readonly Dictionary<string,string> Bodies;
            public readonly ClipPaths[] Clips;
            public Metadata(M46Assets source){
                Powers=source.powerResources==null?null:(string[])source.powerResources.Clone();
                Bodies=source.bodies.ToDictionary(b=>b.key,b=>b.resource);
                // Capture the old dictionary's actual value order before
                // discarding the asset records; that is request-order policy.
                Clips=source.obstacleClips.ToDictionary(c=>c.key).Values.Select(c=>new ClipPaths(c.key,c.pageResources==null?null:(string[])c.pageResources.Clone())).ToArray();
            }
        }
        readonly Metadata metadata;
        readonly Dictionary<string,string[]> familyPaths=new Dictionary<string,string[]>();
        readonly Dictionary<string,string[]> bodyKeys=new Dictionary<string,string[]>();
        static readonly string[] TileKeys={"tile0","tile1","tile2","tile3","tile4","tile5"};
        public CommandResourcePreparation(M46Assets source){
            if(source==null)throw new ArgumentNullException(nameof(source));
            metadata=new Metadata(source);
        }
        CommandResourcePreparation(Metadata source){metadata=source;}
        // Share only private read-only string metadata. Mutable resolver caches
        // are fresh for every context, so main rendering and workers do not race.
        public CommandResourcePreparation Detach()=>new CommandResourcePreparation(metadata);
        public sealed class Plan {
            readonly BoardStep[] phases;
            readonly HashSet<string>[] paths;
            // The renderer/loaders consume these sets read-only, as they did
            // the bank's transient sets. Mutating them invalidates the plan.
            public HashSet<string> All {get;private set;}
            public int Count=>phases.Length;
            internal Plan(BoardStep[] source,HashSet<string>[] perPhase,HashSet<string> all){phases=source;paths=perPhase;All=all;}
            public HashSet<string> Phase(int index){if(index<0||index>=paths.Length)throw new ArgumentOutOfRangeException(nameof(index));return paths[index];}
            public bool MatchesPhase(int index,BoardStep step)=>index>=0&&index<phases.Length&&ReferenceEquals(phases[index],step);
            public bool Matches(IList<BoardStep> source){if(source==null||source.Count!=phases.Length)return false;for(int i=0;i<phases.Length;i++)if(!ReferenceEquals(source[i],phases[i]))return false;return true;}
        }
        // Match the old scanner's one-level track expansion exactly. Deeper
        // recursion would introduce a new dependency/prefetch policy.
        static IEnumerable<BoardStep> Flatten(BoardStep phase){yield return phase;if(phase.playbackTracks!=null)foreach(var track in phase.playbackTracks)yield return track.step;}
        static string PathAt(string[] paths,int index)=>paths!=null&&index<paths.Length?paths[index]:null;
        string[] FamilyPaths(string family){
            string[] cached;string key=family??string.Empty;if(familyPaths.TryGetValue(key,out cached))return cached;
            var found=new List<string>();foreach(var clip in metadata.Clips)if(clip.Key.StartsWith(family+"/",StringComparison.Ordinal))foreach(var path in clip.Paths??Array.Empty<string>())if(!string.IsNullOrEmpty(path))found.Add(path);
            cached=found.ToArray();familyPaths.Add(key,cached);return cached;
        }
        HashSet<string> Resolve(EffectResources typed){
            var paths=new HashSet<string>();
            foreach(int atlas in typed.powers){var path=PathAt(metadata.Powers,atlas);if(!string.IsNullOrEmpty(path))paths.Add(path);}
            foreach(string key in typed.bodies){string path;if(metadata.Bodies.TryGetValue(key,out path)&&!string.IsNullOrEmpty(path))paths.Add(path);}
            foreach(string family in typed.obstacleFamilies)foreach(string path in FamilyPaths(family))paths.Add(path);
            return paths;
        }
        string BodyKey(Piece piece){
            if(piece.family=="crystal")return "crystalIcon";if(piece.family=="gem")return TileKeys[piece.color];if(piece.family=="pail")return "pail_Full";
            string[] keys;if(!bodyKeys.TryGetValue(piece.family,out keys)){keys=new string[16];for(int i=0;i<keys.Length;i++)keys[i]=piece.family+"_"+i;bodyKeys.Add(piece.family,keys);}
            return piece.hp>=0&&piece.hp<keys.Length?keys[piece.hp]:piece.family+"_"+piece.hp;
        }
        static int PowerAtlas(int kind){switch(kind){case 4:return 9;case 5:return 10;case 7:return 19;case 11:return 29;case 16:return 40;default:return 6;}}
        public Plan Build(IList<BoardStep> queue){
            if(queue==null)throw new ArgumentNullException(nameof(queue));
            var phases=new BoardStep[queue.Count];var paths=new HashSet<string>[queue.Count];var all=new EffectResources();
            for(int i=0;i<queue.Count;i++){
                phases[i]=queue[i];var typed=EffectResources.ForSteps(Flatten(phases[i]),BodyKey,PowerAtlas);paths[i]=Resolve(typed);
                all.powers.UnionWith(typed.powers);all.bodies.UnionWith(typed.bodies);all.obstacleFamilies.UnionWith(typed.obstacleFamilies);
            }
            // A union of phase path sets would interleave powers/bodies/clips.
            // Resolve the combined categories to retain the old request order.
            return new Plan(phases,paths,Resolve(all));
        }
    }
    public sealed partial class GameplayScreen {
        CommandResourcePreparation commandResourcePreparation;
        CommandResourcePreparation.Plan commandResourcePlan;
        M46AtlasBank commandResourceOwner;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        [NonSerialized] public bool VerificationUseCheckpoint77Resources;
#endif
        bool UsePreparedCommandResources {get{
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            return !VerificationUseCheckpoint77Resources;
#else
            return true;
#endif
        }}
        void ResetCommandPreparation(){commandResourceOwner=bank;commandResourcePreparation=assets==null?null:new CommandResourcePreparation(assets);commandResourcePlan=null;}
        void ClearCommandResources(){commandResourcePlan=null;}
        void PrepareCommandResources(){
            if(!UsePreparedCommandResources){commandResourcePlan=null;return;}
            if(commandResourceOwner!=bank||commandResourcePreparation==null)ResetCommandPreparation();
            commandResourcePlan=commandResourcePreparation.Build(queue);
        }
        void EnsureCommandResources(){if(commandResourceOwner!=bank||commandResourcePlan==null||!commandResourcePlan.Matches(queue))PrepareCommandResources();}
        HashSet<string> CurrentPhaseResources(){
            if(!UsePreparedCommandResources)return bank.RequiredResources(new[]{queue[queueIndex]});
            EnsureCommandResources();return commandResourcePlan.Phase(queueIndex);
        }
        HashSet<string> WholeQueueResources(){
            if(!UsePreparedCommandResources)return bank.RequiredResources(queue);
            EnsureCommandResources();return commandResourcePlan.All;
        }
    }
}
