using System;
using System.Collections;
using UnityEngine;
namespace HeartOfTheRain.App.Celebrations
{
    [Serializable] public sealed class M68MeshSample {public float opacity,blink;}
    [Serializable] public sealed class M68MeshClip {public int fps,frame_count,vertex_count,triangle_count;public M68MeshSample[] samples;}
    [Serializable] public sealed class M68Particle {public int id;public float x,y,size,height_ratio,angle,opacity;}
    [Serializable] public sealed class M68EffectSample {public float time,scrim_alpha,halo_alpha,halo_angle,halo_size;public float[] halo_center;public M68Particle[] particles;}
    [Serializable] public sealed class M68Effects {public int fps;public M68EffectSample[] samples;}
    [Serializable] public sealed class M68Seed {public int id;public bool star;public string color;}
    [Serializable] public sealed class M68Design {public M68Seed[] seeds;}
    public sealed class M68CelebrationAssets:ScriptableObject
    {
        public Texture2D master,blink,reduced,halo,star;
        public TextAsset clipJson,effectsJson,designJson,positions,uv,indices;
        public AudioClip sound;public Shader blendShader;
        [NonSerialized] public M68MeshClip Clip;[NonSerialized] public M68Effects Effects;[NonSerialized] public M68Design Design;
        [NonSerialized] public float[] Positions,UV;[NonSerialized] public int[] Indices;[NonSerialized] public Color[] Colors;
        static M68CelebrationAssets cached;
        public static M68CelebrationAssets Load(){if(!cached)cached=Resources.Load<M68CelebrationAssets>("M68_RuntimeAssets");if(cached)cached.Prepare();return cached;}
        public static IEnumerator Warmup(){var request=Resources.LoadAsync<M68CelebrationAssets>("M68_RuntimeAssets");yield return request;cached=request.asset as M68CelebrationAssets;if(cached)cached.Prepare();}
        public void Prepare()
        {
            if(Clip!=null)return;
            var clip=JsonUtility.FromJson<M68MeshClip>(clipJson.text);
            var p=positions.bytes;var u=uv.bytes;var idx=indices.bytes;
            if(!BitConverter.IsLittleEndian||clip.frame_count!=210||clip.vertex_count!=5070||p.Length!=clip.frame_count*clip.vertex_count*8||u.Length!=clip.vertex_count*8||idx.Length!=clip.triangle_count*12)throw new InvalidOperationException("Invalid M68 mesh payload.");
            Positions=new float[p.Length/4];UV=new float[u.Length/4];Indices=new int[idx.Length/4];Buffer.BlockCopy(p,0,Positions,0,p.Length);Buffer.BlockCopy(u,0,UV,0,u.Length);Buffer.BlockCopy(idx,0,Indices,0,idx.Length);
            Effects=JsonUtility.FromJson<M68Effects>(effectsJson.text);Design=JsonUtility.FromJson<M68Design>(designJson.text);Colors=new Color[Design.seeds.Length];
            foreach(var seed in Design.seeds){Color c;if(!ColorUtility.TryParseHtmlString(seed.color,out c))c=Color.white;Colors[seed.id]=c;}
            Clip=clip;
        }
        public static int Frame(float seconds)=>Mathf.Clamp(Mathf.FloorToInt(seconds*60),0,209);
    }
}
