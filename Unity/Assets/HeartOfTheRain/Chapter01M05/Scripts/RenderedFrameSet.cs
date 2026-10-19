using UnityEngine;

namespace HeartOfTheRain.M05
{
    /// <summary>Optional editor-baked sprite subassets and native AnimationClips.</summary>
    public sealed class RenderedFrameSet : ScriptableObject
    {
        public Sprite[] frames;
        public AnimationClip[] clips;
    }
}
