#if UNITY_EDITOR
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace HeartOfTheRain.App.Home.Editor
{
    public static class HomePageEditor
    {
        private const string Root = "Assets/HeartOfTheRain/App/Home";
        [MenuItem("Heart of the Rain/App/M55/Open Home Review")]
        public static void OpenReview()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.OpenScene(Root + "/Scenes/M55_Home_Review.unity");
        }
        [MenuItem("Heart of the Rain/App/M55/Refresh Home Asset Bindings")]
        public static void RefreshBindings()
        {
            var asset = AssetDatabase.LoadAssetAtPath<HomePageAssets>(Root + "/HomePageAssets.asset");
            if (asset == null) { asset = ScriptableObject.CreateInstance<HomePageAssets>(); AssetDatabase.CreateAsset(asset,Root+"/HomePageAssets.asset"); }
            asset.layout = AssetDatabase.LoadAssetAtPath<TextAsset>(Root + "/Data/Home_Layout.json");
            asset.previewState = AssetDatabase.LoadAssetAtPath<TextAsset>(Root + "/Data/Home_Preview_State.json");
            asset.boldFont = AssetDatabase.LoadAssetAtPath<Font>(Root + "/Fonts/HomeRounded-Black.ttf");
            asset.regularFont = AssetDatabase.LoadAssetAtPath<Font>(Root + "/Fonts/HomeRounded-ExtraBold.ttf");
            asset.sprites = AssetDatabase.FindAssets("t:Sprite", new[]{Root+"/Art"}).Select(g => AssetDatabase.GUIDToAssetPath(g)).Distinct().Where(p=>System.IO.Path.GetFileName(p).StartsWith("R4_")||System.IO.Path.GetFileName(p).StartsWith("Chapter01_")||System.IO.Path.GetFileName(p)=="R3_Header.png").OrderBy(p=>p).Select(p => new HomeSprite { id=System.IO.Path.GetFileNameWithoutExtension(p), sprite=AssetDatabase.LoadAssetAtPath<Sprite>(p) }).ToArray();
            asset.chapterBackground = asset.Find("Chapter01_VillageWell");
            EditorUtility.SetDirty(asset); AssetDatabase.SaveAssets();
            Selection.activeObject = asset;
        }
    }
}
#endif
