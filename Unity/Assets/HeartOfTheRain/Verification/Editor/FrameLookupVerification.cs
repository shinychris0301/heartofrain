#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Manifest=HeartOfTheRain.M05.SpriteManifest;
namespace HeartOfTheRain.Verification {
    public static class FrameLookupVerification {
        [Serializable] public sealed class Timing {public int iteration,lookups;public double legacyMs,directMs;}
        [Serializable] public sealed class IdleObserverRow {
            public int power,atlas,firstFrame,middleFrame,lastFrame;public bool endpointRectsEqual,passedWithIntermediate,frozenClockRejected,frozenFrameRejected,constantRectRejected;
            public List<PowerupDeviceVerification.IdleSample> samples=new List<PowerupDeviceVerification.IdleSample>();
        }
        [Serializable] public sealed class Report {
            public string status,utc,scope="Native Editor sprite identity, hide/loop/hold, eviction/disposal controls and alternating warmed lookup measurements. Idle observer controls use controlled draw ages and actual native sprite rects, including deduplicated endpoint aliases and injected frozen/stuck negative controls; actual live clocks are recorded separately by Android M70_Device. CPU spans are descriptive; no Android frame-rate claim.";
            public int checks,powerClips,obstacleClips,lookups,idleAliasControls,idleObserverPositiveControls,idleObserverNegativeControls;public List<string> errors=new List<string>();public List<Timing> timings=new List<Timing>();public List<IdleObserverRow> idleObserverRows=new List<IdleObserverRow>();
        }
        static Report report;
        static void Check(bool ok,string name){report.checks++;if(!ok)throw new InvalidOperationException(name);}
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o")};
            try {
                var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                var draws=new List<DrawSprite>();
                for(int a=0;a<ui.boards.powerManifests.Length;a++){
                    var meta=JsonUtility.FromJson<Manifest>(ui.boards.powerManifests[a].text);
                    foreach(var clip in meta.clips){report.powerClips++;foreach(float age in new[]{-.01f,0,(clip.count-.5f)/clip.fps,(clip.count+.5f)/clip.fps,2.7f*clip.count/clip.fps})draws.Add(new DrawSprite{bank="power",atlas=a,key=clip.name,age=age});}
                }
                foreach(var clip in ui.boards.obstacleClips){
                    var meta=JsonUtility.FromJson<ClipData>(clip.metadata.text);report.obstacleClips++;
                    foreach(float age in new[]{-.01f,0,(meta.frames.Length-.5f)/meta.fps,(meta.frames.Length+.5f)/meta.fps,2.7f*meta.frames.Length/meta.fps})draws.Add(new DrawSprite{bank="obstacle",key=clip.key,age=age});
                }
                var bank=new M46AtlasBank(ui.boards){SpriteLimit=65536};
                try {
                    foreach(var draw in draws){
                        bank.BeginFrame();bank.VerificationUseLegacyFrameLookup=false;var fast=bank.Get(draw);int created=bank.SpriteCreates;
                        bank.VerificationUseLegacyFrameLookup=true;var legacy=bank.Get(draw);bank.VerificationUseLegacyFrameLookup=false;
                        Check(ReferenceEquals(fast,legacy),"Exact sprite/hide identity "+draw.bank+"/"+draw.atlas+"/"+draw.key+"/"+draw.age);
                        Check(bank.SpriteCreates==created,"Legacy control does not recreate direct result");bank.EndFrame(false);
                    }
                    IdleObserverControls(ui,bank);
                    // Warm a deterministic subset in both directions before timing.
                    var measured=draws.Where(d=>d.bank=="power"&&new[]{2,3,4,12}.Contains(d.atlas)||d.bank=="obstacle"&&d.key.StartsWith("crate/",StringComparison.Ordinal)).ToArray();
                    for(int pass=0;pass<3;pass++)foreach(var d in measured)bank.Get(d);
                    for(int n=0;n<32;n++){
                        var timing=new Timing{iteration=n,lookups=measured.Length*16};
                        void Measure(bool legacy){bank.VerificationUseLegacyFrameLookup=legacy;long start=Stopwatch.GetTimestamp();for(int repeat=0;repeat<16;repeat++)foreach(var d in measured)bank.Get(d);double ms=(Stopwatch.GetTimestamp()-start)*1000.0/Stopwatch.Frequency;if(legacy)timing.legacyMs=ms;else timing.directMs=ms;}
                        if(n%2==0){Measure(true);Measure(false);}else{Measure(false);Measure(true);}report.timings.Add(timing);
                    }
                    bank.VerificationUseLegacyFrameLookup=false;report.lookups=draws.Count;
                    Check(bank.SpriteEvictions==0,"Paired identities use same resident working set");
                    var directFrames=(Array)typeof(M46AtlasBank).GetField("powerFrames",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(bank);
                    Check(directFrames.Cast<Array>().Any(a=>a.Cast<object>().Any(e=>e!=null)),"Direct slots populated by actual lookups");
                    bank.Dispose();Check(bank.SpriteCount==0&&bank.TextureCount==0,"Disposal clears owned sprites and textures");
                    Check(directFrames.Cast<Array>().All(a=>a.Cast<object>().All(e=>e==null)),"Disposal invalidates all populated frame slots");
                }finally{bank.Dispose();}
                var pressure=new M46AtlasBank(ui.boards){SpriteLimit=1};
                try {
                    var candidates=draws.Where(d=>d.bank=="power"&&d.atlas==2&&d.age==0).ToArray();Check(candidates.Length>=2,"Two pressure clips exist");
                    var first=candidates[0];pressure.BeginFrame();var old=pressure.Get(first);pressure.Get(first);
                    pressure.BeginFrame();var other=draws.First(d=>d.bank=="power"&&d.atlas==3&&d.age==0);pressure.Get(other);pressure.EndFrame(false);
                    Check(pressure.SpriteEvictions>0,"Pressure evicts an unused direct slot");int count=pressure.SpriteCreates;pressure.BeginFrame();var restored=pressure.Get(first);
                    Check(!ReferenceEquals(old,restored)&&pressure.SpriteCreates==count+1,"Evicted slot recreates rather than resurrecting old sprite");
                    pressure.VerificationUseLegacyFrameLookup=true;Check(ReferenceEquals(restored,pressure.Get(first)),"Recreated entry matches legacy lookup");
                    pressure.VerificationUseLegacyFrameLookup=false;pressure.VerificationSkipCachedLookup=true;Check(ReferenceEquals(restored,pressure.Get(first)),"Existing skip-lookup control preserves identity");
                }finally{pressure.Dispose();}
            }catch(Exception e){report.errors.Add(e.ToString());}
            report.status=report.errors.Count==0?"PASS_NATIVE_FRAME_LOOKUP75":"FAIL_NATIVE_FRAME_LOOKUP75";
            string folder=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY75_OUTPUT");if(string.IsNullOrEmpty(folder))folder=Path.GetFullPath("../Verification/Evidence/Gameplay75");folder=Path.Combine(folder,"Native");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"FrameLookup.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors.Count==0?0:1);
        }

