using System;
using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;

namespace HeartOfTheRain.M05.Editor
{
    public static class BombSpriteBaker
    {
        const string Root = "Assets/HeartOfTheRain/Chapter01M05";

        [MenuItem("Heart of the Rain/M05/Bake native sprite clips")]
        static void Bake()
        {
            // Generate into a new folder every time so existing authored assets stay intact.
            string output = Root + "/Baked_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff");
            Directory.CreateDirectory(output); AssetDatabase.Refresh();
            foreach (string direction in new[] { "Bomb", "ExplosionFX", "ExplosionDetail", "Blocker", "Combo_BombBomb", "Combo_RocketBomb" })
            {
                var atlas = AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "/Sprites/" + direction + "_Atlas.png");
                var json = AssetDatabase.LoadAssetAtPath<TextAsset>(Root + "/Data/" + direction + ".json");
                var data = JsonUtility.FromJson<SpriteManifest>(json.text);
                if (atlas.width != data.atlasWidth || atlas.height != data.atlasHeight)
                    throw new InvalidOperationException("Atlas was resized on import; set max size to 2048 or larger.");
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
                    AssetDatabase.CreateAsset(clip, output + "/" + direction + "_" + c.name + ".anim");
                    set.clips[i] = clip;
                    var state = machine.AddState(c.name); state.motion = clip;
                    if (c.name == "Idle" || c.name == "Armed") machine.defaultState = state;
                }
                var idle = machine.defaultState;
                foreach (var child in machine.states)
                    if (direction == "Bomb" && child.state != idle && child.state.name != "Detonate")
                    {
                        var transition = child.state.AddTransition(idle);
                        transition.hasExitTime = true; transition.exitTime = 1; transition.duration = 0;
                    }
                var go = new GameObject(direction + "_Baked");
                var renderer = go.AddComponent<SpriteRenderer>(); renderer.sprite = set.frames[0]; renderer.sortingOrder = 20;
                renderer.sharedMaterial = AssetDatabase.LoadAssetAtPath<Material>("Assets/HeartOfTheRain/Chapter01M04/Materials/SpriteUnlit.mat");
                go.AddComponent<Animator>().runtimeAnimatorController = controller;
                PrefabUtility.SaveAsPrefabAsset(go, output + "/" + direction + ".prefab");
                UnityEngine.Object.DestroyImmediate(go); EditorUtility.SetDirty(set);
            }
            AssetDatabase.SaveAssets(); AssetDatabase.Refresh();
            Debug.Log("M05 native sprites, clips, controllers, and prefabs created in " + output);
        }

        [MenuItem("Heart of the Rain/M05/Open 2D asset demo")]
        static void OpenDemo()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Prefabs/Demo_9x9_Bomb.prefab");
            Selection.activeGameObject = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            Debug.Log("Press Play. Board dimensions and effect can be changed on BombBoardPreview.");
        }
    }
}
