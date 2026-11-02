#if UNITY_EDITOR
using System;
using System.IO;
using System.Text;
using System.Xml;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build;

namespace HeartOfTheRain.App.Launch.Editor
{
    // Native layout only: copy the approved PNG byte-for-byte, then inset it
    // with Android drawables. Never repaint/cut out the user's artwork.
    public sealed class AndroidLaunch99 : IPostGenerateGradleAndroidProject
    {
        public int callbackOrder => 120;
        public const string IconPath = "Assets/HeartOfTheRain/App/Launch/Art/App_Icon_R1.png";
        public const string AndroidNamespace = "http://schemas.android.com/apk/res/android";
        public const string LauncherInset = "20.37037%"; // 64 of the108-layer units.
        public const string StartupInset = "16.666667%"; // fits the system's2/3 icon mask.
        // Exact existing artwork's top-left pixel, not a new palette choice.
        public const string IconSapphire = "#032A8C";

        public void OnPostGenerateGradleAndroidProject(string path) => Apply(path);

        public static void Apply(string unityLibrary)
        {
            string source = Path.GetFullPath(IconPath);
            if (!File.Exists(source)) throw new BuildFailedException("Approved Heart of the Rain icon is missing.");
            string resources = Path.Combine(unityLibrary, "src/main/res");
            string original = Path.Combine(resources, "drawable-nodpi/hotr_icon_original99.png");
            Directory.CreateDirectory(Path.GetDirectoryName(original)); File.Copy(source, original, true);
            Write(resources, "values/hotr_launch99.xml", "<resources>\n"
                + "<color name=\"hotr_icon_sapphire99\">" + IconSapphire + "</color>\n"
                + "<bool name=\"hotr_curtain_enabled99\">" + ((!PlayerSettings.SplashScreen.show && !PlayerSettings.SplashScreen.showUnityLogo) ? "true" : "false") + "</bool>\n"
                + "<style name=\"HeartRainLaunch99Base\" parent=\"@style/UnityThemeSelector\"><item name=\"android:windowBackground\">@drawable/hotr_start_background99</item></style>\n"
                + "<style name=\"HeartRainLaunch99\" parent=\"@style/HeartRainLaunch99Base\"/>\n</resources>");
            Write(resources, "drawable/hotr_start_background99.xml", "<layer-list xmlns:android=\"" + AndroidNamespace + "\">"
                + "<item android:drawable=\"@android:color/black\"/>"
                + "<item android:width=\"192dp\" android:height=\"192dp\" android:gravity=\"center\"><bitmap android:src=\"@drawable/hotr_icon_original99\" android:gravity=\"fill\" android:filter=\"true\"/></item></layer-list>");
            Write(resources, "drawable/hotr_start_icon99.xml", Inset(StartupInset));
            Write(resources, "mipmap-anydpi-v26/hotr_launcher_icon99.xml", "<adaptive-icon xmlns:android=\"" + AndroidNamespace + "\">"
                + "<background android:drawable=\"@color/hotr_icon_sapphire99\"/><foreground>" + Inset(LauncherInset) + "</foreground></adaptive-icon>");
            Write(resources, "values-v31/hotr_launch99.xml", "<resources>"
                + "<style name=\"HeartRainLaunch99Api31\" parent=\"@style/HeartRainLaunch99Base\">"
                + "<item name=\"android:windowBackground\">@android:color/black</item>"
                + "<item name=\"android:windowSplashScreenBackground\">@android:color/black</item>"
                + "<item name=\"android:windowSplashScreenAnimatedIcon\">@drawable/hotr_start_icon99</item>"
                + "<item name=\"android:windowSplashScreenBrandingImage\">@android:color/transparent</item></style>"
                + "<style name=\"HeartRainLaunch99\" parent=\"@style/HeartRainLaunch99Api31\"/></resources>");
            Write(resources, "values-v33/hotr_launch99.xml", "<resources><style name=\"HeartRainLaunch99\" parent=\"@style/HeartRainLaunch99Api31\">"
                + "<item name=\"android:windowSplashScreenBehavior\">icon_preferred</item></style></resources>");

            string manifest = Path.Combine(unityLibrary, "src/main/AndroidManifest.xml");
            var document = new XmlDocument { PreserveWhitespace = true }; document.Load(manifest);
            XmlElement player = null;
            foreach (XmlNode node in document.SelectNodes("/manifest/application/activity"))
                if (node is XmlElement element && element.GetAttribute("name", AndroidNamespace) == "com.unity3d.player.UnityPlayerActivity") player = element;
            if (player == null) throw new BuildFailedException("Expected existing Unity activity is missing; no launch activity replacement is permitted.");
            Set(player, "theme", "@style/HeartRainLaunch99"); document.Save(manifest);

            string launcher = Path.Combine(Path.GetDirectoryName(unityLibrary), "launcher/src/main/AndroidManifest.xml");
            var launchDocument = new XmlDocument { PreserveWhitespace = true }; launchDocument.Load(launcher);
            var application = launchDocument.SelectSingleNode("/manifest/application") as XmlElement;
            if (application == null) throw new BuildFailedException("Generated launcher application is missing.");
            Set(application, "icon", "@mipmap/hotr_launcher_icon99"); Set(application, "roundIcon", "@mipmap/hotr_launcher_icon99");
            launchDocument.Save(launcher);
        }

        static string Inset(string fraction) => "<inset xmlns:android=\"" + AndroidNamespace + "\" android:insetLeft=\"" + fraction
            + "\" android:insetTop=\"" + fraction + "\" android:insetRight=\"" + fraction + "\" android:insetBottom=\"" + fraction
            + "\"><bitmap android:src=\"@drawable/hotr_icon_original99\" android:gravity=\"fill\" android:filter=\"true\"/></inset>";
        static void Write(string root, string relative, string value)
        {
            string path = Path.Combine(root, relative); Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" + value + "\n", new UTF8Encoding(false));
        }
        static void Set(XmlElement element, string name, string value)
        {
            var attribute = element.OwnerDocument.CreateAttribute("android", name, AndroidNamespace); attribute.Value = value; element.Attributes.SetNamedItem(attribute);
        }
    }
}
#endif
