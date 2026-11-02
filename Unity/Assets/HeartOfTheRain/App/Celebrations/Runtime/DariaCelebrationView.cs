using UnityEngine;
using UnityEngine.UI;
namespace HeartOfTheRain.App.Celebrations
{
    // M68 sampled mesh replaces the old cutout rig; no recalculated arm pivots.
    public sealed class DariaCelebrationView:MonoBehaviour
    {
        M68CelebrationAssets data;M68MeshGraphic mesh;RawImage still;
        public bool Ready=>mesh&&still;
        public void Configure(Texture2D legacyAtlas){Configure(CelebrationAssets.Load());}
        public void Configure(CelebrationAssets ignored)
        {
            if(Ready)return;data=M68CelebrationAssets.Load();if(!data)return;
            var m=Child("M68 authored mesh");mesh=m.gameObject.AddComponent<M68MeshGraphic>();mesh.Configure(data);
            var s=Child("M68 reduced motion");still=s.gameObject.AddComponent<RawImage>();still.texture=data.reduced;still.raycastTarget=false;Sample(0,0,false,0);
        }
        RectTransform Child(string label){var go=new GameObject(label,typeof(RectTransform));go.transform.SetParent(transform,false);var r=(RectTransform)go.transform;r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=r.offsetMax=Vector2.zero;return r;}
        public void SampleLevel(float time,bool reduced,float fade=1)
        {
            if(!Ready)return;mesh.enabled=!reduced;still.enabled=reduced;
            if(reduced){float a=Mathf.Clamp01(time/.18f)*(1-Mathf.Clamp01((time-1.68f)/.20f));still.color=new Color(1,1,1,a*fade);}
            else {int frame=M68CelebrationAssets.Frame(time);mesh.Sample(frame,data.Clip.samples[frame].opacity*fade);}
        }
        // Dialogue holds authored sample188 instead of looping or fading out.
        public void Sample(float time,int variant,bool reduced,float opacity=1)
        {if(!Ready)return;mesh.enabled=!reduced;still.enabled=reduced;if(reduced)still.color=new Color(1,1,1,opacity);else mesh.Sample(Mathf.Clamp(12+Mathf.FloorToInt(time*60),12,188),opacity);}
    }
}
