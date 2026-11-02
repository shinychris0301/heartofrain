using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.M47 {
    // Approved PNG alpha bounds (>24/255), normalized to the source canvas.
    // Full-rect sprite meshes include transparent padding. Static measurements
    // avoid texture readbacks, readable imports and per-frame allocations.
    public static class GoalIconLayout106 {
        public const float VisibleSize=58,SlotSize=60,GoalTop=63,GoalHeight=94;
        public const float CounterTop=60,CounterHeight=26,CounterPeakScale=1.16f;
        static Rect Pixels(float left,float top,float right,float bottom,float width,float height)=>new Rect(left/width,top/height,(right-left)/width,(bottom-top)/height);
        public static Rect VisibleBounds(string id){
            switch(id){
                case "crate_1":return Pixels(36,40,477,469,512,512);
                case "moss_1":return Pixels(94,110,418,401,512,512);
                case "stone_1":return Pixels(94,99,418,413,512,512);
                case "pail_Full":return Pixels(119,116,393,400,512,512);
                case "case_1":return Pixels(98,112,414,398,512,512);
                case "gate_1":return Pixels(94,108,418,403,512,512);
                case "crystalIcon":return Pixels(36,3,449,780,484,780);
                case "waterSpirit":return Pixels(36,40,476,472,512,512);
                case "rainlight":return Pixels(11,11,326,535,336,547);
                default:return new Rect(0,0,1,1);
            }
        }
        public static void Fit(Image image,string id){
            if(!image||!image.sprite)return;
            var bounds=VisibleBounds(id);var source=image.sprite.rect;
            float scale=VisibleSize/Mathf.Max(source.width*bounds.width,source.height*bounds.height);
            float width=source.width*scale,height=source.height*scale;
            var rect=image.rectTransform;rect.anchorMin=rect.anchorMax=rect.pivot=new Vector2(0,1);
            rect.sizeDelta=new Vector2(width,height);
            rect.anchoredPosition=new Vector2(SlotSize*.5f-width*bounds.center.x,height*bounds.center.y-SlotSize*.5f);
            image.preserveAspect=true;image.raycastTarget=false;
        }
        public static float CounterWidth(float slotWidth)=>Mathf.Max(1,(slotWidth-4)/CounterPeakScale);
    }
}
