#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.Verification {
    // Independent compiled checkpoint77 dependency resolver. The method body
    // between markers is validated against the frozen77 bank source.
    public sealed class CommandPreparation77Control {
        readonly M46Assets assets;readonly Dictionary<string,BodyAsset> bodies;readonly Dictionary<string,ClipAsset> clips;
        public CommandPreparation77Control(M46Assets source){assets=source;bodies=source.bodies.ToDictionary(b=>b.key);clips=source.obstacleClips.ToDictionary(c=>c.key);}
        static string PathAt(string[] paths,int i)=>paths!=null&&i<paths.Length?paths[i]:null;
// BEGIN EXACT77 RequiredResources
        public HashSet<string> RequiredResources(IEnumerable<BoardStep> steps) {
            steps=steps.SelectMany(s=>s.playbackTracks==null?new[]{s}:new[]{s}.Concat(s.playbackTracks.Select(t=>t.step)));
            var needed=new HashSet<string>();
            Action<int> power=i=>{var p=PathAt(assets.powerResources,i);if(!string.IsNullOrEmpty(p))needed.Add(p);};
            Action<string> body=key=>{BodyAsset b;if(bodies.TryGetValue(key,out b)&&!string.IsNullOrEmpty(b.resource))needed.Add(b.resource);};
            Action<string> family=f=>{foreach(var c in clips.Values.Where(c=>c.key.StartsWith(f+"/",StringComparison.Ordinal)))foreach(var p in c.pageResources??new string[0])if(!string.IsNullOrEmpty(p))needed.Add(p);};
            var plan=HeartOfTheRain.M48.EffectResources.ForSteps(steps);
            foreach(var p in plan.powers)power(p);foreach(var b in plan.bodies)body(b);foreach(var f in plan.obstacleFamilies)family(f);
            return needed;
        }
// END EXACT77 RequiredResources
    }
}
#endif
