using System;
using HeartOfTheRain.M05;
using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;

namespace HeartOfTheRain.M07.Editor
{
    public static class ImpactReviewBaker
    {
        const string Root = "Assets/HeartOfTheRain/Chapter01M07";

        [MenuItem("Heart of the Rain/M07/Bake native sprite clips")]
        static void Bake()
        {
            // Generate into a new folder every time so existing authored assets stay intact.
            string output = Root + "/Baked_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff");
            Directory.CreateDirectory(output); AssetDatabase.Refresh();
            foreach (string direction in new[] { "BombFX", "RocketFX", "FragmentsV0", "FragmentsV1", "FragmentsV2", "WoodFX", "StarFX", "RocketBombBody", "RocketBombFX", "DoubleBombBody", "DoubleBombFX", "DoubleRocketBody", "DoubleRocketFX", "RainbowOrbBody", "RainbowOrbFX", "RainbowOrbImpact", "OrbRocketBody", "OrbRocketFX", "OrbBombBody", "OrbBombFX", "DoubleOrbBody", "DoubleOrbFX", "DoubleOrbWave", "RainSeekerBody", "RainSeekerFX", "RainSeekerRocketH", "RainSeekerRocketV", "RainSeekerRocketFX", "RainSeekerBombBody", "RainSeekerBombFX", "DoubleRainSeekerBody", "DoubleRainSeekerFX", "OrbRainSeekerBody", "OrbRainSeekerFX", "GoldenSeekerBody", "GoldenSeekerTwin" })
            {
                var atlas = AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "/Sprites/" + direction + "_Atlas.png");
                var json = AssetDatabase.LoadAssetAtPath<TextAsset>(Root + "/Data/" + direction + ".json");
                var data = JsonUtility.FromJson<SpriteManifest>(json.text);
                if (atlas.width != data.atlasWidth || atlas.height != data.atlasHeight)
                    throw new InvalidOperationException("Atlas was resized on import; set max size to at least the manifest atlas dimensions (4096 for fragments and DoubleOrbWave).");
                var set = ScriptableObject.CreateInstance<RenderedFrameSet>();
                set.frames = new Sprite[data.frames.Length]; set.clips = new AnimationClip[data.clips.Length];
                string setPath = output + "/" + direction + ".asset";
                AssetDatabase.CreateAsset(set, setPath);
                for (int i = 0; i < set.frames.Length; i++)
                {
                    var f = data.frames[i];
                    var sprite = Sprite.Create(atlas, new Rect(f.x, f.y, f.width, f.height), new Vector2(.5f,.5f),
                        data.pixelsPerUnit, 0, SpriteMeshType.FullRect);
                    sprite.name = f.name; AssetDatabase.AddObjectToAsset(sprite, set); set.frames[i] = sprite;
                }
                var controller = AnimatorController.CreateAnimatorControllerAtPath(output + "/" + direction + ".controller");
                var machine = controller.layers[0].stateMachine;
                for (int i = 0; i < data.clips.Length; i++)
                {
                    var c = data.clips[i];
                    var clip = new AnimationClip { name = c.name, frameRate = c.fps };
                    var keys = new ObjectReferenceKeyframe[c.count + 1];
                    for (int j = 0; j < c.count; j++)
                        keys[j] = new ObjectReferenceKeyframe { time = j / c.fps, value = set.frames[c.start + j] };
                    keys[c.count] = new ObjectReferenceKeyframe { time = c.Duration,
                        value = set.frames[c.start + (c.loop ? 0 : c.count - 1)] };
                    AnimationUtility.SetObjectReferenceCurve(clip,
                        EditorCurveBinding.PPtrCurve("", typeof(SpriteRenderer), "m_Sprite"), keys);
                    var settings = AnimationUtility.GetAnimationClipSettings(clip);
                    settings.loopTime = c.loop; AnimationUtility.SetAnimationClipSettings(clip, settings);
                    if(c.name.StartsWith("GS_"))
                    {
                        float visualScale=(c.name=="GS_Shadow"||c.name=="GS_TwinFlash")?1f:1.4f;
                        foreach(string axis in new[]{"x","y","z"})AnimationUtility.SetEditorCurve(clip,EditorCurveBinding.FloatCurve("",typeof(Transform),"m_LocalScale."+axis),AnimationCurve.Constant(0,c.Duration,visualScale));
                    }
                    AssetDatabase.CreateAsset(clip, output + "/" + direction + "_" + c.name + ".anim");
                    set.clips[i] = clip;
                    var state = machine.AddState(c.name); state.motion = clip;
                    if (c.name == "Idle" || c.name == "Armed" || c.name == "RS_Idle" || c.name == "GS_Idle") machine.defaultState = state;
                }
                var idle = machine.defaultState;
                foreach (var child in machine.states)
                    if (direction == "Bomb" && child.state != idle && child.state.name != "Detonate")
                    {
                        var transition = child.state.AddTransition(idle);
                        transition.hasExitTime = true; transition.exitTime = 1; transition.duration = 0;
                    }
                var go = new GameObject(direction + "_Baked");
                if (direction == "RainSeekerBody" || direction == "RainSeekerRocketH" || direction == "RainSeekerRocketV" || direction == "RainSeekerBombBody" || direction == "DoubleRainSeekerBody" || direction == "OrbRainSeekerBody" || direction == "GoldenSeekerBody" || direction == "GoldenSeekerTwin") go.transform.localScale = Vector3.one * 1.4f;
                var renderer = go.AddComponent<SpriteRenderer>(); renderer.sprite = set.frames[0]; renderer.sortingOrder = 20;
                renderer.sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>("Assets/HeartOfTheRain/Chapter01M04/Materials/SpriteUnlit.mat");
                go.AddComponent<Animator>().runtimeAnimatorController = controller;
                PrefabUtility.SaveAsPrefabAsset(go, output + "/" + direction + ".prefab");
                UnityEngine.Object.DestroyImmediate(go); EditorUtility.SetDirty(set);
            }
            AssetDatabase.SaveAssets(); AssetDatabase.Refresh();
            Debug.Log("M07 native sprites, clips, controllers, and prefabs created in " + output);
        }

        [MenuItem("Heart of the Rain/M25/Open Rain Seeker review")]
        static void OpenRainSeeker()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Prefabs/Demo_9x9_RainSeeker.prefab");
            Selection.activeGameObject = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            Debug.Log("M25 Rain Seeker R3: press Play, or disable play and adjust scrubTime. Change columns, rows, origin and seekerTarget to review other layouts.");
        }

        [MenuItem("Heart of the Rain/M26/Open Rain Seeker + Rocket review")]
        static void OpenRainSeekerRocket()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Prefabs/Demo_9x9_RainSeekerRocket_H.prefab");
            Selection.activeGameObject = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            Debug.Log("M26 Rain Seeker + Rocket R1: press Play, or disable play and adjust scrubTime. Change columns, rows, origin, seekerTarget and rocketVertical to review other layouts.");
        }

        [MenuItem("Heart of the Rain/M27/Open Rain Seeker + Bomb review")]
        static void OpenRainSeekerBomb()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Prefabs/Demo_9x9_RainSeekerBomb.prefab");
            Selection.activeGameObject = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            Debug.Log("M27 Rain Seeker + Bomb R1: press Play, or disable play and adjust scrubTime. Change columns, rows, origin and seekerTarget to review other layouts.");
        }

        [MenuItem("Heart of the Rain/M28/Open Double Rain Seeker review")]
        static void OpenDoubleRainSeeker()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Prefabs/Demo_9x9_DoubleRainSeeker.prefab");
            Selection.activeGameObject = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            Debug.Log("M28 Double Rain Seeker R1: press Play, or disable play and adjust scrubTime. Change columns, rows, origin and seekerTarget to review other layouts.");
        }

        [MenuItem("Heart of the Rain/M29/Open Orb + Rain Seeker review")]
        static void OpenOrbRainSeeker()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Prefabs/Demo_9x9_OrbRainSeeker.prefab");
            Selection.activeGameObject = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            Debug.Log("M29 Orb + Rain Seeker R1: press Play, or disable play and adjust scrubTime. Change columns, rows, origin and targetColor to review other layouts.");
        }

        [MenuItem("Heart of the Rain/M30/Open Golden Seeker review")]
        static void OpenGoldenSeeker()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Prefabs/Demo_9x9_GoldenSeeker.prefab");
            Selection.activeGameObject = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            Debug.Log("M30 Golden Seeker R1: press Play, or disable play and adjust scrubTime. Change columns, rows, origin and seekerTarget to review other layouts.");
        }

        [MenuItem("Heart of the Rain/M31/Open Double Orb Super design review")]
        static void OpenDoubleOrbSuper()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Prefabs/Demo_9x9_DoubleRainbow.prefab");
            Selection.activeGameObject = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            Debug.Log("M31: two normal Rainbow Orbs merge into the rotating Super Orb design. Press Play or adjust scrubTime.");
        }

        [MenuItem("Heart of the Rain/M07/Open 2D asset demo")]
        static void OpenDemo()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Prefabs/Demo_9x9_BombChain.prefab");
            Selection.activeGameObject = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            Debug.Log("Press Play. Board dimensions and effect can be changed on BoardReactionReview.");
        }
    }
}
