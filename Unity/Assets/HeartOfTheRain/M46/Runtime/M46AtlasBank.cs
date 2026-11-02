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
        sealed class SpriteEntry { public Sprite sprite; public int frame; public bool pinned; public TextureEntry owner; public SpriteEntry[] slots; public int slot; }
        readonly M46Assets assets;
        readonly Dictionary<string,SpriteEntry> sprites=new Dictionary<string,SpriteEntry>();
        readonly Dictionary<string,TextureEntry> textures=new Dictionary<string,TextureEntry>();
        readonly Dictionary<Texture2D,TextureEntry> textureOwners=new Dictionary<Texture2D,TextureEntry>();
        readonly HashSet<Texture2D> pinnedTextures=new HashSet<Texture2D>();
        readonly Dictionary<string,ResourceRequest> pending=new Dictionary<string,ResourceRequest>();
        readonly Dictionary<string,BodyAsset> bodies;
        readonly Dictionary<string,ClipAsset> clips;
        readonly Dictionary<string,ClipData> clipData;
        readonly Manifest[] powers;
        readonly Dictionary<string,HeartOfTheRain.M05.SpriteSequence>[] powerClips;
        readonly string[][] powerKeys;readonly Dictionary<string,string[]> obstacleKeys=new Dictionary<string,string[]>();
        readonly SpriteEntry[][] powerFrames;
        readonly Dictionary<string,SpriteEntry[]> obstacleFrames=new Dictionary<string,SpriteEntry[]>();
        readonly List<KeyValuePair<string,SpriteEntry>> spriteCandidates=new List<KeyValuePair<string,SpriteEntry>>();
        readonly List<KeyValuePair<string,TextureEntry>> textureCandidates=new List<KeyValuePair<string,TextureEntry>>();
        readonly List<string> textureSpriteKeys=new List<string>();
        readonly Queue<int> powerPreparationQueue=new Queue<int>();
        readonly bool[] powerPreparationQueued;readonly int[] powerPreparationIndex;
        Action<Sprite> powerGeometryOwner;bool powerPreparationRunning,disposed;
        double powerPreparationBudget;int powerPreparationFrameLimit;
        int frame;float frameTime;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public bool VerificationSkipCachedLookup;
        public bool VerificationUseLegacyFrameLookup;
        [Serializable] public struct PowerPreparationBatch {
            public int frame,frames,spriteCreates,remainingAtlases;
            public double startedWall,finishedWall,milliseconds;
        }
        public PowerPreparationBatch LastPowerPreparationBatch {get;private set;}
        public int PowerPreparationBatches {get;private set;}
        public int PowerPreparationFrames {get;private set;}
        public int PowerPreparationCreates {get;private set;}
        public int PowerPreparationSkippedAtlases {get;private set;}
        public double PowerPreparationMaxBatchMilliseconds {get;private set;}
