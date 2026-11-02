#if UNITY_EDITOR
using System;
using System.IO;
using System.Xml;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.App.Editor;

namespace HeartOfTheRain.Verification
{
    public static class PortraitVerification
    {
        [Serializable] public sealed class Report {public string status,utc,scope="Native pinned Unity Player Settings and generated-manifest policy checks. Real Android launch/rotation evidence is separate.";public int checks;public string[] failures;}
        public static void ConfigureAndRun(){PortraitBuildPolicy.Configure();AssetDatabase.SaveAssets();Run();}
        public static void Run()
        {
            var report=new Report{utc=DateTime.UtcNow.ToString("o")};var failures=new List<string>();
            void Check(bool ok,string label){report.checks++;if(!ok)failures.Add(label);}
            try{
                Check(Application.unityVersion=="2022.3.62f3","Pinned engine");Check(PortraitBuildPolicy.IsPortraitOnly,"Default orientation and allowed rotation flags are portrait-only");
                Check(PlayerSettings.defaultInterfaceOrientation==UIOrientation.Portrait,"Portrait default");Check(PlayerSettings.allowedAutorotateToPortrait,"Portrait allowed");Check(!PlayerSettings.allowedAutorotateToPortraitUpsideDown,"Reverse portrait disabled");Check(!PlayerSettings.allowedAutorotateToLandscapeLeft&&!PlayerSettings.allowedAutorotateToLandscapeRight,"Both landscapes disabled");
                var document=new XmlDocument();document.LoadXml("<manifest xmlns:android='http://schemas.android.com/apk/res/android'><uses-permission android:name='android.permission.INTERNET'/><application android:label='existing'><meta-data android:name='existing' android:value='keep'/><activity android:name='com.unity3d.player.UnityPlayerActivity' android:screenOrientation='portrait' android:configChanges='orientation|screenSize' android:resizeableActivity='false'><meta-data android:name='unityplayer.UnityActivity' android:value='true'/></activity></application></manifest>");
                string ns=PortraitBuildPolicy.AndroidNamespace;var app=(XmlElement)document.SelectSingleNode("/manifest/application");var player=(XmlElement)app.SelectSingleNode("activity");PortraitBuildPolicy.ApplyManifest(document);
                Check(app.GetAttribute("appCategory",ns)=="game","Large-screen game classification");Check(player.GetAttribute("screenOrientation",ns)=="portrait","Activity remains portrait");Check(player.GetAttribute("configChanges",ns)=="orientation|screenSize","Unity configuration callbacks preserved");Check(player.GetAttribute("resizeableActivity",ns)=="false","Resizability preserved");Check(app.GetAttribute("label",ns)=="existing"&&app.SelectSingleNode("meta-data")!=null,"Existing label and metadata preserved");Check(document.SelectSingleNode("/manifest/uses-permission")!=null,"Permissions preserved");
                string once=document.OuterXml;PortraitBuildPolicy.ApplyManifest(document);Check(document.OuterXml==once,"Manifest policy is idempotent");
                foreach(string bad in new[]{"fullUser","landscape","sensorPortrait",""}){player.SetAttribute("screenOrientation",ns,bad);bool rejected=false;try{PortraitBuildPolicy.ApplyManifest(document);}catch(UnityEditor.Build.BuildFailedException){rejected=true;}Check(rejected,"Reject non-portrait activity: "+bad);}
                app.RemoveChild(player);bool missing=false;try{PortraitBuildPolicy.ApplyManifest(document);}catch(UnityEditor.Build.BuildFailedException){missing=true;}Check(missing,"Reject missing Unity player activity");
            }catch(Exception ex){failures.Add(ex.ToString());}
            report.failures=failures.ToArray();report.status=failures.Count==0?"PASS_NATIVE_PORTRAIT_CHECKS":"FAIL_NATIVE_PORTRAIT_CHECKS";string output=Path.GetFullPath("../Verification/Evidence/Portrait");Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Native_Checks.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(failures.Count==0?0:1);
        }
    }
}
#endif
