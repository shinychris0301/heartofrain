using System.Diagnostics;
using System.Globalization;
using UnityEngine;

namespace HeartOfTheRain.App.Launch
{
    // Bounded development diagnostics. No timers, profile mutation, fake progress
    // or readiness signal is manufactured by this logger.
    public static class StartupMilestones99
    {
        public static void SubmitLogoFrame()
        {
#if UNITY_ANDROID && !UNITY_EDITOR
            try
            {
                using(var unity=new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
                using(var activity=unity.GetStatic<AndroidJavaObject>("currentActivity"))
                using(var resources=activity.Call<AndroidJavaObject>("getResources"))
                {
                    string package=activity.Call<string>("getPackageName");
                    int enabled=resources.Call<int>("getIdentifier","hotr_curtain_enabled99","bool",package);
                    if(enabled!=0&&resources.Call<bool>("getBoolean",enabled))
                    using(var resolver=activity.Call<AndroidJavaObject>("getContentResolver"))
                    using(var uriClass=new AndroidJavaClass("android.net.Uri"))
                    using(var uri=uriClass.CallStatic<AndroidJavaObject>("parse","content://"+package+".launch99"))
                    using(var extras=new AndroidJavaObject("android.os.Bundle"))
                    using(var result=resolver.Call<AndroidJavaObject>("call",uri,"logo_frame_submitted99","",extras))
                    {
                        if(result==null||!result.Call<bool>("getBoolean","accepted"))UnityEngine.Debug.LogError("Native startup curtain did not accept its first-frame signal.");
                    }
                }
            }
            catch(AndroidJavaException error){UnityEngine.Debug.LogError("Native startup curtain handoff failed: "+error.Message);}
#endif
            Mark("launch_frame_submitted");
        }
        [Conditional("UNITY_EDITOR"), Conditional("DEVELOPMENT_BUILD")]
        public static void Mark(string stage)
        {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            double monotonic = Stopwatch.GetTimestamp() * 1000.0 / Stopwatch.Frequency;
            UnityEngine.Debug.Log("HOTR_STARTUP99 stage=" + stage + " monotonicMs=" + monotonic.ToString("F3", CultureInfo.InvariantCulture)
                + " realtimeMs=" + (Time.realtimeSinceStartupAsDouble * 1000).ToString("F3", CultureInfo.InvariantCulture) + " frame=" + Time.frameCount);
#endif
        }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSplashScreen)]
        static void BeforeSplash() => Mark("managed_before_splash");
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void BeforeScene() => Mark("before_first_scene");
#endif
    }
}
