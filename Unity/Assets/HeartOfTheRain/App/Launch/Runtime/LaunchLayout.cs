using UnityEngine;

namespace HeartOfTheRain.App.Launch
{
    public struct LaunchFrame
    {
        public Rect art, uv, logo, footer, track, status;
        public bool contain;
    }

    public static class LaunchLayout
    {
        public static LaunchFrame Build(float width,float height,Rect safe)
        {
            width=Mathf.Max(1,width);height=Mathf.Max(1,height);
            if(safe.width<=0||safe.height<=0)safe=new Rect(0,0,width,height);
            const float aspect=941f/1672;
            var f=new LaunchFrame{contain=width/height>=.68f,uv=new Rect(0,0,1,1)};
            if(f.contain)
            {
                float h=Mathf.Min(height,width/aspect),w=h*aspect;
                f.art=new Rect((width-w)/2,(height-h)/2,w,h);
            }
            else
            {
                f.art=new Rect(0,0,width,height);
                float visible=width/height/aspect;
                if(visible<1)f.uv=new Rect((1-visible)/2,0,visible,1);
                else {visible=1/visible;f.uv=new Rect(0,(1-visible)/2,1,visible);}
            }
            float left=Mathf.Max(safe.xMin,f.art.xMin),right=Mathf.Min(safe.xMax,f.art.xMax);
            float bottom=Mathf.Max(safe.yMin,f.art.yMin),top=Mathf.Min(safe.yMax,f.art.yMax);
            float sw=Mathf.Max(1,right-left),sh=Mathf.Max(1,top-bottom),cx=(left+right)/2;
            float lw=sw*.8f,lh=Mathf.Min(sh*.16f,lw/2);lw=lh*2;
            f.logo=new Rect(cx-lw/2,top-sh*.025f-lh,lw,lh);
            float fh=Mathf.Clamp(sh*.12f,58,120),fy=bottom+sh*.025f;
            f.footer=new Rect(cx-sw*.45f,fy,sw*.9f,fh);
            float th=sw*.62f/20f;
            f.track=new Rect(cx-sw*.31f,fy+fh*.66f,sw*.62f,th);
            f.status=new Rect(cx-sw*.43f,fy+fh*.10f,sw*.86f,fh*.5f);
            return f;
        }
    }
}
