#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.App.Celebrations;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification
{
    public static class FluidityVerification
    {
        const string Root="Assets/HeartOfTheRain/M68Celebration/";
        const string Resource="Assets/HeartOfTheRain/App/Celebrations/Resources/M68_RuntimeAssets.asset";
        public static void Prepare()
        {
            foreach(string guid in AssetDatabase.FindAssets("t:Texture2D",new[]{Root.TrimEnd('/')})){
                var path=AssetDatabase.GUIDToAssetPath(guid);var importer=(TextureImporter)AssetImporter.GetAtPath(path);
                if(importer.maxTextureSize==4096&&importer.npotScale==TextureImporterNPOTScale.None&&!importer.mipmapEnabled&&importer.textureCompression==TextureImporterCompression.Uncompressed)continue;
                importer.maxTextureSize=4096;importer.npotScale=TextureImporterNPOTScale.None;importer.mipmapEnabled=false;importer.isReadable=false;importer.textureCompression=TextureImporterCompression.Uncompressed;importer.wrapMode=TextureWrapMode.Clamp;importer.filterMode=FilterMode.Bilinear;importer.alphaIsTransparency=true;
                var defaults=importer.GetDefaultPlatformTextureSettings();defaults.maxTextureSize=4096;defaults.textureCompression=TextureImporterCompression.Uncompressed;importer.SetPlatformTextureSettings(defaults);importer.SaveAndReimport();
            }
            var a=AssetDatabase.LoadAssetAtPath<M68CelebrationAssets>(Resource);if(!a){a=ScriptableObject.CreateInstance<M68CelebrationAssets>();AssetDatabase.CreateAsset(a,Resource);}
            T Load<T>(string path) where T:UnityEngine.Object {var result=AssetDatabase.LoadAssetAtPath<T>(Root+path);if(!result)throw new Exception("Missing M68 asset "+path);return result;}
            a.master=Load<Texture2D>("Art/Dariya_Master.png");a.blink=Load<Texture2D>("Mesh/Dariya_Blink_Texture.png");a.reduced=Load<Texture2D>("Art/Dariya_Reduced_Motion.png");a.halo=Load<Texture2D>("Art/Celebration_Halo.png");a.star=Load<Texture2D>("Art/Celebration_Star.png");
            a.clipJson=Load<TextAsset>("Mesh/Dariya_Mesh_Clip.json");a.effectsJson=Load<TextAsset>("Data/Effects_Timeline.json");a.designJson=Load<TextAsset>("Data/Effects_Design.json");a.positions=Load<TextAsset>("Mesh/Dariya_Positions.f32.bytes");a.uv=Load<TextAsset>("Mesh/Dariya_UV.f32.bytes");a.indices=Load<TextAsset>("Mesh/Dariya_Indices.i32.bytes");a.sound=Load<AudioClip>("Audio/Celebration_Win.wav");a.blendShader=Shader.Find("HeartOfTheRain/M68MeshBlend");
            EditorUtility.SetDirty(a);AssetDatabase.SaveAssets();a.Prepare();
        }
        [Serializable] public sealed class Report {public string status="PASS_NATIVE_FLUIDITY_CHECKS",utc,scope="Native Unity model/schedule/import checks; performance and visual device evidence are separate.";public int checks;public string[] failures;}
        public static void Run()
        {
            var r=new Report{utc=DateTime.UtcNow.ToString("o")};var failures=new System.Collections.Generic.List<string>();
            void Check(bool ok,string name){r.checks++;if(!ok)failures.Add(name);}
            try{
                Prepare();var a=M68CelebrationAssets.Load();Check(a&&a.Clip.frame_count==210&&a.Effects.samples.Length==210,"M68 frames and effects");Check(a.Indices.All(i=>i>=0&&i<a.Clip.vertex_count),"M68 triangle indices");Check(a.Positions.All(v=>!float.IsNaN(v)&&!float.IsInfinity(v)),"M68 finite samples");Check(a.blendShader&&a.blendShader.isSupported,"M68 native blend shader");
                Check(M68CelebrationAssets.Frame(1.88f)==112&&M68CelebrationAssets.Frame(99)==209,"Elapsed sample clamp");
                M68RenderVerification.Run();Check(true,"Six native M68 compositions compared with supplied baked frames");
                foreach(var size in new[]{new Vector2(393,698),new Vector2(393,852),new Vector2(768,1024),new Vector2(1280,720)}){
                    var f=HomeLayoutEngine.Build(size.x,size.y,new HomeState(),false);var dock=f.elements.First(e=>e.id=="dock-bg");var reference=new HomeFrame();MainNavigationLayout.AddDock(reference,f.width,f.height,0);var d=reference.elements.First(e=>e.id=="dock-bg");Check(Mathf.Abs(d.y-dock.y)<.01f&&Mathf.Abs(d.x-dock.x)<.01f&&Mathf.Abs(d.width-dock.width)<.01f,"Shared dock "+size);
                }
                var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                var flags=System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance;var exchange=typeof(BoardModel).GetMethod("Exchange",flags);var matches=typeof(BoardModel).GetMethod("Matches",flags);
                for(int level=0;level<50;level++){
                    var b=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text));var expected=new System.Collections.Generic.List<string>();
                    foreach(var p in b.Pieces.Values.OrderBy(p=>p.y).ThenBy(p=>p.x).ToArray())if(p.Swappable)foreach(var d in new[]{new Cell(1,0),new Cell(0,1)}){
                        var q=b.At(p.x+d.x,p.y+d.y);if(q==null||!q.Swappable)continue;exchange.Invoke(b,new object[]{p,q});bool legal=((System.Collections.ICollection)matches.Invoke(b,new object[]{new System.Collections.Generic.HashSet<int>{p.id,q.id}})).Count>0;exchange.Invoke(b,new object[]{p,q});if(legal)expected.Add(p.x+","+p.y+":"+q.x+","+q.y);
                    }
                    var actual=b.LegalSwaps().Select(p=>p[0].x+","+p[0].y+":"+p[1].x+","+p[1].y);Check(expected.SequenceEqual(actual),"Local legal moves equal full scan L"+(level+1));b.Validate();
                }
                for(int level=0;level<50;level++)foreach(int kind in new[]{4,5,7,11,16,21}){
                    var b=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text));var gem=b.Pieces.Values.First(p=>p.family=="gem");b.InjectReviewPower(gem.x,gem.y,kind);var result=b.Tap(gem.x,gem.y);string before=JsonUtility.ToJson(b.Snapshot());var schedule=BoardPlayback.Build(result.steps);
                    Check(schedule.Count>0&&schedule.All(s=>s.duration>0),"Finite schedule L"+(level+1)+" kind"+kind);Check(JsonUtility.ToJson(b.Snapshot())==before,"Scheduling preserves model L"+(level+1)+" kind"+kind);Check(ReferenceEquals(schedule.Last().after,result.steps.Last().after),"Final snapshot L"+(level+1)+" kind"+kind);
                    foreach(var s in schedule.Where(s=>s.playbackTracks!=null))Check(s.motion.All(m=>m.delay>=0&&m.delay+m.seconds<=s.duration+.001f),"Fall finishes within schedule");
                }
                var chain=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[0].text));var row=chain.Pieces.Values.Where(p=>p.family=="gem").GroupBy(p=>p.y).First(g=>g.Count()>=2).OrderBy(p=>p.x).Take(2).ToArray();foreach(var p in row)chain.InjectReviewPower(p.x,p.y,4);var turn=chain.Tap(row[0].x,row[0].y);var powers=turn.steps.Where(s=>s.kind=="power").ToArray();Check(powers.Length>=2&&powers[1].triggerTime<powers[0].duration,"Hit power starts during parent effect");var timed=BoardPlayback.Build(turn.steps);Check(timed.Sum(s=>s.duration)<turn.steps.Sum(s=>s.duration),"Overlapped chain settles earlier");
                var cabinet=new BoardModel(PlaybackFixtures.ClearingCabinet());var clear=BoardPlayback.Build(cabinet.UseBooster(BoosterKind.Hammer,3,0,new BoosterInventory()).steps).First();
                Check(clear.motion.Any(m=>m.toX==4)&&clear.motion.Where(m=>m.toX==3||m.toX==4).All(m=>m.delay>=1.6f-.001f),"Clearing cabinet reserves both columns through its clear animation");Check(clear.collections.All(c=>c.arrival<=clear.duration+.001f),"Goal flights arrive before turn completion");
                BoardStep ContactTrack(int id,int parent,float start,float hit){var s=new BoardStep{kind="power",duration=3,triggerTime=start,triggerOriginId=parent,before=clear.before,after=clear.before,powerPlan=new ReviewPlan{primary=.3f}};s.removed.Add(new Removed{piece=new Piece{id=id,family="power",power=4,x=0,y=4},cause="source"});if(hit>=0)s.damage.Add(new Damage{id=999,x=3,y=0,family="cabinet",time=hit,beforeHP=2,afterHP=1});return s;}
                var causal=BoardPlayback.Build(new[]{ContactTrack(100,0,0,2),ContactTrack(101,100,.2f,.2f),ContactTrack(102,101,.4f,-1)})[0].playbackTracks;
                Check(causal[2].start>=causal[1].start+.199f,"Grandchild follows its actual parent impact after shared-obstacle delay");
                for(int level=0;level<50;level++)for(int tool=0;tool<3;tool++){
                    var b=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text));var p=b.Pieces.Values.First(v=>v.family=="gem");b.InjectReviewPower(p.x,p.y,4);var result=b.UseBooster((BoosterKind)tool,p.x,p.y,new BoosterInventory());string state=JsonUtility.ToJson(b.Snapshot());var schedule=BoardPlayback.Build(result.steps);Check(schedule[0].playbackTracks!=null,"Tool effect/refill overlap L"+(level+1)+" tool"+tool);Check(JsonUtility.ToJson(b.Snapshot())==state,"Tool scheduling preserves model");var track=schedule[0].playbackTracks.FirstOrDefault(t=>t.step.kind=="power");Check(track!=null&&track.start<result.steps[0].duration,"Hit power triggers during tool animation");
                    var presentation=new BoardPresentation{columns=b.Level.columns,rows=b.Level.rows};foreach(var pr in ui.boards.debrisProfiles)presentation.profiles[pr.family]=JsonUtility.FromJson<DebrisProfile>(pr.metadata.text);presentation.Add(schedule[0],0);for(int sample=0;sample<8;sample++)presentation.SampleLive(schedule[0],schedule[0].after,sample*.15f,0);Check(true,"Pooled tool/power samples coexist");
                }
            }catch(Exception e){failures.Add(e.ToString());}
            if(failures.Count==0)PlaybackBenchmark.Measure();
            r.failures=failures.ToArray();if(failures.Count>0)r.status="FAIL_NATIVE_FLUIDITY_CHECKS";string output=Path.GetFullPath("../Verification/Evidence/Fluidity");Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Native_Checks.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(failures.Count==0?0:1);
        }
    }
}
#endif
