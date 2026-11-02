using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
namespace HeartOfTheRain.App.Celebrations
{
    [RequireComponent(typeof(CanvasRenderer))]
    public sealed class M68MeshGraphic:MaskableGraphic
    {
        M68CelebrationAssets data;Material blend;int frame=-1;float opacity=-1;
        readonly List<UIVertex> vertices=new List<UIVertex>(5070);readonly List<int> triangles=new List<int>(19344);
        public override Texture mainTexture=>data?data.master:Texture2D.whiteTexture;
        public void Configure(M68CelebrationAssets assets){data=assets;data.Prepare();raycastTarget=false;blend=new Material(data.blendShader);blend.SetTexture("_BlinkTex",data.blink);material=blend;triangles.AddRange(data.Indices);SetMaterialDirty();}
        public void Sample(int sample,float alpha){if(frame==sample&&Mathf.Approximately(opacity,alpha))return;frame=sample;opacity=alpha;blend.SetFloat("_Blink",data.Clip.samples[frame].blink);SetVerticesDirty();}
        protected override void OnPopulateMesh(VertexHelper vh)
        {
            vh.Clear();if(!data||frame<0)return;var r=rectTransform.rect;int offset=frame*data.Clip.vertex_count*2;vertices.Clear();var c=(Color32)new Color(1,1,1,opacity);
            for(int i=0;i<data.Clip.vertex_count;i++){var v=UIVertex.simpleVert;v.position=new Vector3(r.xMin+data.Positions[offset+i*2]*r.width,r.yMin+data.Positions[offset+i*2+1]*r.height,0);v.uv0=new Vector2(data.UV[i*2],data.UV[i*2+1]);v.color=c;vertices.Add(v);}
            vh.AddUIVertexStream(vertices,triangles);
        }
        protected override void OnDestroy(){base.OnDestroy();if(blend){if(Application.isPlaying)Destroy(blend);else DestroyImmediate(blend);}}
    }
}
