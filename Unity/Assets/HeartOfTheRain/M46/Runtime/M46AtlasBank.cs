using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Profiling;
using Manifest = HeartOfTheRain.M05.SpriteManifest;
namespace HeartOfTheRain.M46 {
    // M48: references remain compatible with the earlier review scenes.
    // The main gameplay binding uses resource paths so it does not load every atlas at startup.
    public sealed class M46AtlasBank : IDisposable {
        sealed class TextureEntry { public Texture2D texture; public float used; public long bytes; }
        sealed class SpriteEntry { public Sprite sprite; public int frame; public bool pinned; }
        readonly M46Assets assets;
        readonly Dictionary<string,SpriteEntry> sprites=new Dictionary<string,SpriteEntry>();
        readonly Dictionary<string,TextureEntry> textures=new Dictionary<string,TextureEntry>();
        readonly HashSet<Texture2D> pinnedTextures=new HashSet<Texture2D>();
        readonly Dictionary<string,BodyAsset> bodies;
        readonly Dictionary<string,ClipAsset> clips;
        readonly Dictionary<string,ClipData> clipData;
        readonly Manifest[] powers;
        int frame;
        public int SpriteLimit=768;
        public long TextureBudget=128L*1024*1024;
        public int SpriteCount=>sprites.Count;
        public int TextureCount=>textures.Count;
        public long TextureBytes=>textures.Values.Sum(t=>t.bytes);
        public int SynchronousLoads { get; private set; }
        public string LoadError { get; private set; }
        public M46AtlasBank(M46Assets a) {
            assets=a;
            powers=a.powerManifests.Select(m=>JsonUtility.FromJson<Manifest>(m.text)).ToArray();
            bodies=a.bodies.ToDictionary(b=>b.key);
            clips=a.obstacleClips.ToDictionary(c=>c.key);
            clipData=a.obstacleClips.ToDictionary(c=>c.key,c=>JsonUtility.FromJson<ClipData>(c.metadata.text));
        }
        static string PathAt(string[] paths,int i)=>paths!=null&&i<paths.Length?paths[i]:null;
        Texture2D Texture(Texture2D direct,string path) {
            if(direct!=null)return direct;
            if(string.IsNullOrEmpty(path))throw new InvalidOperationException("Texture reference and resource path are both missing");
            TextureEntry entry;
            if(!textures.TryGetValue(path,out entry)) {
                var texture=Resources.Load<Texture2D>(path);
                if(texture==null)throw new InvalidOperationException("Missing texture resource: "+path);
                Store(path,texture);entry=textures[path];SynchronousLoads++;
            }
            entry.used=Time.unscaledTime;return entry.texture;
        }
        void Store(string path,Texture2D texture) {
            textures[path]=new TextureEntry{texture=texture,used=Time.unscaledTime,bytes=Profiler.GetRuntimeMemorySizeLong(texture)};
        }
        public IEnumerator Prewarm(IEnumerable<string> paths) {
            LoadError=null;
            foreach(var path in paths.Where(p=>!string.IsNullOrEmpty(p)).Distinct()) {
                if(textures.ContainsKey(path)){textures[path].used=Time.unscaledTime;continue;}
                var request=Resources.LoadAsync<Texture2D>(path);yield return request;
                var texture=request.asset as Texture2D;
                if(texture==null){LoadError="Missing texture resource: "+path;Debug.LogError(LoadError);yield break;}
                Store(path,texture);
            }
        }
        public HashSet<string> RequiredResources(IEnumerable<BoardStep> steps) {
            var needed=new HashSet<string>();
            Action<int> power=i=>{var p=PathAt(assets.powerResources,i);if(!string.IsNullOrEmpty(p))needed.Add(p);};
            Action<string> body=key=>{BodyAsset b;if(bodies.TryGetValue(key,out b)&&!string.IsNullOrEmpty(b.resource))needed.Add(b.resource);};
            Action<string> family=f=>{foreach(var c in clips.Values.Where(c=>c.key.StartsWith(f+"/",StringComparison.Ordinal)))foreach(var p in c.pageResources??new string[0])if(!string.IsNullOrEmpty(p))needed.Add(p);};
            var plan=HeartOfTheRain.M48.EffectResources.ForSteps(steps);
            foreach(var p in plan.powers)power(p);foreach(var b in plan.bodies)body(b);foreach(var f in plan.obstacleFamilies)family(f);
            return needed;
        }
        public void BeginFrame(){frame++;}
        Sprite Frame(string key,Texture2D texture,Rect rect,float ppu,bool pinned=false) {
            SpriteEntry e;
            if(!sprites.TryGetValue(key,out e)) {
                if(rect.x<0||rect.y<0||rect.xMax>texture.width||rect.yMax>texture.height)
                    throw new InvalidOperationException("Atlas was resized during import: "+key);
                var s=Sprite.Create(texture,rect,new Vector2(.5f,.5f),ppu,0,SpriteMeshType.FullRect);s.name=key;
                e=new SpriteEntry{sprite=s};sprites.Add(key,e);
            }
            e.frame=frame;e.pinned|=pinned;if(pinned)pinnedTextures.Add(texture);return e.sprite;
        }
        public Sprite Whole(string key,Texture2D texture,float cells,bool pinned=false)=>Frame(key,texture,new Rect(0,0,texture.width,texture.height),texture.width/cells,pinned);
        public Sprite BoardSurface(int i){var t=Texture(assets.surfaces[i],PathAt(assets.surfaceResources,i));return Whole("surface/"+i,t,t.width/64f,true);}
        public Sprite BoardMask(int i){var t=Texture(assets.masks[i],PathAt(assets.maskResources,i));return Whole("mask/"+i,t,t.width/64f,true);}
        public Sprite Get(DrawSprite d) {
            if(d.bank=="body"){var b=bodies[d.key];return Whole(d.key,Texture(b.texture,b.resource),b.canvasCells);}
            if(d.bank=="power") {
                var m=powers[d.atlas];var c=Array.Find(m.clips,q=>q.name==d.key);
                if(c==null)throw new InvalidOperationException("Missing clip "+d.atlas+"/"+d.key);
                int n=Mathf.Max(0,Mathf.FloorToInt(d.age*c.fps));
                if(c.loop)n%=c.count;else if(n>=c.count){if(c.endBehavior=="hide")return null;n=c.count-1;}
                n+=c.start;var f=m.frames[n];var t=Texture(assets.powerAtlases[d.atlas],PathAt(assets.powerResources,d.atlas));
                return Frame("p/"+d.atlas+"/"+n,t,new Rect(f.x,f.y,f.width,f.height),m.pixelsPerUnit);
            }
            var meta=clipData[d.key];int index=Mathf.Max(0,Mathf.FloorToInt(d.age*meta.fps));
            if(meta.loop)index%=meta.frames.Length;else if(index>=meta.frames.Length){if(!meta.holdLast)return null;index=meta.frames.Length-1;}
            var cf=meta.frames[index];var clip=clips[d.key];var texture=Texture(clip.pages[cf.page],PathAt(clip.pageResources,cf.page));
            return Frame("o/"+d.key+"/"+index,texture,new Rect(cf.x,cf.y,cf.w,cf.h),meta.pixelsPerUnit);
        }
        public void EndFrame(bool mayEvictTextures) {
            int remove=Math.Max(0,sprites.Count-SpriteLimit);
            foreach(var key in sprites.Where(p=>!p.Value.pinned&&p.Value.frame!=frame).OrderBy(p=>p.Value.frame).Take(remove).Select(p=>p.Key).ToArray())RemoveSprite(key);
            if(!mayEvictTextures||TextureBytes<=TextureBudget)return;
            foreach(var pair in textures.OrderBy(p=>p.Value.used).ToArray()) {
                if(TextureBytes<=TextureBudget)break;
                var t=pair.Value.texture;
                if(pinnedTextures.Contains(t)||Time.unscaledTime-pair.Value.used<2||sprites.Values.Any(e=>e.sprite.texture==t&&e.frame==frame))continue;
                foreach(var key in sprites.Where(p=>p.Value.sprite.texture==t).Select(p=>p.Key).ToArray())RemoveSprite(key);
                Resources.UnloadAsset(t);textures.Remove(pair.Key);
            }
        }
        void RemoveSprite(string key){UnityEngine.Object.Destroy(sprites[key].sprite);sprites.Remove(key);}
        public void Dispose(){foreach(var e in sprites.Values)UnityEngine.Object.Destroy(e.sprite);sprites.Clear();pinnedTextures.Clear();foreach(var e in textures.Values)Resources.UnloadAsset(e.texture);textures.Clear();}
    }
}
