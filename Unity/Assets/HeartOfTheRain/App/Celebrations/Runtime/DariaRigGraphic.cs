using UnityEngine;
using UnityEngine.UI;
namespace HeartOfTheRain.App.Celebrations
{
    // Native UI mesh skinning: one sharp texture sample, no crossfade between character poses.
    public sealed class DariaRigGraphic:MaskableGraphic
    {
        Texture2D art;int part;RigPose pose;
        public override Texture mainTexture=>art?art:Texture2D.whiteTexture;
        public void Configure(Texture2D texture,int partIndex)
        {art=texture;part=partIndex;raycastTarget=false;SetMaterialDirty();SetVerticesDirty();}
        public void Sample(RigPose value,float opacity){pose=value;color=new Color(1,1,1,opacity);SetVerticesDirty();}
        protected override void OnPopulateMesh(VertexHelper vh)
        {
            vh.Clear();if(!art)return;var rect=rectTransform.rect;int nx=part>=2?32:1,ny=part>=2?24:part==1?24:1;
            for(int y=0;y<=ny;y++)for(int x=0;x<=nx;x++)
            {
                float u=x/(float)nx,v=y/(float)ny;var p=DariaRigMotion.Vertex(part,u,v,pose);var c=color;
                if(part==1){float f=Mathf.Clamp01((1-v)/.14f);c.a*=f*f*(3-2*f);}
                var vertex=UIVertex.simpleVert;vertex.position=new Vector3(rect.xMin+p.x*rect.width,rect.yMax-p.y*rect.height,0);vertex.color=c;vertex.uv0=new Vector2(u,1-v);vh.AddVert(vertex);
            }
            for(int y=0;y<ny;y++)for(int x=0;x<nx;x++){int a=y*(nx+1)+x,b=a+1,c=a+nx+1,d=c+1;vh.AddTriangle(a,b,c);vh.AddTriangle(b,d,c);}
        }
    }
}
