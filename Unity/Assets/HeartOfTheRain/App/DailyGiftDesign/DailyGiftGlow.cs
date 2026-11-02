using UnityEngine;
using UnityEngine.UI;
namespace HeartOfTheRain.App.Profile {
    // Small UI mesh, confined to the hero; no texture readback, bloom or particle system.
    [RequireComponent(typeof(CanvasRenderer))] public sealed class DailyGiftGlow:MaskableGraphic {
        public bool solidCircle;
        protected override void OnPopulateMesh(VertexHelper vh){
            vh.Clear();var r=rectTransform.rect;var center=r.center;vh.AddVert(center,color,Vector2.one*.5f);
            for(int i=0;i<=32;i++){float a=i/32f*Mathf.PI*2;vh.AddVert(center+new Vector2(Mathf.Cos(a)*r.width*.45f,Mathf.Sin(a)*r.height*.45f),solidCircle?color:new Color(color.r,color.g,color.b,0),Vector2.zero);if(i>0)vh.AddTriangle(0,i,i+1);}
        }
    }
}
