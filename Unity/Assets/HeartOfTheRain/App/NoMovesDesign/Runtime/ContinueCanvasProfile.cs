using UnityEngine;
using UnityEngine.UI;
namespace HeartOfTheRain.NoMovesUI
{
    // The app's device profile should set tabletLayout on tablets. No unreliable DPI guesses.
    // Remove this component + the dedicated Canvas if embedding in an already configured root canvas.
    [RequireComponent(typeof(CanvasScaler))]
    public sealed class ContinueCanvasProfile : MonoBehaviour
    {
        public bool tabletLayout;
        int width,height;bool wasTablet;
        void OnEnable(){Apply();}
        void LateUpdate(){if(width!=Screen.width||height!=Screen.height||wasTablet!=tabletLayout)Apply();}
        void Apply()
        {
            width=Screen.width;height=Screen.height;wasTablet=tabletLayout;
            var s=GetComponent<CanvasScaler>();s.referencePixelsPerUnit=100;s.matchWidthOrHeight=0;
            s.referenceResolution=tabletLayout?(width>height?new Vector2(1024,768):new Vector2(768,1024)):
                width>height?new Vector2(852,393):new Vector2(393,852);
            foreach(var image in GetComponentsInChildren<Image>(true))image.SetVerticesDirty();
        }
    }
}
