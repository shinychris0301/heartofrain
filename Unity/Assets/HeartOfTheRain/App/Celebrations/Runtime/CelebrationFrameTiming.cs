using System;
namespace HeartOfTheRain.App.Celebrations
{
    [Serializable] public struct CelebrationTimingReport {public int frames,framesOver33ms;public float seconds,averageFps,worstFrameMs;}
    // Measures actual Update cadence in Unity; offline pose samples are never fed into this monitor.
    public sealed class CelebrationFrameTiming
    {
        int count,slow;float seconds,worst;
        public void Reset(){count=slow=0;seconds=worst=0;}
        public void Record(float delta,bool active){if(!active||delta<=0||float.IsNaN(delta)||float.IsInfinity(delta))return;count++;seconds+=delta;worst=Math.Max(worst,delta);if(delta>1f/30)slow++;}
        public CelebrationTimingReport Report=>new CelebrationTimingReport{frames=count,framesOver33ms=slow,seconds=seconds,averageFps=seconds>0?count/seconds:0,worstFrameMs=worst*1000};
    }
}
