using System;
using System.Collections.Generic;
using UnityEngine;

namespace HeartOfTheRain.M04
{
    [Serializable] public class SpriteFrame { public string name; public int x, y, width, height; }
    [Serializable] public class SpriteSequence
    {
        public string name; public int start, count; public float fps; public bool loop;
        public float Duration => count / fps;
    }
    [Serializable] public class SpriteManifest
    {
        public int atlasWidth, atlasHeight; public float pixelsPerUnit;
        public SpriteFrame[] frames; public SpriteSequence[] clips;
    }

    /// <summary>Plays rendered 2D frames. No runtime meshes, lights, or image warping.</summary>
    [DisallowMultipleComponent]
    public sealed class RocketSpritePlayer : MonoBehaviour
    {
        public Texture2D atlas;
        public TextAsset manifest;
        public Material unlitMaterial;
        public string initialClip = "Idle";
        public bool playOnEnable = true;
        public bool returnToIdle = true;
        public bool useUnscaledTime;
        public int sortingOrder = 20;
        public SpriteRenderer Renderer { get; private set; }
        public bool IsPlaying { get; private set; }
        public event Action<string> Completed;

        sealed class SharedFrames
        {
            public SpriteManifest data; public Sprite[] sprites; public int users;
        }
        static readonly Dictionary<string, SharedFrames> Cache = new Dictionary<string, SharedFrames>();
        SharedFrames shared;
        string cacheKey;
        SpriteSequence current;
        float elapsed;
        int shown = -1;

        public bool Initialize()
        {
            if (shared != null) return true;
            if (atlas == null || manifest == null) return false;
            Renderer = GetComponent<SpriteRenderer>();
            if (Renderer == null) Renderer = gameObject.AddComponent<SpriteRenderer>();
            Renderer.sortingOrder = sortingOrder;
            if (unlitMaterial != null) Renderer.sharedMaterial = unlitMaterial;
            cacheKey = atlas.GetInstanceID() + ":" + manifest.GetInstanceID();
            if (!Cache.TryGetValue(cacheKey, out shared))
            {
                var data = JsonUtility.FromJson<SpriteManifest>(manifest.text);
                if (data == null || data.frames == null || data.clips == null || data.pixelsPerUnit <= 0 ||
                    data.atlasWidth != atlas.width || data.atlasHeight != atlas.height)
                    throw new InvalidOperationException("Rocket atlas and manifest dimensions must match. Disable atlas resizing.");
                foreach (var f in data.frames)
                    if (f.width <= 0 || f.height <= 0 || f.x < 0 || f.y < 0 ||
                        f.x + f.width > atlas.width || f.y + f.height > atlas.height)
                        throw new InvalidOperationException("Rocket frame lies outside its atlas.");
                foreach (var c in data.clips)
                    if (c.fps <= 0 || c.count < 1 || c.start < 0 || c.start + c.count > data.frames.Length)
                        throw new InvalidOperationException("Rocket clip has an invalid frame range.");
                shared = new SharedFrames { data = data, sprites = new Sprite[data.frames.Length] };
                for (int i = 0; i < data.frames.Length; i++)
                {
                    var f = data.frames[i];
                    shared.sprites[i] = Sprite.Create(atlas, new Rect(f.x, f.y, f.width, f.height),
                        new Vector2(.5f, .5f), data.pixelsPerUnit, 0, SpriteMeshType.FullRect);
                    shared.sprites[i].name = f.name;
                }
                Cache.Add(cacheKey, shared);
            }
            shared.users++;
            return true;
        }

        void OnEnable() { if (playOnEnable) Play(initialClip); }
        void OnDisable() { IsPlaying = false; }

        public bool Play(string clipName)
        {
            if (!Initialize()) return false;
            var found = Array.Find(shared.data.clips, c => c.name == clipName);
            if (found == null) return false;
            current = found; elapsed = 0; IsPlaying = true;
            Show(current.start);
            return true;
        }

        public void Stop() { IsPlaying = false; }

        void Show(int index)
        {
            if (shown == index) return;
            Renderer.sprite = shared.sprites[index]; shown = index;
        }

        void Update()
        {
            if (!IsPlaying || current == null) return;
            elapsed += useUnscaledTime ? Time.unscaledDeltaTime : Time.deltaTime;
            if (current.loop) elapsed %= current.Duration;
            else if (elapsed >= current.Duration)
            {
                string finished = current.name;
                Show(current.start + current.count - 1); IsPlaying = false;
                if (returnToIdle && finished != "Idle") Play("Idle");
                Completed?.Invoke(finished);
                return;
            }
            Show(current.start + Mathf.Min(current.count - 1, Mathf.FloorToInt(elapsed * current.fps)));
        }

        void OnDestroy()
        {
            if (shared == null) return;
            if (--shared.users == 0)
            {
                foreach (var sprite in shared.sprites) if (sprite != null) Destroy(sprite);
                Cache.Remove(cacheKey);
            }
            shared = null;
        }
    }
}
