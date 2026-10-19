using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using HeartOfTheRain.M05;

namespace HeartOfTheRain.M07.Editor
{
    public static class PowerUpsFinalReview
    {
        const string Root="Assets/HeartOfTheRain/Chapter01M07";
        [Serializable] public class BombFixture {public bool blockers;public ReviewPlan plan;}
        [MenuItem("Heart of the Rain/Power-Ups/Open Playback Gallery")]
        public static void Open()
        {
            if(!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())return;
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"/Prefabs/PowerUpPlaybackGallery.prefab");
            if(prefab==null)throw new InvalidOperationException("Import the complete final power-up package first.");
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            Selection.activeGameObject=(GameObject)PrefabUtility.InstantiatePrefab(prefab);
            Debug.Log("Final power-up gallery: press Play. Board playback and Animation library provide selection, play/pause, replay, frame stepping, speed, scrubbing and board size controls.");
        }
        [MenuItem("Heart of the Rain/Power-Ups/Validate Complete Package")]
        public static void Validate()
        {
            ReviewPlanValidation.Validate();GoldenSeekerComboValidation.Validate();
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"/Prefabs/PowerUpPlaybackGallery.prefab");
            if(prefab==null)throw new InvalidOperationException("Missing playback prefab");
            var board=prefab.GetComponent<BoardReactionReview>();var gallery=prefab.GetComponent<PowerUpPlaybackGallery>();
            if(board==null||gallery==null||gallery.board!=board||gallery.catalog==null||board.atlases.Length!=42||board.manifests.Length!=42||board.referenceTiles.Length!=6)
                throw new InvalidOperationException("Gallery bindings are incomplete");
            var data=JsonUtility.FromJson<PowerUpGalleryCatalog>(gallery.catalog.text);var kinds=new HashSet<int>();
            if(data.entries.Length!=22||data.library.Length!=40)throw new InvalidOperationException("Approved inventory differs");
            foreach(var entry in data.entries)
            {
                if(!kinds.Add(entry.kind))throw new InvalidOperationException("Duplicate gallery entry");
                foreach(var size in new[]{new Vector2Int(9,9),new Vector2Int(9,11),new Vector2Int(11,11)})
                {
                    var plan=ReviewPlan.Build(size.x,size.y,entry.kind,new Vector2Int(-1,-1),true,entry.targetColor);
                    foreach(var e in plan.effects)
                    {
                        if(e.atlas<0||e.atlas>=42)throw new InvalidOperationException("Atlas index invalid");
                        var manifest=JsonUtility.FromJson<SpriteManifest>(board.manifests[e.atlas].text);
                        if(Array.Find(manifest.clips,c=>c.name==e.clip)==null)throw new InvalidOperationException("Missing clip "+e.clip);
                    }
                }
            }
            int clips=0;
            foreach(var item in data.library)
            {
                var m=JsonUtility.FromJson<SpriteManifest>(board.manifests[item.atlas].text);
                if(board.atlases[item.atlas].width!=m.atlasWidth||board.atlases[item.atlas].height!=m.atlasHeight||item.clipLabels.Length!=m.clips.Length)
                    throw new InvalidOperationException("Animation library binding differs");
                clips+=m.clips.Length;
            }
            int bombs=0;
            foreach(string guid in AssetDatabase.FindAssets("t:TextAsset",new[]{Root+"/Data"}))
            {
                string path=AssetDatabase.GUIDToAssetPath(guid);if(!System.IO.Path.GetFileName(path).StartsWith("FinalBomb_"))continue;
                var fixture=JsonUtility.FromJson<BombFixture>(AssetDatabase.LoadAssetAtPath<TextAsset>(path).text);var e=fixture.plan;
                var a=ReviewPlan.Build(e.columns,e.rows,21,new Vector2Int(e.originX,e.originY),fixture.blockers);
                if(a.powers.Length!=1||a.powers[0].atlas!=6||a.blasts.Length!=1||a.tiles.Length!=e.tiles.Length||a.effects.Length!=e.effects.Length)
                    throw new InvalidOperationException("Single Bomb inventory differs");
                for(int i=0;i<a.tiles.Length;i++)
                {
                    var x=a.tiles[i];var y=e.tiles[i];
                    if(x.x!=y.x||x.y!=y.y||x.tile!=y.tile||x.reserved!=y.reserved||x.wood!=y.wood||x.incoming!=y.incoming||Mathf.Abs(x.hit-y.hit)>.0001f||Mathf.Abs(x.fallStart-y.fallStart)>.0001f||Mathf.Abs(x.destY-y.destY)>.0001f)
                        throw new InvalidOperationException("Single Bomb tile timeline differs");
                }
                for(int i=0;i<a.effects.Length;i++)
                {
                    var x=a.effects[i];var y=e.effects[i];
                    if(x.atlas!=y.atlas||x.clip!=y.clip||Mathf.Abs(x.start-y.start)>.0001f||Mathf.Abs(x.duration-y.duration)>.0001f)
                        throw new InvalidOperationException("Single Bomb effect differs");
                }
                bombs++;
            }
            if(bombs!=18)throw new InvalidOperationException("Expected 18 single-bomb comparison fixtures");
            Debug.Log("Final power-up package PASS: 22 board entries, "+clips+" approved animation clips, 18 single-bomb fixtures and all legacy/Golden gates.");
        }
    }
}
