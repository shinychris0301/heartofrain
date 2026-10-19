using UnityEngine;

namespace HeartOfTheRain.M04
{
    /// <summary>Optional editor-baked sprite subassets and native AnimationClips.</summary>
    public sealed class SpriteFrameSet : ScriptableObject
    {
        public Sprite[] frames;
        public AnimationClip[] clips;
    }
}
