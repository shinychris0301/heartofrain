using System;using System.Linq;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;
namespace HeartOfTheRain.M47 {
 public static class GameplayMenu {
  const string Root="Assets/HeartOfTheRain/M47/";
  [MenuItem("Heart of the Rain/M47/Open Chapter 1 Gameplay")]
  public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene(Root+"Scenes/Chapter01_Gameplay.unity");}
  [MenuItem("Heart of the Rain/M47/Validate UI and Chapter Assets")]
  public static void Validate(){var a=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>(Root+"GameplayUIAssets.asset");if(a==null||a.boards==null)throw new Exception("Missing UI/board assets");if(a.boards.levels.Length!=50||a.boards.surfaces.Length!=50||a.boards.masks.Length!=50)throw new Exception("Expected all 50 authored boards");if(a.regular==null||a.bold==null)throw new Exception("Font imports missing");foreach(var s in a.sprites)if(s.sprite==null)throw new Exception("Missing sprite "+s.id);foreach(var s in a.sounds)if(s.clip==null)throw new Exception("Missing sound "+s.id);foreach(var l in a.boards.levels){var data=JsonUtility.FromJson<HeartOfTheRain.M46.LevelData>(l.text);var model=new HeartOfTheRain.M46.BoardModel(data);model.Validate();if(model.LegalSwaps().Count==0)throw new Exception("No opening move "+data.id);}Debug.Log("M47: 50 boards and all UI/audio bindings loaded. Perform visual and device checks separately.");}
  [MenuItem("Heart of the Rain/M47/Rebuild Gameplay Scene")]
  public static void Build(){if(!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())return;var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);var go=new GameObject("Chapter 1 Gameplay");var screen=go.AddComponent<GameplayScreen>();screen.uiAssets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>(Root+"GameplayUIAssets.asset");screen.initialLevel=1;PrefabUtility.SaveAsPrefabAsset(go,Root+"Prefabs/Chapter01_Gameplay.prefab");EditorSceneManager.SaveScene(scene,Root+"Scenes/Chapter01_Gameplay.unity");Selection.activeGameObject=go;}
 }
}
