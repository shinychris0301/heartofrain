#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.App.Launch;
using HeartOfTheRain.App.UIClarity;

namespace HeartOfTheRain.Verification
{
    public static class RussianLaunch80Configuration
    {
        [Serializable] sealed class Report
        {
            public string utc,unity,status,productName,logoGuid,error;
            public bool hasProLicense,splashRemovalSupported,showSplashScreen,showUnityLogo;
            public int importErrors;
            public string scope="Native pinned Editor settings/readback. Entitlement is reported only as a boolean; no license data is recorded. Unsupported Unity2022 splash removal is retained as a limitation; no engine/license modification or runtime bypass.";
        }
        public static void Configure()
        {
            var report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,status="FAIL_RUSSIAN_LAUNCH80_CONFIGURATION"};
            try
            {
                if(Application.unityVersion!="2022.3.62f3")throw new InvalidOperationException("Pinned editor required");
                if(PlayerSettings.productName!="Сердце дождя")throw new InvalidOperationException("Russian visible app name is missing");
                report.hasProLicense=UnityEditorInternal.InternalEditorUtility.HasPro();
                if(report.hasProLicense)
                {
                    PlayerSettings.SplashScreen.show=false;
                    PlayerSettings.SplashScreen.showUnityLogo=false;
                    AssetDatabase.SaveAssets();
                }
                report.productName=PlayerSettings.productName;
                report.showSplashScreen=PlayerSettings.SplashScreen.show;
                report.showUnityLogo=PlayerSettings.SplashScreen.showUnityLogo;
                report.splashRemovalSupported=report.hasProLicense&&!report.showSplashScreen&&!report.showUnityLogo;
                report.logoGuid=AssetDatabase.AssetPathToGUID(HeartOfTheRain.App.Launch.Editor.LaunchSetup.TitlePath);
                if(report.logoGuid!="dbf14ca73e245a739834a16d7faa3b82")throw new InvalidOperationException("Russian logo GUID changed");
                System.Text.StringBuilder log;
                var errors=UIClarityGuard.Validate(out log);
                report.importErrors=errors.Count;
                string output=Path.GetFullPath("../Verification/Evidence/LaunchRuStoreR3/Native");Directory.CreateDirectory(output);
                File.WriteAllText(Path.Combine(output,"Import_Audit.txt"),log+"\nErrors: "+errors.Count+"\n"+string.Join("\n",errors));
                if(errors.Count>0)throw new InvalidOperationException("UI clarity import policy failed");
                if(report.hasProLicense&&!report.splashRemovalSupported)throw new InvalidOperationException("Splash settings did not retain the supported disabled state");
                report.status=report.splashRemovalSupported?"PASS_RUSSIAN_LAUNCH80_SPLASH_DISABLED":"PASS_RUSSIAN_LAUNCH80_BRANDING_SPLASH_ENTITLEMENT_REQUIRED";
            }
            catch(Exception error){report.error=error.ToString();}
            string folder=Path.GetFullPath("../Verification/Evidence/LaunchRuStoreR3/Native");Directory.CreateDirectory(folder);
            File.WriteAllText(Path.Combine(folder,"Configuration.json"),JsonUtility.ToJson(report,true));
            if(Application.isBatchMode)EditorApplication.Exit(report.error==null?0:1);
        }
    }
}
#endif
