using System;
namespace HeartOfTheRain.App.Celebrations
{
    [Serializable] public struct DariaPose
    {
        public int frame, nextFrame;
        public float blend, lift, sway, angle, scale;
    }
    [Serializable] public struct FinalePose {public int beat;public float mix,dariaAlpha,wellZoom,hookZoom;public DariaPose daria;}
    public static class CelebrationMotion
    {
        // Sixteen genuine poses, timed for anticipation, two claps and a soft open-palmed settle.
        public const float DariaDuration=2.48f;
        static readonly float[] Times={0,.12f,.25f,.36f,.43f,.54f,.66f,.80f,.96f,1.08f,1.20f,1.32f,1.50f,1.74f,2.08f,2.48f};
        public static DariaPose Daria(float seconds,int variant,bool reduced)
        {
            if(reduced||seconds>=DariaDuration)return new DariaPose{frame=15,nextFrame=15,scale=1};
            float t=Math.Max(0,seconds);int at=0;while(at<14&&t>=Times[at+1])at++;
            // Fast hand gestures use brief transitions, preventing prolonged translucent duplicate hands.
            float window=(at==6||at==7||at==11||at==12)?.025f:.055f;
            window=Math.Min(window,Times[at+1]-Times[at]);
            float u=Math.Max(0,Math.Min(1,(t-(Times[at+1]-window))/window));u=u*u*(3-2*u);
            float envelope=(float)Math.Sin(Math.PI*t/DariaDuration),direction=variant%2==0?1:-1;
            return new DariaPose{frame=at,nextFrame=at+1,blend=u,
                lift=envelope*(2.5f+1.4f*(float)Math.Sin(t*9)),sway=direction*envelope*(float)Math.Sin(t*3)*1.8f,
                angle=direction*envelope*(float)Math.Sin(t*4)*.8f,scale=1+.007f*envelope*(float)Math.Sin(t*7)};
        }
        public const float FinaleDuration=9.4f;
        public static FinalePose Finale(float seconds,bool reduced)
        {
            float t=Math.Max(0,Math.Min(FinaleDuration,seconds));
            return new FinalePose {beat=Beat(t),mix=HookMix(t,reduced),dariaAlpha=DariaAlpha(t,reduced),
                daria=Daria(Math.Max(0,t-2.4f),0,reduced),
                wellZoom=reduced?1:1+.025f*Math.Min(1,t/5),
                hookZoom=reduced?1:1+.018f*Math.Max(0,Math.Min(1,(t-5)/4.4f))};
        }
        public static int Beat(float seconds) {return seconds<2.4f?0:seconds<5f?1:2;}
        public static float HookMix(float seconds,bool reduced)
        {return reduced?(seconds>=5?1:0):Math.Max(0,Math.Min(1,(seconds-5)/.65f));}
        public static float DariaAlpha(float seconds,bool reduced)
        {
            if(reduced)return seconds>=2.4f&&seconds<5?1:0;
            return Math.Min(Math.Max(0,Math.Min(1,(seconds-2.2f)/.35f)),1-Math.Max(0,Math.Min(1,(seconds-4.8f)/.35f)));
        }
        public static bool ShouldPlayFinale(int level,bool firstClear,int completedAfter)
        {return level>0&&firstClear&&level%50==0&&completedAfter>=level;}
        public static int FirstLevel(int chapter) {return chapter>0?(chapter-1)*50+1:0;}
        public static int LastLevel(int chapter) {return chapter>0?chapter*50:0;}
    }
    [Serializable] public struct CelebrationGeometry
    {
        public float width,height,stageX,stageY,stageW,stageH,captionX,captionY,captionW,captionH;
        public float dariaX,dariaY,dariaSize,buttonX,buttonY,buttonW;
        public bool landscape;
        public static CelebrationGeometry Build(float width,float height)
        {
            var g=new CelebrationGeometry {width=Math.Max(320,width),height=Math.Max(320,height)};
            g.landscape=g.width/g.height>1.25f;
            g.captionW=g.landscape?Math.Min(330,g.width*.43f):Math.Min(520,g.width-28);
            g.captionH=g.landscape?Math.Min(210,g.height-110):182;
            g.captionX=g.landscape?g.width-g.captionW-16:(g.width-g.captionW)/2;
            g.captionY=g.height-g.captionH-18;
            g.stageX=0;g.stageY=0;g.stageW=g.landscape?g.width-g.captionW-28:g.width;g.stageH=g.height;
            g.dariaSize=g.landscape?Math.Min(g.stageW*.73f,g.height*.70f):Math.Min(g.stageW*.77f,Math.Max(1,g.captionY-100));
            g.dariaX=Math.Max(6,(g.stageW-g.dariaSize)*.12f);
            g.dariaY=(g.landscape?g.height-18:g.captionY+4)-g.dariaSize;
            g.buttonW=Math.Min(226,g.captionW-36);g.buttonX=g.captionX+(g.captionW-g.buttonW)/2;
            g.buttonY=g.captionY+g.captionH-66;
            return g;
        }
    }
    // Uses active playback time. Backgrounding never consumes the story duration.
    public sealed class CelebrationPlaybackSession
    {
        public float Elapsed {get;private set;}
        public bool Active {get;private set;}
        public bool Open(){if(Active)return false;Elapsed=0;Active=true;return true;}
        public void Advance(float delta,bool focused){if(!Active||!focused||float.IsNaN(delta)||float.IsInfinity(delta)||delta<=0)return;Elapsed=Math.Min(CelebrationMotion.FinaleDuration,Elapsed+delta);}
        public bool Close(){if(!Active)return false;Active=false;return true;}
    }

}
