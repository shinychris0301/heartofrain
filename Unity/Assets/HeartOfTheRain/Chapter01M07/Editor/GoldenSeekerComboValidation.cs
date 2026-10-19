using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.M07.Editor
{
    /// <summary>Editor gate: execute the actual C# builders and compare every serialized field.
    /// Also exercises target exhaustion and motion sampling. Runnable with -executeMethod.</summary>
    public static class GoldenSeekerComboValidation
    {
        [Serializable] public class Fixture {public bool blockers=true;public ReviewPlan plan;public MotionSample[] motion;}
        [Serializable] public class MotionSample {public int effect;public float age,x,y,scale,angle;}
        static void Require(bool condition,string message){if(!condition)throw new InvalidOperationException(message);}
        static void Close(float a,float b,string field)
        {Require(!float.IsNaN(a)&&!float.IsInfinity(a)&&Mathf.Abs(a-b)<.001f,field+" differs: "+a+" / "+b);}
        static void Same(object actual,object expected,string path)
        {
            if(actual==null||expected==null){Require(actual==expected,path+" null mismatch");return;}
            if(actual is float){Close((float)actual,(float)expected,path);return;}
            var type=actual.GetType();Require(type==expected.GetType(),path+" type mismatch");
            if(type.IsPrimitive||actual is string){Require(actual.Equals(expected),path+" differs");return;}
            if(actual is IList)
            {var a=(IList)actual;var b=(IList)expected;Require(a.Count==b.Count,path+" count differs");for(int i=0;i<a.Count;i++)Same(a[i],b[i],path+"["+i+"]");return;}
            foreach(var f in type.GetFields(BindingFlags.Public|BindingFlags.Instance))Same(f.GetValue(actual),f.GetValue(expected),path+"."+f.Name);
        }
        static void Invariants(ReviewPlan p)
        {
            Require(p.createdSeekers==p.flights.Length+p.unassignedSeekers,"Creation count mismatch");
            Require(p.createdSeekers==p.goldenGroups.Length*2+(p.kind==19?2:0),"Golden pair count mismatch");
            var targets=new HashSet<int>();float last=0;int golden=0;
            foreach(var f in p.flights)
            {
                Require(f.targetX>=0&&f.targetX<p.columns&&f.targetY>=0&&f.targetY<p.rows,"Target out of bounds");
                Require(targets.Add(f.targetY*p.columns+f.targetX),"Duplicate target reservation");
                Require(f.travel>=.8f&&f.travel<=1.4001f,"Invalid flight duration");last=Mathf.Max(last,f.start+f.travel);if(f.golden)golden++;
            }
            int assigned=0;foreach(var g in p.goldenGroups)
            {
                Require(g.goldenCreated==2&&g.flightCount>=0&&g.flightCount<=2,"Pair created wrong count");
                int sameStart=0;foreach(var f in p.flights)if(f.golden&&Mathf.Abs(f.start-g.departure)<.001f)sameStart++;
                Require(sameStart==g.flightCount,"Pair did not depart simultaneously");assigned+=g.flightCount;
            }
            Require(assigned==golden,"Golden flight count differs from source pairs");
            if(p.kind==17){var lines=new HashSet<int>();foreach(var f in p.flights)Require(lines.Add(p.rocketVertical?f.targetX:f.targetY),"Duplicate rocket line");}
            int cleared=0,incoming=0;var final=new HashSet<int>();var destroyed=new HashSet<int>();
            foreach(var t in p.tiles)
            {
                if(t.incoming)incoming++;else if(t.hit>=0)cleared++;
                if(t.fallDuration>0)Require(t.fallStart>=last+.18f-.001f,"Refill starts before final impact");
                if(t.hit<0&&!t.reserved)Require(final.Add((int)t.destY*p.columns+t.x),"Overlapping settled cells");
            }
            Require(cleared==incoming&&final.Count==p.columns*p.rows,"Refill did not restore board");
            foreach(var e in p.effects)
            {
                Require(e.duration>0,"Nonpositive effect duration");
                if(e.atlas>=2&&e.atlas<=5)Require(destroyed.Add((int)e.y*p.columns+(int)e.x),"Duplicate debris");
                if(e.flightMotion>0)Require(e.flightIndex>=0&&e.flightIndex<p.flights.Length,"Flight index out of range");
                var v=p.EffectTransform(e,e.duration*.5f);Close(v.x,v.x,"finite x");Close(v.y,v.y,"finite y");Close(v.z,v.z,"finite scale");
            }
            foreach(var pivot in p.flights)
            {int concurrent=0;foreach(var f in p.flights)if(f.start<=pivot.start+.0001f&&pivot.start<f.start+f.travel-.0001f)concurrent++;Require(concurrent<=8,"Flight wave budget exceeded");}
        }
        [MenuItem("Heart of the Rain/M32/Validate Golden Seeker combinations")]
        public static void Validate()
        {
            int fixtures=0;
            foreach(string guid in AssetDatabase.FindAssets("t:TextAsset",new[]{"Assets/HeartOfTheRain/Chapter01M07/Data"}))
            {
                string path=AssetDatabase.GUIDToAssetPath(guid);if(!System.IO.Path.GetFileName(path).StartsWith("GoldenCombo_"))continue;
                var fixture=JsonUtility.FromJson<Fixture>(AssetDatabase.LoadAssetAtPath<TextAsset>(path).text);var e=fixture.plan;
                var a=ReviewPlan.Build(e.columns,e.rows,e.kind,new Vector2Int(e.originX,e.originY),fixture.blockers,e.targetColor,new Vector2Int(e.requestedTargetX,e.requestedTargetY),e.rocketVertical);
                Same(a,e,path);Invariants(a);
                foreach(var sample in fixture.motion)
                {
                    var v=a.EffectTransform(a.effects[sample.effect],sample.age);Close(v.x,sample.x,"sample x");Close(v.y,sample.y,"sample y");Close(v.z,sample.scale,"sample scale");Close(a.EffectAngle(a.effects[sample.effect],sample.age),sample.angle,"sample angle");
                }
                fixtures++;
            }
            Require(fixtures==63,"Expected 63 Golden combo fixtures, got "+fixtures);
            int dynamicCases=0;
            foreach(var size in new[]{new Vector2Int(3,3),new Vector2Int(3,15),new Vector2Int(15,3),new Vector2Int(9,9),new Vector2Int(9,11),new Vector2Int(11,11),new Vector2Int(15,15)})
            foreach(var origin in new[]{new Vector2Int(-1,-1),Vector2Int.zero,new Vector2Int(size.x-1,size.y-1)})
            for(int kind=17;kind<=20;kind++)for(int mode=0;mode<2;mode++)
            {Invariants(ReviewPlan.Build(size.x,size.y,kind,origin,mode==1,-1,new Vector2Int(0,0),mode==1));dynamicCases++;}
            Debug.Log("M32 PASS: "+fixtures+" C# fixture and motion comparisons; "+dynamicCases+" dynamic board cases. Legacy validation remains under M07.");
        }
    }
}
