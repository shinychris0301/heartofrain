using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using HeartOfTheRain.M46;
using UnityEditor;
using UnityEngine;
using Motion=HeartOfTheRain.M46.Motion;

// Editor-only regression checks. These execute the real presentation code.
// Install with the R2 code patch, then run the menu in Unity.
namespace HeartOfTheRain.M69 {
    public static class M70PowerCreationCheck {
        [Serializable] sealed class Report {public bool passed;public string scope;public string[] checks,errors;}
        static void Check(bool pass,string message){if(!pass)throw new InvalidOperationException(message);}
        static void Near(float a,float b,string message){Check(Math.Abs(a-b)<.0002f,message+": "+a+" != "+b);}
        static Piece Power(int kind,int id=1,int x=3,int y=4){return new Piece{id=id,family="power",power=kind,x=x,y=y};}
        static BoardSnapshot Snap(params Piece[] pieces){return new BoardSnapshot{pieces=pieces,goals=new Goal[0],status="Playing",moves=20};}
        static BoardStep Birth(Piece p){var old=p.Copy();old.family="gem";old.power=-1;old.color=0;var s=new BoardStep{kind="match",duration=.28f,before=Snap(old),after=Snap(p)};s.created.Add(p.Copy());return s;}
        static DrawSprite Body(List<DrawSprite> d,int atlas){return d.Single(v=>v.bank=="power"&&v.atlas==atlas&&v.order==10);}
        static BoardPresentation New(){return new BoardPresentation{columns=9,rows=9};}
        [MenuItem("Heart of the Rain/M70/Validate power-up creation playback")]
        public static void Validate(){
            var checks=new List<string>();var errors=new List<string>();
            Action<string,Action> run=(name,test)=>{try{test();checks.Add(name);}catch(Exception e){errors.Add(name+": "+e.Message);}};
            foreach(var kind in new[]{21,4,5,11,16,7}){
                int k=kind;run("creation-to-idle / kind "+k,()=>{
                    var p=Power(k);var step=Birth(p);var v=New();v.Add(step,2);int atlas=BoardPresentation.PowerAtlas(k);
                    var early=v.Sample(step,step.before,2.1f,2);var draw=Body(early,atlas);
                    Check(draw.key==BoardPresentation.CreationClip(atlas),"Create clip was bypassed");Near(draw.age,.1f,"Birth clock");Near(draw.sx,BoardPresentation.PowerDisplayScale(atlas),"Double-scaled formation");
                    Check(early.Count(d=>d.key=="StarCreate")==1,"Missing or duplicate star accent");
                    float duration=BoardPresentation.CreationDuration(atlas);var done=Body(v.Sample(null,step.after,2+duration+.1f,0),atlas);
                    Check(done.key==BoardPresentation.Idle(atlas),"Idle not entered");Near(done.age,.1f,"Idle phase");
                    var same=Body(v.Sample(null,step.after,2+duration+.1f,0),atlas);Near(same.age,done.age,"Paused sampling advanced");
                });
            }
            run("creation survives match-to-gravity and follows position",()=>{
                var p=Power(21);var birth=Birth(p);var v=New();v.Add(birth,0);var fallen=p.Copy();fallen.y=2;
                var fall=new BoardStep{kind="gravity",duration=.62f,before=birth.after,after=Snap(fallen)};
                fall.motion.Add(new Motion{id=p.id,fromX=3,toX=3,fromY=4,toY=2});v.Add(fall,.28f);
                var draws=v.Sample(fall,birth.after,.31f,.28f);var body=Body(draws,6);var star=draws.Single(d=>d.key=="StarCreate");
                Check(body.key=="Create","Creation cut at end of match");Near(body.age,.31f,"Creation restarted on gravity");Check(body.y<4,"Body did not fall");Near(star.y,body.y,"Star remained at old cell");
                var tail=Body(v.Sample(fall,birth.after,.59f,.28f),6);Check(tail.key=="Create","Creation tail lost");
            });
            run("idle phase survives history pruning",()=>{
                var p=Power(21);var s=Birth(p);var v=New();v.Add(s,0);v.Sample(s,s.before,.1f,0);v.PruneHistory(31);
                Check(v.history.Count==0,"Fixture did not prune");Near(Body(v.Sample(null,s.after,31,0),6).age,30.4f,"Idle phase reset");
            });
            run("consumed power has no leftover birth body or stars",()=>{
                var p=Power(21);var birth=Birth(p);var v=New();v.Add(birth,0);
                var remove=new BoardStep{kind="power",duration=1,before=birth.after,after=Snap()};remove.removed.Add(new Removed{piece=p,time=0,cause="source"});v.Add(remove,.2f);
                var d=v.Sample(remove,remove.before,.25f,.2f);Check(!d.Any(x=>x.atlas==6||x.key=="StarCreate"),"Birth ghost after consumption");
            });
            run("simultaneous births remain independent",()=>{
                var p=Power(21);var q=Power(4,2,5,4);var s=Birth(p);s.after=Snap(p,q);s.created.Add(q);var v=New();v.Add(s,0);
                var d=v.Sample(s,s.before,.15f,0);Check(Body(d,6).key=="Create"&&Body(d,9).key=="Create","One birth replaced another");Check(d.Count(x=>x.key=="StarCreate")==2,"Incorrect birth accents");
            });
            run("existing items do not replay creation",()=>{
                var v=New();var d=v.Sample(null,Snap(Power(7)),8,0);Check(Body(d,19).key=="OR_Idle"&&!d.Any(x=>x.key=="StarCreate"),"Idle power reborn");
            });
            run("starting grant uses explicit reveal clock",()=>{
                var p=Power(16);var v=New();v.Sample(null,Snap(p),10,0);v.RegisterPowerCreation(p,10);
                var d=Body(v.Sample(null,Snap(p),10.1f,0),40);Check(d.key=="GS_Create","Starting item not formed");Near(d.age,.1f,"Hidden modal time consumed birth");
            });
            run("converted power forms before original charge and activation",()=>{
                var v=New();var plan=new ReviewPlan{powers=new[]{new ReviewPower{atlas=6,x=3,y=4,begin=1,end=2,charge=.2f}},effects=new ReviewFx[0],beams=new ReviewBeam[0],tiles=new ReviewTile[0]};
                var s=new BoardStep{kind="power",duration=2,before=Snap(),after=Snap(),powerPlan=plan};v.Add(s,0);
                Func<float,DrawSprite> at=t=>v.Sample(s,s.before,t,0).Single(x=>x.order==20&&x.atlas==6);
                Check(at(1.1f).key=="Create","Converted body bypassed creation");Near(at(1.1f).age,.1f,"Converted clock");Check(at(1.7f).key=="Idle","Converted idle missing");Check(at(1.9f).key=="Charge","Charge interrupted");Check(!v.Sample(s,s.before,2,0).Any(x=>x.order==20),"Activation delayed");
            });
            run("short conversion window preserves action timing",()=>{
                string key;float age;BoardPresentation.GeneratedBodyPhase(9,.03f,.06f,out key,out age);Check(key=="Create","Short formation skipped");Near(age,.3f,"Creation not fitted to window");
                BoardPresentation.GeneratedBodyPhase(9,.06f,.06f,out key,out age);Check(key=="Idle","Creation overran window");
            });
            run("clip names and durations match imported manifests",()=>{
                string root="Assets/HeartOfTheRain/";
                string[] paths={"Chapter01M05/Data/Bomb.json","Chapter01M04/Data/Rocket_Horizontal.json","Chapter01M04/Data/Rocket_Vertical.json","Chapter01M07/Data/RainSeekerBody.json","Chapter01M07/Data/GoldenSeekerBody.json","Chapter01M07/Data/RainbowOrbBody.json"};
                int[] atlases={6,9,10,29,40,19};
                for(int i=0;i<paths.Length;i++){
                    var asset=AssetDatabase.LoadAssetAtPath<TextAsset>(root+paths[i]);Check(asset!=null,"Missing manifest "+paths[i]);
                    var m=JsonUtility.FromJson<HeartOfTheRain.M05.SpriteManifest>(asset.text);int atlas=atlases[i];var clip=m.clips.Single(c=>c.name==BoardPresentation.CreationClip(atlas));
                    Near(clip.count/(float)clip.fps,BoardPresentation.CreationDuration(atlas),"Creation duration");Check(!clip.loop,"Creation must play once");
                }
            });
            var report=new Report{passed=errors.Count==0,scope="Unity Editor sampler/metadata checks only; visual/device checks are separate",checks=checks.ToArray(),errors=errors.ToArray()};
            Directory.CreateDirectory("Temp");File.WriteAllText("Temp/M70R2_CreationChecks.json",JsonUtility.ToJson(report,true));
            if(report.passed)Debug.Log("M70 R2 creation checks passed. Review actual gameplay and device playback separately.");
            else Debug.LogError("M70 R2 creation checks failed:\n"+string.Join("\n",report.errors));
        }
    }
}
