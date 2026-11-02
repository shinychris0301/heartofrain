using System.Collections;
using System.Collections.Generic;
using UnityEngine;
namespace HeartOfTheRain.M47 {
    // Draws one frame's unmasked, non-glow effect sprites (fragments, accents,
    // tile breaks, power clips) as a few procedural meshes instead of one
    // SpriteRenderer each. Geometry, UVs, material, sorting order and colour
    // match the SpriteRenderer path exactly; one mesh per texture page and
    // sorting order, so a dense burst costs a handful of renderers instead
    // of hundreds.
    public sealed class EffectMeshBatcher {
        // Preparation is bounded; later effects still grow through the same
        // demand path. Leave headroom under the existing 4,096-entry cache flush.
        public const int PreparedGeometryLimit=2048,PreparedSlotReserve=32;
        // Verification only: one mesh per contiguous run instead of per page,
        // which keeps exact list order at the cost of many more meshes.
        public bool KeepDrawOrder;
        sealed class Slot {
            public GameObject node;public MeshFilter filter;public MeshRenderer renderer;public Mesh mesh;public MaterialPropertyBlock block;
            public Texture2D texture;public int order=int.MinValue,indexCount,vertexCount,triangleCount;public bool enabled;
            public Vector3[] vertices=new Vector3[512];public Vector2[] uvs=new Vector2[512];
            public Color32[] colors=new Color32[512];public int[] triangles=new int[768];
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            // The same-APK comparison keeps the old storage ready before input.
            // Ordinary release drawing owns only the retained arrays above.
            public readonly List<Vector3> legacyVertices=new List<Vector3>(512);public readonly List<Vector2> legacyUvs=new List<Vector2>(512);
            public readonly List<Color32> legacyColors=new List<Color32>(512);public readonly List<int> legacyTriangles=new List<int>(768);
#endif
        }
        // A sprite's quad in its own units, as SpriteRenderer builds it: rect
        // corners relative to the pivot, divided by pixels per unit.
        sealed class SpriteGeometry {public Texture2D texture;public int textureId;public float left,right,bottom,top;public Vector2 uvMin,uvMax;}
        static readonly int MainTexture=Shader.PropertyToID("_MainTex");
        readonly Transform root;readonly Material material;readonly Bounds bounds;
        readonly List<Slot> slots=new List<Slot>();readonly Dictionary<Sprite,SpriteGeometry> geometry=new Dictionary<Sprite,SpriteGeometry>();
        // One mesh per (texture, sorting order) per frame, in order of first
        // appearance. Within a mesh the quads keep draw order; sprites that
        // share a sorting order but not a texture page compose in page order,
        // which the SpriteRenderer path never defined either.
        readonly Dictionary<long,Slot> open=new Dictionary<long,Slot>();
        Slot current;long currentKey;int used;
        public int Quads {get;private set;}
        public int Meshes=>used;
        public int SlotCount=>slots.Count;
        public int GeometryCount=>geometry.Count;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        // Same-APK verification only; ordinary/release drawing uses the exact
        // zero-angle shortcut below. Never alter counts, geometry or quality.
        public static bool VerificationUseCheckpoint75Transform;
        [System.NonSerialized] public bool VerificationUseCheckpoint77Submission;
        bool legacySubmission;
        public int GeometryMisses {get;private set;}
        public int SlotCreates {get;private set;}
        public int PreparedGeometryCount {get;private set;}
        public int PreparedSlotCount {get;private set;}
        public int PreparationBatches {get;private set;}
        public int PreparationYields {get;private set;}
        public double PreparationMilliseconds {get;private set;}
        public double PreparationMaxBatchMilliseconds {get;private set;}
#endif
        public EffectMeshBatcher(Transform root,Material material,Bounds bounds){this.root=root;this.material=material;this.bounds=bounds;}
        public void Begin(){
            used=0;current=null;currentKey=0;Quads=0;open.Clear();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            // Capture ownership once. A diagnostic switch changed during a
            // frame cannot make End upload a different buffer than Add filled.
            legacySubmission=VerificationUseCheckpoint77Submission;
            GeometryMisses=SlotCreates=0;
#endif
            // Sprites the bank evicted stay as keys; bound the cache instead of tracking them.
            if(geometry.Count>4096)geometry.Clear();
        }
        SpriteGeometry Geometry(Sprite sprite){
            SpriteGeometry g;
            if(!geometry.TryGetValue(sprite,out g)){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                GeometryMisses++;
#endif
                var rect=sprite.textureRect;var texture=sprite.texture;float ppu=sprite.pixelsPerUnit;var pivot=sprite.pivot;
                g=new SpriteGeometry{texture=texture,textureId=texture.GetInstanceID(),left=-pivot.x/ppu,right=(rect.width-pivot.x)/ppu,bottom=-pivot.y/ppu,top=(rect.height-pivot.y)/ppu,
                    uvMin=new Vector2(rect.xMin/texture.width,rect.yMin/texture.height),uvMax=new Vector2(rect.xMax/texture.width,rect.yMax/texture.height)};
                geometry.Add(sprite,g);
            }
            return g;
        }
        // The bank has already copied these references before this iterator can
        // yield. Reading quad geometry never requests a texture or changes its
        // residency. Actual work, rather than a fixed frame count, gates readiness.
        public IEnumerator Prepare(Sprite[] cachedSprites,int reserve=PreparedSlotReserve,double budgetMilliseconds=2){
            int count=cachedSprites==null?0:System.Math.Min(PreparedGeometryLimit,cachedSprites.Length);
            reserve=System.Math.Max(0,reserve);budgetMilliseconds=System.Math.Max(.1,budgetMilliseconds);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            int geometryBefore=geometry.Count,slotsBefore=slots.Count;
            PreparedGeometryCount=PreparedSlotCount=PreparationBatches=PreparationYields=0;
            PreparationMilliseconds=PreparationMaxBatchMilliseconds=0;
#endif
            var watch=System.Diagnostics.Stopwatch.StartNew();bool worked=false;
            for(int i=0;i<count;i++){
                var sprite=cachedSprites[i];
                if(sprite!=null&&(geometry.Count<PreparedGeometryLimit||geometry.ContainsKey(sprite))){Geometry(sprite);worked=true;}
                if(worked&&(i+1<count||slots.Count<reserve)&&watch.Elapsed.TotalMilliseconds>=budgetMilliseconds){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);PreparationYields++;
#endif
                    yield return null;watch.Restart();worked=false;
                }
            }
            while(slots.Count<reserve){
                CreateSlot();worked=true;
                if(slots.Count<reserve&&watch.Elapsed.TotalMilliseconds>=budgetMilliseconds){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);PreparationYields++;
#endif
                    yield return null;watch.Restart();worked=false;
                }
            }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(worked)RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);
            PreparedGeometryCount=geometry.Count-geometryBefore;PreparedSlotCount=slots.Count-slotsBefore;
