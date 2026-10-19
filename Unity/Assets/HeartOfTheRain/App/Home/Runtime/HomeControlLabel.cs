using UnityEngine;
namespace HeartOfTheRain.App.Home
{
    // Stable semantic names for focus tools and an eventual native accessibility bridge.
    // This component alone does not enable VoiceOver/TalkBack.
    public sealed class HomeControlLabel : MonoBehaviour
    {
        public string label;
        public string action;
    }
}
