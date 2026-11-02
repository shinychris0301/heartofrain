using System;
using UnityEngine;
namespace HeartOfTheRain.M47 {
    // Extend the safe-area projection to the full framebuffer. Its original
    // world-to-screen mapping stays identical inside the safe area.
    public struct FullDisplayBoardView {
        public float halfHeight;
        public Vector2 center;
        public static FullDisplayBoardView Compute(float width,float height,Rect safe,float safeHalfHeight,float safeCenterY){
            if(width<=0||height<=0||safeHalfHeight<=0)throw new ArgumentOutOfRangeException("Invalid display or board projection");
            if(safe.width<=0||safe.height<=0)safe=new Rect(0,0,width,height);
            float unitsPerPixel=2*safeHalfHeight/safe.height;
            return new FullDisplayBoardView{halfHeight=unitsPerPixel*height*.5f,center=new Vector2((width*.5f-safe.center.x)*unitsPerPixel,safeCenterY+(height*.5f-safe.center.y)*unitsPerPixel)};
        }
    }
}
