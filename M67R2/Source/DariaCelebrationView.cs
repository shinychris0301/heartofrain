using UnityEngine;
using UnityEngine.UI;
namespace HeartOfTheRain.App.Celebrations
{
    public sealed class DariaCelebrationView:MonoBehaviour
    {
        RawImage front;Material blendMaterial;
        public bool Ready=>front&&front.texture;
        public void Configure(Texture2D atlas)
        {
            if(!atlas)return;
            if(!front)front=Make("Daria animated frame");
            front.texture=atlas;
            var a=CelebrationAssets.Load();
            if(a&&a.dariaBlend&&!blendMaterial){blendMaterial=new Material(a.dariaBlend);front.material=blendMaterial;}
            Sample(0,0,false);
        }
        RawImage Make(string name)
        {
            var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(transform,false);
            var r=(RectTransform)go.transform;r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=r.offsetMax=Vector2.zero;
            var im=go.AddComponent<RawImage>();im.raycastTarget=false;return im;
        }
        // Authored row bounds: the generated sheet is not an exact uniform grid.
        static readonly float[] RowCuts={0,320f/1254,633f/1254,947f/1254,1};
        // Insets prevent neighboring atlas cells bleeding through bilinear sampling.
        public static Rect UV(int frame,Texture texture)
        {
            frame=Mathf.Clamp(frame,0,15);float px=2f/texture.width,py=2f/texture.height;
            int row=frame/4;float top=RowCuts[row],bottom=RowCuts[row+1];
            return new Rect((frame%4)*.25f+px,1-bottom+py,.25f-2*px,bottom-top-2*py);
        }
        public void Sample(float time,int variant,bool reduced,float opacity=1)
        {
            if(!Ready)return;var p=CelebrationMotion.Daria(time,variant,reduced);
            if(blendMaterial){var a=UV(p.frame,front.texture);var b=UV(p.nextFrame,front.texture);
                front.uvRect=new Rect(0,0,1,1);blendMaterial.SetVector("_FrameA",new Vector4(a.x,a.y,a.width,a.height));
                blendMaterial.SetVector("_FrameB",new Vector4(b.x,b.y,b.width,b.height));blendMaterial.SetFloat("_Blend",p.blend);}
            else front.uvRect=UV(p.blend<.5f?p.frame:p.nextFrame,front.texture);
            front.color=new Color(1,1,1,opacity);front.rectTransform.anchoredPosition=new Vector2(p.sway,p.lift);
            front.rectTransform.localRotation=Quaternion.Euler(0,0,p.angle);front.rectTransform.localScale=Vector3.one*p.scale;
        }
        void OnDestroy(){if(blendMaterial)Destroy(blendMaterial);}
    }
}
