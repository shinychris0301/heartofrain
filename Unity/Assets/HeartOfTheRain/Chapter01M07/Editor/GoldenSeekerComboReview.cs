using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace HeartOfTheRain.M07.Editor
{
    public static class GoldenSeekerComboReview
    {
        const string Root="Assets/HeartOfTheRain/Chapter01M07/Prefabs/";
        static void Open(string name)
        {
            if(!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())return;
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"Demo_9x9_"+name+".prefab");
            if(prefab==null)throw new InvalidOperationException("Import the complete M32 Assets folder first.");
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            Selection.activeGameObject=(GameObject)PrefabUtility.InstantiatePrefab(prefab);
            Debug.Log("M32: press Play. Change columns/rows, origin, targetColor or rocketVertical on BoardReactionReview. Disable play and use scrubTime to inspect a frame.");
        }
        [MenuItem("Heart of the Rain/M32/Golden Seeker + Rocket")]
        public static void Rocket(){Open("GoldenSeekerRocket_H");}
        [MenuItem("Heart of the Rain/M32/Golden Seeker + Bomb")]
        public static void Bomb(){Open("GoldenSeekerBomb");}
        [MenuItem("Heart of the Rain/M32/Golden Seeker + Rain Seeker")]
        public static void Rain(){Open("GoldenRainSeeker");}
        [MenuItem("Heart of the Rain/M32/Golden Seeker + Rainbow Orb")]
        public static void Orb(){Open("OrbGoldenSeeker");}
    }
}
