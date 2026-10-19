using System;
namespace HeartOfTheRain.App.Celebrations
{
    [Serializable] public struct VictoryGeometry
    {
        public float width,height,size,x,y;
        public static VictoryGeometry Build(float width,float height)
        {
            var g=new VictoryGeometry{width=Math.Max(1,width),height=Math.Max(1,height)};
            g.size=Math.Min(620,Math.Min(g.width*.86f,g.height*.58f));
            g.x=(g.width-g.size)/2;g.y=(g.height-g.size)*.43f;return g;
        }
    }
    [Serializable] public struct VictoryPose {public float alpha,dim,scale,lift,haloAlpha,haloScale,haloAngle;}
    [Serializable] public struct VictoryParticle {public float x,y,width,height,angle,alpha;public int color;public bool star;}
    public static class VictoryMotion
    {
        public const float Duration=3.5f,ReducedDuration=1.6f,SkipAfter=.65f;
        public const int ParticleCount=52;
        public static float Clamp(float v){return Math.Max(0,Math.Min(1,v));}
        public static float Smooth(float v){v=Clamp(v);return v*v*(3-2*v);}
        public static VictoryPose Sample(float time,bool reduced)
        {
            float duration=reduced?ReducedDuration:Duration;
            float alpha=Smooth(time/.18f)*(1-Smooth((time-duration+.35f)/.35f));
            if(reduced)return new VictoryPose{alpha=alpha,dim=.22f*alpha,scale=1,haloScale=1,haloAlpha=.22f*alpha};
            float u=Clamp((time-.08f)/.58f),back=1+2.70158f*(float)Math.Pow(u-1,3)+1.70158f*(float)Math.Pow(u-1,2);
            return new VictoryPose{alpha=alpha,dim=.24f*alpha,scale=.83f+.17f*back,
                lift=24*(1-Smooth(time/.6f)),haloAlpha=.31f*alpha*(.93f+.07f*(float)Math.Sin(time*3)),
                haloScale=1.05f+.035f*(float)Math.Sin(time*2),haloAngle=time*12};
        }
        public static VictoryParticle Particle(float time,int i,VictoryGeometry g,bool reduced)
        {
            bool star=i%5==0;float delay=.12f+(i%8)*.027f,t=Math.Max(0,time-delay);
            float lane=(i*.61803399f)%1,side=i%2==0?-1:1;
            float x=g.width*.5f+side*g.width*(.10f+lane*.38f)*Math.Min(1,t*2)+(float)Math.Sin(t*3+i)*g.width*.025f;
            float y=g.height*.38f-g.height*(.30f+(i%7)*.032f)*t+g.height*.25f*t*t;
            float size=star?9+(i%4)*2:5+i%4;
            return new VictoryParticle{x=x,y=y,width=size*(star?1:.2f+.8f*Math.Abs((float)Math.Cos(t*7+i))),height=size*(star?1:1.7f),
                angle=i*37+t*(side*100),alpha=reduced||time<delay?0:Smooth(t/.1f)*Math.Min(1,Math.Max(0,(g.height+24-y)/30)),color=i%3,star=star};
        }
    }
    // This gate owns only presentation time, never rewards or progression.
    public sealed class VictoryPlaybackSession
    {
        public bool Active{get;private set;}public float Elapsed{get;private set;}
        public bool Reduced{get;private set;}
        public bool Finished=>Elapsed>=(Reduced?VictoryMotion.ReducedDuration:VictoryMotion.Duration);
        public bool CanSkip=>Active&&Elapsed>=VictoryMotion.SkipAfter;
        public bool Open(bool reduced){if(Active)return false;Active=true;Elapsed=0;Reduced=reduced;return true;}
        public void Advance(float delta,bool focused){if(!Active||!focused||float.IsNaN(delta)||float.IsInfinity(delta)||delta<=0)return;Elapsed=Math.Min(Reduced?VictoryMotion.ReducedDuration:VictoryMotion.Duration,Elapsed+delta);}
        public bool Close(){if(!Active)return false;Active=false;return true;}
    }
}