        static void IdleObserverControls(GameplayUIAssets ui,M46AtlasBank bank) {
            foreach(var spec in new[]{new[]{4,9},new[]{5,10},new[]{21,6}}){
                int power=spec[0],atlas=spec[1];var meta=JsonUtility.FromJson<Manifest>(ui.boards.powerManifests[atlas].text);var clip=meta.clips.First(c=>c.name=="Idle");
                Check(clip.loop&&clip.count==48&&clip.fps==30,"Bound live Idle manifest has48frames at30fps "+atlas);
                foreach(int first in new[]{6,30}){
                    var row=new IdleObserverRow{power=power,atlas=atlas,firstFrame=first,middleFrame=first+6,lastFrame=first+12};
                    foreach(int index in new[]{row.firstFrame,row.middleFrame,row.lastFrame}){
                        var draw=new DrawSprite{bank="power",atlas=atlas,key="Idle",age=(index+.125f)/clip.fps};var sprite=bank.Get(draw);int logical=clip.start+Mathf.FloorToInt(draw.age*clip.fps)%clip.count;
                        row.samples.Add(new PowerupDeviceVerification.IdleSample{frame=row.samples.Count+1,clock=draw.age,drawAge=draw.age,key=draw.key,sprite=sprite.name,logicalFrame=logical,rect=sprite.rect});
                    }
                    row.endpointRectsEqual=row.samples[0].rect==row.samples[2].rect;
                    Check(row.endpointRectsEqual&&row.samples[0].logicalFrame!=row.samples[2].logicalFrame,"Actual Idle endpoint rect alias after12frames/.40s "+atlas+"/"+first);report.idleAliasControls++;
                    PowerupDeviceVerification.IdleObservation Observe(int fault){
                        var observed=new PowerupDeviceVerification.IdleObservation{power=power,atlas=atlas};
                        foreach(var sample in row.samples){var copy=new PowerupDeviceVerification.IdleSample{frame=sample.frame,clock=fault==1?row.samples[0].clock:sample.clock,drawAge=sample.drawAge,key=sample.key,sprite=sample.sprite,logicalFrame=fault==2?row.samples[0].logicalFrame:sample.logicalFrame,rect=fault==3?row.samples[0].rect:sample.rect};PowerupDeviceVerification.ObserveIdle(observed,copy);}return observed;
                    }
                    var valid=Observe(0);row.passedWithIntermediate=valid.passed;Check(valid.clockAdvanced&&valid.frameAdvanced&&valid.rectChanged&&valid.passed,"Intermediate native pose change overcomes endpoint alias "+atlas+"/"+first);report.idleObserverPositiveControls++;
                    row.frozenClockRejected=!Observe(1).passed;row.frozenFrameRejected=!Observe(2).passed;row.constantRectRejected=!Observe(3).passed;
                    Check(row.frozenClockRejected,"Idle observer rejects frozen clock "+atlas+"/"+first);Check(row.frozenFrameRejected,"Idle observer rejects frozen logical frame "+atlas+"/"+first);Check(row.constantRectRejected,"Idle observer rejects constant visible rect "+atlas+"/"+first);report.idleObserverNegativeControls+=3;report.idleObserverRows.Add(row);
                }
            }
        }
    }
}
#endif
