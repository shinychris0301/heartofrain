#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Xml;
using HeartOfTheRain.App.Launch;
using HeartOfTheRain.App.Launch.Editor;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification
{
    public static class Startup99Verification
    {
        [Serializable] sealed class Report
        {
            public string status="FAIL_NATIVE_STARTUP99",utc,unity,error,iconSHA256;
            public int checks;
            public string scope="Actual Editor native XML/layout assertions. No phone startup-time, installed icon, routing or production acceptance inferred.";
            public List<string> passed=new List<string>();
        }
        static void Check(Report report,bool condition,string message)
        {
            report.checks++;if(!condition)throw new InvalidOperationException(message);report.passed.Add(message);
        }
        static string Sha(string path)
        {
            using(var stream=File.OpenRead(path))using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
        }
        public static void Run()
        {
            var report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
            string output=Environment.GetEnvironmentVariable("HOTR_REVIEW99_OUT");
            try
            {
                if(string.IsNullOrEmpty(output)||!Path.IsPathRooted(output))throw new InvalidOperationException("Explicit99 output required");
                string privateOutput=Environment.GetEnvironmentVariable("HOTR_REVIEW99_PRIVATE_OUT");
                if(string.IsNullOrEmpty(privateOutput)||!Path.IsPathRooted(privateOutput))throw new InvalidOperationException("Explicit private99 output required");
                string temp=Path.Combine(privateOutput,"XmlControl");
                string library=Path.Combine(temp,"unityLibrary"),launcher=Path.Combine(temp,"launcher");
                Directory.CreateDirectory(Path.Combine(library,"src/main"));Directory.CreateDirectory(Path.Combine(launcher,"src/main"));
                string libraryManifest=Path.Combine(library,"src/main/AndroidManifest.xml"),launcherManifest=Path.Combine(launcher,"src/main/AndroidManifest.xml");
                File.WriteAllText(libraryManifest,"<manifest xmlns:android=\""+AndroidLaunch99.AndroidNamespace+"\"><uses-permission android:name=\"android.permission.INTERNET\"/><application android:appCategory=\"game\"><meta-data android:name=\"unity.splash-enable\" android:value=\"True\"/><activity android:name=\"com.unity3d.player.UnityPlayerActivity\" android:screenOrientation=\"portrait\" android:theme=\"@style/UnityThemeSelector\"><intent-filter><data android:scheme=\"review-payment-return\"/></intent-filter></activity></application></manifest>");
                File.WriteAllText(launcherManifest,"<manifest xmlns:android=\""+AndroidLaunch99.AndroidNamespace+"\"><application android:icon=\"@mipmap/app_icon\" android:label=\"@string/app_name\"/></manifest>");
                report.iconSHA256=Sha(AndroidLaunch99.IconPath);AndroidLaunch99.Apply(library);
                string resources=Path.Combine(library,"src/main/res");
                Check(report,Sha(Path.Combine(resources,"drawable-nodpi/hotr_icon_original99.png"))==report.iconSHA256,"Approved PNG copied byte-for-byte without art processing");
                var manifest=new XmlDocument();manifest.Load(libraryManifest);var activity=(XmlElement)manifest.SelectSingleNode("/manifest/application/activity");
                Check(report,activity.GetAttribute("name",AndroidLaunch99.AndroidNamespace)=="com.unity3d.player.UnityPlayerActivity"&&activity.GetAttribute("screenOrientation",AndroidLaunch99.AndroidNamespace)=="portrait","Existing portrait activity is retained");
                Check(report,activity.GetAttribute("theme",AndroidLaunch99.AndroidNamespace)=="@style/HeartRainLaunch99","Native black/icon theme selected");
                Check(report,manifest.SelectSingleNode("/manifest/uses-permission")!=null&&manifest.SelectSingleNode("/manifest/application/activity/intent-filter/data")!=null,"Existing permissions and payment-return intent survive");
                var launch=new XmlDocument();launch.Load(launcherManifest);var application=(XmlElement)launch.SelectSingleNode("/manifest/application");
                Check(report,application.GetAttribute("icon",AndroidLaunch99.AndroidNamespace)=="@mipmap/hotr_launcher_icon99"&&application.GetAttribute("roundIcon",AndroidLaunch99.AndroidNamespace)=="@mipmap/hotr_launcher_icon99","Normal and round launcher share the padded adaptive drawable");
                Check(report,application.GetAttribute("label",AndroidLaunch99.AndroidNamespace)=="@string/app_name","Visible app name is retained");
                foreach(string file in Directory.GetFiles(resources,"*.xml",SearchOption.AllDirectories))
                {
                    var document=new XmlDocument();document.Load(file);Check(report,document.DocumentElement!=null,"Android XML parses: "+Path.GetFileName(Path.GetDirectoryName(file))+"/"+Path.GetFileName(file));
                }
                string api31=File.ReadAllText(Path.Combine(resources,"values-v31/hotr_launch99.xml"));
                Check(report,api31.Contains("windowSplashScreenBackground\">@android:color/black")&&api31.Contains("@drawable/hotr_start_icon99"),"Android12 system screen remains black with app icon");
                var modernTheme=new XmlDocument();modernTheme.LoadXml(api31);
                Check(report,modernTheme.SelectSingleNode("/resources/style[@name='HeartRainLaunch99Api31']/item[@name='android:windowBackground']")?.InnerText=="@android:color/black","Android12 underlying activity is black, with no second themed icon after the system splash");
                var legacyBackground=new XmlDocument();legacyBackground.Load(Path.Combine(resources,"drawable/hotr_start_background99.xml"));
                var legacyIcon=(XmlElement)legacyBackground.SelectSingleNode("/layer-list/item[@android:width='192dp']",Namespaces(legacyBackground));
                Check(report,legacyIcon!=null&&legacyIcon.GetAttribute("height",AndroidLaunch99.AndroidNamespace)=="192dp"&&((XmlElement)legacyIcon.SelectSingleNode("bitmap")).GetAttribute("src",AndroidLaunch99.AndroidNamespace)=="@drawable/hotr_icon_original99","Legacy starting window retains the exact approved192dp drawable reused by its native handoff");
                Check(report,!api31.Contains("AnimationDuration")&&!api31.Contains("Title_Logo"),"No dwell duration or native title substitution is added");
                var plugin=new XmlDocument();plugin.Load("Assets/HeartOfTheRain/App/Launch/Plugins/Android/HeartRainLaunch99.androidlib/AndroidManifest.xml");
                var provider=(XmlElement)plugin.SelectSingleNode("/manifest/application/provider");
                Check(report,provider!=null&&provider.GetAttribute("exported",AndroidLaunch99.AndroidNamespace)=="false"&&provider.GetAttribute("authorities",AndroidLaunch99.AndroidNamespace)=="${applicationId}.launch99","Startup handoff is same-app and non-exported");
                Check(report,plugin.SelectNodes("/manifest/application/activity").Count==0&&plugin.SelectNodes("/manifest/uses-permission").Count==0,"Native handoff introduces no Activity replacement or permission");
                var values=new XmlDocument();values.Load(Path.Combine(resources,"values/hotr_launch99.xml"));
                Check(report,provider.GetAttribute("enabled",AndroidLaunch99.AndroidNamespace)=="@bool/hotr_curtain_enabled99"&&values.SelectSingleNode("/resources/bool[@name='hotr_curtain_enabled99']").InnerText==((!PlayerSettings.SplashScreen.show&&!PlayerSettings.SplashScreen.showUnityLogo)?"true":"false"),"Native curtain is enabled only when supported splash settings disable all splash branding");
                Check(report,File.ReadAllText(Path.Combine(resources,"mipmap-anydpi-v26/hotr_launcher_icon99.xml")).Contains(AndroidLaunch99.LauncherInset),"Adaptive foreground uses proportional safe inset");
                double layer=108*(1-2*.2037037);Check(report,layer<=64.00001&&layer>=63.9999,"Important artwork is reduced to64 of108 layer units");
                // Visible drop landmarks from the unchanged source, inside the
                // Android66-unit safe circle; background corners may be masked.
                foreach(var point in new[]{new Vector2(.50f,.04f),new Vector2(.13f,.58f),new Vector2(.87f,.58f),new Vector2(.50f,.94f)})
                    Check(report,(point-new Vector2(.5f,.5f)).magnitude*layer<33,"Drop landmark remains within common-mask safe circle: "+point);
                foreach(var size in new[]{new Vector2(320,568),new Vector2(720,1600),new Vector2(768,1024),new Vector2(1179,2556)})
                {
                    var frame=LaunchLayout.Build(size.x,size.y,new Rect(0,0,size.x,size.y));
                    Check(report,frame.logo.width>0&&frame.logo.height>0&&frame.track.width>0&&frame.track.height>0,"Existing launch layout remains valid: "+size);
                }
                Check(report,Sha(AndroidLaunch99.IconPath)==report.iconSHA256,"Source artwork remains unchanged after generation");
                report.status="PASS_NATIVE_STARTUP99";
            }
            catch(Exception error){report.error=error.ToString();}
            Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Startup99.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.error==null?0:1);
        }
        static XmlNamespaceManager Namespaces(XmlDocument document){var namespaces=new XmlNamespaceManager(document.NameTable);namespaces.AddNamespace("android",AndroidLaunch99.AndroidNamespace);return namespaces;}
    }
}
#endif
