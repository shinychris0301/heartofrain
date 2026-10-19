#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
namespace HeartOfTheRain.App.Home.Editor
{
    [CustomEditor(typeof(HomePage))]
    public sealed class HomeReviewInspector : UnityEditor.Editor
    {
        private int level=18,coins=1250,lives=5,completed=17;
        public override void OnInspectorGUI()
        {
            DrawDefaultInspector();
            var home=(HomePage)target;
            EditorGUILayout.Space();EditorGUILayout.LabelField("Home R3 review",EditorStyles.boldLabel);
            EditorGUILayout.HelpBox("Enter Play mode to review Home. Resize Game view or rotate the device; layout follows Screen.safeArea. Route requests are recorded below. Other pages are approval-gated and are not built by this Home screen.",MessageType.Info);
            if(!Application.isPlaying)return;
            EditorGUILayout.LabelField("Last request",home.LastRequestedAction??"None");
            level=EditorGUILayout.IntField("Level",level);coins=EditorGUILayout.IntField("Coins",coins);
            lives=EditorGUILayout.IntField("Lives",lives);completed=EditorGUILayout.IntSlider("Chapter progress",completed,0,50);
            if(GUILayout.Button("Apply review state"))
            {
                var next=JsonUtility.FromJson<HomeState>(JsonUtility.ToJson(home.State));
                next.currentLevel=level;next.coins=coins;next.lives=lives;next.completedLevelsInChapter=completed;home.ApplyState(next);
            }
            if(GUILayout.Button(home.EventsOpen?"Close events drawer":"Open events drawer"))home.ShowEvents(!home.EventsOpen);
            if(GUILayout.Button("Reset 18 / 1,250 / 5 lives / 17 of 50"))home.ApplyState(new HomeState());
            EditorGUILayout.HelpBox("Set UI Scale Override to 3 for a 1179 × 2556 phone Game view; 1 for a 393 × 852 logical view. Use Device Simulator for real safe insets. Native screen reader support is a separate integration.",MessageType.None);
        }
    }
}
#endif
