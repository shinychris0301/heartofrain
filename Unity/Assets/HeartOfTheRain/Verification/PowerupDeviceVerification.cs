#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using UnityEngine.Profiling;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Manifest=HeartOfTheRain.M05.SpriteManifest;

namespace HeartOfTheRain.Verification
{
    // Opt-in suite only. Exercises the active GameplayScreen, its own bank and clock.
    public static class PowerupDeviceVerification
    {
        [Serializable] public class TextureRecord {public int atlas,width,height;public string name,format;public long runtimeBytes;public int loadedCopies;}
        [Serializable] public sealed class IdleSample {public int frame,logicalFrame;public float clock,drawAge;public string key,sprite;public Rect rect;}
        [Serializable] public sealed class IdleObservation {
            public int power,atlas,pieceId;public bool clockAdvanced,frameAdvanced,rectChanged,invalidSequence,passed;
            public List<IdleSample> samples=new List<IdleSample>();
        }
        [Serializable] public sealed class IdleShape {
            public int columns,rows,sampleLimit=96,sampleCount;public float wallLimitSeconds=1.25f,elapsedWall;
            public bool passed,timedOut,sampleCapReached;public List<IdleObservation> powers=new List<IdleObservation>();
        }
        [Serializable] public class Report {public string status,utc,graphics;public bool astcSupported;public long sevenBodyBytes;public List<TextureRecord> textures=new List<TextureRecord>();public List<IdleShape> idleAdvancement=new List<IdleShape>();public List<string> failures=new List<string>();}
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static T Field<T>(object o,string n)=>(T)o.GetType().GetField(n,Private).GetValue(o);
        // Shared verification predicate, not an animation or gameplay clock.
        // Deduplicated atlas rectangles can recur at different logical frames;
        // observe intermediate poses instead of comparing just two endpoints.
        public static void ObserveIdle(IdleObservation observation,IdleSample sample) {
            observation.invalidSequence|=float.IsNaN(sample.clock)||float.IsInfinity(sample.clock)||float.IsNaN(sample.drawAge)||float.IsInfinity(sample.drawAge)||sample.logicalFrame<0||sample.key!="Idle";
            if(observation.samples.Count>0){
                var first=observation.samples[0];var previous=observation.samples[observation.samples.Count-1];
                observation.invalidSequence|=sample.frame<=previous.frame||sample.clock<previous.clock||sample.drawAge<previous.drawAge||sample.key!=first.key;
                observation.clockAdvanced|=sample.clock>first.clock+.00001f;
                observation.frameAdvanced|=sample.drawAge>first.drawAge+.00001f&&sample.logicalFrame!=first.logicalFrame;
                observation.rectChanged|=sample.rect!=first.rect;
            }
            observation.samples.Add(sample);observation.passed=!observation.invalidSequence&&observation.samples.Count>=3&&observation.clockAdvanced&&observation.frameAdvanced&&observation.rectChanged;
        }
        public static IEnumerator Run(GameplayScreen game,GameplayUIAssets ui,Action<string> capture,Action<bool,string> check)
        {
            var report=new Report{utc=DateTime.UtcNow.ToString("o"),graphics=SystemInfo.graphicsDeviceName,astcSupported=SystemInfo.SupportsTextureFormat(TextureFormat.ASTC_4x4)};
            void Require(bool value,string message){check(value,"M70 "+message);if(!value)report.failures.Add(message);}
            var bank=Field<M46AtlasBank>(game,"bank");var ids=new[]{9,10,6,29,40,19,26};var manifests=new Dictionary<int,Manifest>();
            yield return bank.Prewarm(ids.Select(i=>ui.boards.powerResources[i]));
            foreach(int i in ids){
                var m=JsonUtility.FromJson<Manifest>(ui.boards.powerManifests[i].text);manifests.Add(i,m);var c=m.clips.First();
                var sprite=bank.Get(new DrawSprite{bank="power",atlas=i,key=c.name});var texture=sprite.texture;
                string textureName=texture.name;
                string[] sourceNames={"Rocket_Horizontal_Atlas","Rocket_Vertical_Atlas","Bomb_Atlas","RainSeekerBody_Atlas","GoldenSeekerBody_Atlas","RainbowOrbBody_Atlas","DoubleOrbBody_Atlas"};
                string sourceName=sourceNames[Array.IndexOf(ids,i)];
                var copies=Resources.FindObjectsOfTypeAll<Texture2D>().Count(t=>t.name==textureName||t.name==sourceName);
                var record=new TextureRecord{atlas=i,width=texture.width,height=texture.height,name=textureName,format=texture.format.ToString(),runtimeBytes=Profiler.GetRuntimeMemorySizeLong(texture),loadedCopies=copies};report.textures.Add(record);report.sevenBodyBytes+=record.runtimeBytes;
                Require(texture.width==2048&&texture.height==2048,"runtime dimensions "+i);
                Require(copies==1,"one active texture copy "+i+" ("+copies+")");
                Require(!report.astcSupported||texture.format==TextureFormat.ASTC_4x4,"supported ASTC4x4 used "+i+" / "+texture.format);
            }
            float speed=game.playbackSpeed;game.playbackSpeed=1;
            foreach(var shape in new[]{new[]{9,9},new[]{9,11},new[]{11,11}}){
                int level=Array.FindIndex(ui.boards.levels,t=>{var d=JsonUtility.FromJson<LevelData>(t.text);return d.columns==shape[0]&&d.rows==shape[1];});
                Require(level>=0,"authored shape "+shape[0]+"x"+shape[1]);if(level<0)continue;
                game.Load(level);while(!game.InitializationComplete)yield return null;
                bank=Field<M46AtlasBank>(game,"bank");
                yield return bank.Prewarm(ids.Select(i=>ui.boards.powerResources[i]));
                var cells=game.Model.Pieces.Values.Where(p=>p.family=="gem").OrderByDescending(p=>p.y).ThenBy(p=>p.x).Take(6).ToArray();
                int[] powers={4,5,21,11,16,7};
                for(int n=0;n<cells.Length;n++)game.Model.InjectReviewPower(cells[n].x,cells[n].y,powers[n]);
                game.GetType().GetField("idle",Private).SetValue(game,game.Model.Snapshot());yield return null;
                var presentation=Field<BoardPresentation>(game,"presentation");
                DrawSprite Body(int power,out Piece piece,out float clock){piece=game.Model.Pieces.Values.First(x=>x.family=="power"&&x.power==power);clock=Field<float>(game,"clock");int id=piece.id;return presentation.Sample(null,game.Model.Snapshot(),clock,0).First(x=>x.pieceId==id);}
                Sprite Pose(int power){Piece piece;float clock;return bank.Get(Body(power,out piece,out clock));}
                IdleSample Sample(int power){
                    Piece piece;float clock;var draw=Body(power,out piece,out clock);var sprite=bank.Get(draw);var meta=manifests[draw.atlas];var clip=meta.clips.First(c=>c.name==draw.key);
                    int frame=Mathf.Max(0,Mathf.FloorToInt(draw.age*clip.fps));if(clip.loop)frame%=clip.count;else frame=Math.Min(frame,clip.count-1);
                    return new IdleSample{frame=Time.frameCount,clock=clock,drawAge=draw.age,key=draw.key,sprite=sprite.name,logicalFrame=clip.start+frame,rect=sprite.rect};
                }
                var observation=new IdleShape{columns=shape[0],rows=shape[1]};
                foreach(int power in new[]{4,5,21}){var piece=game.Model.Pieces.Values.First(p=>p.family=="power"&&p.power==power);var row=new IdleObservation{power=power,atlas=BoardPresentation.PowerAtlas(power),pieceId=piece.id};ObserveIdle(row,Sample(power));observation.powers.Add(row);}observation.sampleCount=1;
                capture("M70_"+shape[0]+"x"+shape[1]+"_Idle_A");float began=Time.realtimeSinceStartup;
                while(observation.sampleCount<observation.sampleLimit&&Time.realtimeSinceStartup-began<observation.wallLimitSeconds&&!observation.powers.All(p=>p.passed)){
                    yield return null;if(Time.realtimeSinceStartup-began>=observation.wallLimitSeconds)break;foreach(var row in observation.powers)ObserveIdle(row,Sample(row.power));observation.sampleCount++;
                }
                observation.elapsedWall=Time.realtimeSinceStartup-began;observation.passed=observation.powers.All(p=>p.passed);observation.timedOut=!observation.passed&&observation.elapsedWall>=observation.wallLimitSeconds;observation.sampleCapReached=!observation.passed&&observation.sampleCount>=observation.sampleLimit;report.idleAdvancement.Add(observation);
                Require(observation.passed,"Bomb/Rocket live idle advances "+shape[0]+"x"+shape[1]);capture("M70_"+shape[0]+"x"+shape[1]+"_Idle_B");
                game.SetPause(true);float paused=Field<float>(game,"clock");var frozen=Pose(21);yield return new WaitForSecondsRealtime(.25f);
                Require(Field<float>(game,"clock")==paused&&Pose(21)==frozen,"idle respects pause "+shape[0]+"x"+shape[1]);
                game.SetPause(false);yield return new WaitForSecondsRealtime(.17f);Require(Field<float>(game,"clock")>paused,"idle resumes "+shape[0]+"x"+shape[1]);
                foreach(int power in powers){
                    var p=game.Model.Pieces.Values.FirstOrDefault(x=>x.family=="power"&&x.power==power);if(p==null)continue;
                    var turn=game.Model.Tap(p.x,p.y);Require(turn.accepted,"idle interrupted by activation "+power);
                    game.GetType().GetMethod("Accept",Private).Invoke(game,new object[]{turn});while(game.Busy)yield return null;
                    game.Model.Validate();
                }
            }
            game.playbackSpeed=speed;game.Load(0);while(!game.InitializationComplete)yield return null;
            report.status=report.failures.Count==0?"PASS_NATIVE_M70_DEVICE":"FAIL_NATIVE_M70_DEVICE";
            File.WriteAllText(Path.Combine(PlayerRegressionSuite.Output,"M70_Device.json"),JsonUtility.ToJson(report,true));
        }
    }
}
#endif
