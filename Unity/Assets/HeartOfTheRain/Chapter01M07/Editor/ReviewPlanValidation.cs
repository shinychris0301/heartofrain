using System;
using UnityEngine;
using UnityEditor;

namespace HeartOfTheRain.M07.Editor
{
    public static class ReviewPlanValidation
    {
        static void Close(float a,float b,string field){if(Mathf.Abs(a-b)>.0001f)throw new InvalidOperationException(field+" differs: "+a+" / "+b);}
        [MenuItem("Heart of the Rain/M07/Validate review plans against preview fixtures")]
        public static void Validate()
        {
            int count=0;
            foreach(string path in AssetDatabase.FindAssets("t:TextAsset",new[]{"Assets/HeartOfTheRain/Chapter01M07/Data"}))
            {
                string assetPath=AssetDatabase.GUIDToAssetPath(path);if(!System.IO.Path.GetFileName(assetPath).StartsWith("Review_"))continue;
                var expected=JsonUtility.FromJson<ReviewPlan>(AssetDatabase.LoadAssetAtPath<TextAsset>(assetPath).text);
                var actual=ReviewPlan.Build(expected.columns,expected.rows,expected.kind,new Vector2Int(expected.originX,expected.originY),true,expected.kind>=7?expected.targetColor:5,new Vector2Int(expected.requestedTargetX,expected.requestedTargetY),expected.rocketVertical);
                if(actual.tiles.Length!=expected.tiles.Length||actual.effects.Length!=expected.effects.Length||actual.powers.Length!=expected.powers.Length)throw new InvalidOperationException(assetPath+": array counts differ");
                Close(actual.primary,expected.primary,"primary");Close(actual.duration,expected.duration,"loop duration");
                if(actual.blasts.Length!=expected.blasts.Length)throw new InvalidOperationException("Blast counts differ");
                for(int i=0;i<actual.blasts.Length;i++){var a=actual.blasts[i];var b=expected.blasts[i];if(a.x!=b.x||a.y!=b.y||a.affectsCells!=b.affectsCells)throw new InvalidOperationException("Blast footprint differs");Close(a.start,b.start,"blast start");Close(a.scale,b.scale,"blast recoil scale");}
                for(int i=0;i<actual.tiles.Length;i++)
                {
                    var a=actual.tiles[i];var b=expected.tiles[i];
                    if(a.x!=b.x||a.y!=b.y||a.tile!=b.tile||a.wood!=b.wood||a.reserved!=b.reserved||a.incoming!=b.incoming)throw new InvalidOperationException(assetPath+": tile mismatch "+i);
                    Close(a.hit,b.hit,"hit");if(expected.kind==8||expected.kind==9||expected.kind==15)Close(a.convertedAt,b.convertedAt,"conversion");Close(a.destY,b.destY,"destination");Close(a.fallStart,b.fallStart,"fall start");Close(a.fallDuration,b.fallDuration,"fall duration");
                }
                for(int i=0;i<actual.effects.Length;i++)
                {
                    var a=actual.effects[i];var b=expected.effects[i];if(a.atlas!=b.atlas||a.clip!=b.clip||a.order!=b.order||a.flightMotion!=b.flightMotion||a.flightIndex!=b.flightIndex)throw new InvalidOperationException(assetPath+": effect mismatch "+i);
                    Close(a.start,b.start,"start");Close(a.duration,b.duration,"duration");Close(a.x,b.x,"x");Close(a.y,b.y,"y");Close(a.scale,b.scale,"scale");Close(a.angle,b.angle,"angle");Close(a.vx,b.vx,"velocity x");Close(a.vy,b.vy,"velocity y");Close(a.driftX,b.driftX,"drift x");Close(a.driftY,b.driftY,"drift y");Close(a.gravity,b.gravity,"gravity");Close(a.ramp,b.ramp,"ramp");
                }
                for(int i=0;i<actual.powers.Length;i++){var a=actual.powers[i];var b=expected.powers[i];if(a.atlas!=b.atlas||a.x!=b.x||a.y!=b.y)throw new InvalidOperationException("Power-up binding differs");Close(a.end,b.end,"power activation");Close(a.charge,b.charge,"charge");Close(a.begin,b.begin,"power appearance");}
                if(expected.kind>=7)
                {
                    if(actual.targetColor!=expected.targetColor||actual.beams.Length!=expected.beams.Length)throw new InvalidOperationException("Orb targets differ");Close(actual.activation,expected.activation,"orb activation");
                    for(int i=0;i<actual.beams.Length;i++){var a=actual.beams[i];var b=expected.beams[i];if(a.targetX!=b.targetX||a.targetY!=b.targetY)throw new InvalidOperationException("Beam target differs");Close(a.x,b.x,"beam x");Close(a.y,b.y,"beam y");Close(a.start,b.start,"beam start");Close(a.travel,b.travel,"beam travel");Close(a.end,b.end,"beam end");Close(a.bend,b.bend,"beam bend");}
                }
                if(expected.kind==11||expected.kind==12||expected.kind==13){var a=actual.flight;var b=expected.flight;if(a==null||b==null||a.targetX!=b.targetX||a.targetY!=b.targetY)throw new InvalidOperationException("Flight target differs");Close(a.x,b.x,"flight x");Close(a.y,b.y,"flight y");Close(a.controlX,b.controlX,"flight control x");Close(a.controlY,b.controlY,"flight control y");Close(a.control2X,b.control2X,"second control x");Close(a.control2Y,b.control2Y,"second control y");Close(a.start,b.start,"flight start");Close(a.travel,b.travel,"flight duration");}
                if(expected.kind==14)
                {
                    if(actual.flights.Length!=3||expected.flights.Length!=3)throw new InvalidOperationException("Expected three flights");
                    for(int i=0;i<3;i++){var a=actual.flights[i];var b=expected.flights[i];if(a.targetX!=b.targetX||a.targetY!=b.targetY)throw new InvalidOperationException("Squad target differs");Close(a.x,b.x,"flight x");Close(a.y,b.y,"flight y");Close(a.controlX,b.controlX,"control x");Close(a.controlY,b.controlY,"control y");Close(a.control2X,b.control2X,"second control x");Close(a.control2Y,b.control2Y,"second control y");Close(a.start,b.start,"launch time");Close(a.travel,b.travel,"travel time");}
                }
                if(expected.kind==16)
                {
                    if(actual.flights.Length!=2||expected.flights.Length!=2)throw new InvalidOperationException("Expected two created Golden Seekers");
                    Close(actual.launchTime,expected.launchTime,"lift time");Close(actual.flights[0].start,actual.flights[1].start,"simultaneous departure");
                    for(int i=0;i<2;i++){var a=actual.flights[i];var b=expected.flights[i];if(a.targetX!=b.targetX||a.targetY!=b.targetY)throw new InvalidOperationException("Squad target differs");Close(a.x,b.x,"flight x");Close(a.y,b.y,"flight y");Close(a.controlX,b.controlX,"control x");Close(a.controlY,b.controlY,"control y");Close(a.control2X,b.control2X,"second control x");Close(a.control2Y,b.control2Y,"second control y");Close(a.start,b.start,"launch time");Close(a.travel,b.travel,"travel time");}
                }
                if(expected.kind==15)
                {
                    Close(actual.launchTime,expected.launchTime,"conversion completion");
                    if(actual.flights.Length!=expected.flights.Length||actual.seekerLaunches.Length!=expected.seekerLaunches.Length)throw new InvalidOperationException("Converted seeker counts differ");
                    for(int i=0;i<actual.seekerLaunches.Length;i++){var a=actual.seekerLaunches[i];var b=expected.seekerLaunches[i];if(a.x!=b.x||a.y!=b.y||a.flightIndex!=b.flightIndex)throw new InvalidOperationException("Seeker reservation differs");Close(a.conversion,b.conversion,"conversion");Close(a.start,b.start,"launch");}
                    for(int i=0;i<actual.flights.Length;i++){var a=actual.flights[i];var b=expected.flights[i];if(a.targetX!=b.targetX||a.targetY!=b.targetY)throw new InvalidOperationException("Seeker target differs");Close(a.x,b.x,"flight x");Close(a.y,b.y,"flight y");Close(a.controlX,b.controlX,"control x");Close(a.controlY,b.controlY,"control y");Close(a.control2X,b.control2X,"second control x");Close(a.control2Y,b.control2Y,"second control y");Close(a.start,b.start,"flight start");Close(a.travel,b.travel,"travel");}
                }
                if(actual.rocketVertical!=expected.rocketVertical)throw new InvalidOperationException("Rocket orientation differs");
                count++;
            }
            if(count!=138)throw new InvalidOperationException("Expected 138 supplied review fixtures, got "+count);
            Debug.Log("M30 Golden Seeker R1: all 138 Unity review plans match the exported preview fixtures.");
        }
    }
}
