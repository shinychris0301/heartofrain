#if UNITY_EDITOR
using System;using System.Linq;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;
namespace HeartOfTheRain.M46.Editor {
    public static class M46ReviewMenu {
        const string Root="Assets/HeartOfTheRain/M46/";
        [MenuItem("Heart of the Rain/M46/Open Playable Review")]
        public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene(Root+"Scenes/M46_Playable_Review.unity");}
        [MenuItem("Heart of the Rain/M46/Rebuild Review Scene")]
        public static void Rebuild(){if(!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())return;var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);var go=new GameObject("M46 Playable Review");go.AddComponent<M46Playground>().assets=AssetDatabase.LoadAssetAtPath<M46Assets>(Root+"M46Assets.asset");EditorSceneManager.SaveScene(scene,Root+"Scenes/M46_Playable_Review.unity");}
        [MenuItem("Heart of the Rain/M46/Validate Assets and Gameplay")]
        public static void Validate(){var assets=AssetDatabase.LoadAssetAtPath<M46Assets>(Root+"M46Assets.asset");if(assets==null)throw new InvalidOperationException("M46 asset configuration missing");int cases=0;
            if(assets.powerAtlases.Length!=42||assets.obstacleClips.Length!=86||assets.bodies.Length!=20||assets.levels.Length!=4)throw new InvalidOperationException("Incomplete bindings");
            for(int i=0;i<42;i++){var m=JsonUtility.FromJson<HeartOfTheRain.M05.SpriteManifest>(assets.powerManifests[i].text);if(assets.powerAtlases[i].width!=m.atlasWidth||assets.powerAtlases[i].height!=m.atlasHeight)throw new InvalidOperationException("Atlas was resized: "+assets.powerAtlases[i].name);}
            foreach(var c in assets.obstacleClips){var m=JsonUtility.FromJson<ClipData>(c.metadata.text);foreach(var f in m.frames){var t=c.pages[f.page];if(f.x<0||f.y<0||f.x+f.w>t.width||f.y+f.h>t.height)throw new InvalidOperationException("Invalid frame: "+c.key);}}
            foreach(var text in assets.levels){var l=JsonUtility.FromJson<LevelData>(text.text);var b=new BoardModel(l);var move=b.LegalSwaps().First();var r=b.Swap(move[0].x,move[0].y,move[1].x,move[1].y);if(!r.accepted||b.Status=="Resolution limit")throw new InvalidOperationException("Swap resolution failed");b.Validate();cases++;
                foreach(int kind in new[]{4,5,7,11,16,21}){b=new BoardModel(l);var p=b.Pieces.Values.First(p=>p.family=="gem");b.InjectReviewPower(p.x,p.y,kind);r=b.Tap(p.x,p.y);if(!r.accepted||b.Status=="Resolution limit")throw new InvalidOperationException("Power resolution failed");b.Validate();cases++;}}
            Debug.Log("M46 PASS: 4 level bindings, 20 bodies, 42 power atlases, 86 obstacle clips; "+cases+" gameplay smoke cases. Run the scene and device checks in Documentation before release.");
        }
    }
}
#endif
