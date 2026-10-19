using System;
using System.Collections.Generic;
using UnityEngine;
using Manifest = HeartOfTheRain.M05.SpriteManifest;
namespace HeartOfTheRain.M46 {
    [Serializable] public class BodyAsset {public string key;public Texture2D texture;public string resource;public float canvasCells=1;}
    [Serializable] public class ClipAsset {public string key;public TextAsset metadata;public Texture2D[] pages;public string[] pageResources;}
    [Serializable] public class ProfileAsset {public string family;public TextAsset metadata;}
    [CreateAssetMenu(menuName="Heart of the Rain/M46 assets")]
    public sealed class M46Assets:ScriptableObject {
        public TextAsset[] levels;public Texture2D[] surfaces,masks;public Texture2D exitMarker;
        public BodyAsset[] bodies;public Texture2D[] powerAtlases;public TextAsset[] powerManifests;public string[] powerResources,surfaceResources,maskResources;
        public ClipAsset[] obstacleClips;public ProfileAsset[] debrisProfiles;public Material effectsMaterial,tileGlowMaterial;
    }
    [Serializable] public class ClipFrame {public int page,x,y,w,h;}
    [Serializable] public class ClipData {public int fps,framePixels;public float canvasCells,pixelsPerUnit;public bool loop,holdLast;public ClipFrame[] frames;}
}