#endif
        }
        // Accepted-turn prefetch can prepare newly resident power frames while
        // earlier swap/merge poses play. Keep the existing preparation bound;
        // demand rendering remains responsible for anything outside it.
        public void PrepareSprite(Sprite sprite){
            if(sprite!=null&&(geometry.Count<PreparedGeometryLimit||geometry.ContainsKey(sprite)))Geometry(sprite);
        }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        void RecordPreparationBatch(double milliseconds){PreparationBatches++;PreparationMilliseconds+=milliseconds;PreparationMaxBatchMilliseconds=System.Math.Max(PreparationMaxBatchMilliseconds,milliseconds);}
#endif
        public void Add(Sprite sprite,int order,Vector3 position,float angle,float sx,float sy,Color color){
            var g=Geometry(sprite);
            // Same page/order grouping as before; the immutable texture ID was
            // already read when this sprite's geometry was cached.
            long key=((long)g.textureId<<32)^(uint)order;
            if(current==null||currentKey!=key){
                if(KeepDrawOrder)current=Open(g.texture,order);
                else if(!open.TryGetValue(key,out current)){current=Open(g.texture,order);open.Add(key,current);}
                currentKey=key;
            }
            // Exact zero alone avoids two engine trigonometry calls. Retain
            // signed-zero sine and the original vertex arithmetic/order.
            float radians=angle*Mathf.Deg2Rad,cos=1,sin=radians;bool rotate=angle!=0;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            rotate|=VerificationUseCheckpoint75Transform;
#endif
            if(rotate){cos=Mathf.Cos(radians);sin=Mathf.Sin(radians);}
            float l=g.left*sx,r=g.right*sx,b=g.bottom*sy,t=g.top*sy;int v=current.vertexCount;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(legacySubmission){
                v=current.legacyVertices.Count;
                current.legacyVertices.Add(new Vector3(position.x+l*cos-b*sin,position.y+l*sin+b*cos,0));
                current.legacyVertices.Add(new Vector3(position.x+l*cos-t*sin,position.y+l*sin+t*cos,0));
                current.legacyVertices.Add(new Vector3(position.x+r*cos-t*sin,position.y+r*sin+t*cos,0));
                current.legacyVertices.Add(new Vector3(position.x+r*cos-b*sin,position.y+r*sin+b*cos,0));
                current.legacyUvs.Add(new Vector2(g.uvMin.x,g.uvMin.y));current.legacyUvs.Add(new Vector2(g.uvMin.x,g.uvMax.y));current.legacyUvs.Add(new Vector2(g.uvMax.x,g.uvMax.y));current.legacyUvs.Add(new Vector2(g.uvMax.x,g.uvMin.y));
                Color32 c=color;current.legacyColors.Add(c);current.legacyColors.Add(c);current.legacyColors.Add(c);current.legacyColors.Add(c);
                if(current.indexCount==current.legacyTriangles.Count){current.legacyTriangles.Add(v);current.legacyTriangles.Add(v+1);current.legacyTriangles.Add(v+2);current.legacyTriangles.Add(v);current.legacyTriangles.Add(v+2);current.legacyTriangles.Add(v+3);}
            }else
#endif
            {
                // Retain the exact expressions and order of the old quad fill.
                // One shared capacity check replaces twelve List.Add updates.
                if(v+4>current.vertices.Length){int capacity=System.Math.Max(v+4,current.vertices.Length*2);System.Array.Resize(ref current.vertices,capacity);System.Array.Resize(ref current.uvs,capacity);System.Array.Resize(ref current.colors,capacity);}
                current.vertices[v]=new Vector3(position.x+l*cos-b*sin,position.y+l*sin+b*cos,0);
                current.vertices[v+1]=new Vector3(position.x+l*cos-t*sin,position.y+l*sin+t*cos,0);
                current.vertices[v+2]=new Vector3(position.x+r*cos-t*sin,position.y+r*sin+t*cos,0);
                current.vertices[v+3]=new Vector3(position.x+r*cos-b*sin,position.y+r*sin+b*cos,0);
                current.uvs[v]=new Vector2(g.uvMin.x,g.uvMin.y);current.uvs[v+1]=new Vector2(g.uvMin.x,g.uvMax.y);current.uvs[v+2]=new Vector2(g.uvMax.x,g.uvMax.y);current.uvs[v+3]=new Vector2(g.uvMax.x,g.uvMin.y);
                Color32 c=color;current.colors[v]=c;current.colors[v+1]=c;current.colors[v+2]=c;current.colors[v+3]=c;
                if(current.indexCount==current.triangleCount){
                    int i=current.indexCount;if(i+6>current.triangles.Length)System.Array.Resize(ref current.triangles,System.Math.Max(i+6,current.triangles.Length*2));
                    current.triangles[i]=v;current.triangles[i+1]=v+1;current.triangles[i+2]=v+2;current.triangles[i+3]=v;current.triangles[i+4]=v+2;current.triangles[i+5]=v+3;current.triangleCount+=6;
                }
                current.vertexCount+=4;
            }
            current.indexCount+=6;
            Quads++;
        }
        Slot CreateSlot(){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            SlotCreates++;
#endif
                var slot=new Slot{node=new GameObject("Effect mesh "+slots.Count)};slot.node.transform.SetParent(root,false);
                // Slot ownership never reorders: its depth depends only on its
                // fixed index, including prepared and demand-created slots.
                slot.node.transform.localPosition=new Vector3(0,0,-.001f*(slots.Count+1));
                slot.filter=slot.node.AddComponent<MeshFilter>();slot.renderer=slot.node.AddComponent<MeshRenderer>();
                slot.mesh=new Mesh{name="Effect mesh"};slot.mesh.MarkDynamic();slot.mesh.bounds=bounds;slot.filter.sharedMesh=slot.mesh;
                slot.renderer.sharedMaterial=material;slot.renderer.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;slot.renderer.receiveShadows=false;
                slot.renderer.lightProbeUsage=UnityEngine.Rendering.LightProbeUsage.Off;slot.renderer.reflectionProbeUsage=UnityEngine.Rendering.ReflectionProbeUsage.Off;slot.renderer.motionVectorGenerationMode=MotionVectorGenerationMode.ForceNoMotion;
                slot.block=new MaterialPropertyBlock();slot.renderer.enabled=false;slots.Add(slot);return slot;
        }
        Slot Open(Texture2D texture,int order){
            var slot=used<slots.Count?slots[used]:CreateSlot();
            // Later runs sit a hair nearer the orthographic camera so equal
            // sorting orders still draw in list order.
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(legacySubmission)slot.node.transform.localPosition=new Vector3(0,0,-.001f*(used+1));
#endif
            if(slot.texture!=texture){slot.texture=texture;slot.block.SetTexture(MainTexture,texture);slot.renderer.SetPropertyBlock(slot.block);}
            if(slot.order!=order){slot.order=order;slot.renderer.sortingOrder=order;}
            slot.vertexCount=slot.indexCount=0;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(legacySubmission){slot.legacyVertices.Clear();slot.legacyUvs.Clear();slot.legacyColors.Clear();}
#endif
            used++;return slot;
        }
        public void End(){
            for(int i=0;i<used;i++){
                var slot=slots[i];var mesh=slot.mesh;mesh.Clear(false);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(legacySubmission){mesh.SetVertices(slot.legacyVertices);mesh.SetUVs(0,slot.legacyUvs);mesh.SetColors(slot.legacyColors);mesh.SetTriangles(slot.legacyTriangles,0,slot.indexCount,0,false,0);}
                else
#endif
                {mesh.SetVertices(slot.vertices,0,slot.vertexCount);mesh.SetUVs(0,slot.uvs,0,slot.vertexCount);mesh.SetColors(slot.colors,0,slot.vertexCount);mesh.SetTriangles(slot.triangles,0,slot.indexCount,0,false,0);}
                mesh.bounds=bounds;
                if(!slot.enabled){slot.renderer.enabled=true;slot.enabled=true;}
            }
            for(int i=used;i<slots.Count;i++)if(slots[i].enabled){slots[i].renderer.enabled=false;slots[i].enabled=false;}
        }
        public void Dispose(){
            foreach(var slot in slots){if(slot.mesh)Object.Destroy(slot.mesh);if(slot.node)Object.Destroy(slot.node);}
            slots.Clear();geometry.Clear();used=0;current=null;Quads=0;
        }
    }
}