#endif
        public bool PowerPreparationPending=>powerPreparationRunning||powerPreparationQueue.Count>0;
        long textureBytes;int pinnedSprites;
        // A full orb/rocket or Golden/Bomb turn uses roughly 1,400 distinct
        // frames. Keep that working set within a fixed cap across idle tails.
        // The pinned authored obstacle set prepared before input is added on
        // top of both caps by WarmObstacleFrames so it never squeezes them.
        public const int WorkingSetSpriteLimit=2048;
        public const long WorkingSetTextureBudget=128L*1024*1024;
        public int SpriteLimit=WorkingSetSpriteLimit;
        public long TextureBudget=WorkingSetTextureBudget;
        public int PinnedSprites=>pinnedSprites;
        public int SpriteCount=>sprites.Count;
        public int TextureCount=>textures.Count;
        public long TextureBytes=>textureBytes;
        // Counter-only diagnostics: no per-frame event lists or logging.
        public int SpriteCreates {get;private set;}
        public int SpriteEvictions {get;private set;}
        public int SpriteHighWaterMark {get;private set;}
        // Explicit diagnostic query; never called from live frame rendering.
        public long CachedSpriteRuntimeBytes {get{long bytes=0;foreach(var e in sprites.Values)bytes+=Profiler.GetRuntimeMemorySizeLong(e.sprite);return bytes;}}
        // Snapshot only frames already owned by this bank. Bodies stay on their
        // masked SpriteRenderers; power/obstacle frames feed the effect meshes.
        // The caller bounds preparation independently of later cache demand.
        public Sprite[] CachedEffectSpritesSnapshot(int maximum=2048){
            var snapshot=new List<Sprite>(Math.Min(Math.Max(0,maximum),sprites.Count));
            foreach(var pair in sprites){
                if(snapshot.Count>=maximum)break;
                if(pair.Key.StartsWith("p/",StringComparison.Ordinal)||pair.Key.StartsWith("o/",StringComparison.Ordinal))snapshot.Add(pair.Value.sprite);
            }
            return snapshot.ToArray();
        }
        public int SynchronousLoads { get; private set; }
        public string LoadError { get; private set; }
        public M46AtlasBank(M46Assets a) {
            assets=a;
            powers=a.powerManifests.Select(m=>JsonUtility.FromJson<Manifest>(m.text)).ToArray();
            powerPreparationQueued=new bool[powers.Length];powerPreparationIndex=new int[powers.Length];
            powerClips=powers.Select(m=>m.clips.ToDictionary(c=>c.name)).ToArray();powerKeys=new string[powers.Length][];powerFrames=new SpriteEntry[powers.Length][];
            for(int i=0;i<powers.Length;i++){powerKeys[i]=Enumerable.Range(0,powers[i].frames.Length).Select(n=>"p/"+i+"/"+n).ToArray();powerFrames[i]=new SpriteEntry[powers[i].frames.Length];}
            bodies=a.bodies.ToDictionary(b=>b.key);
            clips=a.obstacleClips.ToDictionary(c=>c.key);
            clipData=a.obstacleClips.ToDictionary(c=>c.key,c=>JsonUtility.FromJson<ClipData>(c.metadata.text));
            foreach(var c in clipData){obstacleKeys[c.Key]=Enumerable.Range(0,c.Value.frames.Length).Select(n=>"o/"+c.Key+"/"+n).ToArray();obstacleFrames[c.Key]=new SpriteEntry[c.Value.frames.Length];}
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
            TextureEntry previous;if(textures.TryGetValue(path,out previous))textureBytes-=previous.bytes;
            var entry=new TextureEntry{texture=texture,used=Time.unscaledTime,bytes=Profiler.GetRuntimeMemorySizeLong(texture)};textures[path]=entry;textureBytes+=entry.bytes;
            textureOwners[texture]=entry;
        }
        public IEnumerator Prewarm(IEnumerable<string> paths) {
            LoadError=null;
            // Issue every missing request before waiting on any of them so the
            // loads overlap. Waiting on each request before issuing the next
            // cost at least one frame per page at the playback gate.
            var wanted=new List<string>();
            foreach(var path in paths.Where(p=>!string.IsNullOrEmpty(p)).Distinct()) {
                if(textures.ContainsKey(path)){textures[path].used=Time.unscaledTime;continue;}
                if(!pending.ContainsKey(path))pending[path]=Resources.LoadAsync<Texture2D>(path);
                wanted.Add(path);
            }
            foreach(var path in wanted) {
                ResourceRequest request;
                // Another coroutine may have completed and stored this path meanwhile.
                if(!pending.TryGetValue(path,out request)){if(textures.ContainsKey(path))continue;request=Resources.LoadAsync<Texture2D>(path);pending[path]=request;}
                // A ResourceRequest can only be yielded by one coroutine. Poll
                // completion so the prefetcher and foreground gate can share it.
                while(!request.isDone)yield return null;
                var texture=request.asset as Texture2D;
                if(texture==null){LoadError="Missing texture resource: "+path;Debug.LogError(LoadError);yield break;}
                if(!textures.ContainsKey(path))Store(path,texture);pending.Remove(path);
            }
        }
        public bool Ready(IEnumerable<string> paths){foreach(var path in paths)if(!string.IsNullOrEmpty(path)&&!textures.ContainsKey(path))return false;return true;}
        // A bank has one geometry owner for its lifetime. Overlapping requests
        // coalesce by atlas into this single worker; they never add another
        // per-frame preparation budget. Textures must already be resident from
        // the normal dependency prefetch. Demand lookup remains the fallback.
        public IEnumerator WarmPowerFrames(IEnumerable<string> resourcePaths,Action<Sprite> prepareGeometry,double budgetMilliseconds=1,int maxFramesPerBatch=16){
            if(disposed)yield break;
            if(prepareGeometry!=null){
                if(powerGeometryOwner!=null&&!powerGeometryOwner.Equals(prepareGeometry))throw new InvalidOperationException("A power atlas bank has one geometry preparation owner");
                powerGeometryOwner=prepareGeometry;
            }
            var wanted=new HashSet<string>(resourcePaths??Array.Empty<string>(),StringComparer.Ordinal);
            for(int atlas=0;atlas<powers.Length;atlas++){
                var path=PathAt(assets.powerResources,atlas);
                if(string.IsNullOrEmpty(path)||!wanted.Contains(path)||!textures.ContainsKey(path)||powerPreparationQueued[atlas])continue;
                powerPreparationQueued[atlas]=true;powerPreparationIndex[atlas]=0;powerPreparationQueue.Enqueue(atlas);
            }
            if(powerPreparationQueue.Count==0)yield break;
            double budget=Math.Max(.1,budgetMilliseconds);int limit=Math.Max(1,maxFramesPerBatch);
            if(powerPreparationRunning){powerPreparationBudget=Math.Min(powerPreparationBudget,budget);powerPreparationFrameLimit=Math.Min(powerPreparationFrameLimit,limit);yield break;}
            powerPreparationRunning=true;powerPreparationBudget=budget;powerPreparationFrameLimit=limit;
            try{
                // Starting this coroutine during Accept must not create native
                // sprites or inspect quad geometry in the command-start span.
                yield return null;
                while(!disposed&&powerPreparationQueue.Count>0){
                    long stamp=System.Diagnostics.Stopwatch.GetTimestamp();int work=0;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    int created=SpriteCreates;double startedWall=Time.realtimeSinceStartupAsDouble;
#endif
                    while(!disposed&&powerPreparationQueue.Count>0){
                        int atlas=powerPreparationQueue.Peek();var path=PathAt(assets.powerResources,atlas);TextureEntry resident;
                        if(!textures.TryGetValue(path,out resident)||!resident.texture){
                            powerPreparationQueue.Dequeue();powerPreparationQueued[atlas]=false;powerPreparationIndex[atlas]=0;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                            PowerPreparationSkippedAtlases++;
#endif
                            continue;
                        }
                        var manifest=powers[atlas];var texture=resident.texture;
                        if(texture.width!=manifest.atlasWidth||texture.height!=manifest.atlasHeight)throw new InvalidOperationException("Power atlas dimensions differ from the manifest: "+atlas+". Reimport at authored resolution.");
                        resident.used=Time.unscaledTime;
                        int index=powerPreparationIndex[atlas];var f=manifest.frames[index];
                        var sprite=Frame(powerKeys[atlas][index],texture,new Rect(f.x,f.y,f.width,f.height),manifest.pixelsPerUnit);
                        powerGeometryOwner?.Invoke(sprite);work++;if(disposed)break;powerPreparationIndex[atlas]=index+1;
                        if(index+1==manifest.frames.Length){powerPreparationQueue.Dequeue();powerPreparationQueued[atlas]=false;powerPreparationIndex[atlas]=0;}
                        if(work>=powerPreparationFrameLimit||(System.Diagnostics.Stopwatch.GetTimestamp()-stamp)*1000.0/System.Diagnostics.Stopwatch.Frequency>=powerPreparationBudget)break;
                    }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    double elapsed=(System.Diagnostics.Stopwatch.GetTimestamp()-stamp)*1000.0/System.Diagnostics.Stopwatch.Frequency;
                    LastPowerPreparationBatch=new PowerPreparationBatch{frame=Time.frameCount,frames=work,spriteCreates=SpriteCreates-created,remainingAtlases=powerPreparationQueue.Count,startedWall=startedWall,finishedWall=Time.realtimeSinceStartupAsDouble,milliseconds=elapsed};
                    PowerPreparationBatches++;PowerPreparationFrames+=work;PowerPreparationCreates+=SpriteCreates-created;PowerPreparationMaxBatchMilliseconds=Math.Max(PowerPreparationMaxBatchMilliseconds,elapsed);
#endif
                    if(!disposed&&powerPreparationQueue.Count>0)yield return null;
                }
            }finally{powerPreparationRunning=false;}
        }
        // These atlases are already loaded for every board. Prepare their
        // native sprite objects before input, in bounded batches, without
        // loading another texture or changing the authored frame geometry.
        public IEnumerator WarmCommonFrames(int batch=16){
            int work=0;
            foreach(int atlas in new[]{2,3,4,12}){
                var texture=Texture(assets.powerAtlases[atlas],PathAt(assets.powerResources,atlas));var manifest=powers[atlas];
                if(texture.width!=manifest.atlasWidth||texture.height!=manifest.atlasHeight)throw new InvalidOperationException("Power atlas dimensions differ from the manifest: "+atlas+". Reimport at authored resolution.");
                for(int index=0;index<manifest.frames.Length;index++){
                    var f=manifest.frames[index];Frame(powerKeys[atlas][index],texture,new Rect(f.x,f.y,f.width,f.height),manifest.pixelsPerUnit);
                    if(++work>=Math.Max(1,batch)){work=0;yield return null;}
                }
            }
        }
        // Obstacle families present on this board. Gems and powers draw from
        // the power atlases; every other family owns clip pages and bodies.
        static List<string> ObstacleFamilies(BoardSnapshot snapshot){
            var families=new List<string>();
            foreach(var p in snapshot.pieces)if(p.family!="gem"&&p.family!="power"&&!families.Contains(p.family))families.Add(p.family);
            return families;
        }
        static bool HasFamilyPrefix(string key,List<string> families){
            int slash=key.IndexOf('/');if(slash<0)return false;
            foreach(var f in families)if(slash==f.Length&&string.CompareOrdinal(key,0,f,0,slash)==0)return true;
            return false;
        }
        // Bodies a family can reveal during play: every surviving layer, plus
        // the spirit/rainlight and shared glint that pod and cabinet
        // collections draw the first time one clears.
        List<string> ObstacleBodyKeys(BoardSnapshot snapshot,List<string> families){
            var keys=new List<string>();
            foreach(var family in families){
                int hp=0;foreach(var p in snapshot.pieces)if(p.family==family)hp=Math.Max(hp,p.hp);
                for(int i=1;i<=Math.Max(1,hp);i++){var key=BoardPresentation.BodyKey(new Piece{family=family,hp=i});if(bodies.ContainsKey(key)&&!keys.Contains(key))keys.Add(key);}
            }
            if(families.Contains("pod")||families.Contains("cabinet")){
                foreach(var key in new[]{"collectionGlint",families.Contains("pod")?"waterSpirit":null,families.Contains("cabinet")?"rainlight":null})
                    if(key!=null&&bodies.ContainsKey(key)&&!keys.Contains(key))keys.Add(key);
            }
            return keys;
        }
        // Fragments, hit accents and lower-HP bodies are one shared set per
        // family, not one sprite set per piece, and many pieces can break in
        // the same power wave. Prepare every family on the board before input
        // rather than creating native sprites mid-burst. Checkpoint 44 did this
        // for crates only; the first hit on any other family still created its
        // frames on the frame the debris appeared.
        public IEnumerator WarmObstacleFrames(BoardSnapshot snapshot,int batch=16){
            var families=ObstacleFamilies(snapshot);
            if(families.Count==0)yield break;
            int work=0;
            foreach(var pair in clipData){
                if(!HasFamilyPrefix(pair.Key,families))continue;
                var clip=clips[pair.Key];var meta=pair.Value;
                for(int index=0;index<meta.frames.Length;index++){
                    var f=meta.frames[index];var texture=Texture(clip.pages[f.page],PathAt(clip.pageResources,f.page));
                    // Keep this fixed working set for the board's lifetime;
                    // unrelated combos must not evict it before a later hit.
                    Frame(obstacleKeys[pair.Key][index],texture,new Rect(f.x,f.y,f.w,f.h),meta.pixelsPerUnit,true);
                    if(++work>=Math.Max(1,batch)){
                        // Render/EndFrame runs between batches. Give the pinned
                        // frames their separate budget before it can evict the
                        // common unpinned sprites prepared just before this pass.
                        SpriteLimit=Math.Max(SpriteLimit,WorkingSetSpriteLimit+pinnedSprites);
                        work=0;yield return null;
                    }
                }
            }
            foreach(var key in ObstacleBodyKeys(snapshot,families))Get(new DrawSprite{bank="body",key=key});
            // The pinned authored set is never evicted; keep the bounded
            // working set for powers and tiles the same size on top of it.
            SpriteLimit=Math.Max(SpriteLimit,WorkingSetSpriteLimit+pinnedSprites);
            long pinnedBytes=0;foreach(var t in pinnedTextures){TextureEntry e;if(textureOwners.TryGetValue(t,out e))pinnedBytes+=e.bytes;}
            TextureBudget=Math.Max(TextureBudget,WorkingSetTextureBudget+pinnedBytes);
        }
        public HashSet<string> CommonResources(BoardSnapshot snapshot){
            var needed=new HashSet<string>();foreach(int i in new[]{2,3,4,12}){var path=PathAt(assets.powerResources,i);if(!string.IsNullOrEmpty(path))needed.Add(path);}
            foreach(var p in snapshot.pieces){BodyAsset b;if(bodies.TryGetValue(BoardPresentation.BodyKey(p),out b)&&!string.IsNullOrEmpty(b.resource))needed.Add(b.resource);}
            // Every refill color is known before the first move.
            for(int i=0;i<6;i++){BodyAsset b;if(bodies.TryGetValue("tile"+i,out b)&&!string.IsNullOrEmpty(b.resource))needed.Add(b.resource);}
            // Every obstacle family on the board: its clip pages and the bodies
            // of each layer it can reveal. Loading these during preparation
            // keeps the first hit of each family off the playback gate.
            var families=ObstacleFamilies(snapshot);
            foreach(var c in clips.Values)if(HasFamilyPrefix(c.key,families))foreach(var path in c.pageResources??Array.Empty<string>())if(!string.IsNullOrEmpty(path))needed.Add(path);
            foreach(var key in ObstacleBodyKeys(snapshot,families)){BodyAsset b;if(bodies.TryGetValue(key,out b)&&!string.IsNullOrEmpty(b.resource))needed.Add(b.resource);}
            return needed;
        }
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
        public void BeginFrame(){frame++;frameTime=Time.unscaledTime;}
        bool Cached(string key,out Sprite sprite){
            sprite=null;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(VerificationSkipCachedLookup)return false;
#endif
            SpriteEntry entry;if(!sprites.TryGetValue(key,out entry))return false;
            entry.frame=frame;if(entry.owner!=null)entry.owner.used=frame==0?Time.unscaledTime:frameTime;
            sprite=entry.sprite;return true;
        }
        // These slots refer only to entries owned by sprites. Removal clears
        // the slot before destruction; a slot never extends an evicted lifetime.
        bool CachedFrame(string key,SpriteEntry[] slots,int index,out Sprite sprite){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(VerificationUseLegacyFrameLookup)return Cached(key,out sprite);
            if(VerificationSkipCachedLookup){sprite=null;return false;}
#endif
            var entry=slots[index];
            if(entry==null){
                if(!sprites.TryGetValue(key,out entry)){sprite=null;return false;}
                entry.slots=slots;entry.slot=index;slots[index]=entry;
            }
            entry.frame=frame;if(entry.owner!=null)entry.owner.used=frame==0?Time.unscaledTime:frameTime;
            sprite=entry.sprite;return true;
        }
        Sprite Frame(string key,Texture2D texture,Rect rect,float ppu,bool pinned=false) {
            SpriteEntry e;
            if(!sprites.TryGetValue(key,out e)) {
                if(rect.x<0||rect.y<0||rect.xMax>texture.width||rect.yMax>texture.height)
                    throw new InvalidOperationException("Atlas was resized during import: "+key);
                var s=Sprite.Create(texture,rect,new Vector2(.5f,.5f),ppu,0,SpriteMeshType.FullRect);s.name=key;
                TextureEntry owner;textureOwners.TryGetValue(texture,out owner);
                e=new SpriteEntry{sprite=s,owner=owner};sprites.Add(key,e);
                SpriteCreates++;SpriteHighWaterMark=Math.Max(SpriteHighWaterMark,sprites.Count);
            }
            e.frame=frame;if(pinned){if(!e.pinned){e.pinned=true;pinnedSprites++;}pinnedTextures.Add(texture);}return e.sprite;
        }
        public Sprite Whole(string key,Texture2D texture,float cells,bool pinned=false)=>Frame(key,texture,new Rect(0,0,texture.width,texture.height),texture.width/cells,pinned);
        public Sprite BoardSurface(int i){var t=Texture(assets.surfaces[i],PathAt(assets.surfaceResources,i));return Whole("surface/"+i,t,t.width/64f,true);}
        public Sprite BoardMask(int i){var t=Texture(assets.masks[i],PathAt(assets.maskResources,i));return Whole("mask/"+i,t,t.width/64f,true);}
        public Sprite BoardSurface(int i,string resource,int width,int height){var t=Texture(null,resource);if(t.width!=width||t.height!=height)throw new InvalidOperationException("Saved board surface dimensions differ");return Whole("surface/"+i+"/"+resource,t,t.width/64f,true);}
        public Sprite BoardMask(int i,string resource,int width,int height){var t=Texture(null,resource);if(t.width!=width||t.height!=height)throw new InvalidOperationException("Saved board mask dimensions differ");return Whole("mask/"+i+"/"+resource,t,t.width/64f,true);}
        public Sprite Get(DrawSprite d) {
            Sprite cached;
            if(d.bank=="body"){if(Cached(d.key,out cached))return cached;var b=bodies[d.key];return Whole(d.key,Texture(b.texture,b.resource),b.canvasCells);}
            if(d.bank=="power") {
                var m=powers[d.atlas];HeartOfTheRain.M05.SpriteSequence c;
                if(!powerClips[d.atlas].TryGetValue(d.key,out c))throw new InvalidOperationException("Missing clip "+d.atlas+"/"+d.key);
                int n=Mathf.Max(0,Mathf.FloorToInt(d.age*c.fps));
                if(c.loop)n%=c.count;else if(n>=c.count){if(c.endBehavior=="hide")return null;n=c.count-1;}
                n+=c.start;if(CachedFrame(powerKeys[d.atlas][n],powerFrames[d.atlas],n,out cached))return cached;
                var f=m.frames[n];var t=Texture(assets.powerAtlases[d.atlas],PathAt(assets.powerResources,d.atlas));
                if(t.width!=m.atlasWidth||t.height!=m.atlasHeight)throw new InvalidOperationException("Power atlas dimensions differ from the manifest: "+d.atlas+". Reimport at authored resolution.");
                return Frame(powerKeys[d.atlas][n],t,new Rect(f.x,f.y,f.width,f.height),m.pixelsPerUnit);
            }
            var meta=clipData[d.key];int index=Mathf.Max(0,Mathf.FloorToInt(d.age*meta.fps));
            if(meta.loop)index%=meta.frames.Length;else if(index>=meta.frames.Length){if(!meta.holdLast)return null;index=meta.frames.Length-1;}
            if(CachedFrame(obstacleKeys[d.key][index],obstacleFrames[d.key],index,out cached))return cached;
            var cf=meta.frames[index];var clip=clips[d.key];var texture=Texture(clip.pages[cf.page],PathAt(clip.pageResources,cf.page));
            return Frame(obstacleKeys[d.key][index],texture,new Rect(cf.x,cf.y,cf.w,cf.h),meta.pixelsPerUnit);
        }
        public void EndFrame(bool mayEvictTextures) {
            // Hysteresis: over the cap, evict down to 7/8 of it so a burst that creates
            // a frame per frame does not rebuild and sort the candidate list every frame.
            int remove=sprites.Count>SpriteLimit?sprites.Count-Math.Max(0,SpriteLimit-SpriteLimit/8):0;
            if(remove>0){spriteCandidates.Clear();foreach(var pair in sprites)if(!pair.Value.pinned&&pair.Value.frame!=frame)spriteCandidates.Add(pair);spriteCandidates.Sort((a,b)=>a.Value.frame.CompareTo(b.Value.frame));for(int i=0;i<remove&&i<spriteCandidates.Count;i++)RemoveSprite(spriteCandidates[i].Key);spriteCandidates.Clear();}
            if(!mayEvictTextures||TextureBytes<=TextureBudget)return;
            textureCandidates.Clear();foreach(var pair in textures)textureCandidates.Add(pair);textureCandidates.Sort((a,b)=>a.Value.used.CompareTo(b.Value.used));
            foreach(var pair in textureCandidates) {
                if(TextureBytes<=TextureBudget)break;
                var t=pair.Value.texture;
                if(pinnedTextures.Contains(t)||Time.unscaledTime-pair.Value.used<2)continue;
                bool visible=false;textureSpriteKeys.Clear();foreach(var sprite in sprites)if(sprite.Value.sprite.texture==t){textureSpriteKeys.Add(sprite.Key);if(sprite.Value.frame==frame)visible=true;}if(visible)continue;
                foreach(var key in textureSpriteKeys)RemoveSprite(key);
                textureOwners.Remove(t);Resources.UnloadAsset(t);textureBytes-=pair.Value.bytes;textures.Remove(pair.Key);
            }
            textureCandidates.Clear();textureSpriteKeys.Clear();
        }
        void RemoveSprite(string key){var entry=sprites[key];if(entry.slots!=null)entry.slots[entry.slot]=null;UnityEngine.Object.Destroy(entry.sprite);sprites.Remove(key);SpriteEvictions++;}
        public void Dispose(){disposed=true;powerPreparationQueue.Clear();Array.Clear(powerPreparationQueued,0,powerPreparationQueued.Length);Array.Clear(powerPreparationIndex,0,powerPreparationIndex.Length);powerGeometryOwner=null;powerPreparationRunning=false;foreach(var e in sprites.Values){if(e.slots!=null)e.slots[e.slot]=null;UnityEngine.Object.Destroy(e.sprite);}sprites.Clear();pinnedTextures.Clear();pinnedSprites=0;foreach(var e in textures.Values)Resources.UnloadAsset(e.texture);textures.Clear();textureOwners.Clear();textureBytes=0;}
    }
}
