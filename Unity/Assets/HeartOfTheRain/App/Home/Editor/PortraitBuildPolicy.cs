using System;
using System.IO;
using System.Xml;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;

namespace HeartOfTheRain.App.Editor
{
    public sealed class PortraitBuildPolicy : IPreprocessBuildWithReport, IPostGenerateGradleAndroidProject
    {
        public int callbackOrder=>100;
        public const string AndroidNamespace="http://schemas.android.com/apk/res/android";

        public static void Configure()
        {
            PlayerSettings.defaultInterfaceOrientation=UIOrientation.Portrait;
            PlayerSettings.allowedAutorotateToPortrait=true;
            PlayerSettings.allowedAutorotateToPortraitUpsideDown=false;
            PlayerSettings.allowedAutorotateToLandscapeLeft=false;
            PlayerSettings.allowedAutorotateToLandscapeRight=false;
        }

        public static bool IsPortraitOnly=>PlayerSettings.defaultInterfaceOrientation==UIOrientation.Portrait&&PlayerSettings.allowedAutorotateToPortrait&&!PlayerSettings.allowedAutorotateToPortraitUpsideDown&&!PlayerSettings.allowedAutorotateToLandscapeLeft&&!PlayerSettings.allowedAutorotateToLandscapeRight;

        public void OnPreprocessBuild(BuildReport report)
        {
            if((report.summary.platform==BuildTarget.Android||report.summary.platform==BuildTarget.iOS)&&!IsPortraitOnly)
                throw new BuildFailedException("Heart of the Rain requires portrait-only Player Settings. Run PortraitBuildPolicy.Configure before building.");
        }

        public void OnPostGenerateGradleAndroidProject(string path)
        {
            string manifest=Path.Combine(path,"src/main/AndroidManifest.xml");
            var document=new XmlDocument{PreserveWhitespace=true};document.Load(manifest);
            ApplyManifest(document);document.Save(manifest);
        }

        // Keep Unity's generated activity, permissions and metadata. Explicitly
        // classify this game for Android's large-screen game compatibility rules.
        public static void ApplyManifest(XmlDocument document)
        {
            var app=document.SelectSingleNode("/manifest/application") as XmlElement;
            if(app==null)throw new BuildFailedException("Generated Android manifest has no application.");
            XmlElement player=null;
            foreach(XmlNode node in app.ChildNodes){var activity=node as XmlElement;if(activity!=null&&activity.Name=="activity"&&activity.GetAttribute("name",AndroidNamespace)=="com.unity3d.player.UnityPlayerActivity")player=activity;}
            if(player==null||player.GetAttribute("screenOrientation",AndroidNamespace)!="portrait")
                throw new BuildFailedException("Generated Unity activity must request portrait before packaging.");
            var category=document.CreateAttribute("android","appCategory",AndroidNamespace);category.Value="game";app.Attributes.SetNamedItem(category);
        }
    }
}
