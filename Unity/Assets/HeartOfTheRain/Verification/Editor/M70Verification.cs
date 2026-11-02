#if UNITY_EDITOR
using System;
using System.IO;
using System.Reflection;
using System.Collections;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M05;

namespace HeartOfTheRain.Verification
{
    public static class M70Verification
    {
        [Serializable] class Entry {public string name,texture,manifest,resourceKey;public int atlasIndex;}
        [Serializable] class Contract {public Entry[] entries;}
        [Serializable] class Report {public string status,utc,scope="Native Unity imports, live binding, all supplied frame rectangles, replay parity and GPU renders. Before images reconstruct previous assets at equal cell size; they are not preceding APK screenshots.";public int checks,frames;public List<string> failures=new List<string>();}
        static Report report;
        static void Check(bool value,string name){report.checks++;if(!value)report.failures.Add(name);}
        public static void Run()
        {
            string output=Path.GetFullPath("../Verification/Evidence/M70");Directory.CreateDirectory(output);
            report=new Report{utc=DateTime.UtcNow.ToString("o")};M46AtlasBank bank=null;GameObject root=null;Material material=null;RenderTexture target=null;
            var owned=new List<UnityEngine.Object>();
            try{
                EditorApplication.ExecuteMenuItem("Heart of the Rain/M70/Reimport power-up clarity assets");
                HeartOfTheRain.M69.M70PowerupAssetCheck.Validate();Check(File.ReadAllText("Temp/M70_Powerup_Validation.json").Contains("\"passed\": true"),"Supplied installation checker");
                File.Copy("Temp/M70_Powerup_Validation.json",Path.Combine(output,"Package_Native_Validation.json"),true);
                var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                var first=AssetDatabase.LoadAssetAtPath<HeartOfTheRain.App.FirstStart.FirstStartAssets>("Assets/HeartOfTheRain/App/FirstStart/FirstStartAssets.asset");
                Check(first&&first.Gameplay==ui,"First-start to active gameplay asset chain");
                // The connected Play Mode smoke and Android suite additionally trace the launched page's binding.
                Check(ui&&ui.boards&&AssetDatabase.GetAssetPath(ui.boards)=="Assets/HeartOfTheRain/M48/M48Chapter01Boards.asset","Live gameplay board binding");
                var contract=JsonUtility.FromJson<Contract>(File.ReadAllText("Assets/HeartOfTheRain/M69/Data/M70_PowerupContract.json"));
                bank=new M46AtlasBank(ui.boards);var oldTextures=new Dictionary<int,Texture2D>();var oldManifests=new Dictionary<int,SpriteManifest>();
                foreach(var e in contract.entries){
                    Check(AssetDatabase.GetAssetPath(ui.boards.powerManifests[e.atlasIndex])==e.manifest&&ui.boards.powerAtlases[e.atlasIndex]==null&&ui.boards.powerResources[e.atlasIndex]==e.resourceKey,"Actual bank streamed binding "+e.name);
                    var m=JsonUtility.FromJson<SpriteManifest>(ui.boards.powerManifests[e.atlasIndex].text);
                    string prior=Path.Combine("../.verification-cache/M70/Before",e.manifest);var old=JsonUtility.FromJson<SpriteManifest>(File.ReadAllText(prior));oldManifests[e.atlasIndex]=old;
                    var tex=new Texture2D(2,2,TextureFormat.RGBA32,false);tex.LoadImage(File.ReadAllBytes(Path.Combine("../.verification-cache/M70/Before",e.texture)));tex.filterMode=FilterMode.Bilinear;owned.Add(tex);oldTextures[e.atlasIndex]=tex;
                        var go=new GameObject("Replay frame parity");owned.Add(go);var replay=go.AddComponent<RenderedSpritePlayer>();replay.playOnEnable=false;replay.atlas=AssetDatabase.LoadAssetAtPath<Texture2D>(e.texture);replay.manifest=ui.boards.powerManifests[e.atlasIndex];replay.Initialize();
                    foreach(var c in m.clips){
                        var before=old.clips.First(x=>x.name==c.name);
                        foreach(float aspect in new[]{.5f,1f,2f}){
                            float half=HeartOfTheRain.M07.PowerUpPlaybackGallery.ClipHalfHeight(m,Array.IndexOf(m.clips,c),aspect);
                            for(int frame=c.start;frame<c.start+c.count;frame++)Check(m.frames[frame].height/m.pixelsPerUnit<2*half&&m.frames[frame].width/m.pixelsPerUnit<2*half*aspect,"Gallery contains every pose "+e.name+"/"+c.name+"/"+frame+" at "+aspect);
                        }
                        if(c.name!="Idle")Check(c.count==before.count&&c.fps==before.fps&&c.loop==before.loop&&c.endBehavior==before.endBehavior,"Preserved non-idle schedule "+e.name+"/"+c.name);
                        if(c.name=="Idle"&&new[]{6,9,10}.Contains(e.atlasIndex))Check(c.count==48&&c.fps==30&&c.loop,"48-frame loop "+e.name);
                        for(int n=0;n<c.count;n++){
                            float age=(n+.01f)/c.fps;var sprite=bank.Get(new DrawSprite{bank="power",atlas=e.atlasIndex,key=c.name,age=age});var f=m.frames[c.start+n];
                            replay.Sample(c.name,age);Check(sprite&&sprite.rect==new Rect(f.x,f.y,f.width,f.height)&&Mathf.Abs(sprite.pixelsPerUnit-m.pixelsPerUnit)<.001f,"Live JSON rect/PPU "+e.name+"/"+c.name+"/"+n);
                            Check(replay.Renderer.sprite.rect==sprite.rect&&replay.Renderer.sprite.pixelsPerUnit==sprite.pixelsPerUnit,"Replay parity "+e.name+"/"+c.name+"/"+n);report.frames++;
                        }
                        if(c.loop)Check(bank.Get(new DrawSprite{bank="power",atlas=e.atlasIndex,key=c.name,age=0}).rect==bank.Get(new DrawSprite{bank="power",atlas=e.atlasIndex,key=c.name,age=c.Duration+.001f}).rect,"Loop wraps "+e.name+"/"+c.name);
                    }
                        // The runtime player uses deferred Destroy. Dispose its temporary sprites
                        // explicitly before its OnDestroy when exercising it in Edit Mode.
                        var shared=typeof(RenderedSpritePlayer).GetField("shared",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(replay);
                        foreach(var frame in (Sprite[])shared.GetType().GetField("sprites").GetValue(shared))if(frame)UnityEngine.Object.DestroyImmediate(frame);
                        UnityEngine.Object.DestroyImmediate(go);owned.Remove(go);
                }
                root=new GameObject("M70 native GPU fixture");root.transform.position=new Vector3(40000,0,0);var camGo=new GameObject("Camera");camGo.transform.SetParent(root.transform,false);var camera=camGo.AddComponent<Camera>();camera.orthographic=true;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.055f,.09f,.14f);target=new RenderTexture(1024,1024,24);camera.targetTexture=target;material=new Material(ui.bodyShader);
                var renderers=new List<GameObject>();
                void Capture(BoardPresentation p,BoardSnapshot snapshot,float age,bool previous,string filename){
                    foreach(var o in renderers)UnityEngine.Object.DestroyImmediate(o);renderers.Clear();
                    foreach(var d in p.Sample(null,snapshot,age,0)){
                        Sprite sprite;float scale=1;
                        if(previous&&d.bank=="power"&&oldManifests.ContainsKey(d.atlas)){
                            var m=oldManifests[d.atlas];var c=m.clips.First(x=>x.name==d.key);int n=Mathf.FloorToInt(age*c.fps);n=c.loop?n%c.count:Mathf.Min(n,c.count-1);var f=m.frames[c.start+n];sprite=Sprite.Create(oldTextures[d.atlas],new Rect(f.x,f.y,f.width,f.height),new Vector2(.5f,.5f),m.pixelsPerUnit);owned.Add(sprite);scale=1/BoardPresentation.PowerDisplayScale(d.atlas);
                        }else sprite=bank.Get(d);
                        if(!sprite)continue;var o=new GameObject(d.key);o.transform.SetParent(root.transform,false);o.transform.localPosition=new Vector3(d.x,d.y,0);o.transform.localScale=new Vector3(d.sx*scale,d.sy*scale,1);var sr=o.AddComponent<SpriteRenderer>();sr.sprite=sprite;sr.sharedMaterial=material;sr.sortingOrder=d.order;renderers.Add(o);
                    }
                    camera.Render();RenderTexture.active=target;var pixels=new Texture2D(1024,1024,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,1024,1024),0,0);pixels.Apply();Check(pixels.GetPixels32().Count(c=>c.r>50||c.g>50||c.b>80)>1000,"GPU visible "+filename);File.WriteAllBytes(Path.Combine(output,filename),pixels.EncodeToPNG());UnityEngine.Object.DestroyImmediate(pixels);
                }
                foreach(var shape in new[]{new[]{9,9},new[]{9,11},new[]{11,11}}){
                    var level=ui.boards.levels.Select(t=>JsonUtility.FromJson<LevelData>(t.text)).First(l=>l.columns==shape[0]&&l.rows==shape[1]);var board=new BoardModel(level);var cells=board.Pieces.Values.Where(x=>x.family=="gem").OrderByDescending(x=>x.y).ThenBy(x=>x.x).Take(6).ToArray();var powers=new[]{4,5,21,11,16,7};
                    for(int n=0;n<6;n++)Check(board.InjectReviewPower(cells[n].x,cells[n].y,powers[n]),"Fixture placement "+powers[n]);
                    var snapshot=board.Snapshot();var presentation=new BoardPresentation{columns=level.columns,rows=level.rows};camera.orthographicSize=level.rows*.5f+.6f;camera.transform.localPosition=new Vector3((level.columns-1)*.5f,(level.rows-1)*.5f,-10);
                    Capture(presentation,snapshot,0,true,shape[0]+"x"+shape[1]+"_Before.png");Capture(presentation,snapshot,0,false,shape[0]+"x"+shape[1]+"_After_A.png");Capture(presentation,snapshot,.4f,false,shape[0]+"x"+shape[1]+"_After_B.png");
                    var a=presentation.Sample(null,snapshot,0,0);var b=presentation.Sample(null,snapshot,.4f,0);
                    foreach(var d in a.Where(d=>d.bank=="power")){
                        Check(Mathf.Abs(d.sx-BoardPresentation.PowerDisplayScale(d.atlas))<.0001f,"Single stationary scale "+d.atlas);
                        var next=b.First(x=>x.pieceId==d.pieceId);if(new[]{6,9,10}.Contains(d.atlas))Check(bank.Get(d).rect!=bank.Get(next).rect,"Idle body pose changes "+d.atlas);
                    }
                }
                var orb=JsonUtility.FromJson<SpriteManifest>(ui.boards.powerManifests[19].text);
                int orbIdle=Array.FindIndex(orb.clips,c=>c.name=="OR_Idle");
                var orbSnapshot=new BoardSnapshot{pieces=new[]{new Piece{id=1,family="power",power=7,x=0,y=0}},goals=new Goal[0]};
                var orbView=new BoardPresentation{columns=1,rows=1};camera.transform.localPosition=new Vector3(0,0,-10);
                float oldHalf=.62f*orb.frames[0].width/orb.pixelsPerUnit;
                camera.orthographicSize=oldHalf;Capture(orbView,orbSnapshot,.2f,false,"Gallery_Orb_Control.png");
                camera.orthographicSize=HeartOfTheRain.M07.PowerUpPlaybackGallery.ClipHalfHeight(orb,orbIdle,camera.aspect);
                Check(camera.orthographicSize>oldHalf*10,"Gallery crop regression witness: tiny Create frame cannot set Idle camera");
                Capture(orbView,orbSnapshot,.2f,false,"Gallery_Orb_Corrected.png");
                Check(report.frames==586,"All 586 supplied frames sampled");
            }catch(Exception e){report.failures.Add(e.ToString());}
            finally{RenderTexture.active=null;if(root)UnityEngine.Object.DestroyImmediate(root);if(target)UnityEngine.Object.DestroyImmediate(target);if(material)UnityEngine.Object.DestroyImmediate(material);if(bank!=null){var cache=(IDictionary)typeof(M46AtlasBank).GetField("sprites",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(bank);foreach(var entry in cache.Values){var sprite=(Sprite)entry.GetType().GetField("sprite").GetValue(entry);if(sprite)UnityEngine.Object.DestroyImmediate(sprite);}cache.Clear();bank.Dispose();}foreach(var o in owned)if(o)UnityEngine.Object.DestroyImmediate(o);}
            report.status=report.failures.Count==0?"PASS_NATIVE_M70_CHECKS":"FAIL_NATIVE_M70_CHECKS";File.WriteAllText(Path.Combine(output,"Native_Checks.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.failures.Count==0?0:1);
        }
    }
}
#endif
